"""M2-01/S5 · design §11.6 C：摘要固定投影（§4.6）与 ``rule_digest``（A268 三条断言）。

``canonicalize`` 一律注入 ``campaignlab.api.common.canonical_json``（A265）；
测试文件 import ``api.common`` 不构成跨层违规（``test_layering.py`` 只扫 domain 面）。
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from campaignlab.api.common import canonical_json
from campaignlab.domain.activity import digests

REPO_ROOT = Path(__file__).resolve().parents[3]
_RULES_PATH = REPO_ROOT / "spec/CampaignLab-SDD-v1.0/fixtures/cases/rules.json"
_EXAMPLES_PATH = REPO_ROOT / "spec/CampaignLab-SDD-v1.0/fixtures/api-examples.json"


def _content() -> dict[str, Any]:
    doc = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    return dict(doc["CP-V1"])


def _terms() -> tuple[dict[str, Any], ...]:
    doc = json.loads(_EXAMPLES_PATH.read_text(encoding="utf-8"))
    return tuple(dict(term) for term in doc["examples"][3]["request"]["terms"])


CONTENT = _content()
TERMS = _terms()
SOURCE = "3"


def _digest(content: Any, terms: Any, source: str | None) -> str:
    return digests.rule_digest(content, terms, source, canonicalize=canonical_json)


def test_rule_digest_projection_is_content_sorted_terms_and_source_version() -> None:
    shuffled = tuple(reversed(TERMS))
    envelope = digests.digest_projection(CONTENT, shuffled, SOURCE)
    assert set(envelope) == {"content", "terms", "source_rule_version"}
    assert envelope["content"] == dict(CONTENT)
    assert envelope["source_rule_version"] == SOURCE
    assert tuple(term["key"] for term in envelope["terms"]) == tuple(
        sorted(str(term["key"]) for term in shuffled)
    )
    none_env = digests.digest_projection(CONTENT, TERMS, None)
    assert none_env["source_rule_version"] is None


def test_rule_digest_ignores_label_and_confirmation() -> None:
    record_a: dict[str, Any] = {
        "label": "版本甲",
        "state": "DRAFT",
        "confirmed_at": None,
        "note": "",
        "digest": None,
        "content": CONTENT,
        "terms": TERMS,
        "source_rule_version": SOURCE,
    }
    record_b: dict[str, Any] = {
        "label": "版本乙（改了标签）",
        "state": "CONFIRMED",
        "confirmed_at": "2026-10-02T00:00:00+08:00",
        "note": "人工复核通过",
        "digest": "f" * 64,
        "content": dict(CONTENT),
        "terms": tuple(dict(term) for term in TERMS),
        "source_rule_version": SOURCE,
    }
    assert _digest(record_a["content"], record_a["terms"], record_a["source_rule_version"]) == (
        _digest(record_b["content"], record_b["terms"], record_b["source_rule_version"])
    )
    envelope = digests.digest_projection(record_a["content"], record_a["terms"], SOURCE)
    for noisy in ("label", "state", "confirmed_at", "note"):
        assert noisy not in envelope
    mutated = dict(CONTENT)
    mutated["coupon_fen"] = int(CONTENT["coupon_fen"]) + 1
    assert _digest(mutated, TERMS, SOURCE) != _digest(CONTENT, TERMS, SOURCE)


def test_rule_digest_is_stable_across_key_order() -> None:
    base = _digest(CONTENT, TERMS, SOURCE)
    reversed_content = dict(reversed(list(CONTENT.items())))
    assert _digest(reversed_content, TERMS, SOURCE) == base
    assert _digest(CONTENT, tuple(reversed(TERMS)), SOURCE) == base
    rotated = TERMS[2:] + TERMS[:2]
    assert _digest(CONTENT, rotated, SOURCE) == base
    assert _digest(reversed_content, rotated, "1") != _digest(CONTENT, TERMS, SOURCE)


def test_rule_digest_matches_stored_column() -> None:
    """A268：领域层钉「同一公式」＝与 ``rule_versions.digest`` 列现算自检同源。"""
    computed = _digest(CONTENT, TERMS, SOURCE)
    independent = hashlib.sha256(
        canonical_json(digests.digest_projection(CONTENT, TERMS, SOURCE)).encode("utf-8")
    ).hexdigest()
    assert computed == independent
    assert re.fullmatch(r"[0-9a-f]{64}", computed) is not None
    assert len(computed) == digests.RULE_DIGEST_LENGTH == 64
    envelope = digests.digest_projection(CONTENT, tuple(reversed(TERMS)), SOURCE)
    assert set(envelope) == {"content", "source_rule_version", "terms"}
    assert canonical_json(digests.digest_projection(CONTENT, TERMS, SOURCE)) == canonical_json(
        envelope
    )
