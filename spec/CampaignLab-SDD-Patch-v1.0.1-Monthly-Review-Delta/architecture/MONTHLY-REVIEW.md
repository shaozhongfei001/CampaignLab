# 全行月度经营复盘实施契约

版本 1.0.1。以 [分析契约](ANALYTICS.append.md) 为业务计算依据。本页约定 M1、M3、M4 的输入输出。基座是 CampaignLab-SDD v1.0.0。

## 1. 扩展数据与发布

使用 v1.0 `SOURCE_JSON` 或 `SOURCE_CSV`，继续先配映射、校验再发布。两种标准格式的元数据都可带 `monthly_review`，增量类型见 [契约节点补丁](../contracts/monthly-contract-delta.json)，导入 JSON 与 CSV 元数据共用 MonthlySource。旧格式和没有该扩展的数据按原流程导入。初次实现优先使用包内 SOURCE_JSON 验证；CSV 用相同元数据和同一归一器验证等价。

| 数据 | 标准粒度 | 校验和留痕 |
|---|---|---|
| 原源表与映射 | v1.0 标准切片，`dedup_mode=DISTINCT_CUSTOMER` | 切片有 `customer_key`、月末截止、策略、机构、渠道、定义和源行。五层为 0/1 且逐层不增。策略来源与字典一致。重复切片 ID、跨月/渠道错误定义、未采集渠道存在切片均阻止发布 |
| `months` | period 唯一 | 固定 `scope_key`、`eligibility_key`、`outcome_key`、`cohort_key`、清册和自主活动状态、每月已覆盖的产能指标。定义键由同一银行版本化管理，键相同表示已核同义。同月月结 roster、源文件及 scope key 可定位 |
| `customers` | period × customer_key 唯一 | 归属分行引用元数据字典。完整清册必须覆盖触达切片全部客户。活动来源状态为 COMPLETE 时，清册无 UNKNOWN 自主活动。非完整清册仅用于明示可核明细 |
| `outcomes` | period × customer_key × metric_id 唯一 | 关联同月清册。某指标已声明覆盖，则该月全清册每户都有一行，零也显式提供。未覆盖指标不收金额。余额增量有符号，五项销量非负。输入字段和单位为整数分 |
| `capacity` | period × channel_id 唯一 | 两值任一可 null，零保持零。远程和 AI 的单位必须 CALL_ATTEMPT。容量、用量单位相同，均为同月已授权可核原值 |
| `revision` | 可选，指向已发布前版本 | 在同一银行同一工作区内解析 `supersedes_snapshot_code`。新 snapshot_code，受影响月份仍存在且写清 reason。每份已发布快照只能被一次直接继任；同内容重放复用已发布记录。先按原幂等规则查重，再在发布事务重验前版本和最新性，冲突返回 409 SNAPSHOT_SUPERSEDED |

扩展声明必须与归一数据一致。缺源但未声称完整时允许发布并给出缺项；已声称完整而不完整返回 INVALID，issues 定位原表行或 JSON Pointer（如 `/metadata/monthly_review/outcomes/7/value_fen`），校验作业没有业务异常地结束。建议问题码 `MONTHLY_DUPLICATE_KEY`、`MONTHLY_REFERENCE_MISSING`、`MONTHLY_COVERAGE_CONFLICT`、`MONTHLY_INVALID_UNIT`。验证存在但待补时在复盘返回可用值与证据问题。导入详情沿用 issues，月报输入按客户、产能、容量三类发 INFO（到齐）或 WARNING（待补）。使用源指针定位。

发布复用不可变快照制品。将客户、产能、容量分别归一为 `monthly_customers.parquet`、`monthly_outcomes.parquet`、`monthly_capacity.parquet`；月目录、版本和修订信息入 metadata.json，源定位保留 source_file_id、table_name+row_number 或 JSON Pointer。SQLite 复用 snapshots.metadata_json、artifact_id、correction_of，已存在的数据不用迁移。月份、分行、产能、容量用 DuckDB 查询；切片先按渠道/策略/来源筛选，构造 DISTINCT 客户集合后再与产能事实连接。严禁在多个触达行 JOIN 后直接 SUM 客户-月金额。

月报补采或产能更正以完整新文件重导并传 revision，旧制品保留。原 `correctSnapshot` 不直接改带月报扩展的快照，返回 422 `MONTHLY_REIMPORT_REQUIRED` 与补导说明，避免源切片、产能事实有两套更正。旧快照走原来流程。月报 v1 首次支持全量文件、复用原大小与行数上限，实际行内体量通过试点衡量。

## 2. 接口和结果

将 [契约节点补丁](../contracts/monthly-contract-delta.json) 合入当前 OpenAPI 后进行代码生成。基座操作编号、响应头、作业类型、对象和路由沿用。只有 `ReviewCreate.profile` 和 `Review.monthly_review` 两个可选字段及 `Monthly*` 类型新增。普通客户端不发 profile，服务端保持原响应结构（不附 null 扩展字段）。

| 操作 | 补丁约定 |
|---|---|
| `runReview → getJob → getReview` | 请求 `{"profile":"BANK_MONTHLY_V1","scope":{"snapshot_id":"<已发布 ID>","period":"2026-09","baseline":{"kind":"previous"}}}`。允许空的维度数组和 ALL 来源，忽略其缺省差异并统一规范化。若传 cutoff 只能等于焦点月末。group_by、非空 periods、非空筛选、非 previous 基准、非 MONTH_END 客层或其他范围冲突给 422 `MONTHLY_INVALID_SCOPE`。工作区越权给原 404。无月报扩展时作业仍产生缺数结果与取数清单。 |
| `getReview` | 原 Review 字段按同 Scope 的常规计算填充，保留其含义。月报页只读 `monthly_review`。新结果随原 Review job 保存一个制品，输入固定快照、规范化范围、profile 与计算版本。摘要覆盖月报稳定业务字段、快照和定义键；排除临时 ID、请求时间与异步进度。相同快照和参数业务值一致。 |
| `getEvidence` | 优先返回安全聚合来源。定位到口径键、源文件 SHA、期/月/渠道、源位置、覆盖集合、分子分母、结果与复算方法。证据不向客户端回传客户键、原逐客金额或源行客户字段。权限按基座验证。 |
| `createReport → getReport` | 月报 Review 走既有 TOPIC，`diagnosis_id`、`question_id` 留空。该 Review 的其他 kind 返回 422 `MONTHLY_REPORT_KIND_REQUIRED`。其他专题和普通报告保持原分支。 |
| `createAction → reviewAction` | 沿用 `review_id` 和证据，观察用 `OBSERVED`；验证时下期月报与当前月报同银行且口径、目标维度和共同范围可比。无可比观察记录 `NEEDS_MORE_DATA`。候选规则命中需原规则链、预发和回执才可用 MATCHED。 |
| `createExport` | 月报 Report 的 REPORT_MD、MISSING_CSV、EVIDENCE_ZIP 沿用；月报 Review 的 REVIEW_CSV 从月报结果出聚合行，UTF-8 BOM，列 `section,period,baseline_period,row_key,metric_id,unit,value,state,numerator,denominator,coverage_key,definition_ids,evidence_ids`。比较数值在 metric_id 后追加 `.observed_delta`、`.comparable_delta`、`.coverage_gap_delta`，用来源指标单位。 |

`monthly_review` 字段绑定如下。所有 `metrics` 项复用 v1.0 Measure，结果顺序按月份、六渠道固定序 remote/manager/ai/wechat/sms/push、表中枚举顺序，组和分行按 ID。BANK key 为 bank_id，BRANCH key 为分行 ID，GROUP key 为 G- 加原组标签 UTF-8 的 SHA-256 前 24 位，label 为源组标签。指标不可算时输出带状态的 Measure。全局缺项使用原 Issue 形状。

| 结果字段 | 粒度及指标 ID |
|---|---|
| `periods, focus_period, common_channels, issues, state` | 固定三月；全三月可比渠道和总体就绪度；未采集、定义冲突、版本不一均指明具体月份和影响 |
| `trend[]` | 每月全行及各渠道。覆盖、定义和 Measure，`monthly.effective_customers`。全行 observed_channels 为当月已采集范围，comparable_channels 为三月共集。单渠道用自身范围 |
| `comparisons[]` | 焦点对两个基准、全行和各渠道各一行。两个原值、共同子集的两个重算值、绝对差、相对差与范围差。有效触达 Measure ID 同上，字段区分基准与结果 |
| `participation[]` | 每月 bank/group/branch × ALL/branch。metrics 为 `monthly.eligible`、`monthly.sent`、`monthly.success`、`monthly.sent_coverage`、`monthly.success_coverage`、`monthly.sent_outside_pool`、`monthly.success_outside_pool`、`monthly.participating_branches`、`monthly.strategy_count`、`monthly.mean_strategy_per_participating_branch`。组覆盖率的 Measure 分子是分行率之和，分母为有效分行数 |
| `capacity[]` | 每月×渠道。metrics 为 `monthly.capacity`、`monthly.used`、`monthly.utilization`、`monthly.effective_customers`、`monthly.effective_per_unit`、`aum`、`monthly.aum_fen_per_effective`、已覆盖销量；`comparable_to_previous` 表示容量及触达口径都可比，跨月 AUM/销量另按 outcome_key 校验 |
| `production[]` | 每月×COHORT/SEGMENT/LIFECYCLE×类别，`monthly.customers` 和已覆盖产能；产能份额 ID `monthly.share.<metric_id>`。COHORT = STRATEGY/SELF_MANAGED/ORGANIC/OTHER，SEGMENT 与 LIFECYCLE 按源枚举。客层率 ID `monthly.strategy_segment_reach`，分母为该层清册 |
| `origin_overlap[]` | 每月×HQ_ONLY/BRANCH_ONLY/BOTH/UNION/BRANCH_WITH_OVERLAP。metrics 为 `monthly.customers`、已覆盖产能。BRANCH_WITH_OVERLAP 行额外带 `monthly.share.<metric_id>`，按同月 UNION 作分母 |

PERSON 为客户数，BRANCH/STRATEGY 为对应整数，容量和使用量为 EVENT 并带 capacity_unit；金额和客均金额用 CNY_FEN，客均的行标题写「分/户」，Measure 记录分子和分母；每单位触达、利用率、份额、覆盖率复用 RATIO，均值用 STRATEGY/分行的业务标签。MISSING 指标给空值、可核的分子分母及原因。结果汇总不包含客户列表。

### 改进项与指标证据绑定

月报页创建改进项时携带一个主计算证据 ID。首个样例支持触达户数与每单位有效触达目标。用现有 COMPUTATION Evidence，source_id 为该 Review ID，location 为指向结果 Measure 的 JSON Pointer。证据在冻结 Review 时生成。服务端在创建时验证指针、归属与摘要，并据该行定位 `metric_id`、`channel_id`、期间、覆盖集及定义键。其他补充证据可随同保留。没有唯一可比主证据时返回 422 `MONTHLY_ACTION_TARGET_REQUIRED`。常规改进项按原路径。

下期选择晚于原焦点月的月报；服务端从同一银行的两个快照解析主指标。每单位有效触达需同渠道、月结、相同 scope_key、触达与容量语义、单位以及两期正用量。全渠道户数按 §2 的共同渠道重算。可比结果带两份 Evidence 和绝对差，写入原 followup；没有可比观察保存 NEEDS_MORE_DATA，保持 WAITING_VALIDATION。候选 MATCHED 另验基座所需案例、预发和回执。

## 3. 报告正文、签认、补数

报告七章键依次为 `summary`（结论摘要）、`reach_trend`（三月趋势与范围桥）、`participation`（分行双覆盖）、`channel_capacity`（渠道容量与效率）、`production`（客群产能、销量、总分行去重）、`actions`（待核原因、改进与复核）、`appendix`（快照、来源、口径、缺项、摘要）。正文从冻结月报结果渲染，复算数据不随导出时最新快照漂移。观察、待核解释、行动和实验用明确标签。缺数清单按月、渠道、指标和材料责任定位。

| 月报就绪 | 条件 | 报告 |
|---|---|---|
| MISSING | 焦点月没有月结可核的已采集触达来源，含未提供扩展 | DATA_REQUIRED。仅列取数清单 |
| PARTIAL | 有焦点月原值，但三月未全六渠道同义、清册或自主来源不完整、全行去重不可证、远程/AI 容量/用量缺失或容量为零、必需产能缺项 | PARTIAL_DRAFT。标明可用范围和待补，不可签认 |
| FULL | 三月均为同口径全六渠道月结；月目录、清册、自主来源、客户身份、总分行集合齐备；三个月远程/AI 容量和用量有值且容量大于零并同单位同语义；`aum` 和五项销量覆盖三月、口径相同 | DRAFT_READY。允许按原签认协议固定报告与证据 |

月度清册明确为空、正数分母不存在等业务情形按对应 Measure 处理。客群和总分行各行的 state 按该月该维度的集合与必需金额判定，缺可核集合为 MISSING，可核集合但必需金额缺失为 PARTIAL，其余 FULL。整个窗口 PARTIAL 时某个已完整月份仍可有 FULL 行。非必需产能指标缺项列入附录。上述 FULL 还要求三月 `scope_key`、`eligibility_key`、`cohort_key`、`outcome_key` 一致。只要新快照沿修订链命中同范围，未签认旧稿 stale。签认在事务中复核 If-Match、报告摘要和新版本；状态冲突 409、修订号冲突按原 412。已签认的内容、摘要、证据、下载均可回看。报告修订使用新快照的新月报 Review、`previous_report_id`、`revision_reason`，与旧报告并列显示。行动中受修订影响的既有验证按基座规则重审。完整案例见 [样例说明](../fixtures/MONTHLY-FIXTURES.md)。
