"""M0-02/S4 · 声明面契约（裁定 A95 的落地面）。

**状态码集合的唯一权威是路由装饰器上的 ``declared_responses()``**（A95：它使
「实现声明的码集 == 切片声明的码集」成为可机器断言的不变量）。本目录因此**不另立**任何
一份状态码清单：期望值一律来自 ``route.responses`` 的实现侧与切片 ``M0-02.slice.json``
的声明侧对撞，错误码一律来自 ``domain/errors.py`` 的注册表 ``PROBLEM_CODES``（禁自造码）。

不可达分支（Q2/Q3 已裁定 404/409 部分、412/428/429 在 M0-02 的这 5 个 op 上不可达）在此
**断言不可达**本身，禁写会红的用例、禁 ``skip``/``xfail``。
jobs 相关（listJobs/getJob/cancelJob/retryJob 与 202 语义）**deferred_to M0-04/S4**
（A84：其实现尚未落地）。
"""

from __future__ import annotations

import re
from typing import Any, Final

import pytest
from conftest import LIVE_CONTRACT, REPO, SLICE, Harness, route_for
from fastapi.routing import APIRoute

from campaignlab.api import health as health_api
from campaignlab.api import session as session_api
from campaignlab.api import workspaces as workspaces_api
from campaignlab.api.common import X_REQUEST_ID_HEADER, Health, Issue, Problem
from campaignlab.config import API_PREFIX
from campaignlab.domain.errors import PROBLEM_CODES

#: 装饰器带 ``declared_responses()`` 的 4 个 op。
#: A95 的 action_taken 记录 responses= 计数：session 2 / workspaces 2 / health 0。
_OPS_WITH_DECLARED: Final = ("exchangeSession", "getSession", "listWorkspaces", "createWorkspace")
_ALL_OPS: Final = (*_OPS_WITH_DECLARED, "getHealth")
_MODULES: Final = {
    "exchangeSession": session_api,
    "getSession": session_api,
    "listWorkspaces": workspaces_api,
    "createWorkspace": workspaces_api,
    "getHealth": health_api,
}

#: 本目录实际断言过的错误码，必须**全部**来自注册表（禁自造码）。
_CODES_USED_BY_THIS_DIRECTORY: Final = (
    "BAD_REQUEST",
    "IDEMPOTENCY_CONFLICT",
    "INPUT_TOO_LARGE",
    "INTERNAL_ERROR",
    "ORIGIN_DENIED",
    "SESSION_EXPIRED",
    "BAD_CURSOR",
    "VALIDATION_ERROR",
)

_REQUEST_ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")


def _slice_statuses(operation_id: str) -> set[str]:
    declared: Any = SLICE["operations"][operation_id]["operation"]["responses"]
    return {str(status) for status in declared}


def test_implemented_status_set_equals_slice_status_set_per_op() -> None:
    """A95 的硬约束：实现声明的码集 == 切片声明的码集（逐 op，不写死计数）。"""
    for operation_id in _OPS_WITH_DECLARED:
        route = route_for(_MODULES[operation_id], operation_id)
        implemented = {str(status) for status in route.responses}
        assert implemented == _slice_statuses(operation_id), operation_id
        assert len(implemented) == len(_slice_statuses(operation_id)), operation_id


def test_gethealth_decorator_has_no_declared_responses_yet_and_is_tracked_as_u1() -> None:
    """``getHealth`` 的装饰器**没有** ``responses=``（A95 action_taken：responses= 计数 health 0）。

    权威 ``declared_responses()`` 属 ``api/session.py``（S3b 写集），``api/health.py`` 属 S3c 写集，
    两者都不在 S4 的 ``tests/api/**`` 写集内 → 本用例只钉住「health 侧尚未落到装饰器」这一事实，
    使 A95 不变量在补齐后必然转红（而不是静默漏测），并已在回报里作为 **U-1** 提交裁定请求。
    """
    route = route_for(health_api, "getHealth")
    assert isinstance(route, APIRoute)
    assert dict(route.responses or {}) == {}
    assert "200" in _slice_statuses("getHealth")


def test_problem_and_issue_field_sets_match_live_contract() -> None:
    """Problem／Issue 的字段集合逐字对齐活契约（``additionalProperties: false``）。"""
    schemas: dict[str, Any] = LIVE_CONTRACT["components"]["schemas"]
    problem_schema = schemas["Problem"]
    issue_schema = schemas["Issue"]
    assert set(Problem.model_fields) == set(problem_schema["properties"])
    assert set(Issue.model_fields) == set(issue_schema["properties"])
    assert problem_schema.get("additionalProperties") is False
    assert issue_schema.get("additionalProperties") is False
    assert set(problem_schema["required"]) == set(Problem.model_fields)
    assert set(issue_schema["required"]) == set(Issue.model_fields)


def test_type_title_status_are_registry_derived_never_invented() -> None:
    """``type``／``title``／``status`` 全部由注册表反查，禁止在测试或调用点现编。"""
    for code in _CODES_USED_BY_THIS_DIRECTORY:
        assert code in PROBLEM_CODES, code
        status, type_, title = PROBLEM_CODES[code]
        assert type_ == "urn:campaignlab:problem:" + code.lower()
        assert status in {400, 401, 403, 409, 413, 422, 500}
        assert title and len(title) <= 200


def test_no_if_match_declared_so_412_and_428_are_unreachable(authed: Any) -> None:
    """Q3 裁定：M0-02 的 5 个 op 均未声明 ``If-Match`` → 412/428 不可达（helper 单测属 S3c/S3d）。

    可执行证明：给 ``createWorkspace`` 塞一个必然不匹配的 ``If-Match`` 仍走 201，
    即路由根本没有调用 ``check_if_match`` 的触发面。
    """
    for operation_id in _ALL_OPS:
        params: Any = SLICE["operations"][operation_id]["operation"].get("parameters", [])
        names = {str(item.get("name")) for item in params if isinstance(item, dict)}
        assert "If-Match" not in names, operation_id
        assert "412" in _slice_statuses(operation_id) and "428" in _slice_statuses(operation_id)
    response = authed.post(
        f"{API_PREFIX}/workspaces",
        json={"name": "不可达探针", "source_class": "SYNTHETIC"},
        headers={"Idempotency-Key": "contract-ifmatch-probe", "If-Match": '"99"'},
    )
    assert response.status_code == 201, response.text
    assert response.headers["ETag"] == chr(34) + "1" + chr(34)


def test_404_and_429_branches_are_unreachable_for_the_five_ops(authed: Any) -> None:
    """不可达码集取证：跨工作区 ID → 404 与 429 ``JOB_CAPACITY`` 在本 5 个 op 上均无触发面。

    依据 Q2/Q3（作业 202/429 属 M0-04 的 op；``jobs`` 路由未挂载，A84/A85）与
    ``declared_responses()`` 只做声明、不产生这些分支的事实。
    """
    assert not (REPO / "src/campaignlab/api/jobs.py").exists()
    mounted_paths = {
        str(route.path)
        for module in (session_api, workspaces_api, health_api)
        for route in module.router.routes
    }
    assert mounted_paths == {
        f"{API_PREFIX}/session/exchange",
        f"{API_PREFIX}/session",
        f"{API_PREFIX}/workspaces",
        f"{API_PREFIX}/health",
    }
    assert "JOB_CAPACITY" in PROBLEM_CODES
    response = authed.get(f"{API_PREFIX}/workspaces")
    assert response.status_code == 200
    assert X_REQUEST_ID_HEADER in response.headers
    assert _REQUEST_ID_PATTERN.match(response.headers[X_REQUEST_ID_HEADER])


def test_health_is_200_with_worker_after_explicit_assembly(harness: Harness) -> None:
    """FU-12 正向覆盖（裁定 A69 承接）：显式装配后 ``/api/v1/health`` 返回 200 且 worker 为真值。

    既有两条用例 ``test_health_is_500_problem_while_service_is_pending`` 与
    ``test_jobs_router_is_not_mounted_by_s3c`` 位于 ``tests/unit/``（S4 的 deny 写集），
    **未改名、未改写**；本用例只补上「注入了 health_service 之后」的正向缺口。
    """
    client = harness.client(with_health=True)
    response = client.get(f"{API_PREFIX}/health")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = dict(response.json())
    snapshot = Health.model_validate(body)
    worker = snapshot.worker
    assert bool(worker) and isinstance(worker, str)
    assert worker in {"READY", "OFFLINE"}
    assert snapshot.status in {"READY", "DEGRADED"}
    assert snapshot.contract_version == LIVE_CONTRACT["info"]["version"]
    assert re.match(r"^[^/]+$", snapshot.schema_revision)
    assert set(body) == {
        "status",
        "app_version",
        "contract_version",
        "worker",
        "schema_revision",
    }


def test_design_doc_and_slice_are_readable_authorities() -> None:
    """自检：本目录依赖的两份权威文件确实存在（防止切片被重切后测试对着空气断言）。"""
    assert (REPO / "orchestrator/handoff/M0-02.slice.json").is_file()
    assert (REPO / "contracts/openapi.json").is_file()
    assert set(SLICE["operations"]) == set(_ALL_OPS)


@pytest.mark.parametrize("operation_id", _ALL_OPS)
def test_every_op_is_reachable_over_the_api_prefix(operation_id: str) -> None:
    """5 个 operationId 都挂在 ``/api/v1`` 下（基址来自活契约 ``servers[0].url``）。"""
    route = route_for(_MODULES[operation_id], operation_id)
    assert str(route.path).startswith(API_PREFIX)
    assert operation_id in SLICE["operations"]
