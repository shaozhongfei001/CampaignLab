# D-016 补卡批次 3 · 预抽上下文摘要（编排器产出 · Lane T 只读）

生成时间：2026-11-13T07:56:00+08:00 · 产出方：编排器（O lane） · 消费方：D-016 批次 3 补卡 lane（`qwen3.8-flash`）

## 为什么有这份文件

批次 1（8 张卡）实测 181k、`over_cap=true`（越 flash 60k 上限 3.02×）；批次 2 降到 4 张 + 预抽上下文后实测 50k（12.5k/卡，降 45%）。
本批沿用同一纠正措施（手册 §15.5 / `budget.guardrail_status.corrective_action`），**4 张卡，目标 ≤45k**。

**硬规则：本文件是 Lane T 的唯一 spec/手册入口。** 除第 5 节列出的精确行区间与第 1 节的 4 份切片（且只能按第 1.1 节的定点抽取配方按键取）外，
禁止整读 `spec/**`、`contracts/openapi.json`（443309 B）、`docs/delivery/LONG-HORIZON-ORCHESTRATION.md`（785 行）、`orchestrator/state.json`（约 190 KB）。
需要本文件未覆盖的信息时，**写进 U 项交编排器裁定，不得自行去读大文件**。

## 0. 本批 4 张卡（数值实测自 `state.json`，禁改写）

| 卡 | lane | tier_planned | deps | depth | height | slack | critical | AC（`acs` 原文） | 标题建议 |
|---|---|---|---|---|---|---|---|---|---|
| M4-02 | S | mixed | M2-03、M4-01 | 10 | 5 | 0 | true | AC-027、AC-028、AC-030 | 行动闭环、复核记录与导出制品 |
| M4-03 | F | mixed | M0-03、M0-04、M4-01、M4-02 | 11 | 4 | 0 | true | AC-025、AC-028、AC-030 | 报告与证据页面、回拨闭环走查 |
| M3-P01 | D | max | M1-P01 | 7 | 4 | 4 | false | AC-MR-03、AC-MR-04、AC-MR-05、AC-MR-06、AC-MR-07、AC-MR-08、AC-008、AC-018、AC-019、AC-020、AC-021、AC-022 | 全行月报复算、三月趋势与总分行去重 |
| M1-P01 | D | max | M0-04、M1-01、M1-02 | 6 | 5 | 4 | false | AC-MR-01、AC-MR-02、AC-MR-10、AC-005、AC-006、AC-007 | 月报输入接入、等价 CSV 归一与原子发布 |

`state.json` 实测 `gates`（**卡内 gate 必须逐字承接这些字符串**，禁转述改写；AC 类 gate 的编号另按第 2 节引原文）：
- **M4-02**（4 条）：`AC-027`；`AC-028`；`AC-030`；`导出制品原子且可校验`
- **M4-03**（2 条）：`AC-025 至 AC-028、AC-030 页面侧`；`回拨闭环 Playwright 证据`
- **M3-P01**（7 条）：`AC-MR-03 三月与范围桥（7/4/6 户等黄金值）`；`AC-MR-04 比较边界（semantic_key 变更/全月缺失/跨年/同名异义/已覆盖零值/月中）`；`AC-MR-05 双覆盖与分行参与`；`AC-MR-06 渠道容量（容量=0/使用=0/超额/缺容量/语义键变化）`；`AC-MR-07 客群与产品（未知新老客标签、未声明保险余额）`；`AC-MR-08 总分行去重（同客户多渠道/重复活动/无法核实交集）`；`monthly-golden.json 全量比对 + 原 AC-008、018-022 回归`
- **M1-P01**（5 条）：`AC-MR-01 标准接入（含等价 CSV 复验、旧 A/B 快照请求月报的兼容）`；`AC-MR-02 输入负例与授权（重复客户月/重复产能键/缺覆盖客户/未知分行/覆盖声明冲突）`；`AC-MR-10 输入侧：修订竞争与不可变旧快照`；`原 AC-005/006/007 回归`；`契约门禁 check_contracts.py check 仍为 PASS（不得偷改活契约）`

`state.json` 实测 `scope`（＝`scope_allow` 的路径字面量来源；A5 裁定：以卡字面量为准，`X/**` 与 `X/` 语义等价、统一写 `X/`，`allow∩deny` 必须为空）：
- **M4-02**：`src/campaignlab/domain/action/`、`src/campaignlab/infra/audit/`、`src/campaignlab/api/actions.py`、`tests/domain/action/`、`tests/integration/audit/`
- **M4-03**：`web/src/pages/report/`、`web/src/pages/evidence/`、`web/tests/unit/report/`、`web/tests/e2e/callback/`
- **M3-P01**：`src/campaignlab/domain/monthly/`、`src/campaignlab/api/monthly_reviews.py`、`tests/domain/monthly/`、`tests/golden/monthly/`、`evidence/monthly/M3-P01/`
- **M1-P01**：`src/campaignlab/domain/monthly_ingest/`、`src/campaignlab/api/monthly_imports.py`、`tests/domain/monthly_ingest/`、`tests/golden/monthly_ingest/`、`evidence/monthly/M1-P01/`

**M4-02 另有 `scope_transferred_out`（必须写进卡的 `scope_deny` 或至少在 U 项说明，禁再认领）**：
- `src/campaignlab/api/evidence.py` → 已转 **M1-03**（2026-11-13T04:25:00+08:00）。理由原文：A1 裁定：evidence 的 HTTP 入口归 M1-03；M2-03 相关证据 deferred_to M2-04。双 owner 会导致两 lane 同写一文件

`scope_deny` 固定项（四卡同）：`spec/**`、`contracts/**`、`migrations/**`、`scripts/**`、`orchestrator/state.json`、`orchestrator/defects/**`、`orchestrator/change-requests/**`、
其他任务的 `src/campaignlab/domain/**` 子目录、`evidence/M0/**`。**M4-03 另须 deny `src/**`（纯前端卡）**；M4-02/M3-P01/M1-P01 另须 deny `web/**`。
**交付必需落点若不在上述 `scope` 内**（如 `orchestrator/handoff/<id>-design.md`、`evidence/M4/<id>/**`、`evidence/monthly/<id>/**`、`evidence/M4/summaries/<id>.md`、
`tests/unit/test_<x>_dto.py`、`src/campaignlab/api/exports.py`），**必须显式补进 `scope_allow` 并写成 U 项说明**（依 A5／D-008 体例，编排器随后同步 state.json）。

## 1. 已预生成的契约切片（PRE-3 三方校验用；本任务只读，**禁自行重切**）

编排器已于 2026-11-13T07:48:00+08:00 用 `scripts/contract_slice.py --depth 5`（D-020 修复后的默认值）生成，四份 `missing=[]`、`truncated_schemas=[]`、`spec_version=1.0.1`：

| 切片 | own sha16 | own bytes | operations（n） | ddl 键 | pages | acceptance_rows |
|---|---|---|---|---|---|---|
| `orchestrator/handoff/M4-02.slice.json` | `febd8628e02b0d02` | 82954 | createAction、createExport、downloadExport、getAction、getExport、listActions、listAudit、listExports、reviewAction、transitionAction、updateAction（11） | action_followups、actions、actions__indexes、artifacts、audit、evidence、exports、jobs、jobs__indexes、receipts、report_actions、reports | UI-23、UI-24、UI-26 | 3 |
| `orchestrator/handoff/M4-03.slice.json` | `6fb6ff3bbf294c04` | 106933 | createExport、downloadExport、getAction、getEvidence、getExport、getReport、listActions、listEvidence、listExports、listReports、reviewAction、signReport、transitionAction（13） | action_followups、actions、actions__indexes、artifacts、evidence、exports、jobs、jobs__indexes、report_actions、reports | UI-21、UI-22、UI-23、UI-24、UI-26 | 3 |
| `orchestrator/handoff/M3-P01.slice.json` | `30c776e4e6a51bbd` | 83931 | createReport、getEvidence、getJob、getReport、getReview、listEvidence、runReview（7） | analysis_results、analysis_results__indexes、artifacts、audit、evidence、imports、jobs、jobs__indexes、object_evidence、snapshots、snapshots__indexes | UI-17 | 12 |
| `orchestrator/handoff/M1-P01.slice.json` | `2f80df94417b2efa` | 111801 | attachImportFile、configureImport、correctSnapshot、createImport、getImport、getSnapshot、listImports、listSnapshots、publishImport、validateImport（10） | artifacts、audit、evidence、import_files、imports、jobs、jobs__indexes、object_evidence、snapshots、snapshots__indexes | UI-06、UI-07、UI-08 | 6 |

四份切片的 `source.openapi` 段均为 `{"path": "contracts/openapi.json", "bytes": 443309, "sha16": "592571099d638251"}`。
**指纹与字节数的权威现值见 `state.json → resume.self_check_gates_rc0.counts.live_openapi_sha16` / `.live_openapi_bytes`，禁写死进卡（D-012/D-013/D-014）**；
卡内一律写「以 state.json counts 为准」的指向句。上表数值仅为编排器本次预生成的留痕。

### 1.1 定点抽取配方（**本批切片 83–112 KB，是批次 2 的 3–6 倍，整读必越限**）

- 禁 `cat` 整份切片、禁 `json.load` 后整体 `print`。整读一份 ≈25–35k token，四份即超 flash 单任务 60k 上限。
- 只按 key 抽，逐次只取需要的那一个：`spec_version`、`source`、`list(operations)`、`list(ddl)`、`operations.<opId>.{method,path,parameters,request_body,responses}`、`acceptance_rows[]`、`pages.<UI-xx>`、`ddl.<table>`、`truncated_schemas`。
- AC 原文**优先读 `acceptance_rows`**（已含四元组：编号 / 输入及操作 / 通过条件 / 主证据），不要再去读 `qa/ACCEPTANCE.md` 或月报 append 清单。
- 写卡时**禁把切片内容大段抄进卡**（卡有 head/tail/total 行数上限，见第 6 节）；只写「指向切片哪个 key」的引用句。

## 2. AC 原文行号与 primary owner

基座 `spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md`（52 行，表体行号规律＝`AC-0NN` → 第 `NN+8` 行）：
`AC-005`→13、`AC-006`→14、`AC-007`→15、`AC-008`→16、`AC-018`→26、`AC-019`→27、`AC-020`→28、`AC-021`→29、`AC-022`→30、`AC-025`→33、`AC-027`→35、`AC-028`→36、`AC-030`→38。
月报 `spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/qa/CampaignLab-Review-Acceptance-Checklist.append.md`（21 行）：
`AC-MR-01`→7、`02`→8、`03`→9、`04`→10、`05`→11、`06`→12、`07`→13、`08`→14、`09`→15、`10`→16、`11`→17、`12`→18。
**D-011：卡内引用 AC 只引编号 + 原文，禁转述改写**（D-008 就是转述错误立的单）。

`primary_owner`（实测自 `state.json → acceptance.primary_owner`，卡内 `cross_ref` 必须照此写；页面呈现面一律记 cross_ref，不得当 primary）：

| AC | primary | cross_ref | confidence |
|---|---|---|---|
| AC-027 | M4-02 | M4-P01 | ARCHITECT_DERIVED |
| AC-028 | M4-02 | M4-03、M4-P01 | ARCHITECT_DERIVED |
| AC-030 | M4-02 | M4-03、M4-P01 | ARCHITECT_DERIVED |
| AC-025 | M4-01 | M4-03、M4-P01 | ARCHITECT_DERIVED |
| AC-MR-03 | M3-P01 | M3-P02、M5-P01 | ARCHITECT_DERIVED |
| AC-MR-04 | M3-P01 | M3-P02、M5-P01 | ARCHITECT_DERIVED |
| AC-MR-05 | M3-P01 | M3-P02、M5-P01 | ARCHITECT_DERIVED |
| AC-MR-06 | M3-P01 | M3-P02、M5-P01 | ARCHITECT_DERIVED |
| AC-MR-07 | M3-P01 | M3-P02、M5-P01 | ARCHITECT_DERIVED |
| AC-MR-08 | M3-P01 | M3-P02、M5-P01 | ARCHITECT_DERIVED |
| AC-008 | M1-02 | M3-P01 | ARCHITECT_DERIVED |
| AC-018 | M3-01 | M3-04、M3-P01 | ARCHITECT_DERIVED |
| AC-019 | M3-01 | M3-P01 | ARCHITECT_DERIVED |
| AC-020 | M3-01 | M1-02、M1-04、M3-P01 | ADJUDICATED |
| AC-021 | M3-02 | M3-P01 | ARCHITECT_DERIVED |
| AC-022 | M3-02 | M3-P01 | ARCHITECT_DERIVED |
| AC-MR-01 | M1-P01 | M5-P01 | ARCHITECT_DERIVED |
| AC-MR-02 | M1-P01 | M5-P01 | ARCHITECT_DERIVED |
| AC-MR-10 | M4-P01 | M1-P01、M5-P01 | ARCHITECT_DERIVED |
| AC-005 | M1-01 | M1-04、M1-P01 | ARCHITECT_DERIVED |
| AC-006 | M1-01 | M1-P01 | ARCHITECT_DERIVED |
| AC-007 | M1-02 | M1-P01 | ARCHITECT_DERIVED |

`ARCHITECT_DERIVED` 尚未由 Q 判定档确认，卡内引用时须保留该 confidence 字样，不得写成「已裁定」。范例写法见 `orchestrator/tasks/M0-04.md` 的 AC-031 段。

**⚠ 已实测到的 owner 冲突（编排器已立账，卡内照此写、不要自行裁定）**：`AC-MR-10` 的 primary 是 **M4-P01**、cross_ref 才是 `[M1-P01, M5-P01]`，
但 `state.json.tasks["M1-P01"].acs` 含 `AC-MR-10`、`gates` 含「AC-MR-10 输入侧：修订竞争与不可变旧快照」。
→ **M1-P01 卡内只承担 cross_ref（输入侧前提）**，禁写成 primary；并写成 U 项。已记 `resume.round5_predispatch.ac_mr10_owner_conflict`。

## 3. 关联 UI 页面（`cross_ref` 用；小节行号已实测）

九个基座 UI 文件的实测小节行号（`## 页面结构` / `## 字段和绑定` / `## 操作、接口与反馈` / `## 页面状态与边界` / `## 验收与衔接`）：

| 文件 | 行数 | 页面结构 | 字段和绑定 | 操作接口与反馈 | 页面状态与边界 | 验收与衔接 |
|---|---|---|---|---|---|---|
| `ui/UI-06-import-list.md` | 40 | 7 | 16 | 23 | 30 | 35 |
| `ui/UI-07-import-detail.md` | 44 | 7 | 17 | 25 | 34 | 39 |
| `ui/UI-08-snapshots.md` | 41 | 7 | 16 | 24 | 31 | 36 |
| `ui/UI-17-strategy-review.md` | 44 | 7 | 18 | 26 | 34 | 39 |
| `ui/UI-21-report-list.md` | 40 | 7 | 16 | 23 | 30 | 35 |
| `ui/UI-22-report-detail.md` | 43 | 7 | 17 | 25 | 33 | 38 |
| `ui/UI-23-action-list.md` | 40 | 7 | 16 | 23 | 30 | 35 |
| `ui/UI-24-action-detail.md` | 42 | 7 | 17 | 24 | 32 | 37 |
| `ui/UI-26-evidence-export.md` | 41 | 7 | 17 | 24 | 31 | 36 |

按卡的页面归属：**M4-02** → UI-23、UI-24、UI-26（后端侧只承担契约与制品，页面呈现记 cross_ref）；
**M4-03** → UI-21、UI-22、UI-23、UI-24、UI-26（`web/src/pages/report/`、`web/src/pages/evidence/`，「回拨闭环」= UI-24 + UI-22）；
**M3-P01** → UI-17；**M1-P01** → UI-06、UI-07、UI-08。

### 3.1 月报页面增量（`--ui` 索引**不覆盖**，必须按行区间定点读原文）

`scripts/contract_slice.py` 第 208 行注释明载「页号索引取活契约 `pages.json`；页面 markdown 原件仍只在 `BASE/ui/` 下」，
故 **`spec/…-Patch-v1.0.1…/ui/MONTHLY-PAGES.md` 不会进任何切片的 `pages` 段**。该文件仅 43 行、可整读，小节行号实测：
`## UI-17 策略复盘 · 全行月度经营复盘`:5–20、`## UI-21 报告列表与新建`:21–24、`## UI-22 报告审阅、签认与修订`:25–32、`## 关联页面增量`:33–43（表含 UI-07/UI-08/UI-24/UI-26 的新分支）。
涉月报页面的三卡（M4-03、M3-P01、M1-P01）必须把这些行区间写进 `inputs.specs`。

`product/TRACEABILITY.md`（117 行；`## 55 个材料点位`:5、`## 47 个手册操作点`:65）已把 AC 与 UI 绑定，本批可直接引用的映射：
AC-025←手册 3.6/6.1/6.2/6.3/6.4；AC-027←（行动闭环段，按 65 行起表查）；AC-028←（复核段）；AC-030←（导出段）。
**只按行区间查 65 行起的表，禁整读 117 行**；查不到就写 U 项，禁臆造手册点位号。

## 4. spec 架构文件小节行号图（写 `inputs.specs` 时按行区间引用，禁整读）

基座 `spec/CampaignLab-SDD-v1.0/`（行数实测）：
- `architecture/DATA.md`（56）：导入通道:3、映射和标准表:13、去重和可比性:27、渠道事件重算:35、更正和发布边界:50 → **M1-P01 读 3–26 与 50–56**
- `architecture/DOMAIN.md`（43）：唯一标识和精度:3、对象与修改:11、数据库迁移约定:26、内容摘要的固定投影:32 → **M3-P01/M1-P01 读 3–25 与 32–43**
- `architecture/REPORTS.md`（40）：报告数据与版本:3、签认和更正:19、行动闭环:23、导出:36 → **M4-02 读 19–40；M4-03 读 3–18 与 36–40**
- `architecture/API.md`（39）：请求与响应:5、错误分类:18（**Problem code 权威表在 22–29 行第 2 列，以「、」分隔，共 20 个**）、主要操作关系:33 → 四卡按需只读 18–32
- `architecture/ANALYTICS.md`（56）：指标与范围:3、复盘输出:18、异常和归因:26、业务问答:42 → **M3-P01 读 3–25**
- `framework/FRONTEND.md`（18）：组件和接口:3、界面实现:9 → **M4-03 可整读（18 行）**；`ui/COMMON.md`（39）同

补丁 `spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/`：
- `architecture/MONTHLY-REVIEW.md`（68）：扩展数据与发布:5–23、接口和结果:24–50、改进项与指标证据绑定:51–56、报告正文/签认/补数:57–68
  → **M1-P01 读 5–23；M3-P01 读 24–68；M4-02 读 51–68（`createAction → reviewAction` 与 `createExport` 两行在 24–50 的表内，故 M4-02 也需 24–50）**
- `architecture/ANALYTICS.append.md`（62）：1 计算范围和数据就绪:5、2 三月触客趋势与覆盖变化:13、3 参与度与双覆盖率:22、4 渠道容量与产能:29、5 客群结构与产品产能:41、6 总分行重复触达与产能核对:49、7 结论/签认/复核:57 → **M3-P01 全文 62 行可整读**
- `fixtures/MONTHLY-FIXTURES.md`（26；`## 从导入到下期复核`:17）→ **M3-P01 与 M1-P01 全文可整读**
- `framework/DELIVERY-PATCH.md`（24；交付次序:3、回执与边界:19）→ 四卡按需读 3–18
- `reference/EVIDENCE-AND-DECISIONS.md`（37；来源和权限:3、从报告到需求和验收:13、设计决定 MR-D01 至 MR-D04:25、行内试点待核:34）→ **M3-P01 读 25–37**
- `contracts/monthly-contract-delta.json` → **禁整读**，其 `additions` 的 11 项已由编排器摘要在本文件第 7 节陷阱 1

## 5. 手册必读区间（只读这 5 段，合计约 142 行；整册 785 行禁整读）

`docs/delivery/LONG-HORIZON-ORCHESTRATION.md`（v1.8，785 行；v1.8 只在 §15.6 之后追加 §15.7–§15.11，故下列区间与批次 2 完全一致、未漂移）：
- §3.2 任务卡模板：**174–204 行**
- §6.3 硬规则（优先于评分，强制 max 触发项）：**312–333 行**
- §6.4 「max 设计 + flash 量产」配对模式（含四列档位表示例）：**334–383 行**
- §15.5 成本账本必填（档位表唯一依据、禁凑配比、越限如实记账）：**656–679 行**
- §15.6 关键路径循环上限与前置策略：**680–694 行**

## 6. 卡的硬格式约束（由守护测试机器判定，违反即红；实测自两个测试文件）

`tests/unit/test_task_card_narrative.py`（D-018）：
1. `head` ≤ **60** 行（口径：卡首 → 「子任务档位表」表头行之前，按原始行数计）；
2. `tail` ≤ **40** 行（口径：档位表最后一行 → 卡尾，含 U 项与裁定追注）——**本批 4 张新卡不享受 `LEGACY_TAIL_ANNOTATED` 豁免**（该豁免只含 M0-02/M0-03），tail 必须真达标；
3. `total` ≤ **200** 行（整卡绝对兜底）；
4. 表头必须**逐字**等于 `| 子任务 | 档位 | 预估 token | 产出 |`（四列，缺「预估 token」即违反 §6.6）；
5. 无档位表的卡只允许是 `LEGACY_NO_TABLE = {M0-01, M0-P01}`，新卡必须有表。

`tests/unit/test_task_cards.py`（D-016）：
1. 任务总数分母钉死 **29**；
2. `KNOWN_MISSING` 必须与实际缺口**双向**对账：补齐 M4-02/M4-03/M3-P01/M1-P01 四张后，必须从 `KNOWN_MISSING` 移除这四个 id（**13 → 9**），不移除即红（`recovered` 分支）；
3. 磁盘上不得出现 `state.json` 不认识的任务卡（孤儿）——**只准建这 4 个文件名**；
4. 非历史卡必含字面量 `scope_allow`、`scope_deny`、`outputs`、`子任务档位表`。

档位表内容要求（§15.5 / §6.6 / C10）：
- 每个 `qwen3.8-flash` 子任务必须在行内标注「低复杂度：<理由>」，理由须落到「按已冻结签名机械展开/逐字段样板填充，无新算法、无跨模块判断，无 §6.3 强制 max 触发项」这一类可审计措辞；
- **禁为凑配比降档或机械拆分**（§15.5）。真低复杂度才允许拆，且逐条注明理由；
- 表下必须自证：flash 子任务占比 ≥60%、flash token 占比 ≤35%、max 合计 ≤200k、flash 合计 ≤60k、单个 flash 子任务上限；命中 §6.3 强制 max 的子任务（并发/租约、资金与比率计算、跨模块一致性不变量、状态机与事务边界）**不得降档**，如因此使 60% 不达标，照实写「不达标 + 理由 + 回补计划」，禁凑数；
- **M3-P01 与 M1-P01 的 `tier_planned` 是 `max`**（月报分母/交集/去重/覆盖率口径、`DISTINCT_CUSTOMER` 与扩展粒度、`SOURCE_JSON` 与等价 CSV 归一、原子发布制品均属 §6.3 强制 max），
  两卡的 flash 子任务占比**很可能天然不达标 60%**——照实写「不达标 + 理由 + 回补计划」，**禁为凑配比把口径计算降档**；
- **M4-02 与 M4-03 的 `tier_planned` 是 `mixed`**，应能达标 60%（DTO/路由按冻结签名机械展开、参数化用例枚举、页面样板铺开、逐字段契约测试、证据采集属强制 flash）；
- `dispatch:` 段必须写明「spawn 时显式填 model，省略即继承父模型＝静默降档」与 `loop_cap`：
  **M4-02/M4-03 为 `2 轮`**（`critical=true`/`slack=0`，§15.6 第 1 条：关键路径 L 循环由 3 收紧为 2）；**M3-P01/M1-P01 为 `3 轮 + 1 轮 max 复审`**（`critical=false`/`slack=4`）。

## 7. 已知陷阱（必须写成 U 项交编排器裁定，禁自行决定）

1. **月报增量没有新增任何 operationId**（编排器实测）。活契约 80 个 operationId 全集里无 `*Monthly*`；`monthly-contract-delta.json` 的 `additions` 只有 11 项：
   2 个可选属性（`ReviewCreate.profile` 枚举 `["BANK_MONTHLY_V1"]`、`Review.monthly_review` → `$ref MonthlyReview`）+ 7 个 `Monthly*` schema
   （`MonthlyCapacity`/`MonthlyComparison`/`MonthlyOriginOverlap`/`MonthlyParticipation`/`MonthlyProduction`/`MonthlyReview`/`MonthlyTrend`）+ 2 个 source-json schema 节点；`version_update` 1.0.0→1.0.1。
   `MONTHLY-REVIEW.md:26` 原文明载「基座操作编号、响应头、作业类型、对象和路由沿用」。
   → **后果**：`state.json` 给 M3-P01 的 scope 含 `src/campaignlab/api/monthly_reviews.py`、给 M1-P01 的含 `src/campaignlab/api/monthly_imports.py`，
     但**契约里没有这两个文件对应的路由**（月报复盘走既有 `runReview`/`getReview` + `profile`；月报导入走既有 `createImport`/`attachImportFile`/`configureImport`/`validateImport`/`publishImport` + `map-monthly`）。
     必须写成 **U 项**，给出可选处置（① 该两文件为非路由的领域/DTO 模块，路由仍归 M3-01/M1-01；② scope 字面量需更正；③ 走 CR 加 op）。
     **禁在卡里发明 operationId、禁自行改契约或 state.json。**
2. **`AC-MR-10` 的 primary owner 是 M4-P01 而非 M1-P01**（见第 2 节 ⚠）。M1-P01 卡内只写 cross_ref + 输入侧前提，并写 U 项。
3. **`MONTHLY_INVALID_SCOPE` / `MONTHLY_REPORT_KIND_REQUIRED` 既不在活契约也不在冻结注册表** —— 已立 **D-022（MAJOR，OPEN_NEEDS_OWNER）**。
   实测：两串在 `contracts/openapi.json` 命中 **0**；`src/campaignlab/api/common.py` 的 `PROBLEM_CODES` 为 **20** 码、`MONTHLY_*` 命中 **0**。
   → M3-P01/M4-P01 相关卡内一律写「依 **D-022** 待裁，暂按选项 A 撰写（复用 `INVALID_SCOPE` / `VALIDATION_ERROR`，语义标签落 `Problem.detail` 与 `Issue.code`），**禁实现 `MONTHLY_*` code、禁扩注册表**」，并写 U 项。
4. **export 四 op 的交付归属必须在本批 M4-02 卡内落定**（`resume.card_gap.export_ops_unowned` 的 `action` 原文：「M4-02 补卡时明确落定 export 四 op 交付归属」）。
   实测：`createExport`/`downloadExport` 已被 `M3-01.md` 与 `M4-01.md` 引用；`getExport`/`listExports` 在既有 16 卡中**零引用**。
   → M4-02 卡的 `outputs` 与档位表必须逐个写明四 op 的归属；`src/campaignlab/api/exports.py` **不在**现 scope 内，必须显式补进 `scope_allow` 并写 U 项。
5. **A6 已裁定（不得重开）**：28 表无 `reviews`/`diagnoses`/`estimates`/`questions`；四类分析对象落 `analysis_results`（以 `kind` 判别）+ `artifacts`。
   **月报结果同样落 `analysis_results` + `artifacts`，不得新增表**（新增表＝改 `migrations/**` 与 28 表分母，属 CR；分母断言取 `ddl_compare.EXPECTED_TABLE_COUNT=28`）。
6. **A13 已裁定（不得重开）**：wave5 加串行前置 `M3-P01 → {M3-01, M3-02, M3-03}`，M3-P01 必须**先冻结月报指标注册签名**。
   → M3-P01 卡的 `outputs` 必须显式含「指标注册签名冻结件」（建议 `orchestrator/handoff/M3-P01-metric-registry.md`，须补进 `scope_allow` 并写 U 项）；
   并写 U 项要求编排器给 M3-01/M3-02/M3-03 三卡的 `deps` 追加 `M3-P01`（**这是 state.json 变更，你无权改**）。
7. **A9–A12 已裁定**：`JobStore` 是唯一写 `jobs` 表的模块；`application/worker.py` 的 `heartbeat(job_id, *, now)` 是唯一写 `jobs.lease_until` 的入口；
   `JOB_INTERRUPTED` **不是** `Problem.code`（只能放 `Issue.code`）；`api/app.py` 的挂载改动 ≤3 行且属 M0-04/S4。M4-02 的异步导出作业**只调用、不重建**。
8. **A7/A8 已裁定**：契约响应码全集**无 304**（前端不得写 304 特判）；`ApiError.kind` 前端自有词汇须是 20 个权威 code 的纯函数映射并有单测。M4-03 卡必须承接。
9. **`--ui` 页号索引不覆盖 `MONTHLY-PAGES.md`**（见第 3.1 节）。
10. Problem `code` 唯一权威 = `architecture/API.md` 第 22–29 行第 2 列（以「、」分隔）共 **20** 个：
    `BAD_REQUEST`、`BAD_CURSOR`、`SESSION_EXPIRED`、`ORIGIN_DENIED`、`ACCESS_DENIED`、`RESOURCE_NOT_FOUND`、`IDEMPOTENCY_CONFLICT`、`STATE_CONFLICT`、`VERSION_MISMATCH`、`STALE_CANDIDATE`、
    `SNAPSHOT_CONFLICT`、`ACTION_REVIEW_REQUIRED`、`REVISION_CONFLICT`、`PRECONDITION_REQUIRED`、`INPUT_TOO_LARGE`、`VALIDATION_ERROR`、`INVALID_SCOPE`、`EVIDENCE_REQUIRED`、`JOB_CAPACITY`、`INTERNAL_ERROR`。
    卡内不得发明 code；`type` 方案见 ADR-005（`urn:campaignlab:problem:` + `code.lower()`）。
11. `migrations/**` 已由 M0-02 首迁交付并冻结（28 表），四卡一律 `scope_deny`，不得新增迁移。
12. **CR-002/ADR-006 已移除 `listWorkspaces.status`**；`WORKSPACE_STATUS_WHITELIST` 与针对 `/query/status` 的 422 `INVALID_SCOPE` 过渡分支已取消、不得实现、不得写用例期望。
13. 领域不变量（四卡同）：只用 `spec/**/fixtures/` 合成数据（月报侧＝`fixtures/source-01-partial.json`/`source-02-backfilled.json`/`source-03-corrected.json`/`source-04-next.json`、`map-monthly.json`、`monthly-golden.json`、`csv-equivalent/{metadata.json,monthly_touch_slices.csv}`）；
    显式时钟（禁系统当前时间做领域计算、禁 `sleep` 固定时长）；金额＝分整数；比率＝十进制字符串；时区 Asia/Shanghai；AC 编号只引原文（D-011）。
14. **计数禁写死**（D-012/D-014）：卡内所有分母（切片 sha16/bytes、活契约 sha16/bytes、pytest 数、表数、码数）一律写「权威现值见 `state.json → resume.self_check_gates_rc0.counts.*`」的指向句。本文件第 1 节数值只是编排器本次预生成的留痕。
15. ops 归属为编排器按「path 前缀 + `state.json` scope 文件名」初判（第 1 节）。若你发现某 operationId 应归别的任务，**写成 U 项**，禁自行改切片或 state.json。

## 8. Archimedes（批次 2）缓置 U 项的逐条处置（编排器本轮已裁，卡内直接引用，不必重开）

批次 2 回收时 Archimedes 上报 **21** 项 U；编排器当轮裁定 **9** 项（归并为 6 条裁定条目，见 `resume.round4_adjudications.archimedes_D016_batch2`），
台账记 `deferred: 15`。**编排器本轮逐条对账复核：可追溯的未裁定项实为 12 项**（15 的口径把「D-008 同型 scope 同步」4 项执行与已裁定项混算），已据实更正台账并加注（不改写历史值）。12 项处置如下：

| # | 来源 | 问题 | 本轮处置 |
|---|---|---|---|
| 1 | M3-01/U-2 | `waves[5].note` 判 `infra/duckdb` 属公共件走 CR，与该卡 scope 含 `src/campaignlab/infra/duckdb/` 冲突 | **裁定**：维持「只经既有入口扩展、不改公共签名」。scope 含该目录＝可在目录内**新增**文件；**改既有公共签名或既有文件**才走 CR。M3-P01 卡按同一口径写 |
| 2 | M3-02/U-1 | 无 `diagnoses`/`estimates` 表且 `analysis_results.kind` 枚举不含 `estimate` | **裁定**：试算（`computeEstimate`）为**纯同步计算不落库**，只回响应体；若必须留痕则落 `artifacts`。**不得扩 `kind` 枚举**（属公共冻结件，走 CR）。M3-P01 月报结果落 `analysis_results(kind='monthly_review')`＋`artifacts` |
| 3 | M3-02/U-2 | 阈值「前后版本可回查」无承载（`thresholds` 无版本列、`listThresholds` 无版本参数） | **裁定**：以「多行 + `created_at` 时序 + `audit`」实现可回查，**不加列不加表**。`AC-021` 取证走 `listThresholds` 时序 + `listAudit` |
| 4 | M3-02/U-4 | `AC-024`「缺分母给缺项」与 M3-01「零分母 null」的统一口径归谁定义 | **裁定**：由 **M3-02** 定义（它是 `AC-024` 的 primary），M3-01 不回改。月报侧口径**由 M3-P01 定义**（`AC-MR-05`「零分母空值且组平均明确有效分行数」），M3-01/M3-02 不回改 |
| 5 | M3-02/U-5 | 月报「改进项与指标证据绑定」的上游绑定签名 | **裁定**：即 A13 的冻结件。`MONTHLY-REVIEW.md:51–56`（`### 改进项与指标证据绑定`）为权威原文，**由 M3-P01 的 S1 冻结签名**并落 `orchestrator/handoff/M3-P01-metric-registry.md`；M4-02 的 `createAction → reviewAction` 只消费不定义 |
| 6 | M3-03/U-1 | 60 条登记问法计划库内无表（实测 `state=CLARIFY` 仅 Q03/Q04、`plan` 为 null） | **裁定**：以 **夹具为登记权威源**（`spec/**/fixtures/`），库内只落**执行结果**（`analysis_results`＋`artifacts`），**不建计划表**。M3-P01 的月报指标注册同理走冻结件而非建表 |
| 7 | M3-03/U-2 | 「题述值仅作 claims」的 claims 无表 | **裁定**：只留 `audit`／`artifacts`，**不可查询**、不建表 |
| 8 | M3-03/U-3 | `AC-023` 为 SOLO，但 `ui/UI-19` 页面证据出具方未定 | **裁定**：页面证据归 **M3-04**（lane F，wave6）。M3-04 卡在本批**不交付**（批次 4），故本条只作登记；M4-03 卡按同一原则处理页面证据（自己出 Playwright 证据，`AC-025`/`AC-028`/`AC-030` 仍记 cross_ref） |
| 9 | M3-03/U-5 | `interpretQuestion`/`executeQuestion`/`getQuestion` 职责切分须按 `API.md:33` 原文确认 | **裁定**：以 `architecture/API.md` 第 33–39 行（`## 主要操作关系`）原文为准，卡内按行区间引用、禁转述。**与本批 4 卡无直接交集**，登记即可 |
| 10 | M4-01/U-2 | `reports.review_id` 外键指向 `analysis_results`，取数依赖 M3-01/U-1 | **裁定**：依 A6，`review_id` 指向 `analysis_results.id`（`kind='review'`）。**M3-P01 的月报 Review 同样落 `analysis_results`**，故 `reports.review_id` 对月报报告仍有效，无需加列 |
| 11 | M4-01/U-3 | 修订链唯一形态未定 | **裁定**：「补数出新行 + `previous_report_id` 指旧行」，旧行与其签认摘要**保留只读**。与 `MONTHLY-PAGES.md:25–32`（UI-22）及 `AC-MR-10` 原文一致。**M4-03 卡的 UI-22 版本链渲染按此口径写** |
| 12 | M4-01/U-5 | 「行动提示待复核」需写 `actions.needs_review`，但该表写权属 M4-02 | **裁定**：`actions` 表写权**唯一归 M4-02**；M4-01 只在 `reports`/`report_actions` 侧出提示。**M4-02 卡必须在档位表里显式认领 `actions`/`action_followups` 的写权，并写明「M4-01 不得写 `actions`」** |

**已裁定的 9 项（不必重开，只可引用）**：`U-28tables`（→A6）、`U-export`（→本文件陷阱 4）、`U-D008-scope`（→A5，编排器逐任务同步 state.json）、
`U-monthly-metric-signature`（→A13，本文件陷阱 6）、`U-6`（**不成立**：Aquinas 写 `web/src/main.ts` 等在 M0-03 卡第 19 行 `scope_allow` 授权内，指控源于 state.json scope 更窄，已按 A5 同步）、`U-tier-ratio`（→批次 3 沿用降批措施）。

## 9. 交付清单与自检（禁 git 写；自检一律用纯 `python3`）

产出（4 个文件 + 1 处修改）：`orchestrator/tasks/M4-02.md`、`M4-03.md`、`M3-P01.md`、`M1-P01.md`，
以及 `tests/unit/test_task_cards.py` 的 `KNOWN_MISSING`（移除这 4 个 id，**13 → 9**）。

自检命令（全部期望 rc=0，逐条贴命令 + rc，**禁「全部通过」式总括**）：
1. `python3 -m pytest -q tests/unit/test_task_cards.py tests/unit/test_task_card_narrative.py` —— 若环境不允许跑 pytest，改用纯 `python3` 复现两文件的 `_split()`/`_header_of()` 口径，复算 head/tail/total/表头四项与 `KNOWN_MISSING` 双向对账，并贴出实测数字；
2. 逐卡实测 `head`/`tail`/`total` 三个行数与表头逐字比对结果（口径见第 6 节）；
3. 逐卡实测档位表的 flash 子任务占比、flash token 占比、max 合计、flash 合计（**由脚本算，禁手填**）；
4. 实测 `orchestrator/tasks/*.md` 文件名集合 == `state.json` 的 29 个任务 id 去掉 `KNOWN_MISSING`(9) 的集合（即 **20** 张）；
5. 实测四卡 `CR=0`、`BOM=0`、`ends-LF=True`，且四份切片与 `state.json`、`handoff/**`、`spec/**`、`web/**` 的 `sha16+bytes` **未发生漂移**（你只读它们）；
6. `git status --porcelain` 完整输出 + 越界自证（本轮并发另有 S lane 写 `src/campaignlab/**`、F lane 写 `web/**`，**它们的变更不是你的**，逐条归因）；
7. 回报格式：每张卡一行 `<id>: head=? tail=? total=? 表头=OK flash_tasks=?/? flash_tokens=?k/?k max_total=?k U项=n`，末尾附**本任务实际消耗 token 自报值**（唯一内容口径，缺失记 null、禁估算）。

**禁**：git commit/push、sudo、`npm`/`node`/`vite`/`vitest`/`playwright`/`uv`/`mypy`/`ruff`（本任务只写 markdown，自检纯 `python3` 标准库即可）；
禁改 `spec/**`、`contracts/**`、`docs/**`、`orchestrator/state.json`、`orchestrator/defects/**`、`orchestrator/change-requests/**`、`tests/unit/test_task_card_narrative.py`。

---

## 10. 编排器自我更正（2026-11-13T08:38:00+08:00 · 纯增量追加，上文第 0–9 节字节不改写）

本节更正**编排器在本文件自身里犯的两处事实错误**，均由 D-016 批次 3 的 T lane（Locke）上报、编排器独立复核成立。
**四张卡未受污染**：Locke 恪守「不自行决定、写 U 项」，把两处都上报为 U 项（`M3-P01.md` U-2；四卡 U-8/U-6/U-9），卡内正文照实记录了冲突而非照抄错误裁定。

### ① 第 8 节第 2 项裁定里的 `analysis_results(kind='monthly_review')` 是编排器的臆断，**作废**

实测 `contracts/sqlite-v1.sql` 第 102 行：
`kind TEXT NOT NULL CHECK(kind IN ('comparison','review','diagnosis','question'))` —— **不含 `monthly_review`**。
编排器撰写第 8 节时**未核 DDL 的 CHECK 约束**即发明了枚举值，属未经取证的臆断（与 D-021 初稿「schema 不存在」同类过失，按用户偏好当场更正留痕）。

**更正后的裁定（A6 的正确落地形态，Round 5 起唯一依据）**：
- 月报 Review 结果落 `analysis_results` 时 **`kind` 取既有值 `'review'`**；
- 判别式为 **`input_json` 内的 `profile: "BANK_MONTHLY_V1"`**（`input_json` 有 `CHECK(json_valid(...))` 但**无枚举约束**，属非冻结面，可安全承载）；
- 大对象/制品照旧落 `artifacts`（其 `kind` 的 CHECK 为 `('SOURCE','CLAUSE','COMPUTATION','TRACE','PREFLIGHT','RECEIPT','SIGNATURE','EXPERIMENT','REVIEW_NOTE')`，月报侧取 `COMPUTATION`，**同样不得扩枚举**）；
- **扩 `kind` 枚举＝改 `contracts/sqlite-v1.sql` 与 `migrations/**` 的 CHECK 约束＝CR 级变更**，且会打破 `tests/integration/bootstrap/test_migration_equivalence.py` 与 `tests/unit/test_migration_schema.py` 的 DDL 等价断言 → **禁止**。任何 lane 不得为落库便利而扩枚举。
- 已同步落 `state.json → decisions.monthly_analysis_result_kind`（ACCEPTED）。

### ② 第 1 节「四份 `missing=[]`」的表述与切片实态不符，**口径更正**

实测四份切片的顶层 key 为 `spec_version / source / operations / acceptance_rows / pages / ddl / truncated_schemas`，**不含 `missing` 键**：
`scripts/contract_slice.py` 只在**有目标未命中时**才写 `missing`；全部命中时该键**不存在**（而非空数组）。
编排器把脚本 **stderr 的诊断输出** `missing=[]` 误当成了**产物字段**。

**更正后的 PRE-3 校验口径（Round 5 起唯一依据）**：判定「切片新鲜且目标全命中」应断言
**`"missing" not in slice` 且 `slice["truncated_schemas"] == []`**；**不得**断言 `slice["missing"] == []`（后者会 `KeyError`）。
四份切片的 stderr 诊断行实测均为 `missing=[] truncated_schemas=[] depth=5`，**结论不变**（切片确实新鲜、目标确实全命中），仅口径表述更正。
已同步落 `state.json → resume.dispatch_requirements` 的 PRE-3 断言口径条目。
