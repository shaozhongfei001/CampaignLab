"""运行期引擎与连接装配（M0-02 · S3a）。

两条硬约束决定了本文件的形状：

1. **路径单一来源**（ADR-005 §2.4 裁定 2）：本文件**不解析**任何路径/连接串，
   一律调 ``campaignlab.infra.db.paths``。``make_engine()`` 不传 ``url`` 时走的就是
   与 ``migrations/env.py`` 完全相同的五级链，因此「alembic 建出来的库」与
   「运行期打开的库」必然是同一个文件——``Health.schema_revision`` 的判定才有意义。
2. **每请求短连接**（PYTHON.md：SQLite 连接短时持有；design §3：SQLite 连接不可跨
   线程）：默认 ``poolclass=NullPool``，不缓存连接、不跨线程复用，配合 ``connect()``
   上下文管理器把连接的生命周期压在一次请求内。

``PRAGMAS`` 是连接级 PRAGMA 的单一来源：``migrations/env.py`` 也 import 它，
所以「迁移期的库」与「运行期的库」外键口径一致——否则跨工作区外键负例只在
一侧被拒绝，等价性判定就是假绿。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

from sqlalchemy import Connection, Engine, create_engine, event
from sqlalchemy.pool import NullPool, Pool

from campaignlab.infra.db.paths import (
    DatabaseLocation,
    ensure_parent_dir,
    location_from_url,
    resolve_database_location,
)

__all__ = ["PRAGMAS", "apply_pragmas", "connect", "make_engine", "make_engine_from_location"]

#: 连接级 PRAGMA（OPERATIONS.md 的运行口径）。``journal_mode=DELETE``；WAL 留待后续评估，
#: 不在 M0-02 决定。``foreign_keys=ON`` 是外键负例能被拒绝的前提——SQLite 默认关闭外键。
PRAGMAS: Final[tuple[str, ...]] = ("foreign_keys=ON", "busy_timeout=5000", "journal_mode=DELETE")


def apply_pragmas(dbapi_connection: object, _connection_record: object = None) -> None:
    """SQLAlchemy ``connect`` 事件回调：每个新建的 DBAPI 连接立即执行 ``PRAGMAS``。

    非 ``sqlite3.Connection``（理论上不会出现）直接放过，不做静默假设。
    """
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    try:
        for pragma in PRAGMAS:
            cursor.execute(f"PRAGMA {pragma}")
    finally:
        cursor.close()


def make_engine_from_location(
    location: DatabaseLocation,
    *,
    echo: bool = False,
    poolclass: type[Pool] = NullPool,
) -> Engine:
    """按已解析好的 ``DatabaseLocation`` 建引擎，并挂上 PRAGMA 监听。"""
    ensure_parent_dir(location)
    engine = create_engine(location.url, echo=echo, poolclass=poolclass)
    event.listen(engine, "connect", apply_pragmas)
    return engine


def make_engine(
    url: str | None = None,
    *,
    echo: bool = False,
    poolclass: type[Pool] = NullPool,
) -> Engine:
    """建运行期引擎。

    ``url=None``（默认）→ 走 ``paths`` 的五级解析，与 alembic 侧同源；
    显式给 ``url`` → 记为 ``CALLER_SUPPLIED``，只用于测试与一次性脚本，
    **不得**成为生产路径的第二套解析口径。
    """
    location = location_from_url(url) if url is not None else resolve_database_location()
    return make_engine_from_location(location, echo=echo, poolclass=poolclass)


@contextmanager
def connect(engine: Engine) -> Iterator[Connection]:
    """每请求短连接：进出即开关，不把 ``Connection`` 泄漏到请求边界之外。"""
    connection = engine.connect()
    try:
        yield connection
    finally:
        connection.close()
