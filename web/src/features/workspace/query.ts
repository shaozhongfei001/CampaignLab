// UI-01 搜索词 q 的唯一清理口径（任务卡 S6 逐条要求）：
//   trim → 折叠连续空白为单空格 → 空则不发送该参数 → 非空截断到契约 maxLength=100。
// 组合层（composables/useWorkspaces.ts，S5 冻结面）已有「q 为空则不带参数」的行为（state.q.length > 0 才写入 query），
// 故本模块只负责归一化，返回空串即等价于「不发送该参数」。
import { WORKSPACE_QUERY_MAX_LENGTH } from "@/api/endpoints";

const COLLAPSE = /\s+/g;

export function normalizeWorkspaceQuery(raw: string): string {
  const collapsed = raw.trim().replace(COLLAPSE, " ");
  if (collapsed.length === 0) return "";
  return collapsed.slice(0, WORKSPACE_QUERY_MAX_LENGTH);
}

export function sendsQuery(raw: string): boolean {
  return normalizeWorkspaceQuery(raw).length > 0;
}
