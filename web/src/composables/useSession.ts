/**
 * web/src/composables/useSession.ts —— 会话 store（exchangeSession / getSession）
 *
 * 依据：
 *   - UI-01 操作表：「入口令牌仅在首次使用，随后按会话检查」；
 *   - M0-03-design.md §5：401 清本地会话与 store → 跳 `/`，原深链存 `?redirect=`；
 *     403（会话/Host/Origin 级）→ 回 `/` 并提示「重开本机入口」；
 *   - FRONTEND.md:12：深链直达、刷新、返回、切工作区、404、过期会话都要能回到合法入口；
 *   - 领域不变量：会话是否过期一律以服务端响应为准，前端不得用系统时间自行推算。
 *
 * 与路由的关系（S6 接线口径）：本 store 不 import vue-router（router 属 S6），
 * 只维护 `pendingRedirect` 与 `takeRedirect()`；S6 的路由守卫负责
 *   ① 进入受保护路由前 `captureRedirect(to.fullPath)`，
 *   ② 会话失效后读 `takeRedirect()` 决定回 `/` 还是回 `/?redirect=<深链>`。
 * 这样 S5 的 store 在 node 环境可单测（不触碰 DOM/router），S8 才能对它写深链断言。
 */
import { reactive } from "vue";
import type { InjectionKey } from "vue";
import { http, type ApiError, type ApiResult, type HttpClient } from "@/api/http";
import { exchangeSession, getSession, type Session } from "@/api/endpoints";
import { useWorkspaceScope, type WorkspaceScope } from "@/composables/useWorkspaceScope";

/** 合法入口（UI-01 路由 `/`）：任何会话级失败的兜底落点。 */
export const ROOT_PATH = "/";

export type SessionPhase = "unknown" | "checking" | "exchanging" | "active" | "anonymous" | "failed";

export type SessionRole = Session["allowed_roles"][number];

export interface SessionState {
  phase: SessionPhase;
  session: Session | null;
  /** 只保存服务端 Problem 映射结果；title 原样渲染，前端不另编文案。 */
  error: ApiError | null;
  /** 入口令牌只用一次：exchange 成功后置 true，bootstrap 不再重复换取。 */
  entryTokenUsed: boolean;
  /** 深链保全：会话失效时把原始目标路径留给路由守卫。 */
  pendingRedirect: string | null;
  lastRequestId: string | null;
  /** 仅证据：signOut 原因（不是用户文案）。 */
  lastSignOutReason: string | null;
}

export interface SessionStore {
  readonly state: SessionState;
  /** 首屏/刷新入口：有未用过的入口令牌则换取，否则按 cookie 会话检查。 */
  bootstrap(entryToken: string | null): Promise<SessionPhase>;
  exchange(entryToken: string): Promise<ApiResult<Session>>;
  verify(): Promise<ApiResult<Session>>;
  /** 清本地会话 + 清工作区作用域（轮询/草稿/临时查询）。 */
  signOut(reason: string, redirect?: string): void;
  /** 路由守卫在跳转前登记深链。 */
  captureRedirect(fullPath: string): void;
  /** 取出并清空深链（一次性消费，避免回退时反复重放）。 */
  takeRedirect(): string | null;
  hasRole(role: SessionRole): boolean;
  /** 观察者：登出时联动清理其他 store（避免 store 之间循环 import）。 */
  onSignOut(handler: (reason: string) => void): () => void;
}

export interface SessionDeps {
  readonly client?: HttpClient | undefined;
  readonly scope?: WorkspaceScope | undefined;
}

export function createSessionStore(deps: SessionDeps = {}): SessionStore {
  const client = deps.client ?? http;
  const scope = deps.scope ?? useWorkspaceScope();
  const state = reactive<SessionState>({
    phase: "unknown",
    session: null,
    error: null,
    entryTokenUsed: false,
    pendingRedirect: null,
    lastRequestId: null,
    lastSignOutReason: null,
  });
  const signOutHandlers = new Set<(reason: string) => void>();

  function signOut(reason: string, redirect?: string): void {
    state.session = null;
    state.phase = "anonymous";
    state.lastSignOutReason = reason;
    // 深链保全：调用方给了就用，没给则保留已登记的，最后兜底合法入口 `/`。
    state.pendingRedirect = redirect ?? state.pendingRedirect ?? ROOT_PATH;
    // 切/清作用域：释放上一个工作区的轮询、草稿范围与失效选择，并中止在飞请求。
    scope.clear("session:" + reason);
    for (const handler of signOutHandlers) handler(reason);
  }

  function applyFailure(error: ApiError): void {
    state.error = error;
    state.lastRequestId = error.requestId.length > 0 ? error.requestId : state.lastRequestId;
    if (error.kind === "problem" && error.status === 401) {
      // 过期会话/无会话：清本地会话与 store，回合法入口（深链由 pendingRedirect 保住）。
      signOut(error.code.length > 0 ? error.code : "SESSION_UNAUTHORIZED");
      return;
    }
    if (error.kind === "problem" && error.status === 403) {
      // 会话/Host/Origin 级 403：回 `/` 并提示「重开本机入口」（提示文案属 S6，用服务端 title）。
      signOut(error.code.length > 0 ? error.code : "SESSION_FORBIDDEN", ROOT_PATH);
      return;
    }
    state.phase = "failed";
  }

  function applySession(session: Session, requestId: string): void {
    state.session = session;
    state.error = null;
    state.phase = "active";
    state.lastRequestId = requestId.length > 0 ? requestId : state.lastRequestId;
  }

  async function exchange(entryToken: string): Promise<ApiResult<Session>> {
    state.phase = "exchanging";
    state.error = null;
    // 入口令牌一次性：无论成败都标记已用，避免刷新页面拿同一令牌反复换取（服务端亦会 401）。
    state.entryTokenUsed = true;
    const result = await exchangeSession(entryToken, client);
    if (result.ok) applySession(result.data, result.requestId);
    else applyFailure(result.error);
    return result;
  }

  async function verify(): Promise<ApiResult<Session>> {
    state.phase = "checking";
    state.error = null;
    const result = await getSession(client);
    if (result.ok) applySession(result.data, result.requestId);
    else applyFailure(result.error);
    return result;
  }

  async function bootstrap(entryToken: string | null): Promise<SessionPhase> {
    if (state.phase === "active") {
      // 已有会话：按会话检查（UI-01「随后按会话检查」），不重复消耗入口令牌。
      await verify();
      return state.phase;
    }
    if (entryToken !== null && entryToken.length > 0 && !state.entryTokenUsed) {
      await exchange(entryToken);
      return state.phase;
    }
    await verify();
    return state.phase;
  }

  return {
    state,
    bootstrap,
    exchange,
    verify,
    signOut,
    captureRedirect(fullPath: string): void {
      // 只接受站内绝对路径：外链/协议相对地址一律不保全（开放重定向防护）。
      state.pendingRedirect = /^\/(?![/\\])/.test(fullPath) ? fullPath : ROOT_PATH;
    },
    takeRedirect(): string | null {
      const redirect = state.pendingRedirect;
      state.pendingRedirect = null;
      return redirect;
    },
    hasRole(role: SessionRole): boolean {
      return state.session?.allowed_roles.includes(role) ?? false;
    },
    onSignOut(handler: (reason: string) => void): () => void {
      signOutHandlers.add(handler);
      return () => {
        signOutHandlers.delete(handler);
      };
    },
  };
}

let singleton: SessionStore | null = null;

export function useSession(): SessionStore {
  if (singleton === null) singleton = createSessionStore();
  return singleton;
}

/** 仅供单测复位。 */
export function resetSessionSingleton(): void {
  singleton = null;
}

export const sessionStoreKey: InjectionKey<SessionStore> = Symbol("campaignlab.session-store");
