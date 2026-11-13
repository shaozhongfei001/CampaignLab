# 03 · M0-03b 六态冻结登记 vs `web/src/components/state/**` 代码复核

- 冻结文档（只读）：`orchestrator/handoff/M0-03b-freeze.md`（331 行），`F:n` = 该文档第 n 行
- 代码面（只读）：`web/src/components/state/**`
- 口径来源：`spec/CampaignLab-SDD-v1.0/ui/COMMON.md`（`C:n` = 该文件第 n 行）

## 1. 首要实测事实：`state/` 目录不存在，六态件 0 行代码落地

| 检验 | 实测命令 | 实测输出（rc 均为 0） |
|---|---|---|
| 目录存在性 | `test -e web/src/components/state && echo STATE_DIR_EXISTS \|\| echo STATE_DIR_ABSENT` | `STATE_DIR_ABSENT` |
| 子目录计数 | `ls -d web/src/components/*/ \| wc -l` | `0`（`ls web/src/components \| grep -c .` = `13`，即 12 个 `.vue` + `componentTypes.ts`，无子目录） |
| 符号落地 | `grep -rn 'ViewState' web/src --include=*.vue --include=*.ts` | 空（全域 0 命中，含 `ViewStateKind` / `ViewState.vue` / `viewState.ts`） |

**该状态与冻结文档自身的声明一致，不构成文档-代码矛盾**：
- `F:115` 标题即写「S3 的目标文件清单（`web/src/components/state/**`，实测当前不存在）」；`F:117` 复跑记录 `STATE_DIR_ABSENT`；`F:119` 列出 6 个只允许新建的文件名。
- `F:108-113` 把第 5-10 项标为「**本卡新冻结**（S3 落地）」；`F:331`「刻意没做的事：没有创建 `web/src/components/state/**` 任何文件」。
- 结论：M0-03b 的 S1 交付物是**冻结登记**（类型签名级），S3 实现未派单/未落地。契约表侧亦同口径（`M0-03-public-components.md:20` C5）。

## 2. 六态逐条对照（态名 / 触发条件 / props 入参 / 取数副作用）

| 态名（冻结字面量） | 文档登记的触发条件 | 文档登记的 props 入参 | 代码实测 | 对应 | 证据 |
|---|---|---|---|---|---|
| 首载 `first-load` | `F:45`：store `phase` ∈ `idle`/`loading`（`web/src/composables/useWorkspaces.ts:32`）或 `unknown`/`checking`/`exchanging`（`web/src/composables/useSession.ts:26`）且 `error === null`；呈现 `F:62` 骨架 + `role="status"` + `aria-live` + `aria-busy` | `state`（必填，`F:176`）；`FirstLoadSkeleton` 的 `heading?` / `headCells?` / `cardCount?`（`F:207`） | NOT_FOUND（`state/` 不存在） | 无法对码；文档内部自洽（枚举 `F:127` 与 §1.2 `F:45` 字面量一致）；触发条件引用的两个 composable 行号已独立复验为真：`web/src/composables/useWorkspaces.ts:32`（`WorkspacesPhase = idle/loading/ready/empty/failed`）、`web/src/composables/useSession.ts:26`（`SessionPhase` 含 `unknown/checking/exchanging`） | `F:45`、`F:62`、`F:127`；代码侧 `web/src/components/state/**` = 0 文件 |
| 无记录 `no-record` | `F:46`：`phase === "empty"`（由 `useWorkspaces.ts:139` 依 `items.length === 0` 判定，实测该行即 `state.phase = state.items.length === 0 ? "empty" : "ready";`）；`F:63` `role="status"`，动作键 `create` / `clear-filter` | `state`、`title?`、`hint?`、`actions?`（`F:176-180`） | NOT_FOUND | 同上；注意该态与现存 `EmptyState.vue`（契约表 §2.7）是**组合复用**关系而非替换（`F:89-97` 裁定「组合而非改写」） | `F:46`、`F:63`、`F:128`、`F:176-180` |
| 失败 `failed` | `F:47`：`error !== null` 且 `error.status !== 412` 且 `presentationOf(error).bucket !== "CONFLICT"`；`F:64` 服务端 `title`/`detail`/`request_id` 原样渲染 | `state`、`error?`（`failed`/`stale-412` 时须非 null，`F:177`）、`title?`、`hint?`、`actions?`、`context?` | NOT_FOUND | 文档对既有件的引用经复验为真：`AlertBanner.vue:10`（`showServerTitle ? error.title : "请求未完成"`）、`AlertBanner.vue:21`（`request_id`）、`AlertBanner.vue:9`（`role="alert"`）逐条与 `F:64` 吻合 | `F:47`、`F:64`、`F:129`、`F:177`；`web/src/components/AlertBanner.vue:9`、`:10`、`:21` |
| 部分可比 `partial-comparable` | `F:48`：成功响应且结果被标记为只按共同子集可比（标记由结果载荷提供，见 `F:326` U-4）；**不是错误态** | 同上；动作键 `export`（`F:65`） | NOT_FOUND | 文档自认该态的**服务器数据源尚未在活契约落地**（`F:326` U-4），故「无代码」是有意的；不得由前端发明触发语义 | `F:48`、`F:65`、`F:130`、`F:326` |
| 待补 `pending-fill` | `F:49`：成功响应且存在缺项（`missing` 非空），差值留空；**不是错误态**；`F:66` 缺值 `—` + 原因 | 同上；`MissingValue` 的 `value`（必填）/ `reason?` / `mono?`（`F:208`） | NOT_FOUND | 与 `F:78` 裁定 F-E 一致：本次不纳入数字单位换算（实测 `web/src/features/shared/` 只有 `navigation.ts` 与 `problemPresentation.ts`，无格式化件 → 声明为真） | `F:49`、`F:66`、`F:131`、`F:208`、`F:78` |
| 412 过期 `stale-412` | `F:50`：`error !== null` 且（`error.status === 412` 或 `presentationOf(error).bucket === "CONFLICT"`）；`F:67` `role="alert"` + 新旧版本串 | 同上；动作键 `refetch` / `rerun`（`F:67`） | NOT_FOUND | 判定链只用 `presentationOf()` 返回 + `error.status`，与 `F:55` 裁定 F-B「禁新增 code 白名单」一致；`web/src/features/shared/problemPresentation.ts` 实测存在且未被要求改动 | `F:50`、`F:67`、`F:132`、`F:55` |

**边界声明复核**：`F:56` 裁定 F-C「排队或计算」不在六态内、归 `JobProgress`（`C:29`）—— 实测 `grep -rn 'JobProgress' web/src` → **0 命中**，即该件亦未落地（首次交付 M0-04）。这不影响六态件的一致性判定，但意味着 `C:29` 场景当前在代码里**完全无载体**，登记为 OBS-1（见 §4）。

## 3. 硬口径核验：「公共件必须无数据获取副作用（组件内禁调 api，触发值由页面 props 传入）」

| 检验 | 命令/方法 | 实测结果 | 判定 |
|---|---|---|---|
| 网络调用 | `grep -rn 'fetch(\|axios\|http\.\|await \|new XMLHttpRequest' web/src/components` | 空（0 命中） | **PASS** |
| `@/api/**` 依赖性质 | `grep -rn 'from "@/api' web/src/components` | 仅 4 行且**全部是 `import type`**：`AlertBanner.vue:2`（`ApiError`）、`AppBar.vue:3`、`AppBar.vue:4`（`Health`/`Session`）、`AppShell.vue:4`、`AppShell.vue:5` | **PASS**（类型导入编译期擦除，无运行期依赖，不发请求） |
| 运行期 import 全量 | `grep -rn 'import ' web/src/components \| grep -v 'import type'` | 仅 5 条：`EvidenceDrawer.vue:2`（vue 生命周期 `onBeforeUpdate`/`onUpdated`/`ref`）、`AlertBanner.vue:3`（`presentationOf`）、`AppShell.vue:2`、`AppShell.vue:3`、`AppBar.vue:2`（子组件） | **PASS**（无 store、无 api、无副作用模块） |
| 触发值来源 | 现存件 props 全部由页面传入：`web/src/pages/workspace/WorkspacePage.vue:137`（`AppShell` 三项）、`:162`（`DataTable` 列/行/排序）、`:205`（`EvidenceDrawer` `:open="evidenceOpen"`）、`:215` 起（`ConfirmDialog`） | **PASS** | **PASS** |
| DOM 副作用边界 | `EvidenceDrawer.vue:10-25` 读写 `document.activeElement`（`:23`）与 `focus()`（`:13`、`:17`） | 属**焦点管理**，非数据获取；符合 `C:38`「抽屉 Esc 可关闭并返回触发焦点」 | **PASS（登记说明）** |
| 呈现分类纯函数 | `AlertBanner.vue:3` 引入 `presentationOf`（函数 `web/src/features/shared/problemPresentation.ts:55-65`，返回类型 `Presentation` 见 `:47`），入参为 props `error`（`AlertBanner.vue:6`、消费于 `:9`、`:10`、`:12`） | 无网络、无 store；该文件在 M0-03b `scope_deny` 内（只读） | **PASS（登记说明）** |
| 冻结签名层面的同一条口径 | `F:124`（`viewState.ts` 草案只 `import type { ApiError }`）、`F:54` 裁定 F-A「`state` 是必填 prop，由页面 / composable 决定，组件不猜」、`F:191`（`ViewState.vue` 的 `action` emit「**不自行导航**，由页面接线」） | 文档已把「无取数副作用」写成硬约束 | **PASS（文档侧亦满足）** |

## 4. 观察项（不裁定，交编排器）

- **OBS-1**：`C:29`「排队或计算」态与 `C:30`「部分可比 / 待补」的服务器字段均未在代码/活契约落地（`F:326` U-4），六态件中两态目前只能是「纯呈现契约 + 测试内联桩数据」。
- **OBS-2**：`F:324` U-2 明确 S4 六态截图在编排器裁定前**不具备可执行输入**；`F:323` U-1 的「不迁移、原址冻结」与 `M0-03-public-components.md:H:117` 同口径，本次复核无异议。
- **OBS-3**：`F:328` U-6 指出 `git diff --name-only HEAD` 对未跟踪新文件不敏感，建议双检 —— 本 lane 已按双检执行（见 `commands.md` 末尾两条），结果 0 / 0（排除本 lane 自身目录后）。
- **OBS-4**：`F:207` 要求骨架「保留导航」= 只放进 `AppShell` 默认槽（`AppShell.vue:14`），实测 `AppShell.vue:11` 的 `<SideRail />` 与之兼容，但 `AppShell` 目前不透传 `drawer`（D-034 #4，见 02 报告），故 S3 落地时「窄屏抽屉态下的骨架呈现」仍需先补 #4 才能成立 —— 记为**依赖关系**，不是矛盾。

## 5. 结论行

RESULT: 六态冻结登记逐条复核完毕 / 与代码对应 0 条 / 文档内部自洽 6 条 / NOT_FOUND 6 件（`state/` 目录实测不存在，与 `F:115`、`F:117`、`F:331` 声明一致）/ 无取数副作用口径核验 PASS（现存 13 件 0 处网络调用，`@/api` 仅类型导入）
