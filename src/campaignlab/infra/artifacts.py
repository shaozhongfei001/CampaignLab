"""原子制品写入（M0-04/S3；design §5 · 交付后按卡内 ``public_frozen`` 列为公共件）。

JOBS.md:25「事务提交失败允许重试并复用同摘要文件」与 OPERATIONS.md:22「只清理超期临时件与
没有记录引用的制品」这两句话，落到文件系统上只有三个支点，本文件就是这三点：

1. **独立尝试目录** ``<data_dir>/tmp/jobs/<workspace_id>/<job_id>/<attempt>/``：``attempt``
   进路径，故重试与并发尝试互不覆写；暂存文件名带随机后缀，同一次尝试内重复 ``begin()``
   也不会互相踩。
2. **同盘原子重命名**：终态路径按**内容寻址**
   ``<data_dir>/results/<kind>/<workspace_id>/<sha256[:2]>/<sha256>``，``os.replace()`` 把
   暂存件搬过去。同内容 ⇒ 同摘要 ⇒ 同路径，所以「提交失败后重试复用同一个摘要文件」不是
   特例分支，而是路径函数的推论。``os.replace()`` 的原子性只在同一文件系统内成立，跨设备
   抛 ``EXDEV``：本文件把它**判红**（``ArtifactCommitFailed``）而不是退化成 copy —— copy
   中途失败会留下半截终态文件，那比失败本身更难查。``verify_same_filesystem()`` 是同一前提
   的启动期检查（不符 → ``ConfigError`` → CLI 侧 rc=2），也是 AC-031「阻止错误切换」的
   写入侧前提之一。
3. **登记与业务写入同事务**：``commit()`` 收 ``Connection``，由调用方在 ``BEGIN IMMEDIATE``
   内调用（design §4 TX5）。文件重命名、``artifacts`` 行登记、以及随后把 ``result_json``
   写进 ``jobs`` 的那条谓词 UPDATE 共用同一事务，于是「终态文件在、索引里没有行」只可能是
   回滚的产物，而那种孤儿件正是 ``sweep_unreferenced()`` 的回收对象。

时间口径：本模块**不取系统当前时间**（``tests/unit/test_clock.py`` 的全树静态守护）。
``commit()``／``sweep_unreferenced()`` 的 ``now`` 一律由调用方从 ``Clock`` 传入；文件年龄用
``st_mtime`` 与传入的 ``now`` 比，``min_age`` 可注入小值，故测试无需 ``sleep``。

SQL 口径：本模块**零 DML**。``artifacts`` 行的写入一律经
``infra.db.repositories.ArtifactRepository.insert``（A81 收敛的是**写点**）；本模块只发两条
只读 ``SELECT``（按内容摘要回读权威 id、取全表已引用路径），因为仓储面没有这两个查询，而
``infra/db/**`` 不在本卡写权内（design §5 明确要求「回读权威 id」）。
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import math
import os
import re
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import IO, Final

from sqlalchemy import Connection, text

from campaignlab.clock import ensure_utc
from campaignlab.config import ConfigError
from campaignlab.domain.ids import is_resource_id, new_request_id, new_resource_id
from campaignlab.infra.db.repositories import ArtifactRecord, ArtifactRepository
from campaignlab.worker.errors import ArtifactCommitFailed

__all__ = [
    "ARTIFACT_ID_PREFIX",
    "ARTIFACT_KIND_JOB_RESULT",
    "TMP_STALE_SECONDS",
    "ArtifactWriter",
    "AttemptStage",
    "CommittedArtifact",
    "SweepReport",
    "relative_path_for",
    "results_root",
    "stage_root",
    "sweep_unreferenced",
]

#: ``artifacts.kind`` 的作业结果取值（A89 裁定，design §10 注⑥为其权威来源）。
ARTIFACT_KIND_JOB_RESULT: Final = "JOB_RESULT"
#: 尝试目录的超期边界（design §2 的运行参数表）。测试用 ``sweep_unreferenced(min_age=...)``
#: 注入小值；``config.AppConfig`` 不在本卡写权内，故本模块只给常量默认值、不改配置面。
TMP_STALE_SECONDS: Final = 3600
#: ``artifacts.id`` 前缀（与 ``audit`` 的 ``aud``、``workspaces`` 的 ``ws`` 同体例）。
ARTIFACT_ID_PREFIX: Final = "art"

#: OPERATIONS.md:17 七子目录里的 ``tmp``／``results``。字符串只在本模块出现一次。
_TMP_PARTS: Final[tuple[str, ...]] = ("tmp", "jobs")
_RESULTS_DIRNAME: Final = "results"
#: 暂存文件后缀：``.part`` 明示「尚未成为终态制品」，也让「results 下不该有 .part」可断言。
_STAGE_PAYLOAD_SUFFIX: Final = ".part"
_SHA256_HEX_LENGTH: Final = 64
_SHA256_PREFIX_LENGTH: Final = 2
_HASH_CHUNK_BYTES: Final = 1 << 20
_MAX_TOKEN_LENGTH: Final = 96
_SHA256_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
#: 尝试目录相对 ``tmp/jobs`` 的层数：``<workspace_id>/<job_id>/<attempt>``。
_ATTEMPT_DEPTH_GLOB: Final = "*/*/*"

#: 本进程内在飞的尝试目录 -> 引用计数。``sweep_unreferenced`` 永不回收其中的目录，
#: 即使它们的 ``st_mtime`` 已经被人为推到超期（跨进程的在飞只能靠 ``min_age`` 兜底）。
_LIVE_STAGES: Final[dict[Path, int]] = {}


def _stage_entered(key: Path) -> None:
    _LIVE_STAGES[key] = _LIVE_STAGES.get(key, 0) + 1


def _stage_exited(key: Path) -> None:
    remaining = _LIVE_STAGES.get(key, 0) - 1
    if remaining > 0:
        _LIVE_STAGES[key] = remaining
    else:
        _LIVE_STAGES.pop(key, None)


def _in_flight_attempt_dirs() -> frozenset[Path]:
    return frozenset(_LIVE_STAGES)


# --------------------------------------------------------------------------------- 路径面


def stage_root(data_dir: Path) -> Path:
    """独立尝试目录的根：``<data_dir>/tmp/jobs``（design §5 目录布局）。"""
    return Path(data_dir).joinpath(*_TMP_PARTS)


def results_root(data_dir: Path) -> Path:
    """终态制品的根：``<data_dir>/results``（OPERATIONS.md:17 七子目录之一）。"""
    return Path(data_dir) / _RESULTS_DIRNAME


def _sha256_hex(value: str) -> str:
    """摘要必须是 64 位小写十六进制（活契约 ``input_digest`` 的 ``^[0-9a-f]{64}$`` 同口径）。"""
    if _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"sha256 必须是 64 位小写十六进制：{value!r}")
    return value


def _safe_token(value: str, *, what: str) -> str:
    """路径片段校验：非空、无分隔符、无 NUL、不以点／空格结尾（Windows 路径陷阱）。"""
    if not value or value in {".", ".."} or len(value) > _MAX_TOKEN_LENGTH:
        raise ValueError(f"{what} 非法（空／.／..／超过 {_MAX_TOKEN_LENGTH} 字符）：{value!r}")
    if "/" in value or "\\" in value or "\x00" in value:
        raise ValueError(f"{what} 不得含路径分隔符或 NUL：{value!r}")
    if value != value.rstrip(". "):
        raise ValueError(f"{what} 不得以点或空格结尾（跨平台路径会被静默改写）：{value!r}")
    return value


def relative_path_for(*, kind: str, workspace_id: str, sha256: str) -> str:
    """内容寻址的**相对**路径（相对 ``<data_dir>``，posix 分隔符，永不为绝对路径）。

    形状：``results/<kind>/<workspace_id>/<sha256[:2]>/<sha256>``。三段前缀都是刻意的：
    ``kind`` 分桶让 M1/M2 的多类制品互不混淆；``workspace_id`` 进路径是 DDL 把
    ``relative_path`` 定为**全表 UNIQUE**（不含 ``workspace_id``）逼出来的 —— 否则两个
    工作区的同内容制品会撞唯一键；``sha256[:2]`` 扇出避免单目录堆十万文件。
    """
    digest = _sha256_hex(sha256)
    token = _safe_token(kind, what="kind")
    if not is_resource_id(workspace_id):
        raise ValueError(f"workspace_id 不匹配活契约 ID 正则：{workspace_id!r}")
    return "/".join((_RESULTS_DIRNAME, token, workspace_id, digest[:_SHA256_PREFIX_LENGTH], digest))


def _hash_file(path: Path, *, chunk_size: int = _HASH_CHUNK_BYTES) -> tuple[str, int]:
    """流式算一个已落盘文件的 ``(sha256, byte_size)``。

    刻意不做成公开符号：design §9 给 S3 划定的符号面里没有它。M0-04/S2b 的
    ``worker/integrity.py::verify_artifact_index`` 需要同一能力，是否把它提升为公共件
    已作为裁定项上交编排器（禁自行扩冻结面）。
    """
    hasher = hashlib.sha256()
    total = 0
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
            total += len(chunk)
    return hasher.hexdigest(), total


def _mtime(path: Path) -> float:
    """文件年龄基准。读不到 ``st_mtime`` 就当作「无限新鲜」→ 不回收（保守优先）。"""
    try:
        return path.lstat().st_mtime
    except OSError:
        return math.inf


def _newest_mtime(root: Path) -> float:
    """子树内最新的 ``st_mtime``。

    只看目录自身的 mtime 是不够的：目录 mtime 只在增删条目时变化，一个正在被写入的大制品
    会让「尝试目录看起来很久没动」，于是被误判为超期。取子树最新值就把「在飞写入」纳入
    了年龄基准。
    """
    newest = _mtime(root)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        for name in (*dirnames, *filenames):
            newest = max(newest, _mtime(Path(dirpath) / name))
    return newest


def _iter_files(root: Path) -> Iterator[Path]:
    """深度优先、**不跟随符号链接**、顺序确定地遍历文件。"""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        for name in sorted(filenames):
            yield Path(dirpath) / name


def _prune_empty_dirs(root: Path) -> None:
    """自底向上删空目录（``root`` 自身保留）。非空即 ``OSError``，正是「不误删别人」。"""
    for dirpath, dirnames, _filenames in os.walk(root, topdown=False, followlinks=False):
        for name in dirnames:
            candidate = Path(dirpath) / name
            try:
                candidate.rmdir()
            except OSError:
                continue


def _assert_within(root: Path, target: Path) -> Path:
    """受控目录守卫（OPERATIONS.md:11「制品路径使用受控目录和 ID 解析」）。"""
    resolved = Path(target).resolve()
    if not resolved.is_relative_to(Path(root).resolve()):
        raise ValueError(f"目标路径逃逸出受控目录：root={root} target={target}")
    return resolved


# ------------------------------------------------------------------------------- 数据形状


@dataclass(frozen=True, slots=True)
class CommittedArtifact:
    """一次成功提交的制品：权威 id ＋ 内容寻址路径 ＋ 落盘位置。

    ``artifact_id`` 是**回读**得到的值（design §5：摘要冲突时既有行的 id 胜出，禁用刚生成的
    id），因此可以直接进 ``result_ref``／``jobs.result_json``。

    ``reused_file`` 为真表示终态路径上已有同摘要文件、本次跳过了 ``os.replace``（JOBS.md:25
    的复用路径）；``reused_row`` 为真表示 ``artifacts`` 里已有同
    ``(workspace_id, kind, sha256)`` 行。

    .. warning::
       ``commit()`` 已经在**同一事务内**登记了 ``artifacts`` 行，调用方**禁**再把本对象
       交给 ``worker/store.py::JobStore.succeed(artifacts=...)`` —— 那会二次 INSERT 撞
       ``UNIQUE(workspace_id,kind,sha256)``。正确用法是 ``succeed(..., artifacts=())``，
       或按 design §4 在同一个 ``BEGIN IMMEDIATE`` 里先 ``commit()`` 再发终态 UPDATE。
    """

    workspace_id: str
    artifact_id: str
    kind: str
    sha256: str
    relative_path: str
    byte_size: int
    path: Path
    reused_file: bool
    reused_row: bool


@dataclass(frozen=True, slots=True)
class SweepReport:
    """一次未引用制品回收的战果。所有路径都是相对 ``<data_dir>`` 的 posix 串。

    ``dry_run=True``（默认）时 ``removed_*`` 恒为 0，四个列表就是「将会动谁」的预告，
    可直接进证据；``dry_run=False`` 才真删。
    """

    dry_run: bool
    min_age_seconds: int
    referenced_rows: int
    scanned_result_files: int
    referenced_files_seen: int
    unreferenced_files: tuple[str, ...]
    young_unreferenced_files: tuple[str, ...]
    stale_attempt_dirs: tuple[str, ...]
    in_flight_attempt_dirs: tuple[str, ...]
    young_attempt_dirs: tuple[str, ...]
    skipped_symlinks: int
    removed_files: int
    removed_dirs: int
    failed_removals: tuple[str, ...]

    @property
    def candidates(self) -> int:
        """命中回收条件的对象数（未引用终态文件 ＋ 超期尝试目录）。"""
        return len(self.unreferenced_files) + len(self.stale_attempt_dirs)

    @property
    def removed(self) -> int:
        return self.removed_files + self.removed_dirs


# -------------------------------------------------------------------------------- 尝试目录


class AttemptStage:
    """一次尝试的独立暂存目录与其中的暂存文件（design §5「独立尝试目录」）。

    用法（由 ``ArtifactWriter.begin()`` 返回，一般作上下文管理器）::

        with writer.begin(workspace_id, job_id, attempt) as stage:
            stage.write(chunk)                       # 增量喂 sha256／byte_size（事务外）
            committed = writer.commit(conn, stage, workspace_id=..., kind=..., now=now)
        # 退出时：已提交 → 只清空尝试目录；未提交 → 连暂存件一起清掉

    摘要与字节数**增量**累计，因此大制品不需要在内存里存第二份，也不需要在提交前把文件
    重读一遍；``seal()`` 会 flush + ``fsync`` 后再关句柄，保证 ``os.replace`` 搬到终态的
    是一份已经落盘的内容（否则崩溃后可能看到零长度终态文件）。
    """

    __slots__ = (
        "_byte_size",
        "_committed",
        "_handle",
        "_hasher",
        "_live_key",
        "_released",
        "_sealed",
        "_writer",
        "attempt",
        "directory",
        "job_id",
        "path",
        "workspace_id",
    )

    def __init__(
        self,
        *,
        writer: ArtifactWriter,
        workspace_id: str,
        job_id: str,
        attempt: int,
        directory: Path,
        path: Path,
    ) -> None:
        self._writer = writer
        self.workspace_id = workspace_id
        self.job_id = job_id
        self.attempt = attempt
        self.directory = directory
        self.path = path
        self._hasher = hashlib.sha256()
        self._byte_size = 0
        self._handle: IO[bytes] | None = None
        self._sealed = False
        self._committed = False
        self._released = False
        self._live_key = directory.resolve()
        _stage_entered(self._live_key)

    # --------------------------------------------------------------------------- 写入面

    @property
    def sha256(self) -> str:
        """到目前为止写入内容的 sha256（十六进制小写，64 位）。"""
        return self._hasher.hexdigest()

    @property
    def byte_size(self) -> int:
        return self._byte_size

    @property
    def committed(self) -> bool:
        return self._committed

    def write(self, chunk: bytes) -> int:
        """追加一段内容，并同步推进摘要与字节数。返回写入字节数。

        每块写完立刻 ``flush()``（**不是** ``fsync``，那留给 ``seal()``）：缓冲留在进程内
        会让暂存件的 ``st_mtime`` 停在开始写入的那一刻，于是「写一个小时的巨大制品」在
        另一个进程的 ``sweep_unreferenced`` 眼里就成了超期尝试目录。flush 让 mtime 跟着
        写入进度走，跨进程的在飞保护（``min_age``）才真的成立。
        """
        if self._sealed or self._committed:
            raise ValueError("暂存件已封口／已提交，不得再写入（摘要会与内容脱节）")
        handle = self._handle
        if handle is None:
            handle = self.path.open("wb")
            self._handle = handle
        handle.write(chunk)
        handle.flush()
        self._hasher.update(chunk)
        self._byte_size += len(chunk)
        return len(chunk)

    def write_file(self, source: Path, *, chunk_size: int = _HASH_CHUNK_BYTES) -> int:
        """把一个已存在的文件按块搬进暂存件（同样增量算摘要）。返回搬运字节数。"""
        written = 0
        with Path(source).open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                self.write(chunk)
                written += len(chunk)
        return written

    def seal(self) -> None:
        """封口：flush + ``fsync`` + 关句柄；从未写过则落一个空制品。幂等。"""
        if self._sealed:
            return
        handle, self._handle = self._handle, None
        if handle is not None:
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
        elif not self.path.exists():
            self.path.write_bytes(b"")
        self._sealed = True

    # --------------------------------------------------------------------------- 收尾面

    def mark_committed(self) -> None:
        """``commit()`` 成功登记后调用：暂存件已被 rename 走（或复用既有终态件），只清目录。"""
        if self._committed:
            return
        self.seal()
        self._committed = True
        self._drop_payload()
        self._prune()
        self._release()

    def discard(self) -> None:
        """未提交即弃：删暂存件与本次尝试目录。幂等；已提交则为空操作。"""
        if self._committed:
            return
        handle, self._handle = self._handle, None
        if handle is not None:
            with contextlib.suppress(OSError):
                handle.close()
        self._sealed = True
        self._drop_payload()
        self._prune()
        self._release()

    def __enter__(self) -> AttemptStage:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        # 刻意不吞异常（返回 None）：提交失败的原因必须原样冒到调用方。
        if not self._committed:
            self.discard()

    # ------------------------------------------------------------------------- 内部动作

    def _drop_payload(self) -> None:
        with contextlib.suppress(OSError):
            self.path.unlink(missing_ok=True)

    def _prune(self) -> None:
        """删掉本次尝试留下的空目录（attempt / job / workspace 三级，只在真空时删）。"""
        for candidate in (self.directory, self.directory.parent, self.directory.parent.parent):
            try:
                candidate.rmdir()
            except OSError:
                continue

    def _release(self) -> None:
        if self._released:
            return
        self._released = True
        _stage_exited(self._live_key)


# ---------------------------------------------------------------------------------- 写入器


class ArtifactWriter:
    """原子制品写入器（design §5 的 ``begin``／``commit``／``verify_same_filesystem``）。

    无状态可复用：所有路径都由 ``data_dir`` 派生，不持有连接、不持有文件句柄（句柄在
    ``AttemptStage`` 上）。``ArtifactRepository`` 可注入，与 ``worker/store.py`` 同一 DI
    体例，便于测试替身。
    """

    __slots__ = ("_artifacts", "_data_dir")

    def __init__(self, data_dir: Path, *, artifacts: ArtifactRepository | None = None) -> None:
        resolved = Path(data_dir)
        if not resolved.is_absolute():
            raise ValueError(f"data_dir 必须是绝对路径（制品路径要能跨进程解析）：{data_dir!r}")
        self._data_dir = resolved
        self._artifacts = artifacts if artifacts is not None else ArtifactRepository()

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    @property
    def tmp_root(self) -> Path:
        return stage_root(self._data_dir)

    @property
    def results_dir(self) -> Path:
        return results_root(self._data_dir)

    # --------------------------------------------------------------------- 启动期前提检查

    def verify_same_filesystem(self) -> None:
        """断言暂存根与终态根同设备（design §5：不符即抛配置错，CLI 侧 rc=2）。

        跨设备 ``os.replace()`` 会 ``EXDEV``、原子性无从保证；这条检查同时是 AC-031
        「快照缺件可定位并阻止错误切换」的写入侧前提之一：数据目录被挂到两个盘上时，
        进程**不该启动**，而不是等到第一次提交才留下半截制品。
        """
        tmp_root = self.tmp_root
        results_dir = self.results_dir
        for root in (tmp_root, results_dir):
            root.mkdir(parents=True, exist_ok=True)
        tmp_dev = os.stat(tmp_root).st_dev
        results_dev = os.stat(results_dir).st_dev
        if tmp_dev != results_dev:
            raise ConfigError(
                "制品暂存目录与终态目录不在同一文件系统，os.replace 无法保证原子性："
                f"tmp={tmp_root}(st_dev={tmp_dev}) results={results_dir}(st_dev={results_dev})；"
                "请把 <data_dir> 整体放在同一挂载点（跨设备复制会留下半截终态文件）"
            )

    # ------------------------------------------------------------------------- 开暂存件

    def begin(self, workspace_id: str, job_id: str, attempt: int) -> AttemptStage:
        """开一个**独立尝试目录**并返回其暂存件（design §5 写入序的第一步）。

        ``attempt`` 进路径 ⇒ 同一作业的重试／并发尝试互不覆写；暂存文件名带随机后缀 ⇒
        同一尝试内重复 ``begin()`` 也互不覆写。本方法只碰 ``tmp/jobs/**``，不碰终态目录、
        不碰数据库，因此可以在事务外安全调用。
        """
        if not is_resource_id(workspace_id):
            raise ValueError(f"workspace_id 不匹配活契约 ID 正则：{workspace_id!r}")
        if not is_resource_id(job_id):
            raise ValueError(f"job_id 不匹配活契约 ID 正则：{job_id!r}")
        if attempt < 0:
            raise ValueError(f"attempt 必须是非负整数（jobs.attempt 同口径）：{attempt!r}")
        directory = self.tmp_root / workspace_id / job_id / str(attempt)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"payload-{new_request_id()}{_STAGE_PAYLOAD_SUFFIX}"
        return AttemptStage(
            writer=self,
            workspace_id=workspace_id,
            job_id=job_id,
            attempt=attempt,
            directory=directory,
            path=path,
        )

    # --------------------------------------------------------------------- 原子提交（TX5）

    def commit(
        self,
        conn: Connection,
        stage: AttemptStage,
        *,
        workspace_id: str,
        kind: str,
        now: datetime,
    ) -> CommittedArtifact:
        """同盘原子重命名 ＋ 同事务登记索引，返回权威 id（design §5 写入序第二／三步）。

        必须在调用方已开的 ``BEGIN IMMEDIATE`` 事务内调用（``worker/store.py::immediate``）：
        文件搬移、``artifacts`` 行登记、以及业务侧那条把 ``result_json`` 写进 ``jobs`` 的
        谓词 UPDATE 共用同一事务，才不会出现「索引有行、文件不在」或「文件在、索引没行」
        的悬挂态。

        幂等性（JOBS.md:25）：终态路径已有同摘要文件则**跳过** ``os.replace`` 直接登记，
        已有同 ``(workspace_id, kind, sha256)`` 行则**复用**其 id。故 TX5 回滚后重试会命中
        同一个摘要文件；``artifact_id`` 一律取回读值，禁用刚生成的 id。
        """
        if stage._writer is not self:
            raise ValueError("stage 不是本 ArtifactWriter 开的：data_dir 不一致，终态路径会落错盘")
        if stage.workspace_id != workspace_id:
            raise ValueError(
                "commit 的 workspace_id 与暂存目录不一致："
                f"stage={stage.workspace_id!r} arg={workspace_id!r}"
            )
        stage.seal()
        digest = stage.sha256
        byte_size = stage.byte_size
        relative = relative_path_for(kind=kind, workspace_id=workspace_id, sha256=digest)
        final_path = _assert_within(self._data_dir, self._data_dir.joinpath(*relative.split("/")))
        reused_file = self._place_file(
            stage, final_path=final_path, digest=digest, byte_size=byte_size
        )
        artifact_id, reused_row = self._register(
            conn,
            workspace_id=workspace_id,
            kind=kind,
            digest=digest,
            relative_path=relative,
            byte_size=byte_size,
            now=now,
            final_path=final_path,
        )
        stage.mark_committed()
        return CommittedArtifact(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            kind=kind,
            sha256=digest,
            relative_path=relative,
            byte_size=byte_size,
            path=final_path,
            reused_file=reused_file,
            reused_row=reused_row,
        )

    # --------------------------------------------------------------------------- 内部动作

    def _place_file(
        self, stage: AttemptStage, *, final_path: Path, digest: str, byte_size: int
    ) -> bool:
        """把暂存件搬到内容寻址的终态路径。返回 ``True`` 表示复用了既有终态文件。"""
        if final_path.exists():
            actual_digest, actual_size = _hash_file(final_path)
            if actual_size != byte_size or actual_digest != digest:
                raise ArtifactCommitFailed(
                    "终态路径上已有不同内容的文件，拒绝覆盖（内容寻址冲突或受控目录被污染）："
                    f"path={final_path} 期望 sha256={digest}/{byte_size}B "
                    f"实测 sha256={actual_digest}/{actual_size}B"
                )
            return True
        final_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(stage.path, final_path)
        except OSError as error:
            if error.errno == errno.EXDEV:
                raise ArtifactCommitFailed(
                    "暂存目录与终态目录跨文件系统，os.replace 无法原子完成（EXDEV）："
                    f"src={stage.path} dst={final_path}；请把 <data_dir> 放在同一挂载点，"
                    "并在启动时调用 verify_same_filesystem() 提前判红（禁退化成 copy）"
                ) from error
            raise ArtifactCommitFailed(
                f"原子重命名失败：src={stage.path} dst={final_path} "
                f"errno={error.errno} detail={error.strerror}"
            ) from error
        placed = final_path.stat().st_size
        if placed != byte_size:
            raise ArtifactCommitFailed(
                f"重命名后终态文件字节数不符：path={final_path} 期望={byte_size} 实测={placed}"
            )
        return False

    def _register(
        self,
        conn: Connection,
        *,
        workspace_id: str,
        kind: str,
        digest: str,
        relative_path: str,
        byte_size: int,
        now: datetime,
        final_path: Path,
    ) -> tuple[str, bool]:
        """在调用方的事务内登记 ``artifacts`` 行，返回 ``(权威 id, 是否复用既有行)``。

        写路径复用 ``ArtifactRepository.insert``（本模块零 DML）。先按内容摘要查一次：
        ``BEGIN IMMEDIATE`` 已把写者串行化，故「查不到 → 插入」之间不会有第二个写者插进来，
        等价于 design §5 写的 ``ON CONFLICT(workspace_id,kind,sha256) DO NOTHING``，却不必
        在仓储面之外再开一个 INSERT 落点。插入后**再回读一次**取权威 id（design §5：冲突
        时既有行的 id 胜出，``result_ref.id`` 禁用刚生成的 id）。
        """
        existing = self._select_artifact_id(
            conn, workspace_id=workspace_id, kind=kind, digest=digest
        )
        if existing is not None:
            return existing, True
        try:
            self._artifacts.insert(
                conn,
                artifact=ArtifactRecord(
                    workspace_id=workspace_id,
                    id=new_resource_id(ARTIFACT_ID_PREFIX),
                    kind=kind,
                    sha256=digest,
                    relative_path=relative_path,
                    byte_size=byte_size,
                    created_at=ensure_utc(now).isoformat(),
                ),
            )
            authoritative = self._select_artifact_id(
                conn, workspace_id=workspace_id, kind=kind, digest=digest
            )
        except BaseException:
            # 登记失败 ⇒ 事务必然回滚 ⇒ 刚刚搬过去的终态文件此刻**无人引用**。就地删掉，
            # 不把清理全推给 sweep：sweep 兜的是「commit 已成功、TX5 的谓词 UPDATE
            # rowcount=0（租约失效／取消抢先）而回滚」那种本函数之外的失败（design §4）。
            # 删除是安全的：走到这里说明本事务内查不到任何已提交行引用该 relative_path，
            # 而 relative_path 由 (kind, workspace_id, sha256) 唯一决定。
            self._reclaim(final_path)
            raise
        if authoritative is None:
            raise ArtifactCommitFailed(
                "artifacts 登记后回读失败（索引与制品不一致，事务应回滚）："
                f"workspace={workspace_id} kind={kind} sha256={digest}"
            )
        return authoritative, False

    def _select_artifact_id(
        self, conn: Connection, *, workspace_id: str, kind: str, digest: str
    ) -> str | None:
        """按内容摘要回读权威 id（design §5 的 ``SELECT id FROM artifacts WHERE ...``）。"""
        row = (
            conn.execute(
                text(
                    "SELECT id FROM artifacts "
                    "WHERE workspace_id = :workspace_id AND kind = :kind AND sha256 = :sha256"
                ),
                {"workspace_id": workspace_id, "kind": kind, "sha256": digest},
            )
            .scalars()
            .first()
        )
        return None if row is None else str(row)

    def _reclaim(self, final_path: Path) -> None:
        """登记失败后的就地清理：只删自己刚搬过去的终态文件，失败不掩盖原始异常。"""
        with contextlib.suppress(OSError):
            final_path.unlink(missing_ok=True)
            _prune_empty_dirs(self.results_dir)


# ---------------------------------------------------------------------------------- 回收面


def sweep_unreferenced(
    conn: Connection,
    data_dir: Path,
    *,
    now: datetime,
    min_age: int = TMP_STALE_SECONDS,
    dry_run: bool = True,
) -> SweepReport:
    """回收「无 ``artifacts`` 行引用的终态制品」与「超期尝试目录」（design §5 / OPERATIONS.md:22）。

    两条边界保护，缺一就会误删在飞制品：

    - **引用边界**：``artifacts`` 有行者永不删；扫描面**只有** ``results/**`` 与
      ``tmp/jobs/**``，``state``／``raw``／``snapshots``／``exports``／``logs`` 一律不碰
      （OPERATIONS.md:22「只清理超期临时件与没有记录引用的制品」，签认与已发表结果的关联
      证据永不被回收）。
    - **时间／在飞边界**：``st_mtime`` 晚于 ``now - min_age`` 的对象一律保留 —— 未引用的
      新鲜终态文件可能正处在 ``os.replace`` 与 ``INSERT`` 之间的那个窗口里；尝试目录另有一层
      **进程内在飞登记**（``_LIVE_STAGES``）保护，即使 mtime 被人为推到超期也不删。

    ``dry_run=True``（默认）只报告不删除，返回的四个列表可直接进证据；``dry_run=False``
    才真删，并把删不掉的（权限、正被占用）记进 ``failed_removals`` 而不是静默跳过。
    """
    root = Path(data_dir)
    if not root.is_absolute():
        raise ValueError(f"data_dir 必须是绝对路径：{data_dir!r}")
    if min_age < 0:
        raise ValueError(f"min_age 不得为负：{min_age!r}")
    cutoff = ensure_utc(now).timestamp() - min_age
    referenced = {
        str(value) for value in conn.execute(text("SELECT relative_path FROM artifacts")).scalars()
    }
    in_flight = _in_flight_attempt_dirs()

    scanned = 0
    referenced_seen = 0
    symlinks = 0
    removed_files = 0
    unreferenced: list[str] = []
    young_files: list[str] = []
    results_dir = results_root(root)
    if results_dir.is_dir():
        for path in _iter_files(results_dir):
            if path.is_symlink():
                symlinks += 1
                continue
            scanned += 1
            relative = path.relative_to(root).as_posix()
            if relative in referenced:
                referenced_seen += 1
                continue
            if _mtime(path) > cutoff:
                young_files.append(relative)
                continue
            unreferenced.append(relative)
            if dry_run:
                continue
            try:
                _assert_within(root, path).unlink(missing_ok=True)
                removed_files += 1
            except OSError:
                continue
    if not dry_run and removed_files:
        _prune_empty_dirs(results_dir)

    stale_dirs: list[str] = []
    live_dirs: list[str] = []
    young_dirs: list[str] = []
    failures: list[str] = []
    removed_dirs = 0
    tmp_dir = stage_root(root)
    if tmp_dir.is_dir():
        for attempt_dir in sorted(p for p in tmp_dir.glob(_ATTEMPT_DEPTH_GLOB) if p.is_dir()):
            relative = attempt_dir.relative_to(root).as_posix()
            resolved = attempt_dir.resolve()
            if resolved in in_flight:
                live_dirs.append(relative)
                continue
            if _newest_mtime(attempt_dir) > cutoff:
                young_dirs.append(relative)
                continue
            stale_dirs.append(relative)
            if dry_run:
                continue
            try:
                shutil.rmtree(resolved)
                removed_dirs += 1
            except OSError:
                failures.append(relative)
    if not dry_run and removed_dirs:
        _prune_empty_dirs(tmp_dir)

    return SweepReport(
        dry_run=dry_run,
        min_age_seconds=min_age,
        referenced_rows=len(referenced),
        scanned_result_files=scanned,
        referenced_files_seen=referenced_seen,
        unreferenced_files=tuple(unreferenced),
        young_unreferenced_files=tuple(young_files),
        stale_attempt_dirs=tuple(stale_dirs),
        in_flight_attempt_dirs=tuple(live_dirs),
        young_attempt_dirs=tuple(young_dirs),
        skipped_symlinks=symlinks,
        removed_files=removed_files,
        removed_dirs=removed_dirs,
        failed_removals=tuple(failures),
    )
