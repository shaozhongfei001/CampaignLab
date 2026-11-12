# M0-02 · S2 命令与实测 rc（commands.md）

> **本文件当前只覆盖 S2（首迁）所属的 V 编号**：Q7 自证、V1、V2、V3、V4、V10、V11、V12。
> V5–V9、V13 属 S3/S4/S5（会话 / 工作区 / Problem / HTTP 样本），由 S5 后续**追加**，
> 追加时请勿改写本文件已有的实测行（手册 15.9 / 15.10：历史测量值不重写）。

- 执行位置：WSL2 仓库根 `/home/szf/dev/CampaignLab`，分支 `m0-framework`，起始 HEAD `42079fa`。
- 全部 rc 与输出**由脚本实跑捕获**，无转录、无估算；时间戳为 `TZ=Asia/Shanghai date -Is`。
- 命令一律用**原文**，不带 `PYTHONPATH=src` 前缀（裁定 Q7 / 缺陷 D-014）。
- 前置：`export PATH="$HOME/.local/bin:$HOME/.local/share/node/bin:$PATH"`（本子任务未运行任何 npm/node 命令）。

## 0. 环境行

| 组件 | 实测版本 |
|---|---|
| OS | `Ubuntu 24.04.2 LTS` |
| 内核/架构 | `Linux 6.18.58.1-microsoft-standard-WSL2 x86_64 GNU/Linux` |
| CPython（patch 级） | `3.14.10 3.14.10` |
| sqlite_version | `3.53.1` |
| uv | `uv 0.13.7 (x86_64-unknown-linux-gnu)` |
| alembic | `alembic 1.20.1` |
| SQLAlchemy | `2.0.57` |
| ruff | `ruff 0.17.4` |
| mypy | `mypy 2.4.1 (compiled: yes)` |
| pytest | `pytest 9.2.0` |

`pyproject.toml` 变更：删除 `[tool.uv] package = false`（保留历史留痕注释）→ `uv lock` rc=0 →
`uv sync` rc=0，构建并安装 `campaignlab==0.0.0`（editable）。

**如实记录一处与裁定原文的偏差**：裁定 Q7 预期「hatchling 进锁」，实测 `uv lock` 后
`uv.lock` 的唯一变化是 `campaignlab` 的 `source = { virtual = "." }` → `{ editable = "." }`，
`grep -c hatchling uv.lock` 返回 **0**（rc=1，无匹配）。uv 0.13.7 不把本地可安装成员的
build-backend 依赖写进锁文件；构建在 `uv sync` 时按需解析。锁与运行环境仍然清楚可复现，
但**「hatchling 进锁」这一句预期与实际工具行为不符**，已列入未决问题交编排器裁定。

## 1. PRE-3 契约新鲜度三方比对（开工第一步，一致才可继续）

| 来源 | sha16 | bytes |
|---|---|---|
| 实算 `contracts/openapi.json` | `592571099d638251` | 443309 |
| 权威 `orchestrator/state.json → resume.self_check_gates_rc0.counts` | `592571099d638251` | 443309 |
| 切片 `orchestrator/handoff/M0-02.slice.json → source.openapi` | `592571099d638251` | 443309 |

结论：**三方一致 = `True`** → 切片新鲜，继续派工。

## 2. 逐条命令 → 实测 rc

| # | V 编号 | 命令 | 实测 rc | 时间戳（Asia/Shanghai） |
|---|---|---|---|---|
| 1 | — | `uv run --no-sync python -c "import platform,sys;print(platform.python_version(), sys.version.split()[0])"` | **0** | `2026-11-13T03:41:21+08:00` |
| 2 | — | `uv run --no-sync python -c "import sqlite3;print(sqlite3.sqlite_version)"` | **0** | `2026-11-13T03:41:21+08:00` |
| 3 | — | `uv --version` | **0** | `2026-11-13T03:41:21+08:00` |
| 4 | — | `uv run --no-sync alembic --version` | **0** | `2026-11-13T03:41:21+08:00` |
| 5 | — | `uv run --no-sync python -c "import sqlalchemy;print(sqlalchemy.__version__)"` | **0** | `2026-11-13T03:41:21+08:00` |
| 6 | — | `uv run --no-sync ruff --version` | **0** | `2026-11-13T03:41:22+08:00` |
| 7 | — | `uv run --no-sync mypy --version` | **0** | `2026-11-13T03:41:22+08:00` |
| 8 | — | `uv run --no-sync pytest --version` | **0** | `2026-11-13T03:41:22+08:00` |
| 9 | — | `lsb_release -ds 2>/dev/null \|\| cat /etc/os-release \| head -2` | **0** | `2026-11-13T03:41:22+08:00` |
| 10 | — | `uname -srmo` | **0** | `2026-11-13T03:41:22+08:00` |
| 11 | Q7 自证 | `uv run --no-sync python -c "import campaignlab; print(campaignlab.__file__)"` | **0** | `2026-11-13T03:41:22+08:00` |
| 12 | V10 | `uv run --no-sync python -m campaignlab doctor` | **1** | `2026-11-13T03:41:22+08:00` |
| 13 | AC-035 | `uv lock --check` | **0** | `2026-11-13T03:41:22+08:00` |
| 14 | V1 / PRE-3 | `uv run --no-sync python -c "import hashlib,pathlib;d=pathlib.Path('contracts/openapi.json').read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))"` | **0** | `2026-11-13T03:41:22+08:00` |
| 15 | V2 | `uv run --no-sync python scripts/check_contracts.py check --validate` | **0** | `2026-11-13T03:41:22+08:00` |
| 16 | V3 | `CAMPAIGNLAB_DATA_DIR=/tmp/s2ev_2iq_y294 uv run --no-sync alembic -c migrations/alembic.ini upgrade head` | **0** | `2026-11-13T03:41:24+08:00` |
| 17 | V3+ | `CAMPAIGNLAB_DATA_DIR=/tmp/s2ev_2iq_y294 uv run --no-sync alembic -c migrations/alembic.ini current` | **0** | `2026-11-13T03:41:25+08:00` |
| 18 | V3+ | `CAMPAIGNLAB_DATA_DIR=/tmp/s2ev_2iq_y294 uv run --no-sync alembic -c migrations/alembic.ini downgrade base` | **0** | `2026-11-13T03:41:26+08:00` |
| 19 | V3 | `CAMPAIGNLAB_DATA_DIR=/tmp/s2ev_2iq_y294 uv run --no-sync alembic -c migrations/alembic.ini upgrade head` | **0** | `2026-11-13T03:41:26+08:00` |
| 20 | V4 | `uv run --no-sync pytest -q tests/integration/bootstrap/test_migration_equivalence.py` | **0** | `2026-11-13T03:41:27+08:00` |
| 21 | V4+ | `uv run --no-sync pytest -q tests/unit/test_migration_schema.py` | **0** | `2026-11-13T03:41:39+08:00` |
| 22 | V11 | `uv run --no-sync ruff check . && uv run --no-sync ruff format --check .` | **0** | `2026-11-13T03:41:40+08:00` |
| 23 | V12 | `uv run --no-sync mypy && uv run --no-sync pytest -q` | **0** | `2026-11-13T03:41:40+08:00` |

## 3. 逐条输出（原样，长输出按字符截断）

### 1. [—] rc=0

```console
$ uv run --no-sync python -c "import platform,sys;print(platform.python_version(), sys.version.split()[0])"
3.14.10 3.14.10
```

### 2. [—] rc=0

```console
$ uv run --no-sync python -c "import sqlite3;print(sqlite3.sqlite_version)"
3.53.1
```

### 3. [—] rc=0

```console
$ uv --version
uv 0.13.7 (x86_64-unknown-linux-gnu)
```

### 4. [—] rc=0

```console
$ uv run --no-sync alembic --version
alembic 1.20.1
```

### 5. [—] rc=0

```console
$ uv run --no-sync python -c "import sqlalchemy;print(sqlalchemy.__version__)"
2.0.57
```

### 6. [—] rc=0

```console
$ uv run --no-sync ruff --version
ruff 0.17.4
```

### 7. [—] rc=0

```console
$ uv run --no-sync mypy --version
mypy 2.4.1 (compiled: yes)
```

### 8. [—] rc=0

```console
$ uv run --no-sync pytest --version
pytest 9.2.0
```

### 9. [—] rc=0

```console
$ lsb_release -ds 2>/dev/null || cat /etc/os-release | head -2
Ubuntu 24.04.2 LTS
```

### 10. [—] rc=0

```console
$ uname -srmo
Linux 6.18.58.1-microsoft-standard-WSL2 x86_64 GNU/Linux
```

### 11. [Q7 自证] rc=0

```console
$ uv run --no-sync python -c "import campaignlab; print(campaignlab.__file__)"
/home/szf/dev/CampaignLab/src/campaignlab/__init__.py
```

说明：删除 `[tool.uv] package = false` 后 `campaignlab` 可**直接导入**，gate 命令不再需要 `PYTHONPATH=src` 前缀（D-014）

### 12. [V10] rc=1

```console
$ uv run --no-sync python -m campaignlab doctor
/home/szf/dev/CampaignLab/.venv/bin/python: No module named campaignlab.__main__; 'campaignlab' is a package and cannot be directly executed
```

说明：`doctor` CLI 与 `__main__` 属 **S3** 交付物，S2 时点尚未存在 → **rc=1 为如实现状，非 S2 缺陷**；本子任务只负责 Q7 裁定的前半段（可导入性）

### 13. [AC-035] rc=0

```console
$ uv lock --check
Resolved 52 packages in 2ms
```

说明：锁文件与 pyproject 一致（删 `package = false` 后重锁的结果自洽）

### 14. [V1 / PRE-3] rc=0

```console
$ uv run --no-sync python -c "import hashlib,pathlib;d=pathlib.Path('contracts/openapi.json').read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))"
592571099d638251 443309
```

说明：契约新鲜度。设计档 §5 V1 原文写的 `01bd28f0772f506e 443552` 已因 CR-002/ADR-006 **作废**；按 D-013/D-014 改为与 `state.json` 权威键 + 切片三方比对

### 15. [V2] rc=0

```console
$ uv run --no-sync python scripts/check_contracts.py check --validate
CONTRACT CHECK PASS 登记项=13 实测差异=13 元校验=6
```

说明：活契约门禁未回归（S2 未触碰 `contracts/**`）

### 16. [V3] rc=0

```console
$ CAMPAIGNLAB_DATA_DIR=/tmp/s2ev_2iq_y294 uv run --no-sync alembic -c migrations/alembic.ini upgrade head
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema, 首迁：CampaignLab SQLite v1 的 28 张表与 6 个显式索引。
```

说明：首迁可执行；数据目录由 `CAMPAIGNLAB_DATA_DIR` 注入，库落在 `<data_dir>/state/campaignlab.db`

### 17. [V3+] rc=0

```console
$ CAMPAIGNLAB_DATA_DIR=/tmp/s2ev_2iq_y294 uv run --no-sync alembic -c migrations/alembic.ini current
0001_initial_schema (head)
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
```

说明：head 簿记为 `0001_initial_schema`，即 `Health.schema_revision` 的取值来源

### 18. [V3+] rc=0

```console
$ CAMPAIGNLAB_DATA_DIR=/tmp/s2ev_2iq_y294 uv run --no-sync alembic -c migrations/alembic.ini downgrade base
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0001_initial_schema -> , 首迁：CampaignLab SQLite v1 的 28 张表与 6 个显式索引。
```

说明：downgrade 完整可逆：逆序 DROP 6 索引 + 28 表

### 19. [V3] rc=0

```console
$ CAMPAIGNLAB_DATA_DIR=/tmp/s2ev_2iq_y294 uv run --no-sync alembic -c migrations/alembic.ini upgrade head
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema, 首迁：CampaignLab SQLite v1 的 28 张表与 6 个显式索引。
```

说明：首迁可执行；数据目录由 `CAMPAIGNLAB_DATA_DIR` 注入，库落在 `<data_dir>/state/campaignlab.db`

### 20. [V4] rc=0

```console
$ uv run --no-sync pytest -q tests/integration/bootstrap/test_migration_equivalence.py
............                                                             [100%]
12 passed in 10.76s
```

说明：DDL 等价 + 28 表 + PRAGMA + 跨工作区外键负例 + CHECK/STRICT 负例 + downgrade 可逆

### 21. [V4+] rc=0

```console
$ uv run --no-sync pytest -q tests/unit/test_migration_schema.py
..............                                                           [100%]
14 passed in 0.32s
```

说明：比对器非空转（10 项变异测试）+ 迁移自包含 AST 守卫 + head 元数据

### 22. [V11] rc=0

```console
$ uv run --no-sync ruff check . && uv run --no-sync ruff format --check .
All checks passed!
81 files already formatted
```

说明：全仓 lint + format。**未对全仓执行 `ruff format`**，只对本子任务新建的 8 个文件跑过 `ruff format <文件>`

### 23. [V12] rc=0

```console
$ uv run --no-sync mypy && uv run --no-sync pytest -q
Success: no issues found in 15 source files
.....................................................................    [100%]
69 passed in 19.41s
```

说明：mypy strict + 全量 pytest

## 4. 汇总

- 共实跑 **23** 条命令；rc≠0 的有 **1** 条。
  - `uv run --no-sync python -m campaignlab doctor` → rc=1：`doctor` CLI 与 `__main__` 属 **S3** 交付物，S2 时点尚未存在 → **rc=1 为如实现状，非 S2 缺陷**；本子任务只负责 Q7 裁定的前半段（可导入性）
- `compare_schema()` 实测返回 `[]`；业务表数 **28**；显式索引 **6**；`PRAGMA integrity_check`=`ok`、`foreign_key_check`=0 行；7 条负例全部被拒、4 条正例全部落库（详见同目录 `migration-diff.md`）。
- 全量 `pytest -q`：**69 passed**，`tests/unit/test_task_cards.py` 本次采集时点为绿（C lane 若在其它时点改写 KNOWN_MISSING 导致瞬时红，属并行 lane 归属，不计入 S2 判定）。

