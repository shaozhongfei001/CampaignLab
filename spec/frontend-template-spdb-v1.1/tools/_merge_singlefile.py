# -*- coding: utf-8 -*-
"""机械合并：template_blank.html -> template_blank_singlefile.html（零重写，只做替换）"""
import io, os, re, hashlib
OUT = r"D:\ws\codex\游侠前端设计模板_浦发风格_V1_20261105"

def rd(rel):
    return io.open(os.path.join(OUT, rel), encoding="utf-8").read()

t = rd("template_blank.html")
css = ("<style>\n/* ---- 内联：css/tokens.css ---- */\n" + rd("css/tokens.css").replace("</style", "<\\/style")
       + "\n/* ---- 内联：css/youxia-ui.css ---- */\n" + rd("css/youxia-ui.css").replace("</style", "<\\/style")
       + "\n</style>")
js = ("<script>\n/* ---- 内联：js/youxia-charts.js ---- */\n" + rd("js/youxia-charts.js").replace("</script", "<\\/script")
      + "\n/* ---- 内联：js/youxia-shell.js ---- */\n" + rd("js/youxia-shell.js").replace("</script", "<\\/script")
      + "\n</script>")

LR = r'<link rel="stylesheet" href="css/tokens\.css">\s*<link rel="stylesheet" href="css/youxia-ui\.css">'
SR = r'<script src="js/youxia-charts\.js"></script>\s*<script src="js/youxia-shell\.js"></script>'
assert len(re.findall(LR, t)) == 1 and len(re.findall(SR, t)) == 1
t2 = re.sub(LR, lambda m: css, t, count=1)
t2 = re.sub(SR, lambda m: js, t2, count=1)
assert 'href="css/' not in t2 and 'src="js/' not in t2, "仍残留外链"
t2 = t2.replace("<title>", "<title>【单文件版】", 1)

p = os.path.join(OUT, "template_blank_singlefile.html")
io.open(p, "w", encoding="utf-8", newline="\n").write(t2)
b = t2.encode("utf-8")
print("singlefile %dB  sha %s" % (len(b), hashlib.sha256(b).hexdigest()[:16]))
