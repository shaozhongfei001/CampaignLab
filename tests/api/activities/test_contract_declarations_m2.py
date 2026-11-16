"""M2-01/S6 · 声明面契约对撞（裁定 A257 授权：M2-01 切片的对撞归本棒、本文件）。

**为什么不是** ``tests/api/test_contract_declarations.py`` 的追加：该文件绑定 **M0-02** 切片且
自身明载 N5 禁第二真源（A257）⇒ M2-01 十一 op 的「实现声明 == 切片声明」在本目录新建文件落。
状态码集合的唯一权威仍是路由装饰器 ``declared_responses()``（A95）；期望值一律从
``orchestrator/handoff/M2-01.slice.json`` **实取**，禁写死码表；错误码一律反查
``domain/errors.py::PROBLEM_CODES``（禁自造码）。体例照 ``_CODES_USED_BY_THIS_DIRECTORY``。
"""

from __future__ import annotations

from typing import Final

from campaignlab.domain.errors import PROBLEM_CODES
from tests.api.activities.conftest import SLICE, m2_routes

#: 本目录（六个测试文件）实际断言过的 Problem 码，必须**全部**来自 20 码注册表（禁自造码）。
_CODES_USED_BY_THIS_DIRECTORY: Final = (
    "BAD_CURSOR",
    "EVIDENCE_REQUIRED",
    "IDEMPOTENCY_CONFLICT",
    "PRECONDITION_REQUIRED",
    "RESOURCE_NOT_FOUND",
    "REVISION_CONFLICT",
    "STATE_CONFLICT",
    "VALIDATION_ERROR",
    "VERSION_MISMATCH",
    # §6.6 断言「不可达本身」的五个码同样来自注册表（test_conflicts 引用）。
    "ACTION_REVIEW_REQUIRED",
    "INVALID_SCOPE",
    "JOB_CAPACITY",
    "SNAPSHOT_CONFLICT",
    "STALE_CANDIDATE",
)


def _slice_responses(operation_id: str) -> set[str]:
    declared = SLICE["operations"][operation_id]["operation"]["responses"]
    return {str(status) for status in declared}


def test_declared_responses_match_the_slice_for_all_eleven_ops() -> None:
    """A95 硬约束逐 op：实现侧 ``route.responses`` 码集 == 切片声明码集（2xx 子集另对撞）。"""
    routes = m2_routes()
    slice_ops = set(SLICE["operations"])
    assert routes, "分母哨兵：实现侧路由枚举不得为空"
    assert set(routes) == slice_ops, "实现面与切片面的 operationId 集合必须逐字相等"
    for operation_id, route in sorted(routes.items()):
        implemented = {str(status) for status in route.responses}
        expected = _slice_responses(operation_id)
        assert implemented == expected, operation_id
        assert len(implemented) == len(expected), operation_id
        implemented_2xx = {status for status in implemented if 200 <= int(status) < 300}
        expected_2xx = {status for status in expected if 200 <= int(status) < 300}
        assert implemented_2xx == expected_2xx, operation_id


def _camel(function_name: str) -> str:
    """snake 函数名到 camel operationId：design §1 「逐字对应」＝ ``list_jobs/listJobs`` 对。"""
    head, *rest = function_name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def test_operation_id_matches_function_name_for_all_eleven_ops() -> None:
    """design §1：函数名与 operationId 逐字对应（装饰器显式给 ``operation_id`` 的形态自证）。"""
    routes = m2_routes()
    assert set(routes) == set(SLICE["operations"]), "对撞面以切片 operationId 集合为分母"
    for operation_id, route in sorted(routes.items()):
        endpoint_name = str(getattr(route.endpoint, "__name__", ""))
        assert _camel(endpoint_name) == operation_id, operation_id


def test_every_problem_code_used_here_is_in_the_registry() -> None:
    """码名反查 ``PROBLEM_CODES``；``type`` 逐字 = ``urn:campaignlab:problem:<code 小写>``。"""
    assert _CODES_USED_BY_THIS_DIRECTORY, "分母哨兵：本目录断言码清单不得为空"
    assert len(_CODES_USED_BY_THIS_DIRECTORY) == len(set(_CODES_USED_BY_THIS_DIRECTORY))
    for code in _CODES_USED_BY_THIS_DIRECTORY:
        assert code in PROBLEM_CODES, code
        status, type_, title = PROBLEM_CODES[code]
        assert type_ == "urn:campaignlab:problem:" + code.lower()
        assert status >= 400 and title
