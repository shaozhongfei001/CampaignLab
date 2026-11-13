"""S3c：R5-1「搬移不是复制」的机器守护（ADR-005 §2.1 / D-019 / D-022）。

三组断言：

1. **同序 20 码**：``PROBLEM_CODES`` 的键序与 ``API.md`` 第 22–29 行第 2 列逐字且同序相等；
2. **单一来源**：``api/common.py`` re-export 的必须是 ``domain`` 里的**同一个对象**（``is``），
   且 ``common.py`` 源码中不得再出现任何一份定义
   （``class DomainError`` / ``PROBLEM_CODES: Final`` / ``def _new_request_id`` …）；
3. **不得扩表**：D-022 的 ``MONTHLY_*`` 与 A12 的 ``JOB_INTERRUPTED`` 一律不在注册表内。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from campaignlab.api import common
from campaignlab.domain import errors, ids
from campaignlab.domain.errors import PROBLEM_CODES, DomainError

REPO = Path(__file__).resolve().parents[2]
API_MD = REPO / "spec" / "CampaignLab-SDD-v1.0" / "architecture" / "API.md"
COMMON_PY = REPO / "src" / "campaignlab" / "api" / "common.py"

MOVED_PUBLIC = (
    "PROBLEM_CODES",
    "RESOURCE_ID_PATTERN",
    "AccessDenied",
    "DomainError",
    "IdempotencyConflict",
    "InputTooLarge",
    "InternalFailure",
    "InvalidScope",
    "JobCapacity",
    "OriginDenied",
    "PreconditionRequired",
    "ResourceNotFound",
    "RevisionConflict",
    "SessionInvalid",
    "StateConflict",
    "ValidationFailure",
    "problem_type",
    "status_to_code",
)

#: 搬移后 ``common.py`` 里**不得**再出现这些定义形态（只允许 import / re-export / 调用）。
FORBIDDEN_DEFINITIONS = (
    r"^class DomainError\b",
    r"^class (SessionInvalid|OriginDenied|AccessDenied|ResourceNotFound|IdempotencyConflict)\b",
    r"^class (StateConflict|RevisionConflict|PreconditionRequired|InputTooLarge)\b",
    r"^class (ValidationFailure|InvalidScope|JobCapacity|InternalFailure)\b",
    r"^PROBLEM_CODES\s*:",
    r"^_STATUS_BY_CODE\s*:",
    r"^_TITLE_BY_CODE\s*:",
    r"^_STATUS_TO_CODE\s*:",
    r"^RESOURCE_ID_PATTERN\s*:",
    r"^def problem_type\b",
    r"^def status_to_code\b",
    r"^def _build_registry\b",
    r"^def _invert_status\b",
    r"^def _new_request_id\b",
)


def spec_codes_from_api_md() -> list[str]:
    """逐行提取 API.md 第 22–29 行第 2 列（以「、」分隔），共 20 个（D-019）。"""
    lines = API_MD.read_text(encoding="utf-8").split("\n")
    codes: list[str] = []
    for line in lines[21:29]:
        columns = line.split("|")
        for cell in columns[2].split("、"):
            name = cell.strip()
            if name:
                codes.append(name)
    return codes


def test_registry_has_exactly_twenty_codes_in_spec_order() -> None:
    assert spec_codes_from_api_md() == list(PROBLEM_CODES)
    assert len(PROBLEM_CODES) == 20


def test_registry_entries_are_status_type_title_triples() -> None:
    for code, entry in PROBLEM_CODES.items():
        status, type_uri, title = entry
        assert isinstance(status, int) and 400 <= status <= 599
        assert type_uri == "urn:campaignlab:problem:" + code.lower()
        assert isinstance(title, str) and title


def test_subclass_default_codes_map_to_declared_status() -> None:
    expected = {
        errors.SessionInvalid: ("SESSION_EXPIRED", 401),
        errors.OriginDenied: ("ORIGIN_DENIED", 403),
        errors.AccessDenied: ("ACCESS_DENIED", 403),
        errors.ResourceNotFound: ("RESOURCE_NOT_FOUND", 404),
        errors.IdempotencyConflict: ("IDEMPOTENCY_CONFLICT", 409),
        errors.StateConflict: ("STATE_CONFLICT", 409),
        errors.RevisionConflict: ("REVISION_CONFLICT", 412),
        errors.PreconditionRequired: ("PRECONDITION_REQUIRED", 428),
        errors.InputTooLarge: ("INPUT_TOO_LARGE", 413),
        errors.ValidationFailure: ("VALIDATION_ERROR", 422),
        errors.InvalidScope: ("INVALID_SCOPE", 422),
        errors.JobCapacity: ("JOB_CAPACITY", 429),
        errors.InternalFailure: ("INTERNAL_ERROR", 500),
    }
    assert len(expected) == 13, "DomainError 子类必须是 13 个（R5-1 硬规则）"
    for cls, (code, status) in expected.items():
        instance = cls()
        assert isinstance(instance, DomainError)
        assert instance.code == code
        assert instance.status == status
        assert instance.title == PROBLEM_CODES[code][2]


def test_unregistered_code_is_rejected_at_construction() -> None:
    """ADR-005 §2.1：任何新增 code 必须先进注册表再使用。"""
    with pytest.raises(KeyError):
        DomainError("x", code="NOT_A_REAL_CODE")


@pytest.mark.parametrize(
    "code", ["MONTHLY_INVALID_SCOPE", "MONTHLY_REPORT_KIND_REQUIRED", "JOB_INTERRUPTED"]
)
def test_forbidden_codes_are_not_in_registry(code: str) -> None:
    """D-022（OPEN）与 A12：这三个都不是 ``Problem.code``，禁扩表。"""
    assert code not in PROBLEM_CODES


def test_common_reexports_the_same_objects_not_a_second_copy() -> None:
    for name in MOVED_PUBLIC:
        left = getattr(common, name)
        right = getattr(errors, name, None) or getattr(ids, name)
        assert left is right, f"{name} 不是同一对象 —— 说明存在第二份定义"


def test_private_registry_names_are_also_single_sourced() -> None:
    """私有名同样只有一份定义（用 getattr 绕过 mypy 的 no-implicit-reexport）。"""
    pairs: tuple[tuple[str, object], ...] = (
        ("_STATUS_BY_CODE", errors._STATUS_BY_CODE),
        ("_TITLE_BY_CODE", errors._TITLE_BY_CODE),
        ("_STATUS_TO_CODE", errors._STATUS_TO_CODE),
        ("_build_registry", errors._build_registry),
        ("_invert_status", errors._invert_status),
        ("_new_request_id", ids.new_request_id),
    )
    for name, target in pairs:
        assert getattr(common, name) is target, f"{name} 不是同一对象 —— 存在第二份定义"


def test_common_py_contains_no_moved_definition() -> None:
    text = COMMON_PY.read_text(encoding="utf-8")
    offenders: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for pattern in FORBIDDEN_DEFINITIONS:
            if re.match(pattern, line):
                offenders.append(f"{lineno}:{line.strip()[:60]}")
    assert offenders == [], f"api/common.py 仍有搬移对象的定义（两处各存一份）：{offenders}"


def test_common_public_surface_is_unchanged() -> None:
    """搬移前后 ``__all__`` 必须逐字相同：51 项、全部可解析、20 码全在其中。"""
    assert len(common.__all__) == 51
    assert len(set(common.__all__)) == 51
    for name in common.__all__:
        assert hasattr(common, name), f"__all__ 声明了但取不到：{name}"
    assert set(MOVED_PUBLIC) <= set(common.__all__)


def test_domain_ids_helpers() -> None:
    assert ids.is_resource_id("ws-1_a.b:c")
    assert not ids.is_resource_id("_lead")
    assert not ids.is_resource_id("has space")
    assert not ids.is_resource_id("trailing-newline\n"), (
        "`$` + match 会放过末尾换行，必须 fullmatch"
    )
    generated = ids.new_resource_id("ws")
    assert generated.startswith("ws-") and ids.is_resource_id(generated)
    with pytest.raises(ValueError):
        ids.new_resource_id("bad prefix")
    assert len(ids.new_request_id()) == 32
