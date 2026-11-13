// S7/S9 共用的合成夹具（FRONTEND.md:16「固定合成输入和视口」）。
// 后端 S3b（api/session.py、api/workspaces.py）尚未落地，本 lane 严禁联调，
// 故所有 /session /health /workspaces 一律由浏览器路由拦截返回合成数据。
// 这些用例证明的是「前端层」交互与呈现基线，不构成端到端联调结论。
import type { Page } from "@playwright/test";

const SESSION = { actor_id: "op-synthetic", actor_name: "本机操作员（合成）", allowed_roles: ["OPERATOR"] };
const HEALTH = { status: "READY", app_version: "0.0.0", contract_version: "1.0.1", worker: "READY", schema_revision: "r1" };
const PAGE1 = {
  items: [
    { id: "ws-1", revision: 1, created_at: "2026-11-11T09:00:00+08:00", name: "合成工作区甲", source_class: "SYNTHETIC", authorization_note: null },
    { id: "ws-2", revision: 2, created_at: "2026-11-12T09:00:00+08:00", name: "授权脱敏工作区乙", source_class: "AUTHORIZED_DEIDENTIFIED", authorization_note: "DR-2026-11" },
  ],
  next_cursor: null,
};
const CREATED = { id: "ws-3", revision: 1, created_at: "2026-11-13T09:00:00+08:00", name: "新建工作区", source_class: "SYNTHETIC", authorization_note: null };

export async function stubCampaignLabApi(page: Page): Promise<void> {
  await page.route("**/*", (route) => {
    const path = new URL(route.request().url()).pathname.replace(/^\/api/, "");
    const method = route.request().method();
    const send = (body: unknown, status = 200) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (path === "/session/exchange") return send(SESSION);
    if (path === "/session") return method === "GET" ? send(SESSION) : route.fallback();
    if (path === "/health") return send(HEALTH);
    if (path === "/workspaces" && method === "GET") return send(PAGE1);
    if (path === "/workspaces" && method === "POST") return send(CREATED, 201);
    return route.fallback();
  });
}
