"""S3d：application 层用例服务 + ``api/deps.py`` 的真实装配。

钉住派单文要求的四条自证：

1. **结构化满足**：三个实现类通过 ``api.deps`` 的 ``@runtime_checkable`` Protocol 校验，
   且 ``application`` 层没有第二份同名 Protocol（ADR-005 §2.1）；
2. **进程重启后会话失效**：用**新建 app 实例**模拟重启，而不是清字典（design §4）；
3. **401 只有一个面孔**：未命中／已过期／重启后一律同码同 detail（杜绝枚举 oracle）；
4. **禁静默回落**：服务未注入时提供器显式 ``RuntimeError``（→ 500 Problem），不造默认实现。

外加幂等与同事务：``workspaces`` 与 ``audit`` 同事务落库、同键同摘要重放同一 ETag、
同键异摘要 409、游标绑定 actor 与查询条件。
"""

from __future__ import annotations

import inspect
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

import campaignlab.application.health_service as app_health
import campaignlab.application.session_service as app_session
import campaignlab.application.workspace_service as app_workspace
from campaignlab.api import deps
from campaignlab.api.app import create_app
from campaignlab.api.common import OriginHostGuard, Session, WorkspaceCreate, WorkspacePage
from campaignlab.application.audit import AuditWriter
from campaignlab.application.health_service import UNMIGRATED_REVISION, HealthService
from campaignlab.application.idempotency import IdempotencyGuard
from campaignlab.application.session_service import (
    SESSION_COOKIE_NAME,
    SESSION_INVALID_DETAIL,
    SessionService,
    SessionStore,
    SessionTokenStore,
)
from campaignlab.application.worker import WorkerSupervisor
from campaignlab.application.workspace_service import WorkspaceCreateOutcome, WorkspaceService
from campaignlab.clock import Clock, FixedClock
from campaignlab.config import AppConfig, AppIdentity, load_config
from campaignlab.domain.errors import (
    DomainError,
    IdempotencyConflict,
    SessionInvalid,
    ValidationFailure,
)
from campaignlab.infra.db.engine import connect, make_engine
from campaignlab.infra.db.repositories import WorkspaceRepository

REPO = Path(__file__).resolve().parents[2]
DDL = REPO / "contracts" / "sqlite-v1.sql"
T0 = datetime(2026, 11, 13, 1, 0, 0, tzinfo=UTC)
TESTSERVER = OriginHostGuard(frozenset({"testserver"}), frozenset({"http://testserver"}))
IDENTITY = AppIdentity(
    actor_id="tester",
    actor_name="tester",
    allowed_roles=("OPERATOR", "DESIGNER", "DATA_OWNER", "ANALYST", "TESTER", "REVIEWER"),
)


@pytest.fixture
def config(tmp_path: Path) -> AppConfig:
    return load_config(environ={"CAMPAIGNLAB_DATA_DIR": str(tmp_path)}, home=tmp_path)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    db = tmp_path / "campaignlab.db"
    raw = sqlite3.connect(db)
    try:
        raw.executescript(DDL.read_text(encoding="utf-8"))
        raw.commit()
    finally:
        raw.close()
    return make_engine(f"sqlite:///{db}")


def _members(port: type) -> set[str]:
    """取 Protocol 声明的成员名（``__protocol_attrs__`` 属实现细节，故用 getattr 取）。"""
    return {str(name) for name in getattr(port, "__protocol_attrs__", ())}


def _actor() -> Session:
    return Session(
        actor_id=IDENTITY.actor_id,
        actor_name=IDENTITY.actor_name,
        allowed_roles=list(IDENTITY.allowed_roles),
    )


def _session_service(token_ttl: int = 60, session_ttl: int = 3600) -> SessionService:
    return SessionService(
        tokens=SessionTokenStore(ttl_seconds=token_ttl),
        sessions=SessionStore(ttl_seconds=session_ttl),
    )


def test_implementations_structurally_satisfy_deps_protocols(
    config: AppConfig, engine: Engine
) -> None:
    clock: Clock = FixedClock(T0)
    session_service = _session_service()
    health_service = HealthService(config=config, clock=clock, engine=engine)
    workspace_service = WorkspaceService(engine=engine, clock=clock, config=config)
    assert isinstance(session_service, deps.SessionService)
    assert isinstance(health_service, deps.HealthService)
    assert isinstance(workspace_service, deps.WorkspaceService)
    assert isinstance(WorkerSupervisor(clock=clock, engine=engine), app_health.WorkerStatus)
    # Protocol 成员面不是空的（S3c 留下的是空端口，S3d 已按实现补全）
    assert _members(deps.SessionService) == {"exchange", "resolve", "cookie"}
    assert _members(deps.WorkspaceService) == {"list_workspaces", "create_workspace"}
    assert _members(deps.HealthService) == {"snapshot"}


def test_application_layer_declares_no_second_protocol() -> None:
    """三个实现类都是**普通类**：接口定义只有一份，在 ``api/deps.py``。"""
    for module, name in (
        (app_session, "SessionService"),
        (app_health, "HealthService"),
        (app_workspace, "WorkspaceService"),
    ):
        cls = getattr(module, name)
        assert inspect.isclass(cls), (module.__name__, name)
        assert not getattr(cls, "_is_protocol", False), f"{name} 是第二份 Protocol"
        assert deps.HealthService not in cls.__mro__
        assert deps.SessionService not in cls.__mro__
        assert deps.WorkspaceService not in cls.__mro__


def test_app_identity_is_imported_from_config_not_redefined() -> None:
    """裁定 A42/§9.4：``AppIdentity`` 的唯一定义处是 ``config.py``，本片不得另建同名类。"""
    import campaignlab.config as config_module

    # 用 __dict__ 取：ruff B009 会把 getattr(mod, "常量") 改回 mod.常量，
    # 而 mypy 的 no_implicit_reexport 又不认「import 进来但没进 __all__」的名字。
    assert app_session.__dict__["AppIdentity"] is config_module.AppIdentity
    assert config_module.AppIdentity.__module__ == "campaignlab.config"
    # 本片**不**把它 re-export 进 application 的公开面：定义处唯一、导入点唯一
    assert "AppIdentity" not in app_session.__all__


def test_token_is_single_use_and_expires_at_ttl() -> None:
    tokens = SessionTokenStore(ttl_seconds=60)
    token = tokens.mint(IDENTITY, T0)
    assert 16 <= len(token) <= 180
    assert tokens.consume(token, T0) == IDENTITY
    assert tokens.consume(token, T0) is None  # 一次性：pop 在锁内完成
    expired = tokens.mint(IDENTITY, T0)
    assert tokens.consume(expired, T0 + timedelta(seconds=60)) is None
    fresh = tokens.mint(IDENTITY, T0)
    assert tokens.consume(fresh, T0 + timedelta(seconds=59)) == IDENTITY


def test_session_store_expires_and_touches() -> None:
    store = SessionStore(ttl_seconds=3600)
    record = store.create(IDENTITY, T0)
    assert record.expires_at == T0 + timedelta(seconds=3600)
    got = store.get(record.session_id, T0 + timedelta(seconds=10))
    assert got is not None and got.last_seen_at == T0 + timedelta(seconds=10)
    assert store.get(record.session_id, record.expires_at) is None
    assert store.get(record.session_id, T0) is None  # 过期即删
    assert store.get(None, T0) is None
    assert store.invalidate_all() == 0


def test_session_invalid_detail_is_identical_for_every_cause() -> None:
    """未命中／已消费／已过期／会话不存在／会话过期 → 同码同 detail（design §4）。"""
    service = _session_service(token_ttl=60, session_ttl=60)
    token = service.tokens.mint(IDENTITY, T0)
    record = service.exchange(token, now=T0 + timedelta(seconds=30))
    causes: list[SessionInvalid] = []
    calls: list[Callable[[], object]] = [
        lambda: service.exchange("never-minted-000000", now=T0),
        lambda: service.exchange(token, now=T0),
        lambda: service.resolve(None, now=T0),
        lambda: service.resolve("bogus", now=T0),
        lambda: service.resolve(record.session_id, now=T0 + timedelta(seconds=120)),
    ]
    for call in calls:
        with pytest.raises(SessionInvalid) as info:
            call()
        causes.append(info.value)
    assert {exc.detail for exc in causes} == {SESSION_INVALID_DETAIL}
    assert {exc.code for exc in causes} == {"SESSION_EXPIRED"}
    assert {exc.status for exc in causes} == {401}


def test_exchange_then_cookie_roundtrip() -> None:
    service = _session_service(token_ttl=60, session_ttl=3600)
    record = service.exchange(service.tokens.mint(IDENTITY, T0), now=T0)
    cookie = service.cookie(record, now=T0)
    assert cookie.name == SESSION_COOKIE_NAME == "cl_session"
    assert cookie.value == record.session_id and cookie.max_age == 3600
    assert cookie.path == "/api/v1"
    assert cookie.httponly is True and cookie.secure is False and cookie.samesite == "strict"
    assert record.to_session() == _actor()
    assert service.cookie(record, now=T0 + timedelta(seconds=3599)).max_age == 1
    assert service.cookie(record, now=T0 + timedelta(seconds=4000)).max_age == 0


def _probe_app(config: AppConfig, clock: Clock, service: SessionService | None) -> FastAPI:
    """建一个只挂了探针路由的 app：这是 ``deps.require_session`` 的真实行为面。

    ``api/session.py`` 与 ``api/workspaces.py`` 的挂载属 S3b（Round 7），本片不代写，
    故用测试内的探针路由来驱动同一个依赖。
    """
    app = create_app(config, clock=clock, guard=TESTSERVER, session_service=service)

    @app.get("/api/v1/probe")
    def probe(
        actor: Session = Depends(deps.require_session),  # noqa: B008 - FastAPI 依赖注入惯用法
    ) -> dict[str, Any]:
        return actor.model_dump(mode="json")

    return app


def test_require_session_401_problem_without_cookie(config: AppConfig) -> None:
    with TestClient(_probe_app(config, FixedClock(T0), _session_service())) as client:
        response = client.get("/api/v1/probe")
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "SESSION_EXPIRED" and body["status"] == 401
    assert body["detail"] == SESSION_INVALID_DETAIL
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["X-Request-Id"] == body["request_id"]


def test_require_session_accepts_valid_cookie(config: AppConfig) -> None:
    service = _session_service()
    record = service.exchange(service.tokens.mint(IDENTITY, T0), now=T0)
    cookie = {SESSION_COOKIE_NAME: record.session_id}
    with TestClient(_probe_app(config, FixedClock(T0), service)) as client:
        response = client.get("/api/v1/probe", cookies=cookie)
    assert response.status_code == 200
    assert response.json() == _actor().model_dump(mode="json")


def test_process_restart_invalidates_session_via_new_app_instance(config: AppConfig) -> None:
    """AC-035：**新建 app 实例**（＝进程重启，两个 store 重新构造）后旧 cookie 必须 401。

    刻意不清字典——清字典证明不了「不落盘」，只有换一套 store 才证明会话没被持久化。
    """
    first = _session_service()
    record = first.exchange(first.tokens.mint(IDENTITY, T0), now=T0)
    cookie = {SESSION_COOKIE_NAME: record.session_id}
    with TestClient(_probe_app(config, FixedClock(T0), first)) as client:
        assert client.get("/api/v1/probe", cookies=cookie).status_code == 200

    second = _session_service()  # 重启：全新的 store + 全新的 app 实例
    with TestClient(_probe_app(config, FixedClock(T0), second)) as client:
        response = client.get("/api/v1/probe", cookies=cookie)
    assert response.status_code == 401
    assert response.json()["detail"] == SESSION_INVALID_DETAIL


def test_expired_session_401_uses_the_same_detail(config: AppConfig) -> None:
    clock = FixedClock(T0)
    service = _session_service(token_ttl=60, session_ttl=30)
    record = service.exchange(service.tokens.mint(IDENTITY, T0), now=T0)
    cookie = {SESSION_COOKIE_NAME: record.session_id}
    with TestClient(_probe_app(config, clock, service)) as client:
        assert client.get("/api/v1/probe", cookies=cookie).status_code == 200
        clock.advance(timedelta(seconds=31))
        response = client.get("/api/v1/probe", cookies=cookie)
    assert response.status_code == 401
    assert response.json()["detail"] == SESSION_INVALID_DETAIL


def test_providers_raise_runtime_error_when_services_are_not_assembled(
    config: AppConfig,
) -> None:
    """禁静默回落：未注入 → ``app.state`` 上没有该属性 → 提供器 RuntimeError → 500 Problem。"""
    app = create_app(config, clock=FixedClock(T0), guard=TESTSERVER)
    assert not hasattr(app.state, "session_service")
    assert not hasattr(app.state, "health_service")
    assert not hasattr(app.state, "workspace_service")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "INTERNAL_ERROR" and body["issues"] == []
    assert "RuntimeError" not in body["detail"] and "Traceback" not in body["detail"]


def test_create_app_attaches_injected_services_and_keeps_legacy_behaviour(
    config: AppConfig, engine: Engine
) -> None:
    clock = FixedClock(T0)
    session_service = _session_service()
    health_service = HealthService(config=config, clock=clock, engine=engine)
    workspace_service = WorkspaceService(engine=engine, clock=clock, config=config)
    app = create_app(
        config,
        clock=clock,
        guard=TESTSERVER,
        session_service=session_service,
        health_service=health_service,
        workspace_service=workspace_service,
    )
    assert app.state.session_service is session_service
    assert app.state.health_service is health_service
    assert app.state.workspace_service is workspace_service
    # 纯追加式扩围的自证：三条既有装配面一字未改
    assert app.state.config is config and app.state.clock is clock and app.state.guard is TESTSERVER
    assert app.openapi_url is None and app.docs_url is None and app.redoc_url is None
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert set(response.json()) == {
        "status",
        "app_version",
        "contract_version",
        "worker",
        "schema_revision",
    }


def test_health_degraded_when_unmigrated_or_worker_missing(
    config: AppConfig, engine: Engine
) -> None:
    service = HealthService(config=config, clock=FixedClock(T0), engine=engine)
    assert service.schema_revision() == UNMIGRATED_REVISION
    snapshot = service.snapshot()
    assert snapshot.worker == "OFFLINE" and snapshot.status == "DEGRADED"
    assert snapshot.schema_revision == UNMIGRATED_REVISION
    assert snapshot.contract_version == config.contract_version
    assert snapshot.app_version == config.app_version
    # 没有 engine（库都还没打开）同样降级，不猜 revision
    assert HealthService(config=config, clock=FixedClock(T0)).schema_revision() == (
        UNMIGRATED_REVISION
    )


def test_health_ready_requires_worker_and_head_revision(config: AppConfig, tmp_path: Path) -> None:
    """READY 是**与**条件：worker 在线且 ``schema_revision`` == alembic head。"""
    head = app_health.read_migration_head()
    assert head is not None and head != UNMIGRATED_REVISION
    db = tmp_path / "migrated.db"
    raw = sqlite3.connect(db)
    try:
        raw.executescript(DDL.read_text(encoding="utf-8"))
        raw.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        raw.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (head,))
        raw.commit()
    finally:
        raw.close()
    migrated = make_engine(f"sqlite:///{db}")
    worker = WorkerSupervisor(clock=FixedClock(T0), engine=migrated, heartbeat_ttl_seconds=15)
    service = HealthService(config=config, clock=FixedClock(T0), engine=migrated, worker=worker)
    assert service.schema_revision() == head
    assert service.snapshot().status == "DEGRADED"  # worker 还没跳过 → 与条件不成立
    worker._heartbeat_at = T0
    snapshot = service.snapshot()
    assert snapshot.worker == "READY" and snapshot.schema_revision == head
    assert snapshot.status == "READY"
    worker._failed = True
    assert service.snapshot().status == "DEGRADED"


def _workspace_service(config: AppConfig, engine: Engine, clock: Clock) -> WorkspaceService:
    return WorkspaceService(
        engine=engine,
        clock=clock,
        config=config,
        workspaces=WorkspaceRepository(),
        idempotency=IdempotencyGuard(),
        audit=AuditWriter(),
        cursor_secret=b"0" * 32,  # 注入固定密钥：测试可复现，不在 tmp 里落 state/cursor.key
    )


def _create(
    service: WorkspaceService, name: str, key: str, body: bytes | None = None
) -> WorkspaceCreateOutcome:
    payload = WorkspaceCreate(name=name, source_class="SYNTHETIC")
    raw = body if body is not None else payload.model_dump_json().encode("utf-8")
    return service.create_workspace(
        payload=payload, body=raw, idempotency_key=key, actor=_actor(), request_id="req-1"
    )


def test_create_workspace_writes_audit_in_the_same_transaction(
    config: AppConfig, engine: Engine
) -> None:
    service = _workspace_service(config, engine, FixedClock(T0))
    outcome = _create(service, "甲", "key-aaaa-1")
    assert outcome.replayed is False and outcome.status == 201
    assert outcome.headers == {"ETag": '"1"'}
    assert outcome.body["revision"] == 1 and outcome.body["authorization_note"] is None
    workspace_id = str(outcome.body["id"])
    with connect(engine) as conn:
        audits = list(
            conn.exec_driver_sql(
                "SELECT sequence, action, outcome, role, workspace_id, request_id, "
                "previous_digest, target_kind, target_id FROM audit"
            )
        )
        idem = list(
            conn.exec_driver_sql(
                "SELECT scope_key, actor_id, operation, response_status FROM idempotency"
            )
        )
        assert len(audits) == 1
        assert audits[0] == (
            1,
            "WORKSPACE_CREATED",
            "ACCEPTED",
            "OPERATOR",
            workspace_id,
            "req-1",
            None,
            "workspace",
            workspace_id,
        )
        assert idem == [("GLOBAL", "tester", "createWorkspace", 201)]


def test_create_workspace_replay_returns_identical_body_and_etag(
    config: AppConfig, engine: Engine
) -> None:
    service = _workspace_service(config, engine, FixedClock(T0))
    body = WorkspaceCreate(name="甲", source_class="SYNTHETIC").model_dump_json().encode("utf-8")
    first = _create(service, "甲", "key-bbbb-1", body)
    second = _create(service, "甲", "key-bbbb-1", body)
    assert second.replayed is True and first.replayed is False
    assert second.status == first.status == 201
    assert second.headers == first.headers  # ETag 从信封回放，不重算
    assert second.body == first.body
    assert second.as_envelope() == {
        "status": 201,
        "headers": first.headers,
        "body": first.body,
    }
    with connect(engine) as conn:
        assert conn.exec_driver_sql("SELECT count(*) FROM workspaces").scalar_one() == 1
        assert conn.exec_driver_sql("SELECT count(*) FROM audit").scalar_one() == 1
        assert conn.exec_driver_sql("SELECT count(*) FROM idempotency").scalar_one() == 1


def test_create_workspace_conflict_is_409(config: AppConfig, engine: Engine) -> None:
    service = _workspace_service(config, engine, FixedClock(T0))
    first_body = '{"name":"甲","source_class":"SYNTHETIC"}'.encode()
    other_body = '{"name":"乙","source_class":"SYNTHETIC"}'.encode()
    _create(service, "甲", "key-cccc-1", first_body)
    with pytest.raises(IdempotencyConflict) as info:
        _create(service, "乙", "key-cccc-1", other_body)
    assert info.value.code == "IDEMPOTENCY_CONFLICT" and info.value.status == 409
    with connect(engine) as conn:
        assert conn.exec_driver_sql("SELECT count(*) FROM workspaces").scalar_one() == 1


def test_create_workspace_rejects_bad_idempotency_key(config: AppConfig, engine: Engine) -> None:
    service = _workspace_service(config, engine, FixedClock(T0))
    with pytest.raises(ValidationFailure) as info:
        _create(service, "甲", "short")
    assert info.value.status == 422
    assert info.value.issues[0].location == "/header/Idempotency-Key"


def test_list_workspaces_pagination_and_next_cursor(config: AppConfig, engine: Engine) -> None:
    clock = FixedClock(T0)
    service = _workspace_service(config, engine, clock)
    for index in range(5):
        clock.advance(timedelta(minutes=1))
        _create(service, f"ws-{index}", f"key-list-{index}")
    page: WorkspacePage = service.list_workspaces(actor=_actor(), cursor=None, limit=2, q=None)
    assert [item.name for item in page.items] == ["ws-4", "ws-3"]
    assert page.next_cursor is not None and len(page.next_cursor) <= 300
    second = service.list_workspaces(actor=_actor(), cursor=page.next_cursor, limit=2, q=None)
    assert [item.name for item in second.items] == ["ws-2", "ws-1"]
    assert second.next_cursor is not None
    third = service.list_workspaces(actor=_actor(), cursor=second.next_cursor, limit=2, q=None)
    assert [item.name for item in third.items] == ["ws-0"]
    assert third.next_cursor is None


def test_list_workspaces_q_filter_and_bad_cursor(config: AppConfig, engine: Engine) -> None:
    clock = FixedClock(T0)
    service = _workspace_service(config, engine, clock)
    _create(service, "Bank 复盘", "key-q-0001")
    clock.advance(timedelta(minutes=1))
    _create(service, "无关工作区", "key-q-0002")
    hit = service.list_workspaces(actor=_actor(), cursor=None, limit=25, q="BANK")
    assert [item.name for item in hit.items] == ["Bank 复盘"]
    empty = service.list_workspaces(actor=_actor(), cursor=None, limit=25, q="zzz")
    assert empty.items == [] and empty.next_cursor is None
    for bad in ("garbage", "a.b", ""):
        with pytest.raises(DomainError) as info:
            service.list_workspaces(actor=_actor(), cursor=bad, limit=25, q=None)
        assert info.value.code == "BAD_CURSOR" and info.value.status == 400


def test_cursor_is_bound_to_actor_and_query(config: AppConfig, engine: Engine) -> None:
    """换 actor 或换 limit/q 复用游标 → 400 ``BAD_CURSOR``，同一句 detail。"""
    clock = FixedClock(T0)
    service = _workspace_service(config, engine, clock)
    for index in range(3):
        clock.advance(timedelta(minutes=1))
        _create(service, f"ws-{index}", f"key-bind-{index}")
    page = service.list_workspaces(actor=_actor(), cursor=None, limit=1, q=None)
    assert page.next_cursor is not None
    other = Session(actor_id="someone", actor_name="someone", allowed_roles=["ANALYST"])
    details: set[str] = set()
    with pytest.raises(DomainError) as wrong_actor:
        service.list_workspaces(actor=other, cursor=page.next_cursor, limit=1, q=None)
    details.add(wrong_actor.value.detail)
    with pytest.raises(DomainError) as wrong_limit:
        service.list_workspaces(actor=_actor(), cursor=page.next_cursor, limit=2, q=None)
    details.add(wrong_limit.value.detail)
    with pytest.raises(DomainError) as wrong_q:
        service.list_workspaces(actor=_actor(), cursor=page.next_cursor, limit=1, q="ws")
    details.add(wrong_q.value.detail)
    assert len(details) == 1  # 三种原因同一句 detail，不给探测面
    assert wrong_actor.value.code == "BAD_CURSOR"


def test_cursor_secret_is_persisted_stable_and_0600(tmp_path: Path) -> None:
    first = app_workspace.load_cursor_secret(tmp_path)
    second = app_workspace.load_cursor_secret(tmp_path)
    assert first == second and len(first) == app_workspace.CURSOR_KEY_BYTES
    key_file = tmp_path / "state" / "cursor.key"
    assert key_file.is_file()
    assert (key_file.stat().st_mode & 0o777) == 0o600
    key_file.write_bytes(b"too-short")
    with pytest.raises(ValueError):
        app_workspace.load_cursor_secret(tmp_path)


def test_workspace_service_does_not_create_cursor_key_until_needed(
    config: AppConfig, engine: Engine
) -> None:
    """构造服务不该在数据目录落文件：否则 doctor 的 data_dir WARN 会被悄悄抹平。"""
    service = _workspace_service(config, engine, FixedClock(T0))
    assert service is not None
    assert not (config.data_dir / "state" / "cursor.key").exists()


def test_audit_role_prefers_operator() -> None:
    assert app_workspace.audit_role_of(_actor()) == "OPERATOR"
    analyst = Session(actor_id="a", actor_name="a", allowed_roles=["ANALYST", "REVIEWER"])
    assert app_workspace.audit_role_of(analyst) == "ANALYST"
