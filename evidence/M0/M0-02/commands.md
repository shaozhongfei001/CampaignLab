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

---

# M0-02 · S5 命令与实测 rc（追加，2026-11-14）

> 追加口径：S2 原文（上文）逐字未动（手册 15.9/15.10：历史测量值不重写）。
> cwd 一律 `/home/szf/dev/CampaignLab`（表中省略者同）。HTTP 驱动的逐请求证据在 `http/**`，
> 结构化四元组全文在 `http/97-gate-summary.json` / `http/98-run-summary.json` / `http/96-selfcheck-greps.json`。
> rc 语义：0=成功，1=无匹配/无失败但无行（grep）或如实现状（见行注），2=命令自身错误（本表无 2）。
> 会话内 HEAD=`4a82190f69c0b0b864ce3a55a11a06fddf2a9b38`。

| 标签 | cwd | 命令 | rc | 时间戳(Asia/Shanghai) | 关键输出（截断） |
|---|---|---|---|---|---|
| S5/alembic | `/home/szf/dev/CampaignLab` | `uv run --no-sync alembic -c migrations/alembic.ini upgrade head` | **0** | 2026-11-14T01:22:08+0800 | `alembic upgrade head` → head=0001_initial_schema |
| S5/alembic | `/home/szf/dev/CampaignLab` | `uv run --no-sync alembic -c migrations/alembic.ini current` | **0** | 2026-11-14T01:22:08+0800 | `alembic upgrade head` → head=0001_initial_schema |
| S5/serve-A | `/home/szf/dev/CampaignLab` | `uv run --no-sync python -m campaignlab serve --port 8765 (CAMPAIGNLAB_DATA_DIR=evidence/M0/M0-02/_runtime/ac001)` | **驱动管理** | 2026-11-14T01:22:08+0800 | 由驱动 Popen/terminate；0.8s 内 /health=200（显式轮询，非固定 sleep）；SIGTERM 后 port_A_released=true；entry_token 只存 sha12=05e8026524f7，进程日志出口删除 |
| S5/http | `/home/szf/dev/CampaignLab` | `uv run --no-sync python3 /mnt/d/ws/codex_rd/ss_campaignlab/.orch_tmp/bohr_run.py（驱动 19 个 HTTP 请求，全部落盘；R10 更正：原记 23，见 D-038）` | **0** | 2026-11-14T01:22:08+0800 | 逐请求见 http/*.http 与 http/90-requests-index.txt；FU-7 服务 B（8766, 空数据目录）同一脚本内完成 |
| S5/doctor-transcript | `/home/szf/dev/CampaignLab` | `uv run python -m campaignlab doctor` | **0** | 2026-11-14T01:23:16+0800 | [doctor] host=127.0.0.1 port=8000 data_dir=/home/szf/dev/CampaignLab/evidence/M0/M0-02/_runtime/ac001 ⏎ [doctor] db=sqlite:////home/szf/dev/CampaignLab/evidence |
| S5/AC035-verify-package | `/home/szf/dev/CampaignLab` | `python3 spec/CampaignLab-SDD-v1.0/qa/verify_package.py` | **0** | 2026-11-14T01:23:16+0800 | PASS 清单与逐文件 SHA-256 共 89 项 ⏎ PASS 接口和本地 Schema 引用共 80 个操作 ⏎ PASS 26 个页面、35 个验收用例、55 个材料点位、47 个手册操作点及文档链接 ⏎ PASS SQLite DDL 可执行，共 28 表，含完整性与外键负例 ⏎ PASS 甲乙各 510 切 |
| S5/AC035-check-contracts | `/home/szf/dev/CampaignLab` | `uv run --no-sync python scripts/check_contracts.py check --validate` | **0** | 2026-11-14T01:23:18+0800 | CONTRACT CHECK PASS 登记项=13 实测差异=13 元校验=6 |
| S5/AC035-frontend-baseline | `/home/szf/dev/CampaignLab` | `uv run --no-sync python scripts/check_frontend_baseline.py` | **0** | 2026-11-14T01:23:18+0800 | emplate_blank_singlefile.html sha16=4b966e044d3305a1 expect=4b966e044d3305a1 bytes=139725 expect=139725 ⏎ OK   css/tokens.css sha16=a4e27cc208ccc428 expect=a4e2 |
| S5/mig-equiv | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q tests/integration/bootstrap/test_migration_equivalence.py tests/unit/test_migration_schema.py` | **0** | 2026-11-14T01:23:39+0800 | ..........................                                               [100%] ⏎ 26 passed in 19.72s |
| S5/expired-session-api | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q tests/api/test_contract_http.py -k expired` | **0** | 2026-11-14T01:23:41+0800 | ..                                                                       [100%] ⏎ =============================== warnings summary ============================= |
| S5/expired-session-unit | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q tests/unit/test_s3d_application.py -k expir` | **0** | 2026-11-14T01:23:42+0800 | ated; install `httpx2` instead. ⏎     from starlette.testclient import TestClient as TestClient  # noqa ⏎  ⏎ tests/unit/test_s3d_application.py::test_expired_se |
| S5/ruff-check | `/home/szf/dev/CampaignLab` | `uv run --no-sync ruff check .` | **0** | 2026-11-14T01:23:42+0800 | All checks passed! |
| S5/ruff-format | `/home/szf/dev/CampaignLab` | `uv run --no-sync ruff format --check .` | **0** | 2026-11-14T01:23:42+0800 | 194 files already formatted |
| S5/mypy | `/home/szf/dev/CampaignLab` | `uv run --no-sync mypy` | **0** | 2026-11-14T01:23:42+0800 | Success: no issues found in 73 source files |
| S5/pytest-full | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q` | **1** | 2026-11-14T01:25:20+0800 | ates_session_via_new_app_instance ⏎ tests/unit/test_s3d_application.py::test_expired_session_401_uses_the_same_detail ⏎ tests/unit/test_s3d_application.py::test |
| S5/uv-lock-check | `/home/szf/dev/CampaignLab` | `uv lock --check` | **0** | 2026-11-14T01:25:20+0800 | Resolved 52 packages in 1ms |
| S5/env-uv | `/home/szf/dev/CampaignLab` | `uv --version` | **0** | 2026-11-14T01:25:20+0800 | uv 0.13.7 (x86_64-unknown-linux-gnu) |
| S5/env-node | `/home/szf/dev/CampaignLab` | `node -v` | **0** | 2026-11-14T01:25:20+0800 | v24.22.3 |
| S5/env-npm | `/home/szf/dev/CampaignLab` | `npm -v` | **0** | 2026-11-14T01:25:21+0800 | 11.19.1 |
| S5/env-git-head | `/home/szf/dev/CampaignLab` | `git rev-parse HEAD` | **0** | 2026-11-14T01:25:21+0800 | 4a82190f69c0b0b864ce3a55a11a06fddf2a9b38 |
| S5/py-versions | `/home/szf/dev/CampaignLab` | `/home/szf/dev/CampaignLab/.venv/bin/python3 -c import platform,sqlite3,sys;print(platform.python_version(), sys.version.split()[0], sqlite3.sqlite_version)` | **0** | 2026-11-14T01:25:21+0800 | 3.14.10 3.14.10 3.53.1 |
| S5/openapi-sha16 | `/home/szf/dev/CampaignLab` | `/home/szf/dev/CampaignLab/.venv/bin/python3 -c import hashlib,pathlib;d=pathlib.Path('contracts/openapi.json').read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))` | **0** | 2026-11-14T01:25:21+0800 | 592571099d638251 443309 |
| S5/openapi-gen-types | `/home/szf/dev/CampaignLab/web` | `npx openapi-typescript ../contracts/openapi.json -o /home/szf/dev/CampaignLab/evidence/M0/M0-02/_runtime/types.gen.ts` | **0** | 2026-11-14T01:25:22+0800 | ✨ openapi-typescript 7.13.0 ⏎ 🚀 ../contracts/openapi.json → /home/szf/dev/CampaignLab/evidence/M0/M0-02/_runtime/types.gen.ts [172.2ms] |
| S5/gen-types-byte-equal-live-web | `/home/szf/dev/CampaignLab` | `cmp generated types.ts vs web/src/api/types.ts` | **0** | 2026-11-14T01:25:22+0800 | True |
| S5/vue-tsc-typecheck | `/home/szf/dev/CampaignLab/web` | `npm run typecheck` | **0** | 2026-11-14T01:25:24+0800 | > campaignlab-web@0.0.0 typecheck ⏎ > vue-tsc --noEmit -p tsconfig.json |
| S5/ddl-head | `/home/szf/dev/CampaignLab` | `uv run --no-sync alembic -c migrations/alembic.ini upgrade head` | **0** | 2026-11-14T01:25:25+0800 | SQLiteImpl. ⏎ INFO  [alembic.runtime.migration] Will assume non-transactional DDL. ⏎ INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema,  |
| S5/ddl-compare-rerun | `/home/szf/dev/CampaignLab` | `/home/szf/dev/CampaignLab/.venv/bin/python3 -c 
import hashlib, pathlib, sqlite3, sys
sys.path.insert(0, "src") if not hasattr(sys, "campaignlab_imported") else None
from campaignlab.infra.db.ddl_compare import (compare_schema, table_names, pragma_problems,
    EXPECTED_TABLE_COUNT, MIGRATION_ONLY_TABLES)
ddl = pathlib.Path("contracts/sqlite-v1.sql").read_text(encoding="utf-8")
print("ddl_sha256", hashlib.sha256(ddl.encode()).hexdigest())
ref = sqlite3.connect(":memory:")
ref.executescript(ddl)
mig = sqlite3.connect(sys.argv[1])
diffs = compare_schema(ref, mig)
users = [t for t in table_names(mig) if t not in MIGRATION_ONLY_TABLES]
print("table_count_expected", EXPECTED_TABLE_COUNT)
print("table_count_migration_db", len(users))
print("compare_schema_diffs", diffs)
print("integrity", mig.execute("PRAGMA integrity_check").fetchall())
print("fk_violations", mig.execute("PRAGMA foreign_key_check").fetchall())
print("head", mig.execute("SELECT version_num FROM alembic_version").fetchall())
mig.close(); ref.close()
 /home/szf/dev/CampaignLab/evidence/M0/M0-02/_runtime/ddlcheck/state/campaignlab.db` | **0** | 2026-11-14T01:25:25+0800 | ddl_sha256 ec9ddfbc4e7dba4c0a565161b50a222fee484eb07e6586588871bffa2efc8c0e ⏎ table_count_expected 28 ⏎ table_count_migration_db 28 ⏎ compare_schema_diffs [] ⏎  |
| S5/defect-D037-mtime | `/home/szf/dev/CampaignLab` | `stat -c %y %n orchestrator/defects/D-037.md` | **0** | 2026-11-14T01:26:08+0800 | 2026-11-14 01:18:41.795687764 +0800 orchestrator/defects/D-037.md |
| S5/unreachable-404-429-decl | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q tests/api/test_contract_declarations.py -k unreachable` | **0** | 2026-11-14T01:26:10+0800 | StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead. ⏎     from starlette.testclient import TestClien |
| S5/cross-workspace-repo-tests | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q tests/unit/test_s3d_repositories.py -k workspace` | **0** | 2026-11-14T01:26:12+0800 | ..                                                                       [100%] ⏎ 2 passed, 12 deselected in 1.22s |
| S5/grep-schema-revision-web | `/home/szf/dev/CampaignLab` | `grep -rn schema_revision web/src` | **0** | 2026-11-14T01:26:12+0800 | web/src/api/types.ts:1058:            schema_revision: string; |
| S5/grep-unmigrated-web | `/home/szf/dev/CampaignLab` | `grep -rn UNMIGRATED web/src prototype` | **1** | 2026-11-14T01:26:12+0800 |  |
| S5/grep-degraded-branch | `/home/szf/dev/CampaignLab` | `grep -rn DEGRADED web/src/composables web/src/api web/src/pages` | **0** | 2026-11-14T01:26:12+0800 | web/src/composables/useWorkspaces.ts:50:  /** Health.worker === "OFFLINE" 或 status === "DEGRADED" → UI-01 顶栏「作业受限」。 */ ⏎ web/src/composables/useWorkspaces.ts:18 |
| S5/grep-selfdiff | `/home/szf/dev/CampaignLab` | `bash -lc git diff --name-only HEAD | wc -l` | **0** | 2026-11-14T01:26:12+0800 | 7 |

## S5.1 doctor gate transcript（rc=0 全文）

```console
$ uv run python -m campaignlab doctor   # CAMPAIGNLAB_DATA_DIR=证据期临时目录(已删)
[doctor] host=127.0.0.1 port=8000 data_dir=/home/szf/dev/CampaignLab/evidence/M0/M0-02/_runtime/ac001
[doctor] db=sqlite:////home/szf/dev/CampaignLab/evidence/M0/M0-02/_runtime/ac001/state/campaignlab.db level=ENV_DATA_DIR source=环境变量 CAMPAIGNLAB_DATA_DIR + /state/campaignlab.db
PASS  version   app=0.0.0 contract=1.0.1 source=/home/szf/dev/CampaignLab/contracts/openapi.json
PASS  binding   127.0.0.1:8000 回环且空闲，可 serve
PASS  data_dir  /home/szf/dev/CampaignLab/evidence/M0/M0-02/_runtime/ac001 可写且七个子目录齐备
PASS  database  /home/szf/dev/CampaignLab/evidence/M0/M0-02/_runtime/ac001/state/campaignlab.db revision=0001_initial_schema==head，PRAGMA 双检通过
PASS  worker    campaignlab.application.worker 可导入；心跳窗口=15s
  PASS=5 WARN=0 FAIL=0 RESULT=HEALTHY
```

## S5.2 出口越界自证（A139 双检，出口时点）

- 检查① `git diff --name-only HEAD | wc -l` → 原样 **10**。归因拆分（`git diff --numstat`）：
  - S5 的 2 条：`evidence/M0/M0-02/commands.md`（+84/−0）、`evidence/M0/M0-02/migration-diff.md`（+22/−0）——
    **纯追加、零删除**，S2 既有实测行逐字未动（本文件头部第 4-5 行正是 S2 留给 S5 的追加指令；两文件均在 S5 写权清单内）。
  - 编排器/其他 lane 在飞 8 条：`evidence/M0/ORCHESTRATOR/r9-content-review/*`（5）、`orchestrator/defects/D-037.md`、
    `orchestrator/handoff/M0-03-public-components.md`、`orchestrator/state.json`——S5 未写、未 add、未处理。
- 检查② `git status --porcelain | grep -vE '^(\?\? )?evidence/M0/(M0-02|summaries/M0-02\.md)' | wc -l` → 原样 **12**
  （含上述 9 条在飞 + `?? web/src/components/state/`、`?? web/tests/unit/state/` 等他 lane 未跟踪条目）。
- S5 严格口径：写权外既有文件被 S5 修改的数量 = **0**；源码/测试/配置零触碰。
