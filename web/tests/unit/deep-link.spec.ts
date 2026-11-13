// 页面侧深链要求，出处＝spec/CampaignLab-SDD-v1.0/framework/FRONTEND.md:12。
// 本文件承担的不是 AC-034（qa/ACCEPTANCE.md:42 的 HTTP 负例，归 M0-02），
// 而是其页面侧后果的呈现一致性：直接打开/刷新/切工作区/404/过期会话都能回到合法入口。
import { describe, expect, it } from "vitest";
import { decideNavigation, isInternalPath, normalizeRedirect } from "@/features/shared/navigation";
import { createSessionStore } from "@/composables/useSession";
import { createWorkspaceScope } from "@/composables/useWorkspaceScope";
import type { ApiResult, HttpClient, HttpRequestOptions } from "@/api/http";
import type { Session } from "@/api/endpoints";
import { presentationOf } from "@/features/shared/problemPresentation";

const SESSION: Session = { actor_id: "op-1", actor_name: "本机操作员", allowed_roles: ["OPERATOR"] };
function ok<T>(data: T): ApiResult<T> {
  return { ok: true as const, status: 200, data, etag: null, requestId: "req-1", notModified: false };
}
function sessionClient(): HttpClient {
  return {
    request<T>(options: HttpRequestOptions): Promise<ApiResult<T>> {
      void options;
      return Promise.resolve(ok(SESSION as unknown as T));
    },
    poll<T>(): Promise<ApiResult<T>> { return Promise.resolve(ok(null as unknown as T)); },
    keyOf(options: Pick<HttpRequestOptions, "method" | "path" | "query">): string { return options.method + " " + options.path; },
    etagFor(): string | null { return null; },
    rememberEtag(): void { /* noop */ },
    devAssertions(): readonly string[] { return []; },
    drainDevAssertions(): string[] { return []; },
    baseUrl: "",
  } satisfies HttpClient;
}

describe("页面侧深链（FRONTEND.md:12）", () => {
  it("只接受站内绝对路径", () => {
    expect(isInternalPath("/workspaces/ws-1")).toBe(true);
    expect(isInternalPath("//evil.example/x")).toBe(false);
    expect(isInternalPath("https://evil.example")).toBe(false);
    expect(normalizeRedirect("//evil.example/x")).toBe("/");
    expect(normalizeRedirect("/workspaces/ws-1")).toBe("/workspaces/ws-1");
  });

  it("未登录访问受保护深链 → 登记深链并回入口", () => {
    const captured: string[] = [];
    const decision = decideNavigation(
      { captureRedirect: (p) => captured.push(p), takeRedirect: () => null, isActive: false },
      { fullPath: "/workspaces/ws-1", requiresSession: true },
    );
    expect(decision).toEqual({ to: "/" });
    expect(captured).toEqual(["/workspaces/ws-1"]);
  });

  it("会话恢复后一次性消费深链，不重放", () => {
    let pending: string | null = "/workspaces/ws-1";
    const deps = { captureRedirect: (p: string) => { pending = p; }, takeRedirect: () => { const v = pending; pending = null; return v; }, isActive: true };
    expect(decideNavigation(deps, { fullPath: "/workspaces/ws-1", requiresSession: true })).toEqual({ pass: true });
    expect(pending).toBeNull();
    expect(decideNavigation(deps, { fullPath: "/", requiresSession: false })).toEqual({ pass: true });
  });

  it("入口路由不需会话：刷新 / 直接打开都落在合法入口", () => {
    expect(decideNavigation({ captureRedirect: () => undefined, takeRedirect: () => null, isActive: false }, { fullPath: "/", requiresSession: false })).toEqual({ pass: true });
  });

  it("401 会话过期由 store 保全深链并清作用域", async () => {
    const scope = createWorkspaceScope();
    scope.setWorkspace("ws-1");
    const session = createSessionStore({ client: sessionClient(), scope });
    await session.bootstrap("t");
    session.signOut("SESSION_EXPIRED", "/workspaces/ws-1");
    expect(session.state.pendingRedirect).toBe("/workspaces/ws-1");
    expect(session.takeRedirect()).toBe("/workspaces/ws-1");
    expect(scope.state.workspaceId).toBeNull();
  });

  it("越权深链与不存在深链呈同一形态（不可见即不可见）", () => {
    const mk = (code: string, status: number) => presentationOf({
      kind: "problem", status, code, type: "urn:campaignlab:problem:" + code.toLowerCase(),
      title: "T", detail: "D", requestId: "r", issues: [],
    });
    expect(mk("ACCESS_DENIED", 403)).toEqual(mk("RESOURCE_NOT_FOUND", 404));
  });

  it("外链深链降级为入口，不构成开放重定向", () => {
    expect(normalizeRedirect("/\\evil.example")).toBe("/");
    expect(decideNavigation({ captureRedirect: (p: string) => p, takeRedirect: () => "//evil.example", isActive: true }, { fullPath: "/x", requiresSession: true })).toEqual({ to: "/" });
  });
});
