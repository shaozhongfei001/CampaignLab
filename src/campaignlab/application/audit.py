"""审计写入侧（M0-02 · S3d；design §3「audit」条 / §6 ``application/audit.py``）。

**本文件只写不读**：``listAudit`` 的读入口归 M4-02（裁定 A15），提前实现会造出第二份
分页／过滤口径。

写入约束（design §3）：

- ``audit.workspace_id NOT NULL REFERENCES workspaces(id)``，因此**只有已落到某工作区的
  操作才能写 audit**。``exchangeSession`` / ``getSession`` / ``getHealth`` / ``listWorkspaces``
  与被拒绝的 ``createWorkspace`` 一律不写 audit，只写结构化日志；
- ``createWorkspace`` 成功时与 ``workspaces`` **同事务**写入 ``sequence=1``、
  ``action="WORKSPACE_CREATED"``、``outcome="ACCEPTED"``、``role=`` actor 的业务角色；
- ``digest`` 是链式摘要（``previous_digest`` 参与计算），任一环节被改写都会让后续摘要对不上。

``digest`` 的计算走 ``api.common.canonical_json``：审计链的价值在于「同一串事实在任何进程
算出同一枚摘要」，另写一个 ``json.dumps`` 就会让链在跨机器复核时断开。
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Final

from sqlalchemy import Connection

from campaignlab.api.common import canonical_json
from campaignlab.domain.ids import new_resource_id
from campaignlab.infra.db.repositories import AuditRecord, AuditRepository

__all__ = [
    "ACTION_WORKSPACE_CREATED",
    "OUTCOME_ACCEPTED",
    "TARGET_KIND_WORKSPACE",
    "AuditWriter",
]

#: design §3 点名的 createWorkspace 审计动作。
ACTION_WORKSPACE_CREATED: Final = "WORKSPACE_CREATED"
#: ``audit.outcome`` 的三个合法值之一（DDL CHECK）。M0-02 只会写 ACCEPTED。
OUTCOME_ACCEPTED: Final = "ACCEPTED"
#: ``audit.target_kind`` 取自活契约 ``ObjectKind`` 枚举；工作区创建的靶对象是 workspace。
TARGET_KIND_WORKSPACE: Final = "workspace"

#: 审计 ID 前缀。
_AUDIT_ID_PREFIX: Final = "aud"


def audit_digest(
    *,
    workspace_id: str,
    sequence: int,
    audit_id: str,
    at: str,
    actor_id: str,
    role: str,
    action: str,
    target_kind: str,
    target_id: str,
    outcome: str,
    request_id: str,
    previous_digest: str | None,
) -> str:
    """链式摘要：覆盖全部业务列（含 ``previous_digest``），小写 64 hex。"""
    envelope = {
        "workspace_id": workspace_id,
        "sequence": sequence,
        "id": audit_id,
        "at": at,
        "actor_id": actor_id,
        "role": role,
        "action": action,
        "target_kind": target_kind,
        "target_id": target_id,
        "outcome": outcome,
        "request_id": request_id,
        "previous_digest": previous_digest,
    }
    return hashlib.sha256(canonical_json(envelope).encode("utf-8")).hexdigest()


class AuditWriter:
    """在调用方已开启的事务里追加一条审计。

    不自己开连接、不自己 commit：审计必须与业务写入同事务（design §4「``workspaces`` 与
    ``audit`` 同事务」），谁开事务谁负责回滚。
    """

    __slots__ = ("_repository",)

    def __init__(self, repository: AuditRepository | None = None) -> None:
        self._repository = repository if repository is not None else AuditRepository()

    def write(
        self,
        conn: Connection,
        *,
        workspace_id: str,
        at: datetime,
        actor_id: str,
        role: str,
        action: str,
        target_kind: str,
        target_id: str,
        outcome: str,
        request_id: str,
        audit_id: str | None = None,
    ) -> AuditRecord:
        """追加一条审计并返回落库形态。

        ``sequence`` 与 ``previous_digest`` 都在同一事务内读取：事务未提交前，
        并发请求看不到彼此的审计行，故链不会分叉。
        """
        sequence = self._repository.next_sequence(conn, workspace_id)
        previous_digest = self._repository.last_digest(conn, workspace_id)
        resolved_id = audit_id if audit_id is not None else new_resource_id(_AUDIT_ID_PREFIX)
        at_text = at.isoformat()
        digest = audit_digest(
            workspace_id=workspace_id,
            sequence=sequence,
            audit_id=resolved_id,
            at=at_text,
            actor_id=actor_id,
            role=role,
            action=action,
            target_kind=target_kind,
            target_id=target_id,
            outcome=outcome,
            request_id=request_id,
            previous_digest=previous_digest,
        )
        record = AuditRecord(
            workspace_id=workspace_id,
            sequence=sequence,
            id=resolved_id,
            at=at_text,
            actor_id=actor_id,
            role=role,
            action=action,
            target_kind=target_kind,
            target_id=target_id,
            outcome=outcome,
            request_id=request_id,
            previous_digest=previous_digest,
            digest=digest,
        )
        self._repository.insert(conn, record=record)
        return record
