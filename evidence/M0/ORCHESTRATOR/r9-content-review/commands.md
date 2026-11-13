# commands.md · Verifier-R9A 实际执行命令台账（可复跑证据）

- 宿主 Win11 / shell PowerShell / cwd `D:\ws\codex_rd\ss_campaignlab`；仓库在 WSL2 `/home/szf/dev/CampaignLab`（分支 `m0-framework`）。
- 所有仓库内读取一律经 `wsl.exe -e bash -lc`（单行，无内层双引号）或「PS 单引号 here-string → `.orch_tmp\vra_*.py` → `wsl.exe -e python3 /mnt/d/...`」通道；rc 全部由 `subprocess.run(...).returncode` 采集，未使用 shell 的问号变量。
- 「工作目录」列：`HOST` = `D:\ws\codex_rd\ss_campaignlab`（PowerShell 侧）；`REPO` = `/home/szf/dev/CampaignLab`（脚本内 `cwd=`）。

| # | 工作目录 | 命令原文 | rc | 关键输出（摘要） |
|---|---|---|---|---|
| 1 | HOST→REPO | `wsl.exe -e bash -lc "cd /home/szf/dev/CampaignLab && pwd && git rev-parse --abbrev-ref HEAD && ls orchestrator/handoff/ && echo --- && ls orchestrator/defects/ && find web/src/components -type f \| sort"` | 0 | `m0-framework`；`components` 下 14 项 = `.gitkeep` + 12 个 `.vue` + `componentTypes.ts`，**无 `state/`** |
| 2 | HOST→REPO | `wsl.exe -e bash -lc "cd ...; wc -l orchestrator/handoff/M0-03-public-components.md orchestrator/handoff/M0-03b-freeze.md orchestrator/defects/D-034.md spec/.../ui/COMMON.md && echo --- && ls -d web/src/components/state 2>&1 && ..."` | **1** | 行数 303 / 331 / 34 / 38；`ls: cannot access web/src/components/state: No such file or directory` 使 `&&` 链中断（后续改用分号分隔重试） |
| 3 | HOST→REPO | `wsl.exe -e bash -lc "cd ...; find web/src -type d \| sort; echo ---; wc -l web/src/components/*.vue web/src/components/componentTypes.ts \| sort -n"` | 0 | 目录树无 `state`；逐件行数 43/27/39/24/34/49/19/53/16/18/34/34/8，合计 **398** |
| 4 | HOST→REPO | `wsl.exe -e bash -lc "cd ...; grep -n 井号或竖线锚点 orchestrator/handoff/M0-03-public-components.md \| head -100"` | 0 | §2.1-§2.12 全部表行绝对行号（`H:34-188`） |
| 5 | HOST→REPO | `wsl.exe -e bash -lc "cd ...; sed -n 186,303p orchestrator/handoff/M0-03-public-components.md \| grep -n . \| sed -n 1,120p"` | 0 | §2.12 余行、§2.13（`H:199-203`）、§3-§7（`H:281-300`，D1-D4 在 `H:297-300`） |
| 6 | HOST→REPO | `wsl.exe -e bash -lc "cd ...; for f in AlertBanner AppBar AppShell CardPanel ConfirmDialog; do echo 回显标记加循环变量; nl -ba web/src/components/...; done"`（内层用了转义双引号与转义美元符） | **1** | `nl: -c: line 1: unexpected EOF while looking for matching '"'` —— **踩坑实录**：PowerShell 剥除内层转义双引号与美元符。处置：立即改走 Python 脚本通道（#7），未误判为「文件不存在」 |
| 7 | REPO | `wsl.exe -e python3 /mnt/d/ws/codex_rd/ss_campaignlab/.orch_tmp/vra_read1.py`（内层 `nl -ba` ×5） | 0 | `AlertBanner.vue:6` props；`AppBar.vue:5`/`:6`/`:18`；`AppShell.vue:6`/`:7`；`CardPanel.vue:2`/`:5`/`:8-12`；`ConfirmDialog.vue:3-14`/`:19`/`:20` |
| 8 | REPO | `...vra_read2.py`（同一循环里对 ts 文件与 vue 文件混用裸名） | 0（子命令 rc=1） | `nl: web/src/components/DataTable: No such file or directory` ×7，另得 `componentTypes.ts:1-8` 全文 —— 脚本自身拼名 bug，非仓库问题 |
| 9 | REPO | `...vra_read3.py`（显式带 `.vue` 扩展名逐件 `nl -ba`） | 0 | `DataTable.vue:3-10`/`:13-14`/`:20`/`:24`/`:34`/`:42`/`:46`；`EmptyState.vue:2-3`/`:7-9`；`EvidenceDrawer.vue:4-25`；`PageBar.vue` 模板段；`PageGrid.vue:2`/`:5-7`/`:11-13`；`SideRail.vue:4`/`:7-8`/`:11`；`StatusTag.vue:3-4`/`:7`/`:22-33` |
| 10 | REPO | `...vra_read4.py`（6 组定点 sed/grep：ED27 / SHELL9 / ROWH / APIIMP / FOCUS / TOKROW） | 0 各 | `EvidenceDrawer.vue:27-53`；`AppShell.vue:11` 为裸 `<SideRail />`、`:13-16`；`tokens.css:77-78`/`:92`；`components` 内 `@/api` 仅 4 行类型导入；`ConfirmDialog.vue` 焦点族 grep 仅命中 `:14`；`tokens.css:83-84` = 480/520 |
| 11 | REPO | `...vra_read5.py`（D-034.md 全文 + COMMON.md 全文 + freeze 标题行 grep） | 0 | `D-034.md:4-6`/`:18-21`/`:23`/`:32-34`；`COMMON.md:5`/`:15`/`:19`/`:27-38`；freeze §1-§8 起始行 11/41/58/80/89/98/115/121/170/203/212/256/276/290/297/321 |
| 12 | REPO | `...vra_read6.py`（`sed 41,79p` 与 `sed 98,120p` 带绝对行号） | 0 | 六态定义表 `F:43-50`；裁定 F-A~F-E `F:54-78`；冻结清单 `F:102-113`；`F:115-119` 目标 6 文件 + `STATE_DIR_ABSENT` |
| 13 | REPO | `...vra_read7.py`（PB / DENSE / CONSUMERS / CD_FOCUS2 / TOK75） | 0 | `PageBar.vue:2` props；密集令牌与 sticky 全域 grep **仅命中定义行 `tokens.css:78`、`:92`，0 处引用、0 处 sticky**；`ConfirmDialog.vue` 的 watch/onMounted/onUpdated/nextTick/focus grep 为空（`grep -c ''` = 34 行）；`AppShell` 消费点仅 `WorkspacePage.vue:4`/`:137` |
| 14 | REPO | `...vra_read8.py`（SIDEFX / RUNTIME_IMP / STATEDIR / COUNTS） | 0 | 网络调用族在 `web/src/components` **0 命中**；运行期 import 仅 5 条（vue 生命周期 / 子组件 / `presentationOf`）；`STATE_DIR_ABSENT`；`ls` 计数 = **13**、子目录数 **0** |
| 15 | REPO | `...vra_read9.py`（TSCONFIG / FSIG） | 0 | `web/tsconfig.json:10` = `exactOptionalPropertyTypes: true`（`:8` `strict: true`）；freeze `:126-156`、`:170-207` 的 `ViewStateKind` / props / emits / 不变量 |
| 16 | REPO | `...vra_read10.py`（TSC2 / MISS_REG / KINDS） | 0 | tsconfig 唯一命中 `web/tsconfig.json:10`；`F:207-210` 两件 props；`F:224-240` `registry.ts` 接口草案；`F:126-132` 六字面量 |
| 17 | REPO | `...vra_w01.py`（首次：在三引号原始字符串内部又做了变量拼接，导致字符串被提前闭合） | **1** | `SyntaxError: invalid decimal literal` → 改为纯字面量后重写（#18） |
| 18 | REPO | `...vra_w01.py`（第二次） | 0 | 写出 `01-component-contract-table-review.md`，47 行 / 11331 B；写后断言无 BOM、无回车符、以换行结尾 |
| 19 | REPO | `...vra_read11.py`（PAGES / WPSP） | 0 | `WorkspacePage.vue` 消费点实测：`DataTable :162-166`（含 `#cell-action`）、`ConfirmDialog :215`、`EvidenceDrawer :205-212`、`StatusTag :140-141`、`AppShell :137`/`:222` |
| 20 | REPO | `...vra_read12.py`（JOBPROG / FZ8） | 0 | `JobProgress` 在 `web/src` **0 命中**；freeze §8 `F:323-331`（U-1~U-7 + 「没有创建 `state/**` 任何文件」） |
| 21 | REPO | `...vra_read13.py`（UW / US / PP / TOK92） | 0 | `useWorkspaces.ts:32`、`:139`；`useSession.ts:26`；`problemPresentation.ts:3`/`:14`/`:47`/`:55`/`:65`；`tokens.css:92` —— 03 报告引用的二手行号全部独立复验 |
| 22 | REPO | `...vra_w02.py` / `...vra_w03.py` | 0 / 0 | 写出 02（106 行 / 12817 B）、03（54 行 / 9058 B），断言同上 |
| 23 | REPO | `...vra_p03.py`（03 报告 3 处精度补丁，每处 `assert count==1`） | 0 | `PATCHED 03 lines= 54`，仅改本 lane 自有新文件 |
| 24 | REPO | `...vra_w00.py`（写 00-index.md + commands.md + 逐文件自检） | 0 | 见下节「越界自证」 |

## 踩坑与处置（共 4 次，全部恢复，未误判件缺失）

1. #6 PowerShell 剥除内层转义双引号与美元符 → bash 报 unexpected EOF；处置：改 Python 脚本通道（与 `M0-03-public-components.md:H:116` D5 记录的同源坑一致）。
2. #8 脚本自身漏写 `.vue` 扩展名 → `nl` 报 No such file；处置：#9 显式带扩展名重跑。
3. #17 三引号原始字符串内部做变量拼接 → Python SyntaxError；处置：#18 改纯字面量。
4. #2 与本次 #24 首次运行同类：内容里出现连续三个单引号会提前闭合字符串；处置：改写为描述性文字，不再把该序列放进内容。

## 越界自证（在仓库根执行，双检；由脚本以 returncode 采集）

下面两行由本次运行的收尾脚本追加实测值。

## 越界自证实测（本次运行，仓库根执行）

| 命令原文（口径规定式） | rc | 实测值 |
|---|---|---|
| `git diff --name-only HEAD | grep -vE '^evidence/M0/ORCHESTRATOR/r9-content-review/' | wc -l` | 0 | **0** |
| `git status --porcelain | grep -vE '^(\?\? )?evidence/M0/ORCHESTRATOR/r9-content-review/' | wc -l` | 0 | **0** |

补充写法互证（均为 0，排除「同一正则假阳性」）：

| 变体 | 实测值 |
|---|---|
| `git status --porcelain | grep -vE '^([?][?] )?evidence/M0/ORCHESTRATOR/r9-content-review/' | wc -l` | **0** |
| `git status --porcelain --untracked-files=all | grep -v '^?? evidence/M0/ORCHESTRATOR/r9-content-review/' | wc -l`（展开未跟踪到文件级） | **0** |

- 命令 1 = 0 ⇒ 本 lane **未修改任何既有文件**；`spec/**`、`contracts/**`、`orchestrator/state.json` 全部零改动。
- 命令 2 = 0 ⇒ `git status --porcelain` 的条目全部落在本 lane 目录内；**无非本 lane 产生的在飞改动**（全量实测只有 1 行 `?? evidence/M0/ORCHESTRATOR/r9-content-review/`，展开后为本目录 5 个新文件）。
- 自纠留痕（本 lane 自身脚本 bug，非仓库状态，共 2 次）：① 首次把排除路径写成自带行首锚点的形式，拼入后正则出现两个锚点、永不匹配，命令 2 误报 1；② 修 ① 时又把可选前缀 `(?? )?` 整段丢掉，`?? ` 行不再被排除，命令 2 再次误报 1。最终按台账规定的原式（含 `(\\?\\? )?` 可选前缀）复测，并用 4 种写法互证为 0。踩坑计数追加至第 6 次：**排除式正则的可选 `?? ` 前缀与锚点数量必须在拼接后仍然完整**，且要用变体互证而非单点取值。
