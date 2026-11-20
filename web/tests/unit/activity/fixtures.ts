/**
 * web/tests/unit/activity/fixtures.ts —— UI-02 单测共用夹具（合成数据，仅用于前端层断言）
 *
 * 字段形状逐字对齐 contracts/openapi.json 的 components.schemas.Activity（additionalProperties:false，
 * 12 个字段全部必填），由 TS 类型 `Activity` 兜住：契约变了这里就红。
 * 这些夹具**不是**端到端联调证据（AC-001 的真 E2E 必须打真实后端，FU-31）。
 */
import type { ApiError, ApiResult } from "@/api/http";
import type { Activity } from "@/api/endpoints";

export function makeActivity(overrides: Partial<Activity> = {}): Activity {
  return {
    id: "act-1",
    revision: 1,
    created_at: "2026-11-01T09:00:00+08:00",
    name: "合成活动甲",
    bank_id: "BANK-A",
    external_activity_id: "EXT-A-001",
    description: "合成数据，仅用于前端层断言",
    status: "OPEN",
    current_rule_id: "rule-1",
    bindings: [],
    rule_ids: ["rule-1"],
    receipt_ids: [],
    ...overrides,
  };
}

/** 缺值样本：三个可空字段全为 null，用于断言「— 与原因」而不是 0 / 空串。 */
export function makeSparseActivity(id: string): Activity {
  return makeActivity({
    id,
    name: "缺值活动 " + id,
    bank_id: null,
    external_activity_id: null,
    current_rule_id: null,
    status: "ARCHIVED",
    rule_ids: [],
  });
}

export function makeProblem(status: number, code: string, overrides: Partial<ApiError> = {}): ApiError {
  return {
    kind: "problem",
    status,
    code,
    type: "urn:campaignlab:problem:" + code.toLowerCase(),
    title: "服务端标题 " + code,
    detail: "服务端明细 " + code,
    requestId: "req-" + code.toLowerCase(),
    issues: [],
    ...overrides,
  };
}

export function makeTransport(status: number): ApiError {
  return {
    kind: "transport",
    status,
    code: "",
    type: "",
    title: "",
    detail: "",
    requestId: "",
    issues: [],
  };
}

export function ok<T>(data: T): ApiResult<T> {
  return { ok: true, status: 200, data, etag: null, requestId: "req-ok", notModified: false };
}

/** 带 ETag 的成功响应（createActivity 201 路径）：revision 缓存断言用。 */
export function okWithEtag<T>(data: T, etag: string, status = 201): ApiResult<T> {
  return { ok: true, status, data, etag, requestId: "req-etag", notModified: false };
}

export function fail(error: ApiError): ApiResult<never> {
  return { ok: false, error };
}
