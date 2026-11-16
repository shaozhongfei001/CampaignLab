"""M2-01/S6 · 409 / 422 冲突家族（design §6.4 逐码触发面 ＋ §6.6 不可达码 ＋ AC-002/003/004）。

413／401／403 面属既有网关（M0-02 / M0-04 已钉），本文件不重复登记（N5）。同银行外部活动号
重复的「明确定位」＝ 409 ＋ **两条** ``issues``（``/bank_id`` 与 ``/external_activity_id``，
``message`` 带既有活动 ID，AC-002）；竞态兜底＝查重未命中但 INSERT 撞 UNIQUE 时同样 409、
**禁**让 ``IntegrityError`` 冒成 500（§6.4）。
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from campaignlab.application.activity_service import (
    ARCHIVED_DETAIL,
    DUPLICATE_EXTERNAL_DETAIL,
    EMPTY_PATCH_DETAIL,
    IMMUTABLE_DETAIL,
)
from campaignlab.config import API_PREFIX
from campaignlab.domain.errors import PROBLEM_CODES
from campaignlab.infra.db.repositories import ActivityRepository
from tests.api.activities.conftest import (
    REPO,
    WS_ID,
    Harness,
    create_activity_json,
    create_rule_json,
    idem_key,
    m2_routes,
    seed_evidence,
)


def _activity_url(activity_id: str) -> str:
    return f"{API_PREFIX}/workspaces/{WS_ID}/activities/{activity_id}"


def _rule_url(rule_id: str) -> str:
    return f"{API_PREFIX}/workspaces/{WS_ID}/rules/{rule_id}"


def _patch_activity(
    client: TestClient,
    activity_id: str,
    payload: dict[str, Any],
    if_match: str,
) -> Any:
    headers = {"Idempotency-Key": idem_key(), "If-Match": if_match}
    return client.patch(_activity_url(activity_id), json=payload, headers=headers)


def test_dup_external_activity_id_is_409_with_two_issues(authed_client: TestClient) -> None:
    """V4 ``-k dup_external``：两条 issues 的 location 与 message 含既有活动 ID（AC-002）。"""
    first = create_activity_json(authed_client, WS_ID)
    assert first.status_code == 201, first.text
    dup = create_activity_json(authed_client, WS_ID, name="复制品")
    assert dup.status_code == 409, dup.text
    body: dict[str, Any] = dup.json()
    assert body["code"] == "STATE_CONFLICT"
    assert body["detail"] == DUPLICATE_EXTERNAL_DETAIL
    issues = body["issues"]
    assert [issue["location"] for issue in issues] == ["/bank_id", "/external_activity_id"]
    assert {issue["code"] for issue in issues} == {"DUPLICATE_EXTERNAL_ACTIVITY"}
    assert str(first.json()["id"]) in issues[1]["message"]


def test_dup_external_race_falls_back_to_409_not_500(
    authed_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """竞态兜底：预检查被「蒙住眼」（首次返回 None），INSERT 撞 UNIQUE 后仍须 409 而非 500。"""
    first = create_activity_json(authed_client, WS_ID)
    assert first.status_code == 201, first.text
    original = ActivityRepository.find_by_external
    state = {"calls": 0}

    def blind_first(
        self: ActivityRepository,
        conn: Any,
        *,
        workspace_id: str,
        bank_id: str,
        external_activity_id: str,
    ) -> Any:
        state["calls"] += 1
        if state["calls"] == 1:
            return None
        return original(
            self,
            conn,
            workspace_id=workspace_id,
            bank_id=bank_id,
            external_activity_id=external_activity_id,
        )

    monkeypatch.setattr(ActivityRepository, "find_by_external", blind_first)
    dup = create_activity_json(authed_client, WS_ID, name="竞态复制品")
    assert state["calls"] >= 2, "竞态路径没有走到 INSERT 兜底的复查"
    assert dup.status_code == 409, dup.text
    body: dict[str, Any] = dup.json()
    assert body["code"] == "STATE_CONFLICT"
    assert len(body["issues"]) == 2
    assert str(first.json()["id"]) in body["issues"][1]["message"]


def test_null_bank_id_never_triggers_dup_external(authed_client: TestClient) -> None:
    "SQLite NULL 语义：UNIQUE 里 NULL 互不相等 ⇒ 任一为 null 永不触发冲突（§6.4）。`n"
    a = create_activity_json(
        authed_client, WS_ID, name="无银行一", bank_id=None, external_activity_id="AC-900"
    )
    b = create_activity_json(
        authed_client, WS_ID, name="无银行二", bank_id=None, external_activity_id="AC-900"
    )
    c = create_activity_json(
        authed_client, WS_ID, name="无外部号", bank_id="B-9", external_activity_id=None
    )
    assert [a.status_code, b.status_code, c.status_code] == [201, 201, 201]


def test_idempotency_conflict_is_409(authed_client: TestClient) -> None:
    key = idem_key()
    first = create_activity_json(authed_client, WS_ID, name="首体", key=key)
    second = create_activity_json(authed_client, WS_ID, name="异体", key=key)
    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text
    body: dict[str, Any] = second.json()
    assert body["code"] == "IDEMPOTENCY_CONFLICT"
    assert body["issues"] == []


def test_empty_patch_is_422(authed_client: TestClient) -> None:
    """``ActivityUpdate.required`` 实测空数组 ⇒ 空 PATCH 由 service 判 422（§6.4）。"""
    created = create_activity_json(authed_client, WS_ID)
    activity_id = str(created.json()["id"])
    response = authed_client.patch(
        _activity_url(activity_id),
        content=b"{}",
        headers={
            "Idempotency-Key": idem_key(),
            "If-Match": '"1"',
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 422, response.text
    body: dict[str, Any] = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["detail"] == EMPTY_PATCH_DETAIL
    assert body["issues"][0]["code"] == "EMPTY_PATCH"
    assert body["issues"][0]["location"] == "/"


def test_archived_activity_rejects_update_409(authed_client: TestClient) -> None:
    created = create_activity_json(authed_client, WS_ID)
    activity_id = str(created.json()["id"])
    archived = _patch_activity(authed_client, activity_id, {"status": "ARCHIVED"}, '"1"')
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "ARCHIVED"
    rejected = _patch_activity(authed_client, activity_id, {"name": "归档后改名"}, '"2"')
    assert rejected.status_code == 409, rejected.text
    body: dict[str, Any] = rejected.json()
    assert body["code"] == "STATE_CONFLICT"
    assert body["detail"] == ARCHIVED_DETAIL
    assert body["issues"][0]["code"] == "ACTIVITY_ARCHIVED"


def test_confirmed_rule_rejects_update_409_and_writes_denied_audit(
    authed_client: TestClient, harness: Harness
) -> None:
    """AC-003「试编辑」：409 ``RULE_CONFIRMED_IMMUTABLE`` ＋ 一行 ``DENIED`` 审计留痕。"""
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    created = create_activity_json(authed_client, WS_ID)
    activity_id = str(created.json()["id"])
    rule = create_rule_json(authed_client, WS_ID, activity_id)
    rule_id = str(rule.json()["id"])
    digest = str(authed_client.get(_rule_url(rule_id)).json()["digest"])
    confirmed = authed_client.post(
        f"{_rule_url(rule_id)}/confirm",
        json={"note": "已复核", "digest": digest},
        headers={"Idempotency-Key": idem_key(), "If-Match": '"1"'},
    )
    assert confirmed.status_code == 200, confirmed.text
    denied = authed_client.patch(
        _rule_url(rule_id),
        json={"label": "确认后再改"},
        headers={"Idempotency-Key": idem_key(), "If-Match": '"2"'},
    )
    assert denied.status_code == 409, denied.text
    body: dict[str, Any] = denied.json()
    assert body["code"] == "STATE_CONFLICT"
    assert body["detail"] == IMMUTABLE_DETAIL
    assert body["issues"][0]["code"] == "RULE_CONFIRMED_IMMUTABLE"
    frozen = authed_client.get(_rule_url(rule_id)).json()
    assert frozen["label"] == "v1" and frozen["revision"] == 2
    assert ("RULE_LABEL_UPDATED", "rule", "DENIED") in harness.audit_rows(outcome="DENIED")


def test_confirm_with_stale_digest_is_409_version_mismatch(
    authed_client: TestClient, harness: Harness
) -> None:
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    created = create_activity_json(authed_client, WS_ID)
    activity_id = str(created.json()["id"])
    rule = create_rule_json(authed_client, WS_ID, activity_id)
    rule_id = str(rule.json()["id"])
    drifted = authed_client.post(
        f"{_rule_url(rule_id)}/confirm",
        json={"note": "过期摘要", "digest": "b" * 64},
        headers={"Idempotency-Key": idem_key(), "If-Match": '"1"'},
    )
    assert drifted.status_code == 409, drifted.text
    body: dict[str, Any] = drifted.json()
    assert body["code"] == "VERSION_MISMATCH"
    assert body["issues"][0]["code"] == "CONFIRMATION_DIGEST_MISMATCH"
    assert body["issues"][0]["location"] == "/digest"
    assert authed_client.get(_rule_url(rule_id)).json()["state"] == "DRAFT"


def test_confirm_without_required_clause_is_422_evidence_required(
    authed_client: TestClient, harness: Harness
) -> None:
    """AC-004 HTTP 面：必需条款缺失 → 422 ``EVIDENCE_REQUIRED`` 逐键定位；补全后可确认。

    被拒的确认**不登记**幂等（§7.5 末条：只登记 2xx）⇒ 同键可在补全条款后重试成功。
    """
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    created = create_activity_json(authed_client, WS_ID)
    activity_id = str(created.json()["id"])
    rule = create_rule_json(authed_client, WS_ID, activity_id, terms=[])
    rule_id = str(rule.json()["id"])
    digest = str(authed_client.get(_rule_url(rule_id)).json()["digest"])
    key = idem_key()
    rejected = authed_client.post(
        f"{_rule_url(rule_id)}/confirm",
        json={"note": "先试试", "digest": digest},
        headers={"Idempotency-Key": key, "If-Match": '"1"'},
    )
    assert rejected.status_code == 422, rejected.text
    body: dict[str, Any] = rejected.json()
    assert body["code"] == "EVIDENCE_REQUIRED"
    locations = {issue["location"] for issue in body["issues"]}
    assert locations == {
        f"/terms/{term_key}"
        for term_key in (
            "new_customer",
            "payment",
            "time_window",
            "stacking",
            "budget_and_quota",
            "refund",
        )
    }
    assert authed_client.get(_rule_url(rule_id)).json()["state"] == "DRAFT"
    patched = authed_client.patch(
        _rule_url(rule_id),
        json={"terms": _full_terms()},
        headers={"Idempotency-Key": idem_key(), "If-Match": '"1"'},
    )
    assert patched.status_code == 200, patched.text
    fresh_digest = str(authed_client.get(_rule_url(rule_id)).json()["digest"])
    accepted = authed_client.post(
        f"{_rule_url(rule_id)}/confirm",
        json={"note": "补齐后重试", "digest": fresh_digest},
        headers={"Idempotency-Key": key, "If-Match": '"2"'},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["state"] == "CONFIRMED"


def _full_terms() -> list[dict[str, Any]]:
    return [
        {
            "key": term_key,
            "clause": "条款原文",
            "decision": "同意",
            "status": "CONFIRMED",
            "evidence_id": "ev-1",
        }
        for term_key in (
            "new_customer",
            "payment",
            "time_window",
            "stacking",
            "budget_and_quota",
            "refund",
        )
    ]


def test_unreachable_codes_are_declared_but_unreachable() -> None:
    """§6.6 五个码：仍在各 op 声明的 Problem 形里，但在 M2-01 生产面**零发射**（禁 skip/xfail）。"""
    unreachable = (
        "STALE_CANDIDATE",
        "SNAPSHOT_CONFLICT",
        "ACTION_REVIEW_REQUIRED",
        "JOB_CAPACITY",
        "INVALID_SCOPE",
    )
    routes = m2_routes()
    assert routes, "分母哨兵：M2-01 路由枚举不得为空"
    for code in unreachable:
        assert code in PROBLEM_CODES, code
    for operation_id, route in sorted(routes.items()):
        declared = {str(status) for status in route.responses}
        for code in unreachable:
            assert str(PROBLEM_CODES[code][0]) in declared, (operation_id, code)
    production_files = (
        "src/campaignlab/api/activities.py",
        "src/campaignlab/api/rules.py",
        "src/campaignlab/application/activity_service.py",
    )
    for relative in production_files:
        text = (REPO / relative).read_text(encoding="utf-8")
        assert text, relative
        for code in unreachable:
            assert code not in text, (relative, code)
