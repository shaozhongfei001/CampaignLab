"""应用层入口（M0-02 · S3a 交付的**装配面**）。

层次与依赖方向（PYTHON.md：分层保持依赖朝领域内收）::

    api/  ──▶  application/  ──▶  domain/ , infra/

应用层的职责只有两条：**用例编排** 与 **事务边界**（「服务层应用事务，不在路由里直接写 SQL」）。
路由函数只做「解析 → 调 application → 组装响应」，SQL 一律下沉到 infra。

本文件当前只承载 S3a 被指派的那部分装配：**运行期数据库装配**。它是 ADR-005 §2.4
裁定 2 的运行期一侧——与 ``migrations/env.py`` 共用 ``infra/db/paths.py`` 的同一份五级解析，
因此「alembic 建出来的库」与「运行期打开的库」必然是同一个文件，
``Health.schema_revision``（取自 ``alembic_version`` 当前行）的判定才成立。

**交付边界说明（S3a 回报 Q2）**：design §6 列在 ``application/`` 下的用例服务
（``session_service.py`` / ``workspace_service.py`` / ``health_service.py`` /
``idempotency.py`` / ``audit.py`` / ``worker.py``）**不在 R4-1 档位表 v2 给 S3a 的产出列里**，
且它们依赖同样未被指派的 ``config.py`` / ``clock.py`` / ``domain/**`` /
``infra/db/repositories.py``。本轮**不预先实现**，以免与后续轮次重复造同一批符号；
本文件因此只提供不依赖上述缺件的装配入口。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sqlalchemy.engine import Engine

from campaignlab.infra.db.engine import make_engine_from_location
from campaignlab.infra.db.paths import (
    DatabaseLocation,
    ResolutionLevel,
    location_from_url,
    resolve_database_location,
)

__all__ = ["DatabaseRuntime", "build_database_runtime"]


@dataclass(frozen=True, slots=True)
class DatabaseRuntime:
    """一次装配的结果：解析到的库位置 + 已挂好 PRAGMA 监听的引擎。

    刻意把 ``location`` 一并带出来：``Health.schema_revision`` 与 doctor 需要能回答
    「我现在连的到底是哪个文件、它是被五级链里的哪一级选中的」，只给一个 ``Engine``
    会让这两个问题退化成靠字符串猜。
    """

    location: DatabaseLocation
    engine: Engine

    @property
    def url(self) -> str:
        return self.location.url

    @property
    def path(self) -> Path | None:
        return self.location.path

    @property
    def level(self) -> ResolutionLevel:
        return self.location.level

    def dispose(self) -> None:
        """释放引擎。默认 ``NullPool`` 下没有连接池可清，但 ``echo``/自定义 poolclass 时需要。"""
        self.engine.dispose()


def build_database_runtime(
    *,
    database_url: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    echo: bool = False,
) -> DatabaseRuntime:
    """装配运行期数据库。

    ``database_url=None``（生产默认）→ 走 ``paths`` 的五级解析，与 alembic 侧同源；
    显式给 ``database_url`` → 记为 ``CALLER_SUPPLIED``，只供测试与一次性脚本使用。
    ``environ`` / ``home`` 可注入，因此装配结果在测试里可复现，不必改动进程环境。
    """
    location: Final = (
        location_from_url(database_url, source="build_database_runtime(database_url=...)")
        if database_url is not None
        else resolve_database_location(environ=environ, home=home)
    )
    return DatabaseRuntime(location=location, engine=make_engine_from_location(location, echo=echo))
