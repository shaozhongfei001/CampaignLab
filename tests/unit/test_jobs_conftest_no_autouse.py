"""A241 / D-049 ③ 的机器判据：``tests/integration/jobs/conftest.py`` 的 autouse 禁令必须有牙。

背景（编排器实测，非转述）：R17 lane S5 的派单文 §7 PC-4 预言「给 conftest 的任一 fixture 加
``autouse=True`` ⇒ 同目录既有三个测试文件判红」，**实测不成立** —— 两个 autouse 变体
（``migrated_job_db`` / ``http_client``）下既有 65 例全部 rc=0（编排器复跑：该目录 88 passed
== 既有 65 ＋ 本批新增 23）。原因是既有模块各自定义了同名或独立的模块级 fixture（实测遮蔽交集
只有 ``data_dir``），autouse 注入并不改变其行为；派单文 §2.4 的遮蔽说明与 §7 的 PC 预言因此
自相矛盾（D-049 ③）。

后果：若禁令只写在 conftest 的 docstring 里，日后任何人加 autouse 都**不会判红** ⇒ 禁令无牙。
本件由编排器在 S5 入库的同批补齐静态哨兵（沿 R16 / A231 的「同批补判据」先例），三条判据：

1. conftest.py 的 fixture 装饰器里 ``autouse`` 恒为假（AST 实取，禁字符串匹配）；
2. 扫描器**非空自证**（PRE-18：同一份扫描器跑合成 autouse 样本必须能抓到 ⇒ 判据非恒真）；
3. conftest.py 的 9 个 fixture 名集与派单文 §1/§3 的冻结名集**双向差集为空**（A115 口径）。
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFTEST = REPO_ROOT / "tests" / "integration" / "jobs" / "conftest.py"

#: 派单文 R17-lane-M0-04-S5.md §1（:30）与 §3 冻结的 9 个 fixture 名（逐字，禁增删改名）
FROZEN_FIXTURES = frozenset(
    {
        "advance_clock",
        "data_dir",
        "fixed_clock",
        "http_client",
        "idem_key",
        "job_store",
        "migrated_job_db",
        "registry_with_stub",
        "stub_handler",
    }
)

#: PRE-18 的非空自证样本：一个 autouse ＋ 一个普通 fixture，扫描器必须分别报 True / False
_PROBE = (
    "import pytest\n"
    "\n"
    "\n"
    "@pytest.fixture(autouse=True)\n"
    "def leaky():\n"
    "    return None\n"
    "\n"
    "\n"
    "@pytest.fixture\n"
    "def polite():\n"
    "    return None\n"
)


def _fixture_autouse_flags(source: str) -> list[tuple[str, bool]]:
    """AST 实取模块级 fixture 的 ``(名, autouse)`` 序列；非 fixture 的函数一律不入表。"""
    tree = ast.parse(source)
    out: list[tuple[str, bool]] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for dec in node.decorator_list:
            head = dec.func if isinstance(dec, ast.Call) else dec
            if not (isinstance(head, ast.Attribute) and head.attr == "fixture"):
                continue
            autouse = False
            if isinstance(dec, ast.Call):
                for kw in dec.keywords:
                    if kw.arg == "autouse":
                        autouse = bool(ast.literal_eval(kw.value))
            out.append((node.name, autouse))
    return out


def _conftest_flags() -> list[tuple[str, bool]]:
    assert CONFTEST.is_file(), f"denominator=0：找不到 {CONFTEST}，本守护不做静默通过"
    return _fixture_autouse_flags(CONFTEST.read_text(encoding="utf-8"))


def test_jobs_conftest_has_no_autouse_fixture() -> None:
    flags = _conftest_flags()
    assert flags, "denominator=0：conftest.py 里一个 fixture 都没扫到 ⇒ 扫描器失效，禁静默通过"
    leaky = [name for name, autouse in flags if autouse]
    assert leaky == [], (
        "conftest.py 禁 autouse（派单文 §2.4；实测归因见本件 docstring）："
        f"autouse 会强行注入同目录既有用例，实测命中 {leaky}"
    )


def test_autouse_scanner_is_not_vacuous() -> None:
    """反向自证：同一份扫描器在合成样本上必须抓到 autouse（否则上一条判据恒真、等于没有牙）。"""
    got = _fixture_autouse_flags(_PROBE)
    assert got == [("leaky", True), ("polite", False)], got


def test_jobs_conftest_fixture_names_match_the_frozen_nine() -> None:
    names = {name for name, _ in _conftest_flags()}
    extra = sorted(names - FROZEN_FIXTURES)
    missing = sorted(FROZEN_FIXTURES - names)
    assert extra == [], f"出现冻结名集之外的 fixture：{extra}"
    assert missing == [], f"冻结的 9 个 fixture 缺失：{missing}"
    assert len(names) == 9, len(names)
