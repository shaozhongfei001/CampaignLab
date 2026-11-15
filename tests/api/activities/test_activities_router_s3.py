"""M2-01/S3 端到端守护：注入的 ``activity_service`` 与 ``deps.get_activity_service`` 的对象同一性。

义务来源（``tasks["M2-01"].s3_precondition_note_R17.obligation`` 原文）：注入
``activity_service`` 后经 TestClient 走一条真实 activities 路由，断言
``deps.get_activity_service`` 取到的对象与注入对象**同一**（``is``），闭合 S2b-2 只做到
「键名双向对撞」的代理证明。``is`` 是进程内对象身份判据：本文件在桩方法体内捕获
被依赖链解析到的 ``self`` 本身再对撞，**禁**拿响应体字段或响应头做代理替代
（PC-1 的变异对照正是沿这条线设计）。

桩面纪律（N8 同型口径：测试桩只建在本目录内，不拉真实 service）：

- 桩成员面逐字对撞 ``api/deps.py::ActivityService`` Protocol 的四个方法（design §11.4
  冻结的端口，PRE-5 实测 4 成员非空）；
- design §6.2 冻结「428/412 由 service 侧调 ``check_if_match``」（实测 ``update_activity``
  签名已收 ``if_match`` ⇒ 路由层不调）。桩内复刻的是**该判定位置**而非路由层行为，
  于是「缺 If-Match → 428」「陈旧 ETag → 412」两条断言有触发面（PC-4 的自建判据）。
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from campaignlab.api import activities as activities_api
from campaignlab.api import deps
from campaignlab.api.app import create_app
from campaignlab.api.common import (
    Activity,
    ActivityCreate,
    ActivityPage,
    ActivityUpdate,
    Session,
    check_if_match,
    etag,
)
from campaignlab.application.activity_service import (
    ActivityCreateOutcome,
    ActivityWriteOutcome,
)
from campaignlab.config import API_PREFIX
from tests.api.conftest import GUARD, T0, TEST_ORIGIN, Harness, route_for

#: 依赖链实际解析到的对象本身（``is`` 断言的唯一取证面；每个用例开头清空）。
_RESOLVED: list[object] = []

_WORKSPACE_ID = "ws-s3-0001"
_ACTIVITY_ID = "act-s3-0001"
_ACTIVITY_NAME = "S3 端到端活动"
_IDEM_KEY = "s3-idem-key-0001"


class _StubActivityService:
    """``deps.ActivityService`` 端口面（4 成员）的同形测试桩，两个实例数据逐字相同。

    PC-1 主体变异要求「换成同类型的另一个实例」仍可构造：故桩的返回数据不含任何
    实例独有内容，字段相等判据对两个实例必然同绿，只有 ``is`` 能分辨注入对象本身。
    """

    revision = 1

    def _activity(self) -> Activity:
        return Activity(
            id=_ACTIVITY_ID,
            revision=self.revision,
            created_at=T0,
            name=_ACTIVITY_NAME,
            bank_id=None,
            external_activity_id=None,
            description="",
            status="OPEN",
            current_rule_id=None,
            bindings=[],
            rule_ids=[],
            receipt_ids=[],
        )

    def list_activities(
        self,
        *,
        actor: Session,
        workspace_id: str,
        cursor: str | None,
        limit: int,
        q: str | None,
        status: str | None,
    ) -> ActivityPage:
        _RESOLVED.append(self)
        return ActivityPage(items=[self._activity()], next_cursor=None)

    def get_activity(self, *, workspace_id: str, activity_id: str) -> Activity:
        _RESOLVED.append(self)
        return self._activity()

    def create_activity(
        self,
        *,
        workspace_id: str,
        payload: ActivityCreate,
        body: bytes,
        idempotency_key: str,
        actor: Session,
        request_id: str,
    ) -> ActivityCreateOutcome:
        _RESOLVED.append(self)
        return ActivityCreateOutcome(
            status=201,
            headers={"ETag": etag(self.revision)},
            body=self._activity().model_dump(mode="json"),
            replayed=False,
        )

    def update_activity(
        self,
        *,
        workspace_id: str,
        activity_id: str,
        payload: ActivityUpdate,
        body: bytes,
        idempotency_key: str,
        if_match: str | None,
        actor: Session,
        request_id: str,
    ) -> ActivityWriteOutcome:
        _RESOLVED.append(self)
        check_if_match(if_match, self.revision)
        return ActivityWriteOutcome(
            status=200,
            headers={"ETag": etag(self.revision)},
            body=self._activity().model_dump(mode="json"),
            replayed=False,
        )


def _app_with(harness: Harness, stub: _StubActivityService) -> FastAPI:
    return create_app(
        harness.config,
        clock=harness.clock,
        guard=GUARD,
        session_service=harness.session_service,
        activity_service=stub,
    )


def _authed_client(harness: Harness, app: FastAPI) -> TestClient:
    client = TestClient(app, headers={"Origin": TEST_ORIGIN})
    response = client.post(f"{API_PREFIX}/session/exchange", json={"token": harness.mint_token()})
    assert response.status_code == 200, response.text
    return client


def test_injected_activity_service_identity_through_real_route(harness: Harness) -> None:
    """V9 端到端：GET 一条真实路由，``deps.get_activity_service`` 解析到的对象 ``is`` 注入对象。

    同一性判据两段闭合：① 路由的真实依赖可调用对象就是 ``deps.get_activity_service``
    本身（没有被 override 悄悄替换）；② 该提供器交回处理器的对象与注入对象同一。
    """
    _RESOLVED.clear()
    injected = _StubActivityService()
    client = _authed_client(harness, _app_with(harness, injected))
    route = route_for(activities_api, "listActivities")
    provider_calls = [sub.call for sub in route.dependant.dependencies]
    assert deps.get_activity_service in provider_calls
    response = client.get(f"{API_PREFIX}/workspaces/{_WORKSPACE_ID}/activities")
    assert response.status_code == 200, response.text
    assert _RESOLVED, "路由没有走到注入的服务；依赖链断在别处"
    assert _RESOLVED[-1] is injected
    assert "ETag" not in response.headers


def test_create_activity_envelope_201_etag_and_identity(harness: Harness) -> None:
    """``createActivity`` 信封路径：201 + ``ETag``，处理对象仍是注入对象本身。"""
    _RESOLVED.clear()
    stub = _StubActivityService()
    client = _authed_client(harness, _app_with(harness, stub))
    response = client.post(
        f"{API_PREFIX}/workspaces/{_WORKSPACE_ID}/activities",
        json={"name": _ACTIVITY_NAME},
        headers={"Idempotency-Key": _IDEM_KEY},
    )
    assert response.status_code == 201, response.text
    assert response.headers["ETag"] == etag(stub.revision)
    assert _RESOLVED[-1] is stub


def test_update_activity_etag412_stale_and_missing_if_match_428(harness: Harness) -> None:
    """PC-4 的自建判据：缺 If-Match → 428，陈旧 → 412，一致 → 200 + 信封 ``ETag``。

    路由侧把 ``if_match`` 原样交给 service（判定位置在 service 侧，design §6.2）；
    若把形参改成契约字面的必填形态，缺头会在进入函数体前被判 422，本条即红。
    """
    _RESOLVED.clear()
    stub = _StubActivityService()
    client = _authed_client(harness, _app_with(harness, stub))
    url = f"{API_PREFIX}/workspaces/{_WORKSPACE_ID}/activities/{_ACTIVITY_ID}"
    headers = {"Idempotency-Key": _IDEM_KEY}
    missing = client.patch(url, json={"name": "改名一"}, headers=headers)
    assert missing.status_code == 428, missing.text
    assert missing.json()["code"] == "PRECONDITION_REQUIRED"
    stale = client.patch(url, json={"name": "改名二"}, headers={**headers, "If-Match": '"9"'})
    assert stale.status_code == 412, stale.text
    assert stale.json()["code"] == "REVISION_CONFLICT"
    fresh = client.patch(
        url, json={"name": "改名三"}, headers={**headers, "If-Match": etag(stub.revision)}
    )
    assert fresh.status_code == 200, fresh.text
    assert fresh.headers["ETag"] == etag(stub.revision)
    assert _RESOLVED[-1] is stub


def test_router_operation_surface_verbatim_design_1_1_to_1_4() -> None:
    """四个 op 的 operationId、方法与路径逐字对撞 design §1.1—§1.4（PC-2 的 pytest 侧触发面）。"""
    expected = {
        "listActivities": ("GET", "/workspaces/{workspace_id}/activities"),
        "createActivity": ("POST", "/workspaces/{workspace_id}/activities"),
        "getActivity": ("GET", "/workspaces/{workspace_id}/activities/{activity_id}"),
        "updateActivity": ("PATCH", "/workspaces/{workspace_id}/activities/{activity_id}"),
    }
    for operation_id, (method, suffix) in expected.items():
        route = route_for(activities_api, operation_id)
        assert route.methods is not None and route.methods == {method}
        assert route.path == f"{API_PREFIX}{suffix}"
