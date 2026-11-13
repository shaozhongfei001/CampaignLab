# LANE-COMMON · 全体子智能体公共纪律（R13 起抽取，依 R12-5 / A183 的降批义务）

> 本文件是**所有** lane 派单文的公共前置段。各 lane 派单文只写「本 lane 特有」的任务、写权、
> 守护判据与证据要求，公共部分一律引用本文件而不重述（目的：把单份派单文压到 ≤110 行，
> 使 lane 的单轮上下文落回手册 §5.1 的输入上限内 —— max 40k / flash 12k）。
> 权威条款：`docs/delivery/LONG-HORIZON-ORCHESTRATION.md` v1.7。冲突时**手册胜**。

## 1. 环境与仓库

- 仓库：WSL2 Ubuntu ext4 `/home/szf/dev/CampaignLab`；宿主：Windows 11，PowerShell，
  宿主侧 cwd = `D:\ws\codex_rd\ss_campaignlab`。
- 工具链一律 `uv run --no-sync <tool>`（`uv` 在 `~/.local/bin/uv`；非登录 shell 里先
  `export PATH="$HOME/.local/bin:$PATH"`）。**禁**加 `PYTHONPATH=src` 前缀（D-014）。
- 所有构建、测试、git 操作在 WSL 内执行；依赖只在 ext4，**禁**在 `/mnt/d` 下安装依赖或构建。
- `spec/**` 与 `contracts/**` **只读**（§1 不变量）。`gh` 未认证，禁建 PR / 禁触发 workflow。

## 2. 写入通道铁律（§13.2 / §13.2.2 —— 违反必然静默损坏）

**禁用** `wsl.exe -e bash -lc "…"` 承载含 `$`、`$(…)`、反引号、嵌套双引号、或 `;` 多段表达式
（如 `sed -n "1,5p;9,12p"`）的命令 —— PowerShell 会**先插值**，实测产生 `unexpected EOF`、
参数被吃掉、以及**字符级静默损坏**。

正确姿势，每次写文件都走这三步：

1. PowerShell 单引号 here-string 装文本，并把 CRLF 归一为 LF：
   `$txt = (@'` … `'@) -replace "\`r\`n","\`n"`
2. 落盘到宿主 scratch（UTF-8 **无 BOM**）：
   `[System.IO.File]::WriteAllText($path,$txt,(New-Object System.Text.UTF8Encoding($false)))`
   `$path` 取 `D:\ws\codex_rd\ss_campaignlab\.orch_scratch\<name>`
3. 用 **bash 接文件路径**（不是 `-lc` 内联）驱动：
   `wsl.exe -e bash /mnt/d/ws/codex_rd/ss_campaignlab/.orch_scratch\<driver>.sh`
   由 driver 把文件 `cp` 进仓库并跑校验。

补充硬规则：

- **R12-1**：本通道实测会把 Python 的 `except (A, B):` 损坏成 `except A, B:`（Python 3 语法错误），
  且损坏是**静默**的、一度还骗过了 ruff 与 mypy。故 ① 你写的 Python **禁用** except 元组形式，
  一律拆成多个 `except` 子句；② 每次写完 `.py` **必须立刻**自证语法：
  `python3 -c 'import ast,sys;ast.parse(open(sys.argv[1],encoding="utf-8").read())' <file>`。
  禁写完直接跑测试 —— 语法损坏会让此后所有测试结果完全不可信（绿是假绿、红是错红）。
- **here-string 里禁出现行首 `'@`**（会提前终止 here-string）。写 Markdown 时尤其注意。
- 命令过长会撞 Windows **`os error 206`**（命令行长度上限）：拆成「数据文件 + 小 driver」。
- 仓库文件（**含 `.md` 与证据文件**）必须 **UTF-8 / 无 BOM / 无 `\r` / 以 `\n` 结尾**。
- sudo 密码只经 **stdin** 传入，**禁落盘**、禁写进任何提交物（§15.7）。

## 3. 仓库反直觉事实（台账已记录在案者，原文照录；踩过的坑别再踩）

1. **`ruff format` 的作用域含 `.md`**（A175）。`pyproject.toml` 的 `extend-exclude` 只排除
   `spec/ prototype/ web/ node_modules`，所以你新写的 `.md`（任务卡、证据、回执）**必须过**
   `ruff format --check`，否则全表 ruff 分母那一门判红。证据里的 ``` 围栏会被重排。
2. **`git status --porcelain` 每行带 3 字符状态前缀**（R11-1）：`XY` 两列 + 一个空格，
   路径从第 4 个字符起。取路径用 `line[3:]`，**禁** `split()`（含空格的路径会被切错）。
3. **生成器产物可能缺尾换行**（A170）：`scripts/contract_slice.py` 之类生成器切出的
   `.slice.json` 不带尾 `\n`。识别他人产物时**不要**顺手「修正」它。
4. **`mypy` 全表口径无路径限定**：`pyproject.toml` 的 `files = ["src","tests","scripts"]`，
   所以 `uv run --no-sync mypy` 一定是全表，会扫到**在飞 lane 的未入库 .py** 并报它们的错。
   要自证「我没引入类型错」，用 `mypy --exclude <在飞文件>` 反证，禁去改别人的文件。
5. **`mypy` strict 开了 `no_implicit_reexport`**：「import 进来但没进 `__all__`」的名字
   **不算**再导出，下游 `from X import Y` 会判 mypy 错。搬移公开符号时必须同步维护 `__all__`。
6. **新增 `conftest.py` 或与既有文件同 basename 的新文件**，必须跑一次**全树** mypy：
   路径限定 mypy 不触发跨目录重复模块名检测（`rule_full_tree_mypy_on_basename_collision`，
   立规原因 = R8-4 / D-035，当时因此漏检了 G9 全表红灯）。

## 4. 共享工作树与在飞污染（A161）

同一轮可能有多条 lane **共享同一个工作树**。因此：

- 你的自验**一律路径限定**（派单文 §「自验命令」给全）。**禁**跑全表门禁当作自己的判据。
- 全表门禁由**编排器**在**冻结索引树**上复跑（`git checkout-index -a -f --prefix=<scratch>/`
  + 软链 `.venv`/`.git`），该树只含**已入索引**的内容，天然隔离在飞 lane（R11-3）。
- 你在工作树上看到的、**不属于你 write_set** 的红点与多余文件 = `IN_FLIGHT_CONTAMINATION`，
  **不是你的 RED，也禁你去修**（A161：复验方对在飞面禁写）。把它如实记进回执的
  `IN_FLIGHT_CONTAMINATION` 段即可。
- 基线对账口径 = **派单消息给你的 HEAD sha 那棵树 + 你 write_set 的增量**。
  **禁**拿工作树快照当基线（R11-7①）。

## 5. 交付纪律

- **禁自行 `git add` / `git commit`**：one-task-one-commit 归编排器（§15.2）。
  改完 + 自验绿 + 落证据 + 写回执即止。
- **禁写 `orchestrator/**`**（台账 `state.json`、任务卡、缺陷单、handoff 一律归编排器），
  除非你的派单文 write_set 里**显式**列出了某个 `orchestrator/` 路径。
- 只用显式路径，**禁** `git add -A`（§15.2）。
- 任何无法从任务卡 / 派单文 / `spec/**` 确定的事 → **如实报 U 项，禁猜**（A159）。
  每条 U 项写成「问题 + 两个候选方案 + 你倾向哪个及理由」。**禁**自己发明判据、
  期望值、opId 或 AC 原文。
- 派单文里凡写「以实取为准」的量（`__all__` 项数、用例数、行数、分母），一律用
  `inspect` / `ast` / `--collect-only` **实取**并抄进证据，**禁**写推断值
  （R8-1 / A115 `rule_no_hardcoded_symbol_counts`；R12-4 `rule_no_hardcoded_tool_verdicts`：
  连 import 序这类**工具裁决**也禁写死，以 `ruff check --select I --diff` 实取为准）。

## 6. 守护必须有牙（手册 §15.4 / A159）

- 你新建或改写的每一条守护，都必须附**正向对照**：主动制造一次 RED、把原始输出落进证据、
  再复原并复验绿。**只交绿证据无法区分「守护有效」与「守护恒绿」，缺此判红。**
- 探针一律用 pytest 的 `tmp_path`，**禁落工作树**（否则会污染 ruff/mypy 分母）。
- 复原必须**可证**：用 sha256 双向核验（改前快照 == 复原后），把两个摘要都写进证据。
- 守护必须自带**分母断言**（防 glob 扫空导致全绿）。
- 判据之间**不得互相否证**，且必须能在**未改动的 HEAD 树上**成立（R12-3
  `rule_verifier_must_be_self_consistent`）：写完先空跑一遍，凡在 HEAD 上即红的判据都是错判据。

## 7. 回执格式（最终消息，纯文本，≤ 90 行）

1. `RESULT: PASS | PARTIAL | STALLED`
2. 逐子任务：改了哪个文件、`git diff --numstat` 实测值、关键判据的**实测**值
3. 自验命令对账表：每条命令的 rc 与「实测 vs 期望」
4. 正向对照证据路径（含 RED 原文位置）
5. `U-项`：逐条「问题 + 两个候选 + 倾向及理由」
6. `自报 token`：两个口径都给 —— **单轮上下文规模** 与 **跨轮累计计费**（A183：
   §15.5 的上限按累计计费口径判定；越限即如实报 `over_cap`，**禁抹平**、
   禁改用「纯产出部分在上限内」这类口径）
7. `L 循环状态`：用了几轮 / 上限几轮 / 是否触发 STALLED
8. `IN_FLIGHT_CONTAMINATION`：归属其他 lane 的红点与多余文件清单（禁修）

## 8. L 循环上限（§4.1 + §15.6）

- `critical=true`（slack=0）的 lane：L 循环上限 **2 轮**。
- 其余：上限 3 轮；slack ≥ 4 的允许 3 轮 + 1 轮 max 复审。
- 同一条守护连续 2 轮修不绿 → **立即停手**，写 `STALLED` 回执 + BLOCKER 描述 +
  **一个「缩小范围」的降级交付选项**（降范围不降质量）交编排器裁定。**禁**第 3 轮硬试。
