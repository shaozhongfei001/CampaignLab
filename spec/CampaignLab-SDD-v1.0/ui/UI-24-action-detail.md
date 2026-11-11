# UI-24 改进执行与下期复核

路由 `/w/:workspace_id/actions/:action_id`。导航为「报告与改进」。适用角色为行动责任人、报告审核者。需求编号 FR-24。

把后续的同范围观察和预发回执连回原问题，并保存复核证据。

## 页面结构

| 区域 | 布局与内容 |
|---|---|
| 左 7 列 | 来源异常、假设、动作、责任、时间线 |
| 右 5 列 | 案例、回执、报告和下期结果 |
| 页脚 | 按状态显示开始、待验证、保存复核、关闭 |

使用 [公共页面规范](COMMON.md) 的 12 列、状态、键盘与证据抽屉。下表以服务端模型为数据来源。

## 字段和绑定

| 区域 | 字段 | 接口模型 |
|---|---|---|
| 复核 | 下一期 review_id、案例、回执、结果、说明 | ActionReview |
| 状态 | 当前状态和需要重核标记 | Action.state/needs_review |

## 操作、接口与反馈

| 动作 | operationId | 提交和反馈 |
|---|---|---|
| 更新与流转 | getAction, updateAction, transitionAction | 按当前版本提交，与阶段前置条件对应 |
| 生成下期观察 | runReview, getJob, getReview, getReceipt | 复制原范围，替换期和比较基准，显示原值与新值 |
| 保存复核 | reviewAction, getEvidence | 校验同口径、窗口、预发与所选结论 |

## 页面状态与边界

- 缺证据记录 NEEDS_MORE_DATA，保留待复核。观察增长为 +216 人，若需因果结论另行补实验。更正后的已关闭项仍保留历史并可复核。
- 首载、空结果、失败、版本变化和权限状态采用公共页面规范。详情和制品以当前工作区校验结果为准。

## 验收与衔接

按 [验收计划](../qa/ACCEPTANCE.md) 核对 AC-017、AC-026、AC-027、AC-028，记录页面实际状态、接口结果、证据引用和失败分支。

衔接页面为 [UI-03 活动详情与版本回执](UI-03-activity-detail.md)、[UI-15 运行结果、轨迹与验收案例](UI-15-run-result.md)、[UI-17 策略复盘工作台](UI-17-strategy-review.md)、[UI-22 报告审阅、签认与修订](UI-22-report-detail.md)、[UI-23 改进项列表](UI-23-action-list.md)。
