# FE-UI-02 命令留痕（原文 + rc + 末行）

口径参照 `evidence/M0/M0-03/S3-S4-commands.md` 的表格形式。执行环境：WSL2 ext4
`/home/szf/dev/CampaignLab-fe`（分支 `frontend/ui-pages`），`PATH` 前置 `$HOME/.local/share/node/bin`
（node v24.22.3 / npm 11.19.1）。日期 2026-11-20（Asia/Shanghai）。

| # | 命令原文 | rc | 末行 / 关键行 |
|---|---|---|---|
| 1 | `npm --prefix web run lint` | 0 | `> eslint .`（零告警零错误） |
| 2 | `npm --prefix web run typecheck` | 0 | `> vue-tsc --noEmit -p tsconfig.json` |
| 3 | `npm --prefix web run test` | 0 | `Test Files  20 passed (20)`；`Tests  380 passed (380)`（基线 277 → 只增不减） |
| 4 | `npm --prefix web run build` | 0 | `✓ built in 642ms` |
| 5 | `cd web && npx playwright test tests/e2e/activity --reporter=list` | 0 | `34 passed (43.3s)`（17 用例 × 2 视口） |
| 6 | `cd web && npx playwright test --reporter=list` | 0 | `46 passed (48.2s)`（全量：含 UI-01 键盘基线与截图用例） |
| 7 | `python3 scripts/check_frontend_baseline.py` | 0 | `FRONTEND BASELINE PASS 8/8（哈希与字节数逐项一致）` |
| 8 | `fc-list \| grep -c "Noto Sans CJK SC"` | 0 | `2`（Regular/Bold 均在，截图可作视觉结论） |
| 9 | `ls web/src/components/state \| wc -l` | 0 | `6`（冻结六态件数量未变） |
| 10 | `git status --porcelain -- evidence`（命令 6 之后） | 0 | 仅 `?? evidence/FE/`；M0 既有截图**字节未变** ⇒ UI-01 无视觉回归 |

## 门禁读数样例（e2e 运行时逐态打印，节选）

```
[gates] {"label":"ready","consoleErrors":0,"consoleWarnings":0,"pageErrors":0,"httpNoise":[],
 "expectedHttpStatuses":[],"forbiddenTokens":0,"overflow":0,"tagPairing":0,"chartContainers":0,
 "chartViolations":0,"classesUsed":45,"classesDefined":1864,"classesUndefined":2,"unreadableSheets":0}
[gates] {"label":"conflict-409",...,"httpNoise":[409],"expectedHttpStatuses":[409],...}
```

- `classesUndefined:2` ＝ 冻结件 `AppBar.vue` 的 `cl-appbar__actor` / `cl-appbar__recent`（已登记
  `KNOWN_FROZEN_CLASS_GAPS` 穷举白名单 + `classGapDrift()` 双向校验 + CR 请求 [4]）；页面自身 0 未定义。
- `httpNoise` 与 `expectedHttpStatuses` 双向对账：失败/冲突分支用例故意触发的状态码必须**恰好**出现，
  多一个（意外错误响应）或少一个（错误分支没走到）都判红。

## 截图清单（evidence/FE/ui/ui-02/，32 张，纯 ASCII）

每态两档：`*-1440x900.png` 与 `*-1024x768.png`。

| 态 / 场景 | 文件名前缀 |
|---|---|
| 首载骨架（延迟响应中） | `ui-02-first-load-` |
| 正常态四行 | `ui-02-activity-list-` |
| 无记录（空列表） | `ui-02-no-record-` |
| 失败 500 | `ui-02-failed-500-` |
| 版本失效 412 | `ui-02-stale-412-` |
| 上一结果保留（刷新中） | `ui-02-previous-result-` |
| 键盘焦点（2px 焦点线） | `ui-02-keyboard-focus-` |
| 详情抽屉（480px） | `ui-02-detail-drawer-` |
| 缺值行详情 | `ui-02-detail-missing-` |
| 新建确认框（520px） | `ui-02-create-confirm-` |
| 成对校验失败 | `ui-02-create-validation-` |
| 创建成功进入详情 | `ui-02-created-` |
| 409 冲突定位 | `ui-02-conflict-409-` |
| 深链捕获（回入口） | `ui-02-deep-link-captured-` |
| 深链恢复 | `ui-02-deep-link-restored-` |
| 授权脱敏工作区（合成标注负对照） | `ui-02-source-class-authorized-` |