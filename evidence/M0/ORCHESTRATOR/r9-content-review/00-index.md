# 00-index · R9 内容级复核（Q lane / Verifier-R9A，qwen3.8-flash）

- 范围：`M0-03-public-components.md`（13 件契约表）+ `M0-03b-freeze.md`（六态冻结）+ `D-034.md`（4 项缺陷）× `web/src/components/**` 逐条对码；即台账 `PENDING_CONTENT_REVIEW` 的取证产物。

| 文件 | 一句话结论 |
|---|---|
| `01-component-contract-table-review.md` | RESULT: 13 件逐条复核完毕 / 一致 12 件 / 差异 1 件 / NOT_FOUND 0 件。唯一差异 = 契约表 §2.13 把 `TableColumn` 的 `sortable?` / `mono?` 写成 `?: boolean`，代码实为 `?: boolean \| undefined`（`componentTypes.ts:5-6`），在 `web/tsconfig.json:10` `exactOptionalPropertyTypes: true` 下语义不等价；件数 13、合计 398 行、逐件行数、路径、import 边全部实测吻合。 |
| `02-d034-four-defects-locations.md` | 四项全 CONFIRMED 并定出权威 file:line：#1 `ConfirmDialog.vue:13`/`:14`（有 `tabindex="-1"`、无 `ref`、focus 族 0 命中；正例 `EvidenceDrawer.vue:10-25`）；#2 `DataTable.vue:46` 单一行高档 + `tokens.css:78`/`:92` 密集令牌零引用 + 全仓 0 处 sticky；#3 `StatusTag.vue:7` + `:29-33` 五 tone 仅改 color/border-color、`:22-28` 圆点 `currentColor`；#4 `AppShell.vue:6` props 无 `drawer`/`entryActive`、`:11` 裸 `<SideRail />`，而 `SideRail.vue:4` 已声明二者。#1/#3 关联 **AC-032**，须在 M5-01 取证前修毕（`D-034.md:7`、`:32`）。 |
| `03-freeze-doc-review.md` | 六态件代码为 0：`web/src/components/state/**` 实测 `STATE_DIR_ABSENT`、子目录 0、`ViewState` 全域 0 命中，与 `M0-03b-freeze.md:115`/`:117`/`:331` 自身声明一致 ⇒ 6 条对应全 NOT_FOUND（非违约）；文档内部六态自洽，所引二手行号已逐条独立复验为真。「公共件无取数副作用」口径 **PASS**：网络调用族 0 命中、`@/api` 仅 4 处 `import type`、触发值全由页面 props 传入（`WorkspacePage.vue:137`/`:162`/`:205`/`:215`）。 |
| `commands.md` | 24 条命令四元组台账（cwd / 命令 / rc / 关键输出）+ 5 次踩坑与自纠实录；rc 一律 `subprocess.run(...).returncode`，未用 shell 问号变量。 |

## 总判定：**PASS_WITH_DIFF**

- PASS 面：13 件的 props / emits / slots / 必填性 / 默认值 / 路径 / 件数 / 行数全部对码吻合；D-034 四项均可定址（NOT_REPRODUCIBLE 0）；无取数副作用口径成立。
- 不给 PASS 的两点：① §2.13 的材料性类型表述差异（建议 append-only 修表，走 CR）；② 六态件「文档已冻结、代码零落地」——本 lane 判为与文档一致的 NOT_FOUND，是否催派 S3 归编排器。
- 本 lane 未做任何裁定，未改 `spec/**`、`contracts/**`、`orchestrator/state.json`，未新建 `state/**`，仅在本目录新建 5 份文件。

## 越界自证（仓库根双检，实测均为 0）

- `git diff --name-only HEAD | grep -vE '^evidence/M0/ORCHESTRATOR/r9-content-review/' | wc -l` → **0**（证明未修改任何既有文件）
- `git status --porcelain | grep -vE '^(\?\? )?evidence/M0/ORCHESTRATOR/r9-content-review/' | wc -l` → **0**（`git status --porcelain` 条目全部为本目录；无非本 lane 在飞改动；另用 `git status --porcelain | grep -vE '^([?][?] )?evidence/M0/ORCHESTRATOR/r9-content-review/' | wc -l` 与 `git status --porcelain --untracked-files=all | grep -v '^?? evidence/M0/ORCHESTRATOR/r9-content-review/' | wc -l` 两种变体互证亦为 0）
