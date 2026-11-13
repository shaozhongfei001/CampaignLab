/**
 * web/tests/unit/state/missingValue.spec.ts —— 缺值呈现用例（M0-03b / S2）
 *
 * 对齐 ui/COMMON.md:36「缺值显示 — 与原因。」与冻结 §3.5 的判定：
 * null、非有限 number、空串 → —；其余原样渲染（数值 0 是合法原值，不得吞成 —，也不得反过来用 0 冒充缺值）。
 * 单位换算（比率转百分数、金额分转元）不在本卡冻结面（F-E / U-3），故本文件不断言任何换算。
 */
import { describe, expect, it } from "vitest";
import { createSSRApp, h } from "vue";
import type { Component } from "vue";
import { renderToString } from "vue/server-renderer";
import MissingValue from "@/components/state/MissingValue.vue";
import {
  checkStateContract,
  dashCount,
  PARTIAL_MISSING,
  PARTIAL_REASON,
  renderCase,
  sixStateMatrix,
  stateSource,
  stripTags,
} from "./stateMatrix";

const DASH = "\u2014";

async function render(props: Record<string, unknown>): Promise<string> {
  return await renderToString(createSSRApp({ render: () => h(MissingValue as Component, props) }));
}

const MISSING_VALUES: readonly (string | number | null)[] = [null, "", Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY];
const REAL_VALUES: readonly (string | number)[] = [0, "0", -120000, 3.5, "3.5%", "共同子集差值"];

describe.each(MISSING_VALUES.map((value) => [String(value), value] as const))("缺值 %s", (_label, value) => {
  it("渲染 —（em dash，与 :36 同一字符）且 data-missing=true", async () => {
    const html = await render({ value });
    expect(stripTags(html)).toContain(DASH);
    expect(html).toContain('data-missing="true"');
  });

  it("给 reason 时 — 与原因同现（:36）", async () => {
    const html = await render({ value, reason: "待补录" });
    const text = stripTags(html);
    expect(text).toContain(DASH);
    expect(text).toContain("待补录");
    expect(html).toContain('data-part="reason"');
    expect(dashCount(html)).toBe(1);
  });
});

describe.each(REAL_VALUES.map((value) => [String(value), value] as const))("原值 %s", (label, value) => {
  it("原样渲染，不判为缺值、不出 —", async () => {
    const html = await render({ value });
    expect(stripTags(html)).toContain(label);
    expect(html).toContain('data-missing="false"');
    expect(stripTags(html)).not.toContain(DASH);
  });

  it("非缺值时不渲染原因（原因只服务缺值，:36）", async () => {
    const html = await render({ value, reason: "不该出现的原因" });
    expect(stripTags(html)).not.toContain("不该出现的原因");
    expect(html).not.toContain('data-part="reason"');
  });
});

describe("MissingValue 细节与窄屏", () => {
  it("空 reason 不渲染原因节点", async () => {
    expect(await render({ value: null, reason: "" })).not.toContain('data-part="reason"');
  });

  it("mono=true 才挂等宽数字类，且源码用 tabular-nums（token-mapping:45）", async () => {
    expect(await render({ value: 1200, mono: true })).toContain("cl-missing--mono");
    expect(await render({ value: 1200 })).not.toContain("cl-missing--mono");
    expect(stateSource("MissingValue.vue")).toContain("font-variant-numeric: tabular-nums");
  });

  it.each(sixStateMatrix().filter((item) => item.state === "partial-comparable" || item.state === "pending-fill"))(
    "$state @ $viewport.label：— 数量与缺项数一致、原因可见、经 ViewState 契约无违规",
    async (testCase) => {
      expect(await checkStateContract(testCase)).toEqual([]);
      const html = await renderCase(testCase);
      const missing = testCase.props["missing"] as readonly string[];
      expect(dashCount(html)).toBeGreaterThanOrEqual(missing.length);
      expect(stripTags(html)).toContain(String(testCase.props["reason"] ?? PARTIAL_REASON));
      expect(missing.length).toBeGreaterThan(0);
      expect(PARTIAL_MISSING.length).toBeGreaterThan(0);
    },
  );
});
