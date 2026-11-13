# 01 · 13 件前端公共组件契约表 —— 内容级逐条对代码复核

- lane：Q / Verifier-R9A（档位 qwen3.8-flash）
- 复核日期：2026-11-14
- 台账项：`PENDING_CONTENT_REVIEW`（口径出处 `orchestrator/defects/D-034.md:23` 的 path_caliber 声明）
- 契约表来源（只读）：`orchestrator/handoff/M0-03-public-components.md` §2.1-§2.13
- 代码面（只读）：`web/src/components/**`（13 个文件：12 个 `.vue` + `componentTypes.ts`）
- 判定口径：**一致** = 件数 / 路径 / prop 名 / 类型 / 必填性 / 默认值 / emits 名与载荷 / slot 名与作用域参数全部与代码实测相符；任一不符记为**差异**；文件查不到记为 **NOT_FOUND**。
- 「代码实测」全部来自真实读文件（`defineProps` / `defineEmits` / `<slot` / 模板兜底 / `<style>` 类），**未从契约表反推**。
- 组件路径前缀：`web/src/components/`。`H:n` = `orchestrator/handoff/M0-03-public-components.md` 的第 n 行。

## 1. 逐件对照表（13 件）

| # | 组件名 | 契约表声明的文件路径 | 磁盘实测是否存在 | 契约表声明的 props/emits/slots | 代码实测的 props/emits/slots | 是否一致 | 差异明细 | 证据 file:line |
|---|---|---|---|---|---|---|---|---|
| 1 | `AlertBanner.vue` | `web/src/components/AlertBanner.vue`（43 行） | 存在（43 行） | props `error: ApiError null`（必填）、`note: string undefined`（否，undefined 或空串不渲染）；emits 无；slots 无 | `defineProps<{ error: ApiError \| null; note?: string \| undefined }>()`；全文无 `defineEmits`、无 `<slot` | 一致 | 无 | 代码 `AlertBanner.vue:6`、`:9`、`:20`；契约表 `H:40-42`；行数基线 `H:16` |
| 2 | `AppBar.vue` | `web/src/components/AppBar.vue`（27 行） | 存在（27 行） | props `health` / `session` / `recentWorkspace` 均必填；emits `evidence: []`（`:18`）；slots 行未列 | `defineProps<{ health: Health \| null; session: Session \| null; recentWorkspace: string \| null }>()`、`defineEmits<{ evidence: [] }>()`、无 `<slot` | 一致 | 无（§2.2 未写 slots 行，代码亦无 slot，语义不冲突 → P3 表述缺项，不计差异） | 代码 `AppBar.vue:5`、`:6`、`:18`；契约表 `H:55-58` |
| 3 | `AppShell.vue` | `web/src/components/AppShell.vue`（39 行） | 存在（39 行） | props `health?` / `session?` / `recentWorkspace?` 可选，模板内 `?? null`（`:13`）；emits `evidence: []`（`:13`）；slots default（`:14`）、`drawer`（`:16`） | `:6` 三个可选 props、`:7` emits、`:13` `?? null` 与 `@evidence`、`:14` 默认槽、`:16` `name="drawer"` | 一致 | 无。`drawer` / `entryActive` 是 `SideRail` 的 props，`AppShell` 契约未声明（与表一致）；未透传属 D-034 #4 | 代码 `AppShell.vue:6`、`:7`、`:11`、`:13`、`:14`、`:16`；契约表 `H:69-74`；`D-034.md:21` |
| 4 | `CardPanel.vue` | `web/src/components/CardPanel.vue`（24 行） | 存在（24 行） | props `title: string`（必填，兼 `aria-label` `:5`）、`subtitle?: string undefined`（否 `:8`）；slots `actions`（`:9`）/ default（`:11`）/ `footer`（`:12`）；emits 行未列 | `defineProps<{ title: string; subtitle?: string \| undefined }>()`；`:5` aria-label、`:8` v-if、`:9` `name="actions"`、`:11` 默认槽、`:12` `name="footer"`；无 `defineEmits` | 一致 | 无 | 代码 `CardPanel.vue:2`、`:5`、`:8`、`:9`、`:11`、`:12`；契约表 `H:86-90` |
| 5 | `ConfirmDialog.vue` | `web/src/components/ConfirmDialog.vue`（34 行） | 存在（34 行） | props `open`（必填 `:13`）、`summary`（必填 `:14`）、`impact`（必填 `:17`）、`confirmLabel?` 默认「确认提交」（`:20`）、`cancelLabel?` 默认「取消」（`:19`）；emits `confirm`（`:20`）、`cancel`（`:13`、`:19`）；slots 无 | `defineProps` 五 props 逐字吻合（`:3-9`）；`defineEmits<{ confirm: []; cancel: [] }>()`（`:10`）；默认值走模板兜底 `?? "取消"`（`:19`）/ `?? "确认提交"`（`:20`），无 `withDefaults`；无 `<slot` | 一致 | 无 | 代码 `ConfirmDialog.vue:3-9`、`:10`、`:13`、`:14`、`:17`、`:19`、`:20`；契约表 `H:98-104` |
| 6 | `DataTable.vue` | `web/src/components/DataTable.vue`（49 行） | 存在（49 行） | props `columns: readonly TableColumn[]`、`rows: readonly TableRow[]`、`caption: string` 必填（`:20`）；`sortKey?`（无排序 `:13`）、`sortDir?`（非 desc 即 ascending `:14`）；emits `sort: [key: string]` 仅 `sortable === true` 触发（`:24`）；slots 动态 `cell-<col.key>` 作用域 `{ row, value }`，默认 `row[col.key] ?? "—"`（`:34`） | `:3-9` props、`:10` emits、`:12-15` `ariaSort()`、`:20` caption、`:24` 排序按钮、`:34` `<slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">` 兜底 `"—"` | 一致 | 无。**覆盖缺口另记**：契约表 §5 自认「36px 密集档与冻结首列未实现」（`H:288`），与 D-034 #2 一致，属规范覆盖问题而非表-码不符 | 代码 `DataTable.vue:3-9`、`:10`、`:13`、`:14`、`:20`、`:24`、`:34`、`:42`、`:46`；契约表 `H:115-121`、`H:288` |
| 7 | `EmptyState.vue` | `web/src/components/EmptyState.vue`（19 行） | 存在（19 行） | props `title`（必填 `:7`）、`hint?`（`:8`）、`actionLabel?`（不渲染按钮 `:9`）；emits `action`（`:9`）；slots 无 | `defineProps<{ title: string; hint?: string \| undefined; actionLabel?: string \| undefined }>()`、`defineEmits<{ action: [] }>()`；`:7` 标题、`:8` hint v-if、`:9` 按钮 v-if + `@click`；无 `<slot` | 一致 | 无 | 代码 `EmptyState.vue:2`、`:3`、`:7`、`:8`、`:9`；契约表 `H:133-137` |
| 8 | `EvidenceDrawer.vue` | `web/src/components/EvidenceDrawer.vue`（53 行） | 存在（53 行） | props `open`（必填 `:35`）、`title`（必填，兼 `aria-label` `:35`）；emits `close`（`:30`、`:38`）；slots default（`:40`） | `defineProps<{ open: boolean; title: string }>()`、`defineEmits<{ close: [] }>()`；`:27-32` `onKeydown` Escape 分支；`:35` `v-if` + `aria-label` + `tabindex="-1"` + `ref="panel"` + `@keydown`；`:38` 关闭按钮；`:40` 默认槽 | 一致 | 无 | 代码 `EvidenceDrawer.vue:4`、`:5`、`:27-32`、`:35`、`:38`、`:40`；契约表 `H:147-150` |
| 9 | `PageBar.vue` | `web/src/components/PageBar.vue`（16 行） | 存在（16 行） | props `title: string`（必填 `:7`）、`crumb?: string undefined`（`:6`）；slots `meta`（`:8`）；emits 行未列 | `defineProps<{ title: string; crumb?: string \| undefined }>()`；`:6` crumb v-if、`:7` `h1`、`:8` `name="meta"`；无 `defineEmits` | 一致 | 无 | 代码 `PageBar.vue:2`、`:6`、`:7`、`:8`；契约表 `H:159-161` |
| 10 | `PageGrid.vue` | `web/src/components/PageGrid.vue`（18 行） | 存在（18 行） | props `narrowTemplate?: "stack" undefined`（默认 `"stack"`，`:5` 写入 `data-narrow`）；slots default（`:6`、`:11`）、`side`（`:7`、`:12`）；emits 行未列 | `defineProps<{ narrowTemplate?: "stack" \| undefined }>()`；`:5` `:data-narrow="props.narrowTemplate ?? 'stack'"`；`:6` 默认槽、`:7` `name="side"`；`:11-13` span 8 / span 4 / repeat(12)；无 `defineEmits` | 一致 | 无 | 代码 `PageGrid.vue:2`、`:5`、`:6`、`:7`、`:11-13`；契约表 `H:169-171` |
| 11 | `SideRail.vue` | `web/src/components/SideRail.vue`（34 行） | 存在（34 行） | props `drawer?: boolean undefined`（仅 `=== true` 生效 `:7`）、`entryActive?: boolean undefined`（仅 `=== false` 隐藏入口 `:8`）；emits / slots 行未列 | `defineProps<{ drawer?: boolean \| undefined; entryActive?: boolean \| undefined }>()`；`:7` `:class="{ 'is-drawer': props.drawer === true }"`；`:8` `v-if="props.entryActive !== false"`；无 `defineEmits`、无 `<slot` | 一致 | 无 | 代码 `SideRail.vue:4`、`:7`、`:8`、`:11`；契约表 `H:179-180`、`H:263`（导航文案冻结） |
| 12 | `StatusTag.vue` | `web/src/components/StatusTag.vue`（34 行） | 存在（34 行） | props `label: string`（必填，唯一文本载体 `:7`）、`tone?: StatusTone undefined`（默认 `"NEUTRAL"` 见 `:4` 的 `tone()`，映射 `is-<lowercase>` 类 `:7`、`:29-33`）；无 slot、无 emit（`H:191`） | `defineProps<{ label: string; tone?: StatusTone \| undefined }>()`；`:4` `const tone = (): StatusTone => props.tone ?? "NEUTRAL"`；`:7` `:class="'is-' + tone().toLowerCase()"`；`:22-28` `::before` 圆点 `currentColor`；`:29-33` 五条 tone 类；无 `defineEmits`、无 `<slot` | 一致 | 无。颜色单载体风险由契约表自行登记（`H:193`），对应 D-034 #3 | 代码 `StatusTag.vue:3`、`:4`、`:7`、`:22-28`、`:29-33`；契约表 `H:188-189`、`H:191`、`H:193` |
| 13 | `componentTypes.ts` | `web/src/components/componentTypes.ts`（8 行） | 存在（8 行） | 导出 `StatusTone`（`:1` 五值联合）、`TableColumn`（`:2-7`：`key: string`、`label: string`、`sortable?: boolean`、`mono?: boolean`，全 `readonly`）、`TableRow`（`:8` `Record<string, string \| number \| null>`） | `:1` 五值逐字相同；`:2-7` `readonly sortable?: boolean \| undefined`（`:5`）、`readonly mono?: boolean \| undefined`（`:6`）；`:8` 逐字相同 | **差异** | 契约表写 `sortable?: boolean` / `mono?: boolean`，代码实为 `boolean \| undefined`。`web/tsconfig.json:10` 打开 `exactOptionalPropertyTypes: true`，二者**语义不等价**（`?: boolean` 禁止显式传 `undefined`）→ 材料性类型差异。且契约表 §2.1-§2.12 各件均逐字写 `\| undefined`，唯 §2.13 未写，表内口径不统一 | 代码 `componentTypes.ts:5`、`:6`；配置 `web/tsconfig.json:10`；契约表 `H:202`（对照 `H:41`、`H:71`、`H:117`、`H:180`） |

## 2. 件数与规模对账（实测，非引用声明）

| 项 | 契约表声明 | 实测 | 结论 |
|---|---|---|---|
| 件数 | 12 个 `.vue` + 1 个 `componentTypes.ts` = 13 件（`H:32`、`H:106`） | `ls web/src/components \| grep -c .` → `13` | 一致 |
| 合计行数 | 398 行（`H:16` C1） | `wc -l` 逐件 43/27/39/24/34/49/19/53/16/18/34/34/8，合计 398 | 一致（逐件行数声明亦全部吻合） |
| `state/` 子目录 | 声明不存在（`H:20` C5 `STATE_DIR_ABSENT`） | 复跑 → `STATE_DIR_ABSENT`；`ls -d web/src/components/*/ \| wc -l` → `0` | 一致 |
| import 边 | `H:27-33` | `AppShell.vue:2-3` → `AppBar.vue:2` → `StatusTag.vue:2` → `componentTypes.ts:1`；`DataTable.vue:2`；`AlertBanner.vue:2-3` | 一致 |

## 3. 系统性观察（登记，不裁定）

1. **表述缺项（P3，不计差异）**：`§2.2` `§2.4` `§2.9` `§2.10` `§2.11` `§2.12` 的表格只列代码中确实存在的类别，未显式写「emits 无 / slots 无」行；实测这些件确无 `defineEmits` / `<slot`，语义不冲突。补行属 append-only 文档改动，需走 CR。
2. **唯一材料性差异（#13）**不影响现存调用方：`DataTable.vue:2` 只以 `TableColumn[]` 接收；唯一消费点 `web/src/pages/workspace/WorkspacePage.vue:162-166` 未见显式传 `sortable: undefined`。定级 P3（表述材料性 / 无运行期影响），裁定权归编排器。
3. 契约表 §7 自认的 D1-D4（`H:297-300`）与 `D-034.md:18-21` 一一对应，权威 file:line 见 `02-d034-four-defects-locations.md`。

## 4. 结论行

RESULT: 13 件逐条复核完毕 / 一致 12 件 / 差异 1 件 / NOT_FOUND 0 件
