# Python 后台与规则开发规范

- Python 3.14 正常 CPython 构建。分层保持依赖朝领域内收。HTTP DTO 与域对象单独建模，业务用例接收已验证输入。Pydantic 拒绝未知字段、布尔冒充整数、非有限数值和不带偏移的时刻。
- 统一 snake_case，业务枚举用字符串常量及明确类型。可选值明确 Optional 语义。面向钱款、次数、预算、事件状态的函数给定输入后可重复。避免单个函数同时接 HTTP、写库、读大文件和改规则。
- 服务层应用事务，不在路由里直接写 SQL。SQLite 连接短时持有。数据库异常翻译为领域错误，服务日志保留 request_id，不泄露用户源字段。
- 长分析和规则批次进入 worker。生命周期、幂等、重试、取消和租约按 [作业契约](../architecture/JOBS.md)。HTTP 进程只运行有界计算。每次业务运行传入显式时钟或事件时间，避免在领域计算内调用系统当前时间。
- 规则实现按两个类型模板、金额分整数、输入事件顺序和清晰原因码。规则检查生成有范围的反例。使用纯函数测试相等边界、重复、退款、初始占用和失效状态。
- 对外 REST 严格符合 [OpenAPI](../contracts/openapi.json)。202、Problem、ETag、幂等、游标语义做契约测试。单元测试用 pytest 固定时刻和临时目录，集成测试用真实 SQLite 临时库、DuckDB 与 HTTP 客户端。
- 变更校验顺序为 ruff、类型检查、单元、契约、迁移、模块集成。失败记录现象、断言、输入与修复原因。遇到设计矛盾先更新 ADR、Schema、示例和关联验收，再改行为。

官方资料 [FastAPI](https://fastapi.tiangolo.com/features/) · [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/changelog/) · [SQLAlchemy SQLite](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)
