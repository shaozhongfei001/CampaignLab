"""M2-01/S5 · design §11.1 末条：``domain/activity`` 零运行期上行导入边（AST 分层守护）。

体例照 ``tests/unit/test_layering_edges.py``：读 AST 不读源文本、白名单为模块级常量、
正向对照走 ``tmp_path``（禁落工作树）。``TYPE_CHECKING`` 块内的导入按先例豁免
（design §14.3 的 A233 口径）。扫描面只有 ``src/campaignlab/domain/activity``，不扫 ``tests/**``。
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DOMAIN_ACTIVITY_ROOT = REPO_ROOT / "src" / "campaignlab" / "domain" / "activity"
FORBIDDEN_PREFIXES = ("campaignlab.api", "campaignlab.infra", "campaignlab.application")
#: §4.1/§6.1-G 实测分母：目录恰 7 个 ``.py``（防 glob 扫空全绿）。
EXPECTED_FILE_NAMES = [
    "__init__.py",
    "bindings.py",
    "checks.py",
    "clauses.py",
    "diff.py",
    "digests.py",
    "states.py",
]


def _module_dotted(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT).as_posix()
    assert relative.startswith("src/")
    return relative[len("src/") :].removesuffix(".py").replace("/", ".")


def _is_type_checking(test: ast.expr) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


def _forbidden(name: str) -> bool:
    return any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_PREFIXES)


def _absolute_from(node: ast.ImportFrom, module_dotted: str) -> str:
    if node.level == 0:
        return node.module or ""
    parts = module_dotted.split(".")[:-1]
    for _ in range(node.level - 1):
        parts = parts[:-1]
    if node.module:
        parts = [*parts, node.module]
    return ".".join(parts)


def _scan_text(text: str, module_dotted: str) -> list[str]:
    """返回运行期（非 ``TYPE_CHECKING`` 块）命中的违禁导入边目标列表。"""
    tree = ast.parse(text)
    edges: list[str] = []

    def walk(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If) and _is_type_checking(child.test):
                continue
            if isinstance(child, ast.Import):
                for alias in child.names:
                    if _forbidden(alias.name):
                        edges.append(alias.name)
            elif isinstance(child, ast.ImportFrom):
                name = _absolute_from(child, module_dotted)
                if _forbidden(name):
                    edges.append(name)
            walk(child)

    walk(tree)
    return edges


def _scan_file(path: Path) -> list[str]:
    return _scan_text(path.read_text(encoding="utf-8"), _module_dotted(path))


def test_domain_activity_has_no_runtime_import_edge_to_api_infra_application() -> None:
    files = sorted(DOMAIN_ACTIVITY_ROOT.glob("*.py"))
    assert len(files) == 7 > 0
    assert [f.name for f in files] == EXPECTED_FILE_NAMES
    offenders = {f.name: _scan_file(f) for f in files}
    assert {name: edges for name, edges in offenders.items() if edges} == {}
    for f in files:
        assert _scan_file(f) == [], f


def test_domain_activity_layering_scanner_has_teeth(tmp_path: Path) -> None:
    probe = tmp_path / "probe_runtime.py"
    probe.write_text(
        "def use() -> object:\n"
        "    from campaignlab.api.common import canonical_json\n"
        "\n"
        "    return canonical_json\n",
        encoding="utf-8",
    )
    edges = _scan_text(probe.read_text(encoding="utf-8"), "campaignlab.domain.activity.probe")
    assert edges == ["campaignlab.api.common"]

    guarded = tmp_path / "probe_type_checking.py"
    guarded.write_text(
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from campaignlab.api.common import canonical_json\n",
        encoding="utf-8",
    )
    assert (
        _scan_text(guarded.read_text(encoding="utf-8"), "campaignlab.domain.activity.probe") == []
    )

    decoy = tmp_path / "probe_decoy.py"
    decoy.write_text(
        "# from campaignlab.infra.db import engine\n"
        'TEXT = "from campaignlab.application.activity_service import svc"\n'
        "def f() -> object:\n"
        "    from campaignlab.domain import errors\n"
        "\n"
        "    return errors\n",
        encoding="utf-8",
    )
    assert _scan_text(decoy.read_text(encoding="utf-8"), "campaignlab.domain.activity.probe") == []

    parent = tmp_path / "probe_parent.py"
    parent.write_text("from campaignlab.api import common\n", encoding="utf-8")
    assert _scan_text(parent.read_text(encoding="utf-8"), "campaignlab.domain.activity.probe") == [
        "campaignlab.api"
    ]
