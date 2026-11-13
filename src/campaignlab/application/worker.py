"""后台 worker 与租约（M0-02 · S3d；design §4「worker 状态在 health 可见」/ §6）。

两条裁定落在本文件：

- **A11/N3**：``heartbeat(job_id, *, now)`` 是**全仓唯一**写 ``jobs.lease_until`` 的入口。
  租约期限只在这里从**注入时钟**派生（``now + lease_seconds``）；``infra/db/repositories.py``
  只提供把它写进列里的那一条 SQL，别的模块连调用点都没有。
- **design §4**：``Health.worker`` 的判定基于**进程内**心跳 ``heartbeat_at``，
  ``(now - heartbeat_at) <= WORKER_HEARTBEAT_TTL_SECONDS`` → ``READY``，否则 ``OFFLINE``；
  循环体一旦抛异常就置 ``failed = True``，``status()`` 立即 ``OFFLINE`` —— 否则
  「线程已死但心跳还在窗口内」会误报 READY（design §4 点名的失败模式）。

**M0-02 不执行任何作业**：契约里没有 HTTP 作业面（Q2），四种分析对象与 ``actions`` 写权
分别归 M1+ 与 M4-02（A6/A14/A15），本里程碑没有可注册的 ``kind``。故 ``poll_once()``
在 ``handlers`` 为空时直接返回 0，只承担「让心跳活着」这一件事；worker 线程的存在
是为了让 ``Health.worker`` 报出真实的 READY，而不是为了跑活。

线程与连接：每轮用 ``infra.db.engine.connect()`` 开关短连接，**不**跨线程持有
``sqlite3.Connection``（design §4）。``Engine`` 本身线程安全，默认 ``NullPool`` 不缓存连接。
"""

from __future__ import annotations

import secrets
import threading
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Final, Literal

from sqlalchemy import Engine

from campaignlab.clock import Clock
from campaignlab.config import WORKER_HEARTBEAT_TTL_SECONDS
from campaignlab.infra.db.engine import connect
from campaignlab.infra.db.repositories import JobRecord, JobRepository

__all__ = [
    "WORKER_BATCH_SIZE",
    "WORKER_LEASE_SECONDS",
    "WORKER_POLL_INTERVAL_SECONDS",
    "JobHandler",
    "WorkerSupervisor",
    "compute_lease_deadline",
]

#: 租约时长。取得／续约后，超过这个窗口没有心跳，别的 worker 才允许接管。
WORKER_LEASE_SECONDS: Final = 30
#: 轮询间隔（秒）。单机场景取小值即可，不需要指数退避。
WORKER_POLL_INTERVAL_SECONDS: Final = 0.2
#: 单轮最多认领的作业数。
WORKER_BATCH_SIZE: Final = 8

#: 作业处理器签名。M0-02 不注册任何处理器（见模块 docstring）。
JobHandler = Callable[[JobRecord], None]


def compute_lease_deadline(now: datetime, *, lease_seconds: int) -> str:
    """租约期限的**全仓唯一** Python 计算点（A83 修订后的 A70 判据①）。

    本函数是 ``heartbeat()`` 原第 142 行内联表达式的**值语义等值**提取：算法一字未变，
    仍是「注入时钟给出的时刻 + 租约秒数」的 ISO-8601 文本。提取出来的动机是 M0-04 的
    认领路径（``QUEUED -> RUNNING`` 取租约）也需要同一个值：若 ``worker/**`` 自己再算
    一次，租约期限就有了第二个来源，A11「租约期限只由注入时钟派生、且只在 worker 内
    计算」的机器可查面即被破坏。故收敛为：**计算点只有本函数，其余模块只准 import
    调用、禁重算**（``worker/leases.py`` 因此只存常量与比较，不做加法）。

    只接受调用方从 ``Clock`` 取来的 ``now``：本函数不取系统时间，调用方也不得用固定
    时长休眠代替可控时钟（``campaignlab.clock`` 的 ``Clock`` / ``FixedClock``）。
    """
    return (now + timedelta(seconds=lease_seconds)).isoformat()


class WorkerSupervisor:
    """后台 worker 线程 + 心跳 + 租约轮询。

    ``status()`` 只读进程内状态，不碰数据库：``Health`` 是免会话的高频探针，
    让它每次都开一条 SQLite 连接，等于把健康检查变成负载源。
    """

    def __init__(
        self,
        *,
        clock: Clock,
        engine: Engine,
        jobs: JobRepository | None = None,
        heartbeat_ttl_seconds: int = WORKER_HEARTBEAT_TTL_SECONDS,
        lease_seconds: int = WORKER_LEASE_SECONDS,
        poll_interval_seconds: float = WORKER_POLL_INTERVAL_SECONDS,
        batch_size: int = WORKER_BATCH_SIZE,
        handlers: Mapping[str, JobHandler] | None = None,
    ) -> None:
        if heartbeat_ttl_seconds < 1:
            raise ValueError(f"心跳窗口必须 >= 1 秒：{heartbeat_ttl_seconds}")
        if lease_seconds < 1:
            raise ValueError(f"租约时长必须 >= 1 秒：{lease_seconds}")
        self._clock = clock
        self._engine = engine
        self._jobs = jobs if jobs is not None else JobRepository()
        self._heartbeat_ttl_seconds = heartbeat_ttl_seconds
        self._lease_seconds = lease_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._batch_size = batch_size
        self._handlers: Mapping[str, JobHandler] = dict(handlers or {})
        self._lease_token = secrets.token_urlsafe(24)
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._heartbeat_at: datetime | None = None
        self._failed = False
        self._last_error: str | None = None

    # ------------------------------------------------------------------ 对外状态（Health 用）

    def status(self, now: datetime) -> Literal["READY", "OFFLINE"]:
        """design §4 的判定式。线程已死／从未跳过／超出心跳窗口 → ``OFFLINE``。"""
        with self._lock:
            if self._failed:
                return "OFFLINE"
            beat = self._heartbeat_at
        if beat is None:
            return "OFFLINE"
        window = timedelta(seconds=self._heartbeat_ttl_seconds)
        return "READY" if (now - beat) <= window else "OFFLINE"

    @property
    def heartbeat_at(self) -> datetime | None:
        with self._lock:
            return self._heartbeat_at

    @property
    def failed(self) -> bool:
        with self._lock:
            return self._failed

    @property
    def last_error(self) -> str | None:
        """最后一次循环异常的类型与消息，仅供日志／诊断。

        **绝不**进 ``Health`` 响应体：那会把内部实现细节回显到契约面
        （OPERATIONS.md：不回显堆栈／SQL／用户源字段）。
        """
        with self._lock:
            return self._last_error

    @property
    def running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    # --------------------------------------------------------------------------- A11 唯一入口

    def heartbeat(self, job_id: str, *, now: datetime) -> bool:
        """取得／续约某作业的租约（**全仓唯一**写 ``jobs.lease_until`` 的入口，A11/N3）。

        返回 ``True``＝写成功；``False``＝该作业已不在可租约状态，或租约属于别的 worker
        （抢占保护，见 ``JobRepository.touch_lease``）。两种情况都不是错误，调用方按
        「这一轮没拿到活」处理即可。
        """
        lease_until = compute_lease_deadline(now, lease_seconds=self._lease_seconds)
        with connect(self._engine) as conn, conn.begin():
            touched = self._jobs.touch_lease(
                conn,
                job_id=job_id,
                lease_token=self._lease_token,
                lease_deadline=lease_until,
            )
        return touched > 0

    # ------------------------------------------------------------------------------ 轮询与线程

    def poll_once(self, *, now: datetime) -> int:
        """扫一轮就绪队列，为**已注册 kind** 的作业取租约并执行。返回认领条数。

        未注册 kind 的作业一律跳过（不取租约）：取了又没人干，只会把一条 QUEUED 作业
        变成永远 RUNNING 的僵尸。M0-02 的 ``handlers`` 恒为空，故本方法恒返回 0。
        """
        if not self._handlers:
            return 0
        with connect(self._engine) as conn:
            ready = self._jobs.list_ready(conn, limit=self._batch_size)
        claimed = 0
        for record in ready:
            handler = self._handlers.get(record.kind)
            if handler is None:
                continue
            if not self.heartbeat(record.id, now=now):
                continue
            handler(record)
            claimed += 1
        return claimed

    def start(self) -> None:
        """启动后台线程（幂等）。``daemon=True``：进程退出不被 worker 拖住。"""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._failed = False
            self._last_error = None
            thread = threading.Thread(target=self._run, name="campaignlab-worker", daemon=True)
            self._thread = thread
        thread.start()

    def stop(self, *, timeout: float | None = 2.0) -> None:
        """请求停止并等待线程退出。``timeout=None`` 表示无限等（测试里别用）。"""
        with self._lock:
            thread = self._thread
            self._thread = None
        self._stop.set()
        if thread is not None and thread.is_alive():
            thread.join(timeout)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.poll_once(now=self._clock.now())
                with self._lock:
                    self._heartbeat_at = self._clock.now()
                    self._failed = False
                    self._last_error = None
            except Exception as exc:
                # design §4：捕获后置 failed，status() 立即 OFFLINE、Health 降 DEGRADED。
                with self._lock:
                    self._failed = True
                    self._last_error = f"{type(exc).__name__}: {exc}"
            self._stop.wait(self._poll_interval_seconds)
