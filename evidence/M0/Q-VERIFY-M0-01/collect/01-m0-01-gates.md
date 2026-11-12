# A1 · M0-01 九项门禁逐项从磁盘重跑

## 1. 「九项门禁」清单出处的核对（存在口径差异，如实记录）

任务卡要求先读 `evidence/M0/M0-01/orchestrator-verification.md` 与 `commands.md` 找「九项门禁」。实测发现：

| 来源 | 门禁清单 | 条数 |
|---|---|---|
| evidence/M0/M0-01/orchestrator-verification.md | 表「门禁」列（锁一致性/依赖同步/前端锁/前端构建/Python 质量门/运行可用性/原型基线无回归/环境诊断） | **8 行，非 9** |
| evidence/M0/M0-01/commands.md | 无「九项」编号清单；为安装与探测过程取证（第 8 节 doctor、第 9 节契约符合性等） | — |
| evidence/M0/summaries/M0-01.md | 「质量门（当前实测 rc 全 0）」列出 9 条命令 | **9 条 ← 本取证采用** |
| orchestrator/tasks/M0-01.md gates: | 4 条（uv sync / npm ci / 环境取证 / 锁入库） | 4 |

结论：名为「九项门禁」的准确清单在 `summaries/M0-01.md`（9 条）；`orchestrator-verification.md` 只有 8 行且集合不同
（它多 `npm ci` 与 import 可用性、少 `ruff format --check`、`mypy`、`pytest`）。本取证按 9 条主清单全量重跑，
并把 verification 表多出的 2 项也实跑（G0a、G10），两来源合起来全覆盖。

## 2. 逐项重跑结果（ts=2026-11-12T23:0x，原文全量在 raw/a1-gates.log）

| # | 命令原文（实跑） | rc | expected | 关键输出 | 与原始证据的差异 |
|---|---|---|---|---|---|
| G1 | `uv lock --check` | 0 | 0 | Resolved 52 packages in 2ms | 一致 |
| G2 | `uv sync --locked` | 0 | 0 | Resolved 52 / Checked 50 packages | 一致 |
| G3 | `uv run --no-sync ruff check .` | 0 | 0 | All checks passed! | 一致（verification 原文为 `uv run ruff check .`，本次加 `--no-sync` 防副作用） |
| G4 | `uv run --no-sync ruff format --check .` | 0 | 0 | **39 files already formatted** | 漂移：recovery 记录当时 18 files；state.json 现为 39（构成见 04/D-006） |
| G5 | `uv run --no-sync mypy` | 0 | 0 | Success: no issues found in **6 source files** | 漂移：D-002 文本当时记「5 个源文件」 |
| G6 | `uv run --no-sync pytest -q` | 0 | 0 | **28 passed** in 0.46s | 漂移：summary 写「8 passed」为 M0-01 时点值；28 为 M0-P01 run-03/04 后现值（state.json counts.pytest_passed=28 吻合） |
| G7 | `npm --prefix web run build` | 0 | 0 | vite ✓ built in 152ms，dist 产物列出 | 一致；同时构成 G13 的 build 半 |
| G8 | `bash scripts/doctor.sh` | 0 | 0 | **PASS=15 WARN=2 FAIL=0 / RESULT: HEALTHY** | **不符预期**（详见 §3） |
| G9 | `bash scripts/verify.sh` | 0 | 0 | SHA256SUMS OK；79/79 PASS；PASS: 字节级复现 | 一致 |
| G0a | `npm --prefix web ci` | 0 | 0 | added 218 packages, audited 219 | 一致（verification「前端锁」行） |
| G10 | `uv run --no-sync python -c "import fastapi,duckdb,pydantic,sqlalchemy,alembic,uvicorn; print(…)"` | 0 | 0 | 2.0.0 2.14.3 2.0.57（duckdb/pydantic/sqlalchemy） | verification 表仅描述「import …」无命令原文，本行为**重建**，如实声明 |

主清单 9/9 与补充 2 项全部 rc=0（G8 的 rc=0 但 WARN 构成与预期不符）。

## 3. G8 doctor 差异取证（重点）

- 实跑 2 次（23:01、23:03）结果相同：`PASS=15  WARN=2  FAIL=0`，`RESULT: HEALTHY`，rc=0。
- 任务预期「PASS=16 WARN=0 FAIL=0」**不符**。两条 WARN 逐一定位：
  1. `[WARN] 工作树存在 1 项未提交改动` —— **本次 Q 取证自身造成**（evidence/M0/Q-VERIFY-M0-01/ 未入库产物）。
     取证开始前 `git status --porcelain` 为空，可排除仓库基线脏。
  2. `[WARN] 未安装 Noto Sans CJK（BLK-02 未解除…）` —— **假阳性**，与磁盘事实矛盾：
     - `dpkg-query` fonts-noto-cjk = `install ok installed`（configure 于 2026-11-12 22:47:59）；
     - `fc-list | grep -i 'noto sans cjk'` 直接执行命中 31 条 Noto 字体（含 Noto Sans CJK JP/HK/KR 等）；
     - 机理实证：`scripts/doctor.sh` 第 246 行 `fc-list | grep -qi "noto sans cjk"`，脚本顶部
       `set -uo pipefail`；`grep -q` 命中即关管道 → `fc-list` 收 SIGPIPE → 管道整体退出码 141 → if 判失败。
       对照实验：无 pipefail rc=0；带 pipefail rc=141（raw 记录见 a1-gates.log 尾部探针）。
     - 后果：**凡字体命中且输出量大时该检查恒 WARN**；与 HEAD 33bf5c5 提交信息「doctor 实为 WARN=0」的表述冲突
       （该 commit 当日字体尚未安装或未触发 SIGPIPE 路径，属推断，不下结论）。
- PASS 计数口径：全绿树（无脏树项）+ 修复上述假阳性后应为 PASS=17（当前 15 过 + 2 警共 17 个结果项），
  与任务给的「16」也不一致，仅如实记录。

## 4. 材料齐备性
- orchestrator-verification.md / commands.md / summaries/M0-01.md / recovery-2026-11-12.md：均存在、已全文读（小文件）。
- 九项全部可从磁盘重跑且 rc=0；无缺失材料。