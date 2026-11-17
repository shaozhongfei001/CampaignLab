"""导入接入的领域数据形状（M1-01 · S2；design §4.1 / §4.3 / §4.6）。

字段序逐字按 design §4.1 的代码块；``Finding`` 的四个字段名与顺序逐字等于实测
``api/common.py::Issue.model_fields`` ＝ ``("code","location","message","severity")``
（design §4.1 正文的**实测**口径；与其示意代码块的顺序不一致，见回执 U-2）。
全部 ``@dataclass(frozen=True, slots=True)``；本文件禁 SQL、禁事务、禁 import
``api 层与 infra 层、禁持时钟（归一与校验是纯函数）。

``MappingLayout`` / ``SourceMoneyUnit`` / ``DedupMode`` 三个 ``Literal`` 依 design §3.1
「五个 Literal 别名一律定义在 domain/ingest/」落在本文件（``MappingSpec`` 的字段类型需要它们，
且 domain 禁 import api）；§11.1 的符号清单未点名其落点，见回执 U-3。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, Final, Literal

from campaignlab.domain.ingest.states import ImportFormat

__all__ = [
    "DEFAULT_LIMITS",
    "INGEST_SEVERITIES",
    "DedupMode",
    "FileRef",
    "Finding",
    "IngestLimits",
    "IngestResult",
    "LongColumnSpec",
    "MappingLayout",
    "MappingSpec",
    "NormalizedSlice",
    "RawSource",
    "RawTable",
    "SliceCounts",
    "SliceKey",
    "SourceMoneyUnit",
    "SourceRow",
    "UploadPayload",
    "UploadedFile",
]

MappingLayout = Literal["wide", "long"]
SourceMoneyUnit = Literal["CNY_YUAN", "CNY_FEN"]
DedupMode = Literal["SYNTHETIC_INTERVAL", "DISTINCT_CUSTOMER", "AGGREGATE_ONLY"]
SliceKey = tuple[str, str, str | None, str | None]
INGEST_SEVERITIES: Final = ("ERROR", "WARNING", "INFO")


@dataclass(frozen=True, slots=True)
class FileRef:
    """上传件的摘要登记三元组（design §4.1）。"""

    table_name: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class RawTable:
    """解析段的原样表：列名与行一律不做类型转换（转换在归一段，design §4.2）。"""

    name: str
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]


@dataclass(frozen=True, slots=True)
class RawSource:
    """四入口解析后的统一形状（design §4.1 / §4.2 ①）。"""

    format: ImportFormat
    tables: Mapping[str, RawTable]
    metadata: Mapping[str, Any]
    file_refs: tuple[FileRef, ...]


@dataclass(frozen=True, slots=True)
class SourceRow:
    """行列定位的追溯单元；``row_number`` 1-based 且只数数据行（design §4.4）。"""

    source_file_id: str
    table_name: str
    row_number: int


@dataclass(frozen=True, slots=True)
class NormalizedSlice:
    """规范切片行：14 维度 ＋ 9 计数 ＋ 12 金额（整数分）＋ 追溯（design §4.3）。"""

    id: str
    period: str
    cutoff: date
    branch: str | None
    subbranch: str | None
    channel: str | None
    strategy: str | None
    origin: str | None
    segment: str | None
    tag: str | None
    definition: str | None
    batch: str | None
    cohort: str | None
    offset: int
    customer_key: str | None
    counts: Mapping[str, int | None]
    money_fen: Mapping[str, int | None]
    source_row: SourceRow
    contributing_rows: tuple[SourceRow, ...]


@dataclass(frozen=True, slots=True)
class LongColumnSpec:
    """长表布局的三列名（design §4.1；实测 map-b.json.long_columns）。"""

    id: str
    metric: str
    value: str


@dataclass(frozen=True, slots=True)
class MappingSpec:
    """映射规格（design §4.1；三个映射名 dimensions/count_fields/money_fields 逐字如此）。"""

    id: str
    bank_id: str
    layout: MappingLayout
    entity_table: str
    counts_table: str | None
    dimensions: Mapping[str, str]
    count_fields: Mapping[str, str]
    money_fields: Mapping[str, str]
    source_money_unit: SourceMoneyUnit
    long_columns: LongColumnSpec | None
    codes: Mapping[str, Mapping[str, str]]
    dedup_mode: DedupMode


@dataclass(frozen=True, slots=True)
class Finding:
    """校验负例；四字段名与顺序逐字等于实测 ``Issue.model_fields``（design §4.1 正文）。"""

    code: str
    location: str
    message: str
    severity: str


@dataclass(frozen=True, slots=True)
class SliceCounts:
    """黄金计数四元组（design §4.1；S7 以此为断言对象）。"""

    slice_count: int
    stage_item_count: int
    entity_row_count: int
    count_cell_count: int


@dataclass(frozen=True, slots=True)
class IngestLimits:
    """结构性上限（design §4.1 ＋ §14.2 A283：10_000 / 90_000 为设计取值，1000 为契约字面量）。"""

    max_slices: int
    max_stage_items: int
    max_findings: int


@dataclass(frozen=True, slots=True)
class UploadedFile:
    """尚未解析的单个上传件；``raw`` 已过 §1.2 的流式体积判定（413 早于本层）。"""

    table_name: str
    raw: bytes
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class UploadPayload:
    """``parse()`` 的唯一入参（design §4.1）。"""

    format: ImportFormat
    files: tuple[UploadedFile, ...]


@dataclass(frozen=True, slots=True)
class IngestResult:
    """``ingest()`` 的唯一出参；不含任何 HTTP / DB 概念（design §4.1）。"""

    slices: tuple[NormalizedSlice, ...]
    findings: tuple[Finding, ...]
    counts: SliceCounts
    projection: Mapping[str, Any]


DEFAULT_LIMITS: Final = IngestLimits(max_slices=10_000, max_stage_items=90_000, max_findings=1000)
