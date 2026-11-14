# R14-CHECKPOINT —— 长程无人值守 DAG 断点续跑检查点（主机重启前冻结）

冻结时刻：2026-11-14（在飞工作树快照 10:45:04+08:00；S2b-3 入库 `7c0c7c4`；本件随 checkpoint 提交入库）。
冻结原因：**主机（Win11）计划重启**。子智能体进程与编排器会话随重启必然消亡，故在其之前把已完成的工作**入库**、把不可再生的上下文**快照**、把全部账本事实**冻结**。
本件是续跑的**权威入口**，与流程规范 `docs/delivery/LONG-HORIZON-ORCHESTRATION.md` 配合使用；账本真值以 `orchestrator/state.json` 为准，本件是其可读索引与恢复剧本。

## 0. 30 秒速览（续跑者先读这段）

- **本会话把关键路径上的在飞成品救回了 git 历史**：M0-04/S2b-3 原为未提交的在飞工作树（4 改 + 3 新），lane 在冻结窗口内返回 DONE 终态回执，编排器独立复测全部真值后经 `run_commit` 入库为 **`7c0c7c4`**（四门全绿）。因此**当前工作树是干净的**，重启不会丢代码。
- HEAD 冻结点 = `7c0c7c4e8b8016fe243b5c726382ede762aa2f48`（100 commits），分支 `m0-framework`；本 checkpoint 提交后 HEAD 前进 1 格（101 commits）。
- 四门实测（**冻结索引树**口径，本提交后）：ruff_format = **259** files already formatted（in_scope_py 88 + in_scope_md 171）/ ruff_check = All checks passed / mypy = **86** source files / pytest = **571**（550 frozen 实跑 + 21 GIT_ENV_IGNORES 静态收集）。
- 任务级完成度 **5/29 = 17.2%**；含在飞链子任务级推进的**如实总体口径 ≈20%**，推导见 §3。
- 唯一需要重派的在飞件：**M2-01/S2a**（lane A1 / Ramanujan，**零落盘**，本会话已关槽；派单文 `orchestrator/handoff/R14-lane-A1-M2-01-S2a.md` 已入库 ⇒ 重派完全无损）。
- 下一个可派的关键路径件：**M0-04/S2c**（max，A169 新立），派单文 `orchestrator/handoff/R13-lane-Y-M0-04-S2c.md` 已入库，且 `src/campaignlab/infra/db/repositories.py` 的 append-only 锁已随 `7c0c7c4` **释放**。
- `dag_paused = true`。**续跑必须等人类明确「开工」指令**；runbook 见 §10。

## 1. 铁律（违反＝静默腐化或假红；续跑者原样继承）

1. **仓库位置**：WSL2 `/home/szf/dev/CampaignLab`，分支 `m0-framework`。宿主 Win11，PowerShell cwd `D:\ws\codex_rd\ss_campaignlab`；scratch 目录 `.orch_scratch\` ↔ `/mnt/d/ws/codex_rd/ss_campaignlab/.orch_scratch/`。
2. **写文件通道（唯一合法形态）**：PowerShell 单引号 here-string → `-replace "`r`n","`n"` → `[System.IO.File]::WriteAllText(..., UTF8Encoding($false))`（无 BOM）→ `wsl.exe -e bash /mnt/d/.../driver.sh`。**禁止** `wsl.exe -e bash -lc "…"` 里带 `$`、反引号、嵌套引号或 `|`——本会话实测两次踩坑，其危害形态是**假阴性**（详见 R14-7）。驱动脚本首行统一 `export PATH="$HOME/.local/bin:$PATH"`；单次写入 >28 KB 会触发 os error 206，必须分块。
3. **R14-1（解释器口径）**：项目钉死 `requires-python ">=3.14,<3.15"`、ruff `target-version = "py314"`、mypy `python_version = 3.14`、`.python-version` = 3.14.10（本会话实测 `uv run --no-sync python -V` = Python 3.14.10）。`except A, B:`（无括号）是 **PEP 758**，在 3.14 上**合法**；全仓仅 `src/campaignlab/api/common.py` 的 :574 与 :608 两处。**一切 AST / 语法 / 导入探针必须用 `uv run --no-sync python`，禁用系统 `python3`（3.12.3）**，否则对合法代码产生假红。被继承的 R12-1「通道静默损坏」表述属误诊；其操作面（写出的 .py 先 `ast.parse` 再跑）保留有效。
4. **门禁一律跑冻结索引树**（R11-3）：`git checkout-index` 导出到 repo 外 scratch，软链 `.venv`/`.git` 后跑四门。理由：共享工作树常有在飞 lane 的未提交改动，直接在树上跑门会得到既非 HEAD 亦非待提交树的第三态。
5. **入库只走 `scripts/orch_harness.py::run_commit(...)`**：八步闭环（文本卫生 → 台账落盘写静态预测值 → 显式 `git add` 并断言暂存集 → 冻结树跑四门双判 rc+文本 → 实测对账预测不符即 `git reset` + 台账 `checkout` 还原 → A144(c) 未跟踪件归属 → 悬空引用扫描 → `git commit -F` + 复验 HEAD 推进）。任一步失败保证 HEAD 不动、不留半成品、不腐化账本。**本会话已实证一次**：首次入库被第 7 步拦下并干净回滚（见 §6 的 R14-5）。**禁止** `git add -A`，**禁止**绕过 harness 手工提交。
6. **不采信交接摘要的计数断言**（`rule_no_trust_handoff_summary_assertions`）：任何新实例接管后一律从磁盘现跑复测。本件所有数字均为本会话实测，续跑者仍须复测。
7. **历史值只加注不改写**（D-011 / D-012 / D-014）：列表型与历史型键禁整体覆盖（R9-5 教训）。引用计数一律指向账本键，禁写死数字。
8. **git 与 `orchestrator/state.json` 的写权限归编排器独占**；lane 只写自己 write_set 内的文件。**A214 成文规则**：LANE-COMMON 对 `orchestrator/**` 的禁令是**默认值**，派单文可授予「单文件 + 仅文末追加 + numstat deleted=0」的窄豁免，且该豁免必须显式写进 lane 的 write_set。
9. **前向引用必须登记**（R14-5 新增义务）：设计冻结件（`*-design.md`）在 S1 入库的**同一批**，必须把其中所有指向未来交付件的 `evidence/**` 路径登记进 `resume.forward_reference_registry`；否则该文件此后每次被重新 add 都会被悬空门拦下，把成本转嫁给无关的下游提交。

## 2. 冻结时刻的仓库与账本实测值

| 项 | 实测值 | 复测口径 |
| --- | --- | --- |
| 分支 | `m0-framework` | `git rev-parse --abbrev-ref HEAD` |
| HEAD | `7c0c7c4e8b8016fe243b5c726382ede762aa2f48` | `git rev-parse HEAD` |
| 提交总数 | 100（本 checkpoint 提交后 101） | `git rev-list --count HEAD` |
| 工作树 | **干净**（`git status --porcelain` 在本件入库前只有 1 条 `??`＝本件自身） | `git status --porcelain` |
| ruff_format | 258 files（py 88 + md 170）→ 本提交后 **259**（md 171） | `uv run --no-sync ruff format --check .` |
| ruff_check | All checks passed | `uv run --no-sync ruff check .` |
| mypy | **86** source files，rc=0（本棒新增 .py = 0，故不变） | `uv run --no-sync mypy` |
| pytest | **571**（550 frozen + 21 env-ignores 静态收集：`test_config.py` 16 + `test_counts_freshness.py` 5） | harness `run_gates` + `count_git_env_ignores` |
| 活契约 | `contracts/openapi.json` sha16=`592571099d638251` / 443,309 B / info.version=1.0.1 | `scripts/check_contracts.py` |
| 任务总数 | 29（DONE 3 / PASS_WITH_TODO 2 / IN_PROGRESS 2 / TODO 22） | `orchestrator/state.json` 的 `tasks[*].status` |
| 验收分母 | 47（baseline 35 + monthly 12），`acceptance_resolvable` = 47 | `orchestrator/state.json` 的 `acceptance` |
| 波次 | 11 波（wave 0–10），当前 wave 2 | `orchestrator/state.json` 的 `waves` |
| budget.subtask_log | 37 条 → 本提交追加第 38 条（S2a INTERRUPTED）后 **38** | `orchestrator/state.json` 的 `budget.subtask_log` |
| followups | 41 条 → 本提交追加 FU-41 后 **42**；其中 9 已闭 | `orchestrator/state.json` 的 `resume.followups` |
| 终裁序号 | 最后 **A214**（`resume.round7_adjudications` 共 132 条，append-only）→ 下一个 **A215** | 同上 |
| 自纠序号 | R14 现有 **R14-1 / R14-4 / R14-5**，本提交追加 **R14-6 / R14-7** → 下一个 **R14-8**。**R14-2 与 R14-3 号段作废**（仅存在于未入库的会话草稿，为避免 id 乱序不再补号，此句即其唯一说明） | `resume.round14_self_corrections` |
| 缺陷 | 42 条（D-001…D-042 连续无缺号，`tests/unit/test_state_ledger.py` 钉死分母与连续性）→ 下一个 **D-043** | `orchestrator/defects/` |
| CR | CR-001 ACCEPTED / CR-002 MERGED → 下一个 **CR-003** | `orchestrator/state.json` 的 `change_requests` |
| 前向引用登记 | 3 条：A173（已闭合）+ M0-04 的 `ac.md`（位于 `evidence/M0/M0-04/`）与 M0-04 摘要（位于 `evidence/M0/summaries/`），两者 lands_in = M0-04/S8 | `resume.forward_reference_registry` |

本会话入库的两笔：`7c0c7c4`（**lane Y · M0-04/S2b-3** 成品入库 + A211–A214 四项终裁 + R14-4/R14-5 两条自纠 + 前向引用登记）→ 本 checkpoint 提交（本件 + `dag_paused=true` + S2a 中断入账 + PENDING 回填 + q_verify_wave1 stage 纠正 + R14-6/R14-7）。
其前的三笔：`d62c0ca`（lane Z · M2-01/S1 设计冻结件）→ `70be045`（lane Y · M0-04/S2b-2）→ `a05ef28`（R14 派单前上下文 + A210 + R14-1）。

## 3. 进度评估（如实、可复核）

### 3.1 任务级（可验收口径）

5/29 = **17.2%**。已完成 5：`M0-01`(PASS_WITH_TODO)、`M0-02`(DONE)、`M0-03`(DONE)、`M0-03b`(PASS_WITH_TODO)、`M0-P01`(DONE)。在飞 2：`M0-04`、`M2-01`。TODO 22：M1-01..M1-04、M2-02..M2-04、M3-01..M3-04、M4-01..M4-03、M5-01..M5-03、M1-P01、M3-P01、M3-P02、M4-P01、M5-P01。

**注意 `M0-04` 仍禁判 DONE、wave3 仍禁开闸**：S2c 未做，且 M0-04 是 21 个 TODO 任务的唯一解锁点（账本 `tasks.M0-04.subtask_progress_note_R14Y` 已明文）。

### 3.2 波次级

| wave | 内容 | 状态 |
| --- | --- | --- |
| 0 | M0-01, M0-P01（serial） | **已闭**，Q 已复核 |
| 1 | M0-02, M0-03（parallel） | **已闭**，Q 已复核（Q-VERIFY-WAVE1 落地 `7db82a7`，本提交已纠正其账本 stage 字段） |
| 2 | M0-04, M0-03b（parallel） | **在飞**：M0-03b 已 PASS_WITH_TODO；M0-04 ≈58% |
| 3–10 | 其余 24 任务（8 波） | 未启动 |

wave2 期间提前启动 M2-01/S1（原属 wave3 的 lane L2）是刻意的关键路径并行：M2-01 的 deps 只有 M0-02（已 DONE），提前做不与 M0-04 争写权。

### 3.3 子任务级（两条在飞链的真实推进）

**M0-04**（关键路径）：卡片原定 8 个子任务（S1/S2/S3 max，S4–S8 flash），执行中 S2 依 A204/A205/A169 拆出 S2b-1、S2b-2、S2b-3、S2c，故有效子任务面为 **12**。

- 已完成 **7**：S1（设计冻结件）、S2、S2b-1（`hash_file`）、S2b-2（`worker/integrity.py` + `worker/deps.py`）、**S2b-3（本会话入库 `7c0c7c4`）**、S3（原子制品写入）、S7（Job DTO 单测）。⇒ design §5:52 的 ①②③④⑤ 判据**全部落地**。
- 剩余 **5**：**S2c**（max，A169：创建 `worker/service.py` + `JobStore.list_jobs` 纯追加；**同一提交内**必须删掉 `deps.py:55` 的 `# type: ignore[import-not-found]`，否则 strict 的 `warn_unused_ignores` 会把全表 mypy 判红）→ S4 → S5 → S6 → S8（**四个全 flash**）。
- ⇒ 子任务级 **7/12 = 58.3%**（入库前为 6/12 = 50%，本会话 +8.3 个百分点）。卡片 token 预算加权约 74%，但 S2 的拆分新增了原预算外的工作量，故**如实取 58% 而非 74%**。

**M2-01**：卡片原定 7 个子任务，A210 把 S2 拆成 S2a（design §11.1+§11.2）与 S2b（§11.3），故有效子任务面为 **8**。

- 已完成 **1**：S1（`orchestrator/handoff/M2-01-design.md`，1322 行 / 146,775 B / 13 个 H2 段）。
- 中断 **1**：S2a —— **零落盘**（实测 `src/campaignlab/domain/activity/` 目录不存在；`api/common.py` 的 `len(__all__)` 仍为 51，该文件 diff 为 0 行）。lane 已关槽，重派无损。
- 剩余 **7**：S2a（重派）→ S2b（max，`repositories.py` 锁已释放，现可派）→ S3 → S4 → S5 → S6 → S7（**五个全 flash**）。
- ⇒ 子任务级 **1/8 = 12.5%**。

### 3.4 总体如实口径

任务级 17.24% + M0-04 的 0.583/29（+2.01%）+ M2-01 的 0.125/29（+0.43%）≈ **19.7%，取 ≈20%**（区间 18–22%）。

必须同时说明的**非线性事实**：M0-04 是关键路径头节点，挡住 21 个下游任务；它一旦闭合，wave3 的 L1（M1-01→M1-02→M1-03）与 L2（M2-02→M2-03）即可并行开闸，进度曲线会陡升。因此「20%」是**已验收工作量占比**，不等于「还剩 80% 的时间」——关键路径长度见 `orchestrator/state.json` 的 `critical_path`（14 节点，M0-04 是第 3 个）。

## 4. 在飞工作树快照（历史证据 + 二次保险）

### 4.1 快照的现状与定位

冻结窗口内做过 4 次采样（10:26 / 10:29 / 10:34 后 / 10:45），目录 `/mnt/d/ws/codex_rd/ss_campaignlab/.orch_scratch/checkpoint_R14/`（244 KB）。**S2b-3 已随 `7c0c7c4` 入库，故该快照不再是唯一副本，降级为历史证据与二次保险**；其价值在于记录了「冻结时刻工作树长什么样」，可用于事后审计 lane 的产出是否与入库内容一致（实测一致，见 §4.3）。

| 文件 | 用途 |
| --- | --- |
| `MANIFEST.txt` | 权威清单：冻结时刻、当时的 HEAD 全 sha（`a05ef28…`）、分支、commits、稳定性判定、全部 sha256 |
| `inflight_worktree.patch` | 当时的 `git diff HEAD` 全量补丁，45,626 B，sha256 `1ce8d678a341c8b9c8f3137c6af38f222547e6534eaab7c156639d8aba58f75b` |
| `inflight_status.txt` / `inflight_numstat.txt` | 冻结时刻的 `git status --porcelain`（4 条 ` M`）与 `--numstat` |
| `files/**` | 5 个文件的逐字节副本（保留 mtime），路径结构与仓库一致 |
| `SHA256SUMS.1/.2/.3`、`MTIMES.1/.2` | 4 次采样的哈希与 mtime，用于证明稳定性 |

### 4.2 当时的逐文件 sha256（与最终入库内容逐字一致）

| 路径 | numstat(+/-) | sha256 |
| --- | --- | --- |
| `orchestrator/handoff/M0-04-design.md` | 38/0 | `f72df55ec32a8d971cb4b8e23d0d03d128b48c3fb4d98fa42aacfc8c4d7c7c14` |
| `src/campaignlab/infra/db/repositories.py` | 22/0 | `33590e99c580e3b78307990628f1d1ea38ffa41fa73d95e379aa30e0ec544038` |
| `src/campaignlab/worker/integrity.py` | 172/31 | `3f04ddd2466c4912a4361e3be8f5d4a11dae57225fa9b4b6ffda800a02fec8d1` |
| `tests/unit/test_worker_integrity.py` | 392/13 | `101ecbdc7b3b3821b44463ed0fbf2fc247d0100f819f04ec9dc3a9e617854014` |
| `evidence/M0/M0-04/positive-control-s2b3.log`（当时未跟踪） | 新增 14,334 B | `d1c0364d7f078f93a9be478ec5676a04aa13f02b60181f5d4461b97da2f612b3` |

另有两份取证 md 在快照后落盘并同批入库：`evidence/M0/M0-04/s2b3-integrity-jobs.md`（19,120 B / 247 行，sha256[:12] `b5c41b901813`）、`evidence/M0/M0-04/commands-s2b3.md`（6,005 B / 67 行，`dda66eaced6b`）。

### 4.3 编排器对 lane 回执的独立复测（禁采信自报）

`run_commit` 之前逐项实测，全部与 lane 自报一致：

- 4 个改动件 sha256 与 §4.2 快照**逐字相同**；3 份取证件 sha256 与 lane 回执自报**逐字相同**。
- `orchestrator/handoff/M0-04-design.md` 前 52 行 sha256 **双向**均为 `a5e3807475ecf2791a879b30f337ff4c2652c84fbd2efb94ecab64c5348513dd`（HEAD 版 vs 工作树版）⇒ D-011「原文不改写」得证，numstat 38/0 ⇒ 纯文末追加。
- `src/campaignlab/infra/db/repositories.py`：numstat 22/0（deleted=0）；`def list_all` 命中 **0**（A204 的 append-only 豁免未被用来开全表枚举后门）；`def list_for_workspace` 命中 2。
- `src/campaignlab/worker/integrity.py`：`len(__all__)` = **17**（11 → 17，新增 5×`POINTER_*` + `RESULT_REF_KIND`）；reason 常量集合 7→7（0 增 0 删，未引入第三个 reason）。
- 用例收集数：HEAD 冻结导出树 **19** / 工作树 **30**（派单要求 ≥24）；全表冻结收集 539 → **550**，env-ignores 静态收集 16+5=**21** ⇒ pytest_passed **571**。
- 阳性对照 5/5：PC-1 摘 ④ 分支→1 failed；PC-2 摘 ⑤ 分支→4 failed；PC-3 去掉 `WHERE workspace_id`→8 failed；PC-4 `_check_job` 空转→7 failed；PC-5 塞只读 `SELECT` 字面量→2 failed（并单跑冻结守护 rc=1，证明 A204 豁免未给 `worker/**` 开 SQL 后门）。5/5 复原后 sha256 == 快照，`ALL_RESTORED_IDENTICAL=True`，终验 93 passed rc=0。

### 4.4 稳定性判定（当时）

`integrity.py` 在 10:26→10:29 之间变化过一次（`89ce88ca…` → `3f04ddd2…`），其后三次采样完全一致，且 `positive-control-s2b3.log` 的 [D] 段自证 `ALL_RESTORED_IDENTICAL=True` ⇒ 代码写入于 10:34 停止，lane 此后处于取证文档撰写阶段（两份 md 于 10:52 / 10:54 落盘，随后 lane 返回 DONE）。

## 5. 子智能体槽位状态（重启后为全新 3 槽）

| 槽位 | 昵称 | agent_id | 档位 | 任务/子任务 | 终态 | 处置 |
| --- | --- | --- | --- | --- | --- | --- |
| lane Y | Mendel | `01a1d733-80c7-7611-81ef-742720a226ec` | qwen3.8-max / high | M0-04/S2b-3（关键路径，slack 0） | **DONE，已回执、已入库 `7c0c7c4`、已 `close_agent`** | 无损。loop 用 1/2 轮，非 STALLED |
| lane A1 | Ramanujan | `01a1d7cf-1a3b-7c23-a762-bea637ec25e6` | qwen3.8-max / high | M2-01/S2a | **INTERRUPTED，零落盘，已 `close_agent`**（关槽返回 `previous_status=running`） | 无损：派单文已入库，重派即可 |

本会话另已关槽：Meitner（lane Z · M2-01/S1）、Lorentz、Peirce、Franklin（后三者为 R11 lane，产出早已入库却长期未关槽，属**槽位泄漏**，记 R14-6）。更早已关：Huygens、Mill、Kant、Newton 等。

并发额度是**会话进程级**资源，重启后为全新 3 槽，不存在残留占用。

**A168 的强制例外（续跑时需以 A215 追认）**：A168 规定 lane Y 为同一 max lane 串行复用、禁关槽、禁档位置换，用于承接 M0-04 的 S2b-3 → S2c → … 链条。S2b-3 已入库，但原 lane 随主机重启**物理消亡**，"禁关槽/禁置换"对 S2c 客观不可满足。这是环境强制而非编排器违规，但必须显式入账，否则续跑者会误判为「有人擅自换 lane 或擅自降档」。补偿措施（必须写进 S2c 的派单文）：

1. 档位仍为 **qwen3.8-max / high**，禁借「重派」之名降档（S2c 含事务边界与跨层装配，命中手册 §6.3 强制 max 清单）。
2. 把账本 `tasks.M0-04` 的 `s2c_obligations_R13`、`remaining_sequence_R14`、`scope_waivers_R13`、`u_rulings_R13` 四键**全量**交给新 lane（尤其 A206：`JobService.__init__` 必须接受 `store` 关键字，禁反过来要求改 `deps.py:135`；A207：创建 `worker/service.py` 的**同一次提交**内删除 `deps.py:55` 的 `# type: ignore[import-not-found]`；A169：`JobStore.list_jobs` 对 `store.py` **纯追加**，既有 12 个方法的签名/函数体/SQL 文本一字不改，numstat deleted=0）。
3. 告知新 lane：S2b-3 的成品已在 `7c0c7c4`，取证三件在 `evidence/M0/M0-04/`，可直接引用不必重做。
4. 新 lane 上工第一步必须复测 HEAD/四门/收集数（铁律 §1.6），与 §2 表不符即停手回报。

## 6. 本次冻结对账本做的变更（两笔提交，逐条可核）

全部变更均为**追加或就地纠正**，无删除键（R9-5 / D-011）。

### 6.1 已随 `7c0c7c4` 入库（S2b-3 成品）

1. `budget.subtask_log` 追加第 37 条（M0-04/S2b-3，max，`result=DONE`，loop 1/2，`tokens=46000` 且 `tokens_estimated=true`）。两个 token 口径均 over_cap，如实记录不抹平：§5.1 单轮输入 ≈46k > max 40k；§15.5 累计计费 ≈2.0M+ > 200k（A183 口径；无计费表读数故为估算，按 A183(a) 记 `estimated=true` 且**不入 token 面分母**）。
2. `flash_share` 程序化重算（禁手填）：27/46 → **27/47 = 0.5745**。重算公式先做**自证**——用它重跑既有 36 条，必须逐键复现账本原值（实测 `SELFCHECK_RECOMPUTE_OK entries=36 units=27/46`）才允许写入，公式错即 `SystemExit` 拒绝提交。
3. `resume.round7_adjudications` 追加 **A211–A214**（裁定 lane 上报的 U-1…U-4）：
   - **A211**（U-1 翻转既有绊线用例）→ 采 **(a) 保留翻转**（改名 `..._and_now_produced` 并取反）。理由：该用例 docstring 自述即「jobs 侧落地即触发的绊线」，改名+取反正是它设计意图要求的显式承认；回退翻转就得保留一个与已实现事实矛盾的 `.. warning::` 占位块＝让文档说谎。覆盖面只增不减（19→30）。
   - **A212**（U-2 `detail` 无承载位）→ 采 **(a) 由既有 `relative_path` 承载** `POINTER_*`，零字段变更。(b) 新增 `detail` 会破坏 `Discrepancy` 的 8 字段冻结与前 5 字段元组逐字不变式（有守护钉死）。义务：若 S2c 之后出现真正的「同一对象多种 detail」需求，走 CR-003 而非再次重载。
   - **A213**（U-3 `__all__` 11→17）→ 采 **(a) 保留导出**。A205 的「只扩 reason 两项」按「reason 集合不增第三项」理解，实测 7→7 已满足；`POINTER_*`/`RESULT_REF_KIND` 是 detail 指针常量而非 reason，导出它们是为了消除魔法字符串。**17 即该模块 `__all__` 的新现值，后续 lane 禁「恢复」为 11**。与 FU-39②（守 `api/common.py` 的 `__all__==51`）不冲突，属不同模块。
   - **A214**（U-4 LANE-COMMON 禁写 `orchestrator/**` vs 派单文授权文末追加）→ 采 **(a) 认可窄豁免并成文化**（见铁律 §1.8）。实证：numstat 38/0 + 前 52 行 sha 双向一致 ⇒ append-only 得证。义务：并入 FU-39③ 同批落地，避免两次触碰 `orchestrator/handoff/LANE-COMMON.md`。
4. `resume.round14_lane_Y_return` 新增（完整回执索引 + 编排器复测结论 + `lane_closed=true` 及 A168 例外说明）。
5. `tasks.M0-04`：`subtask_progress["S2b-3"]="DONE"`、`subtask_progress["S2b"]` 更新为 DONE 并说明 §5:52 ①②③④⑤ 全部落地；新增 `subtask_progress_note_R14Y`、`remaining_sequence_R14`（S2c→S4→S5→S6→S8，含每棒的档位与义务）、`remaining_sequence_note_R14`。**`status` 仍为 IN_PROGRESS**，`commit` 仍为空（任务未闭合）。
6. `resume.forward_reference_registry` 新增两条路径键（见 §6.3 的 R14-5）。
7. `resume.followups` 追加 **FU-42**（在派单文末追加纠正注记 + 把 PRE-6 写进 LANE-COMMON）。
8. `resume.dispatch_preconditions_note_R14` 新增派单前置检查项 **PRE-6**。
9. `counts` 刷新：`ruff_formatted_files` 256→258、`in_scope_md` 168→170、`pytest_passed` 560→571、`mypy_source_files` 86 不变，并写 `counts_refresh_reason`（逐项归因）。

### 6.2 随本 checkpoint 提交入库

1. `dag_paused`：`false` → **`true`**；新增 `dag_paused_at`、`dag_pause_reason`（主机重启 + 人类指令要求 checkpoint 后停止开发）、`dag_pause_resume_precondition`（须人类明确「开工」指令，且 §10 步骤 1–5 全部通过）。
2. 新增 `resume.checkpoint_R14`：本件的机器可读索引（`head_before` 全 sha、四门数值、快照目录与 sha256、S2b-3 的 landing sha、S2a 的重派指令、计数器起点、进度百分比与推导口径）。
3. **PENDING 精确回填**（按 id/agent_id 匹配，禁按位置盲改）：把 `7c0c7c4` 回填进 `budget.subtask_log` 第 37 条的 `commit`、`resume.round14_lane_Y_return.commit`、`resume.in_flight_agents[lane=Y].landing_commit` 三处。
4. `budget.subtask_log` 追加第 38 条（M2-01/S2a，max，`result="INTERRUPTED_HOST_REBOOT"`，`tokens=null`——无计量句柄一律记 null，**禁估算**）；据此重算 `flash_share_tasks` 0.5745 → **27/48 = 0.5625**、`flash_share_dev_lanes` 0.32 → **8/26 = 0.3077**，`flash_share_tokens` 保持 **0.6655**（null 不入分母）；`guardrail_status` 以 append-only 追加 R14 注记（原 `verdict` 文本不改写）。
5. `resume.in_flight_agents` 与 `resume.round14_predispatch.lanes` 的 **A1 条目回填 `agent_id`/`nickname`**（Ramanujan，此前登记为 `TO_SPAWN` 且缺 id，属 R14 派单登记漏项），`status` 改为 **`INTERRUPTED_BY_HOST_REBOOT`**，并记 `snapshot_ref`（零落盘，无需恢复）与 `resume_action`（以新 max lane 重派，派单文不变）。
6. 新增 `resume.in_flight_agents_note_round14_checkpoint`（说明冻结时刻槽位真相与 A168 例外；不覆盖原 `in_flight_agents_note_round14`）。
7. `resume.q_verify_wave1.stage`：`DISPATCHED_REGISTERED` → **`RETURNED_LANDED`**，追加 `landing_commit="7db82a7"`、`stage_corrected_at`、`stage_correction_reason`。git 实证：该提交标题即「wave1 出口 Q 复核入库（11 门实测 rc 回填）+ A158–A167」；账本 `tasks.M0-02`/`tasks.M0-03` 的 gates 中 `"rc": null` 计数实测为 **0**、status 均 DONE。**原键一个不删**，只改 `stage` 并追加纠正说明。
8. `resume.round14_self_corrections` 追加 **R14-6 / R14-7**（见 §6.3）。
9. `resume.followups` 追加 **FU-41**（见 §11）。
10. `budget.dispatched_not_yet_returned` 置 **0**（两条在飞 lane 均已终止）。
11. `counts` 刷新：`ruff_formatted_files` 258→**259**、`in_scope_md` 170→**171**（只新增本件 1 个 .md）、`mypy_source_files` **86** 与 `pytest_passed` **571** 不变。
12. `updated_at` 刷新。

### 6.3 本会话记下的三条编排器自纠（如实上报，含自己的错）

- **R14-5（已随 `7c0c7c4` 入库）**：首次 `run_commit` 被第 7 步悬空引用门拦下并**原子回滚**（HEAD 未动、索引已 reset、台账已 `checkout` 还原 ⇒ 零半成品、零账本腐化）。根因经 `git show HEAD:` 定性：被报的两处引用（M0-04 的 `ac.md` 与 M0-04 摘要）是 **S1 设计冻结件原文**（HEAD 版 :68 与 :91，各命中 1 次；HEAD 170 行 / 工作树 208 行），**不在**本棒追加的 38 行内 ⇒ 属此前提交遗留的**未登记前向引用**，而当时 registry 只有 A173 一条。处置：按 A173 先例登记两条路径键（注明 `lands_in = M0-04/S8` 与豁免作用域），本提交以 `allow_dangling` **精确**豁免这两条、**不放宽扫描本身**。预防升为铁律 §1.9。
- **R14-6（本提交）**：**槽位泄漏**。Lorentz / Peirce / Franklin 三条 R11 lane 的产出早已入库，却长期未 `close_agent`，白占并发额度并迫使后续轮次「留白」；违反手册 §15.11（每轮派单前必须显式释放上一轮槽位）。本会话已全部关槽（含本轮的 Mendel 与 Ramanujan）。纠正：把「**回收即关槽**」写进每轮出口的固定检查项（§10 步骤 8）。
- **R14-7（本提交）**：本会话两次违反铁律 §1.2——用 `wsl.exe -e bash -lc "…"` 传含 `$`、嵌套引号与 `|` 的命令，导致 `python3 -c` 的参数被吞（rc=1，`Argument expected for the -c option`）与 `grep` 模式被破坏（对 `scripts/orch_harness.py` 明明有 20+ 个 `def` 却报 **0 匹配**）。两次均在同一轮内自查发现并回退到 driver.sh 通道，未污染仓库。危害形态是**假阴性**（比报错更危险：会让编排器误判「该符号不存在」进而做出错误裁定）。纠正：把「禁 `-lc` 传参、一律走 here-string→LF→无 BOM→driver.sh」由经验升级为 §1.2 铁律明文，并要求任何「命中 0 / 文件不存在」类结论必须用第二种口径复测后才可入账。

**号段说明**：R14-2 与 R14-3 曾出现在未入库的会话草稿里，为避免 `round14_self_corrections` 出现 id 乱序（append-only 禁重排），这两个号**作废不补**，本句即其唯一说明。

## 7. 共享文件写权锁表（续跑时必须强制；建议以 A215 同批终裁）

| 共享文件 | 冻结时刻持锁者 | 释放条件 | 下一顺位 | 备注 |
| --- | --- | --- | --- | --- |
| `src/campaignlab/infra/db/repositories.py` | **已释放**（原 M0-04/S2b-3，随 `7c0c7c4` 入库即释放） | — | **M2-01/S2b**（追加 3 个仓储约 20 方法） | A204 明确 append-only（禁 `list_all`，实测 `def list_all`=0）；A210 拆分 S2a/S2b 的**唯一原因**就是这把锁，现锁已开 ⇒ **S2b 可与 S2a 并行排期**（但两者同属 M2-01 串行链，仍按 S2a→S2b 顺序） |
| `src/campaignlab/api/common.py` | M2-01/S2a | S2a 入库即释放 | M0-04/S4（追加 `JobPage`，A91） | 纯追加，numstat 删除行必须为 0；`len(__all__)` 现值 **51**，是 `tests/unit/test_domain_errors.py` 的字面量断言对象（FU-39② 要把它纳入守护） |
| `src/campaignlab/api/app.py` | **争用** | — | M0-04/S4 先（关键路径，≤3 行）→ 之后 M2-01/S2b（≤6 行） | 两 lane 都要挂载路由；裁定 M0-04/S4 优先，M2-01 的挂载拆成独立微步骤串行执行 |
| `src/campaignlab/api/deps.py` | M2-01/S2b | S2b 入库即释放 | — | 单一持锁者，无争用 |
| `src/campaignlab/worker/store.py` | **M0-04/S2c** | S2c 入库即释放 | — | A169：`JobStore.list_jobs` 纯追加，既有 12 方法一字不改（deleted=0） |
| `src/campaignlab/worker/deps.py` | **M0-04/S2c** | S2c 入库即释放 | — | A207：创建 `worker/service.py` 的同一提交内必须删掉 :55 的 `# type: ignore[import-not-found]`，否则全表 mypy 判红 |
| `orchestrator/handoff/M0-04-design.md` | M0-04 链（S2c 起） | 各子任务入库即释放 | — | 仅允许**文末追加**（A214 窄豁免），禁改写已冻结段；前 52 行 sha 恒为 `a5e38074…` |

违反锁表的后果是「两个 lane 在同一时间窗追加同一文件」＝写集相交，破坏并行判据（PRE-4/PRE-5）与 A196① 的时序禁令，会在合并时产生**静默覆盖**。

## 8. 计数器与序号起点（续跑第一个编号从这里开始）

- 终裁（A 序列）：最后 **A214** → 下一个 **A215**。容器是 `resume.round7_adjudications`（append-only 列表，现 132 条）；**禁新建 A 序列容器**，禁按位置盲插。
- 自纠（R 序列）：R14 现有 R14-1 / R14-4 / R14-5 / R14-6 / R14-7 → 下一个 **R14-8**（R14-2、R14-3 号段作废，见 §6.3）。
- 轮次：本 checkpoint 属 **R14**；续跑首个派单轮为 **R15**。（scratch 里的 `r15*.sh` / `r16a.sh` 是本会话的状态探针脚本，与轮次编号无关，勿混淆。）
- 缺陷：D-001…D-042 连续无缺号（`tests/unit/test_state_ledger.py` 钉死分母与连续性）→ 下一个 **D-043**。
- CR：下一个 **CR-003**。
- followups：FU-1…FU-42 → 下一个 **FU-43**。
- counts：`ruff_formatted_files` **259** / `in_scope_py` **88** / `in_scope_md` **171** / `mypy_source_files` **86** / `pytest_passed` **571**。引用时一律指向账本键，禁写死数字（D-012/D-014）。
- `worker/integrity.py` 的 `__all__` 现值 **17**（A213）；`api/common.py` 的 `__all__` 现值 **51**（未变）。

## 9. 护栏现状与回升路径（flash_share）

目标（手册 §6.6）：flash 承担 ≥60% 子任务数、token 占比 ≤35%。

实测（本 checkpoint 重算后）：`flash_share_tasks` = **0.5625**（27/48，未达标；本会话内 0.5870 → 0.5745 → 0.5625 两度下滑）；`flash_share_tokens` = **0.6655**（未达标；口径为「仅计 tokens 非 null 且非 estimated 的条目」，known 10 条 / 1,190,000，其中 flash 792,000）；`flash_share_dev_lanes` = **0.3077**（8/26）。

**两度下滑的如实归因**：① S2b-3 是 max 档（只增分母）；② S2a 被主机重启打断、max 档产出归零（只增分母、零分子）。第 ② 项是纯粹的**浪费**，已按实入账而不隐藏。

**回升路径（已排定，不需新增工作，禁为凑配比补造任务）**：

- M0-04 剩余 **S4 / S5 / S6 / S8 四个全 flash**（卡片档位表已钉：10k / 14k / 12k / 9k）。
- M2-01 剩余 **S3 / S4 / S5 / S6 / S7 五个全 flash**（9k / 9k / 8k / 7k / 6k）。
- 这 9 个 flash 子任务入账后：units_flash 27→36、units_total 48→57 ⇒ 36/57 = **0.6316 ≥ 0.60**，护栏①回正；token 侧因 flash 单件预算远低于 max，占比亦会回落。
- 因此护栏①的破口是**时序性**的（max 密集的设计/契约/并发阶段先走，flash 密集的机械铺开阶段后走）+ 一次主机重启的意外损失，**不是档位分配错误**。**严禁**用「把 max 件谎报成 flash」或「拆细 flash 件刷单位数」修复（C10 + 手册 §15.5：`tier_planned` 与 `tier_used` 不符即记缺陷并停该任务）。

## 10. 续跑 runbook（下次会话，人类给出「开工」后逐步执行）

1. **复测（禁采信任何摘要，含本件）**：`git rev-parse --abbrev-ref HEAD` 应为 `m0-framework`；`git log --oneline -1` 应为本 checkpoint 提交；`git rev-list --count HEAD` 应为 **101**；`git status --porcelain` 应为**空**（工作树干净）。任一不符 → 停手，先 `git reflog` 考古再决定。
2. **读本件 + `orchestrator/state.json` 的 `resume.checkpoint_R14`**，并读 `docs/delivery/LONG-HORIZON-ORCHESTRATION.md` 恢复流程规范（档位分配判据、loop engineering 的 3+1 复审上限、每轮出口的关槽检查项）。
3. **环境体检**：`bash scripts/doctor.sh`（预期 RESULT=HEALTHY；WARN 可能因工作树状态或 `DOCTOR_SKIP_VERIFY` 出现，属预期语义，见账本 `resume.environment.doctor_summary.warn_semantics`）；确认 `uv run --no-sync python -V` = **3.14.10**（铁律 §1.3 的前提）。主机重启后若 WSL 侧字体/依赖丢失，先补 `fonts-noto-cjk` 再派单。
4. **四门基线复跑**：确认 ruff_format 259 / ruff_check passed / mypy 86 / pytest 571 与 §2 一致；不一致即先查因，禁在红基线上派单。
5. **解除暂停**：确认人类已给出明确「开工」指令后，把 `dag_paused` 置回 `false` 并记 `dag_resumed_at`；**在此之前禁止 spawn / send_input 任何开发 lane**。
6. **R15 派单（并发上限 3，档位与锁表照 §7 / §9）**：
   - lane Y′（**qwen3.8-max** / high，关键路径）：**M0-04/S2c**，派单文 `orchestrator/handoff/R13-lane-Y-M0-04-S2c.md` 已入库；必须附 §5 的 A168 例外补偿措施 1–4（含 A206/A207/A169 三项义务）。入库后释放 `worker/store.py` 与 `worker/deps.py` 锁。
   - lane A1′（**qwen3.8-max** / high）：**M2-01/S2a 从零重做**，派单文 `orchestrator/handoff/R14-lane-A1-M2-01-S2a.md` 已入库（§11.1 领域层 6 模块 + §11.2 契约 DTO 面；硬禁清单照抄，含「禁碰 `repositories.py`」一条现可放宽为「S2b 才可碰」，需以 A215 明示）。
   - 第 3 槽：按 R14 的实测依赖面，除 M2-01 外无可派独立开发件（M1-01 dep M0-04；M2-02 dep M2-01+M0-04）⇒ **留白优于派废单**；可用来跑非关键路径的编排器自有债务（FU-39 / FU-40 / FU-41 / FU-42），但档位须为 **flash**（同时帮助护栏①回升）。
   - 派单前对 `orchestrator/handoff/M2-01-design.md`（1322 行）做一次**前向引用普查**（R14-5 的预防面），把指向未来交付件的 `evidence/**` 路径同批登记，避免它在 S2a 入库时重演拦停。
7. **每轮出口固定检查项**：回执归档 → `subtask_log` 追加 + flash_share **程序化重算（先自证能复现旧值）** → PENDING 按 id/agent_id 精确回填 → **`close_agent` 显式释放槽位** → `run_commit` 入库 → 复测 HEAD 推进与 counts。
8. 之后按 wave 顺序无人值守推进至 **29 任务 / 11 波 / 47 条 AC** 全绿；loop engineering 上限 **3+1**（3 轮自迭代 + 1 轮复审），超限即升级为缺陷单并停该子任务，禁无限重试。
9. **wave 出口的硬门**：wave9 出口必须校验 M5-P01 已 PASS 才可进 wave10（FU-38）；wave7 派单 M3-P02 前必须先闭合 FU-34 与 FU-36。

## 11. 未结 followups 与已知债务（42 条中 33 条未闭）

已闭 9 条：FU-8、FU-14、FU-22、FU-23、FU-24（ADJUDICATED）、FU-29、FU-32、FU-33、FU-35。

**有明确波次前置约束**（必须在其前置波次之前处理）：

- **FU-34**（OPEN）：为 M3-P02 / M5-P01 / M5-03 三张卡补切契约切片（含 A170② 的 `__indexes` 剔除规则）。A179 已裁定顺延，**必须在 wave7 派单 M3-P02 之前完成**。
- **FU-36**（OPEN）：wave7 派单前的两件准备（含把 M3-04 卡内 U-1 标注为 RESOLVED_BY_A130）。
- **FU-37**（OPEN）：把 M4-03 / M3-P02 / M4-P01 三个 id 补进 `acceptance.primary_owner[AC-MR-12].cross_ref`。
- **FU-38**（OPEN）：在 wave9 出口增设硬门——M5-P01 未 PASS 即**不得**进入 wave10（wave10 是 `mode=serial` 的单环，无并行冗余可吸收上游缺失）。
- **FU-30**（OPEN）：接线面债务，须在依赖它的任务启动前闭合。

**非关键路径、可与开发 lane 并行的编排器自有债务**（适合第 3 槽的 flash 档）：

- **FU-39**（OPEN）：工装面三项收口，**必须同批处理**（避免两次触碰 `scripts/orch_harness.py` 与 `pyproject.toml`）：① 评估把 `scripts` 纳入 mypy 域；② 把 `api/common.py` 的 `__all__==51` 纳入守护；③ 补齐 `orchestrator/handoff/LANE-COMMON.md` 的通用约束段——**A214 追加要求**：把「`orchestrator/**` 禁令为默认值 + 派单文可授予单文件仅文末追加的窄豁免」成文写进去。
- **FU-40**（PENDING）：清理陈年 PENDING 回填（round6–round8 遗留）。**本会话实测确认**：`tasks.M0-02`、`tasks.M0-03`、`tasks.M0-03b` 的 `commit` 字段仍为空，而 `tasks.M0-01`=`061c577d503f`、`tasks.M0-P01`=`baa7389f413b` 已填。回填需逐条 git 考古考证归属提交，**盲改等于伪造历史**，故刻意留到非关键路径窗口与 FU-39 同批做。
- **FU-41**（PENDING，本 checkpoint 新立）：`tasks.M0-03b.gates` 实测仍有 **2 处 `"rc": null`**（违反 A109③「gate 必须给真值与 evidence 指针」），而其 status 已是 PASS_WITH_TODO。需在非关键路径窗口补测真值，或显式记为 N/A 并说明理由。与 FU-40 同批做最省（都要动账本同一区域）。**登记次序说明**：FU-41 的内容在 `7c0c7c4` 之前即已识别，但该提交只追加了 FU-42，故本条在列表中位于 FU-42 之后——id 正确、顺序倒置，按 append-only 原则不重排。
- **FU-42**（PENDING，随 `7c0c7c4` 立）：在 `orchestrator/handoff/R13-lane-Y-M0-04-S2b-3.md` **文末追加**纠正注记（原文依 D-011 不改写），说明其 §3 存在「删 warning 占位块」与「禁删改既有 19 条用例」的互斥指令，已由 A211 裁定为保留翻转、并由 R14-4 记为编排器 authored 缺陷；同时把 PRE-6（派单前反查断言对象）写进 LANE-COMMON，与 FU-39③ 同批落地。
- 其余 FU-1…FU-7、FU-9…FU-13、FU-15…FU-21、FU-25…FU-28、FU-31：状态 PENDING/OPEN，无波次前置约束，按 `resume.followups` 内的 owner 字段分派。

**已闭合的 S2b-3 相关义务（续跑时不要重复做）**：design §5:52 的 ④⑤ 判据、`JobRepository.list_for_workspace`、`Discrepancy` 的 `relative_path` 承载 `POINTER_*`、`__all__`=17 —— 全部已在 `7c0c7c4` 落地并复验。

## 12. 本 checkpoint 的自证

- **抢救了什么**：把关键路径上≈90% 完成、阳性对照已全绿但**尚未入库**的 S2b-3（4 改 + 3 新，共 623 行增量）在主机重启前送进 git 历史（`7c0c7c4`，四门全绿）。这是本次冻结最大的价值——工作树从「4 条未提交改动 + 1 条未跟踪」变为**完全干净**。
- **门禁真的在把门**：首次入库被悬空引用门拦下并**原子回滚**（HEAD 未动、台账已还原），根因查到是 S1 冻结件遗留的未登记前向引用，按 A173 先例登记 + 精确豁免后第二次通过。未通过放宽门禁来「让它过」。
- **计数全部实测**：pytest 571 由「HEAD 冻结树收集 539 / 工作树收集 550 / env-ignores 静态收集 16+5=21」实算得出并被冻结树实跑对账；ruff 258→259 由 in_scope md 计数实算；flash_share 重算公式先自证能复现账本原值（`SELFCHECK_RECOMPUTE_OK`）才允许写入。
- **快照**：4 次采样证明工作树自 10:34 起稳定，快照目录 244 KB，含完整 diff 补丁与逐文件 sha256；入库后与 §4.2 逐字一致（互为印证）。
- **未做的事（刻意）**：未为修复 flash_share 而补造工作（C10）；未改写任何历史值（D-011）；未把 M0-04 判为 DONE（S2c 未做）；未开放 wave3（M0-04 是 21 个 TODO 任务的唯一解锁点）；未在 `dag_paused=true` 生效期间派发任何新 lane。
- **数据损失面（如实）**：仅 Ramanujan 的 S2a 上下文（**零落盘**，重派无损）与 Mendel 上下文中未落盘的中间推理（其交付件已全部入库，无损失）。**代码、取证、账本三者零损失**。
- **续跑充分条件**：工作树干净 + HEAD 明确 + 四门数值已知 + 两条链的派单文均已入库 + 锁表已更新 + 计数器起点已记 + `dag_paused=true` 防误动 ⇒ **具备断点续跑条件**，只等人类「开工」指令。
