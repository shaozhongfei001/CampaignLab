"""S2b-1：``ActivityService`` / ``RuleService`` 的用例级守护（design §6 / §7 的机器可查面）。

钉住七件事（判定顺序一律照 design §6.3，事务边界照 §7.1，审计照 §7.3）：

1. **同事务**：业务写入与 ``audit`` / ``idempotency`` 同事务落库；被拒的写不留半成品，
   但**业务性拒绝**要在回滚之后追加一行 ``DENIED``（协议性拒绝不写）；
2. **幂等**：同键同摘要回放原信封（同一 ETag），同键异摘要 409 ``IDEMPOTENCY_CONFLICT``；
3. **并发控制**：缺 ``If-Match`` → 428、不符 → 412、空 PATCH → 422 ``EMPTY_PATCH``；
   每次被接受的 ``updateActivity`` 都 bump ``revision``（含只改 ``bindings`` 的那一次）；
4. **绑定**：出现即整体替换（design §3.4），空区间／重复键／相交 → 422，
   ``evidence_id`` 未登记 → 422 ``EVIDENCE_REQUIRED``；
5. **状态机**：归档后写一律 409 ``STATE_CONFLICT``，读仍然 200；已确认版本不可改、不可重复确认；
6. **游标复用**：``BAD_CURSOR`` 的 detail 与 ``workspace_service`` **同一句**（派单文 §6③），
   游标绑定 actor 与查询条件；
7. **可注入**：两个构造签名与 ``WorkspaceService`` 同形，各 repository 都能从外面塞进来。

库用活契约 ``contracts/sqlite-v1.sql`` 建（只读）；``evidence`` / ``artifacts`` 两行按
design §3.4 末条用 SQL 直接播种（本卡不实现 evidence 写面）。
"""

from __future__ import annotations

import inspect
import json
import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, Engine

import campaignlab.application.workspace_service as workspace_service
from campaignlab.api.common import (
    ActivityCreate,
    ActivityUpdate,
    Binding,
    Confirmation,
    CouponRule,
    RuleCreate,
    RuleUpdate,
    Session,
    Term,
    Workspace,
    etag,
)
from campaignlab.application.activity_service import (
    ARCHIVED_DETAIL,
    DIGEST_MISMATCH_DETAIL,
    DUPLICATE_EXTERNAL_DETAIL,
    EMPTY_PATCH_DETAIL,
    IMMUTABLE_DETAIL,
    ActivityCreateOutcome,
    ActivityService,
    ActivityWriteOutcome,
    RuleService,
    RuleWriteOutcome,
)
from campaignlab.application.audit import AuditWriter
from campaignlab.application.idempotency import IdempotencyGuard
from campaignlab.clock import Clock, FixedClock
from campaignlab.config import AppConfig, load_config
from campaignlab.domain.errors import DomainError, IdempotencyConflict, ValidationFailure
from campaignlab.infra.db.engine import connect, make_engine
from campaignlab.infra.db.repositories import (
    ActivityBindingRepository,
    ActivityRecord,
    ActivityRepository,
    RuleVersionRecord,
    RuleVersionRepository,
    WorkspaceRepository,
)

REPO = Path(__file__).resolve().parents[2]
DDL = REPO / "contracts" / "sqlite-v1.sql"
T0 = datetime(2026, 11, 15, 1, 0, 0, tzinfo=UTC)
WS = "ws-s2b-svc"
OTHER_WS = "ws-other"
DIGEST64 = "a" * 64
ACTOR = Session(
    actor_id="tester",
    actor_name="tester",
    allowed_roles=["OPERATOR", "DESIGNER", "DATA_OWNER", "ANALYST", "TESTER", "REVIEWER"],
)
STRANGER = Session(actor_id="intruder", actor_name="intruder", allowed_roles=["ANALYST"])
COUPON_FIELDS: dict[str, Any] = {
    "schema_version": 1,
    "template": "coupon_threshold",
    "currency": "CNY",
    "zone": "Asia/Shanghai",
    "starts_at": T0,
    "ends_at": T0 + timedelta(days=10),
    "new_customer_days": 30,
    "min_payment_fen": 10000,
    "coupon_fen": 1000,
    "max_per_customer": 1,
    "budget_fen": 1000000,
    "stacking": "DENY_OTHER_APPLIED",
    "refund_policy": "RECOMPUTE_UNUSED",
}
TERM_KEYS = (
    "new_customer",
    "payment",
    "time_window",
    "stacking",
    "budget_and_quota",
    "refund",
)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    assert DDL.is_file(), f"活契约 DDL 读不到：{DDL}"
    db = tmp_path / "campaignlab.db"
    raw = sqlite3.connect(db)
    try:
        raw.executescript(DDL.read_text(encoding="utf-8"))
        raw.commit()
    finally:
        raw.close()
    return make_engine(f"sqlite:///{db}")


@pytest.fixture
def config(tmp_path: Path) -> AppConfig:
    return load_config(environ={"CAMPAIGNLAB_DATA_DIR": str(tmp_path)}, home=tmp_path)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(T0)


def _seed(engine: Engine) -> None:
    """工作区 ＋ ``artifacts``/``evidence`` 各一行（绑定与条款门禁的 FK 前置）。"""
    with connect(engine) as conn, conn.begin():
        for workspace_id, name in ((WS, "S2b 用例区"), (OTHER_WS, "别的区")):
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
        conn.exec_driver_sql(
            "INSERT INTO artifacts (workspace_id, id, kind, sha256, relative_path, byte_size, "
            "created_at) VALUES (?, 'art-1', 'CLAUSE', ?, 'ev/s2b.txt', 10, ?)",
            (WS, DIGEST64, T0.isoformat()),
        )
        conn.exec_driver_sql(
            "INSERT INTO evidence (workspace_id, id, kind, source_id, locator, label, "
            "content_digest, artifact_id, created_at, source_class) "
            "VALUES (?, 'ev-1', 'CLAUSE', 'S-1', 'loc', 'lbl', ?, 'art-1', ?, 'SYNTHETIC')",
            (WS, DIGEST64, T0.isoformat()),
        )


def _services(
    config: AppConfig, engine: Engine, clock: Clock, **overrides: Any
) -> tuple[ActivityService, RuleService]:
    shared: dict[str, Any] = {
        "engine": engine,
        "clock": clock,
        "config": config,
        "idempotency": IdempotencyGuard(),
        "audit": AuditWriter(),
        "cursor_secret": b"0" * 32,  # 注入固定密钥：测试可复现，不落 state/cursor.key
    }
    shared.update(overrides)
    activity_ports = {name: value for name, value in shared.items() if name != "rules"}
    return ActivityService(**activity_ports), RuleService(**shared)


def _coupon(**changes: Any) -> CouponRule:
    return CouponRule.model_validate({**COUPON_FIELDS, **changes})


def _terms() -> list[Term]:
    return [
        Term(key=key, clause="c", decision="ok", status="CONFIRMED", evidence_id="ev-1")
        for key in TERM_KEYS
    ]


def _create(
    service: ActivityService,
    name: str = "双十一",
    *,
    key: str = "key-s2b-create",
    bank_id: str | None = "B-1",
    external: str | None = "AC-101",
    body: bytes | None = None,
    request_id: str = "req-create",
    workspace_id: str = WS,
) -> ActivityCreateOutcome:
    payload = ActivityCreate(
        name=name, bank_id=bank_id, external_activity_id=external, description=""
    )
    raw = body if body is not None else payload.model_dump_json().encode("utf-8")
    return service.create_activity(
        workspace_id=workspace_id,
        payload=payload,
        body=raw,
        idempotency_key=key,
        actor=ACTOR,
        request_id=request_id,
    )


def _patch(
    service: ActivityService,
    activity_id: str,
    payload: ActivityUpdate,
    *,
    key: str,
    if_match: str | None,
    request_id: str = "req-patch",
    workspace_id: str = WS,
) -> ActivityWriteOutcome:
    return service.update_activity(
        workspace_id=workspace_id,
        activity_id=activity_id,
        payload=payload,
        body=payload.model_dump_json(exclude_unset=True).encode("utf-8"),
        idempotency_key=key,
        if_match=if_match,
        actor=ACTOR,
        request_id=request_id,
    )


def _create_rule(
    service: RuleService,
    activity_id: str,
    *,
    label: str = "v1",
    key: str = "key-s2b-rule",
    content: CouponRule | None = None,
    parent_rule_id: str | None = None,
    source_rule_version: str | None = None,
    request_id: str = "req-rule",
    workspace_id: str = WS,
) -> RuleWriteOutcome:
    payload = RuleCreate(
        label=label,
        content=content or _coupon(),
        terms=_terms(),
        source_rule_version=source_rule_version,
        parent_rule_id=parent_rule_id,
    )
    return service.create_rule(
        workspace_id=workspace_id,
        activity_id=activity_id,
        payload=payload,
        body=payload.model_dump_json().encode("utf-8"),
        idempotency_key=key,
        actor=ACTOR,
        request_id=request_id,
    )


def _audit(engine: Engine) -> list[tuple[Any, ...]]:
    with connect(engine) as conn:
        rows = conn.exec_driver_sql(
            "SELECT sequence, action, target_kind, target_id, outcome, request_id, role, "
            "workspace_id, previous_digest FROM audit ORDER BY sequence"
        )
        return [tuple(row) for row in rows]


def _idempotency(engine: Engine) -> list[tuple[Any, ...]]:
    with connect(engine) as conn:
        rows = conn.exec_driver_sql(
            "SELECT scope_key, actor_id, operation, idem_key, response_status FROM idempotency "
            "ORDER BY operation, idem_key"
        )
        return [tuple(row) for row in rows]


def _binding(
    strategy_id: str, valid_from: str, valid_until: str, evidence_id: str = "ev-1"
) -> Binding:
    return Binding(
        strategy_id=strategy_id,
        source_version="v1",
        valid_from=date.fromisoformat(valid_from),
        valid_until=date.fromisoformat(valid_until),
        evidence_id=evidence_id,
    )


def test_create_activity_lands_audit_and_idempotency_in_one_transaction(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """TX-A1：``activities`` ＋ ``audit`` ＋ ``idempotency`` 同事务；新建活动必然零绑定。"""
    _seed(engine)
    service, _ = _services(config, engine, clock)
    outcome = _create(service)
    assert isinstance(outcome, ActivityCreateOutcome)
    assert outcome.status == 201 and outcome.replayed is False
    assert outcome.headers == {"ETag": '"1"'}
    body = outcome.body
    assert body["revision"] == 1 and body["status"] == "OPEN"
    assert str(body["id"]).startswith("act-")
    # AC-202：``ActivityCreate`` 没有 bindings 字段 ⇒ 三个数组一律是 []，不是 null、不是缺字段
    assert body["bindings"] == [] and body["rule_ids"] == [] and body["receipt_ids"] == []
    assert body["created_at"] == T0.isoformat().replace("+00:00", "Z")
    assert outcome.as_envelope()["status"] == 201
    audit = _audit(engine)
    assert len(audit) == 1
    sequence, action, target_kind, target_id, outcome_name, request_id, role, ws, previous = audit[
        0
    ]
    assert (sequence, action, target_kind, outcome_name, request_id, role, ws, previous) == (
        1,
        "ACTIVITY_CREATED",
        "activity",
        "ACCEPTED",
        "req-create",
        "OPERATOR",
        WS,
        None,
    )
    assert target_id == body["id"]
    assert _idempotency(engine) == [(WS, "tester", "createActivity", "key-s2b-create", 201)]


def test_create_activity_replays_the_same_envelope_and_conflicts_on_another_body(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """同键同摘要 → 回放原信封；同键异摘要 → 409 ``IDEMPOTENCY_CONFLICT``。"""
    _seed(engine)
    service, _ = _services(config, engine, clock)
    first = _create(service)
    replay = _create(service, key="key-s2b-create", request_id="req-again")
    assert replay.replayed is True
    assert replay.status == first.status and replay.headers == first.headers
    assert replay.body == first.body
    other_body = json.dumps(
        {"name": "618", "bank_id": "B-2", "external_activity_id": "AC-618", "description": ""}
    ).encode("utf-8")
    with pytest.raises(IdempotencyConflict) as info:
        _create(service, key="key-s2b-create", body=other_body)
    assert info.value.status == 409 and info.value.code == "IDEMPOTENCY_CONFLICT"
    # 回放与冲突都不追加审计／幂等行
    assert len(_audit(engine)) == 1
    assert len(_idempotency(engine)) == 1


def test_duplicate_external_activity_id_is_located_with_two_issues(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """design §6.4：409 ＋ 两条 ``issues``，第二条带上**既有活动 ID**（AC-002「明确定位」）。"""
    _seed(engine)
    service, _ = _services(config, engine, clock)
    first = _create(service)
    with pytest.raises(DomainError) as info:
        _create(service, name="复制品", key="key-s2b-dup", request_id="req-dup")
    problem = info.value
    assert problem.status == 409 and problem.code == "STATE_CONFLICT"
    assert problem.detail == DUPLICATE_EXTERNAL_DETAIL
    assert [issue.location for issue in problem.issues] == ["/bank_id", "/external_activity_id"]
    assert {issue.code for issue in problem.issues} == {"DUPLICATE_EXTERNAL_ACTIVITY"}
    assert str(first.body["id"]) in problem.issues[1].message
    # 换银行就不算冲突（UNIQUE 是 (workspace_id, bank_id, external_activity_id)）
    moved = _create(
        service, name="换银行", key="key-s2b-bank2", bank_id="B-2", request_id="req-bank2"
    )
    assert moved.status == 201
    # bank_id 为 NULL 时永不触发（SQLite 的 UNIQUE 里 NULL 互不相等）
    nulls = [
        _create(
            service,
            name=f"无银行 {index}",
            key=f"key-s2b-null{index}",
            bank_id=None,
            external="AC-101",
            request_id=f"req-null{index}",
        )
        for index in range(2)
    ]
    assert [item.status for item in nulls] == [201, 201]
    assert len(_audit(engine)) == 4  # 只有被接受的四次写入留痕，409 那次不留


def test_update_activity_gates_empty_patch_precondition_and_revision(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """design §6.3 的判定顺序：幂等 → ``If-Match``（428/412）→ 空 PATCH（422）→ 写。"""
    _seed(engine)
    service, _ = _services(config, engine, clock)
    activity_id = str(_create(service).body["id"])
    empty = ActivityUpdate.model_validate_json(b"{}")
    with pytest.raises(ValidationFailure) as blank:
        _patch(service, activity_id, empty, key="key-s2b-empty", if_match=etag(1))
    assert blank.value.status == 422 and blank.value.code == "VALIDATION_ERROR"
    assert blank.value.detail == EMPTY_PATCH_DETAIL
    assert blank.value.issues[0].code == "EMPTY_PATCH"
    assert blank.value.issues[0].location == "/"
    rename = ActivityUpdate(name="改名")
    with pytest.raises(DomainError) as missing:
        _patch(service, activity_id, rename, key="key-s2b-428", if_match=None)
    assert missing.value.status == 428 and missing.value.code == "PRECONDITION_REQUIRED"
    with pytest.raises(DomainError) as stale:
        _patch(service, activity_id, rename, key="key-s2b-412", if_match=etag(99))
    assert stale.value.status == 412 and stale.value.code == "REVISION_CONFLICT"
    # 协议性拒绝不写审计（design §7.3）
    assert [row[4] for row in _audit(engine)] == ["ACCEPTED"]
    accepted = _patch(service, activity_id, rename, key="key-s2b-ok", if_match=etag(1))
    assert accepted.status == 200 and accepted.replayed is False
    assert accepted.headers == {"ETag": '"2"'}
    assert accepted.body["name"] == "改名" and accepted.body["revision"] == 2
    # 显式给空串是合法的「清空」意图，不算空 PATCH（design §6.4）
    cleared = _patch(
        service,
        activity_id,
        ActivityUpdate(description=""),
        key="key-s2b-clear",
        if_match=etag(2),
    )
    assert cleared.status == 200 and cleared.body["revision"] == 3
    # 显式给 [] 也是合法意图：绑定清空且仍然 bump revision
    emptied = _patch(
        service,
        activity_id,
        ActivityUpdate(bindings=[]),
        key="key-s2b-nobind",
        if_match=etag(3),
    )
    assert emptied.status == 200 and emptied.body["revision"] == 4
    assert emptied.body["bindings"] == []


def test_bindings_patch_replaces_the_whole_set_and_gates_evidence(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """design §3.4：整体替换 ＋ 三类 422；只有 ``EVIDENCE_REQUIRED`` 追加 ``DENIED``。"""
    _seed(engine)
    service, _ = _services(config, engine, clock)
    activity_id = str(_create(service).body["id"])
    two = ActivityUpdate(
        bindings=[
            _binding("S-1", "2026-01-01", "2026-02-01"),
            _binding("S-2", "2026-03-01", "2026-04-01"),
        ]
    )
    written = _patch(service, activity_id, two, key="key-s2b-bind2", if_match=etag(1))
    assert written.status == 200
    assert [(item["strategy_id"], item["valid_from"]) for item in written.body["bindings"]] == [
        ("S-1", "2026-01-01"),
        ("S-2", "2026-03-01"),
    ]
    # 整体替换：给一条就只剩一条，不是 merge
    one = ActivityUpdate(bindings=[_binding("S-9", "2026-05-01", "2026-06-01")])
    replaced = _patch(service, activity_id, one, key="key-s2b-bind1", if_match=etag(2))
    assert [item["strategy_id"] for item in replaced.body["bindings"]] == ["S-9"]
    assert replaced.body["revision"] == 3
    # 空区间（起含止排）→ 422，行内容一字不动
    empty_interval = ActivityUpdate(bindings=[_binding("S-1", "2026-01-01", "2026-01-01")])
    with pytest.raises(DomainError) as interval:
        _patch(service, activity_id, empty_interval, key="key-s2b-int", if_match=etag(3))
    assert interval.value.status == 422 and interval.value.code == "VALIDATION_ERROR"
    assert interval.value.issues[0].code == "BINDING_EMPTY_INTERVAL"
    assert interval.value.issues[0].location == "/bindings/0/valid_until"
    # 重复键 → 422 BINDING_DUPLICATE_KEY（禁让 IntegrityError 冒成 500）
    duplicated = ActivityUpdate(
        bindings=[
            _binding("S-1", "2026-01-01", "2026-02-01"),
            _binding("S-1", "2026-01-01", "2026-03-01"),
        ]
    )
    with pytest.raises(DomainError) as duplicate:
        _patch(service, activity_id, duplicated, key="key-s2b-dup2", if_match=etag(3))
    assert duplicate.value.issues[0].code == "BINDING_DUPLICATE_KEY"
    # 同策略相交 → 422 BINDING_OVERLAP，两条 location 都给
    overlapped = ActivityUpdate(
        bindings=[
            _binding("S-1", "2026-01-01", "2026-03-01"),
            _binding("S-1", "2026-02-01", "2026-04-01"),
        ]
    )
    with pytest.raises(DomainError) as overlap:
        _patch(service, activity_id, overlapped, key="key-s2b-ovl", if_match=etag(3))
    assert overlap.value.issues[0].code == "BINDING_OVERLAP"
    assert [issue.location for issue in overlap.value.issues] == [
        "/bindings/0/valid_from",
        "/bindings/1/valid_from",
    ]
    # 未登记的 evidence_id → 422 EVIDENCE_REQUIRED（业务性拒绝，追加 DENIED）
    unregistered = ActivityUpdate(
        bindings=[_binding("S-1", "2026-01-01", "2026-02-01", evidence_id="ev-nope")]
    )
    with pytest.raises(DomainError) as evidence:
        _patch(service, activity_id, unregistered, key="key-s2b-evi", if_match=etag(3))
    assert evidence.value.status == 422 and evidence.value.code == "EVIDENCE_REQUIRED"
    assert evidence.value.issues[0].code == "BINDING_EVIDENCE_UNREGISTERED"
    assert evidence.value.issues[0].location == "/bindings/0/evidence_id"
    current = service.get_activity(workspace_id=WS, activity_id=activity_id)
    assert current.revision == 3  # 四次被拒的 PATCH 一次都没写进去
    assert [item.strategy_id for item in current.bindings] == ["S-9"]
    outcomes = [(row[1], row[4]) for row in _audit(engine)]
    assert outcomes == [
        ("ACTIVITY_CREATED", "ACCEPTED"),
        ("ACTIVITY_UPDATED", "ACCEPTED"),
        ("ACTIVITY_UPDATED", "ACCEPTED"),
        ("ACTIVITY_UPDATED", "DENIED"),
    ]


def test_archive_activity_blocks_writes_but_keeps_reads(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """A2 归档：写一律 409 ``STATE_CONFLICT`` ＋ ``DENIED`` 留痕，读仍然 200。"""
    _seed(engine)
    activities, rules = _services(config, engine, clock)
    activity_id = str(_create(activities).body["id"])
    draft = _create_rule(rules, activity_id)
    rule_id = str(draft.body["id"])
    archived = _patch(
        activities,
        activity_id,
        ActivityUpdate(status="ARCHIVED"),
        key="key-s2b-arch",
        if_match=etag(1),
    )
    assert archived.status == 200 and archived.body["status"] == "ARCHIVED"
    assert archived.headers == {"ETag": '"2"'}
    with pytest.raises(DomainError) as rename:
        _patch(
            activities,
            activity_id,
            ActivityUpdate(name="归档后改名"),
            key="key-s2b-arch2",
            if_match=etag(2),
        )
    assert rename.value.status == 409 and rename.value.code == "STATE_CONFLICT"
    assert rename.value.detail == ARCHIVED_DETAIL
    assert rename.value.issues[0].code == "ACTIVITY_ARCHIVED"
    with pytest.raises(DomainError) as new_rule:
        _create_rule(rules, activity_id, key="key-s2b-arch3", request_id="req-arch3")
    assert new_rule.value.status == 409 and new_rule.value.code == "STATE_CONFLICT"
    assert new_rule.value.issues[0].location == "/activity_id"
    with pytest.raises(DomainError) as edit_rule:
        rules.update_rule(
            workspace_id=WS,
            rule_id=rule_id,
            payload=RuleUpdate(label="归档后改标签"),
            body=b'{"label":"x"}',
            idempotency_key="key-s2b-arch4",
            if_match=etag(1),
            actor=ACTOR,
            request_id="req-arch4",
        )
    assert edit_rule.value.status == 409 and edit_rule.value.detail == ARCHIVED_DETAIL
    # 读面不受影响（design §6.3：归档活动仍可查、仍可看检查项）
    assert activities.get_activity(workspace_id=WS, activity_id=activity_id).status == "ARCHIVED"
    assert rules.get_rule(workspace_id=WS, rule_id=rule_id).state == "DRAFT"
    assert rules.check_rule(workspace_id=WS, rule_id=rule_id).rule_id == rule_id
    denied = [row for row in _audit(engine) if row[4] == "DENIED"]
    assert [(row[1], row[2]) for row in denied] == [
        ("ACTIVITY_UPDATED", "activity"),
        ("RULE_DRAFT_CREATED", "rule"),
        ("RULE_LABEL_UPDATED", "rule"),
    ]
    # 跨工作区一律 404，与「不存在」同一句 detail（禁枚举 oracle）
    with pytest.raises(DomainError) as foreign:
        activities.get_activity(workspace_id=OTHER_WS, activity_id=activity_id)
    assert foreign.value.status == 404 and foreign.value.code == "RESOURCE_NOT_FOUND"


def test_list_activities_pages_and_binds_the_cursor_to_actor_and_query(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """键集翻页 ＋ 游标绑定 actor/limit/q/status；``BAD_CURSOR`` 复用同一句 detail。"""
    _seed(engine)
    service, _ = _services(config, engine, clock)
    for index in range(3):
        clock.advance(timedelta(minutes=1))
        _create(
            service,
            name=f"活动 {index}",
            key=f"key-s2b-list{index}",
            bank_id=None,
            external=f"AC-{index}",
            request_id=f"req-list{index}",
        )
    page = service.list_activities(
        actor=ACTOR, workspace_id=WS, cursor=None, limit=2, q=None, status=None
    )
    assert [item.name for item in page.items] == ["活动 2", "活动 1"]
    assert page.next_cursor is not None and len(page.next_cursor) <= 300
    tail = service.list_activities(
        actor=ACTOR, workspace_id=WS, cursor=page.next_cursor, limit=2, q=None, status=None
    )
    assert [item.name for item in tail.items] == ["活动 0"]
    assert tail.next_cursor is None
    # q 命中 name 与 external_activity_id（NFKC ＋ casefold）
    by_name = service.list_activities(
        actor=ACTOR, workspace_id=WS, cursor=None, limit=25, q="活动 １", status=None
    )
    assert [item.name for item in by_name.items] == ["活动 1"]
    by_external = service.list_activities(
        actor=ACTOR, workspace_id=WS, cursor=None, limit=25, q="ac-2", status=None
    )
    assert [item.external_activity_id for item in by_external.items] == ["AC-2"]
    # status 白名单：单值、多值都合法；空 token 与未知态名 → 422 /query/status
    only_open = service.list_activities(
        actor=ACTOR, workspace_id=WS, cursor=None, limit=25, q=None, status="OPEN"
    )
    assert len(only_open.items) == 3
    both = service.list_activities(
        actor=ACTOR, workspace_id=WS, cursor=None, limit=25, q=None, status="OPEN,ARCHIVED"
    )
    assert len(both.items) == 3
    for bad in ("OPEN,", "NOPE", "open ,"):
        with pytest.raises(DomainError) as info:
            service.list_activities(
                actor=ACTOR, workspace_id=WS, cursor=None, limit=25, q=None, status=bad
            )
        assert info.value.status == 422 and info.value.code == "VALIDATION_ERROR", bad
        assert info.value.issues[0].location == "/query/status", bad
        assert info.value.issues[0].code == "STATUS_UNKNOWN", bad
    # 游标绑定 actor 与查询条件：三种错配同一句 detail（派单文 §6③ 的复用断言）
    details: set[str] = set()
    for kwargs in (
        {"actor": STRANGER},
        {"limit": 1},
        {"q": "活动"},
        {"status": "ARCHIVED"},
    ):
        with pytest.raises(DomainError) as info:
            parameters: dict[str, Any] = {
                "actor": ACTOR,
                "workspace_id": WS,
                "cursor": page.next_cursor,
                "limit": 2,
                "q": None,
                "status": None,
            }
            parameters.update(kwargs)
            service.list_activities(**parameters)
        assert info.value.status == 400 and info.value.code == "BAD_CURSOR"
        details.add(info.value.detail)
    assert details == {workspace_service.BAD_CURSOR_DETAIL}
    for bad_cursor in ("garbage", "a.b", ""):
        with pytest.raises(DomainError) as info:
            service.list_activities(
                actor=ACTOR, workspace_id=WS, cursor=bad_cursor, limit=25, q=None, status=None
            )
        assert info.value.status == 400 and info.value.code == "BAD_CURSOR"
        assert info.value.detail == workspace_service.BAD_CURSOR_DETAIL
    # 跨工作区不可见
    foreign = service.list_activities(
        actor=ACTOR, workspace_id=OTHER_WS, cursor=None, limit=25, q=None, status=None
    )
    assert foreign.items == [] and foreign.next_cursor is None


class _RecordingActivities(ActivityRepository):
    """只为验证「各 repository 可注入」：记下经手的 ``insert``。"""

    def __init__(self) -> None:
        self.inserts: list[ActivityRecord] = []

    def insert(self, conn: Connection, *, record: ActivityRecord) -> None:
        self.inserts.append(record)
        super().insert(conn, record=record)


class _RecordingRules(RuleVersionRepository):
    """同上，规则面。"""

    def __init__(self) -> None:
        self.inserts: list[RuleVersionRecord] = []

    def insert(self, conn: Connection, *, record: RuleVersionRecord) -> None:
        self.inserts.append(record)
        super().insert(conn, record=record)


def _init_parameters(cls: type) -> list[inspect.Parameter]:
    signature = inspect.signature(cls)
    return [parameter for name, parameter in signature.parameters.items() if name != "self"]


def test_service_constructors_are_isomorphic_with_workspace_service() -> None:
    """design §11.3：两个构造签名与 ``WorkspaceService`` **同形**，全部可注入。"""
    reference = {p.name: p for p in _init_parameters(workspace_service.WorkspaceService)}
    assert list(reference)[:3] == ["engine", "clock", "config"]
    assert list(reference)[-3:] == ["idempotency", "audit", "cursor_secret"]
    shapes = {
        ActivityService: ("activities", "bindings"),
        RuleService: ("activities", "rules", "bindings"),
    }
    for cls, repositories in shapes.items():
        parameters = _init_parameters(cls)
        names = [parameter.name for parameter in parameters]
        assert names[:3] == ["engine", "clock", "config"], names
        assert names[-3:] == ["idempotency", "audit", "cursor_secret"], names
        assert tuple(names[3:-3]) == repositories, names
        for parameter in parameters:
            assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, (cls.__name__, parameter.name)
            if parameter.name in {"engine", "clock", "config"}:
                assert parameter.default is inspect.Parameter.empty, parameter.name
            else:
                assert parameter.default is None, (cls.__name__, parameter.name)
        for name in ("engine", "clock", "config", "idempotency", "audit", "cursor_secret"):
            actual = dict((parameter.name, parameter) for parameter in parameters)[name]
            assert str(actual.annotation) == str(reference[name].annotation), (
                cls.__name__,
                name,
            )


def test_every_repository_port_is_injectable(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """塞进去的实例必须真的被用（不是「参数收了但另起一份默认实现」）。"""
    _seed(engine)
    recording_activities = _RecordingActivities()
    recording_rules = _RecordingRules()
    activities, rules = _services(
        config,
        engine,
        clock,
        activities=recording_activities,
        rules=recording_rules,
        bindings=ActivityBindingRepository(),
    )
    created = _create(activities)
    activity_id = str(created.body["id"])
    assert [record.id for record in recording_activities.inserts] == [activity_id]
    assert recording_activities.inserts[0].status == "OPEN"
    draft = _create_rule(rules, activity_id)
    assert [record.id for record in recording_rules.inserts] == [str(draft.body["id"])]
    assert recording_rules.inserts[0].activity_id == activity_id
    assert recording_rules.inserts[0].state == "DRAFT"


def test_rule_draft_updates_audit_label_and_content_separately(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """``DOMAIN.md``「标签和确认说明分别审计」：只改其一写一行，同时改写两行（§7.3）。"""
    _seed(engine)
    activities, rules = _services(config, engine, clock)
    activity_id = str(_create(activities).body["id"])
    draft = _create_rule(rules, activity_id)
    rule_id = str(draft.body["id"])
    assert draft.status == 201 and draft.headers == {"ETag": '"1"'}
    assert draft.body["state"] == "DRAFT" and draft.body["revision"] == 1
    assert draft.body["confirmed_at"] is None and draft.body["confirmation"] is None
    assert len(str(draft.body["digest"])) == 64
    # R1 不动活动的 revision，但活动视图立刻能看见这条规则
    assert activities.get_activity(workspace_id=WS, activity_id=activity_id).revision == 1
    assert activities.get_activity(workspace_id=WS, activity_id=activity_id).rule_ids == [rule_id]

    def _update(payload: RuleUpdate, key: str, revision: int) -> RuleWriteOutcome:
        return rules.update_rule(
            workspace_id=WS,
            rule_id=rule_id,
            payload=payload,
            body=payload.model_dump_json(exclude_unset=True).encode("utf-8"),
            idempotency_key=key,
            if_match=etag(revision),
            actor=ACTOR,
            request_id=f"req-{key}",
        )

    label_only = _update(RuleUpdate(label="v1-renamed"), "key-s2b-lbl", 1)
    assert label_only.status == 200 and label_only.headers == {"ETag": '"2"'}
    assert label_only.body["label"] == "v1-renamed" and label_only.body["revision"] == 2
    # label 不进摘要（design §4.6）
    assert label_only.body["digest"] == draft.body["digest"]
    content_only = _update(RuleUpdate(content=_coupon(coupon_fen=2000)), "key-s2b-cnt", 2)
    assert content_only.body["revision"] == 3
    assert content_only.body["digest"] != draft.body["digest"]
    assert content_only.body["content"]["coupon_fen"] == 2000
    both = _update(
        RuleUpdate(label="v1-final", content=_coupon(coupon_fen=3000)), "key-s2b-both", 3
    )
    assert both.body["revision"] == 4 and both.body["label"] == "v1-final"
    rule_rows = [(row[0], row[1], row[4]) for row in _audit(engine) if row[2] == "rule"]
    assert rule_rows == [
        (2, "RULE_DRAFT_CREATED", "ACCEPTED"),
        (3, "RULE_LABEL_UPDATED", "ACCEPTED"),
        (4, "RULE_CONTENT_UPDATED", "ACCEPTED"),
        (5, "RULE_LABEL_UPDATED", "ACCEPTED"),
        (6, "RULE_CONTENT_UPDATED", "ACCEPTED"),
    ]
    # 空 PATCH 与形状非法一律 422（design §6.4）
    with pytest.raises(ValidationFailure) as blank:
        _update(RuleUpdate.model_validate_json(b"{}"), "key-s2b-emptyrule", 4)
    assert blank.value.issues[0].code == "EMPTY_PATCH"
    with pytest.raises(DomainError) as missing:
        rules.update_rule(
            workspace_id=WS,
            rule_id=rule_id,
            payload=RuleUpdate(label="x"),
            body=b'{"label":"x"}',
            idempotency_key="key-s2b-428r",
            if_match=None,
            actor=ACTOR,
            request_id="req-428r",
        )
    assert missing.value.status == 428


def test_confirm_rule_bumps_both_etags_and_freezes_the_version(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """R3：确认同时钉死规则与活动的 ETag；确认后不可改、不可重复确认（AC-003）。"""
    _seed(engine)
    activities, rules = _services(config, engine, clock)
    activity_id = str(_create(activities).body["id"])
    rule_id = str(_create_rule(rules, activity_id).body["id"])
    stored = rules.get_rule(workspace_id=WS, rule_id=rule_id)
    drifted = Confirmation(note="已复核", digest="b" * 64)
    with pytest.raises(DomainError) as mismatch:
        rules.confirm_rule(
            workspace_id=WS,
            rule_id=rule_id,
            payload=drifted,
            body=drifted.model_dump_json().encode("utf-8"),
            idempotency_key="key-s2b-cfm1",
            if_match=etag(stored.revision),
            actor=ACTOR,
            request_id="req-cfm1",
        )
    assert mismatch.value.status == 409 and mismatch.value.code == "VERSION_MISMATCH"
    assert mismatch.value.detail == DIGEST_MISMATCH_DETAIL
    assert mismatch.value.issues[0].code == "CONFIRMATION_DIGEST_MISMATCH"
    assert mismatch.value.issues[0].location == "/digest"
    note = Confirmation(note="已复核", digest=stored.digest)
    confirmed = rules.confirm_rule(
        workspace_id=WS,
        rule_id=rule_id,
        payload=note,
        body=note.model_dump_json().encode("utf-8"),
        idempotency_key="key-s2b-cfm2",
        if_match=etag(stored.revision),
        actor=ACTOR,
        request_id="req-cfm2",
    )
    assert confirmed.status == 200 and confirmed.headers == {"ETag": '"2"'}
    assert confirmed.body["state"] == "CONFIRMED" and confirmed.body["revision"] == 2
    assert confirmed.body["confirmed_at"] == T0.isoformat().replace("+00:00", "Z")
    assert confirmed.body["confirmation"] == "已复核"
    # 同事务联动：活动指向它，且活动 ETag 也 bump（design §3.2 末条）
    activity = activities.get_activity(workspace_id=WS, activity_id=activity_id)
    assert activity.current_rule_id == rule_id and activity.revision == 2
    with pytest.raises(DomainError) as edit:
        rules.update_rule(
            workspace_id=WS,
            rule_id=rule_id,
            payload=RuleUpdate(label="确认后再改"),
            body=b'{"label":"x"}',
            idempotency_key="key-s2b-cfm3",
            if_match=etag(2),
            actor=ACTOR,
            request_id="req-cfm3",
        )
    assert edit.value.status == 409 and edit.value.code == "STATE_CONFLICT"
    assert edit.value.detail == IMMUTABLE_DETAIL
    assert edit.value.issues[0].code == "RULE_CONFIRMED_IMMUTABLE"
    with pytest.raises(DomainError) as twice:
        rules.confirm_rule(
            workspace_id=WS,
            rule_id=rule_id,
            payload=note,
            body=note.model_dump_json().encode("utf-8"),
            idempotency_key="key-s2b-cfm4",
            if_match=etag(2),
            actor=ACTOR,
            request_id="req-cfm4",
        )
    assert twice.value.status == 409 and twice.value.code == "STATE_CONFLICT"
    assert twice.value.issues[0].code == "RULE_ALREADY_CONFIRMED"
    frozen = rules.get_rule(workspace_id=WS, rule_id=rule_id)
    assert frozen.label == "v1" and frozen.revision == 2
    assert [(row[1], row[4]) for row in _audit(engine) if row[2] == "rule"] == [
        ("RULE_DRAFT_CREATED", "ACCEPTED"),
        ("RULE_CONFIRMED", "DENIED"),
        ("RULE_CONFIRMED", "ACCEPTED"),
        ("RULE_LABEL_UPDATED", "DENIED"),
        ("RULE_CONFIRMED", "DENIED"),
    ]


def test_successor_draft_requires_a_confirmed_parent(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """R4：以 ``CONFIRMED`` 版本为父新建草稿行，源行一字不改；父未确认 → 409。"""
    _seed(engine)
    activities, rules = _services(config, engine, clock)
    activity_id = str(_create(activities).body["id"])
    first_id = str(_create_rule(rules, activity_id).body["id"])
    with pytest.raises(DomainError) as draft_parent:
        _create_rule(
            rules,
            activity_id,
            label="v2",
            key="key-s2b-suc1",
            parent_rule_id=first_id,
            source_rule_version="S-1",
        )
    assert draft_parent.value.status == 409 and draft_parent.value.code == "STATE_CONFLICT"
    assert draft_parent.value.issues[0].code == "PARENT_NOT_CONFIRMED"
    assert draft_parent.value.issues[0].location == "/parent_rule_id"
    with pytest.raises(DomainError) as unknown_parent:
        _create_rule(
            rules,
            activity_id,
            label="v2",
            key="key-s2b-suc2",
            parent_rule_id="rul-doesnotexist0000000000000000000",
        )
    assert unknown_parent.value.status == 404
    stored = rules.get_rule(workspace_id=WS, rule_id=first_id)
    note = Confirmation(note="已复核", digest=stored.digest)
    rules.confirm_rule(
        workspace_id=WS,
        rule_id=first_id,
        payload=note,
        body=note.model_dump_json().encode("utf-8"),
        idempotency_key="key-s2b-suc3",
        if_match=etag(stored.revision),
        actor=ACTOR,
        request_id="req-suc3",
    )
    # 让两条规则的 ``created_at`` 真的分开：``rule_ids`` 的冻结序是 ``created_at ASC, id ASC``，
    # 同一时刻会退化成按随机 ID 排序（断言就会偶发红）。
    clock.advance(timedelta(minutes=1))
    successor = _create_rule(
        rules,
        activity_id,
        label="v2",
        key="key-s2b-suc4",
        parent_rule_id=first_id,
        source_rule_version="S-1",
    )
    assert successor.status == 201 and successor.body["state"] == "DRAFT"
    assert successor.body["revision"] == 1
    assert successor.body["parent_rule_id"] == first_id
    assert successor.body["source_rule_version"] == "S-1"
    second_id = str(successor.body["id"])
    assert second_id != first_id
    # 源行一字不改（仍是 CONFIRMED / revision 2）
    parent = rules.get_rule(workspace_id=WS, rule_id=first_id)
    assert parent.state == "CONFIRMED" and parent.revision == 2
    activity = activities.get_activity(workspace_id=WS, activity_id=activity_id)
    assert activity.current_rule_id == first_id
    assert activity.rule_ids == [first_id, second_id]
    assert [(row[1], row[4]) for row in _audit(engine) if row[2] == "rule"] == [
        ("RULE_DRAFT_CREATED", "ACCEPTED"),
        ("RULE_SUCCESSOR_DRAFT_CREATED", "DENIED"),
        ("RULE_CONFIRMED", "ACCEPTED"),
        ("RULE_SUCCESSOR_DRAFT_CREATED", "ACCEPTED"),
    ]


def test_compare_rules_reports_changes_and_required_reruns(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """design §6.5：字段级差异 ＋ ``requires_rerun_case_ids``；跨模板 → 422。"""
    _seed(engine)
    activities, rules = _services(config, engine, clock)
    activity_id = str(_create(activities).body["id"])
    baseline_id = str(_create_rule(rules, activity_id, label="v1").body["id"])
    candidate_id = str(
        _create_rule(
            rules,
            activity_id,
            label="v2",
            key="key-s2b-cmp1",
            source_rule_version="S-1",
            content=_coupon(coupon_fen=2000),
        ).body["id"]
    )
    diff = rules.compare_rules(workspace_id=WS, rule_id=baseline_id, candidate_rule_id=candidate_id)
    assert diff.baseline_rule_id == baseline_id and diff.candidate_rule_id == candidate_id
    paths = [change.path for change in diff.changes]
    assert "/label" in paths and "/source_rule_version" in paths
    assert "/content/coupon_fen" in paths
    labelled = next(change for change in diff.changes if change.path == "/label")
    assert labelled.before == "v1" and labelled.after == "v2"
    # ``cases`` 归 M2-02，整表为空 ⇒ 必须给出 []，禁假设「至少一行」
    assert diff.requires_rerun_case_ids == []
    # 自己比自己：无差异 ⇒ 也不需要重跑
    same = rules.compare_rules(workspace_id=WS, rule_id=baseline_id, candidate_rule_id=baseline_id)
    assert same.changes == [] and same.requires_rerun_case_ids == []
    # 跨模板不可比（RULES.md「候选同模板」）：直接播种一行 callback_priority
    with connect(engine) as conn, conn.begin():
        conn.exec_driver_sql(
            "INSERT INTO rule_versions (workspace_id, id, activity_id, parent_rule_id, label, "
            "template, source_rule_version, state, revision, content_json, terms_json, digest, "
            "created_at, confirmed_at, confirmation) VALUES (?, 'rul-cb', ?, NULL, 'cb', "
            "'callback_priority', NULL, 'DRAFT', 1, ?, '[]', ?, ?, NULL, NULL)",
            (
                WS,
                activity_id,
                json.dumps(
                    {
                        "schema_version": 1,
                        "template": "callback_priority",
                        "zone": "Asia/Shanghai",
                        "channel": "remote",
                        "priority": "ARRIVAL",
                        "daily_cap": 3,
                    },
                    sort_keys=True,
                ),
                "c" * 64,
                T0.isoformat(),
            ),
        )
    with pytest.raises(ValidationFailure) as crossed:
        rules.compare_rules(workspace_id=WS, rule_id=baseline_id, candidate_rule_id="rul-cb")
    assert crossed.value.status == 422 and crossed.value.code == "VALIDATION_ERROR"
    assert crossed.value.issues[0].code == "TEMPLATE_MISMATCH"
    assert crossed.value.issues[0].location == "/query/candidate_rule_id"
    # 跨工作区一律 404，同一句 detail
    with pytest.raises(DomainError) as foreign:
        rules.compare_rules(workspace_id=OTHER_WS, rule_id=baseline_id, candidate_rule_id="rul-cb")
    assert foreign.value.status == 404 and foreign.value.code == "RESOURCE_NOT_FOUND"


def test_check_rule_is_read_only_and_returns_the_stored_digest(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """design §5.2：``rule_digest`` 取库里那一列，**禁**在响应里重算出第二个值。"""
    _seed(engine)
    activities, rules = _services(config, engine, clock)
    activity_id = str(_create(activities).body["id"])
    rule_id = str(_create_rule(rules, activity_id).body["id"])
    before_audit = _audit(engine)
    stored = rules.get_rule(workspace_id=WS, rule_id=rule_id)
    check = rules.check_rule(workspace_id=WS, rule_id=rule_id)
    assert check.rule_id == rule_id
    assert check.rule_digest == stored.digest
    assert check.state == "READY"
    assert check.boundary_cases, "检查项必须给出反例数据（design §5.4）"
    for case in check.boundary_cases:
        assert case.id and case.label and case.verification
        assert case.input is not None
    # 去重键 (code, location)：同一事实只报一次
    markers = [(issue.code, issue.location) for issue in check.issues]
    assert len(markers) == len(set(markers))
    # 只读：不追加审计、不动 revision、可重复调用
    assert _audit(engine) == before_audit
    again = rules.check_rule(workspace_id=WS, rule_id=rule_id)
    assert again.rule_digest == check.rule_digest and again.state == check.state
    assert rules.get_rule(workspace_id=WS, rule_id=rule_id).revision == stored.revision
    with pytest.raises(DomainError) as missing:
        rules.check_rule(workspace_id=WS, rule_id="rul-doesnotexist0000000000000000000")
    assert missing.value.status == 404


def test_list_rules_pages_and_filters_by_state(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """``listRules`` 的键集翻页 ＋ ``status`` 过滤的是 ``state`` 列（ADR-006 §4.7 的错位）。"""
    _seed(engine)
    activities, rules = _services(config, engine, clock)
    activity_id = str(_create(activities).body["id"])
    ids: list[str] = []
    for index in range(3):
        clock.advance(timedelta(minutes=1))
        ids.append(
            str(
                _create_rule(rules, activity_id, label=f"v{index}", key=f"key-s2b-ls{index}").body[
                    "id"
                ]
            )
        )
    page = rules.list_rules(
        actor=ACTOR,
        workspace_id=WS,
        activity_id=activity_id,
        cursor=None,
        limit=2,
        q=None,
        status=None,
    )
    assert [item.label for item in page.items] == ["v2", "v1"]
    assert page.next_cursor is not None
    tail = rules.list_rules(
        actor=ACTOR,
        workspace_id=WS,
        activity_id=activity_id,
        cursor=page.next_cursor,
        limit=2,
        q=None,
        status=None,
    )
    assert [item.label for item in tail.items] == ["v0"] and tail.next_cursor is None
    by_label = rules.list_rules(
        actor=ACTOR,
        workspace_id=WS,
        activity_id=activity_id,
        cursor=None,
        limit=25,
        q="Ｖ１",
        status=None,
    )
    assert [item.id for item in by_label.items] == [ids[1]]
    drafts = rules.list_rules(
        actor=ACTOR,
        workspace_id=WS,
        activity_id=activity_id,
        cursor=None,
        limit=25,
        q=None,
        status="DRAFT",
    )
    assert {item.id for item in drafts.items} == set(ids)
    confirmed = rules.list_rules(
        actor=ACTOR,
        workspace_id=WS,
        activity_id=activity_id,
        cursor=None,
        limit=25,
        q=None,
        status="CONFIRMED",
    )
    assert confirmed.items == [] and confirmed.next_cursor is None
    for bad in ("NOPE", "DRAFT,"):
        with pytest.raises(DomainError) as info:
            rules.list_rules(
                actor=ACTOR,
                workspace_id=WS,
                activity_id=activity_id,
                cursor=None,
                limit=25,
                q=None,
                status=bad,
            )
        assert info.value.status == 422 and info.value.issues[0].location == "/query/status", bad
    with pytest.raises(DomainError) as bad_cursor:
        rules.list_rules(
            actor=ACTOR,
            workspace_id=WS,
            activity_id=activity_id,
            cursor="garbage",
            limit=25,
            q=None,
            status=None,
        )
    assert bad_cursor.value.code == "BAD_CURSOR"
    assert bad_cursor.value.detail == workspace_service.BAD_CURSOR_DETAIL
    empty = rules.list_rules(
        actor=ACTOR,
        workspace_id=WS,
        activity_id="act-doesnotexist000000000000000000",
        cursor=None,
        limit=25,
        q=None,
        status=None,
    )
    assert empty.items == []
