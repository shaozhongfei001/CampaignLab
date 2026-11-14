# FU-35 · R13 lane V 自验命令台账（qwen3.8-flash）

- 基线：branch `m0-framework`，HEAD `d22b5f6`（95 commits；HEAD 树 ruff format 240 / mypy 81 files / pytest 503 passed）。
- 交付物：`tests/unit/test_orch_harness.py`（367 行，20 用例）＋本证据目录。被测工装 `scripts/orch_harness.py` 零改动。
- 全部命令路径限定，cwd `/home/szf/dev/CampaignLab`，工具链 `uv run --no-sync`。

## §6 自验命令（最终轮实测）

```bash
uv run --no-sync pytest -q -p no:cacheprovider tests/unit/test_orch_harness.py
# rc=0，20 passed

uv run --no-sync pytest -q -p no:cacheprovider --collect-only tests/unit/test_orch_harness.py
# rc=0，20 tests collected

uv run --no-sync mypy tests/unit/test_orch_harness.py
# rc=0，Success: no issues found in 1 source file

uv run --no-sync ruff format --check tests/unit/test_orch_harness.py evidence/M0/FU-35/commands.md
# rc=0，2 files already formatted

uv run --no-sync ruff check tests/unit/test_orch_harness.py
# rc=0，All checks passed!
```

## 语法自证（R12-1 写入通道防护）

每次落盘后 `python3 -c 'import ast; ast.parse(...)'` → `AST_OK`（rc=0）；scratch↔仓库 md5 双向一致。
本文件无 `except` 元组形式。

## 正向对照（原文见同目录 positive-control.log）

| 对照 | 判据 | 实测 | log 位置 |
| --- | --- | --- | --- |
| (a) TARGETS 副本塞 ghost 符号 | 覆盖分母守护必须红 | rc=1，`AssertionError: 符号 ghost_symbol_not_covered 在任何 test_ 函数体内都未出现` | log 第 30 行 `control_a_rc=1` |
| (b) rc=0 且文本未命中的 Proc | `_judge` 必须 `ok=False` | `GateResult(name='demo', rc=0, ok=False, detail='rc=0 text_ok=False forbid_hit=[]')`，rc=0 | log 第 35 行 |
| (c) 归不上的未跟踪件 | `classify_untracked` 必须放进 `outside` | `outside=['web/stray.md']` `attributed={}`，rc=0 | log 第 41 行 |

对照全程走 tmp 副本 / 一次性进程，测试文件本体未改：sha256
`5d53415657a13b89987801b638581ce8479e81717cc994dc131775a002f08ff9` 双向核验一致
（log `sha_verify_rc=0`），复原后 20 用例复绿（log `final_pytest_rc=0`）。

## 备注

- §6 的 `ruff format --check` 实测接受本 `.md`（rc=0）。
- 工装取用方式偏离 §5 字面（`__import__` + `h: Any` 取代 `import orch_harness as h`）：
  字面形式在路径限定 mypy 下必然 `import-not-found`（`mypy_path` 只含 `src`，pyproject 非本 lane 写权），
  详见回执 U-1。
- 全表实测口径（供编排器参考，非本 lane 判据）：`uv run --no-sync mypy`（全表）86 source files 全绿
  = 基线 81 + lane Y 在飞 4 个 .py + 本文件。
