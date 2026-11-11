# 工具链与工程框架规范

## 目录和运行入口

本目录提供实施依据。实现工作区保留本包在 `spec/` 或作为项目根目录中的固定基线，实际业务代码使用下列模块。

| 路径 | 用途 |
|---|---|
| pyproject.toml、uv.lock、.python-version | Python 项目、依赖锁、精确 CPython 补丁 |
| src/campaignlab/api/ | FastAPI 路由、DTO、错误、会话及作用域 |
| src/campaignlab/application/ | 用例、事务、工作区和作业调度 |
| src/campaignlab/domain/ | 活动、规则、计算口径、结果、报告及状态约束 |
| src/campaignlab/infra/ | SQLite 仓储、文件、DuckDB、审计 |
| src/campaignlab/worker/ | 作业认领、租约、处理器、结果提交 |
| migrations/ | Alembic，首迁与参考 DDL 等价 |
| web/ | Vue 源码、Vite、测试、package-lock.json |
| tests/ | Python 单元、契约、集成、恢复与性能样例 |
| scripts/ | 本机启动、环境检查、备份和恢复入口 |
| evidence/ | 阶段实测记录与检查摘要，测试数据合成 |

命令契约为 `uv run python -m campaignlab serve` 启动 HTTP 和后台进程，`uv run python -m campaignlab doctor` 检查绑定、版本、数据目录、数据库和 worker，`uv run python -m campaignlab backup --output <dir>` 与 `restore --input <dir> --target <dir>` 执行恢复流程。启动器设置独立数据目录和入口令牌，进程收到终止时先停止受理、后释放作业。默认访问地址由启动器显示。

## 依赖选择和锁定

[依赖约束](../contracts/dependencies.json) 给出初始主版本区间。M0 在目标 Ubuntu 环境解析稳定发行版本，锁定 Python、Node、Python 包和 npm 包。记录 CPython patch、sqlite3.sqlite_version、Node 和浏览器。先验证 DuckDB、Pydantic Core 和浏览器在目标机可安装，再保存锁。实际版本由生成的锁与环境证据决定。

- Python 开发使用 `uv sync --locked`。CI 与发布环境使用锁文件，按目标系统和架构准备 wheel 缓存。依赖升级单独提交和复跑。
- 前端使用 Node 24 LTS 和 npm，`npm ci` 与 `npm run build` 可复现构建，生产只带静态文件。
- 可用的构建缓存、浏览器及字体在目标主机准备，首次安装的包源按目标机规则。运行验收断开外部服务，数据、图表、静态资源和页面会话仍可工作。
- Python 每模块声明依赖理由，前端只引入实际调用的组件和图表。固定锁、记录许可证、记录兼容性与回退版本。

## 质量命令

Python 配置 ruff check、ruff format --check、mypy、pytest。前端 package.json 实现 lint、typecheck、test、build、test:e2e。契约检查校验 OpenAPI 3.1、JSON Schema、DDL 与实现路由响应，前端从 OpenAPI 生成类型客户端并检测差异。发布环境的浏览器版本随 Playwright 安装固定。

官方文档于 2026-11-12 核对。[Python 版本](https://devguide.python.org/versions/) · [uv 锁定](https://docs.astral.sh/uv/concepts/projects/sync/) · [Node 发布](https://nodejs.org/en/about/previous-releases) · [Vite 指南](https://vite.dev/guide/) · [Vitest 迁移](https://vitest.dev/guide/migration/) · [Playwright CLI](https://playwright.dev/docs/test-cli)
