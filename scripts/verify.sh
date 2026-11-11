#!/usr/bin/env bash
# 原型基线验收：可在本地(WSL2 Ubuntu)或 CI 中执行，退出码非 0 即失败
set -euo pipefail

# 工具链自发现：本地 WSL2 非登录 shell 也要能找到 Linux node
if [ -d "$HOME/.local/share/node/bin" ]; then PATH="$HOME/.local/share/node/bin:$PATH"; fi
export PATH
for t in node python3 sha256sum git; do
  command -v "$t" >/dev/null 2>&1 || { echo "FAIL: 缺少 $t，请在 WSL2 Ubuntu 中执行"; exit 127; }
done
echo "env: node=$(node -v) python=$(python3 -V 2>&1 | cut -d\" -f2)"
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
