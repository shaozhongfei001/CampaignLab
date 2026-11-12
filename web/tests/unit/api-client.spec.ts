/**
 * web/tests/unit/api-client.spec.ts —— S5 API 客户端与 store 骨架的**纯逻辑**单测
 *
 * 环境纪律：vitest environment 固定 "node"（裁定 Q-S3-F；未决问题 Q1）。
 * 本文件不触碰 document / window / getComputedStyle —— 需要 DOM 的断言归 S8。
 *
 * 归属边界：这里只断言 S5 交付的「接口签名 + 错误映射 + ETag/幂等 + 切工作区清理 + 晚到响应保护」。
 * AC-001 页面断言与页面侧深链断言（framework/FRONTEND.md:12，非 AC-034）属 S8，不在本文件。
 *
 * fetch 全部注入替身：不发真实网络请求，不依赖 Node 的 undici 行为差异。
 */
import { describe, expect, it } from "vitest";
import {
  IDEMPOTENCY_KEY_MAX_LENGTH,
  IDEMPOTENCY_KEY_MIN_LENGTH,
  JSON_BODY_LIMIT_BYTES,
  PROBLEM_TYPE_PREFIX,
  createHttpClient,
  createRequestGate,
  isValidIdempotencyKey,
  jsonBodyBytes,
  newIdempotencyKey,
  type ApiError,
  type ApiOk,
  type ApiResult,
  type HttpClientConfig,
} from "@/api/http";
import type { Health, Session, Workspace, WorkspacePage } from "@/api/endpoints";
import { createSessionStore } from "@/composables/useSession";
import { createWorkspaceScope } from "@/composables/useWorkspaceScope";
import { createWorkspacesStore } from "@/composables/useWorkspaces";

/* ------------------------------------------------------------------ 替身基础设施 */

interface RecordedCall {
  readonly url: string;
  readonly method: string;
  readonly headers: Record<string, string>;
  readonly body: string | undefined;
  readonly credentials: string | undefined;
  readonly signal: AbortSignal | null | undefined;
}

interface FakeResponseInit {
  readonly status: number;
  readonly body?: string | undefined;
  readonly headers?: Record<string, string> | undefined;
}

function fakeResponse(init: FakeResponseInit): Response {
  const headers = new Map<string, string>();
  for (const [name, value] of Object.entries(init.headers ?? {})) headers.set(name.toLowerCase(), value);
  const body = init.body ?? "";
  return {
    status: init.status,
    ok: init.status >= 200 && init.status < 300,
    url: "",
    headers: {
      get: (name: string) => headers.get(name.toLowerCase()) ?? null,
      has: (name: string) => headers.has(name.toLowerCase()),
    },
    text: async (): Promise<string> => body,
  } as unknown as Response;
}

function problemBody(code: string, status: number, overrides: Record<string, unknown> = {}): string {
  return JSON.stringify({
    type: PROBLEM_TYPE_PREFIX + code.toLowerCase(),
    title: "服务端标题 " + code,
    status,
    code,
    detail: "服务端详情 " + code,
    request_id: "rid-" + code,
    issues: [],
    ...overrides,
  });
}

function recordCall(input: RequestInfo | URL, init: RequestInit | undefined, calls: RecordedCall[]): RecordedCall {
  const headers: Record<string, string> = {};
  const raw = init?.headers;
  if (raw !== undefined && raw !== null && typeof raw === "object" && !Array.isArray(raw)) {
    for (const [name, value] of Object.entries(raw as Record<string, string>)) headers[name] = value;
  }
  const call: RecordedCall = {
    url: String(input),
    method: init?.method ?? "GET",
    headers,
    body: typeof init?.body === "string" ? init.body : undefined,
    credentials: init?.credentials,
    signal: init?.signal,
  };
  calls.push(call);
  return call;
}

type Responder = (call: RecordedCall, index: number) => Response | Promise<Response>;

function makeClient(responder: Responder, config: HttpClientConfig = {}) {
  const calls: RecordedCall[] = [];
  const fetchImpl = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> =>
    responder(recordCall(input, init, calls), calls.length - 1);
  return { client: createHttpClient({ fetchImpl, ...config }), calls };
}

interface PendingCall {
  readonly call: RecordedCall;
  resolve(response: Response): void;
}

function makeDeferredClient(config: HttpClientConfig = {}) {
  const calls: RecordedCall[] = [];
  const pending: PendingCall[] = [];
  const fetchImpl = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> =>
    new Promise<Response>((resolve) => {
      pending.push({ call: recordCall(input, init, calls), resolve });
    });
  return { client: createHttpClient({ fetchImpl, ...config }), calls, pending };
}

function expectOk<T>(result: ApiResult<T>): ApiOk<T> {
  if (!result.ok) throw new Error("期望成功，实际失败：" + result.error.kind + "/" + result.error.status);
  return result;
}

function expectFailure<T>(result: ApiResult<T>): ApiError {
  if (result.ok) throw new Error("期望失败，实际成功：status=" + result.status);
  return result.error;
}

function abortError(): Error {
  const error = new Error("The operation was aborted");
  error.name = "AbortError";
  return error;
}

function workspace(id: string, name: string, revision: number): Workspace {
  return {
    id,
    revision,
    created_at: "2026-11-13T09:00:00+08:00",
    name,
    source_class: "SYNTHETIC",
    authorization_note: null,
  };
}

function page(items: Workspace[], nextCursor: string | null): string {
  const body: WorkspacePage = { items, next_cursor: nextCursor };
  return JSON.stringify(body);
}

const sessionBody: Session = { actor_id: "op-1", actor_name: "本机操作员", allowed_roles: ["OPERATOR"] };

/* ------------------------------------------------------------------ 用例 */

describe("API 客户端：Problem → ApiError 单一映射（ADR-005 §2.1/§2.2）", () => {
  it("401 Problem 全字段原样映射；X-Request-Id 头优先于正文 request_id", async () => {
    const { client } = makeClient(() =>
      fakeResponse({
        status: 401,
        body: problemBody("SESSION_EXPIRED", 401),
        headers: { "X-Request-Id": "rid-header", "Content-Type": "application/problem+json" },
      }),
    );
    const error = expectFailure(await client.request<Session>({ method: "GET", path: "/session" }));
    expect(error.kind).toBe("problem");
    expect(error.status).toBe(401);
    expect(error.code).toBe("SESSION_EXPIRED");
    expect(error.type).toBe("urn:campaignlab:problem:session_expired");
    expect(error.title).toBe("服务端标题 SESSION_EXPIRED");
    expect(error.detail).toBe("服务端详情 SESSION_EXPIRED");
    expect(error.requestId).toBe("rid-header");
    expect(error.issues).toEqual([]);
  });

  it("type 与 code 不一致时以 code 为准，并把断言写进水槽（不 console、不抛出）", async () => {
    const { client } = makeClient(() =>
      fakeResponse({
        status: 422,
        body: problemBody("VALIDATION_FAILED", 422, { type: "urn:campaignlab:problem:WRONG_CODE" }),
      }),
    );
    const error = expectFailure(await client.request<WorkspacePage>({ method: "GET", path: "/workspaces" }));
    expect(error.code).toBe("VALIDATION_FAILED");
    expect(error.type).toBe("urn:campaignlab:problem:WRONG_CODE");
    expect(client.devAssertions().some((line) => line.includes("不一致"))).toBe(true);
    // drain 语义：返回被取走的条目并清空水槽（生产环境水槽不得无界增长）。
    expect(client.drainDevAssertions()).toHaveLength(1);
    expect(client.devAssertions()).toEqual([]);
  });

  it("非 Problem 正文 → kind=transport、title 留空（前端不得另编文案）", async () => {
    const { client } = makeClient(() => fakeResponse({ status: 502, body: "<html>bad gateway</html>" }));
    const error = expectFailure(await client.request<Health>({ method: "GET", path: "/health" }));
    expect(error.kind).toBe("transport");
    expect(error.status).toBe(502);
    expect(error.title).toBe("");
    expect(error.code).toBe("");
  });

  it("issues[] 逐条校验：残缺条目丢弃，合法条目保留 location/severity", async () => {
    const { client } = makeClient(() =>
      fakeResponse({
        status: 422,
        body: problemBody("VALIDATION_FAILED", 422, {
          issues: [
            { code: "REQUIRED", location: "name", message: "名称必填", severity: "ERROR" },
            { code: "BROKEN", location: "source_class" },
            { code: "BAD_SEVERITY", location: "q", message: "x", severity: "FATAL" },
          ],
        }),
      }),
    );
    const error = expectFailure(await client.request<Workspace>({ method: "POST", path: "/workspaces" }));
    expect(error.issues).toEqual([{ code: "REQUIRED", location: "name", message: "名称必填", severity: "ERROR" }]);
  });

  it("网络异常 → transport + cause；AbortError → aborted（切工作区/路由离开）", async () => {
    const network = makeClient(() => {
      throw new TypeError("fetch failed");
    });
    const transport = expectFailure(await network.client.request<Health>({ method: "GET", path: "/health" }));
    expect(transport.kind).toBe("transport");
    expect(transport.status).toBe(0);
    expect(transport.cause ?? "").toContain("fetch failed");

    const aborted = makeClient(() => {
      throw abortError();
    });
    const controller = new AbortController();
    controller.abort();
    const error = expectFailure(
      await aborted.client.request<Health>({ method: "GET", path: "/health", signal: controller.signal }),
    );
    expect(error.kind).toBe("aborted");
  });
});

describe("API 客户端：ETag / If-Match / Idempotency-Key / 1 MiB 预检 / 429 退避", () => {
  it("响应 ETag 入请求缓存；变更请求按 ifMatch 上送 If-Match", async () => {
    const { client, calls } = makeClient((_call, index) =>
      index === 0
        ? fakeResponse({ status: 200, body: JSON.stringify(sessionBody), headers: { ETag: '"rev-7"' } })
        : fakeResponse({ status: 200, body: JSON.stringify(sessionBody), headers: {} }),
    );
    const first = expectOk(await client.request<Session>({ method: "GET", path: "/session" }));
    expect(first.etag).toBe('"rev-7"');
    const key = client.keyOf({ method: "GET", path: "/session" });
    expect(client.etagFor(key)).toBe('"rev-7"');

    await client.request<Session>({ method: "POST", path: "/session/exchange", body: { token: "t" }, ifMatch: client.etagFor(key) ?? undefined });
    const second = calls[1];
    expect(second?.headers["If-Match"]).toBe('"rev-7"');
    expect(second?.headers["Accept"]).toBe("application/json");
    expect(second?.credentials).toBe("include");
  });

  it("412 REVISION_CONFLICT 原样透传（UI 呈现新旧 revision 并保留输入）", async () => {
    const { client } = makeClient(() => fakeResponse({ status: 412, body: problemBody("REVISION_CONFLICT", 412) }));
    const error = expectFailure(await client.request<Workspace>({ method: "POST", path: "/workspaces" }));
    expect(error.status).toBe(412);
    expect(error.code).toBe("REVISION_CONFLICT");
    expect(error.kind).toBe("problem");
  });

  it("Idempotency-Key：合法则上送；非法或缺失即不发请求并记断言", async () => {
    const ok = makeClient(() => fakeResponse({ status: 201, body: JSON.stringify(workspace("ws-a", "甲", 1)), headers: { ETag: '"rev-1"' } }));
    const created = expectOk(
      await ok.client.request<Workspace>({
        method: "POST",
        path: "/workspaces",
        body: { name: "甲", source_class: "SYNTHETIC" },
        idempotencyKey: newIdempotencyKey("ws-create"),
        requireIdempotencyKey: true,
        accept: [201],
      }),
    );
    expect(created.etag).toBe('"rev-1"');
    expect(ok.calls[0]?.headers["Idempotency-Key"]).toMatch(/^ws-create-/);

    const bad = makeClient(() => fakeResponse({ status: 201, body: "{}" }));
    const shortKey = expectFailure(
      await bad.client.request<Workspace>({ method: "POST", path: "/workspaces", idempotencyKey: "abc" }),
    );
    expect(shortKey.kind).toBe("assertion");
    expect(bad.calls).toHaveLength(0);

    const missing = expectFailure(
      await bad.client.request<Workspace>({ method: "POST", path: "/workspaces", requireIdempotencyKey: true }),
    );
    expect(missing.kind).toBe("assertion");
    expect(bad.calls).toHaveLength(0);

    const noIfMatch = expectFailure(
      await bad.client.request<Workspace>({ method: "PATCH", path: "/workspaces", requireIfMatch: true }),
    );
    expect(noIfMatch.kind).toBe("assertion");
    expect(bad.calls).toHaveLength(0);
  });

  it("newIdempotencyKey 满足契约 8..128 且 500 次不重复", () => {
    const seen = new Set<string>();
    for (let i = 0; i < 500; i += 1) {
      const key = newIdempotencyKey("ws-create");
      expect(isValidIdempotencyKey(key)).toBe(true);
      expect(key.length).toBeGreaterThanOrEqual(IDEMPOTENCY_KEY_MIN_LENGTH);
      expect(key.length).toBeLessThanOrEqual(IDEMPOTENCY_KEY_MAX_LENGTH);
      seen.add(key);
    }
    expect(seen.size).toBe(500);
    expect(isValidIdempotencyKey("ab cdefgh")).toBe(false);
    expect(isValidIdempotencyKey("x".repeat(IDEMPOTENCY_KEY_MAX_LENGTH + 1))).toBe(false);
  });

  it("JSON 正文超 1 MiB 上限：请求不发出，kind=payload 且给出实算字节", async () => {
    expect(JSON_BODY_LIMIT_BYTES).toBe(1048576);
    const body = { name: "超限".repeat(64), source_class: "SYNTHETIC" };
    const { client, calls } = makeClient(() => fakeResponse({ status: 201, body: "{}" }), { maxJsonBodyBytes: 16 });
    const error = expectFailure(await client.request<Workspace>({ method: "POST", path: "/workspaces", body }));
    expect(error.kind).toBe("payload");
    expect(error.status).toBe(0);
    expect(error.payload?.actualBytes).toBe(jsonBodyBytes(body));
    expect(error.payload?.limitBytes).toBe(16);
    expect(calls).toHaveLength(0);
  });

  it("429 指数退避 1s/2s/4s；耗尽后透传服务端 Problem", async () => {
    const slept: number[] = [];
    const recovering = makeClient(
      (_call, index) =>
        index < 3
          ? fakeResponse({ status: 429, body: problemBody("RATE_LIMITED", 429) })
          : fakeResponse({ status: 200, body: JSON.stringify(sessionBody) }),
      { sleep: async (ms: number) => void slept.push(ms) },
    );
    const ok = expectOk(await recovering.client.request<Session>({ method: "GET", path: "/session" }));
    expect(ok.status).toBe(200);
    expect(slept).toEqual([1000, 2000, 4000]);
    expect(recovering.calls).toHaveLength(4);

    const exhausted: number[] = [];
    const stuck = makeClient(() => fakeResponse({ status: 429, body: problemBody("RATE_LIMITED", 429) }), {
      sleep: async (ms: number) => void exhausted.push(ms),
    });
    const error = expectFailure(await stuck.client.request<Session>({ method: "GET", path: "/session" }));
    expect(error.code).toBe("RATE_LIMITED");
    expect(error.title).toBe("服务端标题 RATE_LIMITED");
    expect(exhausted).toEqual([1000, 2000, 4000]);
  });
});

describe("API 客户端：202 轮询骨架与请求序列闸门", () => {
  it("202→202→200 落地并记满 onAttempt；耗尽上限 → kind=timeout", async () => {
    const slept: number[] = [];
    const attempts: number[] = [];
    const settling = makeClient(
      (_call, index) =>
        index < 2
          ? fakeResponse({ status: 202, body: JSON.stringify({ accepted: true }) })
          : fakeResponse({ status: 200, body: JSON.stringify({ done: true }) }),
      { sleep: async (ms: number) => void slept.push(ms), pollIntervalMs: 40 },
    );
    const settled = expectOk(
      await settling.client.poll<{ done: boolean }>({
        path: "/jobs/job-1",
        settled: (status) => status === 200,
        onAttempt: ({ attempt }) => void attempts.push(attempt),
      }),
    );
    expect(settled.data.done).toBe(true);
    expect(attempts).toEqual([1, 2, 3]);
    expect(slept).toEqual([40, 40]);

    const stuckAttempts: number[] = [];
    const stuck = makeClient(() => fakeResponse({ status: 202, body: "{}" }), {
      sleep: async () => undefined,
      pollMaxAttempts: 3,
    });
    const timeout = expectFailure(
      await stuck.client.poll({ path: "/jobs/job-2", settled: (status) => status === 200, onAttempt: ({ attempt }) => void stuckAttempts.push(attempt) }),
    );
    expect(timeout.kind).toBe("timeout");
    expect(stuckAttempts).toEqual([1, 2, 3]);
  });

  it("RequestGate：更晚请求使旧 token 转 stale 并 abort 旧 signal；cancelAll 清空在飞", () => {
    const gate = createRequestGate();
    const first = gate.begin("list");
    const second = gate.begin("list");
    expect(first.isStale()).toBe(true);
    expect(second.isStale()).toBe(false);
    expect(gate.isCurrent("list", second.token)).toBe(true);
    expect(first.signal.aborted).toBe(true);
    expect(gate.inflightCount()).toBe(1);
    gate.cancelAll();
    expect(second.signal.aborted).toBe(true);
    expect(gate.inflightCount()).toBe(0);
    // cancelAll 后 token 一律转 stale：被取消请求的 aborted 结果不得写回 store（否则切工作区闪一条假错误）。
    expect(second.isStale()).toBe(true);
  });
});
describe("切工作区清理策略（useWorkspaceScope）", () => {
  it("切换只释放上一工作区的资源，全局资源保留，epoch 递增，在飞请求被中止", () => {
    const disposed: string[] = [];
    const scope = createWorkspaceScope({ clock: { now: () => 1763000000000 } });

    scope.register("listener", "app:listener", () => disposed.push("global"));
    expect(scope.setWorkspace("ws-a")).toBe(true);
    scope.register("poll", "activity:poll", () => disposed.push("poll-a"));
    scope.register("draft", "activity:draft", () => disposed.push("draft-a"));
    scope.register("temp-query", "activity:query", () => disposed.push("query-a"));
    const inflight = scope.gate.begin("activity:list");

    expect(scope.setWorkspace("ws-b")).toBe(true);
    expect(disposed.sort()).toEqual(["draft-a", "poll-a", "query-a"]);
    expect(inflight.isStale()).toBe(true);
    expect(inflight.signal.aborted).toBe(true);
    expect(scope.state.epoch).toBe(2);
    expect(scope.isStale(1)).toBe(true);
    expect(scope.state.workspaceId).toBe("ws-b");
    expect(scope.state.lastClearReason).toBe("workspace:switch");
    expect(scope.list().map((item) => item.label)).toEqual(["app:listener"]);
  });

  it("同一工作区重复 setWorkspace 不清场（刷新/深链回到同一工作区不得丢草稿）", () => {
    const disposed: string[] = [];
    const scope = createWorkspaceScope();
    scope.setWorkspace("ws-a");
    scope.register("draft", "draft", () => disposed.push("draft"));
    const epoch = scope.epochOf();
    expect(scope.setWorkspace("ws-a")).toBe(false);
    expect(scope.epochOf()).toBe(epoch);
    expect(disposed).toEqual([]);
    expect(scope.state.resourceCount).toBe(1);
  });

  it("注销函数只移除自己；clear 释放全部资源（含全局）并回到无工作区态", () => {
    const disposed: string[] = [];
    const scope = createWorkspaceScope();
    scope.setWorkspace("ws-a");
    const off = scope.register("poll", "poll-1", () => disposed.push("poll-1"));
    scope.register("poll", "poll-2", () => disposed.push("poll-2"));
    scope.register("listener", "global", () => disposed.push("global"));
    expect(scope.state.resourceCount).toBe(3);

    off();
    expect(disposed).toEqual(["poll-1"]);
    expect(scope.state.resourceCount).toBe(2);

    scope.clear("session:sign-out");
    expect(disposed.sort()).toEqual(["global", "poll-1", "poll-2"]);
    expect(scope.state.resourceCount).toBe(0);
    expect(scope.state.workspaceId).toBeNull();
    expect(scope.state.lastClearReason).toBe("session:sign-out");
  });

  it("dispose 抛错不得阻断其余资源释放（清理是幂等义务，不是事务）", () => {
    const disposed: string[] = [];
    const scope = createWorkspaceScope();
    scope.setWorkspace("ws-a");
    scope.register("poll", "bad", () => {
      throw new Error("dispose 失败");
    });
    scope.register("poll", "good", () => disposed.push("good"));
    expect(scope.setWorkspace("ws-b")).toBe(true);
    expect(disposed).toEqual(["good"]);
    expect(scope.state.resourceCount).toBe(0);
  });
});

describe("会话 store（useSession）", () => {
  it("入口令牌只用一次：第二次 bootstrap 走会话检查而不是重复换取", async () => {
    const paths: string[] = [];
    const { client } = makeClient((call) => {
      paths.push(new URL(call.url, "http://local.test").pathname);
      return call.url.includes("/session/exchange")
        ? fakeResponse({ status: 200, body: JSON.stringify(sessionBody), headers: { "X-Request-Id": "rid-ex" } })
        : fakeResponse({ status: 200, body: JSON.stringify(sessionBody), headers: { "X-Request-Id": "rid-get" } });
    });
    const store = createSessionStore({ client, scope: createWorkspaceScope() });

    expect(await store.bootstrap("entry-token-1")).toBe("active");
    expect(store.state.entryTokenUsed).toBe(true);
    expect(store.state.session?.actor_name).toBe("本机操作员");
    expect(store.state.lastRequestId).toBe("rid-ex");
    expect(store.hasRole("OPERATOR")).toBe(true);
    expect(store.hasRole("REVIEWER")).toBe(false);

    expect(await store.bootstrap("entry-token-1")).toBe("active");
    expect(paths).toEqual(["/session/exchange", "/session"]);
  });

  it("401 → 清会话、清作用域、保住深链；takeRedirect 一次性消费后兜底合法入口", async () => {
    const scope = createWorkspaceScope();
    const disposed: string[] = [];
    scope.setWorkspace("ws-a");
    scope.register("poll", "poll", () => disposed.push("poll"));
    const { client } = makeClient(() => fakeResponse({ status: 401, body: problemBody("SESSION_EXPIRED", 401) }));
    const store = createSessionStore({ client, scope });

    store.captureRedirect("/w/ws-a/activities?status=OPEN");
    expect(await store.bootstrap(null)).toBe("anonymous");
    expect(store.state.session).toBeNull();
    expect(store.state.error?.code).toBe("SESSION_EXPIRED");
    expect(store.state.error?.title).toBe("服务端标题 SESSION_EXPIRED");
    expect(disposed).toEqual(["poll"]);
    expect(scope.state.workspaceId).toBeNull();
    expect(store.state.pendingRedirect).toBe("/w/ws-a/activities?status=OPEN");
    expect(store.takeRedirect()).toBe("/w/ws-a/activities?status=OPEN");
    expect(store.takeRedirect()).toBeNull();
  });

  it("403（会话/Host/Origin 级）→ 强制回合法入口 /，不保留深链", async () => {
    const { client } = makeClient(() => fakeResponse({ status: 403, body: problemBody("ORIGIN_NOT_ALLOWED", 403) }));
    const store = createSessionStore({ client, scope: createWorkspaceScope() });
    store.captureRedirect("/w/ws-a/activities");
    expect(await store.bootstrap(null)).toBe("anonymous");
    expect(store.state.pendingRedirect).toBe("/");
    expect(store.state.lastSignOutReason).toBe("ORIGIN_NOT_ALLOWED");
  });

  it("captureRedirect 拒绝外链与协议相对地址（开放重定向防护）", () => {
    const store = createSessionStore({
      client: makeClient(() => fakeResponse({ status: 200, body: JSON.stringify(sessionBody) })).client,
      scope: createWorkspaceScope(),
    });
    store.captureRedirect("https://evil.example/steal");
    expect(store.state.pendingRedirect).toBe("/");
    store.captureRedirect("//evil.example/steal");
    expect(store.state.pendingRedirect).toBe("/");
    store.captureRedirect("/w/ws-a/activities");
    expect(store.state.pendingRedirect).toBe("/w/ws-a/activities");
  });

  it("非会话级失败（500）→ phase=failed，不清会话也不改深链", async () => {
    const { client } = makeClient(() => fakeResponse({ status: 500, body: problemBody("INTERNAL", 500) }));
    const store = createSessionStore({ client, scope: createWorkspaceScope() });
    store.captureRedirect("/w/ws-a");
    expect(await store.bootstrap(null)).toBe("failed");
    expect(store.state.pendingRedirect).toBe("/w/ws-a");
    expect(store.state.error?.requestId).toBe("rid-INTERNAL");
  });
});

describe("工作区 store（useWorkspaces）", () => {
  function harness() {
    const scope = createWorkspaceScope();
    const sessionClient = makeClient(() => fakeResponse({ status: 200, body: JSON.stringify(sessionBody) })).client;
    const session = createSessionStore({ client: sessionClient, scope });
    return { scope, session };
  }

  it("晚到的列表响应不得覆盖当前范围（FRONTEND.md:13）", async () => {
    const { scope, session } = harness();
    const { client, pending, calls } = makeDeferredClient();
    const store = createWorkspacesStore({ client, scope, session });

    const first = store.loadFirstPage();
    const second = store.setQuery("甲");
    expect(pending).toHaveLength(2);
    expect(calls[1]?.url).toContain("q=%E7%94%B2");

    pending[1]?.resolve(fakeResponse({ status: 200, body: page([workspace("ws-b", "乙", 1)], null) }));
    pending[0]?.resolve(fakeResponse({ status: 200, body: page([workspace("ws-a", "甲", 1)], null) }));
    await Promise.all([first, second]);

    expect(store.state.items.map((item) => item.id)).toEqual(["ws-b"]);
    expect(store.state.phase).toBe("ready");
    expect(store.state.error).toBeNull();
  });

  it("Health.worker=OFFLINE 或 status=DEGRADED → workerRestricted（作业受限）", async () => {
    const { scope, session } = harness();
    const cases: Array<[Health, boolean]> = [
      [{ status: "READY", app_version: "1.0.1", contract_version: "1.0.1", worker: "READY", schema_revision: "1" }, false],
      [{ status: "DEGRADED", app_version: "1.0.1", contract_version: "1.0.1", worker: "READY", schema_revision: "1" }, true],
      [{ status: "READY", app_version: "1.0.1", contract_version: "1.0.1", worker: "OFFLINE", schema_revision: "1" }, true],
    ];
    for (const [health, expected] of cases) {
      const { client } = makeClient(() => fakeResponse({ status: 200, body: JSON.stringify(health) }));
      const store = createWorkspacesStore({ client, scope, session });
      expectOk(await store.refreshHealth());
      expect(store.state.workerRestricted).toBe(expected);
    }
  });

  it("列表 401 → 联动登出：清空列表态与请求缓存，phase 回 idle", async () => {
    const { scope, session } = harness();
    const ready = makeClient(() => fakeResponse({ status: 200, body: page([workspace("ws-a", "甲", 3)], null) }));
    const store = createWorkspacesStore({ client: ready.client, scope, session });
    await store.loadFirstPage();
    expect(store.state.items).toHaveLength(1);
    expect(store.revisionOf("ws-a")).toEqual({ revision: 3, etag: null });

    const expired = makeClient(() => fakeResponse({ status: 401, body: problemBody("SESSION_EXPIRED", 401) }));
    const store2 = createWorkspacesStore({ client: expired.client, scope, session });
    await store2.loadFirstPage();
    expect(store2.state.phase).toBe("idle");
    expect(store2.state.items).toEqual([]);
    expect(session.state.phase).toBe("anonymous");
    // 错误归 session store 呈现的是它自己请求到的 Problem；由 workspaces 联动登出时落在 lastSignOutReason。
    expect(session.state.lastSignOutReason).toBe("SESSION_EXPIRED");
    expect(store.state.items).toEqual([]);
  });

  it("空结果 → phase=empty（UI-01：无工作区时突出创建），与失败态不混用", async () => {
    const { scope, session } = harness();
    const { client } = makeClient(() => fakeResponse({ status: 200, body: page([], null) }));
    const store = createWorkspacesStore({ client, scope, session });
    await store.loadFirstPage();
    expect(store.state.phase).toBe("empty");
    expect(store.state.error).toBeNull();
  });

  it("create：成功写入 revision+ETag 并置顶；失败保留输入且不擅清表单", async () => {
    const { scope, session } = harness();
    const { client, calls } = makeClient(() =>
      fakeResponse({ status: 201, body: JSON.stringify(workspace("ws-new", "新工作区", 1)), headers: { ETag: '"rev-1"' } }),
    );
    const store = createWorkspacesStore({ client, scope, session });
    store.state.items = [workspace("ws-a", "甲", 2)];
    const key = newIdempotencyKey("ws-create");
    const created = expectOk(await store.create({ name: "新工作区", source_class: "SYNTHETIC" }, key));
    expect(created.status).toBe(201);
    expect(store.revisionOf("ws-new")).toEqual({ revision: 1, etag: '"rev-1"' });
    expect(store.state.items.map((item) => item.id)).toEqual(["ws-new", "ws-a"]);
    expect(store.state.creating).toBe(false);
    expect(calls[0]?.headers["Idempotency-Key"]).toBe(key);
    expect(JSON.parse(calls[0]?.body ?? "{}")).toEqual({ name: "新工作区", source_class: "SYNTHETIC" });

    const conflict = makeClient(() => fakeResponse({ status: 409, body: problemBody("IDEMPOTENCY_CONFLICT", 409) }));
    const store2 = createWorkspacesStore({ client: conflict.client, scope, session });
    const error = expectFailure(await store2.create({ name: "新工作区", source_class: "SYNTHETIC" }, key));
    expect(error.code).toBe("IDEMPOTENCY_CONFLICT");
    expect(store2.state.createError?.code).toBe("IDEMPOTENCY_CONFLICT");
    expect(conflict.calls[0]?.headers["Idempotency-Key"]).toBe(key);
  });

  it("select 切换工作区：清请求缓存并驱动作用域清理；同 id 重复 select 不清", async () => {
    const { scope, session } = harness();
    const disposed: string[] = [];
    const { client } = makeClient(() => fakeResponse({ status: 200, body: page([workspace("ws-a", "甲", 3)], null) }));
    const store = createWorkspacesStore({ client, scope, session });
    await store.loadFirstPage();
    store.select("ws-a");
    scope.register("poll", "ws-a-poll", () => disposed.push("ws-a-poll"));
    expect(store.revisionOf("ws-a")).toEqual({ revision: 3, etag: null });

    expect(store.select("ws-b")).toBe(true);
    expect(store.state.selectedId).toBe("ws-b");
    expect(store.revisionOf("ws-a")).toBeNull();
    expect(disposed).toEqual(["ws-a-poll"]);

    const epoch = scope.epochOf();
    expect(store.select("ws-b")).toBe(false);
    expect(scope.epochOf()).toBe(epoch);
  });

  it("游标分页：loadMore 带 cursor 并追加去重；limit 默认 25", async () => {
    const { scope, session } = harness();
    const { client, calls } = makeClient((_call, index) =>
      index === 0
        ? fakeResponse({ status: 200, body: page([workspace("ws-a", "甲", 1)], "cur-2") })
        : fakeResponse({ status: 200, body: page([workspace("ws-a", "甲", 1), workspace("ws-b", "乙", 1)], null) }),
    );
    const store = createWorkspacesStore({ client, scope, session });
    expect(store.state.limit).toBe(25);
    await store.loadFirstPage();
    expect(store.state.nextCursor).toBe("cur-2");
    await store.loadMore();
    expect(calls[1]?.url).toContain("cursor=cur-2");
    expect(calls[1]?.url).toContain("limit=25");
    expect(store.state.items.map((item) => item.id)).toEqual(["ws-a", "ws-b"]);
    expect(store.state.nextCursor).toBeNull();
  });
});
