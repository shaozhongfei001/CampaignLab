"""M0-02/S4 契约测试的公共装配（写集仅 ``tests/api/**``）。

装配口径完全沿用 ``tests/unit/test_s3d_application.py`` 与 ``tests/unit/test_s3b_routes.py``
已落地的做法：``create_app()`` 的六个注入位（config／clock／guard／三个 service）显式给齐，
「不注入就不装配」（裁定 A69）；DDL 直接从活契约 ``contracts/sqlite-v1.sql`` 建库，
时间一律走 ``FixedClock`` 显式时钟（全仓禁「当前时间」字面量调用，含本文件的注释）。

状态码集合的**权威**是路由装饰器上的 ``declared_responses()``（裁定 A95），
本目录因此不复制任何一份状态码清单；切片 ``M0-02.slice.json`` 只用来比对「实现声明 == 切片声明」。
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from campaignlab.api.app import create_app
from campaignlab.api.common import OriginHostGuard, Session
from campaignlab.application.health_service import HealthService
from campaignlab.application.session_service import (
    SESSION_COOKIE_NAME,
    SessionService,
    SessionStore,
    SessionTokenStore,
)
from campaignlab.application.workspace_service import WorkspaceService
from campaignlab.clock import FixedClock
from campaignlab.config import API_PREFIX, AppIdentity, load_config
from campaignlab.infra.db.engine import make_engine

REPO: Final = Path(__file__).resolve().parents[2]
SLICE: Final[dict[str, Any]] = json.loads(
    (REPO / "orchestrator/handoff/M0-02.slice.json").read_text(encoding="utf-8")
)
LIVE_CONTRACT: Final[dict[str, Any]] = json.loads(
    (REPO / "contracts/openapi.json").read_text(encoding="utf-8")
)
DDL: Final = REPO / "contracts/sqlite-v1.sql"

#: 显式时钟基准（与 S3d 用例同一支配合成时刻）。
T0: Final = datetime(2026, 11, 13, 1, 0, 0, tzinfo=UTC)
TOKEN_TTL: Final = 60
SESSION_TTL: Final = 3600
#: ``TestClient`` 的默认 Host 是 ``testserver``，POST 必须显式带上白名单 Origin 才不被守卫拦下。
GUARD: Final = OriginHostGuard(frozenset({"testserver"}), frozenset({"http://testserver"}))
TEST_ORIGIN: Final = "http://testserver"
EVIL_ORIGIN: Final = "http://evil.invalid"
EVIL_HOST: Final = "evil.example"

IDENTITY: Final = AppIdentity(
    actor_id="tester",
    actor_name="tester",
    allowed_roles=("OPERATOR", "DESIGNER", "DATA_OWNER", "ANALYST", "TESTER", "REVIEWER"),
)


def actor() -> Session:
    """契约里 ``Session`` 的期望形状（与 ``IDENTITY`` 同源，禁各处另造一份字面量）。"""
    return Session(
        actor_id=IDENTITY.actor_id,
        actor_name=IDENTITY.actor_name,
        allowed_roles=list(IDENTITY.allowed_roles),
    )


def route_for(target: Any, operation_id: str) -> APIRoute:
    """按 ``operationId`` 取路由：模块、``APIRouter`` 或 ``FastAPI`` 都可。"""
    # 模块对象上没有 ``routes``，故额外翻一层 ``module.router``；app 上则翻 ``_IncludedRouter``。
    candidates: list[Any] = list(getattr(target, "routes", []))
    inner_router = getattr(target, "router", None)
    if inner_router is not None:
        candidates.extend(list(getattr(inner_router, "routes", [])))
    for entry in candidates:
        inner = getattr(entry, "original_router", None)
        if inner is not None:
            candidates.extend(getattr(inner, "routes", []))
    for route in candidates:
        if isinstance(route, APIRoute) and route.operation_id == operation_id:
            return route
    raise AssertionError("路由缺失 operationId：" + operation_id)


def slice_statuses(operation_id: str) -> set[str]:
    """切片声明的响应码集合（只用于比对，不作为断言的期望值来源）。"""
    declared: Any = SLICE["operations"][operation_id]["operation"]["responses"]
    return {str(status) for status in declared}


class Harness:
    """一份 DB + 一套真实服务，多个 client（不同时刻／不同上限／不同白名单）。"""

    def __init__(self, tmp_path: Path) -> None:
        self.db_path = tmp_path / "campaignlab.db"
        raw = sqlite3.connect(self.db_path)
        try:
            raw.executescript(DDL.read_text(encoding="utf-8"))
            raw.commit()
        finally:
            raw.close()
        self.engine: Engine = make_engine(f"sqlite:///{self.db_path}")
        self.config = load_config(environ={"CAMPAIGNLAB_DATA_DIR": str(tmp_path)}, home=tmp_path)
        self.clock = FixedClock(T0)
        self.session_service = SessionService(
            tokens=SessionTokenStore(ttl_seconds=TOKEN_TTL),
            sessions=SessionStore(ttl_seconds=SESSION_TTL),
        )
        self.workspace_service = WorkspaceService(
            engine=self.engine, clock=self.clock, config=self.config
        )
        self.health_service = HealthService(
            config=self.config, clock=self.clock, engine=self.engine
        )

    def mint_token(self, *, at: datetime = T0) -> str:
        return self.session_service.tokens.mint(IDENTITY, at)

    def make_app(
        self,
        *,
        at: datetime = T0,
        max_body_bytes: int | None = None,
        guard: OriginHostGuard = GUARD,
        with_session: bool = True,
        with_workspace: bool = True,
        with_health: bool = False,
    ) -> FastAPI:
        config = (
            self.config
            if max_body_bytes is None
            else replace(self.config, max_json_body_bytes=max_body_bytes)
        )
        return create_app(
            config,
            clock=FixedClock(at),
            guard=guard,
            session_service=self.session_service if with_session else None,
            workspace_service=self.workspace_service if with_workspace else None,
            health_service=self.health_service if with_health else None,
        )

    def client(self, **kwargs: Any) -> TestClient:
        return TestClient(self.make_app(**kwargs), headers={"Origin": TEST_ORIGIN})

    def exchange(
        self, *, at: datetime = T0, token: str | None = None, **kwargs: Any
    ) -> tuple[TestClient, Any]:
        """换取会话并把 Cookie 装回同一个 client（``Path=/api/v1`` 由服务端给出）。"""

        client = self.client(at=at, **kwargs)
        payload = {"token": self.mint_token(at=T0) if token is None else token}
        response = client.post(f"{API_PREFIX}/session/exchange", json=payload)
        return client, response

    def authed_client(self, *, at: datetime = T0) -> TestClient:
        client, response = self.exchange(at=at)
        assert response.status_code == 200, response.text
        return client

    def count_workspaces(self) -> int:
        raw = sqlite3.connect(self.db_path)
        try:
            row = raw.execute("SELECT COUNT(*) FROM workspaces").fetchone()
        finally:
            raw.close()
        return int(row[0])


@pytest.fixture
def harness(tmp_path: Path) -> Harness:
    return Harness(tmp_path)


@pytest.fixture
def authed(harness: Harness) -> TestClient:
    return harness.authed_client()


def session_cookie_header(value: str) -> dict[str, str]:
    return {"Cookie": f"{SESSION_COOKIE_NAME}={value}"}


def delta(seconds: int) -> timedelta:
    return timedelta(seconds=seconds)
