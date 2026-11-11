"use strict";

const embedded = JSON.parse(document.getElementById("samples").textContent);
const banks = new Map(embedded.banks.map(raw => [raw.bankId, normalizeBank(raw)]));
const pages = [
  ["review", "策略复盘", "▥"], ["data", "数据与口径", "≡"], ["diagnose", "异常诊断", "⌕"],
  ["simulate", "试算与回放", "▷"], ["report", "报告与改进", "▤"], ["activity", "活动工作台", "▦"],
];
const localKey = "campaignlab.review.v01";
let saved;
try { saved = JSON.parse(localStorage.getItem(localKey) || "{}"); } catch { saved = {}; }
let state = {
  bankId: "A", scope: scopeFor(banks.get("A")), page: "review", advanced: false, overviewDimension: "branch",
  metric: "effective", dimension: "funnel", anomalyRule: "all", question: "", questionResult: null,
  thresholds: {...banks.get("A").metadata.thresholds}, linkResolution: "pending", intakeLog: [],
  importError: "", bankCheck: null, reportType: "策略复盘报告", reportRequest: null,
  scenario: 45, caseId: "SIM-017", rulesChannel: "remote", classResult: null, actionKind: "leakage",
  reports: Array.isArray(saved.reports) ? saved.reports : [],
  actions: Array.isArray(saved.actions) ? saved.actions : [],
  cases: Array.isArray(saved.cases) ? saved.cases : [],
  preflights: saved.preflights || {}, receipts: saved.receipts || {},
};
const el = id => document.getElementById(id);
const bankNow = () => banks.get(state.bankId);
const evidenceKey = () => `${state.bankId}|${bankNow().snapshot}`;
const rowCurrent = () => analyze(bankNow(), state.scope);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const cleanText = value => String(value ?? "").replace(/[\r\n|]/g, " ");
const pill = (s, tone = "") => `<span class="pill ${tone}">${esc(s)}</span>`;
const empty = s => `<div class="empty">${esc(s)}</div>`;
const banner = (s, tone = "") => `<div class="banner ${tone}">${esc(s)}</div>`;
const button = (label, action, {value = "", tone = "", id = "", disabled = false} = {}) =>
  `<button class="button ${tone}" data-action="${esc(action)}" data-value="${esc(value)}"${id ? ` id="${esc(id)}"` : ""}${disabled ? " disabled" : ""}>${esc(label)}</button>`;
const heading = (title, description, actions = "") =>
  `<div class="page-head"><div><h1>${esc(title)}</h1>${description ? `<p>${esc(description)}</p>` : ""}</div><div class="actions">${actions}</div></div>`;
const section = (title, content, actions = "", desc = "") =>
  `<section class="panel"><div class="panel-header"><div><h2>${esc(title)}</h2>${desc ? `<p class="fine desc">${esc(desc)}</p>` : ""}</div><div class="actions">${actions}</div></div>${content}</section>`;
const tabs = (options, current, action, label) =>
  `<div class="tabs" role="tablist" aria-label="${esc(label)}">${options.map(([key, name]) =>
    `<button class="tab" role="tab" aria-selected="${key === current}" data-action="${action}" data-value="${esc(key)}">${esc(name)}</button>`).join("")}</div>`;
const select = (id, choices, value, label, classes = "") =>
  `<select id="${esc(id)}" aria-label="${esc(label)}" class="${classes}">${choices.map(([k, name]) => `<option value="${esc(k)}"${k === value ? " selected" : ""}>${esc(name)}</option>`).join("")}</select>`;
const field = (id, label, choices, value, classes = "") =>
  `<div class="field ${classes}"><label for="${esc(id)}">${esc(label)}</label>${select(id, choices, value, label)}</div>`;

function table(headers, rows, options = {}) {
  const {raw = [], numeric = [], css = ""} = options;
  return `<div class="table-wrap"><table class="${css}"><thead><tr>${headers.map((header, i) => `<th scope="col" class="${numeric.includes(i) ? "num" : ""}">${esc(header)}</th>`).join("")}</tr></thead><tbody>${rows.map(row =>
    `<tr>${row.map((cell, i) => `<td class="${numeric.includes(i) ? "num" : ""}">${raw.includes(i) ? cell : esc(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function remember() {
  try {
    localStorage.setItem(localKey, JSON.stringify({reports: state.reports, actions: state.actions,
      cases: state.cases, preflights: state.preflights, receipts: state.receipts}));
  } catch {
    announce("浏览器存储不可用，当前记录可通过导出保存。");
  }
}

let noticeTimer;
function announce(message) {
  clearTimeout(noticeTimer);
  const notice = el("notice");
  notice.textContent = message;
  notice.hidden = false;
  noticeTimer = setTimeout(() => { notice.hidden = true; }, 4300);
}

function showDialog(title, html) {
  el("dialog-inner").innerHTML = `<header class="dialog-header"><h2 id="dialog-title">${esc(title)}</h2><button class="icon-button" data-action="close-dialog" aria-label="关闭">×</button></header><div class="dialog-content">${html}</div>`;
  const dialog = el("detail-dialog");
  dialog.setAttribute("aria-labelledby", "dialog-title");
  if (!dialog.open) dialog.showModal();
}

function download(filename, value, type = "text/plain;charset=utf-8") {
  const url = URL.createObjectURL(new Blob([value], {type}));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 500);
}

function renderFrame() {
  el("navigation").innerHTML = `<div class="nav-label">经营复盘</div>${pages.map(([id, title, icon]) => `${id === "activity" ? '<div class="nav-label">活动验证</div>' : ""}<button class="nav-button" data-action="go" data-value="${id}" aria-current="${id === state.page ? "page" : "false"}"><span class="nav-icon" aria-hidden="true">${icon}</span>${title}</button>`).join("")}`;
  el("breadcrumbs").innerHTML = `CampaignLab <span aria-hidden="true">/</span> <strong>${pages.find(page => page[0] === state.page)[1]}</strong>`;
  el("top-actions").innerHTML = `${pill("合成数据", "blue")}${select("bank-picker", [...banks].map(([id, bank]) => [id, bank.name]), state.bankId, "选择模拟银行", "selector")}${button("导入数据", "import", {id: "import-button"})}`;
}

function renderFilters() {
  const bank = bankNow(), s = state.scope;
  const branches = Object.values(bank.branches);
  const groups = unique(branches.map(branch => branch.group));
  const months = unique([...bank.metadata.periods, s.period]).filter(Boolean).sort().reverse().map(month => [month, monthName(month)]);
  const cutoffs = unique(bank.records.filter(row => row.period === s.period).map(row => row.cutoff)).sort();
  const selector = (name, label, options, classes) => field("scope-" + name, label, options, s[name], classes);
  const sources = [[ALL, "全部策略"], ["hq", "总行下发"], ["branch", "分行自主"]];
  return `<div class="filter-card"><div class="filter-body">
    ${selector("branch", "分行", [[ALL, "全行"], ...branches.map(b => [b.id, b.name + "分行"])])}
    ${selector("period", "统计期", months)}
    ${selector("channel", "渠道", [[ALL, "全渠道"], ...Object.entries(bank.metadata.channels)])}
    ${selector("reference", "比较基准", [["previous","上月环比"],["yoy","去年同期"],["peer","同组均值"],["bank","全行均值"],["hq","总行下发"],["target","演示目标"],["custom","自选统计期"],...(s.compareBranch ? [["branch","指定分行"]] : [])])}
    ${s.reference === "custom" ? selector("basePeriod", "基准期", [["","请选择"],...months]) : ""}
    ${button("重置筛选", "reset-scope", {tone: "small"})}
  </div><details id="advanced-filters"${state.advanced ? " open" : ""}><summary>更多筛选</summary><div class="filter-body">
    ${selector("group", "分组", [[ALL,"全部分组"],...groups.map(g => [g,g])])}
    ${selector("subbranch", "支行", [[ALL,"全部支行"],...unique(bank.records.filter(r => s.branch === ALL || r.branch === s.branch).map(r => r.subbranch)).sort().map(name => [name,name])])}
    ${selector("origin", "策略来源", sources)}
    ${selector("strategy", "策略", [[ALL,"全部策略"],...Object.values(bank.strategies).map(item => [item.id,`${item.id} ${item.name}`])], "wide")}
    ${selector("segment", "客群", [[ALL,"全部客群"],...["大众","富裕","贵宾","私行","个贷"].map(name => [name,name])])}
    ${selector("segmentBasis", "客群口径", [["segment","部署客群"],["tag","月末标签"]])}
    ${selector("activity", "活动", [[ALL,"全部活动"],...bank.metadata.activities.map(item => [item.id,item.name + (item.strategies.length ? "" : "（待绑定）")])])}
    ${selector("cutoff", "数据截止日", [["","本期全部已导入快照"],...cutoffs.map(day => [day,day])])}
  </div></details></div>`;
}

function statusLine(result) {
  const evidence = evidenceIndex(bankNow(), result.rows);
  const tone = result.status === "full" ? "good" : "warn";
  const status = result.status === "full" ? "可比" : result.status === "partial" ? "部分可比" : "待补数据";
  let text = "";
  if (state.scope.activity !== ALL && !activityById(bankNow(), state.scope.activity)?.strategies.length) text = "活动与策略待绑定。先提供活动编号、策略版本及关联生效期。";
  else if (result.status === "partial") text = "两期覆盖或口径存在差异。比较只使用可比子集，分组构成与变化不能作为实验结果。";
  else if (result.status === "missing") text = "当前范围缺少本期或基准证据，可在报告页导出取数清单。";
  return `<div class="scope-strip">${pill(status, tone)}<span>${esc(scopeLabel(bankNow(), state.scope))}</span><span>·</span><span>基准 ${esc(result.spec.label)}</span><span>·</span><span>快照 ${esc(evidence.snapshot)}${evidence.cutoff ? " / 截止 " + esc(evidence.cutoff) : ""}</span></div>${text ? banner(text, "warn") : ""}`;
}

function metricCard(result, key) {
  const change = delta(result.comparableCurrent?.[key], result.base?.[key]);
  const relative = ratio(change, result.base?.[key]);
  return `<button class="metric" id="metric-${key}" data-action="metric" data-value="${key}">
    <span class="label">${METRICS[key].name}</span><div class="metric-number">${metricValue(key, result.current?.[key])}</div>
    <div class="fine ${change < 0 ? "fall" : change > 0 ? "rise" : ""}">${finite(change) ? `${deltaValue(key, change)}${finite(relative) ? " · " + pct(relative) : ""}` : "基准或分母待核"}</div>
  </button>`;
}

function funnel(result) {
  if (!result.current) return empty("当前范围没有可展示的五层人数。");
  const values = result.current;
  const low = FUNNEL_RATES.filter(key => finite(values[key])).sort((a,b) => values[a] - values[b])[0];
  return `<div class="funnel" id="funnel">${STAGES.map(([key, label], i) => {
    const rateKey = i ? FUNNEL_RATES[i - 1] : "";
    const width = clamp((ratio(values[key], values.sent) ?? 0) * 100, 0, 100);
    return `<button class="funnel-row" data-action="metric" data-value="${rateKey || key}" title="${i ? "查看相对上一层的计算口径" : "查看下发人数来源"}"><span>${label}</span><span class="bar-track"><span class="bar-fill ${rateKey && rateKey === low ? "critical" : i > 2 ? "end" : i > 1 ? "mid" : ""}" style="display:block;width:${width}%"></span></span><strong class="metric-number">${num(values[key])}</strong><span class="rate ${rateKey && rateKey === low ? "strong" : "fine"}">${i ? pct(values[rateKey]) : "—"}</span></button>`;
  }).join("")}</div><p class="fine desc">人数按客户集合去重。右侧为相对上一层的转化率。</p>`;
}

function participationTable() {
  const bank = bankNow(), scope = state.scope;
  const groups = unique(Object.values(bank.branches).map(b => b.group));
  const items = [["本次范围",scope],["全行",{...scope,branch:ALL,group:ALL,subbranch:ALL}],...groups.map(g => [g,{...scope,branch:ALL,group:g,subbranch:ALL}])];
  return table(["范围","已部署分行","下发策略","可经营客户","下发成功","覆盖率","有效触达率","部署分行月增／环比","策略月增／环比","覆盖率月增／环比"], items.map(([name, s]) => {
    const a = analyze(bank, {...s,reference:"previous"});
    const c = a.current;
    const value = key => delta(a.comparableCurrent?.[key], a.base?.[key]);
    const relative = key => pct(ratio(value(key),a.base?.[key]));
    return [name,num(c?.deployed),num(c?.strategies),num(c?.eligible),num(c?.success),pct(c?.cover),pct(c?.effectiveRate),
      deltaValue("deployed",value("deployed")) + " / " + relative("deployed"),
      deltaValue("strategies",value("strategies")) + " / " + relative("strategies"),
      deltaValue("cover",value("cover")) + " / " + relative("cover")];
  }), {numeric:[1,2,3,4,5,6,7,8,9]});
}

function performanceTable() {
  const bank = bankNow();
  const source = origin => analyze(bank,{...state.scope,origin,reference:"previous"});
  const [current, hq, branch] = [source(state.scope.origin),source("hq"),source("branch")];
  return table(["指标（元）","本期","上月可比值","月增","环比","总行下发","分行自主"],PRODUCTS.map(key => {
    const change = delta(current.comparableCurrent?.[key],current.base?.[key]);
    return [METRICS[key].name,money(current.current?.[key]),money(current.base?.[key]),deltaValue(key,change),
      pct(ratio(change,current.base?.[key])),money(hq.current?.[key]),money(branch.current?.[key])];
  }), {numeric:[1,2,3,4,5,6]});
}

function detailTable(result) {
  const bank = bankNow();
  const dimension = state.overviewDimension;
  const rows = [...byDimension(bank,result.rows,dimension,state.scope)].map(([key,items]) => {
    const item = aggregate(items);
    return [dimensionName(bank,dimension,key),num(item.strategies),num(item.sent),num(item.success),pct(item.successRate),num(item.executed),pct(item.execution),
      num(item.contacted),pct(item.reach),num(item.effective),pct(item.effectiveRate),money(item.aum),money(item.deposit),money(item.wealth),money(item.fund),money(item.loan)];
  });
  return tabs([["branch","分行"],["channel","渠道"],["subbranch","支行"]],dimension,"overview-dimension","明细视图") +
    (rows.length ? table([DIM_LABELS[dimension],"策略数","下发","下发成功","下发成功率","执行","名单执行率","接触","触达率","有效接触","有效触达率","AUM增量","存款增量","理财增量","基金增量","个贷增量"],rows,{numeric:Array.from({length:15},(_,i)=>i+1)}) : empty("当前筛选没有数据明细。"));
}

function segmentActivityStrip(result) {
  const s = state.scope, bank = bankNow(), items = [];
  if (s.segment !== ALL) {
    items.push(`<div class="issue"><div class="issue-title"><h3>${esc(s.segment)} · 客群特色</h3>${pill(s.segmentBasis === "tag" ? "月末标签" : "部署客群","blue")}</div><p>意向沟通 ${num(result.current?.intentCount)} 次 · 有效接触 ${num(result.current?.effective)} 人 · AUM余额增量 ${money(result.current?.aum)}</p></div>`);
  }
  if (s.activity !== ALL) {
    const activity = activityById(bank,s.activity);
    items.push(`<div class="issue"><div class="issue-title"><h3>${esc(activity.name)}</h3>${pill(activity.strategies.length ? "已绑定" : "待绑定",activity.strategies.length ? "good" : "warn")}</div><p>${activity.strategies.length ? esc(activity.metricLabel) + " " + num(result.current?.activityCount) + " · AUM余额增量 " + money(result.current?.aum) + " · " + esc(activity.evidence) : "需提供有效期内的活动与策略关联证据。"}</p></div>`);
  }
  return items.length ? section("专题视图",items.join("")) : "";
}

function reviewPage() {
  const bank = bankNow(), a = rowCurrent();
  const change = delta(a.comparableCurrent?.contactConv,a.base?.contactConv);
  const contributions = !a.spec.peers && !a.spec.target ? funnelDecomposition(a.comparableCurrent,a.base) : null;
  const dominant = contributions?.slice().sort((x,y)=>Math.abs(y.effect)-Math.abs(x.effect))[0];
  const alert = finite(change) ? `<div class="issue"><div class="issue-title"><h3>已执行 → 已接触</h3>${pill(change < 0 ? "接触损失" : "层间变化",change < 0 ? "warn" : "good")}</div><p class="strong">${pct(a.base.contactConv)} → ${pct(a.comparableCurrent.contactConv)} · ${deltaValue("contactConv",change)}</p><p class="fine">可比基准 ${esc(a.spec.label)}${dominant ? " · 最大统计变化 " + esc(dominant.name) + " " + signed(dominant.effect) + " 人" : ""}</p>${a.current.capacity > 0 && state.scope.channel !== ALL ? `<p class="fine">模拟渠道容量 ${num(a.current.capacity)} 席次，可作为排查线索。</p>` : ""}${button("打开异常诊断","diagnose-metric",{value:"effective",tone:"text small"})}</div>` : empty("当前范围缺少层间对比证据。");
  return heading("策略复盘", "核对部署覆盖、触达过程与执行效果", button("生成复盘报告","go",{value:"report",tone:"primary"}) + button("下载当前明细","export-detail"))
    + renderFilters() + tabs([[ALL,"分行整体"],["hq","总行下发"],["branch","分行自主"]],state.scope.origin,"origin-tab","策略来源")
    + statusLine(a)
    + `<div class="metrics">${["cover","execution","effective","effectiveRate"].map(key=>metricCard(a,key)).join("")}</div>
       <div class="split section">${section("五层策略执行漏斗",funnel(a),button("渠道口径","go",{value:"data",tone:"text small"}))}${section("优先核查",alert + (state.actions.some(item=>item.bankId===bank.id) ? `<p class="fine">${state.actions.filter(item=>item.bankId===bank.id).length} 条改进记录</p>${button("查看改进记录","go",{value:"report",tone:"text small"})}` : ""),button("查看全部","go",{value:"diagnose",tone:"text small"}))}</div>`
    + `<div class="section">${segmentActivityStrip(a)}${section("分行策略参与度",participationTable(),"","本次范围、全行及各分组的覆盖与月度变化")}${section("策略执行效果",performanceTable(),"","余额增量和产品销量各自按模拟归属口径展示")}${section("过程与产能明细",detailTable(a))}</div>`;
}

function metricDialog(key, result = rowCurrent()) {
  const bank = bankNow(), definition = METRICS[key], current = result.current;
  const fraction = definition.fraction;
  const evidence = evidenceIndex(bank,result.rows);
  const formula = fraction ? `${METRICS[fraction[0]].name} ÷ ${METRICS[fraction[1]].name}` : definition.unit === "元" ? "相同金额单位的已归属明细相加" : "按当前机构、渠道和期间聚合";
  const value = fraction ? `${num(current?.[fraction[0]])} ÷ ${num(current?.[fraction[1]])} = ${pct(current?.[key])}` : metricValue(key,current?.[key]);
  const rows = result.rows.slice(0,24).map(row=>[row.id,row.evidence,row.definition,fraction ? `${num(row[fraction[0]])} / ${num(row[fraction[1]])}` : num(row[key])]);
  showDialog(definition.name, banner(value + " · " + formula,fraction && !current?.[fraction[1]] ? "warn" : "")
    + table(["项目","内容"],[["范围",scopeLabel(bank,result.scope)],["当前期间",periodText(result.scope)],["比较基准",result.spec.label],["来源快照",evidence.snapshot + " / " + evidence.mapping],["数据截止",evidence.cutoff],["口径版本",evidence.definitions],["计数规则","同统计月、同客户集合按区间取并集；跨月为客户月次"]])
    + (fraction && !current?.[fraction[1]] ? banner("分母为零或缺失，结果显示为待计算。","warn") : "")
    + (rows.length ? table(["切片键","源表与行","口径","源值"],rows) + `<p class="fine">已显示 ${rows.length} / ${result.rows.length} 条。可在工作台下载当前全部明细。</p>` : empty("当前范围未导入源行。")));
}

function channelDefinitions(bank) {
  const standard = "策略覆盖命中且通过渠道初始筛选";
  const received = "渠道节点收到策略客户数据";
  return {
    sms:[standard,received,"短信推送尝试，含成功与失败","短链被点击","点击后进入详情"],
    push:[standard,received,"客户收到推送","短链被点击",bank.metadata.pushDetailSeconds ? `进入详情且停留至少 ${bank.metadata.pushDetailSeconds} 秒` : "点击后进入详情"],
    wechat:[standard,received,"对话发送或有通话记录","消息送达或有通话时长","交互至少 1 轮，或通话至少 60 秒，或点击消息短链"],
    ai:[received,"外呼平台实际收到，扣除频控名单","已拨打，含接通与未接通","拨打且接通","交互至少 1 轮"],
    remote:[standard,received,"在名单下发至截止日之间拨打","拨打且接通","财私至少 60 秒；个贷至少 10 秒"],
    manager:[standard,received,"在统计起始至截止日通过 5+1 渠道联系过","通过 5+1 渠道联系成功","联系成功且对应渠道有效接触条件成立"],
  };
}

function rulesTable(bank) {
  const keys = ["sms","push","wechat","ai","remote","manager"];
  const defs = channelDefinitions(bank);
  return table(["漏斗层级",...keys.map(key=>bank.metadata.channels[key] || key)],
    STAGES.map(([,label],i)=>[label,...keys.map(key=>defs[key][i])]),{css:"rules-grid"});
}

function linkPanel(bank) {
  const links = matchOutcomes(bank,state.linkResolution);
  const count = status => links.filter(item=>item.status===status).length;
  const rules = bank.metadata.linkPolicy;
  const mapping = rules ? Object.entries(rules.routeWindows).map(([key,range])=>[bank.metadata.channels[key],rules.dispatchDays[key].join(" 或 ")+" 天",range.join(" 至 ")+" 天（含端点）"]) : [];
  return section("下发、触达与产能关联核验",
    `<p class="fine">关联合成客户键和业务日期条件。当前规则 ${esc(rules?.version || "待补")}${state.linkResolution === "nearest" ? " / 最近触达优先（已选择）" : ""}。</p>`
    + (mapping.length ? table(["渠道","下发日减触达日","产能日减触达日"],mapping) : empty("关联规则待补。"))
    + `<p class="desc">唯一匹配 ${count("唯一匹配")} · 多候选待核 ${count("多候选待核")} · 已确认归属 ${count("已按规则归属")} · 未匹配 ${count("未匹配")}</p>`
    + (links.length ? table(["产能样本","金额","候选触达（窗口天数）","状态","采用"],links.map(item=>[item.id,money(item.amount),
      item.candidates.map(t=>`${t.id} / ${t.strategy}（产能 ${t.age} 天，下发 ${t.dispatch} 天，${t.matched ? "命中" : "排除"}）`).join("；") || "—",item.status,item.chosen?.strategy || "待补"])) : empty("未提供关联明细。")),
    button("采用最近触达","resolve-link",{value:"nearest",tone:"small",disabled:!links.length||state.linkResolution==="nearest"})+button("恢复待核","resolve-link",{value:"pending",tone:"small",disabled:state.linkResolution==="pending"}));
}

function classifyPanel(bank) {
  const options = [["received","节点已接收",true],["attempted","已拨打或推送",true],["answered","已接通或联系成功",true],["delivered","消息已送达",true],["message","有会话记录",true],["clicked","已点击短链",false],["detail","已进入详情",false],["freqBlocked","频控拦截",false],["daysInRange","在有效时段内",true],["downstream","下游口径为有效",true]];
  const defaults = state.classInput || {};
  const input = (id,label,value) => `<div class="field"><label for="${id}">${label}</label><input id="${id}" name="${id}" type="number" min="0" max="10000" step="1" value="${value}"></div>`;
  return section("历史事件口径重算",
    `<form id="class-form"><div class="filter-body">
       ${field("class-channel","渠道",Object.entries(bank.metadata.channels),defaults.channel || "remote")}
       ${field("class-line","条线",[["wealth","财私"],["loan","个贷"]],defaults.line || "wealth")}
       ${input("class-seconds","时长（秒）",defaults.seconds ?? 59)}${input("class-rounds","交互轮次",defaults.rounds ?? 0)}
    </div><div class="toggle-set">${options.map(([key,label,on])=>`<label><input name="${key}" type="checkbox"${(defaults[key]??on) ? " checked" : ""}>${label}</label>`).join("")}</div>
    <button class="button primary" type="submit">按口径重算</button></form>`
    + (state.classResult ? `<div class="answer" id="class-result">${table(["下发","下发成功","执行","接触","有效接触"],[[...STAGES.map(([key])=>state.classResult[key] ? "命中" : "未命中")]])}<p class="fine">银行配置 ${esc(bank.mapping.version)} · ${esc(bank.metadata.channels[state.classInput.channel])} · ${state.classInput.seconds} 秒</p></div>` : ""));
}

function bankComparison() {
  const [a,b] = ["A","B"].map(id=>banks.get(id));
  if (!a || !b) return null;
  const scope = state.scope;
  const ar = scopeRows(a,scope), br = scopeRows(b,scope);
  const defs = rows=>unique(rows.map(r=>r.channel + ":" + r.definition)).sort().join(" | ");
  const sameDefinition = ar.length && br.length && defs(ar)===defs(br);
  const av = aggregate(ar), bv = aggregate(br);
  const keys = ["sent","success","executed","contacted","effective","effectiveRate","aum"];
  const equal = Boolean(sameDefinition && keys.every(key=>av[key]===bv[key]));
  return {keys,av,bv,sameDefinition,equal,a,b};
}

function dataPage() {
  const bank = bankNow(), a = rowCurrent(), m = bank.mapping;
  const check = state.bankCheck;
  const mappings = [["机构",m.dimensions.branch,"分行标识"],["月份",m.dimensions.period,"统计月"],["渠道",m.dimensions.channel,"按代码字典映射"],["策略来源",m.dimensions.origin,"分行自主／总行下发"],
    ...STAGES.map(([key,label])=>[label,m.countFields[key],m.layout==="long" ? "按切片键及指标码取人数" : "按宽表列取人数"]),["AUM余额增量",m.moneyFields.aum,`除以 ${m.moneyDivisor}，展示为元`]];
  return heading("数据与口径","核对快照、字段映射、渠道定义和关联条件",button("导入数据文件","import",{tone:"primary"})+button("对比甲乙行","compare-banks"))
    + renderFilters() + statusLine(a)
    + (state.importError ? banner(state.importError,"bad") : "")
    + `<div class="split equal">${section("数据快照",table(["项目","当前值"],[["银行",bank.name],["快照版本",bank.snapshot],["接入配置",m.version],["源表",Object.keys(bank.raw.tables).join("、")],["源切片",String(bank.records.length)],["数据来源",bank.metadata.sources.join("、")],["导入记录",state.intakeLog.at(-1)||"已加载内置样本"]])
        + `<div class="actions section">${button("下载甲行样本","download-bank",{value:"A",tone:"small"})}${button("下载乙行样本","download-bank",{value:"B",tone:"small"})}</div>`)
      }${section("来源字段映射",table(["业务对象","原字段／指标码","转换"],mappings),"",m.layout==="wide" ? "月度宽表 · 元" : "阶段人数长表 · 渠道编码 · 分")}</div>`
    + (check ? `<div class="section">${section("甲乙行同语义核对",banner(check.equal ? "已对齐。相同口径的五层人数、有效触达率和 AUM 结果相等。" : check.sameDefinition ? "同口径数值存在差异，逐项查看下表。" : "两边定义或数据范围不同，当前比较待核。",check.equal?"good":"warn") + table(["指标",check.a.name,check.b.name],check.keys.map(key=>[METRICS[key].name,metricValue(key,check.av?.[key]),metricValue(key,check.bv?.[key])]),{numeric:[1,2]}))}</div>` : "")
    + `<div class="section">${section("口径和覆盖",table(["项目","当前范围"],[
      ["有效触达率","有效触达客户数 ÷ 下发成功客户数"],
      ["有效接触层间转化率","有效接触客户数 ÷ 已接触客户数"],
      ["客户去重","按月与客户集合取并集。各渠道的客户数可能重复"],
      ["客群范围",state.scope.segmentBasis==="tag" ? "按月末标签" : "按策略部署时的客群"],
      ["比较差异",a.notes.join("、") || "当前两期可比"],
      ["采集记录",(bank.metadata.coverageEvents||[]).map(item=>`${item.period} ${bank.metadata.channels[item.channel]} ${item.status}`).join("、")],
    ]),button("查看分母与原行","metric",{value:"effectiveRate",tone:"small"}))}${section("各渠道漏斗口径",rulesTable(bank),"","5+1 渠道的具体组成由银行确认，演示通过已知的下游判定结果核对。")}${classifyPanel(bank)}${linkPanel(bank)}</div>`;
}

function anomalyTable(alerts, withScope = false) {
  if (!alerts.length) return empty("已计算当前规则。没有命中，或基准／分母待补，详见数据与口径。");
  return table([...(withScope ? ["对象"] : []),"指标与判定","本期","参照值","变化","阈值与基准","影响"],alerts.map(alert=>[
    ...(withScope ? [alert.scopeName] : []),
    (alert.kind==="mix" ? "" : METRICS[alert.key].name+" · ")+alert.label,
    metricValue(alert.key,alert.cur),metricValue(alert.key,alert.base),
    deltaValue(alert.key,alert.change)+(finite(alert.relative) ? " / "+pct(alert.relative) : ""),
    alert.threshold+" · "+alert.baseline,alert.impact,
  ]),{numeric:withScope?[2,3,4]:[1,2,3]});
}

function thresholdPanel() {
  const fields = [["mom","期间相对变化（%）",0.1,1000],["peer","同组下偏（%）",0.1,1000],["own","自身近 6 月（σ）",0.1,10],
    ["layer","层间同组下偏（%）",0.1,1000],["mix","结构占比变化（百分点）",0.1,100]];
  return `<details id="threshold-details"${state.thresholdOpen ? " open" : ""}><summary>异常判定阈值</summary>
  <form id="threshold-form"><div class="controls-grid">${fields.map(([id,label,step,max])=>`<label for="threshold-${id}">${label}<input id="threshold-${id}" name="${id}" type="number" min="0.1" max="${max}" step="${step}" required value="${state.thresholds[id]}"></label>`).join("")}</div>
  <div class="actions section"><button class="button primary small" type="submit">应用本轮阈值</button>${button("恢复默认","reset-thresholds",{tone:"small"})}</div></form>
  <p class="fine desc">当前阈值版本 T-${state.thresholdVersion || 1} · 阈值含边界。相对比较需要正基数，自身比较需要六个可比月。</p>
  ${state.thresholdHistory?.length ? table(["版本","期间","同组","自身","层间","结构"],state.thresholdHistory.map(item=>[item.version,item.rules.mom+"%",item.rules.peer+"%",item.rules.own+"σ",item.rules.layer+"%",item.rules.mix+" 个百分点"])) : ""}</details>`;
}

function diagnosisContent(diagnosis, result) {
  const {metric,dim,funnel: breakdown,rows,residual,reason}=diagnosis;
  let parts="";
  if (breakdown) {
    const total=breakdown.reduce((sum,item)=>sum+item.effect,0);
    parts+=`<div class="banner" id="breakdown-net">有效触达客户数净变化 <strong>${signed(round(total))} 人</strong> · 固定漏斗顺序的量率拆解</div>`
      +table(["影响因素","基准","本期","对有效触达人数影响"],breakdown.map(item=>[item.name,metricValue(item.key,item.before),metricValue(item.key,item.after),signed(item.effect)+" 人"]),{numeric:[1,2,3]});
  }
  if (rows.length) {
    parts+=`<p class="fine desc">${esc(DIM_LABELS[dim])}拆解 · ${esc(reason)}</p>`+table([DIM_LABELS[dim],"基准","本期","变化贡献"],[
      ...rows.map(item=>[item.name,metricValue(metric,item.base),metricValue(metric,item.current),deltaValue(metric,item.effect)]),
      ["去重调整／未分配余量","—","—",deltaValue(metric,residual)],
    ],{numeric:[1,2,3]});
  }
  if (!parts) parts=empty(reason||"缺少可比范围或所需明细。");
  const latest = delta(result.comparableCurrent?.[metric],result.base?.[metric]);
  return `<div class="row-inline"><strong>${esc(METRICS[metric].name)}</strong>${pill("统计拆解","blue")}<span class="fine">${esc(scopeLabel(bankNow(),result.scope))} · ${esc(result.spec.label)} · ${deltaValue(metric,latest)}</span></div>`+parts;
}

function trendChart(bank, scope, metric) {
  const points=Array.from({length:6},(_,i)=>shiftMonth(scope.period,i-5)).map(period=>[period,aggregate(scopeRows(bank,{...scope,period,periods:null,cutoff:""}))?.[metric]]);
  const max=Math.max(1e-8,...points.map(([,value])=>Math.abs(value??0)));
  return `<div class="mini-chart" role="img" aria-label="${esc(METRICS[metric].name)}近六个月趋势">${points.map(([month,value])=>
    `<div class="mini-col"><div class="fine metric-number">${metricValue(metric,value)}</div><div class="track"><i style="height:${finite(value) ? Math.max(3,Math.abs(value)/max*60) : 0}px${value<0 ? ";background:#a95850" : ""}"></i></div><div class="fine">${Number(month.slice(-2))}月</div></div>`).join("")}</div>`;
}

function questionRows(q) {
  const rows = q.ranking.flatMap(row => q.keys.map(key => {
    const a=row.analysis;
    return [row.label,METRICS[key].name,metricValue(key,a.current?.[key]),metricValue(key,a.base?.[key]),
      deltaValue(key,delta(a.comparableCurrent?.[key],a.base?.[key])),
      a.status === "full" ? a.spec.label : a.status === "partial" ? "仅可比子集 · "+a.spec.label : "待补基准 · "+a.spec.label];
  }));
  if (!rows.length) return empty(q.condition ? "当前数据没有满足条件的记录。" : "没有可展示的范围。");
  return table(["范围","指标","本期","基准值","可比变化","基准"],rows,{numeric:[2,3,4]});
}

function questionAnswer(q) {
  if (!q) return "";
  if (q.intent==="澄清") return `<div class="answer" id="question-answer">${pill("待澄清","warn")}${banner(q.message,"warn")}</div>`;
  const bank=bankNow(), focus=q.focus?.analysis || analyze(bank,q.scope);
  let body=`<div class="row-inline">${pill(q.intent,"blue")}<strong>${esc(scopeLabel(bank,q.scope))}</strong><span class="fine">${esc(periodText(q.scope))} · ${esc(focus.spec.label)} · ${esc(bank.snapshot)}</span></div>`;
  if (q.claims.length) body+=banner("题述数字 "+q.claims.join("、")+" 供核对。下方用当前导入数据重新计算。","warn");
  if (q.condition) body+=`<p class="fine">筛选条件 ${esc(q.condition.text)} · 命中 ${q.ranking.length} 个范围</p>`;
  if (q.intent==="口径") {
    body+=table(["指标","计算规则","当前数值","查看证据"],q.keys.map(key=>{
      const fraction=METRICS[key].fraction;
      return [METRICS[key].name,fraction ? fraction.map(item=>METRICS[item].name).join(" ÷ ") : key==="effective" ? "按渠道有效接触定义计数，再按客户集合去重" : "按当前范围与指标字典聚合",metricValue(key,focus.current?.[key]),button("来源","query-metric",{value:key,tone:"text small"})];
    }),{raw:[3]});
    if (/渠道/.test(q.question)) body+=rulesTable(bank);
  } else {
    body+=questionRows(q);
    if (q.intent==="异常"||q.intent==="组合") body+=anomalyTable(q.compareRows,true);
    if (q.cause) body+=diagnosisContent(q.cause,focus);
    if (q.intent==="组合" && q.conditionalCause && !q.cause) body+=empty("当前可比结果未触发异常，本次保留查询和判定记录。");
    if (q.intent==="报告") body+=button("按该范围生成报告","question-report",{tone:"primary",id:"question-report"});
    if (q.groupBy==="branch" && q.intent==="组合" && /贡献度偏低/.test(q.question)) {
      const all=analyze(bank,q.scope).current?.[q.keys[0]];
      const share=ratio(q.focus?.analysis.current?.[q.keys[0]],all);
      body+=`<p class="fine">渠道汇总 ${metricValue(q.keys[0],all)} · 目标分行占比 ${pct(share)}。</p>`;
    }
  }
  if (!focus.current) body+=banner("此范围的源数据待补，可生成取数清单。","warn");
  else body+=`<p class="fine">来源 ${esc(bank.metadata.sources.join("、"))} · ${num(focus.rows.length)} 条切片。${button("核对首项来源","query-metric",{value:q.keys[0],tone:"text small"})}</p>`;
  return `<div class="answer" id="question-answer" data-intent="${esc(q.intent)}">${body}</div>`;
}

function questionPanel() {
  const types=unique(embedded.questions.map(([,intent])=>intent));
  const examples=embedded.questions.filter(([,intent])=>!state.questionType||state.questionType===intent);
  return section("用业务语言查询",
    `<div class="question-controls">${select("question-type",[["","全部问法"],...types.map(type=>[type,"问"+type])],state.questionType||"","问法类别")}
      ${select("question-sample",[["","选择一个验收问法"],...examples.map(([id,,question])=>[id,`${id} · ${question}`])],state.questionExample||"","验收问法")}</div>
      <form class="question-form" id="question-form"><input id="question-input" aria-label="业务问题" placeholder="例如：解释10月东岚远程渠道有效触达客户数下降的原因" value="${esc(state.question)}"><button class="button primary" type="submit">查询</button></form>
      <p class="fine desc">按已登记的指标、机构与范围解释问题。日期或指标缺失时，可使用当前筛选或补充说明。</p>${questionAnswer(state.questionResult)}`);
}

function diagnosePage() {
  const bank=bankNow(), result=rowCurrent();
  const metricOptions=Object.entries(METRICS).map(([key,value])=>[key,value.name]);
  const diagnosis=diagnose(bank,result,state.metric,state.dimension==="funnel" ? "" : state.dimension);
  const alerts=scanAnomalies(bank,state.scope,state.thresholds,MAIN_METRICS,state.anomalyRule);
  const metricsControl=select("diagnostic-metric",metricOptions,state.metric,"下钻指标");
  const dims=[["funnel","漏斗量率或默认维度"],...["channel","segment","subbranch","origin","branch","depositType"].filter(key=>key!=="depositType"||state.metric==="deposit").map(key=>[key,DIM_LABELS[key]])];
  const alertOptions=[["all","全部规则"],["mom","期间／参照偏离"],["peer","同组下偏"],["own","自身历史"],["layer","层间低于同组"],["mix","结构占比"]];
  return heading("异常诊断","看清偏差出现的位置、影响量和证据",button("生成改进项","new-action",{tone:"primary"}))
    +renderFilters()+statusLine(result)
    +questionPanel()
    +`<div class="section">${section("异常清单",thresholdPanel()+`<div class="section">${anomalyTable(alerts)}</div>`,select("anomaly-rule",alertOptions,state.anomalyRule,"异常规则类型"))}
       ${section("下钻与贡献拆解",diagnosisContent(diagnosis,result),metricsControl+select("diagnostic-dimension",dims,state.dimension,"下钻维度"))}
       ${section("自身趋势",trendChart(bank,state.scope,state.metric),"","按当前范围取最近六个月。负值以红色表示，明细可回查来源。")}
       ${section("待验证的业务假设",table(["假设","下一步验证","责任方"],Object.values(PLAYBOOK).map(item=>[item.name,item.action,item.owner])),
         button("进入试算","go",{value:"simulate",tone:"primary small"}))}</div>`;
}

function relevantReplay(bank) {
  const s=state.scope;
  if (state.aggregateOnly) return [];
  return (bank.metadata.replayCases||[]).filter(item=>
    (s.branch===ALL||s.branch===item.branch) && (s.channel===ALL||s.channel===item.channel) &&
    (s.activity===ALL||s.activity===item.activity) && item.period===s.period);
}

function sampleNow() {
  const cases=relevantReplay(bankNow());
  return cases.find(item=>item.id===state.caseId)||cases[0];
}

function appointmentPanel() {
  const bank=bankNow(), samples=relevantReplay(bank), sample=sampleNow();
  const title="原规则回放与改案验证";
  const extra=button(state.aggregateOnly ? "恢复演示明细" : "模拟仅有汇总","toggle-detail",{tone:"small"});
  if (!sample) return section(title,empty("当前范围缺少可回放的事件、原规则版本、初始状态或实际记录。可在上方对汇总数据做条件式试算。"),extra);
  const actual=sample.observedWinner, original=replayCase(sample,"arrival"), changed=replayCase(sample,"appointment");
  if (!original||!changed||!has(sample,"observedWinner")) return section(title,empty("历史输入或实际结果待补。"),extra);
  const evidence=`<p class="fine">样本 ${esc(sample.id)} · ${esc(sample.day)} · ${esc(sample.customer)} · ${esc(sample.version)} · ${esc(sample.source)} · 已用 ${sample.used} / 上限 ${sample.cap} 次</p>`;
  const show=key=>bank.strategies[key]?.name || key || "无分配";
  const lines=trace=>trace.map(item=>`<li>${esc(item.time)} · ${esc(show(item.strategy))}${item.appointment ? "（已预约）" : ""} · ${esc(item.reason)}</li>`).join("");
  const pass=original.winner===actual;
  return section(title,`${evidence}${banner("实际分配 "+show(actual)+" · 原规则复算 "+show(original.winner)+" · "+(pass?"结果一致":"结果有差异，待核规则版本或历史输入"),pass?"good":"warn")}
    <div class="split equal">
      ${section("V1 · 按到达时间",`<p>分配给 <strong>${esc(show(original.winner))}</strong></p><ol class="trace-list">${lines(original.trace)}</ol>`)}
      ${section("候选 V2 · 已预约优先",`<p>分配给 <strong>${esc(show(changed.winner))}</strong></p><ol class="trace-list">${lines(changed.trace)}</ol>`)}
    </div><p class="fine desc">两套规则共用同日、同客户、同渠道的输入与频次约束。预演结果可作为下次发布前的验收期望。</p>
    <div class="actions section">${button("保存为验收案例","save-case",{tone:"primary",id:"save-case",disabled:!pass})}${button("打开活动工作台","go",{value:"activity",tone:"small"})}</div>`,
    select("replay-case",samples.map(item=>[item.id,item.id]),sample.id,"历史案例")+extra);
}

function simulatePage() {
  const result=rowCurrent(), a=result.current;
  const estimate=a && finite(a.validConv) && finite(a.executed) ? a.executed*state.scenario/100*a.validConv : null;
  const scenario = a ? `<form class="row-inline" id="scenario-form"><label for="scenario-rate">假设接触层间转化率（%）</label>
    <input id="scenario-rate" type="number" min="0" max="100" step="0.1" required value="${state.scenario}"><button type="submit" class="button primary">重新试算</button></form>
    <div class="section" id="scenario-result">${table(["已执行（固定）","有效接触层间转化率（固定）","当前有效接触","试算有效接触","差值"],[[num(a.executed),pct(a.validConv),num(a.effective),num(estimate),deltaValue("effective",delta(estimate,a.effective))]],{numeric:[0,1,2,3,4]})}</div>
    <p class="fine desc">条件式估算使用本期已导入范围。若要估计策略带来的净增量，需要实验分组、观察期与结果证据。</p>` : empty("当前范围缺少可计算的汇总。");
  const bank=bankNow();
  const cases=state.cases.filter(item=>item.bankId===bank.id);
  return heading("试算与回放","同一份输入，核对原结果与改案差异",button("查看活动工作台","go",{value:"activity"}))
    +renderFilters()+statusLine(result)+section("漏斗情景估算",scenario)+appointmentPanel()
    +section("验证记录",cases.length ? table(["案例","来源快照","目标活动","改案期望"],cases.map(item=>[item.id,item.snapshot,item.activity,bank.strategies[item.expected]?.name||"无分配"]))
      : empty("保存一条通过原规则对照的样本，即可在活动工作台复跑。"),button("历史口径重算","go",{value:"data",tone:"small"}));
}

function markdownView(text) {
  const lines=text.split("\n"), parts=[];
  for (let i=0;i<lines.length;i++) {
    const line=lines[i];
    if (!line) continue;
    if (line.startsWith("|") && /^\|[-:| ]+$/.test(lines[i+1]||"")) {
      const split=value=>value.slice(1,-1).split("|").map(s=>s.trim());
      const headers=split(line), rows=[];
      i+=2;
      while (i<lines.length && lines[i].startsWith("|")) {rows.push(split(lines[i]));i++;}
      i--;
      parts.push(table(headers,rows));
    } else if (line.startsWith("### ")) parts.push(`<h3>${esc(line.slice(4))}</h3>`);
    else if (line.startsWith("## ")) parts.push(`<h2>${esc(line.slice(3))}</h2>`);
    else if (line.startsWith("# ")) parts.push(`<h2>${esc(line.slice(2))}</h2>`);
    else if (line.startsWith("- ")) parts.push(`<p>• ${esc(line.slice(2))}</p>`);
    else parts.push(`<p>${esc(line)}</p>`);
  }
  return `<article class="doc">${parts.join("")}</article>`;
}

const bankActions = () => state.actions.filter(item=>item.bankId===state.bankId);
const relatedActions = () => bankActions().filter(item=>item.period===state.scope.period &&
  (state.scope.branch===ALL || item.branch===state.scope.branch) &&
  (state.scope.channel===ALL || item.channel===state.scope.channel));
const buildCurrentReport = () => reportModel(bankNow(),state.scope,state.thresholds,relatedActions(),state.reportType,state.reportRequest);

function improvementsTable() {
  const bank=bankNow(), actions=bankActions();
  if (!actions.length) return empty("从异常诊断保存改进项，记录负责人、时点、验证证据及下次检查条件。");
  return table(["改进项","业务假设与动作","责任方／时点","依据","状态","操作"],actions.map(item=>[
    item.id,item.name+" · "+item.action,item.owner+" · "+item.when+(item.due ? " / "+item.due : ""),
    item.source+" · "+item.evidence,item.status,
    button("查看与分派","edit-action",{value:item.id,tone:"text small"})+
    (["已分派","待复核","待验证"].includes(item.status) ? button("下期复核","follow-up",{value:item.id,tone:"text small"}) : ""),
  ]),{raw:[5]}) + (bank.snapshot.endsWith("-R1") ? `<p class="fine desc">当前快照 ${esc(bank.snapshot)}，受补数影响的改进项保留原依据并标为待复核。</p>` : "");
}

function reportPage() {
  const bank=bankNow(), report=buildCurrentReport(), history=state.reports.filter(item=>item.bankId===bank.id);
  const signedReport=history.find(item=>item.snapshot===bank.snapshot && item.scopeLabel===scopeLabel(bank,state.scope) &&
    item.period===periodText(state.scope) && item.text===report.text);
  const reportBody=`<div class="scope-strip">${pill(signedReport ? "已签认" : report.status,signedReport?"good":report.canSign?"blue":"warn")}
    <span>${esc(report.title)} · ${esc(periodText(state.scope))} · ${esc(bank.snapshot)}</span></div>${markdownView(report.text)}`;
  return heading("报告与改进","审阅复盘结论、移交验证动作并跟踪下期",button("导出 Markdown","export-report",{tone:"primary",disabled:report.status==="待补数据"})+button("导出取数清单","export-request"))
    +renderFilters()+statusLine(report.analysis)
    +section("复盘报告",reportBody,button("核对指标来源","metric",{value:"effectiveRate",tone:"small",disabled:!report.analysis.current})+
      button("提交签认","sign-report",{tone:"small",disabled:!report.canSign||Boolean(signedReport)}))
    +section("改进记录",improvementsTable(),button("新建改进项","new-action",{tone:"small"}))
    +section("签认历史与更正",history.length ? table(["报告","期间","快照","签认人","操作"],history.map(item=>[item.id,item.period,item.snapshot,item.reviewer,button("查看原报告","view-report",{value:item.id,tone:"text small"})]),{raw:[4]})
      : empty("已签认的报告会保存其原始计算结果与来源。"),
      button("模拟迟到数据","revise",{tone:"small",disabled:bank.snapshot.endsWith("-R1")}));
}

function activityPage() {
  const bank=bankNow();
  const id=state.activityId || (state.scope.activity!==ALL ? state.scope.activity : "AC-101");
  const item=activityById(bank,id)||bank.metadata.activities[0];
  if (!item) return heading("活动工作台","")+empty("当前数据未提供活动配置。");
  const savedCases=state.cases.filter(row=>row.bankId===bank.id&&row.activity===item.id);
  const linked=item.strategies.length>0;
  const evidence=state.preflights[bank.id]?.activity===item.id ? state.preflights[bank.id] : null;
  const receipt=state.receipts[bank.id]?.activity===item.id ? state.receipts[bank.id] : null;
  const preflight=bank.metadata.preflight;
  const rows=savedCases.map(row=>{
    const observed=evidence && has(evidence.winners,row.id)?evidence.winners[row.id]:undefined;
    const fmt=key=>bank.strategies[key]?.name || key || "无分配";
    return [row.id,fmt(row.original),"已预约优先 · V2",fmt(row.expected),observed===undefined?"待导入":fmt(observed),observed===undefined?"待验证":observed===row.expected?"通过":"待核差异"];
  });
  return heading("活动工作台","接收策略复盘产生的验收案例，核对正式改案前的预发结果",select("activity-select",bank.metadata.activities.map(a=>[a.id,a.name]),item.id,"活动工作台活动"))
    +section("活动与策略版本",table(["项目","当前状态"],[["活动",item.id+" · "+item.name],["策略",item.strategies.map(key=>key+" "+bank.strategies[key]?.name+" "+bank.strategies[key]?.version).join("、")||"待绑定"],
      ["关联有效期",linked?item.from+" 至 "+item.to:"待补"],["关联证据",item.evidence||"待银行提供"],["行内版本回执",receipt?receipt.version+" · "+receipt.source:"待登记"]]),
      button("查看关联复盘","review-activity",{value:item.id,tone:"small",disabled:!linked}))
    +section("复盘移交的验收案例",rows.length ? table(["案例","原结果","候选规则","验收期望","预发观察","对照结论"],rows) : empty(linked ? "回放页保存的案例会出现在这里。" : "先补充活动与策略的关联证据。"),
      button("导入模拟预发结果","preflight",{value:item.id,tone:"primary small",disabled:!savedCases.length||preflight?.activity!==item.id})
      +button("登记模拟发布回执","receipt",{value:item.id,tone:"small",disabled:!evidence||!savedCases.length||!savedCases.every(row=>has(evidence.winners,row.id)&&evidence.winners[row.id]===row.expected)}))
    +section("下期观察",receipt ? `<p>已登记 ${esc(receipt.version)} · ${esc(receipt.source)}。可切换到下期复盘，按相同范围复核变化。</p>`
      +button("查看下期复盘","next-review",{value:item.id,tone:"primary small"}) : empty("预发结果核对完成后，可登记行内发布回执。正式规则调整、审批和发布由行内平台负责。"));
}

function render() {
  renderFrame();
  const view={review:reviewPage,data:dataPage,diagnose:diagnosePage,simulate:simulatePage,report:reportPage,activity:activityPage}[state.page];
  el("workspace").innerHTML=view();
}

function go(page) {
  if (!pages.some(item=>item[0]===page)) return;
  state.page=page;
  render();
  window.scrollTo(0,0);
  el("workspace").focus({preventScroll:true});
}

function resetScope() {
  state.scope=scopeFor(bankNow());
  state.reportRequest=null;
  state.reportType="策略复盘报告";
  state.questionResult=null;
  state.bankCheck=null;
}

function changeScope(key,value) {
  state.scope[key]=value;
  state.scope.periods=null;
  state.scope.channels=null;
  if (key==="group") {
    state.scope.branch=ALL;
    state.scope.subbranch=ALL;
  }
  if (key==="branch") {
    state.scope.group=ALL;
    state.scope.subbranch=ALL;
  }
  if (key==="period") state.scope.cutoff="";
  if (key==="reference" && value==="custom" && !state.scope.basePeriod) state.scope.basePeriod=shiftMonth(state.scope.period,-1);
  state.reportRequest=null;
  state.questionResult=null;
  state.bankCheck=null;
  render();
}

function csvCell(value) {
  const text=String(value??"");
  const safe=typeof value==="string"&&/^[=+@-]/.test(text) ? "'"+text : text;
  return '"'+safe.replaceAll('"','""')+'"';
}

function exportDetail() {
  const result=rowCurrent(), keys=["period","cutoff","branch","subbranch","channel","strategy","origin","segment","tag","definition","batch",
    ...COUNTS,...MONEY,"evidence"];
  const header=keys.map(key=>METRICS[key]?.name || key);
  const rows=[header,...result.rows.map(row=>keys.map(key=>row[key]))];
  download("CampaignLab-复盘明细-"+state.scope.period+".csv","\uFEFF"+rows.map(row=>row.map(csvCell).join(",")).join("\r\n"),"text/csv;charset=utf-8");
}

function actionScope() {
  const a=rowCurrent(), bank=bankNow();
  const key=state.metric;
  const impact=deltaValue(key,delta(a.comparableCurrent?.[key],a.base?.[key]));
  return {bankId:bank.id,source:bank.snapshot+" / "+bank.mapping.version,period:state.scope.period,branch:state.scope.branch,channel:state.scope.channel,
    scope:{...state.scope,periods:null},metric:key,impact,baseline:a.spec.label,status:"待确认"};
}

function actionDialog(existing) {
  const selected=existing?.kind||state.actionKind||actionFor(state.metric);
  const choice=PLAYBOOK[selected];
  const draft=existing||{kind:selected,...choice,when:"30 天",due:"",evidence:"下期按同口径核对触达与预演证据",...actionScope()};
  showDialog(existing ? "改进项 "+existing.id : "新建改进项",
    `<p class="fine">来源 ${esc(draft.source)} · ${esc(METRICS[draft.metric].name)} ${esc(draft.impact)} · ${esc(draft.baseline)}</p>
    <form id="action-form" data-existing="${esc(existing?.id||"")}">
      <div class="filter-body">${field("action-kind","对应假设",Object.entries(PLAYBOOK).map(([key,item])=>[key,item.name]),selected)}
      ${field("action-when","复核窗口",[["30 天","30 天"],["90 天","90 天"]],draft.when)}
      <div class="field"><label for="action-owner">责任人或岗位</label><input id="action-owner" required maxlength="50" value="${esc(draft.owner)}"></div>
      <div class="field"><label for="action-due">计划日期</label><input id="action-due" type="date" value="${esc(draft.due)}"></div></div>
      <label for="action-text" class="label">动作</label><textarea id="action-text" required maxlength="400">${esc(draft.action)}</textarea>
      <label for="action-evidence" class="label">预期或验证证据</label><textarea id="action-evidence" required maxlength="400">${esc(draft.evidence)}</textarea>
      <div class="actions"><button class="button primary" type="submit" value="已分派">保存并分派</button><button class="button" type="submit" value="待验证">保存为待验证</button></div>
    </form>`);
}

function signDialog() {
  const report=buildCurrentReport();
  if (!report.canSign) return announce("补齐数据或选择可比范围后可签认。");
  showDialog("签认本次复盘",
    `<p>${esc(report.title)} · ${esc(report.evidence.snapshot)} · ${esc(report.analysis.spec.label)}</p>
      <form id="sign-form"><div class="field"><label for="report-reviewer">签认人</label><input id="report-reviewer" required maxlength="40" value="演示复核人"></div>
      <p class="fine desc">签认会保存当前数字、阈值、范围及源快照。</p>
      <button class="button primary" type="submit">确认签认</button></form>`);
}

function followUp(id) {
  const item=state.actions.find(row=>row.id===id&&row.bankId===state.bankId);
  if (!item) return;
  const bank=bankNow(), scope={...item.scope,period:shiftMonth(item.period,1),reference:"custom",basePeriod:item.period,cutoff:""};
  const a=analyze(bank,scope), key=item.metric;
  const ready=a.status==="full"&&finite(a.comparableCurrent?.[key])&&finite(a.base?.[key]);
  showDialog("下期复核 · "+item.id,
    table(["项目","复核依据"],[["本期",monthName(scope.period)],["基准",monthName(item.period)],["范围",scopeLabel(bank,scope)],["观察值",metricValue(key,a.current?.[key])],["可比变化",deltaValue(key,delta(a.comparableCurrent?.[key],a.base?.[key]))],["数据",ready?bank.snapshot:"缺少可比证据"],["验证条件",item.evidence]])+
    `<p class="fine">下期观察对应当前统计口径。策略净增量仍依赖可核对的实验或其他因果证据。</p>
    <form id="follow-form" data-existing="${esc(id)}">${field("follow-status","复核结果",[[ "已复核","记录已复核"],["方案未通过","记录方案未通过"],["待复核","证据不足，待复核"]].filter(([v])=>ready||v==="待复核"),ready?"已复核":"待复核")}
      <label class="label" for="follow-note">复核意见</label><textarea id="follow-note" required maxlength="400">${ready?"已核对下期同口径变化":"需补下期可比数据"}</textarea><button class="button primary" type="submit">保存复核</button></form>`);
}

function saveCase() {
  const bank=bankNow(), sample=sampleNow();
  const old=replayCase(sample,"arrival"), proposed=replayCase(sample,"appointment");
  if (!old||!proposed||old.winner!==sample.observedWinner) return announce("先核对原规则与实际分配。");
  if (!activityById(bank,sample.activity)?.strategies.length) return announce("请补活动和策略关联。");
  if (state.cases.some(item=>item.id===sample.id&&item.bankId===bank.id)) return announce("此样本已保存，可到活动工作台查看。");
  let improvement=bankActions().find(item=>item.period===sample.period&&item.channel===sample.channel);
  if (!improvement) {
    improvement={...actionScope(),...PLAYBOOK.leakage,kind:"leakage",id:`IMP-${String(state.actions.length+1).padStart(3,"0")}`,when:"30 天",due:"",
      evidence:"核对原规则、候选规则及模拟预发，下一期复核接触转化",status:"待验证"};
    state.actions.push(improvement);
  }
  improvement.caseId=sample.id;
  state.cases.push({bankId:bank.id,id:sample.id,snapshot:bank.snapshot,activity:sample.activity,improvement:improvement.id,
    period:sample.period,original:old.winner,expected:proposed.winner,version:sample.version,candidateVersion:"V2",input:sample,
    evidence:sample.source,scope:scopeLabel(bank,state.scope)});
  state.activityId=sample.activity;
  remember();
  render();
  announce(`已保存 ${sample.id} 并关联 ${improvement.id}。`);
}

function saveReceipt(activity) {
  const bank=bankNow();
  const evidence=state.preflights[bank.id];
  const cases=state.cases.filter(item=>item.bankId===bank.id&&item.activity===activity);
  if (!cases.length||evidence?.activity!==activity||!cases.every(item=>has(evidence.winners,item.id)&&evidence.winners[item.id]===item.expected)) return;
  state.receipts[bank.id]={activity,version:evidence.version,source:"模拟行内回执 REL-101",cases:cases.map(item=>item.id)};
  for (const item of bankActions().filter(row=>cases.some(c=>c.improvement===row.id))) item.status="待复核";
  remember();
  render();
  announce("已登记模拟行内发布回执。");
}

function advanceReview(activity) {
  const receipt=state.receipts[state.bankId];
  if (receipt?.activity!==activity) return;
  const item=state.cases.find(row=>receipt.cases.includes(row.id)&&row.bankId===state.bankId);
  if (!item) return;
  state.scope=scopeFor(bankNow(),{period:shiftMonth(item.period,1),branch:item.input.branch,channel:item.input.channel,reference:"custom",basePeriod:item.period});
  state.reportRequest=null;
  go("review");
}

function applyThresholds(next) {
  const previous=state.thresholdVersion||1;
  state.thresholdHistory=[...(state.thresholdHistory||[]),{version:"T-"+previous,rules:{...state.thresholds}}];
  state.thresholdVersion=previous+1;
  state.thresholds=next;
  if (state.questionResult) state.questionResult=runQuestion(state.question,bankNow(),state.scope,next);
  render();
}

function dispatch(action,value) {
  switch (action) {
    case "go": go(value); break;
    case "import": el("file-input").click(); break;
    case "reset-scope": resetScope(); render(); break;
    case "origin-tab": changeScope("origin",value); break;
    case "overview-dimension": state.overviewDimension=value; render(); break;
    case "metric": metricDialog(value); break;
    case "query-metric": metricDialog(value,state.questionResult?.focus?.analysis||rowCurrent()); break;
    case "close-dialog": el("detail-dialog").close(); break;
    case "diagnose-metric": state.metric=value; state.dimension="funnel"; go("diagnose"); break;
    case "export-detail": exportDetail(); break;
    case "download-bank": {
      const input=embedded.banks.find(item=>item.bankId===value);
      if (input) download(`CampaignLab-Simulated-Bank-${value}.json`,JSON.stringify(input)+"\n","application/json;charset=utf-8");
      break;
    }
    case "compare-banks": state.bankCheck=bankComparison(); render(); break;
    case "resolve-link": state.linkResolution=value; render(); break;
    case "reset-thresholds": applyThresholds({...bankNow().metadata.thresholds}); break;
    case "question-report": {
      const q=state.questionResult;
      if (q?.intent!=="报告") return;
      state.scope={...q.scope};
      state.reportRequest=q;
      state.reportType=q.reportType;
      go("report");
      break;
    }
    case "toggle-detail": state.aggregateOnly=!state.aggregateOnly; render(); break;
    case "save-case": saveCase(); break;
    case "new-action": state.actionKind=actionFor(state.metric); actionDialog(); break;
    case "edit-action": actionDialog(bankActions().find(item=>item.id===value)); break;
    case "follow-up": followUp(value); break;
    case "sign-report": signDialog(); break;
    case "view-report": {
      const report=state.reports.find(item=>item.id===value&&item.bankId===state.bankId);
      if (report) showDialog(report.id+" · 已签认",markdownView(report.text)+button("导出此签认版本","export-history",{value:report.id,tone:"small"}));
      break;
    }
    case "export-history": {
      const report=state.reports.find(item=>item.id===value&&item.bankId===state.bankId);
      if (report) download("CampaignLab-"+report.id+".md",report.text+"\n");
      break;
    }
    case "export-report": {
      const report=buildCurrentReport();
      if (report.status!=="待补数据") download("CampaignLab-策略复盘-"+state.scope.period+".md",report.text+"\n");
      break;
    }
    case "export-request": download("CampaignLab-取数清单.md",buildCurrentReport().requests+"\n"); break;
    case "revise": {
      const next=reviseSnapshot(bankNow());
      if (!next) return;
      banks.set(next.id,next);
      for (const item of bankActions().filter(row=>row.period===next.metadata.defaultScope.period)) item.status="待复核";
      state.questionResult=null; state.reportRequest=null; state.bankCheck=null;
      remember(); render(); announce("已导入模拟补数 LATE-01，原签认版本可回查。");
      break;
    }
    case "review-activity": state.scope.activity=value; state.reportRequest=null; go("review"); break;
    case "preflight": {
      const evidence=bankNow().metadata.preflight;
      if (evidence?.activity!==value) return;
      state.preflights[state.bankId]=evidence;
      remember(); render(); announce("已导入模拟预发结果。");
      break;
    }
    case "receipt": saveReceipt(value); break;
    case "next-review": advanceReview(value); break;
  }
}

document.addEventListener("click",event=>{
  const control=event.target.closest("[data-action]");
  if (!control||control.disabled) return;
  event.preventDefault();
  dispatch(control.dataset.action,control.dataset.value);
});

document.addEventListener("toggle",event=>{
  if (event.target.id==="advanced-filters") state.advanced=event.target.open;
  if (event.target.id==="threshold-details") state.thresholdOpen=event.target.open;
},true);

document.addEventListener("change",event=>{
  const {id,value}=event.target;
  if (id.startsWith("scope-")) {changeScope(id.slice(6),value);return;}
  switch (id) {
    case "bank-picker":
      state.bankId=value;state.thresholds={...bankNow().metadata.thresholds};state.thresholdVersion=1;state.thresholdHistory=[];
      state.linkResolution="pending";state.classResult=null;state.classInput=null;state.questionResult=null;
      state.bankCheck=null;state.reportRequest=null;state.importError="";
      if (!bankNow().branches[state.scope.branch] && state.scope.branch!==ALL) resetScope();
      render();
      break;
    case "diagnostic-metric": state.metric=value;state.dimension="funnel";render();break;
    case "diagnostic-dimension": state.dimension=value;render();break;
    case "anomaly-rule": state.anomalyRule=value;render();break;
    case "question-type": state.questionType=value;state.questionExample="";render();break;
    case "question-sample": {
      const q=embedded.questions.find(([id])=>id===value);
      state.questionExample=value;
      if (q) {
        state.question=q[2];
        state.questionResult=runQuestion(state.question,bankNow(),state.scope,state.thresholds);
      }
      render();
      break;
    }
    case "replay-case": state.caseId=value;render();break;
    case "activity-select": state.activityId=value;render();break;
    case "action-kind": {
      const choice=PLAYBOOK[value];
      el("action-owner").value=choice.owner;
      el("action-text").value=choice.action;
      break;
    }
  }
});

document.addEventListener("submit",event=>{
  event.preventDefault();
  const form=event.target;
  switch (form.id) {
    case "question-form":
      state.question=el("question-input").value;
      state.questionExample="";
      state.questionResult=runQuestion(state.question,bankNow(),state.scope,state.thresholds);
      render();
      break;
    case "scenario-form":
      state.scenario=clamp(Number(el("scenario-rate").value),0,100);render();break;
    case "threshold-form":
      applyThresholds(Object.fromEntries([...new FormData(form)].map(([key,value])=>[key,Number(value)])));
      break;
    case "class-form": {
      const data=new FormData(form);
      const flags=["received","attempted","answered","delivered","message","clicked","detail","freqBlocked","daysInRange","downstream"];
      const inputs={channel:el("class-channel").value,line:el("class-line").value,seconds:Number(el("class-seconds").value),rounds:Number(el("class-rounds").value)};
      for (const key of flags) inputs[key]=data.has(key);
      state.classInput=inputs;state.classResult=classifyChannel(bankNow(),inputs);render();break;
    }
    case "action-form": {
      const id=form.dataset.existing;
      const old=bankActions().find(item=>item.id===id);
      const kind=el("action-kind").value;
      const item={...(old||actionScope()),id:id||`IMP-${String(state.actions.length+1).padStart(3,"0")}`,
        kind,name:PLAYBOOK[kind].name,when:el("action-when").value,owner:cleanText(el("action-owner").value),
        due:el("action-due").value,action:cleanText(el("action-text").value),evidence:cleanText(el("action-evidence").value),status:event.submitter?.value||"已分派"};
      if (old) Object.assign(old,item); else state.actions.push(item);
      el("detail-dialog").close();remember();go("report");announce("已保存改进项 "+item.id+"。");break;
    }
    case "sign-form": {
      const report=buildCurrentReport();
      if (!report.canSign) return;
      state.reports.push({id:`RP-${String(state.reports.length+1).padStart(3,"0")}`,bankId:state.bankId,snapshot:bankNow().snapshot,
        scopeLabel:scopeLabel(bankNow(),state.scope),scope:{...state.scope},period:periodText(state.scope),reviewer:cleanText(el("report-reviewer").value),
        thresholds:{...state.thresholds},text:report.text,evidence:report.evidence});
      el("detail-dialog").close();remember();render();announce("已保存本次签认与来源快照。");break;
    }
    case "follow-form": {
      const item=bankActions().find(row=>row.id===form.dataset.existing);
      if (!item) return;
      item.status=el("follow-status").value;
      item.review=cleanText(el("follow-note").value);
      item.reviewSource=bankNow().snapshot;
      el("detail-dialog").close();remember();render();announce("已保存下期复核。");break;
    }
  }
});

el("file-input").addEventListener("change",async event=>{
  const file=event.target.files?.[0];
  if (!file) return;
  try {
    assertData(file.size<=8000000,"文件超过原型的 8 MB 导入上限。");
    const raw=JSON.parse(await file.text());
    const incoming=normalizeBank(raw);
    const existing=banks.get(incoming.id);
    const sameSnapshot=existing?.snapshot===incoming.snapshot;
    if (sameSnapshot) assertData(JSON.stringify(existing.raw)===JSON.stringify(raw),"相同快照版本对应不同内容，请使用新的快照版本。");
    else banks.set(incoming.id,incoming);
    state.bankId=incoming.id;
    state.intakeLog.push(sameSnapshot ? incoming.snapshot+" 已存在，复用原批次" : incoming.snapshot+" 已导入 "+incoming.records.length+" 个统计切片");
    state.importError="";
    state.thresholds={...incoming.metadata.thresholds};
    state.thresholdVersion=1;state.thresholdHistory=[];
    state.linkResolution="pending";state.classResult=null;state.classInput=null;
    resetScope();go("data");announce(state.intakeLog.at(-1));
  } catch(error) {
    state.importError="导入校验失败 · "+error.message;
    go("data");
    announce("导入校验失败，保留当前数据。");
  } finally {event.target.value="";}
});

render();
