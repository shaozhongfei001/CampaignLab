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

## 4. 一致性检查（M0-03 出口条件）

1. 在 `web/src` 内检索六位十六进制色值，排除 `styles/tokens.css` 后应为空 —— 组件内不得写死色值。
2. Element Plus 覆盖只出现在 `web/src/styles/element-theme.css`；项目级样式覆盖只出现在 `web/src/styles/project.css`。
3. 组件视觉与 `spec/frontend-template-spdb-v1.1/gallery_组件图鉴.html` 逐族对照，走查截图存 `evidence/M0/ui-gallery/`。
4. 对比度断言进 Vitest：正文、次要、表头、状态文字对白底与对画布分别不低于 4.5:1。
