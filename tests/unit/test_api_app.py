"""S3c：``create_app()`` 的装配面（A10 边界 + Problem 形错误体 + 依赖注入位）。

钉住四件事：

1. **不暴露第二个 OpenAPI 面**（``api/__init__.py``）：
   ``openapi_url`` / ``docs_url`` / ``redoc_url`` 全为 None；
2. **A10**：S3c 不得挂载 jobs 路由（属 M0-04/S4）；
3. **每个响应都是 Problem 形且带 X-Request-Id**：404（未知路径）、403（回环守卫）、
   500（S3d 未装配 → NotImplementedError 被兜底）三条路径各测一次；
4. **依赖注入位可用**：``app.dependency_overrides`` 注入替身后 ``getHealth`` 立刻 200，
   证明 ``api/deps.py`` 的端口形状对 S3b/S3d 是即插即用的。
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from campaignlab.api.app import create_app
from campaignlab.api.common import Health, OriginHostGuard
from campaignlab.api.deps import get_health_service
from campaignlab.config import AppConfig, load_config

REPO = Path(__file__).resolve().parents[2]
TESTSERVER = OriginHostGuard(frozenset({"testserver"}), frozenset({"http://testserver"}))
LOOPBACK_ONLY = OriginHostGuard(frozenset({"127.0.0.1:8000"}), frozenset({"http://127.0.0.1:8000"}))

#: ``TESTSERVER`` 白名单里的 Origin 值（R18-12）：FU-60 探针必须显式带上，
#: 否则非安全方法会在路由前被 ``OriginHostGuard`` 判 403，掩盖 404 事实。
LOOPBACK_ORIGIN: dict[str, str] = {"Origin": "http://testserver"}


class _StubHealthService:
    """替身：只为验证依赖注入位可用（真实的 HealthService 属 S3d）。"""

    def __init__(self, snapshot: Health) -> None:
        self._snapshot = snapshot

    def snapshot(self) -> Health:
        return self._snapshot


def _config(tmp_path: Path) -> AppConfig:
    return load_config(environ={"CAMPAIGNLAB_DATA_DIR": str(tmp_path)}, home=tmp_path)


def test_no_second_openapi_surface(tmp_path: Path) -> None:
    app = create_app(_config(tmp_path), guard=TESTSERVER)
    assert app.openapi_url is None
    assert app.docs_url is None
    assert app.redoc_url is None


def test_jobs_router_is_not_mounted_by_s3c(tmp_path: Path) -> None:
    """A10：``include_router(jobs.router)`` 属 M0-04/S4，S3c 不得添加。"""
    with TestClient(
        create_app(_config(tmp_path), guard=TESTSERVER), raise_server_exceptions=False
    ) as client:
        # 结构断言不可靠：本版 FastAPI 的 include_router 产出 _IncludedRouter（无 .path），
        # 故改用**行为**断言——jobs / workspaces 路由不存在必须 404 Problem。
        for probe in ("/api/v1/jobs", "/api/v1/jobs/job-1", "/api/v1/workspaces"):
            response = client.get(probe)
            assert response.status_code == 404, probe
            assert response.json()["code"] == "RESOURCE_NOT_FOUND", probe
        # health 路由确实挂上了：500 来自「S3d 未装配」，而非「路由不存在」的 404
        assert client.get("/api/v1/health").status_code == 500


def test_unknown_route_is_problem_404_with_request_id(tmp_path: Path) -> None:
    with TestClient(create_app(_config(tmp_path), guard=TESTSERVER)) as client:
        response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "RESOURCE_NOT_FOUND"
    assert body["status"] == 404
    assert body["type"] == "urn:campaignlab:problem:resource_not_found"
    assert response.headers["X-Request-Id"] == body["request_id"]
    assert set(body) == {"type", "title", "status", "code", "detail", "request_id", "issues"}


def test_origin_host_guard_returns_problem_403(tmp_path: Path) -> None:
    """守卫在用户中间件层抛出，必须就地翻译成 403 而不是被兜成 500。"""
    with TestClient(create_app(_config(tmp_path), guard=LOOPBACK_ONLY)) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "ORIGIN_DENIED"
    assert body["status"] == 403
    assert response.headers["X-Request-Id"]


def test_health_is_500_problem_while_service_is_pending(tmp_path: Path) -> None:
    """S3d 未落地：提供器抛 NotImplementedError → 500 Problem，且不回显堆栈。"""
    with TestClient(
        create_app(_config(tmp_path), guard=TESTSERVER), raise_server_exceptions=False
    ) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert body["issues"] == []
    assert body["request_id"] in body["detail"]
    assert "NotImplementedError" not in body["detail"]
    assert "Traceback" not in body["detail"]


def test_health_returns_200_when_dependency_overridden(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = Health(
        status="READY",
        app_version=config.app_version,
        contract_version=config.contract_version,
        worker="READY",
        schema_revision="0001_initial_schema",
    )
    app = create_app(config, guard=TESTSERVER)
    app.dependency_overrides[get_health_service] = lambda: _StubHealthService(payload)
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == payload.model_dump(mode="json")
    assert response.headers["X-Request-Id"]


def test_activities_router_is_not_mounted_without_activity_service(tmp_path: Path) -> None:
    """FU-60（编排器在 M2-01/S4 入库批同批补，A257 的裁定落地面；纵深防御第二层）。

    裸 ``create_app()``（不注入 ``activity_service``）⇒ activities 的 **4** 条路由**不得**挂载，
    必须 404 Problem。先例＝本文件 ``test_jobs_router_is_not_mounted_by_s3c`` 的 jobs 同形探针
    （该探针只覆盖 jobs，对 activities **0 命中** —— 这正是 lane S3 的 PC-3 与本棒 lane S4 的
    PC-1 先后实测到的「无牙」缺口）。路径面按 **PRE-30** 实测取值（``activities.router.routes``
    的 4 条，方法与路径逐字对撞），**禁**手写想象路径。
    """
    with TestClient(
        create_app(_config(tmp_path), guard=TESTSERVER), raise_server_exceptions=False
    ) as client:
        for method, probe in (
            ("GET", "/api/v1/workspaces/ws-1/activities"),
            ("POST", "/api/v1/workspaces/ws-1/activities"),
            ("GET", "/api/v1/workspaces/ws-1/activities/act-1"),
            ("PATCH", "/api/v1/workspaces/ws-1/activities/act-1"),
        ):
            #: **R18-12**：必须带白名单 ``Origin``。实测 ``OriginHostGuard`` 是 BaseHTTPMiddleware，
            #: 对非安全方法（POST/PATCH）**先于路由**判来源；TestClient 默认不带 Origin ⇒ 会得到
            #: 403 ``ORIGIN_DENIED`` 而**掩盖**「路由未挂载 ⇒ 404」这一本守护要盯的事实。
            response = client.request(method, probe, headers=LOOPBACK_ORIGIN)
            assert response.status_code == 404, (method, probe)
            assert response.json()["code"] == "RESOURCE_NOT_FOUND", (method, probe)


def test_rules_router_is_not_mounted_without_rule_service(tmp_path: Path) -> None:
    """FU-60：裸 ``create_app()``（不注入 ``rule_service``）⇒ rules 的 **7** 条路由**不得**挂载。

    与 activities 探针**同形**（A259 的精确集合不变量盯 **import 面**，本探针盯**运行期挂载面**，
    两层互不替代）。7 条路径按 **PRE-30** 实测取自 ``rules.router.routes``（5 个唯一 path / 7 个
    operationId），方法逐条与装饰器一致 —— 用 ``client.request(method, …)`` 而非一律 GET，
    以免「方法不匹配 405」把「路由未挂载 404」掩盖掉（后者才是本守护要盯的事实）。
    """
    with TestClient(
        create_app(_config(tmp_path), guard=TESTSERVER), raise_server_exceptions=False
    ) as client:
        for method, probe in (
            ("GET", "/api/v1/workspaces/ws-1/activities/act-1/rules"),
            ("POST", "/api/v1/workspaces/ws-1/activities/act-1/rules"),
            ("GET", "/api/v1/workspaces/ws-1/rules/rule-1"),
            ("PATCH", "/api/v1/workspaces/ws-1/rules/rule-1"),
            ("POST", "/api/v1/workspaces/ws-1/rules/rule-1/confirm"),
            ("GET", "/api/v1/workspaces/ws-1/rules/rule-1/checks"),
            ("GET", "/api/v1/workspaces/ws-1/rules/rule-1/diff"),
        ):
            #: **R18-12**：必须带白名单 ``Origin``。实测 ``OriginHostGuard`` 是 BaseHTTPMiddleware，
            #: 对非安全方法（POST/PATCH）**先于路由**判来源；TestClient 默认不带 Origin ⇒ 会得到
            #: 403 ``ORIGIN_DENIED`` 而**掩盖**「路由未挂载 ⇒ 404」这一本守护要盯的事实。
            response = client.request(method, probe, headers=LOOPBACK_ORIGIN)
            assert response.status_code == 404, (method, probe)
            assert response.json()["code"] == "RESOURCE_NOT_FOUND", (method, probe)
