/**
 * web/tests/unit/state/registry.spec.ts —— 外部注册扩展点用例（M0-03b / S2，手册 15.6 末条）
 *
 * 目的：证明月报视角（M3-P02，AC-MR-03 至 AC-MR-08 的**来源为月度 append 清单**，本文件不引用
 * qa/ACCEPTANCE.md 的 AC 编号）能在**不改 §3 任何冻结签名**的前提下接入：注册 / 过滤 / 幂等（R-2）/
 * 卸载 / 无副作用装载（R-5）/ 能力上界（R-3）/ 矩阵复用（R-4）。
 *
 * R-4 的正例与负例都在此：注册 variant 后复用**同一 sixStateMatrix() + checkStateContract()** 复跑；
 * 再注册一个不满足「四条非颜色载体」的 render 替换，用例必须判红 —— 以此自证矩阵非空转。
 */
import { afterEach, describe, expect, it } from "vitest";
import { defineComponent, h } from "vue";
import {
  registerViewStateVariant,
  resolveVariants,
  unregisterViewStateVariant,
} from "@/components/state/registry";
import type { ViewStateContext, ViewStateVariant } from "@/components/state/registry";
import { copyOf, VIEW_STATE_DEV_NOTICES } from "@/components/state/viewState";
import type { ViewStateAction, ViewStateKind } from "@/components/state/viewState";
import {
  checkStateContract,
  dataActions,
  EXPECTED_ACTIONS,
  FROZEN_STATE_KINDS,
  matrixCaseFor,
  NO_RECORD_FILTER_TITLE,
  renderCase,
  sixStateMatrix,
  stateSource,
  stripComments,
  stripTags,
} from "./stateMatrix";

const IDS: string[] = [];

const ctxOf = (state: ViewStateKind, reviewId: string | null = "rvw-0007"): ViewStateContext => ({
  state,
  routeName: "activity-detail",
  workspaceId: "ws-0001",
  reviewId,
});

const track = (variant: ViewStateVariant): ViewStateVariant => {
  IDS.push(variant.id);
  registerViewStateVariant(variant);
  return variant;
};

afterEach(() => {
  while (IDS.length > 0) unregisterViewStateVariant(IDS.pop() ?? "");
  VIEW_STATE_DEV_NOTICES.length = 0;
});

describe("R-5 无副作用装载", () => {
  it("import 期零注册：六态的 resolveVariants 初始皆空", () => {
    for (const state of FROZEN_STATE_KINDS) expect(resolveVariants(ctxOf(state))).toEqual([]);
  });

  it("registry.ts 内 registerViewStateVariant 只以定义形式出现（顶层零调用）", () => {
    const code = stripComments(stateSource("registry.ts"));
    const lines = [...code.matchAll(/^.*(?<!un)registerViewStateVariant\(.*$/gm)].map((m) => m[0].trim());
    expect(lines).toEqual(["export function registerViewStateVariant(variant: ViewStateVariant): void {"]);
    expect([...code.matchAll(/(?<!un)registerViewStateVariant\s*\(/g)]).toHaveLength(1);
  });

  it("state/ 其余五件不反向调用注册（依赖方向恒为页面 / 月报模块 → state/ → registry）", () => {
    for (const file of ["viewState.ts", "ViewState.vue", "FirstLoadSkeleton.vue", "MissingValue.vue"]) {
      expect(stripComments(stateSource(file)), file).not.toContain("registerViewStateVariant(");
    }
  });
});

describe("注册 / 过滤 / 卸载（§4.2 三函数）", () => {
  it("appliesTo 按上下文过滤，返回顺序即注册顺序", () => {
    const all = track({ id: "scope-all", appliesTo: () => true });
    const monthly = track({ id: "monthly-review", appliesTo: (ctx) => ctx.reviewId !== null });
    const none = track({ id: "never", appliesTo: () => false });
    expect(resolveVariants(ctxOf("no-record")).map((v) => v.id)).toEqual(["scope-all", "monthly-review"]);
    expect(resolveVariants(ctxOf("no-record", null)).map((v) => v.id)).toEqual(["scope-all"]);
    expect(resolveVariants(ctxOf("no-record"))).toContain(all);
    expect(resolveVariants(ctxOf("no-record"))).toContain(monthly);
    expect(resolveVariants(ctxOf("no-record"))).not.toContain(none);
  });

  it("unregisterViewStateVariant 对不存在的 id 幂等", () => {
    expect(() => unregisterViewStateVariant("not-registered")).not.toThrow();
    expect(resolveVariants(ctxOf("failed"))).toEqual([]);
  });

  it("R-2 同 id 重复注册即覆盖并落到末位，dev 告警进水槽（禁 console）", () => {
    registerViewStateVariant({ id: "dup", appliesTo: () => true, copy: { failed: { hint: "第一版提示" } } });
    registerViewStateVariant({ id: "dup", appliesTo: () => true, copy: { failed: { hint: "第二版提示" } } });
    IDS.push("dup");
    const hits = resolveVariants(ctxOf("failed"));
    expect(hits).toHaveLength(1);
    expect(hits[0]?.copy?.failed?.hint).toBe("第二版提示");
    expect(VIEW_STATE_DEV_NOTICES.some((n) => n.source === "registry" && n.code === "variant-overwrite")).toBe(true);
  });
});

describe("R-3 能力上界 + R-4 矩阵复用", () => {
  const MONTHLY_TITLE = "月报视角：当前筛选无记录";

  it("copy 覆盖生效且默认串不再出现；页面 props.title 仍优先于 variant.copy（F-4）", async () => {
    track({
      id: "monthly-copy",
      appliesTo: (ctx) => ctx.state === "no-record",
      copy: { "no-record": { title: MONTHLY_TITLE } },
    });
    for (const testCase of sixStateMatrix().filter((item) => item.state === "no-record")) {
      const bare = { ...testCase, props: { state: "no-record" } };
      const bareText = stripTags(await renderCase(bare));
      expect(bareText).toContain(MONTHLY_TITLE);
      expect(bareText).not.toContain(copyOf("no-record").title);
      expect(await checkStateContract(bare, { variantCopy: { title: MONTHLY_TITLE } })).toEqual([]);
      const overridden = stripTags(await renderCase(testCase));
      expect(overridden).toContain(NO_RECORD_FILTER_TITLE);
      expect(overridden).not.toContain(MONTHLY_TITLE);
    }
  });

  it("extraActions 只能追加冻结动作键，且落在默认键之后（R-3）", async () => {
    track({ id: "monthly-actions", appliesTo: (ctx) => ctx.state === "no-record", extraActions: { "no-record": ["export"] } });
    const testCase = matrixCaseFor("no-record");
    const bare = { ...testCase, props: { state: "no-record" } };
    expect(dataActions(await renderCase(bare))).toEqual([...EXPECTED_ACTIONS["no-record"], "export"]);
    expect(await checkStateContract(bare, { extraActions: ["export"] })).toEqual([]);
  });

  it("render 替换后同一矩阵可全量复跑：合规替换不判红（R-4 正例）", async () => {
    const GoodRender = defineComponent({
      name: "GoodMonthlyRender",
      props: {
        state: String,
        title: String,
        hint: String,
        error: Object,
        actions: Array,
        missing: Array,
        reason: String,
        showPrevious: Boolean,
        keepInput: Boolean,
      },
      setup: (raw) => () => {
        const p = raw as unknown as Record<string, unknown>;
        const actions = (p["actions"] ?? []) as readonly ViewStateAction[];
        const missing = (p["missing"] ?? []) as readonly string[];
        const error = p["error"] as { kind?: string; title?: string; requestId?: string } | null;
        // R-3 / R-4：整态替换的呈现必须自己满足 §1.3 的四条非颜色载体 —— 错误两态的标题载体是服务端原样串。
        const titleText = error !== null && error.kind === "problem" ? String(error.title ?? "") : String(p["title"] ?? "");
        return h("div", [
          h("p", titleText),
          h("p", String(p["hint"] ?? "")),
          p["showPrevious"] === true ? h("p", "上一结果") : null,
          ...missing.map((item) => h("span", item + " " + "\u2014" + " " + String(p["reason"] ?? ""))),
          ...actions.map((action) => h("button", { type: "button", "data-action": action }, action)),
          error !== null && error !== undefined ? h("p", "request_id " + String(error.requestId ?? "")) : null,
        ]);
      },
    });
    track({ id: "monthly-render", appliesTo: () => true, render: GoodRender });
    for (const testCase of sixStateMatrix()) {
      expect(await checkStateContract(testCase), testCase.state + " @" + testCase.viewport.label).toEqual([]);
    }
  });

  it("负例：render 替换丢掉文案载体 → 同一矩阵必须判红（自证非空转），但 data-state / role 不可被移除", async () => {
    const BadRender = defineComponent({ name: "BadRender", setup: () => () => h("span", "裸呈现无文案") });
    track({ id: "bad-render", appliesTo: () => true, render: BadRender });
    const violations = await checkStateContract(matrixCaseFor("no-record"));
    expect(violations.some((v) => v.code === "copy-title")).toBe(true);
    expect(violations.some((v) => v.code === "copy-hint")).toBe(true);
    expect(violations.some((v) => v.code === "data-state")).toBe(false);
    expect(violations.some((v) => v.code === "role")).toBe(false);
  });

  it("variant 无法新增态或越界影响他态（copy 只对声明的态生效）", async () => {
    track({ id: "unknown-scope", appliesTo: (ctx) => ctx.state === "no-record", copy: { failed: { title: "不该出现的串" } } });
    expect(stripTags(await renderCase(matrixCaseFor("no-record")))).not.toContain("不该出现的串");
    expect(FROZEN_STATE_KINDS).toHaveLength(6);
  });
});
