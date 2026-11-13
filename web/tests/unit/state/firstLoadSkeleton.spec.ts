/**
 * web/tests/unit/state/firstLoadSkeleton.spec.ts —— 首载骨架用例（M0-03b / S2）
 *
 * 对齐 ui/COMMON.md:27「主区骨架对应标题、表头和卡片位置。保留导航」与冻结 §1.3 / §3.5：
 * 只占位不出字、不渲染 0 或空串冒充数据、不得包裹或替换 SideRail（保留导航 = 纯内容层骨架）。
 */
import { describe, expect, it } from "vitest";
import { createSSRApp, h } from "vue";
import type { Component } from "vue";
import { renderToString } from "vue/server-renderer";
import FirstLoadSkeleton from "@/components/state/FirstLoadSkeleton.vue";
import { checkStateContract, matrixCaseFor, sixStateMatrix, stateSource, stripTags } from "./stateMatrix";

const HEAD_LABELS = ["活动", "口径", "本期", "基准", "覆盖", "摘要"];

async function render(props: Record<string, unknown>): Promise<string> {
  return await renderToString(createSSRApp({ render: () => h(FirstLoadSkeleton as Component, props) }));
}

function count(html: string, part: string): number {
  return (html.match(new RegExp('data-part="' + part + '"', "g")) ?? []).length;
}

const IMPORT_LINES = ((): string[] => [...stateSource("FirstLoadSkeleton.vue").matchAll(/^import\s.*$/gm)].map((m) => m[0]));

describe("FirstLoadSkeleton 占位形状（§3.5 props）", () => {
  it("无 props 时只出容器：零标题块、零表头格、零卡片", async () => {
    const html = await render({});
    expect(html).toContain('data-part="first-load-skeleton"');
    expect(count(html, "heading")).toBe(0);
    expect(count(html, "head-cell")).toBe(0);
    expect(count(html, "card")).toBe(0);
  });

  it("headCells 给定时表头占位格与列数一一对应（6 列即 6 格）", async () => {
    expect(count(await render({ headCells: HEAD_LABELS }), "head-cell")).toBe(HEAD_LABELS.length);
    expect(count(await render({ headCells: HEAD_LABELS.slice(0, 2) }), "head-cell")).toBe(2);
  });

  it("cardCount 给定时卡片占位块数量相等", async () => {
    expect(count(await render({ cardCount: 3 }), "card")).toBe(3);
  });

  it("heading 只决定占位块是否出现，其值不渲染为文字（§1.3 首载「无文案」）", async () => {
    const html = await render({ heading: "活动明细标题", headCells: HEAD_LABELS, cardCount: 2 });
    expect(count(html, "heading")).toBe(1);
    expect(stripTags(html)).toBe("");
  });

  it("不渲染任何数字或空串冒充数据（含 0）", async () => {
    const text = stripTags(await render({ headCells: HEAD_LABELS, cardCount: 4 }));
    expect(text).toBe("");
    expect(/\d/.test(text)).toBe(false);
  });
});

describe("保留导航（§3.5 对齐原文）与矩阵窄屏腿", () => {
  it("骨架件不 import 布局件，渲染结果不含 nav / aside / header", async () => {
    const offenders = IMPORT_LINES().filter((line) => /AppShell|SideRail|AppBar|PageGrid|PageBar/.test(line));
    expect(offenders).toEqual([]);
    const html = await render({ headCells: HEAD_LABELS, cardCount: 2 });
    for (const tag of ["<nav", "<aside", "<header"]) expect(html).not.toContain(tag);
  });

  it.each(sixStateMatrix().filter((item) => item.state === "first-load"))(
    "first-load @ $viewport.label 经 ViewState 契约无违规",
    async (testCase) => {
      expect(await checkStateContract(testCase)).toEqual([]);
    },
  );

  it("两视口腿渲染逐字节相等（骨架自身也与断点无关）", async () => {
    const wide = await render(matrixCaseFor("first-load", "1440x900").props);
    const narrow = await render(matrixCaseFor("first-load", "1024x768").props);
    expect(wide.length).toBeGreaterThan(0);
    expect(narrow).toBe(wide);
  });
});
