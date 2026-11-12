> **编排器修改标注（2026-11-13T01:54:49+08:00，依 D-011）**：本文中 4 处把「页面侧深链」标为 AC-034 的表述已由编排器更正为
> 引用 `spec/CampaignLab-SDD-v1.0/framework/FRONTEND.md:12`；AC-034 的 HTTP 负例本体归 M0-02。
> 修改者为编排器，**非 S1/S2 原作者（Ohm）**；其余内容未改动。

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
