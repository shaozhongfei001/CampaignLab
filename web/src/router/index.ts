import { createRouter, createWebHistory, type RouteLocation, type Router } from "vue-router";
import WorkspacePage from "@/pages/workspace/WorkspacePage.vue";
import ActivityListPage from "@/pages/activity/ActivityListPage.vue";
import NotFoundPage from "@/pages/shared/NotFoundPage.vue";
import { useSession } from "@/composables/useSession";
import { decideNavigation, normalizeRedirect } from "@/features/shared/navigation";

// §7 白名单允许的路由装配（R3-Q7）：本文件是 S6 新增，main.ts 只追加 app.use(router)。
//
// 路由前缀口径（FE-TO-DAG-REQUESTS.md 请求 [1] / [3]）：
//   contracts/pages.json 是 route 的机器真值，26 条一律 `/w/:workspace_id/...`；
//   M0-03/S6 落地时只有 UI-01 一条真实页面，工作区详情用 `/workspaces/:workspaceId` 占位（挂 NotFoundPage）。
//   本次按**契约为主 + 旧路径重定向兼容**（三选一里的 B 方案）落地：
//     ① 新增契约路由 `/w/:workspace_id/activities`（UI-02，name=activity-list）；
//     ② `/workspaces/:workspaceId` 由「渲染 NotFoundPage」改为 301 语义的重定向到该工作区的活动列表，
//        使 UI-01 既有的「进入」跳转与既有截图证据不必改写即可落到真实页面；
//     ③ 未交付的工作区子路径仍由 catch-all 承接（COMMON.md:19「404 显示当前工作区的返回入口」）。
//   主线若裁 A（直接改名）或 C（改契约），本文件只需删掉 ② 或改 ① 的 path，页面与 store 不受影响。
export const ROUTES = [
  { path: "/", name: "workspace-entry", component: WorkspacePage, meta: { requiresSession: false } },
  {
    path: "/w/:workspace_id/activities",
    name: "activity-list",
    component: ActivityListPage,
    meta: { requiresSession: true },
  },
  {
    // 兼容旧实现的重定向记录：meta 在重定向上不生效（守卫看的是目标路由），保留只为可读性。
    path: "/workspaces/:workspaceId",
    name: "workspace-detail",
    redirect: (to: RouteLocation) => ({
      name: "activity-list",
      params: { workspace_id: String(to.params.workspaceId ?? "") },
      query: to.query,
    }),
    meta: { requiresSession: true },
  },
  { path: "/:pathMatch(.*)*", name: "not-found", component: NotFoundPage, meta: { requiresSession: false } },
];

export function createAppRouter(): Router {
  const router = createRouter({ history: createWebHistory(), routes: ROUTES });
  const session = useSession();

  router.beforeEach((to) => {
    const decision = decideNavigation(
      { captureRedirect: session.captureRedirect, takeRedirect: session.takeRedirect, isActive: session.state.phase === "active" },
      { fullPath: to.fullPath, requiresSession: to.meta.requiresSession === true },
    );
    if ("to" in decision) {
      const target = normalizeRedirect(decision.to);
      return target === to.fullPath ? true : target;
    }
    return true;
  });

  return router;
}
