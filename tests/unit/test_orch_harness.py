"""FU-35: scripts/orch_harness.py 的纯单元测试（R13 lane V）。

只覆盖派单文 §2 的 12 个纯函数/纯数据符号。凡需要 git/子进程的符号
（sh/git/git_out/head_sha/branch/status_porcelain/tracked_in_scope/predict_counts/
predict_pytest/stage/commit_staged/frozen_tree/run_gates/count_git_env_ignores/
load_state/dump_state/run_commit/commit_and_verify/main）不在本 lane 范围，禁测。

纯单元测试：无 subprocess、无 git 调用、无工具链、无网络；临时数据一律走 tmp_path。
被测工装文件本体禁改（派单文 §4）。

取工装方式说明（U 项，回执第 5 段）：派单文 §5 的 `import orch_harness as h` 字面形式
在 §6 的路径限定 mypy 下必然 import-not-found（pyproject 的 mypy_path 只含 src，禁改），
故保留「sys.path.insert 后按模块名取工装」的语义，改用 __import__ + 显式 h: Any。
"""

import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
__import__("orch_harness")
h: Any = sys.modules["orch_harness"]

#: 派单文 §2 点名的 12 个必须覆盖符号（§3 的分母守护据此钉死，禁静默删测）。
TARGETS = frozenset(
    {
        "in_scope",
        "_is_mypy_scope",
        "normalize_file",
        "normalize_many",
        "write_msg_file",
        "_judge",
        "gate_number",
        "all_green",
        "get_counts",
        "set_counts",
        "classify_untracked",
        "dangling_refs",
    }
)


def _state_with_counts(counts: object) -> dict[str, object]:
    """按权威路径 COUNTS_JSONPATH（resume.self_check_gates_rc0.counts）构造假台账。"""
    root: dict[str, object] = {}
    node: dict[str, object] = root
    for key in h.COUNTS_JSONPATH[:-1]:
        child: dict[str, object] = {}
        node[key] = child
        node = child
    node[h.COUNTS_JSONPATH[-1]] = counts
    return root


def _test_body_text(src: str) -> str:
    """拼接本文件所有 test_ 函数体的文本（模块级行与私有辅助函数体不计入）。

    兼容 ruff format 可能把 def 签名折行成多行的形态：未闭合签名的续行与收尾行
    （如 `) -> None:`）不得被误判为「函数体结束」而吞掉整个函数体。
    """
    chunks: list[str] = []
    in_test_body = False
    pending_def: str | None = None
    for raw in src.splitlines():
        if raw.startswith("def "):
            in_test_body = False
            fname = raw.removeprefix("def ").split("(", 1)[0].strip()
            if raw.rstrip().endswith(":"):
                in_test_body = fname.startswith("test_")
                pending_def = None
            else:
                pending_def = fname
            continue
        if pending_def is not None:
            if raw and not raw.startswith((" ", "\t")) and raw.rstrip().endswith(":"):
                in_test_body = pending_def.startswith("test_")
                pending_def = None
            continue
        if not in_test_body:
            continue
        if raw and not raw.startswith((" ", "\t")):
            in_test_body = False
            continue
        chunks.append(raw)
    return "\n".join(chunks)


# --------------------------------------------------------------------- 1. in_scope


def test_in_scope_excludes_prefixes_and_requires_suffix() -> None:
    assert h.in_scope("docs/x.md") is True
    assert h.in_scope("src/a.py") is True
    assert h.in_scope("web/x.md") is False
    assert h.in_scope("docs/x.txt") is False
    assert h.in_scope("spec/a.md") is False
    assert h.in_scope("prototype/p.md") is False


# --------------------------------------------------------------------- 2. _is_mypy_scope


def test_is_mypy_scope_three_roots_and_rejects() -> None:
    assert h._is_mypy_scope("scripts/x.py") is True
    assert h._is_mypy_scope("tests/y.py") is True
    assert h._is_mypy_scope("src/z.py") is True
    assert h._is_mypy_scope("web/x.py") is False
    assert h._is_mypy_scope("docs/x.md") is False
    assert h._is_mypy_scope("src/data.json") is False


# --------------------------------------------------------------------- 3. normalize_file


def test_normalize_file_each_fix_once(tmp_path: Path) -> None:
    p_bom = tmp_path / "bom.md"
    p_bom.write_bytes(b"\xef\xbb\xbfhello\n")
    assert h.normalize_file(p_bom) == ["BOM_REMOVED"]
    assert p_bom.read_bytes() == b"hello\n"

    p_cr = tmp_path / "cr.md"
    p_cr.write_bytes(b"a\r\nb\rc\n")
    assert h.normalize_file(p_cr) == ["CR_REMOVED"]
    assert p_cr.read_bytes() == b"a\nb\nc\n"

    p_nl = tmp_path / "nl.md"
    p_nl.write_bytes(b"tail")
    assert h.normalize_file(p_nl) == ["TRAILING_NL_ADDED"]
    assert p_nl.read_bytes() == b"tail\n"


def test_normalize_file_fixes_stack_in_order(tmp_path: Path) -> None:
    p = tmp_path / "all.md"
    p.write_bytes(b"\xef\xbb\xbf\r\nx")
    assert h.normalize_file(p) == ["BOM_REMOVED", "CR_REMOVED", "TRAILING_NL_ADDED"]
    assert p.read_bytes() == b"\nx\n"


def test_normalize_file_compliant_returns_empty_unmodified(tmp_path: Path) -> None:
    p = tmp_path / "ok.md"
    p.write_bytes(b"ok\n")
    before = p.read_bytes()
    mtime_before = p.stat().st_mtime_ns
    assert h.normalize_file(p) == []
    assert p.read_bytes() == before
    assert p.stat().st_mtime_ns == mtime_before  # 合规文件不得被改写


# --------------------------------------------------------------------- 4. normalize_many


def test_normalize_many_keys_only_actual_fixes(tmp_path: Path) -> None:
    good = tmp_path / "good.py"
    good.write_bytes(b"ok\n")
    bad = tmp_path / "bad.py"
    bad.write_bytes(b"no-newline")
    out = h.normalize_many([good, bad])
    assert out == {str(bad): ["TRAILING_NL_ADDED"]}
    assert str(good) not in out


# --------------------------------------------------------------------- 5. write_msg_file


def test_write_msg_file_normalizes_and_returns_path(tmp_path: Path) -> None:
    p = tmp_path / "msg.txt"
    ret = h.write_msg_file("a\r\nb", p)
    assert ret == p
    assert ret.read_bytes() == b"a\nb\n"

    p2 = tmp_path / "msg2.txt"
    assert h.write_msg_file("\ufeffc\n", p2) == p2
    assert p2.read_bytes() == b"c\n"

    p3 = tmp_path / "msg3.txt"
    assert h.write_msg_file("\ufeffz", p3) == p3
    assert p3.read_bytes() == b"z\n"

    p4 = tmp_path / "msg4.txt"
    assert h.write_msg_file("x\ry\n", p4) == p4
    assert p4.read_bytes() == b"x\ny\n"


# --------------------------------------------------------------------- 6. _judge


def test_judge_double_verdict_four_way() -> None:
    pattern = r"(\d+) passed"
    forbid = ("FAILED",)

    g1 = h._judge("g1", h.Proc(rc=0, out="5 passed\n", err=""), pattern, forbid)
    assert g1.ok is True  # rc=0 + 文本命中 + 无禁词
    assert g1.name == "g1" and g1.rc == 0
    assert g1.tail == "5 passed"

    g2 = h._judge("g2", h.Proc(rc=1, out="5 passed\n", err=""), pattern, forbid)
    assert g2.ok is False  # rc 非零即红

    g3 = h._judge("g3", h.Proc(rc=0, out="all quiet\n", err=""), pattern, forbid)
    assert g3.ok is False  # rc=0 但文本未命中
    assert "text_ok=False" in g3.detail

    g4 = h._judge("g4", h.Proc(rc=0, out="5 passed\nFAILED\n", err=""), pattern, forbid)
    assert g4.ok is False  # 文本命中但命中禁词
    assert "forbid_hit=" in g4.detail and "FAILED" in g4.detail

    g5 = h._judge("g5", h.Proc(rc=0, out="", err="2 passed"), pattern, ())
    assert g5.ok is True  # out+err 合并参与判定


# --------------------------------------------------------------------- 7. gate_number


def test_gate_number_tail_precedence_and_fallback() -> None:
    g_tail = h.GateResult("n", 0, True, "482 passed", "503 passed")
    assert h.gate_number(g_tail, r"(\d+) passed") == 503  # 先搜 tail

    g_none = h.GateResult("n", 0, True, "nothing here", "tail nothing")
    assert h.gate_number(g_none, r"(\d+) passed") is None

    g_detail = h.GateResult("n", 0, True, "482 passed", "")
    assert h.gate_number(g_detail, r"(\d+) passed") == 482  # tail 未命中才回退 detail


# --------------------------------------------------------------------- 8. all_green


def test_all_green_empty_mapping_is_vacuously_true() -> None:
    """空字典显式断言 True —— 「空集上的全称命题」陷阱（LANE-COMMON §6 分母断言同源风险）。

    all() 对空 iterable 恒真：gates 为空 dict 时「全部门禁绿」其实一个门禁都没有。
    写成显式断言钉死语义，将来若工装改判或调用方误传空集，此处必须红。
    """
    good = h.GateResult(name="a", rc=0, ok=True, detail="d")
    bad = h.GateResult(name="b", rc=1, ok=False, detail="d")
    assert h.all_green({"x": good, "y": good}) is True
    assert h.all_green({"x": good, "y": bad}) is False
    assert h.all_green({}) is True  # 全称命题在空集上为真：陷阱本体，显式钉死


# --------------------------------------------------------------------- 9. get_counts


def test_get_counts_normal_and_missing_key() -> None:
    counts = {"ruff_format_check": 240, "mypy_source_files": 81, "pytest_passed": 503}
    state = _state_with_counts(counts)
    assert h.get_counts(state) == counts
    assert h.get_counts(state) is counts  # 返回台账内的活引用，非拷贝

    broken: dict[str, object] = {"resume": {"self_check_gates_rc0": {}}}
    with pytest.raises(h.HarnessError):
        h.get_counts(broken)  # 缺键


def test_get_counts_non_dict_on_path_rejected() -> None:
    mid_str: dict[str, object] = {"resume": "not-a-dict"}
    with pytest.raises(h.HarnessError):
        h.get_counts(mid_str)  # 路径中间节点非 dict

    leaf_int = _state_with_counts(240)
    with pytest.raises(h.HarnessError):
        h.get_counts(leaf_int)  # counts 本体非 dict


# --------------------------------------------------------------------- 10. set_counts


def test_set_counts_previous_values() -> None:
    state = _state_with_counts({"a": 1, "b": 2})
    ret = h.set_counts(state, {"a": 9, "b": 2}, reason="r13-measured", at="2026-11-14T00:00:00Z")
    assert ret["a"] == 9 and ret["b"] == 2
    assert ret["previous_values_last"] == {"a": 1}  # 只记变了值的旧值
    assert ret["counts_refreshed_at"] == "2026-11-14T00:00:00Z"
    assert ret["counts_refresh_reason"] == "r13-measured"
    assert ret is h.get_counts(state)  # 同一对象：改的是引用而非副本（run_commit 落盘前提）


def test_set_counts_unchanged_no_key() -> None:
    state = _state_with_counts({"a": 5})
    ret = h.set_counts(state, {"a": 5}, reason="same", at="T2")
    assert "previous_values_last" not in ret
    assert ret["counts_refreshed_at"] == "T2"


# --------------------------------------------------------------------- 11. classify_untracked


def test_classify_untracked_forms(monkeypatch: pytest.MonkeyPatch) -> None:
    files = [
        "docs/a.md",  # f == p
        "src/campaignlab/worker/integrity.py",  # f 在 p 目录下
        "docs/FU35-notes.md",  # 裸 f.startswith(p)
        "stray/x.md",
    ]
    monkeypatch.setattr(h, "untracked_in_scope", lambda: list(files))
    owner_map = {
        "lane-exact": ("docs/a.md",),
        "lane-dir": ("src/campaignlab/worker",),
        "lane-bare": ("docs/FU",),
    }
    attributed, outside = h.classify_untracked(owner_map)
    assert attributed == {
        "lane-exact": ["docs/a.md"],
        "lane-dir": ["src/campaignlab/worker/integrity.py"],
        "lane-bare": ["docs/FU35-notes.md"],
    }
    assert outside == ["stray/x.md"]  # 归不上的即越界


def test_classify_untracked_none_map(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(h, "untracked_in_scope", lambda: ["docs/a.md", "stray/x.md"])
    attributed, outside = h.classify_untracked(None)
    assert attributed == {}
    assert outside == ["docs/a.md", "stray/x.md"]


# --------------------------------------------------------------------- 12. dangling_refs


def test_dangling_refs_basic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    monkeypatch.setattr(h, "REPO", repo)
    (repo / "docs" / "present.md").write_text("anchor\n", encoding="utf-8")
    scan = repo / "docs" / "scan.md"
    scan.write_text("see docs/present.md and docs/absent.md\n", encoding="utf-8")
    assert h.dangling_refs(["docs/scan.md"]) == ["docs/scan.md -> docs/absent.md"]


def test_dangling_refs_skips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "orchestrator").mkdir()
    monkeypatch.setattr(h, "REPO", repo)
    (repo / "orchestrator" / "state.json").write_text('{"ref": "docs/absent.md"}', encoding="utf-8")
    assert h.dangling_refs(["orchestrator/state.json"]) == []  # DANGLING_SWEEP_SKIP
    (repo / "docs" / "notes.html").write_text("docs/absent.md\n", encoding="utf-8")
    assert h.dangling_refs(["docs/notes.html"]) == []  # 后缀不在扫描清单


def test_dangling_refs_rstrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    monkeypatch.setattr(h, "REPO", repo)
    punct = repo / "docs" / "punct.md"
    punct.write_text("docs/a.md。 docs/a.md) docs/a.md.\n", encoding="utf-8")
    got = h.dangling_refs(["docs/punct.md"])
    assert got == ["docs/punct.md -> docs/a.md"]  # 三种尾随标点都解析为 docs/a.md 且去重


# --------------------------------------------------------------------- 分母守护


def test_every_target_symbol_is_covered() -> None:
    """覆盖分母守护（派单文 §3）：TARGETS 钉死 12 个符号，逐个必须在 test_ 函数体内出现。

    正向对照（a）：往 TARGETS 的 tmp 副本里塞一个未覆盖符号名，本守护必须红。
    """
    assert len(TARGETS) == 12  # 分母钉死，防 TARGETS 被清空导致 vacuous green
    src = Path(__file__).resolve().read_text(encoding="utf-8")
    bodies = _test_body_text(src)
    assert bodies, "未扫到任何 test_ 函数体（glob 扫空类陷阱）"
    for name in sorted(TARGETS):
        assert name in bodies, f"符号 {name} 在任何 test_ 函数体内都未出现"


# ------------------------------------------- D-046：冻结树导入隔离（R16 根治的回归守护）


def test_frozen_env_pins_pythonpath_and_mypypath_to_tree_src(tmp_path: Path) -> None:
    """``frozen_env`` 必须把**冻结树自己的** src 钉进 PYTHONPATH / MYPYPATH。

    这是 D-046 的根治点：editable ``.pth`` 写死了活动仓库 src 的绝对路径，
    只有 PYTHONPATH 先于 site 阶段入 ``sys.path`` 才能夺回解析权。
    第二断言钉住「对真实工作树恒等」——本函数不得改变 REPO 口径的既有行为。
    """
    env = h.frozen_env(tmp_path)
    assert env == {"PYTHONPATH": str(tmp_path / "src"), "MYPYPATH": str(tmp_path / "src")}
    assert sorted(env) == ["MYPYPATH", "PYTHONPATH"]
    assert h.frozen_env(h.REPO)["PYTHONPATH"] == str(h.REPO / "src")


def test_run_gates_passes_frozen_env_to_every_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """四门**逐门**必须带 ``env=frozen_env(tree)``；少一门即红（防 D-046 回归）。

    阳性对照（本用例自身的牙）：把 ``run_gates`` 里任意一处的 ``env=env`` 去掉，
    下方 ``all(... env == want)`` 立即判红；把 ``frozen_env`` 改成返回空 dict 同样判红。
    纯 monkeypatch，不起子进程、不跑工具链（守本文件「纯单元测试」纪律）。
    """
    calls: list[tuple[tuple[str, ...], Any, Any]] = []

    def fake_sh(args: Any, cwd: Any = None, env: Any = None) -> Any:
        calls.append((tuple(args), cwd, env))
        return h.Proc(0, "1 passed", "")

    monkeypatch.setattr(h, "sh", fake_sh)
    tree = tmp_path / "tree"
    (tree / "src").mkdir(parents=True)
    gates = h.run_gates(tree)
    assert sorted(gates) == ["mypy", "pytest_frozen", "ruff_check", "ruff_format"]
    assert len(calls) == 4, f"四门应各调一次 sh，实测 {len(calls)}"
    want = {"PYTHONPATH": str(tree / "src"), "MYPYPATH": str(tree / "src")}
    for args, cwd, env in calls:
        assert cwd == tree, args
        assert env == want, args


def test_count_git_env_ignores_passes_frozen_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """静态收集补回分母时同样必须隔离导入，否则收集数也可能来自活动树（D-046 同型）。"""
    seen: list[tuple[Any, Any]] = []

    def fake_sh(args: Any, cwd: Any = None, env: Any = None) -> Any:
        seen.append((cwd, env))
        return h.Proc(0, "2 tests collected", "")

    monkeypatch.setattr(h, "sh", fake_sh)
    tree = tmp_path / "tree"
    (tree / "src").mkdir(parents=True)
    for rel in h.GIT_ENV_IGNORES:
        target = tree / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    total = h.count_git_env_ignores(tree)
    assert total == 2 * len(h.GIT_ENV_IGNORES)
    want = {"PYTHONPATH": str(tree / "src"), "MYPYPATH": str(tree / "src")}
    assert seen, "collect-only 一次都没调"
    assert all(cwd == tree and env == want for cwd, env in seen)
