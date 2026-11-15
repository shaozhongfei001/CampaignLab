"""M0-04/S5 · jobs 集成目录的共享 fixture（design §9-S5 行，9 个名字逐字冻结）。

装配口径照抄 ``tests/integration/jobs/test_jobs_router_s4.py`` 的 ``Harness``：
DDL 直读活契约 ``contracts/sqlite-v1.sql``（禁第二份 DDL）、``FixedClock`` 显式时钟、
注入位显式给齐；jobs 服务不经 ``create_app`` 注入——``worker/deps.py::get_job_service``
按 ``app.state.config.database_url`` 自建引擎，故 DB 位置通过
``CAMPAIGNLAB_DATABASE_URL`` 环境变量与 config 对齐（五级链唯一实现，ADR-005 §2.4）。

**本文件禁 autouse**（派单 §2.4）：同目录三个既有测试文件各自定义了同名模块级
fixture（``data_dir``／``clock``／``engine``／``store`` 等），模块级遮蔽令普通
fixture 互不干扰；但 autouse 会强行注入既有用例，必然改变其行为，故一切 fixture
均按需显式请求，无一例外。

测试桩只准注册在本文件（N8／A89 裁定：src 内禁放桩）；``result_ref`` 口径取
``ObjectRef(kind='job', id=<job_id>)``，制品写入用 ``ArtifactWriter`` ＋
``ARTIFACT_KIND_JOB_RESULT``（该常量即本裁定的权威落点）。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from campaignlab.api.app import create_app
from campaignlab.api.common import ObjectRef, OriginHostGuard
from campaignlab.application.session_service import (
    SessionService,
    SessionStore,
    SessionTokenStore,
)
from campaignlab.application.workspace_service import WorkspaceService
from campaignlab.clock import FixedClock
from campaignlab.config import API_PREFIX, AppIdentity, load_config
from campaignlab.infra.artifacts import ARTIFACT_KIND_JOB_RESULT, ArtifactWriter
from campaignlab.infra.db.engine import make_engine
from campaignlab.worker.runner import HandlerRegistry, JobContext, JobHandler, JobOutcome
from campaignlab.worker.store import JobStore, short_transaction

REPO: Final = Path(__file__).resolve().parents[3]
DDL: Final = REPO / "contracts/sqlite-v1.sql"

T0: Final = datetime(2026, 11, 13, 1, 0, 0, tzinfo=UTC)
TOKEN_TTL: Final = 60
SESSION_TTL: Final = 3600
TEST_ORIGIN: Final = "http://testserver"
GUARD: Final = OriginHostGuard(frozenset({"testserver"}), frozenset({"http://testserver"}))
IDENTITY: Final = AppIdentity(
    actor_id="s5-tester",
    actor_name="s5-tester",
    allowed_roles=("OPERATOR", "DESIGNER", "DATA_OWNER", "ANALYST", "TESTER", "REVIEWER"),
)

#: 桩所覆盖的作业类型（T5 取证所需 kind；design §1 十值枚举之一）。
STUB_KIND: Final = "VALIDATE_IMPORT"
#: 桩写出的结果载荷；制品摘要由 ``ArtifactWriter`` 增量自算，此处只固定内容。
STUB_PAYLOAD: Final = b"s5-stub-result-payload"
#: 入队载荷的固定摘要位（DDL 只要求 64 位十六进制文本）。
STUB_INPUT_DIGEST: Final = "0" * 64


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """本用例独享的数据目录（``tmp_path`` 之下）。与模块级同名 fixture 互不影响。"""
    root = tmp_path / "s5-data"
    root.mkdir()
    return root


@pytest.fixture
def migrated_job_db(data_dir: Path) -> tuple[Path, Engine]:
    """建库并执行首迁 DDL：直读活契约 ``executescript``，再接 ``make_engine``。

    返回 ``(db_path, engine)``；``job_store`` 与 ``http_client`` 共用同一文件库，
    HTTP 侧经 ``CAMPAIGNLAB_DATABASE_URL`` 自建的引擎与本引擎指向同一路径。
    **禁在测试里内嵌第二份 DDL**（派单 §3）。
    """
    db_path = data_dir / "campaignlab.db"
    raw = sqlite3.connect(db_path)
    try:
        raw.executescript(DDL.read_text(encoding="utf-8"))
        raw.commit()
    finally:
        raw.close()
    return db_path, make_engine(f"sqlite:///{db_path}")


@pytest.fixture
def fixed_clock() -> FixedClock:
    """带 tzinfo=UTC 常量起点的 ``FixedClock``（体例照抄 S4：T0 为模块常量）。"""
    return FixedClock(T0)


@pytest.fixture
def advance_clock(fixed_clock: FixedClock) -> Callable[[int], datetime]:
    """推进 ``fixed_clock`` 的唯一通道；T3／T7／T8 的到期分支全部经由它。

    返回推进后的时刻。除本通道外，一切用例不得引入任何流逝语义（红线 3／D-045）。
    """

    def advance(seconds: int) -> datetime:
        fixed_clock.advance(timedelta(seconds=seconds))
        return fixed_clock.now()

    return advance


@pytest.fixture
def job_store(migrated_job_db: tuple[Path, Engine]) -> JobStore:
    """绑定 ``migrated_job_db`` 引擎的 ``JobStore``。

    实测构造签名为 ``JobStore(*, engine, jobs=None, audit=None, artifacts=None)``
    （PRE-7 于 ``worker/store.py`` ``inspect.signature`` 取回），不含时钟位；
    时钟绑定发生在调用侧——各用例一律以 ``fixed_clock`` 现取 ``now`` 传入。
    """
    _db_path, engine = migrated_job_db
    return JobStore(engine=engine)


@pytest.fixture
def stub_handler(
    migrated_job_db: tuple[Path, Engine],
    data_dir: Path,
    fixed_clock: FixedClock,
) -> JobHandler:
    """最小 ``JobHandler`` 桩（N8／A89：桩只准注册在本文件，src 内禁放桩）。

    以 ``ArtifactWriter`` ＋ ``ARTIFACT_KIND_JOB_RESULT`` 写出结果件（同事务登记索引），
    返回 ``JobOutcome(state='SUCCEEDED', result_ref=ObjectRef(kind='job', id=<job_id>))``；
    ``kind='job'`` 在 ``api/common.py`` 的 ``ObjectKind`` 枚举内（实测 20 值含 ``job``）。
    """
    _db_path, engine = migrated_job_db

    def _handler(ctx: JobContext) -> JobOutcome:
        record = ctx.record
        writer = ArtifactWriter(data_dir)
        with writer.begin(record.workspace_id, record.id, record.attempt) as stage:
            stage.write(STUB_PAYLOAD)
            with short_transaction(engine) as conn:
                writer.commit(
                    conn,
                    stage,
                    workspace_id=record.workspace_id,
                    kind=ARTIFACT_KIND_JOB_RESULT,
                    now=fixed_clock.now(),
                )
        return JobOutcome(
            state="SUCCEEDED",
            result_ref=ObjectRef(kind="job", id=record.id),
        )

    return _handler


@pytest.fixture
def registry_with_stub(stub_handler: JobHandler) -> HandlerRegistry:
    """已注册 ``stub_handler`` 的 ``HandlerRegistry``，覆盖 T5 取证所需 kind。"""
    registry = HandlerRegistry()
    registry.register(STUB_KIND, stub_handler)
    return registry


@pytest.fixture
def idem_key() -> Callable[[str], str]:
    """``Idempotency-Key`` 头工厂：前缀＋标签，长度恒落在契约的 8–128 区间。"""

    def make(label: str) -> str:
        return f"s5-idem-{label}"

    return make


@pytest.fixture
def http_client(
    migrated_job_db: tuple[Path, Engine],
    data_dir: Path,
    fixed_clock: FixedClock,
) -> TestClient:
    """已认证的 ``TestClient``：装配口径照抄 ``Harness.authed_client()``。

    ``create_app(config, clock=..., guard=GUARD, session_service=...,
    workspace_service=...)`` ＋ ``Origin`` 头 ＋ ``POST /session/exchange`` 换
    token。DB 位置经 ``CAMPAIGNLAB_DATABASE_URL`` 与 config 对齐（§3 注记）。
    时钟与 ``job_store`` 侧共用同一 ``fixed_clock`` 实例，保证 HTTP 读到的时刻
    与状态机用例推进的时刻同源。
    """
    db_path, engine = migrated_job_db
    config = load_config(
        environ={
            "CAMPAIGNLAB_DATA_DIR": str(data_dir),
            "CAMPAIGNLAB_DATABASE_URL": f"sqlite:///{db_path}",
        },
        home=data_dir,
    )
    session_service = SessionService(
        tokens=SessionTokenStore(ttl_seconds=TOKEN_TTL),
        sessions=SessionStore(ttl_seconds=SESSION_TTL),
    )
    workspace_service = WorkspaceService(engine=engine, clock=fixed_clock, config=config)
    app = create_app(
        config,
        clock=fixed_clock,
        guard=GUARD,
        session_service=session_service,
        workspace_service=workspace_service,
    )
    client = TestClient(app, headers={"Origin": TEST_ORIGIN})
    token = session_service.tokens.mint(IDENTITY, T0)
    response = client.post(f"{API_PREFIX}/session/exchange", json={"token": token})
    assert response.status_code == 200, response.text
    return client
