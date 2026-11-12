#!/usr/bin/env python3
"""按任务生成契约切片，避免把大文件整份读入子智能体上下文。

用法:
  python3 scripts/contract_slice.py --ops exchangeSession,getSession --ac AC-001,AC-034 \
      --ui UI-01 --tables workspaces,audit --out orchestrator/handoff/slice.json
只依赖标准库。openapi.json 420KB 由本脚本定点抽取，绝不整份进上下文。

D-001 修复记录：参考 DDL 的 28 张表全部以 ") STRICT;" 结尾，旧正则找 "\n);"
永不匹配，导致 --tables 静默返回 NOT_FOUND。现兼容任意 ) <选项>; 结尾。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

SPEC = Path("spec/CampaignLab-SDD-v1.0")
Json = dict[str, Any]

# ) 后可跟 STRICT / WITHOUT ROWID 等表选项，再到分号
TABLE_TAIL = r"[\s\S]*?\n\)[^;]*;"
INDEX_HINT = r"CREATE (UNIQUE )?INDEX.*ON "
AC_ROW = r"^\|\s*(AC-\d+)\s*\|"


def load(path: Path) -> Json:
    return cast(Json, json.loads(path.read_text(encoding="utf-8")))


def table_head(name: str) -> str:
    return r"CREATE TABLE(?: IF NOT EXISTS)?" + r"[\s" + chr(34) + r"]+" + re.escape(name)


def refs_of(node: Any, bag: Json, schemas: Json, depth: int, cap: int) -> None:
    """把 $ref 指向的组件就地展开，最多 cap 层，防止整份 components 被拉进来。"""
    if depth > cap:
        return
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref.rsplit("/", 1)[-1]
            if name not in bag:
                bag[name] = "TRUNCATED" if depth == cap else {}
                if depth < cap:
                    sub = json.loads(json.dumps(schemas.get(name, {})))
                    bag[name] = sub
                    refs_of(sub, bag, schemas, depth + 1, cap)
            node.clear()
            node["$schema"] = name
        for child in list(node.values()):
            refs_of(child, bag, schemas, depth, cap)
    elif isinstance(node, list):
        for child in node:
            refs_of(child, bag, schemas, depth, cap)


def slice_ops(op_ids: list[str], cap: int) -> Json:
    """按 operationId 抽取 path/方法/操作体，并就地展开引用组件。"""
    api = load(SPEC / "contracts/openapi.json")
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
        refs_of(op, bag, schemas, 1, cap)
        entry: Json = {"method": meth.upper(), "path": path, "operation": op}
        if bag:
            entry["schemas"] = bag
        out[oid] = entry
    return out


def slice_ac(ac_ids: set[str]) -> Json:
    """抽取验收行原文，禁止转述（任务卡必须引用原句）。"""
    text = (SPEC / "qa/ACCEPTANCE.md").read_text(encoding="utf-8")
    rows: Json = {}
    for line in text.splitlines():
        m = re.match(AC_ROW, line)
        if m is not None and m.group(1) in ac_ids:
            rows[m.group(1)] = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return rows


def slice_pages(page_ids: set[str]) -> Json:
    pages = cast(list[Json], load(SPEC / "contracts/pages.json"))
    out: Json = {}
    for pg in pages:
        pid = str(pg["id"])
        if pid in page_ids:
            md = (SPEC / str(pg["path"])).read_text(encoding="utf-8")
            out[pid] = {"meta": pg, "markdown_lines": md.count(chr(10)) + 1, "markdown": md}
    return out


def slice_tables(tables: list[str]) -> Json:
    sql = (SPEC / "contracts/sqlite-v1.sql").read_text(encoding="utf-8")
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
    sql = (SPEC / "contracts/sqlite-v1.sql").read_text(encoding="utf-8")
    return re.findall(
        r"CREATE TABLE(?: IF NOT EXISTS)?[\s" + chr(34) + r"]+([a-z_][a-z0-9_]*)", sql, re.I
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", default="")
    ap.add_argument("--ac", default="")
    ap.add_argument("--ui", default="")
    ap.add_argument("--tables", default="")
    ap.add_argument("--all-tables", action="store_true", help="抽取参考 DDL 的全部表，用于自检表数")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    bundle: Json = {"spec_version": "1.0.0"}
    if a.ops:
        bundle["operations"] = slice_ops(list(str(a.ops).split(",")), int(a.depth))
    if a.ac:
        bundle["acceptance_rows"] = slice_ac(set(str(a.ac).split(",")))
    if a.ui:
        bundle["pages"] = slice_pages(set(str(a.ui).split(",")))
    names = list(str(a.tables).split(",")) if a.tables else []
    if a.all_tables:
        names = all_table_names()
    if names:
        bundle["ddl"] = slice_tables(names)
    txt = json.dumps(bundle, ensure_ascii=False, indent=1)
    if a.out:
        out_path = Path(str(a.out))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(txt, encoding="utf-8")
    not_found = [k for k, v in bundle.get("ddl", {}).items() if v == "NOT_FOUND"]
    stats = (
        f"slice_bytes={len(txt.encode())} slice_lines={txt.count(chr(10))} "
        f"sections={list(bundle)} ddl_not_found={not_found}"
    )
    print(stats, file=sys.stderr)
    if not_found:
        raise SystemExit(2)
    if not a.out:
        print(txt)


if __name__ == "__main__":
    main()
