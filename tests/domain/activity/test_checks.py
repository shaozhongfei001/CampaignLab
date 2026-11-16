"""M2-01/S5 · design §11.6 E：检查项框架（A264 五口径必触发）与 §5.4 反例面。

函数名含 ``check_framework`` / ``boundary_case``（V6）。全部按 §4.3 实测分母断言：
CP-V1 15 条／CP-V2 15 条／CB-V1 2 条／CB-V2 3 条；``RuleContext.sibling_confirmed`` 用
``()``（§4.4 陷阱 1）。反例合法性走 ``TypeAdapter(CaseInput)``（A265），不起 TestClient。
"""

from __future__ import annotations

import json
import re
import typing
from pathlib import Path
from typing import Any, Literal

import pytest
from pydantic import TypeAdapter, ValidationError

from campaignlab.api.common import CaseInput, canonical_json
from campaignlab.domain.activity import checks, clauses
from campaignlab.domain.activity.checks import RuleContext

REPO_ROOT = Path(__file__).resolve().parents[3]
_RULES_PATH = REPO_ROOT / "spec/CampaignLab-SDD-v1.0/fixtures/cases/rules.json"
FIXTURES = json.loads(_RULES_PATH.read_text(encoding="utf-8"))

COUPON_IDS = (
    "bc-C1-1",
    "bc-C1-2",
    "bc-C1-3",
    "bc-C2-1",
    "bc-C2-2",
    "bc-C3-1",
    "bc-C3-2",
    "bc-C3-3",
    "bc-C4-1",
    "bc-C4-2",
    "bc-C5-1",
    "bc-C5-2",
    "bc-C7-1",
    "bc-C7-2",
    "bc-C7-3",
)
CB_V1_IDS = ("bc-C8-1", "bc-C8-2")
CB_V2_IDS = ("bc-C8-1", "bc-C8-2", "bc-C8-3")
ID_COUNTS = {"CP-V1": 15, "CP-V2": 15, "CB-V1": 2, "CB-V2": 3}
CATEGORY_SET = {
    "DATE",
    "THRESHOLD",
    "BUDGET",
    "STACKING",
    "REFUND",
    "TEMPLATE",
    "SEQUENCE",
    "COMPETITION",
}
#: §4.2 实测：``CHECKS`` 注册序 C1..C9 的类别归属表。
CATEGORY_BY_ID = {
    "C1": "DATE",
    "C2": "THRESHOLD",
    "C3": "BUDGET",
    "C4": "STACKING",
    "C5": "REFUND",
    "C6": "TEMPLATE",
    "C7": "DATE",
    "C8": "SEQUENCE",
    "C9": "COMPETITION",
}


Severity = Literal["ERROR", "WARNING", "INFO"]


def _ctx(name: str, **content_overrides: Any) -> RuleContext:
    content = {**FIXTURES[name], **content_overrides}
    return RuleContext(
        rule_id=f"R-{name}",
        template=content["template"],
        content=content,
        terms=(),
        sibling_confirmed=(),
    )


def _issue_for(issues: tuple[Any, ...], code: str) -> Any:
    hits = [item for item in issues if item.code == code]
    assert len(hits) == 1, f"expected exactly one {code}, got {len(hits)}"
    return hits[0]


def test_check_framework_registers_every_check_id_exactly_once() -> None:
    assert len(checks.CHECKS) == 9 > 0
    assert len(checks.CHECK_IDS) == 9
    assert tuple(item.id for item in checks.CHECKS) == checks.CHECK_IDS
    assert len(set(checks.CHECK_IDS)) == 9
    assert {item.id: item.category for item in checks.CHECKS} == CATEGORY_BY_ID
    assert {item.category for item in checks.CHECKS} <= set(typing.get_args(checks.CheckCategory))
    assert len(checks.CHECK_ISSUE_CODES) == 23
    assert len(checks.REASON_CODE_GLOSSARY) > 0


def test_check_framework_five_ac004_categories_all_have_teeth() -> None:
    """A264：五个口径（门槛／预算／叠加／日期／退款）各造必触发输入，另设 8 项分母断言。"""
    assert set(typing.get_args(checks.CheckCategory)) == CATEGORY_SET
    assert len(CATEGORY_BY_ID) == 9
    assert {"THRESHOLD", "BUDGET", "STACKING", "DATE", "REFUND"} <= {
        CATEGORY_BY_ID[item.id] for item in checks.CHECKS
    }

    swapped = checks._check_window(
        _ctx(
            "CP-V1",
            starts_at=FIXTURES["CP-V1"]["ends_at"],
            ends_at=FIXTURES["CP-V1"]["starts_at"],
        )
    )
    item = _issue_for(swapped.issues, "WINDOW_ORDER_INVALID")  # 日期（C1 · DATE）
    assert item.severity == "ERROR"
    assert item.location == "/content/ends_at"

    threshold = checks._check_threshold(_ctx("CP-V1", coupon_fen=20000))  # 门槛（C2 · THRESHOLD）
    item = _issue_for(threshold.issues, "REWARD_EXCEEDS_THRESHOLD")
    assert item.severity == "WARNING"
    assert item.location == "/content/coupon_fen"

    budget = checks._check_budget(_ctx("CP-V1", budget_fen=0))  # 预算（C3 · BUDGET）
    item = _issue_for(budget.issues, "BUDGET_ZERO")
    assert item.severity == "ERROR"
    assert item.location == "/content/budget_fen"

    stacking = checks._check_stacking(_ctx("CP-V1"))  # 叠加（C4 · STACKING，条款未确认必触发）
    item = _issue_for(stacking.issues, "STACKING_CLAUSE_UNCONFIRMED")
    assert item.severity == "ERROR"
    assert item.location == "/terms/stacking"

    refund = checks._check_refund(_ctx("CP-V1"))  # 退款（C5 · REFUND，条款未确认必触发）
    item = _issue_for(refund.issues, "REFUND_CLAUSE_UNCONFIRMED")
    assert item.severity == "ERROR"
    assert item.location == "/terms/refund"


def test_check_state_needs_confirmation_on_unconfirmed_clause() -> None:
    def issue(severity: Severity) -> clauses.GateIssue:
        return clauses.GateIssue(code="X", location="/content/x", message="m", severity=severity)

    assert checks.check_state_of([issue("ERROR")]) == "NEEDS_CONFIRMATION"
    assert checks.check_state_of([issue("WARNING"), issue("ERROR")]) == "NEEDS_CONFIRMATION"
    assert checks.check_state_of([issue("WARNING")]) == "READY"
    assert checks.check_state_of([issue("INFO")]) == "READY"
    assert checks.check_state_of([]) == "READY"
    result = checks.run_checks(_ctx("CP-V1"))
    assert checks.check_state_of(list(result.issues)) == "NEEDS_CONFIRMATION"


def test_boundary_cases_cover_the_spec_counterexamples_per_template() -> None:
    for name in ("CP-V1", "CP-V2"):
        ids = tuple(case.id for case in checks.boundary_cases_for(_ctx(name)))
        assert ids == COUPON_IDS, name
    cb_v1 = tuple(case.id for case in checks.boundary_cases_for(_ctx("CB-V1")))
    cb_v2 = tuple(case.id for case in checks.boundary_cases_for(_ctx("CB-V2")))
    assert cb_v1 == CB_V1_IDS
    assert cb_v2 == CB_V2_IDS
    pattern = re.compile(r"^bc-C[1-9]-[0-9]+$")
    assert all(pattern.match(item) for item in COUPON_IDS + CB_V2_IDS)
    assert len(set(COUPON_IDS)) == len(COUPON_IDS)
    assert set(COUPON_IDS).isdisjoint(set(CB_V2_IDS))


def test_boundary_case_inputs_validate_against_contract() -> None:
    adapter: TypeAdapter[Any] = TypeAdapter(CaseInput)
    checked = 0
    for name in ("CP-V1", "CP-V2", "CB-V1", "CB-V2"):
        for draft in checks.boundary_cases_for(_ctx(name)):
            payload = dict(draft.input_payload)
            if "template" not in payload:
                payload = {"template": draft.template, **payload}
            adapter.validate_python(payload)
            checked += 1
    assert checked == 35
    coupon_draft = checks.boundary_cases_for(_ctx("CP-V1"))[0]
    emptied = {**dict(coupon_draft.input_payload), "events": []}
    with pytest.raises(ValidationError):
        adapter.validate_python(emptied)


def test_boundary_cases_are_deterministic_without_clock() -> None:
    def signature(context: RuleContext) -> list[Any]:
        return [
            (
                draft.id,
                draft.label,
                draft.template,
                canonical_json(dict(draft.input_payload)),
                draft.verification,
            )
            for draft in checks.boundary_cases_for(context)
        ]

    for name in ("CP-V1", "CP-V2", "CB-V1", "CB-V2"):
        assert signature(_ctx(name)) == signature(_ctx(name))


def test_boundary_case_count_never_exceeds_contract_max() -> None:
    counts = {name: len(checks.boundary_cases_for(_ctx(name))) for name in ID_COUNTS}
    assert counts == ID_COUNTS
    assert all(value <= 30 for value in counts.values())
    assert max(counts.values()) == 15 < 30
