#!/usr/bin/env bash
# CampaignLab 环境诊断（M0-01）
#
# 用法（非登录 shell 亦可直接执行）：
#   bash scripts/doctor.sh
#   DOCTOR_SKIP_VERIFY=1 bash scripts/doctor.sh    # 跳过较慢的原型基线复跑
#
# 只读诊断：不安装依赖、不改写锁、不重装 node_modules
# （uv sync 与 npm ci 均以 --dry-run 检测一致性）。
# 退出码：0 = 关键项全部通过；1 = 存在 FAIL；2 = 无法定位仓库根。

set -uo pipefail

# ---- 工具链自发现 ----
# WSL2 下 PATH 会穿透 Windows 侧的 node/npm；与 scripts/verify.sh 保持一致，
# 优先把 Linux 侧的 ~/.local/bin 与 ~/.local/share/node/bin 放到 PATH 最前。
for d in "$HOME/.local/bin" "$HOME/.local/share/node/bin"; do
  if [ -d "$d" ]; then
    case ":$PATH:" in
      *":$d:"*) ;;
      *) PATH="$d:$PATH" ;;
    esac
  fi
done
export PATH

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ ! -d "$ROOT/.git" ]; then
  echo "FAIL: 无法定位 git 仓库根（$ROOT）"
  exit 2
fi
cd "$ROOT" || exit 2

TMPD="$(mktemp -d)"
trap "rm -rf $TMPD" EXIT

PASS=0; WARN=0; FAIL=0
ok()   { printf "  [ OK ] %s\n" "$1"; PASS=$((PASS+1)); }
warn() { printf "  [WARN] %s\n" "$1"; WARN=$((WARN+1)); }
bad()  { printf "  [FAIL] %s\n" "$1"; FAIL=$((FAIL+1)); }
info() { printf "         %s\n" "$1"; }
sec()  { printf "\n== %s ==\n" "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

printf "CampaignLab doctor @ %s\n" "$(date -Is)"
printf "host: %s | %s\n" "$(uname -srmo)" "$(. /etc/os-release 2>/dev/null; echo "${PRETTY_NAME:-unknown}")"

# ---------------- 1. 仓库与分支 ----------------
sec "1. 仓库与分支"
printf "  path   : %s\n" "$ROOT"
if have git; then
  printf "  branch : %s\n" "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
  printf "  head   : %s\n" "$(git rev-parse --short HEAD 2>/dev/null)"
  DIRTY="$(git status --porcelain)"
  if [ -z "$DIRTY" ]; then
    ok "工作树干净"
  else
    N="$(printf "%s\n" "$DIRTY" | grep -c .)"
    warn "工作树存在 ${N} 项未提交改动"
    printf "%s\n" "$DIRTY" | head -15 | sed "s/^/         /"
  fi
else
  bad "git 不可用"
fi

# ---------------- 2. CPython / SQLite / JSON ----------------
sec "2. CPython 与 SQLite JSON 能力"
PY=""
for c in "$ROOT/.venv/bin/python" "$HOME/.local/bin/python3.14"; do
  if [ -x "$c" ]; then PY="$c"; break; fi
done
if [ -z "$PY" ] && have python3; then PY="$(command -v python3)"; fi
if [ -z "$PY" ]; then
  bad "未找到可用 CPython（期望 .venv/bin/python 或 ~/.local/bin/python3.14）"
else
  PYV="$("$PY" -c "import sys;print(sys.version.split()[0])" 2>/dev/null)"
  printf "  python : %s\n" "$PYV"
  printf "  path   : %s -> %s\n" "$PY" "$(readlink -f "$PY")"
  case "$PYV" in
    3.14.*) ok "CPython ${PYV} 满足 >=3.14,<3.15" ;;
    *)      bad "CPython ${PYV} 不满足 >=3.14,<3.15" ;;
  esac
  "$PY" - >"$TMPD/py" 2>&1 <<"PYEOF"
import json
import sqlite3
v = sqlite3.sqlite_version_info
print("sqlite : %s %s" % (sqlite3.sqlite_version, list(v)))
payload = json.dumps({"a": 1, "b": [10, 20, 30], "c": {"d": "x"}})
con = sqlite3.connect(":memory:")
row = con.execute("select json_extract(?, ?), json_valid(?), json_type(?)", (payload, "$.a", payload, payload)).fetchone()
print("json1  : json_extract=%s json_valid=%s json_type=%s" % row)
rows = con.execute("select count(*) from json_each(?)", (payload,)).fetchone()[0]
grp = con.execute("select json_group_array(value) from json_each(?)", (payload,)).fetchone()[0]
print("         json_each_rows=%s json_group_array=%s" % (rows, grp[:26]))
print("note   : SQLite>=3.38 起 JSON 内建，SQLITE_ENABLE_JSON1 已非独立编译选项")
print("DOCTOR_SQLITE_OK=%s" % (v >= (3, 38)))
print("DOCTOR_JSON_OK=%s" % (row[0] == 1 and row[1] == 1 and rows == 3))
PYEOF
  grep -v "^DOCTOR_" "$TMPD/py" | sed "s/^/  /"
  if grep -q "^DOCTOR_SQLITE_OK=True$" "$TMPD/py"; then ok "sqlite_version >= 3.38"; else bad "sqlite_version < 3.38 或探测失败"; fi
  if grep -q "^DOCTOR_JSON_OK=True$" "$TMPD/py"; then ok "JSON 函数实测可用（json_extract/json_valid/json_type/json_each/json_group_array）"; else bad "JSON 函数实测不可用"; fi
fi

# ---------------- 3. Node / npm（ELF 取证） ----------------
sec "3. Node / npm（含 ELF 取证）"
if have node; then
  NODE_BIN="$(command -v node)"
  NODE_REAL="$(readlink -f "$NODE_BIN")"
  NODE_VER="$(node -v)"
  printf "  node   : %s\n" "$NODE_VER"
  printf "  path   : %s -> %s\n" "$NODE_BIN" "$NODE_REAL"
  case "$NODE_REAL" in
    /mnt/*) bad "node 解析到 Windows 挂载路径（PATH 穿透）：${NODE_REAL}" ;;
    *)      ok "node 位于 Linux 文件系统（非 /mnt/*）：${NODE_REAL}" ;;
  esac
  if have file; then
    SIG="$(file -b "$NODE_REAL" 2>/dev/null | cut -c1-58)"
  else
    SIG="$(head -c 4 "$NODE_REAL" | od -An -tx1 | tr -d " \n")"
  fi
  printf "  elf    : %s\n" "$SIG"
  case "$SIG" in
    ELF*)      ok "node 为 Linux ELF 可执行文件" ;;
    7f454c46*) ok "node 魔数为 ELF（7f 45 4c 46）" ;;
    *)         bad "node 非 ELF：${SIG}" ;;
  esac
  case "$NODE_VER" in
    v24.*) ok "Node ${NODE_VER} 满足 >=24,<25" ;;
    *)     bad "Node ${NODE_VER} 不满足 >=24,<25" ;;
  esac
else
  bad "node 不可用"
fi
if have npm; then
  ok "npm $(npm -v) @ $(readlink -f "$(command -v npm)")"
else
  bad "npm 不可用"
fi

# ---------------- 4. uv 与依赖锁 ----------------
sec "4. uv 与 Python 依赖锁"
if have uv; then
  ok "uv $(uv --version 2>&1) @ $(readlink -f "$(command -v uv)")"
  if [ -f "$ROOT/.python-version" ]; then info ".python-version = $(cat "$ROOT/.python-version")"; fi
  if [ -f "$ROOT/pyproject.toml" ]; then
    info "requires-python = $(grep -m1 "^requires-python" "$ROOT/pyproject.toml" | cut -d= -f2- | tr -d " ")"
  else
    bad "pyproject.toml 不存在"
  fi
  if [ -f "$ROOT/uv.lock" ]; then
    uv lock --check >"$TMPD/lockchk" 2>&1; rc=$?
    printf "  uv lock --check 退出码: %d\n" "$rc"
    if [ $rc -eq 0 ]; then
      ok "uv lock --check 通过（uv.lock 与 pyproject.toml 一致）"
      info "uv.lock 包条目数：$(grep -c "^name = " "$ROOT/uv.lock")"
    else
      bad "uv lock --check 失败（rc=${rc}）"
      sed "s/^/         /" "$TMPD/lockchk" | head -8
    fi
    if [ -d "$ROOT/.venv" ]; then
      uv sync --locked --dry-run >"$TMPD/sync" 2>&1; rc=$?
      if [ $rc -eq 0 ]; then ok "uv sync --locked --dry-run 通过（虚拟环境与锁一致）"; else bad "uv sync --locked --dry-run 失败（rc=${rc}）"; sed "s/^/         /" "$TMPD/sync" | head -8; fi
    else
      bad ".venv 不存在（在仓库根执行 uv sync --locked）"
    fi
  else
    bad "uv.lock 不存在"
  fi
else
  bad "uv 不可用"
fi

# ---------------- 5. 前端依赖（只检测不重装） ----------------
sec "5. 前端依赖（web/）"
if [ -f "$ROOT/web/package.json" ]; then
  if [ -f "$ROOT/web/package-lock.json" ]; then
    ok "web/package-lock.json 存在（$(wc -c < "$ROOT/web/package-lock.json") 字节）"
  else
    bad "web/package-lock.json 不存在"
  fi
  if have npm; then
    (cd "$ROOT/web" && npm ci --dry-run --no-audit --no-fund >"$TMPD/npmci" 2>&1); rc=$?
    printf "  npm ci --dry-run 退出码: %d\n" "$rc"
    if [ $rc -eq 0 ]; then
      ok "npm ci --dry-run 通过（锁与 package.json 一致且可复现；未改动 node_modules）"
      grep -E "^(added|changed|removed|up to date)" "$TMPD/npmci" | head -3 | sed "s/^/         /"
    else
      bad "npm ci --dry-run 失败（rc=${rc}）"
      sed "s/^/         /" "$TMPD/npmci" | head -12
    fi
    if [ -d "$ROOT/web/node_modules" ]; then
      info "web/node_modules 已安装（顶层 $(ls "$ROOT/web/node_modules" | grep -vc "^[.]") 项）"
    else
      warn "web/node_modules 未安装（在 web/ 执行 npm ci）"
    fi
  else
    bad "npm 不可用"
  fi
else
  bad "web/package.json 不存在"
fi

# ---------------- 6. 构建与工具版本 ----------------
sec "6. 构建与工具版本"
for t in git docker make rg curl sha256sum fc-list; do
  if have "$t"; then
    printf "  %-11s: %s\n" "$t" "$("$t" --version 2>&1 | head -1 | cut -c1-70)"
  else
    printf "  %-11s: MISSING\n" "$t"
    case "$t" in
      git|make) bad "${t} 缺失" ;;
      *)        warn "${t} 缺失" ;;
    esac
  fi
done

# ---------------- 7. 原型基线 ----------------
sec "7. 原型基线 scripts/verify.sh（四步结论）"
if [ "${DOCTOR_SKIP_VERIFY:-0}" = "1" ]; then
  warn "DOCTOR_SKIP_VERIFY=1，已跳过原型基线复跑"
elif [ -f "$ROOT/scripts/verify.sh" ]; then
  bash "$ROOT/scripts/verify.sh" >"$TMPD/verify" 2>&1; rc=$?
  sed "s/^/  /" "$TMPD/verify" | head -20
  if [ $rc -eq 0 ]; then ok "verify.sh 退出码 0（原型基线通过）"; else bad "verify.sh 退出码 ${rc}"; fi
else
  bad "scripts/verify.sh 不存在"
fi

# ---------------- 8. 浏览器与字体（信息项） ----------------
sec "8. 浏览器与字体（信息项，不判 FAIL）"
PWDIR="$HOME/.cache/ms-playwright"
if [ -d "$PWDIR" ]; then
  ls "$PWDIR" 2>/dev/null | grep -E "chromium|firefox|webkit" | head -8 | sed "s/^/         cached: /"
  ok "Playwright 浏览器缓存存在：${PWDIR}"
else
  warn "浏览器缺失：无 Playwright 缓存（${PWDIR}）；npx playwright install 的系统依赖需 root（BLK-01）"
fi
if [ -d "$ROOT/web/node_modules/@playwright/test" ]; then
  info "web/node_modules/@playwright/test 已安装"
else
  warn "web/node_modules/@playwright/test 缺失"
fi
if have fc-list; then
  ZH="$(fc-list :lang=zh 2>/dev/null | wc -l)"
  if [ "$ZH" -gt 0 ]; then ok "存在中文字体（fc-list :lang=zh = ${ZH} 条）"; else warn "无中文字体，视觉走查结论不可用（BLK-02，需 root 安装 fonts-noto-cjk）"; fi
  # D-007：此处曾用 `fc-list | grep -qi`。grep -q 命中即退出，fc-list（约 18.8KB 输出）继续写管道
  # 会收 SIGPIPE(141)，在 set -uo pipefail 下被传播成「未安装」假 WARN（实测 30 次中 28 次误报）。
  # grep -c 读完全部输入不提前退出，故无 SIGPIPE；同时把命中条数写进消息便于取证。
  NOTO_CNT="$(fc-list 2>/dev/null | grep -ci "noto sans cjk")"
  if [ "${NOTO_CNT:-0}" -gt 0 ]; then info "Noto Sans CJK 已安装（fc-list 命中 ${NOTO_CNT} 条）"; else warn "未安装 Noto Sans CJK（BLK-02 未解除，字体度量可能与行内设计基线不一致）"; fi
else
  warn "fc-list 不可用，无法判定字体"
fi

# ---------------- 摘要 ----------------
sec "摘要"
printf "  PASS=%d  WARN=%d  FAIL=%d\n" "$PASS" "$WARN" "$FAIL"
if [ "$FAIL" -eq 0 ]; then
  printf "  RESULT: HEALTHY\n"
  exit 0
fi
printf "  RESULT: UNHEALTHY（%d 项 FAIL）\n" "$FAIL"
exit 1
