"""M0-04/S5 · jobs HTTP 面七例（派单 §4.3；design §1 的 listJobs／getJob／cancelJob／retryJob）。

纪律口径：游标版本号与坏游标 detail **一律 import 复用** ``application/workspace_service.py``
的单一真源（A222／FU-46：禁第二个版本号、禁第二句 detail 副本，回收按集合对撞查字面量复制）；
429 的退避秒数取 ``worker.capacity.JOB_CAPACITY_RETRY_AFTER_SECONDS``（N7②，禁写死）；
Problem code 只取权威 20 码（D-019）。前置 ``jobs`` 状态一律经 ``JobStore`` 公开方法
（A81）；工作区行按 S4 体例直插。时间一律 ``fixed_clock``／``advance_clock``。
"""

from __future__ import annotations

import ast
import sqlite3
from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from campaignlab.api.common import ObjectRef
from campaignlab.application.workspace_service import BAD_CURSOR_DETAIL
from campaignlab.clock import FixedClock
from campaignlab.config import API_PREFIX
from campaignlab.infra.db.repositories import JobRecord
from campaignlab.worker.capacity import JOB_CAPACITY_RETRY_AFTER_SECONDS
from campaignlab.worker.store import JobStore

WS_A: str = "ws-s5-a"
WS_B: str = "ws-s5-b"


def _seed_workspace(db_path: Path, workspace_id: str) -> None:
    """插入工作区行（S4 ``Harness.seed_workspace`` 同型体例；不在 A81 禁面）。"""
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


def _enqueue(job_store: JobStore, clock: FixedClock, workspace_id: str, job_id: str) -> JobRecord:
    record = job_store.enqueue(
        workspace_id=workspace_id,
        kind="VALIDATE_IMPORT",
        input_json="{}",
        input_digest="0" * 64,
        now=clock.now(),
        job_id=job_id,
    )
    assert record.state == "QUEUED"
    return record


def _headers(key: str, if_match: str | None = None) -> dict[str, str]:
    headers = {"Idempotency-Key": key}
    if if_match is not None:
        headers["If-Match"] = if_match
    return headers


def test_list_pagination_and_cursor(
    http_client: TestClient,
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
) -> None:
    """翻页＋游标往返：逐页恰好覆盖全部作业，末页 ``next_cursor`` 为空。"""
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, WS_A)
    for job_id in ("j-page-1", "j-page-2", "j-page-3"):
        _enqueue(job_store, fixed_clock, WS_A, job_id)

    seen: list[str] = []
    cursor: str | None = None
    for _page in range(4):
        url = f"{API_PREFIX}/workspaces/{WS_A}/jobs?limit=1"
        if cursor is not None:
            url = f"{url}&cursor={cursor}"
        response = http_client.get(url)
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["items"]) == 1
        seen.append(body["items"][0]["id"])
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert seen == ["j-page-1", "j-page-2", "j-page-3"]
    assert cursor is None


def test_bad_cursor_400(
    http_client: TestClient,
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
) -> None:
    """坏游标 ⇒ 400，detail 用单一真源 ``BAD_CURSOR_DETAIL`` 本体做比较。

    身份性说明（实测，非转述）：JSON 序列化往返必然产出新字符串对象，运行时
    ``is`` 在 TestClient 架构下不成立；故本例的「同对象」判据以**双重形态**落地——
    ① 值比较一律引用 import 的模块级对象（禁在本文件出现该句 detail 的字面量副本），
    ② 函数内 AST 自守护对撞这两条禁令（体例即 A115 集合对撞）：把断言改成同值
    字面量副本会被本守护直接判红（阳性对照 PC-5 的牙齿所在）。
    """
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, WS_A)

    response = http_client.get(f"{API_PREFIX}/workspaces/{WS_A}/jobs?cursor=not-a-real-cursor")
    assert response.status_code == 400, response.text
    body = response.json()
    assert body["code"] == "BAD_CURSOR"
    assert body["detail"] == BAD_CURSOR_DETAIL

    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    literals = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value == BAD_CURSOR_DETAIL
    ]
    assert literals == []
    func = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "test_bad_cursor_400"
    )
    identity_comparisons = [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.Compare)
        and any(
            isinstance(comparator, ast.Name) and comparator.id == "BAD_CURSOR_DETAIL"
            for comparator in node.comparators
        )
    ]
    assert identity_comparisons


def test_status_filter_multi_value(
    http_client: TestClient,
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
) -> None:
    """``status`` 逗号分隔多值（N7① 已裁定），单值是其子集。"""
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, WS_A)
    _enqueue(job_store, fixed_clock, WS_A, "j-a-done")
    _enqueue(job_store, fixed_clock, WS_A, "j-b-running")
    _enqueue(job_store, fixed_clock, WS_A, "j-c-queued")
    first = job_store.claim_next(workspace_id=WS_A, now=fixed_clock.now())
    assert first.record is not None
    assert first.record.id == "j-a-done"
    assert first.lease is not None

    job_store.succeed(
        first.lease,
        result_ref=ObjectRef(kind="job", id="j-a-done"),
        now=fixed_clock.now(),
    )
    second = job_store.claim_next(workspace_id=WS_A, now=fixed_clock.now())
    assert second.record is not None
    assert second.record.id == "j-b-running"

    multi = http_client.get(f"{API_PREFIX}/workspaces/{WS_A}/jobs?status=QUEUED,RUNNING")
    assert multi.status_code == 200, multi.text
    states = {item["state"] for item in multi.json()["items"]}
    assert states == {"QUEUED", "RUNNING"}
    ids = {item["id"] for item in multi.json()["items"]}
    assert ids == {"j-b-running", "j-c-queued"}

    single = http_client.get(f"{API_PREFIX}/workspaces/{WS_A}/jobs?status=QUEUED")
    assert single.status_code == 200, single.text
    assert [item["id"] for item in single.json()["items"]] == ["j-c-queued"]


def test_cross_workspace_is_404(
    http_client: TestClient,
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
) -> None:
    """跨工作区读单条作业 ⇒ 404 ``RESOURCE_NOT_FOUND``（A220；不回显差异）。"""
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, WS_A)
    _seed_workspace(db_path, WS_B)
    _enqueue(job_store, fixed_clock, WS_A, "j-cross")

    response = http_client.get(f"{API_PREFIX}/workspaces/{WS_B}/jobs/j-cross")
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "RESOURCE_NOT_FOUND"

    ok = http_client.get(f"{API_PREFIX}/workspaces/{WS_A}/jobs/j-cross")
    assert ok.status_code == 200, ok.text


def test_cancel_missing_if_match_428(
    http_client: TestClient,
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    idem_key: Callable[[str], str],
) -> None:
    """缺 ``If-Match`` ⇒ 428（先幂等、后 If-Match 的顺序使本分支可达）。"""
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, WS_A)
    _enqueue(job_store, fixed_clock, WS_A, "j-428")

    response = http_client.post(
        f"{API_PREFIX}/workspaces/{WS_A}/jobs/j-428/cancel",
        headers={"Idempotency-Key": idem_key("missing-if-match")},
    )
    assert response.status_code == 428, response.text
    assert response.json()["code"] == "PRECONDITION_REQUIRED"

    still = job_store.get_job(workspace_id=WS_A, job_id="j-428")
    assert still is not None
    assert still.state == "QUEUED"


def test_cancel_stale_if_match_412(
    http_client: TestClient,
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    idem_key: Callable[[str], str],
) -> None:
    """陈旧 ``If-Match`` ⇒ 412 ``REVISION_CONFLICT``，且不落任何状态迁移。"""
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, WS_A)
    record = _enqueue(job_store, fixed_clock, WS_A, "j-412")

    response = http_client.post(
        f"{API_PREFIX}/workspaces/{WS_A}/jobs/j-412/cancel",
        headers=_headers(idem_key("stale-if-match"), f'"{record.revision + 4}"'),
    )
    assert response.status_code == 412, response.text
    assert response.json()["code"] == "REVISION_CONFLICT"

    kept = job_store.get_job(workspace_id=WS_A, job_id="j-412")
    assert kept is not None
    assert kept.state == "QUEUED"
    assert kept.revision == record.revision


def test_retry_capacity_429_has_retry_after(
    http_client: TestClient,
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    idem_key: Callable[[str], str],
) -> None:
    """待办达上限的重试 ⇒ 429 且必带 ``Retry-After``（N7②；值取 capacity 常量，禁写死）。

    待办＝非终态计数（``QUEUED|RUNNING|CANCEL_REQUESTED``），上限 ``JOB_PENDING_LIMIT``；
    本例灌满 QUEUED 后对一条 FAILED 源作业发起重试。
    """
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, WS_A)
    for index in range(10):
        _enqueue(job_store, fixed_clock, WS_A, f"j-full-{index:02d}")

    _enqueue(job_store, fixed_clock, WS_A, "j-cap-source")
    claim = job_store.claim_next(workspace_id=WS_A, now=fixed_clock.now())
    assert claim.lease is not None
    from campaignlab.api.common import PROBLEM_CODES, Problem

    registry = PROBLEM_CODES["INTERNAL_ERROR"]
    problem = Problem(
        type=registry[1],
        title=registry[2],
        status=registry[0],
        code="INTERNAL_ERROR",
        issues=[],
        detail="s5 容量用例",
        request_id="req-cap",
    )
    failed = job_store.fail(claim.lease, problem=problem, now=fixed_clock.now())

    response = http_client.post(
        f"{API_PREFIX}/workspaces/{WS_A}/jobs/j-cap-source/retry",
        headers=_headers(idem_key("capacity"), f'"{failed.revision}"'),
    )
    assert response.status_code == 429, response.text
    assert response.json()["code"] == "JOB_CAPACITY"
    assert response.headers["Retry-After"] == str(JOB_CAPACITY_RETRY_AFTER_SECONDS)

    pending = job_store.pending_count(workspace_id=WS_A)
    assert pending == 10
    untouched = job_store.get_job(workspace_id=WS_A, job_id="j-cap-source")
    assert untouched is not None
    assert untouched.state == "FAILED"
    assert untouched.revision == failed.revision
