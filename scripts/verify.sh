#!/usr/bin/env bash
# 原型基线验收：可在本地(WSL2 Ubuntu)或 CI 中执行，退出码非 0 即失败
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/prototype"

echo "==> 1/4 交付件完整性"
sha256sum -c SHA256SUMS --quiet && echo "SHA256SUMS OK"

echo "==> 2/4 计算与问法断言"
node campaignlab-review-work/verify.mjs

echo "==> 3/4 确定性数据生成"
python3 campaignlab-review-work/generate_data.py >/dev/null

echo "==> 4/4 字节级复现"
python3 campaignlab-review-work/build.py >/dev/null
cd "$ROOT"
if ! git diff --quiet -- prototype; then
  echo "FAIL: 重建产物与入库内容不一致（非字节级复现）"
  git status --short -- prototype
  exit 1
fi
echo "PASS: 字节级复现"
