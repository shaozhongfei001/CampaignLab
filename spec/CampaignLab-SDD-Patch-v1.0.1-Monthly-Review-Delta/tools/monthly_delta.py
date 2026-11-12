"""Inspect CampaignLab monthly contract changes; optionally stage review copies."""

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import sys
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
BASE_PREFIX = "CampaignLab-SDD-v1.0/"
BASE_SHA = "c8ac004c50f53ea08416807bd43a4b585784b31892513082e4aa635952850d81"
BASE_MANIFEST_SHA = "3d3e32632c1d28368fc3fec4e591572dc73b0ed56eb89193e4c84d54e4ef3d91"
FILES = ("openapi.json", "source-json.schema.json", "source-metadata.schema.json")


def sha(data):
    return sha256(data).hexdigest()


def verify_manifest():
    manifest = (ROOT / "DELTA-SHA256SUMS").read_text(encoding="utf-8")
    names = set()
    for line in manifest.splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if (
            not re.fullmatch(r"[0-9a-f]{64}", digest)
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or relative in names
            or not path.resolve().is_relative_to(ROOT)
        ):
            raise ValueError(f"补丁清单非法：{relative}")
        if sha(path.read_bytes()) != digest:
            raise ValueError(f"补丁文件摘要变化：{relative}")
        names.add(relative)
    return len(names)


def read_base(path):
    if path.is_dir():
        manifest = (path / "SHA256SUMS").read_bytes()
        if sha(manifest) != BASE_MANIFEST_SHA:
            raise ValueError("这不是原始 v1.0 SDD 解压目录。已开发的目录请用 --contracts-dir。")
        hashes = {
            name: value for value, name in (line.split("  ", 1) for line in manifest.decode().splitlines())
        }
        files = {name: (path / "contracts" / name).read_bytes() for name in FILES}
        for name, content in files.items():
            if sha(content) != hashes[f"contracts/{name}"]:
                raise ValueError(f"原始契约已改动：contracts/{name}。请改用 --contracts-dir 检查。")
        return files
    archive = path.read_bytes()
    if sha(archive) != BASE_SHA:
        raise ValueError("原 ZIP 的 SHA-256 与 v1.0 基座不匹配。")
    with ZipFile(BytesIO(archive)) as z:
        return {name: z.read(f"{BASE_PREFIX}contracts/{name}") for name in FILES}


def read_current(path):
    documents = {}
    issues = []
    for name in FILES:
        try:
            documents[name] = (path / name).read_bytes()
        except OSError as error:
            issues.append((name, "/", "CONFLICT", str(error)))
    return documents, issues


def parent_of(document, pointer):
    if not pointer.startswith("/"):
        raise ValueError(f"非法路径 {pointer}")
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer[1:].split("/")]
    node = document
    for part in parts[:-1]:
        if not isinstance(node, dict) or part not in node:
            raise ValueError(f"父节点不可定位：{pointer}")
        node = node[part]
    if not isinstance(node, dict):
        raise ValueError(f"父节点不是对象：{pointer}")
    return node, parts[-1]


def plan(documents, delta, initial_issues=()):
    effective = {}
    rows = list(initial_issues)
    for name, raw in documents.items():
        try:
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                raise ValueError("JSON 根节点须为对象")
            effective[name] = obj
        except ValueError as error:
            rows.append((name, "/", "CONFLICT", str(error)))

    for item in delta["additions"]:
        file, pointer = item["file"], item["path"]
        if file not in effective:
            continue
        obj = effective[file]
        value = delta["values"][item["value_key"]]
        try:
            target, key = parent_of(obj, pointer)
            if item.get("optional_property"):
                owner, _ = parent_of(obj, pointer.rsplit("/", 1)[0])
                required = owner.get("required", [])
                if not isinstance(required, list) or key in required:
                    raise ValueError("该字段必须保持可选，请核对 required")
            if key not in target:
                target[key] = value
                rows.append((file, pointer, "ADD", ""))
            elif target[key] == value:
                rows.append((file, pointer, "ALREADY", ""))
            else:
                raise ValueError("现有节点内容不同，请合并该节点")
        except ValueError as error:
            rows.append((file, pointer, "CONFLICT", str(error)))

    item = delta["version_update"]
    file, pointer = item["file"], item["path"]
    if file in effective:
        try:
            parent, key = parent_of(effective[file], pointer)
            current = parent.get(key)
            if not isinstance(current, str):
                raise ValueError("找不到有效的 OpenAPI info.version")
            if current == item["from"]:
                parent[key] = item["to"]
                rows.append((file, pointer, "UPDATE", f"{current} → {item['to']}"))
            elif current == item["to"]:
                rows.append((file, pointer, "ALREADY", ""))
            else:
                rows.append((file, pointer, "KEEP", f"沿用当前版本 {current}"))
        except ValueError as error:
            rows.append((file, pointer, "CONFLICT", str(error)))
    return effective, rows


def write_candidate(path, effective):
    # Only this explicit action writes files. The path must not already exist.
    path.mkdir(exist_ok=False)
    contracts = path / "contracts"
    contracts.mkdir()
    for name in FILES:
        with (contracts / name).open("x", encoding="utf-8") as file:
            json.dump(effective[name], file, ensure_ascii=False, indent=2)
            file.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--base", type=Path, help="原 v1.0 ZIP 或其原始解压根目录")
    source.add_argument("--contracts-dir", type=Path, help="当前实现中三份 JSON 契约所在目录")
    parser.add_argument("--stage", type=Path, help="可选，新建独立目录并生成供核对的候选契约")
    args = parser.parse_args()
    try:
        print(f"PASS 补丁摘要 {verify_manifest()} 项")
        delta = json.loads((ROOT / "contracts/monthly-contract-delta.json").read_bytes())
        if args.base:
            documents, issues = read_base(args.base.resolve()), []
        else:
            documents, issues = read_current(args.contracts_dir.resolve())
        effective, rows = plan(documents, delta, issues)
        for name, pointer, state, detail in rows:
            print(f"{state:8} {name} {pointer}" + (f" · {detail}" if detail else ""))
        if any(row[2] == "CONFLICT" for row in rows):
            print("存在节点冲突。输入契约未写入，请核对上述路径。", file=sys.stderr)
            return 2
        if args.stage:
            path = args.stage.resolve()
            if args.contracts_dir and path.is_relative_to(args.contracts_dir.resolve()):
                raise ValueError("请将 --stage 指向当前契约目录之外的新目录。")
            if args.base and args.base.is_dir() and path.is_relative_to(args.base.resolve()):
                raise ValueError("请将 --stage 指向原 SDD 目录之外的新目录。")
            write_candidate(path, effective)
            print(f"已生成候选契约：{path / 'contracts'}")
        else:
            print("只读检查通过。")
        return 0
    except (OSError, ValueError, KeyError, BadZipFile) as error:
        print(f"DELTA ERROR {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
