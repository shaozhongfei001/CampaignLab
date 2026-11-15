"""M0-04/S5 · 幂等三例（派单 §4.2；jobs HTTP 面的幂等信封行为）。

载体说明（活契约实测）：``contracts/openapi.json`` 的 jobs 面**没有**创建端点
（仅 listJobs／getJob／cancelJob／retryJob，submitJob 出现次数实测为 0），
故「同键同请求体」三例落在 ``cancelJob``——其 ``request_digest`` 覆盖
path＋query＋body＋files（本 op body 为空、path 含 job_id），同键异请求
即异摘要 ⇒ 409，与 §4.2 的语义逐条对齐。「同一对象」的判据取 id 相等＋
响应体逐字节相等（信封重放与新鲜响应共用 ``replay_from_envelope`` 序列化源）。

前置状态一律经 ``JobStore`` 公开方法构造（A81：``jobs`` 表 DML 文本禁入测试件）；
工作区行按 S4 ``Harness.seed_workspace`` 体例直插（``workspaces`` 不在 A81 禁面）。
时间一律 ``fixed_clock``／``advance_clock``，本文件无流逝字面量（红线 3／D-045）。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from campaignlab.clock import FixedClock
from campaignlab.config import API_PREFIX
from campaignlab.worker.store import JobStore

WS: str = "ws-s5-idem"


def _seed_workspace(db_path: Path, workspace_id: str) -> None:
    """按 S4 体例插入工作区行（A81 只禁 ``jobs`` 表 DML 入测试，此处不越界）。"""
    raw = sqlite3.connect(db_path)
    try:
        raw.execute(
            "INSERT INTO workspaces(id, name, source_class, authorization_note, revision,"
            " created_at) VALUES (?, ?, ?, NULL, 1, ?)",
            (workspace_id, f"ws-{workspace_id}", "SYNTHETIC", "2026-11-13T01:00:00+00:00"),
        )
        raw.commit()
    finally:
        raw.close()


def _enqueue(job_store: JobStore, clock: FixedClock, job_id: str) -> None:
    job_store.enqueue(
        workspace_id=WS,
        kind="VALIDATE_IMPORT",
        input_json="{}",
        input_digest="0" * 64,
        now=clock.now(),
        job_id=job_id,
    )


def _cancel(
    client: TestClient,
    job_id: str,
    *,
    key: str,
    if_match: str = '"1"',
) -> httpx.Response:
    response: httpx.Response = client.post(
        f"{API_PREFIX}/workspaces/{WS}/jobs/{job_id}/cancel",
        headers={"Idempotency-Key": key, "If-Match": if_match},
    )
    return response


def test_same_key_same_request_same_object(
    http_client: TestClient,
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    idem_key: Callable[[str], str],
) -> None:
    """同 ``Idempotency-Key``＋同请求 ⇒ 返回**同一对象**：id 相等、体逐字节相等。"""
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, WS)
    _enqueue(job_store, fixed_clock, "j-idem-a")
    key = idem_key("same-object")

    first = _cancel(http_client, "j-idem-a", key=key)
    replay = _cancel(http_client, "j-idem-a", key=key)

    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    assert replay.content == first.content
    body = replay.json()
    assert body["id"] == "j-idem-a"
    assert body["state"] == "CANCELLED"


def test_same_key_different_request_409(
    http_client: TestClient,
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    idem_key: Callable[[str], str],
) -> None:
    """同键异请求 ⇒ 409（peek 摘要不符即抛，禁发明新 code——D-019 取权威 20 码）。"""
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, WS)
    _enqueue(job_store, fixed_clock, "j-idem-c")
    _enqueue(job_store, fixed_clock, "j-idem-d")
    key = idem_key("different-request")

    first = _cancel(http_client, "j-idem-c", key=key)
    assert first.status_code == 200, first.text

    clash = _cancel(http_client, "j-idem-d", key=key)
    assert clash.status_code == 409, clash.text
    assert clash.json()["code"] == "IDEMPOTENCY_CONFLICT"

    untouched = job_store.get_job(workspace_id=WS, job_id="j-idem-d")
    assert untouched is not None
    assert untouched.state == "QUEUED"


def test_replay_body_byte_identical(
    http_client: TestClient,
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    idem_key: Callable[[str], str],
) -> None:
    """重放响应体与首次逐字节相同。

    头对比排除 ``X-Request-Id``：重放路径按 design §4 为每次请求**重新生成**该头
    （``replay_from_envelope(request_id=...)``），它是请求级追踪标识而非对象内容，
    逐字节一致判据只约束正文与 ``ETag`` 等语义头——此为排除该头的理由（§4.2 要求
    在 docstring 写明）。
    """
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, WS)
    _enqueue(job_store, fixed_clock, "j-idem-e")
    key = idem_key("byte-identical")

    first = _cancel(http_client, "j-idem-e", key=key)
    replay = _cancel(http_client, "j-idem-e", key=key)
    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text

    assert first.content == replay.content
    assert first.headers["ETag"] == replay.headers["ETag"]
    semantic_first = {
        name: value for name, value in first.headers.items() if name.lower() != "x-request-id"
    }
    semantic_replay = {
        name: value for name, value in replay.headers.items() if name.lower() != "x-request-id"
    }
    assert semantic_first == semantic_replay
    assert first.headers["x-request-id"] != replay.headers["x-request-id"]
