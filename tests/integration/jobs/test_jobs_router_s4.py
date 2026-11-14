"""M0-04/S4 守护与用例（jobs HTTP 面）——fixture 自带，**本目录的 ``conftest.py`` 归 S5，禁建**。

装配口径照抄 ``tests/api/conftest.py`` 的既有做法（重复不是问题，争用才是，派单 §2.4）：
DDL 直读活契约 ``contracts/sqlite-v1.sql``、``FixedClock`` 显式时钟、六注入位显式给齐。
jobs 服务不经 ``create_app`` 注入——``worker/deps.py::get_job_service`` 按
``app.state.config.database_url`` 自建引擎，故本文件的 DB 位置通过
``CAMPAIGNLAB_DATABASE_URL`` 环境变量与 config 对齐（五级链唯一实现，ADR-005 §2.4）。

本文件钉住 S4 的全部冻结判据：jobs 模块符号面（design §9-S4 行）、挂载条件（派单 §4①
候选 (b)）、``JobPage`` 与活契约逐字段对齐（A91）、``listJobs`` 的路由侧 404（A220）、
游标编解码归路由而绑定校验留服务层（A169③）、先幂等后 If-Match 的四态映射（§6）、
``JOB_INTERRUPTED`` 只落 ``issues[0].code``（N7③）、Problem code 必属权威 20 码（D-019）、
以及 D-045 的墙钟字面量自检（本文件用拼接构造禁串，不内嵌字面量）。
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from campaignlab.api import common as common_module
from campaignlab.api import jobs as jobs_module
from campaignlab.api.app import create_app
from campaignlab.api.common import (
    PROBLEM_CODES,
    JobPage,
    OriginHostGuard,
    Problem,
    encode_cursor,
)
from campaignlab.api.common import Issue as IssueDto
from campaignlab.application.session_service import (
    SessionService,
    SessionStore,
    SessionTokenStore,
)
from campaignlab.application.workspace_service import (
    BAD_CURSOR_DETAIL,
    CURSOR_VERSION,
    WorkspaceService,
    load_cursor_secret,
)
from campaignlab.clock import FixedClock
from campaignlab.config import API_PREFIX, AppIdentity, load_config
from campaignlab.infra.db.engine import make_engine
from campaignlab.worker.store import JobStore

REPO: Final = Path(__file__).resolve().parents[3]
DDL: Final = REPO / "contracts/sqlite-v1.sql"
LIVE_CONTRACT: Final[dict[str, Any]] = json.loads(
    (REPO / "contracts/openapi.json").read_text(encoding="utf-8")
)
JOBS_PY: Final = REPO / "src/campaignlab/api/jobs.py"

T0: Final = datetime(2026, 11, 13, 1, 0, 0, tzinfo=UTC)
TOKEN_TTL: Final = 60
SESSION_TTL: Final = 3600
GUARD: Final = OriginHostGuard(frozenset({"testserver"}), frozenset({"http://testserver"}))
TEST_ORIGIN: Final = "http://testserver"
IDENTITY: Final = AppIdentity(
    actor_id="s4-tester",
    actor_name="s4-tester",
    allowed_roles=("OPERATOR", "DESIGNER", "DATA_OWNER", "ANALYST", "TESTER", "REVIEWER"),
)
JOB_FIELDS: Final = {
    "id",
    "revision",
    "created_at",
    "kind",
    "state",
    "attempt",
    "progress",
    "stage",
    "input_digest",
    "retry_of",
    "result_ref",
    "problem",
    "retryable",
}
_REQUEST_ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")


def _fold_digest(workspace_id: str, limit: int, q: str | None, status: str | None) -> str:
    """design §1 公式在测试侧的复算（fixture 用途，非 src 第二份实现）。"""
    raw = json.dumps(
        {"workspace_id": workspace_id, "limit": limit, "q": q, "status": status},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class Harness:
    """一份 DB + 真实 WorkspaceService/SessionService + 经 config 注入的 jobs 引擎。"""

    def __init__(self, tmp_path: Path) -> None:
        self.db_path = tmp_path / "campaignlab.db"
        raw = sqlite3.connect(self.db_path)
        try:
            raw.executescript(DDL.read_text(encoding="utf-8"))
            raw.commit()
        finally:
            raw.close()
        self.engine: Engine = make_engine(f"sqlite:///{self.db_path}")
        self.config = load_config(
            environ={
                "CAMPAIGNLAB_DATA_DIR": str(tmp_path),
                "CAMPAIGNLAB_DATABASE_URL": f"sqlite:///{self.db_path}",
            },
            home=tmp_path,
        )
        self.clock = FixedClock(T0)
        self.session_service = SessionService(
            tokens=SessionTokenStore(ttl_seconds=TOKEN_TTL),
            sessions=SessionStore(ttl_seconds=SESSION_TTL),
        )
        self.workspace_service = WorkspaceService(
            engine=self.engine, clock=self.clock, config=self.config
        )

    def make_app(self, *, with_workspace: bool = True) -> FastAPI:
        return create_app(
            self.config,
            clock=FixedClock(T0),
            guard=GUARD,
            session_service=self.session_service,
            workspace_service=self.workspace_service if with_workspace else None,
        )

    def authed_client(self, *, with_workspace: bool = True) -> TestClient:
        client = TestClient(
            self.make_app(with_workspace=with_workspace), headers={"Origin": TEST_ORIGIN}
        )
        token = self.session_service.tokens.mint(IDENTITY, T0)
        response = client.post(f"{API_PREFIX}/session/exchange", json={"token": token})
        assert response.status_code == 200, response.text
        return client

    def seed_workspace(self, workspace_id: str) -> None:
        raw = sqlite3.connect(self.db_path)
        try:
            raw.execute(
                "INSERT INTO workspaces(id, name, source_class, authorization_note, revision,"
                " created_at) VALUES (?, ?, ?, NULL, 1, ?)",
                (workspace_id, f"ws-{workspace_id}", "SYNTHETIC", T0.isoformat()),
            )
            raw.commit()
        finally:
            raw.close()

    def seed_job(
        self, workspace_id: str, job_id: str, *, at: datetime = T0, state: str | None = None
    ) -> None:
        JobStore(engine=self.engine).enqueue(
            workspace_id=workspace_id,
            kind="VALIDATE_IMPORT",
            input_json="{}",
            input_digest="0" * 64,
            now=at,
            job_id=job_id,
        )
        if state is not None:
            raw = sqlite3.connect(self.db_path)
            try:
                raw.execute(
                    "UPDATE jobs SET state = ?, retryable = 1 WHERE workspace_id = ? AND id = ?",
                    (state, workspace_id, job_id),
                )
                raw.commit()
            finally:
                raw.close()

    def seed_interrupted_job(self, workspace_id: str, job_id: str) -> None:
        self.seed_job(workspace_id, job_id, state="FAILED")
        registry = PROBLEM_CODES["INTERNAL_ERROR"]
        problem = Problem(
            type=registry[1],
            title=registry[2],
            status=registry[0],
            code="INTERNAL_ERROR",
            detail="request_id=seed",
            request_id="seed",
            issues=[
                IssueDto(
                    code="JOB_INTERRUPTED",
                    location="/state",
                    message="租约到期，作业被判定中断",
                    severity="ERROR",
                )
            ],
        )
        raw = sqlite3.connect(self.db_path)
        try:
            raw.execute(
                "UPDATE jobs SET problem_json = ? WHERE workspace_id = ? AND id = ?",
                (problem.model_dump_json(), workspace_id, job_id),
            )
            raw.commit()
        finally:
            raw.close()

    def count_rows(self, table: str, where: str = "", params: tuple[Any, ...] = ()) -> int:
        raw = sqlite3.connect(self.db_path)
        try:
            row = raw.execute(f"SELECT COUNT(*) FROM {table} {where}", params).fetchone()
        finally:
            raw.close()
        assert row is not None
        return int(row[0])

    def cursor_for(
        self,
        workspace_id: str,
        *,
        limit: int = 25,
        q: str | None = None,
        status: str | None = None,
        version: int = CURSOR_VERSION,
        actor_id: str = IDENTITY.actor_id,
        key: list[Any] | None = None,
        digest: str | None = None,
    ) -> str:
        secret = load_cursor_secret(self.config.data_dir)
        payload: dict[str, Any] = {
            "v": version,
            "q": digest if digest is not None else _fold_digest(workspace_id, limit, q, status),
            "k": key if key is not None else [T0.isoformat(), "j-0001"],
            "s": actor_id,
        }
        return encode_cursor(payload, secret)


@pytest.fixture
def harness(tmp_path: Path) -> Harness:
    return Harness(tmp_path)


@pytest.fixture
def client(harness: Harness) -> TestClient:
    return harness.authed_client()


@pytest.fixture
def ws(client: TestClient, harness: Harness) -> str:
    harness.seed_workspace("ws-s4")
    return "ws-s4"


def jobs_url(workspace_id: str) -> str:
    return f"{API_PREFIX}/workspaces/{workspace_id}/jobs"


def job_url(workspace_id: str, job_id: str) -> str:
    return f"{API_PREFIX}/workspaces/{workspace_id}/jobs/{job_id}"


def assert_problem(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    assert body["code"] == code
    assert code in PROBLEM_CODES
    assert body["type"] == "urn:campaignlab:problem:" + code.lower()
    assert _REQUEST_ID_PATTERN.match(response.headers["X-Request-Id"])
    return body


# ------------------------------------------------------------------ 守护：符号面 / 挂载 / DTO


def test_jobs_module_symbol_surface_is_exactly_frozen() -> None:
    assert list(jobs_module.__all__) == [
        "cancel_job",
        "get_job",
        "list_jobs",
        "retry_job",
        "router",
    ]
    tree = ast.parse(JOBS_PY.read_text(encoding="utf-8"))
    funcs = [
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert sorted(funcs) == sorted(
        ["list_jobs", "get_job", "cancel_job", "retry_job", "_job_page_response", "_job_response"]
    )
    assert classes == []


def test_jobs_router_mounted_only_when_workspace_service_assembled(tmp_path: Path) -> None:
    """§4① 候选 (b) 的挂载守护：装配了 workspace_service 才有 jobs 面（HTTP 行为口径）。

    本仓未知路径被全局处理器统一收敛为 Problem 404（与「工作区不存在」同码），故挂载
    与否的可观测判据是**响应形状**：挂载态返回分页壳（有 items 键），未挂载态返回
    Problem 形（无 items 键）。正向控制（删 include_router 行）会打掉前半段的 200。
    """
    local = Harness(tmp_path)
    local.seed_workspace("ws-mount")
    mounted = local.authed_client(with_workspace=True)
    ok = mounted.get(jobs_url("ws-mount"))
    assert ok.status_code == 200, ok.text
    assert set(ok.json()) == {"items", "next_cursor"}

    unmounted = TestClient(local.make_app(with_workspace=False), headers={"Origin": TEST_ORIGIN})
    token = local.session_service.tokens.mint(IDENTITY, T0)
    assert (
        unmounted.post(f"{API_PREFIX}/session/exchange", json={"token": token}).status_code == 200
    )
    absent = unmounted.get(jobs_url("ws-mount"))
    assert absent.status_code == 404
    assert "items" not in absent.json()
    cancel_absent = unmounted.post(
        job_url("ws-mount", "j-none") + "/cancel",
        headers={"Idempotency-Key": "mount-probe-key", "If-Match": '"1"'},
    )
    assert cancel_absent.status_code == 404
    assert "state" not in cancel_absent.json()


def test_common_all_is_79_with_jobpage_and_problem_codes_still_20() -> None:
    surface = list(common_module.__all__)
    assert len(surface) == 79
    assert "JobPage" in surface
    assert len(PROBLEM_CODES) == 20
    assert surface.count("JobPage") == 1


def test_jobpage_matches_live_contract_schema() -> None:
    schema = LIVE_CONTRACT["components"]["schemas"]["JobPage"]
    assert set(schema["properties"]) == set(JobPage.model_fields)
    assert set(schema["required"]) == {"items", "next_cursor"}
    assert schema["additionalProperties"] is False
    page = JobPage.model_validate({"items": [], "next_cursor": None})
    assert page.items == []
    with pytest.raises(Exception, match="extra"):
        JobPage.model_validate({"items": [], "next_cursor": None, "x": 1})


def test_jobs_source_contains_no_wallclock_literals() -> None:
    src = JOBS_PY.read_text(encoding="utf-8")
    banned = ["datetime" + ".now(", "." + "utcnow(", "time" + ".time(", "time" + ".monotonic("]
    for token in banned:
        assert token not in src, token


# ------------------------------------------------------------------------ listJobs


def test_list_jobs_empty_page_shape(client: TestClient, ws: str) -> None:
    response = client.get(jobs_url(ws))
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    assert set(body) == {"items", "next_cursor"}
    assert body["items"] == []
    assert body["next_cursor"] is None
    assert response.headers["content-type"].startswith("application/json")
    assert _REQUEST_ID_PATTERN.match(response.headers["X-Request-Id"])


def test_list_jobs_ordering_and_cursor_roundtrip(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_job(ws, "j-0001", at=T0)
    harness.seed_job(ws, "j-0002", at=T0 + timedelta(seconds=10))
    harness.seed_job(ws, "j-0003", at=T0 + timedelta(seconds=20))
    first = client.get(jobs_url(ws), params={"limit": 1})
    assert first.status_code == 200
    first_body: dict[str, Any] = first.json()
    assert [item["id"] for item in first_body["items"]] == ["j-0003"]
    cursor = first_body["next_cursor"]
    assert isinstance(cursor, str) and cursor
    second = client.get(jobs_url(ws), params={"limit": 1, "cursor": cursor})
    second_body: dict[str, Any] = second.json()
    assert [item["id"] for item in second_body["items"]] == ["j-0002"]
    third = client.get(jobs_url(ws), params={"limit": 1, "cursor": second_body["next_cursor"]})
    third_body: dict[str, Any] = third.json()
    assert [item["id"] for item in third_body["items"]] == ["j-0001"]
    assert third_body["next_cursor"] is None
    assert set(third_body["items"][0]) == JOB_FIELDS
    assert "lease_token" not in third_body["items"][0]
    assert "lease_until" not in third_body["items"][0]


def test_list_jobs_404_for_absent_workspace(client: TestClient, ws: str) -> None:
    body = assert_problem(client.get(jobs_url("ws-not-seeded")), 404, "RESOURCE_NOT_FOUND")
    assert "ws-not-seeded" not in body["detail"]
    assert body["status"] == 404


def test_list_jobs_sees_other_seeded_workspace_only_when_it_exists(
    client: TestClient, harness: Harness
) -> None:
    harness.seed_workspace("ws-x")
    harness.seed_job("ws-x", "j-x1")
    response = client.get(jobs_url("ws-x"))
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    missing = assert_problem(client.get(jobs_url("ws-y")), 404, "RESOURCE_NOT_FOUND")
    assert missing["detail"] == "工作区不存在或不在你的可见范围"


def test_list_jobs_status_comma_multival_and_illegal(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_job(ws, "j-0001")
    harness.seed_job(ws, "j-0002", at=T0 + timedelta(seconds=5), state="CANCELLED")
    ok = client.get(jobs_url(ws), params={"status": "QUEUED,CANCELLED"})
    assert ok.status_code == 200
    assert {item["state"] for item in ok.json()["items"]} == {"QUEUED", "CANCELLED"}
    six = ",".join(["QUEUED", "RUNNING", "CANCEL_REQUESTED", "SUCCEEDED", "FAILED", "CANCELLED"])
    assert len(six) == 58
    assert client.get(jobs_url(ws), params={"status": six}).status_code == 200
    assert_problem(
        client.get(jobs_url(ws), params={"status": "QUEUED,BOGUS"}), 422, "VALIDATION_ERROR"
    )
    assert_problem(client.get(jobs_url(ws), params={"status": "Q" * 61}), 422, "VALIDATION_ERROR")


def test_list_jobs_limit_out_of_range_is_422(client: TestClient, ws: str) -> None:
    for bad in (0, 101):
        assert_problem(client.get(jobs_url(ws), params={"limit": bad}), 422, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    "mutate",
    ["broken", "version", "digest", "actor", "key"],
    ids=["broken", "version", "digest", "actor", "key"],
)
def test_list_jobs_bad_cursor_matrix(
    client: TestClient, ws: str, harness: Harness, mutate: str
) -> None:
    if mutate == "broken":
        cursor = "not-a-real-cursor"
    elif mutate == "version":
        cursor = harness.cursor_for(ws, version=CURSOR_VERSION + 1)
    elif mutate == "digest":
        cursor = harness.cursor_for(ws, digest="f" * 16)
    elif mutate == "actor":
        cursor = harness.cursor_for(ws, actor_id="someone-else")
    else:
        cursor = harness.cursor_for(ws, key=["a", "b", "c"])
    body = assert_problem(client.get(jobs_url(ws), params={"cursor": cursor}), 400, "BAD_CURSOR")
    assert body["detail"] == BAD_CURSOR_DETAIL


def test_list_jobs_cursor_over_max_length_is_422(client: TestClient, ws: str) -> None:
    assert_problem(client.get(jobs_url(ws), params={"cursor": "x" * 301}), 422, "VALIDATION_ERROR")


def test_list_jobs_q_matches_folded_id(client: TestClient, ws: str, harness: Harness) -> None:
    harness.seed_job(ws, "j-0001")
    harness.seed_job(ws, "j-0002", at=T0 + timedelta(seconds=5))
    response = client.get(jobs_url(ws), params={"q": "J-0002"})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["j-0002"]


# ---------------------------------------------------------------------------- getJob


def test_get_job_200_with_etag_and_repeat_identical(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_job(ws, "j-0001")
    first = client.get(job_url(ws, "j-0001"))
    assert first.status_code == 200, first.text
    assert first.headers["ETag"] == '"1"'
    assert set(first.json()) == JOB_FIELDS
    second = client.get(job_url(ws, "j-0001"))
    assert second.content == first.content


def test_get_job_404_absent_or_cross_workspace(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_workspace("ws-other")
    harness.seed_job(ws, "j-0001")
    body = assert_problem(client.get(job_url(ws, "j-missing")), 404, "RESOURCE_NOT_FOUND")
    assert body["detail"] == "作业不存在或不属于该工作区：j-missing"
    cross = assert_problem(client.get(job_url("ws-other", "j-0001")), 404, "RESOURCE_NOT_FOUND")
    assert cross["detail"] == "作业不存在或不属于该工作区：j-0001"
    assert cross["status"] == body["status"] and cross["code"] == body["code"]


# -------------------------------------------------------------------------- cancelJob


def _cancel(client: TestClient, url: str, key: str, if_match: str | None = None) -> Any:
    headers = {"Idempotency-Key": key}
    if if_match is not None:
        headers["If-Match"] = if_match
    return client.post(url, headers=headers)


def test_cancel_job_queued_becomes_cancelled_200(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_job(ws, "j-0001")
    response = _cancel(client, job_url(ws, "j-0001") + "/cancel", "cancel-key-aaaaaaaa", '"1"')
    assert response.status_code == 200, response.text
    assert response.headers["ETag"] == '"2"'
    assert response.json()["state"] == "CANCELLED"
    assert client.get(job_url(ws, "j-0001")).json()["state"] == "CANCELLED"


def test_cancel_job_missing_if_match_is_428(client: TestClient, ws: str, harness: Harness) -> None:
    harness.seed_job(ws, "j-0001")
    assert_problem(
        _cancel(client, job_url(ws, "j-0001") + "/cancel", "cancel-key-428aaaaa"),
        428,
        "PRECONDITION_REQUIRED",
    )


def test_cancel_job_stale_if_match_is_412(client: TestClient, ws: str, harness: Harness) -> None:
    harness.seed_job(ws, "j-0001")
    assert_problem(
        _cancel(client, job_url(ws, "j-0001") + "/cancel", "cancel-key-412aaaaa", '"99"'),
        412,
        "REVISION_CONFLICT",
    )


def test_cancel_job_absent_is_404(client: TestClient, ws: str) -> None:
    assert_problem(
        _cancel(client, job_url(ws, "j-none") + "/cancel", "cancel-key-404aaaaa", '"1"'),
        404,
        "RESOURCE_NOT_FOUND",
    )


def test_cancel_job_short_idempotency_key_is_422(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_job(ws, "j-0001")
    assert_problem(
        client.post(
            job_url(ws, "j-0001") + "/cancel",
            headers={"Idempotency-Key": "abc", "If-Match": '"1"'},
        ),
        422,
        "VALIDATION_ERROR",
    )


def test_cancel_job_idempotent_replay_is_byte_identical(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_job(ws, "j-0001")
    url = job_url(ws, "j-0001") + "/cancel"
    first = _cancel(client, url, "cancel-key-replay", '"1"')
    second = _cancel(client, url, "cancel-key-replay", '"1"')
    assert first.status_code == 200 and second.status_code == 200
    assert first.content == second.content
    assert first.headers["ETag"] == second.headers["ETag"]
    assert first.headers["X-Request-Id"] != second.headers["X-Request-Id"]
    assert harness.count_rows("idempotency", "WHERE operation = 'cancelJob'") == 1
    after = client.get(job_url(ws, "j-0001")).json()
    assert after["state"] == "CANCELLED" and after["revision"] == 2


def test_cancel_job_same_key_different_request_is_409(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_job(ws, "j-0001")
    url = job_url(ws, "j-0001") + "/cancel"
    ok = _cancel(client, url, "cancel-key-conflict", '"1"')
    assert ok.status_code == 200
    assert_problem(_cancel(client, url, "cancel-key-conflict", '"2"'), 409, "IDEMPOTENCY_CONFLICT")


# --------------------------------------------------------------------------- retryJob


def test_retry_job_202_accepts_new_queued_job(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_job(ws, "j-src01", state="FAILED")
    response = _cancel(client, job_url(ws, "j-src01") + "/retry", "retry-key-accept1", '"1"')
    assert response.status_code == 202, response.text
    body: dict[str, Any] = response.json()
    assert body["state"] == "QUEUED"
    assert body["attempt"] == 0
    assert body["retry_of"] == "j-src01"
    assert body["revision"] == 1
    assert response.headers["ETag"] == '"1"'
    assert response.headers["Location"] == f"{API_PREFIX}/workspaces/{ws}/jobs/{body['id']}"
    source = client.get(job_url(ws, "j-src01")).json()
    # store T9（``enqueue_retry``）对源行做终态守卫更新，「每次写 +1」使源 revision 1→2；
    # 终态本身（FAILED）一字不变，这是 ``worker/store.py`` 冻结语义，见 design §2 jobs 行口径。
    assert source["state"] == "FAILED" and source["revision"] == 2


def test_retry_job_replay_matches_fresh_bytes(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_job(ws, "j-src02", state="FAILED")
    url = job_url(ws, "j-src02") + "/retry"
    first = _cancel(client, url, "retry-key-replay1", '"1"')
    second = _cancel(client, url, "retry-key-replay1", '"1"')
    assert first.status_code == 202 and second.status_code == 202
    assert first.content == second.content
    assert first.headers["ETag"] == second.headers["ETag"]
    assert first.headers["Location"] == second.headers["Location"]
    assert first.headers["X-Request-Id"] != second.headers["X-Request-Id"]
    assert harness.count_rows("jobs") == 2


def test_retry_job_state_conflict_is_409(client: TestClient, ws: str, harness: Harness) -> None:
    harness.seed_job(ws, "j-src03")
    assert_problem(
        _cancel(client, job_url(ws, "j-src03") + "/retry", "retry-key-409aa1", '"1"'),
        409,
        "STATE_CONFLICT",
    )


def test_retry_job_missing_if_match_is_428(client: TestClient, ws: str, harness: Harness) -> None:
    harness.seed_job(ws, "j-src04", state="FAILED")
    assert_problem(
        _cancel(client, job_url(ws, "j-src04") + "/retry", "retry-key-428aa1"),
        428,
        "PRECONDITION_REQUIRED",
    )


def test_retry_job_capacity_is_429_with_retry_after(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_job(ws, "j-src05", state="FAILED")
    for index in range(10):
        harness.seed_job(ws, f"j-p{index:03d}", at=T0 + timedelta(seconds=index + 1))
    response = _cancel(client, job_url(ws, "j-src05") + "/retry", "retry-key-429aa1", '"1"')
    body = assert_problem(response, 429, "JOB_CAPACITY")
    assert response.headers["Retry-After"] == "3"
    assert body["code"] == "JOB_CAPACITY"
    assert harness.count_rows("jobs") == 11


# ------------------------------------------------------------------ N7③ / D-019


def test_job_interrupted_lives_only_in_issues(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_interrupted_job(ws, "j-int01")
    response = client.get(job_url(ws, "j-int01"))
    assert response.status_code == 200
    problem: dict[str, Any] = response.json()["problem"]
    assert problem["code"] == "INTERNAL_ERROR"
    assert problem["status"] == 500
    assert problem["issues"][0]["code"] == "JOB_INTERRUPTED"
    assert "JOB_INTERRUPTED" not in PROBLEM_CODES


def test_jobs_error_codes_are_authoritative_20_codes_only(
    client: TestClient, ws: str, harness: Harness
) -> None:
    harness.seed_job(ws, "j-auth01")
    harness.seed_workspace("ws-auth")
    probes = [
        client.get(jobs_url("ws-ghost")),
        client.get(job_url(ws, "j-ghost")),
        client.get(jobs_url(ws), params={"cursor": "broken.cursor"}),
        client.get(jobs_url(ws), params={"limit": 999}),
        _cancel(client, job_url(ws, "j-auth01") + "/cancel", "cancel-key-author1"),
        _cancel(client, job_url(ws, "j-auth01") + "/cancel", "cancel-key-author2", '"77"'),
        _cancel(client, job_url(ws, "j-auth01") + "/cancel", "k", '"1"'),
    ]
    for response in probes:
        body: dict[str, Any] = response.json()
        assert body["code"] in PROBLEM_CODES, body
