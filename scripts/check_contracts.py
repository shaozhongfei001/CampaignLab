#!/usr/bin/env python3
"""活契约与不可变基线之间的差异门禁（手册第 7 节的 CI 门禁）。

设计要点：
1. 基线 `spec/CampaignLab-SDD-v1.0/contracts/` 只读、按字节入库；活契约在 `contracts/`。
2. 活契约里的 JSON 文件是**规范化后**的（indent=2, ensure_ascii=False），因此比较一律
   走「解析后的结构比较」，不做字节比较；字节真值永远以基线为准。
3. 任何结构差异都必须能在 `contracts/CHANGES.json` 里找到登记项（含 CR 与 ADR 编号），
   否则本门禁失败。登记项反过来也必须真实产生差异，防止僵尸条目。
4. 新增子树只登记其根指针（不递归展开），与 monthly_delta.py 的输出粒度一致。

子命令：
  diff   --base DIR --live DIR [--file NAME]   打印指针级差异（审计用）
  check  [--validate]                          基线 vs 活契约 + 登记完整性；--validate 追加
                                               OpenAPI 与 JSON Schema 元校验（需 dev 依赖）
退出码：0 通过；1 门禁失败；2 用法或文件错误。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "spec/CampaignLab-SDD-v1.0/contracts"
LIVE = ROOT / "contracts"
REGISTRY = LIVE / "CHANGES.json"
CR_DIR = ROOT / "orchestrator/change-requests"
ADR_DIR = ROOT / "docs/decisions"
JSON_FILES = (
    "case-input.schema.json",
    "dependencies.json",
    "openapi.json",
    "operations.json",
    "pages.json",
    "rule-set.schema.json",
    "source-json.schema.json",
    "source-mapping.schema.json",
    "source-metadata.schema.json",
    "traceability.json",
)
OTHER_FILES = ("sqlite-v1.sql",)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def diff_nodes(base: Any, live: Any, pointer: str = "") -> list[tuple[str, str]]:
    """返回 (指针, 类型) 列表；类型为 added / removed / changed。"""
    rows: list[tuple[str, str]] = []
    if isinstance(base, dict) and isinstance(live, dict):
        for key in base:
            child = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
            if key not in live:
                rows.append((child, "removed"))
            else:
                rows.extend(diff_nodes(base[key], live[key], child))
        for key in live:
            if key not in base:
                child = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
                rows.append((child, "added"))
        return rows
    if isinstance(base, list) and isinstance(live, list):
        for index in range(min(len(base), len(live))):
            rows.extend(diff_nodes(base[index], live[index], pointer + "/" + str(index)))
        for index in range(len(live), len(base)):
            rows.append((pointer + "/" + str(index), "removed"))
        for index in range(len(base), len(live)):
            rows.append((pointer + "/" + str(index), "added"))
        return rows
    if base != live:
        rows.append((pointer or "/", "changed"))
    return rows


def diff_file(name: str, base_dir: Path, live_dir: Path) -> list[tuple[str, str]]:
    return diff_nodes(load_json(base_dir / name), load_json(live_dir / name))


def cmd_diff(args: argparse.Namespace) -> int:
    base_dir = Path(args.base)
    live_dir = Path(args.live)
    names: list[str]
    if args.files:
        names = [n for n in str(args.files).split(",") if n]
    elif args.file:
        names = [str(args.file)]
    else:
        names = list(JSON_FILES)
    total = 0
    skipped: list[str] = []
    for name in names:
        if not (base_dir / name).exists() or not (live_dir / name).exists():
            skipped.append(name)
            if args.strict_missing:
                print(f"MISSING {name}", file=sys.stderr)
                return 2
            continue
        rows = diff_file(name, base_dir, live_dir)
        total += len(rows)
        for pointer, kind in rows:
            print(f"{kind:8} {name} {pointer}")
    print(f"total_differences={total} compared={len(names) - len(skipped)} skipped={skipped}")
    return 0


def load_registry() -> list[dict[str, Any]]:
    doc = load_json(REGISTRY)
    entries = doc.get("entries")
    if not isinstance(entries, list):
        raise ValueError("CHANGES.json 缺少 entries 列表")
    out: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("CHANGES.json 登记项必须是对象")
        for field in ("file", "pointer", "kind", "cr", "adr"):
            if not entry.get(field):
                raise ValueError(f"登记项缺字段 {field}: {entry}")
        out.append(entry)
    return out


def cmd_check(args: argparse.Namespace) -> int:
    problems: list[str] = []
    if not BASELINE.is_dir():
        print(f"FAIL 基线目录缺失: {BASELINE}", file=sys.stderr)
        return 2
    if not LIVE.is_dir():
        print(f"FAIL 活契约目录缺失: {LIVE}", file=sys.stderr)
        return 2

    # 1) 非 JSON 文件必须与基线逐字节一致（例如 sqlite-v1.sql 不允许漂移）
    for name in OTHER_FILES:
        a = (BASELINE / name).read_bytes()
        b = (LIVE / name).read_bytes()
        if a != b:
            problems.append(f"{name} 与基线字节不一致，且此类文件不允许漂移")

    # 2) 结构差异必须与登记项一一对应
    try:
        entries = load_registry()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL 读取 {REGISTRY} 失败: {error}", file=sys.stderr)
        return 2
    registered: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        key = (str(entry["file"]), str(entry["pointer"]))
        if key in registered:
            problems.append(f"登记项重复: {key[0]} {key[1]}")
        registered[key] = entry

    observed: dict[tuple[str, str], str] = {}
    for name in JSON_FILES:
        for pointer, kind in diff_file(name, BASELINE, LIVE):
            observed[(name, pointer)] = kind

    for key, kind in observed.items():
        found = registered.get(key)
        if found is None:
            problems.append(f"未登记的契约差异: {key[0]} {key[1]} ({kind})")
        elif found["kind"] != kind:
            problems.append(f"登记类型不符: {key[0]} {key[1]} 登记={found['kind']} 实际={kind}")
    for reg_key, reg_entry in registered.items():
        if reg_key not in observed:
            problems.append(
                f"僵尸登记项（无对应差异）: {reg_key[0]} {reg_key[1]} cr={reg_entry['cr']}"
            )

    # 3) 每个登记项的 CR 与 ADR 文件必须真实存在
    missing_cr: set[str] = set()
    missing_adr: set[str] = set()
    for entry in entries:
        cr_id = str(entry["cr"])
        adr_id = str(entry["adr"])
        if not (CR_DIR / f"{cr_id}.md").exists():
            missing_cr.add(cr_id)
        if not list(ADR_DIR.glob(f"{adr_id}-*.md")):
            missing_adr.add(adr_id)
    for cr_id in sorted(missing_cr):
        problems.append(f"CR 文件缺失: orchestrator/change-requests/{cr_id}.md")
    for adr_id in sorted(missing_adr):
        problems.append(f"ADR 文件缺失: docs/decisions/{adr_id}-*.md")

    # 4) 可选：OpenAPI 与 JSON Schema 元校验（需要 dev 依赖，CI 缺依赖时跳过）
    validated = 0
    if args.validate:
        try:
            from openapi_spec_validator import validate as validate_openapi
        except ImportError:
            print("SKIP openapi-spec-validator 未安装")
        else:
            validate_openapi(load_json(LIVE / "openapi.json"))
            validated += 1
        try:
            import jsonschema
        except ImportError:
            print("SKIP jsonschema 未安装")
        else:
            for name in (
                "case-input.schema.json",
                "rule-set.schema.json",
                "source-json.schema.json",
                "source-mapping.schema.json",
                "source-metadata.schema.json",
            ):
                jsonschema.Draft202012Validator.check_schema(load_json(LIVE / name))
                validated += 1

    if problems:
        for line in problems:
            print(f"FAIL {line}", file=sys.stderr)
        print(f"CONTRACT CHECK FAIL ({len(problems)} 项)", file=sys.stderr)
        return 1
    print(
        f"CONTRACT CHECK PASS 登记项={len(entries)} 实测差异={len(observed)} "
        f"元校验={validated if args.validate else 'skipped'}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_diff = sub.add_parser("diff", help="打印指针级差异")
    p_diff.add_argument("--base", default=str(BASELINE))
    p_diff.add_argument("--live", default=str(LIVE))
    p_diff.add_argument("--file", default="")
    p_diff.add_argument("--files", default="", help="逗号分隔的文件名列表")
    p_diff.add_argument(
        "--strict-missing",
        action="store_true",
        help="任一侧缺文件即失败（默认跳过，便于只含部分文件的候选目录）",
    )
    p_diff.set_defaults(func=cmd_diff)
    p_check = sub.add_parser("check", help="基线 vs 活契约 + 登记完整性门禁")
    p_check.add_argument(
        "--validate", action="store_true", help="追加 OpenAPI / JSON Schema 元校验"
    )
    p_check.set_defaults(func=cmd_check)
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
