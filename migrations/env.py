"""Alembic 运行环境（M0-02 · S2 首迁）。

职责只有三件，多一件都不做：

1. 解析数据库连接串 —— 禁止硬编码（D-004 的教训），优先级见 ``resolve_database_url``；
2. 每个新建连接立即执行 SQLite PRAGMA —— ``foreign_keys=ON`` 是外键负例能被拒绝的前提，
   ``busy_timeout`` / ``journal_mode`` 取 OPERATIONS.md 的运行口径；
3. 把控制权交回 alembic 的 online / offline 迁移流程。

本文件刻意 **不** ``import campaignlab``：迁移必须能在裸环境（只有锁文件里的依赖、
没有应用代码）下独立复现，这是 AC-035「按 M0 锁版本、迁移」可被第三方复核的前提。
数据目录约定来自 spec/CampaignLab-SDD-v1.0/architecture/OPERATIONS.md:17
（``CAMPAIGNLAB_DATA_DIR``，默认放在当前用户可控目录）。
"""

from __future__ import annotations

import os
import sqlite3
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, event, pool

# 数据目录布局（OPERATIONS.md：数据目录含 state、raw、snapshots、results、exports、tmp、logs）
_STATE_SUBDIR = "state"
_DB_FILENAME = "campaignlab.db"
_SQLITE_PREFIX = "sqlite:///"

# 运行期 PRAGMA。journal_mode=DELETE 依 OPERATIONS.md；WAL 留待后续评估，不在 M0-02 决定。
_PRAGMAS: tuple[str, ...] = ("foreign_keys=ON", "busy_timeout=5000", "journal_mode=DELETE")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 首迁为手写 SQL，不做 autogenerate，故无 MetaData 可挂。
target_metadata = None


def _default_data_dir() -> Path:
    """未被 CAMPAIGNLAB_DATA_DIR 覆盖时的数据目录（当前用户可控目录）。"""
    return Path.home() / ".local" / "share" / "campaignlab"


def _data_dir_db_url() -> str:
    raw = os.environ.get("CAMPAIGNLAB_DATA_DIR")
    data_dir = Path(raw).expanduser() if raw else _default_data_dir()
    db_path = data_dir / _STATE_SUBDIR / _DB_FILENAME
    return _SQLITE_PREFIX + db_path.as_posix()


def _ensure_parent_dir(url: str) -> None:
    """SQLite 不会自建父目录；文件型 URL 必须先 mkdir，否则报 unable to open database file。"""
    if not url.startswith(_SQLITE_PREFIX):
        return
    path = Path(url[len(_SQLITE_PREFIX) :])
    if not path.is_absolute() or path.name in {":memory:", ""}:
        return
    path.parent.mkdir(parents=True, exist_ok=True)


def resolve_database_url() -> str:
    """按优先级解析连接串，返回可直接交给 SQLAlchemy 的 URL。

    1. ``-x db_path=<path>``        —— CLI / 工具注入（alembic 惯例的 x-arg）
    2. ``sqlalchemy.url`` 主选项    —— 调用方用 ``Config.set_main_option`` 注入（测试走这条）
    3. ``CAMPAIGNLAB_DATABASE_URL`` —— 运维显式覆盖
    4. ``CAMPAIGNLAB_DATA_DIR``     —— OPERATIONS.md 的数据目录口径
    5. ``~/.local/share/campaignlab`` —— 「默认放在当前用户可控目录」
    """
    x_args = context.get_x_argument(as_dictionary=True)
    db_path = x_args.get("db_path")
    if db_path:
        url = _SQLITE_PREFIX + Path(db_path).expanduser().as_posix()
    else:
        from_ini = config.get_main_option("sqlalchemy.url")
        from_env = os.environ.get("CAMPAIGNLAB_DATABASE_URL")
        url = (from_ini or "").strip() or (from_env or "").strip() or _data_dir_db_url()
    _ensure_parent_dir(url)
    return url


def _apply_pragmas(dbapi_connection: object, _connection_record: object) -> None:
    """连接级 PRAGMA。非 sqlite3 连接（理论上不会出现）直接放过，不做静默假设。"""
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    try:
        for pragma in _PRAGMAS:
            cursor.execute(f"PRAGMA {pragma}")
    finally:
        cursor.close()


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
    """在线模式：建引擎 -> 挂 PRAGMA 监听 -> 在单连接单事务内跑完迁移。"""
    engine = create_engine(resolve_database_url(), poolclass=pool.NullPool)
    event.listen(engine, "connect", _apply_pragmas)
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
