"""D-018 回归：任务卡行数口径必须可复跑，档位表表头必须是手册 15.5 的四列形态。

背景（三个形态，均属 D-018）：

1. 手册 v1.6 的 3.1 写了「叙述正文 <= 60 行」，却在同句附上「实测 M0-02 55 行 /
   M0-03 63 行」两个自述数字。v1.7 把口径固化为「卡首 -> 档位表表头行之前」后，同两张卡
   实测均为 29 行；M0-03 整卡 156 行。原自述数字用的是未写明的第三种口径，
   任何人无法复跑，属不可验证的度量。
2. C11 的新口径只约束表头之前的正文。若不加尾部上限，「<= 60 行」可被无限追加
   U 项（未决问题）与裁定追注绕过 —— 该漏洞由子智能体 Dirac 在 N5 主动上报。
3. 手册 6.4 的示例档位表只有「子任务 / 档 / 产出」三列，与 15.5 要求的四列
   （含「预估 token」）硬约束冲突，示例会误导派单；已由 v1.7 修正。

钉住的不变量（全部只依赖文件字节，任何人可复跑）：

1. head：卡首 -> 「子任务档位表」表头行之前 <= HEAD_MAX_LINES 行；
2. tail：档位表最后一行 -> 卡尾 <= TAIL_MAX_LINES 行（封堵形态 2）；
3. total：整卡 <= TOTAL_MAX_LINES 行（绝对兜底）；
4. 表头必须逐字等于 REQUIRED_TABLE_HEADER（手册 15.5 四列形态）；
5. 无档位表的卡只允许是 LEGACY_NO_TABLE 中登记者，且该集合必须单调收敛；
6. LEGACY_TAIL_ANNOTATED 只豁免第 2 项：这两张卡的尾部是历史裁定追注，按项目纪律
   「历史测量值绝不重写，只加注」不得删改；第 1/3/4 项仍须实测达标，注记不得当豁免用。
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CARD_DIR = REPO / "orchestrator" / "tasks"

HEAD_MAX_LINES = 60
TAIL_MAX_LINES = 40
TOTAL_MAX_LINES = 200
REQUIRED_TABLE_HEADER = "| 子任务 | 档位 | 预估 token | 产出 |"

# 防 glob 扫空导致全绿（手册 15.4：守护测试必须自带分母断言）。
CARD_MIN_COUNT = 12

# 早于手册 15.5 交付、无档位表且不追溯补写的历史卡；补齐一张即须从此处删掉一个 id。
LEGACY_NO_TABLE: frozenset[str] = frozenset({"M0-01", "M0-P01"})

# 口径固化（v1.7 / D-018）前已带裁定追注的卡：仅豁免 tail，head/total/表头仍须达标。
LEGACY_TAIL_ANNOTATED: frozenset[str] = frozenset({"M0-02", "M0-03"})


def _cards() -> list[str]:
    return sorted(p.stem for p in CARD_DIR.glob("*.md"))


def _split(text: str) -> tuple[int, int, int, bool]:
    """返回 (head, tail, total, has_table)，口径见模块 docstring。"""
    lines = text.split("\n")
    header_idx: int | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and "子任务" in stripped:
            header_idx = i
            break
    if header_idx is None:
        return len(lines), 0, len(lines), False
    end = header_idx
    while end < len(lines) and lines[end].strip().startswith("|"):
        end += 1
    return header_idx, len(lines) - end, len(lines), True


def _header_of(text: str) -> str | None:
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|") and "子任务" in stripped:
            return stripped
    return None


def test_card_dir_denominator() -> None:
    cards = _cards()
    assert len(cards) >= CARD_MIN_COUNT, (
        f"任务卡数量异常（疑似 glob 扫空导致假绿）：实测 {len(cards)}，下限 {CARD_MIN_COUNT}"
    )


def test_head_narrative_within_pinned_caliber() -> None:
    over: list[tuple[str, int]] = []
    for card in _cards():
        head, _, _, has_table = _split((CARD_DIR / f"{card}.md").read_text(encoding="utf-8"))
        if has_table and head > HEAD_MAX_LINES:
            over.append((card, head))
    assert not over, (
        f"叙述正文超出手册 3.1 上限 {HEAD_MAX_LINES} 行"
        f"（口径：卡首 -> 档位表表头行之前，按原始行数计）：{over}"
    )


def test_tail_narrative_cannot_grow_unbounded() -> None:
    """D-018 形态 2：尾部（U 项与裁定追注）必须有上限，否则 head 上限可被绕过。"""
    over: list[tuple[str, int]] = []
    for card in _cards():
        if card in LEGACY_TAIL_ANNOTATED:
            continue
        _, tail, _, has_table = _split((CARD_DIR / f"{card}.md").read_text(encoding="utf-8"))
        if has_table and tail > TAIL_MAX_LINES:
            over.append((card, tail))
    assert not over, (
        f"档位表之后的尾部超出 {TAIL_MAX_LINES} 行上限（U 项/追注须收敛或拆卡）：{over}"
    )


def test_total_card_lines_within_absolute_cap() -> None:
    over: list[tuple[str, int]] = []
    for card in _cards():
        total = len((CARD_DIR / f"{card}.md").read_text(encoding="utf-8").split("\n"))
        if total > TOTAL_MAX_LINES:
            over.append((card, total))
    assert not over, f"整卡行数超出绝对兜底 {TOTAL_MAX_LINES} 行，必须拆卡：{over}"


def test_table_header_is_four_column_form() -> None:
    bad: list[tuple[str, str]] = []
    for card in _cards():
        if card in LEGACY_NO_TABLE:
            continue
        header = _header_of((CARD_DIR / f"{card}.md").read_text(encoding="utf-8"))
        if header != REQUIRED_TABLE_HEADER:
            bad.append((card, header or "NO_TABLE"))
    assert not bad, (
        f"档位表表头不是手册 15.5 的四列形态 {REQUIRED_TABLE_HEADER!r}"
        f"（缺「预估 token」列即违反 6.6 成本护栏）：{bad}"
    )


def test_legacy_no_table_set_is_exact() -> None:
    no_table = {
        card
        for card in _cards()
        if not _split((CARD_DIR / f"{card}.md").read_text(encoding="utf-8"))[3]
    }
    unregistered = no_table - LEGACY_NO_TABLE
    assert not unregistered, (
        f"这些卡没有「子任务档位表」，手册 15.5 规定无拆解表不得 spawn：{sorted(unregistered)}"
    )
    recovered = LEGACY_NO_TABLE - no_table
    assert not recovered, (
        f"这些历史卡已补上档位表，必须从 LEGACY_NO_TABLE 移除以保持单调收敛：{sorted(recovered)}"
    )


def test_legacy_tail_annotation_is_not_a_blanket_exempt() -> None:
    """注记不得变成豁免：LEGACY_TAIL_ANNOTATED 仍须过 head / total / 表头三项。"""
    violations: list[str] = []
    for card in sorted(LEGACY_TAIL_ANNOTATED):
        path = CARD_DIR / f"{card}.md"
        if not path.exists():
            violations.append(f"{card}: 卡不存在")
            continue
        text = path.read_text(encoding="utf-8")
        head, _, total, has_table = _split(text)
        if not has_table:
            violations.append(f"{card}: 无档位表，不应登记为 TAIL 豁免")
        if head > HEAD_MAX_LINES:
            violations.append(f"{card}: head {head} > {HEAD_MAX_LINES}")
        if total > TOTAL_MAX_LINES:
            violations.append(f"{card}: total {total} > {TOTAL_MAX_LINES}")
        header = _header_of(text)
        if header != REQUIRED_TABLE_HEADER:
            violations.append(f"{card}: 表头 {header!r}")
    assert not violations, f"LEGACY_TAIL_ANNOTATED 被当成全面豁免使用：{violations}"
