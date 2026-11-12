# Q-VERIFY-M0-01 · M0 阶段独立判定报告（Q lane 判定档 / qwen3.8-max）

- 判定时间：2026-11-12T23:55 → 2026-11-13T01:10（Asia/Shanghai）
- 仓库：`/home/szf/dev/CampaignLab`　分支 `m0-framework`
- **HEAD 在判定期间发生变动**（并发 lane 与编排器推进所致），本报告每条结论都标注测量时点：
  - `6d9f1b2`（23:55–00:15 的全部实测：doctor 确定性、fc-list、Python 门禁、分母 51、契约定点提取）
  - `b1f38a9`（01:03–01:10 的复测：分母 53、pytest 38、D-009 验证、CR-002 §6 事实核实）
  - 任务简报给的 `ee51f3f` **已不是 HEAD**（其后有 `6d9f1b2`、`b1f38a9` 两次提交）
- 判定纪律：不采信任何自述（含取证档结论、编排器转述、提交信息、缺陷单自述），一切以磁盘实测与原文比对为准。
- **引用而非复跑的项**（因并发 lane 正在改 `web/`，且判定档被禁运行 npm/node/vite/playwright）：
  `G13 npm ci && npm run build`、`G11 bash scripts/verify.sh`、`G14 doctor 的完整变体（内部会调 verify.sh 与 node）`、
  `D-002 篡改负例（需改 spec/，被禁）`。这些一律引用 `collect/raw/*.log` 与 `evidence/monthly/M0-P01/run-04/commands.md` 的已实测 rc，并逐条标注。
- 原始命令输出：`evidence/M0/Q-VERIFY-M0-01/judge/*.log`（全部经 `git ls-files --others --exclude-standard` 确认可入库）

## 判定摘要（一行一项）

| 项 | 判定 | 一句话依据 |
|---|---|---|
| A · M0-01 总判定 | **PASS_WITH_TODO** | 9 项门禁中 6 项由本档复跑 rc=0、3 项引用；材料齐备；但门禁清单口径三份互不相同（见 D），且多处历史计数未标时点 |
| B · D-001…D-009 | **9/9 CLOSED**（D-008 附跟进） | 每单的可复跑验证项本档全部实跑通过；D-008 自身两条缺陷已修，但同类错误在 M0-03 卡仍在（见 F） |
| C · D-007 独立复核 | **CLOSED（修复成立）** | doctor 3 次摘要逐字一致 rc=0；`grep -ci` 20/20 rc=0 且命中恒 10；原写法 `grep -qi` 20 次中 15 次 rc=141；确定性单测 4 passed |
| D · A1 文档不一致 | **成立，MINOR** | 四份清单（state.json 9 / summaries 9 / verification 8 / 任务卡 4）集合互不相同，无任一为超集；须指定唯一权威并交叉引用 |
| E · A3 三条措辞级 | ① MINOR 不改文件 ② **MINOR 必须改 CR-001** ③ 非缺陷 | ② 实测为 4 个 pointer / 2 个属性名 / 3 个逻辑属性，「三个新增属性」未写口径 |
| F · 29 张卡 AC 转述 | **分母异常 + 1 处 MAJOR 同类错误** | 磁盘只有 4 张卡（state.json 29 个任务键）；47 分母程序化成立（35+12）；`M0-03.md:12/:38` 把页面侧深链仍挂 AC-034 |
| G · ADR-005 / CR-002 | **均不与 spec/活契约冲突；CR-002 影响面低估** | `Problem.type` 无 pattern 且 1–250 容得下 URN（最长 120）；三默认值与 60s/8MiB/64MiB 对象不同不混用；`status` 参数同类缺口实测还有 5 处 |
| H · M0-02/S1 设计 | **PASS_WITH_TODO** | 117 行 ≤120、7 节齐、5 个 operationId 与切片一致、S3–S5 白名单全落在修正后 scope_allow 内、未决问题未偷渡；但 §5/§6 有 3 处已过期文本会误导 S5 |
| I · 分母核对 | **PASS（两个时点均自洽）** | 6d9f1b2：51 = tracked 51 + untracked 0，pytest 32、mypy 7 与 counts 一致；b1f38a9：53 = 53 + 0，pytest 38、mypy 8 与更新后 counts 一致 |

---

## A · M0-01 总判定：**PASS_WITH_TODO**

### A.1 「九项门禁」的口径出处（四份清单互不相同，详见 D 项）

本档以 `evidence/M0/summaries/M0-01.md` 第 6–8 行的 9 条命令为主清单逐条处置，并补跑
`state.json → tasks.M0-01.gates`（9 条）中主清单未含的 3 条（`npm ci`、cp314 wheels、D-001 修复），
以及 `resume.self_check_gates_rc0`（16 项 G 编号）中可复跑的 Python 侧项。

### A.2 逐项 rc 与「复跑／引用」区分

| # | 命令原文 | rc | expected | 本档处置 | 依据 |
|---|---|---|---|---|---|
| 1 | `uv lock --check` | 0 | 0 | **复跑** | `judge/a1-python-gates-rerun.log`（`Resolved 52 packages`） |
| 2 | `uv sync --locked` | 0 | 0 | **复跑** | 同上（`Checked 50 packages`） |
| 3 | `uv run --no-sync ruff check .` | 0 | 0 | **复跑** | 同上（`All checks passed!`） |
| 4 | `uv run --no-sync ruff format --check .` | 0 | 0 | **复跑** | 同上；6d9f1b2 时 `51 files`，b1f38a9 时 `53 files`（见 I） |
| 5 | `uv run --no-sync mypy` | 0 | 0 | **复跑** | 同上；`7 source files`（6d9f1b2）→ `8`（b1f38a9） |
| 6 | `uv run --no-sync pytest -q` | 0 | 0 | **复跑** | 同上；`32 passed`（6d9f1b2）→ `38 passed`（b1f38a9） |
| 7 | `npm --prefix web run build` | 0 | 0 | **引用**（并发 lane 正在改 `web/`，判定档禁 node） | `collect/raw/a1-gates.log` G7（`vite ✓ built`）；本档未复跑 |
| 8 | `bash scripts/doctor.sh` | 0 | 0 | **复跑（SKIP_VERIFY 变体，3 次）**；完整变体引用 | `judge/c1-…log`、`c2-…log`；完整变体 rc=0 引 `collect/raw/a1-gates.log` G8 与 `run-04/commands.md` 第 7 节 |
| 9 | `bash scripts/verify.sh` | 0 | 0 | **引用**（内部执行 `node campaignlab-review-work/verify.mjs`，判定档禁 node） | `collect/raw/a1-gates.log` G9（`79/79 PASS`、`PASS: 字节级复现`） |
| 补1 | `npm --prefix web ci` | 0 | 0 | **引用** | `collect/raw/a1-gates.log` G0a（`added 218 packages`） |
| 补2 | cp314 wheels（BLK-06 关闭依据） | 0 | 0 | **复跑** | `judge/a2-…log`：python 3.14.10 / duckdb 2.0.0 / pydantic_core 2.50.4 / fastapi 0.162.4 / sqlalchemy 2.0.57 / alembic 1.20.1 / uvicorn 0.54.0，与 `evidence/M0/M0-01/wheels.md:18-24` 逐字一致 |
| 补3 | `check_contracts.py check` / `check --validate` | 0 / 0 | 0 / 0 | **复跑** | `judge/a1-…log`：`登记项=12 实测差异=12`、`元校验=6` |
| 补4 | `check_frontend_baseline.py` | 0 | 0 | **复跑** | `judge/a1-…log`：`FRONTEND BASELINE PASS 8/8` |
| 补5 | `spec/CampaignLab-SDD-v1.0/qa/verify_package.py` | 0 | 0 | **复跑** | `judge/a1-…log`：`PACKAGE PASS 6/6` |
| 补6 | D-001 切片修复（`--all-tables` / 负例） | 0 / 2 | 0 / 2 | **复跑** | `judge/b1-defects-d001-d005-rerun.log` |
| 补7 | `spec/` 未污染、`evidence/` 无被忽略文件 | 空 / 0 项 | 同 | **复跑** | `judge/e2-required-arrays-and-changes-schema.log` §6 |

**材料齐备性**：`state.json → tasks.M0-01.gates[].evidence` 的指针全部落地且已跟踪
（`commands.md` 16792B、`npm.md` 854B、`wheels.md` 7073B、`orchestrator-verification.md` 2455B、
`recovery-2026-11-12.md` 4109B、`env.md` 10474B、`summaries/M0-01.md` 1856B、`defects/D-001.md` 2018B）——
无悬空指针（D-003 的失效模式未复发）。

### A.3 判定

**PASS_WITH_TODO**。理由：所有可复跑门禁 rc==expected，无一项回归；不可复跑的项（G7/G9/G13 与 doctor 完整变体）
均有一手 `collect/raw` 日志与 `run-04` 记录支撑，且未复跑原因（node/npm 禁令 + 并发写 `web/`）已明示。
不判 PASS 的原因是 5 项治理债（TODO），全部为文档/口径层面，不涉及产品行为：

- **T-A1（MINOR）**：门禁清单口径四份互不相同（见 D 项），后续实例无法机械确定「M0-01 的门禁集合」。
- **T-A2（MINOR）**：`evidence/M0/summaries/M0-01.md` 含多处**未标时点**的历史值，会被后续实例误读为现值：
  `pytest -q（8 passed）`（现 38）、`openapi.json 430KB`（现活契约 443552B；430624B 是 v1.0.0 基线）、
  `fc-list :lang=zh 有 7 条 … 无 Noto Sans CJK（BLK-02 仍在）`（现 37 条、Noto 命中 10 条、BLK-02 已关闭）、
  `test_contract_slice.py 8 例`（现 22 例）。必须逐条加「M0-01 时点值」标注或改为指向 `state.json.counts`。
- **T-A3（MINOR）**：`evidence/M0/M0-01/orchestrator-verification.md:14` 记 `PASS=15 WARN=2`，未注明该 2 条 WARN
  在**当时**（字体未装、BLK-02 开启）属真阳性，而 2026-11-12 22:47 字体安装后同一 WARN 属 D-007 假阳性。
  缺时点注解会让读者以为 doctor 一直在报警。
- **T-A4（MINOR）**：`resume.self_check_gates_rc0.gates[*].measured_at` 16 项全为 `2026-11-12T22:48:36`，
  但同键 `note` 记录了 23:30:05 与 00:42:29 两次重测且计数已变（39→46→53）。逐项时间戳未随重测更新，
  违反手册 15.4「分母必须可复现」的时点可追溯要求。
- **T-A5（流程）**：G11/G13 与 doctor 完整变体在 M0 收口前必须由 Q 在**静态树**（无并发 lane）上复跑一次全 16 项，
  本轮因禁令只做到 11 项复跑 + 5 项引用。
---

## B · D-001 … D-009 逐个判定

| 缺陷 | 严重度（单内自述） | 本档判定 | 依据（命令+rc / 文件+行号） |
|---|---|---|---|
| **D-001** 切片 `--tables` 静默 NOT_FOUND | MAJOR | **CLOSED** | `--tables workspaces` rc=0 且输出真 DDL（首行 `CREATE TABLE workspaces (`、尾行 `) STRICT;`，无 `NOT_FOUND`）；`--all-tables` rc=0，ddl 键 34 = 28 表 + 6 索引组，`NOT_FOUND` 值 0 个，28 块全部 `CREATE TABLE` 开头 `STRICT;` 收尾；`grep -c "CREATE TABLE" contracts/sqlite-v1.sql` = 28；`--tables no_such_table` **rc=2** 且不写产物（`ls` rc=2）；`tests/unit/test_contract_slice.py` **22 passed**。见 `judge/b1-…log` |
| **D-002** 前端基线无机读校验 | MINOR | **CLOSED**（附 1 条文档更正） | `python3 scripts/check_frontend_baseline.py` rc=0、`FRONTEND BASELINE PASS 8/8`（4 项哈希与字节逐项一致，`baseline_files=45 manifest_rows=8`）；`tests/unit/test_frontend_baseline.py` 6 例在场；篡改负例**引用** `run-04/commands.md:26`（`G4c … rc=1 expected=1 PASS`）与 `state.json.resume.self_check_gates_rc0.gates.G4c_frontend_tamper_negative.note`（本轮真实执行：备份→追加换行→rc=1→还原→`git status spec/` 空），本档未复跑（禁改 `spec/`）。**更正项**：`orchestrator/defects/D-002.md:23` 仍写 `qa/verify_package.py`，该路径在仓库根**不存在**（`ls` rc=2），实测可运行路径为 `spec/CampaignLab-SDD-v1.0/qa/verify_package.py`（rc=0） |
| **D-003** 证据日志被 `.gitignore` 吞 | MINOR | **CLOSED**（验证方法学需更正） | `.gitignore:15 *.log` + `:18 !evidence/**/*.log` 在场；5 个历史证据日志均 `tracked=yes`；**权威判据**：本档新写的 12 个 `judge/*.log`（未跟踪）全部出现在 `git ls-files --others --exclude-standard evidence/M0/Q-VERIFY-M0-01/judge/`（rc=0），且 `git check-ignore`（**不带 -v**）rc=1 → 否定规则对新文件确实生效；反向对照 `./tmp_probe.log` 命中 `.gitignore:15 *.log`（rc=0，已即时删除）。`git ls-files evidence` = 27。**方法学更正**：`D-003.md` 验证段与 `collect/04-defects.md` 用的 `git check-ignore -v` 对**已跟踪**文件恒 rc=1（索引短路），是恒真断言，不能证明规则生效；手册 15.4 本身已写明该陷阱，缺陷单应改用 `ls-files --others` 判据。见 `judge/b2-…log` |
| **D-004** 切片源钉死基线 + 版本硬编码 | MAJOR | **CLOSED** | 两切片 `spec_version=1.0.1`、`source.openapi.sha16=01bd28f0772f506e`、`bytes=443552`、`live_contracts=contracts`，与本档对 `contracts/openapi.json` 的**独立实算**逐字相同；`--ops noSuchOp` rc=2 且无产物；两份切片用相同参数**重切后 `diff -q` rc=0**（字节级可再生）；`pytest -k live_contract` 1 passed；`scripts/contract_slice.py` 内无版本回退常量（`1.0.1` 只出现在 `DELTA` 目录名与文档串，版本经 `live_spec_version()` 动态读取）。见 `judge/b1-…log`、`judge/i1-…log` §I-8 |
| **D-005** AC-MR 不可解析 | MAJOR | **CLOSED** | 程序化统计：基线 `grep -c '^| AC-'` = **35**，月报 `grep -cE '^\|[[:space:]]*AC-MR-'` = **12**，合计 **47**（与 `counts.acceptance_denominator=47`、`acceptance_resolvable=47` 一致）；`--ac AC-MR-99` **rc=2** 且无产物；`--ops getHealth --ac AC-001,AC-MR-01` rc=0 且 `acceptance_rows=['AC-001','AC-MR-01']`；`pytest -k all_47_acceptance_ids_resolve` 1 passed；原文锚点 `83.33%`（AC-MR-05）与 `79.31%`（AC-MR-08）各命中 1 次。见 `judge/b1-…log`、`judge/f1-ac-transcription-audit.log` |
| **D-006** ruff format 分母口径 | MINOR | **CLOSED**（缺陷单内数字已过期，需加时点注） | 6d9f1b2 实测：`ruff format --check .` = **51**，`git ls-files` 口径 tracked=51（py 7 + md 44）、untracked 未忽略=0 → **恒等式 51=51+0 TRUE**；b1f38a9 复测：**53** = tracked 53（py 8 + md 45）+ 0，与更新后的 `counts.ruff_formatted_files=53` 及 `composition.identity` 一致；两条复现命令逐字可跑；手册 15.4 已含「分母必须写明构成与可复跑命令（依 D-006）」条款。**过期项**：`D-006.md:41-46` 仍写「改为实测 37」「以 `ruff_lint_scope_files=6` 为 Python 分母」，现值为 53 / 8（`state.json` 已更新，缺陷单未加时点注）。见 `judge/i1-…log`、`judge/i2-…log` |
| **D-007** doctor SIGPIPE 假 WARN | MAJOR | **CLOSED**（独立复核见 C 项） | `scripts/doctor.sh:249` 现为 `NOTO_CNT="$(fc-list 2>/dev/null | grep -ci "noto sans cjk")"`；3 次运行摘要逐字一致 rc=0；`grep -ci` 20/20 rc=0 且命中数恒为 10；原写法 `grep -qi` 20 次中 **15 次 rc=141**、5 次 rc=0；不带 pipefail 的对照 20/20 rc=0；`tests/unit/test_doctor_determinism.py` **4 passed** |
| **D-008** 任务卡 AC 抄错 + scope_allow 缺项 | MAJOR | **CLOSED（自身两条缺陷已修）+ 必须跟进 2 项** | ① `orchestrator/tasks/M0-02.md:13-14` 的 AC-034/AC-035 与 `spec/…/ACCEPTANCE.md:42-43` 原文一致（机械比对的卡内独有 token 只剩「已按/spec/原文/修正/见文末/裁定/Q1」等元话语，无语义偏差，覆盖率 0.73/0.70）；`state.json.tasks.M0-02.gates[].authoritative` 亦与 spec 原文一致并标注第 42/43 行。② `M0-02.md:18` 的 `scope_allow` 已含 `pyproject.toml`、`uv.lock`、`evidence/M0/M0-02/**`、`evidence/M0/summaries/M0-02.md`，`state.json.tasks.M0-02.scope` 同步含此四项。③ `git status --porcelain spec/` 空。**跟进 1（MAJOR）**：同类错误仍在 `M0-03.md:12` 与 `:38`（见 F 项）。**跟进 2（MINOR）**：`D-008.md:57` 称「`orchestrator/tasks/*.md`（29 张卡）」，磁盘实测只有 **4** 张；29 是 `state.json.tasks` 的**任务键数**，其中 25 个尚无卡文件。以此为准建工具会立刻触发假分母失败 |
| **D-009** 账本写入静默跳过 | MAJOR | **CLOSED** | 账本回读：`defects = D-001…D-009`（9 条，无缺号、无重复）、`change_requests = CR-001, CR-002`；`uv run --no-sync pytest -q tests/unit/test_state_ledger.py -v` → **6 passed**，rc=0（双向守护 + 分母断言 + 状态取值集合）；磁盘 `orchestrator/defects/` 恰为 D-001…D-009 九个文件（账本↔磁盘双向一致）；手册 15.3 已增补「账本写入必须回读断言；禁止用 `isinstance` 之类守卫静默跳过」（`docs/delivery/LONG-HORIZON-ORCHESTRATION.md:596-598`）；`git status --porcelain spec/` 空。见 `judge/g1-cr002-facts-and-d009.log` §5 |

> 说明：D-001…D-009 在账本中的 `status` 目前均为 `FIXED_PENDING_Q`。本判定即手册要求的 Q 交叉验证，
> 建议编排器据本报告把 9 条一并置 `CLOSED`，并为 D-002/D-003/D-006/D-008 各挂上表中列出的「文档更正/跟进」子项。
---

## C · D-007 修复的独立复核（MAJOR，编排器曾误判一次）

### C.1 `bash scripts/doctor.sh` 连跑 3 次

命令：`DOCTOR_SKIP_VERIFY=1 bash scripts/doctor.sh`（3 次，23:55:08 / :09 / :10，HEAD=6d9f1b2）
**为何用 SKIP_VERIFY 变体**：完整变体第 7 节会执行 `scripts/verify.sh`，而 `verify.sh:19` 是
`node campaignlab-review-work/verify.mjs` —— 判定档被明令禁止运行 node（并发 lane 正在改 `web/`）。
`DOCTOR_SKIP_VERIFY=1` 产生的 WARN 属手册 15.8 与 NOTE-07 明列的**预期 WARN**，不据此判 FAIL。

| 次 | rc | 摘要（逐字） | RESULT | WARN 文本（全部列出） |
|---|---|---|---|---|
| 1 | 0 | `PASS=14  WARN=2  FAIL=0` | `HEALTHY` | ①「工作树存在 1 项未提交改动」（= 本档 `judge/` 目录）②「DOCTOR_SKIP_VERIFY=1，已跳过原型基线复跑」 |
| 2 | 0 | `PASS=14  WARN=2  FAIL=0` | `HEALTHY` | 同上（第 8、57 行，行号亦相同） |
| 3 | 0 | `PASS=14  WARN=2  FAIL=0` | `HEALTHY` | 同上 |

- **摘要逐字一致：成立**（3 次 `PASS/WARN/FAIL` 字符串完全相同，rc 恒 0）→ 手册 15.8 的 N≥3 确定性要求满足。
- **附带观察（NIT，非缺陷）**：整份输出除首行时间戳外，仅**第 43 行**不同——`up to date in 470ms / 412ms / 396ms`，
  即 §5 把 `npm ci --dry-run` 的**耗时回显**原样贴进日志。它是信息行（`info`，不计入 PASS/WARN），不影响门禁判定，
  但使「doctor 输出可字节级复现」这一更强主张不成立。若日后要把 doctor 输出做字节级 diff，必须先归一化该行。
  证据：`judge/c3-doctor-line43-nondeterminism.log`。
- **计数语义核实**（用于判定「预期 16/0」是否可达）：`doctor.sh:38-41` 定义 `ok→PASS+1`、`warn→WARN+1`、
  `bad→FAIL+1`、`info→不计数`；字体命中走的是 `info`（`:250`），故**不存在 PASS=17**。
  推算：本次 14 PASS + 脏树 WARN + skip WARN → 脏树转 `ok` = 15 → verify.sh 转 `ok` = **16 PASS / 0 WARN**，
  与 `run-04/commands.md` 第 7 节在干净树上的实测 `PASS=16 WARN=0 FAIL=0` 吻合。
  **据此更正 `collect/01-m0-01-gates.md` §3 末段「修复后应为 PASS=17」——那是把 info 行误计为 PASS 的算术错误。**
  证据：`judge/c4-doctor-counting-semantics.log`。
- 本档**未**复跑完整变体（node 禁令）；其 rc=0 引用 `collect/raw/a1-gates.log` G8 与 `run-04` 第 7 节。

### C.2 `fc-list` 双变体各 20 次（`bash -c` 内 `set -uo pipefail`）

| 写法 | rc 分布（20 次） | 结论 |
|---|---|---|
| **修复后**：`fc-list 2>/dev/null \| grep -ci "noto sans cjk"` | `rc=0` × **20** | 无抖动 |
| 同上，取命中条数 | `10` × **20**（唯一值） | 与 `test_noto_detection_is_stable_over_20_samples` 的断言一致 |
| **原缺陷写法**：`fc-list 2>/dev/null \| grep -qi "noto sans cjk"` | `rc=141` × **15**、`rc=0` × **5** | **缺陷成立**：假 WARN 率 75%（本档 20 次样本）；D-007 记 93%（30 次样本 28 次 141）。两者同向，均远超可接受抖动 |
| 对照：原写法但**不带** `pipefail`（仅 `set -u`） | `rc=0` × **20** | 证实根因是 `pipefail` 传播 SIGPIPE(141)，而非字体缺失 |

前提事实（独立实测）：`fc-list | wc -c` = **18876** 字节（> 管道缓冲，故 `grep -q` 提前退出会触发 SIGPIPE）；
`fc-list | grep -ci "noto sans cjk"` = **10**；`dpkg-query -W -f='${Status}' fonts-noto-cjk` = `install ok installed`。
→ **字体确已安装，BLK-02 的关闭结论不受 D-007 影响**（此前 WARN 是工具假阴性）。证据：`judge/c2-…log`。

### C.3 确定性回归单测

`uv run --no-sync pytest -q tests/unit/test_doctor_determinism.py -v` → **4 passed**，rc=0（`collected 4 items`）。
四条不变量与 D-007 §6 的自述逐条对应（反模式静态扫描含分母断言、`grep -ci` 定点、3 次摘要一致、20 次采样唯一）。
静态扫描口径实测有效且无误报：`scripts/doctor.sh:101` 的 `grep -q "^DOCTOR_JSON_OK=True$" "$TMPD/py"` 作用于**文件**而非管道，
不属反模式（正则要求 `|` 前缀）。

### C.4 WARN 文本语义判定（NOTE-07 / 手册 15.8）

3 次运行共 2 条 WARN，**两类都属预期**，不得据此判 FAIL：
①「工作树存在 N 项未提交改动」——本档 `judge/` 产物造成（跑前 `git status --porcelain` 只有这一项）；
②「DOCTOR_SKIP_VERIFY=1，已跳过原型基线复跑」——本档为遵守 node 禁令主动设置。
判定 G14 时**必须读 WARN 文本**而非计数；本轮无任何指向真实环境问题的 WARN。

### C.5 判定

**D-007 CLOSED，修复成立**（MAJOR 缺陷已消除，回归测试有效；编排器此前的误判已在 `run-04` 第 8 节留痕更正，
本档独立复现支持其更正结论）。附 2 条不需要立单的更正：doctor 第 43 行耗时回显的非确定性（NIT）、
`collect/01` §3 的「PASS=17」算术误判（应为 16）。

---

## D · A1 文档不一致的严重度裁定

### D.1 实测：同一任务存在**四份**互不相同的门禁清单

| 来源 | 条数 | 成员（按原文） |
|---|---|---|
| `orchestrator/state.json → tasks.M0-01.gates` | **9** | `uv lock --check`、`uv sync --locked`、`npm ci`、`npm run build`、`doctor HEALTHY`、`prototype baseline(verify.sh)`、`python quality gates`（**把 ruff check / ruff format --check / mypy / pytest 四条塞进 1 条**）、`cp314 wheels`、`contract slice tool D-001 fix` |
| `evidence/M0/summaries/M0-01.md:6-8` | **9** | `uv lock --check`、`uv sync --locked`、`ruff check .`、`ruff format --check .`、`mypy`、`pytest -q`、`npm run build`、`doctor.sh`、`verify.sh` |
| `evidence/M0/M0-01/orchestrator-verification.md:5-14` | **8** | 锁一致性、依赖同步、**前端锁 `npm ci`**、前端构建、Python 质量门（**只有 `ruff check .`**）、**运行可用性 `import fastapi/…`**、原型基线、环境诊断 |
| `orchestrator/tasks/M0-01.md` `gates:` | **4** | `uv sync --locked`、`npm ci`、环境取证、锁文件入库 |

差集明细（以 summaries 的 9 条为基准）：
- verification **多**出：`npm ci`（前端锁）、`import fastapi/duckdb/…`（运行可用性）；
- verification **缺**：`ruff format --check .`、`mypy`、`pytest -q`（三条被并入「Python 质量门」一行，且命令原文只写了 `ruff check .`）；
- state.json **多**出：`cp314 wheels`、`contract slice tool D-001 fix`（两条不是可执行命令，`cmd` 字段写的是描述文字）；
- state.json **把 4 条 Python 门禁折叠成 1 条**，导致「九项」在两份文档里指代不同集合；
- 另有第 5 份口径：`resume.self_check_gates_rc0.gates` 的 **16 项 G 编号**（G1…G14，含 G4b/G4c），
  这是唯一带 `{cmd, rc, expected, measured_at}` 结构的机读清单。

### D.2 裁定：谁为准

**以 `orchestrator/state.json → resume.self_check_gates_rc0.gates`（16 项 G 编号）为唯一权威门禁登记表**，理由：
① 机读、含 `cmd`/`rc`/`expected`/`measured_at`/`evidence`，可被脚本逐条复跑（手册 15.3 明确规定其形态）；
② 编排器独占写，不会被多 lane 并发污染；③ 覆盖另外三份清单的全部成员（G1/G2 基线、G3 前端基线、
G4/G4b/G4c 负例、G5/G6 契约、G7–G10 Python 四门、G11 verify、G12 package、G13 npm ci+build、G14 doctor）。
`tasks.M0-01.gates` 降级为**任务级交付门**（4 条口径），`summaries/M0-01.md` 与 `orchestrator-verification.md`
降级为**叙述性快照**，两者必须显式写明「本表为时点快照，权威门禁见 `resume.self_check_gates_rc0`」并给出 G 编号映射。

### D.3 严重度与必须修复项

**严重度：MINOR**（治理/可追溯；不影响任何门禁的实际 rc，也不影响产品行为）。
但必须修：本轮取证档正是因此被迫自行重建清单（`collect/01` §1 花了一整节做口径考古），
下一个接管实例会重复付出同样成本，且存在「按 4 条任务卡口径判定 M0-01 通过」的误判风险。

必须修复项（建议立**一张** MINOR 缺陷单，编号由编排器分配，本报告暂记 **Q-N1**）：
1. 在 `summaries/M0-01.md` 与 `orchestrator-verification.md` 顶部各加一行权威指向 + G 编号映射表（8/9 行 → G7…G14）。
2. `tasks.M0-01.gates` 的 4 条与 16 项 G 的对应关系写进 `state.json`（例如 `gates[].self_check_ids`），消除「九项」歧义。
3. `tasks.M0-01.gates` 里 `cp314 wheels` 与 `contract slice tool D-001 fix` 两条的 `cmd` 字段目前是**描述文字**不是命令，
   必须换成可复跑命令原文（本档已给出并实跑通过：
   `uv run --no-sync python -c "import duckdb,pydantic_core,fastapi,sqlalchemy,alembic,uvicorn; …"`；
   `python3 scripts/contract_slice.py --all-tables --out /tmp/x.json`）——否则违反手册 15.4「每个结论都要能被一条命令复现」。
4. 手册 15.3 增补一句：**同一任务不得存在两份以上门禁清单**；叙述性文档只能引用 G 编号，不得另立集合。
---

## E · A3 三条措辞级不一致的严重度裁定

### E.① `CHANGES.json` 未保留 CR-001 的 4 处「（可选）」语义 → **MINOR，判定为不需要改文件**

实测：`contracts/CHANGES.json` 顶层键 `schema/note/baseline/live/entries`；`entries` 12 条，字段集合固定为
`{file, pointer, kind, source, cr, adr, delta_tool_state}`，**无任何表达可选性/required 的字段**；
CR-001 影响面表（`:24`、`:25`、`:33`、`:34`）有 4 处 `ADD（可选）`。
裁定理由：① 「未进 `required`」是**可从契约机械验证的事实**，不是需要登记的元数据——本档独立复算：
`ReviewCreate.required=['scope']`（1 项，不含 `profile`）、`Review.required` 17 项不含 `monthly_review`、
两份 SourceMetadata `required` 各 9 项不含 `monthly_review`（`judge/e2-…log` §1-3），`CR-001.md:37-38` 的数字逐字正确；
② 往 `CHANGES.json` 加一个**没有门禁校验**的 `optional` 字段，等于制造一条无人守的自述，
反而违反手册 15.4（任何声明必须可复现）。`scripts/check_contracts.py:120` 只强校验
`(file, pointer, kind, cr, adr)` 五个字段，加字段不会红，但也不会被任何人验。
**建议（可选强化，不是必须）**：若要机读化，正确做法是把断言写进门禁而不是加字段——
在 `check_contracts.py` 增一条：凡 `kind=added` 且 pointer 形如 `.../properties/<name>` 的登记项，
断言 `<name>` **不在**其父 schema 的 `required` 数组内（除非登记项显式标 `required_touched=true`）。
这样「可选」从措辞升级为可红可绿的门禁。

### E.② CR-001 说「三个新增属性」，按 pointer 口径实为 4 个 → **MINOR，必须改文件**

实测三种口径：
- 含 `/properties/` 的登记项 = **4**（`Review/properties/monthly_review`、`ReviewCreate/properties/profile`、
  `source-json.schema.json /$defs/SourceMetadata/properties/monthly_review`、`source-metadata.schema.json /properties/monthly_review`）；
- 按**属性名**去重 = **2**（`monthly_review`、`profile`）；
- 按**逻辑属性**（把两份 SourceMetadata 视作同一逻辑定义的两次落地）= **3** ← 这是 CR-001「三个」的唯一可能来源，但 CR 未写明口径；
- 另有 7 条是 schema 级整块新增（`MonthlyCapacity/Comparison/OriginOverlap/Participation/Production/Review/Trend`），不属「属性」。

裁定：**MINOR，必须改**。理由是这句话是**兼容性结论的计数依据**（「三个新增属性均未进入任何 required」），
计数口径不明会让复核者按 4 去找第 4 个属性、或按 2 去质疑漏了一个。实质结论（向后兼容）本档已独立验证成立，
故不升级为 MAJOR。建议改法（`orchestrator/change-requests/CR-001.md:37`）：

> 「本次新增 **4 个属性 pointer / 3 个逻辑属性**（`ReviewCreate.profile`、`Review.monthly_review`、
> `SourceMetadata.monthly_review`〔在 `source-json.schema.json` 与 `source-metadata.schema.json` 各落地一处〕），
> **均未进入任何 `required` 数组**：实测 `ReviewCreate.required=['scope']`；`Review.required` 17 项不含 `monthly_review`；
> 两份 SourceMetadata 的 `required` 各 9 项不含 `monthly_review`。」

### E.③ ADR-004 不枚举 12 节点，仅作机制引用 → **非缺陷（NIT），不改文件**

实测 `docs/decisions/ADR-004-monthly-review-delta-v1.0.1.md:20-21` 写的是机制（「全部差异登记 `contracts/CHANGES.json`，
新增 CI 门禁 `check_contracts.py check` 强制『实测结构差异 ⇄ 登记项』一一对应」），不复述节点清单。
裁定：这是**正确的单一真值设计**——12 节点若在 ADR 里再抄一遍，就出现第二份可漂移副本；
ADR 里所有可交叉的数字（`22 个文件`、`DELTA-SHA256SUMS 21 项`、`11 ADD + 1 UPDATE`、`35 → 47`、`info.version=1.0.1`）
本档均已独立核实一致（`judge/e1-…log`、`judge/g1-…log`）。**无需修改。**
唯一可选改进（NIT）：在 `ADR-004:20` 后加一句指针「12 个节点的权威清单见 `contracts/CHANGES.json.entries`（本 ADR 不复制）」，
让读者不必猜「为什么 ADR 里没有清单」。

---

## F · 全量核对任务卡的 AC 转述（受托的回归防护）

机械化比对脚本：`/tmp/q_ac_compare.py`（**只存 /tmp，未写进仓库**），输出全表已抄入
`evidence/M0/Q-VERIFY-M0-01/judge/f1-ac-transcription-audit.log`。
比对口径：卡内每一处 `AC-(MR-)?\d+` 引用 → 权威行（`spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md` ∪
`spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/qa/CampaignLab-Review-Acceptance-Checklist.append.md`，
即 `scripts/contract_slice.py:48-51` 的 `ACCEPTANCE_SOURCES`）→ 输出双方原文 + 二元中文/ASCII token 覆盖率 + 卡内独有 token。

### F.1 分母断言（程序化）

| 断言 | 实测 | 判定 |
|---|---|---|
| 权威 AC 总数 == 47 | 基线 **35**（AC-001…AC-035，无缺号）+ 月报 **12**（AC-MR-01…AC-MR-12，无缺号）= **47**，两表 id 交集为空 | **成立** |
| 只数 `spec/…/qa/ACCEPTANCE.md` 一张表 == 47？ | **35** | **不成立**：47 必须由**两个来源**相加。任何后续工具（含 D-008 §5 计划的 `check_task_cards.py`）若只读 ACCEPTANCE.md 会立刻假红。旁证：`verify_package.py` 报的是「35 个验收用例」（另一对象：基线包内核验），不得与 47 混用 |
| `orchestrator/tasks/*.md` == 29 张卡？ | **4 张**（`M0-01.md`、`M0-02.md`、`M0-03.md`、`M0-P01.md`） | **分母异常**：29 是 `state.json.tasks` 的任务键数（`M0-01…M5-P01`），其中 **25 个任务尚无卡文件**（`M0-03b、M0-04、M1-01…M5-P01`）。`D-008.md:57`「本轮先由 Q 判定档人工全量核对 `orchestrator/tasks/*.md`（29 张卡）」的口径错误 |

**对 25 个未建卡任务的补偿核对**（本档主动做，避免「只核 4 张」留盲区）：扫描 `state.json` 全部 29 个任务的
AC 引用（`judge/f1-…log` 末段），25 个任务含 AC 引用、4 个不含；**所有被引用的 id 均落在权威 47 条内**
（`AC-001…AC-035`、`AC-MR-01…AC-MR-12`，无 `AC-036`、无 `AC-MR-13` 之类越界 id）。
`state.json.tasks.M0-02.gates[].authoritative` 的两条转写文本与 `ACCEPTANCE.md:42/43` 原文一致（含行号标注），
说明账本侧的转述纪律有效；**风险只在卡片散文里**。

### F.2 逐卡比对结果（14 处引用，去重按「行×id」）

| 卡:行 | AC | 卡内文本要点 | 权威行要点 | 覆盖率 | 判定 |
|---|---|---|---|---|---|
| `M0-01.md` | — | 无 AC 引用 | — | — | 不适用 |
| `M0-P01.md` | — | 无 AC 引用（gates 是命令级） | — | — | 不适用 |
| `M0-02.md:7` | AC-001 | 「切片含 AC-001/034/035 原文行」 | — | 0.14 | **纯指针引用，非转述** → 合规 |
| `M0-02.md:12` | AC-001 | 会话令牌仅首次可用、重复换取拒绝、工作区切换保留各自数据、worker 状态在 health 中可见 | `ACCEPTANCE.md:9`：启动本机模式换取一次性会话、正常会话进入、重复令牌拒绝、工作区切换保留各自数据、worker 状态可见 | 0.65 | **一致**（语义逐项对应）。NIT：「在 health 中可见」是实现落点补充，权威行未指定位置；建议写成「worker 状态可见（M0-02 落点：`getHealth.worker`）」 |
| `M0-02.md:13` | AC-034 | 过期会话、错误 Host/Origin、跨工作区 ID、上传失败 → 401/403/404/413 或 422；隔离、路径、日志与 ETag 证据可查（HTTP 负例） | `ACCEPTANCE.md:42` 同 | **0.73** | **D-008 修复正确**：独有 token 只剩「已按/spec/原文/修正/见文末/裁定/Q1」等元话语，无语义偏差 |
| `M0-02.md:14` | AC-035 | 按 M0 锁版本、迁移、核对包与 API → verify_package.py、DDL 等价、OpenAPI 请求响应及前端生成类型通过；锁与运行环境清楚 | `ACCEPTANCE.md:43` 同 | **0.70** | **D-008 修复正确**（同上） |
| `M0-02.md:32`、`:36`、`:76`、`:79` | AC-001/034/035 | 档位表与裁定记录里的**指针式引用** | — | 0.09–0.15 | **非转述**，低覆盖率属正常 → 合规（工具化时必须豁免此类行，否则 D-008 §5 的「重合度为 0 即 rc=1」规则会把裁定记录本身判红） |
| **`M0-03.md:12`** | **AC-034** | 「**AC-034**：深链、刷新、返回、切工作区、404、过期会话均回到合法入口；切工作区清理临时查询、轮询与失效选择」 | `ACCEPTANCE.md:42`：过期会话、错误 Host/Origin、跨工作区 ID、上传失败 → **401/403/404/413 或 422**；主证据 **HTTP 负例** | **0.29** | **不一致（MAJOR，同类错误未修净）**：① 权威 AC-034 里**没有**「深链/刷新/返回/切工作区/回到合法入口」；② 通过条件被换成「回到合法入口」，丢掉 401/403/413/422 与 Host/Origin、上传失败；③ 主证据是 HTTP 负例，不是页面走查。**同卡 `:68-74` 的加注已写明 AC-034 权威口径是 HTTP 负例**，于是同一文件自相矛盾：加注说 A，gate 行仍写 B |
| **`M0-03.md:38`** | **AC-001 / AC-034** | 「S8 vitest 单测脚手架与 **AC-001 / AC-034 页面侧断言**」 | 同上 | 0.10 | **不一致（同源）**：把「页面侧断言」直接挂到 AC-034 名下。S8 是 flash 档，会照此写 `web/tests/**` 断言并判 PASS |
| `M0-03.md:11` | AC-001 | 「AC-001 **页面侧**：入口换取会话、工作区列表与新建、两条首跑路线；无工作区时突出创建」 | `ACCEPTANCE.md:9` | 0.26 | **可接受**：显式标注「页面侧」＝范围切分而非转述；「两条首跑路线」有权威出处（`ACCEPTANCE.md:47`「浏览器至少覆盖两条逐步走查(WORKFLOWS.md)」）。NIT：建议补注出处行号 |
| `M0-03.md:71` | AC-034 | 加注内**引用 spec 第 42 行原文**解释误挂 | 同行 | 0.10 | **一致**（修正性说明，非转述） |

### F.3 判定与必须修复项

**判定：FAIL（存在 1 处 MAJOR 未修的同类转述错误 + 1 处分母口径错误）。**
D-008 对 M0-02 的修复**正确且到位**，但同类错误在 **M0-03 卡内仍存在**：D-008 的修复动作 4 只给 M0-03 **加了注**（`:68-74`），
没有修 `:12` 的 gate 行与 `:38` 的档位表行，导致同一张卡自相矛盾。
危害与 D-008 完全同类：S8（flash）会按「深链/刷新＝AC-034」写 vitest 断言，
S9 会在 `evidence/M0/M0-03/ac.md` 里对 AC-034 判 PASS，而权威 AC-034 的 HTTP 负例（401/403/413/422、Host/Origin、上传失败）
在 M0-03 侧无人取证——M0-02 侧又已按裁定 Q2/Q3 把部分 HTTP 端到端 `deferred_to` 后续任务，
两边一让，**AC-034 存在整条漏检的可能**（而 gate 还会绿）。

必须修复项（建议立**一张 MAJOR 缺陷单**，暂记 **Q-N2**；派 M0-03 的 S6/S8/S9 之前必须完成）：
1. `orchestrator/tasks/M0-03.md:12` 改为（示例措辞）：
   `- UI-01 页面侧（**非 AC-034**）：深链、刷新、返回、切工作区、404、过期会话均回到合法入口；切工作区清理临时查询、轮询与失效选择。权威 AC-034（spec ACCEPTANCE.md:42）的 HTTP 负例归 M0-02；本卡只负责其前端表现与 403/404「不可见即不可见」语义一致`
2. `orchestrator/tasks/M0-03.md:38` 的 S8 产出改为「AC-001 页面侧断言 + UI-01 深链/刷新断言（**不得命名为 AC-034**）」。
3. `M0-03.slice.json` 实测不含 `acceptance_rows`（`operations=5`、`pages={UI-01}`），
   即 M0-03 的上下文包里**没有 AC 原文**——这正是卡内散文被当成权威的原因。建议重切时带上
   `--ac AC-001,AC-034`（原文行入包，杜绝转述），或在卡内直接粘 `ACCEPTANCE.md:9/42` 两行原文。
4. `orchestrator/defects/D-008.md:57` 的「29 张卡」改为「`orchestrator/tasks/*.md` 现存 4 张（`state.json.tasks` 有 29 个任务键，其余 25 张卡尚未建）；
   工具化时**卡文件数不得作为分母**，分母只能是权威 AC 数 47（两个来源相加）」。
5. 工具化（D-008 §5 的 `scripts/check_task_cards.py`）落地时必须实现三条本档实测得出的约束：
   ① AC 权威源 = **两个文件**（复用 `contract_slice.ACCEPTANCE_SOURCES`，不要重写正则）；
   ② 必须区分**转述行**与**指针/元话语行**（本轮 14 处引用里有 7 处是后者），否则裁定记录本身会被判红；
   ③ 覆盖率阈值不能一刀切——实测合规转述 0.65–0.73、错误转述 0.29、纯指针 0.09–0.15，
   建议规则改为「**卡内出现权威行没有的关键实词**（如『深链』『刷新』『回到合法入口』）即 rc=1」，比「重合度为 0」灵敏得多
   （本轮 `M0-03.md:12` 的覆盖率是 0.29 而非 0，D-008 §5 原规则**抓不到它**）。
---

## G · ADR-005 与 CR-002 是否与 spec / 活契约冲突

### G.1 ADR-005 `urn:campaignlab:problem:<code>` 是否违反契约对 `Problem.type` 的约束 → **不违反**

定点提取（未整读 `contracts/openapi.json`，443552B；全部经 `python3` 按 JSON Pointer 取值）：

| 契约事实（本档实测） | 与 ADR-005 的关系 |
|---|---|
| `Problem.type` = `{type: string, minLength: 1, maxLength: 250}`，**无 `pattern`、无 `format`、无 `enum`** | URN 合法。长度核算：前缀 `urn:campaignlab:problem:` = 24 字符，`code` 受 `maxLength 96` 约束 → 最长 24+96 = **120 ≤ 250** ✓ |
| 全契约所有 schema 中，只有 `Problem.type` 一处对 `type` 施加长度约束，**无任何 `type` 的 pattern/enum** | 不存在「必须 https」的隐含约束；ADR-005 §3 否决 `https://…` 的理由（虚假可解析性）与契约不冲突 |
| `Problem` 全文不含 `urn`、不含 `http` 字样 | 契约确实**未规定**标识方案 → ADR-005 §1 的前提成立 |
| `Problem.required = [type, title, status, code, detail, request_id, issues]`（7 项全必填）、`additionalProperties=false` | **ADR-005 未提及、但实现必须遵守**：7 个字段一个都不能少，且不得加自定义字段 |
| `Problem.detail` = `{minLength: 1, maxLength: 500}` | **ADR-005 §2.2 只说「detail 才允许携带上下文」，未禁止空 `detail`**；契约要求 `minLength 1` → 必须补约束（见 G.3） |
| `Problem.code` / `request_id` = `pattern ^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$` | `code.lower()` 落在该字符集内 ✓；`request_id` 用 `uuid4().hex`（设计 §1 已写）✓ |
| `Problem.status` = `{integer, minimum 400, maximum 599}`；`issues` = `array of Issue, minItems 0, maxItems 1000`；`Issue.required=[code, location, message, severity]`、`additionalProperties=false`、`location maxLength 500`、`severity enum [ERROR,WARNING,INFO]` | CR-002 过渡实现的 `issues[0].location="/query/status"` **合法**（长度、类型均通过），但必须同时给出 `code`/`message`/`severity` 三个必填项——CR-002 §3 只写了 `location`，实现方若照抄会产出不合规的 Problem 体 |

### G.2 三个默认值是否与 `spec/CampaignLab-SDD-v1.0/architecture/OPERATIONS.md` 的 60s / 8 MiB / 64 MiB 冲突或被混用 → **不冲突，且未混用**

| OPERATIONS.md 原文（实测行号） | ADR-005 默认值 | 是否同一对象 | 裁定 |
|---|---|---|---|
| `:5`「令牌一次使用、**有效期 60 秒**、内存存放」（每次进程启动生成一次性入口令牌，换取会话） | `session_ttl_seconds = 3600` | **不同对象**：60s 是**一次性入口令牌**（`exchangeSession` 的 `token`），3600s 是换取后的**会话**存活期 | 不冲突。ADR-005 §2.3 已显式写「是两个不同对象…不得混用」；设计 §1 `exchangeSession` 的 401 条件写「超 60s」，两者分置正确。旁证：`OPERATIONS.md:5` 只说会话「随机会话标识只在当前进程有效」，未给会话 TTL → 3600 是**新决定**而非覆盖既有值 |
| `:11`「普通上传限制单文件 **64 MiB**，合成 v0.1 文件入口限 **8 MiB**」 | `MAX_JSON_BODY_BYTES = 1048576`（1 MiB，超限 413） | **不同对象**：1 MiB 只管 `application/json` 正文；8/64 MiB 管**文件上传** | 不冲突。本档独立验证「导入走文件通道」：`createImport`（`POST /workspaces/{id}/imports`）与 `attachImportFile` 的 requestBody `content-type` **只有 `multipart/form-data`**，`file` 为 `type:string, format:binary`；导入相关的 JSON 体只有 `configureImport`（`mapping`）与 `publishImport`（`validation_digest` ≤64、`note` ≤500）→ 都不可能是 8 MiB 级载荷。**结论：AC-005「合成 v0.1 文件大于 8 MiB 拒绝」与 AC-006「等价 SOURCE_JSON 导入」走文件口径，不会被 1 MiB JSON 上限误伤** |
| 契约无 `ttl` / `heartbeat` / `max_body` 字样（全契约关键字计数：`ttl`=0、`heartbeat`=0、`1048576`=0、`session_ttl`=0；`413`=161 处，`components.responses` 含 `Problem413`） | `WORKER_HEARTBEAT_TTL_SECONDS = 15` | 契约**未规定** → 属新决定 | 不冲突。落点存在：`Health.worker` = `enum [READY, OFFLINE]`、`Health.status` = `enum [READY, DEGRADED]`（5 字段全 required）→ 15s 心跳窗口可支撑 AC-001「worker 状态可见」的取证 |

### G.3 ADR-005 必须补的两条（否则 S3/S4 会踩）

1. **`detail` 不得为空**（契约 `minLength: 1`）：ADR-005 §2.2 只规定 `title` 用固定短句表、`detail` 携带上下文，
   未禁止空 `detail`。必须补一句「`detail` 至少 1 字符、至多 500 字符；无上下文时用固定兜底短句，禁止空串」。
2. **`Problem` 7 字段全必填 + `additionalProperties=false` + `issues[]` 内 4 字段全必填**：
   ADR-005 只谈 `type`/`title`/`detail`，未把「必填全集」写进冻结面。建议在 §2 增一张字段表（含 `status` 400–599、
   `request_id` pattern、`issues` 上限 1000），因为这是 M0-03b 之后要冻结的公共件，缺一条就会在 M1+ 各 lane 各写各的。
   严重度：**MINOR**（不阻塞 M0-02，但必须在 M0-03b 冻结前补齐）。

### G.4 CR-002 的事实是否成立 → **全部成立（本档独立核实，含只读基线，不采信转述）**

| CR-002 断言 | 本档实测 | 判定 |
|---|---|---|
| `listWorkspaces` 声明了 `status` 查询参数（1–60） | `paths./workspaces.get.parameters` = `[cursor, limit, q, status]`，`status` = `{in: query, required: false, schema:{type:string,minLength:1,maxLength:60}}` | **成立** |
| `Workspace` schema 无 `status` | properties = `[authorization_note, created_at, id, name, revision, source_class]`，required = 同 6 项，**无 status** | **成立** |
| `workspaces` 表无 `status` 列 | `contracts/sqlite-v1.sql`：`id, name, source_class, authorization_note, revision, created_at`（含 2 个 CHECK），**无 status** | **成立** |
| `status` 列存在于 `activities` 表，取值 `OPEN`/`ARCHIVED` | DDL 28 表中含状态类列者：`activities.status`、`preflight_rows.status`、`rule_versions/imports/cases/preflights/reports/actions/jobs.state`；`Activity.status` = `enum [OPEN, ARCHIVED]` | **成立** |
| `API.md` 只写「按对应对象状态白名单过滤」 | `spec/CampaignLab-SDD-v1.0/architecture/API.md:10`：「…`q` 对名称和公开编号按 NFKC casefold 查找，**`status` 按对应对象状态白名单过滤**」 | **成立** |
| §6.1：`status` 非 v1.0.1 增量引入；基线 `info.version=1.0.0`、`bytes=430624`、`sha16=3a5c6e3b8a0539cd`，且基线里 `status` schema 与活契约逐字相同 | 本档实算基线：`sha16=3a5c6e3b8a0539cd bytes=430624 info.version=1.0.0`；基线与活契约的 `listWorkspaces` 四个参数 JSON **逐字相同** | **成立** |
| §6.1：12 条登记项完全不涉及 `listWorkspaces`/`workspaces` | 对 `CHANGES.json.entries` 12 条做全文匹配，命中 **0** 条 | **成立** |

### G.5 编排器建议（并已被项目负责人裁定）的**选项 B** 是否合理 → **合理但不完整；影响面字段必须扩写**

本档独立发现的**同类缺口面**（对 17 个声明 `status` 查询参数的 list op 逐个解析其 200 分页体的 item schema）：

| 分类 | 数量 | operationId（资源 schema） |
|---|---|---|
| 资源有 `status` 字段 | **1** | `listActivities`（Activity） |
| 资源有 `state` 字段（**参数名与字段名不一致**） | **9** | `listRules`(RuleVersion)、`listImports`(Import)、`listCases`(Case)、`listRuns`(RunSummary)、`listCandidates`(Candidate)、`listPreflights`(Preflight)、`listReports`(ReportSummary)、`listActions`(Action)、`listJobs`(Job) |
| 资源只有其它状态类字段 | **1** | `listAudit`(AuditEvent.`outcome`) |
| **资源无任何状态字段（与 Workspace 同类缺口）** | **6** | `listWorkspaces`(Workspace)、`listSnapshots`(Snapshot)、`listDefinitions`(Definition)、`listThresholds`(ThresholdVersion)、`listEvidence`(Evidence)、`listExports`(Export) |

裁定：
- **选项 B 对 M0-02 是合理的最小修复**：不动 28 表参考 DDL、不动 `spec/` 基线与 SHA256SUMS，
  只改活契约一处 + 新建 ADR-006 登记，代价与风险都最低；选项 A 会破坏「首迁与 `sqlite-v1.sql` 结构等价」这条 gate。
  本档同意 `CR-002.md:39-46` 的代价评估。`CR-002.md:80-98` 的 8 步原子执行计划（含「pointer 必须用
  `check_contracts.py diff` 实测得到、不得手写猜测」「登记项与实测差异由 12 同时变 13」「重切并核对 sha16/bytes」）
  **符合手册 15.4 第 5/6 条，本档认可**。§6.2「`info.version` 保持 1.0.1 不 bump」的理由亦成立
  （版本基准已被 `M0-03.md:47` 与 `MONTHLY-DELTA-PLAN.md` 钉住，内容身份由 `sha16` 承载）。
- **但 B 不完整**：它只消掉 6 处同类缺口中的 1 处。执行后契约会变成「`listSnapshots`/`listDefinitions`/`listThresholds`/
  `listEvidence`/`listExports` 仍暴露无法实现的 `status` 参数，而 `listWorkspaces` 没有」——
  这本身是一种新的不一致，且 M2/M3/M4 的 lane 走到那 5 个 op 时会**各自发明**行为（有的 422、有的静默忽略），
  正是 ADR-005 要防的「冻结面被污染」。
- 另外 9 个 `state` 资源的**参数名/字段名错配**需要一条**一次性**的实现规则（`status` 查询参数 → 对象的 `state` 字段，
  白名单取自该对象的 enum），否则前端按 `status=OPEN` 发、后端按 `state` 存，会在 M2 起反复对不上。

必须修复项（**MINOR**，不阻塞 M0-02，但必须在 wave2 出口/公共件冻结前完成；建议写进 ADR-006 或另立 **CR-003**，暂记 **Q-N3**）：
1. `CR-002.md:7` 的「影响面」必须扩写为实测面：**17 个 op 声明 `status`；其中 6 个资源无任何状态字段、
   9 个资源字段名为 `state`、1 个为 `outcome`、只有 1 个真叫 `status`**，并写明本次只裁定 `listWorkspaces` 一处。
2. ADR-006 必须显式登记「剩余 5 处同类缺口（Snapshot/Definition/ThresholdVersion/Evidence/Export）」为待决项，
   给出统一处置规则（建议：一并移除，或统一 `status` → 对象状态字段的映射规则 + 白名单来源），
   并规定**在规则落地前，任何 lane 不得对这 5 个 op 自行发明 422/忽略行为**。
3. 过渡实现的 Problem 体必须补齐 `Issue` 的 4 个必填字段（见 G.1 末行），`CR-002.md:33-35` 的示例应改写完整。
4. 契约编辑与重切必须按 `CR-002.md:99-105` 的 HOLD 纪律执行：**本档（Q 判定档）已于 01:10 返回**，
   另一在飞实例（M0-03/S1+S2）返回后方可原子执行；执行后 `counts.live_openapi_sha16`、两份切片、
   以及所有以 `sha16=01bd28f0772f506e` 为基准的门禁文本（`M0-02.md:53-56`、`M0-03.md:50-52`、设计 §5 V1、设计头部）必须同批更新。
---

## H · M0-02/S1 设计文档（`orchestrator/handoff/M0-02-design.md`）的可执行性

| 检查项 | 实测 | 判定 |
|---|---|---|
| 行数 ≤120 | `wc -l` = **117** | **PASS** |
| 7 节是否齐 | `## 1 接口签名（5 个 operationId）`、`## 2 数据结构（字段级）`、`## 3 首迁边界`、`## 4 边界清单（AC→实现约束→已知失败模式）`、`## 5 验证清单（命令→期望 rc）`、`## 6 文件级 TODO 与白名单`、`## 7 未决问题` —— 7 节全在，另有 `## 8 本文件自检`（附加，不违规） | **PASS** |
| 5 个 operationId 与切片一致 | 设计 §1 五条签名 = `exchangeSession`、`getSession`、`getHealth`、`listWorkspaces`、`createWorkspace`；`M0-02.slice.json` 的 `operations` 键**恰为同 5 个**（`acceptance_rows=['AC-001','AC-034','AC-035']`、`spec_version=1.0.1`）；§6 还钉了「路由函数名 ↔ operation_id 逐字对应」表；文档内提及的其它 op（`getJob`/`listJobs`/`createRun`/`createReport`/`createExport`/`publishImport`/`validateImport`）都出现在 Q2/Q3 的「不在切片内」论证里，**不是交付范围** | **PASS** |
| 切片新鲜度 | 设计头部声明 `sha16=01bd28f0772f506e`/`bytes=443552`/`spec_version=1.0.1`，与本档对活契约的独立实算**逐字相同**（`judge/i1-…log` §I-8） | **PASS**（注：CR-002 选项 B 执行后此指纹会变，必须重切并更新设计头部与 §5 V1） |
| S3/S4/S5 白名单是否全落在修正后的 `scope_allow` 内 | 机械化判定（`judge/a2-…log` §5）：`src/campaignlab/**`（含 `__main__.py`、`cli.py`、`config.py`、`clock.py`、`domain/*`、`api/{app,common,deps,health,session,workspaces}.py`、`application/*`、`infra/db/*`）、`migrations/**`、`tests/api/**`、`tests/unit/**`、`tests/integration/bootstrap/**`、`evidence/M0/M0-02/**`（含 `gates/V1..V13.log`、`http/*.json`）、`evidence/M0/summaries/M0-02.md`、`pyproject.toml`、`uv.lock` —— **全部命中**卡内 `scope_allow`（`M0-02.md:18`）∪ `state.json.tasks.M0-02.scope`；§6 里出现的 `contracts/**`、`spec/**`、`scripts/**`、`web/**`、`orchestrator/**`、`tests/**`（对 S3）是**禁止触碰清单**，不是白名单，未构成越界 | **PASS** |
| 有没有把「未决问题」偷偷当成已决定 | §7 明列 Q1–Q8 且标题写明「不自行决定，交编排器／项目负责人裁定」；§1/§4/§6 中所有临时处置都带 Q 标记（如「白名单当前为空集，Q4」「`accepted_response()`…Q2」「`check_if_match()`…Q3」）；全文 `grep -nE "已裁定\|已决定\|已批准\|定稿\|裁定通过"` **零命中**（rc=1） | **PASS**（未偷渡；符合手册 6.4） |

**判定：PASS_WITH_TODO。** 设计本身可执行、边界清晰、未越权裁定；但**派 S3/S4/S5 之前必须打 3 处补丁**
（都是编排器裁定与后续提交把设计文本变成了过期指令，属 MINOR，建议合并立一张单，暂记 **Q-N4**）：

1. **§5 V11 的硬编码分母已错**：原文要求「`ruff format --check .` 计数须为 `40 files already formatted`（基线 39，+1）」。
   本档实测：6d9f1b2 为 **51**、b1f38a9 为 **53**（md 分母随文档提交增长，属 D-006 已认定的预期漂移）。
   S5 若照此执行会当场判红、或（更糟）为了对上数字去动无关文件。**必须改为**：
   「以 `state.json.resume.self_check_gates_rc0.counts.ruff_formatted_files` 为准，并断言恒等式
   `tracked_in_scope + untracked_not_ignored_in_scope == ruff_total`；禁止在设计/任务卡里硬编码该数字」。
2. **§5 V1–V13 全带 `PYTHONPATH=src` 前缀，与 Q7 裁定冲突**：`M0-02.md:71` 的裁定原文明确
   「gate 命令原文必须保持不带 `PYTHONPATH=src` 前缀（`uv run python -m campaignlab doctor`），设计 §5 的 PYTHONPATH 前缀仅为 S2 完成前的过渡」。
   设计文档本身没有回填这条裁定，S5 只读设计就会用错命令口径取证。**必须**在设计 §5 抬头加注
   「Q7 已裁定：S2 删除 `[tool.uv] package = false` 并重跑 `uv lock` 之后，V3–V13 一律去掉 `PYTHONPATH=src` 前缀」。
3. **§6 S5 行的 scope 陈述已过期**：原文写「`evidence/**` 未列入 `scope_allow` 但为任务卡 `outputs:` 指定落点（Q8）」，
   而 `M0-02.md:18` 已于 2026-11-12T23:41:32 把 `evidence/M0/M0-02/**` 与 `evidence/M0/summaries/M0-02.md` 写进 `scope_allow`。
   留着这句会让 S5 以为自己在越界（手册 6.4 要求越界即回报 → 可能白白停一轮）。**必须**改为「已列入 `scope_allow`（Q8 已裁定）」。

NIT（不必修）：§8 C2 记的 `48 files` 是当时值，属自检快照，可接受；
`state.json.tasks.M0-02.scope` 写 `tests/api/session/`（目录）而设计 §6 写 `tests/api/test_session.py`（文件），
两者都在 `tests/api/**` 内，不构成越界，但建议统一粒度以免 S4 犹豫。

---

## I · 分母核对

### I.1 `ruff format --check .` 报的 N vs `git ls-files` 口径

| 时点 | `ruff format --check .` 报的 N | tracked（作用域内 .py+.md，排除 spec/prototype/web） | untracked 未忽略（同口径） | 恒等式 | 与 `state.json.counts` |
|---|---|---|---|---|---|
| HEAD `6d9f1b2`（00:06） | **51**（rc=0） | **51**（py 7 + md 44；分目录：root 1、contracts 1、docs 9、evidence 17、orchestrator 16、scripts 3、src 1、tests 3） | **0** | **51 = 51 + 0 TRUE** | `ruff_formatted_files=51`、`composition={total:51, py:7, md:44}` → **一致** |
| HEAD `b1f38a9`（01:07，D-009 提交后复测） | **53**（rc=0） | **53**（py 8 + md 45） | **0** | **53 = 53 + 0 TRUE** | counts 已同步为 `53`、`composition={total:53, py:8, md:45}`、`identity` 串亦为 53 → **一致** |

- 复现命令（`composition.reproduce_py` / `reproduce_md`）逐字可跑，本档实跑结果与 counts 相同。
- 旁证差异已解释：`find` 口径（含被忽略文件）= **52**，比 git 口径多 1，即 `.pytest_cache/README.md`
  （pytest 自建、被 `.gitignore` 覆盖、ruff 不计数）→ 不构成口径冲突（与 `collect/04-defects.md` §D-006 的结论一致，本档独立复算）。
- **本档产物对分母的影响**：本报告 `qa-reports/m0/Q-VERIFY-M0-01.md` 是作用域内 `.md`，
  写入后 untracked 未忽略 +1 → ruff N 变为 **54**，恒等式仍应为 `53 + 1 == 54`（文末附录为实测值）。
  编排器在提交本报告后必须把 `counts.ruff_formatted_files` 与 `composition` 更新为提交后的实测值。

### I.2 pytest passed / mypy 源文件数 vs `state.json.counts`

| 指标 | 本档实测 | `state.json.counts` | 判定 |
|---|---|---|---|
| `pytest -q` passed | **32**（6d9f1b2）→ **38**（b1f38a9，新增 `tests/unit/test_state_ledger.py` 6 例） | 32 → **38**（同批更新） | **一致** |
| `mypy` 源文件 | **7**（6d9f1b2）→ **8**（b1f38a9） | 7 → **8** | **一致** |
| `ruff check . --show-files` 行数 | **8**（6d9f1b2） | `ruff_lint_scope_files = 7` | **表面不符，实为口径差**：`--show-files` 的输出**含 `pyproject.toml` 一行**（8 行 = 7 个 `.py` + 1 个配置文件）。纯 Python 分母 7 与 counts 一致；b1f38a9 时为 9 行 = 8 个 `.py` + 1，counts=8 亦一致。**建议**补一条复现命令：`uv run --no-sync ruff check . --show-files \| grep -c '\.py$'`，避免后人再用裸 `wc -l` 得到 8 而误报 |
| `acceptance_denominator` / `acceptance_resolvable` | **47 / 47**（F.1 程序化统计） | 47 / 47 | **一致** |
| `frontend_baseline_rows` | **8**（`FRONTEND BASELINE PASS 8/8`） | 8 | **一致** |
| `contract_registered_nodes` | **12**（`登记项=12 实测差异=12`） | 12 | **一致** |
| `live_openapi_sha16` / `live_openapi_info_version` | **01bd28f0772f506e / 1.0.1**（独立实算） | 同 | **一致** |

**判定：PASS（无不一致，不需要替编排器圆场的地方）。**
两点必须记入 TODO（MINOR）：① counts 是**移动靶**——本轮判定期间就变了两次（51→53、32→38、7→8），
建议 `counts` 增 `measured_at_head` 字段（记测量时的 `git rev-parse HEAD`），否则跨实例复核永远对不上时点；
② `resume.self_check_gates_rc0.gates[*].measured_at` 未随两次重测更新（16 项全是 `22:48:36`），同 A 项 T-A4。
---

## 本轮可放行的下一步（不阻塞）

1. **M0-01 置 `PASS_WITH_TODO`**：`state.json.tasks.M0-01.status` 可由 `VERIFYING` 推进（本报告即其 Q 交叉验证），
   条件是同时挂上 A.3 的 T-A1…T-A5 五个 TODO。
2. **D-001…D-009 全部置 `CLOSED`**：账本 9 条一并更新（按 D-009 的修复后流程写入并**回读断言**），
   并附各单的文档更正子项：D-002 的 `qa/verify_package.py` 路径、D-003 的 `check-ignore -v` 判据、
   D-006 的 37/6 过期数字加时点注、D-008 的「29 张卡」口径。
3. **BLK-02 维持关闭**：字体确已装（`dpkg-query` = `install ok installed` + `fc-list` 命中 10 条 + `fc-list :lang=zh` 37 条），
   此前 WARN 属 D-007 工具假阴性；M0-03/M5-01 的视觉走查**不再需要**「字体度量不一致」声明。
4. **BLK-01 维持开启（任务级待验证）**：doctor 只证明缓存与包存在；必须由 M0-03 真跑一次 Playwright 才能关闭。
5. **CR-002 可进入执行**：本档（在飞 Q 实例）已返回，`CR-002.md:99-105` 的 HOLD 条件之一已解除；
   待另一在飞实例（M0-03/S1+S2）返回后按 §6.3 的 8 步原子执行，并附带 G.5 的 4 条修复项。
6. **M0-02 S2（首迁实现）可派**：与 CR-002 的契约编辑无写权限交集（`migrations/**`、`src/campaignlab/infra/db/ddl_compare.py`、
   `tests/integration/bootstrap/**`、`pyproject.toml`、`uv.lock`），但**必须**在派单提示词里带上 Q7 裁定
   （删 `[tool.uv] package = false` + 重跑 `uv lock`），且与 CR-002 的契约提交**分开两次提交**，不要混线。
7. **E 项三条**：①不改文件、③不改文件；②只改 `CR-001.md:37` 一句话（MINOR，可与下次治理提交合并）。
8. **ADR-005 可维持 ACCEPTED**：与契约、spec 均无冲突；只需按 G.3 补两条实现约束（MINOR，M0-03b 冻结前完成）。

## 必须先修才能放行的阻塞项

| # | 阻塞项 | 严重度 | 阻塞什么 | 必须怎么做 |
|---|---|---|---|---|
| **BLK-Q1** | `orchestrator/tasks/M0-03.md:12` 与 `:38` 仍把「深链/刷新/回到合法入口」挂名 **AC-034**，与同卡 `:68-74` 的加注自相矛盾（D-008 同类错误未修净） | **MAJOR** | **阻塞 M0-03 的 S6/S8/S9 派单**（S8 会照错误口径写 vitest 断言、S9 会对 AC-034 出错误 PASS；叠加 M0-02 侧的 `deferred_to`，AC-034 的 HTTP 负例有整条漏检风险） | 按 F.3 的 1–3 条改写两行 + 给 M0-03 重切时带 `--ac AC-001,AC-034`（或把 `ACCEPTANCE.md:9/42` 原文粘进卡内）；立 MAJOR 缺陷单（暂记 Q-N2） |
| **BLK-Q2** | `orchestrator/handoff/M0-02-design.md` §5 V11 硬编码「40 files already formatted」（实测已 51/53）、§5 V1–V13 全带 `PYTHONPATH=src`（与 Q7 裁定冲突）、§6 S5 行仍称 `evidence/**` 不在 `scope_allow`（已被 D-008 修复推翻） | **MINOR（但对 S5 是硬阻塞）** | **阻塞 M0-02 的 S3/S4/S5 派单**（S5 会拿错分母判红，或用错命令口径取证；也可能误认为自己越界而停轮） | 按 H 项 1–3 条打三处补丁（加注即可，不必重写设计）；若 CR-002 选项 B 已执行，同时更新设计头部的 `sha16/bytes`、§5 V1 的期望值与 §1 `listWorkspaces` 的 `status` 参数、§6 的 422 分支 |
| **BLK-Q3** | CR-002 执行后必须**重切两份切片**并更新 `source.openapi.sha16`、`counts.live_openapi_sha16`、以及所有以 `01bd28f0772f506e` / `1.0.1` 为基准的门禁文本（`M0-02.md:53-56`、`M0-03.md:47-52`、设计 §5 V1） | **MAJOR（若漏做）** | **阻塞 CR-002 选项 B 的落地**（漏做会让 M0-03 的 PRE-3 切片新鲜度门禁当场判红，或更糟：静默派发过期切片＝D-004 复发） | 严格按 `CR-002.md:80-98` 的 8 步执行；第 5 步「与入库件 diff，差异仅限 `status` 参数与 sha/bytes」必须由脚本实测并留 rc；执行后重跑 `check_contracts.py check`（登记项与实测差异同变 **13**）、`check --validate`、`pytest -q` |
| **BLK-Q4** | 门禁清单口径不唯一（4 份互不相同），且 `tasks.M0-01.gates` 有 2 条的 `cmd` 字段是描述文字而非命令 | **MINOR** | 不阻塞开发，但**阻塞 M0 收口**（M0 出口需要一份可机械复跑的门禁全集；本轮取证档已为此付出一整节口径考古） | 按 D.3 的 1–4 条执行：指定 `resume.self_check_gates_rc0`（16 项 G）为唯一权威、其余文档改为引用 G 编号、两条描述性 `cmd` 换成命令原文、手册 15.3 增补「同一任务不得存在两份以上门禁清单」 |

> 关于「Q-N1…Q-N4」：这是本报告建议新立的 4 张单（Q-N1 MINOR 门禁口径不唯一、Q-N2 **MAJOR** M0-03 卡 AC-034 转述错误、
> Q-N3 MINOR CR-002 影响面扩写 + 剩余 5 处同类缺口、Q-N4 MINOR 设计文档三处过期文本）。
> 实际编号由编排器分配，并按 D-009 的修复后流程写入账本且**回读断言**。
> **（附录 B.5 更正，2026-11-13T01:42）** `D-010` 已于 01:29 被编排器占用（M0-03 卡三处记载不一致：BLK-02 过期 /
> `scope_allow` 缺项 / `ConfirmDialog` 交付期自相矛盾），并在 `f12dcf8` 入账；故本报告建议的 Q-N1…Q-N4 应从 **`D-011`** 起分配，
> 另新增 Q-N5（缺陷单落盘与台账写入的原子性）。映射见附录 B.5。

---

## 附录 A · 判定档自身的纪律自证

- **写入范围自律**：本档**只**写了 `qa-reports/m0/**` 与 `evidence/M0/Q-VERIFY-M0-01/judge/**`；
  `git status --porcelain spec/` = 空（多次复验）；未执行任何 git 写操作（无 add/commit/push/checkout/reset/stash）；
  未 sudo；未 spawn 子智能体；未运行 `npm install/ci/build`、`vite`、`playwright`、`openapi-typescript`
  （`doctor.sh` 内部的 `node -v`、`npm -v`、`npm ci --dry-run` 属脚本自带的**只读探测**，为完成 C 项「连跑 3 次 doctor」
  的硬性要求而不可避免，已在 C.1 明示；`--dry-run` 不改动 `web/node_modules`）；
  未整读 `contracts/openapi.json`（443552B）与任何 `bank-b.json`，全部经 `python3` 定点提取。
- **写文件通道**：全部经 PowerShell 字面 here-string → base64 → `wsl.exe … base64 -d` 整文件写入（NOTE-02 / 手册 13.2）；
  未使用含 `/` 的 sed 模式串；所有 rc 显式 echo，未用 `| head` 掩盖 rc。
- **并发观测**：判定期间另一 lane 正在改 `web/`（00:10 起出现 ` M web/{eslint,playwright,vite}.config.*`、`web/tsconfig.json`、
  `web/src/main.ts` 与多个 `web/src/*/.gitkeep`、`web/tests/**`），HEAD 亦由 `6d9f1b2` 前进到 `b1f38a9`。
  本档所有分母与门禁结论都标注了测量时点，未把并发变更算作回归。
- **本档产生的证据文件**（`evidence/M0/Q-VERIFY-M0-01/judge/`）：
  `a1-python-gates-rerun.log`、`a2-m0-01-evidence-and-wheels.log`、`b1-defects-d001-d005-rerun.log`、
  `b2-d003-checkignore-method.log`、`c1-doctor-determinism.log`、`c2-doctor-byteidentity-fclist-pytest.log`、
  `c3-doctor-line43-nondeterminism.log`、`c4-doctor-counting-semantics.log`、`e1-cr001-adr004-changes.log`、
  `e2-required-arrays-and-changes-schema.log`、`f1-ac-transcription-audit.log`、`g1-cr002-facts-and-d009.log`、
  `i1-denominators.log`、`i2-ruff-lint-scope-8-vs-7.log`（比对脚本本体在 `/tmp/q_ac_compare.py`，按要求未入库）。

## 附录 B · 可入库确认（`git ls-files --others --exclude-standard`）与写入后的分母复测

> 测量时点：2026-11-13T01:42:00+08:00，HEAD=`f12dcf8`。判定期间 HEAD 由 `ee51f3f` → `6d9f1b2` → `b1f38a9` → `f12dcf8`
> 连续前进（并行 lane 改 `web/`、编排器收 D-009/D-010 与 M0-03/S1+S2 入库），本档**未做任何 git 写操作**。
> 原始输出：`evidence/M0/Q-VERIFY-M0-01/judge/{i3,i4,i5,f2,z1}-*.log`。

### B.1 命令与原文输出（rc=0）

```console
$ git ls-files --others --exclude-standard qa-reports/ evidence/M0/Q-VERIFY-M0-01/judge/
evidence/M0/Q-VERIFY-M0-01/judge/a1-python-gates-rerun.log
evidence/M0/Q-VERIFY-M0-01/judge/a2-m0-01-evidence-and-wheels.log
evidence/M0/Q-VERIFY-M0-01/judge/b1-defects-d001-d005-rerun.log
evidence/M0/Q-VERIFY-M0-01/judge/b2-d003-checkignore-method.log
evidence/M0/Q-VERIFY-M0-01/judge/c1-doctor-determinism.log
evidence/M0/Q-VERIFY-M0-01/judge/c2-doctor-byteidentity-fclist-pytest.log
evidence/M0/Q-VERIFY-M0-01/judge/c3-doctor-line43-nondeterminism.log
evidence/M0/Q-VERIFY-M0-01/judge/c4-doctor-counting-semantics.log
evidence/M0/Q-VERIFY-M0-01/judge/e1-cr001-adr004-changes.log
evidence/M0/Q-VERIFY-M0-01/judge/e2-required-arrays-and-changes-schema.log
evidence/M0/Q-VERIFY-M0-01/judge/f1-ac-transcription-audit.log
evidence/M0/Q-VERIFY-M0-01/judge/f2-m0-03-ac034-recheck-at-f12dcf8.log
evidence/M0/Q-VERIFY-M0-01/judge/g1-cr002-facts-and-d009.log
evidence/M0/Q-VERIFY-M0-01/judge/i1-denominators.log
evidence/M0/Q-VERIFY-M0-01/judge/i2-ruff-lint-scope-8-vs-7.log
evidence/M0/Q-VERIFY-M0-01/judge/i3-appendix-b-recheck-at-b1f38a9.log
evidence/M0/Q-VERIFY-M0-01/judge/i4-identity-fix-quotepath.log
evidence/M0/Q-VERIFY-M0-01/judge/i5-state-counts-at-f12dcf8.log
evidence/M0/Q-VERIFY-M0-01/judge/z1-committable-list-final.log
qa-reports/m0/Q-VERIFY-M0-01.md
rc=0
count=20
```

逐个 `git check-ignore -q` → **20/20 全部 rc=1**（未被忽略），依据 `.gitignore:18` 的 `!evidence/**/*.log` 例外，
19 个 `.log` 与 1 个 `.md`（本报告）**全部可入库**。

### B.2 写入后的分母复测（HEAD=`f12dcf8`）

| 指标 | 受托基线（任务书） | `6d9f1b2` 实测 | `f12dcf8` 实测 | `state.json` counts | 判定 |
| --- | --- | --- | --- | --- | --- |
| `ruff format --check .` 的 N | 51 | 51 | **56** | 56 | 相符（基线已漂移） |
| tracked `.py`+`.md`（作用域内） | — | 51（py7/md44） | **55**（py8/md47） | py=8，md=48（含未跟踪 1） | 相符 |
| untracked 未忽略（作用域内） | — | 0 | **1**（本报告） | `untracked_component`=本报告 | 相符 |
| 恒等式 `tracked+untracked==N` | — | 51=51 ✓ | **55+1=56 ✓** | `identity`=True | **PASS** |
| `pytest -q` passed | 32 | 32 → 38 | **38**（rc=0） | 38 | 相符 |
| `mypy .` 源文件 | 7 | 7 → 8 | **8**（rc=0） | 8 | 相符 |
| `ruff_lint_scope_files` | 7 | 8（`.py`）/ 9（`--show-files`） | **8 / 9** | 8 | 口径差 1＝`pyproject.toml`（见 I.2） |

**口径陷阱（本档踩过并已纠正，记录以免后人复踩）**：`git ls-files '*.md'` 对非 ASCII 路径默认加双引号转义，
使 `grep -v '^spec/'` **失效**——`spec/frontend-template-spdb-v1.1/README_设计与使用说明.md` 与 `checklist_交付前自检.md`
两个文件被误计入，得 tracked=55→57 的假值、恒等式假 FAIL。必须用 `git -c core.quotepath=false ls-files`
（或 `state.json` 里记的 `git ls-files -z ... | tr '\0' '\n' | grep -vE '^[\"]?(spec|prototype|web)/'`）。
纠正后 `i4` 实测：tracked=55、untracked=1、N=56，**IDENTITY=TRUE**。

**结论**：`f12dcf8` 时点三项计数与 `state.json.counts` **逐一相符**；任务书给的「pytest 32 / mypy 7 / ruff 51」
是 `ee51f3f` 时代基线，已被 D-009 提交（+1 py +1 md）与 M0-03/S1+S2 入库（+2 md）连续取代。
`state.json` 的 `denominator_history` 两条（00:42:29 ruff=53、01:37:27 ruff=56）与本档两个实测时点**逐字吻合**，
且已预告「Plato 若据 51/32/7 判红属基准漂移，非真实回归」。本档据此**不判红**，但记 **Q-N1'（MINOR·流程）**：
派单文本携带的分母基线应带 `counts_refreshed_at` 时点戳，否则 Q 档每次都要重做一次口径考古。
另记 **Q-N1''（MINOR·文档）**：`counts.ruff_formatted_files_composition.drift_rule` 内文写「稳定分母是
`ruff_lint_scope_files`（纯 Python，**现 7**）」，而同层 `ruff_lint_scope_files` 实测值已是 **8**——自述数字过期。

### B.3 判定期间观测到的一次**真实 RED**（台账守卫，70 秒内自愈）

- `01:36:17`（HEAD=`b1f38a9`）：`uv run --no-sync pytest -q tests/unit/test_state_ledger.py` → **rc=1，1 failed 5 passed**；
  `test_every_md_on_disk_has_ledger_entry` 报 `orphan=['D-010']`。同刻全量 `pytest -q` → **1 failed, 37 passed**，rc=1。
  旁证：`orchestrator/defects/D-010.md` mtime=`01:29`、`git status --porcelain` = `??`（未跟踪），
  `state.json` 内 `D-009` 命中 **9** 次、`D-010` 命中 **0** 次。
- `01:39:43`（HEAD=`f12dcf8`）复测：**rc=0，38 passed**；台账 `defects` 条目=**10**（D-001…D-010 全 `FIXED_PENDING_Q`）。
- 判定：**这正是 D-009 修复所装守卫的预期行为**——磁盘有单、账本无账即红灯，把「先落 `D-010.md`、后写 `state.json`」
  的窗口暴露成可复现 RED，随后被编排器 01:37:27 的提交闭合。故 **D-009 守卫有效，不判红**；
  但记 **Q-N5（MINOR·流程）**：缺陷单落盘与台账写入必须在**同一次原子提交**内完成，否则并发 Q/子智能体在该窗口
  跑 `pytest` 必得假 RED（本轮就发生了一次）。建议把「新增缺陷单」固化为单一脚本（写 md → 改 `state.json` → 跑守卫 → 提交），
  并在手册 6.x 明列该顺序为硬性纪律。

### B.4 F 项 MAJOR 的复测（HEAD 前进后仍成立，且已扩散到 S1/S2 产物）

`f2-m0-03-ac034-recheck-at-f12dcf8.log` 实测：

1. spec 权威 `spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md:42`：
   `| AC-034 | 测试过期会话、错误 Host/Origin、跨工作区 ID 和上传失败 | 按 401/403/404/413 或 422 返回。隔离、路径、日志和 ETag 证据可查 | HTTP 负例 |`
2. 「深链…回到合法入口」的真实出处是 **`spec/CampaignLab-SDD-v1.0/framework/FRONTEND.md:12`**
   （「界面实现」第 2 条：深链接带工作区和对象标识；直接打开、刷新、返回、切工作区、404 和过期会话都要能回到合法入口），
   **不是** `qa/ACCEPTANCE.md` 的任何 AC（`grep -rn 深链` 在两份 `ACCEPTANCE.md` 内**零命中**）。
3. `orchestrator/tasks/M0-03.md:12` 与 `:38` 仍把该页面侧断言标为 **AC-034**；同卡 `:77` 却明写
   「spec 第 42 行的 AC-034 实为『过期会话、错误 Host/Origin…』」→ **同一张卡自相矛盾**。
4. 已扩散到已入库的 S1/S2 产物 `orchestrator/handoff/M0-03-design.md`：`:5`（`UI-01（route /，FR-01，AC-001 + AC-034）`）、
   `:69`（401 存 `?redirect=`（AC-034））、`:84`（`deep-link.spec.ts`（AC-034））、`:92`（S8「AC-001/AC-034 页面侧断言」）
   → M0-03 的 S3–S10 会按**错误编号**写测试文件、采证据、出 AC 结论。
5. 对照 D-008 已修的 M0-02 卡：`orchestrator/tasks/M0-02.md:13` 已改为 spec 原文口径并加注「（已按 spec 原文修正，见文末裁定 Q1）」，
   `:79` 也写了「M0-03 卡加注：…不是 M0-02 的 AC-034」→ **D-008 的修法正确，但只修了 M0-02，同类错误在 M0-03 未修净**。
6. 判定：**MAJOR**，即 BLK-Q1 / Q-N2 → 建议编号 **`D-011`**。必须修复：把 `M0-03.md:12`、`:38` 与
   `M0-03-design.md:5`、`:69`、`:84`、`:92` 中表示「页面侧深链」的 `AC-034` 改引 `framework/FRONTEND.md:12`
   （或设计文档已用的 `FR-01`），真正的 AC-034（HTTP 负例）保留在 M0-02。**阻塞 M0-03 的 S6/S8/S9 派单**。

### B.5 建议新立缺陷单的编号映射（`D-010` 已被占用后的更正）

| 本报告编号 | 建议实编号 | 严重度 | 一句话 | 阻塞 |
| --- | --- | --- | --- | --- |
| Q-N2 | **D-011** | **MAJOR** | `M0-03.md:12/:38` + `M0-03-design.md:5/:69/:84/:92` 把页面侧深链误标 AC-034（真出处 `framework/FRONTEND.md:12`），与同卡 `:77` 自相矛盾 | 是（M0-03 S6/S8/S9） |
| Q-N1 | **D-012** | MINOR | 门禁清单四份互不唯一 + `tasks.M0-01.gates` 两条 `cmd` 是描述文字；`drift_rule` 自述「现 7」已过期 | 否（阻塞 M0 收口） |
| Q-N3 | **D-013** | MINOR | CR-002 影响面需扩写（另 6 个资源同缺状态字段、9 处用 `state` 命名）；选项 B 执行后必须重切两份切片并更新 sha16 | 是（若漏做＝MAJOR） |
| Q-N4 | **D-014** | MINOR | `M0-02-design.md` 三处过期文本（V11 硬编码 40 files、V1–V13 全带 `PYTHONPATH=src`、§6 S5 称 `evidence/**` 不在 `scope_allow`） | 是（对 M0-02 S3/S4/S5） |
| Q-N5（新增） | **D-015** | MINOR | 缺陷单落盘与 `state.json` 台账写入非原子，产生可复现的假 RED（本轮 `b1f38a9` 实测 orphan=`['D-010']`） | 否 |
| Q-N1'（新增） | 可并入 D-012 | MINOR | 派单文本的分母基线无时点戳（51/32/7 已被 56/38/8 取代） | 否 |

> 以上 5–6 张单**本档一律未写入** `orchestrator/**`（越界），仅提供编号与最小修复面，由编排器按 D-009 修复后的
> 「写入 → 回读断言 → 跑 `test_state_ledger.py`」流程落账；落账后须与 `D-010` 同批提交，避免 B.3 的窗口复发。
