"""M0-02 · S3b 的样板级自证面（派单 §7.4 的 6 项）。

钉住的是样板而非用例逻辑：① 4 条路由存在且 ``operationId`` 与函数名逐字对应；② 逐 op 实现的
响应状态码集合 == 切片声明的集合（计数从切片现值读，**不写死**，D-012／D-014）；③
``listWorkspaces`` 的 query 形参恰为 ``{cursor, limit, q}``（CR-002 选项 B，禁含 ``status``）；
④ 422 的 ``INVALID``+``SCOPE`` 分支已随参数一起删除（无触发面）；⑤ A69「不注入就不装配」
在挂载面的语义；⑥ ``api/app.py`` 只加了 A85 允许的挂载行（且没有 ``jobs.router``，A84）。

完整的契约测试参数化（202/409/412/422 各分支、Problem 结构、ETag 与 412、``Idempotency-Key``
重放一次生效）属 **M0-02/S4（Round 8）**，A84 已把其产出收窄到 ``tests/api/**``。
"""

from __future__ import annotations

import inspect
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Final

from fastapi import FastAPI
from fastapi.routing import APIRoute

from campaignlab.api import session as session_api
from campaignlab.api import workspaces as workspaces_api
from campaignlab.api.app import create_app
from campaignlab.api.common import OriginHostGuard, Session, WorkspaceCreate, WorkspacePage
from campaignlab.application.session_service import SessionCookie, SessionRecord
from campaignlab.application.workspace_service import WorkspaceCreateOutcome
from campaignlab.config import API_PREFIX, AppConfig, load_config

_REPO: Final = Path(__file__).resolve().parents[2]
_SLICE: Final = json.loads(
    (_REPO / "orchestrator/handoff/M0-02-S3b.slice.json").read_text(encoding="utf-8")
)
_GUARD: Final = OriginHostGuard(frozenset({"testserver"}), frozenset({"http://testserver"}))

#: ``operationId -> (路由函数, 期望函数名, method, 切片里的 path, 所属路由模块)``。
_OPS: Final = {
    "exchangeSession": (
        session_api.exchange_session,
        "exchange_session",
        "post",
        "/session/exchange",
        session_api,
    ),
    "getSession": (session_api.get_session, "get_session", "get", "/session", session_api),
    "listWorkspaces": (
        workspaces_api.list_workspaces,
        "list_workspaces",
        "get",
        "/workspaces",
        workspaces_api,
    ),
    "createWorkspace": (
        workspaces_api.create_workspace,
        "create_workspace",
        "post",
        "/workspaces",
        workspaces_api,
    ),
}


class _StubSessionService:
    """只用于满足 ``deps.SessionService`` 端口（挂载面用例不执行任何用例逻辑）。"""

    def exchange(self, token: str, *, now: datetime) -> SessionRecord:
        raise AssertionError("S3b 挂载面用例不该调用 service")

    def resolve(self, session_id: str | None, *, now: datetime) -> SessionRecord:
        raise AssertionError("S3b 挂载面用例不该调用 service")

    def cookie(self, record: SessionRecord, *, now: datetime) -> SessionCookie:
        raise AssertionError("S3b 挂载面用例不该调用 service")


class _StubWorkspaceService:
    """只用于满足 ``deps.WorkspaceService`` 端口。"""

    def list_workspaces(
        self, *, actor: Session, cursor: str | None, limit: int, q: str | None
    ) -> WorkspacePage:
        raise AssertionError("S3b 挂载面用例不该调用 service")

    def create_workspace(
        self,
        *,
        payload: WorkspaceCreate,
        body: bytes,
        idempotency_key: str,
        actor: Session,
        request_id: str,
    ) -> WorkspaceCreateOutcome:
        raise AssertionError("S3b 挂载面用例不该调用 service")


def _config(tmp_path: Path) -> AppConfig:
    return load_config(environ={"CAMPAIGNLAB_DATA_DIR": str(tmp_path)}, home=tmp_path)


def _route_for(module: Any, full_path: str, method: str) -> APIRoute:
    for route in module.router.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = route.methods
        if route.path == full_path and methods is not None and method.upper() in methods:
            return route
    raise AssertionError("路由缺失：" + method.upper() + " " + full_path)


def _mounted_routers(app: FastAPI) -> list[Any]:
    """``include_router()`` 在 FastAPI 0.162 里落成 ``_IncludedRouter`` 包装，取其原 router。"""
    mounted: list[Any] = []
    for entry in app.routes:
        inner: Any = getattr(entry, "original_router", None)
        if inner is not None:
            mounted.append(inner)
    return mounted


def _slice_statuses(operation_id: str) -> set[str]:
    declared: Any = _SLICE["operations"][operation_id]["operation"]["responses"]
    return {str(status) for status in declared}


def test_route_paths_and_methods_match_slice() -> None:
    for operation_id, (_fn, _name, method, suffix, module) in _OPS.items():
        declared: Any = _SLICE["operations"][operation_id]
        assert declared["method"].lower() == method, operation_id
        assert declared["path"] == suffix, operation_id
        _route_for(module, API_PREFIX + suffix, method)


def test_operation_id_and_function_name_match_slice() -> None:
    for operation_id, (fn, func_name, method, suffix, module) in _OPS.items():
        route = _route_for(module, API_PREFIX + suffix, method)
        assert route.operation_id == operation_id
        assert route.endpoint is fn
        assert fn.__name__ == func_name


def test_implemented_statuses_equal_slice_statuses_per_op() -> None:
    for operation_id, (_fn, _name, method, suffix, module) in _OPS.items():
        expected = _slice_statuses(operation_id)
        route = _route_for(module, API_PREFIX + suffix, method)
        implemented = {str(status) for status in route.responses}
        assert implemented == expected, operation_id
        assert len(implemented) == len(expected)


def test_list_workspaces_query_params_are_exactly_cursor_limit_q() -> None:
    route = _route_for(workspaces_api, API_PREFIX + "/workspaces", "get")
    names = {field.name for field in route.dependant.query_params}
    assert names == {"cursor", "limit", "q"}
    assert "status" not in names


def test_invalid_scope_branch_is_absent_and_422_still_declared() -> None:
    needle = "INVALID" + "_SCOPE"
    for module in (session_api, workspaces_api):
        assert needle not in inspect.getsource(module)
    assert "422" in _slice_statuses("listWorkspaces")


def test_app_mounts_routers_only_when_services_injected(tmp_path: Path) -> None:
    bare = create_app(_config(tmp_path), guard=_GUARD)
    bare_mounted = _mounted_routers(bare)
    assert session_api.router not in bare_mounted
    assert workspaces_api.router not in bare_mounted

    wired = create_app(
        _config(tmp_path),
        guard=_GUARD,
        session_service=_StubSessionService(),
        workspace_service=_StubWorkspaceService(),
    )
    wired_mounted = _mounted_routers(wired)
    assert session_api.router in wired_mounted
    assert workspaces_api.router in wired_mounted


def test_app_py_contains_only_the_a85_mount_lines() -> None:
    source = (_REPO / "src/campaignlab/api/app.py").read_text(encoding="utf-8")
    pairs = (
        "    if session_service is not None:\n        app.include_router(session_router)",
        "    if workspace_service is not None:\n        app.include_router(workspaces_router)",
    )
    for pair in pairs:
        assert pair in source
    assert "import router as session_router" in source
    assert "import router as workspaces_router" in source
    mounted_lines = [
        line for line in source.splitlines() if line.strip().startswith("app.include_router(")
    ]
    assert len(mounted_lines) == 3
    assert not any("jobs" in line for line in mounted_lines)
    assert len([line for line in source.splitlines() if "session_router" in line]) <= 3
    assert len([line for line in source.splitlines() if "workspaces_router" in line]) <= 3
