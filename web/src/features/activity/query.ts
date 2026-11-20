/**
 * web/src/features/activity/query.ts —— UI-02 过滤项的唯一清理口径
 *
 * 逐字对齐契约 listActivities 的查询参数（contracts/openapi.json）：
 *   q      minLength 1 / maxLength 100 —— trim → 折叠连续空白 → 空则不发送 → 非空截断到 100；
 *   status minLength 1 / maxLength 60 —— 只接受 Activity.status 的枚举原文（OPEN / ARCHIVED），
 *          其余取值一律归空串（= 不发送该参数）。禁自造状态词（D-011 / D-036 先例）。
 *
 * 与 UI-01 的 features/workspace/query.ts 同构但**不共用**：两者的 maxLength 与取值域不同
 * （listWorkspaces 无 status 参数，CR-002 / ADR-006），共用会把「工作区可按状态过滤」的
 * 已否决语义偷偷带回来。
 */
import { ACTIVITY_QUERY_MAX_LENGTH, ACTIVITY_STATUSES, ACTIVITY_STATUS_MAX_LENGTH } from "@/api/endpoints";
import type { Activity } from "@/api/endpoints";

const COLLAPSE = /\s+/g;

/** 归一化搜索词；返回空串即等价于「不发送 q 参数」。 */
export function normalizeActivityQuery(raw: string): string {
  const collapsed = raw.trim().replace(COLLAPSE, " ");
  if (collapsed.length === 0) return "";
  return collapsed.slice(0, ACTIVITY_QUERY_MAX_LENGTH);
}

/** 归一化状态过滤；返回空串即等价于「不发送 status 参数」（= 全部状态）。 */
export function normalizeActivityStatus(raw: string): Activity["status"] | "" {
  const trimmed = raw.trim().slice(0, ACTIVITY_STATUS_MAX_LENGTH);
  return ACTIVITY_STATUSES.find((value) => value === trimmed) ?? "";
}

export function sendsActivityQuery(raw: string): boolean {
  return normalizeActivityQuery(raw).length > 0;
}

export function sendsActivityStatus(raw: string): boolean {
  return normalizeActivityStatus(raw).length > 0;
}

/** 页面是否处于「有筛选」状态：无记录态的文案必须指明当前筛选（COMMON.md:28）。 */
export function hasActivityFilter(q: string, status: string): boolean {
  return sendsActivityQuery(q) || sendsActivityStatus(status);
}
