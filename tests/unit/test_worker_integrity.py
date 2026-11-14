"""``worker/integrity.py`` 的守护（M0-04/S2b-2 · AC-031 写入侧前提）。

判据分四组，每条都**能被证伪**（正向对照见 ``evidence/M0/M0-04/positive-control-s2b2.log``）：

① **冻结形状**：``verify_artifact_index(conn, data_dir) -> list[Discrepancy]`` 与
   ``manifest_rows(conn) -> list[ManifestRow]`` 的签名逐字取自 ``inspect``（design §5:52），
   ``Discrepancy`` 的**前五个字段**逐字等于 design 给出的五元组
   ``(workspace_id, artifact_id, relative_path, expected_sha256, actual_sha256|None)``。
② **五种差异形态**（design §5:52 / 派单文 §3）：缺件、sha256 不符、byte_size 不符
   三条已落地，各一条用例；另加两条安全兜底（路径逃逸、读不出来）。
   ``result_json`` 侧两条**当前不可产出**，由 ③ 显式钉住，禁被静默当作已覆盖。
③ **同口径复核（A157）**：sha256 必须走 ``infra.artifacts.hash_file``。行为面用
   monkeypatch 记录器证明真的被调到；静态面用 AST 证明本模块**没有第二份**哈希实现
   （不 import ``hashlib``、不出现 ``hexdigest``）。口径分叉即等于校验失效，故两条都留。
④ **零 SQL 文本**（design §4 / A81）：``worker/**`` 内不得出现表级 SQL 字面量。
   全量守护在 ``tests/unit/test_job_repository_terminal.py``（本子任务硬禁，不改），
   这里对**本 lane 新增的两个模块**做同一判据的路径限定复算，便于自验时不依赖全表。

库用活契约 DDL 建（``contracts/sqlite-v1.sql``），不跑 alembic —— 与
``tests/integration/jobs/test_artifact_write.py`` 同体例。探针一律落在 ``tmp_path``。
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import inspect
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

import pytest
from sqlalchemy import Engine

from campaignlab.api.common import canonical_json
from campaignlab.infra.artifacts import (
    ARTIFACT_KIND_JOB_RESULT,
    hash_file,
    relative_path_for,
)
from campaignlab.infra.db.engine import connect, make_engine
from campaignlab.infra.db.repositories import (
    ArtifactRecord,
    ArtifactRepository,
    JobRecord,
    JobRepository,
)
from campaignlab.worker import integrity
from campaignlab.worker.integrity import (
    BYTE_SIZE_MISMATCH,
    MISSING_FILE,
    PATH_ESCAPE,
    POINTER_RESULT_JSON,
    POINTER_RESULT_JSON_OBJECT,
    POINTER_RESULT_REF_ID,
    POINTER_RESULT_REF_KIND,
    POINTER_RESULT_REF_SHAPE,
    RESULT_JSON_UNPARSEABLE,
    RESULT_REF_DANGLING,
    RESULT_REF_KIND,
    SHA256_MISMATCH,
    UNREADABLE,
    Discrepancy,
    ManifestRow,
    manifest_rows,
    verify_artifact_index,
)
from campaignlab.worker.states import STAGE_CLAIMED, STAGE_QUEUED

REPO: Final = Path(__file__).resolve().parents[2]
DDL: Final = REPO / "contracts" / "sqlite-v1.sql"
MODULE_PATH: Final = REPO / "src" / "campaignlab" / "worker" / "integrity.py"
DEPS_PATH: Final = REPO / "src" / "campaignlab" / "worker" / "deps.py"

#: 显式时钟的固定时刻（禁 ``datetime.now()``，design §4）。
T0: Final = datetime(2026, 11, 14, 1, 0, 0, tzinfo=UTC)
WS_A: Final = "ws-int-a"
WS_B: Final = "ws-int-b"
#: 含中文与非 ASCII 标点的载荷：顺带证明摘要口径与编码无关（一律按字节算）。
PAYLOAD_A: Final = "活动 A 复盘结果 · 金额 12345 分".encode()
PAYLOAD_B: Final = "活动 B 复盘结果 · 比率 0.15".encode()

#: ② 组用例的分母下限：至少三个工作区各一行制品，防「glob 扫空导致全绿」。
MIN_ROWS: Final = 3


# ---------------------------------------------------------------------------------- fixture


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def engine(data_dir: Path) -> Iterator[Engine]:
    """按活契约 DDL 建临时库，并插两个工作区（``artifacts.workspace_id`` 的外键目标）。"""
    assert DDL.is_file(), f"活契约 DDL 读不到：{DDL}"
    state_dir = data_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    db = state_dir / "campaignlab.db"
    raw = sqlite3.connect(db)
    try:
        raw.executescript(DDL.read_text(encoding="utf-8"))
        for workspace_id in (WS_A, WS_B):
            raw.execute(
                "INSERT INTO workspaces (id, name, source_class, revision, created_at) "
                "VALUES (?, ?, 'SYNTHETIC', 1, ?)",
                (workspace_id, f"完整性工作区 {workspace_id}", T0.isoformat()),
            )
        raw.commit()
    finally:
        raw.close()
    target = make_engine(f"sqlite:///{db}")
    try:
        yield target
    finally:
        target.dispose()


# ----------------------------------------------------------------------------------- 工具


def _put_artifact(
    engine: Engine,
    data_dir: Path,
    *,
    workspace_id: str,
    artifact_id: str,
    payload: bytes,
    recorded_sha256: str | None = None,
    recorded_byte_size: int | None = None,
    relative_path: str | None = None,
) -> ArtifactRecord:
    """落一个真实制品文件并登记对应 ``artifacts`` 行。

    ``recorded_*`` / ``relative_path`` 可注入**与实物不符**的值，用来造
    sha256 不符／byte_size 不符／路径逃逸三种差异形态；路径一律经
    ``relative_path_for`` 生成，即写入侧同一个内容寻址函数（不自己拼）。
    """
    digest = hashlib.sha256(payload).hexdigest() if recorded_sha256 is None else recorded_sha256
    relative = (
        relative_path_for(kind=ARTIFACT_KIND_JOB_RESULT, workspace_id=workspace_id, sha256=digest)
        if relative_path is None
        else relative_path
    )
    if relative_path is None:
        target = data_dir.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    record = ArtifactRecord(
        workspace_id=workspace_id,
        id=artifact_id,
        kind=ARTIFACT_KIND_JOB_RESULT,
        sha256=digest,
        relative_path=relative,
        byte_size=len(payload) if recorded_byte_size is None else recorded_byte_size,
        created_at=T0.isoformat(),
    )
    with connect(engine) as conn:
        ArtifactRepository().insert(conn, artifact=record)
        # SQLAlchemy 2.0 是 commit-as-you-go：不显式 commit，连接一关这行就回滚了
        conn.commit()
    return record


def _seed_three(engine: Engine, data_dir: Path) -> list[ArtifactRecord]:
    """种下三行**互相一致**的制品（②③④ 组用例的共同前置，兼作分母）。"""
    records = [
        _put_artifact(engine, data_dir, workspace_id=WS_A, artifact_id="art-a1", payload=PAYLOAD_A),
        _put_artifact(engine, data_dir, workspace_id=WS_B, artifact_id="art-b1", payload=PAYLOAD_B),
        _put_artifact(
            engine,
            data_dir,
            workspace_id=WS_A,
            artifact_id="art-a2",
            payload=PAYLOAD_A + b"-second",
        ),
    ]
    assert len(records) >= MIN_ROWS, "前置条件：分母不足，用例会假绿"
    return records


def _reasons(found: list[Discrepancy]) -> list[str]:
    return [item.reason for item in found]


def _sql_verb_offenders(path: Path) -> list[str]:
    """复刻 ``test_worker_package_contains_no_table_dml_literals`` 的判据，限定到单文件。

    只查**非 docstring** 的字符串常量（docstring 用 AST 精确识别），白名单同为
    ``BEGIN IMMEDIATE``／``COMMIT``／``ROLLBACK`` 三条事务控制语句。
    """
    verbs = ("INSERT", "UPDATE", "DELETE", "SELECT", "CREATE", "DROP", "ALTER")
    allowed = {"BEGIN IMMEDIATE", "COMMIT", "ROLLBACK"}
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings or node.value in allowed:
                continue
            upper = node.value.upper()
            if any(f" {verb} " in f" {upper} " or upper.startswith(f"{verb} ") for verb in verbs):
                offenders.append(f"{path.name}:{node.lineno} {node.value[:60]!r}")
    return offenders


# ============================================================================= ① 冻结形状


def test_frozen_signatures_match_design_52() -> None:
    """design §5:52 的两个签名逐字钉住（``inspect`` 实取，禁写死推断值）。"""
    assert str(inspect.signature(verify_artifact_index)) == (
        "(conn: 'Connection', data_dir: 'Path') -> 'list[Discrepancy]'"
    )
    assert str(inspect.signature(manifest_rows)) == "(conn: 'Connection') -> 'list[ManifestRow]'"


def test_discrepancy_leading_five_fields_are_the_design_tuple() -> None:
    """``Discrepancy`` 前五个字段逐字等于 design §5:52 的五元组（顺序也钉住）。"""
    names = [field.name for field in dataclasses.fields(Discrepancy)]
    assert names[:5] == [
        "workspace_id",
        "artifact_id",
        "relative_path",
        "expected_sha256",
        "actual_sha256",
    ]
    assert names[5:] == ["reason", "expected_byte_size", "actual_byte_size"]


def test_manifest_row_field_surface_is_frozen() -> None:
    """``ManifestRow`` 的字段面钉住：与 ``artifacts`` 行同构，但 ``id`` 刻意叫

    ``artifact_id`` —— 清单是给备份／恢复看的，一行里同时可能出现作业 id 与制品 id，
    裸 ``id`` 会被读错。除此之外字段名、顺序与 ``ArtifactRecord`` 逐项对应
    （**不重算**任何值，见 ``ManifestRow`` 的 docstring）。
    """
    assert [field.name for field in dataclasses.fields(ManifestRow)] == [
        "workspace_id",
        "artifact_id",
        "kind",
        "sha256",
        "relative_path",
        "byte_size",
        "created_at",
    ]
    assert [field.name for field in dataclasses.fields(ArtifactRecord)] == [
        "workspace_id",
        "id",
        "kind",
        "sha256",
        "relative_path",
        "byte_size",
        "created_at",
    ]


def test_all_reason_constants_are_exported() -> None:
    """七个 reason 常量全部在 ``__all__`` 内（strict 开着 ``no_implicit_reexport``）。"""
    for name in (
        "BYTE_SIZE_MISMATCH",
        "MISSING_FILE",
        "PATH_ESCAPE",
        "RESULT_JSON_UNPARSEABLE",
        "RESULT_REF_DANGLING",
        "SHA256_MISMATCH",
        "UNREADABLE",
    ):
        assert name in integrity.__all__, name
    for symbol in integrity.__all__:
        assert hasattr(integrity, symbol), f"__all__ 里有取不到的符号：{symbol}"


# ============================================================================ ② 差异形态


def test_manifest_rows_returns_every_artifact_row_sorted(engine: Engine, data_dir: Path) -> None:
    """``manifest_rows`` 必须**逐行**给出全表制品，并按 ``(workspace_id, artifact_id)`` 排序。

    这条是 M8 正向对照暴露出来的缺口补件：原先只有「字段面」与「委托路径」两类静态断言，
    把枚举整个改空（``for workspace in []``）也不会判红 —— 清单恒空对备份来说是灾难性的
    静默失败（备份会认为「没有制品要复制」）。故这里钉住**行数等于制品数**与逐字段取值。
    """
    records = _seed_three(engine, data_dir)
    with connect(engine) as conn:
        rows = manifest_rows(conn)
    # 分母断言：行数必须等于种下的制品数，防「枚举恒空」的假绿
    assert len(rows) == len(records) >= MIN_ROWS
    assert [(row.workspace_id, row.artifact_id) for row in rows] == sorted(
        (record.workspace_id, record.id) for record in records
    )
    by_id = {record.id: record for record in records}
    for row in rows:
        record = by_id[row.artifact_id]
        assert (row.workspace_id, row.kind, row.sha256, row.relative_path) == (
            record.workspace_id,
            record.kind,
            record.sha256,
            record.relative_path,
        )
        assert (row.byte_size, row.created_at) == (record.byte_size, record.created_at)
    assert {row.workspace_id for row in rows} == {WS_A, WS_B}, "必须跨工作区取全，禁只取一个"


def test_manifest_rows_reads_the_index_only_never_the_filesystem(
    engine: Engine, data_dir: Path
) -> None:
    """清单只反映**索引声称**的值：删实物、改实物都不改清单（实测复核是 verify 的职责）。

    顺带把两者的分工钉住：同一状态下 ``verify_artifact_index`` 必须恰好报出这两处差异，
    否则「清单」与「实物」就无法分开归因（OPERATIONS.md:20 的备份语义要求二者可对照）。
    """
    records = _seed_three(engine, data_dir)
    data_dir.joinpath(*records[0].relative_path.split("/")).unlink()
    data_dir.joinpath(*records[1].relative_path.split("/")).write_bytes(b"tampered")
    with connect(engine) as conn:
        rows = manifest_rows(conn)
    assert len(rows) == len(records)
    by_id = {row.artifact_id: row for row in rows}
    for record in records:
        assert by_id[record.id].sha256 == record.sha256, "清单不得随实物漂移"
    with connect(engine) as conn:
        assert sorted(item.reason for item in verify_artifact_index(conn, data_dir)) == sorted(
            [MISSING_FILE, SHA256_MISMATCH]
        )


def test_verify_artifact_index_is_empty_when_index_and_files_agree(
    engine: Engine, data_dir: Path
) -> None:
    """一致 ⇒ 返回 ``[]``（design §5:52：这就是「数据库和制品摘要一致」）。"""
    _seed_three(engine, data_dir)
    with connect(engine) as conn:
        assert verify_artifact_index(conn, data_dir) == []
        # 分母自证：确实核到了行，不是空表假绿
        assert len(manifest_rows(conn)) >= MIN_ROWS


def test_verify_artifact_index_reports_missing_file(engine: Engine, data_dir: Path) -> None:
    """形态一「缺件」：删掉终态文件 ⇒ ``MISSING_FILE`` 且 ``actual_sha256 is None``。"""
    records = _seed_three(engine, data_dir)
    victim = records[0]
    (data_dir.joinpath(*victim.relative_path.split("/"))).unlink()
    with connect(engine) as conn:
        found = verify_artifact_index(conn, data_dir)
    assert _reasons(found) == [MISSING_FILE]
    only = found[0]
    assert (only.workspace_id, only.artifact_id) == (victim.workspace_id, victim.id)
    assert only.relative_path == victim.relative_path
    assert only.expected_sha256 == victim.sha256
    assert only.actual_sha256 is None, "根本没读到内容，禁填一个假摘要"


def test_verify_artifact_index_reports_sha256_mismatch(engine: Engine, data_dir: Path) -> None:
    """形态二「sha256 不符」：换掉文件内容 ⇒ 报出**实测**摘要，可直接定位篡改。"""
    records = _seed_three(engine, data_dir)
    victim = records[1]
    target = data_dir.joinpath(*victim.relative_path.split("/"))
    tampered = b"tampered payload"
    target.write_bytes(tampered)
    with connect(engine) as conn:
        found = verify_artifact_index(conn, data_dir)
    assert _reasons(found) == [SHA256_MISMATCH]
    only = found[0]
    assert only.artifact_id == victim.id
    assert only.expected_sha256 == victim.sha256
    assert only.actual_sha256 == hashlib.sha256(tampered).hexdigest()
    assert only.expected_byte_size == victim.byte_size
    assert only.actual_byte_size == len(tampered)


def test_verify_artifact_index_reports_byte_size_mismatch(engine: Engine, data_dir: Path) -> None:
    """形态三「byte_size 不符」：实物与摘要都对、只有索引行的尺寸被写坏。

    这条正是 ``SHA256_MISMATCH`` 与 ``BYTE_SIZE_MISMATCH`` **不合并报**的意义所在：
    摘要对得上说明内容没被换，尺寸对不上说明是索引行坏了，两者的排查方向完全不同。
    """
    _put_artifact(engine, data_dir, workspace_id=WS_A, artifact_id="art-a1", payload=PAYLOAD_A)
    bad = _put_artifact(
        engine,
        data_dir,
        workspace_id=WS_B,
        artifact_id="art-b1",
        payload=PAYLOAD_B,
        recorded_byte_size=len(PAYLOAD_B) + 999,
    )
    with connect(engine) as conn:
        found = verify_artifact_index(conn, data_dir)
    assert _reasons(found) == [BYTE_SIZE_MISMATCH], found
    only = found[0]
    assert only.artifact_id == bad.id
    assert only.actual_sha256 == hashlib.sha256(PAYLOAD_B).hexdigest(), (
        "前提：摘要必须是对的，否则该报 SHA256_MISMATCH 而不是 BYTE_SIZE_MISMATCH"
    )
    assert (only.expected_byte_size, only.actual_byte_size) == (
        len(PAYLOAD_B) + 999,
        len(PAYLOAD_B),
    )


def test_verify_artifact_index_reports_path_escape_without_hashing_outside(
    engine: Engine, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """安全兜底一：``relative_path`` 逃出 ``<data_dir>`` ⇒ ``PATH_ESCAPE``，且**绝不去读它**。

    DDL 只保证 ``relative_path`` 非空且 UNIQUE，不保证它不含 ``..``。若复核器照着读，
    一个被写坏的索引行就能让「校验」去哈希数据目录之外的文件（甚至 ``data_dir /
    "/etc/passwd"`` 这种被 pathlib 解释成绝对路径而整个覆盖前缀的形状）。
    """
    _seed_three(engine, data_dir)
    outside = data_dir.parent / "outside.bin"
    outside.write_bytes(b"should never be hashed")
    _put_artifact(
        engine,
        data_dir,
        workspace_id=WS_A,
        artifact_id="art-escape",
        payload=b"unused-relative-escape",
        relative_path="../outside.bin",
    )
    _put_artifact(
        engine,
        data_dir,
        workspace_id=WS_A,
        artifact_id="art-abs-escape",
        payload=b"unused-absolute-escape",
        relative_path=str(outside),
    )
    hashed: list[Path] = []
    real_hash_file = hash_file

    def _recorder(path: Path, **kwargs: object) -> tuple[str, int]:
        hashed.append(Path(path))
        return real_hash_file(path)

    monkeypatch.setattr("campaignlab.worker.integrity.hash_file", _recorder)
    with connect(engine) as conn:
        found = verify_artifact_index(conn, data_dir)
    assert sorted(_reasons(found)) == [PATH_ESCAPE, PATH_ESCAPE], found
    assert all(Path(item).resolve() != outside.resolve() for item in hashed), (
        "逃逸路径必须在哈希之前就被拦下"
    )


def test_verify_artifact_index_reports_unreadable_file(
    engine: Engine, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """安全兜底二：文件在但读不出来 ⇒ ``UNREADABLE``，而不是把异常抛给调用方。

    复核器的职责是**出具可定位的差异清单**；一个读不动的文件若让整个校核崩掉，
    就正好丢掉了「缺件可定位」这条 AC-031 前提。用 monkeypatch 造 ``OSError``
    而不是靠 ``chmod 000``：后者在 root 下不成立，会变成环境相关的假绿／假红。
    """
    records = _seed_three(engine, data_dir)
    victim_path = data_dir.joinpath(*records[0].relative_path.split("/"))

    real_hash_file = hash_file
    boom_calls: list[Path] = []

    def _boom(path: Path, **kwargs: object) -> tuple[str, int]:
        if Path(path).resolve() == victim_path.resolve():
            boom_calls.append(Path(path))
            raise OSError(13, "Permission denied")
        return real_hash_file(path)

    monkeypatch.setattr("campaignlab.worker.integrity.hash_file", _boom)
    with connect(engine) as conn:
        found = verify_artifact_index(conn, data_dir)
    assert _reasons(found) == [UNREADABLE]
    assert found[0].artifact_id == records[0].id
    assert found[0].actual_sha256 is None
    assert len(boom_calls) == 1, "只有受害行该抛错，其余行必须被放行"


def test_verify_artifact_index_rejects_relative_data_dir(engine: Engine, tmp_path: Path) -> None:
    """``data_dir`` 必须是绝对路径（与 ``ArtifactWriter`` / ``sweep_unreferenced`` 同口径）。"""
    with connect(engine) as conn, pytest.raises(ValueError, match="绝对路径"):
        verify_artifact_index(conn, Path("relative/data"))
    assert tmp_path.is_absolute(), "前置条件：tmp_path 本身是绝对路径"


# ======================================================================= ③ 同口径（A157）


def test_hashing_goes_through_infra_hash_file(
    engine: Engine, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A157 行为面：复核**确实**调到 ``infra.artifacts.hash_file``，且逐行各调一次。

    用记录器替身包住真函数（不改返回值），故摘要结论仍然成立；断言的是「被调用的
    对象与参数」，这就把「自己另写一份哈希」这条退路堵死了。
    """
    records = _seed_three(engine, data_dir)
    calls: list[Path] = []
    real_hash_file = hash_file

    def _recorder(path: Path, **kwargs: object) -> tuple[str, int]:
        calls.append(Path(path))
        return real_hash_file(path)

    monkeypatch.setattr("campaignlab.worker.integrity.hash_file", _recorder)
    with connect(engine) as conn:
        assert verify_artifact_index(conn, data_dir) == []
    expected = {data_dir.joinpath(*r.relative_path.split("/")).resolve() for r in records}
    assert {item.resolve() for item in calls} == expected
    assert len(calls) == len(records), "每行制品恰好一次，禁重复哈希"


def test_integrity_module_has_no_second_hash_implementation() -> None:
    """A157 静态面：本模块**不含**第二份摘要实现。

    两条 AST 判据（禁正则扫源码文本）：① 必须有 ``from campaignlab.infra.artifacts
    import ... hash_file``；② 全文不得 import ``hashlib``、不得出现 ``hexdigest`` 属性
    访问。理由见 design §11-A157：两份实现必然在 chunk 边界／空文件处置上漂移，
    而漂移的表现形式恰好是「校验静默失配」。
    """
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    imported_from_artifacts: set[str] = set()
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "campaignlab.infra.artifacts":
            imported_from_artifacts.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
    assert "hash_file" in imported_from_artifacts, "必须复用写入侧的公共 hash_file（A157）"
    assert "hashlib" not in imported_modules, "禁引入第二份摘要实现"
    hexdigest_calls = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "hexdigest"
    ]
    assert hexdigest_calls == [], f"禁自算摘要：{hexdigest_calls}"


# ============================================================ ③b jobs 侧缺口的显式钉住


def test_jobs_side_reasons_are_declared_and_now_produced() -> None:
    """**S2b-3 翻转的绊线**（原名 ``..._are_declared_but_not_yet_produced``）。

    S2b-2 交这条用例时 ④⑤ 判据**不可产出**（枚举 ``jobs`` 行需要的只读查询被
    ``test_worker_package_contains_no_table_dml_literals`` 判红、``JobRepository`` 也没有
    读侧枚举访问器，两处都在当时的硬禁内），故它把「缺口」本身钉住：常量各只出现一次
    ＋ docstring 必须写「尚未产出」。它的 docstring 明写了绊线语义 ——「将来谁真的实现了
    jobs 侧（常量出现第二处引用），或谁把披露文字删了，都会立刻判红」。

    S2b-3 依 **A204**（A82 的 append-only 豁免，纯追加 ``JobRepository.list_for_workspace``）
    与 **A205**（④⑤ 的精确判据）把缺口补齐，绊线**按设计触发**，故在此翻转为「已落地」形态：
    两条 reason 必须**既被声明也被使用**，且 docstring 不得再声称未产出。牙没有变钝 ——
    方向反了而已：谁把 ④⑤ 的实现删回去（常量退回只出现一次），这条立刻判红。

    这是本 lane 唯一改动的既有 S2b-2 用例，已按 A159 报 U 项／诚实偏差：派单文 §3 同时
    要求「删掉 ``.. warning::`` 占位」与「禁删改既有 19 条用例」，两条命令对本用例互斥
    （它断言的正是那段占位文字与「常量只出现一次」），无法同时满足。用例总数只增不减。
    """
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    for constant_name in ("RESULT_JSON_UNPARSEABLE", "RESULT_REF_DANGLING"):
        uses = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and node.id == constant_name
        ]
        assert len(uses) >= 2, f"{constant_name} 必须既声明又被使用（④⑤ 已落地），实测 {uses}"
    doc = inspect.getdoc(verify_artifact_index) or ""
    assert "尚未产出" not in doc, "④⑤ 已落地，禁继续声称未产出（那会让覆盖面被高估）"
    assert RESULT_JSON_UNPARSEABLE in doc and RESULT_REF_DANGLING in doc
    assert "五项判据全部落地" in doc, "docstring 必须登记五项判据齐备"


# ======================================================================= ④ 零 SQL 文本


@pytest.mark.parametrize("path", [MODULE_PATH, DEPS_PATH], ids=["integrity", "deps"])
def test_new_worker_modules_contain_no_sql_text(path: Path) -> None:
    """本 lane 新增的两个 ``worker/**`` 模块零表级 SQL 字面量（design §4 / A81）。

    与 ``test_job_repository_terminal.py::test_worker_package_contains_no_table_dml_literals``
    同判据、同白名单，只做**路径限定**复算（LANE-COMMON §4：自验不跑全表）。
    制品行的读取因此必须委托既有仓储面，这正是 ``_artifact_records`` 走
    ``WorkspaceRepository.list_page`` + ``ArtifactRepository.list_for_workspace`` 的原因。
    """
    assert path.is_file(), f"被测模块不存在：{path}"
    assert _sql_verb_offenders(path) == []


def test_artifact_enumeration_delegates_to_repositories() -> None:
    """枚举路径钉住：只准用仓储面，禁就地写查询。"""
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "campaignlab.infra.db.repositories":
            imported.update(alias.name for alias in node.names)
    assert {"ArtifactRecord", "ArtifactRepository", "WorkspaceRepository"} <= imported
    called = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in {"list_page", "list_for_workspace"}
    }
    assert called == {"list_page", "list_for_workspace"}, called


# ================================================ ⑤ S2b-3：``jobs`` 侧 ④⑤ 判据（A204 / A205）

JOB_KIND: Final = "COMPARE"
INPUT_DIGEST: Final = "0" * 64
LEASE_SPAN: Final = timedelta(hours=1)
#: ④⑤ 组的分母下限：至少三个工作区各一行作业，防「枚举扫空导致全绿」。
MIN_JOBS: Final = 3


def _ref_json(job_id: str) -> str:
    """A155① 冻结的 ``result_ref`` 形状（canonical JSON，键序稳定、无多余空白）。

    即 ``ObjectRef(kind="job", id=<job_id>)`` 的 JSON 对象 —— 写入侧 ``store.succeed``
    就是用 ``canonical_json(result_ref.model_dump(mode="json"))`` 落库的（A73），故复核侧
    按同一形状解。
    """
    return canonical_json({"kind": RESULT_REF_KIND, "id": job_id})


def _enqueue(engine: Engine, *, workspace_id: str, job_id: str, created_at: datetime) -> None:
    """入队一条 QUEUED 作业（``result_json`` 为 NULL，A205 要求这类行**不核**）。"""
    with connect(engine) as conn:
        JobRepository().insert(
            conn,
            job=JobRecord(
                workspace_id=workspace_id,
                id=job_id,
                kind=JOB_KIND,
                state="QUEUED",
                attempt=0,
                progress=0,
                stage=STAGE_QUEUED,
                lease_token=None,
                lease_deadline=None,
                retry_of=None,
                retryable=False,
                input_json=canonical_json({"snapshot": "S-1"}),
                input_digest=INPUT_DIGEST,
                result_json=None,
                problem_json=None,
                revision=1,
                created_at=created_at.isoformat(),
            ),
        )
        conn.commit()


def _put_succeeded_job(
    engine: Engine,
    *,
    workspace_id: str,
    job_id: str,
    result_json: str,
    created_at: datetime = T0,
) -> JobRecord:
    """走**真实写路径**（``insert`` → ``claim_next`` → ``mark_succeeded``）造一条 SUCCEEDED 作业。

    刻意不用裸 SQL：下面这些坏形态里，除「JSON 语法错」以外**全都能被 DDL 的
    ``CHECK(json_valid(result_json))`` 放过**，所以必须证明复核器抓得住「DDL 允许写入、
    但语义已坏」的数据 —— 那才是 ④ 的真实威胁面（语法错那一支另见
    ``_inject_invalid_result_json``）。
    """
    repo = JobRepository()
    lease_token = f"lt-{job_id}"
    with connect(engine) as conn:
        repo.insert(
            conn,
            job=JobRecord(
                workspace_id=workspace_id,
                id=job_id,
                kind=JOB_KIND,
                state="QUEUED",
                attempt=0,
                progress=0,
                stage=STAGE_QUEUED,
                lease_token=None,
                lease_deadline=None,
                retry_of=None,
                retryable=False,
                input_json=canonical_json({"snapshot": "S-1"}),
                input_digest=INPUT_DIGEST,
                result_json=None,
                problem_json=None,
                revision=1,
                created_at=created_at.isoformat(),
            ),
        )
        claimed = repo.claim_next(
            conn,
            workspace_id=workspace_id,
            lease_token=lease_token,
            lease_deadline=(created_at + LEASE_SPAN).isoformat(),
            stage=STAGE_CLAIMED,
        )
        assert claimed is not None and claimed.id == job_id, "前置条件：必须认领到刚入队那条"
        moved = repo.mark_succeeded(
            conn,
            workspace_id=workspace_id,
            job_id=claimed.id,
            attempt=claimed.attempt,
            lease_token=lease_token,
            result_json=result_json,
        )
        assert moved == 1, "前置条件：终态写入必须生效（rowcount==1）"
        conn.commit()
        return claimed


def _inject_invalid_result_json(
    data_dir: Path, *, workspace_id: str, job_id: str, result_json: str
) -> None:
    """绕过 DDL 的 ``json_valid`` CHECK 直写坏行（只用于「JSON 语法错」这一支）。

    ``jobs.result_json`` 带 ``CHECK(result_json IS NULL OR json_valid(result_json))``，
    常规写入路径**造不出**真·非法 JSON。这恰好说明 ④ 的「语法错」子形态是**纵深防御**：
    它针对的是绕过 CHECK 的来源（还原的旧备份、外部工具直写、从更宽松的旧 schema 迁移）。
    故用 SQLite 的 ``PRAGMA ignore_check_constraints`` 显式造出这种坏行。探针库在
    ``tmp_path`` 下（``engine`` fixture 建的），**不碰工作树**。
    """
    db = data_dir / "state" / "campaignlab.db"
    assert db.is_file(), f"前置条件：探针库必须已由 engine fixture 建好：{db}"
    raw = sqlite3.connect(db)
    try:
        raw.execute("PRAGMA ignore_check_constraints=ON")
        raw.execute(
            "INSERT INTO jobs (workspace_id, id, kind, state, attempt, progress, stage, "
            "retryable, input_json, input_digest, revision, created_at, result_json) "
            "VALUES (?, ?, ?, 'SUCCEEDED', 1, 100, 'DONE', 0, '{}', ?, 1, ?, ?)",
            (workspace_id, job_id, JOB_KIND, INPUT_DIGEST, T0.isoformat(), result_json),
        )
        raw.commit()
    finally:
        raw.execute("PRAGMA ignore_check_constraints=OFF")
        raw.close()


def _only(found: list[Discrepancy]) -> Discrepancy:
    assert len(found) == 1, f"期望恰好 1 条差异，实测 {found}"
    return found[0]


def test_verify_artifact_index_is_empty_when_a_succeeded_job_self_ref_is_consistent(
    engine: Engine, data_dir: Path
) -> None:
    """④⑤ 的**绿路径**：合法 ``result_json`` ＋ ref 指向自己（A155① 的真实形状）⇒ 无差异。"""
    _put_succeeded_job(engine, workspace_id=WS_A, job_id="J-ok-1", result_json=_ref_json("J-ok-1"))
    _put_succeeded_job(
        engine,
        workspace_id=WS_B,
        job_id="J-ok-2",
        result_json=_ref_json("J-ok-2"),
        created_at=T0 + timedelta(minutes=1),
    )
    with connect(engine) as conn:
        assert verify_artifact_index(conn, data_dir) == []


def test_verify_artifact_index_reports_result_json_unparseable_on_invalid_json(
    engine: Engine, data_dir: Path
) -> None:
    """④-子形态 1：``result_json`` 连 JSON 都不是 ⇒ ``RESULT_JSON_UNPARSEABLE``。"""
    _inject_invalid_result_json(
        data_dir, workspace_id=WS_A, job_id="J-bad-json", result_json="{not json"
    )
    with connect(engine) as conn:
        item = _only(verify_artifact_index(conn, data_dir))
    assert item.reason == RESULT_JSON_UNPARSEABLE
    assert item.relative_path == POINTER_RESULT_JSON
    assert item.workspace_id == WS_A
    assert item.artifact_id == "J-bad-json"


def test_verify_artifact_index_reports_result_json_unparseable_when_payload_is_not_an_object(
    engine: Engine, data_dir: Path
) -> None:
    """④-子形态 2：JSON 合法但**不是对象**（数组）⇒ 同一 reason，指针区分。

    ``[1,2]`` 能通过 DDL 的 ``json_valid``，所以这是「写路径放行、语义已坏」的真实形态。
    """
    _put_succeeded_job(engine, workspace_id=WS_A, job_id="J-arr", result_json="[1,2]")
    with connect(engine) as conn:
        item = _only(verify_artifact_index(conn, data_dir))
    assert item.reason == RESULT_JSON_UNPARSEABLE
    assert item.relative_path == POINTER_RESULT_JSON_OBJECT


def test_verify_artifact_index_reports_result_json_unparseable_on_objectref_shape_violation(
    engine: Engine, data_dir: Path
) -> None:
    """④-子形态 3：对象但不合 ``ObjectRef`` 形状（多一个键，``extra="forbid"``）⇒ 判红。

    比 ``job_from_row`` 的构造式严：构造式会**静默忽略**多出来的键，``model_validate`` 不会。
    """
    bad = canonical_json({"kind": RESULT_REF_KIND, "id": "J-shape", "surplus": "boom"})
    _put_succeeded_job(engine, workspace_id=WS_A, job_id="J-shape", result_json=bad)
    with connect(engine) as conn:
        item = _only(verify_artifact_index(conn, data_dir))
    assert item.reason == RESULT_JSON_UNPARSEABLE
    assert item.relative_path == POINTER_RESULT_REF_SHAPE


def test_verify_artifact_index_reports_result_json_unparseable_when_ref_kind_is_not_job(
    engine: Engine, data_dir: Path
) -> None:
    """④-子形态 4：形状合法但 ``kind`` 非 ``job``（违 A155① 的冻结形状）⇒ 同一 reason。"""
    _put_succeeded_job(
        engine,
        workspace_id=WS_A,
        job_id="J-kind",
        result_json=canonical_json({"kind": "snapshot", "id": "S-1"}),
    )
    with connect(engine) as conn:
        item = _only(verify_artifact_index(conn, data_dir))
    assert item.reason == RESULT_JSON_UNPARSEABLE
    assert item.relative_path == POINTER_RESULT_REF_KIND


def test_verify_artifact_index_reports_result_ref_dangling(engine: Engine, data_dir: Path) -> None:
    """⑤：ref 指向的作业行在同工作区内**不存在** ⇒ ``RESULT_REF_DANGLING``。"""
    _put_succeeded_job(
        engine, workspace_id=WS_A, job_id="J-here", result_json=_ref_json("J-never-existed")
    )
    with connect(engine) as conn:
        item = _only(verify_artifact_index(conn, data_dir))
    assert item.reason == RESULT_REF_DANGLING
    assert item.relative_path == POINTER_RESULT_REF_ID
    assert item.artifact_id == "J-here"


def test_result_ref_dangling_is_scoped_to_the_same_workspace(
    engine: Engine, data_dir: Path
) -> None:
    """⑤ 的存在性**只在同工作区内**查：跨工作区同号不得算「存在」。

    ``jobs`` 主键是 ``(workspace_id, id)``，故 ``WS_B`` 的作业指向 ``WS_A`` 的 id 时，
    在 ``WS_B`` 内那一行并不存在 —— 必须判悬空。这条同时钉住 A204 新增访问器的
    ``WHERE workspace_id = :workspace_id``：谓词一旦被去掉，本用例立刻转红（串号）。
    """
    _put_succeeded_job(
        engine, workspace_id=WS_A, job_id="J-shared", result_json=_ref_json("J-shared")
    )
    _put_succeeded_job(
        engine,
        workspace_id=WS_B,
        job_id="J-cross",
        result_json=_ref_json("J-shared"),
        created_at=T0 + timedelta(minutes=1),
    )
    with connect(engine) as conn:
        found = verify_artifact_index(conn, data_dir)
    assert [(i.workspace_id, i.artifact_id, i.reason) for i in found] == [
        (WS_B, "J-cross", RESULT_REF_DANGLING)
    ], f"WS_A 的自指作业必须干净，只有 WS_B 的跨区引用该判悬空：{found}"


def test_jobs_with_null_result_json_are_skipped(engine: Engine, data_dir: Path) -> None:
    """A205：**只核** ``result_json IS NOT NULL`` 的行 —— QUEUED 作业不得被误报。"""
    _enqueue(engine, workspace_id=WS_A, job_id="J-queued", created_at=T0)
    _enqueue(engine, workspace_id=WS_B, job_id="J-queued-2", created_at=T0 + timedelta(minutes=1))
    with connect(engine) as conn:
        assert verify_artifact_index(conn, data_dir) == []


def test_jobs_side_discrepancy_slots_follow_the_documented_convention(
    engine: Engine, data_dir: Path
) -> None:
    """A205 的硬约束：8 字段与前 5 元组**逐字不变**，``jobs`` 侧按位复用槽位。

    钉住 ``_job_discrepancy`` docstring 里写死的槽位口径，防后来者把作业 id 塞进别的字段
    或给 ``expected_sha256`` 编一个假摘要 —— 那会让「制品侧差异」与「作业侧差异」混形。
    """
    _put_succeeded_job(engine, workspace_id=WS_A, job_id="J-slot", result_json=_ref_json("J-ghost"))
    with connect(engine) as conn:
        item = _only(verify_artifact_index(conn, data_dir))
    assert [f.name for f in dataclasses.fields(Discrepancy)] == [
        "workspace_id",
        "artifact_id",
        "relative_path",
        "expected_sha256",
        "actual_sha256",
        "reason",
        "expected_byte_size",
        "actual_byte_size",
    ], "8 字段面必须逐字不变（design §5:52 / A205）"
    assert item.workspace_id == WS_A
    assert item.artifact_id == "J-slot", "artifact_id 槽位承载被核对象主键 = jobs.id"
    assert item.relative_path == POINTER_RESULT_REF_ID, "relative_path 槽位承载 detail 指针"
    assert item.expected_sha256 == "", "jobs 侧无摘要期望值"
    assert item.actual_sha256 is None, "没做任何哈希"
    assert item.expected_byte_size is None and item.actual_byte_size is None


def test_job_enumeration_delegates_to_repositories() -> None:
    """A204 的枚举口径钉住：``jobs`` 侧也只准走仓储面，禁就地写查询、禁 ``list_all``。"""
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "campaignlab.infra.db.repositories":
            imported.update(alias.name for alias in node.names)
    assert {
        "ArtifactRecord",
        "ArtifactRepository",
        "JobRecord",
        "JobRepository",
        "WorkspaceRepository",
    } <= imported, sorted(imported)
    called = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in {"list_page", "list_for_workspace"}
    }
    assert called == {"list_page", "list_for_workspace"}, called
    banned = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in {"list_all", "execute", "executescript"}
    }
    assert banned == set(), f"禁全表无界枚举／禁就地执行 SQL：{sorted(banned)}"


def test_job_repository_list_for_workspace_is_workspace_scoped_and_ordered(
    engine: Engine,
) -> None:
    """A204 新增访问器的行为面：**只出本工作区**、按 ``(created_at, id)`` 稳定排序。

    这是「WHERE 谓词被去掉就会红」的直接守护（正向对照第 3 条），也钉住排序可复现 ——
    复核与清单都要求「同一库状态 ⇒ 同一顺序」，禁依赖 SQL 的自然返回序。
    """
    _put_succeeded_job(
        engine,
        workspace_id=WS_A,
        job_id="J-a-late",
        result_json=_ref_json("J-a-late"),
        created_at=T0 + timedelta(minutes=2),
    )
    _put_succeeded_job(
        engine,
        workspace_id=WS_A,
        job_id="J-a-early",
        result_json=_ref_json("J-a-early"),
        created_at=T0 + timedelta(minutes=1),
    )
    _put_succeeded_job(
        engine,
        workspace_id=WS_B,
        job_id="J-b-only",
        result_json=_ref_json("J-b-only"),
        created_at=T0,
    )
    with connect(engine) as conn:
        rows_a = JobRepository().list_for_workspace(conn, WS_A)
        rows_b = JobRepository().list_for_workspace(conn, WS_B)
    assert [r.id for r in rows_a] == ["J-a-early", "J-a-late"], "按 created_at, id 排序"
    assert {r.workspace_id for r in rows_a} == {WS_A}, "禁串到别的工作区"
    assert [r.id for r in rows_b] == ["J-b-only"]
    assert len(rows_a) + len(rows_b) >= MIN_JOBS, "前置条件：分母不足，用例会假绿"
    assert rows_a[0].result_json == _ref_json("J-a-early"), "result_json 必须原样透出（④⑤ 的输入）"
