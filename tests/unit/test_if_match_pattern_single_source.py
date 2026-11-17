"""FU-59 / A271 / D-051 §49 的机器化哨兵：If-Match 正则的**全仓单源**。

本文件钉住三件事，缺一即判红：

1. **契约镜像**：活契约 ``contracts/openapi.json`` 里全部 ``If-Match`` 形参的 schema
   两两逐字同构，且其 ``pattern`` 与 ``api/common.py::IF_MATCH_PATTERN`` **逐字相等**
   ⇒ 常量是契约的镜像而不是第二真源（D-051 §49 的原始要求）。
2. **字面唯一**：该正则字面量在 in-scope Python 源里**只出现 1 次**，且就在
   ``api/common.py`` 的 ``IF_MATCH_PATTERN`` 赋值行 ⇒ 路由层不存在第二份正则。
3. **声明收敛**：凡 ``Header(alias="If-Match", ...)`` 的 ``pattern=`` 实参一律是
   **名字** ``IF_MATCH_PATTERN``（AST 判据），禁内联字符串、禁缺省；并兜住
   「换个 alias 名内联同一正则」的绕过面。

三条判据一律写成**纯函数**（入参＝源文本／契约对象，出参＝违规清单），本文件的阳性对照
（PRE-33 / PRE-34 禁无牙守护）把合成输入喂给**同一个**函数 ⇒ 牙是真牙，不是摆设。

本文件**刻意不直接写出**该正则字面量（以拼接构造），否则判据 2 会被本文件自己打红。
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

import pytest

from campaignlab.api import common

REPO: Final = Path(__file__).resolve().parents[2]
OPENAPI: Final = REPO / "contracts" / "openapi.json"
COMMON_REL: Final = "src/campaignlab/api/common.py"
ACTIVITIES_REL: Final = "src/campaignlab/api/activities.py"
JOBS_REL: Final = "src/campaignlab/api/jobs.py"
RULES_REL: Final = "src/campaignlab/api/rules.py"

#: in-scope Python 的口径与 ``scripts/orch_harness.py::_is_mypy_scope`` 逐字一致：
#: ``src`` / ``tests`` / ``scripts`` 三根，排除 ``spec`` / ``prototype`` / ``web`` / ``.venv``。
IN_SCOPE_ROOTS: Final = ("src", "tests", "scripts")
EXCLUDED_PARTS: Final = frozenset(
    {"__pycache__", ".venv", "node_modules", ".git", "spec", "prototype", "web"}
)

#: 刻意以拼接构造：本文件若直接写出该字面量，判据 2 会被自己打红。
IF_MATCH_LITERAL: Final = '^"[1-9]' + '[0-9]*"$'

#: 契约实测分母（2026-11-17，台账 ``live_openapi_sha16 = 592571099d638251``）：全契约共
#: **16** 个 If-Match 形参、schema 两两逐字同构。活契约是冻结件 ⇒ 分母稳定；若契约变更，
#: 本数字须按 D-012 / D-014 同批归因后更新，禁静默改动。
IF_MATCH_PARAM_COUNT: Final = 16

#: If-Match 形参声明处的**下界**（FU-59 解冻批实测 5：activities 1 ＋ jobs 2 ＋ rules 2）。
#: 取 ``>=`` 而非 ``==``：M1 起还有 11 个 op 要接 If-Match，增长属预期，禁把增长判红。
IF_MATCH_HEADER_SITES_FLOOR: Final = 5


# --------------------------------------------------------------------------- 取源


def in_scope_sources() -> dict[str, str]:
    """in-scope Python 源文本；键＝仓库相对 POSIX 路径。"""
    out: dict[str, str] = {}
    for root in IN_SCOPE_ROOTS:
        base = REPO / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if EXCLUDED_PARTS.intersection(path.parts):
                continue
            out[path.relative_to(REPO).as_posix()] = path.read_text(encoding="utf-8")
    return out


def load_spec() -> dict[str, Any]:
    loaded: Any = json.loads(OPENAPI.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"活契约顶层必须是对象；实测 {type(loaded).__name__}"
    return loaded


# --------------------------------------------------------------------- 判据 1（契约）


def contract_if_match_params(spec: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    """契约里全部 ``If-Match`` 形参，形如 ``[(operationId METHOD path, parameter), ...]``。"""
    out: list[tuple[str, Mapping[str, Any]]] = []
    paths = spec.get("paths")
    if not isinstance(paths, Mapping):
        return out
    for path, item in paths.items():
        if not isinstance(item, Mapping):
            continue
        for method, op in item.items():
            if not isinstance(op, Mapping):
                continue
            params = op.get("parameters")
            if not isinstance(params, Sequence) or isinstance(params, (str, bytes)):
                continue
            for prm in params:
                if isinstance(prm, Mapping) and prm.get("name") == "If-Match":
                    out.append((f"{op.get('operationId')} {str(method).upper()} {path}", prm))
    return out


def contract_offenders(spec: Mapping[str, Any], constant: str) -> list[str]:
    """判据 1 的纯函数形态：返回违规描述清单（空列表＝绿）。"""
    bad: list[str] = []
    params = contract_if_match_params(spec)
    if not params:
        return ["denominator=0：契约里没有任何 If-Match 形参"]
    if len(params) != IF_MATCH_PARAM_COUNT:
        bad.append(f"If-Match 形参数 != {IF_MATCH_PARAM_COUNT}（实测 {len(params)}）")
    shapes = {
        json.dumps(prm.get("schema"), ensure_ascii=False, sort_keys=True) for _, prm in params
    }
    if len(shapes) != 1:
        bad.append(f"schema 不两两同构（实测 {len(shapes)} 种）：{sorted(shapes)}")
    for label, prm in params:
        schema = prm.get("schema")
        pattern = schema.get("pattern") if isinstance(schema, Mapping) else None
        if pattern != constant:
            bad.append(f"{label}: pattern={pattern!r} != 常量 {constant!r}")
    return bad


# --------------------------------------------------------------------- 判据 2（字面）


def scan_literal_sites(sources: Mapping[str, str]) -> list[str]:
    """判据 2 的纯函数形态：逐文件逐行找该正则字面量，返回 ``rel:lineno`` 升序清单。"""
    hits: list[str] = []
    for rel, text in sorted(sources.items()):
        for lineno, line in enumerate(text.splitlines(), 1):
            if IF_MATCH_LITERAL in line:
                hits.append(f"{rel}:{lineno}")
    return hits


# ------------------------------------------------------------------- 判据 3（AST 收敛）


def if_match_header_sites(src: str) -> list[int]:
    """``Header(alias="If-Match", ...)`` 的出现行号（不限 pattern 是否合规）。"""
    sites: list[int] = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name: str | None = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name != "Header":
            continue
        alias = next((kw.value for kw in node.keywords if kw.arg == "alias"), None)
        if isinstance(alias, ast.Constant) and alias.value == "If-Match":
            sites.append(node.lineno)
    return sites


def header_offenders(src: str) -> list[str]:
    """判据 3 的纯函数形态（AST）：If-Match 形参的 ``pattern=`` 必须是名字常量。

    另兜一条绕过面：任何 ``pattern=`` 实参若是与本正则逐字相同的字符串常量（哪怕 alias
    换了名字），一律记违规 —— 否则「不改 alias、只把常量抄回字面量」就能静默绕过判据 3。
    """
    bad: list[str] = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name: str | None = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        pat_kw = next((kw for kw in node.keywords if kw.arg == "pattern"), None)
        if (
            pat_kw is not None
            and isinstance(pat_kw.value, ast.Constant)
            and pat_kw.value.value == IF_MATCH_LITERAL
        ):
            bad.append(f"line {node.lineno}: pattern= 是内联字面量（第二份正则）")
        if name != "Header":
            continue
        alias = next((kw.value for kw in node.keywords if kw.arg == "alias"), None)
        if not (isinstance(alias, ast.Constant) and alias.value == "If-Match"):
            continue
        if pat_kw is None:
            bad.append(f"line {node.lineno}: If-Match 形参缺 pattern= 声明")
        elif not (isinstance(pat_kw.value, ast.Name) and pat_kw.value.id == "IF_MATCH_PATTERN"):
            bad.append(f"line {node.lineno}: pattern= 不是名字 IF_MATCH_PATTERN")
    return bad


# --------------------------------------------------------------------------- 用例


def test_contract_if_match_shape_mirrors_the_constant() -> None:
    """判据 1：契约 16 个 If-Match 形参两两同构，且 pattern 逐字等于 ``IF_MATCH_PATTERN``。"""
    assert contract_offenders(load_spec(), common.IF_MATCH_PATTERN) == []


def test_constant_is_exported_and_dual_to_etag() -> None:
    """常量在 ``__all__`` 里、值逐字等于契约 pattern，且与 ``etag()`` 互为对偶。"""
    assert "IF_MATCH_PATTERN" in common.__all__
    assert common.IF_MATCH_PATTERN == IF_MATCH_LITERAL
    assert re.fullmatch(common.IF_MATCH_PATTERN, common.etag(7)) is not None
    assert re.fullmatch(common.IF_MATCH_PATTERN, common.etag(0)) is None, (
        "revision 0 非法（无前导零）"
    )
    assert re.fullmatch(common.IF_MATCH_PATTERN, "7") is None, "缺双引号必须不匹配"


def test_literal_appears_exactly_once_in_scope_python() -> None:
    """判据 2：全仓 in-scope Python 里该字面量只出现 1 次，且就是 common.py 的赋值行。"""
    sources = in_scope_sources()
    assert COMMON_REL in sources, f"denominator=0：in-scope 扫描没覆盖到 {COMMON_REL}"
    hits = scan_literal_sites(sources)
    assert len(hits) == 1, f"该正则必须全仓单源，实测命中：{hits}"
    rel, _, raw_lineno = hits[0].partition(":")
    assert rel == COMMON_REL, f"唯一出处必须是 {COMMON_REL}，实测 {rel}"
    line = sources[rel].splitlines()[int(raw_lineno) - 1]
    assert line.startswith("IF_MATCH_PATTERN:"), f"唯一出处必须是常量赋值行，实测：{line!r}"


def test_every_if_match_header_uses_the_constant() -> None:
    """判据 3：所有 If-Match 形参声明都用名字常量；三个既有路由文件一个都不许漏。"""
    sources = in_scope_sources()
    bad = {rel: header_offenders(src) for rel, src in sorted(sources.items())}
    bad = {rel: v for rel, v in bad.items() if v}
    assert bad == {}, f"存在未收敛的 If-Match 声明：{bad}"
    sites = {rel: if_match_header_sites(src) for rel, src in sorted(sources.items())}
    sites = {rel: v for rel, v in sites.items() if v}
    total = sum(len(v) for v in sites.values())
    assert total >= IF_MATCH_HEADER_SITES_FLOOR, (
        f"denominator 塌陷：If-Match 形参声明处实测 {total} < 下界 "
        f"{IF_MATCH_HEADER_SITES_FLOOR}（{sites}）"
    )
    assert {ACTIVITIES_REL, JOBS_REL, RULES_REL} <= set(sites), (
        f"三个既有路由文件必须都在扫描面里，实测：{sorted(sites)}"
    )


# ------------------------------------------------------------------- 阳性对照（真牙）


def test_positive_control_a_second_literal_would_be_caught() -> None:
    """阳性对照①：合成第二份字面量喂给判据 2 的同一函数，必须报 2 处（即会判红）。"""
    synth = {
        COMMON_REL: "IF_MATCH_PATTERN: Final = r'" + IF_MATCH_LITERAL + "'\n",
        JOBS_REL: "PATTERN = r'" + IF_MATCH_LITERAL + "'\n",
    }
    assert len(scan_literal_sites(synth)) == 2


def test_positive_control_an_inlined_header_pattern_would_be_caught() -> None:
    """阳性对照②：把 ``pattern=`` 改回内联字面量，判据 3 必须报违规。"""
    synth = (
        "if_match: str | None = Header(\n"
        '    alias="If-Match",\n'
        "    default=None,\n"
        "    min_length=3,\n"
        "    max_length=32,\n"
        "    pattern=r'" + IF_MATCH_LITERAL + "',\n"
        ")\n"
    )
    assert header_offenders(synth) != []


def test_positive_control_a_missing_pattern_would_be_caught() -> None:
    """阳性对照③：If-Match 形参干脆不声明 ``pattern=``，判据 3 同样必须报违规。"""
    synth = 'if_match: str | None = Header(alias="If-Match", default=None)\n'
    assert header_offenders(synth) != []


def test_positive_control_contract_drift_would_be_caught() -> None:
    """阳性对照④：把契约里任一个 pattern 改掉（只在内存副本上），判据 1 必须报违规。"""
    spec = load_spec()
    params = contract_if_match_params(spec)
    assert params, "denominator=0：契约里没有 If-Match 形参，阳性对照无从构造"
    label, prm = params[0]
    schema = prm.get("schema")
    assert isinstance(schema, dict), f"{label} 的 schema 不是对象，阳性对照无从构造"
    schema["pattern"] = str(schema["pattern"]) + "-DRIFT"
    assert contract_offenders(spec, common.IF_MATCH_PATTERN) != []


def test_positive_control_contract_count_drift_would_be_caught() -> None:
    """阳性对照⑤：从契约里摘掉一个 If-Match 形参（内存副本），分母判据必须报违规。"""
    spec = load_spec()
    paths = spec["paths"]
    assert isinstance(paths, dict)
    for item in paths.values():
        if not isinstance(item, dict):
            continue
        for op in item.values():
            if not isinstance(op, dict) or not isinstance(op.get("parameters"), list):
                continue
            before = len(op["parameters"])
            op["parameters"] = [
                p
                for p in op["parameters"]
                if not (isinstance(p, dict) and p.get("name") == "If-Match")
            ]
            if len(op["parameters"]) != before:
                assert contract_offenders(spec, common.IF_MATCH_PATTERN) != []
                return
    pytest.fail("denominator=0：没能从契约里摘掉任何一个 If-Match 形参，阳性对照失效")


# ------------------------------------------------------- 判据 4（同族钉桩禁静默分叉）

#: **A292 口径迁移（订正 A281）**：本判据原为「同族钉桩整数两两相等且处数 >= 下界 2」的**下界制**，
#: 与 **A115**（禁写死符号面计数）**不可兼得** —— 全仓
#: ``len(<common 别名>.__all__) == <整数>`` 形态的
#: 硬编码计数钉桩实测**只有 2 处**、恰是 ``tests/unit/test_domain_errors.py:176/:177``，
#: 去掉魔数即「分母塌陷」判红、保留魔数即违 A115（A281 的 ``fact`` 称「保留一处即可满足下界」，
#: 实测不成立：保留一处 ⇒ 处数 1 < 下界 2，仍判红）。故迁移为：
#:   · **上限制**：硬编码计数钉桩处数 <= ``ALL_COUNT_PIN_SITES_CEILING``（＝ 0，A115 机器化）；
#:   · **下界制**（保留原有的牙）：带 ``LIVE_COLLISION_MARKER`` 的实取对撞守护处数 >=
#:     ``LIVE_COLLISION_SITES_FLOOR``（＝ 1）⇒ **禁靠删守护变绿**，与原下界制的立法意图一致。
#: **R19-10 的教训依然成立**且被更强地满足：名单对撞是**全仓单点**，不存在「多处各写一份、
#: 只改了自己扫到的那一处」的分叉面。
ALL_COUNT_PIN_RE: Final = re.compile(
    r"len\((?:set\()?(?P<obj>[A-Za-z_][\w.]*)\.__all__\)\)?\s*==\s*(?P<n>\d+)"
)
COMMON_ALIASES: Final = frozenset({"common", "common_module"})
ALL_COUNT_PIN_SITES_CEILING: Final = 0

#: 刻意以拼接构造：本文件若直接写出完整标记串，``live_collision_sites`` 会把自己扫成守护位点
#: （自指 ⇒ 下界制失去牙：删掉 ``test_domain_errors.py`` 里的真守护也不会判红）。
LIVE_COLLISION_MARKER: Final = "common-surface-live" + "-collision"
LIVE_COLLISION_SITES_FLOOR: Final = 1


def all_count_pins(sources: Mapping[str, str]) -> list[tuple[str, int, str, int]]:
    """扫出 ``(rel, lineno, 别名, 钉住的整数)`` 清单（只认 common 的别名）。"""
    out: list[tuple[str, int, str, int]] = []
    for rel, text in sorted(sources.items()):
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in ALL_COUNT_PIN_RE.finditer(line):
                alias = match.group("obj").rpartition(".")[2]
                if alias in COMMON_ALIASES:
                    out.append((rel, lineno, alias, int(match.group("n"))))
    return out


def live_collision_sites(sources: Mapping[str, str]) -> list[tuple[str, int]]:
    """扫出带 ``LIVE_COLLISION_MARKER`` 的行 ＝ 替代硬编码计数钉桩的**实取对撞**守护位点。"""
    out: list[tuple[str, int]] = []
    for rel, text in sorted(sources.items()):
        for lineno, line in enumerate(text.splitlines(), 1):
            if LIVE_COLLISION_MARKER in line:
                out.append((rel, lineno))
    return out


def test_all_common_surface_pins_agree_with_runtime() -> None:
    """判据 4（A292 迁移后）：全仓零硬编码计数钉桩 ＋ 至少 1 处实取对撞守护 ＋ 名单本身自洽。

    函数名沿用历史（D-044 体例：名称变更会打断 ``tests/integration/jobs/test_jobs_router_s4.py:346``
    的交叉引用），语义已由「钉桩整数两两相等」升级为「禁钉桩 ＋ 必须有实取对撞守护」。
    """
    sources = in_scope_sources()
    pins = all_count_pins(sources)
    assert len(pins) <= ALL_COUNT_PIN_SITES_CEILING, (
        f"A115 违规：仍有 {len(pins)} 处硬编码公开面计数钉桩（{pins}）—— "
        "公开面计数一律改为实取对撞（A292），禁写死"
    )
    sites = live_collision_sites(sources)
    assert len(sites) >= LIVE_COLLISION_SITES_FLOOR, (
        f"denominator 塌陷：实取对撞守护实测 {len(sites)} 处 < 下界 "
        f"{LIVE_COLLISION_SITES_FLOOR} —— 禁靠删守护变绿"
    )
    assert len(set(common.__all__)) == len(common.__all__), "common.__all__ 内有重复声明"


def test_positive_control_a_stale_all_count_pin_would_be_caught() -> None:
    """阳性对照⑥（A292 迁移后）：合成一处硬编码计数钉桩喂给判据 4 的**同一函数**，必须被扫出来。

    合成串刻意用拼接构造（``== `` 之后接 ``"79"``），否则本行自己就会被上限判据扫成钉桩。
    同批配**阴性对照**：不含标记串的源里不得扫出任何实取对撞位点（防「恒判有」型假牙）。
    """
    synth = {"tests/unit/test_synth.py": "    assert len(common.__all__) == " + "79\n"}
    pins = all_count_pins(synth)
    assert pins == [("tests/unit/test_synth.py", 1, "common", 79)]
    assert len(pins) > ALL_COUNT_PIN_SITES_CEILING, "上限判据无牙：合成钉桩未被判为违规"
    assert live_collision_sites({"tests/unit/test_synth.py": "x = 1\n"}) == [], (
        "阴性对照失效：不含标记串的源被扫出了实取对撞位点"
    )
    assert live_collision_sites(synth) == [], "阴性对照失效：钉桩串被误认为对撞守护"
