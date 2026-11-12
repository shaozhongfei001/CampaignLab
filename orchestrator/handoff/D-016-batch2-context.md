# D-016 补卡批次 2 · 预抽上下文摘要（编排器产出 · Lane D 只读）

生成时间：2026-11-13T04:51:35+08:00 · 产出方：编排器（O lane） · 消费方：D-016 批次 2 补卡 lane（`qwen3.8-flash`）

## 为什么有这份文件

批次 1（8 张卡）实测 181k token，`over_cap=true`（上限 60k，越限 3.02×）。诊断：执行方自行整读
手册（758 行）+ 多个 spec 架构文件 + 活契约。纠正措施（手册 15.5 / 账本 `guardrail_status.corrective_action`）：
**批量降到 4 张 + 编排器预抽输入侧上下文**。本批目标 ≤45k。

**硬规则：本文件是 Lane D 的唯一 spec/手册入口。** 除第 5 节列出的精确行区间与第 1 节的 4 份切片外，
禁止整读 `spec/**`、`contracts/openapi.json`（443309 B）、`docs/delivery/LONG-HORIZON-ORCHESTRATION.md`（758 行）、
`orchestrator/state.json`（183065 B）。需要本文件未覆盖的信息时，写进 U 项交编排器裁定，**不得自行去读大文件**。

## 0. 本批 4 张卡（全部 `critical=true` / `slack=0`，实测自 `state.json`）

| 卡 | lane | deps | depth | height | AC | 标题建议 |
|---|---|---|---|---|---|---|
| M3-01 | D | M1-02 | 6 | 9 | AC-018、AC-019、AC-020、AC-033 | 策略复盘计算、五层漏斗与口径切换 |
| M3-02 | D | M3-01 | 7 | 8 | AC-021、AC-022、AC-024 | 阈值诊断、贡献拆解与情景试算 |
| M3-03 | D | M3-01、M3-02 | 8 | 7 | AC-023 | 登记问法计划执行与歧义澄清 |
| M4-01 | S | M3-03 | 9 | 6 | AC-025、AC-026 | 复盘报告生成、签认与修订链 |

`state.json` 实测 `gates`（除 AC 外的卡内 gate 必须逐字承接，禁改写）：
- M3-01：`analytics-golden.json 全量对齐`
- M3-02：`正负贡献分解与黄金值一致`
- M3-03：`60 条问法计划全部可重复执行`、`歧义问法返回待澄清`
- M4-01：`历史签认与后续记录可同时查询`

`state.json` 实测 `scope`（＝`scope_allow` 的路径字面量来源；A5 裁定：以卡字面量为准，
`X/**` 与 `X/` 语义等价、统一写 `X/`，`allow∩deny` 必须为空）：
- M3-01：`src/campaignlab/domain/analytics/`、`src/campaignlab/infra/duckdb/`、`src/campaignlab/api/reviews.py`、`tests/domain/analytics/`、`tests/golden/analytics/`
- M3-02：`src/campaignlab/domain/diagnosis/`、`src/campaignlab/api/diagnosis.py`、`src/campaignlab/api/estimate.py`、`tests/domain/diagnosis/`、`tests/golden/diagnosis/`
- M3-03：`src/campaignlab/domain/ask/`、`src/campaignlab/api/ask.py`、`tests/domain/ask/`、`tests/golden/ask/`
- M4-01：`src/campaignlab/domain/report/`、`src/campaignlab/api/reports.py`、`tests/domain/report/`、`tests/integration/report/`

`scope_deny` 固定项（四卡同）：`spec/**`、`contracts/**`、`web/**`、`migrations/**`、`scripts/**`、
`orchestrator/state.json`、其他任务的 `src/campaignlab/domain/**` 子目录、`evidence/M0/**`。
**交付必需落点若不在上述 `scope` 内（如 `orchestrator/handoff/<id>-design.md`、`evidence/M3/<id>/**`、
`evidence/M3/summaries/<id>.md`、`tests/unit/test_<x>_dto.py`），必须显式补进 `scope_allow` 并在 U 项说明**
（D-008 教训：M0-02 曾因 outputs 要求写 evidence 但 scope_allow 未含而自相矛盾）。

## 1. 已预生成的契约切片（PRE-3 三方校验用；本任务只读，禁自行重切）

编排器已于 2026-11-13T04:51:35+08:00 用 `scripts/contract_slice.py` 生成，四份 `missing=[]`、`spec_version=1.0.1`：

| 切片 | own sha16 | own bytes | operations | ddl 键 | acceptance_rows |
|---|---|---|---|---|---|
| `orchestrator/handoff/M3-01.slice.json` | `64d79b599bfe60d9` | 15681 | runReview、getReview | analysis_results(+indexes)、snapshots(+indexes)、evidence、object_evidence、audit | AC-018/019/020/033 |
| `orchestrator/handoff/M3-02.slice.json` | `3d55ec5497916343` | 27184 | runDiagnosis、getDiagnosis、computeEstimate、listThresholds、createThreshold | analysis_results(+indexes)、thresholds、artifacts、audit | AC-021/022/024 |
| `orchestrator/handoff/M3-03.slice.json` | `ea5be2b20dc1d21f` | 15284 | executeQuestion、interpretQuestion、getQuestion | analysis_results(+indexes)、artifacts、audit | AC-023 |
| `orchestrator/handoff/M4-01.slice.json` | `152c5fd4951eb584` | 26466 | listReports、createReport、getReport、signReport | reports、report_actions、actions(+indexes)、action_followups、receipts、artifacts、audit | AC-025/026 |

四份切片的 `source.openapi` 段均为 `{"path": "contracts/openapi.json", "bytes": 443309, "sha16": "592571099d638251"}`。
**指纹与字节数的权威现值见 `state.json → resume.self_check_gates_rc0.counts.live_openapi_sha16` / `.live_openapi_bytes`，
禁写死进卡（D-012 / D-013 / D-014）**；卡内一律写「以 state.json counts 为准」的指向句。
上表数值仅为编排器本次预生成时的留痕。

## 2. AC 原文行号（`spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md`，全文仅 52 行）

AC-018→第 26 行、AC-019→27、AC-020→28、AC-021→29、AC-022→30、AC-023→31、AC-024→32、
AC-025→33、AC-026→34、AC-033→41。
**D-011：卡内引用 AC 只引编号 + 原文，禁转述改写**（D-008 就是转述错误立的单）。
四份切片的 `acceptance_rows` 已含这些行的四元组原文（编号 / 输入及操作 / 通过条件 / 主证据），
**优先读切片，不要再去读 ACCEPTANCE.md**。

`primary_owner`（实测自 `state.json → acceptance.primary_owner`，卡内 cross_ref 必须照此写）：

| AC | primary | cross_ref | confidence | 主证据列 |
|---|---|---|---|---|
| AC-018 | M3-01 | M3-04、M3-P01 | ARCHITECT_DERIVED | 复盘及证据 |
| AC-019 | M3-01 | M3-P01 | ARCHITECT_DERIVED | 查询与 CSV |
| AC-020 | M3-01 | M1-02、M1-04、M3-P01 | **ADJUDICATED**（B7 裁定：M1-02 只交付快照侧前提） | Review 与导出 |
| AC-021 | M3-02 | M3-P01 | ARCHITECT_DERIVED | 诊断和策略 |
| AC-022 | M3-02 | M3-P01 | ARCHITECT_DERIVED | 数值断言 |
| AC-023 | M3-03 | （无） | **SOLO** | 计划和结果 |
| AC-024 | M3-02 | M3-04 | ARCHITECT_DERIVED | API、试算页 |
| AC-025 | M4-01 | M4-03、M4-P01 | ARCHITECT_DERIVED | 报告及下载 |
| AC-026 | M4-01 | M4-P01 | ARCHITECT_DERIVED | 报告链、制品 |
| AC-033 | M3-01 | M3-04 | ARCHITECT_DERIVED | 计算和问答 |

`ARCHITECT_DERIVED` 尚未由 Q 判定档确认，卡内引用时须保留该 confidence 字样，不得写成「已裁定」。
范例写法见 `orchestrator/tasks/M0-04.md` 的 AC-031 `cross_ref（primary owner = M5-01）` 段。

## 3. 关联 UI 页面（cross_ref 用；小节行号四卡结构一致）

六个 UI 文件均为 40–44 行，小节行号固定：`## 页面结构`:7、`## 字段和绑定`:16–18、
`## 操作、接口与反馈`:23–26、`## 页面状态与边界`:30–34、`## 验收与衔接`:35–39。
- M3-01 → `ui/UI-17-strategy-review.md`（44 行）；AC-019 另涉 `ui/UI-26-evidence-export.md`
- M3-02 → `ui/UI-18-diagnosis.md`（43 行）、`ui/UI-20-estimate.md`（40 行）
- M3-03 → `ui/UI-19-business-ask.md`（43 行）
- M4-01 → `ui/UI-21-report-list.md`（40 行）、`ui/UI-22-report-detail.md`（43 行）

`product/TRACEABILITY.md`（118 行）的「47 个手册操作点」已把 AC 与 UI 绑定，可直接引用的映射：
AC-018←手册 1.1/1.2/1.11；AC-019←1.5/1.6/1.7/1.8；AC-020←1.11；AC-021←3.8；AC-022←3.9/3.10/3.11；
AC-023←3.1/3.3/3.4/3.5/3.7；AC-024←4.1；AC-025←3.6/6.1/6.2/6.3/6.4；AC-026←6.5/6.9；AC-033←（计算侧，无单点）。
**页面呈现面一律记 cross_ref，不得当 primary**（账本 `acceptance.primary_owner.basis` 明载）。

## 4. spec 架构文件小节行号图（写 `inputs.specs` 时按行区间引用，禁整读）

`architecture/ANALYTICS.md`（56 行）：`## 指标与范围`:3、比较基准表:9–11、`## 复盘输出`:18、
`## 异常和归因`:26、`## 业务问答`:42 → M3-01 读 3–25 与 18–25；M3-02 读 26–41；M3-03 读 42–56。
`architecture/REPORTS.md`（41 行）：`## 报告数据与版本`:3、七段章节表:7–18、`## 签认和更正`:19、
`## 行动闭环`:23、`## 导出`:36 → M4-01 全文 41 行可整读（小文件）。
`architecture/DOMAIN.md`（44 行）：`## 唯一标识和精度`:3、`## 对象与修改`:11、
`## 数据库迁移约定`:26、`## 内容摘要的固定投影`:32 → 四卡按需读 3–25 与 32–44。
`architecture/API.md`（40 行）：`## 请求与响应`:5、`## 错误分类`:18（**code 唯一权威枚举 = 第 20–29 行，
20 个 code，D-019 已更正为 20 不是 21**）、`## 主要操作关系`:33。
`architecture/JOBS.md`（33 行）：`## 接口约定`:3、状态机迁移表:9–20、`## 写入与进程恢复`:21、`## 验收`:27
→ M3/M4 的 202 端点全部依赖 M0-04 的作业底座，卡内须写 `deps` 之外的 `consumes: M0-04 公共件`。
`architecture/DATA.md`（57 行）：`## 导入通道`:3、`## 映射和标准表`:13、`## 去重和可比性`:27、
`## 渠道事件重算`:35、`## 更正和发布边界`:50 → M3-01 的口径切换读 27–49。
`architecture/OPERATIONS.md`（27 行）：`## 会话和作用域`:3、`## 文件处理`:9、`## 运行与备份`:13。
`framework/PYTHON.md`（12 行）：全文可整读。
月报增量（v1.0.1）：`DELTA/architecture/ANALYTICS.append.md`（62 行，小节 1–7 在 5/13/22/29/41/49/57 行）
与 `DELTA/architecture/MONTHLY-REVIEW.md`（68 行，`## 1. 扩展数据与发布`:5、`## 2. 接口和结果`:24、
`### 改进项与指标证据绑定`:51、`## 3. 报告正文、签认、补数`:57）→ **四卡都必须预留月报扩展点**
（M3-P01/M3-P02/M4-P01 是月报任务，`AC-MR-*` 由它们 own；本批 4 卡只留扩展点、不实现月报逻辑）。

fixtures（字节数为编排器实算；**>20 KB 一律禁整读**）：
`fixtures/analytics-golden.json` 3277（M3-01 黄金值，可整读）、`fixtures/metric-dictionary.json` 9230（可整读）、
`fixtures/api-examples.json` 15919（可整读，DTO 样本）、`fixtures/cases/golden-cases.json` 21847（**禁整读**）、
`fixtures/questions.json` **131231**（60 条问法计划，**严禁整读**；只允许用 python 定点抽 `id` 列表与条数）、
`fixtures/banks/bank-a.json` 147272 / `bank-b.json` 291343（**严禁整读**）。

## 5. 手册必读区间（只读这 5 段，合计约 142 行；整册 758 行禁整读）

`docs/delivery/LONG-HORIZON-ORCHESTRATION.md`（v1.7，758 行）：
- §3.2 任务卡模板：**174–204 行**
- §6.3 硬规则（优先于评分，强制 max 触发项）：**312–333 行**
- §6.4 「max 设计 + flash 量产」配对模式（含四列档位表示例）：**334–383 行**
- §15.5 成本账本必填（档位表唯一依据、禁凑配比、越限如实记账）：**656–679 行**
- §15.6 关键路径循环上限与前置策略：**680–694 行**

## 6. 卡的硬格式约束（由守护测试机器判定，违反即红；实测自两个测试文件）

`tests/unit/test_task_card_narrative.py`（D-018）：
1. `head` ≤ **60** 行（口径：卡首 → 「子任务档位表」表头行之前，按原始行数计）；
2. `tail` ≤ **40** 行（口径：档位表最后一行 → 卡尾，含 U 项与裁定追注）——**本批 4 张新卡不享受
   `LEGACY_TAIL_ANNOTATED` 豁免**（该豁免只含 M0-02/M0-03），tail 必须真达标；
3. `total` ≤ **200** 行（整卡绝对兜底）；
4. 表头必须**逐字**等于 `| 子任务 | 档位 | 预估 token | 产出 |`（四列，缺「预估 token」即违反 §6.6）；
5. 无档位表的卡只允许是 `LEGACY_NO_TABLE = {M0-01, M0-P01}`，新卡必须有表。

`tests/unit/test_task_cards.py`（D-016）：
1. 任务总数分母钉死 **29**；
2. `KNOWN_MISSING` 必须与实际缺口**双向**对账：补齐 M3-01/M3-02/M3-03/M4-01 四张后，
   必须从 `KNOWN_MISSING` 移除这四个 id（**17 → 13**），不移除即红（`recovered` 分支）；
3. 磁盘上不得出现 `state.json` 不认识的任务卡（孤儿）——**只准建这 4 个文件名**；
4. 非历史卡必含字面量 `scope_allow`、`scope_deny`、`outputs`、`子任务档位表`。

档位表内容要求（§15.5 / §6.6 / C10）：
- 每个 `qwen3.8-flash` 子任务必须在行内标注「低复杂度：<理由>」，理由须落到
  「按已冻结签名机械展开/逐字段样板填充，无新算法、无跨模块判断，无 §6.3 强制 max 触发项」这一类可审计措辞；
- **禁为凑配比降档或机械拆分**（§15.5）。真低复杂度才允许拆，且逐条注明理由；
- 表下必须自证：flash 子任务占比 ≥60%、flash token 占比 ≤35%、max 合计 ≤200k、flash 合计 ≤60k、
  单个 flash 子任务上限；命中 §6.3 强制 max 的子任务（并发/租约、资金与比率计算、跨模块一致性不变量、
  状态机与事务边界）**不得降档**，如因此使 60% 不达标，照实写「不达标 + 理由 + 回补计划」，禁凑数；
- `dispatch:` 段必须写明「spawn 时显式填 model，省略即继承父模型＝静默降档」与
  `loop_cap: 2 轮`（四卡均 `critical=true` / `slack=0`，§15.6 第 1 条：关键路径 L 循环由 3 收紧为 2）。

## 7. 已知陷阱（必须写成 U 项交编排器裁定，禁自行决定）

1. **28 张表里没有 `questions` / `diagnoses` / `reviews` / `estimates` / `metrics` 表**（实测表清单：
   workspaces、artifacts、activities、evidence、activity_bindings、rule_versions、source_mappings、imports、
   import_files、snapshots、cases、thresholds、analysis_results、runs、run_cases、candidates、preflights、
   preflight_rows、receipts、reports、actions、action_followups、report_actions、exports、jobs、
   object_evidence、idempotency、audit；6 个显式索引：cases_one_confirmed_child、jobs_ready、
   snapshots_lookup、rules_activity、analysis_snapshot、actions_due）。
   → M3-01/02/03 的结果落点只能是 `analysis_results` 或 `artifacts`；M3-03 的「问法计划」在库里无表。
   **这是真实缺口，必须写成 U 项**（可选处置：复用 `analysis_results.kind`／落 `artifacts`／提 CR 补表），
   禁在卡里假定一张不存在的表，也禁自行提 CR（`orchestrator/change-requests/**` 不在你的写权限内）。
2. `migrations/**` 已由 M0-02 首迁交付并冻结，四卡一律 `scope_deny`，不得新增迁移。
3. `contracts/openapi.json` 为活契约 v1.0.1，**CR-002/ADR-006 已移除 `listWorkspaces.status`**；
   `WORKSPACE_STATUS_WHITELIST` 与 `422 INVALID_SCOPE`（针对 `/query/status`）的过渡分支已取消、不得实现、不得写用例期望。
4. Problem `code` 的唯一权威枚举 = `architecture/API.md` 第 20–29 行共 **20** 个（含 429 `JOB_CAPACITY`），
   卡内不得发明 code；`type` 方案见 ADR-005（`urn:campaignlab:problem:` + code.lower()）。
5. 领域不变量（四卡同）：只用 `spec/**/fixtures/` 合成数据；显式时钟（禁系统当前时间做领域计算、
   禁 `sleep` 固定时长）；金额＝分整数；比率＝十进制字符串；时区 Asia/Shanghai；AC 编号只引原文。
6. ops 归属为编排器按「path 前缀 + `state.json` scope 文件名」初判（第 1 节）。若你发现某 operationId
   应归别的任务（例如导出类 `createExport`/`downloadExport` 与 AC-019「导出明细」的归属），
   **写成 U 项**，禁自行改切片或 state.json。

## 8. 交付清单与自检（禁 git 写；自检一律用纯 `python3`）

产出（4 个文件 + 1 处修改）：
`orchestrator/tasks/M3-01.md`、`M3-02.md`、`M3-03.md`、`M4-01.md`，
以及 `tests/unit/test_task_cards.py` 的 `KNOWN_MISSING`（移除这 4 个 id，17 → 13）。

自检命令（全部期望 rc=0，逐条贴命令 + rc，禁「全部通过」式总括）：
1. `python3 -m pytest -q tests/unit/test_task_cards.py tests/unit/test_task_card_narrative.py`
   —— 若环境不允许跑 pytest，改用纯 python3 复算 head/tail/total/表头四项与 KNOWN_MISSING 双向对账，并贴出实测数字；
2. 逐卡实测 `head` / `tail` / `total` 三个行数与表头逐字比对结果（口径见第 6 节）；
3. 逐卡实测档位表的 flash 子任务占比、flash token 占比、max 合计、flash 合计（**由脚本算，禁手填**）；
4. 实测 `orchestrator/tasks/*.md` 文件名集合 == `state.json` 的 29 个任务 id 中去掉 `KNOWN_MISSING`(13) 的集合；
5. 回报格式：每张卡一行 `<id>: head=? tail=? total=? 表头=OK flash_tasks=?/? flash_tokens=?k/?k max_total=?k U项=n`，
   末尾附**本任务实际消耗 token 自报值**（唯一内容口径，缺失记 null、禁估算）。
