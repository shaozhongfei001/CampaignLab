"""FU-8（缺陷 D-028 / 裁定 A80）：alembic head 读取「定义点唯一」的机器守护。

对应派单文 §4.3 的三条硬断言：

① **调用点唯一**：用 ``tokenize`` 扫 ``src/campaignlab/`` 下每个 ``*.py`` 的 **NAME token**
   （STRING 与 COMMENT 天然被排除，故 docstring/注释里的提及不算调用），断言
   ``get_current_head`` 的代码级引用只有 ``infra/db/migration_head.py`` 一处；``ScriptDirectory``
   与 ``alembic`` 这两个「实现依赖」同样只准出现在那里。另按**原文**扫描
   ``application/health_service.py`` 与 ``cli.py``：字面量 ``get_current_head`` 命中数必须为 0
   —— 收口后连 docstring 提及都不留，免得下一个读者以为那两侧还各有一份实现。
② **向后兼容**：``campaignlab.application.health_service`` 仍能 import 到 ``read_migration_head``
   与 ``UNMIGRATED_REVISION``（两者都已进 public_frozen 扩围，A77/A78），且它们与新模块是
   **同一个对象**（re-export，不是第二份实现）；哨兵/目录常量的**模块级定义点**钉在已知集合内。
③ **未迁移环境**：``tmp_path`` 造的空迁移目录 → ``read_migration_head()`` 返回 ``None``（降级、
   禁猜 revision）；把真实 ``alembic.ini`` 复制进一个空的脚本目录同样读不出 head。
   ``HealthService.schema_revision()`` 在无库时落哨兵串。全程不碰真实 data_dir、不碰网络。

外加委托自证：``cli._migration_head()`` 只剩一条委托语句（函数体内既无 alembic import 也无
head 调用），且把唯一实现换掉就能改变它的返回值 —— 证明它真的走单点，而不是自己留了一份。
"""

from __future__ import annotations

import ast
import inspect
import io
import shutil
import tokenize
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pytest

import campaignlab.application.health_service as health_service
import campaignlab.cli as campaignlab_cli
import campaignlab.infra.db.migration_head as migration_head
from campaignlab.application.health_service import HealthService, read_migration_head
from campaignlab.clock import FixedClock
from campaignlab.config import load_config, repo_root

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
SRC_ROOT: Final = REPO_ROOT / "src" / "campaignlab"
HEAD_SYMBOL: Final = "get_current_head"
SINGLE_SOURCE_REL: Final = "infra/db/migration_head.py"
DELEGATING_RELS: Final = ("application/health_service.py", "cli.py")
#: 显式时钟（领域不变量：禁取系统当前时间）。
T0: Final = datetime(2026, 11, 13, 1, 0, 0, tzinfo=UTC)
#: 模块级定义点的期望集合。``cli.py`` 的 ``MIGRATIONS_DIR`` 是写集所限（只许改
#: ``_migration_head()``）保留的已知残留，已按 U 项上交编排器；再多一处即判红。
EXPECTED_DEFINITION_SITES: Final[dict[str, set[str]]] = {
    "UNMIGRATED_REVISION": {SINGLE_SOURCE_REL},
    "MIGRATIONS_DIR": {SINGLE_SOURCE_REL, "cli.py"},
}


def _src_python_files() -> list[Path]:
    files = sorted(SRC_ROOT.rglob("*.py"))
    assert files, f"src 下扫不到 Python 文件：{SRC_ROOT}"
    return files


def _code_reference_files(symbol: str) -> set[str]:
    """返回**代码**里出现 ``symbol`` 这个标识符的 src 文件（相对 ``src/campaignlab``）。"""
    hits: set[str] = set()
    for path in _src_python_files():
        source = path.read_text(encoding="utf-8")
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.NAME and token.string == symbol:
                hits.add(str(path.relative_to(SRC_ROOT)))
                break
    return hits


def _top_level_definitions(names: tuple[str, ...]) -> dict[str, set[str]]:
    """模块级赋值（``Assign`` 与 ``x: Final = ...`` 的 ``AnnAssign``）里定义 ``names`` 的文件。"""
    found: dict[str, set[str]] = {name: set() for name in names}
    for path in _src_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for statement in tree.body:
            targets: list[ast.expr] = []
            if isinstance(statement, ast.Assign):
                targets = list(statement.targets)
            elif isinstance(statement, ast.AnnAssign):
                targets = [statement.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in found:
                    found[target.id].add(str(path.relative_to(SRC_ROOT)))
    return found


def test_head_call_site_is_unique_to_the_single_source_module() -> None:
    hits = _code_reference_files(HEAD_SYMBOL)
    assert hits == {SINGLE_SOURCE_REL}, (
        f"{HEAD_SYMBOL} 的代码级调用点必须唯一（D-028 收口）；实测命中 {sorted(hits)}"
    )


def test_alembic_dependency_is_confined_to_the_single_source_module() -> None:
    for symbol in ("ScriptDirectory", "alembic"):
        hits = _code_reference_files(symbol)
        assert hits == {SINGLE_SOURCE_REL}, (
            f"实现依赖 {symbol} 只准出现在唯一实现模块；实测命中 {sorted(hits)}"
        )


def test_delegating_files_never_mention_the_head_symbol_again() -> None:
    offenders: list[str] = []
    for rel in DELEGATING_RELS:
        if HEAD_SYMBOL in (SRC_ROOT / rel).read_text(encoding="utf-8"):
            offenders.append(rel)
    assert not offenders, f"委托方不得再出现 {HEAD_SYMBOL} 字面量（含 docstring/注释）：{offenders}"


def test_sentinel_and_dir_constants_have_the_pinned_definition_sites() -> None:
    measured = _top_level_definitions(tuple(EXPECTED_DEFINITION_SITES))
    assert measured == EXPECTED_DEFINITION_SITES, (
        f"常量定义点漂移：实测 {measured} != 期望 {EXPECTED_DEFINITION_SITES}"
    )


def test_health_service_still_exports_the_frozen_names() -> None:
    assert read_migration_head is migration_head.read_migration_head, (
        "health_service.read_migration_head 必须是唯一实现模块那个对象（re-export）"
    )
    assert health_service.UNMIGRATED_REVISION is migration_head.UNMIGRATED_REVISION
    assert health_service.MIGRATIONS_DIR is migration_head.MIGRATIONS_DIR
    for name in ("MIGRATIONS_DIR", "UNMIGRATED_REVISION", "read_migration_head"):
        assert name in health_service.__all__, f"{name} 已从 health_service.__all__ 消失"
        assert hasattr(health_service, name), f"{name} 无法从 health_service import"


def test_cli_helper_is_a_bare_delegation(monkeypatch: pytest.MonkeyPatch) -> None:
    source = inspect.getsource(campaignlab_cli._migration_head)
    assert HEAD_SYMBOL not in source, "cli._migration_head 里不该再有 head 调用"
    assert "from alembic" not in source, "cli._migration_head 里不该再有 alembic import"
    assert "ScriptDirectory" not in source, "cli._migration_head 里不该再有脚本目录对象"
    assert "read_migration_head(" in source, "cli._migration_head 必须委托唯一实现模块"
    assert campaignlab_cli.MIGRATIONS_DIR == migration_head.MIGRATIONS_DIR

    seen: list[Path | None] = []

    def fake(migrations_dir: Path | None = None) -> str:
        seen.append(migrations_dir)
        return "SENTINEL-VIA-SINGLE-SOURCE"

    monkeypatch.setattr(campaignlab_cli, "read_migration_head", fake)
    assert campaignlab_cli._migration_head() == "SENTINEL-VIA-SINGLE-SOURCE", (
        "cli._migration_head 没走单点：它自己留了一份实现"
    )
    assert seen == [repo_root() / campaignlab_cli.MIGRATIONS_DIR], (
        f"委托时传入的迁移目录必须与收口前逐字相同；实测 {seen}"
    )


def test_empty_migrations_directory_degrades_without_guessing(tmp_path: Path) -> None:
    empty = tmp_path / "migrations"
    empty.mkdir()
    assert migration_head.read_migration_head(empty) is None
    assert migration_head.read_migration_head(tmp_path / "no-such-directory") is None


def test_ini_with_empty_script_directory_reports_no_head(tmp_path: Path) -> None:
    """把真实 ini 搬进一个空的脚本目录：读不出 head 也必须降级为 None，不抛错。"""
    real_ini = REPO_ROOT / "migrations" / "alembic.ini"
    assert real_ini.is_file(), f"本仓迁移环境本身应可用：{real_ini}"
    target = tmp_path / "migrations"
    target.mkdir()
    shutil.copy(real_ini, target / "alembic.ini")
    (target / "versions").mkdir()
    assert migration_head.read_migration_head(target) is None


def test_unmigrated_environment_reports_the_sentinel_string(tmp_path: Path) -> None:
    config = load_config(environ={"CAMPAIGNLAB_DATA_DIR": str(tmp_path)}, home=tmp_path)
    service = HealthService(config=config, clock=FixedClock(T0))
    assert service.schema_revision() == migration_head.UNMIGRATED_REVISION
    snapshot = service.snapshot()
    assert snapshot.schema_revision == health_service.UNMIGRATED_REVISION
    assert snapshot.worker == "OFFLINE"
    assert snapshot.status == "DEGRADED"


def test_both_readers_agree_on_the_repository_head() -> None:
    head = migration_head.read_migration_head()
    assert head is not None, "本仓 migrations/alembic.ini 应能读出 head；读出 None 说明迁移环境坏了"
    assert head != migration_head.UNMIGRATED_REVISION, "哨兵串不得与真实 revision 同值"
    assert campaignlab_cli._migration_head() == head
    assert read_migration_head() == head
