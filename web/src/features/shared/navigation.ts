// 路由守卫的可测内核（纯函数，不依赖 createWebHistory，故 vitest node 环境可直接断言）。
// 深链要求出处＝spec/CampaignLab-SDD-v1.0/framework/FRONTEND.md:12（页面侧），不是 AC-034（D-011）。
export interface GuardSession {
  captureRedirect(fullPath: string): void;
  takeRedirect(): string | null;
  readonly isActive: boolean;
}

export interface GuardTarget {
  fullPath: string;
  requiresSession: boolean;
}

const INTERNAL = /^\/(?![/\\])/;

export function isInternalPath(path: string): boolean {
  return INTERNAL.test(path);
}

export function normalizeRedirect(path: string): string {
  return isInternalPath(path) ? path : "/";
}

export type GuardDecision = { readonly to: string } | { readonly pass: true };

export function decideNavigation(session: GuardSession, target: GuardTarget): GuardDecision {
  if (target.requiresSession && !session.isActive) {
    session.captureRedirect(target.fullPath);
    return { to: "/" };
  }
  if (session.isActive) {
    const pending = session.takeRedirect();
    if (pending !== null) {
      const safe = normalizeRedirect(pending);
      if (safe !== target.fullPath) return { to: safe };
    }
  }
  return { pass: true };
}
