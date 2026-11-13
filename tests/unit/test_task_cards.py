"""D-016 回归：state.json 的任务清单与磁盘任务卡必须双向对账，且可派单的卡必含派单必需段落。

背景：Q-VERIFY-M0-01 的 F 项发现 state.json 有 29 个任务与 11 波计划，而 orchestrator/tasks/
下只有 4 张卡（M0-01/M0-02/M0-03/M0-P01），wave2+ 的 25 张卡从未撰写。手册 15.5 规定
「无拆解表不得 spawn」，故这 25 个任务（其中 14 个在关键路径上）在补卡前一律不可派单。

钉住的不变量：
1. 任务总数分母固定为 29，变动即红（须同步改 waves 与 acceptance 分母并说明理由）；
2. state.json 的每个任务要么有对应 <id>.md，要么在 KNOWN_MISSING 里显式登记；
3. KNOWN_MISSING 必须单调收敛：卡片补齐后不移除登记即红（防缺口被遗忘）；
4. 磁盘上不得有 state.json 不认识的任务卡（孤儿）；
5. 非历史卡必含 scope_allow / scope_deny / outputs / 子任务档位表。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / "orchestrator" / "state.json"
CARD_DIR = REPO / "orchestrator" / "tasks"

TASK_TOTAL_DENOMINATOR = 29

# D-016 登记时的已知缺口（25 张，其中 14 张 critical=true）。补齐一张即须从此处删掉一个 id。
KNOWN_MISSING: frozenset[str] = frozenset(
    {
        "M3-P02",
        "M5-03",
        "M5-P01",
    }
)

# 早于手册 15.5「子任务档位表」要求交付/执行的历史卡，不追溯补写。
LEGACY_CARDS: frozenset[str] = frozenset({"M0-01", "M0-P01"})

REQUIRED_SECTIONS: tuple[str, ...] = ("scope_allow", "scope_deny", "outputs", "子任务档位表")


def _tasks() -> dict[str, Any]:
    raw: Any = json.loads(STATE.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), f"state.json 顶层必须是对象；实测 {type(raw).__name__}"
    tasks: Any = raw.get("tasks")
    assert isinstance(tasks, dict), f"state.json.tasks 必须是 dict；实测 {type(tasks).__name__}"
    return tasks


def _cards_on_disk() -> set[str]:
    return {p.stem for p in CARD_DIR.glob("*.md")}


def test_task_total_denominator_is_pinned() -> None:
    tasks = _tasks()
    assert len(tasks) == TASK_TOTAL_DENOMINATOR, (
        f"任务总数分母变动：实测 {len(tasks)}，登记值 {TASK_TOTAL_DENOMINATOR}；"
        "若确属规划变更，必须同步改本文件、waves 与 acceptance 分母并说明理由"
    )


def test_missing_cards_are_exactly_the_registered_gap() -> None:
    missing = set(_tasks()) - _cards_on_disk()
    unregistered = missing - set(KNOWN_MISSING)
    assert not unregistered, f"出现未登记的任务卡缺口（D-016 形态）：{sorted(unregistered)}"
    recovered = set(KNOWN_MISSING) - missing
    assert not recovered, (
        f"这些任务卡已补齐，必须从 KNOWN_MISSING 移除以让缺口单调收敛：{sorted(recovered)}"
    )


def test_known_missing_denominator_matches_registered_gap() -> None:
    missing = set(_tasks()) - _cards_on_disk()
    assert len(missing) == len(KNOWN_MISSING), (
        f"缺口分母不符：实测 {len(missing)}，登记 {len(KNOWN_MISSING)}"
    )


def test_no_orphan_card_on_disk() -> None:
    orphan = _cards_on_disk() - set(_tasks())
    assert not orphan, f"磁盘上有 state.json 不认识的任务卡：{sorted(orphan)}"


def test_dispatchable_cards_have_required_sections() -> None:
    bad: list[tuple[str, list[str]]] = []
    for card in sorted(_cards_on_disk()):
        if card in LEGACY_CARDS:
            continue
        text = (CARD_DIR / f"{card}.md").read_text(encoding="utf-8")
        lack = [s for s in REQUIRED_SECTIONS if s not in text]
        if lack:
            bad.append((card, lack))
    assert not bad, f"任务卡缺派单必需段落（手册 15.5：无拆解表不得 spawn）：{bad}"
