# 原型需求和手册追踪矩阵

历史状态沿用原型 v0.1 合成验证。新设计状态为契约已定义或待外部证据，应用验收依据后续实测。

## 55 个材料点位

| 来源编号 | 业务需求及定位 | 原型状态 | 本包页面 | 开发验收 | 待外部证据 |
|---|---|---|---|---|---|
| CL01 | P01、P02。数据分散，需要从策略、渠道及产能来源取数 | 条件覆盖 | [UI-06](../ui/UI-06-import-list.md)、[UI-07](../ui/UI-07-import-detail.md)、[UI-08](../ui/UI-08-snapshots.md) | AC-005、AC-006 | 按业务范围补实测 |
| CL02 | P01、P02。人工跨看板汇总和重复制表 | 已测 | [UI-17](../ui/UI-17-strategy-review.md)、[UI-26](../ui/UI-26-evidence-export.md) | AC-018、AC-019、AC-030 | 按业务范围补实测 |
| CL03 | P02。指标口径重复询问和查找 | 已测 | [UI-09](../ui/UI-09-metric-dictionary.md)、[UI-17](../ui/UI-17-strategy-review.md)、[UI-19](../ui/UI-19-business-ask.md) | AC-008、AC-023 | 按业务范围补实测 |
| CL04 | P02。人工分析慢、异常发现滞后 | 条件覆盖 | [UI-18](../ui/UI-18-diagnosis.md) | AC-021、AC-022 | 按业务范围补实测 |
| CL05 | P02、W01。分析能力集中，基层要用业务语言和引导流程 | 条件覆盖 | [UI-19](../ui/UI-19-business-ask.md)、[UI-18](../ui/UI-18-diagnosis.md)、[UI-23](../ui/UI-23-action-list.md) | AC-023、AC-027 | 按业务范围补实测 |
| CL06 | P01、W01。复盘已常态化／机制与标准描述有差异 | 条件覆盖 | [UI-21](../ui/UI-21-report-list.md)、[UI-22](../ui/UI-22-report-detail.md) | AC-025、AC-026 | 按业务范围补实测 |
| CL07 | P01、P08-A。报告应指导下一轮策略提升 | 已测 | [UI-03](../ui/UI-03-activity-detail.md)、[UI-15](../ui/UI-15-run-result.md)、[UI-16](../ui/UI-16-preflight.md)、[UI-24](../ui/UI-24-action-detail.md) | AC-014、AC-016、AC-017、AC-028 | 按业务范围补实测 |
| CL08 | P01-S1、P01-S2。报告用事实、基准、趋势和运营解释 | 条件覆盖 | [UI-17](../ui/UI-17-strategy-review.md)、[UI-18](../ui/UI-18-diagnosis.md)、[UI-22](../ui/UI-22-report-detail.md) | AC-018、AC-021、AC-025 | 按业务范围补实测 |
| CL09 | P01-S2。渠道恢复统计影响对比，原报告作 A/B 类比 | 已测 | [UI-10](../ui/UI-10-bank-compare.md)、[UI-17](../ui/UI-17-strategy-review.md)、[UI-24](../ui/UI-24-action-detail.md) | AC-020、AC-028 | 按业务范围补实测 |
| CL10 | P05、P08-A。已部署分行数及分组参与现状 | 已测 | [UI-17](../ui/UI-17-strategy-review.md) | AC-019 | 按业务范围补实测 |
| CL11 | P05。策略、部署分行和覆盖度的月增、环比 | 已测 | [UI-17](../ui/UI-17-strategy-review.md) | AC-018、AC-019 | 按业务范围补实测 |
| CL12 | P05。可经营客户、成功下发、策略数、覆盖率和有效触达率 | 已测 | [UI-17](../ui/UI-17-strategy-review.md) | AC-008、AC-018 | 按业务范围补实测 |
| CL13 | P05、W04-S2。五层漏斗及最低转化层 | 已测 | [UI-17](../ui/UI-17-strategy-review.md) | AC-018 | 按业务范围补实测 |
| CL14 | W04-S2、W04-S3。经营率与层间率分母 | 已测 | [UI-09](../ui/UI-09-metric-dictionary.md)、[UI-17](../ui/UI-17-strategy-review.md) | AC-008 | 按业务范围补实测 |
| CL15 | P05、W04-S2。全渠道和六类渠道 | 已测 | [UI-11](../ui/UI-11-channel-evidence.md)、[UI-17](../ui/UI-17-strategy-review.md) | AC-010、AC-019 | 按业务范围补实测 |
| CL16 | P05、W04-S2。总行、分行、分组和三种策略来源视角 | 已测 | [UI-17](../ui/UI-17-strategy-review.md)、[UI-18](../ui/UI-18-diagnosis.md) | AC-019、AC-022 | 按业务范围补实测 |
| CL17 | P05、P08-A。AUM、理财及非现管理财、基金及非货基、保险销量 | 已测 | [UI-17](../ui/UI-17-strategy-review.md)、[UI-22](../ui/UI-22-report-detail.md) | AC-019、AC-025 | 按业务范围补实测 |
| CL18 | W04-S2、W04-S3。分行／渠道明细及存款、理财、基金、个贷余额增量 | 已测 | [UI-17](../ui/UI-17-strategy-review.md) | AC-019、AC-020 | 按业务范围补实测 |
| CL19 | W04-S2。按数据日期、分行、分行机构筛选，重置与导出 | 条件覆盖 | [UI-17](../ui/UI-17-strategy-review.md)、[UI-26](../ui/UI-26-evidence-export.md) | AC-019、AC-030 | 按业务范围补实测 |
| CL20 | W04-S1、W05。按业务关联下发、触达和产能，带客户、节点、批次、策略与日期 | 条件覆盖 | [UI-07](../ui/UI-07-import-detail.md)、[UI-11](../ui/UI-11-channel-evidence.md) | AC-006、AC-011 | 按业务范围补实测 |
| CL21 | W04-S1。下发日相等或加 10，产能关联近 7 天或 30–60 天 | 已测 | [UI-11](../ui/UI-11-channel-evidence.md) | AC-011 | 按业务范围补实测 |
| CL22 | W04-S1。多匹配、未匹配的归属与核验 | 已测 | [UI-11](../ui/UI-11-channel-evidence.md) | AC-011 | 按业务范围补实测 |
| CL23 | W04-S2。短信各层和有效详情页条件 | 已测 | [UI-11](../ui/UI-11-channel-evidence.md) | AC-010 | 按业务范围补实测 |
| CL24 | W04-S2。手机银行推送已收到、短链和详情 | 已测 | [UI-10](../ui/UI-10-bank-compare.md)、[UI-11](../ui/UI-11-channel-evidence.md) | AC-009、AC-010 | 按业务范围补实测 |
| CL25 | W04-S2。企微有效接触的三个或条件 | 已测 | [UI-11](../ui/UI-11-channel-evidence.md) | AC-010 | 按业务范围补实测 |
| CL26 | W04-S2。AI 外呼频控、拨打、接通与交互 | 已测 | [UI-11](../ui/UI-11-channel-evidence.md) | AC-010 | 按业务范围补实测 |
| CL27 | W04-S2。远程财私 ≥60 秒、个贷 ≥10 秒与有效期 | 已测 | [UI-11](../ui/UI-11-channel-evidence.md) | AC-010 | 按业务范围补实测 |
| CL28 | W04-S2。经理 5+1、成功触达和下游有效条件 | 条件覆盖 | [UI-11](../ui/UI-11-channel-evidence.md) | AC-010 | 按业务范围补实测 |
| CL29 | W04 正文。月内下发客户、月累计与策略耦合 | 已测 | [UI-07](../ui/UI-07-import-detail.md)、[UI-17](../ui/UI-17-strategy-review.md) | AC-006、AC-019 | 按业务范围补实测 |
| CL30 | 已确认的跨行约定、W04。配置化接入和坏输入校验 | 已测 | [UI-06](../ui/UI-06-import-list.md)、[UI-07](../ui/UI-07-import-detail.md)、[UI-10](../ui/UI-10-bank-compare.md) | AC-005、AC-006、AC-009 | 按业务范围补实测 |
| CL31 | P06、P08-A。重点客群采用部署口径或标签待定 | 条件覆盖 | [UI-17](../ui/UI-17-strategy-review.md) | AC-019 | 按业务范围补实测 |
| CL32 | P06、P08-A。活动与策略关系及特色产能 | 条件覆盖 | [UI-03](../ui/UI-03-activity-detail.md)、[UI-17](../ui/UI-17-strategy-review.md) | AC-002、AC-019 | 按业务范围补实测 |
| CL33 | W04、W05。数据架构补图、三份表结构和现有智能化现状 | 待材料 | [UI-07](../ui/UI-07-import-detail.md)、[UI-08](../ui/UI-08-snapshots.md) | AC-006 | [待银行证据](../research/NEXT-RESEARCH.md) |
| CL34 | P03、W01–W03、P08-A。问口径、数值、异常、归因、报告 | 已测 | [UI-19](../ui/UI-19-business-ask.md) | AC-023 | 按业务范围补实测 |
| CL35 | W01。指标名、期间、机构、分组、渠道、条件与排序 | 已测 | [UI-19](../ui/UI-19-business-ask.md) | AC-023、AC-033 | 按业务范围补实测 |
| CL36 | W01、P08-A。缺范围、指标或策略参数时澄清 | 已测 | [UI-19](../ui/UI-19-business-ask.md)、[UI-22](../ui/UI-22-report-detail.md) | AC-023、AC-025 | 按业务范围补实测 |
| CL37 | W01、P08-A。阈值可调整并识别升降方向 | 已测 | [UI-18](../ui/UI-18-diagnosis.md)、[UI-19](../ui/UI-19-business-ask.md) | AC-021、AC-023 | 按业务范围补实测 |
| CL38 | P08-A。期间 ≥10%、同组下偏 ≥20%、自身 6 月 ≥1σ、层间下偏 ≥15%、结构 ≥5 个百分点 | 已测 | [UI-18](../ui/UI-18-diagnosis.md) | AC-021 | 按业务范围补实测 |
| CL39 | P04、P08-A。环比、同比、同组、自身、全行、总行及目标对照 | 已测 | [UI-17](../ui/UI-17-strategy-review.md)、[UI-18](../ui/UI-18-diagnosis.md)、[UI-19](../ui/UI-19-business-ask.md) | AC-021、AC-033 | 按业务范围补实测 |
| CL40 | P04、P07。有效触达数／率按漏斗、渠道、客群、支行拆解 | 已测 | [UI-17](../ui/UI-17-strategy-review.md)、[UI-18](../ui/UI-18-diagnosis.md) | AC-018、AC-022 | 按业务范围补实测 |
| CL41 | P07。AUM 按客群、渠道、支行、总分行拆解 | 已测 | [UI-18](../ui/UI-18-diagnosis.md) | AC-022 | 按业务范围补实测 |
| CL42 | P07、W03。销量按客群／支行，存款按类型 | 已测 | [UI-18](../ui/UI-18-diagnosis.md)、[UI-19](../ui/UI-19-business-ask.md) | AC-022、AC-023 | 按业务范围补实测 |
| CL43 | P04、P08-A。结论含异常对象、原因线索与影响程度 | 已测 | [UI-18](../ui/UI-18-diagnosis.md)、[UI-22](../ui/UI-22-report-detail.md) | AC-021、AC-022、AC-025 | 按业务范围补实测 |
| CL44 | P04、P08-A。参与度、漏损、渠道、客群、策略效果五种假设 | 已测 | [UI-18](../ui/UI-18-diagnosis.md)、[UI-23](../ui/UI-23-action-list.md)、[UI-24](../ui/UI-24-action-detail.md) | AC-027、AC-028 | 按业务范围补实测 |
| CL45 | W01–W03、P03。组合问法、题述数字、条件归因 | 条件覆盖 | [UI-19](../ui/UI-19-business-ask.md) | AC-023 | 按业务范围补实测 |
| CL46 | W01–W03、P08-A。分行、策略、客群、渠道及专题报告 | 已测 | [UI-19](../ui/UI-19-business-ask.md)、[UI-21](../ui/UI-21-report-list.md)、[UI-22](../ui/UI-22-report-detail.md) | AC-023、AC-025 | 按业务范围补实测 |
| CL47 | P08-A。三块固定顺序、摘要三条、异常表和七段模板 | 已测 | [UI-21](../ui/UI-21-report-list.md)、[UI-22](../ui/UI-22-report-detail.md) | AC-025 | 按业务范围补实测 |
| CL48 | P08-A。绝对与相对值、基准、就近口径、术语一致和源数据 | 已测 | [UI-09](../ui/UI-09-metric-dictionary.md)、[UI-17](../ui/UI-17-strategy-review.md)、[UI-22](../ui/UI-22-report-detail.md) | AC-008、AC-025 | 按业务范围补实测 |
| CL49 | P08-A。异常要有阈值，区分数据验证与假设，建议有责任和动作 | 已测 | [UI-18](../ui/UI-18-diagnosis.md)、[UI-22](../ui/UI-22-report-detail.md)、[UI-23](../ui/UI-23-action-list.md) | AC-021、AC-025、AC-027 | 按业务范围补实测 |
| CL50 | P08-A。缺数时给取数清单 | 已测 | [UI-17](../ui/UI-17-strategy-review.md)、[UI-22](../ui/UI-22-report-detail.md)、[UI-26](../ui/UI-26-evidence-export.md) | AC-020、AC-025、AC-030 | 按业务范围补实测 |
| CL51 | P01、P08-A 与 CampaignLab 设计。试算、规则回放和结果差异 | 已测 | [UI-13](../ui/UI-13-case-detail.md)、[UI-14](../ui/UI-14-run-list.md)、[UI-15](../ui/UI-15-run-result.md)、[UI-20](../ui/UI-20-estimate.md) | AC-013、AC-014、AC-015、AC-024 | 按业务范围补实测 |
| CL52 | 已确认的跨行约定。案例移交、预发、行内回执与下期复核 | 已测 | [UI-03](../ui/UI-03-activity-detail.md)、[UI-15](../ui/UI-15-run-result.md)、[UI-16](../ui/UI-16-preflight.md)、[UI-24](../ui/UI-24-action-detail.md) | AC-016、AC-017、AC-028 | 按业务范围补实测 |
| CL53 | P08-A 与设计稿。签认、补数和版本追溯 | 已测 | [UI-08](../ui/UI-08-snapshots.md)、[UI-22](../ui/UI-22-report-detail.md)、[UI-24](../ui/UI-24-action-detail.md) | AC-007、AC-026、AC-028 | 按业务范围补实测 |
| CL54 | P08-A。完整指标字典及下钻规则引用 | 待材料 | [UI-09](../ui/UI-09-metric-dictionary.md)、[UI-18](../ui/UI-18-diagnosis.md) | AC-008、AC-022 | [待银行证据](../research/NEXT-RESEARCH.md) |
| CL55 | P09、P06。邮件报告样例及其他优化项 | 待材料 | [UI-21](../ui/UI-21-report-list.md)、[UI-22](../ui/UI-22-report-detail.md) | AC-025 | [待银行证据](../research/NEXT-RESEARCH.md) |

## 47 个手册操作点

| 手册位置 | 操作名称 | 页面 | 验收 |
|---|---|---|---|
| 1.1 | 选定本期、范围和比较基准 | [UI-17](../ui/UI-17-strategy-review.md) | AC-018 |
| 1.2 | 用经营卡和五层漏斗锁定优先问题 | [UI-17](../ui/UI-17-strategy-review.md) | AC-018 |
| 1.3 | 追到有效触达率的分子、分母和源行 | [UI-17](../ui/UI-17-strategy-review.md) | AC-008 |
| 1.4 | 核对漏斗最后一层的转化率 | [UI-17](../ui/UI-17-strategy-review.md) | AC-008 |
| 1.5 | 比较分行参与度与覆盖水平 | [UI-17](../ui/UI-17-strategy-review.md) | AC-019 |
| 1.6 | 核对执行效果、余额增量和销量 | [UI-17](../ui/UI-17-strategy-review.md) | AC-019 |
| 1.7 | 下钻过程与产能明细并导出 | [UI-17](../ui/UI-17-strategy-review.md) | AC-019 |
| 1.8 | 按部署客群或月末标签看专题 | [UI-17](../ui/UI-17-strategy-review.md) | AC-019 |
| 1.9 | 查已绑定活动的策略专题 | [UI-17](../ui/UI-17-strategy-review.md) | AC-002 |
| 1.10 | 处理待绑定活动 | [UI-03](../ui/UI-03-activity-detail.md) | AC-002 |
| 1.11 | 识别采集变化引起的部分可比 | [UI-17](../ui/UI-17-strategy-review.md) | AC-020 |
| 2.1 | 导入样本并查来源字段映射 | [UI-07](../ui/UI-07-import-detail.md) | AC-006 |
| 2.2 | 对照两行的同口径结果 | [UI-10](../ui/UI-10-bank-compare.md) | AC-009 |
| 2.3 | 识别跨行定义不同的指标 | [UI-10](../ui/UI-10-bank-compare.md) | AC-009 |
| 2.4 | 阅读六渠道的五层判定矩阵 | [UI-11](../ui/UI-11-channel-evidence.md) | AC-010 |
| 2.5 | 重算一条历史触达事件 | [UI-11](../ui/UI-11-channel-evidence.md) | AC-010 |
| 2.6 | 核对触达与产能的归属窗口 | [UI-11](../ui/UI-11-channel-evidence.md) | AC-011 |
| 3.1 | 用自然语言按条件查数 | [UI-19](../ui/UI-19-business-ask.md) | AC-023 |
| 3.2 | 查询指标公式和分母 | [UI-19](../ui/UI-19-business-ask.md) | AC-008 |
| 3.3 | 询问一个变化是否异常 | [UI-19](../ui/UI-19-business-ask.md) | AC-023 |
| 3.4 | 用问法定位变化来源 | [UI-19](../ui/UI-19-business-ask.md) | AC-023 |
| 3.5 | 一次提问完成查数与对照归因 | [UI-19](../ui/UI-19-business-ask.md) | AC-023 |
| 3.6 | 用问法发起专项报告 | [UI-19](../ui/UI-19-business-ask.md) | AC-025 |
| 3.7 | 遇到模糊问法时补齐条件 | [UI-19](../ui/UI-19-business-ask.md) | AC-023 |
| 3.8 | 设置异常规则与阈值版本 | [UI-18](../ui/UI-18-diagnosis.md) | AC-021 |
| 3.9 | 复算五层量率贡献 | [UI-18](../ui/UI-18-diagnosis.md) | AC-022 |
| 3.10 | 切换下钻维度并核对余量 | [UI-18](../ui/UI-18-diagnosis.md) | AC-022 |
| 3.11 | 用趋势检验异常并提出待核假设 | [UI-18](../ui/UI-18-diagnosis.md) | AC-022 |
| 3.12 | 创建带验证条件的改进项 | [UI-23](../ui/UI-23-action-list.md) | AC-027 |
| 4.1 | 估算接触转化调整的影响量级 | [UI-20](../ui/UI-20-estimate.md) | AC-024 |
| 4.2 | 用历史样本比较原规则和候选规则 | [UI-15](../ui/UI-15-run-result.md) | AC-014 |
| 4.3 | 处理原规则复算与历史实际不一致 | [UI-15](../ui/UI-15-run-result.md) | AC-015 |
| 4.4 | 处理仅有汇总数据的回放 | [UI-13](../ui/UI-13-case-detail.md) | AC-015 |
| 4.5 | 保存验收案例并移交活动工作台 | [UI-15](../ui/UI-15-run-result.md) | AC-016 |
| 5.1 | 核对活动与策略版本并接收案例 | [UI-03](../ui/UI-03-activity-detail.md) | AC-002 |
| 5.2 | 导入模拟预发并核对一致性 | [UI-16](../ui/UI-16-preflight.md) | AC-016 |
| 5.3 | 登记模拟行内发布回执 | [UI-03](../ui/UI-03-activity-detail.md) | AC-017 |
| 5.4 | 沿原范围查看下期观察 | [UI-24](../ui/UI-24-action-detail.md) | AC-028 |
| 6.1 | 生成、审阅和导出复盘报告 | [UI-21](../ui/UI-21-report-list.md) | AC-025 |
| 6.2 | 审阅客户经理渠道专项报告 | [UI-22](../ui/UI-22-report-detail.md) | AC-025 |
| 6.3 | 保留部分可比报告草稿 | [UI-22](../ui/UI-22-report-detail.md) | AC-025 |
| 6.4 | 缺本期或基准时导出取数清单 | [UI-22](../ui/UI-22-report-detail.md) | AC-025 |
| 6.5 | 签认本次复盘并保存版本 | [UI-22](../ui/UI-22-report-detail.md) | AC-026 |
| 6.6 | 查看、分派和跟踪改进项 | [UI-23](../ui/UI-23-action-list.md) | AC-027 |
| 6.7 | 保存下期复核意见 | [UI-24](../ui/UI-24-action-detail.md) | AC-028 |
| 6.8 | 导入模拟补数并重新审阅 | [UI-08](../ui/UI-08-snapshots.md) | AC-007 |
| 6.9 | 查阅和导出历史签认版本 | [UI-22](../ui/UI-22-report-detail.md) | AC-026 |

[历史验收清单](../reference/prototype-acceptance-v0.1.md) · [本包验收计划](../qa/ACCEPTANCE.md)
