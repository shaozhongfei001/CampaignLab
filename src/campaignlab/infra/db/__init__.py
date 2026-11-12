"""SQLite 侧基础设施：路径单一来源、连接工厂、迁移产物校验与（后续任务的）仓储实现。

本 ``__init__`` 刻意**不** re-export 任何子模块：``migrations/env.py`` 会 import
``campaignlab.infra.db.paths`` 与 ``campaignlab.infra.db.engine``，包初始化时若拉起
额外依赖（例如仓储层的 pydantic 模型），迁移期就会被无关的导入失败拖死。
需要哪个子模块就显式 import 哪个。

- ``paths``    ：数据库文件路径的唯一来源（ADR-005 §2.4），alembic 侧与运行期侧共用；
- ``engine``   ：运行期引擎/连接装配与 ``PRAGMAS`` 单一来源；
- ``ddl_compare``：首迁产物与参考 DDL 的等价性比对器。
"""
