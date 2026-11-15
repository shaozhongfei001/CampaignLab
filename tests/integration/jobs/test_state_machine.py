"""M0-04/S5 · T1–T9 状态机矩阵（design §3 转移表 ＋ §4 TX1–TX8 的逐条落库证据）。

判据口径（派单 §4.1）：每条 ``test_t<N>_*`` ①走**真实的** ``JobStore`` 公开方法
（A81：``jobs`` 表的 DML 文本禁入测试件，前置状态一律由 ``enqueue``／``claim_next``／
``request_cancel`` 等公开口构造）；②断言迁移**前**与**后**的行快照，至少含
``state``／``revision``／``attempt``，T3／T7／T8 另含租约到期列（``JobRecord`` 的
Python 侧字段名 ``lease_deadline``，即 DDL 的 ``lease_until``），T9 另证新行 id
不等于旧行 id 且 ``retry_of`` 指回旧行；③参数化 id 含 ``T1``…``T9`` 字样（§8-V2
逐条取证）。

转移矩阵本身不在本文件复制（A115：符号面判据走集合对撞，权威在
``worker/states.py::TRANSITIONS``）；本文件只做「按矩阵逐条落库」的行为证据。
时间流逝一律经 ``advance_clock``（红线 3／D-045：本文件无任何流逝字面量）。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import Engine

from campaignlab.api.common import PROBLEM_CODES, Problem, canonical_json
from campaignlab.clock import FixedClock
from campaignlab.infra.db.repositories import JobRecord
from campaignlab.worker.leases import Lease
from campaignlab.worker.runner import HandlerRegistry, JobContext
from campaignlab.worker.store import JobStore

KIND: str = "VALIDATE_IMPORT"
INPUT_JSON: str = "{}"
INPUT_DIGEST: str = "0" * 64
ACTOR: str = "s5-tester"


def _enqueue(store: JobStore, clock: FixedClock, workspace_id: str, job_id: str) -> JobRecord:
    """经 ``JobStore.enqueue`` 公开口落一条 QUEUED（A81 合规的唯一前置构造）。"""
    return store.enqueue(
        workspace_id=workspace_id,
        kind=KIND,
        input_json=INPUT_JSON,
        input_digest=INPUT_DIGEST,
        now=clock.now(),
        job_id=job_id,
    )


def _snap(store: JobStore, workspace_id: str, job_id: str) -> tuple[str, int, int, str | None]:
    """迁移前后共用的行快照：``(state, revision, attempt, lease_until 列)``。"""
    record = store.get_job(workspace_id=workspace_id, job_id=job_id)
    assert record is not None
    return record.state, record.revision, record.attempt, record.lease_deadline


def _seed_workspace(db_path: Path, workspace_id: str, created_at: str) -> None:
    """Insert the workspace row (S4 Harness.seed_workspace pattern; A81 covers jobs only)."""
    raw = sqlite3.connect(db_path)
    try:
        raw.execute(
            "INSERT INTO workspaces(id, name, source_class, authorization_note, revision,"
            " created_at) VALUES (?, ?, ?, NULL, 1, ?)",
            (workspace_id, f"ws-{workspace_id}", "SYNTHETIC", created_at),
        )
        raw.commit()
    finally:
        raw.close()


def _problem(code: str, request_id: str) -> Problem:
    """按活契约注册表构造 ``Problem``（D-019：code 只取权威 20 码，禁发明）。"""
    registry = PROBLEM_CODES[code]
    return Problem(
        type=registry[1],
        title=registry[2],
        status=registry[0],
        code=code,
        issues=[],
        detail="s5 状态机用例",
        request_id=request_id,
    )


@pytest.mark.parametrize("scenario", ["earliest-queued-first"], ids=["T1-earliest-queued-first"])
def test_t1_claim_queued_to_running(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    scenario: str,
) -> None:
    """T1：事务内最早可认领 ⇒ QUEUED→RUNNING（TX1，守卫 ``state+revision``）。"""
    ws = "ws-t1"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-aaaa")
    _enqueue(job_store, fixed_clock, ws, "j-bbbb")
    before = _snap(job_store, ws, "j-aaaa")
    assert before[0] == "QUEUED"
    assert before[1] == 1
    assert before[2] == 0
    assert before[3] is None

    claim = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    assert claim.record is not None
    assert claim.lease is not None
    assert claim.record.id == "j-aaaa"

    after = _snap(job_store, ws, "j-aaaa")
    assert after[0] == "RUNNING"
    assert after[1] == 2
    assert after[2] == 1
    assert after[3] is not None
    assert _snap(job_store, ws, "j-bbbb")[0] == "QUEUED"


@pytest.mark.parametrize(
    "scenario", ["queued-direct-cancelled"], ids=["T2-queued-direct-cancelled"]
)
def test_t2_cancel_queued_to_cancelled(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    scenario: str,
) -> None:
    """T2：请求取消命中 QUEUED ⇒ 直接终态 CANCELLED（TX3，守卫 ``state+revision``）。"""
    ws = "ws-t2"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-t2")
    before = _snap(job_store, ws, "j-t2")
    assert before == ("QUEUED", 1, 0, None)

    job_store.request_cancel(
        workspace_id=ws,
        job_id="j-t2",
        revision=before[1],
        now=fixed_clock.now(),
        actor_id=ACTOR,
        request_id="req-t2",
    )
    after = _snap(job_store, ws, "j-t2")
    assert after[0] == "CANCELLED"
    assert after[1] == 2
    assert after[2] == 0
    assert after[3] is None


@pytest.mark.parametrize(
    ("scenario", "extra_seconds"),
    [("renew-extends-lease", 10), ("stale-lease-rejected", 10)],
    ids=["T3-renew-extends-lease", "T3-stale-lease-rejected"],
)
def test_t3_renew_keeps_running_and_extends_lease(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    advance_clock: object,
    scenario: str,
    extra_seconds: int,
) -> None:
    """T3：每 5 秒续租 ⇒ RUNNING→RUNNING（TX2，守卫 ``attempt+lease_token+state``）。

    两例：正路证「到期列被向后推进而其余快照不变」；反路证「过期身份（attempt 不符）
    的续租被守卫拒掉」——同一条谓词的两个分支都要有牙。
    """
    ws = "ws-t3"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-t3")
    claim = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    assert claim.lease is not None
    before = _snap(job_store, ws, "j-t3")
    assert before[0] == "RUNNING"

    assert callable(advance_clock)
    from campaignlab.worker.leases import is_expired

    if scenario == "renew-extends-lease":
        now = advance_clock(extra_seconds)
        result = job_store.renew(claim.lease, now=now, stage="s5-probe", progress=40)
        assert result.renewed is True
        after = _snap(job_store, ws, "j-t3")
        assert after[0] == "RUNNING"
        assert after[2] == 1
        assert after[3] is not None and before[3] is not None
        assert after[3] > before[3]
        assert not is_expired(after[3], now=now)
    else:
        now = fixed_clock.now()
        stale = Lease(
            workspace_id=ws,
            job_id="j-t3",
            attempt=99,
            token="stale-token-s5",
            deadline=claim.lease.deadline,
        )
        result = job_store.renew(stale, now=now, stage="s5-probe", progress=40)
        assert result.renewed is False
        after = _snap(job_store, ws, "j-t3")
        assert after == before


@pytest.mark.parametrize(
    "scenario", ["running-cancel-keeps-lease"], ids=["T4-running-cancel-keeps-lease"]
)
def test_t4_running_to_cancel_requested(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    scenario: str,
) -> None:
    """T4：请求取消命中 RUNNING ⇒ CANCEL_REQUESTED（TX3；租约双列必须仍在）。"""
    ws = "ws-t4"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-t4")
    job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    record = job_store.get_job(workspace_id=ws, job_id="j-t4")
    assert record is not None
    before = _snap(job_store, ws, "j-t4")
    assert before[0] == "RUNNING"
    assert before[3] is not None

    job_store.request_cancel(
        workspace_id=ws,
        job_id="j-t4",
        revision=record.revision,
        now=fixed_clock.now(),
        actor_id=ACTOR,
        request_id="req-t4",
    )
    after = _snap(job_store, ws, "j-t4")
    assert after[0] == "CANCEL_REQUESTED"
    assert after[1] == before[1] + 1
    assert after[2] == before[2]
    assert after[3] is not None


@pytest.mark.parametrize("scenario", ["valid-lease-succeeds"], ids=["T5-valid-lease-succeeds"])
def test_t5_succeed_with_valid_lease(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    registry_with_stub: HandlerRegistry,
    scenario: str,
) -> None:
    """T5：成功且租约仍有效 ⇒ RUNNING→SUCCEEDED（TX5；``result_ref`` 口径见 N8／A89）。

    断言 ``result_json`` 恰等于 ``ObjectRef(kind='job', id=<job_id>)`` 的
    ``canonical_json`` 序列化（A73：键序稳定）；随后再以同一租约提交必须被拒
    （终态后守卫 ``state IN ('RUNNING','CANCEL_REQUESTED')`` 不再命中）。
    ``registry_with_stub`` 的桩即本条取证所依赖的 ``kind`` 提供方（§3）。
    """
    ws = "ws-t5"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-t5")
    claim = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    assert claim.lease is not None
    assert claim.record is not None

    before = _snap(job_store, ws, "j-t5")
    assert before[0] == "RUNNING"

    handler = registry_with_stub.get(KIND)
    assert handler is not None
    ctx = JobContext(
        record=claim.record,
        lease=claim.lease,
        store=job_store,
        clock=fixed_clock,
    )
    outcome = handler(ctx)
    assert outcome.state == "SUCCEEDED"
    assert outcome.result_ref is not None
    assert outcome.result_ref.kind == "job"
    assert outcome.result_ref.id == "j-t5"
    result_ref = outcome.result_ref
    record = job_store.succeed(claim.lease, result_ref=result_ref, now=fixed_clock.now())
    assert record.state == "SUCCEEDED"

    after = _snap(job_store, ws, "j-t5")
    assert after[0] == "SUCCEEDED"
    assert after[2] == 1
    assert after[3] is None
    fresh = job_store.get_job(workspace_id=ws, job_id="j-t5")
    assert fresh is not None
    assert fresh.result_json == canonical_json(result_ref.model_dump(mode="json"))

    from campaignlab.worker.errors import LeaseLost

    with pytest.raises(LeaseLost):
        job_store.succeed(claim.lease, result_ref=result_ref, now=fixed_clock.now())


@pytest.mark.parametrize(
    ("scenario", "code", "expect_retryable"),
    [
        ("retryable-internal-error", "INTERNAL_ERROR", True),
        ("permanent-validation-error", "VALIDATION_ERROR", False),
    ],
    ids=["T6-retryable-internal-error", "T6-permanent-validation-error"],
)
def test_t6_fail_known_problem(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    scenario: str,
    code: str,
    expect_retryable: bool,
) -> None:
    """T6：已知失败 ⇒ RUNNING→FAILED（TX6；``retryable`` 由 design §3 口径现算）。

    ``VALIDATION_ERROR`` 属永久性输入缺陷（``NON_RETRYABLE_PROBLEM_CODES``）⇒ 落 0；
    ``INTERNAL_ERROR`` 不在该集合 ⇒ 落 1。守卫与 T5 逐字相同。
    """
    ws = "ws-t6"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-t6")
    claim = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    assert claim.lease is not None
    before = _snap(job_store, ws, "j-t6")
    assert before[0] == "RUNNING"

    job_store.fail(
        claim.lease,
        problem=_problem(code, "req-t6"),
        now=fixed_clock.now(),
    )
    after = _snap(job_store, ws, "j-t6")
    assert after[0] == "FAILED"
    assert after[2] == 1
    assert after[3] is None
    record = job_store.get_job(workspace_id=ws, job_id="j-t6")
    assert record is not None
    assert record.retryable is expect_retryable
    assert record.problem_json is not None


@pytest.mark.parametrize("scenario", ["lease-expiry-reap"], ids=["T7-lease-expiry-reap"])
def test_t7_reap_expired_running_to_failed(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    advance_clock: object,
    scenario: str,
) -> None:
    """T7：超时租约且证据未提交 ⇒ RUNNING→FAILED（TX7，守卫 ``lease_until < :now``）。

    到期分支必须真的依赖 ``advance_clock``：先把时钟推进过 ``lease_until``，
    ``reap_expired`` 才收口。中断 Problem 形状由 A88③ 钉死：``code='INTERNAL_ERROR'``、
    ``issues[0].code='JOB_INTERRUPTED'``（后者禁进 ``Problem.code``，N7③）。
    """
    import json

    from campaignlab.worker.leases import is_expired

    assert callable(advance_clock)
    ws = "ws-t7"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-t7")
    job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    before = _snap(job_store, ws, "j-t7")
    assert before[0] == "RUNNING"
    assert before[3] is not None

    now = advance_clock(31)
    assert is_expired(before[3], now=now)

    reaped = job_store.reap_expired(now=now)
    assert reaped.interrupted == 1
    assert reaped.cancelled == 0

    after = _snap(job_store, ws, "j-t7")
    assert after[0] == "FAILED"
    assert after[3] is None
    record = job_store.get_job(workspace_id=ws, job_id="j-t7")
    assert record is not None and record.problem_json is not None
    problem = json.loads(record.problem_json)
    assert problem["code"] == "INTERNAL_ERROR"
    assert problem["issues"][0]["code"] == "JOB_INTERRUPTED"


@pytest.mark.parametrize(
    "path",
    ["executor-confirm", "expiry-reap"],
    ids=["T8-executor-confirm", "T8-expiry-reap"],
)
def test_t8_cancel_requested_to_cancelled(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    advance_clock: object,
    path: str,
) -> None:
    """T8：CANCEL_REQUESTED→CANCELLED 的两条入口（TX4 执行确认／TX7 租约到期）。"""
    from campaignlab.worker.leases import is_expired

    assert callable(advance_clock)
    ws = "ws-t8"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-t8")
    claim = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    assert claim.lease is not None
    record = job_store.get_job(workspace_id=ws, job_id="j-t8")
    assert record is not None
    job_store.request_cancel(
        workspace_id=ws,
        job_id="j-t8",
        revision=record.revision,
        now=fixed_clock.now(),
        actor_id=ACTOR,
        request_id="req-t8",
    )
    before = _snap(job_store, ws, "j-t8")
    assert before[0] == "CANCEL_REQUESTED"
    assert before[3] is not None

    if path == "executor-confirm":
        mid = job_store.get_job(workspace_id=ws, job_id="j-t8")
        assert mid is not None
        job_store.confirm_cancel(
            Lease.of(mid),
            now=fixed_clock.now(),
            actor_id=ACTOR,
            request_id="req-t8-confirm",
        )
    else:
        now = advance_clock(31)
        assert is_expired(before[3], now=now)
        reaped = job_store.reap_expired(now=now)
        assert reaped.cancelled == 1
        assert reaped.interrupted == 0

    after = _snap(job_store, ws, "j-t8")
    assert after[0] == "CANCELLED"
    assert after[2] == 1
    assert after[3] is None


@pytest.mark.parametrize(
    ("scenario", "source"),
    [("from-failed", "FAILED"), ("from-cancelled", "CANCELLED")],
    ids=["T9-retry-from-failed", "T9-retry-from-cancelled"],
)
def test_t9_retry_creates_new_queued(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    scenario: str,
    source: str,
) -> None:
    """T9：操作员重试 ⇒ FAILED／CANCELLED→**新行** QUEUED（TX8，``creates_new_row``）。"""
    ws = "ws-t9"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-t9")
    if source == "FAILED":
        claim = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
        assert claim.lease is not None
        job_store.fail(
            claim.lease,
            problem=_problem("INTERNAL_ERROR", "req-t9-source"),
            now=fixed_clock.now(),
        )
    else:
        job_store.request_cancel(
            workspace_id=ws,
            job_id="j-t9",
            revision=1,
            now=fixed_clock.now(),
            actor_id=ACTOR,
            request_id="req-t9-source",
        )
    old = job_store.get_job(workspace_id=ws, job_id="j-t9")
    assert old is not None
    assert old.state == source
    old_revision = old.revision

    new = job_store.retry(
        workspace_id=ws,
        job_id="j-t9",
        revision=old_revision,
        now=fixed_clock.now(),
        actor_id=ACTOR,
        request_id="req-t9-retry",
    )
    assert new.id != old.id
    assert new.state == "QUEUED"
    assert new.attempt == 0
    assert new.revision == 1
    assert new.retry_of == old.id
    assert new.kind == old.kind
    assert new.input_digest == old.input_digest
    assert new.input_json == old.input_json

    kept = job_store.get_job(workspace_id=ws, job_id="j-t9")
    assert kept is not None
    assert kept.state == source
    assert kept.revision == old_revision + 1
