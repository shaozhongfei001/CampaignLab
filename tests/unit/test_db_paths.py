"""ADR-005 §2.4 的机器守护：库路径单一来源 + 五级优先级 + 完整可逆（M0-02 · S3a）。

三类断言，缺一不可：

1. **单一来源（裁定 2，本文件存在的理由）**：``migrations/env.py``（alembic 侧）与
   ``infra/db/engine.py``（运行期侧）都不得自带第二份优先级链——先用 AST 静态守卫钉住；
   再**真实跑一次 alembic**，把它回填到 ``Config.attributes`` 的连接串与同一组环境下
   运行期解析出的连接串**逐字**比对。只有静态守卫会漏掉「import 了但没用」，
   只有行为守卫会漏掉「这次恰好相等、下次各自漂移」，所以两个都要。
2. **五级优先级（裁定 1）**：逐级验证高优先级遮蔽低优先级、空值穿透、``~`` 展开、默认落点。
   解析函数是纯函数（``environ=`` / ``home=`` 可注入），故不必改动进程环境即可逐级验证。
3. **完整可逆（裁定 3）**：``downgrade base`` 之后业务表 **0 张** + 仅剩**空的**
   ``alembic_version``；``alembic_version`` 不计入 28 表分母。

不写死任何计数分母：28 表取自 ``ddl_compare.EXPECTED_TABLE_COUNT``（与迁移等价性测试同源）。
"""

from __future__ import annotations

import argparse
import ast
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from campaignlab.application import build_database_runtime
from campaignlab.infra.db import paths
from campaignlab.infra.db.ddl_compare import EXPECTED_TABLE_COUNT, table_names
from campaignlab.infra.db.engine import PRAGMAS, connect
from campaignlab.infra.db.paths import ResolutionLevel

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = REPO_ROOT / "migrations" / "alembic.ini"
ENV_PY = REPO_ROOT / "migrations" / "env.py"
ENGINE_PY = REPO_ROOT / "src" / "campaignlab" / "infra" / "db" / "engine.py"
HEAD_REVISION = "0001_initial_schema"
ALEMBIC_BOOKKEEPING_TABLE = "alembic_version"

#: 一旦这些字面量重新出现在 env.py / engine.py 的**代码**里，就说明有人绕开单一来源
#: 又抄了一份优先级链（ADR-005 §2.4 裁定 2 明令禁止）。
FORBIDDEN_LITERALS: frozenset[str] = frozenset(
    {
        paths.DATA_DIR_ENV,
        paths.DATABASE_URL_ENV,
        paths.SQLITE_URL_PREFIX,
        paths.DB_FILENAME,
        paths.STATE_SUBDIR,
    }
)


# ----------------------------------------------------------------------------- 工具函数


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """清掉两个数据库相关环境变量，避免开发者本机环境把用例带偏。"""
    monkeypatch.delenv(paths.DATA_DIR_ENV, raising=False)
    monkeypatch.delenv(paths.DATABASE_URL_ENV, raising=False)


def _alembic_config(*, ini_url: str | None = None, x_db_path: str | None = None) -> Config:
    """构造与真实 CLI 等价的 alembic 配置。

    ``-x db_path=`` 在 CLI 下由 argparse 注入到 ``Config.cmd_opts.x``，
    ``EnvironmentContext.get_x_argument`` 正是从这里取值，故进程内复现同一形状即可。
    """
    cfg = Config(str(ALEMBIC_INI))
    if ini_url is not None:
        cfg.set_main_option("sqlalchemy.url", ini_url)
    if x_db_path is not None:
        cfg.cmd_opts = argparse.Namespace(x=[f"db_path={x_db_path}"])
    return cfg


def _imported_modules(source: str) -> set[str]:
    """收集源码里出现的全部被导入名，两种写法都算：

    ``import a.b.c`` -> ``a.b.c``；``from a.b import c`` -> ``a.b`` **与** ``a.b.c``。
    只记 ``node.module`` 会把 ``from campaignlab.infra.db import paths`` 误判成
    「没有 import paths」，守卫就成了假红——那和假绿一样不可接受。
    """
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def _imported_names_and_attrs(source: str) -> set[str]:
    """收集源码里出现的全部标识符与属性名（用于守卫「引用了某个常量」这类事实）。"""
    tree = ast.parse(source)
    return {
        node.id if isinstance(node, ast.Name) else node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Name | ast.Attribute)
    }


def _code_string_literals(source: str) -> set[str]:
    """收集**非 docstring** 的字符串字面量。

    注释在 AST 里根本不存在，docstring 单独剔除——否则文件头那句「本文件不得再出现
    ``CAMPAIGNLAB_*`` 字面量」的说明本身就会把守卫触发，守卫立刻变成不可用的摆设。
    """
    tree = ast.parse(source)
    docstring_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstring_nodes.add(id(first.value))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstring_nodes
    }


def _business_tables(conn: sqlite3.Connection) -> set[str]:
    """业务表 = 全部用户表 - alembic 簿记表（裁定 3：簿记表不计入 28 表分母）。"""
    return {name for name in table_names(conn) if not name.startswith("sqlite_")} - {
        ALEMBIC_BOOKKEEPING_TABLE
    }


# ------------------------------------------------- 单一来源①：静态守卫（不得有第二份链条）


def test_env_py_imports_the_single_source() -> None:
    """alembic 侧必须 import paths（裁定 2），且不得自带优先级链的任何字面量。"""
    source = ENV_PY.read_text(encoding="utf-8")
    imported = _imported_modules(source)
    assert "campaignlab.infra.db.paths" in imported, (
        "migrations/env.py 没有 import campaignlab.infra.db.paths —— ADR-005 §2.4 裁定 2 "
        "要求库路径解析只存在一份，alembic 侧必须 import 它，禁止各自复制优先级链。"
    )
    assert "campaignlab.infra.db.engine" in imported, (
        "PRAGMA 的单一来源是 infra/db/engine.py；env.py 不得再抄一份 PRAGMA 常量。"
    )
    assert "os" not in imported, "env.py 不应再直接读环境变量，环境变量两级由 paths 负责"

    literals = _code_string_literals(source)
    leaked = sorted(literals & FORBIDDEN_LITERALS)
    assert not leaked, f"env.py 代码里重新出现了第二份路径口径的字面量：{leaked}"
    # env.py 引用的是常量名（不得就地写字面量），故这里按属性访问名做守卫。
    assert "ALEMBIC_URL_ATTRIBUTE" in _imported_names_and_attrs(source), (
        "env.py 必须把解析结果回填到 config.attributes[paths.ALEMBIC_URL_ATTRIBUTE]，"
        "否则「alembic 侧解析 == 运行期解析」只能靠人眼比对，无法被机器守护"
    )


def test_engine_py_imports_the_single_source() -> None:
    """运行期侧同样必须 import paths，且不得自带第二份优先级链。"""
    source = ENGINE_PY.read_text(encoding="utf-8")
    assert "campaignlab.infra.db.paths" in _imported_modules(source), (
        "infra/db/engine.py 没有 import paths —— 运行期与 alembic 侧会解析到不同的库文件"
    )
    literals = _code_string_literals(source)
    leaked = sorted(literals & FORBIDDEN_LITERALS)
    assert not leaked, f"engine.py 代码里重新出现了第二份路径口径的字面量：{leaked}"


def test_pragmas_single_source_matches_operations_baseline() -> None:
    """PRAGMA 三件套是 OPERATIONS.md 的运行口径；改动必须走 ADR，不能悄悄改常量。"""
    assert PRAGMAS == ("foreign_keys=ON", "busy_timeout=5000", "journal_mode=DELETE")


# --------------------------------------- 单一来源②：行为守卫（alembic 侧 == 运行期，逐字）


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
def test_alembic_side_resolution_equals_runtime_side(
    level: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**ADR-005 §2.4 裁定 2 的核心不变量**：同一组环境下，alembic 侧解析结果 == 运行期解析结果。

    五级各跑一遍：真的执行 ``alembic upgrade head``，把它实际使用的连接串（由 env.py 回填）
    与 ``paths.resolve_database_url()`` 在同一进程、同一环境下的输出做**逐字**比对，
    并额外确认落点文件确实被建出来、被遮蔽的低优先级目标**没有**被建出来。
    """
    _clean_env(monkeypatch)
    home = tmp_path / f"home{level}"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    x_db_path: str | None = None
    ini_url: str | None = None
    shadowed: list[Path] = []

    env_db = paths.database_url_from_path(tmp_path / "env.db")
    if level == 1:
        x_db_path = str(tmp_path / "x.db")
        ini_url = paths.database_url_from_path(tmp_path / "ini.db")
        monkeypatch.setenv(paths.DATABASE_URL_ENV, env_db)
        monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path / "datadir"))
        shadowed = [tmp_path / "ini.db", tmp_path / "env.db", tmp_path / "datadir"]
    elif level == 2:
        ini_url = paths.database_url_from_path(tmp_path / "ini.db")
        monkeypatch.setenv(paths.DATABASE_URL_ENV, env_db)
        monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path / "datadir"))
        shadowed = [tmp_path / "env.db", tmp_path / "datadir"]
    elif level == 3:
        monkeypatch.setenv(paths.DATABASE_URL_ENV, env_db)
        monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path / "datadir"))
        shadowed = [tmp_path / "datadir"]
    elif level == 4:
        monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path / "datadir"))

    cfg = _alembic_config(ini_url=ini_url, x_db_path=x_db_path)
    command.upgrade(cfg, "head")

    alembic_url = str(cfg.attributes[paths.ALEMBIC_URL_ATTRIBUTE])
    runtime = paths.resolve_database_location(x_db_path=x_db_path, ini_url=ini_url)

    assert alembic_url == runtime.url, (
        f"第 {level} 级下 alembic 侧与运行期解析不一致："
        f"alembic={alembic_url!r} runtime={runtime.url!r}"
    )
    assert runtime.level is ResolutionLevel(level), f"命中级别应为 {level}，实测 {runtime.level}"
    assert runtime.path is not None and runtime.path.exists(), (
        f"alembic 没有在解析出的位置建库：{runtime.path}"
    )
    for loser in shadowed:
        assert not loser.exists(), f"第 {level} 级生效时，被遮蔽的低优先级目标不应被创建：{loser}"


def test_runtime_assembly_uses_the_same_resolution(tmp_path: Path) -> None:
    """``application.build_database_runtime`` 也必须走同一份解析，而不是自己拼路径。"""
    environ = {paths.DATA_DIR_ENV: str(tmp_path / "data")}
    expected = paths.resolve_database_location(environ=environ, home=tmp_path)
    runtime = build_database_runtime(environ=environ, home=tmp_path)
    try:
        assert runtime.url == expected.url
        assert runtime.location == expected
        assert runtime.level is ResolutionLevel.ENV_DATA_DIR
        assert runtime.path == expected.path
        assert runtime.engine.url.database == str(expected.path)
    finally:
        runtime.dispose()


def test_runtime_connection_applies_the_shared_pragmas(tmp_path: Path) -> None:
    """运行期连接的 PRAGMA 必须与迁移期一致，否则外键负例只在一侧被拒绝（假绿）。"""
    runtime = build_database_runtime(
        database_url=paths.database_url_from_path(tmp_path / "pragma.db")
    )
    try:
        with connect(runtime.engine) as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar() == 5000
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar() == "delete"
    finally:
        runtime.dispose()


# ----------------------------------------------------------- 五级优先级（纯函数逐级验证）


def test_level1_x_db_path_shadows_everything_below(tmp_path: Path) -> None:
    location = paths.resolve_database_location(
        x_db_path=str(tmp_path / "x.db"),
        ini_url=paths.database_url_from_path(tmp_path / "ini.db"),
        environ={
            paths.DATABASE_URL_ENV: paths.database_url_from_path(tmp_path / "env.db"),
            paths.DATA_DIR_ENV: str(tmp_path / "datadir"),
        },
        home=tmp_path / "home",
    )
    assert location.level is ResolutionLevel.X_DB_PATH
    assert location.path == tmp_path / "x.db"
    assert location.url == paths.database_url_from_path(tmp_path / "x.db")


def test_level2_ini_url_wins_over_env_and_default(tmp_path: Path) -> None:
    location = paths.resolve_database_location(
        ini_url=paths.database_url_from_path(tmp_path / "ini.db"),
        environ={
            paths.DATABASE_URL_ENV: paths.database_url_from_path(tmp_path / "env.db"),
            paths.DATA_DIR_ENV: str(tmp_path / "datadir"),
        },
        home=tmp_path / "home",
    )
    assert location.level is ResolutionLevel.INI_URL
    assert location.path == tmp_path / "ini.db"


def test_level3_env_database_url_wins_over_data_dir(tmp_path: Path) -> None:
    location = paths.resolve_database_location(
        environ={
            paths.DATABASE_URL_ENV: paths.database_url_from_path(tmp_path / "env.db"),
            paths.DATA_DIR_ENV: str(tmp_path / "datadir"),
        },
        home=tmp_path / "home",
    )
    assert location.level is ResolutionLevel.ENV_DATABASE_URL
    assert location.path == tmp_path / "env.db"


def test_level4_env_data_dir_appends_state_subdir(tmp_path: Path) -> None:
    location = paths.resolve_database_location(
        environ={paths.DATA_DIR_ENV: str(tmp_path / "datadir")}, home=tmp_path / "home"
    )
    assert location.level is ResolutionLevel.ENV_DATA_DIR
    assert location.path == tmp_path / "datadir" / "state" / "campaignlab.db"


def test_level5_default_is_home_local_share(tmp_path: Path) -> None:
    location = paths.resolve_database_location(environ={}, home=tmp_path)
    assert location.level is ResolutionLevel.DEFAULT_DATA_DIR
    assert (
        location.path == tmp_path / ".local" / "share" / "campaignlab" / "state" / "campaignlab.db"
    )


def test_default_layout_constants_match_adr005() -> None:
    """裁定 1 的相对布局固定为 ``<data_dir>/state/campaignlab.db``，改它等于改 ADR。"""
    assert paths.STATE_SUBDIR == "state"
    assert paths.DB_FILENAME == "campaignlab.db"
    assert paths.DEFAULT_DATA_DIR_PARTS == (".local", "share", "campaignlab")
    assert paths.database_path_in(Path("/d")) == Path("/d/state/campaignlab.db")


def test_blank_sources_fall_through_to_the_next_level(tmp_path: Path) -> None:
    """空串与纯空白必须视为「未提供」——否则空的 ini 项会把后面四级全部遮蔽。"""
    location = paths.resolve_database_location(
        x_db_path="   ",
        ini_url="",
        environ={paths.DATABASE_URL_ENV: "  ", paths.DATA_DIR_ENV: str(tmp_path / "datadir")},
        home=tmp_path,
    )
    assert location.level is ResolutionLevel.ENV_DATA_DIR
    assert location.path == tmp_path / "datadir" / "state" / "campaignlab.db"


def test_tilde_is_expanded_against_the_injected_home(tmp_path: Path) -> None:
    location = paths.resolve_database_location(environ={paths.DATA_DIR_ENV: "~/cl"}, home=tmp_path)
    assert location.path == tmp_path / "cl" / "state" / "campaignlab.db"
    assert paths.expand_user("~", tmp_path) == tmp_path
    with pytest.raises(ValueError, match="~user"):
        paths.expand_user("~otheruser/cl", tmp_path)


def test_url_and_path_helpers_round_trip(tmp_path: Path) -> None:
    absolute = tmp_path / "state" / "campaignlab.db"
    assert paths.url_to_path(paths.database_url_from_path(absolute)) == absolute
    assert paths.url_to_path("sqlite:///relative/db.sqlite") == Path("relative/db.sqlite")
    assert paths.location_from_url(paths.database_url_from_path(absolute)).level is (
        ResolutionLevel.CALLER_SUPPLIED
    )
    with pytest.raises(ValueError, match="为空"):
        paths.location_from_url("   ")


def test_memory_and_non_sqlite_urls_have_no_file_path() -> None:
    assert paths.url_to_path("sqlite://") is None
    assert paths.url_to_path("sqlite:///:memory:") is None
    assert paths.url_to_path("postgresql+psycopg://u@h/db") is None


def test_resolve_database_path_refuses_to_guess_for_non_file_urls() -> None:
    """解析结果不是文件型库时**显式报错**，绝不静默造一个路径出来。"""
    with pytest.raises(ValueError, match="不是文件型 SQLite 库"):
        paths.resolve_database_path(
            environ={paths.DATABASE_URL_ENV: "sqlite:///:memory:"}, home=Path("/nope")
        )


def test_ensure_parent_dir_creates_only_for_absolute_file_targets(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "nested" / "campaignlab.db"
    paths.ensure_parent_dir(target)
    assert target.parent.is_dir()
    paths.ensure_parent_dir("sqlite:///:memory:")  # 不得抛异常、不得建目录
    assert not (tmp_path / ":memory:").exists()


# ---------------------------------------------------- 完整可逆（裁定 3）与四步迁移闭环


def test_full_reversibility_and_migration_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``upgrade head → 校验 → downgrade base → 再 upgrade`` 全流程，且 downgrade 后完整可逆。

    完整可逆口径（ADR-005 §2.4 裁定 3）＝ **业务表 0 张 + 仅剩空的 ``alembic_version``**；
    簿记表不计入 28 表分母、也不算「额外表」。整条流程走 ``CAMPAIGNLAB_DATA_DIR``，
    顺带把「alembic 落点 == 运行期解析落点」在真实文件系统上再钉一次。
    """
    _clean_env(monkeypatch)
    data_dir = tmp_path / "data"
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(data_dir))

    expected_url = paths.resolve_database_url()
    expected_path = paths.resolve_database_path()
    assert expected_path == data_dir / paths.STATE_SUBDIR / paths.DB_FILENAME

    cfg = Config(str(ALEMBIC_INI))

    command.upgrade(cfg, "head")
    assert str(cfg.attributes[paths.ALEMBIC_URL_ATTRIBUTE]) == expected_url
    assert expected_path.exists()
    with sqlite3.connect(expected_path) as conn:
        assert len(_business_tables(conn)) == EXPECTED_TABLE_COUNT
        assert conn.execute(f"SELECT version_num FROM {ALEMBIC_BOOKKEEPING_TABLE}").fetchall() == [
            (HEAD_REVISION,)
        ]
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    command.downgrade(cfg, "base")
    with sqlite3.connect(expected_path) as conn:
        leftover = sorted(_business_tables(conn))
        assert leftover == [], f"downgrade base 后仍有业务表残留：{leftover}"
        names = {name for name in table_names(conn) if not name.startswith("sqlite_")}
        assert names == {ALEMBIC_BOOKKEEPING_TABLE}, f"应只剩空的簿记表，实测：{sorted(names)}"
        assert conn.execute(f"SELECT count(*) FROM {ALEMBIC_BOOKKEEPING_TABLE}").fetchone()[0] == 0

    command.upgrade(cfg, "head")
    with sqlite3.connect(expected_path) as conn:
        assert len(_business_tables(conn)) == EXPECTED_TABLE_COUNT
        assert conn.execute(f"SELECT version_num FROM {ALEMBIC_BOOKKEEPING_TABLE}").fetchall() == [
            (HEAD_REVISION,)
        ]
