"""M0-04/S3：原子制品写入的集成测试（数据库 × 文件系统 × 事务边界）。

对齐任务卡 gate「原子制品（独立尝试目录、同文件系统原子重命名、提交失败复用同摘要文件、
未引用制品可回收）：``pytest -q tests/integration/jobs -k artifact`` -> rc=0」，覆盖 6 个点：

① 正常写入 ＋ 索引与结果引用同事务登记（design §4 TX5 / §5 写入序）
② 重命名原子性：提交前终态路径不可见、中间态只存在于尝试目录
③ 事务回滚不留终态制品：登记失败就地回收；重命名成功后回滚 → 孤儿件可被 sweep 识别
④ 跨盘 ``EXDEV`` 判红（monkeypatch 决定性用例 ＋ 真实双设备用例），禁静默降级为 copy
⑤ 未引用制品回收：命中未引用终态件与超期尝试目录，**不命中**在飞尝试目录与其它子目录
⑥ 同内容稳定摘要：与分块边界无关、提交失败重试复用同一摘要文件（inode 不变）

时序一律用 ``FixedClock``；文件年龄用 ``os.utime`` 显式钉住，**不 sleep、不取系统当前时间**
（任务卡「禁止」条 / design §4）。库用活契约 DDL 建，不跑 alembic —— 与
``tests/unit/test_worker_runner.py`` 同一口径，``contracts/**`` 只读引用。

刻意**不新建 conftest.py**：D-035／R8-4 的教训是同 basename 文件会让 mypy 判重复模块名，
本文件自带 fixture，不给全树添第二个 ``conftest``。
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NoReturn

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError

from campaignlab.api.common import ObjectRef, canonical_json
from campaignlab.clock import FixedClock, ensure_utc
from campaignlab.config import ConfigError
from campaignlab.infra.artifacts import (
    ARTIFACT_KIND_JOB_RESULT,
    TMP_STALE_SECONDS,
    ArtifactWriter,
    AttemptStage,
    CommittedArtifact,
    relative_path_for,
    results_root,
    stage_root,
    sweep_unreferenced,
)
from campaignlab.infra.db.engine import connect, make_engine
from campaignlab.infra.db.repositories import JobRepository
from campaignlab.worker.errors import ArtifactCommitFailed, LeaseLost
from campaignlab.worker.leases import Lease
from campaignlab.worker.store import JobStore, short_transaction

REPO = Path(__file__).resolve().parents[3]
DDL = REPO / "contracts" / "sqlite-v1.sql"
#: 显式时钟的固定时刻。所有「年龄」判定都以它为基准，故用例与真实挂钟无关。
T0 = datetime(2026, 11, 14, 1, 0, 0, tzinfo=UTC)
#: 远超 ``TMP_STALE_SECONDS`` 的过去时刻（2 小时 vs 1 小时）。
OLD = T0 - timedelta(hours=2)
WS = "ws-art"
JOB = "J-art-1"
INPUT_DIGEST = "0" * 64
#: 含中文与非 ASCII 标点的载荷：顺带证明摘要口径与编码无关（一律按字节算）。
PAYLOAD = "活动 A 复盘结果 · 金额 12345 分 · 比率 0.15".encode() * 4


# ---------------------------------------------------------------------------------- fixture


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """``<data_dir>``：库文件与七个子目录同居一处（OPERATIONS.md:17）。"""
    return tmp_path


@pytest.fixture
def engine(data_dir: Path) -> Engine:
    """按活契约 DDL 建临时库，并插一个工作区（``artifacts.workspace_id`` 的外键目标）。"""
    assert DDL.is_file(), f"活契约 DDL 读不到：{DDL}"
    state_dir = data_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    db = state_dir / "campaignlab.db"
    raw = sqlite3.connect(db)
    try:
        raw.executescript(DDL.read_text(encoding="utf-8"))
        raw.execute(
            "INSERT INTO workspaces (id, name, source_class, revision, created_at) "
            "VALUES (?, ?, 'SYNTHETIC', 1, ?)",
            (WS, "制品工作区", T0.isoformat()),
        )
        raw.commit()
    finally:
        raw.close()
    return make_engine(f"sqlite:///{db}")


@pytest.fixture
def clock() -> FixedClock:
    """``step=0`` 故 ``now()`` 幂等；年龄靠 ``os.utime`` 造，不靠推进时钟。"""
    return FixedClock(T0)


@pytest.fixture
def store(engine: Engine) -> JobStore:
    return JobStore(engine=engine)


@pytest.fixture
def writer(data_dir: Path) -> ArtifactWriter:
    target = ArtifactWriter(data_dir)
    target.verify_same_filesystem()
    return target


@pytest.fixture
def other_device(data_dir: Path) -> Iterator[Path | None]:
    """找一个与 ``data_dir`` 不同 ``st_dev`` 的可写目录（WSL2 上通常是 ``/dev/shm``）。

    找不到就返回 ``None``，由用例自己 ``skip`` 并说明「已由 monkeypatch 用例覆盖」——
    禁把「环境不具备」写成「通过」。
    """
    primary_dev = data_dir.stat().st_dev
    candidate: Path | None = None
    for base in ("/dev/shm", "/run/lock", "/tmp"):
        root = Path(base)
        if not root.is_dir():
            continue
        probe = root / f"campaignlab-exdev-{uuid.uuid4().hex}"
        try:
            probe.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        if probe.stat().st_dev != primary_dev:
            candidate = probe
            break
        shutil.rmtree(probe, ignore_errors=True)
    yield candidate
    if candidate is not None:
        shutil.rmtree(candidate, ignore_errors=True)


# ----------------------------------------------------------------------------------- 工具


def _running_job(store: JobStore, clock: FixedClock, *, job_id: str = JOB) -> Lease:
    """入队 ＋ 认领，拿到一条 ``RUNNING`` 作业的租约（TX1）。"""
    store.enqueue(
        workspace_id=WS,
        kind="COMPARE",
        input_json=canonical_json({"snapshot": "S-1"}),
        input_digest=INPUT_DIGEST,
        now=clock.now(),
        job_id=job_id,
    )
    claim = store.claim_next(workspace_id=WS, now=clock.now())
    assert claim.lease is not None, "前置条件：必须认领成功"
    return claim.lease


def _tx5_commit(
    engine: Engine,
    writer: ArtifactWriter,
    stage: AttemptStage,
    lease: Lease,
    *,
    now: datetime,
    lease_token: str | None = None,
) -> CommittedArtifact:
    """在**一个** ``BEGIN IMMEDIATE`` 里做 design §4 TX5 的两件事：制品登记 ＋ 终态 UPDATE。

    刻意不走 ``JobStore.succeed(artifacts=...)``：那条路只把制品行的 INSERT 放进事务，而
    design §5 要求 ``os.replace`` 也在同一事务内发生（即 ``ArtifactWriter.commit``）。本卡
    无权改 ``worker/**``（S2 已交付、属他人写权），故按其 ``succeed`` 的内部顺序在这里手工
    组装同一条事务，用来证明「同事务」这个性质本身；``lease_token`` 可注入错值以模拟
    「取消／失效租约抢先提交」→ ``rowcount=0`` → 回滚。
    """
    jobs = JobRepository()
    token = lease.token if lease_token is None else lease_token
    with short_transaction(engine) as conn:
        committed = writer.commit(
            conn,
            stage,
            workspace_id=lease.workspace_id,
            kind=ARTIFACT_KIND_JOB_RESULT,
            now=now,
        )
        touched = jobs.mark_succeeded(
            conn,
            workspace_id=lease.workspace_id,
            job_id=lease.job_id,
            attempt=lease.attempt,
            lease_token=token,
            result_json=canonical_json(
                ObjectRef(kind="job", id=lease.job_id).model_dump(mode="json")
            ),
        )
        if touched != 1:
            raise LeaseLost(f"成功提交未命中租约守卫：job={lease.job_id}")
    return committed


def _final_path(data_dir: Path, payload: bytes, *, workspace_id: str = WS) -> Path:
    """独立算一遍内容寻址终态路径（不复用被测函数，作为外部预言值）。"""
    digest = hashlib.sha256(payload).hexdigest()
    return results_root(data_dir) / ARTIFACT_KIND_JOB_RESULT / workspace_id / digest[:2] / digest


def _artifact_count(engine: Engine) -> int:
    with connect(engine) as conn:
        return int(conn.execute(text("SELECT count(*) FROM artifacts")).scalar_one())


def _job_row(engine: Engine, job_id: str) -> RowMapping:
    with connect(engine) as conn:
        return (
            conn.execute(
                text("SELECT state, attempt, result_json FROM jobs WHERE id = :id"),
                {"id": job_id},
            )
            .mappings()
            .one()
        )


def _age(path: Path, *, at: datetime) -> None:
    """把 ``st_mtime`` 显式钉到给定时刻：年龄靠 utime 造，不靠 sleep（design §4）。"""
    stamp = ensure_utc(at).timestamp()
    os.utime(path, (stamp, stamp))


# =============================================== ① 正常写入 ＋ 同事务登记索引与结果引用


def test_artifact_commit_registers_index_and_result_ref_in_one_transaction(
    engine: Engine,
    writer: ArtifactWriter,
    store: JobStore,
    clock: FixedClock,
    data_dir: Path,
) -> None:
    """TX5：``os.replace`` ＋ ``artifacts`` 行 ＋ ``jobs.result_json`` 同事务落地。"""
    lease = _running_job(store, clock)
    with writer.begin(lease.workspace_id, lease.job_id, lease.attempt) as stage:
        stage.write(PAYLOAD)
        committed = _tx5_commit(engine, writer, stage, lease, now=clock.now())

    digest = hashlib.sha256(PAYLOAD).hexdigest()
    expected_rel = f"results/{ARTIFACT_KIND_JOB_RESULT}/{WS}/{digest[:2]}/{digest}"
    assert expected_rel == relative_path_for(
        kind=ARTIFACT_KIND_JOB_RESULT, workspace_id=WS, sha256=digest
    )
    assert committed.relative_path == expected_rel
    assert committed.sha256 == digest
    assert committed.byte_size == len(PAYLOAD)
    assert committed.artifact_id.startswith("art-")
    assert (committed.reused_file, committed.reused_row) == (False, False)
    assert committed.path == data_dir / Path(expected_rel)
    assert committed.path.read_bytes() == PAYLOAD

    with connect(engine) as conn:
        rows = (
            conn.execute(
                text(
                    "SELECT id, workspace_id, kind, sha256, relative_path, byte_size, created_at "
                    "FROM artifacts"
                )
            )
            .mappings()
            .all()
        )
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == committed.artifact_id
    assert row["workspace_id"] == WS
    assert row["kind"] == ARTIFACT_KIND_JOB_RESULT
    assert row["sha256"] == digest
    assert row["relative_path"] == expected_rel
    assert row["byte_size"] == len(PAYLOAD)
    assert row["created_at"] == T0.isoformat()

    job = _job_row(engine, lease.job_id)
    assert job["state"] == "SUCCEEDED"
    assert json.loads(str(job["result_json"])) == {"kind": "job", "id": lease.job_id}
    # 尝试目录已被清空：不留 .part、不留空目录（否则会污染下一轮 sweep 的分母）
    assert list(stage_root(data_dir).rglob("*")) == []


# ================================================== ② 重命名原子性：终态不可见中间态


def test_artifact_final_path_stays_invisible_until_the_atomic_rename(
    engine: Engine,
    writer: ArtifactWriter,
    store: JobStore,
    clock: FixedClock,
    data_dir: Path,
) -> None:
    """提交前终态路径不存在；提交后一次到位，``results`` 下永不出现 ``.part``。"""
    lease = _running_job(store, clock)
    final_path = _final_path(data_dir, PAYLOAD)
    with writer.begin(lease.workspace_id, lease.job_id, lease.attempt) as stage:
        for offset in range(0, len(PAYLOAD), 7):
            stage.write(PAYLOAD[offset : offset + 7])
        # 中间态只在独立尝试目录里，且带 .part 后缀；终态路径完全不可见
        assert not final_path.exists()
        assert stage.path.exists()
        assert stage.path.parent == stage.directory
        assert stage.path.suffix == ".part"
        assert stage.directory.is_relative_to(stage_root(data_dir))
        with short_transaction(engine) as conn:
            committed = writer.commit(
                conn,
                stage,
                workspace_id=WS,
                kind=ARTIFACT_KIND_JOB_RESULT,
                now=clock.now(),
            )
            # 事务内：文件已原子就位，但索引行对**其它连接**仍不可见（尚未 COMMIT）
            assert final_path.exists()
            with connect(engine) as other:
                visible = int(other.execute(text("SELECT count(*) FROM artifacts")).scalar_one())
            assert visible == 0
        assert committed.path == final_path

    assert final_path.read_bytes() == PAYLOAD
    assert [p.name for p in results_root(data_dir).rglob("*.part")] == []
    assert _artifact_count(engine) == 1


def test_artifact_attempt_dirs_are_isolated_per_attempt(
    writer: ArtifactWriter, data_dir: Path
) -> None:
    """``attempt`` 进路径：同一作业的两次尝试互不覆写（design §5 目录布局）。"""
    first = writer.begin(WS, JOB, 1)
    second = writer.begin(WS, JOB, 2)
    try:
        assert first.directory != second.directory
        assert first.directory.name == "1" and second.directory.name == "2"
        assert first.path != second.path
        first.write(b"attempt-1")
        second.write(b"attempt-2")
        assert first.path.read_bytes() == b"attempt-1"
        assert second.path.read_bytes() == b"attempt-2"
        assert first.sha256 != second.sha256
        assert first.directory.is_relative_to(stage_root(data_dir) / WS / JOB)
    finally:
        first.discard()
        second.discard()
    assert list(stage_root(data_dir).rglob("*")) == []


# ============================================== ③ 事务回滚不留已重命名的终态制品


def test_artifact_registration_failure_reclaims_the_renamed_file(
    engine: Engine,
    writer: ArtifactWriter,
    store: JobStore,
    clock: FixedClock,
    data_dir: Path,
) -> None:
    """登记失败（外键）→ 事务回滚 ＋ 就地删掉刚重命名过去的终态文件，不留悬挂。"""
    lease = _running_job(store, clock)
    ghost = "ws-ghost"
    ghost_final = _final_path(data_dir, PAYLOAD, workspace_id=ghost)
    stage = writer.begin(ghost, lease.job_id, lease.attempt)
    with pytest.raises(IntegrityError), short_transaction(engine) as conn:
        writer.commit(
            conn,
            stage,
            workspace_id=ghost,
            kind=ARTIFACT_KIND_JOB_RESULT,
            now=clock.now(),
        )
    assert not ghost_final.exists(), "登记失败后不得留下已重命名的终态制品"
    assert _artifact_count(engine) == 0
    assert [p for p in results_root(data_dir).rglob("*") if p.is_file()] == []
    assert not stage.path.exists(), "暂存件已被 rename 消费，回收后不该有残留"
    stage.discard()
    assert not stage.directory.exists()
    assert _job_row(engine, lease.job_id)["state"] == "RUNNING"


def test_artifact_rollback_after_rename_is_reclaimable_by_sweep(
    engine: Engine,
    writer: ArtifactWriter,
    store: JobStore,
    clock: FixedClock,
    data_dir: Path,
) -> None:
    """重命名成功、事务因租约守卫 ``rowcount=0`` 回滚 → 孤儿件必须能被回收逻辑识别。

    这正是 JOBS.md:23「旧尝试结果登记失败时其制品视为未引用」与 design §4「TX5 败者已
    ``os.replace`` 的制品即成未引用制品」的落点。
    """
    lease = _running_job(store, clock)
    final_path = _final_path(data_dir, PAYLOAD)
    with writer.begin(lease.workspace_id, lease.job_id, lease.attempt) as stage:
        stage.write(PAYLOAD)
        with pytest.raises(LeaseLost):
            _tx5_commit(engine, writer, stage, lease, now=clock.now(), lease_token="stale-token")

    assert final_path.exists(), "前提：重命名已发生"
    assert _artifact_count(engine) == 0, "回滚后索引里不该有行"
    assert _job_row(engine, lease.job_id)["state"] == "RUNNING"

    _age(final_path, at=OLD)
    relative = final_path.relative_to(data_dir).as_posix()
    with connect(engine) as conn:
        preview = sweep_unreferenced(conn, data_dir, now=clock.now(), dry_run=True)
    assert preview.unreferenced_files == (relative,), "孤儿终态件必须被识别为未引用"
    assert preview.referenced_rows == 0
    assert (preview.removed_files, preview.removed_dirs, preview.candidates) == (0, 0, 1)
    assert final_path.exists(), "dry_run 只报告不删除"

    with connect(engine) as conn:
        applied = sweep_unreferenced(conn, data_dir, now=clock.now(), dry_run=False)
    assert (applied.removed_files, applied.removed_dirs) == (1, 0)
    assert not final_path.exists()
    assert applied.failed_removals == ()


# ================================================ ④ 跨盘 EXDEV 判红（禁静默 copy）


def test_artifact_commit_reports_exdev_as_red_instead_of_copying(
    engine: Engine,
    writer: ArtifactWriter,
    store: JobStore,
    clock: FixedClock,
    data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``os.replace`` 抛 ``EXDEV`` → ``ArtifactCommitFailed``（500），禁 copy 兜底。"""
    lease = _running_job(store, clock)
    final_path = _final_path(data_dir, PAYLOAD)
    calls: list[tuple[object, object]] = []

    def _exdev(src: object, dst: object) -> NoReturn:
        calls.append((src, dst))
        raise OSError(errno.EXDEV, os.strerror(errno.EXDEV))

    monkeypatch.setattr(os, "replace", _exdev)  # 同一个 os 模块对象，被测模块即刻生效
    with writer.begin(lease.workspace_id, lease.job_id, lease.attempt) as stage:
        stage.write(PAYLOAD)
        with pytest.raises(ArtifactCommitFailed) as excinfo, short_transaction(engine) as conn:
            writer.commit(
                conn,
                stage,
                workspace_id=WS,
                kind=ARTIFACT_KIND_JOB_RESULT,
                now=clock.now(),
            )

    assert len(calls) == 1, "只允许试一次 rename，不得退化成 copy 循环"
    assert "EXDEV" in str(excinfo.value.detail)
    assert excinfo.value.code == "INTERNAL_ERROR"
    assert excinfo.value.status == 500
    assert not final_path.exists(), "判红后不得留下半截终态文件"
    assert _artifact_count(engine) == 0
    assert _job_row(engine, lease.job_id)["state"] == "RUNNING"


def test_artifact_cross_device_layout_is_rejected_at_startup_and_at_commit(
    engine: Engine,
    store: JobStore,
    clock: FixedClock,
    data_dir: Path,
    other_device: Path | None,
) -> None:
    """真实双设备：``verify_same_filesystem`` 抛 ``ConfigError``（CLI rc=2），commit 抛 EXDEV。

    用 ``<data_dir>/tmp/jobs`` 指向另一个文件系统的符号链接来造真实设备差（本机无 root、
    不能 bind mount）。``results`` 保持真实目录，故 ``commit`` 的受控目录守卫不会先拦下它，
    真正触发的是 ``os.replace`` 的 ``EXDEV``。
    """
    if other_device is None:
        pytest.skip("本机没有第二个可写文件系统；EXDEV 由 monkeypatch 用例覆盖")
    (data_dir / "tmp").mkdir(parents=True, exist_ok=True)
    results_root(data_dir).mkdir(parents=True, exist_ok=True)
    real_jobs = other_device / "jobs"
    real_jobs.mkdir(parents=True, exist_ok=True)
    os.symlink(real_jobs, stage_root(data_dir))
    cross = ArtifactWriter(data_dir)

    with pytest.raises(ConfigError) as startup:
        cross.verify_same_filesystem()
    assert "同一文件系统" in str(startup.value)

    lease = _running_job(store, clock)
    final_path = _final_path(data_dir, PAYLOAD)
    with cross.begin(WS, lease.job_id, lease.attempt) as stage:
        assert stage.directory.resolve().is_relative_to(other_device.resolve())
        assert stage.directory.resolve() != stage.directory, "前提：暂存目录确实经过符号链接"
        stage.write(PAYLOAD)
        with (
            pytest.raises(ArtifactCommitFailed) as commit_error,
            short_transaction(engine) as conn,
        ):
            cross.commit(
                conn,
                stage,
                workspace_id=WS,
                kind=ARTIFACT_KIND_JOB_RESULT,
                now=clock.now(),
            )
    assert "EXDEV" in str(commit_error.value.detail)
    assert not final_path.exists()
    assert _artifact_count(engine) == 0


# ================================================ ⑤ 未引用制品回收（含在飞保护）


def test_artifact_sweep_removes_unreferenced_and_keeps_referenced(
    engine: Engine,
    writer: ArtifactWriter,
    store: JobStore,
    clock: FixedClock,
    data_dir: Path,
) -> None:
    """只删「无 ``artifacts`` 行引用且已超期」的终态件；有行者与新鲜者一律保留。"""
    lease = _running_job(store, clock)
    with writer.begin(lease.workspace_id, lease.job_id, lease.attempt) as stage:
        stage.write(PAYLOAD)
        committed = _tx5_commit(engine, writer, stage, lease, now=clock.now())

    orphan = results_root(data_dir) / ARTIFACT_KIND_JOB_RESULT / WS / "ff" / ("f" * 64)
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(b"orphan")
    _age(orphan, at=OLD)
    young = results_root(data_dir) / ARTIFACT_KIND_JOB_RESULT / WS / "ee" / ("e" * 64)
    young.parent.mkdir(parents=True, exist_ok=True)
    young.write_bytes(b"young")
    _age(young, at=T0 - timedelta(seconds=60))
    # 有索引行的制品即使很旧也永不删（OPERATIONS.md:22）
    _age(committed.path, at=OLD)

    with connect(engine) as conn:
        preview = sweep_unreferenced(conn, data_dir, now=clock.now(), dry_run=True)
    assert preview.dry_run is True
    assert preview.min_age_seconds == TMP_STALE_SECONDS
    assert preview.referenced_rows == 1
    assert preview.scanned_result_files == 3
    assert preview.referenced_files_seen == 1
    assert preview.unreferenced_files == (orphan.relative_to(data_dir).as_posix(),)
    assert preview.young_unreferenced_files == (young.relative_to(data_dir).as_posix(),)
    assert (preview.removed_files, preview.removed_dirs, preview.candidates) == (0, 0, 1)
    assert orphan.exists() and young.exists() and committed.path.exists()

    with connect(engine) as conn:
        applied = sweep_unreferenced(conn, data_dir, now=clock.now(), dry_run=False)
    assert (applied.removed_files, applied.removed_dirs) == (1, 0)
    assert applied.failed_removals == ()
    assert not orphan.exists()
    assert young.exists(), "未超期的未引用件可能正处在 rename→INSERT 窗口里，不得删"
    assert committed.path.read_bytes() == PAYLOAD
    assert _artifact_count(engine) == 1


def test_artifact_sweep_never_touches_in_flight_attempt_dirs(
    engine: Engine,
    writer: ArtifactWriter,
    store: JobStore,
    clock: FixedClock,
    data_dir: Path,
) -> None:
    """在飞尝试目录（进程内登记）即使 mtime 被推到超期也不回收；崩溃残留与新鲜目录分开处置。"""
    lease = _running_job(store, clock)
    live = writer.begin(lease.workspace_id, lease.job_id, lease.attempt)
    live.write(PAYLOAD)
    crashed = stage_root(data_dir) / WS / "J-crashed" / "0"
    crashed.mkdir(parents=True, exist_ok=True)
    crashed_payload = crashed / "payload-deadbeef.part"
    crashed_payload.write_bytes(b"half-written")
    fresh = stage_root(data_dir) / WS / "J-fresh" / "0"
    fresh.mkdir(parents=True, exist_ok=True)
    fresh_payload = fresh / "payload-cafe.part"
    fresh_payload.write_bytes(b"brand-new")

    for target in (live.directory, live.path, crashed, crashed_payload):
        _age(target, at=OLD)
    for target in (fresh, fresh_payload):
        _age(target, at=T0 - timedelta(seconds=30))

    with connect(engine) as conn:
        report = sweep_unreferenced(conn, data_dir, now=clock.now(), dry_run=False)
    assert report.in_flight_attempt_dirs == (live.directory.relative_to(data_dir).as_posix(),)
    assert report.stale_attempt_dirs == (crashed.relative_to(data_dir).as_posix(),)
    assert report.young_attempt_dirs == (fresh.relative_to(data_dir).as_posix(),)
    assert (report.removed_dirs, report.removed_files) == (1, 0)
    assert live.directory.exists() and live.path.exists(), "在飞尝试目录一字节都不能动"
    assert live.path.read_bytes() == PAYLOAD
    assert not crashed.exists(), "超期崩溃残留必须被回收"
    assert fresh.exists() and fresh_payload.exists(), "未超期的尝试目录不得回收"

    # 在飞尝试仍能正常提交：sweep 没有破坏它（TX5 一次成功）
    committed = _tx5_commit(engine, writer, live, lease, now=clock.now())
    assert committed.path.read_bytes() == PAYLOAD
    assert _artifact_count(engine) == 1
    assert not live.directory.exists()


def test_artifact_sweep_ignores_every_other_data_subdir(
    engine: Engine, writer: ArtifactWriter, clock: FixedClock, data_dir: Path
) -> None:
    """扫描面只有 ``results/**`` 与 ``tmp/jobs/**``：其余子目录（含证据）永不触碰。"""
    protected = {
        "raw/import.csv": b"raw-bytes",
        "snapshots/snap-1.parquet": b"snapshot-bytes",
        "exports/report.pdf": b"export-bytes",
        "logs/app.log": b"log-bytes",
        # 刻意不用 .db-wal／.db-journal：SQLite 打开库时会把这类文件当残留日志回收掉，
        # 那是数据库自己的行为、与本用例要证的「sweep 不碰其它子目录」无关。
        "state/restore-marker.txt": b"marker-bytes",
    }
    for relative, content in protected.items():
        path = data_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        _age(path, at=OLD)

    with connect(engine) as conn:
        report = sweep_unreferenced(conn, data_dir, now=clock.now(), min_age=0, dry_run=False)
    assert report.scanned_result_files == 0
    assert (report.candidates, report.removed) == (0, 0)
    for relative, content in protected.items():
        assert (data_dir / relative).read_bytes() == content


# ================================================== ⑥ 同内容稳定摘要 ＋ 复用同摘要文件


def test_artifact_same_content_yields_stable_digest_and_reuses_row(
    engine: Engine,
    writer: ArtifactWriter,
    store: JobStore,
    clock: FixedClock,
    data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """摘要与分块边界无关；同内容第二次提交复用终态文件与索引行，且回读到同一个权威 id。"""
    lease = _running_job(store, clock)
    with writer.begin(lease.workspace_id, lease.job_id, lease.attempt) as stage:
        for offset in range(0, len(PAYLOAD), 11):
            stage.write(PAYLOAD[offset : offset + 11])
        first = _tx5_commit(engine, writer, stage, lease, now=clock.now())

    second_lease = _running_job(store, clock, job_id="J-art-2")

    def _no_replace(src: object, dst: object) -> NoReturn:
        raise AssertionError("复用同摘要文件时不得再调用 os.replace")

    monkeypatch.setattr(os, "replace", _no_replace)
    with writer.begin(
        second_lease.workspace_id, second_lease.job_id, second_lease.attempt
    ) as stage:
        stage.write(PAYLOAD)  # 一次写完，与上面的分块写法不同
        assert stage.sha256 == first.sha256, "摘要必须与写入分块方式无关"
        second = _tx5_commit(engine, writer, stage, second_lease, now=clock.now())

    digest = hashlib.sha256(PAYLOAD).hexdigest()
    assert first.sha256 == second.sha256 == digest
    assert second.relative_path == first.relative_path
    assert second.path == first.path == _final_path(data_dir, PAYLOAD)
    assert (second.reused_file, second.reused_row) == (True, True)
    assert second.artifact_id == first.artifact_id, "必须回读既有行的 id，禁用刚生成的 id"
    assert _artifact_count(engine) == 1, "内容去重：UNIQUE(workspace_id,kind,sha256) 只有一行"
    assert _job_row(engine, "J-art-2")["state"] == "SUCCEEDED"


def test_artifact_retry_after_failed_commit_reuses_the_same_digest_file(
    engine: Engine,
    writer: ArtifactWriter,
    store: JobStore,
    clock: FixedClock,
    data_dir: Path,
) -> None:
    """JOBS.md:25：提交失败后重试复用**同一个**摘要文件（inode 不变，没有重写）。"""
    lease = _running_job(store, clock)
    final_path = _final_path(data_dir, PAYLOAD)
    with writer.begin(lease.workspace_id, lease.job_id, lease.attempt) as stage:
        stage.write(PAYLOAD)
        with pytest.raises(LeaseLost):
            _tx5_commit(engine, writer, stage, lease, now=clock.now(), lease_token="stale-token")
    assert final_path.exists() and _artifact_count(engine) == 0
    inode_before = final_path.stat().st_ino

    with writer.begin(lease.workspace_id, lease.job_id, lease.attempt) as stage:
        stage.write(PAYLOAD)
        retried = _tx5_commit(engine, writer, stage, lease, now=clock.now())

    assert (retried.reused_file, retried.reused_row) == (True, False)
    assert retried.path == final_path
    assert retried.path.stat().st_ino == inode_before, "物理上必须是同一个文件"
    assert retried.sha256 == hashlib.sha256(PAYLOAD).hexdigest()
    assert _artifact_count(engine) == 1
    assert _job_row(engine, lease.job_id)["state"] == "SUCCEEDED"


def test_artifact_commit_rejects_mismatched_content_at_the_final_path(
    engine: Engine,
    writer: ArtifactWriter,
    store: JobStore,
    clock: FixedClock,
    data_dir: Path,
) -> None:
    """终态路径上已有**不同内容**的同名文件 → 判红拒绝覆盖（受控目录被污染的防线）。"""
    lease = _running_job(store, clock)
    final_path = _final_path(data_dir, PAYLOAD)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_bytes(b"poisoned-content")
    with writer.begin(lease.workspace_id, lease.job_id, lease.attempt) as stage:
        stage.write(PAYLOAD)
        with pytest.raises(ArtifactCommitFailed) as excinfo, short_transaction(engine) as conn:
            writer.commit(
                conn,
                stage,
                workspace_id=WS,
                kind=ARTIFACT_KIND_JOB_RESULT,
                now=clock.now(),
            )
    assert "拒绝覆盖" in str(excinfo.value.detail)
    assert final_path.read_bytes() == b"poisoned-content", "不得覆盖既有文件"
    assert _artifact_count(engine) == 0
