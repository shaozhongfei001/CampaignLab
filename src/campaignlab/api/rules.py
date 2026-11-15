"""``campaignlab.api.rules``：rule versions 的 HTTP 面（M2-01 · S4 · design §1.5–§1.11）。

7 个 operationId：``listRules`` / ``createRule`` / ``getRule`` / ``updateRule`` /
``confirmRule`` / ``checkRule`` / ``compareRules``。公开符号面恰为 ``router`` 加这七个 handler，
私面恰为 ``_rule_version_response`` / ``_rule_version_page_response`` / ``_rule_check_response``
/ ``_rule_diff_response``（design §11.5 原文冻结；``__all__`` 字母序，
体例＝``api/jobs.py::__all__`` 的 RUF022 实测口径）。

体例逐字照抄同卡同层的 ``api/activities.py``（S3 交付件），禁自创：

- 路由只做「解析 → 调 service → 组装响应」，一条 SQL 都没有（PYTHON.md:5）；排序、键集、
  游标编解码、``status`` 白名单与 422 位置全在 ``application/activity_service.py``，本层只
  透传形参，不重算游标、不备第二把密钥、不备第二句 detail。
- 一个 ``router`` 装两族前缀（裁定 A255）：``.../activities/{activity_id}/rules`` 与
  ``.../rules/{rule_id}...`` 共用 ``prefix=API_PREFIX``，差异落在相对路径段内，故无需第二个
  router；形态与 ``api/activities.py`` 实测同形（``prefix`` ＋相对路径）。
- 错误路径一律 ``except DomainError`` 后交 ``problem_response``（``request_id_of`` 同一份）；
  本层**不**调用 ``check_if_match``：实测 ``RuleService.update_rule`` / ``confirm_rule`` 的签名
  已收 ``if_match``，428/412 由 service 侧判定（design §6.2；N5 禁两处都调）。
- ``If-Match`` 照 design §6.2 声明为**可选**形参并保留契约长度与正则：照契约的
  ``required=true`` 直译会让缺头在进入函数体前被判 422，428 永不可达；声明形态逐字照
  ``api/jobs.py::cancel_job`` 与 ``api/activities.py::update_activity`` 的 A228 先例（pattern
  取契约字面，仓内没有可 import 的 ``IF_MATCH_PATTERN`` 常量，三处正则必须字面相同）。
- ETag 出现面逐 op 以 design §6.1 的切片实取为准：``listRules`` / ``checkRule`` /
  ``compareRules`` 的 200 **无** ETag（切片 headers 实测只有 ``X-Request-Id``，禁发明），
  ``getRule`` 与三个写 op 带 ``etag(revision)``；幂等重放的 ETag 从信封取、禁重算。
  ``confirmRule`` 成功后同事务改 ``activities.current_rule_id`` 与 ``activities.revision``
  （design §3.2 行 310–314），故**活动自身的 ETag 也会变**——响应体是 ``RuleVersion``、
  ``ETag`` 是规则的新 revision，本层不做任何「补偿」。
- 三个写 op（``createRule`` 201 / ``updateRule`` 200 / ``confirmRule`` 200）一律走信封路径：
  实测 ``RuleWriteOutcome`` 与 ``ActivityWriteOutcome`` 同形（``as_envelope`` / ``body`` /
  ``headers`` / ``replayed`` / ``status``），状态码差别由 service 的 ``status`` 承载，
  禁在路由层再判一次 op 类型、禁自拼 ``Response``。
- 正文解析走冻结三连：``validate_idempotency_key`` → ``read_body_within_limit``（上限取
  ``get_config(request).max_json_body_bytes``）→ ``parse_json_body``，三个助手全部复用既有实现。
- 规则族 DTO 全部**运行期** import 自 ``api/common.py``（方案 A 已落地，A233 行 1394–1396
  明示本文件需要它们来构造响应体，**不需要**照抄 ``deps.py`` 的 ``TYPE_CHECKING`` 形态）；
  本文件不声明任何 DTO。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response

from campaignlab.api.common import (
    IDEMPOTENCY_KEY_HEADER,
    X_REQUEST_ID_HEADER,
    Confirmation,
    DomainError,
    RuleCheck,
    RuleCreate,
    RuleDiff,
    RuleUpdate,
    RuleVersion,
    RuleVersionPage,
    Session,
    etag,
    problem_response,
    read_body_within_limit,
    replay_from_envelope,
    request_id_of,
    validate_idempotency_key,
)
from campaignlab.api.deps import (
    RuleService,
    get_config,
    get_rule_service,
    require_session,
)
from campaignlab.api.session import JSON_MEDIA_TYPE, declared_responses, parse_json_body
from campaignlab.config import API_PREFIX
from campaignlab.domain.ids import RESOURCE_ID_PATTERN

__all__ = [
    "check_rule",
    "compare_rules",
    "confirm_rule",
    "create_rule",
    "get_rule",
    "list_rules",
    "router",
    "update_rule",
]

router = APIRouter(prefix=API_PREFIX, tags=["rules"])


def _rule_version_response(rule: RuleVersion, *, request_id: str, status: int = 200) -> Response:
    """单对象 → ``status`` 的 ``RuleVersion`` + ``ETag``（design §6.1：对象响应必带 ETag）。

    ``status`` 形参是 ``createRule`` 的 201 与其余 200 的**唯一**差别位；三个写 op 走信封
    路径，因此本助手实际只服务 ``getRule``（201/200 的差别在信封里，禁在此重判）。
    ``X-Request-Id`` 取 ``request_id_of`` 已求得的同一个 id，不新造第二个生成点。
    """
    return Response(
        content=rule.model_dump_json(),
        status_code=status,
        media_type=JSON_MEDIA_TYPE,
        headers={X_REQUEST_ID_HEADER: request_id, "ETag": etag(rule.revision)},
    )


def _rule_version_page_response(page: RuleVersionPage, *, request_id: str) -> Response:
    """``RuleVersionPage`` → 200，**无** ETag（design §6.1，与 ``ActivityPage`` 同处置）。"""
    return Response(
        content=page.model_dump_json(),
        status_code=200,
        media_type=JSON_MEDIA_TYPE,
        headers={X_REQUEST_ID_HEADER: request_id},
    )


def _rule_check_response(check: RuleCheck, *, request_id: str) -> Response:
    """``RuleCheck`` → 200，**无** ETag（design §6.1：切片 headers 实测只有 ``X-Request-Id``）。

    依裁定 A256 只做透传组装：**不**二次校验、**不**设 500 ``INTERNAL_ERROR`` 分支。理由＝
    ``BoundaryCase.input`` 的注解实测已是 ``CouponCaseInput | CallbackCaseInput`` 的判别联合
    （``discriminator="template"``），pydantic 在 service 构造 ``RuleCheck`` 时即完成校验，
    非法反例在类型上不可达响应层；design §11.5 的原意（框架自产反例不合法属服务端缺陷、
    禁静默丢弃）由上游构造期校验满足，强度不降。
    """
    return Response(
        content=check.model_dump_json(),
        status_code=200,
        media_type=JSON_MEDIA_TYPE,
        headers={X_REQUEST_ID_HEADER: request_id},
    )


def _rule_diff_response(diff: RuleDiff, *, request_id: str) -> Response:
    """``RuleDiff`` → 200，**无** ETag（design §6.1 同 ``RuleCheck`` 的只读计算面处置）。"""
    return Response(
        content=diff.model_dump_json(),
        status_code=200,
        media_type=JSON_MEDIA_TYPE,
        headers={X_REQUEST_ID_HEADER: request_id},
    )


@router.get(
    "/workspaces/{workspace_id}/activities/{activity_id}/rules",
    operation_id="listRules",
    responses=declared_responses(200),
)
async def list_rules(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    activity_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    cursor: str | None = Query(None, min_length=1, max_length=300),
    limit: int = Query(25, ge=1, le=100),
    q: str | None = Query(None, min_length=1, max_length=100),
    status: str | None = Query(None, min_length=1, max_length=60),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: RuleService = Depends(get_rule_service),  # noqa: B008
) -> Response:
    """``listRules``：200 ``RuleVersionPage``；四个 query 形参逐字透传（design §1.5）。

    参数名是 ``status`` 而被过滤的列是 ``rule_versions.state``（ADR-006 §4.7 点名的错位之一），
    按契约逐字实现、禁改名；``DRAFT`` / ``CONFIRMED`` 白名单与游标查询摘要（必须含
    ``activity_id``）的判定全在 service 侧，本层只把六个形参原样交出去。
    """
    request_id = request_id_of(request)
    try:
        page = svc.list_rules(
            actor=actor,
            workspace_id=workspace_id,
            activity_id=activity_id,
            cursor=cursor,
            limit=limit,
            q=q,
            status=status,
        )
        return _rule_version_page_response(page, request_id=request_id)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.post(
    "/workspaces/{workspace_id}/activities/{activity_id}/rules",
    operation_id="createRule",
    responses=declared_responses(201),
)
async def create_rule(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    activity_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    idempotency_key: str = Header(alias=IDEMPOTENCY_KEY_HEADER, min_length=8, max_length=128),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: RuleService = Depends(get_rule_service),  # noqa: B008
) -> Response:
    """``createRule``：201 ``RuleVersion`` + ``ETag``；**无 If-Match**（design §1.6）。

    调用面以实测签名为准：``create_rule`` 只收 ``workspace_id`` / ``activity_id`` / ``payload``
    / ``body`` / ``idempotency_key`` / ``actor`` / ``request_id`` 七个 kw 形参，**没有**
    ``if_match``，禁多传。新草稿 ``state=DRAFT``、``revision=1``、``parent_rule_id`` 的归属与
    父版本状态（404 / 409）判定全在 service 侧。
    """
    request_id = request_id_of(request)
    try:
        key = validate_idempotency_key(idempotency_key)
        max_bytes = get_config(request).max_json_body_bytes
        body = await read_body_within_limit(request, max_bytes=max_bytes)
        payload = parse_json_body(body, request.headers.get("content-type"), RuleCreate)
        outcome = svc.create_rule(
            workspace_id=workspace_id,
            activity_id=activity_id,
            payload=payload,
            body=body,
            idempotency_key=key,
            actor=actor,
            request_id=request_id,
        )
        return replay_from_envelope(outcome.as_envelope(), request_id=request_id)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.get(
    "/workspaces/{workspace_id}/rules/{rule_id}",
    operation_id="getRule",
    responses=declared_responses(200),
)
async def get_rule(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    rule_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: RuleService = Depends(get_rule_service),  # noqa: B008
) -> Response:
    """``getRule``：200 ``RuleVersion`` + ``ETag``；跨区与不存在同一 404（design §1.7 禁枚举）。

    路径里没有 ``activity_id``：活动归属由行内 ``rule_versions.activity_id`` 决定，工作区隔离
    仍按 ``workspace_id`` 严格校验，该判定在 service 侧，本层不回显 ID、不区分原因。
    """
    request_id = request_id_of(request)
    try:
        rule = svc.get_rule(workspace_id=workspace_id, rule_id=rule_id)
        return _rule_version_response(rule, request_id=request_id)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.patch(
    "/workspaces/{workspace_id}/rules/{rule_id}",
    operation_id="updateRule",
    responses=declared_responses(200),
)
async def update_rule(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    rule_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    idempotency_key: str = Header(alias=IDEMPOTENCY_KEY_HEADER, min_length=8, max_length=128),
    if_match: str | None = Header(
        alias="If-Match",
        default=None,
        min_length=3,
        max_length=32,
        pattern=r'^"[1-9][0-9]*"$',
    ),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: RuleService = Depends(get_rule_service),  # noqa: B008
) -> Response:
    """``updateRule``：200 ``RuleVersion`` + ``ETag``；缺 If-Match → 428、陈旧 → 412。

    ``if_match`` 声明为可选形参是 428 可达的前提（design §6.2 的陷阱；体例＝
    ``jobs.py::cancel_job`` 的 A228 先例）；428/412 与空 PATCH（``RuleUpdate.required`` 实测为
    空数组 ⇒ ``{}`` 能过 Schema，422 由 service 判）、状态机（已确认版本 409）的判定全在
    service 侧，本层只把 ``if_match`` 原样交出去。
    """
    request_id = request_id_of(request)
    try:
        key = validate_idempotency_key(idempotency_key)
        max_bytes = get_config(request).max_json_body_bytes
        body = await read_body_within_limit(request, max_bytes=max_bytes)
        payload = parse_json_body(body, request.headers.get("content-type"), RuleUpdate)
        outcome = svc.update_rule(
            workspace_id=workspace_id,
            rule_id=rule_id,
            payload=payload,
            body=body,
            idempotency_key=key,
            if_match=if_match,
            actor=actor,
            request_id=request_id,
        )
        return replay_from_envelope(outcome.as_envelope(), request_id=request_id)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.post(
    "/workspaces/{workspace_id}/rules/{rule_id}/confirm",
    operation_id="confirmRule",
    responses=declared_responses(200),
)
async def confirm_rule(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    rule_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    idempotency_key: str = Header(alias=IDEMPOTENCY_KEY_HEADER, min_length=8, max_length=128),
    if_match: str | None = Header(
        alias="If-Match",
        default=None,
        min_length=3,
        max_length=32,
        pattern=r'^"[1-9][0-9]*"$',
    ),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: RuleService = Depends(get_rule_service),  # noqa: B008
) -> Response:
    """``confirmRule``：200 ``RuleVersion`` + ``ETag``；正文 ``Confirmation`` 两字段全必填。

    门禁不通过 422 ``EVIDENCE_REQUIRED``、``digest`` 与当前摘要不符 409 ``VERSION_MISMATCH``、
    重复确认 409 ``STATE_CONFLICT``、缺/陈旧 If-Match 428/412（design §1.9 / §6.3 的第 7—9 步）
    全部由 service 判定；判定顺序即代码顺序，本层不重排、不补判。
    """
    request_id = request_id_of(request)
    try:
        key = validate_idempotency_key(idempotency_key)
        max_bytes = get_config(request).max_json_body_bytes
        body = await read_body_within_limit(request, max_bytes=max_bytes)
        payload = parse_json_body(body, request.headers.get("content-type"), Confirmation)
        outcome = svc.confirm_rule(
            workspace_id=workspace_id,
            rule_id=rule_id,
            payload=payload,
            body=body,
            idempotency_key=key,
            if_match=if_match,
            actor=actor,
            request_id=request_id,
        )
        return replay_from_envelope(outcome.as_envelope(), request_id=request_id)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.get(
    "/workspaces/{workspace_id}/rules/{rule_id}/checks",
    operation_id="checkRule",
    responses=declared_responses(200),
)
async def check_rule(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    rule_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: RuleService = Depends(get_rule_service),  # noqa: B008
) -> Response:
    """``checkRule``：200 ``RuleCheck``、**无 ETag**；只读、可重复调用（design §1.10）。

    结果只由 ``rule_versions`` 行内容决定，``rule_digest`` 取自该行 ``digest`` 列，本层不重算、
    不在响应里发明第二个值；金额分回放不归本 op（A203）。
    """
    request_id = request_id_of(request)
    try:
        check = svc.check_rule(workspace_id=workspace_id, rule_id=rule_id)
        return _rule_check_response(check, request_id=request_id)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.get(
    "/workspaces/{workspace_id}/rules/{rule_id}/diff",
    operation_id="compareRules",
    responses=declared_responses(200),
)
async def compare_rules(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    rule_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    candidate_rule_id: str = Query(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: RuleService = Depends(get_rule_service),  # noqa: B008
) -> Response:
    """``compareRules``：200 ``RuleDiff``、**无 ETag**；query ``candidate_rule_id`` 必填。

    ``rule_id`` 为 baseline、``candidate_rule_id`` 为候选。同工作区（否则 404 同一句 detail）
    与同模板（否则 422 ``VALIDATION_ERROR``、``issues[0].code="TEMPLATE_MISMATCH"``）的判定都在
    service 侧（design §1.11），本层只透传该形参，不预校验、不判跨区。
    """
    request_id = request_id_of(request)
    try:
        diff = svc.compare_rules(
            workspace_id=workspace_id, rule_id=rule_id, candidate_rule_id=candidate_rule_id
        )
        return _rule_diff_response(diff, request_id=request_id)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)
