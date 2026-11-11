# -*- coding: utf-8 -*-
import io, os, hashlib
LIN = r"D:\ws\codex\游侠高仿真原型_版本系谱与基线清单_20261105.md"
OUT = r"D:\ws\codex\游侠前端设计模板_浦发风格_V1_20261105"
MASTER = r"D:\ws\codex\游侠高仿真原型_S03S04场景版_20261105\S03_S04_运营后台_全链路联动工作台_V2.3_本地母版_浦发风格.html"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest().upper()
FILES = ["00_模板入口.html", "README_设计与使用说明.md", "checklist_交付前自检.md", "gallery_组件图鉴.html",
         "template_blank.html", "template_blank_singlefile.html", os.path.join("css", "tokens.css"),
         os.path.join("css", "youxia-ui.css"), os.path.join("js", "youxia-charts.js"), os.path.join("js", "youxia-shell.js")]
rows = "\n".join("| `" + f.replace("\\", "/") + "` | " + str(os.path.getsize(os.path.join(OUT, f))) + " B | `"
                 + sha(os.path.join(OUT, f))[:32] + "` |" for f in FILES if os.path.exists(os.path.join(OUT, f)))
BODY = io.open(os.path.join(OUT, "tools", "_lineage_body.md"), encoding="utf-8").read()
SEC = BODY.replace("@@MSHA@@", sha(MASTER)).replace("@@ROWS@@", rows)
assert "@@" not in SEC
t = io.open(LIN, encoding="utf-8").read()
if "## 9. 前端设计模板 V1" in t:
    t = t[:t.index("## 9. 前端设计模板 V1")].rstrip("\n")
    io.open(LIN, "w", encoding="utf-8", newline="\n").write(t)
io.open(LIN, "a", encoding="utf-8", newline="\n").write(SEC)
print("lineage §9 appended, %dB" % len(SEC.encode("utf-8")))
