# CampaignLab 开发交接包

版本 1.0.0，2026-11-12。交接对象为在本机接手实现的 Codex 与技术负责人。

**选型已由发起人确认，包内规范用于实施。** 首版交付本地单机 Web 工作台，贯通满额赠券的规则验证和远程回拨的策略复盘。产品设计覆盖逐页交互、对象、接口、存储、数据接入、计算、运行、测试与角色职责。实现验收由后续开发与独立 QA 提交实测证据。

## 接手顺序

1. 解压后用本机 Codex 打开本目录或在新 Git 工作区中完整保留本包。先阅读 [本机 Codex 启动任务](START-CODEX.md) 和 [AGENTS.md](AGENTS.md)。
2. 在解压根目录用 Python 3.11 及以上并带 SQLite 3.38 或以上和 JSON 函数执行 `python3 qa/verify_package.py`。该脚本使用标准库，校验包完整性、接口与页面引用、样本计算和参考 DDL。
3. 阅读 [规格索引](SPEC_INDEX.md)、[产品与流程](product/PRODUCT.md)、[开发阶段与验收](framework/DELIVERY.md)。按 M0 至 M5 实施，每阶段给出运行证据。功能变更通过 ADR 和用例同步追踪。
4. 页面以 [逐页目录](ui/INDEX.md) 为入口。开发引用 [OpenAPI](contracts/openapi.json)、[SQLite DDL](contracts/sqlite-v1.sql)、[规则版本 Schema](contracts/rule-set.schema.json)、[案例输入 Schema](contracts/case-input.schema.json) 和对应业务契约。首跑输入与期望在 [样例说明](fixtures/README.md)。
5. 发布前按 [验收计划](qa/ACCEPTANCE.md) 重跑双流程、恢复演练和失败分支。将观察到的结果与当前提交、锁文件、数据和契约摘要一并归档。

## 裁定依据

| 优先级 | 依据 | 使用方式 |
|---|---|---|
| 1 | [选型批准与后续决定](decisions/ADR-001-approved-scope.md) | 确定首版范围、技术栈和系统职责 |
| 2 | 本包领域契约、OpenAPI、逐页设计与验收 | 共同约束行为。同一字段和状态冲突时，按问题单修复相关契约 |
| 3 | [跨行约定](reference/cross-bank-principle.md)、[历史验收](reference/prototype-acceptance-v0.1.md) 和合成样例 | 提供需求来源和演示回归基线。真实行内语义由授权输入补齐 |
| 4 | [产品对标](research/BENCHMARK.md)、[后续研究](research/NEXT-RESEARCH.md) | 公开事实和待检验假设，用于产品迭代决策 |

本包可离线阅读与核验。应用首次构建的 Python、Node 和浏览器依赖由目标机已批准的软件源或预置缓存提供。手工执行工作仍由本机 Codex 承担。数据样例为合成数据。

[本包校验清单](SHA256SUMS) 覆盖解压目录内全部交付文件。
