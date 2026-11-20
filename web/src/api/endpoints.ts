/**
 * web/src/api/endpoints.ts —— M0-03.slice.json 的 5 个 operationId 的类型化封装（唯一契约绑定层）
 *
 * 类型全部从 openapi-typescript 产物 web/src/api/types.ts 派生（S4 冻结，不得手改）：
 *   参数/请求体/响应体一律用 operations[...]["parameters"|"requestBody"|"responses"] 抽取，
 *   而不是在 TS 里重抄一遍字段 —— 契约变了这里就红，避免「前端镜像契约」漂移。
 *
 * 边界：本文件只做「签名 + 契约映射」，不含状态、不含缓存、不含 UI 文案；
 * 状态归 web/src/composables/*（Q5 裁定：Vue 原生 reactive + 单例 composable，不引入 Pinia）。
 */
import type { components, operations } from "@/api/types";
import { http, type ApiResult, type HttpClient } from "@/api/http";

export type Session = components["schemas"]["Session"];
export type SessionExchange = components["schemas"]["SessionExchange"];
export type Health = components["schemas"]["Health"];
export type Workspace = components["schemas"]["Workspace"];
export type WorkspaceCreate = components["schemas"]["WorkspaceCreate"];
export type WorkspacePage = components["schemas"]["WorkspacePage"];

type ListWorkspacesOp = operations["listWorkspaces"];
type CreateWorkspaceOp = operations["createWorkspace"];
type ExchangeSessionOp = operations["exchangeSession"];

/** GET /workspaces 的查询参数（CR-002/ADR-006 已移除 status：不得再加回，UI-01 无状态筛选控件）。 */
export type ListWorkspacesQuery = NonNullable<ListWorkspacesOp["parameters"]["query"]>;
export type CreateWorkspaceBody = CreateWorkspaceOp["requestBody"]["content"]["application/json"];
export type CreateWorkspaceHeaders = CreateWorkspaceOp["parameters"]["header"];
export type SessionExchangeBody = ExchangeSessionOp["requestBody"]["content"]["application/json"];

/** 契约 listWorkspaces.limit 的 default=25；UI-01 首屏与「加载更多」共用同一页长。 */
export const WORKSPACE_PAGE_LIMIT = 25;
/** 契约 listWorkspaces.limit 的 minimum/maximum。 */
export const WORKSPACE_PAGE_LIMIT_MIN = 1;
export const WORKSPACE_PAGE_LIMIT_MAX = 100;
/** 契约 q 参数的 minLength/maxLength。 */
export const WORKSPACE_QUERY_MAX_LENGTH = 100;
/** 契约 cursor 参数的 maxLength。 */
export const WORKSPACE_CURSOR_MAX_LENGTH = 300;

/** POST /session/exchange —— 入口令牌仅在首次使用，随后按会话检查（UI-01 操作表）。 */
export function exchangeSession(token: string, client: HttpClient = http): Promise<ApiResult<Session>> {
  const body: SessionExchangeBody = { token };
  return client.request<Session>({
    method: "POST",
    path: "/session/exchange",
    body,
    accept: [200],
  });
}

/** GET /session —— 会话检查。401 → 清本地会话回入口并保存深链；403 → 提示重开本机入口。 */
export function getSession(client: HttpClient = http): Promise<ApiResult<Session>> {
  return client.request<Session>({ method: "GET", path: "/session", accept: [200] });
}

/**
 * GET /health —— 服务与 worker 可用性。
 * 注意：Health.status 是合法响应字段（READY/DEGRADED），与 CR-002 移除的
 * listWorkspaces.status 查询参数是两回事，不得误删。
 */
export function getHealth(client: HttpClient = http): Promise<ApiResult<Health>> {
  return client.request<Health>({ method: "GET", path: "/health", accept: [200] });
}

/** GET /workspaces —— 游标分页（items + next_cursor），limit 默认 25。 */
export function listWorkspaces(
  query: ListWorkspacesQuery = {},
  client: HttpClient = http,
): Promise<ApiResult<WorkspacePage>> {
  const limit = query.limit ?? WORKSPACE_PAGE_LIMIT;
  return client.request<WorkspacePage>({
    method: "GET",
    path: "/workspaces",
    query: {
      cursor: query.cursor,
      limit,
      q: query.q,
    },
    accept: [200],
  });
}

export interface CreateWorkspaceOptions {
  /** 必填：一次用户意图一个 key；409 IDEMPOTENCY_CONFLICT 重试沿原 key。 */
  readonly idempotencyKey: string;
  readonly client?: HttpClient | undefined;
}

/**
 * POST /workspaces —— 新建工作区。
 * 契约要求 Idempotency-Key（8..128）；requireIdempotencyKey 使缺失变成客户端断言失败而不是服务端 400。
 * 201 响应带 ETag（当前对象修订号），由 http 层写入请求缓存，后续变更请求经 ifMatch 带上。
 */
export function createWorkspace(
  body: CreateWorkspaceBody,
  options: CreateWorkspaceOptions,
): Promise<ApiResult<Workspace>> {
  const client = options.client ?? http;
  return client.request<Workspace>({
    method: "POST",
    path: "/workspaces",
    body,
    idempotencyKey: options.idempotencyKey,
    requireIdempotencyKey: true,
    accept: [201],
  });
}

/* ------------------------------------------------------------------ UI-02 活动列表（FR-02）
 * operationId 逐字取自 contracts/pages.json 的 UI-02.operation_ids 与 contracts/operations.json：
 *   listActivities / getActivity / createActivity（D-036 先例：禁自造 opId）。
 * 后端路径原文 = /workspaces/{workspace_id}/activities（契约 path），与前端路由 /w/:workspace_id/activities
 * 是两回事：前者是 HTTP 契约，后者是 contracts/pages.json 的 route 真值。
 */

export type Activity = components["schemas"]["Activity"];
export type ActivityCreate = components["schemas"]["ActivityCreate"];
export type ActivityPage = components["schemas"]["ActivityPage"];

type ListActivitiesOp = operations["listActivities"];
type CreateActivityOp = operations["createActivity"];

/** GET 活动集合的查询参数（cursor/limit/q/status，逐字取契约，不重抄类型）。 */
export type ListActivitiesQuery = NonNullable<ListActivitiesOp["parameters"]["query"]>;
export type CreateActivityBody = CreateActivityOp["requestBody"]["content"]["application/json"];

/** 契约 listActivities.limit 的 default=25；首屏与「加载更多」共用同一页长（COMMON.md:38）。 */
export const ACTIVITY_PAGE_LIMIT = 25;
/** 契约 listActivities.limit 的 minimum/maximum。 */
export const ACTIVITY_PAGE_LIMIT_MIN = 1;
export const ACTIVITY_PAGE_LIMIT_MAX = 100;
/** 契约 q 参数的 minLength/maxLength。 */
export const ACTIVITY_QUERY_MAX_LENGTH = 100;
/** 契约 cursor 参数的 maxLength。 */
export const ACTIVITY_CURSOR_MAX_LENGTH = 300;
/** 契约 status 查询参数的 maxLength（取值口径见 features/activity/query.ts）。 */
export const ACTIVITY_STATUS_MAX_LENGTH = 60;
/** 契约 Activity.status 的枚举原文（唯一取值来源，禁自造状态词）。 */
export const ACTIVITY_STATUSES: readonly Activity["status"][] = ["OPEN", "ARCHIVED"];

/** 契约 path 参数原文拼接；标识符一律 encodeURIComponent，避免深链里的保留字符破坏路径。 */
export function activityCollectionPath(workspaceId: string): string {
  return "/workspaces/" + encodeURIComponent(workspaceId) + "/activities";
}

export function activityItemPath(workspaceId: string, activityId: string): string {
  return activityCollectionPath(workspaceId) + "/" + encodeURIComponent(activityId);
}

/** GET /workspaces/{workspace_id}/activities —— 游标分页（items + next_cursor），limit 默认 25。 */
export function listActivities(
  workspaceId: string,
  query: ListActivitiesQuery = {},
  client: HttpClient = http,
): Promise<ApiResult<ActivityPage>> {
  const limit = query.limit ?? ACTIVITY_PAGE_LIMIT;
  // 空值一律**不出现在 query 对象里**：http.ts 的 searchOf 虽然也会跳过 undefined/null，
  // 但把「不发送该参数」写在绑定层，单测才能对请求形状做集合级断言（而不是依赖序列化实现细节）。
  const effective: ListActivitiesQuery = { limit };
  if (query.cursor !== undefined) effective.cursor = query.cursor;
  if (query.q !== undefined) effective.q = query.q;
  if (query.status !== undefined) effective.status = query.status;
  return client.request<ActivityPage>({
    method: "GET",
    path: activityCollectionPath(workspaceId),
    query: effective,
    accept: [200],
  });
}

/** GET /workspaces/{workspace_id}/activities/{activity_id} —— 活动原值（含 revision，供后续 If-Match）。 */
export function getActivity(
  workspaceId: string,
  activityId: string,
  client: HttpClient = http,
): Promise<ApiResult<Activity>> {
  return client.request<Activity>({
    method: "GET",
    path: activityItemPath(workspaceId, activityId),
    accept: [200],
  });
}

export interface CreateActivityOptions {
  /** 必填：一次用户意图一个 key；409 重试沿原 key（不得重新生成）。 */
  readonly idempotencyKey: string;
  readonly client?: HttpClient | undefined;
}

/** POST /workspaces/{workspace_id}/activities —— 契约要求 Idempotency-Key（8..128）。 */
export function createActivity(
  workspaceId: string,
  body: CreateActivityBody,
  options: CreateActivityOptions,
): Promise<ApiResult<Activity>> {
  const client = options.client ?? http;
  return client.request<Activity>({
    method: "POST",
    path: activityCollectionPath(workspaceId),
    body,
    idempotencyKey: options.idempotencyKey,
    requireIdempotencyKey: true,
    accept: [201],
  });
}
