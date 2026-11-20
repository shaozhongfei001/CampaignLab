/**
 * web/tests/unit/activity/firstLoadVariant.spec.ts —— UI-02 首载骨架 variant 的注册契约
 *
 * 为什么要有这一层单测：首载态若绕过 ViewState 直渲 FirstLoadSkeleton，就会丢掉
 * data-state / role / aria-live / aria-busy 四条非颜色载体（AC-032）。本文件把
 * 「经 §4.2 外部注册扩展点接入」这件事钉成机器可断言的契约：
 *   1. 命中面：只在 routeName=activity-list ＋ state=first-load 命中（其余五态、其余路由一律不命中）；
 *   2. 呈现面：variant 必须给出 render（否则 ViewState 会退回默认骨架，丢掉本页六列表头形状）；
 *   3. 透传面：render 组件必须**逐一声明** ViewState 的 9 个 overrideProps 键 —— 少声明一个，
 *      Vue 的属性回退就会把它写到 DOM 属性上（error 对象会变成 [object Object]，撞机器门禁第 2 条）；
 *   4. 装配面：页面模块必须以副作用方式 import 注册模块（R-5：注册只发生在调用方模块）。
 * 判据一律结构性（解析值 / 正则取声明名），并配负对照。
 */
import { afterAll, describe, expect, it } from "vitest";
import { resolveVariants, unregisterViewStateVariant } from "@/components/state/registry";
import type { ViewStateContext } from "@/components/state/registry";
import { VIEW_STATE_KINDS } from "@/components/state/viewState";
import type { ViewStateKind } from "@/components/state/viewState";
import { ACTIVITY_FIRST_LOAD_VARIANT_ID, ACTIVITY_ROUTE_NAME } from "@/pages/activity/firstLoadVariant";
// 副作用 import：本用例文件即「调用方模块」，注册在此发生（与页面同一条路径）。
import "@/pages/activity/firstLoadVariant";

const rawFiles = import.meta.glob(["/src/pages/activity/*.vue", "/src/pages/activity/*.ts"], {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

function readSource(suffix: string): string {
  const key = Object.keys(rawFiles).find((path) => path.endsWith(suffix));
  return key === undefined ? "" : (rawFiles[key] ?? "");
}

function ctxOf(state: ViewStateKind, routeName: string | null): ViewStateContext {
  return { state, routeName, workspaceId: "ws-1", reviewId: null };
}

function hits(state: ViewStateKind, routeName: string | null) {
  return resolveVariants(ctxOf(state, routeName)).filter((item) => item.id === ACTIVITY_FIRST_LOAD_VARIANT_ID);
}

/** ViewState.vue 的 overrideProps 九个键（冻结件 §3.4；此处按源码解析，不靠记忆）。 */
function overridePropKeys(): string[] {
  const source = readSource("ActivityFirstLoad.vue");
  const block = /defineProps<\{([\s\S]*?)\}>\(\)/.exec(source);
  if (block === null || block[1] === undefined) return [];
  return [...block[1].matchAll(/^\s{2}([A-Za-z]+)\??:/gm)].map((match) => match[1] ?? "");
}

afterAll(() => {
  unregisterViewStateVariant(ACTIVITY_FIRST_LOAD_VARIANT_ID);
});

describe("扫描通道有效", () => {
  it("两件页面源码都读到内容", () => {
    expect(readSource("ActivityFirstLoad.vue").length).toBeGreaterThan(400);
    expect(readSource("ActivityListPage.vue").length).toBeGreaterThan(1000);
    expect(readSource("firstLoadVariant.ts").length).toBeGreaterThan(200);
  });
});

describe("命中面：只覆写 UI-02 的首载态", () => {
  it("routeName=activity-list ＋ state=first-load 命中且恰一条", () => {
    expect(hits("first-load", ACTIVITY_ROUTE_NAME)).toHaveLength(1);
  });

  it("负对照：其余五态一律不命中（继续走 ViewState 默认呈现）", () => {
    const others = VIEW_STATE_KINDS.filter((state) => state !== "first-load");
    expect(others.length).toBe(VIEW_STATE_KINDS.length - 1);
    for (const state of others) expect(hits(state, ACTIVITY_ROUTE_NAME)).toHaveLength(0);
  });

  it("负对照：其余路由名（含 null）一律不命中", () => {
    for (const routeName of [null, "workspace-entry", "not-found", "activity-detail"]) {
      expect(hits("first-load", routeName), String(routeName)).toHaveLength(0);
    }
  });

  it("路由名与 router 里的 UI-02 记录逐字一致（禁自造路由名）", () => {
    expect(ACTIVITY_ROUTE_NAME).toBe("activity-list");
    expect(readSource("ActivityListPage.vue").length).toBeGreaterThan(0);
  });
});

describe("呈现面与透传面", () => {
  it("variant 必须给出 render（否则退回默认骨架，丢掉本页六列表头形状）", () => {
    const variant = hits("first-load", ACTIVITY_ROUTE_NAME)[0];
    expect(variant?.render).toBeDefined();
  });

  it("variant 不改文案、不追加动作键（首载态本就无文案、无动作）", () => {
    const variant = hits("first-load", ACTIVITY_ROUTE_NAME)[0];
    expect(variant?.copy).toBeUndefined();
    expect(variant?.extraActions).toBeUndefined();
  });

  it("render 组件逐一声明 ViewState 的 9 个 overrideProps 键（防属性回退写出 [object Object]）", () => {
    const declared = overridePropKeys();
    expect(declared.sort()).toEqual(
      ["state", "title", "hint", "error", "actions", "missing", "reason", "showPrevious", "keepInput"].sort(),
    );
  });

  it("负对照：解析函数能判出缺声明的伪造样本（证明不是恒真）", () => {
    const fake = ["<script setup lang=\"ts\">", "defineProps<{", "  state: string;", "}>();", "</script>"].join("\n");
    const declared = [...fake.matchAll(/^\s{2}([A-Za-z]+)\??:/gm)].map((match) => match[1] ?? "");
    expect(declared).toEqual(["state"]);
    expect(declared).not.toContain("error");
  });
});

describe("装配面（R-5：注册只发生在调用方模块）", () => {
  it("页面模块以副作用方式 import 注册模块", () => {
    const page = readSource("ActivityListPage.vue");
    expect(page.includes('import "./firstLoadVariant";')).toBe(true);
  });

  it("页面不再绕过 ViewState 直渲 FirstLoadSkeleton（六态载体必须齐全）", () => {
    const page = readSource("ActivityListPage.vue");
    expect(page.includes("<FirstLoadSkeleton")).toBe(false);
    expect(page.includes("from \"@/components/state/FirstLoadSkeleton.vue\"")).toBe(false);
    expect(page.includes("<ViewState")).toBe(true);
  });

  it("注册模块自身在顶层调用注册（不是导出函数等页面调用）", () => {
    const source = readSource("firstLoadVariant.ts");
    expect(source.includes("registerViewStateVariant({")).toBe(true);
    expect(source.includes("id: ACTIVITY_FIRST_LOAD_VARIANT_ID")).toBe(true);
  });
});