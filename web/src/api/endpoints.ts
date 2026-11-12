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
