"""``campaignlab.domain.activity``：活动 / 绑定 / 规则版本 / 条款门禁 / 检查项框架（M2-01 · S2a）。

本包是 M2-01 的**领域层**，也是 ``architecture/DOMAIN.md`` 与 ``RULES.md`` 里那批业务规则
（状态机、有效期区间代数、条款键集合、摘要固定投影、九项检查与反例配方、字段差异）的
唯一代码化副本。分包如下：

- ``states.py``    活动 3 条 ＋ 规则版本 4 条迁移表，与四个取值别名（``ActivityStatus`` /
                   ``RuleState`` / ``RuleCheckState`` / ``TemplateId``）的**单一来源**；
                   ``api/common.py`` 反过来 import 并 re-export 这四个别名（design §11.2）。
- ``digests.py``   规则摘要的固定投影（``content`` ＋ 按 key 排序的 ``terms`` ＋
                   ``source_rule_version``；``label`` 与确认说明分别审计，不进摘要）。
- ``clauses.py``   必需条款键集合（``public_frozen`` 面，M2-02/03/04 按此消费）与 G1–G6 门禁。
- ``bindings.py``  绑定有效期区间代数（起含止排；部分重叠即拒，裁定 A198）。
- ``checks.py``    ``checkRule`` 的九项检查注册表与 18 条反例配方（只生成数据与待验证行为文案）。
- ``diff.py``      ``compareRules`` 的字段差异（四类 ``path``，裁定 A201）。

**三条红线**（照 ``application/__init__.py`` 与 ``worker/__init__.py`` 的体例明写，S5 用 AST 守）：

1. **不碰数据库**：本包不含任何 SQL 文本，也没有连接、游标、事务对象；一切数据由调用方
   以 ``Mapping`` / ``Sequence`` / ``date`` 等纯值注入（含 ``registered_evidence_ids`` 与
   ``sibling_confirmed`` 这两个「只读查询结果」）。
2. **不开事务**：事务边界与 ``rowcount`` 判定归 ``application`` 与 ``infra``（design §7.1）；
   本包只给纯函数，非法迁移／非法区间一律抛 ``campaignlab.domain.errors`` 里既有的类，
   **零新增** ``Problem.code``、**零新增** ``DomainError`` 子类。
3. **不取系统时间**：本包任何位置都不读时钟 —— 不取「当前时刻」「当前日期」，也不读
   单调钟。摘要输入、检查上下文、反例时间戳全部由调用方给出，故同一输入必得
   **逐字节相同**的输出（design §5.4）。

分层还有一条：本包**禁 import** ``campaignlab.api`` / ``campaignlab.application`` /
``campaignlab.infra``（``domain`` 是最内层）。``digests.rule_digest`` 与 ``diff.field_changes``
的 ``canonicalize`` 由调用方注入 ``api/common.py::canonical_json``，正是为了既复用**同一份**
规范化实现、又不产生 ``domain → api`` 的运行期导入边。
"""

from __future__ import annotations

from campaignlab.domain.activity.bindings import (
    BINDING_ISSUE_CODES,
    BINDING_SORT_KEY,
    BindingDraft,
    intervals_intersect,
    validate_bindings,
)
from campaignlab.domain.activity.checks import (
    CHECK_IDS,
    CHECK_ISSUE_CODES,
    CHECKS,
    REASON_CODE_GLOSSARY,
    BoundaryCaseDraft,
    Check,
    CheckCategory,
    CheckId,
    CheckResult,
    RuleContext,
    boundary_cases_for,
    check_state_of,
    run_checks,
)
from campaignlab.domain.activity.clauses import (
    ALL_CLAUSE_KEYS,
    CLAUSE_ISSUE_CODES,
    REQUIRED_CLAUSE_KEYS,
    GateIssue,
    confirm_digest_matches,
    evaluate_clause_gate,
    note_satisfies_warnings,
)
from campaignlab.domain.activity.diff import (
    DIFF_PATH_CONTENT_PREFIX,
    DIFF_PATH_LABEL,
    DIFF_PATH_SOURCE_VERSION,
    DIFF_PATH_TERMS_PREFIX,
    FIELD_CHANGE_MAX_LENGTH,
    FieldChangeDraft,
    field_changes,
    render_scalar,
)
from campaignlab.domain.activity.digests import (
    RULE_DIGEST_LENGTH,
    digest_projection,
    rule_digest,
)
from campaignlab.domain.activity.states import (
    ACTIVITY_ISSUE_CODES,
    ACTIVITY_STATES,
    ACTIVITY_TERMINAL_STATES,
    ACTIVITY_TRANSITIONS,
    RULE_STATES,
    RULE_TERMINAL_STATES,
    RULE_TRANSITIONS,
    ActivityStatus,
    ActivityTransition,
    ActivityTransitionId,
    RuleCheckState,
    RuleState,
    RuleTransition,
    RuleTransitionId,
    TemplateId,
    assert_activity_transition_allowed,
    assert_rule_transition_allowed,
    is_activity_terminal,
    is_rule_terminal,
)

__all__ = [
    "ACTIVITY_ISSUE_CODES",
    "ACTIVITY_STATES",
    "ACTIVITY_TERMINAL_STATES",
    "ACTIVITY_TRANSITIONS",
    "ALL_CLAUSE_KEYS",
    "BINDING_ISSUE_CODES",
    "BINDING_SORT_KEY",
    "CHECKS",
    "CHECK_IDS",
    "CHECK_ISSUE_CODES",
    "CLAUSE_ISSUE_CODES",
    "DIFF_PATH_CONTENT_PREFIX",
    "DIFF_PATH_LABEL",
    "DIFF_PATH_SOURCE_VERSION",
    "DIFF_PATH_TERMS_PREFIX",
    "FIELD_CHANGE_MAX_LENGTH",
    "REASON_CODE_GLOSSARY",
    "REQUIRED_CLAUSE_KEYS",
    "RULE_DIGEST_LENGTH",
    "RULE_STATES",
    "RULE_TERMINAL_STATES",
    "RULE_TRANSITIONS",
    "ActivityStatus",
    "ActivityTransition",
    "ActivityTransitionId",
    "BindingDraft",
    "BoundaryCaseDraft",
    "Check",
    "CheckCategory",
    "CheckId",
    "CheckResult",
    "FieldChangeDraft",
    "GateIssue",
    "RuleCheckState",
    "RuleContext",
    "RuleState",
    "RuleTransition",
    "RuleTransitionId",
    "TemplateId",
    "assert_activity_transition_allowed",
    "assert_rule_transition_allowed",
    "boundary_cases_for",
    "check_state_of",
    "confirm_digest_matches",
    "digest_projection",
    "evaluate_clause_gate",
    "field_changes",
    "intervals_intersect",
    "is_activity_terminal",
    "is_rule_terminal",
    "note_satisfies_warnings",
    "render_scalar",
    "rule_digest",
    "run_checks",
    "validate_bindings",
]
