"""FU-14（编排器自我更正 R6-3）：``counts.ruff_formatted_files`` 的新鲜度机器守护。

**要防的事**：门禁与 counts 采样发生在台账/缺陷单落盘**之前**，权威
``counts.ruff_formatted_files`` 因此记下偏小的分母，而真实待提交树更大。A75 / D-012 / D-014
规定派单文禁写死计数、一律指向 ``counts`` 现值 —— 一个偏小的现值会让下一条 lane 的恒等式
断言撞上「实测 != 台账」的**假 RED**。本守护把「台账现值 == 已提交树重算值」钉成机器断言。

**分母只从已提交树取**（``git ls-tree -r HEAD --name-only -z``），禁从工作树/索引取数
（``git ls-files``）：本轮有 3 条 lane 同处一个工作树，索引与工作树里全是他人半成品，按它们
取数会让守护在轮次中途必然判红；而 ``counts`` 记录的语义正是「上一次全表复验时那棵提交树」
的分母，与 HEAD 树对齐。台账侧的刷新时点与原因记在 ``counts_refreshed_at`` /
``counts_refresh_reason``，本守护失败时会把两者一起打出来，便于区分「守护口径写错」与
「台账真的失真」。

**期望值一律从台账读**（``orchestrator/state.json -> resume.self_check_gates_rc0.counts``），
本文件不写死任何计数。**不调 ruff**：守护不跑 ``ruff format --check``（慢、依赖 .venv、
且会与在飞 lane 抢工具链），只用 ``git`` + 纯 Python 计数。

**口径与台账逐字对齐**：``reproduce_py`` / ``reproduce_md`` 即 ``*.py`` 与 ``*.md`` 两类、
排除 ``spec/``、``prototype/``、``web/``；另按 ``exclusions_verified`` 与 ``pyproject.toml`` 的
``extend-exclude`` 补 ``.venv/`` 与 ``node_modules/``（二者本就不在提交树里，列出为口径显式）。
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
STATE_PATH: Final = REPO_ROOT / "orchestrator" / "state.json"
COUNTS_LABEL: Final = "resume.self_check_gates_rc0.counts"
COMPOSITION_LABEL: Final = "ruff_formatted_files_composition"

PY_SUFFIXES: Final = (".py",)
MD_SUFFIXES: Final = (".md",)
EXCLUDED_PREFIXES: Final = ("spec/", "prototype/", "web/", ".venv/", "node_modules/")
#: 台账 reproduce_* 命令里那段排除前缀的括号分组（内容形如 spec|prototype|web），
#: 用于「口径没被人悄悄换掉」的对账。
_ALTERNATION: Final = re.compile(r"\(([^()]*)\)")


def _as_text(value: object) -> str:
    return value if isinstance(value, str) else repr(value)


def _git(args: list[str]) -> str:
    """跑只读 git 命令并取回文本输出；``stdout`` 不是字符串时显式判红（禁 Any 泄漏）。"""
    completed = subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"git 取数失败：{args} rc={completed.returncode} "
            f"stderr={_as_text(completed.stderr).strip()[:400]}"
        )
    stdout: object = completed.stdout
    if not isinstance(stdout, str):
        raise AssertionError(
            f"git 返回的 stdout 不是文本（实测类型 {type(stdout).__name__}）：{args}"
        )
    return stdout


def _head_tree_paths() -> tuple[str, ...]:
    """HEAD 提交树里的全部文件路径（NUL 分隔：中文名与空格都不被引号转义破坏）。"""
    raw = _git(["git", "ls-tree", "-r", "HEAD", "--name-only", "-z"])
    return tuple(entry for entry in raw.split("\0") if entry)


def _in_scope(paths: tuple[str, ...], suffixes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        path for path in paths if path.endswith(suffixes) and not path.startswith(EXCLUDED_PREFIXES)
    )


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise AssertionError(f"{label} 应是 JSON 对象，实测类型 {type(value).__name__}")
    return {str(key): item for key, item in value.items()}


def _field(mapping: Mapping[str, object], key: str, label: str) -> object:
    if key not in mapping:
        raise AssertionError(f"台账缺字段：{label}.{key}")
    return mapping[key]


def _int_field(mapping: Mapping[str, object], key: str, label: str) -> int:
    value = _field(mapping, key, label)
    if not isinstance(value, int) or isinstance(value, bool):
        raise AssertionError(f"台账 {label}.{key} 应是整数，实测 {value!r}")
    return value


def _str_field(mapping: Mapping[str, object], key: str, label: str) -> str:
    value = _field(mapping, key, label)
    if not isinstance(value, str):
        raise AssertionError(f"台账 {label}.{key} 应是字符串，实测 {value!r}")
    return value


def _optional_str(mapping: Mapping[str, object], key: str) -> str:
    value = mapping.get(key)
    return value if isinstance(value, str) else "<台账未记录>"


def _ledger() -> tuple[Mapping[str, object], Mapping[str, object]]:
    """返回 ``(counts, ruff_formatted_files_composition)``：本守护期望值的唯一来源。"""
    raw: object = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    node = _mapping(raw, "state.json 根")
    for key in ("resume", "self_check_gates_rc0", "counts"):
        node = _mapping(_field(node, key, "state.json"), key)
    composition = _mapping(
        _field(node, COMPOSITION_LABEL, COUNTS_LABEL),
        COUNTS_LABEL + "." + COMPOSITION_LABEL,
    )
    return node, composition


def _refresh_stamp(counts: Mapping[str, object]) -> str:
    return (
        "台账刷新时点="
        + _optional_str(counts, "counts_refreshed_at")
        + "／原因="
        + _optional_str(counts, "counts_refresh_reason")[:120]
    )


def test_head_tree_resolves_to_this_repository() -> None:
    """前置条件：分母必须真来自本仓提交树，否则后面的数字对不上也无从判断。"""
    tree = _head_tree_paths()
    assert tree, "HEAD 提交树为空：cwd 或 git 环境不成立，本守护不做静默通过"
    assert any(path.endswith("orchestrator/state.json") for path in tree), (
        "HEAD 树里找不到 orchestrator/state.json：取数的仓库根不对"
    )
    assert any(path.endswith("pyproject.toml") for path in tree), (
        "HEAD 树里找不到 pyproject.toml：取数的仓库根不对"
    )


def test_denominator_excludes_every_in_flight_working_tree_file() -> None:
    """口径自证：工作树里「尚未入库」的文件一律不进分母 —— 这正是选 HEAD 树的理由。

    本轮 3 条 lane 同处一个工作树。若按 ``git ls-files``（索引）或按工作树 ``rglob``
    取数，在飞的半成品会随时改变分母，守护就会在轮次中途把「别人的中间态」误报成
    「台账失真」（本片自己的守护文件在写作时即属此类：它在磁盘上，却不在 HEAD 树里，
    入库之后才两边一致 —— 所以这里断言的是口径关系而不是它的缺席，免得提交后自判红）。
    HEAD 树不含任何未入库路径，分母只随已提交树变化，与 ``counts`` 的语义一致。
    """
    tree = set(_head_tree_paths())
    status = _git(["git", "status", "--porcelain", "--untracked-files=all"])
    in_flight = {
        rest
        for line in status.splitlines()
        if line.startswith("?? ")
        for rest in [line[3:]]
        if not rest.startswith('"')
    }
    assert not (in_flight & tree), (
        f"未入库的在飞文件不该出现在 HEAD 树里，分母口径被污染：{sorted(in_flight & tree)}"
    )
    own = "tests/unit/test_counts_freshness.py"
    assert (REPO_ROOT / own).is_file(), f"守护文件应在工作树里：{own}"
    assert own in tree or own in in_flight, f"守护文件既不在 HEAD 树也不在未入库集合：{own}"


def test_committed_tree_denominator_matches_authoritative_counts() -> None:
    tree = _head_tree_paths()
    measured_py = len(_in_scope(tree, PY_SUFFIXES))
    measured_md = len(_in_scope(tree, MD_SUFFIXES))
    counts, composition = _ledger()
    ledger_py = _int_field(composition, "in_scope_py", COMPOSITION_LABEL)
    ledger_md = _int_field(composition, "in_scope_md", COMPOSITION_LABEL)
    ledger_total = _int_field(composition, "total", COMPOSITION_LABEL)
    ledger_ruff = _int_field(counts, "ruff_formatted_files", COUNTS_LABEL)
    stamp = _refresh_stamp(counts)

    assert measured_py == ledger_py, (
        f"① py 分母失真：HEAD 提交树实测 {measured_py} != 台账 in_scope_py {ledger_py}（{stamp}）"
    )
    assert measured_md == ledger_md, (
        f"② md 分母失真：HEAD 提交树实测 {measured_md} != 台账 in_scope_md {ledger_md}（{stamp}）"
    )
    assert measured_py + measured_md == ledger_total, (
        f"③ 合计失真：HEAD 提交树实测 {measured_py} + {measured_md} = "
        f"{measured_py + measured_md} != 台账 composition.total {ledger_total}（{stamp}）"
    )
    assert ledger_total == ledger_ruff, (
        f"④ 权威值失真：台账 composition.total {ledger_total} != "
        f"counts.ruff_formatted_files {ledger_ruff}（{stamp}）"
    )


def test_ledger_composition_is_internally_consistent() -> None:
    """台账自身对账：只改 total 而忘了 in_scope_* 也是 R6-3 型失真的一种形态。"""
    counts, composition = _ledger()
    ledger_py = _int_field(composition, "in_scope_py", COMPOSITION_LABEL)
    ledger_md = _int_field(composition, "in_scope_md", COMPOSITION_LABEL)
    ledger_total = _int_field(composition, "total", COMPOSITION_LABEL)
    ledger_ruff = _int_field(counts, "ruff_formatted_files", COUNTS_LABEL)
    assert ledger_py + ledger_md == ledger_total, (
        f"台账内部不自洽：in_scope_py {ledger_py} + in_scope_md {ledger_md} != total "
        f"{ledger_total}（{_refresh_stamp(counts)}）"
    )
    assert ledger_total == ledger_ruff, (
        f"台账内部不自洽：composition.total {ledger_total} != ruff_formatted_files "
        f"{ledger_ruff}（{_refresh_stamp(counts)}）"
    )


def test_ledger_reproduce_caliber_still_matches_this_guard() -> None:
    """口径对账：台账 reproduce_* 换了排除前缀或扩展名，本守护必须同步改，禁各自漂移。"""
    _, composition = _ledger()
    py_cmd = _str_field(composition, "reproduce_py", COMPOSITION_LABEL)
    md_cmd = _str_field(composition, "reproduce_md", COMPOSITION_LABEL)
    assert "*.py" in py_cmd, f"reproduce_py 的扩展名口径变了：{py_cmd}"
    assert "*.md" in md_cmd, f"reproduce_md 的扩展名口径变了：{md_cmd}"
    for cmd in (py_cmd, md_cmd):
        group = _ALTERNATION.search(cmd)
        assert group is not None, f"reproduce 命令里找不到排除前缀的括号分组：{cmd}"
        excluded = {part + "/" for part in group.group(1).split("|")}
        assert excluded <= set(EXCLUDED_PREFIXES), (
            f"台账排除前缀 {sorted(excluded)} 不在本守护实现的 {sorted(EXCLUDED_PREFIXES)} 内："
            "口径变了要由 G lane 同步改本文件，禁默默放宽"
        )
