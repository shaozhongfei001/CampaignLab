# FU-32 commands 记账（cwd 除标注外均为 `/home/szf/dev/CampaignLab`；rc 由 `subprocess.run().returncode` 采集）

守卫命令（G5c 原形，一律 `-E`）：
`grep -rnE '300[012]' web/*.config.* web/playwright.config.ts`

| # | cwd | 命令 | rc | 关键输出 |
|---|-----|------|----|----------|
| 1 | 仓库根 | `grep -nE '300[012]' web/vite.config.ts` | 0 | `32:// 宿主 3000/3001/3002 实测 BUSY（NOTE-01）。…`（HEAD 腐化取证） |
| 2 | 仓库根 | `grep -rnE '300[012]' web/*.config.* web/playwright.config.ts` | 0 | `web/vite.config.ts:32:…`＝**改前 rc=0（腐化）** |
| 3 | 仓库根 | `python3 .orch_tmp/hertz_fu32.py`（首次改写尝试） | 1 | 断言失败：`web/vite.config.ts` 在 HEAD **不以 `\n` 结尾**（69 个 LF、末行 `});` 无换行）；为守 numstat `deleted=1` 未补末行换行（诚实偏差 D-3） |
| 4 | 仓库根 | `python3 .orch_tmp/hertz_chk.py` | 0 | `bytes 3441 CR 0 LF 69 BOM False tail b"},"\n  },\n});"` |
| 5 | 仓库根 | `python3 .orch_tmp/hertz_fu32b.py`（改写 + 守卫复测 + 探针正对照 + 清理） | 0 | 见下方逐条 |
| 5a | 仓库根 | 同上内部：`grep -rnE '300[012]' web/*.config.* web/playwright.config.ts`（**改后**） | **1** | 空输出＝无命中，守卫回到期望态 |
| 5b | 仓库根 | 同形守卫（**探针在位** `web/vite.config.probe.tmp`） | **0** | `web/vite.config.probe.tmp:1:// positive control: host port 3001 was BUSY`（必命中正向对照，证明守卫非恒 1） |
| 5c | 仓库根 | 同形守卫（**探针删除后**） | **1** | 空输出 |
| 5d | 仓库根 | `git status --porcelain web/` | 0 | `M web/vite.config.ts`（探针无残留） |
| 6 | `/home/szf/dev/CampaignLab/web` | `npm run typecheck`（`vue-tsc --noEmit -p tsconfig.json`） | 0 | 无输出错误（**未执行 `npm install`**） |
| 7 | `/home/szf/dev/CampaignLab/web` | `npm run lint`（`eslint .`） | 0 | 无告警输出 |
| 8 | 仓库根 | `git diff --numstat HEAD -- web/vite.config.ts` | 0 | `1  1  web/vite.config.ts`（deleted=1，与「改写一行注释」一致） |

loop_used（件二）= **1**：唯一一轮失败是写回前置断言（末行换行口径），改为「保真字节改写」后一次通过。

## 收工越界自证三段式（cwd=仓库根，证据落盘后复测）
| 段 | 命令 | rc | 输出 |
|----|------|----|------|
| a | `git diff --name-only HEAD \| grep -vE \'<卡内白名单>\' \| wc -l` | 0 | `0` |
| a2 | `git diff --name-only HEAD` | 0 | 仅 `web/vite.config.ts` |
| b | `git diff --numstat HEAD -- web/vite.config.ts` | 0 | `1  1  web/vite.config.ts`（deleted=1，本卡显式授权的一行注释改写） |
| b2 | `git diff --numstat HEAD -- tests/unit/test_job_dto.py` | 0 | 空（新建文件不入 diff） |
| c | `git status --porcelain . \| grep -vE \'<同一白名单>\' \| wc -l` | 0 | `12`＝**口径缺陷**：porcelain 每行带 2 字符状态 + 空格前缀，锚定 `^…$` 的正则永远无法命中任何一行，故该值等于全部条目数，不具判别力（U-3） |
| c2 | 同上但先 `sed -E \'s/^.{3}//\'` 归一化为纯路径再过滤 | 0 | `0`＝真正的「非我路径」计数 |
| c3 | `git status --porcelain . \| sed -E \'s/^.{3}//\'` | 0 | 12 条：`web/vite.config.ts`、4 份本卡证据（含 `r11-fu32/`）、`evidence/M0/ORCHESTRATOR/r11-slices/`（他 lane，白名单在册）、6 份 `orchestrator/handoff/M1-*/M2-*.slice.json`（白名单在册）、`tests/unit/test_job_dto.py` |

结论：**无 `IN_FLIGHT_CONTAMINATION`**——12 条全部落在卡内白名单内；未处理、未删除任何非我路径项。
`src/**`、`contracts/**`、`spec/**`、`scripts/**`、`web/playwright.config.ts`、`web/package.json`、
`web/tsconfig*.json`、`web/src/**`、`web/tests/**` 的 porcelain 命中数实测 0。
