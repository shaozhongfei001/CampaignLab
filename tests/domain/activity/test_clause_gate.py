"""M2-01/S5 · design §11.6 B：条款确认门禁（§4.2 gate 字面量 ``-k clause_gate``）。

纯领域层：只调 ``evaluate_clause_gate`` / ``note_satisfies_warnings`` /
``confirm_digest_matches``，不起 TestClient、不断言任何 HTTP 状态码（A257）。
六条 ``terms`` 的权威取值一律从 ``spec/.../fixtures/api-examples.json`` 的
``examples[3].request.terms`` **读文件**（A266，禁硬编码第二份真相源）。
证据登记面属仓储层，本层只验「给了／没给」两种分支（A266 末款）。
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from campaignlab.domain.activity import clauses

REPO_ROOT = Path(__file__).resolve().parents[3]
_RULES_PATH = REPO_ROOT / "spec/CampaignLab-SDD-v1.0/fixtures/cases/rules.json"
_EXAMPLES_PATH = REPO_ROOT / "spec/CampaignLab-SDD-v1.0/fixtures/api-examples.json"
_CARD_PATH = REPO_ROOT / "orchestrator/tasks/M2-01.md"
EVIDENCE_ID = "EV-CLAUSE-001"


def _coupon_terms() -> tuple[dict[str, Any], ...]:
    doc = json.loads(_EXAMPLES_PATH.read_text(encoding="utf-8"))
    example = doc["examples"][3]
    assert example["operationId"] == "createRule"
    terms = [dict(term) for term in example["request"]["terms"]]
    assert tuple(term["key"] for term in terms) == clauses.REQUIRED_CLAUSE_KEYS["coupon_threshold"]
    assert all(term["status"] == "CONFIRMED" for term in terms)
    assert all(term["evidence_id"] == EVIDENCE_ID for term in terms)
    return tuple(terms)


COUPON_TERMS = _coupon_terms()


def _synth_term(key: str) -> dict[str, Any]:
    return {
        "key": key,
        "clause": f"领域门禁矩阵口径：{key}",
        "decision": f"领域门禁矩阵业务说明：{key}",
        "status": "CONFIRMED",
        "evidence_id": EVIDENCE_ID,
    }


def _all_terms(template: str) -> tuple[dict[str, Any], ...]:
    if template == "coupon_threshold":
        return tuple(dict(term) for term in COUPON_TERMS)
    return tuple(_synth_term(key) for key in clauses.REQUIRED_CLAUSE_KEYS[template])


#: 矩阵参数在**收集期**从 ``REQUIRED_CLAUSE_KEYS`` 实取（A267：6＋3=9，非笛卡尔积）。
MATRIX_PAIRS: tuple[tuple[str, str], ...] = tuple(
    (template, key) for template, keys in clauses.REQUIRED_CLAUSE_KEYS.items() for key in keys
)


def _live_pairs() -> tuple[tuple[str, str], ...]:
    return tuple(
        (template, key) for template, keys in clauses.REQUIRED_CLAUSE_KEYS.items() for key in keys
    )


def _gate(template: str, terms: Sequence[Mapping[str, Any]]) -> tuple[clauses.GateIssue, ...]:
    return clauses.evaluate_clause_gate(
        template=template, terms=terms, registered_evidence_ids=(EVIDENCE_ID,)
    )


@pytest.fixture(autouse=True)
def _pc_c_env_control(monkeypatch: pytest.MonkeyPatch) -> None:
    """PC-C 阳性对照开关：环境旗标置 1 时在**测试进程内**减一个必需键再跑矩阵。"""
    if os.environ.get("CAMPAIGNLAB_S5_PC_C") == "1":
        patched = {
            template: tuple(keys[:-1]) for template, keys in clauses.REQUIRED_CLAUSE_KEYS.items()
        }
        monkeypatch.setattr(clauses, "REQUIRED_CLAUSE_KEYS", patched)


def test_clause_gate_blocks_when_a_required_key_is_missing() -> None:
    issues = clauses.evaluate_clause_gate(
        template="coupon_threshold", terms=(), registered_evidence_ids=()
    )
    assert len(issues) == 6 > 0
    assert [item.code for item in issues] == ["CLAUSE_MISSING"] * 6
    assert [item.location for item in issues] == [
        f"/terms/{key}" for key in clauses.REQUIRED_CLAUSE_KEYS["coupon_threshold"]
    ]
    assert all(item.severity == "ERROR" for item in issues)
    dropped = tuple(term for term in COUPON_TERMS if term["key"] != "refund")
    issues_one = _gate("coupon_threshold", dropped)
    assert len(issues_one) == 1
    assert issues_one[0].code == "CLAUSE_MISSING"
    assert issues_one[0].location == "/terms/refund"


def test_clause_gate_blocks_when_a_required_key_is_open() -> None:
    terms = tuple(
        {**term, "status": "OPEN"} if term["key"] == "payment" else term for term in COUPON_TERMS
    )
    issues = _gate("coupon_threshold", terms)
    assert len(issues) == 1
    assert issues[0].code == "CLAUSE_UNCONFIRMED"
    assert issues[0].location == "/terms/payment/status"
    assert issues[0].severity == "ERROR"


def test_clause_gate_blocks_on_duplicate_key() -> None:
    term = _synth_term("payment")
    issues = _gate("probe_unknown_template", (term, dict(term)))
    assert len(issues) == 2
    assert [item.code for item in issues] == ["CLAUSE_DUPLICATE", "CLAUSE_DUPLICATE"]
    assert [item.location for item in issues] == ["/terms/0", "/terms/1"]
    assert all(item.severity == "ERROR" for item in issues)
    assert _gate("probe_unknown_template", (term,)) == ()


def test_clause_gate_blocks_on_missing_or_unregistered_evidence() -> None:
    no_evidence = tuple(
        {k: v for k, v in term.items() if k != "evidence_id"}
        if term["key"] == "new_customer"
        else term
        for term in COUPON_TERMS
    )
    issues = _gate("coupon_threshold", no_evidence)
    assert len(issues) == 1
    assert issues[0].code == "CLAUSE_EVIDENCE_MISSING"
    assert issues[0].location == "/terms/new_customer/evidence_id"
    assert issues[0].severity == "ERROR"
    bogus = tuple(
        {**term, "evidence_id": "EV-NOT-REGISTERED"} if term["key"] == "refund" else term
        for term in COUPON_TERMS
    )
    issues2 = _gate("coupon_threshold", bogus)
    assert len(issues2) == 1
    assert issues2[0].code == "CLAUSE_EVIDENCE_UNREGISTERED"
    assert issues2[0].location == "/terms/refund/evidence_id"


def test_clause_gate_blocks_on_empty_decision() -> None:
    for blank in ("", "   "):
        terms = tuple(
            {**term, "decision": blank} if term["key"] == "payment" else term
            for term in COUPON_TERMS
        )
        issues = _gate("coupon_threshold", terms)
        assert len(issues) == 1
        assert issues[0].code == "CLAUSE_DECISION_EMPTY"
        assert issues[0].location == "/terms/payment/decision"
        assert issues[0].severity == "ERROR"


@pytest.mark.parametrize("template,key", MATRIX_PAIRS)
def test_clause_gate_six_by_three_matrix(template: str, key: str) -> None:
    # 覆盖率对撞：参数化面必须与**当前进程内**的 REQUIRED_CLAUSE_KEYS 实取一致（PC-C 的牙）。
    assert _live_pairs() == MATRIX_PAIRS
    full = _all_terms(template)
    assert (
        clauses.evaluate_clause_gate(
            template=template, terms=full, registered_evidence_ids=(EVIDENCE_ID,)
        )
        == ()
    )
    dropped = tuple(term for term in full if term["key"] != key)
    issues = _gate(template, dropped)
    assert len(issues) == 1
    assert issues[0].code == "CLAUSE_MISSING"
    assert issues[0].location == f"/terms/{key}"
    assert issues[0].severity == "ERROR"


def test_clause_gate_warning_requires_note() -> None:
    warning = clauses.GateIssue(
        code="FAKE_WARNING", location="/content/x", message="m", severity="WARNING"
    )
    for blank in ("", "   ", "\u00a0", "\u3000"):
        issue = clauses.note_satisfies_warnings(note=blank, warnings=[warning])
        assert issue is not None
        assert issue.code == "CONFIRMATION_NOTE_REQUIRED"
        assert issue.location == "/note"
        assert issue.severity == "ERROR"
    assert clauses.note_satisfies_warnings(note="口径已人工复核", warnings=[warning]) is None
    error_only = clauses.GateIssue(
        code="FAKE_ERROR", location="/content/y", message="m", severity="ERROR"
    )
    assert clauses.note_satisfies_warnings(note="", warnings=[error_only]) is None
    assert clauses.note_satisfies_warnings(note="", warnings=[]) is None


def test_clause_gate_digest_mismatch_is_reported() -> None:
    provided = "a" * 64
    current = "b" * 64
    assert clauses.confirm_digest_matches(provided=provided, current=provided) is True
    assert clauses.confirm_digest_matches(provided=provided, current=current) is False
    assert type(clauses.confirm_digest_matches(provided=provided, current=current)) is bool
    assert provided not in repr(clauses.confirm_digest_matches(provided=provided, current=current))


def test_clause_gate_required_keys_are_the_spec_nine() -> None:
    spec_nine = (
        "new_customer",
        "payment",
        "time_window",
        "stacking",
        "budget_and_quota",
        "refund",
        "same_day_scope",
        "priority",
        "daily_cap",
    )
    assert spec_nine == clauses.ALL_CLAUSE_KEYS
    assert len(clauses.ALL_CLAUSE_KEYS) == 9
    assert tuple(clauses.REQUIRED_CLAUSE_KEYS) == ("coupon_threshold", "callback_priority")
    joined = (
        clauses.REQUIRED_CLAUSE_KEYS["coupon_threshold"]
        + clauses.REQUIRED_CLAUSE_KEYS["callback_priority"]
    )
    assert joined == clauses.ALL_CLAUSE_KEYS
    line = next(
        raw
        for raw in _CARD_PATH.read_text(encoding="utf-8").splitlines()
        if raw.startswith("public_frozen:")
    )
    group = next(item for item in re.findall("（([^（）]*)）", line) if "`new_customer`" in item)
    assert tuple(re.findall("`([^`]+)`", group)) == spec_nine


def test_clause_gate_rejects_unsupported_schema_version() -> None:
    """``SCHEMA_VERSION_UNSUPPORTED`` 标签登记在门禁码面（单一出处），但领域层门禁函数
    不接 ``schema_version``；实测的领域入口是 ``run_checks`` 的 ``TEMPLATE_CONST_MISMATCH``
    （``_CONST_BY_TEMPLATE`` 含 ``("schema_version", 1)``）。⇒ 已按 §8 上报 U 项。
    """
    assert "SCHEMA_VERSION_UNSUPPORTED" in clauses.CLAUSE_ISSUE_CODES
    assert _gate("coupon_threshold", COUPON_TERMS) == ()
    assert all(item.code != "SCHEMA_VERSION_UNSUPPORTED" for item in _gate("zzz", ()))
    from campaignlab.domain.activity import checks

    base = json.loads(_RULES_PATH.read_text(encoding="utf-8"))["CP-V1"]
    bad = {**base, "schema_version": 2}
    ctx_bad = checks.RuleContext(
        rule_id="R-schema", template="coupon_threshold", content=bad, terms=(), sibling_confirmed=()
    )
    ctx_ok = checks.RuleContext(
        rule_id="R-schema",
        template="coupon_threshold",
        content=base,
        terms=(),
        sibling_confirmed=(),
    )
    bad_codes = [
        (item.code, item.location, item.severity) for item in checks.run_checks(ctx_bad).issues
    ]
    ok_codes = {item.code for item in checks.run_checks(ctx_ok).issues}
    assert ("TEMPLATE_CONST_MISMATCH", "/content/schema_version", "ERROR") in bad_codes
    assert "TEMPLATE_CONST_MISMATCH" not in ok_codes
    assert "SCHEMA_VERSION_UNSUPPORTED" not in {code for code, _, _ in bad_codes}
