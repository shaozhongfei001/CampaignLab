"""数据库文件路径的**唯一来源**（ADR-005 §2.4 裁定 1 / 裁定 2）。

裁定 1（路径约定）：库文件固定在 ``<data_dir>/state/campaignlab.db``，``<data_dir>``
默认 ``~/.local/share/campaignlab``。解析优先级由高到低共五级：

1. alembic ``-x db_path=<path>``（仅迁移期显式覆盖）
2. ``alembic.ini`` 的 ``sqlalchemy.url``（``set_main_option`` 注入）
3. 环境变量 ``CAMPAIGNLAB_DATABASE_URL``
4. 环境变量 ``CAMPAIGNLAB_DATA_DIR`` + ``/state/campaignlab.db``
5. 默认 ``~/.local/share/campaignlab/state/campaignlab.db``

裁定 2（单一来源，硬约束）：上述链条**只允许存在这一份**。``migrations/env.py``
（alembic 侧）与 ``infra/db/engine.py``（运行期侧）都必须 import 本模块，禁止各自复制
一份优先级链——否则 ``alembic upgrade`` 与运行期会作用于两个不同的库文件，
``Health.schema_revision`` 的判定随之失真。守护方式见 ``tests/unit/test_db_paths.py``：
既做 AST 静态守卫（两侧源码都不得再出现第二个优先级链的字面量），也做行为守卫
（真实跑一次 alembic，把它回填的连接串与运行期解析结果**逐字**比对）。

设计取向：本模块的解析函数一律是**纯函数**——环境变量与 home 都可注入
（``environ=`` / ``home=``），不隐式读全局状态，因此五级优先级可以在测试里逐级验证，
不需要真的去改进程环境或写到开发者家目录。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Final

from sqlalchemy.engine import make_url

__all__ = [
    "ALEMBIC_URL_ATTRIBUTE",
    "DATABASE_URL_ENV",
    "DATA_DIR_ENV",
    "DB_FILENAME",
    "DEFAULT_DATA_DIR_PARTS",
    "SQLITE_URL_PREFIX",
    "STATE_SUBDIR",
    "DatabaseLocation",
    "ResolutionLevel",
    "database_url_from_path",
    "default_data_dir",
    "ensure_parent_dir",
    "location_from_url",
    "resolve_database_location",
    "resolve_database_path",
    "resolve_database_url",
    "url_to_path",
]

#: 数据目录布局（OPERATIONS.md:17：数据目录含 state、raw、snapshots、results、exports、tmp、logs）
STATE_SUBDIR: Final = "state"
DB_FILENAME: Final = "campaignlab.db"
SQLITE_URL_PREFIX: Final = "sqlite:///"

#: 两个环境变量名。字符串只在本模块出现一次，两侧调用方一律引用常量，不得就地写字面量。
DATA_DIR_ENV: Final = "CAMPAIGNLAB_DATA_DIR"
DATABASE_URL_ENV: Final = "CAMPAIGNLAB_DATABASE_URL"

#: 未注入 ``CAMPAIGNLAB_DATA_DIR`` 时的默认数据目录（「当前用户可控目录」，OPERATIONS.md:17）
DEFAULT_DATA_DIR_PARTS: Final[tuple[str, ...]] = (".local", "share", "campaignlab")

#: alembic 侧把「本次真正使用的连接串」回填到 ``Config.attributes`` 的这个键上，
#: 供 ``tests/unit/test_db_paths.py`` 与运行期解析结果做逐字比对（ADR-005 §2.4 裁定 2）。
ALEMBIC_URL_ATTRIBUTE: Final = "campaignlab.resolved_database_url"


class ResolutionLevel(IntEnum):
    """命中了五级优先级中的哪一级（数值越小优先级越高）。

    ``CALLER_SUPPLIED = 0`` **不属于** ADR-005 §2.4 的五级链，它表示调用方直接把
    连接串塞了进来（例如运行期显式传 ``database_url=``），此时不做任何解析。
    """

    CALLER_SUPPLIED = 0
    X_DB_PATH = 1
    INI_URL = 2
    ENV_DATABASE_URL = 3
    ENV_DATA_DIR = 4
    DEFAULT_DATA_DIR = 5


@dataclass(frozen=True, slots=True)
class DatabaseLocation:
    """一次解析的完整结果：连接串、对应文件路径、命中的级别、人类可读的来源说明。"""

    url: str
    path: Path | None
    level: ResolutionLevel
    source: str


def _clean(value: str | None) -> str:
    """空串与纯空白一律视为「未提供」——否则空 ini 项会把后面四级全部遮蔽。"""
    return (value or "").strip()


def expand_user(raw: str, home: Path) -> Path:
    """把开头的 ``~`` / ``~/`` 展开为**注入的** home，保证解析结果可复现。

    ``~user`` 形式显式拒绝：它依赖 ``/etc/passwd``，无法在注入 home 下确定性展开，
    静默按字面量处理会得到一个谁也找不到的库文件。
    """
    if raw == "~":
        return home
    if raw.startswith("~/"):
        return home / raw[2:]
    if raw.startswith("~"):
        raise ValueError(f"不支持 ~user 形式的路径，无法在注入 home 下确定性展开：{raw!r}")
    return Path(raw)


def default_data_dir(home: Path | None = None) -> Path:
    """第五级兜底用的数据目录。"""
    return (Path.home() if home is None else home).joinpath(*DEFAULT_DATA_DIR_PARTS)


def database_path_in(data_dir: Path) -> Path:
    """ADR-005 §2.4 裁定 1：库文件相对数据目录的位置固定为 ``state/campaignlab.db``。"""
    return data_dir / STATE_SUBDIR / DB_FILENAME


def database_url_from_path(path: Path) -> str:
    """文件路径 -> SQLAlchemy 连接串（绝对路径会得到 ``sqlite:////abs/...`` 四斜杠形）。"""
    return SQLITE_URL_PREFIX + path.as_posix()


def url_to_path(url: str) -> Path | None:
    """连接串 -> 文件路径；``:memory:``、非文件型或非 sqlite 方言一律返回 ``None``。

    用 SQLAlchemy 自己的 URL 解析器而不是手撕字符串：``sqlite:////abs/x`` 与
    ``sqlite:///rel/x`` 的斜杠数差一位就会解析到完全不同的文件，这种地方不允许自己发明。
    """
    parsed = make_url(url)
    if parsed.drivername.split("+")[0] != "sqlite":
        return None
    database = parsed.database
    if database is None or database.strip() in {"", ":memory:"}:
        return None
    return Path(database)


def location_from_url(url: str, *, source: str = "调用方显式传入") -> DatabaseLocation:
    """把调用方直接给定的连接串包成 ``DatabaseLocation``（不经过五级链）。"""
    cleaned = _clean(url)
    if not cleaned:
        raise ValueError("调用方显式传入的连接串为空，拒绝静默回落到默认库路径")
    return DatabaseLocation(
        url=cleaned,
        path=url_to_path(cleaned),
        level=ResolutionLevel.CALLER_SUPPLIED,
        source=source,
    )


def resolve_database_location(
    *,
    x_db_path: str | None = None,
    ini_url: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> DatabaseLocation:
    """按 ADR-005 §2.4 裁定 1 的五级优先级解析库位置。

    ``environ`` / ``home`` 可注入（默认取进程真实值），``x_db_path`` / ``ini_url``
    只有 alembic 侧才有来源，运行期传 ``None`` 即可——**两侧调用的是同一个函数**，
    这正是「alembic 侧解析 == 运行期解析」能成立的原因。
    """
    env = os.environ if environ is None else environ
    base_home = Path.home() if home is None else home

    x_raw = _clean(x_db_path)
    if x_raw:
        path = expand_user(x_raw, base_home)
        return DatabaseLocation(
            url=database_url_from_path(path),
            path=path,
            level=ResolutionLevel.X_DB_PATH,
            source=f"alembic -x db_path={x_raw}",
        )

    ini_raw = _clean(ini_url)
    if ini_raw:
        return DatabaseLocation(
            url=ini_raw,
            path=url_to_path(ini_raw),
            level=ResolutionLevel.INI_URL,
            source="alembic.ini: sqlalchemy.url",
        )

    env_url = _clean(env.get(DATABASE_URL_ENV))
    if env_url:
        return DatabaseLocation(
            url=env_url,
            path=url_to_path(env_url),
            level=ResolutionLevel.ENV_DATABASE_URL,
            source=f"环境变量 {DATABASE_URL_ENV}",
        )

    data_raw = _clean(env.get(DATA_DIR_ENV))
    if data_raw:
        path = database_path_in(expand_user(data_raw, base_home))
        return DatabaseLocation(
            url=database_url_from_path(path),
            path=path,
            level=ResolutionLevel.ENV_DATA_DIR,
            source=f"环境变量 {DATA_DIR_ENV} + /{STATE_SUBDIR}/{DB_FILENAME}",
        )

    path = database_path_in(default_data_dir(base_home))
    return DatabaseLocation(
        url=database_url_from_path(path),
        path=path,
        level=ResolutionLevel.DEFAULT_DATA_DIR,
        source=f"默认 {'/'.join(DEFAULT_DATA_DIR_PARTS)}/{STATE_SUBDIR}/{DB_FILENAME}",
    )


def resolve_database_url(
    *,
    x_db_path: str | None = None,
    ini_url: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> str:
    """只要连接串时用这个（alembic 侧与运行期侧共用）。"""
    return resolve_database_location(
        x_db_path=x_db_path, ini_url=ini_url, environ=environ, home=home
    ).url


def resolve_database_path(
    *,
    x_db_path: str | None = None,
    ini_url: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """只要文件路径时用这个；解析结果不是文件型库就**显式报错**，不静默造一个路径出来。"""
    location = resolve_database_location(
        x_db_path=x_db_path, ini_url=ini_url, environ=environ, home=home
    )
    if location.path is None:
        raise ValueError(
            f"解析结果不是文件型 SQLite 库，无法给出路径：url={location.url!r} "
            f"level={location.level.name} source={location.source}"
        )
    return location.path


def ensure_parent_dir(location: DatabaseLocation | str | Path) -> None:
    """SQLite 不会自建父目录；文件型目标必须先 mkdir，否则报 unable to open database file。"""
    if isinstance(location, DatabaseLocation):
        path = location.path
    elif isinstance(location, Path):
        path = location
    else:
        path = url_to_path(location)
    if path is None or not path.is_absolute() or path.name in {":memory:", ""}:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
