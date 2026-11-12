# contracts/ 活契约溯源与变更治理

## 权威层级（冲突时自上而下）
1. `spec/CampaignLab-SDD-v1.0/` — 原基线，只读，字节可验。
   清单 `SHA256SUMS` 的 SHA256 = `3d3e32632c1d28368fc3fec4e591572dc73b0ed56eb89193e4c84d54e4ef3d91`；
   原始 ZIP `CampaignLab-SDD-Handoff-v1.0.zip` 的 SHA256 = `c8ac004c50f53ea08416807bd43a4b585784b31892513082e4aa635952850d81`。
2. `spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/` — 月报增量补丁，只读，字节可验。
   `DELTA-SHA256SUMS` 21 项全部 OK；源 ZIP SHA256 = `13b1be8cfa11c8b457f3d66eb3d9431e8238c15b5b0985b15d79dc3a1856c371`。
3. `contracts/`（本目录）— **活契约，实现唯一依据**。相对基线的每一处结构差异都必须登记在 `CHANGES.json`。

## 文件来源与规范化
| 文件 | 来源 | 与基线关系 |
|---|---|---|
| case-input.schema.json | v1.0 基线 | 逐字节相同 |
| dependencies.json | v1.0 基线 | 逐字节相同 |
| operations.json | v1.0 基线 | 逐字节相同 |
| pages.json | v1.0 基线 | 逐字节相同 |
| rule-set.schema.json | v1.0 基线 | 逐字节相同 |
| source-mapping.schema.json | v1.0 基线 | 逐字节相同 |
| traceability.json | v1.0 基线 | 逐字节相同 |
| sqlite-v1.sql | v1.0 基线 | 逐字节相同（门禁强制，不允许漂移） |
| openapi.json | v1.0 基线 + v1.0.1 补丁 + **CR-002** | 结构差异 **11** 处（含 CR-002 移除 `listWorkspaces.status` 的 1 处 `removed`）；JSON 规范化 indent=2 / ensure_ascii=False |
| source-json.schema.json | v1.0 基线 + v1.0.1 补丁 | 结构差异 1 处；同上规范化 |
| source-metadata.schema.json | v1.0 基线 + v1.0.1 补丁 | 结构差异 1 处；同上规范化 |
| CHANGES.json | 本仓自建 | 变更登记，非基线内容 |

规范化说明：合并由补丁工具 `--stage` 生成候选后整文件覆盖，因此这 3 个文件与基线**不再字节相同**。
所有比较一律走「解析后的结构比较」（`scripts/check_contracts.py`），字节真值永远以基线为准。

## 门禁命令
```bash
# 只读预检（补丁侧工具，分类 ADD/ALREADY/UPDATE/KEEP/CONFLICT，冲突退出码 2）
python3 spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/tools/monthly_delta.py --contracts-dir contracts

# 指针级差异审计
python3 scripts/check_contracts.py diff --base spec/CampaignLab-SDD-v1.0/contracts --live contracts

# CI 门禁：差异 ⇄ 登记一一对应 + CR/ADR 文件存在 + （可选）OpenAPI/JSON Schema 元校验
python3 scripts/check_contracts.py check --validate
```

## 变更规则（手册第 7 节）
- 只有 Lane T（编排器）能修改 `contracts/`；子智能体一律只读。
- 每处差异必须对应一个 CR 与一个 ADR；触及分母、状态、接口兼容、取数依据或资金模拟语义的必须有 ADR。
- 基线永不修改。需要新基线时按字节入库到 `spec/` 下新目录，并在本文件登记其 SHA256。
- 同一变更集必须同步：OpenAPI + `operations.json`/`pages.json` + 受影响 `ui` 页说明 + 测试 + fixture 期望。
  本次 v1.0.1 补丁未改 `operations.json`/`pages.json`（月报页面说明在补丁 `ui/MONTHLY-PAGES.md`，
  待 M3-P02/M4-P01 落地时再评估是否需要新增页号登记，届时另开 CR）。
## 工具数据源（D-004 修复后登记，2026-11-12）

`scripts/contract_slice.py` 是全体子智能体上下文包的唯一生成器，其数据源已明确为：

| 用途 | 来源 | 说明 |
|---|---|---|
| `openapi.json`（operationId 切片、schema 展开） | `contracts/openapi.json`（**活契约**） | `spec_version` 从其 `info.version` 动态读取，禁止硬编码 |
| `pages.json`（页号索引） | `contracts/pages.json`（活契约） | 与基线逐字节相同；月报页号若需登记，另开 CR |
| `sqlite-v1.sql`（DDL 切片） | `contracts/sqlite-v1.sql`（活契约） | 与基线逐字节相同，受门禁强制不漂移 |
| `qa/ACCEPTANCE.md`（AC-001..035 原文） | `spec/CampaignLab-SDD-v1.0/`（基线） | 活契约目录无 `qa/`，只能取基线原件 |
| AC-MR-01..12 原文 | `spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/qa/…append.md` | 见 D-005 |
| `ui/*.md`（页面 markdown 原件） | `spec/CampaignLab-SDD-v1.0/`（基线） | `pages.json` 的 `path` 字段相对基线根解析 |

切片输出含 `source` 段（来源路径 + `openapi` 的 bytes 与 sha256 前 16），
下游必须校验该 sha16 与派单当时活契约的实算值一致，不一致即重切（手册 15.4 第 5 条）。
当前活契约指纹：`openapi.json` = `592571099d638251`（443309 B，`info.version` 1.0.1）。
**CR-002 / ADR-006 于 2026-11-13T02:17:03+08:00 移除了 `listWorkspaces` 的 `status` 查询参数**，前一指纹 `01bd28f0772f506e` / 443552 B 已作废；
登记项由 12 → **13** 条。指纹属易变值，**权威现值见 `orchestrator/state.json → resume.self_check_gates_rc0.counts.live_openapi_sha16`**，
文档内一律不得写死（依 D-012/D-014）。
