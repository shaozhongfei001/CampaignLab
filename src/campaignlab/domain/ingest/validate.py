"""校验段：design §5.1 的 N1–N18 全部负例（M1-01 · S2；design §4.2 ③／§5.1）。

**这是全仓唯一的一套导入校验器**（卡片红线「禁写第二套校验器」；AC-005／AC-006 的实质）。
四入口（宽表／长表／CSV／SOURCE_JSON）在解析段之后统一为 ``RawSource``，
再经 ``normalize()`` 统一为 ``tuple[NormalizedSlice, ...]``，最后**一律**走本文件。

两条纯度纪律（design §4.0 保证 2；§10 V6 的 AST 守护据此判红）：

1. **完全格式无关**：本文件不出现入口格式维的类型别名，也从不读 ``RawSource`` 的该字段。
   一切判据只来自四个入参：``slices`` ／ ``mapping`` ／ ``metadata`` ／ ``source``。
2. **布局无关**：长表专属的负例（N5／N6／N7 与 N8 的计数列面）一律以
   ``mapping.long_columns``（**映射自身的字段**，不是布局枚举）为判据；而
   ``layout`` 与 ``long_columns`` 是否自洽本身由 N9 判红。故本文件里 ``layout``
   只出现 **1 次**，就在 N9 的 ``_check_layout_mismatch`` 里 —— 因为 design §5.1 的
   N9 行把这条负例**派给了本文件**，而它的判据在字面上就是 ``layout`` 与
   ``long_columns`` 的矛盾（§4.2 表③「validate 不感知布局」与 §5.1 N9 的落点存在张力，
   已按 §11.1「N1–N18 逐条一个 ``_check_*`` 落 validate.py」的更强约束实现，并如实回报）。

每条负例一个私有 ``_check_*``，**函数名后缀＝码名小写**（§11.1；便于 §10 V6 的 AST 守护
与 §10.1 的 PC 配方定位）。N13／N17／N18 各含多个码，仍各只有**一个** ``_check_*``
（其覆盖的码在各自 docstring 里逐条点名）。

``INGEST_ISSUE_CODES`` 里的都是 ``Issue.code``、**不是** ``Problem.code``（design §3.4）：
``Problem.code`` 一律只用 ``domain/errors.py::PROBLEM_CODES`` 的 20 项，本文件零发明。
``severity`` 一律取自 ``model.py::INGEST_SEVERITIES``，并在 ``_finding`` 里做**运行期成员校验**
（design §4.1 的冻结口径）。

本文件禁 SQL、禁事务、禁 import ``campaignlab.api``／``campaignlab.infra``、禁持时钟。
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from itertools import pairwise
from typing import Any, Final

from campaignlab.domain.ingest.locate import make_location
from campaignlab.domain.ingest.model import (
    DEFAULT_LIMITS,
    INGEST_SEVERITIES,
    Finding,
    IngestLimits,
    MappingSpec,
    NormalizedSlice,
    RawSource,
)
from campaignlab.domain.ingest.parse import METADATA_TABLE_NAME

__all__ = ["INGEST_ISSUE_CODES", "validate"]

#: design §5.1 负例矩阵 N1–N18 的 ``Issue.code`` **全集**（形态＝``Final[tuple[str, ...]]``，
#: 体例＝实测 ``domain/activity/states.py::ACTIVITY_ISSUE_CODES``）。N13／N17／N18 各含多码，
#: 故项数多于 18。末项 ``NOT_AN_INTEGER`` 来自 design §4.5「CSV 通道下 ``_coerce_cell`` 用
#: ``int(text)``，失败 → ``Issue.code="NOT_AN_INTEGER"``」—— 它不在 §5.1 的表里，
#: 但 §3.4 要求「本文出现的**每个** ``Issue.code`` 都在 ``INGEST_ISSUE_CODES`` ∪
#: ``INGEST_STATE_ISSUE_CODES`` 内」，故必须登记。
INGEST_ISSUE_CODES: Final[tuple[str, ...]] = (
    "DUPLICATE_SLICE",  # N1
    "NEGATIVE_COUNT",  # N2
    "FUNNEL_INVERSION",  # N3
    "ROW_LENGTH_MISMATCH",  # N4
    "DUPLICATE_CODE",  # N5
    "ORPHAN_SLICE",  # N6（裁定 A304：「未知切片」与「孤立切片」同指一事，只此一个码）
    "MISSING_STAGE",  # N7
    "UNKNOWN_COLUMN",  # N8
    "LAYOUT_MISMATCH",  # N9
    "UNKNOWN_CODE",  # N10
    "UNKNOWN_DICTIONARY_REF",  # N11
    "ORIGIN_STRATEGY_MISMATCH",  # N12
    "INVALID_PERIOD",  # N13
    "INVALID_CUTOFF",  # N13
    "CUTOFF_OUTSIDE_PERIOD",  # N14
    "INVALID_MONEY",  # N15
    "NEGATIVE_SALE",  # N16（裁定 A303：硬 ERROR，不是 WARNING）
    "MISSING_METADATA_TABLE",  # N17
    "NOT_SYNTHETIC",  # N17
    "MISSING_SEMANTIC_KEY",  # N17（唯一一条 WARNING，不阻断）
    "TOO_MANY_SLICES",  # N18
    "TOO_MANY_STAGE_ITEMS",  # N18
    "TOO_MANY_ISSUES",  # N18
    "NOT_AN_INTEGER",  # design §4.5（计数单元的整数归一失败）
)

#: 活契约 ``Issue.properties.message.maxLength``（本轮实测 **500**）。
_MESSAGE_MAX_LENGTH: Final = 500

#: 金额绝对值上限（分）。真值来源＝``contracts/source-json.schema.json`` 的
#: ``amount_fen``／``value_fen`` 的 ``minimum``／``maximum``（本轮实测均为
#: ``-9000000000000``／``9000000000000``）。design §4.5 要求「一律**实取**、禁写死」，
#: 但纯领域层不能在运行期读 ``contracts/``（那是文件 IO，且 ``jsonschema`` 只是 dev 依赖）
#: ⇒ 这条对撞断言只能落在 ``tests/**``（S6 的写权面，本棒无写权）。已如实回报为升级项。
_MONEY_ABS_LIMIT_FEN: Final = 9_000_000_000_000

#: design §4.4 的 ``<section>``：恰为 ``MappingSpec`` 的三个映射名（实测键名逐字如此）。
_SECTION_DIMENSIONS: Final = "dimensions"
_SECTION_COUNT_FIELDS: Final = "count_fields"
_SECTION_MONEY_FIELDS: Final = "money_fields"

#: N3 的名单阶段链（``architecture/DATA.md`` 原文「名单阶段链逐级不增」）。
#: **只此 6 级**：``capacity``／``intentCount``／``activityCount`` 刻意**不纳入**
#: （§9.1 点名的失败模式：DATA.md 只说「名单阶段链」，且「容量、意向次数、活动特色依字典单位」）。
_FUNNEL_CHAIN: Final[tuple[str, ...]] = (
    "eligible",
    "sent",
    "success",
    "executed",
    "contacted",
    "effective",
)

#: N16 的**销量类** 5 键（非负）；其余 7 键（``depositDemand``／``depositTerm``／``aum``／
#: ``deposit``／``wealth``／``fund``／``loan``）是**变动类**，可负
#: （design §4.5；裁定 **A303** 追认该 7/5 划分为权威，禁自行另分）。
_SALE_KEYS: Final[tuple[str, ...]] = (
    "wealthSale",
    "nonCashWealthSale",
    "fundSale",
    "nonMoneyFundSale",
    "insuranceSale",
)

#: N11 的「规范维度 → ``metadata`` 里的字典键」三对
#: （design §5.1 N11 逐字点名 branch／channel／strategy）。
_DICTIONARY_DIMENSIONS: Final[tuple[tuple[str, str], ...]] = (
    ("branch", "branches"),
    ("channel", "channels"),
    ("strategy", "strategies"),
)

_PERIOD_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")
_CUTOFF_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

#: ``_entity_cells`` 的形状：1-based 实体行号 → ``{(段名, 规范键): 原样单元格值}``。
_EntityCells = Mapping[int, Mapping[tuple[str, str], object]]


def validate(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits = DEFAULT_LIMITS,
) -> tuple[Finding, ...]:
    """跑完 §5.1 的 N1–N18，按 N 序返回全部 ``Finding``（design §4.2 ③）。

    ⚠ **对 §4.2 签名的唯一扩展**：多了一个带默认值的 keyword-only 形参 ``limits``。
    理由是硬约束相撞：§5.1 的 N18 判据是 ``len(slices) > limits.max_slices`` 等三条，
    而 §4.1 的 ``ingest(source, *, mapping, limits=DEFAULT_LIMITS)`` 收 ``limits``、
    §4.2 的 ``validate(...)`` 签名里却没有它 ⇒ 不扩就无法让调用方传进来的上限生效。
    带默认值 ⇒ §4.2 原样的调用形态仍然合法（``public_frozen`` 面在 ``api.py``，
    本函数不在其中；§10 V6 ② 只要求形参名集合不含入口格式维，本扩展不触碰该判据）。

    返回的 ``Finding`` 四字段名与顺序逐字等于 ``api/common.py::Issue`` 的实测
    ``model_fields``（裁定 **A297**）⇒ application 层的映射冻结为
    ``Issue(code=f.code, location=f.location, message=f.message, severity=f.severity)``，
    两层之间禁做任何字段改名或增删。
    """
    entity_cells = _entity_cells(source, mapping=mapping)
    findings: list[Finding] = []

    def run(check: Callable[..., tuple[Finding, ...]]) -> None:
        findings.extend(
            check(
                slices,
                mapping=mapping,
                metadata=metadata,
                source=source,
                limits=limits,
                entity_cells=entity_cells,
            )
        )

    run(_check_duplicate_slice)  # N1
    run(_check_negative_count)  # N2 ＋ §4.5 的 NOT_AN_INTEGER
    run(_check_funnel_inversion)  # N3
    run(_check_row_length_mismatch)  # N4
    run(_check_duplicate_code)  # N5
    run(_check_orphan_slice)  # N6
    run(_check_missing_stage)  # N7
    run(_check_unknown_column)  # N8
    run(_check_layout_mismatch)  # N9
    run(_check_unknown_code)  # N10
    run(_check_unknown_dictionary_ref)  # N11
    run(_check_origin_strategy_mismatch)  # N12
    run(_check_invalid_period)  # N13
    run(_check_cutoff_outside_period)  # N14
    run(_check_invalid_money)  # N15
    run(_check_negative_sale)  # N16
    run(_check_missing_metadata_table)  # N17
    # N18 必须最后跑：它的 TOO_MANY_ISSUES 判据是「已积累的负例数」。
    findings.extend(
        _check_too_many_slices(
            slices,
            mapping=mapping,
            metadata=metadata,
            source=source,
            limits=limits,
            entity_cells=entity_cells,
            findings=tuple(findings),
        )
    )
    return tuple(findings)


# --------------------------------------------------------------------- N1–N18 的逐条 _check_*


def _check_duplicate_slice(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N1 重复切片**（ERROR / ``DUPLICATE_SLICE``）。

    触发：``entity_table`` 内两行的 ``dimensions.id`` 相同。
    ``location`` ＝ ``<entity_table>#r<**后出现**行的 1-based 行号>/dimensions/id``，
    ``message`` 里给出**首次**出现的行号 —— §9.1 点名的失败模式正是
    「用 ``dict`` 去重时保留首行而 ``location`` 指向首行（应指向后出现的行）」。

    刻意扫**实体表原文**而不是扫 ``slices``：长表布局下切片的 ``source_row`` 指向
    ``counts_table`` 的 M01 行（design §4.4 的长表定位口径），而 N1 的 ``location``
    要求的是**实体表**行号 ⇒ 只有回到实体表才能对两种布局都给出同一个正确定位。
    同时「只查相邻行 ⇒ 隔行重复漏检」也被排除（全表扫描，非相邻比较）。
    """
    table = source.tables.get(mapping.entity_table)
    id_column = mapping.dimensions.get("id")
    if table is None or id_column is None or id_column not in table.columns:
        return ()
    index = table.columns.index(id_column)
    first_seen: dict[str, int] = {}
    out: list[Finding] = []
    for row_number, row in enumerate(table.rows, start=1):
        if index >= len(row) or row[index] is None:
            continue
        slice_id = str(row[index])
        if not slice_id:
            continue
        first = first_seen.get(slice_id)
        if first is None:
            first_seen[slice_id] = row_number
            continue
        out.append(
            _finding(
                "DUPLICATE_SLICE",
                _field_location(table.name, row_number, _SECTION_DIMENSIONS, "id"),
                f"切片号重复：{slice_id} 首次出现在第 {first} 行，"
                f"第 {row_number} 行是后出现的重复行",
            )
        )
    return tuple(out)


def _check_negative_count(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N2 负人数**（ERROR / ``NEGATIVE_COUNT``）＋ design §4.5 的 ``NOT_AN_INTEGER``。

    N2：任一 ``count_fields`` 归一后 ``< 0``（DATA.md「BIGINT 非负」），
    ``location`` ＝ ``<table>#r<row>/count_fields/<规范键>``。

    ``NOT_AN_INTEGER`` 挂在同一个 ``_check_*`` 里（§11.1 要求「N1–N18 逐条一个」，
    而该码不在 N 表内、又必须被登记）：判据是**按列名寻址**的计数单元其原文非空却
    转不成 ``int`` —— 正是 design §4.5「CSV 通道下 ``_coerce_cell`` 用 ``int(text)``，
    失败 → ``NOT_AN_INTEGER``」那一面（CSV 通道的计数单元就是按列名寻址的）。

    §9.1 点名的失败模式在此被排除：``_coerce_cell`` 用 ``int(text)`` 而不是 ``isdigit()``，
    故 ``-1`` 归一成 ``-1`` ⇒ 报 ``NEGATIVE_COUNT``（正确的码），不会被误报成
    ``NOT_AN_INTEGER``（码错＝证据不可用）。
    """
    out: list[Finding] = []
    for row in slices:
        anchor = row.source_row
        for key, value in row.counts.items():
            if value is not None and value < 0:
                out.append(
                    _finding(
                        "NEGATIVE_COUNT",
                        _field_location(
                            anchor.table_name, anchor.row_number, _SECTION_COUNT_FIELDS, key
                        ),
                        f"计数为负：{key} = {value}（BIGINT 非负）",
                    )
                )
    entity_name = mapping.entity_table
    for row_number, cells in entity_cells.items():
        for key in mapping.count_fields:
            raw = cells.get((_SECTION_COUNT_FIELDS, key))
            if raw is not None and _is_unparseable_int(raw):
                out.append(
                    _finding(
                        "NOT_AN_INTEGER",
                        _field_location(entity_name, row_number, _SECTION_COUNT_FIELDS, key),
                        f"计数单元不是整数：{key} 的源值 {raw!r}"
                        f"（表 {entity_name} 第 {row_number} 行）",
                    )
                )
    return tuple(out)


def _check_funnel_inversion(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N3 层级倒置**（ERROR / ``FUNNEL_INVERSION``）。

    链条 ``eligible ≥ sent ≥ success ≥ executed ≥ contacted ≥ effective``
    （DATA.md 原文「名单阶段链逐级不增」）。``location`` 指到**被破坏的那一级**
    （即下级键），``message`` 必须同时给出**上一级的键名与两个值**（design §5.1 N3 硬要求）。

    §9.1 点名的两个失败模式在此被排除：① ``None``（源缺值）**不参与**比较
    （既不 ``TypeError`` 也不静默跳过整条链，只跳过含缺值的那一级）；
    ② ``capacity``／``intentCount``／``activityCount`` **不在**链条里。
    """
    out: list[Finding] = []
    for row in slices:
        anchor = row.source_row
        for upper, lower in pairwise(_FUNNEL_CHAIN):
            high = row.counts.get(upper)
            low = row.counts.get(lower)
            if high is None or low is None:
                continue
            if low > high:
                out.append(
                    _finding(
                        "FUNNEL_INVERSION",
                        _field_location(
                            anchor.table_name, anchor.row_number, _SECTION_COUNT_FIELDS, lower
                        ),
                        f"名单阶段链逐级不增被破坏：上一级 {upper} = {high}，本级 {lower} = {low}",
                    )
                )
    return tuple(out)


def _check_row_length_mismatch(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N4 错误行长**（ERROR / ``ROW_LENGTH_MISMATCH``），``location`` 用**整行**形状。

    触发：``len(row) != len(columns)``（实测宽表 35 列、B 实体表 26 列、B 长表 3 列）。
    扫 ``source.tables`` 的**全部**表 ⇒ 天然格式无关、布局无关。

    §9.1 点名的失败模式（「CSV 里带引号逗号的单元格被朴素 ``split(',')`` 切碎 ⇒ 行长误判」）
    属**解析段**的义务：本段拿到的是解析段用 ``csv`` 模块切好的 ``RawTable.rows``，
    只做长度对撞，不重新切分。
    """
    out: list[Finding] = []
    for table in source.tables.values():
        expected = len(table.columns)
        for row_number, row in enumerate(table.rows, start=1):
            if len(row) != expected:
                out.append(
                    _finding(
                        "ROW_LENGTH_MISMATCH",
                        make_location(table_name=table.name, row_number=row_number),
                        f"行长不符：期望 {expected} 列，实测 {len(row)} 列",
                    )
                )
    return tuple(out)


def _check_duplicate_code(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N5 重复码**（ERROR / ``DUPLICATE_CODE``），``message`` 含**首次出现的行号**。

    触发：同一 ``(切片键, 指标码)`` 出现两次（DATA.md「long 的阶段先按长表切片键和
    指标码唯一连接」「重复码…均报错」）。``location`` ＝ ``<counts_table>#r<row>``（整行形状）。

    判据是 ``mapping.long_columns`` 给出的**两个列名**（design §9.1 点名的失败模式正是
    「用 ``指标码`` 这个源列名硬编码而不是 ``mapping.long_columns["metric"]`` 取值 ⇒
    换一份映射就失效」）。宽表映射的 ``long_columns`` 为 ``None`` ⇒ 本条自动不适用。
    """
    long_columns = mapping.long_columns
    counts_name = mapping.counts_table
    table = None if counts_name is None else source.tables.get(counts_name)
    if long_columns is None or table is None:
        return ()
    if long_columns.id not in table.columns or long_columns.metric not in table.columns:
        return ()
    id_index = table.columns.index(long_columns.id)
    metric_index = table.columns.index(long_columns.metric)
    first_seen: dict[tuple[object, object], int] = {}
    out: list[Finding] = []
    for row_number, row in enumerate(table.rows, start=1):
        if id_index >= len(row) or metric_index >= len(row):
            continue
        pair = (row[id_index], row[metric_index])
        first = first_seen.get(pair)
        if first is None:
            first_seen[pair] = row_number
            continue
        out.append(
            _finding(
                "DUPLICATE_CODE",
                make_location(table_name=table.name, row_number=row_number),
                f"（切片键, 指标码）重复：{pair[0]!r} / {pair[1]!r} 首次出现在第 {first} 行",
            )
        )
    return tuple(out)


def _check_orphan_slice(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N6 孤立切片**（ERROR / ``ORPHAN_SLICE``）。

    触发：长表的 ``切片键`` 在 ``entity_table`` 的 ``dimensions.id`` 集合里不存在。
    ``location`` ＝ ``<counts_table>#r<row>``（指到长表那一行）。

    裁定 **A304**：DATA.md 的「未知切片」与 AC-005 的「孤立切片」**同指一事**，
    只登记 ``ORPHAN_SLICE`` 一个码（禁发明 ``UNKNOWN_SLICE``）；「切片号里的 branch／channel
    分量解析不出来」是 N11 ``UNKNOWN_DICTIONARY_REF`` 的事，两个码禁混用。
    同理，「实体表有切片但长表没有任何阶段项」是 N7 ``MISSING_STAGE``（§9.1 明令禁混）。
    """
    long_columns = mapping.long_columns
    counts_name = mapping.counts_table
    table = None if counts_name is None else source.tables.get(counts_name)
    entity = source.tables.get(mapping.entity_table)
    id_column = mapping.dimensions.get("id")
    if long_columns is None or table is None or entity is None:
        return ()
    if long_columns.id not in table.columns or id_column is None:
        return ()
    if id_column not in entity.columns:
        return ()
    key_index = table.columns.index(long_columns.id)
    id_index = entity.columns.index(id_column)
    known = {
        str(row[id_index])
        for row in entity.rows
        if id_index < len(row) and row[id_index] is not None
    }
    out: list[Finding] = []
    for row_number, row in enumerate(table.rows, start=1):
        if key_index >= len(row) or row[key_index] is None:
            continue
        slice_key = str(row[key_index])
        if slice_key in known:
            continue
        out.append(
            _finding(
                "ORPHAN_SLICE",
                make_location(table_name=table.name, row_number=row_number),
                f"孤立切片：切片键 {slice_key} 不在实体表 {entity.name} 的 dimensions.id 集合内",
            )
        )
    return tuple(out)


def _check_missing_stage(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N7 缺必填阶段**（ERROR / ``MISSING_STAGE``），``message`` 列出缺失的规范键。

    触发：某切片缺 9 个 ``count_fields`` 规范键中的任意一个（DATA.md「缺必填阶段…均报错」）。
    ``location`` ＝ ``<entity_table>#r<该切片所在行>`` —— 长表布局下切片的 ``source_row``
    指向 ``counts_table``（design §4.4），故行号一律经 ``_entity_id_rows`` 换算回**实体表**行号。

    只在映射声明了长表透视（``long_columns`` 非 ``None``）时适用：宽表的计数是同一行的列，
    「缺阶段」在那里表现为单元格缺值，按 DATA.md「缺值以 null 表达并带证据」是合法的。
    """
    if mapping.long_columns is None:
        return ()
    id_rows = _entity_id_rows(entity_cells)
    out: list[Finding] = []
    for row in slices:
        missing = tuple(key for key in mapping.count_fields if row.counts.get(key) is None)
        if not missing:
            continue
        row_number = id_rows.get(row.id, row.source_row.row_number)
        out.append(
            _finding(
                "MISSING_STAGE",
                make_location(table_name=mapping.entity_table, row_number=row_number),
                f"缺必填阶段：{'、'.join(missing)}",
            )
        )
    return tuple(out)


def _check_unknown_column(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N8 映射引用不存在列**（ERROR / ``UNKNOWN_COLUMN``），``message`` 含**源列名原文**。

    ``location`` ＝ ``<table>#/columns/<该源列名在 mapping 里的规范键>``（design §5.1 N8 逐字：
    指针段放的是**规范键**，不是列下标）。

    判据面（一律由 ``mapping`` 驱动，故格式无关）：

    - ``dimensions`` 与 ``money_fields`` 的源列名 ⊆ ``entity_table.columns``
      （实测 A 的 35 列 ＝ 14＋9＋12 全在宽表；B 的 26 列 ＝ 14＋12 全在实体表）；
    - ``long_columns is None``（宽表）⇒ ``count_fields`` 的源列名 ⊆ ``counts_table.columns``；
    - ``long_columns`` 非 ``None``（长表）⇒ ``count_fields`` 的值是**指标码**而不是列名
      （B 实测为 ``M01…M09``），此时改为要求 ``long_columns`` 的三个列名
      ⊆ ``counts_table.columns``。
      若照宽表口径去查，B 会假报 9 条 ``UNKNOWN_COLUMN``。

    表本身不在 ``source.tables`` 里时本条**不报**（否则一条缺表会炸出 26 条列级负例，
    把真正的证据淹掉）；缺表由 N17／解析段的前置断言负责。
    """
    out: list[Finding] = []
    entity = source.tables.get(mapping.entity_table)
    if entity is not None:
        columns = frozenset(entity.columns)
        for section, pairs in (
            (_SECTION_DIMENSIONS, mapping.dimensions),
            (_SECTION_MONEY_FIELDS, mapping.money_fields),
        ):
            for key, column in pairs.items():
                if column in columns:
                    continue
                out.append(
                    _finding(
                        "UNKNOWN_COLUMN",
                        make_location(table_name=entity.name, pointer=f"/columns/{key}"),
                        f"映射引用不存在的列：{section}.{key} → {column!r}"
                        f"（表 {entity.name} 无此列）",
                    )
                )
    counts_name = mapping.counts_table
    counts_table = None if counts_name is None else source.tables.get(counts_name)
    if counts_table is None:
        return tuple(out)
    counts_columns = frozenset(counts_table.columns)
    long_columns = mapping.long_columns
    if long_columns is None:
        required: tuple[tuple[str, str], ...] = tuple(mapping.count_fields.items())
    else:
        required = (
            ("id", long_columns.id),
            ("metric", long_columns.metric),
            ("value", long_columns.value),
        )
    for key, column in required:
        if column in counts_columns:
            continue
        out.append(
            _finding(
                "UNKNOWN_COLUMN",
                make_location(table_name=counts_table.name, pointer=f"/columns/{key}"),
                f"映射引用不存在的列：{key} → {column!r}（表 {counts_table.name} 无此列）",
            )
        )
    return tuple(out)


def _check_layout_mismatch(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N9 ``layout`` 与 ``long_columns`` 矛盾**（ERROR / ``LAYOUT_MISMATCH``）。

    触发：``layout == "long"`` 而 ``long_columns is None``，或 ``layout == "wide"`` 而
    ``long_columns is not None``。``location`` ＝ ``/layout``（**无表名**的映射面定位，
    与 design §3.4 的 ``/state`` · ``/mapping`` 同族），HTTP 面是 ``configureImport`` 的
    422 ``VALIDATION_ERROR``（映射面错误在配置时即可判，不必等校验作业）。

    这是本文件里**唯一**出现 ``layout`` 的地方 —— design §5.1 的 N9 行把这条负例派给了
    ``validate.py``（§11.1：「N1–N18 逐条一个 ``_check_*``」），而它的判据在字面上就是
    ``layout`` 与 ``long_columns`` 的矛盾，无从回避。§4.0 保证 2 与 §10 V6 ③ 约束的是
    ``normalize.py`` 内的布局分支恰 1 处，本条不触碰该判据。
    """
    declared_long = mapping.layout == "long"
    if declared_long == (mapping.long_columns is not None):
        return ()
    actual = "非 null" if mapping.long_columns is not None else "null"
    return (
        _finding(
            "LAYOUT_MISMATCH",
            make_location(table_name="", pointer="/layout"),
            f"layout 与 long_columns 矛盾：layout={mapping.layout!r} 而 long_columns={actual}",
        ),
    )


def _check_unknown_code(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N10 未知码值**（ERROR / ``UNKNOWN_CODE``），``message`` 含**源值原文**。

    触发：源列值不在 ``mapping.codes[<维度>]`` 的键集合内（实测 A 的 ``codes.channel`` 6 项、
    ``codes.origin`` 2 项）。判据落在**归一后的值**上：``normalize._map_code`` 对未知码值
    **原样保留**（不吞成 ``None``），故「归一后的值不在该码表的标准值集合内」
    ⇔「源值不在码表的键集合内」，且 ``message`` 里拿到的正是源值原文。
    """
    out: list[Finding] = []
    for row in slices:
        anchor = row.source_row
        for key, code_table in mapping.codes.items():
            value = getattr(row, key, None)
            if not isinstance(value, str) or not value:
                continue
            if value in set(code_table.values()):
                continue
            out.append(
                _finding(
                    "UNKNOWN_CODE",
                    _field_location(anchor.table_name, anchor.row_number, _SECTION_DIMENSIONS, key),
                    f"未知码值：{key} 的源值 {value!r} 不在映射 codes.{key} 的标准值集合内",
                )
            )
    return tuple(out)


def _check_unknown_dictionary_ref(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N11 字典引用不存在**（ERROR / ``UNKNOWN_DICTIONARY_REF``；DATA.md「字典引用存在」）。

    触发：``branch``／``channel``／``strategy`` 归一后的**标准值**不在 ``metadata`` 的对应字典里
    （实测 ``metadata.branches`` 为 5 项 list、``metadata.channels`` 为 6 键 dict、
    ``metadata.strategies`` 为 3 项 list）⇒ 两种容器形态都要认：``Mapping`` 取键集合，
    序列取每项的 ``id``。字典本身缺失时**不判**（无从判定，禁把「没有字典」误报成
    「引用不存在」）。

    裁定 **A304**：本条正是「切片号里的分量解析不出来」的归属面，与 N6 ``ORPHAN_SLICE``
    （长表有、实体表无）职责不重叠。
    """
    out: list[Finding] = []
    for row in slices:
        anchor = row.source_row
        for key, metadata_key in _DICTIONARY_DIMENSIONS:
            allowed = _dictionary_ids(metadata, metadata_key)
            if not allowed:
                continue
            value = getattr(row, key, None)
            if not isinstance(value, str) or not value:
                continue
            if value in allowed:
                continue
            out.append(
                _finding(
                    "UNKNOWN_DICTIONARY_REF",
                    _field_location(anchor.table_name, anchor.row_number, _SECTION_DIMENSIONS, key),
                    f"字典引用不存在：{key}={value!r} 不在 metadata.{metadata_key} 内",
                )
            )
    return tuple(out)


def _check_origin_strategy_mismatch(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N12 来源与策略不匹配**（ERROR / ``ORIGIN_STRATEGY_MISMATCH``；DATA.md「来源与策略匹配」）。

    触发：行的 ``origin`` 与 ``metadata.strategies[<strategy>].origin`` 不一致。
    ``location`` 指到 ``dimensions/origin``（design §5.1 N12 逐字）。
    ``metadata.strategies`` 实测是 **list**（不是 dict），故按每项的 ``id`` 建索引；
    策略号在字典里查不到时**不判**（那是 N11 的职责，两个码禁混用）。
    """
    origins = _strategy_origins(metadata)
    if not origins:
        return ()
    out: list[Finding] = []
    for row in slices:
        anchor = row.source_row
        strategy = row.strategy
        if not isinstance(strategy, str) or not strategy:
            continue
        expected = origins.get(strategy)
        actual = row.origin
        if expected is None or not isinstance(actual, str):
            continue
        if actual == expected:
            continue
        out.append(
            _finding(
                "ORIGIN_STRATEGY_MISMATCH",
                _field_location(
                    anchor.table_name, anchor.row_number, _SECTION_DIMENSIONS, "origin"
                ),
                f"来源与策略不匹配：strategy={strategy} 登记的 "
                f"origin={expected!r}，本行 origin={actual!r}",
            )
        )
    return tuple(out)


def _check_invalid_period(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N13 月份／日历非法**（ERROR；两个码 ``INVALID_PERIOD`` / ``INVALID_CUTOFF``）。

    触发：``period`` 不是 ``YYYY-MM`` 或不是合法日历月；``cutoff`` 不是合法 ``YYYY-MM-DD``
    （DATA.md「月份和日期用解析器校验日历」）。

    判据落在**实体表的源文本**上而不是 ``NormalizedSlice`` 上：``period`` 虽是 ``str``、
    但 ``cutoff`` 在模型里是**非空** ``date``（归一段对非法日历日落 ``date.min`` 占位），
    只有回到源文本才能把「非法」与「合法但很早」区分开。
    ``_CUTOFF_RE`` 先卡死 ``YYYY-MM-DD`` 形状，再交 ``date.fromisoformat`` 判日历 ——
    Python 3.11+ 的 ``fromisoformat`` 也吃 ``20250930`` 这种基本格式，不加正则就会漏判。
    """
    entity_name = mapping.entity_table
    out: list[Finding] = []
    for row_number, cells in entity_cells.items():
        if (_SECTION_DIMENSIONS, "period") in cells:
            period = cells[(_SECTION_DIMENSIONS, "period")]
            if not isinstance(period, str) or not _is_period(period):
                out.append(
                    _finding(
                        "INVALID_PERIOD",
                        _field_location(entity_name, row_number, _SECTION_DIMENSIONS, "period"),
                        f"月份非法：{period!r} 不是合法的 YYYY-MM 日历月",
                    )
                )
        if (_SECTION_DIMENSIONS, "cutoff") in cells:
            cutoff = cells[(_SECTION_DIMENSIONS, "cutoff")]
            if not isinstance(cutoff, str) or not _is_cutoff(cutoff):
                out.append(
                    _finding(
                        "INVALID_CUTOFF",
                        _field_location(entity_name, row_number, _SECTION_DIMENSIONS, "cutoff"),
                        f"日期非法：{cutoff!r} 不是合法的 YYYY-MM-DD 日历日",
                    )
                )
    return tuple(out)


def _check_cutoff_outside_period(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N14 ``cutoff`` 不在 ``period`` 内**（ERROR / ``CUTOFF_OUTSIDE_PERIOD``）。

    DATA.md 原文「cutoff 必须在 period」⇒ 判据是 ``cutoff`` 的 ``YYYY-MM`` 前缀
    与 ``period`` 逐字相等。源文本本身非法时**不判**（N13 已判红，
    重复报两条会让同一个脏值产生两个码，证据面反而模糊）。
    """
    entity_name = mapping.entity_table
    out: list[Finding] = []
    for row_number, cells in entity_cells.items():
        period = cells.get((_SECTION_DIMENSIONS, "period"))
        cutoff = cells.get((_SECTION_DIMENSIONS, "cutoff"))
        if not isinstance(period, str) or not isinstance(cutoff, str):
            continue
        if not _is_period(period) or not _is_cutoff(cutoff):
            continue
        if cutoff[:7] == period:
            continue
        out.append(
            _finding(
                "CUTOFF_OUTSIDE_PERIOD",
                _field_location(entity_name, row_number, _SECTION_DIMENSIONS, "cutoff"),
                f"cutoff {cutoff} 不在 period {period} 内",
            )
        )
    return tuple(out)


def _check_invalid_money(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N15 金额精度／类型／上下限**（ERROR / ``INVALID_MONEY``）。

    四条触发面（design §5.1 N15 逐字）：``CNY_YUAN`` 下 ``元×100`` 非整；``CNY_FEN`` 下带小数；
    文本无法解析为 ``Decimal``；绝对值超契约上下限。

    前三条的判据是「**源值存在**而归一结果为 ``None``」—— 直接复用 ``normalize._to_fen``
    的结论，**不在本文件重算一遍** ``Decimal`` 缩放（那会是第二份金额实现，
    正是卡片红线「禁用浮点算金额分」要防的口径分叉）。第四条用 ``_MONEY_ABS_LIMIT_FEN``
    对**已归一的整数分**取绝对值比对。

    ``location`` ＝ ``<table>#r<row>/money_fields/<规范键>``，行号一律换算回**实体表**行
    （金额在两种布局下都住在实体表：实测 A 的 ``月度宽表``、B 的 ``统计切片``）。
    """
    id_rows = _entity_id_rows(entity_cells)
    out: list[Finding] = []
    for row in slices:
        row_number = id_rows.get(row.id, row.source_row.row_number)
        cells = entity_cells.get(row_number, {})
        for key, value in row.money_fen.items():
            location = _field_location(mapping.entity_table, row_number, _SECTION_MONEY_FIELDS, key)
            if value is None:
                raw = cells.get((_SECTION_MONEY_FIELDS, key))
                if _is_present(raw):
                    out.append(
                        _finding(
                            "INVALID_MONEY",
                            location,
                            f"金额无法归一为整数分：{key} 的源值 {raw!r}"
                            f"（单位 {mapping.source_money_unit}）",
                        )
                    )
                continue
            if abs(value) > _MONEY_ABS_LIMIT_FEN:
                out.append(
                    _finding(
                        "INVALID_MONEY",
                        location,
                        f"金额绝对值超出契约上下限：{key} = {value} 分"
                        f"（上限 ±{_MONEY_ABS_LIMIT_FEN}）",
                    )
                )
    return tuple(out)


def _check_negative_sale(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N16 销量为负**（ERROR / ``NEGATIVE_SALE``；DATA.md「余额增量可为负，销量为非负」）。

    裁定 **A303** 追认 design §4.5 的 7/5 划分为权威：``depositDemand``／``depositTerm``／
    ``aum``／``deposit``／``wealth``／``fund``／``loan`` 是**变动类**（可负），
    ``wealthSale``／``nonCashWealthSale``／``fundSale``／``nonMoneyFundSale``／
    ``insuranceSale`` 是**销量类**（非负）⇒ 销量类出现负数一律 **ERROR**（不是 WARNING）。
    放行会直接毁掉黄金值（实测 ``analytics-golden.json`` 的 ``current.wealthSale == "22809600"``）。
    """
    out: list[Finding] = []
    for row in slices:
        anchor = row.source_row
        for key in _SALE_KEYS:
            value = row.money_fen.get(key)
            if value is None or value >= 0:
                continue
            out.append(
                _finding(
                    "NEGATIVE_SALE",
                    _field_location(
                        anchor.table_name, anchor.row_number, _SECTION_MONEY_FIELDS, key
                    ),
                    f"销量为负：{key} = {value} 分（销量类必须非负）",
                )
            )
    return tuple(out)


def _check_missing_metadata_table(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
) -> tuple[Finding, ...]:
    """**N17 元数据面**（三个码；design §5.1 N17）。

    - ``MISSING_METADATA_TABLE``（ERROR）：``SOURCE_CSV`` 缺 ``table_name == "__metadata__"``
      的 JSON 件（DATA.md「导入通道」表 ``SOURCE_CSV`` 行原文「必需一个 table_name 为
      ``__metadata__`` 的 JSON 文件」）。**格式无关的判法**：解析结果里既没有
      ``__metadata__`` 表、``RawSource.metadata`` 又为空 ⇒ 元数据面彻底缺席。
      JSON 两入口的 ``metadata`` 是文件内嵌的、非空 ⇒ 不会假报。
    - ``NOT_SYNTHETIC``（ERROR）：``synthetic`` 非 ``true``（DATA.md「synthetic 必须 true，
      保留原编号和元数据」；实测 ``bank-a.json.synthetic is True``）。只在元数据里
      **确实带了** ``synthetic`` 键时才判 —— 该键属 legacy 入口，SOURCE_JSON／CSV 没有它。
    - ``MISSING_SEMANTIC_KEY``（**WARNING，不阻断**）：``coverage[*]`` 缺 ``semantic_key``
      （design §4.6：本卡对语义键「只归一只校验存在性」；实测
      ``csv-mini/metadata.json.coverage[*].semantic_key == "REMOTE-1"``）。
      指针段的数组下标是 **0-based**（design §4.4 显式声明的不对称）。

    前两者的同步 HTTP 面是 422 ``EVIDENCE_REQUIRED``（``createImport``／``attachImportFile``），
    由解析段的前置断言抛出；本条负责把它们同时留在**结构化 issues** 面里。
    """
    out: list[Finding] = []
    if not metadata and METADATA_TABLE_NAME not in source.tables:
        out.append(
            _finding(
                "MISSING_METADATA_TABLE",
                make_location(table_name=METADATA_TABLE_NAME),
                f"缺少 table_name 为 {METADATA_TABLE_NAME} 的元数据件，且解析结果里没有任何元数据",
            )
        )
    if "synthetic" in metadata and metadata["synthetic"] is not True:
        out.append(
            _finding(
                "NOT_SYNTHETIC",
                make_location(table_name=METADATA_TABLE_NAME, pointer="/synthetic"),
                f"synthetic 必须为 true，实测 {metadata['synthetic']!r}",
            )
        )
    coverage = metadata.get("coverage")
    if isinstance(coverage, Sequence) and not isinstance(coverage, (str, bytes)):
        for index, item in enumerate(coverage):
            if isinstance(item, Mapping) and item.get("semantic_key"):
                continue
            out.append(
                _finding(
                    "MISSING_SEMANTIC_KEY",
                    make_location(
                        table_name=METADATA_TABLE_NAME,
                        pointer=f"/coverage/{index}/semantic_key",
                    ),
                    f"coverage[{index}] 缺 semantic_key（可比性判据缺证据，不阻断）",
                    severity="WARNING",
                )
            )
    return tuple(out)


def _check_too_many_slices(
    slices: tuple[NormalizedSlice, ...],
    *,
    mapping: MappingSpec,
    metadata: Mapping[str, Any],
    source: RawSource,
    limits: IngestLimits,
    entity_cells: _EntityCells,
    findings: Sequence[Finding],
) -> tuple[Finding, ...]:
    """**N18 规模上限**（ERROR；三个码 ``TOO_MANY_SLICES`` / ``TOO_MANY_STAGE_ITEMS`` /
    ``TOO_MANY_ISSUES``），``location`` 一律用**文件级**形状 ``<table>#``。

    三条判据逐字按 design §5.1 N18：``len(slices) > limits.max_slices``、
    长表阶段项 ``> limits.max_stage_items``、``len(findings) > limits.max_findings``。
    阶段项数＝ ``mapping.counts_table`` 的**源行数**（§9.2 实测口径：B 为 4590 ＝ 510 × 9，
    A 为 510 —— §9.2 明确警告「把非空计数单元数当阶段项数」与「把 A 也算成 4590」两种错法）。
    上限值本身来自 ``model.py::DEFAULT_LIMITS``（10_000／90_000／1000；
    design §4.1 ＋ §14.2 A283：前两者是设计取值、1000 是契约字面量），
    **禁在本文件新增阈值**（D16）。

    必须**最后**跑：``TOO_MANY_ISSUES`` 的判据是「已积累的负例数」。
    本函数只**报**超限、不截断 ``findings`` —— 截断是持久化面的策略（活契约
    ``Import.issues.maxItems == 1000``），领域层如实报数，禁在这里悄悄丢证据。
    """
    out: list[Finding] = []
    if len(slices) > limits.max_slices:
        out.append(
            _finding(
                "TOO_MANY_SLICES",
                make_location(table_name=mapping.entity_table),
                f"切片数 {len(slices)} 超过上限 {limits.max_slices}",
            )
        )
    counts_name = mapping.counts_table
    counts_table = None if counts_name is None else source.tables.get(counts_name)
    stage_items = 0 if counts_table is None else len(counts_table.rows)
    if counts_table is not None and stage_items > limits.max_stage_items:
        out.append(
            _finding(
                "TOO_MANY_STAGE_ITEMS",
                make_location(table_name=counts_table.name),
                f"阶段项数 {stage_items} 超过上限 {limits.max_stage_items}",
            )
        )
    if len(findings) > limits.max_findings:
        out.append(
            _finding(
                "TOO_MANY_ISSUES",
                make_location(table_name=mapping.entity_table),
                f"负例数 {len(findings)} 超过上限 {limits.max_findings}",
            )
        )
    return tuple(out)


# ----------------------------------------------------------------------------- 私有共用件


def _finding(code: str, location: str, message: str, severity: str = "ERROR") -> Finding:
    """唯一的 ``Finding`` 构造点：**运行期**校验 ``code`` 与 ``severity`` 的成员资格。

    - ``code`` 必须在 ``INGEST_ISSUE_CODES`` 内 ⇒ D-019「禁发明 code」在运行期就有牙，
      写错一个字母当场炸，不会静默流到契约校验才发现；
    - ``severity`` 必须在 ``model.py::INGEST_SEVERITIES`` 内（design §4.1 冻结口径：
      类型是 ``str`` ＋ 运行期成员校验，**禁**在 domain 里另立第二个 ``Literal``）；
    - ``message`` 按活契约 ``maxLength`` 截断（``location`` 的截断在 ``make_location`` 里，
      只截表名段）。
    """
    if code not in INGEST_ISSUE_CODES:
        raise ValueError(f"未登记的 Issue.code：{code!r}（D-019：禁发明 code）")
    if severity not in INGEST_SEVERITIES:
        raise ValueError(f"severity 必须取自 INGEST_SEVERITIES：{severity!r}")
    return Finding(
        code=code, location=location, message=message[:_MESSAGE_MAX_LENGTH], severity=severity
    )


def _field_location(table_name: str, row_number: int, section: str, canonical_key: str) -> str:
    """design §4.4 的**行内字段**形状：``<table>#r<1-based 行号>/<section>/<canonical_key>``。

    列一律用**规范键**而不是源列名（design §4.4 的理由：A 的源列名是中文 ``可经营``、
    B 的是码 ``M01``，只有规范键 ``eligible`` 能跨入口稳定 ⇒ AC-006 要求 CSV 与
    SOURCE_JSON 给出**同一个** ``location``）；源列名如需出现，一律进 ``message``。
    """
    return make_location(
        table_name=table_name,
        row_number=row_number,
        section=section,
        canonical_key=canonical_key,
    )


def _entity_cells(
    source: RawSource, *, mapping: MappingSpec
) -> dict[int, dict[tuple[str, str], object]]:
    """实体表的**原样**单元格索引：1-based 行号 → ``{(段名, 规范键): 源值}``。

    校验段需要源文本而不是归一值的三个地方（N13／N14 的日历判定、N15 的「源值存在但
    归一失败」、N2 的 ``NOT_AN_INTEGER``）都从这里取，避免把 ``normalize`` 的类型转换
    在本文件里重写第二遍（那正是卡片红线要防的口径分叉）。

    只收「映射声明了、且该源列名**确实**在实体表 ``columns`` 里」的键 ⇒
    「映射引用不存在列」是 N8 的职责，本函数不越权报，也不造 ``KeyError``。
    长表布局下 ``count_fields`` 的值是指标码而不是列名（B 实测 ``M01…M09``），
    自然落不进索引 ⇒ N2 的 ``NOT_AN_INTEGER`` 只在按列名寻址的通道（CSV／宽表）上判，
    与 design §4.5「**CSV 通道下** ``_coerce_cell`` 用 ``int(text)``」的口径一致。
    """
    table = source.tables.get(mapping.entity_table)
    if table is None:
        return {}
    indexes: dict[str, int] = {name: index for index, name in enumerate(table.columns)}
    wanted: list[tuple[str, str, int]] = []
    for section, pairs in (
        (_SECTION_DIMENSIONS, mapping.dimensions),
        (_SECTION_COUNT_FIELDS, mapping.count_fields),
        (_SECTION_MONEY_FIELDS, mapping.money_fields),
    ):
        for key, column in pairs.items():
            index = indexes.get(column)
            if index is not None:
                wanted.append((section, key, index))
    out: dict[int, dict[tuple[str, str], object]] = {}
    for row_number, row in enumerate(table.rows, start=1):
        cells: dict[tuple[str, str], object] = {}
        for section, key, index in wanted:
            cells[(section, key)] = row[index] if index < len(row) else None
        out[row_number] = cells
    return out


def _entity_id_rows(entity_cells: _EntityCells) -> dict[str, int]:
    """切片号 → **实体表**的 1-based 行号（首次出现者胜出）。

    长表布局下 ``NormalizedSlice.source_row`` 指向 ``counts_table`` 的 M01 行
    （design §4.4 的长表定位口径），而 N7／N15 的 ``location`` 要求实体表行号 ⇒
    必须换算。宽表布局下两者本就同表同行，换算恒等。
    """
    out: dict[str, int] = {}
    for row_number, cells in entity_cells.items():
        raw = cells.get((_SECTION_DIMENSIONS, "id"))
        if raw is None:
            continue
        out.setdefault(str(raw), row_number)
    return out


def _is_present(raw: object) -> bool:
    """源单元格是否**确实带了值**。

    ``None`` 与空白串都算「源缺值」（DATA.md「缺值以 null 表达并带证据」）。
    """
    if raw is None:
        return False
    return bool(str(raw).strip())


def _is_unparseable_int(raw: object) -> bool:
    """源单元格带了值、却转不成 ``int`` ⇒ N2 的 ``NOT_AN_INTEGER`` 判据。

    ``int`` 与 ``bool`` 之外的一切非文本类型都算不合格（design §4.5：计数**禁** ``bool``
    冒充整数）；``bool`` 本身算合格整数还是不合格？—— 归一段 ``_coerce_cell`` 已把 ``bool``
    拒成 ``None``，故这里把 ``bool`` 判为**不合格**，与归一段同口径。
    """
    if raw is None:
        return False
    if isinstance(raw, bool):
        return True
    if isinstance(raw, int):
        return False
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return False
        try:
            int(text)
        except ValueError:
            return True
        return False
    return True


def _is_period(text: str) -> bool:
    """``YYYY-MM`` 且是合法日历月（design §5.1 N13；DATA.md「月份和日期用解析器校验日历」）。"""
    return _PERIOD_RE.fullmatch(text) is not None


def _is_cutoff(text: str) -> bool:
    """``YYYY-MM-DD`` 且是合法日历日。

    先正则卡形状、再 ``date.fromisoformat`` 判日历：3.11+ 的 ``fromisoformat`` 也接受
    ``20250930`` 这类基本格式，只用它会漏判（DATA.md 要求的是 ``YYYY-MM-DD``）。
    """
    if _CUTOFF_RE.fullmatch(text) is None:
        return False
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _dictionary_ids(metadata: Mapping[str, Any], key: str) -> frozenset[str]:
    """取 ``metadata`` 里某个字典的**合法 ID 集合**；字典缺失或形态不认识 ⇒ 空集（＝不判）。

    两种实测形态都要认：``metadata.branches``／``metadata.strategies`` 是
    ``list[{id, name, ...}]``（各 5 项／3 项），``metadata.channels`` 是 6 键 ``dict``。
    """
    value = metadata.get(key)
    if isinstance(value, Mapping):
        return frozenset(name for name in value if isinstance(name, str))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        ids: set[str] = set()
        for item in value:
            if isinstance(item, Mapping):
                candidate = item.get("id")
                if isinstance(candidate, str):
                    ids.add(candidate)
        return frozenset(ids)
    return frozenset()


def _strategy_origins(metadata: Mapping[str, Any]) -> dict[str, str]:
    """``metadata.strategies`` → ``{策略号: 登记的 origin}``（N12 的判据；实测为 list 形态）。"""
    value = metadata.get("strategies")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return {}
    out: dict[str, str] = {}
    for item in value:
        if not isinstance(item, Mapping):
            continue
        strategy = item.get("id")
        origin = item.get("origin")
        if isinstance(strategy, str) and isinstance(origin, str):
            out[strategy] = origin
    return out
