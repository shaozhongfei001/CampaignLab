# R18 · M0-04/S8 入库批 —— 编排器独立复验记录（tag `R18-landS8`）

> **口径**：本件全部结论由编排器**自行实测**得出（PRE-29 口径回源义务）。lane 自报值只作**对撞对象**，
> 不作依据；凡自报与实测不符一律以实测入账并如实登记。所有命令在 WSL 仓库根
> `/home/szf/dev/CampaignLab` 执行，Python 一律 `uv run --no-sync python`（PRE-21：禁系统 `python3`）。
> 命令原文与完整输出见同目录 `commands-and-outputs.log`；lane 回执原文见 `lane-return-raw.md`。

## 0. 本批身份

| 项 | 值 |
|---|---|
| lane | `S8`（M0-04 的**第 8 棒**，纯证据棒） |
| 昵称 / agent_id | **Planck** / `01a1e0b9-916a-7ac0-9318-e10f8be00768` |
| 档位 | `qwen3.8-flash` / reasoning `medium` / 预算 9k / loop **2-of-2** |
| 派单文 | `orchestrator/handoff/R18-lane-M0-04-S8.md`（`212L` / `16941B` / `99722f3d4ecd`） |
| predispatch 提交 | `67ba545`（tag `R18-predispatch-S8`） |
| agent_id 回填提交 | `f53ff8d`（tag `R18-backfill-S8agentid`，纯台账） |
| lane 结论 | `RESULT: DONE` |
| 编排器终裁 | **PASS**（零返工；U-1 采纳候选 (a)，见 §6 / A254） |
| critical / slack | `true` / `0` —— **wave-3 的唯一解锁点**，21 个 TODO 任务依赖 M0-04 完成 |

## 1. 交付面：24 件逐件 face 对撞（实测 vs 自报）

编排器对 lane 自报的 24 件逐个 `read_bytes()` 后算 `len(splitlines())` / `len(bytes)` /
`sha256[:12]`，与自报三元组**逐字对撞**。

**结果：24/24 全部相符，不符项 0 条。**

- 4 件 md：`commands-s8.md` 682L/33034B/`653cc29d980e`、`ac.md` 53L/5565B/`832679d66274`、
  `job-states.md` 582L/21463B/`0d84c90542ec`、`summaries/M0-04.md` 15L/2498B/`1547f357dd80`
- 9 件 `gates/V1..V9.log`：sha 逐个相符（`bf7f5757a6fe` / `835f6327ee93` / `82d5eea17c9a` /
  `150d8370b6c4` / `73026e7a042c` / `a0f20510714a` / `feed9aa2838c` / `7044f493f827` / `580636291d05`）
- 11 件 `http/*.json`：文件名闭集**恰为**派单文 §3 的 11 个固定名，无多无少；sha 逐个相符

**一处口径澄清（非偏差）**：11 件 json 自报行数为 `0`（lane 注「单行无换行」），
编排器 `splitlines()` 实测为 `1`。二者同指「文件内容是单行、无末尾换行」这一事实，
差异纯由计数口径（`wc -l` 数换行符 vs `splitlines()` 数行）造成；**字节与 sha 逐字相符**
⇒ 判 **PASS**，不立偏差。该口径差异如实登记于此，禁事后抹平。

## 2. 写权面闭集对撞（**纯证据棒**约束）

派单文 §1 硬约束：本棒**只许新增** `evidence/M0/**`，**禁改任何代码与测试**。

| 判据 | 命令 | 实测 | 判定 |
|---|---|---|---|
| 落盘件总数 | `git status --porcelain -uall` | **24 条** | ✅ 与自报清单**集合相等** |
| 已跟踪件被改 | 同上，筛非 `??` 行 | **0 条** | ✅ 零改动 |
| 超出清单的落盘件 | 集合差 | **0 条** | ✅ 无越界 |
| A253 落点 | `evidence/M0/M0-04/commands-s8.md` 存在？ | **存在** | ✅ 按 A253 落 `-s8` 后缀名 |
| A253 冲突面 | `evidence/M0/M0-04/commands.md`（**既有已跟踪件**）被改？ | **无改动** | ✅ 禁改写已入库件成立 |

> **编排器自纠一处探针错误（见 §8 / R18-9）**：初版复验脚本把「`commands.md` 必须不存在」当判据，
> 实测打印 `True（必须 False）`。经核：该文件是 M0-04 早期棒次的**既有已跟踪件**，
> 正是 A253 裁定「落点已被占用 ⇒ S8 改落 `commands-s8.md`」的**冲突源本身**。
> 正确判据是「S8 **未新建也未修改**它」，实测成立（不在 24 条未跟踪清单内、且无 tracked 改动）。
> **lane 无过失，探针预期写错**；错误原文在 `commands-and-outputs.log` 中逐字保留不删改。

## 3. 门的独立复跑（PRE-29：用派单文的**逐字**命令，禁按单文件路径替代）

这正是 R18-8 / PRE-29 立规的成因形态（把 `-k` 目录关键字口径与单文件收集口径混配 ⇒ 假 MISMATCH）。
本批**严格按派单文 §4 的逐字命令**复跑：

| 门 | 逐字命令 | lane 自报 | 编排器实测 | 判定 |
|---|---|---|---|---|
| V1 | `…sha256(d).hexdigest()[:16],len(d)` on `contracts/openapi.json` | `592571099d638251 443309` | `592571099d638251 443309` | ✅ 逐字相符；且＝台账 `live_openapi_sha16` 现值 |
| V2 | `pytest -q tests/integration/jobs -k state_machine` | `13 passed, 85 deselected` | `13 passed, 85 deselected, 1 warning in 6.28s` | ✅ |
| V3 | `pytest -q tests/integration/jobs -k lease` | `14 passed, 84 deselected` | `14 passed, 84 deselected, 1 warning in 8.24s` | ✅ |
| V4 | `pytest -q tests/integration/jobs -k artifact` | `19 passed, 79 deselected` | `19 passed, 79 deselected, 1 warning in 9.01s` | ✅ |
| V5 | `pytest -q tests/unit/test_job_dto.py` | `66 passed` | `66 passed in 0.62s` | ✅ |
| V7 | `python scripts/check_contracts.py check --validate` | `PASS 登记项=13 实测差异=13 元校验=6` | 同 | ✅ ＝`counts.contract_registered_nodes` 现值 13 |
| V6b | `ruff format --check .`（4 件 md 落盘后） | `321 files already formatted` | `321 files already formatted` rc=0 | ✅ 供 `run_commit` 对账 |

全部 rc=0。**7/7 门逐字吻合，零偏差。**

> **计数口径提醒（禁再犯 R18-8 同型错）**：V2/V3/V4 的 13 / 14 / 19 是**目录关键字过滤**口径，
> **含既有用例**（该目录 collected 98），**不是**本批净新增。本批 lane **零新增 .py**
> ⇒ `pytest_passed` 沿用 **748** 不变。禁把 13+14+19 当增量加进 748。

## 4. AC 判定面复核

- **AC-029**：`evidence/M0/M0-04/ac.md:9` 实测原文 `**判定：PASS**`，标题行
  `## AC-029（spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md:37）` ⇒ **判定在场、口径正确**。
  依据面（V8 五条 ＋ `job-states.md` 的 T7 中断快照 ＋ `http/retryJob-202.json` /
  `cancelJob-409.json` / `cancelJob-200.json`）编排器抽查相符。
- **AC-031**：`ac.md` 实测原文
  「**判定（口径固定，本卡不出 PASS/FAIL）：写入侧前提已交付 ＋ 判定归 M5-01（`primary_owner = M5-01`）**」
  ⇒ **未越权判定**（owner 是 M5-01，本棒只交付写入侧四项前提），且未引用 M5 侧任何尚不存在的落点
  （PRE-28）。文中 `PASS`/`FAIL` 各 2 次命中，逐个核过上下文：分别为 AC-029 的判定
  与「本卡不出 PASS/FAIL」这句**禁判声明本身**，**不构成越权判定**。✅
- `evidence/M0/summaries/M0-04.md` 实测 **15 行 ≤ 30** ✅
- 11 件 `http/*.json` 内出现的 `Problem.code` 实测 7 种
  （`INTERNAL_ERROR` / `JOB_CAPACITY` / `PRECONDITION_REQUIRED` / `RESOURCE_NOT_FOUND` /
  `REVISION_CONFLICT` / `STATE_CONFLICT` / `VALIDATION_ERROR`），与
  `domain/errors.py::PROBLEM_CODES`（实测 **20** 码）对撞 ⇒ **未注册码 0 个** ✅（D-019：无发明码）

## 5. lane 自报偏差 7 项的逐条终裁

| # | lane 自报 | 编排器实测/判定 | 终裁 |
|---|---|---|---|
| 1 | HEAD 漂移：派单文 §0 记 `f105061`，开工实测 `67ba545`，gate 期间又出 `f53ff8d` | 三者均为**编排器自己的**提交（predispatch ＋ 纯台账回填），lane 只读、无权亦无从预知；`f53ff8d` 实测零代码/契约改动 | **PASS**（非 lane 过失；lane 如实记录环境行、并改用台账现值 317/112/748/13 比对，处置正确） |
| 2 | WSL `/tmp` 会话间被回收 ⇒ 首跑 manifest 丢失，辅证改持久化到**仓库外** `_tools/` | 主日志 V1–V9 全落**仓库盘**，实测 9/9 在位；仓库外工具面不污染写权闭集（§2 实测 24 条无越界） | **PASS**（处置得当：同逐字命令重跑 ＋ 源码与 sha 逐字嵌入 `commands-s8.md` §7，可复核） |
| 3 | `job-states.md` 的「触发迁移的 HTTP 样本」：T1/T3/T5/T6/T7/T8 是 worker 侧事务、**无 HTTP 面** | 与 design 的状态机定义相符（这些迁移由 worker 事务触发，不经 HTTP）；lane **未编造** HTTP 样本，改以迁移前后**全行快照**为见证 | **PASS**（如实报「无此面」优于伪造；T4 的响应体逐字内联且属同一采集批） |
| 4 | `http/*.json` 只存**纯响应体**，状态码/头由文件名位 ＋ 采集报告行承载 | 与派单文 §3「真实响应体」口径一致；文件名闭集 11/11 恰含状态码位（如 `cancelJob-409.json`），`commands-s8.md` §4 有 expect/got 逐条对账（`fails=[]`） | **PASS** |
| 5 | 轮内修正两处：`problem-500` 初跑 rc=1（`TestClient` 默认 `raise_server_exceptions=True` 重抛）⇒ 改按既有冻结面同口径 `False`；台账构建器 env 行截取 bug | 前者是**照既有冻结面**（`tests/unit/test_api_app.py`）对齐，非放宽期望；后者是 lane 自有工具的 bug，已修复重建。**两处均主动如实报**，未隐瞒 | **PASS**（loop engineering 自迭代正常收敛，2-of-2 未超限） |
| 6 | jobs 路由面上现存代码**无法真实触发 500**；500 样本取自既有行为（`create_app` 未注入 `health_service` → deps 显式 `RuntimeError`） | 实测 `problem-500.json` 的 `code=INTERNAL_ERROR` 属注册码；lane **未伪造**、**未改期望**，且指明了真实触发面与其既有守护 | **PASS**（诚实取证：宁可说明触发面在别处，也不造假样本） |
| 7 | 零新增仓库内 `.py`；`.log`/`.json` 不入 `RUFF_SUFFIXES` 分母；4 件新 md 已过 `ruff format --check` | 与 §3 的 V6b 实测 `321 files already formatted` 一致；`RUFF_SUFFIXES=(".py",".md")` ⇒ 20 件 `.log`/`.json` 确不入分母 | **PASS** |

**7/7 全部 PASS，零返工。**

## 6. U-1 终裁 —— **A254**

**lane 的 U-1（原文见 `lane-return-raw.md`）**：派单文 V9 的期望原文含「**且切换守卫阻断**」，
但实测（grep 全 `src` / `scripts`）`verify_artifact_index` **无任何消费者**，
`worker/integrity.py:4` 自述「判定归 M5-01，本模块只交付那把尺子」⇒「阻断动作」的主体
（备份／提升接线）在 **M0-04 面上根本不存在**。候选：(a) 维持现状（信号面＝写入侧前提，
阻断接线归 M5-01）；(b) 编排器为 M0 出口补一个消费面锚点。lane 倾向 (a)。

**裁定 A254：采纳候选 (a)。** 理由：

1. **职责边界正确**：AC-031 的 `primary_owner` 实测就是 **M5-01**（「停受理备份＋恢复至新目录＋
   运行迁移校核」的端到端复跑归它）。在 M0 出口**另造**一个消费面锚点，等于把 M5-01 的判定面
   提前到 M0，会造出**第二个真相源**（违反「禁两处各存一份」的仓内一贯口径）。
2. **本棒已交付的是「尺子」而非「判决」**：编排器实测确认四项写入侧前提全部可复核 ——
   `verify_artifact_index()` 返回空差异、注入缺件后差异清单非空且**四要素可定位**（`MISSING_FILE`）、
   `manifest_rows()` 提供清单来源、`verify_same_filesystem()` 提供同盘前提（`gates/V9.log`）。
   「据以阻断的信号已可产出」＝ M0-04 的**充分**交付面；「阻断动作」是 M5-01 的**消费**面。
3. **不降强度**：采纳 (a) 不豁免任何判据 —— AC-031 仍**必须**由 M5-01 出 PASS/FAIL，
   本棒亦**未**越权判定（§4 已实测复核）。若 M5-01 届时发现「尺子」不足以支撑阻断，
   走 CR 回到 M0-04，而不是现在预先猜测它的需要。
4. **成本纪律**：候选 (b) 需新立一棒并扩 M0-04 的写权面，而 M0-04 已是 wave-3 的**唯一解锁点**
   （21 个 TODO 在等）；为「可能的未来需要」阻塞解锁点，违反关键路径纪律（`slack=0`）。

**连带义务**：M5-01 派单时**必须**把 A254 逐字携带（含「阻断接线归你、尺子已由 M0-04 交付」的分工），
禁让 M5-01 重新发明一遍 `verify_artifact_index` 的消费者。

## 7. counts 变化与 A101 恒等式

| 键 | 上批（`67ba545` / `f53ff8d`） | 本批 | 增量 | 增量来源（逐个点名） |
|---|---|---|---|---|
| `ruff_formatted_files` | 317 | **323** | +6 | lane 的 4 件 md ＋ 编排器 `00-index.md`、`lane-return-raw.md` |
| `in_scope_py` | 114 | **114** | 0 | 本批**零** `.py` 改动 |
| `in_scope_md` | 203 | **209** | +6 | 同上 6 件 md |
| `mypy_source_files` | 112 | **112** | 0 | 零 `.py` |
| `pytest_passed` | 748 | **748** | 0 | 零新增用例（V2/V3/V4 的 13/14/19 是过滤口径、含既有，见 §3 提醒） |

- **A101 恒等式（冻结索引树口径）**：`114 py + 209 md + 0 untracked == 323 == ruff format --check 的报数`；
  由 `run_commit` 的 `expect_counts` 逐条对账，不符即 `git reset` ＋ 台账回滚。
- **不入分母的 20 件**：9 件 `gates/*.log` ＋ 11 件 `http/*.json`（后缀不在 `RUFF_SUFFIXES=(".py",".md")`）
  ＋ 编排器的 `commands-and-outputs.log` ⇒ 共 **21 件**不计入 ruff 分母（R13-X 先例实测口径）。
- **双重实证**：工作树 `ruff format --check .` 实测 **321**（仅 lane 4 件 md 落盘时），
  加编排器 2 件 md 后应为 **323**，由 `run_commit` 在冻结索引树上实跑确认。

## 8. 编排器自纠 —— **R18-9**

**失误**：编排器的 S8 回填复验脚本 `.orch_tmp/r18_vbf_s8.py` 与交付面复验脚本 `.orch_tmp/r18_s8reverify.py`
共**猜错 4 处字段路径／预期**，打印出 4 条**假 FAIL**：

1. 读 `resume.in_flight` —— 真键名是 **`resume.in_flight_agents`**（假报「S8 命中 0 处」）。
2. 读 `resume.s8_predispatch_R18` —— 真位在 **`tasks["M0-04"].s8_predispatch_R18`**（假报 keys 为空）。
3. 把 `counts.in_scope_py/in_scope_md` 当顶层键 —— 真位在
   **`counts.ruff_formatted_files_composition`** 下（顶层为 `null`，假报 counts 不符）。
4. 把「`evidence/M0/M0-04/commands.md` 必须不存在」当判据 —— 该文件是**既有已跟踪件**、
   正是 A253 的冲突源（详见 §2 的澄清框）。

**后果**：若直接采信初版脚本，编排器会把一次**完全正确**的回填与一次**完全合规**的 lane 交付
误报为 RED，进而触发无谓的返工或（更糟）为「消除红灯」而去动本不该动的台账。

**根因**：违反 **PRE-29 的同一精神** —— PRE-29 禁的是「采信二手复述而不回源」，
编排器这里犯的是**同型错的镜像**：「不先实测台账的真实结构，就按想象的键名写断言」。
断言的**期望值**本身也是一种口径，同样必须回源。

**纠正措施（本批一并落地）**：
- 改为 `.orch_tmp/r18_vbf_s8c.py`：先 dump 真键名与真结构，**再**按真路径断言 ⇒ 6 类回填目标
  **全部 PASS**（`dispatch_log[-1]` / `in_flight_agents[lane=S8]` / `round18_predispatch_S8.baseline_at_dispatch.head` /
  `baseline_authoritative.current+history[-1]` / `tasks[M0-04].s8_predispatch_R18` / 本键自身 `status=DONE`）。
- 新立 **PRE-30（断言期望值回源义务）**：任何复验／对撞脚本在写 `assert` 或 `ck(...)` 之前，
  **必须先实测被断言对象的真实结构**（键名、层级、类型），并把该实测命令与输出留档；
  **禁**凭记忆或凭文档复述拼字段路径。凡打印 FAIL，**必须先排除「探针自身字段路径错」**再判定对象有缺陷。
- 错误原文（含 4 条假 FAIL 的完整输出）在 `commands-and-outputs.log` 中**逐字保留、不删改**（D-011）。

## 9. 护栏如实报（**两项仍未达标；禁为达标而降档**）

| 护栏 | 目标 | 本批后实测 | 判定 |
|---|---|---|---|
| ① `flash_share_tasks` | ≥ 0.60 | 见台账 `budget.flash_share_tasks`（程序化重算，非手填） | **未达标** |
| ② `flash_share_tokens` | ≤ 0.35 | 见台账 `budget.flash_share_tokens` | **未达标／不可判**：token 读数持续为 `null`（运行环境未向 agent 暴露计数接口，lane 亦如实报「未报」，见 `lane-return-raw.md` 的 `TOKEN_USAGE`）⇒ 分母无实测来源，**FU-61 仍 OPEN** |
| ③ `flash_share_dev_lanes` | 参考项 | 见台账 `budget.flash_share_dev_lanes` | 参考 |

**如实声明**：本批 S8 是 flash 棒，理论上应**改善**护栏①；但改善幅度取决于程序化重算的分母
（`subtask_log` 47→48）。编排器**不会**为了让护栏变绿而把任何后续棒次降档 —— 
档位只按**实测复杂度**定（手册 §15.5 / A234 的降档回路），护栏数值一律如实上报。
护栏②在 FU-61 闭合前**冻结为「不可判」**，禁填推算值冒充实测。

## 10. 本批的 DAG 后果 —— **M0-04 DONE ⇒ wave-3 开闸**

- `tasks["M0-04"].status`：`IN_PROGRESS` → **`DONE`**（8 棒全部落地：S1 / S2a / S2b-1 / S2b-2 /
  S3 / S4 / S5 / S6 / S8；其中 S2b-* 属 M2-01，禁混淆 —— 见台账 `subtask_progress_note_R16`）。
- **M0-04 是 wave-3 的唯一解锁点**，实测 **21 个 TODO 任务**依赖它 ⇒ 本批入库后 wave-3 具备开闸条件。
- **开闸前必须先处理的 FU**（台账实测）：`FU-50` / `FU-52` / `FU-53` / `FU-58` / `FU-59` / `FU-60` / `FU-61`。
  其中 `FU-53`（`check_if_match` 字面量收敛，需 `common.py` 写权）与 `FU-60`（activities 裸装配 404 守护）
  **与 M2-01/S4 直接相关**，须在 S4 入库批前后明确归属，禁悬空。
- 并行安排：`M2-01/S4` 的派单文已备好（`orchestrator/handoff/R18-lane-M2-01-S4.md`），
  其写权面（`api/rules.py` 新建 ＋ `app.py` ≤3 行）与本批（`evidence/M0/**`）**完全不相交**
  ⇒ 依 PRE-5 三判据（写集不相交 ＋ 无单向依赖 ＋ 被依赖符号成员面已可用：`RuleService` 7 成员、
  `get_rule_service`、规则族 16 个 DTO 全部 `inspect` 实取在位）判 **可并行**。
- **S4 的预期红清单已实测锁定**（E1 `test_s3b_routes.py:220`、E2 `test_s2b2_app_injection.py:275/280`），
  按 A245 / A248 先例，守护迁移归**编排器**在 S4 入库批同批做，lane 禁改 `tests/**`。
## 1bis. 文本卫生（normalize）造成的 face 差异 —— **如实登记双 face，禁掩盖**

`scripts/orch_harness.py::run_commit` 的第 1 步是**文本卫生**（BOM / CR / 尾换行），它对 ADD 全集生效。
实测（`.orch_tmp/r18_norm_s8.py`，输出留档于 `commands-and-outputs.log` §8）：27 件中**恰 11 件**被修正，
修正类型**全部**是 `TRAILING_NL_ADDED`，即「补一个末尾换行符」⇒ **每件 +1 字节、内容零改动**。

被修正的 11 件正是 `http/*.json`：lane 采集时写入的是**纯响应体单行、无末尾换行**
（其自报行数为 `0` 即由此而来，见 §1 的口径澄清）。仓内其余 16 件（4 md ＋ 9 log ＋ 编排器 3 件）
**face 未变**，即 lane 与编排器交付时已符合尾换行卫生。

| 文件 | lane 自报 face（bytes / sha256[:12]） | 入库 face（normalize 后） | 差异 |
|---|---|---|---|
| `listJobs.json` | 927 / `66bbe5754511` | 928 / `cb29c66a470d` | +1 字节 |
| `getJob.json` | 296 / `c0bd18d44a34` | 297 / `6641c6d76f29` | +1 字节 |
| `cancelJob-200.json` | 297 / `51f0689a3b5a` | 298 / `2f0518e6d610` | +1 字节 |
| `cancelJob-409.json` | 248 / `6df6b49f6bac` | 249 / `f74b26fc9668` | +1 字节 |
| `cancelJob-412.json` | 229 / `65c2f7c5a3fd` | 230 / `5caf43c34fe0` | +1 字节 |
| `cancelJob-428.json` | 245 / `d9686d113283` | 246 / `b1c76ad079ed` | +1 字节 |
| `retryJob-202.json` | 327 / `305bbb8926d3` | 328 / `1fef1e910c56` | +1 字节 |
| `retryJob-429.json` | 305 / `07afd740f7c7` | 306 / `b15bd870a75a` | +1 字节 |
| `problem-404.json` | 254 / `a8d41d2445ad` | 255 / `19697edeacc9` | +1 字节 |
| `problem-422.json` | 360 / `225adf278af5` | 361 / `64a3b557796e` | +1 字节 |
| `problem-500.json` | 230 / `1cac23746307` | 231 / `58d1bf5e57c8` | +1 字节 |

**判定**：该差异**不是** lane 的偏差，也**不是**内容改动，而是仓库既有的文本卫生规则在入库时的统一施加
（与 R18-landS6 批「post-format faces」的处置同口径）。因此：

- §1 的「24/24 bytes 与 sha 逐字相符」结论在**采集时点**成立且**不被推翻** —— 它证明 lane 未篡改、未漏交；
- 台账 `face_orchestrator_measured` 一律入**normalize 后**的值（即 `run_commit` 冻结索引树上的实际字节），
  因为那才是**入库后**可复现的 face；两值同时留档于此，禁只留一个。
- 驱动 `r18_land_s8.py` 的 `FACE` 字典取自 `.orch_tmp/s8_face.json`（normalize 后实测），
  preflight 会逐件复测并断言相等 ⇒ 若入库前文件再被改动，preflight 立即 RED、零副作用。
