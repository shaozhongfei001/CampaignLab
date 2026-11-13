"""M0-04/S2b-1 → FU-29：``infra/** → campaignlab.worker`` 导入边守护（白名单已收紧为空集）。

``infra`` 是 HTTP 进程与 worker 进程共用的底座，``worker`` 是只有 worker 进程才该拉起的
执行层，故 ``infra → worker`` 是**分层倒置**。A153 曾追认过全仓唯一一条这样的边
（``src/campaignlab/infra/artifacts.py`` 里的
``from campaignlab.worker.errors import ArtifactCommitFailed``）：**FU-29 已把该异常类下沉
到 ``domain/errors.py``、把消费端改指 ``campaignlab.domain.errors``，那条边随之消失**，
白名单 ``ALLOWED_INFRA_TO_WORKER_EDGES`` 因此收紧为 ``frozenset()``。从现在起**任何**
``infra → worker`` 边都判红，不再有豁免项。

边目标记为**被执行的那个模块** —— ``from X import Y`` 记 ``X``，因为无论 ``Y`` 是不是
子模块，``X`` 都已被执行。这个口径在 FU-29 之后依然重要：它区分「子模块路径」
（``from campaignlab.worker.errors import ...``，只执行 ``worker/errors.py``）与**父包
属性式**（``from campaignlab.worker import ...``，会传递执行整个 ``worker/__init__.py``，
把状态机、租约、事务边界与执行编排一并拖进 HTTP 进程 —— A153 硬约束）。两者现在都判红，
但报错文本里的边目标不同，能直接指出是哪一种回退。

**白名单是模块级常量**，且本文件的用例一律**不写死**其内容：这正是 FU-29 只改一行即可
收紧的原因，也让将来万一要再开豁免时同样只改一行（并被迫面对
``test_the_whitelist_never_legalises_a_parent_package_edge``：父包边永不豁免）。

扫描用 ``ast``（禁正则扫源码文本）：正则读不出 ``ImportFrom.level``（相对导入的点数），
也分不清真导入与注释／字符串里的伪导入。四条 ``tmp_path`` 探针（**不落工作树**）分别
证明：父包式判红、非白名单文件判红、相对导入不能规避、注释与字符串不算边；最后一条与
前三条合起来破掉「恒返回全集」与「恒返回空集」两种假绿。收紧为空集后又多一条对照：
``test_infra_to_worker_edges_are_exactly_the_allowed_whitelist`` 会用探针证明扫描器**仍能**
扫出 FU-29 之前那条边，故「实测空集」是真没边，不是扫描器坏了。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
INFRA_ROOT: Final = REPO_ROOT / "src" / "campaignlab" / "infra"
SELF_PATH: Final = Path(__file__).resolve()
SOURCE_PREFIX: Final = "src/"
PY_SUFFIX: Final = ".py"
WORKER_PACKAGE: Final = "campaignlab.worker"
WHITELIST_SYMBOL: Final = "ALLOWED_INFRA_TO_WORKER_EDGES"
#: 探针树里那个「非白名单文件」的仓库相对键（探针布局与工作树同形，故键也同形）。
PROBE_KEY: Final = "src/campaignlab/infra/probe.py"

#: **FU-29 已闭合**：``ArtifactCommitFailed`` 下沉到 ``domain/errors.py``，
#: ``infra/artifacts.py`` 改指 ``campaignlab.domain.errors``，全仓 ``infra → worker``
#: 反向边归零。故本白名单是**空集**，任何一条 ``infra → worker`` 边（子模块路径或父包
#: 属性式，一律）都判红。收紧只改了这一行 —— 这正是把它做成模块级常量的目的。
#: 形态也受守护：必须保持「模块顶层恰好一次 ``AnnAssign``」，因为
#: ``test_the_whitelist_is_a_module_level_constant_ready_for_fu29`` 用 AST 数声明次数 == 1。
ALLOWED_INFRA_TO_WORKER_EDGES: Final[frozenset[tuple[str, str]]] = frozenset()


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
    """``from ..mod import X`` → 绝对点分路径。``level=1`` 指本包，故裁掉 ``level - 1`` 级。

    裁穿了顶层（``keep < 0``）在 CPython 里就是 ``ImportError: attempted relative import
    beyond top-level package``，即该文件根本导入不起来。本守护**不静默跳过**这种写法，
    而是显式抛错让它判红：静默跳过等于给「用畸形相对导入绕过白名单」留口子。
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


def _is_worker(dotted: str) -> bool:
    """是否落在 ``campaignlab.worker`` 包里（含父包自身）。"""
    return dotted == WORKER_PACKAGE or dotted.startswith(WORKER_PACKAGE + ".")


def _import_from_target(node: ast.ImportFrom, package: str) -> str:
    """``ImportFrom`` 节点**被执行**的模块：``level == 0`` 即绝对导入，直接取 ``module``。

    绝对导入不能走 ``_resolve_relative``：那里 ``keep = len(parts) - (level - 1)`` 在
    ``level == 0`` 时会多留一级，把 ``campaignlab.worker.errors`` 拼成
    ``campaignlab.infra.campaignlab.worker.errors``，边就被静默漏掉（本片 loop3 实测到过，
    表现是「唯一那条边扫出 0 条」—— 正是本文件要防的假绿方向）。
    """
    if node.level:
        return _resolve_relative(node.level, node.module, package)
    return node.module or ""


def _imported_modules(node: ast.AST, package: str) -> list[str]:
    """一个导入节点会**执行**哪些模块（点分路径列表）。

    ``from X import Y`` 只记 ``X``：A153 关心的是父包 ``__init__`` 会不会被传递执行，而
    无论 ``Y`` 是不是子模块，``X`` 都已经被执行了 —— 记成 ``X.Y`` 反而会把「执行了父包」
    这个最关键的事实抹掉，正是本守护要判红的那种「整理」。
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        return [_import_from_target(node, package)]
    return []


def scan_worker_import_edges(scan_root: Path, *, repo_root: Path) -> list[tuple[str, int, str]]:
    """扫描器本体：``(仓库相对路径, 行号, 被执行的 worker 点分路径)``，按路径与行号排序。

    ``repo_root`` 只负责把文件路径与模块名都表达成仓库相对形式：真实调用传仓库根，正向
    对照传 ``tmp_path``（探针树自带 ``src/campaignlab/infra/`` 布局，故相对导入同样可解析）。
    """
    found: list[tuple[str, int, str]] = []
    for path in sorted(scan_root.rglob("*" + PY_SUFFIX)):
        dotted = _module_dotted_name(path, repo_root)
        package = _package_of(dotted, path)
        key = path.relative_to(repo_root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for target in _imported_modules(node, package):
                if _is_worker(target):
                    found.append((key, node.lineno, target))
    return sorted(found, key=lambda item: (item[0], item[1]))


def collect_worker_import_edges(scan_root: Path, *, repo_root: Path) -> set[tuple[str, str]]:
    """边**集合**（守护断言用的口径；行号只服务于报错定位，故在此收敛掉）。"""
    return {
        (key, target)
        for key, _lineno, target in scan_worker_import_edges(scan_root, repo_root=repo_root)
    }


def _probe_repo(tmp_path: Path, source: str) -> Path:
    """在 ``tmp_path`` 里搭一棵 ``src/campaignlab/infra/probe.py`` 探针树，返回其仓库根。

    探针只活在 pytest 的 ``tmp_path``（用例结束随临时目录销毁），**绝不落工作树**：正向
    对照必须能被判红，但判红的载体不能留在仓库里污染 ``ruff``／``mypy`` 的分母。
    """
    infra = tmp_path / "src" / "campaignlab" / "infra"
    infra.mkdir(parents=True, exist_ok=True)
    (infra / "probe.py").write_text(source, encoding="utf-8", newline="\n")
    return tmp_path


def test_infra_to_worker_edges_are_exactly_the_allowed_whitelist(tmp_path: Path) -> None:
    """FU-29 后：``infra/** → worker`` 的边集合恰等于白名单（现为空集，既不多也不少）。

    「实测为空」必须能与「扫描器坏了」区分开，否则守护会退化成恒绿。故断言空集之后再用
    ``_probe_repo`` 造一棵含 FU-29 之前那条边（``from campaignlab.worker.errors import
    ArtifactCommitFailed``）的探针树，证明**同一个扫描器仍能扫出它** —— 工作树为空是真没边。
    """
    measured = collect_worker_import_edges(INFRA_ROOT, repo_root=REPO_ROOT)
    located = scan_worker_import_edges(INFRA_ROOT, repo_root=REPO_ROOT)
    extra = measured - ALLOWED_INFRA_TO_WORKER_EDGES
    gone = ALLOWED_INFRA_TO_WORKER_EDGES - measured
    assert not extra, (
        "出现未授权的 infra → worker 反向边（FU-29 已把白名单收紧为空集，任何一条都判红）："
        + str(sorted(extra))
    )
    assert not gone, "白名单里的边已不在工作树中：" + str(sorted(gone))
    assert not located, f"FU-29 后 infra → worker 应为零边，实测 {located}"
    # 正向对照（反假绿，禁删）：同一个扫描器仍能扫出 FU-29 之前的那条边。
    probe_source = "from campaignlab.worker.errors import ArtifactCommitFailed\n"
    probe_root = _probe_repo(tmp_path, probe_source)
    assert scan_worker_import_edges(probe_root, repo_root=probe_root) == [
        (PROBE_KEY, 1, "campaignlab.worker.errors")
    ], "扫描器扫不出 FU-29 之前那条边：空集不可信，守护已失去反假绿能力"


def test_artifacts_has_zero_worker_import_nodes_of_either_kind() -> None:
    """FU-29 逐节点核对：``artifacts.py`` 里 worker 导入节点数 == **0**（两种节点都覆盖）。

    原用例的前提是「恰有 1 条边」且它必须走子模块路径 ``campaignlab.worker.errors``；
    FU-29 把 ``ArtifactCommitFailed`` 下沉 ``domain/errors.py`` 后该前提消失，故改为零反向边
    语义。``ImportFrom`` 与 ``Import`` **分别**核对：``from campaignlab.worker... import X``
    与 ``import campaignlab.worker...`` 都必须不存在 —— 只覆盖一种就是给另一种留绕过口子。
    """
    artifacts = INFRA_ROOT / "artifacts.py"
    package = _package_of(_module_dotted_name(artifacts, REPO_ROOT), artifacts)
    tree = ast.parse(artifacts.read_text(encoding="utf-8-sig"), filename=str(artifacts))
    from_nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and _is_worker(_import_from_target(node, package))
    ]
    assert from_nodes == [], (
        "artifacts.py 仍有 from … worker 的反向边（FU-29 后必须是 0 条）："
        + str([(node.lineno, node.module, node.level) for node in from_nodes])
    )
    plain = [
        alias.name
        for item in ast.walk(tree)
        if isinstance(item, ast.Import)
        for alias in item.names
        if _is_worker(alias.name)
    ]
    assert plain == [], f"artifacts.py 不得用 import 语句引入 worker：{plain}"


def test_parent_package_style_import_would_be_flagged(tmp_path: Path) -> None:
    """正向对照①：把它「整理」成父包属性式导入 → 检出、白名单不覆盖 → 判红。"""
    repo_root = _probe_repo(tmp_path, "from campaignlab.worker import ArtifactCommitFailed\n")
    measured = collect_worker_import_edges(repo_root, repo_root=repo_root)
    assert measured == {(PROBE_KEY, WORKER_PACKAGE)}, (
        f"父包属性式导入必须被记成 {WORKER_PACKAGE!r} 这条边，实测 {sorted(measured)}"
    )
    assert not (measured <= ALLOWED_INFRA_TO_WORKER_EDGES), "父包边不得被白名单放过"


def test_worker_import_from_a_non_whitelisted_file_would_be_flagged(tmp_path: Path) -> None:
    """正向对照②：换个文件走同样的子模块路径 → 仍判红（白名单按 ``(文件, 模块)`` 配对）。"""
    repo_root = _probe_repo(tmp_path, "from campaignlab.worker.leases import Lease\n")
    measured = collect_worker_import_edges(repo_root, repo_root=repo_root)
    assert measured == {(PROBE_KEY, "campaignlab.worker.leases")}
    assert not (measured <= ALLOWED_INFRA_TO_WORKER_EDGES), "非白名单文件的边不得被放过"


def test_relative_import_cannot_be_used_to_evade_the_whitelist(tmp_path: Path) -> None:
    """正向对照③：相对导入 ``from ..worker.store import JobStore`` 同样被解析并检出。"""
    repo_root = _probe_repo(tmp_path, "from ..worker.store import JobStore\n")
    measured = collect_worker_import_edges(repo_root, repo_root=repo_root)
    assert measured == {(PROBE_KEY, "campaignlab.worker.store")}, (
        f"相对导入必须解析成绝对点分路径，实测 {sorted(measured)}"
    )
    assert not (measured <= ALLOWED_INFRA_TO_WORKER_EDGES)


CLEAN_PROBE: Final = (
    "# from campaignlab.worker.errors import ArtifactCommitFailed  ← 注释里的伪导入\n"
    'NOT_AN_IMPORT = "import campaignlab.worker.store"\n'
    "from campaignlab.domain.errors import DomainError\n"
    "from campaignlab.infra.db import repositories\n"
)


def test_scanner_reads_the_ast_not_the_source_text(tmp_path: Path) -> None:
    """正向对照④（反假绿）：注释与字符串里的伪导入不算边，且扫描器**能**返回空集。

    与前三条合起来破掉两种假绿：「恒返回全集」被本条判红，「恒返回空集」被前三条判红。
    """
    repo_root = _probe_repo(tmp_path, CLEAN_PROBE)
    assert collect_worker_import_edges(repo_root, repo_root=repo_root) == set()


def test_the_whitelist_is_a_module_level_constant_ready_for_fu29() -> None:
    """FU-29 的收紧点必须是**本文件顶层的常量**且只声明一次（写进用例里就没法一行收紧）。"""
    tree = ast.parse(SELF_PATH.read_text(encoding="utf-8-sig"), filename=str(SELF_PATH))
    declarations = [
        statement
        for statement in tree.body
        if isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
        and statement.target.id == WHITELIST_SYMBOL
    ]
    assert len(declarations) == 1, (
        f"{WHITELIST_SYMBOL} 必须在本文件顶层恰好声明一次（FU-29 要能一行收紧为空集）"
    )


def test_the_whitelist_never_legalises_a_parent_package_edge() -> None:
    """白名单自身也服从 A153：任何一项都不得是父包 ``campaignlab.worker``。

    本条不写死白名单内容，故 FU-29 把它收紧为 ``frozenset()`` 后自动继续成立。
    """
    for key, target in sorted(ALLOWED_INFRA_TO_WORKER_EDGES):
        assert target != WORKER_PACKAGE, f"白名单不得合法化父包属性式导入：{key}"
        assert target.startswith(WORKER_PACKAGE + "."), (
            f"白名单项必须是 worker 的子模块路径：{target}"
        )
        assert (REPO_ROOT / key).is_file(), f"白名单指向的文件不在工作树里：{key}"
