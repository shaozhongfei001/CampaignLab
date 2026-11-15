# R17-CHECKPOINT —— 长程无人值守 DAG 断点续跑检查点（主机重启前冻结）

冻结时刻：2026-11-15T09:51:20+08:00（HEAD `97fc9d9`；Round 17 两条 lane 全部落地、sha 全部回填、并发槽全部释放）。
冻结原因：**主机（Win11）计划重启操作系统**。子智能体进程与编排器会话随重启必然消亡，故在其之前把已完成工作**入库并推送**、把全部账本事实**冻结**、把进度口径**如实测定**、把续跑剧本**写死**。
本件是续跑的**权威入口**，与流程规范 `docs/delivery/LONG-HORIZON-ORCHESTRATION.md` 配合使用；账本真值以 `orchestrator/state.json` 为准，本件是其可读索引与恢复剧本。前一次同类检查点为 `orchestrator/handoff/R14-CHECKPOINT.md`（体例沿用）。

## 0. 30 秒速览（续跑者先读这段）

- **本次重启零数据损失、零重派**：`dispatched_not_yet_returned = 0`，**无在飞 lane**。Round 17 的两条 lane（M2-01/S2b-2 → `87c897a`、M0-04/S5 → `d36e214`）均已落地、sha 均已由纯台账提交回填（`50be48f` / `97fc9d9`）、两个并发槽均已 `close_agent` 释放。**与 R14 的关键差别**：R14 有一个零落盘的在飞件（M2-01/S2a）必须重派，本次没有。
- HEAD 冻结点 = `97fc9d9fa9549c863b534e2b9d685251c2f6c6f2`（**117 commits**），分支 `m0-framework`，**已 push 到 origin**（`origin/m0-framework == 97fc9d9`），工作树干净（`git status --porcelain` 为空、无未跟踪件、无 stash）。
- 四门实测（**冻结索引树**口径，`97fc9d9`）：ruff_format = **301** files already formatted（in_scope_py **109** + in_scope_md **192**）/ ruff_check = All checks passed / mypy = **107** source files / pytest = **734**（**713** frozen 实跑 + **21** GIT_ENV_IGNORES 静态收集）。
- **任务级完成度 5/29 = 17.2%**；含在飞链子任务级推进的**如实总体口径 ≈ 21.6%（取 22%）**，推导见 §3。
- **AC 口径 2/47 = 4.3%**（严格 primary_owner 判据）。AC 闭合率远低于代码完成率是**结构性**的、不是缺陷：47 条 AC 中 41 条的 primary_owner 属 TODO 任务、4 条属 IN_PROGRESS 任务。详见 §3.3。
- **护栏双双未达标（如实报告；禁为凑配比而降档或补造工作，手册 §6.6 / C10）**：flash_share_tasks = **0.5556**（目标 ≥ 0.60）、flash_share_tokens = **0.6655**（目标 ≤ 0.35）、flash_share_dev_lanes = **0.3438**。详见 §5。
- 缺陷面：**无 blocking 缺陷**（逐条实测 `blocking` 字段，命中 0 条）。49 条中 CLOSED 22 / FIXED_PENDING_Q 18 / OPEN 9。
- `dag_paused = true`。**续跑必须等人类明确「开工」指令**；runbook 见 §10，首个派单见 §11。

## 1. 铁律（违反＝静默腐化或假红；续跑者原样继承）

R14-CHECKPOINT.md §1 的 9 条**逐条仍有效**，原样继承。下列为本会话新增或需再强调者。

1. **仓库位置**：WSL2 `/home/szf/dev/CampaignLab`，分支 `m0-framework`，远端 `git@github.com:shaozhongfei001/CampaignLab.git`。宿主 Win11，PowerShell cwd `D:\ws\codex_rd\ss_campaignlab`；scratch `.orch_tmp\` ↔ `/mnt/d/ws/codex_rd/ss_campaignlab/.orch_tmp/`。
2. **解释器口径（R14-1，本会话再次踩中）**：项目钉死 Python **3.14**。**系统 `python3` 是 3.12，无法解析仓库源码**（`except A, B:` 属 PEP 758，3.14 才合法；全仓两处，均在 `src/campaignlab/api/common.py`）。一切 AST / 语法 / 导入 / pytest 探针必须走 `uv run --no-sync python`。仅读 `orchestrator/state.json`（纯 JSON）这类不碰仓库 .py 的脚本可用系统 python3。
3. **写文件通道（唯一合法形态）**：PowerShell 单引号 here-string → `-replace "`r`n","`n"` → `[System.IO.File]::WriteAllText(..., UTF8Encoding($false))`（无 BOM）→ 从 WSL 执行。单次写入 > 28 KB 触发 os error 206，必须分块。
4. **WSL 引号吞噬（本会话实测三次，新增为铁律）**：`wsl -e bash -lc '...'` 的单引号串里，**双引号会被吃掉**、**`$(...)` 直接语法错**、**`$var` 会被展开成空**。实测危害形态：`grep -Ei "a|b"` 退化为 `grep -Ei a|b`，把 `b` 当命令执行并输出 `command not found`（**假阴性**：看起来像"没匹配到"，实际是模式根本没生效）。安全形态：用 `grep -e X -e Y` 代替 `grep "X|Y"`；用 `;` 串联代替 `$(...)`；把复杂逻辑一律写进 `.py`/`.sh` 文件再执行；需要变量时写进脚本文件而不是命令行。
5. **门禁一律跑冻结索引树**（R11-3）：`git checkout-index` 导出到 repo 外 scratch，软链 `.venv` / `.git` 后跑四门。理由：共享工作树常有在飞 lane 的未提交改动，直接在树上跑门会得到既非 HEAD 亦非待提交树的第三态。
6. **入库只走 `scripts/orch_harness.py::run_commit(...)`**：八步闭环（文本卫生 → 台账落盘写静态预测值 → 显式 `git add` 并断言暂存集 → 冻结树跑四门双判 rc+文本 → 实测对账预测不符即 `git reset` + 台账还原 → A144(c) 未跟踪件归属 → 悬空引用扫描 → `git commit -F` + 复验 HEAD 推进）。任一步失败保证 HEAD 不动、不留半成品、不腐化账本。**禁止** `git add -A`，**禁止**绕过 harness 手工提交。
7. **不采信交接摘要的计数断言**（`rule_no_trust_handoff_summary_assertions`）：任何新实例接管后一律从磁盘现跑复测。本件所有数字均为本会话实测，续跑者仍须复测。
8. **历史值只加注不改写**（D-011 / D-012 / D-014）：列表型与历史型键禁整体覆盖（R9-5 教训）。引用计数一律指向账本键，禁写死数字。
9. **git 与 `orchestrator/state.json` 的写权限归编排器独占**；lane 只写自己 write_set 内的文件（A214 窄豁免须显式写进派单文）。
10. **PRE-13 派单前先提交**：predispatch commit 必须在 `spawn_agent` **之前**落地，agent_id 事后由纯台账提交回填。
11. **PRE-19..PRE-22（本会话新增，源 D-049 的三处立法面失真）**：PRE-19 检索命令限定路径 / 输出上限 / 排除散文面；PRE-20 派单文里的三类断言（枚举、计数、阳性对照判红预言）必须**派单前脚本实测**并贴命令原文，判红预言必须写明「若不红则如实入档并补替代对照」；PRE-21 探针脚本一律 `uv run --no-sync python`；PRE-22 断言的期望集必须与被调判据用**同一过滤口径**构造。
12. **dangling sweep 口径（本会话实测确认，新增为铁律）**：`DANGLING_SWEEP_SKIP = {"orchestrator/state.json"}` —— **台账本体不被扫**，故 `forward_reference_registry` 里的未落地路径留在 state.json 不触发门；但**新写的 .md 会被扫**。正则 `(?:evidence|orchestrator|docs|contracts|scripts)/[A-Za-z0-9._@/\-]+`，命中后 `.rstrip(".,;:)】、。")` 再判磁盘存在。本件 §8 的 6 条前向引用即由此进入 `allow_dangling`，逐条登记并做**集合相等**断言（不是子集断言）。注意 `tests/**`、`src/**`、`web/**` 前缀**不在**正则内，可自由书写。

## 2. 冻结时刻的仓库与账本实测值

### 2.1 git 面（全部实测）

| 项 | 值 |
| --- | --- |
| HEAD | `97fc9d9fa9549c863b534e2b9d685251c2f6c6f2` |
| commits（`git rev-list --count HEAD`） | **117** |
| 分支 | `m0-framework` |
| origin/m0-framework | `97fc9d9fa9549c863b534e2b9d685251c2f6c6f2`（**已同步**） |
| `rev-list --left-right --count origin...HEAD` | `0  0` |
| `git status --porcelain` | 空 |
| `git diff --cached --stat` / `git diff HEAD --stat` | 均空 |
| `git ls-files --others --exclude-standard` | 空 |
| `git stash list` | 空 |
| `orchestrator/state.json` worktree sha1 | `516f929c61ca`（1736314 B），与 `HEAD:` blob **逐字节相同** |
| `orchestrator/state.json` JSON 可解析 | True |

### 2.2 本会话落地的 4 个提交（按时序）

| sha | tag | 内容 |
| --- | --- | --- |
| `87c897a` | R17-landS2b2 | **M2-01/S2b-2 成品**：`create_app` 追加 `activity_service` / `rule_service` 两个可注入 kwonly 形参 ＋ 两组条件装配（**不含 include_router**，A217 ③ 下放给 S3/S4）；`app.state` 6→8；＋ `tests/unit/test_s2b2_app_injection.py`（新建，9 条守护 G1–G9）。编排器 49 项独立复验全绿，终裁 A235–A238。 |
| `50be48f` | R17-backfill-sha | **纯台账回填** S2b-2 的 sha `87c897a` ＋ 如实登记该批 normalize 命中 1 件（取证索引 TRAILING_NL_ADDED，`e64663c84cca`→`3f1825ee4fa0`，+1 B）＋ `close_agent(Mendel)` 释放并发槽。 |
| `d36e214` | R17-landS5 | **M0-04/S5 成品**：`tests/integration/jobs/` 集成测试奠基 —— conftest 9 个 fixture（**零 autouse**）＋ T1–T9 状态机 13 例 ＋ Idempotency-Key 3 例 ＋ jobs API 7 例 = **23 例**，该目录 **88 passed**；＋ 编排器同批补牙的 autouse 静态哨兵（`tests/unit/test_jobs_conftest_no_autouse.py`，3 例）。共 8 个新文件、**零修改件**。编排器 **70 项独立复验全 PASS / 0 FAIL**，终裁 A239–A242，立 **D-049**，自我更正 R17-3 / R17-4（新增 PRE-21 / PRE-22），开 FU-56。 |
| `97fc9d9` | R17-backfill-sha | **纯台账回填** S5 的 sha `d36e214`（六类目标全核销）＋ R16-8 体例双录该批 normalize 命中 1 件（`orchestrator/defects/D-049.md` TRAILING_NL_ADDED，`49b419b3b407`→`ef3509a79458`，7003→7004 B）＋ `close_agent(Kierkegaard)` 释放并发槽。四门读数与 `d36e214` **逐条相同**（301/107/734，109 py + 192 md），符合"纯台账提交"定义。 |

### 2.3 四门读数（冻结索引树口径，`97fc9d9`）

| 门 | 读数 | 备注 |
| --- | --- | --- |
| `ruff format --check .` | rc=0，**301** files already formatted | in_scope_py **109** + in_scope_md **192**；ruff 0.17.4 的 format 作用域含 .md |
| `ruff check` | rc=0，All checks passed | |
| `mypy` | rc=0，Success: no issues found in **107** source files | strict 干净 |
| `pytest`（全表） | rc=0，**713 passed** frozen 实跑 + **21** GIT_ENV_IGNORES 静态收集 = **734** | GIT_ENV_IGNORES = test_config.py(16) + test_counts_freshness.py(5) = 21 |
| 前端 vitest（历史值，未在本会话重跑） | 104 passed / 7 files | 测于 2026-11-13T08:48:41+08:00，编排器独立复跑 |

`live_openapi_sha16 = 592571099d638251`、`live_openapi_bytes = 443309`、`info.version = 1.0.1`、`contract_registered_nodes = 13`、`frontend_baseline_rows = 8`、`task_cards_on_disk = 29`、`known_missing_cards = 0`。

### 2.4 账本规模（实测）

`defects = 49`（D-001..D-049 连续无缺号）· `followups = 56` · `round17_adjudications = 9`（A234..A242）· `round17_self_corrections = 4`（R17-1..R17-4）· `budget.subtask_log = 45` · `resume.next_actions = 33` · `baseline_authoritative.history = 11` · `decisions = 15` · `change_requests = 2`（CR-001、CR-002）· `forward_reference_registry = 7` 条（1 条为 A173 规则项，6 条为路径项）。
## 3. 进度如实口径与推导

### 3.1 任务级（权威口径）

29 张任务卡全部在盘（`task_cards_on_disk = 29`、`known_missing_cards = 0`，由 `tests/unit/test_task_cards_complete.py` 机器守护逐键比对磁盘实测）。

| status | n | 任务 |
| --- | --- | --- |
| DONE | 3 | M0-02、M0-03、M0-P01 |
| PASS_WITH_TODO | 2 | M0-01、M0-03b |
| IN_PROGRESS | 2 | M0-04、M2-01 |
| TODO | 22 | M1-01、M1-02、M1-03、M1-04、M1-P01、M2-02、M2-03、M2-04、M3-01、M3-02、M3-03、M3-04、M3-P01、M3-P02、M4-01、M4-02、M4-03、M4-P01、M5-01、M5-02、M5-03、M5-P01 |

**任务级完成度 = 5/29 = 0.1724**（DONE + PASS_WITH_TODO 计满）。

### 3.2 在飞链的子任务级推进（沿用 R14 的分母口径，保证可比）

**M0-04**（分母 12，R14 同口径）：已 DONE = S1、S2、S2b-1、S2b-2、S2b-3、S2c、S3、S4、S7、**S5** = **10**；剩余 = **S6、S8** = 2（账本 `remaining_sequence_R17_post_S5` 实测为 `["S6（qwen3.8-flash）","S8（qwen3.8-flash）"]`）。⇒ **10/12 = 0.8333**（R14 时点为 7/12 = 0.583，本会话 +S2c +S4 +S5）。

**M2-01**（分母 9：R14 的 8 因 S2b 拆成 S2b-1 + S2b-2 而 +1）：已 DONE = S1、S2a、S2b-1、**S2b-2** = **4**；剩余 = **S3 → S4 → S5 → S6 → S7** = 5（账本 `remaining_sequence_R17_post_S2b2` 实测）。⇒ **4/9 = 0.4444**（R14 时点为 1/8 = 0.125）。

**加权总体口径** = 0.1724 + 0.8333/29 + 0.4444/29 = 0.1724 + 0.02874 + 0.01532 = **0.2165 ≈ 21.6%（取 22%，区间 20–23%）**。
对照：R14 检查点为 ≈19.7% ⇒ 本会话净推进 **≈ +2 个百分点**（两个子任务成品入库 + 两次 sha 回填）。

### 3.3 AC 口径（47 条，**必须与任务级口径分开看**）

`acceptance.primary_owner` 实测 **47 条**，与 `acceptance_denominator = 47`、`acceptance_resolvable = 47` 一致。判据：**AC 闭合 ⇔ 其 primary_owner 任务的 status ∈ {DONE, PASS_WITH_TODO}**。

- **已闭合 2 条 = 2/47 = 4.3%**：AC-001（primary = M0-02）、AC-034（primary = M0-02）。
- primary_owner 属 **IN_PROGRESS** 的 4 条：M2-01 × 3、M0-04 × 1。
- primary_owner 属 **TODO** 的 41 条：M3-P01 × 6、M2-02 × 4、M3-01 × 4、M1-03 × 3、M3-02 × 3、M4-02 × 3、M5-01 × 3、M4-P01 × 3、M1-01 × 2、M1-02 × 2、M2-03 × 2、M1-P01 × 2、M3-03 × 1、M4-01 × 2、M5-P01 × 1。
- **wave1_composite 口径**（`acceptance.wave1_composite`，来源 = Q lane 亲自重跑的四支柱复合判据）：AC-001 = PASS_WITH_TODO、AC-034 = PASS_WITH_TODO、**AC-035 = PASS**。注意 **AC-035 的 primary_owner 是 M5-01（尚 TODO）**，故它在复合口径下已有 PASS 结论、但在任务级严格判据下**不计闭合** —— 这是两套口径的真实差异，续跑者不要把它算成 3/47。

**结论（如实）**：AC 闭合率（4.3%）显著低于代码完成率（22%）**是结构性的**：绝大多数 AC 的权威取证件归属 wave 3–10 的任务，而这些任务尚未开工。AC 曲线会在 M5-01 / M5-02 / M5-03 / M5-P01（纯验证任务）阶段集中跃升。**不得**用 AC 闭合率倒推"项目只做了 4%"，也**不得**用子任务完成率（下条）倒推"项目做了 92%"。

### 3.4 子任务桶（**不是**全局进度指标，仅用于在飞链）

实测桶分布：DONE 35 · TODO 2（M0-04/S6、M0-04/S8）· DEFERRED 1（M0-03b/S4）· DONE_WITH_GAP 1（S2b-2 lane）。
**警告**：该桶只登记了**已拆解**的任务（M0-* 与 M2-01），22 个 TODO 任务尚未拆解 ⇒ 36/39 = 92% 这个比值**严重高估**全局进度，禁止对外引用为完成度。
**待核项（续跑时先验，本会话未擅改）**：探针按 `tasks[*].subtasks` 聚合时把 `S2b-2` 归到了 **M0-04** 名下，而 `budget.subtask_log` 与 `round17_lane_S2b2_return` 都明确 `task = M2-01`。疑为账本某处 `subtasks` 映射的归属笔误（不影响任何交付件与四门读数，属台账可读性问题）。**本会话未修改**（超出 checkpoint 授权范围）；续跑第一步应按 §10 复核并如实登记（若确认为笔误则立缺陷 + 纯台账更正，禁静默改写历史键）。

### 3.5 波次口径

11 个波次（wave 0..10）。**已闭合 wave 0、wave 1**（2/11）；**wave 2 在飞**（M0-03b 已 PASS_WITH_TODO、M0-04 = 0.833 ⇒ wave 2 ≈ 91.7%）；**wave 3–10 未开工**（8 个波次、22 个 TODO 任务）。
当前 `phase = M0`、`wave = 2`。关键路径 14 节点：M0-01 → M0-02 → **M0-04** → M1-01 → M1-02 → M3-01 → M3-02 → M3-03 → M4-01 → M4-02 → M4-03 → M5-01 → M5-02 → M5-03。
**M0-04 是关键路径头节点、也是 21 个 TODO 任务的唯一解锁点**；它闭合后 wave 3 的 L1/L2 可并行开闸。⇒「22%」是**已验收工作量占比**，不等于还剩 78% 的**时间**。

## 4. 剩余工作与 DAG 续跑面

### 4.1 必须先收口的两条链（wave 2 出口）

**M0-04（关键路径，剩 2 棒，均 flash）**
- **S6**（qwen3.8-flash）：前置已由 S5 满足（conftest 的 9 个 fixture 面 + 该目录 88 passed 绿基线）。义务见账本 `tasks['M0-04'].s6_obligations_R17`，5 条：① 复用 S5 的 9 名冻结 fixture（禁增删、禁 autouse —— 已由入库哨兵 `tests/unit/test_jobs_conftest_no_autouse.py` 机器看守，违反即 rc=1）；② 逐字携带 design §9-S6 的 FixedClock / advance_clock 用法（**禁** time.sleep / time.monotonic / datetime.now / utcnow）；③ 若需 runner 级端到端取证，同批产出（可复用 S5 的 registry_with_stub / stub_handler）；④ 逐字携带 PRE-13..PRE-22 + R16-6 派单文瘦身 + PRE-14 预期红清单；⑤ 枚举/计数类断言必须派单前脚本实测并贴命令原文（PRE-20，源 D-049 ①）。**硬禁**：改 S5 已入库的 4 件（sha `90ba7b17b115` / `39e6c8423b1a` / `69a69d80abeb` / `64a157a2f176`）与哨兵件（`0f37d540f63a`）；**禁碰 `src/campaignlab/api/app.py`**（那是 M2-01/S3 的写集，Round 18 并行）。
- **S8**（qwen3.8-flash）：收口取证 —— `evidence/M0/M0-04/` 的 ac.md / job-states.md / commands.md / gates/ / http 面，并**闭合 §8 的 2 条前向引用**。M0-04 在 S8 入库前**禁判 DONE**。

**M2-01（剩 5 棒，均 flash，严格串行）**
- **S3**（`api/activities.py` + 在 app.py 挂载）：前置已由 S2b-2 满足（`s3_unblocked_R17`）。**必须同批补端到端判据**（账本 `s3_precondition_note_R17`）：注入 activity_service 后经 TestClient 走一条真实 activities 路由，断言 `deps.get_activity_service` 取到的对象与注入对象**同一**（`is`），以闭合 S2b-2 只做到"键名双向对撞"的代理证明。
- **S4**（`api/rules.py` + 挂载）：对 rule_service 同理。**S3 与 S4 都要改 `api/app.py` ⇒ 互斥、必须串行**（N4 禁双主写）。
- **S5**（`tests/api/**`）→ **S6**（`tests/api/activities/**`，**必须逐字携带 FU-54 与 design §3.2 的 `set_current_rule` SQL 原文**）→ **S7**（`evidence/M2/**`，**闭合 §8 的 4 条前向引用**）。M2-01 的 AC 取证归 S7，**S7 入库前禁判 DONE**。

### 4.2 wave 3–10（22 个 TODO 任务）

wave 2 出口（M0-04 判 DONE）后开闸。写权限不相交性已在账本 `waves` 里逐波登记：
- **wave 3**（parallel-lanes）：L1 = M1-01 → M1-02 → M1-03；L2 = M2-01 → M2-02 → M2-03。lane 内串行、两 lane 并行，跨 lane 写权限已确认不相交。**注意 M2-01 已在 wave 2 期间提前推进**，续跑时须按实际状态重排 L2 的入口。
- **wave 4**（parallel）：M1-04、M2-04、M1-P01（pages/data 与 pages/{rules,cases} 与后端 monthly_ingest 三者写权限不相交）。
- **wave 5**（parallel-lanes）：L1 = M3-01 → M3-02 → M3-03；L3 = M3-P01（只写 domain/monthly 与 tests/{domain,golden}/monthly；infra/duckdb 与指标注册表属公共件，改动走 CR）。
- **wave 6**（parallel）：M3-04、M4-01。
- **wave 7**（parallel-lanes）：L1 = M4-02 → M4-03；L4 = M3-P02（只写 pages/review/monthly 与 features/monthly，改 UI-17 既有文件走 CR）。
- **wave 8**（serial）：M4-P01 → M5-01。
- **wave 9**（parallel）：M5-02、M5-P01（两条独立 QA 线，写集互不相交：M5-02 写 qa-reports 根 ＋ M5-qa 取证面 ＋ D-* 缺陷；M5-P01 写 qa-reports/monthly ＋ monthly/M5-P01 取证面 ＋ DMR-* 缺陷）。
- **wave 10**（serial）：M5-03。

### 4.3 债务面（不阻塞，但须在指定时点前清理）

- **FU-50 / FU-52 / FU-53 必须在 wave 3 开闸前处理**（既有登记）。
- followups 实测 56 条，状态分布：PENDING 20 · OPEN 11 · None 16 · DONE 4 · CLOSED 4 · ADJUDICATED 1 ⇒ **非闭合 47 条**。
- 缺陷 49 条：CLOSED 22 · FIXED_PENDING_Q 18 · OPEN 9（D-012、D-016、D-017、D-022、D-024、D-033、D-034、D-039、D-040）。**blocking 命中 0 条**。FIXED_PENDING_Q 的 18 条待 Q 线（M5-02 / M5-P01）统一验收消解，含本会话新立的 **D-049**。

## 5. 模型档位分配与护栏（成本控制的如实账）

### 5.1 实测护栏读数

| 指标 | 实测 | 目标（手册 §6.6） | 达标 |
| --- | --- | --- | --- |
| flash_share_tasks | **0.5556**（30/54） | ≥ 0.60 | **否** |
| flash_share_dev_lanes | **0.3438**（11/32） | — | 参考 |
| flash_share_tokens | **0.6655** | ≤ 0.35 | **否** |

`budget.subtask_log` 的 tier 直方图（45 条）：qwen3.8-flash **21** · qwen3.8-max **22** · None 1 · orchestrator-self-served 1。

### 5.2 未达标的成因与合规处置

**两条护栏都未达标，本会话如实报告、不做任何粉饰。** 成因：
1. **token 口径被估算值污染**：平台无 token 计量句柄，lane 自报均为区间估算。S5 的 lane 自报「150k–220k」即按 A183 记 `tokens = null` + `tokens_estimated = true`，计入 `token_entries_null`。**在缺少真实计量的前提下，flash_share_tokens 的分母本身不可靠** ⇒ 该指标只能作趋势参考，不能作硬性达成判据。这是如实陈述，不是为不达标找理由。
2. **max 档集中在 wave 0–2 的地基件**（领域层、契约 DTO、事务边界、跨层装配），命中手册 §6.3 的强制 max 清单，**不可降档**。
3. **已钉死的 flash 后续件尚未入账**：M0-04 的 S6/S8 + M2-01 的 S3–S7 = **9 个 flash 子任务**已钉死，入账后 flash_share_tasks 将升到 **≈ 39/63 = 0.619 ≥ 0.60**（护栏①可望达标）。wave 3–10 的 22 个任务绝大多数为 flash 档，护栏①会持续走高。

**绝对禁令（C10 / 手册 §6.6）**：**禁补造 flash 工作凑配比**、**禁把 max 件谎报成 flash**、**禁拆细 flash 件刷单位数**、**禁为达标而降档**。护栏是**观测指标**，不是可以反向驱动交付面的目标函数。

### 5.3 续跑的档位分配原则（按复杂度识别，非按任务名）

- **强制 qwen3.8-max / high**：事务边界、跨层装配、DDL 与迁移等价性、契约（OpenAPI / DTO）变更、并发与幂等语义、任何需要改公共件（`api/app.py`、`api/common.py`、`api/deps.py`、`infra/duckdb`、指标注册表）的件。
- **qwen3.8-flash / medium**：纯新建测试文件、路由层薄封装（挂载点已由 max 件冻结）、页面组件（设计模板已冻结）、取证归档件、文档与 evidence 编制、债务清理（FU-*）。
- **判据**：若一个子任务的 write_set **只含新建文件**且其接口面已被上游 max 件冻结 ⇒ flash 可胜任；若需**修改既有公共件**或**引入新语义** ⇒ max。
- **降档必须留痕**：S2b-2 曾发生计划 max/high 实用 flash/medium 的降档，由 **A234** 追认并如实登记 `tier_match = false`。**禁静默降档**。

## 6. 本会话的自我更正、终裁与缺陷（loop engineering 的可审计痕迹）

- **终裁 A235–A238**（S2b-2 lane）：含 **A234 降档追认**、A217 ③ 的 include_router 下放。
- **终裁 A239–A242**（S5 lane）：**A241** = 编排器同批补牙 autouse 静态哨兵（把"conftest 禁 autouse"从散文约定升级为机器守护）；GAP 定性为**派单文判红预言失真**而非交付面缺陷，**当批闭合、不留给下一棒**。
- **自我更正 R17-1..R17-4**：R17-3 / R17-4 新增 **PRE-21**（探针一律 `uv run --no-sync python`）与 **PRE-22**（断言期望集与被调判据同一过滤口径）。
- **D-049（本会话新立，MINOR / FIXED_PENDING_Q / 非阻塞）**：S5 派单文的**三处立法面失真** —— ① 枚举/计数类断言未经派单前实测；② 检索命令未限定路径与输出上限；③ 阳性对照的判红预言失真（PC-4 的 [B] 步未判红）。**责任在立法面（编排器），不在交付面（lane）**。这是本会话最重要的一条经验：**派单文里的每一个数字与每一条"应该会红"的预言，都必须先跑一遍再写进去。**
- **FU-56** 已开。
- **loop 使用**：S5 lane 自报 loop **2-of-2**（用满但未硬撑第 3 轮）。编排器**不采信自报**，以终态佐证：23 例全绿 + 该目录 88 passed + 70 项独立对撞全 PASS + `git diff --numstat HEAD` 全空（零修改件 ⇒ 无返工痕迹）。loop 用满的**部分成因是 D-049 的三处失真** ⇒ 归因于立法面。
## 7. 锁与写集（续跑第一轮必须照此排他）

账本无独立 `locks` 键（R14 的 locks 段由编排器依据 design 与 write_set 归纳，非账本字段）。下列为**冻结时刻的有效锁面**，续跑时按 Round 18 的实际派单重新核定：

| 文件 | 归属 / 状态 |
| --- | --- |
| `src/campaignlab/api/app.py` | **Round 18 的争用焦点**：M2-01/S3 先（挂 activities router，include_router 4→5）→ M2-01/S4 后（挂 rules router，5→6）。**M0-04/S6 禁碰**。既有冻结面不得回退：add_middleware 顺序、`openapi_url = docs_url = redoc_url = None`、`ALLOWED_*`、`app.state` 既有 8 个键。 |
| `src/campaignlab/api/common.py` | 已由 M2-01/S2a 释放；`__all__` 现值 **51**。S4 的 JobPage 已 append-only 落地。 |
| `src/campaignlab/api/deps.py` | M2-01/S2b-1 已落地（纯追加），S3/S4 取用其提供器。 |
| `src/campaignlab/application/activity_service.py` | M2-01/S2b-1 新建，已入库。 |
| `src/campaignlab/infra/db/repositories.py` | append-only 锁已随 `a0ee343` 释放；**禁 `list_all`**。 |
| `src/campaignlab/worker/service.py` / `worker/store.py` | M0-04/S2c 已落地（A169 纯追加，既有 20 个 def 一字不改）。 |
| `tests/integration/jobs/conftest.py` | **9 个 fixture 名已冻结**，禁增删、禁 autouse；由 `tests/unit/test_jobs_conftest_no_autouse.py` 机器看守。 |
| `orchestrator/handoff/M0-04-design.md` | M0-04 链专属（A214 窄豁免：**仅文末追加** + numstat deleted = 0）。 |
| `orchestrator/handoff/M2-01-design.md` | M2-01 链专属，同上窄豁免。 |
| git 与 `orchestrator/state.json` | **编排器独占**，lane 一律禁写。 |

**N4 禁双主写**：同一文件不得在同一轮内被两条并行 lane 主写。Round 18 的 M0-04/S6 与 M2-01/S3 之所以可并行，正因 write_set 不相交（S6 只写 `tests/integration/jobs/`，S3 写 `api/activities.py` + `api/app.py`）。

## 8. 前向引用登记面（6 条路径项**全部仍悬空**，逐条实测）

`resume.forward_reference_registry` 共 7 条：1 条为 A173 规则项（非路径），6 条为路径项。**本会话对这 6 条逐一做了 `os.path.exists` 实测，结果全部为 False**（即仍悬空、仍未闭合）：

| 路径 | 闭合于 | 登记来源 |
| --- | --- | --- |
| `evidence/M0/M0-04/ac.md` | **M0-04/S8** | R14-5（design 的 :68 与 :91，S1 设计冻结件原文遗留） |
| `evidence/M0/summaries/M0-04.md` | **M0-04/S8** | R14-5（design 的 :91） |
| `evidence/M2/M2-01/` | **M2-01/S7** | R15 第 3 槽留白期的前向引用普查（design 的 :1180/:1245/:1303） |
| `evidence/M2/M2-01/clauses.md` | **M2-01/S7** | 同上（design 的 :1264） |
| `evidence/M2/M2-01/gates/` | **M2-01/S7** | 同上（design 的 :951） |
| `evidence/M2/summaries/M2-01.md` | **M2-01/S7** | 同上（design 的 :1180/:1189/:1245/:1303） |

**本会话的更正（如实登记）**：编排器首次探查时用一个"找 `status ∈ {OPEN,PENDING}` 字段"的过滤器，得出 **0 条 open** 的结论 —— 这是**假阴性**：这些登记项**根本没有 `status` 字段**（其字段为 referenced_in / registered_at / registered_by / rule）。改用**磁盘存在性实测**后才得到真实的 6 条。教训与 PRE-22 同源：**判据的口径必须与被判对象的真实结构对齐，不能凭想象套一个字段名。**
**对续跑的影响**：本件（.md）会被 dangling sweep 扫描，故这 6 条必须显式进入 `allow_dangling` 并做集合相等断言；`orchestrator/state.json` 在 `DANGLING_SWEEP_SKIP` 内，不受影响。

## 9. 风险与已知问题（续跑者先读，避免重蹈）

1. **【中】§3.4 的子任务归属疑点**：S2b-2 在 `tasks[*].subtasks` 聚合中疑似被归到 M0-04 名下（权威 lane 记录为 M2-01）。不影响交付件与四门，但**会污染任何基于 subtasks 聚合的进度统计**。续跑第一步复核，确认后走纯台账更正 + 立缺陷，**禁静默改写历史键**。
2. **【中】flash_share_tokens 不可作为硬判据**：无平台计量句柄，分母由区间估算构成（A183）。**禁**为了改善该数字而调整交付面。
3. **【中】AC 曲线与代码曲线不同步**：见 §3.3。若续跑者或人类看到"AC 只有 4.3%"而误判项目濒临失败，应回到 §3.2 的任务级口径。**两套口径都要报，不得只报有利的那一个。**
4. **【高】wave 2 出口是唯一解锁点**：M0-04/S8 未入库前，wave 3–10 的 21 个任务全部无法开工。任何把资源从 M0-04 链挪走去"刷" TODO 任务的做法都会**拉长总工期**。
5. **【中】S3/S4 对 app.py 的串行约束**：若误判为可并行，会触发 N4 双主写，导致其中一棒的守护判据假红并被迫返工。
6. **【低】D-049 类型的立法面失真会重复发生**：派单文越长越容易夹带未实测的数字。PRE-20 是解药，但需要**每棒都执行**，不是执行一次就够。
7. **【低】18 条 FIXED_PENDING_Q 缺陷积压**：集中在 Q 线（M5-02 / M5-P01）消解。若 wave 9 之前 Q 线范围发生变更，这批缺陷的验收归属需重新裁定。

## 10. 续跑 runbook（**九步，逐步复测，禁跳步**）

1. **复测 git 面**：`git rev-parse HEAD` 应为 `97fc9d9fa9549c863b534e2b9d685251c2f6c6f2`（或其后代）；`git status --porcelain` 应为空；`git rev-list --left-right --count origin/m0-framework...HEAD` 应为 `0  0`。**若 HEAD 不是 97fc9d9 或其后代 ⇒ 停手回报，禁强行续跑。**
2. **复测四门**（冻结索引树口径）：应得 ruff_format **301** / mypy **107** / pytest **734**（713 + 21）。**若测得 294 / 102 / 708 ⇒ 说明 checkout 到了 `d36e214` 之前**（R15-3 的根治措辞），停手核对。
3. **复测账本不变量**：`dag_paused == true`；`resume.checkpoint_R17` 存在；`dispatched_not_yet_returned == 0`；`resume.in_flight_agents` 中 6 条 lane 全为 RETURNED_*；`commit_backfill_pending_R17_S5.status == "DONE"`；defects == 49、followups == 56、subtask_log == 45。
4. **复核 §9.1 的子任务归属疑点**，如实登记（立缺陷或判为探针口径问题）。
5. **解除暂停**：把 `dag_paused` 置 false、写 `dag_resumed_at` 与 `dag_resume_authorization`（**必须记录人类的「开工」指令时刻**），走一次纯台账提交（`run_commit`，EXPECT 与 §2.3 完全相同：301/107/734，109 py + 192 md）。
6. **清理并发槽**：重启后为全新 3 槽（进程级资源），无残留占用。确认无僵尸 agent 需 `close_agent`。
7. **写 Round 18 派单文**（M0-04/S6 与 M2-01/S3），**逐条执行 PRE-20**：派单文里出现的每一个枚举值、计数值、阳性对照判红预言，都必须**派单前脚本实测**并把命令原文贴进派单文。携带 PRE-13..PRE-22、R16-6 瘦身、PRE-14 预期红清单、§7 的锁面、§4.1 的义务清单。
8. **PRE-13：predispatch commit 先落地，再 `spawn_agent`**；agent_id 事后由纯台账提交回填。
9. **恢复 loop engineering 节奏**：每棒返回后编排器**独立复验**（禁采信自报），终裁入 `round18_adjudications`（首号 **A243**），自我更正入 `round18_self_corrections`（首号 **R18-1**），缺陷首号 **D-050**，CR 首号 **CR-003**，followup 首号 **FU-57**。

**计数器下一号（实测）**：adjudication **A243**（现 A234..A242，共 9 条，append-only）· self_correction **R18-1**（R17-1..R17-4 已用满）· defect **D-050** · change_request **CR-003** · followup **FU-57** · round **R18**。

## 11. 续跑首个派单（Round 18，人类说「开工」后立即执行）

| 槽 | 任务 | 档位 | 依赖 | 备注 |
| --- | --- | --- | --- | --- |
| lane 1 | **M0-04/S6** | qwen3.8-flash / medium | S5 已入库（`d36e214`）⇒ **已满足** | 关键路径；携带 `s6_obligations_R17` 五条 + **禁碰 api/app.py** |
| lane 2 | **M2-01/S3** | qwen3.8-flash / medium | S2b-2 已入库（`87c897a`）⇒ **已满足**（`s3_unblocked_R17`） | 携带 `s3_precondition_note_R17` 的端到端 `is` 同一性判据 |
| lane 3 | **留白或债务清理** | qwen3.8-flash | — | R14 先例：**留白优于派废单**。可用于 FU-50 / FU-52 / FU-53（wave 3 前必须清）或 §9.1 的复核，同时助护栏①回升 |

两 lane 的 write_set 不相交（S6 → `tests/integration/jobs/`；S3 → `api/activities.py` + `api/app.py`），满足 N4。
**S4 必须等 S3 入库后**再派（同改 `api/app.py`）。**M0-04/S8 必须等 S6 入库后**再派。

## 12. 数据损失评估（逐项，如实）

| 面 | 损失 | 依据 |
| --- | --- | --- |
| 代码 | **ZERO** | 全部成品已入库；`git status --porcelain` 为空；无未跟踪件；无 stash |
| 取证 / evidence | **ZERO** | S5 的两件取证已随 `d36e214` 入库 |
| 账本 | **ZERO** | 本 checkpoint 提交冻结全部账本事实；state.json worktree 与 HEAD blob 逐字节相同 |
| 远端 | **ZERO** | `97fc9d9` 已 push，`origin/m0-framework == HEAD`，即使本机磁盘全毁也可 `git clone` 完整恢复 |
| 在飞 lane 上下文 | **ZERO** | `dispatched_not_yet_returned = 0`，无在飞 lane；两个并发槽均已 `close_agent` 释放 |
| 编排器会话内存态 | **有损但可再生** | 本会话的推理上下文随重启消亡；但所有**决策**已落账本（A234..A242、R17-1..R17-4、D-049、FU-56），所有**义务**已落账本（`s6_obligations_R17`、`s3_precondition_note_R17`、`remaining_sequence_*`），本件 §10 给出九步 runbook ⇒ **可无损续跑** |

**总结论：具备断点续跑的全部条件。** 唯一需要人类做的是给出「开工」指令。

---
*本件由编排器在 `97fc9d9` 冻结时刻实测生成；所有数字均来自本会话磁盘复测，未采信任何交接摘要的断言（`rule_no_trust_handoff_summary_assertions`）。*
