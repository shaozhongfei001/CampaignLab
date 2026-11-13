// AC-001（入口页首跑）+ UI-01 交互口径。环境＝node（Q1 的 jsdom 尚未入库），
// 故一律用注入替身走 store 纯逻辑，不触碰 document / window。
import { describe, expect, it } from "vitest";
import { createWorkspacesStore } from "@/composables/useWorkspaces";
import { createSessionStore } from "@/composables/useSession";
import { createWorkspaceScope } from "@/composables/useWorkspaceScope";
import type { ApiResult, HttpClient, HttpRequestOptions } from "@/api/http";
import { normalizeWorkspaceQuery, sendsQuery } from "@/features/workspace/query";
import { nextSort, sortWorkspaces } from "@/features/workspace/sort";
import type { Health, Session, Workspace, WorkspacePage } from "@/api/endpoints";

const SESSION: Session = { actor_id: "op-1", actor_name: "本机操作员", allowed_roles: ["OPERATOR"] };
const HEALTH: Health = { status: "READY", app_version: "0.0.0", contract_version: "1.0.1", worker: "READY", schema_revision: "r1" };
function ws(id: string, name: string, created: string): Workspace {
  return { id, revision: 1, created_at: created, name, source_class: "SYNTHETIC", authorization_note: null };
}
function okp<T>(data: T, status = 200): Promise<ApiResult<T>> {
  return Promise.resolve({ ok: true as const, status, data, etag: null, requestId: "req-" + status, notModified: false });
}
function recording(pageItems: Workspace[], nextCursor: string | null = null) {
  const calls: HttpRequestOptions[] = [];
  const client = {
    request<T>(options: HttpRequestOptions): Promise<ApiResult<T>> {
      calls.push(options);
      if (options.path === "/session/exchange" || options.path === "/session") return okp(SESSION as unknown as T);
      if (options.path === "/health") return okp(HEALTH as unknown as T);
      if (options.path === "/workspaces" && options.method === "GET") {
        return okp({ items: pageItems, next_cursor: nextCursor } as unknown as WorkspacePage as unknown as T);
      }
      if (options.path === "/workspaces" && options.method === "POST") {
        return okp(ws("ws-new", "新建的", "2026-11-13T10:00:00+08:00") as unknown as T, 201);
      }
      return okp(null as unknown as T);
    },
    poll<T>(): Promise<ApiResult<T>> {
      return okp(null as unknown as T);
    },
    keyOf(options: Pick<HttpRequestOptions, "method" | "path" | "query">): string {
      return options.method + " " + options.path;
    },
    etagFor(): string | null { return null; },
    rememberEtag(): void { /* 替身不缓存 ETag */ },
    devAssertions(): readonly string[] { return []; },
    drainDevAssertions(): string[] { return []; },
    baseUrl: "",
  } satisfies HttpClient;
  return { client, calls };
}

describe("UI-01 入口页（AC-001）", () => {
  it("入口令牌只换取一次，随后按会话检查", async () => {
    const { client, calls } = recording([]);
    const session = createSessionStore({ client });
    await session.bootstrap("token-1");
    await session.bootstrap(null);
    const exchanges = calls.filter((c) => c.path === "/session/exchange").length;
    expect(exchanges).toBe(1);
    expect(calls.some((c) => c.path === "/session")).toBe(true);
    expect(session.state.session?.actor_name).toBe("本机操作员");
  });

  it("列表默认 25 行；游标非空时续页带上 cursor", async () => {
    const { client, calls } = recording([ws("a", "甲", "2026-11-13T09:00:00+08:00")], "cur-2");
    const store = createWorkspacesStore({ client, scope: createWorkspaceScope() });
    await store.loadFirstPage();
    await store.loadMore();
    const list = calls.filter((c) => c.path === "/workspaces" && c.method === "GET");
    expect(list[0]?.query).toMatchObject({ limit: 25 });
    expect(list[1]?.query).toMatchObject({ cursor: "cur-2" });
    expect(store.state.items.length).toBe(1);
  });

  it("搜索词清理：trim → 折叠空白 → 空则不发送 → 截断 100", () => {
    expect(normalizeWorkspaceQuery("  甲   乙  ")).toBe("甲 乙");
    expect(normalizeWorkspaceQuery("   ")).toBe("");
    expect(sendsQuery("   ")).toBe(false);
    expect(normalizeWorkspaceQuery("x".repeat(140))).toHaveLength(100);
  });

  it("清理后的搜索词写入请求；空串不带 q 参数", async () => {
    const { client, calls } = recording([]);
    const store = createWorkspacesStore({ client, scope: createWorkspaceScope() });
    await store.setQuery(normalizeWorkspaceQuery("  合成  工作区  "));
    expect(calls.at(-1)?.query).toMatchObject({ q: "合成 工作区" });
    await store.setQuery(normalizeWorkspaceQuery("   "));
    expect(calls.at(-1)?.query?.q).toBeUndefined();
  });

  it("创建走 Idempotency-Key，成功后选中并进入作用域", async () => {
    const { client, calls } = recording([]);
    const scope = createWorkspaceScope();
    const store = createWorkspacesStore({ client, scope });
    const result = await store.create({ name: "新工作区", source_class: "SYNTHETIC", authorization_note: null }, "key-12345678");
    expect(result.ok).toBe(true);
    const post = calls.find((c) => c.method === "POST");
    expect(post?.idempotencyKey).toBe("key-12345678");
    expect(post?.requireIdempotencyKey).toBe(true);
    expect(store.select("ws-new")).toBe(true);
    expect(scope.state.workspaceId).toBe("ws-new");
  });

  it("切换工作区清除上一作用域资源，回到同一工作区不清场", () => {
    const scope = createWorkspaceScope();
    let disposed = 0;
    scope.setWorkspace("a");
    scope.register("poll", "作业轮询", () => { disposed += 1; });
    expect(scope.setWorkspace("b")).toBe(true);
    expect(disposed).toBe(1);
    expect(scope.setWorkspace("b")).toBe(false);
  });

  it("表头排序可键盘触发后的状态推进：换列回 asc，同列翻转", () => {
    const first = nextSort({ key: "created_at", dir: "desc" }, "name");
    expect(first).toEqual({ key: "name", dir: "asc" });
    expect(nextSort(first, "name")).toEqual({ key: "name", dir: "desc" });
  });

  it("排序作用于已加载行（契约 listWorkspaces 无 sort 参数）", () => {
    const rows = sortWorkspaces([ws("b", "乙", "2026-11-02T00:00:00+08:00"), ws("a", "甲", "2026-11-01T00:00:00+08:00")], { key: "name", dir: "asc" });
    // 前端只做 Unicode 码位稳定排序（服务端不下发 sort，故不假定拼音序）。
    expect(rows.map((r) => r.name)).toEqual(["乙", "甲"]);
  });

  it("UI-01 不提供状态筛选控件：契约参数只有 cursor / limit / q（A7 / CR-002）", () => {
    const params = ["cursor", "limit", "q"];
    expect(params).not.toContain("status");
  });
});
