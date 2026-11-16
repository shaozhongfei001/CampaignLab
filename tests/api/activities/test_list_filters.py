"""M2-01/S6 · 列表过滤与游标（design §1.1 / §1.5 / §6.1；V10 ``-k list_filter``）。

前 5 条函数名含 ``list_filter``；``test_list_rules_status_param_filters_the_state_column``
钉 §1.5 的命名陷阱（参数名 ``status``、被过滤列 ``rule_versions.state``，逐字照契约不改名）；
``test_list_pages_have_no_etag_header`` 钉 §6.1「列表与只读计算面无 ETag」；末条钉跨工作区
404 与「不存在」逐字同 detail（禁枚举 oracle）。
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from campaignlab.application.workspace_service import BAD_CURSOR_DETAIL
from campaignlab.config import API_PREFIX
from tests.api.activities.conftest import (
    STRANGER,
    WS_ID,
    WS_OTHER,
    Harness,
    create_activity_json,
    create_rule_json,
    idem_key,
    seed_activity,
    seed_evidence,
)


def _activities_url(workspace_id: str = WS_ID) -> str:
    return f"{API_PREFIX}/workspaces/{workspace_id}/activities"


def _activity_url(activity_id: str, workspace_id: str = WS_ID) -> str:
    return f"{_activities_url(workspace_id)}/{activity_id}"


def _rules_url(activity_id: str, workspace_id: str = WS_ID) -> str:
    return f"{_activity_url(activity_id, workspace_id)}/rules"


def _create(client: TestClient, index: int, *, name: str | None = None) -> str:
    created = create_activity_json(
        client,
        WS_ID,
        name=name if name is not None else f"活动 {index}",
        bank_id=None,
        external_activity_id=f"AC-{index}",
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def test_list_filter_by_status_multi_value(authed_client: TestClient) -> None:
    """``status`` 逗号多值（N7① 已裁口径）：单值、另一单值、双值命中数 1/1/2（§1.1）。"""
    first = _create(authed_client, 1)
    _create(authed_client, 2)
    archived = authed_client.patch(
        _activity_url(first),
        json={"status": "ARCHIVED"},
        headers={"Idempotency-Key": idem_key(), "If-Match": '"1"'},
    )
    assert archived.status_code == 200, archived.text
    only_archived = authed_client.get(_activities_url(), params={"status": "ARCHIVED"})
    only_open = authed_client.get(_activities_url(), params={"status": "OPEN"})
    both = authed_client.get(_activities_url(), params={"status": "OPEN,ARCHIVED"})
    assert [len(r.json()["items"]) for r in (only_archived, only_open, both)] == [1, 1, 2]
    assert only_archived.json()["items"][0]["id"] == first


def test_list_filter_by_q_matches_name_and_external_id(authed_client: TestClient) -> None:
    """``q`` 对 ``name`` 与 ``external_activity_id`` 做 NFKC＋casefold 子串匹配（§1.1）。"""
    named = _create(authed_client, 1, name="双十一大促")
    _create(authed_client, 2)
    by_name = authed_client.get(_activities_url(), params={"q": "大促"})
    by_external_folded = authed_client.get(_activities_url(), params={"q": "ac-2"})
    by_external_exact = authed_client.get(_activities_url(), params={"q": "AC-2"})
    hits = [by_name.json()["items"], by_external_folded.json()["items"]]
    assert [item["id"] for item in hits[0]] == [named]
    assert [item["external_activity_id"] for item in hits[1]] == ["AC-2"]
    assert by_external_folded.json() == by_external_exact.json()


def test_list_filter_unknown_status_is_422(authed_client: TestClient) -> None:
    """未知态名与空 token 一律 422，``issues[0].location`` 固定 ``/query/status``（§1.1）。"""
    for bad in ("NOPE", "OPEN,", "open ,"):
        response = authed_client.get(_activities_url(), params={"status": bad})
        assert response.status_code == 422, (bad, response.text)
        body: dict[str, Any] = response.json()
        assert body["code"] == "VALIDATION_ERROR", bad
        assert body["issues"][0]["location"] == "/query/status", bad
        assert body["issues"][0]["code"] == "STATUS_UNKNOWN", bad


def test_list_filter_cursor_binds_all_four_params(
    authed_client: TestClient, harness: Harness
) -> None:
    """游标 digest 绑 ``workspace_id/limit/q/status`` 且 ``s`` 绑 actor：四种错配同判 400。"""
    for index in (1, 2, 3):
        _create(authed_client, index)
    page = authed_client.get(_activities_url(), params={"limit": 2})
    assert page.status_code == 200, page.text
    cursor = str(page.json()["next_cursor"])
    assert cursor and cursor != "None"
    stranger = harness.s6_client(STRANGER)
    mismatches = (
        authed_client.get(_activities_url(), params={"limit": 1, "cursor": cursor}),
        authed_client.get(_activities_url(), params={"limit": 2, "q": "活动", "cursor": cursor}),
        authed_client.get(
            _activities_url(), params={"limit": 2, "status": "OPEN", "cursor": cursor}
        ),
        stranger.get(_activities_url(), params={"limit": 2, "cursor": cursor}),
    )
    for response in mismatches:
        assert response.status_code == 400, response.text
        assert response.json()["code"] == "BAD_CURSOR"
        assert response.json()["detail"] == BAD_CURSOR_DETAIL


def test_list_filter_bad_cursor_is_400_with_the_frozen_detail(authed_client: TestClient) -> None:
    """解不开／HMAC 不符的游标 → 400 ``BAD_CURSOR``，detail 与 workspace 侧同一句（禁另编）。"""
    response = authed_client.get(_activities_url(), params={"cursor": "garbage"})
    assert response.status_code == 400, response.text
    body: dict[str, Any] = response.json()
    assert body["code"] == "BAD_CURSOR"
    assert body["detail"] == BAD_CURSOR_DETAIL


def test_list_rules_status_param_filters_the_state_column(
    authed_client: TestClient, harness: Harness
) -> None:
    """§1.5 命名陷阱：参数名 ``status`` 过滤的是 ``rule_versions.state`` 列（§1.5）。
    白名单 DRAFT/CONFIRMED，逐字照契约实现，不做改名。
    """
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    activity = _create(authed_client, 7, name="规则过滤样本")
    draft = create_rule_json(authed_client, WS_ID, activity, label="d-1")
    confirmed = create_rule_json(authed_client, WS_ID, activity, label="c-1")
    confirmed_id = str(confirmed.json()["id"])
    digest = str(
        authed_client.get(f"{API_PREFIX}/workspaces/{WS_ID}/rules/{confirmed_id}").json()["digest"]
    )
    response = authed_client.post(
        f"{API_PREFIX}/workspaces/{WS_ID}/rules/{confirmed_id}/confirm",
        json={"note": "确认其一", "digest": digest},
        headers={"Idempotency-Key": idem_key(), "If-Match": '"1"'},
    )
    assert response.status_code == 200, response.text
    drafts = authed_client.get(_rules_url(activity), params={"status": "DRAFT"})
    confirmeds = authed_client.get(_rules_url(activity), params={"status": "CONFIRMED"})
    assert [item["id"] for item in drafts.json()["items"]] == [str(draft.json()["id"])]
    assert [item["id"] for item in confirmeds.json()["items"]] == [confirmed_id]
    assert all(item["state"] == "DRAFT" for item in drafts.json()["items"])
    assert all(item["state"] == "CONFIRMED" for item in confirmeds.json()["items"])


def test_list_pages_have_no_etag_header(authed_client: TestClient) -> None:
    """§6.1：``listActivities`` / ``listRules`` / ``checkRule`` / ``compareRules`` 无 ``ETag``。"""
    activity = _create(authed_client, 8)
    first = create_rule_json(authed_client, WS_ID, activity, label="r-a")
    second = create_rule_json(authed_client, WS_ID, activity, label="r-b")
    first_id = str(first.json()["id"])
    second_id = str(second.json()["id"])
    pages = (
        authed_client.get(_activities_url()),
        authed_client.get(_rules_url(activity)),
        authed_client.get(f"{API_PREFIX}/workspaces/{WS_ID}/rules/{first_id}/checks"),
        authed_client.get(
            f"{API_PREFIX}/workspaces/{WS_ID}/rules/{first_id}/diff",
            params={"candidate_rule_id": second_id},
        ),
    )
    for response in pages:
        assert response.status_code == 200, response.text
        assert "ETag" not in response.headers
    single = authed_client.get(_activity_url(activity))
    assert single.status_code == 200 and "ETag" in single.headers


def test_cross_workspace_is_404(authed_client: TestClient, harness: Harness) -> None:
    """他区活动在本区不可见：404 与不存在逐字同 detail（§1.3 禁枚举口径）。"""
    seed_activity(harness.engine, WS_OTHER, "act-s6-foreign", name="客场活动")
    foreign = authed_client.get(_activity_url("act-s6-foreign", WS_ID))
    ghost = authed_client.get(_activity_url("act-s6-ghost", WS_ID))
    assert foreign.status_code == 404 and ghost.status_code == 404
    assert foreign.json()["code"] == "RESOURCE_NOT_FOUND"
    fields = ("type", "title", "status", "code", "detail")
    assert {key: foreign.json()[key] for key in fields} == {
        key: ghost.json()[key] for key in fields
    }
    visible = authed_client.get(_activity_url("act-s6-foreign", WS_OTHER))
    assert visible.status_code == 200, visible.text
