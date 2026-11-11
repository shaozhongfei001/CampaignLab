"""Offline handoff checks. This script validates contracts and fixture arithmetic."""

from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
CHECKED = []


def data(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def record(description):
    CHECKED.append(description)
    print(f"PASS {description}")


def verify_manifest():
    hashes = {}
    for line in (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        assert re.fullmatch("[0-9a-f]{64}", digest), name
        path = ROOT / name
        assert path.resolve().is_relative_to(ROOT) and path.is_file() and not path.is_symlink(), name
        assert name not in hashes and sha256(path.read_bytes()).hexdigest() == digest, name
        hashes[name] = digest
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
              if p.is_file() and p != ROOT / "SHA256SUMS"}
    assert set(hashes) == actual, (set(hashes)-actual, actual-set(hashes))
    record(f"清单与逐文件 SHA-256 共 {len(hashes)} 项")


def resolve(document, pointer):
    assert pointer.startswith("#/"), pointer
    value = document
    for key in pointer[2:].split("/"):
        value = value[key.replace("~1", "/").replace("~0", "~")]
    return value


def verify_references(value, document):
    if isinstance(value, dict):
        if "$ref" in value:
            assert isinstance(resolve(document, value["$ref"]), dict)
        for child in value.values():
            verify_references(child, document)
    elif isinstance(value, list):
        for child in value:
            verify_references(child, document)


def verify_contracts():
    api = data("contracts/openapi.json")
    assert api["openapi"].startswith("3.1")
    verify_references(api, api)
    ops = {}
    for path, verbs in api["paths"].items():
        for method, op in verbs.items():
            key = op["operationId"]
            assert key not in ops, key
            ops[key] = op
            parameters = {p["name"] for p in op["parameters"] if p["in"] == "path" and p["required"]}
            assert parameters == set(re.findall(r"\{(\w+)\}", path)), (path, parameters)
            assert any(code.startswith("2") for code in op["responses"]), key
    assert set(ops) == {o["id"] for o in data("contracts/operations.json")}
    for entry in data("contracts/operations.json"):
        actual = api["paths"][entry["path"]][entry["method"]]
        assert actual["operationId"] == entry["id"]
        assert str(entry["status"]) in actual["responses"]
    for p in (ROOT/"contracts").glob("*.schema.json"):
        schema = data(p.relative_to(ROOT))
        verify_references(schema, schema)
    record(f"接口和本地 Schema 引用共 {len(ops)} 个操作")

    pages = data("contracts/pages.json")
    acceptance = set(re.findall(r"^\| (AC-\d{3}) \|", (ROOT / "qa/ACCEPTANCE.md").read_text(), re.M))
    ids = {page["id"] for page in pages}
    assert len(pages) == len(ids) == 26
    assert len({page["route"] for page in pages}) == len(pages)
    assert len(acceptance) == 35
    used_ops = set()
    for page in pages:
        content = (ROOT / page["path"]).read_text(encoding="utf-8")
        assert page["route"] in content and page["requirement"] in content
        assert set(page["operation_ids"]) <= set(ops)
        assert set(page["acceptance"]) <= acceptance
        used_ops.update(page["operation_ids"])
        for value in page["operation_ids"] + page["acceptance"]:
            assert value in content, (page["id"],value)
    assert used_ops == set(ops), set(ops) - used_ops
    matrix = data("contracts/traceability.json")
    assert len(matrix["source_points"]) == len({p["id"] for p in matrix["source_points"]}) == 55
    assert len(matrix["manual_points"]) == len({p["id"] for p in matrix["manual_points"]}) == 47
    assert {p["id"] for p in matrix["source_points"] if p["new_status"] == "EVIDENCE_PENDING"} == {"CL33","CL54","CL55"}
    assert Counter(p["legacy_state"] for p in matrix["source_points"]) == {"已测":41,"条件覆盖":11,"待材料":3}
    for row in matrix["source_points"]:
        assert set(row["ui_ids"]) <= ids and set(row["acceptance"]) <= acceptance, row["id"]
    for row in matrix["manual_points"]:
        assert row["ui_id"] in ids and row["acceptance"] in acceptance, row["id"]
    for p in ROOT.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", p.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            linked = (p.parent / target.split("#")[0]).resolve()
            assert linked.is_relative_to(ROOT) and linked.exists(), (p.name, target)
    record("26 个页面、35 个验收用例、55 个材料点位、47 个手册操作点及文档链接")


def verify_database():
    db = sqlite3.connect(":memory:")
    db.executescript((ROOT/"contracts/sqlite-v1.sql").read_text(encoding="utf-8"))
    assert db.execute("PRAGMA foreign_keys").fetchone() == (1,)
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    assert len(tables) >= 20
    for key in ("WS-A","WS-B"):
        db.execute("INSERT INTO workspaces(id,name,source_class,created_at) VALUES(?,?,?,?)",
                   (key,key,"SYNTHETIC","2026-11-12T00:00:00Z"))
    db.execute("""INSERT INTO activities(workspace_id,id,name,description,status,revision,created_at)
                  VALUES('WS-A','ACT-01','Activity','','OPEN',1,'2026-11-12T00:00:00Z')""")
    try:
        db.execute("""INSERT INTO activity_bindings(workspace_id,activity_id,strategy_id,source_version,valid_from,valid_until,evidence_id)
                      VALUES('WS-B','ACT-01','S-1','V1','2026-01-01','2026-12-01','NO-EVIDENCE')""")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("Missing workspace foreign key")
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    db.close()
    record(f"SQLite DDL 可执行，共 {len(tables)} 表，含完整性与外键负例")


STAGES = ["sent","success","executed","contacted","effective"]


def normalize(raw):
    mapping = raw["mapping"]
    source = raw["tables"][mapping["entityTable"]]
    longs = defaultdict(dict)
    if mapping["layout"] == "long":
        records = raw["tables"][mapping["countsTable"]]
        assert len(records["rows"]) == 4590
        for values in records["rows"]:
            row = dict(zip(records["columns"],values,strict=True))
            fields = mapping["longColumns"]
            key, metric, value = (row[fields[k]] for k in ("id","metric","value"))
            assert metric not in longs[key]
            longs[key][metric] = value
    out = []
    for values in source["rows"]:
        row = dict(zip(source["columns"],values,strict=True))
        canonical = {k: mapping["codes"].get(k,{}).get(row[v],row[v]) for k,v in mapping["dimensions"].items()}
        assert canonical["period"] == canonical["cutoff"][:7]
        seen = row if mapping["layout"] == "wide" else longs[canonical["id"]]
        for k,v in mapping["countFields"].items():
            assert type(seen[v]) is int and seen[v] >= 0
            canonical[k] = seen[v]
        levels = [canonical[k] for k in ["eligible",*STAGES]]
        assert levels == sorted(levels,reverse=True)
        for k,v in mapping["moneyFields"].items():
            canonical[k] = None if row[v] is None else int(Decimal(str(row[v])) * 100 / mapping["moneyDivisor"])
        out.append(canonical)
    assert len(out) == len({row["id"] for row in out}) == 510
    if longs:
        assert set(longs) == {row["id"] for row in out}
    return out


def union_count(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["period"],row["cohort"])].append((row["offset"],row["offset"]+row[key]))
    count = 0
    for intervals in groups.values():
        edge = 0
        for start, stop in sorted(intervals):
            count += max(0,stop-max(start,edge))
            edge = max(stop,edge)
    return count


def verify_banks():
    raw_a, raw_b = (data(f"fixtures/banks/bank-{key}.json") for key in ("a","b"))
    a,b = (normalize(x) for x in (raw_a,raw_b))
    golden = data("fixtures/analytics-golden.json")
    select = lambda bank,period,channel: [r for r in bank if (r["period"],r["channel"],r["branch"]) == (period,channel,"B01")]
    current,base = (select(a, month,"remote") for month in ("2026-10","2026-09"))
    assert [union_count(current,k) for k in STAGES] == [12000,11520,8640,3456,1728]
    assert [union_count(base,k) for k in STAGES] == [10000,9600,7680,3840,1920]
    for k in ["eligible",*STAGES]:
        assert union_count(current,k) == union_count(select(b,"2026-10","remote"),k) == int(golden["current"][k])
    aum=sum(r["aum"] for r in current)
    correction=golden["correction"]
    corrected = sum(correction["value_fen"] if r["id"]==correction["slice_id"] else r["aum"] for r in current)
    assert aum == correction["base_total_fen"] == -407400000
    assert corrected == correction["corrected_total_fen"] == -394900000
    rates=lambda rows: [Fraction(union_count(rows,l),union_count(rows,r)) for l,r in zip(STAGES[1:],STAGES)]
    assert Fraction(union_count(current,"effective"),union_count(current,"success")) == Fraction(15,100)
    assert rates(current)[-1] == Fraction(1,2)
    assert union_count(select(a,"2026-11","remote"),"effective") == 1944
    assert Fraction(8640) * Fraction(45,100) * Fraction(1,2) == 1944
    lo = [union_count(base,"sent"),*rates(base)]
    hi = [union_count(current,"sent"),*rates(current)]
    from math import prod
    steps = [prod(hi[:n]+lo[n:]) for n in range(6)]
    assert [y-x for x,y in zip(steps,steps[1:])] == golden["funnel_contributions"]
    assert {r["definition"] for r in select(a,"2026-10","push")} != {r["definition"] for r in select(b,"2026-10","push")}
    assert raw_b["metadata"]["pushDetailSeconds"] == 3
    assert any(r["channel"]=="wechat" and r["period"]=="2026-10" for r in a)
    assert not any(r["channel"]=="wechat" and r["period"]=="2026-09" for r in a)
    with (ROOT/"fixtures/banks/csv-mini/slices.csv").open(encoding="utf-8", newline="") as fp:
        csv_rows = list(csv.reader(fp))
    source = data("fixtures/banks/csv-mini/source.json")["tables"]["月度宽表"]
    assert len(csv_rows[1:]) == len(source["rows"]) == 6
    assert csv_rows[0] == source["columns"]
    assert [[str(v) if v is not None else "" for v in row] for row in source["rows"]] == csv_rows[1:]
    q = data("fixtures/questions.json")
    assert {row["id"] for row in q} == {f"R{n:02d}" for n in range(1,57)} | {f"Q{n:02d}" for n in range(1,5)}
    by_id = {item["id"]:item for item in q}
    assert by_id["R08"]["expected"]["row_count"] == 2
    selected = [r for r in a if r["period"]=="2026-09" and r["channel"]=="manager"]
    for item in by_id["R08"]["expected"]["rows"]:
        assert union_count([r for r in selected if r["branch"]==item["branch"]],"sent") == int(item["current_values"]["sent"]) > 500000
    assert by_id["Q03"]["state"] == by_id["Q04"]["state"] == "CLARIFY"
    record("甲乙各 510 切片、元分与六行 CSV/JSON、分母、量率、估算、补数及 60 个问法条目")


def coupon_oracle(r, x):
    used, budget = x["initial_used"], x["initial_budget_used_fen"]
    orders = {}
    seen = set()
    for e in x["events"]:
        if e["event_id"] in seen:
            continue
        seen.add(e["event_id"])
        key = e["order_id"]
        if e["kind"] == "PAYMENT":
            if key in orders:
                continue
            now = datetime.fromisoformat(e["at"])
            fresh = now - datetime.fromisoformat(x["registered_at"]) < timedelta(days=r["new_customer_days"])
            active = datetime.fromisoformat(r["starts_at"]) <= now < datetime.fromisoformat(r["ends_at"])
            net = e["amount_fen"]
            good = active and fresh and net >= r["min_payment_fen"] and used < r["max_per_customer"]
            stack = not e["other_offer_applied"] or r["stacking"] == "ALLOW"
            if good and stack and budget + r["coupon_fen"] <= r["budget_fen"]:
                used += 1
                budget += r["coupon_fen"]
                orders[key] = [net,"ISSUED"]
            else:
                orders[key] = [net,"NONE"]
        elif e["kind"] == "REDEEM":
            assert orders[key][1] == "ISSUED"
            orders[key][1] = "REDEEMED"
        else:
            orders[key][0] -= e["amount_fen"]
            if orders[key][0] < r["min_payment_fen"] and r["refund_policy"] == "RECOMPUTE_UNUSED":
                if orders[key][1] == "ISSUED":
                    orders[key][1] = "REVOKED"
                    used -= 1
                    budget -= r["coupon_fen"]
                elif orders[key][1] == "REDEEMED":
                    orders[key][1] = "MANUAL_REVIEW"
    return {"winner_ids":[],"used":used,"budget_used_fen":budget,
            "coupons":[{"order_id":k,"net_paid_fen":net,"coupon_state":state} for k,(net,state) in sorted(orders.items())],
            "manual_review":any(o[1]=="MANUAL_REVIEW" for o in orders.values())}


def callback_oracle(r, x):
    ordering = sorted(x["events"],key=lambda e: (not e["appointment"] if r["priority"]=="APPOINTMENT_FIRST" else False,e["at"],e["seq"]))
    chosen = ordering[:max(0,r["daily_cap"]-x["used"])]
    return {"winner_ids":[e["strategy_id"] for e in chosen],"used":x["used"]+len(chosen),"budget_used_fen":None,
            "coupons":[],"manual_review":False}


def verify_rules():
    rules = data("fixtures/cases/rules.json")
    cases = data("fixtures/cases/golden-cases.json")
    assert len(cases) == 15
    for c in cases:
        calculate = coupon_oracle if c["input"]["template"] == "coupon_threshold" else callback_oracle
        a = calculate(rules[c["baseline_rule_id"]],c["input"])
        b = calculate(rules[c["candidate_rule_id"]],c["input"])
        assert a == c["expected_baseline"] and b == c["expected_candidate"], c["id"]
        original = "NOT_REQUIRED" if c["mode"]=="SYNTHETIC" else "MATCH" if a==c["observed_original"] else "DIFF"
        assert original == c["expected_original_status"], c["id"]
        assert c["candidate_eligible"] == (original != "DIFF" and not b["manual_review"]), c["id"]
    vectors = data("fixtures/cases/preflight-vectors.json")
    case_ids = {c["id"]: c for c in cases}
    for v in vectors:
        wanted = case_ids[v["case_id"]]["expected_candidate"]
        status = "STALE" if v.get("invalidate") else "MISSING" if v["observed"] is None else (
            "VERSION_MISMATCH" if "DIFFERENT" in (v["case_digest"], v["rule_digest"]) else (
                "MATCH" if wanted == v["observed"] else "DIFF"))
        assert status == v["state"], v["id"]
    record("四版规则、15 个案例双版本、五种预发状态")


def main():
    if not __debug__:
        raise RuntimeError("Run without -O so assertions are active")
    verify_manifest()
    verify_contracts()
    verify_database()
    verify_banks()
    verify_rules()
    print(f"PACKAGE PASS {len(CHECKED)}/{len(CHECKED)}")


if __name__ == "__main__":
    main()
