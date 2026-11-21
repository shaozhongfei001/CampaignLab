/* ===========================================================================
   游侠 · 浦发风格 壳层运行时  youxia-shell.js  V1.0（2026-11-05）
   职责：左导航折叠 / 视图注册与切换 / 页头 seg / 抽屉 / 轻提示 / 事件委托。
   约定：DOM 骨架必须含 .shell > .rail + .main(.appbar + .pagebar#pagebar + .view#viewHost)，
        以及 body 末尾的 #scrim / #sheetHost / #toast。缺任一节点只降级不报错。
   数据无关：本文件不含任何业务字段、演示数据与故事步骤；视图内容全部由页面注册进来。
   依赖：youxia-charts.js 的 esc()（若缺失则内部兜底）。
   =========================================================================== */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var E = (typeof esc === "function") ? esc : function (s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); };

  var YX = {
    views: {},          /* id -> {title,sub,group,segs,fn} */
    sheets: {},         /* id -> function():html */
    hooks: {},          /* {act(name,el), afterRender(cfg), beforeNav(id)} */
    current: null,
    state: {},          /* 页面共享状态容器（由业务页自行读写） */
    render: render, nav: nav, say: say, openSheet: openSheet, closeSheet: closeSheet,
    register: register, init: init
  };

  function register(id, cfg) { YX.views[id] = cfg; return YX; }

  /* ---------------- 页头 ---------------- */
  function pagebarHTML(cfg) {
    var seg = (cfg.segs || []).map(function (x) {
      return '<a href="#' + x[0] + '" data-nav="' + x[0] + '" class="' + (x[0] === YX.current ? "on" : "") + '"><b>' + E(x[1]) + '</b>' + (x[2] == null ? "" : x[2]) + '</a>';
    }).join("");
    return '<span class="pt">' + E(cfg.title || "") + '</span><span class="ps">' + E(cfg.sub || "") + '</span>'
         + '<div class="sp"></div>' + (seg ? '<nav class="seg">' + seg + '</nav>' : "");
  }

  /* ---------------- 渲染 ---------------- */
  function render() {
    var cfg = YX.views[YX.current];
    var host = $("#viewHost"), pb = $("#pagebar");
    if (!host) return;
    if (!cfg) {
      host.innerHTML = '<div class="banner danger"><span class="ic">!</span><div><b>视图未注册：</b>' + E(YX.current) + '</div></div>';
      return;
    }
    if (pb) pb.innerHTML = pagebarHTML(cfg);
    try {
      host.innerHTML = (typeof cfg.fn === "function") ? cfg.fn() : (cfg.fn || "");
    } catch (e) {
      /* 渲染失败必须可见：不给空白页 */
      host.innerHTML = '<div class="banner danger"><span class="ic">!</span><div><b>本页渲染失败：</b>' + E(e && e.message) + '</div></div>';
      if (window.console) console.error(e);
    }
    /* 长页整屏滚动（母版 V2.3 规则，卡片高度不被 flex 压缩） */
    host.classList.toggle("vscroll", !!host.querySelector(":scope>.screen.v2scroll"));
    syncNav();
    if (YX.hooks.afterRender) YX.hooks.afterRender(cfg);
  }

  /* ---------------- 导航高亮（rail-item 按 group，其余按视图 id） ---------------- */
  function syncNav() {
    var cfg = YX.views[YX.current] || {};
    $$("[data-nav]").forEach(function (a) {
      var v = a.getAttribute("data-nav");
      if (a.classList.contains("rail-item")) {
        var g = a.getAttribute("data-group");
        a.classList.toggle("on", g ? (g === cfg.group) : (v === YX.current));
      } else {
        a.classList.toggle("on", v === YX.current);
      }
    });
  }

  function nav(v) {
    if (!YX.views[v]) return;
    if (YX.hooks.beforeNav && YX.hooks.beforeNav(v) === false) return;
    YX.current = v;
    if (location.hash.slice(1) !== v) { try { location.hash = v; } catch (e) {} }
    render();
    var m = $(".main"); if (m && m.scrollTop) m.scrollTop = 0;
  }

  /* ---------------- 轻提示 ---------------- */
  var toastTimer = null;
  function say(msg, cls, ms) {
    var t = $("#toast");
    if (!t) return;
    t.className = "toast on " + (cls || "");
    t.innerHTML = msg;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.className = "toast " + (cls || ""); }, ms || 3600);
  }

  /* ---------------- 右侧抽屉 ---------------- */
  var sheetTimer = null;
  function openSheet(id) {
    var fn = YX.sheets[id];
    var host = $("#sheetHost");
    if (!fn || !host) return;
    clearTimeout(sheetTimer);
    host.innerHTML = (typeof fn === "function") ? fn() : fn;
    var sc = $("#scrim"); if (sc) sc.classList.add("on");
    requestAnimationFrame(function () { var el = host.querySelector(".sheet"); if (el) el.classList.add("on"); });
  }
  function closeSheet() {
    clearTimeout(sheetTimer);
    var sc = $("#scrim"); if (sc) sc.classList.remove("on");
    var host = $("#sheetHost");
    if (host) {
      var el = host.querySelector(".sheet");
      if (el) el.classList.remove("on");
      sheetTimer = setTimeout(function () { host.innerHTML = ""; }, 240);
    }
  }

  /* ---------------- 事件委托（一次绑定，全页生效） ---------------- */
  function bind() {
    document.addEventListener("click", function (e) {
      var t = e.target;
      if (!t || !t.closest) return;
      var x;
      if ((x = t.closest("[data-close]"))) { closeSheet(); return; }
      if ((x = t.closest("[data-nav]")) && !x.disabled) { e.preventDefault(); nav(x.getAttribute("data-nav")); return; }
      if ((x = t.closest("[data-open]")) && !x.disabled) { openSheet(x.getAttribute("data-open")); return; }
      if ((x = t.closest("[data-say]")) && !x.disabled) { say(x.getAttribute("data-say"), x.getAttribute("data-tone")); return; }
      if ((x = t.closest("#scrim"))) { closeSheet(); return; }
      if ((x = t.closest("[data-act]")) && !x.disabled && YX.hooks.act) { YX.hooks.act(x.getAttribute("data-act"), x); return; }
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeSheet(); });
  }

  /* ---------------- 初始化 ---------------- */
  function init(opt) {
    opt = opt || {};
    if (opt.views) for (var k in opt.views) if (Object.prototype.hasOwnProperty.call(opt.views, k)) YX.views[k] = opt.views[k];
    if (opt.sheets) for (var s2 in opt.sheets) if (Object.prototype.hasOwnProperty.call(opt.sheets, s2)) YX.sheets[s2] = opt.sheets[s2];
    if (opt.hooks) for (var h in opt.hooks) if (Object.prototype.hasOwnProperty.call(opt.hooks, h)) YX.hooks[h] = opt.hooks[h];
    if (opt.state) YX.state = opt.state;

    var fold = $("#fold");
    if (fold) fold.addEventListener("click", function () { document.body.classList.toggle("rail-collapsed"); });

    var order = Object.keys(YX.views);
    var hash = location.hash.slice(1);
    YX.current = YX.views[hash] ? hash : (opt.start || order[0]);
    bind();
    window.addEventListener("hashchange", function () {
      var v = location.hash.slice(1);
      if (YX.views[v] && v !== YX.current) { YX.current = v; render(); }
    });
    render();
    return YX;
  }

  window.YX = YX;
  /* 兼容母版 V2.3 里的裸函数名写法，便于整段搬运既有视图代码 */
  window.render = render; window.nav = nav; window.say = say;
  window.openSheet = openSheet; window.closeSheet = closeSheet; window.pagebarHTML = pagebarHTML;
})();
