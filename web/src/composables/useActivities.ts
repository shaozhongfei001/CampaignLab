/**
 * web/src/composables/useActivities.ts —— UI-02 活动列表 / 详情 / 新建 store
 *
 * 依据：
 *   - UI-02 操作表：「搜索与进入活动 = listActivities, getActivity」「新建活动 = createActivity」；
 *   - UI-02 字段表：过滤 = 名称或编号(q) + 状态(status)；新建 = ActivityCreate；
 *   - UI-02 边界：「已归档活动可检索和查看」「相同银行行内活动编号重复显示冲突并定位既有记录」；
 *   - COMMON.md:38：列表默认 25 行，更多数据由服务器游标加载；
 *   - FRONTEND.md:13：abort + 请求序列，晚到响应不得覆盖当前范围；
 *   - COMMON.md:19：工作区切换清理本地页面临时查询、轮询及失效选择。
 *
 * 状态源纪律（Q5 / M0-03-design §6）：URL（路由 :workspace_id + query）> 请求缓存（本 store）> 本地表单（页面）。
 * 本 store 只搬运服务端原值：金额/比率/时区换算一律不做（换算属显示层）。
 *
 * 与 useWorkspaces 的关系：两者共用同一个 WorkspaceScope 单例（gate + epoch + 资源表），
 * 但**各自持有独立的列表态**；本 store 不复用 workspaces 的 phase 词汇之外的第三套词汇
 * （M0-03b-freeze §5：页面私有词汇固定为 idle/loading/ready/empty/failed）。
 */
import { reactive } from "vue";
import type { InjectionKey } from "vue";
import { http, type ApiError, type ApiResult, type HttpClient } from "@/api/http";
import {
  ACTIVITY_PAGE_LIMIT,
  createActivity,
  getActivity,
  listActivities,
  type Activity,
  type CreateActivityBody,
  type ListActivitiesQuery,
} from "@/api/endpoints";
import { useWorkspaceScope, type WorkspaceScope } from "@/composables/useWorkspaceScope";
import { useSession, type SessionStore } from "@/composables/useSession";
import { normalizeActivityQuery, normalizeActivityStatus } from "@/features/activity/query";
import type { ActivitiesPhase } from "@/features/activity/viewState";

export interface ActivityRevision {
  /** 契约 Activity.revision：后续变更请求经 If-Match 带上（本页面只读，缓存供 UI-03/04 复用）。 */
  readonly revision: number;
  /** 响应 ETag 原值（含引号）；null 表示服务端未给。 */
  readonly etag: string | null;
}

export interface ActivitiesState {
  /** 当前作用域的工作区标识（来自路由 :workspace_id）；null = 尚未绑定。 */
  workspaceId: string | null;
  phase: ActivitiesPhase;
  items: Activity[];
  nextCursor: string | null;
  limit: number;
  /** 过滤：名称或编号（契约 q）。空串 = 不发送该参数。 */
  q: string;
  /** 过滤：状态（契约 status，取值限 Activity.status 枚举）。空串 = 全部状态。 */
  status: Activity["status"] | "";
  error: ApiError | null;
  creating: boolean;
  createError: ApiError | null;
  /** 409 冲突后按行内编号定位既有记录时置位（UI-02:32）；页面据此给出可见说明。 */
  locatedExternalId: string | null;
  /** 详情抽屉当前活动（getActivity 原值）；null = 未打开。 */
  detail: Activity | null;
  detailLoading: boolean;
  detailError: ApiError | null;
  lastRequestId: string | null;
}

export interface ActivitiesStore {
  readonly state: ActivitiesState;
  /** 请求缓存：activityId → { revision, etag }。 */
  readonly revisions: Record<string, ActivityRevision>;
  /** 绑定/切换工作区（路由驱动）。返回 true 表示作用域确实变了并已清场。 */
  setWorkspace(workspaceId: string | null): boolean;
  loadFirstPage(): Promise<void>;
  loadMore(): Promise<void>;
  setQuery(raw: string): Promise<void>;
  setStatus(raw: string): Promise<void>;
  /** 一次「筛选」意图只发一次请求：q 与 status 同时落定后再加载（避免两次请求互相取消）。 */
  setFilters(rawQ: string, rawStatus: string): Promise<void>;
  create(body: CreateActivityBody, idempotencyKey: string): Promise<ApiResult<Activity>>;
  /** 「进入活动」：UI-03 详情页未交付前由本页抽屉承载，数据一律取 getActivity 原值。 */
  openDetail(activityId: string): Promise<ApiResult<Activity>>;
  closeDetail(): void;
  revisionOf(activityId: string): ActivityRevision | null;
  resetForSignOut(): void;
}

export interface ActivitiesDeps {
  readonly client?: HttpClient | undefined;
  readonly scope?: WorkspaceScope | undefined;
  readonly session?: SessionStore | undefined;
}

const LIST_GATE_PREFIX = "activities:list:";
const DETAIL_GATE_PREFIX = "activities:detail:";

export function createActivitiesStore(deps: ActivitiesDeps = {}): ActivitiesStore {
  const client = deps.client ?? http;
  const scope = deps.scope ?? useWorkspaceScope();
  const session = deps.session ?? useSession();

  const state = reactive<ActivitiesState>({
    workspaceId: null,
    phase: "idle",
    items: [],
    nextCursor: null,
    limit: ACTIVITY_PAGE_LIMIT,
    q: "",
    status: "",
    error: null,
    creating: false,
    createError: null,
    locatedExternalId: null,
    detail: null,
    detailLoading: false,
    detailError: null,
    lastRequestId: null,
  });
  const revisions = reactive<Record<string, ActivityRevision>>({});

  function remember(activity: Activity, etag: string | null): void {
    revisions[activity.id] = { revision: activity.revision, etag };
  }

  function touchRequestId(requestId: string): void {
    if (requestId.length > 0) state.lastRequestId = requestId;
  }

  /** 会话级失败（401/403）统一交 session store：清会话 + 清作用域 + 登记回合法入口的深链。 */
  function isSessionFailure(error: ApiError): boolean {
    return error.kind === "problem" && (error.status === 401 || error.status === 403);
  }

  /** 清空列表态（切工作区 / 登出）：本地临时筛选与详情一并清（COMMON.md:19）。 */
  function clearListState(): void {
    state.phase = "idle";
    state.items = [];
    state.nextCursor = null;
    state.q = "";
    state.status = "";
    state.error = null;
    state.creating = false;
    state.createError = null;
    state.locatedExternalId = null;
    closeDetail();
    for (const id of Object.keys(revisions)) delete revisions[id];
  }

  function finish(items: Activity[], nextCursor: string | null, append: boolean): void {
    const merged = append ? [...state.items, ...items] : items;
    const seen = new Set<string>();
    state.items = merged.filter((item) => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    });
    state.nextCursor = nextCursor;
    // 无记录单独成态，不与失败态混用（COMMON.md:28）。
    state.phase = state.items.length === 0 ? "empty" : "ready";
  }

  async function load(append: boolean): Promise<void> {
    const workspaceId = state.workspaceId;
    if (workspaceId === null) {
      // 未绑定工作区就不发请求：深链缺 :workspace_id 属路由层问题，不得拿空标识打服务端。
      state.phase = "idle";
      return;
    }
    const inflight = scope.gate.begin(LIST_GATE_PREFIX + workspaceId);
    const epoch = scope.epochOf();
    state.phase = "loading";
    state.error = null;

    const query: ListActivitiesQuery = { limit: state.limit };
    if (state.q.length > 0) query.q = state.q;
    if (state.status.length > 0) query.status = state.status;
    if (append && state.nextCursor !== null) query.cursor = state.nextCursor;

    const result = await listActivities(workspaceId, query, client);

    // 晚到响应不得覆盖当前范围：被更晚请求取代、期间切过工作区、或作用域已清场 ⇒ 一律丢弃。
    if (inflight.isStale() || scope.isStale(epoch) || state.workspaceId !== workspaceId) return;

    touchRequestId(result.ok ? result.requestId : result.error.requestId);

    if (result.ok) {
      for (const item of result.data.items) remember(item, null);
      finish(result.data.items, result.data.next_cursor, append);
      return;
    }
    if (isSessionFailure(result.error)) {
      session.signOut(result.error.code.length > 0 ? result.error.code : "ACTIVITIES_UNAUTHORIZED");
      state.phase = "idle";
      return;
    }
    state.error = result.error;
    state.phase = "failed";
  }

  async function openDetail(activityId: string): Promise<ApiResult<Activity>> {
    const workspaceId = state.workspaceId;
    if (workspaceId === null) {
      return { ok: false, error: assertionError("未绑定工作区，无法获取活动详情") };
    }
    const inflight = scope.gate.begin(DETAIL_GATE_PREFIX + activityId);
    state.detailLoading = true;
    state.detailError = null;

    const result = await getActivity(workspaceId, activityId, client);

    if (inflight.isStale() || state.workspaceId !== workspaceId) return result;

    state.detailLoading = false;
    touchRequestId(result.ok ? result.requestId : result.error.requestId);
    if (result.ok) {
      remember(result.data, result.etag);
      state.detail = result.data;
      // 详情原值回填列表行：表格与抽屉共用同一服务器结果，不得各存一份（FRONTEND.md 界面实现第 5 条）。
      state.items = state.items.map((item) => (item.id === result.data.id ? result.data : item));
      return result;
    }
    if (isSessionFailure(result.error)) {
      session.signOut(result.error.code.length > 0 ? result.error.code : "ACTIVITY_UNAUTHORIZED");
      return result;
    }
    state.detailError = result.error;
    return result;
  }

  function closeDetail(): void {
    state.detail = null;
    state.detailLoading = false;
    state.detailError = null;
  }

  async function create(body: CreateActivityBody, idempotencyKey: string): Promise<ApiResult<Activity>> {
    const workspaceId = state.workspaceId;
    if (workspaceId === null) {
      return { ok: false, error: assertionError("未绑定工作区，无法新建活动") };
    }
    state.creating = true;
    state.createError = null;
    // 幂等键由调用方按「一次用户意图一个 key」生成；409 重试必须沿原 key，不得在此重新生成。
    const result = await createActivity(workspaceId, body, { idempotencyKey, client });
    state.creating = false;
    touchRequestId(result.ok ? result.requestId : result.error.requestId);

    if (result.ok) {
      remember(result.data, result.etag);
      state.items = [result.data, ...state.items.filter((item) => item.id !== result.data.id)];
      state.phase = "ready";
      return result;
    }
    if (isSessionFailure(result.error)) {
      session.signOut(result.error.code.length > 0 ? result.error.code : "ACTIVITY_CREATE_UNAUTHORIZED");
      return result;
    }
    // 其余失败（409 / 412 / 422 / 413 …）一律保留本地输入（COMMON.md:31），由页面按分支呈现。
    state.createError = result.error;
    // UI-02:32「相同银行行内活动编号重复显示冲突并定位既有记录」：
    // 409 且草稿填了行内编号 ⇒ 以该行内编号作为 q 重新检索，把既有记录带回列表。
    const external = (body.external_activity_id ?? "").trim();
    if (result.error.status === 409 && external.length > 0) {
      state.locatedExternalId = external;
      state.q = normalizeActivityQuery(external);
      state.status = "";
      state.nextCursor = null;
      await load(false);
    }
    return result;
  }

  /** 客户端断言失败（不发请求）：与 http.ts 的 kind="assertion" 同形，供上层统一呈现。 */
  function assertionError(message: string): ApiError {
    return {
      kind: "assertion",
      status: 0,
      code: "",
      type: "",
      title: "",
      detail: message,
      requestId: "",
      issues: [],
    };
  }

  const store: ActivitiesStore = {
    state,
    revisions,
    setWorkspace(workspaceId: string | null): boolean {
      const changed = scope.setWorkspace(workspaceId, "ui-02:route");
      const previous = state.workspaceId;
      state.workspaceId = workspaceId;
      if (changed || previous !== workspaceId) {
        // 切工作区：清上一作用域的列表态、临时筛选、详情抽屉与请求缓存（COMMON.md:19）。
        clearListState();
        state.workspaceId = workspaceId;
      }
      return changed;
    },
    loadFirstPage: () => load(false),
    loadMore: () => load(true),
    async setQuery(raw: string): Promise<void> {
      state.q = normalizeActivityQuery(raw);
      state.nextCursor = null;
      state.locatedExternalId = null;
      await load(false);
    },
    async setStatus(raw: string): Promise<void> {
      state.status = normalizeActivityStatus(raw);
      state.nextCursor = null;
      await load(false);
    },
    async setFilters(rawQ: string, rawStatus: string): Promise<void> {
      state.q = normalizeActivityQuery(rawQ);
      state.status = normalizeActivityStatus(rawStatus);
      state.nextCursor = null;
      state.locatedExternalId = null;
      await load(false);
    },
    create,
    openDetail,
    closeDetail,
    revisionOf(activityId: string): ActivityRevision | null {
      return revisions[activityId] ?? null;
    },
    resetForSignOut(): void {
      state.workspaceId = null;
      clearListState();
    },
  };

  // 登出联动（观察者而非 import：session 不反向依赖 activities，避免循环）。
  session.onSignOut(() => {
    store.resetForSignOut();
  });

  return store;
}

let singleton: ActivitiesStore | null = null;

export function useActivities(): ActivitiesStore {
  if (singleton === null) singleton = createActivitiesStore();
  return singleton;
}

/** 仅供单测复位。 */
export function resetActivitiesSingleton(): void {
  singleton = null;
}

export const activitiesStoreKey: InjectionKey<ActivitiesStore> = Symbol("campaignlab.activities-store");
