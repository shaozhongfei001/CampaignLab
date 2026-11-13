# Q-VERIFY-WAVE1 · 派单上下文包（编排器生成，wave1 出口复核）

> 本文件由脚本从 `orchestrator/state.json`（834 KB）与 `spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md` 抽取生成，
> 目的是让你**无需整读**台账与契约（`dispatch_requirements` 第 3 条）。如需其它字段，向编排器索取，禁自行整读。
> 生成时点 HEAD = `69db892`。

## 1. 你的唯一任务

对 **wave1（M0-02 + M0-03）** 做出口复核，判定这两个任务能否由 `IN_PROGRESS` 翻为 `DONE`，
并为 **11 个 gate**（M0-02 五个 + M0-03 六个）逐条给出 `rc` 与 `evidence` 指针（A109 ②③：wave 出口由 Q lane 复核汇总，**禁裸 null**）。

**你是判定方，不是台账写入方**：禁改 `orchestrator/state.json`、禁任何 git 写操作。
把结论写进你的报告，由编排器落账。

## 2. 写权（严格）

- **允许**：`evidence/M0/Q-VERIFY-WAVE1/**`（新建目录）
- **禁止**：其它一切路径。特别是 `src/**`、`web/**`、`tests/**`、`contracts/**`、`spec/**`、`migrations/**`、`orchestrator/**`（含 state.json 与 handoff/）、`docs/**`。
- 你**只读**复核，不修任何缺陷；发现问题只**归因并立建议**，由编排器裁定（非自有红点只归因不修）。

## 3. 待复核的 11 个 gate（现值全为裸 null，这是 A109 ③ 的违规，需你给出真值）

### M0-02（lane S，status IN_PROGRESS，acs ['AC-001', 'AC-034', 'AC-035']）

| # | gate.id | 现 rc | 现 evidence | authoritative（spec 原文口径） |
|---|---|---|---|---|
| 1 | AC-001 | `None` | `` | — |
| 2 | AC-034 | `None` | `` | 过期会话、错误 Host/Origin、跨工作区 ID、上传失败 -> 401/403/404/413 或 422；隔离/路径/日志/ETag 证据可查（spec ACCEPTANCE.md 第 42 行） |
| 3 | AC-035 | `None` | `` | 按 M0 锁版本、迁移、核对包与 API -> verify_package.py、DDL 等价、OpenAPI 请求响应及前端生成类型通过；锁与运行环境清楚（spec ACCEPTANCE.md 第 43 行） |
| 4 | alembic 首迁与 sqlite-v1.sql 结构比对通过 | `None` | `` | — |
| 5 | 契约测试（口径依裁定 Q2/Q3 收窄） | `None` | `` | HTTP 层：Problem 结构、Idempotency-Key 重放一次生效、createWorkspace 的 ETag 发布；DTO/单测层：Job 202 语义与 If-Match 412/428；HTTP 端到端 202 与 412 deferred_to 拥有对应 op 的后续任务 |

**已登记的子任务证据指针（`subtask_progress_evidence`，你需逐条核验其真实存在与内容相符）**：

- `S1`：orchestrator/handoff/M0-02-design.md（117 行）
- `S2`：migrations/**（0001_initial_schema）+ evidence/M0/M0-02/migration-diff.md
- `S4`：本提交：tests/api/{conftest.py(193),test_contract_declarations.py(191),test_contract_http.py(436)}，51 passed；覆盖 5 个已实现 operationId 的 200/201/400/401/403/409/413/422 分支 + Problem/Issue 结构 + ETag + 幂等重放 + FU-12 正向 health
- `S5`：本提交（R10-A）：evidence/M0/M0-02/ac.md + http/**（24 件：编号 .http 19 = 01–12、14–20；辅助 40/90/96/97/98）+ evidence/M0/summaries/M0-02.md；commands.md 追加 S5 段（90 行纯追加）、migration-diff.md 追加 S5 复核（22 行纯追加）。AC-001 PASS / AC-034 PASS_WITH_TODO / AC-035 PASS；doctor `PASS=5 WARN=0 FAIL=0 RESULT=HEALTHY`；FU-7 已取证（http/20 = status DEGRADED / worker READY / schema_revision UNMIGRATED）；D-033 实锤复现（幂等重放正文非逐字节相同：首次 DTO 序 vs 重放字典序，状态码/ETag/字段值全一致）-> 归 FU-21。编排器抽验：2 处 tracked 修改 numstat 90/0、22/0 纯追加；源码/测试/配置零改动；_runtime/ 已删；明文令牌零残留（仅存 sha256 前 12 位）。抽验另发现证据计数五处失真 -> 立 D-038 并同批更正、索引补全 2 行。**M0-02 暂不翻 DONE**：仍需 wave1 出口 Q 复核 + AC 取证回填（A109），且须等 Mencius 交回 web/** 后再派。
- `S3a`：src/campaignlab/infra/db/paths.py 等公共冻结件（f457ec9）
- `S3b`：31908fa：api/session.py + api/workspaces.py + app.py 挂载 + tests/unit/test_s3b_routes.py
- `S3c`：f457ec9 feat(M0-02/S3c)：config/clock/domain/__main__/cli(含 doctor)/api{app,deps,health}
- `S3d`：46dca2b feat(M0-02/S3d)：application 服务与 repositories、api/deps.py 三端口实体化（14 文件）

**subtask_progress 现值**：`{"S1": "DONE", "S2": "DONE", "S3a": "DONE", "S3b": "DONE", "S4": "DONE", "S5": "DONE", "S3c": "DONE", "S3d": "DONE"}`

### M0-03（lane F，status IN_PROGRESS，acs ['AC-001', 'AC-034']）

| # | gate.id | 现 rc | 现 evidence | authoritative（spec 原文口径） |
|---|---|---|---|---|
| 1 | AC-001 页面侧 | `None` | `` | — |
| 2 | AC-034 | `None` | `` | — |
| 3 | vue-tsc 通过 | `None` | `` | — |
| 4 | vitest 通过 | `None` | `` | — |
| 5 | 1440x900 与 1024x768 截图 | `None` | `` | — |
| 6 | 公共组件冻结清单 | `None` | `` | — |

**已登记的子任务证据指针（`subtask_progress_evidence`，你需逐条核验其真实存在与内容相符）**：

- `S1`：f12dcf8 feat(web): M0-03/S1+S2（web/*.config.*、tsconfig、src/main.ts）
- `S2`：f12dcf8 + docs/design/token-mapping.md + orchestrator/handoff/M0-03-design.md
- `S3`：052a492（web/src/styles/tokens.css + 一致性守卫）+ evidence/M0/M0-03/S3-S4-commands.md
- `S4`：052a492（web/src/api/types.ts 由 OpenAPI 生成，diff 为空）+ 同一证据文件
- `S5`：9832fd1 feat(M0-03/S5) + evidence/M0/M0-03/S5-gate-transcript.txt
- `S6`：5d16d4d feat(M0-03/S6-S9)：web/src/pages/**（2 页）+ web/src/components/**（13 件）
- `S7`：5d16d4d：web/tests/**（11 文件）键盘基线参数化
- `S8`：5d16d4d：vitest 单测脚手架 + AC-001 断言 + 深链断言（framework/FRONTEND.md:12）
- `S9`：5d16d4d + evidence/M0/ui/{ui-01-desktop-1440x900.png,ui-01-laptop-1024x768.png,ui-01-visual-notes.md} + evidence/M0/M0-03/playwright-readiness.json
- `S10`：本提交：orchestrator/handoff/M0-03-public-components.md（303 行/26803B），13 件公共组件的 props/slots/emits 契约表（30 行 grep 实抽）、依赖关系、冻结边界、消费方指引、与 26 页覆盖对账

**subtask_progress 现值**：`{"S1": "DONE", "S2": "DONE", "S3": "DONE", "S4": "DONE", "S5": "DONE", "S6": "DONE", "S7": "DONE", "S8": "DONE", "S9": "DONE", "S10": "DONE"}`

## 4. AC 原文（权威路径 `spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md`，行号实测）

- `ACCEPTANCE.md:9` [AC-001] | AC-001 | 启动本机模式，换取一次性会话，新建并进入工作区 | 正常会话进入。重复令牌拒绝。工作区切换保留各自数据。worker 状态可见 | HTTP 与 Playwright |
- `ACCEPTANCE.md:42` [AC-034] | AC-034 | 测试过期会话、错误 Host/Origin、跨工作区 ID 和上传失败 | 按 401/403/404/413 或 422 返回。隔离、路径、日志和 ETag 证据可查 | HTTP 负例 |
- `ACCEPTANCE.md:43` [AC-035] | AC-035 | 按 M0 锁版本、迁移、核对包和 API | `verify_package.py`、DDL 等价、OpenAPI 请求响应及前端生成类型通过。锁和运行环境清楚 | 命令、锁和报告 |
- `ACCEPTANCE.md:48` [AC-001] - 集成覆盖 AC-001、002、005–007、009、012、015–017、025–031、034、035。

> 上表由脚本 grep 实抽（含 `AC-001`/`AC-034`/`AC-035` 字样的所有行）。若你认为还需其它行，
> **只读** `spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md` 该文件是允许的（它是 AC 唯一权威），
> 但禁整读 `contracts/openapi.json`（443 KB）与 `spec/**/bank-b.json`（284 KB）。

## 5. 必须遵守的既有裁定与规则（违反即判红）

- **A109**：AC 的 `rc`/`evidence` 禁裸 null；未取证者必须写 `evidence_status: NOT_YET_COLLECTED` + `deferred_to: <任务/子任务>`，使 47 条 AC 的收敛可度量。
- **A144（三段式越界自证）**：出口必须自证 (a) 写权外 tracked 修改 == 0；(b) 写权内 tracked 修改 `numstat` 的 `deleted == 0`（你全为新建，平凡成立）；(c) 写权外未跟踪新文件 == 0。三条均在仓库根 `/home/szf/dev/CampaignLab` 执行，按门禁四元组记账。
- **rule_rc**：`0`=成功/有匹配，`1`=无匹配（守卫期望），`2`=命令自身错误（**必须判红并修命令，禁记为 1**）。
- **R9-4**：grep 模式以 `-` 开头必须加 `--` 分隔符。
- **R10-5（本轮新立，务必遵守）**：grep 模式含 `|` `+` `?` `{}` `()` 者**一律加 `-E`**；BRE 下 `|` 是字面量，会把「有匹配」误报成 `rc=1 无匹配`的**假绿**。且任何「rc=1 无匹配」型守卫作为通过判据引用前，**必须再跑一条必命中的正向对照 grep**。
- **rule_no_tmp_only_evidence**：证据一律落 `evidence/M0/Q-VERIFY-WAVE1/**` 并使其可入库，禁只存 `/tmp`（WSL2 VM 空闲即被终止，/tmp 会清空）。
- **rule_evidence_count_must_be_programmatic（本轮新立）**：报告里任何「共 N 件 / N 行 / N 条」必须由脚本实测生成，禁手工累加。
- **不采信自报**：M0-02/S5 与 M0-03 各子任务的 gate rc 均由 lane 自报，你必须**亲自重跑**关键门禁（见第 6 节），不得照抄。
- **写入通道**：多行文件一律用 `python3` 脚本 + `open(..., "w", encoding="utf-8", newline="\n")`；写后回读断言**无 BOM、无 `\r`、以 `\n` 结尾**。禁在 `wsl.exe -e bash -lc "..."` 的内层双引号里放 `$`（宿主是 PowerShell，`$HOME`/`$?` 会被展开成 Windows 值）。

## 6. 必须亲自重跑的门禁（cwd 已注明；rc 与关键输出按四元组记账）

| # | cwd | 命令 | 期望 |
|---|---|---|---|
| 1 | `/home/szf/dev/CampaignLab` | `export PATH="$HOME/.local/bin:$HOME/.local/share/node/bin:$PATH" && uv run --no-sync python -m campaignlab doctor` | rc=0，`RESULT=HEALTHY` |
| 2 | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q tests/api` | rc=0（契约/HTTP 层） |
| 3 | `/home/szf/dev/CampaignLab` | `python3 spec/CampaignLab-SDD-v1.0/qa/verify_package.py` | rc=0，`PACKAGE PASS` |
| 4 | `/home/szf/dev/CampaignLab` | `uv run --no-sync alembic -c migrations/alembic.ini current` | rc=0，head=`0001_initial_schema` |
| 5 | `/home/szf/dev/CampaignLab/web` | `npm run test` | rc=0（当前应为 12 files / 277 tests） |
| 6 | `/home/szf/dev/CampaignLab/web` | `npm run typecheck` | rc=0 |
| 7 | `/home/szf/dev/CampaignLab/web` | `npx playwright --version` 或等价探测 | **仅探测**：判定 M0-03 的「1440x900 与 1024x768 截图」gate 是真已取证还是 `NOT_YET_COLLECTED` |

> **注意**：`Volta(M0-04/S3)` 仍在同一工作树在飞（`src/campaignlab/infra/artifacts.py`、`tests/integration/jobs/`、`tests/unit/test_artifacts.py` 未入库）。
> 因此**禁跑全仓** `pytest -q` / `mypy` / `ruff .`（会把他 lane 半成品计入 → 假 RED）。第 2 项限定 `tests/api` 即为此故。
> 若你发现某条失败**源于 Volta 的在飞文件**，如实记为 `IN_FLIGHT_CONTAMINATION` 并归因，**不判 M0-02/M0-03 失败**。

## 7. 交付物（写在 `evidence/M0/Q-VERIFY-WAVE1/`）

1. `00-index.md` —— 本目录件数与行数（**脚本实测生成**）。
2. `verdict.md` —— 逐 gate 的判定表：`gate.id | 你实测的 rc | evidence 指针（仓库内相对路径，可含 :行号）| 判定（PASS / PASS_WITH_TODO / FAIL / NOT_YET_COLLECTED）| 依据`；末尾给 **M0-02 / M0-03 能否翻 DONE 的结论与阻塞项清单**。
3. `commands.md` —— 所有你跑过的命令的四元组（`cwd | 命令 | rc | 关键输出`）。
4. `defects-proposed.md` —— 你发现的新问题（若有），按「现象 / 证据 file:line / 定性 / 建议严重度 / 归属任务」格式，**只建议不立单**（立单是编排器的权）。

## 8. 回报格式（给编排器的最终消息）

① 11 个 gate 的判定摘要（一行一个）；② M0-02 / M0-03 的 DONE 结论与阻塞项；
③ 新发现问题清单（若有）；④ 越界自证三段式实测值；⑤ `loop_used`；⑥ 自估 token（如无计量句柄请明说，禁编造）；
⑦ 任何需编排器裁定的口径冲突（**不要自行决定**，§8 明写实现方不得自裁）。

