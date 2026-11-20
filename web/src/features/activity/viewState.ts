/**
 * web/src/features/activity/viewState.ts —— UI-02 页面态 → 六态呈现词汇的唯一映射
 *
 * 为什么要有这一层：M0-03b-freeze.md §5 规定 store 的 phase 是**页面私有词汇**、六态是**呈现层词汇**，
 * 二者非一对一，映射规则必须固定且不得让页面各自发明第三种词汇。本文件就是 UI-02 的那条映射，
 * 纯函数、可穷举单测（含负对照）。
 *
 * 可达性诚实声明（禁自造触发条件）：
 *   listActivities 是纯列表读，契约不含任何「部分可比 / 待补」语义（无基准窗口、无共同子集、无缺项清单），
 *   故 partial-comparable 与 pending-fill 在 UI-02 **不可达**；本页的缺值一律按 COMMON.md:36
 *   在单元格层用 MissingValue（— + 原因）承载，不冒充页面级六态。
 *   ⇒ REACHABLE 常量把这一事实钉成机器可断言的集合，单测同时断言「不可达两态确实不在像集内」。
 */
import { stateFromError } from "@/components/state/viewState";
import type { ViewStateKind } from "@/components/state/viewState";
import type { ApiError } from "@/api/http";

/** 页面私有词汇：与 useWorkspaces 的 WorkspacesPhase 同一套五值（不新造第三套）。 */
export type ActivitiesPhase = "idle" | "loading" | "ready" | "empty" | "failed";

export interface ActivityListViewStateInput {
  readonly phase: ActivitiesPhase;
  readonly error: ApiError | null;
  /** 已加载行数：>0 时刷新/翻页保留上次结果（COMMON.md:29「上次结果可见且有『上一结果』标识」）。 */
  readonly itemCount: number;
}

/** null = 不进入六态呈现，主区渲染真实表格。 */
export type ActivityListViewState = ViewStateKind | null;

/** UI-02 实际可达的呈现态（诚实边界，见文件头）。 */
export const REACHABLE_VIEW_STATES: readonly ViewStateKind[] = ["first-load", "no-record", "failed", "stale-412"];

/** UI-02 结构上不可达的呈现态（缺契约触发条件，不得伪造）。 */
export const UNREACHABLE_VIEW_STATES: readonly ViewStateKind[] = ["partial-comparable", "pending-fill"];

export function activityListViewState(input: ActivityListViewStateInput): ActivityListViewState {
  if (input.phase === "failed") {
    // 失败态的 412 / CONFLICT 分桶由冻结件 stateFromError 判定，本页不另编分支（F-B）。
    return input.error === null ? "failed" : stateFromError(input.error);
  }
  // 无记录：store 在 items 为空时置 empty；ready 却 0 行属防御分支（同样按无记录呈现，不冒充首载骨架）。
  if (input.phase === "empty") return "no-record";
  if (input.phase === "ready") return input.itemCount === 0 ? "no-record" : null;
  // idle / loading：尚无上次结果才出骨架；已有行则保留上次结果（COMMON.md:29），主区继续渲染表格。
  return input.itemCount === 0 ? "first-load" : null;
}

/** 上次结果可见性：加载中且已有行 → 表格继续显示并打「上一结果」标识。 */
export function showsPreviousResult(input: ActivityListViewStateInput): boolean {
  return input.phase === "loading" && input.itemCount > 0;
}
