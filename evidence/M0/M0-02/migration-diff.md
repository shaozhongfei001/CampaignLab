# M0-02 · S2 首迁等价性证据（migration-diff.md）

- 生成方式：**全部数据由脚本实跑取得**，无转录、无估算。
- 比对器：`src/campaignlab/infra/db/ddl_compare.py::compare_schema(ref_conn, mig_conn) -> list[str]`，**返回空列表即等价**。
- 参考库：`contracts/sqlite-v1.sql` 经 `sqlite3.Connection.executescript` 建出的内存库。
- 迁移库：`CAMPAIGNLAB_DATA_DIR=/tmp/s2ev_2iq_y294` 下由 `alembic -c migrations/alembic.ini upgrade head` **真实执行**产出的文件库 `/tmp/s2ev_2iq_y294/state/campaignlab.db`（迁移脚本自包含，运行时不读 DDL 文件）。

## 0. 基准与指纹

| 项 | 实测值 |
|---|---|
| `contracts/sqlite-v1.sql` sha256 | `ec9ddfbc4e7dba4c0a565161b50a222fee484eb07e6586588871bffa2efc8c0e` |
| `spec/CampaignLab-SDD-v1.0/contracts/sqlite-v1.sql` 与活契约字节相同 | `是（sha256 相等，17284 B）` |
| 任务卡给定的期望 sha256 | `ec9ddfbc4e7dba4c0a565161b50a222fee484eb07e6586588871bffa2efc8c0e` |
| 指纹一致 | `True` |
| alembic head（`SELECT version_num FROM alembic_version`） | `[('0001_initial_schema',)]` |
| `sqlite_master` 中 type='table' 的对象数 | 29（含 `alembic_version` 簿记表） |
| **业务表数（排除 `alembic_version`）** | **28** |
| `sqlite_master` 中 type='index' 且 sql 非空（显式索引）数 | 6 |

### PRE-3 契约新鲜度三方比对（开工第一步）

| 来源 | sha16 | bytes |
|---|---|---|
| 实算 `contracts/openapi.json` | `592571099d638251` | 443309 |
| 权威 `state.json → resume.self_check_gates_rc0.counts` | `592571099d638251` | 443309 |
| 切片 `M0-02.slice.json → source.openapi` | `592571099d638251` | 443309 |

**三方一致：`True`** → 切片新鲜、可继续（不一致即 BLOCKER，不得自行重切）。

## 1. `compare_schema()` 的返回值（总判据）

```python
compare_schema(ref_conn, mig_conn)  # -> list[str]
```

实测返回：

```python
[]
```

长度 = **0**，即**空返回** → 判据 ①–⑦ 全部通过。

覆盖的判据（设计档 §3）：① 表集合相等且 28；② `PRAGMA table_info` 六元组；③ `PRAGMA foreign_key_list` 八元组（复合外键列序敏感）；④ `PRAGMA index_list` + `index_info`；⑤ `PRAGMA table_list.strict` 全为 1；⑥ `sqlite_master.sql` 空白归一后逐对象相等（表 + 显式索引，含部分唯一索引的 `WHERE` 子句）；⑦ `integrity_check` / `foreign_key_check`。

### 比对器非空转证明（变异测试，`tests/unit/test_migration_schema.py`）

一个恒返回 `[]` 的比对器同样能让上面这条全绿，故对参考 DDL 注入 8 种单点变异，逐一要求**必须**报出差异且差异指向被改对象：

| 变异 | 测试 | 结果 |
|---|---|---|
| 多建一张表 `zz_extra` | `test_detects_added_table` | PASS |
| 少建一张表 `thresholds` | `test_detects_missing_table` | PASS |
| 改列名 `thresholds.label → title` | `test_detects_renamed_column` | PASS |
| 改默认值 `workspaces.revision DEFAULT 1 → 2` | `test_detects_changed_default` | PASS |
| 改 CHECK `length(sha256)=64 → 32` | `test_detects_changed_check_clause` | PASS |
| `workspaces` 丢掉 `STRICT` | `test_detects_lost_strict` | PASS |
| 改部分唯一索引 `WHERE state='CONFIRMED' → 'DRAFT'` | `test_detects_changed_partial_index` | PASS |
| 8 处外键加 `ON DELETE CASCADE` | `test_detects_changed_foreign_key_action` | PASS |
| 少建显式索引 `actions_due` | `test_detects_dropped_explicit_index` | PASS |
| 制造悬挂外键引用（`foreign_key_check` 可查） | `test_detects_integrity_or_fk_violation` | PASS |

## 2. 28 表指纹摘要（迁移库实测，逐表与参考库比对一致）

`CHECK 子句数` 为对归一化 SQL 中 `CHECK(` token 的**词法计数**（SQLite 无暴露 CHECK 的 PRAGMA）；它只用于展示，等价判定用的是整条归一化 `sqlite_master.sql`（严格强于任何计数）。

| # | 表名 | 列数 | 主键列数 | 外键声明数 | 唯一约束数 | 显式索引数 | CHECK 子句数 | STRICT |
|---|---|---|---|---|---|---|---|---|
| 1 | `action_followups` | 7 | 3 | 3 | 1 | 0 | 1 | 1 |
| 2 | `actions` | 14 | 2 | 2 | 1 | 1 | 4 | 1 |
| 3 | `activities` | 10 | 2 | 2 | 2 | 0 | 2 | 1 |
| 4 | `activity_bindings` | 7 | 5 | 2 | 1 | 0 | 1 | 1 |
| 5 | `alembic_version` | 1 | 1 | 0 | 1 | 0 | 0 | 0 |
| 6 | `analysis_results` | 8 | 2 | 3 | 1 | 1 | 3 | 1 |
| 7 | `artifacts` | 7 | 2 | 1 | 3 | 0 | 2 | 1 |
| 8 | `audit` | 13 | 2 | 1 | 2 | 0 | 3 | 1 |
| 9 | `candidates` | 10 | 2 | 2 | 2 | 0 | 3 | 1 |
| 10 | `cases` | 16 | 2 | 4 | 1 | 1 | 7 | 1 |
| 11 | `evidence` | 10 | 2 | 2 | 1 | 0 | 2 | 1 |
| 12 | `exports` | 8 | 2 | 2 | 1 | 0 | 1 | 1 |
| 13 | `idempotency` | 8 | 4 | 0 | 1 | 0 | 2 | 1 |
| 14 | `import_files` | 6 | 2 | 2 | 2 | 0 | 0 | 1 |
| 15 | `imports` | 14 | 2 | 5 | 1 | 0 | 4 | 1 |
| 16 | `jobs` | 17 | 2 | 2 | 1 | 1 | 11 | 1 |
| 17 | `object_evidence` | 4 | 4 | 1 | 1 | 0 | 0 | 1 |
| 18 | `preflight_rows` | 4 | 3 | 2 | 1 | 0 | 1 | 1 |
| 19 | `preflights` | 11 | 2 | 2 | 2 | 0 | 3 | 1 |
| 20 | `receipts` | 11 | 2 | 3 | 2 | 0 | 1 | 1 |
| 21 | `report_actions` | 3 | 3 | 2 | 1 | 0 | 0 | 1 |
| 22 | `reports` | 13 | 2 | 4 | 1 | 0 | 5 | 1 |
| 23 | `rule_versions` | 15 | 2 | 2 | 1 | 1 | 7 | 1 |
| 24 | `run_cases` | 4 | 3 | 2 | 1 | 0 | 1 | 1 |
| 25 | `runs` | 10 | 2 | 5 | 1 | 0 | 2 | 1 |
| 26 | `snapshots` | 12 | 2 | 5 | 2 | 1 | 3 | 1 |
| 27 | `source_mappings` | 6 | 2 | 1 | 1 | 0 | 2 | 1 |
| 28 | `thresholds` | 6 | 2 | 1 | 1 | 0 | 2 | 1 |
| 29 | `workspaces` | 6 | 1 | 0 | 1 | 0 | 3 | 1 |
| | **合计（29 表）** | **261** | **67** | **63** | **38** | **6** | **76** | 全部为 1 |

参考库同口径摘要与上表**逐格相等**（脚本内已断言，不一致会直接抛异常）。

## 3. 表名清单（迁移建出，升序，共 28 张）

```
action_followups, actions, activities, activity_bindings, analysis_results, artifacts, audit, candidates, cases, evidence, exports, idempotency, import_files, imports, jobs, object_evidence, preflight_rows, preflights, receipts, report_actions, reports, rule_versions, run_cases, runs, snapshots, source_mappings, thresholds, workspaces
```

与参考 DDL 的 `CREATE TABLE` 名集合逐一相等；迁移库额外只有 `alembic_version`（白名单内）。

### 6 个显式索引

| 索引名 | 归一化 CREATE INDEX |
|---|---|
| `actions_due` | `CREATE INDEX actions_due ON actions(workspace_id,state,due_on)` |
| `analysis_snapshot` | `CREATE INDEX analysis_snapshot ON analysis_results(workspace_id,snapshot_id,kind)` |
| `cases_one_confirmed_child` | `CREATE UNIQUE INDEX cases_one_confirmed_child ON cases(workspace_id,parent_case_id) WHERE parent_case_id IS NOT NULL AND state='CONFIRMED'` |
| `jobs_ready` | `CREATE INDEX jobs_ready ON jobs(state,created_at,workspace_id,id)` |
| `rules_activity` | `CREATE INDEX rules_activity ON rule_versions(workspace_id,activity_id,created_at)` |
| `snapshots_lookup` | `CREATE INDEX snapshots_lookup ON snapshots(workspace_id,bank_id,created_at)` |

> 设计档 §3 写「5 个显式索引」，漏计了部分唯一索引 `cases_one_confirmed_child`；以活契约 `contracts/sqlite-v1.sql` 为准（手册第 7 节），实测为 **6** 个。

## 4. PRAGMA 结果

| PRAGMA | 迁移库实测 | 参考库实测 | 判定 |
|---|---|---|---|
| `integrity_check` | `[('ok',)]` | `[('ok',)]` | PASS |
| `foreign_key_check` | `[]`（0 行） | `[]`（0 行） | PASS |
| `foreign_keys` | `(1,)` | `(1,)` | 必须为 1，否则下面的负例全是假绿 |
| `pragma_problems(迁移库)` | `[]` | — | 空即通过 |

连接级 PRAGMA 由 `migrations/env.py` 在建连接时设置：`foreign_keys=ON`、`busy_timeout=5000`、`journal_mode=DELETE`（OPERATIONS.md 口径）。`PRAGMA foreign_keys` 在事务内是 no-op，故**不能**写在迁移脚本里。

## 5. 跨工作区外键负例与 CHECK / STRICT 负例（实跑）

全部在**迁移库**上执行，且执行前已断言 `PRAGMA foreign_keys = 1`。

| # | 场景 | 实测结果 | 判定 |
|---|---|---|---|
| 1 | ① evidence 引用**别的工作区**的制品：evidence(workspace_id='WS-B', artifact_id='ART-A1'∈WS-A) | `IntegrityError: FOREIGN KEY constraint failed` | PASS（被拒绝） |
| 2 | ② audit 引用不存在的 workspace：audit(workspace_id='WS-MISSING') | `IntegrityError: FOREIGN KEY constraint failed` | PASS（被拒绝） |
| 3 | ③ artifacts 引用不存在的 workspace：artifacts(workspace_id='WS-MISSING') | `IntegrityError: FOREIGN KEY constraint failed` | PASS（被拒绝） |
| 4 | ④ CHECK 枚举：workspaces.source_class='X' | `IntegrityError: CHECK constraint failed: source_class IN ('SYNTHETIC','AUTHORIZED_DEIDENTIFIED')` | PASS（被拒绝） |
| 5 | ⑤ 跨列 CHECK：source_class='AUTHORIZED_DEIDENTIFIED' 且 authorization_note='' | `IntegrityError: CHECK constraint failed: source_class='SYNTHETIC' OR length(coalesce(authorization_note,''))>0` | PASS（被拒绝） |
| 6 | ⑥ 跨列 CHECK：source_class='AUTHORIZED_DEIDENTIFIED' 且 authorization_note IS NULL | `IntegrityError: CHECK constraint failed: source_class='SYNTHETIC' OR length(coalesce(authorization_note,''))>0` | PASS（被拒绝） |
| 7 | ⑦ STRICT 类型：workspaces.revision='not-an-int'（INTEGER 列塞字符串） | `IntegrityError: cannot store TEXT value in INTEGER column workspaces.revision` | PASS（被拒绝） |

### 正例（分母断言：只测「被拒」不测「能过」等于没测）

| 场景 | 落库行数 | 判定 |
|---|---|---|
| 正例 A：evidence(workspace_id='WS-A', artifact_id='ART-A1'∈WS-A) 同工作区引用 | 1 | PASS |
| 正例 B：audit(workspace_id='WS-A') 合法工作区 | 1 | PASS |
| 正例 C：source_class='SYNTHETIC' 且 authorization_note IS NULL | 1 | PASS |
| 正例 D：source_class='AUTHORIZED_DEIDENTIFIED' 且 authorization_note 非空 | 1 | PASS |

同一组负例／正例在 `tests/integration/bootstrap/test_migration_equivalence.py` 中对**参考库与迁移库同时**执行，两边行为必须一致。

## 6. 可逆性（downgrade）

命令序列（同一数据目录，全部 rc=0，详见 `commands.md`）：

```
alembic -c migrations/alembic.ini upgrade head    # 28 表 + 6 索引
alembic -c migrations/alembic.ini current         # 0001_initial_schema (head)
alembic -c migrations/alembic.ini downgrade base  # 逆序 DROP INDEX x6 + DROP TABLE x28
alembic -c migrations/alembic.ini upgrade head    # 重建
```

`downgrade base` 后：业务表 0 张，只剩 `alembic_version`（空表，alembic 的正常行为）；再次 `upgrade head` 后 `compare_schema()` 仍返回 `[]`。由 `test_downgrade_is_reversible` 断言。

## 7. 环境

| 组件 | 版本 |
|---|---|
| os | `Ubuntu 24.04.2 LTS` |
| kernel | `Linux 6.18.58.1-microsoft-standard-WSL2 x86_64 GNU/Linux` |
| cpython | `3.14.10 3.14.10` |
| sqlite | `3.53.1` |
| uv | `uv 0.13.7 (x86_64-unknown-linux-gnu)` |
| alembic | `alembic 1.20.1` |
| sqlalchemy | `2.0.57` |
| ruff | `ruff 0.17.4` |
| mypy | `mypy 2.4.1 (compiled: yes)` |
| pytest | `pytest 9.2.0` |

