"""M2-01/S6 ``tests/api/activities`` 端到端守护的公共装配（design §11.7，写集＝只新建 7 件）。

装配体例照 ``tests/api/conftest.py::Harness``（design §11.7 原文）：本目录的 ``harness`` fixture
与上层同名，会**遮蔽**父目录 fixture ⇒ 既有 S3 用例（``test_activities_router_s3.py`` 依赖
``harness.mint_token()`` 等面）必须继续可用，故 ``Harness`` 采取**继承扩展**而非平行重写；
新增成员一律 ``s6_`` 前缀，避免与父类方法签名冲突（mypy Liskov）。注入位仍逐条满足
「``create_app()`` 的注入位**显式给齐**、不注入就不装配」（A69）；库从活契约
``contracts/sqlite-v1.sql`` 原样建立；时间一律 ``FixedClock`` 显式时钟。S6 服务侧时钟带
``step=1s``，使 ``created_at`` / ``confirmed_at`` 逐调用严格递增（FU-54 ① 的「顺序确认 A→B」
行为钉桩依赖它）；S6 会话侧时钟固定于 T0，会话有效期与用例步进无关。

``artifacts`` / ``evidence`` 两行按 design §3.4 末条用**纯 SQL** 播种（本卡不实现 evidence
写入面，**禁** import ``api/evidence.py``）。状态码集合的唯一权威是路由装饰器的
``declared_responses()``（A95）：本目录不复制任何一份状态码清单，切片 ``M2-01.slice.json``
只用于「实现声明 == 切片声明」的对撞。

⚠ 本文件与既有 ``tests/api/conftest.py`` 同 basename ⇒ 落盘后必须跑一次**全树** mypy
（V15，LANE-COMMON §3.6 ``rule_full_tree_mypy_on_basename_collision``）。
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

import httpx
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from campaignlab.api import activities as activities_api
from campaignlab.api import rules as rules_api
from campaignlab.api.app import create_app
from campaignlab.api.common import OriginHostGuard, Workspace
from campaignlab.application.activity_service import ActivityService, RuleService
from campaignlab.application.audit import AuditWriter
from campaignlab.application.idempotency import IdempotencyGuard
from campaignlab.clock import FixedClock
from campaignlab.config import API_PREFIX, AppIdentity
from campaignlab.infra.db.engine import connect
from campaignlab.infra.db.repositories import WorkspaceRepository
from tests.api.conftest import Harness as _SharedHarness

REPO: Final = Path(__file__).resolve().parents[3]
SLICE: Final[dict[str, Any]] = json.loads(
    (REPO / "orchestrator" / "handoff" / "M2-01.slice.json").read_text(encoding="utf-8")
)
LIVE_CONTRACT: Final[dict[str, Any]] = json.loads(
    (REPO / "contracts" / "openapi.json").read_text(encoding="utf-8")
)
DDL: Final = REPO / "contracts" / "sqlite-v1.sql"

#: 合成基准时刻（与父目录体例一致：全仓禁「当前时间」字面量调用）。
T0: Final = datetime(2026, 11, 16, 1, 0, 0, tzinfo=UTC)
#: S6 服务侧时钟步进：保证 ``created_at`` / ``confirmed_at`` 逐调用严格递增。
CLOCK_STEP: Final = timedelta(seconds=1)
TOKEN_TTL: Final = 60
SESSION_TTL: Final = 3600
#: ``TestClient`` 默认 Host 是 ``testserver``，unsafe 请求必须显式带白名单 Origin。
GUARD: Final = OriginHostGuard(frozenset({"testserver"}), frozenset({"http://testserver"}))
TEST_ORIGIN: Final = "http://testserver"
#: 注入固定游标密钥：测试可复现、不落 ``state/cursor.key``（体例照 ``test_s2b_activity_service``）。
CURSOR_SECRET: Final = b"0" * 32
DIGEST64: Final = "a" * 64

IDENTITY: Final = AppIdentity(
    actor_id="tester",
    actor_name="tester",
    allowed_roles=("OPERATOR", "DESIGNER", "DATA_OWNER", "ANALYST", "TESTER", "REVIEWER"),
)
STRANGER: Final = AppIdentity(
    actor_id="intruder", actor_name="intruder", allowed_roles=("ANALYST",)
)

WS_ID: Final = "ws-s6-main"
WS_OTHER: Final = "ws-s6-other"

#: 条款键全集（G1–G6，真值来源＝领域门禁；与 ``test_s2b_activity_service.TERM_KEYS`` 同源）。
TERM_KEYS: Final = (
    "new_customer",
    "payment",
    "time_window",
    "stacking",
    "budget_and_quota",
    "refund",
)
#: fixture 逐字样本（``api-examples.json`` 口径）：``AC-101`` 是 ``external_activity_id``，
#: 不是本地 ``id``（design §7.5 / §9 AC-002）。
COUPON_JSON: Final[dict[str, Any]] = {
    "schema_version": 1,
    "template": "coupon_threshold",
    "currency": "CNY",
    "zone": "Asia/Shanghai",
    "starts_at": "2026-01-01T00:00:00Z",
    "ends_at": "2026-12-31T00:00:00Z",
    "new_customer_days": 30,
    "min_payment_fen": 10000,
    "coupon_fen": 1000,
    "max_per_customer": 1,
    "budget_fen": 1000000,
    "stacking": "DENY_OTHER_APPLIED",
    "refund_policy": "RECOMPUTE_UNUSED",
}
CALLBACK_JSON: Final[dict[str, Any]] = {
    "schema_version": 1,
    "template": "callback_priority",
    "zone": "Asia/Shanghai",
    "channel": "remote",
    "priority": "ARRIVAL",
    "daily_cap": 5,
}


def idem_key() -> str:
    """全新幂等键（8–128 字符，契约 ``minLength=8``）。"""
    return f"idem-s6-{uuid.uuid4().hex}"


def term_json(key: str, *, evidence_id: str = "ev-1") -> dict[str, Any]:
    return {
        "key": key,
        "clause": "条款原文（fixture）",
        "decision": "同意",
        "status": "CONFIRMED",
        "evidence_id": evidence_id,
    }


def default_terms(*, evidence_id: str = "ev-1") -> list[dict[str, Any]]:
    """六键齐全且各带已登记证据 ⇒ 确认门禁可过的条款集（``ev-1`` 须先播种）。"""
    return [term_json(key, evidence_id=evidence_id) for key in TERM_KEYS]


def binding_json(
    strategy_id: str,
    valid_from: str,
    valid_until: str,
    *,
    evidence_id: str = "ev-1",
    source_version: str = "S-1@1",
) -> dict[str, Any]:
    """``Binding`` 5 字段全必填、无 ``id``（design §3.4）。"""
    return {
        "strategy_id": strategy_id,
        "source_version": source_version,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "evidence_id": evidence_id,
    }


def m2_routes() -> dict[str, APIRoute]:
    """activities＋rules 两模块全部 ``APIRoute`` 的 ``operationId → 路由`` 映射（分母实取）。"""
    routes: dict[str, APIRoute] = {}
    for module in (activities_api, rules_api):
        for entry in module.router.routes:
            if isinstance(entry, APIRoute) and entry.operation_id:
                routes[entry.operation_id] = entry
    return routes


class Harness(_SharedHarness):
    """在 ``tests.api.conftest.Harness`` 之上叠加两个真实 service 与两个活工作区。

    继承（而非平行重写）的理由：本目录 ``harness`` fixture 遮蔽父目录同名 fixture，
    S3 既有用例依赖父类的 ``mint_token``／``clock``／``session_service``／``config`` 面
    （**预期红清单＝空集** 是本棒硬约束，派单文 §2）。S6 侧新增成员一律 ``s6_`` 前缀。
    """

    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path)
        self.s6_clock = FixedClock(T0, step=CLOCK_STEP)
        self.s6_app_clock = FixedClock(T0)
        self.activity_service = ActivityService(
            engine=self.engine,
            clock=self.s6_clock,
            config=self.config,
            idempotency=IdempotencyGuard(),
            audit=AuditWriter(),
            cursor_secret=CURSOR_SECRET,
        )
        self.rule_service = self.make_rule_service()
        with connect(self.engine) as conn, conn.begin():
            for workspace_id, name in ((WS_ID, "S6 主场馆"), (WS_OTHER, "S6 客场馆")):
                WorkspaceRepository().insert(
                    conn,
                    workspace=Workspace(
                        id=workspace_id,
                        revision=1,
                        created_at=T0,
                        name=name,
                        source_class="SYNTHETIC",
                        authorization_note=None,
                    ),
                )

    def make_rule_service(self, *, clock: FixedClock | None = None) -> RuleService:
        """独立 ``RuleService``：tie 用例注入 step=0 固定时钟以制造真实 ``confirmed_at`` 并列。"""
        return RuleService(
            engine=self.engine,
            clock=clock if clock is not None else self.s6_clock,
            config=self.config,
            idempotency=IdempotencyGuard(),
            audit=AuditWriter(),
            cursor_secret=CURSOR_SECRET,
        )

    def s6_app(
        self,
        *,
        activity_service: ActivityService | None = None,
        rule_service: RuleService | None = None,
    ) -> FastAPI:
        return create_app(
            self.config,
            clock=self.s6_app_clock,
            guard=GUARD,
            session_service=self.session_service,
            activity_service=(
                activity_service if activity_service is not None else self.activity_service
            ),
            rule_service=rule_service if rule_service is not None else self.rule_service,
        )

    def s6_client(
        self,
        identity: AppIdentity = IDENTITY,
        *,
        activity_service: ActivityService | None = None,
        rule_service: RuleService | None = None,
    ) -> TestClient:
        client = TestClient(
            self.s6_app(activity_service=activity_service, rule_service=rule_service),
            headers={"Origin": TEST_ORIGIN},
        )
        token = self.session_service.tokens.mint(identity, T0)
        response = client.post(f"{API_PREFIX}/session/exchange", json={"token": token})
        assert response.status_code == 200, response.text
        return client

    def audit_rows(self, *, outcome: str | None = None) -> list[tuple[str, str, str]]:
        """``(action, target_kind, outcome)`` 三元组清单（§7.3 审计留痕判据面）。"""
        sql = "SELECT action, target_kind, outcome FROM audit"
        params: tuple[Any, ...] = ()
        if outcome is not None:
            sql += " WHERE outcome = ?"
            params = (outcome,)
        raw = sqlite3.connect(self.db_path)
        try:
            return [(str(a), str(k), str(o)) for a, k, o in raw.execute(sql, params)]
        finally:
            raw.close()


def seed_evidence(engine: Engine, workspace_id: str, *, artifact_id: str, evidence_id: str) -> None:
    """只播种 ``artifacts``＋``evidence`` 两行（design §3.4：FK 要求两表同插）。"""
    with connect(engine) as conn, conn.begin():
        conn.exec_driver_sql(
            "INSERT INTO artifacts (workspace_id, id, kind, sha256, relative_path, "
            "byte_size, created_at) VALUES (?, ?, 'CLAUSE', ?, ?, 10, ?)",
            (workspace_id, artifact_id, DIGEST64, f"ev/{artifact_id}.txt", T0.isoformat()),
        )
        conn.exec_driver_sql(
            "INSERT INTO evidence (workspace_id, id, kind, source_id, locator, label, "
            "content_digest, artifact_id, created_at, source_class) "
            "VALUES (?, ?, 'CLAUSE', 'S-1', 'loc', 'lbl', ?, ?, ?, 'SYNTHETIC')",
            (workspace_id, evidence_id, DIGEST64, artifact_id, T0.isoformat()),
        )


def seed_activity(
    engine: Engine,
    workspace_id: str,
    activity_id: str,
    *,
    name: str = "播种活动",
    bank_id: str | None = None,
    external_activity_id: str | None = None,
    description: str = "",
    status: str = "OPEN",
    revision: int = 1,
) -> None:
    """SQL 播种一行 ``activities``（跨工作区用例需要确定性 ID）。"""
    with connect(engine) as conn, conn.begin():
        conn.exec_driver_sql(
            "INSERT INTO activities (workspace_id, id, name, bank_id, "
            "external_activity_id, description, status, current_rule_id, revision, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)",
            (
                workspace_id,
                activity_id,
                name,
                bank_id,
                external_activity_id,
                description,
                status,
                revision,
                T0.isoformat(),
            ),
        )


def create_activity_json(
    client: TestClient,
    workspace_id: str,
    *,
    name: str = "双十一",
    bank_id: str | None = "B-1",
    external_activity_id: str | None = "AC-101",
    description: str = "",
    key: str | None = None,
) -> httpx.Response:
    response: httpx.Response = client.post(
        f"{API_PREFIX}/workspaces/{workspace_id}/activities",
        json={
            "name": name,
            "bank_id": bank_id,
            "external_activity_id": external_activity_id,
            "description": description,
        },
        headers={"Idempotency-Key": key if key is not None else idem_key()},
    )
    return response


def create_rule_json(
    client: TestClient,
    workspace_id: str,
    activity_id: str,
    *,
    label: str = "v1",
    content: dict[str, Any] | None = None,
    terms: list[dict[str, Any]] | None = None,
    source_rule_version: str | None = None,
    parent_rule_id: str | None = None,
    key: str | None = None,
) -> httpx.Response:
    response: httpx.Response = client.post(
        f"{API_PREFIX}/workspaces/{workspace_id}/activities/{activity_id}/rules",
        json={
            "label": label,
            "content": content if content is not None else dict(COUPON_JSON),
            "terms": default_terms() if terms is None else terms,
            "source_rule_version": source_rule_version,
            "parent_rule_id": parent_rule_id,
        },
        headers={"Idempotency-Key": key if key is not None else idem_key()},
    )
    return response


@pytest.fixture
def harness(tmp_path: Path) -> Harness:
    return Harness(tmp_path)


@pytest.fixture
def authed_client(harness: Harness) -> TestClient:
    return harness.s6_client()
