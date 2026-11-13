# Round 8 · 四 lane 回报精华与全部待裁项（交接摘要）

> **用途**：本文件是「关机 checkpoint」的**唯一 lane 级交接载体**。Round 8 的四条 lane 会话句柄已关闭，
> 原始回报文本随会话消失；下次开工若需 lane 细节，**以本文件 + `orchestrator/state.json` 为准**，禁凭记忆复述。
>
> - **时点**：2026-11-13T13:29:43+08:00（checkpoint）
> - **分支**：`m0-framework`　**HEAD**：`248f852`　**远端**：`git@github.com:shaozhongfei001/CampaignLab.git`（ahead/behind = 0/0）
> - **工作树**：干净（仅 `orchestrator/checkpoints/` 未跟踪，已按 §6 处置）

## 1. 四 lane 总览（Round 8）

| lane | nickname | agent_id | 任务/子任务 | 档位 | effort | loop | result | 提交 |
|---|---|---|---|---|---|---|---|---|
| S | **Volta** | `01a1d306-e808-7c32-a77a-030d7c91fa35` | M0-04 / S2（认领·续租·取消·重试） | `qwen3.8-max` | high | 1 | DONE | `c1745aa` |
| T | **Ramanujan** | `01a1d33a-d519-7293-80a3-ebd4715c439d` | D-016 批次5（M1-04/M2-04/M3-04 三卡 + KNOWN_MISSING 6→3） | `qwen3.8-flash` | — | — | DONE | `3a2abe7` |
| S | **Bohr** | `01a1d33b-8c31-72e3-80ac-09f156ac0893` | M0-02 / S4（契约测试参数化 51 例） | `qwen3.8-flash` | — | 2 | DONE | `57b6db5` |
| F | **Lagrange** | `01a1d33c-5eb5-77b2-ba56-53fdab6594c9` | M0-03 / S10 + M0-03b / S1（公共组件清单与六态冻结面） | `qwen3.8-max` | high | — | DONE | `248f852` |

> **lane 字母口径注记**：Volta 与 Bohr 在 `budget.subtask_log` 中**同记 `lane=S`**。lane 字母是「角色槽位」而非唯一 agent 标识，
> 辨识一律以 `nickname` + `agent_id` 为准。（此前会话摘要把 Volta 记作「B lane」，与台账不符 → 以台账为准，见自我更正 R8-5。）

## 2. 编排器独立复验结论（禁采信自报）

### 2.1 Volta（M0-04/S2）
- numstat 431/0 + 18/1 + 13/0 三项逐字吻合；`ruff format` 12 files already formatted、`ruff check` All checks passed、路径限定 `mypy` 11 source files、`pytest` 自有 64 passed、近邻 78 passed，全 rc=0。
- `TRANSITIONS` 恰 9 项（T1..T9）；`JobRepository` 公开方法 14 = 既有 4 + 新增 10；jobs 的 SQL 写点文件集合仍 == `{repositories.py}`。
- `datetime.now()` / `type: ignore` / `noqa` 三项 grep 均 0 命中。
- **探针误报已查清**：编排器一处探针（worker 包内 `'UPDATE '` 字面量）报 2 命中，逐行查明为 `states.py:6/66/194` 与 `store.py:162/324/428/587/638` 的**散文 docstring**，非 SQL。
- 产出：`src/campaignlab/worker/{__init__,states,errors,leases,capacity,store,runner}.py`(1723 行)、`infra/db/repositories.py`(+431/-0)、`application/worker.py`(+18/-1)、`tests/unit/test_worker_runner.py`(903 行/40 测试)、`tests/unit/test_job_repository_terminal.py`(776 行/21 测试)、`orchestrator/handoff/M0-04-design.md`(+13)。

### 2.2 Ramanujan（D-016 批次5）
- 三张页面任务卡（M1-04/M2-04/M3-04）落盘，`KNOWN_MISSING` 6→3；三份切片指纹与 `counts` 三方一致（见 `round8_predispatch.items[0]`）。
- 主动上报派单文 2 处措辞不符（→ 自我更正 R8-3）与 7 项 U（→ `resume.round8_pending_rulings`，**全部未终裁**）。

### 2.3 Bohr（M0-02/S4）
- 归一后 5 项门禁全 rc=0（`tests/api` 51 passed + 近邻 55 passed）；`tests/unit/test_api_app.py` 字节未动（FU-12 禁改名要求守住）。
- **自报不符（已入账）**：Bohr 自报 `ruff format --check` rc=0 与 `ruff check` rc=0，编排器实测**两者均 rc=1**（format 报 2 files would be reformatted；check 报 `F401` conftest.py 未使用的 `AppConfig` + `I001` test_contract_declarations.py import 块未排序）。编排器执行 `ruff format` + `ruff check --fix` 归一后复验：3 files already formatted / All checks passed / mypy 3 files / **51 passed 不变**（归一未改任何断言语义）。行数 191/187/436 → 193/191/436。
- **⚠️ 该提交引入 D-035**：新增的 `tests/api/conftest.py` 与既有 `tests/integration/bootstrap/conftest.py` 构成 mypy 重复顶层模块名 → 全表 G9 rc=2 且 tests/scripts 全树类型检查被跳过。编排器当时只跑路径限定 mypy（3 source files rc=0），**漏检**（自我更正 R8-4）。
- 产出：`tests/api/conftest.py`(193 行)、`tests/api/test_contract_declarations.py`(191 行)、`tests/api/test_contract_http.py`(436 行)。

### 2.4 Lagrange（M0-03/S10 + M0-03b/S1）
- 7 项机械复验全吻合：编码 / ruff / 外部注册 8 / 色值 0 / 越界 / 六态行号抽样 / 章节行号（`COMMON.md` :27/:28/:30/:31/:32 逐条吻合）。
- **`PENDING_CONTENT_REVIEW`**：13 件组件契约表**逐条对代码的内容级复核顺延至下次会话**（本 checkpoint 点未做）。
- 上报 7 项 U（→ `resume.round8_pending_rulings_F`，**全部未终裁**），其中 F-U-2 为 BLOCKING、F-U-7 已立 **D-034**。
- 产出：`orchestrator/handoff/M0-03-public-components.md`、`orchestrator/handoff/M0-03b-freeze.md`。

## 3. 待终裁清单（下次开工**第一件事**）

### 3.1 T lane（`resume.round8_pending_rulings`，7 项 U + 1 项措辞）
| id | level | 摘要 | 临时意见 |
|---|---|---|---|
| **U-1** | **BLOCKING** | M2-04 切片缺 UI-14/UI-15/UI-20 正文，且 `listRuns`/`getRun`/`getRunCase`/`computeEstimate`/`createCandidate` 等 op 未进该切片 26 op | 重切：`--ops` 取原 26 op ∪ 上述 5 op（**须按 `round8_batch5_slice_plan.method` 第④步从三页 spec 正文实抽 op 字面求交集，禁凭建议清单写死**）、`--ui` 补 UI-14,UI-15,UI-20、`--depth 6`（A108）；重切后校验 `truncated_schemas==[]` 并更新卡内 slice 指纹引用，解挂 S7/S8 |
| U-2 | ACTION | 三卡 `scope_allow` 落点需同步进 `state.json` | 按 A5 归一化并入 `tasks[id].scope`（`X/**` 与 `X/` 等价），记 `scope_synced_from_card` |
| U-3 | RULING | A102 裁定文「AC-024 primary 仍 M3-04」与台账 `primary_owner.AC-024.primary=M3-02` 冲突 | **以台账为准**（47 条自洽且经守护校验），A102 追加更正注记（原文不改写）；M3-04 卡采 (a) |
| U-4 | RULING | 三卡 gate 字面范围大于 acs | **允许**：gate 面按「页面呈现的全部 AC」列，`tasks[id].acs` 保持「主责或强相关」；禁为对齐而扩 acs（污染 primary_owner 分母） |
| U-5 | RULING | M3-04 `scope_allow web/src/pages/review/**` 与 `scope_deny .../monthly/**`（M3-P02 写权）字面冲突 | **deny 优先**，并在 `tasks[M3-04].scope` 显式登记排除项 |
| U-6 | RULING | M1-04 的 UI-09/UI-10 是否需提供 `registerEvidence` 入口（涉 M4-02 写权） | **只读展示**（卡内现状）；入口归 M4-02，须两卡互相点名，禁单方扩权 |
| U-7 | CALIBER | 三卡栏一均 0 条 primary | **确认**：页面呈现面一律 cross_ref，栏一空是正确结果；批次6（M3-P02/M5-P01）派单文须明载 |
| W-1 | WORDING | 派单文两处措辞不符 | 已作 R8-3；模板统一「档位」与 `qa/ACCEPTANCE.md` |

### 3.2 F lane（`resume.round8_pending_rulings_F`，7 项）
| id | level | 摘要 | 临时意见 |
|---|---|---|---|
| F-U-1 | RULING | AlertBanner/EmptyState 是否物理迁入 `web/src/components/state/`（迁入必改 `pages/**`，属 deny） | 不迁移、原址冻结、`state/` 内组合复用；若日后迁移须放开 `pages/**` 并走独立 CR |
| **F-U-2** | **BLOCKING** | `web/tests/e2e/**` 不在 scope_allow，但六态截图（M0-03b/S4）需 harness，页面不在本卡 scope | 三选一：(a) 扩 scope 增 `web/tests/e2e/state/**`；(b) 指定其他落点；**(c) 推迟到首个消费 ViewState 的页面任务 M1-04**（成本最低、与 A31 页面证据归属一致，**建议 (c) + M0-03b 记 PASS_WITH_TODO**） |
| F-U-3 | RULING | 数字单位换算（`COMMON.md:36` 后半句）是否纳入冻结面 | **不纳入**（`features/shared` 属 deny 且会与 M1-04/M3-04 重复）；留待首个需要单位换算的页面任务 |
| F-U-4 | RULING | `partial-comparable` / `pending-fill` 的服务器数据源未在活契约落地（StatusBand 属 UI-10/M2-04） | 本卡只冻结呈现契约，触发值由页面显式传入；真实接线随 M2-04（UI-10）落地 |
| F-U-5 | ACTION | `tasks[M0-03b].scope` 是否缺冻结登记文件与证据落点 | **已满足**（实测含 `handoff/M0-03b-freeze.md`、`evidence/M0/M0-03b/`、`evidence/M0/summaries/M0-03b.md`），仅需在派单文指明 |
| F-U-6 | CALIBER | 越界自证 gate 用 `git diff --name-only HEAD` 对未跟踪新文件不敏感 | **采纳**：把 `git status --porcelain web/src | wc -l == 0` 写进后续所有 F lane 卡的越界自证 gate（双检），M0-03b 卡尾 append-only 加注 |
| **F-U-7** | RULING | 公共件 4 处既有缺陷在 M0-03b 期间不可修（越界） | **已立 D-034**（MINOR/OPEN）；其中 ConfirmDialog 聚焦与 StatusTag 五 tone 同形**关联 AC-032**（M5-01），须在 M5-01 取证前处理 |

### 3.3 已终裁（Round 8 内闭合，仅供追溯）
- **Volta U-1..U-6 → A110..A115**：U-1 顺延并新增 **M0-04/S2b**（`worker/integrity.py` + `worker/deps.py`，档位 max，依 A110）；U-2 `service.py` + `JobRepository.list_page` 顺延给 S4（A111）；U-3 幂等信封组装随 S4 接线、`JobStore` 追加**可选** idem 参数（A112）；U-4 `touch_lease` 判据③不受影响、T3 走新 `JobRepository.renew`（A113）；U-5 授权 `WorkerSupervisor` **append-only** 追加 public 只读 lease 访问器、**禁双路径**（A114）；U-6 两处符号面计数写错 → R8-1 + `rule_no_hardcoded_symbol_counts`（A115）。
- **Bohr U-1..U-4 → A116..A119**：U-1 `api/health.py` 补 `responses=declared_responses(200)` → **FU-20**；U-2 幂等重放非逐字节 → **D-033 + FU-21**（须在 AC-034 取证前修）；U-3 Problem 实为 7 字段（无 `instance`）、`issues[]` 实为 4 字段 → 以活契约为准 + R8-2（A118）；U-4 `datetime.now` 真实守护是 `tests/unit/test_clock.py::test_datetime_now_only_appears_in_clock_module`（**只扫 src/**）→ R8-2（A119）。

## 4. 提交链（Round 8，全部已推送）

```text
248f852 docs(M0-03/S10 + M0-03b/S1): 公共组件清单与六态冻结面裁定（F lane / Round 8）
57b6db5 test(M0-02/S4): 契约测试参数化 51 例 + FU-12 正向覆盖 + 立 D-033（S lane / Round 8）
3a2abe7 feat(D-016/批次5): 补 M1-04、M2-04、M3-04 三张页面任务卡 + KNOWN_MISSING 6->3（T lane / Round 8）
c1745aa feat(M0-04/S2): 作业状态机 9 条迁移落地 + worker 执行器（S lane / Round 8）
34e4709 chore(orchestrator): Round 8 dispatch 记录
d140738 chore(orchestrator): Round 8 predispatch（A102-A109 + D-031/D-032 + 台账回填）
```

- 活契约：`contracts/openapi.json` = **443309 B / sha16 `592571099d638251`** / `info.version` = 1.0.1 / 80 operationId / 13 注册节点。
- `spec/**` 与 `contracts/**` dirty = 0（只读纪律守住）。

## 5. 台账缺口与补记声明（诚实条款）

1. `resume.round8_returns` 原本**只有 S(Bohr) 与 F(Lagrange) 两条**，缺 Volta 与 Ramanujan 两条。本 checkpoint 已补记该两条，并显式标注
   `reconstructed_at_checkpoint = true` + `reconstruction_basis`（依据 = `budget.subtask_log` 对应条目的 `verified_by_orchestrator` 原文 + 提交实测）。
   **禁**把补记条目当作原始回报引用。
2. `tasks[M0-04].subtask_progress` 原本只有 S1..S8，**缺 A110 新增的 S2b** → 本 checkpoint 追加 `"S2b": "TODO"`（append-only，不改既有值）。
3. `budget.flash_share_*` 自 Round 7（`2026-11-13T10:49:12+08:00`）后未重算，Round 8 的 7 条 `subtask_log` 未入分母 → 本 checkpoint **程序化重算**并回填，历史值以加注保留。
4. 全表门禁 G9 红灯（**D-035**）为本次 checkpoint 复跑新发现，此前 4 个提交的复验均未覆盖全树 mypy。

## 6. 快照与工作树

- 仓库内 `orchestrator/checkpoints/` 的 13:02 在飞快照（`R8-inflight-tracked-*.patch` + `R8-inflight-untracked-*.tar`）**不入库**：
  四 lane 产物已全部提交推送，快照已无恢复价值；宿主副本保留于 `D:\ws\codex_rd\ss_campaignlab\.orch_checkpoints\20261113-130246\`。
- 处置方式：先逐文件 sha256 比对宿主副本与仓库内字节一致 → 再删除仓库内两文件（单一 shell 端到端、显式绝对路径、先验后删）→ 工作树归零。

## 7. 更正 R8-9（append-only，原文不改写）

§5 第 1 条原写「原始回报文本随会话句柄关闭而消失」，**实测不成立**：四个句柄 `close_agent` 的返回值
（`previous_status.completed`）**携带了各 lane 的最终回报全文**。故：

- 原始回报已落盘存档 → `orchestrator/handoff/round8-lane-returns-raw.md`（含 Volta 的 §5.4 符号面实取核对表、
  Ramanujan 的 AC 两栏明细与返工记录、Bohr 的覆盖判定依据与自报/实测 rc 对照、Lagrange 的六态行号对照与抽取命令原文）。
- `resume.round8_returns` 中 Volta / Ramanujan 两条的 `reconstructed_at_checkpoint = true` 应理解为
  **「台账条目系 checkpoint 补记」**，而非「原文已丢失」；已取回原文的部分**以 raw 存档为准**。
- **⚠️ 工具截断**：`close_agent` 输出对 Volta 中段约 **10723 tokens 被截断**（`domain/errors.py::PROBLEM_CODES`
  的 20 个码名只取回前 2 个），Ramanujan 约 90 tokens、Bohr 约 38 tokens 被截断。截断部分**未取回**，
  raw 存档中如实标注 `[TRUNCATED]`，**禁臆造补全**；`PROBLEM_CODES` 全集可从 `src/campaignlab/domain/errors.py` 实测恢复。
