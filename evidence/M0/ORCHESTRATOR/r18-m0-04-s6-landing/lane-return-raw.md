# lane S6（M0-04/S6）原始回执归档 —— 逐字留档（R18-6 的补齐动作 · FU-61 的人工纪律先行）

> **归档口径（如实登记，禁粉饰）**：本件是编排器**实际收到**的 lane 回执原文。Round 18 编排器**未在回收当刻落盘**
> 原始回执（违反 R12 / R13 的既有先例）⇒ 立自纠 **R18-6** ＋ **FU-61**（机器化 `archive_lane_return` ＋
> `run_commit` 顺序门）。本件由两段拼合：
>
> - **§1**＝lane **第 2 轮**回传的首次文本（编排器 `wait_agent` 收到），其中尾部遇传输截断 `…3125 tokens truncated…`；
> - **§2**＝编排器发出「只重发原文、禁任何文件操作与命令」窄请求后，lane 重发的 `U_ITEMS` /
>   `SELF_REPORTED_DEVIATIONS` / `COVERAGE_MAP_3B 尾段` / `residual` / `TIER_CONFIRM`。
>
> **不可复原部分（明示，禁凭记忆重构）**：
> ① §1 尾部被截断处（`COVERAGE_MAP_3B` 的 5 名逐条映射全文）—— §2 只重发了其**尾段 2 名**，其余 3 名**不可复原**；
> ② lane **第 1 轮**的回执全文（含当时的 `FILES_NEW` 读数 `006aa53d2694` 等）**未留档**，只在编排器上下文里存在过；
>    `close_agent(Lorentz)` 返回的 `previous_status.completed` 是**第 2 轮**的终态回执，**不含**第 1 轮原文 ⇒ 第 1 轮
>    原文确认不可复原；
> ③ lane **未报** token 用量（两段文本均无该字段，`close_agent` 带回的完整终态回执里同样没有，编排器已复核）
>    ⇒ 台账 `tokens=null`、`tokens_estimated=true`，**无自报区间可引**。
>
> 编排器对 lane 自报的一切**均不采信**：交付面读数（行 / 字节 / sha256 / rc / collected）全部由编排器独立实测，
> 见同目录 `00-index.md` 与 `commands-and-outputs.log`。**本批未抓到自报失真**：V1/V2 的 collected（14 / 19）
> 经编排器按派单文 §4 的**逐字命令**（`pytest -q tests/integration/jobs -k lease` / `-k artifact`，均为
> **目录关键字过滤**口径，非按文件口径）独立复跑，实测同为 **14 / 19**，逐字相符；编排器初稿曾误按
> 「单文件」口径判为失真，该误判已由本次实证推翻并**在归档件内如实更正**（详见 §3 与 §3bis），
> 不构成 lane 缺陷，故**不立** A252 / R18-8。

- **lane**：S6 · **task**：M0-04 · **round**：18
- **agent_id**：`01a1dff2-a13f-7531-91c9-1eeccf61a928` · **昵称**：Lorentz
- **档位**：`qwen3.8-flash` / `medium`（lane `TIER_CONFIRM` 与派单档位一致，未升降档 ⇒ `tier_match=true`）
- **派单文**：`orchestrator/handoff/R18-lane-M0-04-S6.md`（249 行 / 26367 B / sha256[:12]=`4f15d3614700`）
- **loop**：**2 / 2**（用满但未硬撑第 3 轮）· **critical=true、slack=0**

---

## §1 第 2 轮回传的首次文本（逐字；尾部含传输截断标记）

```text
第 2 轮全部完成：新例落地、PC-5 判红闭环、复原逐字节全等；唯一的全量红是我上工后由编排器自己放进工作树的 `orchestrator/defects/D-051.md`（未入台账）触发的账本哨兵，与本棒零因果，只报不裁。以下为完整回执。

---

**第 2 轮摘要**：仅改 `tests/integration/jobs/test_lease.py` 一件——落地 U-1 终裁版 `test_interrupted_job_marked_job_interrupted`（断言面改钉可满足真残差：`status==500`／`code != JOB_INTERRUPTED`（import 常量）／行级 `record.retryable is True`；禁写的 `issues[0]["retryable"]` 未写；T7 六项未重复断言）。V1 13→14、V3 97→98、V2/V4 不变；9 件保护面复核全等；`test_artifact.py` 未再触碰（字节与第 1 轮复验态相同）。

RESULT: DONE
LOOP_USED: 2/2
BASE_SHA: bc8a52d（git log --oneline -1 -- orchestrator/handoff/R18-lane-M0-04-S6.md 复测仍指 bc8a52d；HEAD 现为纯台账提交 c94eff9，numstat 实测只含 state.json 40/30，不触碰任何测试面）
FILES_NEW:
  tests/integration/jobs/test_lease.py  476 行  20778 B  sha256[:12]=112b149f1b12（第 2 轮落地态）
  tests/integration/jobs/test_artifact.py  113 行  4924 B  sha256[:12]=1d65896e618a（第 2 轮未改动，与复验态逐字节相同）
FILES_MODIFIED: （空——第 2 轮改动全部发生在新建件 test_lease.py 内；S3/编排器在飞件零触碰）

V1_lease: rc=0, collected=14（既有 5 ＋ 本棒净新增 9：6 函数、CVC×2、终态×3；较第 1 轮 +1）
V2_artifact: rc=0, collected=19（未变，与复验值全等）
V3_dir: rc=0, collected=98（97 + 新增 1）
V4_state_machine: rc=0, collected=13（未回归）
V5_full: rc=1, passed=747, failed=1 —— 唯一红＝ tests/unit/test_state_ledger.py::test_every_md_on_disk_has_ledger_entry，红原文「磁盘上有缺陷单但账本查不到（D-009 的形态：新实例按账本恢复会漏掉它们）：['D-051'] / assert ['D-051'] == []」；触发面是编排器自己新建的未跟踪件 orchestrator/defects/D-051.md（本棒无任何 md 产物，单独复跑该哨兵 rc=1 取证，因果链不含本棒 2 件）。与你「期望 0 failed」不符的差值如实报：D-051 入库前该红会一直存在，见 U-4
V6_quality: ruff_check rc=0, ruff_format rc=0, mypy rc=0（全仓快照，含 S3/编排器在飞件）
V7_numstat_frozen: 全部行如下（实测 3 行，均属 S3/编排器授权在飞面；**无任何一行属于 tests/integration/jobs/**；本棒 2 件为 untracked 新建故不入 numstat）：
  3	0	src/campaignlab/api/app.py
  10	3	tests/unit/test_s2b2_app_injection.py
  16	1	tests/unit/test_s3b_routes.py
V8_redline_hits: 0（grep -n -e 'time.sleep' -e 'monotonic' -e 'datetime.now' -e 'utcnow' 扫本棒 2 件，grep rc=1 即无命中）
V9_ttl_literal_hits: 2 —— L20（模块 docstring 指涉函数名）、L339（test_renew_extends_lease_by_30s 的 def 行，design 逐字规格名）；两处均非断言字面量。新增例未引入任何 '30'（推钟入参 31 处注释写明 31 > LEASE_TTL_SECONDS；500 为 Problem.status 规格值非 TTL）
V10_clock_usage:（AST 复取，7 函数 / 10 collected 全部 fixed_clock/advance_clock 驱动，0 处系统时间、0 处禁用读数）
  test_two_claimers_only_one_wins: fixed_clock
  test_expired_lease_token_commit_rejected: fixed_clock + advance_clock
  test_interrupted_job_marked_job_interrupted: fixed_clock + advance_clock（新增例）
  test_cancel_vs_complete_first_commit_wins(×2): fixed_clock
  test_renew_extends_lease_by_30s: fixed_clock + advance_clock
  test_terminal_state_is_immutable(×3): fixed_clock
  test_verify_artifact_index_detects_missing_file: fixed_clock（＋data_dir, registry_with_stub）
PROTECTED_SHA_AFTER:（9/9 与派单 §5 全等，第 2 轮落地后复测）
  90ba7b17b115 conftest.py ✓ / 39e6c8423b1a test_state_machine.py ✓ / 69a69d80abeb test_idempotency.py ✓ /
  64a157a2f176 test_jobs_api.py ✓ / 056664ce00b3 __init__.py ✓ / ffce1792d82f test_artifact_write.py ✓ /
  69234fb4f35d test_worker_deps.py ✓ / c3110b40b71d test_jobs_router_s4.py ✓ / 0f37d540f63a test_jobs_conftest_no_autouse.py ✓
PC_RESULTS:（第 1 轮四条全部维持，文件已含新增例，PC-1..PC-4 的变异/复原逻辑仅涉已复验字节面；本轮未重放旧 PC，如实说明：第 1 轮记录仍有效，PC-1/PC-2 涉及的 test_lease.py 字节面本轮已演进为新落地态 112b149f1b12，其原始取证 sha 对应的是上一落地态 006aa53d2694）
  PC-1: 变异 advance_clock(31)→(0)，AST 实取 literal=0；-k expired_lease_token rc=1「DID NOT RAISE LeaseLost」；复原 sha＝当时落地态 ✓
  PC-2: 2a ==→>=（AST op=GtE）rc=0 仍绿，按预言入档「等值强于 >=」；2b renew 不经推进（AST：函数内 advance_clock 调用数=0）rc=1「'2026-11-13T01:00:30+00:00' != 同值」；复原 ✓
  PC-3: 删 target.unlink()（AST unlink=0）rc=1「assert 0 == 1」；复原 sha=1d65896e618a ✓
  PC-4: 删矩阵 ("fail",...) 行（AST calls 元素 4→3、名字集不含 fail）-k terminal_state rc=1（3 failed）「Right contains 1 more item: {'fail': 'LeaseLost'}」；复原 ✓
PC5_RESULT: 变异点＝新增例中「assert record.retryable is True」→「is False」（建议形态）；AST 生效证明＝test_interrupted_job_marked_job_interrupted 内 Compare(left=Attribute retryable, op=Is, comparator=False) 实取；判据「uv run --no-sync pytest -q tests/integration/jobs/test_lease.py」rc=1；红原文「E assert True is False / E + where True = JobRecord(workspace_id='ws-s6-interrupted', id='j-int', ..., state='FAILED'...)」——红证同时反证真实行值 retryable=True；复原后 sha=112b149f1b12 与落地态逐字相同 ✓（无需替代对照：判据有牙已实证）
COVERAGE_MAP_3B:（5 名第 1 轮复核结论维持【同意】，本轮 test_artifact.py 零改…【传输截断 …3125 tokens truncated… 该 5 名的逐条映射全文不可复原，尾段 2 名见 §2】
```

---

## §2 lane 重发的尾段（逐字；编排器窄请求「只重发原文、禁任何文件操作与命令」）

```text
U_ITEMS:
  U-1（已按终裁落地关闭）：候选 (a) 四断言形态全部钉住，PC-5 有牙实证。
  U-2（按终裁维持关闭）：contended 两枚 False ＋ docstring 语义说明原样保留，未新增并发 fixture。
  U-3（按终裁关闭）：第 2 轮实测 E1/E2 迁移后两条 mount 哨兵已恢复通过（V5 中不再出现），V7 的 3 行全部为你所列授权行，本棒未触碰。
  U-4｜现象：V5 全量仍有 1 红，与你「期望 0 failed」不符。命令原文：uv run --no-sync pytest -q tests/unit/test_md_on_disk…——实为 uv run --no-sync pytest -q tests/unit/test_state_ledger.py::test_every_md_on_disk_has_ledger_entry，rc=1。实测到的事实：红原文「AssertionError: 磁盘上有缺陷单但账本查不到（D-009 的形态：新实例按账本恢复会漏掉它们）：['D-051']」；git status 实测 orchestrator/defects/D-051.md 为 ?? 未跟踪（本棒上工第 1 轮时不存在该文件，系编排器 U-1 自纠新建）；哨兵扫描面为 *.md 台账一致性，与本棒 2 件 py 零因果。候选处置：(a) 编排器把 D-051.md 与台账条目同批入库后复跑 V5（预期 0 failed）；(b) 编排器先补账本条目、保持文件在飞。倾向 (a)——与既有 D-0xx 缺陷单入库路径同型；依约只报不裁。

SELF_REPORTED_DEVIATIONS:
  1. V5 实数 rc=1/747 passed/1 failed ≠ 你期望的 0 failed——差值全部归因 U-4（编排器在飞 D-051.md），本棒无责但如实报数。
  2. 新增例断言②用 JOB_INTERRUPTED **import 常量**而非字符串字面量「"JOB_INTERRUPTED"」：语义与你指令的 code != "JOB_INTERRUPTED" 全等且更符合「禁发明/禁写死」；如需字面量形态请告知，本棒不擅自再改。
  3. 模块 docstring 同步改写为「新增 6 个函数、净新增 9 例 collected」并记录 U-1 终裁事实（A88 无④、终裁属编排器侧派单文缺陷）——仍在唯一授权改动件内。
  4. PC-1/PC-2 为第 1 轮落地态（006aa53d2694）取证；本轮文件已演进，未重放旧 PC 的原样变异，新落地态的有牙证明由 PC-5 承担（如需对新态重放 PC-1..PC-4，请另派）。
  5. test_artifact.py 第 2 轮零改动；git status 中 S3/编排器的 M/?? 件（app.py、两哨兵、activities、tests/api、D-051.md）全程未 add/checkout/clean/reset/stash。
  6. V6 三门是全仓在飞快照值；辅助脚本仍在仓库外（/mnt/c temp ＋ /home/szf/.s6_land 落地态备份），未新建 evidence/**。

COVERAGE_MAP_3B 尾段（逐字）:
  test_unreferenced_artifact_swept → …::test_artifact_sweep_removes_unreferenced_and_keeps_referenced ＋ …::test_artifact_rollback_after_rename_is_reclaimable_by_sweep【同意】
  test_referenced_artifact_never_swept → …::test_artifact_sweep_removes_unreferenced_and_keeps_referenced ＋ …::test_artifact_sweep_never_touches_in_flight_attempt_dirs ＋ …::test_artifact_sweep_ignores_every_other_data_subdir【同意】

residual／残差（独立字段）: （本段无内容）——残差断言面已随 §3.A 各例 docstring 与 U1_REMEDY_LANDED 段报出，回执未设单独 residual 字段。

TIER_CONFIRM: model=qwen3.8-flash, reasoning=medium（与派单档位一致）
```

---

## §3 编排器对自报值的独立复核结论（禁采信自报）—— **本批零失真；一处口径澄清见 §3bis**

| lane 自报 | 编排器实测 | 判定 |
|---|---|---|
| `test_lease.py` 476 行 / 20778 B / `112b149f1b12` | **477** 行 / 20778 B / `112b149f1b12` | 字节与 sha **逐字相符**；行数差 1＝口径差（`wc -l` vs `len(split("\n"))`，与 S3 同型）⇒ 非实质不符 |
| `test_artifact.py` 113 行 / 4924 B / `1d65896e618a` | **114** 行 / 4924 B / `1d65896e618a` | 同上 |
| `V1_lease collected=14` | **14**（按派单文逐字命令 `-k lease` 的目录过滤口径复跑；分解 9 新 ＋ 5 既有 `test_state_machine.py`） | **逐字相符**（≥11 门槛满足）⇒ 见 §3bis 口径澄清 |
| `V2_artifact collected=19` | **19**（按逐字命令 `-k artifact` 复跑；分解 1 新 ＋ 13 `test_artifact_write.py` ＋ 5 `test_worker_deps.py`） | **逐字相符**（＝派单文「现值 18 ＋ 新增 1」）⇒ 见 §3bis |
| `V3_dir collected=98` | **98**，且逐件求和 1+13+3+7+34+9+13+18 = **98** 闭合 | 相符 |
| `V4_state_machine collected=13` | **13** | 相符 |
| `V10_clock_usage`：「**7 函数 / 10 collected**」 | 6 函数（lease）+ 1 函数（artifact）= **7**；9 + 1 = **10** | **逐字相符**。与 V1=14 / V2=19 **不矛盾**：V10 是「本棒新增两件」的**按文件**口径（10），V1/V2 是派单文指定的**目录关键字过滤**口径（含 23 例既有），两口径可精确闭合：14+19 = 33 = **10 新 ＋ 23 既有**（5 + 13 + 5 = 23，且两组既有文件互不相交）⇒ 见 §3bis |
| `V5_full rc=1 / 747 passed / 1 failed`（D-051 哨兵） | 编排器复跑：**rc=0 / 748 passed / 0 failed**；该哨兵单跑 `1 passed` | 差值已由 **`3422621`（R18-landS3）** 消除（D-051.md 与台账条目同批入库）⇒ U-4 采纳候选 (a)，见 A250 |
| `V6` ruff check / ruff format / mypy 全 rc=0 | 工作树复测 rc=0 / rc=0「313 files」/ rc=0「112 source files」 | 相符（313 与 112 均为**工作树**口径，含本棒 2 件；冻结树权威值见 `00-index.md` §6） |
| `V7_numstat_frozen` 3 行（全属 S3/编排器） | 本批入库前复测 numstat **空**（S3 已随 `3422621` 入库） | 相符（时点差：lane 测于 S3 入库前） |
| `V8_redline_hits: 0` | 文本实测 `datetime.now`/`utcnow`/`time.time(`/`monotonic`/`time.sleep`/`asyncio.sleep`/`# type: ignore` **全 0** | 相符。AST 扫到的 `now` 全部是 `fixed_clock.now()` / `clock.now()`（注入的 FixedClock）或由其绑定的局部名 ⇒ **非**系统时间读数 |
| `PROTECTED_SHA_AFTER` 9/9 全等 | 独立复测 **9/9 全等**（含 `tests/integration/jobs/__init__.py` = `056664ce00b3`） | 相符 |
| `PC5_RESULT` 有牙、复原 sha 全等 | 编排器**独立复放 PC-5**：变异态 sha `8441748853db`、AST 生效证明 True、rc=1、红原文 `assert True is False` / `FAILED …test_interrupted_job_marked_job_interrupted`（`1 failed, 8 passed`）、逐字节复原回 `112b149f1b12`、复原后 `9 passed` rc=0 | 相符 ⇒ **判据确有牙** |
| S3 已入库面（activities.py 等 6 件）禁触碰 | 独立复测 **6/6 sha 全等** | 相符 ⇒ 两 lane 写集**零交叉**（A144(c) 归属成立） |

**关于 `issues[0]["retryable"]`**：该字符串在 `test_lease.py` 中命中 **1** 次，位置为 **`:223` 的 docstring**，
原文是「…``issues[0]["retryable"]``——该键在契约 ``extra="forbid"`` 下不可能存在」，即**说明为何不这么写**，
**不是断言** ⇒ 符合 R18-5 的终裁（禁写该形态）。实际断言面为 `:237 assert record.retryable is True`、
`:240 assert problem["status"] == 500`、`:241 assert problem["code"] != JOB_INTERRUPTED`，
且 `JOB_INTERRUPTED` 由 `from campaignlab.worker.errors import JOB_INTERRUPTED, LeaseLost` **import 常量**引入
（lane 自报偏差 #2，编排器认可：语义全等且更符合「禁发明/禁写死」）。

---

## §3bis 口径澄清（编排器**自纠**：初稿误判 lane「失真」，现以实证推翻并如实更正）

**背景（如实登记，禁粉饰）**：编排器在 R18 回收 S6 时，初稿 §3 把 lane 自报的 `V1_lease collected=14` /
`V2_artifact collected=19` 判为**自报失真**，理由是「编排器按**单文件**复跑得 9 / 1」，并进一步把
V10 的「7 函数 / 10 collected」当作「与 14/19 自相矛盾」的**内部证据**，据此拟立 **A252 / R18-8**。
**该判断是编排器自己的口径错误**，现已用派单文原文 ＋ 实证复跑推翻。

**判据来源（派单文逐字，`orchestrator/handoff/R18-lane-M0-04-S6.md`，sha256[:12]=`4f15d3614700` / 26367 B / 249 行）**：

| 判据 | 派单文 §4 逐字命令 | 派单文期望（逐字） |
|---|---|---|
| V1 | `uv run --no-sync pytest -q tests/integration/jobs -k lease` | 「rc=0；collected **≥11**（现值 **5** ＋ 你新增 **6**；若你参数化则更多，须在回执报出实数）」 |
| V2 | `uv run --no-sync pytest -q tests/integration/jobs -k artifact` | 「rc=0；collected **≥19**（现值 **18** ＋ 新增 **1**）」 |

⇒ V1/V2 的目标**从派单当刻起就是目录级关键字过滤**（`tests/integration/jobs` 整目录 ＋ `-k`），
**不是**按文件计数。lane 报 14 / 19 正是**照命令执行**的结果。

**编排器实证复跑（本批，见 `commands-and-outputs.log` 同段）**：

| 口径 | 命令 | 实测 |
|---|---|---|
| 目录过滤（＝派单文 V1/V2 口径） | `pytest -q --collect-only tests/integration/jobs -k lease` | **14/98 collected（84 deselected）** |
| 目录过滤（＝派单文 V1/V2 口径） | `pytest -q --collect-only tests/integration/jobs -k artifact` | **19/98 collected（79 deselected）** |
| 按文件（编排器初稿误用的口径） | `pytest -q --collect-only tests/integration/jobs/test_lease.py` | **9 collected** |
| 按文件（编排器初稿误用的口径） | `pytest -q --collect-only tests/integration/jobs/test_artifact.py` | **1 collected** |

**`-k` 命中的文件分解（实证 `--collect-only` ＋ 按文件归并计数）**：

| 过滤词 | 命中文件 : collected | 合计 |
|---|---|---|
| `lease` | `test_lease.py`（**本棒新增**）: **9** ＋ `test_state_machine.py`（既有）: **5** | **14** |
| `artifact` | `test_artifact.py`（**本棒新增**）: **1** ＋ `test_artifact_write.py`（既有）: **13** ＋ `test_worker_deps.py`（既有）: **5** | **19** |

**闭合校验（算术级，禁口算）**：新增 9 + 1 = **10**；既有 5 + 13 + 5 = **23**；14 + 19 = **33** = 10 + 23 ✔。
两组既有命中文件（`test_state_machine.py` vs `test_artifact_write.py` / `test_worker_deps.py`）**互不相交**
⇒ 无重复计数，V1/V2 之和可加。派单文 V2 期望「现值 **18**」亦与实测既有 13 + 5 = **18** 逐字相符。

**结论（终裁，如实）**：
1. lane 的 V1=14 / V2=19 **无失真**，且 V1 满足 `≥11`、V2 满足 `≥19` 门槛 ⇒ **判据通过**。
2. 「V10 与 V1/V2 自相矛盾」的推论**作废** —— 二者是**两个不同口径**，且可精确闭合（见上）。
3. 编排器初稿的误判**不构成 lane 缺陷**，故**不立 A252**（原拟「lane 自报失真」终裁，ID 作废不复用）。
4. 但初稿误判本身**是编排器的一处真实失误**，须留纪律痕迹。原拟自纠项 **R18-8**（主题「lane 自报口径
   与命令不符」）**主题被重新界定**为编排器自身失误，仍以 **R18-8** 编号入账（该 ID 此前未被占用，
   实测台账内 `R18-` 系列最大值＝R18-7），其内容改为：
   「**判据复核必须以派单文的逐字命令为唯一口径来源**；编排器在判定 lane 自报值失真前，
   须先回到派单文取该判据的**逐字命令**并照此复跑，禁以自选口径替代」。
   ⇒ 已并入 PRE-25/26/27 系列的派单文一致性检查（本批新增 **PRE-29**：失真判定前的口径回源义务；
   实测该 ID 此前未被占用，`PRE-` 系列最大值＝PRE-28）。
5. 归档件（本件）**不重写历史**：初稿的错误结论以本节更正方式留档，§3 表格同步更正为实测值，
   二者并存以供审计追溯；本更正发生在**入库之前**（本件从未以错误结论入库），故不存在已入库事实被改写。
