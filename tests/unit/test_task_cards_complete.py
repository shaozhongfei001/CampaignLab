"""FU-33 守护（D-041 + D-042）：台账任务集 == 任务卡文件集（双向），且台账卡片三键 == 磁盘实测。

背景（两个缺陷、同一处盲区）：

1. D-041：`state.json -> tasks` 有 29 个任务键，而 `orchestrator/tasks/` 只有 26 张卡，
   缺口 M3-P02 / M5-P01 / M5-03 自 v1.0.1 补丁合入（M0-P01）起静默存活 10 轮派单。
   根因不是某一轮的疏忽，而是**缺一条全集对账守护**：既有 `test_task_cards.py` 按
   `KNOWN_MISSING` 白名单判缺口，白名单漏登记时缺口就无人照到。手册 §15.5「无拆解表
   不得 spawn」，故这种缺口会直接让 wave7/9/10 停摆（M5-P01、M5-03 在关键路径上）。
2. D-042：台账 `counts` 的卡片三键腐化为 `task_cards_on_disk=20 / known_missing_cards=9`，
   磁盘实测却是 26 / 3。恒等式 `20 + 9 == 29` **算术成立**，任何只做加法核对的复核都会
   放过它 —— 等式为真、代入值为假，是比「等式不平」更隐蔽的腐化形态。

钉住的不变量（只依赖文件字节，任何人可复跑）：

1. 双向相等：`tasks` 键集 == 卡文件名 stem 集；`missing`（有任务无卡）与 `orphan`
   （有卡无任务）各自独立断言、各自独立报错文本；
2. 分母写死：任务数与卡数都须等于 `TASK_TOTAL_DENOMINATOR`（手册 §15.4：守护必须自带
   分母，防 glob 扫空导致假绿）；
3. 台账三键逐键对账：`task_cards_on_disk` / `known_missing_cards` /
   `task_total_denominator` 须分别等于磁盘实测卡数、实测缺口数、29，**且**恒等式成立
   （只核恒等式必然放过 D-042，故两者都要）；
4. 正向对照：判定逻辑抽成可传 `card_dir` / `task_ids` / `counts` 的纯函数，用 `tmp_path`
   造假树与假台账，证明它们**能**分别报出 `orphan`、`missing` 与 D-042 的历史腐化值。

只用 `json` + `pathlib`：不 import 被测源码（避免副作用）、不用 `__subclasses__`、
不跑 `subprocess`。台账写入权归编排器，本守护只读、只判红。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / "orchestrator" / "state.json"
CARD_DIR = REPO / "orchestrator" / "tasks"

#: 冻结面写死分母（手册 §15.5 允许的「不得静默增减」语义）。
#: 任务总数变更须同批更新此分母并说明依据（并同步 waves 与 acceptance 分母）。
TASK_TOTAL_DENOMINATOR = 29

#: 台账卡片三键在 state.json 内的位置（D-042 的腐化面）。
COUNTS_PATH = ("resume", "self_check_gates_rc0", "counts")
KEY_CARDS = "task_cards_on_disk"
KEY_MISSING = "known_missing_cards"
KEY_TOTAL = "task_total_denominator"
IDENTITY_MARK = "恒等式"


def _load_json_object(path: Path) -> dict[str, Any]:
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), f"{path.name} 顶层必须是 JSON 对象；实测 {type(raw).__name__}"
    return raw


def _registered_task_ids() -> frozenset[str]:
    """台账 `tasks` 的键集，即权威任务全集。"""
    tasks: Any = _load_json_object(STATE).get("tasks")
    assert isinstance(tasks, dict), f"state.json.tasks 必须是 dict；实测 {type(tasks).__name__}"
    return frozenset(str(key) for key in tasks)


def _ledger_counts() -> dict[str, Any]:
    """台账 `resume.self_check_gates_rc0.counts`，即 D-042 三键所在处。"""
    node: Any = _load_json_object(STATE)
    walked: list[str] = []
    for key in COUNTS_PATH:
        walked.append(key)
        dotted = "state.json 的 " + ".".join(walked)
        assert isinstance(node, dict), dotted + " 必须是对象；实测 " + type(node).__name__
        node = node.get(key)
    dotted = "state.json 的 " + ".".join(walked)
    assert isinstance(node, dict), dotted + " 必须是对象；实测 " + type(node).__name__
    counts: dict[str, Any] = node
    return counts


def card_ids_on_disk(card_dir: Path) -> frozenset[str]:
    """实测 `card_dir` 下的任务卡 id 集（文件名 stem）。

    目录不存在时返回空集：这**不是**静默放过，调用方的分母断言会立刻照到。
    """
    if not card_dir.is_dir():
        return frozenset()
    return frozenset(path.stem for path in card_dir.glob("*.md"))


def reconcile(card_dir: Path, task_ids: frozenset[str]) -> tuple[frozenset[str], frozenset[str]]:
    """纯函数：返回 `(missing, orphan)`。

    - `missing`：台账有任务、磁盘无卡（D-041 形态，违反手册 §15.5「无拆解表不得 spawn」）；
    - `orphan`：磁盘有卡、台账无任务（无主卡，waves / deps / counts 都照不到它）。

    实树用例与 `tmp_path` 正向对照**共用**本函数；禁把判定逻辑写死在用例里，否则对照
    只是在验证用例自己，照不到真实缺口（手册 §15.4 / A159）。
    """
    on_disk = card_ids_on_disk(card_dir)
    return task_ids - on_disk, on_disk - task_ids


def _ledger_int(counts: dict[str, Any], key: str) -> int:
    """取台账整数键；缺键或非整数一律抛断言，禁静默当成 0（A159）。"""
    value: Any = counts.get(key)
    is_int = isinstance(value, int) and not isinstance(value, bool)
    assert is_int, f"counts.{key} 必须是整数；实测 {type(value).__name__}={value!r}"
    return int(value)


def ledger_violations(
    counts: dict[str, Any], measured_cards: int, measured_missing: int
) -> list[str]:
    """纯函数：台账卡片三键 vs 磁盘实测，返回违规描述（空列表 == 对账通过）。

    刻意**不只**核恒等式：D-042 的腐化形态是「等式为真、代入值为假」
    （`20 + 9 == 29` 成立，而磁盘真值是 `26 + 3`），只核恒等式必然放过。
    """
    cards = _ledger_int(counts, KEY_CARDS)
    missing = _ledger_int(counts, KEY_MISSING)
    total = _ledger_int(counts, KEY_TOTAL)
    bad: list[str] = []
    if cards != measured_cards:
        bad.append(
            f"{KEY_CARDS}={cards} 与磁盘实测卡数 {measured_cards} 不符"
            "（D-042：卡片变更未与本键同批刷新）"
        )
    if missing != measured_missing:
        bad.append(f"{KEY_MISSING}={missing} 与实测缺口数 {measured_missing} 不符")
    if total != TASK_TOTAL_DENOMINATOR:
        bad.append(f"{KEY_TOTAL}={total} 与冻结分母 {TASK_TOTAL_DENOMINATOR} 不符")
    if cards + missing != total:
        bad.append(
            f"{IDENTITY_MARK}不成立：{KEY_CARDS}({cards}) + {KEY_MISSING}({missing})"
            f" != {KEY_TOTAL}({total})"
        )
    return bad


def test_no_registered_task_lacks_a_card() -> None:
    """方向一：台账有任务，磁盘必须有卡（D-041 的原始缺口方向）。"""
    missing, _ = reconcile(CARD_DIR, _registered_task_ids())
    assert not missing, (
        f"台账有任务、磁盘无卡（D-041 形态）：{sorted(missing)}。手册 §15.5「无拆解表"
        "不得 spawn」，这些任务在补卡前一律不可派单"
    )


def test_no_card_lacks_a_registered_task() -> None:
    """方向二：磁盘有卡，台账必须认识它（无主卡会让 waves / deps / counts 全瞎）。"""
    _, orphan = reconcile(CARD_DIR, _registered_task_ids())
    assert not orphan, (
        f"磁盘有卡、台账无任务（孤儿卡）：{sorted(orphan)}。孤儿卡不进 waves、不被 deps"
        "引用、也不被 counts 计数，必须删卡或补登台账（台账写入权归编排器）"
    )


def test_task_and_card_denominators_are_pinned() -> None:
    """分母写死：防 glob 扫空或台账被清空导致「双向都为空」的假绿（手册 §15.4）。"""
    tasks = _registered_task_ids()
    cards = card_ids_on_disk(CARD_DIR)
    note = "任务总数变更须同批更新此分母并说明依据（并同步 waves 与 acceptance 分母）"
    assert len(tasks) == TASK_TOTAL_DENOMINATOR, (
        f"台账任务数分母变动：实测 {len(tasks)}，冻结值 {TASK_TOTAL_DENOMINATOR}；{note}"
    )
    assert len(cards) == TASK_TOTAL_DENOMINATOR, (
        f"磁盘任务卡数分母变动：实测 {len(cards)}，冻结值 {TASK_TOTAL_DENOMINATOR}；{note}"
    )


def test_ledger_card_counts_match_disk_measurement() -> None:
    """D-042：台账卡片三键必须与磁盘实测逐键相符，禁只核恒等式。"""
    cards = card_ids_on_disk(CARD_DIR)
    missing, _ = reconcile(CARD_DIR, _registered_task_ids())
    bad = ledger_violations(_ledger_counts(), len(cards), len(missing))
    assert not bad, (
        "台账 counts 的卡片三键已腐化（D-042 形态）：卡片变更必须与 counts 刷新在**同一次"
        "提交**内完成（A101 rule_counts_same_commit；R12-2：按语义类别而非文件后缀判断该刷"
        f"哪些键）。违规项：{bad}"
    )


def _fake_card_tree(tmp_path: Path, card_ids: tuple[str, ...]) -> Path:
    """在 `tmp_path` 下造一棵假的 `orchestrator/tasks/` 树，返回该目录。"""
    card_dir = tmp_path / "orchestrator" / "tasks"
    card_dir.mkdir(parents=True)
    for card_id in card_ids:
        (card_dir / f"{card_id}.md").write_text(f"# {card_id}\n", encoding="utf-8")
    return card_dir


def test_positive_control_extra_card_is_reported_as_orphan(tmp_path: Path) -> None:
    """正向对照（多卡形态）：判定函数必须能报出 `orphan`。"""
    registered = frozenset({"M0-01", "M0-02"})
    card_dir = _fake_card_tree(tmp_path, ("M0-01", "M0-02", "M9-99"))
    missing, orphan = reconcile(card_dir, registered)
    assert orphan == frozenset({"M9-99"}), (
        f"正向对照失效：多卡形态未报出 orphan，实测 {sorted(orphan)}"
    )
    assert not missing, f"正向对照应只报 orphan，却同时报了 missing：{sorted(missing)}"


def test_positive_control_missing_card_is_reported_as_missing(tmp_path: Path) -> None:
    """正向对照（少卡形态）：判定函数必须能报出 `missing`。"""
    registered = frozenset({"M0-01", "M0-02", "M0-03"})
    card_dir = _fake_card_tree(tmp_path, ("M0-01",))
    missing, orphan = reconcile(card_dir, registered)
    assert missing == frozenset({"M0-02", "M0-03"}), (
        f"正向对照失效：少卡形态未报出 missing，实测 {sorted(missing)}"
    )
    assert not orphan, f"正向对照应只报 missing，却同时报了 orphan：{sorted(orphan)}"


def test_positive_control_both_directions_at_once(tmp_path: Path) -> None:
    """多卡与少卡同时存在时，两个方向必须各报各的，不得互相掩盖。"""
    registered = frozenset({"M0-01", "M0-02"})
    card_dir = _fake_card_tree(tmp_path, ("M0-01", "M9-99"))
    missing, orphan = reconcile(card_dir, registered)
    assert missing == frozenset({"M0-02"}), f"missing 实测 {sorted(missing)}"
    assert orphan == frozenset({"M9-99"}), f"orphan 实测 {sorted(orphan)}"


def test_positive_control_empty_tree_is_not_silently_green(tmp_path: Path) -> None:
    """防 glob 扫空假绿：空目录必须把全部登记任务报成 missing，而非双双为空即通过。"""
    registered = frozenset({"M0-01", "M0-02"})
    card_dir = _fake_card_tree(tmp_path, ())
    assert card_ids_on_disk(card_dir) == frozenset(), "空树实测卡数应为 0"
    missing, orphan = reconcile(card_dir, registered)
    assert missing == registered, f"空树未把全部登记任务报成 missing：{sorted(missing)}"
    assert not orphan, f"空树不应报 orphan：{sorted(orphan)}"


def test_positive_control_absent_dir_is_not_silently_green(tmp_path: Path) -> None:
    """目录压根不存在时同样不得假绿。"""
    missing, orphan = reconcile(tmp_path / "absent", frozenset({"M0-01"}))
    assert missing == frozenset({"M0-01"}), f"missing 实测 {sorted(missing)}"
    assert not orphan, f"orphan 实测 {sorted(orphan)}"


def test_positive_control_d042_ledger_drift_is_reported() -> None:
    """回放 D-042 的真实历史腐化值：恒等式成立、代入值为假，必须仍判红。"""
    corrupted: dict[str, Any] = {KEY_CARDS: 20, KEY_MISSING: 9, KEY_TOTAL: 29}
    bad = ledger_violations(corrupted, measured_cards=26, measured_missing=3)
    assert bad, "正向对照失效：D-042 的历史腐化值（台账 20/9，磁盘实测 26/3）未被判红"
    assert any(KEY_CARDS in item for item in bad), bad
    assert any(KEY_MISSING in item for item in bad), bad
    # 关键：`20 + 9 == 29` 算术成立 —— 只核恒等式的守护必然放过它（D-042 §1）。
    assert not any(IDENTITY_MARK in item for item in bad), (
        "D-042 的腐化形态是等式为真、代入值为假，此处不应报恒等式违规：" + str(bad)
    )


def test_positive_control_broken_identity_is_reported() -> None:
    """反向对照：代入值与实测一致、但恒等式被破坏时也必须判红。"""
    broken: dict[str, Any] = {KEY_CARDS: 29, KEY_MISSING: 1, KEY_TOTAL: 29}
    bad = ledger_violations(broken, measured_cards=29, measured_missing=1)
    assert any(IDENTITY_MARK in item for item in bad), f"恒等式违规未报出：{bad}"


def test_positive_control_consistent_ledger_passes() -> None:
    """对照的对照：三键与实测一致时必须返回空列表，否则上面各条都是空转。"""
    ok: dict[str, Any] = {KEY_CARDS: 29, KEY_MISSING: 0, KEY_TOTAL: 29}
    bad = ledger_violations(ok, measured_cards=29, measured_missing=0)
    assert bad == [], f"一致的台账不应报违规：{bad}"


def test_positive_control_missing_ledger_key_is_reported() -> None:
    """台账缺键不得静默当成 0：必须直接判红（A159 禁判据在缺输入时静默通过）。"""
    incomplete: dict[str, Any] = {KEY_CARDS: 29, KEY_TOTAL: 29}
    raised = False
    try:
        ledger_violations(incomplete, measured_cards=29, measured_missing=0)
    except AssertionError:
        raised = True
    assert raised, "台账缺 known_missing_cards 时必须判红，不得静默通过（A159）"
