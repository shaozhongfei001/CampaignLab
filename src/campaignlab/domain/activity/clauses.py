"""条款确认门禁（M2-01 · S2a；design §4.1 / §4.2 / §4.3）。

对齐 AC-004「必填条款未确认时无法确认」。本文件冻结三件事：

1. **条款键集合**（design §4.1，任务卡 ``public_frozen`` 面）：``REQUIRED_CLAUSE_KEYS`` 是
   全仓**唯一来源**，M2-02 / M2-03 / M2-04 按此消费，改动走 CR。``checks.py`` 的九项检查
   共用同一张表，但**各自独立求值、互不调用**（``checkRule`` 是只读 GET，不得触发门禁写路径）。
2. **门禁的六条规则**（design §4.3 的 G1–G6，全部 ``severity="ERROR"``）：门禁本身不产生
   ``WARNING`` —— 警告只来自 ``checks.py`` 的检查项框架。
3. **两个确认前置判定的纯函数侧**（design §4.2 第 6 / 第 8 条）：摘要比对与「警告需备注」。

``GateIssue`` 是**领域侧中间形态**，由 api 层映射成契约 ``Issue``（design §11.1）：
domain 层禁 import ``campaignlab.api``，故这里**不**出现 ``Issue``；四字段与契约
``components.schemas.Issue`` 逐字同形（``code`` / ``location`` / ``message`` / ``severity``），
映射是纯字段搬运，不含判定。

``Issue.code`` 是**自由串**（契约：ID 正则 1–96），与 ``Problem.code`` 的 20 码注册表是两个面
⇒ ``CLAUSE_ISSUE_CODES`` 里的标签**禁**提升为 ``Problem.code``（ADR-005 §2.1；本设计零新增
``Problem.code``、零新增 ``DomainError`` 子类）。

本文件不含 SQL 文本、不开事务、不取系统时间；``registered_evidence_ids`` 由调用方从
``evidence`` 表只读查出后注入（design §4.3 G5 的存在性校验）。
"""

from __future__ import annotations

import unicodedata
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal

__all__ = [
    "ALL_CLAUSE_KEYS",
    "CLAUSE_ISSUE_CODES",
    "REQUIRED_CLAUSE_KEYS",
    "GateIssue",
    "confirm_digest_matches",
    "evaluate_clause_gate",
    "note_satisfies_warnings",
]

#: design §4.1：按模板索引的**必需**条款键。顺序即 ``architecture/RULES.md``
#: 「条款键与无效案例」的原文顺序（满额赠券六项、远程回拨三项），``issues[]`` 的稳定排序靠它。
#: 键名禁发明成 spec 之外的值；表外的自由键**允许**存在（既不阻塞确认、也不参与必需性判定），
#: 但**同键重复**一律拒（G3）。
REQUIRED_CLAUSE_KEYS: Final[dict[str, tuple[str, ...]]] = {
    "coupon_threshold": (
        "new_customer",
        "payment",
        "time_window",
        "stacking",
        "budget_and_quota",
        "refund",
    ),
    "callback_priority": ("same_day_scope", "priority", "daily_cap"),
}

#: 两个模板的必需键按序去重后的并集（项数以 ``len(ALL_CLAUSE_KEYS)`` 运行时实取为准，禁写死）。
ALL_CLAUSE_KEYS: Final[tuple[str, ...]] = tuple(
    dict.fromkeys(key for keys in REQUIRED_CLAUSE_KEYS.values() for key in keys)
)

#: 本文件产出的全部 ``Issue.code`` 标签：design §4.3 的 G1–G6 六个
#: ＋ design §4.2 第 5 / 6 / 8 条的三个（``SCHEMA_VERSION_UNSUPPORTED`` 的**判定**在 api／service
#: 层，标签冻结在这里，使 M2-01 的 ``Issue.code`` 登记面有唯一出处）。
CLAUSE_ISSUE_CODES: Final[tuple[str, ...]] = (
    "CLAUSE_MISSING",
    "CLAUSE_UNCONFIRMED",
    "CLAUSE_DUPLICATE",
    "CLAUSE_EVIDENCE_MISSING",
    "CLAUSE_EVIDENCE_UNREGISTERED",
    "CLAUSE_DECISION_EMPTY",
    "SCHEMA_VERSION_UNSUPPORTED",
    "CONFIRMATION_DIGEST_MISMATCH",
    "CONFIRMATION_NOTE_REQUIRED",
)

#: design §4.2 第 8 条冻结的文案（同时用作 ``Problem.detail`` 与 ``Issue.message``：
#: 二者语义完全重合，写两份必然漂移）。
_NOTE_REQUIRED_TEXT: Final = "存在需审核备注的警告，请在确认备注中记录判断"

#: 契约 ``Issue.message`` 的 maxLength（``components.schemas.Issue.properties.message``）。
_MESSAGE_MAX_LENGTH: Final = 500


@dataclass(frozen=True, slots=True)
class GateIssue:
    """领域侧的 issue 中间形态（字段与契约 ``Issue`` 逐字同形，禁在 domain 里 import ``Issue``）。

    ``location`` 一律 JSON Pointer 形。**条款用键名而非数组下标定位**（``/terms/stacking``）：
    条款的身份是 ``key``，下标会随客户端给出的数组顺序漂移（design §5.3 末条）。
    ``bindings`` 侧相反（用下标），因为 ``Binding`` 没有身份键 —— 这个差异是**刻意的**，禁统一。
    """

    code: str
    location: str
    message: str
    severity: Literal["ERROR", "WARNING", "INFO"]


def _issue(code: str, location: str, message: str) -> GateIssue:
    """门禁项一律 ``ERROR``（design §4.3：六条全是 ERROR ⇒ 全部阻塞确认）。"""
    return GateIssue(
        code=code, location=location, message=message[:_MESSAGE_MAX_LENGTH], severity="ERROR"
    )


def _rank(key: str, required: tuple[str, ...]) -> int:
    """排序主键：``REQUIRED_CLAUSE_KEYS`` 的键序；表外自由键一律排在必需键之后。"""
    return required.index(key) if key in required else len(required)


def evaluate_clause_gate(
    *,
    template: str,
    terms: Sequence[Mapping[str, Any]],
    registered_evidence_ids: Collection[str],
) -> tuple[GateIssue, ...]:
    """design §4.3 的 G1→G6，返回**全部** ERROR 项（不是首错即返）。

    求值顺序＝G1→G6（design §11.1）；返回顺序另按 design §4.2 第 7 条稳定排序：
    **先按 ``REQUIRED_CLAUSE_KEYS`` 的键序、再按 ``terms`` 数组下标**（同键同下标时保持
    G 序，故同一条款的 G2 → G4/G5 → G6 相邻出现）。两条口径同时满足，靠
    「按 G 序收集 ＋ 最后按 (键序, 下标) 稳定排序」实现。

    同一必需键最多命中 G1 **或** {G2, G4/G5, G6} 之一（缺失与存在互斥）。存在重复登记时，
    G2 / G4 / G5 / G6 一律对**首个**下标求值（重复本身已由 G3 逐下标报出），保证结果确定。

    ``template`` 不在 ``REQUIRED_CLAUSE_KEYS`` 里时必需键集为空（只有 G3 仍对自由键生效）：
    未知模板由 ``checks.py`` 的 C6（``TEMPLATE_UNKNOWN``）负责报，本函数不重复报同一事实。
    """
    required = REQUIRED_CLAUSE_KEYS.get(template, ())
    occurrences: dict[str, list[int]] = {}
    for index, term in enumerate(terms):
        occurrences.setdefault(str(term.get("key", "")), []).append(index)

    collected: list[tuple[int, int, GateIssue]] = []

    # G1：必需键缺失。
    for key in required:
        if key not in occurrences:
            collected.append(
                (
                    _rank(key, required),
                    -1,
                    _issue("CLAUSE_MISSING", f"/terms/{key}", f"必需条款 {key} 缺失"),
                )
            )

    # G2：必需键仍为 OPEN。
    for key in required:
        indexes = occurrences.get(key)
        if not indexes:
            continue
        index = indexes[0]
        if str(terms[index].get("status", "")) != "CONFIRMED":
            collected.append(
                (
                    _rank(key, required),
                    index,
                    _issue(
                        "CLAUSE_UNCONFIRMED", f"/terms/{key}/status", f"必需条款 {key} 仍为 OPEN"
                    ),
                )
            )

    # G3：任一 key 出现 >1 次（含自由键），逐下标各报一条。
    for key, indexes in occurrences.items():
        if len(indexes) < 2:
            continue
        rank = _rank(key, required)
        for index in indexes:
            collected.append(
                (
                    rank,
                    index,
                    _issue("CLAUSE_DUPLICATE", f"/terms/{index}", f"条款键 {key} 重复登记"),
                )
            )

    # G4 / G5 / G6：必需键的来源与业务说明。
    for key in required:
        indexes = occurrences.get(key)
        if not indexes:
            continue
        index = indexes[0]
        term = terms[index]
        rank = _rank(key, required)
        evidence_id = term.get("evidence_id")
        if evidence_id is None:
            collected.append(
                (
                    rank,
                    index,
                    _issue(
                        "CLAUSE_EVIDENCE_MISSING",
                        f"/terms/{key}/evidence_id",
                        f"必需条款 {key} 缺已登记来源",
                    ),
                )
            )
        elif str(evidence_id) not in registered_evidence_ids:
            collected.append(
                (
                    rank,
                    index,
                    _issue(
                        "CLAUSE_EVIDENCE_UNREGISTERED",
                        f"/terms/{key}/evidence_id",
                        f"必需条款 {key} 的来源未登记",
                    ),
                )
            )
        if not str(term.get("decision", "")).strip():
            collected.append(
                (
                    rank,
                    index,
                    _issue(
                        "CLAUSE_DECISION_EMPTY",
                        f"/terms/{key}/decision",
                        f"必需条款 {key} 缺业务说明",
                    ),
                )
            )

    collected.sort(key=lambda item: (item[0], item[1]))
    return tuple(item[2] for item in collected)


def note_satisfies_warnings(*, note: str, warnings: Sequence[GateIssue]) -> GateIssue | None:
    """design §4.2 第 8 条：存在 ``WARNING`` 时，``Confirmation.note`` 经 NFKC ＋ ``strip()``
    后必须**非空**；满足返回 ``None``，不满足返回那条 ``CONFIRMATION_NOTE_REQUIRED``。

    契约的 ``note.minLength=1`` 允许单个空格（真值来源
    ``components.schemas.Confirmation.properties.note``），故「非空」必须由领域侧判、
    禁依赖 Schema。用 NFKC 而不是 ``strip()`` 单打：全角空格（U+3000）在不规范化时
    ``strip()`` 已经能吃掉，但 NBSP（U+00A0）在 NFKC 下才折叠成普通空格 ——
    「一个 NBSP 就算写过备注」正是本条要堵的口子。

    ``warnings`` 可以直接传**全部** issue：本函数自己按 ``severity == "WARNING"`` 过滤，
    故调用方不必先分组（ERROR 项归 design §4.2 第 7 条，与本条互不影响）。
    """
    if not any(item.severity == "WARNING" for item in warnings):
        return None
    if unicodedata.normalize("NFKC", note).strip():
        return None
    return _issue("CONFIRMATION_NOTE_REQUIRED", "/note", _NOTE_REQUIRED_TEXT)


def confirm_digest_matches(*, provided: str, current: str) -> bool:
    """design §4.2 第 6 条：**只比较、不回显**。

    不相等时调用方抛 409 ``VERSION_MISMATCH``（``DomainError(code="VERSION_MISMATCH")``，
    该码在 20 码注册表内但没有专属异常类），``issues[0].code`` 用
    ``CONFIRMATION_DIGEST_MISMATCH``、``location="/digest"``；detail 固定
    「确认摘要与当前规则内容不一致，请重新读取后再确认」，**禁回显两个摘要值**
    （回显等于给客户端一个「服务端存了哪一版」的探针）。本函数返回 ``bool`` 而不是抛异常，
    正是为了让「回显」在类型上无从发生。
    """
    return provided == current
