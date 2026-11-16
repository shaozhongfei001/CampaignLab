"""M2-01/S5 · design §11.6 F：字段差异（§6.5 四类 path ＋ 渲染口径 ＋ 投影外字段排除）。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from campaignlab.api.common import canonical_json
from campaignlab.domain.activity import diff
from campaignlab.domain.errors import InternalFailure

REPO_ROOT = Path(__file__).resolve().parents[3]
_RULES_PATH = REPO_ROOT / "spec/CampaignLab-SDD-v1.0/fixtures/cases/rules.json"
FIXTURES = json.loads(_RULES_PATH.read_text(encoding="utf-8"))


def _changes(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> tuple[diff.FieldChangeDraft, ...]:
    return diff.field_changes(baseline=baseline, candidate=candidate, canonicalize=canonical_json)


def test_rule_diff_paths_are_frozen_and_sorted() -> None:
    assert diff.DIFF_PATH_LABEL == "/label"
    assert diff.DIFF_PATH_SOURCE_VERSION == "/source_rule_version"
    assert diff.DIFF_PATH_CONTENT_PREFIX == "/content/"
    assert diff.DIFF_PATH_TERMS_PREFIX == "/terms/"
    baseline = {
        "label": "甲",
        "content": {"b_field": 1, "a_field": 1, "same": 7},
        "source_rule_version": "1",
        "terms": [{"key": "refund", "clause": "旧口径", "decision": "d", "status": "OPEN"}],
    }
    candidate = {
        "label": "乙",
        "content": {"b_field": 2, "a_field": 3, "same": 7},
        "source_rule_version": "2",
        "terms": [
            {"key": "refund", "clause": "旧口径", "decision": "d", "status": "CONFIRMED"},
            {"key": "priority", "clause": "新条款", "decision": "n", "status": "OPEN"},
        ],
    }
    paths = tuple(item.path for item in _changes(baseline, candidate))
    assert paths == (
        "/label",
        "/content/a_field",
        "/content/b_field",
        "/source_rule_version",
        "/terms/priority",
        "/terms/refund/status",
    )


def test_rule_diff_excludes_non_projection_fields() -> None:
    shared: dict[str, Any] = {
        "label": "同一版本",
        "content": {"coupon_fen": 2000},
        "source_rule_version": "1",
        "terms": [
            {"key": "payment", "clause": "c", "decision": "d", "status": "CONFIRMED"},
            {"key": "refund", "clause": "r", "decision": "d2", "status": "OPEN"},
        ],
    }
    other_terms_order = {**shared, "terms": list(reversed(shared["terms"]))}
    assert _changes(dict(shared), {**shared, "rule_id": "R-other"}) == ()
    assert _changes(dict(shared), {**shared, "updated_at": "2026-10-09T00:00:00+08:00"}) == ()
    assert _changes(dict(shared), dict(other_terms_order)) == ()
    assert _changes(dict(shared), {**shared, "confirmed_at": "2026-10-09T00:00:00+08:00"}) == ()
    assert len(_changes(dict(shared), {**shared, "label": "改了标签"})) == 1


def test_rule_diff_renders_values_as_strings() -> None:
    assert diff.render_scalar(5) == "5"
    assert diff.render_scalar(0) == "0"
    assert diff.render_scalar(True) == "true"
    assert diff.render_scalar(False) == "false"
    moment = datetime(2026, 10, 1, 8, 30, tzinfo=UTC)
    assert diff.render_scalar(moment) == moment.isoformat()
    assert diff.render_scalar(None) is None
    assert diff.render_scalar("文本") == "文本"
    baseline = {"label": "a", "content": {"n": 1, "flag": True, "gone": "x"}}
    candidate = {"label": "b", "content": {"n": 2, "flag": False}}
    changes = {item.path: item for item in _changes(baseline, candidate)}
    assert changes["/content/n"].before == "1" and changes["/content/n"].after == "2"
    assert changes["/content/flag"].after == "false"
    assert changes["/content/gone"].after is None
    for item in changes.values():
        for side in (item.before, item.after):
            assert side is None or len(side) <= diff.FIELD_CHANGE_MAX_LENGTH == 1000
    huge = "字" * (diff.FIELD_CHANGE_MAX_LENGTH + 1)
    with pytest.raises(InternalFailure):
        _changes({"content": {"big": "other"}}, {"content": {"big": huge}})


def test_rule_diff_cp_v1_to_cp_v2_is_refund_policy_only() -> None:
    cp_v1 = FIXTURES["CP-V1"]
    cp_v2 = FIXTURES["CP-V2"]
    assert set(cp_v1) == set(cp_v2)
    assert len(cp_v1) == 13
    differing = {key for key in cp_v1 if cp_v1[key] != cp_v2[key]}
    assert differing == {"refund_policy"}
    assert cp_v1["refund_policy"] == "KEEP"
    assert cp_v2["refund_policy"] == "RECOMPUTE_UNUSED"
    changes = _changes(
        {"content": cp_v1, "terms": [], "label": "same", "source_rule_version": "1"},
        {"content": cp_v2, "terms": [], "label": "same", "source_rule_version": "1"},
    )
    assert len(changes) == 1
    assert changes[0].path == "/content/refund_policy"
    assert changes[0].before == "KEEP"
    assert changes[0].after == "RECOMPUTE_UNUSED"
