/**
 * web/tests/unit/activity/store.spec.ts —— UI-02 store 的请求纪律与状态机
 *
 * 覆盖的硬规则（全部取解析值，不比对渲染串）：
 *   - 契约路径原文 /workspaces/{workspace_id}/activities（后端路径 ≠ 前端路由 /w/:workspace_id/activities）；
 *   - COMMON.md:38 默认 25 行 + 服务器游标；
 *   - FRONTEND.md:13 abort/请求序列：晚到响应不得覆盖当前范围；切工作区丢弃上一作用域响应；
 *   - COMMON.md:19 工作区切换清理本地临时查询与失效选择；
 *   - COMMON.md:31/34 校验失败保留输入、409 重试沿原幂等键、一次意图一个 key；
 *   - UI-02:32 相同银行行内编号重复 → 显示冲突并**定位既有记录**；
 *   - 表格与抽屉共用同一服务器结果（getActivity 原值回填列表行）。
 */
import { describe, expect, it } from "vitest";
import type { ApiResult, HttpClient, HttpRequestOptions, QueryInput } from "@/api/http";
import type { Activity, ActivityPage } from "@/api/endpoints";
import { ACTIVITY_PAGE_LIMIT } from "@/api/endpoints";
import { createSessionStore } from "@/composables/useSession";
import { createWorkspaceScope } from "@/composables/useWorkspaceScope";
import { createActivitiesStore } from "@/composables/useActivities";
import { fail, makeActivity, makeProblem, ok, okWithEtag } from "./fixtures";

interface RecordedCall {
  readonly method: string;
  readonly path: string;
  readonly query: QueryInput | undefined;
  readonly body: unknown;
  readonly idempotencyKey: string | undefined;
}

interface Deferred<T> {
  readonly promise: Promise<T>;
  resolve(value: T): void;
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((inner) => {
    resolve = inner;
  });
  return { promise, resolve };
}

type Responder = (call: RecordedCall, index: number) => ApiResult<unknown> | Promise<ApiResult<unknown>>;

function makeHarness(responder: Responder) {
  const calls: RecordedCall[] = [];
  const client: HttpClient = {
    request<T>(options: HttpRequestOptions): Promise<ApiResult<T>> {
      const call: RecordedCall = {
        method: options.method,
        path: options.path,
        query: options.query,
        body: options.body,
        idempotencyKey: options.idempotencyKey,
      };
      calls.push(call);
      return Promise.resolve(responder(call, calls.length - 1)) as Promise<ApiResult<T>>;
    },
    poll<T>(): Promise<ApiResult<T>> {
      return Promise.resolve(ok(null as unknown as T));
    },
    keyOf(options: Pick<HttpRequestOptions, "method" | "path" | "query">): string {
      return options.method + " " + options.path;
    },
    etagFor(): string | null {
      return null;
    },
    rememberEtag(): void {
      /* noop */
    },
    devAssertions(): readonly string[] {
      return [];
    },
    drainDevAssertions(): string[] {
      return [];
    },
    baseUrl: "",
  };
  const scope = createWorkspaceScope();
  const session = createSessionStore({ client, scope });
  const store = createActivitiesStore({ client, scope, session });
  return { calls, client, scope, session, store };
}

function pageOf(items: readonly Activity[], nextCursor: string | null = null): ActivityPage {
  return { items: [...items], next_cursor: nextCursor };
}

const listResponder = (page: ActivityPage): Responder => (call) =>
  call.path.endsWith("/activities") && call.method === "GET" ? ok(page) : fail(makeProblem(404, "RESOURCE_NOT_FOUND"));

describe("请求发出前的作用域纪律", () => {
  it("未绑定工作区时不发任何请求（不得拿空标识打服务端）", async () => {
    const harness = makeHarness(listResponder(pageOf([])));
    await harness.store.loadFirstPage();
    expect(harness.calls).toEqual([]);
    expect(harness.store.state.phase).toBe("idle");
  });

  it("绑定后首屏：契约路径原文 + limit 默认 25，空筛选不带 q/status 键", async () => {
    const harness = makeHarness(listResponder(pageOf([makeActivity()])));
    harness.store.setWorkspace("ws-1");
    await harness.store.setFilters("", "");
    expect(harness.calls.length).toBe(1);
    const call = harness.calls[0];
    expect(call?.method).toBe("GET");
    expect(call?.path).toBe("/workspaces/ws-1/activities");
    expect(call?.query?.limit).toBe(ACTIVITY_PAGE_LIMIT);
    expect(Object.keys(call?.query ?? {}).sort()).toEqual(["limit"]);
    expect(harness.store.state.phase).toBe("ready");
  });

  it("工作区标识进 URL 前被编码（深链里的保留字符不破坏路径）", async () => {
    const harness = makeHarness(listResponder(pageOf([])));
    harness.store.setWorkspace("ws 1/甲");
    await harness.store.loadFirstPage();
    expect(harness.calls[0]?.path).toBe("/workspaces/ws%201%2F%E7%94%B2/activities");
  });

  it("筛选参数按契约归一化后发送；非法状态不发送", async () => {
    const harness = makeHarness(listResponder(pageOf([])));
    harness.store.setWorkspace("ws-1");
    await harness.store.setFilters("  满额   赠券  ", "OPEN");
    expect(harness.calls[0]?.query?.q).toBe("满额 赠券");
    expect(harness.calls[0]?.query?.status).toBe("OPEN");

    await harness.store.setFilters("", "DRAFT");
    expect(Object.keys(harness.calls[1]?.query ?? {}).sort()).toEqual(["limit"]);
    expect(harness.store.state.status).toBe("");
  });

  it("负对照：任何请求都不得带契约未声明的查询参数（如 sort / page / status 之外的自造键）", async () => {
    const harness = makeHarness(listResponder(pageOf([makeActivity()], "cursor-2")));
    harness.store.setWorkspace("ws-1");
    await harness.store.setFilters("q1", "ARCHIVED");
    await harness.store.loadMore();
    const allowed = ["cursor", "limit", "q", "status"];
    for (const call of harness.calls) {
      for (const key of Object.keys(call.query ?? {})) expect(allowed, "自造查询参数 " + key).toContain(key);
    }
    expect(harness.calls[1]?.query?.cursor).toBe("cursor-2");
  });
});

describe("晚到响应与工作区切换（FRONTEND.md:13 / COMMON.md:19）", () => {
  it("较晚发出的响应先落地后，较早的晚到响应不得覆盖当前范围", async () => {
    const gates: Array<Deferred<ApiResult<unknown>>> = [];
    const harness = makeHarness(() => {
      const gate = deferred<ApiResult<unknown>>();
      gates.push(gate);
      return gate.promise;
    });
    harness.store.setWorkspace("ws-1");
    const first = harness.store.loadFirstPage();
    const second = harness.store.loadFirstPage();

    gates[1]?.resolve(ok(pageOf([makeActivity({ id: "new" })])));
    gates[0]?.resolve(ok(pageOf([makeActivity({ id: "old" })])));
    await Promise.all([first, second]);

    expect(harness.store.state.items.map((item) => item.id)).toEqual(["new"]);
  });

  it("切工作区后，上一作用域的响应被丢弃（epoch + 作用域标识双重判定）", async () => {
    const gates: Array<Deferred<ApiResult<unknown>>> = [];
    const harness = makeHarness(() => {
      const gate = deferred<ApiResult<unknown>>();
      gates.push(gate);
      return gate.promise;
    });
    harness.store.setWorkspace("ws-1");
    const pending = harness.store.loadFirstPage();
    harness.store.setWorkspace("ws-2");
    gates[0]?.resolve(ok(pageOf([makeActivity({ id: "stale-ws1" })])));
    await pending;
    expect(harness.store.state.items).toEqual([]);
    expect(harness.store.state.workspaceId).toBe("ws-2");
  });

  it("切工作区清理本地临时筛选、游标与详情（COMMON.md:19）", async () => {
    const detail = makeActivity({ id: "a-9" });
    const harness = makeHarness((call) => {
      if (call.method === "GET" && call.path.endsWith("/activities/a-9")) return ok(detail);
      return ok(pageOf([makeActivity({ id: "a-1" })], "cursor-1"));
    });
    harness.store.setWorkspace("ws-1");
    await harness.store.setFilters("满额", "OPEN");
    await harness.store.openDetail("a-9");
    expect(harness.store.state.detail?.id).toBe("a-9");

    harness.store.setWorkspace("ws-2");
    expect(harness.store.state.q).toBe("");
    expect(harness.store.state.status).toBe("");
    expect(harness.store.state.nextCursor).toBeNull();
    expect(harness.store.state.items).toEqual([]);
    expect(harness.store.state.detail).toBeNull();
    expect(harness.store.revisionOf("a-9")).toBeNull();
  });

  it("同一工作区重复绑定不清场（刷新/深链回到同一工作区不得清掉已加载数据）", async () => {
    const harness = makeHarness(listResponder(pageOf([makeActivity({ id: "a-1" })])));
    harness.store.setWorkspace("ws-1");
    await harness.store.loadFirstPage();
    const changed = harness.store.setWorkspace("ws-1");
    expect(changed).toBe(false);
    expect(harness.store.state.items.map((item) => item.id)).toEqual(["a-1"]);
  });
});

describe("会话级失败交回 session store", () => {
  it("401 → signOut + 作用域清空 + 页面回 idle，不重复持有同一份 Problem", async () => {
    const harness = makeHarness(() => fail(makeProblem(401, "SESSION_EXPIRED")));
    harness.store.setWorkspace("ws-1");
    await harness.store.loadFirstPage();
    expect(harness.store.state.phase).toBe("idle");
    expect(harness.store.state.error).toBeNull();
    expect(harness.scope.state.workspaceId).toBeNull();
    // signOut 未带显式深链时回落到入口路径（ROOT_PATH），即「回到合法入口」而不是留空。
    expect(harness.session.state.pendingRedirect).toBe("/");
  });

  it("非会话级失败 → phase=failed 且保留 Problem 供 AlertBanner 呈现", async () => {
    const problem = makeProblem(500, "INTERNAL_ERROR");
    const harness = makeHarness(() => fail(problem));
    harness.store.setWorkspace("ws-1");
    await harness.store.loadFirstPage();
    expect(harness.store.state.phase).toBe("failed");
    expect(harness.store.state.error?.code).toBe("INTERNAL_ERROR");
  });

  it("空结果 → phase=empty（与失败态不混用）", async () => {
    const harness = makeHarness(listResponder(pageOf([])));
    harness.store.setWorkspace("ws-1");
    await harness.store.loadFirstPage();
    expect(harness.store.state.phase).toBe("empty");
    expect(harness.store.state.error).toBeNull();
  });
});

describe("新建活动（createActivity）", () => {
  it("成功：201 原值头插、ETag 进请求缓存、幂等键原样透传", async () => {
    const created = makeActivity({ id: "a-new", revision: 1 });
    const harness = makeHarness((call) =>
      call.method === "POST" ? okWithEtag(created, '"rev-1"') : ok(pageOf([makeActivity({ id: "a-1" })])),
    );
    harness.store.setWorkspace("ws-1");
    await harness.store.loadFirstPage();
    const result = await harness.store.create({ name: "新活动" }, "activity-create-abcdefgh");

    expect(result.ok).toBe(true);
    const post = harness.calls.find((call) => call.method === "POST");
    expect(post?.path).toBe("/workspaces/ws-1/activities");
    expect(post?.idempotencyKey).toBe("activity-create-abcdefgh");
    expect(post?.body).toEqual({ name: "新活动" });
    expect(harness.store.state.items.map((item) => item.id)).toEqual(["a-new", "a-1"]);
    expect(harness.store.revisionOf("a-new")).toEqual({ revision: 1, etag: '"rev-1"' });
  });

  it("409 且草稿带行内编号 → 保留输入、记录冲突、并自动按行内编号定位既有记录", async () => {
    const harness = makeHarness((call) =>
      call.method === "POST" ? fail(makeProblem(409, "IDEMPOTENCY_CONFLICT")) : ok(pageOf([makeActivity({ id: "a-1" })])),
    );
    harness.store.setWorkspace("ws-1");
    await harness.store.loadFirstPage();
    const result = await harness.store.create(
      { name: "重复活动", bank_id: "BANK-A", external_activity_id: "EXT-DUP" },
      "activity-create-dupkey01",
    );

    expect(result.ok).toBe(false);
    expect(harness.store.state.createError?.status).toBe(409);
    expect(harness.store.state.locatedExternalId).toBe("EXT-DUP");
    const locate = harness.calls.filter((call) => call.method === "GET").at(-1);
    expect(locate?.query?.q).toBe("EXT-DUP");
    expect(locate?.query).not.toHaveProperty("status");
  });

  it("409 但草稿无行内编号 → 只报冲突，不改筛选（无定位依据就不伪造定位）", async () => {
    const harness = makeHarness((call) =>
      call.method === "POST" ? fail(makeProblem(409, "IDEMPOTENCY_CONFLICT")) : ok(pageOf([])),
    );
    harness.store.setWorkspace("ws-1");
    await harness.store.setFilters("原始筛选", "");
    await harness.store.create({ name: "重复活动" }, "activity-create-noext01");
    expect(harness.store.state.locatedExternalId).toBeNull();
    expect(harness.store.state.q).toBe("原始筛选");
  });

  it("未绑定工作区时 create 不发请求，返回 assertion 失败", async () => {
    const harness = makeHarness(listResponder(pageOf([])));
    const result = await harness.store.create({ name: "甲" }, "activity-create-nosuchws");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.kind).toBe("assertion");
    expect(harness.calls).toEqual([]);
  });
});

describe("进入活动详情（getActivity）", () => {
  it("路径原文正确，detail 与列表行共用同一份服务器结果（同一对象引用）", async () => {
    const detail = makeActivity({ id: "a-1", revision: 7, name: "服务端改名后的活动" });
    const harness = makeHarness((call) =>
      call.path.endsWith("/activities/a-1") ? okWithEtag(detail, '"rev-7"', 200) : ok(pageOf([makeActivity({ id: "a-1" })])),
    );
    harness.store.setWorkspace("ws-1");
    await harness.store.loadFirstPage();
    await harness.store.openDetail("a-1");

    const get = harness.calls.find((call) => call.path.endsWith("/activities/a-1"));
    expect(get?.method).toBe("GET");
    expect(harness.store.state.detail?.revision).toBe(7);
    expect(harness.store.revisionOf("a-1")).toEqual({ revision: 7, etag: '"rev-7"' });
    const row = harness.store.state.items.find((item) => item.id === "a-1");
    expect(row?.name).toBe("服务端改名后的活动");
    expect(row === harness.store.state.detail).toBe(true);
  });

  it("详情失败保留列表数据，只置 detailError", async () => {
    const harness = makeHarness((call) =>
      call.path.endsWith("/activities/a-1") ? fail(makeProblem(404, "RESOURCE_NOT_FOUND")) : ok(pageOf([makeActivity({ id: "a-1" })])),
    );
    harness.store.setWorkspace("ws-1");
    await harness.store.loadFirstPage();
    await harness.store.openDetail("a-1");
    expect(harness.store.state.detail).toBeNull();
    expect(harness.store.state.detailError?.code).toBe("RESOURCE_NOT_FOUND");
    expect(harness.store.state.items.length).toBe(1);
  });

  it("closeDetail 清空详情态", async () => {
    const harness = makeHarness((call) =>
      call.path.endsWith("/activities/a-1") ? ok(makeActivity({ id: "a-1" })) : ok(pageOf([makeActivity({ id: "a-1" })])),
    );
    harness.store.setWorkspace("ws-1");
    await harness.store.loadFirstPage();
    await harness.store.openDetail("a-1");
    expect(harness.store.state.detail).not.toBeNull();
    harness.store.closeDetail();
    expect(harness.store.state.detail).toBeNull();
    expect(harness.store.state.detailError).toBeNull();
    expect(harness.store.state.detailLoading).toBe(false);
  });
});

describe("登出联动", () => {
  it("session.signOut 清空列表态并解绑工作区", async () => {
    const harness = makeHarness(listResponder(pageOf([makeActivity({ id: "a-1" })])));
    harness.store.setWorkspace("ws-1");
    await harness.store.loadFirstPage();
    expect(harness.store.state.items.length).toBe(1);
    harness.session.signOut("SESSION_EXPIRED", "/w/ws-1/activities");
    expect(harness.store.state.items).toEqual([]);
    expect(harness.store.state.workspaceId).toBeNull();
    expect(harness.store.state.phase).toBe("idle");
    expect(harness.session.state.pendingRedirect).toBe("/w/ws-1/activities");
  });
});
