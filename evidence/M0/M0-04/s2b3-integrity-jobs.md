# M0-04 / S2b-3 证据 · design §5:52 判据④⑤（jobs 侧）落地

- lane：**Y**（R14，档位 qwen3.8-max / reasoning high）；任务 M0-04/S2b-3，critical=true，slack=0
- 基线：branch `m0-framework` · HEAD `a05ef28`（`a05ef28a0ef2…`）。S2b-2 已由 `70be045` 入库；本轮 HEAD 是编排器
  predispatch 提交，只动 `orchestrator/handoff/R14-lane-A1-M2-01-S2a.md` 与 `state.json`，与本棒 write_set 不相交。
- 对账口径：**HEAD 树 + 本棒 write_set 的增量**（numstat 见 §1）。
- 生成方式：本文件**所有**数字与清单由 `.orch_scratch/y4_facts.py` / `y4_facts2.py` 实测注入
  （`inspect` / `ast` / `git` / `pytest --collect-only` / `ruff --select I --diff`），**无手抄、无写死符号面计数**。
- 裁决声明：本文件**不**给 AC-031 的 PASS/FAIL —— 该判定归 M5-01（design §7）。

## 1. 交付件与行数账（`git diff --numstat HEAD` 实取）

| 文件 | add | del | bytes | lines | sha256[:12] | HEAD sha256[:12] |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `src/campaignlab/worker/integrity.py` | 172 | 31 | 21824 | 412 | `3f04ddd2466c` | `2434f4e42fa7` |
| `src/campaignlab/infra/db/repositories.py` | 22 | 0 | 47226 | 1054 | `33590e99c580` | `a817a8bb8959` |
| `tests/unit/test_worker_integrity.py` | 392 | 13 | 42866 | 975 | `101ecbdc7b3b` | `1cef72d3092d` |
| `orchestrator/handoff/M0-04-design.md` | 38 | 0 | 60021 | 208 | `f72df55ec32a` | `57d2ceb1e9ae` |

**A204 硬指标**：`repositories.py` = **22 add / 0 del**（要求 N add / **0 del**）→ 满足。

### 1.1 硬禁面 / 不许碰面自证（`git show HEAD:<f>` 与工作树**逐字节**比对）

| 文件 | HEAD sha256[:12] | 工作树 sha256[:12] | byte_identical | 归属 |
| --- | --- | --- | --- | --- |
| `src/campaignlab/worker/deps.py` | `1f2be9761afe` | `1f2be9761afe` | **True** | A206（:135 不动）/ A207（:55 ignore 本棒禁删） |
| `src/campaignlab/cli.py` | `d34fe6962c95` | `d34fe6962c95` | **True** | A208（serve 接线归 S4，本棒禁碰 cli.py） |
| `scripts/doctor.sh` | `185f0805fb04` | `185f0805fb04` | **True** | 硬禁：`scripts/**`（doctor 部署期可见性属 FU-30） |
| `pyproject.toml` | `4b4eb3223b0e` | `4b4eb3223b0e` | **True** | 硬禁：构建配置不在本棒 write_set |

### 1.2 `git status --porcelain`（实测原文）

```
M orchestrator/handoff/M0-04-design.md
 M src/campaignlab/infra/db/repositories.py
 M src/campaignlab/worker/integrity.py
 M tests/unit/test_worker_integrity.py
?? evidence/M0/M0-04/positive-control-s2b3.log
```

4 条 `M` = 本棒 write_set；1 条 `??` = 本棒正向对照原始日志（编排器入库）。**无 IN_FLIGHT_CONTAMINATION 之外的多余文件**（本轮开工时无其他 lane 在飞残留）。

## 2. 符号面（`inspect` / `ast` 实取，禁写死）

### 2.1 `worker/integrity.py::__all__`

- HEAD（S2b-2 入库态）= **11** 项；工作树 = **17** 项。
- 新增 6 项（**纯追加**）：`POINTER_RESULT_JSON`, `POINTER_RESULT_JSON_OBJECT`, `POINTER_RESULT_REF_ID`, `POINTER_RESULT_REF_KIND`, `POINTER_RESULT_REF_SHAPE`, `RESULT_REF_KIND`
- 删除 **0** 项：[]

### 2.2 `Discrepancy`（A205 冻结面）

- 字段数 = **8**（A205 要求 8 字段逐字不变），`frozen=True`
- 字段序 = `workspace_id`, `artifact_id`, `relative_path`, `expected_sha256`, `actual_sha256`, `reason`, `expected_byte_size`, `actual_byte_size`
- 前 5 元组（design §5:52 的可定位元组）= `workspace_id`, `artifact_id`, `relative_path`, `expected_sha256`, `actual_sha256` —— 逐字未变

### 2.3 reason 常量集合（A205：禁新增第三个 reason）

- 工作树 reason 常量 = **7** 项：`BYTE_SIZE_MISMATCH`, `MISSING_FILE`, `PATH_ESCAPE`, `RESULT_JSON_UNPARSEABLE`, `RESULT_REF_DANGLING`, `SHA256_MISMATCH`, `UNREADABLE`
- HEAD 的 `__all__` 已含同名 7 项（S2b-2 只**声明**未**产出**），故本棒 reason 集合
  **0 增 0 删** —— ④ 的三个失败子形态**共用** `RESULT_JSON_UNPARSEABLE`，⑤ 用既有
  `RESULT_REF_DANGLING`，未引入第三个 reason。

### 2.4 ④ 子形态指针与 ref kind（新增的 6 个 `Final` 常量）

- `POINTER_RESULT_JSON` = `'jobs.result_json'`
- `POINTER_RESULT_JSON_OBJECT` = `'jobs.result_json:object'`
- `POINTER_RESULT_REF_ID` = `'jobs.result_ref.id'`
- `POINTER_RESULT_REF_KIND` = `'jobs.result_ref.kind'`
- `POINTER_RESULT_REF_SHAPE` = `'jobs.result_ref:shape'`
- `RESULT_REF_KIND` = `'job'`

- 实测值：`RESULT_REF_KIND` = `'job'`（A155① 冻结的 `ObjectRef(kind="job", id=<job_id>)`）

### 2.5 冻结签名（`inspect.signature` 实取）

- `verify_artifact_index(conn: 'Connection', data_dir: 'Path') -> 'list[Discrepancy]'`
- `manifest_rows(conn: 'Connection') -> 'list[ManifestRow]'`
- `ManifestRow` 字段（7）= `workspace_id`, `artifact_id`, `kind`, `sha256`, `relative_path`, `byte_size`, `created_at`

### 2.6 `JobRepository` 方法面（A204：只准纯追加）

- 工作树公有方法 **15** 个：
  - `cancel_expired_requested(self, conn: 'Connection', *, now: 'str') -> 'int'`
  - `claim_next(self, conn: 'Connection', *, workspace_id: 'str', lease_token: 'str', lease_deadline: 'str', stage: 'str') -> 'JobRecord \| None'`
  - `confirm_cancel(self, conn: 'Connection', *, workspace_id: 'str', job_id: 'str', attempt: 'int', lease_token: 'str') -> 'int'`
  - `count_pending(self, conn: 'Connection', *, workspace_id: 'str', states: 'tuple[str, ...]') -> 'int'`
  - `enqueue_retry(self, conn: 'Connection', *, workspace_id: 'str', source_job_id: 'str', source_revision: 'int', new_job: 'JobRecord') -> 'int'`
  - `fail_expired_running(self, conn: 'Connection', *, now: 'str', problem_json: 'str') -> 'int'`
  - `get(self, conn: 'Connection', *, workspace_id: 'str', job_id: 'str') -> 'JobRecord \| None'`
  - `insert(self, conn: 'Connection', *, job: 'JobRecord') -> 'None'`
  - `list_for_workspace(self, conn: 'Connection', workspace_id: 'str') -> 'list[JobRecord]'`
  - `list_ready(self, conn: 'Connection', *, limit: 'int') -> 'list[JobRecord]'`
  - `mark_failed(self, conn: 'Connection', *, workspace_id: 'str', job_id: 'str', attempt: 'int', lease_token: 'str', problem_json: 'str', retryable: 'bool') -> 'int'`
  - `mark_succeeded(self, conn: 'Connection', *, workspace_id: 'str', job_id: 'str', attempt: 'int', lease_token: 'str', result_json: 'str') -> 'int'`
  - `renew(self, conn: 'Connection', *, workspace_id: 'str', job_id: 'str', attempt: 'int', lease_token: 'str', lease_deadline: 'str', stage: 'str', progress: 'int') -> 'JobRecord \| None'`
  - `request_cancel(self, conn: 'Connection', *, workspace_id: 'str', job_id: 'str', revision: 'int') -> 'int'`
  - `touch_lease(self, conn: 'Connection', *, job_id: 'str', lease_token: 'str', lease_deadline: 'str') -> 'int'`

- 新增仅 `list_for_workspace`；A82 冻结的 4 方法（`insert` / `get` / `list_ready` /
  `touch_lease`）签名逐字未变（由 `tests/unit/test_job_repository_terminal.py::FROZEN_JOB_REPOSITORY_SIGNATURES` 钉住，本轮该套件 rc=0）。
- 体例对齐自证：`ArtifactRepository.list_for_workspace(self, conn: 'Connection', workspace_id: 'str') -> 'list[ArtifactRecord]'` vs
  `JobRepository.list_for_workspace(self, conn: 'Connection', workspace_id: 'str') -> 'list[JobRecord]'` —— 同为 `(self, conn, workspace_id)` 位置参数、同返回 `list[Record]`、同只读。

## 3. A204 逐条自证

1. **纯追加**：numstat = 22 add / **0 del**。
2. **复用既有行→记录转换**：AST 实测 `JobRepository.list_for_workspace`（第 455 行）体内
   Name 集合含 `_job_of` = **True**，含 `job_from_row` = **False**；
   全文件 `def _job_of(` = **1** 处、`def job_from_row(` = **1** 处 ⇒ 未新写第二个转换器。
3. **禁 `list_all` 全表无界枚举**：全文件 `def list_all` 命中 = **False**。
4. **枚举口径复用 integrity 既有形状**：`integrity.py` 非 docstring 字符串常量里的 SQL 动词
   命中 = **0** 条（AST 实取，清单 []）；
   模块 import 面 = `__future__`, `campaignlab.api.common`, `campaignlab.infra.artifacts`, `campaignlab.infra.db.repositories`, `collections.abc`, `dataclasses`, `json`, `pathlib`, `pydantic`, `sqlalchemy`, `typing`
   ⇒ 取数只走 `campaignlab.infra.db.repositories`，无任何直连 SQL 通道。
5. **可复现序**：`ORDER BY created_at, id`（与制品侧同口径，禁依赖 SQL 自然返回序）。
6. **A153 反向边仍为 0**：`tests/unit/test_layering_edges.py` rc=0，8 passed in 0.06s。

## 4. A205 逐条自证（判据④⑤）

- **④**：`json.loads` 失败（语法错）／结果不是 `Mapping`（不是对象）／`ObjectRef.model_validate`
  抛 `ValidationError`（形状或 `kind` 非 `job`）—— 三子形态**共用** `RESULT_JSON_UNPARSEABLE`，
  由 `POINTER_RESULT_JSON` / `POINTER_RESULT_JSON_OBJECT` / `POINTER_RESULT_REF_SHAPE` /
  `POINTER_RESULT_REF_KIND` 区分（承载位见 §9 U-2）。
- **⑤**：`ObjectRef(kind="job", id=<job_id>)` 的 `id` 指向的 `jobs` 行**在同工作区内存在**；
  不存在 → `RESULT_REF_DANGLING`（`POINTER_RESULT_REF_ID`）。
- **只核 `result_json IS NOT NULL` 的行**（DDL 双条件 CHECK `(state='SUCCEEDED')=(result_json IS NOT NULL)`）。
- **形状判据复用写入侧同一个模型** `api.common.ObjectRef`（`extra="forbid"` + Literal `kind`
  + `RESOURCE_ID_PATTERN`），不自写第二份形状校验；比 `repositories.job_from_row` 的构造式严一处
  （`model_validate` 会抓 `ObjectRef` 里多出的键，构造式会静默忽略）。
- **否决候选 b**（核制品表）已写进 `_check_job` docstring：`ArtifactRecord` 无 job 关联列、
  `relative_path_for(kind, workspace_id, sha256)` 不内嵌 job id ⇒ 只能退化成工作区级弱判据，
  对无制品作业会假红。
- **模块 docstring 的清单已同步**（`verify_artifact_index` docstring 现列 5 项判据；S2b-2 的 `.. warning::`「jobs 侧未落地」占位块按派单文 §3 删除）。

## 5. A157 复核（S2b-2 结论本棒未回退）

- `integrity.py` 是否 import `hashlib` = **False**；
  模块内定义的含 `hash` 的函数 = **0** 个 [] ⇒ **无第二份哈希实现**。
- 唯一哈希来源（AST 实取）：["from campaignlab.infra.artifacts import ['hash_file']"]
- 守护 `test_integrity_module_has_no_second_hash_implementation` / `test_hashing_goes_through_infra_hash_file` 均在绿：本文件 rc=0。

## 6. A206 / A207 / A208 / A209 逐条自证

- **A206**：`deps.py` 与 HEAD `byte_identical=True` ⇒ 第 135 行
  `factory(store=…)` **未动**。实测第 135 行原文：`    return cast("JobService", factory(store=get_job_store(config)))`
- **A207**：`# type: ignore[import-not-found]` 全文件 **2** 处，
  第 55 行仍在（本棒**禁删**，由 S2c 建 `service.py` 的同批删除）。实测第 55 行原文：
  `    from campaignlab.worker.service import JobService  # type: ignore[import-not-found]`
- **A208**：`cli.py` 与 HEAD `byte_identical=True` ⇒ **未碰**（serve 接线归 S4）。
- **A209**：提供器形态未改 —— `Depends(` **7** 处、`# noqa: B008` **3** 处、`Annotated` **1** 处（均为既有，本棒零改动，故不可能改成 `Annotated` 形态）。

## 7. D-011：design 第 52 行未改

- 第 1–52 行 HEAD 与工作树**逐行相同** = **True**；第 52 行单独比对 = **True**。
- design numstat = 38 add / **0 del**；行数 169 → 208（追加节位于**文末**）。
- 第 52 行原文（HEAD 版，逐字抄录，前 200 字）：

```
- AC-031 写入侧前提：`worker/integrity.py::verify_artifact_index(conn, data_dir) -> list[Discrepancy]`（逐行核 `artifacts.relative_path` 存在性、sha256、byte_size，及 `jobs.result_json` 可解析且指向存在的制品；缺件返回 `(workspace_id …
```

## 8. 用例数与守护

- `pytest --collect-only -q tests/unit/test_worker_integrity.py` 实测：HEAD **19** → 工作树 **30**（要求 ≥24 → 满足）；原始输出 `30 tests collected in 0.25s`。
- AST 顶层 `test_*` 函数：18 → 29；差额恒为 1，来自两版都有的 `test_new_worker_modules_contain_no_sql_text x2`。
- 名称账（AST 实取）：保留 **17** / 新增 **12** / 移除 **1**。移除项 = `test_jobs_side_reasons_are_declared_but_not_yet_produced`
  （见 §9 偏离报告 + 回执 U-1；用例**总数**只增不减）。
- 新增的 12 条：
  - `test_jobs_side_reasons_are_declared_and_now_produced`
  - `test_verify_artifact_index_is_empty_when_a_succeeded_job_self_ref_is_consistent`
  - `test_verify_artifact_index_reports_result_json_unparseable_on_invalid_json`
  - `test_verify_artifact_index_reports_result_json_unparseable_when_payload_is_not_an_object`
  - `test_verify_artifact_index_reports_result_json_unparseable_on_objectref_shape_violation`
  - `test_verify_artifact_index_reports_result_json_unparseable_when_ref_kind_is_not_job`
  - `test_verify_artifact_index_reports_result_ref_dangling`
  - `test_result_ref_dangling_is_scoped_to_the_same_workspace`
  - `test_jobs_with_null_result_json_are_skipped`
  - `test_jobs_side_discrepancy_slots_follow_the_documented_convention`
  - `test_job_enumeration_delegates_to_repositories`
  - `test_job_repository_list_for_workspace_is_workspace_scoped_and_ordered`

### 8.1 静态自检（AST，非工具裁决写死）

- `except (A, B):` 元组（R12-1 静默损坏）命中：`src/campaignlab/worker/integrity.py`=0, `src/campaignlab/infra/db/repositories.py`=0, `tests/unit/test_worker_integrity.py`=0, `src/campaignlab/worker/deps.py`=0 ⇒ 全 0。
- 行宽：`integrity.py`=99、`repositories.py`=100、`tests/unit/test_worker_integrity.py`=100（上限 100）。
- CR 字符：三文件均 `has_cr=False`；UTF-8 无 BOM（`ruff format --check` rc=0）。
- import 序：`ruff check --select I --diff` rc=0，输出 `(empty output)`（空 = 无建议）。

### 8.2 正向对照（≥5 条，原始输出见 `positive-control-s2b3.log`）

| # | 变异 | 目标 | 变异后 rc | 红点数 | 复原 sha256 双向核验 |
| --- | --- | --- | ---: | ---: | --- |
| PC-1 | 摘掉判据④ 的 JSON 语法错分支（`except ValueError` → `return []`） | `integrity.py` | 1 | 1 failed, 92 passed in 31.97s | True（5f7684c9b221 → 3f04ddd2466c） |
| PC-2 | 摘掉判据⑤ 的悬空分支（`ref.id not in job_ids` → `return []`） | `integrity.py` | 1 | 4 failed, 89 passed in 26.56s | True（65fcb3646f3f → 3f04ddd2466c） |
| PC-3 | A204 追加面丢掉工作区限定（`list_for_workspace` 去掉 `WHERE workspace_id`） | `repositories.py` | 1 | 8 failed, 85 passed in 27.15s | True（c6b7752a8049 → 33590e99c580） |
| PC-4 | `_check_job` 整体空转（首行 `return []`，④⑤ 全失语） | `integrity.py` | 1 | 7 failed, 86 passed in 28.32s | True（89ce88cac7fc → 3f04ddd2466c） |
| PC-5 | 往 `integrity.py` 塞只读 `SELECT` 字面量（验 A204 未开后门） | `integrity.py` | 1 | 2 failed, 91 passed in 27.27s | True（90e9524575ac → 3f04ddd2466c） |

- PC-5 追加单跑冻结守护 `test_job_repository_terminal.py::test_worker_package_contains_no_table_dml_literals`
  → **rc=1**（日志原文 `==> frozen-guard rc=1`，`1 failed in 0.30s`）⇒ 证明 A204 的
  append-only 豁免**没有**被用来给 `worker/**` 开 SQL 后门；复原后同一守护 rc=0（见 §10 表末行 `frozen guard single (post-restore)`）。
- 5 条变异中 **5 条** `mutated rc≠0`（逐条 rc 见上表，全部由日志解析而来，非写死）；
  **5 条**的「变异态 sha256 ≠ 复原态 sha256 且复原态 == 快照」双向核验为 `True`，
  复原后 `ALL_RESTORED_IDENTICAL=True`；基线 `93 passed in 28.04s`（rc=0），终验 `93 passed in 27.51s`（rc=0）。
- 数据注入类探针一律走 `tmp_path`（用例内建），**未落工作树**；变异类探针为「原地改 + 字节级复原 + sha256 双向核验」，日志 `[E]`/`[F]` 段证明复原后 `git status` 与 numstat 与变异前逐字一致。

## 9. 偏离报告（**只报不裁**，裁定见回执 §5 U 项）

1. **翻转 1 条既有 tripwire 用例**：`test_jobs_side_reasons_are_declared_but_not_yet_produced`
   → `test_jobs_side_reasons_are_declared_and_now_produced`，断言取反。派单文 §3 自相矛盾：
   既要求删掉 `integrity.py` 的 `.. warning::` 占位块，又要求「禁删改既有 19 条用例」，而该
   用例的断言正是「warning 文本存在 + 两个 reason 常量在模块内只出现一次（= 未被产出）」，
   两者不可能同时成立。该用例 docstring 自述是「jobs 侧落地即触发」的设计性绊线。
   用例**总数只增不减**（19 → 30）。
2. **`detail` 的承载位**：A205 要求「同一 reason，detail 区分」，但 `Discrepancy` 8 字段已冻结
   且**无 detail 槽**。本棒把子形态指针放在 `relative_path` 字段（语义 = 「被核对象在哪」），
   取值即 `POINTER_*`。候选：(a) 用 `relative_path` 承载（本棒所选，零字段变更）；
   (b) 给 `Discrepancy` 加 `detail` 字段（破坏 8 字段冻结与前 5 元组）。倾向 (a)。
3. **`__all__` 增 6 项**（5 个 `POINTER_*` + `RESULT_REF_KIND`），纯追加、0 删除。
   A205 的「只扩 reason 两项」按「**reason 集合不增第三项**」理解并满足（§2.3 实测 0 增 0 删）；
   `POINTER_*` 不是 reason，是 detail 指针常量。若编排器认为 `__all__` 也应冻结在 11 项，
   候选：(a) 保留导出（调用方/守护需要引用常量而非字面量）；(b) 改为模块私有 `_POINTER_*`。
   倾向 (a)。

## 10. 门禁 rc 汇总（**实测**，非「应该通过」）

| 命令 | rc | 关键输出 |
| --- | ---: | --- |
| `ruff format --check (3 py + design md)` | 0 | 4 files already formatted |
| `ruff check (3 py)` | 0 | All checks passed! |
| `ruff check --select I --diff (3 py)` | 0 | (empty output) |
| `mypy (full table)` | 0 | Success: no issues found in 86 source files |
| `pytest -q (dispatch-scoped 4 suites)` | 0 | 93 passed in 28.86s |
| `pytest -q tests/unit/test_worker_integrity.py` | 0 | 30 passed in 10.08s |
| `pytest -q tests/unit/test_job_repository_terminal.py` | 0 | 24 passed in 6.29s |
| `pytest -q tests/unit/test_layering_edges.py` | 0 | 8 passed in 0.06s |
| `pytest -q tests/integration/jobs/test_worker_deps.py` | 0 | 18 passed in 5.65s |
| `pytest --collect-only -q tests/unit/test_worker_integrity.py` | 0 | 30 tests collected in 0.25s |
| `ruff format --check evidence/M0/M0-04` | 0 | 8 files already formatted |
| `frozen guard single (post-restore)` | 0 | 1 passed in 0.29s |

- `mypy` 实测输出 = `Success: no issues found in 86 source files`；分母 **86** 个 source files 的归因：
  HEAD `a05ef28` 树 tracked `.py` 实测 = **104** 个，本棒新增 `.py` = **0** 个（`git status` 的 `??` 中 `.py` 计数），
  故分母与 S2b-2 复验同值（R13-6：分母只报实测值 + 归因，不当判据）。
- 所有 pytest 一律**路径限定**；全表由编排器在冻结索引树上复跑（R13-6：绝对数字不作判据）。

