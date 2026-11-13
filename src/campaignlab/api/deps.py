"""FastAPI 依赖提供器（M0-02 · S3c；design §6 指派 ``api/deps.py``）。

本文件被指派的符号：``get_config`` / ``get_clock`` / ``get_session_service`` /
``get_health_service`` / ``get_workspace_service`` / ``require_session``。

**装配口径（S3d 落地，依裁定 A40/§9.2）**

五个提供器一律**同构**：只从 ``app.state`` 取，取不到就显式 ``raise RuntimeError``。
**禁静默回落**——静默构造一个默认实现，会让测试注入的小 TTL 配置被真实默认值悄悄替换，
413／过期用例随之假绿（``get_config`` 的 docstring 已点名这个失败模式）。
装配点是 ``api.app.create_app(session_service=..., health_service=..., workspace_service=...)``；
测试期可绕过提供器：``app.dependency_overrides[get_health_service] = fake``。

三个 **Protocol 端口**的成员面按 ``application/*`` 实现类的真实公开方法补全（结构化子类型）：
实现类**不 import 本文件**，本文件也**不 import 实现类**——运行期用 ``@runtime_checkable``
的 ``isinstance`` 做结构化校验，类型检查期由 mypy 比对成员签名。
``application`` 层没有、也不得有第二份同名 Protocol（ADR-005 §2.1）。

``require_session`` 只做「读 cookie → 交 ``SessionService.resolve()``」：Host／Origin 校验由
``create_app()`` 装配的守卫中间件在更外层完成，此处不重复，避免两处白名单口径漂移。
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, cast, runtime_checkable

from fastapi import Request

from campaignlab.api.common import Health, Session, WorkspaceCreate, WorkspacePage
from campaignlab.application.session_service import (
    SESSION_COOKIE_NAME,
    SessionCookie,
    SessionRecord,
)
from campaignlab.application.workspace_service import WorkspaceCreateOutcome
from campaignlab.clock import Clock
from campaignlab.config import AppConfig

__all__ = [
    "HealthService",
    "SessionService",
    "WorkspaceService",
    "get_clock",
    "get_config",
    "get_health_service",
    "get_session_service",
    "get_workspace_service",
    "require_session",
]


@runtime_checkable
class HealthService(Protocol):
    """端口：``api/health.py`` 只依赖 ``snapshot() -> Health``。

    ``Health`` 五字段全必填（design §2）；``contract_version`` 必须运行时取自活契约，
    ``schema_revision`` 取自 ``alembic_version`` 当前行，``worker`` 判定见 design §4。
    S3d 的 ``application/health_service.py::HealthService`` 必须结构化满足本协议。
    """

    def snapshot(self) -> Health: ...


@runtime_checkable
class SessionService(Protocol):
    """端口：``api/session.py`` 两个 op 与 ``require_session`` 依赖的成员面。

    实现＝``application/session_service.py::SessionService``。``now`` 一律由调用方从
    ``Depends(get_clock)`` 传入，application 层禁自取系统时间（design §2「显式时钟」）。
    ``exchange`` 与 ``resolve`` 的所有失效分支都抛同一个 ``SessionInvalid``（同码同 detail）。
    """

    def exchange(self, token: str, *, now: datetime) -> SessionRecord: ...

    def resolve(self, session_id: str | None, *, now: datetime) -> SessionRecord: ...

    def cookie(self, record: SessionRecord, *, now: datetime) -> SessionCookie: ...


@runtime_checkable
class WorkspaceService(Protocol):
    """端口：``api/workspaces.py`` 两个 op 依赖的成员面。

    实现＝``application/workspace_service.py::WorkspaceService``。
    CR-002（选项 B，已 MERGED）：``list_workspaces`` 只有 ``cursor`` / ``limit`` / ``q``，
    **没有 ``status``、没有 ``sort``**，故本端口不存在任何 status 白名单校验。
    ``create_workspace`` 返回纯数据结果（不返回 ``Response``）：状态码与头字段由路由组装，
    幂等重放时路由用 ``api.common.replay_from_envelope`` 回放信封并重新生成 ``X-Request-Id``。
    """

    def list_workspaces(
        self, *, actor: Session, cursor: str | None, limit: int, q: str | None
    ) -> WorkspacePage: ...

    def create_workspace(
        self,
        *,
        payload: WorkspaceCreate,
        body: bytes,
        idempotency_key: str,
        actor: Session,
        request_id: str,
    ) -> WorkspaceCreateOutcome: ...


def get_config(request: Request) -> AppConfig:
    """取本次应用的配置。必须由 ``create_app()`` 装配；缺失即报错，不静默 ``load_config()``。

    静默回落会让「测试注入的小 TTL 配置」被真实默认值悄悄替换，413／过期用例随之假绿。
    """
    config = getattr(request.app.state, "config", None)
    if not isinstance(config, AppConfig):
        raise RuntimeError(
            "app.state.config 未装配：应用必须经 campaignlab.api.app.create_app() 构造"
        )
    return config


def get_clock(request: Request) -> Clock:
    """取本次应用的时钟（``FixedClock`` 可注入，领域计算禁自取系统时间）。"""
    clock = getattr(request.app.state, "clock", None)
    if not isinstance(clock, Clock):
        raise RuntimeError(
            "app.state.clock 未装配：应用必须经 campaignlab.api.app.create_app() 构造"
        )
    return clock


def _state_service(request: Request, attribute: str, port: type) -> object:
    """三个服务提供器共用的取值口径：读 ``app.state``，缺失或形状不符即 ``RuntimeError``。

    ``port`` 是 ``@runtime_checkable`` 的 Protocol 类，故 ``isinstance`` 做的是**结构化**校验
    （有没有这些方法），不绑定具体实现类——测试替身与真实实现同样能通过。
    """
    service = getattr(request.app.state, attribute, None)
    if not isinstance(service, port):
        raise RuntimeError(
            f"app.state.{attribute} 未装配：应用必须经 campaignlab.api.app.create_app("
            f"{attribute}=...) 构造，或用 app.dependency_overrides 注入替身"
        )
    return service


def get_session_service(request: Request) -> SessionService:
    """取会话服务（实现：``application/session_service.py::SessionService``）。"""
    return cast(SessionService, _state_service(request, "session_service", SessionService))


def get_health_service(request: Request) -> HealthService:
    """取健康服务（实现：``application/health_service.py::HealthService``）。"""
    return cast(HealthService, _state_service(request, "health_service", HealthService))


def get_workspace_service(request: Request) -> WorkspaceService:
    """取工作区服务（实现：``application/workspace_service.py::WorkspaceService``）。"""
    return cast(WorkspaceService, _state_service(request, "workspace_service", WorkspaceService))


def require_session(request: Request) -> Session:
    """会话依赖位（design §1：``actor: Session = Depends(require_session)``）。

    落地顺序：① Host（GET）／Host+Origin（unsafe）校验由 ``create_app()`` 装配的守卫中间件
    在更外层完成，本函数不重复；② 读 cookie ``cl_session``；③ 交 ``SessionService.resolve()``
    判定，未命中／已过期／进程重启后一律 **401 ``SESSION_EXPIRED`` 同码同 detail**
    （``SessionInvalid`` 经 ``install_error_handlers`` 收敛，杜绝枚举 oracle）。
    """
    service = get_session_service(request)
    clock = get_clock(request)
    record = service.resolve(request.cookies.get(SESSION_COOKIE_NAME), now=clock.now())
    return record.to_session()
