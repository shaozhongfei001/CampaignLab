# R19-CHECKPOINT · CampaignLab SDD 长程无人值守 DAG · 断点续跑单一真相源

> **本文件的用途**：会话/进程/操作系统被中断后，接管者（可能是**另一个模型实例**）**只读本文件 ＋ `orchestrator/state.json`** 即可无损续跑。
> **纪律**：接管者**禁采信本文件的任何读数**（PRE-29）——所有 sha、counts、哨兵、护栏比值**必须重新实测**，本文件只告诉你「去哪里实测、实测什么、期望是什么」。
> **口径**：append-only（D-011）。本文件登记的是 **Round 19 · S5 predispatch 批之后**的状态。

---

## 0. 锚点（A261：一律以 **sha** 为锚，禁写 tag —— `git tag -l` 实测 0 项，tag 只是提交信息首行的名义锚点）

| 项 | 值（接管后必须用 `git rev-parse` 逐字复验） |
|---|---|
| 仓库 | WSL2 `/home/szf/dev/CampaignLab`（Windows 侧 `\\wsl.localhost\Ubuntu\home\szf\dev\CampaignLab`） |
| 分支 | `m0-framework` |
| 远端 | `git@github.com:shaozhongfei001/CampaignLab.git` |
| **HEAD** | **`fe3bed7`** / `fe3bed7a071a19985607d2ecd423fc90feb9f2d4` |
| origin/m0-framework | **与 HEAD 相同**（已 push，实测 `0765099..fe3bed7`） |
| 工作树 | **干净**（`git status --porcelain` 实测 0 行） |
| HEAD 的提交 tag | `R19-predispatch-S5` |
| 上一批 | `0765099`（`R19-backfill-S8S4land`，纯台账） |
| 再上一批 | `4514de4`（`R18-landS4`，M2-01/S4 交付入库） |
| 宿主 | Win11 ＋ PowerShell，cwd `D:\ws\codex_rd\ss_campaignlab`，暂存区 `.orch_tmp\` ↔ `/mnt/d/ws/codex_rd/ss_campaignlab/.orch_tmp/` |
| Python | **3.14.10**（`uv` 管理）。**禁**系统 python3（3.12.3 在 PEP 758 上崩）⇒ 一律 `uv run --no-sync python` |
| counts（**冻结索引树**口径，四门实测背书） | **329 / 113 / 750**（115 py ＋ 214 md） |
| 本 checkpoint 批之后应为 | **330 / 113 / 750**（115 py ＋ **215** md）—— 只 +1 md（本文件），py/mypy/pytest 三项**逐字不变** |

**每个 runner `.sh` 的固定前两行（禁省略）**：
```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
cd /home/szf/dev/CampaignLab
```

---

## 1. 本回合（Round 19 · 第 2 段）落地了什么

**唯一提交**：`fe3bed7`（tag `R19-predispatch-S5`），入库 2 件：
1. `orchestrator/handoff/R19-lane-M2-01-S5.md` —— **424 行 / 48257 B / sha256[:12] `c3ff2c257573`**（M2-01/S5 的派单契约，10 节）
2. `orchestrator/state.json` —— run_commit 自动追加

**四门实测（冻结索引树，全部 rc=0）**：
- `ruff_format`：**329** files already formatted
- `ruff_check`：All checks passed!
- `mypy`：Success: no issues found in **113** source files
- `pytest_frozen`：**729** passed（＋ `GIT_ENV_IGNORES` 静态收集 **21** ＝ **750**），223.51s
- 提交后工作树 `post_status_lines=0`

**台账面（11 步）**：
- ① **兑现 R19 的 7 处哨兵**（PRE-35 全量普查：`round19_self_corrections[R19-1/R19-2]` 4 处 ＋ `round19_resume` 2 处 ＋ `commit_backfill_pending_R19.status`）⇒ 全部回填为 `0765099`，普查前后**集合相等**、零陈旧。
- ② counts 328/113/750(115+213) → **329/113/750(115+214)**，**top-level 与 composition 两处镜像同批写全**并断言逐项相等（R19-5 的修正面）。
- ③ 新建 `resume.round19_predispatch_S5`（镜像 `round18_predispatch_S4` 的全部 11 键；`preconditions_checked` 含 **PRE-13~18/21/24~27/29~37 共 20 项**逐项留痕）。
- ④ 新建 `resume.round19_adjudications` ＝ **A262–A268**（7 条终裁，派单文 §5 逐字携带）。
- ⑤ `dispatch_log` 17→**18**、`in_flight_agents` 10→**11**（**PRE-32 全新构造**，禁深拷贝；未定值一律 `None`）。
- ⑥ `budget.dispatched_not_yet_returned` 0→**1**；**PRE-36** 重算 flash_share（无新样本 ⇒ 三比值逐项不变）。
- ⑦ `tasks['M2-01'].s5_predispatch_R19` ＋ `subtask_progress['S5']` = IN_FLIGHT。
- ⑧ `baseline_authoritative.current` 翻新（旧 `head_note` 移存 `head_note_pre_R19_S5pd`，D-011 不改写）＋ `history` append **[19]**。
- ⑨ 新建 `resume.commit_backfill_pending_R19_S5`（含 `sites_expected_breakdown` 与 `assignment_point_reconciliation_PRE37`）。
- ⑩b/⑩c/⑩d 自纠 **R19-3 / R19-4 / R19-5** 入账（`round19_self_corrections` 2→**5** 条）＋ `resume.preconditions_added_R19_S5pd` 登记 **PRE-37（两款）＋ PRE-36 第 2 款**。
- ⑩ `next_actions` append R19-S5pd 段（9 条）。
- ⑪ **末断言**：`sentinel_paths(state) == EXPECT_SENTINELS_AFTER`（**21** 处，逐字**集合相等**、非包含）且与已兑现的 7 处**零交集** ⇒ 提交后复验实测 **21/21 True、R19_DUE 残留 0**。

---

## 2. 本回合的三次「提交前被门拦下」（全部零副作用、零数据损失；如实登记，禁粉饰）

| id | 严重度 | 拦下它的门 | 事实 | 根因 |
|---|---|---|---|---|
| **R19-3** | MINOR | `mut()` 的**末断言**（PRE-35） | 哨兵实测 **15** 处 vs 常量期望 **13** 处，差集＝`tasks['M2-01'].s5_predispatch_R19.commit/.commit_full` | 同一份 predispatch 记录在台账里有**四处镜像**（`round19_predispatch_S5` / `dispatch_log[17]` / `in_flight_agents[10]` / `tasks[...]s5_predispatch_R19`），枚举时按记忆罗列、漏了 task 级那一处 |
| **R19-4** | MINOR | 同一道末断言（第二跑） | 实测 **19** vs 期望 **17**，差集＝R19-3 修正版新加的 `sites_expected_breakdown.*.sentinel_literal` 两个键 | **哨兵字面量是污染性数据**：`sentinel_paths` 是纯字符串**相等**判据，把字面量当**描述性值**原样落盘 ⇒ 被计成 2 处**永不可回填的伪哨兵**（风险高于 R19-3：真哨兵下批实扫可补，伪哨兵会永久污染此后每次普查） |
| **R19-5** | MINOR（**成本最高**） | `run_commit` 的 **drift 门**（第三跑，四门全绿**之后**） | `台账 counts != 实测 {'in_scope_md': (213, 214)}`；白跑一整轮冻结树门禁 ≈ **2.9 分钟** | `counts` 的 `in_scope_py`/`in_scope_md`/`total` 有**双份镜像**（top-level 与 `ruff_formatted_files_composition`）；沿用的既有辅助函数 `set_counts_view`（`.orch_tmp/r17_s2b2_commit.py:114`）只写 top-3 ＋ composition，**从不写 top-level 那三项**，而 drift 门读的正是 **top-level** |

**由此新立/增补的立法（全文在 `round19_self_corrections[*].prevention`）**：
- **PRE-37 第 1 款（哨兵清单的赋值点回源义务）**：清单**必须**由「mut 内每一处对哨兵字面量的赋值点」反推，**禁**凭记忆或凭上一批清单增删；条目与赋值点**一一对应**（禁「无源之条」，禁「无条之源」）。
- **PRE-37 第 2 款（哨兵字面量的污染性约束）**：禁把字面量原样写进任何**描述性**字段（note/breakdown/to_backfill/prevention 正文）；指称时一律用「含子串但**不相等**」的形态或指向源码常量名。推论：任何扫描哨兵的机器守护（FU-62）必须同时给出「合法引用位置」白名单口径，否则会把自己的说明文本判成待办。
- **PRE-36 第 2 款（镜像读数的全键显式赋值义务）**：凡同一读数存在**多份镜像**（本仓已实测两处：`counts` 的 top-level vs composition；`baseline_authoritative.current` 的 counts 五项 vs `history[-1].counts_snapshot`），写入时必须**同批写全每一份**并**当场断言逐项相等**；**禁**依赖辅助函数「顺带」写全 —— 复用前必须 `inspect.getsource` 回源核对它**实际写了哪些键**。另：机器守护必须覆盖 `total` 这类**不在 drift 门 5 键内**的镜像键（否则可长期不同步而无人判红）。
- **附带实证**：分组求和自证**两次算错**（首版「8×2＋1×1＋2×2」＝21 而分组数写 9，自相矛盾；修正版在 R19-5 入账后未把 10 组/19 条同步为 11 组/21 条），**都由 preflight 的 P18e 判红拦下** ⇒ 连「自证算式」本身也必须被机器核对，禁当注释写。
---

## 3. DAG 状态（接管后必须从 `orchestrator/state.json` 重新实测，禁采信下列数字）

| 维度 | 实测值（于 `fe3bed7`） |
|---|---|
| 任务总数 | **29** |
| 状态分布 | `DONE` **4**（M0-02 / M0-03 / M0-04 / M0-P01）· `PASS_WITH_TODO` **2**（M0-01 / M0-03b）· `IN_PROGRESS` **1**（M2-01）· `TODO` **22** |
| 波次 | **11**（`st['waves']`）；`st['wave']` = 2，`st['phase']` = M0，`st['dag_paused']` = **False** |
| 关键路径 | **14** 个任务：M0-01 → M0-02 → M0-04 → **M1-01** → M1-02 → M3-01 → M3-02 → M3-03 → M4-01 → M4-02 → M4-03 → M5-01 → M5-02 → M5-03 |
| 关键路径已走完 | **3 / 14**（M0-01 PASS_WITH_TODO、M0-02 DONE、M0-04 DONE）⇒ 下一个关键路径任务＝**M1-01** |
| AC 分母 | **47**（baseline 35 ＋ monthly 12；`st['acceptance']`） |
| defects | **52** 条，末条 **D-052** |
| followups | **62** 条，末条 **FU-62**；未关闭 **53** 条（含 FU-50/51/52/53/54/55/56/57/58/59/61/62） |
| self_corrections（R19） | **5** 条（R19-1 … R19-5） |
| adjudications | `round18_adjudications` 末条 **A261**；`round19_adjudications` 末条 **A268** |

**READY 集（依赖齐备且未开始）＝只有 `M1-01`**，且它在**关键路径**上（slack=0）。
- `M1-01`：lane **D**、tier **`qwen3.8-max`**、wave-3 L1、deps `[M0-04]`（已 DONE）、与 M2-01 **可并行**（`waves[3].note` 明写写权面不相交）。
- 派单前置件 `orchestrator/handoff/M1-01.slice.json` 实测**已存在**。
- **但 M1 族被 `FU-59` 卡住**（wave-3 开闸另需 `FU-53`）：`api/common.py` 的 `IF_MATCH_PATTERN` 解冻 —— 常量定义必须落在**真实源模块**（common.py 按其纯转发纪律只转发，见 `api/common.py:22-25`），并替换 `api/jobs.py:216`、`api/jobs.py:300`、`api/activities.py` 的 `update_activity` 三处内联字面量，另加机器哨兵。该批**需要 common.py 写权** ⇒ 必须是**编排器自办的专门解冻批**。
- wave-3 开闸治理簇：**FU-50 / FU-52 / FU-53 / FU-58 / FU-59 / FU-62**（FU-61 保持 OPEN 并冻结护栏② 为不可判）。

**M2-01 内部进度**（`tasks['M2-01'].subtask_progress`）：
`S1` `S2a` `S2b`(拆为 `S2b-1`/`S2b-2`) `S3` `S4` ＝ **DONE**；`S5` ＝ **IN_FLIGHT（predispatch 已入库、尚未 spawn）**；`S6` `S7` ＝ 未开。
按 8 个名义棒（S1/S2a/S2b/S3/S4/S5/S6/S7）计：**5 DONE ＋ 1 已派单 ＋ 2 TODO**。
**禁**在 S7 入库前判 M2-01 DONE（**AC-002 / AC-003 / AC-004 的判定在 S7**）。

**S6 / S7 的必携义务**（权威原文在 `tasks['M2-01'].remaining_sequence_R18_post_S4` 的 `S6_must_carry` / `S7_must_carry`）：
- S6：`tests/api/activities/**` 只新建；必须逐字携带 **A257** ＋ **A260** ＋ **FU-54** ＋ design §3.2 的 `set_current_rule` **SQL 原文**（行 310–314）＋ **A232**（specific 覆盖 general 的 SQL 谓词，禁补 guard 镜像）＋ **A256 ＋ D-052 §9**（`_rule_check_response` 透传的正确理由＝校验点在应用层 `activity_service.py:1925`，**禁**再抄「类型上不可达」）；卡片三个 gate 字面量必须命中：`-k etag412`、`-k dup_external`、`-k rule_diff`；**禁改** S3 的 `api/activities.py` 与 `tests/api/activities/test_activities_router_s3.py`。
- S7：取证面（M2 目录下的 M2-01 子目录 ＋ clauses.md ＋ gates ＋ summaries 下的 M2-01.md），闭合 **4** 条前向引用；**判 AC-002/003/004**。
- **窗口期风险（如实）**：在 S6 入库前，「7 条 rules 路由面与活契约的逐 op 对撞」与「实现返回的运行期状态码」**均无仓内守护**；现有守护只覆盖挂载面（FU-60）、import 面（A259）与声明面（A258）。

---

## 4. M2-01/S5 的当前状态（**关键：predispatch 已入库，但 spawn 尚未发生**）

| 项 | 值 |
|---|---|
| lane / task / round | **S5** / **M2-01** / **19** |
| 派单文 | `orchestrator/handoff/R19-lane-M2-01-S5.md`（**424 行 / 48257 B / sha256[:12] `c3ff2c257573`**） |
| model / reasoning | **`qwen3.8-flash`** / **medium**（卡片 `orchestrator/tasks/M2-01.md:46` 原文冻结；budget 8k；loop 帽 **2**） |
| critical / slack | false / 4（**但**是 M2-01 必经棒，S7 判 AC 需要它 ⇒ **不得跳棒**） |
| 写权面 | **9 件全新建**：`tests/domain/__init__.py`（**A262 授权**的唯一越卡片字面量件）、`tests/domain/activity/__init__.py`、`test_states.py`、`test_clause_gate.py`、`test_digest.py`、`test_bindings.py`、`test_checks.py`、`test_diff.py`、`test_layering.py` |
| 只修改 | **无**（`numstat deleted` 必须全 0） |
| 预期红清单 | **空**（编排器实测：AST 实取既有 **594** 个用例名与派单文 §6.1 的 **40** 个新名集合对撞 ⇒ 交集 **0**） |
| 携带裁定 | **A262–A268** ＋ 承前批 A232 / A256 / **A257**（rules 的 7-op 契约对撞归 **S6** ⇒ S5 **禁写任何 HTTP/路由/状态码断言**）/ A261 / D-052 §9 |
| 台账状态 | `dispatch_log[17]` 与 `in_flight_agents[10]` 的 `status` ＝ `PREDISPATCH_COMMITTED_AWAITING_SPAWN`；`agent_id` / `nickname` / `tier_used` / `spawned_at` / `result` / `slot_closed_at` 一律 **None**；`spawned_after_predispatch` ＝ **False** |
| `budget.dispatched_not_yet_returned` | **1** |
| **PRE-31 双键警告** | 仓内**已有** `lane=='S5'` 属 **M0-04**（`in_flight_agents[4]` / `dispatch_log[11]`，昵称 Kierkegaard，RETURNED_LANDED @R17）⇒ 定位本棒**必须**用 **(lane='S5', task='M2-01')** 双键，**禁**按 lane 单键查找 |

**⚠ 关键未完成动作：`spawn_agent` 尚未调用。** PRE-13 只走完第①步（派单文入库）。第②③步待做：
- **第②步**：`spawn_agent`，**必须显式**指定 `model="qwen3.8-flash"` 与 `reasoning_effort="medium"`（**禁**省略 model ⇒ 否则会静默继承父模型，违反手册 §15.1 与 A234 的档位纪律），message 逐字指向派单文路径。
- **第③步**：**纯台账回填批** —— 写 `agent_id` / `nickname` / `spawned_at` / `agent_id_backfilled_at` / `tier_used`、`spawned_after_predispatch` False→**True**、`status` →**IN_FLIGHT**，并把 predispatch 提交 sha `fe3bed7` 回填到全部相关键。

> **本 checkpoint 批已代为完成第③步里「sha 回填」的部分**（见 §6），剩下的**只有** spawn 相关的 6 个字段 ＋ 状态迁移；该义务已**显式重新递延**并登记为 `resume.commit_backfill_pending_R19_S5_spawn`。

---

## 5. 续跑 runbook（严格按序；每步都要先实测再动手）

**第 0 步 · 接管自检（禁跳过，全部实测）**
```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
cd /home/szf/dev/CampaignLab
git rev-parse HEAD origin/m0-framework     # 期望：两者相同
git rev-parse --abbrev-ref HEAD            # 期望：m0-framework
git status --porcelain                     # 期望：0 行（干净）
git log --oneline -3
uv run --no-sync python -c "import sys;print(sys.version)"
```
再用一段 Python 实测台账：counts 五项、`sentinel_paths(state)` 的全量普查、`dispatch_log` / `in_flight_agents` / `subtask_log` / `defects` / `followups` 的长度与末条 id、`budget.flash_share_*` 三比值与 `recompute_flash_share(subtask_log)` 的重算值是否逐项相等（**PRE-36**）。
**期望（本 checkpoint 批入库后）**：HEAD ＝ 本 checkpoint 提交的 sha；counts ＝ **330 / 113 / 750（115 py ＋ 215 md）**；哨兵**恰 10 处**（构成见 §6 的「本 checkpoint 批自身新增的 9 处」＋ 1 处 spawn 义务），且义务方**唯一**＝「spawn 之后的第一次纯台账提交」；`dispatch_log` **18** 条；`in_flight_agents` **11** 条；`subtask_log` **49** 条；`dispatched_not_yet_returned` **1**；`defects` **52**（末 D-052）；`followups` **62**（末 FU-62）；`round19_self_corrections` **5** 条；`round19_adjudications` **7** 条（A262–A268）。

**第 1 步 · spawn M2-01/S5**（见 §4 的第②步；显式 model/reasoning，记录返回的 agent_id 与 nickname）

**第 2 步 · 纯台账回填批**（PRE-13 第③步 ＋ PRE-35 全量普查）：兑现 `commit_backfill_pending_R19_S5_spawn` 的 1 处哨兵与 6 个字段；counts **五项逐字不变**。

**第 3 步 · S5 在飞期间并行**（写权面不相交，PRE-5 三判据）：落 **FU-59 的 `api/common.py` 专门解冻批**（编排器自办）。
> ⚠ 该批会动工作树，而 S5 正在 `tests/domain/**` 写 9 件**未跟踪**文件 ⇒ **必须**给 `run_commit` 传 `untracked_owner_map`，把这 9 件归属到 `(S5, M2-01)`，否则 A144(c) 会判「越界未跟踪件」而拒绝提交。
> ⚠ 该批**不动** `domain/activity/**`、不动 `canonical_json`、不动 `tests/**`（派单文 §0 已把这条并发提示逐字告给 lane）。
> ⚠ 若该批推进了 HEAD，S5 复测 HEAD 时会发现 sha 变了 ⇒ lane 应按派单文 §8 报 **U-BASELINE**；派单文已明写这是预期行为、**无需** lane 改动任何东西。

**第 4 步 · prepare ＋ predispatch `M1-01/S1`**（**关键路径**，slack=0）：先确认 `FU-59` 已落地、`orchestrator/handoff/M1-01.slice.json` 存在，再写派单文（tier **`qwen3.8-max`**）→ predispatch 提交 → spawn → 回填。

**第 5 步 · S5 回收**：编排器**独立复验**（PRE-29，**禁采信自报**）——
face 三件套逐件；AST 实取 40 个用例名与 §6.1 逐字对撞；`git diff --numstat` 9 件**全 deleted=0**；硬禁面 0 行改动；全量 pytest 的**净新增 collected**（禁把 `-k` 过滤计数当增量）；PC-A..PC-E **亲自重做**并区分 `rc=4`（收集期）与 `rc=1`（断言红）；分层守护自身有牙。
→ 一任务一提交（`run_commit`）→ push → 纯台账回填。

**第 6 步 · S6 → S7**（必携义务见 §3）→ **判 AC-002/003/004** → 才可判 M2-01 DONE。

**第 7 步 · wave-3 开闸治理簇**：FU-50 / FU-52 / FU-53 / FU-58 / FU-62（**FU-62 ＝ 哨兵陈旧度 ＋ 派生比值 ＋ 镜像一致性的机器守护，P1，开闸前必须落地**）；FU-61 保持 OPEN。

**第 8 步 · M1-01 → M1-02 → M3-* → M4-* → M5-***（关键路径 11 个任务），并按 `waves` 的并行度铺开非关键路径任务。

**第 9 步 · 循环直至 29 任务 / 11 波 / 47 AC 全部交付并留证。未全部完成不得停（用户死命令）。**
---

## 6. 哨兵与待兑现义务（PRE-35 / PRE-37 的权威清单）

**本 checkpoint 批入库前**（即 `fe3bed7` 的状态）：哨兵 **21** 处，构成如下（`sentinel_paths` 实测，与 `resume.commit_backfill_pending_R19_S5.sites_expected_after_mut` 逐字相等）：
- **15 处** `PENDING_BACKFILL_AFTER_SPAWN`（10 组赋值点 ×2 － 1 ＋ pending 键 status ×1）：
  `baseline_authoritative.current.head/.head_full`（2）· `history[19].head/.head_full`（2）· `history[19].counts_snapshot.head/.head_full`（2）· `dispatch_log[17].commit/.commit_full`（2）· `in_flight_agents[10].commit/.commit_full`（2）· `round19_predispatch_S5.predispatch_commit/.predispatch_commit_full`（2）· `tasks['M2-01'].s5_predispatch_R19.commit/.commit_full`（2）· `commit_backfill_pending_R19_S5.status`（1）
- **6 处** `PENDING_BACKFILL_BY_NEXT_LEDGER_ONLY_COMMIT`：`round19_self_corrections[2]/[3]/[4]`（＝R19-3 / R19-4 / R19-5）各自的 `.commit/.commit_full`

**本 checkpoint 批做的处置**：
1. 上述 **21 处全部回填**为 predispatch 提交的实测 sha **`fe3bed7`**（全 `fe3bed7a071a19985607d2ecd423fc90feb9f2d4`）。归属实证：`git show --numstat fe3bed7` 触及 `orchestrator/handoff/R19-lane-M2-01-S5.md`（新建）＋ `orchestrator/state.json`。
2. `commit_backfill_pending_R19_S5.status` 由哨兵改为 **`SHA_BACKFILLED__AGENT_ID_PENDING_SPAWN`**（**非**哨兵字面量 ⇒ 普查不再命中），并追加 `backfilled_commit` / `backfilled_commit_full` / `backfilled_at` / `partial_backfill_note`。
3. **显式重新递延**（PRE-35 允许的两种处置之一：同批清掉 **或** 显式重新递延并写明理由与新义务方）：新建 `resume.commit_backfill_pending_R19_S5_spawn`，其 `status` 是哨兵（**这是本批之后 10 处哨兵里唯一的「spawn 义务」哨兵**），义务方＝**spawn 之后的第一次纯台账提交**，`to_backfill` 逐条列出剩余的 **6 个字段 ＋ 1 次状态迁移**：
   - `dispatch_log[17]`.agent_id / .nickname / .agent_id_backfilled_at
   - `in_flight_agents[(S5,M2-01)]`.agent_id / .nickname / .spawned_at / .agent_id_backfilled_at / .tier_used / .mapping_verified_by
   - `in_flight_agents[(S5,M2-01)]`.spawned_after_predispatch **False→True**
   - `in_flight_agents[(S5,M2-01)]`.status 与 `dispatch_log[17]`.status 与 `tasks['M2-01'].s5_predispatch_R19`.status：`PREDISPATCH_COMMITTED_AWAITING_SPAWN` → **`IN_FLIGHT`**
   - `tasks['M2-01'].s5_predispatch_R19`.agent_id / .nickname / .spawned_at
   - 该 pending 键自身 status → **DONE** ＋ backfilled_* 三键
   **递延理由（如实）**：`spawn_agent` **尚未调用**，agent_id / nickname 在客观上**不存在**；依 A183 与 PRE-13 的「禁写猜测值」，只能先写哨兵。这不是遗漏，是**唯一诚实的做法**。
4. **本 checkpoint 批自身新增的 9 处哨兵**（本批入库了本文件 ⇒ 树变了、counts 由 329 变 330 ⇒ `baseline_authoritative.current` 必须推进到本提交，而本提交的 sha 在 mutate 时尚不存在）：
   - `resume.baseline_authoritative.current.head` / `.head_full`（2）
   - `resume.baseline_authoritative.history[20].head` / `.head_full`（2）
   - `resume.baseline_authoritative.history[20].counts_snapshot.head` / `.counts_snapshot.head_full`（2）
   - `resume.checkpoint_R19.commit` / `.commit_full`（2）
   - `resume.commit_backfill_pending_R19_checkpoint.status`（1）
   这 9 处的义务方**与第 3 项相同**（spawn 之后的第一次纯台账提交）⇒ **10 处同批兑现**，不产生第二次递延。
   **如实登记（PRE-37 第 1 款的一次现场应用）**：本清单**初版写成 7 处 / 合计 8 处**，漏了 `checkpoint_R19.commit/.commit_full`
   —— 因为该键在驱动里的写入顺序**晚于** pending 键的清单常量。修正方式**不是**去改记忆的常量，而是让 `mut()` 末尾
   以 `sentinel_paths(state)` 的**实测集合**为权威、并把实测结果**回写**进 `sites_expected_after_mut`
   （台账里已把这段来龙去脉写进 `sites_expected_note`）。**教训**：清单必须**由赋值点反推**，
   且当写入顺序与清单常量分离时，一律以**末断言的实测集合**为准。
   **注意口径**：`baseline_authoritative.current` 的 counts 五项在本批写入 **330 / 113 / 750（115 py ＋ 215 md）**，
   而 `head` 暂为哨兵 —— 在回填之前，**下一棒派单文 §0 的权威基线应读作「head ＝ 本 checkpoint 提交（回填后取值）、counts ＝ 330/113/750」**；
   若接管者需要 sha 锚，用 `git rev-parse HEAD` 实测（禁猜）。**纯台账批不推进 `current.head`**（既有惯例：`0765099` 那批就把 `current.head` 留在 `4514de4`），本批因**改了树**故必须推进。

**⚠ PRE-37 第 2 款的硬约束（写台账时必读）**：**禁**把 `PENDING_BACKFILL_AFTER_SPAWN` / `PENDING_BACKFILL_BY_NEXT_LEDGER_ONLY_COMMIT` 这两个字面量**原样**写进任何**描述性**字段（note / breakdown / to_backfill / prevention 正文等）。`sentinel_paths` 是**纯字符串相等**判据，原样落盘会被计成一处**永不可回填的伪哨兵**，永久污染此后每一次普查（这就是 R19-4）。需要指称时一律用「含子串但**不相等**」的形态（例如加前后缀说明）或指向驱动源码的常量名。

---

## 7. 工具链陷阱（全部实测踩过，逐字留档；接管者禁重新踩）

1. **`wsl -e bash -lc "…"` 会吃掉引号 / `$(…)` / `|`** ⇒ **一律**先用 PowerShell 的 `@'…'@` **单引号 here-string**（字面量，不插值）把 `.sh` / `.py` 写到 `.orch_tmp\`，再 `wsl -e bash <runner>`。写完必须 `-replace '\r',''` 去 CR（bash 不吃 CRLF），并用 `New-Object System.Text.UTF8Encoding($false)` 写（**无 BOM**）。读输出一律 `Get-Content -Encoding UTF8`。
2. **CreateProcess ≈ 32k 字符上限** ⇒ 大文件**分片写**再拼接（本批的 predispatch 驱动分 **7** 片：p1/p2/p3/p4/p4b/p5/p6 → `r19pd_full.py`，137832 B / 1565 行）。
3. **长提交必须在前台 PTY 跑**：`exec_command tty=true yield_time_ms≈30000`，再用 `write_stdin` 轮询（一次可等 120–300s）。**禁** `nohup` / 后台（会丢失门禁输出与 rc）。冻结树四门 ≈ **3–4 分钟**（本轮 pytest 223.51s）。
4. **`.Replace(old,new)` 是 .NET 一次性全量替换、不回扫**；但**禁**写 `while ($c.Contains($old)) { $c = $c.Replace($old,$new) }` —— 若 `new` 含 `old` 作子串（例如把 `{x}` 转义成 `{{x}}`）就会**死循环烧 CPU**。本回合实测踩过一次（跑飞 ≈4 分钟 CPU，已 `Stop-Process` 终止；因 `WriteAllText` 在循环之后，**文件未被写坏**）。
5. **`run_commit(tag, add_paths, msg, *, mutate_ledger, want_pytest, want_mypy, untracked_owner_map, scratch, allow_dangling, keep_scratch, expect_counts)` 的执行次序**：normalize → **mutate_ledger → dump_state** → `git add`（**自动追加** `orchestrator/state.json`，**禁**把它写进 ADD）→ 从索引导出**冻结树** → 四门（ruff_format / ruff_check / mypy / pytest_frozen，双判 rc ＋ 文本）→ `expect_counts` 对账 → **drift 门**（台账 counts vs 冻结树实测）→ A144(c) 未跟踪件归属 → 悬空引用扫描 → `git commit -F` → 复验 HEAD 已推进。
   - **门禁次序的代价**：drift 门排在四门**之后** ⇒ counts 写错会白跑 ≈3 分钟（R19-5）。
   - **失败回滚**：`_rollback` 会 `git reset -q HEAD --` ＋ `git checkout -- orchestrator/state.json`。但 **`mutate_ledger` 自己抛异常时 harness 不做还原** ⇒ 调用方**必须**用 try/except 兜底执行上述两条命令（本批驱动已内置，实测生效 3 次）。
6. **counts 有双份镜像**（R19-5）：`resume.self_check_gates_rc0.counts` 的 top-level `in_scope_py`/`in_scope_md`/`total` 与 `ruff_formatted_files_composition` 内同名键。既有辅助函数 `set_counts_view`（`.orch_tmp/r17_s2b2_commit.py:114`）**只写 top-3 ＋ composition**，drift 门读的却是 **top-level** ⇒ 凡改 counts 必须**同批写全两处**并当场断言相等。
7. **`recompute_flash_share(log)` 只返回 9 个聚合键**，**不含** 3 个比值键（`flash_share_tasks` / `flash_share_tokens` / `flash_share_dev_lanes`）也**不含** `flash_share_detail` ⇒ 比值必须**显式**赋值（PRE-36 第 1 款，R19-1 的教训）。
8. **`h.dangling_refs(paths)`** 的正则是 `(?:evidence|orchestrator|docs|contracts|scripts)/[A-Za-z0-9._@/\-]+`：入库文件里出现的这些前缀路径**必须在磁盘上存在**，否则判红。`orchestrator/state.json` 在 `DANGLING_SWEEP_SKIP` 里（不被扫）。写文档时若引用**尚未存在**的取证目录，必须走 `forward_reference_registry` 登记 ＋ `allow_dangling` 豁免，或改写措辞避开该正则。
9. **Python 3.14.10 pinned**：一切探针/pytest 走 `uv run --no-sync python`；**禁**系统 `python3`（3.12.3 在 PEP 758 上崩）。
10. **`git tag -l` 实测 0 项**（A261）：台账里的 `R18-*` / `R19-*` 只是 `run_commit(TAG,…)` 写进提交信息首行的**名义锚点**，**不是** git tag ⇒ 派单文与简报一律以 **sha** 为锚。

---

## 8. 档位分配与护栏（**两项均未达标 —— 如实上报，禁粉饰、禁为凑配比降档**）

**双档制**：高复杂度＝`qwen3.8-max`，低复杂度＝`qwen3.8-flash`。目标：`flash_share_tasks ≥ 0.60`、`flash_share_tokens ≤ 0.35`。

| 护栏 | 实测（于 `fe3bed7`） | 判定 |
|---|---|---|
| ① `flash_share_tasks` | **0.5862**（34 / 58 subtask_units） | **FAIL**（< 0.60） |
| ② `flash_share_tokens` | **0.6655**（792000 / 1190000） | **FAIL 且统计上不可判**：仅 **10 / 48** 条有计量句柄，其余 **38** 条依 **A183** 记 `null`（**禁**估算、禁取中值当精确数）⇒ 该比值只是**已知样本内**读数。**FU-61 保持 OPEN**，护栏② 冻结为「不可判」 |
| 参考 `flash_share_dev_lanes` | 0.4167（15 / 36） | 参考口径，非护栏 |

- **权威口径**＝`flash_share_tasks`（subtask_units，`units = subtask_count or 1`，**排除** `tier_used == 'orchestrator-self-served'` 的 1 条 ＝ `subtask_log[40]`）。
- `budget.guardrail_status.verdict` 里那句「0.6129 已达标」是早期 **all_lanes** 口径（19/31）的**历史留档**，分母不同、按 D-011 并存，**以本键为准**（R19-1 已纠正过一次同类失真）。
- **S5 回传后的投影**：`flash_share_tasks` 34/58 → 35/59 ≈ **0.5932**（仍 FAIL）；`flash_share_dev_lanes` → ≈ **0.4324**。
- **纪律**：编排器**不会**为达标把后续本应用 max 的棒降档，也**不会**为压占比牺牲判据强度（手册 §6.6 / A234）。达标只能靠后续棒次的**实测复杂度**本来就低来实现；若持续未达标，按手册升级给项目负责人。
- **每批义务**：程序化重算 flash_share（PRE-36：比值键**显式**赋值 ＋ 全键覆盖断言）。**禁**手填。

**档位裁定的既定事实（供后续棒参照）**：
- 锁定为 **flash** 的棒：M2-01 的 **S5 / S6 / S7**。
- 锁定为 **max** 的棒：**M1-01**（关键路径，卡片档位表原文）。
- 其余 22 个 TODO 任务按其**卡片档位表原文** ＋ **实测复杂度**逐个裁定；升档回路照 **A234**（lane 撞上裁定无法覆盖的设计冲突 ⇒ 停手报 U，由编排器裁定是否升档重派，**禁** lane 自行决定）。

---

## 9. Loop engineering（自迭代）与并发纪律

- **loop 帽**：每棒在派单文里写死（S5 ＝ **2**）。超帽即**停手回报现状**，禁硬闯；每轮必须写明「上一轮红在哪、这一轮改了什么」。
- **阳性对照（PC）必须有牙**：每条 PC 先实证「变异**形态成立**且不引入**收集期**错误」再看读数；`rc=4`（收集期 ImportError）**不等于**`rc=1`（断言红），前者**不能**当「有牙」的证据（**PRE-34**，R18-12 的两次作废 PC-B 变异即此）。做不到有牙的一律如实标 `NO_TEETH`，**禁**标 PASS。
- **禁采信自报（PRE-29）**：lane 回执的每一条都要编排器**独立重做**；`token` 用量若环境未暴露计数接口，依 **A183** 记 `null`。
- **禁靠删守护压绿**：守护变强/变红必须**修正**守护或**修正**实现，不能删除。
- **并发三判据（PRE-5）**：① 写集不相交；② 无编译期/运行期单向依赖；③ 被依赖符号已具备可用成员面。三条全 PASS 才可并行。
- **在飞污染（D-046）**：在飞 lane 的未跟踪件**不入索引** ⇒ **冻结树口径不变**；**禁**用在飞工作树的读数覆盖 `baseline_authoritative.current`。
- **一任务一提交**：一律经 `scripts/orch_harness.py::run_commit`；台账 append-only（D-011），**禁**改写历史，只能移存到 `*_superseded_*` / `*_pre_*` 键。

---

## 10. 计数器与下一个可用编号（接管后必须实测复核，禁凭此表直接用）

| 类别 | 当前末条 | **下一个可用** |
|---|---|---|
| 终裁 adjudication | **A268**（`round19_adjudications`） | **A269** |
| 自纠 self-correction（R19） | **R19-5** | **R19-6** |
| 缺陷 defect | **D-052** | **D-053** |
| 前置条件 precondition | **PRE-37** | **PRE-38** |
| followup | **FU-62** | **FU-63** |
| `dispatch_log` | **18** 条（末条 (S5,M2-01)） | 追加 index **18** |
| `in_flight_agents` | **11** 条（末条 (S5,M2-01)） | 追加 index **11** |
| `budget.subtask_log` | **49** 条 | 追加 index **49**（S5 **回传入账时**才追加，predispatch/回填批**不**追加） |
| `baseline_authoritative.history` | 本 checkpoint 批**之前** **20** 条（index 19 ＝ S5 predispatch 批）；本批 append index **20** ⇒ 之后 **21** 条 | 追加 index **21** |

---

## 11. 数据损失声明与停机授权

- **数据损失：无。** 本回合三次「提交前被门拦下」（R19-3 / R19-4 / R19-5）**全部**由 harness 的 `_rollback` 或驱动自带兜底完成 `git reset` ＋ `git checkout -- orchestrator/state.json`；每次都复验 HEAD 未动（仍 `0765099`）、工作树仍只有 1 条 `??` 派单文。第 4 次跑成功入库 `fe3bed7` 并已 **push** 到 origin（实测 `0765099..fe3bed7`，HEAD == origin）。
- **停机时的状态是自洽的**：工作树干净、HEAD == origin、台账哨兵**恰 10 处**且义务方**唯一**明确（`commit_backfill_pending_R19_S5_spawn` ＋ `commit_backfill_pending_R19_checkpoint`，两者同批兑现）、**无在飞 agent**（`spawn_agent` 尚未调用 ⇒ 没有需要 `close_agent` 的槽位、没有丢失回执的风险）。
- **停机授权**：本 checkpoint 由项目负责人（人类）明确要求「保存完整 checkpoint，确认可断点续跑后停止任务」。standing 指令「没有全部完成前不允许停，必须 DAG 开发流程全部结束」**仍然有效**，本次停止是**人类显式授权的暂停**，不是编排器自行停工；`st['dag_paused']` 的语义与 `dag_resume_authorization_R18` 同源 —— **续跑需要人类明确的「开工」指令**。
- **续跑的第一件事**：§5 的第 0 步接管自检（全部实测），然后第 1 步 spawn S5。

---

## 12. 关键文件索引（全部为**已存在**的仓内路径）

| 用途 | 路径 |
|---|---|
| 长程派发任务提示词（本工作流的宪法） | `docs/delivery/LONG-HORIZON-ORCHESTRATION.md` |
| 提交工装（四门 / 冻结树 / 对账 / 回滚） | `scripts/orch_harness.py` |
| 台账（单一真相源，append-only） | `orchestrator/state.json` |
| M2-01 任务卡（档位表原文冻结） | `orchestrator/tasks/M2-01.md` |
| M2-01 设计冻结件（1396 行；§11.6 在 1093-1134） | `orchestrator/handoff/M2-01-design.md` |
| **S5 派单契约（本回合入库）** | `orchestrator/handoff/R19-lane-M2-01-S5.md` |
| S4 派单文（S5 的结构先例，466 行） | `orchestrator/handoff/R18-lane-M2-01-S4.md` |
| M1-01 契约切片（wave-3 关键路径备料，实测已存在） | `orchestrator/handoff/M1-01.slice.json` |
| D-052（design §11.5/§11.6 的口径失真单，§9 是 R18-11 的更正附录） | `orchestrator/defects/D-052.md` |
| lane 通用纪律（loop 帽 / 禁 commit&push / 回执结构） | `orchestrator/handoff/LANE-COMMON.md` |
| 编排器暂存区（驱动脚本、探针、门禁输出留档；**非仓内**） | `.orch_tmp/`（宿主 `D:\ws\codex_rd\ss_campaignlab\.orch_tmp\`） |
