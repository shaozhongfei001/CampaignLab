"""M0-04/S3：原子制品写入的纯函数面、暂存件生命周期与静态守护（不碰数据库）。

集成面（事务、外键、sweep 与索引的交互）在 ``tests/integration/jobs/test_artifact_write.py``；
本文件只测不需要库的部分，外加三条静态守护：

- **冻结面守护**：``begin``／``commit``／``verify_same_filesystem``／``sweep_unreferenced``
  的参数名、参数序、关键字-only 边界与默认值逐条对齐 design §5（卡内 ``public_frozen``）。
- **零 DML 守护**：本模块的 SQL 常量只允许是只读 ``SELECT``（写点收敛在
  ``infra/db/repositories.py``，A81 同型）。
- **显式时钟守护**：本模块不得 ``import time``、不得出现 ``datetime.now(``／``time.monotonic(``
  （``tests/unit/test_clock.py`` 的全树守护只看 ``datetime.now``，这里补上单调钟）。

摘要一律与 ``hashlib`` 现算值比对，**不写死十六进制字面量**（D-012／D-014：禁凭记忆填数）。
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import re
from pathlib import Path
from typing import Final

import pytest

from campaignlab.infra.artifacts import (
    ARTIFACT_ID_PREFIX,
    ARTIFACT_KIND_JOB_RESULT,
    TMP_STALE_SECONDS,
    ArtifactWriter,
    AttemptStage,
    CommittedArtifact,
    SweepReport,
    relative_path_for,
    results_root,
    stage_root,
    sweep_unreferenced,
)

REPO: Final = Path(__file__).resolve().parents[2]
MODULE_PATH: Final = REPO / "src" / "campaignlab" / "infra" / "artifacts.py"
DATA_DIR: Final = Path("/var/lib/campaignlab")
WS: Final = "ws-1"
DIGEST: Final = "a" * 64
PAYLOAD: Final = b"campaignlab-artifact-payload" * 5


# ============================================================================ 路径纯函数


def test_artifact_relative_path_is_content_addressed_and_relative() -> None:
    """design §5 的形状：``results/<kind>/<workspace_id>/<sha256[:2]>/<sha256>``。"""
    relative = relative_path_for(kind=ARTIFACT_KIND_JOB_RESULT, workspace_id=WS, sha256=DIGEST)
    assert relative == f"results/JOB_RESULT/{WS}/aa/{DIGEST}"
    assert not relative.startswith("/"), "必须是相对 <data_dir> 的路径（DDL 禁绝对路径）"
    assert "\\" not in relative, "一律 posix 分隔符，跨平台可复现"
    assert not Path(relative).is_absolute()


def test_artifact_relative_path_embeds_workspace_so_two_workspaces_never_collide() -> None:
    """``relative_path`` 是**全表** UNIQUE（不含 workspace_id），故工作区必须进路径。"""
    first = relative_path_for(kind=ARTIFACT_KIND_JOB_RESULT, workspace_id="ws-1", sha256=DIGEST)
    second = relative_path_for(kind=ARTIFACT_KIND_JOB_RESULT, workspace_id="ws-2", sha256=DIGEST)
    assert first != second
    assert first.split("/")[2] == "ws-1"
    assert second.split("/")[2] == "ws-2"


def test_artifact_roots_are_inside_the_data_dir() -> None:
    assert stage_root(DATA_DIR) == DATA_DIR / "tmp" / "jobs"
    assert results_root(DATA_DIR) == DATA_DIR / "results"
    assert stage_root(DATA_DIR).is_relative_to(DATA_DIR)
    assert results_root(DATA_DIR).is_relative_to(DATA_DIR)


@pytest.mark.parametrize(
    "digest",
    ["", "0" * 63, "0" * 65, "A" * 64, "z" * 64, "0" * 63 + "g", " " * 64],
)
def test_artifact_relative_path_rejects_bad_digest(digest: str) -> None:
    with pytest.raises(ValueError, match="sha256"):
        relative_path_for(kind=ARTIFACT_KIND_JOB_RESULT, workspace_id=WS, sha256=digest)


@pytest.mark.parametrize(
    ("kind", "workspace_id"),
    [
        ("../evil", WS),
        ("a/b", WS),
        ("a\\b", WS),
        ("", WS),
        (".", WS),
        ("..", WS),
        ("JOB_RESULT.", WS),
        ("JOB_RESULT ", WS),
        ("x" * 97, WS),
        (ARTIFACT_KIND_JOB_RESULT, "../ws"),
        (ARTIFACT_KIND_JOB_RESULT, "ws/../x"),
        (ARTIFACT_KIND_JOB_RESULT, ""),
        (ARTIFACT_KIND_JOB_RESULT, "ws 1"),
        (ARTIFACT_KIND_JOB_RESULT, "."),
    ],
)
def test_artifact_relative_path_rejects_unsafe_tokens(kind: str, workspace_id: str) -> None:
    """路径片段一律校验：``..``／分隔符／尾点尾空格都会被拒，不给目录穿越留口子。"""
    with pytest.raises(ValueError):
        relative_path_for(kind=kind, workspace_id=workspace_id, sha256=DIGEST)


# ========================================================================== 暂存件生命周期


@pytest.fixture
def writer(tmp_path: Path) -> ArtifactWriter:
    return ArtifactWriter(tmp_path)


def test_artifact_digest_is_stable_across_chunk_boundaries(
    writer: ArtifactWriter, tmp_path: Path
) -> None:
    """⑥ 同内容稳定摘要的纯函数面：分块方式不影响 sha256／byte_size。"""
    observed: set[tuple[str, int]] = set()
    for chunk_size in (1, 3, 17, len(PAYLOAD), len(PAYLOAD) + 100):
        with writer.begin(WS, "J-1", 0) as stage:
            for offset in range(0, len(PAYLOAD), chunk_size):
                stage.write(PAYLOAD[offset : offset + chunk_size])
            stage.seal()
            observed.add((stage.sha256, stage.byte_size))
    assert observed == {(hashlib.sha256(PAYLOAD).hexdigest(), len(PAYLOAD))}


def test_artifact_write_file_matches_incremental_write(
    writer: ArtifactWriter, tmp_path: Path
) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(PAYLOAD)
    with writer.begin(WS, "J-1", 0) as stage:
        moved = stage.write_file(source)
        stage.seal()
        assert moved == len(PAYLOAD)
        assert stage.sha256 == hashlib.sha256(PAYLOAD).hexdigest()
        assert stage.path.read_bytes() == PAYLOAD


def test_artifact_empty_payload_is_a_legal_artifact(writer: ArtifactWriter) -> None:
    """DDL 只要求 ``byte_size>=0``，故空制品合法；摘要取空串摘要（现算，不写死字面量）。"""
    with writer.begin(WS, "J-1", 0) as stage:
        stage.seal()
        assert stage.byte_size == 0
        assert stage.sha256 == hashlib.sha256(b"").hexdigest()
        assert stage.path.exists()
        assert stage.path.read_bytes() == b""


def test_artifact_stage_discards_payload_when_not_committed(
    writer: ArtifactWriter, tmp_path: Path
) -> None:
    """design §5：上下文退出时未提交即清 —— 尝试目录与暂存件都不留。"""
    stage = writer.begin(WS, "J-1", 3)
    stage.write(b"partial")
    assert stage.path.exists()
    stage.discard()
    assert not stage.path.exists()
    assert not stage.directory.exists()
    assert list(stage_root(tmp_path).rglob("*")) == []
    stage.discard()  # 幂等


def test_artifact_stage_cleans_up_when_handler_raises(
    writer: ArtifactWriter, tmp_path: Path
) -> None:
    """handler 抛错时暂存件被清掉，且异常**原样**冒出去（不被上下文管理器吞掉）。"""
    stage = writer.begin(WS, "J-2", 0)
    with pytest.raises(ValueError, match="handler 失败"), stage:
        stage.write(b"partial")
        raise ValueError("handler 失败")
    assert not stage.path.exists()
    assert not stage.directory.exists()
    assert list(stage_root(tmp_path).rglob("*")) == []


def test_artifact_stage_rejects_write_after_seal(writer: ArtifactWriter) -> None:
    """封口后再写会让摘要与内容脱节，必须判红而不是静默接受。"""
    with writer.begin(WS, "J-1", 0) as stage:
        stage.write(b"x")
        stage.seal()
        with pytest.raises(ValueError, match="已封口"):
            stage.write(b"y")


def test_artifact_stage_is_reusable_only_once_per_attempt_dir(
    writer: ArtifactWriter,
) -> None:
    """同一 ``(workspace_id, job_id, attempt)`` 连开两次：暂存文件名不同，互不覆写。"""
    first = writer.begin(WS, "J-1", 1)
    second = writer.begin(WS, "J-1", 1)
    try:
        assert first.directory == second.directory
        assert first.path != second.path
        first.write(b"one")
        second.write(b"two")
        assert first.path.read_bytes() == b"one"
        assert second.path.read_bytes() == b"two"
        assert first.sha256 != second.sha256
    finally:
        first.discard()
        second.discard()


@pytest.mark.parametrize("identifier", ["", ".", "..", "a/b", "a\\b", "ws 1", "x" * 97])
def test_artifact_begin_rejects_unsafe_identifiers(writer: ArtifactWriter, identifier: str) -> None:
    with pytest.raises(ValueError):
        writer.begin(identifier, "J-1", 0)
    with pytest.raises(ValueError):
        writer.begin(WS, identifier, 0)


def test_artifact_begin_rejects_negative_attempt(writer: ArtifactWriter) -> None:
    with pytest.raises(ValueError, match="attempt"):
        writer.begin(WS, "J-1", -1)


def test_artifact_writer_requires_absolute_data_dir(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="绝对路径"):
        ArtifactWriter(Path("relative/data-dir"))
    assert ArtifactWriter(tmp_path).data_dir == tmp_path


def test_artifact_verify_same_filesystem_creates_both_roots(tmp_path: Path) -> None:
    """同盘布局下不抛，并把两个根建出来（启动期幂等）。"""
    target = ArtifactWriter(tmp_path)
    target.verify_same_filesystem()  # 返回 None：不抛即通过（design §5 的签名）
    assert stage_root(tmp_path).is_dir()
    assert results_root(tmp_path).is_dir()
    target.verify_same_filesystem()  # 幂等：重复调用不得报错或重复建目录


def test_artifact_constants_match_the_frozen_design() -> None:
    """A89（kind 取 ``JOB_RESULT``）与 design §2（``TMP_STALE_SECONDS=3600``）。"""
    assert ARTIFACT_KIND_JOB_RESULT == "JOB_RESULT"
    assert TMP_STALE_SECONDS == 3600
    assert ARTIFACT_ID_PREFIX == "art"


# ============================================================================ 静态守护


def test_artifact_public_surface_matches_frozen_design() -> None:
    """卡内 ``public_frozen``：签名不得改名／改参数序／改返回类型（design §7）。"""
    begin = inspect.signature(ArtifactWriter.begin)
    assert list(begin.parameters) == ["self", "workspace_id", "job_id", "attempt"]
    assert begin.return_annotation == "AttemptStage"

    commit = inspect.signature(ArtifactWriter.commit)
    kinds = [p.kind for p in commit.parameters.values()]
    assert list(commit.parameters) == ["self", "conn", "stage", "workspace_id", "kind", "now"]
    assert kinds[:3] == [inspect.Parameter.POSITIONAL_OR_KEYWORD] * 3
    assert kinds[3:] == [inspect.Parameter.KEYWORD_ONLY] * 3
    assert commit.return_annotation == "CommittedArtifact"

    verify = inspect.signature(ArtifactWriter.verify_same_filesystem)
    assert list(verify.parameters) == ["self"]
    assert verify.return_annotation == "None"

    sweep = inspect.signature(sweep_unreferenced)
    assert list(sweep.parameters) == ["conn", "data_dir", "now", "min_age", "dry_run"]
    assert sweep.parameters["min_age"].default == TMP_STALE_SECONDS
    assert sweep.parameters["dry_run"].default is True
    assert sweep.return_annotation == "SweepReport"


def test_artifact_exported_symbols_cover_the_frozen_list() -> None:
    """design §9 给 S3 点名的符号必须全部导出；多出项白名单见下（A157 追加 hash_file）。"""
    expected = {
        "ARTIFACT_KIND_JOB_RESULT",
        "TMP_STALE_SECONDS",
        "relative_path_for",
        "stage_root",
        "results_root",
        "CommittedArtifact",
        "AttemptStage",
        "ArtifactWriter",
        "SweepReport",
        "sweep_unreferenced",
    }
    exported = set(artifacts_module_all())
    assert expected <= exported, f"冻结符号缺失：{sorted(expected - exported)}"
    #: A157：``_hash_file`` 提升为公共 ``hash_file`` 并进 ``__all__``，故多出项白名单追加
    #: 一个符号。这是**追加式**放宽：上面的 ``expected`` 冻结集合与下面各条判据一字未改。
    assert exported - expected == {"ARTIFACT_ID_PREFIX", "hash_file"}
    for name in ("begin", "commit", "verify_same_filesystem"):
        assert callable(getattr(ArtifactWriter, name))
    for symbol in (AttemptStage, ArtifactWriter, CommittedArtifact, SweepReport):
        assert isinstance(symbol, type)


def artifacts_module_all() -> list[str]:
    """读 ``__all__``（用 AST 而不是 import 副作用，避免与集成用例互相影响）。"""
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8-sig"), filename=str(MODULE_PATH))
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in statement.targets
        ):
            value = statement.value
            assert isinstance(value, ast.List)
            return [
                str(element.value) for element in value.elts if isinstance(element, ast.Constant)
            ]
    raise AssertionError(f"__all__ 不在模块顶层：{MODULE_PATH}")


def _non_docstring_strings(tree: ast.AST) -> list[tuple[int, str]]:
    """模块里所有**非 docstring** 的字符串常量（体例同 test_job_repository_terminal.py）。"""
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
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            out.append((node.lineno, node.value))
    return out


def test_artifact_module_issues_no_dml() -> None:
    """零 DML：SQL 常量只允许是两条只读 ``SELECT``，写入一律走 ``ArtifactRepository.insert``。"""
    source = MODULE_PATH.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(MODULE_PATH))
    dml = re.compile(r"\b(INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\b", re.IGNORECASE)
    offenders = [
        f"artifacts.py:{lineno} {value[:60]!r}"
        for lineno, value in _non_docstring_strings(tree)
        if dml.search(value)
    ]
    assert offenders == [], offenders
    selects = [
        value for _lineno, value in _non_docstring_strings(tree) if "SELECT" in value.upper()
    ]
    assert len(selects) == 2, f"只读 SELECT 应当恰好两条（回读权威 id + 取已引用路径）：{selects}"
    assert "ArtifactRepository" in source, "写路径必须复用仓储，禁自开 INSERT 落点"


def test_artifact_module_never_reads_the_system_clock() -> None:
    """显式时钟：不 ``import time``、不出现 ``datetime.now(``／``time.monotonic(``。"""
    source = MODULE_PATH.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(MODULE_PATH))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    assert "time" not in imported, "禁 import time：年龄判定只用 st_mtime 与注入的 now"
    for banned in ("datetime.now(", "time.monotonic(", "utcnow(", "time.time("):
        assert banned not in source, f"禁取系统当前时间：{banned}"
    assert "ensure_utc" in imported or "campaignlab.clock" in imported


def test_artifact_module_has_no_suppression_of_domain_errors() -> None:
    """``except`` 只允许吞 ``OSError`` 类的清理失败，禁吞领域错（判红优先）。"""
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8-sig"), filename=str(MODULE_PATH))
    allowed = {"OSError", "BaseException"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler) or node.type is None:
            continue
        names: list[str] = []
        if isinstance(node.type, ast.Name):
            names.append(node.type.id)
        elif isinstance(node.type, ast.Tuple):
            names.extend(item.id for item in node.type.elts if isinstance(item, ast.Name))
        for name in names:
            assert name in allowed, f"artifacts.py:{node.lineno} 吞了未预期的异常类型 {name}"
