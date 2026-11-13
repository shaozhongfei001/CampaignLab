"""S3c：``evidence/M0/M0-02/problem-code-registry.json`` 只读快照的一致性。

M0-03 卡 Q4 / RULING_NO_FRONTEND_MIRROR：前端 S8 **参数化读本快照**，禁镜像一份 code 白名单。
因此本快照必须与 ``domain/errors.py::PROBLEM_CODES``（唯一来源）逐字节对齐，
且必须是 UTF-8 **无 BOM**、LF 换行——BOM 会让前端 ``JSON.parse`` 直接抛错（本项目踩过 BOM 坑）。
"""

from __future__ import annotations

import json
from pathlib import Path

from campaignlab.domain.errors import PROBLEM_CODES

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / "evidence" / "M0" / "M0-02" / "problem-code-registry.json"
API_MD = REPO / "spec" / "CampaignLab-SDD-v1.0" / "architecture" / "API.md"


def load_snapshot() -> dict[str, object]:
    result: dict[str, object] = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return result


def test_snapshot_is_utf8_without_bom_and_lf_only() -> None:
    raw = REGISTRY.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "快照不得带 UTF-8 BOM"
    assert b"\r" not in raw, "快照必须是 LF 换行"
    assert raw.endswith(b"\n")


def test_snapshot_codes_match_registry_exactly_and_in_order() -> None:
    snapshot = load_snapshot()
    codes = snapshot["codes"]
    assert isinstance(codes, list)
    assert snapshot["count"] == len(codes) == len(PROBLEM_CODES) == 20
    assert [item["code"] for item in codes] == list(PROBLEM_CODES)
    for item in codes:
        code = str(item["code"])
        status, type_uri, title = PROBLEM_CODES[code]
        assert item["status"] == status
        assert item["type"] == type_uri
        assert item["title"] == title


def test_snapshot_matches_api_md_twenty_codes() -> None:
    lines = API_MD.read_text(encoding="utf-8").split("\n")
    spec_codes: list[str] = []
    for line in lines[21:29]:
        for cell in line.split("|")[2].split("、"):
            if cell.strip():
                spec_codes.append(cell.strip())
    snapshot = load_snapshot()
    codes = snapshot["codes"]
    assert isinstance(codes, list)
    assert [item["code"] for item in codes] == spec_codes
    assert len(spec_codes) == 20


def test_snapshot_declares_single_source_and_no_frontend_mirror() -> None:
    snapshot = load_snapshot()
    assert snapshot["kind"] == "read-only-snapshot"
    assert snapshot["single_source_of_truth"] == "src/campaignlab/domain/errors.py :: PROBLEM_CODES"
    assert snapshot["type_scheme"] == "urn:campaignlab:problem:<code.lower()>"
    assert "NO_FRONTEND_MIRROR" in str(snapshot["frontend_policy"])


def test_snapshot_records_excluded_codes() -> None:
    snapshot = load_snapshot()
    excluded = snapshot["excluded"]
    assert isinstance(excluded, dict)
    assert set(excluded) == {
        "MONTHLY_INVALID_SCOPE",
        "MONTHLY_REPORT_KIND_REQUIRED",
        "JOB_INTERRUPTED",
    }
    for name in excluded:
        assert name not in PROBLEM_CODES
