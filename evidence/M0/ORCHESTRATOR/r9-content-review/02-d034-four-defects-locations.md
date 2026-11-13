# 02 · D-034 四处公共组件既有缺陷 —— 权威 file:line 定位

- 缺陷单：`orchestrator/defects/D-034.md`（`severity MINOR`、`status OPEN`、`blocking false`，见 `D-034.md:4-6`）
- 定址依据：`D-034.md:23` 的 path_caliber 把权威行号交给「13 件组件契约表的内容级复核」；本次复核已完成（见 `01-component-contract-table-review.md`），故本报告给出**权威 file:line**。
- 缺陷四项原文口径出处：`D-034.md:18`（#1）、`D-034.md:19`（#2）、`D-034.md:20`（#3）、`D-034.md:21`（#4）；修法约束 `D-034.md:33`；时序 `D-034.md:32`。
- 全部结论基于本会话实测读取，未引用记忆值。

## #1 `ConfirmDialog` 打开时未主动聚焦（关联 **AC-032**）

**结论：CONFIRMED**

| 要素 | 权威 file:line | 实测内容 |
|---|---|---|
| 组件文件 | `web/src/components/ConfirmDialog.vue`（全文 34 行） | 件存在于 13 件清单（`ls` 实测） |
| `open` prop 声明 | `web/src/components/ConfirmDialog.vue:4` | `open: boolean;`（必填，`:3` 起 `defineProps<{`） |
| open 的唯一处理位置 | `web/src/components/ConfirmDialog.vue:13` | `<div v-if="props.open" class="cl-confirm-mask" @keydown.esc="emit('cancel')">` —— `open` 只驱动渲染，**不触发任何焦点动作** |
| 可编程聚焦目标 | `web/src/components/ConfirmDialog.vue:14` | `<div class="cl-confirm" role="dialog" aria-modal="true" :aria-label="props.summary" tabindex="-1">` —— 有 `tabindex="-1"` 但无 `ref`，因此不可被脚本聚焦 |
| `focus()` 相关代码是否存在 | **不存在**（NOT_FOUND，实测 0 命中） | grep `focus\|tabindex\|autofocus` → 仅 `:14` 一处 `tabindex="-1"`；grep `watch\|onUpdated\|onMounted\|nextTick\|focus` → 空 |
| Esc 关闭路径 | `web/src/components/ConfirmDialog.vue:13` | `@keydown.esc` 绑在 mask 上，keydown 只能源自该子树内已聚焦元素 → 焦点不在框内时 Esc 无效，缺陷描述成立 |
| 现存正例（证明是缺口而非架构限制） | `web/src/components/EvidenceDrawer.vue:10-25`、`:13`、`:17`、`:35` | 抽屉件已实现 `panel.value?.focus()`（`:13`）+ 关闭归还 `trigger.value?.focus()`（`:17`），模板 `:35` 同时具备 `ref="panel"` 与 `tabindex="-1"` |
| 唯一调用方 | `web/src/pages/workspace/WorkspacePage.vue:215`（import 于 `:12`，`</AppShell>` 收尾 `:222`） | 实测 pages 目录内仅这一处 `ConfirmDialog` 用法 |

**最小修复面建议（append-only，禁改既有 props 语义）**
1. `web/src/components/ConfirmDialog.vue:14` 给 `.cl-confirm` 增加 `ref="panel"`（`tabindex="-1"` 已具备，无需新增语义）。
2. 在 `:2` 的 import 位增加 `onUpdated`/`watch`，新增一个 open→true 的聚焦分支与 open→false 的焦点归还分支，逻辑照抄 `EvidenceDrawer.vue:10-25` 的 `closable` 状态机；新增私有 `ref`（`panel`/`trigger`）**不得**进入 props/emits 契约（对外签名不变，`D-034.md:33` 要求「open 时把焦点移入框内并处理关闭后的焦点归还」）。
3. 修复须与 `D-034.md:33` 一致，并同步 `M0-03-public-components.md` §2.5（`H:98-104`）与 §7 D1（`H:297`）。

## #2 `DataTable` 缺 36px 密集档 + 宽表未冻结首列

**结论：CONFIRMED（两点均成立）**

| 要素 | 权威 file:line | 实测内容 |
|---|---|---|
| 组件文件 | `web/src/components/DataTable.vue`（49 行） | — |
| 行高档位 props | **不存在**（NOT_FOUND） | `defineProps` 仅 `:3-9` 的 `columns` / `rows` / `sortKey` / `sortDir` / `caption`，无 `rowHeight` / `dense` / `size` 类 prop |
| 行高 CSS 唯一消费点 | `web/src/components/DataTable.vue:46` | `.cl-table td { height: var(--cl-row-h); ... }` —— 单一档 |
| 表头行高 | `web/src/components/DataTable.vue:45` | `.cl-table th { height: 32px; ... }` 硬编码，亦无档位开关 |
| 40px 令牌 | `web/src/styles/tokens.css:77` | `--cl-row-h: 40px;`（规范基线 `spec/CampaignLab-SDD-v1.0/ui/COMMON.md:5`「表格行高 40px，密集数据表 36px」） |
| 36px 令牌已存在但**零消费** | `web/src/styles/tokens.css:78`、`:92` | `--cl-row-h-dense: 36px;`、`--cl-fs-table-dense: 12.5px;`；grep `row-h-dense\|fs-table-dense` 于 `web/src` 与 `web/tests` 全域 → 仅命中这两处**定义行**，无任何引用 |
| 冻结首列实现 | **不存在**（NOT_FOUND） | grep `sticky` 于 `web/src` + `web/tests` → 0 命中；`DataTable.vue:42` 只有 `.cl-table-scroll { overflow-x: auto; }`（横滚已具备，`COMMON.md:15`「数据表在自身区域横滚」），但无 `position: sticky` / 首列 `nth-child(1)` 规则 |
| 规范侧口径 | `spec/CampaignLab-SDD-v1.0/ui/COMMON.md:15` | 「冻结首列仅用于宽表」 |
| 契约表自认 | `orchestrator/handoff/M0-03-public-components.md:288`、`:299` | 「36px 密集档与冻结首列未实现（首次需要者 M2-04）」；D3 已登记不修 |
| 唯一调用方 | `web/src/pages/workspace/WorkspacePage.vue:162-166`（import `:8`） | `<DataTable ... caption="工作区">` + `#cell-action` 作用域槽 |

**最小修复面建议（append-only）**
1. 新增可选 prop（如 `rowHeight?: "default" \| "dense" \| undefined`，默认 `"default"`）于 `DataTable.vue:3-9` 的 props 块尾部；不改动 `columns`/`rows`/`caption` 等既有必填项语义。
2. 模板 `:18` 的滚动容器上输出档位标记（`:data-row-height="..."`），CSS 追加 `.cl-table-scroll[data-row-height="dense"] td { height: var(--cl-row-h-dense); }`，直接复用 `tokens.css:78`、`:92` 的既有令牌 → **不新增令牌**，避免触碰 `M0-03-public-components.md:H:61` 的令牌 CR 边界。
3. 冻结首列走同类 append-only：`:33` 的 `<td>` 增加 `:class="col.mono === true ? 'is-mono' : ''"` 之外的首列标记（如按 `colIndex === 0` 加 `is-frozen`），并在 `:42` 容器上以 `position: sticky; left: 0` 实现，规则仅在 `columns.length` 超阈值时生效；`th` 同步。
4. 同步登记：`M0-03-public-components.md` §2.6（`H:115-121`）、§7 D3（`H:299`）、§5 覆盖对账行（`H:288`）。

## #3 `StatusTag` 五 tone 形状完全相同、仅靠颜色区分（关联 **AC-032**）

**结论：CONFIRMED**

| tone 枚举值 | 生成类名（`StatusTag.vue:7` 的 `'is-' + tone().toLowerCase()`） | 该 tone 的**全部**样式差异 | 非颜色维度（图标/形状/文本前缀） |
|---|---|---|---|
| `OK` | `.is-ok` | `web/src/components/StatusTag.vue:29` 仅 `color: var(--cl-ok-text); border-color: var(--cl-ok-600);` | **无** |
| `WARN` | `.is-warn` | `:30` 仅 `color` + `border-color` | **无** |
| `DANGER` | `:31` → `.is-danger` 仅 `color` + `border-color` | `:31` | **无** |
| `INFO` | `.is-info` | `:32` 仅 `color: var(--cl-ink-600); border-color: var(--cl-info-600);` | **无** |
| `NEUTRAL`（默认，`:4`） | `.is-neutral` | `:33` 仅 `color: var(--cl-ink-500);`（连 `border-color` 都不覆盖） | **无** |

| 要素 | 权威 file:line | 实测内容 |
|---|---|---|
| 枚举定义（五值） | `web/src/components/componentTypes.ts:1` | `"NEUTRAL" \| "OK" \| "WARN" \| "DANGER" \| "INFO"` |
| 模板唯一渲染结构 | `web/src/components/StatusTag.vue:7` | `<span class="cl-tag" :class="'is-' + tone().toLowerCase()">{{ label }}</span>` —— 五个 tone 共用**同一个** `<span>` 结构与同一条 class 规则，无分支 |
| 基盒（形状） | `:10-21` | `height: 20px`、`padding: 0 8px`、`border: 1px solid var(--cl-line)`、`border-radius: var(--cl-radius-sm)` —— tone 不改任何尺寸/圆角/边框宽度 |
| 圆点伪元素 = 颜色跟随 | `:22-28` | `content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor;` —— 形状恒为 6px 圆，`currentColor` 使其**只是颜色的另一种投影**，不构成非颜色载体 |
| 无图标 / 无前缀 / 无 slot | `:6-8`（模板全部 3 行）、无 `defineEmits`、无 `<slot` | 唯一非颜色信息载体是 `label` 文本（props `:3`） |
| 调用方实例（证明依赖文本兜底） | `web/src/pages/workspace/WorkspacePage.vue:140` | `<StatusTag :label="'phase ' + workspaces.state.phase" />` 未传 tone；`:141` 传 tone 但同时改 label 文本 |
| 六态件的连带口径 | `orchestrator/handoff/M0-03b-freeze.md:76`（补充裁定 F-D） | 明写「五 tone 形状完全相同、只靠颜色 + `currentColor` 圆点区分（实测 `StatusTag.vue:22-33`）」，并要求六态件不得以 tone 作唯一区分手段 |
| 可达性红线 | `D-034.md:20`、`D-034.md:34` | 违反「不得仅以颜色传达状态」；**禁**为过 AC-032 以「颜色可辨」替代非颜色维度；**禁**删既有 tone 枚举值 |

**最小修复面建议（append-only，禁改既有 props 语义、禁删枚举值）**
1. 保持 `tone` prop 名 / 类型 / 默认值不变（`StatusTag.vue:3-4`），只在 `:29-33` 各 tone 类上追加**非颜色维度**：`::before` 按 tone 改形状（如 `OK` 圆 / `WARN` 三角 `clip-path` / `DANGER` 方 / `INFO` 环 / `NEUTRAL` 横线），或按 tone 追加文本前缀（`aria-hidden` 图形 + 已有 `label` 不动）。
2. 若走图标路线，须按 `spec/CampaignLab-SDD-v1.0/ui/COMMON.md:38`「图标按钮须有名称」同批提供可访问名称；建议新增可选 prop（如 `shapeVariant?: boolean \| undefined`，默认 `false`）而非改动 `tone`，以便渐进启用且不破调用方。
3. 新增形状类不得引入六位十六进制字面量（`M0-03-public-components.md:H:49` 的令牌守卫 `web/tests/unit/tokens-guard.spec.ts`）。
4. 同步登记：§2.12（`H:188-189`）、风险点段（`H:193`）、§7 D4（`H:300`）。

## #4 `AppShell` 未把 `drawer` / `entryActive` 透传给 `SideRail`

**结论：CONFIRMED**

| 要素 | 权威 file:line | 实测内容 |
|---|---|---|
| `AppShell` 的 props（无 `drawer` / `entryActive`） | `web/src/components/AppShell.vue:6` | `defineProps<{ health?: Health \| undefined; session?: Session \| undefined; recentWorkspace?: string \| null }>()` —— 仅三项 |
| 模板里 `SideRail` 的绑定 | `web/src/components/AppShell.vue:11` | `<SideRail />` —— **零绑定**，既无 props 也无 emits，`drawer` / `entryActive` 完全无法由外壳驱动 |
| `SideRail` 自身声明的 props | `web/src/components/SideRail.vue:4` | `defineProps<{ drawer?: boolean \| undefined; entryActive?: boolean \| undefined }>()` |
| 消费侧行为 | `SideRail.vue:7`（`is-drawer` 类，仅 `=== true`）、`:8`（入口链接，仅 `=== false` 隐藏） | 因 `:11` 无绑定，两处分支恒走默认：无 `is-drawer`、入口链接恒渲染 |
| import 边存在 | `AppShell.vue:3` | `import SideRail from "./SideRail.vue";` |
| 唯一 `AppShell` 调用方 | `web/src/pages/workspace/WorkspacePage.vue:137` | 绑定 `health` / `session` / `recent-workspace` / `@evidence`，未含 `drawer` / `entryActive`（`SideRail` 在 pages 层无直接引用，grep 实测 0 命中） |
| 契约表自认 | `M0-03-public-components.md:298`（§7 D2）、`H:179-180`（SideRail props 表）、`H:69-74`（AppShell 表） | 登记不修 |
| 规范动因 | `spec/CampaignLab-SDD-v1.0/ui/COMMON.md:15` | 「≤800px 导航改抽屉」—— 抽屉态需外壳可下发；`AppShell.vue:36-38` 已有 800px 断点栅格但无法联动 `is-drawer` |

**最小修复面建议（append-only 接口补齐）**
1. `AppShell.vue:6` 的 props 块**追加**两个可选项：`drawer?: boolean \| undefined`、`entryActive?: boolean \| undefined`（全部可选 ⇒ `WorkspacePage.vue:137` 现存调用不破）。
2. `AppShell.vue:11` 改为 `<SideRail :drawer="props.drawer" :entry-active="props.entryActive" />`（`SideRail.vue:4` 签名已具备，无需改动 SideRail）。
3. 因新 props 可选且默认 `undefined`，`SideRail.vue:7` 的 `=== true` 与 `:8` 的 `!== false` 判定语义保持不变 → **不改既有 props 语义**（符合 `D-034.md:33` 「透传属接口补齐，须同步 13 件组件契约表」）。
4. 同步登记：§2.3（`H:69-74`）、§7 D2（`H:298`）；如要页面侧真正驱动，须由页面任务（M1-04 / M2-04）以视口或 store 值传入，禁在组件内自行发明媒体查询副作用。

## 关联与时序（照 `D-034.md:7`、`:32`）

- **#1 与 #3 关联 AC-032**（`D-034.md:18`、`:20`），**必须在 M5-01（AC-032 取证）之前修复并留证**（`D-034.md:32`）；#2 与 #4 可随首个消费方任务（M1-04 / M2-04）顺带处理，但须在派单文里显式点名。
- 四项均落在**已冻结面**（`web/src/components/**`），任何修复都须走 CR（`M0-03-public-components.md:H:56-62` 冻结边界表）。

RESULT: 4 项定位完毕 / CONFIRMED 4 项 / NOT_REPRODUCIBLE 0 项 / 整体 NOT_FOUND 0 项（仅 #1 的 focus 代码子项为 NOT_FOUND，作为缺陷成立的正面证据）
