"""首迁：CampaignLab SQLite v1 的 28 张表与 6 个显式索引。

来源与可追溯性
--------------
建表语句逐字取自活契约 ``contracts/sqlite-v1.sql``
（sha256 ``ec9ddfbc4e7dba4c0a565161b50a222fee484eb07e6586588871bffa2efc8c0e``，17284 字节，
与只读基线 ``spec/CampaignLab-SDD-v1.0/contracts/sqlite-v1.sql`` 字节相同）。
唯一的改写是**空白归一**：原文按可读性换行缩进，本文件为了通过仓库的
``ruff line-length = 100`` 而把每条语句折成 <=88 字符的相邻字面量；
Python 在编译期拼接相邻字面量，故运行时执行的 SQL 与「原文折叠空白后」逐字节相同。
等价性由 ``src/campaignlab/infra/db/ddl_compare.py::compare_schema`` 判定
（判据 ⑥ 正是「``sqlite_master.sql`` 空白归一后逐对象相等」）。

本文件**不**在运行时读取 ``contracts/sqlite-v1.sql``：迁移必须自包含，
否则「按锁版本重放迁移」会依赖一个可被后续 CR 改动的活文件（AC-035 不可复现）。

为什么是手写 SQL 而不是 ``op.create_table``
------------------------------------------
参考 DDL 用到三种 SQLAlchemy DDL 编译器无法表达（或表达后不等价）的 SQLite 特性：

1. ``STRICT`` 表（28 张全是），决定列类型亲和性的强校验；
2. **复合外键**，例如
   ``FOREIGN KEY(workspace_id, artifact_id) REFERENCES artifacts(workspace_id, id)``，
   这是「跨工作区引用必须被拒绝」的数据库级兜底；
3. **部分唯一索引** ``cases_one_confirmed_child``（带 ``WHERE`` 子句）。

用 ``op.create_table`` 重建会丢失上述语义或产生不同的 ``sqlite_master.sql``，
故按 alembic 官方对 SQLite 的推荐做法，用 ``op.execute`` 下发原文 DDL。

PRAGMA
------
``PRAGMA foreign_keys=ON`` **不在本文件里执行**：SQLite 明确规定该 PRAGMA 在事务内是
no-op，而 alembic 把每个迁移包在事务里。它由 ``migrations/env.py`` 在**建连接时**设置
（同时设 ``busy_timeout=5000``、``journal_mode=DELETE``）。

修订标识
--------
``revision = "0001_initial_schema"``、``down_revision = None``：
``Health.schema_revision`` 与「schema 是否为最新」的判定都以此串为准（设计档 §1/§3）。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 建表顺序与参考 DDL 完全一致。表之间存在前后向引用
# （activities -> rule_versions、imports -> snapshots/jobs、cases -> actions、
# snapshots -> imports 与 imports -> snapshots 互为前后），SQLite 允许建表时引用
# 尚不存在的表，外键在**使用**时才校验，故保持原序即正确，不需要拓扑排序。

_CREATE_TABLE_STATEMENTS: Final[tuple[str, ...]] = (
    # --- workspaces ---
    "CREATE TABLE workspaces ( id TEXT PRIMARY KEY, name TEXT NOT NULL, source_class TEXT NOT"
    " NULL CHECK(source_class IN ('SYNTHETIC','AUTHORIZED_DEIDENTIFIED')), authorization_note"
    " TEXT, revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>=1), created_at TEXT NOT NULL,"
    " CHECK(source_class='SYNTHETIC' OR length(coalesce(authorization_note,''))>0) ) STRICT",
    # --- artifacts ---
    "CREATE TABLE artifacts ( workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT"
    " NOT NULL, kind TEXT NOT NULL, sha256 TEXT NOT NULL CHECK(length(sha256)=64),"
    " relative_path TEXT NOT NULL UNIQUE, byte_size INTEGER NOT NULL CHECK(byte_size>=0),"
    " created_at TEXT NOT NULL, PRIMARY KEY(workspace_id,id),"
    " UNIQUE(workspace_id,kind,sha256) ) STRICT",
    # --- activities ---
    "CREATE TABLE activities ( workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT"
    " NOT NULL, name TEXT NOT NULL, bank_id TEXT, external_activity_id TEXT, description TEXT"
    " NOT NULL, status TEXT NOT NULL CHECK(status IN ('OPEN','ARCHIVED')), current_rule_id"
    " TEXT, revision INTEGER NOT NULL CHECK(revision>=1), created_at TEXT NOT NULL, PRIMARY"
    " KEY(workspace_id,id), UNIQUE(workspace_id,bank_id,external_activity_id), FOREIGN"
    " KEY(workspace_id,current_rule_id) REFERENCES rule_versions(workspace_id,id) ) STRICT",
    # --- evidence ---
    "CREATE TABLE evidence ( workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT"
    " NOT NULL, kind TEXT NOT NULL CHECK(kind IN"
    " ('SOURCE','CLAUSE','COMPUTATION','TRACE','PREFLIGHT','RECEIPT','SIGNATURE','EXPERIMENT'"
    ",'REVIEW_NOTE')), source_id TEXT NOT NULL, locator TEXT NOT NULL, label TEXT NOT NULL,"
    " source_class TEXT NOT NULL, content_digest TEXT NOT NULL"
    " CHECK(length(content_digest)=64), artifact_id TEXT NOT NULL, created_at TEXT NOT NULL,"
    " PRIMARY KEY(workspace_id,id), FOREIGN KEY(workspace_id,artifact_id) REFERENCES"
    " artifacts(workspace_id,id) ) STRICT",
    # --- activity_bindings ---
    "CREATE TABLE activity_bindings ( workspace_id TEXT NOT NULL, activity_id TEXT NOT NULL,"
    " strategy_id TEXT NOT NULL, source_version TEXT NOT NULL, valid_from TEXT NOT NULL,"
    " valid_until TEXT NOT NULL CHECK(valid_until>valid_from), evidence_id TEXT NOT NULL,"
    " PRIMARY KEY(workspace_id,activity_id,strategy_id,source_version,valid_from), FOREIGN"
    " KEY(workspace_id,activity_id) REFERENCES activities(workspace_id,id), FOREIGN"
    " KEY(workspace_id,evidence_id) REFERENCES evidence(workspace_id,id) ) STRICT",
    # --- rule_versions ---
    "CREATE TABLE rule_versions ( workspace_id TEXT NOT NULL, id TEXT NOT NULL, activity_id"
    " TEXT NOT NULL, parent_rule_id TEXT, label TEXT NOT NULL, template TEXT NOT NULL"
    " CHECK(template IN ('coupon_threshold','callback_priority')), source_rule_version TEXT,"
    " state TEXT NOT NULL CHECK(state IN ('DRAFT','CONFIRMED')), revision INTEGER NOT NULL"
    " CHECK(revision>=1), content_json TEXT NOT NULL CHECK(json_valid(content_json)),"
    " terms_json TEXT NOT NULL CHECK(json_valid(terms_json)), digest TEXT NOT NULL"
    " CHECK(length(digest)=64), created_at TEXT NOT NULL, confirmed_at TEXT, confirmation"
    " TEXT, CHECK((state='CONFIRMED')=(confirmed_at IS NOT NULL AND confirmation IS NOT"
    " NULL)), PRIMARY KEY(workspace_id,id), FOREIGN KEY(workspace_id,activity_id) REFERENCES"
    " activities(workspace_id,id), FOREIGN KEY(workspace_id,parent_rule_id) REFERENCES"
    " rule_versions(workspace_id,id) ) STRICT",
    # --- source_mappings ---
    "CREATE TABLE source_mappings ( workspace_id TEXT NOT NULL REFERENCES workspaces(id), id"
    " TEXT NOT NULL, bank_id TEXT NOT NULL, content_json TEXT NOT NULL"
    " CHECK(json_valid(content_json)), digest TEXT NOT NULL CHECK(length(digest)=64),"
    " created_at TEXT NOT NULL, PRIMARY KEY(workspace_id,id) ) STRICT",
    # --- imports ---
    "CREATE TABLE imports ( workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT"
    " NULL, bank_id TEXT NOT NULL, snapshot_code TEXT NOT NULL, format TEXT NOT NULL"
    " CHECK(format IN ('LEGACY_SYNTHETIC_JSON','SOURCE_JSON','SOURCE_CSV')), state TEXT NOT"
    " NULL CHECK(state IN"
    " ('RECEIVED','CONFIGURED','VALIDATING','VALID','INVALID','PUBLISHING','PUBLISHED')),"
    " mapping_id TEXT, validation_digest TEXT, issue_json TEXT NOT NULL"
    " CHECK(json_valid(issue_json)), snapshot_id TEXT, correction_of TEXT, job_id TEXT,"
    " revision INTEGER NOT NULL CHECK(revision>=1), created_at TEXT NOT NULL, PRIMARY"
    " KEY(workspace_id,id), FOREIGN KEY(workspace_id,mapping_id) REFERENCES"
    " source_mappings(workspace_id,id), FOREIGN KEY(workspace_id,snapshot_id) REFERENCES"
    " snapshots(workspace_id,id), FOREIGN KEY(workspace_id,correction_of) REFERENCES"
    " snapshots(workspace_id,id), FOREIGN KEY(workspace_id,job_id) REFERENCES"
    " jobs(workspace_id,id) ) STRICT",
    # --- import_files ---
    "CREATE TABLE import_files ( workspace_id TEXT NOT NULL, id TEXT NOT NULL, import_id TEXT"
    " NOT NULL, artifact_id TEXT NOT NULL, table_name TEXT NOT NULL, label TEXT NOT NULL,"
    " PRIMARY KEY(workspace_id,id), UNIQUE(workspace_id,import_id,table_name), FOREIGN"
    " KEY(workspace_id,import_id) REFERENCES imports(workspace_id,id), FOREIGN"
    " KEY(workspace_id,artifact_id) REFERENCES artifacts(workspace_id,id) ) STRICT",
    # --- snapshots ---
    "CREATE TABLE snapshots ( workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT"
    " NOT NULL, bank_id TEXT NOT NULL, snapshot_code TEXT NOT NULL, mapping_id TEXT NOT NULL,"
    " import_id TEXT, correction_of TEXT, row_count INTEGER NOT NULL CHECK(row_count>=0),"
    " artifact_id TEXT NOT NULL, metadata_json TEXT NOT NULL"
    " CHECK(json_valid(metadata_json)), digest TEXT NOT NULL CHECK(length(digest)=64),"
    " created_at TEXT NOT NULL, PRIMARY KEY(workspace_id,id),"
    " UNIQUE(workspace_id,bank_id,snapshot_code), FOREIGN KEY(workspace_id,import_id)"
    " REFERENCES imports(workspace_id,id), FOREIGN KEY(workspace_id,mapping_id) REFERENCES"
    " source_mappings(workspace_id,id), FOREIGN KEY(workspace_id,correction_of) REFERENCES"
    " snapshots(workspace_id,id), FOREIGN KEY(workspace_id,artifact_id) REFERENCES"
    " artifacts(workspace_id,id) ) STRICT",
    # --- cases ---
    "CREATE TABLE cases ( workspace_id TEXT NOT NULL, id TEXT NOT NULL, activity_id TEXT NOT"
    " NULL, parent_case_id TEXT, name TEXT NOT NULL, mode TEXT NOT NULL CHECK(mode IN"
    " ('SYNTHETIC','HISTORICAL')), state TEXT NOT NULL CHECK(state IN ('DRAFT','CONFIRMED')),"
    " revision INTEGER NOT NULL CHECK(revision>=1), input_json TEXT NOT NULL"
    " CHECK(json_valid(input_json)), expected_json TEXT CHECK(expected_json IS NULL OR"
    " json_valid(expected_json)), observed_original_json TEXT CHECK(observed_original_json IS"
    " NULL OR json_valid(observed_original_json)), observed_rule_id TEXT, action_id TEXT,"
    " digest TEXT NOT NULL CHECK(length(digest)=64), confirmation TEXT, created_at TEXT NOT"
    " NULL, PRIMARY KEY(workspace_id,id), FOREIGN KEY(workspace_id,activity_id) REFERENCES"
    " activities(workspace_id,id), FOREIGN KEY(workspace_id,parent_case_id) REFERENCES"
    " cases(workspace_id,id), FOREIGN KEY(workspace_id,observed_rule_id) REFERENCES"
    " rule_versions(workspace_id,id), FOREIGN KEY(workspace_id,action_id) REFERENCES"
    " actions(workspace_id,id) ) STRICT",
    # --- thresholds ---
    "CREATE TABLE thresholds ( workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT"
    " NOT NULL, label TEXT NOT NULL, values_json TEXT NOT NULL"
    " CHECK(json_valid(values_json)), digest TEXT NOT NULL CHECK(length(digest)=64),"
    " created_at TEXT NOT NULL, PRIMARY KEY(workspace_id,id) ) STRICT",
    # --- analysis_results ---
    "CREATE TABLE analysis_results ( workspace_id TEXT NOT NULL REFERENCES workspaces(id), id"
    " TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN"
    " ('comparison','review','diagnosis','question')), input_json TEXT NOT NULL"
    " CHECK(json_valid(input_json)), artifact_id TEXT NOT NULL, digest TEXT NOT NULL"
    " CHECK(length(digest)=64), snapshot_id TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY"
    " KEY(workspace_id,id), FOREIGN KEY(workspace_id,artifact_id) REFERENCES"
    " artifacts(workspace_id,id), FOREIGN KEY(workspace_id,snapshot_id) REFERENCES"
    " snapshots(workspace_id,id) ) STRICT",
    # --- runs ---
    "CREATE TABLE runs ( workspace_id TEXT NOT NULL, id TEXT NOT NULL, activity_id TEXT NOT"
    " NULL, baseline_rule_id TEXT NOT NULL, candidate_rule_id TEXT, snapshot_id TEXT,"
    " request_json TEXT NOT NULL CHECK(json_valid(request_json)), artifact_id TEXT NOT NULL,"
    " digest TEXT NOT NULL CHECK(length(digest)=64), created_at TEXT NOT NULL, PRIMARY"
    " KEY(workspace_id,id), FOREIGN KEY(workspace_id,activity_id) REFERENCES"
    " activities(workspace_id,id), FOREIGN KEY(workspace_id,baseline_rule_id) REFERENCES"
    " rule_versions(workspace_id,id), FOREIGN KEY(workspace_id,candidate_rule_id) REFERENCES"
    " rule_versions(workspace_id,id), FOREIGN KEY(workspace_id,snapshot_id) REFERENCES"
    " snapshots(workspace_id,id), FOREIGN KEY(workspace_id,artifact_id) REFERENCES"
    " artifacts(workspace_id,id) ) STRICT",
    # --- run_cases ---
    "CREATE TABLE run_cases ( workspace_id TEXT NOT NULL, run_id TEXT NOT NULL, case_id TEXT"
    " NOT NULL, case_digest TEXT NOT NULL CHECK(length(case_digest)=64), PRIMARY"
    " KEY(workspace_id,run_id,case_id), FOREIGN KEY(workspace_id,run_id) REFERENCES"
    " runs(workspace_id,id), FOREIGN KEY(workspace_id,case_id) REFERENCES"
    " cases(workspace_id,id) ) STRICT",
    # --- candidates ---
    "CREATE TABLE candidates ( workspace_id TEXT NOT NULL, id TEXT NOT NULL, run_id TEXT NOT"
    " NULL, case_id TEXT NOT NULL, rule_id TEXT NOT NULL, case_digest TEXT NOT NULL"
    " CHECK(length(case_digest)=64), rule_digest TEXT NOT NULL CHECK(length(rule_digest)=64),"
    " expected_json TEXT NOT NULL CHECK(json_valid(expected_json)), review_note TEXT NOT"
    " NULL, created_at TEXT NOT NULL, PRIMARY KEY(workspace_id,id),"
    " UNIQUE(workspace_id,run_id,case_id), FOREIGN KEY(workspace_id,run_id,case_id)"
    " REFERENCES run_cases(workspace_id,run_id,case_id), FOREIGN KEY(workspace_id,rule_id)"
    " REFERENCES rule_versions(workspace_id,id) ) STRICT",
    # --- preflights ---
    "CREATE TABLE preflights ( workspace_id TEXT NOT NULL, id TEXT NOT NULL, activity_id TEXT"
    " NOT NULL, source_batch TEXT NOT NULL, observed_at TEXT NOT NULL, state TEXT NOT NULL"
    " CHECK(state IN ('MATCH','REVIEW_REQUIRED')), artifact_id TEXT NOT NULL, digest TEXT NOT"
    " NULL CHECK(length(digest)=64), review_note TEXT, revision INTEGER NOT NULL"
    " CHECK(revision>=1), created_at TEXT NOT NULL, PRIMARY KEY(workspace_id,id),"
    " UNIQUE(workspace_id,activity_id,source_batch), FOREIGN KEY(workspace_id,activity_id)"
    " REFERENCES activities(workspace_id,id), FOREIGN KEY(workspace_id,artifact_id)"
    " REFERENCES artifacts(workspace_id,id) ) STRICT",
    # --- preflight_rows ---
    "CREATE TABLE preflight_rows ( workspace_id TEXT NOT NULL, preflight_id TEXT NOT NULL,"
    " candidate_id TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN"
    " ('MATCH','DIFF','MISSING','VERSION_MISMATCH','STALE')), PRIMARY"
    " KEY(workspace_id,preflight_id,candidate_id), FOREIGN KEY(workspace_id,preflight_id)"
    " REFERENCES preflights(workspace_id,id), FOREIGN KEY(workspace_id,candidate_id)"
    " REFERENCES candidates(workspace_id,id) ) STRICT",
    # --- receipts ---
    "CREATE TABLE receipts ( workspace_id TEXT NOT NULL, id TEXT NOT NULL, activity_id TEXT"
    " NOT NULL, preflight_id TEXT NOT NULL, source_system TEXT NOT NULL, source_release_id"
    " TEXT NOT NULL, source_version TEXT NOT NULL, rule_digest TEXT NOT NULL"
    " CHECK(length(rule_digest)=64), released_at TEXT NOT NULL, evidence_id TEXT NOT NULL,"
    " created_at TEXT NOT NULL, PRIMARY KEY(workspace_id,id),"
    " UNIQUE(workspace_id,activity_id,source_system,source_release_id), FOREIGN"
    " KEY(workspace_id,activity_id) REFERENCES activities(workspace_id,id), FOREIGN"
    " KEY(workspace_id,preflight_id) REFERENCES preflights(workspace_id,id), FOREIGN"
    " KEY(workspace_id,evidence_id) REFERENCES evidence(workspace_id,id) ) STRICT",
    # --- reports ---
    "CREATE TABLE reports ( workspace_id TEXT NOT NULL, id TEXT NOT NULL, review_id TEXT NOT"
    " NULL, previous_report_id TEXT, state TEXT NOT NULL CHECK(state IN"
    " ('DRAFT_READY','PARTIAL_DRAFT','DATA_REQUIRED','SIGNED')), input_json TEXT NOT NULL"
    " CHECK(json_valid(input_json)), artifact_id TEXT NOT NULL, digest TEXT NOT NULL"
    " CHECK(length(digest)=64), signer TEXT, signed_at TEXT, signature_evidence_id TEXT,"
    " revision INTEGER NOT NULL CHECK(revision>=1), created_at TEXT NOT NULL,"
    " CHECK((state='SIGNED')=(signed_at IS NOT NULL AND signer IS NOT NULL AND"
    " signature_evidence_id IS NOT NULL)), PRIMARY KEY(workspace_id,id), FOREIGN"
    " KEY(workspace_id,review_id) REFERENCES analysis_results(workspace_id,id), FOREIGN"
    " KEY(workspace_id,previous_report_id) REFERENCES reports(workspace_id,id), FOREIGN"
    " KEY(workspace_id,artifact_id) REFERENCES artifacts(workspace_id,id), FOREIGN"
    " KEY(workspace_id,signature_evidence_id) REFERENCES evidence(workspace_id,id) ) STRICT",
    # --- actions ---
    "CREATE TABLE actions ( workspace_id TEXT NOT NULL, id TEXT NOT NULL, review_id TEXT NOT"
    " NULL, diagnosis_id TEXT, title TEXT NOT NULL, owner TEXT NOT NULL, due_on TEXT NOT"
    " NULL, checkpoint_days INTEGER NOT NULL CHECK(checkpoint_days IN (30,90)), hypothesis"
    " TEXT NOT NULL, verification TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN"
    " ('OPEN','IN_PROGRESS','WAITING_VALIDATION','VERIFIED','CLOSED','CANCELLED')),"
    " needs_review INTEGER NOT NULL CHECK(needs_review IN (0,1)), revision INTEGER NOT NULL"
    " CHECK(revision>=1), created_at TEXT NOT NULL, PRIMARY KEY(workspace_id,id), FOREIGN"
    " KEY(workspace_id,review_id) REFERENCES analysis_results(workspace_id,id), FOREIGN"
    " KEY(workspace_id,diagnosis_id) REFERENCES analysis_results(workspace_id,id) ) STRICT",
    # --- action_followups ---
    "CREATE TABLE action_followups ( workspace_id TEXT NOT NULL, action_id TEXT NOT NULL, id"
    " TEXT NOT NULL, next_review_id TEXT NOT NULL, receipt_id TEXT, details_json TEXT NOT"
    " NULL CHECK(json_valid(details_json)), created_at TEXT NOT NULL, PRIMARY"
    " KEY(workspace_id,action_id,id), FOREIGN KEY(workspace_id,action_id) REFERENCES"
    " actions(workspace_id,id), FOREIGN KEY(workspace_id,next_review_id) REFERENCES"
    " analysis_results(workspace_id,id), FOREIGN KEY(workspace_id,receipt_id) REFERENCES"
    " receipts(workspace_id,id) ) STRICT",
    # --- report_actions ---
    "CREATE TABLE report_actions ( workspace_id TEXT NOT NULL, report_id TEXT NOT NULL,"
    " action_id TEXT NOT NULL, PRIMARY KEY(workspace_id,report_id,action_id), FOREIGN"
    " KEY(workspace_id,report_id) REFERENCES reports(workspace_id,id), FOREIGN"
    " KEY(workspace_id,action_id) REFERENCES actions(workspace_id,id) ) STRICT",
    # --- exports ---
    "CREATE TABLE exports ( workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT"
    " NULL, kind TEXT NOT NULL, subject_json TEXT NOT NULL CHECK(json_valid(subject_json)),"
    " reason TEXT NOT NULL, filename TEXT NOT NULL, artifact_id TEXT NOT NULL, created_at"
    " TEXT NOT NULL, PRIMARY KEY(workspace_id,id), FOREIGN KEY(workspace_id,artifact_id)"
    " REFERENCES artifacts(workspace_id,id) ) STRICT",
    # --- jobs ---
    "CREATE TABLE jobs ( workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT"
    " NULL, kind TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN"
    " ('QUEUED','RUNNING','CANCEL_REQUESTED','SUCCEEDED','FAILED','CANCELLED')), attempt"
    " INTEGER NOT NULL CHECK(attempt>=0), progress INTEGER NOT NULL CHECK(progress BETWEEN 0"
    " AND 100), stage TEXT NOT NULL, lease_token TEXT, lease_until TEXT, retry_of TEXT,"
    " retryable INTEGER NOT NULL CHECK(retryable IN (0,1)), input_json TEXT NOT NULL"
    " CHECK(json_valid(input_json)), input_digest TEXT NOT NULL"
    " CHECK(length(input_digest)=64), result_json TEXT CHECK(result_json IS NULL OR"
    " json_valid(result_json)), problem_json TEXT CHECK(problem_json IS NULL OR"
    " json_valid(problem_json)), revision INTEGER NOT NULL CHECK(revision>=1), created_at"
    " TEXT NOT NULL, CHECK((state IN ('RUNNING','CANCEL_REQUESTED'))=(lease_token IS NOT NULL"
    " AND lease_until IS NOT NULL)), CHECK((state='SUCCEEDED')=(result_json IS NOT NULL)),"
    " PRIMARY KEY(workspace_id,id), FOREIGN KEY(workspace_id,retry_of) REFERENCES"
    " jobs(workspace_id,id) ) STRICT",
    # --- object_evidence ---
    "CREATE TABLE object_evidence ( workspace_id TEXT NOT NULL, object_kind TEXT NOT NULL,"
    " object_id TEXT NOT NULL, evidence_id TEXT NOT NULL, PRIMARY"
    " KEY(workspace_id,object_kind,object_id,evidence_id), FOREIGN"
    " KEY(workspace_id,evidence_id) REFERENCES evidence(workspace_id,id) ) STRICT",
    # --- idempotency ---
    "CREATE TABLE idempotency ( scope_key TEXT NOT NULL, actor_id TEXT NOT NULL, operation"
    " TEXT NOT NULL, idem_key TEXT NOT NULL, request_digest TEXT NOT NULL"
    " CHECK(length(request_digest)=64), response_status INTEGER NOT NULL, response_json TEXT"
    " NOT NULL CHECK(json_valid(response_json)), created_at TEXT NOT NULL, PRIMARY"
    " KEY(scope_key,actor_id,operation,idem_key) ) STRICT",
    # --- audit ---
    "CREATE TABLE audit ( workspace_id TEXT NOT NULL REFERENCES workspaces(id), sequence"
    " INTEGER NOT NULL CHECK(sequence>=1), id TEXT NOT NULL, at TEXT NOT NULL, actor_id TEXT"
    " NOT NULL, role TEXT NOT NULL, action TEXT NOT NULL, target_kind TEXT NOT NULL,"
    " target_id TEXT NOT NULL, outcome TEXT NOT NULL CHECK(outcome IN"
    " ('ACCEPTED','DENIED','FAILED')), request_id TEXT NOT NULL, previous_digest TEXT, digest"
    " TEXT NOT NULL CHECK(length(digest)=64), PRIMARY KEY(workspace_id,sequence),"
    " UNIQUE(workspace_id,id) ) STRICT",
)

_CREATE_INDEX_STATEMENTS: Final[tuple[str, ...]] = (
    # --- cases_one_confirmed_child ---
    "CREATE UNIQUE INDEX cases_one_confirmed_child ON cases(workspace_id,parent_case_id)"
    " WHERE parent_case_id IS NOT NULL AND state='CONFIRMED'",
    # --- jobs_ready ---
    "CREATE INDEX jobs_ready ON jobs(state,created_at,workspace_id,id)",
    # --- snapshots_lookup ---
    "CREATE INDEX snapshots_lookup ON snapshots(workspace_id,bank_id,created_at)",
    # --- rules_activity ---
    "CREATE INDEX rules_activity ON rule_versions(workspace_id,activity_id,created_at)",
    # --- analysis_snapshot ---
    "CREATE INDEX analysis_snapshot ON analysis_results(workspace_id,snapshot_id,kind)",
    # --- actions_due ---
    "CREATE INDEX actions_due ON actions(workspace_id,state,due_on)",
)

# 建表顺序（用于 downgrade 逆序 DROP TABLE）。
_TABLE_NAMES: Final[tuple[str, ...]] = (
    "workspaces",
    "artifacts",
    "activities",
    "evidence",
    "activity_bindings",
    "rule_versions",
    "source_mappings",
    "imports",
    "import_files",
    "snapshots",
    "cases",
    "thresholds",
    "analysis_results",
    "runs",
    "run_cases",
    "candidates",
    "preflights",
    "preflight_rows",
    "receipts",
    "reports",
    "actions",
    "action_followups",
    "report_actions",
    "exports",
    "jobs",
    "object_evidence",
    "idempotency",
    "audit",
)

# 显式索引名（用于 downgrade 逆序 DROP INDEX）。共 6 个：
# 1 个部分唯一索引 cases_one_confirmed_child ＋ 5 个普通索引。
# 设计档 §3 写「5 个显式索引」，漏计了 cases_one_confirmed_child；
# 以活契约 contracts/sqlite-v1.sql 为准（手册第 7 节：活契约是实现唯一依据）。
_INDEX_NAMES: Final[tuple[str, ...]] = (
    "cases_one_confirmed_child",
    "jobs_ready",
    "snapshots_lookup",
    "rules_activity",
    "analysis_snapshot",
    "actions_due",
)


def upgrade() -> None:
    """建 28 张表与 6 个显式索引。"""
    for statement in _CREATE_TABLE_STATEMENTS:
        op.execute(statement)
    for statement in _CREATE_INDEX_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    """完整可逆：先逆序删显式索引，再逆序删表。

    逆序是为了让「被引用者后删」，即使库中已有数据、``foreign_keys=ON``，
    DROP TABLE 隐含的 DELETE 也不会因为仍有子表引用而失败。
    自动索引（``sqlite_autoindex_*``）随所属表一起消失，无需显式处理。
    """
    for name in reversed(_INDEX_NAMES):
        op.execute(f"DROP INDEX {name}")
    for name in reversed(_TABLE_NAMES):
        op.execute(f"DROP TABLE {name}")
