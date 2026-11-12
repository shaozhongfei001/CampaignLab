#!/usr/bin/env python3
"""校验前端设计基线（spec/frontend-template-spdb-v1.1）与其 README 第九节记录的哈希一致。

背景（D-002）：三份不可变基线中，v1.0 与 v1.0.1 补丁自带机读清单
（SHA256SUMS / DELTA-SHA256SUMS），前端模板基线没有 —— 它的 8 项产物哈希只写在自带
README 的第九节表格里，此前只能人工比对，CI 无法守护。本脚本把该表解析出来做机器校验，
全程只读 spec/，不写任何文件（不违反「基线不可变」）。

退出码：0 全部一致；1 有不一致或缺文件；2 用法或表格式解析错误。
"""

from __future__ import annotations

import re
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "spec/frontend-template-spdb-v1.1"
README = BASELINE / "README_设计与使用说明.md"
ROW = re.compile(
    r"^\|\s*`(?P<name>[^`]+)`\s*\|\s*(?P<size>\d+)\s*B\s*\|\s*`(?P<hash>[0-9a-f]{16})`\s*\|\s*$"
)
EXPECTED_ROWS = 8
# README 刻意不记录自身与 00_模版入口.html 的哈希（文件无法记录自己的哈希）
SELF_EXCLUDED = ("README_设计与使用说明.md", "00_模版入口.html")


def parse_manifest(text: str) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if m is not None:
            rows.append((m.group("name"), int(m.group("size")), m.group("hash")))
    return rows


def main() -> int:
    if not README.exists():
        print(f"FAIL 找不到基线 README: {README}", file=sys.stderr)
        return 2
    rows = parse_manifest(README.read_text(encoding="utf-8"))
    if len(rows) != EXPECTED_ROWS:
        print(
            f"FAIL 第九节应记录 {EXPECTED_ROWS} 项产物，实际解析到 {len(rows)} 项（表格式可能已变）",
            file=sys.stderr,
        )
        return 2
    bad: list[str] = []
    for name, size, want in rows:
        path = BASELINE / name
        if not path.exists():
            print(f"FAIL {name} 文件缺失")
            bad.append(name)
            continue
        data = path.read_bytes()
        got = sha256(data).hexdigest()[:16]
        ok = got == want and len(data) == size
        print(
            f"{'OK  ' if ok else 'FAIL'} {name} sha16={got} expect={want} "
            f"bytes={len(data)} expect={size}"
        )
        if not ok:
            bad.append(name)
    file_count = sum(1 for p in BASELINE.rglob("*") if p.is_file())
    print(
        f"baseline_files={file_count} manifest_rows={len(rows)} "
        f"self_excluded={','.join(SELF_EXCLUDED)}"
    )
    if bad:
        print(f"FRONTEND BASELINE FAIL ({len(bad)} 项): {bad}", file=sys.stderr)
        return 1
    print(f"FRONTEND BASELINE PASS {len(rows)}/{len(rows)}（哈希与字节数逐项一致）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
