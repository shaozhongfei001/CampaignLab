# 同类产品对标与差异设计

公开资料核对日期 2026-11-12。证据以官方操作说明为主，适用产品版本、数据和权限以来源页面为准。表中右两列为 CampaignLab 实施假设与可检查结果。

| 证据 | 公开可查能力 | 差异设计 | 同题验证 |
|---|---|---|---|
| E01 Talon.One 官方活动及集成文档 | 活动暂存后可测试，支持的干跑请求可指定模拟时间并返回规则失败原因。证据强，依赖该平台应用、活动规则和测试权限 | 绑定两个可复查的规则版本，按同一交易序列显示首次差异、券与预算分录、需人工处理项 | 用 99.99/100 元、重复支付、部分退款同题比较，记录规则发现、轨迹完整和可移交预期。[暂存](https://docs.talon.one/docs/product/campaigns/create-and-manage-campaigns) · [Dry requests](https://docs.talon.one/docs/dev/integration-api/best-practices) · [规则失败原因](https://docs.talon.one/docs/product/applications/overview) |
| E02 Pega Customer Decision Hub | Audience Simulation 逐层展示策略过滤规模，Impact Analyzer 使用对照组实验。证据强，依赖配置好的策略、测试环境及实验上下文 | 保留统计拆解、试算、实际观察和实验各自的证据类型，从一次业务偏差转为可复跑验收案例 | 同一批 SIM 样本核对原规则、频控和候选优先级。观察结果能定位到行为和版本。[Audience Simulation](https://academy.pega.com/topic/audience-simulation/v1/in/23166/25916/25946) · [Impact Analyzer](https://academy.pega.com/sites/default/files/media/documents/2024-10/MIS20301-8-EN-StudentGuide.pdf) |
| E03 Adobe Journey Optimizer 与 Customer Journey Analytics | 干跑基于实际受众数据模拟路径，消息动作在该模式禁用。CJA 支持自定义漏斗触点。证据强，依赖 Adobe 环境、配置和可用数据 | 固定范围、截止和指标分母，将离线仿真、历史回放和预发证据关联为同一案例 | 检查 15% 经营率与 50% 层间率，预发版本变化后能定位待复测案例。[Journey Dry run](https://experienceleague.adobe.com/en/docs/journey-optimizer/using/orchestrate-journeys/create-journey/validate-journey/journey-dry-run) · [Fallout](https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-workspace/visualizations/fallout/configuring-fallout) |
| E04 Salesforce Marketing Cloud Intelligence | 提供营销数据模型及多来源协调能力。证据强，适用于它的营销数据模型与映射工作流 | 同一代码以 A/B 配置复用。区分字段映射与定义、截止、客户去重、关联窗口，保留原值 | 远程同义对齐，推送定义不同时解释为何不能直接比较。记录接入改动量。[Harmonize Your Data](https://help.salesforce.com/s/articleView?id=mktg.dato_harmonize.htm&language=en_US&type=5) |
| E05 神策智能运营 | 运营计划按目标和渠道观察趋势，可按策略组和对照组评估。证据强，依赖原计划与采集数据 | 异常、报告、责任人与规则验收案例关联，下一期可回查试算、实测及正式来源 | 复盘发现可独立交给下一位业务人员重跑，再验证签认修订和复核。[运营计划效果评估](https://manual.sensorsdata.cn/sf/docs/plan_report) |
| E06 Salesforce Loyalty Management | 交易日志仿真展示规则条件的满足情况。证据强，依赖交易日志与适用的会员流程 | 在定义明确的赠券样例中并排呈现多版本状态和账本，支持与外部预发逐字段核验 | 对付 120 元再退 25 元，验证撤券、次数回退与已核销待人工。[交易日志模拟](https://help.salesforce.com/s/articleView?id=xcloud.promotion_setup_processing_simulation.htm&language=en_US&type=5) |

## 比较方法

用同一合成任务、同样规则说明、同样初始状态与有限时间比较。记录独立完成率、首次耗时、漏检、误报、需要手写转换的范围、证据能否被第二人复跑。若竞品因许可、环境或数据粒度无法测，记录条件和证据缺口。继续比较现有平台、Excel 和人工流程的同题成本。产品决策依据实际复用和交接质量。

差异落点有三个。规则对比能指出第一处差异及账本影响。跨行适配能证实同义并保留不同比较结果。复盘能生成可移交且可在下一版本重跑的验收案例。三项都纳入 [验收](../qa/ACCEPTANCE.md) 和 [进一步研究](NEXT-RESEARCH.md)。
