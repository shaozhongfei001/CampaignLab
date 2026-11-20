# FE-UI-02 活动列表 · 交付与走查记录（前端分支会话）

- 分支：`frontend/ui-pages`（独立 worktree `/home/szf/dev/CampaignLab-fe`，主树未动）
- 基线 HEAD：`0cccb76`（m0-framework）；本批在其上追加提交
- 日期：2026-11-20（Asia/Shanghai）
- 页面契约：`contracts/pages.json` UI-02（route `/w/:workspace_id/activities`；operation_ids `listActivities / getActivity / createActivity`；acceptance `AC-002 / AC-032`）
- 页面规范：`spec/CampaignLab-SDD-v1.0/ui/UI-02-activity-list.md`；公共规范 `ui/COMMON.md`
- 证据：截图 `evidence/FE/ui/ui-02/`（32 张，纯 ASCII，1440×900 与 1024×768 各 16 张）；命令留痕见 `web/docs/FE-UI-02-commands.md`

## 1. 交付清单与写权限归类

| 路径 | 归类 | 说明 |
|---|---|---|
| `web/src/pages/activity/ActivityListPage.vue` | 自由写 | UI-02 主页面（六态映射、筛选、新建、详情抽屉、证据抽屉） |
| `web/src/pages/activity/ActivityFirstLoad.vue` | 自由写 | 首载骨架的 variant 呈现件（§4.2 外部注册扩展点） |
| `web/src/pages/activity/firstLoadVariant.ts` | 自由写 | variant 注册（R-5：注册只发生在调用方模块） |
| `web/src/features/activity/{query,sort,presentation,viewState}.ts` | 自由写 | 过滤清理 / 表头排序 / 显示层 / 页面态→六态映射 |
| `web/src/composables/useActivities.ts` | 自由写 | 工作区作用域 store（epoch 清场、409 定位、请求缓存） |
| `web/src/api/endpoints.ts` | 自由写（追加） | `listActivities / getActivity / createActivity` 类型化封装 |
| `web/src/router/index.ts` | 自由写（按契约追加） | 新增 `activity-list` 路由；旧 `/workspaces/:workspaceId` 重定向（B 方案暂定，见请求 [1]/[3]） |
| `web/tests/unit/activity/*.spec.ts` | 自由写 | 7 个单测文件 + fixtures（含 route/class/presentation/sort/query/store/viewState） |
| `web/tests/e2e/activity/{gates,stubActivityApi,ui-02-activity-list.spec}.ts` | 自由写 | 机器门禁实现、合成夹具、出口用例 |
| `web/docs/**`（本文件等 3 件） | 自由写（`web/**` 不在主线 counts 分母） | 交付记录 / 26 页走查矩阵 / 命令留痕 |
| `web/src/components/**`、`web/src/components/state/**` | **冻结，零改动** | 只消费既有 props/emits/slots；`git diff` 可证 |
| `web/src/main.ts`、`web/src/api/http.ts`、`web/*.config.*`、`web/package*.json` | **需 CR，未改** | 见 FE-TO-DAG-REQUESTS.md 请求 [4] |

## 2. 六态可达性（诚实边界，禁伪造）

| 六态 | UI-02 可达性 | 触发与呈现 |
|---|---|---|
| first-load | 可达 | 首屏无上次结果；经 variant 覆写呈现六列骨架，`data-state/role/aria-live/aria-busy` 四载体齐全 |
| no-record | 可达 | 筛选后 0 行；标题由页面 `title` prop 覆盖为「当前筛选没有活动：…」，动作键按有无筛选给 `create` / `create+clear-filter` |
| failed | 可达 | 非 412/CONFLICT 的失败；`role=alert` + AlertBanner（code / HTTP / request_id 可见）+ `refetch` |
| stale-412 | 可达 | 412 或 CONFLICT 分桶；`data-keep-input=true`，本地筛选输入保留 |
| partial-comparable | **不可达** | 契约无基准窗口/共同子集语义；`viewState.ts` 的 `UNREACHABLE_VIEW_STATES` 钉成机器断言 |
| pending-fill | **不可达** | 同上；单元格缺值一律走 MissingValue（— + 原因），不冒充页面级六态 |

排队或计算（COMMON.md:29）不属六态：本页「上一结果」标识在刷新期间由 `showsPreviousResult` 给出，旧行保留不清空。

## 3. 冻结件消费面（零改动，只消费）

AppShell、PageBar、CardPanel、DataTable、AlertBanner、EvidenceDrawer、ConfirmDialog、StatusTag、
state/ViewState、state/FirstLoadSkeleton、state/MissingValue、state/registry（外部注册扩展点）。

消费纪律留痕：
- 首载骨架形状经 `registry.registerViewStateVariant({ render })` 覆写（FU-28：禁给 ViewState 扩 props；
  绕开 ViewState 直渲骨架会丢 `data-state/role/aria-live/aria-busy` 四载体）。variant 组件**逐一声明**
  ViewState 的 9 个 overrideProps 键，防 Vue 属性回退把 error 对象写成 `[object Object]`（机器门禁第 2 条）；
  该约束由 `tests/unit/activity/firstLoadVariant.spec.ts` 钉死（含负对照）。
- ViewState 的 `context` 由页面显式传入（FU-27：公共件禁读路由）。
- 六态文案一律取冻结件 `copyOf`；页面只覆盖 no-record 的 `title`（COMMON.md:28 要求指明当前筛选）。

## 4. 诚实偏差与待办（不降档、不掩盖）

1. **UI-03 未交付** ⇒「行点击进入活动详情」由本页 EvidenceDrawer 承载，数据一律 `getActivity` 原值，不发假路由；
   页面脚注与抽屉内均有可见说明（「UI-03 详情页未交付」）。
2. **SideRail「入口」rail 项恒不渲染**（冻结面缺陷，非本批引入）：`SideRail.vue` 的
   `entryActive?: boolean` 未给显式默认值，Vue 对可选 Boolean prop 的隐式转换使缺省值为 `false`，
   于是 `v-if="props.entryActive !== false"` 恒假；M0-03 的 UI-01 证据截图同样无该项（可对照
   `evidence/M0/ui/ui-01-desktop-1440x900.png`）。回入口的合法路径目前只有 404 页「返回入口」与浏览器回退。
   属冻结面 ⇒ 已登记 CR 请求 [4]，本批不改。
3. **SideRail 六项导航仍是 `aria-disabled` 占位**（激活导航需改公共件）⇒ CR 请求 [4]。
4. **G6 实测出两条未定义 class**（冻结件 `AppBar.vue:16/17` 的 `cl-appbar__actor` / `cl-appbar__recent`，
   全仓无样式定义）。处置：`tests/e2e/activity/gates.ts` 的 `KNOWN_FROZEN_CLASS_GAPS` 穷举白名单 +
   `classGapDrift()` 双向校验（新增未定义 class 判红；白名单条目失效也判红）+ CR 请求 [4]。
5. **路由前缀口径**：按 B 方案暂定（契约路由为主 + 旧路径重定向），待主线裁定（请求 [1]/[3]）。
6. **UI-06 阻塞 FE-BLK-01**：`web/src/api/http.ts:414-416` 正文恒为 JSON，无法发 `multipart/form-data`
   （`createImport` 契约要求）⇒ 未实现 UI-06，CR 请求 [4]。
7. **`main.ts` 未 provide `activitiesStoreKey`**：页面直接取 `useActivities()` 单例，功能不受影响；
   与其余三个 store 的接线口径对齐需改 `main.ts` ⇒ CR 请求 [4]。
8. 1024×768 下折叠 rail 的六项文案换行为两行（`--cl-rail-w-collapsed=64px`），可读但偏挤；
   属冻结件 SideRail 的呈现，登记观察项，未改。

## 5. 机器门禁结果（ADR-003 A 段 7 条）

实现：`web/tests/e2e/activity/gates.ts`（浏览器侧 6 条）+ `web/tests/unit/activity/class-contract.spec.ts`（第 6/7 条的源码侧）。
判据结构性；每条门禁配**注入式负对照**（`seedGateViolation` / `clearGateSeeds`），植入违规必判红、摘除后必归零。

| # | 门禁 | 结果 | 说明 |
|---|---|---|---|
| 1 | 0 个 console.error / pageerror | PASS | 应用侧恒 0；浏览器对 ≥400 响应的网络层噪声与应用日志分开统计，并与用例**故意触发**的状态码双向对账（多一个少一个都判红） |
| 2 | 文本与属性无 NaN/undefined/[object Object]/Infinity | PASS | 词边界匹配；文本节点与全部属性（含 SVG）逐一扫 |
| 3 | 标签配对 + 嵌套不变量 | PASS | 开合计数逐标签相等；td/th/tr/li/dt/dd/caption 的父元素不变量（能抓住 DOM API 造出的错嵌套） |
| 4 | 无横向溢出 | PASS | 文档不横向滚动；未被滚动/裁剪祖先收容的元素不得越出视口；内容溢出者必须自身可滚动（表格滚动容器） |
| 5 | 无 0 宽/0 高图表容器 | N/A（checked=0） | UI-02 无图表；如实报 0 而非「通过」 |
| 6 | 用到的 class 都有定义 | PASS_WITH_TODO | 页面自身 0 未定义；冻结件 AppBar 两条登记白名单 + CR（见偏差 4） |
| 7 | 禁「行尾 + 接行首 +」 | PASS | 源码扫描覆盖 `pages/activity/**`、`features/activity/**`、`composables/useActivities.ts` |

## 6. 视觉走查（人眼 + 截图）

- 前置：`fc-list | grep -c "Noto Sans CJK SC"` = 2（Regular/Bold 均在），截图可作视觉结论。
- 1440×900：六列全宽表、缺值「— + 原因」、状态词「开放/已归档」+ 契约枚举原文（`data-status`）、
  合成芯片「合成数据」可见；详情抽屉 480px、确认框 520px（冻结语义常量，断言留痕）。
- 1024×768：rail 折叠 64px、表格无横向溢出（六列仍完整可读）；折叠态六项文案换行两行（观察项，见偏差 8）。
- 不靠颜色区分（AC-032）：状态区分载体 = `data-status` 枚举原文 + 中文状态词；实测 StatusTag 五 tone
  形状完全相同（D-034③，冻结面），故颜色/形状均不作区分依据，用例对二者都做了断言留痕。

## 7. 测试与用例数

- vitest：19 文件/368 用例 → **20 文件/380 用例**（只增不减；新增 `firstLoadVariant.spec.ts` 12 例）。
- Playwright：`tests/e2e/activity/ui-02-activity-list.spec.ts` 17 用例 × 2 视口 = 34 通过，0 失败。
- 三门（lint / typecheck / test）rc=0；`npm --prefix web run build` rc=0。