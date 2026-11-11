#!/usr/bin/env python3
"""按任务生成契约切片，避免把大文件整份读入子智能体上下文。

用法:
  python3 scripts/contract_slice.py --ops exchangeSession,getSession --ac AC-001,AC-034 \\
      --ui UI-01 --tables workspaces,sessions --out orchestrator/handoff/slice.json
只依赖标准库。openapi.json 420KB 由本脚本定点抽取，绝不整份进上下文。
"""
import argparse, json, re, sys
from pathlib import Path

SPEC = Path("spec/CampaignLab-SDD-v1.0")


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def refs_of(node, bag, schemas, depth, cap):
    """把 $ref 指向的组件就地展开，最多 cap 层，防止整份 components 被拉进来。"""
    if depth > cap:
        return
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str) and node["$ref"].startswith("#/components/schemas/"):
            name = node["$ref"].rsplit("/", 1)[-1]
            if name not in bag:
                bag[name] = "TRUNCATED" if depth == cap else {}
                if depth < cap:
                    sub = json.loads(json.dumps(schemas.get(name, {})))
                    bag[name] = sub
                    refs_of(sub, bag, schemas, depth + 1, cap)
            node.clear()
            node["$schema"] = name
        for v in list(node.values()):
            refs_of(v, bag, schemas, depth, cap)
    elif isinstance(node, list):
        for v in node:
            refs_of(v, bag, schemas, depth, cap)


def slice_ops(op_ids, cap):
    api = load(SPEC / "contracts/openapi.json")
    schemas = api.get("components", {}).get("schemas", {})
    out = {}
    for oid in op_ids:
        found = None
        for path, item in api.get("paths", {}).items():
            for meth, op in item.items():
                if isinstance(op, dict) and op.get("operationId") == oid:
                    found = (path, meth, op)
                    break
            if found:
                break
        if not found:
            out[oid] = "NOT_FOUND"
            continue
        path, meth, op = found
        op = json.loads(json.dumps(op))
        bag = {}
        refs_of(op, bag, schemas, 1, cap)
        out[oid] = {"method": meth.upper(), "path": path, "operation": op}
        if bag:
            out[oid]["schemas"] = bag
    return out


def slice_ac(ac_ids):
    text = (SPEC / "qa/ACCEPTANCE.md").read_text(encoding="utf-8")
    rows = {}
    for line in text.splitlines():
        m = re.match(r"^\|\s*(AC-\d+)\s*\|", line)
        if m and m.group(1) in ac_ids:
            rows[m.group(1)] = [c.strip() for c in line.strip().strip("|").split("|")]
    return rows


def slice_pages(page_ids):
    pages = load(SPEC / "contracts/pages.json")
    out = {}
    for pg in pages:
        if pg["id"] in page_ids:
            md = (SPEC / pg["path"]).read_text(encoding="utf-8")
            out[pg["id"]] = {"meta": pg, "markdown_lines": md.count("\n") + 1, "markdown": md}
    return out


def slice_tables(tables):
    sql = (SPEC / "contracts/sqlite-v1.sql").read_text(encoding="utf-8")
    out = {}
    for name in tables:
        m = re.search(r"CREATE TABLE(?: IF NOT EXISTS)?[\s\"]+" + re.escape(name) + r"[\s\S]*?\n\);", sql, re.I)
        out[name] = m.group(0) if m else "NOT_FOUND"
        idx = [l.strip() for l in sql.splitlines() if re.search(r"CREATE (UNIQUE )?INDEX.*ON " + re.escape(name) + r"\b", l, re.I)]
        if idx:
            out[name + "__indexes"] = idx
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", default="")
    ap.add_argument("--ac", default="")
    ap.add_argument("--ui", default="")
    ap.add_argument("--tables", default="")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    bundle = {"spec_version": "1.0.0"}
    if a.ops:
        bundle["operations"] = slice_ops(a.ops.split(","), a.depth)
    if a.ac:
        bundle["acceptance_rows"] = slice_ac(set(a.ac.split(",")))
    if a.ui:
        bundle["pages"] = slice_pages(set(a.ui.split(",")))
    if a.tables:
        bundle["ddl"] = slice_tables(a.tables.split(","))
    txt = json.dumps(bundle, ensure_ascii=False, indent=1)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(txt, encoding="utf-8")
    print("slice_bytes=%d slice_lines=%d sections=%s" % (len(txt.encode()), txt.count("\n"), list(bundle)), file=sys.stderr)
    if not a.out:
        print(txt)


if __name__ == "__main__":
    main()
