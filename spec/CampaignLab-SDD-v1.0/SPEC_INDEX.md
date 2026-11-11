# CampaignLab 规格索引

版本 1.0.0。发起人已确认产品和技术选型。以下设计契约用于本机开发，验收状态随实际证据登记。

| 契约 | 权威内容 | 维护角色 |
|---|---|---|
| [ADR-001](decisions/ADR-001-approved-scope.md) | 选型、范围、批准证据 | 项目负责人 |
| [ADR-002](decisions/ADR-002-implementation-details.md) | 首版设计细节、运行默认与演进依据 | 技术负责人 |
| [产品](product/PRODUCT.md) · [需求](product/REQUIREMENTS.md) · [追踪](product/TRACEABILITY.md) | 角色、业务流程、BR/FR/NFR，55 个材料及 47 个操作点 | 产品 |
| [总架构](architecture/ARCHITECTURE.md) · [业务对象](architecture/DOMAIN.md) | 部署、模块、持久化、对象边界、摘要 | 架构和服务端 |
| [服务接口](architecture/API.md) · [OpenAPI](contracts/openapi.json) · [操作索引](contracts/operations.json) | 方法、字段、响应、错误、并发与兼容 | 服务端 |
| [SQLite DDL](contracts/sqlite-v1.sql) · [作业](architecture/JOBS.md) · [运行](architecture/OPERATIONS.md) | 初始表、状态、恢复和权限 | 服务端和运行 |
| [数据接入](architecture/DATA.md) · [映射](contracts/source-mapping.schema.json) · [元数据](contracts/source-metadata.schema.json) · [JSON 接入](contracts/source-json.schema.json) | 源文件、映射、语义、版本与归一 | 数据 |
| [指标与问答](architecture/ANALYTICS.md) · [指标字典](fixtures/metric-dictionary.json) | 分母、比较、归因、试算和问法 | 数据 |
| [规则和回放](architecture/RULES.md) · [规则 Schema](contracts/rule-set.schema.json) · [输入 Schema](contracts/case-input.schema.json) | 两种规则、案例、回放、预发 | 规则 |
| [报告与改进](architecture/REPORTS.md) | 生成、签认、更正、复核和导出 | 产品和服务端 |
| [页面目录](ui/INDEX.md) · [公共规范](ui/COMMON.md) · [页面注册表](contracts/pages.json) | 26 个独立 Markdown 页面、路由、操作与验收 | 前端设计 |
| [工具链](framework/TOOLCHAIN.md) · [依赖范围](contracts/dependencies.json) · [Python](framework/PYTHON.md) · [数据](framework/DATA.md) · [前端](framework/FRONTEND.md) | 代码与工程标准、构建、环境与迁移 | 技术负责人 |
| [阶段与角色](framework/DELIVERY.md) · [实施任务](framework/IMPLEMENTATION-TASKS.md) · [本机启动任务](START-CODEX.md) | 实施顺序、角色、回执与独立复核 | 技术负责人 |
| [验收](qa/ACCEPTANCE.md) · [走查](qa/WORKFLOWS.md) · [合成样本](fixtures/README.md) · [包校验](qa/verify_package.py) · [核验记录](qa/PACKAGE-VERIFICATION.md) | 35 项应用验收、两条业务流程、数据与包检查 | 独立 QA |
| [对标](research/BENCHMARK.md) · [后续研究](research/NEXT-RESEARCH.md) | 来源、差异验收、实际机会与待行内证据 | 产品 |
| [追踪索引 JSON](contracts/traceability.json) · [历史原型](reference/prototype-acceptance-v0.1.md) · [原型程序验证](reference/prototype-results-v0.1.json) | 既有样例核查和来源状态 | 需求和 QA |

如修改一个业务字段，按使用它的页面、OpenAPI、存储、样例及 AC 查影响。运行结果和文档设计的验收状态分别记录。当前基础数据为合成输入。
