"""FastAPI 依赖提供器（M0-02 · S3c；design §6 指派 ``api/deps.py``）。

本文件被指派的符号：``get_config`` / ``get_clock`` / ``get_session_service`` /
``get_health_service`` / ``get_workspace_service`` / ``require_session``。

**交付边界（S3c 回报 Q 项，务必读完再改本文件）**

``SessionService`` / ``HealthService`` / ``WorkspaceService`` 以及 ``WorkerSupervisor``、
``JobStore``、``IdempotencyGuard`` 属 **S3d（Round 6）**（A11/A12：``application/worker.py`` 与
``infra/db/repositories.py`` 不在 S3c 写权限内）。S3c **不 stub 假实现**——假实现会被 S3d
复制成第二份，直接违反 ADR-005 §2.1。本文件只提供：

1. ``get_config`` / ``get_clock``：**已可工作**（读 ``app.state``，由 ``create_app()`` 装配）；
2. 三个 service 提供器的**装配位**：S3d 落地前显式抛 ``NotImplementedError``
   （经 ``install_error_handlers`` 收敛成 500 Problem，不返回任何编造数据）；
   落地后把函数体替换为真实装配即可，**签名不得改**（design §1 已冻结）；
3. ``HealthService`` / ``SessionService`` / ``WorkspaceService`` 三个 **Protocol 端口声明**：
   路由注解必须在运行期可解析（FastAPI 对路由函数做 ``get_type_hints``），而实现类还不存在。
   Protocol 让 S3d 的实现**结构化满足**即可，无需 import 本文件；
   **S3d 禁在 application 层再声明同名 Protocol**（避免第二份接口定义）。
   ``SessionService`` / ``WorkspaceService`` 当前是**空端口**：S3c 不猜方法名，
   成员由 S3b/S3d 落地时按 design §1 的调用点补全。

测试期注入用 ``app.dependency_overrides[get_health_service] = fake``，无需等 S3d。
"""

from __future__ import annotations

from typing import Protocol

from fastapi import Request

from campaignlab.api.common import Health, Session
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

_PENDING = (
    "{name} 尚未装配：其实现属 M0-02/S3d（Round 6，application 层）。"
    "S3c 依硬规则不 stub 假实现；测试期请用 app.dependency_overrides[{name}] 注入替身。"
)


class HealthService(Protocol):
    """端口：``api/health.py`` 只依赖 ``snapshot() -> Health``。

    ``Health`` 五字段全必填（design §2）；``contract_version`` 必须运行时取自活契约，
    ``schema_revision`` 取自 ``alembic_version`` 当前行，``worker`` 判定见 design §4。
    S3d 的 ``application/health_service.py::HealthService`` 必须结构化满足本协议。
    """

    def snapshot(self) -> Health: ...


class SessionService(Protocol):
    """端口占位（空）：成员由 S3b/S3d 按 design §1 的调用点补全，S3c 不猜方法名。"""


class WorkspaceService(Protocol):
    """端口占位（空）：同上。"""


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


def get_session_service(request: Request) -> SessionService:
    """装配位：实现属 S3d（``application/session_service.py``）。"""
    raise NotImplementedError(_PENDING.format(name="SessionService"))


def get_health_service(request: Request) -> HealthService:
    """装配位：实现属 S3d（``application/health_service.py``）。"""
    raise NotImplementedError(_PENDING.format(name="HealthService"))


def get_workspace_service(request: Request) -> WorkspaceService:
    """装配位：实现属 S3d（``application/workspace_service.py``）。"""
    raise NotImplementedError(_PENDING.format(name="WorkspaceService"))


def require_session(request: Request) -> Session:
    """会话依赖位（design §1：``actor: Session = Depends(require_session)``）。

    落地顺序（S3b/S3d）：① 校验 Host（GET）／Host+Origin（unsafe）——守卫中间件已在
    ``create_app()`` 装配；② 读 cookie ``cl_session``；③ 经 ``SessionService`` 查会话，
    未命中／已过期／进程重启后一律 **401 ``SESSION_EXPIRED`` 同码同 detail**（杜绝枚举 oracle）。
    S3c 不实现③（依赖 S3d 的 ``SessionStore``），故此处显式未实现。
    """
    raise NotImplementedError(_PENDING.format(name="SessionService"))
