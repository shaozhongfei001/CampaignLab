# UI-22 报告审阅、签认与修订

路由 `/w/:workspace_id/reports/:report_id`。导航为「报告与改进」。适用角色为报告审核者。需求编号 FR-22。

审阅正文和来源，签认当前版本，补数后可同时查阅旧报告与新报告。

## 页面结构

| 区域 | 布局与内容 |
|---|---|
| 摘要条 | 本期、基准、快照、比较状态与签认状态 |
| 左 3 列 | 章节目录和版本链 |
| 右 9 列 | 七段正文或取数清单，右侧证据抽屉 |

使用 [公共页面规范](COMMON.md) 的 12 列、状态、键盘与证据抽屉。下表以服务端模型为数据来源。

## 字段和绑定

| 区域 | 字段 | 接口模型 |
|---|---|---|
| 正文 | 七章节、专题对照、来源及缺项 | Report.sections/missing_requirements |
| 签认 | 摘要、签认人、说明 | SignReport |
| 修订 | 更正后的 review_id、原报告编号、修订理由 | ReportCreate |

## 操作、接口与反馈

| 动作 | operationId | 提交和反馈 |
|---|---|---|
| 审阅与签认 | getReport, getEvidence, signReport | DRAFT_READY 且 stale 为 false 时可签认，匹配 ETag 和摘要后显示签认人时间 |
| 生成修订 | createReport, getJob | 关联原报告与更正快照，保留原版本链接 |
| 导出当前版本 | createExport, getExport, downloadExport | 按状态提供 Markdown 或取数 CSV，文件标注版本 |

## 页面状态与边界

- DATA_REQUIRED 显示清单，PARTIAL_DRAFT 显示草稿与缺项，已签认只读。报告正文按 Markdown 安全渲染。
- 首载、空结果、失败、版本变化和权限状态采用公共页面规范。详情和制品以当前工作区校验结果为准。

## 验收与衔接

按 [验收计划](../qa/ACCEPTANCE.md) 核对 AC-025、AC-026、AC-030，记录页面实际状态、接口结果、证据引用和失败分支。

衔接页面为 [UI-08 数据快照与更正](UI-08-snapshots.md)、[UI-19 业务问答与专题入口](UI-19-business-ask.md)、[UI-21 报告列表与新建](UI-21-report-list.md)、[UI-24 改进执行与下期复核](UI-24-action-detail.md)、[UI-26 证据、审计与导出](UI-26-evidence-export.md)。
