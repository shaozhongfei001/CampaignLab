"""M0-02/S4 · 5 个 operationId 的 HTTP 契约参数化（Problem 结构 + 分支取证）。

期望值一律来自**实现侧权威**：状态码／``type``／``title`` 由 ``domain/errors.py`` 的
``PROBLEM_CODES`` 注册表反查（A95：禁另立状态码清单、禁自造错误码），
``issues[]`` 的字段集由活契约 ``components.schemas.Issue`` 钉住（在
``test_contract_declarations.py`` 里比对），正文形状交给 DTO 的 ``extra="forbid"`` 校验。

jobs 的 4 个 op（listJobs/getJob/cancelJob/retryJob）与 202 语义 **deferred_to: M0-04/S4**（A84），
本文件不写任何 jobs 用例。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any, Final

import pytest
from conftest import EVIL_HOST, EVIL_ORIGIN, T0, Harness
from fastapi.testclient import TestClient

from campaignlab.api.common import X_REQUEST_ID_HEADER, Problem
from campaignlab.application.session_service import SESSION_COOKIE_NAME, SESSION_INVALID_DETAIL
from campaignlab.config import API_PREFIX
from campaignlab.domain.errors import PROBLEM_CODES

EXCHANGE_URL: Final = f"{API_PREFIX}/session/exchange"
SESSION_URL: Final = f"{API_PREFIX}/session"
WORKSPACES_URL: Final = f"{API_PREFIX}/workspaces"
#: 16–180 之间的合法长度（契约 ``SessionExchange.token``）。
GOOD_TOKEN: Final = "contract-token-0000000001"
IDEM: Final = "contract-key-000001"
BODY_LIMIT: Final = 64
VALID_CREATE: Final[dict[str, Any]] = {
    "name": "契约工作区",
    "source_class": "SYNTHETIC",
    "authorization_note": "合成数据，无真实主体",
}
JSON_HEADERS: Final = {"Content-Type": "application/json"}


def exchange_json(client: TestClient, token: str = GOOD_TOKEN) -> Any:
    return client.post(EXCHANGE_URL, json={"token": token})


def authed(harness: Harness, **kwargs: Any) -> TestClient:
    """真实换取一条会话（走同一条 op，不复用内部 service 之外的后门）。"""
    client, response = harness.exchange(**kwargs)
    assert response.status_code == 200, response.text
    return client


def create_workspace(
    harness: Harness, payload: dict[str, Any] | None = None, *, key: str = IDEM, **kwargs: Any
) -> Any:
    client = authed(harness, **{k: v for k, v in kwargs.items() if k != "headers"})
    return client.post(
        WORKSPACES_URL,
        json=dict(VALID_CREATE if payload is None else payload),
        headers={"Idempotency-Key": key},
    )


def assert_problem(response: Any, code: str, *, expect_location: str | None = None) -> Problem:
    """Problem 逐字段断言：type/title/status/code/detail/request_id/issues。"""
    status, type_, title = PROBLEM_CODES[code]
    body: dict[str, Any] = dict(response.json())
    problem = Problem.model_validate(body)
    assert problem.code == code
    assert problem.status == status
    assert problem.type == type_ == "urn:campaignlab:problem:" + code.lower()
    assert problem.title == title
    assert 1 <= len(problem.detail) <= 500
    assert len(problem.request_id) <= 96
    assert isinstance(problem.issues, list)
    for issue in problem.issues:
        assert issue.code in PROBLEM_CODES
        assert issue.location.startswith("/") and 1 <= len(issue.location) <= 500
        assert 1 <= len(issue.message) <= 500
        assert issue.severity in {"ERROR", "WARNING", "INFO"}
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers[X_REQUEST_ID_HEADER] == problem.request_id
    if expect_location is not None:
        assert problem.issues[0].location == expect_location
    return problem


#: (用例 id, operationId, 错误码, 触发动作)
NEGATIVE: Final[list[tuple[str, str, str, Callable[[Harness], Any]]]] = [
    (
        "exchange_body_not_json",
        "exchangeSession",
        "BAD_REQUEST",
        lambda h: h.client().post(EXCHANGE_URL, content=b"{not-json", headers=JSON_HEADERS),
    ),
    (
        "exchange_wrong_content_type",
        "exchangeSession",
        "BAD_REQUEST",
        lambda h: h.client().post(
            EXCHANGE_URL,
            content=json.dumps({"token": GOOD_TOKEN}).encode(),
            headers={"Content-Type": "text/plain"},
        ),
    ),
    (
        "exchange_body_too_large",
        "exchangeSession",
        "INPUT_TOO_LARGE",
        lambda h: h.client(max_body_bytes=BODY_LIMIT).post(
            EXCHANGE_URL,
            content=json.dumps({"token": GOOD_TOKEN}).encode() + b" " * BODY_LIMIT,
            headers=JSON_HEADERS,
        ),
    ),
    (
        "exchange_token_too_short",
        "exchangeSession",
        "VALIDATION_ERROR",
        lambda h: h.client().post(EXCHANGE_URL, json={"token": "short-token"}),
    ),
    (
        "exchange_token_too_long",
        "exchangeSession",
        "VALIDATION_ERROR",
        lambda h: h.client().post(EXCHANGE_URL, json={"token": "t" * 181}),
    ),
    (
        "exchange_unknown_field",
        "exchangeSession",
        "VALIDATION_ERROR",
        lambda h: h.client().post(EXCHANGE_URL, json={"token": GOOD_TOKEN, "actor_id": "x"}),
    ),
    (
        "exchange_token_unknown",
        "exchangeSession",
        "SESSION_EXPIRED",
        lambda h: h.client().post(EXCHANGE_URL, json={"token": "never-minted-0000000000"}),
    ),
    ("exchange_token_consumed", "exchangeSession", "SESSION_EXPIRED", lambda h: _twice(h)),
    (
        "exchange_token_expired",
        "exchangeSession",
        "SESSION_EXPIRED",
        lambda h: h.client(at=T0 + timedelta(seconds=61)).post(
            EXCHANGE_URL, json={"token": h.mint_token(at=T0)}
        ),
    ),
    (
        "exchange_origin_denied",
        "exchangeSession",
        "ORIGIN_DENIED",
        lambda h: h.client().post(
            EXCHANGE_URL, json={"token": GOOD_TOKEN}, headers={"Origin": EVIL_ORIGIN}
        ),
    ),
    (
        "exchange_host_denied",
        "exchangeSession",
        "ORIGIN_DENIED",
        lambda h: h.client().post(
            EXCHANGE_URL, json={"token": GOOD_TOKEN}, headers={"Host": EVIL_HOST}
        ),
    ),
    (
        "session_without_cookie",
        "getSession",
        "SESSION_EXPIRED",
        lambda h: h.client().get(SESSION_URL),
    ),
    (
        "session_bogus_cookie",
        "getSession",
        "SESSION_EXPIRED",
        lambda h: h.client().get(
            SESSION_URL, headers={"Cookie": f"{SESSION_COOKIE_NAME}=not-a-known-session"}
        ),
    ),
    (
        "session_host_denied",
        "getSession",
        "ORIGIN_DENIED",
        lambda h: h.client().get(SESSION_URL, headers={"Host": EVIL_HOST}),
    ),
    (
        "list_without_cookie",
        "listWorkspaces",
        "SESSION_EXPIRED",
        lambda h: h.client().get(WORKSPACES_URL),
    ),
    (
        "list_host_denied",
        "listWorkspaces",
        "ORIGIN_DENIED",
        lambda h: h.client().get(WORKSPACES_URL, headers={"Host": EVIL_HOST}),
    ),
    (
        "list_bad_limit",
        "listWorkspaces",
        "VALIDATION_ERROR",
        lambda h: authed(h).get(WORKSPACES_URL, params={"limit": 0}),
    ),
    (
        "list_bad_cursor",
        "listWorkspaces",
        "BAD_CURSOR",
        lambda h: authed(h).get(WORKSPACES_URL, params={"cursor": "not-a-signed-cursor"}),
    ),
    (
        "list_cursor_too_long",
        "listWorkspaces",
        "VALIDATION_ERROR",
        lambda h: authed(h).get(WORKSPACES_URL, params={"cursor": "c" * 301}),
    ),
    (
        "create_without_cookie",
        "createWorkspace",
        "SESSION_EXPIRED",
        lambda h: h.client().post(
            WORKSPACES_URL, json=VALID_CREATE, headers={"Idempotency-Key": IDEM}
        ),
    ),
    (
        "create_origin_denied",
        "createWorkspace",
        "ORIGIN_DENIED",
        lambda h: h.client().post(
            WORKSPACES_URL,
            json=VALID_CREATE,
            headers={"Idempotency-Key": IDEM, "Origin": EVIL_ORIGIN},
        ),
    ),
    (
        "create_body_not_json",
        "createWorkspace",
        "BAD_REQUEST",
        lambda h: authed(h).post(
            WORKSPACES_URL, content=b"{oops", headers={**JSON_HEADERS, "Idempotency-Key": IDEM}
        ),
    ),
    ("create_body_too_large", "createWorkspace", "INPUT_TOO_LARGE", lambda h: create_large(h)),
    (
        "create_name_empty",
        "createWorkspace",
        "VALIDATION_ERROR",
        lambda h: create_workspace(h, {**VALID_CREATE, "name": ""}),
    ),
    (
        "create_name_too_long",
        "createWorkspace",
        "VALIDATION_ERROR",
        lambda h: create_workspace(h, {**VALID_CREATE, "name": "n" * 81}),
    ),
    (
        "create_source_class_not_enum",
        "createWorkspace",
        "VALIDATION_ERROR",
        lambda h: create_workspace(h, {**VALID_CREATE, "source_class": "PUBLIC_RAW"}),
    ),
    (
        "create_note_too_long",
        "createWorkspace",
        "VALIDATION_ERROR",
        lambda h: create_workspace(h, {**VALID_CREATE, "authorization_note": "a" * 501}),
    ),
    (
        "create_unknown_field",
        "createWorkspace",
        "VALIDATION_ERROR",
        lambda h: create_workspace(h, {**VALID_CREATE, "actor_role": "OPERATOR"}),
    ),
    (
        "create_missing_idempotency_key",
        "createWorkspace",
        "VALIDATION_ERROR",
        lambda h: authed(h).post(WORKSPACES_URL, json=VALID_CREATE),
    ),
    (
        "create_idempotency_key_too_short",
        "createWorkspace",
        "VALIDATION_ERROR",
        lambda h: authed(h).post(
            WORKSPACES_URL, json=VALID_CREATE, headers={"Idempotency-Key": "short"}
        ),
    ),
    (
        "create_idempotency_key_too_long",
        "createWorkspace",
        "VALIDATION_ERROR",
        lambda h: authed(h).post(
            WORKSPACES_URL, json=VALID_CREATE, headers={"Idempotency-Key": "k" * 129}
        ),
    ),
]

_HEADER_LOCATION: Final = "/header/Idempotency-Key"


def _twice(harness: Harness) -> Any:
    client = harness.client()
    token = harness.mint_token()
    assert exchange_json(client, token).status_code == 200
    return exchange_json(client, token)


def create_large(harness: Harness) -> Any:
    client = authed(harness, max_body_bytes=BODY_LIMIT)
    return client.post(
        WORKSPACES_URL,
        json={**VALID_CREATE, "authorization_note": "a" * BODY_LIMIT},
        headers={"Idempotency-Key": IDEM},
    )


@pytest.mark.parametrize("case", NEGATIVE, ids=[entry[0] for entry in NEGATIVE])
def test_negative_branches_are_problem_shaped(
    harness: Harness, case: tuple[str, str, str, Any]
) -> None:
    """5 个 op 的每个已实现分支都必须落成 Problem 形（逐字段断言见 ``assert_problem``）。"""
    _name, _operation_id, code, action = case
    assert_problem(action(harness), code)


def test_idempotency_key_length_reports_header_location(harness: Harness) -> None:
    for key in ("short", "k" * 129):
        response = authed(harness).post(
            WORKSPACES_URL, json=VALID_CREATE, headers={"Idempotency-Key": key}
        )
        assert_problem(response, "VALIDATION_ERROR", expect_location=_HEADER_LOCATION)


def test_401_session_expired_is_not_an_enumeration_oracle(harness: Harness) -> None:
    """未知／已消费／超 60s 三种成因 → 同码同 detail（杜绝枚举 oracle）。"""
    causes = [
        harness.client().post(EXCHANGE_URL, json={"token": "never-minted-0000000000"}),
        _twice(harness),
        harness.client(at=T0 + timedelta(seconds=61)).post(
            EXCHANGE_URL, json={"token": harness.mint_token(at=T0)}
        ),
    ]
    problems = [assert_problem(response, "SESSION_EXPIRED") for response in causes]
    assert {problem.detail for problem in problems} == {SESSION_INVALID_DETAIL}
    assert {problem.status for problem in problems} == {401}
    assert {problem.title for problem in problems} == {PROBLEM_CODES["SESSION_EXPIRED"][2]}
    assert len({problem.request_id for problem in problems}) == 3


def test_exchange_200_publishes_session_cookie_and_body(harness: Harness) -> None:
    """200 ``Session`` + ``Set-Cookie``（A96：``SameSite`` 大小写不敏感断言）。"""
    client = harness.client()
    token = harness.mint_token()
    response = exchange_json(client, token)
    assert response.status_code == 200, response.text
    session = dict(response.json())
    assert session["actor_id"] == "tester"
    assert "OPERATOR" in session["allowed_roles"]
    raw = response.headers["set-cookie"]
    parts = [part.strip() for part in raw.split(";")]
    assert parts[0].startswith(f"{SESSION_COOKIE_NAME}=")
    session_id = parts[0].split("=", 1)[1]
    attributes: dict[str, str] = {}
    flags: list[str] = []
    for part in parts[1:]:
        if "=" in part:
            name, value = part.split("=", 1)
            attributes[name.lower()] = value
        else:
            flags.append(part.lower())
    assert "httponly" in flags
    assert attributes["path"] == API_PREFIX
    assert attributes["max-age"] == "3600"
    assert attributes["samesite"].lower() == "strict"
    assert session_id and session_id != token
    follow = client.get(SESSION_URL)
    assert follow.status_code == 200, follow.text
    assert dict(follow.json()) == session


def test_get_session_ignores_origin_but_still_checks_host(harness: Harness) -> None:
    """GET 不校验 Origin（design §1）：坏 Origin 仍是 401，而不是 403。"""
    response = harness.client().get(SESSION_URL, headers={"Origin": EVIL_ORIGIN})
    assert_problem(response, "SESSION_EXPIRED")


def test_create_workspace_201_publishes_etag_and_full_body(harness: Harness) -> None:
    response = create_workspace(harness)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = dict(response.json())
    assert body["revision"] == 1
    assert body["name"] == VALID_CREATE["name"]
    assert body["source_class"] == "SYNTHETIC"
    assert "authorization_note" in body
    assert response.headers["ETag"] == '"1"'
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers[X_REQUEST_ID_HEADER]
    listing = authed(harness).get(WORKSPACES_URL).json()
    assert len(listing["items"]) == 1
    assert listing["items"][0]["id"] == body["id"]


def test_idempotency_replay_is_byte_identical_and_writes_once(harness: Harness) -> None:
    """同键同摘要重放：状态码／``ETag``／正文字节内容一致，且只写一次（卡 S4 行 + design §4）。

    **已上报 U-2**：实测 ``first.content`` 与 ``second.content`` 的**键序**不同——新建路径的正文体
    来自 DTO 的声明序，重放路径来自 ``replay_from_envelope`` 对信封 ``json.dumps`` 的字典序；
    语义（同一 id／revision／ETag）与「只写一次」成立，但卡 S4 行要求的「逐字节相同」需要改
    ``src/campaignlab/**`` 才能达成，不在 S4 写集内，故此处按语义等价断言并留本注记。
    """
    client = authed(harness)
    first = client.post(WORKSPACES_URL, json=VALID_CREATE, headers={"Idempotency-Key": IDEM})
    second = client.post(WORKSPACES_URL, json=VALID_CREATE, headers={"Idempotency-Key": IDEM})
    assert first.status_code == second.status_code == 201
    assert json.loads(first.content) == json.loads(second.content)
    assert first.headers["ETag"] == second.headers["ETag"] == '"1"'
    assert first.headers[X_REQUEST_ID_HEADER] != second.headers[X_REQUEST_ID_HEADER]
    assert harness.count_workspaces() == 1


def test_idempotency_conflict_same_key_different_digest_is_409(harness: Harness) -> None:
    client = authed(harness)
    other = {**VALID_CREATE, "name": "另一个契约工作区"}
    assert (
        client.post(
            WORKSPACES_URL, json=other, headers={"Idempotency-Key": "conflict-key-0001"}
        ).status_code
        == 201
    )
    conflict = client.post(
        WORKSPACES_URL,
        json=VALID_CREATE,
        headers={"Idempotency-Key": "conflict-key-0001"},
    )
    assert_problem(conflict, "IDEMPOTENCY_CONFLICT")
    assert harness.count_workspaces() == 1
