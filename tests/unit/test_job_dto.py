"""M0-04/S7：Job DTO 与活契约的双向一致性（design §9-S7，7 个函数逐字落地）。

判据来源（一律**只读**）：

* 契约真值：``orchestrator/handoff/M0-04.slice.json`` 的 ``operations.<opId>.schemas.*``。
  该切片由 ``scripts/contract_slice.py`` 以 depth=5 展开，``truncated_schemas == []``；
  本文件**不整读** 443KB 的 ``contracts/openapi.json``，也不读 ``spec/**``。
* DTO 真值：``campaignlab.api.common`` 的 4 个 DTO（``extra="forbid"``）。
* 枚举与 ``retryable_for`` 真值：``campaignlab.worker.states``。
* 20 码注册表真值：``campaignlab.domain.errors.PROBLEM_CODES``。

假绿防护：枚举、必填清单、注册表 code 集一律**双向**比对（代码 ⊆ 契约 **且** 契约 ⊆ 代码），
并在每条比对上追加一次「构造非法值必须 ``ValidationError``」的反向取证——单向 ``issubset``
在契约被截空时会恒真，本文件不接受这种绿。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final, cast, get_args

import pytest
from pydantic import ValidationError

from campaignlab.api.common import Issue, Job, JobKind, JobState, ObjectKind, ObjectRef, Problem
from campaignlab.domain.errors import PROBLEM_CODES, problem_type
from campaignlab.worker.states import (
    JOB_KINDS,
    JOB_STATES,
    NON_RETRYABLE_PROBLEM_CODES,
    retryable_for,
)

REPO: Final[Path] = Path(__file__).resolve().parents[2]
SLICE: Final[Path] = REPO / "orchestrator" / "handoff" / "M0-04.slice.json"
JOB_OPS: Final[tuple[str, ...]] = ("listJobs", "getJob", "cancelJob", "retryJob")

#: 租约字段的在册命名（DDL 列名 + 常见的同族写法）；HTTP 体的 Job DTO 一个都不许有。
LEASE_LIKE_FIELDS: Final[tuple[str, ...]] = (
    "lease_token",
    "lease_until",
    "lease_owner",
    "lease_expires_at",
    "lease_renewed_at",
)

#: 永久性输入缺陷（API.md 错误分类表口径）；与 ``states.NON_RETRYABLE_PROBLEM_CODES`` 双向比对。
SPEC_NON_RETRYABLE_CODES: Final[frozenset[str]] = frozenset(
    {"EVIDENCE_REQUIRED", "INPUT_TOO_LARGE", "INVALID_SCOPE", "VALIDATION_ERROR"}
)

#: 20 码注册表的本卡冻结期望（多一个少一个都判红）。
EXPECTED_20_CODES: Final[tuple[str, ...]] = (
    "BAD_REQUEST",
    "BAD_CURSOR",
    "SESSION_EXPIRED",
    "ORIGIN_DENIED",
    "ACCESS_DENIED",
    "RESOURCE_NOT_FOUND",
    "IDEMPOTENCY_CONFLICT",
    "STATE_CONFLICT",
    "VERSION_MISMATCH",
    "STALE_CANDIDATE",
    "SNAPSHOT_CONFLICT",
    "ACTION_REVIEW_REQUIRED",
    "REVISION_CONFLICT",
    "PRECONDITION_REQUIRED",
    "INPUT_TOO_LARGE",
    "VALIDATION_ERROR",
    "INVALID_SCOPE",
    "EVIDENCE_REQUIRED",
    "JOB_CAPACITY",
    "INTERNAL_ERROR",
)


def _slice_data() -> dict[str, Any]:
    assert SLICE.is_file(), f"契约切片缺失：{SLICE}"
    data = cast("dict[str, Any]", json.loads(SLICE.read_text(encoding="utf-8")))
    assert data["truncated_schemas"] == [], "切片存在未展开的 schema，不能当契约真值"
    return data


def _schema(name: str) -> dict[str, Any]:
    """定点取切片里的一个 schema，并要求四个 jobs operation 的副本逐字一致。"""
    ops = _slice_data()["operations"]
    copies = [cast("dict[str, Any]", ops[op]["schemas"][name]) for op in JOB_OPS]
    assert all(copy == copies[0] for copy in copies[1:]), f"{name} 的切片副本不一致"
    return copies[0]


def _ddl_jobs() -> str:
    ddl = cast("dict[str, Any]", _slice_data()["ddl"])["jobs"]
    assert isinstance(ddl, str), "ddl.jobs 必须是建表 SQL 文本"
    return ddl


def _names(value: Any, label: str) -> set[str]:
    assert isinstance(value, (list, tuple)), f"{label} 不是字符串数组"
    assert all(isinstance(item, str) for item in value), f"{label} 含非字符串项"
    return {str(item) for item in value}


def _contract_required(schema: dict[str, Any], label: str) -> set[str]:
    return _names(schema["required"], f"{label}.required")


def _contract_enum(schema: dict[str, Any], field: str) -> set[str]:
    prop = schema["properties"][field]
    assert isinstance(prop, dict), f"{field} 属性不是对象"
    enum = prop.get("enum")
    assert enum is not None, f"契约 {field} 无 enum，不能作枚举真值"
    return _names(enum, f"{field}.enum")


def _job_payload(**overrides: object) -> dict[str, object]:
    """一份逐字段合法的 Job 体（13 字段，与契约 required 同集）。"""
    payload: dict[str, object] = {
        "id": "job_01",
        "revision": 1,
        "created_at": "2026-11-14T10:00:00+08:00",
        "kind": "COMPARE",
        "state": "QUEUED",
        "attempt": 0,
        "progress": 0,
        "stage": "QUEUED",
        "input_digest": "0" * 64,
        "retry_of": None,
        "result_ref": None,
        "problem": None,
        "retryable": False,
    }
    payload.update(overrides)
    return payload


def test_job_dto_matches_live_schema_13_required() -> None:
    contract = _schema("Job")
    required = _contract_required(contract, "Job")
    dto_fields = set(Job.model_fields)
    assert len(required) == 13, f"契约 Job.required 应为 13 项，实为 {sorted(required)}"
    # 双向：DTO ⊆ 契约、契约 ⊆ DTO
    assert not dto_fields - required, f"DTO 多出契约未要求的字段：{sorted(dto_fields - required)}"
    assert not required - dto_fields, f"DTO 缺契约必填字段：{sorted(required - dto_fields)}"
    props_prop = contract["properties"]
    assert isinstance(props_prop, dict), "契约 Job.properties 不是对象"
    props = set(props_prop)
    assert props == required, "契约 Job.properties 与 required 不同集（存在可选漏网字段）"
    # additionalProperties:false <-> extra="forbid"
    assert contract.get("additionalProperties") is False
    assert Job.model_config.get("extra") == "forbid"
    job = Job.model_validate(_job_payload())
    assert set(job.model_dump()) == required
    with pytest.raises(ValidationError):
        Job.model_validate(_job_payload(not_in_contract=1))


def test_job_dto_forbids_lease_fields() -> None:
    contract = _schema("Job")
    leaked = sorted(name for name in contract["properties"] if "lease" in name.lower())
    assert leaked == [], f"契约 Job.properties 含租约字段：{leaked}"
    ddl = _ddl_jobs()
    assert "lease_token" in ddl and "lease_until" in ddl, "租约列应只活在 DDL 层"
    for field in LEASE_LIKE_FIELDS:
        assert field not in Job.model_fields, f"DTO 泄露租约字段 {field}"
        with pytest.raises(ValidationError):
            Job.model_validate(_job_payload(**{field: "2026-11-14T10:05:00+08:00"}))


def test_state_enum_is_6_values() -> None:
    contract_states = _contract_enum(_schema("Job"), "state")
    code_states = _names(JOB_STATES, "JOB_STATES")
    assert len(contract_states) == 6
    assert len(code_states) == 6
    assert not code_states - contract_states, (
        f"代码多出契约外状态：{sorted(code_states - contract_states)}"
    )
    assert not contract_states - code_states, (
        f"代码缺契约状态：{sorted(contract_states - code_states)}"
    )
    assert set(get_args(JobState)) == code_states, "Literal 与 JOB_STATES 不同源"
    ddl = _ddl_jobs()
    assert all(f"'{state}'" in ddl for state in contract_states), "DDL CHECK 与契约枚举漂移"
    with pytest.raises(ValidationError):
        Job.model_validate(_job_payload(state="LEASED"))


def test_kind_enum_is_10_values() -> None:
    contract_kinds = _contract_enum(_schema("Job"), "kind")
    code_kinds = _names(JOB_KINDS, "JOB_KINDS")
    assert len(contract_kinds) == 10
    assert len(code_kinds) == 10
    assert not code_kinds - contract_kinds, (
        f"代码多出契约外 kind：{sorted(code_kinds - contract_kinds)}"
    )
    assert not contract_kinds - code_kinds, (
        f"代码缺契约 kind：{sorted(contract_kinds - code_kinds)}"
    )
    assert set(get_args(JobKind)) == code_kinds, "Literal 与 JOB_KINDS 不同源"
    with pytest.raises(ValidationError):
        Job.model_validate(_job_payload(kind="MIGRATE"))


def test_objectref_kind_enum() -> None:
    contract = _schema("ObjectRef")
    contract_kinds = _contract_enum(contract, "kind")
    code_kinds = _names(get_args(ObjectKind), "ObjectKind")
    assert len(contract_kinds) == 20
    assert not code_kinds - contract_kinds, (
        f"代码多出契约外 ObjectKind：{sorted(code_kinds - contract_kinds)}"
    )
    assert not contract_kinds - code_kinds, (
        f"代码缺契约 ObjectKind：{sorted(contract_kinds - code_kinds)}"
    )
    required = _contract_required(contract, "ObjectRef")
    assert required == {"kind", "id"}
    assert set(ObjectRef.model_fields) == required
    assert contract.get("additionalProperties") is False
    assert ObjectRef.model_config.get("extra") == "forbid"
    assert ObjectRef.model_validate({"kind": "job", "id": "job_01"}).kind == "job"
    with pytest.raises(ValidationError):
        ObjectRef.model_validate({"kind": "lease", "id": "job_01"})
    with pytest.raises(ValidationError):
        ObjectRef.model_validate({"kind": "job", "id": "job_01", "lease_until": "x"})


@pytest.mark.parametrize("state", JOB_STATES)
@pytest.mark.parametrize("kind", JOB_KINDS)
def test_retryable_matrix(state: str, kind: str) -> None:
    """6 状态 × 10 kind × (20 code + None) 的全矩阵，禁只测几个点。"""
    assert NON_RETRYABLE_PROBLEM_CODES == SPEC_NON_RETRYABLE_CODES
    assert set(JOB_STATES) == set(_contract_enum(_schema("Job"), "state"))
    for problem_code in (None, *sorted(PROBLEM_CODES)):
        permanent = problem_code is not None and problem_code in SPEC_NON_RETRYABLE_CODES
        expected = state == "CANCELLED" or (state == "FAILED" and not permanent)
        assert retryable_for(state, problem_code) is expected, (state, kind, problem_code)
    Job.model_validate(_job_payload(state=state, kind=kind))


def test_problem_code_all_in_registry_20() -> None:
    registry = tuple(PROBLEM_CODES)
    assert len(registry) == 20, f"注册表必须恰为 20 码，实为 {len(registry)}"
    assert len(set(registry)) == 20
    assert not set(registry) - set(EXPECTED_20_CODES), (
        f"注册表多出：{sorted(set(registry) - set(EXPECTED_20_CODES))}"
    )
    assert not set(EXPECTED_20_CODES) - set(registry), (
        f"注册表缺失：{sorted(set(EXPECTED_20_CODES) - set(registry))}"
    )
    assert registry == EXPECTED_20_CODES, "注册表顺序与 API.md 错误分类表漂移"
    contract = _schema("Problem")
    assert _contract_required(contract, "Problem") == set(Problem.model_fields)
    assert set(Issue.model_fields) == _contract_required(_schema("Issue"), "Issue")
    assert _contract_enum(_schema("Issue"), "severity") == set(
        get_args(Issue.model_fields["severity"].annotation)
    )
    code_prop = contract["properties"]["code"]
    assert isinstance(code_prop, dict)
    status_prop = contract["properties"]["status"]
    type_prop = contract["properties"]["type"]
    assert isinstance(status_prop, dict) and isinstance(type_prop, dict)
    enum = code_prop.get("enum")
    if enum is not None:
        assert _names(enum, "Problem.code.enum") == set(registry)
    else:
        # U 项：活契约未把 Problem.code 收紧为 enum，故改为逐码校验契约约束（禁发明第 21 码）。
        pattern = re.compile(str(code_prop["pattern"]))
        for code in registry:
            status, type_uri, title = PROBLEM_CODES[code]
            assert pattern.match(code), f"{code} 不合契约 code.pattern"
            assert 1 <= len(code) <= int(code_prop["maxLength"])
            assert status <= int(status_prop["maximum"])
            assert len(type_uri) <= int(type_prop["maxLength"])
            assert problem_type(code) == type_uri and title
            Problem.model_validate(
                {
                    "type": type_uri,
                    "title": title,
                    "status": status,
                    "code": code,
                    "detail": "契约一致性取证",
                    "request_id": "req_01",
                    "issues": [],
                }
            )
        with pytest.raises(ValidationError):
            Problem.model_validate(
                {
                    "type": problem_type("NOT_A_REGISTRY_CODE"),
                    "title": "x",
                    "status": 400,
                    "code": "NOT A CODE",
                    "detail": "d",
                    "request_id": "r",
                    "issues": [],
                }
            )
