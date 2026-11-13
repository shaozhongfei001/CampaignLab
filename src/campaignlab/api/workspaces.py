"""``listWorkspaces`` / ``createWorkspace`` 路由（M0-02 · S3b；design §1 第 4/5 条、§6）。

唯一契约权威是切片 ``orchestrator/handoff/M0-02-S3b.slice.json``：两个 op 都**未**写
``security`` → 继承全局 ``LocalSession``，故一律 ``actor: Session = Depends(require_session)``；
``listWorkspaces`` 声明 200 + 11 个 Problem 形，``createWorkspace`` 声明 201 + 同样 11 个。

**CR-002（选项 B，已 MERGED，ADR-006）**：``status`` 查询参数已从活契约的 ``listWorkspaces``
移除，本实现因此**只有** ``cursor`` / ``limit`` / ``q`` 三个 query 形参，原先为 ``status``
白名单准备的 422 分支也随之删除（无触发面）。该裁定**只**作用于 ``listWorkspaces``，其它
list* op 的 ``status`` 参数不受影响。ETag 口径同样以切片为准：只有 ``createWorkspace`` 的
201 声明了 ``ETag``，``WorkspacePage`` 与 ``Session`` 都没有 ``revision`` 字段，不发明 ETag。

游标编解码、幂等键摘要与重放信封都留在 application/service 侧
（``WorkspaceService`` 内部调用 ``common.encode_cursor`` / ``decode_cursor``），路由不实现
第二份；本文件同样只做「解析 → 调 service → 组装响应」（PYTHON.md:5 禁写 SQL）。

正文解析复用 ``api/session.py`` 的同名私有助手（``scope_deny`` 禁改 ``api/common.py``，
把第三个私有助手面复制两份比重用更容易漂移）；签名口径差异与 design §1 的那一处偏差，
见 ``api/session.py`` 模块 docstring。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from campaignlab.api.common import (
    IDEMPOTENCY_KEY_HEADER,
    DomainError,
    Session,
    WorkspaceCreate,
    problem_response,
    read_body_within_limit,
    replay_from_envelope,
    request_id_of,
    validate_idempotency_key,
)
from campaignlab.api.deps import (
    WorkspaceService,
    get_config,
    get_workspace_service,
    require_session,
)
from campaignlab.api.session import (
    JSON_MEDIA_TYPE,
    declared_responses,
    parse_json_body,
)
from campaignlab.config import API_PREFIX

__all__ = ["create_workspace", "list_workspaces", "router"]

router = APIRouter(prefix=API_PREFIX, tags=["workspaces"])


@router.get("/workspaces", operation_id="listWorkspaces", responses=declared_responses(200))
async def list_workspaces(
    request: Request,
    # A47 / 手册 §9.9：``Depends(...)`` 作形参默认值与 ruff B008 冲突，且该形状被 design §1
    # 冻结（改 ``Annotated`` 形会动冻结签名），故就地豁免；``Query``/``Header`` 实测不触发 B008。
    cursor: str | None = Query(None, min_length=1, max_length=300),
    limit: int = Query(25, ge=1, le=100),
    q: str | None = Query(None, min_length=1, max_length=100),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: WorkspaceService = Depends(get_workspace_service),  # noqa: B008
) -> Response:
    """``listWorkspaces``：200 ``WorkspacePage``；游标不匹配当前筛选/actor → 400。"""
    request_id = request_id_of(request)
    try:
        page = svc.list_workspaces(actor=actor, cursor=cursor, limit=limit, q=q)
        return Response(
            content=page.model_dump_json(),
            status_code=200,
            media_type=JSON_MEDIA_TYPE,
        )
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.post(
    "/workspaces",
    operation_id="createWorkspace",
    responses=declared_responses(201),
)
async def create_workspace(
    request: Request,
    idempotency_key: str = Header(alias=IDEMPOTENCY_KEY_HEADER, min_length=8, max_length=128),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: WorkspaceService = Depends(get_workspace_service),  # noqa: B008
) -> Response:
    """``createWorkspace``：201 ``Workspace`` + ``ETag``；同键同摘要重放逐字节相同。

    ``Idempotency-Key`` 先过 ``validate_idempotency_key``（8–128，
    ``issues[0].location="/header/Idempotency-Key"``）；正文大小走
    ``read_body_within_limit``（上限来自 ``AppConfig.MAX_JSON_BODY_BYTES``）；新建与重放共用
    ``replay_from_envelope``，故两条路径的正文与 ``ETag`` 必然逐字节一致（design §4）。
    """
    request_id = request_id_of(request)
    try:
        key = validate_idempotency_key(idempotency_key)
        max_bytes = get_config(request).max_json_body_bytes
        body = await read_body_within_limit(request, max_bytes=max_bytes)
        payload = parse_json_body(body, request.headers.get("content-type"), WorkspaceCreate)
        outcome = svc.create_workspace(
            payload=payload,
            body=body,
            idempotency_key=key,
            actor=actor,
            request_id=request_id,
        )
        return replay_from_envelope(outcome.as_envelope(), request_id=request_id)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)
