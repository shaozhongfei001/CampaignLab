# D-016 补卡批次 4 · 共用规则（编排器产出 · Lane T 只读）

_生成时间：2026-11-13T09:24:20+08:00 ｜ 本批 3 张卡：**M4-P01、M5-01、M5-02**（均 `critical=true` / `slack=0`）_

## 0. 为什么是 3 张（不是 4 张）

`state.json → budget.guardrail_status.corrective_action_next` 明载：批次 3 的 4 张卡正文合计 96231 B
（单卡 20–28 KB）是成本越限主因，故**批次 4 起降到 2–3 张**，并把「卡正文生成量」显式计入预算。
本批取 3 张：M4-P01（wave8 串行首）、M5-01（wave8 串行次）、M5-02（wave9）。
余 6 张（M1-04、M2-04、M3-04、M3-P02、M5-03、M5-P01）排批次 5/6。

**本批成本目标 ≤40k token**（批次 2 实测 50k/4 卡、批次 3 越限）。若你判断会越限，
**先把已完成的卡落盘并在回报里说明**，不要为省预算而降低卡的质量或跳过自检。

## 1. 唯一入口与禁读清单

**只读这些**（本文件 + 3 份按卡分节文件 + 3 份预生成切片 + 各卡分节文件里列出的 spec 小文件按行区间）：

- `orchestrator/handoff/D-016-batch4-rules.md`（本文件）
- `orchestrator/handoff/D-016-batch4-M4-P01.md` / `-M5-01.md` / `-M5-02.md`（**写哪张卡才读哪份**）
- `orchestrator/handoff/{M4-P01,M5-01,M5-02}.slice.json`（**禁整读**，见 §2 定点抽取配方）
- `orchestrator/tasks/M4-01.md`（**格式骨架参照**，分段读，别整读）
- 手册 `docs/delivery/LONG-HORIZON-ORCHESTRATION.md` **只读这 5 段**（合计约 142 行，全册 785 行禁整读）：
  §3.2 任务卡模板（174–204）、§6.3 硬规则（312–333）、§6.4 max 设计+flash 量产（334–383）、
  §15.5 成本账本必填（656–679）、§15.6 关键路径循环上限（680–694）

**禁整读**：`contracts/openapi.json`（443309 B）、`orchestrator/state.json`（346 KB）、
`spec/**/bank-b.json`（284 KB）、手册全文、任何 `*.slice.json` 全文。

**禁改**：`spec/**`、`contracts/**`、`docs/**`、`orchestrator/**`（除你自己新建的 3 张卡）、
`tests/unit/test_task_card_narrative.py`、`src/**`、`web/**`、`migrations/**`、`scripts/**`、
`pyproject.toml`、`uv.lock`。**唯一允许修改的既有文件** = `tests/unit/test_task_cards.py`
（且只准删 KNOWN_MISSING 的 3 行）。

## 2. 定点抽取配方（切片 109729 / 3781 / 14977 B，M4-P01 整读必越限）

一律用 `python3` 按键取值，禁 `cat` 整份切片。中间脚本放**仓库外**
`D:\ws\codex_rd\ss_campaignlab\.orch_tmp\laneT4\`（不进 git）：

    import json
    d = json.load(open("orchestrator/handoff/M4-P01.slice.json", encoding="utf-8"))
    print(sorted(d["operations"]))                                  # 只看 op 名
    op = d["operations"]["signReport"]                              # 只取一个 op
    print(json.dumps(op["responses"], ensure_ascii=False)[:2000])   # 截断打印
    print(json.dumps(d["acceptance_rows"]["AC-MR-09"], ensure_ascii=False))  # AC 原文四元组
    print(d["ddl"]["reports"][:1500])                               # DDL 片段

**PRE-3 断言口径（A18 更正，务必照此写）**：判定切片新鲜且目标全命中，必须断言
`("missing" not in d) and d["truncated_schemas"] == []`。
**禁**断言 `d["missing"] == []` —— `contract_slice.py` 仅在**有未命中目标**时才写 `missing` 键，
全命中时该键**不存在**，断言会 `KeyError`（批次 3 已踩过，见 D-023）。

**守卫命令的 cwd 口径（D-024 的教训）**：一切 `grep` 守卫**必须在仓库根** `/home/szf/dev/CampaignLab` 执行。
相对通配（`web/*`、`src/*`）在子目录下不展开 → `grep` 返回 **rc=2**，那是「命令没跑起来」，
**不是** rc=1「无匹配」。rc 语义：`0` = 有匹配、`1` = 无匹配、`2` = 命令自身错误（必须判红并修命令）。

## 3. 卡的硬格式约束（由守护测试机器判定，违反即红）

实测自 `tests/unit/test_task_cards.py`（100 行）与 `tests/unit/test_task_card_narrative.py`：

| 项 | 约束 | 判定处 |
|---|---|---|
| head | 卡首 → 「子任务档位表」表头行之前 **≤60 行** | `HEAD_MAX_LINES = 60` |
| tail | 档位表最后一行 → 卡尾 **≤40 行** | `TAIL_MAX_LINES = 40` |
| total | 整卡 **≤200 行** | `TOTAL_MAX_LINES = 200` |
| 表头 | **逐字**等于四列形态（见下） | `REQUIRED_TABLE_HEADER` |
| 必需段落 | 每卡必含 4 段：`scope_allow`、`scope_deny`、`outputs`、`子任务档位表` | `REQUIRED_SECTIONS` |
| 任务总数 | `len(state.json.tasks) == 29`（钉死，禁增删） | `TASK_TOTAL_DENOMINATOR` |
| 缺口对账 | 磁盘卡 ∪ KNOWN_MISSING == 29，双向无差、无孤儿卡 | 3 个 test |
| 豁免集合 | `LEGACY_NO_TABLE = {M0-01, M0-P01}`、`LEGACY_TAIL_ANNOTATED = {M0-02, M0-03}` —— **本批 3 张卡都不在豁免集内，四项全须达标** | 常量 |

`REQUIRED_TABLE_HEADER` 的逐字形态（四列，前后各一个竖线，空格位置照抄）：

    | 子任务 | 档位 | 预估 token | 产出 |

**KNOWN_MISSING 必须 9 → 6**：删掉 `"M4-P01"`、`"M5-01"`、`"M5-02"` 三行，其余字节不动
（`git diff --numstat tests/unit/test_task_cards.py` 应为 **`0  3`**）。
删后余 6 项 = `M1-04、M2-04、M3-04、M3-P02、M5-03、M5-P01`；恒等式 **磁盘卡 23 + 缺口 6 == 29**。

## 4. 档位表要求（手册 §15.5：无拆解表不得 spawn）

1. 每个子任务一行，四列（表头见 §3）。
2. **flash 行必须附「低复杂度：<可审计理由>」**（批次 3 口径：flash 行数 == 带理由行数，缺一条即红）。
3. **max 行必须给出 §6.3 的强制触发项**（跨模块一致性不变量 / 幂等与并发语义 / 状态机 /
   公共冻结件 / 基础设施单一来源 / 契约面变更 / 设计先行）。
4. 上限：**max 合计 ≤200k**、**flash 合计 ≤60k**、单个 flash 子任务 ≤12k。
5. 占比目标：flash 子任务数占比 ≥60 percent、flash token 占比 ≤35 percent。
   **不达标就照实写「不达标 + 理由 + 回补计划」，禁为凑配比降档、禁机械拆分**（手册 §15.5 / §6.6）。
   批次 3 的 M3-P01（44.4 percent / 18.9 percent）与 M1-P01（50.0 percent / 22.7 percent）
   就是照实记不达标的正面样本。
6. 卡内自证句里的百分比必须能被脚本重算复现（编排器会逐位比对，禁手填约数）。

## 5. 已知陷阱（**必须写成 U 项交编排器裁定，禁自行决定**）

1. **D-022（OPEN，pending_owner D-022-1）**：`MONTHLY_INVALID_SCOPE`、`MONTHLY_REPORT_KIND_REQUIRED`、
   `SNAPSHOT_SUPERSEDED` 三个 code **既不在活契约也不在 ADR-005 冻结的 20 码注册表**。
   暂按**选项 A**：分别复用 `INVALID_SCOPE` / `VALIDATION_ERROR` / `SNAPSHOT_CONFLICT`，
   语义标签落 `Problem.detail` + `Issue.code`。**禁在卡里要求实现这三个 code、禁要求扩注册表**，
   但**必须**写成 U 项：「AC-MR-10 原文要求 409 SNAPSHOT_SUPERSEDED，与 20 码权威表冲突，待项目负责人终裁」。
2. **A16**：`api/monthly_reviews.py` / `api/monthly_imports.py` / `api/monthly_reports.py` 是
   **非路由的领域/DTO 模块**；月报路由走既有 `runReview` / `getReview`
   （+ `input_json.profile='BANK_MONTHLY_V1'` 判别）与 `createImport` 等 + map-monthly。
   **禁在卡里新增月报专属 operationId**（活契约实测 0 个）。
3. **A17（编排器自我更正，原臆断已作废）**：月报结果落 `analysis_results(kind='review')` +
   `input_json.profile='BANK_MONTHLY_V1'` 判别，制品落 `artifacts(kind='COMPUTATION')`。
   **禁扩 `kind` 的 CHECK 枚举** —— 实测 `contracts/sqlite-v1.sql:102` 的 CHECK 只含
   `('comparison','review','diagnosis','question')`，不含 `monthly_review`。扩枚举属公共冻结件变更 = 走 CR。
4. **A30**：月报 MISSING 的承载 = `Review.monthly_review.state`（FULL/PARTIAL/MISSING）+
   `MonthlyReview.issues[]` + `Review.missing_requirements`（既有必填）。**禁增删字段**。
5. **A14 / A15 / A36（归属，避免双 owner）**：export 四 op（`createExport`/`getExport`/`listExports`/
   `downloadExport`）全归 **M4-02**，落 `src/campaignlab/api/exports.py`；`actions`/`action_followups`
   的**写权唯一归 M4-02**；`listAudit` 的**读入口归 M4-02**；`createReport`/`getReport` 归 **M4-01**。
   M4-P01 对这些只做 **cross_ref / 调用**，**禁写成 primary owner、禁重复实现**。
6. **A28**：M4-03 对 AC-026/027 **无取证义务**（其 cross_ref 不含 M4-03），只对 AC-025/028/030。
   写 M5-02 的 47 条 AC 复核矩阵时按 `acceptance.primary_owner` 逐条取，**禁臆断 owner**。
7. **`AC-101` / `AC-202` 不是 AC 编号**：它们是 `spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md:10`
   （AC-002 行）描述文本里的**活动编号**（「给 AC-101 绑定 S-101」）。真实 AC 只有
   `AC-001..AC-035`（35 条）+ `AC-MR-01..AC-MR-12`（12 条）= **47 条**
   （== `counts.acceptance_denominator`）。写 M5-02 的「47 条」矩阵时**禁把 AC-101/AC-202 当 AC**。
8. **AC-MR 原文位置**：在补丁的 `qa/CampaignLab-Review-Acceptance-Checklist.append.md`（20 行）、
   `framework/DELIVERY-PATCH.md`（23 行）、`reference/EVIDENCE-AND-DECISIONS.md`（36 行）、
   `START-CODEX-PATCH.md` —— **不在** `architecture/MONTHLY-REVIEW.md`（该文件 67 行，无 AC-MR 编号）。
   `contract_slice.py` 的 `ACCEPTANCE_SOURCES` 已含 BASE 与 DELTA 两源，切片里的 `acceptance_rows`
   就是权威原文；**AC 编号与原文一律只引切片/spec 原文，禁改写措辞**（D-011）。
9. **M5-02 的口径已扩大**：`docs/delivery/MONTHLY-DELTA-PLAN.md:22` 明载由「独立重跑 35 条」改为
   「独立重跑 **47 条**」，与 M5-P01 并行但**证据分目录**（M5-02 用 `qa-reports/m5-02/` +
   `evidence/M5-qa/` + `orchestrator/defects/D-*.md`；M5-P01 用 `qa-reports/monthly/` +
   `evidence/monthly/M5-P01/` + `defects/DMR-*`）。两条 QA 线写权限**互不包含**，禁交叉。
   注意 `state.json → tasks[M5-02].acs` 是**空数组**、gates 写的是「35 条 AC 逐条结论」——
   这是 wave 规划期的原文快照，**不要改 state.json**（你无写权）；按 D-011 与「不改写历史」偏好，
   在卡内以**加注**方式说明「口径已按 MONTHLY-DELTA-PLAN.md:22 扩为 47 条」，并把该不一致写成 U 项。
10. **wave8 是 serial**：`M4-P01 → M5-01`（月报报告闭环完成后才做固定环境全量回归）。
    卡内 deps 必须与 state.json 一致：M4-P01 deps = `[M4-01, M4-02, M4-03, M3-P01]`；
    M5-01 deps = `[M4-03]`；M5-02 deps = `[M5-01]`。**禁自行增删 deps**（state.json 变更属编排器写权），
    如需调整写 U 项。

## 6. 交付清单与自检（禁 git 写；自检一律用纯 `python3`）

⚠️ **本轮另有 S lane（S3d / Godel）正在写 `src/campaignlab/**` 并独占 Python 工具链**。
你**禁跑** `pytest` / `mypy` / `ruff` / `uv run`（会与在飞 lane 争用 `.venv` 产生**假红**，NOTE-10）。
自检只用系统 `python3` + 只读 `git status/diff`。编排器回收后会亲自用真实 pytest 复验守护测试。

交付物 = **3 个新文件** + **1 处修改**：

- `orchestrator/tasks/M4-P01.md`、`orchestrator/tasks/M5-01.md`、`orchestrator/tasks/M5-02.md`
- `tests/unit/test_task_cards.py`：KNOWN_MISSING 删 3 行（numstat `0  3`）

自检脚本必须覆盖（逐条给出实测值）：

1. 每卡 `head` / `tail` / `total`（**自己复现 `_split()` 口径**：head = 卡首→表头行前；
   tail = 档位表最后一行→卡尾；total = 整卡）+ 表头逐字比对；
2. 4 个 `REQUIRED_SECTIONS` 段落齐备；`scope_allow ∩ scope_deny == EMPTY`
   （前缀比较用 `startswith(prefix + "/")`；批次 3 曾因把 `monthly` 当 `monthly_ingest` 前缀而误报）；
3. KNOWN_MISSING 双向对账：`missing(实算) == KNOWN_MISSING`、`23 + 6 == 29`、
   `unregistered/recovered/orphans` 均空；
4. 每卡 `state.json.tasks[id].acs` 集合 == 该卡切片 `acceptance_rows` 的 id 集合
   （逐卡给出两侧列表与差集；M5-02 的 `acs` 是空数组，见 §5 第 9 条，按加注处理并写 U 项）；
5. 档位表占比重算（flash 子任务数占比、flash token 占比、max/flash 合计），与卡内自证句**逐位比对**；
6. 卫生：`CR=0`、`BOM=0`、以换行结尾（3/3 卡）；
7. 三份切片 + 4 份 context 文件 + `spec/**` + `contracts/openapi.json` 的 `sha256[:16]`+bytes
   **无漂移**（开工前先存基线，收工后比对）。

## 7. 回报格式（中文）

1. PRE-3 三方校验：`contracts/openapi.json` 自算 bytes/sha256[:16]
   （应为 **443309 / `592571099d638251`**）与三份切片 `source.openapi` 比对；三份切片自身指纹与
   §8 表比对；**自算，禁采信本文件**。
2. 每卡一行：`<ID>: head=.. tail=.. total=.. 表头=OK flash_tasks=a/b flash_tokens=..k/..k max_total=..k U项=n`
3. KNOWN_MISSING 双向对账结果 + `git diff --numstat tests/unit/test_task_cards.py`
4. U 项清单（逐条：现象 + 你的处置 + 请裁定什么）
5. 自检各项实测值 + 失败/重跑留痕（含你自己脚本的 bug 与更正）
6. `git status --porcelain` 全文 + 逐条归因（哪些是你的、哪些属 S lane）+ 越界自证
   （未做 git 写、未 sudo、未跑 pytest/mypy/ruff/uv）
7. **诚实偏差清单**（没做到的、妥协的、成本越限的）
8. token 自报值（`get_goal` 若无计量句柄则写 `null`，**禁估算**；可给客观量：工具调用次数、卡正文字节数）

## 8. 预生成切片指纹（**你自己必须重算比对，禁采信本表**）

| 卡 | 文件 | bytes | sha256[:16] | ops | pages | acceptance_rows | ddl |
|---|---|---|---|---|---|---|---|
| M4-P01 | `orchestrator/handoff/M4-P01.slice.json` | 109729 | `73a9bcf1c483adbd` | 8 | UI-21,UI-22,UI-24,UI-26 | 9 | 9 |
| M5-01 | `orchestrator/handoff/M5-01.slice.json` | 3781 | `87bfe2b0db49373d` | 1 | — | 4 | 0 |
| M5-02 | `orchestrator/handoff/M5-02.slice.json` | 14977 | `4ed7f37be9e8039a` | 0 | — | 47 | 0 |

三份均：`spec_version=1.0.1`、`source.openapi={bytes:443309, sha16:592571099d638251}`、
**无 `missing` 键**（全命中）、`truncated_schemas=[]`、`depth=5`。

M4-P01 切片内容清单（供你定点抽取，禁整读）：
ops(8) = `correctSnapshot`, `getReport`, `getReview`, `listReports`, `runReview`, `signReport`, `transitionAction`, `updateAction`；pages = UI-21, UI-22, UI-24, UI-26；
acceptance_rows(9) = AC-025, AC-026, AC-027, AC-028, AC-029, AC-030, AC-MR-09, AC-MR-10, AC-MR-11；ddl(9) = `action_followups`, `actions`, `actions__indexes`, `analysis_results`, `analysis_results__indexes`, `artifacts`, `reports`, `snapshots`, `snapshots__indexes`。

M5-01 切片：ops = `getHealth`；acceptance_rows = AC-029, AC-031, AC-032, AC-035。
M5-02 切片：无 ops / 无 pages / 无 ddl，只有 acceptance_rows(47 条 = 35 + 12)。
