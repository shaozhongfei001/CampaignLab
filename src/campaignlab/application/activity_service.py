"""活动 / 规则版本用例服务（M2-01 · S2b-1；design §1 / §2 / §3 / §4 / §6 / §7）。

职责严格限于「用例编排 ＋ 事务边界」（``application/__init__.py`` 的分层说明）：
SQL 一律下沉到 ``infra/db/repositories.py``（A81「SQL 写点唯一」），响应组装留给
``api/activities.py``（S3）与 ``api/rules.py``（S4）。本文件返回 DTO / 纯数据结果，
**不返回 ``Response``** —— application 层一旦开始造 HTTP 响应，就会和路由层各持一份
状态码与头字段口径（体例＝``application/workspace_service.py``）。

四条口径直接照抄 design，禁在本层重新论证：

- **判定顺序**（§6.3）：形参级校验 → 会话 → ``Idempotency-Key`` → 正文 → 开事务读当前行（404）
  → **幂等重放** → ``If-Match``（428/412）→ 状态机（409）→ 业务门禁（422/409）→ 写＋审计＋幂等登记。
  「先幂等、后 If-Match」是 ``API.md`` 的明文顺序，故同键同体的重放会回放**原**结果而不再判 412。
- **事务**（§7.1）：一方法一短事务、``BEGIN IMMEDIATE``（``conn.begin()``）、业务写入与审计同事务，
  被拒的写请求不留半成品；只读面（``get_*`` / ``list_*`` / ``check_rule`` / ``compare_rules``）
  单连接、不开显式事务。
- **游标**（§1.1 / §1.5）：复用 ``workspace_service.py::load_cursor_secret`` 的那**一把**密钥与
  ``BAD_CURSOR_DETAIL`` 的那**一句** detail —— 换密钥会让已发出的游标瞬间失效，第二句 detail
  会让措辞差异变成探测游标结构的 oracle。
- **显式时钟**（§7.5）：``created_at`` / ``confirmed_at`` / ``audit.at`` 全取注入的 ``Clock``；
  本模块不出现任何取系统当前时刻的调用，也不 import 时钟以外的时间源
  （``tests/unit/test_clock.py`` 是**按源文本正则**扫 ``src/`` 的，连 docstring 里的字面量都判红，
  D-045 实测踩过 ⇒ 此处刻意以描述代替字面量）。

分层：``application → api.common`` / ``application → infra.db`` / ``application → domain``
都是既有正向边（``workspace_service.py`` 同型，design §11.3 已实测确认，禁自行怀疑）。
本模块**禁** import ``campaignlab.api.deps``（端口在 deps，实现在这里，反向即成环）。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final, cast

from sqlalchemy import Connection, Engine
from sqlalchemy.exc import IntegrityError

from campaignlab.api.common import (
    Activity,
    ActivityCreate,
    ActivityPage,
    ActivityUpdate,
    Binding,
    BoundaryCase,
    Confirmation,
    DomainError,
    FieldChange,
    InternalFailure,
    Issue,
    ResourceNotFound,
    RuleCheck,
    RuleCreate,
    RuleDiff,
    RuleUpdate,
    RuleVersion,
    RuleVersionPage,
    Session,
    StateConflict,
    ValidationFailure,
    canonical_json,
    check_if_match,
    decode_cursor,
    encode_cursor,
    etag,
    idempotency_envelope,
    request_digest,
    validate_idempotency_key,
)
from campaignlab.application.audit import OUTCOME_ACCEPTED, AuditWriter
from campaignlab.application.idempotency import IdempotencyGuard, IdempotencyKey
from campaignlab.application.workspace_service import (
    BAD_CURSOR_DETAIL,
    audit_role_of,
    load_cursor_secret,
)
from campaignlab.clock import Clock
from campaignlab.config import API_PREFIX, AppConfig
from campaignlab.domain.activity import (
    ACTIVITY_STATES,
    ACTIVITY_TRANSITIONS,
    FIELD_CHANGE_MAX_LENGTH,
    RULE_STATES,
    RULE_TERMINAL_STATES,
    RULE_TRANSITIONS,
    BindingDraft,
    GateIssue,
    RuleContext,
    assert_activity_transition_allowed,
    assert_rule_transition_allowed,
    check_state_of,
    confirm_digest_matches,
    digest_projection,
    evaluate_clause_gate,
    field_changes,
    is_activity_terminal,
    is_rule_terminal,
    note_satisfies_warnings,
    rule_digest,
    run_checks,
    validate_bindings,
)
from campaignlab.domain.ids import new_resource_id
from campaignlab.infra.db.engine import connect
from campaignlab.infra.db.repositories import (
    ActivityBindingRepository,
    ActivityRecord,
    ActivityRepository,
    BindingRecord,
    IdempotencyRecord,
    RuleVersionRecord,
    RuleVersionRepository,
    _iso,
)

__all__ = [
    "ACTION_ACTIVITY_ARCHIVED",
    "ACTION_ACTIVITY_CREATED",
    "ACTION_ACTIVITY_UPDATED",
    "ACTION_RULE_CONFIRMED",
    "ACTION_RULE_CONTENT_UPDATED",
    "ACTION_RULE_DRAFT_CREATED",
    "ACTION_RULE_LABEL_UPDATED",
    "ACTION_RULE_SUCCESSOR_DRAFT_CREATED",
    "ACTIVITIES_CURSOR_VERSION",
    "ACTIVITY_ID_PREFIX",
    "ARCHIVED_DETAIL",
    "DIGEST_MISMATCH_DETAIL",
    "DUPLICATE_EXTERNAL_DETAIL",
    "EMPTY_PATCH_DETAIL",
    "IMMUTABLE_DETAIL",
    "NOTE_REQUIRED_DETAIL",
    "RULE_ID_PREFIX",
    "TARGET_KIND_ACTIVITY",
    "TARGET_KIND_RULE",
    "ActivityCreateOutcome",
    "ActivityService",
    "ActivityWriteOutcome",
    "RuleService",
    "RuleWriteOutcome",
    "activity_query_digest",
    "rule_query_digest",
]

#: design §7.3：``audit.action`` 的八个取值。``AuditWriter.write(action=…)`` 收 ``str``，
#: 故这些常量定义在本模块而**不是** ``application/audit.py``（该文件禁改，design §11.3）。
ACTION_ACTIVITY_CREATED: Final = "ACTIVITY_CREATED"
ACTION_ACTIVITY_UPDATED: Final = "ACTIVITY_UPDATED"
ACTION_ACTIVITY_ARCHIVED: Final = "ACTIVITY_ARCHIVED"
ACTION_RULE_DRAFT_CREATED: Final = "RULE_DRAFT_CREATED"
ACTION_RULE_SUCCESSOR_DRAFT_CREATED: Final = "RULE_SUCCESSOR_DRAFT_CREATED"
ACTION_RULE_CONTENT_UPDATED: Final = "RULE_CONTENT_UPDATED"
ACTION_RULE_LABEL_UPDATED: Final = "RULE_LABEL_UPDATED"
ACTION_RULE_CONFIRMED: Final = "RULE_CONFIRMED"

#: design §7.3：``audit.target_kind`` 取 ``"activity"`` / ``"rule"``
#: （两者都在 ``api/common.py::ObjectKind`` 的 Literal 里）。
TARGET_KIND_ACTIVITY: Final = "activity"
TARGET_KIND_RULE: Final = "rule"

#: design §7.5：ID 前缀（``domain/ids.py::new_resource_id`` 的既有生成器）。
ACTIVITY_ID_PREFIX: Final = "act"
RULE_ID_PREFIX: Final = "rul"

#: design §6.4「空 PATCH」：``exclude_unset`` 后为空 → 422，detail 固定这一句。
EMPTY_PATCH_DETAIL: Final = "PATCH 正文至少给出一个字段"
#: design §3.1「归档后修改」与 §3.1 末条「聚合终态的连带面」共用这一句。
#: 文本必须与 ``domain/activity/states.py`` 抛出的那句**逐字相同**（守护对撞，禁第二句）。
ARCHIVED_DETAIL: Final = "活动已归档，不可再修改"
#: design §3.2「试编辑已确认版本」；同样是领域层那句的镜像。
IMMUTABLE_DETAIL: Final = "已确认版本不可修改，请以其为父版本新建草稿"
#: design §4.2 第 6 条：**禁回显两个摘要值**（回显等于给客户端一个「服务端存了哪一版」的探针）。
DIGEST_MISMATCH_DETAIL: Final = "确认摘要与当前规则内容不一致，请重新读取后再确认"
#: design §4.2 第 8 条。
NOTE_REQUIRED_DETAIL: Final = "存在需审核备注的警告，请在确认备注中记录判断"
#: design §6.4「同银行外部活动号重复」（AC-002「明确定位」）。
DUPLICATE_EXTERNAL_DETAIL: Final = "同一银行下外部活动号已存在"

#: 游标 payload 的版本号（design §1.1）。活动面与规则面共用同一个版本号：
#: 两者的 payload 靠**查询摘要**区分（``rule_query_digest`` 多绑一个 ``activity_id``），
#: 而不是靠第二个版本号——第二把版本只会让「跨资源复用游标」多一条需要各自维护的判据。
ACTIVITIES_CURSOR_VERSION: Final = 1

#: 查询摘要长度（与 ``workspace_service.CURSOR_QUERY_DIGEST_HEX`` 同值同义）。
_QUERY_DIGEST_HEX: Final = 16
#: ``audit.outcome`` 的第二个合法值（DDL CHECK 三值之一）。``application/audit.py`` 只导出
#: ``OUTCOME_ACCEPTED`` 且禁改 ⇒ 本模块自备这一个字面量（design §7.3 的 DENIED 面）。
_OUTCOME_DENIED: Final = "DENIED"
#: 幂等四元组里的 ``operation`` 取 operationId 字面量（design §7.5）。
#: 同时用作 ``assert_*_transition_allowed`` 的 ``trigger``（迁移表按 operationId 前缀匹配）。
_OPERATION_CREATE_ACTIVITY: Final = "createActivity"
_OPERATION_UPDATE_ACTIVITY: Final = "updateActivity"
_OPERATION_CREATE_RULE: Final = "createRule"
_OPERATION_UPDATE_RULE: Final = "updateRule"
_OPERATION_CONFIRM_RULE: Final = "confirmRule"
#: design §6.4：``status`` 含未知态名或空 token → ``issues[0].location``。
_STATUS_LOCATION: Final = "/query/status"
#: design §6.4：空 PATCH → ``issues[0]``。
_EMPTY_PATCH_CODE: Final = "EMPTY_PATCH"
_ROOT_LOCATION: Final = "/"
#: design §3.2：父版本仍是草稿。
_PARENT_NOT_CONFIRMED_CODE: Final = "PARENT_NOT_CONFIRMED"
_PARENT_LOCATION: Final = "/parent_rule_id"
_ACTIVITY_LOCATION: Final = "/activity_id"
_STATUS_FIELD_LOCATION: Final = "/status"
#: design §6.4：同银行外部活动号重复的两条 ``issues`` 的细因标签与 location。
_DUPLICATE_EXTERNAL_CODE: Final = "DUPLICATE_EXTERNAL_ACTIVITY"
_BANK_LOCATION: Final = "/bank_id"
_EXTERNAL_LOCATION: Final = "/external_activity_id"
#: design §4.2 第 6 条。
_DIGEST_MISMATCH_CODE: Final = "CONFIRMATION_DIGEST_MISMATCH"
_DIGEST_LOCATION: Final = "/digest"
_NOTE_LOCATION: Final = "/note"
#: design §4.2 第 5 条。
_SCHEMA_VERSION_CODE: Final = "SCHEMA_VERSION_UNSUPPORTED"
_SCHEMA_VERSION_LOCATION: Final = "/content/schema_version"
#: design §1.1 / §6.4：``compareRules`` 跨模板。
_TEMPLATE_MISMATCH_CODE: Final = "TEMPLATE_MISMATCH"
_CANDIDATE_LOCATION: Final = "/query/candidate_rule_id"
#: design §6.5：条款整条新增／删除时 ``FieldChange`` 的长度上限自检（超限 → 500，禁截断）。
_ERROR_SEVERITY: Final = "ERROR"


class _Replay(Exception):
    """内部控制流：事务内发现幂等键已被并发请求占用，需要**回滚**本次写入后重放。

    照 ``application/workspace_service.py::_Replay`` 的同名类（design §6.3 第 10 条：
    禁改成裸「先查后插」）。用异常而不是返回值，是因为此刻已经写入了业务行与审计行，
    只有让 ``conn.begin()`` 的上下文管理器看到异常才会回滚。
    """

    __slots__ = ("record",)

    def __init__(self, record: IdempotencyRecord) -> None:
        super().__init__("幂等重放")
        self.record = record


@dataclass(frozen=True, slots=True)
class ActivityCreateOutcome:
    """``createActivity`` 的结果：新建与幂等重放共用一个形状（体例＝``WorkspaceCreateOutcome``）。

    刻意**不含** ``X-Request-Id``：重放时它必须重新生成（design §1.2），由路由层覆盖。
    """

    status: int
    headers: dict[str, str]
    body: dict[str, Any]
    replayed: bool

    def as_envelope(self) -> dict[str, Any]:
        """还原成 ``api.common.replay_from_envelope`` 能直接吃的信封。"""
        return {"status": self.status, "headers": dict(self.headers), "body": self.body}


@dataclass(frozen=True, slots=True)
class ActivityWriteOutcome:
    """``updateActivity`` 的结果（200 ＋ ``ETag``；design §1.4）。字段序与 create 面逐字相同。"""

    status: int
    headers: dict[str, str]
    body: dict[str, Any]
    replayed: bool

    def as_envelope(self) -> dict[str, Any]:
        """还原成 ``api.common.replay_from_envelope`` 能直接吃的信封。"""
        return {"status": self.status, "headers": dict(self.headers), "body": self.body}


@dataclass(frozen=True, slots=True)
class RuleWriteOutcome:
    """``createRule`` / ``updateRule`` / ``confirmRule`` 三个写 op 共用的结果形状。

    三者都是「一个 ``RuleVersion`` ＋ ``ETag``」，差别只在状态码（201 / 200 / 200），
    故共用一个 Outcome；``status`` 字段承载这个差别，禁在路由层再判一次 op 类型。
    """

    status: int
    headers: dict[str, str]
    body: dict[str, Any]
    replayed: bool

    def as_envelope(self) -> dict[str, Any]:
        """还原成 ``api.common.replay_from_envelope`` 能直接吃的信封。"""
        return {"status": self.status, "headers": dict(self.headers), "body": self.body}


#: design §6.4：``status`` 含未知态名或空 token 的细因标签。
_STATUS_UNKNOWN_CODE: Final = "STATUS_UNKNOWN"
#: design §3.1 / §6.4：状态机细因标签。
_ACTIVITY_ARCHIVED_CODE: Final = "ACTIVITY_ARCHIVED"
_RULE_IMMUTABLE_CODE: Final = "RULE_CONFIRMED_IMMUTABLE"
_RULE_ALREADY_CONFIRMED_CODE: Final = "RULE_ALREADY_CONFIRMED"


def _replayed_parts(record: IdempotencyRecord) -> tuple[int, dict[str, str], dict[str, Any]]:
    """``idempotency`` 行 → ``(status, headers, body)``（体例＝``workspace_service._outcome_of``）。

    三个 Outcome 的字段序逐字相同，故信封拆解只写这**一份**；``response_status`` 与信封
    ``status`` 同值并**以列为准**（design §2 的既有裁定）。重放时 ``X-Request-Id`` 不在这里，
    由路由层用本次请求的值覆盖。
    """
    envelope = record.envelope()
    raw_headers = envelope.get("headers") or {}
    headers = (
        {str(name): str(value) for name, value in raw_headers.items()}
        if isinstance(raw_headers, Mapping)
        else {}
    )
    raw_body = envelope.get("body")
    body = cast(dict[str, Any], raw_body if isinstance(raw_body, Mapping) else {})
    return record.response_status, headers, body


def activity_query_digest(
    *, workspace_id: str, limit: int, q: str | None, status: str | None
) -> str:
    """``listActivities`` 游标里绑定的查询摘要（design §1.1 的 ``q`` 字段）。

    绑定**全部**筛选条件：翻页途中改了筛选却继续用旧游标必须判 400，否则会把两种不同
    查询的结果拼成一条看似连续的列表。规范化用 ``api.common.canonical_json`` 的那一份。
    """
    raw = canonical_json(
        {"workspace_id": workspace_id, "limit": limit, "q": q, "status": status}
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:_QUERY_DIGEST_HEX]


def rule_query_digest(
    *,
    workspace_id: str,
    activity_id: str,
    limit: int,
    q: str | None,
    status: str | None,
) -> str:
    """``listRules`` 的查询摘要（design §1.5）。

    **必须**含 ``activity_id``：否则跨活动复用同一个游标不会被判 400，两个活动的规则列表
    会被拼成一条看似连续的翻页。
    """
    raw = canonical_json(
        {
            "workspace_id": workspace_id,
            "activity_id": activity_id,
            "limit": limit,
            "q": q,
            "status": status,
        }
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:_QUERY_DIGEST_HEX]


def _cursor_payload(
    *, actor_id: str, query_digest: str, created_at: str, resource_id: str
) -> dict[str, Any]:
    """游标载荷（design §1.1）。活动面与规则面共用同一形状，靠 ``query_digest`` 区分。"""
    return {
        "v": ACTIVITIES_CURSOR_VERSION,
        "q": query_digest,
        "k": [created_at, resource_id],
        "s": actor_id,
    }


def _cursor_key(cursor: str, *, secret: bytes, actor_id: str, query_digest: str) -> tuple[str, str]:
    """解游标并校验绑定；任何一项不符 → 400 ``BAD_CURSOR``（**同一句** detail）。

    四条判据与 ``WorkspaceService._cursor_key`` 逐条同形（版本 / 查询摘要 / actor / ``k`` 形状），
    且共用 ``workspace_service.BAD_CURSOR_DETAIL`` 与 ``load_cursor_secret`` 的那一把密钥
    —— design §11.3 明写「禁第二把密钥、禁第二句 detail」。换 actor 也判 400 而不是 403：
    游标本身是不可信输入，用状态码区分「签名错」与「不是你的」等于给出探测面。
    """
    payload = decode_cursor(cursor, secret)
    if not isinstance(payload, Mapping):
        raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
    if payload.get("v") != ACTIVITIES_CURSOR_VERSION:
        raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
    if payload.get("q") != query_digest:
        raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
    if payload.get("s") != actor_id:
        raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
    key = payload.get("k")
    if (
        not isinstance(key, list)
        or len(key) != 2
        or not isinstance(key[0], str)
        or not isinstance(key[1], str)
    ):
        raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
    return (key[0], key[1])


def _parse_status(status: str | None, allowed: tuple[str, ...]) -> list[str] | None:
    """``status`` 逗号分隔多值 → 状态名列表；``None`` 表示不筛（design §1.1 / §1.5）。

    白名单一律 ``allowed`` 实取（``ACTIVITY_STATES`` / ``RULE_STATES``，两者都由
    ``tuple(get_args(<Literal 别名>))`` 从活契约 DTO 反推），**禁抄字面量**。
    任何一段不在白名单里（含空段，例如 ``"OPEN,"``）→ 422 ``VALIDATION_ERROR``：
    静默忽略未知态名会让「筛了一个不存在的状态」返回空页，看起来像库里真没有数据。
    重复段去重但**保序**（``dict.fromkeys``），体例＝``worker/service.py::_parse_status``。
    """
    if status is None:
        return None
    names = status.split(",")
    for name in names:
        if name not in allowed:
            raise ValidationFailure(
                f"status 含未注册的状态名：{name!r}",
                issues=[
                    Issue(
                        code=_STATUS_UNKNOWN_CODE,
                        location=_STATUS_LOCATION,
                        message=f"未知状态名 {name!r}",
                        severity=_ERROR_SEVERITY,
                    )
                ],
            )
    return list(dict.fromkeys(names))


def _activity_dto(
    record: ActivityRecord,
    *,
    bindings: list[BindingRecord],
    rule_ids: list[str],
    receipt_ids: list[str],
) -> Activity:
    """``activities`` 行 ＋ 三张从表的批量投影 → 活契约 ``Activity``（design §2.4 / §7.4）。

    走 ``model_validate`` 而不是逐字段构造：DTO 是**活契约**的镜像，让 pydantic 再校验一遍
    等于免费拿到「列取值漂移」的早期失败，且不需要对 ``status`` 做 ``cast``。
    """
    payload: dict[str, Any] = {
        "id": record.id,
        "revision": record.revision,
        "created_at": record.created_at,
        "name": record.name,
        "bank_id": record.bank_id,
        "external_activity_id": record.external_activity_id,
        "description": record.description,
        "status": record.status,
        "current_rule_id": record.current_rule_id,
        "bindings": [
            {
                "strategy_id": item.strategy_id,
                "source_version": item.source_version,
                "valid_from": item.valid_from,
                "valid_until": item.valid_until,
                "evidence_id": item.evidence_id,
            }
            for item in bindings
        ],
        "rule_ids": list(rule_ids),
        "receipt_ids": list(receipt_ids),
    }
    return Activity.model_validate(payload)


def _rule_dto(record: RuleVersionRecord) -> RuleVersion:
    """``rule_versions`` 行 → 活契约 ``RuleVersion``（design §2.4）。

    ``content`` 的 ``oneOf[CouponRule, CallbackRule]`` **无判别式字段声明**（判别靠
    ``template`` 的 ``const``），故一律交给 pydantic 的联合校验，禁在本层自己挑分支。
    ``terms`` 保持**落库顺序**（design §2.4：排序只发生在摘要投影里）。
    """
    payload: dict[str, Any] = {
        "id": record.id,
        "revision": record.revision,
        "created_at": record.created_at,
        "label": record.label,
        "content": json.loads(record.content_json),
        "terms": json.loads(record.terms_json),
        "source_rule_version": record.source_rule_version,
        "parent_rule_id": record.parent_rule_id,
        "activity_id": record.activity_id,
        "state": record.state,
        "digest": record.digest,
        "confirmed_at": record.confirmed_at,
        "confirmation": record.confirmation,
    }
    return RuleVersion.model_validate(payload)


def _binding_draft(dto: Binding) -> BindingDraft:
    """``Binding`` DTO → 领域层的 ``BindingDraft``（区间代数的唯一入参形状）。"""
    return BindingDraft(
        strategy_id=dto.strategy_id,
        source_version=dto.source_version,
        valid_from=dto.valid_from,
        valid_until=dto.valid_until,
        evidence_id=dto.evidence_id,
    )


def _binding_record(*, workspace_id: str, activity_id: str, dto: Binding) -> BindingRecord:
    """``Binding`` DTO → ``activity_bindings`` 行。日期列落 ``format=date`` 文本。"""
    return BindingRecord(
        workspace_id=workspace_id,
        activity_id=activity_id,
        strategy_id=dto.strategy_id,
        source_version=dto.source_version,
        valid_from=dto.valid_from.isoformat(),
        valid_until=dto.valid_until.isoformat(),
        evidence_id=dto.evidence_id,
    )


def _duplicate_external(
    *, bank_id: str, external_activity_id: str, existing_id: str
) -> StateConflict:
    """design §6.4「同银行外部活动号重复」：409 ``STATE_CONFLICT`` ＋ **两条** ``issues``。

    AC-002 的「明确定位」＝同时给出**冲突字段**与**既有活动 ID**。这不是回显探针：
    ``bank_id`` 与 ``external_activity_id`` 都是客户端自己刚提交的值，既有活动 ID 属于同一
    工作区（已过 404 隔离），与「404 不回显 ID」的禁枚举口径不冲突。
    """
    return StateConflict(
        DUPLICATE_EXTERNAL_DETAIL,
        issues=[
            Issue(
                code=_DUPLICATE_EXTERNAL_CODE,
                location=_BANK_LOCATION,
                message=f"银行 {bank_id}",
                severity=_ERROR_SEVERITY,
            ),
            Issue(
                code=_DUPLICATE_EXTERNAL_CODE,
                location=_EXTERNAL_LOCATION,
                message=(f"外部活动号 {external_activity_id} 已用于活动 {existing_id}"),
                severity=_ERROR_SEVERITY,
            ),
        ],
    )


def _is_business_denial(exc: DomainError) -> bool:
    """design §7.3：哪些被拒要追加一行 ``DENIED``。

    业务性拒绝＝409 ``STATE_CONFLICT``（试编辑已确认版本、归档后修改）、409 ``VERSION_MISMATCH``、
    422 ``EVIDENCE_REQUIRED``（条款门禁／绑定证据不通过）。协议性拒绝（401/403/404/412/413/
    422 形状校验/428）**不写**审计：无业务判断可留痕，且 404 写审计会把「不存在」与
    「属外工作区」的差异带进审计链。``FAILED`` 本卡不使用（无异步作业面）。
    """
    return exc.code in {"STATE_CONFLICT", "VERSION_MISMATCH", "EVIDENCE_REQUIRED"}


#: design §3.4：绑定校验的两类 422 的固定 detail（禁在调用点现编）。
_BINDING_INVALID_DETAIL: Final = "绑定有效期区间非法或存在重复，请修正后重试"
_BINDING_EVIDENCE_DETAIL: Final = "绑定引用的证据未登记，无法保存绑定"
#: design §4.2 第 7 条的固定 detail（逐字）。
_CLAUSE_GATE_DETAIL: Final = "必需条款未全部确认，无法确认该规则版本"
#: design §3.4 ④ 的细因标签：只由它构成时走 422 EVIDENCE_REQUIRED，否则 VALIDATION_ERROR。
_EVIDENCE_UNREGISTERED_CODE: Final = "BINDING_EVIDENCE_UNREGISTERED"
#: A1 的 target（design §3.1）。取值由 ``ACTIVITY_TRANSITIONS`` 里 ``sources`` 为空的那一行反推，
#: 禁抄字面量（``domain/activity/states.py`` 的同一纪律：取值来自活契约 DTO 的 Literal 参数）。
_ACTIVITY_INITIAL_STATE: Final = next(row.target for row in ACTIVITY_TRANSITIONS if not row.sources)
#: R1 / R4 的 target（design §3.2），同法反推。
_RULE_DRAFT_STATE: Final = next(row.target for row in RULE_TRANSITIONS if not row.sources)
#: R3 的 target（design §3.2）＝规则面的终态。
_RULE_CONFIRMED_STATE: Final = next(iter(RULE_TERMINAL_STATES))


class _ExternalClash(Exception):
    """内部控制流：``INSERT activities`` 撞 ``UNIQUE(workspace_id,bank_id,external_activity_id)``。

    与 ``_Replay`` 同理用异常而不是返回值：此刻事务必须**回滚**，回滚之后才能用一条新连接把
    「既有活动 ID」查出来 —— design §6.4 的竞态兜底要求 409 的两条 ``issues`` 带上它才算
    AC-002 的「明确定位」，而在已中止的事务里继续查是没有意义的。
    """

    __slots__ = ("bank_id", "cause", "external_activity_id")

    def __init__(self, *, bank_id: str, external_activity_id: str, cause: BaseException) -> None:
        super().__init__("同银行外部活动号冲突")
        self.bank_id = bank_id
        self.external_activity_id = external_activity_id
        self.cause = cause


def _issues_of(drafts: Sequence[GateIssue]) -> list[Issue]:
    """领域层 ``GateIssue`` 序列 → 契约 ``Issue`` 列表（四字段逐字对应，禁改字段名）。

    领域层刻意不 import ``api.common``（``domain/activity/__init__.py`` 的三条红线之一），
    故这层转换只能发生在 application：它同时是「领域层零上行依赖」的代价与证据。
    """
    return [
        Issue(
            code=draft.code,
            location=draft.location,
            message=draft.message,
            severity=draft.severity,
        )
        for draft in drafts
    ]


def _audit_denied(
    engine: Engine,
    audit: AuditWriter,
    *,
    workspace_id: str,
    at: datetime,
    actor: Session,
    action: str,
    target_kind: str,
    target_id: str,
    request_id: str,
) -> None:
    """design §7.3：业务性拒绝在**业务事务回滚之后**的独立短事务里追加一行 ``DENIED``。

    必须在回滚之后：AC-003 的主证据含「审计」，「确认并试编辑」被拒这件事必须留痕，
    而它与被回滚的业务写入同事务就会一起消失。``sequence`` 与 ``previous_digest`` 仍由
    ``AuditWriter`` 在这条短事务内独家取，故审计链不会分叉（体例＝M0-04 对被拒取消／重试
    写 ``DENIED`` 的裁定）。
    """
    with connect(engine) as conn, conn.begin():
        audit.write(
            conn,
            workspace_id=workspace_id,
            at=at,
            actor_id=actor.actor_id,
            role=audit_role_of(actor),
            action=action,
            target_kind=target_kind,
            target_id=target_id,
            outcome=_OUTCOME_DENIED,
            request_id=request_id,
        )


class ActivityService:
    """结构化满足 ``api.deps.ActivityService`` 端口（design §1.1–§1.4；构造签名与
    ``WorkspaceService`` 同形，全部依赖可注入）。
    """

    def __init__(
        self,
        *,
        engine: Engine,
        clock: Clock,
        config: AppConfig,
        activities: ActivityRepository | None = None,
        bindings: ActivityBindingRepository | None = None,
        idempotency: IdempotencyGuard | None = None,
        audit: AuditWriter | None = None,
        cursor_secret: bytes | None = None,
    ) -> None:
        self._engine = engine
        self._clock = clock
        self._config = config
        self._activities = activities if activities is not None else ActivityRepository()
        self._bindings = bindings if bindings is not None else ActivityBindingRepository()
        self._idempotency = idempotency if idempotency is not None else IdempotencyGuard()
        self._audit = audit if audit is not None else AuditWriter()
        # 密钥**延迟**加载：构造 service 不该在数据目录里落文件，否则 doctor 的
        # data_dir 子目录 WARN 会被一次健康检查悄悄抹平（workspace_service 的同一理由）。
        self._cursor_secret = cursor_secret

    def _secret(self) -> bytes:
        """复用 ``workspace_service.load_cursor_secret`` 的那**一把**密钥（禁第二把）。"""
        if self._cursor_secret is None:
            self._cursor_secret = load_cursor_secret(self._config.data_dir)
        return self._cursor_secret

    def _assemble(
        self, conn: Connection, *, workspace_id: str, records: list[ActivityRecord]
    ) -> list[Activity]:
        """把 ``activities`` 行与三张从表的**批量**投影组装成 ``Activity``（design §7.4）。

        三张从表各一次查询（``list_for_activities`` / ``list_rule_ids`` / ``list_receipt_ids``），
        在 Python 侧分组回填 ⇒ 一页 100 个活动也只有 3 条从表 SQL，**禁 N+1**。
        ``getActivity`` 走同一方法（页大小 1），禁为单对象另写第二套查询。
        """
        ids = [record.id for record in records]
        binding_map = self._bindings.list_for_activities(
            conn, workspace_id=workspace_id, activity_ids=ids
        )
        rule_map = self._activities.list_rule_ids(conn, workspace_id=workspace_id, activity_ids=ids)
        receipt_map = self._activities.list_receipt_ids(
            conn, workspace_id=workspace_id, activity_ids=ids
        )
        return [
            _activity_dto(
                record,
                bindings=binding_map.get(record.id, []),
                rule_ids=rule_map.get(record.id, []),
                receipt_ids=receipt_map.get(record.id, []),
            )
            for record in records
        ]

    def _validate_bindings(
        self, conn: Connection, *, workspace_id: str, dto_bindings: list[Binding]
    ) -> None:
        """design §3.4 的绑定门禁：区间代数全部交领域层，本层只补 ``evidence`` 的只读投影。

        ``registered_evidence_ids`` 由 ``ActivityBindingRepository.evidence_exists`` 一次性批量取，
        与条款面共用同一个集合（禁各查一遍）。四类违例一律 ``ERROR``：只含
        ``BINDING_EVIDENCE_UNREGISTERED`` 时走 422 ``EVIDENCE_REQUIRED``，否则走 422
        ``VALIDATION_ERROR``（design §3.4 ①②③ 与 ④ 的分码），两种情况都把**全部**违例
        一次返回，禁首错即返。
        """
        drafts = [_binding_draft(item) for item in dto_bindings]
        evidence_ids = list(dict.fromkeys(draft.evidence_id for draft in drafts))
        registered = self._bindings.evidence_exists(
            conn, workspace_id=workspace_id, evidence_ids=evidence_ids
        )
        found = _issues_of(validate_bindings(drafts=drafts, registered_evidence_ids=registered))
        errors = [issue for issue in found if issue.severity == _ERROR_SEVERITY]
        if not errors:
            return
        if {issue.code for issue in errors} == {_EVIDENCE_UNREGISTERED_CODE}:
            raise DomainError(_BINDING_EVIDENCE_DETAIL, code="EVIDENCE_REQUIRED", issues=errors)
        raise ValidationFailure(_BINDING_INVALID_DETAIL, issues=errors)

    # -------------------------------------------------------------------------- listActivities

    def list_activities(
        self,
        *,
        actor: Session,
        workspace_id: str,
        cursor: str | None,
        limit: int,
        q: str | None,
        status: str | None,
    ) -> ActivityPage:
        """``GET /api/v1/workspaces/{workspace_id}/activities`` 的用例实现（TX-READ，只读）。"""
        if limit < 1:
            raise DomainError(f"limit 必须 >= 1：{limit}", code="VALIDATION_ERROR")
        statuses = _parse_status(status, ACTIVITY_STATES)
        digest = activity_query_digest(workspace_id=workspace_id, limit=limit, q=q, status=status)
        after: tuple[str, str] | None = None
        if cursor is not None:
            after = _cursor_key(
                cursor,
                secret=self._secret(),
                actor_id=actor.actor_id,
                query_digest=digest,
            )
        with connect(self._engine) as conn:
            rows = self._activities.list_page(
                conn,
                workspace_id=workspace_id,
                limit=limit + 1,
                after=after,
                q=q,
                statuses=statuses,
            )
            items = self._assemble(conn, workspace_id=workspace_id, records=rows[:limit])
        next_cursor: str | None = None
        if len(rows) > limit and items:
            last = items[-1]
            next_cursor = encode_cursor(
                _cursor_payload(
                    actor_id=actor.actor_id,
                    query_digest=digest,
                    created_at=last.created_at.isoformat(),
                    resource_id=last.id,
                ),
                self._secret(),
            )
        return ActivityPage(items=items, next_cursor=next_cursor)

    # ---------------------------------------------------------------------------- getActivity

    def get_activity(self, *, workspace_id: str, activity_id: str) -> Activity:
        """``GET …/activities/{activity_id}``（design §1.3）。归档后读取不受限（§3.1）。"""
        with connect(self._engine) as conn:
            record = self._activities.get(conn, workspace_id=workspace_id, activity_id=activity_id)
            if record is None:
                # 越区与不存在逐字相同，不回显 ID（``ResourceNotFound`` 的禁枚举口径）。
                raise ResourceNotFound()
            items = self._assemble(conn, workspace_id=workspace_id, records=[record])
        return items[0]

    # ------------------------------------------------------------------------- createActivity

    def create_activity(
        self,
        *,
        workspace_id: str,
        payload: ActivityCreate,
        body: bytes,
        idempotency_key: str,
        actor: Session,
        request_id: str,
    ) -> ActivityCreateOutcome:
        """``POST …/activities`` 的用例实现（TX-A1；design §1.2 / §6.3 / §7.1）。

        ``ActivityCreate`` 实测**没有** ``bindings`` 字段 ⇒ 新建活动必然零绑定，
        AC-002 的绑定由随后的 ``updateActivity`` 落（design §7.1 TX-A1 的注）。
        """
        key_value = validate_idempotency_key(idempotency_key)
        digest = request_digest(
            path=f"{API_PREFIX}/workspaces/{workspace_id}/activities",
            query={},
            body=body,
            files=(),
        )
        key = IdempotencyKey(
            scope_key=workspace_id,
            actor_id=actor.actor_id,
            operation=_OPERATION_CREATE_ACTIVITY,
            idem_key=key_value,
        )
        now = self._clock.now()
        try:
            with connect(self._engine) as conn, conn.begin():
                existing = self._idempotency.peek(conn, key=key, request_digest=digest)
                if existing is not None:
                    status, headers, body_of = _replayed_parts(existing)
                    return ActivityCreateOutcome(
                        status=status, headers=headers, body=body_of, replayed=True
                    )
                bank_id = payload.bank_id
                external = payload.external_activity_id
                if bank_id is not None and external is not None:
                    clash = self._activities.find_by_external(
                        conn,
                        workspace_id=workspace_id,
                        bank_id=bank_id,
                        external_activity_id=external,
                    )
                    if clash is not None:
                        raise _duplicate_external(
                            bank_id=bank_id,
                            external_activity_id=external,
                            existing_id=clash.id,
                        )
                assert_activity_transition_allowed(
                    None, _ACTIVITY_INITIAL_STATE, trigger=_OPERATION_CREATE_ACTIVITY
                )
                record = ActivityRecord(
                    workspace_id=workspace_id,
                    id=new_resource_id(ACTIVITY_ID_PREFIX),
                    name=payload.name,
                    bank_id=payload.bank_id,
                    external_activity_id=payload.external_activity_id,
                    # DDL 的 ``description`` 是 NOT NULL，契约 ``minLength=0`` ⇒ 缺省写空串。
                    description="" if payload.description is None else payload.description,
                    status=_ACTIVITY_INITIAL_STATE,
                    current_rule_id=None,
                    revision=1,
                    created_at=_iso(now),
                )
                try:
                    self._activities.insert(conn, record=record)
                except IntegrityError as exc:
                    # design §6.4 竞态兜底：查重未命中但 INSERT 撞 UNIQUE ⇒ 同样翻成 409。
                    # 只有两个键都非空时才可能是那条 UNIQUE，其余完整性错误原样冒出去。
                    if record.bank_id is None or record.external_activity_id is None:
                        raise
                    raise _ExternalClash(
                        bank_id=str(record.bank_id),
                        external_activity_id=str(record.external_activity_id),
                        cause=exc,
                    ) from exc
                self._audit.write(
                    conn,
                    workspace_id=workspace_id,
                    at=now,
                    actor_id=actor.actor_id,
                    role=audit_role_of(actor),
                    action=ACTION_ACTIVITY_CREATED,
                    target_kind=TARGET_KIND_ACTIVITY,
                    target_id=record.id,
                    outcome=OUTCOME_ACCEPTED,
                    request_id=request_id,
                )
                items = self._assemble(conn, workspace_id=workspace_id, records=[record])
                response_body = items[0].model_dump(mode="json")
                headers = {"ETag": etag(items[0].revision)}
                envelope = idempotency_envelope(status=201, headers=headers, body=response_body)
                stored = self._idempotency.record(
                    conn,
                    key=key,
                    request_digest=digest,
                    status=201,
                    envelope_json=canonical_json(envelope),
                    now=now,
                )
                if stored is not None:
                    raise _Replay(stored)
                return ActivityCreateOutcome(
                    status=201, headers=headers, body=response_body, replayed=False
                )
        except _Replay as signal:
            status, headers, body_of = _replayed_parts(signal.record)
            return ActivityCreateOutcome(
                status=status, headers=headers, body=body_of, replayed=True
            )
        except _ExternalClash as clash:
            with connect(self._engine) as conn:
                found = self._activities.find_by_external(
                    conn,
                    workspace_id=workspace_id,
                    bank_id=clash.bank_id,
                    external_activity_id=clash.external_activity_id,
                )
            if found is None:
                # 不是那条 UNIQUE（例如工作区 FK 缺失）⇒ 禁把它伪装成 409。
                raise clash.cause from None
            raise _duplicate_external(
                bank_id=clash.bank_id,
                external_activity_id=clash.external_activity_id,
                existing_id=found.id,
            ) from None

    # ------------------------------------------------------------------------- updateActivity

    def update_activity(
        self,
        *,
        workspace_id: str,
        activity_id: str,
        payload: ActivityUpdate,
        body: bytes,
        idempotency_key: str,
        if_match: str | None,
        actor: Session,
        request_id: str,
    ) -> ActivityWriteOutcome:
        """``PATCH …/activities/{activity_id}`` 的用例实现（TX-A2；design §1.4 / §6.3 / §7.1）。

        判定顺序严格照 design §6.3：读当前行（404）→ 幂等重放 → ``If-Match``（428/412）→
        空 PATCH（422）→ 状态机（409）→ 绑定门禁（422）→ 写＋审计＋幂等登记。
        「先幂等、后 If-Match」是 ``API.md`` 的明文顺序，故同键同体的重放会回放**原**结果
        而不再判 412。
        """
        key_value = validate_idempotency_key(idempotency_key)
        digest = request_digest(
            path=f"{API_PREFIX}/workspaces/{workspace_id}/activities/{activity_id}",
            query={},
            body=body,
            files=(),
        )
        key = IdempotencyKey(
            scope_key=workspace_id,
            actor_id=actor.actor_id,
            operation=_OPERATION_UPDATE_ACTIVITY,
            idem_key=key_value,
        )
        # design §6.4：判空一律 ``exclude_unset``（**不是** ``exclude_none``）——
        # ``description`` 允许 ``""``、``bindings`` 允许 ``[]``，显式给空值是合法的「清空」意图。
        patch = payload.model_dump(exclude_unset=True)
        bindings_given = "bindings" in payload.model_fields_set
        now = self._clock.now()
        archived = "status" in patch and is_activity_terminal(str(patch["status"]))
        action = ACTION_ACTIVITY_ARCHIVED if archived else ACTION_ACTIVITY_UPDATED
        try:
            with connect(self._engine) as conn, conn.begin():
                record = self._activities.get(
                    conn, workspace_id=workspace_id, activity_id=activity_id
                )
                if record is None:
                    raise ResourceNotFound()
                existing = self._idempotency.peek(conn, key=key, request_digest=digest)
                if existing is not None:
                    status, headers, body_of = _replayed_parts(existing)
                    return ActivityWriteOutcome(
                        status=status, headers=headers, body=body_of, replayed=True
                    )
                check_if_match(if_match, record.revision)
                if not patch:
                    raise ValidationFailure(
                        EMPTY_PATCH_DETAIL,
                        issues=[
                            Issue(
                                code=_EMPTY_PATCH_CODE,
                                location=_ROOT_LOCATION,
                                message=EMPTY_PATCH_DETAIL,
                                severity=_ERROR_SEVERITY,
                            )
                        ],
                    )
                if is_activity_terminal(record.status):
                    raise StateConflict(
                        ARCHIVED_DETAIL,
                        issues=[
                            Issue(
                                code=_ACTIVITY_ARCHIVED_CODE,
                                location=(
                                    _STATUS_FIELD_LOCATION if "status" in patch else _ROOT_LOCATION
                                ),
                                message=ARCHIVED_DETAIL,
                                severity=_ERROR_SEVERITY,
                            )
                        ],
                    )
                target = str(patch["status"]) if "status" in patch else record.status
                assert_activity_transition_allowed(
                    record.status, target, trigger=_OPERATION_UPDATE_ACTIVITY
                )
                if bindings_given:
                    self._validate_bindings(
                        conn,
                        workspace_id=workspace_id,
                        dto_bindings=list(payload.bindings or []),
                    )
                touched = self._activities.update_fields(
                    conn,
                    workspace_id=workspace_id,
                    activity_id=activity_id,
                    revision=record.revision,
                    name=cast(str | None, patch.get("name")),
                    description=cast(str | None, patch.get("description")),
                    status=cast(str | None, patch.get("status")),
                )
                if touched != 1:
                    # 谓词 ``status='OPEN' AND revision=:revision`` 落空。revision 已由上面的
                    # ``check_if_match`` 判过 412，故这里只剩「并发归档」一种解释（design §3.1）。
                    raise StateConflict(
                        ARCHIVED_DETAIL,
                        issues=[
                            Issue(
                                code=_ACTIVITY_ARCHIVED_CODE,
                                location=_STATUS_FIELD_LOCATION,
                                message=ARCHIVED_DETAIL,
                                severity=_ERROR_SEVERITY,
                            )
                        ],
                    )
                if bindings_given:
                    self._bindings.replace_set(
                        conn,
                        workspace_id=workspace_id,
                        activity_id=activity_id,
                        bindings=[
                            _binding_record(
                                workspace_id=workspace_id,
                                activity_id=activity_id,
                                dto=item,
                            )
                            for item in (payload.bindings or [])
                        ],
                    )
                self._audit.write(
                    conn,
                    workspace_id=workspace_id,
                    at=now,
                    actor_id=actor.actor_id,
                    role=audit_role_of(actor),
                    action=action,
                    target_kind=TARGET_KIND_ACTIVITY,
                    target_id=activity_id,
                    outcome=OUTCOME_ACCEPTED,
                    request_id=request_id,
                )
                refreshed = self._activities.get(
                    conn, workspace_id=workspace_id, activity_id=activity_id
                )
                if refreshed is None:
                    raise InternalFailure(f"活动行在写入后消失：request_id={request_id}")
                items = self._assemble(conn, workspace_id=workspace_id, records=[refreshed])
                response_body = items[0].model_dump(mode="json")
                headers = {"ETag": etag(items[0].revision)}
                envelope = idempotency_envelope(status=200, headers=headers, body=response_body)
                stored = self._idempotency.record(
                    conn,
                    key=key,
                    request_digest=digest,
                    status=200,
                    envelope_json=canonical_json(envelope),
                    now=now,
                )
                if stored is not None:
                    raise _Replay(stored)
                return ActivityWriteOutcome(
                    status=200, headers=headers, body=response_body, replayed=False
                )
        except _Replay as signal:
            status, headers, body_of = _replayed_parts(signal.record)
            return ActivityWriteOutcome(status=status, headers=headers, body=body_of, replayed=True)
        except DomainError as exc:
            if _is_business_denial(exc):
                _audit_denied(
                    self._engine,
                    self._audit,
                    workspace_id=workspace_id,
                    at=now,
                    actor=actor,
                    action=action,
                    target_kind=TARGET_KIND_ACTIVITY,
                    target_id=activity_id,
                    request_id=request_id,
                )
            raise


#: design §4.2 第 5 条：``content.schema_version`` 的唯一受支持取值（契约 ``CouponRule`` /
#: ``CallbackRule`` 的 ``const: 1``）。契约的 ``const`` 已在解析期挡住绝大多数情况，
#: 本条是**纵深防御**，禁删。
_SUPPORTED_SCHEMA_VERSION: Final = 1
#: design §3.2：父版本必须是已确认版本才能派生新草稿。
_PARENT_NOT_CONFIRMED_DETAIL: Final = "父版本尚未确认，不能作为派生新草稿的来源"
#: design §3.2「重复确认」与 §4.2 第 5 条、§1.11 跨模板的固定 detail（禁在调用点现编）。
_ALREADY_CONFIRMED_DETAIL: Final = "该规则版本已确认，不可重复确认"
_SCHEMA_VERSION_DETAIL: Final = "规则内容的 schema_version 不受支持，无法确认"
_TEMPLATE_MISMATCH_DETAIL: Final = "两个规则版本的模板不同，不可比较"


def _comparison_projection(record: RuleVersionRecord) -> dict[str, Any]:
    """design §6.5：``compareRules`` 只比较**参与摘要的投影 ＋ ``label``**（§4.6）。

    ``id`` / ``revision`` / ``created_at`` / ``confirmed_at`` / ``confirmation`` / ``state`` /
    ``activity_id`` / ``parent_rule_id`` **不进** ``changes``：它们不是「候选字段变化」
    （``RULES.md``「候选字段变化可在草稿中比较」）。投影信封复用
    ``domain/activity/digests.py::digest_projection``，故「比较的面」与「摘要的面」天然同源，
    不会出现「摘要说变了、diff 说没变」。
    """
    projection = digest_projection(
        json.loads(record.content_json),
        json.loads(record.terms_json),
        record.source_rule_version,
    )
    projection["label"] = record.label
    return projection


class RuleService:
    """结构化满足 ``api.deps.RuleService`` 端口（design §1.5–§1.11；构造签名与
    ``WorkspaceService`` 同形，全部依赖可注入）。
    """

    def __init__(
        self,
        *,
        engine: Engine,
        clock: Clock,
        config: AppConfig,
        activities: ActivityRepository | None = None,
        rules: RuleVersionRepository | None = None,
        bindings: ActivityBindingRepository | None = None,
        idempotency: IdempotencyGuard | None = None,
        audit: AuditWriter | None = None,
        cursor_secret: bytes | None = None,
    ) -> None:
        self._engine = engine
        self._clock = clock
        self._config = config
        self._activities = activities if activities is not None else ActivityRepository()
        self._rules = rules if rules is not None else RuleVersionRepository()
        self._bindings = bindings if bindings is not None else ActivityBindingRepository()
        self._idempotency = idempotency if idempotency is not None else IdempotencyGuard()
        self._audit = audit if audit is not None else AuditWriter()
        self._cursor_secret = cursor_secret

    def _secret(self) -> bytes:
        """复用 ``workspace_service.load_cursor_secret`` 的那**一把**密钥（禁第二把）。"""
        if self._cursor_secret is None:
            self._cursor_secret = load_cursor_secret(self._config.data_dir)
        return self._cursor_secret

    def _require_activity_open(
        self, conn: Connection, *, workspace_id: str, activity_id: str, strict: bool
    ) -> ActivityRecord | None:
        """design §3.1「聚合终态的连带面」：活动 ``ARCHIVED`` 后写路径一律 409。

        ``strict=True``（create / confirm）时活动行必须存在，缺失即 500 —— 规则行的
        ``activity_id`` 有 FK，读不到只能是数据被外部改坏。``strict=False``（update）时
        容忍 ``None``：``updateRule`` 的 404 判据是**规则行**，不该因为活动面缺失而换码。
        归档后**读取不受限**，故本方法只被三个写 op 调用。
        """
        activity = self._activities.get(conn, workspace_id=workspace_id, activity_id=activity_id)
        if activity is None:
            if strict:
                raise InternalFailure("规则所属活动行缺失：activity_id 未落库")
            return None
        if is_activity_terminal(activity.status):
            raise StateConflict(
                ARCHIVED_DETAIL,
                issues=[
                    Issue(
                        code=_ACTIVITY_ARCHIVED_CODE,
                        location=_ACTIVITY_LOCATION,
                        message=ARCHIVED_DETAIL,
                        severity=_ERROR_SEVERITY,
                    )
                ],
            )
        return activity

    def _context(
        self,
        conn: Connection,
        *,
        workspace_id: str,
        record: RuleVersionRecord,
        content: Mapping[str, Any],
        terms: list[Any],
    ) -> tuple[RuleContext, frozenset[str]]:
        """组装 ``checkRule`` / ``confirmRule`` 共用的检查上下文与「已登记证据」集合。

        ``sibling_confirmed`` 与 ``registered_evidence_ids`` 都是**只读查询结果**，由本层注入
        （``domain/activity/__init__.py`` 红线 1：领域层不碰数据库）。两个 op 共用这一份组装，
        禁各写一遍——否则「确认时看到的」与「检查时看到的」会漂移。
        """
        siblings = self._rules.list_confirmed_siblings(
            conn,
            workspace_id=workspace_id,
            activity_id=record.activity_id,
            exclude_rule_id=record.id,
        )
        evidence_ids = list(
            dict.fromkeys(
                str(item.get("evidence_id"))
                for item in terms
                if isinstance(item, Mapping) and item.get("evidence_id")
            )
        )
        registered = self._bindings.evidence_exists(
            conn, workspace_id=workspace_id, evidence_ids=evidence_ids
        )
        context = RuleContext(
            rule_id=record.id,
            template=record.template,
            content=content,
            terms=terms,
            sibling_confirmed=siblings,
        )
        return context, frozenset(registered)

    def _verify_digest(self, record: RuleVersionRecord, computed: str) -> None:
        """design §5.2 / §6.4：``digest`` 列与现算摘要不符 → 500 ``INTERNAL_ERROR``。

        这是「可复算摘要」的自检点：不符意味着落库字节与摘要投影曾经漂移过
        （例如有人绕过 service 直接改过 ``content_json``），此时继续返回 200 会让
        ``confirmRule`` 的 409 ``VERSION_MISMATCH`` 判定建立在一个不可信的基线之上。
        """
        if record.digest != computed:
            raise InternalFailure("规则摘要与落库内容不一致，拒绝返回可能不可信的检查结果")

    # ------------------------------------------------------------------------------ listRules

    def list_rules(
        self,
        *,
        actor: Session,
        workspace_id: str,
        activity_id: str,
        cursor: str | None,
        limit: int,
        q: str | None,
        status: str | None,
    ) -> RuleVersionPage:
        """``GET …/activities/{activity_id}/rules``（design §1.5，TX-READ 只读）。

        ⚠ 查询参数叫 ``status``，被筛的列是 ``rule_versions.state``（ADR-006 §4.7 点名的
        命名错位）；本文按契约逐字实现，不改名、也不据此推断其它资源。
        """
        if limit < 1:
            raise DomainError(f"limit 必须 >= 1：{limit}", code="VALIDATION_ERROR")
        states = _parse_status(status, RULE_STATES)
        digest = rule_query_digest(
            workspace_id=workspace_id,
            activity_id=activity_id,
            limit=limit,
            q=q,
            status=status,
        )
        after: tuple[str, str] | None = None
        if cursor is not None:
            after = _cursor_key(
                cursor,
                secret=self._secret(),
                actor_id=actor.actor_id,
                query_digest=digest,
            )
        with connect(self._engine) as conn:
            rows = self._rules.list_page(
                conn,
                workspace_id=workspace_id,
                activity_id=activity_id,
                limit=limit + 1,
                after=after,
                q=q,
                states=states,
            )
        items = [_rule_dto(record) for record in rows[:limit]]
        next_cursor: str | None = None
        if len(rows) > limit and items:
            last = items[-1]
            next_cursor = encode_cursor(
                _cursor_payload(
                    actor_id=actor.actor_id,
                    query_digest=digest,
                    created_at=last.created_at.isoformat(),
                    resource_id=last.id,
                ),
                self._secret(),
            )
        return RuleVersionPage(items=items, next_cursor=next_cursor)

    # ------------------------------------------------------------------------------ createRule

    def create_rule(
        self,
        *,
        workspace_id: str,
        activity_id: str,
        payload: RuleCreate,
        body: bytes,
        idempotency_key: str,
        actor: Session,
        request_id: str,
    ) -> RuleWriteOutcome:
        """``POST …/activities/{activity_id}/rules``（TX-R1；design §1.6 / §7.1）。

        新草稿一律 ``state='DRAFT'`` / ``revision=1`` / 确认双列为 NULL ——
        DDL 的双条件 CHECK 双向钉死，禁只写一侧。``parent_rule_id`` 给出时必须指向
        **同一活动**的既有 ``CONFIRMED`` 版本（R4），否则 404 / 409。
        """
        key_value = validate_idempotency_key(idempotency_key)
        digest = request_digest(
            path=(f"{API_PREFIX}/workspaces/{workspace_id}/activities/{activity_id}/rules"),
            query={},
            body=body,
            files=(),
        )
        key = IdempotencyKey(
            scope_key=workspace_id,
            actor_id=actor.actor_id,
            operation=_OPERATION_CREATE_RULE,
            idem_key=key_value,
        )
        now = self._clock.now()
        parent_id = payload.parent_rule_id
        action = (
            ACTION_RULE_SUCCESSOR_DRAFT_CREATED
            if parent_id is not None
            else ACTION_RULE_DRAFT_CREATED
        )
        try:
            with connect(self._engine) as conn, conn.begin():
                # design §7.1 TX-R1 的顺序：读活动行 → 读父版本 → 幂等 → INSERT。
                self._require_activity_open(
                    conn, workspace_id=workspace_id, activity_id=activity_id, strict=True
                )
                parent: RuleVersionRecord | None = None
                if parent_id is not None:
                    parent = self._rules.get(conn, workspace_id=workspace_id, rule_id=parent_id)
                    # 不存在、属外工作区、**或属别的活动**一律 404 逐字相同（design §3.2 R4）。
                    if parent is None or parent.activity_id != activity_id:
                        raise ResourceNotFound()
                    if parent.state != _RULE_CONFIRMED_STATE:
                        raise StateConflict(
                            _PARENT_NOT_CONFIRMED_DETAIL,
                            issues=[
                                Issue(
                                    code=_PARENT_NOT_CONFIRMED_CODE,
                                    location=_PARENT_LOCATION,
                                    message=_PARENT_NOT_CONFIRMED_DETAIL,
                                    severity=_ERROR_SEVERITY,
                                )
                            ],
                        )
                existing = self._idempotency.peek(conn, key=key, request_digest=digest)
                if existing is not None:
                    status, headers, body_of = _replayed_parts(existing)
                    return RuleWriteOutcome(
                        status=status, headers=headers, body=body_of, replayed=True
                    )
                assert_rule_transition_allowed(
                    None if parent is None else parent.state,
                    _RULE_DRAFT_STATE,
                    trigger=_OPERATION_CREATE_RULE,
                )
                content_dump = payload.content.model_dump(mode="json")
                terms_dump = [item.model_dump(mode="json") for item in payload.terms]
                record = RuleVersionRecord(
                    workspace_id=workspace_id,
                    id=new_resource_id(RULE_ID_PREFIX),
                    activity_id=activity_id,
                    parent_rule_id=parent_id,
                    label=payload.label,
                    # design §2.4：``template`` 冗余列由 service 从 ``content.template`` 取，
                    # 禁由客户端第二处给。
                    template=str(content_dump["template"]),
                    source_rule_version=payload.source_rule_version,
                    state=_RULE_DRAFT_STATE,
                    revision=1,
                    content_json=canonical_json(content_dump),
                    terms_json=canonical_json(terms_dump),
                    digest=rule_digest(
                        content_dump,
                        terms_dump,
                        payload.source_rule_version,
                        canonicalize=canonical_json,
                    ),
                    created_at=_iso(now),
                    confirmed_at=None,
                    confirmation=None,
                )
                self._rules.insert(conn, record=record)
                self._audit.write(
                    conn,
                    workspace_id=workspace_id,
                    at=now,
                    actor_id=actor.actor_id,
                    role=audit_role_of(actor),
                    action=action,
                    target_kind=TARGET_KIND_RULE,
                    target_id=record.id,
                    outcome=OUTCOME_ACCEPTED,
                    request_id=request_id,
                )
                dto = _rule_dto(record)
                response_body = dto.model_dump(mode="json")
                headers = {"ETag": etag(dto.revision)}
                envelope = idempotency_envelope(status=201, headers=headers, body=response_body)
                stored = self._idempotency.record(
                    conn,
                    key=key,
                    request_digest=digest,
                    status=201,
                    envelope_json=canonical_json(envelope),
                    now=now,
                )
                if stored is not None:
                    raise _Replay(stored)
                return RuleWriteOutcome(
                    status=201, headers=headers, body=response_body, replayed=False
                )
        except _Replay as signal:
            status, headers, body_of = _replayed_parts(signal.record)
            return RuleWriteOutcome(status=status, headers=headers, body=body_of, replayed=True)
        except DomainError as exc:
            if _is_business_denial(exc):
                _audit_denied(
                    self._engine,
                    self._audit,
                    workspace_id=workspace_id,
                    at=now,
                    actor=actor,
                    action=action,
                    target_kind=TARGET_KIND_RULE,
                    target_id=activity_id,
                    request_id=request_id,
                )
            raise

    # --------------------------------------------------------------------------------- getRule

    def get_rule(self, *, workspace_id: str, rule_id: str) -> RuleVersion:
        """``GET …/rules/{rule_id}``（design §1.7）。

        路径里没有 ``activity_id``：活动归属由行内 ``rule_versions.activity_id`` 决定，
        但工作区隔离仍按 ``workspace_id`` 严格校验，越区 → 404（不回显 ID、不区分原因）。
        """
        with connect(self._engine) as conn:
            record = self._rules.get(conn, workspace_id=workspace_id, rule_id=rule_id)
        if record is None:
            raise ResourceNotFound()
        return _rule_dto(record)

    # ------------------------------------------------------------------------------ updateRule

    def update_rule(
        self,
        *,
        workspace_id: str,
        rule_id: str,
        payload: RuleUpdate,
        body: bytes,
        idempotency_key: str,
        if_match: str | None,
        actor: Session,
        request_id: str,
    ) -> RuleWriteOutcome:
        """``PATCH …/rules/{rule_id}``（TX-R2；design §1.8 / §3.2 / §6.3 / §7.3）。

        ``label`` 与 ``content``/``terms`` **分别审计**（``DOMAIN.md``「规则标签和确认说明
        分别审计」）：同时改两者写两行，只改其一写一行。``label`` 不进摘要（§4.6），
        故只改 label 时 ``digest`` 列一动不动。
        """
        key_value = validate_idempotency_key(idempotency_key)
        digest = request_digest(
            path=f"{API_PREFIX}/workspaces/{workspace_id}/rules/{rule_id}",
            query={},
            body=body,
            files=(),
        )
        key = IdempotencyKey(
            scope_key=workspace_id,
            actor_id=actor.actor_id,
            operation=_OPERATION_UPDATE_RULE,
            idem_key=key_value,
        )
        patch = payload.model_dump(exclude_unset=True)
        label_value = cast(str | None, patch.get("label"))
        label_given = label_value is not None
        content_given = "terms" in patch or ("content" in patch and payload.content is not None)
        now = self._clock.now()
        action = ACTION_RULE_CONTENT_UPDATED if content_given else ACTION_RULE_LABEL_UPDATED
        try:
            with connect(self._engine) as conn, conn.begin():
                record = self._rules.get(conn, workspace_id=workspace_id, rule_id=rule_id)
                if record is None:
                    raise ResourceNotFound()
                self._require_activity_open(
                    conn,
                    workspace_id=workspace_id,
                    activity_id=record.activity_id,
                    strict=False,
                )
                existing = self._idempotency.peek(conn, key=key, request_digest=digest)
                if existing is not None:
                    status, headers, body_of = _replayed_parts(existing)
                    return RuleWriteOutcome(
                        status=status, headers=headers, body=body_of, replayed=True
                    )
                check_if_match(if_match, record.revision)
                if not patch or not (label_given or content_given):
                    # design §6.4：``RuleUpdate.required`` 是空数组 ⇒ ``{}`` 能过 Schema，
                    # 必须由 service 判空。``{"label": null}`` 同样落不到任何可写列
                    # （DDL 的 ``label`` 是 NOT NULL），一并归入空 PATCH。
                    raise ValidationFailure(
                        EMPTY_PATCH_DETAIL,
                        issues=[
                            Issue(
                                code=_EMPTY_PATCH_CODE,
                                location=_ROOT_LOCATION,
                                message=EMPTY_PATCH_DETAIL,
                                severity=_ERROR_SEVERITY,
                            )
                        ],
                    )
                if is_rule_terminal(record.state):
                    raise StateConflict(
                        IMMUTABLE_DETAIL,
                        issues=[
                            Issue(
                                code=_RULE_IMMUTABLE_CODE,
                                location=_ROOT_LOCATION,
                                message=IMMUTABLE_DETAIL,
                                severity=_ERROR_SEVERITY,
                            )
                        ],
                    )
                assert_rule_transition_allowed(
                    record.state, _RULE_DRAFT_STATE, trigger=_OPERATION_UPDATE_RULE
                )
                content_dump: Any = (
                    payload.content.model_dump(mode="json")
                    if payload.content is not None and "content" in patch
                    else json.loads(record.content_json)
                )
                terms_dump: Any = (
                    [item.model_dump(mode="json") for item in payload.terms]
                    if "terms" in patch and payload.terms is not None
                    else json.loads(record.terms_json)
                )
                new_digest = (
                    rule_digest(
                        content_dump,
                        terms_dump,
                        record.source_rule_version,
                        canonicalize=canonical_json,
                    )
                    if content_given
                    else None
                )
                touched = self._rules.update_draft(
                    conn,
                    workspace_id=workspace_id,
                    rule_id=rule_id,
                    revision=record.revision,
                    label=label_value,
                    content_json=canonical_json(content_dump) if content_given else None,
                    terms_json=canonical_json(terms_dump) if content_given else None,
                    digest=new_digest,
                )
                if touched != 1:
                    # 谓词 ``state='DRAFT' AND revision=:revision`` 落空。revision 已由
                    # ``check_if_match`` 判过 412，故只剩「已确认」一种解释（AC-003）。
                    raise StateConflict(
                        IMMUTABLE_DETAIL,
                        issues=[
                            Issue(
                                code=_RULE_IMMUTABLE_CODE,
                                location=_ROOT_LOCATION,
                                message=IMMUTABLE_DETAIL,
                                severity=_ERROR_SEVERITY,
                            )
                        ],
                    )
                if label_given:
                    self._audit.write(
                        conn,
                        workspace_id=workspace_id,
                        at=now,
                        actor_id=actor.actor_id,
                        role=audit_role_of(actor),
                        action=ACTION_RULE_LABEL_UPDATED,
                        target_kind=TARGET_KIND_RULE,
                        target_id=rule_id,
                        outcome=OUTCOME_ACCEPTED,
                        request_id=request_id,
                    )
                if content_given:
                    self._audit.write(
                        conn,
                        workspace_id=workspace_id,
                        at=now,
                        actor_id=actor.actor_id,
                        role=audit_role_of(actor),
                        action=ACTION_RULE_CONTENT_UPDATED,
                        target_kind=TARGET_KIND_RULE,
                        target_id=rule_id,
                        outcome=OUTCOME_ACCEPTED,
                        request_id=request_id,
                    )
                refreshed = self._rules.get(conn, workspace_id=workspace_id, rule_id=rule_id)
                if refreshed is None:
                    raise InternalFailure(f"规则版本行在写入后消失：request_id={request_id}")
                dto = _rule_dto(refreshed)
                response_body = dto.model_dump(mode="json")
                headers = {"ETag": etag(dto.revision)}
                envelope = idempotency_envelope(status=200, headers=headers, body=response_body)
                stored = self._idempotency.record(
                    conn,
                    key=key,
                    request_digest=digest,
                    status=200,
                    envelope_json=canonical_json(envelope),
                    now=now,
                )
                if stored is not None:
                    raise _Replay(stored)
                return RuleWriteOutcome(
                    status=200, headers=headers, body=response_body, replayed=False
                )
        except _Replay as signal:
            status, headers, body_of = _replayed_parts(signal.record)
            return RuleWriteOutcome(status=status, headers=headers, body=body_of, replayed=True)
        except DomainError as exc:
            if _is_business_denial(exc):
                _audit_denied(
                    self._engine,
                    self._audit,
                    workspace_id=workspace_id,
                    at=now,
                    actor=actor,
                    action=action,
                    target_kind=TARGET_KIND_RULE,
                    target_id=rule_id,
                    request_id=request_id,
                )
            raise

    def confirm_rule(
        self,
        *,
        workspace_id: str,
        rule_id: str,
        payload: Confirmation,
        body: bytes,
        idempotency_key: str,
        if_match: str | None,
        actor: Session,
        request_id: str,
    ) -> RuleWriteOutcome:
        """``POST …/rules/{rule_id}/confirm``（TX-R3；design §1.9 / §4.2 / §6.3 / §7.1）。

        判定顺序**逐条照 design §4.2**（顺序即代码顺序，禁调序）：存在性 → 幂等 →
        ``If-Match`` → 状态（已确认 / 活动已归档）→ ``schema_version`` → 摘要匹配 →
        条款门禁 → 警告需备注 → 写。「任一不通过即抛，不做后续判定」，避免一次返回一堆
        互相掩盖的错。成功后同事务把 ``activities.current_rule_id`` 指向本版本并 bump 活动
        ``revision``（design §3.2 末条），故确认规则会使**活动自身**的 ETag 变化。
        """
        key_value = validate_idempotency_key(idempotency_key)
        digest = request_digest(
            path=f"{API_PREFIX}/workspaces/{workspace_id}/rules/{rule_id}/confirm",
            query={},
            body=body,
            files=(),
        )
        key = IdempotencyKey(
            scope_key=workspace_id,
            actor_id=actor.actor_id,
            operation=_OPERATION_CONFIRM_RULE,
            idem_key=key_value,
        )
        now = self._clock.now()
        try:
            with connect(self._engine) as conn, conn.begin():
                record = self._rules.get(conn, workspace_id=workspace_id, rule_id=rule_id)
                if record is None:
                    raise ResourceNotFound()
                existing = self._idempotency.peek(conn, key=key, request_digest=digest)
                if existing is not None:
                    status, headers, body_of = _replayed_parts(existing)
                    return RuleWriteOutcome(
                        status=status, headers=headers, body=body_of, replayed=True
                    )
                check_if_match(if_match, record.revision)
                if is_rule_terminal(record.state):
                    raise StateConflict(
                        _ALREADY_CONFIRMED_DETAIL,
                        issues=[
                            Issue(
                                code=_RULE_ALREADY_CONFIRMED_CODE,
                                location=_ROOT_LOCATION,
                                message=_ALREADY_CONFIRMED_DETAIL,
                                severity=_ERROR_SEVERITY,
                            )
                        ],
                    )
                self._require_activity_open(
                    conn,
                    workspace_id=workspace_id,
                    activity_id=record.activity_id,
                    strict=True,
                )
                assert_rule_transition_allowed(
                    record.state,
                    _RULE_CONFIRMED_STATE,
                    trigger=_OPERATION_CONFIRM_RULE,
                )
                content_dump = json.loads(record.content_json)
                terms_dump = json.loads(record.terms_json)
                schema_version = (
                    content_dump.get("schema_version")
                    if isinstance(content_dump, Mapping)
                    else None
                )
                if schema_version != _SUPPORTED_SCHEMA_VERSION:
                    raise ValidationFailure(
                        _SCHEMA_VERSION_DETAIL,
                        issues=[
                            Issue(
                                code=_SCHEMA_VERSION_CODE,
                                location=_SCHEMA_VERSION_LOCATION,
                                message=_SCHEMA_VERSION_DETAIL,
                                severity=_ERROR_SEVERITY,
                            )
                        ],
                    )
                computed = rule_digest(
                    content_dump,
                    terms_dump,
                    record.source_rule_version,
                    canonicalize=canonical_json,
                )
                self._verify_digest(record, computed)
                # design §4.2 第 6 条：**只比较、不回显**（``confirm_digest_matches`` 返回 bool
                # 而不是抛异常，正是为了让「回显」在类型上无从发生）。
                if not confirm_digest_matches(provided=payload.digest, current=computed):
                    raise DomainError(
                        DIGEST_MISMATCH_DETAIL,
                        code="VERSION_MISMATCH",
                        issues=[
                            Issue(
                                code=_DIGEST_MISMATCH_CODE,
                                location=_DIGEST_LOCATION,
                                message=DIGEST_MISMATCH_DETAIL,
                                severity=_ERROR_SEVERITY,
                            )
                        ],
                    )
                context, registered = self._context(
                    conn,
                    workspace_id=workspace_id,
                    record=record,
                    content=content_dump,
                    terms=terms_dump,
                )
                gate = evaluate_clause_gate(
                    template=record.template,
                    terms=terms_dump,
                    registered_evidence_ids=registered,
                )
                errors = [item for item in gate if item.severity == _ERROR_SEVERITY]
                if errors:
                    raise DomainError(
                        _CLAUSE_GATE_DETAIL,
                        code="EVIDENCE_REQUIRED",
                        issues=_issues_of(errors),
                    )
                # design §4.2 第 8 条：警告来自**条款门禁 ＋ 检查项框架**两面，
                # ``note_satisfies_warnings`` 自己按 severity 过滤，故调用方不必先分组。
                warnings = [*gate, *run_checks(context).issues]
                note_issue = note_satisfies_warnings(note=payload.note, warnings=warnings)
                if note_issue is not None:
                    raise DomainError(
                        NOTE_REQUIRED_DETAIL,
                        code="EVIDENCE_REQUIRED",
                        issues=_issues_of([note_issue]),
                    )
                touched = self._rules.confirm(
                    conn,
                    workspace_id=workspace_id,
                    rule_id=rule_id,
                    revision=record.revision,
                    digest=computed,
                    confirmed_at=_iso(now),
                    confirmation=payload.note,
                )
                if touched != 1:
                    raise StateConflict(
                        _ALREADY_CONFIRMED_DETAIL,
                        issues=[
                            Issue(
                                code=_RULE_ALREADY_CONFIRMED_CODE,
                                location=_ROOT_LOCATION,
                                message=_ALREADY_CONFIRMED_DETAIL,
                                severity=_ERROR_SEVERITY,
                            )
                        ],
                    )
                # design §3.2 末条（冻结）：R3 成功后同事务联动 ``activities.current_rule_id``。
                if (
                    self._activities.set_current_rule(
                        conn,
                        workspace_id=workspace_id,
                        activity_id=record.activity_id,
                        rule_id=rule_id,
                    )
                    != 1
                ):
                    raise InternalFailure("确认规则时活动行联动失败")
                self._audit.write(
                    conn,
                    workspace_id=workspace_id,
                    at=now,
                    actor_id=actor.actor_id,
                    role=audit_role_of(actor),
                    action=ACTION_RULE_CONFIRMED,
                    target_kind=TARGET_KIND_RULE,
                    target_id=rule_id,
                    outcome=OUTCOME_ACCEPTED,
                    request_id=request_id,
                )
                refreshed = self._rules.get(conn, workspace_id=workspace_id, rule_id=rule_id)
                if refreshed is None:
                    raise InternalFailure(f"规则版本行在写入后消失：request_id={request_id}")
                dto = _rule_dto(refreshed)
                response_body = dto.model_dump(mode="json")
                headers = {"ETag": etag(dto.revision)}
                envelope = idempotency_envelope(status=200, headers=headers, body=response_body)
                stored = self._idempotency.record(
                    conn,
                    key=key,
                    request_digest=digest,
                    status=200,
                    envelope_json=canonical_json(envelope),
                    now=now,
                )
                if stored is not None:
                    raise _Replay(stored)
                return RuleWriteOutcome(
                    status=200, headers=headers, body=response_body, replayed=False
                )
        except _Replay as signal:
            status, headers, body_of = _replayed_parts(signal.record)
            return RuleWriteOutcome(status=status, headers=headers, body=body_of, replayed=True)
        except DomainError as exc:
            if _is_business_denial(exc):
                _audit_denied(
                    self._engine,
                    self._audit,
                    workspace_id=workspace_id,
                    at=now,
                    actor=actor,
                    action=ACTION_RULE_CONFIRMED,
                    target_kind=TARGET_KIND_RULE,
                    target_id=rule_id,
                    request_id=request_id,
                )
            raise

    # ------------------------------------------------------------------------------- checkRule

    def check_rule(self, *, workspace_id: str, rule_id: str) -> RuleCheck:
        """``GET …/rules/{rule_id}/checks``（design §1.10 / §5.2；TX-READ 只读）。

        只读、可重复调用、结果只由 ``rule_versions`` 行内容决定：``rule_digest`` 取自该行
        ``digest`` 列，**禁**在响应里重算出第二个值（现算值只用于 §5.2 的一致性自检，
        不符即 500，绝不返回一个与库里不同的摘要）。本 op **只生成反例数据与待验证行为文案，
        不做任何金额分回放判定**（design §5.4）。
        """
        with connect(self._engine) as conn:
            record = self._rules.get(conn, workspace_id=workspace_id, rule_id=rule_id)
            if record is None:
                raise ResourceNotFound()
            content_dump = json.loads(record.content_json)
            terms_dump = json.loads(record.terms_json)
            context, registered = self._context(
                conn,
                workspace_id=workspace_id,
                record=record,
                content=content_dump,
                terms=terms_dump,
            )
        computed = rule_digest(
            content_dump,
            terms_dump,
            record.source_rule_version,
            canonicalize=canonical_json,
        )
        self._verify_digest(record, computed)
        gate = evaluate_clause_gate(
            template=record.template,
            terms=terms_dump,
            registered_evidence_ids=registered,
        )
        result = run_checks(context)
        raw = [*gate, *result.issues]
        # design §5.2：去重键 ``(code, location)`` —— 同一事实只报一次。``run_checks`` 内部
        # 已去重，但「条款门禁」与「检查项框架」是两个注册表，跨表仍可能撞上同一事实。
        issues: list[Issue] = []
        seen: set[tuple[str, str]] = set()
        for issue in _issues_of(raw):
            marker = (issue.code, issue.location)
            if marker in seen:
                continue
            seen.add(marker)
            issues.append(issue)
        boundary_cases = [
            BoundaryCase.model_validate(
                {
                    "id": draft.id,
                    "label": draft.label,
                    "input": draft.input_payload,
                    "verification": draft.verification,
                }
            )
            for draft in result.boundary_cases
        ]
        return RuleCheck(
            rule_id=rule_id,
            rule_digest=record.digest,
            state=check_state_of(raw),
            issues=issues,
            boundary_cases=boundary_cases,
        )

    # ---------------------------------------------------------------------------- compareRules

    def compare_rules(self, *, workspace_id: str, rule_id: str, candidate_rule_id: str) -> RuleDiff:
        """``GET …/rules/{rule_id}/diff?candidate_rule_id=…``（design §1.11 / §6.5）。

        ``rule_id`` 为 baseline、``candidate_rule_id`` 为候选；两者必须同工作区，否则 404
        （同一句 detail）。跨模板 → 422 ``TEMPLATE_MISMATCH``（``RULES.md``「候选同模板」）。
        ``requires_rerun_case_ids`` 只读 ``cases``：``state='CONFIRMED'`` 且 ``observed_rule_id``
        落在两者的 ``id``，升序去重；``changes`` 为空则直接 ``[]``（无字段变化即无需重跑）。
        """
        with connect(self._engine) as conn:
            baseline = self._rules.get(conn, workspace_id=workspace_id, rule_id=rule_id)
            if baseline is None:
                raise ResourceNotFound()
            candidate = self._rules.get(conn, workspace_id=workspace_id, rule_id=candidate_rule_id)
            if candidate is None:
                raise ResourceNotFound()
            baseline_template = json.loads(baseline.content_json).get("template")
            candidate_template = json.loads(candidate.content_json).get("template")
            if baseline_template != candidate_template:
                raise ValidationFailure(
                    _TEMPLATE_MISMATCH_DETAIL,
                    issues=[
                        Issue(
                            code=_TEMPLATE_MISMATCH_CODE,
                            location=_CANDIDATE_LOCATION,
                            message=_TEMPLATE_MISMATCH_DETAIL,
                            severity=_ERROR_SEVERITY,
                        )
                    ],
                )
            drafts = field_changes(
                baseline=_comparison_projection(baseline),
                candidate=_comparison_projection(candidate),
                canonicalize=canonical_json,
            )
            changes = [
                FieldChange(path=item.path, before=item.before, after=item.after) for item in drafts
            ]
            for change in changes:
                for value in (change.before, change.after):
                    # design §6.5：超限时截断会破坏可复查性 ⇒ 500，**不是截断**。
                    if value is not None and len(value) > FIELD_CHANGE_MAX_LENGTH:
                        raise InternalFailure("字段差异超出契约长度上限，拒绝截断返回")
            rerun: list[str] = []
            if changes:
                rerun = self._rules.list_confirmed_case_ids(
                    conn,
                    workspace_id=workspace_id,
                    rule_ids=[rule_id, candidate_rule_id],
                )
        return RuleDiff(
            baseline_rule_id=rule_id,
            candidate_rule_id=candidate_rule_id,
            changes=changes,
            requires_rerun_case_ids=rerun,
        )
