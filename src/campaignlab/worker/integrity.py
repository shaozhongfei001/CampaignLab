"""作业制品索引复核（M0-04/S2b-2；design §5:52 · AC-031 的**写入侧前提**）。

AC-031 原文「数据库和制品摘要一致。历史报告和原规则仍能回查。快照缺件可定位并阻止错误
切换」的判定归 M5-01（design §7 的 cross_ref）；本模块只交付判定所依赖的那把尺子：

- ``verify_artifact_index(conn, data_dir)`` 返回 ``[]`` ⇒ 数据库与制品摘要一致；
  返回非空 ⇒ 每一项都是**可独立定位**的差异（工作区、制品 id、相对路径、期望摘要、
  实测摘要），据此即可「阻止错误切换」。禁只回一个布尔值——那样失败时无法归因
  （与 ``infra/db/ddl_compare.py::compare_schema`` 同一取向）。
- ``manifest_rows(conn)`` 给 ``backup_manifest.json`` 提供 SHA 清单数据来源
  （OPERATIONS.md:20「复制被引用制品和摘要清单，同一批次写 backup_manifest.json」）。

**同口径复核（A157）**：sha256 一律调 ``infra.artifacts.hash_file``，本模块**不含**
第二份分块读 + 摘要累加实现。提升 ``hash_file`` 为公共符号的唯一理由就是这里：复核方
若自己另写一遍，两份实现必然在 chunk 边界与空文件处置上漂移，而漂移的表现形式恰好是
「校验静默失配」这种最难查的形态 —— **口径分叉即等于校验失效**（design §11-A157）。

**本模块零 SQL 文本**（design §4 / A81）：``tests/unit/test_job_repository_terminal.py``
的 ``test_worker_package_contains_no_table_dml_literals`` 守护「``worker/**`` 里出现的
SQL 文本只有 ``BEGIN IMMEDIATE``／``COMMIT``／``ROLLBACK`` 三条」，只读查询也不例外。
故制品行的读取一律委托既有仓储面：``WorkspaceRepository.list_page`` 枚举工作区 ＋
``ArtifactRepository.list_for_workspace`` 逐工作区取行，与 ``worker/store.py`` 委托
``JobRepository`` 是同一分层口径。

时间口径：本模块**不取系统当前时间**（``tests/unit/test_clock.py`` 的全树静态守护），
也不做任何年龄判定 —— 超期临时件的回收归 ``infra.artifacts.sweep_unreferenced``。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sqlalchemy import Connection

from campaignlab.infra.artifacts import hash_file
from campaignlab.infra.db.repositories import (
    ArtifactRecord,
    ArtifactRepository,
    WorkspaceRepository,
)

__all__ = [
    "BYTE_SIZE_MISMATCH",
    "MISSING_FILE",
    "PATH_ESCAPE",
    "RESULT_JSON_UNPARSEABLE",
    "RESULT_REF_DANGLING",
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
#: design §5:52 点名的两种 ``jobs.result_json`` 侧差异形态。**当前不可产出**，见
#: ``verify_artifact_index`` 的 docstring 与本子任务回执的 U 项（枚举 ``jobs`` 行需要
#: 一条只读查询或一个仓储读侧访问器，两者都不在本子任务写权内）。
RESULT_JSON_UNPARSEABLE: Final = "RESULT_JSON_UNPARSEABLE"
RESULT_REF_DANGLING: Final = "RESULT_REF_DANGLING"
#: 两条安全兜底（design §9 的符号面是**下限而非上限**，A151）：复核器读到的路径必须
#: 落在 ``<data_dir>`` 内、且必须真能读出来，否则「一致」这个结论本身不可信。
PATH_ESCAPE: Final = "PATH_ESCAPE"
UNREADABLE: Final = "UNREADABLE"

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


def _artifact_records(conn: Connection) -> list[ArtifactRecord]:
    """全表 ``artifacts`` 行，委托既有仓储面（本模块零 SQL 文本，见模块 docstring）。"""
    workspaces = WorkspaceRepository().list_page(conn, limit=_WORKSPACE_ENUM_LIMIT)
    if len(workspaces) >= _WORKSPACE_ENUM_LIMIT:
        raise RuntimeError(
            f"工作区数达到单次枚举上限 {_WORKSPACE_ENUM_LIMIT}，无法确认已取全；"
            "拒绝在可能漏核的前提下出具「索引一致」结论（请改为分页游标实现并另行裁定）"
        )
    repository = ArtifactRepository()
    records: list[ArtifactRecord] = []
    for workspace in workspaces:
        records.extend(repository.list_for_workspace(conn, workspace.id))
    return records


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


def verify_artifact_index(conn: Connection, data_dir: Path) -> list[Discrepancy]:
    """逐行核 ``artifacts`` 与落盘制品是否一致；``[]`` 即「数据库和制品摘要一致」。

    **已落地的判据（design §5:52 前三项）**：``artifacts.relative_path`` 的存在性、
    sha256、byte_size；另加两条安全兜底（``PATH_ESCAPE`` / ``UNREADABLE``）。

    .. warning::
       **``jobs.result_json`` 那两项判据（``RESULT_JSON_UNPARSEABLE`` /
       ``RESULT_REF_DANGLING``）当前尚未产出**，故本函数返回 ``[]`` 只证明
       「制品侧一致」，**不**证明「``result_json`` 侧一致」。原因不是取舍而是写权：
       枚举 ``jobs`` 行需要一条只读查询或一个 ``JobRepository`` 读侧访问器，而
       ① ``worker/**`` 内的任何 SQL 文本（含只读查询）被
       ``test_worker_package_contains_no_table_dml_literals`` 判红，该守护文件在本子任务
       硬禁内；② ``infra/db/repositories.py`` 现有读侧只有按主键取一行与
       ``list_ready``（只出 QUEUED），**没有**全表／按工作区枚举 jobs 的访问器，
       而 ``infra/db/**`` 同样在硬禁内。两条路都要编排器裁定，已按 A159 报 U 项，
       未自行发明判据、也未用字符串拼接去绕过静态守护（那属静默损坏，R12-1 同类）。
       另：A155① 已把 M0-04 的 ``result_ref`` 断言面定为
       ``ObjectRef(kind="job", id=<job_id>)``，即 id 指向**作业行**而非制品行，
       故「指向存在的制品」在 M0-04 口径下恒不成立 —— 该判据到底核 ``jobs`` 还是核
       ``artifacts`` 也需一并裁定（同一 U 项内）。
    """
    root = Path(data_dir)
    if not root.is_absolute():
        raise ValueError(
            f"data_dir 必须是绝对路径（artifacts.relative_path 相对它解析）：{data_dir!r}"
        )
    resolved_root = root.resolve()
    found: list[Discrepancy] = []
    for record in _artifact_records(conn):
        found.extend(_check_record(record, root=root, resolved_root=resolved_root))
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
