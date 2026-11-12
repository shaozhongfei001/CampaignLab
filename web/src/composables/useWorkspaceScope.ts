/**
 * web/src/composables/useWorkspaceScope.ts —— 「切工作区清理策略」的唯一实现
 *
 * 依据：
 *   - FRONTEND.md:12 深链带工作区标识，切工作区必须回到合法入口；
 *   - FRONTEND.md:13 用 abort 或请求序列保护晚到响应覆盖当前范围，路由离开后释放图表与轮询定时器；
 *   - UI-01 页面状态：「切换后清除上一个工作区的草稿范围和轮询」；
 *   - M0-03-design.md §6 把清理策略列为 S5 交付项。
 *
 * 模型：工作区作用域 = (workspaceId, epoch, 资源表)。
 *   - epoch 单调递增；任何在 epoch 变更前发出的请求/轮询，回来后一律判为 stale 并丢弃；
 *   - 资源表按 kind 登记轮询、临时查询、失效选择、草稿、图表、事件监听，切换即 dispose；
 *   - 绑定 workspaceId === null 的资源是「全局资源」，不随切换清理（只随 clear() 显式释放）；
 *   - gate（RequestGate）与 epoch 配套：cancelAll() 中止在飞请求，token 全部转 stale。
 *
 * Q5 裁定：不引入 Pinia，状态用 Vue 原生 reactive + 单例 composable 承载。
 */
import { reactive } from "vue";
import type { InjectionKey } from "vue";
import { createRequestGate, systemClock, type HttpClock, type RequestGate } from "@/api/http";

/** 资源类别：证据与调试可读，且与 COMMON.md 的「临时查询/轮询/失效选择」用词对齐。 */
export type ScopeResourceKind = "poll" | "temp-query" | "selection" | "draft" | "chart" | "listener";

export interface ScopeResourceInfo {
  readonly id: number;
  readonly kind: ScopeResourceKind;
  readonly label: string;
  /** null = 全局资源（不随工作区切换清理）。 */
  readonly workspaceId: string | null;
}

interface ScopeResource extends ScopeResourceInfo {
  dispose(): void;
}

export interface WorkspaceScopeState {
  workspaceId: string | null;
  epoch: number;
  resourceCount: number;
  lastClearReason: string | null;
  /** 证据时标（注入时钟）；不得用于任何业务过期推算。 */
  lastClearedAt: number | null;
}

export interface WorkspaceScope {
  readonly state: WorkspaceScopeState;
  readonly gate: RequestGate;
  /** 登记一个作用域资源，返回注销函数（组件卸载时调用，避免泄漏）。 */
  register(kind: ScopeResourceKind, label: string, dispose: () => void): () => void;
  /** 证据用快照：不含 dispose 闭包。 */
  list(): ScopeResourceInfo[];
  /**
   * 切换工作区。id 与当前相同 → 不做任何清理并返回 false（刷新/深链回到同一工作区不得清场）；
   * 不同 → dispose 上一个工作区的资源、gate.cancelAll()、epoch+1，返回 true。
   */
  setWorkspace(id: string | null, reason?: string): boolean;
  /** 显式清场（登出、会话过期、404 回入口）：连同全局资源一起释放。 */
  clear(reason: string): void;
  isStale(epoch: number): boolean;
  epochOf(): number;
}

export interface WorkspaceScopeDeps {
  readonly gate?: RequestGate | undefined;
  readonly clock?: HttpClock | undefined;
}

export function createWorkspaceScope(deps: WorkspaceScopeDeps = {}): WorkspaceScope {
  const clock = deps.clock ?? systemClock;
  const gate = deps.gate ?? createRequestGate();
  const state = reactive<WorkspaceScopeState>({
    workspaceId: null,
    epoch: 0,
    resourceCount: 0,
    lastClearReason: null,
    lastClearedAt: null,
  });

  // 资源表刻意不进 reactive：里面是闭包，代理化只会增加开销与栈深；对外只暴露 resourceCount。
  let resources: ScopeResource[] = [];
  let nextId = 1;

  function sync(): void {
    state.resourceCount = resources.length;
  }

  function disposeMatching(predicate: (resource: ScopeResource) => boolean): number {
    const kept: ScopeResource[] = [];
    let disposed = 0;
    for (const resource of resources) {
      if (predicate(resource)) {
        disposed += 1;
        try {
          resource.dispose();
        } catch {
          // dispose 失败不得阻断其余资源释放：清理是幂等义务，不是事务。
        }
      } else {
        kept.push(resource);
      }
    }
    resources = kept;
    sync();
    return disposed;
  }

  return {
    state,
    gate,
    register(kind: ScopeResourceKind, label: string, dispose: () => void): () => void {
      const resource: ScopeResource = { id: nextId, kind, label, workspaceId: state.workspaceId, dispose };
      nextId += 1;
      resources = [...resources, resource];
      sync();
      return () => {
        disposeMatching((item) => item.id === resource.id);
      };
    },
    list(): ScopeResourceInfo[] {
      return resources.map(({ id, kind, label, workspaceId }) => ({ id, kind, label, workspaceId }));
    },
    setWorkspace(id: string | null, reason = "workspace:switch"): boolean {
      if (id === state.workspaceId) return false;
      // 先中止在飞请求，再 dispose 资源，最后推进 epoch：
      // 顺序保证 dispose 里触发的最后一次回调仍被判为 stale，不会写回新作用域。
      gate.cancelAll();
      const previous = state.workspaceId;
      disposeMatching((resource) => resource.workspaceId !== null && resource.workspaceId === previous);
      state.workspaceId = id;
      state.epoch += 1;
      state.lastClearReason = reason;
      state.lastClearedAt = clock.now();
      return true;
    },
    clear(reason: string): void {
      gate.cancelAll();
      disposeMatching(() => true);
      state.workspaceId = null;
      state.epoch += 1;
      state.lastClearReason = reason;
      state.lastClearedAt = clock.now();
    },
    isStale(epoch: number): boolean {
      return epoch !== state.epoch;
    },
    epochOf(): number {
      return state.epoch;
    },
  };
}

let singleton: WorkspaceScope | null = null;

/** 单例（Q5：reactive + composable 单例，不引入 stores 层）。 */
export function useWorkspaceScope(): WorkspaceScope {
  if (singleton === null) singleton = createWorkspaceScope();
  return singleton;
}

/** 仅供单测复位；生产代码不得调用（S6/S8 不要接线到 UI 上）。 */
export function resetWorkspaceScopeSingleton(): void {
  if (singleton !== null) singleton.clear("test:reset");
  singleton = null;
}

export const workspaceScopeKey: InjectionKey<WorkspaceScope> = Symbol("campaignlab.workspace-scope");
