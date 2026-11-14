# R15 · M2-01/S2a 编排器自办入库 —— 独立复验索引（00-index）

- **轮次**：R15　**任务**：M2-01　**子任务**：S2a（A210 拆分：design §11.1 领域层六模块 + §11.2 契约 DTO 面；**不含 §11.3**）
- **原 lane**：A1b　**昵称**：James　**agent_id**：`01a1da6f-f30e-7181-a324-8f41da5ac537`　**档位**：qwen3.8-max / high　**loop_cap**：3
- **lane 结局**：`ERRORED_429_RECEIPT_LOST` —— 429 Too Many Requests；`resume_agent` 与 `send_input` 双双 429 ⇒ **回执丢失、lane 物理不可恢复**
- **入库方**：编排器（自办）　**入库时点**：2026-11-15（Asia/Shanghai）　**HEAD before**：`1d9bcb0`
- **原始命令与输出**：同目录 `commands-and-outputs.log`（146 行 / 8725 B，七段）
- **取证纪律**：`rule_no_trust_handoff_summary_assertions` —— **本棒无 lane 自报证据**，以下每一条读数均由编排器在本机现跑取得；
  凡引用继承数字（设计文档、派单文、旧台账）一律视为待复核参考值（PRE-7）。

## 0. 为什么由编排器自办入库，而不是重派 lane

依 A168 的例外口径（与 A215 同型）：**磁盘产出完整 ⇒ 逐条独立实测代替自报，直接自办入库；不重派、不重做。**
重派会白耗一整棒 max 预算，且既有交付面已能通过全部守护与四门（见 §4/§5），重做无任何信息增量。
交付面在入库前按 **PRE-12** 泊出于 `/tmp/park_a1b_R15/`（`MANIFEST.json` 10 条 sha256），
本提交前复原并**逐条核验 sha256 全等**（含 `D-044.md`；该缺陷单依 A224 已随上一提交 `1d9bcb0` 入库，泊出副本仅作留档）。

采集本证据时刻意**不**在仓库工作树里落任何文件（先写 `/tmp`，收尾再入库）——
第一次尝试把日志直接写进 `evidence/` 导致 §4 的「在树面 ⊆ ADD」断言被自己的日志判红，属**观测者效应**，已在本文件与日志抬头留痕。

## 1. 在树面（PRE-12 前置断言）

`git status --porcelain=v1 -uall` 实测 9 条，恰为 S2a 的 ADD 集，**无第三条 lane 的件、无残留**：

```text
 M src/campaignlab/api/common.py
 M tests/unit/test_domain_errors.py
?? src/campaignlab/domain/activity/{__init__,bindings,checks,clauses,diff,digests,states}.py
```

## 2. 交付面读数

### 2.1 `src/campaignlab/domain/activity/`（新建 7 模块，共 2370 行 / 99261 B）

| 文件 | 行数 | 字节 | sha256[:12] |
| --- | ---: | ---: | --- |
| `__init__.py` | 161 | 5676 | `db271880cd20` |
| `bindings.py` | 197 | 8818 | `ac323b88213c` |
| `checks.py` | 1134 | 45522 | `894392c86169` |
| `clauses.py` | 261 | 11463 | `56eb85ffb5a0` |
| `diff.py` | 225 | 9395 | `8f7ee7168fd2` |
| `digests.py` | 79 | 3959 | `ca60c91c39f2` |
| `states.py` | 313 | 14428 | `954c557fe84a` |

- 六个子模块在全新解释器里逐个 `import` 成功；`__init__` 的 `__all__` 实测 **55** 项。
- 导出面样本：`ACTIVITY_STATES` / `ACTIVITY_TERMINAL_STATES` / `ACTIVITY_TRANSITIONS` / `ACTIVITY_ISSUE_CODES` /
  `ALL_CLAUSE_KEYS` / `ActivityStatus` / `ActivityTransition` / `ActivityTransitionId` …

### 2.2 `src/campaignlab/api/common.py`（纯追加）

- 1153 行 / 45039 B / sha256[:12]=`31a84b00f02c`；`git diff --numstat` = **401 added / 0 deleted** ⇒ **A82 纯追加达标**。
- AST 口径与运行期口径**双测一致**：`__all__` = **78**（S2a 前 51，净增 27）；`set(__all__)` 亦 78（无重复）；
  不可解析名 = **[]**。
- `PROBLEM_CODES` = **20**（未变）、`DomainError` 子类 = **14**（未变）⇒ **A91 的追加额度只用在 DTO 面**，
  问题码面与异常面零改动（这两面是 M2-01 后续 S3/S4 的契约判据，动它们会污染整条链）。

### 2.3 `tests/unit/test_domain_errors.py`（守护订正）

- 189 行 / 7771 B / sha256[:12]=`e2f9fba56bf0`；numstat = **9 added / 3 deleted**（lane 原始为 2/2）。
- 增量的 7/3 由**编排器**依 **A218 / D-044** 同批写入：把 docstring 第 164 行的「51 项、逐字相同」订正为实测值 **78**，
  并补注 A91（追加额度）与 A115（禁写死符号面计数）的依据。
- 用例数 **12 → 12**（无增无减）；基线 **12 passed**，rc=0。
- 函数名的语义升级与「(a) 与 `inspect` 实取的公开名集合对撞」改造**不在本批** ⇒ 归 **FU-48**（与 M2-01/S5 同批最省）。

## 3. 分层红线（AST 实测，全 `domain/**` 扫描）

- `domain/activity/**` 七个模块对 `campaignlab.{api, worker, application, infra}` 的导入边 = **0** ⇒ 领域层零上行依赖。
- 全 `domain/**` 只有 1 条命中：`src/campaignlab/domain/errors.py:36 -> campaignlab.api.common`。
  该文件**不在本棒写集**、在 HEAD 即已存在 ⇒ 属**既有事实、非本棒引入**；收口归 **FU-47**（A219 候选 B：契约层下沉）。

## 4. 守护变异探针（证明钉子有牙，三态双向复原）

| 编号 | 变异 | 结果 | 判定 |
| --- | --- | --- | --- |
| PC0 | 无（基线） | `12 passed`，rc=0 | 绿 |
| PC1 | 往 `__all__` 注入不存在的名字 `ZzNoSuchSymbolR15` | `1 failed, 11 passed`，rc=1 | **红（有牙）** |
| PC2 | 从 `__all__` 移除真名 `Activity` | `1 failed, 11 passed`，rc=1 | **红（有牙）** |
| PC3 | 字节级复原 | sha256 = `31a84b00f02c…`（与 lane 原件**全等**），`12 passed`，rc=0 | 绿（双向复原） |

结论：`test_common_public_surface_is_unchanged` 确实照得到「多了不该多的名字」与「少了该有的名字」**两个方向**，
是 `api/common.py` 公开面的有效唯一钉桩（`no_implicit_reexport` 已开，re-export 漏进 `__all__` 会 mypy 红，但「多名字」只有这条照得到）。
探针全部在 `/tmp` 或原地字节复原，**零落工作树残留**（§6 复验 sha256 全等）。

## 5. 四门读数

- **活动工作树**（本棒 9 件，采集时尚未含本目录的取证件）：
  `ruff format --check .` → **275 files already formatted**；`ruff check .` → **All checks passed!**；
  `mypy` → **Success: no issues found in 95 source files**；`pytest -q` → **615 passed, 6 warnings in 118.68s**。
- **冻结索引树**（`run_commit` 实测，入库判据；预测值先写、实测值逐条对账，不符即原子回滚）：
  `ruff_formatted_files` **276**（in_scope_py 90→**97**、in_scope_md 178→**179**，+1 md 即本文件）、
  `mypy_source_files` **95**、`pytest_passed` **615**。
- 解释器：一律 `uv run --no-sync python`（3.14.10）。系统 `python3`（3.12.3）**禁用于探针**（R14-1：会对 PEP 758 假报 SyntaxError）。

## 6. 探针后工作树一致性

`sha256sum src/campaignlab/api/common.py` → `31a84b00f02c33737afe5f6acdc9ae4f8860281cf728428cfe627f90138ddf4d`，
与泊出前 MANIFEST 记录**全等**；`git status --porcelain=v1 -uall` 仍为同 9 条 ⇒ 变异探针未留任何残留。

## 7. 关联

- 裁定：**A210**（S2 拆 S2a/S2b）· **A217**（S2b 再拆 S2b-1/S2b-2）· **A218**（§11.2 二选一裁为 (b) 按实取值更新）·
  **A224**（D-* 连续性守护强制把 D-044.md 并入上一提交）· **A82 / A91 / A115**（纯追加、追加额度、禁写死符号面计数）
- 缺陷：**D-044**（MINOR / CLOSED；守护用例名与 docstring 同断言体自相矛盾，编排器同批订正 docstring）
- 后续：**FU-48**（函数名语义升级 + (a) 方案评估 + `api/common.py:22` 表述层订正）· **FU-47**（`domain/errors.py:36` 那条既有边的契约层下沉收口）
- 下一棒：**M2-01/S2b-1**（max；派单文 `orchestrator/handoff/R15-lane-M2-01-S2b-1.md` 已在 `fa3a6c8` 入库，
  sha256[:12]=`02a3ea765672`；其 precondition「S2a 必须已入库」由本提交满足）
