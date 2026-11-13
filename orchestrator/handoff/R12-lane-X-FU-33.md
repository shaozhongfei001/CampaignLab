# R12 · Lane X · FU-33 / D-041 派单文（档位 qwen3.8-max / reasoning high）

> 权威条款：`docs/delivery/LONG-HORIZON-ORCHESTRATION.md` v1.7（§1 不变量、§3.2 任务卡模板、
> §4.1 L 循环、§13.2 写入通道铁律、§15.2 提交纪律、§15.5 成本账本【无拆解表不得 spawn】）。
> 缺陷单原文：`orchestrator/defects/D-041.md`（**先读它**，§6 是修复方案）。
> 本文是 lane X 的**唯一**上下文包。

## 0. 基线三行（as-of HEAD `cf39d64`，branch `m0-framework`，编排器 2026-11-14 实测于冻结索引树）

| 门 | 命令（cwd=仓库根，WSL 内） | 期望 |
|---|---|---|
| ruff format | `uv run --no-sync ruff format --check .` | rc=0 且 `225 files already formatted`（**注意：ruff format 的 in-scope 含 `.md`，你新增的 4 个 .md 会被计入**） |
| ruff check | `uv run --no-sync ruff check .` | rc=0 且含 `All checks passed!` |
| mypy | `uv run --no-sync mypy` | rc=0 且 `Success: no issues found in 79 source files` |
| pytest | `uv run --no-sync pytest -q` | rc=0 且 `490 passed` |

**在飞污染警告**：本轮同时有 lane W（FU-29）在飞，写集是
`src/campaignlab/{domain,worker}/errors.py`、`src/campaignlab/infra/artifacts.py`、
`tests/unit/test_layering_edges.py`。你在工作树上跑全表门禁**必然**看到它的中间态。
这是 IN_FLIGHT_CONTAMINATION，**不是你的 RED，也不许你去修**（A161：复验方对在飞面禁写）。
你的自验一律**路径限定**（见 §4），全表由编排器在冻结索引树上复跑。

## 1. 任务：补齐三张缺失任务卡 + 立一条「台账任务集 == 卡文件集」的守护

编排器 2026-11-14 实测复验（**不是**采信交接摘要）：
- `orchestrator/tasks/*.md` = **26** 张；`state.json -> tasks` = **29** 个任务键。
- 缺口恰为 3 张：`M3-P02`、`M5-P01`、`M5-03`（`EXTRA` = 空集，无孤儿卡）。
- 三者的台账条目（你写卡时的**权威输入**，禁自己发明）：

| 任务 | lane | tier_planned | wave | deps | slack | critical | scope（写权落点） |
|---|---|---|---|---|---|---|---|
| M3-P02 | F | mixed | 7（L4） | M0-03, M3-P01, M3-04 | 2 | false | `web/src/pages/review/monthly/`、`web/src/features/monthly/`、`web/tests/unit/monthly/`、`web/tests/e2e/monthly/`、`evidence/monthly/M3-P02/` |
| M5-P01 | Q | max | 9 | M3-P02, M4-P01, M5-01 | 0 | **true** | `qa-reports/monthly/`、`evidence/monthly/M5-P01/`、`orchestrator/defects/DMR-*.md` |
| M5-03 | O | **human** | 10（serial） | M5-02, M5-P01 | 0 | **true** | `docs/delivery/HANDOVER.md` |

三者的 `gates` 与 `acs` 逐字取自 `state.json -> tasks[<id>]`（用 python 读，禁手抄）：
- M3-P02 → acs = AC-MR-03..08（6 条）
- M5-P01 → acs = AC-MR-01..12（12 条）
- M5-03 → acs = **空**（它是交付确认节点，不承载 AC）

### 1.1 编排器已就 D-041 §6 作出的两项终裁（你必须照此执行，禁自行改口径）

**A178 — D-041 §6① 引用的 AC 路径不存在，纠正为**：
- ❌ `spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/qa/ACCEPTANCE-MONTHLY.md`（**磁盘上无此文件**，编排器 2026-11-14 实测 `os.path.exists` = False）
- ✅ 月报 AC 权威 = `spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/qa/CampaignLab-Review-Acceptance-Checklist.append.md`
  （与 `state.json -> acceptance.monthly_source` **逐字一致**，12 条 AC-MR-01..12）
- ✅ 基线 AC 权威 = `spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md`
- ✅ 月报 UI 权威 = `spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/ui/MONTHLY-PAGES.md`；
  既有页面 UI-17 = `spec/CampaignLab-SDD-v1.0/ui/UI-17-strategy-review.md`
- ✅ 月报架构权威 = `spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/architecture/MONTHLY-REVIEW.md`
**写卡时只准引用上面这些实测存在的路径**；卡内任何路径引用都会被编排器的悬空引用扫描复核，
指向不存在的文件 = 整条 lane 判红。

**A179 — D-041 §6③「补切 3 张契约切片」不在本 lane 范围内，顺延为 FU-34**：
理由是 wave3–wave6 仍可能通过 CR 改动活契约 `contracts/openapi.json`，此刻切出的
`sha16` 基准文本会腐化（D-013 的教训：契约改动后**必须重切切片并同步全部 sha16 基准**）。
FU-34 的 trigger = 各卡**派单前**（M3-P02 在 wave7）。**你不要切切片**，
但要在三张卡的 `inputs` 段落里**显式写明**「切片待 FU-34 于派单前补切，本卡的 op/schema
目标以届时的切片为准」，以免下游 lane 误以为切片已存在。

### 1.2 M5-03 的特殊性（**最容易做错的一条**）

M5-03 的 `tier_planned = human`，是**人类确认节点**。卡内必须：
- 显式标注 `human_only_action`（字面串，编排器与后续 Q 复核会 grep 它）；
- 明写「**禁**把交付确认动作派给任何子智能体自证通过」（D-041 §6②）；
- 它的「子任务档位表」仍然**必须有**，且表头**逐字**等于四列硬约束（见 §2.2），
  档位列填 `human`。理由：`test_task_cards.py:37` 的 `LEGACY_CARDS` 只豁免
  `{M0-01, M0-P01}`，`test_task_card_narrative.py:41` 的 `LEGACY_NO_TABLE` 同样只豁免这两个；
  **你不得把 M5-03 加进这两个豁免集**（那等于用豁免掩盖缺口，
  `test_legacy_no_table_set_is_exact` 的 `recovered` 分支会判红，且违反单调收敛纪律）。

## 2. 必须满足的既有守护（编排器已逐条实测其判据，期望值如下）

### 2.1 `tests/unit/test_task_cards.py`（93 行，**在你的写集内**）

| 判据 | 现值 | 你改完后必须是 |
|---|---|---|
| `TASK_TOTAL_DENOMINATOR`（:25） | 29 | **29 不变**（任务总数没变，只是补齐卡） |
| `KNOWN_MISSING`（:28-34） | `frozenset({"M3-P02","M5-03","M5-P01"})` | **`frozenset()`** |
| `LEGACY_CARDS`（:37） | `{"M0-01","M0-P01"}` | **不变** |
| `REQUIRED_SECTIONS`（:39） | `("scope_allow","scope_deny","outputs","子任务档位表")` | **不变**；三张新卡的正文必须**各自逐字包含**这 4 个串 |

关键用例：
- `test_missing_cards_are_exactly_the_registered_gap`（:62-70）双向判：
  `unregistered = missing - KNOWN_MISSING` 必须空，**且** `recovered = KNOWN_MISSING - missing`
  也必须空 —— 所以补了卡就**必须**同步清空 `KNOWN_MISSING`，漏一步即红（单调收敛）。
- `test_known_missing_denominator_matches_registered_gap`（:72-77）：`len(missing) == len(KNOWN_MISSING)`，
  改完两边都应为 **0**。
- `test_no_orphan_card_on_disk`（:79-81）：磁盘卡集 ⊆ 台账任务集。
- `test_dispatchable_cards_have_required_sections`（:84-93）：逐卡查 `REQUIRED_SECTIONS` 4 个串。

### 2.2 `tests/unit/test_task_card_narrative.py`（167 行，**只读，禁改**）

`_split()`（:51-65）的口径是编排器实测复现过的，逐字如下：
- `head` = **表头行的 0-based 下标**（即表头之前的行数），上限 `HEAD_MAX_LINES = 60`
- `tail` = `len(text.split("\n")) - end`，`end` = 表头起**连续以 `|` 开头**的最后一行的下一行下标；
  上限 `TAIL_MAX_LINES = 40`
- `total` = `len(text.split("\n"))`（**文件以 `\n` 结尾时会多算 1 个空元素**），上限 `TOTAL_MAX_LINES = 200`
- 表头识别条件 = `line.strip().startswith("|") and "子任务" in line.strip()`
- `REQUIRED_TABLE_HEADER`（:35）**逐字** = `| 子任务 | 档位 | 预估 token | 产出 |`
  （四列、竖线两侧各一个空格、`预估 token` 中间一个半角空格）
- `LEGACY_NO_TABLE`（:41）= `{M0-01, M0-P01}`，`LEGACY_TAIL_ANNOTATED`（:44）= `{M0-02, M0-03}`，
  **两个集合都不许动**
- `CARD_MIN_COUNT`（:38）= 12，防 glob 扫空全绿

**26 张既有卡的实测指标（编排器逐卡跑 `_split` 得到，给你当尺度参照）**：
head 区间 29–55、tail 区间 0–27（M0-02=159、M0-03=114 属 TAIL 豁免）、total 区间 33–195。
**最贴身的三个模板**（按你要写的卡的性质选）：
- `M3-P02`（页面卡、P 系列）→ 抄 **`M4-P01.md`**（head 36 / tail 22 / total 70）；
  `M3-P01.md` head=55 已逼近 60 上限，**不要**拿它当骨架。
- `M5-P01`（独立 QA 线）→ 抄 **`M5-02.md`**（head 35 / tail 22 / total 65）与 `M5-01.md`（37/27/71）。
- `M5-03`（human 确认）→ 抄 **`M5-02.md`** 的骨架，把档位列全填 `human`，正文压到最短。

**head ≤ 60 是硬约束**：表头之前只能放「标题 / 元信息行 / 目标 / inputs / scope_allow /
scope_deny / outputs / 门禁表 / AC 归属」这些必需段，禁在表头前写长篇叙述。
写完**自己跑一遍 `_split` 口径**（§4 给了现成脚本）再交。

### 2.3 你要新增的守护：`tests/unit/test_task_cards_complete.py`

D-041 §2 的根因判定是「**缺少一条『台账任务集 == 卡文件集』的守护**，而不是某一轮的疏忽」。
所以本 lane 的核心产出不是三张卡，而是这条让缺口**不可能再次静默存在**的守护。要求：

1. **双向相等**：`set(state.json -> tasks 的键) == set(orchestrator/tasks/*.md 的文件名 stem)`。
   两个方向各自给独立断言与独立报错文本（`missing` = 有任务无卡；`orphan` = 有卡无任务）。
2. **分母断言**（手册 §15.4：守护必须自带分母，防 glob 扫空全绿）：
   `len(tasks) == 29` 且 `len(cards) == 29`，两者都写死 —— 这属 §15.5 允许的
   「冻结面写死」（语义即「不得静默增减」），**但**必须在断言消息里写明
   「任务总数变更须同批更新此分母并说明依据」。
3. **台账三键对账**（闭合 D-042）：从 `resume.self_check_gates_rc0.counts` 读
   `task_cards_on_disk`、`known_missing_cards`、`task_total_denominator`，断言
   `task_cards_on_disk == 实测卡数`、`known_missing_cards == 实测缺口数`、
   `task_cards_on_disk + known_missing_cards == task_total_denominator == 29`。
   **本条是新增价值**：现状台账写的是 `task_cards_on_disk=20 / known_missing_cards=9`，
   而磁盘实测是 26 / 3 —— 台账已腐化（见 §2.4），没有任何机器守护照到它，
   这条守护就是要把这个盲区堵死。
4. **正向对照**（手册 §15.4 / A159，缺此判红）：用 `tmp_path` 造一棵假的
   `orchestrator/tasks/` 树（多一张卡 / 少一张卡两种形态），断言你的判定函数
   **能**分别报出 `orphan` 与 `missing`。禁把判定逻辑写死在用例里导致无法对照 ——
   抽出一个可传 `card_dir` / `tasks` 的纯函数，用例与对照共用它。
5. **禁**用 `__subclasses__`、禁 import 被测源码产生副作用；只用 `json` + `pathlib`。
6. mypy strict 干净（`from __future__ import annotations`、全量类型标注、
   `subprocess` 输出显式判型），**禁** `# type: ignore`。
7. ruff：`E,F,I,UP,B,SIM,RUF` 全开，line-length 100。

### 2.4 D-042（编排器本轮已立单，你在回执里认领即可，**台账由编排器改**）

台账 `counts` 腐化：`task_cards_on_disk=20`、`known_missing_cards=9`、
`task_card_identity` 声称「20 + 9 == 29 实测成立」—— 而磁盘实测 26 张、缺 3 张。
根因：R11-T 那批入库了 6 张卡（M1-01/02/03、M2-01/02/03）却**只刷新了**
ruff/pytest/mypy 三项，漏刷 `task_cards_on_disk` / `known_missing_cards`，
违反 A101 `rule_counts_same_commit`；且 `test_counts_freshness.py` 只守
`ruff_formatted_files`，照不到卡数，故静默腐化了一整轮。
**你不要改 state.json**（`orchestrator/**` 在你的 hard_deny 内）；
编排器会在你的提交里把这三键一次性校正为 `29 / 0 / 29` 并刷新 `task_card_identity`。
你要做的是：让 §2.3 第 3 条守护**能照到**这三键，并在回执里给出你实测的三键现值。

## 3. 写权（write_set）与硬禁（hard_deny）

**只许写这些**：
```
orchestrator/tasks/M3-P02.md               # 新卡
orchestrator/tasks/M5-P01.md               # 新卡
orchestrator/tasks/M5-03.md                # 新卡（human_only_action）
tests/unit/test_task_cards_complete.py     # 新守护（本 lane 的核心产出）
tests/unit/test_task_cards.py              # 仅 KNOWN_MISSING -> frozenset()
evidence/M0/FU-33/**                       # 你的取证目录，自建
```
**硬禁（写一个即判越界、整条 lane 判红）**：
```
orchestrator/state.json                    # 台账只归编排器写
orchestrator/defects/**  orchestrator/handoff/**  orchestrator/tasks/<其余 26 张卡>
tests/unit/test_task_card_narrative.py     # 只读；LEGACY_* 两个豁免集禁动
tests/unit/test_counts_freshness.py        # 只读
src/**  web/**  scripts/**  migrations/**
spec/**  contracts/**  prototype/**  docs/**
```
**禁自行提交**：你不跑 `git add` / `git commit`。改完 + 自验绿 + 落证据 + 写回执即止，
由编排器复验后单独提交（one-task-one-commit，§15.2）。

## 4. 自验命令（一律路径限定，避开在飞 lane W）

```bash
cd /home/szf/dev/CampaignLab
export PATH="$HOME/.local/bin:$PATH"

# 卡体口径自验（把 test_task_card_narrative 的 _split 原样复用，禁自造口径）
uv run --no-sync python - <<'PY'
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location(
    "narr", "tests/unit/test_task_card_narrative.py")
narr = importlib.util.module_from_spec(spec); spec.loader.exec_module(narr)
for c in ("M3-P02", "M5-P01", "M5-03"):
    t = pathlib.Path(f"orchestrator/tasks/{c}.md").read_text(encoding="utf-8")
    h, tl, tot, ht = narr._split(t)
    hdr = narr._header_of(t)
    print(c, "head", h, "<=60", h <= 60, "| tail", tl, "<=40", tl <= 40,
          "| total", tot, "<=200", tot <= 200, "| table", ht,
          "| header_ok", hdr == narr.REQUIRED_TABLE_HEADER)
PY

uv run --no-sync ruff format --check orchestrator/tasks/M3-P02.md \
  orchestrator/tasks/M5-P01.md orchestrator/tasks/M5-03.md \
  tests/unit/test_task_cards_complete.py tests/unit/test_task_cards.py
uv run --no-sync ruff check tests/unit/test_task_cards_complete.py tests/unit/test_task_cards.py
uv run --no-sync mypy        # 全表；期望 79 -> 80（你新增 1 个 .py）
uv run --no-sync pytest -q tests/unit/test_task_cards.py \
  tests/unit/test_task_cards_complete.py tests/unit/test_task_card_narrative.py \
  tests/unit/test_state_ledger.py tests/unit/test_wave_deps_consistency.py \
  tests/unit/test_counts_freshness.py
```
**反直觉点 ①**：`ruff format` 的 in-scope **包含 `.md`**（`pyproject.toml` 的
`extend-exclude` 只排除 `spec/prototype/web/node_modules`）。所以你新写的 3 张卡
**必须过 `ruff format --check`**，否则全表 ruff 分母那 225 会判红。
**反直觉点 ②**：`test_counts_freshness.py` 断言「台账 `ruff_formatted_files` ==
从 `git ls-tree -r HEAD` 重算的 py+md 件数」。你**未提交前**它必然红
（台账还是 225，而你新增了 4 个 in-scope 文件）—— 这是**预期的中间态红**，
编排器会在同一次提交里把 counts 刷成 229（py 81→82、md 144→147）。
你只需在回执里写明「`test_counts_freshness` 中间态红属预期，由编排器同批刷新」。
**反直觉点 ③**：`git status --porcelain` 的状态码是 **XY 两列 + 一个空格**共 3 字符前缀，
文件名从第 4 个字符起；用 `line[3:]` 取路径，禁 `split()`（含空格的路径会被切错）。
**反直觉点 ④**：仓库文件必须 **UTF-8 / 无 BOM / 无 `\r` / 以 `\n` 结尾**（`.md` 同样适用）。
**反直觉点 ⑤**：由 `contract_slice.py` 之类生成器产出的切片文件**可能缺尾换行**，
但你本 lane 不产切片（A179），此项仅供你识别他人产物时不要误改。

## 5. 写入通道铁律（§13.2 / §13.2.2 —— 违反必然静默损坏）

宿主是 Windows 11 PowerShell，仓库在 WSL2 ext4。**不要**用
`wsl.exe -e bash -lc "…"` 传含 `$`、`$(…)`、反引号或嵌套双引号的命令 —— PowerShell 先插值，
实测产生 `bash: unexpected EOF`、参数被吃、以及**字符级静默损坏**。
`sed -n "1,5p;9,12p"` 这种带 `;` 的多段表达式同样会被切碎。

正确姿势（每次写文件都走这三步）：
1. PowerShell 单引号 here-string：`$txt = (@'` … `'@) -replace "\`r\`n","\`n"`
2. `[System.IO.File]::WriteAllText($path,$txt,(New-Object System.Text.UTF8Encoding($false)))`
   写到 `D:\ws\codex_rd\ss_campaignlab\.orch_scratch\<name>`
3. `wsl.exe -e bash /mnt/d/ws/codex_rd/ss_campaignlab/.orch_scratch/<driver>.sh`
   （**bash 后接文件路径，不用 `-lc` 传内联脚本**），由 driver `cp` 进仓库并跑校验。

**R12-1（本轮新立的自我更正，务必遵守）**：本通道实测会把 Python 的
`except (A, B):` 元组形式损坏成 `except A, B:`（Python 3 语法错误）。因此：
① 你写的 Python **禁用** `except (A, B):`，一律拆成两个 `except` 子句；
② 每次写完 .py **必须**立刻
`python3 -c "import ast,pathlib;ast.parse(pathlib.Path('<file>').read_text())"` 自证语法，
禁写完直接跑测试（语法损坏会让测试结果完全不可信）。

**命令过长会撞 Windows `os error 206`**：拆成「数据文件 + 小 driver」。
**here-string 里禁止出现行首 `'@`**（会提前终止 here-string）。

## 6. 产出与回执

**证据落点** `evidence/M0/FU-33/`（自建）：
- `commands.md` —— 实跑的每条命令原文 + rc + 关键输出行（禁只写结论）
- `card-metrics.txt` —— §4 那段 `_split` 自验的原始输出（三张卡的 head/tail/total/header_ok）
- `positive-control.log` —— §2.3 第 4 条要求的「假树多卡 / 假树少卡」两种形态的 RED 原始输出
- `counts-drift.txt` —— 你实测的 `task_cards_on_disk` / `known_missing_cards` /
  `task_total_denominator` 台账现值 vs 磁盘实测值（D-042 的证据）
- `diff-stat.txt` —— `git diff --numstat -- <你的 write_set>` + 新文件的 `wc -c`

**回执格式**（最终消息，纯文本，≤ 90 行）：
1. `RESULT: PASS | PARTIAL | STALLED`
2. 三张卡逐项：head/tail/total/表头逐字核对结果、`REQUIRED_SECTIONS` 4 串命中、
   M5-03 的 `human_only_action` 标注位置（行号）
3. 新守护：用例数、双向断言与分母断言的实测值、正向对照 RED 证据路径
4. §4 全部命令的 rc 与期望值对账表（含 `test_counts_freshness` 中间态红的说明）
5. `U-项`：任何无法从卡/派单文确定的事，**如实上报禁猜**（A159）。
   每条写成「问题 + 两个候选方案 + 你倾向哪个及理由」。
   **特别地**：若你在 `spec/**` 里找不到某条 AC-MR 的原文，禁自己编判据，报 U 项。
6. `自报 token`（§15.5 入账；max 单任务上限 200k，超限即停并报 `over_cap`，禁抹平）
7. `IN_FLIGHT_CONTAMINATION`：你观察到的、归属 lane W 的红/多余文件清单（禁修）

## 7. L 循环上限（§4.1 + §15.6）

M5-P01 与 M5-03 都在**关键路径**上（`critical=true`，slack=0），故本 lane 的 L 循环
上限**收紧为 2 轮**：同一条守护连续 2 轮修不绿，**立即停手**写 `STALLED` 回执 +
BLOCKER 描述 + 一个「缩小范围」的降级交付选项（例如：先交 M5-P01/M5-03 两张关键卡 +
守护，M3-P02 顺延）交编排器裁定。禁第 3 轮硬试。
