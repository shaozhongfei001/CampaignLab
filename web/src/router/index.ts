import { createRouter, createWebHistory, type Router } from "vue-router";
import WorkspacePage from "@/pages/workspace/WorkspacePage.vue";
import NotFoundPage from "@/pages/shared/NotFoundPage.vue";
import { useSession } from "@/composables/useSession";
import { decideNavigation, normalizeRedirect } from "@/features/shared/navigation";

// §7 白名单允许的路由装配（R3-Q7）：本文件是 S6 新增，main.ts 只追加 app.use(router)。
export const ROUTES = [
  { path: "/", name: "workspace-entry", component: WorkspacePage, meta: { requiresSession: false } },
  { path: "/workspaces/:workspaceId", name: "workspace-detail", component: NotFoundPage, meta: { requiresSession: true } },
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
