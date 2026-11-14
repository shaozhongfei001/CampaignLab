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
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pytest
from sqlalchemy import Engine

from campaignlab.infra.artifacts import (
    ARTIFACT_KIND_JOB_RESULT,
    hash_file,
    relative_path_for,
)
from campaignlab.infra.db.engine import connect, make_engine
from campaignlab.infra.db.repositories import ArtifactRecord, ArtifactRepository
from campaignlab.worker import integrity
from campaignlab.worker.integrity import (
    BYTE_SIZE_MISMATCH,
    MISSING_FILE,
    PATH_ESCAPE,
    RESULT_JSON_UNPARSEABLE,
    RESULT_REF_DANGLING,
    SHA256_MISMATCH,
    UNREADABLE,
    Discrepancy,
    ManifestRow,
    manifest_rows,
    verify_artifact_index,
)

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


def test_jobs_side_reasons_are_declared_but_not_yet_produced() -> None:
    """``RESULT_JSON_*`` 两条 reason **只存在于声明处**，且缺口在 docstring 里显式披露。

    design §5:52 要求 ``verify_artifact_index`` 也核 ``jobs.result_json``（可解析 ＋
    指向存在的制品）。枚举 ``jobs`` 行需要一条只读查询或一个仓储读侧访问器：前者被
    ``test_worker_package_contains_no_table_dml_literals`` 判红（该文件在本子任务硬禁内），
    后者所在的 ``infra/db/repositories.py`` 同样硬禁且现无此访问器。故这两条当前
    **不可产出**，已按 A159 报 U 项而非自行发明判据。

    本用例的牙在于：将来谁真的实现了 jobs 侧（常量出现第二处引用），或谁把披露文字删了，
    都会立刻判红 —— 防止「声明了七个 reason、实际只产五个」被后来者静默当作已全覆盖。
    """
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    for constant_name in ("RESULT_JSON_UNPARSEABLE", "RESULT_REF_DANGLING"):
        uses = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and node.id == constant_name
        ]
        assert len(uses) == 1, f"{constant_name} 只应在定义处出现一次，实测 {uses}"
    doc = inspect.getdoc(verify_artifact_index) or ""
    assert "尚未产出" in doc, "缺口必须在 docstring 里显式披露，禁静默缩小覆盖面"
    assert RESULT_JSON_UNPARSEABLE in doc and RESULT_REF_DANGLING in doc


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
