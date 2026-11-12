# 全行月报第一个可复算样例

所有数据是新造合成数据，同一模拟银行、两分行、六渠道。2026 年 7–10 月为演示时间轴。数值、组织名、客户键与银行报告无对应。样例不替代基座甲乙两银行及两条原业务流程。

| 文件 | 次序与目的 |
|---|---|
| [map-monthly.json](map-monthly.json) | SOURCE_JSON 标准宽表映射，`DISTINCT_CUSTOMER`。四个快照使用同一映射 |
| [source-01-partial.json](source-01-partial.json) | MR-SYN-001。2026-08 企微未采集；2026-09 恢复。首个全行月报取 2026-09 |
| [source-02-backfilled.json](source-02-backfilled.json) | MR-SYN-002。先导入 01，再全量导入 02。补采 08 企微，生成可签认草稿 |
| [source-03-corrected.json](source-03-corrected.json) | MR-SYN-003。先保留 02 签认报告及另一份未签草稿，再导入。9 月 AUM 更正，核对旧签认、旧草稿和版本链 |
| [source-04-next.json](source-04-next.json) | MR-SYN-004。按正常新月发布，取 2026-10 做远程单位有效触达的下期观察 |
| [csv-equivalent](csv-equivalent) | 01 的标准 CSV 等价输入。metadata.json 上传为 __metadata__，切片 CSV 上传为 monthly_touch_slices |
| [request-examples.json](request-examples.json) | 复盘、报告、行动和复核请求体。将 LOOKUP-* 替换为本次运行真实对象 ID |
| [monthly-golden.json](monthly-golden.json) | 合成输入的数值预期。金额分、率小数、人数户。界面舍入两位，原始计算按契约精度 |
| 原包 fixtures/metric-dictionary.json、fixtures/questions.json | 常规复盘沿用原包内的只读基座样例 |

## 从导入到下期复核

1. 新建 source_class 为 SYNTHETIC 的工作区，导入 01，设置映射，校验并发布。用发布返回的 snapshot ID 计算月报。核对「观察 +2、可比 +1、范围差 +1」。三月图查看 7/4/6 与 6/4/5。
2. 生成部分报告。取报告及缺口证据，验证不可签认。发布 02，用同月计算生成修订报告，签认后下载。另生成一份未签草稿。
3. 用 02 月报的远程单位触达证据建改进项，按基座操作将其推进到 WAITING_VALIDATION。04 快照生成 10 月月报，用同口径指标填 OBSERVED。可先保留该结果，再执行第 4 步的迟到修订。
4. 发布 03，比较 UNION 的 AUM 新旧值，核对旧签认原摘要仍可查，未签旧稿已过期。更正影响的行动以证据定位后标记重审。用 04 中同口径数据重做观察并留版本记录。
5. 可直接使用 csv-equivalent。也可用同一元数据作为 `__metadata__`，将 `monthly_touch_slices` 的 columns 作首行、rows 写数据行，null 用空字段；按原接入约定保存至独立合成工作区。用断言核对相同快照内容与各自文件证据。

三月趋势中 8 月空值只落在缺采渠道；全行观察行明确为已采集渠道。样例源切片的金额字段为空，月报产能取客户-月权威金额。普通 A-001 回归在基座快照执行。离线校验复算黄金算术；运行态报告、UI 与修订由实现 Agent 执行 AC-MR 用例。
