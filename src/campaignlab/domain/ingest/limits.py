"""体积与件数上限（M1-01 · S2；design §5.2；D16：禁新增阈值）。

常量住**领域层**、不住 ``config.py``（``config.py`` 不在 scope_allow，且 framework/PYTHON.md 第 3 行
要求依赖朝领域内收）⇒ ``api/imports.py`` 与 ``infra/files.py`` 都从本文件**单向** import。
**禁**用 ``AppConfig.max_json_body_bytes``（1 MiB，仅 JSON 请求正文）当文件上限（ADR-005 §2.3）。
"""

from __future__ import annotations

from typing import Final

from campaignlab.domain.errors import InputTooLarge
from campaignlab.domain.ingest.states import ImportFormat

__all__ = [
    "GENERIC_UPLOAD_MAX_BYTES",
    "MAX_FILES_PER_IMPORT",
    "SYNTHETIC_V01_MAX_BYTES",
    "assert_within_size_limit",
    "max_bytes_for_format",
]

SYNTHETIC_V01_MAX_BYTES: Final = 8 * 1024 * 1024
GENERIC_UPLOAD_MAX_BYTES: Final = 64 * 1024 * 1024
MAX_FILES_PER_IMPORT: Final = 32


def max_bytes_for_format(fmt: ImportFormat) -> int:
    """合成 v0.1 入口 8 MiB；SOURCE_JSON / SOURCE_CSV 的每个上传件 64 MiB（OPERATIONS.md:11）。"""
    if fmt == "LEGACY_SYNTHETIC_JSON":
        return SYNTHETIC_V01_MAX_BYTES
    return GENERIC_UPLOAD_MAX_BYTES


def assert_within_size_limit(*, fmt: ImportFormat, size_bytes: int, location: str) -> None:
    """超限抛 413 INPUT_TOO_LARGE（InputTooLarge 来自 domain.errors，禁新增异常类）。"""
    limit = max_bytes_for_format(fmt)
    if size_bytes > limit:
        raise InputTooLarge(f"{location}：{size_bytes} 字节超过上限 {limit} 字节")
