"""``campaignlab.api.jobs``：jobs 的 HTTP 面（M0-04/S4 · design §1/§6/§9-S4）。

4 个 operationId：``listJobs`` / ``getJob`` / ``cancelJob`` / ``retryJob``。
公开符号面恰为 ``router, list_jobs, get_job, cancel_job, retry_job``，
私有符号面恰为 ``_job_page_response, _job_response``（design §9-S4 行冻结，
守护在 ``tests/integration/jobs/test_jobs_router_s4.py`` 按 AST 钉住）。

本文件的落地纪律：

- 路由只做「解析 → 调 ``worker/service.py`` → 组装响应」（PYTHON.md:5），一条 SQL 都没有；
  行→DTO 的唯一映射点是 ``infra.db.repositories.job_from_row``（N5/A81，禁复制第二份）。
- 时钟一律 ``clock: Clock = Depends(get_clock)`` 注入后由调用方传入（派单 §3 D-045 条：
  取系统当前时间的字面量在 ``src/campaignlab/**`` 的任何位置都不许出现，注释与本
  docstring 也不例外，故此处以描述代替字面量）。
- 游标 ``str <-> payload`` 的编解码与 ``query_digest`` 计算归本层（A169③／design
  §9-S2 行「留给 S4 的三件事」②）；载荷绑定校验留在 ``worker/service.py``，本层不重复
  实现；版本号与 detail 复用 ``application/workspace_service.py`` 的同一份
  ``CURSOR_VERSION`` / ``BAD_CURSOR_DETAIL``，禁第二个版本号、禁第二句 detail。
- ``listJobs`` 的 404（工作区不存在或属外工作区）由路由侧产生（A220：``JobService``
  的构造面被 A206 钉死、``JobStore`` 无工作区查读面，服务层产生不了）。核验面只有
  ``api/deps.py::get_workspace_service`` 端口的 ``list_workspaces``——它没有单条读取口，
  故按**有界翻页枚举**逐页比对 ``Workspace.id``，枚举自然终止于 ``next_cursor`` 为空；
  未命中即与「不存在」同一 404，不回显差异、不构成探测面。装配口径取 §4① 候选 (b)：
  ``create_app`` 未装配 ``workspace_service`` 时整个 jobs.router 不挂载（与既有
  ``if workspace_service is not None:`` 体例一致），路由内的 ``get_workspace_service``
  因此不可能在挂载态下抛 ``RuntimeError``。
- ``cancelJob`` / ``retryJob`` 的幂等信封归本层（design §9-S2 行 S2c 注记：「幂等重放
  归 S4 的 ``IdempotencyGuard``」）。信封形状复用 ``api.common.idempotency_envelope`` /
  ``replay_from_envelope`` 的 M0-02 落地口径；顺序固定「先幂等、后 If-Match」（API.md）；
  新鲜响应与重放响应逐字节一致（仅 ``X-Request-Id`` 按 design §4 重新生成）。
  ``retryJob`` 的新鲜 202 按 design §1 必须走 ``accepted_response``，重放走
  ``replay_from_envelope``，两者的正文由同一 ``model_dump(mode="json")`` 序列化源保证
  字节一致（守护用例逐条钉住）。
- 引擎取用与 ``worker/deps.py::get_job_store`` 同一入口
  ``application.build_database_runtime(database_url=config.database_url)``（五级链唯一
  实现，ADR-005 §2.4），不为 jobs 另开第二套解析；每请求短连接、NullPool 即时回收。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response

from campaignlab.api.common import (
    CURSOR_MAX_LENGTH,
    IDEMPOTENCY_KEY_HEADER,
    DomainError,
    JobPage,
    ResourceNotFound,
    Session,
    accepted_response,
    canonical_json,
    check_if_match,
    decode_cursor,
    encode_cursor,
    etag,
    idempotency_envelope,
    problem_response,
    replay_from_envelope,
    request_digest,
    request_id_of,
    validate_idempotency_key,
)
from campaignlab.api.deps import get_clock, get_config, get_workspace_service, require_session
from campaignlab.api.session import JSON_MEDIA_TYPE, declared_responses
from campaignlab.application import build_database_runtime
from campaignlab.application.idempotency import IdempotencyGuard, IdempotencyKey
from campaignlab.application.workspace_service import (
    BAD_CURSOR_DETAIL,
    CURSOR_QUERY_DIGEST_HEX,
    load_cursor_secret,
)
from campaignlab.clock import Clock
from campaignlab.config import API_PREFIX
from campaignlab.domain.ids import RESOURCE_ID_PATTERN
from campaignlab.infra.db.engine import connect
from campaignlab.infra.db.repositories import JobRecord, job_from_row
from campaignlab.worker.deps import get_job_service
from campaignlab.worker.service import JobService

__all__ = ["cancel_job", "get_job", "list_jobs", "retry_job", "router"]

router = APIRouter(prefix=API_PREFIX, tags=["jobs"])


def _job_page_response(
    records: Sequence[JobRecord], next_payload: Mapping[str, Any] | None, *, secret: bytes
) -> Response:
    """``JobRecord`` 序列 → 200 ``JobPage``（HTTP 分页壳由本层组装，A169④）。

    ``next_payload`` 是 ``JobService.list_jobs`` 交回的**未编码**下一页载荷，此处编成
    游标串；无下一页即 ``next_cursor = null``（design §1：空结果两态都要能出）。
    """
    page = JobPage(
        items=[job_from_row(record) for record in records],
        next_cursor=None if next_payload is None else encode_cursor(next_payload, secret),
    )
    return Response(content=page.model_dump_json(), status_code=200, media_type=JSON_MEDIA_TYPE)


def _job_response(record: JobRecord) -> Response:
    """单行 → 200 ``Job`` + ``ETag: "<revision>"``（design §1：对象响应必带 ETag）。"""
    job = job_from_row(record)
    return Response(
        content=job.model_dump_json(),
        status_code=200,
        media_type=JSON_MEDIA_TYPE,
        headers={"ETag": etag(job.revision)},
    )


@router.get(
    "/workspaces/{workspace_id}/jobs",
    operation_id="listJobs",
    responses=declared_responses(200),
)
async def list_jobs(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    cursor: str | None = Query(None, min_length=1, max_length=CURSOR_MAX_LENGTH),
    limit: int = Query(25, ge=1, le=100),
    q: str | None = Query(None, min_length=1, max_length=100),
    status: str | None = Query(None, min_length=1, max_length=60),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: JobService = Depends(get_job_service),  # noqa: B008
) -> Response:
    """``listJobs``：200 ``JobPage``；工作区不可见 → 404；游标不符 → 400 ``BAD_CURSOR``。

    ``status`` 为逗号分隔多值（N7①），非法态名由服务层翻 422；``query_digest`` 按
    design §1 公式 ``sha256(canonical_json({workspace_id, limit, q, status}))[:16]``
    由本层计算并传入服务层做绑定校验（A169③：编解码与摘要归路由，校验留服务层）。
    """
    request_id = request_id_of(request)
    try:
        workspace_service = get_workspace_service(request)
        visible = False
        scan_cursor: str | None = None
        while True:
            page = workspace_service.list_workspaces(
                actor=actor, cursor=scan_cursor, limit=100, q=None
            )
            visible = any(item.id == workspace_id for item in page.items)
            if visible or page.next_cursor is None:
                break
            scan_cursor = page.next_cursor
        if not visible:
            raise ResourceNotFound("工作区不存在或不在你的可见范围")
        secret = load_cursor_secret(get_config(request).data_dir)
        payload: Mapping[str, Any] | None = None
        if cursor is not None:
            decoded = decode_cursor(cursor, secret)
            if decoded is None:
                raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
            payload = decoded
        query_digest = hashlib.sha256(
            canonical_json(
                {"workspace_id": workspace_id, "limit": limit, "q": q, "status": status}
            ).encode("utf-8")
        ).hexdigest()[:CURSOR_QUERY_DIGEST_HEX]
        records, next_payload = svc.list_jobs(
            workspace_id=workspace_id,
            actor_id=actor.actor_id,
            query_digest=query_digest,
            limit=limit,
            cursor_payload=payload,
            q=q,
            status=status,
        )
        return _job_page_response(records, next_payload, secret=secret)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.get(
    "/workspaces/{workspace_id}/jobs/{job_id}",
    operation_id="getJob",
    responses=declared_responses(200),
)
async def get_job(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    job_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    actor: Session = Depends(require_session),  # noqa: B008
    svc: JobService = Depends(get_job_service),  # noqa: B008
) -> Response:
    """``getJob``：200 ``Job`` + ``ETag``；不存在或属外工作区 → 404。

    跨工作区由 ``JobStore`` 的 ``workspace_id`` 过滤自然读不到（design §7 / §4①），
    本层不再加第二层工作区核验；终态重复查询逐字节一致由只读语义天然保证。
    """
    request_id = request_id_of(request)
    try:
        record = svc.get_job(workspace_id=workspace_id, job_id=job_id)
        if record is None:
            raise ResourceNotFound(f"作业不存在或不属于该工作区：{job_id}")
        return _job_response(record)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.post(
    "/workspaces/{workspace_id}/jobs/{job_id}/cancel",
    operation_id="cancelJob",
    responses=declared_responses(200),
)
async def cancel_job(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    job_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    idempotency_key: str = Header(alias=IDEMPOTENCY_KEY_HEADER, min_length=8, max_length=128),
    if_match: str | None = Header(
        alias="If-Match",
        default=None,
        min_length=3,
        max_length=32,
        pattern=r'^"[1-9][0-9]*"$',
    ),
    actor: Session = Depends(require_session),  # noqa: B008
    clock: Clock = Depends(get_clock),  # noqa: B008
    svc: JobService = Depends(get_job_service),  # noqa: B008
) -> Response:
    """``cancelJob``：200 ``Job`` + ``ETag``（契约只声明 200，**非 204**）。

    处置顺序：先幂等（peek 命中即逐字节重放）、再 If-Match（缺 → 428、陈旧 → 412）。
    ``if_match`` 声明为可空形参是 428 可达的前提：若按字面声明必填，缺头会被 FastAPI
    在进入函数体前判 422，design §6/§7 要求的 428 分支就结构上不可达（U 项上报）。
    ``Idempotency-Key`` 保持契约必填声明，与 ``api/workspaces.py::create_workspace``
    同一口径。重放与新鲜响应共用 ``replay_from_envelope`` 序列化源，字节一致。
    """
    request_id = request_id_of(request)
    try:
        key_value = validate_idempotency_key(idempotency_key)
        guard = IdempotencyGuard()
        idem = IdempotencyKey(
            scope_key=workspace_id,
            actor_id=actor.actor_id,
            operation="cancelJob",
            idem_key=key_value,
        )
        digest = request_digest(
            path=f"{API_PREFIX}/workspaces/{workspace_id}/jobs/{job_id}/cancel",
            query={"if_match": if_match if if_match is not None else ""},
            body=b"",
            files=(),
        )
        engine = build_database_runtime(database_url=get_config(request).database_url).engine
        with connect(engine) as conn, conn.begin():
            existing = guard.peek(conn, key=idem, request_digest=digest)
        if existing is not None:
            return replay_from_envelope(existing.envelope(), request_id=request_id)
        record = svc.get_job(workspace_id=workspace_id, job_id=job_id)
        if record is None:
            raise ResourceNotFound(f"作业不存在或不属于该工作区：{job_id}")
        check_if_match(if_match, record.revision)
        outcome = svc.cancel_job(
            workspace_id=workspace_id,
            job_id=job_id,
            revision=record.revision,
            now=clock.now(),
            actor_id=actor.actor_id,
            request_id=request_id,
        )
        job = job_from_row(outcome)
        envelope = idempotency_envelope(
            status=200,
            headers={"ETag": etag(job.revision)},
            body=job.model_dump(mode="json"),
        )
        with connect(engine) as conn, conn.begin():
            stored = guard.record(
                conn,
                key=idem,
                request_digest=digest,
                status=200,
                envelope_json=json.dumps(envelope, ensure_ascii=False, separators=(",", ":")),
                now=clock.now(),
            )
        if stored is not None:
            return replay_from_envelope(stored.envelope(), request_id=request_id)
        return replay_from_envelope(envelope, request_id=request_id)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)


@router.post(
    "/workspaces/{workspace_id}/jobs/{job_id}/retry",
    operation_id="retryJob",
    responses=declared_responses(202),
)
async def retry_job(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    job_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    idempotency_key: str = Header(alias=IDEMPOTENCY_KEY_HEADER, min_length=8, max_length=128),
    if_match: str | None = Header(
        alias="If-Match",
        default=None,
        min_length=3,
        max_length=32,
        pattern=r'^"[1-9][0-9]*"$',
    ),
    actor: Session = Depends(require_session),  # noqa: B008
    clock: Clock = Depends(get_clock),  # noqa: B008
    svc: JobService = Depends(get_job_service),  # noqa: B008
) -> Response:
    """``retryJob``：202 新作业 + ``Location`` + ``ETag: "1"``（design §1，Q2 口径）。

    新鲜路径按 design §1 走 ``accepted_response``；重放路径按同一信封走
    ``replay_from_envelope``（信封 ``headers`` 含 ``ETag`` 与 ``Location``，
    ``REPLAYED_HEADERS`` 恰覆盖这两个头）。源作业非 ``FAILED``/``CANCELLED`` 由
    store 翻 409 ``STATE_CONFLICT``；待办达上限由 store 翻 429 ``JOB_CAPACITY``，
    ``Retry-After: 3`` 由 ``problem_response`` 从异常自带的 ``retry_after`` 落成头。
    """
    request_id = request_id_of(request)
    try:
        key_value = validate_idempotency_key(idempotency_key)
        guard = IdempotencyGuard()
        idem = IdempotencyKey(
            scope_key=workspace_id,
            actor_id=actor.actor_id,
            operation="retryJob",
            idem_key=key_value,
        )
        digest = request_digest(
            path=f"{API_PREFIX}/workspaces/{workspace_id}/jobs/{job_id}/retry",
            query={"if_match": if_match if if_match is not None else ""},
            body=b"",
            files=(),
        )
        engine = build_database_runtime(database_url=get_config(request).database_url).engine
        with connect(engine) as conn, conn.begin():
            existing = guard.peek(conn, key=idem, request_digest=digest)
        if existing is not None:
            return replay_from_envelope(existing.envelope(), request_id=request_id)
        record = svc.get_job(workspace_id=workspace_id, job_id=job_id)
        if record is None:
            raise ResourceNotFound(f"作业不存在或不属于该工作区：{job_id}")
        check_if_match(if_match, record.revision)
        outcome = svc.retry_job(
            workspace_id=workspace_id,
            job_id=job_id,
            revision=record.revision,
            now=clock.now(),
            actor_id=actor.actor_id,
            request_id=request_id,
        )
        job = job_from_row(outcome)
        location = f"{API_PREFIX}/workspaces/{workspace_id}/jobs/{job.id}"
        envelope = idempotency_envelope(
            status=202,
            headers={"ETag": etag(job.revision), "Location": location},
            body=job.model_dump(mode="json"),
        )
        with connect(engine) as conn, conn.begin():
            stored = guard.record(
                conn,
                key=idem,
                request_digest=digest,
                status=202,
                envelope_json=json.dumps(envelope, ensure_ascii=False, separators=(",", ":")),
                now=clock.now(),
            )
        if stored is not None:
            return replay_from_envelope(stored.envelope(), request_id=request_id)
        return accepted_response(job, location=location, request_id=request_id)
    except DomainError as exc:
        return problem_response(exc, request_id=request_id)
