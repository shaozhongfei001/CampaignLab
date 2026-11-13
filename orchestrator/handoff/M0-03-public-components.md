# M0-03 公共组件清单与冻结边界（S10 产出）

- 产出子任务：M0-03 / S10（档位表见 `orchestrator/tasks/M0-03.md:41`：`qwen3.8-max` / 16k / 产出本文件）
- 产出日期：2026-11-13（Asia/Shanghai）
- 实测基线：分支 `m0-framework`，`git rev-parse --short HEAD` = `34e4709`；`git status --porcelain web/src | wc -l` = `0`
- 本文件性质：**只读裁定**。S10 未改动 `web/**` 任何一行；文中所有「缺口 / 偏差」只登记归属，不在本文件内修复
- 令牌口径：本文**不出现任何六位十六进制色值**；色值唯一真值为 `docs/design/token-mapping.md` → `web/src/styles/tokens.css`，组件内只允许 `var(--cl-*)`
- 读者：M0-03b（S1 冻结面裁定、S2-S4 实现）与 wave3 起的所有页面任务

## 1. 实测方法与抽取命令原文

清单与契约**全部由下列命令的输出抽取**，无一条凭印象编写。工作目录 `/home/szf/dev/CampaignLab`。

| # | 命令原文 | 命中 | 用途 |
|---|---|---|---|
| C1 | `wc -l web/src/components/*.vue web/src/components/componentTypes.ts` | 13 文件 / 398 行合计 | 件数与规模基线 |
| C2 | `grep -n 'defineProps\|defineEmits\|withDefaults\|defineSlots\|defineModel\|defineExpose\|import ' web/src/components/*.vue` | 30 命中行 | props / emits / 依赖边 |
| C3 | `grep -n '<slot' web/src/components/*.vue` | 10 命中行，分布于 6 个文件 | slots 清单（其余 6 件无 slot） |
| C4 | `nl -ba web/src/components/componentTypes.ts` | 8 行全文 | 共享类型真值 |
| C5 | `test -e web/src/components/state && echo STATE_DIR_EXISTS \|\| echo STATE_DIR_ABSENT` | 输出 `STATE_DIR_ABSENT` | 证明 `state/` 目录当前不存在 |
| C6 | `head -n 20 web/src/components/{AppShell,AppBar,SideRail,PageBar,PageGrid,CardPanel,StatusTag}.vue` | 逐件 script + 模板首段 | 默认值兜底位置、aria 属性 |
| C7 | `nl -ba web/src/components/AlertBanner.vue`、`nl -ba web/src/components/EmptyState.vue`、`nl -ba web/src/components/ConfirmDialog.vue`、`nl -ba web/src/components/DataTable.vue` | 全文 | 六态收敛对象的现有签名 |
| C8 | `sed -n 26,53p web/src/components/EvidenceDrawer.vue`、`sed -n 18,39p web/src/components/AppShell.vue`、`sed -n 20,34p web/src/components/StatusTag.vue` | 全文余段 | Esc / 焦点回收 / 全局焦点线 / tone 类 |
| C9 | `python3 /mnt/d/ws/codex_rd/ss_campaignlab/.orch_tmp/laneF_freeze/probe.py` | 页面消费点 22 处 | 消费方指引的行号真值 |

关键实测事实（影响冻结契约的写法）：

1. **`withDefaults` 0 命中**（C2）。所有可选 props 都用 `?: T | undefined` 声明，默认值**不在 props 层**，而在模板层用 `??` 或 `v-if` 兜底（例：`AppShell.vue:13` 的 `props.health ?? null`、`DataTable.vue:34` 的 `row[col.key] ?? "—"`、`ConfirmDialog.vue:19-20` 的 `props.cancelLabel ?? "取消"`）。因此下表的「默认」列一律写**模板兜底值**，冻结的是「不传时的可观察行为」而不是 props 默认值。
2. **`defineSlots` / `defineModel` / `defineExpose` 全部 0 命中**（C2）。slots 只有 C3 的模板级声明，**无类型化 slot props 契约**；唯一带作用域参数的 slot 是 `DataTable.vue:34` 的 `cell-<key>`（`{ row, value }`）。
3. `web/src/components/` 下**没有任何子目录**（C1 只列出 13 个文件），`state/` 尚不存在（C5）。

## 2. 逐件清单（13 件）

### 2.1 `AlertBanner.vue`（43 行）

职责：把一个 `ApiError` 呈现为可读的失败条；服务端 Problem 的 `title` / `detail` / `request_id` 原样可见（ADR-005 §2.2，件内注释 `:4`）。

| 类别 | 名称 | 类型 | 必填 | 默认（模板兜底） | 约束与实测行 |
|---|---|---|---|---|---|
| props | `error` | `ApiError \| null` | 是 | — | `null` 时整段 `v-if` 不渲染（`:9`） |
| props | `note` | `string \| undefined` | 否 | 不渲染 | `undefined` 或空串都不渲染（`:20`） |
| slots | — | — | — | — | 无（C3 未命中） |
| emits | — | — | — | — | 无（C2 未命中 `defineEmits`） |

- 呈现要素：`role="alert"`（`:9`）、`data-bucket`＝`presentationOf(error).bucket ?? "default"`（`:9`）、标题在 `kind === "problem"` 时原样渲染服务端 `title`、否则固定「请求未完成」（`:10`）、`code` 与 HTTP 状态仅在 problem 时显示（`:12-14`）、`issues` 逐条 `location — message` 并带 `data-severity`（`:15-19`）、`request_id` 恒显示且等宽（`:21`、`:39`）。
- 依赖：`@/api/http`（`ApiError`，`:2`）、`@/features/shared/problemPresentation`（`presentationOf`，`:3`）。**组件内不抄 code 白名单**（Q4 / RULING_NO_FRONTEND_MIRROR，见 `problemPresentation.ts:3`）。
- 色值：只用 `var(--cl-danger-600)`、`var(--cl-brand-50)`、`var(--cl-danger-text)`、`var(--cl-warn-text)`、`var(--cl-ink-*)`（`:26-42`），无字面量。

### 2.2 `AppBar.vue`（27 行）

职责：顶栏，呈现 worker 健康、契约版本、操作者与最近工作区，并提供证据入口按钮。

| 类别 | 名称 | 类型 | 必填 | 默认 | 约束与实测行 |
|---|---|---|---|---|---|
| props | `health` | `Health \| null` | 是 | — | `null` → 标签「状态未知」/ tone `NEUTRAL`，版本串显示 `—`（`:11`、`:13`） |
| props | `session` | `Session \| null` | 是 | — | `session?.actor_name ?? "未登录"`（`:16`） |
| props | `recentWorkspace` | `string \| null` | 是 | — | `?? "—"`（`:17`） |
| emits | `evidence` | `[]` | — | — | 证据按钮 `@click`（`:18`） |

- 附加规则：`health.worker === "OFFLINE"` 时追加一枚「作业受限」`DANGER` 标签（`:12`）。
- 依赖：`./StatusTag.vue`（`:2`）、`@/api/endpoints` 的 `Health` / `Session`（`:3-4`；二者是 `components["schemas"]` 别名，见 `endpoints.ts:14`、`:16`）。

### 2.3 `AppShell.vue`（39 行）

职责：全站壳（左导航 + 顶栏 + 主区 + 抽屉位），并承载**全站 2px 焦点可见线**。

| 类别 | 名称 | 类型 | 必填 | 默认 | 约束与实测行 |
|---|---|---|---|---|---|
| props | `health` | `Health \| undefined` | 否 | 模板内 `?? null`（`:13`） | 透传给 `AppBar` |
| props | `session` | `Session \| undefined` | 否 | 同上 | 透传给 `AppBar` |
| props | `recentWorkspace` | `string \| null \| undefined` | 否 | 同上 | 透传给 `AppBar` |
| emits | `evidence` | `[]` | — | — | 由 `AppBar` 冒泡（`:13`） |
| slots | default | — | — | — | 主区 `<main class="cl-shell__main">`（`:14`） |
| slots | `drawer` | — | — | — | 抽屉挂载位（`:16`） |

- 全局（非 scoped）样式块 `:19-25` 定义 `:where(a, button, input, select, textarea, [tabindex]):focus-visible { outline: 2px solid var(--cl-brand-600) }`；这是**唯一**允许非 scoped 的公共件样式，改动即影响全站，必须走 CR。
- 断点：`--cl-rail-w` → 1100px 折叠为 `--cl-rail-w-collapsed`（`:31-34`）→ 800px 单列（`:36-38`）。
- **实测边界（登记不修）**：`:11` 是 `<SideRail />` 无参调用，`SideRail` 的 `drawer` / `entryActive` 在壳内永远取默认值；壳未按断点把 `drawer` 传下去。归属：M0-03 lane（页面壳行为）或走 CR，不属 M0-03b。

### 2.4 `CardPanel.vue`（24 行）

职责：卡片容器（标题 + 副标题 + 动作区 + 主体 + 页脚）。

| 类别 | 名称 | 类型 | 必填 | 默认 | 约束与实测行 |
|---|---|---|---|---|---|
| props | `title` | `string` | 是 | — | 同时作为 `:aria-label`（`:5`） |
| props | `subtitle` | `string \| undefined` | 否 | 不渲染 | `undefined` 或空串不渲染（`:8`） |
| slots | `actions` | — | — | — | 头部右侧（`:9`） |
| slots | default | — | — | — | 卡片主体（`:11`） |
| slots | `footer` | — | — | — | 卡片页脚（`:12`） |

### 2.5 `ConfirmDialog.vue`（34 行）

职责：确认对话框最小实现（520px，摘要 + 影响 + 取消 + 主按钮）。件内注释 `:2` 记 Q3 裁定：**M2-04 复用同一实现，禁止二次实现**。

| 类别 | 名称 | 类型 | 必填 | 默认 | 约束与实测行 |
|---|---|---|---|---|---|
| props | `open` | `boolean` | 是 | — | `v-if`（`:13`） |
| props | `summary` | `string` | 是 | — | 同时作为 `:aria-label`（`:14`） |
| props | `impact` | `string` | 是 | — | 影响说明（`:17`） |
| props | `confirmLabel` | `string \| undefined` | 否 | `"确认提交"`（`:20`） | — |
| props | `cancelLabel` | `string \| undefined` | 否 | `"取消"`（`:19`） | — |
| emits | `confirm` | `[]` | — | — | 主按钮（`:20`） |
| emits | `cancel` | `[]` | — | — | 取消按钮与 `@keydown.esc`（`:13`、`:19`） |

- 宽度走 `var(--cl-dialog-w)`（`:27`），`role="dialog"` + `aria-modal="true"` + `tabindex="-1"`（`:14`）。
- **实测边界（登记不修）**：`@keydown.esc` 挂在 mask（`:13`）上，而 mask 无 `tabindex`；对话框虽 `tabindex="-1"` 却**没有打开时主动 `focus()` 的逻辑**（对比 `EvidenceDrawer.vue:10-25` 有 `onBeforeUpdate` / `onUpdated` 焦点回收）。因此 Esc 只在焦点已位于对话框内时生效。归属：M0-03 键盘基线（S7）/ 走 CR；M0-03b **不得**顺手改（越界自证 gate 会判红）。

### 2.6 `DataTable.vue`（49 行）

职责：等宽数字表格，支持键盘可触发的列排序与作用域单元格插槽。

| 类别 | 名称 | 类型 | 必填 | 默认 | 约束与实测行 |
|---|---|---|---|---|---|
| props | `columns` | `readonly TableColumn[]` | 是 | — | `TableColumn` 见 `componentTypes.ts:2-7` |
| props | `rows` | `readonly TableRow[]` | 是 | — | `TableRow` 见 `componentTypes.ts:8` |
| props | `sortKey` | `string \| undefined` | 否 | 视为无排序（`:13`） | — |
| props | `sortDir` | `string \| undefined` | 否 | 非 `"desc"` 即 `ascending`（`:14`） | 取值事实上只有 `"asc"` / `"desc"`，但**类型是 `string`**（未收窄） |
| props | `caption` | `string` | 是 | — | `<caption>`（`:20`），读屏可达 |
| emits | `sort` | `[key: string]` | — | — | 仅 `col.sortable === true` 的表头按钮触发（`:24`） |
| slots | `cell-<col.key>` | 作用域 `{ row, value }` | 否 | `row[col.key] ?? "—"`（`:34`） | **动态 slot 名**，每列一个 |

- `aria-sort` 三值由 `ariaSort()` 计算（`:12-15`），非排序列恒 `none`。
- 等宽数字：`col.mono === true` → `is-mono` → `font-variant-numeric: tabular-nums`（`:33`、`:47`）；行高 `var(--cl-row-h)`（`:46`）。
- **未覆盖项（登记不修）**：`page-component-map.md` 第 1 节要求 `DataTable` 具备「行高 40/36、游标 25 行、宽表冻结首列」。实测：36px 密集档未实现（只有 `--cl-row-h` 一档）、游标 25 行由页面承担（`WorkspacePage.vue:168-169`）、**冻结首列未实现**（`.cl-table-scroll` 只有 `overflow-x: auto`，`:42`）。归属：密集档与冻结首列首次真正需要者是 M2-04（宽表 `DiffTable` 页），扩公共件须走 CR。

### 2.7 `EmptyState.vue`（19 行）

职责：空态占位（标题 + 提示 + 一个可选动作按钮）。

| 类别 | 名称 | 类型 | 必填 | 默认 | 约束与实测行 |
|---|---|---|---|---|---|
| props | `title` | `string` | 是 | — | `:7` |
| props | `hint` | `string \| undefined` | 否 | 不渲染 | `undefined` 或空串不渲染（`:8`） |
| props | `actionLabel` | `string \| undefined` | 否 | 不渲染按钮 | `undefined` 或空串不渲染（`:9`） |
| emits | `action` | `[]` | — | — | 动作按钮 `@click`（`:9`） |
| slots | — | — | — | — | 无 |

- **实测缺口（正是 M0-03b 的收敛对象）**：本件**没有任何状态语义**——无 `data-state`、无 `role`、无 `aria-live`，只有「空」一种含义。`page-component-map.md` 第 1 节要求 `AlertBanner` `EmptyState` 承载「首载 / 空 / 失败 / 部分可比 / 待补 / 412 过期」六态；当前两件合计只能表达「失败」（AlertBanner）与「无记录」（EmptyState）两态。收敛方案见 `orchestrator/handoff/M0-03b-freeze.md`。

### 2.8 `EvidenceDrawer.vue`（53 行）

职责：证据抽屉（桌面 480px、窄屏全宽），Esc 关闭并把焦点归还触发元素。

| 类别 | 名称 | 类型 | 必填 | 默认 | 约束与实测行 |
|---|---|---|---|---|---|
| props | `open` | `boolean` | 是 | — | `v-if`（`:35`） |
| props | `title` | `string` | 是 | — | 同时作为 `:aria-label`（`:35`） |
| emits | `close` | `[]` | — | — | 关闭按钮与 Esc（`:30`、`:38`） |
| slots | default | — | — | — | 抽屉主体（`:40`） |

- 焦点回收是**公共件行为契约**：`onBeforeUpdate` 在打开前记录 `document.activeElement`（`:21-25`），`onUpdated` 打开时聚焦面板、关闭时归还触发焦点并清空（`:10-20`）。Esc 走 `onKeydown`（`:27-32`）并 `stopPropagation()`。
- 宽度 `var(--cl-drawer-w)`，`@media (max-width: 800px)` 全宽（`:44`、`:50-52`）。

### 2.9 `PageBar.vue`（16 行）

| 类别 | 名称 | 类型 | 必填 | 默认 | 约束与实测行 |
|---|---|---|---|---|---|
| props | `title` | `string` | 是 | — | `<h1>`（`:7`） |
| props | `crumb` | `string \| undefined` | 否 | 不渲染 | `undefined` 或空串不渲染（`:6`） |
| slots | `meta` | — | — | — | 标题右侧元信息 / 动作区（`:8`） |

职责：页头（面包屑 + `h1` + 元信息位）。每页**唯一** `h1` 由此件产生，页面不得再自行写 `h1`。

### 2.10 `PageGrid.vue`（18 行）

| 类别 | 名称 | 类型 | 必填 | 默认 | 约束与实测行 |
|---|---|---|---|---|---|
| props | `narrowTemplate` | `"stack" \| undefined` | 否 | `"stack"`（`:5` 写入 `data-narrow`） | 字面量联合**只有一个取值**，为将来扩展预留 |
| slots | default | — | — | — | 主区，12 栅格占 8（`:6`、`:11`） |
| slots | `side` | — | — | — | 侧区，占 4（`:7`、`:12`） |

职责：8+4 十二栅格页面骨架；`@media (max-width: 800px)` 两区各占 12（`:15-17`）。

### 2.11 `SideRail.vue`（34 行）

| 类别 | 名称 | 类型 | 必填 | 默认 | 约束与实测行 |
|---|---|---|---|---|---|
| props | `drawer` | `boolean \| undefined` | 否 | 不加 `is-drawer` 类（`:7`） | 仅 `=== true` 生效 |
| props | `entryActive` | `boolean \| undefined` | 否 | 渲染入口链接（`:8`） | 仅 `=== false` 时隐藏 |

职责：一级导航（入口 + `COMMON.md:19` 的六项分组）。**无 slot、无 emit**。未交付页面以 `aria-disabled="true"` + `@click.prevent` 呈现，不发假路由（件内注释 `:2-3`）。改动导航项文案即改 `COMMON.md:19` 的落地，须走 CR。

### 2.12 `StatusTag.vue`（34 行）

| 类别 | 名称 | 类型 | 必填 | 默认 | 约束与实测行 |
|---|---|---|---|---|---|
| props | `label` | `string` | 是 | — | 唯一文本载体（`:7`） |
| props | `tone` | `StatusTone \| undefined` | 否 | `"NEUTRAL"`（`:4` 的 `tone()`） | 映射为 `is-<lowercase>` 类（`:7`、`:29-33`） |

职责：收敛模板 `.tag` 与 `.st` 双体系的单一状态标签。**无 slot、无 emit**。

- **「不靠颜色区分」的风险点（登记不修）**：五个 tone 只靠颜色 + `.cl-tag::before` 的 `currentColor` 圆点区分（`:22-33`），**形状完全相同**。因此非颜色载体只有 `label` 文本；`label` 是必填 props 这一点构成事实上的冻结约束：**调用方不得传空串或只传 tone**。M0-03b 的六态件因此不得用 `StatusTag` 的 tone 作为唯一区分手段（见 `M0-03b-freeze.md` §1）。

### 2.13 `componentTypes.ts`（8 行）

职责：公共件共享类型的唯一落点。

| 导出 | 定义行 | 内容 |
|---|---|---|
| `StatusTone` | `:1` | `"NEUTRAL" \| "OK" \| "WARN" \| "DANGER" \| "INFO"` |
| `TableColumn` | `:2-7` | `key: string`、`label: string`、`sortable?: boolean \| undefined`、`mono?: boolean \| undefined`（全 `readonly`；**D-037 更正**：原写作 `sortable?: boolean`／`mono?: boolean`，与代码 `componentTypes.ts:5-6` 及本表 §2.1 前置约定「所有可选 props 都用 `?: T \| undefined` 声明」均不符，在 `web/tsconfig.json:10` `exactOptionalPropertyTypes: true` 下语义不等价） |
| `TableRow` | `:8` | `Record<string, string \| number \| null>` |

约束：新增字面量（例如给 `StatusTone` 加值）＝改公共冻结件签名，**必须走 CR**（手册 §3.1 / §7）。

## 3. 依赖关系

### 3.1 组件间 import 边（C2 实测）

```text
AppShell.vue ──▶ AppBar.vue ──▶ StatusTag.vue ──▶ componentTypes.ts (StatusTone)
     └────────▶ SideRail.vue
DataTable.vue ─────────────────────────────────▶ componentTypes.ts (TableColumn, TableRow)
AlertBanner.vue ──▶ @/api/http (ApiError)
                └─▶ @/features/shared/problemPresentation (presentationOf)
AppBar.vue / AppShell.vue ──▶ @/api/endpoints (Health, Session)
其余 5 件（CardPanel / ConfirmDialog / EmptyState / EvidenceDrawer / PageBar / PageGrid）无内部 import
```

- 唯一的多级链是 `AppShell → AppBar → StatusTag`；`SideRail` 与 `StatusTag` 是叶子。
- `problemPresentation.ts` 是 **ApiError → 呈现分类**的唯一落点（`PROBLEM_CODE_BUCKETS` 20 个 code，`:14-35`；`presentationOf` 返回 `{ bucket, showServerTitle, sameAsNotFound, keepInput, backoff }`，`:47-65`）。它位于 `web/src/features/shared/`，**不在 M0-03b 的 scope_allow 内**，只能被读、不能被改。

### 3.2 与 `web/src/api/types.ts`（生成物）的关系

- `types.ts` 是 openapi-typescript 从活契约生成的产物（`endpoints.ts:19` `import type { components } from "@/api/types"`）。
- **没有任何组件直接 import `types.ts`**：组件只经 `@/api/endpoints`（`Health` / `Session` / `Workspace`）与 `@/api/http`（`ApiError` / `Issue` / `Problem`）间接消费；`http.ts:21-22` 把 `Problem` / `Issue` 别名到 `components["schemas"]`。
- 结论：契约漂移只会在 `types.ts` → `endpoints.ts` → 组件 props 类型这条链上表现为 `vue-tsc` 报错，**不会**表现为组件运行期分支变化。M0-03b 的「类型客户端未漂移」gate（`git diff --name-only -- web/src/api/types.ts | wc -l` → 0）因此是本清单冻结有效性的前置条件。

### 3.3 与 `styles/tokens.css` 的关系

- 令牌定义只在 `web/src/styles/tokens.css`（108 行）；`--el-*` 只在 `element-theme.css`；项目级覆盖只在 `project.css`（三文件的互斥规则见 `main.ts:5-9` 与 `project.css:3`、`element-theme.css:7`）。
- 装载顺序由组合根 `web/src/main.ts:13-16` 固定：`element-plus/dist/index.css` → `tokens.css` → `element-theme.css` → `project.css`，**错序即覆盖失效**。
- 13 件公共组件全部只写 `var(--cl-*)`，实测无六位十六进制字面量；该性质由 `web/tests/unit/tokens-guard.spec.ts`（268 行）持续守卫，是 M0-03 的出口条件（`web/vitest.config.ts:22` 注释）。
- `AppShell.vue:19-25` 的非 scoped 焦点线是**唯一**跨组件样式副作用，它依赖 `--cl-brand-600`。

## 4. 冻结边界

### 4.1 公共冻结件（改动必须走 CR，手册 §3.1 / §7）

| 冻结对象 | 冻结的具体内容 |
|---|---|
| 12 个 `.vue` 的**对外契约** | props 名称 / 类型 / 必填性、emits 事件名与载荷、slot 名与作用域参数 |
| `componentTypes.ts` | `StatusTone` 字面量集合、`TableColumn` / `TableRow` 形状 |
| 语义常量 | `ConfirmDialog` 520px（`--cl-dialog-w`）、`EvidenceDrawer` 480px（`--cl-drawer-w`）、焦点回收行为、`AppShell` 2px 焦点线、断点 1100 / 800 |
| 令牌引用方式 | 组件内只允许 `var(--cl-*)`；新增或改名令牌走 CR |
| `SideRail` 导航六项文案 | 落地 `COMMON.md:19`，改文案＝改规范落地 |

### 4.2 页面私有 / 可改（不需 CR）

- `web/src/pages/**`、`web/src/features/**`、`web/src/composables/**` 内的调用方代码：传什么 props、用哪些 slot、把 emit 接到哪个 handler。
- 页面自己的表格列定义、排序状态、筛选与游标逻辑（例：`WorkspacePage.vue:162` 传 `COLUMNS` / `rows` / `sort`，`:168-169` 承担 25 行游标语义）。
- 页面内联的桩数据与断言（M0-03b 的六态桩数据只允许内联在 `web/tests/unit/state/`，禁改 `spec/**` / `contracts/**` 样本）。

### 4.3 `web/src/components/state/**`：当前不存在，是 M0-03b 的落点

- 实测 `STATE_DIR_ABSENT`（C5）；`web/src/components/` 下当前**只有 13 个文件、0 个子目录**。
- M0-03b 的越界自证 gate 是 `git diff --name-only HEAD -- web/src | grep -v '^web/src/components/state/' | wc -l` → 0，也就是说 **M0-03b 在 `web/src` 内只被允许写 `state/` 一个目录**；`AlertBanner.vue` 与 `EmptyState.vue` 本体在 M0-03b 期间**不可改**。
- 因此六态收敛只能以「**组合而非改写**」落地：新建 `state/` 下的调度件去复用既有两件的现有签名。目标文件清单、冻结签名与外部注册扩展点方案由 S1 裁定，见 `orchestrator/handoff/M0-03b-freeze.md` §2 / §3 / §4；实现落点是 M0-03b 的 S3。
- 门禁提示（交编排器）：`git diff HEAD` **不含未跟踪文件**，故上述 gate 对「新增越界文件」不敏感；建议以 `git status --porcelain web/src` 交叉核对（本文件基线值 = 0）。

## 5. 消费方指引（wave3 起）

1. **只可消费、不得改动**：页面任务需要新能力时，优先用现有 props / slot / emit 组合；确实需要改公共件签名，提 CR 由 T lane 串行合并，不得在页面任务里就地改 `web/src/components/**`。
2. **最小复用示例（只引路径与行号，不复制代码）**：
   - 壳与页头：`web/src/pages/workspace/WorkspacePage.vue:137`（`AppShell` 三 props 全可选，用 `?? undefined` 归一）、`:138-144`（`PageBar` + `meta` slot 放两枚 `StatusTag`）。
   - 8+4 布局与卡片：`:148`（`PageGrid`）、`:149`（`CardPanel` 的 `title` / `subtitle`）、`:167-170`（`footer` slot 放游标「加载更多」）。
   - 失败态：`:146`（`AlertBanner` 传 store 的 `error`，并用 `note` 承载 worker 离线提示）、`:196`（第二处独立错误位，创建表单自己的 `createError`）。
   - 空态：`:155-161`（`EmptyState` 由 `workspaces.state.phase === "empty"` 触发，`action-label` + `@action` 把用户送到创建表单）。
   - 表格与作用域插槽：`:162-166`（`DataTable` + `#cell-action` 覆盖动作列，其余列走 `?? "—"` 默认渲染）。
   - 抽屉与确认：`:205-212`（`EvidenceDrawer` 的 `open` / `title` / `@close`）、`:215` 起（`ConfirmDialog`，属性跨行）。
   - 404 页最小用法：`web/src/pages/shared/NotFoundPage.vue:3`（只 import `CardPanel`）、`:8-13`。
3. **状态来源约定**：store 的 `phase` 是页面私有词汇（`WorkspacesPhase = "idle" | "loading" | "ready" | "empty" | "failed"`，`useWorkspaces.ts:32`；`SessionPhase` 六值，`useSession.ts:26`）。M0-03b 冻结的六态是**呈现层词汇**，二者不是一对一：映射规则由 `M0-03b-freeze.md` §1 的触发条件列固定，页面不得各自发明第三种词汇。
4. **禁止事项**（沿用 M0-03 / M0-03b 卡）：不 `npm install`、不改 `web/*.config.*` 与 `package*.json`、不在组件内写死色值、不 import `spec/frontend-template-spdb-v1.1/**` 的模板 CSS/JS（只读视觉参照）。
5. **工作区列表口径**：`listWorkspaces` 现契约只有 `cursor` / `limit` / `q` 三个查询参数（CR-002 已按 ADR-006 移除 `status`）。任何页面或桩数据**不得出现「按 status 过滤工作区」**；注意别把它与 `Health.status`（`READY` / `DEGRADED`，`endpoints.ts:59-63`）混淆。

## 6. 与 26 页的覆盖对账

依据 `docs/design/page-component-map.md` 第 1 节「公共组件交付顺序」中标注**首次交付 M0-03** 的 6 行：

| §1 行（组件） | 覆盖页面 | 实测落点 | 对账 |
|---|---|---|---|
| `AppShell` `SideRail` `AppBar` `PageBar` | 26 / 26 | 4 件齐备（§2.3 / §2.11 / §2.2 / §2.9） | 一致 |
| `EvidenceDrawer`（`.sheet`，480px，Esc 关闭并返回触发焦点） | 26 / 26 | §2.8，焦点回收实测在 `:10-25` | 一致 |
| `StatusTag`（收敛 `.tag` 与 `.st`） | 26 / 26 | §2.12 | 一致（颜色单载体风险已登记） |
| `PageGrid` `CardPanel` | 26 / 26 | §2.10 / §2.4 | 一致 |
| `AlertBanner` `EmptyState`（含六态） | 26 / 26 | §2.1 / §2.7 | **部分**：两件齐备，但六态语义未落地（当前只有失败 / 无记录两态）→ 由 M0-03b 收敛 |
| `DataTable`（行高 40/36、等宽数字、键盘排序、游标 25 行、宽表冻结首列） | 24 / 26 | §2.6 | **部分**：等宽数字与键盘排序已落地；36px 密集档与冻结首列未实现（首次需要者 M2-04） |
| `ConfirmDialog`（520px，最小实现，M2-04 复用同一实现） | UI-01/04/08/13/22/24 | §2.5 | 一致（Esc 焦点边界已登记） |

- 计数对账：§1 中「首次交付 M0-03」的组件名共 **12 个**，实测 `web/src/components/` 有 **12 个 `.vue` + 1 个 `componentTypes.ts` = 13 件**，**无缺件、无计划外多余件**。
- 尚未交付的 §1 组件（不属本清单，仅列明以免 wave3 误引用）：`ScopeBar`（M1-04）、`JobProgress`（M0-04）、`DiffTable` / `DiffPanel` / `Timeline`（M2-04）、`Tabs` / `StepFlow`（M1-04）、`ChartWithTable`（M3-04）。
- 「排队或计算」态（`COMMON.md:29`）由 `JobProgress` 承担，首次交付 M0-04，**不在** M0-03b 的六态内。

## 7. 诚实偏差与未决问题

- D1（已登记不修）：`ConfirmDialog` 打开时未主动聚焦，Esc 依赖焦点已在框内（§2.5）。
- D2（已登记不修）：`AppShell` 未把 `drawer` / `entryActive` 透传给 `SideRail`（§2.3）。
- D3（已登记不修）：`DataTable` 缺 36px 密集档与宽表冻结首列（§2.6）。
- D4（已登记不修）：`StatusTag` 五 tone 形状相同，颜色是主要区分载体（§2.12）。
- D5（工具链偏差）：抽取 slot 与页面消费点时，PowerShell 会剥除 `bash -lc` 内层双引号，导致 `<slot` / `<AlertBanner` 里的 `<` 被 bash 当重定向（实测报错 `bash: line 1: AlertBanner|: No such file or directory`）；已改走 `python3 /mnt/d/.../probe.py` 通道（C9），未使用 `\$?` 采集 rc。
- U-1（交编排器裁定）：`AlertBanner.vue` / `EmptyState.vue` 是否需要**物理迁入** `web/src/components/state/`？迁入会改 `web/src/pages/**` 的 import 路径，而 `pages/**` 在 M0-03b 的 `scope_deny` 内 → 本清单按「**不迁移，原址冻结 + `state/` 内组合复用**」裁定；若编排器要求迁移，须同时放开 `pages/**` 并作为独立 CR。
- U-2（交编排器裁定）：`web/tests/e2e/**` 未列入 M0-03b 的 `scope_allow`，但六态截图（S4）需要一个可渲染六态的 harness；请裁定扩 `web/tests/e2e/state/**` 或指定其他落点。
