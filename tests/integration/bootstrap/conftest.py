"""bootstrap 集成夹具：真实 SQLite 临时库上并排建出「参考库」与「迁移库」。

- ``reference_db``：直接 ``executescript`` 活契约 ``contracts/sqlite-v1.sql``；
- ``migrated_db`` ：跑**真实的** ``alembic upgrade head``（迁移脚本自身不读 DDL 文件）。

两件事必须在这里钉死，否则后面所有等价性断言都可能是假绿：

1. 参考 DDL 的 sha256 必须等于任务卡给的值 —— 文件被换过就要立刻红，而不是「悄悄和另一个
   版本比出个相等」；
2. 每个连接都显式 ``PRAGMA foreign_keys=ON`` —— SQLite 默认**关闭**外键，
   不开的话跨工作区外键负例会全部通过，等于没测。
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

REPO_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = REPO_ROOT / "migrations" / "alembic.ini"
REFERENCE_DDL = REPO_ROOT / "contracts" / "sqlite-v1.sql"

# 任务卡 gates 给定的参考 DDL 指纹（contracts/sqlite-v1.sql 与只读基线字节相同）。
EXPECTED_DDL_SHA256 = "ec9ddfbc4e7dba4c0a565161b50a222fee484eb07e6586588871bffa2efc8c0e"


def connect(path: Path | str) -> sqlite3.Connection:
    """打开文件型 SQLite 连接，并按 OPERATIONS.md 的运行口径设置 PRAGMA。"""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def run_alembic(db_path: Path, revision: str = "head") -> None:
    """在指定库文件上跑 alembic。连接串经 ``set_main_option`` 注入 env.py，不碰环境变量。"""
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", "sqlite:///" + Path(db_path).as_posix())
    if revision == "base":
        command.downgrade(cfg, "base")
    else:
        command.upgrade(cfg, revision)


@pytest.fixture(scope="session")
def reference_ddl_text() -> str:
    """参考 DDL 原文，附带指纹校验（分母断言：文件不存在／被改都必须显式失败）。"""
    raw = REFERENCE_DDL.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == EXPECTED_DDL_SHA256, (
        f"参考 DDL 指纹漂移：期望 {EXPECTED_DDL_SHA256}，实测 {digest}。"
        "contracts/sqlite-v1.sql 是活契约，改动必须走 CR，测试不得就地改期望值。"
    )
    return raw.decode("utf-8")


@pytest.fixture(scope="session")
def run_migration() -> Callable[[Path, str], None]:
    """把 alembic 运行器交给用例（downgrade 可逆性测试要多次调用）。"""
    return run_alembic


@pytest.fixture
def reference_db(tmp_path: Path, reference_ddl_text: str) -> Iterator[sqlite3.Connection]:
    """用参考 DDL 建出的库（每用例一个全新临时文件）。"""
    conn = connect(tmp_path / "reference.db")
    try:
        conn.executescript(reference_ddl_text)
        conn.commit()
        yield conn
    finally:
        conn.close()


@pytest.fixture
def migrated_db_path(tmp_path: Path) -> Path:
    """跑完 ``upgrade head`` 的库文件路径。"""
    path = tmp_path / "migrated.db"
    run_alembic(path, "head")
    assert path.exists(), f"alembic upgrade head 没有产出库文件：{path}"
    return path


@pytest.fixture
def migrated_db(migrated_db_path: Path) -> Iterator[sqlite3.Connection]:
    """迁移后的库连接（可写，供负例插入使用；负例一律 rollback，不留脏行）。"""
    conn = connect(migrated_db_path)
    try:
        yield conn
    finally:
        conn.close()
