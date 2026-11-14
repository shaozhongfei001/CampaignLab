"""M0-04/S2c：``worker/service.py:JobService`` + ``JobStore.list_jobs`` 的用例与守护。

分三半，每半都自带正向对照（LANE-COMMON §6：只交绿证据无法区分「守护有效」与「守护恒绿」）：

**A. 符号面**。A169 点名 ``JobService`` 的方法面恰为 ``list_jobs`` / ``get_job`` /
``cancel_job`` / ``retry_job``（禁增减、禁改名），A206 要求构造吃 ``store`` 关键字
（``deps.get_job_service`` 已按 ``factory(store=...)`` 装配），A207 要求 ``service.py``
落地的同一次工作里删掉 ``deps.py`` 那条 ``# type: ignore[import-not-found]``
（strict 开着 ``warn_unused_ignores``，留着会让全表 mypy 判红）。

**B. ``store.py`` 纯追加**。A169：既有 **20** 个 ``def``（含私有）的签名／函数体／SQL 文本
一字不改。判据不是「行数没少」，而是**逐个 def 的源码段 sha256** —— 源码段含 docstring
与函数体，故「改一个字」即判红；期望值由 ``git show HEAD:src/campaignlab/worker/store.py``
机器求得后写死（体例同 ``test_job_repository_terminal.py::FROZEN_JOB_REPOSITORY_SIGNATURES``，
钉的是冻结面，故刻意写死）。另钉 A81 的文本面：``store.py`` 里像 SQL 的字符串常量仍**只有**
``BEGIN IMMEDIATE`` / ``COMMIT`` / ``ROLLBACK`` 三条（``list_jobs`` 一条 SQL 都没写，
取行走 A204 的 ``JobRepository.list_for_workspace``）。

**C. 分层**。红线 3（``worker/__init__.py``）：``service.py`` 不取系统当前时间，``now``
一律由调用方从 ``Clock`` 传入。A169③ 的分层预裁：``service.py`` **零** ``worker -> api``
导入边（``encode_cursor`` / ``decode_cursor`` / ``canonical_json`` 都在 ``api/common.py``，
故 ``list_jobs`` 收发未编码的游标载荷，``str <-> payload`` 两端归 S4）。

关于 C 的口径，**已按 A159 报 U 项**：派单文要求「断言 ``worker/*.py`` 没有任何一条指向
``campaignlab.api`` 的导入边」，但 HEAD 树上这样的边实测有 **6** 条（``deps.py`` /
``states.py`` / ``runner.py`` / ``errors.py`` / ``integrity.py`` / ``store.py``），且
``worker/deps.py`` 的模块 docstring 明写「import ``infra``／``api``／``application`` 都是
正向边，合法」，``infra/db/repositories.py`` 自己也 import ``api.common`` 取 DTO。按
LANE-COMMON §6 末条（判据必须能在**未改动的 HEAD 树**上成立），「零边」是错判据，故
``test_worker_to_api_edges_are_exactly_the_frozen_baseline`` 钉的是**冻结基线集合**：
新增一条即判红（本 lane 的义务面），删掉一条也判红（意味着有人动了 S2c 写集外的文件）。
扫描口径逐字照抄 ``tests/unit/test_layering_edges.py``（含它 docstring 里记的那个坑：
``ImportFrom.level == 0`` 走 ``_resolve_relative`` 会多留一级，把边静默漏掉）。

正向对照一律用 ``tmp_path`` 探针；需要改本体的三条（B 的 def 段、A207 的 ignore、C 的
api 边）用 sha256 双向核验复原，两个摘要与 RED 原文都落在
``evidence/M0/M0-04/positive-control-s2c.log``。
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import json
import re
import sqlite3
import unicodedata
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

import pytest
from sqlalchemy import Engine

from campaignlab import worker as worker_package
from campaignlab.application.workspace_service import BAD_CURSOR_DETAIL, CURSOR_VERSION
from campaignlab.domain.errors import DomainError, RevisionConflict
from campaignlab.infra.db.engine import make_engine
from campaignlab.infra.db.repositories import JobRecord
from campaignlab.worker import deps as worker_deps
from campaignlab.worker.service import JobService
from campaignlab.worker.states import JOB_STATES
from campaignlab.worker.store import JobStore

REPO: Final = Path(__file__).resolve().parents[2]
SRC: Final = REPO / "src" / "campaignlab"
WORKER_DIR: Final = SRC / "worker"
STORE_PY: Final = WORKER_DIR / "store.py"
SERVICE_PY: Final = WORKER_DIR / "service.py"
DEPS_PY: Final = WORKER_DIR / "deps.py"
DDL: Final = REPO / "contracts" / "sqlite-v1.sql"

PY_SUFFIX: Final = ".py"
SOURCE_PREFIX: Final = "src/"
API_PACKAGE: Final = "campaignlab.api"

#: A81 的判定正则（与 ``test_job_repository_terminal.py::JOBS_DML`` 同式）。
JOBS_DML: Final = re.compile(r"INSERT INTO jobs|UPDATE jobs")
#: 「像 SQL」的判定：本仓 ``store.py`` 里合法出现的只有三条事务控制语句。
SQLISH: Final = re.compile(r"\b(BEGIN|COMMIT|ROLLBACK|SELECT|INSERT|UPDATE|DELETE)\b", re.I)
TRANSACTION_CONTROL_ONLY: Final = frozenset({"BEGIN IMMEDIATE", "COMMIT", "ROLLBACK"})
#: 红线 3 的属性式取值名单（``datetime`` 作为**类型注解**是合法的，故不扫裸名字）。
SYSTEM_TIME_ATTRS: Final = frozenset(
    {"now", "utcnow", "today", "time", "monotonic", "perf_counter", "localtime", "gmtime"}
)


# ===========================================================================================
# 共用扫描器（一律走 AST：正则读不出 ``end_lineno`` / ``ImportFrom.level``，也分不清真代码
# 与注释、字符串里的伪代码 —— R13-2 的假红教训）
# ===========================================================================================


def _non_docstring_strings(path: Path) -> list[tuple[int, str]]:
    """文件里所有**非 docstring** 的字符串常量 ``(行号, 值)``，按行号排序。

    排除 docstring 是这几条文本守护能成立的前提：本仓大量 docstring 正在**声明**
    「本模块不含 DML」，裸扫子串会把这些声明判成命中（假红），也会把
    ``test_job_repository_terminal.py`` 里那条 A81 正则自己判红。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc_ids: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if not isinstance(first, ast.Expr):
            continue
        value = first.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            doc_ids.add(id(value))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, str):
            continue
        if id(node) in doc_ids:
            continue
        found.append((node.lineno, node.value))
    return sorted(found)


def _def_segments(text: str) -> dict[str, str]:
    """``{限定名: 该 def 源码段的 sha256[:16]}``；限定名形如 ``JobStore.get_job``。

    源码段 = ``def`` 行到 ``end_lineno``，**逐字节**（含装饰器下方的一切：签名、
    docstring、函数体、SQL 文本）。故 A169 的「签名／函数体／SQL 文本一字不改」三件事
    由一个摘要一次钉死；``ast`` 负责把段边界算准（正则数不出嵌套与续行）。
    """
    tree = ast.parse(text)
    lines = text.splitlines()
    found: dict[str, str] = {}

    def walk(body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                walk(node.body, prefix + node.name + ".")
                continue
            if not isinstance(node, ast.FunctionDef):
                continue
            end = node.end_lineno
            assert end is not None, f"{prefix}{node.name} 缺 end_lineno"
            segment = "\n".join(lines[node.lineno - 1 : end])
            digest = hashlib.sha256(segment.encode("utf-8")).hexdigest()[:16]
            found[prefix + node.name] = digest

    walk(tree.body, "")
    return found


def _module_dotted_name(path: Path, repo_root: Path) -> str:
    """仓库内 ``.py`` 路径 → 点分模块名（解析相对导入的 ``level`` 要靠它定位本包）。"""
    relative = path.relative_to(repo_root).as_posix()
    if relative.startswith(SOURCE_PREFIX):
        relative = relative[len(SOURCE_PREFIX) :]
    if relative.endswith(PY_SUFFIX):
        relative = relative[: -len(PY_SUFFIX)]
    parts = relative.split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _package_of(dotted: str, path: Path) -> str:
    """模块所属包：``__init__.py`` 的包即其自身，普通模块的包是其父路径。"""
    if path.name == "__init__.py":
        return dotted
    return dotted.rpartition(".")[0]


def _resolve_relative(level: int, module: str | None, package: str) -> str:
    """``from ..api.common import X`` → 绝对点分路径。``level=1`` 指本包，故裁 ``level - 1`` 级。

    裁穿顶层（``keep < 0``）在 CPython 里就是 ``ImportError``，即该文件根本导入不起来。
    本守护**不静默跳过**这种写法，而是显式抛错让它判红：静默跳过等于给「用畸形相对导入
    绕过守护」留口子（口径照抄 ``test_layering_edges.py``）。
    """
    if level < 1:
        msg = f"_resolve_relative 只接受 level >= 1（绝对导入直接取 module）：level={level}"
        raise ValueError(msg)
    parts = package.split(".") if package else []
    keep = len(parts) - (level - 1)
    if keep < 0:
        msg = f"相对导入越过顶层包：level={level} package={package!r} module={module!r}"
        raise ValueError(msg)
    prefix = ".".join(parts[:keep])
    if module is None:
        return prefix
    return f"{prefix}.{module}" if prefix else module


def _is_api(dotted: str) -> bool:
    """是否落在 ``campaignlab.api`` 包里（含父包自身）。"""
    return dotted == API_PACKAGE or dotted.startswith(API_PACKAGE + ".")


def _import_from_target(node: ast.ImportFrom, package: str) -> str:
    """``ImportFrom`` 节点**被执行**的模块：``level == 0`` 即绝对导入，直接取 ``module``。

    绝对导入不能走 ``_resolve_relative``：那里 ``keep = len(parts) - (level - 1)`` 在
    ``level == 0`` 时会多留一级，把 ``campaignlab.api.common`` 拼成
    ``campaignlab.worker.campaignlab.api.common``，边就被静默漏掉（``test_layering_edges.py``
    docstring 记的同一个坑）。
    """
    if node.level:
        return _resolve_relative(node.level, node.module, package)
    return node.module or ""


def collect_worker_to_api_edges(scan_root: Path, *, repo_root: Path) -> set[tuple[str, str]]:
    """``worker/*.py`` 的 ``-> api`` 导入边集合：``(仓库相对路径, 被执行的 api 点分路径)``。

    ``from X import Y`` 只记 ``X``：无论 ``Y`` 是不是子模块，``X`` 都已被执行。
    ``repo_root`` 让正向对照能把 ``tmp_path`` 探针树当成仓库根来扫（探针布局与工作树同形，
    故相对导入同样可解析）。
    """
    found: set[tuple[str, str]] = set()
    for path in sorted(scan_root.rglob("*" + PY_SUFFIX)):
        if "__pycache__" in path.parts:
            continue
        dotted = _module_dotted_name(path, repo_root)
        package = _package_of(dotted, path)
        key = path.relative_to(repo_root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                targets = [_import_from_target(node, package)]
            for target in targets:
                if _is_api(target):
                    found.add((key, target))
    return found


def _system_time_reads(path: Path) -> list[tuple[int, str]]:
    """``path`` 里所有**属性式**取系统当前时间的调用 ``(行号, 原文)``。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in SYSTEM_TIME_ATTRS:
            found.append((node.lineno, ast.unparse(node)))
    return sorted(found)


# ===========================================================================================
# A. 符号面（A169 禁增减禁改名 / A206 store= / A207 删 ignore）
# ===========================================================================================

FROZEN_METHOD_FACE: Final = frozenset({"cancel_job", "get_job", "list_jobs", "retry_job"})


def test_job_service_method_face_is_exactly_the_four_a169_named() -> None:
    """A169：方法面**恰为**四个，禁增减、禁改名（多一个也算越界）。"""
    measured = {name for name, _ in inspect.getmembers(JobService, callable) if name[:1] != "_"}
    assert measured == set(FROZEN_METHOD_FACE), (
        f"JobService 公有方法面漂移（A169 禁增减禁改名）：实测 {sorted(measured)}"
    )


def test_job_service_constructor_takes_keyword_only_store() -> None:
    """A206：构造必须吃 ``store`` **关键字**参数，且无默认值。

    ``worker/deps.py::get_job_service`` 按 ``factory(store=get_job_store(config))`` 装配，
    名字改一个字母装配当场 ``TypeError``；给了默认值则等于允许「没接库也能构造」，
    那正是 A169 要避免的静默替身。
    """
    signature = inspect.signature(JobService.__init__)
    params = list(signature.parameters.values())
    assert [item.name for item in params] == ["self", "store"], (
        f"__init__ 形参面漂移（A206 要求 store=）：实测 {[item.name for item in params]}"
    )
    store_param = params[1]
    assert store_param.kind is inspect.Parameter.KEYWORD_ONLY, "store 必须是 keyword-only"
    assert store_param.default is inspect.Parameter.empty, "store 不得有默认值"
    assert store_param.annotation == "JobStore", f"store 注解漂移：{store_param.annotation!r}"


def test_job_service_is_not_reexported_from_the_worker_package() -> None:
    """R13 §3：``worker/__init__.py`` 的 ``__all__`` 禁加 ``JobService``（公共冻结面）。

    下游按 ``campaignlab.worker.service.JobService`` 直接取；再导出会让「导入 worker 包」
    顺带拉起 ``application.workspace_service``（游标常量的来源模块）。
    """
    assert "JobService" not in worker_package.__all__, "禁把 JobService 加进 worker.__all__"
    assert not hasattr(worker_package, "JobService"), "禁在 worker/__init__.py 里绑定 JobService"


def test_deps_provider_resolves_the_real_class_by_its_own_constants() -> None:
    """A169 端到端：``deps.py`` 自己那两个常量指的模块／类名，取到的就是本文件的 ``JobService``。

    这条把「延迟 import 的拼写」与「真实交付物」钉在一起：S2c 若把模块或类改名，
    ``deps.get_job_service`` 会在运行期抛 ``RuntimeError``，而本用例会先判红。
    """
    assert worker_deps._SERVICE_MODULE == "campaignlab.worker.service"
    assert worker_deps._SERVICE_CLASS == "JobService"
    module = importlib.import_module(worker_deps._SERVICE_MODULE)
    assert getattr(module, worker_deps._SERVICE_CLASS) is JobService


def test_deps_no_longer_carries_the_import_not_found_ignore() -> None:
    """A207：``service.py`` 落地的同一次工作里必须删掉 ``deps.py`` 那条 ignore 注释。

    strict 开着 ``warn_unused_ignores``：模块已存在还留着 ``import-not-found`` 的豁免 →
    ``error: Unused "type: ignore" comment`` → **全表** mypy 判红。

    判据走 AST 定位那条 ``TYPE_CHECKING`` 导入的**行号**、再看该行行尾有没有注释 ——
    直接对全文搜 ``type: ignore`` 会把 ``deps.py`` docstring 里那句「必须**同步删掉**
    下面那条 …」的**声明文本**判成命中（R13-2 的假红形态，本 lane 第 1 轮实测踩过）。
    """
    source = DEPS_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    hits = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "campaignlab.worker.service"
    ]
    assert len(hits) == 1, f"deps.py 对 worker.service 的导入应恰有 1 处，实测 {len(hits)}"
    line = source.splitlines()[hits[0].lineno - 1]
    assert line.strip() == "from campaignlab.worker.service import JobService", (
        f"A207：注解用的 TYPE_CHECKING 导入必须原样留着且行尾无注释：{line!r}"
    )
    assert "#" not in line, f"A207：该行行尾不得再挂任何注释（含 type: ignore）：{line!r}"


# ===========================================================================================
# B. ``store.py`` 纯追加（A169）+ A81 的文本面
# ===========================================================================================

#: 由 ``git show HEAD:src/campaignlab/worker/store.py`` 机器求得（命令与输出见
#: ``evidence/M0/M0-04/commands-s2c.md``）。**刻意写死**：钉的是冻结面，体例同
#: ``test_job_repository_terminal.py::FROZEN_JOB_REPOSITORY_SIGNATURES``。禁手改 ——
#: 改一个字节都会让下面那条用例判红。
FROZEN_STORE_DEFS: Final[dict[str, str]] = {
    "Claim.claimed": "defcbd09f343844a",
    "JobStore.__init__": "14281266a2a0106f",
    "JobStore.claim_next": "0adb772484258426",
    "JobStore.confirm_cancel": "cee0d361d66d79b0",
    "JobStore.enqueue": "f9007ffa28222357",
    "JobStore.fail": "aee7052d7ef4f251",
    "JobStore.fail_unhandled": "0da07330d2cc3898",
    "JobStore.get_job": "fa0b29ad03df31bc",
    "JobStore.pending_count": "814713931cf98517",
    "JobStore.reap_expired": "789c2731db19374c",
    "JobStore.renew": "cf812ffe294434cb",
    "JobStore.request_cancel": "22c984b1def072c8",
    "JobStore.retry": "01245b514f98de9c",
    "JobStore.succeed": "b655697936d169fa",
    "Reaped.total": "e863c5b3c8c9bdd0",
    "RenewResult.cancel_requested": "934b7db59db90407",
    "_is_lock_contention": "71cdc65893fe0c41",
    "connect_autocommit": "06094b0b13df8f7c",
    "immediate": "d57a258c8df3bab9",
    "short_transaction": "dc879819637b0014",
}


def test_store_py_frozen_defs_are_byte_identical() -> None:
    """A169：``store.py`` 既有 **20** 个 ``def``（含私有）的源码段逐字节未变。

    源码段含签名、docstring、函数体与 SQL 文本，故「一字不改」由 sha256 一次钉死。
    末尾那条「只准多出一个 def」是纯追加的另一半：S2c 的交付物就是 ``JobStore.list_jobs``，
    多出第二个 def 即意味着动了冻结面。
    """
    measured = _def_segments(STORE_PY.read_text(encoding="utf-8"))
    assert len(FROZEN_STORE_DEFS) == 20, (
        f"冻结基线表必须是 20 个 def（R15-1 实测值），实测表长 {len(FROZEN_STORE_DEFS)}"
    )
    missing = sorted(set(FROZEN_STORE_DEFS) - set(measured))
    assert missing == [], f"既有 def 被删或被改名（纯追加不允许）：{missing}"
    drifted = sorted(key for key in FROZEN_STORE_DEFS if measured[key] != FROZEN_STORE_DEFS[key])
    assert drifted == [], f"既有 def 的签名／函数体／SQL 文本被改动：{drifted}"
    assert "JobStore.list_jobs" in measured, "S2c 的交付物 JobStore.list_jobs 不在 store.py 里"
    assert len(measured) == len(FROZEN_STORE_DEFS) + 1, (
        f"store.py 只准比基线多出 list_jobs 一个 def：实测 {len(measured)} 个"
    )


def test_store_py_sql_text_is_still_only_the_three_transaction_control_statements() -> None:
    """红线 1 的文本面：``store.py`` 里像 SQL 的字符串常量仍**只有**那三条事务控制语句。

    判据是**集合相等**而不是「不含 SELECT」的裸否定：后者在扫描器扫空时同样为真（假绿）。
    ``list_jobs`` 刻意一条 SQL 都不写（取行走 A204 的 ``JobRepository.list_for_workspace``），
    故 ``immediate()`` 上方那句「只此三条是本模块出现的全部 SQL 文本」在 S2c 之后仍为真。
    """
    measured = {value for _, value in _non_docstring_strings(STORE_PY) if SQLISH.search(value)}
    assert measured == set(TRANSACTION_CONTROL_ONLY), (
        f"store.py 的 SQL 文本面漂移（S2c 必须零新增 SQL）：{sorted(measured)}"
    )


def test_store_and_service_carry_no_jobs_dml_text() -> None:
    """A81 的本地一面：两个文件里**非 docstring** 的字符串常量都不含 jobs 表 DML。

    全仓守护在 ``test_job_repository_terminal.py``（文件集合恒等于 ``{repositories.py}``）；
    本条是同一判据在本 lane 写集上的定点复算，口径按 R13-2 扫 AST 常量而非裸子串。
    """
    hits = [
        (path.name, lineno, value)
        for path in (STORE_PY, SERVICE_PY)
        for lineno, value in _non_docstring_strings(path)
        if JOBS_DML.search(value)
    ]
    assert hits == [], f"worker 包内出现 jobs 表 DML 文本（A81：SQL 写点唯一）：{hits}"


def test_service_module_def_face_is_exactly_the_delivered_one() -> None:
    """A169①／④：``service.py`` 里定义的函数**恰为**交付的那 8 个，一个转换器都没有。

    ``job_from_row`` 是 ``JobRecord -> api.common.Job`` 的唯一一份实现（住在
    ``infra/db/repositories.py``），调用点归 S4。本层既不复制第二份、也不提前调用 ——
    多出一个 ``_to_job`` 之类的辅助函数即判红，这正是「禁复制第二份实现」的机器牙。
    """
    expected = {
        "JobService.__init__",
        "JobService.cancel_job",
        "JobService.get_job",
        "JobService.list_jobs",
        "JobService.retry_job",
        "_cursor_key",
        "_next_cursor_payload",
        "_parse_status",
    }
    measured = set(_def_segments(SERVICE_PY.read_text(encoding="utf-8")))
    assert measured == expected, (
        f"service.py 的 def 面漂移：多出 {sorted(measured - expected)}、"
        f"少了 {sorted(expected - measured)}"
    )
    imported = [
        alias.name
        for node in ast.walk(ast.parse(SERVICE_PY.read_text(encoding="utf-8")))
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    ]
    assert "job_from_row" not in imported, "A169①：行→DTO 的调用点归 S4，本层不得 import"


# ===========================================================================================
# C. 分层：红线 3（显式时钟）+ A169③ 的 worker -> api 禁令
# ===========================================================================================


def test_service_module_never_reads_the_system_clock() -> None:
    """红线 3：``service.py`` 里没有任何取系统当前时间的调用，也不 import ``time``。

    扫 AST 属性节点而不是扫裸子串：``datetime`` 作为**类型注解**（``now: datetime``）是
    合法的，裸子串会把它一起判红（假红方向）；``datetime.now`` / ``datetime.utcnow`` /
    ``date.today`` / ``time.time`` 这些**属性式取值**才是红线。
    """
    hits = _system_time_reads(SERVICE_PY)
    assert hits == [], f"service.py 取了系统当前时间（红线 3）：{hits}"
    tree = ast.parse(SERVICE_PY.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    assert "time" not in imported, "service.py 不得 import time（红线 3）"


def test_mutating_service_methods_take_now_as_a_required_keyword() -> None:
    """红线 3 的正面一面：两个写方法的 ``now`` 是**必填关键字**参数，没有默认值。

    给了默认值（例如 ``now: datetime | None = None`` 再在函数体里兜底取当前时间）
    就等于给「本层自取系统时间」开了口子，故默认值本身即判红。
    """
    for name in ("cancel_job", "retry_job"):
        params = inspect.signature(getattr(JobService, name)).parameters
        assert "now" in params, f"{name} 缺 now 参数（红线 3）"
        param = params["now"]
        assert param.kind is inspect.Parameter.KEYWORD_ONLY, f"{name} 的 now 必须是 keyword-only"
        assert param.default is inspect.Parameter.empty, f"{name} 的 now 不得有默认值"
        assert param.annotation == "datetime", f"{name} 的 now 注解漂移：{param.annotation!r}"


#: HEAD 树上实测的 6 条 ``worker -> api`` 导入边（AST 口径，命令见 commands-s2c.md）。
#: **本 lane 禁改这个基线**：新增一条 = 违反 A169③ 的分层预裁；少一条 = 有人动了 S2c
#: 写集外的文件。要收紧或放宽都由编排器裁定（已报 U 项）。
FROZEN_WORKER_TO_API_EDGES: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("src/campaignlab/worker/deps.py", "campaignlab.api.deps"),
        ("src/campaignlab/worker/errors.py", "campaignlab.api.common"),
        ("src/campaignlab/worker/integrity.py", "campaignlab.api.common"),
        ("src/campaignlab/worker/runner.py", "campaignlab.api.common"),
        ("src/campaignlab/worker/states.py", "campaignlab.api.common"),
        ("src/campaignlab/worker/store.py", "campaignlab.api.common"),
    }
)

PROBE_KEY: Final = "src/campaignlab/worker/probe.py"


def test_worker_to_api_edges_are_exactly_the_frozen_baseline() -> None:
    """``worker/*.py`` 的 ``-> api`` 导入边集合 == 冻结基线（6 条，实测于 HEAD）。"""
    measured = collect_worker_to_api_edges(WORKER_DIR, repo_root=REPO)
    baseline = set(FROZEN_WORKER_TO_API_EDGES)
    assert len(FROZEN_WORKER_TO_API_EDGES) == 6, "基线表被截断（HEAD 实测 6 条）"
    assert measured == baseline, (
        f"worker -> api 导入边集合漂移：多出 {sorted(measured - baseline)}、"
        f"少了 {sorted(baseline - measured)}"
    )


def test_service_py_contributes_no_worker_to_api_edge() -> None:
    """本 lane 的硬约束：``service.py`` 自己**零** ``-> api`` 边（A169③ 的分层预裁）。"""
    measured = {
        target
        for key, target in collect_worker_to_api_edges(WORKER_DIR, repo_root=REPO)
        if key == SOURCE_PREFIX + "campaignlab/worker/service.py"
    }
    assert measured == set(), f"service.py 不得 import campaignlab.api：{sorted(measured)}"


def _probe_worker_tree(tmp_path: Path, source: str) -> Path:
    """在 ``tmp_path`` 里造一棵与工作树同形的探针树（**禁落工作树**，LANE-COMMON §6）。"""
    worker_dir = tmp_path / "src" / "campaignlab" / "worker"
    worker_dir.mkdir(parents=True)
    (worker_dir / "probe.py").write_text(source, encoding="utf-8")
    return tmp_path


def test_submodule_style_api_import_would_be_flagged(tmp_path: Path) -> None:
    """正向对照①：子模块式 ``from campaignlab.api.common import ...`` → 检出、基线不覆盖。"""
    repo_root = _probe_worker_tree(tmp_path, "from campaignlab.api.common import canonical_json\n")
    measured = collect_worker_to_api_edges(
        repo_root / "src" / "campaignlab" / "worker", repo_root=repo_root
    )
    assert measured == {(PROBE_KEY, "campaignlab.api.common")}, f"实测 {sorted(measured)}"
    assert not measured <= FROZEN_WORKER_TO_API_EDGES, "新增的子模块式 api 边不得被基线放过"


def test_parent_package_style_api_import_would_be_flagged(tmp_path: Path) -> None:
    """正向对照②：父包属性式 ``from campaignlab.api import ...`` → 记成父包这条边。"""
    repo_root = _probe_worker_tree(tmp_path, "from campaignlab.api import common\n")
    measured = collect_worker_to_api_edges(
        repo_root / "src" / "campaignlab" / "worker", repo_root=repo_root
    )
    assert measured == {(PROBE_KEY, API_PACKAGE)}, f"实测 {sorted(measured)}"
    assert not measured <= FROZEN_WORKER_TO_API_EDGES


def test_plain_import_of_api_would_be_flagged(tmp_path: Path) -> None:
    """正向对照③：``import campaignlab.api.jobs`` 这种不带 from 的形态同样检出。"""
    repo_root = _probe_worker_tree(tmp_path, "import campaignlab.api.jobs\n")
    measured = collect_worker_to_api_edges(
        repo_root / "src" / "campaignlab" / "worker", repo_root=repo_root
    )
    assert measured == {(PROBE_KEY, "campaignlab.api.jobs")}, f"实测 {sorted(measured)}"
    assert not measured <= FROZEN_WORKER_TO_API_EDGES


def test_relative_import_cannot_evade_the_api_guard(tmp_path: Path) -> None:
    """正向对照④：相对导入 ``from ..api.common import ...`` 被解析成绝对路径后检出。"""
    repo_root = _probe_worker_tree(tmp_path, "from ..api.common import encode_cursor\n")
    measured = collect_worker_to_api_edges(
        repo_root / "src" / "campaignlab" / "worker", repo_root=repo_root
    )
    assert measured == {(PROBE_KEY, "campaignlab.api.common")}, f"实测 {sorted(measured)}"
    assert not measured <= FROZEN_WORKER_TO_API_EDGES


CLEAN_PROBE: Final = (
    "# from campaignlab.api.common import canonical_json  ← 注释里的伪导入\n"
    'NOT_AN_IMPORT = "import campaignlab.api.jobs"\n'
    "from campaignlab.domain.errors import DomainError\n"
    "from campaignlab.infra.db import repositories\n"
)


def test_api_edge_scanner_reads_the_ast_not_the_source_text(tmp_path: Path) -> None:
    """正向对照⑤（反假绿）：注释与字符串里的伪导入不算边，且扫描器**能**返回空集。

    与前四条合起来破掉两种假绿：「恒返回全集」被本条判红，「恒返回空集」被前四条判红。
    """
    repo_root = _probe_worker_tree(tmp_path, CLEAN_PROBE)
    measured = collect_worker_to_api_edges(
        repo_root / "src" / "campaignlab" / "worker", repo_root=repo_root
    )
    assert measured == set(), f"扫描器把注释/字符串当成了导入边：{sorted(measured)}"


def test_api_edge_scanner_is_not_fooled_by_a_type_checking_block(tmp_path: Path) -> None:
    """正向对照⑥：藏在 ``if TYPE_CHECKING:`` 里的 api 导入**照样**算边。

    ``TYPE_CHECKING`` 只影响运行期，mypy 与 ruff 都看得见它；把它当豁免口子就会让
    「注解里偷偷引 api」这种回退静默通过。
    """
    source = (
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from campaignlab.api.common import Job\n"
    )
    repo_root = _probe_worker_tree(tmp_path, source)
    measured = collect_worker_to_api_edges(
        repo_root / "src" / "campaignlab" / "worker", repo_root=repo_root
    )
    assert measured == {(PROBE_KEY, "campaignlab.api.common")}, f"实测 {sorted(measured)}"


# ===========================================================================================
# D. 行为面：list_jobs 的排序／键集翻页／筛选／游标绑定，与另三个方法的转发
# ===========================================================================================

T0: Final = datetime(2026, 11, 14, 1, 0, 0, tzinfo=UTC)
WS: Final = "ws-1"
OTHER_WS: Final = "ws-2"
DIGEST: Final = "0" * 64
ACTOR: Final = "op-1"
OTHER_ACTOR: Final = "op-2"
REQUEST: Final = "req-1"
QDIGEST: Final = "a1b2c3d4e5f60718"


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    """按活契约 DDL 建临时库（只读引用 ``contracts/**``，不改一字节）。"""
    assert DDL.is_file(), f"活契约 DDL 读不到：{DDL}"
    db = tmp_path / "campaignlab.db"
    raw = sqlite3.connect(db)
    try:
        raw.executescript(DDL.read_text(encoding="utf-8"))
        raw.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        raw.execute("INSERT INTO alembic_version (version_num) VALUES ('0001_initial_schema')")
        for workspace_id in (WS, OTHER_WS):
            raw.execute(
                "INSERT INTO workspaces (id,name,source_class,revision,created_at) "
                "VALUES (?,?,?,?,?)",
                (workspace_id, f"合成工作区 {workspace_id}", "SYNTHETIC", 1, T0.isoformat()),
            )
        raw.commit()
    finally:
        raw.close()
    return make_engine(f"sqlite:///{db}")


@pytest.fixture
def store(engine: Engine) -> JobStore:
    return JobStore(engine=engine)


@pytest.fixture
def service(store: JobStore) -> JobService:
    """A206 的装配口径：``JobService(store=...)``，与 ``deps.get_job_service`` 同一形态。"""
    return JobService(store=store)


def _enqueue(
    store: JobStore,
    job_id: str,
    *,
    now: datetime,
    kind: str = "COMPARE",
    workspace_id: str = WS,
) -> JobRecord:
    return store.enqueue(
        workspace_id=workspace_id,
        kind=kind,
        input_json=json.dumps({"snapshot": "S-1"}, ensure_ascii=False),
        input_digest=DIGEST,
        now=now,
        job_id=job_id,
    )


def _seed(store: JobStore, count: int, *, kind: str = "COMPARE") -> list[JobRecord]:
    """按 ``created_at`` 递增播 ``count`` 条 QUEUED 作业（每条差 1 分钟，故键集无并列）。"""
    return [
        _enqueue(store, f"J-{index:02d}", now=T0 + timedelta(minutes=index), kind=kind)
        for index in range(count)
    ]


def _signature_text(function: Any) -> str:
    """``inspect.signature`` 原文，去掉开头的 ``self, `` 以便跨类逐字比对。"""
    return str(inspect.signature(function)).replace("(self, ", "(", 1)


def _call_list(
    service: JobService,
    *,
    limit: int = 25,
    cursor_payload: Mapping[str, Any] | None = None,
    q: str | None = None,
    status: str | None = None,
    actor_id: str = ACTOR,
    query_digest: str = QDIGEST,
    workspace_id: str = WS,
) -> tuple[list[JobRecord], dict[str, Any] | None]:
    return service.list_jobs(
        workspace_id=workspace_id,
        actor_id=actor_id,
        query_digest=query_digest,
        limit=limit,
        cursor_payload=cursor_payload,
        q=q,
        status=status,
    )


def test_list_jobs_returns_an_empty_page_when_there_is_nothing_to_list(
    service: JobService,
) -> None:
    """design §1：无结果 → ``items=[]``、``next_cursor=null``（本层即 ``([], None)``）。"""
    assert _call_list(service) == ([], None)


def test_list_jobs_orders_created_at_desc_then_id_asc(store: JobStore, service: JobService) -> None:
    """design §1 的固定排序：``created_at DESC, id ASC``（禁依赖 SQL 的自然返回序）。"""
    _seed(store, 4)
    items, _ = _call_list(service)
    assert [record.id for record in items] == ["J-03", "J-02", "J-01", "J-00"]


def test_list_jobs_ties_on_created_at_fall_back_to_id_asc(
    store: JobStore, service: JobService
) -> None:
    """同一 ``created_at`` 的多行按 ``id`` 升序 —— 键集翻页不漏行的前提。"""
    for index in range(3):
        _enqueue(store, f"J-T{index}", now=T0)
    items, _ = _call_list(service)
    assert [record.id for record in items] == ["J-T0", "J-T1", "J-T2"]


def test_list_jobs_first_page_yields_limit_items_and_an_unencoded_payload(
    store: JobStore, service: JobService
) -> None:
    """每页取 ``limit + 1`` 行判 ``next_cursor``；本层交出的是**未编码**载荷（A169③）。"""
    _seed(store, 3)
    items, payload = _call_list(service, limit=2)
    assert [record.id for record in items] == ["J-02", "J-01"]
    assert payload == {
        "v": CURSOR_VERSION,
        "q": QDIGEST,
        "k": [items[-1].created_at, "J-01"],
        "s": ACTOR,
    }, f"载荷四键必须与 design §1 逐字同形，实测 {payload}"
    assert list(payload or {}) == ["v", "q", "k", "s"], "键序也照抄 design §1"


def test_list_jobs_second_page_consumes_the_keyset_and_exhausts(
    store: JobStore, service: JobService
) -> None:
    """把上一页的载荷原样传回来 → 拿到剩下的行，且末页 ``next_cursor`` 为 ``None``。"""
    _seed(store, 3)
    first, payload = _call_list(service, limit=2)
    assert payload is not None
    second, tail = _call_list(service, limit=2, cursor_payload=payload)
    assert [record.id for record in second] == ["J-00"]
    assert tail is None
    assert [record.id for record in first + second] == ["J-02", "J-01", "J-00"]


def test_list_jobs_full_walk_visits_every_row_exactly_once(
    store: JobStore, service: JobService
) -> None:
    """``limit=1`` 走完全部页：无重复、无遗漏、顺序与首页一次性取全时完全一致。"""
    seeded = _seed(store, 5)
    walked: list[JobRecord] = []
    payload: Mapping[str, Any] | None = None
    for _ in range(len(seeded) + 2):
        items, payload = _call_list(service, limit=1, cursor_payload=payload)
        walked.extend(items)
        if payload is None:
            break
    assert [record.id for record in walked] == [
        record.id for record in _call_list(service, limit=25)[0]
    ]
    assert len(walked) == len(seeded)


def test_list_jobs_filters_by_comma_separated_status(store: JobStore, service: JobService) -> None:
    """``status`` 是逗号分隔多值（design §1）：6 态名全连恰 58 字符 ≤ 契约的 60。"""
    seeded = _seed(store, 2)
    cancelled = service.cancel_job(
        workspace_id=WS,
        job_id=seeded[0].id,
        revision=seeded[0].revision,
        now=T0,
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    assert cancelled.state == "CANCELLED"
    queued_only, _ = _call_list(service, status="QUEUED")
    assert [record.id for record in queued_only] == [seeded[1].id]
    both, _ = _call_list(service, status="QUEUED,CANCELLED")
    assert {record.id for record in both} == {seeded[0].id, seeded[1].id}
    all_six, _ = _call_list(service, status=",".join(sorted(JOB_STATES)))
    assert len(all_six) == 2
    assert len(",".join(JOB_STATES)) == 58, "design §1 的 N7①：6 态名全连恰 58 字符"


@pytest.mark.parametrize("status", ["NOPE", "QUEUED,", ",QUEUED", "", "queued", "QUEUED,NOPE"])
def test_list_jobs_rejects_an_unregistered_status_segment(service: JobService, status: str) -> None:
    """未知／空态名 → 422 ``VALIDATION_ERROR``。

    判据取自 design §6 的 listJobs 行原文：「422 ``VALIDATION_ERROR`` ``limit`` 越界、
    ``q``/``status`` 超长、``status`` 含未知态名」，且 ``_STATUS_BY_CODE`` 里
    ``VALIDATION_ERROR`` 就是 422（不是 400）。静默忽略未知态名会让「筛了一个不存在的
    状态」返回空页，看起来像库里真没数据，故必须显式判错；大小写也不放宽
    （``queued`` 不是注册态名，与 ``q`` 的 casefold 子串匹配是两回事）。
    """
    with pytest.raises(DomainError) as caught:
        _call_list(service, status=status)
    assert caught.value.code == "VALIDATION_ERROR"
    assert caught.value.status == 422


def test_list_jobs_q_matches_id_kind_and_stage_with_nfkc_casefold(
    store: JobStore, service: JobService
) -> None:
    """``q`` 对 ``id`` / ``kind`` / ``stage`` 做 NFKC + casefold 子串匹配（design §1）。"""
    _enqueue(store, "J-Alpha-9", now=T0, kind="COMPARE")
    _enqueue(store, "J-Beta-9", now=T0 + timedelta(minutes=1), kind="REPORT")
    by_id, _ = _call_list(service, q="ALPHA")
    assert [record.id for record in by_id] == ["J-Alpha-9"]
    by_kind, _ = _call_list(service, q="report")
    assert [record.id for record in by_kind] == ["J-Beta-9"]
    # 全角 ＣＯＭＰ 经 NFKC 归一后命中 kind="COMPARE"；这条是折叠口径的正面自证。
    by_nfkc, _ = _call_list(service, q="\uff23\uff2f\uff2d\uff30")
    assert [record.id for record in by_nfkc] == ["J-Alpha-9"]
    # stage 也是被匹配的三列之一：QUEUED 既不在 id 里也不在 kind 里。
    by_stage, _ = _call_list(service, q="queued")
    assert {record.id for record in by_stage} == {"J-Alpha-9", "J-Beta-9"}


def test_list_jobs_q_returns_an_empty_page_when_nothing_matches(
    store: JobStore, service: JobService
) -> None:
    _seed(store, 2)
    assert _call_list(service, q="zzz-no-such-needle") == ([], None)


def test_list_jobs_q_folding_matches_the_repository_single_source() -> None:
    """折叠口径与 ``repositories._fold`` **等价**：本模块刻意不复制第二个公共折叠函数。

    A169① 的精神是「禁第二份实现」。``repositories.py`` 的 append-only 豁免不给 S2c，
    故 ``JobStore.list_jobs`` 就地写 NFKC + casefold；本条把它与那一份私有实现逐探针
    对齐（含全角、合字、德语 sharp s、带变音符的组合序列），漂移即判红。
    """
    from campaignlab.infra.db import repositories

    probes = [
        "COMPARE",
        "ｃｏｍｐａｒｅ",
        "\uff23\uff2f\uff2d\uff30",
        "stra\u00dfe",
        "STRASSE",
        "e\u0301clair",
        "\u00e9clair",
        "\ufb01le",
        "J-Alpha_9",
        "\u0130stanbul",
    ]
    for probe in probes:
        mine = unicodedata.normalize("NFKC", probe).casefold()
        assert mine == repositories._fold(probe), f"折叠口径漂移：{probe!r}"


def test_list_jobs_rejects_limit_below_one(service: JobService) -> None:
    """``limit < 1`` → 422 ``VALIDATION_ERROR``（与 ``WorkspaceService.list_workspaces`` 同判据）。

    上界（``limit <= 100``）由 design §1 冻结的 ``Query(25, ge=1, le=100)`` 在 api 层挡住，
    本层刻意**不**再设第二个上界常量：那会开出第二套口径（D-014），且 A169 只点名了
    四个方法，禁增符号。
    """
    with pytest.raises(DomainError) as caught:
        _call_list(service, limit=0)
    assert caught.value.code == "VALIDATION_ERROR"
    assert caught.value.status == 422


def test_list_jobs_never_mixes_in_rows_from_another_workspace(
    store: JobStore, service: JobService
) -> None:
    """主键含 ``workspace_id``：外工作区的行自然读不到（OPERATIONS.md:7）。"""
    _seed(store, 2)
    _enqueue(store, "J-Report", now=T0 + timedelta(minutes=9), kind="REPORT")
    _enqueue(store, "J-Other", now=T0, workspace_id=OTHER_WS)
    mine, _ = _call_list(service)
    assert sorted(record.id for record in mine) == ["J-00", "J-01", "J-Report"]
    assert "J-Other" not in [record.id for record in mine]
    theirs, _ = _call_list(service, workspace_id=OTHER_WS)
    assert [record.id for record in theirs] == ["J-Other"]


def test_list_jobs_rejects_a_payload_whose_binding_does_not_match(
    store: JobStore, service: JobService
) -> None:
    """版本／查询摘要／actor／``k`` 形状任一不符 → 400 ``BAD_CURSOR``，且**同一句 detail**。

    detail 必须完全相同：游标是不可信外部输入，措辞差异会变成探测其结构的 oracle。
    换 actor 也判 400 而不是 403，理由同上。
    """
    _seed(store, 3)
    good: dict[str, Any] = {"v": CURSOR_VERSION, "q": QDIGEST, "k": ["x", "y"], "s": ACTOR}
    broken: list[dict[str, Any]] = [
        {**good, "v": CURSOR_VERSION + 1},
        {**good, "q": "0" * 16},
        {**good, "s": OTHER_ACTOR},
        {**good, "k": ["only-one"]},
        {**good, "k": "not-a-list"},
        {**good, "k": ["2026-11-14T01:00:00+00:00", 7]},
        {"v": CURSOR_VERSION, "q": QDIGEST, "s": ACTOR},
    ]
    details: set[str] = set()
    for payload in broken:
        with pytest.raises(DomainError) as caught:
            _call_list(service, limit=2, cursor_payload=payload)
        assert caught.value.code == "BAD_CURSOR", f"{payload} 没被判成 BAD_CURSOR"
        assert caught.value.status == 400
        details.add(caught.value.detail)
    assert details == {BAD_CURSOR_DETAIL}, f"七种失败必须收敛成同一句 detail：{sorted(details)}"


def test_list_jobs_returns_records_not_an_http_page_shell(
    store: JobStore, service: JobService
) -> None:
    """A169④／A91：本层只交 ``JobRecord`` 序列 + 游标载荷，**不组装** ``JobPage``。

    ``JobPage`` 归 M0-04/S4 在 ``api/common.py`` append-only 追加。故判据是 AST 级的
    「``service.py`` 里不出现 ``JobPage`` 这个名字」，而不是「``api.common`` 现在还没有
    它」—— 后者会在 S4 落地后变成一条假红。
    """
    _seed(store, 2)
    result = _call_list(service)
    assert isinstance(result, tuple) and len(result) == 2
    items, payload = result
    assert all(isinstance(record, JobRecord) for record in items)
    assert payload is None or isinstance(payload, dict)
    names = {
        node.id
        for node in ast.walk(ast.parse(SERVICE_PY.read_text(encoding="utf-8")))
        if isinstance(node, ast.Name)
    }
    assert "JobPage" not in names, "A91：JobPage 归 S4，S2c 禁抢先落地"
    attrs = {
        node.attr
        for node in ast.walk(ast.parse(SERVICE_PY.read_text(encoding="utf-8")))
        if isinstance(node, ast.Attribute)
    }
    assert "JobPage" not in attrs


def test_the_unencoded_payload_round_trips_through_the_frozen_codec(
    store: JobStore, service: JobService
) -> None:
    """A169③ 的落地自证：本层交出的载荷，S4 用冻结的 ``encode_cursor``/``decode_cursor``
    一把就能编解码，且查询摘要正是 design §1 那一条公式。

    本用例**是测试**，故可以 import ``api.common``；``worker/service.py`` 不可以 ——
    这个不对称正是 A169③ 分层预裁的内容。
    """
    from campaignlab.api.common import canonical_json, decode_cursor, encode_cursor

    _seed(store, 3)
    secret = b"7" * 32
    query = {"workspace_id": WS, "limit": 2, "q": None, "status": None}
    digest = hashlib.sha256(canonical_json(query).encode("utf-8")).hexdigest()[:16]
    _, payload = _call_list(service, limit=2, query_digest=digest)
    assert payload is not None and payload["q"] == digest
    token = encode_cursor(payload, secret)
    assert isinstance(token, str) and token
    assert decode_cursor(token, secret) == payload
    # 解回来的载荷能直接喂回 list_jobs（翻页闭环不依赖 S4 的任何私有状态）。
    tail, _ = _call_list(service, limit=2, query_digest=digest, cursor_payload=payload)
    assert [record.id for record in tail] == ["J-00"]


# --------------------------------------------------------------------------- 另三个方法


def test_service_signatures_mirror_the_store_method_they_forward_to() -> None:
    """``get_job`` / ``cancel_job`` / ``retry_job`` 的参数面与 store 侧**逐字同形**。

    本层不加不减、不改默认值：一旦服务层偷偷给 ``role`` 换个默认值、或把 ``revision``
    变成可选，S4 的 ``If-Match`` 与审计角色语义就会在这里被悄悄改写。
    """
    assert _signature_text(JobService.get_job) == _signature_text(JobStore.get_job)
    assert _signature_text(JobService.cancel_job) == _signature_text(JobStore.request_cancel)
    assert _signature_text(JobService.retry_job) == _signature_text(JobStore.retry)


def test_get_job_returns_none_for_a_foreign_workspace(store: JobStore, service: JobService) -> None:
    seeded = _seed(store, 1)
    assert service.get_job(workspace_id=WS, job_id=seeded[0].id) == seeded[0]
    assert service.get_job(workspace_id=OTHER_WS, job_id=seeded[0].id) is None


def test_cancel_job_reaches_the_terminal_state_and_conflicts_on_a_stale_revision(
    store: JobStore, service: JobService
) -> None:
    """QUEUED 直接终态（TX3）；``If-Match`` 过期 → ``RevisionConflict``（412）。"""
    seeded = _seed(store, 1)
    with pytest.raises(RevisionConflict) as conflict:
        service.cancel_job(
            workspace_id=WS,
            job_id=seeded[0].id,
            revision=seeded[0].revision + 7,
            now=T0,
            actor_id=ACTOR,
            request_id=REQUEST,
        )
    assert conflict.value.status == 412
    cancelled = service.cancel_job(
        workspace_id=WS,
        job_id=seeded[0].id,
        revision=seeded[0].revision,
        now=T0,
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    assert cancelled.state == "CANCELLED"
    assert cancelled.revision == seeded[0].revision + 1


def test_retry_job_creates_a_new_queued_row_and_leaves_the_source_untouched(
    store: JobStore, service: JobService
) -> None:
    """TX8：新建一条 QUEUED，源作业终态**一字不变**（JOBS.md:19）。"""
    seeded = _seed(store, 1)
    source_id = seeded[0].id
    cancelled = service.cancel_job(
        workspace_id=WS,
        job_id=source_id,
        revision=seeded[0].revision,
        now=T0,
        actor_id=ACTOR,
        request_id=REQUEST,
    )
    retried = service.retry_job(
        workspace_id=WS,
        job_id=source_id,
        revision=cancelled.revision,
        now=T0 + timedelta(minutes=5),
        actor_id=ACTOR,
        request_id="req-2",
    )
    assert retried.id != source_id
    assert retried.state == "QUEUED"
    assert retried.retry_of == source_id
    assert retried.revision == 1 and retried.attempt == 0
    assert retried.kind == cancelled.kind
    assert retried.input_digest == cancelled.input_digest
    fresh = service.get_job(workspace_id=WS, job_id=source_id)
    assert fresh is not None
    assert fresh.state == "CANCELLED", "源作业的终态不得被重试抹掉"
