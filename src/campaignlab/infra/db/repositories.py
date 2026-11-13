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

    # ------------------------------------------------------------------ M0-04/S2（A82 纯追加）
    #
    # 以下是 A82 给 M0-04/S2 的**窄口径 append-only 豁免**落点：只新增方法。既有 4 个方法
    # （``insert`` / ``get`` / ``list_ready`` / ``touch_lease``）的签名、函数体与 SQL 文本
    # 一字未改，``job_from_row``、5 个 Record dataclass、其余 4 个 Repository 类同样未动，
    # 故 ``git diff --numstat`` 对本文件恒为「N add / 0 del」。
    #
    # 三条不随方法数量增加的口径：
    #
    # 1. **只接受绑定参数**——``lease_deadline`` 一律由调用方从
    #    ``application/worker.py::compute_lease_deadline`` 取来（A83 修订后的 A70 判据①），
    #    本文件任何方法都不算时间、不出现 ``timedelta``；``now`` 也只以 ISO-8601 文本形态
    #    作绑定参数进来，与同为 ISO 文本的 ``lease_until`` 做字典序比较（同 ``created_at``
    #    的既有口径，见模块 docstring 第 3 条）。
    # 2. **谓词 UPDATE**——每条状态写都是**单条**带 WHERE 谓词的 UPDATE，``rowcount`` 即
    #    真值：worker 侧谓词含 ``attempt`` 与 ``lease_token``，操作员侧谓词含 ``revision``。
    #    ``rowcount == 0`` 表示守卫不成立（租约失效／已终态／revision 过期），由调用方翻译
    #    成领域错。**禁** SELECT-then-UPDATE 的无谓词写法：``BEGIN IMMEDIATE`` 串行化写者
    #    ＋谓词 UPDATE 使败者 ``rowcount = 0``，是并发正确性的唯一机器保证（design §4）。
    # 3. **终态唯一**——T1–T8 的前态集合**均不含** ``SUCCEEDED`` / ``FAILED`` /
    #    ``CANCELLED``，故终态行的任何后续 UPDATE 恒 ``rowcount == 0``。这就是 JOBS.md:23
    #    「若取消与完成争用，先成功提交的合法状态决定结果」的实现：败者改不动那一行，
    #    也就覆写不了别人已提交的终态。
    #
    # ``lease_until`` 的**写语句**因此从 1 条变成 3 条（``touch_lease`` / ``claim_next`` /
    # ``renew``），但 A70 判据②钉的是「SQL 层写点唯一在 ``infra/db/repositories.py``、
    # 只接受绑定参数」——文件与口径都没变；判据③（``touch_lease`` 的唯一调用方是
    # ``WorkerSupervisor.heartbeat``）也未受影响，本文件的 M0-04 方法一个都不调它。

    def claim_next(
        self,
        conn: Connection,
        *,
        workspace_id: str,
        lease_token: str,
        lease_deadline: str,
        stage: str,
    ) -> JobRecord | None:
        """T1 ``QUEUED -> RUNNING``：认领**事务内最早可认领**的一条作业（JOBS.md:11）。

        两步都跑在调用方已开好的 ``BEGIN IMMEDIATE`` 短事务里（design §4 TX1）：先按显式
        索引 ``jobs_ready(state, created_at, workspace_id, id)`` 顺扫取出最早的一条 QUEUED，
        再发一条带 ``state`` ＋ ``revision`` 双谓词的 UPDATE。于是「两个执行者争用同一
        作业」只有一个 ``rowcount == 1``：败者要么在 ``BEGIN IMMEDIATE`` 处被写锁挡住
        （``OperationalError``），要么在胜者提交后读到 ``state`` 已非 QUEUED —— 两者都不
        会留下半状态（AC-029「两次尝试争抢同一作业时只有有效租约可发布」）。

        返回认领后的整行（``state == 'RUNNING'``、``attempt`` 已 +1、租约双列已写）；队列
        为空或被别人抢先时返回 ``None`` 而**不抛异常**：worker 侧把「这一轮没拿到活」当
        正常情况处理，与 ``WorkerSupervisor.heartbeat`` 返回 ``False`` 同一语义。
        """
        head = (
            conn.execute(
                text(
                    "SELECT workspace_id, id, revision FROM jobs "
                    "WHERE state = 'QUEUED' AND workspace_id = :ws "
                    "ORDER BY created_at, workspace_id, id LIMIT 1"
                ),
                {"ws": workspace_id},
            )
            .mappings()
            .first()
        )
        if head is None:
            return None
        head_id = str(head["id"])
        touched = conn.execute(
            text(
                "UPDATE jobs SET "
                "state = 'RUNNING', "
                "attempt = attempt + 1, "
                "lease_token = :lease_token, "
                "lease_until = :lease_deadline, "
                "stage = :stage, "
                "progress = 0, "
                "revision = revision + 1 "
                "WHERE workspace_id = :ws AND id = :id "
                "AND state = 'QUEUED' AND revision = :revision"
            ),
            {
                "lease_token": lease_token,
                "lease_deadline": lease_deadline,
                "stage": stage,
                "ws": workspace_id,
                "id": head_id,
                "revision": int(head["revision"]),
            },
        )
        if int(touched.rowcount or 0) != 1:
            return None
        return self.get(conn, workspace_id=workspace_id, job_id=head_id)

    def renew(
        self,
        conn: Connection,
        *,
        workspace_id: str,
        job_id: str,
        attempt: int,
        lease_token: str,
        lease_deadline: str,
        stage: str,
        progress: int,
    ) -> JobRecord | None:
        """T3 ``RUNNING -> RUNNING``：续租并写阶段进度（JOBS.md:13，design §4 TX2）。

        谓词是 ``attempt`` ＋ ``lease_token`` ＋ ``state IN ('RUNNING','CANCEL_REQUESTED')``：
        attempt 不匹配（作业已被别人重认领）或 token 不匹配（租约已易主）都得到
        ``rowcount == 0``，即 JOBS.md:21「完成和续租均匹配工作区、作业、attempt 和
        lease token」与 AC-029「失效租约不能提交」的落点。前态含 ``CANCEL_REQUESTED``
        是刻意的：取消请求不该剥夺执行进程的续租能力，否则它会被 T7 误判为中断。

        返回续租后的整行，调用方据其 ``state`` 判断是否已被请求取消（design §4 末条
        「TX2 续租顺带回读 ``state``」）；守卫不成立时返回 ``None``，由调用方抛
        ``LeaseLost`` 并**不改任何字段**。
        """
        touched = conn.execute(
            text(
                "UPDATE jobs SET "
                "lease_until = :lease_deadline, "
                "stage = :stage, "
                "progress = :progress, "
                "revision = revision + 1 "
                "WHERE workspace_id = :ws AND id = :id "
                "AND attempt = :attempt AND lease_token = :lease_token "
                "AND state IN ('RUNNING', 'CANCEL_REQUESTED')"
            ),
            {
                "lease_deadline": lease_deadline,
                "stage": stage,
                "progress": progress,
                "ws": workspace_id,
                "id": job_id,
                "attempt": attempt,
                "lease_token": lease_token,
            },
        )
        if int(touched.rowcount or 0) != 1:
            return None
        return self.get(conn, workspace_id=workspace_id, job_id=job_id)

    def request_cancel(
        self, conn: Connection, *, workspace_id: str, job_id: str, revision: int
    ) -> int:
        """T2 ``QUEUED -> CANCELLED`` 与 T4 ``RUNNING -> CANCEL_REQUESTED`` 的共用谓词写。

        JOBS.md 把「请求取消」按前态分成两行（:12 排队中直接落终态、:14 运行中先置
        ``CANCEL_REQUESTED`` 等执行进程在安全分段确认），但两者是**同一条**带 ``revision``
        谓词的 UPDATE：一个事务里发两条语句，等于给「先提交者定终态」凭空造出第二个
        竞争者。故用 ``CASE`` 按**旧** ``state`` 分派（SQLite 的 SET 右值一律取行原值）：

        - 旧 ``QUEUED`` → ``CANCELLED``；租约双列本就是 NULL（DDL CHECK 要求），
          ``retryable`` 置 1（design §3 T2）。
        - 旧 ``RUNNING`` → ``CANCEL_REQUESTED``；**保留** ``lease_token`` / ``lease_until``
          ——DDL 那条 CHECK 是**双条件式**：state 属 RUNNING/CANCEL_REQUESTED **当且仅当**
          租约双列非空，此处置 NULL 会直接违约；``retryable`` 不动，等 T8 收口。

        谓词 ``revision = :revision`` 承接 ``If-Match``（design §6：不符 → 412
        ``REVISION_CONFLICT``）。前态集合不含任何终态、也不含 ``CANCEL_REQUESTED``，故对
        已终态或已请求过取消的作业 ``rowcount == 0`` → 409 ``STATE_CONFLICT``。
        """
        result = conn.execute(
            text(
                "UPDATE jobs SET "
                "state = CASE WHEN state = 'QUEUED' THEN 'CANCELLED' "
                "ELSE 'CANCEL_REQUESTED' END, "
                "lease_token = CASE WHEN state = 'QUEUED' THEN NULL ELSE lease_token END, "
                "lease_until = CASE WHEN state = 'QUEUED' THEN NULL ELSE lease_until END, "
                "retryable = CASE WHEN state = 'QUEUED' THEN 1 ELSE retryable END, "
                "revision = revision + 1 "
                "WHERE workspace_id = :ws AND id = :id AND revision = :revision "
                "AND state IN ('QUEUED', 'RUNNING')"
            ),
            {"ws": workspace_id, "id": job_id, "revision": revision},
        )
        return int(result.rowcount or 0)

    def confirm_cancel(
        self, conn: Connection, *, workspace_id: str, job_id: str, attempt: int, lease_token: str
    ) -> int:
        """T8 的**执行确认**入口：``CANCEL_REQUESTED -> CANCELLED``（JOBS.md:18）。

        JOBS.md:18 给的是「执行确认**或**租约到期」两条入口、同一终态：本方法是前者
        （执行进程在安全分段读到取消信号后主动收口，走 design §4 TX4，谓词含 ``attempt``
        与 ``lease_token``），后者是 ``cancel_expired_requested``（走 TX7 恢复扫描）。两条
        入口的前态都只有 ``CANCEL_REQUESTED``，因此谁先提交谁定终态，败者 ``rowcount == 0``。

        **保留原输入**：``input_json`` / ``input_digest`` / ``kind`` 一字不动（design §3 T8），
        重试才能拿同一输入快照再跑一遍；``result_json`` / ``problem_json`` 置 NULL ——
        取消不是失败，不该带 Problem；DDL 的双条件 CHECK 也要求非 SUCCEEDED 时
        ``result_json`` 为 NULL。租约双列同步置 NULL 以满足该 CHECK 的另一半。
        """
        result = conn.execute(
            text(
                "UPDATE jobs SET "
                "state = 'CANCELLED', "
                "result_json = NULL, "
                "problem_json = NULL, "
                "retryable = 1, "
                "lease_token = NULL, "
                "lease_until = NULL, "
                "revision = revision + 1 "
                "WHERE workspace_id = :ws AND id = :id "
                "AND attempt = :attempt AND lease_token = :lease_token "
                "AND state = 'CANCEL_REQUESTED'"
            ),
            {"ws": workspace_id, "id": job_id, "attempt": attempt, "lease_token": lease_token},
        )
        return int(result.rowcount or 0)

    def mark_succeeded(
        self,
        conn: Connection,
        *,
        workspace_id: str,
        job_id: str,
        attempt: int,
        lease_token: str,
        result_json: str,
    ) -> int:
        """T5 ``RUNNING -> SUCCEEDED``：成功且租约仍有效（JOBS.md:15，design §4 TX5）。

        谓词 ``attempt`` ＋ ``lease_token`` ＋ ``state IN ('RUNNING','CANCEL_REQUESTED')``。
        前态**含** ``CANCEL_REQUESTED`` 是 JOBS.md:23「若取消与完成争用，先成功提交的合法
        状态决定结果」的正面实现：TX4（``confirm_cancel``）与 TX5 的前态集合相交，谁先
        ``COMMIT`` 谁定终态，败者 ``rowcount == 0`` → 不得覆写、不得重试成第二终态。

        ``result_json`` 存 ``ObjectRef`` 的 JSON 对象（A73 的映射口径），DDL 的双条件 CHECK
        ``(state='SUCCEEDED') = (result_json IS NOT NULL)`` 保证「成功必有结果指针」，故空串
        直接拒；``problem_json`` 置 NULL（成功作业不带 Problem）。制品行的同事务登记由
        调用方（``worker/store.py``）用 ``ArtifactRepository.insert`` 完成——本方法只管
        ``jobs`` 一张表，A81 要求 SQL 写点收敛在这里，不要求它跨表。
        """
        if not result_json:
            raise ValueError(
                "mark_succeeded 需要非空 result_json（DDL CHECK 要求 SUCCEEDED 必有结果）"
            )
        result = conn.execute(
            text(
                "UPDATE jobs SET "
                "state = 'SUCCEEDED', "
                "result_json = :result_json, "
                "problem_json = NULL, "
                "progress = 100, "
                "retryable = 0, "
                "lease_token = NULL, "
                "lease_until = NULL, "
                "revision = revision + 1 "
                "WHERE workspace_id = :ws AND id = :id "
                "AND attempt = :attempt AND lease_token = :lease_token "
                "AND state IN ('RUNNING', 'CANCEL_REQUESTED')"
            ),
            {
                "result_json": result_json,
                "ws": workspace_id,
                "id": job_id,
                "attempt": attempt,
                "lease_token": lease_token,
            },
        )
        return int(result.rowcount or 0)

    def mark_failed(
        self,
        conn: Connection,
        *,
        workspace_id: str,
        job_id: str,
        attempt: int,
        lease_token: str,
        problem_json: str,
        retryable: bool,
    ) -> int:
        """T6 ``RUNNING -> FAILED``：已知失败（JOBS.md:16，design §4 TX6）。

        守卫与 T5 逐字相同（含 ``CANCEL_REQUESTED``），故失败与取消争用时同样是先提交者
        定终态。``problem_json`` 存 ``Problem`` 的 JSON 对象（A73），**保留错误码**；
        ``stage`` 与 ``progress`` 刻意**不写**——JOBS.md:16 要求「保留错误码、阶段」，
        失败发生在哪个阶段本身就是诊断证据，抹成 0 会让页面看不出死在哪一步。

        ``result_json`` 置 NULL（DDL 双条件 CHECK：非 SUCCEEDED 不得有结果）；
        ``retryable`` 由调用方按 design §3 的口径算好传进来（``worker/states.py::
        retryable_for``），本方法不内置业务判断；租约双列置 NULL。
        """
        if not problem_json:
            raise ValueError("mark_failed 需要非空 problem_json（JOBS.md:16 要求保留错误码）")
        result = conn.execute(
            text(
                "UPDATE jobs SET "
                "state = 'FAILED', "
                "problem_json = :problem_json, "
                "result_json = NULL, "
                "retryable = :retryable, "
                "lease_token = NULL, "
                "lease_until = NULL, "
                "revision = revision + 1 "
                "WHERE workspace_id = :ws AND id = :id "
                "AND attempt = :attempt AND lease_token = :lease_token "
                "AND state IN ('RUNNING', 'CANCEL_REQUESTED')"
            ),
            {
                "problem_json": problem_json,
                "retryable": int(retryable),
                "ws": workspace_id,
                "id": job_id,
                "attempt": attempt,
                "lease_token": lease_token,
            },
        )
        return int(result.rowcount or 0)

    def fail_expired_running(self, conn: Connection, *, now: str, problem_json: str) -> int:
        """T7 ``RUNNING -> FAILED``：租约超时且证据未提交（JOBS.md:17，design §4 TX7）。

        这是**系统行为者**的迁移，故谓词里刻意**没有** ``lease_token``：中断的 worker 已经
        死了，没人能出示 token；能用「租约已过期」当唯一守卫，正是因为过期本身就证明
        原持有者失去了发布权（JOBS.md:21「只有有效租约可发布」的 contrapositive）。

        ``now`` 是 ISO-8601 文本绑定参数，与同为 ISO 文本的 ``lease_until`` 做字典序比较
        （同格式字符串的字典序即时序）。**绝不触碰** ``SUCCEEDED`` / ``FAILED`` /
        ``CANCELLED`` / ``QUEUED``：前态集合只有 ``RUNNING``，即 JOBS.md:23「不重写已成功
        作业」。``retryable`` 恒 1 —— 中断是可重试的原型场景（AC-029「中断后可重试」）。
        """
        result = conn.execute(
            text(
                "UPDATE jobs SET "
                "state = 'FAILED', "
                "problem_json = :problem_json, "
                "result_json = NULL, "
                "retryable = 1, "
                "lease_token = NULL, "
                "lease_until = NULL, "
                "revision = revision + 1 "
                "WHERE state = 'RUNNING' AND lease_until < :now"
            ),
            {"problem_json": problem_json, "now": now},
        )
        return int(result.rowcount or 0)

    def cancel_expired_requested(self, conn: Connection, *, now: str) -> int:
        """T8 的**租约到期**入口：``CANCEL_REQUESTED -> CANCELLED``（JOBS.md:18，TX7）。

        与 ``confirm_cancel`` 同一终态、不同守卫：那条要 ``attempt`` ＋ ``lease_token``
        （执行者自证身份），这条只要 ``lease_until < :now``（执行者已失联，系统代为收口）。
        JOBS.md:18 的「执行确认**或**租约到期」由此两条 UPDATE 承担，前态都只有
        ``CANCEL_REQUESTED``，先提交者定终态。

        ``stage`` / ``progress`` 保留（诊断证据），``input_json`` / ``input_digest`` / ``kind``
        一字不改（design §3 T8「保留原输入」），``result_json`` / ``problem_json`` 置 NULL
        （取消不是失败），``retryable`` 置 1（design §3：``CANCELLED`` → 1），租约双列置
        NULL 以满足 DDL 的双条件 CHECK。
        """
        result = conn.execute(
            text(
                "UPDATE jobs SET "
                "state = 'CANCELLED', "
                "result_json = NULL, "
                "problem_json = NULL, "
                "retryable = 1, "
                "lease_token = NULL, "
                "lease_until = NULL, "
                "revision = revision + 1 "
                "WHERE state = 'CANCEL_REQUESTED' AND lease_until < :now"
            ),
            {"now": now},
        )
        return int(result.rowcount or 0)

    def enqueue_retry(
        self,
        conn: Connection,
        *,
        workspace_id: str,
        source_job_id: str,
        source_revision: int,
        new_job: JobRecord,
    ) -> int:
        """T9 ``FAILED``／``CANCELLED`` → **新** QUEUED 作业（JOBS.md:19，design §4 TX8）。

        重试不是把原作业改回 QUEUED，而是**新建一行**：``new_job.id`` 是新资源 ID、
        ``retry_of`` 指向源作业、``attempt`` 从 0 重新起算，**源作业的终态一字不变**
        （只 ``revision + 1``，让客户端的 ``If-Match`` 失效、被迫重读）。这样「终态唯一」
        与「重试得到一次可见结果」（AC-029）才能同时成立：历史终态是可回查的证据，
        不会被重试抹掉。

        两步同一事务：先对源作业发带 ``state IN ('FAILED','CANCELLED')`` ＋ ``revision``
        双谓词的 UPDATE，``rowcount != 1`` 即返回 0（源作业还在跑、已成功、或 revision
        过期），**一行都不插**；成功后调用 ``self.insert`` 落新行 —— 刻意复用既有
        ``insert`` 而不自己写一条插入语句：A81／FU-10 要求 ``jobs`` 的插入落点唯一，
        本方法因此不含任何插入 SQL 文本。
        """
        if new_job.workspace_id != workspace_id:
            raise ValueError("enqueue_retry 的新作业必须与源作业同工作区（FK 是复合键）")
        if new_job.retry_of != source_job_id:
            raise ValueError(f"new_job.retry_of 必须指向源作业：{new_job.retry_of!r}")
        bumped = conn.execute(
            text(
                "UPDATE jobs SET revision = revision + 1 "
                "WHERE workspace_id = :ws AND id = :id AND revision = :revision "
                "AND state IN ('FAILED', 'CANCELLED')"
            ),
            {"ws": workspace_id, "id": source_job_id, "revision": source_revision},
        )
        if int(bumped.rowcount or 0) != 1:
            return 0
        self.insert(conn, job=new_job)
        return 1

    def count_pending(self, conn: Connection, *, workspace_id: str, states: tuple[str, ...]) -> int:
        """统计某工作区处于 ``states`` 的作业数（``JOB_CAPACITY`` 闸的读数，A88②）。

        ``states`` 由 ``worker/capacity.py::pending_states()`` 给出，取**非终态**三值
        ``QUEUED|RUNNING|CANCEL_REQUESTED``（JOBS.md:7「默认工作区最多 10 个待办」）。
        只读、不开事务、不改任何行。

        IN 列表的占位符按 ``len(states)`` 现拼，但拼进去的只有 ``:s0``／``:s1`` 这类
        **由整数生成**的参数名，状态值本身一律走绑定参数 —— SQL 文本里不出现任何调用方
        数据，故没有注入面。
        """
        if not states:
            raise ValueError("count_pending 的 states 不得为空（空集合会让 IN () 语法错）")
        marks = ", ".join(":s" + str(index) for index in range(len(states)))
        params: dict[str, Any] = {"ws": workspace_id}
        for index, state in enumerate(states):
            params["s" + str(index)] = state
        total = conn.execute(
            text("SELECT COUNT(*) FROM jobs WHERE workspace_id = :ws AND state IN (" + marks + ")"),
            params,
        ).scalar()
        return int(total or 0)


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
