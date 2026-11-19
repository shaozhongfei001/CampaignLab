"""导入接入的**唯一入口**（M1-01 · S2；design §4.1；卡片 ``public_frozen`` 面）。

卡片 ``M1-01.md:24``：M1-P01（月报接入）**只能经此扩展、禁改签名** ⇒ 本文件两个函数的
签名逐字按 design §4.1，且裁定 **A302** 明确：``parse``／``ingest`` **不带 clock 形参**
——归一与校验是**纯函数**，时刻只在 application 层用于 ``created_at``；
``framework/PYTHON.md`` 第 6 行禁的是「在领域计算内调用系统当前时间」，不是要求注入时钟。
若 M1-P01 后续需要时点判定，走 §14 追记 ＋ CR，**不走本文件**。

``ingest()`` 内部严格三段（design §4.2）：解析段的产物 ``RawSource`` → ``normalize()`` →
``validate()``。四入口（宽表／长表／CSV／SOURCE_JSON）**共用这一条路径**，
禁第二套校验器（AC-005／AC-006 的实质）。

返回值不含任何 HTTP／DB 概念（design §4.1）。本文件禁 SQL、禁开事务、
禁 import ``campaignlab.api``／``campaignlab.infra``、禁持时钟。
"""

from __future__ import annotations

from typing import Any

from campaignlab.domain.ingest.digests import VALIDATION_DIGEST_KIND
from campaignlab.domain.ingest.model import (
    DEFAULT_LIMITS,
    IngestLimits,
    IngestResult,
    MappingSpec,
    RawSource,
    SliceCounts,
)
from campaignlab.domain.ingest.normalize import normalize
from campaignlab.domain.ingest.parse import PARSER_VERSION, parse
from campaignlab.domain.ingest.validate import validate

__all__ = ["ingest", "parse"]


def ingest(
    source: RawSource,
    *,
    mapping: MappingSpec,
    limits: IngestLimits = DEFAULT_LIMITS,
) -> IngestResult:
    """归一 ＋ 校验，一次跑完（design §4.1 的 ``public_frozen`` 签名，逐字）。

    ``limits`` 一律向下透传给 ``validate()``：design §4.1 让调用方能改上限，
    而 §5.1 N18 的三条判据正是拿 ``limits`` 比的 —— 不透传就等于 ``ingest(limits=...)``
    是个装饰（这是本棒对 §4.2 ``validate`` 签名做的唯一扩展，见该文件 docstring）。

    ``counts`` 四个数的口径逐字按 design §9.2（S7 以 ``SliceCounts`` 为黄金断言对象）：

    - ``slice_count`` ＝ 切片数（A／B 实测各 **510**）；
    - ``stage_item_count`` ＝ ``mapping.counts_table`` 的**源行数**（B 实测 **4590** ＝ 510 × 9；
      A 是宽表，其 ``counts_table`` 行数 ＝ 510 —— §9.2 明确警告禁把 A 也算成 4590，
      也禁把「非空计数单元数」当阶段项数）；
    - ``entity_row_count`` ＝ ``mapping.entity_table`` 的源行数；
    - ``count_cell_count`` ＝ 全部切片里**非空**计数单元数（``None`` 不计，
      DATA.md「缺值以 null 表达并带证据」）。

    ``projection`` 是 design §4.7 固定投影中**领域层能独立算出的那部分**：
    ``kind``／``parser_version``／``files``（按 ``(table_name, sha256)`` 升序）／``metadata`` 原样。
    另两个键 ``mapping_digest`` 与 ``metadata_digest`` 需要**注入的** ``canonicalize``
    （``api/common.py::canonical_json``）才能算，而 §4.1 冻结的本签名里没有它
    ⇒ 由 application 层调 ``digests.validation_projection(...)`` 补齐后再取
    ``validation_digest``。design 未定义 ``IngestResult.projection`` 的内容，
    已如实回报为升级项（禁在领域层自写第二份 JSON 序列化，那是 §4.7 明令禁的）。
    """
    slices = normalize(source, mapping=mapping)
    findings = validate(
        slices, mapping=mapping, metadata=source.metadata, source=source, limits=limits
    )
    counts_name = mapping.counts_table
    counts_table = None if counts_name is None else source.tables.get(counts_name)
    entity_table = source.tables.get(mapping.entity_table)
    counts = SliceCounts(
        slice_count=len(slices),
        stage_item_count=0 if counts_table is None else len(counts_table.rows),
        entity_row_count=0 if entity_table is None else len(entity_table.rows),
        count_cell_count=sum(
            1 for row in slices for value in row.counts.values() if value is not None
        ),
    )
    projection: dict[str, Any] = {
        "kind": VALIDATION_DIGEST_KIND,
        "parser_version": PARSER_VERSION,
        "files": [
            {"table_name": ref.table_name, "sha256": ref.sha256, "size_bytes": ref.size_bytes}
            for ref in sorted(source.file_refs, key=lambda ref: (ref.table_name, ref.sha256))
        ],
        "metadata": dict(source.metadata),
    }
    return IngestResult(slices=slices, findings=findings, counts=counts, projection=projection)
