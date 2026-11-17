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
from typing import Final

import pytest

from campaignlab.api import common
from campaignlab.domain import errors, ids
from campaignlab.domain.errors import PROBLEM_CODES, DomainError

REPO = Path(__file__).resolve().parents[2]
API_MD = REPO / "spec" / "CampaignLab-SDD-v1.0" / "architecture" / "API.md"
COMMON_PY = REPO / "src" / "campaignlab" / "api" / "common.py"

#: common-surface-live-collision（A292 / A115）：公开面的**显式名单**，
#: 由 `common.__all__` 实取生成（程序化派生，禁手打 —— PRE-37 第 1 款）。
#: 以「名单对撞」替代 A115 禁止的「写死项数」：公开面任何增减都必须在本名单里增删对应名字，
#: 于是 diff 直接显示**加了/删了哪个符号**，而不是只显示一个数字从 80 变 81；且全仓**单点**
#: ⇒ 根除 R19-10 的「多处各写一份、只改了自己扫到的那一处」的分叉面。
COMMON_ALL_NAMES: Final = (
    "AccessDenied",
    "Activity",
    "ActivityCreate",
    "ActivityPage",
    "ActivityStatus",
    "ActivityUpdate",
    "Binding",
    "BoundaryCase",
    "CURSOR_MAX_LENGTH",
    "CallbackCaseInput",
    "CallbackEvent",
    "CallbackRule",
    "CaseInput",
    "Confirmation",
    "CouponCaseInput",
    "CouponEvent",
    "CouponRule",
    "DomainError",
    "FieldChange",
    "Health",
    "IDEMPOTENCY_KEY_HEADER",
    "IDEMPOTENCY_KEY_MAX_LENGTH",
    "IDEMPOTENCY_KEY_MIN_LENGTH",
    "IF_MATCH_PATTERN",
    "IdempotencyConflict",
    "InputTooLarge",
    "InternalFailure",
    "InvalidScope",
    "Issue",
    "Job",
    "JobCapacity",
    "JobPage",
    "ObjectRef",
    "OriginDenied",
    "OriginHostGuard",
    "PROBLEM_CODES",
    "PROBLEM_MEDIA_TYPE",
    "PreconditionRequired",
    "Problem",
    "RESOURCE_ID_PATTERN",
    "ResourceNotFound",
    "RevisionConflict",
    "RuleCheck",
    "RuleCheckState",
    "RuleContent",
    "RuleCreate",
    "RuleDiff",
    "RuleState",
    "RuleUpdate",
    "RuleVersion",
    "RuleVersionPage",
    "Session",
    "SessionExchange",
    "SessionInvalid",
    "StateConflict",
    "TemplateId",
    "Term",
    "UNSAFE_METHODS",
    "ValidationFailure",
    "Workspace",
    "WorkspaceCreate",
    "WorkspacePage",
    "X_REQUEST_ID_HEADER",
    "accepted_response",
    "canonical_json",
    "check_if_match",
    "decode_cursor",
    "encode_cursor",
    "etag",
    "idempotency_envelope",
    "install_error_handlers",
    "loopback_allowlists",
    "problem_response",
    "problem_type",
    "read_body_within_limit",
    "replay_from_envelope",
    "request_digest",
    "request_id_middleware",
    "status_to_code",
    "validate_idempotency_key",
)


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
    """``api/common.py`` 公开面钉桩：``__all__`` 项数、全部可解析、20 码全在其中。

    78 是 **M2-01/S2a 追加 DTO 面之后的实测值**（51 → 78，净增 27）；依 A218 采用设计文档 §11.2
    的「按新实取值更新」口径。按 D-012/D-014，引用计数必须给归因，故本行数字**只在公开面再次变更时**
    才允许改动，且须同批过账。**79 → 80 的归因（D-012/D-014）**：FU-59 / A271 解冻批在
    ``api/common.py`` 新增 HTTP 常量 ``IF_MATCH_PATTERN``（If-Match 正则的全仓单源，值逐字
    镜像活契约）并纳入 ``__all__``；同批把 ``api/activities.py`` 1 处 ＋ ``api/jobs.py`` 2 处
    ＋ ``api/rules.py`` 2 处的内联字面量改为 import 该常量，守护落在
    ``tests/unit/test_if_match_pattern_single_source.py``。
    函数名沿用历史（初版语义＝「搬移前后不变」），现语义已升级为
    「公开面任何增减都必须在本用例显式过账」—— D-044 修正了原名/原 docstring 与断言体自相矛盾之处。

    **A292 口径迁移（订正 A281）**：上文「78 / 79 → 80」的归因段是
    **历史留档、逐字不改写**（D-011），
    但其描述的「钉死项数」形态已**废止** —— A115 本就禁止写死符号面计数，而元守护
    ``test_all_common_surface_pins_agree_with_runtime`` 的下界制（钉桩处数 >= 2）与 A115 不可兼得：
    全仓硬编码计数钉桩实测**只有 2 处**、恰是本用例的这两行，去掉魔数即「分母塌陷」判红、
    保留魔数即违 A115。故同批把元守护迁移为**上限制 ＋ 实取对撞下界制**（见
    ``tests/unit/test_if_match_pattern_single_source.py`` 判据 4），
    本用例改为与 ``COMMON_ALL_NAMES``
    显式名单对撞。上文首句「``__all__`` 项数、全部可解析、20 码全在其中」里的「项数」一项，
    自本迁移起读作「**名单**」（语义更强：钉的是名字集合而非其基数）。
    """
    # common-surface-live-collision（A292：实取对撞，禁写死项数 —— A115）
    assert set(common.__all__) == set(COMMON_ALL_NAMES), (
        "api/common.py 的公开面与本用例的显式名单分叉 —— 公开面任何增减都必须**同批**在"
        " `COMMON_ALL_NAMES` 里过账（D-012 / D-014 归因）："
        f"only_runtime={sorted(set(common.__all__) - set(COMMON_ALL_NAMES))} "
        f"only_pinned={sorted(set(COMMON_ALL_NAMES) - set(common.__all__))}"
    )
    assert len(set(common.__all__)) == len(common.__all__), "__all__ 内有重复声明"
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
