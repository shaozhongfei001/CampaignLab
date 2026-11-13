"""S3d：仓储层与 worker 租约（A11/A12 的机器可查面）。

钉住五件事：

1. ``WorkspaceRepository`` 的键集翻页与 ``q`` 的 NFKC＋casefold 匹配（design §1）；
2. ``IdempotencyRepository.insert`` 靠主键唯一返回 False，不靠异常（design §2）；
3. ``AuditRepository`` 的 ``sequence`` 递增与 ``previous_digest`` 成链（design §3）；
4. ``JobRepository`` 是 ``jobs`` 的唯一写入口，``touch_lease`` 有抢占保护；
5. ``WorkerSupervisor.heartbeat(job_id, *, now)`` 是 ``jobs.lease_until`` 的唯一写入路径，
   且租约期限只由**注入时钟**派生（不自取系统时间）。

库用活契约 ``contracts/sqlite-v1.sql`` 建（只读），不跑 alembic：本文件要测的是 SQL 与
DDL 约束的互动，不是迁移本身（迁移等价性由 ``tests/integration/bootstrap`` 守）。
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from campaignlab.api.common import Issue, Problem, Workspace
from campaignlab.application.worker import WORKER_LEASE_SECONDS, WorkerSupervisor
from campaignlab.clock import FixedClock
from campaignlab.infra.db.engine import connect, make_engine
from campaignlab.infra.db.repositories import (
    ArtifactRecord,
    ArtifactRepository,
    AuditRecord,
    AuditRepository,
    IdempotencyRecord,
    IdempotencyRepository,
    JobRecord,
    JobRepository,
    WorkspaceRepository,
    job_from_row,
)

REPO = Path(__file__).resolve().parents[2]
DDL = REPO / "contracts" / "sqlite-v1.sql"
T0 = datetime(2026, 11, 13, 1, 0, 0, tzinfo=UTC)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    """按活契约 DDL 建一个临时库，并预置 ``alembic_version``（供 health 侧判定）。"""
    assert DDL.is_file(), f"活契约 DDL 读不到：{DDL}"
    db = tmp_path / "campaignlab.db"
    raw = sqlite3.connect(db)
    try:
        raw.executescript(DDL.read_text(encoding="utf-8"))
        raw.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        raw.execute("INSERT INTO alembic_version (version_num) VALUES ('0001_initial_schema')")
        raw.commit()
    finally:
        raw.close()
    return make_engine(f"sqlite:///{db}")


def _workspace(ws_id: str, created_at: datetime, name: str = "工作区") -> Workspace:
    return Workspace(
        id=ws_id,
        revision=1,
        created_at=created_at,
        name=name,
        source_class="SYNTHETIC",
        authorization_note=None,
    )


def _job(ws_id: str, job_id: str, kind: str = "COMPARE") -> JobRecord:
    return JobRecord(
        workspace_id=ws_id,
        id=job_id,
        kind=kind,
        state="QUEUED",
        attempt=0,
        progress=0,
        stage="QUEUED",
        lease_token=None,
        lease_deadline=None,
        retry_of=None,
        retryable=True,
        input_json="{}",
        input_digest="0" * 64,
        result_json=None,
        problem_json=None,
        revision=1,
        created_at=T0.isoformat(),
    )


def test_workspace_roundtrip_keeps_all_six_fields(engine: Engine) -> None:
    repos = WorkspaceRepository()
    with connect(engine) as conn, conn.begin():
        repos.insert(conn, workspace=_workspace("ws-1", T0, name="甲"))
        got = None
    with connect(engine) as conn:
        got = repos.get(conn, "ws-1")
        missing = repos.get(conn, "ws-missing")
    assert got is not None
    assert got.id == "ws-1" and got.revision == 1 and got.name == "甲"
    assert got.created_at == T0
    assert got.authorization_note is None
    assert missing is None


def test_list_page_orders_created_at_desc_id_asc_and_respects_limit(engine: Engine) -> None:
    repos = WorkspaceRepository()
    with connect(engine) as conn, conn.begin():
        for index, ws_id in enumerate(("ws-b", "ws-a", "ws-c")):
            # created_at 依次递增：ws-b(T0) < ws-a(T0+1m) < ws-c(T0+2m)
            repos.insert(conn, workspace=_workspace(ws_id, T0 + timedelta(minutes=index)))
        page = repos.list_page(conn, limit=2)
    assert [item.id for item in page] == ["ws-c", "ws-a"]  # created_at DESC
    last = page[-1]
    with connect(engine) as conn:
        rest = repos.list_page(conn, limit=2, after=(last.created_at.isoformat(), last.id))
    assert [item.id for item in rest] == ["ws-b"]


def test_list_page_q_filter_is_nfkc_and_casefold(engine: Engine) -> None:
    """``q`` 必须 NFKC＋casefold：全角与大小写混排都要命中（design §1）。"""
    repos = WorkspaceRepository()
    with connect(engine) as conn, conn.begin():
        repos.insert(conn, workspace=_workspace("ws-1", T0, name="Bank Ａ 复盘"))
        repos.insert(conn, workspace=_workspace("ws-2", T0 + timedelta(minutes=1), name="无关"))
        hit = repos.list_page(conn, limit=10, q="bank a")
        miss = repos.list_page(conn, limit=10, q="zzz")
    assert [item.id for item in hit] == ["ws-1"]
    assert miss == []


def test_list_page_rejects_non_positive_limit(engine: Engine) -> None:
    with connect(engine) as conn, pytest.raises(ValueError):
        WorkspaceRepository().list_page(conn, limit=0)


def test_artifact_relative_path_is_globally_unique(engine: Engine) -> None:
    """``artifacts.relative_path`` 是全局 UNIQUE：两工作区同路径必须撞约束（design §4）。"""
    repos = WorkspaceRepository()
    arts = ArtifactRepository()

    def record(ws_id: str) -> ArtifactRecord:
        return ArtifactRecord(
            workspace_id=ws_id,
            id="art-1",
            kind="RAW",
            sha256="a" * 64,
            relative_path="raw/shared.csv",
            byte_size=10,
            created_at=T0.isoformat(),
        )

    with connect(engine) as conn, conn.begin():
        repos.insert(conn, workspace=_workspace("ws-a", T0))
        repos.insert(conn, workspace=_workspace("ws-b", T0))
        arts.insert(conn, artifact=record("ws-a"))
    with pytest.raises(IntegrityError), connect(engine) as conn, conn.begin():
        arts.insert(conn, artifact=record("ws-b"))
    with connect(engine) as conn:
        assert arts.get(conn, workspace_id="ws-b", artifact_id="art-1") is None
        assert arts.get(conn, workspace_id="ws-a", artifact_id="art-1") is not None
        assert arts.list_for_workspace(conn, "ws-b") == []


def test_idempotency_insert_conflict_returns_false_not_exception(engine: Engine) -> None:
    repos = IdempotencyRepository()

    def record(digest: str) -> IdempotencyRecord:
        return IdempotencyRecord(
            scope_key="GLOBAL",
            actor_id="tester",
            operation="createWorkspace",
            idem_key="key-1234",
            request_digest=digest,
            response_status=201,
            response_json='{"status":201,"headers":{},"body":{}}',
            created_at=T0.isoformat(),
        )

    with connect(engine) as conn, conn.begin():
        assert repos.insert(conn, record=record("d" * 64)) is True
    with connect(engine) as conn, conn.begin():
        assert repos.insert(conn, record=record("e" * 64)) is False
    with connect(engine) as conn:
        stored = repos.fetch(
            conn,
            scope_key="GLOBAL",
            actor_id="tester",
            operation="createWorkspace",
            idem_key="key-1234",
        )
    assert stored is not None and stored.request_digest == "d" * 64
    assert stored.envelope() == {"status": 201, "headers": {}, "body": {}}


def test_audit_sequence_increments_and_previous_digest_chains(engine: Engine) -> None:
    repos = WorkspaceRepository()
    audits = AuditRepository()
    with connect(engine) as conn, conn.begin():
        repos.insert(conn, workspace=_workspace("ws-1", T0))
        repos.insert(conn, workspace=_workspace("ws-2", T0))
        assert audits.next_sequence(conn, "ws-1") == 1
        assert audits.last_digest(conn, "ws-1") is None
        audits.insert(
            conn,
            record=AuditRecord(
                workspace_id="ws-1",
                sequence=1,
                id="aud-1",
                at=T0.isoformat(),
                actor_id="tester",
                role="OPERATOR",
                action="WORKSPACE_CREATED",
                target_kind="workspace",
                target_id="ws-1",
                outcome="ACCEPTED",
                request_id="r1",
                previous_digest=None,
                digest="1" * 64,
            ),
        )
        assert audits.next_sequence(conn, "ws-1") == 2
        assert audits.last_digest(conn, "ws-1") == "1" * 64
        assert audits.next_sequence(conn, "ws-2") == 1


def test_job_insert_only_accepts_queued(engine: Engine) -> None:
    repos = WorkspaceRepository()
    jobs = JobRepository()
    base = _job("ws-1", "job-2")
    running = replace(base, state="RUNNING")
    leased = replace(base, lease_token="t", lease_deadline=T0.isoformat())
    with connect(engine) as conn, conn.begin():
        repos.insert(conn, workspace=_workspace("ws-1", T0))
        with pytest.raises(ValueError):
            jobs.insert(conn, job=running)
        with pytest.raises(ValueError):
            jobs.insert(conn, job=leased)
        jobs.insert(conn, job=_job("ws-1", "job-1"))


def test_job_get_is_scoped_by_workspace_id(engine: Engine) -> None:
    """跨工作区读必须落空（design §4：单对象查询漏 workspace_id 就是跨工作区读）。"""
    repos = WorkspaceRepository()
    jobs = JobRepository()
    with connect(engine) as conn, conn.begin():
        repos.insert(conn, workspace=_workspace("ws-a", T0))
        repos.insert(conn, workspace=_workspace("ws-b", T0))
        jobs.insert(conn, job=_job("ws-a", "job-1"))
    with connect(engine) as conn:
        assert jobs.get(conn, workspace_id="ws-a", job_id="job-1") is not None
        assert jobs.get(conn, workspace_id="ws-b", job_id="job-1") is None
        assert [row.id for row in jobs.list_ready(conn, limit=10)] == ["job-1"]


def test_job_from_row_maps_result_ref_and_problem() -> None:
    problem = Problem(
        type="urn:campaignlab:problem:internal_error",
        title="内部错误",
        status=500,
        code="INTERNAL_ERROR",
        detail="request_id=r1",
        request_id="r1",
        issues=[Issue(code="INTERNAL_ERROR", location="/x", message="m", severity="ERROR")],
    )
    record = replace(
        _job("ws-1", "job-1"),
        state="FAILED",
        problem_json=problem.model_dump_json(),
        result_json='{"kind":"report","id":"rep-1"}',
    )
    job = job_from_row(record)
    assert job.state == "FAILED"
    assert job.problem is not None and job.problem.code == "INTERNAL_ERROR"
    assert len(job.problem.issues) == 1
    assert job.result_ref is not None and job.result_ref.kind == "report"


def test_worker_heartbeat_is_the_only_lease_writer(engine: Engine) -> None:
    repos = WorkspaceRepository()
    jobs = JobRepository()
    with connect(engine) as conn, conn.begin():
        repos.insert(conn, workspace=_workspace("ws-1", T0))
        jobs.insert(conn, job=_job("ws-1", "job-1"))
    clock = FixedClock(T0)
    worker = WorkerSupervisor(clock=clock, engine=engine, lease_seconds=WORKER_LEASE_SECONDS)

    assert worker.heartbeat("job-1", now=T0) is True
    with connect(engine) as conn:
        row = jobs.get(conn, workspace_id="ws-1", job_id="job-1")
    assert row is not None
    assert row.lease_deadline == (T0 + timedelta(seconds=WORKER_LEASE_SECONDS)).isoformat()
    assert row.state == "RUNNING" and row.attempt == 1 and row.revision == 2

    later = T0 + timedelta(seconds=10)
    assert worker.heartbeat("job-1", now=later) is True
    with connect(engine) as conn:
        row2 = jobs.get(conn, workspace_id="ws-1", job_id="job-1")
    assert row2 is not None
    assert row2.attempt == 1 and row2.revision == 3
    assert row2.lease_deadline == (later + timedelta(seconds=WORKER_LEASE_SECONDS)).isoformat()

    intruder = WorkerSupervisor(clock=clock, engine=engine)
    assert intruder.heartbeat("job-1", now=later) is False
    with connect(engine) as conn:
        row3 = jobs.get(conn, workspace_id="ws-1", job_id="job-1")
    assert row3 is not None and row3.lease_deadline == row2.lease_deadline
    assert worker.heartbeat("job-missing", now=later) is False


def test_poll_once_claims_nothing_without_handlers(engine: Engine) -> None:
    """M0-02 没有可注册的作业 kind：poll_once 不得把 QUEUED 作业变成僵尸 RUNNING。"""
    repos = WorkspaceRepository()
    jobs = JobRepository()
    with connect(engine) as conn, conn.begin():
        repos.insert(conn, workspace=_workspace("ws-1", T0))
        jobs.insert(conn, job=_job("ws-1", "job-1"))
    worker = WorkerSupervisor(clock=FixedClock(T0), engine=engine)
    assert worker.poll_once(now=T0) == 0
    with connect(engine) as conn:
        row = jobs.get(conn, workspace_id="ws-1", job_id="job-1")
    assert row is not None and row.state == "QUEUED" and row.lease_deadline is None


def test_worker_status_is_offline_until_first_beat_and_on_failure() -> None:
    clock = FixedClock(T0)
    worker = WorkerSupervisor(
        clock=clock, engine=make_engine("sqlite://"), heartbeat_ttl_seconds=15
    )
    assert worker.status(T0) == "OFFLINE"
    worker._heartbeat_at = T0
    assert worker.status(T0) == "READY"
    assert worker.status(T0 + timedelta(seconds=15)) == "READY"
    assert worker.status(T0 + timedelta(seconds=16)) == "OFFLINE"
    worker._failed = True
    assert worker.status(T0) == "OFFLINE"


def test_worker_thread_beat_makes_status_ready(engine: Engine) -> None:
    """起真线程跑一轮：心跳落地后 status() 报 READY，stop() 能干净收场。"""
    import time

    worker = WorkerSupervisor(
        clock=FixedClock(T0), engine=engine, heartbeat_ttl_seconds=15, poll_interval_seconds=0.01
    )
    assert worker.status(T0) == "OFFLINE"
    worker.start()
    worker.start()  # 幂等
    try:
        for _ in range(500):
            if worker.heartbeat_at is not None:
                break
            time.sleep(0.01)
        beat = worker.heartbeat_at
        assert beat is not None
        assert worker.failed is False and worker.last_error is None
        assert worker.status(beat) == "READY"
    finally:
        worker.stop(timeout=2.0)
    assert worker.running is False
