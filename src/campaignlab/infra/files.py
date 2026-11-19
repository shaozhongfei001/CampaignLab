"""导入上传件的文件底座（M1-01 · S2；design §7.4）。

卡片红线：**不把 duckdb 关系导入绕过本文件的摘要登记** ⇒ ``ImportFileStore.register`` 是
导入件摘要登记的**唯一入口**；任何「把文件塞进 DuckDB／Parquet 的关系导入」都必须先经它
拿到 ``artifact_id``。

**零 DML**（A81 不破）：本文件不出现任何 INSERT／UPDATE／DELETE，也不开事务。制品行的写入
发生在 ``infra/artifacts.py::ArtifactWriter.commit`` 内部（它复用
``infra.db.repositories.ArtifactRepository.insert``）；``import_files`` 行由**调用方**在同一
短事务里写。本文件只调 ``ArtifactWriter.begin``／``AttemptStage.write``／``AttemptStage.seal``／
``ArtifactWriter.commit``／``AttemptStage.discard`` 这五个既有公开面（``infra/artifacts.py``
在卡片 ``scope_deny`` 里：**只 import 与调用，禁修改**）。

裁定 **A305**：暂存目录沿用 ``ArtifactWriter.begin(workspace_id, job_id=<import_id>,
attempt=<该导入下的第几个上传件，从 0 起>)``，物理上落在 ``<data_dir>/tmp/jobs/**`` 下。
「名字不副实」是**已记录并被接受**的代价：另立 ``tmp/imports/**`` 需要改 ``scope_deny`` 的
``artifacts.py``，要重写约 200 行原子重命名＋同盘校验＋超期回收，而既有
``sweep_unreferenced`` **只扫** ``results/**`` 与 ``tmp/jobs/**`` ⇒ 另立的目录会变成
没人回收的垃圾。``import_id`` 用 ``imp`` 前缀 ⇒ 过 ``is_resource_id``，可直接当 ``job_id`` 传。

制品 ``kind`` 取 ``IMPORT_FILE``：``relative_path_for`` 的实测 docstring 原文
「三段前缀都是刻意的：``kind`` 分桶让 M1／M2 的多类制品互不混淆」⇒ ``kind`` 是自由 token
（只过 ``_safe_token``），传 ``IMPORT_FILE`` **无需**改 ``artifacts.py``；且落点在
``results/**`` 内 ⇒ 自动受既有 ``sweep_unreferenced`` 的引用边界保护。

时间口径：本文件**不取系统当前时间**，``now`` 一律由调用方注入（design §7.3）。
体积口径：一律从 ``domain/ingest/limits.py`` **单向** import（design §5.2）；裁定 **A299**
已冻结 ``assert_within_size_limit`` 的 detail 文案与「**严格大于**才拒」的边界语义，
本文件禁重述、禁改写、禁另立阈值，也**禁**用 ``AppConfig.max_json_body_bytes``
（1 MiB，仅 JSON 请求正文）当文件上限（ADR-005 §2.3）。
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from sqlalchemy import Connection

from campaignlab.clock import ensure_utc
from campaignlab.domain.ids import new_resource_id
from campaignlab.domain.ingest.limits import assert_within_size_limit
from campaignlab.domain.ingest.states import ImportFormat
from campaignlab.infra.artifacts import ArtifactWriter, AttemptStage

__all__ = [
    "ARTIFACT_KIND_IMPORT_FILE",
    "UPLOAD_CHUNK_BYTES",
    "ImportFileRef",
    "ImportFileStore",
    "label_from_filename",
]

#: ``artifacts.kind`` 的导入上传件取值（design §7.4；与既有 ``ARTIFACT_KIND_JOB_RESULT`` 同体例）。
ARTIFACT_KIND_IMPORT_FILE: Final = "IMPORT_FILE"

#: 流式喂字节时的分块大小（1 MiB，与 ``infra/artifacts.py`` 内部实测的
#: ``_HASH_CHUNK_BYTES == 1 << 20`` 同量级）：块越小，413 的判定点越靠前、白读的字节越少；
#: 块越大，系统调用越少。取 1 MiB 是这两端的既有平衡点。
UPLOAD_CHUNK_BYTES: Final = 1 << 20

#: 活契约 ``ImportFile.label`` 的 ``maxLength``（本轮实测 **180**；``minLength`` 为 1）。
_LABEL_MAX_LENGTH: Final = 180

#: ``import_files.id`` 前缀（与 ``artifacts`` 的 ``art``、``jobs`` 的 ``job`` 同体例）。
_IMPORT_FILE_ID_PREFIX: Final = "imf"

#: 413 的 ``location`` 段：指到 ``AttachFile.table_name`` 所代表的那一份上传件。
_SIZE_LOCATION_PREFIX: Final = "/files/"


@dataclass(frozen=True, slots=True)
class ImportFileRef:
    """一次成功登记的导入上传件：``import_files`` 行 ＋ ``ImportFile`` DTO 所需的全部字段。

    ``import_file_id`` 由本模块生成（``imf`` 前缀，过 ``is_resource_id``），但**行不由本模块写**
    （零 DML）：调用方在同一个 ``BEGIN IMMEDIATE`` 短事务里 INSERT ``import_files``
    （design §7.4 的 ``TX-I1``／``TX-I2`` 面）。

    裁定 **A306**：``NormalizedSlice.source_row.source_file_id`` 一律取本字段
    （``import_files.id``），**不是** ``artifact_id`` —— ``artifacts`` 是内容寻址且
    **跨导入共享**的（``CommittedArtifact.reused_file``／``reused_row`` 就是为此存在），
    用它做 ``source_file_id`` 会在内容复用场景下歧义；且 ``table_name`` 与 ``import_files.id``
    同表 ⇒ ``(source_file_id, table_name, row_number)`` 三元组自洽。

    ⚠ 已落地的 ``model.py::FileRef`` 只有 ``(table_name, sha256, size_bytes)`` 三字段、
    ``UploadedFile`` 亦然 ⇒ 本字段目前**无法**经 ``RawSource`` 流进 ``normalize()``。
    这是冻结数据形状与裁定 A306 之间的实缺口，已如实回报为升级项（需 CR 扩 ``FileRef``
    或给 ``normalize()`` 注入 ``table_name → import_files.id`` 映射），禁在本棒自行改冻结面。
    """

    import_file_id: str
    workspace_id: str
    import_id: str
    table_name: str
    label: str
    artifact_id: str
    sha256: str
    size_bytes: int
    relative_path: str
    path: Path
    reused_file: bool
    reused_row: bool


def label_from_filename(filename: str) -> str:
    """由上传文件名派生 ``import_files.label``（活契约 ``ImportFile.label``：1–180 字符）。

    只取 **basename**（``/`` 与 ``\\`` 都当分隔符：客户端可能来自任一平台，且
    ``AttachFile`` 是 multipart 上传，浏览器给的 ``filename`` 有时会带整条本地路径），
    滤掉不可打印字符（控制字符进 SQLite TEXT 列后在页面上不可见，等于丢证据），
    再按契约上限**从尾部截断**（保留前缀：文件名前缀通常更具辨识度）。

    结果为空一律 ``ValueError`` —— 契约的 ``minLength=1`` 不允许空 label，
    静默兜一个占位串会让「这是哪一份文件」这条证据失真（体例＝``infra/artifacts.py``
    的 ``_safe_token``：路径／标识面非法就立刻报，不猜）。
    """
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = "".join(char for char in base if char.isprintable()).strip()
    if not cleaned:
        raise ValueError(f"无法从文件名派生非空 label：{filename!r}")
    return cleaned[:_LABEL_MAX_LENGTH]


class ImportFileStore:
    """导入上传件的暂存与摘要登记（design §7.4 的公开面：三个方法，不多不少）。

    无状态可复用：所有路径都由 ``data_dir`` 派生（经注入的 ``ArtifactWriter``），
    本类不持连接、不持文件句柄（句柄在 ``AttemptStage`` 上）、不持时钟（``now`` 由调用方注入）。
    """

    __slots__ = ("_writer",)

    def __init__(self, data_dir: Path, *, writer: ArtifactWriter | None = None) -> None:
        self._writer = writer if writer is not None else ArtifactWriter(data_dir)

    def stage_from_chunks(
        self,
        *,
        workspace_id: str,
        import_id: str,
        attempt: int,
        fmt: ImportFormat,
        table_name: str,
        chunks: Iterable[bytes] | Path,
        chunk_size: int = UPLOAD_CHUNK_BYTES,
    ) -> AttemptStage:
        """把上传字节喂进一个**独立尝试目录**，边喂边判 design §5.2 的体积上限。

        事务外调用（``begin``／``write``／``seal`` 都不碰数据库）；判定用**流式累计**而不是
        一次性 ``len(body)`` —— ``read_body_within_limit`` 的 docstring 原文即此警告：
        先全量读入再判长度等于**没有**上限。裁定 **A299**：``assert_within_size_limit``
        用严格大于判定 ⇒ **恰好等于上限放行、严格大于才拒**，与 AC-005「大于 8 MiB 拒绝」一致。

        **不留半成品**（design §5.2 的 ``test_size_limit_leaves_no_partial_artifact`` 断言面）：
        任何异常（含 413）都先 ``stage.discard()`` 再原样冒出去 —— ``discard()`` 删暂存件与
        本次尝试目录，于是 ``artifacts`` 表零插入、``import_files`` 表零插入、终态目录零文件，
        而 ``imports`` 行根本还没被创建／改状态（413 抛在 TX 之前）。

        ``attempt`` ＝ 该导入下的第几个上传件（从 0 起，design §7.4 的冻结口径）；
        ``job_id`` 位传 ``import_id``（裁定 **A305**）。
        """
        stage = self._writer.begin(workspace_id, import_id, attempt)
        location = f"{_SIZE_LOCATION_PREFIX}{table_name}"
        written = 0
        try:
            for chunk in _iter_chunks(chunks, chunk_size):
                assert_within_size_limit(
                    fmt=fmt, size_bytes=written + len(chunk), location=location
                )
                written += stage.write(chunk)
            stage.seal()
        except BaseException:
            stage.discard()
            raise
        return stage

    def register(
        self,
        conn: Connection,
        stage: AttemptStage,
        *,
        workspace_id: str,
        import_id: str,
        table_name: str,
        label: str,
        now: datetime,
    ) -> ImportFileRef:
        """**摘要登记的唯一入口**：``ArtifactWriter.commit`` ＋ 组装 ``import_files`` 行所需字段。

        本方法**零 DML**：``artifacts`` 行的 INSERT 发生在 ``commit()`` 内部（经
        ``ArtifactRepository.insert``）；``import_files`` 行由**调用方**写。
        必须在调用方已开的 ``BEGIN IMMEDIATE`` 事务内调用（``commit()`` 的既有约束：
        文件搬移与索引登记同事务，才不会出现「DB 有行 ⇔ 磁盘无文件」的悬挂态）。

        ``now`` 一律注入并经 ``ensure_utc`` 归一（禁系统当前时间做领域计算，design §7.3）。
        ``commit()`` 天生幂等（JOBS.md:25「事务提交失败允许重试并复用同摘要文件」）：
        同内容 ⇒ 同摘要 ⇒ 同终态路径，``reused_file``／``reused_row`` 会把复用情况报回来，
        ``artifact_id`` 一律取 ``commit()`` 的**回读**值。
        """
        committed = self._writer.commit(
            conn,
            stage,
            workspace_id=workspace_id,
            kind=ARTIFACT_KIND_IMPORT_FILE,
            now=ensure_utc(now),
        )
        return ImportFileRef(
            import_file_id=new_resource_id(_IMPORT_FILE_ID_PREFIX),
            workspace_id=workspace_id,
            import_id=import_id,
            table_name=table_name,
            label=label,
            artifact_id=committed.artifact_id,
            sha256=committed.sha256,
            size_bytes=committed.byte_size,
            relative_path=committed.relative_path,
            path=committed.path,
            reused_file=committed.reused_file,
            reused_row=committed.reused_row,
        )

    def label_from_filename(self, filename: str) -> str:
        """实例面转发到模块级 ``label_from_filename``。

        design §7.4 把它列为 ``ImportFileStore`` 的**方法**，§11.1 又把它列为
        ``infra/files.py`` 的**模块级符号** ⇒ 两处都要有，且只能有**一份实现**
        （本方法只是转发，禁在类里另写一份规则）。
        """
        return label_from_filename(filename)


def _iter_chunks(source: Iterable[bytes] | Path, chunk_size: int) -> Iterator[bytes]:
    """把「一个文件路径」或「一段字节迭代器」统一成字节块迭代器。

    ``Path`` 分支按 ``chunk_size`` 读 ⇒ 大文件不会整份进内存（这正是「流式累计判上限」
    能成立的前提）；``Iterable`` 分支原样透传，由调用方决定块大小
    （HTTP 侧一般直接喂 multipart 的分块）。
    """
    if chunk_size <= 0:
        raise ValueError(f"chunk_size 必须是正整数：{chunk_size!r}")
    if isinstance(source, Path):
        with source.open("rb") as handle:
            while True:
                block = handle.read(chunk_size)
                if not block:
                    break
                yield block
        return
    yield from source
