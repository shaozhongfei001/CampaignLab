"""行列定位串的生成与解析（M1-01 · S2；design §4.4）。

活契约里 ``Issue.location`` 是**纯字符串**（实测 ``Issue.properties.location`` ＝
``type=string, minLength=1, maxLength=500``，**无结构**）⇒ 行列语义全靠本文件冻结的三种形状：

- **行内字段**：``<table_name>#r<row_number>/<section>/<canonical_key>``，
  例 ``月度宽表#r4/count_fields/eligible``（A 宽表第 4 数据行的「可经营」列）；
- **整行**：``<table_name>#r<row_number>``，例 ``阶段人数长表#r17``
  （B 长表的第 17 个数据行）；
- **文件／元数据级**：``<table_name>#<json_pointer>``（**无**行号段），
  例 ``__metadata__#/coverage/0/period`` · ``月度宽表#/columns/3``。

**0/1-based 口径（design §4.4 要求「显式声明」的那个刻意不对称，禁「顺手统一」）**：

- ``row_number`` 一律 **1-based**，且**只数数据行**（表头／``columns`` 行不计）。
  权威出处＝ ``architecture/API.md``「错误分类」段末原文：「字段路径用 JSON Pointer，
  CSV 可补表名和 **1 起数据行号**」。``SOURCE_CSV`` 的 7 行文件（1 表头 ＋ 6 数据行）
  其第 1 个数据行 ``row_number == 1``；JSON 侧 ``tables[t].rows[i]`` ⇒ ``row_number == i + 1``。
  两侧必须同基数，否则 CSV 与 SOURCE_JSON 的 ``location`` 差 1，AC-006 的「同值」面直接破。
- **JSON Pointer 里的数组下标一律 0-based**（RFC 6901 标准）⇒ ``__metadata__#/coverage/0/period``
  指的是 ``coverage`` 数组的**第 1 项**。
  即：同一个 ``location`` 串内，``#r4`` 是 1-based 而 ``/coverage/0`` 是 0-based。

``make_location`` 与 ``parse_location`` **互为逆**（S6 落 round-trip 断言）。超过
``LOCATION_MAX_LENGTH`` 时**只截断表名段**，全名由调用方保留在 ``message`` 里
（design §4.4：禁截断行号或指针段 —— 那会毁掉可追溯性）。

本文件禁 SQL、禁事务、禁 import ``campaignlab.api``／``campaignlab.infra``、禁持时钟。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

__all__ = ["LOCATION_MAX_LENGTH", "LocationParts", "make_location", "parse_location"]

#: 真值来源＝活契约 ``Issue.properties.location.maxLength``（本轮回源实测 **500**）。
LOCATION_MAX_LENGTH: Final = 500

#: 行内字段形状：``r<1-based 行号>/<section>/<canonical_key>``。
_ROW_FIELD_RE: Final[re.Pattern[str]] = re.compile(
    r"^r(?P<row>[0-9]+)/(?P<section>[^/]+)/(?P<key>[^/]+)$"
)
#: 整行形状：``r<1-based 行号>``。
_ROW_RE: Final[re.Pattern[str]] = re.compile(r"^r(?P<row>[0-9]+)$")
_TABLE_SEPARATOR: Final = "#"
_ROW_PREFIX: Final = "r"


@dataclass(frozen=True, slots=True)
class LocationParts:
    """``parse_location`` 的出参：三种形状共用一个数据类，不适用的段为 ``None``。

    - 行内字段形状 ⇒ ``row_number`` / ``section`` / ``canonical_key`` 三者皆非 ``None``，
      ``pointer`` 为 ``None``；
    - 整行形状 ⇒ 只有 ``row_number`` 非 ``None``；
    - 文件／元数据级形状 ⇒ 只有 ``pointer`` 非 ``None``（可为空串，如 ``__metadata__#``）。

    ``table_name`` 为空串表示这是一个**无表级**的定位（design §3.4 的 ``/state`` · ``/mapping``
    与 §5.1 N9 的 ``/layout`` 都是这一族：映射／状态面错误没有具体的表）。
    """

    table_name: str
    row_number: int | None
    section: str | None
    canonical_key: str | None
    pointer: str | None


def make_location(
    *,
    table_name: str,
    row_number: int | None = None,
    section: str | None = None,
    canonical_key: str | None = None,
    pointer: str | None = None,
) -> str:
    """按 design §4.4 的三种形状之一拼出 ``Issue.location``。

    形状由入参组合唯一决定，非法组合一律 ``ValueError``（定位串是证据面，
    拼歪了比抛错更难查）：

    - ``row_number`` 非空 ＋ ``section``／``canonical_key`` 皆非空 ⇒ 行内字段形状；
    - ``row_number`` 非空 ＋ 二者皆空 ⇒ 整行形状；
    - ``row_number`` 为空 ⇒ 文件／元数据级形状（``pointer`` 可为 ``None``，即 ``<table>#``）。

    超长处置：**只截断表名段**（design §4.4）。表名截到 0 字符仍放不下时抛 ``ValueError``
    —— 那种情况下唯一能截的就是行号或指针段，而那是明令禁止的。
    """
    if row_number is not None:
        if pointer is not None:
            raise ValueError(f"行号段与指针段互斥（design §4.4 的三种形状）：{pointer!r}")
        if (section is None) != (canonical_key is None):
            raise ValueError(f"section 与 canonical_key 必须同时给出或同时省略：{section!r}")
        if section is None or canonical_key is None:
            tail = f"{_ROW_PREFIX}{row_number}"
        else:
            tail = f"{_ROW_PREFIX}{row_number}/{section}/{canonical_key}"
    else:
        if section is not None or canonical_key is not None:
            raise ValueError("没有行号段时不得给出 section／canonical_key（那是行内字段形状）")
        tail = "" if pointer is None else pointer
    body = f"{table_name}{_TABLE_SEPARATOR}{tail}" if table_name else tail
    if not body:
        raise ValueError("定位串不得为空（活契约 Issue.location.minLength == 1）")
    if len(body) <= LOCATION_MAX_LENGTH:
        return body
    if not table_name:
        raise ValueError(
            f"无表名的指针段本身已超 {LOCATION_MAX_LENGTH} 字符，禁截断指针段：{tail!r}"
        )
    overflow = len(body) - LOCATION_MAX_LENGTH
    kept = len(table_name) - overflow
    if kept < 1:
        raise ValueError(
            f"表名段截到 0 字符仍超 {LOCATION_MAX_LENGTH}，禁截断行号／指针段：{tail!r}"
        )
    return f"{table_name[:kept]}{_TABLE_SEPARATOR}{tail}"


def parse_location(location: str) -> LocationParts:
    """``make_location`` 的逆：把定位串拆回五种段（不适用的段为 ``None``）。

    只按**第一个** ``#`` 切分表名段 —— 表名本身不含 ``#``（活契约的 ``table_name``
    是 1–120 字符的自由文本，本仓的四份实测数据里都没有 ``#``），而 JSON Pointer 段
    可能含任意字符，故取最左的 ``#`` 才是稳定的切法。
    """
    if _TABLE_SEPARATOR not in location:
        return LocationParts(
            table_name="", row_number=None, section=None, canonical_key=None, pointer=location
        )
    table_name, _, tail = location.partition(_TABLE_SEPARATOR)
    field_match = _ROW_FIELD_RE.fullmatch(tail)
    if field_match is not None:
        return LocationParts(
            table_name=table_name,
            row_number=int(field_match.group("row")),
            section=field_match.group("section"),
            canonical_key=field_match.group("key"),
            pointer=None,
        )
    row_match = _ROW_RE.fullmatch(tail)
    if row_match is not None:
        return LocationParts(
            table_name=table_name,
            row_number=int(row_match.group("row")),
            section=None,
            canonical_key=None,
            pointer=None,
        )
    return LocationParts(
        table_name=table_name, row_number=None, section=None, canonical_key=None, pointer=tail
    )
