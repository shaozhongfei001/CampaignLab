# SQLite DuckDB 与数据分析开发规范

## SQLite 与迁移

以 [参考 DDL](../contracts/sqlite-v1.sql) 为结构目标。用 Alembic 管理顺序迁移，每次迁移提供空库、上版数据保留和外键一致性检查。禁止跨工作区读取或以 UI 条件代替数据库作用域。使用 SQLAlchemy 2.x typed query 和参数绑定。短事务提交，可靠的幂等、备份和作业租约按领域契约处理。

## 文件与 DuckDB

- 先按 [接入数据契约](../architecture/DATA.md) 固定字段类型和快照，再进入 DuckDB。CSV 的类型转换发生在映射层。缺值、非法值、零和负数各有明确语义。
- 表名与字段来自受控元数据，SQL 查询由固定模板和白名单组装。过滤值参数化，文件路径由制品 ID 解析。读取 CSV 时记录列名、源行和数据字典，宽长转换校验键唯一性。
- DuckDB 查询每任务独立连接，读 Parquet 固定快照。使用显式 ORDER BY，设置 threads=2、memory_limit=1GiB、临时目录及磁盘上限，验证实际进程峰值。DuckDB 的 memory_limit 针对缓冲区，运行进程 RSS 另测。大结果仅返回概要或分页，制品保存明细。
- 指标函数独立校验计数并集、分母、语义对齐、缺失值、比较基准与变化单位。分析 SQL 报告写执行计划、基准快照与参数。单表聚合与跨维度并集用等价小样本交叉校核。
- 分析基准先用甲乙各 510 切片，再生成 1 万聚合切片与 10 万事件的合成压力数据。记录真实行数、过滤粒度、磁盘、冷暖缓存、返回行数及耗时。性能问题优先查读范围、分区、排序和中间表。

官方资料 [DuckDB 并发](https://duckdb.org/docs/2.0/connect/concurrency) · [Parquet 读取](https://duckdb.org/docs/stable/data/parquet/overview) · [DuckDB 限制](https://www.duckdb.org/docs/current/operations_manual/limits) · [SQLite 本机并发](https://sqlite.org/wal.html)
