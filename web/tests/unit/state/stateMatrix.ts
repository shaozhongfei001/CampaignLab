/**
 * web/tests/unit/state/stateMatrix.ts —— 六态 × 视口矩阵工厂与可复用契约检查（M0-03b / S2）
 *
 * 出处：orchestrator/handoff/M0-03b-freeze.md §7「S2」的矩阵与断言项清单，以及 §4.2 R-4
 * 「S2 的参数化用例必须以工厂函数形式导出（六态 × 视口标签矩阵），M3-P02 注册 variant 后复用同一
 *  矩阵对自己复跑一遍」—— 故本文件把**期望表 + 渲染 + 契约检查**做成可 import 的工厂。
 * 本文件不是 spec（vitest include 为 *.spec.ts）：从 .spec 互相 import 会把对方的用例在本文件里
 * 重复注册一遍，所以共享层必须独立成模块（回报 S2-1）。
 *
 * 渲染通道：vue/server-renderer 的 renderToString。环境固定 node（web/vitest.config.ts 顶部裁定：
 * 未声明 jsdom / happy-dom / @vue/test-utils，用例不得触碰 document / window / getComputedStyle），
 * 因此这里做的是**真实 Vue 渲染 + 真实属性/文本断言**，但**不含布局与真实视口**：
 * 1024x768 这一腿用「断点不改变语义呈现」+ matchMedia mock + 源码级宽度纪律来取证，
 * 真实窄屏截图按裁定 A135 推迟到 M1-04，本卡不在 vitest 里谎称做了真实视口渲染。
 *
 * 桩数据全部内联在本目录（F-5）；不出现「按 status 过滤工作区」的任何语义（F-6）。
 */
import { createSSRApp, h } from "vue";
import type { Component } from "vue";
import { renderToString } from "vue/server-renderer";
import type { ApiError } from "@/api/http";
import { AUTHORITATIVE_PROBLEM_CODES, bucketOfCode } from "@/features/shared/problemPresentation";
import ViewState from "@/components/state/ViewState.vue";
import { copyOf } from "@/components/state/viewState";
import type { ViewStateCopy, ViewStateKind } from "@/components/state/viewState";
import type { ViewStateAction } from "@/components/state/viewState";
import type { ViewStateContext } from "@/components/state/registry";

/* ---------------------------------------------------------------- 规范原文通道（D-011 逐字校验用） */

const COMMON_UI = import.meta.glob("../../../../spec/CampaignLab-SDD-v1.0/ui/COMMON.md", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const COMMON_TEXT: string = Object.values(COMMON_UI)[0] ?? "";

/** 1 基行号取 ui/COMMON.md 磁盘原文行（行号即契约，冻结登记 §3.3 的映射表用它对齐）。 */
export function commonLine(no: number): string {
  return COMMON_TEXT.split("\n")[no - 1] ?? "";
}

/** 只留代码：剥块注释、行注释与 HTML 注释（http:// 之类的冒号前斜杠不剥）。 */
export function stripComments(text: string): string {
  return text
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}

/** 取共享状态表某一行的「行为」列原文（第二列），已去首尾空白。 */
export function commonBehavior(no: number): string {
  return (commonLine(no).split("|")[2] ?? "").trim();
}

/** state/ 六文件的磁盘原文（静态门禁用；扫描通道同 tokens-guard / breakpoint-guard）。 */
export const STATE_SOURCES = import.meta.glob("/src/components/state/**", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

/** 被 F-2 强制复用的两件（原址冻结，本卡禁改）：交叉核对固定串时读它们的磁盘原文。 */
export const REUSED_SOURCES = import.meta.glob("/src/components/*.vue", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

export function reusedSource(file: string): string {
  const hit = Object.entries(REUSED_SOURCES).find(([path]) => path.endsWith("/" + file));
  return hit?.[1] ?? "";
}

export function stateSource(file: string): string {
  const hit = Object.entries(STATE_SOURCES).find(([path]) => path.endsWith("/" + file));
  return hit?.[1] ?? "";
}

/* ---------------------------------------------------------------- 视口轴 */

export interface ViewportCase {
  readonly label: string;
  readonly width: number;
  readonly height: number;
  readonly narrow: boolean;
}

/** 桌面参考画布 1440x900（ui/COMMON.md:5）× 窄屏 1024x768（AC-032 的第二视口档）。 */
export const VIEWPORTS: readonly ViewportCase[] = [
  { label: "1440x900", width: 1440, height: 900, narrow: false },
  { label: "1024x768", width: 1024, height: 768, narrow: true },
];

/** 导航折叠阈值媒体查询（真值 --cl-bp-rail-collapse=1100px，token-mapping §3）；1024x768 命中它。 */
export const RAIL_COLLAPSE_QUERY = "(max-width: 1100px)";

/* ---------------------------------------------------------------- 期望表（抄自冻结 §1.2 / §1.3，不由被测函数推导） */

export const FROZEN_STATE_KINDS: readonly ViewStateKind[] = [
  "first-load",
  "no-record",
  "failed",
  "partial-comparable",
  "pending-fill",
  "stale-412",
];

/** §1.3「role / aria」列：错误两态 alert，其余四态 status。 */
export const EXPECTED_ROLE: Record<ViewStateKind, "alert" | "status"> = {
  "first-load": "status",
  "no-record": "status",
  failed: "alert",
  "partial-comparable": "status",
  "pending-fill": "status",
  "stale-412": "alert",
};

/** §1.3「默认动作键」列原样抄录。 */
export const EXPECTED_ACTIONS: Record<ViewStateKind, readonly ViewStateAction[]> = {
  "first-load": [],
  "no-record": ["create", "clear-filter"],
  failed: [],
  "partial-comparable": ["export"],
  "pending-fill": ["export"],
  "stale-412": ["refetch", "rerun"],
};

/** §1.3「图标」列全为「无」，且 F-D 禁把 StatusTag 的 tone 当区分手段。 */
export const FORBIDDEN_IN_STATE = ["<StatusTag", "@/components/StatusTag", "iconfont", "data-narrow", "@media"];

/* ---------------------------------------------------------------- 错误桩 */

export function errorStub(over: Partial<ApiError>): ApiError {
  return {
    kind: "transport",
    status: 0,
    code: "",
    type: "",
    title: "",
    detail: "",
    requestId: "rid-transport-0001",
    issues: [],
    ...over,
  };
}

/** 由 problemPresentation 的分桶表派生 code，测试侧同样不写 code 字面量（与被测件同一纪律）。 */
export function codeOfBucket(bucket: string): string {
  return AUTHORITATIVE_PROBLEM_CODES.find((code) => bucketOfCode(code) === bucket) ?? "";
}

const STALE_SERVER_TITLE = "候选版本已失效";
const STALE_RID = "rid-stale-412-0001";
const FAILED_RID = "rid-transport-0001";
/** AlertBanner.vue:10 的固定非 problem 标题（viewStateCopy.spec.ts 会与该件源码原文交叉核对）。 */
export const NON_PROBLEM_TITLE = "请求未完成";

/** 页面按 ui/COMMON.md:28 指明的当前筛选原文（组件不编，故由 props 给）。 */
export const NO_RECORD_FILTER_TITLE = "当前筛选：2026 年 11 月 · 全部机构 · 渠道=全部";
export const PARTIAL_MISSING = ["渠道 A 明细", "支行映射"];
export const PARTIAL_REASON = "共同子集外的记录未参与差值";
export const PENDING_MISSING = ["月末标签"];
export const PENDING_REASON = "待补录";
/** :30「原值仍显示」的载体：原值由页面经 default slot 传入，组件不持有数据（A137）。 */
export const ORIGINAL_VALUE_TEXT = "本期余额增量 -120000";
/** :32「显示新旧版本」的载体，同上经 default slot 传入；版本号是字符串原值，不做数字格式化。 */
export const REVISION_TEXT = "v3 → v4";

const STALE_CONTEXT: ViewStateContext = {
  state: "stale-412",
  routeName: "activity-detail",
  workspaceId: "ws-0001",
  reviewId: "rvw-0007",
};

/* ---------------------------------------------------------------- 六态基准夹具 */

export interface MatrixCase {
  readonly state: ViewStateKind;
  readonly viewport: ViewportCase;
  readonly props: Record<string, unknown>;
  readonly slots: Record<string, () => string> | undefined;
}

const BASE: Record<ViewStateKind, { props: Record<string, unknown>; slots?: Record<string, () => string> }> = {
  "first-load": { props: { state: "first-load" } },
  "no-record": {
    props: { state: "no-record", title: NO_RECORD_FILTER_TITLE },
  },
  failed: {
    props: { state: "failed", error: errorStub({ requestId: FAILED_RID }) },
  },
  "partial-comparable": {
    props: { state: "partial-comparable", missing: PARTIAL_MISSING, reason: PARTIAL_REASON },
    slots: { default: () => ORIGINAL_VALUE_TEXT },
  },
  "pending-fill": {
    props: { state: "pending-fill", missing: PENDING_MISSING, reason: PENDING_REASON },
    slots: { default: () => ORIGINAL_VALUE_TEXT },
  },
  "stale-412": {
    props: {
      state: "stale-412",
      error: errorStub({
        kind: "problem",
        status: 412,
        code: codeOfBucket("CONFLICT"),
        type: "urn:campaignlab:problem:stub",
        title: STALE_SERVER_TITLE,
        detail: "候选已失效",
        requestId: STALE_RID,
      }),
      showPrevious: true,
      keepInput: true,
      context: STALE_CONTEXT,
    },
    slots: { default: () => REVISION_TEXT },
  },
};

/** R-4 工厂：六态 × 视口标签矩阵（长度不写死，由冻结枚举与 VIEWPORTS 相乘得出）。 */
export function sixStateMatrix(): MatrixCase[] {
  const out: MatrixCase[] = [];
  for (const viewport of VIEWPORTS) {
    for (const state of FROZEN_STATE_KINDS) {
      const base = BASE[state];
      out.push({ state, viewport, props: base.props, slots: base.slots });
    }
  }
  return out;
}

/* ---------------------------------------------------------------- 渲染与解析 */

export async function renderCase(c: MatrixCase): Promise<string> {
  return await renderToString(
    createSSRApp({
      render: () => h(ViewState as Component, c.props, c.slots as Record<string, () => string> | undefined),
    }),
  );
}

export function rootTag(html: string): string {
  const end = html.indexOf(">");
  return end === -1 ? html : html.slice(0, end);
}

export function rootAttr(html: string, name: string): string | null {
  const hit = new RegExp('(?:^|\\s)' + name + '="([^"]*)"').exec(rootTag(html));
  return hit?.[1] ?? null;
}

export function stripTags(html: string): string {
  return html
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function dataActions(html: string): string[] {
  return [...html.matchAll(/data-action="([^"]*)"/g)].map((m) => m[1] ?? "");
}

export function buttonNames(html: string): string[] {
  return [...html.matchAll(/<button\b[^>]*>([\s\S]*?)<\/button>/g)].map((m) => stripTags(m[1] ?? ""));
}

export function dashCount(html: string): number {
  return stripTags(html).split("\u2014").length - 1;
}

/** 解析后的期望文案（F-4 优先级：props > variant.copy > copyOf；错误态标题取服务端原样）。 */
export function expectedCopyOf(
  state: ViewStateKind,
  props: Record<string, unknown>,
  variantCopy?: Partial<ViewStateCopy>,
): { title: string | null; hint: string | null } {
  if (state === "first-load") return { title: null, hint: null };
  const base = copyOf(state);
  const propTitle = props["title"];
  const propHint = props["hint"];
  const isError = state === "failed" || state === "stale-412";
  const error = props["error"] as ApiError | null | undefined;
  const serverTitle = error !== null && error !== undefined && error.kind === "problem" ? error.title : NON_PROBLEM_TITLE;
  const title =
    variantCopy?.title ?? (isError ? serverTitle : typeof propTitle === "string" ? propTitle : base.title);
  const hint = variantCopy?.hint ?? (typeof propHint === "string" ? propHint : base.hint);
  return { title, hint };
}

/** 取某态的基准用例（默认桌面 1440x900 腿）；找不到即抛，禁静默回退成 undefined。 */
export function matrixCaseFor(state: ViewStateKind, label = "1440x900"): MatrixCase {
  const hit = sixStateMatrix().find((item) => item.state === state && item.viewport.label === label);
  if (hit === undefined) throw new Error("MATRIX-MISSING " + state + " " + label);
  return hit;
}

/** 直接给 props 渲染（用于 props 覆写、variant 注册、dev 断言等非基准用例）。 */
export async function renderProps(
  props: Record<string, unknown>,
  slots?: Record<string, () => string>,
): Promise<string> {
  return await renderToString(createSSRApp({ render: () => h(ViewState as Component, props, slots) }));
}

export interface Violation {
  readonly code: string;
  readonly detail: string;
}

export interface ContractOptions {
  /** variant 覆写后的期望文案（R-3：只允许覆盖 copy / 追加动作 / 替换呈现）。 */
  readonly variantCopy?: Partial<ViewStateCopy>;
  /** variant extraActions 追加后的期望动作键序列。 */
  readonly extraActions?: readonly ViewStateAction[];
}

/**
 * 六态契约检查（§3.4 不变量 + §1.3 四条非颜色载体）。返回违规清单而非直接 expect：
 * 使 M3-P02 能在自己的 spec 里对**同一矩阵**复跑并自行决定判红口径（R-4）。
 */
export async function checkStateContract(c: MatrixCase, options: ContractOptions = {}): Promise<Violation[]> {
  const html = await renderCase(c);
  const text = stripTags(html);
  const violations: Violation[] = [];
  const push = (code: string, detail: string): void => {
    violations.push({ code, detail });
  };

  if (rootAttr(html, "data-state") !== c.state) {
    push("data-state", c.viewport.label + " 根元素 data-state=" + String(rootAttr(html, "data-state")));
  }
  const role = EXPECTED_ROLE[c.state];
  if (rootAttr(html, "role") !== role) push("role", c.viewport.label + " role=" + String(rootAttr(html, "role")));

  const expectLive = role === "alert" ? null : "polite";
  if (rootAttr(html, "aria-live") !== expectLive) {
    push("aria-live", c.viewport.label + " aria-live=" + String(rootAttr(html, "aria-live")));
  }
  const expectBusy = c.state === "first-load" ? "true" : null;
  if (rootAttr(html, "aria-busy") !== expectBusy) {
    push("aria-busy", c.viewport.label + " aria-busy=" + String(rootAttr(html, "aria-busy")));
  }

  const want = expectedCopyOf(c.state, c.props, options.variantCopy);
  if (want.title !== null && !text.includes(want.title)) push("copy-title", c.viewport.label + " 缺标题「" + want.title + "」");
  if (want.hint !== null && !text.includes(want.hint)) push("copy-hint", c.viewport.label + " 缺提示「" + want.hint + "」");

  const wantActions = [...EXPECTED_ACTIONS[c.state], ...(options.extraActions ?? [])].filter(
    (item, index, all) => all.indexOf(item) === index,
  );
  const gotActions = dataActions(html);
  if (gotActions.join(",") !== wantActions.join(",")) {
    push("actions", c.viewport.label + " data-action=" + gotActions.join(",") + " 期望 " + wantActions.join(","));
  }
  if (wantActions.length > 0) {
    const names = buttonNames(html);
    if (names.length !== wantActions.length) push("action-names", c.viewport.label + " 按钮数 " + String(names.length));
    if (names.some((name) => name.length === 0)) push("action-names", c.viewport.label + " 存在无名称动作按钮（:38）");
  }
  if (wantActions.length === 0 && html.includes('data-part="actions"')) {
    push("actions", c.viewport.label + " 无动作却渲染了动作区（口径同 EmptyState.vue:9）");
  }

  if (role === "alert") {
    const error = c.props["error"] as ApiError | null | undefined;
    const rid = error?.requestId ?? "";
    if (!text.includes("request_id " + rid)) push("request-id", c.viewport.label + " request_id 不可见（:38）");
  }

  const missing = c.props["missing"] as readonly string[] | undefined;
  if (missing !== undefined && missing.length > 0) {
    if (dashCount(html) < missing.length) {
      push("missing-dash", c.viewport.label + " — 数量 " + String(dashCount(html)) + " 少于缺项数 " + String(missing.length));
    }
    for (const item of missing) {
      if (!text.includes(item)) push("missing-name", c.viewport.label + " 缺项名「" + item + "」不可见");
    }
    const reason = c.props["reason"];
    if (typeof reason === "string" && !text.includes(reason)) push("missing-reason", c.viewport.label + " 原因不可见");
  }

  if (c.state === "first-load") {
    if (text.length > 0) push("skeleton-text", c.viewport.label + " 骨架出字：「" + text + "」（§1.3 无文案）");
    if (/\d/.test(text)) push("skeleton-digit", c.viewport.label + " 骨架渲染数字冒充数据（§1.3）");
  }

  if (c.props["showPrevious"] === true) {
    if (rootAttr(html, "data-show-previous") !== "true") push("previous-attr", c.viewport.label + " 缺 data-show-previous");
    if (!text.includes("上一结果")) push("previous-text", c.viewport.label + " 缺「上一结果」标识（:29）");
  }
  if (c.props["keepInput"] === true && rootAttr(html, "data-keep-input") !== "true") {
    push("keep-input", c.viewport.label + " 缺 data-keep-input");
  }

  const body = c.slots?.["default"];
  if (body !== undefined && !text.includes(body())) {
    push("slot-default", c.viewport.label + " default slot 内容未渲染（原值/新旧版本由页面传入）");
  }

  return violations;
}
