"""M0-04/S6 (R18) · 制品索引复核的集成层残差：``verify_artifact_index`` 检出缺件。

对应判据（派单 §4）：V2 ``pytest -q tests/integration/jobs -k artifact``（既有 18 例 ＋
本例净新增 1 例 collected）。

A243 重切依据（派单 §1 / §3.B）：design §9-S6 列的 ``test_artifact.py`` 6 名里 5 名已被
同目录同层的 ``test_artifact_write.py``（13 例）完整覆盖、判重豁免（逐名映射与复核结论见
回执 COVERAGE_MAP_3B，禁写重复用例也禁静默跳过）；第 6 名
``test_verify_artifact_index_detects_missing_file`` 在集成层是真缺口——实测
``verify_artifact_index`` 在 ``tests/**`` 的命中全部位于 ``tests/unit/test_worker_integrity.py``，
集成层 0 命中。本文件只落地该 1 例。

AC-031 判定归 M5-01；本例只交付 design §8 V9 的写入侧前提：制品必须经**真实写入路径**产生
（``claim → handler → succeed`` 的 T5 链，handler 取 conftest 冻结的 ``registry_with_stub``），
再把制品文件删除，断言差异**可定位**且 ``reason`` 取 ``worker/integrity.py`` 的注册常量
``MISSING_FILE``（禁自造字符串，红线 3）。时钟只经 ``fixed_clock``。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import Engine

from campaignlab.clock import FixedClock
from campaignlab.infra.db.engine import connect
from campaignlab.worker.integrity import MISSING_FILE, manifest_rows, verify_artifact_index
from campaignlab.worker.runner import HandlerRegistry, JobContext
from campaignlab.worker.store import JobStore

KIND: str = "VALIDATE_IMPORT"
INPUT_JSON: str = "{}"
INPUT_DIGEST: str = "0" * 64


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


def test_verify_artifact_index_detects_missing_file(
    job_store: JobStore,
    fixed_clock: FixedClock,
    migrated_job_db: tuple[Path, Engine],
    data_dir: Path,
    registry_with_stub: HandlerRegistry,
) -> None:
    """既有覆盖 vs 本例残差：``verify_artifact_index`` 仅单元层命中（36 处全在
    ``tests/unit/test_worker_integrity.py``），集成层为 0；同层 ``test_artifact_write.py``
    覆盖的是写入侧（begin/commit/sweep），不含索引复核。本例残差：真实 T5 链在 ``data_dir``
    ＋迁移库上落一个被 ``artifacts`` 行引用的制品 ⇒ 健康库 ``verify_artifact_index`` 恰回
    ``[]``；删除制品文件后差异集非空、``reason`` 恰为注册常量 ``MISSING_FILE``，且差异携带的
    ``workspace_id`` / ``artifact_id`` / ``relative_path`` / ``expected_sha256`` 与
    ``manifest_rows`` 的索引行逐字段对上、``actual_sha256`` 为 ``None``（「根本没读到内容」
    的语义，与「读到但摘要不符」严格区分），足以定位到该制品。
    """
    ws = "ws-s6-index"
    jid = "j-index"
    db_path, engine = migrated_job_db
    _seed_workspace(db_path, ws, fixed_clock.now().isoformat())
    job_store.enqueue(
        workspace_id=ws,
        kind=KIND,
        input_json=INPUT_JSON,
        input_digest=INPUT_DIGEST,
        now=fixed_clock.now(),
        job_id=jid,
    )
    claim = job_store.claim_next(workspace_id=ws, now=fixed_clock.now())
    assert claim.record is not None and claim.lease is not None

    handler = registry_with_stub.get(KIND)
    assert handler is not None
    outcome = handler(
        JobContext(record=claim.record, lease=claim.lease, store=job_store, clock=fixed_clock)
    )
    assert outcome.state == "SUCCEEDED"
    assert outcome.result_ref is not None
    job_store.succeed(claim.lease, result_ref=outcome.result_ref, now=fixed_clock.now())

    with connect(engine) as conn:
        rows = manifest_rows(conn)
    assert len(rows) == 1
    row = rows[0]
    assert row.workspace_id == ws

    with connect(engine) as conn:
        assert verify_artifact_index(conn, data_dir) == []

    target = data_dir / row.relative_path
    assert target.is_file()
    target.unlink()

    with connect(engine) as conn:
        discrepancies = verify_artifact_index(conn, data_dir)
    assert len(discrepancies) == 1
    found = discrepancies[0]
    assert found.reason == MISSING_FILE
    assert found.workspace_id == row.workspace_id
    assert found.artifact_id == row.artifact_id
    assert found.relative_path == row.relative_path
    assert found.expected_sha256 == row.sha256
    assert found.actual_sha256 is None
