# 文件接入与指标来源契约

## 导入通道

| 格式 | 输入与组装 | 支持边界 |
|---|---|---|
| LEGACY_SYNTHETIC_JSON | 原型 v0.1 单 JSON，见 [甲乙样本](../fixtures/README.md)。解析 schemaVersion、synthetic、bankId、snapshotVersion、mapping、tables、metadata | synthetic 必须 true，保留原编号和元数据。内嵌映射由后端生成配置，映射与文件摘要固定 |
| SOURCE_JSON | 一个 UTF-8 JSON，含 tables 和 metadata，见 [源文件 Schema](../contracts/source-json.schema.json)。映射通过 configureImport 配置 | 结构化列和行，授权标签从工作区取。数据源字典与时间范围显式提供 |
| SOURCE_CSV | 一个导入任务承载多份 CSV。逐表调用 attachImportFile。必需一个 table_name 为 __metadata__ 的 JSON 文件，结构为 [元数据 Schema](../contracts/source-metadata.schema.json) | 首行为列名，表名称随上传传入。导入向导显示缺少的表和字典。金额小数字符串按映射单位解析 |

createImport 返回导入对象。修改文件或映射使此前验证失效并递增 revision。支持状态流 RECEIVED → CONFIGURED → VALIDATING → VALID 或 INVALID → PUBLISHING → PUBLISHED。VALIDATING、PUBLISHING 期间文件与映射只读。校验的业务问题记入 INVALID 与结构化 issues。技术失败回到可重试的稳定状态，关联 FAILED 作业。已发布记录只读。多个表必需同一完整快照，必填列的结构错误阻止发布。发布在同一事务更新 import 与 snapshot 的索引。

## 映射和标准表

[映射 Schema](../contracts/source-mapping.schema.json) 的 dimensions、count_fields、money_fields 键为下表规范键。表内每个源列名字只出现一次。codes 按规范维度为键，映射源代码至标准值。wide 的阶段来自 entity_table。long 的阶段先按长表切片键和指标码唯一连接。未知切片、重复码、缺必填阶段、映射引用不存在列均报错。甲行金额元乘 100，乙行分保持原整数。超出精度报 INVALID_MONEY。余额增量可为负，销量为非负。缺值以 null 表达并带证据。

| 文件与粒度 | 字段 |
|---|---|
| slices.parquet，每行一个源切片 | id、period、cutoff、branch、subbranch、channel、strategy、origin、segment、tag、definition、batch、cohort、offset、customer_key、source_row。source_row 由导入器生成，含 source_file_id、table_name、row_number。类型 ID 或字符串，cutoff 为 DATE，offset 为 BIGINT，未适用字段可空 |
| 人数与次数，在切片列 | eligible、sent、success、executed、contacted、effective、capacity、intentCount、activityCount。BIGINT 非负。名单阶段链逐级不增。容量、意向次数、活动特色依字典单位 |
| 金额，在切片列 | aum、deposit、wealth、fund、loan、wealthSale、nonCashWealthSale、fundSale、nonMoneyFundSale、insuranceSale、depositDemand、depositTerm。BIGINT 分，可空 |
| metadata.json | bank、机构及策略、活动及有效关联、渠道、覆盖、截止、口径语义键、目标、关联政策、制品清单、source_class。原型补充的历史事件和演示预发样本映射为可选只读来源，不在发布时自动确认案例 |
| 可选的触达和结果明细 | 触达含 touch_id、customer、strategy、node、batch、channel、dispatchDate、at。结果含 id、customer、date、amount_fen。时间窗口表见下文。按 workspace 与 snapshot 隔离 |

月份和日期用解析器校验日历，cutoff 必须在 period。字典引用存在，来源与策略匹配，整数、比例和布尔类型严格区分。相同银行和版本标签仅允许同摘要复用。校验摘要覆盖文件原始 SHA、映射内容、元数据及解析器版本。分析快照摘要覆盖完整标准表和元数据的逻辑投影。新发布时校验摘要必须仍匹配。相同标准数值的不同来源允许同一比较值并保留各自证据。

## 去重和可比性

- SYNTHETIC_INTERVAL 只用于合成数据。以银行快照、period、cohort 分组，逐阶段求半开区间 [offset, offset+count) 的并集长度。相邻区间允许合并。多月相加为客户月次。
- DISTINCT_CUSTOMER 仅接收授权的范围内键，每客户切片的名单阶段为 0 或 1。按客户键、月、所选维度查询，同一客户跨策略和渠道取并集。个人键不跨银行拼接。
- AGGREGATE_ONLY 可显示来源明确的单一聚合范围和同口径两期对比。多行范围内缺交集时，人数显示待补去重证据。金额与次数按已明确可加范围聚合。汇总支持条件试算，逐笔历史回放还需事件和实测。
- 每个本期和基准配对以渠道、统计范围、采集状态、语义键和截止进度判断。月结与月结可比。月中按日序且源定义相同才配对。覆盖恢复可保留本期原值，变化只用共同子集。
- 口径 semantic_key 表示已经声明的同义定义。相同显示名可以不同 semantic_key。乙行推送最短 3 秒有独立语义键，比较保留 A、B 原值和差异原因。业务负责人确认同义后，通过新映射和快照记录证据。

## 渠道事件重算

在同一快照下使用配置版本。以下为合成方案。每个后继阶段都要求前阶段成立。

| 渠道 | 下发、接收 | 执行、接触 | 有效接触 |
|---|---|---|---|
| 短信 sms | 候选下发、节点接收 | 已尝试发送、短链点击 | 已访问详情 |
| 手机银行推送 push | 候选下发、节点接收 | 已送达、短链点击 | 已访问详情且停留达到该快照门槛，A 为 0，B 为 3 秒 |
| 企业微信 wechat | 候选下发、节点接收 | 已有会话或通话时长正数、消息送达或通话时长正数 | 交互一轮、通话 60 秒、点击短链，任一成立 |
| AI 外呼 ai | 节点接收、接收且通过频控 | 已拨打、接通 | 有效交互至少一轮 |
| 远程 remote | 候选下发、节点接收 | 已拨打且在有效窗、接通 | 财私至少 60 秒，个贷至少 10 秒 |
| 客户经理 manager | 候选下发、节点接收 | 已执行且在有效窗、接通或成功接触 | 采用下游有效判定。5+1 完整定义待行内确认 |

关联方向固定为「结果日减触达日」和「下发日减触达日」，按业务日期计算，不用时间戳整天截断。LINK-1 远程结果窗 0–7 天且下发差 0 或 10，推送结果窗 30–60 天且下发差为 0，端点包含。先客户键和渠道筛候选，再算两种差。只有一条匹配自动显示唯一。多条默认待核。选择 NEAREST 只接受唯一最小非负结果日差，最小值相同仍待核。结果无匹配显示待补。查询展示所有参与验证候选和来源。关联验证结果作为证据记录，采用结果后产生新的上游快照或更正输入。

## 更正和发布边界

correctSnapshot 对已发布快照的特定切片金额提交显式新值和证据。支持更正链，版本后缀 R1、R2 由服务分配。更正保持原快照、报告与导出，触发依赖旧范围且命中补数行的改进项复核。数据范围和受影响程度随任务证据记录。需要补采渠道或调整定义时用新导入和新版本，按相同兼容规则运行。

Legacy 活动绑定的 from、to 为含端点月份，导入时转为首月第一天含、末月下一个月第一天不含。策略版本来自来源字典。标准导入的 valid_until 直接采用排除端点。预发、回放、目标、关联窗口等原型元数据仅作为合成来源，作用域与口径在业务页确认。

发布后 Snapshot.source_activities 提供来源活动和绑定线索，用户可在活动工作台从这些线索建本地活动和确认绑定。工作区创建事务预置「默认阈值」版本，参数见分析黄金样例。每次映射实际变更保存为新映射 ID，老快照仍引用原版。
