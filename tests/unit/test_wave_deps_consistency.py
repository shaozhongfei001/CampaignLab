"""D-026 回归：waves 的 serial 次序必须由 tasks[*].deps 表达。

并钉住 deps / acs / wave 覆盖三类台账不变量。

背景：D-016 批次 4 的 T lane（Planck / qwen3.8-flash）撰写 M5-01.md 时上报 U-4——
`waves[8]` 是 `mode=serial`、次序 `M4-P01 -> M5-01`，而 `tasks["M5-01"].deps`
只有 `["M4-03"]`。派单器按手册 6.2 只读 deps 判「依赖齐备」，就会把两者当可并行放行，
直接违反 serial 约束。编排器独立复核实测成立，并普查出同类形态共 2 处（另一处是 wave0 的
`M0-01 -> M0-P01`，两任务均已交付、wave0 已闭合，按「不改写历史」登记为显式豁免集）；
同时普查发现 `tasks["M5-02"].acs` 为 `[]`，而该卡是「独立 QA 全量走查（47 条 AC）」、
`gates[0]` 又写「35 条」——AC 分母口径在台账里不自洽。

钉住的不变量：
1. serial 波的相邻次序必须由后者的 deps 表达（豁免集之外，违反即红）；
2. 豁免集必须精确等于登记值，且其中每个任务的状态仍属已交付态（防豁免被当通行证）；
3. deps 不得悬空（引用的任务必须在 tasks 里）；
4. deps 不得成环（Kahn 全排序必须覆盖全部任务）；
5. 11 个波必须恰好覆盖 29 个任务，每任务归属唯一一波，且不得收录 tasks 不认识的任务；
6. tasks[*].acs 必须是 acceptance.primary_owner 键集的子集；
7. 全部 AC 必须被至少一个任务的 acs 认领（AC -> 任务方向的对账）；
8. 全量走查卡 M5-02 的 acs 必须等于 AC 全集（本缺陷形态 (b) 的复发防线）。
"""

from __future__ import annotations

import itertools
import json
from collections import deque
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / "orchestrator" / "state.json"

TASK_TOTAL_DENOMINATOR = 29
WAVE_TOTAL_DENOMINATOR = 11
FULL_SWEEP_TASK = "M5-02"
DELIVERED_STATUS: frozenset[str] = frozenset({"DONE", "PASS", "PASS_WITH_TODO"})
# wave0 的 M0-01 -> M0-P01：两任务均已交付、wave0 已闭合，追溯改 deps 属改写历史，
# 且不改变任何派单行为，故登记为显式豁免（豁免集精确性另由一条断言钉住）。
SERIAL_ORDER_EXEMPT: frozenset[tuple[str, str]] = frozenset({("M0-01", "M0-P01")})


def _state() -> dict[str, Any]:
    raw: Any = json.loads(STATE.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), f"state.json 顶层必须是对象；实测 {type(raw).__name__}"
    return raw


def _tasks(state: dict[str, Any]) -> dict[str, Any]:
    tasks: Any = state.get("tasks")
    assert isinstance(tasks, dict), f"state.json.tasks 必须是 dict；实测 {type(tasks).__name__}"
    return tasks


def _waves(state: dict[str, Any]) -> list[dict[str, Any]]:
    waves: Any = state.get("waves")
    assert isinstance(waves, list) and waves, (
        f"state.json.waves 必须是非空 list；实测 {type(waves).__name__}"
    )
    return waves


def _wave_no(wave: dict[str, Any]) -> int:
    no: Any = wave.get("wave")
    assert isinstance(no, int), f"waves 条目缺整数 wave 号：{wave!r}"
    return no


def _wave_task_ids(wave: dict[str, Any]) -> list[str]:
    """waves 有两种形态：{"tasks": [...]} 与 {"lanes": {"L1": [...]}}，都要展开。"""
    ids: list[str] = list(wave.get("tasks") or [])
    lanes = wave.get("lanes")
    if isinstance(lanes, dict):
        for lane in lanes.values():
            ids += list(lane)
    return ids


def _deps_of(tasks: dict[str, Any], tid: str) -> list[str]:
    deps = tasks.get(tid, {}).get("deps") or []
    assert isinstance(deps, list), f"tasks[{tid}].deps 必须是 list；实测 {type(deps).__name__}"
    return list(deps)


def test_serial_wave_order_is_expressed_by_deps() -> None:
    state = _state()
    tasks = _tasks(state)
    bad: list[tuple[int, str, str, list[str]]] = []
    for wave in _waves(state):
        if wave.get("mode") != "serial":
            continue
        ids = _wave_task_ids(wave)
        for prev, nxt in itertools.pairwise(ids):
            if (prev, nxt) in SERIAL_ORDER_EXEMPT:
                continue
            if prev not in _deps_of(tasks, nxt):
                bad.append((_wave_no(wave), prev, nxt, _deps_of(tasks, nxt)))
    assert not bad, (
        "serial 波的次序未被 deps 表达，派单器只读 deps 会并行放行（D-026 形态 a）："
        f"{bad}；修法＝把前者补进后者的 deps，或按 SERIAL_ORDER_EXEMPT 登记豁免并说明理由"
    )


def test_serial_order_exempt_set_is_exact_and_still_delivered() -> None:
    """豁免不得变成通行证：豁免对必须真实存在于某个 serial 波，且两任务均已交付。"""
    state = _state()
    tasks = _tasks(state)
    serial_pairs: set[tuple[str, str]] = set()
    for wave in _waves(state):
        if wave.get("mode") != "serial":
            continue
        serial_pairs.update(itertools.pairwise(_wave_task_ids(wave)))
    stale = sorted(SERIAL_ORDER_EXEMPT - serial_pairs)
    assert not stale, (
        f"豁免集里的对在 serial 波中已不存在（豁免过时，必须移除以保持单调收敛）：{stale}"
    )
    not_delivered: list[tuple[str, str, Any]] = []
    for a, b in sorted(SERIAL_ORDER_EXEMPT):
        for tid in (a, b):
            st = tasks.get(tid, {}).get("status")
            if st not in DELIVERED_STATUS:
                not_delivered.append((a, b, st))
    assert not not_delivered, (
        f"豁免的前提是两任务均已交付；实测状态回退或未完成：{not_delivered}"
        f"（允许状态 {sorted(DELIVERED_STATUS)}）"
    )


def test_deps_are_not_dangling() -> None:
    tasks = _tasks(_state())
    dangling = {t: [d for d in _deps_of(tasks, t) if d not in tasks] for t in tasks}
    dangling = {k: v for k, v in dangling.items() if v}
    assert not dangling, f"deps 引用了 state.json.tasks 里不存在的任务（悬空依赖）：{dangling}"


def test_deps_are_acyclic() -> None:
    tasks = _tasks(_state())
    indeg = {t: 0 for t in tasks}
    adj: dict[str, list[str]] = {t: [] for t in tasks}
    for t in tasks:
        for d in _deps_of(tasks, t):
            if d in tasks:
                adj[d].append(t)
                indeg[t] += 1
    q = deque(t for t, n in indeg.items() if n == 0)
    order: list[str] = []
    while q:
        n = q.popleft()
        order.append(n)
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    assert len(order) == len(tasks), (
        f"deps 存在环，拓扑排序只覆盖 {len(order)}/{len(tasks)}；未覆盖："
        f"{sorted(set(tasks) - set(order))}"
    )


def test_waves_cover_every_task_exactly_once() -> None:
    state = _state()
    tasks = _tasks(state)
    waves = _waves(state)
    assert len(waves) == WAVE_TOTAL_DENOMINATOR, (
        f"波数分母变动：实测 {len(waves)}，登记 {WAVE_TOTAL_DENOMINATOR}；"
        "若确属规划变更须同步改本文件并说明理由"
    )
    seen: dict[str, list[int]] = {}
    for wave in waves:
        for tid in _wave_task_ids(wave):
            seen.setdefault(tid, []).append(_wave_no(wave))
    dup = {k: v for k, v in seen.items() if len(v) > 1}
    assert not dup, f"这些任务被多个波收录（归属不唯一，派单器无法定序）：{dup}"
    assert set(seen) == set(tasks), (
        f"波计划与任务清单不一致：未被任何波收录 {sorted(set(tasks) - set(seen))}；"
        f"波收录但 tasks 无此任务 {sorted(set(seen) - set(tasks))}"
    )
    assert len(tasks) == TASK_TOTAL_DENOMINATOR, (
        f"任务总数分母变动：实测 {len(tasks)}，登记 {TASK_TOTAL_DENOMINATOR}"
    )


def _registry(state: dict[str, Any]) -> set[str]:
    acc: Any = state.get("acceptance", {})
    po: Any = acc.get("primary_owner")
    assert isinstance(po, dict) and po, "acceptance.primary_owner 必须是非空 dict（AC 权威注册表）"
    return set(po.keys())


def test_acs_are_subset_of_acceptance_registry() -> None:
    state = _state()
    reg = _registry(state)
    bad: list[tuple[str, list[str]]] = []
    for t, v in _tasks(state).items():
        acs = v.get("acs") or []
        assert isinstance(acs, list), f"tasks[{t}].acs 必须是 list；实测 {type(acs).__name__}"
        unknown = sorted(set(acs) - reg)
        if unknown:
            bad.append((t, unknown))
    assert not bad, f"这些任务的 acs 引用了注册表之外的 AC 编号（D-011：AC 编号只引原文）：{bad}"


def test_every_acceptance_item_is_claimed_by_some_task() -> None:
    state = _state()
    reg = _registry(state)
    claimed: set[str] = set()
    for v in _tasks(state).values():
        claimed |= set(v.get("acs") or [])
    assert not (reg - claimed), (
        f"这些 AC 没有任何任务在 acs 里认领（验收分母 {len(reg)} 会出现无主项）："
        f"{sorted(reg - claimed)}"
    )


def test_full_sweep_card_claims_all_47() -> None:
    """D-026 形态 (b)：全量走查卡的 acs 必须是全集，否则 AC <-> 任务 对账失效。"""
    state = _state()
    reg = _registry(state)
    acs = set(_tasks(state).get(FULL_SWEEP_TASK, {}).get("acs") or [])
    assert acs == reg, (
        f"{FULL_SWEEP_TASK} 是独立 QA 全量走查卡，acs 必须等于注册表全集"
        f"（{len(reg)} 条）；实测 {len(acs)} 条，缺失 {sorted(reg - acs)}，"
        f"越界 {sorted(acs - reg)}"
    )
