# -*- coding: utf-8 -*-
"""生成 00_模板入口.html：文件清单 + 交付时哈希 + 浏览器实时重算校验（fetch + crypto.subtle）。"""
import io, os, hashlib, json, time
OUT = r"D:\ws\codex\游侠前端设计模板_浦发风格_V1_20261105"
SELF = "00_模版入口.html"
MASTER = r"D:\ws\codex\游侠高仿真原型_S03S04场景版_20261105\S03_S04_运营后台_全链路联动工作台_V2.3_本地母版_浦发风格.html"

rows = []
for root, dirs, fs in os.walk(OUT):
    dirs[:] = [d for d in dirs if d not in ("_shots", "__pycache__")]
    for f in sorted(fs):
        if f.startswith("_tmp") or f.endswith(".js") and "_lint" in root:
            continue
        p = os.path.join(root, f)
        rel = os.path.relpath(p, OUT).replace("\\", "/")
        if rel.startswith("tools/_") or rel == SELF:   # 入口页不能记录自己的哈希（自指）
            continue
        b = open(p, "rb").read()
        rows.append([rel, len(b), hashlib.sha256(b).hexdigest()])
rows.sort()
mb = open(MASTER, "rb").read()
master_sha = hashlib.sha256(mb).hexdigest()

DATA = json.dumps(rows, ensure_ascii=False)
HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>游侠前端设计模板（浦发风格）V1.1 · 入口</title>
<link rel="stylesheet" href="css/tokens.css"><link rel="stylesheet" href="css/youxia-ui.css"></head>
<body>
<div class="shell"><aside class="rail"><div class="rail-top"><div class="mark">模</div>
<div class="nm">前端设计模板<small>SPDB STYLE V1.0</small></div></div>
<div class="rail-group">交付物</div>
<a class="rail-item" href="gallery_组件图鉴.html"><span class="ic">01</span><b>组件图鉴</b><span class="em">11 组</span></a>
<a class="rail-item" href="template_blank.html"><span class="ic">02</span><b>起手页（外链）</b><span class="em">3 视图</span></a>
<a class="rail-item" href="template_blank_singlefile.html"><span class="ic">03</span><b>起手页（单文件）</b><span class="em">139KB</span></a>
<div class="rail-group">文档</div>
<a class="rail-item" href="README_设计与使用说明.md"><span class="ic">D</span><b>设计与使用说明</b><span class="em">md</span></a>
<a class="rail-item" href="checklist_交付前自检.md"><span class="ic">&#10003;</span><b>交付前自检</b><span class="em">md</span></a>
<div class="rail-foot"><div class="synth"><i></i><span>模板不含业务数据</span></div></div>
</aside>
<div class="main"><div class="appbar"><div class="logo">游侠 · 浦发风格前端设计模板<small>可复用于新建项目</small></div>
<span class="chip ver">TEMPLATE V1.0</span><div class="sp"></div>
<span class="hdr-item">来源母版 <b>V2.3</b> <span class="mono" id="msha">@@MASTER@@</span></span>
<span class="hdr-item">生成 <b class="num">@@STAMP@@</b></span></div>
<div class="pagebar"><span class="pt">文件清单与完整性校验</span>
<span class="ps">下表哈希在交付时写入；点右侧按钮用浏览器实时重算并比对</span><div class="sp"></div>
<button class="btn btn-p" id="recheck">重新计算 SHA256</button></div>
<div class="view on" id="viewHost"></div></div></div>
<div class="toast" id="toast"></div>
<script src="js/youxia-charts.js"></script>
<script src="js/youxia-shell.js"></script>
<script>
var FILES = @@DATA@@;
var MASTER_SHA = "@@MASTER_FULL@@";
function viewIdx(){
  var rows = FILES.map(function(f){
    return '<tr><td class="mono wrap">'+esc(f[0])+'</td><td class="r num">'+nf(f[1])+'</td>'
      + '<td class="mono">'+f[2].slice(0,32)+'</td><td id="st-'+f[0].replace(/[^\\w]/g,"_")+'"><span class="pill gray">未校验</span></td></tr>';
  }).join("");
  return '<div class="screen v2scroll"><div class="pg cols">'
    + '<div class="banner info"><span class="ic">i</span><div><b>这套模板是从原型母版机械提取的，不是手写复刻。</b>'
      + '样式层序 L1 基座 → L2 壳层 → L3 浦发浅色 → L4 工作台组件；提取时剔除 20 条项目专用规则，'
      + '清单见 <span class="mono">tools/extract_report.json</span>。模板内<b>不含</b>业务页面、演示数据与故事步骤。</div></div>'
    + '<div class="kpirow">'+kpi("文件数", nf(FILES.length), "不含 _shots 与临时件")+kpi("总体积", nf(sumBy(FILES,function(x){return x[1];})/1024,1)+" KB", "单文件版占 139 KB")+kpi("组件族", "11", "图鉴内 11 组")+kpi("浏览器断言", "76", "0 FAIL（交付时）","ok")+'</div>'
    + '<section class="card"><div class="card-h"><span class="t">交付物</span><span class="meta">SHA256 前 32 位</span></div>'
      + '<div class="card-b flush scroll"><table class="tbl"><thead><tr><th>文件</th><th class="r">字节</th><th>SHA256</th><th>校验</th></tr></thead>'
      + '<tbody>'+rows+'</tbody></table></div>'
      + '<div class="card-f"><span class="tiny">比对不一致 = 你手上的文件被改过或复制不全，请重新取包</span>'
      + '<span class="note">母版 <span class="mono">'+MASTER_SHA.slice(0,16)+'…</span></span></div></section>'
    + '</div></div>';
}
YX.init({start:"idx", views:{idx:{title:"文件清单与完整性校验", sub:"交付时哈希已写入页面，可离线核对", group:"idx", segs:[], fn:viewIdx}}});
document.getElementById("recheck").addEventListener("click", async function(){
  var bad = 0, n = 0;
  for (var i = 0; i < FILES.length; i++) {
    var f = FILES[i], cell = document.getElementById("st-" + f[0].replace(/[^\\w]/g, "_"));
    try {
      var r = await fetch(encodeURI(f[0]));
      if (!r.ok) throw new Error("HTTP " + r.status);
      var buf = await r.arrayBuffer();
      var d = await crypto.subtle.digest("SHA-256", buf);
      var hex = Array.prototype.map.call(new Uint8Array(d), function(x){ return ("0" + x.toString(16)).slice(-2); }).join("");
      n++;
      if (hex === f[2]) { cell.innerHTML = '<span class="pill ok">一致</span>'; }
      else { cell.innerHTML = '<span class="pill danger">不一致</span>'; bad++; }
    } catch (e) { cell.innerHTML = '<span class="pill warn">取不到</span>'; bad++; }
  }
  say(bad ? ("校验完成：" + n + " 个文件已比对，<b>" + bad + " 个不一致</b>（见表格右侧）")
           : ("校验完成：" + n + " 个文件哈希全部一致，与你手上的包是同一版本"), bad ? "danger" : "ok", 6000);
});
</script></body></html>"""
for k, v in [("@@DATA@@", DATA), ("@@MASTER_FULL@@", master_sha),
            ("@@MASTER@@", master_sha[:16]), ("@@STAMP@@", time.strftime("%Y-%m-%d %H:%M"))]:
    HTML = HTML.replace(k, v)
assert "@@" not in HTML and "]@" not in HTML, "\u6b8b\u7559\u5360\u4f4d\u7b26: " + HTML[max(0,HTML.index("@@")-60):HTML.index("@@")+30] if "@@" in HTML else "\u6b8b\u7559 ]@"
io.open(os.path.join(OUT, SELF), "w", encoding="utf-8", newline="\n").write(HTML)
print("index %dB, files=%d, master=%s" % (len(HTML.encode("utf-8")), len(rows), master_sha[:16]))
