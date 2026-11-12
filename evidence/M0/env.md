# 环境取证

| 项 | 值 |
|---|---|
| as_of | 2026-11-12T03:13:10+08:00 |
| os | MISSING |
| kernel | 6.18.58.1-microsoft-standard-WSL2 x86_64 |
| python3_system | Python 3.12.3 |
| sqlite3_system | 3.45.1 |
| uv | MISSING |
| python314_uv | Python 3.14.10 |
| node | v24.22.3 |
| node_elf | /home/szf/.local/share/node-v24/bin/node |
| git | git version 2.43.0 |
| make | GNU Make 4.3 |
| ripgrep | ripgrep 14.1.0 |
| docker | Docker version 29.1.3, build 29.1.3-0ubuntu3~24.04.2 |
| browser | MISSING（见 BLK-01） |

说明：M0-01 的锁定版本、cp314 wheel 判定与锁文件哈希由该任务追加到 `evidence/M0/M0-01/`；本表为编排器 wave0 基线取证。

## M0-01 锁定后

| 项 | 值 |
|---|---|
| CPython | 3.14.10（uv standalone） |
| SQLite | 3.53.1，JSON 函数实测可用 |
| Node | v24.22.3，~/.local/share/node-v24/bin/node（ELF） |
| npm | 11.19.1 |
| uv.lock | 4d3e6bc8af419fde |
| web/package-lock.json | ee1cd610219f6347 |

---

## M0-01 锁定后（明细，S1 追加）

> 本节由 M0-01-S1（依赖与构建工程师）追加，是上方「## M0-01 锁定后」编排器复核摘要表的**明细展开**；
> wave0 基线表与该摘要表均**原样保留未改**。锁文件哈希与编排器独立复核值逐字节一致
> （`uv.lock` = `4d3e6bc8af419fde`、`web/package-lock.json` = `ee1cd610219f6347`）。
> 与 wave0 基线表的差异见 §5「基线表勘误」。

### 1. 工具链锁定值

| 项 | 值 | 取证 |
|---|---|---|
| as_of | 2026-11-12T03:25:00+08:00 | — |
| os | Ubuntu 24.04.2 LTS | `/etc/os-release` PRETTY_NAME |
| kernel | 6.18.58.1-microsoft-standard-WSL2 x86_64 | `uname -srmo` |
| uv | **0.13.7** (x86_64-unknown-linux-gnu) | `/home/szf/.local/bin/uv`，ELF；源自 PyPI 官方 wheel，sha256 `2c9bdc4a872b60a9…` 与索引一致 |
| CPython（锁定） | **3.14.10** | `.python-version` = `3.14.10`；`uv python install 3.14`；pbs tag `20261110` |
| CPython 路径 | `/home/szf/.local/share/uv/python/cpython-3.14.10-linux-x86_64-gnu/bin/python3.14` | ELF x86-64；shim `/home/szf/.local/bin/python3.14` |
| `sys.version` | `3.14.10 (main, Oct 26 2026, 14:09:22) [Clang 23.1.3]` | — |
| **`sqlite3.sqlite_version`** | **3.53.1**（info `(3, 53, 1)`）→ 满足 `>= 3.38` | `.venv/bin/python` 实测 |
| **json1 实测** | `json_extract`=1、`json_valid`=1、`json_type`=object、`json_each` rows=3、`json_group_array` OK | 6 项函数全部可用；SQLite>=3.38 起 JSON 内建，`SQLITE_ENABLE_JSON1` 已非独立编译选项 |
| Node | **v24.22.3**（LTS **Krypton**，2026-11-10） | `nodejs.org/dist/index.json` 取 v24 最新且含 linux-x64 |
| Node ELF 路径 | `/home/szf/.local/share/node-v24/bin/node` | `ELF 64-bit LSB executable, x86-64`；非 `/mnt/*`，PATH 穿透已排除 |
| Node tarball sha256 | `061ec3e3062115705b56b51fa9cc330ab50d34b6969387d4e4b1a50c6809acc2` | `sha256sum -c` → **OK** |
| 符号链接 | `~/.local/share/node` → `node-v24`；`~/.local/bin/{node,npm,npx,corepack}` 均有效 | 旧版保留为 `~/.local/share/node-v22.23.5`（未删除） |
| npm | **11.19.1** | `readlink -f` → `/home/szf/.local/share/node-v24/lib/node_modules/npm/bin/npm-cli.js` |
| 编译器 | **无**（gcc/cc/g++/pkg-config 均 MISSING，无 sudo） | 故所有 Python 包必须有 wheel，见 `M0-01/wheels.md` |
| browser | **可用**（见 §4） | Chromium 158.0.8127.18 无头启动实测通过 |

### 2. 锁文件与哈希

| 锁文件 | 大小 | sha256（前 16 位） | 规模 | 校验命令与退出码 |
|---|---|---|---|---|
| `uv.lock` | 129054 B | `4d3e6bc8af419fde` | 52 个包条目 / 实装 50 | `uv lock --check` → **0**；`uv sync --locked` → **0** |
| `web/package-lock.json` | 122775 B | `ee1cd610219f6347` | lockfileVersion 3 / 254 条 / 实装 218 | `npm ci` → **0**；`npm ci --dry-run` → **0**；`npm ls --all` → **0** |

两个锁均为**工具生成物**，非手写。`web/dist/index.html`（324 B）与
`web/dist/assets/index-BLIIWH5l.js`（62829 B）由 `npm run build` 真实产出，退出码 **0**。

### 3. 锁定版本清单

#### 3.1 Python（契约区间 → 锁定，逐项 IN-RANGE，`PYTHON_VIOLATIONS=0`）

| 类别 | 包 | 契约区间 | 锁定 | cp314 wheel |
|---|---|---|---|---|
| runtime | fastapi | `>=0.118,<1` | 0.162.4 | py3-none-any |
| runtime | pydantic | `>=2.12,<3` | 2.14.3 | py3-none-any |
| runtime | pydantic-core | （pydantic 传递依赖） | 2.50.4 | **cp314-cp314-manylinux2014_x86_64** |
| runtime | uvicorn | `>=0.38,<1` | 0.54.0 | py3-none-any |
| runtime | sqlalchemy | `>=2.0,<2.1` | 2.0.57 | **cp314-cp314-manylinux2014_x86_64** |
| runtime | alembic | `>=1.16,<2` | 1.20.1 | py3-none-any |
| runtime | duckdb | `>=1.4,<3` | 2.0.0 | **cp312-abi3-manylinux_2_27_x86_64**（稳定 ABI，实测可查询） |
| runtime | python-multipart | `>=0.0.20,<1` | 0.0.33 | py3-none-any |
| runtime | greenlet | （sqlalchemy 传递依赖） | 3.5.6 | **cp314-cp314-manylinux_2_24_x86_64** |
| dev | ruff | — | 0.17.4 | py3-none-manylinux_2_17_x86_64 |
| dev | mypy | — | 2.4.1 | **cp314-cp314-manylinux2014_x86_64**（`compiled: yes`） |
| dev | pytest | — | 9.2.0 | py3-none-any |
| dev | httpx | — | 0.28.1 | py3-none-any |
| dev | jsonschema | — | 4.26.0 | py3-none-any |
| dev | openapi-spec-validator | — | 0.9.0 | py3-none-any |

其余传递依赖含 starlette 1.10.0、anyio 4.16.0、click 8.5.1、mako 1.4.3、pyyaml 6.0.3、
markupsafe 3.0.4、rpds-py 2026.9.1、attrs 26.1.0、referencing 0.37.0、pydantic-settings 2.16.2、
opentelemetry-api 1.45.2 等（合计 52 条）。site-packages 内 `.so` 共 **255** 个，
一律为 `cpython-314-x86_64-linux-gnu.so` 或 `abi3.so`，无旧 ABI 残留。

#### 3.2 前端（契约区间 → 锁定，`NPM_VIOLATIONS=0`）

| 类别 | 包 | 契约 | 声明 | 锁定 |
|---|---|---|---|---|
| runtime | vue | `>=3.5 <4` | `>=3.5 <4` | 3.5.45 |
| runtime | vue-router | `>=4 <5` | `>=4 <5` | 4.6.4 |
| runtime | element-plus | `>=2 <3` | `>=2 <3` | 2.14.8 |
| runtime | echarts | `>=6 <7` | `>=6 <7` | 6.1.0 |
| dev | vite | `>=7 <9` | `>=7 <9` | 8.3.8 |
| dev | @vitejs/plugin-vue | resolve compatible stable | `^6` | 6.0.10 |
| dev | typescript | `>=5.9 <7` | `>=5.9 <6`（**区间内收窄**） | 5.9.3 |
| dev | vitest | `>=5 <6` | `>=5 <6` | 5.1.0 |
| dev | @playwright/test | `>=1 <2` | `>=1 <2` | 1.65.0 |
| dev | vue-tsc | resolve compatible stable | `^3` | 3.3.14 |
| dev | eslint | resolve compatible stable | `^10` | 10.14.0 |
| dev | eslint-plugin-vue | resolve compatible stable | `^10` | 10.12.1 |
| dev | openapi-typescript | resolve compatible stable | `^7` | 7.13.0 |
| dev | vue-eslint-parser | 契约未列（**必需 peer**） | `^10.3.0` | 10.4.2 |
| dev | @typescript-eslint/parser | 契约未列（**可选 peer，缺则 lint 失败**） | `^8` | 8.72.2 |

`engines.node` = `>=24 <25`；实际 `v24.22.3` 对 `engines` 与契约 `target.node` 均 satisfies = true。
peer 冲突 **0**，ERESOLVE **0**，npm warn **0**，未使用 `--legacy-peer-deps`/`--force`/`overrides`。

### 4. 浏览器可用性结论（BLK-01）

| 项 | 值 |
|---|---|
| Playwright | 1.65.0（web/node_modules/@playwright/test） |
| 所需浏览器 | Chrome for Testing **158.0.8127.18** = playwright chromium **v1254** |
| 缓存状态 | `~/.cache/ms-playwright/` 已含 `chromium-1254`、`chromium_headless_shell-1254`、`ffmpeg-1013`（正是 1.65.0 所需版本） |
| 关键系统库 | `libnss3.so`、`libatk-1.0.so.0`、`libgbm.so.1`、`libasound.so.2`、`libgtk-3.so.0`、`libxkbcommon.so.0` **全部 present** |
| **真实启动实测** | 无头启动成功，`browserVersion: 158.0.8127.18`，页面文本含中文正确回读，截图 14690 B，退出码 **0** |
| 下载源可达性 | `cdn.playwright.dev` 可达（`install --dry-run` 退出码 0） |
| **结论** | 本机 **BLK-01 当前不构成阻塞**（浏览器与系统依赖均已具备，无需 root）。建议保留 BLK-01 登记：换机或 CI 干净镜像仍需 `npx playwright install --with-deps chromium`（需 root） |
| 中文字体（BLK-02） | `fc-list :lang=zh` = 7 条（含 `WenQuanYi Zen Hei`），中文可渲染；**未安装 Noto Sans CJK**，字体度量可能与行内设计基线不一致 → BLK-02 **仅部分解除**，像素级视觉走查仍建议装 `fonts-noto-cjk`（需 root） |

### 5. 基线表勘误（wave0 表中因当时未装/未探测而记为 MISSING 的项）

| 项 | wave0 基线值 | M0-01 实测值 |
|---|---|---|
| `os` | `MISSING` | **Ubuntu 24.04.2 LTS** |
| `uv` | `MISSING` | **0.13.7** @ `/home/szf/.local/bin/uv` |
| `browser` | `MISSING（见 BLK-01）` | **可用**：Chromium 158.0.8127.18 无头启动实测通过（见 §4） |
| `node` | `v24.22.3` | 一致，已复核 ELF 路径与 tarball sha256 |
| `python314_uv` | `Python 3.14.10` | 一致，并补测 `sqlite_version = 3.53.1` 与 json1 六项函数 |

### 6. 环境诊断入口

```
bash scripts/doctor.sh                      # 全量，退出码 0 = HEALTHY
DOCTOR_SKIP_VERIFY=1 bash scripts/doctor.sh # 跳过较慢的原型基线复跑
```

实测：`env -i HOME=/home/szf PATH=/usr/bin:/bin TERM=dumb bash scripts/doctor.sh` → 退出码 **0**，
`PASS=15 WARN=2 FAIL=0`，`RESULT: HEALTHY`（证明非登录 shell、极简 PATH 下自发现生效）。
负向测试（`HOME=/tmp/emptyhome` 隐藏工具链）→ 退出码 **1**，打印 5 条 `[FAIL]` 与 `RESULT: UNHEALTHY`。
两处 WARN 为「工作树有未提交改动」（本任务产物待编排器提交）与「未安装 Noto Sans CJK」（BLK-02）。
doctor 只读：uv 与 npm 均用 `--dry-run`，不重装 `.venv` 与 `node_modules`。

### 7. BLK-06 判定

BLK-06 触发条件为「duckdb 或 pydantic-core 若无 cp314 wheel」。实测：
duckdb 2.0.0 提供 `cp312-abi3-manylinux_2_27_x86_64` 稳定 ABI wheel（导入 + 真实 SQL + JSON 函数均通过），
pydantic-core 2.50.4 提供字面 `cp314-cp314-manylinux2014_x86_64` 原生 wheel（校验往返通过）。
**BLK-06 不触发**，无需 CR/ADR，无需 ADR-002 回退路径，**无需退回 Python 3.13**。

### 8. 详见

- `evidence/M0/M0-01/commands.md`：命令、退出码、关键输出（含网络可达性判定与 uv/CPython 安装路径偏离说明）
- `evidence/M0/M0-01/wheels.md`：13 项 wheel 逐项判定表、abi3 说明、10 个原生传递依赖
- `evidence/M0/M0-01/npm.md`：解析结论、peer 相容性核对、三项需登记的决议、六个 scripts 真实状态
