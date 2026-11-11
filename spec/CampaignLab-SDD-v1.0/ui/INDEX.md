# 页面契约目录

共 26 个路由，抽屉、对话框和页签由承载页定义。入口使用 [公共规范](COMMON.md)。

| 页面 | 路由 | 导航 | 验收 |
|---|---|---|---|
| [UI-01 工作区与首次进入](UI-01-workspace.md) | `/` | 入口 | AC-001、AC-034 |
| [UI-02 活动列表](UI-02-activity-list.md) | `/w/:workspace_id/activities` | 活动与规则 | AC-002、AC-032 |
| [UI-03 活动详情与版本回执](UI-03-activity-detail.md) | `/w/:workspace_id/activities/:activity_id` | 活动与规则 | AC-002、AC-003、AC-017 |
| [UI-04 规则版本编辑与对比](UI-04-rule-version.md) | `/w/:workspace_id/activities/:activity_id/rules/:rule_id` | 活动与规则 | AC-003、AC-004、AC-034 |
| [UI-05 规则检查与边界案例](UI-05-rule-check.md) | `/w/:workspace_id/activities/:activity_id/rules/:rule_id/checks` | 活动与规则 | AC-004、AC-012 |
| [UI-06 数据导入任务](UI-06-import-list.md) | `/w/:workspace_id/imports` | 数据与口径 | AC-005、AC-006 |
| [UI-07 映射配置与发布](UI-07-import-detail.md) | `/w/:workspace_id/imports/:import_id` | 数据与口径 | AC-005、AC-006、AC-029 |
| [UI-08 数据快照与更正](UI-08-snapshots.md) | `/w/:workspace_id/snapshots` | 数据与口径 | AC-007、AC-020、AC-026 |
| [UI-09 指标字典与口径证据](UI-09-metric-dictionary.md) | `/w/:workspace_id/definitions` | 数据与口径 | AC-008、AC-018 |
| [UI-10 跨行同义指标对账](UI-10-bank-compare.md) | `/w/:workspace_id/compare` | 数据与口径 | AC-009、AC-020 |
| [UI-11 渠道重算与时间窗关联](UI-11-channel-evidence.md) | `/w/:workspace_id/channels` | 数据与口径 | AC-010、AC-011 |
| [UI-12 场景案例库](UI-12-case-list.md) | `/w/:workspace_id/cases` | 仿真与验收 | AC-012、AC-034 |
| [UI-13 案例输入、实测与预期](UI-13-case-detail.md) | `/w/:workspace_id/cases/:case_id` | 仿真与验收 | AC-012、AC-013、AC-015 |
| [UI-14 运行中心与批量复跑](UI-14-run-list.md) | `/w/:workspace_id/runs` | 仿真与验收 | AC-013、AC-029 |
| [UI-15 运行结果、轨迹与验收案例](UI-15-run-result.md) | `/w/:workspace_id/runs/:run_id` | 仿真与验收 | AC-014、AC-015、AC-016、AC-030 |
| [UI-16 行内预发结果对照](UI-16-preflight.md) | `/w/:workspace_id/preflight` | 仿真与验收 | AC-016、AC-017 |
| [UI-17 策略复盘工作台](UI-17-strategy-review.md) | `/w/:workspace_id/review` | 策略复盘 | AC-008、AC-018、AC-019、AC-020、AC-025、AC-033 |
| [UI-18 异常诊断与贡献拆解](UI-18-diagnosis.md) | `/w/:workspace_id/diagnosis` | 策略复盘 | AC-021、AC-022、AC-027 |
| [UI-19 业务问答与专题入口](UI-19-business-ask.md) | `/w/:workspace_id/ask` | 策略复盘 | AC-008、AC-023、AC-025、AC-033 |
| [UI-20 接触转化情景试算](UI-20-estimate.md) | `/w/:workspace_id/estimate` | 仿真与验收 | AC-024、AC-028 |
| [UI-21 报告列表与新建](UI-21-report-list.md) | `/w/:workspace_id/reports` | 报告与改进 | AC-025、AC-026 |
| [UI-22 报告审阅、签认与修订](UI-22-report-detail.md) | `/w/:workspace_id/reports/:report_id` | 报告与改进 | AC-025、AC-026、AC-030 |
| [UI-23 改进项列表](UI-23-action-list.md) | `/w/:workspace_id/actions` | 报告与改进 | AC-027、AC-028 |
| [UI-24 改进执行与下期复核](UI-24-action-detail.md) | `/w/:workspace_id/actions/:action_id` | 报告与改进 | AC-017、AC-026、AC-027、AC-028 |
| [UI-25 作业状态与恢复](UI-25-jobs.md) | `/w/:workspace_id/jobs` | 作业与证据 | AC-029、AC-031 |
| [UI-26 证据、审计与导出](UI-26-evidence-export.md) | `/w/:workspace_id/evidence` | 作业与证据 | AC-030、AC-031、AC-034 |
