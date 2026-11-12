# M0-01 cp314 / manylinux x86_64 wheel 可用性判定

- 目标解释器：CPython **3.14.10**（uv python-build-standalone `20261110`，ELF x86-64）
- 目标平台：linux / x86_64 / glibc（Ubuntu 24.04.2，WSL2）
- 判定依据（三重，互为印证）：
  1. `uv.lock` 中该包登记的 wheel 文件名（真实文件名，非推断）
  2. 已安装分发元数据 `*.dist-info/WHEEL` 的 `Tag:` 行（实际落地的那个 wheel）
  3. `uv sync` 退出码 0 且输出无 `Building`/`Built` 行 → 全部来自 wheel，无现场构建

**关键前提：本机无编译器**（`gcc`/`cc`/`g++`/`pkg-config` 均 MISSING，且无 sudo 无法安装
build-essential）。因此「sdist 现场构建」这条回退路径在本机**不存在**：任何缺 wheel 的包都会让
`uv sync` 直接失败。`uv sync` / `uv sync --locked` 退出码 0 本身即 wheel 全可用的强证明。

## 1. 判定表（任务卡指定的 13 项）

| 包名 | 目标 | 锁定版本 | 实际使用的 linux x86_64 wheel 文件名 | 安装后 WHEEL Tag | 判定 |
|---|---|---|---|---|---|
| duckdb | cp314 | 2.0.0 | `duckdb-2.0.0-cp312-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl` | `cp312-abi3-manylinux_2_27_x86_64` | **可用（abi3 稳定 ABI）** |
| pydantic-core | cp314 | 2.50.4 | `pydantic_core-2.50.4-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | `cp314-cp314-manylinux2014_x86_64` | **可用（原生 cp314）** |
| sqlalchemy | cp314 | 2.0.57 | `sqlalchemy-2.0.57-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl` | `cp314-cp314-manylinux_2_17_x86_64` | **可用（原生 cp314）** |
| alembic | cp314 | 1.20.1 | `alembic-1.20.1-py3-none-any.whl` | `py3-none-any` | **可用（纯 Python）** |
| fastapi | cp314 | 0.162.4 | `fastapi-0.162.4-py3-none-any.whl` | `py3-none-any` | **可用（纯 Python）** |
| uvicorn | cp314 | 0.54.0 | `uvicorn-0.54.0-py3-none-any.whl` | `py3-none-any` | **可用（纯 Python）** |
| python-multipart | cp314 | 0.0.33 | `python_multipart-0.0.33-py3-none-any.whl` | `py3-none-any` | **可用（纯 Python）** |
| ruff | cp314 | 0.17.4 | `ruff-0.17.4-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | `py3-none-manylinux_2_17_x86_64` | **可用（Rust 二进制，版本无关 tag）** |
| mypy | cp314 | 2.4.1 | `mypy-2.4.1-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl` | `cp314-cp314-manylinux_2_17_x86_64` | **可用（原生 cp314，mypyc 已编译）** |
| pytest | cp314 | 9.2.0 | `pytest-9.2.0-py3-none-any.whl` | `py3-none-any` | **可用（纯 Python）** |
| httpx | cp314 | 0.28.1 | `httpx-0.28.1-py3-none-any.whl` | `py3-none-any` | **可用（纯 Python）** |
| jsonschema | cp314 | 4.26.0 | `jsonschema-4.26.0-py3-none-any.whl` | `py3-none-any` | **可用（纯 Python）** |
| openapi-spec-validator | cp314 | 0.9.0 | `openapi_spec_validator-0.9.0-py3-none-any.whl` | `py3-none-any` | **可用（纯 Python）** |

**13/13 可用，0 项不可用，0 项需要 sdist 构建，0 项需要降级替代。**

### 关于 duckdb 的 abi3 说明（BLK-06 关注点）

duckdb 2.0.0 未发布字面 `cp314` tag 的 wheel，而是发布 `cp312-abi3` —— 这是 CPython **稳定 ABI**
（PEP 384）wheel，`abi3` 表示「cp312 及以上任意版本通用」，因此在 3.14 上不仅可安装，而且是官方
支持路径，非侥幸命中。已用三重实测确认可用性，而非仅凭文件名判定：

| 实测 | 结果 |
|---|---|
| site-packages 内落地二进制 | `_duckdb.abi3.so` |
| `import duckdb; duckdb.__version__` | `2.0.0` |
| `duckdb.connect().execute("select 40+2").fetchone()[0]` | `42` |
| `json_extract_string(...)`（真实查询，含参数绑定） | `v` |
| `select sum(x) from (values (1),(2),(3)) t(x)` | `6` |

### 关于 pydantic-core（BLK-06 另一关注点）

`pydantic_core-2.50.4-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` 为**字面 cp314 原生 wheel**，
无需 abi3 推断。实测：`pydantic.VERSION = 2.14.3`，`BaseModel` 定义/校验/`model_dump`/`model_json_schema`
与 `TypeAdapter(list[int]).validate_python(["1","2"])` 强转全部正常。

### BLK-06 判定

`BLOCKERS.md` BLK-06 的触发条件是「duckdb 或 pydantic-core 若无 cp314 wheel」。二者均有可用 wheel
（duckdb 走 abi3、pydantic-core 走原生 cp314）且实测可导入可查询，故 **BLK-06 不触发，无需 CR/ADR，
无需启用 ADR-002 的回退路径，也无需退回 Python 3.13**。

## 2. 传递依赖中的原生包（同样必须逐一有 wheel）

`uv.lock` 共 52 个包条目、`uv sync` 实装 50 个。其中「仅原生 wheel（无 py3-none-any 变体）」的
10 个包全部拿到 cp314 或 abi3 wheel，这是 `uv sync` 能退出 0 的必要条件：

| 包名 | 版本 | cp314 证据 |
|---|---|---|
| duckdb | 2.0.0 | `_duckdb.abi3.so` |
| pydantic-core | 2.50.4 | `cp314-cp314-manylinux2014_x86_64` |
| greenlet | 3.5.6 | `greenlet-3.5.6-cp314-cp314-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl`；落地 `greenlet/_greenlet.cpython-314-x86_64-linux-gnu.so` |
| sqlalchemy | 2.0.57 | `cp314-cp314-manylinux...`；`sqlalchemy.util.has_compiled_ext()` → True |
| mypy | 2.4.1 | `cp314-cp314-manylinux...`；`mypy --version` 报 `compiled: yes` |
| ast-serialize | 0.13.1 | `ast_serialize.abi3.so` |
| lazy-object-proxy | 1.13.0 | `lazy_object_proxy-1.13.0-cp314-cp314-manylinux1_x86_64...whl`；`cext.cpython-314-x86_64-linux-gnu.so` |
| librt | 0.16.0 | `librt-0.16.0-cp314-cp314-...`；7 个 `cpython-314-x86_64-linux-gnu.so` |
| markupsafe | 3.0.4 | `markupsafe-3.0.4-cp314-cp314-...`；`_speedups.cpython-314-x86_64-linux-gnu.so` |
| pyyaml | 6.0.3 | `pyyaml-6.0.3-cp314-cp314-...` |
| ruff | 0.17.4 | `py3-none-manylinux_2_17_x86_64`（Rust，版本无关） |

site-packages 内 `.so` 合计 **255 个**，命名一律为 `*.cpython-314-x86_64-linux-gnu.so` 或 `*.abi3.so`，
无任何 `cpython-312`/`cpython-313` 残留，可反证不存在「装了旧版 ABI 的二进制」这类隐性错配。

## 3. 锁文件与环境哈希

| 项 | 值 |
|---|---|
| `uv.lock` 大小 | 129054 B |
| `uv.lock` sha256（前 16 位） | `4d3e6bc8af419fde` |
| `uv.lock` 包条目数 | 52（`grep -c "^name = "`） |
| `requires-python`（锁内） | `==3.14.*` |
| `.venv` 解释器 | `/home/szf/dev/CampaignLab/.venv/bin/python` → `~/.local/share/uv/python/cpython-3.14.10-linux-x86_64-gnu/bin/python3.14` |

## 4. 复现命令

```
export PATH="$HOME/.local/bin:$HOME/.local/share/node/bin:$PATH"
# 本机 github.com 不可达，CPython 下载需镜像；已装好则无需该变量
export UV_PYTHON_INSTALL_MIRROR="https://mirror.nju.edu.cn/github-release/astral-sh/python-build-standalone"
uv python install 3.14
uv lock            # 或 uv lock --check 校验既有锁
uv sync --locked   # 退出码须为 0
```

注：`UV_PYTHON_INSTALL_MIRROR` 仅影响**解释器下载源**，不参与依赖解析，不写入 `pyproject.toml`
或 `uv.lock`，因此锁文件本身与镜像无关、在可达 GitHub 的 CI 上可原样复现。
