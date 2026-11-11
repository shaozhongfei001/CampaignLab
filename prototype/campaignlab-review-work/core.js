"use strict";

const STAGES = [
  ["sent", "渠道下发"], ["success", "下发成功"], ["executed", "已执行"],
  ["contacted", "已接触"], ["effective", "有效接触"],
];
const COUNTS = ["eligible", ...STAGES.map(([key]) => key), "capacity", "intentCount", "activityCount"];
const MONEY = ["aum", "deposit", "wealth", "fund", "loan", "wealthSale", "nonCashWealthSale", "fundSale", "nonMoneyFundSale", "insuranceSale", "depositDemand", "depositTerm"];
const DIMS = ["id", "period", "cutoff", "branch", "subbranch", "channel", "strategy", "origin", "segment", "tag", "cohort", "offset", "definition", "batch"];
const SALES = ["wealthSale", "nonCashWealthSale", "fundSale", "nonMoneyFundSale", "insuranceSale"];
const PRODUCTS = ["aum", "deposit", "wealth", "fund", "loan", ...SALES];
const METRICS = {
  deployed: {name: "已部署分行数", unit: "家"},
  strategies: {name: "下发策略数", unit: "项", aliases: ["策略数", "策略数量"]},
  eligible: {name: "可经营客户数", unit: "人"},
  sent: {name: "下发客户数", unit: "人", aliases: ["下发人数", "名单规模"]},
  success: {name: "下发成功客户数", unit: "人", aliases: ["下发成功人数"]},
  executed: {name: "已执行客户数", unit: "人"},
  contacted: {name: "已接触客户数", unit: "人", aliases: ["触达客户数", "接触客户数"]},
  effective: {name: "有效触达客户数", unit: "人", aliases: ["有效接触客户数", "有效触客数", "有效触达人数"]},
  cover: {name: "策略覆盖率", fraction: ["success", "eligible"], aliases: ["覆盖率"]},
  successRate: {name: "下发成功率", fraction: ["success", "sent"]},
  execution: {name: "名单执行率", fraction: ["executed", "success"], aliases: ["执行率"]},
  reach: {name: "触达率", fraction: ["contacted", "success"], aliases: ["接触率"]},
  effectiveRate: {name: "有效触达率", fraction: ["effective", "success"], aliases: ["有效接触率"]},
  contactConv: {name: "接触层间转化率", fraction: ["contacted", "executed"], aliases: ["接触转化率"]},
  validConv: {name: "有效接触层间转化率", fraction: ["effective", "contacted"], aliases: ["有效接触转化率"]},
  aum: {name: "AUM余额增量", unit: "元", aliases: ["AUM增量", "AUM"]},
  deposit: {name: "存款余额增量", unit: "元", aliases: ["存款增量"]},
  wealth: {name: "理财余额增量", unit: "元", aliases: ["理财增量"]},
  fund: {name: "基金余额增量", unit: "元", aliases: ["基金增量"]},
  loan: {name: "个贷余额增量", unit: "元", aliases: ["个贷增量"]},
  wealthSale: {name: "理财销量", unit: "元"},
  nonCashWealthSale: {name: "非现金管理类理财销量", unit: "元", aliases: ["非现管理财销量"]},
  fundSale: {name: "基金销量", unit: "元"},
  nonMoneyFundSale: {name: "非货币基金销量", unit: "元", aliases: ["非货基金销量", "非货基销量"]},
  insuranceSale: {name: "保险销量", unit: "元"},
  depositDemand: {name: "活期存款增量", unit: "元"},
  depositTerm: {name: "定期存款增量", unit: "元"},
  intentCount: {name: "意向沟通次数", unit: "次"},
  activityCount: {name: "活动特色人数", unit: "人"},
  capacity: {name: "可执行容量", unit: "席次"},
};
const FUNNEL_RATES = ["successRate", "execution", "contactConv", "validConv"];
const MAIN_METRICS = ["cover", "successRate", "execution", "reach", "effectiveRate", "effective", "contactConv", "validConv", "aum", "deposit", ...SALES];
const ALL = "all";
const DECIMALS = new Intl.NumberFormat("zh-CN", {maximumFractionDigits: 2});
const num = value => value === null || value === undefined || !Number.isFinite(value) ? "—" : DECIMALS.format(value);
const pct = value => value === null || value === undefined || !Number.isFinite(value) ? "—" : `${(value * 100).toFixed(2).replace(/\.?0+$/, "")}%`;
const ratio = (a, b) => Number.isFinite(a) && b > 0 ? a / b : null;
const finite = value => Number.isFinite(value);
const round = value => Math.round((value + Number.EPSILON) * 100) / 100;
const unique = values => [...new Set(values)];
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const money = value => !finite(value) ? "—" : `${value < 0 ? "−" : ""}¥${num(Math.abs(value))}`;
const signed = value => !finite(value) ? "—" : `${value > 0 ? "+" : ""}${num(value)}`;
const metricValue = (key, value) => METRICS[key].fraction ? pct(value) : METRICS[key].unit === "元" ? money(value) : num(value);
const deltaValue = (key, value) => !finite(value) ? "—" : METRICS[key].fraction ? `${signed(round(value * 100))} 个百分点` : `${signed(round(value))} ${METRICS[key].unit}`;
const delta = (a, b) => finite(a) && finite(b) ? a - b : null;
const monthName = period => period && /^\d{4}-\d{2}$/.test(period) ? `${period.slice(0, 4)} 年 ${Number(period.slice(-2))} 月` : period || "待选";
const has = (object, key) => Object.hasOwn(object, key);

function shiftMonth(period, difference) {
  if (!/^\d{4}-\d{2}$/.test(period || "")) return null;
  const [y, m] = period.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1 + difference, 1)).toISOString().slice(0, 7);
}

function assertData(condition, message) {
  if (!condition) throw new Error(message);
}

function readTable(tables, name) {
  const table = tables?.[name];
  assertData(table && Array.isArray(table.columns) && Array.isArray(table.rows), `缺少数据表「${name}」`);
  assertData(unique(table.columns).length === table.columns.length, `「${name}」存在重复列名`);
  assertData(table.rows.every(row => Array.isArray(row) && row.length === table.columns.length), `「${name}」的行列数不一致`);
  return table.rows.map(row => Object.fromEntries(table.columns.map((key, index) => [key, row[index]])));
}

function normalizeBank(input) {
  assertData(input && input.synthetic === true && input.schemaVersion === 1, "请选择格式版本 1 的 CampaignLab 合成数据文件。");
  const {mapping, metadata, tables} = input;
  assertData(input.bankId && input.bankName && input.snapshotVersion && mapping?.version && metadata, "缺少银行、快照或接入配置。");
  assertData(["wide", "long"].includes(mapping.layout) && finite(mapping.moneyDivisor) && mapping.moneyDivisor > 0, "接入配置的表形或金额单位无效。");
  assertData(Array.isArray(metadata.branches) && Array.isArray(metadata.strategies) && Array.isArray(metadata.periods) && Array.isArray(metadata.activities) && Array.isArray(metadata.sources) && metadata.channels && metadata.defaultScope && metadata.thresholds, "缺少机构、渠道、策略、月份、数据来源或异常规则字典。");
  const branches = Object.fromEntries(metadata.branches.map(b => [b.id, b]));
  const strategies = Object.fromEntries(metadata.strategies.map(s => [s.id, s]));
  const entities = readTable(tables, mapping.entityTable);
  const byId = new Map();
  if (mapping.layout === "long") {
    const {id, metric, value} = mapping.longColumns || {};
    for (const row of readTable(tables, mapping.countsTable)) {
      assertData(typeof row[id] === "string" && typeof row[metric] === "string", "阶段长表缺少切片键或指标码。");
      if (!byId.has(row[id])) byId.set(row[id], Object.create(null));
      const item = byId.get(row[id]);
      assertData(!has(item, row[metric]), `阶段指标重复 · ${row[id]} · ${row[metric]}`);
      item[row[metric]] = row[value];
    }
  }
  const ids = new Set();
  const records = entities.map((row, index) => {
    const item = {};
    for (const field of DIMS) {
      const raw = row[mapping.dimensions?.[field]];
      const codes = mapping.codes?.[field];
      item[field] = codes && has(codes, raw) ? codes[raw] : raw;
      assertData(field === "offset" ? Number.isSafeInteger(item[field]) && item[field] >= 0 : typeof item[field] === "string" && item[field].length, `第 ${index + 1} 行缺少「${field}」`);
    }
    assertData(!ids.has(item.id), `重复切片 ${item.id}`);
    ids.add(item.id);
    assertData(branches[item.branch] && strategies[item.strategy] && has(metadata.channels, item.channel), `未知机构、策略或渠道 · ${item.id}`);
    assertData(["branch", "hq"].includes(item.origin) && item.origin === strategies[item.strategy].origin, `策略来源不一致 · ${item.id}`);
    assertData(/^\d{4}-(0[1-9]|1[0-2])$/.test(item.period) && item.cutoff.startsWith(item.period) && /^\d{4}-\d{2}-\d{2}$/.test(item.cutoff), `统计期或数据截止无效 · ${item.id}`);
    const values = mapping.layout === "wide" ? row : byId.get(item.id);
    for (const field of COUNTS) {
      const value = values?.[mapping.countFields?.[field]];
      assertData(Number.isSafeInteger(value) && value >= 0, `「${field}」缺失或不是非负人数 · ${item.id}`);
      item[field] = value;
    }
    const levels = [item.eligible, ...STAGES.map(([key]) => item[key])];
    assertData(levels.every((value, i) => i === 0 || value <= levels[i - 1]), `漏斗人数不满足嵌套关系 · ${item.id}`);
    for (const field of MONEY) {
      const value = row[mapping.moneyFields?.[field]];
      assertData(value === null || finite(value), `「${field}」缺失或金额格式无效 · ${item.id}`);
      item[field] = value === null ? null : round(value / mapping.moneyDivisor);
    }
    item.evidence = `${mapping.entityTable} / 第 ${index + 1} 行 / ${item.batch}`;
    return item;
  });
  assertData([...byId.keys()].every(id => ids.has(id)), "阶段长表存在无法匹配的切片键。");
  return {raw: input, id: input.bankId, name: input.bankName, snapshot: input.snapshotVersion, mapping, metadata, branches, strategies, records};
}

function scopeFor(bank, patch = {}) {
  return {
    period: bank.metadata.defaultScope.period, branch: bank.metadata.defaultScope.branch,
    channel: bank.metadata.defaultScope.channel, group: ALL, origin: ALL, subbranch: ALL,
    segment: ALL, segmentBasis: "segment", strategy: ALL, activity: ALL,
    reference: "previous", basePeriod: "", compareBranch: "", periods: null, channels: null, cutoff: "", ...patch,
  };
}

function activityById(bank, id) {
  return bank.metadata.activities.find(item => item.id === id);
}

function scopeRows(bank, scope, periods = scope.periods || [scope.period]) {
  const selected = new Set(periods);
  const activity = scope.activity !== ALL ? activityById(bank, scope.activity) : null;
  if (scope.activity !== ALL && !activity?.strategies?.length) return [];
  return bank.records.filter(row =>
    selected.has(row.period) && (!scope.cutoff || row.period !== scope.period || row.cutoff === scope.cutoff) &&
    (scope.branch === ALL || row.branch === scope.branch) &&
    (scope.group === ALL || bank.branches[row.branch].group === scope.group) &&
    (scope.channel === ALL || row.channel === scope.channel) && (!scope.channels || scope.channels.includes(row.channel)) &&
    (scope.origin === ALL || row.origin === scope.origin) &&
    (scope.subbranch === ALL || row.subbranch === scope.subbranch) &&
    (scope.strategy === ALL || row.strategy === scope.strategy) &&
    (scope.segment === ALL || row[scope.segmentBasis] === scope.segment) &&
    (!activity || (row.period >= activity.from && row.period <= activity.to && activity.strategies.includes(row.strategy)))
  );
}

function unionLength(intervals) {
  const ordered = intervals.slice().sort((a, b) => a[0] - b[0]);
  let end = 0;
  let result = 0;
  for (const [start, stop] of ordered) {
    result += Math.max(0, stop - Math.max(start, end));
    end = Math.max(end, stop);
  }
  return result;
}

function aggregate(rows) {
  if (!rows.length) return null;
  const sets = new Map();
  for (const row of rows) {
    const key = `${row.period}|${row.cohort}`;
    if (!sets.has(key)) sets.set(key, []);
    sets.get(key).push(row);
  }
  const result = {
    deployed: unique(rows.filter(row => row.sent > 0).map(row => row.branch)).length,
    strategies: unique(rows.filter(row => row.sent > 0).map(row => `${row.period}|${row.strategy}`)).length,
  };
  for (const key of ["eligible", ...STAGES.map(([field]) => field)]) {
    result[key] = [...sets.values()].reduce((n, set) => n + unionLength(set.map(row => [row.offset, row.offset + row[key]])), 0);
  }
  for (const key of ["capacity", "intentCount", "activityCount"]) result[key] = rows.reduce((sum, row) => sum + row[key], 0);
  for (const key of MONEY) result[key] = rows.some(row => row[key] === null) ? null : round(rows.reduce((sum, row) => sum + row[key], 0));
  for (const [key, metric] of Object.entries(METRICS)) {
    if (metric.fraction) result[key] = ratio(...metric.fraction.map(field => result[field]));
  }
  return result;
}

function scopeLabel(bank, scope) {
  const parts = [];
  parts.push(scope.branch === ALL ? scope.group === ALL ? "全行" : scope.group : `${bank.branches[scope.branch]?.name || scope.branch}分行`);
  if (scope.subbranch !== ALL) parts.push(scope.subbranch);
  parts.push(scope.channel === ALL ? "全渠道" : bank.metadata.channels[scope.channel]);
  if (scope.origin !== ALL) parts.push(scope.origin === "hq" ? "总行下发" : "分行自主");
  if (scope.strategy !== ALL) parts.push(bank.strategies[scope.strategy]?.name || scope.strategy);
  if (scope.segment !== ALL) parts.push(`${scope.segment}（${scope.segmentBasis === "tag" ? "月末标签" : "部署客群"}）`);
  if (scope.activity !== ALL) parts.push(activityById(bank, scope.activity)?.name || scope.activity);
  return parts.join(" · ");
}

function baselineSpec(bank, scope) {
  const selected = scope.periods || [scope.period];
  if (scope.reference === "target") return {label: "演示目标", target: true, periods: selected};
  if (scope.reference === "peer" || scope.reference === "bank") {
    const branch = bank.branches[scope.branch];
    const group = scope.reference === "peer" ? branch?.group || (scope.group !== ALL ? scope.group : null) : null;
    const peers = Object.values(bank.branches).filter(b => (!group || b.group === group) && (scope.reference === "bank" || b.id !== scope.branch));
    return {label: scope.reference === "peer" ? `${group || "当前组待选"}均值（分行等权，剔除本行）` : "全行分行均值（分行等权）", peers: scope.reference === "peer" && !group ? [] : peers, periods: selected};
  }
  if (scope.reference === "hq") return {label: "同期间总行下发策略", patch: {origin: "hq"}, periods: selected};
  if (scope.reference === "branch") return {label: `${bank.branches[scope.compareBranch]?.name || "待选"}分行`, patch: {branch: scope.compareBranch, group: ALL, subbranch: ALL}, periods: selected};
  if (scope.reference === "custom") return {label: monthName(scope.basePeriod), periods: [scope.basePeriod]};
  const yearly = scope.reference === "yoy" || selected.length > 1;
  const periods = selected.map(period => shiftMonth(period, yearly ? -12 : -1));
  return {label: periods.length > 1 ? `${periods[0]} 至 ${periods.at(-1)}（去年同期）` : `${monthName(periods[0])}（${yearly ? "同比" : "环比"}）`, periods};
}

function alignRows(current, base, spec, scope, bank) {
  if (!current.length || !base.length) return {status: "missing", current: [], base: [], notes: ["缺本期或基准数据"]};
  const endOfMonth = row => shiftMonth(row.period, 1) && new Date(`${shiftMonth(row.period, 1)}-01T00:00:00Z`).getTime() - Date.parse(`${row.cutoff}T00:00:00Z`) === 86400000;
  const timePair = new Map();
  (scope.periods || [scope.period]).forEach((period, index) => timePair.set(period, spec.periods[index] || spec.periods[0]));
  const left = [], right = [], notes = [];
  for (const [period, comparator] of timePair) {
    const a = current.filter(row => row.period === period);
    const b = base.filter(row => row.period === comparator);
    for (const channel of unique([...a, ...b].map(row => row.channel))) {
      const ar = a.filter(row => row.channel === channel), br = b.filter(row => row.channel === channel);
      const versions = rows => unique(rows.map(row => row.definition)).sort().join("|");
      const dateTag = rows => unique(rows.map(row => endOfMonth(row) ? "月结" : row.cutoff.slice(-2))).sort().join("|");
      if (!ar.length || !br.length || versions(ar) !== versions(br) || dateTag(ar) !== dateTag(br)) {
        notes.push(`${period} / ${bank.metadata.channels[channel]} · ${!ar.length || !br.length ? "采集覆盖不同" : versions(ar) !== versions(br) ? "指标口径不同" : "数据截止进度不同"}`);
      } else {
        left.push(...ar);
        right.push(...br);
      }
    }
  }
  return {status: !left.length ? "missing" : notes.length ? "partial" : "full", current: left, base: right, notes};
}

function averageSummaries(items) {
  if (!items.length) return null;
  return Object.fromEntries(Object.keys(METRICS).map(key => {
    const values = items.map(item => item[key]);
    return [key, values.every(finite) ? values.reduce((a, b) => a + b, 0) / values.length : null];
  }));
}

function analyze(bank, scope, prefiltered = null) {
  const rows = prefiltered || scopeRows(bank, scope);
  const current = aggregate(rows);
  const spec = baselineSpec(bank, scope);
  if (spec.target) return {scope, spec, rows, current, comparableCurrent: current, base: bank.metadata.goals || {}, baselineRows: [], status: current ? "full" : "missing", notes: ["演示目标仅提供已登记指标"]};
  if (spec.peers) {
    const aligned = spec.peers.map(branch => {
      const compared = scopeRows(bank, {...scope, branch: branch.id, group: ALL, subbranch: ALL}, spec.periods);
      return alignRows(rows, compared, spec, scope, bank);
    }).filter(item => item.status !== "missing");
    const ready = aligned.length > 0 && aligned.length === spec.peers.length && aligned.every(item => item.status === "full");
    return {scope, spec, rows, current, comparableCurrent: ready ? current : null,
      base: ready ? averageSummaries(aligned.map(item => aggregate(item.base))) : null,
      baselineRows: aligned.flatMap(item => item.base), status: ready ? "full" : "missing",
      notes: ready ? [] : ["同组或全行参照缺少完整同口径分行样本"]};
  }
  const baseRows = scopeRows(bank, {...scope, ...spec.patch}, spec.periods);
  const aligned = alignRows(rows, baseRows, spec, scope, bank);
  return {scope, spec, rows, current, comparableCurrent: aggregate(aligned.current), base: aggregate(aligned.base), baselineRows: aligned.base, comparableRows: aligned.current, status: aligned.status, notes: aligned.notes};
}

function funnelDecomposition(current, previous) {
  if (!current || !previous || [current, previous].some(summary => FUNNEL_RATES.some(key => !finite(summary[key])))) return null;
  const keys = ["sent", ...FUNNEL_RATES];
  const before = keys.map(key => previous[key]);
  const after = keys.map(key => current[key]);
  const product = values => values.reduce((total, value) => total * value, 1);
  let last = product(before);
  return keys.map((key, i) => {
    const next = product(after.slice(0, i + 1).concat(before.slice(i + 1)));
    const effect = round(next - last);
    last = next;
    return {key, name: METRICS[key].name, before: before[i], after: after[i], effect};
  });
}

function byDimension(bank, rows, dimension, scope) {
  const groups = new Map();
  for (const row of rows) {
    const key = dimension === "group" ? bank.branches[row.branch].group : dimension === "segment" ? row[scope.segmentBasis] : row[dimension];
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return groups;
}

function dimensionName(bank, dimension, key) {
  if (dimension === "branch") return `${bank.branches[key]?.name || key}分行`;
  if (dimension === "channel") return bank.metadata.channels[key] || key;
  if (dimension === "strategy") return bank.strategies[key]?.name || key;
  if (dimension === "origin") return key === "hq" ? "总行下发" : "分行自主";
  return key;
}

function dimensionSplit(bank, result, metric, dimension) {
  const {scope, status, base, spec} = result;
  if (!result.comparableCurrent || !base || status === "missing" || spec.target) return {rows: [], residual: null, reason: "缺少可用于拆解的可比明细"};
  const denom = METRICS[metric].fraction?.[1];
  const numer = METRICS[metric].fraction?.[0];
  if (dimension === "depositType") {
    const rows = ["depositDemand", "depositTerm"].map(key => ({
      key, name: METRICS[key].name, current: result.comparableCurrent[key], base: base[key],
      effect: delta(result.comparableCurrent[key], base[key]),
    }));
    return {rows, residual: 0, reason: "存款余额增量按活期与定期组成拆分"};
  }
  const left = byDimension(bank, result.comparableRows || result.rows, dimension, scope);
  const right = byDimension(bank, result.baselineRows, dimension, scope);
  const weighted = (summary, total) => denom ? ratio(summary?.[numer] || 0, total?.[denom]) : summary?.[metric] ?? null;
  function benchmarkFor(rows) {
    if (!rows.length) return null;
    if (!spec.peers) return aggregate(rows);
    const byBranch = byDimension(bank, rows, "branch", scope);
    return averageSummaries(spec.peers.map(branch => aggregate(byBranch.get(branch.id) || []) || Object.fromEntries(Object.keys(METRICS).map(key => [key, METRICS[key].fraction ? null : 0]))));
  }
  const rows = unique([...left.keys(), ...right.keys()]).map(key => {
    const l = aggregate(left.get(key) || []);
    const r = benchmarkFor(right.get(key) || []);
    let effect = delta(weighted(l, result.comparableCurrent), weighted(r, base));
    if (!denom && effect === null && Boolean(l) !== Boolean(r)) effect = (l?.[metric] ?? 0) - (r?.[metric] ?? 0);
    return {key, name: dimensionName(bank, dimension, key), current: l?.[metric] ?? null, base: r?.[metric] ?? null, effect};
  }).sort((a, b) => Math.abs(b.effect ?? 0) - Math.abs(a.effect ?? 0));
  const total = delta(result.comparableCurrent[metric], base[metric]);
  const residual = finite(total) && rows.every(row => finite(row.effect)) ? total - rows.reduce((sum, row) => sum + row.effect, 0) : null;
  return {rows, residual, reason: spec.peers && denom ? "分行等权基准与合计分母存在差异时，余量保留在表尾。"
    : denom ? "各维度分子除以当期总体分母后比较，交叉覆盖调整计入余量。"
    : "按可比子集的变化量比较，客户交叉覆盖调整计入余量。"};
}

function scanAnomalies(bank, scope, threshold, keys = MAIN_METRICS, rules = "all", direction = "both") {
  const main = analyze(bank, scope);
  if (!main.current) return [];
  const rows = [];
  const compare = (key, label, result, limit, kind, directionOnly = "both") => {
    const cur = result.comparableCurrent?.[key], base = result.base?.[key];
    if (result.status !== "full" || !finite(cur) || !finite(base) || base <= 0) return;
    const change = cur - base, relative = change / base;
    if (Math.abs(relative) + 1e-10 < limit / 100 || change === 0 ||
      (directionOnly === "down" || direction === "down") && change >= 0 || direction === "up" && change <= 0) return;
    rows.push({key, label, kind, cur, base, change, relative, threshold: `${limit}%`, baseline: result.spec.label, impact: METRICS[key].fraction ? deltaValue(key, change) : `${num(Math.abs(change))} ${METRICS[key].unit}`});
  };
  if (["all", "mom"].includes(rules)) {
    const used = ["previous", "yoy", "custom", "target", "branch", "hq", "peer", "bank"].includes(scope.reference) ? main : analyze(bank, {...scope, reference: "previous"});
    for (const key of keys) compare(key, scope.reference === "peer" || scope.reference === "bank" ? "参照偏离" : "期间偏离", used, threshold.mom, "mom");
  }
  if (["all", "peer", "layer"].includes(rules)) {
    const peer = analyze(bank, {...scope, reference: "peer"});
    for (const key of keys) {
      if (rules !== "layer") compare(key, "显著跑输同组", peer, threshold.peer, "peer", "down");
      if (rules !== "peer" && FUNNEL_RATES.includes(key)) compare(key, "层间转化低于同组", peer, threshold.layer, "layer", "down");
    }
  }
  if (["all", "own"].includes(rules) && !scope.periods && direction !== "up") {
    const history = Array.from({length: 6}, (_, index) => shiftMonth(scope.period, -index - 1)).map(period =>
      analyze(bank, {...scope, reference: "custom", basePeriod: period}));
    if (history.every(item => item.status === "full")) {
      for (const key of keys) {
        const values = history.map(item => item.base[key]);
        const cur = main.current[key];
        if (!values.every(finite) || !finite(cur)) continue;
        const mean = values.reduce((a, b) => a + b, 0) / values.length;
        const sigma = Math.sqrt(values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length);
        if (sigma > 0 && cur < mean && mean - cur + 1e-10 >= threshold.own * sigma) {
          rows.push({key, label: "低于近 6 月自身均值", kind: "own", cur, base: mean, change: cur - mean, threshold: `${threshold.own}σ（σ=${metricValue(key, sigma)}）`, baseline: "近 6 个可比月", impact: deltaValue(key, cur - mean)});
        }
      }
    }
  }
  if (["all", "mix"].includes(rules) && keys.includes("effective")) {
    const pair = analyze(bank, {...scope, reference: "previous"});
    if (pair.status === "full" && pair.baselineRows.length) {
      for (const dim of ["channel", "segment", "subbranch"]) {
        const group = rows => {
          const splits = byDimension(bank, rows, dim, scope);
          const values = [...splits].map(([key, items]) => [key, aggregate(items).effective]);
          const sum = values.reduce((total, [, value]) => total + value, 0);
          return Object.fromEntries(values.map(([key, value]) => [key, ratio(value, sum)]));
        };
        const a = group(pair.rows), b = group(pair.baselineRows);
        for (const key of unique([...Object.keys(a), ...Object.keys(b)])) {
          const cur = a[key] ?? 0, base = b[key] ?? 0, change = cur - base;
          if (Math.abs(change) + 1e-10 >= threshold.mix / 100 && !(direction === "up" && change <= 0 || direction === "down" && change >= 0)) {
            rows.push({key: "effectiveRate", label: `结构变化 · ${dimensionName(bank, dim, key)}`, kind: "mix", cur, base, change, threshold: `${threshold.mix} 个百分点`, baseline: "与上月对比的分组有效接触计次占比", impact: `${signed(round(change * 100))} 个百分点`});
          }
        }
      }
    }
  }
  return rows;
}

function daysBetween(later, earlier) {
  return (Date.parse(`${later}T00:00:00Z`) - Date.parse(`${earlier}T00:00:00Z`)) / 86400000;
}

function matchOutcomes(bank, resolution = "pending") {
  const {linkPolicy, linkEvidence} = bank.metadata;
  if (!linkPolicy || !linkEvidence) return [];
  return linkEvidence.outcomes.map(outcome => {
    const candidates = linkEvidence.touches.filter(t => t.customer === outcome.customer).map(touch => {
      const age = daysBetween(outcome.date, touch.at);
      const dispatch = daysBetween(touch.dispatchDate, touch.at);
      const window = linkPolicy.routeWindows[touch.channel];
      const allowed = linkPolicy.dispatchDays[touch.channel];
      return {...touch, age, dispatch, matched: Boolean(window && allowed?.includes(dispatch) && age >= window[0] && age <= window[1])};
    });
    const matched = candidates.filter(touch => touch.matched).sort((a, b) => a.age - b.age || a.id.localeCompare(b.id));
    const chosen = matched.length === 1 ? matched[0] : resolution === "nearest" && matched.length && matched[0].age !== matched[1]?.age ? matched[0] : null;
    return {...outcome, candidates, matched, chosen, status: !matched.length ? "未匹配" : chosen ? matched.length === 1 ? "唯一匹配" : "已按规则归属" : "多候选待核"};
  });
}

function replayCase(sample, rule) {
  if (!sample || !sample.version || !Array.isArray(sample.events) || !Number.isSafeInteger(sample.used) || !Number.isSafeInteger(sample.cap)) return null;
  const order = sample.events.slice().sort((a, b) => {
    const priority = rule === "appointment" ? Number(b.appointment) - Number(a.appointment) : 0;
    return priority || a.time.localeCompare(b.time) || a.strategy.localeCompare(b.strategy);
  });
  let used = sample.used;
  const trace = order.map(event => {
    const chosen = used < sample.cap;
    if (chosen) used++;
    return {...event, chosen, reason: chosen ? "已获得触达名额" : "单日同渠道频次已达上限"};
  });
  const winners = trace.filter(event => event.chosen).map(event => event.strategy);
  return {trace, winner: winners[0] ?? null, used};
}

function classifyChannel(bank, input) {
  const {channel, seconds, line, rounds, clicked, detail, received, attempted, answered, message, delivered, freqBlocked, daysInRange, downstream} = input;
  const sent = channel === "ai" ? received : true;
  const success = sent && received && !(channel === "ai" && freqBlocked);
  let execution = false, contact = false, effective = false;
  if (channel === "sms" || channel === "push") {
    execution = channel === "sms" ? attempted : delivered;
    contact = clicked;
    effective = detail && (channel !== "push" || seconds >= bank.metadata.pushDetailSeconds);
  } else if (channel === "wechat") {
    execution = message || seconds > 0;
    contact = delivered || seconds > 0;
    effective = rounds >= 1 || seconds >= 60 || clicked;
  } else if (channel === "ai" || channel === "remote") {
    execution = attempted && (channel !== "remote" || daysInRange);
    contact = answered;
    effective = channel === "ai" ? rounds >= 1 : seconds >= (line === "loan" ? 10 : 60);
  } else if (channel === "manager") {
    execution = attempted && daysInRange;
    contact = answered;
    effective = downstream;
  }
  const executed = success && execution;
  const contacted = executed && contact;
  return {sent, success, executed, contacted, effective: contacted && effective};
}

const DIM_LABELS = {branch: "分行", group: "分组", channel: "渠道", subbranch: "支行", segment: "客群", origin: "策略来源", strategy: "策略", depositType: "存款类型"};
const TERMS = Object.entries(METRICS).flatMap(([key, definition]) => [definition.name, ...(definition.aliases || [])].map(term => [term, key])).sort((a, b) => b[0].length - a[0].length);
const ROUTES = {
  remote: ["远程"], manager: ["客户经理", "个贷经理"], ai: ["AI外呼", "ai外呼"],
  wechat: ["企业微信", "企微"], sms: ["短信"], push: ["手机银行推送", "手机银行push", "手机银行", "push", "PUSH"],
};

function findMetrics(question) {
  let remainder = question;
  const keys = [];
  for (const [term, key] of TERMS) {
    if (remainder.includes(term)) {
      keys.push(key);
      remainder = remainder.replaceAll(term, " ");
    }
  }
  return unique(keys);
}

function requestedDates(question, context) {
  const dates = [];
  const year = question.match(/(20\d{2})年/)?.[1] || context.period.slice(0, 4);
  for (const match of question.matchAll(/(?:(20\d{2})年\s*)?(1[0-2]|0?[1-9])\s*月|\b(20\d{2})-(0[1-9]|1[0-2])\b/g)) {
    dates.push(`${match[1] || match[3] || year}-${(match[2] || match[4]).padStart(2, "0")}`);
  }
  if (/上个?月/.test(question)) dates.push(shiftMonth(context.period, -1));
  return unique(dates).sort();
}

function parseQuestion(question, bank, context) {
  const t = question.trim().replace(/\s+/g, "");
  const clarify = message => ({intent: "澄清", question, message});
  if (!t) return clarify("请输入业务问题，或从问法示例选择一项。");
  const knownBranches = Object.values(bank.branches).filter(branch => t.includes(branch.name));
  const knownGroups = unique(Object.values(bank.branches).map(branch => branch.group)).filter(group => t.includes(group));
  const channels = Object.entries(ROUTES).filter(([key, aliases]) => has(bank.metadata.channels, key) && aliases.some(alias => t.includes(alias))).map(([key]) => key);
  const namedStrategies = Object.values(bank.strategies).filter(s => t.includes(s.id) || t.includes(s.name));
  const activity = bank.metadata.activities.find(a => t.includes(a.id) || t.includes(a.name) && /活动|报告|复盘/.test(t));
  const subbranch = unique(bank.records.map(row => row.subbranch)).find(name => t.includes(name));
  const dates = requestedDates(t, context);
  const scope = {...context, periods: null, channels: null, cutoff: "", reference: "previous", basePeriod: "", compareBranch: ""};
  const explicitAllBranches = /各分行|哪些分行|分行有哪些|分行及|异常分行|按分行|全组|全行|各机构|分行间|排名/.test(t);
  const arbitraryBranch = t.match(/(?:生成|查看|查询|统计|复盘|核对)(?:20\d{2}年\d{1,2}月)?([\p{Script=Han}]{2,4})分行/u)?.[1];
  if (!knownBranches.length && !explicitAllBranches && !knownGroups.length && arbitraryBranch) return clarify(`机构「${arbitraryBranch}分行」未登记，请在筛选器选择机构。`);
  if (t.includes("XXX") || t.includes("策略ID或名称") || /策略[：:]\s*$/.test(t)) return clarify("请填写策略编号或名称，例如 S-101 预约回拨。");
  if (explicitAllBranches || knownGroups.length || knownBranches.length > 1 || /整体|全渠道/.test(t)) scope.branch = ALL;
  else if (knownBranches.length) scope.branch = knownBranches[0].id;
  if (knownGroups.length) scope.group = knownGroups[0];
  else if (knownBranches.length || explicitAllBranches) scope.group = ALL;
  if (subbranch) scope.subbranch = subbranch;
  if (knownBranches.length || knownGroups.length || explicitAllBranches || dates.length || /各渠道|全渠道/.test(t)) scope.channel = ALL;
  if (channels.length === 1) scope.channel = channels[0];
  else if (channels.length > 1) {
    scope.channel = ALL;
    scope.channels = channels;
  }
  if (namedStrategies.length === 1) scope.strategy = namedStrategies[0].id;
  if (activity) scope.activity = activity.id;
  if (/总行下发|全行策略/.test(t)) scope.origin = "hq";
  if (/分行自主|分行策略类别/.test(t)) scope.origin = "branch";
  const segment = ["大众", "富裕", "贵宾", "私行", "个贷"].find(name => t.includes(`${name}客群`) || t.includes(`${name}客户`));
  if (segment) scope.segment = segment;
  if (/标签口径|月末标签/.test(t)) scope.segmentBasis = "tag";
  if (dates.length) scope.period = dates.at(-1);
  if (dates.length > 1) {
    scope.reference = "custom";
    scope.basePeriod = dates.at(-2);
  }
  if (/近两个月|近2个月/.test(t)) {
    scope.reference = "custom";
    scope.basePeriod = shiftMonth(scope.period, -1);
  }
  if (/本年度|今年|全年/.test(t)) {
    scope.periods = bank.metadata.periods.filter(p => p.slice(0, 4) === scope.period.slice(0, 4) && p <= scope.period);
  }
  if (/同比|去年同期/.test(t)) scope.reference = "yoy";
  if (/同组均值|组内|高于均值|低于均值|分行间|排名靠后/.test(t)) scope.reference = "peer";
  if (/全行均值/.test(t)) scope.reference = "bank";
  if (/目标值|目标差距/.test(t)) scope.reference = "target";
  const keys = findMetrics(t);
  if (/漏斗转化率|漏斗.*断点/.test(t)) keys.push(...FUNNEL_RATES);
  if (/所有产能指标|产能诊断/.test(t)) keys.push(...PRODUCTS);
  if (/效能对比|执行效率/.test(t) && !keys.length) keys.push("execution", "reach", "effectiveRate", "aum");
  const needsGlossary = /口径|分母|怎么算|定义是什么/.test(t);
  const needsReport = /复盘|报告/.test(t) && !needsGlossary;
  const needsCause = /归因|原因|解释|拖累|为什么|影响因素|贡献最大|导致/.test(t);
  const needsScan = /异常|断点|正常范围/.test(t);
  let intent = needsGlossary ? "口径" : needsReport ? "报告" : needsCause ? "归因" : needsScan ? "异常" : "数值";
  if (!needsReport && !needsGlossary && needsCause && (/并分析|同时归因|如果异常|异常值|偏离是否异常/.test(t))) intent = "组合";
  if (intent === "数值" && !keys.length) return clarify("请确认要看的指标，例如已接触客户数、触达率、有效触达客户数或有效触达率。");
  if (intent === "口径" && !keys.length) return clarify("请给出指标名称，例如有效触达率。");
  if ((intent === "归因" || intent === "组合") && !keys.length) return clarify("请给出需要拆解的指标，例如有效触达客户数或 AUM余额增量。");
  if ((intent === "归因" || intent === "组合") && knownBranches.length >= 2) {
    scope.branch = knownBranches[0].id;
    scope.reference = "branch";
    scope.compareBranch = knownBranches[1].id;
  }
  const contributionByBranch = intent === "组合" && /贡献度偏低/.test(t);
  if (contributionByBranch) {
    scope.branch = ALL;
    scope.reference = "peer";
  }
  const groupBy = explicitAllBranches || contributionByBranch || knownBranches.length > 1 && intent === "数值" ? "branch" : channels.length > 1 || /各渠道/.test(t) ? "channel" : "";
  const dimension = /存款类型/.test(t) ? "depositType" : /客层|客群|客户类型/.test(t) ? "segment" : /支行/.test(t) ? "subbranch" : /策略来源|总分行/.test(t) ? "origin" : /渠道/.test(t) && !channels.length ? "channel" : "";
  const filter = t.match(/(超过|大于|低于|少于|不低于|至少)(\d+(?:\.\d+)?)(%|万|亿)?/);
  const condition = filter ? {
    op: {"超过": ">", "大于": ">", "低于": "<", "少于": "<", "不低于": ">=", "至少": ">="}[filter[1]],
    value: Number(filter[2]) * ({"%": 0.01, 万: 10000, 亿: 100000000}[filter[3]] || 1),
    text: filter[0],
  } : null;
  const claims = [...t.matchAll(/(\d+(?:\.\d+)?)(%|亿)/g)].map(m => m[0]).filter(c => !condition?.text.endsWith(c));
  const focusBranch = intent === "组合" && knownBranches[0] ? knownBranches[0].id : null;
  const direction = /下降|下滑|偏低|跑输/.test(t) && !/上升或下降/.test(t) ? "down" : /异常上升/.test(t) ? "up" : "both";
  return {intent, question, keys: unique(keys.length ? keys : MAIN_METRICS), scope, groupBy, dimension, condition, direction,
    branches: knownBranches.map(branch => branch.id), channels, claims, focusBranch, conditionalCause: /如果异常/.test(t),
    sort: /从高到低|排名|贡献最大/.test(t), reportType: /产能诊断/.test(t) ? "产能诊断报告" : /专项|专题|效能对比/.test(t) ? "专题分析报告" : "策略复盘报告"};
}

function queryScopes(bank, query) {
  const {scope, groupBy} = query;
  if (groupBy === "branch") {
    const branches = Object.values(bank.branches).filter(branch => (scope.group === ALL || branch.group === scope.group) && (!query.branches.length || /各分行|排名|贡献度偏低/.test(query.question) || query.branches.includes(branch.id)));
    return branches.map(branch => ({label: `${branch.name}分行`, scope: {...scope, branch: branch.id}}));
  }
  if (groupBy === "channel") {
    const channels = Object.entries(bank.metadata.channels).filter(([key]) => !query.channels.length || query.channels.includes(key));
    return channels.map(([key, name]) => ({label: name, scope: {...scope, channel: key}}));
  }
  return [{label: scopeLabel(bank, scope), scope}];
}

function meetsCondition(value, condition) {
  if (!finite(value)) return false;
  switch (condition.op) {
    case ">": return value > condition.value;
    case "<": return value < condition.value;
    case ">=": return value >= condition.value;
    default: return false;
  }
}

function diagnose(bank, result, metric, explicitDimension = "") {
  const dim = explicitDimension || (metric === "deposit" ? "depositType" : SALES.includes(metric) || metric === "wealth" || metric === "fund" ? "segment" : "channel");
  const countsFromRate = METRICS[metric].fraction?.[0];
  const processMetric = ["sent", "success", "executed", "contacted", "effective"].includes(metric) || ["sent", "success", "executed", "contacted", "effective"].includes(countsFromRate);
  const funnel = !explicitDimension && processMetric && !result.spec.peers && !result.spec.target ?
    funnelDecomposition(result.comparableCurrent, result.base) : null;
  const split = dimensionSplit(bank, result, metric, dim);
  return {metric, dim, funnel, ...split};
}

function runQuestion(question, bank, context, threshold) {
  const query = parseQuestion(question, bank, context);
  if (query.intent === "澄清") return query;
  const rows = queryScopes(bank, query).map(item => ({...item, analysis: analyze(bank, item.scope)}));
  const ranking = rows.filter(row => !query.condition || meetsCondition(row.analysis.current?.[query.keys[0]], query.condition));
  if (query.sort) ranking.sort((a, b) => (b.analysis.current?.[query.keys[0]] ?? -Infinity) - (a.analysis.current?.[query.keys[0]] ?? -Infinity));
  const compareRows = ["异常", "组合"].includes(query.intent) ? ranking.flatMap(row =>
    scanAnomalies(bank, row.scope, threshold, query.keys, "all", query.direction).map(alert => ({...alert, scopeName: row.label}))
  ) : [];
  const focus = query.focusBranch ? rows.find(row => row.scope.branch === query.focusBranch) || rows[0] : rows[0];
  const cause = ["归因", "组合"].includes(query.intent) && focus && (!query.conditionalCause || compareRows.length)
    ? diagnose(bank, focus.analysis, query.keys[0], query.dimension) : null;
  return {...query, rows, ranking, compareRows, focus, cause};
}

function reviseSnapshot(bank) {
  if (bank.snapshot.endsWith("-R1")) return null;
  const scope = scopeFor(bank);
  const selected = scopeRows(bank, scope)[0];
  if (!selected) return null;
  const records = bank.records.map(row => row.id !== selected.id || !finite(row.aum) ? row : {
    ...row, aum: row.aum + 125000, batch: "LATE-" + row.batch,
    evidence: row.evidence + " / 补数批次 LATE-01",
  });
  return {...bank, snapshot: bank.snapshot + "-R1", records};
}

const PLAYBOOK = {
  participation: {name: "参与度不足", action: "核对未部署支行与适用客户清单，确认后安排覆盖补位", owner: "分行运营"},
  leakage: {name: "漏斗漏损", action: "调取接触环节的排队与拨打日志，复跑预约优先级案例", owner: "渠道运营"},
  channel: {name: "渠道拖累", action: "核对渠道容量和触达失败记录，试算渠道分配调整", owner: "渠道运营"},
  mix: {name: "客群结构变化", action: "按部署客群和月末标签分别重算，确认口径后复核构成", owner: "指标负责人"},
  result: {name: "策略效果差", action: "复核客群、策略及观察窗，确定需验证的策略调整", owner: "策略负责人"},
};

function actionFor(metric) {
  if (["cover", "eligible", "strategies", "deployed"].includes(metric)) return "participation";
  if (PRODUCTS.includes(metric)) return "result";
  return "leakage";
}

function periodText(scope) {
  return scope.periods?.length > 1 ? `${scope.periods[0]} 至 ${scope.periods.at(-1)}（${scope.periods.length} 个已选月份）` : monthName(scope.period);
}

function evidenceIndex(bank, rows) {
  return {bank: bank.name, snapshot: bank.snapshot, mapping: bank.mapping.version,
    rows: rows.length, cutoff: unique(rows.map(row => row.cutoff)).sort().join("、"),
    definitions: unique(rows.map(row => row.definition)).sort().join("、"),
    batches: unique(rows.map(row => row.batch)).sort().join("、")};
}

function dataRequest(bank, scope, result) {
  const base = result.spec.label;
  const title = scopeLabel(bank, scope);
  const gap = scope.activity !== ALL && !activityById(bank, scope.activity)?.strategies?.length ? "活动与策略关联待补" : "核对统计期、采集范围与指标口径";
  return [
    "# 策略复盘取数清单",
    `范围 ${title}｜本期 ${periodText(scope)}｜基准 ${base}`,
    gap,
    "| 所需数据 | 粒度与字段 | 建议来源 |",
    "|---|---|---|",
    "| 参与度与五层漏斗 | 分行、支行、渠道、策略、周期、去重范围、分子分母 | 策略看板与渠道执行导出 |",
    "| 产能与销量 | 分行、策略来源、金额单位、归属窗口、AUM 及余额和销量细项 | 产能看板或分行视角导出 |",
    "| 口径与关联 | 指标字典、渠道覆盖、数据截止、策略与活动的绑定及有效期 | 指标负责人、活动平台导出 |",
    "| 规则复跑 | 原规则版本、事件与初始状态、实际判定、回传或预发结果 | 渠道执行日志及活动平台 |",
    ...result.notes.map(note => `- ${note}`),
  ].join("\n");
}

function reportModel(bank, scope, thresholds, actions = [], type = "策略复盘报告", requested = null) {
  const a = analyze(bank, scope);
  const title = `${scopeLabel(bank, scope)} · ${type}`;
  const eligible = a.status === "full" && a.current && a.base && !a.spec.target && PRODUCTS.every(key => finite(a.current[key]));
  const evidence = evidenceIndex(bank, a.rows);
  const requests = dataRequest(bank, scope, a);
  if (!a.current || a.status === "missing") return {status: "待补数据", title, analysis: a, evidence, requests, text: requests, canSign: false};
  const compare = a.comparableCurrent;
  const base = a.base;
  const yo = analyze(bank, {...scope, reference: "yoy"});
  const peer = analyze(bank, {...scope, reference: "peer"});
  const alerts = scanAnomalies(bank, scope, thresholds);
  const low = FUNNEL_RATES.filter(key => finite(a.current[key])).sort((x, y) => a.current[x] - a.current[y])[0];
  const participation = ["deployed", "strategies", "eligible", "success", "cover", "effectiveRate"];
  const show = (key, item) => metricValue(key, item?.[key]);
  const deltaText = key => deltaValue(key, delta(compare?.[key], base?.[key]));
  const pctText = key => finite(base?.[key]) && base[key] > 0 && finite(compare?.[key]) ? pct((compare[key] - base[key]) / base[key]) : "—";
  const percentTable = keys => [
    "| 指标 | 本期 | 比较基准 | 可比差值 | 相对变化 |",
    "|---|---:|---:|---:|---:|",
    ...keys.map(key => `| ${METRICS[key].name} | ${show(key, a.current)} | ${show(key, base)} | ${deltaText(key)} | ${pctText(key)} |`),
  ];
  const focusKeys = ["effective", low || "execution", "aum"];
  const insights = focusKeys.map((key, i) => {
    const desc = i === 0 ? "核对漏斗的量与转化变化" : i === 1 ? "该项为本期最低可算的层间转化率" : "产能采用当前快照的时间窗归属";
    return `- ${METRICS[key].name} ${show(key, a.current)}，可比差值 ${deltaText(key)}（${pctText(key)}）。${desc}。`;
  });
  const breakdown = funnelDecomposition(compare, base);
  const majorAlerts = unique(alerts.map(alert => alert.key)).slice(0, 6);
  const diagnostics = majorAlerts.map(key => {
    const diag = diagnose(bank, a, key);
    const top = diag.rows[0];
    const issue = alerts.find(alert => alert.key === key);
    const note = top ? `${top.name}可比拆解 ${deltaValue(key, top.effect)}` : "可用维度证据待补";
    return `- ${scopeLabel(bank, scope)} · ${METRICS[key].name}。${issue.label}（阈值 ${issue.threshold}，基准 ${issue.baseline}），${note}，影响 ${issue.impact}。业务机制待验证。`;
  });
  const groups = unique(Object.values(bank.branches).map(branch => branch.group));
  const groupRows = [{name: "全行", group: ALL}, ...groups.map(group => ({name: group, group}))].map(item => {
    const result = analyze(bank, {...scope, branch: ALL, subbranch: ALL, group: item.group, reference: "previous"});
    return `| ${item.name} | ${show("deployed", result.current)} | ${show("strategies", result.current)} | ${show("cover", result.current)} | ${deltaValue("deployed", delta(result.comparableCurrent?.deployed, result.base?.deployed))} | ${deltaValue("strategies", delta(result.comparableCurrent?.strategies, result.base?.strategies))} | ${deltaValue("cover", delta(result.comparableCurrent?.cover, result.base?.cover))} |`;
  });
  const origins = ["hq", "branch"].map(origin => {
    const result = analyze(bank, {...scope, origin});
    return `| ${origin === "hq" ? "总行下发" : "分行自主"} | ${show("aum", result.current)} | ${deltaValue("aum", delta(result.comparableCurrent?.aum, result.base?.aum))} |`;
  });
  const actionList = actions.length ? actions : [
    {...PLAYBOOK.leakage, when: "30 天", evidence: "按同口径重算五层漏斗并核对预演结果"},
    {...PLAYBOOK.result, when: "90 天", evidence: "取得同口径观察期与实际执行证据"},
  ];
  const safeCell = text => String(text ?? "").replace(/[\r\n|]+/g, " ");
  const lines = [
    `# ${title}`, "", `本期 ${periodText(scope)} · 基准 ${a.spec.label} · ${evidence.bank} · 快照 ${evidence.snapshot}`,
    a.status === "partial" ? "本报告按可比子集计算差值，表中本期值展示已导入范围。待补范围见附录。" : "本报告使用可比的导入快照。范围与口径见附录。",
    "", "## 一、执行摘要", "", ...insights, "",
    "| 异常对象／指标 | 阈值 | 影响 | 主要解释 |", "|---|---|---|---|",
    ...(alerts.length ? alerts.slice(0, 10).map(alert => `| ${METRICS[alert.key].name} · ${alert.label} | ${alert.threshold} | ${alert.impact} | 基准 ${alert.baseline}，业务机制待核 |`) : ["| 当前可比较范围 | 当前阈值配置 | — | 未触发规则，缺数或不可比范围见附录 |"]),
    "", "## 二、分行策略参与度", "", ...percentTable(participation), "",
    `同组覆盖率 ${show("cover", peer.base)}，同比基准 ${yo.spec.label}，同比有效触达基准 ${show("effective", yo.base)}（${yo.status === "full" ? "可比" : "有覆盖缺口"}）。`,
    "", "| 机构范围 | 部署分行 | 策略数 | 覆盖率 | 部署分行月增 | 策略数月增 | 覆盖率月增 |",
    "|---|---:|---:|---:|---:|---:|---:|", ...groupRows, "",
    "## 三、分行策略执行情况（漏斗）", "",
    "| 层级 | 客户数 | 较上一层 | 基准差值 |", "|---|---:|---:|---:|",
    ...STAGES.map(([key, name], index) => `| ${name} | ${show(key, a.current)} | ${index ? show(FUNNEL_RATES[index - 1], a.current) : "—"} | ${deltaText(key)} |`),
    "", `最低可算层间转化 ${low ? METRICS[low].name + " " + show(low, a.current) : "待补"}。有效触达率以成功下发客户数为分母。`,
    "", "## 四、分行策略执行效果", "", ...percentTable(PRODUCTS), "",
    "| 策略来源 | AUM余额增量 | 可比差值 |", "|---|---:|---:|", ...origins, "",
    "## 五、异常归因", "",
    ...(diagnostics.length ? diagnostics : ["- 当前比较范围未触发异常，待补项另见附录。"]),
    ...(breakdown && alerts.some(alert => alert.key === "effective" || FUNNEL_RATES.includes(alert.key)) ? ["", `漏斗量率核对（按业务阶段固定替换顺序） ${breakdown.map(item => item.name + " " + signed(item.effect)).join("、")} 人。`] : []),
  ];
  if (requested?.ranking?.length > 1 || (requested?.keys?.length && type === "专题分析报告")) {
    lines.push("", "### 专题对照", "", "| 范围 | 指标 | 本期 | 基准 | 差值 |", "|---|---|---:|---:|---:|");
    for (const row of requested.ranking) {
      for (const key of requested.keys) lines.push(`| ${row.label} | ${METRICS[key].name} | ${show(key, row.analysis.current)} | ${show(key, row.analysis.base)} | ${deltaValue(key, delta(row.analysis.comparableCurrent?.[key], row.analysis.base?.[key]))} |`);
    }
    if (type === "专题分析报告" && requested.keys[0]) {
      const diag = diagnose(bank, a, requested.keys[0], requested.dimension);
      const top = diag.rows[0];
      lines.push("", top ? `专题拆解首项 ${top.name}，统计影响 ${deltaValue(requested.keys[0], top.effect)}。业务假设待验证。` : "专题拆解所需明细待补。");
    }
  }
  lines.push("", "## 六、行动建议", "", "| 顺序 | 动作 | 对应假设 | 预期或验证条件 | 责任方 | 时点 |", "|---|---|---|---|---|---|",
    ...actionList.map((item, i) => `| ${i + 1} | ${safeCell(item.action)} | ${safeCell(item.name)} | ${safeCell(item.evidence)} | ${safeCell(item.owner)} | ${safeCell(item.when)} |`),
    "", "## 七、附录", "",
    `- 数据来源 ${bank.metadata.sources.join("、")}。快照 ${evidence.snapshot}，接入配置 ${evidence.mapping}，本期 ${periodText(scope)}，基准 ${a.spec.label}。`,
    `- 源行 ${evidence.rows} 条，批次 ${evidence.batches}，数据截止 ${evidence.cutoff}，口径版本 ${evidence.definitions}。`,
    `- 明细复算按范围 ${scopeLabel(bank,scope)} 筛选。源行键示例 ${a.rows.slice(0,3).map(row=>row.id).join("、")}。基准源批次 ${unique(a.baselineRows.map(row=>row.batch)).join("、")||"目标或待补"}。`,
    "- 客户按统计月与集合取并集，跨月为客户月次。活动与客群采用本次选定的范围及口径。",
    "- AUM余额增量与产品销量分别计量。时间窗归属和变化拆解是统计证据，策略增量待实验或后续验证。",
    ...a.notes.map(note => `- 待核 ${note}`));
  const missingFields = PRODUCTS.filter(key => !finite(a.current[key]));
  if (missingFields.length) lines.push(`- 缺项 ${missingFields.map(key => METRICS[key].name).join("、")}。`);
  return {status: eligible ? "待核结论" : "部分可比草稿", title, analysis: a, evidence, requests, text: lines.join("\n"), canSign: Boolean(eligible)};
}
