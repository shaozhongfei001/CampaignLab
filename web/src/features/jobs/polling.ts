// 202 轮询的项目级唯一实现档（state.json → decisions.poll_defaults，ACCEPTED，R3-Q4 裁定）：
//   初始 1000ms、退避 ×1.5、上限 8000ms、终态 SUCCEEDED/FAILED/CANCELLED 即停。
// 纪律：全站只此一个 composable，后续作业页（UI-25 等）必须复用，禁各处自建轮询。
// UI-01 的 5 个 operationId 均不返回 202，故本页不发起轮询；本模块为 M0-03 落地的共享档。
import { onScopeDispose, reactive } from "vue";
import { http, type ApiResult, type HttpClient } from "@/api/http";
import { useWorkspaceScope, type WorkspaceScope } from "@/composables/useWorkspaceScope";

export const POLL_DEFAULTS = {
  initialIntervalMs: 1000,
  backoffFactor: 1.5,
  maxIntervalMs: 8000,
} as const;

export const TERMINAL_JOB_STATES = ["SUCCEEDED", "FAILED", "CANCELLED"] as const;
export type TerminalJobState = (typeof TERMINAL_JOB_STATES)[number];

export function isTerminalState(state: string): boolean {
  return (TERMINAL_JOB_STATES as readonly string[]).includes(state);
}

export function intervalForAttempt(attempt: number): number {
  const raw = POLL_DEFAULTS.initialIntervalMs * POLL_DEFAULTS.backoffFactor ** Math.max(attempt - 1, 0);
  return Math.min(Math.round(raw), POLL_DEFAULTS.maxIntervalMs);
}

export interface JobPollState {
  running: boolean;
  attempt: number;
  lastStatus: number | null;
  jobState: string | null;
  stoppedReason: string | null;
}

export interface JobPollOptions {
  readonly path: string;
  readonly readState: (data: unknown) => string | null;
  readonly client?: HttpClient | undefined;
  readonly scope?: WorkspaceScope | undefined;
}

export function createJobPoller(options: JobPollOptions) {
  const client = options.client ?? http;
  const state = reactive<JobPollState>({
    running: false,
    attempt: 0,
    lastStatus: null,
    jobState: null,
    stoppedReason: null,
  });
  let timer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  function stop(reason: string): void {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
    state.running = false;
    state.stoppedReason = reason;
  }

  async function tick(job: JobPollOptions): Promise<void> {
    if (disposed || !state.running) return;
    state.attempt += 1;
    const result: ApiResult<unknown> = await client.request<unknown>({
      method: "GET",
      path: job.path,
      accept: [200, 202],
    });
    if (disposed || !state.running) return;
    state.lastStatus = result.ok ? result.status : result.error.status;
    if (!result.ok) {
      if (result.error.kind === "aborted") {
        stop("aborted");
        return;
      }
    } else {
      const current = job.readState(result.data);
      state.jobState = current;
      if (current !== null && isTerminalState(current)) {
        stop("terminal:" + current);
        return;
      }
    }
    timer = setTimeout(() => {
      void tick(job);
    }, intervalForAttempt(state.attempt + 1));
  }

  return {
    state,
    start(): void {
      if (state.running || disposed) return;
      state.running = true;
      state.attempt = 0;
      state.stoppedReason = null;
      timer = setTimeout(() => {
        void tick(options);
      }, intervalForAttempt(1));
    },
    stop,
    dispose(): void {
      disposed = true;
      stop("disposed");
    },
  };
}

export type JobPoller = ReturnType<typeof createJobPoller>;

export function useJobPolling(options: JobPollOptions): JobPoller {
  const scope = options.scope ?? useWorkspaceScope();
  const poller = createJobPoller({ ...options, scope });
  const unregister = scope.register("poll", options.path, () => poller.dispose());
  onScopeDispose(() => {
    unregister();
    poller.dispose();
  });
  return poller;
}
