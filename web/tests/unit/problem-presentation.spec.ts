// S8 / A8 裁定：ApiError 的前端呈现分类必须是 20 个权威 code 的纯函数映射，
// 20 个输入 code 全覆盖，一个都不能漏；未知 code 走 default 分支渲染服务端 title/detail/request_id（Q4）。
// 权威 code 集合出处＝spec/CampaignLab-SDD-v1.0/architecture/API.md 第 22–29 行（20 个，非前端白名单拷贝，
// 运行时白名单只有 problemPresentation.ts 一处；本清单是测试侧的防漂移夹具）。
import { describe, expect, it } from "vitest";
import {
  AUTHORITATIVE_PROBLEM_CODES,
  PROBLEM_CODE_BUCKETS,
  bucketOfCode,
  presentationOf,
  type PresentationBucket,
} from "@/features/shared/problemPresentation";
import type { ApiError } from "@/api/http";

const API_MD_CODES = [
  "BAD_REQUEST", "BAD_CURSOR",
  "SESSION_EXPIRED", "ORIGIN_DENIED", "ACCESS_DENIED",
  "RESOURCE_NOT_FOUND",
  "IDEMPOTENCY_CONFLICT", "STATE_CONFLICT", "VERSION_MISMATCH", "STALE_CANDIDATE", "SNAPSHOT_CONFLICT", "ACTION_REVIEW_REQUIRED",
  "REVISION_CONFLICT", "PRECONDITION_REQUIRED",
  "INPUT_TOO_LARGE", "VALIDATION_ERROR", "INVALID_SCOPE", "EVIDENCE_REQUIRED",
  "JOB_CAPACITY", "INTERNAL_ERROR",
];
const ALL_BUCKETS: readonly PresentationBucket[] = ["ENTRY", "INVISIBLE", "INPUT", "CONFLICT", "TRANSIENT"];

function problem(code: string, status: number, over: Partial<ApiError> = {}): ApiError {
  return {
    kind: "problem", status, code,
    type: "urn:campaignlab:problem:" + code.toLowerCase(),
    title: "服务端标题", detail: "服务端说明", requestId: "req-1", issues: [],
    ...over,
  };
}

describe("Problem code → 前端呈现分类（20 → 5 全覆盖）", () => {
  it("映射输入集与 API.md 第 22–29 行的 20 个 code 完全一致", () => {
    expect(AUTHORITATIVE_PROBLEM_CODES.slice().sort()).toEqual(API_MD_CODES.slice().sort());
    expect(AUTHORITATIVE_PROBLEM_CODES.length).toBe(20);
  });

  it("映射值恰为 5 个前端自有档位", () => {
    const used = new Set(Object.values(PROBLEM_CODE_BUCKETS));
    expect([...used].sort()).toEqual(ALL_BUCKETS.slice().sort());
  });

  it.each(API_MD_CODES)("code %s → 命中 5 档之一且非空", (code) => {
    const bucket = bucketOfCode(code);
    expect(bucket).not.toBeNull();
    expect(ALL_BUCKETS).toContain(bucket);
    const view = presentationOf(problem(code, 400));
    expect(view.bucket).toBe(bucket);
    expect(view.showServerTitle).toBe(true);
  });

  it.each(["ENTRY", "INVISIBLE", "INPUT", "CONFLICT", "TRANSIENT"] as const)("档位 %s 至少有一个 code 落位", (bucket) => {
    const count = API_MD_CODES.filter((code) => bucketOfCode(code) === bucket).length;
    expect(count).toBeGreaterThan(0);
  });

  it("403 与 404 同一呈现（不可见即不可见，D-011 页面侧后果）", () => {
    const denied = presentationOf(problem("ACCESS_DENIED", 403));
    const missing = presentationOf(problem("RESOURCE_NOT_FOUND", 404));
    expect(denied.sameAsNotFound).toBe(true);
    expect(missing.sameAsNotFound).toBe(true);
    expect(denied.bucket).toBe(missing.bucket);
  });

  it("INPUT / CONFLICT 保留输入，ENTRY 不保留", () => {
    expect(presentationOf(problem("VALIDATION_ERROR", 422)).keepInput).toBe(true);
    expect(presentationOf(problem("REVISION_CONFLICT", 412)).keepInput).toBe(true);
    expect(presentationOf(problem("SESSION_EXPIRED", 401)).keepInput).toBe(false);
  });

  it("未知 code → default 分支仍渲染服务端 title/detail/request_id（Q4 不镜像冻结面）", () => {
    const view = presentationOf(problem("SOME_FUTURE_CODE", 418));
    expect(view.bucket).toBeNull();
    expect(view.showServerTitle).toBe(true);
  });

  it("五类前端自有 kind 不伪装服务端 code（R3-Q6）", () => {
    for (const kind of ["transport", "aborted", "payload", "assertion", "timeout"] as const) {
      const view = presentationOf({ ...problem("X", 0), kind, code: "", title: "" });
      expect(view.showServerTitle).toBe(false);
      expect(view.bucket).toBeNull();
    }
  });

  it("429 触发退避；契约响应码全集无 304，故不存在任何 304 特判（A7）", () => {
    expect(presentationOf(problem("JOB_CAPACITY", 429)).backoff).toBe(true);
    const source = JSON.stringify(Object.keys(PROBLEM_CODE_BUCKETS));
    expect(source).not.toContain("304");
  });
});
