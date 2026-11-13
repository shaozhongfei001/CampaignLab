"""领域异常与 Problem code 注册表（M0-02 · S3c；公共冻结件）。

R5-1 硬规则：本文件的内容是把 S3a **暂存**于 ``api/common.py`` 的
``PROBLEM_CODES`` / ``_TITLE_BY_CODE`` / ``_STATUS_BY_CODE`` / ``DomainError`` 及其 13 个子类
**整块搬移（不是复制）**过来的结果；``api/common.py`` 改为 import 后 re-export，
公开符号集与搬移前逐字相同。依 ADR-005 §2.1，code 注册表的单一来源就是本文件，
**严禁两处各存一份**。

取值集合的唯一权威枚举是 ``spec/CampaignLab-SDD-v1.0/architecture/API.md``
第 20–29 行「错误分类」表的第 2 列（以「、」分隔，D-019 实测 **20 个**）：
本文件是该表的**代码化副本**——不得新增表外 code、不得改名、不得删除。
确需新增时**先改 ADR-005（走 CR，手册第 7 节）再改本注册表**。

- ``type`` 按 ADR-005 §2.1：``"urn:campaignlab:problem:" + code.lower()``；
- ``title`` 按 ADR-005 §2.2：与 code 一一对应的**固定中文短句表**，禁在调用点现编；
- D-022（OPEN）：``MONTHLY_INVALID_SCOPE`` / ``MONTHLY_REPORT_KIND_REQUIRED`` **不在**
  活契约也不在本注册表，本文件不得实现、不得扩表。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar, Final

if TYPE_CHECKING:
    # ``DomainError.issues`` 的元素类型。``Issue`` 是活契约 DTO，归 ``api/common.py``
    # （design §6 未把它划给 domain 层），故只在类型检查期引用，运行期不产生
    # ``domain -> api`` 的导入边（``from __future__ import annotations`` 保证注解不求值）。
    from campaignlab.api.common import Issue

__all__ = [
    "PROBLEM_CODES",
    "AccessDenied",
    "DomainError",
    "IdempotencyConflict",
    "InputTooLarge",
    "InternalFailure",
    "InvalidScope",
    "JobCapacity",
    "OriginDenied",
    "PreconditionRequired",
    "ResourceNotFound",
    "RevisionConflict",
    "SessionInvalid",
    "StateConflict",
    "ValidationFailure",
    "problem_type",
    "status_to_code",
]

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
