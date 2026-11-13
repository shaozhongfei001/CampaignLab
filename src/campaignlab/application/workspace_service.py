"""工作区用例服务（M0-02 · S3d；design §1 后两个 op / §2 / §3 / §6）。

职责严格限于「用例编排 + 事务边界」（``application/__init__.py`` 的分层说明）：
SQL 一律下沉到 ``infra/db/repositories.py``，响应组装留给 ``api/workspaces.py``（S3b）。
本文件返回的是 DTO / 纯数据结果，**不返回 ``Response``** —— application 层一旦开始造
HTTP 响应，就会和路由层各持一份状态码与头字段口径。

三处口径直接照抄 design：

- **翻页**（§1）：排序固定 ``created_at DESC, id ASC``，键集谓词
  ``created_at < :k0 OR (created_at = :k0 AND id > :k1)``，每页取 ``limit+1`` 行以判
  ``next_cursor``；``q`` 对 ``name`` 做 NFKC + casefold 子串匹配。
- **游标**（§2）：``encode_cursor`` / ``decode_cursor`` 用 ``api.common`` 的那一份实现；
  payload = ``{"v": 1, "q": <查询摘要16hex>, "k": [created_at, id], "s": <actor_id>}``；
  密钥取数据目录 ``state/cursor.key``（首次生成 32 随机字节、0600、跨重启稳定）。
  解不开／版本不符／查询摘要不符／换了 actor → 一律 400 ``BAD_CURSOR`` 同一句 detail。
- **幂等**（§2）：``createWorkspace`` 的 ``scope_key="GLOBAL"``、``operation="createWorkspace"``；
  同键同摘要 → 重放信封（ETag 从信封取、**不重算**，仅 ``X-Request-Id`` 由路由重新生成）；
  同键异摘要 → 409 ``IDEMPOTENCY_CONFLICT``；``workspaces`` 与 ``audit`` **同事务**。

CR-002（选项 B，已 MERGED）：``listWorkspaces`` 只有 ``cursor`` / ``limit`` / ``q`` 三个参数，
**没有 ``status``、没有 ``sort``**，故本文件不存在任何 ``status`` 白名单校验分支。
（``getHealth`` 响应里的 ``Health.status`` 是另一回事，见 ``api/common.py::Health``。）
"""

from __future__ import annotations

import hashlib
import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

from sqlalchemy import Engine

from campaignlab.api.common import (
    AccessDenied,
    DomainError,
    Session,
    Workspace,
    WorkspaceCreate,
    WorkspacePage,
    canonical_json,
    decode_cursor,
    encode_cursor,
    etag,
    idempotency_envelope,
    request_digest,
    validate_idempotency_key,
)
from campaignlab.application.audit import (
    ACTION_WORKSPACE_CREATED,
    OUTCOME_ACCEPTED,
    TARGET_KIND_WORKSPACE,
    AuditWriter,
)
from campaignlab.application.idempotency import (
    GLOBAL_SCOPE,
    IdempotencyGuard,
    IdempotencyKey,
)
from campaignlab.clock import Clock
from campaignlab.config import API_PREFIX, AppConfig
from campaignlab.domain.ids import new_resource_id
from campaignlab.infra.db.engine import connect
from campaignlab.infra.db.paths import STATE_SUBDIR
from campaignlab.infra.db.repositories import IdempotencyRecord, WorkspaceRepository

__all__ = [
    "AUDIT_ROLE_PREFERRED",
    "BAD_CURSOR_DETAIL",
    "CURSOR_KEY_BYTES",
    "CURSOR_KEY_FILENAME",
    "CURSOR_QUERY_DIGEST_HEX",
    "CURSOR_VERSION",
    "OPERATION_CREATE_WORKSPACE",
    "WORKSPACES_PATH",
    "WORKSPACE_ID_PREFIX",
    "WorkspaceCreateOutcome",
    "WorkspaceService",
    "audit_role_of",
    "load_cursor_secret",
]

#: design §2：游标密钥文件名（数据目录 ``state/`` 下）、长度与权限。
CURSOR_KEY_FILENAME: Final = "cursor.key"
CURSOR_KEY_BYTES: Final = 32
CURSOR_KEY_MODE: Final = 0o600

#: 游标 payload 的版本号与查询摘要长度（design §2）。
CURSOR_VERSION: Final = 1
CURSOR_QUERY_DIGEST_HEX: Final = 16

#: 幂等摘要里的「规范化路径」（design §2）。
WORKSPACES_PATH: Final = f"{API_PREFIX}/workspaces"
#: ``idempotency.operation`` 取 operationId 字面量（design §2）。
OPERATION_CREATE_WORKSPACE: Final = "createWorkspace"
#: 工作区 ID 前缀。
WORKSPACE_ID_PREFIX: Final = "ws"

#: 400 ``BAD_CURSOR`` 的唯一 detail。游标是不可信外部输入，任何解析失败都收敛成这一句，
#: 不让异常措辞的差异变成探测游标结构的 oracle（``api.common.decode_cursor`` 同一思路）。
BAD_CURSOR_DETAIL: Final = "游标不可用，请从第一页重新查询"

#: ``audit.role`` 的优先取值：建工作区是操作者动作（design §3「role= actor 业务角色」）。
AUDIT_ROLE_PREFERRED: Final = "OPERATOR"


class _Replay(Exception):
    """内部控制流：事务内发现幂等键已被并发请求占用，需要**回滚**本次写入后重放。

    用异常而不是返回值，是因为此刻已经写入了 workspace / audit 行，
    只有让 ``conn.begin()`` 的上下文管理器看到异常才会回滚。
    """

    __slots__ = ("record",)

    def __init__(self, record: IdempotencyRecord) -> None:
        super().__init__("幂等重放")
        self.record = record


def load_cursor_secret(data_dir: Path) -> bytes:
    """读取（首次则生成）``<data_dir>/state/cursor.key``。

    跨重启必须稳定：换密钥会让所有已发出的游标瞬间失效，而客户端看到的只是
    一个无法解释的 400。故文件存在但长度不对时**报错**而不是静默重生成。
    """
    path = data_dir / STATE_SUBDIR / CURSOR_KEY_FILENAME
    if path.is_file():
        return _read_key(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, CURSOR_KEY_MODE)
    except FileExistsError:
        # 另一个进程刚生成完：读它的那一份，保证全机只有一个密钥。
        return _read_key(path)
    with os.fdopen(fd, "wb") as handle:
        handle.write(secrets.token_bytes(CURSOR_KEY_BYTES))
    os.chmod(path, CURSOR_KEY_MODE)
    return _read_key(path)


def _read_key(path: Path) -> bytes:
    raw = path.read_bytes()
    if len(raw) != CURSOR_KEY_BYTES:
        raise ValueError(
            f"游标密钥长度非法（应为 {CURSOR_KEY_BYTES} 字节，实测 {len(raw)}）：{path}；"
            "拒绝静默重生成——换密钥会让已发出的游标全部失效"
        )
    return raw


def audit_role_of(actor: Session) -> str:
    """从会话的 ``allowed_roles`` 里挑一个写进 ``audit.role``。

    本机模式 6 个角色全给（design §2），故必须有确定性的挑选规则：优先 ``OPERATOR``，
    否则取契约枚举序里的第一个。**已列为 Q 项**——活契约没有规定多角色时审计记哪一个。
    """
    roles = actor.allowed_roles
    if not roles:
        raise AccessDenied("会话未携带任何业务角色")
    return AUDIT_ROLE_PREFERRED if AUDIT_ROLE_PREFERRED in roles else str(roles[0])


def _query_digest(limit: int, q: str | None) -> str:
    """游标里绑定的查询摘要（design §2 的 ``q`` 字段）。

    绑定 ``limit`` 与 ``q``：翻页途中改了筛选条件却继续用旧游标，必须判 400，
    否则会把两种不同查询的结果拼成一条看似连续的列表。
    """
    raw = canonical_json({"limit": limit, "q": q}).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:CURSOR_QUERY_DIGEST_HEX]


@dataclass(frozen=True, slots=True)
class WorkspaceCreateOutcome:
    """``createWorkspace`` 的结果：新建与幂等重放共用一个形状。

    刻意**不含** ``X-Request-Id``：重放时它必须重新生成（design §2），
    由路由层用本次请求的 request_id 覆盖，application 层不碰它。
    """

    status: int
    headers: dict[str, str]
    body: dict[str, Any]
    replayed: bool

    def as_envelope(self) -> dict[str, Any]:
        """还原成 ``api.common.replay_from_envelope`` 能直接吃的信封。"""
        return {"status": self.status, "headers": dict(self.headers), "body": self.body}


def _outcome_of(record: IdempotencyRecord) -> WorkspaceCreateOutcome:
    envelope = record.envelope()
    raw_headers = envelope.get("headers") or {}
    headers = (
        {str(name): str(value) for name, value in raw_headers.items()}
        if isinstance(raw_headers, Mapping)
        else {}
    )
    raw_body = envelope.get("body")
    body = cast(dict[str, Any], raw_body if isinstance(raw_body, Mapping) else {})
    # design §2：``response_status`` 与信封 ``status`` 同值，并**以列为准**。
    return WorkspaceCreateOutcome(
        status=record.response_status, headers=headers, body=body, replayed=True
    )


class WorkspaceService:
    """结构化满足 ``api.deps.WorkspaceService`` 端口。"""

    def __init__(
        self,
        *,
        engine: Engine,
        clock: Clock,
        config: AppConfig,
        workspaces: WorkspaceRepository | None = None,
        idempotency: IdempotencyGuard | None = None,
        audit: AuditWriter | None = None,
        cursor_secret: bytes | None = None,
    ) -> None:
        self._engine = engine
        self._clock = clock
        self._config = config
        self._workspaces = workspaces if workspaces is not None else WorkspaceRepository()
        self._idempotency = idempotency if idempotency is not None else IdempotencyGuard()
        self._audit = audit if audit is not None else AuditWriter()
        # 密钥**延迟**加载：构造 WorkspaceService 不该在数据目录里落文件，
        # 否则 doctor 的 data_dir 子目录 WARN 会被一次健康检查悄悄抹平。
        self._cursor_secret = cursor_secret

    def _secret(self) -> bytes:
        if self._cursor_secret is None:
            self._cursor_secret = load_cursor_secret(self._config.data_dir)
        return self._cursor_secret

    # --------------------------------------------------------------------------- listWorkspaces

    def list_workspaces(
        self, *, actor: Session, cursor: str | None, limit: int, q: str | None
    ) -> WorkspacePage:
        """``GET /api/v1/workspaces`` 的用例实现。"""
        if limit < 1:
            raise DomainError(f"limit 必须 >= 1：{limit}", code="VALIDATION_ERROR")
        after: tuple[str, str] | None = None
        if cursor is not None:
            after = self._cursor_key(cursor, actor_id=actor.actor_id, limit=limit, q=q)
        with connect(self._engine) as conn:
            rows = self._workspaces.list_page(conn, limit=limit + 1, after=after, q=q)
        items = rows[:limit]
        next_cursor: str | None = None
        if len(rows) > limit and items:
            last = items[-1]
            next_cursor = encode_cursor(
                self._cursor_payload(
                    actor_id=actor.actor_id,
                    limit=limit,
                    q=q,
                    created_at=last.created_at.isoformat(),
                    workspace_id=last.id,
                ),
                self._secret(),
            )
        return WorkspacePage(items=items, next_cursor=next_cursor)

    def _cursor_payload(
        self, *, actor_id: str, limit: int, q: str | None, created_at: str, workspace_id: str
    ) -> dict[str, Any]:
        return {
            "v": CURSOR_VERSION,
            "q": _query_digest(limit, q),
            "k": [created_at, workspace_id],
            "s": actor_id,
        }

    def _cursor_key(
        self, cursor: str, *, actor_id: str, limit: int, q: str | None
    ) -> tuple[str, str]:
        """解游标并校验绑定；任何一项不符 → 400 ``BAD_CURSOR``（同一句 detail）。"""
        payload = decode_cursor(cursor, self._secret())
        if not isinstance(payload, Mapping):
            raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
        if payload.get("v") != CURSOR_VERSION:
            raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
        if payload.get("q") != _query_digest(limit, q):
            raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
        if payload.get("s") != actor_id:
            # 换人复用游标也必须判 400 而不是 403：游标本身是不可信输入，
            # 用状态码区分「签名错」与「不是你的」等于给出探测面。
            raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
        key = payload.get("k")
        if (
            not isinstance(key, list)
            or len(key) != 2
            or not isinstance(key[0], str)
            or not isinstance(key[1], str)
        ):
            raise DomainError(BAD_CURSOR_DETAIL, code="BAD_CURSOR")
        return (key[0], key[1])

    # -------------------------------------------------------------------------- createWorkspace

    def create_workspace(
        self,
        *,
        payload: WorkspaceCreate,
        body: bytes,
        idempotency_key: str,
        actor: Session,
        request_id: str,
    ) -> WorkspaceCreateOutcome:
        """``POST /api/v1/workspaces`` 的用例实现。

        ``body`` 必须是路由层收到的**原始字节**（design §2：``body_sha256`` 是原字节的
        sha256）。用重新序列化的 DTO 代替原字节，会让「同键同体」在字段顺序或空白不同的
        两次请求上算出不同摘要，幂等重放随之失效。
        """
        key_value = validate_idempotency_key(idempotency_key)
        digest = request_digest(path=WORKSPACES_PATH, query={}, body=body, files=())
        key = IdempotencyKey(
            scope_key=GLOBAL_SCOPE,
            actor_id=actor.actor_id,
            operation=OPERATION_CREATE_WORKSPACE,
            idem_key=key_value,
        )
        try:
            with connect(self._engine) as conn, conn.begin():
                existing = self._idempotency.peek(conn, key=key, request_digest=digest)
                if existing is not None:
                    return _outcome_of(existing)
                now = self._clock.now()
                workspace = Workspace(
                    id=new_resource_id(WORKSPACE_ID_PREFIX),
                    revision=1,
                    created_at=now,
                    name=payload.name,
                    source_class=payload.source_class,
                    authorization_note=payload.authorization_note,
                )
                self._workspaces.insert(conn, workspace=workspace)
                # design §3：audit.workspace_id NOT NULL REFERENCES workspaces(id)，
                # 故审计只能在 workspace 落库之后、同一事务之内写。
                self._audit.write(
                    conn,
                    workspace_id=workspace.id,
                    at=now,
                    actor_id=actor.actor_id,
                    role=audit_role_of(actor),
                    action=ACTION_WORKSPACE_CREATED,
                    target_kind=TARGET_KIND_WORKSPACE,
                    target_id=workspace.id,
                    outcome=OUTCOME_ACCEPTED,
                    request_id=request_id,
                )
                response_body = workspace.model_dump(mode="json")
                headers = {"ETag": etag(workspace.revision)}
                envelope = idempotency_envelope(status=201, headers=headers, body=response_body)
                stored = self._idempotency.record(
                    conn,
                    key=key,
                    request_digest=digest,
                    status=201,
                    envelope_json=canonical_json(envelope),
                    now=now,
                )
                if stored is not None:
                    raise _Replay(stored)
                return WorkspaceCreateOutcome(
                    status=201, headers=headers, body=response_body, replayed=False
                )
        except _Replay as signal:
            return _outcome_of(signal.record)
