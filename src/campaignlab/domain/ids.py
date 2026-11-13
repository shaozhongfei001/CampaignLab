"""资源 ID 与请求 ID 的唯一来源（M0-02 · S3c）。

R5-1 硬规则：``RESOURCE_ID_PATTERN`` 与 ``_new_request_id`` 原由 S3a 暂存于
``api/common.py``（见该文件 docstring 的历史「临时归属声明」），本轮**整块搬移（不是复制）**至此；
``api/common.py`` 改为 ``from campaignlab.domain.ids import ...`` 后 re-export。
依 ADR-005 §2.1，ID／请求号规则属公共冻结件，全仓**只允许存在一份**。

design §6 指派给本文件的符号：``RESOURCE_ID_RE`` / ``is_resource_id`` /
``new_resource_id`` / ``new_request_id``；``RESOURCE_ID_PATTERN`` 是搬移进来的既有常量。
"""

from __future__ import annotations

import re
import uuid
from typing import Final

__all__ = [
    "RESOURCE_ID_PATTERN",
    "RESOURCE_ID_RE",
    "is_resource_id",
    "new_request_id",
    "new_resource_id",
]

#: 活契约里 ID 型字段（``Problem.code`` / ``request_id`` / ``Workspace.id`` …）共用的正则。
RESOURCE_ID_PATTERN: Final = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$"

#: design §6：同一正则的**已编译**形态。活契约把该 pattern 逐字重复在每个 ID 型字段上，
#: 每个校验点各自 ``re.compile`` 既慢又容易写歪，这里收口成一份。
RESOURCE_ID_RE: Final[re.Pattern[str]] = re.compile(RESOURCE_ID_PATTERN)


def is_resource_id(value: str) -> bool:
    """``value`` 是否匹配活契约的 ID 正则（1–96，首字符必须字母数字）。

    用 ``fullmatch`` 而不是 ``match``：pattern 尾部的 ``$`` 在 ``match`` 语义下会匹配
    末尾换行前的位置，``"ws-1\n"`` 会被判为合法 ID —— 这种「差一个换行」的口子不允许留。
    """
    return RESOURCE_ID_RE.fullmatch(value) is not None


def new_resource_id(prefix: str) -> str:
    """生成带前缀的资源 ID：``<prefix>-<uuid4 hex>``。

    前缀与结果各断言一次：前缀含 ``/``、空格或超长时**立刻**报错，
    而不是让一个不合法 ID 静默写进数据库、等到契约校验才炸。
    """
    if not is_resource_id(prefix):
        raise ValueError(f"资源 ID 前缀不合法：{prefix!r}")
    candidate = f"{prefix}-{uuid.uuid4().hex}"
    if not is_resource_id(candidate):
        raise ValueError(f"生成的资源 ID 超出 ID 正则：{candidate!r}")
    return candidate


def new_request_id() -> str:
    """design 开头：``X-Request-Id`` 取 ``uuid4().hex``（43→32 hex，落在 1–96 且匹配 ID 正则）。

    R5-1：本函数原为 ``api/common.py::_new_request_id``（S3a 暂存），S3c 整块搬移至此；
    ``api/common.py`` 以 ``new_request_id as _new_request_id`` re-export，语义零变化。
    """
    return uuid.uuid4().hex
