# R19-CHECKPOINT-S1PAUSE — 人类授权停机检查点（wave-3 / lane S1 已回传未入库）

> **本件性质**：`kind = HUMAN_AUTHORIZED_STOP_CHECKPOINT`。这是**人类显式授权的暂停**，不是编排器自行停工。
> **权威口径**：机器可读权威值一律以 `orchestrator/state.json` 的 `resume.checkpoint_R19_S1pause` 为准；本件是**人读续跑手册**，两者同批入库、同批对账。凡本件出现的数字均为**写入时点实测**，续跑方必须**重新实测**后再用（PRE-37 第 1 款：禁沿用散文数字）。
> **体例先例**：`orchestrator/handoff/R19-CHECKPOINT.md`（304L/35043B/`b80e41f17d0e`）、`orchestrator/handoff/R17-CHECKPOINT.md`、`orchestrator/handoff/R14-CHECKPOINT.md`。

---

## §0 一句话状态

**wave-3 的 lane S1（M1-01 设计棒 · Peirce · `qwen3.8-max` high · `slack=0` 关键路径）已回传、已由编排器独立复验 37/37 GREEN、取证件已建好，但 landing 批（tag `R19-landS1`）的台账写入驱动只写到 5 片中的第 2 片 ⇒ 交付件仍是未跟踪件、尚未入库。本次停机点＝「写第 3 片驱动脚本」之前。零数据损失。**

---

## §1 停机授权与范围

| 项 | 值 |
|---|---|
| 授权人 | 项目负责人（人类） |
| 授权原文 | 「保存 checkpoint，然后暂停 DAG 交付工作流」 |
| 停机时点 | 本批（tag `R19-ckS1pause`）入库并 push 成功之后 |
| 死命令是否仍有效 | **仍有效**：「没有全部完成前不允许停，必须 DAG 开发流程全部结束」。本次是**暂停**不是**终止**；续跑需人类明确的「开工」指令（与 `dag_resume_authorization_R18` / `_R19` 同源） |
| 停机期间禁做 | 禁 `spawn_agent`、禁 `close_agent`、禁任何 `git add/commit/push`、禁改台账。只允许**只读**实测 |
| 停机原因（本次） | ① 人类要求暂停；② 上一轮遭遇模型服务端 `429 Too Many Requests`（`exceeded retry limit`，request id `b5bd0289-99b8-4c92-950a-6bcc90cae44c`）⇒ 配额/限流风险，需要人类决定续跑节奏 |

---

## §2 git / 工作树 / 远端快照（实测）

| 项 | 值 |
|---|---|
| 仓库 | WSL2 `/home/szf/dev/CampaignLab` |
| 分支 | `m0-framework` |
| remote | `git@github.com:shaozhongfei001/CampaignLab.git` |
| **HEAD（本批入库前）** | `465282f`（全 `465282f816bc8e94302636bb81d1ff56d42f5046`，台账 tag `R19-backfill-S6landBF`） |
| origin/m0-framework | `465282f` ⇒ **HEAD == origin，已对齐** |
| 提交总数（本批前） | **143** |
| `git diff --numstat` | **0 行**（零修改既有被跟踪文件） |
| `git diff --cached` | **空**（零 staged 残留） |
| `git stash list` | **空** |
| merge/rebase/lock 残留 | **无**（`.git/MERGE_HEAD`、`rebase-merge`、`rebase-apply`、`CHERRY_PICK_HEAD`、`index.lock` 全 ABSENT） |
| **未跟踪件（4 件，全部属 lane S1 本批待入库面）** | `orchestrator/handoff/M1-01-design.md` · `evidence/M0/ORCHESTRATOR/r19-m1-01-s1-landing/00-index.md` · `evidence/M0/ORCHESTRATOR/r19-m1-01-s1-landing/lane-receipt-S1-raw.md` · `evidence/M0/ORCHESTRATOR/r19-m1-01-s1-landing/gates/V-independent-reverify.log` |
| 越界垃圾件 | **0**（`=` 前缀件 ABSENT ⇒ PRE-42③ 事故未复发） |

> **注**：本 checkpoint 批自身会新增 1 件 `.md`（本文件）⇒ 入库后未跟踪件仍是上述 4 件（本文件已 `git add`）。**这 4 件在停机期间必须原样留在工作树，禁删禁改**——它们是 lane S1 的唯一交付物与取证链，删除即真损失。

---

## §3 台账快照（`orchestrator/state.json`，append-only / D-011）

### 3.1 counts（权威读数，冻结索引树口径）

| 键 | 本批入库前 | 本批入库后（预期，由 `expect_counts` 逐条对账） |
|---|---|---|
| `ruff_formatted_files` | 354 | **355** |
| `mypy_source_files` | 130 | **130（不变）** |
| `pytest_passed` | 852 | **852（不变）** |
| `in_scope_py` | 132 | **132（不变）** |
| `in_scope_md` | 222 | **223（+1，本文件）** |
| `total` | 354 | **355** |

双镜像要求（R19-5）：顶层 6 键与 `counts.ruff_formatted_files_composition` 的 3 键镜像必须**同一赋值点派生**并当场断言相等。

### 3.2 权威基线

- `resume.baseline_authoritative.current.head` = `dafe0f0`（tag `R19-landS6`）——中间的 `465282f` 是**纯台账批**，依 PRE-36 / A261 **不推进**基线。
- `history` 条目数 = **26**（本批因**内容面变更**（+1 md）⇒ 必须追加第 27 条并推进基线）。
- 语义位点四分（R19-14，禁互相覆盖）：(a) 本批入库前 HEAD = `465282f`；(b) 本批要**兑现**的那个提交 = `465282f`；(c) 上一**权威** head = `dafe0f0`；(d) 新权威节点的 `head_before` = `465282f`。

### 3.3 治理活指针 `resume.counters_next`（本批入库前）

| 号池 | 下一个可用 | 本批消耗 |
|---|---|---|
| `adjudication` | **A277** | 0（15 条裁定 A277–A291 **递延**到 S1 landing 批） |
| `self_correction_R19` | **R19-19** | 0（R19-19 / R19-20 **递延**） |
| `defect` | **D-053** | 0 |
| `precondition` | **PRE-44** | 0（PRE-44 **递延**） |
| `followup` | **FU-67** | 0（FU-67 / FU-68 **递延**） |
| `dispatch_log_index` | 20 | 0 |
| `in_flight_agents_index` | 13 | 0 |
| `subtask_log_index` | 51 | 0（S1 样本 **递延**到 landing 批） |
| `baseline_history_index` | 26 | **1**（本批追加第 27 条） |

### 3.4 哨兵链（PRE-35 全量普查）

- 本批入库前**活哨兵 = 5 处**，与 `resume.commit_backfill_pending_R19_S6landBF.sites_expected_after_mut` **逐字集合相等**：
  `$.resume.commit_backfill_pending_R19_S6landBF.status` · `$.resume.round19_self_corrections.[16].commit` / `.commit_full`（R19-17）· `[17].commit` / `.commit_full`（R19-18）
- 本批**兑现这 5 处**（回填为 `465282f` / 全 sha），并为本提交自身的 sha 登记**新哨兵链** `resume.commit_backfill_pending_R19_ckS1pause`（权威位点清单由其 `sites_expected_after_mut` 承载，由 mut **末断言的实测集合回写**，禁凭记忆枚举）。
- **续跑义务**：下一次提交（预期就是 `R19-landS1`）必须先做全量普查并与该键逐字集合相等，再回填。

### 3.5 其它治理量

| 项 | 值 |
|---|---|
| R19 裁定条数 | **15**（末条 `A276`） |
| R19 自纠条数 | **18**（末条 `R19-18`） |
| defects | **52** |
| change_requests | **2**（CR-002 已按选项 B 合入） |
| followups | **66**（未闭 **52**；治理簇 FU-50/52/53/58/61/62/63/64/66 仍 OPEN） |
| `next_actions` | **123** 条 |
| `budget.subtask_log` | **51** 条样本（入护栏分母 **50** 条，1 条 `tier_used == orchestrator-self-served` 排除） |
| `budget.dispatched_not_yet_returned` | **1**（＝ Peirce 未关账；**本批不动**，landing 批才归零） |

---

## §4 在飞 lane 与并发槽（停机时的真实状态）

| 索引 | lane | task | 昵称 | 状态 | 档位 |
|---|---|---|---|---|---|
| [0]–[10] | Y2/A1b/S4/S2b-1/S5/S2b-2/S6/S3/S8/S4/S5 | M0-04 / M2-01 | Lorentz, James, Anscombe, Hooke, Kierkegaard, Mendel, Lorentz, Nash, Planck, Wegener, Sagan | 全部 `RETURNED_LANDED`（[1] James 为 `RETURNED_ERRORED_LANDED`，[7] Nash 为 `RETURNED_DONE_WITH_GAP`） | — |
| **[11]** | **S1** | **M1-01** | **Peirce** | **`IN_FLIGHT`** | `qwen3.8-max` high |
| [12] | S6 | M2-01 | Beauvoir | `RETURNED_LANDED`（`close_agent` 已调用，正文因 R19-18 不可复得，已如实置 null） | `qwen3.8-flash` |

**关键：`close_agent(Peirce)` 尚未调用 ⇒ 并发槽仍占用 1，且运行环境 `<subagents>` 清单实测仍含 `01a1e5f1-850c-7683-876a-a1720bae9139: Peirce`。**

- **好处**：无悬空易失态。`wait_agent` 的原始回执**已按 PRE-43 即时落盘**（见 §5.2），所以即便 Peirce 的槽位在停机期间被运行环境回收，也**零信息损失**。
- **续跑义务（PRE-43 第③款，硬规则）**：landing 批 push 成功之后调用 `close_agent(target=01a1e5f1-850c-7683-876a-a1720bae9139)`，**返回文本必须先原样落盘** `.orch_tmp/orch_S1_close_agentret.txt`（UTF-8 无 BOM / LF / 末换行），**再**据以写 `in_flight_agents[11].close_agent_returned`。禁重蹈 R19-18。
- 若续跑时实测该 agent 已 `not found`：按 R19-18 的既定处置——`previous_status_head_verbatim` **刻意置 null 并附 caliber 说明**，一致性锚改用**在仓 sha 锚定证据**（`lane-receipt-S1-raw.md`），禁凭记忆补写（A183）。

---

## §5 已完成的工作（全部有在仓/在盘 sha 锚定，停机不丢）

### 5.1 lane S1 交付件（**一字未改**，编排器零改动）

| 文件 | face | 说明 |
|---|---|---|
| `orchestrator/handoff/M1-01-design.md` | **1301L / 159632B / `99dd191f43b3`**（全 `99dd191f43b343f5fc0c477d85b50cb9ad26d312024977c2fd4173676c809e13`） | §0–§14 **十五章齐备**；§11 共 **11** 个子节，棒号恰为 **S2–S8**；§12 的 **U-1…U-15** 连续无缺号；§10 覆盖 **V1–V16**（含 A275 的 `V4a`/`V4b` 形态） |

### 5.2 取证链（编排器自办 3 件）

| 文件 | face |
|---|---|
| `evidence/M0/ORCHESTRATOR/r19-m1-01-s1-landing/00-index.md` | 76L / 8412B / `b7e09eed6c69` |
| `evidence/M0/ORCHESTRATOR/r19-m1-01-s1-landing/lane-receipt-S1-raw.md` | 166L / 15409B / `76b3c0ac4009`（**字节级 cat** 原始回执 + PRE-43 链 + 传输层截断如实注记） |
| `evidence/M0/ORCHESTRATOR/r19-m1-01-s1-landing/gates/V-independent-reverify.log` | 52L / 16177B / `dc242889ab1b`（`.log` **不入** ruff 分母，但**会入库**：`.gitignore` 的 `!evidence/**/*.log` 反排除） |

- Peirce 的 `wait_agent` 原始回执落盘件：`.orch_tmp/orch_S1_wait_agentret.txt` = **119L / 11807B / `cf7a926affa0`**（PRE-43 第①款）。传输层截断 ~916 tokens（§6 STRUCT 区），**已如实登记**；零信息损失（全部事实可从在仓交付件重新实测）。

### 5.3 编排器独立复验（PRE-29 禁采信自报）＝ **VERIFY RESULT: GREEN，37 判据 / 0 FAIL**

脚本 `.orch_tmp/orch_v1s.py`（254L / 16551B / `597975913c55`），逐字日志已归档为 §5.2 的 `.log`。已复验通过的关键项：

- 交付件 face 逐字对撞 · 编码四判据（无 BOM/CR/NUL/C0C1 且末换行）· 工作树只有本棒 1 件 `??` · `numstat` 0 行 · PRE-40 冻结面 **8 件** sha 未变
- 工作树 `ruff format --check .` = **355**（＝台账 354 ＋ 未跟踪 in-scope 1，**R11-3 恒等式**）· `ruff check` All checks passed · `mypy` **130** · 全量 `pytest` **852 passed** · 契约门 `CONTRACT CHECK PASS 登记项=13 实测差异=13 元校验=6`
- §11 子节 **11** 条且棒号恰为 S2–S8 · §12 的 U-1…U-15 连续 · §10 覆盖 V1–V16 · **A275** 独立复测（全文无任何一行含两个 `-k`）· 卡片 `:14–:18` 的 **6** 个 `-k` 字面量全部落在 §10 · **A276** 包标记已点名
- FU-59 成果在位：`IF_MATCH_PATTERN` 实存 / 在 `__all__` 内 / 类型 `str`（值 `^"[1-9][0-9]*"$`）/ `len(common.__all__)` = **80** ＋ 单源守护 **11 passed**
- **独立重跑** lane 的 `s1m1_selfcheck.py` **RC=0**（C3/C7/C8/C9a/C9b/C10 六条 OK；既有符号对撞 **104/105**，唯一缺失＝本文标「待创建」的 `api/deps.py::ImportService`）
- **阳性对照 PC-A…PC-E 全部判红**（判据有牙自证，PRE-33）

### 5.4 断点完整性自检（429 中断之后跑的）＝ **30/30 GREEN**

脚本 `.orch_tmp/orch_integ1.py`。六面：A git 完整性 7/7 · B 交付件 face 对撞 4/4 · C PRE-43 易失态落盘 3/3 · D 驱动碎片完整性 10/10 · E 台账一致性 7/7 · F 仓内工具在位 4/4 ⇒ **`INTEGRITY RESULT: GREEN（零损失，可断点续跑）`**。

### 5.5 入库驱动脚本（**5 片范式，已写 2 片**）

| 片 | 文件 | face | 内容 | 状态 |
|---|---|---|---|---|
| 1 | `.orch_tmp/orch_s1l1.py` | 274L / 17277B / `1d42f63156cd` | 模块 docstring + 全部常量 + `preflight()`（**41 判据，实测 GREEN**） | ✅ 已写，py_compile OK |
| 2 | `.orch_tmp/orch_s1l2.py` | 195L / 19630B / `18dfa21e3645` | `MSG`（提交信息全文）+ `mut()` 的 §① counts 双镜像 §② 兑现 5 哨兵 §③ 权威基线推进 + history 追加 | ✅ 已写，py_compile OK |
| **3** | `.orch_tmp/orch_s1l3.py` | — | §④ **15 条裁定 A277–A291** 写入 `resume.round19_adjudications` | ⬜ **← 精确恢复点** |
| 4 | `.orch_tmp/orch_s1l4.py` | — | §⑤ `round19_lane_S1_return` + `subtask_log` 第 52 条样本 + `dispatched_not_yet_returned` 1→0 + `in_flight_agents[11]` → `RETURNED_LANDED` + 护栏程序化重算 + `tasks.M1-01` 状态面 | ⬜ 待写 |
| 5 | `.orch_tmp/orch_s1l5.py` | — | §⑥ 自纠 R19-19 / R19-20 + 立规 PRE-44 + FU-67 / FU-68 + FU-66 扩围 + `counters_next` + 新哨兵链 + `next_actions` + 末断言 + `main()` | ⬜ 待写 |

合并与执行范式（既有）：`cat orch_s1l1.py orch_s1l2.py orch_s1l3.py orch_s1l4.py orch_s1l5.py > orch_s1l.full.py` → `py_compile` → `--preflight-only` → `--dry-mut` → 真提交 → push → 独立 post-verify。

---

## §6 进度总账（四口径，全部程序化实测）

| 口径 | 进度 | 明细 |
|---|---|---|
| **任务** | **6/29 ≈ 20.7%** | DONE 4（M0-02 / M0-03 / M0-04 / M0-P01）＋ PASS_WITH_TODO 2（M0-01 / M0-03b）；IN_PROGRESS 2（M1-01 / M2-01）；TODO **21** |
| **波次** | **3/11 ≈ 27.3%** | wave-0/1/2 已交付；**wave-3 进行中**（L1: M1-01→M1-02→M1-03 ∥ L2: M2-01→M2-02→M2-03）；wave-4…10 未开闸 |
| **关键路径** | **3/14 ≈ 21.4%** | 已过 M0-01 / M0-02 / M0-04；**下一个＝ M1-01（slack=0，正在入库）**；其后 M1-02 → M3-01 → M3-02 → M3-03 → M4-01 → M4-02 → M4-03 → M5-01 → M5-02 → M5-03 |
| **验收 AC** | **≈4–5 / 47 ≈ 10%** | 已判：AC-001 `PASS_WITH_TODO`、AC-034 `PASS_WITH_TODO`（wave1 复合口径，来源 Q lane Newton 的 verdict §6）、AC-029 / AC-031（M0-04）、AC-035（M0-02）。**AC-002/003/004 归 M2-01/S7**、**AC-005/006 归 M1-01/S8**，均未判 |

里程碑分布：**M0（6 任务）100% 交付** · **M1（5）** M1-01 在飞、余 4 全 TODO · **M2（4）** M2-01 的 9 棒已回收、只差 S7 判 AC，余 3 全 TODO · **M3（6）/ M4（4）/ M5（4）全 TODO**。

> `state.wave` 字段实测仍是 **2**（陈旧指针，实际已在 wave-3）。按 D-011 append-only **不改写**，续跑方以 `resume.round19_*` 与 `waves` 定义为准。

---

## §7 续跑 runbook（冷启动可执行，逐步）

**第 0 步 · 接管自检（只读）**
1. `export PATH=/home/szf/.local/bin:/home/szf/.cargo/bin:/usr/bin:/bin; cd /home/szf/dev/CampaignLab`
2. 实测 `git rev-parse HEAD`、`git rev-parse origin/m0-framework`、`git status --porcelain -uall`、`git diff --numstat`，与本件 §2 对撞。**若 HEAD 已推进到本 checkpoint 提交之后，说明上一轮已入库成功，跳到第 1 步的"landing"分支。**
3. 实测 counts（`h.get_counts(h.load_state())`）与 §3.1 的**入库后**列对撞（355/130/852/132/223）。
4. 跑 `sentinel_paths(state)` 全量普查，与 `resume.commit_backfill_pending_R19_ckS1pause.sites_expected_after_mut` 做**逐字集合相等**断言。
5. 复跑 `.orch_tmp/orch_integ1.py`，要求 **30/30 GREEN**（若 scratch 被清理，按 §5.4 的六面重写）。
6. 确认 `dag_paused == True` ⇒ **必须等人类明确的「开工」指令**才可继续（禁自行恢复）。

**第 1 步 · 恢复 `R19-landS1`**
1. 复核 `.orch_tmp/orch_s1l1.py`（`1d42f63156cd`）与 `orch_s1l2.py`（`18dfa21e3645`）face 未变；若 scratch 丢失，按 §5.5 的内容说明与本件 §8 的裁定原文**重建**（裁定原文已在本件落盘 ⇒ 智力成果不依赖会话记忆）。
2. 写 `orch_s1l3.py`（§④ 15 条裁定，键集 `{id, round, at, lane, task, source, question, fact, ruling, basis, action_taken}`，全部 `round=19, lane=S1, task=M1-01`，id 从 **A277** 连续到 **A291**）。
3. 写 `orch_s1l4.py`（§⑤，镜像 `resume.round19_lane_S6_return` 的 **46 键**体例；`subtask_log` 第 **52** 条镜像 S6 样本的 **41 键**体例）。
4. 写 `orch_s1l5.py`（§⑥ + `main()`，镜像 `orch_s6l.full.py` 的 `main` 与末断言体例）。
5. `cat` 五片 → `orch_s1l.full.py` → `py_compile` → `--preflight-only`（要求 41 判据 GREEN）→ `--dry-mut`（deepcopy 上跑，磁盘台账不动）→ 真提交。
6. `run_commit` 参数：`tag=R19-landS1`、`add_paths=[DEL, EV_INDEX, EV_RECEIPT, EV_LOG]`、`mutate_ledger=mut`、`untracked_owner_map={"S1":[DEL],"ORCHESTRATOR":[EV_INDEX,EV_RECEIPT]}`、`expect_counts=EXPECT_AFTER`、**`allow_dangling=` 实测的 11 条 `evidence/M1/**` 前向引用**（见 §12.2）。
7. counts 预期 **354/130/852(132+222) → 357/130/852(132+225)**（S1 landing 批含 3 件新 md；本 checkpoint 批已先 +1 ⇒ 实际起点是 **355**， landing 后为 **358**。**续跑方必须重新实测起点，禁沿用本行的 354/357**）。

> ⚠️ **口径订正（重要）**：本 checkpoint 批已使 counts 变为 **355/130/852(132py+223md)**。因此 `orch_s1l1.py` 里的 `EXPECT_BEFORE`（354/222）与 `EXPECT_AFTER`（357/225）**在续跑时必须改为 355/223 → 358/226**，`preflight` 的 P15/P16/P17/P18/P19 与 `mut` §① 的常量同批改。这是本 checkpoint 批引入的**唯一**口径漂移，已在 §11 登记为待办。**改法**：只改 `EXPECT_BEFORE` / `EXPECT_AFTER` / `EXPECT_AFTER_TOTAL` 三个常量与 P16 的 `132/222` 字面量，其余判据全部程序化派生、无需动。

**第 2 步 · landing 之后（不停，长程无人值守）**
1. 独立 post-verify 新提交（HEAD 已推进、5 处旧哨兵零残留、counts 对账、护栏守卫通过），镜像 `465282f` 之后的 `orch_vpost6b.py` 体例（**52 判据**）。
2. **按 PRE-43 关 Peirce**：先落盘 `.orch_tmp/orch_S1_close_agentret.txt`，再写 `in_flight_agents[11].close_agent_returned`（纯台账批或与下一 predispatch 批同批）。
3. **predispatch + spawn**：**M2-01/S7**（`qwen3.8-flash`，判 AC-002/003/004，闭合 4 条 `evidence/M2/**` dangling 白名单）与 **M1-01/S2**（`qwen3.8-max` high，**必须携带 §8 的 A277–A291 全部裁定原文**）。**PRE-5 三判据实测写权面不相交**才并行；否则先 S2 后 S7（并见 §9 的 429 缓解措施）。
4. **§14 追记**：`M1-01-design.md` 的裁定原文追记随 **S2 predispatch 批**同批落地（A214 窄豁免：**只在文末追加**，`numstat` 的 `deleted` 列必须为 **0**，追加前后做前 N 行拼接 `sha256[:12]` 的**双向核验**）。
5. 治理簇：FU-50 / 52 / 53 / 58 / 61 / 62 / 63 / 64 / 66（+ 待开的 FU-67 / FU-68）。
6. 循环直至 **29 任务 / 11 波 / 47 AC** 全部交付并留证 —— **未全部完成不得停**（用户死命令）。
---

## §8 待写入台账的 15 条裁定原文（A277–A291）— **本批最贵的智力成果，已落盘防丢**

> 依据手册 §6.4：**禁**让 lane 自行裁定；lane 的 §12 U 项一律由编排器终裁。以下 15 条对应 `M1-01-design.md` §12 的 **U-1…U-15**，全部 `round=19, lane=S1, task=M1-01`，键集 `{id, round, at, lane, task, source, question, fact, ruling, basis, action_taken}`。**续跑方写 `orch_s1l3.py` 时逐条照此落台账**（`question` / `fact` 需回源 design §12 与实测补齐原文，`ruling` / `basis` / `action_taken` 以下列为准）。

| 号 | ←U | 争点 | **裁定（rule）** | 依据 | 落地动作 |
|---|---|---|---|---|---|
| **A277** | U-1 | 写权缺口 G1–G7（另 G8 `tests/golden/__init__.py`、G9 `tests/api/imports/**`）超出卡片 `scope_allow` 字面量 | **rule A：全部扩围授权给 S2（`qwen3.8-max`）**，并同步 `tasks.M1-01.scope`。**否决 plan B**（把缺口分派给 S3–S8）——B 会破坏 A81 分层与棒的写权单一性，且 G7/G8 在 flash 棒上不可解 | A262（同型缺口先例）· A276（包标记形态）· A81 分层 · PRE-34 | 改 `tasks.M1-01.scope`；派单文 §1 写权面逐条点名 G1–G9 |
| **A278** | U-2 | 卡片 `M1-01.md:18` 的 gate `pytest -k validate_import` 实测 **NO_TEETH**（rc=0 但 **0 collected**） | **rule A**：由 **M0-04 / 编排器**预置具名用例到 `tests/integration/jobs/**`（开新单 **FU-67**）；**补牙之前 S8 一律标 `NO_TEETH`，禁标 PASS** | PRE-33（判据必须有牙）· PRE-34（rc=0/0 collected ≠ 通过）· C10（禁粉饰） | 开 FU-67；S8 的 AC 判定表加 `NO_TEETH` 态 |
| **A279** | U-3 | multipart DTO 命名与 `file` 字段对撞 | **rule A**：采 `UploadFields` / `AttachFileFields`（**不含** `file` 成员）＋ **两条对撞断言**：① 文本字段逐字相等；② `properties.file.format == "binary"` 单独断言（分离关注点） | A115（禁硬编码计数、要实取对撞）· OpenAPI multipart 规范 | design §11.3 的 DTO 面按此定名；S2 落契约测试 |
| **A280** | U-4 | `SourceMapping.id` 由客户端给定 ⇒ 主键语义与冲突处理未定 | **rule A**：**客户端给的 id 即主键**；同 id + 同 digest ⇒ **幂等复用**；同 id + 异 digest ⇒ **409 `VERSION_MISMATCH`**。并**删除 §11.3 的 `SOURCE_MAPPING_ID_PREFIX`**（服务端前缀与"客户端 id 即主键"矛盾） | D-019（禁凭空加错误码）· 既有 409 语义 · 幂等性口径 | 经 §14 追记删除该常量；S2 落幂等/冲突用例 |
| **A281** | U-5 | `tests/unit/test_domain_errors.py:176/:177` 用 `len(__all__) == 80` 钉死魔数 | **rule B**：改为**实取对撞（live-set collision）**，去掉魔数。**无需开 CR** —— A115 本就禁止硬编码计数 | A115 · 既有守护体例 | 由**编排器同批**改这两行（lane 无 `tests/unit/` 写权，A245/A248 先例） |
| **A282** | U-6 | 领域层是否需要时钟 | **rule A：保持零时钟依赖**（领域层纯函数；`created_at` 一律在**应用层**注入） | A81 分层 · 红线 3（禁墙钟/sleep）· 可测性 | design §11 明示；S2 落层界守护 |
| **A283** | U-7 | `IngestLimits.max_slices = 10_000` / `max_stage_items = 90_000` 的取值来源 | **rule A**：认定为**设计取值**（spec 派生），**走 §14 追记**说明来源，**不另立 ADR** | ADR 门槛（非跨模块架构抉择）· §14 追记体例 | §14 追记一条 |
| **A284** | U-8 | 金额字段能否为负 | **rule A**：**7 个 variable 键可为负** ＋ **5 个 sale 键非负**（保持 N16 ERROR）。**退货冲销**的业务确认开新单 **FU-68**（不阻塞本棒） | 业务口径未定 ⇒ 禁自行裁定业务 · C10 | 开 FU-68；design §11 标注两类的符号约束 |
| **A285** | U-9 | AC-006 的「CSV/JSON 同值」是否包含 `validation_digest` 同值 | **rule A**：同值 ＝ **归一化业务值 ＋ `metadata_digest`**；**排除 `validation_digest`** —— 其 `files` 段含**原字节 SHA**，跨通道必然不同，要求同值即逻辑不可能 | AC-006 原文 · digest 口径定义 | S8 判 AC-006 时按此口径；design §10 标注 |
| **A286** | U-10 | 「未知切片」与「孤立切片」是否两个错误码 | **rule A：同指一事** ⇒ 只登记 **`ORPHAN_SLICE`** 一个码。（N11 的 `UNKNOWN_DICTIONARY_REF` 覆盖的是**字典解析**，不是切片归属） | D-019（禁凭空加码）· 既有 PROBLEM_CODES 冻结面 | design §11 统一用 `ORPHAN_SLICE` |
| **A287** | U-11 | 暂存目录落点与 `job_id` 传参 | **rule A**：传 `job_id = <import_id>`，**接受暂存落 `tmp/jobs/**`** —— 换来 `sweep_unreferenced` 的既有保护，避免重复实现 ~200 行清理逻辑 | 复用优先 · `infra/files.py` 既有能力 | design §11.3 固化；S2 落清理守护 |
| **A288** | U-12 | `SourceRow.source_file_id` 指向哪张表 | **rule A**：指向 **`import_files.id`**。（若指向内容寻址的 `artifacts.id`，在**复用**场景下会产生歧义） | 数据模型无歧义原则 | design §11.3 / DDL 面对齐 |
| **A289** | U-13 | `VALIDATE_IMPORT` handler 的实现落点与注册落点；作业是否独立进程 | **rule A**：实现落 **`application/import_jobs.py`**，注册落 **`api/app.py` 装配面**（G7 的**最小例外**）。**并裁定该作业「同进程内跑」**（独立 worker 进程**不在本卡 scope**）⇒ 连带确定 I5/I6/I7 集成用例落点与 U-2 的补牙位置 | A81 分层 · A217 ③（装配面归属）· scope 边界 | design §11.3/§11.7 固化；FU-67 的落点随之确定 |
| **A290** | U-14 | HTTP 层测试放哪 | **rule A：扩围新建 `tests/api/imports/**`**（新目录 ＋ `__init__.py` ＋ `conftest.py`；同族先例 `tests/api/activities/**`）。**否决**把 TestClient 塞进领域层测试 —— 会污染 `-k` 的分母 | A276（包标记形态）· S6 先例 · PRE-34 | `tasks.M1-01.scope` 同步（与 A277 同批） |
| **A291** | U-15 | 派单文里 fixtures 路径是简写 | **rule A**：认定为**简写**，一律使用实测全路径 **`spec/CampaignLab-SDD-v1.0/fixtures/**`**。**仅口径报备、不阻塞** | PRE-37 第 1 款（用实测路径） | 派单文口径注记 |

**裁定产生的连带义务**：新单 **FU-67**（U-2 补牙，落 `tests/integration/jobs/**`）· 新单 **FU-68**（U-8 退货冲销业务确认）· **FU-66 扩围**（追加 S1 的档位预算复核：55k 档 vs lane 自估 ≈105k）· `tasks.M1-01.scope` 同步（A277 + A290）· `M1-01-design.md` §14 追记（A280 删常量、A283 取值来源、A285 口径）。

**M1-01 状态裁定**：`RESULT = DONE_WITH_GAP`（交付面 100%；GAP ＝ §12 的 15 个 U 项待裁，本批已全部裁毕）；loop 实耗 **1 / 2**（未超帽）；**token 超支**（lane 自估 ≈105k vs 55k 档）⇒ 依 **A183** 记 `tokens=null` + `tokens_estimated=true`，**不入**护栏分母。`tasks.M1-01.status` **保持 `IN_PROGRESS`**（S2–S8 未做；**AC-005/AC-006 的判定归 S8**）⇒ **禁判 DONE**。

---

## §9 成本护栏与档位纪律（如实报，禁降档凑数 C10）

| 护栏 | 目标 | 停机时实测 | 判定 | S1 入账后的**已预告**结果 |
|---|---|---|---|---|
| ① `flash_share_tasks` | ≥ 0.60 | **0.6000**（36/60） | ⚠️ 达标但**余量 0.0** | S1 是 max 档 ⇒ **36/61 = 0.5902 → FAIL**（必然，已在 `next_actions` ⑧ 预告） |
| ② `flash_share_tokens` | ≤ 0.35 | **0.6655**（792000/1190000） | ❌ **FAIL 且统计上不可判**（仅 **10/50** 条有真实计量句柄，其余依 A183 记 `null`） | 不变（S1 `tokens=null` ⇒ `token_entries_null` 40→41） |
| ③ `flash_share_dev_lanes` | 参考口径 | **0.4474**（17/38） | 参考 | **17/39 = 0.4359** |

- **回升路径（算术预测，非承诺）**：M1-01 的 **S3–S8 六棒全 flash** ＋ M2-01/S7 flash ＋ 治理簇 flash ⇒ units 可回升过 0.60。
- **铁律**：**禁**为凑配比把该用 max 的棒降档，也**禁**为压 token 占比改写口径（手册 §6.6 / C10 / A234）。跌破就如实报 FAIL ＋ 留归因。
- **档位分配（手册 §6.3 硬规则）**：OpenAPI / DDL / 状态机 / 公共冻结件变更 / 跨模块判断 ⇒ **强制 `qwen3.8-max`**；参数化枚举、样板铺开、证据采集、按已冻结签名机械展开 ⇒ **强制 `qwen3.8-flash`**。`spawn_agent` **必须显式**给 `model` + `reasoning_effort`，禁静默继承父模型（§15.1 / A234）。
- **429 缓解（本次停机新增）**：① 探针一次写盘、按 `sed` 行区间定点读，禁整份拉大日志；② 大驱动**分片写 + `cat` 合并**，单片 < 20KB；③ 下一波派单**串行优先**（S2 与 S7 只有在 PRE-5 三判据实测写权面不相交时才并行，否则先 S2 后 S7），避免并发把 TPM 打穿；④ 每批边界**必提交 + push**。

---

## §10 环境铁律与工具陷阱（**实测复发过，续跑方必读**）

| # | 铁律 | 出处 |
|---|---|---|
| 1 | **Python 一律 `uv run --no-sync`，禁系统 `python3`**。每次 WSL 调用前置：`export PATH=/home/szf/.local/bin:/home/szf/.cargo/bin:/usr/bin:/bin; cd /home/szf/dev/CampaignLab` | 环境 |
| 2 | **经传输层投递的 `bash -c` 载荷里禁半角双引号** —— 会被嚼碎（实测 `grep -n "^### "` 退化成重定向、`sed -n "1,5p"` 断成两个参数）。替代：`grep -n -e A -e B`；`sed -n -e 1,5p`；`#` 开头要用 `\#\#\#` 转义；建文件一律走**脚本文件范式** | **PRE-42①** |
| 3 | **脚本文件范式**：PowerShell 单引号 here-string `@'...'@` → `-replace "`r",""` → `[IO.File]::WriteAllText(path, s, (New-Object Text.UTF8Encoding $false))` → `wsl bash -c '... uv run --no-sync python <script>'`。单次 exec_command 载荷 < ~30KB，**大驱动分片再 `cat`** | PRE-42① |
| 4 | **禁用 PowerShell `Get-Content -Raw` 拼接 UTF-8 文件**（ANSI  mojibake）。要字节级拼接一律用 WSL `cat a b > full` | 实测 |
| 5 | **`pathlib.write_text(..., newline=...)` 禁用** ⇒ 用 `write_bytes` | 实测 |
| 6 | **scratch 件一律 `orch_` 前缀**，落 `.orch_tmp/`（↔ `/mnt/d/ws/codex_rd/ss_campaignlab/.orch_tmp/`）；lane 自己的 scratch 是 `s1m1_` 前缀 | **PRE-39** |
| 7 | **`run_commit` 的 drift 门读的是顶层 counts** ⇒ 计数必须**双镜像**写全（顶层 6 键 ＋ `ruff_formatted_files_composition` 3 键镜像），且**同一赋值点派生** | **R19-5** |
| 8 | **后台 WSL 进程随启动器退出而死** ⇒ 用 `setsid nohup ... > log 2>&1 < /dev/null &` | 实测 |
| 9 | **易失态工具返回（`spawn_agent` / `close_agent` / `wait_agent` / `send_input`）必须收到后下一步立即原样落盘**，再据以写台账；台账引用该 scratch 件的路径 ＋ 行数/字节/`sha256[:12]`。**禁**依赖会话记忆跨批传递（模型切换 / 主机重启 / 429 中断即不可复得）；一旦丢失**只能置 null 并附 caliber**，禁补写猜测值 | **PRE-43** / A183 / R19-18 |
| 10 | **counts 口径**：`RUFF_SUFFIXES = (".py", ".md")`；门一律在**冻结索引树**上实测；R11-3 恒等式 ＝ 工作树 ruff 报数 == 台账值 + 未跟踪 in-scope；`ruff_formatted_files == in_scope_py + in_scope_md == total`（A101） | R11-3 / A101 |
| 11 | **期望值禁手填**：一律由**同口径测量函数程序化派生**；每条判据都要有**阳性对照**证明有牙 | **PRE-37 第 1 款** / PRE-33 |
| 12 | **台账 append-only（D-011）**：更正一律走追加附录，禁改写既有原文；一任务一提交 | D-011 |
| 13 | 需要 sudo 时（**预期永远不需要**）：密码 `mahound`，**只经 stdin 传入**，禁写进命令行/文件 | 用户授权 |

---

## §11 数据损失核验结论 ＋ 本 checkpoint 批引入的唯一口径漂移

### 11.1 结论：**无数据损失**

- `INTEGRITY RESULT: GREEN`（`.orch_tmp/orch_integ1.py`，**30/30** 判据）：git 完整性 7/7 · 交付件 face 对撞 4/4 · PRE-43 落盘 3/3 · 驱动碎片 10/10 · 台账一致性 7/7 · 仓内工具 4/4。
- 429 中断的**性质**：模型服务端限流（TPM/RPM 配额或高峰容量），客户端重试耗尽后中断当轮。**不是** git 冲突、不是门判红、不是台账写坏。`run_commit` 是**原子闭环**（任一门失败即 `git reset` + 台账 `checkout` 回滚），中断时它**尚未被调用** ⇒ 结构上不可能留半成品。
- **对照历史事故 R19-18**：那次是 `close_agent` 返回未落盘 + 模型切换 ⇒ 正文永久不可复得（已如实置 null）。**本次 PRE-43 生效**：`wait_agent` 回执在收到当刻即落盘，且 `close_agent` 尚未调用 ⇒ **零悬空易失态**。

### 11.2 本批引入的唯一口径漂移（**续跑必办**）

本 checkpoint 批新增 1 件 `.md` ⇒ counts 由 **354/130/852(132py+222md)** 变为 **355/130/852(132py+223md)**，权威基线推进到本提交、`history` 26→**27**。因此 `orch_s1l1.py` 中的以下常量在续跑时**必须同批改**：

| 常量 | 现值（写作时点） | 续跑应改为 |
|---|---|---|
| `EXPECT_BEFORE` | `354 / 130 / 852 / 132 / 222` | **`355 / 130 / 852 / 132 / 223`** |
| `EXPECT_AFTER` | `357 / 130 / 852 / 132 / 225` | **`358 / 130 / 852 / 132 / 226`** |
| `EXPECT_AFTER_TOTAL` | `357` | **`358`** |
| `HEAD_BEFORE` / `BACKFILL_SHA` | `465282f` | **本 checkpoint 提交的 sha**（实测 `git rev-parse HEAD`；哨兵链的 obligor 也换成 `commit_backfill_pending_R19_ckS1pause`） |
| `PREV_PEND_KEY` | `commit_backfill_pending_R19_S6landBF` | **`commit_backfill_pending_R19_ckS1pause`**（且待兑现哨兵数由 5 变为本批实测登记数） |
| preflight `P16` 的 `132/222` 字面量 | `132, 222` | **`132, 223`** |
| `CN_BEFORE.subtask_log_index` / `baseline_history_index` | `51` / `26` | **`51` / `27`** |

> 其余判据（P04–P14、P17–P38）**全部程序化派生**，无需改动。`mut` §② 的 `assert len(sites_before) == 5` 必须改为本批实测登记数（**禁写死**，改为 `== len(pend["sites_expected_after_mut"])` 更安全）。

---

## §12 冻结面、锁与前向引用白名单

### 12.1 PRE-40 冻结面（**8 件，sha256[:12] 逐字不得变**；续跑派单前必须重测）

| 文件 | sha256[:12] |
|---|---|
| `src/campaignlab/api/common.py` | `b2908617d193` |
| `src/campaignlab/api/activities.py` | `3865f3eb6b3c` |
| `src/campaignlab/api/rules.py` | `eac1377a4b72` |
| `src/campaignlab/api/jobs.py` | `e9b575602e56` |
| `tests/api/activities/__init__.py` | `8ccc54fe0ab9` |
| `orchestrator/handoff/M2-01-design.md` | `2d39feaac2d1` |
| `orchestrator/handoff/M1-01.slice.json` | `eadbd88e4ef7` |
| `orchestrator/handoff/M2-01.slice.json` | `8f44b036f065` |

### 12.2 前向引用白名单（`allow_dangling`，S1 landing 批必须携带）

`h.dangling_refs(ADD)` 实测 **11 条**，全部指向 `evidence/M1/**`（由 **M1-01/S8** 创建）：`evidence/M1/` · `evidence/M1/M1-01/` · `evidence/M1/M1-01/ac.md` · `.../commands.md` · `.../counts.md` · `.../gates/` · `.../gates/V1.log` · `.../http/` · `evidence/M1/summaries/M1-01.md`（引用方分别为 `M1-01-design.md` 与 2 件取证件）。**续跑方必须重新实测**（PRE-37），并按 `forward_reference_registry` 体例登记 `referenced_in` / `registered_at` / `registered_by` / `rule` / `lands_in` / `allow_dangling_scope`（先例：`evidence/M2/M2-01/` 条目、A173 条目）。

### 12.3 锁（改动须走专门解冻批 / CR）

| 锁面 | 约束 |
|---|---|
| `src/campaignlab/api/common.py` | **冻结**（改动须走 FU-59 型专门解冻批；`len(__all__)` 实测 **80**） |
| `orchestrator/handoff/M2-01-design.md` / `M1-01-design.md` | 设计冻结件，**禁改写**（D-011）；更正只能走 §14 **文末追记**（A214 窄豁免，`numstat deleted` 必须为 0 ＋ 前后 N 行拼接 sha **双向核验**） |
| `orchestrator/state.json` | **append-only**，只经 `run_commit` 的 `mutate_ledger` 写 |
| `tests/**` | lane 的**硬禁面**（守护迁移归编排器同批做，A245/A248 先例） |
| 已入库文件 | 禁改写；更正一律走 append-only 附录（先例 D-052 §9） |
| `pyproject.toml` / `ruff.toml` / `mypy.ini` | 全 lane 硬禁面 |

---

## §13 关键文件索引（续跑方按此定位）

| 用途 | 路径 | face（写入时点） |
|---|---|---|
| **长程编排契约（v1.7）** | `docs/delivery/LONG-HORIZON-ORCHESTRATION.md` | 785L / 69552B / `f64ebc4e9eb0` |
| 台账（唯一权威机器面） | `orchestrator/state.json` | — |
| 闭环提交工具 | `scripts/orch_harness.py` | 676L / 26510B / `0d8ac533afec` |
| S1 派单文 | `orchestrator/handoff/R19-lane-M1-01-S1.md` | 409L / 40168B / `7c692d223a49` |
| S6 派单文 | `orchestrator/handoff/R19-lane-M2-01-S6.md` | 463L / 35841B / `93a62069914e` |
| M1-01 契约切片 | `orchestrator/handoff/M1-01.slice.json` | 2875L / 60641B / `eadbd88e4ef7` |
| M2-01 契约切片 | `orchestrator/handoff/M2-01.slice.json` | — / `8f44b036f065` |
| lane 通用规约 | `orchestrator/handoff/LANE-COMMON.md` | — |
| 任务卡 | `orchestrator/tasks/M1-01.md`（`:14–:18` 六个 `-k` 字面量；`:36` 档位表 S1=55k/max/high）· `orchestrator/tasks/M2-01.md`（`:46` S6 档位原文） | — |
| 上一次 checkpoint | `orchestrator/handoff/R19-CHECKPOINT.md` | 304L / 35043B / `b80e41f17d0e` |
| **可复用驱动模板** | `.orch_tmp/orch_s6l.full.py`（**1349L / 91426B**，landing 批全范式，`main()` 在 :1319）· `.orch_tmp/orch_bf6.full.py`（66608B，纯台账回填批范式）· `.orch_tmp/orch_v1s.py`（S1 独立复验 37 判据）· `.orch_tmp/orch_s1ev.py`（取证件生成器）· `.orch_tmp/r19ck_full.py`（`sentinel_paths` / `PEND2`） | — |
| 本批自检 | `.orch_tmp/orch_integ1.py`（30 判据）· `.orch_tmp/orch_prog1.py`（进度快照）· `.orch_tmp/orch_s1insp{,2,3}.py`（台账键集探针） | — |

> ⚠️ `.orch_tmp/` 在 **Windows 侧**（`D:\ws\codex_rd\ss_campaignlab\.orch_tmp\`），**不入 git**。若被清理，§5/§8/§12 已把**不可重得的智力成果**（15 条裁定原文、face 基线、驱动分片内容说明）全部落进本件与台账 ⇒ 可据此重建，**无需依赖会话记忆**。

---

## §14 停机签署

| 项 | 值 |
|---|---|
| checkpoint 键 | `resume.checkpoint_R19_S1pause` |
| `kind` | `HUMAN_AUTHORIZED_STOP_CHECKPOINT` |
| 本批 tag | `R19-ckS1pause` |
| `dag_paused` | **True**（`dag_paused_at_R19_S1pause` / `dag_pause_reason_R19_S1pause` / `dag_pause_resume_precondition_R19_S1pause` 同批写；既有 `dag_pause_reason_R19` 等按 D-011 **留档不改写**） |
| 恢复前置 | ① 人类明确的「开工」指令；② 第 0 步接管自检全绿（含 `orch_integ1.py` 30/30）；③ §11.2 的口径漂移已按实测订正 |
| 恢复后第一动作 | 写 `.orch_tmp/orch_s1l3.py`（§④ 15 条裁定），按 §7 第 1 步推进 |
| 数据损失 | **无**（§11.1，30/30 GREEN） |

**—— 检查点结束。未竟义务已全部定址有主，续跑方无需任何会话上下文即可接管。**
