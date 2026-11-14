# M0-04 / S2b-3 自验命令表（四元组：命令 / rc / 关键输出 / 期望）

- lane Y · R14 · branch `m0-framework` · HEAD `a05ef28`
- 通道：全部命令在 **WSL** 内 `cd /home/szf/dev/CampaignLab` 后用 `uv run --no-sync` 执行；
  宿主侧只经 `.orch_scratch/*.sh` driver 触发（LANE-COMMON §2 三步范式，避 PowerShell 插值）。
- 表中 rc 与「关键输出」**全部实取**（由 `.orch_scratch/y4_ev.py` 现场重跑并注入），无手抄。
- 「期望」列写的是**判据**而非结果，避免把绝对数字当判据（R13-6）。

## 1. 门禁（路径限定）

| # | 命令 | rc(实测) | 关键输出(实测) | 期望 |
| --- | --- | ---: | --- | --- |
| 1 | `ruff format --check (3 py + design md)` | 0 | 4 files already formatted | rc=0，`N files already formatted`，无重排建议 |
| 2 | `ruff check (3 py)` | 0 | All checks passed! | rc=0，`All checks passed!` |
| 3 | `ruff check --select I --diff (3 py)` | 0 | (empty output) | rc=0 且 diff 输出为空（import 序已合规） |
| 4 | `mypy (full table)` | 0 | Success: no issues found in 86 source files | rc=0，`Success: no issues found in N source files`（N 只报实测+归因） |
| 5 | `pytest -q (dispatch-scoped 4 suites)` | 0 | 93 passed in 28.86s | rc=0，全 passed，0 failed |
| 6 | `pytest -q tests/unit/test_worker_integrity.py` | 0 | 30 passed in 10.08s | rc=0，用例数 ≥24（派单文要求 19 → ≥24） |
| 7 | `pytest -q tests/unit/test_job_repository_terminal.py` | 0 | 24 passed in 6.29s | rc=0，A81/A82 冻结守护全绿（含 worker 无 SQL 文本） |
| 8 | `pytest -q tests/unit/test_layering_edges.py` | 0 | 8 passed in 0.06s | rc=0，`ALLOWED_INFRA_TO_WORKER_EDGES=frozenset()`，反向边 0 |
| 9 | `pytest -q tests/integration/jobs/test_worker_deps.py` | 0 | 18 passed in 5.65s | rc=0，S2b-2 的 deps 套件本棒未回退（deps.py byte_identical） |
| 10 | `pytest --collect-only -q tests/unit/test_worker_integrity.py` | 0 | 30 tests collected in 0.25s | rc=0，collected ≥24，且 = HEAD 的 19 只增不减 |
| 11 | `ruff format --check evidence/M0/M0-04` | 0 | 10 files already formatted | rc=0（A175：证据文件不得带格式债；本行在两个 .md 落盘后实测） |
| 12 | `frozen guard single (post-restore)` | 0 | 1 passed in 0.29s | 复原后 rc=0；正向对照 PC-5 期间同一守护 rc=1（见 positive-control-s2b3.log） |

## 2. git / 静态事实命令

| # | 命令 | 关键输出(实测) | 期望 |
| --- | --- | --- | --- |
| 1 | `git log --oneline -1` | a05ef28 chore(R14): 派单前上下文入库 … | HEAD = 编排器 predispatch 提交，含 S2b-2 的 70be045 为祖先 |
| 2 | `git status --porcelain` | M orchestrator/handoff/M0-04-design.md / M src/campaignlab/infra/db/reposito | 只有本棒 write_set 的 4 条 M + 1 条 ?? 证据日志，无多余文件 |
| 3 | `git diff --numstat HEAD` | orchestrator/handoff/M0-04-design.md:38+/0- / src/campaignlab/infra/db/repos | repositories.py 必须 22 add / **0 del**（A204） |
| 4 | `git show HEAD:src/campaignlab/worker/deps.py \| sha256sum` | 1f2be9761afe == 工作树 1f2be9761afe | byte_identical=True ⇒ A206/A207 未动 deps.py |
| 5 | `git show HEAD:src/campaignlab/cli.py \| sha256sum` | d34fe6962c95 == 工作树 d34fe6962c95 | byte_identical=True ⇒ A208 未碰 cli.py |
| 6 | `grep -c hashlib src/campaignlab/worker/integrity.py` | 0（AST imports 实测无 hashlib） | A157：禁第二份哈希，必须复用 infra 的 hash_file |
| 7 | `grep -c 'def list_all' src/campaignlab/infra/db/repositories.py` | 0 | A204：禁全表无界枚举 |

## 3. 正向对照命令（原始输出全文见 `positive-control-s2b3.log`，216 行 / 14334 bytes；下表 rc 与红点数**全部由该日志解析**）

| # | 变异（原地改 → 跑目标套件 → 字节复原 → sha256 双向核验） | rc(实测) | 红点 | 期望 |
| --- | --- | ---: | --- | --- |
| 1 | PC-1 摘掉判据④ 的 JSON 语法错分支（`except ValueError` → `return []`）（`integrity.py`） | 1 | 1 failed, 92 passed in 31.97s | rc≠0；复原 sha256=3f04ddd2466c == 快照，双向核验 True |
| 2 | PC-2 摘掉判据⑤ 的悬空分支（`ref.id not in job_ids` → `return []`）（`integrity.py`） | 1 | 4 failed, 89 passed in 26.56s | rc≠0；复原 sha256=3f04ddd2466c == 快照，双向核验 True |
| 3 | PC-3 A204 追加面丢掉工作区限定（`list_for_workspace` 去掉 `WHERE workspace_id`）（`repositories.py`） | 1 | 8 failed, 85 passed in 27.15s | rc≠0；复原 sha256=33590e99c580 == 快照，双向核验 True |
| 4 | PC-4 `_check_job` 整体空转（首行 `return []`，④⑤ 全失语）（`integrity.py`） | 1 | 7 failed, 86 passed in 28.32s | rc≠0；复原 sha256=3f04ddd2466c == 快照，双向核验 True |
| 5 | PC-5 往 `integrity.py` 塞只读 `SELECT` 字面量（验 A204 未开后门）（`integrity.py`） | 1 | 2 failed, 91 passed in 27.27s | rc≠0；复原 sha256=3f04ddd2466c == 快照，双向核验 True |
| 6 | PC-5 追加：冻结守护单跑 `test_worker_package_contains_no_table_dml_literals` | 1 | 1 failed in 0.30s | rc≠0 ⇒ A204 豁免未开 SQL 后门 |
| 7 | 复原后全量复验（dispatch-scoped 4 套件） | 0 | 93 passed in 27.51s | rc=0；`ALL_RESTORED_IDENTICAL=True` |

## 4. 复跑方式（编排器可直接执行）

```bash
cd /home/szf/dev/CampaignLab
export PATH="$HOME/.local/bin:$PATH"
PY='src/campaignlab/worker/integrity.py src/campaignlab/infra/db/repositories.py \
    tests/unit/test_worker_integrity.py'
uv run --no-sync ruff format --check $PY orchestrator/handoff/M0-04-design.md
uv run --no-sync ruff check $PY
uv run --no-sync ruff check --select I --diff $PY
uv run --no-sync mypy
uv run --no-sync pytest -q tests/unit/test_worker_integrity.py \
    tests/unit/test_job_repository_terminal.py tests/unit/test_layering_edges.py \
    tests/integration/jobs/
uv run --no-sync pytest --collect-only -q tests/unit/test_worker_integrity.py
git diff --numstat HEAD
```

