"""三层摘要里的**校验摘要**与**映射／元数据摘要**（M1-01 · S2；design §4.7）。

design §4.7 的三层摘要各有单一真值来源：① 文件摘要＝制品原字节 SHA-256（落
``artifacts.sha256``，由 ``infra/files.py`` 登记）；② 映射摘要＝ ``source_mappings.digest``；
③ 校验摘要＝ ``imports.validation_digest``。本文件是 ②③ 的**唯一**代码化副本。

``validation_digest`` 的输入是 ``validation_projection`` 产出的**固定投影**，权威依据两句原文：

- ``architecture/DATA.md``「映射和标准表」段：「校验摘要覆盖**文件原始 SHA、映射内容、
  元数据及解析器版本**」⇒ 投影恰为 ``files`` / ``mapping_digest`` / ``metadata_digest`` /
  ``parser_version`` 四件事；
- ``architecture/DOMAIN.md``「业务摘要排除运行时间、作业号、租约和随机资源 ID」⇒
  ``created_at`` · ``job_id`` · ``import_id`` · ``artifact_id`` · ``revision`` · ``lease_*`` ·
  ``request_id`` **一律禁入**投影。加上第 5 个键 ``kind``（与 ``DOMAIN.md``「内容摘要的
  固定投影」表的「快照」行同族），投影的键集合**恰等于 5 键**（S6 落「多一键少一键都判红」的断言）。

``canonicalize`` 一律由**调用方注入** ``api/common.py::canonical_json``（体例逐字对齐实测的
``domain/activity/digests.py::rule_digest(..., *, canonicalize)``）：这样既不在领域层产生
``domain → api`` 的运行期导入边（domain 三禁之一），又不出现第二份序列化实现 ——
``canonical_json`` 的 docstring 明写「两个 lane 各写一个 ``json.dumps`` 就会让同键同体算出
不同摘要」。**禁**在本文件里 ``import campaignlab.api``、**禁**自己写 ``json.dumps``。

``PARSER_VERSION`` 的**定义点在** ``domain/ingest/parse.py``（design §4.7 的投影表点名
``domain/ingest/parse.py::PARSER_VERSION``）；本文件按 §11.1 的符号清单把它 re-export，
使摘要面与解析面共用同一个对象，**不是**第二份定义。

本文件不含 SQL 文本、不开事务、不取系统时间（摘要输入全部由调用方给出）。
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final

from campaignlab.domain.ingest.model import FileRef
from campaignlab.domain.ingest.parse import PARSER_VERSION

__all__ = [
    "DIGEST_LENGTH",
    "PARSER_VERSION",
    "VALIDATION_DIGEST_KIND",
    "mapping_digest",
    "metadata_digest",
    "validation_digest",
    "validation_projection",
]

#: 投影的 ``kind`` 键取值（design §4.7 投影表第 1 行，逐字）。
VALIDATION_DIGEST_KIND: Final = "IMPORT_VALIDATION"

#: 摘要长度。真值来源＝切片 ``ddl.source_mappings``／``ddl.imports`` 的
#: ``CHECK(length(digest)=64)``；``hashlib.sha256(...).hexdigest()`` 天然产出
#: 64 位小写十六进制，二者逐字相符。
#: 体例＝实测 ``domain/activity/digests.py::RULE_DIGEST_LENGTH == 64``。
DIGEST_LENGTH: Final = 64


def validation_projection(
    *,
    file_refs: Sequence[FileRef],
    mapping_digest: str,
    metadata: Mapping[str, Any],
    parser_version: str,
    canonicalize: Callable[[object], str],
) -> dict[str, Any]:
    """design §4.7 的**固定投影**（5 个键，不多不少；**键序即摘要输入序，禁调序**）。

    五个键与 DATA.md「校验摘要覆盖…」原文的四件事一一对应：

    - ``kind`` ＝ ``"IMPORT_VALIDATION"``：与 DOMAIN.md「内容摘要的固定投影」表的
      「快照」行同族（该行含「原始文件摘要」）；
    - ``parser_version`` ＝ ``parse.py::PARSER_VERSION``：「及解析器版本」；
    - ``files`` ＝ 每个上传件的三元组，按 ``(table_name, sha256)`` **升序**：
      「文件原始 SHA」；排序是为了让「同一组文件、不同上传顺序」得到同一摘要；
    - ``mapping_digest`` ＝ 64hex：「映射内容」；
    - ``metadata_digest`` ＝ ``sha256(canonicalize(metadata))``：「元数据」。

    ⚠ 形参名 ``mapping_digest`` 与本模块的同名函数**刻意同名**（design §4.7 的签名草图如此）：
    传进来的是**已算好**的 64hex 串，本函数内部不再调用 ``mapping_digest()``，故无遮蔽问题。
    """
    return {
        "kind": VALIDATION_DIGEST_KIND,
        "parser_version": parser_version,
        "files": [
            {"table_name": ref.table_name, "sha256": ref.sha256, "size_bytes": ref.size_bytes}
            for ref in sorted(file_refs, key=lambda ref: (ref.table_name, ref.sha256))
        ],
        "mapping_digest": mapping_digest,
        "metadata_digest": metadata_digest(metadata, canonicalize=canonicalize),
    }


def validation_digest(
    projection: Mapping[str, Any], *, canonicalize: Callable[[object], str]
) -> str:
    """``sha256(canonicalize(投影))`` 的 64 位小写十六进制（写进 ``imports.validation_digest``）。

    可复算、可跨进程比对：投影里**没有**任何运行时间／作业号／租约／随机资源 ID，
    故 M1-02 的 ``publishImport`` 能用同一份输入重算并比对（DATA.md「新发布时校验摘要
    必须仍匹配」）。这也是 design §5.3「双层保证」的摘要面：``mapping_digest`` 在输入里，
    新映射必然算出新摘要，即使某条路径漏了清空动作也会对撞失败。
    """
    return hashlib.sha256(canonicalize(projection).encode("utf-8")).hexdigest()


def mapping_digest(content: Mapping[str, Any], *, canonicalize: Callable[[object], str]) -> str:
    """映射摘要：``sha256(canonicalize(SourceMapping.model_dump(mode="json")))``。

    真值来源＝design §4.7 第 2 条的 ``source_mappings.digest``（64 位小写十六进制）。
    调用方传入的必须是**契约 DTO 的 ``model_dump(mode="json")``** 原样（不排序、不裁剪）：
    规范化交给注入进来的 ``canonicalize``。DDL 实测 ``CHECK(length(digest)=64)`` ⇒
    返回值长度恒等于 ``DIGEST_LENGTH``。
    """
    return hashlib.sha256(canonicalize(content).encode("utf-8")).hexdigest()


def metadata_digest(metadata: Mapping[str, Any], *, canonicalize: Callable[[object], str]) -> str:
    """``sha256(canonicalize(metadata))``。

    **输入面口径**（design §4.7）：``SOURCE_JSON``／``LEGACY_SYNTHETIC_JSON`` 取文件内嵌的
    ``metadata`` 对象；``SOURCE_CSV`` 取 ``__metadata__`` 件的**已解析 JSON 对象**（不是原字节）。
    实测 ``csv-mini/metadata.json`` 与 ``csv-mini/source.json`` 的 ``metadata`` 子树逐字相等
    ⇒ 两者的 ``metadata_digest`` 相同（AC-006 在元数据投影面也成立）。
    ⚠ 但两者的 ``files`` 段必然不同（原字节 SHA 不同）⇒ ``validation_digest`` **不相同**；
    design §4.7 已显式声明「AC-006 的同值指归一后的切片值与元数据投影同值，不指
    ``validation_digest`` 同值」（§12 U-9）。
    """
    return hashlib.sha256(canonicalize(metadata).encode("utf-8")).hexdigest()
