"""规则检查项框架（M2-01 · S2a；design §5）。

对齐 AC-004「门槛、预算、叠加、日期和退款口径分别检查」。本文件是 design §5.1 注册形态、
§5.2 判定结果、§5.3 九项检查与 §5.4 反例配方的唯一代码化副本。

三条边界（**越界即设计不合格**）：

1. **只读 ``RuleContext``**：不含连接、不含时钟、不含 SQL 文本。反例的全部时间戳与金额
   **只从被检规则版本的 ``content`` 推导**（``checkRule`` 无正文、无查询参数），故同一规则版本
   重复调用必须产出**逐字节相同**的 ``boundary_cases``（design §5.4）。
2. **禁判定、禁回放**（裁定 A203）：反例只有「数据 ＋ 待验证行为文案」。契约
   ``BoundaryCase`` 实测只有 ``id``/``label``/``input``/``verification`` 四字段，**没有**
   ``expected``/``actual``/``verdict`` ⇒ 契约本身就不允许 ``checkRule`` 返回数值判定。
   ±1 分的**数值面**归 M2-02 的 ``domain/rules/**``；本文件不做任何金额分推进。
3. ``REASON_CODE_GLOSSARY`` 里的原因码只是**文案字面量**，既不是本文件算出的判定，
   也**禁**提升为 ``Problem.code``（20 码冻结面）。

与 design §4 的条款门禁共用同一份键表 ``REQUIRED_CLAUSE_KEYS``（唯一来源），但**各自独立
求值、互不调用**：门禁跑在 ``confirmRule`` 里、结果进 ``Problem.issues``；检查跑在
``checkRule`` 里、结果进 ``RuleCheck.issues``（design §5.3 末段）。每个必需键**恰由一个**
检查项负责报「未确认」（coupon：``time_window``→C1、``payment``→C2、``budget_and_quota``→C3、
``stacking``→C4、``refund``→C5、``new_customer``→C7；callback：三键→C8），
``run_checks`` 再按 ``(code, location)`` 去重做纵深防御。

⚠ design §5.2 的命名陷阱：``RuleCheckState``（``READY``/``NEEDS_CONFIRMATION``，检查结论）与
``RuleVersion.state``（``DRAFT``/``CONFIRMED``）、与 ``listRules`` 的 ``status`` **查询参数**
是三个不同的面，取值集合互不相同，禁互相赋值。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Final, Literal, get_args

from campaignlab.domain.activity.clauses import REQUIRED_CLAUSE_KEYS, GateIssue
from campaignlab.domain.activity.states import RuleCheckState, TemplateId
from campaignlab.domain.values import TZ_SHANGHAI

__all__ = [
    "CHECKS",
    "CHECK_IDS",
    "CHECK_ISSUE_CODES",
    "REASON_CODE_GLOSSARY",
    "BoundaryCaseDraft",
    "Check",
    "CheckCategory",
    "CheckId",
    "CheckResult",
    "RuleContext",
    "boundary_cases_for",
    "check_state_of",
    "run_checks",
]

CheckId = Literal["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9"]

#: 前五类即 AC-004 点名的「日期 / 门槛 / 预算 / 叠加 / 退款口径」，后三类来自
#: ``architecture/RULES.md``「规则检视」的「候选同模板、竞争和事件顺序」（design §5.1）。
CheckCategory = Literal[
    "DATE", "THRESHOLD", "BUDGET", "STACKING", "REFUND", "TEMPLATE", "SEQUENCE", "COMPETITION"
]

#: design §5.3 表里出现的**全部** ``Issue.code``（23 个；含 ``TEMPLATE_MISMATCH`` ——
#: 它不落 ``RuleCheck``，而是 ``compareRules`` 跨模板时直接 422 ``VALIDATION_ERROR`` 的
#: ``issues[0].code``，登记在此使 M2-01 的 code 面有唯一出处）。
CHECK_ISSUE_CODES: Final[tuple[str, ...]] = (
    "WINDOW_ORDER_INVALID",
    "TIME_WINDOW_CLAUSE_UNCONFIRMED",
    "REWARD_EXCEEDS_THRESHOLD",
    "THRESHOLD_ZERO",
    "PAYMENT_CLAUSE_UNCONFIRMED",
    "BUDGET_ZERO",
    "BUDGET_BELOW_COUPON",
    "QUOTA_EXCEEDS_BUDGET",
    "BUDGET_CLAUSE_UNCONFIRMED",
    "STACKING_CLAUSE_UNCONFIRMED",
    "STACKING_ALLOW",
    "REFUND_CLAUSE_UNCONFIRMED",
    "REFUND_RECOMPUTE",
    "TEMPLATE_UNKNOWN",
    "TEMPLATE_CONST_MISMATCH",
    "TEMPLATE_MISMATCH",
    "NEW_CUSTOMER_CLAUSE_UNCONFIRMED",
    "NEW_CUSTOMER_WINDOW_INVALID",
    "SAME_DAY_CLAUSE_UNCONFIRMED",
    "PRIORITY_CLAUSE_UNCONFIRMED",
    "DAILY_CAP_CLAUSE_UNCONFIRMED",
    "PRIORITY_APPOINTMENT_FIRST",
    "RULE_OVERLAP_REVIEW",
)

#: design §5.4 的 15 个原因码字面量（``RULES.md``「满额赠券」段 14 个 ＋「远程回拨」段的
#: ``CAP_REACHED``）。**只作文案用**：本文件不计算它们，也不得把它们变成 ``Problem.code``。
REASON_CODE_GLOSSARY: Final[tuple[str, ...]] = (
    "ISSUED",
    "OUTSIDE_ACTIVITY",
    "NOT_NEW",
    "BELOW_THRESHOLD",
    "STACK_DENIED",
    "CUSTOMER_LIMIT",
    "BUDGET_EXHAUSTED",
    "DUPLICATE_EVENT",
    "DUPLICATE_ORDER",
    "REFUND_RECORDED",
    "REVOKED",
    "USED_COUPON_REVIEW",
    "REDEEMED",
    "INVALID_EVENT",
    "CAP_REACHED",
)

#: ``CheckId`` 的 2 值模板白名单由 ``states.TemplateId`` 反推（禁抄字面量）。
_TEMPLATE_IDS: Final[tuple[str, ...]] = tuple(get_args(TemplateId))

_COUPON: Final = "coupon_threshold"
_CALLBACK: Final = "callback_priority"

#: 契约 ``const`` 面（真值来源 ``components.schemas.CouponRule`` / ``.CallbackRule``）。
#: C6 用它做纵深防御：DTO 校验期已经挡住绝大多数偏离，这里再挡一次「绕过 DTO 直接
#: 喂字典」的路径（design §5.3 C6 第二行）。
_CONST_BY_TEMPLATE: Final[dict[str, tuple[tuple[str, object], ...]]] = {
    _COUPON: (
        ("schema_version", 1),
        ("template", _COUPON),
        ("currency", "CNY"),
        ("zone", "Asia/Shanghai"),
    ),
    _CALLBACK: (
        ("schema_version", 1),
        ("template", _CALLBACK),
        ("zone", "Asia/Shanghai"),
        ("channel", "remote"),
    ),
}

#: design §5.4 冻结的反例常量：客户号、回拨固定日与首个事件时刻（09:00 起、逐小时递增）、
#: 回拨策略号。全部是**冻结字面量**，不读时钟。
_CUSTOMER_ID: Final = "CUS-CHECK"
_CALLBACK_FIRST_HOUR: Final = 9
_CALLBACK_BASE: Final[datetime] = datetime(2026, 1, 5, _CALLBACK_FIRST_HOUR, tzinfo=TZ_SHANGHAI)
_CALLBACK_DAY: Final[str] = _CALLBACK_BASE.date().isoformat()
_CALLBACK_STRATEGY_ID: Final = "S-101"

#: 契约 ``Issue.message`` 的 maxLength；``boundary_cases.items.label`` 是 120、
#: ``.verification`` 是 500（design §5.3：长度按契约截）。
_MESSAGE_MAX_LENGTH: Final = 500
_LABEL_MAX_LENGTH: Final = 120
_VERIFICATION_MAX_LENGTH: Final = 500


@dataclass(frozen=True, slots=True)
class RuleContext:
    """一次 ``checkRule`` 的全部输入（design §11.1）。

    **不含连接、不含时钟**（design §5.1）：``content`` 是 ``model_dump(mode="json")`` 后的
    映射，``terms`` 是条款映射序列（**保持落库顺序**），``sibling_confirmed`` 是同活动下
    其它 ``CONFIRMED`` 版本的只读投影（只含 ``id`` / ``template`` / ``starts_at`` / ``ends_at``，
    供 C9 判「多个规则覆盖同一情境」）。
    """

    rule_id: str
    template: str
    content: Mapping[str, Any]
    terms: Sequence[Mapping[str, Any]]
    sibling_confirmed: Sequence[Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class BoundaryCaseDraft:
    """反例的**领域侧**形态（api 层 ``model_validate`` 成契约 ``BoundaryCase``）。

    ``input_payload`` 是领域侧的 ``CaseInput`` **字典**：本文件不 import 契约 DTO，
    故 ``template`` 单独带出来供 api 层选判别式分支。反例的 ``input`` 自身必须能过契约校验
    （``events.minItems=1``、``seq >= 1``、``amount_fen >= 0`` …）—— design §5.4 要求 S5
    把每个生成的 ``input`` 都 ``model_validate`` 一遍，因为「生成的反例自身不合法」
    是这类框架最典型的假绿。
    """

    id: str
    label: str
    template: str
    input_payload: Mapping[str, Any]
    verification: str


@dataclass(frozen=True, slots=True)
class CheckResult:
    """一个检查项的产出（design §5.1：``issues`` ＋ ``boundary_cases`` 两段）。"""

    issues: tuple[GateIssue, ...] = ()
    boundary_cases: tuple[BoundaryCaseDraft, ...] = ()


@dataclass(frozen=True, slots=True)
class Check:
    """注册表的一行（design §5.1，与 §3 的迁移表同构，便于同一套读法复核）。"""

    id: CheckId
    category: CheckCategory
    templates: tuple[TemplateId, ...]
    spec_ref: str
    clause_keys: tuple[str, ...]
    run: Callable[[RuleContext], CheckResult]


def _as_int(value: object) -> int | None:
    """``model_dump(mode="json")`` 后的整数；``bool`` 显式排除（它是 ``int`` 的子类）。"""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _as_datetime(value: object) -> datetime | None:
    """把 ISO 串（或已是时刻的值）解析成 ``datetime``；解析不出返回 ``None``。

    契约 ``format=date-time`` 已在 DTO 校验期挡住非时刻串，故 ``None`` 只可能来自
    「绕过 DTO 直接喂字典」的路径 —— 那时**不产出** issue 而不是抛异常
    （纯函数不炸；C6 的常量纵深防御另有其位）。
    """
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _iso(value: object) -> str | None:
    """时刻 → 契约可接受的 ISO 串（带偏移）；不可解析返回 ``None``。"""
    parsed = _as_datetime(value)
    return None if parsed is None else parsed.isoformat()


def _issue(
    code: str, location: str, message: str, severity: Literal["ERROR", "WARNING", "INFO"] = "ERROR"
) -> GateIssue:
    return GateIssue(
        code=code, location=location, message=message[:_MESSAGE_MAX_LENGTH], severity=severity
    )


def _clause_message(key: str) -> str:
    """C1/C2/C3/C4/C5/C7/C8 共用的「三态」文案（键缺失 / 状态非 CONFIRMED / 缺已登记来源）。"""
    return f"必需条款 {key} 未确认（缺失、状态非 CONFIRMED 或缺已登记来源）"


def _clause_unconfirmed(terms: Sequence[Mapping[str, Any]], key: str) -> bool:
    """必需键的三态判定（design §5.3 C1 行的口径，其余检查项复用）。

    与 ``clauses.evaluate_clause_gate`` 的 G1/G2/G4 **不共用实现**：门禁跑在写路径、
    要逐条给出细因 location；检查跑在只读 GET、只要一个布尔。两者共用的是**键表**。
    """
    for term in terms:
        if str(term.get("key", "")) == key:
            return term.get("status") != "CONFIRMED" or term.get("evidence_id") is None
    return True


def _ids(case: str, seq: int) -> tuple[str, str]:
    """``(event_id, order_id)``：design §5.4 冻结的 ``EV-<CheckId>-<n>-<seq>`` /
    ``ORD-<CheckId>-<n>-<seq>`` 形态（``<n>`` 是反例在该检查项内的序号，与 ``id`` 的
    ``bc-<CheckId>-<n>`` 同号），均满足 ID 正则。
    """
    return f"EV-{case}-{seq}", f"ORD-{case}-{seq}"


def _coupon_event(
    *,
    seq: int,
    event_id: str,
    order_id: str,
    kind: str,
    at: str,
    amount_fen: int,
    other_offer_applied: bool = False,
) -> dict[str, Any]:
    return {
        "seq": seq,
        "event_id": event_id,
        "kind": kind,
        "at": at,
        "order_id": order_id,
        "amount_fen": amount_fen,
        "other_offer_applied": other_offer_applied,
    }


def _coupon_case_input(
    *,
    registered_at: str,
    events: Sequence[Mapping[str, Any]],
    initial_used: int = 0,
    initial_budget_used_fen: int = 0,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "template": _COUPON,
        "customer_id": _CUSTOMER_ID,
        "registered_at": registered_at,
        "initial_used": initial_used,
        "initial_budget_used_fen": initial_budget_used_fen,
        "events": [dict(event) for event in events],
    }


def _callback_event(*, seq: int, event_id: str, at: str, appointment: bool) -> dict[str, Any]:
    return {
        "seq": seq,
        "event_id": event_id,
        "at": at,
        "strategy_id": _CALLBACK_STRATEGY_ID,
        "appointment": appointment,
    }


def _callback_case_input(*, used: int, events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "template": _CALLBACK,
        "customer_id": _CUSTOMER_ID,
        "day": _CALLBACK_DAY,
        "channel": "remote",
        "used": used,
        "events": [dict(event) for event in events],
    }


def _callback_at(hours_after_base: int) -> str:
    """``2026-01-05`` 当日 09:00、10:00… 逐小时递增（design §5.4 反例 16 的配方）。

    ``daily_cap`` 上限是 20 ⇒ 反例 16/17 最多 21 个事件，逐小时递增会跨过当日午夜；
    design 原文冻结的就是「09:00、10:00…」，故照抄不改（``day`` 是**输入参数**，
    事件时刻与它不同日不构成契约违例，判定面归 M2-02）。
    """
    return (_CALLBACK_BASE + timedelta(hours=hours_after_base)).isoformat()


def _case(
    *, case_id: str, label: str, template: str, payload: Mapping[str, Any], verification: str
) -> BoundaryCaseDraft:
    return BoundaryCaseDraft(
        id=case_id,
        label=label[:_LABEL_MAX_LENGTH],
        template=template,
        input_payload=payload,
        verification=verification[:_VERIFICATION_MAX_LENGTH],
    )


def _min_payment(context: RuleContext) -> int:
    """``content.min_payment_fen``（缺失时退 0，只为让反例的 ``amount_fen >= 0`` 恒成立）。"""
    return _as_int(context.content.get("min_payment_fen")) or 0


def _payment_event(case: str, at: str, amount_fen: int, seq: int = 1) -> dict[str, Any]:
    event_id, order_id = _ids(case, seq)
    return _coupon_event(
        seq=seq,
        event_id=event_id,
        order_id=order_id,
        kind="PAYMENT",
        at=at,
        amount_fen=amount_fen,
    )


def _check_window(context: RuleContext) -> CheckResult:
    """C1 · DATE · coupon · 负责 ``time_window``（design §5.3 C1 ＋ §5.4 反例 3/4/5）。"""
    starts = _as_datetime(context.content.get("starts_at"))
    ends = _as_datetime(context.content.get("ends_at"))
    issues: list[GateIssue] = []
    if starts is not None and ends is not None and starts >= ends:
        issues.append(
            _issue(
                "WINDOW_ORDER_INVALID",
                "/content/ends_at",
                f"活动止时刻 {ends.isoformat()} 不晚于起时刻 {starts.isoformat()}，"
                "窗口 [starts_at, ends_at) 为空或倒挂",
            )
        )
    if _clause_unconfirmed(context.terms, "time_window"):
        issues.append(
            _issue(
                "TIME_WINDOW_CLAUSE_UNCONFIRMED",
                "/terms/time_window",
                _clause_message("time_window"),
            )
        )

    cases: list[BoundaryCaseDraft] = []
    amount = _min_payment(context)
    if starts is not None:
        at = starts.isoformat()
        cases.append(
            _case(
                case_id="bc-C1-1",
                label="活动起点（含）",
                template=_COUPON,
                payload=_coupon_case_input(
                    registered_at=at, events=[_payment_event("C1-1", at, amount)]
                ),
                verification="起点包含，期望参与判定（[starts_at, ends_at) 左闭）",
            )
        )
    if ends is not None:
        cases.append(
            _case(
                case_id="bc-C1-2",
                label="活动终点（排）",
                template=_COUPON,
                payload=_coupon_case_input(
                    registered_at=ends.isoformat(),
                    events=[_payment_event("C1-2", ends.isoformat(), amount)],
                ),
                verification="终点排除，期望不触发（原因码 OUTSIDE_ACTIVITY）",
            )
        )
    if starts is not None:
        at = starts.isoformat()
        # 反例 5：两笔**同一 event_id、同一 order_id、同一金额**的支付（seq 递增）。
        event_id, order_id = _ids("C1-3", 1)
        cases.append(
            _case(
                case_id="bc-C1-3",
                label="重复支付",
                template=_COUPON,
                payload=_coupon_case_input(
                    registered_at=at,
                    events=[
                        _coupon_event(
                            seq=1,
                            event_id=event_id,
                            order_id=order_id,
                            kind="PAYMENT",
                            at=at,
                            amount_fen=amount,
                        ),
                        _coupon_event(
                            seq=2,
                            event_id=event_id,
                            order_id=order_id,
                            kind="PAYMENT",
                            at=at,
                            amount_fen=amount,
                        ),
                    ],
                ),
                verification="同 ID 同业务字段仅记重复（原因码 DUPLICATE_EVENT），第二笔不再发放",
            )
        )
    return CheckResult(issues=tuple(issues), boundary_cases=tuple(cases))


def _check_threshold(context: RuleContext) -> CheckResult:
    """C2 · THRESHOLD · coupon · 负责 ``payment``（design §5.3 C2 ＋ §5.4 反例 1/2）。"""
    content = context.content
    min_payment = _as_int(content.get("min_payment_fen"))
    coupon_fen = _as_int(content.get("coupon_fen"))
    issues: list[GateIssue] = []
    if min_payment is not None and coupon_fen is not None and coupon_fen > min_payment:
        issues.append(
            _issue(
                "REWARD_EXCEEDS_THRESHOLD",
                "/content/coupon_fen",
                f"券面额 {coupon_fen} 分高于门槛 {min_payment} 分，单笔支付即可净赚",
                "WARNING",
            )
        )
    if min_payment == 0:
        issues.append(
            _issue(
                "THRESHOLD_ZERO",
                "/content/min_payment_fen",
                "门槛为 0 分，任何一笔支付都能触发发放",
                "WARNING",
            )
        )
    if _clause_unconfirmed(context.terms, "payment"):
        issues.append(
            _issue("PAYMENT_CLAUSE_UNCONFIRMED", "/terms/payment", _clause_message("payment"))
        )

    cases: list[BoundaryCaseDraft] = []
    starts_at = _iso(content.get("starts_at"))
    if starts_at is not None and min_payment is not None:
        if min_payment > 0:
            # 反例 1：``min_payment_fen == 0`` 时**不生成**
            # （无合法的「减一分」值，且 C2 已报 THRESHOLD_ZERO）。
            cases.append(
                _case(
                    case_id="bc-C2-1",
                    label="门槛减一分",
                    template=_COUPON,
                    payload=_coupon_case_input(
                        registered_at=starts_at,
                        events=[_payment_event("C2-1", starts_at, min_payment - 1)],
                    ),
                    verification="净实付低于门槛一分，期望不发放（原因码 BELOW_THRESHOLD）",
                )
            )
        cases.append(
            _case(
                case_id="bc-C2-2",
                label="等于阈值",
                template=_COUPON,
                payload=_coupon_case_input(
                    registered_at=starts_at,
                    events=[_payment_event("C2-2", starts_at, min_payment)],
                ),
                verification="相等边界通过，期望发放一张（原因码 ISSUED）",
            )
        )
    return CheckResult(issues=tuple(issues), boundary_cases=tuple(cases))


def _check_budget(context: RuleContext) -> CheckResult:
    """C3 · BUDGET · coupon · 负责 ``budget_and_quota``（design §5.3 C3 ＋ §5.4 反例 8/9/10）。"""
    content = context.content
    budget_fen = _as_int(content.get("budget_fen"))
    coupon_fen = _as_int(content.get("coupon_fen"))
    max_per_customer = _as_int(content.get("max_per_customer"))
    issues: list[GateIssue] = []
    if budget_fen == 0:
        issues.append(
            _issue("BUDGET_ZERO", "/content/budget_fen", "预算为 0 分，规则不可能发出任何一张券")
        )
    if budget_fen is not None and coupon_fen is not None and budget_fen < coupon_fen:
        issues.append(
            _issue(
                "BUDGET_BELOW_COUPON",
                "/content/budget_fen",
                f"预算 {budget_fen} 分低于单张券面额 {coupon_fen} 分",
                "WARNING",
            )
        )
    if (
        budget_fen is not None
        and coupon_fen is not None
        and max_per_customer is not None
        and max_per_customer * coupon_fen > budget_fen
    ):
        issues.append(
            _issue(
                "QUOTA_EXCEEDS_BUDGET",
                "/content/max_per_customer",
                f"单人上限 {max_per_customer} 张 × 券面额 {coupon_fen} 分 "
                f"= {max_per_customer * coupon_fen} 分，超出预算 {budget_fen} 分",
                "INFO",
            )
        )
    if _clause_unconfirmed(context.terms, "budget_and_quota"):
        issues.append(
            _issue(
                "BUDGET_CLAUSE_UNCONFIRMED",
                "/terms/budget_and_quota",
                _clause_message("budget_and_quota"),
            )
        )

    cases: list[BoundaryCaseDraft] = []
    starts_at = _iso(content.get("starts_at"))
    min_payment = _min_payment(context)
    if starts_at is not None and budget_fen is not None and coupon_fen is not None:
        cases.append(
            _case(
                case_id="bc-C3-1",
                label="预算刚足",
                template=_COUPON,
                payload=_coupon_case_input(
                    registered_at=starts_at,
                    events=[_payment_event("C3-1", starts_at, min_payment)],
                    initial_budget_used_fen=max(budget_fen - coupon_fen, 0),
                ),
                verification="剩余预算恰够一张，期望发放后预算用尽（原因码 ISSUED）",
            )
        )
        cases.append(
            _case(
                case_id="bc-C3-2",
                label="预算不足",
                template=_COUPON,
                payload=_coupon_case_input(
                    registered_at=starts_at,
                    events=[_payment_event("C3-2", starts_at, min_payment)],
                    initial_budget_used_fen=budget_fen,
                ),
                verification="剩余预算不足一张，期望不发放（原因码 BUDGET_EXHAUSTED）",
            )
        )
    if starts_at is not None and max_per_customer is not None:
        cases.append(
            _case(
                case_id="bc-C3-3",
                label="频次用尽",
                template=_COUPON,
                payload=_coupon_case_input(
                    registered_at=starts_at,
                    events=[_payment_event("C3-3", starts_at, min_payment)],
                    initial_used=max_per_customer,
                ),
                verification="单人次数已用尽，期望不发放（原因码 CUSTOMER_LIMIT）",
            )
        )
    return CheckResult(issues=tuple(issues), boundary_cases=tuple(cases))


def _check_stacking(context: RuleContext) -> CheckResult:
    """C4 · STACKING · coupon · 负责 ``stacking``（design §5.3 C4 ＋ §5.4 反例 6/7）。"""
    issues: list[GateIssue] = []
    if _clause_unconfirmed(context.terms, "stacking"):
        issues.append(
            _issue("STACKING_CLAUSE_UNCONFIRMED", "/terms/stacking", _clause_message("stacking"))
        )
    if context.content.get("stacking") == "ALLOW":
        issues.append(
            _issue(
                "STACKING_ALLOW",
                "/content/stacking",
                "叠加口径为 ALLOW，允许与其他优惠同时生效（记录生效口径，供复查）",
                "INFO",
            )
        )

    cases: list[BoundaryCaseDraft] = []
    starts_at = _iso(context.content.get("starts_at"))
    if starts_at is not None:
        amount = _min_payment(context)
        for case_id, label, applied, verification in (
            (
                "bc-C4-1",
                "互斥命中",
                True,
                "DENY_OTHER_APPLIED 下期望被抑制（原因码 STACK_DENIED）；ALLOW 下期望照常发放",
            ),
            ("bc-C4-2", "叠加放行", False, "无互斥优惠，期望发放（原因码 ISSUED）"),
        ):
            event_id, order_id = _ids(case_id.removeprefix("bc-"), 1)
            cases.append(
                _case(
                    case_id=case_id,
                    label=label,
                    template=_COUPON,
                    payload=_coupon_case_input(
                        registered_at=starts_at,
                        events=[
                            _coupon_event(
                                seq=1,
                                event_id=event_id,
                                order_id=order_id,
                                kind="PAYMENT",
                                at=starts_at,
                                amount_fen=amount,
                                other_offer_applied=applied,
                            )
                        ],
                    ),
                    verification=verification,
                )
            )
    return CheckResult(issues=tuple(issues), boundary_cases=tuple(cases))


def _check_refund(context: RuleContext) -> CheckResult:
    """C5 · REFUND · coupon · 负责 ``refund``（design §5.3 C5 ＋ §5.4 反例 11/12）。"""
    issues: list[GateIssue] = []
    if _clause_unconfirmed(context.terms, "refund"):
        issues.append(
            _issue("REFUND_CLAUSE_UNCONFIRMED", "/terms/refund", _clause_message("refund"))
        )
    if context.content.get("refund_policy") == "RECOMPUTE_UNUSED":
        issues.append(
            _issue(
                "REFUND_RECOMPUTE",
                "/content/refund_policy",
                "退款口径为 RECOMPUTE_UNUSED，退款后需重算并撤回未核销券",
                "INFO",
            )
        )

    cases: list[BoundaryCaseDraft] = []
    starts_at = _iso(context.content.get("starts_at"))
    min_payment = _as_int(context.content.get("min_payment_fen"))
    if starts_at is not None and min_payment is not None:
        if min_payment > 0:
            # 反例 11：``min_payment_fen == 0`` 时**不生成**（design §5.4）。
            first_id, first_order = _ids("C5-1", 1)
            second_id, second_order = _ids("C5-1", 2)
            cases.append(
                _case(
                    case_id="bc-C5-1",
                    label="退款后跌破阈值",
                    template=_COUPON,
                    payload=_coupon_case_input(
                        registered_at=starts_at,
                        events=[
                            _coupon_event(
                                seq=1,
                                event_id=first_id,
                                order_id=first_order,
                                kind="PAYMENT",
                                at=starts_at,
                                amount_fen=min_payment,
                            ),
                            _coupon_event(
                                seq=2,
                                event_id=second_id,
                                order_id=second_order,
                                kind="REFUND",
                                at=starts_at,
                                amount_fen=1,
                            ),
                        ],
                    ),
                    verification=(
                        "净实付回落到门槛以下：RECOMPUTE_UNUSED 下撤回未核销券（REVOKED），"
                        "KEEP 下保持（REFUND_RECORDED）"
                    ),
                )
            )
        paid_id, paid_order = _ids("C5-2", 1)
        used_id, used_order = _ids("C5-2", 2)
        back_id, back_order = _ids("C5-2", 3)
        cases.append(
            _case(
                case_id="bc-C5-2",
                label="已核销退款",
                template=_COUPON,
                payload=_coupon_case_input(
                    registered_at=starts_at,
                    events=[
                        _coupon_event(
                            seq=1,
                            event_id=paid_id,
                            order_id=paid_order,
                            kind="PAYMENT",
                            at=starts_at,
                            amount_fen=min_payment,
                        ),
                        _coupon_event(
                            seq=2,
                            event_id=used_id,
                            order_id=used_order,
                            kind="REDEEM",
                            at=starts_at,
                            amount_fen=0,
                        ),
                        _coupon_event(
                            seq=3,
                            event_id=back_id,
                            order_id=back_order,
                            kind="REFUND",
                            at=starts_at,
                            amount_fen=1,
                        ),
                    ],
                ),
                verification=(
                    "券已核销后退款，期望转人工（USED_COUPON_REVIEW / manual_review=true）"
                ),
            )
        )
    return CheckResult(issues=tuple(issues), boundary_cases=tuple(cases))


def _check_template(context: RuleContext) -> CheckResult:
    """C6 · TEMPLATE · 两个模板 · 集合级（design §5.3 C6；不产出反例）。

    第三行（``compareRules`` 跨模板）**不落 ``RuleCheck``**：它直接翻成 422
    ``VALIDATION_ERROR``、``issues[0].code="TEMPLATE_MISMATCH"``（design §1.11 / §6.4），
    该标签仍登记在 ``CHECK_ISSUE_CODES`` 里以保持 code 面单一出处。
    """
    content = context.content
    template = content.get("template")
    issues: list[GateIssue] = []
    if template not in _TEMPLATE_IDS:
        issues.append(
            _issue("TEMPLATE_UNKNOWN", "/content/template", f"未知规则模板：{template!r}")
        )
    for name, expected in _CONST_BY_TEMPLATE.get(str(template), ()):
        if content.get(name) != expected:
            issues.append(
                _issue(
                    "TEMPLATE_CONST_MISMATCH",
                    f"/content/{name}",
                    f"字段 {name} 的取值偏离契约常量（本文件不实现数值容差判定，A203）",
                )
            )
    return CheckResult(issues=tuple(issues))


def _check_new_customer(context: RuleContext) -> CheckResult:
    """C7 · DATE · coupon · 负责 ``new_customer``（design §5.3 C7 ＋ §5.4 反例 13/14/15）。"""
    content = context.content
    days = _as_int(content.get("new_customer_days"))
    issues: list[GateIssue] = []
    if _clause_unconfirmed(context.terms, "new_customer"):
        issues.append(
            _issue(
                "NEW_CUSTOMER_CLAUSE_UNCONFIRMED",
                "/terms/new_customer",
                _clause_message("new_customer"),
            )
        )
    if days is not None and days <= 0:
        # 契约 ``minimum=1`` 已挡，本条是纵深防御（design §5.3 C7 第二行）。
        issues.append(
            _issue(
                "NEW_CUSTOMER_WINDOW_INVALID",
                "/content/new_customer_days",
                f"新客窗口天数 {days} 非正数，注册时刻起算的新客判定无从成立",
            )
        )

    cases: list[BoundaryCaseDraft] = []
    starts = _as_datetime(content.get("starts_at"))
    amount = _min_payment(context)
    if starts is not None and days is not None:
        at = starts.isoformat()
        recipes = (
            (
                "bc-C7-1",
                "新客未满",
                starts - timedelta(hours=days * 24 - 1),
                f"注册尚未满 {days} 天，期望按新客发放（原因码 ISSUED）",
            ),
            (
                "bc-C7-2",
                "新客已满",
                starts - timedelta(hours=(days + 1) * 24),
                "注册已满，期望不发（原因码 NOT_NEW）",
            ),
            (
                "bc-C7-3",
                "注册时刻在未来",
                starts + timedelta(hours=24),
                "注册时刻晚于事件时刻属无效输入，期望该行返回 Issue 且不形成候选"
                "（原因码 INVALID_EVENT）",
            ),
        )
        for case_id, label, registered_at, verification in recipes:
            cases.append(
                _case(
                    case_id=case_id,
                    label=label,
                    template=_COUPON,
                    payload=_coupon_case_input(
                        registered_at=registered_at.isoformat(),
                        events=[_payment_event(case_id.removeprefix("bc-"), at, amount)],
                    ),
                    verification=verification,
                )
            )
    return CheckResult(issues=tuple(issues), boundary_cases=tuple(cases))


def _check_callback_sequence(context: RuleContext) -> CheckResult:
    """C8 · SEQUENCE · callback · 负责三个必需键（design §5.3 C8 ＋ §5.4 反例 16/17/18）。"""
    issues: list[GateIssue] = []
    for key, code in (
        ("same_day_scope", "SAME_DAY_CLAUSE_UNCONFIRMED"),
        ("priority", "PRIORITY_CLAUSE_UNCONFIRMED"),
        ("daily_cap", "DAILY_CAP_CLAUSE_UNCONFIRMED"),
    ):
        if _clause_unconfirmed(context.terms, key):
            issues.append(_issue(code, f"/terms/{key}", _clause_message(key)))
    if context.content.get("priority") == "APPOINTMENT_FIRST":
        issues.append(
            _issue(
                "PRIORITY_APPOINTMENT_FIRST",
                "/content/priority",
                "优先级口径为 APPOINTMENT_FIRST，先处理已预约组，再按各组 at、seq",
                "INFO",
            )
        )

    cases: list[BoundaryCaseDraft] = []
    daily_cap = _as_int(context.content.get("daily_cap"))
    if daily_cap is not None:
        arrivals = tuple(
            _callback_event(
                seq=seq, event_id=_ids("C8-1", seq)[0], at=_callback_at(seq - 1), appointment=False
            )
            for seq in range(1, daily_cap + 2)
        )
        cases.append(
            _case(
                case_id="bc-C8-1",
                label="同日抢占",
                template=_CALLBACK,
                payload=_callback_case_input(used=0, events=arrivals),
                verification=(
                    f"名额到 daily_cap={daily_cap} 用尽，超出部分期望被抑制（CAP_REACHED）"
                ),
            )
        )
        cases.append(
            _case(
                case_id="bc-C8-2",
                label="频次用尽（回拨）",
                template=_CALLBACK,
                payload=_callback_case_input(used=daily_cap, events=arrivals),
                verification="本轮前已占满名额，期望全部抑制并保留已用值（CAP_REACHED）",
            )
        )
        if context.content.get("priority") == "APPOINTMENT_FIRST":
            # 反例 18：``daily_cap`` 个未预约事件（at 较早）＋ 1 个已预约事件（at 较晚）。
            mixed = [
                _callback_event(
                    seq=seq,
                    event_id=_ids("C8-3", seq)[0],
                    at=_callback_at(seq - 1),
                    appointment=False,
                )
                for seq in range(1, daily_cap + 1)
            ]
            mixed.append(
                _callback_event(
                    seq=daily_cap + 1,
                    event_id=_ids("C8-3", daily_cap + 1)[0],
                    at=_callback_at(daily_cap),
                    appointment=True,
                )
            )
            cases.append(
                _case(
                    case_id="bc-C8-3",
                    label="先已预约组",
                    template=_CALLBACK,
                    payload=_callback_case_input(used=0, events=mixed),
                    verification="期望先处理已预约组，再按各组 at、seq（winner_ids 保留分配顺序）",
                )
            )
    return CheckResult(issues=tuple(issues), boundary_cases=tuple(cases))


def _check_competition(context: RuleContext) -> CheckResult:
    """C9 · COMPETITION · 两个模板 · 无必需键（design §5.3 C9；不产出反例）。

    「多个规则覆盖同一情境」＝同活动下**另一条** ``CONFIRMED`` 版本、同 ``template``、
    且（coupon 时）有效期区间与本版**相交**。只读 ``RuleContext.sibling_confirmed``
    （由 service 从库里只读查出后注入），不查库、不读时钟。

    同一 ``location``（``/content``）只会产出一条：``run_checks`` 按 ``(code, location)``
    去重，多条会互相掩盖，故这里直接对命中的对方 ``rule_id`` 升序取**第一个**写进 message。
    """
    issues: list[GateIssue] = []
    mine_starts = _as_datetime(context.content.get("starts_at"))
    mine_ends = _as_datetime(context.content.get("ends_at"))
    overlapped: list[str] = []
    for sibling in context.sibling_confirmed:
        sibling_id = str(sibling.get("id", ""))
        if not sibling_id or sibling_id == context.rule_id:
            continue
        if str(sibling.get("template", "")) != context.template:
            continue
        if context.template == _COUPON:
            other_starts = _as_datetime(sibling.get("starts_at"))
            other_ends = _as_datetime(sibling.get("ends_at"))
            if (
                mine_starts is None
                or mine_ends is None
                or other_starts is None
                or other_ends is None
            ):
                continue
            if not (mine_starts < other_ends and other_starts < mine_ends):
                continue
        overlapped.append(sibling_id)
    if overlapped:
        overlapped.sort()
        issues.append(
            _issue(
                "RULE_OVERLAP_REVIEW",
                "/content",
                f"同活动下已确认规则 {overlapped[0]} 与本版本同模板且情境相交，请人工复查"
                f"（命中 {len(overlapped)} 条）",
                "WARNING",
            )
        )
    return CheckResult(issues=tuple(issues))


CHECK_IDS: Final[tuple[str, ...]] = tuple(get_args(CheckId))

#: **唯一**注册表（design §5.1）。顺序即 ``run_checks`` 的求值序与 ``issues`` 的稳定排序主序。
CHECKS: Final[tuple[Check, ...]] = (
    Check(
        id="C1",
        category="DATE",
        templates=(_COUPON,),
        spec_ref="architecture/RULES.md「检查活动时间顺序」＋「条款键与无效案例」",
        clause_keys=("time_window",),
        run=_check_window,
    ),
    Check(
        id="C2",
        category="THRESHOLD",
        templates=(_COUPON,),
        spec_ref="architecture/RULES.md「阈值和奖励量」",
        clause_keys=("payment",),
        run=_check_threshold,
    ),
    Check(
        id="C3",
        category="BUDGET",
        templates=(_COUPON,),
        spec_ref="architecture/RULES.md「预算和单人上限」＋「预算低于单张券…可复查告警」",
        clause_keys=("budget_and_quota",),
        run=_check_budget,
    ),
    Check(
        id="C4",
        category="STACKING",
        templates=(_COUPON,),
        spec_ref="architecture/RULES.md「叠加条件」",
        clause_keys=("stacking",),
        run=_check_stacking,
    ),
    Check(
        id="C5",
        category="REFUND",
        templates=(_COUPON,),
        spec_ref="architecture/RULES.md「退款条款」",
        clause_keys=("refund",),
        run=_check_refund,
    ),
    Check(
        id="C6",
        category="TEMPLATE",
        templates=(_COUPON, _CALLBACK),
        spec_ref="architecture/RULES.md「候选同模板」＋切片 ddl.rule_versions 的 template CHECK",
        clause_keys=(),
        run=_check_template,
    ),
    Check(
        id="C7",
        category="DATE",
        templates=(_COUPON,),
        spec_ref="architecture/RULES.md「新客在支付时按注册时刻起不足 new_customer_days×24 小时」",
        clause_keys=("new_customer",),
        run=_check_new_customer,
    ),
    Check(
        id="C8",
        category="SEQUENCE",
        templates=(_CALLBACK,),
        spec_ref="architecture/RULES.md「远程回拨」「事件顺序」「同日抢占与频次用尽」",
        clause_keys=("same_day_scope", "priority", "daily_cap"),
        run=_check_callback_sequence,
    ),
    Check(
        id="C9",
        category="COMPETITION",
        templates=(_COUPON, _CALLBACK),
        spec_ref="architecture/RULES.md「多个规则覆盖同一情境分别给到可复查告警」",
        clause_keys=(),
        run=_check_competition,
    ),
)

# 模块级自证（design §5.1「不多不少」，体例＝``worker/states.py`` 的「9 条不多不少」）：
# 少一条或多一条都判启动期断言失败，重复注册同样判失败（两条合起来才是双射）。
assert len(CHECKS) == len(CHECK_IDS), (
    f"CHECKS 注册了 {len(CHECKS)} 项，与 CheckId 面值 {len(CHECK_IDS)} 不符（design §5.1）"
)
assert len({check.id for check in CHECKS}) == len(CHECKS), "CheckId 重复注册：" + str(
    sorted(check.id for check in CHECKS)
)


def _applicable(context: RuleContext) -> list[tuple[Check, CheckResult]]:
    """按注册序跑**模板命中**的检查项（``templates`` 不含本模板的直接跳过）。"""
    return [(check, check.run(context)) for check in CHECKS if context.template in check.templates]


def run_checks(context: RuleContext) -> CheckResult:
    """跑全部命中的检查项，返回去重且稳定排序后的 ``issues`` 与全部 ``boundary_cases``。

    - **求值序**＝``CHECKS`` 的注册序；
    - **去重键**＝``(code, location)``（design §5.2：同一事实只报一次。§5.3 的归属表已保证
      每个必需键只由一个检查项负责报未确认，去重是纵深防御）；
    - **排序**＝先按注册序、再按检查项内部产出序（稳定、可复跑）；
    - ``boundary_cases`` 与 ``boundary_cases_for(context)`` **逐项相同**（同一份产出，
      两个入口，禁两处各算一遍 —— 本函数直接复用 ``_applicable``）。

    契约上限（``issues`` ≤1000、``boundary_cases`` ≤30）的**组装期断言**在 api 层
    （design §5.2「组装前 assert」）；本函数只保证产出的确定性，超限即 500
    ``INTERNAL_ERROR``，**不是截断**（截断会让「有几个错」不可信）。
    """
    issues: list[GateIssue] = []
    seen: set[tuple[str, str]] = set()
    cases: list[BoundaryCaseDraft] = []
    for _check, result in _applicable(context):
        for issue in result.issues:
            key = (issue.code, issue.location)
            if key in seen:
                continue
            seen.add(key)
            issues.append(issue)
        cases.extend(result.boundary_cases)
    return CheckResult(issues=tuple(issues), boundary_cases=tuple(cases))


def check_state_of(issues: Sequence[GateIssue]) -> RuleCheckState:
    """design §5.2 的判定式：``issues`` 里存在 ``ERROR`` **当且仅当** ``NEEDS_CONFIRMATION``。

    ``WARNING`` / ``INFO`` **不**影响 state（它们是「可复查告警」）。⚠ 本函数返回的是
    ``RuleCheckState``，与 ``RuleVersion.state``（``DRAFT``/``CONFIRMED``）是两个面，禁互相赋值。
    """
    return "NEEDS_CONFIRMATION" if any(item.severity == "ERROR" for item in issues) else "READY"


def boundary_cases_for(context: RuleContext) -> tuple[BoundaryCaseDraft, ...]:
    """design §5.4 的 18 条配方（coupon 15 条 ＋ callback 3 条），按注册序拼接。

    **禁读时钟**：全部时间戳与金额只从 ``context.content`` 推导，故同一规则版本重复调用
    产出**逐字节相同**的反例（S6 钉「两次 GET 的响应体除 ``X-Request-Id`` 外全等」）。
    数量天然不触契约的 30 上限（余量是给 M2-02 扩充用的，本卡不预留占位项）。
    """
    cases: list[BoundaryCaseDraft] = []
    for _check, result in _applicable(context):
        cases.extend(result.boundary_cases)
    return tuple(cases)


# 键表单一来源自检：九项检查声明负责的必需键必须**都在** ``REQUIRED_CLAUSE_KEYS`` 里，
# 且每个必需键**恰由一个**检查项负责（design §5.3 末条的归属表）。
_declared = tuple(key for check in CHECKS for key in check.clause_keys)
assert len(_declared) == len(set(_declared)), f"必需键被多个检查项重复负责：{_declared}"
assert set(_declared) == set(REQUIRED_CLAUSE_KEYS[_COUPON]) | set(
    REQUIRED_CLAUSE_KEYS[_CALLBACK]
), f"检查项的必需键归属与键表不一致：{sorted(set(_declared))}"
