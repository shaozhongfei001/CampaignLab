/* ===========================================================================
   游侠 · 浦发风格 图表与格式化运行时  youxia-charts.js  V1.0（2026-11-05）
   零依赖 · 函数体从母版 V2.3 原样搬运（未重写实现），保证模板出图与现行原型一致。
   格式化：esc pad nf pct n2 pc ii pp | 徽标：stTag bandTag kpi objCard synRow
   统计：normCdf twoProp srmTest sumBy wavgBy（p 值一律 0..1；缺数返回 null）
   图表：svg lineChart hbars columns spark donut stacked radar + 色板 PAL
   红线：数值缺失传 null → 渲染「—」；禁止用 0 顶替缺数；禁止把 SVG 当图片贴死数据。
   ========================================================================== */
var PAL=["#0048d8","#18a890","#f39c12","#8a94a6","#e74c3c","#60c0a8","#3368e0"];

function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}

function pad(n){return n<10?"0"+n:""+n;}

function nf(n,d){return Number(n).toFixed(d==null?0:d).replace(/\B(?=(\d{3})+(?!\d))/g,",");}

function pct(n,d){return (n*100).toFixed(d==null?1:d)+"%";}

function n2(v,d){ return (v==null||v==="")?"—":Number(v).toFixed(d==null?2:d); }

function pc(v,d){ return (v==null||v==="")?"—":(Number(v)*100).toFixed(d==null?2:d)+"%"; }

function ii(v){ return (v==null||v==="")?"—":nf(Number(v),0); }

function pp(v,d){ return (v==null||isNaN(v))?"—":(v>=0?"+":"")+(v*100).toFixed(d==null?2:d)+"pp"; }

function stTag(s){
  var c=(s==="PASS"||s==="OK"||s==="APPROVED")?"ok":((s==="WARN"||s==="REVIEW"||s==="PENDING_REVIEW"||s==="DEGRADED"||s==="INFO")?"warn":"bad");
  return '<span class="tag '+c+'">'+esc(s==null?"—":s)+'</span>';
}

function bandTag(s){ var c=(s==="LOW"||s==="OK")?"ok":((s==="MID"||s==="WARN")?"warn":"bad"); return '<span class="tag '+c+'">'+esc(s==null?"—":s)+'</span>'; }

function sumBy(a,f){ var t=0; (a||[]).forEach(function(x){ var v=f(x); if(v!=null&&!isNaN(v)) t+=Number(v); }); return t; }

function wavgBy(a,fn,fw){ var n=0,d=0; (a||[]).forEach(function(x){ var w=Number(fw(x))||0,v=Number(fn(x)); if(!isNaN(v)){n+=v*w;d+=w;} }); return d?n/d:null; }

function normCdf(z){
  var t=1/(1+0.2316419*Math.abs(z));
  var s=1-0.3989422804014327*Math.exp(-z*z/2)*t*(0.319381530+t*(-0.356563782+t*(1.781477937+t*(-1.821255978+t*1.330274429))));
  return z>=0?s:1-s;
}

function twoProp(x1,n1,x2,n2){
  var p1=n1?x1/n1:0,p2=n2?x2/n2:0,d=p2-p1;
  var se=Math.sqrt((n1?p1*(1-p1)/n1:0)+(n2?p2*(1-p2)/n2:0));
  var z=se?d/se:0,pv=se?2*(1-normCdf(Math.abs(z))):null;
  return {p1:p1,p2:p2,diff:d,se:se,lo:d-1.96*se,hi:d+1.96*se,z:z,p:pv,ciCross0:(d-1.96*se<=0&&d+1.96*se>=0)};
}

function srmTest(n1,n2){
  var tot=n1+n2,e=tot/2,chi=e?((n1-e)*(n1-e)/e+(n2-e)*(n2-e)/e):0;
  return {chi:chi,p:2*(1-normCdf(Math.sqrt(chi))),diff:tot?Math.abs(n1-n2)/tot:null};
}

function synRow(cls){ return cls||""; }

function kpi(l,v,s,cls){return '<div class="kpi2 '+(cls||"")+'"><div class="l">'+l+'</div><div class="v">'+v+'</div><div class="s">'+(s||"&nbsp;")+'</div></div>';}

function objCard(i,l,v,st,cls){return '<div class="obj '+(cls||"")+'"><span class="idx">'+i+'</span><div class="l">'+l+'</div><div class="v" title="'+esc(v)+'">'+esc(v)+'</div><div class="st">'+st+'</div></div>';}

function svg(w,h,inner,cls){return '<svg class="chart '+(cls||"")+'" viewBox="0 0 '+w+' '+h+'" width="100%" height="'+h+'" role="img">'+inner+'</svg>';}

function lineChart(series,labels,opt){
  opt=opt||{};var w=opt.w||420,h=opt.h||132,pl=30,pr=8,pt=10,pb=18;
  var all=[];series.forEach(function(s){all=all.concat(s.data);});
  var mn=opt.min!=null?opt.min:Math.min.apply(null,all),mx=opt.max!=null?opt.max:Math.max.apply(null,all);
  var pad0=(mx-mn)*.14||1;if(opt.min==null)mn=Math.max(0,mn-pad0);mx=mx+pad0;
  var iw=w-pl-pr,ih=h-pt-pb;
  function X(i){return pl+iw*(labels.length<2?0:i/(labels.length-1));}
  function Y(v){return pt+ih*(1-(v-mn)/(mx-mn));}
  var g="",i;
  for(i=0;i<=3;i++){var yy=pt+ih*i/3;g+='<line class="grid" x1="'+pl+'" y1="'+yy+'" x2="'+(w-pr)+'" y2="'+yy+'"/>';
    g+='<text class="ax" x="'+(pl-4)+'" y="'+(yy+3)+'" text-anchor="end">'+(mx-(mx-mn)*i/3).toFixed(opt.dec==null?0:opt.dec)+'</text>';}
  if(opt.threshold!=null){g+='<line x1="'+pl+'" y1="'+Y(opt.threshold)+'" x2="'+(w-pr)+'" y2="'+Y(opt.threshold)+'" stroke="#e74c3c" stroke-dasharray="4 3"/>';}
  var L="";series.forEach(function(s){var p="";s.data.forEach(function(v,j){p+=(j?"L":"M")+X(j)+" "+Y(v);});
    if(opt.area&&s.fill){L+='<path d="'+p+'L'+X(s.data.length-1)+' '+(pt+ih)+'L'+pl+' '+(pt+ih)+'Z" fill="'+s.fill+'" opacity=".18"/>';}
    L+='<path d="'+p+'" fill="none" stroke="'+s.color+'" stroke-width="'+(s.width||2)+'" '+(s.dash?'stroke-dasharray="4 3"':'')+' stroke-linejoin="round"/>';
    s.data.forEach(function(v,j){L+='<circle cx="'+X(j)+'" cy="'+Y(v)+'" r="2.2" fill="'+s.color+'" stroke="#fff" stroke-width="1"/>';});});
  var xl="";labels.forEach(function(l,j){if(labels.length<=8||j%Math.max(2,Math.ceil(labels.length/12))===0||j===labels.length-1)xl+='<text class="ax" x="'+X(j)+'" y="'+(h-4)+'" text-anchor="middle">'+esc(l)+'</text>';});
  var lgd="";if(opt.legend!==false)series.forEach(function(s){lgd+='<span><i class="ln" style="background:'+s.color+'"></i>'+esc(s.name)+'</span>';});
  return svg(w,h,g+L+xl)+(lgd?'<div class="legend">'+lgd+'</div>':"");
}

function hbars(items,opt){
  opt=opt||{};var w=opt.w||330,rh=opt.rh||22,pl=opt.pl||82,pr=opt.pr||40,h=items.length*rh+2,inner="";
  var mx=opt.max||Math.max.apply(null,items.map(function(x){return x.v;}));
  items.forEach(function(it,i){var y=i*rh+3,bw=(w-pl-pr)*(it.v/mx);
    inner+='<text class="ax" x="'+(pl-6)+'" y="'+(y+rh/2+1)+'" text-anchor="end">'+esc(it.l)+'</text>';
    inner+='<rect x="'+pl+'" y="'+(y+5)+'" width="'+(w-pl-pr)+'" height="'+(rh-11)+'" rx="3" fill="#f2f5fa"/>';
    inner+='<rect x="'+pl+'" y="'+(y+5)+'" width="'+Math.max(2,bw)+'" height="'+(rh-11)+'" rx="3" fill="'+(it.c||"#0048d8")+'"/>';
    inner+='<text class="axb" x="'+(w-pr+4)+'" y="'+(y+rh/2+1)+'">'+esc(it.t!=null?it.t:it.v)+'</text>';});
  return svg(w,h,inner);
}

function donut(items,opt){
  opt=opt||{};var w=opt.w||150,h=opt.h||110,cx=w/2,cy=h/2,r=opt.r||38,sw=opt.sw||14,tot=0;
  items.forEach(function(x){tot+=x.v;});if(!tot)tot=1;
  var a=-Math.PI/2,inner="";
  items.forEach(function(x){var ang=2*Math.PI*x.v/tot;if(x.v<=0)return;
    var x1=cx+r*Math.cos(a),y1=cy+r*Math.sin(a),x2=cx+r*Math.cos(a+ang),y2=cy+r*Math.sin(a+ang);
    inner+='<path d="M '+x1+' '+y1+' A '+r+' '+r+' 0 '+(ang>Math.PI?1:0)+' 1 '+x2+' '+y2+'" fill="none" stroke="'+(x.c||"#0048d8")+'" stroke-width="'+sw+'" '+(x.dash?'stroke-dasharray="3 2"':'')+'/>';
    a+=ang;});
  inner+='<text x="'+cx+'" y="'+(cy-1)+'" text-anchor="middle" style="font-size:16px;font-weight:700;fill:#1a2438">'+esc(opt.center||"")+'</text>';
  inner+='<text x="'+cx+'" y="'+(cy+12)+'" text-anchor="middle" style="font-size:8.5px;fill:#8896a8">'+esc(opt.sub||"")+'</text>';
  var lgd=items.map(function(x){return '<span><i style="background:'+(x.c||"#0048d8")+';border-radius:50%"></i>'+esc(x.l)+' '+esc(x.t||x.v)+'</span>';}).join("");
  return svg(w,h,inner)+(opt.legend===false?"":'<div class="legend">'+lgd+'</div>');
}

function radar(items,opt){
  opt=opt||{};var w=opt.w||210,h=opt.h||180,cx=w/2,cy=h/2+4,R=opt.r||66,n=items.length,inner="";
  for(var k=1;k<=4;k++){var pts=[];for(var i=0;i<n;i++){var a=-Math.PI/2+2*Math.PI*i/n,rr=R*k/4;pts.push((cx+rr*Math.cos(a))+" "+(cy+rr*Math.sin(a)));}
    inner+='<polygon points="'+pts.join(",")+'" fill="none" stroke="#eef2f7" stroke-width="1"/>';}
  for(var i=0;i<n;i++){var a=-Math.PI/2+2*Math.PI*i/n;inner+='<line x1="'+cx+'" y1="'+cy+'" x2="'+(cx+R*Math.cos(a))+'" y2="'+(cy+R*Math.sin(a))+'" stroke="#eef2f7"/>';}
  var pts2=[];items.forEach(function(it,i){var a=-Math.PI/2+2*Math.PI*i/n,rr=R*(it.v/100);pts2.push((cx+rr*Math.cos(a))+" "+(cy+rr*Math.sin(a)));});
  inner+='<polygon points="'+pts2.join(",")+'" fill="rgba(0,72,216,.13)" stroke="#0048d8" stroke-width="1.6"/>';
  items.forEach(function(it,i){var a=-Math.PI/2+2*Math.PI*i/n;var x=cx+R*(it.v/100)*Math.cos(a),y=cy+R*(it.v/100)*Math.sin(a);
    inner+='<circle cx="'+x+'" cy="'+y+'" r="2.4" fill="#0048d8" stroke="#fff" stroke-width="1"/>';});
  items.forEach(function(it,i){var a=-Math.PI/2+2*Math.PI*i/n,rr=R+13,x=cx+rr*Math.cos(a),y=cy+rr*Math.sin(a);
    var anc=Math.abs(Math.cos(a))<.2?"middle":(Math.cos(a)>0?"start":"end");
    inner+='<text x="'+x+'" y="'+(y+3)+'" text-anchor="'+anc+'" style="font-size:8.5px;fill:#4a5568">'+esc(it.l)+'</text>';});
  return svg(w,h,inner);
}

function columns(items,opt){
  opt=opt||{};var w=opt.w||330,h=opt.h||100,pl=26,pr=6,pt=8,pb=18;
  var mx=opt.max||Math.max.apply(null,items.map(function(x){return x.v;}))||1,iw=w-pl-pr,ih=h-pt-pb;
  var step=iw/items.length,bw=step*.56,inner="";
  for(var i=0;i<=2;i++){var yy=pt+ih*i/2;inner+='<line class="grid" x1="'+pl+'" y1="'+yy+'" x2="'+(w-pr)+'" y2="'+yy+'"/>';}
  items.forEach(function(it,i){var bh=ih*(it.v/mx),x=pl+step*i+(step-bw)/2,y=pt+ih-bh;
    inner+='<rect x="'+x+'" y="'+y+'" width="'+bw+'" height="'+Math.max(1,bh)+'" rx="2" fill="'+(it.c||"#3368e0")+'" opacity="'+(it.dim?.45:.9)+'"/>';
    if(it.t)inner+='<text class="axb" x="'+(x+bw/2)+'" y="'+(y-3)+'" text-anchor="middle" style="font-size:8.5px">'+esc(it.t)+'</text>';
    if(items.length<=10||i%2===0)inner+='<text class="ax" x="'+(x+bw/2)+'" y="'+(h-4)+'" text-anchor="middle">'+esc(it.l)+'</text>';});
  return svg(w,h,inner);
}

function stacked(segs,opt){
  opt=opt||{};var w=opt.w||330,h=opt.h||13,tot=0;segs.forEach(function(s){tot+=s.v;});if(!tot)tot=1;
  var x=0,inner="";segs.forEach(function(s){var ww=w*s.v/tot;inner+='<rect x="'+x+'" y="0" width="'+Math.max(0,ww-(s.v?1:0))+'" height="'+h+'" rx="2" fill="'+s.c+'"/>';x+=ww;});
  return svg(w,h,inner);
}

function spark(data,opt){
  opt=opt||{};var w=opt.w||110,h=opt.h||26,mn=Math.min.apply(null,data),mx=Math.max.apply(null,data);if(mx===mn)mx=mn+1;
  var p="";data.forEach(function(v,i){p+=(i?"L":"M")+(i*w/(data.length-1))+" "+(h-2-(h-4)*(v-mn)/(mx-mn));});
  return svg(w,h,'<path d="'+p+'" fill="none" stroke="'+(opt.color||"#0048d8")+'" stroke-width="1.6"/>');
}
