"""R17 · M2-01/S2b-2：``api/app.py`` 两个 service 注入位的守护（派单文 §4 的 G1–G9）。

判据一律走**集合／身份对撞**（A115）：形参面用 ``inspect`` 解析后实取、装配面用 ``is`` 判身份、
跨文件的 ``app.state`` 键名用 AST 双向对撞、挂载面与中间件顺序用 AST **有序清单**逐字相等，
全程不拿「计数 == N」当唯一判据。本文件不新增任何 ``include_router``，也不得改动 ``src/**``
（本棒写权面恰好 2 件）。时钟一律 ``campaignlab.clock.FixedClock``（红线 3 / D-045）。
"""

from __future__ import annotations

import ast
import inspect
import typing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from campaignlab.api import app as app_module
from campaignlab.api import deps
from campaignlab.api.app import create_app
from campaignlab.api.common import Health, OriginHostGuard
from campaignlab.api.deps import get_health_service
from campaignlab.clock import FixedClock
from campaignlab.config import AppConfig, load_config

REPO = Path(__file__).resolve().parents[2]
APP_SOURCE = REPO / "src" / "campaignlab" / "api" / "app.py"
DEPS_SOURCE = REPO / "src" / "campaignlab" / "api" / "deps.py"
T0 = datetime(2026, 11, 13, 1, 0, 0, tzinfo=UTC)
TESTSERVER = OriginHostGuard(frozenset({"testserver"}), frozenset({"http://testserver"}))

# 尚不存在的两个 router 模块名（A217 ③ 归 S3/S4）：按 §2.6 用拼接构造，禁直写禁串。
_BANNED_ROUTER_MODULES = frozenset(
    f"campaignlab.api.{leaf}" for leaf in ("activ" + "ities", "rul" + "es")
)

#: G3：条件装配面的期望字典——五个服务形参各对应一个同名 app.state 属性。
#: 无条件赋值不会进入该字典，故这条断言与「不注入就不装配」同源。
EXPECTED_WIRING = {
    "session_service": "session_service",
    "health_service": "health_service",
    "workspace_service": "workspace_service",
    "activity_service": "activity_service",
    "rule_service": "rule_service",
}

#: G1：kwonly 的期望有序清单（尾部追加两个注入位，既有五个一字不改）。
EXPECTED_KWONLY = [
    "clock",
    "guard",
    "session_service",
    "health_service",
    "workspace_service",
    "activity_service",
    "rule_service",
]

#: G6：挂载行的期望有序清单（新增挂载或换序都会破坏它）。
EXPECTED_MOUNT_LINES = [
    "app.include_router(health.router)",
    "app.include_router(session_router)",
    "app.include_router(workspaces_router)",
    "app.include_router(jobs_router)",
]


@pytest.fixture
def config(tmp_path: Path) -> AppConfig:
    return load_config(environ={"CAMPAIGNLAB_DATA_DIR": str(tmp_path)}, home=tmp_path)


def _protocol_members(port: type) -> frozenset[str]:
    """动态取 Protocol 成员面（public API；禁在测试里硬编码方法名清单当权威）。"""
    return frozenset(typing.get_protocol_members(port))


def _stub_for(port: type) -> Any:
    """按 Protocol 成员面**动态**造结构合规的替身（``_state_service`` 只查结构）。"""
    members = _protocol_members(port)
    assert members, f"{port} 的成员面为空，替身将失去结构意义"
    namespace: dict[str, Any] = {name: (lambda *args, **kwargs: None) for name in sorted(members)}
    stub = type("ServiceStub", (), namespace)()
    assert isinstance(stub, port), f"替身未满足 {port} 的结构"
    return stub


def _activity_stub() -> deps.ActivityService:
    return cast("deps.ActivityService", _stub_for(deps.ActivityService))


def _rule_stub() -> deps.RuleService:
    return cast("deps.RuleService", _stub_for(deps.RuleService))


def _calls_named(tree: ast.AST, name: str) -> list[ast.Call]:
    """取 ``foo(...)`` 与 ``x.foo(...)`` 两种调用点（按源码顺序无关，调用方自己排 lineno）。"""
    out: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        by_name = isinstance(func, ast.Name) and func.id == name
        by_attr = isinstance(func, ast.Attribute) and func.attr == name
        if by_name or by_attr:
            out.append(node)
    return out


def _conditional_state_wiring(source: str) -> dict[str, str]:
    """取「``if <param> is not None:`` → ``app.state.<attr> = <param>``」的条件装配面。"""
    wiring: dict[str, str] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            not isinstance(test, ast.Compare)
            or len(test.ops) != 1
            or not isinstance(test.ops[0], ast.Is | ast.IsNot)  # IsNot 是单个谓词
        ):
            continue
        left, comparator = test.left, test.comparators[0]
        if not isinstance(left, ast.Name) or not (
            isinstance(comparator, ast.Constant) and comparator.value is None
        ):
            continue
        param = left.id
        for stmt in node.body:
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1):
                continue
            target, value = stmt.targets[0], stmt.value
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Attribute)
                and target.value.attr == "state"
                and isinstance(value, ast.Name)
                and value.id == param
            ):
                wiring[param] = target.attr
    return wiring


def _provider_state_reads(source: str) -> dict[str, str]:
    """取 ``api/deps.py`` 各提供器实际读取的 ``app.state`` 键名（``_state_service`` 第二实参）。"""
    reads: dict[str, str] = {}
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.FunctionDef) and node.name.startswith("get_")):
            continue
        for call in _calls_named(node, "_state_service"):
            if len(call.args) < 2:
                continue
            attribute = call.args[1]
            if isinstance(attribute, ast.Constant):
                reads[node.name] = str(attribute.value)
    return reads


class _StubHealthService:
    """既有 health 端口的替身（G8 用；体例照抄 ``tests/unit/test_api_app.py``）。"""

    def __init__(self, snapshot: Health) -> None:
        self._snapshot = snapshot

    def snapshot(self) -> Health:
        return self._snapshot


def test_g1_signature_is_the_frozen_injection_surface() -> None:
    """G1：形参面 + 注解**解析后**对撞端口对象（本文件 ``from __future__`` ⇒ 注解是字符串）。"""
    params = inspect.signature(app_module.create_app, eval_str=True).parameters
    positional = [
        name
        for name, param in params.items()
        if param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
    ]
    kwonly = [name for name, param in params.items() if param.kind is param.KEYWORD_ONLY]
    assert positional == ["config"]
    assert kwonly == EXPECTED_KWONLY
    assert all(param.default is None for param in params.values())
    for name, port in (
        ("activity_service", deps.ActivityService),
        ("rule_service", deps.RuleService),
    ):
        resolved = typing.get_args(params[name].annotation)
        assert resolved == (port, type(None)), f"{name} 解析后的注解是 {resolved}"


def test_g2_both_new_services_are_attached_by_identity(config: AppConfig) -> None:
    """G2：注入即装配，且装的是同一个对象（身份判定，非相等）。"""
    activity, rule = _activity_stub(), _rule_stub()
    app = create_app(
        config,
        clock=FixedClock(T0),
        guard=TESTSERVER,
        activity_service=activity,
        rule_service=rule,
    )
    assert app.state.activity_service is activity
    assert app.state.rule_service is rule


def test_g3_bare_app_assembles_neither_new_slot(config: AppConfig) -> None:
    """G3：不注入就不装配——属性根本不存在，且条件装配面逐字等于期望字典。"""
    app = create_app(config, clock=FixedClock(T0), guard=TESTSERVER)
    assert not hasattr(app.state, "activity_service")
    assert not hasattr(app.state, "rule_service")
    assert _conditional_state_wiring(APP_SOURCE.read_text(encoding="utf-8")) == EXPECTED_WIRING


def test_g4_the_two_new_slots_are_independent(config: AppConfig) -> None:
    """G4：只给其一 ⇒ 另一个不存在（两个 ``if`` 相互独立，不是 ``and`` 连写）。"""
    activity, rule = _activity_stub(), _rule_stub()
    only_activity = create_app(config, guard=TESTSERVER, activity_service=activity)
    assert only_activity.state.activity_service is activity
    assert not hasattr(only_activity.state, "rule_service")
    only_rule = create_app(config, guard=TESTSERVER, rule_service=rule)
    assert only_rule.state.rule_service is rule
    assert not hasattr(only_rule.state, "activity_service")


def test_g5_existing_assembly_and_openapi_face_untouched(config: AppConfig) -> None:
    """G5：既有装配面一字未改（含身份），第二个 OpenAPI 面仍未开。"""
    clock = FixedClock(T0)
    session = _stub_for(deps.SessionService)
    health = _stub_for(deps.HealthService)
    workspace = _stub_for(deps.WorkspaceService)
    activity, rule = _activity_stub(), _rule_stub()
    app = create_app(
        config,
        clock=clock,
        guard=TESTSERVER,
        session_service=session,
        health_service=health,
        workspace_service=workspace,
        activity_service=activity,
        rule_service=rule,
    )
    assert app.state.config is config
    assert app.state.clock is clock
    assert app.state.guard is TESTSERVER
    attached = {
        "session_service": session,
        "health_service": health,
        "workspace_service": workspace,
        "activity_service": activity,
        "rule_service": rule,
    }
    for name, service in attached.items():
        assert getattr(app.state, name) is service, f"{name} 未以身份装配"
    assert app.openapi_url is None
    assert app.docs_url is None
    assert app.redoc_url is None


def test_g6_mount_and_middleware_surface_unchanged() -> None:
    """G6：挂载行有序清单、被禁的 router import、中间件先后与 error-handler 位置全部对撞。"""
    source = APP_SOURCE.read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source)
    mount_pairs = sorted(
        (node.lineno, lines[node.lineno - 1].strip())
        for node in _calls_named(tree, "include_router")
    )
    ordered = [text for _, text in mount_pairs]
    assert ordered == EXPECTED_MOUNT_LINES
    assert [text for text in ordered if "jobs" in text] == ["app.include_router(jobs_router)"]
    imported_modules = {
        node.module for node in tree.body if isinstance(node, ast.ImportFrom) and node.module
    }
    banned_hits = imported_modules & _BANNED_ROUTER_MODULES
    assert not banned_hits, f"A217 ③：不得 import {sorted(banned_hits)}"

    middleware: list[str] = []
    middleware_lines: list[int] = []
    for call in _calls_named(tree, "add_middleware"):
        first = call.args[0] if call.args else None
        if isinstance(first, ast.Name):
            middleware.append(first.id)
            middleware_lines.append(call.lineno)
    assert middleware == ["BaseHTTPMiddleware", "CORSMiddleware"]

    handler_lines = sorted(call.lineno for call in _calls_named(tree, "install_error_handlers"))
    assert handler_lines, "install_error_handlers(app) 的调用必须在场"
    assert all(line < handler_lines[0] for line in middleware_lines), (
        f"中间件必须早于 install_error_handlers：{middleware_lines} vs {handler_lines}"
    )


def test_g7_public_surface_and_cors_constants_unchanged() -> None:
    """G7：``__all__`` 双向差集为 ∅，两个 CORS 常量与冻结元组逐字相等（含顺序）。"""
    frozen = {"ALLOWED_HEADERS", "ALLOWED_METHODS", "create_app", "origin_host_guard_middleware"}
    assert set(app_module.__all__) ^ frozen == set()
    assert app_module.ALLOWED_METHODS == (
        "DELETE",
        "GET",
        "HEAD",
        "OPTIONS",
        "PATCH",
        "POST",
        "PUT",
    )
    assert app_module.ALLOWED_HEADERS == (
        "Content-Type",
        "ETag",
        "Idempotency-Key",
        "If-Match",
        "X-Request-Id",
    )


def test_g8_provider_keys_match_and_health_chain_works(config: AppConfig) -> None:
    """G8：新增键名 ↔ ``deps.py`` 读取口径双向对撞；注入后既有路由仍 200 且带 X-Request-Id。"""
    wiring = _conditional_state_wiring(APP_SOURCE.read_text(encoding="utf-8"))
    reads = _provider_state_reads(DEPS_SOURCE.read_text(encoding="utf-8"))
    assert reads["get_activity_service"] == wiring["activity_service"]
    assert reads["get_rule_service"] == wiring["rule_service"]
    assert {reads["get_activity_service"], reads["get_rule_service"]} == {
        "activity_service",
        "rule_service",
    }

    payload = Health(
        status="READY",
        app_version=config.app_version,
        contract_version=config.contract_version,
        worker="READY",
        schema_revision="0001_initial_schema",
    )
    app = create_app(
        config,
        clock=FixedClock(T0),
        guard=TESTSERVER,
        activity_service=_activity_stub(),
        rule_service=_rule_stub(),
    )
    app.dependency_overrides[get_health_service] = lambda: _StubHealthService(payload)
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == payload.model_dump(mode="json")
    assert response.headers["X-Request-Id"]


def test_g9_unassembled_services_still_yield_500_problem(config: AppConfig) -> None:
    """G9：只注入两个新服务、health 仍未装配 ⇒ 既有 500 Problem 收敛行为未回归。"""
    app = create_app(
        config,
        clock=FixedClock(T0),
        guard=TESTSERVER,
        activity_service=_activity_stub(),
        rule_service=_rule_stub(),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert body["issues"] == []
    assert "RuntimeError" not in body["detail"]
    assert "Traceback" not in body["detail"]
