# -*- coding: utf-8 -*-
"""模板包一键构建 + 静态门禁。
   顺序：提取 CSS/JS → 生成起手页/图鉴 → 合并单文件 → 类名契约检查 → 内联 JS 语法检查（node --check）
   任一步失败即退出非 0，不允许「生成了但没验证」。"""
import io, os, re, subprocess, sys, hashlib
OUT = r"D:\ws\codex\游侠前端设计模板_浦发风格_V1_20261105"
TOOLS = os.path.join(OUT, "tools")
PY = sys.executable


def run(script):
    r = subprocess.run([PY, "-X", "utf8", os.path.join(TOOLS, script)], capture_output=True, text=True, encoding="utf-8")
    print("[" + script + "]")
    print((r.stdout or "").rstrip())
    if r.returncode:
        print((r.stderr or "").rstrip()); sys.exit(1)


for s in ["_build_template.py", "_write_blank.py", "_write_gallery.py", "_merge_singlefile.py",
          "_check_used.py", "_write_readme.py", "_gen_index.py"]:
    run(s)

# ---- 双加号门禁：a +\n + b 会被解析成 a + (+b) → NaN ----
dbl = 0
for f in sorted(os.listdir(OUT)):
    if not f.endswith(".html"):
        continue
    t2 = io.open(os.path.join(OUT, f), encoding="utf-8").read()
    for i, js in enumerate(re.findall(r"<script>(.*?)</script>", t2, re.S)):
        hits = [m.start() for m in re.finditer(r"\+\s*\n\s*\+", js)]
        for h in hits:
            dbl += 1
            print("FAIL %-32s block%d  双加号 @%d: %s" % (f, i, h, js[max(0, h - 60):h + 30].replace("\n", " ")))
print("双加号处数：", dbl)
if dbl:
    sys.exit(1)

# ---- 转义残留门禁：\\uXXXX 会在页面上显示成字面量 ----
res = 0
for f in sorted(os.listdir(OUT)):
    if f.endswith((".html", ".md")):
        txt = io.open(os.path.join(OUT, f), encoding="utf-8").read()
        hits = re.findall(r"\\\\u[0-9a-fA-F]{4}", txt)
        if hits:
            res += len(hits)
            print("FAIL %-30s 残留双转义 %s" % (f, sorted(set(hits))))
print("\u53cc转义残留：", res)
if res:
    sys.exit(1)

# ---- 内联 JS 语法门禁 ----
tmp = os.path.join(TOOLS, "_lint")
os.makedirs(tmp, exist_ok=True)
bad = 0
for f in sorted(os.listdir(OUT)):
    if not f.endswith(".html"):
        continue
    t = io.open(os.path.join(OUT, f), encoding="utf-8").read()
    for i, js in enumerate(re.findall(r"<script>(.*?)</script>", t, re.S)):
        p = os.path.join(tmp, "%s_%d.js" % (re.sub(r"\W", "_", f), i))
        io.open(p, "w", encoding="utf-8", newline="\n").write(js)
        r = subprocess.run(["node", "--check", p], capture_output=True, text=True, encoding="utf-8", errors="replace")
        tag = "OK   " if r.returncode == 0 else "FAIL "
        if r.returncode:
            bad += 1
            print(tag + "%-34s block%d  %s" % (f, i, (r.stderr or "").strip().split("\n")[0:3]))
        else:
            print(tag + "%-34s block%d  %dB" % (f, i, len(js.encode("utf-8"))))
for j in ("js/youxia-charts.js", "js/youxia-shell.js"):
    p = os.path.join(OUT, j.replace("/", os.sep))
    r = subprocess.run(["node", "--check", p], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(("OK   " if r.returncode == 0 else "FAIL ") + j + ("  " + (r.stderr or "")[:200] if r.returncode else ""))
    bad += (r.returncode != 0)
print("\nLINT FAILURES:", bad)
sys.exit(1 if bad else 0)
