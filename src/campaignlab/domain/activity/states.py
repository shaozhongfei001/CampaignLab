"""活动与规则版本的状态机（M2-01 · S2a；design §3）。

本文件是 design §3.1 / §3.2 两张迁移表的**唯一代码化副本**，体例逐条对齐
``worker/states.py``（``Literal`` 别名 ＋ ``@dataclass(frozen=True, slots=True)`` 的迁移行
＋ ``Final[tuple[…]]`` 注册表 ＋ 纯函数判定），但**不 import** ``campaignlab.worker``
（本卡 ``scope_deny``），也不 import ``campaignlab.api``（domain 层三禁之一）。

四个取值别名（``ActivityStatus`` / ``RuleState`` / ``RuleCheckState`` / ``TemplateId``）住在
领域层而不是 ``api/common.py``：``api/common.py`` 反过来 import 并 re-export 它们
（design §11.2）。这样「契约改枚举 → 代码跟着改」的单一来源落在最内层，且不会产生
``domain → api`` 的运行期导入边（否则本文件与 ``api/common.py`` 直接成环）。

三条红线（照 ``worker/states.py``）：

1. **表外迁移根本不存在**：``ARCHIVED -> *``（活动）、``CONFIRMED`` 上的就地改写／重复确认／
   就地回退（规则）在注册表里没有任何一行，``assert_*_transition_allowed`` 一律抛
   409 ``STATE_CONFLICT``；
2. ``guard`` 是那条写语句的**谓词可读镜像**（体例＝``worker/states.py``：只写谓词与目标列，
   不写语句本体 —— 领域层禁 SQL 文本），供测试与证据文档逐条对照；**运行期只信 ``rowcount``**；
3. 本文件不含 SQL 文本、不开事务、不取系统时间。

``trigger`` 口径（冻结）：调用方传 **operationId**（``createActivity`` / ``updateActivity`` /
``createRule`` / ``updateRule`` / ``confirmRule``），与迁移行 ``trigger`` 字段的**前缀**匹配。
这一维不是装饰：``R4``（``CONFIRMED -> DRAFT``、``creates_new_row=True``，语义是「以已确认
版本为父新建草稿」）与 design §3.2 明写「在表里**不存在**」的「就地回退／撤确认」在
``(source, target)`` 上完全同形，只有 ``trigger`` 能把二者分开。

细因标签的落点：domain 层禁 import ``api``，故本文件抛出的 ``StateConflict`` 只带 design 冻结的
``detail``（体例＝``worker/states.py::assert_transition_allowed`` 同样只抛 detail）；
``issues[0].code`` / ``issues[0].location`` 由 api／service 层按 ``ACTIVITY_ISSUE_CODES`` 与
design §3.1 / §3.2 的逐条映射附加。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, get_args

from campaignlab.domain.errors import StateConflict

__all__ = [
    "ACTIVITY_ISSUE_CODES",
    "ACTIVITY_STATES",
    "ACTIVITY_TERMINAL_STATES",
    "ACTIVITY_TRANSITIONS",
    "RULE_STATES",
    "RULE_TERMINAL_STATES",
    "RULE_TRANSITIONS",
    "ActivityStatus",
    "ActivityTransition",
    "ActivityTransitionId",
    "RuleCheckState",
    "RuleState",
    "RuleTransition",
    "RuleTransitionId",
    "TemplateId",
    "assert_activity_transition_allowed",
    "assert_rule_transition_allowed",
    "is_activity_terminal",
    "is_rule_terminal",
]

#: 活动状态。取值逐字对齐活契约 ``components.schemas.Activity.properties.status.enum``
#: （实测 ``["OPEN", "ARCHIVED"]``）与切片 ``ddl.activities`` 的 CHECK 两值。
ActivityStatus = Literal["OPEN", "ARCHIVED"]

#: 规则版本状态。取值＝``components.schemas.RuleVersion.properties.state.enum``
#: （``["DRAFT", "CONFIRMED"]``）。**与 ``api/common.py::JobState`` 同名不同物，禁复用**。
RuleState = Literal["DRAFT", "CONFIRMED"]

#: ``checkRule`` 的**检查结论**态（``components.schemas.RuleCheck.properties.state.enum``）。
#: ⚠ design §5.2 的命名陷阱：本态与 ``RuleVersion.state``、与 ``listRules`` 的 ``status``
#: **查询参数**是三个互不相同的面，取值集合不同，禁互相赋值。
RuleCheckState = Literal["READY", "NEEDS_CONFIRMATION"]

#: 规则模板。取值＝``components.schemas.CouponRule.properties.template.const`` 与
#: ``.CallbackRule.properties.template.const``，与切片 ``ddl.rule_versions`` 的 CHECK 逐字一致。
TemplateId = Literal["coupon_threshold", "callback_priority"]

#: 2 个活动状态。取值一律由 ``get_args`` 从契约别名反推，**禁抄字面量**
#: （体例＝``worker/states.py::JOB_STATES``）。
ACTIVITY_STATES: Final[tuple[str, ...]] = tuple(get_args(ActivityStatus))
#: 2 个规则版本状态（同上口径）。
RULE_STATES: Final[tuple[str, ...]] = tuple(get_args(RuleState))

#: 活动终态：归档后**读取不受限**、写入一律 409（design §3.1）。
ACTIVITY_TERMINAL_STATES: Final[frozenset[str]] = frozenset({"ARCHIVED"})
#: 规则终态：语义是「内容冻结」，但 ``R4`` 允许**从终态派生新草稿行**（design §3.2）。
RULE_TERMINAL_STATES: Final[frozenset[str]] = frozenset({"CONFIRMED"})

#: design §3.1 的细因标签（``Issue.code`` 面，**不是** ``Problem.code``；ADR-005 §2.1）。
#: 归档后的任何写操作（含重复归档、复活、以及活动归档后建／改／确认规则）共用这一个标签，
#: 靠 ``location`` 区分是「改活动自身」还是「动它下面的规则」。
ACTIVITY_ISSUE_CODES: Final[tuple[str, ...]] = ("ACTIVITY_ARCHIVED",)

#: design §3.1 冻结的 detail 原文（归档后写操作一律这一句）。
_ACTIVITY_ARCHIVED_DETAIL: Final = "活动已归档，不可再修改"
#: design §3.2 冻结的 detail 原文（试编辑已确认版本）。
_RULE_CONFIRMED_DETAIL: Final = "已确认版本不可修改，请以其为父版本新建草稿"

ActivityTransitionId = Literal["A1", "A2", "A3"]
RuleTransitionId = Literal["R1", "R2", "R3", "R4"]


@dataclass(frozen=True, slots=True)
class ActivityTransition:
    """活动迁移表的一行（字段名与 ``worker/states.py::Transition`` 逐字对齐）。

    ``sources`` 是**集合**：空元组表示「新建」（``A1`` 没有源行）。``guard`` 是那条写语句的
    谓词／目标列**可读镜像**，``transaction`` 是 design §7.1 的事务号与落点方法名 ——
    两者供测试与证据文档逐条对照，不参与运行期决策。
    """

    id: ActivityTransitionId
    sources: tuple[str, ...]
    target: str
    trigger: str
    spec_ref: str
    guard: str
    transaction: str


@dataclass(frozen=True, slots=True)
class RuleTransition:
    """规则版本迁移表的一行（比活动面多一个 ``creates_new_row``，体例＝``T9``）。"""

    id: RuleTransitionId
    sources: tuple[str, ...]
    target: str
    trigger: str
    spec_ref: str
    guard: str
    transaction: str

    #: ``R4`` 的 ``target`` 落在**新行**上（以 ``parent_rule_id`` 建新草稿），源行一字不改。
    creates_new_row: bool = False


ACTIVITY_TRANSITIONS: Final[tuple[ActivityTransition, ...]] = (
    ActivityTransition(
        id="A1",
        sources=(),
        target="OPEN",
        trigger="createActivity 建活动（新建即 OPEN，DDL 无默认值 ⇒ service 显式写）",
        spec_ref="architecture/DOMAIN.md「对象与修改」：活动及绑定「OPEN → ARCHIVED」",
        guard="新建行初值 status='OPEN', revision=1",
        transaction="TX-A1 ActivityService.create_activity",
    ),
    ActivityTransition(
        id="A2",
        sources=("OPEN",),
        target="ARCHIVED",
        trigger='updateActivity 且 status="ARCHIVED"',
        spec_ref="architecture/DOMAIN.md「对象与修改」：活动及绑定「OPEN → ARCHIVED」",
        guard=(
            "目标列 status='ARCHIVED', revision=revision+1；"
            "谓词 status='OPEN' AND revision=:revision"
        ),
        transaction="TX-A2 ActivityService.update_activity",
    ),
    ActivityTransition(
        id="A3",
        sources=("OPEN",),
        target="OPEN",
        trigger="updateActivity 改 name/description/bindings（status 缺省或仍为 OPEN）",
        spec_ref="architecture/API.md「更新」：PATCH 只覆盖给出的字段",
        guard=(
            "目标列 name/description/bindings 与 revision=revision+1（status 列不参与）；"
            "谓词 status='OPEN' AND revision=:revision"
        ),
        transaction="TX-A2 ActivityService.update_activity（同一方法）",
    ),
)


RULE_TRANSITIONS: Final[tuple[RuleTransition, ...]] = (
    RuleTransition(
        id="R1",
        sources=(),
        target="DRAFT",
        trigger="createRule，parent_rule_id 缺省",
        spec_ref="architecture/DOMAIN.md「规则版本」：DRAFT 可修改",
        guard="新建行初值 state='DRAFT', revision=1, confirmed_at=NULL, confirmation=NULL",
        transaction="TX-R1 RuleService.create_rule",
    ),
    RuleTransition(
        id="R2",
        sources=("DRAFT",),
        target="DRAFT",
        trigger="updateRule（改 label / content / terms）",
        spec_ref=(
            "architecture/DOMAIN.md「规则版本」：DRAFT 可修改 ＋ architecture/API.md「更新」"
        ),
        guard=(
            "目标列 label/content_json/terms_json/digest 与 revision=revision+1；"
            "谓词 state='DRAFT' AND revision=:revision"
        ),
        transaction="TX-R2 RuleService.update_rule",
    ),
    RuleTransition(
        id="R3",
        sources=("DRAFT",),
        target="CONFIRMED",
        trigger="confirmRule（条款门禁 §4.2 ＋ 摘要匹配全过）",
        spec_ref=(
            "architecture/DOMAIN.md「CONFIRMED 固定字段和条款」；"
            "architecture/RULES.md「条款键与无效案例」"
        ),
        guard=(
            "目标列 state='CONFIRMED', confirmed_at=:now, confirmation=:note, "
            "digest=:digest, revision=revision+1；"
            "谓词 state='DRAFT' AND revision=:revision AND digest=:digest"
        ),
        transaction="TX-R3 RuleService.confirm_rule",
    ),
    RuleTransition(
        id="R4",
        sources=("CONFIRMED",),
        target="DRAFT",
        trigger="createRule 且 parent_rule_id = 某 CONFIRMED 版本",
        spec_ref="architecture/DOMAIN.md：变动时以 parent_rule_id 建新草稿",
        guard="新建行初值 state='DRAFT', parent_rule_id=:parent, revision=1；父行一字不改",
        transaction="TX-R1 RuleService.create_rule（同方法，仅多带 parent_rule_id）",
        creates_new_row=True,
    ),
)


def is_activity_terminal(state: str) -> bool:
    """``state`` 是否活动终态。终态活动的任何写操作都必然 ``rowcount == 0``。"""
    return state in ACTIVITY_TERMINAL_STATES


def is_rule_terminal(state: str) -> bool:
    """``state`` 是否规则终态（内容冻结）。

    终态**不可就地再迁移**，但可由 ``R4`` 派生新草稿行 —— 二者不矛盾
    （``creates_new_row=True`` 的 ``target`` 落在新行上）。
    """
    return state in RULE_TERMINAL_STATES


def _require_trigger(trigger: str) -> None:
    """``trigger`` 必须是 operationId：空串会匹配到全部迁移行，等于把守卫掏空。"""
    if not trigger:
        raise ValueError("trigger 必须是 operationId（如 'updateActivity'），不得为空串")


def assert_activity_transition_allowed(source: str | None, target: str, *, trigger: str) -> None:
    """校验 ``source -> target`` 在 design §3.1 的 3 条迁移内（``source=None`` 表示新建）。

    不在表内即抛 409 ``STATE_CONFLICT``。**终态唯一**由此得到双重保证：一是
    ``ACTIVITY_TRANSITIONS`` 里没有任何一行的 ``sources`` 含 ``ARCHIVED``，二是本函数对
    终态出边一律抛错；于是「归档与并发改写争用」时后到者既改不动行（谓词写 ``rowcount == 0``），
    也过不了这道纯函数校验。

    归档后**读取不受限**（``getActivity`` / ``listActivities`` / ``getRule`` / ``listRules`` /
    ``checkRule`` / ``compareRules`` 照常 200），本函数只服务写路径。
    """
    _require_trigger(trigger)
    if source is not None and source not in ACTIVITY_STATES:
        raise StateConflict(f"未知的活动状态：{source!r}")
    if target not in ACTIVITY_STATES:
        raise StateConflict(f"未知的目标状态：{target!r}")
    matched = tuple(
        row
        for row in ACTIVITY_TRANSITIONS
        if row.target == target
        and row.trigger.startswith(trigger)
        and (source in row.sources if source is not None else not row.sources)
    )
    if matched:
        return
    if source == "ARCHIVED":
        # design §3.1：归档后再 PATCH 任何字段（含重复归档）与归档后复活都走这一句固定 detail。
        raise StateConflict(_ACTIVITY_ARCHIVED_DETAIL)
    raise StateConflict(
        f"迁移表内不存在 {source} -> {target}"
        f"（trigger={trigger}；design §3.1 共 {len(ACTIVITY_TRANSITIONS)} 条）"
    )


def assert_rule_transition_allowed(source: str | None, target: str, *, trigger: str) -> None:
    """校验 ``source -> target`` 在 design §3.2 的 4 条迁移内（``source=None`` 表示新建）。

    与活动面同形，多一条 ``trigger`` 维度的必要性说明：``R4`` 与「就地撤确认」同为
    ``CONFIRMED -> DRAFT``，靠 ``trigger`` 前缀（``createRule`` vs 其它 op）区分 ——
    design §3.2 明写就地回退／撤确认「在表里**不存在**」（契约也没有 ``unconfirmRule`` op）。

    三类非法面（细因标签由 api／service 层附加，见模块 docstring）：
    ``CONFIRMED --updateRule--> *``（试编辑）、``CONFIRMED --confirmRule--> CONFIRMED``
    （重复确认）、``CONFIRMED -> DRAFT`` 的就地回退。
    """
    _require_trigger(trigger)
    if source is not None and source not in RULE_STATES:
        raise StateConflict(f"未知的规则版本状态：{source!r}")
    if target not in RULE_STATES:
        raise StateConflict(f"未知的目标状态：{target!r}")
    matched = tuple(
        row
        for row in RULE_TRANSITIONS
        if row.target == target
        and row.trigger.startswith(trigger)
        and (source in row.sources if source is not None else not row.sources)
    )
    if matched:
        return
    if source == "CONFIRMED" and trigger == "updateRule":
        raise StateConflict(_RULE_CONFIRMED_DETAIL)
    raise StateConflict(
        f"迁移表内不存在 {source} -> {target}"
        f"（trigger={trigger}；design §3.2 共 {len(RULE_TRANSITIONS)} 条）"
    )
