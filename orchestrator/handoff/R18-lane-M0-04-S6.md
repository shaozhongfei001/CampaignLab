# R18 · lane M0-04/S6 派单文 —— `tests/integration/jobs/` 的租约争用与制品索引完整性

> **上工第一件事**：按 §5 逐条复测冻结面读数并与本文对账。若不符，**先查** `orchestrator/state.json`
> 的 `resume.baseline_authoritative.current`（A223 / PRE-10：编排器在你在飞期间的自办入库会在同一提交内更新该键），
> 对账口径＝**派单快照 ＋ 该键 history 的累计增量**；不符**不要直接判失真、也不要停手空转**，按 §9 报 U。

## §0 身份、档位与预算

| 项 | 值 |
|---|---|
| 任务 / 子任务 | **M0-04**（持久作业、认领续租、取消重试与原子制品）/ **S6**（租约与制品争用用例枚举） |
| 轮次 / lane | Round 18 / lane **S6** |
| 档位 | **`qwen3.8-flash`** · reasoning **medium**（design §9-S6 冻结为 flash 12k；**A243 只重切范围，未升降档**） |
| loop | 上限 **2** 轮（`tasks["M0-04"]` 实测 critical=true、slack=0，手册 15.6 第 1 条）；超限即停手写 U 项，禁硬撑 |
| 派单基线 | **含本派单文的那个提交**（tag `R18-predispatch`，其 parent = `1c591b4`）。上工时自取 sha：`git log --oneline -1 -- orchestrator/handoff/R18-lane-M0-04-S6.md`（**禁写猜测值**）· 分支 `m0-framework` · counts 基线 **305 / 107 / 734**（in-scope **109 py + 196 md**）。305 与 196 已计入本批入库的 **+3 in-scope md**（两份 R18 派单文 ＋ `orchestrator/defects/D-050.md`）；除此之外交付面与 `1c591b4` **逐字节相同**（该提交是纯台账提交） |
| 并行邻居 | lane **S3**（M2-01：新建 `src/campaignlab/api/activities.py` ＋ `src/campaignlab/api/app.py` ≤3 行 ＋ 新建 `tests/api/activities/**`）—— 写集与你**零交叉**；它的文件对你而言是 **IN_FLIGHT_CONTAMINATION**：**禁改、禁 add、禁 checkout、禁 clean / reset / stash**（PRE-11 / A161：复验方与邻居对在飞面禁写） |

## §1 写权面（**只新建 2 件**；越界即按 §9 报 U，禁自行扩大）

```
tests/integration/jobs/test_lease.py      （新建 · 6 个函数，名字逐字见 §3）
tests/integration/jobs/test_artifact.py   （新建 · **1** 个函数，见 §3 与 A243）
```

design §9-S6 的**原文**（`orchestrator/handoff/M0-04-design.md:89`，逐字，禁改写）：

> **S6**（`qwen3.8-flash`，12k，`tests/integration/jobs/**`，**只新建**）：`test_lease.py:test_two_claimers_only_one_wins,
> test_expired_lease_token_commit_rejected,test_interrupted_job_marked_job_interrupted,test_cancel_vs_complete_first_commit_wins,
> test_renew_extends_lease_by_30s,test_terminal_state_is_immutable` · `test_artifact.py:test_stage_dir_isolated_per_attempt,
> test_atomic_rename_same_filesystem,test_commit_failure_reuses_same_digest_file,test_unreferenced_artifact_swept,
> test_referenced_artifact_never_swept,test_verify_artifact_index_detects_missing_file`。全部用 `FixedClock`/`advance_clock`，
> **禁 `sleep`、禁 `time.monotonic` 判定**。

**A243 重切（本棒范围以本段为准，不以 design §9-S6 的 12 名字面为准）**：编排器派单前实测（命令原文见 §5）发现
`test_artifact.py` 的 6 个名字里有 **5 个**已被**同目录同层**的既有 `tests/integration/jobs/test_artifact_write.py`（13 例）
完整覆盖，第 6 个（`test_verify_artifact_index_detects_missing_file`）在集成层是**真缺口**。故：

- `test_lease.py`：**6 个名字全部落地**（逐名的「既有覆盖 vs 本棒必须断言的残差」见 §3，禁写重复断言）。
- `test_artifact.py`：**只落地 `test_verify_artifact_index_detects_missing_file` 1 例**；其余 5 名依 A243 判重豁免
  （映射表见 §3.B），**禁写重复用例**（禁 duplicate），也**禁静默跳过**——必须在回执的 §3.B 映射表里逐名给出
  既有覆盖的 `file::test_id`，若你的实测与该表不符，按 §9 报 U。

读取面（PRE-19：限定路径 ＋ 带输出上限 ＋ 排除散文面；**禁**无界 `grep -rn` / `rg` 全仓）：

```
sed -n '1,120p' tests/integration/jobs/conftest.py
sed -n '85,200p' tests/integration/jobs/test_state_machine.py
sed -n '240,300p' tests/integration/jobs/test_state_machine.py
sed -n '342,383p' tests/integration/jobs/test_state_machine.py
grep -n -e 'def ' -e '__all__' src/campaignlab/worker/store.py | head -60
grep -n -e 'def ' -e '__all__' src/campaignlab/worker/integrity.py | head -40
grep -n -e 'def ' -e 'SECONDS' src/campaignlab/worker/leases.py | head -30
grep -n 'class FixedClock' -A 24 src/campaignlab/clock.py | head -40
grep -n -e 'def test_artifact' tests/integration/jobs/test_artifact_write.py | head -20
```

## §2 硬禁面（**逐条**，含 PRE-14 要求的「预期红清单」）

1. **禁改任何 `src/**`**（含 `worker/**`、`infra/**`、`api/**`、`application/**`、`domain/**`）。S6 是**纯测试棒**。
   若发现 src 侧缺陷 ⇒ 按 §9 报 U，**禁就地修**、**禁为过测改测试期望**（卡片「禁止」行原文）。
2. **禁改既有测试件**（sha 见 §5，回收时逐件对撞）：`tests/integration/jobs/{__init__.py,conftest.py,test_artifact_write.py,
   test_worker_deps.py,test_jobs_router_s4.py,test_state_machine.py,test_idempotency.py,test_jobs_api.py}`、
   `tests/unit/**`、`tests/api/**`。
3. **禁改** `contracts/**`、`spec/**`、`scripts/**`、`orchestrator/**`、`web/**`、`migrations/**`、`evidence/**`
   （取证件归 S8）、`pyproject.toml`、`uv.lock`、`README.md`。
4. **禁碰 `src/campaignlab/api/app.py`**（`tasks["M0-04"].s6_obligations_R17.hard_ban` 原文；它同时是并行邻居 lane S3 的写集）。
5. **禁碰 `orchestrator/state.json`**（T lane / 编排器独占写）。
6. **禁新建 `tests/integration/jobs/__init__.py`**（已存在，108 B）；**禁给 conftest.py 增删 fixture**（9 名已冻结，
   由 `tests/unit/test_jobs_conftest_no_autouse.py` 机器看守：`len(names)==9` 且与 `FROZEN_FIXTURES` 双向差集为空，
   多一个红、少一个红、出现 `autouse=True` 也红）。
7. 不执行 `git commit / push / add / reset`；不 `sudo`；无浏览器不得谎称 E2E 通过。

### 2.1 预期红清单（PRE-14：**本棒落地后不会打红任何既有哨兵**，此结论已由编排器派单前实测）

实测依据（命令原文见 §5）：全仓**无任何**以「`tests/integration/jobs` 的用例数 / 文件数」为判据的哨兵
（`grep` 命中面只有路径字符串引用，无计数断言）；`test_jobs_conftest_no_autouse.py` 只看守 conftest 的 fixture 名集与
autouse，不看用例数；`test_job_repository_terminal.py::test_lease_computation_exists_only_inside_compute_lease_deadline`
的扫描面是 `application/worker.py` + `infra/db/repositories.py` + `worker/**`（**不含 `tests/**`**）。
⇒ **本棒的预期红清单为空集**。若你落地后实测到任何既有用例变红，**那是真信号**：禁改判据、禁改既有用例，
按 §9 报 U 并附红的原文（编排器会判断是否属 A243 未预见的立法面失真）。
## §3 逐名 delta 表（**编排器派单前实测**，PRE-20；你的实测若与此表不符 ⇒ 按 §9 报 U，禁自行改判）

### 3.A `test_lease.py` 的 6 名（全部落地；每例只断言「残差」列，禁重复既有断言）

| # | 函数名（逐字） | 既有覆盖（实测 file::test / 行号） | **本棒必须断言的残差** |
|---|---|---|---|
| 1 | `test_two_claimers_only_one_wins` | **仅单元层** `tests/unit/test_job_repository_terminal.py:361`；集成层 `-k lease` 现选中的 5 例（T3×2/T4/T5/T7）**无一**涉及双认领 | 在 `migrated_job_db` 上只留一条 QUEUED，两个认领者先后 `claim_next` ⇒ **恰一个** `claimed is True`；另一个 `claimed is False` 且 DB 侧该行 `state=='RUNNING'`、`attempt==1`、只有一个 lease_token。若 `Claim.contended`（实测字段存在）在你构造的串行争用下恒为 `False`，**如实报 U 并说明语义**，禁为过测改期望 |
| 2 | `test_expired_lease_token_commit_rejected` | 集成层 T5 尾部（`test_state_machine.py:290-293`）只覆盖「**终态后**同租约再 `succeed` → `LeaseLost`」；T3 反路只覆盖「`attempt=99` 陈旧身份 `renew` → `renewed is False`」。单元层 `tests/unit/test_worker_runner.py:440` 是 runner 级 | **过期**（非终态）路径：`claim_next` → `advance_clock(31)`（> `LEASE_TTL_SECONDS`）→ `pytest.raises(LeaseLost)` 于 `succeed(...)`；并断言 DB 侧该行**仍为 `RUNNING`**、`lease_until` 未被改写；再以 token/attempt 不匹配的 `Lease` 调 `fail(...)` 同样 `LeaseLost` |
| 3 | `test_interrupted_job_marked_job_interrupted` | **集成层已覆盖大部分**：T7（`test_state_machine.py:342-383`）已断言 `FAILED` / `reaped.interrupted==1` / `reaped.cancelled==0` / `lease_until` 清空 / `problem["code"]=="INTERNAL_ERROR"` / `problem["issues"][0]["code"]=="JOB_INTERRUPTED"` | **窄残差**（T7 未断言的字段，A88④ 的完整 Problem 形状）：`problem["status"]==500`、`problem["issues"][0]["retryable"] is True`、且 `problem["code"] != "JOB_INTERRUPTED"`（N7③：`JOB_INTERRUPTED` 禁提升为 `Problem.code`）。**禁**重复断言 T7 已钉的 6 项；在 docstring 里注明「状态与 code/issues[0].code 由 T7 覆盖，本例只补形状残差」 |
| 4 | `test_cancel_vs_complete_first_commit_wins` | **仅单元层** `tests/unit/test_worker_runner.py:712 test_cancel_then_complete_first_committer_wins`；集成层 T4 只到 `CANCEL_REQUESTED`、T8 只做 executor confirm / expiry reap，**无争用** | 集成层双向：(a) `request_cancel` 后执行者 `succeed` ⇒ 断言**先提交者定终态**（按 store 的真实守卫 `state IN ('RUNNING','CANCEL_REQUESTED')` 断言实际终态，并把 `revision` 的递增值与审计行数一并钉住）；(b) `succeed` 之后 `confirm_cancel` ⇒ 断言终态**不变**、第二次写被拒（`LeaseLost` 或 `rowcount==0`，以实测为准）。两向的真实语义若与卡片「取消/完成只有一个终态」表述有出入，**报 U**，禁自行发明 |
| 5 | `test_renew_extends_lease_by_30s` | T3 正路（`test_state_machine.py:178-187`）只断言 `after[3] > before[3]` 与 `not is_expired(...)`，**未断言延长量** | **窄残差**：断言新 `lease_until` **恰等于** `now + LEASE_TTL_SECONDS`（`from campaignlab.worker.leases import LEASE_TTL_SECONDS`）。**禁写字面量 `30`**（`worker/leases.py:37` 注释原文「禁在此另写 30」；D-012 / D-014 禁写死）。函数名里的 `30s` 只是规格值（实测 `application/worker.py:47 WORKER_LEASE_SECONDS: Final = 30`，`LEASE_TTL_SECONDS` 是其 re-export） |
| 6 | `test_terminal_state_is_immutable` | **仅单元层**全矩阵 `tests/unit/test_job_repository_terminal.py:524 test_terminal_state_rejects_every_further_transition`；集成层只有 T5 那一条路径（SUCCEEDED 后再 `succeed`） | 集成层用 **JobStore ＋ 真实迁移后的 DB** 重做终态不可逆矩阵：对 `SUCCEEDED` / `FAILED` / `CANCELLED` 三个终态，逐条验证 `renew` / `succeed` / `fail` / `request_cancel` / `confirm_cancel` 全部被拒，且行快照（`state`/`attempt`/`revision`/`lease_until`/`problem_json`/`result_json`）**逐字段不变**。**禁**跨层 import 单元测试的私有 helper（conftest 禁改；需要 helper 就在本文件内自建私有函数） |

### 3.B `test_artifact.py`：A243 判重豁免映射表（**5 名禁写**，回执里逐名照抄本表并附你的复核结论）

| design §9-S6 名 | 既有覆盖（同目录同层，实测 `-k artifact` 选中 18 例） | 裁定 |
|---|---|---|
| `test_stage_dir_isolated_per_attempt` | `test_artifact_write.py::test_artifact_attempt_dirs_are_isolated_per_attempt` | 判重豁免 |
| `test_atomic_rename_same_filesystem` | `…::test_artifact_final_path_stays_invisible_until_the_atomic_rename` ＋ `…::test_artifact_commit_reports_exdev_as_red_instead_of_copying` ＋ `…::test_artifact_cross_device_layout_is_rejected_at_startup_and_at_commit` | 判重豁免 |
| `test_commit_failure_reuses_same_digest_file` | `…::test_artifact_retry_after_failed_commit_reuses_the_same_digest_file` ＋ `…::test_artifact_same_content_yields_stable_digest_and_reuses_row` | 判重豁免 |
| `test_unreferenced_artifact_swept` | `…::test_artifact_sweep_removes_unreferenced_and_keeps_referenced` ＋ `…::test_artifact_rollback_after_rename_is_reclaimable_by_sweep` | 判重豁免 |
| `test_referenced_artifact_never_swept` | `…::test_artifact_sweep_removes_unreferenced_and_keeps_referenced`（keeps referenced 分支）＋ `…::test_artifact_sweep_never_touches_in_flight_attempt_dirs` ＋ `…::test_artifact_sweep_ignores_every_other_data_subdir` | 判重豁免 |
| **`test_verify_artifact_index_detects_missing_file`** | `verify_artifact_index` 在 `tests/**` 的命中**全部**在 `tests/unit/test_worker_integrity.py`（36 处）；**集成层 0 命中** | **本棒落地（真 delta）** |

`test_verify_artifact_index_detects_missing_file` 的要求（design §8 V9 的写入侧前提，AC-031 归 M5-01 判定，本棒**只交付写入侧**）：
在 `data_dir` + `migrated_job_db` 上经**真实写入路径**产生一个被索引引用的制品（走 T5 那条 `claim → handler → succeed` 链，
或直接 `ArtifactWriter.begin/commit`），先断言健康库上 `verify_artifact_index(...) == []`；再把该制品文件删除或改名，
断言返回的差异**可定位**且 `reason` 取 `worker/integrity.py` 的注册常量（实测 `MISSING_FILE` 在 `__all__` 17 名内），
并断言差异里带的标识足以定位到该制品（`ManifestRow` 的字段以实测为准）。**禁**把 `reason` 写成自造字符串。

## §4 判据（回收时编排器**逐条独立复验**，禁采信你的自报）

| 判据 | 命令（逐字） | 期望 |
|---|---|---|
| V1 租约门 | `uv run --no-sync pytest -q tests/integration/jobs -k lease` | rc=0；collected **≥11**（现值 **5** ＋ 你新增 **6**；若你参数化则更多，须在回执报出实数） |
| V2 制品门 | `uv run --no-sync pytest -q tests/integration/jobs -k artifact` | rc=0；collected **≥19**（现值 **18** ＋ 新增 **1**） |
| V3 目录面 | `uv run --no-sync pytest -q tests/integration/jobs` | rc=0；collected **≥95**（现值 **88** ＋ 新增 **7**） |
| V4 状态机门未回归 | `uv run --no-sync pytest -q tests/integration/jobs -k state_machine` | rc=0；collected **13**（现值，禁变） |
| V5 全量 | `uv run --no-sync pytest -q` | rc=0；passed **≥741**（现值 734 ＋ 新增 7；口径＝冻结树实跑 ＋ GIT_ENV_IGNORES 静态 21） |
| V6 质量门 | `uv run --no-sync ruff check .` / `ruff format --check .` / `mypy` | 各 rc=0（计数不写死，权威现值见 `state.json -> resume.self_check_gates_rc0.counts`） |
| V7 冻结面 | `git diff --numstat HEAD -- tests/integration/jobs tests/unit tests/api src` | **输出为空**（你只新建 2 件；任何既有件被改即判红） |
| V8 红线（**只扫你新建的 2 件**） | `grep -n -e 'time.sleep' -e 'monotonic' -e 'datetime.now' -e 'utcnow' tests/integration/jobs/test_lease.py tests/integration/jobs/test_artifact.py` | **0 命中**（design §9-S6 原文禁令；D-049③ 教训：**扫描面只限你的新文件**，且注释/docstring 里若必须提到这些词，用字符串拼接自指形态如 `"datetime" + ".now("`，避免自匹配假红） |
| V9 禁写死 | `grep -n -e '30' tests/integration/jobs/test_lease.py` | 命中处**不得**是 TTL 断言里的字面量（必须 import `LEASE_TTL_SECONDS`）；`advance_clock(31)` 这类「推过租约」的入参允许，但须在注释里写明它 > `LEASE_TTL_SECONDS` |
| V10 时钟面 | AST/grep 实取 | 6+1 例全部经 `fixed_clock` / `advance_clock` 驱动时间；**0** 处系统当前时间 |

## §5 冻结面读数（PRE-15：**全部由编排器脚本实测**，命令原文一并给出；`.orch_tmp/r18_frozen_readings.py`）

保护件（sha256[:12]，回收时逐件对撞，**任一变动即判红**）：

```
tests/integration/jobs/conftest.py             8509 B  90ba7b17b115
tests/integration/jobs/test_state_machine.py  18040 B  39e6c8423b1a
tests/integration/jobs/test_idempotency.py     5697 B  69a69d80abeb
tests/integration/jobs/test_jobs_api.py       11320 B  64a157a2f176
tests/integration/jobs/__init__.py              108 B  056664ce00b3
tests/integration/jobs/test_artifact_write.py 30646 B  ffce1792d82f
tests/integration/jobs/test_worker_deps.py    27316 B  69234fb4f35d
tests/integration/jobs/test_jobs_router_s4.py 26515 B  c3110b40b71d
tests/unit/test_jobs_conftest_no_autouse.py    4483 B  0f37d540f63a
```

复测命令（逐字，禁改用系统 `python3`——PRE-21：系统 3.12 在 PEP 758 语法上直接 SyntaxError）：

```
python3 -c "import hashlib,pathlib;[print(p, pathlib.Path(p).stat().st_size, hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:12]) for p in ['tests/integration/jobs/conftest.py','tests/integration/jobs/test_state_machine.py','tests/integration/jobs/test_idempotency.py','tests/integration/jobs/test_jobs_api.py','tests/integration/jobs/__init__.py','tests/integration/jobs/test_artifact_write.py','tests/integration/jobs/test_worker_deps.py','tests/integration/jobs/test_jobs_router_s4.py','tests/unit/test_jobs_conftest_no_autouse.py']]"
uv run --no-sync pytest --collect-only -q tests/integration/jobs | tail -2
uv run --no-sync pytest --collect-only -q tests/integration/jobs -k lease | tail -2
uv run --no-sync pytest --collect-only -q tests/integration/jobs -k artifact | tail -2
```

符号面（AST 实取，**枚举/计数类断言一律以此为准**，PRE-20）：

- `tests/integration/jobs/conftest.py` 的 fixture **恰 9 名**、autouse **0** 个：`data_dir, migrated_job_db, fixed_clock,
  advance_clock, job_store, stub_handler, registry_with_stub, idem_key, http_client`。
  `advance_clock` 在 `conftest.py:101`，类型 `Callable[[int], datetime]`（传入秒数、返回推进后的 `datetime`）。
- `src/campaignlab/clock.py:51 class FixedClock`（`now()` @63、`advance(delta)` @68）。
- `worker/store.py::__all__` **14 名**；`JobStore` 的方法 **13 个公开 ＋ `__init__`**：`get_job, pending_count, claim_next,
  renew, request_cancel, confirm_cancel, succeed, fail, reap_expired, enqueue, retry, fail_unhandled, list_jobs`。
  `Claim` 字段 `record / lease / contended`（+property `claimed`）；`RenewResult` 字段 `renewed / record`（+property
  `cancel_requested`）；`Reaped` 字段 `interrupted / cancelled`（+property `total`）。
- `worker/leases.py::__all__` **6 名**：`LEASE_TTL_SECONDS, RENEW_INTERVAL_SECONDS, Lease, deadline_after, is_expired,
  new_lease_token`。`LEASE_TTL_SECONDS` = re-export `application/worker.py::WORKER_LEASE_SECONDS`（实测 `Final = 30`，
  `worker.py:47`）；`RENEW_INTERVAL_SECONDS: Final = 5`。
- `worker/errors.py::__all__` **7 名**：`JOB_INTERRUPTED, NO_HANDLER, ArtifactCommitFailed, LeaseLost,
  interrupted_problem, no_handler_problem, problem_of`。
- `infra/artifacts.py::__all__` **12 名**：`ARTIFACT_ID_PREFIX, ARTIFACT_KIND_JOB_RESULT, TMP_STALE_SECONDS, ArtifactWriter,
  AttemptStage, CommittedArtifact, SweepReport, hash_file, relative_path_for, results_root, stage_root, sweep_unreferenced`。
- `worker/integrity.py::__all__` **17 名**：`BYTE_SIZE_MISMATCH, MISSING_FILE, PATH_ESCAPE, POINTER_RESULT_JSON,
  POINTER_RESULT_JSON_OBJECT, POINTER_RESULT_REF_ID, POINTER_RESULT_REF_KIND, POINTER_RESULT_REF_SHAPE,
  RESULT_JSON_UNPARSEABLE, RESULT_REF_DANGLING, RESULT_REF_KIND, SHA256_MISMATCH, UNREADABLE, Discrepancy, ManifestRow,
  manifest_rows, verify_artifact_index`。
## §6 纪律（红线，违反即判红）

1. **禁 `sleep` 固定时长代替可控时钟**；**禁 `time.monotonic` 参与判定**；**禁系统当前时间做领域计算**（卡片「禁止」行原文）。
2. **禁为过测改测试期望**；**禁改既有用例/哨兵**（§2.1：本棒预期红为空集，红即真信号 ⇒ 报 U）。
3. **禁发明 code / reason / kind 常量**：`Problem.code` 只用 `domain/errors.py` 注册表内的码；`Discrepancy.reason` 只用
   `worker/integrity.py::__all__` 里的注册常量；`result_ref.kind` 用 `"job"`、`artifacts.kind` 用 `ARTIFACT_KIND_JOB_RESULT`
   （N8 / A89 既有裁定）。
4. **禁写死**计数、指纹、TTL 字面量（D-012 / D-014）：TTL 一律 import `LEASE_TTL_SECONDS`。
5. 时区 `Asia/Shanghai`、金额分整数、比率十进制字符串（卡片原文）；本棒不涉及金额/比率，若断言时间戳一律用
   `fixed_clock` 的 aware `datetime`，**禁** naive datetime 与 `utcnow`。
6. mypy strict 必须过：新文件的类型注解齐全（fixture 参数用实测类型，如 `job_store: JobStore`、
   `migrated_job_db: tuple[Path, Engine]`、`advance_clock: Callable[[int], datetime]`；`advance_clock` 若声明为 `object`
   则必须像 T3 那样先 `assert callable(advance_clock)` 再调用）。
7. ruff：`__all__` 不需要（测试模块）；禁 `# noqa` 之外的规则豁免，禁改 `pyproject.toml`。
8. **禁** `git commit / push / add / reset / checkout / clean / stash`（编排器一任务一提交）。
9. 体例照 `test_state_machine.py`：模块 docstring 写明本文件对应的 gate 与 A243 重切依据；每例 docstring 写明
   「既有覆盖 vs 本例残差」（对应 §3 的表），使下一棒不必再猜。

## §7 阳性对照（PRE-18 / PRE-20③：**先证变异生效，再证判据有牙**）

规则（逐字遵守）：① 每条 PC 先用 **AST / 运行期实取**断言「变异确已生效」（「文件 sha 变了」不构成证明）；
② 变异点必须是**语义合法位置**（禁追加到 `return` 之后或模块尾部导致 import 期崩溃 ⇒ 假阳性取证，A238）；
③ 跑判据、记录 rc 与红的原文；④ **字节级复原到落地态**（不是复原到派单基线；PRE-15 追加注记），复原后 sha 必须
与你落地时的 sha 逐字相同，并把两次 sha 都写进回执；⑤ 判红预言一律写成「**若不红则如实入档并补替代对照**」，
**禁**写成「必然判红」（PRE-20③）。

| PC | 变异点（只动你新建的文件） | 判据 | 预言 |
|---|---|---|---|
| PC-1 | `test_expired_lease_token_commit_rejected` 里把 `advance_clock(31)` 改成 `advance_clock(0)` | `uv run --no-sync pytest -q tests/integration/jobs/test_lease.py -k expired_lease_token` | 期望 rc≠0（`LeaseLost` 不再触发）；**若不红则如实入档并补替代对照**（例如改断言 `record.state`） |
| PC-2 | `test_renew_extends_lease_by_30s` 里把「恰等于 `now + LEASE_TTL_SECONDS`」的等值断言改成 `>=` | 同上（`-k renew_extends`） | 变异后**仍绿** ⇒ 证明等值断言比 `>=` 强；随后再做主体变异：把传给 `renew` 的 `now` 换成 `fixed_clock.now()`（不推进），期望 rc≠0 |
| PC-3 | `test_verify_artifact_index_detects_missing_file` 里去掉「删除/改名制品文件」那一步 | `uv run --no-sync pytest -q tests/integration/jobs/test_artifact.py` | 期望 rc≠0（差异集为空使断言失败）；**若不红则如实入档并补替代对照** |
| PC-4 | `test_terminal_state_is_immutable` 里把某一个非法迁移调用整段删掉（选一个**语义合法**的位置） | `uv run --no-sync pytest -q tests/integration/jobs/test_lease.py -k terminal_state` | 期望 rc≠0 或 collected 数下降（证明矩阵非空转）；**若不红则如实入档**——「删断言」永远不构成判据有牙的证明，必须补主体变异 |

## §8 取证落点

S6 **只产出代码**；`evidence/M0/M0-04/**` 与 `evidence/M0/summaries/M0-04.md` 归 **S8**（禁在本棒新建 evidence 文件，
否则会与前向引用登记面冲突）。本棒只需在回执里给出**可复现命令 ＋ rc ＋ collected 实数**（§4 的 V1–V10 全部），
编排器会独立复跑并把这些数字作为 S8 取证的输入。

## §9 U 项协议（只报不裁；编排器逐条终裁）

遇到下列情形**立即停手该条、写 U 项**，禁自行决定（手册 6.4：flash 只在 max 设计划定的文件与函数内工作）：

- 你实测的既有覆盖面与 §3 的表**不符**（例如某个「真 delta」其实已被覆盖，或某个「判重豁免」其实有残差）；
- `JobStore` / `verify_artifact_index` 的真实语义使 §3 要求的断言**不可满足**（例如串行调用下争用不可构造）；
- 任何既有哨兵/用例因你的产物变红（§2.1 预期红为空集 ⇒ 红即真信号）；
- 需要改 `src/**`、`conftest.py` 或任何既有测试件才能过测；
- 需要新增 fixture 才能表达某条断言（conftest 的 9 名已冻结）。

U 项格式：`U-<n>｜现象（含 file:line 与命令原文）｜你实测到的事实｜候选处置（≥2 个）｜你倾向哪个及理由`。
**禁**在 U 项里自行落地任何一种候选处置。

## §10 回执格式（最后一条消息，逐字用这些字段名）

```
RESULT: DONE | DONE_WITH_GAP | PARTIAL | BLOCKED
LOOP_USED: <n>/2
BASE_SHA: <你上工时的派单基线 sha，git log 自取>
FILES_NEW: <逐件：路径 行数 字节 sha256[:12]>
FILES_MODIFIED: <必须为空；非空即越界>
V1_lease: rc=<>, collected=<>
V2_artifact: rc=<>, collected=<>
V3_dir: rc=<>, collected=<>
V4_state_machine: rc=<>, collected=<>
V5_full: rc=<>, passed=<>
V6_quality: ruff_check rc=<>, ruff_format rc=<>, mypy rc=<>
V7_numstat_frozen: <git diff --numstat 输出，必须为空>
V8_redline_hits: <>
V9_ttl_literal_hits: <>
V10_clock_usage: <每例用的 fixture 名>
PROTECTED_SHA_AFTER: <§5 九件逐件 sha，必须与派单值全等>
PC_RESULTS: <PC-1..PC-4 逐条：变异点、AST/运行期生效证明、rc、红的原文、复原后 sha（须与落地态相同）>
COVERAGE_MAP_3B: <§3.B 五个判重豁免名的逐名复核结论（同意/不同意＋依据 file::test）>
U_ITEMS: <逐条按 §9 格式；无则写 NONE>
SELF_REPORTED_DEVIATIONS: <任何与本派单文不一致之处，宁报勿藏>
TIER_CONFIRM: model=qwen3.8-flash, reasoning=medium（若你被以其它档位启动，必须在此如实写明）
```
