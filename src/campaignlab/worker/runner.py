"""作业执行循环：handler 注册、协作式取消、9 条迁移的运行期编排（M0-04/S2）。

**与 ``application/worker.py::WorkerSupervisor`` 的分工**（A90②，务必读）：

- ``WorkerSupervisor`` 是 M0-02 的冻结面：它拥有后台线程与**进程内**心跳 ``heartbeat_at``，
  ``Health.worker`` 的 READY/OFFLINE 由它决定；它的 ``poll_once()`` 只做「取就绪队列 →
  按 kind 找 handler → ``heartbeat()`` 取租约 → 调 handler」。本卡**一字未改**它。
- ``WorkerRunner``（本模块）是 M0-04 的**执行**路径：认领（T1）、续租（T3）、终态提交
  （T5/T6/T8）、恢复扫描（T7）、重试（T9）都在这里编排，SQL 全部经 ``JobStore`` 落到
  ``JobRepository``（A81）。
- 两条路径共用两个单点：租约期限的 Python 计算点 ``compute_lease_deadline``（A83），
  以及 jobs 表的 SQL 写点 ``JobRepository``（A81／A70 判据②）。

本模块**不起线程**：线程生命周期归 ``WorkerSupervisor``。``run_forever`` 是一个由调用方
用 ``stop`` 谓词驱动、用可注入 ``sleeper`` 休眠的同步循环——测试传记录型假函数，
**禁**用固定时长 ``sleep`` 制造时序（design §4）。
"""

from __future__ import annotations

import contextlib
import json
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final, Literal

from campaignlab.api.common import ObjectRef, Problem
from campaignlab.application.worker import WORKER_POLL_INTERVAL_SECONDS
from campaignlab.clock import Clock
from campaignlab.domain.ids import new_request_id
from campaignlab.infra.db.repositories import JobRecord
from campaignlab.worker.errors import LeaseLost, no_handler_problem, problem_of
from campaignlab.worker.leases import LEASE_TTL_SECONDS, Lease
from campaignlab.worker.states import JOB_KINDS
from campaignlab.worker.store import (
    DEFAULT_AUDIT_ROLE,
    Claim,
    JobStore,
    Reaped,
    RenewResult,
)

__all__ = [
    "SYSTEM_ACTOR_ID",
    "CancelToken",
    "HandlerRegistry",
    "JobContext",
    "JobHandler",
    "JobOutcome",
    "WorkerRunner",
]

#: 系统行为者的 ``audit.actor_id``：worker 自身发起的迁移（T7 中断、T8 到期）没有会话，
#: 但 ``audit.actor_id`` 是 NOT NULL，故用一个固定且可辨识的取值。
SYSTEM_ACTOR_ID: Final = "system:worker"

#: handler 签名：拿到 ``JobContext``，回一个 ``JobOutcome``。
#:
#: 注意这与 ``application/worker.py::JobHandler``（``Callable[[JobRecord], None]``，M0-02
#: 冻结面）**同名不同形**：那一个只吃行、不回值，结构上无法表达 T5/T6（既拿不到胜出的
#: lease token，也没有结果指针可交）。design §9 把本模块的 ``JobHandler`` 列为独立符号，
#: 二者刻意并存、各自服务自己的循环。
JobHandler = Callable[["JobContext"], "JobOutcome"]


@dataclass(frozen=True, slots=True)
class JobOutcome:
    """handler 的返回值：三种终态之一，加上该终态需要的载荷。

    刻意做成**封闭三选一**而不是让 handler 直接调 store：handler 拿不到 Connection，
    就无法在事务外偷偷写库，也就无法绕过「先提交者定终态」（design §4）。
    """

    state: Literal["CANCELLED", "FAILED", "SUCCEEDED"]
    result_ref: ObjectRef | None = None
    problem: Problem | None = None
    stage: str | None = None
    retryable: bool | None = None

    @classmethod
    def succeeded(cls, result_ref: ObjectRef, *, stage: str | None = None) -> JobOutcome:
        """T5：必须带 ``result_ref``——DDL 的双条件 CHECK 要求 SUCCEEDED ⇔ 结果非空。"""
        return cls(state="SUCCEEDED", result_ref=result_ref, stage=stage, retryable=False)

    @classmethod
    def failed(
        cls,
        problem: Problem,
        *,
        retryable: bool | None = None,
        stage: str | None = None,
    ) -> JobOutcome:
        """T6：``retryable`` 留 ``None`` 即由 ``states.retryable_for`` 按 problem.code 现算。"""
        return cls(state="FAILED", problem=problem, stage=stage, retryable=retryable)

    @classmethod
    def cancelled(cls, *, stage: str | None = None) -> JobOutcome:
        """T8 的执行确认入口：handler 在安全分段读到 ``ctx.cancelled()`` 后返回它。"""
        return cls(state="CANCELLED", stage=stage, retryable=True)


class CancelToken:
    """协作式取消信号（JOBS.md:14「执行进程在安全分段读取取消信号」）。

    刻意**不**做抢占式 kill：JOBS.md:27 明载「被 kill 的作业视为中断」，抢占会让「取消」
    与「中断」在证据上无法区分。handler 在安全分段边界主动查 ``cancelled()``，
    检测延迟上界＝``RENEW_INTERVAL_SECONDS``（design §4 末条）。
    """

    def __init__(self) -> None:
        self._event = threading.Event()

    def request(self) -> None:
        self._event.set()

    def cancelled(self) -> bool:
        return self._event.is_set()


class JobContext:
    """handler 唯一能看到的作业面：读输入、报进度、查取消信号。

    刻意**不给** handler 任何 ``Connection``／``Engine``／``JobStore``：事务边界属 store，
    「禁在事务内做重 I/O」（design §4）只有在 handler 拿不到连接时才是硬约束。
    """

    def __init__(
        self,
        *,
        record: JobRecord,
        lease: Lease,
        store: JobStore,
        clock: Clock,
        cancel: CancelToken | None = None,
        lease_seconds: int = LEASE_TTL_SECONDS,
    ) -> None:
        self._record = record
        self._lease = lease
        self._store = store
        self._clock = clock
        self._cancel = cancel if cancel is not None else CancelToken()
        self._lease_seconds = lease_seconds

    @property
    def record(self) -> JobRecord:
        return self._record

    @property
    def lease(self) -> Lease:
        return self._lease

    @property
    def workspace_id(self) -> str:
        return self._record.workspace_id

    @property
    def job_id(self) -> str:
        return self._record.id

    @property
    def kind(self) -> str:
        return self._record.kind

    @property
    def attempt(self) -> int:
        return self._lease.attempt

    def input_payload(self) -> Any:
        """``jobs.input_json`` 解析后的对象。解析失败即抛，**不**静默回落成 ``None``。"""
        return json.loads(self._record.input_json)

    def cancelled(self) -> bool:
        """handler 在安全分段边界调用它（JOBS.md:14）。"""
        return self._cancel.cancelled()

    def request_cancel(self) -> None:
        """本地立起取消信号。测试用它模拟「取消已到达执行侧」，不经数据库。"""
        self._cancel.request()

    def renew(self, *, stage: str, progress: int) -> RenewResult:
        """T3 续租 + 写阶段进度（JOBS.md:13「每 5 秒续租」）。

        顺带回读 ``state``：若已 ``CANCEL_REQUESTED`` 就立刻置本地 ``CancelToken``
        （design §4 末条），**不额外发查询、不长事务轮询**。返回 ``renewed=False`` 表示
        租约守卫不成立（attempt/token 失配或已过期），handler 应当立即停手并返回
        ``JobOutcome.cancelled()`` 或直接退出——它已经没有发布权了。
        """
        result = self._store.renew(
            self._lease,
            now=self._clock.now(),
            stage=stage,
            progress=progress,
            lease_seconds=self._lease_seconds,
        )
        if result.cancel_requested:
            self._cancel.request()
        return result


class HandlerRegistry:
    """``kind -> handler`` 的注册表。

    只接受 ``JOB_KINDS`` 里的 10 个类型（JOBS.md:5）：注册一个契约外的 kind 会让作业永远
    认领不到，是静默故障，故当场拒。**src 内不放业务 handler**（A89）——测试桩注册在
    ``tests/integration/jobs/conftest.py``，业务映射归 M1/M2。
    """

    def __init__(self, handlers: Mapping[str, JobHandler] | None = None) -> None:
        self._handlers: dict[str, JobHandler] = {}
        self._lock = threading.RLock()
        for kind, handler in dict(handlers or {}).items():
            self.register(kind, handler)

    def register(self, kind: str, handler: JobHandler) -> None:
        if kind not in JOB_KINDS:
            raise ValueError(f"未知的作业类型：{kind!r}（JOBS.md:5 共 {len(JOB_KINDS)} 个）")
        with self._lock:
            self._handlers[kind] = handler

    def get(self, kind: str) -> JobHandler | None:
        with self._lock:
            return self._handlers.get(kind)

    def kinds(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._handlers))

    def __contains__(self, kind: object) -> bool:
        with self._lock:
            return kind in self._handlers

    def __len__(self) -> int:
        with self._lock:
            return len(self._handlers)


class WorkerRunner:
    """9 条迁移的运行期编排者。

    一次 ``poll_once`` 的完整轨迹：``claim_next``（T1，拿到 lease）→ 找 handler →
    建 ``JobContext`` → 调 handler（其间 handler 自行 ``ctx.renew()`` 走 T3）→ 按
    ``JobOutcome`` 提交 T5／T6／T8。**未注册 kind** 不跳过而是直接判 T6 失败
    （``VALIDATION_ERROR`` + ``issues[0].code='NO_HANDLER'``、``retryable=0``，design §9）：
    一条没人能干的作业留在 QUEUED 里会永远堵在队首，把它判失败才看得见、才可诊断。
    """

    def __init__(
        self,
        *,
        clock: Clock,
        store: JobStore,
        registry: HandlerRegistry,
        lease_seconds: int = LEASE_TTL_SECONDS,
        poll_interval_seconds: float = WORKER_POLL_INTERVAL_SECONDS,
        sleeper: Callable[[float], None] = time.sleep,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        if lease_seconds < 1:
            raise ValueError(f"租约时长必须 >= 1 秒：{lease_seconds}")
        self._clock = clock
        self._store = store
        self._registry = registry
        self._lease_seconds = lease_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._sleeper = sleeper
        self._logger = logger

    # ------------------------------------------------------------------ 结构化日志（无副作用）

    def _note(self, message: str) -> None:
        """记一条结构化日志。**只记类型名与 ID，不记异常文本**（OPERATIONS.md:19：
        不回显堆栈／SQL／用户源字段）。未注入 logger 时静默丢弃。"""
        if self._logger is not None:
            self._logger(message)

    # ------------------------------------------------------------------------- T7/T8 恢复

    def recover(self, *, now: datetime | None = None) -> Reaped:
        """启动即跑的恢复扫描（JOBS.md:23「遇到中断，启动恢复逻辑扫描过期租约」）。

        委托 ``JobStore.reap_expired``（TX7）：过期 RUNNING → FAILED + ``JOB_INTERRUPTED``
        （T7），过期 CANCEL_REQUESTED → CANCELLED（T8 的第二条入口）。终态行恒不被触碰。
        """
        moment = self._clock.now() if now is None else now
        reaped = self._store.reap_expired(now=moment)
        if reaped.total:
            self._note(
                "recover 扫描到过期租约："
                f"interrupted={reaped.interrupted} cancelled={reaped.cancelled}"
            )
        return reaped

    # ------------------------------------------------------------------------------ T3

    def beat(
        self, lease: Lease, *, stage: str, progress: int, now: datetime | None = None
    ) -> RenewResult:
        """design §9 点名的 ``beat``：T3 续租的运行期入口，委托 ``JobStore.renew``。

        与 ``WorkerSupervisor.heartbeat()`` 的关系见 A70 判据③：后者是 ``touch_lease`` 的
        唯一调用方、只推迟租约期限；本方法走 ``JobRepository.renew``，额外校验 ``attempt``
        并写 ``stage``／``progress`` —— 那是 ``touch_lease`` 的签名结构上表达不了的
        （它不收 stage/progress、也不匹配 attempt）。两条路径互不调用、互不替代。
        """
        moment = self._clock.now() if now is None else now
        return self._store.renew(
            lease,
            now=moment,
            stage=stage,
            progress=progress,
            lease_seconds=self._lease_seconds,
        )

    # ------------------------------------------------------------------------ T1 + 执行

    def poll_once(self, *, workspace_id: str, now: datetime | None = None, limit: int = 1) -> int:
        """认领并执行至多 ``limit`` 条作业，返回**认领**条数。

        ``limit`` 而非「一轮扫干」：单轮工作量必须有界（PYTHON.md:6「HTTP 进程只运行
        有界计算」同理适用于同进程的 worker）。认领失败（队列空／被抢先／写锁冲突）
        即停，不在本轮重试——下一轮 ``poll_once`` 自然会再试。
        """
        moment = self._clock.now() if now is None else now
        claimed = 0
        for _ in range(max(1, limit)):
            claim = self._store.claim_next(
                workspace_id=workspace_id, now=moment, lease_seconds=self._lease_seconds
            )
            if not claim.claimed:
                if claim.contended:
                    self._note(f"claim 撞写锁，本轮退让：workspace={workspace_id}")
                break
            claimed += 1
            self.execute(claim, now=moment)
        return claimed

    def execute(self, claim: Claim, *, now: datetime) -> JobRecord | None:
        """跑一条已认领的作业到终态。返回终态行；未提交成功（租约失效）时返回 ``None``。

        任何 ``LeaseLost`` 都被**吞掉并记日志**（design §4：「败者不得覆写、不得重试成
        第二终态，只记结构化日志」）。这是「取消与完成争用，先提交者定终态」的运行期
        半边：数据库谓词保证败者改不动行，本方法保证败者不去反复重试。
        """
        record = claim.record
        lease = claim.lease
        if record is None or lease is None:
            return None
        handler = self._registry.get(record.kind)
        if handler is None:
            self._note(f"未注册 kind，判 T6 失败：job={record.id} kind={record.kind}")
            with contextlib.suppress(LeaseLost):
                return self._store.fail(
                    lease,
                    problem=no_handler_problem(kind=record.kind),
                    now=now,
                    retryable=False,
                )
            return None
        ctx = JobContext(
            record=record,
            lease=lease,
            store=self._store,
            clock=self._clock,
            lease_seconds=self._lease_seconds,
        )
        try:
            outcome = handler(ctx)
        except Exception as exc:  # handler 是外部代码，任何异常都不得逃出 worker 循环
            self._note(
                f"handler 抛出异常：job={record.id} kind={record.kind} type={type(exc).__name__}"
            )
            with contextlib.suppress(LeaseLost):
                return self._store.fail_unhandled(lease, error=exc, now=now)
            return None
        return self._commit(ctx, outcome, now=now)

    def _commit(self, ctx: JobContext, outcome: JobOutcome, *, now: datetime) -> JobRecord | None:
        """按 ``JobOutcome`` 提交 T5／T6／T8。``LeaseLost`` 一律静默放弃。"""
        lease = ctx.lease
        if outcome.state == "SUCCEEDED":
            if outcome.result_ref is None:
                self._note(f"SUCCEEDED 缺 result_ref，改判失败：job={ctx.job_id}")
                with contextlib.suppress(LeaseLost):
                    return self._store.fail_unhandled(
                        lease,
                        error=ValueError("JobOutcome.succeeded 必须带 result_ref"),
                        now=now,
                    )
                return None
            with contextlib.suppress(LeaseLost):
                return self._store.succeed(lease, result_ref=outcome.result_ref, now=now)
            return None
        if outcome.state == "CANCELLED":
            with contextlib.suppress(LeaseLost):
                return self._store.confirm_cancel(
                    lease,
                    now=now,
                    actor_id=SYSTEM_ACTOR_ID,
                    request_id=new_request_id(),
                    role=DEFAULT_AUDIT_ROLE,
                )
            return None
        problem = (
            outcome.problem if outcome.problem is not None else problem_of(_internal_failure())
        )
        with contextlib.suppress(LeaseLost):
            return self._store.fail(lease, problem=problem, now=now, retryable=outcome.retryable)
        return None

    # ---------------------------------------------------------------------------- 循环

    def run_forever(
        self,
        *,
        workspace_id: str,
        stop: Callable[[], bool],
        max_rounds: int | None = None,
        recover_on_start: bool = True,
        limit: int = 1,
    ) -> int:
        """同步轮询循环。**不起线程**——线程与进程内心跳归 ``WorkerSupervisor``。

        ``stop`` 是调用方给的停止谓词（``WorkerSupervisor`` 的 ``threading.Event.is_set``
        即可直接传），``max_rounds`` 给测试一个确定性的上界。休眠走注入的 ``sleeper``：
        默认 ``time.sleep``，测试传记录型假函数并推进 ``FixedClock``，**禁**用固定时长
        休眠制造时序（design §4）。
        """
        if recover_on_start:
            self.recover()
        handled = 0
        rounds = 0
        while not stop():
            if max_rounds is not None and rounds >= max_rounds:
                break
            rounds += 1
            handled += self.poll_once(workspace_id=workspace_id, limit=limit)
            self._sleeper(self._poll_interval_seconds)
        return handled


def _internal_failure() -> Any:
    """``JobOutcome.failed`` 却没带 Problem 时的兜底（handler 违约，500）。"""
    from campaignlab.domain.errors import InternalFailure

    return InternalFailure("handler 返回 FAILED 但未提供 Problem")
