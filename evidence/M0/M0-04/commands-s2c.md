# M0-04/S2c · 命令对账表（lane Y2 · qwen3.8-max / reasoning high · R15）

所有工具一律 `uv run --no-sync …`（R14-1：AST / 语法 / pytest / mypy / ruff 探针必须走 3.14.10，
禁系统 `python3` 3.12.3 —— `except A, B:` 是 PEP 758，用 3.12 探针会产生假红）。
写文件一律走「PowerShell 单引号 here-string → CRLF 归一 → UTF-8 无 BOM 落 scratch →
`wsl.exe -e bash <driver.sh>`」；本 lane **零次** `wsl.exe -e bash -lc` 内联表达式，
**零次** git 写操作（`add` / `commit` / `checkout` / `reset` / `stash` / `clean` 全部未用）。

## 1. 开工首检（基线复测）

| #   | 命令                                                        |  rc  | 实测                                                              | 期望                        |
| --- | ----------------------------------------------------------- | :--: | ----------------------------------------------------------------- | --------------------------- |
| 1.1 | `git rev-parse --abbrev-ref HEAD`                             |  0   | `m0-framework`                                                    | `m0-framework`              |
| 1.2 | `git rev-parse --short HEAD`                                  |  0   | `bc2ea43`                                                         | `bc2ea43`                   |
| 1.3 | `git status --porcelain`                                      |  0   | 空（0 行）                                                        | 空                          |
| 1.4 | `sha256sum contracts/openapi.json`                            |  0   | `592571099d638251…8b33aec1`（前 16 位 `592571099d638251`）          | 前 16 位 `592571099d638251` |
| 1.5 | `stat -c %s contracts/openapi.json`                           |  0   | `443309`                                                          | `443309`                    |
| 1.6 | `head -n 52 orchestrator/handoff/M0-04-design.md \| sha256sum` |  0   | `a5e3807475ecf2791a879b30f337ff4c2652c84fbd2efb94ecab64c5348513dd` | 同左（A214 不变量）         |
| 1.7 | `ls src/campaignlab/worker/service.py`                         |  2   | No such file                                                      | ABSENT                      |
| 1.8 | `sed -n '55p' src/campaignlab/worker/deps.py`                  |  0   | `    from campaignlab.worker.service import JobService  # type: ignore[import-not-found]` | 同左        |

## 2. 冻结面复测（R15-1 三处失真的独立第二口径）

| #   | 口径                                                                       | 实测                                                            |
| --- | -------------------------------------------------------------------------- | --------------------------------------------------------------- |
| 2.1 | `ast` 数 `git show HEAD:src/campaignlab/worker/store.py` 的 `def`            | **20** 个（`JobStore` 15 公有 + `claimed`/`cancel_requested`/`total` 3 property + `immediate`/`connect_autocommit`/`short_transaction`/`_is_lock_contention` 4 模块级） |
| 2.2 | `def list_jobs` 在 HEAD 的 `store.py` 里的出现次数                            | **0**                                                             |
| 2.3 | `ast` 扫 HEAD 的 `worker/*.py`（9 个文件）→ `campaignlab.api` 导入边           | **6** 条                                                          |
| 2.4 | `grep -rn 'campaignlab.api' src/campaignlab/worker/`（第二口径，R14-7）        | **6** 处命中，与 2.3 逐条一致（`deps.py:47`、`states.py:20`、`runner.py:30`、`errors.py:27`、`integrity.py:59`、`store.py:33`） |
| 2.5 | `^__all__` / `def job_from_row` 在 `infra/db/repositories.py` 的行号            | 42 / 221（**行号不作判据**，判据一律用符号名；本 lane 未碰该文件）  |
| 2.6 | HEAD 树可被 `ruff format` 的文件数（`git ls-tree -r HEAD` 取 `.py`+`.md`，排除 `spec/ prototype/ web/ node_modules/ .venv/`） | **261**（`.py` 88 + `.md` 173） |

**2.6 是对派单文 §四「259 files already formatted」的实测更正**（归因见 §5.3）。

## 3. 落地与自验（rc 全部实测）

| #   | 命令                                                                                                                       |  rc  | 实测                                        | 期望            |
| --- | -------------------------------------------------------------------------------------------------------------------------- | :--: | ------------------------------------------- | --------------- |
| 3.1 | `uv run --no-sync python .orch_scratch/y2/patch.py`（插 `import unicodedata` + 纯追加 `list_jobs` + 新建 `service.py` + 删 `deps.py:55` ignore + 生成测试文件） |  0   | 4 个文件 `AST_OK`，无 BOM、无 `\r`            | rc=0            |
| 3.2 | `uv run --no-sync ruff format <4 个文件>`                                                                                    |  0   | 3 reformatted / 1 unchanged                  | rc=0            |
| 3.3 | `git diff --numstat src/campaignlab/worker/store.py`                                                                        |  0   | **65 add / 0 del**                           | deleted **必须** 0 |
| 3.4 | `uv run --no-sync ruff check .`                                                                                             |  0   | `All checks passed!`                         | 同左            |
| 3.5 | `uv run --no-sync ruff format --check .`                                                                                    |  0   | `263 files already formatted`（= HEAD 261 + 本 lane 2；当时 A1b 尚未落文件） | rc=0 |
| 3.6 | `uv run --no-sync mypy`                                                                                                     |  0   | `Success: no issues found in 88 source files`（= 基线 86 + 本 lane 2） | rc=0，**A207 生效**：无 `unused-ignore` |
| 3.7 | `uv run --no-sync pytest tests/unit/test_worker_service.py -q`                                                              |  0   | `44 passed`（第 1 轮曾 8 failed，见 §4）      | rc=0            |
| 3.8 | `uv run --no-sync pytest tests/unit/test_worker_service.py --collect-only -q`                                                |  0   | `44 tests collected`                          | —               |
| 3.9 | `uv run --no-sync pytest tests/integration/jobs -q`                                                                          |  0   | `31 passed`（改写前 2 failed，见 §4.3）        | rc=0            |
| 3.10 | 邻接回归（10 个 unit 文件 + `tests/integration/jobs`，**路径限定、非全表**）                                                    |  0   | `299 passed`                                  | rc=0            |
| 3.11 | `uv run --no-sync pytest tests/unit/test_layering_edges.py -q`（含在 3.10 内）                                                 |  0   | 全绿，`ALLOWED_INFRA_TO_WORKER_EDGES` 仍为 `frozenset()`（反向边 0） | 全绿 |
| 3.12 | `uv run --no-sync pytest tests/unit/test_job_repository_terminal.py -q`（含在 3.10 内，A81/A82 全仓守护）                        |  0   | 全绿：`INSERT INTO jobs\|UPDATE jobs` 的文件集合仍 == `{repositories.py}` | 全绿 |

## 4. L 循环（loop_cap=2，实用 1 轮）

第 1 轮 `pytest tests/unit/test_worker_service.py -q` → **8 failed / 36 passed**，三类根因，
全部是**判据写错**而不是交付物有缺陷：

1. `test_list_jobs_rejects_an_unregistered_status_segment` 的 6 个参数化实例断言 `status == 400`，
   实测 422 —— `_STATUS_BY_CODE["VALIDATION_ERROR"] = 422`，且 design §6 的 `listJobs` 行原文就是
   「422 `VALIDATION_ERROR` … `status` 含未知态名」。**改用例**（并同步更正 `service.py::_parse_status`
   docstring 里同一处「→ 400」的笔误）。
2. `test_deps_no_longer_carries_the_import_not_found_ignore` 对全文搜 `type: ignore[import-not-found]`，
   命中了 `deps.py` docstring 里「必须**同步删掉**下面那条 …」的**声明文本** —— 正是 R13-2 记的假红形态。
   **改用 AST 定位那条 `TYPE_CHECKING` 导入的行号、再断言该行行尾无 `#`**。
3. `test_list_jobs_never_mixes_in_rows_from_another_workspace` 自己造数据时两次 `_seed` 用了同一批
   `job_id`，撞 `UNIQUE (workspace_id, id)`。**改用例数据**。

第 2 轮：`44 passed`，未触发 STALLED。

## 5. 分母归因（R13-6：只报实测值 + 归因，禁写死判据）

1. `ruff format --check .`：263（本 lane 代码交付完、A1b 未落文件时）→ 270（A1b 落 7 个 `.py` 后）
   → **272**（本 lane 落 2 个证据 `.md` 后，收尾值）。归因：HEAD 261 + 本 lane 2 个 `.py`
   （`worker/service.py`、`tests/unit/test_worker_service.py`）+ 本 lane 2 个 `.md`
   （`evidence/M0/M0-04/{s2c-worker-service,commands-s2c}.md`；`.log` 不在 ruff 作用域）
   + 在飞 lane A1b 7（`src/campaignlab/domain/activity/{__init__,bindings,checks,clauses,diff,digests,states}.py`）= 272。
2. `mypy`：88（本 lane 代码交付完）→ **95**（收尾时，证据 `.md` 不计入 mypy）。
   归因：基线 86 + 本 lane 2 + A1b 7 = 95。
   两次都是 `Success: no issues found`，**A1b 的在飞文件不是本 lane 的红，也不是本 lane 的绿**。
3. 派单文 §四 给的 `259` 与 HEAD 树实测的 `261` 差 2；本 lane 用「`git ls-tree -r HEAD` 取
   `.py`+`.md` 并按 `pyproject.toml` 的 `extend-exclude` 排除」这一独立口径复算得 261，
   且 261 + 2（本 lane）= 263、261 + 9（本 lane 2 + A1b 7）= 270 两次实测都自洽。
   ⇒ **261 是 HEAD 树的真实分母**，已按 R15-1 的体例报作实测更正，未自行改任何台账。
4. pytest 全表分母（派单文给 571）**未自测**：派单文 §四 明禁本 lane 跑全表，
   全表由编排器在冻结索引树上复跑。本 lane 只报路径限定的实测值：
   `tests/unit/test_worker_service.py` 44 条（新增）、`tests/integration/jobs` 31 条（改写 2 条，条数不变）。

## 6. 阳性对照

见 `positive-control-s2c.log`（PC1–PC9，`tests/unit/test_worker_service.py`）与同文件末段
（PC10–PC11，`tests/integration/jobs/test_worker_deps.py`）。11 条全部 rc≠0、全部 sha256 双向核验复原、
收尾 `git status --porcelain` / `git diff --numstat` 与开跑前逐字一致（工作树零残留）。
