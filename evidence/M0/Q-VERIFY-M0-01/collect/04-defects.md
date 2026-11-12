# A4 · 缺陷 D-001..D-006 「修复/验证」段材料核对与复跑

方法：逐个读 `orchestrator/defects/D-00X.md` 的「修复」「验证」段，从中提取验证命令原文，从磁盘复跑记 rc。
原始输出：`raw/a4-defects.log`。只列事实，不下 CLOSED 结论。

## D-001 切片工具 --tables 静默 NOT_FOUND

| 验证声明（缺陷单/引 recovery 第4节） | 复跑命令 | expected | 实测 rc | 事实 |
|---|---|---|---|---|
| `--all-tables` 28 表 0 NOT_FOUND、全部 STRICT; 收尾 | `python3 scripts/contract_slice.py --all-tables --out /tmp/qverify_all.json` | 0 | 0 | **28 表 + 6 个 `<table>__indexes` 组键，ddl 段共 34 键**（D-004 修复后工具新增索引组，属设计变更；28 张真实表全部抽取、0 NOT_FOUND、每块 `CREATE TABLE` 开头 `STRICT;` 收尾，实测 `tables=34 not_found=0` 与逐键检查通过）。`grep -c "CREATE TABLE" contracts/sqlite-v1.sql` = **28** ✓；`workspaces` 块 head/tail 实测 ✓ |
| 未知表 rc=2 | `--tables no_such_table` | 2 | **2** | stderr `FAIL 切片目标未命中 … ['ddl:no_such_table']` ✓ |
| 差分回归 --ops/--ac/--ui 与修复前逐字节一致 | （需 HEAD 旧版工具，已被 D-004 版取代） | — | 不可直接复跑 | 该条属「修复当时」的一次性差分，磁盘不可重放；由 `tests/unit/test_contract_slice.py`（现 22 条用例中对应项）与金样本重切复现承担（见 D-004/A5） |
| 金样本重跑逐字节一致 | 见 A5：重切 M0-02/M0-03 → `diff -q` | 0 | **0** | 两切片与入库文件逐字节一致 |
| 8 条单测（分母 28、索引 6/6 等） | `uv run --no-sync pytest -q` 含 test_contract_slice.py | 0 | 0 | 全仓 28 passed（该文件用例数为修复时 8 条 + D-004/005 扩至 22 条，「8 例」为历史口径） |

材料：齐（缺陷单 + recovery 第 4 节表 + 可复跑部分全绿）。不可复跑项已如实标注。

## D-002 前端基线无机读校验

| 验证声明 | 复跑命令 | expected | 实测 rc | 事实 |
|---|---|---|---|---|
| 8/8 OK | `python3 scripts/check_frontend_baseline.py` | 0 | 0 | `FRONTEND BASELINE PASS 8/8（哈希与字节数逐项一致）` |
| 篡改负例 rc=1 | **未重跑**（禁令：不为负例篡改 spec/） | 1 | — | 引用编排器实测：`evidence/monthly/M0-P01/run-04/commands.md` §1.1（cp 备份→printf 追加换行→rc=1→cp 还原→`git status spec/.../tokens.css` 行数 0，按字节还原） |
| `qa/verify_package.py`=PACKAGE PASS 6/6 | 缺陷单写 `qa/verify_package.py`（仓库根无此文件，首跑 rc=2）；实际入库路径按 state.json G12：`python3 spec/CampaignLab-SDD-v1.0/qa/verify_package.py` | 0 | 0 | `PACKAGE PASS 6/6`。**注意**：M0-01 期证据（verification.md/恢复单）曾以 `qa/verify_package.py PACKAGE PASS 6/6` 行文，仓库根并无该路径，属**文档命令原文与磁盘路径不一致**（不影响结论：补丁包内脚本可运行） |
| ruff/format/mypy/pytest | 同 A1 G3/G4/G5/G6 | 0 | 0 | 全部 rc=0；缺陷单括注「mypy 5 个源文件」「pytest 8 passed」为**当时值**，现值 6 源文件/28 passed（后续任务加文件所致，非回归） |
| verify.sh=0、check check=PASS | A1 G9 / A2 C1 | 0 | 0 | 一致 |
| 补记 6 条前端单测 | `uv run --no-sync python -m pytest -q -k frontend_baseline` | 0 | 0（并入 8 passed 组合） | collect 可见 6 条 test_frontend_baseline 用例 ✓ |

材料：齐；两处口径漂移（文件数/用例数为历史值、verify_package 路径）已列出。

## D-003 证据日志被 .gitignore 忽略

| 验证声明 | 复跑 | expected | 实测 | 事实 |
|---|---|---|---|---|
| `git check-ignore -v` 对 5 个证据 .log 非 0 | 逐条跑 | ≠0 | 5 条全部 **rc=1** | precheck-base / post-merge-precheck / merged-diff / check-validate / frontend-baseline.log 均不再被忽略 |
| `git ls-files evidence` 由 8 增至 14 | 计数 | ≥14 | **16** | 后续 run-03/04 证据入库使分母继续增长，与「14」不冲突（14 为当时值） |
| .gitignore 含 `!evidence/**/*.log` | grep | 命中 | 第 18 行命中 | ✓ |

材料：齐。

## D-004 切片源钉死基线 + 版本硬编码

| 验证声明 | 复跑 | expected | 实测 | 事实 |
|---|---|---|---|---|
| 切片 spec_version=1.0.1 | S1/S4 + 两切片文件 | 1.0.1 | 1.0.1 | 实跑与入库切片均 ✓ |
| source 段 sha16/bytes | A5 独立复算 | 01bd28f0772f506e/443552 | 同左 | ✓ |
| 未知 op rc=2 且不写出文件 | S3 | 2 | 2 | `ls /tmp/qverify_noop.json` rc=2（无产物）✓ |
| test_live_contract_is_the_source | pytest -k | 0 | 0 | 用例存在且过 ✓ |
| wave1 差分字节等价 | 重切 diff（见 A5） | 0 | 0 | ✓ |
| D-004 单测扩至 22 条 / 全仓 28 passed | collect+pytest | — | 28 passed | ✓（test_contract_slice.py 现逐条清点 = **22 条**，`--collect-only | grep -c '::'` = 22，与 D-004 文「扩至 22 条」一致；全仓 28 passed 自洽） |

材料：齐。注：缺陷单「修复方案（尚未执行）」为建单当时文本，其「修复（已执行）」节与磁盘一致。

## D-005 AC-MR 不可解析

| 验证声明 | 复跑 | expected | 实测 | 事实 |
|---|---|---|---|---|
| 基线 AC 行数 35 | `grep -c ''^| AC-'' spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md` | 35 | **35** ✓ | |
| 月报 AC 行数 12 | `grep -cE ''^\|\s*AC-MR-'' …append.md` | 12 | **12** ✓ | |
| 47 条全可解析 | `-k all_47_acceptance_ids_resolve` | 0 | 0 ✓ | |
| AC-MR-05 含 83.33% / AC-MR-08 含 79.31% | grep 原文行 | 命中 | 两行均命中（83.33% 与 79.31% 原样在场）✓ | |
| 未知 AC rc=2 | S5 `--ac AC-MR-99` | 2 | 2 ✓（且未静默） | |
| 正常路径 rc=0 spec_version=1.0.1 | S4 `--ops getHealth --ac AC-001,AC-MR-01` | 0 | 0 ✓ acceptance_rows=2 条 | |

材料：齐。

## D-006 ruff format 分母口径（重点复核）

state.json `resume.self_check_gates_rc0.counts` 实测读取：
`ruff_formatted_files=39`，`ruff_lint_scope_files=6`，`ruff_formatted_files_composition = {total:39, in_scope_py:6, in_scope_md:33, …}`。

两条复现命令实跑：

| 复现命令（composition 原文） | 期望 | 实跑 |
|---|---|---|
| `git ls-files ''*.py'' | grep -vE ''^(spec|prototype|web)/'' | wc -l` | 6 | **6** ✓ |
| `git ls-files -z ''*.md'' | tr ''\0'' ''\n'' | grep -vE ''^"?(spec|prototype|web)/'' | wc -l` | 33（**当前**值） | **33** ✓ |

- `uv run --no-sync ruff format --check .` 实跑 = **39 files already formatted**（rc=0），39 = 6(py) + 33(md) 与两条复现命令自洽。
- **与任务简报「composition 里记的 31/39」的关系（如实说明）**：`orchestrator/defects/D-006.md` 第 3 节记载的当时构成是 **37 = 6 py + 31 md**（22:50 实测）；随后 22:52 的治理提交（ce2d9fa）新增 2 个 .md（`evidence/monthly/M0-P01/run-04/commands.md`、`orchestrator/defects/D-006.md` 本身）并同步把 state.json composition 改为 **39 = 6 + 33**（composition.measured_after 字段自述了这一 37→39 过程）。当前磁盘三数（39/6/33）与 state.json **完全一致**；「31」只存在于 D-006.md 的历史叙述中。简报里「31/39」是把历史 md 数与当前 total 混写，实测无未解释缺口（差 2 个 md，来源即上述两文件的入库）。
- 附带事实：磁盘 .md（find 口径，排除 spec/prototype/web/.venv/.git）= **34**，比 git ls-files 口径多 1：`.pytest_cache/README.md`（pytest 自建缓存、被 .gitignore 覆盖、且 ruff 不计数——39 的构成不含它）。不构成口径冲突。

材料：齐（缺陷单 + composition 字段 + 可复现命令闭环）。

## 本次新采集事实（无对应缺陷单，供判定档处置）

- **F-A4-1（新缺陷候选）**：`scripts/doctor.sh` 第 246 行字体检查 `fc-list | grep -qi "noto sans cjk"` 在
  `set -uo pipefail` 下命中即触发 SIGPIPE，管道 rc=141 → **字体实际已装却恒判 WARN（假阳性）**。
  机理对照实测：无 pipefail rc=0；带 pipefail rc=141（详见 01 文件 §3）。受影响面：G14_doctor 的 WARN 计数、
  BLK-02 解除状态的机器可读证据、以及 HEAD 提交信息「doctor 实为 WARN=0」与当前磁盘状态（WARN=2）的矛盾。
- F-A4-2（文档措辞）：D-002 验证段命令原文 `qa/verify_package.py` 在仓库根不存在（实际路径在 spec 基线内），
  state.json G12 已用正确路径。
- F-A4-3（口径漂移记录）：D-001「8 例单测」、D-002「mypy 5 源文件 / pytest 8 passed」均为历史值，现值 22 例 / 6 文件 / 28 passed，后续任务自然增长，无回归迹象。