"""M2-01/S6 · ETag / If-Match 面（design §6.1 / §6.2 / §3.2 / §4.6 / §7.5；裁定 A273 / A274）。

412 与 428 的判定位置在 service 侧（``api/common.py::check_if_match``，design §6.2），三个
If-Match 端点（``updateActivity`` / ``updateRule`` / ``confirmRule``）各钉「陈旧 → 412」与
「缺头 → 428 而非 422」两面（A273 三条具名展开；函数名含 ``etag412`` 满足 V2 的 ``-k``）。
``current_rule_id`` 两条为 FU-54 ①② 的行为钉桩（A274）：判红**禁改 SQL**，走 §8 上报。
"""

from __future__ import annotations

import re
from typing import Any

from fastapi.testclient import TestClient

from campaignlab.api.common import IF_MATCH_PATTERN, etag
from campaignlab.clock import FixedClock
from campaignlab.config import API_PREFIX
from tests.api.activities.conftest import (
    T0,
    WS_ID,
    Harness,
    create_activity_json,
    create_rule_json,
    idem_key,
    seed_evidence,
)


def _activity_url(activity_id: str) -> str:
    return f"{API_PREFIX}/workspaces/{WS_ID}/activities/{activity_id}"


def _rule_url(rule_id: str) -> str:
    return f"{API_PREFIX}/workspaces/{WS_ID}/rules/{rule_id}"


def _new_activity(client: TestClient) -> tuple[str, str]:
    created = create_activity_json(client, WS_ID)
    assert created.status_code == 201, created.text
    return str(created.json()["id"]), str(created.headers["ETag"])


def _new_rule(client: TestClient, activity_id: str, **kwargs: Any) -> tuple[str, str]:
    created = create_rule_json(client, WS_ID, activity_id, **kwargs)
    assert created.status_code == 201, created.text
    return str(created.json()["id"]), str(created.headers["ETag"])


def _digest_of(client: TestClient, rule_id: str) -> str:
    return str(client.get(_rule_url(rule_id)).json()["digest"])


def test_update_activity_etag412_rejects_stale_if_match(authed_client: TestClient) -> None:
    activity_id, first = _new_activity(authed_client)
    assert first == etag(1)
    response = authed_client.patch(
        _activity_url(activity_id),
        json={"name": "改名"},
        headers={"Idempotency-Key": idem_key(), "If-Match": '"9"'},
    )
    assert response.status_code == 412, response.text
    assert response.json()["code"] == "REVISION_CONFLICT"
    current = authed_client.get(_activity_url(activity_id))
    assert current.headers["ETag"] == first


def test_update_rule_etag412_rejects_stale_if_match(authed_client: TestClient) -> None:
    activity_id, _ = _new_activity(authed_client)
    rule_id, first = _new_rule(authed_client, activity_id)
    response = authed_client.patch(
        _rule_url(rule_id),
        json={"label": "v2"},
        headers={"Idempotency-Key": idem_key(), "If-Match": '"9"'},
    )
    assert response.status_code == 412, response.text
    assert response.json()["code"] == "REVISION_CONFLICT"
    frozen = authed_client.get(_rule_url(rule_id))
    assert frozen.headers["ETag"] == first and frozen.json()["revision"] == 1


def test_confirm_rule_etag412_rejects_stale_if_match(
    authed_client: TestClient, harness: Harness
) -> None:
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    activity_id, _ = _new_activity(authed_client)
    rule_id, first = _new_rule(authed_client, activity_id)
    response = authed_client.post(
        f"{_rule_url(rule_id)}/confirm",
        json={"note": "已复核", "digest": _digest_of(authed_client, rule_id)},
        headers={"Idempotency-Key": idem_key(), "If-Match": '"9"'},
    )
    assert response.status_code == 412, response.text
    assert response.json()["code"] == "REVISION_CONFLICT"
    assert authed_client.get(_rule_url(rule_id)).headers["ETag"] == first


def test_update_activity_etag412_missing_if_match_is_428_not_422(
    authed_client: TestClient,
) -> None:
    """A273：缺头必须走到 service 的 ``check_if_match``（428），而非形参必填的 422（§6.2）。"""
    activity_id, _ = _new_activity(authed_client)
    response = authed_client.patch(
        _activity_url(activity_id),
        json={"name": "改名"},
        headers={"Idempotency-Key": idem_key()},
    )
    assert response.status_code == 428, response.text
    assert response.json()["code"] == "PRECONDITION_REQUIRED"


def test_update_rule_etag412_missing_if_match_is_428_not_422(
    authed_client: TestClient,
) -> None:
    activity_id, _ = _new_activity(authed_client)
    rule_id, _ = _new_rule(authed_client, activity_id)
    response = authed_client.patch(
        _rule_url(rule_id),
        json={"label": "v2"},
        headers={"Idempotency-Key": idem_key()},
    )
    assert response.status_code == 428, response.text
    assert response.json()["code"] == "PRECONDITION_REQUIRED"


def test_confirm_rule_etag412_missing_if_match_is_428_not_422(
    authed_client: TestClient,
) -> None:
    activity_id, _ = _new_activity(authed_client)
    rule_id, _ = _new_rule(authed_client, activity_id)
    response = authed_client.post(
        f"{_rule_url(rule_id)}/confirm",
        json={"note": "已复核", "digest": _digest_of(authed_client, rule_id)},
        headers={"Idempotency-Key": idem_key()},
    )
    assert response.status_code == 428, response.text
    assert response.json()["code"] == "PRECONDITION_REQUIRED"


def test_malformed_if_match_is_422(authed_client: TestClient) -> None:
    """格式非法（非陈旧）由形参级校验拦截 → 422，location 固定 ``/header/If-Match``（§6.2）。"""
    activity_id, _ = _new_activity(authed_client)
    for malformed in ("abc", '"0"', "0"):
        response = authed_client.patch(
            _activity_url(activity_id),
            json={"name": "改名"},
            headers={"Idempotency-Key": idem_key(), "If-Match": malformed},
        )
        assert response.status_code == 422, (malformed, response.text)
        body: dict[str, Any] = response.json()
        assert body["code"] == "VALIDATION_ERROR", malformed
        assert body["issues"][0]["location"] == "/header/If-Match", malformed


def test_etag_is_quoted_decimal_revision(authed_client: TestClient) -> None:
    """``ETag`` 形态：带双引号十进制整数，字面 ``fullmatch(IF_MATCH_PATTERN)``（§6.1）。"""
    activity_id, first = _new_activity(authed_client)
    assert first == '"1"'
    assert re.fullmatch(IF_MATCH_PATTERN, first)
    patched = authed_client.patch(
        _activity_url(activity_id),
        json={"name": "改名"},
        headers={"Idempotency-Key": idem_key(), "If-Match": first},
    )
    assert patched.status_code == 200, patched.text
    second = str(patched.headers["ETag"])
    assert second == '"2"' and int(second.strip('"')) == 2
    assert re.fullmatch(IF_MATCH_PATTERN, second)
    assert authed_client.get(_activity_url(activity_id)).headers["ETag"] == second


def test_confirm_rule_bumps_activity_etag_and_current_rule_id(
    authed_client: TestClient, harness: Harness
) -> None:
    """§3.2 末条：确认同事务把 ``current_rule_id`` 指向本版本并 bump 活动 revision（V9）。"""
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    activity_id, act_etag = _new_activity(authed_client)
    assert authed_client.get(_activity_url(activity_id)).json()["current_rule_id"] is None
    rule_id, rule_etag = _new_rule(authed_client, activity_id)
    confirmed = authed_client.post(
        f"{_rule_url(rule_id)}/confirm",
        json={"note": "已复核", "digest": _digest_of(authed_client, rule_id)},
        headers={"Idempotency-Key": idem_key(), "If-Match": rule_etag},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["state"] == "CONFIRMED"
    assert confirmed.headers["ETag"] == etag(2)
    activity = authed_client.get(_activity_url(activity_id))
    assert activity.headers["ETag"] == etag(2) and activity.headers["ETag"] != act_etag
    assert activity.json()["current_rule_id"] == rule_id


def test_current_rule_id_follows_the_latest_confirmed_successor_a_then_b(
    authed_client: TestClient, harness: Harness
) -> None:
    """FU-54 ①（A274）：顺序确认 A→B（B 为 A 的 R4 后继）后 ``current_rule_id == B``。"""
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    activity_id, _ = _new_activity(authed_client)
    a_id, a_etag = _new_rule(authed_client, activity_id, label="A")
    confirmed_a = authed_client.post(
        f"{_rule_url(a_id)}/confirm",
        json={"note": "确认A", "digest": _digest_of(authed_client, a_id)},
        headers={"Idempotency-Key": idem_key(), "If-Match": a_etag},
    )
    assert confirmed_a.status_code == 200, confirmed_a.text
    b_id, b_etag = _new_rule(authed_client, activity_id, label="B", parent_rule_id=a_id)
    confirmed_b = authed_client.post(
        f"{_rule_url(b_id)}/confirm",
        json={"note": "确认B", "digest": _digest_of(authed_client, b_id)},
        headers={"Idempotency-Key": idem_key(), "If-Match": b_etag},
    )
    assert confirmed_b.status_code == 200, confirmed_b.text
    at_a = str(authed_client.get(_rule_url(a_id)).json()["confirmed_at"])
    at_b = str(confirmed_b.json()["confirmed_at"])
    assert at_b > at_a, "服务侧步进时钟失效：B 的确认时刻必须严格晚于 A"
    activity = authed_client.get(_activity_url(activity_id))
    assert activity.json()["current_rule_id"] == b_id
    assert activity.json()["revision"] == 3


def test_current_rule_id_tie_break_is_id_lexicographic_max_per_design_3_2(
    harness: Harness,
) -> None:
    """FU-54 ②（A274）：``confirmed_at`` 真实并列时，最终值取 ``id`` 字典序最大者（§3.2）。

    并列由 step=0 固定时钟的独立 ``RuleService`` 制造；确认顺序按 ``id`` 升序（先小后大），
    于是「最后确认者」与「字典序最大者」重合，设计语义与实现行为在此用例内必然同绿。
    """
    seed_evidence(harness.engine, WS_ID, artifact_id="art-1", evidence_id="ev-1")
    client = harness.s6_client(
        rule_service=harness.make_rule_service(clock=FixedClock(T0)),
    )
    activity_id, _ = _new_activity(client)
    x_id, _ = _new_rule(client, activity_id, label="X")
    y_id, _ = _new_rule(client, activity_id, label="Y")
    smaller, larger = sorted((x_id, y_id))
    for rule_id, note in ((smaller, "先确认小"), (larger, "后确认大")):
        response = client.post(
            f"{_rule_url(rule_id)}/confirm",
            json={"note": note, "digest": _digest_of(client, rule_id)},
            headers={"Idempotency-Key": idem_key(), "If-Match": '"1"'},
        )
        assert response.status_code == 200, response.text
    at_smaller = client.get(_rule_url(smaller)).json()["confirmed_at"]
    at_larger = client.get(_rule_url(larger)).json()["confirmed_at"]
    assert at_smaller == at_larger == "2026-11-16T01:00:00Z", "并列前提未成立"
    activity = client.get(_activity_url(activity_id))
    assert activity.json()["current_rule_id"] == larger


def test_replay_returns_the_original_etag_even_with_a_wrong_if_match(
    authed_client: TestClient,
) -> None:
    """§7.5 末条：先幂等、后 If-Match ⇒ 同键同体重放回放**原** ETag，即便带错误 If-Match。"""
    activity_id, first = _new_activity(authed_client)
    body = b'{"name":"replay probe"}'
    key = idem_key()
    headers = {
        "Idempotency-Key": key,
        "If-Match": first,
        "Content-Type": "application/json",
    }
    original = authed_client.patch(_activity_url(activity_id), content=body, headers=headers)
    assert original.status_code == 200, original.text
    assert original.headers["ETag"] == etag(2)
    replay = authed_client.patch(
        _activity_url(activity_id),
        content=body,
        headers={**headers, "If-Match": '"9"'},
    )
    assert replay.status_code == 200, replay.text
    assert replay.headers["ETag"] == etag(2)
    assert replay.json() == original.json()
    assert authed_client.get(_activity_url(activity_id)).headers["ETag"] == etag(2)


def test_label_only_update_changes_etag_but_not_digest(
    authed_client: TestClient,
) -> None:
    """§4.6 反直觉面：``label`` 不进摘要 ⇒ 只改 label 时 ETag 变、digest 不变。"""
    activity_id, _ = _new_activity(authed_client)
    rule_id, first = _new_rule(authed_client, activity_id)
    before = authed_client.get(_rule_url(rule_id)).json()
    patched = authed_client.patch(
        _rule_url(rule_id),
        json={"label": "v1-改名"},
        headers={"Idempotency-Key": idem_key(), "If-Match": first},
    )
    assert patched.status_code == 200, patched.text
    after: dict[str, Any] = patched.json()
    assert patched.headers["ETag"] == etag(2)
    assert after["digest"] == before["digest"]
    assert after["label"] == "v1-改名" and after["revision"] == 2
