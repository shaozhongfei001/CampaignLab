# M0-P01 · run-02 · 命令与退出码（D-002 / D-003 修复）

运行号 run-02 · 时间 2026-11-12T21:05:45+08:00 · 分支 m0-framework · 运行时 HEAD f842ec2
环境：Ubuntu 24.04.2 LTS / 系统 python Python 3.12.3 / 项目 venv Python 3.14.10 / uv uv 0.13.7 (x86_64-unknown-linux-gnu) / Node v24.22.3 / SQLite 3.53.1
说明：本轮由「模型切换后的恢复自检」触发。所有 rc 均由脚本实跑后回填，非人工誊写。
前端工程：web/ 骨架已由 M0-01 建立，本轮按手册 13.1 第 6 条实跑 npm 与 doctor 门禁（见第 5 节 G13/G14），rc 均为 0。

## 1. 三份不可变基线的字节可验性

| # | 命令 | rc | 期望 |
|---|---|---|---|
| G1 | `( cd spec/CampaignLab-SDD-v1.0 && sha256sum -c SHA256SUMS --quiet )` | 0 | 0 |
| G2 | `( cd spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta && sha256sum -c DELTA-SHA256SUMS --quiet )` | 0 | 0 |
| G3 | `python3 scripts/check_frontend_baseline.py` | 0 | 0 |

G3 末行输出：`FRONTEND BASELINE PASS 8/8（哈希与字节数逐项一致）`

> 三份基线**必须 `cd` 进各自目录**再校验：清单内路径是目录内相对路径，在仓库根执行会全部 FAILED；
> 且禁止用 `| head` 之类管道掩盖 rc（手册 13.2 / 13.3）。CI 的 `contract-gate` job 已按此拆成三个 step。

## 2. 篡改负例（证明校验器不是恒真）

| 步骤 | 命令 | rc | 期望 |
|---|---|---|---|
| 篡改 | `printf '\n' >> spec/frontend-template-spdb-v1.1/css/tokens.css` 后跑 G3 | 1 | **1** |
| 还原 | `cp /tmp/tokens.bak <原路径>` 后跑 G3 | 0 | 0 |
| 基线未污染 | `git status --porcelain spec/` | 输出=EMPTY | 空 |
| 基线未污染 | `git diff --quiet -- spec/` | 0 | 0 |

> 负例的 rc=1 是**期望值**，不是失败；Q lane 复核时不得据此判红。

## 3. 活契约治理门禁

| # | 命令 | rc | 期望 |
|---|---|---|---|
| G5 | `python3 scripts/check_contracts.py check` | 0 | 0 |
| G6 | `uv run --no-sync python scripts/check_contracts.py check --validate` | 0 | 0 |

G5 输出：`CONTRACT CHECK PASS 登记项=12 实测差异=12 元校验=skipped`
G6 输出：`CONTRACT CHECK PASS 登记项=12 实测差异=12 元校验=6`（元校验需 dev 依赖，故走 `uv run`；CI 无 dev 依赖时自动 skipped）

## 4. Python 质量门与单测护栏（含 D-002 新增工具的用例）

| # | 命令 | rc | 期望 | 实测输出末行 |
|---|---|---|---|---|
| G7 | `uv run --no-sync ruff check .` | 0 | 0 | All checks passed! |
| G8 | `uv run --no-sync ruff format --check .` | 0 | 0 | 33 files already formatted |
| G9 | `uv run --no-sync mypy` | 0 | 0 | Success: no issues found in 6 source files |
| G10 | `uv run --no-sync pytest -q` | 0 | 0 | .............. [100%] 14 passed in 0.07s |

新增 `tests/unit/test_frontend_baseline.py` 6 条用例（手册 13.3 第 4 条要求「每个自建工具至少一条用例钉住核心不变量」）：
真基线 8/8 通过、`SELF_EXCLUDED` 文件名真实存在、清单项均为基线内相对路径且无 `..`、
篡改必 rc=1、行数≠8 必 rc=2（禁静默通过）、README 缺失 rc=2。用例数由 8 增至 14。

## 5. 原型基线、交付包、前端工程与环境自诊

| # | 命令 | rc | 期望 | 实测输出末行 |
|---|---|---|---|---|
| G11 | `bash scripts/verify.sh` | 0 | 0 | PASS: 字节级复现 |
| G12 | `python3 spec/CampaignLab-SDD-v1.0/qa/verify_package.py` | 0 | 0 | PACKAGE PASS 6/6 |
| G13 | `npm --prefix web ci` → `npm --prefix web run build` | 0 | 0 | `npm_ci_rc=0`、`npm_build_rc=0`、`built in 129ms`（dist 与 node_modules 已忽略，工作树未变脏） |
| G14 | `bash scripts/doctor.sh` | 0 | 0 | `RESULT: HEALTHY`，PASS=15 WARN=2 FAIL=0（WARN 之一为 BLK-02 未装 Noto Sans CJK；中文字体实测 7 条可用） |

## 6. D-003 修复：证据文件必须能入库

修复前：`.gitignore` 的 `*.log` 把 5 个证据日志排除，`orchestrator/state.json` 中
`tasks["M0-P01"].gates[]` 的 7 条 evidence 指针里有 4 条在仓库内悬空。

| 检查 | 命令 | 实测 | 期望 |
|---|---|---|---|
| 已跟踪证据文件数 | `git ls-files evidence \| wc -l` | 8 | 修复前为 8 |
| 待入库证据文件数 | `git ls-files --others --exclude-standard evidence \| wc -l` | 6 | 6（4 个 run-01 日志 + 1 个 run-02 日志 + 本 commands.md 自身） |
| evidence 下仍被忽略的文件数 | `git status --porcelain --ignored=matching -- evidence \| grep -c '^!!'` | 0 | **0** |

判定：否定规则 `!evidence/**/*.log` 生效（以 `git ls-files --others --exclude-standard` 为权威依据；
`git check-ignore -v` 对否定匹配也会打印规则并返回 0，不能作为「是否被忽略」的判据）。

## 7. 本轮结论

- 全部门禁 rc 与期望一致（第 2 节负例 rc=1 为期望值）。
- 三份基线均可字节级复验，`spec/**` 未被污染。
- D-002（前端基线机读校验）与 D-003（证据可入库）均已修复并留证，状态 FIXED_PENDING_Q。
- 待 M0 阶段 Q 交叉验证时，与 D-001 一并复核。