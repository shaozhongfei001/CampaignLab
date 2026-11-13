/**
 * web/src/components/state/viewState.ts —— 六态枚举、唯一文案来源、错误态推导（M0-03b / S3）
 *
 * 签名冻结源：orchestrator/handoff/M0-03b-freeze.md §3.3（类型签名级冻结；改动须走 CR，同文 §5 第 2 行）。
 * 态名与措辞冻结源：spec/CampaignLab-SDD-v1.0/ui/COMMON.md 的 :27 / :28 / :30 / :31 / :32 / :36
 * （D-011：只引原文，禁改写措辞；行号是契约的一部分）。
 *
 * 依赖纪律：
 *   - A137（无数据获取副作用）：对 `@/api/http` **只做 type-only import** —— tsconfig 的
 *     verbatimModuleSyntax 会把它整条擦除，运行时不存在指向 api/** 的模块边；不 fetch、不 axios、
 *     不持有请求状态，六态触发值一律由消费页面以 props 显式传入（F-A：组件不猜）。
 *   - F-B：禁止新增 problem code 白名单。stateFromError() 只消费 presentationOf() 的返回与
 *     error.status，本文件内不出现任何 problem code 字面量。
 *   - 回报 S3-5：§4.2 R-1 字面禁 import features/**，但 F-A + F-B + §1.2 的 stale-412 触发条件
 *     （bucket === "CONFLICT"）只能靠 presentationOf() 判定；被 §2 F-2 强制复用的
 *     AlertBanner.vue:3 早已存在同一条依赖边，故本次未新增任何新的耦合方向。
 */
import type { ApiError } from "@/api/http";
import { presentationOf } from "@/features/shared/problemPresentation";

/** 六态字面量，逐字取 M0-03b-freeze.md §1.2「冻结字面量」列，顺序同 §3.3 联合类型声明序。 */
export type ViewStateKind =
  | "first-load"
  | "no-record"
  | "failed"
  | "partial-comparable"
  | "pending-fill"
  | "stale-412";

/** 动作键；取值集合冻结（§3.3），variant 亦只能在此集合内追加（R-3）。 */
export type ViewStateAction =
  | "create"
  | "import"
  | "clear-filter"
  | "export"
  | "refetch"
  | "rerun";

export interface ViewStateCopy {
  readonly title: string;
  readonly hint: string;
}

/** §3.3 冻结常量：顺序即 §1.2 表行序，测试按整序相等断言（禁自造态名）。 */
export const VIEW_STATE_KINDS: readonly ViewStateKind[] = [
  "first-load",
  "no-record",
  "failed",
  "partial-comparable",
  "pending-fill",
  "stale-412",
];

/**
 * 唯一文案来源表（§3.3「copyOf 的原文映射」逐字落地）。
 * 每个字段都是 COMMON.md 被引行的**连续子串**，pending-fill 的 hint 由 :30 与 :36 两条原文子串
 * 以全角分号拼接（拼接符不是措辞）；S2 的 viewStateCopy.spec.ts 会对磁盘原文做子串校验。
 */
const COPY: Record<ViewStateKind, ViewStateCopy> = {
  // :27 首载 —— 行为列首句 / 次句（§1.3：骨架本身不出字，此文案供消费方与 a11y 取名）。
  "first-load": { title: "主区骨架对应标题、表头和卡片位置。", hint: "保留导航" },
  // :28 无记录 —— 前半语义作 title（页面须用 title prop 覆盖为具体筛选原文），动作句作 hint。
  "no-record": { title: "指明当前筛选", hint: "提供创建、导入或清空筛选入口" },
  // :31 失败 —— 非 problem 失败的固定标题沿用 AlertBanner.vue:10 的同一串；hint 取 :31 原文。
  failed: { title: "请求未完成", hint: "错误摘要跳转字段，字段标注语义。保留输入" },
  // :30 部分可比 —— 首句 / 次句。
  "partial-comparable": { title: "原值仍显示，差值按共同子集或留空。", hint: "提供原因、缺项和导出入口" },
  // :30 + :36 待补 —— 标题同为 :30 首句（§3.3），区分由 data-state + hint + 缺项区承载。
  "pending-fill": {
    title: "原值仍显示，差值按共同子集或留空。",
    hint: "提供原因、缺项和导出入口；缺值显示 — 与原因。",
  },
  // :32 过期 —— 同句承载 title 与 hint，「重新获取或复跑」由动作键 refetch / rerun 落地。
  "stale-412": {
    title: "412 或候选失效时保留本地输入，显示新旧版本和重新获取或复跑入口",
    hint: "412 或候选失效时保留本地输入，显示新旧版本和重新获取或复跑入口",
  },
};

/** 默认动作键，逐条对齐 §1.3 表「默认动作键」列；空数组 = 该态默认无动作区。 */
const ACTIONS: Record<ViewStateKind, readonly ViewStateAction[]> = {
  "first-load": [],
  "no-record": ["create", "clear-filter"],
  failed: [],
  "partial-comparable": ["export"],
  "pending-fill": ["export"],
  "stale-412": ["refetch", "rerun"],
};

/** 文案只读访问器（F-4 第三优先级的唯一落点）。 */
export function copyOf(state: ViewStateKind): ViewStateCopy {
  return COPY[state];
}

/** 默认动作键只读访问器。 */
export function actionsOf(state: ViewStateKind): readonly ViewStateAction[] {
  return ACTIONS[state];
}

/**
 * dev 断言水槽（回报 S3-2：§3.4 要求 dev 断言，但本仓红线 no-console 与 A137 禁 import api/**
 * 使 http.ts 的现成水槽不可用，故在 state/ 内自建同型只增通道；仅 dev 写入、按键去重）。
 * 生产构建 import.meta.env.DEV === false → 恒空，不增长。
 */
export interface ViewStateDevNotice {
  readonly source: "ViewState" | "registry";
  readonly code: "error-required" | "variant-overwrite";
  readonly message: string;
}

export const VIEW_STATE_DEV_NOTICES: ViewStateDevNotice[] = [];

export function pushViewStateNotice(
  source: ViewStateDevNotice["source"],
  code: ViewStateDevNotice["code"],
  message: string,
): void {
  if (!import.meta.env.DEV) return;
  const dup = VIEW_STATE_DEV_NOTICES.some(
    (notice) => notice.source === source && notice.code === code && notice.message === message,
  );
  if (!dup) VIEW_STATE_DEV_NOTICES.push({ source, code, message });
}

/** 错误态推导（§3.3）：412 或 CONFLICT 分桶 → stale-412，其余失败 → failed。 */
export function stateFromError(error: ApiError): "failed" | "stale-412" {
  if (error.status === 412) return "stale-412";
  return presentationOf(error).bucket === "CONFLICT" ? "stale-412" : "failed";
}
