"""M2-01/S5 · design §11.6 A：活动／规则版本状态机与不可变性（纯领域层，禁 HTTP／DB）。

函数名同时满足卡片 gate 的 ``-k immutable`` 与派单文 V7 的 ``state_machine`` 字面量。
断言分母全部回源 ``src/campaignlab/domain/activity/states.py`` 的注册表实测值（§4.2）。
"""

from __future__ import annotations

import typing
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from campaignlab.domain.activity import states
from campaignlab.domain.errors import StateConflict

#: §4.2 实测冻结：``(id, sources, target)`` 逐行三元组，注册序即表序。
ACTIVITY_ROWS = (
    ("A1", (), "OPEN"),
    ("A2", ("OPEN",), "ARCHIVED"),
    ("A3", ("OPEN",), "OPEN"),
)
RULE_ROWS = (
    ("R1", (), "DRAFT"),
    ("R2", ("DRAFT",), "DRAFT"),
    ("R3", ("DRAFT",), "CONFIRMED"),
    ("R4", ("CONFIRMED",), "DRAFT"),
)
#: 每行 ``trigger`` 文案必须挂在的 op 前缀（匹配逻辑就是 ``row.trigger.startswith(trigger)``）。
ACTIVITY_TRIGGER_OPS = {"A1": "createActivity", "A2": "updateActivity", "A3": "updateActivity"}
RULE_TRIGGER_OPS = {
    "R1": "createRule",
    "R2": "updateRule",
    "R3": "confirmRule",
    "R4": "createRule",
}


def _rows_snapshot(rows: Sequence[Any]) -> tuple[tuple[str, tuple[str, ...], str], ...]:
    out = []
    for row in rows:
        item = (str(row.id), tuple(row.sources), str(row.target))
        out.append(item)
    return tuple(out)


def _serialize(rows: tuple[tuple[str, tuple[str, ...], str], ...]) -> str:
    return "".join(f"{rid}|{','.join(sources)}|{target}\n" for rid, sources, target in rows)


def _parse_table(text: str) -> tuple[tuple[str, tuple[str, ...], str], ...]:
    out = []
    for line in text.splitlines():
        rid, sources, target = line.split("|")
        parsed_sources = tuple() if sources == "" else tuple(sources.split(","))
        out.append((rid, parsed_sources, target))
    return tuple(out)


def _table_diff(
    registered: tuple[tuple[str, tuple[str, ...], str], ...],
    candidate: tuple[tuple[str, tuple[str, ...], str], ...],
) -> list[str]:
    """把「候选表 vs 注册表」的缺失／多出／错位列出来；空表＝两面逐行相符。"""
    out = [f"missing:{row}" for row in registered if row not in candidate]
    out += [f"extra:{row}" for row in candidate if row not in registered]
    if not out and registered != candidate:
        out.append("order-drift")
    return out


def test_activity_state_machine_a1_a2_a3_are_exactly_the_registered_rows() -> None:
    rows = states.ACTIVITY_TRANSITIONS
    assert len(rows) == 3 > 0
    assert tuple(row.id for row in rows) == ("A1", "A2", "A3")
    assert _rows_snapshot(rows) == ACTIVITY_ROWS
    assert typing.get_args(states.ActivityTransitionId) == ("A1", "A2", "A3")
    for row in rows:
        assert row.trigger.startswith(ACTIVITY_TRIGGER_OPS[row.id])


def test_rule_state_machine_r1_r4_are_exactly_the_registered_rows() -> None:
    rows = states.RULE_TRANSITIONS
    assert len(rows) == 4 > 0
    assert tuple(row.id for row in rows) == ("R1", "R2", "R3", "R4")
    assert _rows_snapshot(rows) == RULE_ROWS
    assert typing.get_args(states.RuleTransitionId) == ("R1", "R2", "R3", "R4")
    assert {row.id: row.creates_new_row for row in rows} == {
        "R1": False,
        "R2": False,
        "R3": False,
        "R4": True,
    }
    for row in rows:
        assert row.trigger.startswith(RULE_TRIGGER_OPS[row.id])


def test_archived_activity_is_immutable_and_rejects_every_mutation() -> None:
    assert states.is_activity_terminal("ARCHIVED") is True
    assert states.is_activity_terminal("OPEN") is False
    assert "ARCHIVED" not in states.ACTIVITY_STATES or states.ACTIVITY_STATES == (
        "OPEN",
        "ARCHIVED",
    )
    assert all("ARCHIVED" not in row.sources for row in states.ACTIVITY_TRANSITIONS)
    assert states.ACTIVITY_ISSUE_CODES == ("ACTIVITY_ARCHIVED",)
    for target in states.ACTIVITY_STATES:
        for trigger in ("updateActivity", "createActivity", "confirmRule"):
            with pytest.raises(StateConflict) as excinfo:
                states.assert_activity_transition_allowed("ARCHIVED", target, trigger=trigger)
            assert excinfo.value.code == "STATE_CONFLICT"
    with pytest.raises(StateConflict):
        states.assert_activity_transition_allowed("ARCHIVED", "OPEN", trigger="updateActivity")


def test_confirmed_rule_version_is_immutable_on_update() -> None:
    assert states.is_rule_terminal("CONFIRMED") is True
    with pytest.raises(StateConflict) as excinfo:
        states.assert_rule_transition_allowed("CONFIRMED", "CONFIRMED", trigger="updateRule")
    assert excinfo.value.code == "STATE_CONFLICT"
    with pytest.raises(StateConflict):
        states.assert_rule_transition_allowed("CONFIRMED", "DRAFT", trigger="updateRule")
    states.assert_rule_transition_allowed("DRAFT", "DRAFT", trigger="updateRule")


def test_confirmed_rule_version_is_immutable_on_reconfirm() -> None:
    with pytest.raises(StateConflict) as excinfo:
        states.assert_rule_transition_allowed("CONFIRMED", "CONFIRMED", trigger="confirmRule")
    assert excinfo.value.code == "STATE_CONFLICT"
    states.assert_rule_transition_allowed("DRAFT", "CONFIRMED", trigger="confirmRule")


def test_successor_draft_does_not_touch_the_confirmed_parent() -> None:
    states.assert_rule_transition_allowed("CONFIRMED", "DRAFT", trigger="createRule")
    successor = next(row for row in states.RULE_TRANSITIONS if row.id == "R4")
    assert successor.creates_new_row is True
    assert (successor.sources, successor.target) == (("CONFIRMED",), "DRAFT")
    assert all(row.creates_new_row is False for row in states.RULE_TRANSITIONS if row.id != "R4")


def test_transition_tables_have_teeth_positive_control(tmp_path: Path) -> None:
    """正向对照（PC-A 同族）：少一行／多一行的迁移表副本必须被对撞函数抓到。"""
    registered = _rows_snapshot(states.RULE_TRANSITIONS)
    assert registered == RULE_ROWS

    probe = tmp_path / "rule_table_short.txt"
    probe.write_text(_serialize(RULE_ROWS[:2] + RULE_ROWS[3:]), encoding="utf-8")
    dropped = _parse_table(probe.read_text(encoding="utf-8"))
    assert dropped != registered
    diff = _table_diff(registered, dropped)
    assert any("R3" in item and item.startswith("missing:") for item in diff)

    extra_probe = tmp_path / "rule_table_extra.txt"
    extra_probe.write_text(
        _serialize((*registered, ("R5", ("DRAFT",), "CONFIRMED"))), encoding="utf-8"
    )
    padded = _parse_table(extra_probe.read_text(encoding="utf-8"))
    extra_diff = _table_diff(registered, padded)
    assert any(item.startswith("extra:") and "R5" in item for item in extra_diff)

    assert _table_diff(registered, _parse_table(_serialize(registered))) == []
