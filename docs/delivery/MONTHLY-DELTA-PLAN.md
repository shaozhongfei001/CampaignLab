# 月报增量（v1.0.1）交付计划插入 · M0-P01 产出

依据：补丁 `framework/DELIVERY-PATCH.md`、`qa/CampaignLab-Review-Acceptance-Checklist.append.md`（AC-MR-01..12）、
本仓 `docs/delivery/LONG-HORIZON-ORCHESTRATION.md` 第 2 节 DAG 与第 6 节模型路由。
状态：已插入 `orchestrator/state.json`（waves 与 tasks 同步更新），**尚未开工**。

## 1. 验收基线变化
- 原 35 条 AC 保持不变；新增 **AC-MR-01 至 AC-MR-12**，合计 **47 条**。
- 活契约 `contracts/openapi.json` 的 `info.version` = **1.0.1**（CR-001 / ADR-004 / `contracts/CHANGES.json` 12 项）。
- 前端类型客户端必须在 M0-03 及其后各前端任务中按 1.0.1 重新生成（门禁：openapi-typescript 产物 diff 为空）。

## 2. 新增任务与依赖（P 系列）
| 任务 | lane | tier | 依赖（开工条件） | 落点 wave | 覆盖 AC |
|---|---|---|---|---|---|
| M0-P01 接续登记与契约合入 | T | max | 补丁已解压 | wave0 尾（**已完成**） | 无（治理与门禁） |
| M1-P01 月报接入 | S/D | max | M0-04、M1-01、M1-02 | wave4 | AC-MR-01、02、10（输入侧）＋原 AC-005/006/007 |
| M3-P01 月报计算 | R/D | max(high) | M1-P01（算法单测可先用包内样本提前起） | wave5（L3 lane） | AC-MR-03..08＋原 AC-008、018–022 |
| M3-P02 月报工作台 | F | mixed | M0-03、M3-P01、M3-04（UI-17 骨架已就位） | wave7 | AC-MR-03..08 的浏览器走查 |
| M4-P01 月报报告与改进 | S/F | mixed | M4-01、M4-02、M4-03、M3-P01 | wave8 | AC-MR-09、10、11＋原 AC-025–030 |
| M5-P01 月报独立走查 | Q | max 判定＋flash 采集 | M3-P02、M4-P01、M5-01 | wave9 | AC-MR-12 及 AC-MR-01..11 实测复跑 |

M5-02 的口径同步扩大：由「独立重跑 35 条」改为「独立重跑 **47 条**」，与 M5-P01 并行但证据分目录
（`evidence/M5/M5-02/` 与 `evidence/monthly/M5-P01/`），避免两条 QA 线互相覆盖。

## 3. 波次重排（原 9 波 → 11 波）
| wave | 模式 | 任务 | 写权限不相交论证 |
|---|---|---|---|
| 0 | serial | M0-01 →（尾）M0-P01 | 单任务 |
| 1 | parallel | M0-02 ∥ M0-03 | 后端 `src/**` vs 前端 `web/**` |
| 2 | parallel | M0-04 ∥ M0-03b | 作业/租约 vs 页面状态；出口后公共件冻结 |
| 3 | parallel-lanes | L1[M1-01→02→03] ∥ L2[M2-01→02→03] | domain 子包与 tests 子目录不相交 |
| 4 | parallel | M1-04 ∥ M2-04 ∥ **M1-P01** | 前端 `pages/data` vs `pages/{rules,cases}` vs 后端导入发布 |
| 5 | parallel-lanes | L1[M3-01→02→03] ∥ **L3[M3-P01]** | 分析域按子包切分：既有 `analytics/**` vs `analytics/monthly/**`、`domain/monthly/**`、`tests/monthly/**`；**共享注册表属公共件，需注册月报指标时提 CR 由 T 串行合并** |
| 6 | parallel | M3-04 ∥ M4-01 | 页面 UI-17..20 vs 报告后端 |
| 7 | mixed | [M4-02→M4-03] ∥ **M3-P02** | 报告/导出页 `pages/report/**` vs 月报视角 `pages/review/monthly/**`；M3-P02 若需改 UI-17 既有结构，走 CR |
| 8 | serial | **M4-P01** → M5-01 | 月报报告闭环完成后才做固定环境全量回归 |
| 9 | parallel | M5-02 ∥ **M5-P01** | 均为只读 QA，仅写各自 evidence 目录 |
| 10 | serial | M5-03 | 项目负责人交付确认 |

关键路径长度仍为 **14 个任务**，但出现 **3 条并列链**（由 state.json 依赖图程序化枚举，非手写）：

1. M0-01 → M0-02 → M0-04 → M1-01 → M1-02 → M3-01 → M3-02 → M3-03 → M4-01 → M4-02 → M4-03 → M5-01 → M5-02 → M5-03
2. M0-01 → M0-02 → M0-04 → M1-01 → M1-02 → M3-01 → M3-02 → M3-03 → M4-01 → M4-02 → M4-03 → M4-P01 → M5-P01 → M5-03
3. M0-01 → M0-02 → M0-04 → M1-01 → M1-02 → M3-01 → M3-02 → M3-03 → M4-01 → M4-02 → M4-03 → M5-01 → M5-P01 → M5-03

**据实修正**（先前的手写描述不准确，已按程序化 slack 计算改写）：三条并列链的月报段是
`M4-P01 → M5-P01`，**不包含** M1-P01 与 M3-P01 —— 因为 M4-P01 还依赖更晚的 M4-03，
月报前段因此拥有浮动时间。逐任务 slack 已写入 state.json（`depth`/`height`/`slack`/`critical`）：

| 月报任务 | depth | height | slack | 是否关键 |
|---|---|---|---|---|
| M0-P01 | 1 | 1 | 13 | 否（治理任务，已完成） |
| M1-P01 | 6 | 5 | 4 | 否 |
| M3-P01 | 7 | 4 | 4 | 否 |
| M3-P02 | 10 | 3 | 2 | 否 |
| M4-P01 | 12 | 3 | 0 | **是** |
| M5-P01 | 13 | 2 | 0 | **是** |

调度含义：M4-P01 与 M5-P01 无浮动，延误即延误交付；M1-P01 与 M3-P01 各有 4 个任务的浮动、M3-P02 有 2 个，
可用来吸收 max 档的返工轮次（L 循环上限 3 轮）而不冲击关键路径。
为保证 M5-03 交付确认覆盖 AC-MR-12 的三条路径，`M5-03.deps` 已补为 `[M5-02, M5-P01]`。

wave9 两条 QA 线的写权限已收敛为互不包含（M0-P01 的冲突校验器要求）：M5-02 用 `qa-reports/m5-02/`
与 `orchestrator/defects/D-*.md`；M5-P01 用 `qa-reports/monthly/` 与 `orchestrator/defects/DMR-*.md`。
## 4. 复杂度评分与档位（第 6 节 C1–C5，各 0–3 分）
| 任务 | C1 契约 | C2 语义 | C3 不确定 | C4 半径 | C5 验证 | 合计 | 档位 |
|---|---|---|---|---|---|---|---|
| M0-P01 | 3 | 2 | 2 | 3 | 1 | 11 | T3 max（已执行） |
| M1-P01 | 2 | 3 | 2 | 2 | 2 | 11 | T3 max |
| M3-P01 | 2 | 3 | 3 | 2 | 2 | 12 | T3 max high |
| M3-P02 | 1 | 2 | 2 | 2 | 3 | 10 | T3 → 采 mixed（max 出交互设计，flash 量产页面与状态） |
| M4-P01 | 2 | 3 | 2 | 3 | 2 | 12 | T3 → 状态机与签认语义 max，页面与导出样板 flash |
| M5-P01 | 1 | 2 | 1 | 2 | 3 | 9 | T3 判定 max＋采集 flash |

强制 max 命中项：M1-P01（客户键与归一化语义）、M3-P01（分母、交集、去重、覆盖率口径）、
M4-P01（PARTIAL_DRAFT 与更正状态机）、M0-P01（改 OpenAPI 与 JSON Schema）。
可下放 flash 的子任务：月报页面样板与表单铺开、参数化负例枚举（AC-MR-02/04/06 的注入用例）、
CSV 等价样例校验、截图与证据采集、文档与回执。

## 5. 数据与样例（只用合成数据）
补丁 `fixtures/` 提供 source-01-partial / 02-backfilled / 03-corrected / 04-next、monthly-golden、
map-monthly、csv-equivalent（含 metadata.json 与 monthly_touch_slices.csv）、request-examples。
使用约束：黄金值以 `fixtures/monthly-golden.json` 为准，任何改动必须能追溯到补丁文件哈希；
真实行内分母、口径归属、客户键与容量定义仍属 `PENDING_OWNER`（BLK-04 / SRC-1）。

## 6. 证据路径约定
`evidence/monthly/<任务号>/<运行号>/`（补丁建议），原任务证据仍在 `evidence/M<n>/<任务号>/`。
M0-P01 的 run-01 已落盘：`evidence/monthly/M0-P01/run-01/{commands.md,precheck-base.log,post-merge-precheck.log,merged-diff.log,check-validate.log}`。
