"""M0-04/S6 (R18) · jobs 租约争用的集成残差面（派单 §3.A 的「残差」列逐名落地）。

对应判据（派单 §4）：V1 ``pytest -q tests/integration/jobs -k lease`` —— 本目录既有 5 例，
本文件新增 6 个函数、净新增 9 例 collected（``test_cancel_vs_complete_first_commit_wins``
按 (a)/(b) 双向参数化 ×2，``test_terminal_state_is_immutable`` 按三个终态参数化 ×3）。
``test_interrupted_job_marked_job_interrupted``（§3.A 第 3 名）已于第 2 轮按 U-1 终裁落地
（采纳候选 (a)）：实测落库 ``jobs.problem_json`` 的 ``issues[0]`` 键集恰为契约冻结的 4 字段
（``Issue`` 为 ``extra="forbid"``，无 ``retryable`` 槽位），原派单文该断言形态经编排器终裁
判为其派单文缺陷（A88 在册仅 ①②③，无 ④）；本例改钉可满足的真残差：
``problem["status"] == 500``、``problem["code"] != JOB_INTERRUPTED``（标签用 import 常量）、
行级 ``record.retryable is True``（``retryable`` 的真实落点在 jobs 行列）。

A243 重切依据：design §9-S6 的 ``test_artifact.py`` 6 名里 5 名已被同目录同层
``test_artifact_write.py`` 完整覆盖（判重豁免映射见派单 §3.B 与回执 COVERAGE_MAP_3B），
真缺口 1 名落在 ``test_artifact.py``；本文件承担 ``test_lease.py`` 的其余名字。
每例 docstring 标注「既有覆盖 vs 本例残差」，禁重复既有断言。

时钟纪律（红线 1）：一切时间流逝只经 ``fixed_clock`` / ``advance_clock``；本文件不含
sleep、系统单调读数或系统当前时刻参与判定。TTL 一律 import ``LEASE_TTL_SECONDS``，断言里
禁写秒数字面量（D-012 / D-014）——``test_renew_extends_lease_by_30s`` 名字里的秒数是
design 冻结的规格名（逐字来自 §3.A），不是断言字面量。
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from campaignlab.api.common import PROBLEM_CODES, ObjectRef, Problem
from campaignlab.clock import FixedClock
from campaignlab.domain.errors import DomainError, StateConflict
from campaignlab.worker.errors import JOB_INTERRUPTED, LeaseLost
from campaignlab.worker.leases import LEASE_TTL_SECONDS, Lease, deadline_after
from campaignlab.worker.store import JobStore

KIND: str = "VALIDATE_IMPORT"
INPUT_JSON: str = "{}"
INPUT_DIGEST: str = "0" * 64
ACTOR: str = "s6-tester"


def _seed_workspace(db_path: Path, workspace_id: str, created_at: str) -> None:
    """前置 workspaces 行（A81 只禁 jobs DML；体例照 T 文件同名私有件）。"""
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


def _enqueue(store: JobStore, clock: FixedClock, workspace_id: str, job_id: str) -> None:
    """经 ``JobStore.enqueue`` 公开口落一条 QUEUED（A81 合规的唯一前置构造）。"""
    store.enqueue(
        workspace_id=workspace_id,
        kind=KIND,
        input_json=INPUT_JSON,
        input_digest=INPUT_DIGEST,
        now=clock.now(),
        job_id=job_id,
    )


def _snap6(
    store: JobStore, workspace_id: str, job_id: str
) -> tuple[str, int, int, str | None, str | None, str | None]:
    """逐字段行快照：``(state, attempt, revision, lease_until 列, problem_json, result_json)``。"""
    record = store.get_job(workspace_id=workspace_id, job_id=job_id)
    assert record is not None
    return (
        record.state,
        record.attempt,
        record.revision,
        record.lease_deadline,
        record.problem_json,
        record.result_json,
    )


def _problem(code: str = "INTERNAL_ERROR") -> Problem:
    """按活契约注册表构造 ``Problem``（D-019：code 只取权威 20 码，禁发明）。"""
    registry = PROBLEM_CODES[code]
    return Problem(
        type=registry[1],
        title=registry[2],
        status=registry[0],
        code=code,
        issues=[],
        detail="s6 租约争用用例",
        request_id="req-s6",
    )


def _audit_count(db_path: Path, workspace_id: str) -> int:
    """审计行数（只读 SELECT；供「先提交者定终态」把审计行数一并钉住）。"""
    raw = sqlite3.connect(db_path)
    try:
        row = raw.execute(
            "SELECT COUNT(*) FROM audit WHERE workspace_id = ?", (workspace_id,)
        ).fetchone()
        return int(row[0])
    finally:
        raw.close()


def test_two_claimers_only_one_wins(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
) -> None:
    """双认领恰一个赢。既有覆盖：仅单元层 ``tests/unit/test_job_repository_terminal.py:361``；
    集成层 ``-k lease`` 既有 5 例（T3×2/T4/T5/T7）无一涉及双认领。

    本例残差：同一 ``JobStore`` 先后两次 ``claim_next`` 争抢同一条 QUEUED —— 恰一个
    ``claimed is True``；败者 ``claimed is False`` 且 ``record``/``lease`` 双空，DB 侧该行
    ``state=='RUNNING'``、``attempt==1``、``lease_token`` 仍是胜者那一个（败者没换掉令牌）。
    ``contended`` 实测语义（派单 §3.A#1 要求如实入档，见回执 U-2）：它是 SQLite **写锁物理
    争用**（``OperationalError`` 翻译）的信号，串行调用下恒为 ``False``；本例只钉串行面
    可见事实（两个 ``contended`` 都是 False），不为过测改造构造、不改动任何期望。
    """
    ws = "ws-s6-two-claimers"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-two")

    first = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    second = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())

    assert first.claimed is True
    assert first.record is not None and first.lease is not None
    assert first.record.id == "j-two"
    assert second.claimed is False
    assert second.record is None
    assert second.lease is None

    row = job_store.get_job(workspace_id=ws, job_id="j-two")
    assert row is not None
    assert row.state == "RUNNING"
    assert row.attempt == 1
    assert row.lease_token is not None
    assert row.lease_token == first.lease.token

    assert first.contended is False
    assert second.contended is False


def test_expired_lease_token_commit_rejected(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    advance_clock: Callable[[int], datetime],
) -> None:
    """过期租约（非终态路径）的提交必须被拒。既有覆盖：集成层 T5 尾部
    （``test_state_machine.py:290-293``）只覆盖「终态后同租约再 ``succeed``」；T3 反路只覆盖
    「``attempt=99`` 陈旧身份 ``renew`` → ``renewed is False``」；单元层
    ``tests/unit/test_worker_runner.py:440`` 是 runner 级。

    本例残差：``claim_next`` → ``advance_clock(31)``（推过租约的整秒入参，31 大于
    ``LEASE_TTL_SECONDS``，不是 TTL 断言字面量）→ ``succeed`` 抛 ``LeaseLost``
    （AC-029 的过期前置判定在开事务之前拒），且 DB 侧该行**仍为 RUNNING**、``lease_until``
    未被改写；再以 token/attempt 不匹配、自身 deadline 尚未过期的 ``Lease`` 调 ``fail``
    ——走守卫 ``rowcount == 0`` 分支——同样 ``LeaseLost``，行快照逐字段不变。
    """
    ws = "ws-s6-expired"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-exp")
    claim = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    assert claim.lease is not None
    lease = claim.lease
    before = _snap6(job_store, ws, "j-exp")
    assert before[0] == "RUNNING"

    now = advance_clock(31)  # 推过租约：31 > LEASE_TTL_SECONDS（TTL 值由 import 对照，禁在此重写）

    with pytest.raises(LeaseLost):
        job_store.succeed(lease, result_ref=ObjectRef(kind="job", id="j-exp"), now=now)

    row = job_store.get_job(workspace_id=ws, job_id="j-exp")
    assert row is not None
    assert row.state == "RUNNING"
    assert row.lease_deadline == lease.deadline

    stale = Lease(
        workspace_id=ws,
        job_id="j-exp",
        attempt=99,
        token="s6-stale-token",
        deadline=deadline_after(now, lease_seconds=LEASE_TTL_SECONDS),
    )
    with pytest.raises(LeaseLost):
        job_store.fail(stale, problem=_problem(), now=now)

    assert _snap6(job_store, ws, "j-exp") == before


def test_interrupted_job_marked_job_interrupted(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    advance_clock: Callable[[int], datetime],
) -> None:
    """中断作业的 Problem 形状残差 ＋ 行级 retryable。既有覆盖：集成层 T7
    （``test_state_machine.py:342-383``）已钉 ``FAILED`` / ``reaped.interrupted == 1`` /
    ``reaped.cancelled == 0`` / ``lease_until`` 清空 / ``problem["code"] == "INTERNAL_ERROR"``
    / ``issues[0]["code"] == "JOB_INTERRUPTED"`` 六项——状态与 code / issues[0].code 由 T7
    覆盖，本例只补形状残差与行级 retryable，不重复断言那六项。

    本例残差断言（U-1 终裁版）：``problem["status"] == 500``；``problem["code"] !=
    JOB_INTERRUPTED``（N7③，标签常量 import 自 ``worker.errors``，禁自造字符串）；行级
    ``record.retryable is True``（经 ``get_job`` 读行，``retryable`` 的真实落点是 jobs 行，
    ``fail_expired_running`` 注释原文「中断是可重试的原型场景」）。**不**断言
    ``issues[0]["retryable"]``——该键在契约 ``extra="forbid"`` 下不可能存在。时间流逝
    只经 ``advance_clock``；不跨层 import 单元测试私有 helper。
    """
    ws = "ws-s6-interrupted"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-int")
    job_store.claim_next(workspace_id=ws, now=fixed_clock.now())

    now = advance_clock(31)  # 推过租约：31 > LEASE_TTL_SECONDS（TTL 由 import 对照）
    job_store.reap_expired(now=now)

    record = job_store.get_job(workspace_id=ws, job_id="j-int")
    assert record is not None
    assert record.retryable is True
    assert record.problem_json is not None
    problem = json.loads(record.problem_json)
    assert problem["status"] == 500
    assert problem["code"] != JOB_INTERRUPTED


@pytest.mark.parametrize(
    "direction",
    ["cancel-first", "complete-first"],
    ids=["CVC-a-cancel-first", "CVC-b-complete-first"],
)
def test_cancel_vs_complete_first_commit_wins(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    direction: str,
) -> None:
    """取消与完成争用：先提交者定终态（集成层双向）。既有覆盖：仅单元层
    ``tests/unit/test_worker_runner.py:712``；集成层 T4 只到 ``CANCEL_REQUESTED``、
    T8 只做 executor confirm / expiry reap，无争用。

    本例残差（真实迁移库 ＋ ``JobStore``，(a)/(b) 参数化成两条独立取证行）：
    (a) ``request_cancel`` 命中 RUNNING 后执行者再 ``succeed``：store 的真实守卫
    ``state IN ('RUNNING','CANCEL_REQUESTED')`` 允许从 ``CANCEL_REQUESTED`` 提交成功
    （JOBS.md:23「先成功提交的合法状态决定结果」）——取消**请求**不是终态提交，先**定终态**
    的一方赢 ⇒ 终态 SUCCEEDED，``revision`` 递进链 1→2→3→4 与审计行数（1 条
    ``JOB_CANCEL_REQUESTED``）一并钉住；败者 ``confirm_cancel`` → ``LeaseLost``、审计不增。
    (b) ``succeed`` 先行后 ``confirm_cancel`` → ``LeaseLost``，终态与快照逐字段不变、零审计；
    追加 ``request_cancel`` → ``StateConflict``（实测类型，终态不可再请求取消）。
    实测两向语义与卡片「取消/完成只有一个终态」互洽（每行恰一个终态提交），无需 U。
    """
    ws = f"ws-s6-cvc-{direction}"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-cvc")
    claim = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    assert claim.lease is not None
    assert claim.record is not None
    assert claim.record.revision == 2
    lease = claim.lease

    if direction == "cancel-first":
        cur = job_store.get_job(workspace_id=ws, job_id="j-cvc")
        assert cur is not None
        job_store.request_cancel(
            workspace_id=ws,
            job_id="j-cvc",
            revision=cur.revision,
            now=fixed_clock.now(),
            actor_id=ACTOR,
            request_id="req-s6-a",
        )
        mid = _snap6(job_store, ws, "j-cvc")
        assert mid[0] == "CANCEL_REQUESTED"
        assert mid[2] == 3

        record = job_store.succeed(
            lease, result_ref=ObjectRef(kind="job", id="j-cvc"), now=fixed_clock.now()
        )
        assert record.state == "SUCCEEDED"
        after_a = _snap6(job_store, ws, "j-cvc")
        assert after_a[0] == "SUCCEEDED"
        assert after_a[2] == 4
        assert _audit_count(db_path, ws) == 1

        with pytest.raises(LeaseLost):
            job_store.confirm_cancel(
                lease, now=fixed_clock.now(), actor_id=ACTOR, request_id="req-s6-a2"
            )
        assert _snap6(job_store, ws, "j-cvc") == after_a
        assert _audit_count(db_path, ws) == 1
    else:
        record = job_store.succeed(
            lease, result_ref=ObjectRef(kind="job", id="j-cvc"), now=fixed_clock.now()
        )
        assert record.state == "SUCCEEDED"
        after_b = _snap6(job_store, ws, "j-cvc")
        assert after_b[2] == 3
        assert _audit_count(db_path, ws) == 0

        with pytest.raises(LeaseLost):
            job_store.confirm_cancel(
                lease, now=fixed_clock.now(), actor_id=ACTOR, request_id="req-s6-b"
            )
        assert _snap6(job_store, ws, "j-cvc") == after_b

        cur = job_store.get_job(workspace_id=ws, job_id="j-cvc")
        assert cur is not None
        with pytest.raises(StateConflict):
            job_store.request_cancel(
                workspace_id=ws,
                job_id="j-cvc",
                revision=cur.revision,
                now=fixed_clock.now(),
                actor_id=ACTOR,
                request_id="req-s6-b2",
            )
        assert _snap6(job_store, ws, "j-cvc") == after_b
        assert _audit_count(db_path, ws) == 0


def test_renew_extends_lease_by_30s(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    advance_clock: Callable[[int], datetime],
) -> None:
    """续租把 ``lease_until`` 恰推到「本次调用的 now ＋ TTL」。既有覆盖：T3 正路
    （``test_state_machine.py:178-187``）只断言 ``after[3] > before[3]`` 与未过期，未断言延长量。

    本例残差：``renew`` 后行 ``lease_deadline`` **恰等于**
    ``deadline_after(now, lease_seconds=LEASE_TTL_SECONDS)``（等值断言，强于 T3 的不等式；
    TTL 由 import 而来，断言不含秒数字面量——函数名里的秒数是 §3.A 逐字规格名）。
    同时钉住该值不等于认领时刻的 deadline，证明延长量跟着推进后的 ``now`` 走。
    """
    ws = "ws-s6-renew-ext"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-renew")
    claim = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    assert claim.lease is not None
    base_deadline = claim.lease.deadline

    advanced = advance_clock(10)
    result = job_store.renew(claim.lease, now=advanced, stage="s6-probe", progress=40)
    assert result.renewed is True

    row = job_store.get_job(workspace_id=ws, job_id="j-renew")
    assert row is not None
    assert row.lease_deadline == deadline_after(advanced, lease_seconds=LEASE_TTL_SECONDS)
    assert row.lease_deadline != base_deadline


@pytest.mark.parametrize(
    "scenario",
    ["terminal-SUCCEEDED", "terminal-FAILED", "terminal-CANCELLED"],
    ids=["T-IMM-SUCCEEDED", "T-IMM-FAILED", "T-IMM-CANCELLED"],
)
def test_terminal_state_is_immutable(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    scenario: str,
) -> None:
    """终态不可逆矩阵（集成层重做）。既有覆盖：仅单元层全矩阵
    ``tests/unit/test_job_repository_terminal.py:524``；集成层只有 T5 那一条
    （SUCCEEDED 后再 ``succeed``）。

    本例残差：用 ``JobStore`` ＋真实迁移库对 ``SUCCEEDED`` / ``FAILED`` / ``CANCELLED``
    三个终态，逐条验证 ``renew`` / ``succeed`` / ``fail`` / ``request_cancel`` /
    ``confirm_cancel`` 全部被拒（实测：``renewed is False`` 且 ``record`` 为 ``None``；
    ``succeed``/``fail``/``confirm_cancel`` 抛 ``LeaseLost``；``request_cancel`` 抛
    ``StateConflict``），且行快照六字段（``state``/``attempt``/``revision``/
    ``lease_until``/``problem_json``/``result_json``）逐字段不变。矩阵以「尝试表 vs 预期表」
    的键集对撞收尾：删掉任何一次尝试调用都会让 ``attempts`` 键集缺失、判红（PC-4 实证）。
    不跨层 import 单元测试私有 helper：``_problem`` / ``_snap6`` 均为本文件私有件。
    """
    ws = f"ws-s6-imm-{scenario}"
    db_path, _engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    _enqueue(job_store, fixed_clock, ws, "j-imm")
    claim = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    assert claim.lease is not None
    lease = claim.lease

    if scenario == "terminal-SUCCEEDED":
        job_store.succeed(
            lease, result_ref=ObjectRef(kind="job", id="j-imm"), now=fixed_clock.now()
        )
    elif scenario == "terminal-FAILED":
        job_store.fail(lease, problem=_problem(), now=fixed_clock.now())
    else:
        cur = job_store.get_job(workspace_id=ws, job_id="j-imm")
        assert cur is not None
        job_store.request_cancel(
            workspace_id=ws,
            job_id="j-imm",
            revision=cur.revision,
            now=fixed_clock.now(),
            actor_id=ACTOR,
            request_id="req-s6-imm",
        )
        job_store.confirm_cancel(
            lease, now=fixed_clock.now(), actor_id=ACTOR, request_id="req-s6-imm2"
        )

    terminal = scenario.removeprefix("terminal-")
    before = _snap6(job_store, ws, "j-imm")
    assert before[0] == terminal
    cur = job_store.get_job(workspace_id=ws, job_id="j-imm")
    assert cur is not None

    renew_result = job_store.renew(lease, now=fixed_clock.now(), stage="s6-imm-probe", progress=5)
    attempts: dict[str, str] = {"renew": "renewed" if renew_result.renewed else "rejected"}
    if renew_result.record is not None:
        attempts["renew_record"] = "present"
    calls: list[tuple[str, Callable[[], object]]] = [
        (
            "succeed",
            lambda: job_store.succeed(
                lease, result_ref=ObjectRef(kind="job", id="j-imm"), now=fixed_clock.now()
            ),
        ),
        ("fail", lambda: job_store.fail(lease, problem=_problem(), now=fixed_clock.now())),
        (
            "request_cancel",
            lambda: job_store.request_cancel(
                workspace_id=ws,
                job_id="j-imm",
                revision=cur.revision,
                now=fixed_clock.now(),
                actor_id=ACTOR,
                request_id="req-s6-imm3",
            ),
        ),
        (
            "confirm_cancel",
            lambda: job_store.confirm_cancel(
                lease, now=fixed_clock.now(), actor_id=ACTOR, request_id="req-s6-imm4"
            ),
        ),
    ]
    expected = {
        "renew": "rejected",
        "succeed": "LeaseLost",
        "fail": "LeaseLost",
        "request_cancel": "StateConflict",
        "confirm_cancel": "LeaseLost",
    }
    for name, call in calls:
        try:
            call()
            attempts[name] = "accepted"
        except DomainError as exc:
            attempts[name] = type(exc).__name__

    assert renew_result.record is None
    assert attempts == expected
    assert _snap6(job_store, ws, "j-imm") == before
