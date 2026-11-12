"""契约切片工具的回归护栏（D-001 修复后新增）。

背景：slice_tables 的旧正则在找 "\n);"，而参考 DDL 的 28 张表一律以 ") STRICT;"
结尾，导致 --tables 静默返回 NOT_FOUND 且退出码为 0。本测试把三件事钉死：
表数分母、解析完整性、索引覆盖完整性。任一退化即红。

约定：必须从仓库根目录运行 pytest（contract_slice 以仓库根为相对路径基准）。
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    path = ROOT / "scripts" / "contract_slice.py"
    spec = importlib.util.spec_from_file_location("contract_slice", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ddl_text() -> str:
    return (ROOT / "spec/CampaignLab-SDD-v1.0/contracts/sqlite-v1.sql").read_text(encoding="utf-8")


def test_working_dir_is_repo_root() -> None:
    assert (mod_spec := Path.cwd() / "spec/CampaignLab-SDD-v1.0").is_dir(), mod_spec


def test_all_table_names_finds_28(mod: ModuleType) -> None:
    names = mod.all_table_names()
    assert len(names) == 28
    assert len(set(names)) == 28


def test_every_table_resolves_without_not_found(mod: ModuleType) -> None:
    ddl = mod.slice_tables(mod.all_table_names())
    not_found = [k for k, v in ddl.items() if v == "NOT_FOUND"]
    assert not_found == []
    tables = [k for k in ddl if not k.endswith("__indexes")]
    assert len(tables) == 28


def test_table_blocks_are_well_formed(mod: ModuleType) -> None:
    ddl = mod.slice_tables(mod.all_table_names())
    for name, block in ddl.items():
        if name.endswith("__indexes"):
            continue
        assert str(block).lstrip().upper().startswith("CREATE TABLE"), name
        assert str(block).rstrip().endswith("STRICT;"), name
        assert name.split("__")[0] in str(block), name


def test_index_coverage_is_complete(mod: ModuleType, ddl_text: str) -> None:
    total = len(re.findall(r"(?m)^CREATE (?:UNIQUE )?INDEX", ddl_text))
    ddl = mod.slice_tables(mod.all_table_names())
    captured = sum(len(v) for k, v in ddl.items() if k.endswith("__indexes"))
    assert captured == total, "索引语句必须被全部归到所属表，否则迁移比对会漏索引"


def test_unknown_table_is_not_found(mod: ModuleType) -> None:
    ddl = mod.slice_tables(["no_such_table"])
    assert ddl["no_such_table"] == "NOT_FOUND"


def test_operations_slice_resolves(mod: ModuleType) -> None:
    ops = mod.slice_ops(["exchangeSession", "getHealth", "listWorkspaces"], 2)
    assert all(v != "NOT_FOUND" for v in ops.values())
    assert ops["getHealth"]["method"] in {"GET"}
    assert str(ops["getHealth"]["path"]).startswith("/")


def test_acceptance_rows_are_verbatim(mod: ModuleType) -> None:
    rows = mod.slice_ac({"AC-001", "AC-034", "AC-035"})
    assert set(rows) == {"AC-001", "AC-034", "AC-035"}
    for cells in rows.values():
        assert len(cells) >= 4, "验收行必须是原表行切片，不得转述"
