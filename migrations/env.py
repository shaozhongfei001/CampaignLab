"""Alembic 运行环境（M0-02 · S2 首迁；S3a 依 ADR-005 §2.4 裁定 2 重构为单一来源）。

职责只有三件，多一件都不做：

1. 取连接串 —— **不在本文件解析**，一律转发到 ``campaignlab.infra.db.paths``（唯一来源）；
2. 每个新建连接立即执行 SQLite PRAGMA —— 常量与回调同样来自 ``infra.db.engine``，不在此复制；
3. 把控制权交回 alembic 的 online / offline 迁移流程。

**历史留痕（只加注、不改写）**：S2 版本的本文件曾刻意「不 ``import campaignlab``」，理由是
迁移要能在裸环境下独立复现（AC-035），并据此自带了一份五级优先级链。ADR-005 §2.4
**裁定 2（硬约束）** 其后要求解析逻辑**只存在一份**、``migrations/env.py`` 必须 import
``src/campaignlab/infra/db/paths.py``——否则 ``alembic upgrade`` 与运行期可能作用于两个
不同的库文件，``Health.schema_revision`` 的判定随之失真。裁定 2 优先，本文件改为 import。
「可复现」的口径由 Q7 裁定后的 ``uv sync``（从 ``uv.lock`` 重建含 ``campaignlab`` 的环境）
承担，不再由「env.py 不依赖应用包」承担。

守护：``tests/unit/test_db_paths.py`` 既用 AST 静态断言本文件不再出现第二份优先级链
（不得出现 ``CAMPAIGNLAB_*`` 字面量、``sqlite:///`` 前缀、``os.environ``），也用行为断言
把本文件回填到 ``config.attributes`` 的连接串与运行期解析结果**逐字**比对。
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, event, pool

try:
    from campaignlab.infra.db import paths
    from campaignlab.infra.db.engine import apply_pragmas
except ModuleNotFoundError as exc:  # pragma: no cover - 环境未装好时的可读报错
    raise RuntimeError(
        "migrations/env.py 需要 import campaignlab.infra.db.paths（ADR-005 §2.4 裁定 2："
        "库路径解析必须单一来源）。请先在仓库根执行 `uv sync` 从 uv.lock 重建环境，"
        "再用 `uv run --no-sync alembic -c migrations/alembic.ini ...` 运行迁移。"
    ) from exc

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 首迁为手写 SQL，不做 autogenerate，故无 MetaData 可挂。
target_metadata = None


def resolve_database_url() -> str:
    """**转发**到单一来源，本函数自身不含任何优先级判断。

    只有 alembic 侧才有的两个来源（``-x db_path=`` 与 ``sqlalchemy.url`` 主选项）在这里取出、
    原样交给 ``paths.resolve_database_location``；环境变量与默认家目录两级由 ``paths`` 自己读。
    解析结果同时回填到 ``config.attributes``，供「alembic 侧解析 == 运行期解析」的断言比对。
    """
    x_args = context.get_x_argument(as_dictionary=True)
    location = paths.resolve_database_location(
        x_db_path=x_args.get("db_path"),
        ini_url=config.get_main_option("sqlalchemy.url"),
    )
    config.attributes[paths.ALEMBIC_URL_ATTRIBUTE] = location.url
    # SQLite 不会自建父目录；文件型 URL 必须先 mkdir，否则报 unable to open database file。
    paths.ensure_parent_dir(location)
    return location.url


def run_migrations_offline() -> None:
    """离线模式（``alembic upgrade head --sql``）：只产出 SQL 文本，不建连接。

    因此 PRAGMA 不会被执行 —— 离线产物仅供人工审阅，等价性判定一律走在线模式。
    """
    context.configure(
        url=resolve_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：建引擎 -> 挂 PRAGMA 监听 -> 在单连接单事务内跑完迁移。

    PRAGMA 常量与回调来自 ``infra.db.engine``（单一来源），故迁移期与运行期的外键口径一致；
    ``NullPool`` 保证迁移用完即弃，不给后续步骤留下跨线程连接。
    """
    engine = create_engine(resolve_database_url(), poolclass=pool.NullPool)
    event.listen(engine, "connect", apply_pragmas)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
