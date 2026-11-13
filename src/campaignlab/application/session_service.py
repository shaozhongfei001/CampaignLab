"""会话语义：一次性入口令牌 + 进程内会话（M0-02 · S3d；design §2 / §6）。

**两个 store 都只活在进程内存里**——28 张表里没有 ``sessions`` 表，把会话落库即违背
AC-035「进程重启后会话失效」。因此：

- ``SessionTokenStore``：``RLock`` + ``dict[token, _Grant]``，``consume()`` 在锁内 ``pop``，
  返回值即所有权；两个并发请求同时换取，只有一方拿到身份（design §4）。
- ``SessionStore``：``RLock`` + ``dict[session_id, SessionRecord]``，``get()`` 命中即刷新
  ``last_seen_at``，过期即删并返回 ``None``。

**401 只有一个面孔**：令牌未知／已消费／已过期／会话不存在／会话过期／进程重启后查不到，
一律 ``SessionInvalid(SESSION_INVALID_DETAIL)`` —— 同码同 detail。detail 里一旦出现
「令牌已使用」这类区分性措辞，就等于给客户端一个枚举 oracle（design §4 点名的失败模式），
并让 M0-03 前端走进错误分支。

**显式时钟**：``mint`` / ``consume`` / ``create`` / ``get`` 全部要求调用方传 ``now``，
本文件不自取系统当前时间（``clock.py`` 是全仓唯一允许处）。60s 令牌 TTL 与
``session_ttl_seconds``（默认 3600）
是两个不同对象，禁混用（ADR-005 §2.3）。

``AppIdentity`` 依裁定 A42/§9.4 **从 ``config.py`` import**，本文件不另建同名类。
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from campaignlab.api.common import Role, Session
from campaignlab.config import API_PREFIX, TOKEN_TTL_SECONDS, AppIdentity
from campaignlab.domain.errors import SessionInvalid

__all__ = [
    "SESSION_COOKIE_NAME",
    "SESSION_INVALID_DETAIL",
    "SessionCookie",
    "SessionRecord",
    "SessionService",
    "SessionStore",
    "SessionTokenStore",
]

#: design §2：Cookie 名固定 ``cl_session``。
SESSION_COOKIE_NAME: Final = "cl_session"

#: 401 的唯一 detail。所有失效原因共用这一句，禁按原因分叉。
SESSION_INVALID_DETAIL: Final = "会话不可用，请重新使用一次性令牌换取会话"


@dataclass(frozen=True, slots=True)
class SessionCookie:
    """``Set-Cookie`` 的参数组（design §2）。

    ``secure=False`` 是刻意的：本机模式只绑定 127.0.0.1 的 **http**（OPERATIONS.md），
    置 True 会让浏览器直接不下发 cookie。``samesite="strict"`` + ``httponly=True`` 是
    CSRF／XSS 读取的第一道挡板，不得为了联调方便而放宽。
    """

    name: str
    value: str
    max_age: int
    path: str = API_PREFIX
    httponly: bool = True
    samesite: str = "strict"
    secure: bool = False


@dataclass(frozen=True, slots=True)
class _Grant:
    """一次铸出的入口令牌（design §2）。"""

    identity: AppIdentity
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """一条会话（design §2 的字段面）。``allowed_roles`` 用 tuple：会话内容不可就地改写。"""

    session_id: str
    actor_id: str
    actor_name: str
    allowed_roles: tuple[Role, ...]
    created_at: datetime
    expires_at: datetime
    last_seen_at: datetime

    def to_session(self) -> Session:
        """转成活契约 ``Session`` DTO（3 字段全必填，``allowed_roles`` 1–6 项）。"""
        return Session(
            actor_id=self.actor_id,
            actor_name=self.actor_name,
            allowed_roles=list(self.allowed_roles),
        )

    def remaining_seconds(self, now: datetime) -> int:
        """Cookie ``max_age`` 用的剩余整数秒；已过期归 0（不给负数）。"""
        left = (self.expires_at - now).total_seconds()
        return int(left) if left > 0 else 0

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at


class SessionTokenStore:
    """一次性入口令牌存储（进程内存、仅首次可用、60s 过期）。"""

    __slots__ = ("_grants", "_lock", "_ttl_seconds")

    def __init__(self, *, ttl_seconds: int = TOKEN_TTL_SECONDS) -> None:
        if ttl_seconds < 1:
            raise ValueError(f"令牌 TTL 必须 >= 1 秒：{ttl_seconds}")
        self._ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._grants: dict[str, _Grant] = {}

    def mint(self, identity: AppIdentity, now: datetime) -> str:
        """铸一枚令牌。``secrets.token_urlsafe(32)`` → 43 字符，落在活契约的 16–180。"""
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._grants[token] = _Grant(
                identity=identity,
                issued_at=now,
                expires_at=now + timedelta(seconds=self._ttl_seconds),
            )
        return token

    def consume(self, token: str, now: datetime) -> AppIdentity | None:
        """消费令牌：命中且未过期 → 返回身份；**未知／已消费／已过期一律 ``None``**。

        ``pop`` 在锁内完成，故「两个并发请求同时换取同一令牌」只有一方拿到身份。
        过期条目在 ``pop`` 后就地丢弃，不做后台清理线程（M0 规模不需要，
        多一个线程就多一个不确定性来源）。
        """
        with self._lock:
            grant = self._grants.pop(token, None)
            if grant is None:
                return None
            if now >= grant.expires_at:
                return None
            return grant.identity

    def pending(self) -> int:
        """当前尚未消费的令牌数（诊断用，不进任何 HTTP 响应体）。"""
        with self._lock:
            return len(self._grants)


class SessionStore:
    """会话存储（进程内存）。重启即空 → 浏览器仍带 cookie 但查不到 → 401。"""

    __slots__ = ("_lock", "_sessions", "_ttl_seconds")

    def __init__(self, *, ttl_seconds: int) -> None:
        if ttl_seconds < 1:
            raise ValueError(f"会话 TTL 必须 >= 1 秒：{ttl_seconds}")
        self._ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._sessions: dict[str, SessionRecord] = {}

    def create(self, identity: AppIdentity, now: datetime) -> SessionRecord:
        """建会话。``expires_at = created_at + session_ttl_seconds``（design §2）。"""
        record = SessionRecord(
            session_id=secrets.token_urlsafe(32),
            actor_id=identity.actor_id,
            actor_name=identity.actor_name,
            allowed_roles=tuple(identity.allowed_roles),
            created_at=now,
            expires_at=now + timedelta(seconds=self._ttl_seconds),
            last_seen_at=now,
        )
        with self._lock:
            self._sessions[record.session_id] = record
        return record

    def get(self, session_id: str | None, now: datetime) -> SessionRecord | None:
        """取会话：未命中／已过期 → ``None``（过期条目就地删除）；命中则刷新 ``last_seen_at``。"""
        if not session_id:
            return None
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            if record.is_expired(now):
                del self._sessions[session_id]
                return None
            touched = SessionRecord(
                session_id=record.session_id,
                actor_id=record.actor_id,
                actor_name=record.actor_name,
                allowed_roles=record.allowed_roles,
                created_at=record.created_at,
                expires_at=record.expires_at,
                last_seen_at=now,
            )
            self._sessions[session_id] = touched
            return touched

    def invalidate_all(self) -> int:
        """清空全部会话（登出／测试用）。返回被清掉的条数。"""
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            return count

    def active(self, now: datetime) -> int:
        """未过期会话数（诊断用）。顺手清掉已过期条目，避免只增不减。"""
        with self._lock:
            expired = [sid for sid, rec in self._sessions.items() if rec.is_expired(now)]
            for sid in expired:
                del self._sessions[sid]
            return len(self._sessions)


class SessionService:
    """``exchangeSession`` / ``getSession`` 的用例编排（design §1 前两个 op）。

    结构化满足 ``api.deps.SessionService`` 端口；本类**不 import** ``api.deps``
    （Protocol 的意义就在于实现方无需反向依赖）。
    """

    __slots__ = ("_sessions", "_tokens")

    def __init__(self, *, tokens: SessionTokenStore, sessions: SessionStore) -> None:
        self._tokens = tokens
        self._sessions = sessions

    @property
    def tokens(self) -> SessionTokenStore:
        return self._tokens

    @property
    def sessions(self) -> SessionStore:
        return self._sessions

    def exchange(self, token: str, *, now: datetime) -> SessionRecord:
        """用一次性令牌换会话。

        令牌未知／已消费／已过期 → **同一个** 401 ``SESSION_EXPIRED``＋同一句 detail。
        """
        identity = self._tokens.consume(token, now)
        if identity is None:
            raise SessionInvalid(SESSION_INVALID_DETAIL)
        return self._sessions.create(identity, now)

    def resolve(self, session_id: str | None, *, now: datetime) -> SessionRecord:
        """按 cookie 里的 session_id 取会话；失效一律 401 同码同 detail。"""
        record = self._sessions.get(session_id, now)
        if record is None:
            raise SessionInvalid(SESSION_INVALID_DETAIL)
        return record

    def cookie(self, record: SessionRecord, *, now: datetime) -> SessionCookie:
        """按 design §2 的固定参数生成 ``Set-Cookie`` 参数组。"""
        return SessionCookie(
            name=SESSION_COOKIE_NAME,
            value=record.session_id,
            max_age=record.remaining_seconds(now),
        )
