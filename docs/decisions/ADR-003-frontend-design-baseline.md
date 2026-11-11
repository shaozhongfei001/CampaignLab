# ADR-003 前端设计基线与令牌裁定

日期 2026-11-12。状态 `PROPOSED`：品牌色、导航结构、语义色三项待项目负责人裁定，其余技术项由技术负责人裁定。

## 背景

1. 发起人在 SDD 交接包之外追加提供《前端设计模板（浦发风格）V1.1》。两份输入均已按字节原样入库：
   - `spec/CampaignLab-SDD-v1.0/`（版本 1.0.0，入库后 `python3 qa/verify_package.py` 为 `PACKAGE PASS 6/6`，`qa/verify_schemas.py` 为 `SCHEMA PASS`）
   - `spec/frontend-template-spdb-v1.1/`（8 个产物 SHA256 前 16 位与其 `README_设计与使用说明.md` §九 记录逐项一致）
2. 模板由母版 `S03_S04_运营后台_全链路联动工作台_V2.3_本地母版_浦发风格.html`（SHA256 前 16 `f1b54b203443db54`）机械提取，含四层样式（L1 hifi-design-system 基座 → L2 壳层 shell V1 → L3 SPDB 浅色主题 V4 → L4 工作台组件扩展）、473 个 CSS 类、壳层运行时 `YX.*`、零依赖 SVG 图表，不含业务逻辑与演示数据。
3. 交接包 `framework/FRONTEND.md` 与 `contracts/dependencies.json` 已把前端栈定为 Vue 3.5 + TypeScript strict + Vite + Element Plus + ECharts + Vitest + Playwright（ADR-001 已批准）。模板栈为原生 JS + 自研 CSS/图表，两者冲突。
4. 按 `AGENTS.md` 的裁定优先级，模板属包外输入，优先级低于 ADR-001 与包内契约，须经本 ADR 提级后方可作为设计依据。

## 决定：采纳视觉语言，不采纳运行时

**采纳**

- `css/tokens.css` 的设计令牌体系（`:root` 变量，四层生效关系已在文件内标注）
- 四层样式的视觉语言与组件视觉规格，以 `gallery_组件图鉴.html` 的 11 族组件作为走查基准
- `checklist_交付前自检.md` 的 A 段机器门禁、C 段内容红线、E 段环境坑

**不采纳**

- `js/youxia-shell.js` 壳层运行时（hash 路由、`data-nav/data-open/data-say/data-act` 声明式交互、`YX.*` 全局）
- `js/youxia-charts.js` 的 SVG 图表原语（`lineChart/hbars/columns/stacked/donut/radar/spark`）
- `css/youxia-ui.css` 规则本体作为生产样式表

**实现方式**

- 裁定后的令牌落到 `web/src/styles/tokens.css`，作为项目侧唯一令牌源；项目级覆盖写 `web/src/styles/project.css`（对应模板 README §十一 所述 `youxia-project.css` 职责）
- Element Plus 通过 CSS 变量主题化对齐令牌；ECharts 使用同一色板生成主题
- 组件按 `framework/FRONTEND.md` 的 pages / features / components / composables / api / router / styles 分层，模板 11 族映射为 Vue 组件，见 `docs/design/page-component-map.md`
- 模板与 `youxia-ui.css` 仅作视觉真值参照，不参与构建、不被 import

## 理由

1. 26 条路由携带 `workspace_id` 与资源 ID 的深链接、404 回退、切工作区清理轮询与失效选择、ETag/412 冲突、202 作业轮询、`Idempotency-Key`、由 OpenAPI 生成类型客户端、WCAG 2.2 AA —— 在原生壳层上需自研路由、状态、表单校验、表格、图表等义表与类型层，工作量与风险全部落在 M0–M5 关键路径。
2. `contracts/dependencies.json` 是 M0-01 产出真实 npm 锁的输入。改栈等于推翻 ADR-001/ADR-002，代价远高于把令牌移植进 Vue。
3. 模板自身门禁未闭合：`tools/class_contract.json` 的 `used_not_defined` 有 9 项（`btn-pri`、`btn-xs`、`dp02`、`dp04`、`dp06`、`four`、`p5`、`pkhead`、`veto2`），而其 checklist A 段要求 `_check_used.py` 输出 `UNDEFINED=[]`；另有 `.tag`(L1) 与 `.st`(L4) 两套状态徽标、`.tl` 时间线在 L1/L4 各定义一次。在 26 页规模下会放大，正好由 FRONTEND.md「公共组件各只有一个实现」收敛。
4. 模板图表有明确能力缺口（`hbars` 不支持负值、`radar` 单序列且 v 须为 0..100、`donut` 为描边环），而 M3 的异常诊断与贡献拆解需要正负对比与多序列。

## 令牌裁定

裁定原则：**文字与图标用 AA 达标色；填充与徽标底色用模板浅色阶；品牌色与图表色板用模板值。** 对比度为白底（`#FFFFFF`）实测值，按 WCAG 2.1 相对亮度公式计算。

| 项 | COMMON.md | 模板 | 实测对比度 | 裁定 |
|---|---|---|---|---|
| 主色 / 主动作 | #2456C8（6.48 AA） | `--brand-600` #0048d8 | 7.20 AAA | **#0048d8**，浦发风格识别要素 |
| 焦点线 | 2px #2456C8 | 2px `--brand-500` #3368e0 | 5.00 AA | **2px #3368e0 + offset 2px**，沿用模板 `:focus-visible` |
| 正文 | #172942（14.66 AAA） | `--ink-900` #1a2438 | 15.52 AAA | **#1a2438** |
| 次要文字 | #4F6177（6.35 AA） | `--ink-700` #4a5568 | 7.53 AAA | **#4a5568** |
| 表头 / 占位 | — | `--ink-500` #7a8899 | 3.61（canvas 上 3.37）仅大字 | **表头改 `--ink-600` #4a5568**；ink-500 只用于禁用态与非文本图标 |
| 画布 / 卡面 / 分割 | #F3F6FA / #FFF / #DCE4ED | `--canvas` #f5f7fb / `--card` #fff / `--line` #e8ecf4 | ink-700 on canvas 7.02 AAA | **采纳模板** |
| 成功（文字/图标） | #176A48 | `ok-700` #148f7b / `ok-600` #18a890 | 6.58 AA / 4.00 仅大字 / 2.98 FAIL | **#176A48**；ok-600 禁止用于文字 |
| 警示（文字/图标） | #875900 | `warn-700` #c87f0a / `warn-600` #f39c12 | 6.07 AA / 3.23 仅大字 / 2.19 FAIL | **#875900**；warn-600 禁止用于文字 |
| 错误（文字/图标） | #A53232 | `danger-700` #c0392b / `danger-600` #e74c3c | 6.77 AA / 5.44 AA / 3.82 仅大字 | **#A53232** |
| 语义填充 / 徽标底 | #F0F5FF / #FFF4D8 | `*-50` / `*-100` 各四组 | 700 on 50：ok 3.72、warn 3.06、danger 4.99、brand 8.30 | **采纳模板浅色阶**，其上文字一律用本表裁定的深色 |
| 导航结构 | 深色左导航 #14243B、216px | 白底 rail 196px（折叠 58px）+ 深蓝渐变顶栏 #0B2440→#123B63、appbar 48px | 白字 on #14243B 15.61 AAA | **采纳模板结构**（白 rail + 深蓝 appbar），尺寸取 **rail 216px / appbar 56px** 以对齐 12 列栅格与 1440×900 画布 |
| 密度 | 正文 14px、表格行高 40px（密集 36px） | body 14px、`.tbl` 12.5px、td 7px/8px ≈ 33px | — | **正文 14px；业务表 13px + 行高 40px；密集表 12.5px + 36px** |
| 按钮 | 高 36px，每区最多一个主动作 | `.btn` 32px，checklist 同样要求一屏一个 `.btn-p` | — | **主按钮 36px，表内小按钮 32px**；「唯一主动作」直接采纳为门禁 |
| 圆角 / 阴影 | 组件 8px | `--r-sm` 4 / `--r-md` 8 / `--r-lg` 12、`--sh-1..3` | — | **采纳模板三档**：卡片 12、控件 8、徽标 4 |
| 字体栈 | Noto Sans CJK SC 首选 | Inter / Segoe UI / PingFang SC / Hiragino / Microsoft YaHei | — | **`Inter, "Noto Sans CJK SC", "Microsoft YaHei", system-ui, sans-serif`**；等宽 `JetBrains Mono, Cascadia Code, Consolas, monospace`；保留 `font-variant-numeric: tabular-nums` |
| 图表色板 | — | `--c1..--c6` | c1 7.20 AAA、c3 2.98 FAIL、c4 2.19 FAIL（对白底） | **采纳为 ECharts 主题色板**；c3/c4 用于图形时须配数据标签或等义表（见未决项 3） |
| 断点 | ≤1100px 导航折 64px；≤800px 抽屉导航 + 单列 + 表横滚 | 仅 `max-width:1500px` 与两条 `max-height:940px` | — | **必须新增 ≤1100px 与 ≤800px 断点**；模板 README 自述母版无响应式 |

## 组件收敛：模板 11 族 → Vue 单一实现

| 模板族（代表类名） | Vue 组件 | 说明 |
|---|---|---|
| 壳层 `.shell .rail .appbar .pagebar .seg .view .scrim .sheet .toast` | `AppShell` `SideRail` `AppBar` `PageBar` `EvidenceDrawer` `useToast` | 路由由 vue-router 承担，`data-*` 声明式交互改为组件事件 |
| 布局 `.screen .pg .cols .two .three .kpirow .objrow` | `PageGrid` | 12 列栅格、列间距与卡片间距 16px |
| 卡片 `.card .card-h .card-b .card-f` | `CardPanel` | header/body/footer 插槽，`tight/flush/scroll` 变体 |
| 指标 `.kpi2 .kpi .metric-line` | `MetricCard` `MetricLine` | 缺值显示 `—` 并给出原因；分子分母与口径入证据抽屉 |
| 对象 `.obj .objrow` | `ObjectStatusCard` | 多对象并列状态总览 |
| 表格 `.tbl(.compact) .tbl-wrap` | `DataTable`（封装 `el-table`） | 行高 40/36、等宽数字、键盘排序、宽表冻结首列、默认 25 行游标加载 |
| 徽标 `.tag .chip .pill .st .dot-s .badge-n` | `StatusTag` `FlowState` `CountBadge` | 收敛 `.tag` 与 `.st` 双体系，一页只用一套 |
| 提示 `.banner .okbox .warnbox .badbox .infobox .hint .empty` | `AlertBanner` `EmptyState` | 空态须含当前筛选说明与创建/导入/清空入口 |
| 流程 `.statusband .stepper .tl .gates .gate2 .seg4x` | `StatusBand` `StepFlow` `Timeline` `GateCheck` | `.tl` 双重定义收敛为单实现，按图鉴的 `.d` 写法 |
| 控件 `.btn(.btn-p/.btn-s/.btn-g/.btn-d/.btn-ok/.btn-sm) .btnrow .chk .inp .filterbar` | `ActionButton` `TriStateCheck` `ScopeBar` + Element Plus 表单 | 危险按钮旁必须给后果说明；`ScopeBar` 为 COMMON.md 的公共范围条 |
| 图表 `svg.chart .legend .ln .ax .axb .grid` | `ChartWithTable`（ECharts 按需模块） | 强制提供等义表格切换，图表与表格共用同一服务器结果 |

## 门禁采纳（并入前端 CI）

**A 段机器门禁** → Playwright 断言 + Vitest 单测 + 类名契约检查：

- 0 个 `console.error` / `pageerror`
- 页面文本与 SVG 属性中不得出现 `NaN` / `undefined` / `[object Object]` / `Infinity`
- 视图渲染的 HTML 标签配对（div/table/tr/td/span 开合数量相等）
- 无横向溢出：任何元素右边界不得超出其卡片/分栏/表格容器
- 无 0 宽或 0 高图表容器（小图必须定宽包裹）
- 用到的每个 class 都能在样式源中找到定义（对应 `_check_used.py` 的 `UNDEFINED=[]`）
- 禁止「行尾 `+` 接行首 `+`」写法（会被解析为 `a + (+b)` 产生 NaN）

**C 段内容红线** → 禁字样扫描 + 评审清单：

- 禁用总括语：`监听`、`情绪识别`、`语气分析`、`生产就绪`、`冻结生效`
- **`已签署` / `已验收` 按 SDD 语境校准**：报告「已签认」是 `architecture/REPORTS.md` 定义的真实状态词，允许出现在状态徽标与签认记录中；禁止的是「N/N 已验收」「全部通过」这类无法核对的总括语
- 关联 ≠ 因果：观察结论不得写成「因为…所以…」
- 提交 ≠ 发布：按钮文案与状态词区分「已提交 / 待审批 / 已发布」
- 合成数据必须有可见标注（页头 SYNTHETIC 芯片或等价说明），且与生产口径分列
- 不得把摘要冒充原件：引用外部资料保留文件名与索引

**E 段环境坑** → 记入 `docs/design/frontend-pitfalls.md`，作为本仓库执行约定。

## 影响

1. `ui/COMMON.md` 的令牌表由本 ADR 裁定表取代。包内文件保持不可变，冲突处以本 ADR 为准；相关 AC 的视觉验收口径按裁定值执行。
2. M0-01 的 npm 锁须包含 Element Plus 与 ECharts 主题化所需依赖；M0-03 的路由壳与 UI-01 用 `AppShell` + `PageGrid` + `MetricCard` 落地。
3. 部署机需安装 `fonts-noto-cjk`（需 sudo），否则中文回退到默认无衬线，视觉走查结论不可用。
4. 模板的 `_tpl_verify.mjs`（76 项断言）位于包外 `D:\ws\codex\youxia_ai_platform\web\`，未随包入库；其断言项已转写为上述门禁，不引入该脚本本身。
5. `prototype/` 的 v0.1 原型（79 项断言）与本 ADR 无冲突，继续作为历史回归基线由 CI 复跑。

## 未决项（待项目负责人裁定）

1. 主色由 `#2456C8` 改为浦发深蓝 `#0048d8`，导航由深色左导航改为白 rail + 深蓝顶栏 —— 属品牌视觉裁定。
2. 语义色的文字层保留 SDD 深色（AA 达标）而非模板亮色。若坚持模板亮色，须接受 WCAG 2.2 AA 目标下调并留痕。
3. 图表中 `--c3 #18a890`（2.98）与 `--c4 #f39c12`（2.19）对白底不足 3:1，是否允许以数据标签与等义表补偿。

## 回退

裁定被否时回退到 `ui/COMMON.md` 与 `framework/FRONTEND.md` 原值，模板降级为纯参考件，不影响 M0 其余任务。
