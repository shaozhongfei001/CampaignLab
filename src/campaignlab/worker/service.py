"""``campaignlab.worker.service``：jobs 的用例服务面（M0-04/S2c · A169）。

design §9 只给本文件指派一个符号：``JobService``，方法面恰为 ``list_jobs`` / ``get_job`` /
``cancel_job`` / ``retry_job``（禁增减、禁改名）。五条落地口径，每条都有守护用例
（``tests/unit/test_worker_service.py``）：

1. **事务边界不在本层**（design §9：``JobStore`` 才是事务边界）：本模块不持有 ``Engine``、
   不开连接、不含一条 SQL 文本，四个方法一律转发 ``JobStore``。故 A206 要求构造参数就叫
   ``store`` —— ``worker/deps.py::get_job_service`` 已按 ``factory(store=...)`` 装配，换个
   名字装配当场断裂。本文件落地的同一次工作里删掉了 ``deps.py:55`` 那条
   ``# type: ignore[import-not-found]``（A207：strict 开着 ``warn_unused_ignores``，
   模块一旦出现，留着那条 ignore 会让全表 mypy 判红）。
2. **不组装 HTTP 分页壳**（A169④ / A91）：``list_jobs`` 返回
   ``(JobRecord 列表, 下一页游标载荷 | None)`` 这个**裸二元组**。契约面的 ``JobPage`` 归
   M0-04/S4 在 ``api/common.py`` append-only 追加，S2c 禁抢先落地（避免双主写）。同理，
   行→DTO 的 ``infra.db.repositories.job_from_row`` **不在本层调用**：它是
   ``JobRecord -> api.common.Job`` 的契约映射，调用点在 S4；A169① 落在本层的实际义务是
   「**禁复制第二份**」，故本文件一个转换器都没有（守护按 AST 钉住）。
3. **游标禁另发明**（A169③）：``CURSOR_VERSION`` 与 ``BAD_CURSOR_DETAIL`` 直接 import
   ``application/workspace_service.py`` 的那一份 —— design §1 明写 listJobs 与
   listWorkspaces「复用同一份冻结游标实现」，本文件不写第二个版本号、不写第二句 detail。
   **但编解码不在本层**：``encode_cursor`` / ``decode_cursor`` / ``canonical_json`` 都住在
   ``api/common.py``，而本 lane 的硬约束是 ``service.py`` 不得新增 ``worker -> api`` 导入边，
   故 ``list_jobs`` 收发的是**未编码的游标载荷**（与 ``encode_cursor`` 的入参
   ``payload: Mapping[str, Any]`` 同形状），查询摘要由调用方算好经 ``query_digest`` 传入，
   ``str <-> payload`` 的两端归 S4。载荷的**绑定校验**留在本层：只有本层同时握有本次请求的
   ``limit`` / ``q`` / ``status`` / ``actor_id``，S4 无法代劳；任一项不符即 400
   ``BAD_CURSOR``，且**四句 detail 完全相同**（游标是不可信外部输入，措辞差异会变成探测
   其结构的 oracle）。
4. **只返回领域/DTO 层结果**：``get_job`` 回 ``JobRecord | None``，``cancel_job`` /
   ``retry_job`` 回 ``JobRecord``，与 ``JobStore`` 逐字同形；ETag、状态码、响应体、
   幂等信封一律归 S4。
5. **显式时钟**（``worker/__init__.py`` 红线 3）：``cancel_job`` / ``retry_job`` 的 ``now``
   是**必填**关键字参数，由调用方从 ``Clock`` 取；本模块不 import ``time``、不出现
   ``datetime`` 模块的 now 工厂之类取系统当前时间的调用。
   ⚠ 该守护（``tests/unit/test_clock.py``）是**按源文本正则**逐行扫描 ``src/`` 的，不是 AST ——
   故连**本 docstring 里出现那个字面量都会判红**（D-045 实测踩过）。此处刻意以描述代替字面量。

分层：``worker -> application`` / ``worker -> infra`` / ``worker -> domain`` 都是既有正向边
（``store.py`` 同体例）。本模块 ``worker -> api`` 的导入边数为 **0**，由
``test_worker_service.py`` 的 AST 守护钉住（口径照抄 ``test_layering_edges.py``）。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from campaignlab.application.workspace_service import BAD_CURSOR_DETAIL, CURSOR_VERSION
from campaignlab.domain.errors import DomainError
from campaignlab.infra.db.repositories import JobRecord
from campaignlab.worker.states import JOB_STATES
from campaignlab.worker.store import DEFAULT_AUDIT_ROLE, JobStore

__all__ = ["JobService"]


class JobService:
    """jobs 的用例服务（design §9 ``worker/service.py:JobService``）。

    结构化满足 ``worker/deps.py::get_job_service`` 的装配契约：构造只吃 ``store=``。
    刻意**不**经 ``worker/__init__.py`` 再导出（A169／R13 §3：下游按
    ``campaignlab.worker.service.JobService`` 直接取），否则「导入 worker 包」会顺带拉起
    ``application.workspace_service`` 这条游标常量的来源模块。
    """

    def __init__(self, *, store: JobStore) -> None:
        self._store = store

    # ---------------------------------------------------------------------------- listJobs

    def list_jobs(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        query_digest: str,
        limit: int,
        cursor_payload: Mapping[str, Any] | None = None,
        q: str | None = None,
        status: str | None = None,
    ) -> tuple[list[JobRecord], dict[str, Any] | None]:
        """``GET /api/v1/workspaces/{workspace_id}/jobs`` 的用例实现（design §1）。

        翻页口径与 ``WorkspaceService.list_workspaces`` **逐条同形**：排序固定
        ``created_at DESC, id ASC``、键集谓词、每页取 ``limit + 1`` 行以判 ``next_cursor``、
        无结果 → ``([], None)``。差别只有 design §1 给 listJobs 加的两点：``status`` 是
        逗号分隔多值，``q`` 命中 ``id`` / ``kind`` / ``stage`` 三列（NFKC + casefold
        子串匹配，折叠口径单点在 ``JobStore.list_jobs``）。

        ``cursor_payload`` 是**已解码**的载荷（``api.common.decode_cursor`` 的返回值形状）；
        ``query_digest`` 是调用方按 design §1 算好的
        ``sha256(canonical_json({workspace_id, limit, q, status}))[:16]``。二者都由 S4 传入，
        本层不做 ``str`` 编解码（A169③ 的分层预裁）。
        """
        if limit < 1:
            raise DomainError(f"limit 必须 >= 1：{limit}", code="VALIDATION_ERROR")
        states = _parse_status(status)
        after: tuple[str, str] | None = None
        if cursor_payload is not None:
            after = _cursor_key(cursor_payload, actor_id=actor_id, query_digest=query_digest)
        rows = self._store.list_jobs(
            workspace_id=workspace_id,
            limit=limit + 1,
            after=after,
            q=q,
            states=states,
        )
        items = rows[:limit]
        next_payload: dict[str, Any] | None = None
        if len(rows) > limit and items:
            last = items[-1]
            next_payload = _next_cursor_payload(
                actor_id=actor_id,
                query_digest=query_digest,
                created_at=last.created_at,
                job_id=last.id,
            )
        return items, next_payload

    # ------------------------------------------------------------------------------ getJob

    def get_job(self, *, workspace_id: str, job_id: str) -> JobRecord | None:
        """``GET .../jobs/{job_id}`` 的读侧（design §1：只读短连接，**不开** ``BEGIN IMMEDIATE``）。

        跨工作区自然读不到即 ``None``，由 S4 映射成 404（OPERATIONS.md:7）。终态重复查询
        逐字节一致（JOBS.md:23）由「只读 + 不重算派生字段」天然成立。
        """
        return self._store.get_job(workspace_id=workspace_id, job_id=job_id)

    # ---------------------------------------------------------------------------- cancelJob

    def cancel_job(
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
        """``POST .../jobs/{job_id}/cancel`` → ``JobStore.request_cancel``（TX3）。

        参数面与 ``request_cancel`` **逐字同形**（含 ``role`` 的默认值取同一个
        ``DEFAULT_AUDIT_ROLE``）：本层不加不减，免得以「服务层默认值」的名义开出第二套
        审计角色口径。``If-Match`` 与当前 ``revision`` 不符由 store 翻成
        ``RevisionConflict``（412），QUEUED 直接终态／RUNNING 先置 CANCEL_REQUESTED 的
        分支判定也在 store 内；幂等重放（design §1：同键同体逐字节相同，含 ETag）归 S4 的
        ``IdempotencyGuard``，本层不碰信封。
        """
        return self._store.request_cancel(
            workspace_id=workspace_id,
            job_id=job_id,
            revision=revision,
            now=now,
            actor_id=actor_id,
            request_id=request_id,
            role=role,
        )

    # ----------------------------------------------------------------------------- retryJob

    def retry_job(
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
        """``POST .../jobs/{job_id}/retry`` → ``JobStore.retry``（TX8）。

        与 ``cancel_job`` 同一取向：**新建**一条 QUEUED 作业、源作业终态一字不变
        （JOBS.md:19），容量闸（A88②：待办上限 10 → ``JobCapacity`` + ``Retry-After: 3``）
        在 store 的 ``BEGIN IMMEDIATE`` 之内重算，本层不预判、不缓存计数。返回的是**新行**
        （``retry_of`` 指向源作业、``revision`` 从 1 重起），S4 据此出 200 + 新 ETag。
        """
        return self._store.retry(
            workspace_id=workspace_id,
            job_id=job_id,
            revision=revision,
            now=now,
            actor_id=actor_id,
            request_id=request_id,
            role=role,
        )


def _parse_status(status: str | None) -> tuple[str, ...] | None:
    """``status`` 逗号分隔多值 → 状态名元组；``None`` 表示不筛（design §1）。

    6 个态名全连恰 58 字符，故契约给的 ``maxLength=60`` 刚好放得下「六态全要」这一种写法。
    任何一段不在 ``JOB_STATES`` 里（含空段，例如 ``"QUEUED,"``）→ 422 ``VALIDATION_ERROR``：
    静默忽略未知态名会让「筛了一个不存在的状态」返回空页，看起来像库里真没有数据。
    重复段去重但**保序**（``dict.fromkeys``），让「同一库状态 ⇒ 同一顺序」继续成立。
    """
    if status is None:
        return None
    names = status.split(",")
    for name in names:
        if name not in JOB_STATES:
            raise DomainError(
                f"status 含未注册的状态名：{name!r}（权威 6 态见 worker.states.JOB_STATES）",
                code="VALIDATION_ERROR",
            )
    return tuple(dict.fromkeys(names))


def _cursor_key(payload: Mapping[str, Any], *, actor_id: str, query_digest: str) -> tuple[str, str]:
    """未编码游标载荷 → 键集 ``(created_at, id)``；任一项不符 → 400 ``BAD_CURSOR``。

    四条判据与 ``WorkspaceService._cursor_key`` 逐条同形（版本 / 查询摘要 / actor /
    ``k`` 形状），且**共用同一句 detail**（``BAD_CURSOR_DETAIL`` 是从
    ``application/workspace_service.py`` import 来的那一份，不是第二句）。换 actor 也判
    400 而不是 403：游标本身是不可信输入，用状态码区分「签名错」与「不是你的」等于给出
    探测面。
    """
    if payload.get("v") != CURSOR_VERSION:
        raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
    if payload.get("q") != query_digest:
        raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
    if payload.get("s") != actor_id:
        raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
    key = payload.get("k")
    if (
        not isinstance(key, list)
        or len(key) != 2
        or not isinstance(key[0], str)
        or not isinstance(key[1], str)
    ):
        raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
    return (key[0], key[1])


def _next_cursor_payload(
    *, actor_id: str, query_digest: str, created_at: str, job_id: str
) -> dict[str, Any]:
    """下一页的**未编码**载荷：design §1 的 ``{"v", "q", "k", "s"}`` 四键，键序也照抄。

    ``created_at`` 直接取 ``JobRecord.created_at`` —— 持久层的时刻本就是 UTC ISO-8601
    字符串（``repositories._iso``），故这里**不**再 ``.isoformat()``；与 workspaces 侧
    那句 ``last.created_at.isoformat()`` 的差别只源于 ``Workspace.created_at`` 是
    ``datetime`` 而 ``JobRecord.created_at`` 是 ``str``，键集语义完全一致。
    """
    return {
        "v": CURSOR_VERSION,
        "q": query_digest,
        "k": [created_at, job_id],
        "s": actor_id,
    }
