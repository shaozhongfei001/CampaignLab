# M0-01 编排器独立复核（T 循环交叉验证）

取证时间 2026-11-12T03:26:10+08:00

| 门禁 | 命令 | rc | 结论 |
|---|---|---|---|
| 锁一致性 | uv lock --check | 0 | Resolved 52 packages |
| 依赖同步 | uv sync --locked | 0 | Checked 50 packages |
| 前端锁 | npm --prefix web ci | 0 | added 218 packages |
| 前端构建 | npm --prefix web run build | 0 | vite build 成功 |
| Python 质量门 | uv run ruff check . | 0 | 见修正项 |
| 运行可用性 | import fastapi/duckdb/pydantic/sqlalchemy/alembic/uvicorn | 0 | duckdb 2.0.0 / pydantic 2.14.3 |
| 原型基线无回归 | bash scripts/verify.sh | 0 | SHA256SUMS OK、79/79 PASS、字节级复现（Node 24 下） |
| 环境诊断 | bash scripts/doctor.sh | 0 | PASS=15 WARN=2 FAIL=0，RESULT HEALTHY |

## 修正项（编排器发现并修复，attempt 内 1 轮）

1. 首次 ruff check . 报 720 错：spec 616、prototype 92、scripts 12。根因是质量门未排除 vendored 基线，且中文标点触发 RUF001/RUF002。已在 pyproject.toml 修正并复验 rc=0：ruff extend-exclude 排除 spec/prototype/web/node_modules；lint ignore 关闭 RUF001/RUF002/RUF003；mypy 加 files 与 exclude；pytest 加 testpaths 与 norecursedirs。
2. 首 patch 写出不合法 TOML（基本字符串内的 \.venv），已改为 [.]venv 正则写法。
3. 编排器自写的 scripts/contract_slice.py 有 E741 与 UP031 两处违规，已修正并回归切片功能。
4. prototype/ 不参与 Python lint，由 scripts/verify.sh 单独守护。

## cp314 wheel 判定（BLK-06 关闭）

CPython 3.14.10（uv standalone）下 duckdb 2.0.0、pydantic-core 2.50.4、sqlalchemy 2.0.57、alembic 1.20.1、fastapi 0.162.4、uvicorn 0.54.0、python-multipart 0.0.33 与 dev 工具全部安装成功，无需 ADR 回退。内置 SQLite 3.53.1，json_extract、json_valid、json_type、json_each、json_group_array 实测可用。

## 新发现（影响 BLOCKERS）

- BLK-01 降级：~/.cache/ms-playwright 已缓存 chromium-1254 与 headless shell，@playwright/test 已装，M5 的 E2E 可能无需 sudo，待 M0-03 用真实 spec 验证启动。
- BLK-02 仍在：fc-list :lang=zh 有 7 条字体但无 Noto Sans CJK，视觉度量可能与行内基线不一致。

## 锁文件哈希

| 文件 | sha256 前16 | 字节 |
|---|---|---|
| uv.lock | 4d3e6bc8af419fde | 129054 |
| web/package-lock.json | ee1cd610219f6347 | 122775 |
| pyproject.toml | c16a90a00026d950 | 2102 |
