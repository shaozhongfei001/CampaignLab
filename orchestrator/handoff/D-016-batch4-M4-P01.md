# D-016 批次 4 · M4-P01 分节上下文（月报报告与改进）

_配套共用规则：`orchestrator/handoff/D-016-batch4-rules.md`（**必读**）。本文件只讲这一张卡。生成时间：2026-11-13T09:27:40+08:00_

## 1. state.json 实取事实（数值禁改写，卡内引用须与此一致）

| 键 | 值 |
|---|---|
| `status` | TODO |
| `lane` / `tier_planned` | S / mixed |
| `deps` | M4-01, M4-02, M4-03, M3-P01 |
| `critical` / `slack` | True / 0 |
| `depth` / `height` | 12 / 3 |
| `wave` | wave8（**serial**：M4-P01 → M5-01） |
| `acs`（9 条） | AC-MR-09, AC-MR-10, AC-MR-11, AC-025, AC-026, AC-027, AC-028, AC-029, AC-030 |
| `scope`（7 项） | `src/campaignlab/domain/monthly_report/`<br>`src/campaignlab/api/monthly_reports.py`<br>`web/src/pages/report/monthly/`<br>`tests/domain/monthly_report/`<br>`tests/integration/monthly_report/`<br>`web/tests/e2e/monthly_report/`<br>`evidence/monthly/M4-P01/` |

### 1.1 gates（原文快照，卡内 `gates:` 段照抄，禁改写措辞 · D-011）

- AC-MR-09 月报、签认与缺项（PARTIAL_DRAFT、缺焦点月快照）
- AC-MR-10 补采更正与恢复（两份报告其一签认、03 更正、重启与恢复）
- AC-MR-11 行动与下期（改进项责任与检查点、04 复核、无同义口径）
- 原 AC-025-030 回归

## 2. 预生成切片（**禁整读**，用共用规则 §2 的定点抽取配方）

| 项 | 实测值 |
|---|---|
| 路径 | `orchestrator/handoff/M4-P01.slice.json` |
| bytes / sha256[:16] | 109729 / `73a9bcf1c483adbd` |
| `spec_version` | 1.0.1 |
| `source.openapi` | `{{bytes: 443309, sha16: 592571099d638251}}` |
| 顶层 keys | `acceptance_rows`, `ddl`, `operations`, `pages`, `source`, `spec_version`, `truncated_schemas` |
| `missing` 键 | **不存在**（全命中；PRE-3 断言写 `'missing' not in d`） |
| `truncated_schemas` | `None` |
| operations（8） | `correctSnapshot`, `getReport`, `getReview`, `listReports`, `runReview`, `signReport`, `transitionAction`, `updateAction` |
| pages（4） | UI-21, UI-22, UI-24, UI-26 |
| acceptance_rows（9） | AC-025, AC-026, AC-027, AC-028, AC-029, AC-030, AC-MR-09, AC-MR-10, AC-MR-11 |
| ddl（9） | `action_followups`, `actions`, `actions__indexes`, `analysis_results`, `analysis_results__indexes`, `artifacts`, `reports`, `snapshots`, `snapshots__indexes` |

## 3. AC 归属（`acceptance.primary_owner` 实取 · 禁臆断 owner）

| AC | primary | cross_ref | confidence | basis（截断） |
|---|---|---|---|---|
| AC-MR-09 | M4-P01 | M5-P01 | ARCHITECT_DERIVED | 主证据所指权威工件由 M4-P01 产出；纯验证任务（M5-02/M5-P01/M5-03）与页面呈现面一律记 cross_ref |
| AC-MR-10 | M4-P01 | M1-P01, M5-P01 | ARCHITECT_DERIVED | 三声明者中主体是「报告修订链 + 签认 409 SNAPSHOT_SUPERSEDED + 制品 SHA + 恢复审计」→ M4-P01；M1-P01 提供 03 更正导入前提，M5-P01 为独立 QA |
| AC-MR-11 | M4-P01 | M5-P01 | ARCHITECT_DERIVED | 主证据所指权威工件由 M4-P01 产出；纯验证任务（M5-02/M5-P01/M5-03）与页面呈现面一律记 cross_ref |
| AC-025 | M4-01 | M4-03, M4-P01 | ARCHITECT_DERIVED | 主证据所指权威工件由 M4-01 产出；纯验证任务（M5-02/M5-P01/M5-03）与页面呈现面一律记 cross_ref |
| AC-026 | M4-01 | M4-P01 | ARCHITECT_DERIVED | 主证据所指权威工件由 M4-01 产出；纯验证任务（M5-02/M5-P01/M5-03）与页面呈现面一律记 cross_ref |
| AC-027 | M4-02 | M4-P01 | ARCHITECT_DERIVED | 主证据所指权威工件由 M4-02 产出；纯验证任务（M5-02/M5-P01/M5-03）与页面呈现面一律记 cross_ref |
| AC-028 | M4-02 | M4-03, M4-P01 | ARCHITECT_DERIVED | 主证据所指权威工件由 M4-02 产出；纯验证任务（M5-02/M5-P01/M5-03）与页面呈现面一律记 cross_ref |
| AC-029 | M0-04 | M5-01, M4-P01 | ARCHITECT_DERIVED | 主证据「作业与 DB」：M0-04 实现作业状态机与租约语义，M5-01 复验、M4-P01 页面侧 → cross_ref |
| AC-030 | M4-02 | M4-03, M4-P01 | ARCHITECT_DERIVED | 主证据所指权威工件由 M4-02 产出；纯验证任务（M5-02/M5-P01/M5-03）与页面呈现面一律记 cross_ref |

## 4. 本卡的定位（`docs/delivery/MONTHLY-DELTA-PLAN.md` 实取）

- `DELIVERY-PATCH.md:16`：**M4-P01 月报与改进** ｜ 前置＝原 M4-01、M4-02 的报告/行动/导出基础，
  M3-P01 可取实际结果 ｜ 范围＝服务端/产品/前端落实 **UI-21、22、24、26**；验 **PARTIAL_DRAFT、
  补采可签认、更正、旧制品和下期观察** ｜ AC＝**AC-MR-09 至 11；原 AC-025–030**。
- `MONTHLY-DELTA-PLAN.md:19`：M4-P01 ｜ lane S/F ｜ 档位 **mixed** ｜ deps M4-01、M4-02、M4-03、M3-P01 ｜ wave8。
- `MONTHLY-DELTA-PLAN.md:36`：wave8 = **serial**，`M4-P01 → M5-01`（月报报告闭环完成后才做固定环境全量回归）。
- `MONTHLY-DELTA-PLAN.md:47`：关键路径 2 含 `M4-P01 → M5-P01`；`MONTHLY-DELTA-PLAN.md:56`：M4-P01 复杂度 12 / slack 0 / **critical**。
- `MONTHLY-DELTA-PLAN.md:72`：复杂度评分 C1–C5 = 2/3/2/3/2 = 12 → 档位建议 **T3：状态机与签认语义 max，页面与导出样板 flash**。
- `MONTHLY-DELTA-PLAN.md:76`：M4-P01（PARTIAL_DRAFT 与更正状态机）被列为**必须 max** 的高复杂项之一。

## 5. spec 行号图（按行区间定点读，禁整读；文件都很小，但请只读需要的段）

| 文件 | 行数 | 你要读什么 |
|---|---|---|
| `spec/...-Monthly-Review-Delta/architecture/MONTHLY-REVIEW.md` | 67 | 月报状态机、PARTIAL_DRAFT、签认与更正语义（**第 16 行**要求 409 `SNAPSHOT_SUPERSEDED` → 见共用规则 §5-1 / D-022） |
| `spec/...-Monthly-Review-Delta/architecture/ANALYTICS.append.md` | 61 | 月报指标与分母/交集/覆盖率口径增量（与 M3-P01 冻结件 `orchestrator/handoff/M3-P01-metric-registry.md` 对齐） |
| `spec/...-Monthly-Review-Delta/ui/MONTHLY-PAGES.md` | 42 | UI-21/22/24/26 的月报增量视角 |
| `spec/...-Monthly-Review-Delta/qa/CampaignLab-Review-Acceptance-Checklist.append.md` | 20 | **AC-MR-09/10/11 的权威原文** |
| `spec/...-Monthly-Review-Delta/framework/DELIVERY-PATCH.md` | 23 | 第 16 行＝本卡定位（已抄在 §4） |
| `spec/...-Monthly-Review-Delta/reference/EVIDENCE-AND-DECISIONS.md` | 36 | 证据与决策留痕要求 |
| `spec/CampaignLab-SDD-v1.0/architecture/REPORTS.md` | 40 | 报告与制品基线语义 |
| `spec/CampaignLab-SDD-v1.0/ui/UI-21-report-list.md` | 39 | 页面基线 |
| `spec/CampaignLab-SDD-v1.0/ui/UI-22-report-detail.md` | 42 | 页面基线 |
| `spec/CampaignLab-SDD-v1.0/ui/UI-24-action-detail.md` | 41 | 页面基线（行动与下期观察） |
| `spec/CampaignLab-SDD-v1.0/ui/UI-26-evidence-export.md` | 40 | 页面基线（导出；op 归 M4-02，本卡只做页面侧 cross_ref） |
| `spec/CampaignLab-SDD-v1.0/ui/COMMON.md` | 38 | 通用交互/键盘/表格约束 |
| `spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md` | 51 | AC-025..AC-030 原文（第 10 行的 `AC-101`/`AC-202` 是活动编号，**不是 AC**） |

## 6. 建议的 scope_allow / scope_deny（以 state.json 的 `scope` 为准，可细化但禁放宽）

**scope_allow**（= state.json 的 7 项，逐项照抄）：`src/campaignlab/domain/monthly_report/`、
`src/campaignlab/api/monthly_reports.py`、`web/src/pages/report/monthly/`、`tests/domain/monthly_report/`、
`tests/integration/monthly_report/`、`web/tests/e2e/monthly_report/`、`evidence/monthly/M4-P01/`。

**scope_deny**（必须显式列出，且与 allow 交集为空）：`src/campaignlab/api/exports.py`（A14 归 M4-02）、
`src/campaignlab/api/actions.py`（A15 归 M4-02）、`src/campaignlab/api/reports.py`（A36 createReport/getReport 归 M4-01）、
`web/src/pages/review/monthly/`（M3-P02）、`web/src/features/monthly/`（M3-P02）、`src/campaignlab/infra/duckdb/`（公共件，改动走 CR）、
`src/campaignlab/api/common.py`、`src/campaignlab/domain/errors.py`（公共冻结件，20 码禁扩）、
`contracts/`、`spec/`、`migrations/`、`pyproject.toml`、`uv.lock`、`orchestrator/`、`qa-reports/`、`evidence/M5-qa/`。

## 7. 本卡必须写成 U 项的点（禁自行决定）

1. **D-022**：AC-MR-10 原文要求 409 `SNAPSHOT_SUPERSEDED`，但该 code 不在 20 码权威表内 → 按选项 A 暂用
   `SNAPSHOT_CONFLICT`，语义标签落 `Problem.detail` + `Issue.code`；写成 U 项待项目负责人终裁。
2. **A16**：`api/monthly_reports.py` 是**非路由**领域/DTO 模块（活契约 0 个月报专属 operationId）；
   路由走既有 `runReview`/`getReview` + `input_json.profile='BANK_MONTHLY_V1'`、`signReport`、`correctSnapshot`。
   卡内禁出现「新增月报 op」的产出项。
3. **A17**：月报结果落 `analysis_results(kind='review')` + `input_json.profile` 判别；制品落 `artifacts(kind='COMPUTATION')`。
   **禁扩 `kind` 的 CHECK 枚举**（`sqlite-v1.sql:102` 只有 comparison/review/diagnosis/question）。
4. **A14/A15/A36 归属**：export 四 op、`actions`/`action_followups` 写权、`listAudit` 读入口归 M4-02；
   `createReport`/`getReport` 归 M4-01。本卡只 cross_ref / 调用，禁重复实现、禁写成 primary owner。
5. **AC-025..AC-030 的 primary 都不是 M4-P01**（分别是 M4-01 / M4-01 / M4-02 / M4-02 / M0-04 / M4-02，
   M4-P01 只在 cross_ref 里）→ 卡内 `gates` 对这 6 条只能写「回归 / cross_ref 取证」，**禁写成 primary 取证义务**。
   只有 AC-MR-09/10/11 的 primary 是 M4-P01。
6. **档位 mixed**：状态机与签认语义（PARTIAL_DRAFT / 更正 / 旧制品不可变）属 §6.3 强制 max；
   页面样板（UI-21/22/24/26）与导出复用属量产型 flash。请按此拆子任务并给出可审计理由；
   若 flash 占比不达标（<60 percent），照实写「不达标 + 理由 + 回补计划」，**禁降档凑数**。

