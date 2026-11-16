"""M2-01/S6 · ``compareRules`` 差异面（design §6.5；AC-003「差异字段、条款来源和摘要」）。

``RuleDiff.changes[].path`` 只准是 §6.5 冻结四类（``/label``、``/content/<字段>``、
``/source_rule_version``、``/terms/<key>/...``）；409 响应体**不存在** ``diff`` 字段
（A201／§6.5 口径，差异只在 200 ``RuleDiff``）。跨模板 → 422 ``TEMPLATE_MISMATCH``，
跨工作区 → 404 同一句 detail（禁枚举 oracle）。
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from campaignlab.config import API_PREFIX
from tests.api.activities.conftest import (
    CALLBACK_JSON,
    COUPON_JSON,
    WS_ID,
    WS_OTHER,
    Harness,
    create_activity_json,
    create_rule_json,
    idem_key,
    seed_evidence,
)

_ALLOWED_PATH_PREFIXES: tuple[str, ...] = (
    "/content/",
    "/terms/",
    "/label",
    "/source_rule_version",
)


def _activity(client: TestClient, workspace_id: str = WS_ID, **kwargs: Any) -> str:
    created = create_activity_json(client, workspace_id, **kwargs)
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def _rule(client: TestClient, activity_id: str, **kwargs: Any) -> str:
    created = create_rule_json(client, WS_ID, activity_id, **kwargs)
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def _digest(client: TestClient, rule_id: str) -> str:
    response = client.get(f"{API_PREFIX}/workspaces/{WS_ID}/rules/{rule_id}")
    assert response.status_code == 200, response.text
    return str(response.json()["digest"])


def _diff(client: TestClient, baseline: str, candidate: str) -> Any:
    return client.get(
        f"{API_PREFIX}/workspaces/{WS_ID}/rules/{baseline}/diff",
        params={"candidate_rule_id": candidate},
    )


def test_rule_diff_shows_changed_fields_sources_and_digest(
    authed_client: TestClient, harness: Harness
) -> None:
    """V5 ``-k rule_diff``：AC-003 三件（差异字段／条款来源／摘要）在同一条用例里一起断言。"""
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    activity_id = _activity(authed_client)
    baseline = _rule(authed_client, activity_id, label="CP-V1")
    candidate = _rule(
        authed_client,
        activity_id,
        label="CP-V2",
        content={**COUPON_JSON, "refund_policy": "KEEP"},
    )
    response = _diff(authed_client, baseline, candidate)
    assert response.status_code == 200, response.text
    assert "ETag" not in response.headers
    body: dict[str, Any] = response.json()
    assert body["baseline_rule_id"] == baseline and body["candidate_rule_id"] == candidate
    changes = body["changes"]
    paths = [str(change["path"]) for change in changes]
    assert "/content/refund_policy" in paths
    for path in paths:
        assert path.startswith(_ALLOWED_PATH_PREFIXES), path
    entry = changes[paths.index("/content/refund_policy")]
    assert entry["before"] == "RECOMPUTE_UNUSED" and entry["after"] == "KEEP"
    assert isinstance(entry["before"], str) and isinstance(entry["after"], str)
    # 条款来源：``getRule`` 的 ``terms[]`` 原样携带 ``clause`` 与 ``evidence_id``（RULES.md）
    terms: list[dict[str, Any]] = authed_client.get(
        f"{API_PREFIX}/workspaces/{WS_ID}/rules/{baseline}"
    ).json()["terms"]
    assert terms and all(term["clause"] and term["evidence_id"] == "ev-1" for term in terms)
    # 摘要：两版 digest 各自 64 位小写 hex 且随内容变化
    digest_a = _digest(authed_client, baseline)
    digest_b = _digest(authed_client, candidate)
    assert len(digest_a) == 64 and len(digest_b) == 64 and digest_a != digest_b


def test_rule_diff_cross_template_is_422(authed_client: TestClient) -> None:
    activity_id = _activity(authed_client)
    baseline = _rule(authed_client, activity_id)
    candidate = _rule(authed_client, activity_id, label="cb-v1", content=dict(CALLBACK_JSON))
    response = _diff(authed_client, baseline, candidate)
    assert response.status_code == 422, response.text
    body: dict[str, Any] = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["issues"][0]["code"] == "TEMPLATE_MISMATCH"
    assert body["issues"][0]["location"] == "/query/candidate_rule_id"


def test_rule_diff_requires_rerun_case_ids_is_empty_when_no_change(
    authed_client: TestClient, harness: Harness
) -> None:
    """投影逐字相同 ⇒ ``changes == []`` 且 ``requires_rerun_case_ids == []``（§6.5 末段）。"""
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    activity_id = _activity(authed_client)
    baseline = _rule(authed_client, activity_id, label="同文一")
    confirmed = authed_client.post(
        f"{API_PREFIX}/workspaces/{WS_ID}/rules/{baseline}/confirm",
        json={"note": "为派生草稿先确认", "digest": _digest(authed_client, baseline)},
        headers={"Idempotency-Key": idem_key(), "If-Match": '"1"'},
    )
    assert confirmed.status_code == 200, confirmed.text
    clone = _rule(authed_client, activity_id, label="同文一", parent_rule_id=baseline)
    response = _diff(authed_client, baseline, clone)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    assert body["changes"] == []
    assert body["requires_rerun_case_ids"] == []


def test_rule_diff_across_workspaces_is_404(authed_client: TestClient, harness: Harness) -> None:
    """候选属外工作区 → 404 与「不存在」逐字同 detail（禁枚举 oracle，§1.11／§6.4）。"""
    activity_id = _activity(authed_client)
    baseline = _rule(authed_client, activity_id)
    other_activity = _activity(authed_client, WS_OTHER, name="客场活动", bank_id=None)
    foreign = create_rule_json(authed_client, WS_OTHER, other_activity, label="客场规则")
    assert foreign.status_code == 201, foreign.text
    cross = _diff(authed_client, baseline, str(foreign.json()["id"]))
    ghost = _diff(authed_client, baseline, "rul-ghost-does-not-exist")
    assert cross.status_code == 404, cross.text
    assert ghost.status_code == 404, ghost.text
    assert cross.json()["code"] == "RESOURCE_NOT_FOUND"
    assert cross.json()["detail"] == ghost.json()["detail"]
