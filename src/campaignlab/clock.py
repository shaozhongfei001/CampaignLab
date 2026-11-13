"""显式时钟（M0-02 · S3c；design §2「显式时钟」条）。

任务卡「禁止」条：**不使用系统当前时间做领域计算**。本文件是该约束的唯一落点——
``SystemClock`` 是**全仓唯一**允许出现 ``datetime.now(UTC)`` 的地方；
application／domain／infra 层一律经 ``Depends(get_clock)`` 注入 ``Clock``，禁止自取系统时间。

``FixedClock`` 存在的理由是**可测性**：ADR-005 §2.3 要求令牌 60s、会话 TTL、worker 心跳窗口
都能用小值在毫秒内触发，禁止在测试里 sleep 到真实 TTL。``now()`` 每次调用前进 ``step``，
因此「连续取三次时刻」这类断言也能确定性地写出来。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable

__all__ = ["Clock", "FixedClock", "SystemClock", "ensure_utc"]


def ensure_utc(value: datetime) -> datetime:
    """把时刻归一到 tz-aware UTC。

    ``Clock.now()`` 的返回值必须是 tz-aware UTC（design §2）。naive 时刻按 **UTC** 解释而
    **不是**按本机时区——猜本地时区会让同一份数据在不同机器上算出不同业务日期，
    这类静默偏差比直接报错难查得多。
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@runtime_checkable
class Clock(Protocol):
    """时钟协议：只暴露 ``now()``，返回 tz-aware UTC。"""

    def now(self) -> datetime: ...


class SystemClock:
    """真实时钟。**全仓唯一**允许调用 ``datetime.now(UTC)`` 的类。

    无状态、可共享单例；``__slots__ = ()`` 让它保持零开销。
    """

    __slots__ = ()

    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """固定时钟：``now()`` 从 ``initial`` 起，每次调用后前进 ``step``（默认 0，即恒定）。

    ``initial`` 经 ``ensure_utc`` 归一，故注入 naive 时刻也不会让领域层拿到无时区的值。
    """

    __slots__ = ("_current", "_step")

    def __init__(self, initial: datetime, step: timedelta = timedelta(0)) -> None:
        self._current = ensure_utc(initial)
        self._step = step

    def now(self) -> datetime:
        value = self._current
        self._current = self._current + self._step
        return value

    def advance(self, delta: timedelta) -> None:
        """显式推进当前时刻（与 ``now()`` 的自动步进互不干扰）。"""
        self._current = self._current + delta
