# M0-03b 六态冻结面裁定（S1 产出）

- 产出子任务：M0-03b / S1（`orchestrator/tasks/M0-03b.md:37`：`qwen3.8-max` high / 14k / 产出本文件）
- 产出日期：2026-11-13（Asia/Shanghai）
- 上游输入：`orchestrator/handoff/M0-03-public-components.md`（M0-03 / S10，同批产出，本文件所有「现有签名」均引它而不复述）
- 实测基线：分支 `m0-framework`，HEAD `34e4709`，`git status --porcelain web/src | wc -l` = `0`
- 本文件性质：**只裁定，不落码**。S1 未创建 `web/src/components/state/**`、未改任何 `web/**` 文件；实现由 S2-S4 承担
- 令牌口径：本文不出现任何六位十六进制色值，色值一律引令牌名（唯一真值 `docs/design/token-mapping.md`）
- gate 自证：本文件含「外部注册」字样（§4 全章），满足 `grep -c 外部注册 orchestrator/handoff/M0-03b-freeze.md` >= 1

## 1. 六态定义表（与 `spec/CampaignLab-SDD-v1.0/ui/COMMON.md` 逐条对齐）

### 1.1 原文逐条引用（D-011：只引原文、禁改写措辞）

以下 8 行是六态的**唯一规范来源**，逐字抄录（含表格竖线），行号为 `spec/CampaignLab-SDD-v1.0/ui/COMMON.md` 实测行号（章节标题在 `:23`「共享状态与操作」，表头在 `:25-26`）：

> `ui/COMMON.md:27` ｜ 首载
> `| 首载 | 主区骨架对应标题、表头和卡片位置。保留导航 |`

> `ui/COMMON.md:28` ｜ 无记录
> `| 无记录 | 指明当前筛选，提供创建、导入或清空筛选入口 |`

> `ui/COMMON.md:29` ｜ 排队或计算（**不属六态**，见 §1.4）
> `| 排队或计算 | 显示作业号、阶段和进度，允许到作业中心。上次结果可见且有「上一结果」标识 |`

> `ui/COMMON.md:30` ｜ 部分可比 / 待补（**一行承载两态**）
> `| 部分可比 / 待补 | 原值仍显示，差值按共同子集或留空。提供原因、缺项和导出入口 |`

> `ui/COMMON.md:31` ｜ 失败
> `| 校验失败 | 错误摘要跳转字段，字段标注语义。保留输入 |`

> `ui/COMMON.md:32` ｜ 412 过期
> `| 过期 | 412 或候选失效时保留本地输入，显示新旧版本和重新获取或复跑入口 |`

> `ui/COMMON.md:36` ｜ 数字与缺项规则（六态通用）
> `| 数字 | 缺值显示 — 与原因。比率小数转百分数，率差转百分点，金额分转元，负余额增量保留 |`

> `ui/COMMON.md:38` ｜ 通用交互与可读性（六态通用）
> `表单绑定输入 Schema。相同任务请求收到 202 后使用 GET 作业，成功再取结果。错误显示 request_id。列表默认 25 行，更多数据由服务器游标加载。图标按钮须有名称，抽屉 Esc 可关闭并返回触发焦点，表格排序支持键盘。焦点和读屏提示以 WCAG 2.2 AA 为验收目标。所有业务页面使用这些规则及各页专属状态。`

### 1.2 态 → 触发条件 → 原文行号

| 态名 | 冻结字面量 | 触发条件（可判定，禁发明语义） | `ui/COMMON.md` 行 | 引文摘要（逐字） |
|---|---|---|---|---|
| 首载 | `first-load` | 页面首次装载且尚无成功响应：store `phase` 属 `idle` / `loading`（`useWorkspaces.ts:32`）或 `unknown` / `checking` / `exchanging`（`useSession.ts:26`），且 `error === null` | `:27` | 主区骨架对应标题、表头和卡片位置。保留导航 |
| 无记录 | `no-record` | 请求成功且结果集为空（`phase === "empty"`，由 `useWorkspaces.ts:139` 依 `items.length === 0` 判定） | `:28` | 指明当前筛选，提供创建、导入或清空筛选入口 |
| 失败 | `failed` | `error !== null` 且**非** 412 / 候选失效：即 `error.status !== 412` 且 `presentationOf(error).bucket !== "CONFLICT"`（含 `bucket === null` 的未知 code 与非 problem 失败） | `:31`（+ `:38` 的 request_id） | 错误摘要跳转字段，字段标注语义。保留输入 |
| 部分可比 | `partial-comparable` | 成功响应且结果被标记为只按共同子集可比（标记由结果载荷提供，见 U-4）；**不是错误态** | `:30` | 原值仍显示，差值按共同子集或留空。提供原因、缺项和导出入口 |
| 待补 | `pending-fill` | 成功响应且存在缺项（`missing` 非空），差值留空；**不是错误态** | `:30`（+ `:36` 的缺值规则） | 同上；缺值显示 — 与原因 |
| 412 过期 | `stale-412` | `error !== null` 且（`error.status === 412` 或 `presentationOf(error).bucket === "CONFLICT"`） | `:32` | 412 或候选失效时保留本地输入，显示新旧版本和重新获取或复跑入口 |

裁定要点：

- **F-A：`state` 是必填 prop，由页面 / composable 决定**。`stateFromError()` 只推导两个错误态（`failed` / `stale-412`），其余四态由调用方按 store `phase` 与结果载荷显式传入；组件不猜。
- **F-B：错误态判定禁止新增 code 白名单**。`web/src/components/state/**` 内只允许消费 `presentationOf()` 的返回（`problemPresentation.ts:55-65`）与 `error.status`，**不得**再出现任何 problem code 字面量（Q4 / RULING_NO_FRONTEND_MIRROR，见 `problemPresentation.ts:3`）。`problemPresentation.ts` 位于 `web/src/features/shared/`，在 M0-03b 的 `scope_deny` 内：只读，不改。
- **F-C：`排队或计算` 不在六态内**（`:29`），归 `JobProgress`（首次交付 M0-04）。六态件只提供 `showPrevious` 呈现「上一结果」标识，不实现作业号 / 阶段 / 进度。

### 1.3 态 → 呈现要素 → 数字与缺项 → 不靠颜色区分的落实

| 态名 | 文案来源（禁改写） | 图标 | 默认动作键 | role / aria | `data-state` | 数字与缺项规则 |
|---|---|---|---|---|---|---|
| 首载 | 无文案（骨架只占位，不出字） | 无 | 无 | `role="status"` + `aria-live="polite"` + `aria-busy="true"` | `first-load` | 骨架**不得**渲染 `0` 或空串冒充数据；缺值一律走 `—` |
| 无记录 | 页面按 `:28` 指明当前筛选（筛选原文由页面契约给，组件不编） | 无 | `create`、`clear-filter`（`import` 只在有导入语义的页面由 `actions` prop 显式加入） | `role="status"` | `no-record` | 无数字；若出现计数，必须是服务端原值 |
| 失败 | 服务端 Problem 的 `title` / `detail` / `request_id` **原样渲染**（ADR-005 §2.2，`AlertBanner.vue:10`、`:21`）；非 problem 失败用固定「请求未完成」（`AlertBanner.vue:10`） | 无 | 无（「跳转字段」由页面按 `issues[].location` 自行接线） | `role="alert"`（沿用 `AlertBanner.vue:9`） | `failed` | 不显示业务数字；`request_id` 恒可见且等宽（`:38`） |
| 部分可比 | 页面按 `:30` 给原因；组件不编措辞 | 无 | `export` | `role="status"` + `aria-live="polite"` | `partial-comparable` | **原值仍显示**，差值按共同子集；不可比的单元格用 `—` + 原因 |
| 待补 | 页面按 `:30` 给缺项名与原因 | 无 | `export` | `role="status"` + `aria-live="polite"` | `pending-fill` | **原值仍显示**，差值留空 → `—` + 原因（`:36`） |
| 412 过期 | 服务端 Problem 原样 + 页面给新旧版本串 | 无 | `refetch`、`rerun` | `role="alert"` | `stale-412` | 版本号是字符串原值，**不做**数字格式化；保留本地输入（`:32`） |

「不靠颜色区分」的四条**非颜色载体**（六态各自至少具备前三条，第四条按需）：

1. **文案**：每态有唯一**可判定标识**（根元素 `data-state="<字面量>"`）；错误态的标题来自服务端原文，其余来自 `copyOf(state)`（逐字引 `ui/COMMON.md` 对应行，见 §3.3）。〔**A150 更正（R10）**：原记「每态有唯一标题」——与 §3.3 的 `partial-comparable` / `pending-fill` 共用 `COMMON.md:30` 首句相冲突。裁定：逐字文案是**硬约束**、唯一标题降为**软目标**，两态的区分由 `data-state` + hint + 缺项区（`—` + 原因）三者共同承载；**禁**为造唯一标题而改写 `ui/COMMON.md` 原文（spec 侧只读区，且属文案漂移）。〕
2. **机器可读属性**：根元素恒有 `data-state="<字面量>"`，测试与走查用属性选择器定位，不取 `computed color`。
3. **语义角色**：`role="alert"`（失败 / 过期）与 `role="status"`（其余四态）二分，读屏可区分。
4. **动作键**：`data-action="<ViewStateAction>"` 落在每个动作按钮上，动作集合本身即区分手段；图标按钮必须有名称（`:38`）。

补充裁定 **F-D**：`StatusTag` 的五个 tone 形状完全相同、只靠颜色 + `currentColor` 圆点区分（实测 `StatusTag.vue:22-33`，见 `M0-03-public-components.md` §2.12）。因此六态件**不得**把 `StatusTag` 的 tone 当作唯一区分手段；六态件自身不引入图标字形依赖，若页面要加图标，必须同时给可访问名称（`:38`）。

补充裁定 **F-E**：本次冻结面**不包含**数字单位换算（`:36` 后半句「比率小数转百分数，率差转百分点，金额分转元，负余额增量保留」）。理由：`web/src/features/shared/` 现无任何格式化实现（实测只有 `navigation.ts` 与 `problemPresentation.ts`），而 `features/**` 在 M0-03b 的 `scope_deny` 内；在 `state/` 内新建格式化件会与 M1-04 / M3-04 的首个真实需要者重复。故 `MissingValue` 只负责「缺值 `—` + 原因」，单位换算归各页面显示层（`framework/FRONTEND.md:7`），待首次需要时抽公共件并走 CR（U-3）。

### 1.4 相邻但**不在**六态内的场景（边界声明）

| `ui/COMMON.md` 行 | 场景 | 归属 |
|---|---|---|
| `:29` | 排队或计算 | `JobProgress`，M0-04（六态件只提供 `showPrevious`） |
| `:33` | 会话 / 权限 | 组合根与 `useSession`；越权按不可见处理由 `presentationOf().sameAsNotFound` 承载（`problemPresentation.ts:61`） |
| `:34` | 确认动作 | `ConfirmDialog`（M0-03 已交付，`ConfirmDialog.vue`） |
| `:35` | 明细和证据 | `EvidenceDrawer`（M0-03 已交付，含 Esc 与焦点回收） |

## 2. 收敛方式裁定（组合而非改写）

- **F-1（硬约束）**：M0-03b 的越界自证 gate 是 `git diff --name-only HEAD -- web/src | grep -v '^web/src/components/state/' | wc -l` → `0`，即本卡在 `web/src` 内**只能写 `state/` 一个目录**。故 `AlertBanner.vue` 与 `EmptyState.vue`（实测各 43 / 19 行，位于 `web/src/components/` 根）在 M0-03b 期间**一行都不得改**。卡 goal 里的「把 `AlertBanner` / `EmptyState` 收敛为六态公共件」据此落地为：**在 `state/` 内新建调度件去复用两件的现有签名**，而不是改写它们。
- **F-2**：两件**原址保留**，签名冻结不变（`M0-03-public-components.md` §2.1 / §2.7）。`state/ViewState.vue` 内部：`failed` / `stale-412` 渲染 `AlertBanner`，`no-record` / `partial-comparable` / `pending-fill` 渲染 `EmptyState`，`first-load` 渲染 `FirstLoadSkeleton`。既有页面（`WorkspacePage.vue:146`、`:155-161`、`:196`）**不在本卡迁移**；页面改用 `ViewState` 属各页面任务自己的 scope。
- **F-3**：`state/` 内的件**不得**复制 `AlertBanner` / `EmptyState` 的样式或结构（禁止二次实现，口径同 `page-component-map.md` §1 对 `ConfirmDialog` 的裁定）；只允许 import 复用。
- **F-4**：文案只能有三个来源，优先级 **props（页面显式）> 外部注册 variant 的 `copy`（§4）> `copyOf(state)`（`ui/COMMON.md` 原文）**。任何第四来源（组件内自编、模板 HTML 抄写）都视为越界。
- **F-5**：`state/` 内**不新增**任何 HTTP 端点、不改 `web/src/api/types.ts`（生成物）、不新增或修改 `spec/**` / `contracts/**` 样本；六态桩数据只允许内联在 `web/tests/unit/state/**`（卡 `fixtures` 段）。
- **F-6**：桩数据与用例**一律不得出现「按 status 过滤工作区」**（CR-002 / ADR-006：`listWorkspaces` 只有 `cursor` / `limit` / `q`）。注意别把该禁令与 `Health.status`（`READY` / `DEGRADED`，`endpoints.ts:59-63`）混淆——后者是 `AppBar` / `first-load` 的合法输入。

## 3. 冻结签名（冻结清单）

### 3.1 冻结清单总表

| # | 组件 / 模块 | 位置 | 冻结级别 | 契约出处 |
|---|---|---|---|---|
| 1 | `AlertBanner` | `web/src/components/AlertBanner.vue` | 公共冻结件（M0-03 起，本卡不改） | `M0-03-public-components.md` §2.1 |
| 2 | `EmptyState` | `web/src/components/EmptyState.vue` | 同上 | 同上 §2.7 |
| 3 | `AppShell` `AppBar` `SideRail` `PageBar` `PageGrid` `CardPanel` `DataTable` `EvidenceDrawer` `ConfirmDialog` `StatusTag` | `web/src/components/*.vue` | 同上 | 同上 §2.2-§2.6、§2.8-§2.12 |
| 4 | `componentTypes.ts`（`StatusTone` / `TableColumn` / `TableRow`） | `web/src/components/componentTypes.ts` | 同上 | 同上 §2.13 |
| 5 | `viewState.ts`（六态枚举 + `copyOf` + `stateFromError`） | `web/src/components/state/viewState.ts` | **本卡新冻结**（S3 落地） | 本文 §3.3 |
| 6 | `ViewState.vue`（六态调度件） | `web/src/components/state/ViewState.vue` | **本卡新冻结** | 本文 §3.4 |
| 7 | `FirstLoadSkeleton.vue` | `web/src/components/state/FirstLoadSkeleton.vue` | **本卡新冻结** | 本文 §3.5 |
| 8 | `MissingValue.vue` | `web/src/components/state/MissingValue.vue` | **本卡新冻结** | 本文 §3.5 |
| 9 | `registry.ts`（外部注册扩展点） | `web/src/components/state/registry.ts` | **本卡新冻结**（签名冻结，注册内容开放） | 本文 §4.2 |
| 10 | `index.ts`（barrel，只 re-export 5-9） | `web/src/components/state/index.ts` | 冻结（新增导出须走 CR） | 本文 §3.2 |

### 3.2 S3 的目标文件清单（`web/src/components/state/**`，实测当前不存在）

实测 `test -e web/src/components/state` → `STATE_DIR_ABSENT`，`web/src/components/` 当前 13 个文件、0 个子目录。S3 只允许新建下列 6 个文件，**不得**新增其他文件：

`viewState.ts`、`ViewState.vue`、`FirstLoadSkeleton.vue`、`MissingValue.vue`、`registry.ts`、`index.ts`

### 3.3 `viewState.ts`（类型签名级冻结）

```ts
import type { ApiError } from "@/api/http";

export type ViewStateKind =
  | "first-load"
  | "no-record"
  | "failed"
  | "partial-comparable"
  | "pending-fill"
  | "stale-412";

export type ViewStateAction =
  | "create"
  | "import"
  | "clear-filter"
  | "export"
  | "refetch"
  | "rerun";

export interface ViewStateCopy {
  readonly title: string;
  readonly hint: string;
}

export const VIEW_STATE_KINDS: readonly ViewStateKind[];

// 唯一文案来源 = ui/COMMON.md 的 :27 / :28 / :30 / :31 / :32 行原文（D-011：禁改写措辞）
export function copyOf(state: ViewStateKind): ViewStateCopy;

// 默认动作键，逐条对齐 §1.3 表；返回空数组表示该态默认无动作
export function actionsOf(state: ViewStateKind): readonly ViewStateAction[];

// 只允许消费 presentationOf() 与 error.status，禁止出现 problem code 字面量（F-B）
export function stateFromError(error: ApiError): "failed" | "stale-412";
```

`copyOf` 的原文映射（S3 必须逐字实现，S2 必须逐字断言）：

| `state` | `title` 取自 | `hint` 取自 |
|---|---|---|
| `first-load` | `ui/COMMON.md:27` 行为列首句「主区骨架对应标题、表头和卡片位置。」 | 同行次句「保留导航」 |
| `no-record` | `ui/COMMON.md:28` 行为列首句「指明当前筛选，提供创建、导入或清空筛选入口」的前半语义（页面用 `title` prop 覆盖为具体筛选原文） | `:28` 原文动作句 |
| `failed` | 服务端 Problem `title` 原样（`AlertBanner.vue:10`）；非 problem 时固定「请求未完成」 | `ui/COMMON.md:31`「错误摘要跳转字段，字段标注语义。保留输入」 |
| `partial-comparable` | `ui/COMMON.md:30`「原值仍显示，差值按共同子集或留空。」 | `:30`「提供原因、缺项和导出入口」 |
| `pending-fill` | 同 `:30` 首句 | `:30` + `:36`「缺值显示 — 与原因。」 |
| `stale-412` | `ui/COMMON.md:32`「412 或候选失效时保留本地输入，显示新旧版本和重新获取或复跑入口」 | 同句（动作键 `refetch` / `rerun` 承载「重新获取或复跑」） |

### 3.4 `ViewState.vue`（六态调度件）冻结签名

props：

| 名称 | 类型 | 必填 | 默认（模板兜底，口径同 `M0-03-public-components.md` §1 事实 1） | 约束 |
|---|---|---|---|---|
| `state` | `ViewStateKind` | 是 | — | 渲染为根元素 `data-state`；六字面量之外即类型错误 |
| `error` | `ApiError \| null` | 否 | `null` | `state` 为 `failed` / `stale-412` 时必须非 `null`（dev 断言），原样转交 `AlertBanner` |
| `title` | `string \| undefined` | 否 | `copyOf(state).title` | 覆盖优先级见 F-4 |
| `hint` | `string \| undefined` | 否 | `copyOf(state).hint` | 同上 |
| `actions` | `readonly ViewStateAction[] \| undefined` | 否 | `actionsOf(state)` | 每个动作渲染为**有名称**的按钮并带 `data-action`（`:38`） |
| `missing` | `readonly string[] \| undefined` | 否 | `[]` | 仅 `partial-comparable` / `pending-fill` 使用；每项渲染为「缺项名 — 原因」 |
| `reason` | `string \| undefined` | 否 | `undefined` | 与 `—` 同现（`:36`） |
| `showPrevious` | `boolean \| undefined` | 否 | `false` | 「上一结果」标识（`:29`），只呈现不计算 |
| `keepInput` | `boolean \| undefined` | 否 | `false` | 提示保留本地输入（`:31` / `:32`）；组件**不持有**表单状态 |
| `context` | `ViewStateContext \| undefined` | 否 | `undefined`（未传即三字段 null，组件不猜） | 传给 `resolveVariants()`（§4.2）；消费页面**必须显式传入**（M3-P02 接入见 FU-27）。〔**A148 更正（R10）**：原记「由当前路由推导」不可采纳——读路由属数据获取副作用，与 A137 直接冲突；**编排器复核实测（R10-5 更正）**：`grep -rnE -- "from ['\"]vue-router"`、`grep -rnE -- 'useRoute'`、`grep -rnE -- 'import\(|require\('` 在 `state/` + `tests/unit/state/` 上均 **rc=1、0 命中**（无运行期路由依赖）；`grep -rnE -- 'vue-router|useRoute'` 有 **1 命中**，是 `ViewState.vue:22` 的**注释行**（正是记录「context 默认值需 vue-router、与 A137 冲突故不用」），非依赖边。〕 |

emits：

| 事件 | 载荷 | 触发 |
|---|---|---|
| `action` | `[kind: ViewStateAction]` | 任一动作按钮被点击或键盘激活；`ViewState` **不自行导航**，由页面接线 |

slots：

| 名称 | 作用域参数 | 用途 |
|---|---|---|
| `default` | 无 | 该态的附加内容（如新旧版本对照、缺项明细表） |
| `footer` | 无 | 状态区下方补充位 |
| `evidence` | 无 | 证据入口（接到 `EvidenceDrawer`，`:35`） |

不变量（S2 必须逐条断言）：根元素恒有 `data-state`；`failed` / `stale-412` 的 `role="alert"` 且 `request_id` 可见；其余四态 `role="status"` + `aria-live="polite"`；`first-load` 另带 `aria-busy="true"`；无动作时不渲染动作区（口径同 `EmptyState.vue:9`）。

### 3.5 `FirstLoadSkeleton.vue` 与 `MissingValue.vue`

| 组件 | props（名称 / 类型 / 必填 / 默认） | slots | emits | 对齐的原文 |
|---|---|---|---|---|
| `FirstLoadSkeleton` | `heading: string \| undefined`（否 / 不渲染文字，只出占位块）；`headCells: readonly string[] \| undefined`（否 / `[]`，给定时渲染同数量表头占位格）；`cardCount: number \| undefined`（否 / `0`） | 无 | 无 | `:27`「主区骨架对应标题、表头和卡片位置。保留导航」——**保留导航**指骨架只放进 `AppShell` 的 default slot（`AppShell.vue:14`），不得包裹或替换 `SideRail` |
| `MissingValue` | `value: string \| number \| null`（是 / —）；`reason: string \| undefined`（否 / 不渲染原因）；`mono: boolean \| undefined`（否 / `false`，为 `true` 时加 `font-variant-numeric: tabular-nums`） | 无 | 无 | `:36`「缺值显示 — 与原因。」+ `token-mapping.md:45`（数字一律 tabular-nums） |

`MissingValue` 的判定：`value === null` 或（`typeof value === "number"` 且 `Number.isFinite(value) === false`）或（`typeof value === "string"` 且长度为 0）→ 渲染 `—`；否则渲染原值。空串视为缺值是**呈现层裁定**，不改变任何契约字段。

## 4. 外部注册扩展点方案（月报视角）

### 4.1 要求出处

- 手册 15.6 末条：`docs/delivery/LONG-HORIZON-ORCHESTRATION.md:691-692`——「公共件冻结前（wave2 出口）必须确认已为后续月报指标预留**外部注册**扩展点，否则 wave5 的 L3 lane 将被迫走 CR 串行合并，吃掉其 slack 并被推成关键路径。」
- `docs/delivery/MONTHLY-DELTA-PLAN.md` 第 3 节：`:33`（wave5 行）——「共享注册表属公共件，需注册月报指标时提 CR 由 T 串行合并」；`:35`（wave7 行）——「M3-P02 若需改 UI-17 既有结构，走 CR」。
- 本卡 gate：`orchestrator/tasks/M0-03b.md:15`——月报视角（归 **M3-P02**，覆盖 **AC-MR-03 至 AC-MR-08**，**来源为月度 append 清单而非 ACCEPTANCE.md**）必须能在**不改冻结件**的前提下经注册表接入。

本章的目标就是让 wave5 / wave7 的月报工作**不需要碰本文件 §3 的任何签名**，从而不吃 CR 串行合并的代价。

### 4.2 `registry.ts` 接口草案（类型签名级冻结；注册内容开放）

```ts
import type { Component } from "vue";
import type { ViewStateAction, ViewStateCopy, ViewStateKind } from "./viewState";

export interface ViewStateContext {
  readonly state: ViewStateKind;
  readonly routeName: string | null;
  readonly workspaceId: string | null;
  readonly reviewId: string | null; // ui/COMMON.md:21：可复盘链接优先使用固定的 review_id
}

export interface ViewStateVariant {
  readonly id: string; // 唯一键，月报视角用 "monthly-review"
  readonly appliesTo: (ctx: ViewStateContext) => boolean;
  readonly copy?: Partial<Record<ViewStateKind, Partial<ViewStateCopy>>>;
  readonly extraActions?: Partial<Record<ViewStateKind, readonly ViewStateAction[]>>;
  readonly render?: Component; // 可选：整态替换呈现，必须自行满足 §1.3 的四条非颜色载体
}

export function registerViewStateVariant(variant: ViewStateVariant): void;
export function unregisterViewStateVariant(id: string): void; // 仅测试用
export function resolveVariants(ctx: ViewStateContext): readonly ViewStateVariant[];
```

规则：

- **R-1 单向依赖**：`state/` 内的冻结件**不得** import 任何页面、features 或月报模块；依赖方向恒为「页面 / 月报模块 → `state/` → `registry`」。这是「不改冻结件即可接入」的结构保证。〔**A145 豁免（R10）**：**唯一例外**是 `@/features/shared/problemPresentation` 的 `presentationOf()` —— §1.2/F-B 强制 `stateFromError()` 只消费它（禁在 `state/` 自建 problem code 白名单），且 F-2 强制组合的 `AlertBanner.vue:3` 早已有同一条依赖边（既有先例，非新增耦合形态）。立法意图澄清：R-1 防的是**业务特性**耦合，而 `features/shared/` 是跨特性共享的表现层纯函数、不持业务状态。除此一处外 R-1 全文仍生效；实测 `state/` 内 `features` 依赖边恰 1 条（`viewState.ts:19`）。〕
- **R-2 幂等注册**：同 `id` 重复注册即覆盖，并在 dev 下告警；`resolveVariants` 按注册顺序返回，`ViewState` 取**最后一个**命中的 variant 生效（后注册者可细化，但不能取消前者的 `appliesTo`）。
- **R-3 能力上界**：variant 只能做三件事——覆盖文案（`copy`）、追加动作键（`extraActions`，取值仍限 `ViewStateAction`）、替换呈现（`render`）。**不能**新增 `ViewStateKind` / `ViewStateAction` 字面量、不能改 props 名、不能移除 `data-state` / `role`。
- **R-4 可测性传递**：S2 的参数化用例必须以工厂函数形式导出（六态 × 视口标签矩阵），M3-P02 注册 variant 后**复用同一矩阵**对自己复跑一遍；`render` 替换若不满足四条非颜色载体，用例即判红。
- **R-5 无副作用装载**：`registry.ts` 顶层不得有注册调用；注册发生在调用方模块。

### 4.3 月报视角（M3-P02）的接入路径

1. M3-P02 在自己的 scope（`web/src/pages/review/monthly/**`，见 `MONTHLY-DELTA-PLAN.md:35` 的写权限论证）里 `import { registerViewStateVariant } from "@/components/state"`。
2. 注册一个 `id: "monthly-review"` 的 variant：`appliesTo` 用 `ctx.routeName` / `ctx.reviewId` 判定；`copy` 覆盖月度视角需要的标题与提示（措辞来源必须是月度 append 清单原文，禁自编）；`extraActions` 追加 `export`（月报导出入口）。
3. 覆盖的 AC 是 **AC-MR-03 至 AC-MR-08**，其**来源为月度 append 清单**（`qa/CampaignLab-Review-Acceptance-Checklist.append.md`，见 `MONTHLY-DELTA-PLAN.md:3`、`:18`），**不是** `qa/ACCEPTANCE.md`；断言里引用的 AC 编号必须从两份 QA 文件抄录（D-011）。
4. 若需**全局**注册（而非页面模块顶层副作用），落点是组合根 `web/src/main.ts`（实测 `:27-30` 已有固定注入顺序）——`main.ts` 不在 M0-03b 也不在 M3-P02 的 scope 内，属编排器 / CR。

### 4.4 与后端指标注册表的分工

`MONTHLY-DELTA-PLAN.md:33` 说的「共享注册表属公共件」在**后端**指指标注册表（M0-04 的「指标注册表可外部注册」验收项，见 `docs/delivery/POST-PATCH-REVIEW-v1.0.1.md:44`），在**分析域**指 M3-01 / M3-02 预留的注册式扩展点（`orchestrator/tasks/M3-01.md:73`、`M3-02.md:72`）。本章的 `registry.ts` 是**前端呈现层**的同型扩展点，三者互不代替：前端 variant 只改呈现，不得承载指标口径或计算逻辑。

### 4.5 外部注册的 CR 边界

| 动作 | 是否需要 CR |
|---|---|
| 调用 `registerViewStateVariant()` 注册新 variant（含月报视角） | **不需要** |
| 给 `ViewStateVariant` / `ViewStateContext` 增删字段、改 `appliesTo` 签名 | 需要 |
| 新增 `ViewStateKind` / `ViewStateAction` 字面量 | 需要 |
| 改 `copyOf` / `actionsOf` 的原文映射或默认动作集 | 需要 |

## 5. CR 边界总表（「改动必须走 CR」的登记）

| 改动类型 | 判定 | 依据 |
|---|---|---|
| 改 §3.1 表内 1-4 项（M0-03 既有 12 件 + `componentTypes.ts`）的任何 props / slots / emits / 字面量 | **必须 CR**，且 M0-03b 期间**禁改** | 手册 §3.1 / §7；越界自证 gate |
| 改 §3.1 表内 5-10 项（`state/` 六文件）的签名、枚举字面量、slot 名、emit 载荷 | **必须 CR** | 本卡 `public_frozen` 段：`state/**` 落盘后即公共冻结件 |
| 改 `copyOf` 的原文映射（含 `ui/COMMON.md` 行号漂移导致的重新对齐） | **必须 CR** | D-011：只引原文，行号是契约的一部分 |
| 新增 / 改名 / 删除令牌引用（`var(--cl-*)`），或出现任何色值字面量 | **必须 CR** | `token-mapping.md:3`、`tokens-guard.spec.ts` |
| 改 `registry.ts` 签名 | **必须 CR** | §4.5 |
| 在 `state/` 内新增文件（超出 §3.2 的 6 个） | **必须 CR** | 本卡 `scope_allow` |
| S2 用例展开、S3 件内样板（在已冻结签名内）、S4 截图与证据归档 | **不需 CR** | 卡档位表 S2-S4 = flash，只在 max 划定的文件与函数内工作 |
| 页面消费方从 `AlertBanner` / `EmptyState` 改为 `ViewState` | 不需 CR（属该页面任务自己的 scope） | F-2 |
| 注册外部 variant（月报等） | 不需 CR | §4.5 |

## 6. 验收衔接（照卡「参考引用（非本任务 gate）」段口径）

- **AC-032 不是本卡的 gate**。其原文（`qa/ACCEPTANCE.md:40`）为：「1440×900 与 1024×768 操作键盘、空页和错误分支」→「状态可读，焦点回收，表头和表格滚动正常。数字和缺项不靠颜色区分」〔主证据：截图、键盘轨迹〕。
- AC-032 的验收归属是 **M5-01**（`state.json.tasks["M5-01"].acs` 含 AC-032）。本卡只保证六态件为它提供「不靠颜色区分」的**可测呈现**：即 §1.3 的四条非颜色载体 + `data-state` 属性选择器 + `role` 二分，使 M5-01 能在不取色值的前提下判定「状态可读」。
- 本卡的 gate 只有卡 `gates` 段所列 7 条（六态参数化单测、前端三门、冻结登记、月报外部注册扩展点、越界自证、切片新鲜度、类型客户端未漂移）；S4 的截图是**证据**而非 AC-032 的验收判定。
- 六态件不承担「焦点回收」：焦点回收是 `EvidenceDrawer.vue:10-25` 与 `AppShell.vue:21-24` 的既有契约，六态件只需保证动作按钮可键盘激活（`:38`）。

## 7. 给 S2-S4 的派单就绪清单

### S2 六态参数化 vitest 用例展开（`qwen3.8-flash` / 3k）

- 输入：本文 §1.2、§1.3、§3.3、§3.4、§3.5、§4.2；`M0-03-public-components.md` §2.1 / §2.7；静态断言口径参照 `web/tests/unit/breakpoint-guard.spec.ts`（实测 327 行）；`web/tests/unit/tokens-guard.spec.ts`（实测 268 行）是令牌守卫，别混用。
- 产出（只写 `web/tests/unit/state/**`）：`viewState.spec.ts`、`viewStateCopy.spec.ts`（逐字断言 `copyOf` 与 `ui/COMMON.md` 行原文一致）、`firstLoadSkeleton.spec.ts`、`missingValue.spec.ts`、`registry.spec.ts`。〔**A151 追认（R10）**：另含 `stateMatrix.ts`（405 行）——它**不是 spec**（编排器实测 `describe(` / `it(` / `expect(` 均 0 命中，vitest `include` 为 `*.spec.ts`），是 R-4「S2 的参数化用例必须以工厂函数形式导出」的必要落点：5 个 spec 互相 import 会把对方用例在本文件重复注册一遍，故共享层必须独立成模块。**spec 仍恰为上述 5 个**，§7 的 spec 数量与命名约束未被突破。〕
- 矩阵：`describe.each` 六态 × 视口标签 `{1440x900, 1024x768}`；断言项 = `data-state`、`role` / `aria-live` / `aria-busy`、文案逐字、动作键集合与 `data-action`、`—` + 原因、`failed` / `stale-412` 的 `request_id` 可见。
- 门禁：`cd web && npm run test -- tests/unit/state`、`cd web && npm run typecheck`、`cd web && npm run lint`（各 rc=0；用例数以 rc 为判据，**不写死**）。
- 禁止：不得改 `web/src/**`（那是 S3）；**不得在 vitest 里谎称做了真实视口渲染**——1024x768 在 node/jsdom 下只能做静态断言（断点阈值与 `data-narrow` 语义），真实视口截图归 S4；桩数据只内联在测试文件；不得出现「按 status 过滤工作区」（F-6）；不得引用未从两份 QA 文件抄录的 AC 编号（D-011）。

### S3 件内样板收敛（`qwen3.8-flash` / 2k）

- 输入：本文 §2（F-1..F-6）、§3.2 文件清单、§3.3 类型、§3.4 / §3.5 签名、§4.2 registry 草案。
- 产出（只写 `web/src/components/state/**`，恰好 6 个文件）：`viewState.ts`、`ViewState.vue`、`FirstLoadSkeleton.vue`、`MissingValue.vue`、`registry.ts`、`index.ts`。
- 门禁：`cd web && npm run typecheck`、`npm run lint`、`npm run build`、`npm run test -- tests/unit/state`（各 rc=0）；越界自证 `git diff --name-only HEAD -- web/src | grep -v '^web/src/components/state/' | wc -l` → `0`，并**追加**交叉核对 `git status --porcelain web/src`（因 `git diff HEAD` 不含未跟踪文件，见 §8 U-6）。
- 禁止：不改 `AlertBanner.vue` / `EmptyState.vue` / `componentTypes.ts` / `pages/**` / `features/**` / `composables/**` / `styles/**` / `web/*.config.*` / `package*.json`；不新增设计外分支（六态之外无第七态）；不写死色值（只用 `var(--cl-*)`）；不在 `state/` 内出现 problem code 字面量（F-B）；不 `npm install`。

### S4 截图与证据采集（`qwen3.8-flash` / 2k）

- 输入：本文 §1.3 呈现要素、§6 验收衔接口径；S3 产物；既有截图口径参照 `web/tests/e2e/ui-01-screenshots.spec.ts`（36 行）。
- 产出：`evidence/M0/M0-03b/commands.md`（每条命令原文 + rc + 末行）、`evidence/M0/M0-03b/ac.md`、`evidence/M0/M0-03b/state/*.png`（1440x900 与 1024x768 各一组，六态 × 2 视口，**文件名纯 ASCII**，如 `state-failed-1024x768.png`）、`evidence/M0/summaries/M0-03b.md`（<= 30 行）。
- 门禁：`commands.md` 内逐条 rc=0；越界自证同 S3；截图字节数非 0。
- 阻塞与禁止：**U-2 未裁定前 S4 无法开工**（六态 harness 的 e2e 落点不在 `scope_allow`）。Playwright 不可用时**不得谎称 E2E 通过**，记 `PASS_WITH_TODO` 并关联 `BLK-01`（卡 `禁止` 段）。

## 8. 诚实偏差与未决问题（交编排器裁定，实现方不得自行决定）

- **U-1**：`AlertBanner.vue` / `EmptyState.vue` 是否需要**物理迁入** `web/src/components/state/`？迁入必然改 `web/src/pages/**` 的 import 路径（实测 `WorkspacePage.vue:9-10`），而 `pages/**` 在本卡 `scope_deny` 内。本文件按 **F-2「不迁移、原址冻结、`state/` 内组合复用」** 裁定；若编排器要求迁移，须同时放开 `pages/**` 并作独立 CR。
- **U-2**：`web/tests/e2e/**` 未列入本卡 `scope_allow`，但 S4 的六态截图需要一个能渲染六态的 harness（页面不在本卡 scope，无法直接截 UI-01）。请裁定：(a) 扩 `scope_allow` 加 `web/tests/e2e/state/**`；(b) 指定其他 harness 落点；(c) 把 S4 截图推迟到首个消费 `ViewState` 的页面任务。**在裁定前 S4 不具备可执行输入**。
- **U-3**：数字单位换算（`:36` 后半句）本次**不纳入冻结面**（F-E）。若编排器希望提前抽公共件，请指定落点（`web/src/features/shared/` 在本卡 `scope_deny` 内，`state/` 内新建会与 M1-04 / M3-04 重复）。
- **U-4**：`partial-comparable` / `pending-fill` 的**服务器数据源尚未在活契约中落地**（可比性条 `StatusBand` 属 UI-10，首次交付 M2-04）。本卡只冻结**呈现契约**，两态的触发值由页面显式传入、桩数据内联在测试；请确认这一口径，或把两态的实现推迟到 M2-04（则 S2 的矩阵对这两态只断言呈现、不断言数据来源）。
- **U-5**：卡内 U-2 已提出 `state.json` 的 `tasks["M0-03b"].scope` 只有 2 项，未含冻结登记文件与证据落点。本文件已按卡 `scope_allow` 产出，**请编排器同步 `state.json`**（本 lane 无权改）。
- **U-6**：越界自证 gate 用 `git diff --name-only HEAD`，**对未跟踪的新文件不敏感**（新增越界文件不会出现在 diff 里）。建议编排器把口径补成 `git diff --name-only HEAD -- web/src` + `git status --porcelain web/src` 双检；本文件基线值：两者皆为 0 / 空。〔**R10 收口**：本建议已采纳并两次演进——A139 立「双检」，A144 进一步收紧为「三段式」（写权外 tracked 修改 0 / 写权内 numstat `deleted==0` / 写权外未跟踪新文件 0），已写进 `resume.dispatch_requirements` 第 8 与第 12 条，**U-6 关闭**。〕
- **U-7**：`M0-03-public-components.md` §7 登记的 D1（`ConfirmDialog` 打开时未主动聚焦，Esc 依赖焦点已在框内）与 D3（`DataTable` 缺 36px 密集档与宽表冻结首列）**都不能在 M0-03b 期间修**（越界）。请裁定走独立 CR 还是并入 M0-03 收尾。
- **偏差自报（本 S1 轮）**：抽取阶段踩到 PowerShell 引号陷阱两次——(1) `bash -lc` 内层双引号被 PS 剥除，导致 `<slot` / `<AlertBanner` 的 `<` 被 bash 当重定向（实测 `bash: line 1: AlertBanner|: No such file or directory`）；(2) 内层 `#` 未加引号时被 bash 当行注释，吞掉整条命令的剩余部分（实测 `grep` 只收到 `-nE` 而报 usage）。修法：一律改走 `python3 /mnt/d/ws/codex_rd/ss_campaignlab/.orch_tmp/laneF_freeze/*.py` 通道，rc 由 `subprocess.run(...).returncode` 采集，不使用 `\$?`。写入用 `open(..., "w", encoding="utf-8", newline="\n")` 等价路径（`pathlib.Path.write_text`），写后回读断言：无 BOM、无 `\r`、以 `\n` 结尾。
- **刻意没做的事**：没有创建 `web/src/components/state/**` 任何文件；没有改 `AlertBanner.vue` / `EmptyState.vue`；没有跑全仓 `pytest` / `mypy` / `ruff .` / `doctor` / `verify` / `npm run build`（另有 3 条 lane 同树在飞，只跑路径限定门禁）；没有执行任何 git 写操作；没有把 AC-032 写成本卡 gate；没有在文档里写死任何六位十六进制色值。
## 9. R10 编排器裁定：S2+S3 回收时的 7 项终裁（A145–A151）

> 来源：lane F（Mencius，`qwen3.8-flash`）交付 M0-03b/S2+S3 时上报 7 项「需编排器裁定」，均在冻结面内取了唯一可行解、未自行扩 scope。编排器**不采信自报**，逐项独立复验后裁定如下。全部 7 项的实现**均已验收**，本章只补口径与文书，**不要求任何返工**。

| # | 争议 | 裁定 | 依据（编排器实测） |
|---|---|---|---|
| ① | §4.2 R-1 禁 `state/` import `features/**`，而 §1.2/F-B 要求 `stateFromError()` 消费 `presentationOf()`（住在 `features/shared/`） | **A145**：给 R-1 加**唯一豁免**（`features/shared/problemPresentation`） | `viewState.ts:19` 恰 1 条依赖边；`AlertBanner.vue:3` 同边已在先；`state/` 内 `features` 命中总数 = 1 |
| ② | A137「公共件无数据获取副作用」的字面 vs `ApiError` 只能 `import type` | **A146**：判据 = **运行期模块边**，非字面文本。`import type` 在 `verbatimModuleSyntax` 下整条擦除 → 0 运行期边 → 合规。**禁**为凑字面零引用而新增 `ApiError` 结构镜像类型（两处定义必分叉，那才是真契约漂移） | `@/api/` 命中 3 = 注释 1 + `import type` 2（`viewState.ts:18`、`ViewState.vue:28`）；`fetch(`/`axios`/`XMLHttpRequest` 非注释命中 **0** |
| ③ | dev 水槽三导出 + `data-dev-assert` 是否须走 CR | **A147**：**均不需 CR**。`data-dev-assert` 是 DOM data 属性，不改 props/emits/slots，不构成 §5:281 的签名变更；dev 水槽是 `viewState.ts` 的模块级导出但 **barrel 未 re-export**（§3.1:113 的「新增导出须走 CR」条件未触发），公共 API 面零扩张 | `index.ts` 全文 17 行只导出 `viewState`/`registry`/三组件的冻结面；水槽消费者仅 `registry.ts:14`、`ViewState.vue:35`、`registry.spec.ts:19`（按模块路径） |
| ④ | §3.4 `context` 默认「由当前路由推导」不可满足 | **A148**：**A137 优先**。未传即三字段 null（F-A 组件不猜）；§3.4 该行已更正；**M3-P02 接入必须显式传 `context`**（立 FU-27，trigger = M3-P02 派单前） | `from 'vue-router'` / `useRoute` / `import(` / `require(` 四项 ERE 守卫在 `state/`+`tests/unit/state/` 上均 **rc=1、0 命中**；`vue-router` 字样仅 1 处注释（`ViewState.vue:22`），非依赖边（**R10-5**：原先引的「命中 0」是 BRE 假绿，已更正） |
| ⑤ | `FirstLoadSkeleton` 的 `heading/headCells/cardCount` 不在 `ViewState` 冻结 props 内，是否 append `skeleton` props | **A149**：**不 append、不扩冻结面、不走 CR**。骨架形状属**页面级差异知识**，放进公共件会让 `ViewState` 承载页面语义（违 F-A）；`variant.render` 已是既有扩展点，足以承载。页面可**直接用 `FirstLoadSkeleton`** 或经 `variant.render` 注入（立 FU-28，写进 M1-04/M2-04/M3-04/M4-03 页面卡） | `ViewState` props 面与 §3.4 冻结表逐字一致，未被扩 |
| ⑥ | §1.3「每态唯一标题」与 §3.3「partial/pending 共用 `COMMON.md:30` 首句」冲突；动作名文案来源不足 | **A150**：**§3.3 逐字文案优先**（硬约束），§1.3 降为「每态唯一**可判定标识**」；动作名与「上一结果」一律取 `ui/COMMON.md` :28/:29/:30/:32 原文子串并逐字校验（含正/负例自证）——**采纳** | `viewStateCopy.spec.ts` 54 例全绿（编排器复跑 rc=0）；`state/` 内 `@media`/`data-narrow`/`matchMedia` 命中 0 |
| ⑦ | `stateMatrix.ts` 超出 §7 所列 5 个 spec 名 | **A151**：**追认**。R-4 要求矩阵工厂化，工厂必须有非 spec 落点（.spec 互 import 会重复注册用例）；它是 helper，§7 的 spec 数量与命名约束未被突破。§7 S2 产出段已 append-only 追记 | `describe(`/`it(`/`expect(` 在 `stateMatrix.ts` 内命中 **0**；唯一 `test(` 命中是正则 `/\d/.test(text)`，非用例注册 |

### 9.1 编排器独立复验结论（不采信自报，全部亲自重跑）

- **交付面**：`web/src/components/state/` 6 件 + `web/tests/unit/state/` 6 件 = **12 件**，逐件行数与自报**全等**（258/129/87/54/62/17 与 281/183/168/88/78/405），全部无 BOM、无 CR、有尾换行；`state/` 内**无第 7 个文件**（§5:285 的 CR 条件未触发）。
- **越界自证（A144 三段式）**：(a) `git diff --name-only HEAD` **全仓为空**（写权外 tracked 修改 0，且写权内也为 0 —— 本卡全为新建文件）；(b) 无 tracked 修改故 numstat 无行，`deleted==0` 平凡成立；(c) `git status --porcelain web` 12 行**全部**落在 `web/src/components/state/` 与 `web/tests/unit/state/` 内，写权外未跟踪新文件 **0**。
- **前端四门禁（cwd=`/home/szf/dev/CampaignLab/web`，编排器亲自重跑）**：`npm run test -- tests/unit/state` rc=0 → **5 files / 173 tests passed**；`npm run test` rc=0 → **12 files / 277 tests passed**；`npm run typecheck`（`vue-tsc --noEmit`）rc=0；`npm run lint`（`eslint .`）rc=0；`npm run build` rc=0 → `dist/assets/index-*.css 377.54 kB`、`✓ built in 511ms`。与自报逐项一致。
- **既有守卫未被新 CSS 触发**：`breakpoint-guard` 扫描 38 文件、`web/src` 内 `@media` 断点 6 条全部落在 `AppShell.vue:31/36`、`EvidenceDrawer.vue:50`、`PageGrid.vue:15`、`SideRail.vue:24/30`（**均在 `state/` 外**），违规条数 **0**；`tokens-guard` 11 例全绿（`state/` 内零色值字面量）。
- **守卫口径自我更正（R10-5）**：编排器首轮复验时对 `vue-router|useRoute` 与 `features` 两条守卫误用 **BRE**（`grep -rn` 未加 `-E`），BRE 下 `|` 是**字面量**而非交替，导致「有匹配」被误报成 `rc=1 无匹配`的**假绿**（这是 R9-4「`-` 开头模式被当选项 → rc=2 假红」的镜像陷阱）。已改 `-E` 重跑并逐条更正结论；两条守卫的**实质结论不变**（`@/features` 依赖边确为 1 条、路由依赖确为 0 条），但引用证据已换成正确的 ERE 命令与命中数。固化规则 `rule_grep_alternation_requires_ERE`。
- **ruff / mypy 不适用**：本卡产物为 TS/Vue，`pyproject.toml:51` 的 `extend-exclude` 含 `web`、`:68` 的 mypy `exclude` 含 `web/`，不在 Python 作用域；`in_scope_py` 恒 75。

### 9.2 本轮成本教训（如实入账，不粉饰）

Mencius 自报 token ≈ **3.8e5**，而派单预算仅 **5k** → 越限 **76×**，是本仓最严重的单条越限（前值：Dirac 181k=3.02×、Bohr 65k=5.42×）。根因**不是档位选错，而是编排器派单设计错**：

1. 该卡表面是「S2 用例展开 + S3 件内样板」（看似量产型 → 按 §6.3 派 flash），实质要在 **331 行冻结文档 + 303 行组件契约表 + `ui/COMMON.md` 逐字文案 + 13 件既有公共组件**之间做**跨文档一致性判定**，并处理 7 处冻结面内部冲突 —— 按 §6.3「跨模块一致性」与「公共冻结件」两条硬规则，**本应派 max**。
2. 5k 的预算是按「产出份数」估的，不是按「被判定面行数」估的（与 Epicurus 的 33k 教训同源，见 A143 `cost_lesson`）。331+303 行的冻结面逐条对码本身就远超 5k。
3. 7 处冲突意味着必然多轮 loop（实测 `loop_used=3`，含一次「模板重排误删动作区→补回并全文校验」的返工），每轮都要重读冻结面。

**纠正措施（记 R10-4）**：① 凡卡文含「冻结文档 / 公共件契约表 / 逐字文案对齐」输入者，一律按 §6.3 判 **max**，禁因「动作看似量产」而降档；② flash 预算一律按「被判定面行数 × 每行单价 + loop 轮数」估，禁按产出份数估；③ 派单前先做一次**冲突面预扫**（本卡的 7 处冲突全部可在派单前由编排器扫出），冲突 ≥3 处即升档或拆卡。
