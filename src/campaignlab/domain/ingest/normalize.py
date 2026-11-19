"""归一段：源列名 → 规范键，宽表逐行／长表透视（M1-01 · S2；design §4.2 ②／§4.3／§4.5）。

design §4.0 的三条**结构性保证**里，本文件承担前两条（S6 的 §10 V6 用 AST 守护）：

1. **不感知上传入口的格式维**：``normalize()`` 的形参面里根本没有它，本文件也不出现
   它的类型别名 —— 四入口（宽表／长表／CSV／SOURCE_JSON）在解析段之后形状已统一为
   ``RawSource``，归一段无从分叉。
2. **``layout`` 的分支在本文件内恰 1 处**，就在 ``normalize()`` 里；两条分支汇合到
   **同一个** ``NormalizedSlice`` 构造点（``_assemble_slice``，全文件唯一的构造调用）
   与同一套 ``validate()``。这是卡片红线「禁写第二套校验器」在归一面的落点。

金额纪律（design §4.5；卡片红线「禁用浮点算金额分」）：``_to_fen`` 只用 ``Decimal`` 与 ``int``，
**禁** ``float``、**禁** ``round(float(x) * 100)``（``0.29 * 100 == 28.999999999999996``，
浮点会静默丢分）。计数与 ``offset`` 一律 ``int``、**禁** ``bool`` 冒充整数
（``framework/PYTHON.md`` 第 3 行）。

本文件禁 SQL、禁事务、禁 import ``campaignlab.api``／``campaignlab.infra``、禁持时钟
（归一是纯函数，design §4.1；裁定 **A302**：本层零时钟依赖）。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import cast

from campaignlab.domain.ingest.model import (
    MappingSpec,
    NormalizedSlice,
    RawSource,
    SourceMoneyUnit,
    SourceRow,
)

__all__ = ["normalize"]


def normalize(source: RawSource, *, mapping: MappingSpec) -> tuple[NormalizedSlice, ...]:
    """把 ``RawSource`` 归一成规范切片行（design §4.2 ②）。

    **这是本文件里唯一一处布局分支**（design §4.0 保证 2）：长表走透视，宽表走逐行，
    两条分支最终都调用 ``_assemble_slice`` —— 同一个 ``NormalizedSlice`` 构造点，
    因此不存在「宽表一套规则、长表另一套规则」的可能。

    本函数**不抛**业务异常：源数据的一切脏值都归一成 ``None``／占位值原样带下去，
    由校验段（``validate.py`` 的 N1–N18）判成 ``Finding``。抛出去会把一条可定位的
    业务负例变成 500，那就丢掉了 AC-005 要求的「返回具体行列」。
    """
    if mapping.layout == "long":
        return _normalize_long(source, mapping=mapping)
    return _normalize_wide(source, mapping=mapping)


def _normalize_wide(source: RawSource, *, mapping: MappingSpec) -> tuple[NormalizedSlice, ...]:
    """宽表：``entity_table`` 的每一数据行 ⇒ 恰一个切片，``contributing_rows`` 恰 1 项。

    维度／计数／金额**全部**取自 ``entity_table``（design §5.1 N9 的 spec_ref 原文
    「wide 的阶段来自 entity_table」；实测 A 的 ``entity_table == counts_table == 月度宽表``，
    35 列 ＝ 14 维度 ＋ 9 计数 ＋ 12 金额）。
    """
    table = source.tables.get(mapping.entity_table)
    if table is None:
        return ()
    file_ids = {ref.table_name: ref.sha256 for ref in source.file_refs}
    file_id = file_ids.get(table.name, "")
    unit = mapping.source_money_unit
    slices: list[NormalizedSlice] = []
    for row_number, row in enumerate(table.rows, start=1):
        cells = dict(zip(table.columns, row, strict=False))
        dims = {
            key: _map_code(
                key,
                _coerce_cell(cells.get(column), key=key, role="dimension", unit=unit),
                mapping=mapping,
            )
            for key, column in mapping.dimensions.items()
        }
        counts = {
            key: cast(
                "int | None", _coerce_cell(cells.get(column), key=key, role="count", unit=unit)
            )
            for key, column in mapping.count_fields.items()
        }
        money_fen = {
            key: cast(
                "int | None", _coerce_cell(cells.get(column), key=key, role="money", unit=unit)
            )
            for key, column in mapping.money_fields.items()
        }
        source_row = SourceRow(source_file_id=file_id, table_name=table.name, row_number=row_number)
        slices.append(
            _assemble_slice(
                dims=dims,
                counts=counts,
                money_fen=money_fen,
                source_row=source_row,
                contributing_rows=(source_row,),
            )
        )
    return tuple(slices)


def _normalize_long(source: RawSource, *, mapping: MappingSpec) -> tuple[NormalizedSlice, ...]:
    """长表：``entity_table`` 逐行给维度与金额，``counts_table`` 按
    ``(切片键, 指标码)`` 透视给计数。

    定位口径（design §4.4，逐字）：``source_row`` 取 ``指标码 == mapping.count_fields["eligible"]``
    （B 实测即 ``M01``）的那一行；``contributing_rows`` 保留全部 9 行，
    **顺序 ＝ ``mapping.count_fields`` 的键序**（实测 ``eligible,sent,success,executed,
    contacted,effective,capacity,intentCount,activityCount`` ＝ ``M01…M09``）。

    透视时 ``(切片键, 指标码)`` 撞键**保留首次出现**的那一行：重复本身由校验段的
    N5 ``DUPLICATE_CODE`` 判红（design §5.1 N5 要求 ``message`` 里给出首次出现的行号），
    归一段不吞、也不静默取后者。
    """
    counts_name = mapping.counts_table
    entity = source.tables.get(mapping.entity_table)
    counts_table = None if counts_name is None else source.tables.get(counts_name)
    long_columns = mapping.long_columns
    if entity is None or counts_table is None or long_columns is None:
        return ()
    file_ids = {ref.table_name: ref.sha256 for ref in source.file_refs}
    entity_file_id = file_ids.get(entity.name, "")
    counts_file_id = file_ids.get(counts_table.name, "")
    unit = mapping.source_money_unit

    metric_codes = frozenset(mapping.count_fields.values())
    pivot: dict[str, dict[str, tuple[int, object]]] = {}
    for row_number, row in enumerate(counts_table.rows, start=1):
        cells = dict(zip(counts_table.columns, row, strict=False))
        slice_key = cells.get(long_columns.id)
        metric = cells.get(long_columns.metric)
        if not isinstance(slice_key, str) or not isinstance(metric, str):
            continue
        if metric not in metric_codes:
            continue
        stage_rows = pivot.setdefault(slice_key, {})
        stage_rows.setdefault(metric, (row_number, cells.get(long_columns.value)))

    slices: list[NormalizedSlice] = []
    for row_number, row in enumerate(entity.rows, start=1):
        cells = dict(zip(entity.columns, row, strict=False))
        dims = {
            key: _map_code(
                key,
                _coerce_cell(cells.get(column), key=key, role="dimension", unit=unit),
                mapping=mapping,
            )
            for key, column in mapping.dimensions.items()
        }
        money_fen = {
            key: cast(
                "int | None", _coerce_cell(cells.get(column), key=key, role="money", unit=unit)
            )
            for key, column in mapping.money_fields.items()
        }
        slice_id = str(dims.get("id", ""))
        stage_rows = pivot.get(slice_id, {})
        counts: dict[str, int | None] = {}
        contributing: list[SourceRow] = []
        for key, metric in mapping.count_fields.items():
            entry = stage_rows.get(metric)
            if entry is None:
                counts[key] = None
                continue
            counts[key] = cast(
                "int | None", _coerce_cell(entry[1], key=key, role="count", unit=unit)
            )
            contributing.append(
                SourceRow(
                    source_file_id=counts_file_id,
                    table_name=counts_table.name,
                    row_number=entry[0],
                )
            )
        contributing_rows = tuple(contributing)
        anchor = stage_rows.get(mapping.count_fields.get("eligible", ""))
        if anchor is not None:
            source_row = SourceRow(
                source_file_id=counts_file_id,
                table_name=counts_table.name,
                row_number=anchor[0],
            )
        elif contributing_rows:
            source_row = contributing_rows[0]
        else:
            # 该切片在长表里一条阶段项都没有（N7 MISSING_STAGE 会判红）：
            # 退回实体行做锚点，禁造 row_number=0（design §4.4：行号一律 1-based）。
            source_row = SourceRow(
                source_file_id=entity_file_id, table_name=entity.name, row_number=row_number
            )
        slices.append(
            _assemble_slice(
                dims=dims,
                counts=counts,
                money_fen=money_fen,
                source_row=source_row,
                contributing_rows=contributing_rows,
            )
        )
    return tuple(slices)


def _assemble_slice(
    *,
    dims: Mapping[str, object],
    counts: Mapping[str, int | None],
    money_fen: Mapping[str, int | None],
    source_row: SourceRow,
    contributing_rows: tuple[SourceRow, ...],
) -> NormalizedSlice:
    """design §4.0 保证 2 的**唯一** ``NormalizedSlice`` 构造点（宽／长两条分支汇合于此）。

    §11.1 给本文件点了 5 个私有函数；本函数是**必需的第 6 个**，因为 §4.0 保证 2 的原文
    要求「两条分支汇合到**同一个** ``NormalizedSlice`` 构造点」—— 把构造复制进两条分支
    正是该保证要禁的形态（依 A151：符号清单是下限而非上限）。

    字段序逐字按已落地的 ``model.py::NormalizedSlice``（design §4.3 的 14 维度 ＋ 9 计数
    ＋ 12 金额 ＋ 追溯）。``customer_key`` 取自 ``dims``：只有当映射自己声明了
    ``dimensions["customer_key"]`` 才非 ``None``（design §4.3：本卡三份实测数据的
    ``dedup_mode`` 均为 ``SYNTHETIC_INTERVAL``，无该源列 ⇒ 恒 ``None``）。
    """
    cutoff_value = dims.get("cutoff")
    offset_value = dims.get("offset")
    offset = 0
    if isinstance(offset_value, int) and not isinstance(offset_value, bool):
        offset = offset_value
    return NormalizedSlice(
        id=str(dims.get("id", "")),
        period=str(dims.get("period", "")),
        # 非法日历日在 _coerce_cell 里落 date.min，由校验段 N13 INVALID_CUTOFF 按源文本判红。
        cutoff=cutoff_value if isinstance(cutoff_value, date) else date.min,
        branch=cast("str | None", dims.get("branch")),
        subbranch=cast("str | None", dims.get("subbranch")),
        channel=cast("str | None", dims.get("channel")),
        strategy=cast("str | None", dims.get("strategy")),
        origin=cast("str | None", dims.get("origin")),
        segment=cast("str | None", dims.get("segment")),
        tag=cast("str | None", dims.get("tag")),
        definition=cast("str | None", dims.get("definition")),
        batch=cast("str | None", dims.get("batch")),
        cohort=cast("str | None", dims.get("cohort")),
        offset=offset,
        customer_key=cast("str | None", dims.get("customer_key")),
        counts=dict(counts),
        money_fen=dict(money_fen),
        source_row=source_row,
        contributing_rows=contributing_rows,
    )


def _coerce_cell(value: object, *, key: str, role: str, unit: SourceMoneyUnit) -> object:
    """按规范键的角色把**原样单元格**转成目标类型（design §4.2 ②／§4.5）。

    CSV 的类型转换发生在**映射层**（``framework/DATA.md``「文件与 DuckDB」第 2 条原文）
    ⇒ 本函数属②归一段、不属①解析段：``parse_source_csv`` 交出的 ``RawTable.rows`` 一律是
    原文字符串，由本函数按角色决定目标类型。这正是 §4.0 保证 3「CSV 与等价 SOURCE_JSON
    逐字段相等」能成立的唯一正确落点（实测 ``slices.csv`` 的 ``集合起点`` 列是文本 ``0``、
    ``source.json`` 里是 int ``0``）。

    - ``role="money"`` ⇒ 转交 ``_to_fen``（整数分）；
    - ``role="count"`` 或 ``key="offset"`` ⇒ ``int``（**禁** ``bool``；``int(text)`` 而非
      ``isdigit()``，否则 ``-1`` 会被判成「非数字」而错报 ``NOT_AN_INTEGER``，见 §9.1）；
    - ``key="cutoff"`` ⇒ ``date``；``key in {"id","period"}`` ⇒ ``str``（非空口径）；
    - 其余维度 ⇒ ``str | None``（空串归 ``None``，DATA.md「未适用字段可空」）。

    **一律不抛**：转不出来就落 ``None``／``date.min``／``0``，把判红的机会留给校验段。
    """
    if role == "money":
        return _to_fen(value, unit=unit)
    if role == "count" or key == "offset":
        fallback: int | None = None if role == "count" else 0
        if value is None or isinstance(value, bool):
            return fallback
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return fallback
            try:
                return int(text)
            except ValueError:
                return fallback
        return fallback
    if key == "cutoff":
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = "" if value is None else str(value).strip()
        try:
            return date.fromisoformat(text)
        except ValueError:
            return date.min
    if key in ("id", "period"):
        return "" if value is None else str(value)
    if value is None:
        return None
    return str(value) or None


def _to_fen(value: object, *, unit: SourceMoneyUnit) -> int | None:
    """元／分 → **整数分**（design §4.5；卡片红线「禁用浮点算金额分」）。

    冻结实现（逐字按 §4.5）：``Decimal(源文本或源整数)`` → ``scaled = value.scaleb(2)``
    （仅 ``CNY_YUAN``；``CNY_FEN`` 的源值本身已是分，不再缩放）→ 断言
    ``scaled == scaled.to_integral_value()``，成立则 ``int(scaled)``，不成立则返回 ``None``
    交校验段 N15 报 ``INVALID_MONEY``（``architecture/DATA.md`` 原文「甲行金额元乘 100，
    乙行分保持原整数。超出精度报 INVALID_MONEY」）。

    **禁** ``float``：``0.29 * 100 == 28.999999999999996`` 会静默丢分，故 ``float``／``bool``
    源值一律判不合格（``Decimal(float)`` 取的是二进制精确值，正是漂移的来源）。

    实测对撞（design §4.3）：A 的 ``AUM变动 == 182260``（元）与 B 的 ``amount_01_fen ==
    18226000``（分）归一后**同为 18226000**，逐字相等 ⇒ AC-006「元分归一后远程值一致」。

    本函数**不做**绝对值上下限判定（那是校验段 N15 的事，上下限真值来源是
    ``contracts/source-json.schema.json``），故同一个越限值在这里仍能算出整数分。
    """
    if value is None or isinstance(value, (bool, float)):
        return None
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            decimal_value = Decimal(text)
        except InvalidOperation:
            return None
    else:
        return None
    if decimal_value.is_nan() or decimal_value.is_infinite():
        return None
    scaled = decimal_value.scaleb(2) if unit == "CNY_YUAN" else decimal_value
    if scaled != scaled.to_integral_value():
        return None
    return int(scaled)


def _map_code(key: str, value: object, *, mapping: MappingSpec) -> str | None:
    """码值 → 标准值（design §4.3：``channel``／``origin`` 一律经 ``mapping.codes`` 映射）。

    实测：A 的源值 ``远程`` → ``remote``、``分行`` → ``branch``；B 的 ``C01`` → ``remote``、
    ``L`` → ``branch``。``mapping.codes`` 未声明该维度时原样返回（14 个维度里只有
    ``channel``／``origin`` 有码表）。

    **未知码值原样保留、不吞成 ``None``**：这样校验段 N10 ``UNKNOWN_CODE`` 才能在
    ``message`` 里给出**源值原文**（design §5.1 N10 的硬要求），而不是只说「有个值不合法」。
    """
    if value is None:
        return None
    text = value if isinstance(value, str) else str(value)
    codes = mapping.codes.get(key)
    if not codes:
        return text
    return codes.get(text, text)
