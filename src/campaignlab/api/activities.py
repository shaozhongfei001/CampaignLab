"""``campaignlab.api.activities``：activities 的 HTTP 面（M2-01 · S3 · design §1 / §6.1 / §11.4）。

4 个 operationId：``listActivities`` / ``createActivity`` / ``getActivity`` / ``updateActivity``。
公开符号面恰为 ``router, list_activities, create_activity, get_activity, update_activity``，
私面恰为 ``_activity_response, _activity_page_response``（design §11.4 原文冻结；
``__all__`` 字母序，体例＝``api/jobs.py::__all__`` 的 RUF022 实测口径）。

体例照抄 ``api/workspaces.py`` 与 ``api/jobs.py`` 的实测先例，禁自创：

- 路由只做「解析 → 调 service → 组装响应」，一条 SQL 都没有（PYTHON.md:5）；排序、键集、
  游标编解码、白名单与 422 位置全在 ``application/activity_service.py``，本层只透传四个
  query 形参，不重算游标、不备第二把密钥、不备第二句 detail。
- 错误路径一律 ``except DomainError`` 后交 ``problem_response``（``request_id_of`` 同一份）；
  本层**不**调用 ``check_if_match``：实测 ``update_activity`` 签名已收 ``if_match``，428/412
  由 service 侧判定（两者择一的口径取 service 调，N5 禁两处都调）。
- ``If-Match`` 照 design §1.4/§6.2 声明为**可选**形参并保留契约长度与正则：照契约的
  ``required=true`` 直译会让缺头在进入函数体前被判 422，428 永不可达；形参声明形态
  逐字照 ``api/jobs.py::cancel_job`` 的 A228 先例（pattern 取契约字面，仓内没有可 import
  的 ``IF_MATCH_PATTERN`` 常量，见派单 §9 U 项）。
- ETag 出现面逐 op 以 design §6.1 为准：列表 200 **无** ETag（切片 headers 实测只有
  ``X-Request-Id``，禁发明），对象响应带 ``etag(revision)``；幂等重放的 ETag 从信封取、
  禁重算（``replay_from_envelope`` 的既有口径）。
- ``createActivity`` / ``updateActivity`` 走信封路径（两个 Outcome 均有 ``as_envelope()`` 且
  刻意不含 ``X-Request-Id``，重放时由 ``request_id`` 覆盖），禁在路由里自拼 ``Response``；
  ``listActivities`` / ``getActivity`` 无信封，走两个私有助手。
- 正文解析走冻结三连：``validate_idempotency_key`` → ``read_body_within_limit``（上限取
  ``get_config(request).max_json_body_bytes``）→ ``parse_json_body``，三个助手全部复用既有实现。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response

from campaignlab.api.common import (
    IDEMPOTENCY_KEY_HEADER,
    X_REQUEST_ID_HEADER,
    Activity,
    ActivityCreate,
    ActivityPage,
    ActivityUpdate,
    DomainError,
    Session,
    etag,
    problem_response,
    read_body_within_limit,
    replay_from_envelope,
    request_id_of,
    validate_idempotency_key,
)
from campaignlab.api.deps import (
    ActivityService,
    get_activity_service,
    get_config,
    require_session,
)
from campaignlab.api.session import JSON_MEDIA_TYPE, declared_responses, parse_json_body
from campaignlab.config import API_PREFIX
from campaignlab.domain.ids import RESOURCE_ID_PATTERN

__all__ = ["create_activity", "get_activity", "list_activities", "router", "update_activity"]

router = APIRouter(prefix=API_PREFIX, tags=["activities"])


def _activity_response(activity: Activity, *, request_id: str, status: int = 200) -> Response:
    """单对象 → ``status`` 的 ``Activity`` + ``ETag``（design §6.1：对象响应必带 ETag）。

    ``X-Request-Id`` 取 ``request_id_of`` 已求得的同一个 id（``replay_from_envelope`` 在
    信封路径上的既有头部口径），不新造第二个生成点。
    """
    return Response(
        content=activity.model_dump_json(),
        status_code=status,
        media_type=JSON_MEDIA_TYPE,
        headers={X_REQUEST_ID_HEADER: request_id, "ETag": etag(activity.revision)},
    )


def _activity_page_response(page: ActivityPage, *, request_id: str) -> Response:
    """``ActivityPage`` → 200，**无** ETag（design §6.1，与 ``WorkspacePage`` 同处置）。"""
    return Response(
        content=page.model_dump_json(),
        status_code=200,
        media_type=JSON_MEDIA_TYPE,
        headers={X_REQUEST_ID_HEADER: request_id},
    )


@router.get(
    "/workspaces/{workspace_id}/activities",
    operation_id="listActivities",
    responses=declared_responses(200),
)
async def list_activities(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    cursor: str | None = Query(None, min_length=1, max_length=300),
    limit: int = Query(25, ge=1, le=100),
    q: str | None = Query(None, min_length=1, max_length=100),
    status: str | None = Query(None, min_length=1, max_length=60),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: ActivityService = Depends(get_activity_service),  # noqa: B008
) -> Response:
    """``listActivities``：200 ``ActivityPage``；四个 query 形参逐字透传（design §1.1）。"""
    request_id = request_id_of(request)
    try:
        page = svc.list_activities(
            actor=actor,
            workspace_id=workspace_id,
            cursor=cursor,
            limit=limit,
            q=q,
            status=status,
        )
        return _activity_page_response(page, request_id=request_id)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.post(
    "/workspaces/{workspace_id}/activities",
    operation_id="createActivity",
    responses=declared_responses(201),
)
async def create_activity(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    idempotency_key: str = Header(alias=IDEMPOTENCY_KEY_HEADER, min_length=8, max_length=128),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: ActivityService = Depends(get_activity_service),  # noqa: B008
) -> Response:
    """``createActivity``：201 ``Activity`` + ``ETag``；同键同体重放逐字节相同（design §1.2）。

    关键字名以实测签名为准：``create_activity`` 收 ``workspace_id``（体例＝design §3.3 的
    workspace 示例再前置该形参，派单文已预告「真实关键字名以实测为准」）。
    """
    request_id = request_id_of(request)
    try:
        key = validate_idempotency_key(idempotency_key)
        max_bytes = get_config(request).max_json_body_bytes
        body = await read_body_within_limit(request, max_bytes=max_bytes)
        payload = parse_json_body(body, request.headers.get("content-type"), ActivityCreate)
        outcome = svc.create_activity(
            workspace_id=workspace_id,
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
    "/workspaces/{workspace_id}/activities/{activity_id}",
    operation_id="getActivity",
    responses=declared_responses(200),
)
async def get_activity(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    activity_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: ActivityService = Depends(get_activity_service),  # noqa: B008
) -> Response:
    """``getActivity``：200 ``Activity`` + ``ETag``；跨区与不存在同一 404（§1.3 禁枚举）。"""
    request_id = request_id_of(request)
    try:
        activity = svc.get_activity(workspace_id=workspace_id, activity_id=activity_id)
        return _activity_response(activity, request_id=request_id)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.patch(
    "/workspaces/{workspace_id}/activities/{activity_id}",
    operation_id="updateActivity",
    responses=declared_responses(200),
)
async def update_activity(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    activity_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    idempotency_key: str = Header(alias=IDEMPOTENCY_KEY_HEADER, min_length=8, max_length=128),
    if_match: str | None = Header(
        alias="If-Match",
        default=None,
        min_length=3,
        max_length=32,
        pattern=r'^"[1-9][0-9]*"$',
    ),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: ActivityService = Depends(get_activity_service),  # noqa: B008
) -> Response:
    """``updateActivity``：200 ``Activity`` + ``ETag``；缺 If-Match → 428、陈旧 → 412。

    ``if_match`` 声明为可选形参是 428 可达的前提（§6.2 的陷阱；体例＝``jobs.py::cancel_job``
    的 A228 先例）；428/412 与空 PATCH（422）、状态机（409）、绑定门禁（422）的判定全在
    service 侧，本层只把 ``if_match`` 原样交出去。
    """
    request_id = request_id_of(request)
    try:
        key = validate_idempotency_key(idempotency_key)
        max_bytes = get_config(request).max_json_body_bytes
        body = await read_body_within_limit(request, max_bytes=max_bytes)
        payload = parse_json_body(body, request.headers.get("content-type"), ActivityUpdate)
        outcome = svc.update_activity(
            workspace_id=workspace_id,
            activity_id=activity_id,
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
