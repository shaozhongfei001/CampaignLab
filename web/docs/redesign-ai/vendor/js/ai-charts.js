/* ai-charts.js · 模板未覆盖的图：贡献瀑布 / 零轴发散条 / 本体关系图（提案并入 youxia-charts V1.1，CR-CHART-01）
   红线同模板：缺数传 null 渲染「—」；不把 SVG 当图片贴死数据。 */
var AIC = {
  waterfall: function(steps,opt){
    opt=opt||{};
    var w=opt.w||430,h=opt.h||190,pl=opt.pl||8,pr=opt.pr||8,pt=16,pb=40;
    var vals=[];steps.forEach(function(s){vals.push(s.from,s.to);});
    var mn=opt.min!=null?opt.min:Math.min.apply(null,vals),mx=opt.max!=null?opt.max:Math.max.apply(null,vals);
    var pad=(mx-mn)*.12||1;mn-=pad;mx+=pad;
    var iw=w-pl-pr,ih=h-pt-pb;
    function Y(v){return pt+ih*(1-(v-mn)/(mx-mn));}
    var step=iw/steps.length,bw=Math.min(46,step*.6),inner="",prevTop=null;
    steps.forEach(function(s,i){
      var cx=pl+step*i+step/2,x=cx-bw/2;
      var yTop=Y(Math.max(s.from,s.to)),yBot=Y(Math.min(s.from,s.to));
      var fill=s.type==="tot"?"#0048d8":(s.type==="neg"?"#e74c3c":"#18a890");
      if(prevTop!=null)inner+='<line class="wflink" x1="'+(cx-step/2+bw/2)+'" y1="'+prevTop+'" x2="'+x+'" y2="'+prevTop+'"/>';
      inner+='<rect x="'+x+'" y="'+yTop+'" width="'+bw+'" height="'+Math.max(2,yBot-yTop)+'" rx="3" fill="'+fill+'" opacity="'+(s.type==="tot"?1:.88)+'"/>';
      var dv=(s.to-s.from);
      var lab=(s.type==="tot")?s.tot:((dv>=0?"+":"")+(Math.round(dv*100)/100));
      inner+='<text class="axb" x="'+cx+'" y="'+(yTop-5)+'" text-anchor="middle">'+esc(lab)+'</text>';
      inner+='<text class="ax" x="'+cx+'" y="'+(h-24)+'" text-anchor="middle">'+esc(s.l)+'</text>';
      if(s.sub)inner+='<text class="ax" x="'+cx+'" y="'+(h-12)+'" text-anchor="middle">'+esc(s.sub)+'</text>';
      prevTop=Y(s.to);
    });
    inner+='<line class="axline" x1="'+pl+'" y1="'+(pt+ih)+'" x2="'+(w-pr)+'" y2="'+(pt+ih)+'"/>';
    return svg(w,h,inner);
  },
  divbars: function(items,opt){
    opt=opt||{};var w=opt.w||430,rh=opt.rh||26,pl=opt.pl||70,pr=opt.pr||44,h=items.length*rh+2;
    var mx=opt.max||Math.max.apply(null,items.map(function(x){return Math.abs(x.v);}));
    var iw=w-pl-pr,mid=pl+iw/2,inner='<line class="axline" x1="'+mid+'" y1="0" x2="'+mid+'" y2="'+h+'"/>';
    items.forEach(function(it,i){
      var y=i*rh+4,bh=rh-10,bw=iw/2*(Math.abs(it.v)/mx);
      inner+='<text class="ax" x="'+(pl-6)+'" y="'+(y+bh/2+3)+'" text-anchor="end">'+esc(it.l)+'</text>';
      inner+='<rect x="'+pl+'" y="'+y+'" width="'+iw+'" height="'+bh+'" rx="3" fill="#f2f5fa"/>';
      var x=it.v<0?mid-bw:mid;
      inner+='<rect x="'+x+'" y="'+y+'" width="'+Math.max(2,bw)+'" height="'+bh+'" rx="3" fill="'+(it.c||(it.v<0?"#e74c3c":"#18a890"))+'"/>';
      inner+='<text class="axb" x="'+(w-pr+8)+'" y="'+(y+bh/2+3)+'" text-anchor="start">'+esc(it.t!=null?it.t:it.v)+'</text>';
    });
    return svg(w,h,inner);
  },
  onto: function(opt){
    opt=opt||{};var w=opt.w||420,h=opt.h||250;
    var N=[
      {id:"prod",x:70,y:52,l:"产品",s:"浦闪贷/车贷",cls:"core"},
      {id:"seg",x:70,y:128,l:"客群",s:"优客/普客",cls:""},
      {id:"app",x:196,y:52,l:"申请",s:"进件/审批",cls:""},
      {id:"asset",x:196,y:128,l:"资产",s:"放款/账期",cls:""},
      {id:"risk",x:322,y:128,l:"风险事件",s:"首逾/不良",cls:"risk"},
      {id:"met",x:322,y:52,l:"指标对象",s:"通过率/触达率",cls:"met"}
    ];
    var E=[
      {a:"prod",b:"seg",l:"包含",cls:"ok"},
      {a:"prod",b:"app",l:"产生",cls:"ok"},
      {a:"app",b:"asset",l:"形成",cls:"ok"},
      {a:"asset",b:"risk",l:"作用于",cls:"ok"},
      {a:"met",b:"app",l:"度量",cls:"ok"},
      {a:"seg",b:"risk",l:"禁止直连",cls:"no"}
    ];
    function n(id){for(var i=0;i<N.length;i++)if(N[i].id===id)return N[i];return N[0];}
    var inner="";
    E.forEach(function(e){var a=n(e.a),b=n(e.b);
      var mx=(a.x+b.x)/2,my=(a.y+b.y)/2;
      if(e.cls==="no"){
        inner+='<path class="eg no" d="M '+a.x+' '+(a.y+19)+' Q '+mx+' '+(a.y+62)+' '+b.x+' '+(b.y+19)+'"/>';
        inner+='<text class="el" x="'+mx+'" y="'+(a.y+58)+'">'+esc(e.l)+'</text>';
      }else{
        inner+='<line class="eg '+e.cls+'" x1="'+a.x+'" y1="'+a.y+'" x2="'+b.x+'" y2="'+b.y+'"/>';
        inner+='<text class="el" x="'+mx+'" y="'+(my-4)+'">'+esc(e.l)+'</text>';
      }});
    N.forEach(function(d){
      inner+='<rect class="nd '+d.cls+'" x="'+(d.x-46)+'" y="'+(d.y-19)+'" width="92" height="38" rx="8"/>';
      inner+='<text class="nl" x="'+d.x+'" y="'+(d.y-2)+'">'+esc(d.l)+'</text>';
      inner+='<text class="ns" x="'+d.x+'" y="'+(d.y+11)+'">'+esc(d.s)+'</text>';});
    return svg(w,h,inner,"onto");
  }
};