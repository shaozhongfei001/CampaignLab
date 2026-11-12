/**
 * web/src/composables/useWorkspaces.ts —— 工作区列表 / 新建 / 健康度 store
 *
 * 依据：
 *   - UI-01 字段表：列表取 Workspace.name/source_class/created_at；创建取 WorkspaceCreate；
 *   - UI-01 操作表：刷新走 getHealth + listWorkspaces，worker 离线显示「作业受限」；
 *     新建走 createWorkspace，成功后进入所选工作区的活动页（导航属 S6，本 store 只置状态）；
 *   - CR-002 / ADR-006：listWorkspaces 无 status 参数 → 本 store 不提供任何状态筛选入口；
 *   - M0-03-design.md §5：401 清会话回入口；412 REVISION_CONFLICT 保留本地输入并暴露新旧 revision；
 *   - FRONTEND.md:13：abort + 请求序列，晚到响应不得覆盖当前范围。
 *
 * 状态源纪律（Q5 / §6）：URL（S6 路由）> 请求缓存（本 store）> 本地表单（S6 组件）。
 * 金额=分整数、比率=十进制字符串、时区 Asia/Shanghai —— 本 store 只搬运服务端原值，
 * 一律不做单位换算（换算属显示层，S6）。
 */
import { reactive } from "vue";
import type { InjectionKey } from "vue";
import { http, type ApiError, type ApiResult, type HttpClient } from "@/api/http";
import {
  WORKSPACE_PAGE_LIMIT,
  createWorkspace,
  getHealth,
  listWorkspaces,
  type CreateWorkspaceBody,
  type Health,
  type ListWorkspacesQuery,
  type Workspace,
} from "@/api/endpoints";
import { useWorkspaceScope, type WorkspaceScope } from "@/composables/useWorkspaceScope";
import { useSession, type SessionStore } from "@/composables/useSession";

export type WorkspacesPhase = "idle" | "loading" | "ready" | "empty" | "failed";

export interface WorkspaceRevision {
  /** 契约 Workspace.revision：乐观并发用，变更请求经 If-Match 带上。 */
  readonly revision: number;
  /** 响应 ETag 原值（含引号）；null 表示服务端未给。 */
  readonly etag: string | null;
}

export interface WorkspacesState {
  phase: WorkspacesPhase;
  items: Workspace[];
  nextCursor: string | null;
  limit: number;
  /** 入口页搜索词（契约 q，<=100 字）；属页面自身状态，不随工作区切换清理。 */
  q: string;
  error: ApiError | null;
  health: Health | null;
  /** Health.worker === "OFFLINE" 或 status === "DEGRADED" → UI-01 顶栏「作业受限」。 */
  workerRestricted: boolean;
  creating: boolean;
  createError: ApiError | null;
  selectedId: string | null;
  lastRequestId: string | null;
}

export interface WorkspacesStore {
  readonly state: WorkspacesState;
  /** 请求缓存：workspaceId → { revision, etag }。切工作区时清上一作用域的条目，只留新选中项。 */
  readonly revisions: Record<string, WorkspaceRevision>;
  refreshHealth(): Promise<ApiResult<Health>>;
  /** 首页/刷新。不设「加载中就不许再发」的闸：更晚的请求经 gate 取消更早的（FRONTEND.md:13）。 */
  loadFirstPage(): Promise<void>;
  loadMore(): Promise<void>;
  setQuery(q: string): Promise<void>;
  create(body: CreateWorkspaceBody, idempotencyKey: string): Promise<ApiResult<Workspace>>;
  /** 选中/切换工作区：驱动作用域清理（轮询、草稿范围、失效选择、在飞请求）。 */
  select(workspaceId: string | null): boolean;
  revisionOf(workspaceId: string): WorkspaceRevision | null;
  /** 登出联动：清空列表态与请求缓存（由 session.onSignOut 注册，非 UI 调用）。 */
  resetForSignOut(): void;
}

export interface WorkspacesDeps {
  readonly client?: HttpClient | undefined;
  readonly scope?: WorkspaceScope | undefined;
  readonly session?: SessionStore | undefined;
}

const LIST_GATE_KEY = "workspaces:list";
const HEALTH_GATE_KEY = "workspaces:health";

export function createWorkspacesStore(deps: WorkspacesDeps = {}): WorkspacesStore {
  const client = deps.client ?? http;
  const scope = deps.scope ?? useWorkspaceScope();
  const session = deps.session ?? useSession();

  const state = reactive<WorkspacesState>({
    phase: "idle",
    items: [],
    nextCursor: null,
    limit: WORKSPACE_PAGE_LIMIT,
    q: "",
    error: null,
    health: null,
    workerRestricted: false,
    creating: false,
    createError: null,
    selectedId: null,
    lastRequestId: null,
  });
  const revisions = reactive<Record<string, WorkspaceRevision>>({});

  function remember(workspace: Workspace, etag: string | null): void {
    revisions[workspace.id] = { revision: workspace.revision, etag };
  }

  /**
   * 清空请求缓存，只保留 keepId：新选中工作区自身那条是刚由列表响应给出的，属当前作用域，
   * 删掉它等于把服务端已给的 revision 白白丢弃（下一次变更请求就要多跑一趟 412）。
   * keepId 为 null 即全清（登出路径）。
   */
  function dropRevisionsExcept(keepId: string | null): void {
    for (const id of Object.keys(revisions)) {
      if (id !== keepId) delete revisions[id];
    }
  }

  function touchRequestId(requestId: string): void {
    if (requestId.length > 0) state.lastRequestId = requestId;
  }

  /** 会话级失败（401/403）统一交 session store：清会话 + 清作用域 + 登记回合法入口的深链。 */
  function isSessionFailure(error: ApiError): boolean {
    return error.kind === "problem" && (error.status === 401 || error.status === 403);
  }

  function finish(items: Workspace[], nextCursor: string | null, append: boolean): void {
    const merged = append ? [...state.items, ...items] : items;
    const seen = new Set<string>();
    state.items = merged.filter((item) => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    });
    state.nextCursor = nextCursor;
    // UI-01：无工作区时突出创建 → 空结果单独成态，不与失败态混用。
    state.phase = state.items.length === 0 ? "empty" : "ready";
  }

  async function load(append: boolean): Promise<void> {
    const inflight = scope.gate.begin(LIST_GATE_KEY);
    const epoch = scope.epochOf();
    state.phase = "loading";
    state.error = null;

    const query: ListWorkspacesQuery = { limit: state.limit };
    if (state.q.length > 0) query.q = state.q;
    if (append && state.nextCursor !== null) query.cursor = state.nextCursor;

    const result = await listWorkspaces(query, client);

    // 晚到响应不得覆盖当前范围：被更晚请求取代，或期间切过工作区，一律丢弃（FRONTEND.md:13）。
    if (inflight.isStale() || scope.isStale(epoch)) return;

    touchRequestId(result.ok ? result.requestId : result.error.requestId);

    if (result.ok) {
      for (const item of result.data.items) remember(item, null);
      finish(result.data.items, result.data.next_cursor, append);
      return;
    }
    if (isSessionFailure(result.error)) {
      // 错误归 session store 呈现；本 store 回到入口态，不重复持有同一份 Problem。
      session.signOut(result.error.code.length > 0 ? result.error.code : "WORKSPACES_UNAUTHORIZED");
      state.phase = "idle";
      return;
    }
    state.error = result.error;
    state.phase = "failed";
  }

  async function refreshHealth(): Promise<ApiResult<Health>> {
    const inflight = scope.gate.begin(HEALTH_GATE_KEY);
    const result = await getHealth(client);
    if (inflight.isStale()) return result;
    if (result.ok) {
      state.health = result.data;
      state.workerRestricted = result.data.worker === "OFFLINE" || result.data.status === "DEGRADED";
      touchRequestId(result.requestId);
      return result;
    }
    if (isSessionFailure(result.error)) {
      session.signOut(result.error.code.length > 0 ? result.error.code : "HEALTH_UNAUTHORIZED");
      return result;
    }
    // 健康度失败不清空既有判定：worker 状态未知时不额外限制，服务不可用文案由 UI 层给。
    touchRequestId(result.error.requestId);
    return result;
  }

  async function create(body: CreateWorkspaceBody, idempotencyKey: string): Promise<ApiResult<Workspace>> {
    state.creating = true;
    state.createError = null;
    // 幂等键由调用方（S6）按「一次用户意图一个 key」生成；409 重试必须沿原 key，不得在此重新生成。
    const result = await createWorkspace(body, { idempotencyKey, client });
    state.creating = false;
    if (result.ok) {
      touchRequestId(result.requestId);
      remember(result.data, result.etag);
      state.items = [result.data, ...state.items.filter((item) => item.id !== result.data.id)];
      state.phase = "ready";
      return result;
    }
    touchRequestId(result.error.requestId);
    if (isSessionFailure(result.error)) {
      session.signOut(result.error.code.length > 0 ? result.error.code : "CREATE_UNAUTHORIZED");
      return result;
    }
    // 其余失败（409 IDEMPOTENCY_CONFLICT / 412 REVISION_CONFLICT / 422 / 413 …）一律保留本地输入，
    // 由 S6 按 M0-03-design.md §5 的分支表呈现；本 store 不擅自清表单。
    state.createError = result.error;
    return result;
  }

  const store: WorkspacesStore = {
    state,
    revisions,
    refreshHealth,
    loadFirstPage: () => load(false),
    loadMore: () => load(true),
    async setQuery(q: string): Promise<void> {
      state.q = q;
      state.nextCursor = null;
      await load(false);
    },
    create,
    select(workspaceId: string | null): boolean {
      const changed = scope.setWorkspace(workspaceId, "ui-01:select");
      state.selectedId = workspaceId;
      if (changed) {
        // 切工作区：清上一作用域的请求缓存与创建残留（草稿范围/轮询由 scope 资源表负责）。
        dropRevisionsExcept(workspaceId);
        state.createError = null;
      }
      return changed;
    },
    revisionOf(workspaceId: string): WorkspaceRevision | null {
      return revisions[workspaceId] ?? null;
    },
    resetForSignOut(): void {
      state.phase = "idle";
      state.items = [];
      state.nextCursor = null;
      state.q = "";
      state.error = null;
      state.creating = false;
      state.createError = null;
      state.selectedId = null;
      dropRevisionsExcept(null);
    },
  };

  // 登出联动（观察者而非 import：session 不反向依赖 workspaces，避免循环）。
  session.onSignOut(() => {
    store.resetForSignOut();
  });

  return store;
}

let singleton: WorkspacesStore | null = null;

export function useWorkspaces(): WorkspacesStore {
  if (singleton === null) singleton = createWorkspacesStore();
  return singleton;
}

/** 仅供单测复位。 */
export function resetWorkspacesSingleton(): void {
  singleton = null;
}

export const workspacesStoreKey: InjectionKey<WorkspacesStore> = Symbol("campaignlab.workspaces-store");
