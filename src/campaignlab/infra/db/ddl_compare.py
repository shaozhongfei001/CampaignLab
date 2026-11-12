"""参考 DDL 与 Alembic 首迁产物的 schema 等价性比对（M0-02 · S2）。

判据逐条对应 ``orchestrator/handoff/M0-02-design.md`` §3 的 ①–⑦：

① 表集合相等且数量为 28（迁移库额外**只**允许 ``alembic_version``，显式排除后再比）；
② 每表 ``PRAGMA table_info`` 六元组逐行相等（cid,name,type,notnull,dflt_value,pk）；
③ 每表 ``PRAGMA foreign_key_list`` 八元组逐行相等（复合外键**列序敏感**）；
④ ``PRAGMA index_list`` ＋每索引 ``PRAGMA index_info`` 相等（名、unique、origin、partial、列序）；
⑤ ``PRAGMA table_list`` 的 ``strict`` 列，28 表全为 1；
⑥ ``sqlite_master.sql`` 空白归一后逐对象字符串相等（表**与**显式索引都比，
   这样部分唯一索引 ``cases_one_confirmed_child`` 的 WHERE 子句也被覆盖）；
⑦ ``PRAGMA integrity_check`` = ``ok`` 且 ``PRAGMA foreign_key_check`` 返回 0 行。

⑧（外键／CHECK 负例）属**行为**验证，落在 ``tests/integration/bootstrap/``，不在本模块。

``compare_schema`` 的契约：**返回空列表即等价**；非空时每一项是一条可独立定位的可读差异，
禁止只回一个布尔值（那样失败时无法归因，违反手册 15.4 的「断言必须可归因」）。

本模块**只读**：不建表、不写行、不改 PRAGMA、不动事务；连接生命周期由调用方负责。
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any, Final, NamedTuple

__all__ = [
    "EXPECTED_TABLE_COUNT",
    "MIGRATION_ONLY_TABLES",
    "TableFingerprint",
    "TableSummary",
    "compare_schema",
    "index_sql_map",
    "normalize_sql",
    "pragma_problems",
    "schema_summary",
    "table_fingerprint",
    "table_names",
]

#: 参考 DDL ``contracts/sqlite-v1.sql`` 建的表数（任务卡 gate：表数 28）。
EXPECTED_TABLE_COUNT: Final = 28

#: 迁移库允许存在、参考库不存在的簿记表。只有这一个，多一张即算差异。
MIGRATION_ONLY_TABLES: Final = frozenset({"alembic_version"})

_INTERNAL_PREFIX: Final = "sqlite_"
_WHITESPACE_RUN: Final = re.compile(r"\s+")
_CHECK_TOKEN: Final = re.compile(r"\bCHECK\s*\(", re.IGNORECASE)


class TableFingerprint(NamedTuple):
    """单表的结构指纹。字段全部来自 PRAGMA / sqlite_master，不含任何推断。"""

    name: str
    columns: tuple[tuple[Any, ...], ...]
    foreign_keys: tuple[tuple[Any, ...], ...]
    indexes: tuple[tuple[str, int, str, int, tuple[str | None, ...]], ...]
    strict: int
    sql: str


class TableSummary(NamedTuple):
    """供证据档使用的每表摘要（人类可读，不参与等价判定）。"""

    name: str
    columns: int
    pk_columns: int
    foreign_keys: int
    unique_constraints: int
    explicit_indexes: int
    check_clauses: int
    strict: int


def normalize_sql(sql: str) -> str:
    """把连续空白归一为单个空格并去首尾。

    这是判据 ⑥ 的唯一归一化手段：**只**折叠空白，不改大小写、不重排 token、
    不删注释（参考 DDL 的 CREATE 语句内部没有注释）。因此「换行位置不同」
    与「缩进不同」被视为等价，而任何 token 级差异都会被保留下来。
    """
    return _WHITESPACE_RUN.sub(" ", sql).strip()


def _ident(name: str) -> str:
    """把标识符包成双引号形式，供 PRAGMA 参数使用。"""
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def _rows(conn: sqlite3.Connection, sql: str) -> list[tuple[Any, ...]]:
    return [tuple(row) for row in conn.execute(sql).fetchall()]


def _strict_flags(conn: sqlite3.Connection) -> dict[str, int]:
    """``PRAGMA table_list`` -> {表名: strict}。列序为 schema,name,type,ncol,wr,strict。"""
    flags: dict[str, int] = {}
    for row in _rows(conn, "PRAGMA table_list"):
        if str(row[0]) != "main" or str(row[2]) != "table":
            continue
        name = str(row[1])
        if name.startswith(_INTERNAL_PREFIX):
            continue
        flags[name] = int(row[5])
    return flags


def table_names(conn: sqlite3.Connection) -> tuple[str, ...]:
    """main 库中的用户表名（升序），排除 ``sqlite_*`` 内部表。"""
    names = [
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    ]
    return tuple(sorted(n for n in names if not n.startswith(_INTERNAL_PREFIX)))


def _object_sql(conn: sqlite3.Connection, object_type: str, name: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type=? AND name=?", (object_type, name)
    ).fetchone()
    if row is None or row[0] is None:
        msg = f"sqlite_master 中找不到 {object_type} {name} 的建对象语句"
        raise LookupError(msg)
    return normalize_sql(str(row[0]))


def index_sql_map(conn: sqlite3.Connection) -> dict[str, str]:
    """显式索引名 -> 归一化后的 CREATE INDEX 语句。

    自动索引（``sqlite_autoindex_*``）的 ``sql`` 为 NULL，不在此表中；它们的等价性
    由 ``table_fingerprint().indexes``（名/unique/origin/partial/列序）覆盖。
    """
    out: dict[str, str] = {}
    for row in conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
    ).fetchall():
        out[str(row[0])] = normalize_sql(str(row[1]))
    return out


def table_fingerprint(conn: sqlite3.Connection, table: str) -> TableFingerprint:
    """取单表的结构指纹（判据 ②③④⑤⑥ 的表侧数据）。"""
    ident = _ident(table)

    columns = tuple(tuple(row) for row in _rows(conn, f"PRAGMA table_info({ident})"))
    foreign_keys = tuple(tuple(row) for row in _rows(conn, f"PRAGMA foreign_key_list({ident})"))

    indexes: list[tuple[str, int, str, int, tuple[str | None, ...]]] = []
    for row in _rows(conn, f"PRAGMA index_list({ident})"):
        index_name = str(row[1])
        info = sorted(_rows(conn, f"PRAGMA index_info({_ident(index_name)})"), key=lambda r: r[0])
        # index_info 的 name 列为 NULL 表示表达式索引；本 DDL 无表达式索引，
        # 但保留 None 语义而不是丢列，避免将来出现表达式索引时被静默当作相等。
        cols = tuple(None if item[2] is None else str(item[2]) for item in info)
        indexes.append((index_name, int(row[2]), str(row[3]), int(row[4]), cols))
    indexes.sort(key=lambda item: item[0])

    return TableFingerprint(
        name=table,
        columns=columns,
        foreign_keys=foreign_keys,
        indexes=tuple(indexes),
        strict=_strict_flags(conn).get(table, -1),
        sql=_object_sql(conn, "table", table),
    )


def schema_summary(conn: sqlite3.Connection) -> list[TableSummary]:
    """每表摘要，供 ``evidence/M0/M0-02/migration-diff.md`` 的指纹表使用。

    ``check_clauses`` 是对归一化 SQL 中 ``CHECK(`` token 的**词法计数**：SQLite 没有
    暴露 CHECK 约束的 PRAGMA。它只用于证据展示，**不参与**等价判定 ——
    等价判定用的是整条归一化 SQL（严格强于任何计数）。
    """
    flags = _strict_flags(conn)
    out: list[TableSummary] = []
    for table in table_names(conn):
        fp = table_fingerprint(conn, table)
        pk_columns = sum(1 for col in fp.columns if col[5])
        fk_ids = {fk[0] for fk in fp.foreign_keys}
        unique_constraints = sum(1 for idx in fp.indexes if idx[1] == 1 and idx[2] in {"pk", "u"})
        explicit_indexes = sum(1 for idx in fp.indexes if idx[2] == "c")
        out.append(
            TableSummary(
                name=table,
                columns=len(fp.columns),
                pk_columns=pk_columns,
                foreign_keys=len(fk_ids),
                unique_constraints=unique_constraints,
                explicit_indexes=explicit_indexes,
                check_clauses=len(_CHECK_TOKEN.findall(fp.sql)),
                strict=flags.get(table, -1),
            )
        )
    return out


def pragma_problems(conn: sqlite3.Connection, label: str) -> list[str]:
    """判据 ⑦：integrity_check 必须为 ok，foreign_key_check 必须返回 0 行。"""
    problems: list[str] = []
    integrity = [str(row[0]) for row in _rows(conn, "PRAGMA integrity_check")]
    if integrity != ["ok"]:
        problems.append(f"{label}: PRAGMA integrity_check != ['ok']，实测 {integrity}")
    fk_violations = _rows(conn, "PRAGMA foreign_key_check")
    if fk_violations:
        problems.append(
            f"{label}: PRAGMA foreign_key_check 返回 {len(fk_violations)} 行，"
            f"样例 {fk_violations[:5]}"
        )
    return problems


def _fingerprint_diffs(ref: TableFingerprint, mig: TableFingerprint) -> list[str]:
    diffs: list[str] = []
    if ref.columns != mig.columns:
        diffs.append(
            f"表 {ref.name}: PRAGMA table_info 不一致\n"
            f"    参考={ref.columns}\n"
            f"    迁移={mig.columns}"
        )
    if ref.foreign_keys != mig.foreign_keys:
        diffs.append(
            f"表 {ref.name}: PRAGMA foreign_key_list 不一致\n"
            f"    参考={ref.foreign_keys}\n"
            f"    迁移={mig.foreign_keys}"
        )
    if ref.indexes != mig.indexes:
        diffs.append(
            f"表 {ref.name}: 索引清单不一致\n    参考={ref.indexes}\n    迁移={mig.indexes}"
        )
    if ref.strict != mig.strict:
        diffs.append(f"表 {ref.name}: STRICT 标志不一致 参考={ref.strict} 迁移={mig.strict}")
    if ref.sql != mig.sql:
        diffs.append(f"表 {ref.name}: 归一化建表语句不一致\n    参考={ref.sql}\n    迁移={mig.sql}")
    return diffs


def compare_schema(
    ref_conn: sqlite3.Connection,
    mig_conn: sqlite3.Connection,
) -> list[str]:
    """比对「参考 DDL 建出的库」与「迁移后的库」。**返回空列表即等价。**

    参数顺序固定为 ``(ref_conn, mig_conn)``；差异文案统一以「参考 / 迁移」标注，
    便于直接贴进证据档而不需要再解释方向。
    """
    diffs: list[str] = []

    ref_tables = table_names(ref_conn)
    mig_tables = table_names(mig_conn)
    mig_comparable = tuple(t for t in mig_tables if t not in MIGRATION_ONLY_TABLES)

    if len(ref_tables) != EXPECTED_TABLE_COUNT:
        diffs.append(f"参考库表数 {len(ref_tables)} != 期望 {EXPECTED_TABLE_COUNT}（分母断言失败）")
    if len(mig_comparable) != EXPECTED_TABLE_COUNT:
        diffs.append(
            f"迁移库表数（排除 {sorted(MIGRATION_ONLY_TABLES)} 后）"
            f"{len(mig_comparable)} != 期望 {EXPECTED_TABLE_COUNT}"
        )

    missing = [t for t in ref_tables if t not in mig_comparable]
    extra = [t for t in mig_comparable if t not in ref_tables]
    if missing:
        diffs.append(f"迁移库缺表 {len(missing)} 张: {missing}")
    if extra:
        allowed = sorted(MIGRATION_ONLY_TABLES)
        diffs.append(f"迁移库多出表 {len(extra)} 张（不在 {allowed} 白名单内）: {extra}")

    ref_flags = _strict_flags(ref_conn)
    for table in ref_tables:
        if table in missing:
            continue  # 已作为「缺表」报出，再逐列比只会刷屏
        if ref_flags.get(table) != 1:
            diffs.append(f"表 {table}: 参考库的 STRICT 标志为 {ref_flags.get(table)}，期望 1")
        ref_fp = table_fingerprint(ref_conn, table)
        mig_fp = table_fingerprint(mig_conn, table)
        diffs.extend(_fingerprint_diffs(ref_fp, mig_fp))

    mig_flags = _strict_flags(mig_conn)
    for table in mig_comparable:
        if mig_flags.get(table) != 1:
            diffs.append(
                f"表 {table}: 迁移库的 STRICT 标志为 {mig_flags.get(table)}，"
                f"期望 1（{EXPECTED_TABLE_COUNT} 表全为 STRICT）"
            )

    ref_indexes = index_sql_map(ref_conn)
    mig_indexes = index_sql_map(mig_conn)
    if sorted(ref_indexes) != sorted(mig_indexes):
        diffs.append(
            f"显式索引名集合不一致\n    参考={sorted(ref_indexes)}\n    迁移={sorted(mig_indexes)}"
        )
    for name in sorted(set(ref_indexes) & set(mig_indexes)):
        if ref_indexes[name] != mig_indexes[name]:
            diffs.append(
                f"索引 {name}: 归一化 CREATE INDEX 不一致\n"
                f"    参考={ref_indexes[name]}\n    迁移={mig_indexes[name]}"
            )

    diffs.extend(pragma_problems(ref_conn, "参考库"))
    diffs.extend(pragma_problems(mig_conn, "迁移库"))
    return diffs
