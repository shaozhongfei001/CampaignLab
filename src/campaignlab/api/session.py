"""``exchangeSession`` / ``getSession`` 路由（M0-02 · S3b；design §1 第 1/2 条、§6）。

唯一契约权威是切片 ``orchestrator/handoff/M0-02-S3b.slice.json``：

- ``exchangeSession`` ``POST /api/v1/session/exchange`` 的 ``security`` 是**空列表** —— 它是建立
  会话的端点，自身不要求已有会话，故**不挂** ``require_session``；200 ``Session`` + ``Set-Cookie``，
  另声明 400/401/403/404/409/412/413/422/428/429/500。
- ``getSession`` ``GET /api/v1/session`` **未**写 ``security`` → 继承全局 ``LocalSession``，因此走
  ``Depends(require_session)``；200 ``Session``，另声明同上那 11 个 Problem 形。

路由只做「解析 → 调 service → 组装响应」（PYTHON.md:5 禁写 SQL）。令牌消费、会话落库、
``SESSION_EXPIRED`` 同码同 detail、Cookie 参数组的取值全部留在
``application/session_service.py``（S3d 已落地），本文件不复制任何一条判定。

与 design §1 冻结签名的口径差异（回报里已作为偏差提出）：冻结签名把正文写成
``payload: SessionExchange``，而 FastAPI 解析该形参时会自行消费请求流，
``common.read_body_within_limit`` 的两阶段 413 判定（design §4）随之失去触发面。为同时守住
「413 必走 ``read_body_within_limit``」与「其余形参名与 ``-> Response`` 返回类型逐字不变」，
这里把正文形参换成 ``request: Request`` 后手工读取校验，错误形状仍由 Problem 收敛。
"""

from __future__ import annotations

import json
from typing import Any, Final

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ValidationError

from campaignlab.api.common import (
    PROBLEM_MEDIA_TYPE,
    DomainError,
    Issue,
    Session,
    SessionExchange,
    problem_response,
    read_body_within_limit,
    request_id_of,
)
from campaignlab.api.deps import (
    SessionService,
    get_clock,
    get_config,
    get_session_service,
    require_session,
)
from campaignlab.application.session_service import SessionCookie
from campaignlab.clock import Clock
from campaignlab.config import API_PREFIX

__all__ = ["exchange_session", "get_session", "router"]

router = APIRouter(prefix=API_PREFIX, tags=["session"])

#: ``common.py`` 只导出 Problem 的媒体类型，JSON 的正媒体类型由路由侧自持。
JSON_MEDIA_TYPE: Final = "application/json"

#: 切片里 4 个 op 共同声明的 Problem 形状态码；2xx 由各装饰器按 op 补上。
PROBLEM_STATUSES: Final = (400, 401, 403, 404, 409, 412, 413, 422, 428, 429, 500)


def declared_responses(success_status: int) -> dict[int | str, dict[str, Any]]:
    """把切片声明的响应码集合如实落到装饰器上（自证面 ② 的实现侧）。"""
    declared: dict[int | str, dict[str, Any]] = {
        success_status: {"description": "业务结果或受理状态"}
    }
    for status in PROBLEM_STATUSES:
        declared[status] = {"description": PROBLEM_MEDIA_TYPE}
    return declared


def validation_issues(exc: ValidationError) -> list[Issue]:
    """pydantic 的字段错误 → 契约 ``issues[]``；``location`` 用 JSON Pointer 形状。"""
    issues: list[Issue] = []
    for err in exc.errors():
        pointer = "/".join(str(part) for part in err["loc"])
        message = str(err["msg"])
        issues.append(
            Issue(
                code="VALIDATION_ERROR",
                location=("/" + pointer)[:500] if pointer else "/",
                message=message[:500] if message else "字段校验失败",
                severity="ERROR",
            )
        )
    return issues


def parse_json_body[ModelT: BaseModel](
    raw: bytes, content_type: str | None, model: type[ModelT]
) -> ModelT:
    """Content-Type／JSON 语法 → 400；DTO 校验（含未知字段）→ 422。"""
    main_type = (content_type or "").split(";")[0].strip().lower()
    if main_type != JSON_MEDIA_TYPE:
        raise DomainError("Content-Type 必须是 application/json", code="BAD_REQUEST")
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DomainError("请求正文不是合法 JSON", code="BAD_REQUEST") from exc
    try:
        return model.model_validate(parsed)
    except ValidationError as exc:
        raise DomainError(
            "请求正文未通过契约校验",
            code="VALIDATION_ERROR",
            issues=validation_issues(exc),
        ) from exc


def render_session_cookie(cookie: SessionCookie) -> str:
    """把 ``SessionCookie`` 参数组渲染成单个 ``Set-Cookie`` 头值（属性顺序不影响语义）。"""
    attributes = [
        f"{cookie.name}={cookie.value}",
        f"Path={cookie.path}",
        f"Max-Age={cookie.max_age}",
    ]
    if cookie.httponly:
        attributes.append("HttpOnly")
    attributes.append(f"SameSite={cookie.samesite}")
    if cookie.secure:
        attributes.append("Secure")
    return "; ".join(attributes)


@router.post(
    "/session/exchange",
    operation_id="exchangeSession",
    responses=declared_responses(200),
)
async def exchange_session(
    request: Request,
    # A47 / 手册 §9.9：``Depends(...)`` 作形参默认值是 FastAPI 惯用法且被 design §1 冻结，
    # 与 ruff B008 直接冲突（改 Annotated 形会动冻结签名），故就地豁免。
    svc: SessionService = Depends(get_session_service),  # noqa: B008
    clock: Clock = Depends(get_clock),  # noqa: B008
) -> Response:
    """``exchangeSession``：一次性令牌换会话，200 ``Session`` + ``Set-Cookie``。"""
    request_id = request_id_of(request)
    try:
        max_bytes = get_config(request).max_json_body_bytes
        raw = await read_body_within_limit(request, max_bytes=max_bytes)
        payload = parse_json_body(raw, request.headers.get("content-type"), SessionExchange)
        now = clock.now()
        record = svc.exchange(payload.token, now=now)
        cookie = svc.cookie(record, now=now)
        return Response(
            content=record.to_session().model_dump_json(),
            status_code=200,
            media_type=JSON_MEDIA_TYPE,
            headers={"Set-Cookie": render_session_cookie(cookie)},
        )
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.get("/session", operation_id="getSession", responses=declared_responses(200))
async def get_session(
    request: Request,
    actor: Session = Depends(require_session),  # noqa: B008
) -> Response:
    """``getSession``：200 ``Session``。

    无 cookie／已过期／进程重启后由 ``require_session`` 抛 ``SessionInvalid``（401 同码同
    detail）；Host 非法由 ``create_app()`` 装配的回环守卫在更外层拦下（403）。
    """
    return Response(
        content=actor.model_dump_json(),
        status_code=200,
        media_type=JSON_MEDIA_TYPE,
    )
