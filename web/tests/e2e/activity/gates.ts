/**
 * web/tests/e2e/activity/gates.ts —— ADR-003「A 段机器门禁」7 条的 Playwright 侧实现
 *
 * 出处（禁凭记忆）：
 *   docs/decisions/ADR-003-frontend-design-baseline.md「门禁采纳 · A 段机器门禁」7 条；
 *   spec/frontend-template-spdb-v1.1/checklist_交付前自检.md A 段（同一 7 条的原始清单）。
 * 其中第 7 条「行尾 + 接行首 +」是**源码文本**层面的门禁，不属浏览器可断言面，
 *   由 vitest 侧的源码扫描承担（见 tests/unit/activity/class-contract.spec.ts 的同族断言），本文件不重复实现。
 *
 * 判据纪律（PRE-29）：一律取 DOM 结构 / 解析值 / computed style，
 *   禁渲染串前缀匹配、禁裸子串、禁写死位置下标；每条门禁都配**注入式负对照**
 *   （seedGateViolation / clearGateSeeds）—— 门禁抓不到人为植入的违规就是假绿。
 */
import type { Page } from "@playwright/test";

/** 统一的违规条目形状：gate = 门禁编号与名称，where = 结构性定位，detail = 可核对事实。 */
export interface Violation {
  readonly gate: string;
  readonly where: string;
  readonly detail: string;
  /** 仅 G6 使用：未定义的 class 名（用于与已登记的冻结面缺口清单比对）。 */
  readonly token?: string | undefined;
}

/**
 * 已知冻结面缺口（G6）—— 禁就地修，须走 CR。
 *
 * 实测（本文件首次把 ADR-003 第 6 条门禁真正跑起来后发现）：`web/src/components/AppBar.vue`
 * 的模板用了两个 class，但全仓（含 tokens.css / element-theme.css / project.css 与各件 scoped 块）
 * 都没有它们的样式定义：
 *   cl-appbar__actor  —— AppBar.vue:16 使用（「操作者 …」）；
 *   cl-appbar__recent —— AppBar.vue:17 使用（「最近工作区 …」）。
 * AppBar.vue 属 M0-03 冻结的 13 件公共件（改动必须走 CR），本分支不得自行修正。
 *
 * 处置：登记于 .orch_tmp/FE-TO-DAG-REQUESTS.md 请求 [4]（CR 批次）与 web/docs/FE-UI-02-activity-list.md
 * 「诚实偏差」；本清单是**穷举白名单**：第三条未定义 class 仍会判红，
 * 且 classGapDrift() 会在「白名单条目已不再违规」时同样报错（防止白名单变成永久豁免区）。
 */
export const KNOWN_FROZEN_CLASS_GAPS: readonly string[] = ["cl-appbar__actor", "cl-appbar__recent"];

export interface ConsoleRecorder {
  readonly errors: string[];
  readonly warnings: string[];
  readonly pageErrors: string[];
}

/** 门禁 1 的采集器：console.error 与 pageerror 一律记原文（warnings 只报告不判红）。 */
export function watchConsole(page: Page): ConsoleRecorder {
  const errors: string[] = [];
  const warnings: string[] = [];
  const pageErrors: string[] = [];
  page.on("console", (message) => {
    const text = message.type() + " | " + message.text();
    if (message.type() === "error") errors.push(text);
    else if (message.type() === "warning") warnings.push(text);
  });
  page.on("pageerror", (error) => {
    pageErrors.push(error.name + " | " + error.message);
  });
  return { errors, warnings, pageErrors };
}

/** 门禁 2：页面文本与属性（含 SVG）禁 NaN / undefined / [object Object] / Infinity。 */
export async function scanForbiddenTokens(page: Page): Promise<readonly Violation[]> {
  return page.evaluate<readonly Violation[]>(() => {
    const out: Violation[] = [];
    // 词边界：避免把 predefined / infinite 之类的合法词误判（判据要能过负对照，也要过正对照）。
    const pattern = /(^|[^A-Za-z0-9_$])(NaN|undefined|\[object Object\]|Infinity)(?![A-Za-z0-9_$])/;
    const skip = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"]);
    const describe = (el: Element): string => {
      const parts: string[] = [el.tagName.toLowerCase()];
      if (el.id.length > 0) parts.push("#" + el.id);
      const marker =
        el.getAttribute("data-part") ??
        el.getAttribute("data-state") ??
        el.getAttribute("data-field") ??
        el.getAttribute("data-action") ??
        el.getAttribute("data-status");
      if (marker !== null) parts.push("[data=" + marker + "]");
      const label = el.getAttribute("aria-label");
      if (label !== null) parts.push("[aria-label=" + label + "]");
      const cls = el.getAttribute("class");
      if (cls !== null && cls.trim().length > 0) parts.push("." + cls.trim().split(/\s+/)[0]);
      return parts.join("");
    };
    const report = (el: Element, where: string, text: string): void => {
      const hit = pattern.exec(text);
      if (hit === null) return;
      out.push({ gate: "G2-forbidden-token", where: describe(el) + " > " + where, detail: "命中 " + hit[2] });
    };
    for (const el of Array.from(document.querySelectorAll("*"))) {
      if (skip.has(el.tagName)) continue;
      // 只取本元素直属文本节点，避免父元素 textContent 把同一处违规重复计数。
      for (const node of Array.from(el.childNodes)) {
        if (node.nodeType === Node.TEXT_NODE) report(el, "text", node.nodeValue ?? "");
      }
      for (const attr of Array.from(el.attributes)) report(el, "@" + attr.name, attr.value);
    }
    return out;
  });
}

/** 门禁 4：无横向溢出 —— 文档不得横向滚动；未被任何滚动/裁剪祖先收容的元素不得超出视口右界。 */
export async function scanHorizontalOverflow(page: Page): Promise<readonly Violation[]> {
  return page.evaluate<readonly Violation[]>(() => {
    const out: Violation[] = [];
    const doc = document.documentElement;
    const viewport = window.innerWidth;
    if (doc.scrollWidth > viewport + 1) {
      out.push({
        gate: "G4-no-horizontal-overflow",
        where: "html",
        detail: "scrollWidth " + doc.scrollWidth + " > innerWidth " + viewport,
      });
    }
    const clips = (el: Element): boolean => {
      const value = getComputedStyle(el).overflowX;
      return value === "auto" || value === "scroll" || value === "hidden" || value === "clip";
    };
    const describe = (el: Element): string => {
      const cls = el.getAttribute("class");
      const marker = el.getAttribute("data-part") ?? el.getAttribute("data-state");
      return (
        el.tagName.toLowerCase() +
        (el.id.length > 0 ? "#" + el.id : "") +
        (marker !== null ? "[data=" + marker + "]" : "") +
        (cls !== null && cls.trim().length > 0 ? "." + cls.trim().split(/\s+/)[0] : "")
      );
    };
    for (const el of Array.from(document.body.querySelectorAll("*"))) {
      const rect = el.getBoundingClientRect();
      // 未渲染（0×0）的元素不参与右界判定，但会被门禁 5 单独检查（图表容器）。
      if (rect.width === 0 && rect.height === 0) continue;
      let container: Element | null = el.parentElement;
      while (container !== null && !clips(container)) container = container.parentElement;
      // 有滚动/裁剪祖先 ⇒ 溢出被该容器收容（AC-032「表头和表格滚动正常」即依赖此机制），不判违规。
      if (container !== null) continue;
      if (rect.right > viewport + 1) {
        out.push({
          gate: "G4-no-horizontal-overflow",
          where: describe(el),
          detail: "right " + Math.round(rect.right) + " > viewport " + viewport + "（无滚动祖先收容）",
        });
      }
    }
    // 正向断言：任何内容溢出的元素都必须自身可横向滚动/裁剪，否则溢出会外泄到页面。
    for (const el of Array.from(document.body.querySelectorAll("*"))) {
      if (el.scrollWidth <= el.clientWidth + 1) continue;
      const value = getComputedStyle(el).overflowX;
      if (value === "visible") {
        out.push({
          gate: "G4-no-horizontal-overflow",
          where: describe(el),
          detail: "scrollWidth " + el.scrollWidth + " > clientWidth " + el.clientWidth + " 且 overflow-x=visible",
        });
      }
    }
    return out;
  });
}

/** 门禁 3：标签配对（开合数量相等）＋ 表格/列表/定义列表的父子嵌套不变量（结构性，非仅计数）。 */
export async function scanTagPairing(page: Page): Promise<readonly Violation[]> {
  return page.evaluate<readonly Violation[]>(() => {
    const out: Violation[] = [];
    const html = document.documentElement.outerHTML;
    const tags = ["div", "span", "table", "thead", "tbody", "tr", "td", "th", "section", "ul", "li", "dl", "dt", "dd", "button", "a", "p"];
    for (const tag of tags) {
      const open = (html.match(new RegExp("<" + tag + "(?=[\\s>/])", "g")) ?? []).length;
      const close = (html.match(new RegExp("</" + tag + "(?=[\\s>/])", "g")) ?? []).length;
      // 自闭合写法（<td />）在 HTML 里不成立，故 void 元素不在本表内；开合数必须逐一相等。
      if (open !== close) {
        out.push({ gate: "G3-tag-pairing", where: tag, detail: "开 " + open + " ≠ 合 " + close });
      }
    }
    const requireParent = (selector: string, allowed: readonly string[], label: string): void => {
      for (const el of Array.from(document.querySelectorAll(selector))) {
        const parent = el.parentElement;
        const name = parent === null ? "(none)" : parent.tagName.toLowerCase();
        if (!allowed.includes(name)) {
          out.push({ gate: "G3-tag-pairing", where: label, detail: el.tagName.toLowerCase() + " 的父元素是 " + name });
        }
      }
    };
    requireParent("td", ["tr"], "嵌套: td");
    requireParent("th", ["tr"], "嵌套: th");
    requireParent("tr", ["thead", "tbody", "tfoot", "table"], "嵌套: tr");
    requireParent("li", ["ul", "ol", "menu"], "嵌套: li");
    requireParent("dt", ["dl", "div"], "嵌套: dt");
    requireParent("dd", ["dl", "div"], "嵌套: dd");
    requireParent("caption", ["table"], "嵌套: caption");
    requireParent("thead", ["table"], "嵌套: thead");
    requireParent("tbody", ["table"], "嵌套: tbody");
    return out;
  });
}

export interface ChartScan {
  readonly checked: number;
  readonly violations: readonly Violation[];
}

/** 门禁 5：无 0 宽/0 高图表容器。UI-02 无图表 ⇒ checked=0，如实报 N/A（禁把空集当通过）。 */
export async function scanChartContainers(page: Page): Promise<ChartScan> {
  return page.evaluate<ChartScan>(() => {
    const selector = 'canvas, svg, [_echarts_instance_], [data-part="chart"], [data-chart]';
    const nodes = Array.from(document.querySelectorAll(selector));
    const violations: Violation[] = [];
    for (const el of nodes) {
      const rect = el.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) continue;
      const cls = el.getAttribute("class");
      violations.push({
        gate: "G5-chart-box",
        where: el.tagName.toLowerCase() + (cls !== null && cls.trim().length > 0 ? "." + cls.trim().split(/\s+/)[0] : ""),
        detail: "宽 " + rect.width + " × 高 " + rect.height,
      });
    }
    return { checked: nodes.length, violations };
  });
}

export interface ClassScan {
  readonly used: number;
  readonly defined: number;
  readonly unreadableSheets: number;
  readonly violations: readonly Violation[];
}

/** 门禁 6：用到的每个 class 都能在样式源里找到定义（ADR-003 对应 _check_used.py 的 UNDEFINED=[]）。 */
export async function scanClassDefinitions(page: Page): Promise<ClassScan> {
  return page.evaluate<ClassScan>(() => {
    const used = new Map<string, string>();
    for (const el of Array.from(document.querySelectorAll("*"))) {
      const cls = el.getAttribute("class");
      if (cls === null) continue;
      for (const token of cls.split(/\s+/)) {
        if (token.length === 0) continue;
        if (!used.has(token)) {
          const marker = el.getAttribute("data-part") ?? el.getAttribute("data-state");
          used.set(token, el.tagName.toLowerCase() + (marker !== null ? "[data=" + marker + "]" : ""));
        }
      }
    }
    const defined = new Set<string>();
    let unreadableSheets = 0;
    const tokenPattern = /\.(-?[_a-zA-Z][\w-]*)/g;
    const walk = (rules: CSSRuleList): void => {
      for (const rule of Array.from(rules)) {
        const style = rule as CSSStyleRule;
        if (typeof style.selectorText === "string") {
          for (const match of style.selectorText.matchAll(tokenPattern)) {
            const name = match[1];
            if (name !== undefined) defined.add(name);
          }
          continue;
        }
        const group = rule as CSSGroupingRule;
        if (group.cssRules !== undefined) walk(group.cssRules);
      }
    };
    const sheets: CSSStyleSheet[] = Array.from(document.styleSheets);
    for (const sheet of Array.from(document.adoptedStyleSheets ?? [])) sheets.push(sheet);
    for (const sheet of sheets) {
      try {
        walk(sheet.cssRules);
      } catch {
        unreadableSheets += 1;
      }
    }
    const violations: Violation[] = [];
    for (const [token, where] of used) {
      if (defined.has(token)) continue;
      violations.push({
        gate: "G6-class-defined",
        where,
        detail: "class ." + token + " 无样式定义",
        token,
      });
    }
    violations.sort((a, b) => a.detail.localeCompare(b.detail));
    return { used: used.size, defined: defined.size, unreadableSheets, violations };
  });
}

/**
 * 浏览器对 HTTP >= 400 的资源加载会**自动**打一条 console 错误（网络层噪声，非应用日志）。
 * 失败/冲突分支的用例必然伴随这类消息，故门禁 1 把它们与应用侧 console.error 分开统计：
 *   应用侧一律必须为 0；网络噪声则必须与用例**故意触发**的状态码集合双向对上
 *   （出现未预期状态码 ⇒ 判红；预期状态码没出现 ⇒ 也判红，证明错误分支根本没走到）。
 */
const HTTP_NOISE = /^error \| Failed to load resource: the server responded with a status of (\d{3}) /;

export interface GateReport {
  readonly label: string;
  /** 应用侧 console.error（已排除浏览器的 HTTP 状态码噪声）。 */
  readonly consoleErrors: readonly string[];
  readonly consoleWarnings: readonly string[];
  readonly pageErrors: readonly string[];
  /** 实测到的 HTTP 噪声状态码（含重复，已排序）。 */
  readonly httpNoiseStatuses: readonly number[];
  readonly expectedHttpStatuses: readonly number[];
  /** 未预期的噪声状态码（去重）。 */
  readonly unexpectedHttpStatuses: readonly number[];
  /** 预期触发但未出现的状态码。 */
  readonly missingHttpStatuses: readonly number[];
  readonly forbiddenTokens: readonly Violation[];
  readonly overflow: readonly Violation[];
  readonly tags: readonly Violation[];
  readonly charts: ChartScan;
  readonly classes: ClassScan;
}

/** 一次跑完 6 条浏览器侧门禁，返回结构化报告（判红由 gateFailures 统一出串，便于一次断言看全貌）。 */
export async function runMachineGates(
  page: Page,
  recorder: ConsoleRecorder,
  label: string,
  expectedHttpStatuses: readonly number[] = [],
): Promise<GateReport> {
  const [forbiddenTokens, overflow, tags, charts, classes] = await Promise.all([
    scanForbiddenTokens(page),
    scanHorizontalOverflow(page),
    scanTagPairing(page),
    scanChartContainers(page),
    scanClassDefinitions(page),
  ]);
  const appErrors: string[] = [];
  const noise: number[] = [];
  for (const line of recorder.errors) {
    const match = HTTP_NOISE.exec(line);
    const status = match?.[1];
    if (status === undefined) appErrors.push(line);
    else noise.push(Number(status));
  }
  noise.sort((a, b) => a - b);
  const expected = [...expectedHttpStatuses].sort((a, b) => a - b);
  return {
    label,
    consoleErrors: appErrors,
    consoleWarnings: [...recorder.warnings],
    pageErrors: [...recorder.pageErrors],
    httpNoiseStatuses: noise,
    expectedHttpStatuses: expected,
    unexpectedHttpStatuses: [...new Set(noise.filter((status) => !expected.includes(status)))],
    missingHttpStatuses: [...new Set(expected.filter((status) => !noise.includes(status)))],
    forbiddenTokens,
    overflow,
    tags,
    charts,
    classes,
  };
}

/** 把报告折成「一行一条」的失败清单；空数组 = 6 条门禁全绿（门禁 7 在源码侧另测）。 */
export function gateFailures(report: GateReport): readonly string[] {
  const lines: string[] = [];
  for (const item of report.consoleErrors) lines.push("G1-console.error | " + item);
  for (const item of report.pageErrors) lines.push("G1-pageerror | " + item);
  for (const status of report.unexpectedHttpStatuses) {
    lines.push("G1-http-noise | 未预期的 HTTP 错误响应被浏览器记录 | status=" + String(status));
  }
  for (const status of report.missingHttpStatuses) {
    lines.push("G1-http-noise | 预期触发的错误分支未出现（用例没走到） | status=" + String(status));
  }
  for (const item of report.forbiddenTokens) lines.push(item.gate + " | " + item.where + " | " + item.detail);
  for (const item of report.overflow) lines.push(item.gate + " | " + item.where + " | " + item.detail);
  for (const item of report.tags) lines.push(item.gate + " | " + item.where + " | " + item.detail);
  for (const item of report.charts.violations) lines.push(item.gate + " | " + item.where + " | " + item.detail);
  for (const item of report.classes.violations) {
    // 已登记的冻结面缺口不在本页判红（它们属 CR 批次）；但漂移由 classGapDrift 盯住。
    if (item.token !== undefined && KNOWN_FROZEN_CLASS_GAPS.includes(item.token)) continue;
    lines.push(item.gate + " | " + item.where + " | " + item.detail);
  }
  return lines;
}

/**
 * 白名单双向校验：既报「新增未定义 class」（需修或需新登记），
 * 也报「白名单里的条目已不再违规」（需删登记）—— 两者都说明台账与实测不一致。
 */
export function classGapDrift(scan: ClassScan): readonly string[] {
  const found = scan.violations.map((item) => item.token ?? "");
  const drift: string[] = [];
  for (const token of found) {
    if (token.length > 0 && !KNOWN_FROZEN_CLASS_GAPS.includes(token)) drift.push("新增未定义 class: " + token);
  }
  for (const token of KNOWN_FROZEN_CLASS_GAPS) {
    if (!found.includes(token)) drift.push("白名单条目已不再违规（应删登记）: " + token);
  }
  return drift;
}

/** 报告摘要（写进证据文档用；不含判定，只含可核对读数）。 */
export function gateSummary(report: GateReport): string {
  return JSON.stringify({
    label: report.label,
    consoleErrors: report.consoleErrors.length,
    consoleWarnings: report.consoleWarnings.length,
    pageErrors: report.pageErrors.length,
    httpNoise: report.httpNoiseStatuses,
    expectedHttpStatuses: report.expectedHttpStatuses,
    forbiddenTokens: report.forbiddenTokens.length,
    overflow: report.overflow.length,
    tagPairing: report.tags.length,
    chartContainers: report.charts.checked,
    chartViolations: report.charts.violations.length,
    classesUsed: report.classes.used,
    classesDefined: report.classes.defined,
    classesUndefined: report.classes.violations.length,
    unreadableSheets: report.classes.unreadableSheets,
  });
}

export type GateSeed = "forbidden-token" | "overflow" | "nesting" | "undefined-class" | "zero-size-chart";

/**
 * 负对照植入：在页面上造一处**确定违规**的 DOM，用于证明对应门禁真的会红。
 * 植入体一律带 data-gate-seed 标记，由 clearGateSeeds 摘除（不污染后续断言与截图）。
 */
export async function seedGateViolation(page: Page, seed: GateSeed): Promise<void> {
  await page.evaluate((kind: GateSeed) => {
    const host = document.createElement("div");
    host.setAttribute("data-gate-seed", kind);
    if (kind === "forbidden-token") host.textContent = "种子：本行故意出现 undefined 字样";
    if (kind === "overflow") host.setAttribute("style", "width:6000px;height:8px;background:transparent");
    if (kind === "undefined-class") host.setAttribute("class", "cl-seed-class-with-no-definition");
    if (kind === "zero-size-chart") {
      const canvas = document.createElement("canvas");
      canvas.setAttribute("style", "width:0;height:0");
      host.appendChild(canvas);
    }
    if (kind === "nesting") {
      // 用 DOM API 造出解析器不会产生的错嵌套（td 直接挂在 div 下），验证嵌套不变量真的在跑。
      const cell = document.createElement("td");
      cell.textContent = "seed";
      host.appendChild(cell);
    }
    document.body.appendChild(host);
  }, seed);
}

/** 摘除全部负对照植入体。 */
export async function clearGateSeeds(page: Page): Promise<void> {
  await page.evaluate(() => {
    for (const el of Array.from(document.querySelectorAll("[data-gate-seed]"))) el.remove();
  });
}