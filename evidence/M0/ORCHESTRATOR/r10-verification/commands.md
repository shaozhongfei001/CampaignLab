# R10 编排器复验 · 命令与实测 rc（门禁四元组）

> 本文件由脚本 `.orch_tmp/r10_regen_commands.py` **从实跑日志与实测结果生成**，非手工誊写
> （依 `gate_measurement_caliber.rule_evidence_count_must_be_programmatic`）。
> rc 语义：0=成功/有匹配，1=无匹配（守卫期望值），2=命令自身错误（判红重跑，禁记为 1）；`-` 表示该段为自由格式输出（非 run() 四元组）。
> 原始日志全文见 `logs/`（3 份，禁只存 /tmp，依 `rule_no_tmp_only_evidence`）。
> cwd 一律 `/home/szf/dev/CampaignLab`，前端四门禁为 `/home/szf/dev/CampaignLab/web`（表中显式标注）。

## 1. 门禁四元组

| # | 标签 | cwd | 命令 | rc | 关键输出（末行/实测值，截断 190 字） |
|---|---|---|---|---|---|
| 1 | ruff_format_batch | `/home/szf/dev/CampaignLab` | `uv run --no-sync ruff format --check evidence/M0/M0-02/ac.md evidence/M0/M0-02/commands.md evidence/M0/M0-02/migration-diff.md evidence/M0/summaries/M0-02.md orchestrator/defects/D-038.md` | **0** | 5 files already formatted |
| 2 | pytest_counts_and_ledger | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q tests/unit/test_counts_freshness.py tests/unit/test_state_ledger.py` | **1** | 1 failed, 10 passed in 0.15s |
| 3 | post_commit_counts_guard | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q tests/unit/test_counts_freshness.py` | **0** | 5 passed in 0.07s |
| 4 | post_commit_ledger | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q tests/unit/test_state_ledger.py` | **0** | 6 passed in 0.02s |
| 5 | HEAD tree recount | `/home/szf/dev/CampaignLab` | `` | **-** | MATCH True |
| 6 | index vs disk set equality | `/home/szf/dev/CampaignLab` | `` | **-** | SET_EQUAL True |
| 7 | A137_runtime_edge | `/home/szf/dev/CampaignLab` | `grep -rnE "@/api/" web/src/components/state \| grep -vE "^[^:]+:[0-9]+: *(\*\|//\|/\*)" \| grep -vc "^.*import type"` | **0** | VERDICT=PASS_no_runtime_api_edge |
| 8 | fetch_axios (ERE, 修 R9-4 的 rc=2) | `/home/szf/dev/CampaignLab` | `grep -rnE "\bfetch\(\|axios\|XMLHttpRequest" web/src/components/state` | **0** | web/src/components/state/ViewState.vue:17: *          不 fetch、不 axios；state 为必填 prop，触发值全部由页面显式传入（F-A 组件不猜）。 |
| 9 | media_query_and_narrow_guards | `/home/szf/dev/CampaignLab` | `` | **-** | <no match> |
| 10 | vitest_state | `/home/szf/dev/CampaignLab` | `npm run test -- tests/unit/state` | **0** | [2m   Duration [22m 342ms[2m (transform 45%, import 36%, tests 16%, worker 2%)[22m |
| 11 | vitest_full | `/home/szf/dev/CampaignLab` | `npm run test` | **0** | [2m   Duration [22m 788ms[2m (transform 48%, import 41%, tests 9%, worker 2%)[22m |
| 12 | typecheck | `/home/szf/dev/CampaignLab` | `npm run typecheck` | **0** | > vue-tsc --noEmit -p tsconfig.json |
| 13 | lint | `/home/szf/dev/CampaignLab` | `npm run lint` | **0** | > eslint . |
| 14 | build | `/home/szf/dev/CampaignLab` | `npm run build` | **0** | ✓ built in 511ms |
| 15 | state/ 内 @media 零命中 | `/home/szf/dev/CampaignLab` | `grep -rnE -- '@media' web/src/components/state` | **1** | measured=0 |
| 16 | state/ 内 data-narrow 零命中 | `/home/szf/dev/CampaignLab` | `grep -rnE -- 'data-narrow' web/src/components/state` | **1** | measured=0 |
| 17 | state/ 内 matchMedia 零命中 | `/home/szf/dev/CampaignLab` | `grep -rnE -- 'matchMedia' web/src/components/state` | **1** | measured=0 |
| 18 | state/ 内 vue-router 字样命中（A148；实测 1 且为注释行，运行期路由边 0） | `/home/szf/dev/CampaignLab` | `grep -rnE -- 'vue-router\|useRoute' web/src/components/state` | **0** | measured=1 |
| 19 | state/ 内 6 位十六进制色值零命中 | `/home/szf/dev/CampaignLab` | `grep -rnE -- '#[0-9a-fA-F]{6}' web/src/components/state` | **1** | measured=0 |
| 20 | stateMatrix.ts 内 describe( 零命中（A151） | `/home/szf/dev/CampaignLab` | `grep -rnE -- '\bdescribe\(' web/tests/unit/state/stateMatrix.ts` | **1** | measured=0 |
| 21 | stateMatrix.ts 内 it( 零命中（A151） | `/home/szf/dev/CampaignLab` | `grep -rnE -- '\bit\(' web/tests/unit/state/stateMatrix.ts` | **1** | measured=0 |
| 22 | stateMatrix.ts 内 expect( 零命中（A151） | `/home/szf/dev/CampaignLab` | `grep -rnE -- '\bexpect\(' web/tests/unit/state/stateMatrix.ts` | **1** | measured=0 |
| 23 | state/ 内 fetch/axios/XMLHttpRequest（A146） | `/home/szf/dev/CampaignLab` | `grep -rnE -- '\bfetch\(\|axios\|XMLHttpRequest' web/src/components/state` | **0** | measured=0 |
| 24 | state/ 内 @/api/ 命中（A146） | `/home/szf/dev/CampaignLab` | `grep -rnE -- '@/api/' web/src/components/state` | **0** | measured=3 |
| 25 | state/ 内 features 依赖边（A145） | `/home/szf/dev/CampaignLab` | `grep -rnE -- '@/features' web/src/components/state` | **0** | measured=1 |

## 2. 实测计数（脚本生成，禁手工累加）

- 本表行数：**25**（由解析 `logs/` 3 份日志 + 11 条定点守卫生成）
- Mencius 交付件：**12** 件（`web/src/components/state/` 6 + `web/tests/unit/state/` 6）
- 编码三断言（无 BOM / 无 CR / 有尾换行）违规件数：**0**
- `git status --porcelain -uall web` 行数：**12**，写权外条目：**0**
- `index.ts` barrel 导出行：**7**，其中 dev 水槽符号：**0**（A147 判据：barrel 未 re-export → 不触发 CR）
- A146 判据：`@/api/` 命中 **3** = 注释 1 + `import type` 2 → 运行期 api 边 **0**
- 前端用例数（取自 vitest reporter 实测，非写死）：`tests/unit/state` **173**、全量 **277**
