"""仓储层：M0-02 真正接读写的 5 张表（M0-02 · S3d；design §3 / §6 ``infra/db/repositories.py``）。

边界（design §3）：28 张表里只有 ``workspaces`` / ``artifacts`` / ``jobs`` / ``idempotency`` /
``audit`` 5 张在本里程碑接读写，其余 23 张只建结构、不写 repository、不出现在任何路由。
本文件是这 5 张表**唯一**的 SQL 落点：

- ``JobRepository``（任务卡 A12/N5 所称的 *JobStore*）是唯一写 ``jobs`` 表的入口，
  其他模块禁直接 ``INSERT INTO jobs`` / ``UPDATE jobs``；
- ``jobs.lease_until`` 的**取值**只由 ``application/worker.py::WorkerSupervisor.heartbeat``
  派生（A11/N3）。本文件只提供「把这个值写进列里」的那一条 SQL，自己不算租约期限、
  也不在任何别处触碰该列——因此全仓 ``lease_until`` 的写路径只有一条。

三条实现口径：

1. **不持有连接**：每个方法首参都是 ``Connection``，由调用方经 ``infra.db.engine.connect()``
   在请求内开关。SQLite 连接不可跨线程共享（design §4 点名的失败模式）。
2. **事务由 application 层开**（``conn.begin()``）：仓储只发语句、不自行 commit，
   否则「``workspaces`` 与 ``audit`` 同事务」无从保证。
3. **键集翻页**（design §1）：排序固定 ``created_at DESC, id ASC``，谓词
   ``created_at < :k0 OR (created_at = :k0 AND id > :k1)``。``created_at`` 以 UTC ISO-8601
   文本落库，同格式字符串的字典序即时序，故可直接在 SQL 里比较。

``q`` 过滤走 NFKC + casefold（design §1），SQLite 既无 NFKC 也无 Unicode casefold，
故在 Python 侧对已按序取出的行做子串判定并**提前停止**（凑满 ``limit`` 即 break），
不在 SQL 里用 ``lower()``——那是 ASCII-only，会把全角／大小写混排的命中悄悄漏掉。
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final, cast

from sqlalchemy import Connection, text
from sqlalchemy.engine import RowMapping

from campaignlab.api.common import Job, JobKind, JobState, ObjectRef, Problem, Workspace

__all__ = [
    "ArtifactRecord",
    "ArtifactRepository",
    "AuditRecord",
    "AuditRepository",
    "IdempotencyRecord",
    "IdempotencyRepository",
    "JobRecord",
    "JobRepository",
    "WorkspaceRepository",
    "job_from_row",
]

#: ``workspaces`` 的列序（SELECT 与 DTO 映射共用一份，避免两处漂移）。
_WORKSPACE_COLUMNS: Final = "id, revision, created_at, name, source_class, authorization_note"

#: ``jobs`` 的列序。
_JOB_COLUMNS: Final = (
    "workspace_id, id, kind, state, attempt, progress, stage, lease_token, lease_until, "
    "retry_of, retryable, input_json, input_digest, result_json, problem_json, "
    "revision, created_at"
)


def _fold(value: str) -> str:
    """NFKC 归一 + casefold（design §1 的 ``q`` 匹配口径）。"""
    return unicodedata.normalize("NFKC", value).casefold()


def _iso(value: datetime) -> str:
    """持久层时刻统一 UTC ISO-8601（design §2）。"""
    return value.isoformat()


# --------------------------------------------------------------------------- 行记录（表结构镜像）


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    """``artifacts`` 行。``relative_path`` 是**全局** UNIQUE（不含 workspace_id），
    故制品路径必须内嵌 ``workspace_id`` 前缀，否则两工作区同内容互撞（design §4）。
    """

    workspace_id: str
    id: str
    kind: str
    sha256: str
    relative_path: str
    byte_size: int
    created_at: str


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """``idempotency`` 行。主键 ``(scope_key, actor_id, operation, idem_key)``。"""

    scope_key: str
    actor_id: str
    operation: str
    idem_key: str
    request_digest: str
    response_status: int
    response_json: str
    created_at: str

    def envelope(self) -> dict[str, Any]:
        """取回 ``api.common.idempotency_envelope`` 落下的信封。"""
        return cast(dict[str, Any], json.loads(self.response_json))


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """``audit`` 行。主键 ``(workspace_id, sequence)``、``UNIQUE(workspace_id, id)``。"""

    workspace_id: str
    sequence: int
    id: str
    at: str
    actor_id: str
    role: str
    action: str
    target_kind: str
    target_id: str
    outcome: str
    request_id: str
    previous_digest: str | None
    digest: str


@dataclass(frozen=True, slots=True)
class JobRecord:
    """``jobs`` 行。

    列 ``lease_until`` 在 Python 侧叫 ``lease_deadline``：这不是改名游戏，而是把
    「谁在决定租约期限」显式化——本文件只做绑定参数的搬运，A11 要求的取值点
    （``lease_until = ...``）只在 ``application/worker.py``。
    """

    workspace_id: str
    id: str
    kind: str
    state: str
    attempt: int
    progress: int
    stage: str
    lease_token: str | None
    lease_deadline: str | None
    retry_of: str | None
    retryable: bool
    input_json: str
    input_digest: str
    result_json: str | None
    problem_json: str | None
    revision: int
    created_at: str


def _workspace_of(row: RowMapping) -> Workspace:
    return Workspace(
        id=str(row["id"]),
        revision=int(row["revision"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        name=str(row["name"]),
        source_class=row["source_class"],
        authorization_note=row["authorization_note"],
    )


def _artifact_of(row: RowMapping) -> ArtifactRecord:
    return ArtifactRecord(
        workspace_id=str(row["workspace_id"]),
        id=str(row["id"]),
        kind=str(row["kind"]),
        sha256=str(row["sha256"]),
        relative_path=str(row["relative_path"]),
        byte_size=int(row["byte_size"]),
        created_at=str(row["created_at"]),
    )


def _idempotency_of(row: RowMapping) -> IdempotencyRecord:
    return IdempotencyRecord(
        scope_key=str(row["scope_key"]),
        actor_id=str(row["actor_id"]),
        operation=str(row["operation"]),
        idem_key=str(row["idem_key"]),
        request_digest=str(row["request_digest"]),
        response_status=int(row["response_status"]),
        response_json=str(row["response_json"]),
        created_at=str(row["created_at"]),
    )


def _job_of(row: RowMapping) -> JobRecord:
    lease = row["lease_until"]
    retry_of = row["retry_of"]
    result_json = row["result_json"]
    problem_json = row["problem_json"]
    return JobRecord(
        workspace_id=str(row["workspace_id"]),
        id=str(row["id"]),
        kind=str(row["kind"]),
        state=str(row["state"]),
        attempt=int(row["attempt"]),
        progress=int(row["progress"]),
        stage=str(row["stage"]),
        lease_token=None if row["lease_token"] is None else str(row["lease_token"]),
        lease_deadline=None if lease is None else str(lease),
        retry_of=None if retry_of is None else str(retry_of),
        retryable=bool(row["retryable"]),
        input_json=str(row["input_json"]),
        input_digest=str(row["input_digest"]),
        result_json=None if result_json is None else str(result_json),
        problem_json=None if problem_json is None else str(problem_json),
        revision=int(row["revision"]),
        created_at=str(row["created_at"]),
    )


def job_from_row(record: JobRecord) -> Job:
    """``jobs`` 行 → 活契约 ``Job`` DTO（design §6 指派给本文件的公开符号）。

    ``result_ref`` / ``problem`` 在表里没有独立列，分别落在 ``result_json`` /
    ``problem_json``：``result_json`` 存 ``ObjectRef`` 的 JSON 对象，``problem_json`` 存
    ``Problem`` 的 JSON 对象。两者都经 DTO 校验，解不开就报错——静默降级成 ``None``
    会让「作业成功但没有结果指针」这种坏数据混过契约面。
    """
    result_ref: ObjectRef | None = None
    if record.result_json is not None:
        payload = json.loads(record.result_json)
        if not isinstance(payload, Mapping):
            raise ValueError(f"jobs.result_json 必须是对象：job={record.id}")
        result_ref = ObjectRef(kind=payload["kind"], id=str(payload["id"]))
    problem: Problem | None = None
    if record.problem_json is not None:
        problem = Problem.model_validate(json.loads(record.problem_json))
    return Job(
        id=record.id,
        revision=record.revision,
        created_at=datetime.fromisoformat(record.created_at),
        kind=cast(JobKind, record.kind),
        state=cast(JobState, record.state),
        attempt=record.attempt,
        progress=record.progress,
        stage=record.stage,
        input_digest=record.input_digest,
        retry_of=record.retry_of,
        result_ref=result_ref,
        problem=problem,
        retryable=record.retryable,
    )


# ------------------------------------------------------------------------------------- workspaces


class WorkspaceRepository:
    """``workspaces`` 表读写（listWorkspaces 读、createWorkspace 写）。"""

    def insert(self, conn: Connection, *, workspace: Workspace) -> None:
        conn.execute(
            text(
                "INSERT INTO workspaces "
                "(id, name, source_class, authorization_note, revision, created_at) "
                "VALUES (:id, :name, :source_class, :authorization_note, :revision, :created_at)"
            ),
            {
                "id": workspace.id,
                "name": workspace.name,
                "source_class": workspace.source_class,
                "authorization_note": workspace.authorization_note,
                "revision": workspace.revision,
                "created_at": _iso(workspace.created_at),
            },
        )

    def get(self, conn: Connection, workspace_id: str) -> Workspace | None:
        row = (
            conn.execute(
                text(f"SELECT {_WORKSPACE_COLUMNS} FROM workspaces WHERE id = :id"),
                {"id": workspace_id},
            )
            .mappings()
            .first()
        )
        return None if row is None else _workspace_of(row)

    def list_page(
        self,
        conn: Connection,
        *,
        limit: int,
        after: tuple[str, str] | None = None,
        q: str | None = None,
    ) -> list[Workspace]:
        """取一页（最多 ``limit`` 行）。``after`` 是上一页末行的 ``(created_at, id)``。

        ``q`` 非空时**不**下推 SQL LIMIT：过滤发生在 Python 侧，先 LIMIT 会 cutting 掉
        本应命中的后续行，翻页就会漏数据。改为流式迭代并凑满即停。
        """
        if limit < 1:
            raise ValueError(f"limit 必须 >= 1：{limit}")
        sql = f"SELECT {_WORKSPACE_COLUMNS} FROM workspaces"
        params: dict[str, Any] = {}
        if after is not None:
            sql += " WHERE created_at < :k0 OR (created_at = :k0 AND id > :k1)"
            params["k0"], params["k1"] = after
        sql += " ORDER BY created_at DESC, id ASC"
        needle = _fold(q) if q else None
        if needle is None:
            sql += " LIMIT :limit"
            params["limit"] = limit
        rows: Iterator[RowMapping] = iter(conn.execute(text(sql), params).mappings())
        page: list[Workspace] = []
        for row in rows:
            if needle is not None and needle not in _fold(str(row["name"])):
                continue
            page.append(_workspace_of(row))
            if len(page) >= limit:
                break
        return page


# -------------------------------------------------------------------------------------- artifacts


class ArtifactRepository:
    """``artifacts`` 表读写。M0-02 无 HTTP 面，为 M1 的导入落制品预置（design §3）。"""

    def insert(self, conn: Connection, *, artifact: ArtifactRecord) -> None:
        conn.execute(
            text(
                "INSERT INTO artifacts "
                "(workspace_id, id, kind, sha256, relative_path, byte_size, created_at) "
                "VALUES (:workspace_id, :id, :kind, :sha256, :relative_path, "
                ":byte_size, :created_at)"
            ),
            {
                "workspace_id": artifact.workspace_id,
                "id": artifact.id,
                "kind": artifact.kind,
                "sha256": artifact.sha256,
                "relative_path": artifact.relative_path,
                "byte_size": artifact.byte_size,
                "created_at": artifact.created_at,
            },
        )

    def get(
        self, conn: Connection, *, workspace_id: str, artifact_id: str
    ) -> ArtifactRecord | None:
        row = (
            conn.execute(
                text(
                    "SELECT workspace_id, id, kind, sha256, relative_path, byte_size, created_at "
                    "FROM artifacts WHERE workspace_id = :workspace_id AND id = :id"
                ),
                {"workspace_id": workspace_id, "id": artifact_id},
            )
            .mappings()
            .first()
        )
        return None if row is None else _artifact_of(row)

    def list_for_workspace(self, conn: Connection, workspace_id: str) -> list[ArtifactRecord]:
        rows = conn.execute(
            text(
                "SELECT workspace_id, id, kind, sha256, relative_path, byte_size, created_at "
                "FROM artifacts WHERE workspace_id = :workspace_id ORDER BY created_at, id"
            ),
            {"workspace_id": workspace_id},
        ).mappings()
        return [_artifact_of(row) for row in rows]


# ------------------------------------------------------------------------------------------- jobs


class JobRepository:
    """``jobs`` 表的唯一写入口（任务卡 A12/N5 的 *JobStore*）。

    **本类只实现 M0-02 需要的面**：入队、按主键读、取就绪队列、写租约。
    作业终态转换（SUCCEEDED / FAILED / CANCELLED）属 M0-04：本里程碑没有任何已注册的
    作业 kind，也没有 HTTP 作业面，先建终态写路径只会成为没人校验的死代码。
    """

    def insert(self, conn: Connection, *, job: JobRecord) -> None:
        """入队一条 QUEUED 作业。

        刻意只写 13 个非空列：DDL 的 CHECK 要求「非 RUNNING/CANCEL_REQUESTED 时
        ``lease_token`` 与 ``lease_until`` 皆 NULL」「非 SUCCEEDED 时 ``result_json`` 为 NULL」，
        省略这些列即落 NULL 默认值，同时也保证本文件除 ``touch_lease`` 外不再出现
        ``lease_until`` 字样（A11 的机器可查面）。
        """
        if job.state != "QUEUED":
            raise ValueError(f"JobRepository.insert 只接受 QUEUED 作业：state={job.state}")
        if job.lease_token is not None or job.lease_deadline is not None:
            raise ValueError("QUEUED 作业不得带租约（DDL CHECK 会拒绝）")
        if job.result_json is not None or job.problem_json is not None:
            raise ValueError("QUEUED 作业不得带 result_json / problem_json（DDL CHECK 会拒绝）")
        conn.execute(
            text(
                "INSERT INTO jobs "
                "(workspace_id, id, kind, state, attempt, progress, stage, retry_of, retryable, "
                "input_json, input_digest, revision, created_at) "
                "VALUES (:workspace_id, :id, :kind, :state, :attempt, :progress, :stage, "
                ":retry_of, :retryable, :input_json, :input_digest, :revision, :created_at)"
            ),
            {
                "workspace_id": job.workspace_id,
                "id": job.id,
                "kind": job.kind,
                "state": job.state,
                "attempt": job.attempt,
                "progress": job.progress,
                "stage": job.stage,
                "retry_of": job.retry_of,
                "retryable": int(job.retryable),
                "input_json": job.input_json,
                "input_digest": job.input_digest,
                "revision": job.revision,
                "created_at": job.created_at,
            },
        )

    def get(self, conn: Connection, *, workspace_id: str, job_id: str) -> JobRecord | None:
        row = (
            conn.execute(
                text(f"SELECT {_JOB_COLUMNS} FROM jobs WHERE workspace_id = :ws AND id = :id"),
                {"ws": workspace_id, "id": job_id},
            )
            .mappings()
            .first()
        )
        return None if row is None else _job_of(row)

    def list_ready(self, conn: Connection, *, limit: int) -> list[JobRecord]:
        """就绪队列：``state='QUEUED'`` 按 ``created_at, workspace_id, id`` 取前 ``limit`` 条。

        列序对齐显式索引 ``jobs_ready(state, created_at, workspace_id, id)``，
        因此这是一次索引顺扫而不是全表排序。
        """
        if limit < 1:
            raise ValueError(f"limit 必须 >= 1：{limit}")
        rows = conn.execute(
            text(
                f"SELECT {_JOB_COLUMNS} FROM jobs WHERE state = 'QUEUED' "
                "ORDER BY created_at, workspace_id, id LIMIT :limit"
            ),
            {"limit": limit},
        ).mappings()
        return [_job_of(row) for row in rows]

    def touch_lease(
        self, conn: Connection, *, job_id: str, lease_token: str, lease_deadline: str
    ) -> int:
        """写入租约（**全仓唯一**的 ``jobs.lease_until`` 写语句，A11）。

        一条语句同时覆盖「首次取得租约」与「续约」：QUEUED → RUNNING 并 ``attempt+1``；
        已 RUNNING/CANCEL_REQUESTED 且租约属于本 worker → 只推迟期限。
        ``lease_token IS NULL OR lease_token = :lease_token`` 是抢占保护：别的 worker
        持有的作业不会被本 worker 悄悄改期（返回 0 行）。

        ``lease_deadline`` 的值一律由 ``application/worker.py::heartbeat`` 从注入时钟算出，
        本方法不接受调用方以外的第二个来源。
        """
        result = conn.execute(
            text(
                "UPDATE jobs SET "
                "state = CASE WHEN state = 'QUEUED' THEN 'RUNNING' ELSE state END, "
                "attempt = attempt + CASE WHEN state = 'QUEUED' THEN 1 ELSE 0 END, "
                "lease_token = :lease_token, "
                "lease_until = :lease_deadline, "
                "revision = revision + 1 "
                "WHERE id = :id AND state IN ('QUEUED', 'RUNNING', 'CANCEL_REQUESTED') "
                "AND (lease_token IS NULL OR lease_token = :lease_token)"
            ),
            {"lease_token": lease_token, "lease_deadline": lease_deadline, "id": job_id},
        )
        return int(result.rowcount or 0)


# ------------------------------------------------------------------------------------ idempotency


class IdempotencyRepository:
    """``idempotency`` 表读写。并发正确性靠主键唯一，不靠「先查后插」（design §2）。"""

    def fetch(
        self, conn: Connection, *, scope_key: str, actor_id: str, operation: str, idem_key: str
    ) -> IdempotencyRecord | None:
        row = (
            conn.execute(
                text(
                    "SELECT scope_key, actor_id, operation, idem_key, request_digest, "
                    "response_status, response_json, created_at FROM idempotency "
                    "WHERE scope_key = :scope_key AND actor_id = :actor_id "
                    "AND operation = :operation AND idem_key = :idem_key"
                ),
                {
                    "scope_key": scope_key,
                    "actor_id": actor_id,
                    "operation": operation,
                    "idem_key": idem_key,
                },
            )
            .mappings()
            .first()
        )
        return None if row is None else _idempotency_of(row)

    def insert(self, conn: Connection, *, record: IdempotencyRecord) -> bool:
        """登记一行。返回 ``True``＝本次插入成功；``False``＝主键已被并发请求占用。

        用 ``ON CONFLICT DO NOTHING`` 而不是捕获 ``IntegrityError``：后者会把当前事务
        推进「需要 rollback」的状态，而幂等冲突是**预期路径**，不该用异常表达。
        """
        result = conn.execute(
            text(
                "INSERT INTO idempotency "
                "(scope_key, actor_id, operation, idem_key, request_digest, "
                "response_status, response_json, created_at) "
                "VALUES (:scope_key, :actor_id, :operation, :idem_key, :request_digest, "
                ":response_status, :response_json, :created_at) "
                "ON CONFLICT(scope_key, actor_id, operation, idem_key) DO NOTHING"
            ),
            {
                "scope_key": record.scope_key,
                "actor_id": record.actor_id,
                "operation": record.operation,
                "idem_key": record.idem_key,
                "request_digest": record.request_digest,
                "response_status": record.response_status,
                "response_json": record.response_json,
                "created_at": record.created_at,
            },
        )
        return int(result.rowcount or 0) == 1


# ------------------------------------------------------------------------------------------ audit


class AuditRepository:
    """``audit`` 表写入侧。

    **读入口（``listAudit``）属 M4-02**（裁定 A15），本文件不提供列表查询——
    提前实现会和 M4-02 的分页／过滤口径打架，成为第二份定义。
    """

    def next_sequence(self, conn: Connection, workspace_id: str) -> int:
        row = conn.execute(
            text(
                "SELECT coalesce(max(sequence), 0) + 1 AS next_seq FROM audit "
                "WHERE workspace_id = :workspace_id"
            ),
            {"workspace_id": workspace_id},
        ).one()
        return int(row[0])

    def last_digest(self, conn: Connection, workspace_id: str) -> str | None:
        """该工作区审计链的上一枚摘要（``previous_digest`` 的来源）。"""
        row = (
            conn.execute(
                text(
                    "SELECT digest FROM audit WHERE workspace_id = :workspace_id "
                    "ORDER BY sequence DESC LIMIT 1"
                ),
                {"workspace_id": workspace_id},
            )
            .scalars()
            .first()
        )
        return None if row is None else str(row)

    def insert(self, conn: Connection, *, record: AuditRecord) -> None:
        conn.execute(
            text(
                "INSERT INTO audit "
                "(workspace_id, sequence, id, at, actor_id, role, action, target_kind, "
                "target_id, outcome, request_id, previous_digest, digest) "
                "VALUES (:workspace_id, :sequence, :id, :at, :actor_id, :role, :action, "
                ":target_kind, :target_id, :outcome, :request_id, :previous_digest, :digest)"
            ),
            {
                "workspace_id": record.workspace_id,
                "sequence": record.sequence,
                "id": record.id,
                "at": record.at,
                "actor_id": record.actor_id,
                "role": record.role,
                "action": record.action,
                "target_kind": record.target_kind,
                "target_id": record.target_id,
                "outcome": record.outcome,
                "request_id": record.request_id,
                "previous_digest": record.previous_digest,
                "digest": record.digest,
            },
        )
