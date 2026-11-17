"""导入状态机（M1-01 · S2；design §3 / §3.2 / §3.4）。

本文件是 design §3.2 迁移表 I1–I7 的**唯一代码化副本**：``ImportTransition`` 的 8 个字段名
逐字对齐实测 ``worker/states.py::Transition``（``id / sources / target / trigger / spec_ref /
guard / transaction / creates_new_row``），体例对齐 ``domain/activity/states.py``，但**不 import**
worker 层（本卡 scope_deny）、也不 import api 层（domain 三禁之一）。

I8–I10 属 **M1-02** 写权，本卡**禁注册**（design §3.3）⇒ ``PUBLISHED`` 结构上不可达，
但 ``is_import_terminal("PUBLISHED")`` 已为 ``True``。

三条红线（照 ``worker/states.py``）：

1. **表外迁移根本不存在**：``assert_import_transition_allowed`` 一律抛 409 ``StateConflict``，
   ``detail`` 取 design §3.4 的逐条冻结原文；``Issue.code`` / ``Issue.location`` 由 api/service
   层按 ``INGEST_STATE_ISSUE_CODES`` 附加（domain 层不给 issues）。
2. ``guard`` 是谓词的可读镜像（领域层禁 SQL 执行），运行期只信 ``rowcount``（A232）。
3. 本文件不含 SQL 执行、不开事务、不取系统时间。

``trigger`` 口径（冻结，与 ``domain/activity/states.py`` 同）：调用方传 **operationId**
（``createImport`` / ``attachImportFile`` / ``configureImport`` / ``validateImport``）或作业 kind
（``VALIDATE_IMPORT``，I5/I6/I7 共用，三者只以 ``target`` 相区分）。design §3.2 的 ``trigger`` 列
是该 token 后附中文说明的**散文**，本文件只存 token 本身（见回执 U-1）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, get_args

from campaignlab.domain.errors import StateConflict

__all__ = [
    "IMPORT_FORMATS",
    "IMPORT_STATES",
    "IMPORT_TERMINAL_STATES",
    "IMPORT_TRANSITIONS",
    "INGEST_STATE_ISSUE_CODES",
    "ImportFormat",
    "ImportState",
    "ImportTransition",
    "ImportTransitionId",
    "assert_import_transition_allowed",
    "is_import_terminal",
]

ImportState = Literal[
    "RECEIVED",
    "CONFIGURED",
    "VALIDATING",
    "VALID",
    "INVALID",
    "PUBLISHING",
    "PUBLISHED",
]
ImportFormat = Literal["LEGACY_SYNTHETIC_JSON", "SOURCE_JSON", "SOURCE_CSV"]

IMPORT_STATES: Final[tuple[str, ...]] = tuple(get_args(ImportState))
IMPORT_FORMATS: Final[tuple[str, ...]] = tuple(get_args(ImportFormat))
IMPORT_TERMINAL_STATES: Final[frozenset[str]] = frozenset({"PUBLISHED"})

ImportTransitionId = Literal["I1", "I2", "I3", "I4", "I5", "I6", "I7"]

INGEST_STATE_ISSUE_CODES: Final[tuple[str, ...]] = (
    "IMPORT_BUSY",
    "IMPORT_PUBLISHED",
    "IMPORT_NOT_CONFIGURED",
    "IMPORT_NOT_VALIDATING",
)

_JOB_TRIGGER: Final = "VALIDATE_IMPORT"
_CONFIGURABLE_SOURCES: Final[tuple[str, ...]] = ("RECEIVED", "CONFIGURED", "VALID", "INVALID")
_BUSY_SOURCES: Final[frozenset[str]] = frozenset({"VALIDATING", "PUBLISHING"})

_BUSY_DETAIL: Final = "导入正在处理中，文件与映射只读"
_PUBLISHED_DETAIL: Final = "导入已发布，记录只读"
_NOT_CONFIGURED_DETAIL: Final = "导入尚未配置映射，无法校验"
_NOT_VALIDATING_DETAIL: Final = "导入不在校验中，作业结果已失效"


@dataclass(frozen=True, slots=True)
class ImportTransition:
    """design §3.2 迁移表的一行（8 字段名逐字对齐 worker/states.py::Transition）。"""

    id: ImportTransitionId
    sources: tuple[str, ...]
    target: str
    trigger: str
    spec_ref: str
    guard: str
    transaction: str
    creates_new_row: bool


IMPORT_TRANSITIONS: Final[tuple[ImportTransition, ...]] = (
    ImportTransition(
        id="I1",
        sources=(),
        target="RECEIVED",
        trigger="createImport",
        spec_ref=(
            "architecture/DATA.md:11「支持状态流 RECEIVED → CONFIGURED → VALIDATING → "
            "VALID 或 INVALID → PUBLISHING → PUBLISHED」"
        ),
        guard=(
            "INSERT INTO imports(…) VALUES(… state='RECEIVED', revision=1, "
            "issue_json='[]', validation_digest=NULL …)"
        ),
        transaction="TX-I1 ImportService.create_import",
        creates_new_row=True,
    ),
    ImportTransition(
        id="I2",
        sources=_CONFIGURABLE_SOURCES,
        target="CONFIGURED",
        trigger="attachImportFile",
        spec_ref=(
            "architecture/DATA.md:11 同句 ＋ 同段「VALIDATING、PUBLISHING 期间文件与映射只读」"
        ),
        guard=(
            "UPDATE imports SET state='CONFIGURED', validation_digest=NULL, issue_json='[]', "
            "revision=revision+1 WHERE workspace_id=:workspace_id AND id=:id AND state IN "
            "('RECEIVED','CONFIGURED','VALID','INVALID') AND revision=:revision"
        ),
        transaction="TX-I2 ImportService.attach_file",
        creates_new_row=False,
    ),
    ImportTransition(
        id="I3",
        sources=_CONFIGURABLE_SOURCES,
        target="CONFIGURED",
        trigger="configureImport",
        spec_ref=(
            "architecture/DATA.md「更正和发布边界」段「每次映射实际变更保存为新映射 ID，"
            "老快照仍引用原版」＋ architecture/DOMAIN.md「对象与修改」"
            "表「配置内容同 ID 变更要求新 ID」"
        ),
        guard=(
            "UPDATE imports SET mapping_id=:mapping_id, state='CONFIGURED', "
            "validation_digest=NULL, issue_json='[]', revision=revision+1 WHERE "
            "workspace_id=:workspace_id AND id=:id AND state IN "
            "('RECEIVED','CONFIGURED','VALID','INVALID') AND revision=:revision"
        ),
        transaction=(
            "TX-I3 ImportService.configure_mapping（同一短事务内先 INSERT source_mappings，"
            "再 UPDATE imports）"
        ),
        creates_new_row=False,
    ),
    ImportTransition(
        id="I4",
        sources=("CONFIGURED", "VALID", "INVALID"),
        target="VALIDATING",
        trigger="validateImport",
        spec_ref=(
            "architecture/DATA.md:11 ＋ architecture/API.md「作业」行「202 返回 Job 和 Location」"
        ),
        guard=(
            "UPDATE imports SET state='VALIDATING', job_id=:job_id, revision=revision+1 WHERE "
            "workspace_id=:workspace_id AND id=:id AND state IN ('CONFIGURED','VALID','INVALID') "
            "AND revision=:revision"
        ),
        transaction=(
            "TX-I4 ImportService.accept_validation（复用 M0-04 的 "
            "worker/store.py::JobStore.enqueue，"
            "禁重写队列）"
        ),
        creates_new_row=False,
    ),
    ImportTransition(
        id="I5",
        sources=("VALIDATING",),
        target="VALID",
        trigger=_JOB_TRIGGER,
        spec_ref="architecture/DATA.md:11「校验的业务问题记入 INVALID 与结构化 issues」的反面",
        guard=(
            "UPDATE imports SET state='VALID', validation_digest=:validation_digest, "
            "issue_json=:issue_json, revision=revision+1 WHERE workspace_id=:workspace_id AND "
            "id=:id AND state='VALIDATING' AND revision=:revision"
        ),
        transaction="TX-I5 ImportService.finish_validation（由作业处理器调用，见 §11.8）",
        creates_new_row=False,
    ),
    ImportTransition(
        id="I6",
        sources=("VALIDATING",),
        target="INVALID",
        trigger=_JOB_TRIGGER,
        spec_ref="architecture/DATA.md:11 原文「校验的业务问题记入 INVALID 与结构化 issues」",
        guard=(
            "UPDATE imports SET state='INVALID', validation_digest=:validation_digest, "
            "issue_json=:issue_json, revision=revision+1 WHERE workspace_id=:workspace_id AND "
            "id=:id AND state='VALIDATING' AND revision=:revision"
        ),
        transaction="TX-I5（同一方法，仅 target 与 issue 面不同）",
        creates_new_row=False,
    ),
    ImportTransition(
        id="I7",
        sources=("VALIDATING",),
        target="CONFIGURED",
        trigger=_JOB_TRIGGER,
        spec_ref="architecture/DATA.md:11 原文「技术失败回到可重试的稳定状态，关联 FAILED 作业」",
        guard=(
            "UPDATE imports SET state='CONFIGURED', validation_digest=NULL, issue_json='[]', "
            "job_id=:job_id, revision=revision+1 WHERE workspace_id=:workspace_id AND id=:id AND "
            "state='VALIDATING' AND revision=:revision"
        ),
        transaction="TX-I7 ImportService.fail_validation",
        creates_new_row=False,
    ),
)


def is_import_terminal(state: str) -> bool:
    """``PUBLISHED`` 是唯一的终态（体例＝domain/activity/states.py::is_activity_terminal）。"""
    return state in IMPORT_TERMINAL_STATES


def assert_import_transition_allowed(source: str | None, target: str, *, trigger: str) -> None:
    """表内迁移放行；表外迁移按 design §3.4 的逐条冻结映射抛 409 ``StateConflict``。"""
    if target not in IMPORT_STATES:
        raise StateConflict(f"未知的目标状态：{target!r}")
    if source is not None and source not in IMPORT_STATES:
        raise StateConflict(f"未知的导入状态：{source!r}")
    for row in IMPORT_TRANSITIONS:
        if row.target != target or row.trigger != trigger:
            continue
        if source is None:
            if row.creates_new_row:
                return
            continue
        if source in row.sources:
            return
    if source == "PUBLISHED":
        raise StateConflict(_PUBLISHED_DETAIL)
    if trigger == _JOB_TRIGGER:
        raise StateConflict(_NOT_VALIDATING_DETAIL)
    if source in _BUSY_SOURCES:
        raise StateConflict(_BUSY_DETAIL)
    if source == "RECEIVED" and trigger == "validateImport":
        raise StateConflict(_NOT_CONFIGURED_DETAIL)
    raise StateConflict(_BUSY_DETAIL)
