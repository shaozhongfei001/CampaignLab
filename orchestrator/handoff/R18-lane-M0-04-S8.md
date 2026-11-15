# R18 · lane **S8** · task **M0-04** · 派单文（编排器立法面；本件一经 predispatch 入库即冻结）

> **档位**：`qwen3.8-flash` / reasoning `medium` / 预算 **9k**（任务卡档位表原文冻结）
> **loop 上限**：**2 轮**（用满即停并如实报，禁硬撑第 3 轮）
> **critical=true / slack=0**：M0-04/S8 是 **wave-3 的唯一解锁点**（其后 21 个 TODO 任务依赖它）
> **性质**：**纯取证棒**。design §9 原文：「**S8 禁改任何代码或测试**」⇒ 写权面**只有** md/log/json 取证件。

---

## §0 开工基线（**一律以本键为准，禁自行写死分母**）

- **HEAD**：`f105061`（tag `R18-backfill-S6sha`）　**分支**：`m0-framework`
- **counts 权威值**（台账 `resume.self_check_gates_rc0.counts`）：
  `ruff_formatted_files=316`、`mypy_source_files=112`、`pytest_passed=748`、`in_scope_py=114`、`in_scope_md=202`
- **若你测得 311/110/738（112 py + 199 md）说明 checkout 到了 `928676d` 之前** ⇒ 立即回报，禁继续。
- 解释器口径：**一律** `uv run --no-sync <cmd>`（Python 3.14）。系统 `python3`（3.12.3）**禁用**于任何探针
  （R14-1 / PRE-21：会对 PEP 758 假报 SyntaxError）。
- **本棒不新增任何 py 文件** ⇒ counts 的 py/mypy/pytest 三项**必须不变**；只有 `in_scope_md` 会因你新增的
  md 取证件而增长（`.log` / `.json` **不在** `RUFF_SUFFIXES=(".py",".md")` ⇒ 不入分母，但仍须入库）。

---

## §1 写权面（**闭集**；越界即回报编排器，手册 6.4，禁自行扩大）

**只允许新建**下列路径（父目录 `evidence/M0/M0-04/` 已存在；`gates/`、`http/` 两个子目录由你新建）：

1. `evidence/M0/M0-04/commands-s8.md`　← **注意：不是 `commands.md`**，见 §2 的裁定 A253
2. `evidence/M0/M0-04/ac.md`
3. `evidence/M0/M0-04/job-states.md`
4. `evidence/M0/M0-04/gates/V1.log` … `gates/V9.log`（**9 件**）
5. `evidence/M0/M0-04/http/` 下 **11 件** `.json`：
   `listJobs.json`、`getJob.json`、`cancelJob-200.json`、`cancelJob-409.json`、`cancelJob-412.json`、
   `cancelJob-428.json`、`retryJob-202.json`、`retryJob-429.json`、`problem-404.json`、
   `problem-422.json`、`problem-500.json`
6. `evidence/M0/summaries/M0-04.md`（**≤30 行**，硬约束）

**硬禁**（触碰即判越界、拒收）：
- 禁改**任何** `src/**`、`tests/**`、`scripts/**`、`contracts/**`、`spec/**`、`web/**`、`orchestrator/**`
  （含 `orchestrator/state.json` —— 台账由**编排器独占写**，D-011 / A144(c)）。
- 禁改 `evidence/M0/M0-04/` 下**任何既有件**（`commands.md`、`commands-s2b1.md`、`commands-s2b2.md`、
  `commands-s2b3.md`、`commands-s2c.md`、`commands-s4.md`、`commands-s7.md`、`s2b1-hash-file.md`、
  `s2b2-integrity-deps.md`、`s2b3-integrity-jobs.md`、`s2c-worker-service.md`、`s3-artifacts.md`、
  `s4-jobs-router.md`、`s7-job-dto.md`、`positive-control-*.log`）。**只新建，禁修改**。
- 禁建 `evidence/M2/**`（归 M2-01/S7）、禁建 `evidence/M0/summaries/` 下除 `M0-04.md` 外的任何件。
- 禁 `git add` / `git commit` / `git push` / `git checkout` / `git reset` / `git stash` / `git clean`
  （入库由编排器执行；你只把文件写在磁盘上）。

---

## §2 编排器裁定（**A253**）：design §9 的 `commands.md` 落点冲突

**冲突事实**（编排器实测）：design §9 第 91 行要求 S8 产出 `commands.md`（V1–V9 逐条），
但 `evidence/M0/M0-04/commands.md` **已存在**（12575 B，2026-11-14 02:26），其首行标题为
「**M0-04 / S3 原子制品写入 · 命令台账**」⇒ 该件属 **S3** 的证据面，S8 **无权改写**（§1 硬禁）。

**裁定**：S8 的 V1–V9 命令台账落在 **`commands-s8.md`**。
**依据**：① 同目录既有先例一律按子任务后缀命名（实测存在 `commands-s2b1.md`、`commands-s2b2.md`、
`commands-s2b3.md`、`commands-s2c.md`、`commands-s4.md`、`commands-s7.md`）⇒ `commands-s8.md` 与先例同型；
② D-011 append-only：禁改写已入库件；③ 一任务一提交 + A144(c) 写集归属要求写集互不相交。
**design §9 原文不改写**（D-011），该冲突由本裁定解决并在台账留痕。

---

## §3 交付面规格（design §9 第 91 行**逐字**要求，禁自行增删）

- **`commands-s8.md`**：V1–V9 **逐条**记录「**命令 · rc · 时间戳 · 环境行**」四元组
  （门禁记账四元组口径同既有 `commands*.md`）。命令必须与 §4 **逐字相同**（PRE-29）。
- **`ac.md`**：
  - **AC-029** → 给「**判定 ＋ 依据 ＋ 证据指针**」。判定只允许基于 §5 的实测事实；
    证据指针写**仓库相对路径**（可指向 `http/*.json`、`gates/V*.log`、`job-states.md`、既有 `test_*` 用例名）。
  - **AC-031** → **只写**「**写入侧前提已交付 ＋ 判定归 M5-01**」，
    **禁写 AC-031 的 PASS/FAIL 结论**（design §7 原文与任务卡 U-2 口径；`primary_owner = M5-01`）。
- **`job-states.md`**：**T1–T9** × 「迁移前 / 迁移后」的 `jobs` 行快照 ＋ 触发该迁移的 **HTTP 样本**。
  T1–T9 的权威定义是 `src/campaignlab/worker/states.py::TRANSITIONS`（`TransitionId` 实测为
  `Literal['T1'..'T9']`）⇒ **逐条以实测为准**，禁凭记忆填表。
- **`gates/V1.log` … `gates/V9.log`**：V1–V9 的**原始输出**逐字落盘（可含 stderr；禁裁剪成「只留绿」）。
- **`http/*.json`**：11 件，按 §1 的**逐字文件名**。内容必须是**真实响应体**（禁手写编造），
  且 `Problem` 形状须与契约一致（见 §6 实测事实）。
- **`evidence/M0/summaries/M0-04.md`**：**≤30 行**（硬约束）。体例参考同目录既有 `M0-01.md`（18 行）、
  `M0-02.md`（38 行 —— 注意它**超**了 30 行，**不要照抄它的长度**，本棒以 ≤30 行为准）。

---

## §4 判据（回收时编排器**逐条独立复验**，禁采信你的自报）

**命令逐字取自 design §8（`orchestrator/handoff/M0-04-design.md`，sha256[:12]=`acb2629ca10d`）第 74–82 行**
（PRE-29：回收侧复核命令与本表**逐字同源**；你的 `commands-s8.md` 也必须逐字照抄本表，禁改写、禁加前缀）：

| 判据 | 命令（逐字） | 期望 |
|---|---|---|
| **V1** | `uv run --no-sync python -c "import hashlib,pathlib;d=pathlib.Path('contracts/openapi.json').read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))"` | rc=0；输出须与台账 `counts.live_openapi_sha16` / `.live_openapi_bytes` **现值**一致（**禁与 design 写死值比对**，那是基准漂移） |
| **V2** | `uv run --no-sync pytest -q tests/integration/jobs -k state_machine` | rc=0；且 **T1–T9 每条 ≥1 例**（参数化 id 必须含 `T1`…`T9`） |
| **V3** | `uv run --no-sync pytest -q tests/integration/jobs -k lease` | rc=0（两执行者、失效 token、模拟中断→`JOB_INTERRUPTED`、取消／完成争用各 ≥1 例） |
| **V4** | `uv run --no-sync pytest -q tests/integration/jobs -k artifact` | rc=0（独立尝试目录、同盘原子重命名、提交失败复用同摘要、未引用回收各 ≥1 例） |
| **V5** | `uv run --no-sync pytest -q tests/unit/test_job_dto.py` | rc=0（`Job` 13 字段以活契约 schema 做 jsonschema 校验；断言 `lease_token`/`lease_until` **不在**响应体） |
| **V6** | `uv run --no-sync ruff check .` ／ `uv run --no-sync ruff format --check .` ／ `uv run --no-sync mypy` ／ `uv run --no-sync pytest -q` | 各 rc=0；分母以 counts **现值**为准（**禁写死**） |
| **V7** | `uv run --no-sync python scripts/check_contracts.py check --validate` | rc=0；登记项数以 `counts.contract_registered_nodes` 为准。**本卡不应改变该计数**；若变了立即回报 |
| **V8** | design §7 的 **①–⑤** 逐条命令 ＋ rc ＋ HTTP 样本落 `evidence/M0/M0-04/` | rc **全 0** |
| **V9** | `verify_artifact_index()` 在正常库上返回 `[]`；注入「删一个被引用制品」后返回可定位差异且切换守卫阻断 | rc=0；**判定归 M5-01，本卡不出结论** |

**⚠ PRE-29 口径提醒（本批新立，因 R18-8 而生）**：V2/V3/V4 是**目录关键字过滤**口径
（`tests/integration/jobs -k <词>`），其 collected **包含既有用例**，**不是**「本棒新增」。
你**只报实测 collected 数**即可，**禁**把它当作「新增数」推算任何增量；编排器回收时也按**逐字命令**复核。
既有实测参考（R18-landS6 批，供你交叉核对，**禁直接采信**）：`-k state_machine`=13、`-k lease`=14、
`-k artifact`=19、整目录=98、全量=748 passed / 0 failed。

---

## §5 AC-029 的实测事实面（design §7 原文**逐字**，你的 `ac.md` 判定只能基于这些）

**AC-029**（`spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md:37`，编排器已实测该行原文与 design 引用**逐字一致**）：
切片原文「重复提交、两个执行者争用、运行中断、取消和重试」→「同键同请求同对象，异请求 409。
失效租约不能提交。中断后可重试。取消/完成只有一个终态」，主证据：作业与 DB。

design §7 的 ①–⑤（**这就是 V8 要逐条取证的**）：
- **①** 同键同请求 → `idempotency` PK 命中 → 重放 `response_status`+`response_json`，DB 只 1 行、
  两次响应含头**逐字节相同**；异请求（`request_digest` 不同）→ **409 `IDEMPOTENCY_CONFLICT`**
- **②** 两执行者争用 → `BEGIN IMMEDIATE` ＋ T1 谓词 UPDATE，一方 `rowcount=1`、另一方 **`LeaseLost`**
- **③** 失效 lease token 提交 → TX5/TX2 的 `attempt=? AND lease_token=?` 不匹配 → `rowcount=0` 拒提交、
  原状态与 `revision` **不变**
- **④** 运行中断 → `FixedClock` 推过 `lease_until` → TX7 记 `FAILED` ＋ `issues[0].code='JOB_INTERRUPTED'`，
  T9 重试得到一次可见结果（`JOBS.md:30`）
- **⑤** 取消／完成争用 → 先 `COMMIT` 者定终态，终态重复查询**逐字节一致**
  （`JOBS.md:23,31`：取消排队 **T2**、运行中取消 **T4**、原子提交后取消 → **409 `STATE_CONFLICT`**，三者分别落测）

**AC-031**（`ACCEPTANCE.md:39`）：切片原文「停受理备份，恢复至新目录，运行迁移校核」→
「数据库和制品摘要一致。历史报告和原规则仍能回查。快照缺件可定位并阻止错误切换」，主证据：日志、SHA、数据库。
**cross_ref：`primary_owner = M5-01`** ⇒ 本卡只交付**写入侧前提**：`verify_artifact_index()` 返回 `[]`、
缺件时返回可定位差异并阻断切换、`manifest_rows()` 提供 SHA 清单来源、`verify_same_filesystem()`
保证原子重命名前提。**M0-04 不出 AC-031 判定**。

---

## §6 符号面（编排器 **AST 实取**，PRE-25/PRE-26；**枚举/计数类断言一律以此为准，禁凭记忆**）

- `src/campaignlab/api/common.py`：**1169 行 / 45605 B / sha256[:12]=`836e7b3e8d3a`**（冻结件，**禁改**）
  - `class Job`（**:338**）：`model_config = ConfigDict(extra='forbid')`，**恰 13 个**注解字段，逐字为
    `id, revision, created_at, kind, state, attempt, progress, stage, input_digest, retry_of,
    result_ref, problem, retryable`
    ⇒ **`lease_token` / `lease_until` 不在其中**（V5 要断言的正是这一点）
  - `JobState`（**:233**）＝ `Literal[...]` **恰 6 值**：`QUEUED, RUNNING, CANCEL_REQUESTED, SUCCEEDED,
    FAILED, CANCELLED`
  - `JobKind`（**:221**）＝ **恰 10 值**：`VALIDATE_IMPORT, PUBLISH_IMPORT, CORRECT_SNAPSHOT, COMPARE,
    REVIEW, DIAGNOSE, QUESTION, SIMULATE, REPORT, EXPORT`
  - `ObjectKind`（**:234**）＝ **恰 20 值**（含 `job`）
- `src/campaignlab/worker/states.py`（**8353 B / sha256[:12]=`aa60b26090e1`**）：
  **`JobState` / `JobKind` 在此文件是 re-export**（原文 `from campaignlab.api.common import JobKind, JobState`），
  **定义点在 `api/common.py`** ⇒ 引用时**两者皆可 import**，但**定义点归属**写 `api/common.py`（禁写反）。
  本文件自有：`JOB_STATES, JOB_KINDS, TERMINAL_STATES, STAGE_QUEUED, STAGE_CLAIMED,
  NON_RETRYABLE_PROBLEM_CODES, TransitionId, Transition, TRANSITIONS, is_terminal,
  assert_transition_allowed, retryable_for`；`TransitionId = Literal['T1'..'T9']`（**9 值**）。
- `src/campaignlab/worker/integrity.py`（**21824 B / `3f04ddd2466c`**）：`Discrepancy, ManifestRow,
  verify_artifact_index, manifest_rows` **全部实测存在**（V9 用）。
- `src/campaignlab/infra/artifacts.py`（**36033 B / `14515bc840da`**）：`ArtifactWriter`
  （含方法 `verify_same_filesystem, begin, commit`）、`sweep_unreferenced`、`relative_path_for`、
  `SweepReport`、`CommittedArtifact`、`AttemptStage` **全部实测存在**。
- `src/campaignlab/worker/store.py`（**34328 B / `c9e9416dfb05`**）：`JobStore` 及方法
  `get_job, list_jobs, claim_next, renew, request_cancel, confirm_cancel, succeed, fail,
  reap_expired, enqueue, retry, pending_count` **全部实测存在**。
- `src/campaignlab/worker/service.py`（**12924 B / `7b0dd1591fd5`**）：`JobService` 及
  `list_jobs, get_job, cancel_job, retry_job` **全部实测存在**。
- `src/campaignlab/api/jobs.py`（**16916 B / `735d30baf0c4`**）：`router, list_jobs, get_job,
  cancel_job, retry_job` **全部实测存在**。
- `tests/unit/test_job_dto.py` **已存在**（12679 B），其 import 面为
  `from campaignlab.api.common import Issue, Job, JobKind, JobState, ObjectKind, ObjectRef, Problem`
  ⇒ V5 的既有断言面**禁改**（S7 已交付）。

---

## §7 纪律与红线（违反即拒收）

1. **禁写死分母/计数**：一切计数指向 `state.json → resume.self_check_gates_rc0.counts` 现值
   （D-012 / D-014）。`ac.md` / `commands-s8.md` 里的分母写「台账现值」或**实测输出原文**，禁抄本派单文的数字。
2. **禁发明**：AC 编号只引 spec 原文（D-011）；错误码只用已注册 code
   （`domain/errors.py::PROBLEM_CODES`，实测 20 项）；禁自造 `Problem.code`。
3. **禁系统时间**：任何需要推进时间的取证一律用注入的 `FixedClock` / `advance_clock`
   （`tests/integration/jobs/conftest.py`），**禁 `sleep`、禁 `time.monotonic` 判定**。
4. **禁前向占位（PRE-28）**：取证件里指向**后续棒**的落点**只写职责归属、不写路径字面量**。
   具体到本棒：`ac.md` 写 AC-031 时**只写**「判定归 **M5-01**」这一职责归属，
   **禁**写出 M5 阶段的证据目录裸路径（该目录此刻**尚不存在** ⇒ 悬空引用门会判红）。
   同理，指向 wave-3 及之后任何落点时，一律写「归 <任务号> 负责」而非路径。
   注意：`evidence/M0/M0-04/ac.md` 与 `evidence/M0/summaries/M0-04.md` 是**你本棒要建的**，
   它们已在台账 `forward_reference_registry` 登记、由你**本棒闭合**，故可在文中互相引用。
5. **禁粉饰**：任何一条 V 判红、任何一处实测与期望不符 ⇒ **如实报 U**（`U_ITEMS`）并给出候选处置，
   **禁为过测改期望、禁裁剪输出、禁只留绿**。护栏与计数一律如实。
6. **HTTP 样本真实性**：`http/*.json` 必须是**实跑得到**的响应体（可用既有测试夹具/`TestClient` 采集），
   **禁手写编造**。若某个状态码在现有面上**无法真实触发**，**报 U**，禁伪造。
7. **台账只读**：你可以**读** `orchestrator/state.json` 取 counts 现值，**禁写**。

---

## §8 回执格式（**必须逐字用这些字段名**；编排器会逐字留档，禁省略）

```text
RESULT: DONE | DONE_WITH_GAP | BLOCKED
LOOP_USED: <n>/2
FILES_NEW: <逐件：路径 · 行数 · 字节 · sha256[:12]>
FILES_MODIFIED: 应为**空**（本棒禁改既有件）；若非空必须逐件说明并报 U
V1..V9: <逐条：命令原文 · rc · 关键输出末行>
SUMMARY_LINES: <evidence/M0/summaries/M0-04.md 的实测行数，必须 ≤30>
AC029_VERDICT: <PASS | FAIL | 附依据与证据指针>
AC031_STATEMENT: <必须是「写入侧前提已交付＋判定归 M5-01」形态，禁 PASS/FAIL>
U_ITEMS: <逐条：现象 · 命令原文 · 实测事实 · 候选处置 · 你的倾向；无则写「无」>
SELF_REPORTED_DEVIATIONS: <逐条；无则写「无」>
TOKEN_USAGE: <**必填**：实际用量或区间；若确实无法获知，必须逐字写「未报」并说明成因
             —— 编排器如实登记：连续两棒（S3/S6）未报 token 已使护栏② 不可判定，故本棒强制要求该字段>
TIER_CONFIRM: model=<实际模型>, reasoning=<实际 reasoning>
```

**遇设计外问题必须回报，不得自行决定**（手册 6.4）。你的 loop 上限是 **2 轮**：
第 1 轮落地 + 自验，第 2 轮修正 + 复验；若第 2 轮仍未绿 ⇒ 如实报 `DONE_WITH_GAP` 或 `BLOCKED`，禁硬撑。
