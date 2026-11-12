"""首迁等价性集成测试（M0-02 · S2）。

覆盖任务卡 gate「首迁与参考 DDL 比对通过：表数 28、列与约束一致，PRAGMA integrity_check
与 foreign_key_check 通过，跨工作区外键负例被拒绝」，以及设计档 §3 判据 ①–⑧。

一条纪律贯穿全文件：**每个负例都配一个正例**。只断言「插入被拒」而不证明「同样的语句
在合法数据下能被接受」，等于没测 —— 一个把所有 INSERT 都拒掉的库同样能全绿。
"""

from __future__ import annotations

import importlib.util
import re
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from campaignlab.infra.db.ddl_compare import (
    EXPECTED_TABLE_COUNT,
    MIGRATION_ONLY_TABLES,
    compare_schema,
    index_sql_map,
    normalize_sql,
    pragma_problems,
    schema_summary,
    table_fingerprint,
    table_names,
)

# 显式时刻：领域相关的时间戳一律写死，禁止取系统当前时间（任务卡「禁止」条）。
TS = "2026-01-01T00:00:00+00:00"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64

EXPLICIT_INDEX_COUNT = 6
REPO_ROOT = Path(__file__).resolve().parents[3]


def _user_tables(conn: sqlite3.Connection) -> tuple[str, ...]:
    """排除 alembic 簿记表后的表名（升序）。"""
    return tuple(t for t in table_names(conn) if t not in MIGRATION_ONLY_TABLES)


def _insert_workspace(
    conn: sqlite3.Connection,
    workspace_id: str,
    *,
    source_class: str = "SYNTHETIC",
    note: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO workspaces (id, name, source_class, authorization_note, revision, created_at)"
        " VALUES (?, ?, ?, ?, 1, ?)",
        (workspace_id, workspace_id, source_class, note, TS),
    )


def _insert_artifact(conn: sqlite3.Connection, workspace_id: str, artifact_id: str) -> None:
    conn.execute(
        "INSERT INTO artifacts"
        " (workspace_id, id, kind, sha256, relative_path, byte_size, created_at)"
        " VALUES (?, ?, 'IMPORT_FILE', ?, ?, 1, ?)",
        (workspace_id, artifact_id, DIGEST_A, f"{workspace_id}/{artifact_id}.json", TS),
    )


def _insert_evidence(
    conn: sqlite3.Connection, workspace_id: str, evidence_id: str, artifact_id: str
) -> None:
    conn.execute(
        "INSERT INTO evidence"
        " (workspace_id, id, kind, source_id, locator, label, source_class,"
        " content_digest, artifact_id, created_at)"
        " VALUES (?, ?, 'SOURCE', 'src-1', 'locator', 'label', 'SYNTHETIC', ?, ?, ?)",
        (workspace_id, evidence_id, DIGEST_B, artifact_id, TS),
    )


def _insert_audit(conn: sqlite3.Connection, workspace_id: str) -> None:
    conn.execute(
        'INSERT INTO audit (workspace_id, sequence, id, "at", actor_id, role, action,'
        " target_kind, target_id, outcome, request_id, previous_digest, digest)"
        " VALUES (?, 1, 'audit-1', ?, 'actor-1', 'ANALYST', 'WORKSPACE_CREATED',"
        " 'WORKSPACE', 'ws-1', 'ACCEPTED', 'req-1', NULL, ?)",
        (workspace_id, TS, DIGEST_C),
    )


def _assert_foreign_keys_are_on(conn: sqlite3.Connection) -> None:
    """分母断言：外键没开的话，下面所有负例都会假绿。"""
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


# --------------------------------------------------------------------------- ①


def test_28_tables(reference_db: sqlite3.Connection, migrated_db: sqlite3.Connection) -> None:
    ref, mig = _user_tables(reference_db), _user_tables(migrated_db)
    assert len(ref) == EXPECTED_TABLE_COUNT, f"参考库表数 {len(ref)} != 28"
    assert len(mig) == EXPECTED_TABLE_COUNT, f"迁移库表数 {len(mig)} != 28"
    assert mig == ref, "表名集合不一致"
    # 迁移库只允许比参考库多 alembic_version 一张簿记表
    assert table_names(migrated_db) == tuple(sorted((*ref, *MIGRATION_ONLY_TABLES)))
    rows = migrated_db.execute("SELECT version_num FROM alembic_version").fetchall()
    assert rows == [("0001_initial_schema",)], f"alembic 版本簿记异常：{rows}"


# --------------------------------------------------------------------- ②③④⑤⑥


def test_column_fingerprint_equal(
    reference_db: sqlite3.Connection, migrated_db: sqlite3.Connection
) -> None:
    """判据 ②：每表 PRAGMA table_info 六元组逐行相等（含 notnull / dflt_value / pk）。"""
    bad = {
        t: (table_fingerprint(reference_db, t).columns, table_fingerprint(migrated_db, t).columns)
        for t in _user_tables(reference_db)
        if table_fingerprint(reference_db, t).columns != table_fingerprint(migrated_db, t).columns
    }
    assert bad == {}


def test_foreign_key_list_equal(
    reference_db: sqlite3.Connection, migrated_db: sqlite3.Connection
) -> None:
    """判据 ③：每表 PRAGMA foreign_key_list 八元组逐行相等，复合外键列序敏感。"""
    bad = {
        t: (
            table_fingerprint(reference_db, t).foreign_keys,
            table_fingerprint(migrated_db, t).foreign_keys,
        )
        for t in _user_tables(reference_db)
        if table_fingerprint(reference_db, t).foreign_keys
        != table_fingerprint(migrated_db, t).foreign_keys
    }
    assert bad == {}
    # 分母断言：参考 DDL 确实含复合外键，否则上面比的是空集合
    composite = {
        t: fk
        for t in _user_tables(reference_db)
        for fk in table_fingerprint(reference_db, t).foreign_keys
        if fk[1] == 1
    }
    assert composite, "参考 DDL 中找不到任何复合外键，断言口径已失效"


def test_index_list_equal(
    reference_db: sqlite3.Connection, migrated_db: sqlite3.Connection
) -> None:
    """判据 ④：index_list（名/unique/origin/partial）＋每索引 index_info 列序相等。"""
    bad = {
        t: (table_fingerprint(reference_db, t).indexes, table_fingerprint(migrated_db, t).indexes)
        for t in _user_tables(reference_db)
        if table_fingerprint(reference_db, t).indexes != table_fingerprint(migrated_db, t).indexes
    }
    assert bad == {}
    explicit = sorted(index_sql_map(migrated_db))
    assert len(explicit) == EXPLICIT_INDEX_COUNT, f"显式索引数 {len(explicit)} != 6"
    assert explicit == [
        "actions_due",
        "analysis_snapshot",
        "cases_one_confirmed_child",
        "jobs_ready",
        "rules_activity",
        "snapshots_lookup",
    ]


def test_all_tables_strict(
    reference_db: sqlite3.Connection, migrated_db: sqlite3.Connection
) -> None:
    """判据 ⑤：28 表全为 STRICT，且 STRICT 真的在起作用（不只是元数据摆设）。"""
    for conn, label in ((reference_db, "参考库"), (migrated_db, "迁移库")):
        flags = {
            row.name: row.strict
            for row in schema_summary(conn)
            if row.name not in MIGRATION_ONLY_TABLES
        }
        assert len(flags) == EXPECTED_TABLE_COUNT, f"{label}表数 {len(flags)} != 28"
        assert set(flags.values()) == {1}, f"{label}存在非 STRICT 表：{flags}"

    # 行为验证：STRICT 表拒绝把字符串塞进 INTEGER 列（非 STRICT 表会静默转换）
    with pytest.raises(sqlite3.IntegrityError):
        migrated_db.execute(
            "INSERT INTO workspaces (id, name, source_class, revision, created_at)"
            f" VALUES ('WS-STRICT', 'n', 'SYNTHETIC', 'not-an-int', '{TS}')"
        )
    migrated_db.rollback()


def test_sql_text_normalized_equal(
    reference_db: sqlite3.Connection, migrated_db: sqlite3.Connection
) -> None:
    """判据 ⑥：sqlite_master.sql 空白归一后逐对象相等（表＋显式索引，覆盖 WHERE 子句）。"""
    bad = {
        t: (table_fingerprint(reference_db, t).sql, table_fingerprint(migrated_db, t).sql)
        for t in _user_tables(reference_db)
        if table_fingerprint(reference_db, t).sql != table_fingerprint(migrated_db, t).sql
    }
    assert bad == {}
    assert index_sql_map(reference_db) == index_sql_map(migrated_db)
    partial = index_sql_map(migrated_db)["cases_one_confirmed_child"]
    assert "WHERE parent_case_id IS NOT NULL" in partial, "部分唯一索引的 WHERE 子句丢失"


def test_inline_sql_matches_reference_objects(reference_db: sqlite3.Connection) -> None:
    """迁移文件里内联的 SQL 与参考库的 sqlite_master 逐对象相等（静态 × 动态交叉验证）。

    这条把「迁移文件写了什么」和「参考 DDL 建出了什么」直接对上，
    不经过迁移库，因此即使 alembic 未来改变落库方式也能守住等价性。
    """
    ref_sql = {
        str(name): normalize_sql(str(sql))
        for name, sql in reference_db.execute(
            "SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL"
        ).fetchall()
    }
    statements = _load_inline_statements()
    assert len(statements) == EXPECTED_TABLE_COUNT + EXPLICIT_INDEX_COUNT
    for stmt in statements:
        match = re.match(r"^CREATE (?:TABLE|UNIQUE INDEX|INDEX)\s+([A-Za-z_][A-Za-z0-9_]*)", stmt)
        assert match is not None, f"内联语句无法解析出对象名：{stmt[:80]}"
        name = match.group(1)
        assert name in ref_sql, f"内联对象 {name} 在参考 DDL 中不存在"
        assert ref_sql[name] == stmt, f"内联 SQL 与参考 DDL 归一化后不等：{name}"


def _load_inline_statements() -> list[str]:
    """从迁移文件里取出内联的 CREATE 语句（不执行迁移，只读模块常量）。"""
    path = REPO_ROOT / "migrations" / "versions" / "0001_initial_schema.py"
    spec = importlib.util.spec_from_file_location("campaignlab_migration_0001", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tables = [str(x) for x in module._CREATE_TABLE_STATEMENTS]
    indexes = [str(x) for x in module._CREATE_INDEX_STATEMENTS]
    assert len(tables) == EXPECTED_TABLE_COUNT, f"内联建表语句 {len(tables)} 条 != 28"
    assert len(indexes) == EXPLICIT_INDEX_COUNT, f"内联建索引语句 {len(indexes)} 条 != 6"
    return [*tables, *indexes]


# ------------------------------------------------------------------------- ⑦


def test_pragma_integrity_and_fk_check(
    reference_db: sqlite3.Connection, migrated_db: sqlite3.Connection
) -> None:
    """判据 ⑦：integrity_check = ok，foreign_key_check 返回 0 行。"""
    assert pragma_problems(reference_db, "参考库") == []
    assert pragma_problems(migrated_db, "迁移库") == []
    # 分母断言：PRAGMA 确实被执行并返回了内容
    assert migrated_db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert migrated_db.execute("PRAGMA foreign_key_check").fetchall() == []
    _assert_foreign_keys_are_on(migrated_db)


# ------------------------------------------------------------ 汇总判据：空即等价


def test_compare_schema_returns_empty(
    reference_db: sqlite3.Connection, migrated_db: sqlite3.Connection
) -> None:
    """总判据：返回空列表即等价。证据档 migration-diff.md 直接贴本条结果。"""
    assert compare_schema(reference_db, migrated_db) == []


# ------------------------------------------------------------------------- ⑧


def test_cross_workspace_fk_negative(
    reference_db: sqlite3.Connection, migrated_db: sqlite3.Connection
) -> None:
    """跨工作区外键负例：引用别的工作区的行必须被拒；同工作区内必须能成功。

    对**参考库与迁移库同时**跑，两边行为必须一致 —— 只测迁移库无法证明「等价」。
    """
    for conn in (reference_db, migrated_db):
        _assert_foreign_keys_are_on(conn)
        _insert_workspace(conn, "WS-A")
        _insert_workspace(conn, "WS-B")
        _insert_artifact(conn, "WS-A", "ART-A1")
        conn.commit()

        # ① 复合外键 (workspace_id, artifact_id) -> artifacts：WS-B 引用 WS-A 的制品
        with pytest.raises(sqlite3.IntegrityError):
            _insert_evidence(conn, "WS-B", "EV-B1", "ART-A1")
        conn.rollback()

        # ② 单列外键 workspace_id -> workspaces(id)：workspace 不存在
        with pytest.raises(sqlite3.IntegrityError):
            _insert_audit(conn, "WS-MISSING")
        conn.rollback()

        # ③ 同上，走 artifacts
        with pytest.raises(sqlite3.IntegrityError):
            _insert_artifact(conn, "WS-MISSING", "ART-X")
        conn.rollback()

        # 正例（分母断言）：同工作区内引用必须成功，否则上面的"被拒"没有意义
        _insert_evidence(conn, "WS-A", "EV-A1", "ART-A1")
        _insert_audit(conn, "WS-A")
        conn.commit()
        assert conn.execute("SELECT count(*) FROM evidence").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM audit").fetchone()[0] == 1


def test_check_constraints_negative(
    reference_db: sqlite3.Connection, migrated_db: sqlite3.Connection
) -> None:
    """CHECK 负例：枚举、跨列 CHECK（AUTHORIZED_DEIDENTIFIED 必须带授权说明）。"""
    for conn in (reference_db, migrated_db):
        # source_class 不在枚举内
        with pytest.raises(sqlite3.IntegrityError):
            _insert_workspace(conn, "WS-X", source_class="X")
        conn.rollback()

        # 表级 CHECK：AUTHORIZED_DEIDENTIFIED 必须有非空 authorization_note
        with pytest.raises(sqlite3.IntegrityError):
            _insert_workspace(conn, "WS-Y", source_class="AUTHORIZED_DEIDENTIFIED", note="")
        conn.rollback()
        with pytest.raises(sqlite3.IntegrityError):
            _insert_workspace(conn, "WS-Z", source_class="AUTHORIZED_DEIDENTIFIED", note=None)
        conn.rollback()

        # 正例：SYNTHETIC + note IS NULL 通过；AUTHORIZED_DEIDENTIFIED + 非空 note 通过
        _insert_workspace(conn, "WS-SYN", source_class="SYNTHETIC", note=None)
        _insert_workspace(
            conn, "WS-AUTH", source_class="AUTHORIZED_DEIDENTIFIED", note="已获授权且已去标识"
        )
        conn.commit()
        rows = conn.execute("SELECT id FROM workspaces ORDER BY id").fetchall()
        assert rows == [("WS-AUTH",), ("WS-SYN",)], f"正例未按预期落库：{rows}"


# ------------------------------------------------------------------- 可逆性


def test_downgrade_is_reversible(
    tmp_path: Path,
    run_migration: Callable[[Path, str], None],
    reference_ddl_text: str,
) -> None:
    """upgrade head -> downgrade base -> upgrade head：库回到与参考 DDL 等价的状态。"""
    db_path = tmp_path / "reversible.db"
    run_migration(db_path, "head")

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        assert len(_user_tables(conn)) == EXPECTED_TABLE_COUNT

        run_migration(db_path, "base")
        leftover = _user_tables(conn)
        assert leftover == (), f"downgrade base 后仍残留用户表：{leftover}"
        assert table_names(conn) == tuple(sorted(MIGRATION_ONLY_TABLES)), (
            f"downgrade base 后应只剩 alembic 簿记表，实测：{table_names(conn)}"
        )
        assert conn.execute("SELECT count(*) FROM alembic_version").fetchone()[0] == 0

        run_migration(db_path, "head")
        reference = sqlite3.connect(":memory:")
        try:
            reference.execute("PRAGMA foreign_keys=ON")
            reference.executescript(reference_ddl_text)
            assert compare_schema(reference, conn) == []
        finally:
            reference.close()
    finally:
        conn.close()
