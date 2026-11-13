// A8 裁定：ApiError 的前端呈现分类是「20 个权威 code 的纯函数映射」。
// 唯一输入集来源＝spec/CampaignLab-SDD-v1.0/architecture/API.md 第 22–29 行（20 个 code）。
// 本模块是该集合在前端的唯一落点：组件不得再抄一份 code 白名单（Q4 / RULING_NO_FRONTEND_MIRROR）。
// 未知 code 一律返回 null → 走 default 分支，原样渲染服务端 title/detail/request_id。
import type { ApiError, Issue } from "@/api/http";

export type PresentationBucket =
  | "ENTRY"
  | "INVISIBLE"
  | "INPUT"
  | "CONFLICT"
  | "TRANSIENT";

export const PROBLEM_CODE_BUCKETS = {
  BAD_REQUEST: "INPUT",
  BAD_CURSOR: "INPUT",
  SESSION_EXPIRED: "ENTRY",
  ORIGIN_DENIED: "ENTRY",
  ACCESS_DENIED: "INVISIBLE",
  RESOURCE_NOT_FOUND: "INVISIBLE",
  INPUT_TOO_LARGE: "INPUT",
  VALIDATION_ERROR: "INPUT",
  INVALID_SCOPE: "INPUT",
  EVIDENCE_REQUIRED: "INPUT",
  IDEMPOTENCY_CONFLICT: "CONFLICT",
  STATE_CONFLICT: "CONFLICT",
  VERSION_MISMATCH: "CONFLICT",
  STALE_CANDIDATE: "CONFLICT",
  SNAPSHOT_CONFLICT: "CONFLICT",
  ACTION_REVIEW_REQUIRED: "CONFLICT",
  REVISION_CONFLICT: "CONFLICT",
  PRECONDITION_REQUIRED: "TRANSIENT",
  JOB_CAPACITY: "TRANSIENT",
  INTERNAL_ERROR: "TRANSIENT",
} as const satisfies Record<string, PresentationBucket>;

export type AuthoritativeProblemCode = keyof typeof PROBLEM_CODE_BUCKETS;

export const AUTHORITATIVE_PROBLEM_CODES: readonly AuthoritativeProblemCode[] = Object.keys(
  PROBLEM_CODE_BUCKETS,
) as AuthoritativeProblemCode[];

export function bucketOfCode(code: string): PresentationBucket | null {
  return (PROBLEM_CODE_BUCKETS as Record<string, PresentationBucket | undefined>)[code] ?? null;
}

export interface Presentation {
  readonly bucket: PresentationBucket | null;
  readonly showServerTitle: boolean;
  readonly sameAsNotFound: boolean;
  readonly keepInput: boolean;
  readonly backoff: boolean;
}

export function presentationOf(error: ApiError): Presentation {
  const isProblem = error.kind === "problem";
  const bucket = isProblem ? bucketOfCode(error.code) : null;
  return {
    bucket,
    showServerTitle: isProblem,
    sameAsNotFound: bucket === "INVISIBLE",
    keepInput: bucket === "INPUT" || bucket === "CONFLICT",
    backoff: bucket === "TRANSIENT" && error.status === 429,
  };
}

export function issuesForLocation(issues: readonly Issue[], location: string): Issue[] {
  return issues.filter((issue) => issue.location === location);
}

export function severityOf(issues: readonly Issue[]): "ERROR" | "WARNING" | "INFO" | null {
  if (issues.some((i) => i.severity === "ERROR")) return "ERROR";
  if (issues.some((i) => i.severity === "WARNING")) return "WARNING";
  if (issues.length > 0) return "INFO";
  return null;
}
