// 契约 listWorkspaces 无 sort 参数（切片 parameters 仅 cursor/limit/q），
// 故 UI-01 的「表头排序」只能作用于已加载行（COMMON.md 只要求排序可键盘触发）。
import type { Workspace } from "@/api/endpoints";

export type SortDir = "asc" | "desc";
export interface SortState {
  readonly key: "name" | "source_class" | "created_at";
  readonly dir: SortDir;
}

export function nextSort(current: SortState, key: SortState["key"]): SortState {
  if (current.key !== key) return { key, dir: "asc" };
  return { key, dir: current.dir === "asc" ? "desc" : "asc" };
}

export function sortWorkspaces(rows: readonly Workspace[], sort: SortState): Workspace[] {
  const factor = sort.dir === "asc" ? 1 : -1;
  return rows.slice().sort((a, b) => {
    const left = String(a[sort.key] ?? "");
    const right = String(b[sort.key] ?? "");
    if (left === right) return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
    return left < right ? -factor : factor;
  });
}
