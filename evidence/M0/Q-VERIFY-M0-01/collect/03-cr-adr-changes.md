# A3 · CR-001 / ADR-004 / contracts/CHANGES.json 三方一致性

三份材料均为小文件全文读取；活契约指针存在性用 python3 定点提取（未整读 openapi.json）。
原始探针输出：`raw/a3-cr-adr.log`。

## 1. 三方各自声明的月报节点

- **CR-001.md「影响面（12 个节点）」表**：12 行——
  openapi.json ×10（`/info/version` changed + `/components/schemas/` 下 MonthlyCapacity、MonthlyComparison、
  MonthlyOriginOverlap、MonthlyParticipation、MonthlyProduction、MonthlyReview、MonthlyTrend 7 个 added +
  `/components/schemas/Review/properties/monthly_review` added + `/components/schemas/ReviewCreate/properties/profile` added）、
  source-json.schema.json `/$defs/SourceMetadata/properties/monthly_review` added、
  source-metadata.schema.json `/properties/monthly_review` added。工具状态：1×UPDATE + 11×ADD（其中 4 处标「（可选）」）。
- **contracts/CHANGES.json**：`entries` 共 **12** 条，file+pointer 组合与上表逐一对应；
  kind：1×`changed`（/info/version，delta_tool_state=UPDATE）+ 11×`added`（全 UPDATE→ADD）；每条均带 `cr=CR-001`、`adr=ADR-004`。
- **ADR-004.md**：不逐条列节点；声明「全部差异登记 CHANGES.json」「验收 35→47（AC-MR-01..12 共 12 条）」
  「活契约 info.version = 1.0.1」「只读预检 11 ADD + 1 UPDATE（CR-001 第 3 节，引 ADR 机制）」。

## 2. 交集 / 差集（CR-001 表 ⇄ CHANGES.json entries）

- 交集：**12/12 完全一致**（文件名+JSON Pointer+变更类型三要素逐条对齐）。
- 差集：**空**（CR 无孤儿行，CHANGES 无未声明条目）。
- 与 ADR-004 的间接声明：11 ADD + 1 UPDATE、版本 1.0.1、12 条 AC-MR——与 CR/CHANGES 一致，无冲突。

## 3. 对磁盘事实的独立验证（不采信三方自述）

- 12 个 pointer 在 `contracts/` 全部 **EXISTS**（raw 日志 12 行 POINTER 输出）。
- `contracts/openapi.json` `info/version = 1.0.1`；`CHANGES.json.baseline.openapi_info_version_at_baseline=1.0.0`，
  `live.openapi_info_version=1.0.1`，与 CR-001「UPDATE 1.0.0 → 1.0.1」及条件更新描述一致。
- CR-001 兼容性声明实测：`ReviewCreate.required=['scope']`（不含 profile）；`Review.required` 长度 **17** 且不含
  `monthly_review`；source-json `/$defs/SourceMetadata.required` 长度 **9** 不含 monthly_review；
  source-metadata `required` 长度 **9** 不含 monthly_review——与 CR-001 「17 项 / 9 项」表述逐项吻合。
- CR-001「覆盖活契约 3 个文件；其余 8 个与基线逐字节相同」实测：baseline contracts 共 **11** 个文件；
  `cmp` 全仓比对 SAME=8、DIFFERS=3（恰为被改 3 个文件）——成立。

## 4. 措辞/口径不一致清单（仅细节，无实质节点分歧）

1. CHANGES.json 的 12 条 `delta_tool_state` 全为 `ADD`/`UPDATE`，**未保留** CR-001 表中 4 处「（可选）」标注
   （即"未进 required"的语义只写在 CR-001，CHANGES.json 无对应字段）。属登记粒度差异，非节点差异。
2. CR-001 兼容性段写「三个新增属性均未进入任何 required」，而其影响面表与 CHANGES.json 的新增**属性**类节点实为
   4 个 pointer（profile、Review.monthly_review、两份 SourceMetadata 的 monthly_review 分属 2 个文件）。
   按「属性名」口径是 3 个（monthly_review 算一个），按「文件×pointer」口径是 4 个——CR 未写明口径，列备案。
3. ADR-004 未复述 12 节点清单本身（引用机制而非枚举），无法做逐字比对，但所有可交叉数字（11+1、47-35=12、1.0.1）与三方一致。
4. CHANGES.json.note 声明由 `check_contracts.py check` 强制一一对应——A2 实测该门禁 rc=0 且 12==12，闭环成立。

## 5. 材料齐备性
三份文本均存在可读；指针级、字节级磁盘验证全部可复跑（命令见 raw）。无缺失。