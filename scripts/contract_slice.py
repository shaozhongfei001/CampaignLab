#!/usr/bin/env python3
"""按任务生成契约切片，避免把大文件整份读入子智能体上下文。

用法:
  python3 scripts/contract_slice.py --ops exchangeSession,getSession --ac AC-001,AC-034 \
      --ui UI-01 --tables workspaces,audit --out orchestrator/handoff/slice.json
只依赖标准库。活契约 openapi.json 443KB 由本脚本定点抽取，绝不整份进上下文。
必须从仓库根目录运行（路径为 cwd 相对，与既有单测约定一致）。

数据源（D-004 修复后）:
  LIVE  = contracts/                                活契约，**实现唯一依据**（手册第 7 节）
  BASE  = spec/CampaignLab-SDD-v1.0/                不可变基线，仅供活契约中不存在的只读原件
                                                    （qa/ACCEPTANCE.md、ui/*.md）
  DELTA = spec/CampaignLab-SDD-Patch-v1.0.1-.../    月报增量，供 AC-MR-01..12 原文行（D-005）
  spec_version 从 LIVE/openapi.json 的 info.version **动态读取**，禁止硬编码；
  输出附 source 段（来源路径 + openapi 字节数与 sha256 前 16），使上下文包可追溯来源字节。

D-001 修复记录：参考 DDL 的 28 张表全部以 ") STRICT;" 结尾，旧正则找 "\n);"
永不匹配，导致 --tables 静默返回 NOT_FOUND。现兼容任意 ) <选项>; 结尾。

D-004 修复记录：此前 openapi / pages / DDL 全部只读 BASE，且 spec_version 硬编码 "1.0.0"。
活契约升到 1.0.1 后，切片会**静默提供过期契约**（rc=0，无任何提示）。现改读 LIVE 并动态取版本。

D-005 修复记录：AC_ROW 原为 ^\\|\\s*(AC-\\d+)\\s*\\|，既不匹配 AC-MR-<n>（月报行首单元格还带标题），
也不读月报追加清单；而 slice_ac 只返回命中的行、未命中不报错 —— 5 个 P 任务共 30 处 AC-MR
引用会**静默得到空的验收上下文**。现扩展正则为 AC-(?:MR-)?\\d+ 且允许单元格内带标题，
并读取 DELTA 的追加清单；任何请求目标未命中一律 rc=2。

静默失效防护（手册 13.3 / 15.4）：--ops / --ac / --ui / --tables 中任一目标未命中，
一律 rc=2，禁止返回 NOT_FOUND 或空字典后 rc=0；且**校验通过后才写出文件**，
未命中时不产生任何切片产物，避免坏上下文被派发。

D-020 修复记录：--depth 默认 2 时，depth==cap 的组件被写成 "TRUNCATED"，7 份**已派发**切片
共 45 处被截断（M0-02:1 / M0-03:1 / M0-04:7 / M3-01:8 / M3-02:8 / M3-03:11 / M4-01:9），
且被截断的正是 Problem / ObjectRef / Issue / Job 这类核心 schema —— lane 只能回读 443KB
活契约，M0-04/S1 因此超支 11k token。现三处修死：
  ① 默认 --depth 由 2 提到 5（实测 depth=6 与 depth=5 产出字节数相同，故 5 即足够；
     5 层展开后 45 处 TRUNCATED 全部归零，切片仍仅为活契约的 8–11%）；
  ② 输出顶层恒有 truncated_schemas 清单（无截断时为 []），使消费方可断言；
  ③ 清单非空一律 rc=2 且不写出文件，令截断不可能再次静默发生。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

LIVE = Path("contracts")
BASE = Path("spec/CampaignLab-SDD-v1.0")
DELTA = Path("spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta")
ACCEPTANCE_SOURCES: tuple[Path, ...] = (
    BASE / "qa/ACCEPTANCE.md",
    DELTA / "qa/CampaignLab-Review-Acceptance-Checklist.append.md",
)
Json = dict[str, Any]

# ) 后可跟 STRICT / WITHOUT ROWID 等表选项，再到分号
TABLE_TAIL = r"[\s\S]*?\n\)[^;]*;"
INDEX_HINT = r"CREATE (UNIQUE )?INDEX.*ON "
# AC-001 与 AC-MR-01 都要匹配；月报清单首单元格形如 "AC-MR-01 标准接入"，故允许尾部标题
AC_ROW = r"^\|\s*(AC-(?:MR-)?\d+)\b[^|]*\|"

# D-020：组件展开达到 cap 层仍未展开时写入该哨兵。哨兵**不得被静默吞掉**——
# main 会把 truncated_schemas 非空转成 rc=2，理由见模块 docstring 的 D-020 修复记录。
TRUNCATED_SENTINEL = "TRUNCATED"
# 实测 depth=6 与 depth=5 产出字节数完全相同，故 5 层已覆盖活契约的最深 $ref 链。
DEFAULT_DEPTH = 5


def load(path: Path) -> Json:
    return cast(Json, json.loads(path.read_text(encoding="utf-8")))


def sha16(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()[:16]


def live_spec_version() -> str:
    """从活契约读取 info.version；缺失即 rc=2，禁止回退到硬编码值。"""
    openapi = LIVE / "openapi.json"
    if not openapi.exists():
        print(f"FAIL 活契约缺失: {openapi}", file=sys.stderr)
        raise SystemExit(2)
    info = load(openapi).get("info") or {}
    version = info.get("version")
    if not isinstance(version, str) or not version:
        print(f"FAIL 活契约 info.version 缺失或非法: {openapi}", file=sys.stderr)
        raise SystemExit(2)
    return version


def source_block() -> Json:
    """把数据来源写进切片，使上下文包可追溯到具体字节。"""
    openapi = LIVE / "openapi.json"
    return {
        "live_contracts": str(LIVE),
        "openapi": {
            "path": str(openapi),
            "bytes": openapi.stat().st_size,
            "sha16": sha16(openapi),
        },
        "readonly_originals": str(BASE),
        "monthly_delta": str(DELTA),
        "rule": (
            "活契约 contracts/ 是实现唯一依据（手册第 7 节）；BASE 仅供活契约中不存在的只读原件"
            "（qa/ACCEPTANCE.md、ui/*.md）；spec_version 从活契约 info.version 动态读取，禁止硬编码。"
        ),
    }


def table_head(name: str) -> str:
    return r"CREATE TABLE(?: IF NOT EXISTS)?" + r"[\s" + chr(34) + r"]+" + re.escape(name)


def refs_of(
    node: Any,
    bag: Json,
    schemas: Json,
    depth: int,
    cap: int,
    truncated: set[str] | None = None,
) -> None:
    """把 $ref 指向的组件就地展开，最多 cap 层，防止整份 components 被拉进来。

    达到 cap 层仍未展开的组件写入 ``TRUNCATED_SENTINEL`` 并登记进 ``truncated``。
    登记项由 ``main`` 转成 rc=2（D-020）：一条不响的守卫等于没有守卫。
    ``truncated`` 为 ``None`` 时退化为旧行为，供只想探测不想收集的调用方使用。
    """
    if depth > cap:
        return
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref.rsplit("/", 1)[-1]
            if name not in bag:
                if depth == cap:
                    bag[name] = TRUNCATED_SENTINEL
                    if truncated is not None:
                        truncated.add(name)
                else:
                    sub = json.loads(json.dumps(schemas.get(name, {})))
                    bag[name] = sub
                    refs_of(sub, bag, schemas, depth + 1, cap, truncated)
            node.clear()
            node["$schema"] = name
        for child in list(node.values()):
            refs_of(child, bag, schemas, depth, cap, truncated)
    elif isinstance(node, list):
        for child in node:
            refs_of(child, bag, schemas, depth, cap, truncated)


def slice_ops(op_ids: list[str], cap: int, truncated: set[str] | None = None) -> Json:
    """按 operationId 从**活契约**抽取 path/方法/操作体，并就地展开引用组件。

    ``truncated`` 用于回收 ``refs_of`` 登记的被截断组件名（D-020）。
    """
    api = load(LIVE / "openapi.json")
    components = cast(Json, api.get("components") or {})
    schemas = cast(Json, components.get("schemas") or {})
    paths = cast(Json, api.get("paths") or {})
    out: Json = {}
    for oid in op_ids:
        found: tuple[str, str, Json] | None = None
        for path, item in paths.items():
            if not isinstance(item, dict):
                continue
            for meth, op in item.items():
                if isinstance(op, dict) and op.get("operationId") == oid:
                    found = (str(path), str(meth), cast(Json, op))
                    break
            if found is not None:
                break
        if found is None:
            out[oid] = "NOT_FOUND"
            continue
        path, meth, op = found
        op = json.loads(json.dumps(op))
        bag: Json = {}
        refs_of(op, bag, schemas, 1, cap, truncated)
        entry: Json = {"method": meth.upper(), "path": path, "operation": op}
        if bag:
            entry["schemas"] = bag
        out[oid] = entry
    return out


def slice_ac(ac_ids: set[str]) -> Json:
    """抽取验收行原文，禁止转述。同时覆盖基线 AC-001..035 与月报 AC-MR-01..12。"""
    rows: Json = {}
    for src in ACCEPTANCE_SOURCES:
        if not src.exists():
            continue
        text = src.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(AC_ROW, line)
            if m is not None and m.group(1) in ac_ids and m.group(1) not in rows:
                rows[m.group(1)] = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return rows


def slice_pages(page_ids: set[str]) -> Json:
    """页号索引取活契约 pages.json；页面 markdown 原件仍只在 BASE/ui/ 下。"""
    pages = cast(list[Json], load(LIVE / "pages.json"))
    out: Json = {}
    for pg in pages:
        pid = str(pg["id"])
        if pid in page_ids:
            md = (BASE / str(pg["path"])).read_text(encoding="utf-8")
            out[pid] = {"meta": pg, "markdown_lines": md.count(chr(10)) + 1, "markdown": md}
    return out


def slice_tables(tables: list[str]) -> Json:
    sql = (LIVE / "sqlite-v1.sql").read_text(encoding="utf-8")
    out: Json = {}
    for name in tables:
        m = re.search(table_head(name) + TABLE_TAIL, sql, re.I)
        out[name] = m.group(0) if m is not None else "NOT_FOUND"
        idx = [
            raw.strip()
            for raw in sql.splitlines()
            if re.search(INDEX_HINT + re.escape(name) + r"\b", raw, re.I)
        ]
        if idx:
            out[name + "__indexes"] = idx
    return out


def all_table_names() -> list[str]:
    sql = (LIVE / "sqlite-v1.sql").read_text(encoding="utf-8")
    return re.findall(
        r"CREATE TABLE(?: IF NOT EXISTS)?[\s" + chr(34) + r"]+([a-z_][a-z0-9_]*)", sql, re.I
    )


def missing_targets(requested: Json, bundle: Json) -> Json:
    """比对请求目标与切片结果，返回各 section 的未命中清单。

    这是「分母断言」的实现：任何请求了却没切到的目标都必须被检出，由 main 转成 rc=2。
    NOT_FOUND 哨兵与「键根本不存在」两种形态都算未命中。
    """
    out: Json = {}
    for section, ids in requested.items():
        got = bundle.get(section)
        if not ids or not isinstance(got, dict):
            if ids:
                out[str(section)] = [str(i) for i in ids]
            continue
        miss = [str(i) for i in ids if got.get(str(i)) in (None, "NOT_FOUND")]
        if miss:
            out[str(section)] = miss
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", default="")
    ap.add_argument("--ac", default="")
    ap.add_argument("--ui", default="")
    ap.add_argument("--tables", default="")
    ap.add_argument("--all-tables", action="store_true", help="抽取参考 DDL 的全部表，用于自检表数")
    ap.add_argument("--depth", type=int, default=DEFAULT_DEPTH)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    bundle: Json = {"spec_version": live_spec_version(), "source": source_block()}
    requested: Json = {}
    truncated: set[str] = set()

    if a.ops:
        ids = [x.strip() for x in str(a.ops).split(",") if x.strip()]
        bundle["operations"] = slice_ops(ids, int(a.depth), truncated)
        requested["operations"] = ids
    if a.ac:
        ids = sorted({x.strip() for x in str(a.ac).split(",") if x.strip()})
        bundle["acceptance_rows"] = slice_ac(set(ids))
        requested["acceptance_rows"] = ids
    if a.ui:
        ids = [x.strip() for x in str(a.ui).split(",") if x.strip()]
        bundle["pages"] = slice_pages(set(ids))
        requested["pages"] = ids
    names = [x.strip() for x in str(a.tables).split(",") if x.strip()] if a.tables else []
    if a.all_tables:
        names = all_table_names()
    if names:
        bundle["ddl"] = slice_tables(names)
        requested["ddl"] = names

    bundle["truncated_schemas"] = sorted(truncated)

    txt = json.dumps(bundle, ensure_ascii=False, indent=1)
    missing = missing_targets(requested, bundle)
    flat = [f"{sec}:{i}" for sec, items in missing.items() for i in cast(list[str], items)]
    stats = (
        f"spec_version={bundle['spec_version']} slice_bytes={len(txt.encode())} "
        f"slice_lines={txt.count(chr(10))} sections={list(bundle)} missing={flat} "
        f"depth={int(a.depth)} truncated_schemas={bundle['truncated_schemas']}"
    )
    print(stats, file=sys.stderr)
    if flat:
        print(f"FAIL 切片目标未命中（禁止静默，见手册 13.3/15.4）: {flat}", file=sys.stderr)
        raise SystemExit(2)
    if truncated:
        print(
            f"FAIL 组件展开在 depth={int(a.depth)} 处被截断（禁止静默，见 D-020）: "
            f"{sorted(truncated)}。请提高 --depth（默认 {DEFAULT_DEPTH}；实测 depth=6 与 5 "
            f"产出字节数相同，5 即足够）。被截断的正是 Problem/Job/ObjectRef 这类核心 "
            f"schema，派发出去会迫使 lane 回读 443KB 活契约，成本与偏差同时失控。",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if a.out:
        out_path = Path(str(a.out))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(txt, encoding="utf-8")
    else:
        print(txt)


if __name__ == "__main__":
    main()
