# R10 编排器复验证据索引（r10-verification）

本目录由脚本生成，件数与行数均为**实测值**（`rule_evidence_count_must_be_programmatic`）。

| 文件 | 行数 | 字节 |
|---|---|---|
| `00-index.md` | 本文件（自指，不记行） | - |
| `commands.md` | 47 | 5560 |
| `verify-report.md` | 96 | 8747 |
| `logs/r10_mencius_gates.log` | 101 | 5094 |
| `logs/r10_post_commit.log` | 20 | 676 |
| `logs/r10_pre_commit.log` | 39 | 2370 |

**合计 6 件**（由脚本对目录实测生成；新增文件后必须重跑生成脚本刷新此数）。

## 覆盖范围

- **R10-A**：M0-02/S5 入库前的 `ruff format --check`（本批 5 个 .md）与 `pytest` counts/ledger 守护（预期 RED），以及入库后的守护转绿复验、HEAD 树分母重算（75 py + 122 md = 197）、索引↔磁盘集合相等复验（19 == 19）。
- **R10-B**：Mencius（M0-03b/S2+S3）12 件交付的逐件行数与编码实测、越界自证 A144 三段式、前端四门禁亲自重跑（vitest 173/277、typecheck、lint、build）、11 条定点守卫、A145–A151 的裁定依据、以及编排器自身 BRE 假绿的自我更正（R10-5）。

## 关联

- 提交：R10-A `eaf02dd`（M0-02/S5 + D-038 + A144）；R10-B（本批：M0-03b/S2+S3 + A145–A151 + FU-26/27/28 + R10-4/R10-5）。
- 裁定全文：`orchestrator/state.json` 的 `resume.round7_adjudications`（A145–A151）与 `orchestrator/handoff/M0-03b-freeze.md` §9。
- 缺陷：D-038（`orchestrator/defects/D-038.md`）。
