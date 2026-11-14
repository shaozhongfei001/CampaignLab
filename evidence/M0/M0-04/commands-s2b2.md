# M0-04/S2b-2 命令日志（lane Y 专属；禁写 `commands.md` / `commands-s2b1.md` / `commands-s7.md`）

记账口径：**四元组** = cwd + 命令 + rc + 关键输出。门禁／取证类命令的 rc 一律由
`subprocess.run(...).returncode` 采集，或由 WSL 内 bash driver 的 `echo "rc=$?"` 采集（**在 WSL 内**取值，
不经 PowerShell 插值）。宿主 PowerShell 与 WSL 之间的文件传递一律走 LANE-COMMON §2 的三步通道：
PowerShell 单引号 here-string（CRLF→LF）→ `.orch_scratch/` 落盘（UTF-8 无 BOM）→
`wsl.exe -e bash /mnt/d/ws/codex_rd/ss_campaignlab/.orch_scratch/<driver>.sh`。

采集时点：branch `m0-framework`，HEAD `6c35aad`（全 sha `6c35aadb3e2352d9705561c09efd3c74e94a6fb4`）。派单基线 = `51af733`。

## 1. 门禁与取证命令（四元组）

| # | 类型 | cwd | 命令 | rc | 关键输出 |
| --- | --- | --- | --- | --- | --- |
| 1 | 只读 | `/home/szf/dev/CampaignLab` | `git rev-parse --short HEAD` + `git rev-parse --abbrev-ref HEAD` | **0** | `6c35aad` / `m0-framework` |
| 2 | 只读 | `/home/szf/dev/CampaignLab` | `wsl.exe -e bash .orch_scratch/readf.sh orchestrator/handoff/LANE-COMMON.md` | **0** | 120 行全文（派单第一步①，`cat -n`） |
| 3 | 只读 | `/home/szf/dev/CampaignLab` | `wsl.exe -e bash .orch_scratch/readf.sh orchestrator/handoff/R13-lane-Y-M0-04-S2b-2.md` | **0** | 126 行全文（派单第一步②） |
| 4 | 只读 | `/home/szf/dev/CampaignLab` | `sha256sum <4 files>` + `wc -l <4 files>` + `ls -la evidence/M0/M0-04/` | **0** | 4 个 sha256 与取证文件 §0 表格逐字一致 |
| 5 | 只读 | `/home/szf/dev/CampaignLab` | `bash .orch_scratch/y_final_gates.sh`（G1 `ast.parse` ×4 ＋ G2 字节卫生 ×4，**只读**不改文件） | **0** | `AST OK` ×4；`noBOM noCR ENDS_NL` ×4 |
| 6 | 门禁 | `/home/szf/dev/CampaignLab` | `uv run --no-sync ruff format --check <4 files>` | **0** | `4 files already formatted` |
| 7 | 门禁 | `/home/szf/dev/CampaignLab` | `uv run --no-sync ruff check <4 files>` | **0** | `All checks passed!` |
| 8 | 门禁 | `/home/szf/dev/CampaignLab` | `uv run --no-sync ruff check --select I --diff <4 files>` | **0** | `(空 diff = import 序无需重排)` |
| 9 | 门禁 | `/home/szf/dev/CampaignLab` | `uv run --no-sync mypy`（全表，LANE-COMMON §3.4 / §3.6） | **0** | `Success: no issues found in 86 source files` |
| 10 | 门禁 | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q <7 个路径限定套件>` | **0** | `169 passed in 35.89s` |
| 11 | 只读 | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q --collect-only <逐套件>` ×7 ＋ 合并一次 | **0** | 19 / 18 / 8 / 47 / 40 / 24 / 13，合计 169 ✓ |
| 12 | 只读 | `/home/szf/dev/CampaignLab` | `git ls-tree -r --name-only <rev> -- src tests scripts \| grep -c '\.py$'`（`51af733` / `d22b5f6` / HEAD `6c35aad` 各一次）＋ `find src tests scripts -name '*.py' \| wc -l` ＋ `git diff --name-status 51af733 <HEAD> -- src tests scripts` | **0** | 80 / 81 / 82；工作树 86（mypy 分母归因，见取证 §12.1） |
| 13 | 只读 | `/home/szf/dev/CampaignLab` | `git diff --no-index --numstat /dev/null <file>` ×4 | **1** | 271 / 156 / 596 / 605 added；rc=1 是「有差异」的正常语义，索引未被触碰 |
| 14 | 只读 | `/home/szf/dev/CampaignLab` | `git status --porcelain -- <每条硬禁路径>` | **0** | 仅 4 行命中，全在 `orchestrator/handoff/`（取证 §13） |
| 15 | 只读 | `/home/szf/dev/CampaignLab` | `grep -n 'no_table_dml_literals' -A 60 tests/unit/test_job_repository_terminal.py` | **0** | 取回冻结守护原算法（verb 正则 ＋ docstring 排除 ＋ 三条事务白名单），**未改该文件** |
| 16 | 只读 | `/home/szf/dev/CampaignLab` | `sed -n '/def test_a154_forbidden_third_wiring_is_red/,/^def /p' tests/integration/jobs/test_worker_deps.py`（同法取 rc2 / jobs 侧披露两条用例） | **0** | 抄回取证 §6 / §7 / §11 的断言口径 |
| 17 | 取证 | `/home/szf/dev/CampaignLab` | `uv run --no-sync python .orch_scratch/y_facts.py` | **0** | `FACTS_OK bytes= 18030` / `keys= 60` → `/tmp/y_facts.json` |
| 18 | 取证 | `/home/szf/dev/CampaignLab` | `python3 .orch_scratch/y_facts2.py`（按冻结守护原算法重算零 SQL 文本） | **0** | `worker_package_sql_verb_offenders = []`；被扫 9 个 `.py`（分母断言，防扫空全绿） |
| 19 | 取证 | `/home/szf/dev/CampaignLab` | `bash .orch_scratch/y_facts3.sh`（`worker/__init__.py` 未改自证 ＋ `type: ignore` 真实行号 ＋ 硬禁自证） | **0** | `git diff --quiet HEAD -- worker/__init__.py` rc=0；`deps.py:55` |
| 20 | 写 | `/home/szf/dev/CampaignLab` | `bash .orch_scratch/run_pos_control.sh`（14 变异正向对照） | **0** | 14 RED / 14 复原 PASS / 末尾 `169 passed`；日志 48023 bytes → `/tmp/s2b2-positive-control.log` |
| 21 | 写 | `/home/szf/dev/CampaignLab` | `shutil.copyfile('/tmp/s2b2-positive-control.log', 'evidence/M0/M0-04/positive-control-s2b2.log')` | **0** | sha256 见取证 §15 |
| 22 | 写 | `/home/szf/dev/CampaignLab` | `uv run --no-sync python .orch_scratch/y_ev.py`（生成取证文件与本文件） | **0** | 见 §3 |
| 23 | 门禁 | `/home/szf/dev/CampaignLab` | `uv run --no-sync ruff format evidence/M0/M0-04/s2b2-integrity-deps.md evidence/M0/M0-04/commands-s2b2.md` | **见 §3** | A175：`ruff format` 作用域含 `.md`，证据文件必须过 |
| 24 | 门禁 | `/home/szf/dev/CampaignLab` | `uv run --no-sync ruff format --check evidence/M0/M0-04/*.md` ＋ `ruff check` | **见 §3** | 落盘后复验 |

## 2. 写入通道 driver 清单（本 lane 产出，全在 `.orch_scratch/`，**未落工作树**）

源码／测试的落盘一律走「here-string → `.orch_scratch/<payload>` → driver `cp` 进仓库 → **立刻** `ast.parse`
自证（R12-1）→ 才跑测试」；下表 driver 的产物即取证 §0 的 4 个文件（sha256 已双向核验）。

| 用途 | driver / payload |
| --- | --- |
| 读文件（避 PowerShell 插值陷阱） | `readf.sh`（`cat -n` + 行区间）、`readw.sh` / `readx.sh` |
| 落 `integrity.py` / `deps.py` | `install_src.sh` + payload `integrity.py` / `deps.py` |
| 落单元测试 | `install_unit_test.sh` + payload `test_worker_integrity.py`；`install_deps_test.sh` + payload `test_worker_deps.py` |
| 门禁批量 | `gates_all.sh`、`gate_src.sh`、`bg_gates.sh`、`y_final_gates.sh`（**只读**版，不改文件） |
| 正向对照 | `run_pos_control.sh` + `pos_control.py` |
| 取证 | `y_facts.py`、`y_facts2.py`、`y_facts3.sh`、`y_ev.py`、`y_dump{1..4}.sh`、`y_collect{,2}.sh`、`y_mypy_attr.sh`、`y_base.sh`、`y_loggrep.sh` |
| 迭代修补（L 循环内） | `patch1.sh`、`patch2.sh`、`fix_deps_test.py`、`fix_unit_test{,2,3}.py`、`fix_lint.py`、`fix_fixer{,2}.py`、`add_manifest_tests.py` |
| mypy / ignore / 符号探查 | `mypyprobe.sh`、`ignoreprobe.sh`、`introspect.sh`、`s2cprobe.sh`、`s2c.py`、`dump{2..6}.py` |

## 3. 证据文件落盘后的复验（A175：`ruff format` 的作用域含 `.md`）

`ruff format` 对 `.md` 的作用实测（A175 / LANE-COMMON §3.1）。**分趟测**：每趟把占位符换成实测行后再复验，
故第 3–6 行测的都是「替换之后」的状态；表内所有 rc 由 `subprocess.run(...).returncode` 采集。

| 趟 | 命令（cwd = `/home/szf/dev/CampaignLab`） | rc | 关键输出 |
| --- | --- | --- | --- |
| 1 | `uv run --no-sync ruff format evidence/M0/M0-04/s2b2-integrity-deps.md evidence/M0/M0-04/commands-s2b2.md` | **0** | `1 file reformatted, 1 file left unchanged` |
| 2 | `uv run --no-sync ruff format --check evidence/M0/M0-04/s2b2-integrity-deps.md evidence/M0/M0-04/commands-s2b2.md` | **0** | `2 files already formatted` |
| 3 | 趟 1–2 写入后复验：`uv run --no-sync ruff format --check evidence/M0/M0-04/s2b2-integrity-deps.md evidence/M0/M0-04/commands-s2b2.md` | **0** | `2 files already formatted` |
| 4 | 目录级复验（含既有 `commands.md` / `commands-s7.md` / `commands-s2b1.md` / `s3-artifacts.md` / `s7-job-dto.md` / `s2b1-hash-file.md`，**均未改**）：`uv run --no-sync ruff format --check evidence/M0/M0-04/` | **0** | `8 files already formatted` |
| 5 | `uv run --no-sync ruff check evidence/M0/M0-04/`（该目录无 `.py`，ruff 只出 warning） | **0** | `All checks passed! / warning: No Python files found under the given path(s)` |
| 6 | 本行写入前一刻的最终态复验：`uv run --no-sync ruff format --check evidence/M0/M0-04/s2b2-integrity-deps.md evidence/M0/M0-04/commands-s2b2.md` | **0** | `2 files already formatted` |

## 4. 禁触清单自证

本 lane 写入的路径只有 7 个，全部在 write_set 内：

- `src/campaignlab/worker/integrity.py`（新建）
- `src/campaignlab/worker/deps.py`（新建）
- `tests/unit/test_worker_integrity.py`（新建）
- `tests/integration/jobs/test_worker_deps.py`（新建）
- `evidence/M0/M0-04/s2b2-integrity-deps.md`（新建）
- `evidence/M0/M0-04/commands-s2b2.md`（新建，即本文件）
- `evidence/M0/M0-04/positive-control-s2b2.log`（新建，正向对照原始日志）

**未执行任何 git 写操作**（无 `add` / `commit` / `push` / `checkout` / `reset` / `stash` / `branch`）；git 命令
全部只读：`rev-parse`、`status`、`ls-tree`、`diff`（含 `--no-index`，不触碰索引）。未写 `orchestrator/**`；
未写 `scripts/**`（FU-30）；未写 `spec/**`、`contracts/**`、`migrations/**`、`docs/**`、`web/**`、
`src/campaignlab/{infra,api,domain}/**`；未 sudo；未整读 443 KB 活契约（只读 `M0-04.slice.json` 切片）；
未在 `tests/integration/jobs/` 新增 `conftest.py`（`rule_full_tree_mypy_on_basename_collision`）；
未跑全表 `ruff format --check .` / 全表 `pytest` 当自己的判据（LANE-COMMON §4）。

