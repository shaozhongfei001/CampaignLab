"""作业制品索引复核（M0-04/S2b-2；design §5:52 · AC-031 的**写入侧前提**）。

AC-031 原文「数据库和制品摘要一致。历史报告和原规则仍能回查。快照缺件可定位并阻止错误
切换」的判定归 M5-01（design §7 的 cross_ref）；本模块只交付判定所依赖的那把尺子：

- ``verify_artifact_index(conn, data_dir)`` 返回 ``[]`` ⇒ 数据库与制品摘要一致；
  返回非空 ⇒ 每一项都是**可独立定位**的差异（工作区、制品 id、相对路径、期望摘要、
  实测摘要），据此即可「阻止错误切换」。禁只回一个布尔值——那样失败时无法归因
  （与 ``infra/db/ddl_compare.py::compare_schema`` 同一取向）。
- ``manifest_rows(conn)`` 给 ``backup_manifest.json`` 提供 SHA 清单数据来源
  （OPERATIONS.md:20「复制被引用制品和摘要清单，同一批次写 backup_manifest.json」）。

**reason 清单**（design §5:52 的五项判据 ＋ 两条安全兜底；④⑤ 由 S2b-3 依 A204/A205 补齐）：

- ``MISSING_FILE`` —— ① 存在性：``relative_path`` 在 ``<data_dir>`` 内不存在
- ``SHA256_MISMATCH`` —— ② sha256：实测摘要 != ``artifacts.sha256``
- ``BYTE_SIZE_MISMATCH`` —— ③ byte_size：摘要对得上但字节数 != ``artifacts.byte_size``
- ``RESULT_JSON_UNPARSEABLE`` —— ④：``jobs.result_json`` 解不开或形状不合规
- ``RESULT_REF_DANGLING`` —— ⑤：ref 指向的 ``jobs`` 行在同工作区内不存在
- ``PATH_ESCAPE`` / ``UNREADABLE`` —— 两条安全兜底（A151）：路径逃出受控目录／读不出来

**禁新增第八个 reason**（A205）：④ 的「JSON 语法错」「不是对象」「不合 ``ObjectRef`` 形状
或 ``kind`` 非 ``job``」三个子形态**共用** ``RESULT_JSON_UNPARSEABLE``，由
``POINTER_*`` 五个位置指针区分。A205 原文要求「用 ``detail`` 区分」，而 design §5:52
冻结的 ``Discrepancy`` 8 字段里**没有** ``detail`` 槽位、A205 又同时要求 8 字段逐字不变，
故取语义最贴近的 ``relative_path``（＝「被核对象的位置」）承载指针；制品侧与 ``jobs`` 侧
由 ``reason`` 天然区分。该取舍已按 A159 报 U 项，未自行改字段面。

**同口径复核（A157）**：sha256 一律调 ``infra.artifacts.hash_file``，本模块**不含**
第二份分块读 + 摘要累加实现。提升 ``hash_file`` 为公共符号的唯一理由就是这里：复核方
若自己另写一遍，两份实现必然在 chunk 边界与空文件处置上漂移，而漂移的表现形式恰好是
「校验静默失配」这种最难查的形态 —— **口径分叉即等于校验失效**（design §11-A157）。

**本模块零 SQL 文本**（design §4 / A81）：``tests/unit/test_job_repository_terminal.py``
的 ``test_worker_package_contains_no_table_dml_literals`` 守护「``worker/**`` 里出现的
SQL 文本只有 ``BEGIN IMMEDIATE``／``COMMIT``／``ROLLBACK`` 三条」，只读查询也不例外。
故制品行与作业行的读取一律委托既有仓储面：``WorkspaceRepository.list_page`` 有界枚举
工作区 ＋ ``ArtifactRepository.list_for_workspace`` / ``JobRepository.list_for_workspace``
逐工作区取行，与 ``worker/store.py`` 委托 ``JobRepository`` 是同一分层口径。
后者是 S2b-3 依 **A204**（A82 的 append-only 豁免）给 ``JobRepository`` **纯追加**的只读
访问器（``infra/db/repositories.py``，22 add / 0 del），逐字对齐制品侧同方法的体例；
**禁** ``list_all`` 式全表无界枚举，枚举口径与制品侧完全一致。

时间口径：本模块**不取系统当前时间**（``tests/unit/test_clock.py`` 的全树静态守护），
也不做任何年龄判定 —— 超期临时件的回收归 ``infra.artifacts.sweep_unreferenced``。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pydantic import ValidationError
from sqlalchemy import Connection

from campaignlab.api.common import ObjectRef
from campaignlab.infra.artifacts import hash_file
from campaignlab.infra.db.repositories import (
    ArtifactRecord,
    ArtifactRepository,
    JobRecord,
    JobRepository,
    WorkspaceRepository,
)

__all__ = [
    "BYTE_SIZE_MISMATCH",
    "MISSING_FILE",
    "PATH_ESCAPE",
    "POINTER_RESULT_JSON",
    "POINTER_RESULT_JSON_OBJECT",
    "POINTER_RESULT_REF_ID",
    "POINTER_RESULT_REF_KIND",
    "POINTER_RESULT_REF_SHAPE",
    "RESULT_JSON_UNPARSEABLE",
    "RESULT_REF_DANGLING",
    "RESULT_REF_KIND",
    "SHA256_MISMATCH",
    "UNREADABLE",
    "Discrepancy",
    "ManifestRow",
    "manifest_rows",
    "verify_artifact_index",
]

#: design §5:52 点名的三种制品侧差异形态。
MISSING_FILE: Final = "MISSING_FILE"
SHA256_MISMATCH: Final = "SHA256_MISMATCH"
BYTE_SIZE_MISMATCH: Final = "BYTE_SIZE_MISMATCH"
#: design §5:52 点名的两种 ``jobs.result_json`` 侧差异形态（④⑤，S2b-3 依 A204/A205 落地）。
RESULT_JSON_UNPARSEABLE: Final = "RESULT_JSON_UNPARSEABLE"
RESULT_REF_DANGLING: Final = "RESULT_REF_DANGLING"
#: 两条安全兜底（design §9 的符号面是**下限而非上限**，A151）：复核器读到的路径必须
#: 落在 ``<data_dir>`` 内、且必须真能读出来，否则「一致」这个结论本身不可信。
PATH_ESCAPE: Final = "PATH_ESCAPE"
UNREADABLE: Final = "UNREADABLE"

#: A155① 冻结的 ``result_ref`` 形状：``ObjectRef(kind="job", id=<job_id>)``，id 指向**作业行**。
RESULT_REF_KIND: Final = "job"

#: A205 要求 ④ 的多个失败子形态共用 ``RESULT_JSON_UNPARSEABLE`` 并以 ``detail`` 区分。
#: design §5:52 冻结的 ``Discrepancy`` 8 字段里**没有** ``detail`` 槽位，A205 又同时要求
#: 8 字段逐字不变 ⇒ 用 ``relative_path`` 承载下面五个**位置指针**（语义＝「被核对象在哪」），
#: 见 ``_job_discrepancy`` 的槽位口径。指针是**稳定字面量**，禁随实现改写（下游按它归因）。
POINTER_RESULT_JSON: Final = "jobs.result_json"
POINTER_RESULT_JSON_OBJECT: Final = "jobs.result_json:object"
POINTER_RESULT_REF_SHAPE: Final = "jobs.result_ref:shape"
POINTER_RESULT_REF_KIND: Final = "jobs.result_ref.kind"
POINTER_RESULT_REF_ID: Final = "jobs.result_ref.id"

#: 枚举工作区的单页上限。取足够大的值一次取全，是为了**不依赖游标**：
#: ``list_page`` 的 ``after`` 游标是 ``(created_at, id)``，而 ``Workspace.created_at``
#: 已被映射成 ``datetime``，回填游标就要把 ``datetime`` 再 ``isoformat()`` 一次；
#: 一旦库里的 TEXT 与该往返值不逐字相同（例如 ``Z`` 与 ``+00:00`` 之别），翻页就会
#: **静默漏行** —— 对一个「用来证明没有缺件」的函数，静默漏行比抛错严重得多。
#: 故这里宁可一次取全，并在真的取满时**抛错拒绝出具结论**，也不静默少核。
_WORKSPACE_ENUM_LIMIT: Final = 1_000_000


@dataclass(frozen=True, slots=True)
class Discrepancy:
    """一条可定位的索引／制品差异（design §5:52 给出的五元组形状，前五个字段逐字对应）。

    ``actual_sha256`` 为 ``None`` 表示**根本没读到内容**（缺件、路径逃逸、读不出来），
    与「读到了但摘要不符」严格区分：前者要查文件系统与备份，后者要查写入侧或篡改。
    ``expected_byte_size`` / ``actual_byte_size`` 只在尺寸相关形态下填，其余为 ``None``。
    """

    workspace_id: str
    artifact_id: str
    relative_path: str
    expected_sha256: str
    actual_sha256: str | None
    reason: str
    expected_byte_size: int | None = None
    actual_byte_size: int | None = None


@dataclass(frozen=True, slots=True)
class ManifestRow:
    """``backup_manifest.json`` 的一行（OPERATIONS.md:20「复制被引用制品和摘要清单」）。

    字段面即 ``artifacts`` 行本身，**不重新计算**任何值：清单的语义是「数据库此刻声称
    这些制品的摘要是这些」，与 ``verify_artifact_index`` 实测出的值对照才有意义。
    两者同源同值 ⇒ 备份与索引一致；不一致 ⇒ 由 ``verify_artifact_index`` 报出。
    """

    workspace_id: str
    artifact_id: str
    kind: str
    sha256: str
    relative_path: str
    byte_size: int
    created_at: str


def _workspace_ids(conn: Connection) -> list[str]:
    """有界枚举全部工作区 id（**禁** ``list_all`` 式全表无界枚举，A204）。

    取全而不翻页的理由见 ``_WORKSPACE_ENUM_LIMIT`` 的注释：静默漏行对一个「用来证明没有
    缺件」的函数比抛错严重得多，故真的取满时**抛错拒绝出具结论**，也不静默少核。
    """
    workspaces = WorkspaceRepository().list_page(conn, limit=_WORKSPACE_ENUM_LIMIT)
    if len(workspaces) >= _WORKSPACE_ENUM_LIMIT:
        raise RuntimeError(
            f"工作区数达到单次枚举上限 {_WORKSPACE_ENUM_LIMIT}，无法确认已取全；"
            "拒绝在可能漏核的前提下出具「索引一致」结论（请改为分页游标实现并另行裁定）"
        )
    return [workspace.id for workspace in workspaces]


def _artifacts_of(conn: Connection, workspace_ids: list[str]) -> list[ArtifactRecord]:
    """逐工作区取 ``artifacts`` 行（与 ``_jobs_of`` 共用同一枚举口径，A204）。"""
    repository = ArtifactRepository()
    records: list[ArtifactRecord] = []
    for workspace_id in workspace_ids:
        records.extend(repository.list_for_workspace(conn, workspace_id))
    return records


def _jobs_of(conn: Connection, workspace_ids: list[str]) -> list[JobRecord]:
    """逐工作区取 ``jobs`` 行（④⑤ 判据的数据来源）。

    走 ``JobRepository.list_for_workspace`` —— S2b-3 依 A204（A82 的 append-only 豁免）
    **纯追加**到 ``infra/db/repositories.py`` 的只读访问器，逐字对齐制品侧同方法的体例、
    复用既有行→记录转换 ``_job_of``。本模块因此仍然**零 SQL 文本**：冻结守护
    ``test_worker_package_contains_no_table_dml_literals`` 连只读查询也判红，故这里连
    一条 ``SELECT`` 都不许出现（把 SQL 藏进 docstring 再拼接取出属静默损坏，同样禁）。
    """
    repository = JobRepository()
    records: list[JobRecord] = []
    for workspace_id in workspace_ids:
        records.extend(repository.list_for_workspace(conn, workspace_id))
    return records


def _artifact_records(conn: Connection) -> list[ArtifactRecord]:
    """全表 ``artifacts`` 行，委托既有仓储面（本模块零 SQL 文本，见模块 docstring）。"""
    return _artifacts_of(conn, _workspace_ids(conn))


def _resolve_within(root: Path, resolved_root: Path, relative_path: str) -> Path | None:
    """把 ``artifacts.relative_path`` 解析成 ``<data_dir>`` 内的绝对路径；不受控即 ``None``。

    DDL 只保证 ``relative_path`` 非空且全表 UNIQUE，**不保证**它是内容寻址形状，更不保证
    它不含 ``..``、不是绝对路径。故按 ``infra/artifacts.py`` 的同一取向做两道守卫
    （OPERATIONS.md:11「制品路径使用受控目录和 ID 解析」）：

    1. **形状守卫**：空串、以 ``/`` 开头（绝对路径）、含 ``\\``（Windows 分隔符）一律拒。
       绝对路径必须在这里显式拒掉 —— ``Path.joinpath(*"/etc/passwd".split("/"))`` 的首段是
       空串，会被静默重解释成 ``<data_dir>/etc/passwd``，于是「库里的绝对路径」被换成了
       另一个根本不存在的受控路径，报出来的就是 ``MISSING_FILE`` 而非真实成因。
       ``\\`` 与 ``relative_path_for`` 的 ``_safe_token`` 同口径（写入侧本来就禁两种分隔符）。
    2. **受控目录守卫**：``resolve()`` 后必须仍在 ``<data_dir>`` 内，拦 ``..`` 与符号链接逃逸。
    """
    if not relative_path or relative_path.startswith("/") or "\\" in relative_path:
        return None
    candidate = root.joinpath(*relative_path.split("/")).resolve()
    if not candidate.is_relative_to(resolved_root):
        return None
    return candidate


def _discrepancy(
    record: ArtifactRecord,
    reason: str,
    *,
    actual_sha256: str | None = None,
    expected_byte_size: int | None = None,
    actual_byte_size: int | None = None,
) -> Discrepancy:
    """按 design §5:52 的五元组形状组装一条差异（``expected_*`` 一律取数据库声称值）。"""
    return Discrepancy(
        workspace_id=record.workspace_id,
        artifact_id=record.id,
        relative_path=record.relative_path,
        expected_sha256=record.sha256,
        actual_sha256=actual_sha256,
        reason=reason,
        expected_byte_size=expected_byte_size,
        actual_byte_size=actual_byte_size,
    )


def _check_record(record: ArtifactRecord, *, root: Path, resolved_root: Path) -> list[Discrepancy]:
    """核一行 ``artifacts``：存在性 → sha256 → byte_size（design §5:52 的三项判据）。

    摘要与尺寸**不同时报**：内容被换掉时两者必然一起变，只报 ``SHA256_MISMATCH``
    一条即可定位；``BYTE_SIZE_MISMATCH`` 因此专门留给「摘要对得上、尺寸对不上」这种
    只有索引行被写坏才会出现的形态，两条判据互不掩盖。
    """
    target = _resolve_within(root, resolved_root, record.relative_path)
    if target is None:
        return [_discrepancy(record, PATH_ESCAPE)]
    if not target.is_file():
        return [_discrepancy(record, MISSING_FILE)]
    try:
        actual_sha256, actual_byte_size = hash_file(target)
    except OSError:
        return [_discrepancy(record, UNREADABLE)]
    if actual_sha256 != record.sha256:
        return [
            _discrepancy(
                record,
                SHA256_MISMATCH,
                actual_sha256=actual_sha256,
                expected_byte_size=record.byte_size,
                actual_byte_size=actual_byte_size,
            )
        ]
    if actual_byte_size != record.byte_size:
        return [
            _discrepancy(
                record,
                BYTE_SIZE_MISMATCH,
                actual_sha256=actual_sha256,
                expected_byte_size=record.byte_size,
                actual_byte_size=actual_byte_size,
            )
        ]
    return []


def _job_discrepancy(record: JobRecord, reason: str, pointer: str) -> Discrepancy:
    """组装一条 ``jobs`` 侧差异（A205：8 字段与前 5 元组逐字不变，故按位复用槽位）。

    ``jobs`` 行没有制品，三个制品字段按语义就近承载，口径写死在这里以免下游各自猜测：

    - ``artifact_id`` ← **被核对象的主键**，即 ``jobs.id``。design §5:52 要求五元组能把
      差异定位到具体一行，``jobs`` 侧唯一定位键就是作业 id，故占这个槽位。
    - ``relative_path`` ← **被核字段的位置指针**（``POINTER_*`` 五个之一），即 A205 要求
      用来区分 ④ 各子形态的 ``detail``。
    - ``expected_sha256`` ← 空串：``jobs`` 侧不存在摘要期望值（不是「期望值为空摘要」，
      而是「本判据与摘要无关」）。``actual_sha256`` 恒为 ``None``：没做任何哈希，与制品侧
      「根本没读到内容」的 ``None`` 语义一致，两者由 ``reason`` 天然区分，不会混淆。
    - ``expected_byte_size`` / ``actual_byte_size`` ← 保持默认 ``None``（与尺寸无关）。
    """
    return Discrepancy(
        workspace_id=record.workspace_id,
        artifact_id=record.id,
        relative_path=pointer,
        expected_sha256="",
        actual_sha256=None,
        reason=reason,
    )


def _check_job(record: JobRecord, *, job_ids: frozenset[str]) -> list[Discrepancy]:
    """核一行 ``jobs``：④ ``result_json`` 可解析且形状合规 → ⑤ ref 指向的作业行存在。

    ``result_json`` 可空（DDL 的双条件 CHECK ``(state='SUCCEEDED')=(result_json IS NOT NULL)``），
    故**只核非 NULL 的行**（A205）。三段判据顺序不可换：解不开就谈不上形状，形状不合规
    就谈不上指向。④ 的三个失败子形态（JSON 语法错／不是对象／不合 ``ObjectRef`` 形状或
    ``kind`` 非 ``job``）**共用** ``RESULT_JSON_UNPARSEABLE``（A205：禁新增第三个 reason），
    由 ``POINTER_*`` 区分。

    形状判据**复用写入侧同一个模型** ``api.common.ObjectRef``（``extra="forbid"`` ＋ ``kind``
    的 Literal 枚举 ＋ ``id`` 的 ``RESOURCE_ID_PATTERN``），不自写第二份形状校验 —— 与 A157
    「同口径复核」同理：两份形状实现必然漂移，而漂移的表现形式恰好是「校验静默失配」。
    比 ``repositories.job_from_row`` 的构造式（``ObjectRef(kind=payload["kind"], ...)``）
    严一处：这里用 ``model_validate``，故 ``ObjectRef`` 里**多出的键**也会判红，构造式会静默忽略。

    ⑤ 的存在性判据只在**同工作区内**查（``jobs`` 的主键是 ``(workspace_id, id)``，跨工作区
    同号是两个不同对象）。A205 明确否决「核制品表」的候选：``ArtifactRecord`` 没有任何 job
    关联列、``relative_path_for(kind, workspace_id, sha256)`` 也不内嵌 job id ⇒ 制品侧与作业侧
    不存在逐作业的精确链接，那种判据只能退化成工作区级弱判据，对无制品的作业会**假红**。
    """
    if record.result_json is None:
        return []
    try:
        payload = json.loads(record.result_json)
    except ValueError:
        return [_job_discrepancy(record, RESULT_JSON_UNPARSEABLE, POINTER_RESULT_JSON)]
    if not isinstance(payload, Mapping):
        return [_job_discrepancy(record, RESULT_JSON_UNPARSEABLE, POINTER_RESULT_JSON_OBJECT)]
    try:
        ref = ObjectRef.model_validate(dict(payload))
    except ValidationError:
        return [_job_discrepancy(record, RESULT_JSON_UNPARSEABLE, POINTER_RESULT_REF_SHAPE)]
    if ref.kind != RESULT_REF_KIND:
        return [_job_discrepancy(record, RESULT_JSON_UNPARSEABLE, POINTER_RESULT_REF_KIND)]
    if ref.id not in job_ids:
        return [_job_discrepancy(record, RESULT_REF_DANGLING, POINTER_RESULT_REF_ID)]
    return []


def verify_artifact_index(conn: Connection, data_dir: Path) -> list[Discrepancy]:
    """逐行核 ``artifacts``／``jobs`` 与落盘制品是否一致；``[]`` 即「数据库和制品摘要一致」。

    design §5:52 的**五项判据全部落地**（④⑤ 由 S2b-3 依 A204/A205 补齐）：

    1. ① ``artifacts.relative_path`` 指向的文件**存在** ⇒ 否则 ``MISSING_FILE``；
    2. ② 实测 sha256 与 ``artifacts.sha256`` 相等 ⇒ 否则 ``SHA256_MISMATCH``；
    3. ③ 实测字节数与 ``artifacts.byte_size`` 相等 ⇒ 否则 ``BYTE_SIZE_MISMATCH``；
    4. ④ ``jobs.result_json`` 可解析**且**形状合规 ⇒ 否则 ``RESULT_JSON_UNPARSEABLE``；
    5. ⑤ 该 ref 指向的 ``jobs`` 行**在同工作区内存在** ⇒ 否则 ``RESULT_REF_DANGLING``。

    另加两条安全兜底（``PATH_ESCAPE`` / ``UNREADABLE``，A151）。返回项按
    ``(workspace_id, artifact_id, reason)`` 排序，故同一库状态必得同一份差异清单
    （禁依赖 SQL 的自然返回序 —— 那会随插入顺序漂移，复核结果就不可复现了）。

    ⑤ 的口径由 A205 钉死：A155① 已把 M0-04 的 ``result_ref`` 冻结为
    ``ObjectRef(kind="job", id=<job_id>)``，即 id 指向**作业行**而非制品行，故这里核
    ``jobs`` 行存在性，**不**核「制品表里有没有对应行」（否决理由见 ``_check_job``）。
    枚举口径见 ``_workspace_ids`` / ``_artifacts_of`` / ``_jobs_of``（A204：有界、逐工作区）。
    """
    root = Path(data_dir)
    if not root.is_absolute():
        raise ValueError(
            f"data_dir 必须是绝对路径（artifacts.relative_path 相对它解析）：{data_dir!r}"
        )
    resolved_root = root.resolve()
    workspace_ids = _workspace_ids(conn)
    found: list[Discrepancy] = []
    for record in _artifacts_of(conn, workspace_ids):
        found.extend(_check_record(record, root=root, resolved_root=resolved_root))
    jobs = _jobs_of(conn, workspace_ids)
    ids_by_workspace: dict[str, set[str]] = {}
    for job in jobs:
        ids_by_workspace.setdefault(job.workspace_id, set()).add(job.id)
    for job in jobs:
        ids = ids_by_workspace.get(job.workspace_id)
        found.extend(_check_job(job, job_ids=frozenset(() if ids is None else ids)))
    found.sort(key=lambda item: (item.workspace_id, item.artifact_id, item.reason))
    return found


def manifest_rows(conn: Connection) -> list[ManifestRow]:
    """全表 ``artifacts`` 的 SHA 清单行（``backup_manifest.json`` 的数据来源）。

    只读数据库、**不碰文件系统**：清单要记的是「索引声称什么」，实测复核是
    ``verify_artifact_index`` 的职责。备份时两者一起出，才能把「清单」与「实物」分开归因。
    输出按 ``(workspace_id, artifact_id)`` 排序，故同一库状态必得同一份清单字节
    （禁依赖 SQL 的自然返回序 —— 那会随插入顺序漂移，摘要清单就不可复现了）。
    """
    rows = [
        ManifestRow(
            workspace_id=record.workspace_id,
            artifact_id=record.id,
            kind=record.kind,
            sha256=record.sha256,
            relative_path=record.relative_path,
            byte_size=record.byte_size,
            created_at=record.created_at,
        )
        for record in _artifact_records(conn)
    ]
    rows.sort(key=lambda row: (row.workspace_id, row.artifact_id))
    return rows
