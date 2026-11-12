> **编排器修改标注（2026-11-13T01:54:49+08:00，依 D-011）**：本文中 4 处把「页面侧深链」标为 AC-034 的表述已由编排器更正为
> 引用 `spec/CampaignLab-SDD-v1.0/framework/FRONTEND.md:12`；AC-034 的 HTTP 负例本体归 M0-02。
> 修改者为编排器，**非 S1/S2 原作者（Ohm）**；其余内容未改动。

>
> **编排器追注（2026-11-13T02:17:03+08:00，依 CR-002 / ADR-006 / D-013）**：下文 **PRE-3 门禁自证**
> （`bytes=443552`、sha256 `01bd28f0…`、`source.openapi.sha16=01bd28f0772f506e`）是 S1/S2 于 HEAD=`f12dcf8`
> 时点的**历史测量，原值不改写**，但**已作废、不得再作为期望值复跑**：CR-002 选项 B 已移除 `listWorkspaces.status`，
> 活契约现值 `592571099d638251` / `443309 B`（权威来源
> `orchestrator/state.json → resume.self_check_gates_rc0.counts.live_openapi_sha16` / `.live_openapi_bytes`，禁写死）。
> 切片已重切，**S3/S4 必须以重切后的 `orchestrator/handoff/M0-03.slice.json` 为准**。
> 另：§8 **Q7** 的临时处置已由「临时」转「终态」，详见 §8 表后的编排器追注块；
> §9 自检中的 ruff 分母（54 files）亦已漂移，权威值见 `counts.ruff_formatted_files`。

# M0-03 设计 · S1 工程骨架与严格基线 + S2 令牌体系

lane F · tier `qwen3.8-max` · 子任务 S1（工程骨架与严格模式基线）+ S2（令牌体系设计）。依据（全部只读）：`orchestrator/tasks/M0-03.md`（含 PRE-3 门禁与文末加注）、`docs/design/token-mapping.md`（唯一令牌真值）、`docs/design/page-component-map.md` §1、`docs/decisions/ADR-003`、`docs/decisions/ADR-005`、`ui/COMMON.md`、`framework/FRONTEND.md`、`orchestrator/handoff/M0-03.slice.json`、`docs/design/frontend-pitfalls.md`。

**PRE-3 门禁自证（实算，不采信派单文本）**：`contracts/openapi.json` bytes=443552、sha256=`01bd28f0772f506e15fb70f07a37479ab9c33c4a3c9a39651445e6fa435cf583`、sha16=`01bd28f0772f506e`、`info.version=1.0.1`；`M0-03.slice.json` 的 `spec_version=1.0.1`、`source.openapi.sha16=01bd28f0772f506e`、`bytes=443552` → 三项逐字一致，**PASS**。切片 5 op = exchangeSession / getSession / getHealth / listWorkspaces / createWorkspace；pages = UI-01（route `/`，FR-01，AC-001；页面侧深链依据 `framework/FRONTEND.md:12`，**非** AC-034，见 D-011）。

## 1. S1 已落地（实测结论，非计划）

| 文件 | 关键决定 | 实测 |
|---|---|---|
| `web/tsconfig.json` | `strict` 之外补 `noUncheckedIndexedAccess`、`exactOptionalPropertyTypes`、`noImplicitOverride`、`noFallthroughCasesInSwitch`、`noImplicitReturns`、`noImplicitThis`、`noUnusedLocals`、`noUnusedParameters`、`allowUnreachableCode:false`、`allowUnusedLabels:false`、`forceConsistentCasingInFileNames`、`useDefineForClassFields`、`allowImportingTsExtensions`；`include` 扩到 `tests/**/*.ts` 与三个 `*.config.ts`（配置文件一并受严格检查）；`exclude` 预留 `src/api/types.ts` | `typecheck` rc=0 |
| `web/vite.config.ts` | 别名 `@` → `<web>/src`，用 `new URL("./src", import.meta.url)` 求绝对路径（**零 node 内建**，因 `@types/node` 未声明，见 Q2）；`server`/`preview` 均 `port:5173` + `strictPort:true` | dev 实测仅 `LISTEN 127.0.0.1:5173`；`curl 127.0.0.1:5174` → rc=7（不顺延，避免 baseURL 指向空气） |
| `web/vitest.config.ts`（新增） | `defineConfig({ ...viteConfig, test:{ environment:"node", include:["src/**/*.spec.ts","tests/**/*.spec.ts"], exclude:["tests/e2e/**","node_modules/**","dist/**","test-results/**","playwright-report/**"], restoreMocks:true, clearMocks:true } })`。单独成文而非把 `test` 塞进 `vite.config.ts`：`vite build` 不必载入 vitest，别名仍单一真值 | `test` rc=0，4 passed；`tests/e2e/**` 已排除，S7 的 Playwright 用例不会被 vitest 误跑成假红 |
| `web/playwright.config.ts` | `testDir:"./tests/e2e"`、`baseURL` 与 `webServer.url` 均 `http://127.0.0.1:5173`、`webServer.command:"npm run dev"` + `reuseExistingServer:true`、两个 project（`desktop-1440x900` / `laptop-1024x768`，供 S9 直接采图）、`locale:"zh-CN"`、`timezoneId:"Asia/Shanghai"`；**所有数值刻意避开 `300[012]` 子串**（如用 45000 而非 30000） | `npx playwright test --list` → `Total: 0 tests in 0 files`，rc=1 **仅因 S7 尚未写用例**，配置本身加载成功 |
| `web/eslint.config.js` | 保留 M0-01 结构；`ignores` 增 `src/api/types.ts`（S4 生成物约 400KB）；新增 `src/**` 三条机器红线：`no-restricted-syntax`（六位十六进制色值字面量）、`no-restricted-imports`（`*frontend-template-spdb*` / `*youxia*`）、`no-console`（ADR-003 A 段要求浏览器 0 个 console.error） | 探针 `web/src/__eslint_probe.ts`（`"#0048d8"` + `console.log`）→ rc=1、2 errors；删除后 rc=0（探针已确认不存在） |
| `web/src/main.ts` | 组合根：注释钉死 S3/S5/S6 的接线顺序；`import App from "@/App.vue"` 让别名进入 build 图 | `build` rc=0（11 modules，`dist/assets/index-BLIIWH5l.js`） |
| `web/tests/unit/project-baseline.spec.ts`（新增） | 4 条基线不变量：5173+strictPort、配置序列化后无 `300[012]`、`@` 与 `tsconfig.compilerOptions.paths` 同义、严格开关未被后续 lane 关掉 | 4 passed（node 环境，不触碰 DOM） |
| 目录骨架 | `web/src/{api,components,composables,features,pages,router,styles}/.gitkeep`、`web/tests/{unit,e2e}/`（分层沿用 FRONTEND.md：pages/features/components/composables/api/router/styles） | `find` 实测 11 个文件；空目录用 `.gitkeep` 保证可入库 |

未改动：`web/package.json`、`web/package-lock.json`（任务卡禁改；新增依赖一律走 §8 裁定）、`web/index.html`、`web/src/App.vue`（S6 的活）。本阶段 `web/src` 内零十六进制色值、零模板 import。

## 2. 令牌与主题（S2）

### 2.1 令牌落地决策（ADR-003 → token-mapping.md）

- **真值链单向**：ADR-003 裁定值 → `docs/design/token-mapping.md`（表格）→ `web/src/styles/tokens.css`（`:root{--cl-*}`，S3 生成）。组件层只允许 `var(--cl-*)`，禁止任何色值字面量（rg + eslint 双守，见 §3）。
- **命名空间三分且不得互串**：`--cl-*`（项目令牌，只在 `tokens.css` 定义）／`--el-*`（Element Plus，只在 `element-theme.css` 定义且值一律为 `var(--cl-*)`）／项目级覆盖只在 `project.css`。对应 token-mapping §4.2。
- **前缀统一 `--cl-`**（CampaignLab），与模板 `--brand-600`/`--ink-900` 等原名去耦：模板只是视觉真值参照，不 import、不继承其变量名。
- **`main.ts` 导入顺序（S3 接线，顺序错则覆盖失效）**：`element-plus/dist/index.css` → `./styles/tokens.css` → `./styles/element-theme.css` → `./styles/project.css`。Element Plus 走全量 CSS（未声明 `unplugin-*`，不做按需样式）。
- **ADR-003 三项未决（BLK-04）按推荐值推进**：主色 `#0048d8`、白 rail + 深蓝顶栏（`--cl-nav-grad`）、语义色文字层用 SDD 深色（`--cl-ok-text`/`--cl-warn-text`/`--cl-danger-text`）、c3/c4 以数据标签 + 等义表补偿。若被改判，回改只动 `tokens.css` 一个文件（强制 flash 机械替换，返工成本低）。
- **字体与数字**：`--cl-font-sans: Inter, "Noto Sans CJK SC", "Microsoft YaHei", system-ui, sans-serif`；数字一律 `font-variant-numeric: tabular-nums`；缺值显示 `—` 并给出原因。**BLK-02 现状更正（实测）**：本机 `bash scripts/doctor.sh` 第 8 节为 `[ OK ] 存在中文字体（fc-list :lang=zh = 37 条）` 与 `Noto Sans CJK 已安装（fc-list 命中 10 条）`，**无字体 WARN** → BLK-02 在本机已解除，与任务卡「未安装」的记载不一致。任务卡仍要求 S9 的视觉结论附字体声明，故 S9 应把 doctor 第 8 节原文（而不是照抄「未安装」）作为声明证据附入，否则视觉结论不可用于验收。

### 2.2 Element Plus 主题接入：**选定 CSS 变量覆盖**

`web/src/styles/element-theme.css` 内 `:root { --el-color-primary: var(--cl-brand-600); --el-color-primary-dark-2: var(--cl-brand-700); … }`，逐条照抄 token-mapping §1「Element Plus 覆盖」列。理由：① token-mapping §1 给出的本就是 `--cl-*` ↔ `--el-*` 一一映射，语义天然吻合；② **零新增依赖**（`sass` 未在 `package.json`，见 Q6）；③ 覆盖结果可被机器断言（Playwright `getComputedStyle`；拿到 DOM 环境后 vitest 亦可）；④ `element-theme.css` 内不含任何色值，天然通过 rg 门禁，改令牌只改 `tokens.css`。

被否决：**SCSS 变量方案**（`@use "element-plus/theme-chalk/src/index.scss" with (...)`）—— 需新增 `sass`（违反「不引入未声明依赖」），且要把整个 theme-chalk 源纳入构建，build 时间与产物体积双升；本项目无编译期多主题需求，收益为零。**运行时 token 注入**（JS `setProperty`）—— 首屏 FOUC、无法静态自证，且把色值搬进 TS 会直接撞 rg 门禁。

### 2.3 ECharts 主题接入 + c3/c4 对比度补偿

- **按需模块**（FRONTEND.md 要求，`echarts` 包内已支持，零新增依赖）：`echarts/core` + 显式 `use([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, AriaComponent, LabelLayout, CanvasRenderer])`，落 `web/src/features/charts/echarts.ts`（M3-04 才真正使用，S6 不引入）。
- **主题注册**：`echarts.registerTheme("campaignlab", theme)`，`theme.color` 的 c1–c6 **在运行时从 CSS 变量读取**（`getComputedStyle(document.documentElement).getPropertyValue("--cl-c1").trim()`），落 `web/src/features/charts/theme.ts`。理由：色板若写进 TS 即违反「`web/src` 内除 `tokens.css` 外无六位十六进制」门禁；读 CSS 变量使 `tokens.css` 保持唯一真值。
- **c3(#18a890, 2.98 FAIL) / c4(#f39c12, 2.19 FAIL) 补偿（ADR-003 已裁定默认值；三条同时生效，缺一即判不通过）**：① 主题级 `aria: { enabled: true, decal: { enabled: true } }`，图案填充使序列不单靠颜色区分；② 系列级默认 `label: { show: true }`（数据标签直标数值）+ `emphasis.focus: "series"`；③ 组件级强制等义表格：任何图表只能由 `ChartWithTable`（page-component-map §1，首交 M3-04）渲染，图表与表格**共用同一服务器结果**，切换控件以用户可见名称定位。
- 另：c4 不得单独承载「警示」语义（语义色一律 `--cl-warn-text`，6.07 AA）；c6 仅「已触发/失败/禁止」；c5 仅填充或次要序列；M3 正负对比一律用 ECharts 柱状图（模板 `hbars` 不支持负值，已弃用）。
- **无 0 宽/0 高图表容器**（ADR-003 A 段）：`ChartWithTable` 必须给定宽包裹，S9 以 Playwright 断言 `boundingBox()` 宽高 > 0。

## 3. S3 机械落地指令（令牌一致性守卫）

- **产物**：`web/src/styles/tokens.css`（**唯一**允许出现六位十六进制色值的文件）、`web/src/styles/element-theme.css`、`web/src/styles/project.css`，并在 `web/src/main.ts` 按 §2.1 顺序接线（三个文件必须一次落齐，否则 `build` 会因缺文件而红）。变量名逐条照 token-mapping §1/§2 的「项目变量」列，不得自创、不得改名、不得增删档位；断点变量按 §3（>1100 / ≤1100 / ≤800）。
- **主门禁（必须，命令原文，仓库根执行）**：`rg -n '#[0-9a-fA-F]{6}' web/src --glob '!**/styles/tokens.css'` → **期望无输出、rc=1**（rc=1 表示无匹配属期望；rc=0 即违规）。
- **扩展门禁（同一次跑完）**：`rg -n '#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(' web/src --glob '!**/styles/tokens.css'` → 期望无输出、rc=1（阴影/透明色也必须走 `--cl-shadow-*` 或 `color-mix()`，不得在组件里写 `rgba()`）。
- **eslint 侧（S1 已装，S3 不必改配置）**：`no-restricted-syntax` 覆盖 TS/JS/SFC `<script>` 的色值字面量；`<style>` 块与 `.css` 不经 ESLint，由上面两条 rg 兜底 —— 两者互补，缺一不可。
- **vitest 守卫（推荐）**：`web/tests/unit/tokens.spec.ts` 用 `import tokensCss from "@/styles/tokens.css?raw"` 断言 token-mapping §1/§2 的每个 `--cl-*` 都在 `tokens.css` 中定义，并断言对比度（正文/次要/表头/状态文字对白底与画布 ≥4.5:1）。`*?raw` 由 `vite/client` 声明（实测 `node_modules/vite/client.d.ts` 第 249 行），`import.meta.glob` 由 `vite/types/importGlob.d.ts` 声明 —— **两者都不需要 `node:fs`**，故不会撞 `@types/node` 缺失（Q2）。

## 4. S4 类型客户端指令

- **命令原文**（`openapi-typescript` v7.13.0 已在 devDependencies，`--version` 实测 rc=0；不得改 `package.json`）：`cd /home/szf/dev/CampaignLab/web && node_modules/.bin/openapi-typescript ../contracts/openapi.json -o src/api/types.ts`
- **产物路径**：`web/src/api/types.ts`（已在 `eslint.config.js` 的 `ignores` 与 `tsconfig.json` 的 `exclude` 中预留位置）。
- **「diff 为空」验证（三步，逐条记 rc）**：① 幂等性：生成 → `cp src/api/types.ts /tmp/types.a.ts` → 再生成 → `cmp -s /tmp/types.a.ts src/api/types.ts; echo rc=$?` → 期望 **rc=0**；② 与入库版本一致：`git diff --exit-code -- web/src/api/types.ts; echo rc=$?` → 首次生成时该文件未入库，rc=1 且 `git ls-files --others --exclude-standard web/src/api/types.ts` 应列出该文件，S4 重跑时期望 **rc=0**；③ 版本锚（PRE-3）：`python3 -c "import json;print(json.load(open('contracts/openapi.json'))['info']['version'])"` → 期望 `1.0.1`，不一致即契约已变，必须重切后再派，不得就地生成。
- **禁止**：手写或手改 `types.ts`；把 `openapi.json` 拷进 `web/`；整读 `openapi.json` 进上下文（需字段用 `python3` 定点提取）。
- **收尾**：`npm --prefix web run typecheck` 必须仍 rc=0（生成物不得引入类型错误），并把 `wc -l web/src/api/types.ts` 记入证据。

## 5. 错误分支对齐 ADR-005

- **单一入口**：`web/src/api/http.ts`（S5 落地）把任何非 2xx 解析为 `ApiError = { status, code, type, title, detail, requestId, issues }`；字段与活契约 `Problem` 一一对应（required：`type/title/status/code/detail/request_id/issues`，`additionalProperties:false`）。
- **分支键只用 `code`**，不解析 `type` 里的 URL；但 `http.ts` 必须做一次一致性断言 `type === "urn:campaignlab:problem:" + code.toLowerCase()`（ADR-005 §2.1）：不一致时**以 `code` 为准**，dev 下抛断言、生产下走 AlertBanner 呈现（不得 `console.*`，eslint 已禁）。
- **`title` 直接渲染服务端返回值，前端不得另编文案**（ADR-005 §2.2；§3 已否决「各 lane 自定义 title」）。`detail` 可展示；`request_id` 必须可见（COMMON.md「错误显示 request_id」）；`issues[]` 按 `location` 定位到表单字段，`severity` 的 ERROR/WARNING/INFO → AlertBanner 危险/警示/信息。
- **前端不内置 code 白名单**：契约只约束 `code` 为 pattern 串，注册表 `src/campaignlab/domain/errors.py` 实测尚不存在（Q4）。未知 code 一律走 default 分支，渲染服务端 `title` + `detail` + `request_id`，禁止「全部通过」式总括文案。
- **status → 前端行为（UI-01 范围）**：401（`SESSION_EXPIRED`/无会话）清本地会话与 store → 跳 `/`，原深链存 `?redirect=`（页面侧深链要求，依据 `framework/FRONTEND.md:12`；AC-034 的 HTTP 负例本体归 M0-02，见 D-011）；403 对象级 → 与 404 **同一呈现**（COMMON.md「越权对象按不可见处理」＝不可见即不可见），仅证据里区分 status；403 会话/Host/Origin 级（exchangeSession/getSession）→ 回 `/` 并提示「重开本机入口」；404 → 404 页 + 当前工作区返回入口；400 `INVALID_SCOPE` / 422 → AlertBanner + `issues[]` 定位字段且**保留输入**；409 `IDEMPOTENCY_CONFLICT` → ConfirmDialog「已受理，勿重复提交」，重试沿原 `Idempotency-Key`；412 `REVISION_CONFLICT` → 保留本地输入 + 显示新旧 `revision` + 「重新获取/复跑」入口；413 → JSON 正文上限 **1 MiB**（ADR-005 §2.3），`createWorkspace` 提交前用 `new TextEncoder().encode(JSON.stringify(body)).byteLength` 预检，超限即字段级提示且**不发请求**（文件上传的 8/64 MiB 是另一对象，不得混用）；428 `PRECONDITION_REQUIRED` → 缺 `If-Match`，属前端缺陷：dev 断言 + 通用失败态；429 → 指数退避（首次 1s，上限 3 次）后仍渲染服务端 `title`；500 → 通用失败 + `request_id`。
- **运行参数**：会话 TTL 1h、worker 心跳 15s（ADR-005 §2.3）。UI-01 顶栏「作业受限」由 `Health.worker === "OFFLINE"` 或 `status === "DEGRADED"` 驱动；**前端一律以服务端响应为准，不得用系统当前时间自行推算过期**（领域不变量）。

## 6. 状态章节（S5 填写，本节仅留边界，S1/S2 不替 S5 决定）

S5 需在本节补：`web/src/api/http.ts`（cookie credentials、ETag/If-Match、`Idempotency-Key`、Problem→ApiError、202 轮询骨架、abort/请求序列防晚到覆盖）、`web/src/composables/useSession.ts`（exchangeSession/getSession、401 回入口、深链 `redirect`）、`web/src/composables/useWorkspaces.ts`（listWorkspaces 游标 25 行、createWorkspace + ETag/revision）、切工作区清理策略（COMMON.md：清临时查询、轮询、失效选择）。接口边界：S5 只导出「签名 + 错误映射」，S6 页面侧不得直接 `fetch`。

已定约束（S5 不得推翻）：状态源限 URL / 请求缓存 / 本地表单；金额=分整数、比率=十进制字符串，仅在显示层转元/百分数/百分点；时区 Asia/Shanghai；只用合成数据。依赖前提：Pinia 未声明（Q5）→ 默认 Vue 原生 `reactive` + composable 单例。

## 7. S6–S9 文件白名单（越界即回报，手册 6.4）

| 子任务 | 允许创建/修改 | 组件名 / 文件 | 禁止 |
|---|---|---|---|
| S6 | `web/src/pages/**`、`web/src/components/**`、`web/src/features/**`、`web/src/router/index.ts`、`web/src/main.ts`（仅接线）、`web/src/styles/**`（仅接线，不改令牌值） | page-component-map §1 首交 M0-03：`AppShell` `SideRail` `AppBar` `PageBar` `EvidenceDrawer` `StatusTag` `PageGrid` `CardPanel` `AlertBanner` `EmptyState` `DataTable`（+ `ConfirmDialog`，见 Q3）；页面 `web/src/pages/workspace/WorkspacePage.vue` | 改 `tokens.css` 色值；import 模板；写死色值；自建 store（属 S5）；`console.*` |
| S7 | `web/tests/e2e/**` | `keyboard-baseline.spec.ts`：焦点可见 2px、Tab 序、抽屉 Esc 关闭并返回触发焦点、表头排序可键盘触发 | 改 `web/src/**`；绑 3000 段端口 |
| S8 | `web/tests/unit/**` | `workspace-entry.spec.ts`（AC-001）、`deep-link.spec.ts`（页面侧深链，依据 `framework/FRONTEND.md:12`，**非** AC-034，见 D-011）、`tokens.spec.ts`（S3 守卫） | 需 DOM 的用例依赖 Q1 裁定；未裁定前只写 node 环境可跑的纯函数断言 |
| S9 | `evidence/M0/M0-03/**`、`evidence/M0/ui/**`、`web/tests/e2e/**`（截图 spec） | `ui-01-desktop-1440x900.png`、`ui-01-laptop-1024x768.png`（文件名 ASCII） | 写 `web/src/**`；未附字体声明（doctor 第 8 节原文）即下视觉结论；浏览器不可用却谎称 E2E 通过（须记 PASS_WITH_TODO 关联 BLK-01） |
| S10 | `orchestrator/handoff/M0-03-public-components.md` | 公共组件清单与冻结边界 | 见 Q8（该目录未列入 `scope_allow`） |

## 8. 未决问题（不自行决定，交编排器／项目负责人裁定）

| # | 问题 | 影响面 | 本设计的临时处置 |
|---|---|---|---|
| Q1 | **DOM 测试环境缺失**：`web/package.json` 未声明 `jsdom`（registry 实测 latest 31.0.0）或 `happy-dom`（21.0.4），也未声明 `@vue/test-utils`（2.5.1）；vitest 只能 `environment:"node"`。而 token-mapping §4.4「对比度断言进 Vitest」与 S8「AC-001 断言 + 页面侧深链断言（`framework/FRONTEND.md:12`，非 AC-034，见 D-011）」都需要 DOM/computed style。 | S3 守卫、S8 全部页面侧断言 | 请求批准新增 devDependencies：`jsdom@^31.0.0`（或更轻的 `happy-dom@^21.0.4`）+ `@vue/test-utils@^2.5.1`。未裁定前 vitest 固定 `node` 环境，用例不得触碰 `document`/`window` |
| Q2 | **`@types/node` 未声明**（registry latest 26.6.6）：`web/*.config.ts` 不能用 `node:path`/`node:url`（本子任务改用 `new URL(...).pathname` 规避），而 S9 的 Playwright 截图归档几乎必然要 `node:fs`/`node:path`；`tests/**` 已纳入 tsconfig，届时 `typecheck` 会红。 | S9 证据采集、typecheck 门禁 | 请求批准新增 devDependency `@types/node@^26`；若否决，须把 `tests/e2e/**` 移出 `tsconfig.json` 的 `include`（牺牲 e2e 类型检查），二选一请裁定 |
| Q3 | **`ConfirmDialog` 交付期冲突**：`page-component-map.md` §1 记「首次交付 M2-04」，但同文件 §2 的 UI-01 行写「创建走 `ConfirmDialog`」，且 M0-03 gates 要求 UI-01 能新建工作区。 | S6 组件清单、S10 冻结边界 | 建议 M0-03 交付 `ConfirmDialog` 最小实现（520px，摘要+影响+取消+主按钮），并把 §1 的「首次交付」改为 M0-03；或改用 `ElDialog` 顶替（会与「公共组件各只有一个实现」冲突） |
| Q4 | **`code` 注册表不可得**：契约只把 `code` 约束为 pattern 串、未枚举取值；ADR-005 §2.1 指定的单一来源 `src/campaignlab/domain/errors.py` 实测尚不存在（`find src -name errors.py` 为空）。 | §5 错误分支、S8 参数化断言 | 前端不内置 code 白名单，未知 code 走 default 分支渲染服务端 `title`/`detail`/`request_id`。请求 M0-02 S3 落地后把注册表以**只读快照**交 S8 做参数化，而不是让前端镜像一份（镜像即污染冻结面） |
| Q5 | **Pinia 未声明**（registry latest 4.1.0）：FRONTEND.md 的七层里没有 stores 层，S5 的「store」无既定载体。 | S5 状态设计、S6 接线 | 默认用 Vue 原生 `reactive` + composable 单例（`web/src/composables/`），零新增依赖；若裁定引入 `pinia@^4`，需同步改 `package.json`/`package-lock.json`（由编排器执行） |
| Q6 | **`sass` 未声明**（registry latest 1.108.2）：若坚持 Element Plus 走 SCSS 变量方案，必须新增该依赖并接受构建变重。 | §2.2 主题方案 | 已选 CSS 变量覆盖（零依赖、可机器断言）。若改判 SCSS，属方案级返工，需重跑 S3 |
| Q7 | **`listWorkspaces` 的 `status` 查询参数语义未定**：M0-02 设计 Q4 已记「`Workspace` schema 与表都无 `status` 字段」，其临时处置是任何非空 `status` → 422 `INVALID_SCOPE`。 | UI-01 工作区列表是否需要状态筛选控件 | S6 暂不提供该筛选控件；若裁定补 `status` 字段，属契约变更，须重切再派 |
| Q8 | **`scope_allow` 未含 `orchestrator/handoff/**`**：任务卡 `scope_allow` 只列 `web/**` 与 `evidence/M0/{ui,M0-03}/**`，但档位表把 S2/S5 的 `M0-03-design.md` 与 S10 的 `M0-03-public-components.md` 指定为该目录产物（与 M0-02 设计 Q8 同类冲突）。 | S2/S5/S10 是否越界 | 按档位表 `outputs` 执行（本文件即产物），未触碰 `scope_deny`；请求把这两个文件显式加入 `scope_allow` |
| Q9 | **`exactOptionalPropertyTypes` 与 Element Plus props 的摩擦风险**：该开关对库组件的可选 prop 极严（`undefined` 与「不传」不等价），S6 铺开表单字段时可能大量报错。 | S6 工作量、typecheck 门禁 | 保留该开关（派单明确要求）。S6 处置口径：可选 prop 用 `v-bind="x ?? undefined"` 或 `:prop="value ?? undefined"`，**不得**为过检查而关掉 tsconfig 开关；摩擦面过大即回报编排器 |

> **【编排器追注 · 2026-11-13T02:17:03+08:00 · CR-002 / ADR-006 · 只加注不改写】**
>
> 上表 **Q7** 已随 CR-002 **选项 B** 落定：`listWorkspaces` 的 `status` 查询参数已从活契约移除（ADR-006）。
>
> - 「UI-01 **不提供**状态筛选控件」由**临时处置转为终态**；S6 不得实现该控件。
> - M0-02 设计 Q4 的「任何非空 `status` → 422 `INVALID_SCOPE`」过渡分支同步**取消**，前端不得为其写错误分支断言。
> - 切片已重切，**S3/S4 必须以重切后的 `orchestrator/handoff/M0-03.slice.json` 为准**；
>   其 `source.openapi.sha16` / `bytes` 权威现值见
>   `orchestrator/state.json → resume.self_check_gates_rc0.counts.live_openapi_sha16` / `.live_openapi_bytes`（禁写死）。
>
> 本追注为**新增留痕**；上表 Q7 行原文**保持字节不变**。

## 9. 本文件自检（命令 → 实测 rc；均在 WSL 仓库根 `/home/szf/dev/CampaignLab` 执行）

| # | 命令 | 实测 rc | 关键输出 |
|---|---|---|---|
| G1 | `npm --prefix web run typecheck` | 0 | 无输出。**留痕**：首跑 rc=2，报 `tests/unit/project-baseline.spec.ts(31,16) TS7053`（`AliasOptions` 联合类型不能用字符串索引）；加 `readAlias()` 收窄后第 2 次 rc=0 |
| G2 | `npm --prefix web run lint` | 0 | 无输出。**留痕**：中途插入探针 `web/src/__eslint_probe.ts` 时 rc=1（2 errors：色值字面量 + no-console），用于自证红线生效；删除探针后 rc=0 |
| G3 | `npm --prefix web run test` | 0 | `Test Files 1 passed (1)`、`Tests 4 passed (4)`。**留痕**：验证 `@` 别名时临时加 `tests/unit/__alias_probe.spec.ts` → 5 passed，随后删除并复跑回到 4 passed |
| G4 | `npm --prefix web run build` | 0 | `vite v8.3.8`、`11 modules transformed`、`dist/index.html 0.32 kB`、`dist/assets/index-BLIIWH5l.js 62.82 kB` |
| G5 | `uv run --no-sync ruff format --check .` | 0 | `54 files already formatted`；追加 `--exclude orchestrator/handoff/M0-03-design.md` 复测得 `53 files already formatted` → 差值 **+1**，证明本 `.md` 已进入 ruff format 作用域并被接受。**留痕**：本子任务开工时基线为 51，其间并行 lane 推进使基线升到 53，非本子任务所为 |
| G6 | `uv run --no-sync ruff check .` | 0 | `All checks passed!` |
| G7 | `grep -rn '300[012]' web/*.config.* web/playwright.config.ts` | 1 | 无输出（rc=1 = 无匹配，属期望）→ 端口纪律 NOTE-01 自证。**留痕**：首跑 rc=0 并命中 5 行，全部是 `vite.config.ts` / `playwright.config.ts` 里我自己写的中文注释中的那三个端口数字字面量（配置值本身干净）；把注释改写为「30xx 段三个端口」后复跑 rc=1。此为自伤型假红，已修正，未反复重跑 |
| G8 | `rg -n '#[0-9a-fA-F]{6}' web/src --glob '!**/styles/tokens.css'` | 1 | 无输出（rc=1 = 无匹配，属期望）→ S1/S2 阶段未留色值债 |
| G9 | `bash scripts/doctor.sh` | 0 | `PASS=15  WARN=1  FAIL=0`、`RESULT: HEALTHY`。唯一 WARN 文本为 `[WARN] 工作树存在 16 项未提交改动` —— 脏树 WARN 属预期（本子任务正在写文件），判定看 WARN 文本而非计数。**无字体 WARN**（BLK-02 在本机已解除，见 §2.1）；Playwright 缓存实测 `chromium-1234`/`chromium-1254` 与两个 headless shell 均在 |
| G10 | `git status --porcelain` | 0 | 16 行：` M` 5 项 = `web/{eslint.config.js,playwright.config.ts,tsconfig.json,vite.config.ts,src/main.ts}`；`??` 11 项 = `orchestrator/handoff/M0-03-design.md`、`web/vitest.config.ts`、`web/src/{api,components,composables,features,pages,router,styles}/`、`web/tests/`，**加 1 项非本子任务所为的 `evidence/M0/Q-VERIFY-M0-01/judge/`**（并行 Q lane 产物，文件时间戳 23:55–01:06，本子任务从未写 `evidence/**`）。`web/package.json` 与 `web/package-lock.json` 均无改动。采集期间并行 lane 使 HEAD 由 `ee51f3f` 推进到 `b1f38a9`，同样非本子任务所为（本子任务未执行任何 git 写操作） |
| G11 | `git ls-files --others --exclude-standard orchestrator/handoff/M0-03-design.md` | 0 | 输出该路径 → 未被 `.gitignore` 忽略、可入库 |
| G12 | `npx playwright test --list`（在 `web/`） | 1 | `Listing tests: Total: 0 tests in 0 files` + `Error: No tests found`；配置加载成功，rc=1 仅因 S7 未写用例 |

## 10. 状态章节（S5 落地实录 · 2026-11-13 · 纯增量追加）

> **追加纪律自证**：§6「状态章节（S5 填写，本节仅留边界）」是 S2 留下的占位边界，本节按项目纪律
> 「历史值只加注不改写」**只在其后追加**，§6 与 §1–§9 的既有字节一字未动
> （`git diff --numstat` 对本文件 removed=0 即为自证）。本节即 §6 点名要 S5 补的全部内容：
> 接口签名、错误映射、ETag 与幂等处理、切工作区清理策略，外加 token-mapping §3 指定随 S5 落地的
> **断点变量一致性守卫**。S5 未引入任何新依赖（Q5 裁定：Vue 原生 `reactive` + composable 单例），
> 未 `import vue-router`（router 属 S6），未改 `web/package.json`、`tokens.css` 令牌值、`api/types.ts`。

### 10.1 落地文件（全部落在 `scope_allow`：`web/src/**`、`web/tests/**`）

| 文件 | 行数 | 职责 |
|---|---|---|
| `web/src/api/http.ts` | 554 | 唯一 HTTP 出口：cookie、Problem→ApiError、ETag/If-Match、Idempotency-Key、1 MiB 预检、429 退避、202 轮询骨架、RequestGate（abort + 请求序列） |
| `web/src/api/endpoints.ts` | 108 | 切片 5 个 operationId 的类型化封装；参数/请求体/响应体全部从 `operations[...]` 抽取，不重抄字段 |
| `web/src/composables/useWorkspaceScope.ts` | 167 | 工作区作用域 = (workspaceId, epoch, 资源表, gate)；**切工作区清理策略的唯一实现** |
| `web/src/composables/useSession.ts` | 187 | 会话 store：exchangeSession/getSession、入口令牌一次性、401/403 回合法入口、深链 `pendingRedirect` |
| `web/src/composables/useWorkspaces.ts` | 275 | 工作区 store：listWorkspaces 游标 25 行、createWorkspace、getHealth→作业受限、revision/ETag 请求缓存 |
| `web/src/main.ts` | 32（改） | 按 §6 接线 `app.provide(...)`；顺序＝依赖顺序 http ← scope ← session ← workspaces |
| `web/tests/unit/api-client.spec.ts` | 677 | 29 条纯逻辑用例（node 环境，注入 fetch 替身，不发真实请求、不触碰 DOM） |
| `web/tests/unit/breakpoint-guard.spec.ts` | 327 | 12 条断点一致性守卫用例（含正/负例夹具自证非空转） |

### 10.2 接口签名（冻结面：S6 只准调用，不得重定义或直接 `fetch`）

```ts
// web/src/api/http.ts
type ApiErrorKind = "problem" | "transport" | "aborted" | "payload" | "assertion" | "timeout";
interface ApiError { kind; status; code; type; title; detail; requestId; issues: readonly Issue[];
                     payload?: { limitBytes; actualBytes }; cause?: string }
type ApiResult<T> = ApiOk<T> /* { ok:true, status, data:T, etag, requestId, notModified } */
                  | { ok:false, error: ApiError };
interface HttpClient {
  request<T>(options: HttpRequestOptions): Promise<ApiResult<T>>;   // 不抛异常：失败一律走 ApiResult
  poll<T>(options: PollOptions): Promise<ApiResult<T>>;             // 202 轮询骨架
  keyOf(o): string; etagFor(key): string|null; rememberEtag(key, etag): void;
  devAssertions(): readonly string[]; drainDevAssertions(): string[]; baseUrl: string;
}
interface HttpRequestOptions { method; path; query?; body?; headers?; ifMatch?; idempotencyKey?;
  ifNoneMatch?; accept?; signal?; requireIdempotencyKey?; requireIfMatch? }
function createHttpClient(config?: HttpClientConfig): HttpClient;   // fetchImpl/clock/sleep 均可注入
function createRequestGate(): RequestGate;                          // begin/isCurrent/cancelAll/inflightCount
function newIdempotencyKey(purpose: string): string;                // 8..128，一次用户意图一个
function isValidIdempotencyKey(key: string): boolean;
function jsonBodyBytes(body: unknown): number;                      // TextEncoder 实算
const http: HttpClient;  const httpKey: InjectionKey<HttpClient>;

// web/src/api/endpoints.ts（签名与切片逐一对应）
exchangeSession(token: string, client?): Promise<ApiResult<Session>>          // POST /session/exchange
getSession(client?): Promise<ApiResult<Session>>                              // GET  /session
getHealth(client?): Promise<ApiResult<Health>>                                // GET  /health
listWorkspaces(query?: ListWorkspacesQuery, client?): Promise<ApiResult<WorkspacePage>>  // GET /workspaces
createWorkspace(body: CreateWorkspaceBody, o: { idempotencyKey; client? }): Promise<ApiResult<Workspace>>

// web/src/composables/*.ts（单例 + 工厂双出口：工厂供单测隔离，单例供组合根 provide）
createWorkspaceScope(deps?) / useWorkspaceScope(): WorkspaceScope
  { state{workspaceId,epoch,resourceCount,lastClearReason,lastClearedAt}, gate,
    register(kind,label,dispose)=>unregister, list(), setWorkspace(id,reason?)=>changed,
    clear(reason), isStale(epoch), epochOf() }
createSessionStore(deps?) / useSession(): SessionStore
  { state{phase,session,error,entryTokenUsed,pendingRedirect,lastRequestId,lastSignOutReason},
    bootstrap(entryToken|null)=>phase, exchange(token), verify(), signOut(reason,redirect?),
    captureRedirect(fullPath), takeRedirect(), hasRole(role), onSignOut(handler)=>off }
createWorkspacesStore(deps?) / useWorkspaces(): WorkspacesStore
  { state{phase,items,nextCursor,limit=25,q,error,health,workerRestricted,creating,createError,
          selectedId,lastRequestId}, revisions,
    refreshHealth(), loadFirstPage(), loadMore(), setQuery(q), create(body,idempotencyKey),
    select(id|null)=>changed, revisionOf(id), resetForSignOut() }
```

### 10.3 错误映射（承接 §5，不重开裁定）

- **单一入口**：所有非 2xx 一律经 `http.ts` 的 `readProblem()` 映射成 `ApiError`；`kind === "problem"` 是唯一可渲染 `title` 的来源（ADR-005 §2.2：`title` 原样透传，前端不另编文案）。
- **分支键只用 `code`**；`type` 仅做一次一致性校验 `type === "urn:campaignlab:problem:" + code.toLowerCase()`，不一致以 `code` 为准并写 dev 断言水槽（不 `console.*`、不抛出，S8 可断言水槽为空）。§5 所称「dev 下抛断言」在 S5 的落地形态即该水槽 + `drainDevAssertions()`（水槽上限 100 条，生产不无界增长）。
- **`issues[]` 逐条校验**：四字段（code/location/message/severity）任一残缺即丢弃该条，避免把错误字段定位塞给表单。
- **非 Problem 的失败**分五类，`title`/`code` 恒为空串，UI 只能用 COMMON.md 通用失败态 + `request_id`：`transport`（网络异常/正文非 Problem/2xx 正文非 JSON）、`aborted`（AbortSignal）、`payload`（1 MiB 预检失败，请求未发出）、`assertion`（缺 If-Match / 缺或非法 Idempotency-Key，属前端缺陷，请求未发出）、`timeout`（202 轮询耗尽上限）。
- **status → 行为**照 §5 表执行，S5 已在 store 里落地的部分：401 → `session.signOut()`（清会话 + `scope.clear()` + 保深链）；403（会话级）→ `signOut(reason, "/")` 强制回合法入口；409/412/413/422 → `createError` 保留、**不擅清表单输入**；403 与 404 的同一呈现属 S6 视图层。
- **`getHealth` 的 `Health.status` 是合法响应字段**（READY/DEGRADED），与 CR-002 移除的 `listWorkspaces.status` 查询参数无关；`endpoints.ts` 未提供任何状态筛选入口（CR-002 终态）。

### 10.4 ETag 与幂等处理

- **缓存键**：`keyOf({method,path,query})` = `method + " " + path + "?" + 排序后的 query`；ETag 与请求序列共用同一口径。
- **响应侧**：任何带 `ETag` 的响应自动入内存缓存；`createWorkspace` 201 的 ETag 与 `Workspace.revision` 一并写进 `revisions[workspaceId]`，后续变更请求经 `ifMatch` 上送 `If-Match`。
- **请求侧**：`requireIfMatch: true` 时缺 `If-Match` → `kind:"assertion"`，**请求不发出**（对应服务端 428 `PRECONDITION_REQUIRED` 属前端缺陷，在客户端先拦下）。
- **304 / 条件 GET**：活契约未声明 304，故默认**不发** `If-None-Match`；`ifNoneMatch` 仅作显式开关保留，收到无 `If-None-Match` 的 304 记 dev 断言并判 `transport`（见 R3-Q3）。
- **幂等键**：`newIdempotencyKey(purpose)` 生成 `<purpose>-<uuid>`（截断至 128）；`isValidIdempotencyKey` 按契约 8..128 且排除空白/控制字符校验；非法或缺失 → `kind:"assertion"`，请求不发出。**409 `IDEMPOTENCY_CONFLICT` 的重试必须沿原 key**：store 不重新生成，键由 S6 按「一次用户意图一个」持有。
- **1 MiB 预检**：`jsonBodyBytes()` 用 `new TextEncoder().encode(JSON.stringify(body)).length` 实算，超限即 `kind:"payload"` 且带 `{limitBytes, actualBytes}`，**请求不发出**（与文件上传的 8/64 MiB 是不同对象，未混用）。
- **429 退避**：首次 1s、倍增、上限 3 次（共 4 次尝试），退避期间被取消即返回 `aborted`；耗尽后透传服务端 Problem 的 `title`。

### 10.5 切工作区清理策略（FRONTEND.md:12/13 + UI-01「切换后清除上一个工作区的草稿范围和轮询」）

- **作用域三元组**：`(workspaceId, epoch, 资源表)`。`epoch` 单调递增；任何在 epoch 变更前发出的请求/轮询回来后一律 `isStale()` 判真并丢弃。
- **资源表**：`register(kind, label, dispose)`，`kind ∈ {poll, temp-query, selection, draft, chart, listener}`；返回注销函数供组件卸载时调用。绑定 `workspaceId === null` 的是**全局资源**（如 app 级监听），只随 `clear()` 释放，不随切换清理。
- **`setWorkspace(id)` 顺序**：`gate.cancelAll()` → dispose 上一工作区资源 → 写新 id → `epoch+1`。先中止再 dispose 再推进 epoch，保证 dispose 内触发的最后一次回调仍判 stale，不会写回新作用域。
- **同 id 重复 `setWorkspace` 直接返回 false 且不做任何清理**：刷新、深链回到同一工作区、返回键都不许丢草稿（FRONTEND.md:12）。
- **`dispose` 抛错不得阻断其余资源释放**（清理是幂等义务，不是事务）；异常被吞掉且不留 `console.*`。
- **`gate.cancelAll()` 同时递增序列号**（本轮实测修正的关键点）：被取消的请求即使仍以 `aborted` 结果返回，也一律判 stale 而丢弃，否则切工作区/登出瞬间会在 UI 上闪一条假的传输错误。
- **请求缓存清理粒度**：`select()` 只清上一作用域的 `revisions` 条目，**保留新选中工作区自身那条**（它刚由列表响应给出，删掉等于把服务端已给的 revision 白扔，下次变更请求要多跑一趟 412）；登出路径 `resetForSignOut()` 全清。
- **入口页搜索词 `q` 不随切换清理**：判定为页面级状态而非对象级临时查询（见 R3-Q5）。
- **store 间联动用观察者而非互相 import**：`session.onSignOut(handler)`，`useWorkspaces` 创建时注册 `resetForSignOut`，避免 session ↔ workspaces 循环依赖。

### 10.6 断点变量一致性守卫（token-mapping §3 指定随 S5 落地的项）

- **位置**：`web/tests/unit/breakpoint-guard.spec.ts`（12 条用例，`environment: node`，与 `tokens-guard.spec.ts` 同风格、同扫描通道 `import.meta.glob("/src/**/*", { query:"?raw", eager:true })`，不依赖 `node:fs`/`@types/node`，见 Q2）。
- **三条校验规则**：
  1. `tokens.css` 必须逐字声明 §3 表格三变量且**各只声明一次**：`--cl-bp-rail-collapse: 1100px`、`--cl-bp-rail-drawer: 800px`、`--cl-content-max: 1440px`；
  2. `web/src` 内每个 `@media` 断点字面量（`px`/`em`/`rem`，em/rem 按根字号 16px 折算）都必须能在 §3 表格找到**取值相等的同名变量**，否则判违规；表外像素值（如 1024px）必红；
  3. 该字面量所在行或其上一行必须**写出同名变量名**（可追溯注记），把 §3 的「找到同名变量」变成机器可证明；断点变量不得在 `tokens.css` 之外重声明，也不得出现 §3 之外的第四个断点变量。
- **实测结果**（`npm --prefix web run test -- tests/unit/breakpoint-guard.spec.ts`，rc=0，12 passed）：扫描 11 个源文件（排除 `src/api/types.ts`）；`tokens.css` 三变量命中 `1100px / 800px / 1440px`；**`web/src` 内 `@media` 断点条数 = 0，违规条数 = 0** —— 与 §3「在 S5 之前不得出现写死像素的媒体查询」一致（Shell 布局属 S6，届时本守卫自动升级为实质校验）。
- **非空转自证**：6 条夹具用例证明校验逻辑真的会红——正例（注记齐备的 1100px）通过并给出映射；负例一（表外 1024px）判「找不到同名变量」；负例二（800px 值对但未注记变量名）判「未注记同名变量」；`50em` 折算 800px 命中 `--cl-bp-rail-drawer`；跨行 `@media` 前置条件可解析；CSS 块注释与 TS 行注释里的 `@media` 不计入（`tokens.css:96` 注释中的「@media」已作真实文件回归断言）。
- **给 S6 的硬要求**：写媒体查询时必须在同行或上一行注记变量名，例如
  `/* --cl-bp-rail-collapse */` 换行 `@media (max-width: 1100px) { … }`；否则守卫判红。

### 10.7 S5 出口门禁实测（WSL 仓库根 `/home/szf/dev/CampaignLab`；判定看输出文本，不只看管道末端 rc）

| # | 命令 | 实测 rc | 关键输出 |
|---|---|---|---|
| G1 | `npm --prefix web run typecheck` | 0 | 无输出（首跑 rc=2：`http.ts` 的 `RequestInit.signal` 撞 `exactOptionalPropertyTypes`、用例一处未用形参；按需展开 + `_call` 后 rc=0） |
| G2 | `npm --prefix web run test` | 0 | `Test Files 4 passed (4)`、`Tests 56 passed (56)`、0 skipped（基线 15 → 新增 41：api-client 29 + breakpoint-guard 12） |
| G3 | `npm --prefix web run lint` | 0 | 无输出 |
| G4 | `npm --prefix web run build` | 0 | `vite v8.3.8`、`20 modules transformed`（S1 为 11，+9 即本次接线进图）、`dist/assets/index-Bh3UH9B3.js 75.01 kB` |
| G5a | `rg -n '#[0-9a-fA-F]{6}' web/src --glob '!**/styles/tokens.css'` | 1 | 无输出（rc=1＝无匹配，属期望） |
| G5b | `rg -n '#[0-9a-fA-F]{3,8}\b\|\brgba?\(\|\bhsla?\(' web/src --glob '!**/styles/tokens.css'` | 1 | 无输出 |
| G5c | `grep -rn '300[012]' web/*.config.* web/playwright.config.ts` | 1 | 无输出（源码内亦无 30xx 端口字面量：baseURL 只从 `VITE_API_BASE_URL` 注入） |
| G6 | `npm --prefix web run test -- tests/unit/breakpoint-guard.spec.ts` | 0 | `12 passed`；`@media 断点条数 = 0`、`违规条数 = 0`（详见 §10.6） |
| G7 | `python3 scripts/check_frontend_baseline.py` | 0 | `FRONTEND BASELINE PASS 8/8（哈希与字节数逐项一致）` |

### 10.8 S6 接线须知（不得推翻的口径）

1. 页面/组件**不得直接 `fetch`**，一律经 `endpoints.ts`；需要新 operationId 时在 `endpoints.ts` 追加同风格封装，不要在组件里就地拼 URL。
2. 组合根已按 `http ← scope ← session ← workspaces` 顺序 `provide`；S6 只在 `main.ts` **追加** `app.use(router)`，不得改这段顺序（后创建的 store 复用前者的单例）。
3. 深链由 S6 的路由守卫消费：进受保护路由前 `session.captureRedirect(to.fullPath)`；会话失效后 `session.takeRedirect()`（一次性消费，兜底 `/`）。`captureRedirect` 只接受站内绝对路径，外链与 `//host` 一律降级为 `/`（开放重定向防护）。
4. 需要随工作区释放的东西（轮询定时器、临时查询、图表实例、失效选择、事件监听）**必须** `scope.register(kind, label, dispose)`，并在组件卸载时调用返回的注销函数；不要自己另建清理表。
5. `exactOptionalPropertyTypes` 保留（Q9）：可选 prop 一律 `:prop="value ?? undefined"`；本层已按此实现（如 `ifMatch: client.etagFor(key) ?? undefined`、`signal` 按需展开）。
6. 单位与显示：store 只搬运服务端原值（金额＝分整数、比率＝十进制字符串、时间＝带 `+08:00` 的 ISO 串），转元/百分数/百分点/时区呈现一律在显示层做（S6）。

### 10.9 S5 新增未决问题（编号 R3-Q*，交编排器／项目负责人裁定；不自行决定）

| # | 问题 | 影响面 | S5 的临时处置 |
|---|---|---|---|
| R3-Q1 | **后端 baseURL 注入方式未定**：`web/*.config.*` 禁出现 30xx 端口（G5c），vite 也未配 `server.proxy`，故 dev 期前端如何指向后端无既定口径。 | S6 联调、S9 Playwright 取证 | `http.ts` 默认同源相对路径，只认 `VITE_API_BASE_URL`。请裁定：dev 走 vite proxy（由编排器改 `web/vite.config.ts`）还是走 `.env.local` 注入 |
| R3-Q2 | **断点守卫的「变量名注记」规则比 §3 原文更严**：§3 只要求「找到同名变量且取值相等」，S5 另加了「同行或上一行必须写出变量名」以让「同名」可机器证明。 | S6 写 `@media` 的自由度 | 建议保留（否则「同名」只能靠人工走查）。若判过严，删掉 `breakpoint-guard.spec.ts` 里 `未注记同名变量` 那一条分支即可降级 |
| R3-Q3 | **304 / 条件 GET 无契约依据**：5 个 operationId 的 responses 均未声明 304。 | 请求缓存策略 | 默认不发 `If-None-Match`；`ifNoneMatch` 仅留开关。若后端要支持，须先在活契约声明再重切 |
| R3-Q4 | **202 轮询默认档（1.5s × 20 = 30s）无契约依据**，UI-01 的 5 个 operationId 也没有 202。 | 后续作业页（UI-25 等） | 作为骨架默认值，`pollIntervalMs`/`pollMaxAttempts` 均可按调用覆写；请各作业任务按自己的 SLA 明确取值 |
| R3-Q5 | **入口页搜索词 `q` 是否随切工作区清理**：UI-01 只说「清除上一个工作区的草稿范围和轮询」，列表搜索词属页面级还是对象级临时查询无明文。 | UI-01 交互一致性 | S5 判为**页面级**、不清理（回退到 `/` 时保留用户上次的搜索更符合入口页语义）。若 COMMON.md 口径要求清，改一行即可 |
| R3-Q6 | **`ApiError.kind` 的五个非 problem 取值是前端自有词汇**（transport/aborted/payload/assertion/timeout），不是服务端 `code`。 | S6 文案、S8 断言 | 已严格区分：只有 `kind === "problem"` 才渲染服务端 `title`，其余五类 `title`/`code` 恒空，UI 只能用 COMMON.md 通用失败态；未把任何值伪装成服务端 code（守 Q4 裁定） |
