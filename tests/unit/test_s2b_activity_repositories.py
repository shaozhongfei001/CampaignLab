"""S2b-1：三个新 Repository 的行为守护（design §3 的 ``guard`` 镜像 ＋ §7.4 的批量读）。

钉住五件事：

1. **guard 镜像有牙**（派单文 §6①）：``update_fields`` / ``update_draft`` / ``confirm`` 的
   WHERE 谓词一旦丢掉 ``revision=:revision``、``status='OPEN'``、``state='DRAFT'`` 或
   ``digest=:digest``，本文件的用例必须红 —— 断言的是 ``rowcount`` 与行内容，**不是源文本**；
2. 所有写 UPDATE 一律返回 ``int``，仓储层**不翻译**领域错（落空就是 ``0``，
   由 ``application/activity_service.py`` 翻成 409/412）；
3. ``update_fields`` 在三列全不给时**仍**bump ``revision``（design §3.4：只改 ``bindings`` 的
   PATCH 不碰 ``activities`` 的任何内容列，但 ETag 必须变，否则 412 语义失效）；
4. ``replace_set`` 是整体替换、``list_for_activity`` 的顺序照 design §7.4 的冻结序，
   ``evidence`` 侧只提供**只读**的批量存在性投影；
5. ``list_for_activities`` / ``list_rule_ids`` / ``list_receipt_ids`` 批量取，**禁 N+1**
   （用 SQLAlchemy 的 ``before_cursor_execute`` 事件数 SELECT 条数）。

库用活契约 ``contracts/sqlite-v1.sql`` 建（只读），不跑 alembic：本文件测的是 SQL 与 DDL
约束的互动（体例＝``tests/unit/test_s3d_repositories.py``）。
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, event

from campaignlab.api.common import Workspace
from campaignlab.infra.db.engine import connect, make_engine
from campaignlab.infra.db.repositories import (
    ActivityBindingRepository,
    ActivityRecord,
    ActivityRepository,
    BindingRecord,
    RuleVersionRecord,
    RuleVersionRepository,
    WorkspaceRepository,
)

REPO = Path(__file__).resolve().parents[2]
DDL = REPO / "contracts" / "sqlite-v1.sql"
T0 = datetime(2026, 11, 15, 1, 0, 0, tzinfo=UTC)
ISO0 = T0.isoformat()
ISO1 = (T0 + timedelta(minutes=1)).isoformat()
ISO2 = (T0 + timedelta(minutes=2)).isoformat()
ISO9 = (T0 + timedelta(minutes=9)).isoformat()
WS = "ws-s2b"
OTHER_WS = "ws-other"
DIGEST = "a" * 64
OTHER_DIGEST = "b" * 64
CONTENT_JSON = json.dumps({"schema_version": 1, "template": "coupon_threshold"}, sort_keys=True)
TERMS_JSON = json.dumps([], sort_keys=True)
#: 带时间窗的内容（``callback_priority`` 模板没有这两列，故两种形状都要能读）
WINDOW_JSON = json.dumps(
    {
        "schema_version": 1,
        "template": "coupon_threshold",
        "starts_at": "2026-01-01T00:00:00+00:00",
        "ends_at": "2026-02-01T00:00:00+00:00",
    },
    sort_keys=True,
)

activities = ActivityRepository()
bindings = ActivityBindingRepository()
rules = RuleVersionRepository()


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    """按活契约 DDL 建一个临时库（不建 ``alembic_version``：本文件不碰 health 面）。"""
    assert DDL.is_file(), f"活契约 DDL 读不到：{DDL}"
    db = tmp_path / "campaignlab.db"
    raw = sqlite3.connect(db)
    try:
        raw.executescript(DDL.read_text(encoding="utf-8"))
        raw.commit()
    finally:
        raw.close()
    return make_engine(f"sqlite:///{db}")


def _activity(
    activity_id: str,
    *,
    name: str = "双十一",
    status: str = "OPEN",
    revision: int = 1,
    bank_id: str | None = "B-1",
    external: str | None = "AC-101",
    created_at: str = ISO0,
    current_rule_id: str | None = None,
    workspace_id: str = WS,
) -> ActivityRecord:
    return ActivityRecord(
        workspace_id=workspace_id,
        id=activity_id,
        name=name,
        bank_id=bank_id,
        external_activity_id=external,
        description="",
        status=status,
        current_rule_id=current_rule_id,
        revision=revision,
        created_at=created_at,
    )


def _binding(
    activity_id: str,
    strategy_id: str,
    source_version: str,
    valid_from: str,
    valid_until: str,
    evidence_id: str = "ev-1",
) -> BindingRecord:
    return BindingRecord(
        workspace_id=WS,
        activity_id=activity_id,
        strategy_id=strategy_id,
        source_version=source_version,
        valid_from=valid_from,
        valid_until=valid_until,
        evidence_id=evidence_id,
    )


def _rule(
    rule_id: str,
    *,
    activity_id: str = "act-1",
    state: str = "DRAFT",
    revision: int = 1,
    digest: str = DIGEST,
    label: str = "v1",
    created_at: str = ISO0,
    parent_rule_id: str | None = None,
    confirmed_at: str | None = None,
    confirmation: str | None = None,
    content_json: str = CONTENT_JSON,
) -> RuleVersionRecord:
    return RuleVersionRecord(
        workspace_id=WS,
        id=rule_id,
        activity_id=activity_id,
        parent_rule_id=parent_rule_id,
        label=label,
        template="coupon_threshold",
        source_rule_version=None,
        state=state,
        revision=revision,
        content_json=content_json,
        terms_json=TERMS_JSON,
        digest=digest,
        created_at=created_at,
        confirmed_at=confirmed_at,
        confirmation=confirmation,
    )


def _seed_base(conn: Connection) -> None:
    """工作区 ＋ 一行 ``artifacts``/``evidence``（``activity_bindings`` 的 FK 前置）。"""
    WorkspaceRepository().insert(
        conn,
        workspace=Workspace(
            id=WS,
            revision=1,
            created_at=T0,
            name="S2b 仓储用例",
            source_class="SYNTHETIC",
            authorization_note=None,
        ),
    )
    conn.exec_driver_sql(
        "INSERT INTO artifacts (workspace_id, id, kind, sha256, relative_path, byte_size, "
        "created_at) VALUES (?, ?, 'CLAUSE', ?, 'ev/s2b.txt', 10, ?)",
        (WS, "art-1", DIGEST, ISO0),
    )
    conn.exec_driver_sql(
        "INSERT INTO evidence (workspace_id, id, kind, source_id, locator, label, source_class, "
        "content_digest, artifact_id, created_at) "
        "VALUES (?, ?, 'CLAUSE', 'S-1', 'loc', 'lbl', 'SYNTHETIC', ?, 'art-1', ?)",
        (WS, "ev-1", DIGEST, ISO0),
    )


def _count_selects(engine: Engine, statements: list[str]) -> Callable[[], None]:
    """挂 ``before_cursor_execute`` 收集语句，返回卸载器（防 N+1 的取证口径）。"""

    def listener(
        conn: Connection,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", listener)

    def detach() -> None:
        event.remove(engine, "before_cursor_execute", listener)

    return detach


def test_update_fields_ignores_a_stale_revision(engine: Engine) -> None:
    """派单文 §6①：去掉 ``AND revision = :revision`` 本条必须红。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=_activity("act-1"))
    with connect(engine) as conn, conn.begin():
        first = activities.update_fields(
            conn, workspace_id=WS, activity_id="act-1", revision=1, name="改名"
        )
        assert first == 1 and isinstance(first, int)
        stale = activities.update_fields(
            conn, workspace_id=WS, activity_id="act-1", revision=1, name="再改"
        )
        assert stale == 0, "旧 revision 竟然写进去了：guard 镜像失效"
        record = activities.get(conn, workspace_id=WS, activity_id="act-1")
        assert record is not None
        assert record.name == "改名" and record.revision == 2


def test_update_fields_ignores_an_archived_row(engine: Engine) -> None:
    """A2 归档后 A3 不可再写：去掉 ``status='OPEN'`` 本条必须红。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=_activity("act-1"))
        assert (
            activities.update_fields(
                conn, workspace_id=WS, activity_id="act-1", revision=1, status="ARCHIVED"
            )
            == 1
        )
        assert (
            activities.update_fields(
                conn, workspace_id=WS, activity_id="act-1", revision=2, name="归档后改名"
            )
            == 0
        )
        record = activities.get(conn, workspace_id=WS, activity_id="act-1")
        assert record is not None
        assert record.status == "ARCHIVED" and record.name == "双十一" and record.revision == 2


def test_update_fields_bumps_revision_when_no_content_column_is_given(engine: Engine) -> None:
    """只改 ``bindings`` 的 PATCH（design §3.4）：SET 列为空也必须 bump ``revision``。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=_activity("act-1"))
        touched = activities.update_fields(conn, workspace_id=WS, activity_id="act-1", revision=1)
        assert touched == 1
        record = activities.get(conn, workspace_id=WS, activity_id="act-1")
        assert record is not None
        assert record.revision == 2
        assert (record.name, record.description, record.status) == ("双十一", "", "OPEN")


def test_update_fields_on_an_unknown_row_returns_zero_not_an_error(engine: Engine) -> None:
    """仓储层不翻译领域错（``worker/store.py`` 的既有分工）：落空就是 0。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        assert (
            activities.update_fields(
                conn, workspace_id=WS, activity_id="act-nope", revision=1, name="x"
            )
            == 0
        )
        # 跨工作区同样不可见
        WorkspaceRepository().insert(
            conn,
            workspace=Workspace(
                id=OTHER_WS,
                revision=1,
                created_at=T0,
                name="别的区",
                source_class="SYNTHETIC",
                authorization_note=None,
            ),
        )
        activities.insert(conn, record=_activity("act-1", workspace_id=OTHER_WS))
        assert (
            activities.update_fields(
                conn, workspace_id=WS, activity_id="act-1", revision=1, name="越区改"
            )
            == 0
        )


def test_set_current_rule_links_the_rule_and_bumps_the_activity_revision(engine: Engine) -> None:
    """design §3.2 末条的联动写：谓词**不带** revision 镜像（R3 不是活动状态机的一行）。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=_activity("act-1"))
        rules.insert(conn, record=_rule("rul-1"))
        touched = activities.set_current_rule(
            conn, workspace_id=WS, activity_id="act-1", rule_id="rul-1"
        )
        assert touched == 1 and isinstance(touched, int)
        record = activities.get(conn, workspace_id=WS, activity_id="act-1")
        assert record is not None
        assert record.current_rule_id == "rul-1" and record.revision == 2
        # 连 bump 也是幂等可见的：再指一次仍然 +1
        assert (
            activities.set_current_rule(conn, workspace_id=WS, activity_id="act-1", rule_id="rul-1")
            == 1
        )
        again = activities.get(conn, workspace_id=WS, activity_id="act-1")
        assert again is not None and again.revision == 3
        assert (
            activities.set_current_rule(
                conn, workspace_id=WS, activity_id="act-nope", rule_id="rul-1"
            )
            == 0
        )


def test_find_by_external_locates_the_clash_and_null_bank_never_clashes(engine: Engine) -> None:
    """design §6.4：只有 ``bank_id`` 与 ``external_activity_id`` 都非空才可能撞 UNIQUE。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=_activity("act-1"))
        # 两个 bank_id 为 NULL 的活动共用同一外部号：SQLite 的 UNIQUE 里 NULL 互不相等
        activities.insert(conn, record=_activity("act-2", bank_id=None, external="AC-101"))
        activities.insert(conn, record=_activity("act-3", bank_id=None, external="AC-101"))
        hit = activities.find_by_external(
            conn, workspace_id=WS, bank_id="B-1", external_activity_id="AC-101"
        )
        assert hit is not None and hit.id == "act-1"
        miss = activities.find_by_external(
            conn, workspace_id=WS, bank_id="B-9", external_activity_id="AC-101"
        )
        assert miss is None
        other = activities.find_by_external(
            conn, workspace_id=OTHER_WS, bank_id="B-1", external_activity_id="AC-101"
        )
        assert other is None


def test_replace_set_is_a_full_replacement_and_reads_back_in_the_frozen_order(
    engine: Engine,
) -> None:
    """design §3.4 的整体替换 ＋ §7.4 的冻结序 ``valid_from, strategy_id, source_version``。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=_activity("act-1"))
        bindings.replace_set(
            conn,
            workspace_id=WS,
            activity_id="act-1",
            bindings=[
                _binding("act-1", "S-2", "v1", "2026-03-01", "2026-04-01"),
                _binding("act-1", "S-1", "v2", "2026-01-01", "2026-02-01"),
                _binding("act-1", "S-1", "v1", "2026-01-01", "2026-02-01"),
            ],
        )
        got = bindings.list_for_activity(conn, workspace_id=WS, activity_id="act-1")
        assert [(item.strategy_id, item.source_version, item.valid_from) for item in got] == [
            ("S-1", "v1", "2026-01-01"),
            ("S-1", "v2", "2026-01-01"),
            ("S-2", "v1", "2026-03-01"),
        ]
        # 整体替换：给一条就只剩一条（不是 merge）
        bindings.replace_set(
            conn,
            workspace_id=WS,
            activity_id="act-1",
            bindings=[_binding("act-1", "S-9", "v1", "2026-05-01", "2026-06-01")],
        )
        after = bindings.list_for_activity(conn, workspace_id=WS, activity_id="act-1")
        assert [item.strategy_id for item in after] == ["S-9"]
        # 空数组＝清空（AC-202 的合法意图）
        bindings.replace_set(conn, workspace_id=WS, activity_id="act-1", bindings=[])
        assert bindings.list_for_activity(conn, workspace_id=WS, activity_id="act-1") == []
        # 别的活动不受影响
        assert bindings.list_for_activity(conn, workspace_id=WS, activity_id="act-2") == []


def test_evidence_exists_returns_the_registered_subset_only(engine: Engine) -> None:
    """只读 ``evidence``：返回**已登记子集**，跨工作区不可见，空入参不打库。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        assert bindings.evidence_exists(conn, workspace_id=WS, evidence_ids=[]) == set()
        assert bindings.evidence_exists(
            conn, workspace_id=WS, evidence_ids=["ev-1", "ev-nope"]
        ) == {"ev-1"}
        assert bindings.evidence_exists(conn, workspace_id=OTHER_WS, evidence_ids=["ev-1"]) == set()


def test_binding_reads_are_batched_and_never_n_plus_one(engine: Engine) -> None:
    """design §7.4「禁 N+1」：三个活动一次 ``IN (…)`` 查询，无绑定活动预置空数组。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        for index, created in enumerate((ISO0, ISO1, ISO2)):
            activities.insert(
                conn, record=_activity(f"act-{index + 1}", created_at=created, external=None)
            )
        bindings.replace_set(
            conn,
            workspace_id=WS,
            activity_id="act-1",
            bindings=[_binding("act-1", "S-1", "v1", "2026-01-01", "2026-02-01")],
        )
        rules.insert(conn, record=_rule("rul-1", activity_id="act-1"))
    statements: list[str] = []
    detach = _count_selects(engine, statements)
    try:
        with connect(engine) as conn:
            ids = ["act-1", "act-2", "act-3"]
            grouped = bindings.list_for_activities(conn, workspace_id=WS, activity_ids=ids)
            rule_ids = activities.list_rule_ids(conn, workspace_id=WS, activity_ids=ids)
            receipt_ids = activities.list_receipt_ids(conn, workspace_id=WS, activity_ids=ids)
            empty = bindings.list_for_activities(conn, workspace_id=WS, activity_ids=[])
    finally:
        detach()
    selects = [item for item in statements if item.lstrip().upper().startswith("SELECT")]
    assert len(selects) == 3, f"批量读退化成 N+1：{selects}"
    assert set(grouped) == {"act-1", "act-2", "act-3"}
    assert [item.strategy_id for item in grouped["act-1"]] == ["S-1"]
    assert grouped["act-2"] == [] and grouped["act-3"] == []
    assert rule_ids == {"act-1": ["rul-1"], "act-2": [], "act-3": []}
    # ``receipts`` 是 M2-03 的写面，本卡只读：整表为空也必须给出每个键的空数组
    assert receipt_ids == {"act-1": [], "act-2": [], "act-3": []}
    assert empty == {}


def test_update_draft_mirrors_state_and_revision(engine: Engine) -> None:
    """R2：去掉 ``state='DRAFT'`` 或 ``revision=:revision`` 本条必须红。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=_activity("act-1"))
        rules.insert(conn, record=_rule("rul-1"))
        assert (
            rules.update_draft(conn, workspace_id=WS, rule_id="rul-1", revision=99, label="x") == 0
        )
        touched = rules.update_draft(
            conn, workspace_id=WS, rule_id="rul-1", revision=1, label="v1-renamed"
        )
        assert touched == 1 and isinstance(touched, int)
        record = rules.get(conn, workspace_id=WS, rule_id="rul-1")
        assert record is not None
        assert record.label == "v1-renamed" and record.revision == 2
        # label 不进摘要：不给 digest 时该列必须原样保留（design §4.6）
        assert record.digest == DIGEST and record.state == "DRAFT"
        assert record.confirmed_at is None and record.confirmation is None


def test_confirm_mirrors_state_revision_and_digest(engine: Engine) -> None:
    """R3：三谓词缺一即红（重复确认／旧 revision／摘要漂移全部落成 ``rowcount == 0``）。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=_activity("act-1"))
        rules.insert(conn, record=_rule("rul-1"))
        stale = rules.confirm(
            conn,
            workspace_id=WS,
            rule_id="rul-1",
            revision=99,
            digest=DIGEST,
            confirmed_at=ISO9,
            confirmation="已复核",
        )
        assert stale == 0
        drifted = rules.confirm(
            conn,
            workspace_id=WS,
            rule_id="rul-1",
            revision=1,
            digest=OTHER_DIGEST,
            confirmed_at=ISO9,
            confirmation="已复核",
        )
        assert drifted == 0, "摘要漂移竟然确认成功：digest 镜像失效"
        touched = rules.confirm(
            conn,
            workspace_id=WS,
            rule_id="rul-1",
            revision=1,
            digest=DIGEST,
            confirmed_at=ISO9,
            confirmation="已复核",
        )
        assert touched == 1 and isinstance(touched, int)
        confirmed = rules.get(conn, workspace_id=WS, rule_id="rul-1")
        assert confirmed is not None
        assert confirmed.state == "CONFIRMED" and confirmed.revision == 2
        assert confirmed.confirmed_at == ISO9 and confirmed.confirmation == "已复核"
        # 已确认后再确认／再改草稿：state 镜像让它们全部落空
        assert (
            rules.confirm(
                conn,
                workspace_id=WS,
                rule_id="rul-1",
                revision=2,
                digest=DIGEST,
                confirmed_at=ISO9,
                confirmation="再确认",
            )
            == 0
        )
        assert (
            rules.update_draft(conn, workspace_id=WS, rule_id="rul-1", revision=2, label="改不动")
            == 0
        )
        unchanged = rules.get(conn, workspace_id=WS, rule_id="rul-1")
        assert unchanged is not None
        assert unchanged.confirmation == "已复核" and unchanged.label == "v1"


def test_list_confirmed_siblings_excludes_drafts_and_itself(engine: Engine) -> None:
    """C9 的输入面：只要**同活动**、**已确认**、**不是自己**的兄弟版本。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=_activity("act-1"))
        activities.insert(conn, record=_activity("act-2", created_at=ISO1, external=None))
        rules.insert(conn, record=_rule("rul-1", created_at=ISO0))
        rules.insert(
            conn,
            record=_rule(
                "rul-2",
                created_at=ISO1,
                state="CONFIRMED",
                confirmed_at=ISO1,
                confirmation="已复核",
                content_json=WINDOW_JSON,
            ),
        )
        rules.insert(conn, record=_rule("rul-3", activity_id="act-2", created_at=ISO2))
        siblings = rules.list_confirmed_siblings(
            conn, workspace_id=WS, activity_id="act-1", exclude_rule_id="rul-3"
        )
        assert [item["id"] for item in siblings] == ["rul-2"]
        # 只给 ``RuleContext.sibling_confirmed`` 声明的四个键（design §5.3）
        assert set(siblings[0]) == {"id", "template", "starts_at", "ends_at"}
        assert siblings[0]["template"] == "coupon_threshold"
        assert siblings[0]["starts_at"] == "2026-01-01T00:00:00+00:00"
        assert siblings[0]["ends_at"] == "2026-02-01T00:00:00+00:00"
        # 没有时间窗的模板一律 None，禁假设「每个模板都有」
        windowless = rules.list_confirmed_siblings(
            conn, workspace_id=WS, activity_id="act-1", exclude_rule_id="rul-1"
        )
        assert windowless[0]["id"] == "rul-2"
        # 自己即使已确认也要被排除
        assert (
            rules.list_confirmed_siblings(
                conn, workspace_id=WS, activity_id="act-1", exclude_rule_id="rul-2"
            )
            == []
        )


def test_list_confirmed_case_ids_tolerates_an_empty_cases_table(engine: Engine) -> None:
    """design §6.5 的 ``requires_rerun_case_ids``：``cases`` 归 M2-02，空表必须返回 ``[]``。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=_activity("act-1"))
        rules.insert(
            conn,
            record=_rule("rul-1", state="CONFIRMED", confirmed_at=ISO0, confirmation="已复核"),
        )
        assert rules.list_confirmed_case_ids(conn, workspace_id=WS, rule_ids=[]) == []
        assert rules.list_confirmed_case_ids(conn, workspace_id=WS, rule_ids=["rul-1"]) == []
        conn.exec_driver_sql(
            "INSERT INTO cases (workspace_id, id, activity_id, name, mode, state, revision, "
            "input_json, observed_rule_id, digest, created_at) "
            "VALUES (?, 'case-2', 'act-1', '乙', 'SYNTHETIC', 'CONFIRMED', 1, '{}', 'rul-1', ?, ?)",
            (WS, DIGEST, ISO1),
        )
        conn.exec_driver_sql(
            "INSERT INTO cases (workspace_id, id, activity_id, name, mode, state, revision, "
            "input_json, observed_rule_id, digest, created_at) "
            "VALUES (?, 'case-1', 'act-1', '甲', 'SYNTHETIC', 'CONFIRMED', 1, '{}', 'rul-1', ?, ?)",
            (WS, DIGEST, ISO0),
        )
        conn.exec_driver_sql(
            "INSERT INTO cases (workspace_id, id, activity_id, name, mode, state, revision, "
            "input_json, observed_rule_id, digest, created_at) "
            "VALUES (?, 'case-3', 'act-1', '丙', 'SYNTHETIC', 'DRAFT', 1, '{}', 'rul-1', ?, ?)",
            (WS, DIGEST, ISO2),
        )
        # 只取 CONFIRMED，且按 id 升序（与 design §7.4 的稳定序一致）
        assert rules.list_confirmed_case_ids(conn, workspace_id=WS, rule_ids=["rul-1"]) == [
            "case-1",
            "case-2",
        ]
        assert rules.list_confirmed_case_ids(conn, workspace_id=WS, rule_ids=["rul-nope"]) == []


def test_activity_list_page_pages_by_keyset_and_pushes_down_status(engine: Engine) -> None:
    """键集翻页与 ``WorkspaceRepository.list_page`` 同口径：``created_at DESC, id ASC``。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=_activity("act-1", name="双十一", created_at=ISO0))
        activities.insert(
            conn, record=_activity("act-2", name="618", created_at=ISO1, external=None)
        )
        activities.insert(
            conn,
            record=_activity(
                "act-3", name="年货节", created_at=ISO2, external=None, status="ARCHIVED"
            ),
        )
        first = activities.list_page(conn, workspace_id=WS, limit=2)
        assert [item.id for item in first] == ["act-3", "act-2"]
        last = first[-1]
        second = activities.list_page(
            conn, workspace_id=WS, limit=2, after=(last.created_at, last.id)
        )
        assert [item.id for item in second] == ["act-1"]
        only_open = activities.list_page(conn, workspace_id=WS, limit=10, statuses=["OPEN"])
        assert [item.id for item in only_open] == ["act-2", "act-1"]
        # ``q`` 命中 name 与 external_activity_id，且是 NFKC ＋ casefold 的子串匹配
        by_name = activities.list_page(conn, workspace_id=WS, limit=10, q="６１８")
        assert [item.id for item in by_name] == ["act-2"]
        by_external = activities.list_page(conn, workspace_id=WS, limit=10, q="ac-101")
        assert [item.id for item in by_external] == ["act-1"]
        assert activities.list_page(conn, workspace_id=WS, limit=10, q="zzz") == []
        assert activities.list_page(conn, workspace_id=OTHER_WS, limit=10) == []
        with pytest.raises(ValueError, match="limit"):
            activities.list_page(conn, workspace_id=WS, limit=0)


def test_rule_list_page_filters_by_state_and_matches_label(engine: Engine) -> None:
    """``RuleVersionRepository.list_page`` 与活动面同口径（design §1.5）。"""
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=_activity("act-1"))
        rules.insert(conn, record=_rule("rul-1", label="v1", created_at=ISO0))
        rules.insert(
            conn,
            record=_rule(
                "rul-2",
                label="V2 复核版",
                created_at=ISO1,
                state="CONFIRMED",
                confirmed_at=ISO1,
                confirmation="已复核",
            ),
        )
        page = rules.list_page(conn, workspace_id=WS, activity_id="act-1", limit=10)
        assert [item.id for item in page] == ["rul-2", "rul-1"]
        drafts = rules.list_page(
            conn, workspace_id=WS, activity_id="act-1", limit=10, states=["DRAFT"]
        )
        assert [item.id for item in drafts] == ["rul-1"]
        hit = rules.list_page(conn, workspace_id=WS, activity_id="act-1", limit=10, q="v2 复核")
        assert [item.id for item in hit] == ["rul-2"]
        first = rules.list_page(conn, workspace_id=WS, activity_id="act-1", limit=1)
        tail = rules.list_page(
            conn,
            workspace_id=WS,
            activity_id="act-1",
            limit=1,
            after=(first[-1].created_at, first[-1].id),
        )
        assert [item.id for item in tail] == ["rul-1"]
        assert rules.list_page(conn, workspace_id=WS, activity_id="act-2", limit=10) == []


def test_row_mappers_round_trip_every_column(engine: Engine) -> None:
    """``_activity_of`` / ``_binding_of`` / ``_rule_version_of`` 不丢列、不改类型。"""
    record = _activity("act-1", current_rule_id=None, created_at=ISO0)
    binding = _binding("act-1", "S-1", "v1", "2026-01-01", "2026-02-01")
    rule = _rule("rul-1", created_at=ISO0)
    with connect(engine) as conn, conn.begin():
        _seed_base(conn)
        activities.insert(conn, record=record)
        bindings.replace_set(conn, workspace_id=WS, activity_id="act-1", bindings=[binding])
        rules.insert(conn, record=rule)
        assert activities.get(conn, workspace_id=WS, activity_id="act-1") == record
        assert bindings.list_for_activity(conn, workspace_id=WS, activity_id="act-1") == [binding]
        assert rules.get(conn, workspace_id=WS, rule_id="rul-1") == rule
        assert activities.get(conn, workspace_id=WS, activity_id="act-nope") is None
        assert rules.get(conn, workspace_id=WS, rule_id="rul-nope") is None
