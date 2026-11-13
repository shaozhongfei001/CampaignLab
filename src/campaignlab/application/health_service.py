"""``getHealth`` 的用例服务（M0-02 · S3d；design §1 第 3 条 / §4 / §6）。

``api/health.py`` 只调 ``snapshot() -> Health``，五字段的取值逻辑**全部**在本文件，
路由不复制任何一条判定：

- ``app_version``     ← ``AppConfig.app_version``；
- ``contract_version``← ``AppConfig.contract_version``，而它由 ``config.load_config()``
  经 ``read_contract_version(config.contract_path)`` 从**活契约** ``contracts/openapi.json``
  的 ``info.version`` 读出。本文件不再读第二遍：两处各读一次就会出现「健康面报的版本」
  与「装配时校验的版本」不一致，而 D-004 的教训正是版本口径必须只有一份；
- ``schema_revision`` ← 库文件 ``alembic_version`` 表的当前行；库不存在／未迁移 →
  ``UNMIGRATED_REVISION``（活契约只约束 1–48 的字符串，无 pattern，故合法）；
- ``worker``          ← ``WorkerSupervisor.status(now)``；未装配 worker → ``"OFFLINE"``；
- ``status``          ← ``"READY"`` 当且仅当 ``worker == "READY"`` 且 ``schema_revision``
  等于 alembic head（design §1）。

``status="READY"`` 的两个条件是**与**关系：库未迁移时 worker 再健康也必须 DEGRADED，
否则前端会在一个写不进数据的库上显示绿灯。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from campaignlab.api.common import Health
from campaignlab.clock import Clock
from campaignlab.config import AppConfig
from campaignlab.infra.db.engine import connect
from campaignlab.infra.db.migration_head import (
    MIGRATIONS_DIR,
    UNMIGRATED_REVISION,
    read_migration_head,
)

__all__ = [
    "MIGRATIONS_DIR",
    "UNMIGRATED_REVISION",
    "HealthService",
    "WorkerStatus",
    "read_migration_head",
]

#: ``MIGRATIONS_DIR`` / ``UNMIGRATED_REVISION`` / ``read_migration_head`` 自 FU-8（D-028 /
#: 裁定 A80）起以 ``campaignlab.infra.db.migration_head`` 为**唯一来源**，本模块只 re-export，
#: 不再自己实现一遍：``cli._migration_head()`` 与本模块 ``HealthService.snapshot()`` 从此共用
#: 同一个 head 判据，「doctor 报的迁移状态」与「/api/v1/health 的 schema_revision」不可能分叉。
#: 上面的 ``__all__`` 逐字未变，既有 ``from campaignlab.application.health_service import
#: UNMIGRATED_REVISION, HealthService`` 的读取方（含 S3d 用例）签名与语义都不受影响。
#: 唯一性守护：tests/unit/test_migration_head_single_source.py。


@runtime_checkable
class WorkerStatus(Protocol):
    """``HealthService`` 需要的 worker 侧面：只问「现在算不算在线」。

    与 ``api.deps`` 的三个端口**不同名**，故不违反「禁在 application 层再声明同名 Protocol」。
    """

    def status(self, now: datetime) -> Literal["READY", "OFFLINE"]: ...


class HealthService:
    """结构化满足 ``api.deps.HealthService``（``snapshot() -> Health``，已追认为冻结接口）。"""

    __slots__ = ("_clock", "_config", "_engine", "_worker")

    def __init__(
        self,
        *,
        config: AppConfig,
        clock: Clock,
        engine: Engine | None = None,
        worker: WorkerStatus | None = None,
    ) -> None:
        self._config = config
        self._clock = clock
        self._engine = engine
        self._worker = worker

    def schema_revision(self) -> str:
        """``alembic_version`` 当前行；库不存在／未迁移 → ``UNMIGRATED_REVISION``。

        只吞 ``OperationalError``（＝表不存在这一种预期情形）。库文件损坏、磁盘满一类
        错误必须往上冒成 500 —— 把它们也降级成 UNMIGRATED，等于让真故障伪装成
        「还没迁移」这种可恢复状态。
        """
        if self._engine is None:
            return UNMIGRATED_REVISION
        try:
            with connect(self._engine) as conn:
                row = conn.exec_driver_sql(
                    "SELECT version_num FROM alembic_version LIMIT 1"
                ).first()
        except OperationalError:
            return UNMIGRATED_REVISION
        if row is None or row[0] is None:
            return UNMIGRATED_REVISION
        return str(row[0])

    def worker_status(self, now: datetime) -> Literal["READY", "OFFLINE"]:
        """未装配 worker → ``OFFLINE``（design §4：``Health.worker`` 必须可见地反映真实状态）。"""
        if self._worker is None:
            return "OFFLINE"
        return self._worker.status(now)

    def snapshot(self) -> Health:
        now = self._clock.now()
        worker = self.worker_status(now)
        revision = self.schema_revision()
        head = read_migration_head()
        ready = worker == "READY" and head is not None and revision == head
        return Health(
            status="READY" if ready else "DEGRADED",
            app_version=self._config.app_version,
            contract_version=self._config.contract_version,
            worker=worker,
            schema_revision=revision,
        )
