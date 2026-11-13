# R10 编排器复验报告 · Mencius（M0-03b / S2+S3，lane F，qwen3.8-flash）

**口径**：编排器不采信子智能体自报，逐项独立重跑与实测。本报告的全部数字由脚本生成。

## 1. 交付面逐件实测（行数 / 字节 / 编码三断言）

| 文件（相对 `web/`） | 实测行数 | 自报行数 | 一致 | 字节 | BOM | CR | 尾换行 |
|---|---|---|---|---|---|---|---|
| `src/components/state/FirstLoadSkeleton.vue` | 87 | 87 | ✓ | 2825 | 无 | 无 | 有 |
| `src/components/state/MissingValue.vue` | 62 | 62 | ✓ | 2174 | 无 | 无 | 有 |
| `src/components/state/ViewState.vue` | 258 | 258 | ✓ | 10161 | 无 | 无 | 有 |
| `src/components/state/index.ts` | 17 | 17 | ✓ | 1012 | 无 | 无 | 有 |
| `src/components/state/registry.ts` | 54 | 54 | ✓ | 2446 | 无 | 无 | 有 |
| `src/components/state/viewState.ts` | 129 | 129 | ✓ | 6097 | 无 | 无 | 有 |
| `tests/unit/state/firstLoadSkeleton.spec.ts` | 78 | 78 | ✓ | 3692 | 无 | 无 | 有 |
| `tests/unit/state/missingValue.spec.ts` | 88 | 88 | ✓ | 3954 | 无 | 无 | 有 |
| `tests/unit/state/registry.spec.ts` | 183 | 183 | ✓ | 9049 | 无 | 无 | 有 |
| `tests/unit/state/stateMatrix.ts` | 405 | 405 | ✓ | 17233 | 无 | 无 | 有 |
| `tests/unit/state/viewState.spec.ts` | 281 | 281 | ✓ | 12785 | 无 | 无 | 有 |
| `tests/unit/state/viewStateCopy.spec.ts` | 168 | 168 | ✓ | 6993 | 无 | 无 | 有 |

**结论**：12/12 件行数与自报**全等**、编码三断言**全过**、`state/` 内**无第 7 个文件**（`M0-03b-freeze.md:285` 的 CR 条件未触发）→ 验收通过

## 2. 越界自证（A144 三段式）

| 段 | 判据 | 实测 | 结论 |
|---|---|---|---|
| (a) | 写权外 tracked 修改 == 0 | `git diff --name-only HEAD` 全仓 → 复验时点仅 `orchestrator/handoff/M0-03b-freeze.md`（**编排器自己的 A145–A151 更正**，非 lane 产物）；Mencius 交回时点为空 | ✓ |
| (b) | 写权内 numstat `deleted == 0` | 本卡全为**新建**文件，无 tracked 修改，`deleted==0` 平凡成立 | ✓ |
| (c) | 写权外未跟踪新文件 == 0 | `git status --porcelain -uall web` **12** 行，全部落在 `web/src/components/state/` 与 `web/tests/unit/state/` 内；写权外 **0** 条 | ✓ |

## 3. 前端门禁（编排器亲自重跑，cwd=`/home/szf/dev/CampaignLab/web`）

| 门禁 | rc | 实测 | 与自报一致 |
|---|---|---|---|
| `npm run test -- tests/unit/state` | 0 | 5 files / **173** tests passed | ✓ |
| `npm run test`（全量回归） | 0 | 12 files / **277** tests passed | ✓ |
| `npm run typecheck`（`vue-tsc --noEmit`） | 0 | 无输出 | ✓ |
| `npm run lint`（`eslint .`） | 0 | 无输出 | ✓ |
| `npm run build`（`vite build`） | 0 | 83 modules，`index-*.css 377.54 kB`，`✓ built in 511ms` | ✓ |

既有守卫未被新 CSS 触发：`breakpoint-guard` 扫描 38 文件、`web/src` 内 `@media` 断点 6 条全部在 `AppShell.vue:31/36`、`EvidenceDrawer.vue:50`、`PageGrid.vue:15`、`SideRail.vue:24/30`（**均在 `state/` 外**），违规 **0**；`tokens-guard` 11 例全绿。

## 4. 定点守卫实测（ERE，rc=1 表示真无匹配）

| 守卫 | 命令 | rc | 实测 | 判据 | 结论 |
|---|---|---|---|---|---|
| state/ 内 @media 零命中 | `grep -rnE -- '@media' web/src/components/state` | 1 | 0 命中 | ==0 | ✓ |
| state/ 内 data-narrow 零命中 | `grep -rnE -- 'data-narrow' web/src/components/state` | 1 | 0 命中 | ==0 | ✓ |
| state/ 内 matchMedia 零命中 | `grep -rnE -- 'matchMedia' web/src/components/state` | 1 | 0 命中 | ==0 | ✓ |
| state/ 内 vue-router 字样命中（A148；实测 1 且为注释行，运行期路由边 0） | `grep -rnE -- 'vue-router|useRoute' web/src/components/state` | 0 | 1 命中且为注释（`ViewState.vue:22`）；`from 'vue-router'`/`useRoute`/`import(`/`require(` 四项均 0 | 运行期边 ==0 | ✓ |
| state/ 内 6 位十六进制色值零命中 | `grep -rnE -- '#[0-9a-fA-F]{6}' web/src/components/state` | 1 | 0 命中 | ==0 | ✓ |
| stateMatrix.ts 内 describe( 零命中（A151） | `grep -rnE -- '\bdescribe\(' web/tests/unit/state/stateMatrix.ts` | 1 | 0 命中 | ==0 | ✓ |
| stateMatrix.ts 内 it( 零命中（A151） | `grep -rnE -- '\bit\(' web/tests/unit/state/stateMatrix.ts` | 1 | 0 命中 | ==0 | ✓ |
| stateMatrix.ts 内 expect( 零命中（A151） | `grep -rnE -- '\bexpect\(' web/tests/unit/state/stateMatrix.ts` | 1 | 0 命中 | ==0 | ✓ |
| state/ 内 fetch/axios/XMLHttpRequest（A146） | `grep -rnE -- '\bfetch\(|axios|XMLHttpRequest' web/src/components/state` | 0 | 非注释命中 0（2 命中均为注释） | ==0 | ✓ |
| state/ 内 @/api/ 命中（A146） | `grep -rnE -- '@/api/' web/src/components/state` | 0 | 3 = 注释 1 + `import type` 2 | 非注释全为 import type | ✓ |
| state/ 内 features 依赖边（A145） | `grep -rnE -- '@/features' web/src/components/state` | 0 | 1 条（`viewState.ts:19` → `@/features/shared/problemPresentation`） | ==1 | ✓ |

## 5. R10-5：编排器自身的 BRE 假绿与更正

首轮复验时有两条守卫误用 **BRE**（`grep -rn` 未加 `-E`）：`vue-router|useRoute` 与 `features` 交替模式。
BRE 下 `|` 是**字面量**，grep 实际在找字符串 `"vue-router|useRoute"` → 必然 0 命中、rc=1，看起来像「守卫通过」的**假绿**。
这是 R9-4（模式以 `-` 开头被当选项 → rc=2 **假红**）的**镜像陷阱**：rc=1 也可能是假绿，不能一律当作「无匹配=通过」。

改 `-E` 重跑后的真实值：

- `vue-router|useRoute` → **1 命中**，为 `ViewState.vue:22` 的注释行（内容恰是「context 默认值需 vue-router、与 A137 冲突故不用」）；追加 `from ['\"]vue-router`、`useRoute`、`import\(|require\(` 三条 ERE 守卫均 **rc=1、0 命中** → **A148 实质结论不变**（无运行期路由依赖），但引用证据已换成正确命令。
- `@/features` → **1 命中**（`viewState.ts:19`），与 `presentationOf` 正向 grep 交叉一致 → **A145 实质结论不变**。

**固化规则**：`gate_measurement_caliber.rule_grep_alternation_requires_ERE` —— 凡 grep 模式含 `|`、`+`、`?`、`{}`、`()` 者一律加 `-E`（或用 `-F` 明确声明字面量）；且「rc=1 无匹配」型守卫在作为**通过判据**引用前，必须再用一条**必命中**的正向对照 grep 证明该命令本身能命中（否则无法区分「真无匹配」与「模式写错」）。

## 6. 7 项裁定的落点（详见 `orchestrator/handoff/M0-03b-freeze.md` §9）

| 项 | 裁定 | 是否需返工 | 文书动作 |
|---|---|---|---|
| ① R-1 vs F-B | **A145** R-1 加唯一豁免（`features/shared/problemPresentation`） | 否 | 冻结文档 :250 行内更正 + §9 |
| ② A137 字面 vs `import type` | **A146** 判据=运行期模块边；禁造 `ApiError` 镜像类型 | 否 | §9（A137 口径澄清） |
| ③ dev 水槽 + `data-dev-assert` | **A147** 均不需 CR（barrel 未 re-export，公共 API 面零扩张） | 否 | §9 + FU-26 |
| ④ `context` 默认值 | **A148** A137 优先，未传即三字段 null | 否 | 冻结文档 :185 行内更正 + §9 + FU-27 |
| ⑤ 是否 append `skeleton` props | **A149** 不 append、不扩冻结面；页面用 `FirstLoadSkeleton` 或 `variant.render` | 否 | §9 + FU-28 |
| ⑥ 唯一标题 vs 逐字文案 | **A150** §3.3 逐字文案优先，§1.3 降为「唯一可判定标识」 | 否 | 冻结文档 :71 行内更正 + §9 |
| ⑦ `stateMatrix.ts` 超出 §7 | **A151** 追认（非 spec，R-4 工厂的必要落点） | 否 | 冻结文档 :302 行内追记 + §9 |

## 7. S4 状态与任务级判定

- S2 **DONE**、S3 **DONE**（本报告即其验收证据）。
- S4（六态截图）依 **A135** 推迟至 M1-04（需 e2e harness，而 `web/tests/e2e/**` 不在 M0-03b 的 `scope_allow`）→ S4 保持 **DEFERRED(A135)**，不判 TODO 以免误当遗漏。
- 故 **M0-03b 任务级判定 = `PASS_WITH_TODO`**（TODO 项即 S4 截图，已定址到 M1-04），**不判 DONE**。
- 本卡未产出 `evidence/M0/M0-03b/**`：§7 的 S4 段才规定该落点，S2/S3 的门禁证据按 `rule_no_tmp_only_evidence` 落在本目录（编排器复验证据）。

## 8. 成本（如实入账，不粉饰）

- Mencius 自报 token ≈ **3.8e5**，派单预算 **5k** → 越限 **76×**，为本仓最严重单条越限（前值 Dirac 181k=3.02×、Bohr 65k=5.42×）。
- 自报内部表述不自洽（「输入 ≈3.4e5 / 输出 ≈4e5 的 1/10 量级，即输出 ≈4e4」），且无计量句柄可核 → 按「如实上报不粉饰」入账，并标注 `tokens_caliber=self_estimate_unverified`。
- 根因判定为**编排器派单设计错**而非档位选错或模型失控，详见冻结文档 §9.2 与 `round10_self_corrections.R10-4`。
