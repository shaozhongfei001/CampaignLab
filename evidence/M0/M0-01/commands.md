# M0-01 命令与退出码取证

执行环境：WSL2 Ubuntu 24.04.2 LTS，kernel 6.18.58.1-microsoft-standard-WSL2 x86_64，仓库 `/home/szf/dev/CampaignLab`，分支 `m0-framework`。
所有命令均以非登录 bash 执行；工具链路径按 `scripts/verify.sh` 的自发现方式导出
`PATH="$HOME/.local/bin:$HOME/.local/share/node/bin:$PATH"`。

约定：只记录命令、退出码与关键输出行，不贴全量日志。

---

## 0. 网络可达性前置判定（决定安装路径）

`github.com` 主站不可达，直接改变 uv 与 CPython 的安装方式，故先取证。

| 目标 | 结果 |
|---|---|
| `https://pypi.org/simple/duckdb/` | 200（1.49s） |
| `https://files.pythonhosted.org/` | 可达 |
| `https://api.github.com/repos/astral-sh/uv` | 200（0.68s） |
| `https://raw.githubusercontent.com/...` | 200（0.86s） |
| `https://codeload.github.com/` | 200（1.28s） |
| `https://objects.githubusercontent.com/` | 404（可达） |
| `https://release-assets.githubusercontent.com/` | 404（可达，5.29s） |
| `https://github.com/astral-sh/uv/releases/latest` | **000 超时（45.96s，不可达）** |
| `https://mirror.ghproxy.com/` | **000 超时（不可达）** |
| `https://ghfast.top/` | 200，但对 pbs 资产返回 403 |
| `https://mirror.nju.edu.cn/github-release/` | 200（0.08s） |
| `https://registry.npmjs.org/`、`https://nodejs.org/dist/index.json` | 200 |
| `https://cdn.playwright.dev/` | 可达 |

**结论与偏离说明（需编排器知悉）**：官方 installer `https://astral.sh/uv/install.sh` 可下载，但其内部
从 `github.com/<owner>/<repo>/releases/download/...` 取二进制，该主机不可达，故官方 installer 在本机无法完成。
改用 **PyPI 官方 wheel**（同一发布物、Astral 官方打包）安装 uv，sha256 与 PyPI simple 索引中的
fragment 逐字节一致。同理 `uv python install` 走 `UV_PYTHON_INSTALL_MIRROR` 指向南京大学镜像。

---

## 1. uv 安装（无 sudo，装入 ~/.local/bin）

```
curl -sS https://pypi.org/simple/uv/ | grep -o "https://files.pythonhosted.org/[^#]*uv-0.13.7-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
curl -sSL -o uv.whl <上述 URL>
sha256sum uv.whl
python3 -c <从 uv-0.13.7.data/scripts/ 解出 uv、uvx 到 ~/.local/bin，chmod 0755>
uv --version
```

| 项 | 值 | 退出码 |
|---|---|---|
| 下载 | `uv-0.13.7-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`（17202345 B） | 0 |
| wheel sha256 | `2c9bdc4a872b60a93c5f26c0791089ea11585a4f9d3b3c017d78eb8487505e25` | — |
| 与 PyPI 索引 fragment 比对 | **一致** | — |
| `uv --version` | `uv 0.13.7 (x86_64-unknown-linux-gnu)` | 0 |
| `uvx --version` | `uvx 0.13.7 (x86_64-unknown-linux-gnu)` | 0 |
| 安装路径 | `/home/szf/.local/bin/uv`（ELF 64-bit LSB pie executable, x86-64） | — |

注：`~/.local/bin` 原无 uv；系统 python3.12 无 pip 模块、无 pipx，且 `/usr/lib/python3.12/EXTERNALLY-MANAGED`
存在，故 `pip install --user` 路径不可用，PyPI wheel 直取是无 sudo 下最干净的方案。

---

## 2. CPython 3.14 安装与 sqlite/json1 取证

```
export UV_PYTHON_INSTALL_MIRROR="https://mirror.nju.edu.cn/github-release/astral-sh/python-build-standalone"
uv python install 3.14
uv python list --only-installed
```

| 项 | 值 | 退出码 |
|---|---|---|
| `uv python install 3.14` | `Installed Python 3.14.10 in 7.62s`（下载 35.1 MiB） | 0 |
| python-build-standalone tag | `20261110`（由 api.github.com 取得，该主机可达） | — |
| 解释器路径 | `/home/szf/.local/share/uv/python/cpython-3.14.10-linux-x86_64-gnu/bin/python3.14` | — |
| `file` | ELF 64-bit LSB executable, x86-64, not stripped | — |
| shim | `/home/szf/.local/bin/python3.14` | — |
| `sys.version` | `3.14.10 (main, Oct 26 2026, 14:09:22) [Clang 23.1.3]` | — |
| **`sqlite3.sqlite_version`** | **3.53.1**（`sqlite_version_info = (3, 53, 1)`）→ **>= 3.38 满足** | 0 |

`json1` 实测（`python3.14 - <<PY`，退出码 0）：

| 探测 | 实测结果 |
|---|---|
| `json_extract(payload, "$.a")` | `1` |
| `json_extract(payload, "$.b[1]")` | `20` |
| `json_extract(payload, "$.c.d")` | `x` |
| `json_valid(payload)` / `json_type(payload)` | `1` / `object` |
| `select count(*) from json_each(payload)` | `3` |
| `json_group_array(value)` | `[1,[10,20,30],{"d":"x"}]` |
| `pragma_compile_options()` 中含 JSON 的项 | `[]`（空） |

**说明**：自 SQLite 3.38 起 JSON 函数已默认内建，`SQLITE_ENABLE_JSON1` 不再是独立编译选项，
因此编译选项列表为空属预期，不代表 JSON 缺失；以上 6 项函数实测全部可用，`dependencies.json`
的 `sqlite >= 3.38 with JSON functions` 判定为**满足**。

3.13 回退未触发（3.14 安装成功且 sqlite 达标），故未安装 3.13、未产生 3.13 证据。

---

## 3. Node 24 LTS 安装与符号链接重指

```
curl -sS https://nodejs.org/dist/index.json          # 取 v24 最新且含 linux-x64 的版本
curl -sSL -o node-v24.22.3-linux-x64.tar.gz https://nodejs.org/dist/v24.22.3/node-v24.22.3-linux-x64.tar.gz
curl -sSL -o SHASUMS256.txt https://nodejs.org/dist/v24.22.3/SHASUMS256.txt
sha256sum -c <(grep " node-v24.22.3-linux-x64.tar.gz$" SHASUMS256.txt)
tar -xzf ... -C ~/.local/share/node-v24 --strip-components=1
mv ~/.local/share/node ~/.local/share/node-v22.23.5   # 保留旧版，未删除
ln -s ~/.local/share/node-v24 ~/.local/share/node
```

| 项 | 值 | 退出码 |
|---|---|---|
| index.json 选定版本 | `v24.22.3`（date 2026-11-10，**lts = Krypton**，npm 11.19.1） | 0 |
| 下载 | `node-v24.22.3-linux-x64.tar.gz`，58330843 B，3.72s | 0 |
| **sha256sum -c** | `node-v24.22.3-linux-x64.tar.gz: OK`（`061ec3e3062115705b56b51fa9cc330ab50d34b6969387d4e4b1a50c6809acc2`） | **0** |
| `node -v` / `npm -v` / `npx -v` | `v24.22.3` / `11.19.1` / `11.19.1` | 0 |
| `command -v node` | `/home/szf/.local/bin/node` | — |
| `readlink -f` | `/home/szf/.local/share/node-v24/bin/node` | — |
| `file` | **ELF 64-bit LSB executable, x86-64**（非 `/mnt/c/...`，PATH 穿透陷阱已排除） | — |
| `~/.local/bin/{node,npm,npx,corepack}` | 4 条符号链接均有效（指向 `~/.local/share/node/bin/*` → `node-v24`） | — |

### 3.1 原型基线在 Node 24 下复跑（编排器已独立复核）

```
bash scripts/verify.sh
```

退出码 **0**；关键输出：

```
env: node=v24.22.3 python=Python 3.12.3
==> 1/4 交付件完整性      SHA256SUMS OK
==> 2/4 计算与问法断言    79/79 PASS
==> 3/4 确定性数据生成    （无输出）
==> 4/4 字节级复现        PASS: 字节级复现
```

Node 22.23.5 → 24.22.3 **无回归**，复跑后 `git status --porcelain -- prototype` 为空。

---

## 4. pyproject.toml 与 .python-version

写入 `/home/szf/dev/CampaignLab/pyproject.toml`（1239 B）与 `.python-version`（内容 `3.14.10`）。
TOML 可解析性自检（`tomllib`，退出码 0）：`name=campaignlab`、`requires-python=>=3.14,<3.15`、
运行依赖 7 项、dev group 6 项、`tool.uv.package=false`。

关键决策：`[tool.uv] package = false`。因 `src/**` 在本任务 scope_deny 内，`src/campaignlab`
业务包尚不存在，若按打包项目同步会因缺包目录而失败。已声明 `[build-system] hatchling` 与
`[tool.hatch.build.targets.wheel] packages = ["src/campaignlab"]`，**M0-02 建包后删除该行即恢复可安装项目**。

---

## 5. Python 侧解析、锁定与验证

| 命令 | 退出码 | 关键输出 |
|---|---|---|
| `uv lock` | **0** | `Using CPython 3.14.10` / `Resolved 52 packages in 3.69s` / 生成 `uv.lock` 129054 B |
| `uv sync` | **0** | `Creating virtual environment at: .venv` / `Prepared 50 packages in 1m 01s` / `Installed 50 packages in 66ms` |
| `uv sync --locked` | **0** | `Resolved 52 packages in 1ms` / `Checked 50 packages in 0.28ms` |
| `uv lock --check` | **0** | `Resolved 52 packages in 1ms`（无差异输出即为通过） |
| `uv pip list` | 0 | 50 个已安装包，见 `wheels.md` |
| `uv sync --locked --dry-run` | 0 | 虚拟环境与锁一致 |

`uv sync` 输出中**无任何 `Building ...` / `Built ...` 行**，即 50 个包全部来自预编译 wheel，
无 sdist 现场构建。这一点在本机是硬约束而非巧合：

```
gcc=NO  cc=NO  g++=NO  pkg-config=NO        # 无编译器，且无 sudo 无法安装 build-essential
```

因此任一包若无 cp314/abi3/pure wheel 都将直接失败——`uv sync` 退出码 0 本身即 wheel 全可用的证明。
wheel 级逐项判定见 `wheels.md`。

### 5.1 导入与 CLI 冒烟（`.venv/bin/python`，退出码 0）

| 目标 | 实测 |
|---|---|
| `duckdb` | 2.0.0；`select 40+2` → `42`；`json_extract_string` → `v`；聚合 → `6` |
| `pydantic` / `pydantic_core` | 2.14.3 / 2.50.4；`BaseModel` 与 `TypeAdapter` 校验往返 OK；`model_json_schema` OK |
| `sqlalchemy` | 2.0.57；`util.has_compiled_ext()` → **True**；`cyextension/collections.cpython-314-x86_64-linux-gnu.so` 存在 |
| `fastapi` + `TestClient` | 0.162.4；`GET /ping` → `200 {"ok":true}`；`POST /upload` → `200 {"n":3}`；`openapi` → **3.1.0** |
| `greenlet` | 3.5.6 导入 OK（`_greenlet.cpython-314-x86_64-linux-gnu.so`） |
| `alembic` / `uvicorn` / `multipart` | 1.20.1 / 0.54.0 / 0.0.33 |
| `httpx` / `jsonschema` / `openapi_spec_validator` | 0.28.1 / 4.26.0（`validate` 实测通过）/ 0.9.0 |
| `ruff --version` | `ruff 0.17.4` |
| `mypy --version` | `mypy 2.4.1 (compiled: yes)` |
| `pytest --version` | `pytest 9.2.0` |
| `alembic --version` | `alembic 1.20.1` |
| site-packages 内 `.so` | **255 个**，全部为 `cpython-314-x86_64-linux-gnu.so` 或 `abi3.so` |

---

## 6. 前端依赖（web/）

写入 `web/package.json`、`web/index.html`、`web/vite.config.ts`、`web/tsconfig.json`、
`web/eslint.config.js`、`web/playwright.config.ts`、`web/src/{main.ts,App.vue,vite-env.d.ts}`。

| 命令（cwd = `web/`） | 退出码 | 关键输出 |
|---|---|---|
| `npm install --no-audit --no-fund` | **0** | `added 210 packages in 34s`（首次）；追加 `@typescript-eslint/parser` 后 `added 8 packages in 5s` |
| `npm ci --no-audit --no-fund` | **0** | `added 218 packages in 11s`（清空重装，未产生任何 warn） |
| `npm ci --dry-run` | **0** | `up to date in 781ms`（只检测，不重装） |
| `npm run build` | **0** | `vite v8.3.8 building client environment for production...` / `✓ 11 modules transformed` / `dist/index.html 0.32 kB │ gzip: 0.23 kB` / `dist/assets/index-BLIIWH5l.js 62.82 kB │ gzip: 24.88 kB` / `✓ built in 137ms` |
| `npm run lint` | **0** | `> eslint .`（无输出即无告警） |
| `npm run typecheck` | **0** | `> vue-tsc --noEmit -p tsconfig.json`（无错误） |
| `npm run test` | **0** | `RUN v5.1.0` / `No test files found, exiting with code 0`（`--passWithNoTests`，当前 0 个测试文件，属预期） |
| `npm run test:e2e` | **1** | `Error: No tests found`（e2e 用例属 M5-01；**如实失败，未伪造成功**） |
| `npm ls --depth=0` | 0 | 14 个顶层依赖，见 `npm.md` |
| `npm ls --all` | 0 | 无 `invalid` / `extraneous` / ERESOLVE；UNMET 项全部为 OPTIONAL |
| `npm install --dry-run` 告警计数 | 0 | `grep -icE "warn\|ERESOLVE"` → `0` |

构建产物实测：`web/dist/index.html` 324 B（含 `<div id="app">` 与 module script），
`web/dist/assets/index-BLIIWH5l.js` 62829 B。`web/dist` 与 `web/node_modules` 均被现有
`.gitignore` 的 `dist/`、`node_modules/` 规则覆盖，**未修改 .gitignore**。

### 6.1 中途修正记录（lint 真实失败 → 修好，非绕过）

首版 `npm run lint` 退出码 **1**：

```
web/src/App.vue
  3:11  error  Parsing error: Unexpected token :
```

原因：`<script setup lang="ts">` 需要 TS 解析器，而 `eslint-plugin-vue@10` 把
`@typescript-eslint/parser` 列为 **可选 peer**，未安装即用 espree 解析 TS 必然失败。
处置：显式声明 `@typescript-eslint/parser@^8`（实测 8.72.2，peer 为
`eslint ^8.57||^9||^10` 与 `typescript >=4.8.4 <6.1.0`，与本锁的 eslint 10.14.0 / TS 5.9.3 相容），
并在 `eslint.config.js` 中把它同时设为 `.ts` 的 parser 与 `.vue` 的 `parserOptions.parser`。
修正后 `npm run lint` 退出码 **0**。**未通过放宽规则或删除 TS 语法来掩盖问题。**

---

## 7. 浏览器可用性探测（只读，未安装任何东西）

| 命令 | 退出码 | 关键输出 |
|---|---|---|
| `npx playwright --version` | 0 | `Version 1.65.0` |
| `npx playwright install --dry-run chromium` | 0 | `Chrome for Testing 158.0.8127.18 (playwright chromium v1254)`；Install location `~/.cache/ms-playwright/chromium-1254`；Download url `https://cdn.playwright.dev/builds/cft/158.0.8127.18/linux64/chrome-linux64.zip` |
| `ls ~/.cache/ms-playwright` | 0 | 已存在 `chromium-1254`、`chromium_headless_shell-1254`、`ffmpeg-1013`（即 1.65.0 所需的 v1254 已就位） |
| `ldconfig -p` 关键库 | 0 | `libnss3.so`、`libatk-1.0.so.0`、`libgbm.so.1`、`libasound.so.2`、`libgtk-3.so.0`、`libxkbcommon.so.0` **全部 present** |
| 真实无头启动（探针置于仓库外 `~/tmp/probe`） | **0** | `browserName: chromium`；`browserVersion: 158.0.8127.18`；`pageText: CampaignLab 中文字体探测`；UA `HeadlessChrome/158.0.8127.18`；截图 14690 B；`LAUNCH_OK` |
| `fc-list :lang=zh` | 0 | 7 条中文字体（含 `WenQuanYi Zen Hei`）；**未安装 Noto Sans CJK** |

**结论**：Playwright 1.65.0 所需 chromium v1254 二进制与全部关键系统库在本机**已具备**，
无头启动、中文页面渲染与截图实测通过，`BLK-01` 在本机**当前不构成阻塞**（仍建议保留登记，
因换机或 CI 干净镜像上需 root 执行 `--with-deps`）。`BLK-02` 仅部分解除：有中文字体但非 Noto CJK，
字体度量可能与行内设计基线不一致。

---

## 8. scripts/doctor.sh

| 场景 | 命令 | 退出码 | 结论 |
|---|---|---|---|
| 语法检查 | `bash -n scripts/doctor.sh` | 0 | `SYNTAX_OK` |
| 文件属性 | — | — | 10196 B / 259 行 / LF（crlf=0）/ 末行换行 / 可执行位 0755 |
| **最小非登录环境全量运行** | `env -i HOME=$HOME PATH=/usr/bin:/bin TERM=dumb bash scripts/doctor.sh` | **0** | `PASS=15 WARN=2 FAIL=0` / `RESULT: HEALTHY` |
| 跳过基线开关 | `DOCTOR_SKIP_VERIFY=1 ... bash scripts/doctor.sh` | **0** | `[WARN] DOCTOR_SKIP_VERIFY=1，已跳过原型基线复跑` / `PASS=14 WARN=3 FAIL=0` / HEALTHY |
| **负向测试（工具链缺失）** | `env -i HOME=/tmp/emptyhome PATH=/usr/bin:/bin bash scripts/doctor.sh` | **1** | 打印 `[FAIL] node 不可用`、`[FAIL] npm 不可用`、`[FAIL] uv 不可用`、`[FAIL] verify.sh 退出码 127`；`PASS=5 WARN=3 FAIL=5` / `RESULT: UNHEALTHY（5 项 FAIL）` |

`env -i` + `PATH=/usr/bin:/bin` 证明脚本不依赖登录 shell 的 PATH，自发现逻辑
（`~/.local/bin`、`~/.local/share/node/bin`）真实生效。doctor 对依赖只检测不安装：
`uv sync --locked --dry-run` 与 `npm ci --dry-run`，运行后 `web/node_modules` 与 `.venv` 未被改动。

---

## 9. 契约符合性校验（scripts 之外的一次性核对）

以 `spec/CampaignLab-SDD-v1.0/contracts/dependencies.json` 为唯一判据，逐项比对锁文件实际版本：

| 校验 | 退出码 | 结果 |
|---|---|---|
| Python：`uv.lock` × `python_runtime` 7 项（`packaging.SpecifierSet`） | 0 | 全部 `IN-RANGE`，`PYTHON_VIOLATIONS=0` |
| Python：`uv.lock` × `python_dev` 6 项 | 0 | 全部 `PRESENT` |
| Python：`target.python` / `target.sqlite` | 0 | `3.14.10` 满足 `>=3.14,<3.15`；`3.53.1` 满足 `>=3.38 with JSON functions` |
| 前端：`package-lock.json` × `frontend_runtime` 4 项（`semver.satisfies`） | 0 | 全部 `IN-RANGE` |
| 前端：`package-lock.json` × `frontend_dev` 9 项 | 0 | 4 项 `IN-RANGE` + 5 项 `STABLE-RESOLVED`（契约为 `resolve compatible stable`），`NPM_VIOLATIONS=0` |
| `engines.node` × 实际 node | 0 | `>=24 <25` vs `v24.22.3` → `true`；对契约 `>=24,<25` 亦为 `true` |

**偏离区间项：0。** 唯一需登记的是一处**区间内收窄**与两项**契约未列的必需 peer**，详见 `npm.md` 第 4 节。

---

## 10. 未执行 / 边界确认

- 未执行 `git add` / `git commit` / `git push`；收尾 `git status --porcelain` 仅
  `?? .python-version`、`?? pyproject.toml`、`?? scripts/doctor.sh`、`?? uv.lock`、`?? web/`。
- 未使用 `sudo` / `apt-get`；未改动 `/mnt/d`；所有产物落在 ext4（仓库、`~/.local`、`~/.cache`）。
- 未修改 `spec/**`；未读取 `contracts/openapi.json`。
- 未创建 `src/campaignlab`、`migrations/`、`tests/` 任何内容。
- 未修改 `.gitignore`（现有 `node_modules/`、`dist/` 已覆盖 `web/node_modules`、`web/dist`）。
- 未安装 Playwright 浏览器（本机已存在所需 v1254，无需安装）。
