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
from pathlib import Path
from typing import Final, Literal, Protocol, runtime_checkable

from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from campaignlab.api.common import Health
from campaignlab.clock import Clock
from campaignlab.config import AppConfig, repo_root
from campaignlab.infra.db.engine import connect

__all__ = [
    "MIGRATIONS_DIR",
    "UNMIGRATED_REVISION",
    "HealthService",
    "WorkerStatus",
    "read_migration_head",
]

#: 迁移目录（相对仓库根）。与 ``cli.MIGRATIONS_DIR`` 同值；见 ``read_migration_head`` 的
#: 单一来源说明（Q 项已上报编排器）。
MIGRATIONS_DIR: Final = "migrations"

#: 库尚未迁移时 ``Health.schema_revision`` 的取值。刻意**不等于**任何合法 revision 串，
#: 这样 ``status`` 才会落 DEGRADED 而不是假 READY。
UNMIGRATED_REVISION: Final = "UNMIGRATED"


def read_migration_head(migrations_dir: Path | None = None) -> str | None:
    """alembic 脚本目录的当前 head；取不到返回 ``None``（调用方降级，不猜 revision）。

    **单一来源说明（已列为 Q 项）**：``cli._migration_head()`` 是同一段逻辑的既有实现，
    但 ``cli.py`` 在本片只允许改两处，把它改成委托本函数属越界。故本轮两处并存，
    已请编排器裁定后续由哪一侧收口；两处的判据完全一致（同一个 ``alembic.ini``、
    同一个 ``ScriptDirectory.get_current_head()``），不存在口径分叉。
    """
    directory = migrations_dir if migrations_dir is not None else repo_root() / MIGRATIONS_DIR
    ini = directory / "alembic.ini"
    if not ini.is_file():
        return None
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
    except ImportError:
        return None
    try:
        cfg = Config(str(ini))
        cfg.set_main_option("script_location", str(ini.parent))
        return ScriptDirectory.from_config(cfg).get_current_head()
    except Exception:
        return None


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
