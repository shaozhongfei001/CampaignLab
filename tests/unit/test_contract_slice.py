"""契约切片工具的回归护栏（D-001 修复后新增；D-004 / D-005 修复后扩充）。

D-001：slice_tables 的旧正则在找 "\n);"，而参考 DDL 的 28 张表一律以 ") STRICT;"
结尾，导致 --tables 静默返回 NOT_FOUND 且退出码为 0。
D-004：openapi / pages / DDL 全部只读 v1.0.0 不可变基线，且 spec_version 硬编码，
活契约升到 1.0.1 后切片会静默提供过期契约。
D-005：AC 正则不匹配 AC-MR-<n> 且不读月报追加清单，未命中还不报错，
月报任务的验收上下文会静默为空。

本文件把这些钉死：表数分母、解析完整性、索引覆盖、数据源必须是活契约、
spec_version 必须动态读取、47 条 AC 分母必须全可解析、未命中必须 rc=2 且不产出文件。

约定：必须从仓库根目录运行 pytest（contract_slice 以 cwd 相对路径为基准）。
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "contract_slice.py"
LIVE_OPENAPI = ROOT / "contracts" / "openapi.json"
BASE_OPENAPI = ROOT / "spec" / "CampaignLab-SDD-v1.0" / "contracts" / "openapi.json"
BASE_IDS = {f"AC-{i:03d}" for i in range(1, 36)}
MONTHLY_IDS = {f"AC-MR-{i:02d}" for i in range(1, 13)}


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    spec = importlib.util.spec_from_file_location("contract_slice", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ddl_text() -> str:
    return (ROOT / "spec/CampaignLab-SDD-v1.0/contracts/sqlite-v1.sql").read_text(encoding="utf-8")


def run_cli(*args: str, out: Path | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), *args]
    if out is not None:
        cmd += ["--out", str(out)]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


# ---------------------------------------------------------------- D-001 既有护栏


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


# ---------------------------------------------------------------- D-004 数据源


def test_live_contract_is_the_source(mod: ModuleType) -> None:
    live_dir, base_dir = str(mod.LIVE), str(mod.BASE)
    assert live_dir == "contracts"
    assert base_dir == "spec/CampaignLab-SDD-v1.0"
    for name in ("openapi.json", "pages.json", "sqlite-v1.sql"):
        assert (mod.LIVE / name).exists(), name


def test_spec_version_is_read_from_live_not_hardcoded(mod: ModuleType) -> None:
    live = json.loads(LIVE_OPENAPI.read_text(encoding="utf-8"))
    base = json.loads(BASE_OPENAPI.read_text(encoding="utf-8"))
    assert live["info"]["version"] != base["info"]["version"], (
        "两版本相同则本测试无法证明数据源已切换，请改用其他判别点"
    )
    assert mod.live_spec_version() == live["info"]["version"]


def test_get_review_slice_exposes_monthly_review_from_live(mod: ModuleType) -> None:
    blob = json.dumps(mod.slice_ops(["getReview"], 2)["getReview"], ensure_ascii=False)
    assert "monthly_review" in blob, "活契约 Review.monthly_review 未进入切片"
    assert "MonthlyReview" in blob, "月报 schema 未被展开"


def test_baseline_source_would_miss_monthly_review(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """反证：把数据源换回基线（即修复前的行为），月报字段就消失。"""
    monkeypatch.setattr(mod, "LIVE", mod.BASE / "contracts")
    assert mod.live_spec_version() == "1.0.0"
    blob = json.dumps(mod.slice_ops(["getReview"], 2)["getReview"], ensure_ascii=False)
    assert "monthly_review" not in blob
    assert "MonthlyReview" not in blob


def test_source_block_points_at_live_openapi(mod: ModuleType) -> None:
    src = mod.source_block()
    data = LIVE_OPENAPI.read_bytes()
    assert str(src["live_contracts"]) == str(Path("contracts"))
    assert src["openapi"]["sha16"] == sha256(data).hexdigest()[:16]
    assert src["openapi"]["bytes"] == len(data)
    assert str(src["readonly_originals"]) == str(mod.BASE)


# ---------------------------------------------------------------- D-005 验收分母


def test_all_47_acceptance_ids_resolve(mod: ModuleType) -> None:
    rows = mod.slice_ac(BASE_IDS | MONTHLY_IDS)
    assert set(rows) == BASE_IDS | MONTHLY_IDS
    assert len(rows) == 47, "验收分母必须是 35 + 12 = 47"


def test_monthly_rows_are_verbatim_with_golden_numbers(mod: ModuleType) -> None:
    rows = mod.slice_ac({"AC-MR-05", "AC-MR-08"})
    assert set(rows) == {"AC-MR-05", "AC-MR-08"}
    for cells in rows.values():
        assert len(cells) >= 4, "月报验收行必须是原表行切片，不得转述"
    assert "83.33%" in "|".join(rows["AC-MR-05"]), "AC-MR-05 原文应含分组等权成功覆盖率 83.33%"
    assert "79.31%" in "|".join(rows["AC-MR-08"]), "AC-MR-08 原文应含分行含重率 79.31%"


def test_monthly_ids_are_unreachable_without_delta_source(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """反证：不读月报追加清单（即修复前），AC-MR 一条也切不到。"""
    monkeypatch.setattr(mod, "ACCEPTANCE_SOURCES", (mod.BASE / "qa/ACCEPTANCE.md",))
    assert mod.slice_ac(MONTHLY_IDS) == {}
    assert len(mod.slice_ac(BASE_IDS)) == 35


# ------------------------------------------------------- 分母断言与静默失效防护


def test_missing_targets_flags_every_section(mod: ModuleType) -> None:
    bundle = {
        "operations": mod.slice_ops(["getHealth", "noSuchOp"], 2),
        "acceptance_rows": mod.slice_ac({"AC-001"}),
        "pages": mod.slice_pages({"UI-99"}),
        "ddl": mod.slice_tables(["workspaces", "no_such_table"]),
    }
    miss = mod.missing_targets(
        {
            "operations": ["getHealth", "noSuchOp"],
            "acceptance_rows": ["AC-001", "AC-MR-99"],
            "pages": ["UI-99"],
            "ddl": ["workspaces", "no_such_table"],
        },
        bundle,
    )
    assert miss == {
        "operations": ["noSuchOp"],
        "acceptance_rows": ["AC-MR-99"],
        "pages": ["UI-99"],
        "ddl": ["no_such_table"],
    }


def test_missing_targets_empty_when_all_hit(mod: ModuleType) -> None:
    bundle = {"operations": mod.slice_ops(["getHealth"], 2)}
    assert mod.missing_targets({"operations": ["getHealth"]}, bundle) == {}


def test_cli_unknown_op_exits_2_and_writes_nothing(tmp_path: Path) -> None:
    out = tmp_path / "slice.json"
    proc = run_cli("--ops", "noSuchOp", out=out)
    assert proc.returncode == 2, proc.stderr
    assert not out.exists(), "未命中时不得写出切片文件，避免坏上下文被派发"
    assert "noSuchOp" in proc.stderr


def test_cli_unknown_ac_exits_2(tmp_path: Path) -> None:
    proc = run_cli("--ac", "AC-MR-99", out=tmp_path / "s.json")
    assert proc.returncode == 2, proc.stderr
    assert "AC-MR-99" in proc.stderr


def test_cli_happy_path_stamps_live_version_and_monthly_ac(tmp_path: Path) -> None:
    out = tmp_path / "slice.json"
    proc = run_cli("--ops", "getHealth", "--ac", "AC-001,AC-MR-01", out=out)
    assert proc.returncode == 0, proc.stderr
    d = json.loads(out.read_text(encoding="utf-8"))
    live_version = json.loads(LIVE_OPENAPI.read_text(encoding="utf-8"))["info"]["version"]
    assert d["spec_version"] == live_version
    assert set(d["acceptance_rows"]) == {"AC-001", "AC-MR-01"}
    assert d["source"]["openapi"]["sha16"] == sha256(LIVE_OPENAPI.read_bytes()).hexdigest()[:16]


def test_cli_all_tables_still_finds_28(tmp_path: Path) -> None:
    out = tmp_path / "ddl.json"
    proc = run_cli("--all-tables", out=out)
    assert proc.returncode == 0, proc.stderr
    ddl = json.loads(out.read_text(encoding="utf-8"))["ddl"]
    tables = [k for k in ddl if not k.endswith("__indexes")]
    assert len(tables) == 28
    assert not [k for k, v in ddl.items() if v == "NOT_FOUND"]


# ---------------------------------------------------------------- D-020 截断守卫
#
# D-020：--depth 默认 2 时 depth==cap 的组件被写成 "TRUNCATED"，7 份已派发切片共 45 处
# 被截断（M0-02:1 / M0-03:1 / M0-04:7 / M3-01:8 / M3-02:8 / M3-03:11 / M4-01:9），
# 且被截断的正是 Problem / ObjectRef / Issue / Job 等核心 schema，迫使 lane 回读 443KB
# 活契约（M0-04/S1 因此超支 11k token）。以下用例把三件事钉死：默认深度足够、截断必被
# 登记、登记必致 rc=2 且不产出文件。其中「浅深度确实检出截断」一例是守卫的自证——
# 一条永不触发的守卫等于没有守卫，绿灯毫无意义。

# 已派发切片的 operationId 集合（取自各切片文件自身的 operations 段，非杜撰）
D020_OP_SETS: tuple[tuple[str, ...], ...] = (
    ("exchangeSession", "getSession", "getHealth", "listWorkspaces", "createWorkspace"),
    ("listJobs", "getJob", "cancelJob", "retryJob", "getHealth"),
    ("runReview", "getReview"),
    ("runDiagnosis", "getDiagnosis", "computeEstimate", "listThresholds", "createThreshold"),
    ("executeQuestion", "interpretQuestion", "getQuestion"),
    ("listReports", "createReport", "getReport", "signReport"),
)
D020_CORE_SCHEMAS = ("Problem", "Issue", "ObjectRef", "Job")


def _sentinels(node: object, hits: list[str], where: str = "") -> list[str]:
    """递归收集任何等于 TRUNCATED 哨兵的值，返回其 JSON 路径。"""
    if isinstance(node, dict):
        for k, v in node.items():
            if v == "TRUNCATED":
                hits.append(f"{where}/{k}")
            else:
                _sentinels(v, hits, f"{where}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _sentinels(v, hits, f"{where}[{i}]")
    return hits


def test_d020_default_depth_is_five(mod: ModuleType) -> None:
    assert mod.DEFAULT_DEPTH == 5, "默认深度必须是 5：实测 depth=6 与 5 产出字节数相同"
    assert mod.TRUNCATED_SENTINEL == "TRUNCATED"


@pytest.mark.parametrize("ops", D020_OP_SETS)
def test_d020_all_dispatched_op_sets_expand_without_truncation(
    mod: ModuleType, ops: tuple[str, ...]
) -> None:
    truncated: set[str] = set()
    out = mod.slice_ops(list(ops), mod.DEFAULT_DEPTH, truncated)
    assert truncated == set(), sorted(truncated)
    assert _sentinels(out, []) == []
    assert set(out) == set(ops)


def test_d020_core_schemas_are_real_objects_at_default_depth(mod: ModuleType) -> None:
    truncated: set[str] = set()
    out = mod.slice_ops(
        ["listJobs", "getJob", "cancelJob", "retryJob", "getHealth"], mod.DEFAULT_DEPTH, truncated
    )
    merged: dict[str, object] = {}
    for v in out.values():
        if isinstance(v, dict):
            merged.update(v.get("schemas") or {})
    for name in D020_CORE_SCHEMAS:
        assert name in merged, f"核心 schema {name} 未进入切片"
        assert isinstance(merged[name], dict), name


def test_d020_shallow_depth_does_register_truncation(mod: ModuleType) -> None:
    """守卫自证：depth=1 必须真的检出截断。"""
    truncated: set[str] = set()
    mod.slice_ops(["getJob"], 1, truncated)
    assert truncated, "depth=1 未检出任何截断，守卫已失效"


def test_d020_cli_shallow_depth_exits_2_and_writes_nothing(tmp_path: Path) -> None:
    out = tmp_path / "shallow.json"
    proc = run_cli("--ops", "getJob", "--depth", "1", out=out)
    assert proc.returncode == 2, proc.stderr
    assert not out.exists(), "截断时不得写出切片文件，避免坏上下文被派发"
    assert "D-020" in proc.stderr
    assert "truncated_schemas" in proc.stderr


def test_d020_cli_default_depth_emits_empty_truncated_schemas(tmp_path: Path) -> None:
    out = tmp_path / "deep.json"
    proc = run_cli("--ops", "getJob,listJobs", "--ac", "AC-029,AC-031", out=out)
    assert proc.returncode == 0, proc.stderr
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["truncated_schemas"] == []
    assert _sentinels(d, []) == []
    assert "truncated_schemas=[]" in proc.stderr
