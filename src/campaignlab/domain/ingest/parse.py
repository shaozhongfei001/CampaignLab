"""解析段的**骨架与注册表**（M1-01 · S2；design §4.2 ①）。

**本棒只落骨架与注册表**（§11.1 逐字）：``PARSE_ADAPTERS`` 现为**空**注册表，三个
``parse_*`` 适配器（``parse_legacy_synthetic``／``parse_source_json``／``parse_source_csv``）
由 **S3／S4** 填。空注册表是刻意的：占位适配器会把「哪个入口还没落地」这件事藏起来，
而 ``parse()`` 现在对任何入口都抛 ``NotImplementedError`` 并在消息里点名缺的是哪一个。

``parse()`` 是全 ``domain/ingest`` 内**唯一**读 ``payload.format`` 的函数，也是入口格式维的
**唯一分派点**（design §4.0 保证 1；§10 V6 的 AST 守护据此判红）⇒ 归一段与校验段的
形参面里根本不出现该维，想在下游分叉必须先改签名。

``legacy_mapping_to_source_mapping`` 是 legacy 通道「内嵌映射由后端生成配置」
（``architecture/DATA.md``「导入通道」表原文）的落点：把文件内嵌的 **camelCase** 映射
子树转成 ``MappingSpec``。实测 ``bank-a.json.mapping`` 的键为
``version / layout / entityTable / countsTable / dimensions / countFields / moneyFields /
moneyDivisor / longColumns / codes``，与 ``map-a.json`` 的 snake_case 面一一对应，
差别只有三处：``version`` ↔ ``id``、``moneyDivisor`` ↔ ``source_money_unit``、
以及 ``bank_id``／``dedup_mode`` **不在**内嵌子树里（``bankId`` 在文件顶层）。

本文件禁 SQL、禁事务、禁 import ``campaignlab.api``、禁持时钟。
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Final, Protocol, cast

from campaignlab.domain.errors import ValidationFailure
from campaignlab.domain.ingest.model import (
    DedupMode,
    LongColumnSpec,
    MappingLayout,
    MappingSpec,
    RawSource,
    SourceMoneyUnit,
    UploadPayload,
)
from campaignlab.domain.ingest.states import ImportFormat

__all__ = [
    "METADATA_TABLE_NAME",
    "PARSER_VERSION",
    "PARSE_ADAPTERS",
    "ParseAdapter",
    "legacy_mapping_to_source_mapping",
    "parse",
]

#: 解析器版本。进 ``validation_digest`` 的固定投影（design §4.7 的 ``parser_version`` 键，
#: 依据 ``architecture/DATA.md``「校验摘要覆盖文件原始 SHA、映射内容、元数据**及解析器版本**」）
#: ⇒ 解析口径一旦变更就必须递增此值，否则旧摘要会与新解析结果**假匹配**。
#: ⚠ design 未冻结其字面值（§12 无对应 U 项），本棒取 ``"1.0.0"`` 作为首个交付版本，
#: 已如实回报为升级项（S3／S4 落三个适配器时若改变解析口径，需一并递增）。
PARSER_VERSION: Final = "1.0.0"

#: ``SOURCE_CSV`` 的元数据件所用的表名（design §4.2 逐字；依据 ``architecture/DATA.md``
#: 「导入通道」表 ``SOURCE_CSV`` 行原文「必需一个 table_name 为 ``__metadata__`` 的 JSON 文件」）。
#: 长度 12 字符，落在活契约 ``AttachFile.table_name`` 的 ``maxLength=120`` 内，合法。
#: 缺失 → 422 ``EVIDENCE_REQUIRED``，``Issue.code="MISSING_METADATA_TABLE"``，
#: ``location="__metadata__#"``（design §4.4／§5.1 N17）。
METADATA_TABLE_NAME: Final = "__metadata__"

#: legacy 内嵌映射的 ``moneyDivisor`` → ``source_money_unit`` 的实测对应：
#: ``bank-a.json.mapping.moneyDivisor == 1`` ↔ ``map-a.json.source_money_unit == "CNY_YUAN"``；
#: ``bank-b.json.mapping.moneyDivisor == 100`` ↔ ``map-b.json.source_money_unit == "CNY_FEN"``。
_YUAN_DIVISOR: Final = 1
_FEN_DIVISOR: Final = 100


class ParseAdapter(Protocol):
    """入口格式 → ``RawSource`` 的适配器协议（S3／S4 落三个实现）。

    职责边界（design §4.2 表①）：把字节变成 ``RawSource`` —— JSON 解码、CSV 解码
    （UTF-8 或 UTF-8 BOM）、表名／列名／行的**原样保留**（一律不做类型转换，
    转换在归一段）、``schema_version`` 与 ``synthetic`` 的前置断言。
    **不得**感知 ``layout``（那是归一段的事，且只有一处分支）。
    """

    def __call__(self, payload: UploadPayload) -> RawSource: ...


#: 入口格式 → 适配器的**唯一**注册表（design §4.0 保证 1）。
#: 现为空：S3 落 ``parse_legacy_synthetic``／``parse_source_json``，S4 落 ``parse_source_csv``，
#: 三者逐键填进来即可，``parse()`` 与下游**一字不改**。
PARSE_ADAPTERS: Final[Mapping[ImportFormat, ParseAdapter]] = MappingProxyType({})


def parse(payload: UploadPayload) -> RawSource:
    """把「尚未解析的上传件集合」变成四入口统一的 ``RawSource``（design §4.1／§4.2 ①）。

    **全 ``domain/ingest`` 内唯一读 ``payload.format`` 的地方**：下游（``normalize``／
    ``validate``）的形参面里根本没有这一维，故「四入口共用一套规范校验」（AC-005／AC-006）
    不靠约定、靠结构。

    体积上限**不在这里判**：``UploadedFile.raw`` 是已经过 design §1.2 三段流式判定的字节
    （413 ``INPUT_TOO_LARGE`` 在到达本层之前就已抛，见 ``domain/ingest/limits.py`` 与
    裁定 **A299**）；本层只做**结构**上限（件数／规模），落在 ``validate`` 的 N18。
    """
    adapter = PARSE_ADAPTERS.get(payload.format)
    if adapter is None:
        raise NotImplementedError(
            "解析适配器尚未落地（design §11.1：三个 parse_* 由 S3／S4 交付）："
            f"{payload.format}；已注册的入口 = {sorted(PARSE_ADAPTERS)}"
        )
    return adapter(payload)


def legacy_mapping_to_source_mapping(
    legacy: Mapping[str, Any],
    *,
    bank_id: str,
    dedup_mode: DedupMode = "SYNTHETIC_INTERVAL",
) -> MappingSpec:
    """legacy 文件内嵌的 camelCase 映射 → ``MappingSpec``（design §4.2 ①）。

    ``bank_id`` 与 ``dedup_mode`` 必须由调用方给出：实测内嵌 ``mapping`` 子树里**没有**这两项
    （``bankId`` 在文件顶层；``dedup_mode`` 是 ``SourceMapping`` 契约面才有的字段，
    三份实测映射一律 ``SYNTHETIC_INTERVAL``，故取它为默认值）。

    两个必须知道的实测陷阱：

    1. ``longColumns`` 在 **A（宽表）文件里也存在**（实测 ``bank-a.json.mapping.longColumns``
       ＝ ``{"id":"切片键","metric":"指标码","value":"计数"}``），而权威的 ``map-a.json``
       的 ``long_columns`` 是 **``null``** ⇒ 本函数**只在** ``layout == "long"`` 时才构造
       ``LongColumnSpec``。照抄会让每一份 legacy 宽表都撞上 N9 ``LAYOUT_MISMATCH``。
    2. ``id`` 取内嵌的 ``version``（实测 ``bank-a.json.mapping.version == "MAP-A-1"``
       ＝ ``map-a.json.id``），**不是** ``bankId``。

    结构不合法一律抛 422 ``ValidationFailure``（``domain/errors.py::PROBLEM_CODES`` 的既有码，
    **禁**新增异常类）：legacy 映射是客户端可控输入，不该让 ``KeyError``／``TypeError`` 冒成 500。
    """
    layout_raw = _text_of(legacy, "layout")
    if layout_raw not in ("wide", "long"):
        raise ValidationFailure(f"legacy 映射的 layout 非法：{layout_raw!r}")
    layout = cast("MappingLayout", layout_raw)
    long_columns: LongColumnSpec | None = None
    if layout == "long":
        raw_long = legacy.get("longColumns")
        if not isinstance(raw_long, Mapping):
            raise ValidationFailure("layout=long 的 legacy 映射必须带 longColumns 对象")
        long_columns = LongColumnSpec(
            id=_text_of(raw_long, "id"),
            metric=_text_of(raw_long, "metric"),
            value=_text_of(raw_long, "value"),
        )
    divisor = legacy.get("moneyDivisor", _YUAN_DIVISOR)
    if divisor == _FEN_DIVISOR:
        unit: SourceMoneyUnit = "CNY_FEN"
    elif divisor == _YUAN_DIVISOR:
        unit = "CNY_YUAN"
    else:
        raise ValidationFailure(
            f"legacy 映射的 moneyDivisor 只支持 {_YUAN_DIVISOR}（元）或 {_FEN_DIVISOR}（分）："
            f"{divisor!r}"
        )
    return MappingSpec(
        id=_text_of(legacy, "version"),
        bank_id=bank_id,
        layout=layout,
        entity_table=_text_of(legacy, "entityTable"),
        counts_table=_text_of(legacy, "countsTable"),
        dimensions=_str_map_of(legacy, "dimensions"),
        count_fields=_str_map_of(legacy, "countFields"),
        money_fields=_str_map_of(legacy, "moneyFields"),
        source_money_unit=unit,
        long_columns=long_columns,
        codes=_codes_of(legacy),
        dedup_mode=dedup_mode,
    )


def _text_of(source: Mapping[str, Any], key: str) -> str:
    """取一个必须存在的非空字符串字段（legacy 映射是客户端可控输入，缺字段要报 422 不是 500）。"""
    value = source.get(key)
    if not isinstance(value, str) or not value:
        raise ValidationFailure(f"legacy 映射缺 {key}，或其值不是非空字符串：{value!r}")
    return value


def _str_map_of(source: Mapping[str, Any], key: str) -> Mapping[str, str]:
    """取一个 ``{规范键: 源列名}`` 的子树（``dimensions``／``countFields``／``moneyFields``）。"""
    value = source.get(key)
    if not isinstance(value, Mapping):
        raise ValidationFailure(f"legacy 映射缺 {key}，或其值不是对象：{value!r}")
    out: dict[str, str] = {}
    for name, column in value.items():
        if not isinstance(name, str) or not isinstance(column, str):
            raise ValidationFailure(
                f"legacy 映射 {key} 的键与值必须都是字符串：{name!r} → {column!r}"
            )
        out[name] = column
    return MappingProxyType(out)


def _codes_of(source: Mapping[str, Any]) -> Mapping[str, Mapping[str, str]]:
    """取 ``codes`` 子树：``{规范维度: {源代码: 标准值}}``。

    实测 A／B 均只有 ``channel``／``origin`` 两维。
    """
    value = source.get("codes")
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping):
        raise ValidationFailure(f"legacy 映射的 codes 必须是对象：{value!r}")
    out: dict[str, Mapping[str, str]] = {}
    for dimension, table in value.items():
        if not isinstance(dimension, str) or not isinstance(table, Mapping):
            raise ValidationFailure(
                f"legacy 映射 codes 的每一维必须是「字符串键 → 对象」：{dimension!r}"
            )
        inner: dict[str, str] = {}
        for raw, standard in table.items():
            if not isinstance(raw, str) or not isinstance(standard, str):
                raise ValidationFailure(
                    f"legacy 映射 codes.{dimension} 的键与值必须都是字符串：{raw!r} → {standard!r}"
                )
            inner[raw] = standard
        out[dimension] = MappingProxyType(inner)
    return MappingProxyType(out)
