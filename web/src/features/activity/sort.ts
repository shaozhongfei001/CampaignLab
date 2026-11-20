/**
 * web/src/features/activity/sort.ts —— UI-02 表头排序（只作用于已加载行）
 *
 * 契约 listActivities 无 sort 参数（parameters 仅 cursor/limit/q/status），故排序是纯显示层行为，
 * 不得被当成服务端语义（COMMON.md:38 只要求「表格排序支持键盘」）。
 * 缺值（null）在升序与降序下都固定排在末尾：排序不得把 — 混进有值行中间，否则「缺项」会被读成最小值。
 */
import type { Activity } from "@/api/endpoints";

export type ActivitySortDir = "asc" | "desc";

/** 可排序键 = UI-02 全宽列表的六列（契约「页面结构」表原文顺序）。 */
export type ActivitySortKey =
  | "id"
  | "name"
  | "bank_id"
  | "external_activity_id"
  | "current_rule_id"
  | "status";

export interface ActivitySortState {
  readonly key: ActivitySortKey;
  readonly dir: ActivitySortDir;
}

export function nextActivitySort(current: ActivitySortState, key: ActivitySortKey): ActivitySortState {
  if (current.key !== key) return { key, dir: "asc" };
  return { key, dir: current.dir === "asc" ? "desc" : "asc" };
}

function compareId(left: string, right: string): number {
  if (left === right) return 0;
  return left < right ? -1 : 1;
}

export function sortActivities(rows: readonly Activity[], sort: ActivitySortState): Activity[] {
  const factor = sort.dir === "asc" ? 1 : -1;
  return rows.slice().sort((a, b) => {
    const left = a[sort.key];
    const right = b[sort.key];
    const leftMissing = left === null;
    const rightMissing = right === null;
    if (leftMissing !== rightMissing) return leftMissing ? 1 : -1;
    if (leftMissing) return compareId(a.id, b.id);
    const leftText = String(left);
    const rightText = String(right);
    if (leftText === rightText) return compareId(a.id, b.id);
    return leftText < rightText ? -factor : factor;
  });
}

/**
 * 可排序键的封闭集合（= UI-02 六列的 key，顺序同契约列序）。
 * 页面据此把 DataTable 的 string 型 sort 事件收敛回联合类型，不用 as 断言；
 * 单测断言本集合与 ACTIVITY_COLUMNS 的 key 整序相等，防止两处漂移。
 */
export const ACTIVITY_SORT_KEYS: readonly ActivitySortKey[] = [
  "id",
  "name",
  "bank_id",
  "external_activity_id",
  "current_rule_id",
  "status",
];

/** 把外部字符串收敛为可排序键；不在集合内返回 null（禁自造排序键）。 */
export function asActivitySortKey(key: string): ActivitySortKey | null {
  return ACTIVITY_SORT_KEYS.find((candidate) => candidate === key) ?? null;
}
