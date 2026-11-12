import { describe, expect, it } from "vitest";

// S3 令牌一致性守卫（docs/design/token-mapping.md 4.1/4.2/4.4；M0-03-design.md 3；裁定 Q-S3-A/D/E/F）。
//
// 扫描通道：import.meta.glob + query "?raw"（Vite 在转换期对磁盘真实文件求值，覆盖 .css 全文、
// .vue 的 <style> 块与 .d.ts，不依赖 import 图，也不需要 node:fs / @types/node）。
// CSS 原文可读性依赖编排器写入的 web/vitest.config.ts 的 css:true（裁定 Q-S3-A）：
// css:false 时三个 .css 被 stub 成空串（实测 length=0），本文件第 1 条用例会立刻红，不会静默降级。
//
// 本文件所有断言都必须是**执行态**：任何 it.skip / it.runIf 都等于把 §4.1 出口条件交回人工走查，
// 不被接受。需要 DOM/getComputedStyle 的渲染态断言归 S8（vitest environment 固定 node，未决问题 Q1）。
//
// 后缀用 .spec.ts：vitest include 实测为 ["src/**/*.spec.ts","tests/**/*.spec.ts"]（裁定 Q-S3-B）。

const HEX6 = /#[0-9a-fA-F]{6}\b/g;
const HEX_ANY = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/g;
const VAR_DECL = /(--[a-zA-Z0-9-]+)\s*:\s*([^;]+);/g;
const CL_REF = /var\(--cl-[a-z0-9-]+\)/g;
const RGB_LINE = /^\s*(--el-[a-z0-9-]+-rgb)\s*:\s*([^;]+);\s*\/\*([^*]*)\*\/\s*$/;
const HEX6_VALUE = /^#[0-9a-fA-F]{6}$/;

const TOKENS_FILE = "/src/styles/tokens.css";
const THEME_FILE = "/src/styles/element-theme.css";
const PROJECT_FILE = "/src/styles/project.css";

const rawModules = import.meta.glob("/src/**/*", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const scanned = Object.entries(rawModules);
const read = (file: string): string => rawModules[file] ?? "";
const repoPath = (file: string): string => "web" + file.slice(file.indexOf("/src/"));
const stripComments = (text: string): string => text.replace(/\/\*[\s\S]*?\*\//g, "");

/** 除 tokens.css 外，扫描全部文件的磁盘原文，返回命中行（文件:行号）。 */
function scan(pattern: RegExp): string[] {
  const hits: string[] = [];
  for (const [file, content] of scanned) {
    if (file.endsWith("/styles/tokens.css") || content.length === 0) continue;
    content.split("\n").forEach((line, index) => {
      const re = new RegExp(pattern.source, pattern.flags.includes("g") ? pattern.flags : pattern.flags + "g");
      if (re.test(line)) hits.push(repoPath(file) + ":" + String(index + 1));
    });
  }
  return hits;
}

/** 解析一个文件里的全部自定义属性声明（注释已剥离，值取首个声明）。 */
function customProps(text: string): Map<string, string> {
  const map = new Map<string, string>();
  for (const match of stripComments(text).matchAll(VAR_DECL)) {
    const name = match[1];
    const value = match[2];
    if (!name || value === undefined) continue;
    if (!map.has(name)) map.set(name, value.trim());
  }
  return map;
}

const tokensProps = customProps(read(TOKENS_FILE));
const themeProps = customProps(read(THEME_FILE));

/** 把 var(--cl-x) 绑定解析到 tokens.css 的实际取值。 */
function boundToken(value: string): string | undefined {
  const m = /^var\((--cl-[a-z0-9-]+)\)$/.exec(value);
  return m?.[1];
}

function toRgb(hex: string): [number, number, number] | undefined {
  if (!HEX6_VALUE.test(hex)) return undefined;
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** WCAG 2.1 相对亮度：c<=0.04045 走线性段，否则 ((c+0.055)/1.055)^2.4，系数 .2126/.7152/.0722。 */
function luminance(hex: string): number | undefined {
  const rgb = toRgb(hex);
  if (!rgb) return undefined;
  const [r, g, b] = rgb;
  const lin = (c: number): number => {
    const s = c / 255;
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function contrast(fgHex: string, bgHex: string): number | undefined {
  const a = luminance(fgHex);
  const b = luminance(bgHex);
  if (a === undefined || b === undefined) return undefined;
  const hi = Math.max(a, b);
  const lo = Math.min(a, b);
  return (hi + 0.05) / (lo + 0.05);
}

/** 断言 §4.4 的对比度：角色 -> 令牌 -> 对白底与对画布均 >= 4.5。 */
function assertRatio(role: string, token: string, offenders: string[]): void {
  const fg = tokensProps.get(token);
  const card = tokensProps.get("--cl-card");
  const canvas = tokensProps.get("--cl-canvas");
  if (!fg || !card || !canvas) {
    offenders.push(role + " 缺令牌：" + token + " / --cl-card / --cl-canvas");
    return;
  }
  for (const [bgName, bg] of [
    ["白底", card],
    ["画布", canvas],
  ] as const) {
    const ratio = contrast(fg, bg);
    if (ratio === undefined) {
      offenders.push(role + " " + token + "=" + fg + " 非六位十六进制");
    } else if (ratio < 4.5) {
      offenders.push(role + " " + token + "=" + fg + " 对" + bgName + "(" + bg + ")=" + ratio.toFixed(3) + " < 4.5");
    }
  }
}

describe("令牌一致性守卫（token-mapping 4.1/4.2/4.4）", () => {
  it("扫描通道有效：三个样式文件与非 CSS 源文件都拿到磁盘原文", () => {
    for (const expected of ["/src/main.ts", "/src/App.vue", "/src/api/types.ts"]) {
      expect(Object.keys(rawModules), "缺文件 " + expected).toContain(expected);
    }
    expect(read(TOKENS_FILE).length, "tokens.css 原文长度（css:true 未生效则为 0）").toBeGreaterThan(4000);
    expect(read(THEME_FILE).length, "element-theme.css 原文长度").toBeGreaterThan(4000);
    expect(read(PROJECT_FILE).length, "project.css 原文长度").toBeGreaterThan(1000);
  });

  it("主门禁：除 styles/tokens.css 外，web/src 内不得出现六位十六进制色值", () => {
    expect(scan(HEX6)).toEqual([]);
  });

  it("扩展门禁：除 styles/tokens.css 外，web/src 内不得出现任意十六进制色值或 rgb()/rgba()/hsl()/hsla()", () => {
    expect(scan(HEX_ANY)).toEqual([]);
  });

  it("命名空间三分：--cl-* 只在 tokens.css 定义", () => {
    const offenders: string[] = [];
    for (const [file, content] of scanned) {
      if (file === TOKENS_FILE || content.length === 0) continue;
      for (const [name] of customProps(content)) {
        if (name.startsWith("--cl-")) offenders.push(repoPath(file) + " 定义 " + name);
      }
    }
    expect(offenders).toEqual([]);
    expect(tokensProps.size, "tokens.css 的 --cl-* 条数").toBeGreaterThanOrEqual(68);
  });

  it("element-theme.css 只含 --el-* 声明，且取值一律 var(--cl-*)（唯一例外：带出处的 -rgb 三元组）", () => {
    const offenders: string[] = [];
    for (const [name, value] of themeProps) {
      if (!name.startsWith("--el-")) {
        offenders.push("非 --el-* 声明：" + name);
        continue;
      }
      if (name.endsWith("-rgb")) continue;
      if (!/^var\(--cl-[a-z0-9-]+\)$/.test(value)) offenders.push(name + ": " + value + " 不是 var(--cl-*)");
    }
    expect(offenders).toEqual([]);
    expect([...themeProps.keys()].filter((n) => n.startsWith("--cl-"))).toEqual([]);
  });

  it("rgb 三元组换算一致性（Q-S3-E(c) 硬条件：由 hex 机械换算，无守卫即不成立）", () => {
    const rgbDecls = [...themeProps.keys()].filter((n) => n.endsWith("-rgb"));
    const lines = read(THEME_FILE).split("\n");
    const offenders: string[] = [];
    const checked: string[] = [];
    for (const line of lines) {
      const m = RGB_LINE.exec(line);
      if (!m) continue;
      const name = m[1];
      const value = m[2];
      const comment = m[3];
      if (!name || value === undefined || !comment) continue;
      const src = /--cl-[a-z0-9-]+/.exec(comment)?.[0];
      if (!src) {
        offenders.push(name + " 缺 --cl-* 出处注释");
        continue;
      }
      const hex = tokensProps.get(src);
      const rgb = hex ? toRgb(hex) : undefined;
      if (!rgb) {
        offenders.push(name + " 出处 " + src + " 在 tokens.css 中不是六位十六进制");
        continue;
      }
      const expected = rgb.join(", ");
      const normalized = value.replace(/\s+/g, " ").trim();
      if (normalized !== expected) offenders.push(name + " 声明 " + normalized + "，机械换算应为 " + expected + "（" + src + "=" + hex + "）");
      else checked.push(name + "=" + expected + "<-" + src);
    }
    // 先报具体不符项，再查条数：保证失败信息直接指名是哪一条三元组、换算应等于什么。
    expect(offenders).toEqual([]);
    expect(checked.length, "已复算条数须等于 -rgb 声明条数：" + rgbDecls.join(",")).toBe(rgbDecls.length);
  });

  it("project.css 不声明自定义属性，也不含色值", () => {
    const projectText = read(PROJECT_FILE);
    expect([...customProps(projectText).keys()]).toEqual([]);
    const offenders: string[] = [];
    projectText.split("\n").forEach((line, index) => {
      const re = new RegExp(HEX_ANY.source, "g");
      if (re.test(line)) offenders.push(repoPath(PROJECT_FILE) + ":" + String(index + 1));
    });
    expect(offenders).toEqual([]);
    expect(projectText).toContain("var(--cl-");
  });

  it("对比度（token-mapping 4.4）：正文/次要/表头/状态文字对白底与画布均 >= 4.5:1", () => {
    const offenders: string[] = [];
    const rows: ReadonlyArray<readonly [string, string]> = [
      ["正文", "--cl-ink-900"],
      ["次要文字", "--cl-ink-700"],
      ["表头", "--cl-ink-600"],
      ["成功状态文字", "--cl-ok-text"],
      ["警示状态文字", "--cl-warn-text"],
      ["错误状态文字", "--cl-danger-text"],
    ];
    for (const [role, token] of rows) {
      assertRatio(role, token, offenders);
    }
    expect(offenders).toEqual([]);
  });

  it("Element Plus 文字与状态色绑定后仍达标（防止把 secondary 绑回不合格档）", () => {
    const offenders: string[] = [];
    const rows: ReadonlyArray<readonly [string, string]> = [
      ["正文", "--el-text-color-primary"],
      ["常规文字", "--el-text-color-regular"],
      ["次要文字", "--el-text-color-secondary"],
      ["成功", "--el-color-success"],
      ["警示", "--el-color-warning"],
      ["错误", "--el-color-danger"],
    ];
    for (const [role, elVar] of rows) {
      const value = themeProps.get(elVar);
      const token = value ? boundToken(value) : undefined;
      if (!token) {
        offenders.push(elVar + " 未绑定 var(--cl-*)");
        continue;
      }
      assertRatio(role + " 经 " + elVar, token, offenders);
    }
    expect(offenders).toEqual([]);
  });

  it("援引 WCAG 1.4.3 豁免的两条必须把豁免写在同行注释（豁免不得口头生效）", () => {
    const offenders: string[] = [];
    for (const line of read(THEME_FILE).split("\n")) {
      const m = /^\s*(--el-text-color-(?:placeholder|disabled))\s*:/.exec(line);
      const name = m?.[1];
      if (!name) continue;
      if (!line.includes("WCAG 1.4.3")) offenders.push(name + " 绑到非 AA 档却未写豁免依据");
    }
    expect(offenders).toEqual([]);
  });

  it("悬空引用：element-theme.css 与 project.css 用到的每个 var(--cl-*) 都在 tokens.css 有定义", () => {
    const offenders: string[] = [];
    for (const file of [THEME_FILE, PROJECT_FILE]) {
      for (const match of stripComments(read(file)).matchAll(CL_REF)) {
        const token = match[0].slice(4, -1);
        if (!tokensProps.has(token)) offenders.push(repoPath(file) + " 引用未定义令牌 " + token);
      }
    }
    expect(offenders).toEqual([]);
  });
});
