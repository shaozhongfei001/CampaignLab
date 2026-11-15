# R18 · M0-04/S6 入库取证索引 —— 编排器独立复验全绿 ＋ U-4 终裁（A250）＋ 6 项自报偏差终裁（A251）＋ 阳性对照 PC-5 复放有牙 ＋ **编排器自纠 R18-8 / 新立 PRE-29（口径回源义务）**

> **本件性质**：编排器对 lane S6（M0-04/S6 · agent `Lorentz` · `qwen3.8-flash`/`medium` · loop 2/2）交付面的
> **独立复验取证索引**。一切读数由编排器**实测**，禁采信 lane 自报（`rule_no_trust_handoff_summary_assertions`）。
> 命令原文与逐字输出见同目录 `commands-and-outputs.log`；lane 回执原文（逐字留档）见同目录 `lane-return-raw.md`。
>
> **本批最重要的一条如实登记**：编排器初稿曾把 lane 自报的 `V1=14` / `V2=19` 判为**「自报失真」**并拟立 A252。
> 该判定是**编排器自己的口径错误**，已按派单文逐字命令回源实证推翻 ⇒ **lane 无失真**，A252 作废不立；
> 编排器自身失误立自纠 **R18-8** ＋ 新立预防项 **PRE-29**。详见本件 §3bis。

- **入库前 HEAD**：`4b9150c`　**分支**：`m0-framework`　**tag**：`R18-landS6`
- **派单文**：`orchestrator/handoff/R18-lane-M0-04-S6.md`（249 行 / 26367 B / sha256[:12]=`4f15d3614700`）
- **lane agent_id**：`01a1dff2-a13f-7531-91c9-1eeccf61a928`（昵称 Lorentz；已 `close_agent`，并发槽已释放）
- **档位一致性**：lane `TIER_CONFIRM: model=qwen3.8-flash, reasoning=medium` 与派单档位一致 ⇒ `tier_match=true`
- **critical=true / slack=0**（关键路径，M0-04/S8 是 wave-3 唯一解锁点）

---

## 1. 交付面逐件实测（**入库前**工作树实测值；编排器口径 `lines = len(text.split("\n"))`）

| 件 | 类型 | lines | bytes | sha256[:12] | collected | lane 自报 | 判定 |
|---|---|---|---|---|---|---|---|
| `tests/integration/jobs/test_lease.py` | 新增 py | **477** | **20778** | `112b149f1b12` | **9** | 476 / 20778 / `112b149f1b12` | 字节与 sha **逐字相符**；行数差 1 ＝口径差（`wc -l` vs `split("\n")`，与 S3 同型）⇒ 非实质不符 |
| `tests/integration/jobs/test_artifact.py` | 新增 py | **114** | **4924** | `1d65896e618a` | **1** | 113 / 4924 / `1d65896e618a` | 同上 |

**目录面闭合校验（算术级，禁口算）**：`tests/integration/jobs` 实测 collected **98**，
逐件求和 `1 + 13 + 3 + 7 + 34 + 9 + 13 + 18 = 98` ✔（其中 `9`＝本棒 `test_lease.py`、`1`＝本棒 `test_artifact.py`）。

---

## 2. 编排器独立复验（V1–V11 全绿；原文见 cmdlog §1 / §2 / §3）

| 判据 | 派单文逐字命令口径 | 期望 | **编排器实测** | 判定 |
|---|---|---|---|---|
| V1 租约门 | `pytest -q tests/integration/jobs -k lease`（**目录关键字过滤**） | rc=0；collected **≥11**（现值 5 ＋ 新增 ≥6） | rc=0；**14/98 collected（84 deselected）** ＝ 9 新 ＋ 5 既有 `test_state_machine.py` | **通过**（见 §3bis） |
| V2 制品门 | `pytest -q tests/integration/jobs -k artifact`（**目录关键字过滤**） | rc=0；collected **≥19**（现值 18 ＋ 新增 1） | rc=0；**19/98 collected（79 deselected）** ＝ 1 新 ＋ 13 `test_artifact_write.py` ＋ 5 `test_worker_deps.py` | **通过**（既有 13+5=18 与派单文「现值 18」逐字相符） |
| V3 目录面 | `pytest -q tests/integration/jobs` | rc=0；collected **≥95** | rc=0；**98** | **通过** |
| V4 状态机门未回归 | `pytest -q tests/integration/jobs -k state_machine` | rc=0；collected **13**（禁变） | rc=0；**13** | **通过**（零回归） |
| V5 全量 | `pytest -q` | rc=0；passed **≥741** | rc=0；**748 passed, 0 failed**（161.15s） | **通过**（lane 自报的 1 红＝U-4，已由 `3422621` 消除，见 §3 / A250） |
| V6 质量门 | `ruff check .` / `ruff format --check .` / `mypy` | 三门 rc=0 | rc=0「All checks passed!」/ rc=0「**313** files already formatted」/ rc=0「Success: no issues found in **112** source files」 | **通过**（313 与 112 为**工作树**口径，含本棒 2 件；**冻结树**权威值见 §5） |
| V7 numstat（冻结面） | `git diff --numstat HEAD` | 仅授权行 | 本批入库前复测 **空**（S3 的 3 行已随 `3422621` 入库） | **通过**（时点差：lane 测于 S3 入库前） |
| V8 红线扫描 | `datetime.now` / `utcnow` / `time.time(` / `monotonic` / `time.sleep` / `asyncio.sleep` / `# type: ignore` | **0 命中** | **全 0**。AST 扫到的 `now` 全部是 `fixed_clock.now()` / `clock.now()`（注入的 FixedClock）或由其绑定的局部名 ⇒ **非**系统时间读数 | **通过** |
| V10 时钟面 | 每例只用注入时钟 | 7 函数 / 10 collected | 6 函数（lease）＋ 1 函数（artifact）＝ **7**；9 ＋ 1 ＝ **10** | **逐字相符**（与 V1/V2 不矛盾，闭合见 §3bis） |
| V11 保护面 | 9 件 PROTECTED sha 对撞 | 9/9 全等 | **9/9 全等**（含 `tests/integration/jobs/__init__.py` = `056664ce00b3`） | **通过** |
| — S3 已入库面 | S3 的 6 件冻结文件 sha 对撞 | 6/6 全等 | **6/6 全等** | **通过** ⇒ 两 lane 写集**零交叉**（A144(c) 归属成立） |

**SQL 面说明（如实）**：新件内出现 `INSERT` / `SELECT` 字面量，与该目录**已入库的 7 件同型文件全部一致**
⇒ 属集成层既有约定（直连 SQLite 断言 DB 侧真实行状态），**不判红线**。

**`issues[0]["retryable"]` 形态核查（U-1 终裁的执行面）**：该字符串在 `test_lease.py` 中命中 **1** 次，
位置 **`:223`**，处于 **docstring** 内，原文是「…`issues[0]["retryable"]`——该键在契约 `extra="forbid"` 下不可能存在」，
即**说明为何不这么写**，**不是断言** ⇒ 符合终裁。真实断言面为 `:237 assert record.retryable is True`、
`:240 assert problem["status"] == 500`、`:241 assert problem["code"] != JOB_INTERRUPTED`；
`JOB_INTERRUPTED` 由 `from campaignlab.worker.errors import JOB_INTERRUPTED, LeaseLost` **import 常量**引入。
新增例名实测为 `test_interrupted_job_marked_job_interrupted`。

---

## 3. U 项终裁（A250 / A251，事实均经编排器独立复核）

**A250 —— U-4 采纳候选 (a)，判定「已消除」**
lane 报 U-4：V5 全量 1 红，红原文「磁盘上有缺陷单但账本查不到（D-009 的形态）：`['D-051']`」，
且 `orchestrator/defects/D-051.md` 当时为 `??` 未跟踪（系编排器为 U-1 自纠新建，**在飞**）。
lane 依约**只报不裁**，给出候选 (a) 同批入库后复跑 / (b) 先补账本条目保持文件在飞，倾向 (a)。
**编排器终裁：采纳 (a)**。事实依据：D-051.md 与其台账条目已随 **`3422621`（R18-landS3）** 同批入库；
编排器于本批独立复跑 `pytest -q` ⇒ **rc=0 / 748 passed / 0 failed**，
且哨兵单跑 `tests/unit/test_state_ledger.py::test_every_md_on_disk_has_ledger_entry` ⇒ **rc=0 / 1 passed**。
⇒ U-4 **已消除**，且与本棒 2 件 py **零因果**（哨兵扫描面是 `*.md` 台账一致性）。

**A251 —— 6 项自报偏差的逐条终裁**

| # | lane 自报偏差 | 编排器终裁 |
|---|---|---|
| 1 | V5 实数 rc=1/747 passed/1 failed ≠ 期望 0 failed，差值全归 U-4 | **接受**。如实报数正确；差值已由 A250 消除 |
| 2 | 断言②用 `JOB_INTERRUPTED` **import 常量**而非字符串字面量 | **接受**。语义全等，且更符合「禁发明/禁写死」（D-012 / D-014）⇒ 优于字面量形态 |
| 3 | 模块 docstring 改写为「新增 6 函数 / 净新增 9 例 collected」并记录 U-1 终裁事实 | **接受**。仍在唯一授权改动件内，未越权 |
| 4 | PC-1/PC-2 为第 1 轮落地态（`006aa53d2694`）取证，未对第 2 轮新态重放；新态有牙证明由 PC-5 承担 | **接受**。编排器已**自行复放 PC-5**（§4）对新态实证有牙 ⇒ 缺口已由编排器侧补齐，不需另派 |
| 5 | `test_artifact.py` 第 2 轮零改动；S3/编排器在飞件全程未 add/checkout/clean/reset/stash | **接受且已实证**：编排器独立复测 S3 的 6 件 sha **6/6 全等**、numstat **空** ⇒ 零污染成立 |
| 6 | V6 三门是全仓在飞快照值；辅助脚本留在仓库外（`/mnt/c` temp ＋ `/home/szf/.s6_land`），未新建 `evidence/**` | **接受**。取证件由**编排器**建（本目录），符合「lane 禁建 evidence」的既有先例；仓库外残留**不入库**，如实登记于 §8 |

**U-1 / U-2 / U-3**：lane 报「已按终裁落地关闭 / 维持关闭 / 关闭」。编排器复核：
U-1 的四断言形态全部钉住且经 PC-5 实证有牙（§4）；U-2 的 `contended` 两枚 `False` ＋ docstring 语义说明原样保留、
未新增并发 fixture（符合终裁）；U-3 的两条 mount 哨兵在 V5 全量中**不再出现红** ⇒ 三项关闭**成立**。

---

## 3bis 口径澄清与编排器自纠（R18-8 ＋ PRE-29）—— **本批零 lane 失真**

**编排器初稿的错误（如实登记，禁粉饰）**：编排器首轮复验脚本 `.orch_tmp/r18_v_s6.py` 在
**第 108 行**把判据写成 `("V1 lease", LEASE, 14)` / `("V2 artifact", ARTIF, 19)`，其中
`LEASE = "tests/integration/jobs/test_lease.py"`、`ARTIF = "tests/integration/jobs/test_artifact.py"`（第 15–16 行）。
即：**期望值 14/19 取自派单文的「目录关键字过滤」口径，而收集命令却用了「按单文件路径」口径** —— 两者口径不一致，
于是打印出 `collected=9 want=14 **MISMATCH**` / `collected=1 want=19 **MISMATCH**`。
编排器据此初稿判 lane「自报失真」，并把 V10 的「7 函数 / 10 collected」误当作「14+19=33 ≠ 10」的**内部矛盾证据**，
拟立终裁 **A252** 与自纠 **R18-8**。

**回源取证（派单文原文，cmdlog §4）**：`orchestrator/handoff/R18-lane-M0-04-S6.md` §4 判据表逐字为

- V1：`uv run --no-sync pytest -q tests/integration/jobs -k lease` → 「rc=0；collected **≥11**（现值 **5** ＋ 你新增 **6**…）」
- V2：`uv run --no-sync pytest -q tests/integration/jobs -k artifact` → 「rc=0；collected **≥19**（现值 **18** ＋ 新增 **1**）」

⇒ V1/V2 **从派单当刻起就是目录级 `-k` 过滤**，不是按文件计数。lane 报 14 / 19 正是**照命令执行**的结果。

**实证复跑（cmdlog §3）**：

| 口径 | 命令 | 实测 |
|---|---|---|
| 目录过滤（＝派单文 V1/V2 口径） | `pytest -q --collect-only tests/integration/jobs -k lease` | **14/98（84 deselected）** |
| 目录过滤（＝派单文 V1/V2 口径） | `pytest -q --collect-only tests/integration/jobs -k artifact` | **19/98（79 deselected）** |
| 按文件（编排器初稿误用口径） | `pytest -q --collect-only tests/integration/jobs/test_lease.py` | **9** |
| 按文件（编排器初稿误用口径） | `pytest -q --collect-only tests/integration/jobs/test_artifact.py` | **1** |

**`-k` 命中文件分解与闭合校验**：

| 过滤词 | 命中文件 : collected | 合计 |
|---|---|---|
| `lease` | `test_lease.py`（**本棒新增**）: **9** ＋ `test_state_machine.py`（既有）: **5** | **14** |
| `artifact` | `test_artifact.py`（**本棒新增**）: **1** ＋ `test_artifact_write.py`（既有）: **13** ＋ `test_worker_deps.py`（既有）: **5** | **19** |

新增 9 + 1 = **10**；既有 5 + 13 + 5 = **23**；14 + 19 = **33** = 10 + 23 ✔。
两组既有命中文件互不相交 ⇒ 无重复计数，V1/V2 之和可加；派单文 V2 期望「现值 18」亦与实测 13 + 5 = **18** 逐字相符。

**终裁**：
1. lane 的 V1=14 / V2=19 **无失真**，且满足 `≥11` / `≥19` 门槛 ⇒ **判据通过**。
2. 「V10 与 V1/V2 自相矛盾」的推论**作废**：二者是两个不同口径且可精确闭合。
3. **不立 A252**（原拟「lane 自报失真」终裁；该 ID 作废不复用）。
4. **立自纠 R18-8**（该 ID 此前未占用，实测台账 `R18-` 系列最大值＝R18-7）：主题由原拟「lane 自报口径与命令不符」
   **重新界定**为编排器自身失误 ——「编排器在判定 lane 自报值失真前，**必须**先回到派单文取该判据的
   **逐字命令**并照此复跑；禁以编排器自选口径替代派单文口径」。
5. **新立 PRE-29（口径回源义务）**（实测该 ID 此前未占用，`PRE-` 系列最大值＝PRE-28）：
   派单文一致性检查系列（PRE-25 / PRE-26 / PRE-27）新增一条 —— **回收侧**的判据复核，
   其收集命令必须与派单文 §判据表的命令**逐字同源**；任何 `want=` 值必须与该命令的口径配对，
   否则该次复核结论**无效**，须回源重跑后方可下判。
6. 归档**不重写历史**：`lane-return-raw.md` §3 表格已更正为实测值，并新增 §3bis 完整留档本次误判与更正过程；
   `commands-and-outputs.log` §1 **逐字保留**了那两行错误的 `**MISMATCH**` 原文（附编排器按语说明其为脚本口径缺陷）。
   本更正发生在**入库之前**（错误结论从未入库），故不存在已入库事实被改写。

---

## 4. 编排器自办阳性对照 PC-5 复放（证明 A250/U-1 终裁版判据**确有牙**）

lane 自报偏差 #4 指出 PC-1/PC-2 取证于第 1 轮落地态。为免「判据无牙」，编排器**对第 2 轮新落地态自行复放 PC-5**：

| 步 | 动作 | 实测 |
|---|---|---|
| [0] | 复原基准 | sha=`112b149f1b12`，bytes=**20778** |
| [1] | 目标断言原文出现次数 | **1**（唯一命中，变异面确定） |
| [2] | 施加变异 `record.retryable is True` → `is False` | 变异态 sha=`8441748853db`（≠ 基准）✔ |
| [3] | AST 生效证明（存在 `record.retryable is False` 比较节点） | **True** ⇒ 变异确实落到语法树 |
| [4] | `pytest -q tests/integration/jobs/test_lease.py` | **rc=1**；`FAILED …::test_interrupted_job_marked_job_interrupted`；`1 failed, 8 passed`；红原文 `>       assert record.retryable is False` / `E       assert True is False` ⇒ **判红成立** |
| [5] | 逐字节复原 | sha=`112b149f1b12` **== 基准** ⇒ **True**（零残留） |
| [6] | 复原后复跑 | **rc=0**；`9 passed` ⇒ 复原态健康 |

⇒ **判据确有牙**：变异必判红、复原必回绿，且字节级可逆。PC-5 复放全程由编排器执行，未假手 lane。

---

## 5. counts 与两项护栏（如实上报，禁粉饰、禁为凑配比降档）

**入库后 counts（冻结索引树实测；`run_commit` 逐条对账，不符即拒绝提交并回滚）**

| 键 | 入库前（HEAD `4b9150c`） | **入库后** | 增量 | 增量归因 |
|---|---|---|---|---|
| `ruff_formatted_files` | 311 | **316** | +5 | 2 py ＋ 3 md（`.log` 不在 `RUFF_SUFFIXES=(".py",".md")` 内，不计数） |
| `in_scope_py` | 112 | **114** | +2 | `test_lease.py`、`test_artifact.py` |
| `in_scope_md` | 199 | **202** | +3 | S6 `00-index.md`、S6 `lane-return-raw.md`、S3 `lane-return-raw-addendum.md` |
| `mypy_source_files` | 110 | **112** | +2 | 两件新 py 均在 `tests/` ⇒ 落在 mypy `files=["src","tests","scripts"]` 域内 |
| `pytest_passed` | 738 | **748** | +10 | 9（lease）＋ 1（artifact） |

**两项护栏（如实上报：本批仍**双双未达标**，禁粉饰、禁为凑配比降档）**

| 护栏 | 目标 | 入库前 | **入库后** | 判定 |
|---|---|---|---|---|
| `flash_share_tasks`（低复杂度任务占比） | **≥ 0.60** | 0.5636（31/55） | **0.5714（32/56）** | **未达标（FAIL）** —— 方向改善（+0.0078）但仍差 0.0286 |
| `flash_share_tokens`（低复杂度 token 占比） | **≤ 0.35** | 0.6655 | **0.6655** | **未达标（FAIL）** —— 本批 lane tokens=null（见下），无新样本 ⇒ 数值不变 |

**token 口径的如实说明**：lane S6 **未报 token 用量**（两段回执原文与 `close_agent(Lorentz)` 带回的完整终态回执中
均无该字段，编排器已复核）⇒ 台账记 `tokens=null` / `tokens_estimated=true`，**无自报区间可引**，
本批对 `flash_share_tokens` **无贡献**（分母中 null 计数 35 → 36）。这本身是护栏可信度的缺口，
已挂 FU（机器化 token 记账）—— 见 §9。

**dev-lane 子口径**：`flash_share_tasks_dev` ＝ 13/34 ＝ **0.3824**（开发型 lane 的 flash 占比显著低于总体，
是总口径未达标的主因；如实登记，不以「总体接近 0.6」掩盖）。

---

## 6. 悬空引用与未跟踪件归属

- `h.dangling_refs(["tests/integration/jobs/test_lease.py", "tests/integration/jobs/test_artifact.py"])` ⇒ **`[]`**（零悬空）。
- 本批入库后新增的取证件（3 md ＋ 1 log）同批纳入悬空扫描面；`orchestrator/state.json` 按
  `DANGLING_SWEEP_SKIP` 豁免（其引用面由 `test_state_ledger.py` 两条机器守护专管）。
- **入库前工作树未跟踪件**：`?? tests/integration/jobs/test_artifact.py`、`?? tests/integration/jobs/test_lease.py`
  （lane S6 交付面）＋ 本批取证件 4 件（编排器产出）。**全部**由本提交显式路径 `git add`（禁 `-A`），
  归属划分：2 py ⇒ lane S6（A144(c)）；4 取证件 ⇒ 编排器。
- **写集零交叉实证**：S3 的 6 件冻结文件 sha **6/6 全等**、`git diff --numstat HEAD` **空** ⇒ 两 lane 未互碰。

---

## 7. 同批入库的 S3 回执补遗（`lane-return-raw-addendum.md`）

上一提交 `4b9150c` 在台账中登记了 `resume.s3_return_addendum_note_R18`（status **OPEN**），
承诺「以 append-only 补遗件更正 S3 归档口径段 ②」。本批兑现该承诺：
补遗件落于 `evidence/M0/ORCHESTRATOR/r18-m2-01-s3-landing/lane-return-raw-addendum.md`（6540 B / 60 行 / sha256[:12]=`b034f3415b4e`），
内容为 **PC-1(b) / PC-2 原文的复原**（经 `close_agent(Nash)` 的 `previous_status` 取回，
推翻了此前「已不可复原」的判断）。该 note 于本批**关闭为 DONE**（append-only，原 OPEN 记录不改写）。

---

## 8. 未尽面（如实登记，不含糊）

1. **lane 的仓库外残留未清理**：lane 自报偏差 #6 提到辅助脚本留在 `/mnt/c` temp 与 `/home/szf/.s6_land`
   （第 1 轮落地态备份）。二者**均在仓库外**、不入库、不影响任何门禁；但属**未清理的环境残留**，
   编排器**不代为删除**（禁越权动 lane 私有目录），如实登记留痕。
2. **COVERAGE_MAP_3B 的 3 名逐条映射全文不可复原**：lane 第 2 轮回执尾部遇传输截断
   （`…3125 tokens truncated…`），窄请求重发只取回**尾段 2 名**，其余 **3 名不可复原**。
   已在 `lane-return-raw.md` 归档口径段 ① 明示，**禁凭记忆重构**。
3. **lane 第 1 轮回执全文未留档**（含当时 `FILES_NEW` 读数 `006aa53d2694`）：`close_agent(Lorentz)` 返回的
   `previous_status.completed` 是**第 2 轮**终态回执，不含第 1 轮原文 ⇒ 确认不可复原（同件归档口径段 ②）。
4. **token 记账仍为 null**：见 §5，护栏 `flash_share_tokens` 因此**长期不可信**，FU 未闭环。
5. **任务级未完结**：M0-04 交付到 S6，**S8 尚未开工**。M0-04 的**任务级 AC 取证面**与
   **M0 阶段汇总件**（二者均登记于台账 `forward_reference_registry`，落点由 S8 负责）是 **S8 的前向引用**，
   本批**不预建**、且依 **PRE-28** 在本件内**只写职责归属、不写路径字面量**（避免悬空引用）。
   M0-04/S8 是 wave-3 的**唯一解锁点**（其后 21 个 TODO 任务依赖它）⇒ 仍在关键路径，slack=0。
6. **M2-01 交付到 S3**，余 **S4 → S5 → S6 → S7**；S4 与 S3 **同文件**（`api/rules.py` ＋ `app.py` 挂载 5→6）
   ⇒ **必须串行**，禁与 M0-04 lane 并发写同文件。

---

## 9. 自纠（append-only，原文不改写）

| 编号 | 事实 | 处置 |
|---|---|---|
| **R18-6**（既存，本批继续兑现） | Round 18 编排器未在回收当刻落盘 lane 原始回执，违反 R12 / R13 既有先例 | 本批 `lane-return-raw.md` **已落盘**（S6）＋ S3 补遗件落盘；机器化 `archive_lane_return` ＋ `run_commit` 顺序门仍挂 **FU-61**（未闭环，如实登记） |
| **R18-8**（本批新立） | 编排器复验脚本把派单文的「目录过滤」期望值与「按单文件」收集口径配对，导致误判 lane 自报失真，并据误判拟立 A252 | ① 回源实证推翻误判（§3bis）；② A252 作废不立；③ 立 **PRE-29** 口径回源义务；④ 错误原文（cmdlog §1 的两行 `**MISMATCH**`）**逐字保留**不删改 |

**本批新立预防项 PRE-29（口径回源义务）**：回收侧对 lane 自报值的任何复核，其**收集/度量命令必须与派单文
§判据表的命令逐字同源**；任何 `want=` 期望值必须与该命令的口径**配对**。若二者口径不一致，
则该次复核结论**无效**，必须回源重跑后方可下判；**禁**以编排器自选口径替代派单文口径来判定 lane「失真」。
（归属：PRE-25 / PRE-26 / PRE-27 派单文一致性检查系列的**回收侧**延伸。）
