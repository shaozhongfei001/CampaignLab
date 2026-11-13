"""worker 侧的领域错与 Problem 构造（M0-04/S2；design §9 ``worker/errors.py``）。

两条铁律：

1. **只用已注册的 20 个 code**（ADR-005 §2.1／D-019）。``DomainError.__init__`` 本身就
   会对注册表外的 code 抛 ``KeyError``，故本文件的两个子类只固定 ``default_code``，
   不发明新码。
2. **``JOB_INTERRUPTED`` 不是 Problem code**（A88③）。它是 JOBS.md:17 的**语义标签**，
   落在 ``Problem.issues[0].code``（``Issue.code`` 是自由串 1-96，非冻结面），外层
   ``Problem.code`` 取 ``INTERNAL_ERROR``、``status`` 取 500。把它提升为 ``Problem.code``
   会污染 ADR-005 冻结的注册表，故此处显式禁止。
"""

from __future__ import annotations

from typing import ClassVar, Final

from campaignlab.api.common import Issue, Problem
from campaignlab.domain.errors import PROBLEM_CODES, DomainError
from campaignlab.domain.ids import new_request_id

__all__ = [
    "JOB_INTERRUPTED",
    "NO_HANDLER",
    "ArtifactCommitFailed",
    "LeaseLost",
    "interrupted_problem",
    "no_handler_problem",
    "problem_of",
]

#: JOBS.md:17 的中断标签。**只进 ``Problem.issues[0].code``**，禁进 ``Problem.code``（A88③）。
JOB_INTERRUPTED: Final = "JOB_INTERRUPTED"
#: 未注册 kind 的标签（design §9）。同样只进 ``issues[0].code``。
NO_HANDLER: Final = "NO_HANDLER"

_INTERRUPTED_DETAIL: Final = "作业租约已过期且证据未提交，本次尝试记为中断；可发起重试。"


class LeaseLost(DomainError):
    """租约守卫不成立：``attempt`` 或 ``lease_token`` 不匹配，或作业已不在可租约状态。

    worker 侧的正常信号而非故障——design §4 要求「静默放弃本次尝试」，不得重试成第二
    终态。取 ``STATE_CONFLICT``（409）是因为 AC-029「失效租约不能提交」在 HTTP 面上的
    对偶就是状态冲突；它同时是注册表内的既有 code，未新增任何码。
    """

    default_code: ClassVar[str] = "STATE_CONFLICT"


class ArtifactCommitFailed(DomainError):
    """制品提交失败（跨设备 ``os.replace``、摘要不符、登记冲突等）。

    取 ``INTERNAL_ERROR``：这是服务端基础设施故障，不该让客户端以为是自己输入的问题。
    本卡不实现制品写入（``infra/artifacts.py`` 归 M0-04/S3），此处只提供 design §9
    点名的异常类型，供 S3 落地后直接复用。
    """

    default_code: ClassVar[str] = "INTERNAL_ERROR"


def _build(code: str, *, request_id: str, detail: str, issues: tuple[Issue, ...] = ()) -> Problem:
    """按注册表组装 ``Problem``：``type``／``title``／``status`` 一律取权威值，禁自拟。"""
    status, type_, title = PROBLEM_CODES[code]
    return Problem(
        type=type_,
        title=title,
        status=status,
        code=code,
        detail=detail,
        request_id=request_id,
        issues=list(issues),
    )


def interrupted_problem(
    *, request_id: str | None = None, detail: str = _INTERRUPTED_DETAIL
) -> Problem:
    """T7（``RUNNING -> FAILED``，JOB_INTERRUPTED）写进 ``jobs.problem_json`` 的 Problem。

    形状由 A88③ 钉死：``code='INTERNAL_ERROR'``、``status=500``、
    ``issues[0].code='JOB_INTERRUPTED'``。``location`` 指回租约列而不是请求体——中断是
    服务端失去执行权，客户端没有任何可改的字段。
    """
    return _build(
        "INTERNAL_ERROR",
        request_id=request_id if request_id is not None else new_request_id(),
        detail=detail,
        issues=(
            Issue(
                code=JOB_INTERRUPTED,
                location="/job/lease_until",
                message="租约已过期且证据未提交",
                severity="ERROR",
            ),
        ),
    )


def no_handler_problem(*, kind: str, request_id: str | None = None) -> Problem:
    """未注册 kind 的作业直接判失败（design §9：``VALIDATION_ERROR`` + ``NO_HANDLER``）。

    ``retryable`` 由调用方置 0：没有 handler 是部署配置缺陷，重试同一进程只会再失败一次。
    """
    return _build(
        "VALIDATION_ERROR",
        request_id=request_id if request_id is not None else new_request_id(),
        detail=f"没有可执行该作业类型的处理器：{kind}",
        issues=(
            Issue(
                code=NO_HANDLER,
                location="/job/kind",
                message=f"未注册 kind：{kind}",
                severity="ERROR",
            ),
        ),
    )


def problem_of(error: DomainError, *, request_id: str | None = None) -> Problem:
    """``DomainError`` → ``Problem``，用于 handler 抛错时写 ``jobs.problem_json``（T6）。

    逐字段搬运异常上已解析好的 ``code``／``status``／``type``／``title``／``detail``／
    ``issues``，不重新查表、不改写 code —— 异常构造时已经过注册表校验。
    """
    return Problem(
        type=error.type,
        title=error.title,
        status=error.status,
        code=error.code,
        detail=error.detail,
        request_id=request_id if request_id is not None else new_request_id(),
        issues=list(error.issues),
    )
