# 26 页 ↔ 模板组件族映射表（ADR-003 实施面）

依据 `spec/CampaignLab-SDD-v1.0/ui/INDEX.md` 与 26 份页面契约的「页面结构」「操作、接口与反馈」两节，映射到模板 11 族组件与本项目 Vue 组件。区域划分沿用页面契约原文（列数为 12 列栅格占比）。

## 1. 公共组件交付顺序

| 组件 | 覆盖页面 | 首次交付 |
|---|---|---|
| `AppShell` `SideRail` `AppBar` `PageBar` | 26 / 26 | M0-03 |
| `EvidenceDrawer`（模板 `.sheet`，480px，Esc 关闭并返回触发焦点） | 26 / 26 | M0-03 |
| `StatusTag`（收敛 `.tag` 与 `.st` 双体系） | 26 / 26 | M0-03 |
| `PageGrid` `CardPanel` | 26 / 26 | M0-03 |
| `AlertBanner` `EmptyState`（含首载/空/失败/部分可比/待补/412 过期六态） | 26 / 26 | M0-03 |
| `DataTable`（行高 40/36、等宽数字、键盘排序、游标 25 行、宽表冻结首列） | 24 / 26 | M0-03 |
| `ScopeBar`（基本项 + 高级项展开，预览后点计算） | 全站，显式 7 页 | M1-04 |
| `JobProgress`（202 轮询、租约、重试、取消） | UI-07、14、25 | M0-04 |
| `DiffTable` `DiffPanel` | UI-04、10、13、15、16、20、23 | M2-04 |
| `Timeline` | UI-03、08、13、15、24、26 | M2-04 |
| `Tabs` `StepFlow` | UI-03、11、26 / UI-07 | M1-04 |
| `ChartWithTable`（ECharts + 等义表格） | UI-17、18、20 | M3-04 |
| `ConfirmDialog`（520px，摘要 + 影响 + 取消 + 主按钮） | UI-01、04、08、13、22、24 | M2-04 |

## 2. 逐页映射

| 页面 | 路由 | 导航 | FR | 区域 → 组件 | 图表 | AC |
|---|---|---|---|---|---|---|
| UI-01 工作区 | `/` | 入口 | FR-01 | 顶栏 `AppBar`（状态/操作者/最近工作区）；主卡 8+4 `PageGrid` + `DataTable`（工作区列表）+ `CardPanel`（两条首跑路线，窄屏置下方）；创建走 `ConfirmDialog`，授权脱敏须填授权依据 | — | 001、034 |
| UI-02 活动列表 | `/w/:wid/activities` | 活动与规则 | FR-02 | 标题行 `PageBar` + `ActionButton`（新建活动，本屏唯一主按钮）；全宽 `DataTable`（编号/活动/来源银行/行内编号/当前仿真版本/状态 → `StatusTag`） | — | 002、032 |
| UI-03 活动详情 | `…/activities/:aid` | 活动与规则 | FR-03 | 摘要 8+4 `CardPanel`（名称/来源/当前验证版本）+ `ObjectStatusCard`（准备状态）；下方 `Tabs`（绑定 / 规则版本 / 预发与回执）→ `DataTable` + `Timeline` | — | 002、003、017 |
| UI-04 规则版本 | `…/rules/:rid` | 活动与规则 | FR-04 | 7+5：`RuleTemplateForm`（满额赠券 / 远程回拨两套模板字段）；右侧 `DiffPanel`（原条款/待确认项/版本对比）+ `GateCheck` + `EvidenceDrawer`；底部 `ActionButton` 行（草稿保存 / 规则检查 / 确认版本 → `ConfirmDialog`） | — | 003、004、034 |
| UI-05 规则检查 | `…/rules/:rid/checks` | 活动与规则 | FR-05 | `ScopeBar`（活动/版本/摘要/待确认数）；8+4：`DataTable`（问题按 错误·警告·信息 排序）+ `CardPanel`（边界案例推荐与定位） | — | 004、012 |
| UI-06 导入任务 | `/w/:wid/imports` | 数据与口径 | FR-06 | 全宽 `FilterBar`（银行/格式/状态 + 新建导入）；`DataTable`（任务/版本/表数/状态/快照/更新时间）+ 导出 `ActionButton` | — | 005、006 |
| UI-07 映射与发布 | `…/imports/:iid` | 数据与口径 | FR-07 | `StepFlow`（文件 → 映射 → 校验 → 发布）；7+5：`MappingGrid`（表形/维度/阶段/金额/代码映射）+ `CardPanel`（文件摘要）+ `AlertBanner`（问题列表）+ 发布 `ActionButton`；`JobProgress` 承担重试 | — | 005、006、029 |
| UI-08 快照与更正 | `/w/:wid/snapshots` | 数据与口径 | FR-08 | 4+8：`DataTable`（快照列表按创建倒序）；右侧 `CardPanel`（来源/覆盖/字典/批次）+ `Timeline`（更正历史）+ `StatusTag`（签认） | — | 007、020、026 |
| UI-09 指标字典 | `/w/:wid/definitions` | 数据与口径 | FR-09 | 上方 `ScopeBar` 固定快照与口径版本；全宽 `DataTable`（指标/单位/公式/分子/分母/聚合方式/来源）+ `FormulaCell` + `EvidenceDrawer` | — | 008、018 |
| UI-10 跨行对账 | `/w/:wid/compare` | 数据与口径 | FR-10 | 顶行 6+6：两个 `ScopeBar`（A / B 范围，支持复制范围）；下方 `StatusBand`（可比性条）+ `DiffTable`（差异原因、两边原值、对齐值、差值） | — | 009、020 |
| UI-11 渠道与时间窗 | `/w/:wid/channels` | 数据与口径 | FR-11 | `Tabs`：页签一 六渠道公式，5+7 `FormulaPanel`（单事件输入）+ `DataTable`（逐阶段结果）；页签二 时间窗与候选分配，全宽 `DataTable` | — | 010、011 |
| UI-12 案例库 | `/w/:wid/cases` | 仿真与验收 | FR-12 | 上方 `FilterBar`（活动/状态/模板 + 新建）；全宽 `DataTable`（案例/活动/合成或历史/修订/证据/状态） | — | 012、034 |
| UI-13 案例详情 | `…/cases/:cid` | 仿真与验收 | FR-13 | 8+4：`EventSequence`（客户范围/初始状态/事件序列，基于 `Timeline`）+ `DiffPanel`（期望与原实际/来源/摘要/确认）；底部 `ActionButton`（提交确认 → `ConfirmDialog` / 复制为新修订 / 加入运行） | — | 012、013、015 |
| UI-14 运行中心 | `/w/:wid/runs` | 仿真与验收 | FR-14 | 上方 `FilterBar`（活动/原规则/候选规则/快照）；全宽 `DataTable`（案例多选）+ 运行列表 + `JobProgress`（重试）；底部唯一主按钮「运行」 | — | 013、029 |
| UI-15 运行结果 | `…/runs/:runid` | 仿真与验收 | FR-15 | 摘要 `CardPanel`（快照/输入/原规则/候选规则/摘要）；4+8：`DataTable`（案例列表）+ `DiffTable`（双栏结果）+ `Timeline`（轨迹）；底部 `ActionButton`（验收预期确认 / 移交 / 导出） | — | 014、015、016、030 |
| UI-16 预发对照 | `/w/:wid/preflight` | 仿真与验收 | FR-16 | 上方 `FilterBar`（活动/候选集合/预发来源/批次）；全宽 `DiffTable`（候选、原与候选摘要、预期、实际、差异、状态）；右侧 `EvidenceDrawer`（差异路径与来源证据） | — | 016、017 |
| UI-17 策略复盘 | `/w/:wid/review` | 策略复盘 | FR-17 | 头部 `ScopeBar` + 快捷基准 + `ActionButton`（生成报告 / 下载）；指标行 4 × `MetricCard`（覆盖率、名单执行率、有效触达数、有效触达率，每张 3 列）；中部 7+5 `FunnelChart`（五层漏斗，低转化层突出）+ `CardPanel`（优先核查）+ `DataTable`（专题）；下部全宽 `DataTable`（参与度、执行效果、分行/渠道/支行/客群明细） | 漏斗 + 等义表 | 008、018、019、020、025、033 |
| UI-18 异常诊断 | `/w/:wid/diagnosis` | 策略复盘 | FR-18 | 顶部 `ScopeBar`（固定复盘范围）+ `FilterBar`（阈值版本、规则筛选）；中部全宽 `DataTable`（异常清单 + 阈值标记）+ 两列 `ChartWithTable`（量率、维度，需正负对比）；下部 `LineChart`（六个月趋势）+ `CardPanel`（可核查业务假设）+ `ActionButton`（登记改进项） | 柱 + 折线 | 021、022、027 |
| UI-19 业务问答 | `/w/:wid/ask` | 策略复盘 | FR-19 | 上方 问题输入 + `ChipList`（常用示例）+ `ActionButton`（解析）；5+7：`ScopeEditor`（已解析范围与可编辑条件）+ `MetricCard` / `DataTable`（数值、字典、异常、拆解）+ 专题入口 | 可选迷你图 | 008、023、025、033 |
| UI-20 情景试算 | `/w/:wid/estimate` | 仿真与验收 | FR-20 | 上方 `ScopeBar`（固定复盘、快照、期间、渠道）；5+7：`FormulaPanel`（公式与转化假设）+ `DiffTable`（原值、试算、差值）+ `ChartWithTable` | 对比柱 | 024、028 |
| UI-21 报告列表 | `/w/:wid/reports` | 报告与改进 | FR-21 | 头部 `FilterBar`（状态、关键词 + 生成报告）；`DataTable`（标题/类型/期间/快照/状态/签认人/版本链 → `StatusTag` + `VersionChain`） | — | 025、026 |
| UI-22 报告详情 | `…/reports/:repid` | 报告与改进 | FR-22 | 摘要条 `StatusBand`（本期/基准/快照/比较状态/签认状态）；3+9：`TocNav`（章节目录）+ `VersionChain` + `ReportBody`（七段正文或取数清单，Markdown 安全解析，禁远程资源与原始 HTML）+ `EvidenceDrawer`；导出 `ActionButton` | — | 025、026、030 |
| UI-23 改进项列表 | `/w/:wid/actions` | 报告与改进 | FR-23 | `FilterBar`（状态、关键字 + 从复盘新建）；全宽 `DataTable`（责任/到期/30·90 天/状态/待复核标记 + `DueBadge`） | — | 027、028 |
| UI-24 改进执行 | `…/actions/:actid` | 报告与改进 | FR-24 | 7+5：`CardPanel`（来源异常/假设/动作/责任）+ `Timeline`（时间线）+ `DataTable`（案例/回执/报告/下期结果）+ `StatusTag`；页脚 `ActionButton` 按状态显示（开始 / 待验证 / 保存复核 / 关闭 → `ConfirmDialog`） | — | 017、026、027、028 |
| UI-25 作业与恢复 | `/w/:wid/jobs` | 作业与证据 | FR-25 | 顶部 `HealthChip`（执行进程健康）+ 排队数 + `FilterBar`（状态过滤）；全宽 `DataTable`（任务/阶段/尝试号/进度 `JobProgress`/结果/操作 重试·取消）；`EvidenceDrawer`（请求摘要、失败原因、原结果引用） | — | 029、031 |
| UI-26 证据与导出 | `/w/:wid/evidence` | 作业与证据 | FR-26 | `Tabs`（证据 / 审计 / 已导出）；全宽 `DataTable`（类型/来源/位置/摘要/对象/时间）；`EvidenceDrawer`（节选、访问范围、复制编号）+ 导出 | — | 030、031、034 |

## 3. 模板未覆盖、需自研的部分（前端主要工作量）

| 组件 | 模板为何不能直接用 | 出现页面 | 里程碑 |
|---|---|---|---|
| `ScopeBar` 公共范围条 | 模板只有单排 `.filterbar`；契约要求基本项 + 高级项展开、先预览后计算、URL 保存受控筛选、区分所选范围与上次计算范围 | 全站，显式 UI-05/09/10/17/18/19/20 | M1-04 |
| `DiffTable` / `DiffPanel` | 模板无差异对照组件 | UI-04、10、13、15、16、20、23 | M2-04 |
| `JobProgress` + 202 轮询 | 模板 `.demo-progress` 属演示控件，提取时已被剔除 | UI-07、14、25 | M0-04 |
| `FunnelChart` 五层漏斗 | 模板图表原语无漏斗 | UI-17 | M3-04 |
| `VersionChain` 版本链 | 模板无 | UI-02、03、21、22 | M2-04 |
| `ReportBody` Markdown 安全渲染 | 模板 `.quote` / `.evrow` 不足以承载七段正文 | UI-22 | M4-03 |
| `MappingGrid` 可编辑映射网格 | 模板 `.editrow` 可作视觉基础，但需绑定输入 Schema 与校验 | UI-07 | M1-04 |
| `EventSequence` 事件序列 | 模板 `.tl` 可作基础，需承载时间窗与候选归属 | UI-13、15 | M2-04 |
| `ChartWithTable` 等义表格 | 模板图表无数据表替代 | UI-17、18、20 | M3-04 |
| 六类页面状态 | 模板有 `.empty` / `.banner`，但缺「部分可比」「待补」「412 过期」语义 | 全站 | M0-03 |

## 4. 走查与验收挂钩

1. 每页出口给 Playwright 截图，档位 1440×900 与 1024×768，存 `evidence/M*/ui/<page-id>/`，文件名 ASCII。
2. 视觉逐族对照 `spec/frontend-template-spdb-v1.1/gallery_组件图鉴.html`，偏差记为 NOTE 或 MINOR。
3. AC 编号沿用页面契约与 `qa/ACCEPTANCE.md`；机器门禁与内容红线按 [ADR-003](../decisions/ADR-003-frontend-design-baseline.md) 第「门禁采纳」节执行。
4. 页面契约中的 `operationId` 为接口真值，任何新接口须同时更新 `contracts/openapi.json`、调用页面与测试（AGENTS.md 要求）。
