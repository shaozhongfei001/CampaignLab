/**
 * web/src/features/activity/presentation.ts —— UI-02 显示层（状态词 / 列定义 / 行投影 / 缺值原因）
 *
 * 口径出处：
 *   - 列与列序：spec/CampaignLab-SDD-v1.0/ui/UI-02-activity-list.md「页面结构 · 全宽列表」原文
 *     （编号、活动、来源银行、行内编号、当前仿真版本、状态）；
 *   - 缺值：ui/COMMON.md:36「缺值显示 — 与原因。」⇒ 一律走 MissingValue，禁把 null 渲染成 0 或空串；
 *   - 不靠颜色区分（AC-032）：StatusTag 五 tone 同形（D-034③，属冻结面），故 tone 只作辅助载体，
 *     判据落在 data-status（契约枚举原文）+ 状态词文本 + 缺值 — 形状三条非颜色载体上；
 *   - 状态词措辞留痕：ARCHIVED → 「已归档」逐字取 UI-02-activity-list.md:32 原文；
 *     OPEN 在 spec 内**无**中文原文（实测 grep 全 spec 无「进行中/开放」），故取直译「开放」，
 *     并在同屏同时给出契约枚举原文（label + code），使显示层措辞可回退且不掩盖服务端真值。
 *     该措辞属显示层（PRODUCT.md:43「显示文案按公共页面规范与各页契约映射」），非契约词、非六态冻结文案。
 */
import type { Activity } from "@/api/endpoints";
import { ACTIVITY_STATUSES } from "@/api/endpoints";
import type { StatusTone, TableColumn, TableRow } from "@/components/componentTypes";

export interface ActivityStatusView {
  /** 契约 Activity.status 枚举原文：机器可读载体，供 data-status 选择器与单测断言。 */
  readonly code: string;
  readonly label: string;
  readonly tone: StatusTone;
}

const STATUS_VIEW: Record<Activity["status"], ActivityStatusView> = {
  OPEN: { code: "OPEN", label: "开放", tone: "OK" },
  ARCHIVED: { code: "ARCHIVED", label: "已归档", tone: "NEUTRAL" },
};

/** 顺序 = ACTIVITY_STATUSES（即契约枚举声明序），供筛选下拉与单测整序断言。 */
export const ACTIVITY_STATUS_VIEWS: readonly ActivityStatusView[] = ACTIVITY_STATUSES.map(
  (code) => STATUS_VIEW[code],
);

export function statusViewOf(status: Activity["status"]): ActivityStatusView {
  return STATUS_VIEW[status];
}

/** 「label（code）」：抽屉与筛选项用，保证契约枚举原文在任何呈现处都可见。 */
export function statusTextOf(status: Activity["status"]): string {
  const view = STATUS_VIEW[status];
  return view.label + "（" + view.code + "）";
}

/** UI-02 全宽列表六列（列序 = 契约原文，禁重排）。 */
export const ACTIVITY_COLUMNS: readonly TableColumn[] = [
  { key: "id", label: "编号", sortable: true, mono: true },
  { key: "name", label: "活动", sortable: true },
  { key: "bank_id", label: "来源银行", sortable: true, mono: true },
  { key: "external_activity_id", label: "行内编号", sortable: true, mono: true },
  { key: "current_rule_id", label: "当前仿真版本", sortable: true, mono: true },
  { key: "status", label: "状态", sortable: true },
];

/** 表头文字（FirstLoadSkeleton 的 headCells 直接用同一真值，骨架与真表列数恒等）。 */
export const ACTIVITY_COLUMN_LABELS: readonly string[] = ACTIVITY_COLUMNS.map((column) => column.label);

/** 行投影：只搬运服务端原值，不做任何单位换算或补默认值（null 保持 null 交给 MissingValue）。 */
export function toActivityRow(activity: Activity): TableRow {
  return {
    id: activity.id,
    name: activity.name,
    bank_id: activity.bank_id,
    external_activity_id: activity.external_activity_id,
    current_rule_id: activity.current_rule_id,
    status: activity.status,
  };
}

/** 缺值原因（COMMON.md:36）：只陈述「服务端未返回」这一可核对事实，不推测业务原因（关联≠因果）。 */
export const MISSING_REASON: Readonly<Record<"bank_id" | "external_activity_id" | "current_rule_id", string>> = {
  bank_id: "服务端未返回来源银行",
  external_activity_id: "服务端未返回行内活动编号",
  current_rule_id: "服务端未返回当前仿真版本",
};

/** 新建活动的成对校验（UI-02:28「来源银行与行内编号成对填写」）。返回空串表示通过。 */
export function validateActivityDraft(draft: {
  readonly name: string;
  readonly bank_id: string;
  readonly external_activity_id: string;
}): string {
  if (draft.name.trim().length === 0) return "名称必填";
  const hasBank = draft.bank_id.trim().length > 0;
  const hasExternal = draft.external_activity_id.trim().length > 0;
  if (hasBank !== hasExternal) return "来源银行与行内活动编号须成对填写";
  return "";
}

/**
 * 运行时防御：服务端若返回枚举外取值，原样回显该取值而不是渲染 undefined
 * （机器门禁第 2 条：页面文本禁 NaN/undefined/[object Object]/Infinity）。
 */
export function statusViewOfCode(code: string): ActivityStatusView {
  const hit = ACTIVITY_STATUS_VIEWS.find((view) => view.code === code);
  return hit ?? { code, label: code, tone: "NEUTRAL" };
}

/** TableRow 索引在 noUncheckedIndexedAccess 下含 undefined，一律折成 null 交 MissingValue。 */
export function asCellValue(value: string | number | null | undefined): string | number | null {
  return value === undefined ? null : value;
}

/** 同上，折成字符串：null/undefined → 空串（禁把 undefined 拼进可见文本）。 */
export function asCellText(value: string | number | null | undefined): string {
  return value === undefined || value === null ? "" : String(value);
}

/**
 * 数组字段（bindings / rule_ids / receipt_ids）的可见投影：
 * 空数组 = 缺值（null）交 MissingValue，禁渲染成 0 或空串冒充数据（COMMON.md:36 + M0-03b §1.3）。
 */
export function joinIdsOrNone(values: readonly string[]): string | null {
  return values.length === 0 ? null : values.join("、");
}
