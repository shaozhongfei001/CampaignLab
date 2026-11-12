"""D-009 回归：state.json 的缺陷/CR 账本必须与磁盘双向一致，且结构假设被显式钉住。

背景：编排器曾用 `if isinstance(st.get("defects"), dict): st["defects"]["D-006"] = {...}` 写账本，
而 `defects` 实际是 `list[dict]`，守卫为假导致整段**静默跳过**——D-006/D-007/D-008 与 CR-002
只存在于 .md 文件与提交信息里，账本查不到。静默跳过在无人值守长程里比崩溃更危险。

钉住的不变量：
1. 结构假设：defects / change_requests 必须是 list[dict] 且每条含非空 id；
2. 账本 -> 磁盘：每条 defect 的 id 必须有对应 orchestrator/defects/<id>.md；
3. 磁盘 -> 账本：每个 D-*.md 都必须在账本里有对应条目（本缺陷的形态）；
4. 分母断言：id 不得重复、D-* 编号必须连续无缺号；
5. 字段完整性：severity 与 status 必填，status 取值受限。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / "orchestrator" / "state.json"
DEFECT_DIR = REPO / "orchestrator" / "defects"
ALLOWED_STATUS = {"OPEN", "FIXED_PENDING_Q", "CLOSED", "WONT_FIX"}


@pytest.fixture(scope="module")
def state() -> dict[str, Any]:
    if not STATE.exists():
        pytest.fail(f"denominator=0：找不到 {STATE}，无法校验账本", pytrace=False)
    raw: Any = json.loads(STATE.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), f"state.json 顶层必须是对象；实测 {type(raw).__name__}"
    return raw


def _assert_list_of_dicts_with_id(value: object, name: str) -> list[dict[str, Any]]:
    assert isinstance(value, list), (
        f"state.json 的 {name} 必须是 list[dict]（D-009 的根因就是把它当成 dict 写，"
        f"isinstance 守卫静默跳过）；实测类型 {type(value).__name__}"
    )
    for entry in value:
        assert isinstance(entry, dict), f"{name} 的条目必须是 dict：{entry!r}"
        assert isinstance(entry.get("id"), str) and entry["id"].strip(), (
            f"{name} 条目缺 id：{entry!r}"
        )
    return value


def test_ledger_structure_is_list_of_dicts_with_id(state: dict[str, Any]) -> None:
    _assert_list_of_dicts_with_id(state.get("defects"), "defects")
    _assert_list_of_dicts_with_id(state.get("change_requests"), "change_requests")


def test_defect_ids_are_unique_and_contiguous(state: dict[str, Any]) -> None:
    entries = _assert_list_of_dicts_with_id(state.get("defects"), "defects")
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids)), f"defects 存在重复 id：{ids}"
    nums = []
    for i in ids:
        m = re.fullmatch(r"D-(\d{3})", i)
        assert m is not None, f"defect id 不符合 D-NNN 形态：{i}"
        nums.append(int(m.group(1)))
    assert nums == list(range(1, len(nums) + 1)), (
        f"D-* 编号必须从 D-001 连续无缺号（分母断言）；实测 {sorted(nums)}"
    )


def test_every_ledger_defect_has_md_on_disk(state: dict[str, Any]) -> None:
    entries = _assert_list_of_dicts_with_id(state.get("defects"), "defects")
    if not entries:
        pytest.fail("denominator=0：账本里没有任何缺陷条目", pytrace=False)
    missing = [e["id"] for e in entries if not (DEFECT_DIR / f"{e['id']}.md").exists()]
    assert missing == [], f"账本引用了磁盘上不存在的缺陷单（悬空引用，手册 15.3）：{missing}"


def test_every_md_on_disk_has_ledger_entry(state: dict[str, Any]) -> None:
    entries = _assert_list_of_dicts_with_id(state.get("defects"), "defects")
    ledger = {e["id"] for e in entries}
    on_disk = sorted(p.stem for p in DEFECT_DIR.glob("D-*.md"))
    if not on_disk:
        pytest.fail(f"denominator=0：{DEFECT_DIR} 下没有任何 D-*.md", pytrace=False)
    orphan = [d for d in on_disk if d not in ledger]
    assert orphan == [], (
        f"磁盘上有缺陷单但账本查不到（D-009 的形态：新实例按账本恢复会漏掉它们）：{orphan}"
    )


def test_defect_entries_have_severity_and_valid_status(state: dict[str, Any]) -> None:
    entries = _assert_list_of_dicts_with_id(state.get("defects"), "defects")
    bad = []
    for e in entries:
        if not e.get("severity") or e.get("status") not in ALLOWED_STATUS:
            bad.append((e["id"], e.get("severity"), e.get("status")))
    assert bad == [], f"缺陷条目缺 severity 或 status 非法（允许 {sorted(ALLOWED_STATUS)}）：{bad}"


def test_change_request_ids_are_unique(state: dict[str, Any]) -> None:
    entries = _assert_list_of_dicts_with_id(state.get("change_requests"), "change_requests")
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids)), f"change_requests 存在重复 id：{ids}"
    for e in entries:
        ref = e.get("file")
        if ref:
            assert (REPO / ref).exists(), f"CR 账本引用了不存在的文件：{e['id']} -> {ref}"
