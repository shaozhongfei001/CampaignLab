# 令牌映射表（ADR-003 实施面）

用途：把 [ADR-003](../decisions/ADR-003-frontend-design-baseline.md) 的裁定值落成三处一致的实现映射 —— 项目 CSS 变量（唯一真值）→ Element Plus 主题变量 → ECharts 主题色板。改颜色只改本表与 `web/src/styles/tokens.css`，组件内不得写死色值。

模板令牌来源为 `spec/frontend-template-spdb-v1.1/css/tokens.css`；`COMMON.md` 指 `spec/CampaignLab-SDD-v1.0/ui/COMMON.md`。对比度为白底实测值。

## 1. 基础令牌

| 项目变量 | 裁定值 | 来源 | Element Plus 覆盖 | 用途 |
|---|---|---|---|---|
| `--cl-brand-700` | #003bb3 | 模板 `--brand-700` | `--el-color-primary-dark-2` | 按下态 |
| `--cl-brand-600` | #0048d8 | 模板 `--brand-600` | `--el-color-primary` | 主动作、链接、选中 |
| `--cl-brand-500` | #3368e0 | 模板 `--brand-500` | `--el-color-primary-light-3` | 焦点线、次级链接（5.00 AA） |
| `--cl-brand-100` | #dbe6ff | 模板 `--brand-100` | `--el-color-primary-light-8` | 选中底、标签底 |
| `--cl-brand-50` | #eef3fe | 模板 `--brand-50` | `--el-color-primary-light-9` | 提示底、行 hover |
| `--cl-ink-900` | #1a2438 | 模板 `--ink-900` | `--el-text-color-primary` | 正文（15.52 AAA） |
| `--cl-ink-700` | #4a5568 | 模板 `--ink-700` | `--el-text-color-regular` | 次要文字（7.53 AAA） |
| `--cl-ink-600` | #4a5568 | 模板 `--ink-600` | — | 表头文字专用档，替代 ink-500 |
| `--cl-ink-500` | #7a8899 | 模板 `--ink-500` | `--el-text-color-placeholder` | 仅禁用态与非文本图标（3.61，禁用于小字） |
| `--cl-ink-300/200/100/50` | #d0d6e0 / #e8ecf4 / #f0f4fc / #f7f9fd | 模板同名 | `--el-border-color-*` / `--el-fill-color-*` | 边框、分割、填充 |
| `--cl-canvas` | #f5f7fb | 模板 `--canvas` | `--el-bg-color-page` | 页面底 |
| `--cl-card` | #ffffff | 模板 `--card` | `--el-bg-color` | 卡面 |
| `--cl-line` | #e8ecf4 | 模板 `--line` | `--el-border-color` | 分割线 |
| `--cl-nav-grad` | linear-gradient(90deg,#0B2440,#123B63) | 模板 L3 `.appbar` | — | 顶栏（白字 15.61 AAA） |
| `--cl-ok-text` | #176A48 | COMMON.md | `--el-color-success` | 成功文字与图标（6.58 AA） |
| `--cl-warn-text` | #875900 | COMMON.md | `--el-color-warning` | 警示文字与图标（6.07 AA） |
| `--cl-danger-text` | #A53232 | COMMON.md | `--el-color-danger` | 错误文字与图标（6.77 AA） |
| `--cl-ok-600/100/50` | #18a890 / #d7f2ec / #eef9f6 | 模板 | `--el-color-success-light-*` | 仅填充与徽标底 |
| `--cl-warn-600/100/50` | #f39c12 / #fdeccd / #fff8ec | 模板 | `--el-color-warning-light-*` | 仅填充与徽标底 |
| `--cl-danger-600/100/50` | #e74c3c / #fbdcd8 / #fdf3f1 | 模板 | `--el-color-danger-light-*` | 仅填充与徽标底 |
| `--cl-info-600/100/50` | #0048d8 / #dbe6ff / #eef3fe | 模板 | `--el-color-info-*` | 范围与待补提示 |
| `--cl-radius-sm/md/lg` | 4px / 8px / 12px | 模板 `--r-*` | `--el-border-radius-base: 8px` | 徽标 / 控件 / 卡片 |
| `--cl-shadow-1/2/3` | 模板 `--sh-1..3` | 模板 | `--el-box-shadow*` | 卡片 / 浮层 / 抽屉 |
| `--cl-topbar-h` | 56px | COMMON.md（模板 48px） | — | 顶栏高 |
| `--cl-rail-w` / `--cl-rail-w-collapsed` | 216px / 64px | COMMON.md（模板 196/58） | — | 左导航 |
| `--cl-space-1..6` | 4 / 8 / 12 / 16 / 24 / 32px | COMMON.md 边距体系 | — | 间距；列间距与卡片间距 16px |
| `--cl-row-h` / `--cl-row-h-dense` | 40px / 36px | COMMON.md（模板约 33px） | — | 表格行高 |
| `--cl-btn-h` / `--cl-btn-h-sm` | 36px / 32px | COMMON.md + 模板 `.btn-sm` | `--el-component-size*` | 主按钮 / 表内小按钮 |
| `--cl-drawer-w` | 480px（窄屏全宽） | COMMON.md | — | 证据抽屉 |
| `--cl-dialog-w` | 520px | COMMON.md | — | 确认对话框 |
| `--cl-font-sans` | Inter, Noto Sans CJK SC, Microsoft YaHei, system-ui, sans-serif | 裁定（模板栈前置 Noto） | `--el-font-family` | 正文 |
| `--cl-font-mono` | JetBrains Mono, Cascadia Code, Consolas, monospace | 模板 `--font-mono` | — | 编号、证据号 |
| `--cl-fs-body/-label/-table/-table-dense` | 14 / 13 / 13 / 12.5px | 裁定 | `--el-font-size-base` | 字号档位 |

数字一律加 `font-variant-numeric: tabular-nums`（模板 `.num` / `.mono` 规则）；缺值显示 `—` 并给出原因。

### 1.1 令牌展开规则（Q-S3-D 裁定 · 2026-11-13）

Element Plus 需要比本表更细的档位（`light-3/5/7/8/9`、`dark-2` 等）。展开时**只允许**：

1. **同族单调复用**：EP 的细分档一律映射到本表**同色族已有档位的值**，且映射必须保持明度
   单调（EP 档位越浅 → 取值越接近白）；不得跨族借色。
2. **绝不引入表外色值**：任何新出现的六位十六进制 / `rgb()` / `hsl()` 都视为越界，由
   `web/tests/unit/tokens-guard.spec.ts` 的扩展门禁判红（`web/src/**` 内除
   `styles/tokens.css` 外不得出现任何色值字面量，即 §4 第 1 条）。
3. **无对应令牌者保持 EP 默认**：本表未裁定取值的 EP 变量（尺寸、字号等）一律保持 EP 默认值
   并标注 `PENDING_OWNER`，登记于 §5.3 与 `orchestrator/defects/D-017.md`，任何 lane
   不得自行发明取值。

唯一有记录的例外是 `--el-color-*-rgb` 裸数字三元组，硬条件见 §5.2。

## 2. 图表色板（ECharts 主题）

| 序 | 变量 | 值 | 白底对比度 | 使用限制 |
|---|---|---|---|---|
| c1 | `--cl-c1` | #0048d8 | 7.20 AAA | 无 |
| c2 | `--cl-c2` | #3368e0 | 5.00 AA | 无 |
| c3 | `--cl-c3` | #18a890 | 2.98 FAIL | 须配数据标签或等义表 |
| c4 | `--cl-c4` | #f39c12 | 2.19 FAIL | 同上，且不得单独承载「警示」语义 |
| c5 | `--cl-c5` | #60c0a8 | 约 2.4 FAIL | 仅填充或次要序列 |
| c6 | `--cl-c6` | #e74c3c | 3.82 仅大字 | 仅「已触发 / 失败 / 禁止」 |

规则：语义色不得当装饰色（模板红线）；每个图表必须提供可切换的等义表格（COMMON.md）；主题统一开启 `aria.decal` 与数据标签，补偿 c3/c4/c5 的对比度不足。M3 的贡献拆解需正负对比，一律用 ECharts 柱状图（模板 `hbars` 不支持负值，已弃用）。

## 3. 断点（模板缺失，项目新增）

| 断点 | 行为 |
|---|---|
| 大于 1100px | rail 216px，12 列栅格，主内容左右 24px，内容区最大 1440px 居中 |
| 小于等于 1100px | rail 折至 64px 图标列并提供标签提示，左右内边距 16px，双列可折叠 |
| 小于等于 800px | rail 改抽屉，主内容单列，数据表在自身区域横滚，证据抽屉全宽 |

设计基准 1440×900。验证档位：1440×900、1280×800、1024×768、800×600（保留模板原验证档 1600×950）。

三个阈值落成 CSS 变量（Q-S3-C 裁定 · 2026-11-13）。CSS 自定义属性不能直接写进 `@media`
条件，故落地方式为「**变量是唯一真值，媒体查询字面量必须与变量值一致**」：

| 变量 | 值 | 对应上表行为 |
|---|---|---|
| `--cl-bp-rail-collapse` | 1100px | rail 由 216px 折至 64px 图标列的阈值 |
| `--cl-bp-rail-drawer` | 800px | rail 改抽屉、主内容单列、表格自身横滚的阈值 |
| `--cl-content-max` | 1440px | 内容区最大宽度（大于 1100px 档居中） |

一致性断言随 Shell 布局子任务（M0-03/S5）落地，届时守卫须校验每个 `@media` 断点字面量都能
在本表找到同名变量且取值相等；在 S5 之前不得出现写死像素的媒体查询。

## 4. 一致性检查（M0-03 出口条件）

1. 在 `web/src` 内检索六位十六进制色值，排除 `styles/tokens.css` 后应为空 —— 组件内不得写死色值。
2. Element Plus 覆盖只出现在 `web/src/styles/element-theme.css`；项目级样式覆盖只出现在 `web/src/styles/project.css`。
3. 组件视觉与 `spec/frontend-template-spdb-v1.1/gallery_组件图鉴.html` 逐族对照，走查截图存 `evidence/M0/ui-gallery/`。
4. 对比度断言进 Vitest：正文、次要、表头、状态文字对白底与对画布分别不低于 4.5:1。
   **断言归属（Q-S3-F 裁定 · 2026-11-13）**：只依赖令牌 hex 的**纯计算型**对比度断言归
   M0-03/S3（`web/tests/unit/tokens-guard.spec.ts`，`environment: node`，已落地）；需要
   `getComputedStyle` 的 **DOM 型**断言（EP 变量在真实组件上的生效值）归 M0-03/S8，届时再引入
   jsdom/happy-dom，不得为赶 S3 提前改 `environment`。4.5:1 的合规例外见 §4.5，
   数字来源与复算公式见 §5.4。


### 4.5 WCAG 1.4.3 豁免清单（Q-S3-E(b) 裁定 · 2026-11-13）

下表两档低于 4.5:1 但**合规**，依 WCAG 2.1 SC 1.4.3 对 disabled 与 incidental 文本的豁免：

| EP 变量 | 绑定令牌 | 取值 | 对白底 | 对画布 | 豁免依据 |
|---|---|---|---|---|---|
| `--el-text-color-placeholder` | `--cl-ink-500` | #7a8899 | 3.6150 | 3.3705 | 占位提示非必需信息，输入后即被真实文本取代；≥3.0 另满足 SC 1.4.11 非文本对比度 |
| `--el-text-color-disabled` | `--cl-ink-500` | #7a8899 | 3.6150 | 3.3705 | SC 1.4.3 明确豁免禁用态控件 |

留痕为**双份，缺一即判红**：① `element-theme.css` 对应声明行的同行注释；② 守卫断言
「豁免注释在位」。豁免清单只允许这两条，新增必须先改本表再改代码。

其余文字档**一律不得豁免**，实测值（编排器按 §5.4 公式独立复算）：

| 角色 | 绑定令牌 | 取值 | 对白底 | 对画布 |
|---|---|---|---|---|
| 正文 `--el-text-color-primary` | `--cl-ink-900` | #1a2438 | 15.5167 | 14.4674 |
| 常规 `--el-text-color-regular` | `--cl-ink-700` | #4a5568 | 7.5256 | 7.0167 |
| 次要 `--el-text-color-secondary` | `--cl-ink-700` | #4a5568 | 7.5256 | 7.0167 |
| 成功文字 | `--cl-ok-text` | #176A48 | 6.5797 | 6.1348 |
| 警示文字 | `--cl-warn-text` | #875900 | 6.0709 | 5.6603 |
| 错误文字 | `--cl-danger-text` | #A53232 | 6.7695 | 6.3117 |

**`--el-text-color-secondary` 必须绑 `var(--cl-ink-700)`**：EP 默认值 `#909399` 实测仅
3.0795（白底）/ 2.8712（画布），两档均 < 4.5，直接违反本节；`--cl-ink-500`
（3.6150 / 3.3705）同样不合格，故次要文字不得降到 ink-500。层次说明：`--cl-ink-600` 与
`--cl-ink-700` 同值，regular 与 secondary 的层次只能由字号（14px / 13px）承载，这是本表既有约束。

> 更正留痕（2026-11-13）：编排器早前在账本中把 EP 默认 secondary `#909399` 记作「2.85:1」，
> 那是**画布档**的数字（精确值 2.8712），白底档为 3.0795。两档均远低于 4.5，
> 「必须覆盖」的裁定结论不变，此处仅更正数字口径，不改写历史测量值。

## 5. Element Plus 覆盖的特殊裁定

### 5.1 `--el-color-error*` 归入 danger 族（Q-S3-E(a)）

EP 同时存在 `danger` 与 `error` 两套语义变量。本项目**不新增红色**：`--el-color-error`、
`--el-color-error-light-*`、`--el-color-error-dark-2` 一律绑 `--cl-danger-*` 同族令牌，
取值与 `--el-color-danger*` 完全一致，使「表单校验错误」与「危险操作」视觉同色
（符合 ADR-003「语义色不得当装饰色」的红线）。

### 5.2 `--el-color-*-rgb` 三元组为唯一有记录例外（Q-S3-E(c)）

EP 的遮罩与透明叠加需要 `R, G, B` 形式的**裸数字三元组**，无法写成 `var(--cl-*)`。
这是 §1.1 第 2 条的唯一例外，硬条件三条，缺一即判红：

1. 每条声明必须在同行注释写出换算出处（`/* 换算自 --cl-xxx */`）；
2. 守卫从 `tokens.css` 解析对应令牌 hex，机械换算成 `R, G, B` 后逐条比对；
3. 守卫断言「已复算条数 == `-rgb` 声明条数」，防止只换算一部分。

权威值（编排器独立复算，与 `element-theme.css` 现值逐字一致）：

| 变量 | 三元组 | 换算自 |
|---|---|---|
| `--el-color-primary-rgb` | 0, 72, 216 | `--cl-brand-600` #0048d8 |
| `--el-color-success-rgb` | 23, 106, 72 | `--cl-ok-text` #176A48 |
| `--el-color-warning-rgb` | 135, 89, 0 | `--cl-warn-text` #875900 |
| `--el-color-danger-rgb` | 165, 50, 50 | `--cl-danger-text` #A53232 |
| `--el-color-error-rgb` | 165, 50, 50 | `--cl-danger-text` #A53232（见 §5.1） |
| `--el-color-info-rgb` | 0, 72, 216 | `--cl-info-600` #0048d8 |

### 5.3 未覆盖项：保持 EP 默认 + PENDING_OWNER（Q-S3-E(d) · D-017）

EP 的尺寸与字号令牌中无对应项目令牌者（`--el-component-size-large`、
`--el-font-size-extra-small` / `-medium` / `-large` / `-extra-large` 等）一律**保持 EP 默认值**，
在声明处标注 `PENDING_OWNER`，并登记于 `orchestrator/defects/D-017.md`。
D-017 必须在 **M0-03b 公共件冻结前**关闭；冻结后改值须走 CR（手册第 7 节）。

### 5.4 对比度复算公式（本节全部数字的来源，可复跑）

WCAG 2.1 相对亮度：对 8bit 通道值 `C8` 令 `C = C8 / 255`；
`Clin = C / 12.92`（当 `C <= 0.04045`），否则 `Clin = ((C + 0.055) / 1.055) ** 2.4`；
`L = 0.2126 * Rlin + 0.7152 * Glin + 0.0722 * Blin`；
`对比度 = (L亮 + 0.05) / (L暗 + 0.05)`。

基准背景：白底 `#ffffff`（L = 1.000000）、画布 `#f5f7fb`（L = 0.928990）。
本表与 §1/§2 中所有对比度数字均由编排器按此公式独立复算（2026-11-13），与
`web/tests/unit/tokens-guard.spec.ts` 的断言同源；引用时以本公式重算为准，禁止转述近似值。
