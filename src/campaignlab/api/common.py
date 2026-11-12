"""HTTP 公共件：Problem 错误体、ETag、Idempotency-Key 与游标包装（M0-02 · S3a）。

本文件是 M0-03b 的**冻结面**之一，故所有取值都写死在此并附出处，禁止在调用点现编：

- ``Problem`` / ``Issue`` 的字段、长度、必填集合逐字对齐活契约
  ``contracts/openapi.json -> components.schemas.{Problem,Issue}``（``additionalProperties: false``
  ⇒ ``extra="forbid"``）；
- ``code`` 的取值集合唯一权威枚举是 ``spec/CampaignLab-SDD-v1.0/architecture/API.md``
  第 20–29 行的「错误分类」表，共 **20 个**（D-019 已更正为 20，不是 21）。
  本文件**不新增表外 code、不改名**；
- ``type`` 按 ADR-005 §2.1：``"urn:campaignlab:problem:" + code.lower()``；
- ``title`` 按 ADR-005 §2.2：与 code 一一对应的**固定中文短句表**，保证同一错误在
  所有 lane 措辞一致（可测、可截图比对）；``detail`` 才允许携带上下文；
- 500 的 ``detail`` 只含 ``request_id``，禁止回显堆栈／SQL／用户源字段（OPERATIONS.md）。

> **⚠ 临时归属声明（S3a 回报 Q1，务必读完再改本文件）**
> ADR-005 §2.1 增补指定 code 注册表的单一来源是 ``src/campaignlab/domain/errors.py``，
> design §6 把 ``domain/errors.py``（code+title+异常类）与 ``domain/ids.py``（ID 正则、
> ``new_request_id``）划给 S3。但 R4-1 修订档位表 v2 给 S3a 的写权限清单里**没有**
> ``src/campaignlab/domain/**``，且该目录尚不存在。为使 ``api/common.py`` 可用（S3b 的
> 路由与 ``install_error_handlers`` 都依赖它），下列符号**暂存于本文件**：
> ``PROBLEM_CODES`` / ``_TITLE_BY_CODE`` / ``_STATUS_BY_CODE`` / ``DomainError`` 及其 13 个子类
> / ``_new_request_id`` / ``RESOURCE_ID_PATTERN``。
> 后续轮次建 ``domain/errors.py`` 与 ``domain/ids.py`` 时必须**整块搬移（不是复制）**，
> 并让本文件改为 ``from campaignlab.domain.errors import ...`` 后再导出；
> **严禁两处各存一份**——那会直接违反 ADR-005 §2.1 的单一来源约束。
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import unicodedata
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar, Final, Literal

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

__all__ = [
    "CURSOR_MAX_LENGTH",
    "IDEMPOTENCY_KEY_HEADER",
    "IDEMPOTENCY_KEY_MAX_LENGTH",
    "IDEMPOTENCY_KEY_MIN_LENGTH",
    "PROBLEM_CODES",
    "PROBLEM_MEDIA_TYPE",
    "RESOURCE_ID_PATTERN",
    "UNSAFE_METHODS",
    "X_REQUEST_ID_HEADER",
    "AccessDenied",
    "DomainError",
    "Health",
    "IdempotencyConflict",
    "InputTooLarge",
    "InternalFailure",
    "InvalidScope",
    "Issue",
    "Job",
    "JobCapacity",
    "ObjectRef",
    "OriginDenied",
    "OriginHostGuard",
    "PreconditionRequired",
    "Problem",
    "ResourceNotFound",
    "RevisionConflict",
    "Session",
    "SessionExchange",
    "SessionInvalid",
    "StateConflict",
    "ValidationFailure",
    "Workspace",
    "WorkspaceCreate",
    "WorkspacePage",
    "accepted_response",
    "canonical_json",
    "check_if_match",
    "decode_cursor",
    "encode_cursor",
    "etag",
    "idempotency_envelope",
    "install_error_handlers",
    "loopback_allowlists",
    "problem_response",
    "problem_type",
    "read_body_within_limit",
    "replay_from_envelope",
    "request_digest",
    "request_id_middleware",
    "status_to_code",
    "validate_idempotency_key",
]

# --------------------------------------------------------------------- 常量与 code 注册表

#: 活契约里 ID 型字段（``Problem.code`` / ``request_id`` / ``Workspace.id`` …）共用的正则。
RESOURCE_ID_PATTERN: Final = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$"
X_REQUEST_ID_HEADER: Final = "X-Request-Id"
PROBLEM_MEDIA_TYPE: Final = "application/problem+json"

IDEMPOTENCY_KEY_HEADER: Final = "Idempotency-Key"
IDEMPOTENCY_KEY_MIN_LENGTH: Final = 8
IDEMPOTENCY_KEY_MAX_LENGTH: Final = 128

#: design §2：游标 = ``b64u(canonical_json(payload)) + "." + hmac_sha256(secret, b64u)[:16]``，
#: 编码后总长必须 ≤300（活契约 ``next_cursor`` 的 maxLength）。
CURSOR_TAG_HEX_LENGTH: Final = 16
CURSOR_MAX_LENGTH: Final = 300

#: design §4：unsafe 方法同时校验 Host 与 Origin，GET 只校验 Host。
UNSAFE_METHODS: Final[frozenset[str]] = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: HTTP 状态 -> code。唯一权威来源是 API.md 第 20–29 行的「错误分类」表，逐行照抄，禁发明。
_STATUS_BY_CODE: Final[dict[str, int]] = {
    "BAD_REQUEST": 400,
    "BAD_CURSOR": 400,
    "SESSION_EXPIRED": 401,
    "ORIGIN_DENIED": 403,
    "ACCESS_DENIED": 403,
    "RESOURCE_NOT_FOUND": 404,
    "IDEMPOTENCY_CONFLICT": 409,
    "STATE_CONFLICT": 409,
    "VERSION_MISMATCH": 409,
    "STALE_CANDIDATE": 409,
    "SNAPSHOT_CONFLICT": 409,
    "ACTION_REVIEW_REQUIRED": 409,
    "REVISION_CONFLICT": 412,
    "PRECONDITION_REQUIRED": 428,
    "INPUT_TOO_LARGE": 413,
    "VALIDATION_ERROR": 422,
    "INVALID_SCOPE": 422,
    "EVIDENCE_REQUIRED": 422,
    "JOB_CAPACITY": 429,
    "INTERNAL_ERROR": 500,
}

#: ADR-005 §2.2：固定中文短句表。同一 code 在所有 lane 必须逐字相同，不得在调用点现编。
_TITLE_BY_CODE: Final[dict[str, str]] = {
    "BAD_REQUEST": "请求格式不正确",
    "BAD_CURSOR": "翻页游标无效",
    "SESSION_EXPIRED": "会话已失效",
    "ORIGIN_DENIED": "来源不受信任",
    "ACCESS_DENIED": "权限不足",
    "RESOURCE_NOT_FOUND": "对象不存在或不可见",
    "IDEMPOTENCY_CONFLICT": "幂等键冲突",
    "STATE_CONFLICT": "当前状态不允许该操作",
    "VERSION_MISMATCH": "版本不一致",
    "STALE_CANDIDATE": "候选已过期",
    "SNAPSHOT_CONFLICT": "快照冲突",
    "ACTION_REVIEW_REQUIRED": "动作需先完成复核",
    "REVISION_CONFLICT": "修订号不匹配",
    "PRECONDITION_REQUIRED": "缺少 If-Match 前置条件",
    "INPUT_TOO_LARGE": "输入体积超过上限",
    "VALIDATION_ERROR": "字段校验未通过",
    "INVALID_SCOPE": "筛选范围不合法",
    "EVIDENCE_REQUIRED": "证据不齐备",
    "JOB_CAPACITY": "作业队列已满",
    "INTERNAL_ERROR": "服务内部错误",
}


def problem_type(code: str) -> str:
    """ADR-005 §2.1：``type = "urn:campaignlab:problem:" + code.lower()``。"""
    return "urn:campaignlab:problem:" + code.lower()


def _build_registry() -> dict[str, tuple[int, str, str]]:
    """由状态表与标题表合成 ``code -> (status, type, title)``。

    两张表键集合必须完全一致，否则注册表会缺项——这里直接断言，让缺口在 import 期就炸，
    而不是等到某个错误分支返回了空 title。
    """
    missing_titles = set(_STATUS_BY_CODE) - set(_TITLE_BY_CODE)
    unknown_titles = set(_TITLE_BY_CODE) - set(_STATUS_BY_CODE)
    if missing_titles or unknown_titles:
        raise RuntimeError(
            f"code 注册表不自洽：缺 title={sorted(missing_titles)} 多余={sorted(unknown_titles)}"
        )
    return {
        code: (status, problem_type(code), _TITLE_BY_CODE[code])
        for code, status in _STATUS_BY_CODE.items()
    }


#: ``code -> (status, type, title)``（design §2 的既定形状）。
PROBLEM_CODES: Final[dict[str, tuple[int, str, str]]] = _build_registry()


def _invert_status() -> dict[int, str]:
    inverted: dict[int, str] = {}
    for code, entry in PROBLEM_CODES.items():
        inverted.setdefault(entry[0], code)
    return inverted


_STATUS_TO_CODE: Final[dict[int, str]] = _invert_status()


def status_to_code(status: int) -> str:
    """HTTP 状态 -> 默认 code（用于把框架产生的异常翻译成 Problem 形）。

    表外状态（例如 FastAPI 的 405）不允许发明新 code，只能落到同族既有 code：
    4xx -> ``BAD_REQUEST``、5xx -> ``INTERNAL_ERROR``。
    """
    mapped = _STATUS_TO_CODE.get(status)
    if mapped is not None:
        return mapped
    return "INTERNAL_ERROR" if status >= 500 else "BAD_REQUEST"


def _new_request_id() -> str:
    """design 开头：``X-Request-Id`` 取 ``uuid4().hex``（43→32 hex，落在 1–96 且匹配 ID 正则）。

    临时私有实现，见文件头「临时归属声明」：Round 5 建 ``domain/ids.py::new_request_id`` 后改引用。
    """
    return uuid.uuid4().hex


# ------------------------------------------------------------------------- 领域异常与 code


class DomainError(Exception):
    """所有可翻译成 Problem 的领域异常基类。

    子类用 ``code`` 类属性固定 code；未列入 design §6 的 code（``BAD_REQUEST``、
    ``BAD_CURSOR``、``VERSION_MISMATCH``、``STALE_CANDIDATE``、``SNAPSHOT_CONFLICT``、
    ``ACTION_REVIEW_REQUIRED``、``EVIDENCE_REQUIRED``）用 ``DomainError(code=...)`` 直接抛，
    不额外造类，避免与 Round 5 的 ``domain/errors.py`` 命名打架。
    """

    default_code: ClassVar[str] = "INTERNAL_ERROR"

    def __init__(
        self,
        detail: str | None = None,
        *,
        code: str | None = None,
        issues: Sequence[Issue] = (),
        retry_after: int | None = None,
    ) -> None:
        resolved = code if code is not None else self.default_code
        if resolved not in PROBLEM_CODES:
            # 注册表外的 code 一律拒绝：ADR-005 §2.1「任何新增 code 必须先进注册表再使用」。
            raise KeyError(f"未注册的 Problem code：{resolved!r}（权威枚举见 API.md 第 20-29 行）")
        status, type_, title = PROBLEM_CODES[resolved]
        self.code: Final = resolved
        self.status: Final = status
        self.type: Final = type_
        self.title: Final = title
        self.detail = title if detail is None else detail
        self.issues: tuple[Issue, ...] = tuple(issues)
        self.retry_after = retry_after
        super().__init__(self.detail)


class SessionInvalid(DomainError):
    """401：令牌未知／已消费／超时／会话过期／进程重启后。

    上述各态**同码同 detail**，杜绝枚举 oracle（design §4）。
    """

    default_code: ClassVar[str] = "SESSION_EXPIRED"


class OriginDenied(DomainError):
    """403：Origin 或 Host 非实际绑定的回环源。"""

    default_code: ClassVar[str] = "ORIGIN_DENIED"


class AccessDenied(DomainError):
    """403：身份合法但角色/范围不足。"""

    default_code: ClassVar[str] = "ACCESS_DENIED"


class ResourceNotFound(DomainError):
    """404：归属校验失败与「不存在」必须返回**逐字相同**的响应，不回显 ID、不区分原因。"""

    default_code: ClassVar[str] = "RESOURCE_NOT_FOUND"


class IdempotencyConflict(DomainError):
    """409：同一 Idempotency-Key 命中不同请求摘要。"""

    default_code: ClassVar[str] = "IDEMPOTENCY_CONFLICT"


class StateConflict(DomainError):
    """409：对象状态不允许该操作。"""

    default_code: ClassVar[str] = "STATE_CONFLICT"


class RevisionConflict(DomainError):
    """412：If-Match 与当前 revision 不匹配。"""

    default_code: ClassVar[str] = "REVISION_CONFLICT"


class PreconditionRequired(DomainError):
    """428：需要 If-Match 却没给。"""

    default_code: ClassVar[str] = "PRECONDITION_REQUIRED"


class InputTooLarge(DomainError):
    """413：JSON 正文超过上限（与文件上传的 8 MiB / 64 MiB 口径不得混用，ADR-005 §2.3）。"""

    default_code: ClassVar[str] = "INPUT_TOO_LARGE"


class ValidationFailure(DomainError):
    """422：字段级校验未通过，``issues[].location`` 必须是 JSON Pointer。"""

    default_code: ClassVar[str] = "VALIDATION_ERROR"


class InvalidScope(DomainError):
    """422：筛选/范围不合法。"""

    default_code: ClassVar[str] = "INVALID_SCOPE"


class JobCapacity(DomainError):
    """429：作业队列已满，**必须**附 ``Retry-After``（1–3600）。"""

    default_code: ClassVar[str] = "JOB_CAPACITY"


class InternalFailure(DomainError):
    """500：detail 只含 request_id，不回显堆栈／SQL／用户源字段。"""

    default_code: ClassVar[str] = "INTERNAL_ERROR"


# ------------------------------------------------------------------------------ DTO（活契约）

_IdStr = Annotated[StrictStr, Field(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN)]


class Issue(BaseModel):
    """活契约 ``components.schemas.Issue``：4 字段全必填、``additionalProperties: false``。"""

    model_config = ConfigDict(extra="forbid")

    code: _IdStr
    location: Annotated[StrictStr, Field(min_length=1, max_length=500)]
    message: Annotated[StrictStr, Field(min_length=1, max_length=500)]
    severity: Literal["ERROR", "WARNING", "INFO"]


class Problem(BaseModel):
    """活契约 ``components.schemas.Problem``（RFC 9457）：7 字段全必填（``issues`` 可为空数组）。"""

    model_config = ConfigDict(extra="forbid")

    type: Annotated[StrictStr, Field(min_length=1, max_length=250)]
    title: Annotated[StrictStr, Field(min_length=1, max_length=200)]
    status: Annotated[StrictInt, Field(ge=400, le=599)]
    code: _IdStr
    detail: Annotated[StrictStr, Field(min_length=1, max_length=500)]
    request_id: _IdStr
    issues: Annotated[list[Issue], Field(max_length=1000)]


Role = Literal["OPERATOR", "DESIGNER", "DATA_OWNER", "ANALYST", "TESTER", "REVIEWER"]
JobKind = Literal[
    "VALIDATE_IMPORT",
    "PUBLISH_IMPORT",
    "CORRECT_SNAPSHOT",
    "COMPARE",
    "REVIEW",
    "DIAGNOSE",
    "QUESTION",
    "SIMULATE",
    "REPORT",
    "EXPORT",
]
JobState = Literal["QUEUED", "RUNNING", "CANCEL_REQUESTED", "SUCCEEDED", "FAILED", "CANCELLED"]
ObjectKind = Literal[
    "workspace",
    "activity",
    "rule",
    "import",
    "snapshot",
    "definition",
    "case",
    "run",
    "candidate",
    "preflight",
    "receipt",
    "comparison",
    "review",
    "diagnosis",
    "question",
    "report",
    "action",
    "job",
    "export",
    "evidence",
]
SourceClass = Literal["SYNTHETIC", "AUTHORIZED_DEIDENTIFIED"]
RevisionInt = Annotated[StrictInt, Field(ge=1, le=9007199254740991)]
NoteStr = Annotated[StrictStr, Field(min_length=1, max_length=500)]


class SessionExchange(BaseModel):
    """活契约 ``SessionExchange``：``token`` 16–180，必填、无默认。"""

    model_config = ConfigDict(extra="forbid")

    token: Annotated[StrictStr, Field(min_length=16, max_length=180)]


class Session(BaseModel):
    """活契约 ``Session``：3 字段全必填，``allowed_roles`` 1–6 项。"""

    model_config = ConfigDict(extra="forbid")

    actor_id: _IdStr
    actor_name: Annotated[StrictStr, Field(min_length=1, max_length=80)]
    allowed_roles: Annotated[list[Role], Field(min_length=1, max_length=6)]


class Health(BaseModel):
    """活契约 ``Health``。``contract_version`` 必须运行时从活契约读取，禁硬编码（D-004）。

    注意：这里的 ``status`` 是 ``Health`` 自己的合法字段，与 CR-002 移除的
    ``listWorkspaces.status`` **查询参数**是两回事，不得误删（ADR-006）。
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["READY", "DEGRADED"]
    app_version: Annotated[StrictStr, Field(min_length=1, max_length=48)]
    contract_version: Annotated[StrictStr, Field(min_length=1, max_length=48)]
    worker: Literal["READY", "OFFLINE"]
    schema_revision: Annotated[StrictStr, Field(min_length=1, max_length=48)]


class WorkspaceCreate(BaseModel):
    """活契约 ``WorkspaceCreate``：``required=[name, source_class]``，note 可省。"""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[StrictStr, Field(min_length=1, max_length=80)]
    source_class: SourceClass
    authorization_note: NoteStr | None = None


class Workspace(BaseModel):
    """活契约 ``Workspace``：6 字段全在 ``required``（含 null），序列化必须显式出现
    ``authorization_note``，故本字段**不给默认值**。
    """

    model_config = ConfigDict(extra="forbid")

    id: _IdStr
    revision: RevisionInt
    created_at: AwareDatetime
    name: Annotated[StrictStr, Field(min_length=1, max_length=80)]
    source_class: SourceClass
    authorization_note: NoteStr | None


class WorkspacePage(BaseModel):
    """活契约 ``WorkspacePage``：``items`` 0–100，``next_cursor`` 1–300 或 null。"""

    model_config = ConfigDict(extra="forbid")

    items: Annotated[list[Workspace], Field(max_length=100)]
    next_cursor: Annotated[StrictStr, Field(min_length=1, max_length=300)] | None


class ObjectRef(BaseModel):
    """活契约 ``ObjectRef``：``kind`` 20 个枚举值 + ``id``。"""

    model_config = ConfigDict(extra="forbid")

    kind: ObjectKind
    id: _IdStr


class Job(BaseModel):
    """活契约 ``Job``：13 字段全必填（``retry_of`` / ``result_ref`` / ``problem`` 可为 null）。

    Q2 裁定：M0-02 内没有任何返回 202 的 operationId，故本 DTO 只用于
    ``accepted_response()`` 的 DTO/单测层覆盖，HTTP 端到端取证 deferred_to 拥有 202 op 的后续任务。
    """

    model_config = ConfigDict(extra="forbid")

    id: _IdStr
    revision: RevisionInt
    created_at: AwareDatetime
    kind: JobKind
    state: JobState
    attempt: Annotated[StrictInt, Field(ge=0, le=9000000000000)]
    progress: Annotated[StrictInt, Field(ge=0, le=100)]
    stage: Annotated[StrictStr, Field(min_length=1, max_length=120)]
    input_digest: Annotated[
        StrictStr, Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    ]
    retry_of: _IdStr | None
    result_ref: ObjectRef | None
    problem: Problem | None
    retryable: StrictBool


# -------------------------------------------------------------------------- 响应构造 helper


def _json_response(
    payload: BaseModel,
    *,
    status: int,
    media_type: str,
    request_id: str,
    extra_headers: Mapping[str, str] | None = None,
) -> Response:
    headers = {X_REQUEST_ID_HEADER: request_id}
    if extra_headers:
        headers.update(extra_headers)
    return Response(
        content=payload.model_dump_json(),
        status_code=status,
        media_type=media_type,
        headers=headers,
    )


def problem_response(
    error: DomainError | str,
    *,
    request_id: str,
    detail: str | None = None,
    issues: Sequence[Issue] = (),
    extra_headers: Mapping[str, str] | None = None,
) -> Response:
    """构造 ``application/problem+json`` 响应；每个响应必带 ``X-Request-Id``。

    500 的 ``detail`` 被**强制**改写为只含 ``request_id``、``issues`` 清空——这是
    OPERATIONS.md 的「不回显堆栈／SQL／用户源字段」，不允许调用方绕过。
    """
    code = error.code if isinstance(error, DomainError) else error
    if code not in PROBLEM_CODES:
        raise KeyError(f"未注册的 Problem code：{code!r}")
    status, type_, title = PROBLEM_CODES[code]
    resolved_detail = (
        (error.detail if isinstance(error, DomainError) else title) if detail is None else detail
    )
    resolved_issues = tuple(error.issues if isinstance(error, DomainError) else ()) + tuple(issues)
    headers: dict[str, str] = dict(extra_headers or {})
    if status >= 500:
        resolved_detail = f"request_id={request_id}"
        resolved_issues = ()
    elif code == "JOB_CAPACITY":
        retry_after = error.retry_after if isinstance(error, DomainError) else None
        if retry_after is None or not 1 <= retry_after <= 3600:
            raise ValueError("429 JOB_CAPACITY 必须附 Retry-After，且取值在 1–3600 秒之间")
        headers["Retry-After"] = str(retry_after)
    problem = Problem(
        type=type_,
        title=title,
        status=status,
        code=code,
        detail=resolved_detail,
        request_id=request_id,
        issues=list(resolved_issues),
    )
    return _json_response(
        problem,
        status=status,
        media_type=PROBLEM_MEDIA_TYPE,
        request_id=request_id,
        extra_headers=headers,
    )


def accepted_response(
    job: Job,
    *,
    location: str,
    request_id: str,
    extra_headers: Mapping[str, str] | None = None,
) -> Response:
    """202 ＋ ``Location`` ＋ ``ETag`` ＋ ``Job`` 体（Q2 裁定的 DTO 级覆盖）。"""
    headers = {"Location": location, "ETag": etag(job.revision)}
    if extra_headers:
        headers.update(extra_headers)
    return _json_response(
        job, status=202, media_type="application/json", request_id=request_id, extra_headers=headers
    )


# ---------------------------------------------------------------------------------- ETag


def etag(revision: int) -> str:
    """``ETag: "<revision>"``（带双引号十进制整数，对齐 If-Match 正则 ``^"[1-9][0-9]*"$``）。"""
    return f'"{revision}"'


def check_if_match(header: str | None, current_revision: int) -> None:
    """缺头 → 428 ``PRECONDITION_REQUIRED``；不匹配 → 412 ``REVISION_CONFLICT``。

    Q3 裁定：M0-02 的 5 个 op 均未声明 If-Match，故 ``create_workspace`` **不得**调用本函数；
    helper 仍须实现并被单测钉住，供 M1 起 16 个 If-Match op 复用。
    顺序固定「先幂等、后 If-Match」（API.md）。
    """
    if header is None:
        raise PreconditionRequired("本操作要求提供 If-Match 头")
    if header != etag(current_revision):
        raise RevisionConflict("If-Match 与当前修订号不一致")


# --------------------------------------------------------------------------- 幂等与规范化 JSON


def canonical_json(obj: object) -> str:
    """稳定序列化：键排序、无多余空白、非 ASCII 原样保留、字符串先 NFC。

    幂等摘要与游标摘要都必须走这一份实现——两个 lane 各写一个 ``json.dumps``
    就会让「同键同体」在不同进程算出不同摘要，幂等重放直接失效。
    """
    return json.dumps(_nfc(obj), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _nfc(obj: object) -> object:
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, Mapping):
        return {_nfc_key(key): _nfc(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_nfc(item) for item in obj]
    return obj


def _nfc_key(key: object) -> str:
    if not isinstance(key, str):
        raise TypeError(
            f"canonical_json 只接受字符串键（sort_keys=True 的前提），实测：{type(key).__name__}"
        )
    return unicodedata.normalize("NFC", key)


def request_digest(
    *,
    path: str,
    query: Mapping[str, str] | Sequence[tuple[str, str]],
    body: bytes,
    files: Sequence[str] = (),
) -> str:
    """design §2：``sha256(canonical_json({path, query, body_sha256, files}))``，小写 64 hex。

    ``query`` 先排序再入摘要，故键序不同、语义相同的两次请求算出同一个摘要。
    """
    pairs = (
        sorted(query.items())
        if isinstance(query, Mapping)
        else sorted((str(k), str(v)) for k, v in query)
    )
    envelope = {
        "path": path,
        "query": [[key, value] for key, value in pairs],
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "files": list(files),
    }
    return hashlib.sha256(canonical_json(envelope).encode("utf-8")).hexdigest()


def validate_idempotency_key(value: str | None) -> str:
    """``Idempotency-Key`` 头 8–128；不合规 → 422。

    ``issues[0].location`` 固定为 ``"/header/Idempotency-Key"``（design §1）。
    """
    location = f"/header/{IDEMPOTENCY_KEY_HEADER}"
    if value is None:
        raise ValidationFailure(
            f"缺少必填头 {IDEMPOTENCY_KEY_HEADER}",
            issues=[
                Issue(
                    code="VALIDATION_ERROR",
                    location=location,
                    message=f"必须提供 {IDEMPOTENCY_KEY_HEADER} 头",
                    severity="ERROR",
                )
            ],
        )
    if not IDEMPOTENCY_KEY_MIN_LENGTH <= len(value) <= IDEMPOTENCY_KEY_MAX_LENGTH:
        raise ValidationFailure(
            f"{IDEMPOTENCY_KEY_HEADER} 长度必须在 {IDEMPOTENCY_KEY_MIN_LENGTH}"
            f"–{IDEMPOTENCY_KEY_MAX_LENGTH} 之间",
            issues=[
                Issue(
                    code="VALIDATION_ERROR",
                    location=location,
                    message=f"实测长度 {len(value)}",
                    severity="ERROR",
                )
            ],
        )
    return value


#: 重放时**只**回放这两个头（design §2/§4：ETag、Location）。
#: ``X-Request-Id`` 必须重新生成，其余头一律不带，避免把上一次的运行痕迹当成本次结果。
REPLAYED_HEADERS: Final[tuple[str, ...]] = ("ETag", "Location")


def idempotency_envelope(
    *, status: int, headers: Mapping[str, str], body: object
) -> dict[str, Any]:
    """落库 ``idempotency.response_json`` 的信封（design §2）。

    形状固定为 ``{"status": int, "headers": {...}, "body": {...}}``。
    """
    return {"status": status, "headers": dict(headers), "body": body}


def replay_from_envelope(envelope: Mapping[str, Any], *, request_id: str) -> Response:
    """命中同摘要时按信封重放；**仅 ``X-Request-Id`` 重新生成**。

    ETag 从信封取、**不得重算**（design §4：幂等重放必须回放同一 ETag）。
    """
    status = int(envelope["status"])
    raw_headers = envelope.get("headers") or {}
    if not isinstance(raw_headers, Mapping):
        raise ValueError("幂等信封的 headers 必须是对象")
    headers = {X_REQUEST_ID_HEADER: request_id}
    for name in REPLAYED_HEADERS:
        for key, value in raw_headers.items():
            if str(key).lower() == name.lower() and value is not None:
                headers[name] = str(value)
    return Response(
        content=json.dumps(envelope.get("body"), ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        ),
        status_code=status,
        media_type="application/json",
        headers=headers,
    )


# ------------------------------------------------------------------------------------ 游标


def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64u_decode(text: str) -> bytes | None:
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except ValueError, binascii.Error:
        return None


def encode_cursor(payload: Mapping[str, Any], secret: bytes) -> str:
    """``b64u(canonical_json(payload)) + "." + hmac_sha256(secret, b64u)[:16]``。

    HMAC 覆盖的是 base64 文本本身（不是原始 JSON），解码侧无需先解码即可验签，
    避免「先解出内容再校验」把畸形输入送进解析器。
    """
    body = _b64u_encode(canonical_json(payload).encode("utf-8"))
    tag = hmac.new(secret, body.encode("ascii"), hashlib.sha256).hexdigest()[:CURSOR_TAG_HEX_LENGTH]
    return f"{body}.{tag}"


def decode_cursor(cursor: str, secret: bytes) -> dict[str, Any] | None:
    """解不开／HMAC 不符／查询摘要不符 → ``None``，由调用方映射为 400 ``BAD_CURSOR``。

    一律返回 ``None`` 而不抛异常：游标是**不可信外部输入**，任何解析失败都必须收敛成
    同一个 400，不得让异常类型差异变成探测游标结构的 oracle。
    """
    body, separator, tag = cursor.partition(".")
    if not separator or not body or len(tag) != CURSOR_TAG_HEX_LENGTH:
        return None
    expected = hmac.new(secret, body.encode("ascii"), hashlib.sha256).hexdigest()[
        :CURSOR_TAG_HEX_LENGTH
    ]
    if not hmac.compare_digest(tag, expected):
        return None
    raw = _b64u_decode(body)
    if raw is None:
        return None
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError, json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded


# ------------------------------------------------------------------------ Host / Origin 守卫


def loopback_allowlists(port: int) -> tuple[frozenset[str], frozenset[str]]:
    """design §4 的默认白名单：``{127.0.0.1:<port>, localhost:<port>}`` 与对应 http Origin。"""
    hosts = frozenset({f"127.0.0.1:{port}", f"localhost:{port}"})
    origins = frozenset({f"http://127.0.0.1:{port}", f"http://localhost:{port}"})
    return hosts, origins


@dataclass(frozen=True, slots=True)
class OriginHostGuard:
    """回环来源守卫。白名单必须**可注入**：``TestClient`` 默认 ``Host: testserver`` 且不带
    Origin，不注入就会让全部用例 403（design §4 点名的失败模式）。
    """

    allowed_hosts: frozenset[str]
    allowed_origins: frozenset[str]

    def check(self, *, method: str, host: str | None, origin: str | None) -> None:
        """GET 只校验 Host；unsafe 方法（POST/PUT/PATCH/DELETE）同时校验 Host 与 Origin。"""
        if (host or "").strip() not in self.allowed_hosts:
            raise OriginDenied("请求的 Host 不在本机回环白名单内")
        if method.upper() in UNSAFE_METHODS and (origin or "").strip() not in self.allowed_origins:
            raise OriginDenied("请求的 Origin 不在本机回环白名单内")


# --------------------------------------------------------------------------- 正文上限与中间件


async def read_body_within_limit(request: Request, *, max_bytes: int) -> bytes:
    """两阶段判定（design §4）：先按 ``Content-Length`` 预判，再在流式读取时累计二次判定。

    只信 ``Content-Length`` 可被伪造；先 ``await request.body()`` 全量读入再判长度
    等于没有上限。``max_bytes`` 由调用方从 ``AppConfig.MAX_JSON_BODY_BYTES`` 注入，
    本文件**不持有**该常量（它属 ``config.py``，ADR-005 §2.3）。
    """
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared.strip())
        except ValueError as exc:
            raise DomainError("Content-Length 不是合法整数", code="BAD_REQUEST") from exc
        if declared_size > max_bytes:
            raise InputTooLarge(f"JSON 正文超过 {max_bytes} 字节上限")
    buffer = bytearray()
    async for chunk in request.stream():
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise InputTooLarge(f"JSON 正文超过 {max_bytes} 字节上限")
    return bytes(buffer)


def request_id_of(request: Request) -> str:
    """取本次请求的 ``X-Request-Id``；中间件没跑到（例如启动期异常）就现生成一个。"""
    value = getattr(request.state, "request_id", None)
    return str(value) if value else _new_request_id()


async def request_id_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """每个响应必带 ``X-Request-Id``（design 开头：取 ``uuid4().hex``）。

    写进 ``request.state`` 而不是局部变量：``State`` 落在 ``scope["state"]`` 上，
    下游路由与异常处理器才能取到同一个 id，日志与响应头因此可对齐。
    """
    request_id = request_id_of(request)
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers[X_REQUEST_ID_HEADER] = request_id
    return response


def _issues_from_validation_error(exc: RequestValidationError) -> list[Issue]:
    """把 pydantic/FastAPI 的校验错误翻译成 ``issues[]``（``location`` 为 JSON Pointer）。"""
    issues: list[Issue] = []
    for error in exc.errors():
        location = "/" + "/".join(str(part).lstrip("/") for part in error.get("loc", ()))
        issues.append(
            Issue(
                code="VALIDATION_ERROR",
                location=location or "/",
                message=str(error.get("msg", "字段校验未通过"))[:500],
                severity="ERROR",
            )
        )
    return issues[:1000]


# Starlette 的 ``add_exception_handler`` 要求处理器签名统一为 ``(Request, Exception)``，
# 故下列处理器一律先收窄类型再翻译；收窄失败说明注册表与派发类型对不上，按 500 兜底而不是崩在
# 类型断言上——错误处理器自身抛异常会让客户端拿到一个没有 Problem 形的裸 500。


def _handle_domain_error(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, DomainError):
        return _handle_unexpected(request, exc)
    return problem_response(exc, request_id=request_id_of(request))


def _handle_validation_error(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, RequestValidationError):
        return _handle_unexpected(request, exc)
    return problem_response(
        ValidationFailure("请求体或查询参数校验未通过"),
        request_id=request_id_of(request),
        issues=_issues_from_validation_error(exc),
    )


def _handle_http_exception(request: Request, exc: Exception) -> Response:
    """把框架产生的 HTTP 异常也收敛成 Problem 形。

    design §4 点名的场景：契约中不存在的路径（深链探测）必须返回 Problem 形 404，
    而不是 FastAPI 默认的 ``{"detail":"Not Found"}``。
    """
    if not isinstance(exc, StarletteHTTPException):
        return _handle_unexpected(request, exc)
    code = status_to_code(exc.status_code)
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail else PROBLEM_CODES[code][2]
    return problem_response(DomainError(detail, code=code), request_id=request_id_of(request))


def _handle_unexpected(request: Request, exc: Exception) -> Response:
    """兜底 500：``detail`` 只含 ``request_id``（``problem_response`` 内部强制），不回显堆栈。"""
    return problem_response(InternalFailure(), request_id=request_id_of(request))


def install_error_handlers(app: FastAPI) -> None:
    """把「每个响应都有 X-Request-Id + 所有错误都是 Problem 形」一次性装到 app 上。

    必须在 ``create_app()`` 里调用；漏掉它就会退回 FastAPI 默认错误体，
    前端（M0-03）按 ``code`` 分支的逻辑会全部走进未知分支。
    """
    app.add_middleware(BaseHTTPMiddleware, dispatch=request_id_middleware)
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected)
