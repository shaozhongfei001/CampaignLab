# CHECKPOINT · 2026-11-13 R8（关机暂停点）

> **状态：DAG 已暂停（`dag_paused = true`）。** 本 checkpoint 由编排器在用户「准备关机，保存完整 checkpoint，检查无误即可暂停」指令下建立。
> **未经用户明确「开工」指令，禁止派发任何 lane、禁止改动 `src/**`、`web/**`、`tests/**`、`orchestrator/tasks/**`。**

- **时点**：2026-11-13T13:29:43+08:00（Asia/Shanghai）
- **仓库**：WSL2 Ubuntu ext4 `/home/szf/dev/CampaignLab`
- **分支**：`m0-framework`　**HEAD**：`248f852`　**远端**：`git@github.com:shaozhongfei001/CampaignLab.git`
- **同步**：ahead/behind = **0 / 0**（全部已推送）
- **phase / wave**：M0 / wave1（wave2 已部分启动）
- **配套交接件**：`orchestrator/handoff/round8-lane-returns-digest.md`（四 lane 回报精华 + 全部 U 项原文摘要）
- **机器可读恢复态**：`orchestrator/state.json` → `resume.checkpoint_R8`、`resume.self_check_gates_rc0`、`resume.round8_pending_rulings`、`resume.round8_pending_rulings_F`

---

## 1. 全表门禁真值（15 项，编排器独占复跑，证据 `/tmp/fulltable.json`）

| 门 | 命令 | rc | 期望 | 结论 | 摘要 |
|---|---|---|---|---|---|
| G1 | `( cd spec/CampaignLab-SDD-v1.0 && sha256sum -c SHA256SUMS --quiet )` | 0 | 0 | OK | 基线 v1.0 完整 |
| G2 | `( cd spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta && sha256sum -c DELTA-SHA256SUMS --quiet )` | 0 | 0 | OK | 补丁 v1.0.1 完整 |
| G3 | `python3 scripts/check_frontend_baseline.py` | 0 | 0 | OK | PASS 8/8；baseline_files=45 manifest_rows=8 |
| G4 | `python3 scripts/contract_slice.py --ops noSuchOp --out /tmp/neg_op.json` | 2 | 2 | OK | 负例如实 FAIL（missing=`operations:noSuchOp`） |
| G4b | `python3 scripts/contract_slice.py --ac AC-MR-99 --out /tmp/neg_ac.json` | 2 | 2 | OK | 负例如实 FAIL（missing=`acceptance_rows:AC-MR-99`） |
| G5 | `python3 scripts/check_contracts.py check` | 0 | 0 | OK | 登记项=13 实测差异=13 元校验=skipped |
| G6 | `uv run --no-sync python scripts/check_contracts.py check --validate` | 0 | 0 | OK | 登记项=13 元校验=6 |
| G7 | `uv run --no-sync ruff check .` | 0 | 0 | OK | All checks passed! |
| G8 | `uv run --no-sync ruff format --check .` | 0 | 0 | OK | 176 files already formatted |
| **G9** | `uv run --no-sync mypy` | **2** | **0** | **MISMATCH** | **D-035**：Duplicate module named `conftest`；`errors prevented further checking` |
| G10 | `uv run --no-sync pytest -q` | 0 | 0 | OK | **350 passed**, 6 warnings, 146.63s |
| G11 | `bash scripts/verify.sh` | 0 | 0 | OK | 4/4 字节级复现 |
| G12 | `python3 spec/CampaignLab-SDD-v1.0/qa/verify_package.py` | 0 | 0 | OK | PACKAGE PASS 6/6 |
| G14 | `bash scripts/doctor.sh` | 0 | 0 | OK | PASS=15 WARN=1 FAIL=0 → **HEALTHY** |
| G14b | `uv run --no-sync python -m campaignlab doctor` | 0 | (无期望) | 记录 | PASS=3 WARN=2 FAIL=0 → **DEGRADED**（预期态，非红灯） |

**本点刻意未跑的 2 项及原因**：

- **G13 `npm --prefix web ci && npm --prefix web run build`**：Round 8 四 lane 写集**均未触及 `web/`**（Volta=`src/campaignlab/worker/**`+`infra/db/repositories.py`+`application/worker.py`+`tests/unit/**`；Bohr=`tests/api/**`；Ramanujan=`orchestrator/tasks/**`；Lagrange=`orchestrator/handoff/**` 两份 md）。上次实测 rc=0 / `✓ built in 148ms`（2026-11-13T02:41:56+08:00）仍有效；且 `npm ci` 耗时长、关机前不宜占用窗口。**保留历史值 + 加注，未改写**。
- **G4c 前端基线篡改负例**：该门需要「备份 → `printf` 追加换行到 `spec/frontend-template-spdb-v1.1/css/tokens.css` → 实测 rc → 还原 → 断言 `spec/` dirty=0」，是唯一会**临时写入只读 `spec/**`** 的门。关机前不做可避免的只读区写入风险。上次真实执行结果 rc=1 / 期望 1 / `spec_dirty_after_restore=0`（2026-11-13T02:41:57+08:00）仍有效。

**恒等式核验**：`tracked in-scope py+md = 176`，`untracked in-scope = 0` → 与 G8 报的 `176 files already formatted` **相等**（A101 恒等式成立）。
**只读区核验**：`git status --porcelain spec/ contracts/` = 空。

---

## 2. ⚠️ 唯一红灯：D-035（G9 mypy，MAJOR / BLOCKING）

- **事实**：`uv run --no-sync mypy` rc=2，`tests/integration/bootstrap/conftest.py: error: Duplicate module named "conftest" (also at "tests/api/conftest.py")` + `Found 1 error in 1 file (errors prevented further checking)`。
- **引入点**：`57b6db5`（Round 8 / Bohr / M0-02-S4）新增 `tests/api/conftest.py`；`tests/**` 各级无 `__init__.py`。
- **影响**：`src` + `tests` + `scripts` **三棵树全部未被类型检查**，`strict = true` 的机器保障自 `57b6db5` 起实际失效；`counts.mypy_source_files` **本次不可测**（按禁估算纪律保留上次可测值 + 加注）。
- **编排器责任**：`57b6db5` 复验只跑路径限定 mypy（3 source files rc=0），漏检跨目录重复模块名 → **自我更正 R8-4**。
- **修法**：详见 `orchestrator/defects/D-035.md` §5（推荐选项 B：`[tool.mypy]` 增 `explicit_package_bases = true`，1-2 行配置、不动测试文件、覆盖面不减）。
- **纪律**：G9 红灯期间，**wave1 出口 Q 复核与任何 AC 取证均不得放行**；**下次开工第一件事即修 D-035**（先于任何新派单）。

---

## 3. 进度真值（多口径，禁单一数字伪装精度）

### 3.1 任务级（29 张卡）
| 状态 | 数量 | 任务 |
|---|---|---|
| DONE | 1 | M0-P01 |
| PASS_WITH_TODO | 1 | M0-01 |
| IN_PROGRESS | 3 | M0-02（7/8）、M0-03（10/10，status 未判 DONE）、M0-04（2/8） |
| TODO（已部分开工） | 1 | M0-03b（1/4，S1 DONE） |
| TODO（未开工） | 23 | M1-01..M1-04、M2-01..M2-04、M3-01..M3-04、M4-01..M4-03、M5-01..M5-03、M1-P01、M3-P01、M3-P02、M4-P01、M5-P01 |

> **自我更正 R8-6**：此前会话摘要称「M0-02 6/8」，实测 `tasks[M0-02].subtask_progress` 为 **7/8 DONE**（S1、S2、S3a、S3b、S3c、S3d、S4；仅 S5 TODO）。以台账实测为准。
> **M0-03 虽 10/10 子任务全 DONE，但 `status` 仍为 `IN_PROGRESS`**：禁在无取证的情况下判 DONE，须待 wave1 出口 Q 复核 + AC 取证回填（A109）。

### 3.2 子任务级（仅已分解的 4 张卡）
- 已分解子任务 **31 个**（M0-02 8 + M0-03 10 + M0-03b 4 + M0-04 8 + **S2b 1**，S2b 依 A110 新增、本 checkpoint 补键）
- 其中 DONE **20 个** → **64.5%**
- ⚠️ 该口径**只覆盖 29 张卡中的 4 张**，其余 25 张尚未做子任务分解，**不可外推为全项目进度**。

### 3.3 波次级（11 波 / wave0..wave10）
- **wave0** 闭合（M0-01 PASS_WITH_TODO、M0-P01 DONE）
- **wave1** 接近闭合（M0-02 仅剩 S5 证据；M0-03 子任务全交付，待出口 Q 复核）→ 被 **D-035 阻塞**
- **wave2** 部分启动（M0-04 2/8 + S2b 待派；M0-03b 1/4，S4 被 F-U-2 阻塞）
- **wave3..wave10** 未启动（8 波 / 23 张卡）
- → 波次口径约 **1.5 / 11 ≈ 14%**

### 3.4 验收级（最关键缺口）
- **AC 取证 = 0 / 47**（baseline 35 + monthly 12）。`acceptance.primary_owner` 47 条已自洽并经守护校验，但**证据尚未采集**。
- → 验收口径 **0%**。**这是全项目最大的未偿债务**，且 M5-03 属 human tier（须用户本人确认，禁代完）。

### 3.5 工件级
- 提交总数：**72**（`git rev-list --count HEAD` 实测，为本 checkpoint 提交**之前**的值）
- `orchestrator/defects/`：33 → **35** 张（本 checkpoint 新增 D-034、D-035）
- `orchestrator/tasks/`：磁盘卡 26 + `KNOWN_MISSING` 3 == 29
- 全仓 in-scope py+md：176（本 checkpoint 提交后增长，以 `counts` 为唯一权威）

> **综合判断（诚实版）**：环境/契约/公共件奠基（M0）已大体成形，但**业务功能（M1-M4）与验收（M5）几乎未启动**。
> 按可交付价值口径，整体完成度约 **15%±5%**；按「已开工部分的子任务完成度」口径为 64.5%。两个数字口径不同，禁混用。

---

## 4. counts 权威指针（禁写死数字）

`resume.self_check_gates_rc0.counts` 是唯一权威（依 D-012/D-014/A101）。本 checkpoint 提交后的关键真值：

- `pytest_passed` = **350**（G10 全表实测）
- `mypy_source_files` = **本次不可测**（D-035 阻塞）→ 保留上次可测值并加注，**禁填新数、禁估算**
- `ruff_formatted_files` = 以 G8 报数为准（本提交新增 md 会推高该值；恒等式 `tracked(py+md) + untracked == ruff 报数` 必须成立）
- `contract_registered_nodes` = 13、`acceptance_denominator` = 47、`frontend_baseline_rows` = 8
- `live_openapi_sha16` = `592571099d638251`、`live_openapi_info_version` = `1.0.1`、`openapi.json` = 443309 B

---

## 5. 快照与数据保全

- 仓库内 13:02 在飞快照（四 lane 产物已全部入库，快照失去恢复价值）：
  - `orchestrator/checkpoints/R8-inflight-tracked-20261113-130246.patch`（34349 B）
    sha256 `ec17cc41becfe47fac58764cca1340bfdb91ee78da1dd5a117711ad257a8bc39`
  - `orchestrator/checkpoints/R8-inflight-untracked-20261113-130246.tar`（317440 B）
    sha256 `a324ef6df456b007a665a148aaaa9224fa00af645732712b5ee0e6be5ff07d9e`
- **⚠️ 摘要纠错**：此前会话摘要称宿主副本「已存于 `D:\ws\codex_rd\ss_campaignlab\.orch_checkpoints\20261113-130246\`」，**实测该目录不存在**（自我更正 R8-7）。
  故本 checkpoint 采取「**先建宿主副本 → sha256 逐文件比对全等 → 才删仓库内文件**」的顺序，任何一步不等即中止删除并保留仓库内文件。
- 处置实现：单一 python 进程端到端（`shutil.copy2` + `hashlib.sha256` 双向比对 + `os.remove`），显式绝对路径，先验后删。

---

## 6. 恢复步骤（下次开工，严格按序）

```bash
# ① 进仓 + 确认基线一致（应为 m0-framework / 本 checkpoint 提交 / 0 0）
cd /home/szf/dev/CampaignLab
git rev-parse --abbrev-ref HEAD
git log --oneline -3
git rev-list --left-right --count origin/m0-framework...HEAD
git status --porcelain            # 期望为空

# ② 只读校验：spec/contracts 未被触碰 + 活契约指纹
git status --porcelain spec/ contracts/                      # 期望空
sha256sum contracts/openapi.json | cut -c1-16                # 期望 592571099d638251

# ③ 读交接件（下次会话无上下文，必须全读）
cat docs/delivery/CHECKPOINT-2026-11-13-R8.md
cat orchestrator/handoff/round8-lane-returns-digest.md
cat orchestrator/defects/D-035.md
cat orchestrator/defects/D-034.md

# ④ 复跑门禁确认与 checkpoint 一致（先跑快门，G10 约 2.5 分钟）
uv run --no-sync ruff check . ; uv run --no-sync ruff format --check .
uv run --no-sync mypy          # 期望仍 rc=2（D-035 未修前）
uv run --no-sync pytest -q     # 期望 350 passed

# ⑤ 修 D-035（第一优先，先于任何新派单）→ 复跑 mypy 至 rc=0 → 回填 counts.mypy_source_files
# ⑥ 终裁 resume.round8_pending_rulings（U-1 BLOCKING）与 round8_pending_rulings_F（F-U-2 BLOCKING、F-U-7→D-034 已立）
# ⑦ 置 dag_paused = false，按 §7 路线派 Round 9
```

---

## 7. Round 9 续跑路线（用户下「开工」后执行）

1. **D-035 修复**（MAJOR/BLOCKING，最高优先）→ G9 转绿 + `counts.mypy_source_files` 重测回填。
2. **M2-04 重切**（U-1 BLOCKING）：`--ui` 补 UI-14/UI-15/UI-20、`--depth 6`（A108）、op 集合**按 method 第④步从页面 spec 正文实抽**（禁凭建议清单写死）；重切后校验 `truncated_schemas==[]`，解挂 S7/S8。
3. **M0-02 / S5**（证据采集，唯一剩余子任务）→ 使 wave1 的 M0-02 具备判 DONE 条件。
4. **M0-04 / S3**（`infra/artifacts.py`）→ 解锁 **S2b**（`worker/integrity.py` + `worker/deps.py`，档位 max，依 A110）。
5. **M0-04 / S4**（`api/jobs.py` + `JobPage`）：携 A111（`service.py` + `JobRepository.list_page`）、A112（`JobStore` 可选 idem 参数 + 信封组装）、A114（`WorkerSupervisor` append-only public lease 访问器，**禁双路径**）豁免，并落实 FU-20（`api/health.py` 补 `declared_responses(200)`）与 FU-21（D-033 幂等重放逐字节收口）。
6. **wave1 出口 Q 复核 + AC 取证回填**（A109）：M0-03 判 DONE 的唯一合法路径；同时补 Lagrange 两文档的 **`PENDING_CONTENT_REVIEW`**（13 件组件契约表逐条对代码）。
7. **wave3 六任务**（L1: M1-01→M1-02→M1-03 ∥ L2: M2-01→M2-02→M2-03），lane 内串行、两 lane 并行、写权限已确认不相交。
8. 循环至 **29 任务全交付、11 波全闭合、47 AC 全取证**。用户死命令：**「没有全部完成前不允许停，必须 DAG 开发流程全部结束」**。

---

## 8. 模型配比与 loop 纪律（下次派单必须遵守）

- **护栏**：`flash_share_tasks ≥ 0.60`、`flash_share_tokens ≤ 0.35`（手册 6.6）。
- **当前真值**：两项**均未达标**（`budget.guardrail_status.verdict` 已如实记录「不粉饰」）。本 checkpoint 已**程序化重算**（Round 8 的 7 条 `subtask_log` 此前未入分母），结果写入 `budget.flash_share_detail` / `flash_share_tasks` / `flash_share_tokens`，历史值以加注保留、禁改写。
- **重算口径**（禁手填）：`units = subtask_count or 1`；`flash = (tier_used == 'qwen3.8-flash')`；`dev lane = task.startswith('M')`；`tokens` 仅统计非 null（**无计量句柄一律记 null，禁估算**）。
- **回补计划**：wave3 起量产型子任务（参数化枚举、样板铺开、证据采集、卡片补齐）严格按手册 6.3 强制 flash 清单派 `qwen3.8-flash`；仅 OpenAPI/DDL/状态机/公共冻结件变更、设计先行件保持 `qwen3.8-max`。护栏检查点 = wave2 出口；若仍不达标，按手册 6.6 升级给项目负责人。
- **loop engineering**：每 lane 自迭代（`loop_used` 入账），Bohr 本轮 `loop_used=2` 为范例；上限按档位（flash 60k / max 200k tokens），无计量值则不判越限、只记客观量（工具调用数、文件数、行数、测试数）。
- **并发纪律**：开发 lane ≤ 3 + QA 1；多 lane 同树只跑**路径限定**门禁；非自有文件红点**只归因不修**；子智能体**禁一切 git 写操作**；全表复验**编排器独占**；派单必须显式填 `model`。
- **⚠️ 新增纪律（R8-4 教训）**：凡新增 `conftest.py` 或与既有文件**同 basename** 的新文件，复验**必须跑全树 `uv run --no-sync mypy`**，禁以路径限定 mypy 替代。

---

## 9. 人类专属事项（禁代完）

- **M5-03** 属 human tier：须**用户本人**确认，编排器与任何子智能体**禁代完、禁代签**。
- **CR-002** 已由用户裁定采**选项 B**（从契约移除 `listWorkspaces.status` 参数），执行须走契约变更流程（`contracts/**` 只读，须 CR + 重新登记 + 刷新 `live_openapi_sha16`）。
- `sudo` 密码只经 stdin 传入（用户已授权 `fonts-noto-cjk` 安装），**禁写入任何文件或日志**。

---

## 10. 暂停声明

本 checkpoint 提交并推送、快照保全核验通过后，编排器已：
1. 回填 `resume.self_check_gates_rc0`（15 项真值 + G13/G4c 未跑原因）；
2. 写入 `resume.checkpoint_R8` 与顶层 `dag_paused = true`；
3. 立 D-034 / D-035 两张缺陷单并同提交入账；
4. 补记 `round8_returns` 缺失的 Volta / Ramanujan 两条（标 `reconstructed_at_checkpoint`）；
5. 追加 `tasks[M0-04].subtask_progress.S2b = "TODO"`（A110）；
6. 程序化重算 `flash_share_*`；
7. 释放四个子智能体句柄（并发槽归零）。

**DAG 处于暂停态。等待用户明确「开工」指令。**
