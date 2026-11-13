"""幂等守卫（M0-02 · S3d；design §2「幂等」条 / §6 ``application/idempotency.py``）。

口径全部来自 design §2，本文件不另立规则：

- 唯一键 ``(scope_key, actor_id, operation, idem_key)``；``createWorkspace`` 的
  ``scope_key = "GLOBAL"``（无工作区上下文），``operation`` 取 operationId 字面量；
- ``request_digest`` 由 ``api.common.request_digest`` 算出（路由层负责传原始字节），
  本文件只比较、不重算——两处各算一份就会让「同键同体」在不同进程得出不同摘要；
- 落库 ``response_json`` ＝ ``api.common.idempotency_envelope`` 的信封
  ``{"status", "headers", "body"}``，``response_status`` 与 ``status`` 同值并以列为准；
- **只登记 2xx**：4xx/5xx 不写行，重试重新求值，拒绝与失败由结构化日志留痕；
- 并发靠主键唯一：``record()`` 的 INSERT 冲突即回读已存行，**禁止裸「先查后插」**。

``peek()`` 只是快路径（省掉一次无用写入），正确性由 ``record()`` 的 INSERT 冲突分支兜住：
两个并发请求同时 peek 到空、同时干活，最终只有一方 INSERT 成功，另一方在 ``record()``
里拿到已存行并按摘要判定「重放」或 409。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy import Connection

from campaignlab.api.common import IdempotencyConflict
from campaignlab.infra.db.repositories import IdempotencyRecord, IdempotencyRepository

__all__ = ["CONFLICT_DETAIL", "GLOBAL_SCOPE", "IdempotencyGuard", "IdempotencyKey"]

#: ``createWorkspace`` 无工作区上下文（design §2）。
GLOBAL_SCOPE: Final = "GLOBAL"

#: 同键异摘要的固定 detail。不回显摘要值——回显等于给客户端一个
#: 「服务端存了哪一版正文」的探针。
CONFLICT_DETAIL: Final = "同一 Idempotency-Key 已用于不同的请求内容"


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    """幂等主键四元组。``frozen`` + ``slots``：键在请求生命周期内不得被就地改写。"""

    scope_key: str
    actor_id: str
    operation: str
    idem_key: str


class IdempotencyGuard:
    """把「查—干活—登记」串成一个可重放的用例步骤。"""

    __slots__ = ("_repository",)

    def __init__(self, repository: IdempotencyRepository | None = None) -> None:
        self._repository = repository if repository is not None else IdempotencyRepository()

    def peek(
        self, conn: Connection, *, key: IdempotencyKey, request_digest: str
    ) -> IdempotencyRecord | None:
        """快路径：已登记则返回该行（供重放），未登记返回 ``None``。

        同键**异**摘要 → 409 ``IDEMPOTENCY_CONFLICT``（design §1）。
        """
        stored = self._fetch(conn, key)
        if stored is None:
            return None
        if stored.request_digest != request_digest:
            raise IdempotencyConflict(CONFLICT_DETAIL)
        return stored

    def record(
        self,
        conn: Connection,
        *,
        key: IdempotencyKey,
        request_digest: str,
        status: int,
        envelope_json: str,
        now: datetime,
    ) -> IdempotencyRecord | None:
        """登记本次 2xx 结果。返回 ``None``＝登记成功；返回已存行＝主键被并发请求占用。

        只允许登记 2xx：把 4xx 也写进去会让一次「参数写错的重试」永远重放同一个错误。
        """
        if not 200 <= status <= 299:
            raise ValueError(f"幂等只登记 2xx：status={status}")
        candidate = IdempotencyRecord(
            scope_key=key.scope_key,
            actor_id=key.actor_id,
            operation=key.operation,
            idem_key=key.idem_key,
            request_digest=request_digest,
            response_status=status,
            response_json=envelope_json,
            created_at=now.isoformat(),
        )
        if self._repository.insert(conn, record=candidate):
            return None
        stored = self._fetch(conn, key)
        if stored is None:
            # 主键冲突后回读却读不到：只可能是同事务内被回滚／连接被换掉。
            # 不猜原因，直接报内部错误，好过静默重放一个不存在的响应。
            raise RuntimeError(f"幂等键冲突后回读为空：{key}")
        if stored.request_digest != request_digest:
            raise IdempotencyConflict(CONFLICT_DETAIL)
        return stored

    def _fetch(self, conn: Connection, key: IdempotencyKey) -> IdempotencyRecord | None:
        return self._repository.fetch(
            conn,
            scope_key=key.scope_key,
            actor_id=key.actor_id,
            operation=key.operation,
            idem_key=key.idem_key,
        )
