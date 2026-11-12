# M0-03 · S3（令牌机械落地与一致性守卫）+ S4（类型客户端生成）执行证据

- lane：F（前端）· 子任务 S3 + S4 · critical=false · slack=8 · L 循环上限 3（实际用 2 轮）
- 执行时间：2026-11-13T03:15:29+08:00
- 仓库：WSL2 ext4 `/home/szf/dev/CampaignLab`（`/mnt/d` 下零安装零构建）
- `git rev-parse --short HEAD` → `b81f893`（rc=0）· 分支 `m0-framework`（rc=0）
- 开工时 HEAD=`42079fa`（派单所述）；作业期间编排器推进到 `b81f893`（wave1 Round 3 派单提交），本文件取证时 HEAD=`b81f893`。**HEAD 漂移为并行提交所致，非本 lane 动作**：`git log --oneline -3 -- web/src/styles/tokens.css web/src/api/types.ts web/tests/unit/tokens-guard.spec.ts` 为空，即 S3/S4 产物全部未入库、仍在工作树。
- 开工前工作树 CLEAN；本文件与 S3/S4 产物均留在工作树，**未做任何 git add/commit/push**（由编排器统一提交）

## 0. 环境（实测版本行）

| 工具 | 命令 | rc | 实测版本 |
|---|---|---|---|
| Node | `node -v` | 0 | v24.22.3 |
| npm | `npm -v` | 0 | 11.19.1 |
| openapi-typescript | `cd web && npx openapi-typescript --version` | 0 | v7.13.0（已在 devDependencies，**未改 package.json**） |
| vue-tsc | `cd web && npx vue-tsc --version` | 0 | Version 5.9.3 |
| vite | `cd web && npx vite --version` | 0 | vite/8.3.8 linux-x64 node-v24.22.3 |
| vitest | `cd web && npx vitest --version` | 0 | vitest/5.1.0 linux-x64 node-v24.22.3 |

Windows interop 规避：所有 npm/npx/node 调用前显式前置 `PATH=$HOME/.local/share/node/bin`（docs/design/frontend-pitfalls.md「Windows interop PATH」条），Node 为 Linux 版 v24.22.3。

## 1. PRE-3 活契约版本门禁（实算三方比对，不采信派单文本）

| 来源 | 字段 | 实算值 |
|---|---|---|
| `contracts/openapi.json`（`hashlib` 读 bytes，未整读进上下文） | `sha256` 前 16 位 | `592571099d638251` |
| 同上 | 完整 `sha256` | `592571099d63825188446e33d297befa8911554a77782b9318a34e328b33aec1` |
| 同上 | 字节数 | `443309` |
| 同上（首 600 字节定点正则） | `info.version` | `1.0.1` |
| `orchestrator/state.json → resume.self_check_gates_rc0.counts` | `live_openapi_sha16` | `592571099d638251` |
| 同上 | `live_openapi_bytes` | `443309` |
| 同上 | `live_openapi_info_version` | `1.0.1` |
| `orchestrator/handoff/M0-03.slice.json` | `source.openapi.sha16` | `592571099d638251` |
| 同上 | `source.openapi.bytes` | `443309` |
| 同上 | `spec_version`（**实际路径为切片顶层 `spec_version`，不在 `source.openapi` 下**） | `1.0.1` |

**结论：三方逐字一致，且等于 CR-002/ADR-006 重切后的期望值（sha16=592571099d638251 / bytes=443309 / spec_version=1.0.1）→ PRE-3 PASS，继续 S3/S4。**
手册 15.4 第 5 条的「切片 `source.openapi.sha16` == `contracts/openapi.json` 实算 sha16」同样成立。

## 2. S3 令牌机械落地

### 2.1 产物

| 文件 | 内容 | 实算规模 |
|---|---|---|
| `web/src/styles/tokens.css` | 唯一令牌真值，按 `docs/design/token-mapping.md` §1/§2/§3 机械落地 | `--cl-*` 定义 **68 条**（去重 68），六位十六进制出现 39 次 |
| `web/src/styles/element-theme.css` | `--el-*` ← `var(--cl-*)`（Q6 裁定：CSS 变量方案，未引入 `sass`） | `--el-*` 定义 **64 条**（去重 64），取值 64/64 全部为 `var(--cl-*)`，色值字面量 0 |
| `web/src/styles/project.css` | 项目级覆盖唯一文件（S3 只落令牌派生的最小基线层） | 自定义属性定义 0 条，色值/`rgba(` 0 次 |
| `web/src/main.ts` | 按 M0-03-design.md 2.1 顺序接线四个 CSS import | 见文件 |
| `web/tests/unit/tokens-guard.spec.ts` | 一致性守卫（vitest，node 环境，不触碰 DOM） | 5 用例：4 passed / 1 skipped（跳过原因见 4.2） |

条数由脚本实算（`re.findall(r"^\s*(--cl-[a-z0-9-]+)\s*:", css, re.M)`），非手数。

### 2.2 与 token-mapping.md 的机器对账（双向差集 + 逐值比对）

- `docs/design/token-mapping.md` §1 表「项目变量」列展开后共 **59** 个 `--cl-*` 名 → `MD 有 / CSS 缺 = []`（零缺失）。
- §1 全部值列（十六进制与 px 档）与 `tokens.css` 实际取值逐条比对 → **值不一致条数 = 0**。
- §2 图表色板 6 条（c1-c6）逐条比对 → **不一致 = 0**。
- `CSS 有 / MD 无` = 3 条断点变量（`--cl-bp-rail-collapse` 1100px、`--cl-bp-rail-drawer` 800px、`--cl-content-max` 1440px，来自 §3 断点表），另 6 条即 §2 的 c1-c6。变量名 S2 未枚举 → 见第 5 节 Q-S3-C。

### 2.3 rg 主门禁 / 扩展门禁（仓库根，命令原文与实测 rc）

```
$ rg -n '#[0-9a-fA-F]{6}' web/src --glob '!**/styles/tokens.css'
（无输出）
rc_rg_hex6 = 1     at 2026-11-13T03:12:29+08:00   输出行数 0
```

```
$ rg -n '#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(' web/src --glob '!**/styles/tokens.css'
（无输出）
rc_rg_ext = 1      at 2026-11-13T03:12:29+08:00   输出行数 0
```

两条均 rc=1（无匹配）即**期望结果**；`spec/**` 未被 import（`rg -c 'frontend-template-spdb|youxia' web/src` 无命中，ESLint 的 `no-restricted-imports` 同处红线亦为 rc=0 通过）。

### 2.4 守卫有效性探针（证明守卫不是空跑）

临时探针 `web/src/__guard_probe.ts`（内容含 `"#0048d8"` 与 `"rgba(0, 72, 216, 0.5)"`）：

| 步骤 | 命令 | 实测 rc | 关键输出 |
|---|---|---|---|
| 探针在位 | `cd web && npx vitest run tests/unit/tokens-guard.spec.ts` | **1** | 命中列表含 `web/src/__guard_probe.ts:1`、`:2`、`:3`（文件名+行号） |
| 删除探针后 | 同上 | **0** | 4 passed / 1 skipped |

探针文件已删除（`ls web/src` 复核：`App.vue api components composables features main.ts pages router styles vite-env.d.ts`，无残留）。

## 3. S4 类型客户端生成

### 3.1 生成命令与 rc

```
$ cd /home/szf/dev/CampaignLab/web && npx openapi-typescript ../contracts/openapi.json -o src/api/types.ts
✨ openapi-typescript 7.13.0
🚀 ../contracts/openapi.json → src/api/types.ts [213.5ms]
rc_gen1 = 0
```

CLI 形态先经 `npx openapi-typescript --version` 确认（v7.13.0，rc=0），未凭记忆猜参数；`package.json` / `package-lock.json` 未改动。

### 3.2 可复现性（gate：重跑 diff 为空）

| 次序 | 输出路径 | sha256 | 字节数 |
|---|---|---|---|
| 第 1 次（入仓库） | `web/src/api/types.ts` | `bddac66ccf9379e96238ff81b52f121494e893670a156b7290eb309401d990d5` | 194220 |
| 第 2 次（仅 `/tmp/types_rerun.ts`，未写进仓库） | `/tmp/types_rerun.ts` | `bddac66ccf9379e96238ff81b52f121494e893670a156b7290eb309401d990d5` | 194220 |
| 第 3 次（幂等复核，`/tmp/types2.ts`） | `/tmp/types2.ts` | 同上 | 194220 |

```
$ cmp -s web/src/api/types.ts /tmp/types_rerun.ts
rc_diff_empty = 0        # 三次生成逐字节相同 → 生成确定性成立，重跑 diff 为空
$ wc -l web/src/api/types.ts
5672
```

生成物头部为 `/** * This file was auto-generated by openapi-typescript. * Do not direct modifications. */` + `export interface paths {`，**不含时间戳**，故无需手工干预即复现（未手工编辑生成物）。

### 3.3 CR-002 定点自证：`listWorkspaces` query 不含 `status`

```
$ rg -n -A6 'listWorkspaces: \{' web/src/api/types.ts
2568:    listWorkspaces: {
2569-        parameters: {
2570-            query?: {
2571-                cursor?: string;
2572-                limit?: number;
2573-                q?: string;
2574-            };
rc_grep_listworkspaces = 0
```

query 参数只有 `cursor` / `limit` / `q`，**无 `status`**（与活契约该 op 的 parameters 实算值 `[cursor query, limit query, q query]` 一致）。
反向自证（CR-002 要求保留的合法响应字段未被误删）：

```
$ rg -n 'status: "READY" \| "DEGRADED"' web/src/api/types.ts
1053:            status: "READY" | "DEGRADED";
rc_health_status_kept = 0
```

`Health.status` 与 `Health.worker`（`"READY" | "OFFLINE"`，1057 行）均保留在生成物中。

## 4. 四条门禁（最终实测 rc + 时间戳）

| # | 命令 | 实测 rc | 时间戳 | 备注 |
|---|---|---|---|---|
| G1 | `npm --prefix web run typecheck` | **0** | 2026-11-13T03:12:25+08:00 | `vue-tsc --noEmit -p tsconfig.json`，严格开关（含 `exactOptionalPropertyTypes`）未关闭 |
| G2 | `npm --prefix web run lint` | **0** | 2026-11-13T03:12:26+08:00 | 无输出 |
| G3 | `npm --prefix web run test` | **0** | 2026-11-13T03:12:27+08:00 | 2 files / 8 passed + 1 skipped（跳过项见 4.2） |
| G4 | `npm --prefix web run build` | **0** | 2026-11-13T03:12:28+08:00 | 15 modules，`dist/assets/index-BNbSk9FG.css` 366.90 kB、`index-Cv9cf-cW.js` 62.82 kB |

### 4.1 失败历史（如实记录，L 循环第 1 轮）

首次全量跑门禁时 **G3 rc=1、G4 rc=1**，分类均为「实现缺陷」（非契约歧义、非环境问题、非测试期望错误）：

1. **G4 rc=1**：`[lightningcss minify] Unexpected token Delim('/')` —— 我在 `tokens.css` 的块注释里写了 `--glob '!**/styles/tokens.css'`，其中的星号斜杠序列提前终止了 CSS 注释。**修复**：改写该行注释、不含该序列（单点修复，只复跑 build → rc=0）。
2. **G3 rc=1（2 failed）**：我假设 `import.meta.glob` 能取到 `.css` 原文。实测（探针 `__glob_probe.spec.ts`，用后即删）vitest 默认 `css:false` 把 CSS 模块 stub 成空串：`?raw` 与 `?inline` 下三个 `.css` 文件 `length=0`，而非 CSS 文件正常（`/src/api/types.ts=191796`、`/src/main.ts=782`、`/src/App.vue=259`、`/src/vite-env.d.ts=38`）。**修复**：守卫改为自适应扫描（只扫拿到内容的文件）+ 把依赖 CSS 文本的那条断言写成 `it.runIf(cssReadable)`，读不到即**显式 skipped 留痕**，不做空洞通过；CSS 侧真值由 2.3 的两条 rg 门禁兜底。未改 `vitest.config.ts`、未新增依赖 → 该项升级为未决问题 Q-S3-A。

探针、临时文件均在 WSL `/tmp` 或已删除；`web/tests/unit/` 最终只剩 `project-baseline.spec.ts` 与 `tokens-guard.spec.ts`。

### 4.2 skipped 用例说明

`--cl-* 只在 tokens.css 定义；element-theme.css 的每个 --el-* 取值一律为 var(--cl-*)` —— 后半句需读 `element-theme.css` 文本，当前 vitest 配置读不到（4.1 第 2 条）。前半句（非 CSS 文件零 `--cl-*` 定义）已执行并通过。编排器裁定 Q-S3-A 后此条自动转为执行态。

## 5. 未决问题（S3/S4 不自行决定，交编排器裁定）

| # | 问题 | 现状处置 | 需要裁定什么 |
|---|---|---|---|
| Q-S3-A | vitest `css:false` 默认 stub 使 CSS 文件在测试里读不到原文（实测 length=0），守卫无法覆盖 CSS 侧；`node:fs` 又被 Q2（无 `@types/node`）挡住。 | 不改 `vitest.config.ts`；自适应扫描 + `it.runIf` 显式 skip；CSS 侧由仓库根两条 rg 门禁兜底（均 rc=1）。 | 批准 `test.css: true`（一行配置，无新依赖）或批准 `@types/node`（原 Q2）以改用 `node:fs` 递归扫描。二选一。 |
| Q-S3-B | 派单要求文件名 `web/tests/unit/tokens-guard.test.ts`，但 S1 的 vitest `include` 只收 `*.spec.ts`，`.test.ts` 不会被收集（等于守卫不跑）。 | 落地为 `tokens-guard.spec.ts`（可被收集），未改配置。 | 确认命名（设计文件 §7 S8 行写的是 `tokens.spec.ts`，我避让该名以免与 S8 相撞）。 |
| Q-S3-C | token-mapping 未枚举「断点变量」的变量名，而设计 §3 要求「断点变量按 §3」。 | 自定义 `--cl-bp-rail-collapse` / `--cl-bp-rail-drawer` / `--cl-content-max`（值 1100/800/1440px 逐字照 §3）。 | 认可命名或给出正式命名；改名只动 tokens.css 一处。 |
| Q-S3-D | token-mapping §1 的 `--el-*` 覆盖列写成 `*` 通配的族，EP 档位多于项目档位（EP 有 primary light-3/5/7/8/9 而表只给 3/8/9；success/warning/danger/info 各有 dark-2 + 5 个 light 档，表只给 600/100/50 三档）。 | 采用「同族档位单调复用」：表未列档就近复用相邻 `--cl-*` 档（如 `--el-color-primary-light-5: var(--cl-brand-500)`、`--el-color-*-dark-2: var(--cl-*-text)`），**绝不引入表外色值**，全部取值仍为 `var(--cl-*)`。 | 认可该展开规则；若判改只动 `element-theme.css` 一个文件。 |
| Q-S3-E | token-mapping 未覆盖的 EP 变量保持 EP 默认值，存在视觉残留风险：`--el-color-error*`（EP 默认 `#f56c6c`，用于表单校验/Badge，与 `--el-color-danger` 分列）、`--el-text-color-secondary`（`#909399`，对白底 2.85 不足 AA）、`--el-component-size-large`（40px）、`--el-font-size-{extra-small,small,medium,large,extra-large}`、`--el-color-*-rgb` 三元组（EP 内部用它组 `rgba()`，按「`--el-*` 取值一律 `var(--cl-*)`」规则无法表达）。 | 一律不覆盖，逐条列此。 | 需在 token-mapping.md 补行（尤其 `--el-color-error` 与 `--el-*-rgb`），S3 不自行发明档位。 |
| Q-S3-F | `docs/design/token-mapping.md` §4.4 要求「对比度断言进 Vitest」，但需读 CSS 文本且不能触碰 `getComputedStyle`（Q1）。 | 未在本轮实现；建议随 Q-S3-A 一并裁定后落到 `tokens.spec.ts`（S8 白名单已含该名）。 | 归属确认：S3 补写还是 S8 落地。 |
| Q-S4-A | 切片 `spec_version` 实际位于顶层 `spec_version`，而非派单文本所述 `source.openapi.spec_version`（`source.openapi` 只有 `path/bytes/sha16`）。 | 已按顶层值 1.0.1 比对，与 `contracts/openapi.json` 的 `info.version`、state 的 `live_openapi_info_version` 三者一致。 | 派单文本的路径描述需修正（不影响本轮结论）。 |

## 6. 交付边界自证

- 仅写入 `web/src/**`（`styles/tokens.css`、`styles/element-theme.css`、`styles/project.css`、`main.ts`、`api/types.ts`）、`web/tests/**`（`unit/tokens-guard.spec.ts`）、`evidence/M0/M0-03/**`（本文件）。
- `web/package.json` / `web/package-lock.json` / `web/*.config.*` / `web/tsconfig*.json` 未改动；`spec/**`、`contracts/**`、`src/**`、`migrations/**`、`orchestrator/**`、`scripts/**` 未改动（并行 lane 的 `orchestrator/tasks/**` 变更非本 lane 产物）。
- 未运行 `uv` / `pytest` / `mypy` / `ruff`；未 `git add` / `commit` / `push`。
- 未 import `spec/**` 模板 CSS/JS；未在 `web/src` 写死色值（除 `styles/tokens.css`）。

### 6.1 未越界机器自证（取证于 `2026-11-13T03:16:16+08:00`）

```
$ git -c core.quotepath=false status --porcelain          # rc=0
 M tests/unit/test_task_cards.py
 M web/src/main.ts
?? evidence/M0/M0-03/
?? orchestrator/tasks/M0-03b.md
?? orchestrator/tasks/M0-04.md
?? orchestrator/tasks/M1-01.md
?? orchestrator/tasks/M1-02.md
?? orchestrator/tasks/M1-03.md
?? orchestrator/tasks/M2-01.md
?? orchestrator/tasks/M2-02.md
?? orchestrator/tasks/M2-03.md
?? web/src/api/types.ts
?? web/src/styles/element-theme.css
?? web/src/styles/project.css
?? web/src/styles/tokens.css
?? web/tests/unit/tokens-guard.spec.ts
```

- 本 lane 写入项：`web/src/main.ts`（M）、`web/src/api/types.ts`、`web/src/styles/tokens.css`、
  `web/src/styles/element-theme.css`、`web/src/styles/project.css`、`web/tests/unit/tokens-guard.spec.ts`、
  `evidence/M0/M0-03/`（?? 全部在 scope_allow 三条之内）。
- 非本 lane 变更（并行 lane 所有，我未触碰）：`tests/unit/test_task_cards.py`（M）、`orchestrator/tasks/*.md`（??）。
- `git diff --quiet -- web/package.json web/package-lock.json` → rc=0（**0 即无改动**）
- `git diff --quiet -- web/vitest.config.ts web/vite.config.ts web/tsconfig.json web/eslint.config.js web/playwright.config.ts` → rc=0（**0 即配置与 tsconfig 严格开关均未动**）
- `git log --oneline -3 -- <S3/S4 产物>` → 空（产物未入库，等编排器统一提交）


---

# Round 2 · 裁定落地收尾（Q-S3-A / D / E / F）

- 执行时间：2026-11-13T03:40+08:00 · lane F · S3 收尾（HEAD 仍为 `b81f893`，本段产物全部留在工作树）
- 编排器代改：`web/vitest.config.ts` 加 `css: true`（`git diff --numstat` → `7 0`，我未再触碰该文件，见第 6 节 rc 自证）

## R2-1. `css:true` 后 CSS 原文可读性（实测长度，非推断）

探针（临时 `web/tests/unit/__css_read_probe.spec.ts`，用后即删）在 `css:true` 下实测：

| 文件 | `?raw` 得到的 JS 字符串长度（chars） | 磁盘字节数 | 结论 |
|---|---|---|---|
| `web/src/styles/tokens.css` | **4749** | 6251 | 可读（Round 1 为 0） |
| `web/src/styles/element-theme.css` | **6238** | 7723 | 可读（Round 1 为 0） |
| `web/src/styles/project.css` | **1078** | 1434 | 可读（Round 1 为 0） |

绝对形与相对形两种 glob 均可用且长度相同（`/src/styles/*.css` 与 `../../src/styles/*.css` 均返回同一长度），故守卫沿用 Round 1 的 `/src/**/*` 单一 glob。字节数大于字符数是中文注释的 UTF-8 多字节所致，非内容缺失。

## R2-2. 守卫终态：11 条断言全部执行态，**0 skip**

`web/tests/unit/tokens-guard.spec.ts`（268 行）断言清单：

| # | 断言 | 裁定来源 |
|---|---|---|
| 1 | 三个样式文件与 `main.ts`/`App.vue`/`api/types.ts` 均拿到磁盘原文（CSS 长度阈值 >4000/>4000/>1000，`css:true` 退化即红） | Q-S3-A |
| 2 | 除 `styles/tokens.css` 外，`web/src/**` 无六位十六进制色值（含 `.css` 与 `.vue <style>`） | 4.1 出口条件 |
| 3 | 同上扩展：无任意长度十六进制、无 `rgb()/rgba()/hsl()/hsla()` | 设计 3 |
| 4 | `--cl-*` 只在 `tokens.css` 定义（其余文件零定义；`tokens.css` 声明数 ≥68） | 4.2 |
| 5 | `element-theme.css` 只含 `--el-*` 声明，且每个取值形如 `var(--cl-*)`（唯一例外：带出处的 `-rgb`） | 4.2 + Q-S3-D/E(c) |
| 6 | **rgb 三元组换算一致性**：解析注释指定的 `--cl-*` hex → 拆 R,G,B → 与声明逐一比对，不符即红；且「已复算条数 == `-rgb` 声明条数」（缺出处注释也算不符） | Q-S3-E(c) 硬条件 |
| 7 | `project.css` 零自定义属性声明、零色值，且确实消费 `var(--cl-` | 4.2 + 本轮要求 |
| 8 | 对比度：正文/次要/表头/成功/警示/错误 对白底与对画布 ≥4.5:1 | 4.4 + Q-S3-F |
| 9 | 绑定态对比度：`--el-text-color-{primary,regular,secondary}` 与 `--el-color-{success,warning,danger}` 解析到令牌后再算 ≥4.5:1（防止日后把 secondary 绑回 3.62 档） | Q-S3-E(b) |
| 10 | 援引 WCAG 1.4.3 豁免的 `--el-text-color-{placeholder,disabled}` 两行必须把「WCAG 1.4.3」写在同行注释，注释被删即红 | Q-S3-E(b) 附加要求 |
| 11 | 悬空引用：`element-theme.css`/`project.css` 里每个 `var(--cl-*)` 在 `tokens.css` 都有定义 | 4.2 |

`it.skip` / `it.runIf` 已全部移除。

## R2-3. WCAG 对比度独立重算（公式与中间值，非转录编排器数字）

公式（WCAG 2.1）：`C = C8bit/255`；`Clin = C/12.92`（当 `C <= 0.04045`）否则 `((C+0.055)/1.055)^2.4`；
`L = 0.2126*Rlin + 0.7152*Glin + 0.0722*Blin`；`CR = (L_亮 + 0.05) / (L_暗 + 0.05)`。
背景实测：`--cl-card = #ffffff` → `L = 1.000000`；`--cl-canvas = #f5f7fb` → `L = 0.928990`。

| 角色 | hex | R/G/B (8bit) | Rlin/Glin/Blin | L | CR vs 白底 | CR vs 画布 |
|---|---|---|---|---|---|---|
| --cl-ink-900（正文） | `#1a2438` | 26 / 36 / 56 | 0.010330 / 0.017642 / 0.039546 | 0.017669 | **15.5167** | **14.4674** |
| --cl-ink-700（次要/常规） | `#4a5568` | 74 / 85 / 104 | 0.068478 / 0.090842 / 0.138432 | 0.089523 | **7.5256** | **7.0167** |
| --cl-ink-600（表头，与 ink-700 同值） | `#4a5568` | 74 / 85 / 104 | 0.068478 / 0.090842 / 0.138432 | 0.089523 | **7.5256** | **7.0167** |
| --cl-ink-500（禁用/占位） | `#7a8899` | 122 / 136 / 153 | 0.194618 / 0.246201 / 0.318547 | 0.240458 | **3.6150** | **3.3705** |
| EP 默认 --el-text-color-secondary（未覆盖时） | `#909399` | 144 / 147 / 153 | 0.278894 / 0.291771 / 0.318547 | 0.290966 | **3.0795** | **2.8712** |
| --cl-ok-text（成功） | `#176A48` | 23 / 106 / 72 | 0.008568 / 0.144128 / 0.064803 | 0.109581 | **6.5797** | **6.1348** |
| --cl-warn-text（警示） | `#875900` | 135 / 89 / 0 | 0.242281 / 0.099899 / 0.000000 | 0.122957 | **6.0709** | **5.6603** |
| --cl-danger-text（错误） | `#A53232` | 165 / 50 / 50 | 0.376262 / 0.031896 / 0.031896 | 0.105108 | **6.7695** | **6.3117** |

**与编排器口径的一处出入（如实报）**：你给 `#909399` 的 2.85:1 我算为 **对白底 3.0795、对画布 2.8712** —— 2.85 更接近「对画布」档，**两者都远低于 4.5**，结论不变：EP 默认 secondary 违反 `token-mapping.md` §4.4，必须覆盖。
`--cl-ink-700 = #4a5568` 我算 **7.5256 / 7.0167**（你给 7.52，一致）；`--cl-ink-500 = #7a8899` 我算 **3.6150 / 3.3705**（你给 3.62，一致，仍不合格）；`--cl-ink-900` **15.5167 / 14.4674**（你给 15.5，一致）。
旁证：我的公式复算出 `token-mapping.md`/ADR-003 已载的 ink-700 7.53 / ink-500 3.61 / ink-500 on canvas 3.37 / ok-text 6.58 / warn-text 6.07 / danger-text 6.77 / brand-600 7.20 / brand-500 5.00 —— **八档逐位吻合**，说明实现与文档同源。

落地绑定（`element-theme.css`）：`--el-text-color-primary: var(--cl-ink-900)`、`regular: var(--cl-ink-700)`、`secondary: var(--cl-ink-700)`、`placeholder: var(--cl-ink-500)`、`disabled: var(--cl-ink-500)`。
层次说明：`--cl-ink-600` 与 `--cl-ink-700` 同值（`#4a5568`），故 secondary 与 regular 无法靠墨色分档区分，视觉层次只能由字号（`--cl-fs-label` 13px vs `--cl-fs-body` 14px）承载 —— 这一点是令牌表本身的既有约束，非本轮引入。
**豁免声明（显式援引）**：`placeholder` 与 `disabled` 绑 `--cl-ink-500`（3.615 / 3.371）**援引 WCAG 1.4.3 对「禁用控件/非活动元素」的豁免**；`placeholder` 不在 §4.4 的分母（正文、次要、表头、状态文字）内，且 `token-mapping.md` §1 已把 ink-500 的用途钉为「仅禁用态与非文本图标，禁用于小字」。该豁免写在 CSS 同行注释里，并由断言 10 机器守护（注释被删即红）。

## R2-4. rgb 三元组机械换算表（断言 6 的复算依据）

| EP 变量 | 出处 `--cl-*` | hex | 三元组 | 与 `element-theme.css` 声明 |
|---|---|---|---|---|
| `--el-color-primary-rgb` | `--cl-brand-600` | `#0048d8` | 0, 72, 216 | 一致 |
| `--el-color-success-rgb` | `--cl-ok-text` | `#176A48` | 23, 106, 72 | 一致 |
| `--el-color-warning-rgb` | `--cl-warn-text` | `#875900` | 135, 89, 0 | 一致 |
| `--el-color-danger-rgb` | `--cl-danger-text` | `#A53232` | 165, 50, 50 | 一致 |
| `--el-color-error-rgb` | `--cl-danger-text` | `#A53232` | 165, 50, 50 | 一致 |
| `--el-color-info-rgb` | `--cl-info-600` | `#0048d8` | 0, 72, 216 | 一致 |

## R2-5. Q-S3-E 其余落地

**(a) error 族并入项目 danger 族**（Q-S3-D 单调复用）：
`--el-color-error: var(--cl-danger-text)`、`error-dark-2: var(--cl-danger-text)`、`error-light-3: var(--cl-danger-600)`、
`error-light-5/7/8: var(--cl-danger-100)`、`error-light-9: var(--cl-danger-50)`，另有 `--el-color-error-rgb`（见 R2-4）。

**(d) PENDING_OWNER（缺陷 D-017，M0-03b 冻结前须解决，S3 未自创任何 `--cl-*` 令牌）**：
`--el-component-size-large`、`--el-font-size-extra-small`、`--el-font-size-medium`、`--el-font-size-large`、
`--el-font-size-extra-large` 保持 EP 默认。已映射的只有 `--el-font-size-base → var(--cl-fs-body)` 与
`--el-font-size-small → var(--cl-fs-label)`。`element-theme.css` 内以注释钉住该清单，防止后来者误读为遗漏。

**规模实算（脚本，非手数）**：`element-theme.css` 现 **79 条 `--el-*` 声明**（Round 1 为 64；新增 15 = error 族 7 + secondary 1 + font-size-small 1 + rgb 6），
去重 79，非 `--el-*` 声明 **0** 条，`-rgb` 三元组 **6** 条，文件内十六进制/`rgba(`/`hsla(` **0** 次；
`tokens.css` 仍 **68 条**（去重 68，本轮未增删令牌）；`project.css` 自定义属性声明 **0** 条。

## R2-6. 探针取证（4 轮篡改，全部断言「红→还原→绿」）

| # | 篡改 | 命令 | 实测 rc | 守卫给出的失败信息 |
|---|---|---|---|---|
| P1 | 新建 `web/src/__guard_probe.ts`（含 `"#0048d8"` 与 `"rgba(0, 72, 216, .5)"`） | `cd web && npx vitest run tests/unit/tokens-guard.spec.ts` | **1** | 断言 2 → `web/src/__guard_probe.ts:2`；断言 3 → `:2`、`:3` |
| P2 | `project.css` 末尾追加 `.probe-bad { color: #123456; }` | 同上 | **1** | 断言 2 → `web/src/styles/project.css:41` —— **CSS 原文确被扫描（Q-S3-A 的意义所在）** |
| P3 | `--el-color-warning-rgb: 135, 89, 0` 改成 `136, 89, 0` | 同上 | **1** | 断言 6 → 「`--el-color-warning-rgb` 声明 136, 89, 0，机械换算应为 135, 89, 0（`--cl-warn-text=#875900`）」 |
| P4 | `--cl-ink-700: #4a5568` 改成 `#7a8899` | 同上 | **1** | 断言 8 → 「次要文字 `--cl-ink-700=#7a8899` 对白底(#ffffff)=3.615 < 4.5 / 对画布(#f5f7fb)=3.371 < 4.5」；断言 9 另报 4 条（regular/secondary 经 `--el-*` 绑定） |

还原与复绿：

```
$ sha256sum -c /tmp/styles.sha      # P1-P4 前备份的三个样式文件
web/src/styles/tokens.css: OK
web/src/styles/element-theme.css: OK
web/src/styles/project.css: OK
rc_restored_sha = 0
$ cd web && npx vitest run tests/unit/tokens-guard.spec.ts
rc_green = 0（11 passed，无 skipped）
$ diff -q <还原后的 element-theme.css> /tmp/the.bak
rc_theme_identical = 0
```

探针文件已全部删除（P1 的 `__guard_probe.ts`、P2/P3/P4 均为原文件内临时写入后逐字节还原；Round 1 的 `__glob_probe.spec.ts` 亦已删除）。

## R2-7. 四条门禁终态（实测 rc + 时间戳）

| 命令 | rc | 时间戳 | 备注 |
|---|---|---|---|
| `npm --prefix web run typecheck` | **0** | 2026-11-13T03:40:01+08:00 | vue-tsc 严格开关未动 |
| `npm --prefix web run lint` | **0** | 2026-11-13T03:40:02+08:00 | 无输出 |
| `npm --prefix web run test` | **0** | 2026-11-13T03:40:03+08:00 | `Test Files 2 passed (2)` / `Tests 15 passed (15)`；`rg -c skipped /tmp/f2_test.log` → rc=1 即**输出中 0 条 skipped** |
| `npm --prefix web run build` | **0** | 2026-11-13T03:40:04+08:00 | 15 modules |
| `rg -q '#[0-9a-fA-F]{6}' web/src --glob '!**/styles/tokens.css'` | **1** | 同上 | 1 = 无匹配（期望） |
| `rg -q '#[0-9a-fA-F]{3,8}\b\|\brgba?\(\|\bhsla?\(' web/src --glob '!**/styles/tokens.css'` | **1** | 同上 | 1 = 无匹配（期望） |

passed/skipped 精确计数：**15 passed, 0 skipped, 0 failed**（守卫 11 + Round 1 的 `project-baseline` 4）。

## R2-8. 未越界自证（本轮终态）

```
$ git diff --quiet -- web/package.json web/package-lock.json                → rc_pkg_untouched = 0
$ git diff --quiet -- web/vite.config.ts web/tsconfig.json web/eslint.config.js web/playwright.config.ts \
    spec contracts src migrations scripts docs                              → rc_other_untouched = 0
$ git diff --numstat -- web/vitest.config.ts                                 → 7 0（编排器的 css:true，我未再改）
```

我本轮只写：`web/src/styles/element-theme.css`、`web/tests/unit/tokens-guard.spec.ts`、本证据文件。
`web/src/styles/tokens.css`、`web/src/styles/project.css` 与 `web/src/main.ts`、`web/src/api/types.ts` 内容本轮**未变**（P1-P4 篡改已逐字节还原，`sha256sum -c` rc=0 为证）。
并行 lane 的 `pyproject.toml` / `uv.lock` / `migrations/` / `src/campaignlab/infra/` / `tests/integration/` / `tests/unit/test_task_cards.py` / `tests/unit/test_migration_schema.py` / `orchestrator/tasks/*.md` 我未触碰，也未运行任何 `uv`/`pytest`/`mypy`/`ruff`。

## R2-9. 收尾后剩余未决 / 需编排器复核

| # | 事项 | 证据 |
|---|---|---|
| R2-Q1 | **`docs/design/token-mapping.md` 的三处修订在工作树里不存在**：回执称已把三个断点名写进 §3、把单调复用规则写进 §1、把 error 族与 rgb 例外写进 §5，但 `rg -n -- '--cl-bp-rail-collapse\|--cl-bp-rail-drawer\|--cl-content-max\|单调复用\|error-rgb\|## 5\.' docs/design/token-mapping.md` → **rc=1（零命中）**；`rg -n '^#'` 仍只有 §1-§4；`git diff --numstat -- docs/design/token-mapping.md` 为空；该文件最后一次提交仍是 `dbdd701`。 | 我按裁定文本照常落地（裁定本身是权威），但**权威文档尚未同步**，`web/src/**` 与文档目前存在口径差。`docs/**` 不在我的 scope_allow，我未改。请 Lane T/编排器补写，否则 §4.1/§4.4 出口条件的审计链会在 Q 档断在「文档未载」。 |
| R2-Q2 | 断言 10 把「WCAG 1.4.3 豁免」写在注释里并由机器守护 —— 这是我按你「豁免必须显式」的要求做的实现选择，若你希望豁免改以别的形式（例如 `token-mapping.md` 增设 §4.5 豁免清单）留痕，需 Lane T 配合。 | 本轮已生效 |
| R2-Q3 | 无 DOM 环境下 `getComputedStyle` 类断言（EP 覆盖在真实组件上的落地效果）仍归 S8；`element-theme.css` 的 79 条 `--el-*` 目前只有静态保障。 | Q1 未批 jsdom/happy-dom |
