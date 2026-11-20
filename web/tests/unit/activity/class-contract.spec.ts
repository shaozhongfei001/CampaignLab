/**
 * web/tests/unit/activity/class-contract.spec.ts —— 机器门禁第 6 条「用到的 class 都有定义」
 *
 * 对应模板 tools/_check_used.py 的 UNDEFINED=[] 口径，落到项目侧：
 * UI-02 页面模板里出现的每个 class 令牌，都必须能在**同文件 <style> 块**或 web/src/styles/project.css 找到选择器定义。
 * 判据结构性（解析 class 属性值与 CSS 选择器），并配负对照证明检查函数不是恒真。
 */
import { describe, expect, it } from "vitest";

const pageFiles = import.meta.glob("/src/pages/activity/*.vue", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;
const projectCss = import.meta.glob("/src/styles/project.css", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;
// UI-02 的逻辑面源文件（只读原文）：门禁 7 「行尾 + 接行首 +」对它们一并扫描。
const logicFiles = import.meta.glob(
  ["/src/features/activity/*.ts", "/src/composables/useActivities.ts", "/src/pages/activity/*.ts"],
  { query: "?raw", import: "default", eager: true },
) as Record<string, string>;

/** 按文件名取页面源码（禁写死下标 / 禁依赖 glob 返回顺序）。 */
function readPage(name: string): string {
  const key = Object.keys(pageFiles).find((path) => path.endsWith("/" + name));
  return key === undefined ? "" : (pageFiles[key] ?? "");
}

const CLASS_ATTR = /\sclass="([^"]*)"/g;
const CLASS_SELECTOR = /\.(-?[A-Za-z_][A-Za-z0-9_-]*)/g;

function templateOf(source: string): string {
  const start = source.indexOf("<template>");
  const end = source.lastIndexOf("</template>");
  return start === -1 || end === -1 || end <= start ? "" : source.slice(start, end);
}

function stylesOf(source: string): string {
  const out: string[] = [];
  for (const match of source.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)) {
    const body = match[1];
    if (body !== undefined) out.push(body);
  }
  return out.join("\n");
}

function usedClasses(template: string): string[] {
  const out = new Set<string>();
  for (const match of template.matchAll(new RegExp(CLASS_ATTR.source, "g"))) {
    const value = match[1] ?? "";
    for (const token of value.split(/\s+/)) {
      if (token.length > 0) out.add(token);
    }
  }
  return [...out];
}

function definedClasses(css: string): Set<string> {
  const out = new Set<string>();
  const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const match of withoutComments.matchAll(new RegExp(CLASS_SELECTOR.source, "g"))) {
    const name = match[1];
    if (name !== undefined) out.add(name);
  }
  return out;
}

const GLOBAL_CSS = definedClasses(Object.values(projectCss).join("\n"));

function undefinedClasses(source: string): string[] {
  const defined = definedClasses(stylesOf(source));
  return usedClasses(templateOf(source))
    .filter((name) => !defined.has(name) && !GLOBAL_CSS.has(name))
    .sort();
}

describe("扫描通道有效", () => {
  it("UI-02 页面源码与 project.css 都读到内容", () => {
    // 本目录两件 .vue：主页面 + 首载骨架的 variant 呈现件（M0-03b-freeze.md §4.2 注册扩展点）。
    expect(Object.keys(pageFiles).map((path) => path.split("/").pop()).sort()).toEqual([
      "ActivityFirstLoad.vue",
      "ActivityListPage.vue",
    ]);
    expect(Object.keys(logicFiles).length).toBeGreaterThanOrEqual(6);
    const source = readPage("ActivityListPage.vue");
    expect(source.length).toBeGreaterThan(1000);
    expect(templateOf(source).length).toBeGreaterThan(500);
    expect(stylesOf(source).length).toBeGreaterThan(200);
    expect(GLOBAL_CSS.size).toBeGreaterThan(0);
  });
});

describe("机器门禁 6：class 全部有定义", () => {
  it("UI-02 两件页面源码模板用到的 class 无未定义项", () => {
    for (const [path, source] of Object.entries(pageFiles)) {
      if (path.endsWith("ActivityListPage.vue")) expect(usedClasses(templateOf(source)).length).toBeGreaterThan(8);
      expect(undefinedClasses(source), path).toEqual([]);
    }
  });

  it("负对照：检查函数能判出伪造 class（证明不是恒真）", () => {
    const fake = [
      "<template>",
      '  <div class="cl-real cl-totally-fake">x</div>',
      "</template>",
      "<style scoped>",
      ".cl-real { display: block; }",
      "</style>",
    ].join("\n");
    expect(undefinedClasses(fake)).toEqual(["cl-totally-fake"]);
  });

  it("负对照：全局 project.css 里定义的 class 不算未定义（.num / .mono）", () => {
    const fake = ['<template><span class="num mono">1</span></template>', "<style scoped></style>"].join("\n");
    expect(undefinedClasses(fake)).toEqual([]);
    expect(GLOBAL_CSS.has("num")).toBe(true);
    expect(GLOBAL_CSS.has("mono")).toBe(true);
  });
});

describe("机器门禁 7：禁「行尾 + 接行首 +」写法（会被解析成 a + (+b) 产生 NaN）", () => {
  it("UI-02 相关源文件里不存在该写法", () => {
    const offenders: string[] = [];
    const files: Record<string, string> = { ...pageFiles, ...logicFiles };
    for (const [name, source] of Object.entries(files)) {
      const lines = source.split("\n");
      for (let index = 0; index + 1 < lines.length; index += 1) {
        const current = (lines[index] ?? "").trimEnd();
        const next = (lines[index + 1] ?? "").trimStart();
        if (current.endsWith("+") && next.startsWith("+")) offenders.push(name + ":" + String(index + 1));
      }
    }
    expect(offenders).toEqual([]);
  });

  it("负对照：检查逻辑能判出伪造样本", () => {
    const bad = 'const text = "a"\n  + "b";';
    const lines = bad.split("\n");
    const hit = (lines[0] ?? "").trimEnd().endsWith("+") && (lines[1] ?? "").trimStart().startsWith("+");
    expect(hit).toBe(false);
    const reallyBad = ["const text = \"a\" +", "+ \"b\";"].join("\n");
    const badLines = reallyBad.split("\n");
    expect((badLines[0] ?? "").trimEnd().endsWith("+") && (badLines[1] ?? "").trimStart().startsWith("+")).toBe(true);
  });
});
