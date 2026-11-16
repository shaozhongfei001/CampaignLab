"""M2-01/S6 · 绑定 HTTP 面（design §3.4 区间代数；V8 ``-k binding`` 五例函数名一律含 ``binding``）。

三条冻结口径逐一定位：① ``bindings`` 出现即**整体替换**、未出现**完全不动**
（AC-002「AC-202 保持无绑定」）；② 空区间／相交／重复键一律 422，**禁**让 DDL 的
``IntegrityError`` 冒成 500；③ ``evidence_id`` 未登记 → 422 ``EVIDENCE_REQUIRED``
（业务性拒绝，另追加 ``DENIED`` 审计行，§7.3）。
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from campaignlab.config import API_PREFIX
from tests.api.activities.conftest import (
    WS_ID,
    Harness,
    binding_json,
    create_activity_json,
    idem_key,
    seed_evidence,
)


def _activity_url(activity_id: str) -> str:
    return f"{API_PREFIX}/workspaces/{WS_ID}/activities/{activity_id}"


def _new_activity(client: TestClient) -> str:
    created = create_activity_json(client, WS_ID)
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def _patch_bindings(
    client: TestClient, activity_id: str, bindings: list[dict[str, Any]] | None, if_match: str
) -> Any:
    payload: dict[str, Any] = {"bindings": bindings} if bindings is not None else {"name": "只改名"}
    return client.patch(
        _activity_url(activity_id),
        json=payload,
        headers={"Idempotency-Key": idem_key(), "If-Match": if_match},
    )


def _get(client: TestClient, activity_id: str) -> dict[str, Any]:
    response = client.get(_activity_url(activity_id))
    assert response.status_code == 200, response.text
    return dict(response.json())


def test_binding_full_replacement_semantics(authed_client: TestClient, harness: Harness) -> None:
    """出现即整体替换：给两条剩两条、再给一条只剩一条，不是 merge（§3.4）。"""
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    activity_id = _new_activity(authed_client)
    two = _patch_bindings(
        authed_client,
        activity_id,
        [
            binding_json("S-1", "2026-01-01", "2026-02-01"),
            binding_json("S-2", "2026-03-01", "2026-04-01"),
        ],
        '"1"',
    )
    assert two.status_code == 200, two.text
    assert [item["strategy_id"] for item in two.json()["bindings"]] == ["S-1", "S-2"]
    one = _patch_bindings(
        authed_client, activity_id, [binding_json("S-9", "2026-05-01", "2026-06-01")], '"2"'
    )
    assert one.status_code == 200, one.text
    assert [item["strategy_id"] for item in one.json()["bindings"]] == ["S-9"]
    assert one.json()["revision"] == 3
    assert [item["strategy_id"] for item in _get(authed_client, activity_id)["bindings"]] == ["S-9"]


def test_binding_absent_from_patch_leaves_rows_untouched(
    authed_client: TestClient, harness: Harness
) -> None:
    """``bindings`` 未出现在 PATCH ⇒ 完全不动；从未给过 ⇒ 保持 ``[]``（AC-002「AC-202」）。"""
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    busy = _new_activity(authed_client)
    written = _patch_bindings(
        authed_client, busy, [binding_json("S-1", "2026-01-01", "2026-02-01")], '"1"'
    )
    assert written.status_code == 200, written.text
    renamed = _patch_bindings(authed_client, busy, None, '"2"')
    assert renamed.status_code == 200, renamed.text
    assert [item["strategy_id"] for item in renamed.json()["bindings"]] == ["S-1"]
    virgin_resp = create_activity_json(
        authed_client, WS_ID, name="618", bank_id=None, external_activity_id="AC-202"
    )
    assert virgin_resp.status_code == 201, virgin_resp.text
    virgin = str(virgin_resp.json()["id"])
    untouched = authed_client.patch(
        _activity_url(virgin),
        json={"description": "没碰绑定"},
        headers={"Idempotency-Key": idem_key(), "If-Match": '"1"'},
    )
    assert untouched.status_code == 200, untouched.text
    assert untouched.json()["bindings"] == []


def test_binding_overlap_is_422(authed_client: TestClient, harness: Harness) -> None:
    """同策略区间相交即拒；两条 ``location`` 同时给出（§3.4 严口径）。"""
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    activity_id = _new_activity(authed_client)
    response = _patch_bindings(
        authed_client,
        activity_id,
        [
            binding_json("S-1", "2026-01-01", "2026-03-01"),
            binding_json("S-1", "2026-02-01", "2026-04-01"),
        ],
        '"1"',
    )
    assert response.status_code == 422, response.text
    body: dict[str, Any] = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["issues"][0]["code"] == "BINDING_OVERLAP"
    assert [issue["location"] for issue in body["issues"]] == [
        "/bindings/0/valid_from",
        "/bindings/1/valid_from",
    ]
    assert _get(authed_client, activity_id)["bindings"] == []


def test_binding_unregistered_evidence_is_422_evidence_required(
    authed_client: TestClient,
) -> None:
    """未播种证据的 ``evidence_id`` → 422 ``EVIDENCE_REQUIRED`` ＋ DENIED 审计（§3.4/§7.3）。"""
    activity_id = _new_activity(authed_client)
    response = _patch_bindings(
        authed_client,
        activity_id,
        [binding_json("S-1", "2026-01-01", "2026-02-01", evidence_id="ev-nope")],
        '"1"',
    )
    assert response.status_code == 422, response.text
    body: dict[str, Any] = response.json()
    assert body["code"] == "EVIDENCE_REQUIRED"
    assert body["issues"][0]["code"] == "BINDING_EVIDENCE_UNREGISTERED"
    assert body["issues"][0]["location"] == "/bindings/0/evidence_id"
    assert _get(authed_client, activity_id)["bindings"] == []


def test_binding_empty_interval_is_422_not_500(authed_client: TestClient, harness: Harness) -> None:
    """起含止排：``valid_until == valid_from`` 是空区间 → 422，领域先判拦住 DDL CHECK（§3.4）。"""
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    activity_id = _new_activity(authed_client)
    response = _patch_bindings(
        authed_client,
        activity_id,
        [binding_json("S-1", "2026-01-01", "2026-01-01")],
        '"1"',
    )
    assert response.status_code == 422, response.text
    assert response.status_code != 500
    body: dict[str, Any] = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["issues"][0]["code"] == "BINDING_EMPTY_INTERVAL"
    assert body["issues"][0]["location"] == "/bindings/0/valid_until"
    current = _get(authed_client, activity_id)
    assert current["bindings"] == [] and current["revision"] == 1
