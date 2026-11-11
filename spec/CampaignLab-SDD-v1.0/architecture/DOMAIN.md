# 业务对象与存储契约

## 唯一标识和精度

API 对象键以 snake_case 表达。指标 ID 沿用原型字典，例如 effectiveRate。路径 ID 是受限的不透明标识。外部活动、规则版本和切片号单独保存，唯一性含银行和工作区。API 中 snapshot_id 为本地资源 ID，snapshot_code 是银行可读版本，例如 A-001。合成工作区的首次样例可用同名本地 ID，调用方从响应获取实际 ID。

时刻使用带偏移的 RFC 3339，持久层时刻归一到 UTC。业务日期按 Asia/Shanghai 投影。月份为 YYYY-MM。货币为人民币分的整数，传输和数据库的单笔范围见 Schema。分析汇总使用整型扩展或 Decimal，超范围时返回数值溢出。比率和统计值经 API 用十进制字符串。显示时半入到两位小数，判阈使用未显示舍入的计算值。

可复算摘要对业务输入和逻辑投影使用 UTF-8 JSON，键排序，无额外空格，保留数组顺序，字符串先 NFC。百分比使用普通十进制字符串并去冗余尾零，整数保持整数。省略项先展开约定默认值。SHA-256 以小写 64 位十六进制记录。制品摘要按原字节计算。业务摘要排除运行时间、作业号、租约和随机资源 ID，固定输入标识及内容版本仍参与。

## 对象与修改

| 对象 | 生命周期与约束 | 持久化 |
|---|---|---|
| 活动及绑定 | OPEN → ARCHIVED。绑定使用生效起日包含、截止日排除。相同策略同有效区间仅允许一条权威绑定。有依赖活动归档后可查询历史 | activities、activity_bindings |
| 规则版本 | DRAFT 可修改。CONFIRMED 固定字段和条款，变动时以 parent_rule_id 建新草稿。最近确认版本为活动候选规则，原规则版本可按源证据继续用于历史比较 | rule_versions、activities.current_rule_id |
| 案例 | DRAFT → CONFIRMED。编辑已确认案例通过子版本。每个父版本仅一条已确认直接后继。历史案例须记录观察值、原规则和来源。模拟案例人工确认预期 | cases |
| 导入、映射和快照 | 已发布快照不可变。配置内容同 ID 变更要求新 ID。更正产生新快照，原报告与作业仍指向原版本 | imports、import_files、source_mappings、snapshots |
| 计算、回放与候选 | 已产出结果固定输入及摘要。候选冻结人工确认的预期和版本。如果活动当前规则或确认案例改变，相关候选标为 STALE | analysis_results、runs、run_cases、candidates |
| 预发和版本回执 | 一批预发保留选择集、实际值、差异和审阅说明。新的证据批次生成新记录。回执绑定已审阅且仍一致的预发 | preflights、preflight_rows、receipts |
| 报告、改进和观察 | 签认固定内容，修订另建版本。改进可关联案例、报告和后续观察 | reports、actions、report_actions、action_followups |
| 证据、导出及作业 | 原文件、运行结果和报告制品按引用保留。证据定位至源行、规则、事件或确认记录 | artifacts、evidence、object_evidence、jobs、exports、audit |

说明中「冻结」指形成不可变版本。签认和归档均为本机产品内记录。正式业务责任见 [已确认选型](../decisions/ADR-001-approved-scope.md)。

## 数据库迁移约定

[SQLite 参考 DDL](../contracts/sqlite-v1.sql) 定义初始表、主键、外键、索引与检查约束。Alembic 首次迁移与 DDL 的结构应等价，比较 sqlite_master、PRAGMA table_info、foreign_key_list、index_list。所有连接开启外键。复杂可空引用和对象类型在领域服务校验，例如报告 review_id 必须是 review 类型，策略、案例、预发必须归属对应活动。object_evidence 的多态目标在同一事务内校验。不可变约束由领域服务、迁移测试及历史重读验证。

结构字段和状态以表头列为准。JSON 列保存相应已验证的请求、内容、结果指针或来源元数据，服务端组装响应。读取顺序稳定，以 created_at、id 做游标。日期、摘要长度和关联唯一性需在入库前校验。数据变更和审计事件同事务。事务外运行重计算与文件传输。

## 内容摘要的固定投影

| 内容 | 参与摘要的字段 |
|---|---|
| 规则 | content、按 key 排序的 terms、source_rule_version。规则标签和确认说明分别审计 |
| 案例 | input、mode、expected、observed_original、observed_rule_id、排序后的 source_evidence_ids |
| 快照 | schema_version、标准字段、按源切片 ID 排序的内容、字典与映射、原始文件摘要 |
| 分析 | 标准 Scope、定义版本、阈值版本、算法版本、结果业务字段和证据来源编号 |
| 回放 | 规则摘要、按请求顺序的案例摘要、引擎版本、Outcome 与 TraceStep 的业务字段 |
| 报告 | 快照和计算摘要、报告类别、范围、正文、前版本与证据引用。签认记录单独计算摘要 |

Revision 用于修改冲突控制，内容摘要用于业务版本、复现与证据引用。JSON 通过 Schema 验证再写入。回放总览返回案例摘要，getRunCase 逐个读取完整轨迹。列表按概要展示。复盘明细最多返回 1000 行，detail_count 保留总数，完整范围由 REVIEW_CSV 导出。
