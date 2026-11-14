"""规则摘要的固定投影（M2-01 · S2a；design §4.6）。

``DOMAIN.md``「内容摘要的固定投影」表·规则行原文：「``content``、按 key 排序的 ``terms``、
``source_rule_version``。规则标签和确认说明分别审计」⇒ 本文件是那句话的唯一代码化副本，
也是 ``rule_versions.digest`` 列、``RuleVersion.digest`` 字段、``RuleCheck.rule_digest``、
``Confirmation.digest`` 比对这**四处的同一个来源**（禁复制第二份）。

**不参与**摘要：``id`` / ``revision`` / ``created_at`` / ``activity_id`` / ``parent_rule_id`` /
``state`` / ``confirmed_at`` / ``confirmation`` / **``label``**（``label`` 与确认说明按原文
「分别审计」，走 design §7.3 的独立审计事件）。故**改 ``label`` 不改 ``digest``** ——
这是 design §4.6 点名要 S6 钉住的反直觉用例。

``canonicalize`` 由**调用方注入** ``api/common.py::canonical_json``（键排序、无多余空白、
非 ASCII 原样、字符串先 NFC）：这样既不在领域层产生 ``domain → api`` 的运行期导入边
（domain 层三禁之一），又不出现第二份规范化实现 —— ``canonical_json`` 的 docstring 明写
「两个 lane 各写一个 ``json.dumps`` 就会让同键同体算出不同摘要」。

本文件不含 SQL 文本、不开事务、不取系统时间（摘要输入全部由调用方给出）。
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final

__all__ = ["RULE_DIGEST_LENGTH", "digest_projection", "rule_digest"]

#: 摘要长度。真值来源＝切片 ``ddl.rule_versions`` 的 ``CHECK(length(digest)=64)``；
#: ``hashlib.sha256(...).hexdigest()`` 天然产出 64 位小写十六进制，二者逐字相符。
RULE_DIGEST_LENGTH: Final = 64


def _as_mapping(value: object) -> Mapping[str, Any]:
    """把投影输入统一成 ``Mapping``（非映射一律视为空，禁让 ``AttributeError`` 冒成 500）。"""
    return value if isinstance(value, Mapping) else {}


def digest_projection(
    content: Mapping[str, Any],
    terms: Sequence[Mapping[str, Any]],
    source_rule_version: str | None,
) -> dict[str, Any]:
    """design §4.6 的**投影信封**（三个键，不多不少）。

    - ``content``：调用方给出的 ``content.model_dump(mode="json")`` 原样（**不排序**，
      规范化时由 ``canonicalize`` 统一按键排序）；
    - ``source_rule_version``：``str | None``，``None`` 保留为 JSON ``null``；
    - ``terms``：每个条款的 ``model_dump(mode="json")``，按 ``key`` **升序**排序。
      排序键只用 ``key`` —— design §4.3 的 G3 已保证同键不重复，故排序稳定、无二级键歧义。

    ⚠ 与 ``RuleVersion.terms`` 的**响应顺序**（保持落库顺序，design §2.4）是两个面，禁混用。
    """
    return {
        "content": dict(_as_mapping(content)),
        "source_rule_version": source_rule_version,
        "terms": sorted(
            (dict(_as_mapping(term)) for term in terms),
            key=lambda term: str(term.get("key", "")),
        ),
    }


def rule_digest(
    content: Mapping[str, Any],
    terms: Sequence[Mapping[str, Any]],
    source_rule_version: str | None,
    *,
    canonicalize: Callable[[object], str],
) -> str:
    """``sha256(canonicalize(投影信封))`` 的 64 位小写十六进制摘要。

    ``canonicalize`` 必须注入 ``api/common.py::canonical_json``（见模块 docstring）：
    自己 ``json.dumps`` 会让「同键同体」在不同 lane 算出不同摘要，而摘要一旦漂移，
    ``confirmRule`` 的 409 ``VERSION_MISMATCH`` 与 ``checkRule`` 的
    「digest 列 vs 现算」自检（design §5.2）就会同时失去意义。
    """
    envelope = digest_projection(content, terms, source_rule_version)
    return hashlib.sha256(canonicalize(envelope).encode("utf-8")).hexdigest()
