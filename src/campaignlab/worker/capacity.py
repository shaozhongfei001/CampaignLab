"""``JOB_CAPACITY`` 闸：待办上限与退避头（M0-04/S2；design §9 ``worker/capacity.py``）。

口径全部由 A88② 钉死：

- **「待办」＝非终态**（``QUEUED | RUNNING | CANCEL_REQUESTED``），不是「仅 QUEUED」。
  JOBS.md:7 原文是「默认工作区最多 10 个待办」，而一个正在跑的作业显然还占着执行资源；
  只数 QUEUED 会让「1 个在跑 + 10 个排队」这种实际 11 个待办的情况被判为合规。
- ``Retry-After = 3``：取 JOBS.md:5 轮询退避到 3 秒的那个值，落在活契约
  ``components.responses.Problem429.headers.Retry-After`` 的 1-3600 内。design §6 明载
  「缺头即违约」，故 ``JobCapacity`` 必须带 ``retry_after``，由 HTTP 层落成响应头。

非终态集合**不写字面量**：从 ``states.py`` 的 ``JOB_STATES`` 减 ``TERMINAL_STATES`` 现算，
这样契约若增删状态，这里自动跟随，不会出现「状态机 6 态、容量闸只认 3 态里的 2 态」的漂移。
"""

from __future__ import annotations

from typing import Final

from campaignlab.domain.errors import JobCapacity
from campaignlab.worker.states import JOB_STATES, TERMINAL_STATES

__all__ = [
    "JOB_CAPACITY_DETAIL",
    "JOB_CAPACITY_RETRY_AFTER_SECONDS",
    "JOB_PENDING_LIMIT",
    "check_capacity",
    "pending_states",
]

#: 单工作区待办上限（JOBS.md:7「默认工作区最多 10 个待办」）。
JOB_PENDING_LIMIT: Final = 10
#: 429 响应必须带的 ``Retry-After`` 秒数（A88②；JOBS.md:5 的退避值）。
JOB_CAPACITY_RETRY_AFTER_SECONDS: Final = 3

JOB_CAPACITY_DETAIL: Final = (
    f"该工作区的待办作业已达上限 {JOB_PENDING_LIMIT} 个，请按 Retry-After 稍后重试；"
    "已提交的结果入口保持不变。"
)

#: 非终态三值。由 ``JOB_STATES - TERMINAL_STATES`` 现算，禁写死字面量元组。
_PENDING_STATES: Final[tuple[str, ...]] = tuple(
    state for state in JOB_STATES if state not in TERMINAL_STATES
)


def pending_states() -> tuple[str, ...]:
    """计入「待办」的状态集合（``QUEUED``／``RUNNING``／``CANCEL_REQUESTED``）。"""
    return _PENDING_STATES


def check_capacity(pending_count: int) -> None:
    """``pending_count >= JOB_PENDING_LIMIT`` 即抛 429 ``JOB_CAPACITY``（带 ``retry_after``）。

    取 ``>=`` 而非 ``>``：``pending_count`` 是**插入前**的读数，等于上限就说明再入队一个
    就会变成 11 个待办。判定必须在 TX8 的 ``BEGIN IMMEDIATE`` **之内**做（见
    ``JobStore.retry``），否则两个并发重试会各自读到 9、各自入队，最后留下 11 个。
    """
    if pending_count >= JOB_PENDING_LIMIT:
        raise JobCapacity(JOB_CAPACITY_DETAIL, retry_after=JOB_CAPACITY_RETRY_AFTER_SECONDS)
