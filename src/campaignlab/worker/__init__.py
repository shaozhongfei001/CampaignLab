"""``campaignlab.worker``：作业状态机与执行循环（M0-04/S2）。

本包是 JOBS.md 第 11-19 行那 9 条迁移的运行期归属地。分层刻意做到「一眼看得出谁有权写库」：

- ``states.py``   纯数据：6 个状态、10 个 kind、9 条 ``Transition``、两条纯函数判定。
- ``errors.py``   领域错与 ``Problem`` 构造（只用注册表内的 20 个 code，A88③）。
- ``leases.py``   租约常量／令牌／过期**比较**。不做时间加法（A83）。
- ``capacity.py`` ``JOB_CAPACITY`` 闸：待办＝非终态计数，上限 10，``Retry-After=3``（A88②）。
- ``store.py``    **事务边界**：``BEGIN IMMEDIATE`` 短事务 + ``rowcount`` → 领域错 + 同事务审计。
- ``runner.py``   **执行编排**：handler 注册、协作式取消、认领→执行→终态提交。

三条不可越的红线：

1. **SQL 写点唯一**（A81）：本包**不含任何** jobs 表的 DML 文本。``store.py`` 里出现的
   全部 SQL 只有 ``BEGIN IMMEDIATE``／``COMMIT``／``ROLLBACK`` 三条事务控制语句；插入、
   9 条迁移的谓词 UPDATE、重试入队一律调用 ``infra.db.repositories.JobRepository``
   （A82 给它纯追加的那批方法）。
2. **租约期限计算点唯一**（A83 修订后的 A70 判据①）：只有
   ``application/worker.py::compute_lease_deadline`` 做 ``(now + timedelta(...)).isoformat()``，
   本包只 import 调用（``leases.deadline_after`` 也只是转发）。
3. **显式时钟**：本包任何位置都不取系统当前时间，``now`` 一律由调用方从 ``Clock`` 传入；
   等待用可注入的 ``sleeper``，不用固定时长休眠代替可控时钟。

未在本卡落地的 design §9 符号（``integrity.py``、``deps.py``、``store.list_jobs``）见
M0-04/S2 的回报：前者与 ``deps.get_artifact_writer`` 依赖 ``infra/artifacts.py``
（M0-04/S3，当前工作树内不存在），后者与其 HTTP 面 ``JobPage`` 一并由 A91 判归 Round 8。
"""

from __future__ import annotations

from campaignlab.worker.capacity import (
    JOB_CAPACITY_RETRY_AFTER_SECONDS,
    JOB_PENDING_LIMIT,
    check_capacity,
    pending_states,
)
from campaignlab.worker.errors import JOB_INTERRUPTED, NO_HANDLER, ArtifactCommitFailed, LeaseLost
from campaignlab.worker.leases import LEASE_TTL_SECONDS, RENEW_INTERVAL_SECONDS, Lease
from campaignlab.worker.runner import (
    CancelToken,
    HandlerRegistry,
    JobContext,
    JobHandler,
    JobOutcome,
    WorkerRunner,
)
from campaignlab.worker.states import (
    JOB_KINDS,
    JOB_STATES,
    TERMINAL_STATES,
    TRANSITIONS,
    Transition,
    TransitionId,
    assert_transition_allowed,
    retryable_for,
)
from campaignlab.worker.store import Claim, JobStore, Reaped, RenewResult, immediate

__all__ = [
    "JOB_CAPACITY_RETRY_AFTER_SECONDS",
    "JOB_INTERRUPTED",
    "JOB_KINDS",
    "JOB_PENDING_LIMIT",
    "JOB_STATES",
    "LEASE_TTL_SECONDS",
    "NO_HANDLER",
    "RENEW_INTERVAL_SECONDS",
    "TERMINAL_STATES",
    "TRANSITIONS",
    "ArtifactCommitFailed",
    "CancelToken",
    "Claim",
    "HandlerRegistry",
    "JobContext",
    "JobHandler",
    "JobOutcome",
    "JobStore",
    "Lease",
    "LeaseLost",
    "Reaped",
    "RenewResult",
    "Transition",
    "TransitionId",
    "WorkerRunner",
    "assert_transition_allowed",
    "check_capacity",
    "immediate",
    "pending_states",
    "retryable_for",
]
