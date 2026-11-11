# 游侠前端设计模板（浦发风格）V1.1 · 2026-11-05

> 用途：给**新建项目**当起点。它不是游侠原型的复制品，而是从现行原型母版**机械提取**的
> 设计令牌 + 组件样式 + 壳层运行时 + 图表函数，**不含业务逻辑与演示数据**。
>
> 来源母版（唯一真值）：`D:\ws\codex\游侠高仿真原型_S03S04场景版_20261105\S03_S04_运营后台_全链路联动工作台_V2.3_本地母版_浦发风格.html`
> 母版 SHA256 前16：`@@SRC16@@`　提取器：`tools\_build_template.py`　剔除清单：`tools\extract_report.json`

---

## 一、五分钟上手

| 我想… | 怎么做 |
|---|---|
| 新建一个页面 | 复制 `template_blank.html` + `css/` + `js/`，改 `viewP01/P02/P03` 与 `YX.init` 里的 `views` 配置 |
| 双击就能演示、不带文件夹 | 用 `template_blank_singlefile.html`（tokens+ui+charts+shell 已内联，零外链） |
| 看有哪些组件、怎么用 | 打开 `gallery_组件图鉴.html`：11 组组件，每组都有实时渲染 + 代码 + 应当/不要 |
| 换成别的银行配色 | 只改 `css/tokens.css` 的 `:root`，不要动 `youxia-ui.css` |
| 交付前自检 | 按 `checklist_交付前自检.md` 逐条打勾，再跑 `node _tpl_verify.mjs` |

`00_模板入口.html` 会实时重算本目录所有文件的 SHA256，用于确认「你手上这份就是我交付的那份」。

---

## 二、四层样式层序（改哪一层，影响谁）

| 层 | 名称 | 职责 | 换项目时 |
|---|---|---|---|
| L1 | 设计系统基座 hifi-design-system V1.0 | 令牌、卡片、表格、徽标、图表原语 | 保留 |
| L2 | 共用壳层 shell V1 | rail / appbar / pagebar / view / sheet / toast | 保留 |
| L3 | SPDB 浅色主题层 V4 | 主色覆盖为浦发深蓝 `#0048d8`、深色顶栏、组件密度 | 换肤主要动这里对应的令牌 |
| L4 | 工作台组件扩展 | 状态带、闸门、对象卡、时间线、迷你线 | 按需保留 |

`youxia-ui.css` 由这四层 `<style>` 原样拼接，头部注释标明层序。提取时**剔除了 20 条项目专用规则**
（`.screen.dp01…dp06`、`.screen.p5` 这类只服务某几个原型页的排版补丁），清单在
`tools/extract_report.json` 的 `dropped_project_rules`。剔除是有意的：模板不该带着
「某个后台页第 5 屏怎么排」这种知识。

---

## 三、设计令牌（由 `css/tokens.css` 读出，行尾 L# = 最终生效层）

### 中性色与主色
@@TBL_INK@@

### 语义色（只有两种合法用途：表达状态、表达风险等级）
@@TBL_SEM@@

### 排版、形状、图表色
@@TBL_MISC@@

正文基准 **13.5px / `--ink-900` / `--canvas`**（规则在 `youxia-ui.css` 内，`tokens.css` 只留 `:root` 变量）；所有数字用 `.num` 或 `.mono`
（`font-variant-numeric:tabular-nums`）。表格小数位、千分位能对齐，是"看起来专业"的第一要件，
比配色更管用。

---

## 四、组件族清单（类名 → 用途）

| 族 | 类名 | 用在哪 |
|---|---|---|
| 壳层 | `.shell .rail .rail-item .rail-sub .main .appbar .pagebar .seg .view .scrim .sheet .toast` | 全站骨架，DOM 结构固定 |
| 布局 | `.screen .pg .pg.c2/.c3/.c4 .cols .two .three .kpirow .objrow .span2` | 一屏之内的栅格 |
| 卡片 | `.card .card-h(.t .ic .meta) .card-b(.tight .flush .scroll .scroll-thin) .card-f(.note .tiny)` | 信息单元 |
| 指标 | `.kpi2(.ok .warn .bad .dim) .kpi(.good .bad .mid) .metric-line(.bar2 i)` | 数字与阈值 |
| 对象 | `.obj(.ok .req .bad .auth) .objrow` | 多对象并列状态总览 |
| 表格 | `.tbl(.compact) th/td(.r .wrap .mono .strong) tr(.roww .rowbad) .tbl-wrap` | 数据密集区 |
| 徽标 | `.tag(.ok .warn .bad .ai .sys .syn) .chip(.ok .warn .danger .info .violet .dark .syn .ver) .pill(.ok .warn .danger .info .gray .violet) .st(.ok .req .bad) .dot-s(.w .b .g) .badge-n(.g .w .b)` | 状态、口径、计数 |
| 提示 | `.banner(.info .warn .danger)+.ic` / `.okbox .warnbox .badbox .infobox` / `.hint` / `.empty` | 结论与告警 |
| 流程 | `.statusband(.sb-l .sb-flow .sb-node .sb-r) .stepper(.sp.done/.now/.block) .tl(.tl-i .done .warn .bad .trim) .gates/.gate(.ok .warn .bad) .gate2/.gc .seg4x/.sg` | 状态机与审批链 |
| 控件 | `.btn(.btn-p .btn-s .btn-g .btn-d .btn-ok .btn-sm) .btnrow .chk(.ok .warn .bad)+.ci .inp .filterbar` | 操作 |
| 图表 | `svg.chart .legend .ln .ax .axb .grid` | 由 JS 生成，见下节 |

---

## 五、图表 API（`js/youxia-charts.js`，零依赖，函数体从母版原样搬运）

```js
lineChart(series, labels, {w,h,min,max,dec,threshold,area,legend})  // series:[{name,color,data,fill,width,dash}]
hbars(items, {w,rh,pl,pr,max})      // items:[{l,v,c,t}]  ⚠ 只画正值：负值被 Math.max(2,bw) 夹成 2px 短线
columns(items, {w,h,max})           // items:[{l,v,t,c,dim}]
stacked(segs, {w,h})                // segs:[{l,v,c}]
donut(items, {w,h,r,sw,center,sub,legend})   // items:[{l,v,c,t,dash}]
radar(items, {w,h,r})               // items:[{l,v}]，v 是 0..100，单序列（多序列会互相覆盖）
spark(data, {w,h,color})
svg(w, h, inner, cls)               // 底层：viewBox + width:100%
PAL                                   // 7 色基线色板（母版未引用，留给新项目）
```

格式化与徽标：`esc pad nf pct n2 pc ii pp stTag bandTag kpi objCard synRow`
统计：`normCdf twoProp srmTest sumBy wavgBy`（`twoProp` 用非合并方差，`p` 一定落在 0..1；`pp(0.0079)` → `+0.79pp`）

**三条硬规矩**（违反过就会在演示当场翻车，自检已加门禁）：

1. 缺数传 `null` 或直接写 `—`，**禁止用 0 顶替**。0 会让折线假跌到零轴，读者会当成业务下滑。
2. 小图（`donut/radar/spark`，viewBox 宽 ≤260）**必须包一层定宽 div**：
   `'<div style="flex:none;width:132px">'+donut(...)+</div>'`。
   SVG 是 `width:100%` 的弹性项，放进 `.flex`/`.two` 会抢满宽度，把兄弟节点压成 0 宽。
3. 不要把图表导出成 PNG 贴图，数据一改就对不上。

---

## 六、壳层 API（`js/youxia-shell.js`）

```js
YX.init({ start:"p01",
          views:{  id:{title,sub,group,segs,fn} },
          sheets:{ id:function(){return html} },
          hooks:{ act(name,el), afterRender(cfg), beforeNav(id) } });
YX.nav(id)  YX.render()  YX.say(html,cls,ms)  YX.openSheet(id)  YX.closeSheet()  YX.register(id,cfg)
```

声明式交互（不写 JS）：`data-nav` 切视图 · `data-open` 开抽屉 · `data-close`/点遮罩/Esc 关闭 ·
`data-say` 轻提示 · `data-act` 交给 `hooks.act`。

长页规则：视图根写 `<div class="screen v2scroll">`，`render()` 会自动给 `.view` 加 `.vscroll`
（`.view.vscroll>.screen{height:auto}`、`.pg{flex:0 0 auto;align-content:start}`），
否则卡片被 flex 压扁、内容溢出到卡片外。这条是上一轮真实修 bug 换来的，别绕开它。

---

## 七、哪些东西**故意没有**放进模板

| 没进模板 | 原因 |
|---|---|
| S01 副驾建议卡、S02 接管队列、S03 联运、S04 偏好、D 后台的业务页 | 是业务实现，不是通用组件 |
| `.lk-*` 联动沙盘、`.phone/.scr/.pst/.pcard` 手机预览、`.demo-*` 演示控制、`STEPS/goStep/applyStory` | 只为"演示完整业务故事"服务，新项目拿去只会碍事 |
| 合成数据 `SY`、`mById/svcById/ragBy` | 与游侠数据结构绑死；模板保持数据无关 |
| 20 条 `.screen.dp0X/.screen.p5` 规则 | 项目专用排版补丁，见 `extract_report.json` |

需要这些时回母版复制，**不要改模板**——模板一改，所有基于它的新项目都被污染。

---

## 八、换肤指引（三步）

1. 改 `tokens.css` 的 `--brand-500/600/700/100/50`、`--canvas`、`--c1..--c6`；
2. 深色顶栏在 L3 的 `.appbar{background:linear-gradient(...)}` 与 `.rail-item.on`；要改就只在 L3 加覆盖，不要改 L1/L2；
3. 语义色（ok/warn/danger/info/violet）不要当品牌色用；`--danger-*` 只用于已触发/失败/禁止。

---

## 九、产物清单与哈希

@@FTAB@@

> 上表刻意不含 `README_设计与使用说明.md` 与 `00_模版入口.html`：文件不能记录自己的哈希（写入即失效）。完整清单以 `00_模版入口.html` 的实时校验结果为准。

复现：`python -X utf8 tools\_build_all.py`（提取 → 起手页 → 图鉴 → 单文件合并 → 类名契约 → 双加号 → node --check）
浏览器验证：`node D:\ws\codex\youxia_ai_platform\web\_tpl_verify.mjs`（76 项断言：0 console 错误、无 NaN 属性、
无容器溢出、标签配对、小图定宽、路由/抽屉/折叠）

---

## 十、已知限制（诚实清单）

1. `hbars` 不支持负值（源码 `Math.max(2,bw)`），要画正负对比请用 `columns` 或自行加零线。
2. `radar` 只支持单序列，且 `v` 必须是 0..100；`donut` 是描边环不是填充扇形，中心只有两行文字位。
3. `PAL` 在母版里定义了但没被引用。模板保留它是给新项目的默认色板，**不代表**原型出图用的就是它。
4. 状态徽标有两套并行体系：`.tag`（L1，`stTag()` 生成）与 `.st`（L4，原型页手写）。同一页只用一套，混用会出现两种高度。
5. `.tl` 时间线在 L1 与 L4 各定义一次（`::before` 圆点 + `.d` span），实际以 L4 为准；新项目照图鉴写法用 `.d`。
6. 只在 1600×950 与 1280×800 两档验证过，更窄视口需自行加断点（母版没有响应式）。
7. 本模板是**样式与交互骨架**，不含权限、审计、埋点；接真实系统时这些必须在后端与页面动作层补上。

---

## 十一、修订记录

| 版本 | 日期 | 改动 | 影响 |
|---|---|---|---|
| V1.0 | 2026-11-05 | 首次从 V2.3 母版机械提取交付 | — |
| V1.1 | 2026-11-05 | `tokens.css` 改为**只含 `:root` 变量**：原先放在这里的 `body` 基准排版规则与 `.num,.mono` 数字归一化规则下移到 `youxia-ui.css` 末尾的「L1 归一化」段 | 层叠结果不变（已用元素级重绘回归验证）；换肤时不用再看 `tokens.css` 里混入的选择器规则 |

**V1.1 为什么要改**：换品牌色时工程师只会打开 `tokens.css`。里面残留 `body{}` / `.num,.mono{}` 这类选择器规则，
就会出现「改了主色没改排版」或「想改字号却不敢动令牌文件」。现在职责划干净：
`tokens.css` = 变量，`youxia-ui.css` = 规则，`youxia-project.css`（项目侧）= 页面级覆盖。
