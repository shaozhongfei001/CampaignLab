"""作业状态机：JOBS.md 第 11-19 行 9 条迁移的**唯一代码化副本**（M0-04/S2；design §3）。

本文件不写 SQL、不开事务、不碰数据库，只做三件事：把 6 个状态与 10 个作业类型收成
**单一来源**（直接 re-export ``api/common.py`` 的两个 Literal 别名，不抄第二份字面量）、
把 9 条迁移逐条钉成 ``Transition`` 数据、给出两条纯函数判定（``assert_transition_allowed``
与 ``retryable_for``）。真正的守卫是 ``infra/db/repositories.py`` 里每条 UPDATE 的 WHERE
谓词——本文件的 ``Transition.guard`` 是那些谓词的**可读镜像**，用于测试逐条对照，
不用于运行期决策（运行期只信 ``rowcount``，design §4）。

**9 条不多不少**：``TRANSITIONS`` 恰 9 项，与 JOBS.md 迁移表逐行一一对应；表外迁移
（例如 ``QUEUED -> SUCCEEDED``、``SUCCEEDED -> *``）在本文件里根本不存在，
``assert_transition_allowed`` 一律抛 409 ``STATE_CONFLICT``。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, get_args

from campaignlab.api.common import JobKind, JobState
from campaignlab.domain.errors import StateConflict

__all__ = [
    "JOB_KINDS",
    "JOB_STATES",
    "NON_RETRYABLE_PROBLEM_CODES",
    "STAGE_CLAIMED",
    "STAGE_QUEUED",
    "TERMINAL_STATES",
    "TRANSITIONS",
    "JobKind",
    "JobState",
    "Transition",
    "TransitionId",
    "assert_transition_allowed",
    "is_terminal",
    "retryable_for",
]

#: 6 个状态。取值直接来自活契约 DTO 的 Literal 参数，故契约改枚举这里立刻跟着改。
JOB_STATES: Final[tuple[str, ...]] = tuple(get_args(JobState))
#: 10 个作业类型（JOBS.md:5）。
JOB_KINDS: Final[tuple[str, ...]] = tuple(get_args(JobKind))
#: 终态集合。**一旦进入即不可再迁移**（JOBS.md:23「终态重复查询一致」）。
TERMINAL_STATES: Final[frozenset[str]] = frozenset({"CANCELLED", "FAILED", "SUCCEEDED"})

#: 入队时的阶段名（``jobs.stage`` 非空，DDL 要求 NOT NULL）。
STAGE_QUEUED: Final = "QUEUED"
#: 认领成功、handler 尚未报进度时的阶段名（design §3 T1）。
STAGE_CLAIMED: Final = "CLAIMED"

#: 永久性输入缺陷：这类失败重试也不会好，故 ``retryable = 0``（design §3 末段）。
NON_RETRYABLE_PROBLEM_CODES: Final[frozenset[str]] = frozenset(
    {"EVIDENCE_REQUIRED", "INPUT_TOO_LARGE", "INVALID_SCOPE", "VALIDATION_ERROR"}
)

TransitionId = Literal["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9"]


@dataclass(frozen=True, slots=True)
class Transition:
    """迁移表的一行。

    ``sources`` 是**集合**：T8 有「执行确认」与「租约到期」两条入口、T6/T7 都以 FAILED
    收尾，但每条 JOBS.md 行仍是一个 ``TransitionId``，与 design §3 的编号逐字对齐。
    ``guard`` 是那条 UPDATE 的 WHERE 谓词镜像，``transaction`` 是 design §4 的事务号与
    落点方法名——两者供测试与证据文档（S8 的 ``job-states.md``）逐条对照用。
    """

    id: TransitionId
    sources: tuple[str, ...]
    target: str
    trigger: str
    spec_ref: str
    guard: str
    transaction: str

    #: T9 的 ``target`` 落在**新行**上（新建 QUEUED 作业），源作业终态一字不变。
    creates_new_row: bool = False


TRANSITIONS: Final[tuple[Transition, ...]] = (
    Transition(
        id="T1",
        sources=("QUEUED",),
        target="RUNNING",
        trigger="事务内最早可认领",
        spec_ref="JOBS.md:11",
        guard="state = 'QUEUED' AND revision = :revision",
        transaction="TX1 JobRepository.claim_next",
    ),
    Transition(
        id="T2",
        sources=("QUEUED",),
        target="CANCELLED",
        trigger="请求取消",
        spec_ref="JOBS.md:12",
        guard="state = 'QUEUED' AND revision = :revision",
        transaction="TX3 JobRepository.request_cancel",
    ),
    Transition(
        id="T3",
        sources=("RUNNING",),
        target="RUNNING",
        trigger="每 5 秒续租",
        spec_ref="JOBS.md:13",
        guard=(
            "attempt = :attempt AND lease_token = :lease_token "
            "AND state IN ('RUNNING', 'CANCEL_REQUESTED'"
            ")"
        ),
        transaction="TX2 JobRepository.renew",
    ),
    Transition(
        id="T4",
        sources=("RUNNING",),
        target="CANCEL_REQUESTED",
        trigger="请求取消（执行进程在安全分段读取取消信号）",
        spec_ref="JOBS.md:14",
        guard="state = 'RUNNING' AND revision = :revision",
        transaction="TX3 JobRepository.request_cancel",
    ),
    Transition(
        id="T5",
        sources=("RUNNING",),
        target="SUCCEEDED",
        trigger="成功与租约仍有效",
        spec_ref="JOBS.md:15",
        guard=(
            "attempt = :attempt AND lease_token = :lease_token "
            "AND state IN ('RUNNING', 'CANCEL_REQUESTED'"
            ")"
        ),
        transaction="TX5 JobRepository.mark_succeeded",
    ),
    Transition(
        id="T6",
        sources=("RUNNING",),
        target="FAILED",
        trigger="已知失败",
        spec_ref="JOBS.md:16",
        guard=(
            "attempt = :attempt AND lease_token = :lease_token "
            "AND state IN ('RUNNING', 'CANCEL_REQUESTED'"
            ")"
        ),
        transaction="TX6 JobRepository.mark_failed",
    ),
    Transition(
        id="T7",
        sources=("RUNNING",),
        target="FAILED",
        trigger="超时租约且证据未提交",
        spec_ref="JOBS.md:17",
        guard="state = 'RUNNING' AND lease_until < :now",
        transaction="TX7 JobRepository.fail_expired_running",
    ),
    Transition(
        id="T8",
        sources=("CANCEL_REQUESTED",),
        target="CANCELLED",
        trigger="执行确认或租约到期",
        spec_ref="JOBS.md:18",
        guard=(
            "执行确认：attempt = :attempt AND lease_token = :lease_token "
            "AND state = 'CANCEL_REQUESTED'；"
            "到期：state = 'CANCEL_REQUESTED' AND lease_until < :now"
        ),
        transaction="TX4 JobRepository.confirm_cancel / TX7 JobRepository.cancel_expired_requested",
    ),
    Transition(
        id="T9",
        sources=("CANCELLED", "FAILED"),
        target="QUEUED",
        trigger="操作员发起重试",
        spec_ref="JOBS.md:19",
        guard="state IN ('FAILED', 'CANCELLED') AND revision = :revision",
        transaction="TX8 JobRepository.enqueue_retry（新行复用既有入队方法）",
        creates_new_row=True,
    ),
)


def is_terminal(state: str) -> bool:
    """``state`` 是否终态。终态行的任何后续迁移都必然 ``rowcount == 0``。"""
    return state in TERMINAL_STATES


def assert_transition_allowed(current: str, target: str) -> tuple[Transition, ...]:
    """校验 ``current -> target`` 在 9 条迁移表内，返回全部命中行（T6/T7 会同形状）。

    不在表内即抛 409 ``STATE_CONFLICT``。**终态唯一**由此得到双重保证：一是
    ``TRANSITIONS`` 里没有任何一条的 ``sources`` 含终态，二是本函数对终态出边一律抛错。
    于是「取消与完成争用」时后到者既改不动数据库行（谓词 UPDATE ``rowcount == 0``），
    也过不了这道纯函数校验——先提交者定终态（JOBS.md:23）。
    """
    if current not in JOB_STATES:
        raise StateConflict(f"未知的作业状态：{current!r}")
    if target not in JOB_STATES:
        raise StateConflict(f"未知的目标状态：{target!r}")
    matched = tuple(t for t in TRANSITIONS if current in t.sources and t.target == target)
    if not matched:
        raise StateConflict(f"迁移表内不存在 {current} -> {target}（JOBS.md:11-19 共 9 条）")
    return matched


def retryable_for(target_state: str, problem_code: str | None = None) -> bool:
    """``jobs.retryable`` 的取值口径（design §3 末段，逐字实现）。

    ``FAILED`` → 1，除非 ``problem_code`` 属永久性输入缺陷；``CANCELLED`` → 1；
    ``SUCCEEDED`` 与非终态 → 0（还在跑的作业谈不上「可重试」）。
    """
    if target_state == "FAILED":
        return problem_code not in NON_RETRYABLE_PROBLEM_CODES
    return target_state == "CANCELLED"
