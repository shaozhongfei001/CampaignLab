"""应用工厂（M0-02 · S3c；design §6 ``api/app.py:create_app``）。

A10 边界：本文件的 **CORS／中间件／异常处理装配属 S3c**；而 ``include_router(jobs.router)``
一类挂载语句（≤3 行）属 **M0-04/S4**——S3c **不得**添加任何 jobs 路由挂载，也不得创建
``api/jobs.py``。``api/session.py`` 与 ``api/workspaces.py`` 属 S3b（Round 6），本文件为它们
预留了明确的挂载位（注释），S3b 只需在此追加两行 ``include_router``。

三条装配硬约束：

1. ``openapi_url=docs_url=redoc_url=None``（``api/__init__.py``）：契约真值只在
   ``contracts/openapi.json``，**不得暴露第二个 OpenAPI 面**（否则前端会对着自动生成面开发）。
2. ``install_error_handlers(app)`` 必须**最后**添加中间件：Starlette 的 ``add_middleware``
   后加者在外层，只有让它最外层，``X-Request-Id`` 才会出现在**每个**响应上（含 403 与 500）。
3. 回环守卫自己翻译 ``DomainError``：守卫中间件位于用户中间件层，**在** Starlette 的
   ``ExceptionMiddleware`` 之外抛出，若不就地捕获就会被 ``ServerErrorMiddleware`` 兜成 500，
   而契约要求的是 403 ``ORIGIN_DENIED``。
"""

from __future__ import annotations

from typing import Final

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from campaignlab.api import health
from campaignlab.api.common import (
    DomainError,
    OriginHostGuard,
    install_error_handlers,
    loopback_allowlists,
    problem_response,
    request_id_of,
)
from campaignlab.api.deps import HealthService, SessionService, WorkspaceService
from campaignlab.clock import Clock, SystemClock
from campaignlab.config import AppConfig, load_config

__all__ = ["ALLOWED_HEADERS", "ALLOWED_METHODS", "create_app", "origin_host_guard_middleware"]

#: CORS 允许的方法＝契约实际用到的方法集（不放开 TRACE/CONNECT 之类）。
ALLOWED_METHODS: Final[tuple[str, ...]] = (
    "DELETE",
    "GET",
    "HEAD",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
)

#: CORS 允许的请求头：JSON 正文类型 + 幂等键 + 乐观并发 + 请求号回显。
ALLOWED_HEADERS: Final[tuple[str, ...]] = (
    "Content-Type",
    "ETag",
    "Idempotency-Key",
    "If-Match",
    "X-Request-Id",
)


async def origin_host_guard_middleware(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    """OPERATIONS.md：每次 unsafe 请求校验准确 Origin 与 Host；GET 只校验 Host。

    白名单来自 ``app.state.guard``（可注入）：``TestClient`` 默认 ``Host: testserver``
    且不带 Origin，不可注入就会让全部用例 403（``OriginHostGuard`` docstring 点名的失败模式）。
    """
    guard = getattr(request.app.state, "guard", None)
    if isinstance(guard, OriginHostGuard):
        try:
            guard.check(
                method=request.method,
                host=request.headers.get("host"),
                origin=request.headers.get("origin"),
            )
        except DomainError as exc:
            # 就地翻译成 Problem：本层在 ExceptionMiddleware 之外，抛出会被兜成 500。
            return problem_response(exc, request_id=request_id_of(request))
    return await call_next(request)


def create_app(
    config: AppConfig | None = None,
    *,
    clock: Clock | None = None,
    guard: OriginHostGuard | None = None,
    session_service: SessionService | None = None,
    health_service: HealthService | None = None,
    workspace_service: WorkspaceService | None = None,
) -> FastAPI:
    """构造 FastAPI 应用。

    六个参数全部**可注入**（配置／时钟／回环白名单／三个用例服务），因此测试能确定性地
    触发小 TTL、413 与 403 分支，而不必改进程环境或 sleep（ADR-005 §2.3）。

    后三个参数是 **S3d 的纯追加式扩围**：既有三个参数的语义与默认行为一字未改，
    ``openapi_url=docs_url=redoc_url=None``、中间件添加顺序（guard 最内 → CORS →
    request_id 最外，``install_error_handlers`` 最后）、守卫就地翻译 ``DomainError``
    的行为全部保持原样；本文件也**没有**新增任何 ``include_router``
    （``api/session.py`` / ``api/workspaces.py`` 的挂载属 S3b，Round 7）。

    **不注入就不装配**（刻意的，不是遗漏）：三个服务缺省时 ``app.state`` 上根本不存在
    对应属性，``api/deps.py`` 的提供器会显式 ``RuntimeError`` → 500 Problem。
    在本函数里静默构造默认实现会有两个后果：① 测试注入的小 TTL 配置被真实默认值悄悄
    替换，413／过期用例假绿；② ``tests/unit/test_api_app.py`` 钉住的「服务未装配 →
    ``/api/v1/health`` 返回 500 Problem」这条既有行为被破坏（该文件不在 S3d 写权限内）。
    真实装配由 ``cli.cmd_serve`` 与测试侧显式完成。
    """
    cfg = config if config is not None else load_config()
    resolved_clock: Clock = clock if clock is not None else SystemClock()
    resolved_guard = guard if guard is not None else OriginHostGuard(*loopback_allowlists(cfg.port))

    app = FastAPI(
        title="CampaignLab",
        version=cfg.app_version,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    app.state.config = cfg
    app.state.clock = resolved_clock
    app.state.guard = resolved_guard
    # ---- S3d 追加：仅在显式注入时挂载（见 create_app docstring 的「不注入就不装配」）----
    if session_service is not None:
        app.state.session_service = session_service
    if health_service is not None:
        app.state.health_service = health_service
    if workspace_service is not None:
        app.state.workspace_service = workspace_service

    # 添加顺序即嵌套顺序（后加者在外层）：guard 最内 → CORS → request_id 最外。
    # 故 CORS 预检 OPTIONS 不会先被回环守卫拦下，而每个响应都带 X-Request-Id。
    app.add_middleware(BaseHTTPMiddleware, dispatch=origin_host_guard_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(resolved_guard.allowed_origins),
        allow_credentials=True,
        allow_methods=list(ALLOWED_METHODS),
        allow_headers=list(ALLOWED_HEADERS),
        max_age=0,
    )
    install_error_handlers(app)

    app.include_router(health.router)
    # ---- 挂载位（S3c 不得代写）----
    # S3b（Round 6）：app.include_router(session.router) / app.include_router(workspaces.router)
    # M0-04/S4（A10 最小例外，≤3 行）：app.include_router(jobs.router)
    return app
