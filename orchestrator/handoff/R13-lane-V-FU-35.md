# R13 · Lane V · FU-35 派单文（qwen3.8-flash / medium · 非关键路径 · loop_cap=3）

> **第一步必做**：完整读 `orchestrator/handoff/LANE-COMMON.md`。本文只写本 lane 特有内容（R12-5）。

## 0. 基线（编排器实测）

- branch `m0-framework`，HEAD = **`d22b5f6`（95 commits）**；HEAD 树基线：`ruff format --check` **240**、
  `mypy` **81 source files**、`pytest` **503 passed**（= 482 frozen + 21 GIT_ENV_IGNORES 静态收集）。
- 在飞：lane Y（`src/campaignlab/worker/{integrity,deps}.py` + `tests/unit/test_worker_integrity.py`）、
  lane Z（`orchestrator/handoff/M2-01-design.md`）。**自验一律路径限定**，禁跑全表门禁当判据；
  全表 mypy 会因它们的未入库 `.py` 报 82+ 而非 81，那不是你的红，禁修。

## 1. 任务：给 `scripts/orch_harness.py` 补单测（FU-35）

该工装是编排器「一任务一提交」的唯一通道（卫生 → 台账 → 显式 add → 冻结树四门双判 → 实测对账 →
越界分类 → 悬空扫描 → commit → 复验），至今只以「本提交由它自身把门」自证，**无任何单测**。
交付物 = **一个新文件**：`tests/unit/test_orch_harness.py`。

**禁读整份 630 行工装**（flash 输入上限 12k，整读会挤爆上下文）。只读下列行段：

```text
26-70    常量（REPO / COUNTS_JSONPATH / EXCLUDED_PREFIXES / RUFF_SUFFIXES / GIT_ENV_IGNORES / _UV）
         + HarnessError + Proc + GateResult + CommitReport
116-150  normalize_file / normalize_many / in_scope
168-195  untracked_in_scope / classify_untracked
213-224  _judge
262-296  gate_number / all_green
296-332  load_state / get_counts / dump_state / _is_mypy_scope
373-394  set_counts
409-420  write_msg_file
434-461  DANGLING_SWEEP_SKIP / dangling_refs
```

## 2. 必须覆盖的 12 个符号（逐个都要有牙）

1. `in_scope(rel)`：纯函数。对照 `web/x.md`→False、`docs/x.txt`→False、`docs/x.md`→True、`src/a.py`→True。
2. `_is_mypy_scope(rel)`：纯函数。对照 `scripts/x.py`→True、`tests/y.py`→True、`web/x.py`→False、`docs/x.md`→False。
3. `normalize_file(path)`：`tmp_path`。三种修正各一条（`BOM_REMOVED` / `CR_REMOVED` / `TRAILING_NL_ADDED`）
   ＋ 已合规文件返回 `[]`（**且断言文件内容未被改写**）。
4. `normalize_many(paths)`：`tmp_path`。只把**实际被修正**的收进字典（返回值为空列表者不入键）。
5. `write_msg_file(msg, path)`：`tmp_path`。CRLF→LF、无尾 `\n` 则补、开头 BOM 被剥离；返回值 `== path`。
6. `_judge(name, Proc, pattern, forbid)`：构造 `Proc`。**四条对照**（这是「双判规则」的本体，缺一即失去意义）：
   rc=0 ＋ 文本命中 ＋ 无禁词 → `ok=True`；rc=1 → False；rc=0 但文本未命中 → False；
   rc=0 且文本命中但命中禁词 → False。
7. `gate_number(GateResult, pattern)`：命中→整数；未命中→`None`；并验证「先搜 `tail` 再搜 `detail`」的次序
   （两者都放数字但不同时，取 `tail` 的那个）。
8. `all_green(gates)`：全 True→True；任一 False→False；**空字典→True** —— 把这条写成显式断言并在
   docstring 注明它是「空集上的全称命题」陷阱（LANE-COMMON §6 的分母断言同源风险）。
9. `get_counts(state)`：正常取值；**缺键→`HarnessError`**；该路径上非 dict→`HarnessError`（两条都要测）。
10. `set_counts(state, values, reason=, at=)`：值变化→`previous_values_last` 记旧值；值未变→**不记**该键；
    `counts_refreshed_at` / `counts_refresh_reason` 被写入；返回值与 `get_counts(state)` 是**同一对象**
    （用 `is` 断言，证明它改的是引用而非副本 —— 这是 `run_commit` 台账落盘正确性的前提）。
11. `classify_untracked(owner_map)`：monkeypatch `h.untracked_in_scope` 返回固定清单。三种前缀匹配形态各一条
    （`f == p` / `f` 在 `p` 目录下 / `f.startswith(p)`）；归不上的进 `outside`；`owner_map=None` → 全部进 `outside`。
12. `dangling_refs(paths)`：monkeypatch `h.REPO` 到 `tmp_path`。引用不存在路径→报出；引用存在路径→不报；
    `orchestrator/state.json` 被跳过（`DANGLING_SWEEP_SKIP`）；后缀不在 `.md/.json/.py/.txt/.jsonl` 的被跳过；
    尾随标点被 `rstrip`（如 `docs/a.md。` 与 `docs/a.md)` 都应解析为 `docs/a.md`）。

## 3. 覆盖分母守护（禁静默删测）

必须有一条 `test_every_target_symbol_is_covered`：读本测试文件**自己的源码**，对模块级常量
`TARGETS`（上述 12 个符号名的 `frozenset`）逐个断言该名字在本文件的测试函数体内至少出现一次；
并断言 `len(TARGETS) == 12`（**分母钉死**，防 TARGETS 被清空导致 vacuous green）。

## 4. 写权与硬禁

**只许写**：`tests/unit/test_orch_harness.py`、`evidence/M0/FU-35/commands.md`、`evidence/M0/FU-35/positive-control.log`
**硬禁（写一个即整条 lane 判红）**：**`scripts/orch_harness.py` 一个字都不许改**（它是被测对象；
若你认为它有 bug → **报 U 项**，禁自行修）；`src/**`、`web/**`、`contracts/**`、`spec/**`、`docs/**`、
`migrations/**`、`orchestrator/**`（含台账/卡片/handoff）、`tests/` 下除你那一个文件外的一切。
**禁自行 `git add` / `git commit`**（LANE-COMMON §5）。

## 5. 技术硬约束

- **纯单元测试**：禁 `subprocess`、禁任何 git 调用、禁跑工具链、禁触网；只准用 `tmp_path`。
  凡需要 git/子进程的符号（`sh` `git` `git_out` `head_sha` `branch` `status_porcelain` `tracked_in_scope`
  `predict_counts` `predict_pytest` `stage` `commit_staged` `frozen_tree` `run_gates` `count_git_env_ignores`
  `load_state` `dump_state` `run_commit` `commit_and_verify` `main`）**不在本 lane 范围，禁测**。
- import 面只允许：`sys` / `pathlib` / `pytest` / `typing` ＋ 工装本体。取工装用
  `sys.path.insert(0, str(REPO / "scripts"))` 后 `import orch_harness as h`（`REPO` 自己用
  `Path(__file__).resolve().parents[2]` 求，禁写死绝对路径）。**禁** import `campaignlab` 任何东西。
- **禁 except 元组形式**（R12-1 静默损坏）；写完 `.py` **立刻** ast.parse 自证语法再跑测试。
- monkeypatch 一律用 pytest 的 `monkeypatch` fixture（自动还原），禁手工改模块属性不还原。
- mypy strict 干净、**无 `type: ignore`**；`ruff format --check` 与 `ruff check` 干净。
- 文件卫生：UTF-8 / 无 BOM / 无 `\r` / 以 `\n` 结尾（`.md` 证据同）。

## 6. 自验（全部路径限定）＋正向对照

```bash
cd /home/szf/dev/CampaignLab && export PATH="$HOME/.local/bin:$PATH"
uv run --no-sync pytest -q -p no:cacheprovider tests/unit/test_orch_harness.py
uv run --no-sync pytest -q -p no:cacheprovider --collect-only tests/unit/test_orch_harness.py
uv run --no-sync mypy tests/unit/test_orch_harness.py
uv run --no-sync ruff format --check tests/unit/test_orch_harness.py evidence/M0/FU-35/commands.md
uv run --no-sync ruff check tests/unit/test_orch_harness.py
```

正向对照 ≥3 条，原始输出留 `evidence/M0/FU-35/positive-control.log`，**全部用 tmp_path / 局部变量构造，
禁改本测试文件本体**（若确需改本体，必须 sha256 双向核验复原并把两个摘要写进证据）：
(a) 往 `TARGETS` 的**副本**里加一个不存在的符号名 → 覆盖分母守护必须红；
(b) 构造 rc=0 但文本未命中的 `Proc` → `_judge` 必须 `ok=False`；
(c) 构造一个 `owner_map` 归不上的未跟踪件 → `classify_untracked` 必须把它放进 `outside`。

## 7. 回执（LANE-COMMON §7 的 8 段，≤90 行）

第 2 段给 `git diff --numstat` 与 collected 用例数；第 3 段给 §6 每条命令的 rc 与「实测 vs 期望」；
第 4 段给三条正向对照的 RED 原文位置；第 5 段 U 项（含你在工装里发现的任何可疑处，**只报不改**）；
第 6 段自报 token 两口径（**flash 累计计费上限 60k**，A183，越限如实报 `over_cap` 禁抹平）；
第 7 段 L 循环用量；第 8 段 IN_FLIGHT_CONTAMINATION（归 Y/Z 的红点与多余文件，禁修）。

## 8. L 循环

上限 **3 轮**。同一条守护连续 2 轮修不绿 → **立即停手**，写 `STALLED` 回执 + BLOCKER + 一个
「缩小范围不降质量」的降级交付选项交编排器裁定，禁第 3 轮硬试。
