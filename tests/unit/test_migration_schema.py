"""首迁的单元级守卫（M0-02 · S2）。

集成侧（``tests/integration/bootstrap/``）证明「迁移库 == 参考库」。本文件补两类
集成测试证明不了的东西：

1. **比对器本身不是摆设**。``compare_schema`` 返回空列表是 S2 的总判据，可一个恒返回
   ``[]`` 的实现同样能全绿。因此这里对参考 DDL 注入 8 种单点变异，逐一要求比对器
   **必须**报出差异、且报出的差异指向被改的那个对象（手册 15.4：断言必须可归因）。
2. **迁移脚本自包含且元数据正确**。任务卡明令禁止「直接执行 sqlite-v1.sql」式的绕过，
   用 AST 静态钉住：``upgrade``/``downgrade`` 只允许调 ``op.execute`` 与白名单内建，模块只允许
   import ``__future__`` / ``collections.abc`` / ``typing`` / ``alembic.op``。
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import sqlite3
from pathlib import Path
from types import ModuleType

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from campaignlab.infra.db.ddl_compare import (
    EXPECTED_TABLE_COUNT,
    compare_schema,
    normalize_sql,
    table_names,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = REPO_ROOT / "migrations" / "alembic.ini"
MIGRATION_FILE = REPO_ROOT / "migrations" / "versions" / "0001_initial_schema.py"
REFERENCE_DDL = REPO_ROOT / "contracts" / "sqlite-v1.sql"
HEAD_REVISION = "0001_initial_schema"
EXPECTED_DDL_SHA256 = "ec9ddfbc4e7dba4c0a565161b50a222fee484eb07e6586588871bffa2efc8c0e"

#: 迁移脚本允许的 import 来源。多一个都算「迁移不再自包含」。
ALLOWED_IMPORT_MODULES = frozenset({"__future__", "collections.abc", "typing", "alembic"})

#: upgrade/downgrade 里允许出现的内建调用。reversed 用于 downgrade 的逆序 DROP，
#: 它不读文件、不连库，不破坏「迁移自包含」这条不变量。
ALLOWED_BUILTINS = frozenset({"reversed"})


@pytest.fixture(scope="module")
def ddl_text() -> str:
    """参考 DDL 原文（带指纹校验：契约被换过必须显式失败，而不是悄悄比出个相等）。"""
    raw = REFERENCE_DDL.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == EXPECTED_DDL_SHA256, (
        f"参考 DDL 指纹漂移：期望 {EXPECTED_DDL_SHA256}，实测 {digest}"
    )
    return raw.decode("utf-8")


def _build(ddl: str) -> sqlite3.Connection:
    """按给定 DDL 文本建一个内存库。"""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(ddl)
    return conn


def _mutate(ddl: str, old: str, new: str, *, count: int = 1) -> str:
    """单点变异。锚点出现次数不符就失败 —— 否则变异可能根本没生效，测试变成假绿。"""
    found = ddl.count(old)
    assert found == count, f"变异锚点出现 {found} 次，期望 {count} 次：{old[:70]!r}"
    return ddl.replace(old, new)


def _load_migration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("campaignlab_migration_0001_unit", MIGRATION_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------- 修订元数据


def test_alembic_head_is_the_initial_revision() -> None:
    """head 唯一且为 0001_initial_schema，down_revision 为 None。"""
    script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    assert script.get_heads() == [HEAD_REVISION]
    revision = script.get_revision(HEAD_REVISION)
    assert revision is not None
    assert revision.down_revision is None
    assert revision.module.__file__ is not None
    assert Path(revision.module.__file__).name == "0001_initial_schema.py"


def test_migration_module_is_self_contained() -> None:
    """AST 守卫：迁移不在运行时读 DDL 文件，也不干 op.execute 以外的任何事。"""
    tree = ast.parse(MIGRATION_FILE.read_text(encoding="utf-8"))

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "迁移脚本不得用相对导入"
            imported.add(node.module or "")
    assert imported <= ALLOWED_IMPORT_MODULES, f"迁移脚本出现了额外 import：{sorted(imported)}"

    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert set(functions) == {"upgrade", "downgrade"}, f"迁移入口异常：{sorted(functions)}"

    for name in ("upgrade", "downgrade"):
        calls = [n for n in ast.walk(functions[name]) if isinstance(n, ast.Call)]
        assert calls, f"{name}() 没有任何调用，迁移是空的"
        for call in calls:
            func = call.func
            if isinstance(func, ast.Name):
                assert func.id in ALLOWED_BUILTINS, f"{name}() 调用了未授权的内建 {func.id}"
                continue
            assert isinstance(func, ast.Attribute), f"{name}() 调用了非属性对象"
            assert func.attr == "execute", f"{name}() 调用了 op.{func.attr}，只允许 op.execute"
            assert isinstance(func.value, ast.Name) and func.value.id == "op"


# ------------------------------------------------------- 比对器不是摆设（变异测试）


def test_compare_schema_empty_for_identical_builds(ddl_text: str) -> None:
    """同一份 DDL 建两个库：必须返回空（比对器的正例，也是变异测试的基线）。"""
    left, right = _build(ddl_text), _build(ddl_text)
    try:
        assert compare_schema(left, right) == []
        assert len(table_names(left)) == EXPECTED_TABLE_COUNT
    finally:
        left.close()
        right.close()


def test_detects_added_table(ddl_text: str) -> None:
    ref = _build(ddl_text)
    mig = _build(ddl_text)
    try:
        mig.execute("CREATE TABLE zz_extra (id TEXT PRIMARY KEY) STRICT")
        diffs = compare_schema(ref, mig)
        assert diffs, "多建一张表居然没被检出"
        assert any("zz_extra" in d for d in diffs), diffs
        assert any("表数" in d for d in diffs), diffs
    finally:
        ref.close()
        mig.close()


def test_detects_missing_table(ddl_text: str) -> None:
    ref = _build(ddl_text)
    mig = _build(ddl_text)
    try:
        mig.execute("DROP TABLE thresholds")
        diffs = compare_schema(ref, mig)
        assert diffs, "少建一张表居然没被检出"
        assert any("thresholds" in d for d in diffs), diffs
    finally:
        ref.close()
        mig.close()


def test_detects_renamed_column(ddl_text: str) -> None:
    ref = _build(ddl_text)
    mig = _build(ddl_text)
    try:
        mig.execute("ALTER TABLE thresholds RENAME COLUMN label TO title")
        diffs = compare_schema(ref, mig)
        assert diffs, "改列名居然没被检出"
        assert any(d.startswith("表 thresholds") for d in diffs), diffs
        assert any("table_info" in d for d in diffs), diffs
    finally:
        ref.close()
        mig.close()


def test_detects_changed_default(ddl_text: str) -> None:
    mutated = _mutate(ddl_text, "DEFAULT 1", "DEFAULT 2")
    ref, mig = _build(ddl_text), _build(mutated)
    try:
        diffs = compare_schema(ref, mig)
        assert diffs, "改列默认值居然没被检出"
        assert any("table_info" in d and "workspaces" in d for d in diffs), diffs
    finally:
        ref.close()
        mig.close()


def test_detects_changed_check_clause(ddl_text: str) -> None:
    mutated = _mutate(ddl_text, "CHECK(length(sha256)=64)", "CHECK(length(sha256)=32)")
    ref, mig = _build(ddl_text), _build(mutated)
    try:
        diffs = compare_schema(ref, mig)
        assert diffs, "改 CHECK 约束居然没被检出"
        assert any(d.startswith("表 artifacts") and "建表语句" in d for d in diffs), diffs
    finally:
        ref.close()
        mig.close()


def test_detects_lost_strict(ddl_text: str) -> None:
    mutated = _mutate(
        ddl_text,
        "CHECK(source_class='SYNTHETIC' OR length(coalesce(authorization_note,''))>0)\n) STRICT;",
        "CHECK(source_class='SYNTHETIC' OR length(coalesce(authorization_note,''))>0)\n);",
    )
    ref, mig = _build(ddl_text), _build(mutated)
    try:
        diffs = compare_schema(ref, mig)
        assert diffs, "丢掉 STRICT 居然没被检出"
        assert any("workspaces" in d and "STRICT" in d for d in diffs), diffs
    finally:
        ref.close()
        mig.close()


def test_detects_changed_partial_index(ddl_text: str) -> None:
    mutated = _mutate(
        ddl_text,
        "WHERE parent_case_id IS NOT NULL AND state='CONFIRMED'",
        "WHERE parent_case_id IS NOT NULL AND state='DRAFT'",
    )
    ref, mig = _build(ddl_text), _build(mutated)
    try:
        diffs = compare_schema(ref, mig)
        assert diffs, "改部分唯一索引的 WHERE 子句居然没被检出"
        assert any("cases_one_confirmed_child" in d for d in diffs), diffs
    finally:
        ref.close()
        mig.close()


def test_detects_changed_foreign_key_action(ddl_text: str) -> None:
    mutated = _mutate(
        ddl_text,
        "REFERENCES artifacts(workspace_id,id)",
        "REFERENCES artifacts(workspace_id,id) ON DELETE CASCADE",
        count=8,
    )
    ref, mig = _build(ddl_text), _build(mutated)
    try:
        diffs = compare_schema(ref, mig)
        assert diffs, "改外键动作居然没被检出"
        assert any("foreign_key_list" in d for d in diffs), diffs
    finally:
        ref.close()
        mig.close()


def test_detects_dropped_explicit_index(ddl_text: str) -> None:
    ref = _build(ddl_text)
    mig = _build(ddl_text)
    try:
        mig.execute("DROP INDEX actions_due")
        diffs = compare_schema(ref, mig)
        assert diffs, "少建一个显式索引居然没被检出"
        assert any("actions_due" in d for d in diffs), diffs
    finally:
        ref.close()
        mig.close()


def test_detects_integrity_or_fk_violation(ddl_text: str) -> None:
    """判据 ⑦ 也必须能真红：手工插一条违反外键的行（绕过 PRAGMA）后应被报出。"""
    ref = _build(ddl_text)
    mig = _build(ddl_text)
    try:
        # 关掉外键校验再插脏行，制造一个 foreign_key_check 能查出的悬挂引用
        mig.execute("PRAGMA foreign_keys=OFF")
        mig.execute(
            "INSERT INTO artifacts"
            " (workspace_id, id, kind, sha256, relative_path, byte_size, created_at)"
            " VALUES ('WS-NONE', 'A1', 'K', ?, 'p/a1.json', 1, '2026-01-01T00:00:00+00:00')",
            ("a" * 64,),
        )
        mig.commit()
        diffs = compare_schema(ref, mig)
        assert diffs, "存在悬挂外键引用却没被检出"
        assert any("foreign_key_check" in d for d in diffs), diffs
    finally:
        ref.close()
        mig.close()


# ------------------------------------------------------------------ normalize_sql


def test_normalize_sql_only_collapses_whitespace() -> None:
    """归一化只折叠空白：不得改大小写、不得动引号内内容、不得删 token。"""
    assert normalize_sql("  CREATE TABLE  a\t(\n  b TEXT\n) STRICT ;  ") == (
        "CREATE TABLE a ( b TEXT ) STRICT ;"
    )
    assert normalize_sql("x IN ('A B','C  D')") == "x IN ('A B','C D')"
    assert normalize_sql("") == ""
    assert normalize_sql("a") == "a"
