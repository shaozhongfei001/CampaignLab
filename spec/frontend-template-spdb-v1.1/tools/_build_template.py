# -*- coding: utf-8 -*-
"""游侠前端设计模板生成器（浦发风格）· 从现行母版机械提取，不凭记忆重写。
   输入：S03_S04_..._V2.3_本地母版_浦发风格.html
   输出：css/tokens.css  css/youxia-ui.css  js/youxia-charts.js  tools/extract_report.json
"""
import io, os, re, hashlib, json

SRC = r"D:\ws\codex\游侠高仿真原型_S03S04场景版_20261105\S03_S04_运营后台_全链路联动工作台_V2.3_本地母版_浦发风格.html"
OUT = r"D:\ws\codex\游侠前端设计模板_浦发风格_V1_20261105"
for sub in ("css", "js", "tools"):
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)
html = io.open(SRC, encoding="utf-8").read()
sha_src = hashlib.sha256(io.open(SRC, "rb").read()).hexdigest()


def wr(rel, txt):
    p = os.path.join(OUT, rel)
    io.open(p, "w", encoding="utf-8", newline="\n").write(txt)
    return (rel.replace("/", "\\"), len(txt.encode("utf-8")), hashlib.sha256(txt.encode("utf-8")).hexdigest()[:16])


def chunks(css):
    """深度感知的顶层规则切分；@media / @keyframes 整块保留，注释单独成块。"""
    out, i, n = [], 0, len(css)
    while i < n:
        while i < n and css[i] in " \n\r\t":
            i += 1
        if i >= n:
            break
        if css.startswith("/*", i):
            j = css.index("*/", i + 2) + 2
            out.append(css[i:j]); i = j; continue
        j = css.index("{", i)
        if j < 0:
            break
        depth, k = 1, j + 1
        while k < n and depth:
            c = css[k]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif c == "/" and css[k:k + 2] == "/*":
                k = css.index("*/", k + 2) + 1
            k += 1
        out.append(css[i:k].strip()); i = k
    return out


PROJ = re.compile(r"\.screen\.(dp0\d|p5)\b")
blocks = re.findall(r"<style>(.*?)</style>", html, re.S)
assert len(blocks) == 4, len(blocks)
LAYERS = ["L1 设计系统基座 hifi-design-system V1.0", "L2 共用壳层 shell V1（SPDB 浅色）",
          "L3 SPDB 浅色主题层 V4（参考 credit-risk-decision 前端）", "L4 工作台组件扩展层（已去项目专用）"]
dropped, css_out = [], []
for bi, b in enumerate(blocks):
    body = []
    for c in chunks(b):
        if c.startswith("/*") or "{" not in c:
            body.append(c); continue
        head = c.split("{", 1)[0]
        if PROJ.search(head):
            dropped.append(["L" + str(bi + 1), head.strip().replace("\n", " ")[:72]])
            continue
        body.append(c)
    css_out.append("/* ########## " + LAYERS[bi] + " ########## */\n" + "\n".join(body))

HDR = ("/* ============================================================================\n"
       "   游侠 · 浦发风格前端设计模板  youxia-ui.css  V1.1（2026-11-05）\n"
       "   来源：游侠高仿真原型 V2.3 本地母版（SHA256 %s…）四层样式表机械提取，规则本体未手写改动；V1.1 追加 1 条数字归一化规则（见文件末尾）。\n"
       "   层序：L1 设计系统基座 → L2 共用壳层 → L3 SPDB 浅色主题 → L4 工作台组件扩展\n"
       "   剔除：项目专用规则 %d 条（.screen.dp0X / .screen.p5），清单见 tools/extract_report.json\n"
       "   用法：新项目 <link> 本文件即可；换肤只覆盖 tokens.css 的 :root 变量，不要改本文件。\n"
       "   ========================================================================== */\n") % (sha_src[:16], len(dropped))
NUMNORM = ("\n/* ########## L1 归一化（V1.1 新增，非母版规则）########## */\n"
           "/* 数字/代号统一等宽 + tabular 对齐；正文排版由 L1 body 规则给出，勿在此层覆盖。 */\n"
           ".num,.mono{font-family:var(--font-mono);font-variant-numeric:tabular-nums}\n")

res = [wr("css/youxia-ui.css", HDR + "\n".join(css_out) + NUMNORM)]

vars_order, final = [], {}
for bi, b in enumerate(blocks):
    for m in re.finditer(r":root\s*\{([^}]*)\}", b, re.S):
        for vm in re.finditer(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", m.group(1)):
            k, v = vm.group(1), vm.group(2).strip()
            if k not in vars_order:
                vars_order.append(k)
            final[k] = (v, bi + 1)
lines = ["/* ============================================================================",
         "   游侠 · 浦发风格 设计令牌  tokens.css  V1.1（2026-11-05）· 只含 :root 变量",
         "   由母版四层 :root 合并生成；行尾 L# = 该值最终生效于哪一层（后层覆盖前层）。",
         "   新项目只改这里即可换品牌：中性色阶 / 品牌色 / 语义色 / 圆角 / 阴影 / 图表色板。",
         "   红线：语义色不得挪作装饰；--danger-* 只用于「已触发/失败/禁止」，不用于强调。",
         "   ========================================================================== */", ":root{"]
for k in vars_order:
    v, lay = final[k]
    lines.append("  %-14s %s;  /* L%d */" % (k, v, lay))
lines.append("}")
lines.append("/* 基准排版与数字归一化已移至 youxia-ui.css（tokens 只放变量，V1.1） */")
res.append(wr("css/tokens.css", "\n".join(lines) + "\n"))

# ---------- JS 提取：窗口 + 函数边界切分（不做括号解析，避免字符串/正则误判） ----------
def win(a, b):
    i = html.index(a)
    j = html.index(b, i)
    return html[i:j]

W1 = win("function esc(", "/* ---------------- 全局状态 ---------------- */")
W2 = win("function n2(", "/* ================= V2 新增业务动作")
W3 = win("function kpi(", "\nObject.defineProperty(window,")

def trim(seg):
    """seg 以 'function ' 开头；截到函数结束（同行或顶格 } ），丢弃尾部注释杂项。"""
    lines = seg.split("\n")
    if lines[0].rstrip().endswith("}") and lines[0].count("{") >= lines[0].count("}"):
        return lines[0].rstrip()
    out = []
    for ln in lines:
        out.append(ln)
        if ln.rstrip() == "}":
            break
    return "\n".join(out).rstrip()

fns, fsize = {}, {}
for wi, w in enumerate([W1, W2, W3], 1):
    for seg in re.split(r"(?=\nfunction )", "\n" + w):
        seg = seg.lstrip("\n")
        if not seg.startswith("function "):
            continue
        name = re.match(r"function\s+([A-Za-z_$][\w$]*)", seg).group(1)
        code = trim(seg)
        fns[name] = code
        fsize[name] = (wi, code.count("{") - code.count("}"))

pal = re.search(r"var PAL=\[[^\]]*\];", html).group(0)
ORDER = ["esc", "pad", "nf", "pct", "n2", "pc", "ii", "pp", "stTag", "bandTag",
         "sumBy", "wavgBy", "normCdf", "twoProp", "srmTest", "synRow", "kpi", "objCard",
         "svg", "lineChart", "hbars", "donut", "radar", "columns", "stacked", "spark"]
missing = [f for f in ORDER if f not in fns]
assert not missing, "MISSING:" + ",".join(missing)
unbal = {k: v for k, v in fsize.items() if v[1] != 0}
parts = [pal] + [fns[f] for f in ORDER]
print("js win bytes:", len(W1), len(W2), len(W3), " fns:", len(fns), " unbalanced:", unbal)
print("js body bytes:", sum(len(p.encode("utf-8")) for p in parts))

JSHDR = ("/* ===========================================================================\n"
         "   游侠 \u00b7 浦发风格 图表与格式化运行时  youxia-charts.js  V1.0（2026-11-05）\n"
         "   零依赖 \u00b7 函数体从母版 V2.3 原样搬运（未重写实现），保证模板出图与现行原型一致。\n"
         "   格式化：esc pad nf pct n2 pc ii pp | 徽标：stTag bandTag kpi objCard synRow\n"
         "   统计：normCdf twoProp srmTest sumBy wavgBy（p 值一律 0..1；缺数返回 null）\n"
         "   图表：svg lineChart hbars columns spark donut stacked radar + 色板 PAL\n"
         "   红线：数值缺失传 null \u2192 渲染\u300c\u2014\u300d；禁止用 0 顶替缺数；禁止把 SVG 当图片贴死数据。\n"
         "   ========================================================================== */\n")
res.append(wr("js/youxia-charts.js", JSHDR + "\n\n".join(parts) + "\n"))
io.open(os.path.join(OUT, "tools", "extract_report.json"), "w", encoding="utf-8").write(json.dumps(
    {"source_master": os.path.basename(SRC), "source_master_sha256": sha_src,
     "dropped_project_rules": dropped, "js_functions": [p.split("(")[0].replace("function ", "").strip() for p in parts],
     "js_missing": missing, "files": [[n, s, h] for n, s, h in res]}, ensure_ascii=False, indent=1))
print("dropped:", len(dropped), " js fns:", len(parts), " missing:", missing)
for n, s, h in res:
    print("  %-24s %8dB  sha %s" % (n, s, h))
print("OK")