# M0-04/S7 commands 记账（lane U / Hertz，专属文件；**未触碰** `commands.md`）

四元组 = cwd + 命令 + rc + 关键输出。所有 rc 由 `subprocess.run(...).returncode` 采集（禁 `$?`）。
除标注外 cwd 均为 `/home/szf/dev/CampaignLab`。

| # | 命令 | rc | 关键输出 |
|---|------|----|----------|
| 1 | `python3 -c <切片定点探测>`（读 `orchestrator/handoff/M0-04.slice.json`） | 0 | `truncated_schemas=[]`；顶层无 `components`；`Job.required` 13 项、`kind` 10、`state` 6、`ObjectRef.kind` 20、`Problem.required` 7、`Issue.severity` 3；`Problem.code` 无 enum（pattern/maxLength 96） |
| 2 | `python3 /mnt/d/ws/codex_rd/ss_campaignlab/.orch_tmp/hertz_probe4.py`（读 `ddl.jobs`） | 0 | `jobs` 表含 `lease_token`/`lease_until` 列与 `CHECK(state IN (6 值))` |
| 3 | `python3 /mnt/d/ws/codex_rd/ss_campaignlab/.orch_tmp/hertz_write.py`（写入新文件 + 回读断言） | 0 | `WROTE bytes=12576`（首轮，后经 E501 修补为 12679）；回读无 BOM、无 `\r`、以 `\n` 结尾 |
| 4 | `uv run --no-sync ruff format tests/unit/test_job_dto.py`（第 1 轮） | 0 | `1 file reformatted` |
| 5 | `uv run --no-sync ruff check tests/unit/test_job_dto.py`（第 1 轮） | 1 | 2×E501（docstring 中 CJK 宽度 115/117 > 100）→ 第 2 轮改写该两行 |
| 6 | `uv run --no-sync ruff check tests/unit/test_job_dto.py`（第 2 轮） | 0 | `All checks passed!` |
| 7 | `uv run --no-sync mypy tests/unit/test_job_dto.py`（第 2 轮） | 1→（同轮 pytest） | 首轮 `pytest` 4 failed：`_names()` 只接受 list（`JOB_STATES`/`get_args()` 为 tuple；`Job.properties` 为 dict） |
| 8 | `python3 /mnt/d/ws/codex_rd/ss_campaignlab/.orch_tmp/hertz_fix1.py`（第 3 轮修补） | 0 | `PATCHED bytes=12679 lines=299` |
| 9 | `uv run --no-sync ruff format tests/unit/test_job_dto.py` | 0 | `1 file left unchanged` |
| 10 | `uv run --no-sync ruff check tests/unit/test_job_dto.py` | 0 | `All checks passed!` |
| 11 | `uv run --no-sync mypy tests/unit/test_job_dto.py` | 0 | `Success: no issues found in 1 source file` |
| 12 | `uv run --no-sync pytest -q tests/unit/test_job_dto.py` | 0 | `66 passed in 0.30s`（作用域套件全绿） |
| 13 | `uv run --no-sync ruff check .` | 0 | `All checks passed!` |
| 14 | `uv run --no-sync ruff format --check .` | 0 | `217 files already formatted`（基线 214，含本卡 1 个新文件 + 其他 lane 在飞新增） |
| 15 | `uv run --no-sync mypy` | 0 | `Success: no issues found in 78 source files`（基线 77 + 本卡新文件） |
| 16 | `uv run --no-sync pytest -q` | 0 | `482 passed, 6 warnings in 80.48s`；failed=0（416 基线 + 66 = 482） |
| 17 | `uv run --no-sync pytest -q tests/unit/test_job_dto.py`（全量后复跑） | 0 | `66 passed in 0.27s` |

loop_used（件一）= **3**（上限 3）：
1. E501（CJK 显示宽度）→ 拆分/改写 docstring 两行；
2. `_names()` 类型契约过窄（只认 list）→ 放宽为 list/tuple 并去掉不必要的 `cast`，
   `Job.properties` 改用键集而非 `_names`；
3. 复跑四门（format/check/mypy/pytest）全 rc=0，矩阵与全量零回归。

## 收工复测（同轮，证据落盘后）
- `ruff format --check .` rc=0 → `221 files already formatted`（在飞 lane 又新增 .py，数字随之变动）
- `pytest -q tests/unit/test_job_dto.py` rc=0 → `66 passed`
- 7 个函数名逐字实测在位（`grep -nE '^def test_' tests/unit/test_job_dto.py` → 139/160/172/190/206/231/242 行）
- M0-02/S4 三个在册函数名在本文件命中数 0；新建 `conftest.py` 数 0
- 越界自证：(a) 0、(b) `web/vite.config.ts` = `1  1`、`tests/unit/test_job_dto.py` 无 numstat 输出、(c) 见 r11-fu32/commands.md
