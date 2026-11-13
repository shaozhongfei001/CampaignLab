"""M0-04/S2：9 条状态机迁移 × 认领／续租／取消／重试的单测（design §3 逐条落测）。

覆盖面对齐 JOBS.md 第 11-19 行的迁移表：**9 条逐条一个 ``test_tN_*``**，函数名里带
``t1``…``t9``，与 design §9 给 S5 的命名体例一致，便于编排器按名核对「9 条不多不少」。
另外覆盖执行侧（``WorkerRunner``）的三件事：未注册 kind 的处置、handler 抛错的收口、
以及取消信号如何经续租回读传导到 ``CancelToken``。

时序一律用 ``FixedClock``：租约过期靠 ``clock.advance()`` 推过 ``lease_until``，
**不用固定时长 ``sleep``**（design §4）；库用活契约 DDL 建，不跑 alembic
（与 ``test_s3d_repositories.py`` 同一口径）。
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from campaignlab.api.common import ObjectRef, Problem
from campaignlab.application.worker import WORKER_LEASE_SECONDS, compute_lease_deadline
from campaignlab.clock import FixedClock
from campaignlab.domain.errors import (
    DomainError,
    InternalFailure,
    JobCapacity,
    ResourceNotFound,
    RevisionConflict,
    StateConflict,
    ValidationFailure,
)
from campaignlab.infra.db.engine import connect, make_engine
from campaignlab.infra.db.repositories import ArtifactRecord, JobRecord
from campaignlab.worker.capacity import JOB_CAPACITY_RETRY_AFTER_SECONDS, JOB_PENDING_LIMIT
from campaignlab.worker.errors import JOB_INTERRUPTED, LeaseLost, problem_of
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
    assert_transition_allowed,
    retryable_for,
)
from campaignlab.worker.store import Claim, JobStore, Reaped

REPO = Path(__file__).resolve().parents[2]
DDL = REPO / "contracts" / "sqlite-v1.sql"
T0 = datetime(2026, 11, 13, 1, 0, 0, tzinfo=UTC)
WS = "ws-1"
DIGEST = "0" * 64
ACTOR = "op-1"
REQUEST = "req-1"


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    """按活契约 DDL 建临时库（只读引用 ``contracts/**``，不改一字节）。"""
    assert DDL.is_file(), f"活契约 DDL 读不到：{DDL}"
    db = tmp_path / "campaignlab.db"
    raw = sqlite3.connect(db)
    try:
        raw.executescript(DDL.read_text(encoding="utf-8"))
        raw.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        raw.execute("INSERT INTO alembic_version (version_num) VALUES ('0001_initial_schema')")
        raw.execute(
            "INSERT INTO workspaces (id,name,source_class,revision,created_at) "
            "VALUES ('ws-1','合成工作区','SYNTHETIC',1,'2026-11-13T01:00:00+00:00')"
        )
        raw.commit()
    finally:
        raw.close()
    return make_engine(f"sqlite:///{db}")


@pytest.fixture
def clock() -> FixedClock:
    """显式时钟。``step=0`` 故 ``now()`` 幂等，只有 ``advance()`` 会推进时刻。"""
    return FixedClock(T0)


@pytest.fixture
def store(engine: Engine) -> JobStore:
    return JobStore(engine=engine)


def _enqueue(store: JobStore, job_id: str = "J-1", kind: str = "COMPARE") -> JobRecord:
    return store.enqueue(
        workspace_id=WS,
        kind=kind,
        input_json=json.dumps({"snapshot": "S-1"}, ensure_ascii=False),
        input_digest=DIGEST,
        now=T0,
        job_id=job_id,
    )


def _claim(store: JobStore, clock: FixedClock, job_id: str = "J-1") -> Claim:
    _enqueue(store, job_id)
    claim = store.claim_next(workspace_id=WS, now=clock.now())
    assert claim.claimed, "前置条件：必须认领成功"
    return claim


def _audit_rows(engine: Engine) -> list[tuple[str, str, str]]:
    with connect(engine) as conn:
        rows = conn.execute(
            text("SELECT action, target_id, outcome FROM audit ORDER BY sequence")
        ).all()
    return [(str(a), str(b), str(c)) for a, b, c in rows]


# ============================================================ 迁移表本身（纯数据，不碰库）


def test_transitions_table_is_exactly_nine_rows_of_jobs_md() -> None:
    """``TRANSITIONS`` 恰 9 项，与 JOBS.md:11-19 逐行对应，编号 T1..T9 无重复无缺。"""
    assert len(TRANSITIONS) == 9
    assert [t.id for t in TRANSITIONS] == [f"T{i}" for i in range(1, 10)]
    assert [t.spec_ref for t in TRANSITIONS] == [f"JOBS.md:{n}" for n in range(11, 20)]


def test_t1_to_t8_never_leave_a_terminal_state() -> None:
    """**终态唯一**的静态半边：T1-T8 的前态集合都不含任何终态（design §3 原文口径）。

    T9 是**唯一**例外，且它并不迁移终态行——它新建一行 QUEUED，源作业的终态一字不变，
    只 ``revision + 1``。故本断言按 ``creates_new_row`` 分开核对：改写既有行的 8 条
    一条都不许从终态出发；新建行的那条只许从 FAILED／CANCELLED 出发。

    这条与数据库谓词是双保险——即便有人日后写出一条 ``SUCCEEDED -> *`` 的 UPDATE，
    它也无法被登记进 ``TRANSITIONS``，``assert_transition_allowed`` 会先拒。
    """
    rewriting = [t for t in TRANSITIONS if not t.creates_new_row]
    creating = [t for t in TRANSITIONS if t.creates_new_row]
    assert len(rewriting) == 8 and len(creating) == 1
    for t in rewriting:
        assert not (set(t.sources) & TERMINAL_STATES), t.id
    assert creating[0].id == "T9"
    assert set(creating[0].sources) == {"CANCELLED", "FAILED"}
    assert "SUCCEEDED" not in creating[0].sources  # 成功作业不可重试


def test_assert_transition_allowed_rejects_off_table_moves() -> None:
    """表外迁移一律 409 ``STATE_CONFLICT``；表内迁移返回命中行（T6/T7 同形状故 2 行）。"""
    assert len(assert_transition_allowed("QUEUED", "RUNNING")) == 1
    assert len(assert_transition_allowed("RUNNING", "FAILED")) == 2  # T6 与 T7
    assert len(assert_transition_allowed("CANCEL_REQUESTED", "CANCELLED")) == 1
    for bad in [("QUEUED", "SUCCEEDED"), ("QUEUED", "FAILED"), ("CANCEL_REQUESTED", "SUCCEEDED")]:
        with pytest.raises(StateConflict):
            assert_transition_allowed(*bad)
    for terminal in sorted(TERMINAL_STATES):
        for target in JOB_STATES:
            matched = [t for t in TRANSITIONS if terminal in t.sources and t.target == target]
            if matched:
                # 唯一合法的终态出边是 T9：它新建一行，不改写终态行本身。
                assert all(t.creates_new_row for t in matched), matched
                assert terminal != "SUCCEEDED"
                assert target == "QUEUED"
            else:
                with pytest.raises(StateConflict):
                    assert_transition_allowed(terminal, target)


def test_state_and_kind_enums_match_live_contract() -> None:
    """6 个状态、10 个作业类型，取值直接来自活契约 DTO 的 Literal 参数。"""
    assert len(JOB_STATES) == 6
    assert set(JOB_STATES) == {
        "QUEUED",
        "RUNNING",
        "CANCEL_REQUESTED",
        "SUCCEEDED",
        "FAILED",
        "CANCELLED",
    }
    assert len(JOB_KINDS) == 10
    assert "VALIDATE_IMPORT" in JOB_KINDS and "EXPORT" in JOB_KINDS


def test_retryable_for_matrix() -> None:
    """design §3 末段的 ``retryable`` 口径逐格核对。"""
    assert retryable_for("CANCELLED") is True
    assert retryable_for("SUCCEEDED") is False
    for state in ("QUEUED", "RUNNING", "CANCEL_REQUESTED"):
        assert retryable_for(state) is False
    assert retryable_for("FAILED", "INTERNAL_ERROR") is True
    assert retryable_for("FAILED", None) is True
    for code in ("VALIDATION_ERROR", "INPUT_TOO_LARGE", "INVALID_SCOPE", "EVIDENCE_REQUIRED"):
        assert retryable_for("FAILED", code) is False, code


# ==================================================================== T1 QUEUED -> RUNNING


def test_t1_claim_queued_to_running(store: JobStore, clock: FixedClock) -> None:
    """T1（JOBS.md:11）：递增 attempt、生成随机 lease token、写 lease_until。"""
    queued = _enqueue(store)
    assert (queued.state, queued.attempt, queued.revision) == ("QUEUED", 0, 1)

    claim = store.claim_next(workspace_id=WS, now=clock.now())
    assert claim.claimed and claim.record is not None and claim.lease is not None
    row = claim.record
    assert row.state == "RUNNING"
    assert row.attempt == 1
    assert row.progress == 0
    assert row.stage == "CLAIMED"
    assert row.revision == 2
    assert row.lease_token is not None and len(row.lease_token) >= 32
    # 租约期限只能来自 compute_lease_deadline（A83）：这里用它做**期望值**，不是重算。
    assert row.lease_deadline == compute_lease_deadline(T0, lease_seconds=WORKER_LEASE_SECONDS)
    assert claim.lease.attempt == 1 and claim.lease.token == row.lease_token


def test_t1_claim_on_empty_queue_returns_none(store: JobStore, clock: FixedClock) -> None:
    """队列空时 ``claim_next`` 返回 ``Claim(claimed=False)`` 而不抛异常（design §3 T1）。"""
    claim = store.claim_next(workspace_id=WS, now=clock.now())
    assert claim.claimed is False and claim.contended is False


def test_t1_claims_earliest_first(store: JobStore, clock: FixedClock) -> None:
    """「事务内最早可认领」＝按 ``created_at, workspace_id, id`` 取队首。"""
    store.enqueue(
        workspace_id=WS,
        kind="COMPARE",
        input_json="{}",
        input_digest=DIGEST,
        now=T0 + timedelta(seconds=9),
        job_id="J-late",
    )
    store.enqueue(
        workspace_id=WS,
        kind="COMPARE",
        input_json="{}",
        input_digest=DIGEST,
        now=T0,
        job_id="J-early",
    )
    claim = store.claim_next(workspace_id=WS, now=clock.now())
    assert claim.record is not None and claim.record.id == "J-early"


# ================================================================== T2 QUEUED -> CANCELLED


def test_t2_cancel_queued_goes_straight_to_cancelled(
    store: JobStore, clock: FixedClock, engine: Engine
) -> None:
    """T2（JOBS.md:12）：排队中取消直接落终态、写审计、``retryable`` 置真。"""
    queued = _enqueue(store)
    row = store.request_cancel(
        workspace_id=WS,
        job_id=queued.id,
        revision=queued.revision,
        now=clock.now(),
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    assert row.state == "CANCELLED"
    assert row.lease_token is None and row.lease_deadline is None
    assert row.retryable is True
    assert row.revision == 2
    assert row.input_json == queued.input_json and row.input_digest == queued.input_digest
    assert _audit_rows(engine) == [("JOB_CANCEL_REQUESTED", "J-1", "ACCEPTED")]


def test_t2_cancel_missing_job_is_404(store: JobStore, clock: FixedClock) -> None:
    with pytest.raises(ResourceNotFound):
        store.request_cancel(
            workspace_id=WS,
            job_id="J-nope",
            revision=1,
            now=clock.now(),
            actor_id=ACTOR,
            request_id=REQUEST,
        )


def test_t2_cancel_stale_revision_is_412(store: JobStore, clock: FixedClock) -> None:
    """``If-Match`` 与当前 ``revision`` 不符 → 412 ``REVISION_CONFLICT``（design §6）。"""
    queued = _enqueue(store)
    with pytest.raises(RevisionConflict):
        store.request_cancel(
            workspace_id=WS,
            job_id=queued.id,
            revision=queued.revision + 7,
            now=clock.now(),
            actor_id=ACTOR,
            request_id=REQUEST,
        )
    untouched = store.get_job(workspace_id=WS, job_id=queued.id)
    assert untouched is not None and untouched.state == "QUEUED"  # 412 未改任何字段
    assert untouched.revision == queued.revision


# ======================================================================= T3 RUNNING 续租


def test_t3_renew_extends_lease_by_ttl_and_writes_progress(
    store: JobStore, clock: FixedClock
) -> None:
    """T3（JOBS.md:13）：租约到期＝当前时刻 + 30 秒，同时写阶段与进度。"""
    claim = _claim(store, clock)
    assert claim.lease is not None
    clock.advance(timedelta(seconds=5))
    result = store.renew(claim.lease, now=clock.now(), stage="LOADING", progress=40)
    assert result.renewed is True and result.record is not None
    assert result.record.lease_deadline == compute_lease_deadline(
        T0 + timedelta(seconds=5), lease_seconds=WORKER_LEASE_SECONDS
    )
    assert result.record.stage == "LOADING" and result.record.progress == 40
    assert result.record.state == "RUNNING"
    assert result.record.attempt == 1  # 续租不递增 attempt
    assert result.cancel_requested is False


def test_t3_renew_with_stale_lease_token_is_rejected(store: JobStore, clock: FixedClock) -> None:
    """**失效 lease token 的提交必须被拒**：改一位 token，续租即 ``renewed=False``。"""
    claim = _claim(store, clock)
    assert claim.record is not None and claim.lease is not None
    forged = replace(claim.lease, token="forged-token")
    result = store.renew(forged, now=clock.now(), stage="LOADING", progress=10)
    assert result.renewed is False and result.record is None
    fresh = store.get_job(workspace_id=WS, job_id=claim.record.id)
    assert fresh is not None
    assert fresh.stage == "CLAIMED" and fresh.progress == 0  # 一字未改


def test_t3_renew_reports_cancel_requested_without_extra_query(
    store: JobStore, clock: FixedClock
) -> None:
    """design §4 末条：续租顺带回读 ``state``，``CANCEL_REQUESTED`` 由 ``RenewResult`` 暴露。"""
    claim = _claim(store, clock)
    assert claim.record is not None and claim.lease is not None
    store.request_cancel(
        workspace_id=WS,
        job_id=claim.record.id,
        revision=claim.record.revision,
        now=clock.now(),
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    result = store.renew(claim.lease, now=clock.now(), stage="LOADING", progress=20)
    assert result.renewed is True
    assert result.cancel_requested is True
    assert result.record is not None and result.record.state == "CANCEL_REQUESTED"


# ============================================================== T4 RUNNING -> CANCEL_REQUESTED


def test_t4_cancel_running_keeps_lease_and_sets_cancel_requested(
    store: JobStore, clock: FixedClock, engine: Engine
) -> None:
    """T4（JOBS.md:14）：置 ``CANCEL_REQUESTED`` 并**保留**租约双列（DDL 双条件 CHECK）。"""
    claim = _claim(store, clock)
    assert claim.record is not None
    row = store.request_cancel(
        workspace_id=WS,
        job_id=claim.record.id,
        revision=claim.record.revision,
        now=clock.now(),
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    assert row.state == "CANCEL_REQUESTED"
    assert row.lease_token == claim.record.lease_token
    assert row.lease_deadline == claim.record.lease_deadline
    assert row.revision == 3
    assert _audit_rows(engine) == [("JOB_CANCEL_REQUESTED", "J-1", "ACCEPTED")]


def test_t4_second_cancel_request_is_409(store: JobStore, clock: FixedClock) -> None:
    """已 ``CANCEL_REQUESTED`` 再请求取消 → 409 ``STATE_CONFLICT``，不产生第二次 revision 跳。"""
    claim = _claim(store, clock)
    assert claim.record is not None
    store.request_cancel(
        workspace_id=WS,
        job_id=claim.record.id,
        revision=claim.record.revision,
        now=clock.now(),
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    with pytest.raises(StateConflict):
        store.request_cancel(
            workspace_id=WS,
            job_id=claim.record.id,
            revision=claim.record.revision + 1,
            now=clock.now(),
            actor_id=ACTOR,
            request_id=REQUEST,
        )


# ================================================================== T5 RUNNING -> SUCCEEDED


def test_t5_succeed_registers_artifact_in_same_transaction(
    store: JobStore, clock: FixedClock, engine: Engine
) -> None:
    """T5（JOBS.md:15）：登记制品与结果引用、**同事务**公开结果（design §3 T5）。"""
    claim = _claim(store, clock)
    assert claim.record is not None and claim.lease is not None
    artifact = ArtifactRecord(
        workspace_id=WS,
        id="A-1",
        kind="JOB_RESULT",  # A89：本裁定即 artifacts.kind 的权威来源
        sha256="a" * 64,
        relative_path="results/JOB_RESULT/ws-1/aa/" + "a" * 64,
        byte_size=12,
        created_at=T0.isoformat(),
    )
    row = store.succeed(
        claim.lease,
        result_ref=ObjectRef(kind="job", id=claim.record.id),  # A89 的断言口径
        now=clock.now(),
        artifacts=(artifact,),
    )
    assert row.state == "SUCCEEDED"
    assert row.progress == 100 and row.retryable is False
    assert row.lease_token is None and row.lease_deadline is None
    assert row.result_json is not None
    assert json.loads(row.result_json) == {"kind": "job", "id": "J-1"}
    assert row.problem_json is None
    with connect(engine) as conn:
        found = conn.execute(text("SELECT id, kind FROM artifacts")).all()
    assert [(str(a), str(b)) for a, b in found] == [("A-1", "JOB_RESULT")]


def test_t5_succeed_with_expired_lease_is_rejected(store: JobStore, clock: FixedClock) -> None:
    """AC-029「失效租约不能提交」：租约过期后连**成功**也不得发布（JOBS.md:21）。"""
    claim = _claim(store, clock)
    assert claim.record is not None and claim.lease is not None
    clock.advance(timedelta(seconds=WORKER_LEASE_SECONDS + 1))
    with pytest.raises(LeaseLost):
        store.succeed(
            claim.lease, result_ref=ObjectRef(kind="job", id=claim.record.id), now=clock.now()
        )
    fresh = store.get_job(workspace_id=WS, job_id=claim.record.id)
    assert fresh is not None and fresh.state == "RUNNING"  # 未被覆写


# ====================================================================== T6 RUNNING -> FAILED


def test_t6_fail_keeps_stage_and_problem_code(store: JobStore, clock: FixedClock) -> None:
    """T6（JOBS.md:16）：保留错误码与阶段；``VALIDATION_ERROR`` 属永久缺陷故 ``retryable`` 假。"""
    claim = _claim(store, clock)
    assert claim.record is not None and claim.lease is not None
    store.renew(claim.lease, now=clock.now(), stage="PARSING", progress=55)
    problem = problem_of(_validation_error("输入快照缺列"))
    row = store.fail(claim.lease, problem=problem, now=clock.now())
    assert row.state == "FAILED"
    assert row.stage == "PARSING" and row.progress == 55  # 阶段与进度被保留
    assert row.result_json is None
    assert row.retryable is False
    assert row.lease_token is None and row.lease_deadline is None
    assert row.problem_json is not None
    parsed = Problem.model_validate(json.loads(row.problem_json))
    assert parsed.code == "VALIDATION_ERROR" and parsed.status == 422


def test_t6_fail_retryable_defaults_follow_problem_code(store: JobStore, clock: FixedClock) -> None:
    """``retryable`` 缺省由 ``retryable_for`` 按 ``problem.code`` 现算（design §3 末段）。"""
    claim = _claim(store, clock)
    assert claim.record is not None and claim.lease is not None
    row = store.fail(claim.lease, problem=problem_of(_internal_error("计算失败")), now=clock.now())
    assert row.state == "FAILED" and row.retryable is True


# ============================================== T7 RUNNING -> FAILED（JOB_INTERRUPTED）


def test_t7_expired_running_is_marked_job_interrupted(store: JobStore, clock: FixedClock) -> None:
    """T7（JOBS.md:17）：超时租约且证据未提交 → FAILED，``issues[0].code='JOB_INTERRUPTED'``。

    A88③ 的形状断言全在这里：``Problem.code`` 必须是注册表内的 ``INTERNAL_ERROR``、
    ``status`` 必须 500，``JOB_INTERRUPTED`` **只能**出现在 ``issues[0].code``。
    """
    claim = _claim(store, clock)
    assert claim.record is not None
    assert claim.lease is not None
    store.renew(claim.lease, now=clock.now(), stage="SIMULATING", progress=70)
    clock.advance(timedelta(seconds=WORKER_LEASE_SECONDS + 1))

    reaped = store.reap_expired(now=clock.now())
    assert isinstance(reaped, Reaped) and reaped.interrupted == 1 and reaped.cancelled == 0

    row = store.get_job(workspace_id=WS, job_id=claim.record.id)
    assert row is not None and row.state == "FAILED"
    assert row.retryable is True
    assert row.stage == "SIMULATING" and row.progress == 70  # 保留阶段与进度
    assert row.lease_token is None and row.lease_deadline is None
    problem = Problem.model_validate(json.loads(row.problem_json or "{}"))
    assert problem.code == "INTERNAL_ERROR"
    assert problem.status == 500
    assert len(problem.issues) == 1
    assert problem.issues[0].code == JOB_INTERRUPTED
    assert JOB_INTERRUPTED not in problem.code


def test_t7_reap_never_touches_terminal_or_queued_rows(store: JobStore, clock: FixedClock) -> None:
    """JOBS.md:23「不重写已成功作业」：终态行与 QUEUED 行都不在扫描面内。"""
    done = _claim(store, clock, "J-done")
    assert done.record is not None and done.lease is not None
    store.succeed(done.lease, result_ref=ObjectRef(kind="job", id="J-done"), now=clock.now())
    _enqueue(store, "J-queued")
    snapshot_done = store.get_job(workspace_id=WS, job_id="J-done")
    snapshot_queued = store.get_job(workspace_id=WS, job_id="J-queued")

    clock.advance(timedelta(seconds=WORKER_LEASE_SECONDS * 3))
    reaped = store.reap_expired(now=clock.now())
    assert reaped == Reaped(interrupted=0, cancelled=0)
    assert store.get_job(workspace_id=WS, job_id="J-done") == snapshot_done
    assert store.get_job(workspace_id=WS, job_id="J-queued") == snapshot_queued


# ================================================== T8 CANCEL_REQUESTED -> CANCELLED


def test_t8_executor_confirmation_cancels_and_keeps_input(
    store: JobStore, clock: FixedClock, engine: Engine
) -> None:
    """T8 第一条入口（JOBS.md:18「执行确认」）：保留原输入，清 result/problem，写审计。"""
    claim = _claim(store, clock)
    assert claim.record is not None and claim.lease is not None
    store.request_cancel(
        workspace_id=WS,
        job_id=claim.record.id,
        revision=claim.record.revision,
        now=clock.now(),
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    row = store.confirm_cancel(claim.lease, now=clock.now(), actor_id=ACTOR, request_id=REQUEST)
    assert row.state == "CANCELLED"
    assert row.input_json == claim.record.input_json
    assert row.input_digest == claim.record.input_digest
    assert row.kind == claim.record.kind
    assert row.result_json is None and row.problem_json is None
    assert row.retryable is True
    assert row.lease_token is None and row.lease_deadline is None
    assert _audit_rows(engine) == [
        ("JOB_CANCEL_REQUESTED", "J-1", "ACCEPTED"),
        ("JOB_CANCELLED", "J-1", "ACCEPTED"),
    ]


def test_t8_lease_expiry_also_cancels(store: JobStore, clock: FixedClock) -> None:
    """T8 第二条入口（JOBS.md:18「租约到期」）：走 TX7，与执行确认同一终态。"""
    claim = _claim(store, clock)
    assert claim.record is not None
    store.request_cancel(
        workspace_id=WS,
        job_id=claim.record.id,
        revision=claim.record.revision,
        now=clock.now(),
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    clock.advance(timedelta(seconds=WORKER_LEASE_SECONDS + 1))
    reaped = store.reap_expired(now=clock.now())
    assert reaped == Reaped(interrupted=0, cancelled=1)
    row = store.get_job(workspace_id=WS, job_id=claim.record.id)
    assert row is not None and row.state == "CANCELLED" and row.retryable is True


def test_t8_confirm_cancel_after_expiry_is_rejected(store: JobStore, clock: FixedClock) -> None:
    """过期后执行者已失去发布权：``confirm_cancel`` 抛 ``LeaseLost``，由 TX7 代为收口。"""
    claim = _claim(store, clock)
    assert claim.record is not None and claim.lease is not None
    store.request_cancel(
        workspace_id=WS,
        job_id=claim.record.id,
        revision=claim.record.revision,
        now=clock.now(),
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    clock.advance(timedelta(seconds=WORKER_LEASE_SECONDS + 1))
    with pytest.raises(LeaseLost):
        store.confirm_cancel(claim.lease, now=clock.now(), actor_id=ACTOR, request_id=REQUEST)


# ================================================ T9 FAILED/CANCELLED -> 新 QUEUED 作业


def test_t9_retry_creates_new_queued_and_leaves_source_terminal(
    store: JobStore, clock: FixedClock, engine: Engine
) -> None:
    """T9（JOBS.md:19）：新建作业、``retry_of`` 指回源、同一输入快照；源终态一字不变。"""
    claim = _claim(store, clock)
    assert claim.record is not None and claim.lease is not None
    failed = store.fail(
        claim.lease, problem=problem_of(_internal_error("计算失败")), now=clock.now()
    )
    assert failed.state == "FAILED"

    clock.advance(timedelta(seconds=1))
    fresh = store.retry(
        workspace_id=WS,
        job_id=failed.id,
        revision=failed.revision,
        now=clock.now(),
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    assert fresh.id != failed.id
    assert fresh.retry_of == failed.id
    assert fresh.state == "QUEUED" and fresh.attempt == 0 and fresh.progress == 0
    assert fresh.revision == 1 and fresh.stage == "QUEUED"
    assert fresh.retryable is False
    assert fresh.kind == failed.kind
    assert fresh.input_json == failed.input_json  # 同一输入快照
    assert fresh.input_digest == failed.input_digest
    assert fresh.lease_token is None and fresh.lease_deadline is None
    assert fresh.result_json is None and fresh.problem_json is None

    source = store.get_job(workspace_id=WS, job_id=failed.id)
    assert source is not None
    assert source.state == "FAILED"  # 终态未被改写
    assert source.revision == failed.revision + 1  # 只 bump revision，让旧 If-Match 失效
    assert source.problem_json == failed.problem_json
    assert _audit_rows(engine)[-1] == ("JOB_RETRIED", fresh.id, "ACCEPTED")


def test_t9_retry_of_non_terminal_job_is_409(store: JobStore, clock: FixedClock) -> None:
    """design §6：源作业非 FAILED／CANCELLED（如 RUNNING／SUCCEEDED）→ 409 ``STATE_CONFLICT``。"""
    claim = _claim(store, clock)
    assert claim.record is not None
    with pytest.raises(StateConflict):
        store.retry(
            workspace_id=WS,
            job_id=claim.record.id,
            revision=claim.record.revision,
            now=clock.now(),
            actor_id=ACTOR,
            request_id=REQUEST,
        )


def test_t9_retry_stale_revision_is_412(store: JobStore, clock: FixedClock) -> None:
    claim = _claim(store, clock)
    assert claim.record is not None and claim.lease is not None
    failed = store.fail(
        claim.lease, problem=problem_of(_internal_error("计算失败")), now=clock.now()
    )
    with pytest.raises(RevisionConflict):
        store.retry(
            workspace_id=WS,
            job_id=failed.id,
            revision=failed.revision + 3,
            now=clock.now(),
            actor_id=ACTOR,
            request_id=REQUEST,
        )


def test_t9_retry_capacity_gate_is_429_with_retry_after(store: JobStore, clock: FixedClock) -> None:
    """A88②：待办＝**非终态**计数，达 ``JOB_PENDING_LIMIT`` 即 429 且带 ``Retry-After=3``。"""
    failed = _claim(store, clock, "J-seed")
    assert failed.record is not None and failed.lease is not None
    dead = store.fail(
        failed.lease, problem=problem_of(_internal_error("计算失败")), now=clock.now()
    )
    for index in range(JOB_PENDING_LIMIT):
        store.enqueue(
            workspace_id=WS,
            kind="COMPARE",
            input_json="{}",
            input_digest=DIGEST,
            now=clock.now(),
            job_id=f"J-fill-{index}",
        )
    assert store.pending_count(workspace_id=WS) == JOB_PENDING_LIMIT
    with pytest.raises(JobCapacity) as excinfo:
        store.retry(
            workspace_id=WS,
            job_id=dead.id,
            revision=dead.revision,
            now=clock.now(),
            actor_id=ACTOR,
            request_id=REQUEST,
        )
    assert excinfo.value.retry_after == JOB_CAPACITY_RETRY_AFTER_SECONDS
    assert excinfo.value.code == "JOB_CAPACITY" and excinfo.value.status == 429


def test_pending_count_ignores_terminal_states(store: JobStore, clock: FixedClock) -> None:
    """非终态口径的反面核对：终态作业不计入待办。"""
    claim = _claim(store, clock, "J-run")
    _enqueue(store, "J-queue")
    assert store.pending_count(workspace_id=WS) == 2
    assert claim.lease is not None
    store.succeed(claim.lease, result_ref=ObjectRef(kind="job", id="J-run"), now=clock.now())
    assert store.pending_count(workspace_id=WS) == 1


# ============================================================ 争用：取消 vs 完成（JOBS.md:23）


def test_cancel_then_complete_first_committer_wins(store: JobStore, clock: FixedClock) -> None:
    """取消已提交 → 后到的成功提交被拒，终态保持 CANCELLED（不得出现第二终态）。"""
    claim = _claim(store, clock)
    assert claim.record is not None and claim.lease is not None
    store.request_cancel(
        workspace_id=WS,
        job_id=claim.record.id,
        revision=claim.record.revision,
        now=clock.now(),
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    # 执行进程在安全分段确认取消（TX4 先提交）
    store.confirm_cancel(claim.lease, now=clock.now(), actor_id=ACTOR, request_id=REQUEST)
    with pytest.raises(LeaseLost):
        store.succeed(
            claim.lease, result_ref=ObjectRef(kind="job", id=claim.record.id), now=clock.now()
        )
    row = store.get_job(workspace_id=WS, job_id=claim.record.id)
    assert row is not None and row.state == "CANCELLED"
    assert row.result_json is None


def test_complete_then_cancel_loser_cannot_overwrite(store: JobStore, clock: FixedClock) -> None:
    """完成先提交 → 后到的取消请求 409，终态保持 SUCCEEDED。"""
    claim = _claim(store, clock)
    assert claim.record is not None and claim.lease is not None
    done = store.succeed(
        claim.lease, result_ref=ObjectRef(kind="job", id=claim.record.id), now=clock.now()
    )
    with pytest.raises(StateConflict):
        store.request_cancel(
            workspace_id=WS,
            job_id=done.id,
            revision=done.revision,
            now=clock.now(),
            actor_id=ACTOR,
            request_id=REQUEST,
        )
    assert store.get_job(workspace_id=WS, job_id=done.id) == done


# ============================================================== WorkerRunner（执行编排）


def _ok_handler() -> JobHandler:
    def handler(ctx: JobContext) -> JobOutcome:
        assert ctx.renew(stage="WORKING", progress=50).renewed is True
        if ctx.cancelled():
            return JobOutcome.cancelled(stage="WORKING")
        return JobOutcome.succeeded(ObjectRef(kind="job", id=ctx.job_id), stage="DONE")

    return handler


def test_runner_poll_once_drives_job_to_succeeded(store: JobStore, clock: FixedClock) -> None:
    _enqueue(store, "J-run")
    registry = HandlerRegistry({"COMPARE": _ok_handler()})
    runner = WorkerRunner(clock=clock, store=store, registry=registry)
    assert runner.poll_once(workspace_id=WS, now=clock.now()) == 1
    row = store.get_job(workspace_id=WS, job_id="J-run")
    assert row is not None and row.state == "SUCCEEDED"
    assert json.loads(row.result_json or "{}") == {"kind": "job", "id": "J-run"}
    assert row.stage == "WORKING" or row.progress == 100


def test_runner_unregistered_kind_fails_with_no_handler(store: JobStore, clock: FixedClock) -> None:
    """design §9：未注册 kind → TX6 失败（``VALIDATION_ERROR`` + ``NO_HANDLER``）。"""
    _enqueue(store, "J-orphan", kind="REPORT")
    runner = WorkerRunner(clock=clock, store=store, registry=HandlerRegistry())
    assert runner.poll_once(workspace_id=WS, now=clock.now()) == 1
    row = store.get_job(workspace_id=WS, job_id="J-orphan")
    assert row is not None and row.state == "FAILED" and row.retryable is False
    problem = Problem.model_validate(json.loads(row.problem_json or "{}"))
    assert problem.code == "VALIDATION_ERROR"
    assert problem.issues[0].code == "NO_HANDLER"


def test_runner_handler_exception_becomes_internal_error(
    store: JobStore, clock: FixedClock
) -> None:
    """handler 抛非领域异常 → 500 ``INTERNAL_ERROR``，且**不回显**异常文本（OPERATIONS.md:19）。"""

    def boom(ctx: JobContext) -> JobOutcome:
        raise RuntimeError("SELECT * FROM secrets")

    _enqueue(store, "J-boom")
    runner = WorkerRunner(clock=clock, store=store, registry=HandlerRegistry({"COMPARE": boom}))
    runner.poll_once(workspace_id=WS, now=clock.now())
    row = store.get_job(workspace_id=WS, job_id="J-boom")
    assert row is not None and row.state == "FAILED"
    problem = Problem.model_validate(json.loads(row.problem_json or "{}"))
    assert problem.code == "INTERNAL_ERROR" and problem.status == 500
    assert "secrets" not in json.dumps(problem.model_dump(mode="json"), ensure_ascii=False)


def test_runner_cancel_token_is_set_by_renew_readback(store: JobStore, clock: FixedClock) -> None:
    """design §4 末条：续租回读到 ``CANCEL_REQUESTED`` 即置 ``CancelToken``，handler 提前收口。"""
    seen: dict[str, bool] = {}

    def cancellable(ctx: JobContext) -> JobOutcome:
        ctx.renew(stage="STEP-1", progress=10)
        seen["after_first"] = ctx.cancelled()
        result = ctx.renew(stage="STEP-2", progress=20)
        seen["cancel_requested"] = result.cancel_requested
        seen["after_second"] = ctx.cancelled()
        return JobOutcome.cancelled(stage="STEP-2") if ctx.cancelled() else JobOutcome.cancelled()

    _enqueue(store, "J-cancel")

    # 时序由**显式调用顺序**构造，不靠 sleep：先认领，再由「操作员」请求取消，
    # 最后跑 handler —— handler 的第一次续租就会回读到 CANCEL_REQUESTED。
    claim = store.claim_next(workspace_id=WS, now=clock.now())
    assert claim.record is not None
    store.request_cancel(
        workspace_id=WS,
        job_id=claim.record.id,
        revision=claim.record.revision,
        now=clock.now(),
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    assert claim.lease is not None
    ctx = JobContext(record=claim.record, lease=claim.lease, store=store, clock=clock)
    outcome = cancellable(ctx)
    assert outcome.state == "CANCELLED"
    assert seen == {"after_first": True, "cancel_requested": True, "after_second": True}
    row = store.confirm_cancel(claim.lease, now=clock.now(), actor_id=ACTOR, request_id=REQUEST)
    assert row.state == "CANCELLED"


def test_runner_recover_marks_interrupted_and_reports(store: JobStore, clock: FixedClock) -> None:
    notes: list[str] = []
    claim = _claim(store, clock, "J-crash")
    runner = WorkerRunner(clock=clock, store=store, registry=HandlerRegistry(), logger=notes.append)
    clock.advance(timedelta(seconds=WORKER_LEASE_SECONDS + 1))
    reaped = runner.recover()
    assert reaped.interrupted == 1
    assert any("interrupted=1" in note for note in notes)
    assert claim.record is not None


def test_runner_run_forever_uses_injected_sleeper_and_stop(
    store: JobStore, clock: FixedClock
) -> None:
    """循环不起线程、不用真实 ``sleep``：``sleeper`` 与 ``stop`` 都由调用方注入。"""
    _enqueue(store, "J-loop")
    slept: list[float] = []
    calls = {"n": 0}

    def stop() -> bool:
        calls["n"] += 1
        return calls["n"] > 2

    runner = WorkerRunner(
        clock=clock,
        store=store,
        registry=HandlerRegistry({"COMPARE": _ok_handler()}),
        sleeper=slept.append,
    )
    handled = runner.run_forever(workspace_id=WS, stop=stop, max_rounds=2)
    assert handled == 1
    assert len(slept) == 2 and all(value > 0 for value in slept)
    row = store.get_job(workspace_id=WS, job_id="J-loop")
    assert row is not None and row.state == "SUCCEEDED"


def test_cancel_token_is_thread_safe_and_idempotent() -> None:
    token = CancelToken()
    assert token.cancelled() is False
    token.request()
    token.request()
    assert token.cancelled() is True


def test_handler_registry_rejects_unknown_kind() -> None:
    registry = HandlerRegistry()
    with pytest.raises(ValueError):
        registry.register("NOT_A_KIND", lambda ctx: JobOutcome.cancelled())
    for kind in JOB_KINDS:
        registry.register(kind, lambda ctx: JobOutcome.cancelled())
    assert len(registry) == len(JOB_KINDS)
    assert "COMPARE" in registry
    assert registry.kinds()[0] == "COMPARE"


def _validation_error(detail: str) -> DomainError:
    return ValidationFailure(detail)


def _internal_error(detail: str) -> DomainError:
    return InternalFailure(detail)
