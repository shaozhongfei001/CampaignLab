"""M2-01/S5 · design §11.6 D：绑定有效期（A198 起含止排）与绑定门禁。

纯领域层：``validate_bindings`` 只吃 ``BindingDraft`` 序列与已登记证据集合。
"""

from __future__ import annotations

from datetime import date
from typing import Any

from campaignlab.domain.activity import bindings

EV_OK = "EV-BIND-OK"
S101 = "S-101"


def _draft(
    *,
    strategy: str = S101,
    source: str = "1",
    start: date = date(2026, 10, 1),
    until: date = date(2026, 11, 1),
    evidence: str = EV_OK,
) -> bindings.BindingDraft:
    return bindings.BindingDraft(
        strategy_id=strategy,
        source_version=source,
        valid_from=start,
        valid_until=until,
        evidence_id=evidence,
    )


def _validate(*drafts: bindings.BindingDraft, registered: Any = (EV_OK,)) -> tuple[Any, ...]:
    return bindings.validate_bindings(drafts=drafts, registered_evidence_ids=tuple(registered))


def test_binding_interval_is_start_inclusive_end_exclusive() -> None:
    early = _draft(start=date(2026, 10, 1), until=date(2026, 10, 5))
    touching = _draft(start=date(2026, 10, 5), until=date(2026, 10, 9))
    assert bindings.intervals_intersect(early, touching) is False
    assert bindings.intervals_intersect(touching, early) is False
    partial = _draft(start=date(2026, 10, 4), until=date(2026, 10, 9))
    assert bindings.intervals_intersect(early, partial) is True
    assert bindings.intervals_intersect(partial, early) is True
    inside = _draft(start=date(2026, 10, 2), until=date(2026, 10, 3))
    assert bindings.intervals_intersect(early, inside) is True
    assert bindings.intervals_intersect(early, early) is True
    leading = _draft(start=date(2026, 9, 1), until=date(2026, 10, 1))
    assert bindings.intervals_intersect(leading, early) is False


def test_binding_empty_interval_is_rejected() -> None:
    for until in (date(2026, 10, 1), date(2026, 9, 30)):
        issues = _validate(_draft(start=date(2026, 10, 1), until=until))
        assert len(issues) == 1
        assert issues[0].code == "BINDING_EMPTY_INTERVAL"
        assert issues[0].location == "/bindings/0/valid_until"
        assert issues[0].severity == "ERROR"


def test_binding_overlap_is_rejected() -> None:
    first = _draft(start=date(2026, 10, 1), until=date(2026, 10, 10))
    second = _draft(start=date(2026, 10, 5), until=date(2026, 10, 20))
    issues = _validate(first, second)
    assert [item.code for item in issues] == ["BINDING_OVERLAP", "BINDING_OVERLAP"]
    assert [item.location for item in issues] == [
        "/bindings/0/valid_from",
        "/bindings/1/valid_from",
    ]
    assert all(item.severity == "ERROR" for item in issues)
    other = _draft(strategy="S-202", start=date(2026, 10, 5), until=date(2026, 10, 20))
    assert _validate(first, other) == ()


def test_binding_duplicate_key_is_rejected() -> None:
    first = _draft(start=date(2026, 10, 1), until=date(2026, 10, 10))
    twin = _draft(start=date(2026, 10, 1), until=date(2026, 10, 10))
    issues = _validate(first, twin)
    codes = sorted(item.code for item in issues)
    assert codes == ["BINDING_DUPLICATE_KEY", "BINDING_OVERLAP", "BINDING_OVERLAP"]
    dup = [item for item in issues if item.code == "BINDING_DUPLICATE_KEY"]
    assert len(dup) == 1
    assert dup[0].location == "/bindings/1"
    assert dup[0].severity == "ERROR"
    same_key_other_until = _draft(start=date(2026, 10, 1), until=date(2026, 10, 3))
    assert any(
        item.code == "BINDING_DUPLICATE_KEY" for item in _validate(first, same_key_other_until)
    )


def test_binding_evidence_must_be_registered() -> None:
    draft = _draft(evidence="EV-NOT-IN-REGISTRY")
    issues = _validate(draft, registered=())
    assert len(issues) == 1
    assert issues[0].code == "BINDING_EVIDENCE_UNREGISTERED"
    assert issues[0].location == "/bindings/0/evidence_id"
    assert issues[0].severity == "ERROR"
    assert "EV-NOT-IN-REGISTRY" not in issues[0].message
    assert _validate(_draft(evidence=EV_OK), registered=(EV_OK,)) == ()


def test_binding_sort_key_is_frozen() -> None:
    late = _draft(strategy="S-101", source="2", start=date(2026, 10, 20), until=date(2026, 11, 1))
    early = _draft(strategy="S-090", source="9", start=date(2026, 10, 1), until=date(2026, 10, 5))
    tie_b = _draft(strategy="S-101", source="b", start=date(2026, 10, 1), until=date(2026, 10, 9))
    tie_a = _draft(strategy="S-101", source="a", start=date(2026, 10, 1), until=date(2026, 10, 9))
    ordered = sorted([late, tie_b, early, tie_a], key=bindings.BINDING_SORT_KEY)
    assert ordered == [early, tie_a, tie_b, late]
    for draft in (early, tie_a, tie_b, late):
        assert bindings.BINDING_SORT_KEY(draft) == (
            draft.valid_from,
            draft.strategy_id,
            draft.source_version,
        )
    assert sorted([late, early], key=bindings.BINDING_SORT_KEY) == [early, late]
    assert sorted([late, early], key=bindings.BINDING_SORT_KEY)[0] is early
