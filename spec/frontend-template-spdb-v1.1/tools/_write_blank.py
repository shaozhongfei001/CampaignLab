# -*- coding: utf-8 -*-
import io, os
OUT = r"D:\ws\codex\游侠前端设计模板_浦发风格_V1_20261105"

HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(T)s</title>
<link rel="stylesheet" href="css/tokens.css">
<link rel="stylesheet" href="css/youxia-ui.css">
</head>
"""

# =====================================================================
# 1) 起手页 template_blank.html
# =====================================================================
BLANK = HEAD % dict(T="游侠设计模板 · 起手页 template_blank") + r"""<body>
<div class="shell">
  <!-- ========== L2 壳层：左导航（rail） ========== -->
  <aside class="rail" id="rail">
    <div class="rail-top">
      <div class="mark">项</div>
      <div class="nm">系统名称<small>EN SUBTITLE</small></div>
      <button class="fold" id="fold" title="收起导航">&#8249;</button>
    </div>
    <div class="rail-group">分组标题一</div>
    <a class="rail-item" href="#p01" data-nav="p01" data-group="g1"><span class="ic">01</span><b>页面名称</b><span class="em">P01</span></a>
    <div class="rail-sub">
      <a href="#p01" data-nav="p01"><i></i>P01 子页名称</a>
      <a href="#p02" data-nav="p02"><i></i>P02 子页名称</a>
    </div>
    <div class="rail-group">分组标题二</div>
    <a class="rail-item" href="#p03" data-nav="p03" data-group="g2"><span class="ic">02</span><b>页面名称</b><span class="em">P03</span></a>
    <div class="rail-foot">
      <div class="synth"><i></i><span>数据来源标注位（示例／生产）</span></div>
    </div>
  </aside>

  <div class="main">
    <!-- ========== 顶栏（appbar） ========== -->
    <div class="appbar">
      <div class="logo">机构 · 系统全称<small>所属模块</small></div>
      <span class="chip ver">TEMPLATE V1.1</span>
      <div class="sp"></div>
      <span class="hdr-item"><i class="dot"></i>统一状态模型</span>
      <span class="hdr-item">操作者 <b>张三</b> <span class="mono">A-0001</span></span>
      <span class="clock num" id="clk">--:--:--</span>
    </div>
    <!-- ========== 页头（脚本渲染）与视图宿主 ========== -->
    <div class="pagebar" id="pagebar"></div>
    <div class="view on" id="viewHost"></div>
  </div>
</div>

<div class="scrim" id="scrim" data-close></div>
<div id="sheetHost"></div>
<div class="toast" id="toast"></div>

<script src="js/youxia-charts.js"></script>
<script src="js/youxia-shell.js"></script>
<script>
/* 起手页示例：三个视图，展示壳层 + 卡片 + 图表 + 抽屉的正确用法。
   业务页请整体替换 viewP01/P02/P03 与 VIEWS 配置。 */
var SEGS = [["p01","P01","概览"],["p02","P02","明细"],["p03","P03","配置"]];
var L = ["W1","W2","W3","W4","W5","W6","W7","W8","W9"];

function viewP01(){
  return '<div class="screen">'
    + '<div class="pg cols">'
      + '<div class="kpirow">'
        + kpi("指标名称","1,284","较上周期 <b>+2.1%</b>","ok")
        + kpi("指标名称","96.4%","阈值 95.0% 之上")
        + kpi("指标名称","\u2014","缺数显示破折号，不得用 0 顶替")
        + kpi("指标名称","18","阻断 3 项","bad")
      + '</div>'
      + '<div class="gates">'
        + '<div class="gate ok"><div class="gi">&#10003;</div><div style="min-width:0"><div class="gt">闸门名称</div><div class="gv">已通过</div><div class="gs">闸门说明一行写完</div></div><div class="gx"><span class="tag ok">PASS</span></div></div>'
        + '<div class="gate warn"><div class="gi">2</div><div style="min-width:0"><div class="gt">闸门名称</div><div class="gv">待复核</div><div class="gs">缺证据时不得推进</div></div><div class="gx"><button class="btn btn-sm" data-open="sh1">查看</button></div></div>'
        + '<div class="gate bad"><div class="gi">&#215;</div><div style="min-width:0"><div class="gt">闸门名称</div><div class="gv">已阻断</div><div class="gs">阻断原因必须写清</div></div><div class="gx"><span class="tag bad">FAILED</span></div></div>'
      + '</div>'
      + '<div class="two" style="min-height:0">'
        + '<section class="card"><div class="card-h"><span class="t">趋势 · 双口径分列</span><span class="meta">观察结果不构成因果结论</span></div>'
          + '<div class="card-b scroll scroll-thin">'
            + lineChart([{name:"口径 A",color:"#0048d8",data:[132,141,148,152,161,170,175,181,186],fill:"#0048d8"},
                         {name:"口径 B",color:"#8a94a6",data:[98,101,103,109,112,118,121,124,127]}],L,{h:150,threshold:170})
            + '<div class="hint" style="margin-top:6px">阈值线用 <b>stroke-dasharray</b> 单独画出，不与数据线共用样式。</div>'
          + '</div></section>'
        + '<section class="card"><div class="card-h"><span class="t">分布 · 横向条形</span><span class="meta">仅正值；负值会被夹成 2px</span></div>'
          + '<div class="card-b scroll scroll-thin">'
            + hbars([{l:"类别甲",v:412},{l:"类别乙",v:288},{l:"类别丙",v:164,c:"#18a890"},{l:"类别丁",v:97},{l:"类别戊",v:38,c:"#e74c3c"}],{rh:26})
            + '<div class="hr"></div>'
            + columns([{l:"A",v:12},{l:"B",v:19,t:"19"},{l:"C",v:7},{l:"D",v:24,t:"24"},{l:"E",v:3}],{h:96})
          + '</div></section>'
      + '</div>'
    + '</div></div>';
}

function viewP02(){
  var rows = [["OBJ-0001","示例对象甲",nf(1284),"38.2%","PASS","09:12:04",0],
              ["OBJ-0002","示例对象乙",nf(912),"27.1%","REVIEW","09:14:22",1],
              ["OBJ-0003","示例对象丙","\u2014","\u2014","FAILED","09:16:01",2],
              ["OBJ-0004","示例对象丁",nf(404),"12.0%","PENDING","09:18:44",0]].map(function(r){
    return '<tr class="'+(r[6]===2?"rowbad":(r[6]===1?"roww":""))+'"><td class="mono">'+r[0]+'</td><td class="wrap">'+r[1]
      + '</td><td class="r num">'+r[2]+'</td><td class="r num">'+r[3]+'</td><td>'+stTag(r[4])+'</td><td class="mono">'+r[5]+'</td></tr>';
  }).join("");
  return '<div class="screen v2scroll"><div class="pg cols">'
    + '<div class="statusband"><div class="sb-l"><div><div class="t">流程状态</div><div class="s">节点只反映已发生事实</div></div></div>'
      + '<div class="sb-flow">'
        + '<div class="sb-node done"><span class="n">1</span><span class="tx"><b>生成</b><span>09:12 已完成</span></span></div>'
        + '<div class="sb-node done"><span class="n">2</span><span class="tx"><b>复核</b><span>09:14 已完成</span></span></div>'
        + '<div class="sb-node now"><span class="n">3</span><span class="tx"><b>提交</b><span>当前节点</span></span></div>'
        + '<div class="sb-node wait"><span class="n">4</span><span class="tx"><b>回执</b><span>未发生</span></span></div>'
      + '</div><div class="sb-r"><span class="chip">合计 <b class="num">2,604</b></span></div></div>'
    + '<section class="card"><div class="card-h"><span class="t">明细表</span><span class="meta">数据密集区首选表格，不用卡片网格堆表</span></div>'
      + '<div class="card-b flush scroll"><table class="tbl"><thead><tr><th>编号</th><th>名称</th><th class="r">数值</th><th class="r">占比</th><th>状态</th><th>更新时间</th></tr></thead>'
      + '<tbody>'+rows+'</tbody></table></div>'
      + '<div class="card-f"><span class="tiny">表尾只放影响本页判断的事实</span><span class="note">共 4 条</span></div></section>'
    + '<div class="two">'
      + '<section class="card"><div class="card-h"><span class="t">空状态</span></div><div class="card-b">'
        + '<div class="empty"><div class="big">&#9723;</div><b>暂无可展示的数据</b><div class="tiny">说明为什么没有，以及下一步做什么；不得留白屏或写 0。</div></div>'
      + '</div></section>'
      + '<section class="card"><div class="card-h"><span class="t">提示条</span></div><div class="card-b">'
        + '<div class="banner info"><span class="ic">i</span><div><b>口径：</b>统计口径说明放在数字之前。</div></div>'
        + '<div class="banner warn"><span class="ic">!</span><div><b>注意：</b>降级只向更安全档位。</div></div>'
        + '<div class="banner danger"><span class="ic">&#215;</span><div><b>阻断：</b>缺证据时禁止提交正式动作。</div></div>'
      + '</div></section>'
    + '</div></div></div>';
}

function viewP03(){
  return '<div class="screen"><div class="pg cols">'
    + '<div class="two">'
      + '<section class="card"><div class="card-h"><span class="t">勾选与度量</span></div><div class="card-b">'
        + '<div class="chk ok"><span class="ci">&#10003;</span><span><b>已授权项</b>说明对象与范围</span><span class="r">2026-11-18 到期</span></div>'
        + '<div class="chk warn"><span class="ci">!</span><span><b>待确认项</b>需要人工补充证据</span><span class="r">待复核</span></div>'
        + '<div class="chk bad"><span class="ci">&#215;</span><span><b>禁止项</b>客户已明确拒绝，不得再次触达</span><span class="r">已拒绝</span></div>'
        + '<div class="hr"></div>'
        + '<div class="metric-line"><span>度量名称</span><b>82.4%</b><span class="bar2"><i style="width:82%"></i></span></div>'
        + '<div class="metric-line"><span>度量名称</span><b>14.7%</b><span class="bar2"><i style="width:15%"></i></span></div>'
        + '<div class="metric-line"><span>度量名称（缺数）</span><b style="color:var(--ink-400)">\u2014</b><span class="bar2"><i style="width:0"></i></span></div>'
      + '</div></section>'
      + '<section class="card"><div class="card-h"><span class="t">图表复用</span><span class="meta">雷达／环形／迷你线</span></div><div class="card-b">'
        + '<div style="max-width:230px;margin:0 auto">'+radar([{l:"维度一",v:82},{l:"维度二",v:55},{l:"维度三",v:70},{l:"维度四",v:40},{l:"维度五",v:62},{l:"维度六",v:50}],{w:230,h:196,r:62})+'</div>'
        + '<div class="hr"></div>'
        + '<div class="flex" style="justify-content:space-between;align-items:flex-start">'
            + '<div style="flex:none;width:132px">' + donut([{l:"甲",v:44,c:"#0048d8"},{l:"乙",v:31,c:"#18a890"},{l:"丙",v:25,c:"#f39c12"}],{w:132,h:112,r:34,sw:12,center:"3",sub:"类型"}) + '</div>'
            + '<div style="flex:1;min-width:0;margin-left:12px">' + spark([9,11,10,14,13,17,16,19,22],{w:220,h:34,color:"#0048d8"})
            + '<div class="tiny">迷你线只表达形状，不标数值；环形/雷达这类小图必须用定宽 div 包一层</div></div></div>'
      + '</div></section>'
    + '</div>'
    + '<section class="card"><div class="card-h"><span class="t">徽标与按钮</span></div><div class="card-b">'
      + '<div class="tagline">'+stTag("PASS")+stTag("PENDING_REVIEW")+stTag("FAILED")+bandTag("LOW")+bandTag("MID")+bandTag("HIGH")
        + '<span class="tag sys">系统</span><span class="tag ai">候选</span><span class="tag syn">示例</span></div>'
      + '<div class="hr"></div>'
      + '<div class="btnrow"><span class="pill ok">ok</span><span class="pill warn">warn</span><span class="pill danger">danger</span>'
        + '<span class="pill info">info</span><span class="pill gray">gray</span><span class="pill violet">violet</span></div>'
      + '<div class="hr"></div>'
      + '<div class="btnrow">'
        + '<button class="btn btn-p" data-say="主操作示例">主操作</button>'
        + '<button class="btn" data-open="sh1">打开抽屉</button>'
        + '<button class="btn btn-s" data-act="demo">data-act 钩子</button>'
        + '<button class="btn btn-g">次级</button>'
        + '<button class="btn btn-ok">通过</button>'
        + '<button class="btn btn-d">拒绝</button>'
        + '<button class="btn btn-sm">小按钮</button>'
        + '<button class="btn" disabled>禁用态</button>'
      + '</div>'
    + '</div></section>'
    + '</div></div>';
}

var SHEETS = { sh1: function(){
  return '<div class="sheet"><div class="sheet-h"><div class="t">抽屉标题<span class="tag warn">待复核</span></div>'
    + '<div class="s">抽屉放明细、证据与时间线；关闭方式：右上角／点遮罩／Esc。<button class="btn btn-sm x" data-close>关闭</button></div></div>'
    + '<div class="sheet-b">'
      + '<div class="sec-t">证据链<span class="r">只列可回放来源</span></div>'
      + '<div class="evrow"><span class="ev"><span class="i">&#9670;</span>来源一 · 09:12:04</span><span class="ev"><span class="i">&#9670;</span>SESS-0001</span><span class="ev"><span class="i">&#9670;</span>规则 v3.2</span></div>'
      + '<div class="sec-t" style="margin-top:12px">时间线</div>'
      + '<div class="tl">'
        + '<div class="tl-i done"><span class="d"></span><div class="h"><span class="ti">事件标题</span><span class="tm num">09:12</span></div><div class="m">事件说明，只写已发生事实。</div></div>'
        + '<div class="tl-i warn"><span class="d"></span><div class="h"><span class="ti">当前事件</span><span class="tm num">09:14</span></div><div class="m">等待人工确认，未确认前不得提交。</div></div>'
        + '<div class="tl-i trim"><span class="d"></span><div class="h"><span class="ti">未发生事件</span><span class="tm num">\u2014</span></div><div class="m">裁剪节点或尚未到达的节点不得预填时间。</div></div>'
      + '</div>'
    + '</div>'
    + '<div class="sheet-f"><button class="btn" data-close>关闭</button> <button class="btn btn-p" data-close data-say="已写入本地记录（示例）">确认</button></div></div>';
}};

YX.init({
  start: "p01",
  sheets: SHEETS,
  views: {
    p01: {title:"页面标题 · 一句话职责", sub:"P01 · 页头 seg 由壳层自动生成", group:"g1", segs:SEGS, fn:viewP01},
    p02: {title:"页面标题 · 长页整屏滚动", sub:"P02 · screen.v2scroll 自动切换滚动模式", group:"g1", segs:SEGS, fn:viewP02},
    p03: {title:"页面标题 · 控件页", sub:"P03 · 控件、徽标与图表集合", group:"g2", segs:SEGS, fn:viewP03}
  },
  hooks: { act: function(name){ say("data-act=" + name + " 由业务页 hooks.act 处理"); } }
});
(function tick(){ var c = document.getElementById("clk"); if (c) { c.textContent = new Date().toTimeString().slice(0,8); } setTimeout(tick,1000); })();
</script>
</body></html>
"""
io.open(os.path.join(OUT, "template_blank.html"), "w", encoding="utf-8", newline="\n").write(BLANK)
print("blank", len(BLANK.encode("utf-8")))
