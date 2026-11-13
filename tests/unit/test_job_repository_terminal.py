"""M0-04/S2：终态写入 + A81／A82／A83 的机器可查守护（append-only 豁免的自证）。

分两半：

**前半＝守护**。本卡拿到了两处 append-only 豁免（A82 给 ``repositories.py``、A83 给
``application/worker.py``），豁免的代价是必须留下机器可查的边界证据，否则下一片无法判断
自己是否越界。故这里钉住：

1. ``INSERT INTO jobs|UPDATE jobs`` 的**文件集合**恒等于 ``{infra/db/repositories.py}``（A81）；
2. ``JobRepository`` 既有 4 个方法与 ``job_from_row`` 的签名**逐字未变**（A82）；
3. 租约计算表达式（``+ timedelta(`` 形态）只出现在 ``compute_lease_deadline`` 函数体内
   （A83 修订后的 A70 判据①）；
4. 终态唯一：任何终态行都拒绝全部 8 类后续迁移，且行内容逐字段不变；
5. 并发认领：两个连接 + ``BEGIN IMMEDIATE``，只有一个 ``rowcount == 1``。

签名串与迁移数在测试里**允许写死**——它们钉的是**冻结面**，不是会随交付增长的分母计数
（分母计数一律指向 ``state.json -> resume.self_check_gates_rc0.counts``，A75/D-012/D-014）。

**后半＝终态写入**本身：T5／T6／T7／T8 的仓储级行为，含 DDL 双条件 CHECK 的联动。
"""

from __future__ import annotations

import ast
import inspect
import re
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from campaignlab.api.common import ObjectRef, Problem
from campaignlab.application import worker as app_worker
from campaignlab.application.worker import WORKER_LEASE_SECONDS, compute_lease_deadline
from campaignlab.clock import FixedClock
from campaignlab.domain.errors import InternalFailure, ValidationFailure
from campaignlab.infra.db import repositories as repos_mod
from campaignlab.infra.db.engine import connect, make_engine
from campaignlab.infra.db.repositories import JobRecord, JobRepository, job_from_row
from campaignlab.worker.errors import problem_of
from campaignlab.worker.states import STAGE_CLAIMED, TERMINAL_STATES
from campaignlab.worker.store import (
    _BEGIN_IMMEDIATE,
    _COMMIT,
    _ROLLBACK,
    _is_lock_contention,
    connect_autocommit,
    immediate,
)

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "campaignlab"
DDL = REPO / "contracts" / "sqlite-v1.sql"
T0 = datetime(2026, 11, 13, 1, 0, 0, tzinfo=UTC)
WS = "ws-1"
DIGEST = "0" * 64

#: A82 要求「既有 4 方法签名逐字未变」。**刻意写死**：钉的是冻结面（见模块 docstring）。
FROZEN_JOB_REPOSITORY_SIGNATURES = {
    "insert": "(self, conn: 'Connection', *, job: 'JobRecord') -> 'None'",
    "get": (
        "(self, conn: 'Connection', *, workspace_id: 'str', job_id: 'str') -> 'JobRecord | None'"
    ),
    "list_ready": "(self, conn: 'Connection', *, limit: 'int') -> 'list[JobRecord]'",
    "touch_lease": (
        "(self, conn: 'Connection', *, job_id: 'str', lease_token: 'str', "
        "lease_deadline: 'str') -> 'int'"
    ),
}
FROZEN_JOB_FROM_ROW_SIGNATURE = "(record: 'JobRecord') -> 'Job'"

#: A81 的判定正则。
JOBS_DML = re.compile(r"INSERT INTO jobs|UPDATE jobs")


# ======================================================================================
# 守护 1：jobs 表的 SQL 写点唯一（A81）
# ======================================================================================


def test_jobs_dml_file_set_is_exactly_repositories() -> None:
    """扫 ``src/campaignlab/`` 全部 ``*.py``：命中 jobs 插入／更新语句的文件集合恒为 1 个。

    用 pathlib + 正则，**不依赖 shell**（守护测试自己要能在任何环境复跑）。
    ``worker/**`` 一片命中都不该有：``JobStore`` 是 A81 要求的「调用 ``JobRepository``
    的薄封装」，不是第二个 SQL 写点。
    """
    hits: dict[str, list[int]] = {}
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        found = [i + 1 for i, line in enumerate(text.split("\n")) if JOBS_DML.search(line)]
        if found:
            hits[str(path.relative_to(REPO))] = found
    assert set(hits) == {"src/campaignlab/infra/db/repositories.py"}, hits


def test_worker_package_contains_no_table_dml_literals() -> None:
    """``worker/**`` 里出现的 SQL 文本**只有**三条事务控制语句（design §4 / A81）。

    只检查**非 docstring** 的字符串常量：说明性文字里当然会提到 UPDATE／SELECT，
    那是在解释为什么本包不写它们。docstring 用 AST 精确识别（模块／类／函数体的首条
    ``Expr(Constant(str))``）。
    """
    verbs = re.compile(r"\b(INSERT|UPDATE|DELETE|SELECT|CREATE|DROP|ALTER)\b", re.IGNORECASE)
    allowed = {_BEGIN_IMMEDIATE, _COMMIT, _ROLLBACK}
    offenders: list[str] = []
    for path in sorted((SRC / "worker").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        docstrings: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                body = getattr(node, "body", [])
                if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)
                ):
                    docstrings.add(id(body[0].value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstrings or node.value in allowed:
                    continue
                if verbs.search(node.value):
                    offenders.append(f"{path.relative_to(REPO)}:{node.lineno} {node.value[:60]!r}")
    assert offenders == [], offenders


def test_transaction_control_constants_are_the_only_sql_in_store() -> None:
    """把「本包只有事务控制语句」这条断言的三个常量本身钉住，防止被悄悄改写。"""
    assert (_BEGIN_IMMEDIATE, _COMMIT, _ROLLBACK) == ("BEGIN IMMEDIATE", "COMMIT", "ROLLBACK")


# ======================================================================================
# 守护 2：既有 4 方法 + job_from_row 的签名逐字未变（A82）
# ======================================================================================


def test_frozen_job_repository_signatures_are_unchanged() -> None:
    """``inspect.signature`` 与硬编码期望串逐字比对（A82 交付条件②）。"""
    for name, expected in FROZEN_JOB_REPOSITORY_SIGNATURES.items():
        actual = str(inspect.signature(getattr(JobRepository, name)))
        assert actual == expected, f"{name}: 实际 {actual!r} != 期望 {expected!r}"


def test_frozen_job_from_row_signature_is_unchanged() -> None:
    """``job_from_row`` 禁改（A82）：签名与返回类型都不许动。"""
    assert str(inspect.signature(job_from_row)) == FROZEN_JOB_FROM_ROW_SIGNATURE


def test_new_job_repository_methods_only_grew_the_surface() -> None:
    """新增方法是**纯追加**：既有 4 个名字仍在，新增的都是 M0-04 的迁移／读写面。"""
    public = {n for n in dir(JobRepository) if not n.startswith("_")}
    assert set(FROZEN_JOB_REPOSITORY_SIGNATURES) <= public
    expected_new = {
        "claim_next",
        "renew",
        "request_cancel",
        "confirm_cancel",
        "mark_succeeded",
        "mark_failed",
        "fail_expired_running",
        "cancel_expired_requested",
        "enqueue_retry",
        "count_pending",
    }
    assert expected_new <= public, sorted(expected_new - public)


def test_repositories_module_all_is_unchanged() -> None:
    """``repositories.__all__`` 十项逐字未变（A82：禁改其余 4 个 Repository 类的公开面）。"""
    assert repos_mod.__all__ == [
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


# ======================================================================================
# 守护 3：租约计算点唯一（A83 修订后的 A70 判据①）
# ======================================================================================


def _timedelta_additions(root: Path) -> list[tuple[Path, str, int]]:
    """AST 扫出所有 ``<expr> + timedelta(...)`` 形态的加法，附**所属函数名**。

    比 grep 强在两点：不会被注释／字符串里的字面量误伤，也能报出所属函数，从而判定
    「这条加法在不在 ``compute_lease_deadline`` 体内」。
    """
    out: list[tuple[Path, str, int]] = []
    paths = [root] if root.is_file() else sorted(root.rglob("*.py"))
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        owners: dict[int, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    owners.setdefault(id(child), node.name)
        for node in ast.walk(tree):
            if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Add):
                continue
            call = node.right
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name != "timedelta":
                continue
            out.append((path, owners.get(id(node), "<module>"), node.lineno))
    return out


def test_lease_computation_exists_only_inside_compute_lease_deadline() -> None:
    """租约模块面内，``+ timedelta(`` 只出现在 ``compute_lease_deadline`` 体内（A83）。

    扫描面＝``application/worker.py`` + ``infra/db/repositories.py`` + ``worker/**``，
    即 A70 判据①③与 A83 共同圈定的「租约承载模块」。``application/session_service.py``
    的两处 ``now + timedelta(seconds=self._ttl_seconds)`` 是**会话** TTL、与租约无关，
    刻意不在扫描面内——把两者混为一谈会让这条守护永远红。
    """
    lease_bearing = [
        SRC / "application" / "worker.py",
        SRC / "infra" / "db" / "repositories.py",
    ]
    lease_bearing += sorted((SRC / "worker").rglob("*.py"))
    hits: list[tuple[str, str, int]] = []
    for path in lease_bearing:
        for found, owner, lineno in _timedelta_additions(path):
            hits.append((str(found.relative_to(REPO)), owner, lineno))
    for path_rel, owner, lineno in hits:
        assert path_rel == "src/campaignlab/application/worker.py", (path_rel, owner, lineno)
        assert owner == "compute_lease_deadline", (path_rel, owner, lineno)
    assert len(hits) == 1, hits


def test_compute_lease_deadline_is_exported_and_value_identical() -> None:
    """A83 要求：纳入 ``__all__``，且与原第 142 行内联表达式**值语义逐字节等价**。"""
    assert "compute_lease_deadline" in app_worker.__all__
    assert str(inspect.signature(compute_lease_deadline)) == (
        "(now: 'datetime', *, lease_seconds: 'int') -> 'str'"
    )
    for seconds in (1, 15, 30, 3600):
        expected = (T0 + timedelta(seconds=seconds)).isoformat()
        assert compute_lease_deadline(T0, lease_seconds=seconds) == expected
    naive = datetime(2026, 11, 13, 9, 0, 0)
    assert (
        compute_lease_deadline(naive, lease_seconds=30)
        == (naive + timedelta(seconds=30)).isoformat()
    )


def test_heartbeat_still_uses_the_single_computation_point() -> None:
    """``heartbeat()`` 的租约值仍来自 ``compute_lease_deadline``（A83 的等价替换）。"""
    source = inspect.getsource(app_worker.WorkerSupervisor.heartbeat)
    assert "compute_lease_deadline(now, lease_seconds=self._lease_seconds)" in source
    assert "timedelta" not in source


# ======================================================================================
# 守护 5：并发认领（两个连接 + BEGIN IMMEDIATE，禁 sleep）
# ======================================================================================


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
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


def _seed_queued(engine: Engine, job_id: str = "J-1") -> JobRecord:
    record = JobRecord(
        workspace_id=WS,
        id=job_id,
        kind="COMPARE",
        state="QUEUED",
        attempt=0,
        progress=0,
        stage="QUEUED",
        lease_token=None,
        lease_deadline=None,
        retry_of=None,
        retryable=False,
        input_json="{}",
        input_digest=DIGEST,
        result_json=None,
        problem_json=None,
        revision=1,
        created_at=T0.isoformat(),
    )
    with connect(engine) as conn, conn.begin():
        JobRepository().insert(conn, job=record)
    return record


def test_two_claimers_only_one_wins(engine: Engine) -> None:
    """AC-029「两次尝试争抢同一作业时只有有效租约可发布」。

    时序**不靠 sleep**，靠显式的事务顺序：A 先 ``BEGIN IMMEDIATE`` 拿到写锁但**不提交**，
    此时 B 的 ``BEGIN IMMEDIATE`` 必然拿不到 RESERVED 锁（B 的 ``busy_timeout`` 置 0，
    于是立刻 ``SQLITE_BUSY`` 而不是等 5 秒）；A 提交后 B 再试，读到的 ``state`` 已非
    QUEUED，谓词 UPDATE 命中 0 行 → ``None``。两条路径都以「只有一个赢家」收场，
    且败者不留半状态。
    """
    _seed_queued(engine)
    jobs = JobRepository()
    deadline = compute_lease_deadline(T0, lease_seconds=WORKER_LEASE_SECONDS)

    conn_a = connect_autocommit(engine)
    conn_b = connect_autocommit(engine)
    try:
        conn_b.exec_driver_sql("PRAGMA busy_timeout=0")
        with immediate(conn_a):
            won = jobs.claim_next(
                conn_a,
                workspace_id=WS,
                lease_token="tok-A",
                lease_deadline=deadline,
                stage=STAGE_CLAIMED,
            )
            assert won is not None and won.state == "RUNNING" and won.attempt == 1
            # A 未提交，写锁仍被占：B 的 BEGIN IMMEDIATE 必须干净失败。
            with pytest.raises(OperationalError) as excinfo, immediate(conn_b):
                jobs.claim_next(
                    conn_b,
                    workspace_id=WS,
                    lease_token="tok-B",
                    lease_deadline=deadline,
                    stage=STAGE_CLAIMED,
                )
            assert "locked" in str(excinfo.value).lower() or "busy" in str(excinfo.value).lower()
        # A 已提交。B 重试：谓词 UPDATE 命中 0 行，返回 None，不抛异常。
        with immediate(conn_b):
            lost = jobs.claim_next(
                conn_b,
                workspace_id=WS,
                lease_token="tok-B",
                lease_deadline=deadline,
                stage=STAGE_CLAIMED,
            )
        assert lost is None
    finally:
        conn_a.close()
        conn_b.close()

    with connect(engine) as conn:
        row = jobs.get(conn, workspace_id=WS, job_id="J-1")
    assert row is not None
    assert row.lease_token == "tok-A"  # 赢家的令牌，败者一字未改
    assert row.attempt == 1  # 只递增一次
    assert row.revision == 2  # 只 +1 一次：证明败者没留下半状态


def test_loser_rollback_leaves_no_partial_state(engine: Engine) -> None:
    """败者事务回滚后，行内容与胜者提交的结果**逐字段**一致（无脏写）。"""
    _seed_queued(engine)
    jobs = JobRepository()
    deadline = compute_lease_deadline(T0, lease_seconds=WORKER_LEASE_SECONDS)
    conn_a = connect_autocommit(engine)
    conn_b = connect_autocommit(engine)
    try:
        with immediate(conn_a):
            jobs.claim_next(
                conn_a,
                workspace_id=WS,
                lease_token="tok-A",
                lease_deadline=deadline,
                stage=STAGE_CLAIMED,
            )
        with immediate(conn_b):
            # 败者尝试写终态：attempt/token 都不匹配 → rowcount 0，不改任何字段。
            touched = jobs.mark_succeeded(
                conn_b,
                workspace_id=WS,
                job_id="J-1",
                attempt=99,
                lease_token="tok-B",
                result_json='{"kind":"job","id":"J-1"}',
            )
            assert touched == 0
        with connect(engine) as conn:
            row = jobs.get(conn, workspace_id=WS, job_id="J-1")
    finally:
        conn_a.close()
        conn_b.close()
    assert row is not None and row.state == "RUNNING" and row.result_json is None
    assert row.lease_token == "tok-A" and row.revision == 2


def test_lock_contention_is_classified_not_swallowed() -> None:
    """``BEGIN IMMEDIATE`` 撞锁 → 归类为退让；其余 ``OperationalError`` → 原样抛出。

    把所有 ``OperationalError`` 都当「这轮没抢到」会掩盖磁盘满／库损坏这类真故障，
    故 ``_is_lock_contention`` 只认 locked／busy 两种文本。
    """
    locked = OperationalError("BEGIN IMMEDIATE", {}, sqlite3.OperationalError("database is locked"))
    assert _is_lock_contention(locked) is True
    busy = OperationalError("BEGIN IMMEDIATE", {}, sqlite3.OperationalError("database is busy"))
    assert _is_lock_contention(busy) is True
    disk = OperationalError("x", {}, sqlite3.OperationalError("disk I/O error"))
    assert _is_lock_contention(disk) is False


# ======================================================================================
# 守护 4 + 终态写入：终态唯一性
# ======================================================================================


def _drive_to_terminal(engine: Engine, terminal: str) -> JobRecord:
    """把一条作业驱动到指定终态，返回终态行。"""
    clock = FixedClock(T0)
    jobs = JobRepository()
    _seed_queued(engine, "J-term")
    deadline = compute_lease_deadline(T0, lease_seconds=WORKER_LEASE_SECONDS)
    with connect(engine) as conn, conn.begin():
        if terminal == "CANCELLED":
            assert jobs.request_cancel(conn, workspace_id=WS, job_id="J-term", revision=1) == 1
        else:
            claimed = jobs.claim_next(
                conn,
                workspace_id=WS,
                lease_token="tok-T",
                lease_deadline=deadline,
                stage=STAGE_CLAIMED,
            )
            assert claimed is not None
            if terminal == "SUCCEEDED":
                assert (
                    jobs.mark_succeeded(
                        conn,
                        workspace_id=WS,
                        job_id="J-term",
                        attempt=1,
                        lease_token="tok-T",
                        result_json='{"kind":"job","id":"J-term"}',
                    )
                    == 1
                )
            else:
                assert (
                    jobs.mark_failed(
                        conn,
                        workspace_id=WS,
                        job_id="J-term",
                        attempt=1,
                        lease_token="tok-T",
                        problem_json=problem_of(InternalFailure("x")).model_dump_json(),
                        retryable=True,
                    )
                    == 1
                )
        row = jobs.get(conn, workspace_id=WS, job_id="J-term")
    assert row is not None and row.state == terminal
    _ = clock
    return row


@pytest.mark.parametrize("terminal", sorted(TERMINAL_STATES))
def test_terminal_state_rejects_every_further_transition(engine: Engine, terminal: str) -> None:
    """守护 4：**终态唯一**。对每个终态，8 类后续迁移全部 ``rowcount == 0``／``None``。

    这是 JOBS.md:23「若取消与完成争用，先成功提交的合法状态决定结果」的机器保证：
    败者改不动行，故永远造不出第二个终态。``enqueue_retry`` 只对 FAILED／CANCELLED 合法
    （那就是 T9 本身），故 SUCCEEDED 才把它列入被拒集合。
    """
    frozen_row = _drive_to_terminal(engine, terminal)
    jobs = JobRepository()
    deadline = compute_lease_deadline(T0 + timedelta(seconds=99), lease_seconds=30)
    problem_json = Problem.model_validate_json(
        problem_of(ValidationFailure("y")).model_dump_json()
    ).model_dump_json()

    with connect(engine) as conn, conn.begin():
        assert (
            jobs.claim_next(
                conn, workspace_id=WS, lease_token="tok-X", lease_deadline=deadline, stage="X"
            )
            is None
        )
        assert (
            jobs.renew(
                conn,
                workspace_id=WS,
                job_id="J-term",
                attempt=frozen_row.attempt,
                lease_token="tok-T",
                lease_deadline=deadline,
                stage="X",
                progress=1,
            )
            is None
        )
        assert (
            jobs.request_cancel(
                conn, workspace_id=WS, job_id="J-term", revision=frozen_row.revision
            )
            == 0
        )
        assert (
            jobs.confirm_cancel(
                conn,
                workspace_id=WS,
                job_id="J-term",
                attempt=frozen_row.attempt,
                lease_token="tok-T",
            )
            == 0
        )
        assert (
            jobs.mark_succeeded(
                conn,
                workspace_id=WS,
                job_id="J-term",
                attempt=frozen_row.attempt,
                lease_token="tok-T",
                result_json='{"kind":"job","id":"J-term"}',
            )
            == 0
        )
        assert (
            jobs.mark_failed(
                conn,
                workspace_id=WS,
                job_id="J-term",
                attempt=frozen_row.attempt,
                lease_token="tok-T",
                problem_json=problem_json,
                retryable=True,
            )
            == 0
        )
        assert (
            jobs.fail_expired_running(
                conn, now=(T0 + timedelta(days=1)).isoformat(), problem_json=problem_json
            )
            == 0
        )
        assert jobs.cancel_expired_requested(conn, now=(T0 + timedelta(days=1)).isoformat()) == 0
        if terminal == "SUCCEEDED":
            retry_row = JobRecord(
                workspace_id=WS,
                id="J-new",
                kind=frozen_row.kind,
                state="QUEUED",
                attempt=0,
                progress=0,
                stage="QUEUED",
                lease_token=None,
                lease_deadline=None,
                retry_of="J-term",
                retryable=False,
                input_json=frozen_row.input_json,
                input_digest=frozen_row.input_digest,
                result_json=None,
                problem_json=None,
                revision=1,
                created_at=T0.isoformat(),
            )
            assert (
                jobs.enqueue_retry(
                    conn,
                    workspace_id=WS,
                    source_job_id="J-term",
                    source_revision=frozen_row.revision,
                    new_job=retry_row,
                )
                == 0
            )
        after = jobs.get(conn, workspace_id=WS, job_id="J-term")
    assert after == frozen_row  # 逐字段未变：终态行连 revision 都没被动过


@pytest.mark.parametrize("terminal", ["CANCELLED", "FAILED"])
def test_terminal_failed_and_cancelled_are_retryable_sources(engine: Engine, terminal: str) -> None:
    """T9 的正面：FAILED／CANCELLED 可以当重试源，且源行终态一字不变、只 ``revision + 1``。"""
    source = _drive_to_terminal(engine, terminal)
    jobs = JobRepository()
    new_job = JobRecord(
        workspace_id=WS,
        id="J-retry",
        kind=source.kind,
        state="QUEUED",
        attempt=0,
        progress=0,
        stage="QUEUED",
        lease_token=None,
        lease_deadline=None,
        retry_of=source.id,
        retryable=False,
        input_json=source.input_json,
        input_digest=source.input_digest,
        result_json=None,
        problem_json=None,
        revision=1,
        created_at=(T0 + timedelta(seconds=5)).isoformat(),
    )
    with connect(engine) as conn, conn.begin():
        assert (
            jobs.enqueue_retry(
                conn,
                workspace_id=WS,
                source_job_id=source.id,
                source_revision=source.revision,
                new_job=new_job,
            )
            == 1
        )
        fresh_source = jobs.get(conn, workspace_id=WS, job_id=source.id)
        fresh_new = jobs.get(conn, workspace_id=WS, job_id="J-retry")
    assert fresh_source is not None and fresh_new is not None
    assert fresh_source.state == terminal
    assert fresh_source.revision == source.revision + 1
    assert fresh_source.result_json == source.result_json
    assert fresh_source.problem_json == source.problem_json
    assert fresh_new.state == "QUEUED" and fresh_new.retry_of == source.id
    assert fresh_new.input_digest == source.input_digest


def test_enqueue_retry_rejects_cross_reference(engine: Engine) -> None:
    """``retry_of`` 必须指向源作业、且同工作区（复合 FK），否则当场拒，不落库。"""
    source = _drive_to_terminal(engine, "FAILED")
    jobs = JobRepository()
    bad = JobRecord(
        workspace_id=WS,
        id="J-bad",
        kind=source.kind,
        state="QUEUED",
        attempt=0,
        progress=0,
        stage="QUEUED",
        lease_token=None,
        lease_deadline=None,
        retry_of="J-other",
        retryable=False,
        input_json="{}",
        input_digest=DIGEST,
        result_json=None,
        problem_json=None,
        revision=1,
        created_at=T0.isoformat(),
    )
    with connect(engine) as conn, conn.begin(), pytest.raises(ValueError):
        jobs.enqueue_retry(
            conn,
            workspace_id=WS,
            source_job_id=source.id,
            source_revision=source.revision,
            new_job=bad,
        )


def test_mark_succeeded_rejects_empty_result_json() -> None:
    """DDL 的双条件 CHECK ``(state='SUCCEEDED') = (result_json IS NOT NULL)`` 的 Python 侧对偶。"""
    with connect(make_engine("sqlite://")) as conn, pytest.raises(ValueError):
        JobRepository().mark_succeeded(
            conn, workspace_id=WS, job_id="J", attempt=1, lease_token="t", result_json=""
        )


def test_count_pending_counts_only_requested_states(engine: Engine) -> None:
    """``count_pending`` 的 IN 列表由绑定参数驱动，SQL 文本里不出现调用方数据。"""
    jobs = JobRepository()
    _seed_queued(engine, "J-a")
    _seed_queued(engine, "J-b")
    with connect(engine) as conn:
        assert jobs.count_pending(conn, workspace_id=WS, states=("QUEUED",)) == 2
        assert jobs.count_pending(conn, workspace_id=WS, states=("RUNNING",)) == 0
        assert jobs.count_pending(conn, workspace_id=WS, states=("QUEUED", "RUNNING")) == 2
        assert jobs.count_pending(conn, workspace_id="ws-other", states=("QUEUED",)) == 0
        with pytest.raises(ValueError):
            jobs.count_pending(conn, workspace_id=WS, states=())


def test_count_pending_never_interpolates_state_values(engine: Engine) -> None:
    """注入面核对：把状态值写成 SQL 片段，也只会被当成**普通字符串**比较，命中 0 行。"""
    jobs = JobRepository()
    _seed_queued(engine, "J-a")
    with connect(engine) as conn:
        hostile = "QUEUED') OR ('1'='1"
        assert jobs.count_pending(conn, workspace_id=WS, states=(hostile,)) == 0


def test_terminal_write_preserves_stage_and_progress(engine: Engine) -> None:
    """T6／T7 要求保留 ``stage``／``progress``（JOBS.md:16「保留错误码、阶段」）。"""
    _seed_queued(engine, "J-stage")
    jobs = JobRepository()
    deadline = compute_lease_deadline(T0, lease_seconds=WORKER_LEASE_SECONDS)
    with connect(engine) as conn, conn.begin():
        assert (
            jobs.claim_next(
                conn, workspace_id=WS, lease_token="tok-S", lease_deadline=deadline, stage="CLAIMED"
            )
            is not None
        )
        assert (
            jobs.renew(
                conn,
                workspace_id=WS,
                job_id="J-stage",
                attempt=1,
                lease_token="tok-S",
                lease_deadline=deadline,
                stage="DIAGNOSING",
                progress=35,
            )
            is not None
        )
        assert (
            jobs.mark_failed(
                conn,
                workspace_id=WS,
                job_id="J-stage",
                attempt=1,
                lease_token="tok-S",
                problem_json=problem_of(InternalFailure("boom")).model_dump_json(),
                retryable=True,
            )
            == 1
        )
        row = jobs.get(conn, workspace_id=WS, job_id="J-stage")
    assert row is not None
    assert row.state == "FAILED" and row.stage == "DIAGNOSING" and row.progress == 35
    problem = Problem.model_validate_json(row.problem_json or "{}")
    assert problem.code == "INTERNAL_ERROR"
    assert row.result_json is None  # 非 SUCCEEDED 不得有结果（DDL CHECK）


def test_result_json_roundtrips_through_job_from_row(engine: Engine) -> None:
    """A73 的映射口径：``result_json`` 存 ``ObjectRef`` 的 JSON 对象，``job_from_row`` 能解开。"""
    _seed_queued(engine, "J-dto")
    jobs = JobRepository()
    deadline = compute_lease_deadline(T0, lease_seconds=WORKER_LEASE_SECONDS)
    ref = ObjectRef(kind="job", id="J-dto")
    with connect(engine) as conn, conn.begin():
        jobs.claim_next(
            conn, workspace_id=WS, lease_token="tok-D", lease_deadline=deadline, stage="CLAIMED"
        )
        assert (
            jobs.mark_succeeded(
                conn,
                workspace_id=WS,
                job_id="J-dto",
                attempt=1,
                lease_token="tok-D",
                result_json=ref.model_dump_json(),
            )
            == 1
        )
        record = jobs.get(conn, workspace_id=WS, job_id="J-dto")
    assert record is not None
    dto = job_from_row(record)
    assert dto.state == "SUCCEEDED" and dto.progress == 100
    assert dto.result_ref == ref and dto.problem is None
    assert dto.retryable is False
