# 合成输入与黄金结果

| 文件 | 用法 |
|---|---|
| banks/bank-a.json、banks/bank-b.json | 原型 v0.1 合成宽表、长表，分别 510 个切片。B 有 4590 阶段项。上传为 LEGACY_SYNTHETIC_JSON |
| banks/map-a.json、banks/map-b.json | 同两份来源的标准映射对象。CSV 小样本用 map-a |
| banks/csv-mini/slices.csv 与 metadata.json | 六行小样本。slices.csv 的 table_name 为「月度宽表」，元数据上传使用 __metadata__，snapshot_code 为 A-CSV-001 |
| banks/csv-mini/source.json | 同六行的 SOURCE_JSON 形式。测试时可使用另一工作区区分两入口 |
| metric-dictionary.json | 指标、公式和别名。证据和定义版本由所选快照实际补齐 |
| analytics-golden.json | 默认复盘、比较、分母、异常拆解、估算、更正及关联预期 |
| cases/rules.json | 四个规则版本，满额赠券两个退款口径和回拨两个优先级 |
| cases/golden-cases.json | 12 条赠券和 3 条历史回拨。expected_baseline/candidate 为业务预期，observed_original 为来源实际 |
| cases/preflight-vectors.json | 五条预发状态向量，MATCH 表示使用运行结果的当前摘要，DIFFERENT 表示构造另一摘要 |
| questions.json | 原型 60 条问题转成受控计划和黄金结果。默认 A-001 与 2026-10 上下文。随快照和有效过滤参数重新执行 |
| api-examples.json | 核心接口请求体与预期指针。资源 ID 在测试用例解析为实际 ID |

问法预期中的 current_values 保存原型计算值，金额已转分，比率为小数。钱款与整数用精确相等，比率及均值按 1e−12 容差校对，正式计算按当前契约。legacy_report_state 是原型同条件的历史结果。应用报告状态按当前契约和输入证据判定。

样例全部为合成，可用于本机开发、QA 和竞品同题测试。银行授权数据按照独立输入和权限管理。
