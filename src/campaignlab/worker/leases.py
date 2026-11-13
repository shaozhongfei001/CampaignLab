"""租约：常量、令牌、过期判定（M0-04/S2；design §9 ``worker/leases.py``）。

**本模块不做任何时间加法。** A83 把租约期限的 Python 计算点收敛到
``application/worker.py::compute_lease_deadline`` 一处，故这里只：

- 存两个常量（``LEASE_TTL_SECONDS`` 直接 re-export ``WORKER_LEASE_SECONDS``，不写第二份
  字面量 30；``RENEW_INTERVAL_SECONDS`` 是 JOBS.md:13「每 5 秒续租」）；
- 生成随机令牌（JOBS.md:11「生成随机 lease token」）；
- 做**比较**（``is_expired``）与**转发**（``deadline_after`` 只调 ``compute_lease_deadline``）。

``Lease`` 是「谁有权提交」的凭据三元组（``attempt`` + ``token`` + ``deadline``）加作业
定位（``workspace_id`` + ``job_id``）。TX2/TX4/TX5/TX6 的谓词全部由它派生，故 handler
拿到的是不可变值对象——中途改不了，也就伪造不出一次有效提交（AC-029「失效租约不能提交」）。
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from campaignlab.application.worker import WORKER_LEASE_SECONDS, compute_lease_deadline
from campaignlab.clock import ensure_utc
from campaignlab.infra.db.repositories import JobRecord
from campaignlab.worker.errors import LeaseLost

__all__ = [
    "LEASE_TTL_SECONDS",
    "RENEW_INTERVAL_SECONDS",
    "Lease",
    "deadline_after",
    "is_expired",
    "new_lease_token",
]

#: 租约时长（秒）。单点来自 ``application/worker.py::WORKER_LEASE_SECONDS``，禁在此另写 30。
LEASE_TTL_SECONDS: Final = WORKER_LEASE_SECONDS
#: 续租间隔（秒）＝JOBS.md:13「每 5 秒续租」。与 30 秒 TTL 的关系是 1:6，
#: 即容忍连续 5 次续租失败才过期，检测取消的延迟上界也是这个值（design §4 末条）。
RENEW_INTERVAL_SECONDS: Final = 5

#: design §3 T1 指定 ``secrets.token_urlsafe(32)``：密码学随机、URL 安全、43 字符。
_LEASE_TOKEN_BYTES: Final = 32


def new_lease_token() -> str:
    """生成随机 lease token（JOBS.md:11）。用 ``secrets`` 而非 ``random``：

    令牌是**权限凭据**——猜中它就能替别人提交终态。``random`` 的梅森旋转器可由少量
    输出反推内部状态，不满足这个用途。
    """
    return secrets.token_urlsafe(_LEASE_TOKEN_BYTES)


def deadline_after(now: datetime, *, lease_seconds: int = LEASE_TTL_SECONDS) -> str:
    """转发到全仓唯一计算点（A83）。本函数**只转发、不重算**。

    存在的意义是给 worker 侧一个不必 import ``application.worker`` 内部细节的调用面；
    真正的 ``(now + timedelta(seconds=...)).isoformat()`` 只有一份。
    """
    return compute_lease_deadline(now, lease_seconds=lease_seconds)


def is_expired(lease_deadline: str, *, now: datetime) -> bool:
    """``lease_until < now`` 的 Python 侧判定（供测试与恢复扫描的前置检查用）。

    两侧都过 ``ensure_utc`` 再比：``lease_until`` 落库是 ISO-8601 文本，混入 naive 或
    非 UTC 偏移时直接比会得出错误结论。SQL 侧（TX7）用同格式文本的字典序比较，
    与此处等价——同格式 ISO-8601 的字典序即时序。
    """
    return ensure_utc(datetime.fromisoformat(lease_deadline)) < ensure_utc(now)


@dataclass(frozen=True, slots=True)
class Lease:
    """一次认领／续租得到的租约凭据（不可变）。"""

    workspace_id: str
    job_id: str
    attempt: int
    token: str
    deadline: str

    @classmethod
    def of(cls, record: JobRecord) -> Lease:
        """从 ``jobs`` 行构造。租约双列为空即说明该行不处于可租约状态。

        刻意**抛错**而不是返回 ``None``：调用点都在「刚刚认领／续租成功」之后，此时
        双列为空只能是数据被外部改写，静默降级会让后续提交带着 ``None`` 令牌去匹配
        谓词，得到一次含义不明的 ``rowcount == 0``。
        """
        if record.lease_token is None or record.lease_deadline is None:
            raise LeaseLost(f"作业不处于可租约状态：job={record.id} state={record.state}")
        return cls(
            workspace_id=record.workspace_id,
            job_id=record.id,
            attempt=record.attempt,
            token=record.lease_token,
            deadline=record.lease_deadline,
        )

    def expired(self, *, now: datetime) -> bool:
        """本租约是否已过期（``is_expired`` 的便捷绑定）。"""
        return is_expired(self.deadline, now=now)
