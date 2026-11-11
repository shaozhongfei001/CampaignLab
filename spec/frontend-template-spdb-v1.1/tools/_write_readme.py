# -*- coding: utf-8 -*-
"""生成 README —— 令牌表/文件哈希从实际产物读出；正文用 @@占位@@ 替换（不用 % 格式化，正文里有大量百分号）。"""
import io, os, re, hashlib, json
OUT = r"D:\ws\codex\游侠前端设计模板_浦发风格_V1_20261105"

def sha(rel):
    return hashlib.sha256(io.open(os.path.join(OUT, rel), "rb").read()).hexdigest()[:16]

tok = io.open(os.path.join(OUT, "css", "tokens.css"), encoding="utf-8").read()
rows = []
for m in re.finditer(r"^\s*(--[a-z0-9-]+)\s+(.+?);\s*/\* (L\d) \*/", tok, re.M):
    rows.append((m.group(1), m.group(2), m.group(3)))

def tbl(prefixes):
    o = ["| 令牌 | 值 | 生效层 |", "|---|---|---|"]
    for k, v, l in rows:
        if any(k.startswith(p) for p in prefixes):
            o.append("| `" + k + "` | `" + v.replace("|", "\\|") + "` | " + l + " |")
    return "\n".join(o)

rep = json.load(io.open(os.path.join(OUT, "tools", "extract_report.json"), encoding="utf-8"))
FILES = ["checklist_交付前自检.md", "gallery_组件图鉴.html",
         "template_blank.html", "template_blank_singlefile.html", "css/tokens.css", "css/youxia-ui.css",
         "js/youxia-charts.js", "js/youxia-shell.js"]
ft = ["| 文件 | 大小 | SHA256 前16 |", "|---|---|---|"]
for f in FILES:
    p = os.path.join(OUT, f.replace("/", os.sep))
    if os.path.exists(p):
        ft.append("| `" + f + "` | " + str(os.path.getsize(p)) + " B | `" + sha(f) + "` |")
ftab = "\n".join(ft)

MD = io.open(os.path.join(OUT, "tools", "_readme_body.md"), encoding="utf-8").read()
for k, v in [("@@SRC16@@", rep["source_master_sha256"][:16]), ("@@TBL_INK@@", tbl(("--ink", "--brand"))),
             ("@@TBL_SEM@@", tbl(("--ok", "--warn", "--danger", "--info", "--violet"))),
             ("@@TBL_MISC@@", tbl(("--font", "--r-", "--sh-", "--canvas", "--card", "--line", "--topbar", "--ribbon", "--c"))),
             ("@@FTAB@@", ftab)]:
    MD = MD.replace(k, v)
assert "@@" not in MD, MD[MD.index("@@")-80:MD.index("@@")+40]
io.open(os.path.join(OUT, "README_设计与使用说明.md"), "w", encoding="utf-8", newline="\n").write(MD)
print("README %dB" % len(MD.encode("utf-8")))
