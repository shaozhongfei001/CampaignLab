"""``jobs`` 的**事务边界**层：一方法一短事务，SQL 一律委托 ``JobRepository``（M0-04/S2）。

A81 裁定：``infra/db/repositories.py::JobRepository`` 是**唯一**含 jobs 插入／更新语句的
模块，design §10-N5 提议的「``JobStore`` 为唯一 SQL 写点」已被否决。故本模块**不含任何
jobs 表的 DML 文本**——认领、9 条迁移、终态写入、重试入队全部调用 ``JobRepository``
的方法（A82 给它纯追加的那批）。本文件只承担 ``JobRepository`` 刻意不管的三件事：

1. ``BEGIN IMMEDIATE`` 短事务的开关与回滚。``immediate()`` 只发**事务控制**语句
   （``BEGIN IMMEDIATE``／``COMMIT``／``ROLLBACK``），一条表 DML 都没有；这是 design §4
   点名的并发原语，也是「两个执行者争用只有一个成功」的物理前提。
2. ``rowcount == 0`` → 领域错的翻译：404／409／412／429 与 worker 侧的 ``LeaseLost``。
   仓储层刻意只回 ``int``，把「零行意味着什么」留给知道上下文的本层判断。
3. 状态变更与 ``audit`` 的**同事务**写入（JOBS.md:12「写审计」；design §4 末条）。

连接口径照 design §4：每个事务一条新连接、AUTOCOMMIT 隔离级、短时持有、不跨线程。
库路径不在本文件出现——本层只接 ``Engine``，路径解析仍单点在 ``infra/db/paths.py``
（ADR-005 §2.4 裁定 2）。
"""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy import Connection, Engine
from sqlalchemy.exc import OperationalError

from campaignlab.api.common import ObjectRef, Problem, canonical_json
from campaignlab.application.audit import OUTCOME_ACCEPTED, AuditWriter
from campaignlab.application.worker import compute_lease_deadline
from campaignlab.domain.errors import (
    DomainError,
    InternalFailure,
    ResourceNotFound,
    RevisionConflict,
    StateConflict,
)
from campaignlab.domain.ids import new_resource_id
from campaignlab.infra.db.engine import connect
from campaignlab.infra.db.repositories import (
    ArtifactRecord,
    ArtifactRepository,
    JobRecord,
    JobRepository,
)
from campaignlab.worker.capacity import check_capacity, pending_states
from campaignlab.worker.errors import LeaseLost, interrupted_problem, problem_of
from campaignlab.worker.leases import LEASE_TTL_SECONDS, Lease, is_expired, new_lease_token
from campaignlab.worker.states import STAGE_CLAIMED, STAGE_QUEUED, is_terminal, retryable_for

__all__ = [
    "ACTION_JOB_CANCELLED",
    "ACTION_JOB_CANCEL_REQUESTED",
    "ACTION_JOB_RETRIED",
    "DEFAULT_AUDIT_ROLE",
    "JOB_ID_PREFIX",
    "TARGET_KIND_JOB",
    "Claim",
    "JobRow",
    "JobStore",
    "Reaped",
    "RenewResult",
    "connect_autocommit",
    "immediate",
    "short_transaction",
]

#: 事务控制语句。**只此三条**是本模块出现的全部 SQL 文本，且都与表无关。
_BEGIN_IMMEDIATE: Final = "BEGIN IMMEDIATE"
_COMMIT: Final = "COMMIT"
_ROLLBACK: Final = "ROLLBACK"

#: SQLite 写锁被占时的错误文本（``BEGIN IMMEDIATE`` 拿不到 RESERVED 锁）。
_LOCKED_MARKER: Final = "database is locked"

#: ``jobs.id`` 前缀（design §3 T9：``new_resource_id("J")``）。
JOB_ID_PREFIX: Final = "J"
#: ``audit.target_kind``：与 ``ObjectRef.kind`` 的 21 枚举里的 ``job`` 同字。
TARGET_KIND_JOB: Final = "job"
#: ``audit.action`` 三值。``audit.action`` 列在 DDL 里无 CHECK，取值由本卡定义。
ACTION_JOB_CANCEL_REQUESTED: Final = "JOB_CANCEL_REQUESTED"
ACTION_JOB_CANCELLED: Final = "JOB_CANCELLED"
ACTION_JOB_RETRIED: Final = "JOB_RETRIED"
#: 本机模式下的审计角色（A72：优先 OPERATOR）。调用方**应当**显式传 ``role``，
#: 这个默认值只是让 worker 自身（无会话）发起的系统迁移也有确定取值。
DEFAULT_AUDIT_ROLE: Final = "OPERATOR"

#: 行形态直接复用 ``JobRecord``（design §9 的 ``JobRow``）：不抄第二份 17 字段表，
#: 否则 ``jobs`` 加一列就要改两处；A82 也禁我改 ``JobRecord``。
JobRow = JobRecord


@contextmanager
def immediate(conn: Connection) -> Iterator[None]:
    """``BEGIN IMMEDIATE`` 短事务（design §4 的并发原语）。

    为什么必须是 IMMEDIATE 而不是默认的 DEFERRED：SQLite 的写锁在**第一条写语句**才申请。
    DEFERRED 事务里「先 SELECT 再 UPDATE」的两个并发写者会各自读到 QUEUED、各自升级到写
    锁，后者拿不到锁就在事务中途失败——已经做过的读白费，还可能留下半状态。IMMEDIATE 在
    ``BEGIN`` 时就取 RESERVED 锁，把写者**串行化**在事务入口，于是败者要么立刻退让、要么
    在胜者提交后读到最新状态，两种结局都干净。

    前置条件：``conn`` 处于 AUTOCOMMIT 隔离级（见 ``connect_autocommit``），否则
    SQLAlchemy 自己已经开了一个事务，再发 ``BEGIN`` 会报错。异常一律 ``ROLLBACK`` 后原样
    重抛——不回滚会把失败事务的写留给下一条语句，正是「留下半状态」的成因。
    """
    conn.exec_driver_sql(_BEGIN_IMMEDIATE)
    try:
        yield
    except BaseException:
        # ROLLBACK 自身失败（连接已断等）不得掩盖原始异常。
        with contextlib.suppress(Exception):
            conn.exec_driver_sql(_ROLLBACK)
        raise
    conn.exec_driver_sql(_COMMIT)


def connect_autocommit(engine: Engine) -> Connection:
    """开一条 AUTOCOMMIT 连接，交给 ``immediate()`` 显式控事务。

    AUTOCOMMIT 在这里**不是**「不要事务」，而是「关掉 SQLAlchemy 与 pysqlite 的隐式
    事务，由本模块显式发 ``BEGIN IMMEDIATE``」——隐式 BEGIN 是 DEFERRED 的，拿不到
    写者串行化（见 ``immediate`` 的说明）。
    """
    return engine.connect().execution_options(isolation_level="AUTOCOMMIT")


@contextmanager
def short_transaction(engine: Engine) -> Iterator[Connection]:
    """一个事务一条新连接（design §4：连接短时持有、不跨线程）。"""
    conn = connect_autocommit(engine)
    try:
        with immediate(conn):
            yield conn
    finally:
        conn.close()


def _is_lock_contention(error: OperationalError) -> bool:
    """``BEGIN IMMEDIATE`` 撞写锁（``busy_timeout`` 耗尽）的判定。

    只认 ``database is locked``／``database is busy``：其余 ``OperationalError``
    （磁盘满、库损坏、SQL 语法）是真故障，必须原样抛出，不能被当成「这轮没抢到」。
    """
    raw = error.orig
    text_ = str(raw) if raw is not None else str(error)
    return isinstance(raw, sqlite3.OperationalError) and (
        _LOCKED_MARKER in text_ or "database is busy" in text_
    )


@dataclass(frozen=True, slots=True)
class Claim:
    """一次认领的结果。

    ``record`` 为 ``None`` 即「这一轮没拿到活」，三种成因都不是错误：队列空、被别人抢先
    （谓词 UPDATE ``rowcount == 0``）、写锁被占（``contended=True``）。调用方按需重试或
    睡到下一轮，**不抛异常**——``WorkerSupervisor.poll_once`` 对 ``heartbeat()`` 返回
    ``False`` 的处理是同一语义。
    """

    record: JobRecord | None
    lease: Lease | None
    contended: bool = False

    @property
    def claimed(self) -> bool:
        return self.record is not None and self.lease is not None


@dataclass(frozen=True, slots=True)
class RenewResult:
    """一次续租（T3）的结果。``record`` 顺带回读 ``state``，供执行侧发现取消信号。"""

    renewed: bool
    record: JobRecord | None

    @property
    def cancel_requested(self) -> bool:
        """design §4 末条：续租顺带回读 ``state``，``CANCEL_REQUESTED`` 即置取消信号。"""
        return self.record is not None and self.record.state == "CANCEL_REQUESTED"


@dataclass(frozen=True, slots=True)
class Reaped:
    """一次恢复扫描（TX7）的战果：T7 记中断几条、T8 到期收口几条。"""

    interrupted: int
    cancelled: int

    @property
    def total(self) -> int:
        return self.interrupted + self.cancelled


class JobStore:
    """``jobs`` 的事务边界 + 领域错翻译 + 同事务审计。

    每个公开方法**恰好一个**短事务（design §4：「事务号即函数边界，一函数一事务，禁一
    函数跨两事务」）。方法内不做重 I/O：摘要计算、临时件写入、DuckDB 计算一律在事务外
    由 handler 完成，事务内唯一允许的文件操作是 T5 的制品登记（且 ``os.replace`` 归
    ``infra/artifacts.py``，本层只发 ``ArtifactRepository.insert``）。
    """

    def __init__(
        self,
        *,
        engine: Engine,
        jobs: JobRepository | None = None,
        audit: AuditWriter | None = None,
        artifacts: ArtifactRepository | None = None,
    ) -> None:
        self._engine = engine
        self._jobs = jobs if jobs is not None else JobRepository()
        self._audit = audit if audit is not None else AuditWriter()
        self._artifacts = artifacts if artifacts is not None else ArtifactRepository()

    # --------------------------------------------------------------------------- 只读

    def get_job(self, *, workspace_id: str, job_id: str) -> JobRecord | None:
        """按主键读一行。跨工作区自然读不到（主键含 ``workspace_id``），即 OPERATIONS.md:7
        「外工作区对象按 404 返回」的落点。只读，不开写事务。"""
        with connect(self._engine) as conn:
            return self._jobs.get(conn, workspace_id=workspace_id, job_id=job_id)

    def pending_count(self, *, workspace_id: str) -> int:
        """非终态计数（A88②）。只读；真正的闸在 ``retry`` 的事务内重算一次。"""
        with connect(self._engine) as conn:
            return self._jobs.count_pending(
                conn, workspace_id=workspace_id, states=pending_states()
            )

    # --------------------------------------------------------------------- T1 认领（TX1）

    def claim_next(
        self,
        *,
        workspace_id: str,
        now: datetime,
        lease_seconds: int = LEASE_TTL_SECONDS,
        stage: str = STAGE_CLAIMED,
    ) -> Claim:
        """认领最早可认领的一条 QUEUED 作业（JOBS.md:11 / design §3 T1 / §4 TX1）。

        租约期限**只**经 ``compute_lease_deadline`` 取得（A83），本方法不自己算时间；
        令牌每次新生成，故两次认领必得两个不同 token——这正是「失效 lease token 的提交
        必须被拒」能成立的前提。

        写锁冲突（并发认领的败者）翻译成 ``Claim(contended=True)`` 而**不是**异常：
        AC-029 要求「两次尝试争抢同一作业时只有有效租约可发布」，败者必须干净失败且
        不留半状态——``immediate()`` 的 ``ROLLBACK`` 保证后者，本方法保证前者。
        """
        token = new_lease_token()
        deadline = compute_lease_deadline(now, lease_seconds=lease_seconds)
        try:
            with short_transaction(self._engine) as conn:
                record = self._jobs.claim_next(
                    conn,
                    workspace_id=workspace_id,
                    lease_token=token,
                    lease_deadline=deadline,
                    stage=stage,
                )
        except OperationalError as exc:
            if _is_lock_contention(exc):
                return Claim(record=None, lease=None, contended=True)
            raise
        if record is None:
            return Claim(record=None, lease=None)
        return Claim(record=record, lease=Lease.of(record))

    # --------------------------------------------------------------------- T3 续租（TX2）

    def renew(
        self,
        lease: Lease,
        *,
        now: datetime,
        stage: str,
        progress: int,
        lease_seconds: int = LEASE_TTL_SECONDS,
    ) -> RenewResult:
        """续租并写阶段进度（JOBS.md:13「每 5 秒续租」/ design §3 T3 / §4 TX2）。

        谓词带 ``attempt`` 与 ``lease_token``，故租约易主后本方法**改不动任何字段**，
        只回 ``renewed=False``（AC-029「失效租约不能提交」在续租路径上的同一保证）。
        刻意不在此抛 ``LeaseLost``：续租失败在长跑作业里是「该收手了」的信号，
        由 ``WorkerRunner.beat`` 决定是静默放弃还是记日志。
        """
        deadline = compute_lease_deadline(now, lease_seconds=lease_seconds)
        with short_transaction(self._engine) as conn:
            record = self._jobs.renew(
                conn,
                workspace_id=lease.workspace_id,
                job_id=lease.job_id,
                attempt=lease.attempt,
                lease_token=lease.token,
                lease_deadline=deadline,
                stage=stage,
                progress=progress,
            )
        return RenewResult(renewed=record is not None, record=record)

    # ------------------------------------------------------------- T2/T4 请求取消（TX3）

    def request_cancel(
        self,
        *,
        workspace_id: str,
        job_id: str,
        revision: int,
        now: datetime,
        actor_id: str,
        request_id: str,
        role: str = DEFAULT_AUDIT_ROLE,
    ) -> JobRecord:
        """操作员请求取消（``cancelJob``）：QUEUED 直接终态、RUNNING 先置 CANCEL_REQUESTED。

        JOBS.md 的第 2 行与第 4 行是**同一条** UPDATE 的两个分支（见
        ``JobRepository.request_cancel`` 的说明）：一个事务里发两条语句等于给「先提交者
        定终态」凭空造出第二个竞争者。

        错误分类顺序＝design §6 的 ``cancelJob`` 行：404（读不到，含跨工作区）→ 409
        ``STATE_CONFLICT``（已终态，或已请求过取消）→ 412 ``REVISION_CONFLICT``
        （``If-Match`` 与当前 ``revision`` 不符）。读取与写入在同一 ``BEGIN IMMEDIATE``
        事务内，写者被串行化，故这次分类不会被并发改动插队。

        审计与状态变更**同事务**（JOBS.md:12「写审计」；design §4 末条）：审计写失败则
        取消一起回滚，不留「状态改了但没证据」的窗口。
        """
        with short_transaction(self._engine) as conn:
            current = self._jobs.get(conn, workspace_id=workspace_id, job_id=job_id)
            if current is None:
                raise ResourceNotFound(f"作业不存在或不属于该工作区：{job_id}")
            if is_terminal(current.state) or current.state == "CANCEL_REQUESTED":
                raise StateConflict(f"作业已处于 {current.state}，不可再请求取消")
            touched = self._jobs.request_cancel(
                conn, workspace_id=workspace_id, job_id=job_id, revision=revision
            )
            if touched != 1:
                raise RevisionConflict(f"If-Match 与当前 revision 不符：{revision}")
            self._audit.write(
                conn,
                workspace_id=workspace_id,
                at=now,
                actor_id=actor_id,
                role=role,
                action=ACTION_JOB_CANCEL_REQUESTED,
                target_kind=TARGET_KIND_JOB,
                target_id=job_id,
                outcome=OUTCOME_ACCEPTED,
                request_id=request_id,
            )
            fresh = self._jobs.get(conn, workspace_id=workspace_id, job_id=job_id)
        if fresh is None:
            raise StateConflict(f"取消已提交但回读失败：{job_id}")
        return fresh

    # ------------------------------------------------------- T8 执行确认取消（TX4）

    def confirm_cancel(
        self,
        lease: Lease,
        *,
        now: datetime,
        actor_id: str,
        request_id: str,
        role: str = DEFAULT_AUDIT_ROLE,
    ) -> JobRecord:
        """执行进程在安全分段确认后收口为 CANCELLED（JOBS.md:18 的第一条入口 / TX4）。

        与 ``JobStore.reap_expired`` 里的到期收口（第二条入口）同终态、不同守卫：这条要
        ``attempt`` ＋ ``lease_token`` 自证身份，那条只要租约已过期。两条的前态都只有
        ``CANCEL_REQUESTED``，故谁先提交谁定终态，败者 ``rowcount == 0``。

        ``rowcount == 0`` 抛 ``LeaseLost`` 而**不是** ``StateConflict``：调用方是持租约的
        执行者，改不动行的原因只可能是租约已失效或作业已被别人收口，两者对执行者的处置
        相同——静默放弃（design §4）。租约已过期时在**开事务之前**就先拒：此时该由 TX7
        的到期入口收口，执行者已失去发布权（JOBS.md:21）。
        """
        if is_expired(lease.deadline, now=now):
            raise LeaseLost(f"租约已过期，不得确认取消：job={lease.job_id}")
        with short_transaction(self._engine) as conn:
            touched = self._jobs.confirm_cancel(
                conn,
                workspace_id=lease.workspace_id,
                job_id=lease.job_id,
                attempt=lease.attempt,
                lease_token=lease.token,
            )
            if touched != 1:
                raise LeaseLost(f"取消确认未命中守卫：job={lease.job_id} attempt={lease.attempt}")
            self._audit.write(
                conn,
                workspace_id=lease.workspace_id,
                at=now,
                actor_id=actor_id,
                role=role,
                action=ACTION_JOB_CANCELLED,
                target_kind=TARGET_KIND_JOB,
                target_id=lease.job_id,
                outcome=OUTCOME_ACCEPTED,
                request_id=request_id,
            )
            fresh = self._jobs.get(conn, workspace_id=lease.workspace_id, job_id=lease.job_id)
        if fresh is None:
            raise StateConflict(f"取消已提交但回读失败：{lease.job_id}")
        return fresh

    # ------------------------------------------------------------------- T5 成功（TX5）

    def succeed(
        self,
        lease: Lease,
        *,
        result_ref: ObjectRef,
        now: datetime,
        artifacts: Sequence[ArtifactRecord] = (),
    ) -> JobRecord:
        """成功收口：登记制品与结果引用，**同事务公开结果**（JOBS.md:15 / design §3 T5）。

        顺序是刻意的：先插 ``artifacts`` 行，再发那条把 ``state`` 改成 SUCCEEDED 的谓词
        UPDATE。若 UPDATE ``rowcount == 0``（租约失效，或取消抢先提交），整个事务回滚，
        制品行不会留下——这正是 JOBS.md:23「旧尝试结果登记失败时其制品视为未引用」的
        数据库侧对偶（文件侧的孤儿件由 ``sweep_unreferenced`` 回收，归 S3）。

        与取消争用：本方法的前态集合含 ``CANCEL_REQUESTED``，与 ``confirm_cancel`` 相交，
        谁先 ``COMMIT`` 谁定终态。败者抛 ``LeaseLost``，调用方**禁**重试成第二终态，
        只记结构化日志（design §4）。

        ``result_json`` 存 ``ObjectRef`` 的 JSON 对象、走 ``canonical_json``（A73）：键序
        稳定，同内容必得同字节，摘要与重放才可复现。
        """
        if is_expired(lease.deadline, now=now):
            # AC-029「失效租约不能提交」：过期即失去发布权。SQL 谓词匹配的是
            # attempt + lease_token，在「已过期但 TX7 还没扫到」的窗口里仍会 rowcount=1，
            # 故必须由这条纯函数前置判定堵住（JOBS.md:21「只有有效租约可发布」）。
            raise LeaseLost(f"租约已过期，不得提交成功：job={lease.job_id}")
        result_json = canonical_json(result_ref.model_dump(mode="json"))
        with short_transaction(self._engine) as conn:
            for artifact in artifacts:
                self._artifacts.insert(conn, artifact=artifact)
            touched = self._jobs.mark_succeeded(
                conn,
                workspace_id=lease.workspace_id,
                job_id=lease.job_id,
                attempt=lease.attempt,
                lease_token=lease.token,
                result_json=result_json,
            )
            if touched != 1:
                raise LeaseLost(f"成功提交未命中租约守卫：job={lease.job_id}")
            fresh = self._jobs.get(conn, workspace_id=lease.workspace_id, job_id=lease.job_id)
        if fresh is None:
            raise StateConflict(f"成功已提交但回读失败：{lease.job_id}")
        return fresh

    # ------------------------------------------------------------------- T6 失败（TX6）

    def fail(
        self,
        lease: Lease,
        *,
        problem: Problem,
        now: datetime,
        retryable: bool | None = None,
    ) -> JobRecord:
        """已知失败收口（JOBS.md:16 / design §3 T6 / §4 TX6）。

        守卫与 ``succeed`` 逐字相同，故失败与取消／成功争用时同样是先提交者定终态。
        ``retryable`` 缺省时按 design §3 的口径由 ``retryable_for`` 现算（``FAILED`` → 1，
        除非 ``problem.code`` 属永久性输入缺陷）。``stage``／``progress`` 刻意不写，
        保留失败发生的阶段作为诊断证据。租约已过期时同样在开事务前先拒。
        """
        if is_expired(lease.deadline, now=now):
            # 与 ``succeed`` 同理：过期租约不得发布任何终态，失败也不行。
            raise LeaseLost(f"租约已过期，不得提交失败：job={lease.job_id}")
        problem_json = canonical_json(problem.model_dump(mode="json"))
        resolved = retryable_for("FAILED", problem.code) if retryable is None else bool(retryable)
        with short_transaction(self._engine) as conn:
            touched = self._jobs.mark_failed(
                conn,
                workspace_id=lease.workspace_id,
                job_id=lease.job_id,
                attempt=lease.attempt,
                lease_token=lease.token,
                problem_json=problem_json,
                retryable=resolved,
            )
            if touched != 1:
                raise LeaseLost(f"失败提交未命中租约守卫：job={lease.job_id}")
            fresh = self._jobs.get(conn, workspace_id=lease.workspace_id, job_id=lease.job_id)
        if fresh is None:
            raise StateConflict(f"失败已提交但回读失败：{lease.job_id}")
        return fresh

    # ------------------------------------------------------- T7 + T8 到期（TX7 恢复扫描）

    def reap_expired(self, *, now: datetime) -> Reaped:
        """恢复扫描：过期租约的 RUNNING 记中断（T7）、过期的 CANCEL_REQUESTED 收口（T8）。

        JOBS.md:23「遇到中断，启动恢复逻辑扫描过期租约，不重写已成功作业」——两条 UPDATE
        的前态集合分别是 ``RUNNING`` 与 ``CANCEL_REQUESTED``，**都不含任何终态**，故已
        SUCCEEDED／FAILED／CANCELLED 的行恒不被触碰；QUEUED 没有租约，也不在扫描面内。

        两条语句共用**一个**事务（design §4 TX7）：一次恢复扫描要么整体生效要么整体回滚，
        不会出现「中断记了、取消没记」的半截恢复。

        中断的 Problem 形状由 A88③ 钉死：``code='INTERNAL_ERROR'``、``status=500``、
        ``issues[0].code='JOB_INTERRUPTED'``——``JOB_INTERRUPTED`` **不得**进
        ``Problem.code``，那会污染 ADR-005 冻结的 20 码注册表。
        """
        now_text = now.isoformat()
        problem_json = canonical_json(interrupted_problem().model_dump(mode="json"))
        with short_transaction(self._engine) as conn:
            interrupted = self._jobs.fail_expired_running(
                conn, now=now_text, problem_json=problem_json
            )
            cancelled = self._jobs.cancel_expired_requested(conn, now=now_text)
        return Reaped(interrupted=interrupted, cancelled=cancelled)

    # ------------------------------------------------------------------------- 入队

    def enqueue(
        self,
        *,
        workspace_id: str,
        kind: str,
        input_json: str,
        input_digest: str,
        now: datetime,
        job_id: str | None = None,
        retry_of: str | None = None,
    ) -> JobRecord:
        """入队一条 QUEUED 作业（TX8 的入队半边）。

        **复用 ``JobRepository.insert``**，本方法不含任何插入语句（A81／FU-10：禁新增
        jobs 插入落点）。``insert`` 自己会拒非 QUEUED、拒带租约、拒带 result/problem 的行，
        这三条前置校验正是 DDL 那三条 CHECK 的 Python 侧对偶。
        """
        record = JobRecord(
            workspace_id=workspace_id,
            id=job_id if job_id is not None else new_resource_id(JOB_ID_PREFIX),
            kind=kind,
            state="QUEUED",
            attempt=0,
            progress=0,
            stage=STAGE_QUEUED,
            lease_token=None,
            lease_deadline=None,
            retry_of=retry_of,
            retryable=False,
            input_json=input_json,
            input_digest=input_digest,
            result_json=None,
            problem_json=None,
            revision=1,
            created_at=now.isoformat(),
        )
        with short_transaction(self._engine) as conn:
            self._jobs.insert(conn, job=record)
            fresh = self._jobs.get(conn, workspace_id=workspace_id, job_id=record.id)
        if fresh is None:
            raise StateConflict(f"入队已提交但回读失败：{record.id}")
        return fresh

    # ------------------------------------------------------------- T9 重试（TX8）

    def retry(
        self,
        *,
        workspace_id: str,
        job_id: str,
        revision: int,
        now: datetime,
        actor_id: str,
        request_id: str,
        role: str = DEFAULT_AUDIT_ROLE,
    ) -> JobRecord:
        """操作员发起重试：**新建**一条 QUEUED 作业，源作业终态一字不变（JOBS.md:19 / TX8）。

        事务内顺序（design §4）：读源作业 → 404／409 分类 → **容量闸** → 谓词 UPDATE 源
        作业 ``revision + 1`` → 经 ``JobRepository.insert`` 落新行 → 写审计。

        容量闸必须在 ``BEGIN IMMEDIATE`` **之内**重算：IMMEDIATE 把写者串行化，故两个并发
        重试不可能各自读到 9 再各自入队成 11（A88②：待办＝非终态计数，上限 10，触发时
        ``JobCapacity`` 带 ``retry_after=3``，HTTP 层落成 ``Retry-After: 3``）。

        新行逐字复制 ``kind``／``input_json``／``input_digest``（JOBS.md:19「引用 retry_of
        与同一输入快照」），``attempt`` 从 0 重起、``revision`` 从 1 重起；源作业只
        ``revision + 1``，让客户端手里的 ``If-Match`` 失效、被迫重读——历史终态是可回查的
        证据，不被重试抹掉（AC-029「重试得到一次可见结果」）。
        """
        with short_transaction(self._engine) as conn:
            source = self._jobs.get(conn, workspace_id=workspace_id, job_id=job_id)
            if source is None:
                raise ResourceNotFound(f"作业不存在或不属于该工作区：{job_id}")
            if source.state not in ("CANCELLED", "FAILED"):
                raise StateConflict(f"只有 FAILED／CANCELLED 的作业可重试：当前 {source.state}")
            check_capacity(
                self._jobs.count_pending(conn, workspace_id=workspace_id, states=pending_states())
            )
            new_id = new_resource_id(JOB_ID_PREFIX)
            new_job = JobRecord(
                workspace_id=workspace_id,
                id=new_id,
                kind=source.kind,
                state="QUEUED",
                attempt=0,
                progress=0,
                stage=STAGE_QUEUED,
                lease_token=None,
                lease_deadline=None,
                retry_of=source.id,
                retryable=False,
                input_json=source.input_json,
                input_digest=source.input_digest,
                result_json=None,
                problem_json=None,
                revision=1,
                created_at=now.isoformat(),
            )
            if (
                self._jobs.enqueue_retry(
                    conn,
                    workspace_id=workspace_id,
                    source_job_id=job_id,
                    source_revision=revision,
                    new_job=new_job,
                )
                != 1
            ):
                # 源行的读取与本 UPDATE 在同一 IMMEDIATE 事务内、状态已校验过，
                # 故 rowcount == 0 只可能是 revision 过期。
                raise RevisionConflict(f"If-Match 与当前 revision 不符：{revision}")
            self._audit.write(
                conn,
                workspace_id=workspace_id,
                at=now,
                actor_id=actor_id,
                role=role,
                action=ACTION_JOB_RETRIED,
                target_kind=TARGET_KIND_JOB,
                target_id=new_id,
                outcome=OUTCOME_ACCEPTED,
                request_id=request_id,
            )
            fresh = self._jobs.get(conn, workspace_id=workspace_id, job_id=new_id)
        if fresh is None:
            raise StateConflict(f"重试已提交但回读失败：{new_id}")
        return fresh

    # ------------------------------------------------------------------ 供 runner 复用

    def fail_unhandled(self, lease: Lease, *, error: BaseException, now: datetime) -> JobRecord:
        """把 handler 抛出的异常翻成 T6 失败（``problem_of`` + ``fail`` 的组合）。

        ``error`` 是 ``DomainError`` 时逐字段搬其已解析的 code／status／title／issues；
        其余异常一律 500 ``INTERNAL_ERROR``，**不回显**异常文本（OPERATIONS.md:19：
        不回显堆栈／SQL／用户源字段），细节只进结构化日志。
        """
        if isinstance(error, DomainError):
            problem = problem_of(error, request_id=None)
        else:
            problem = problem_of(InternalFailure("作业执行失败"), request_id=None)
        return self.fail(lease, problem=problem, now=now)
