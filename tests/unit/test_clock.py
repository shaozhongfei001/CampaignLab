"""S3c：显式时钟不变量（design §2「显式时钟」条 / 任务卡「禁止」条）。

除单测 ``FixedClock`` 的可注入性外，本文件还钉住一条**静态**不变量：
``datetime.now(UTC)`` 在 ``src/`` 下**只允许**出现在 ``clock.py``——否则「领域计算不取系统时间」
就只是口号，任何一处偷取都会让 TTL／租约判定在测试里变得不可复现。
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from campaignlab.clock import Clock, FixedClock, SystemClock, ensure_utc

SRC = Path(__file__).resolve().parents[2] / "src" / "campaignlab"
NOW_CALL = re.compile(r"datetime\.now\(|\.utcnow\(|time\.time\(")


def test_fixed_clock_is_constant_by_default() -> None:
    initial = datetime(2026, 11, 13, 1, 2, 3, tzinfo=UTC)
    clock = FixedClock(initial)
    assert clock.now() == initial
    assert clock.now() == initial


def test_fixed_clock_steps_on_every_read() -> None:
    initial = datetime(2026, 11, 13, 1, 2, 3, tzinfo=UTC)
    clock = FixedClock(initial, step=timedelta(seconds=30))
    assert clock.now() == initial
    assert clock.now() == initial + timedelta(seconds=30)
    assert clock.now() == initial + timedelta(seconds=60)


def test_fixed_clock_normalizes_naive_to_utc() -> None:
    clock = FixedClock(datetime(2026, 11, 13, 1, 2, 3))
    value = clock.now()
    assert value.tzinfo is not None
    assert value.utcoffset() == timedelta(0)


def test_fixed_clock_advance_is_independent_of_step() -> None:
    initial = datetime(2026, 11, 13, tzinfo=UTC)
    clock = FixedClock(initial)
    clock.advance(timedelta(seconds=61))
    assert clock.now() == initial + timedelta(seconds=61)


def test_system_clock_returns_tz_aware_utc() -> None:
    value = SystemClock().now()
    assert value.tzinfo is not None
    assert value.utcoffset() == timedelta(0)


def test_clock_protocol_is_structural() -> None:
    assert isinstance(SystemClock(), Clock)
    assert isinstance(FixedClock(datetime(2026, 1, 1, tzinfo=UTC)), Clock)


def test_ensure_utc_converts_without_shifting_instant() -> None:
    shanghai = timezone(timedelta(hours=8))
    value = datetime(2026, 11, 13, 9, 0, 0, tzinfo=shanghai)
    converted = ensure_utc(value)
    assert converted == datetime(2026, 11, 13, 1, 0, 0, tzinfo=UTC)
    assert converted.tzinfo is not None and converted.utcoffset() == timedelta(0)


def test_datetime_now_only_appears_in_clock_module() -> None:
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        if path.name == "clock.py":
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if NOW_CALL.search(line):
                offenders.append(f"{path.relative_to(SRC)}:{lineno}")
    assert offenders == [], f"只有 clock.py 允许取系统当前时间，实测越界：{offenders}"
