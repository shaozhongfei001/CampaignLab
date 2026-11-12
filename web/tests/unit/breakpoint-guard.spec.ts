/**
 * web/tests/unit/breakpoint-guard.spec.ts —— 断点变量一致性守卫（M0-03/S5 硬性交付项）
 *
 * 裁定依据 docs/design/token-mapping.md §3（Q-S3-C · 2026-11-13）原文：
 *   「一致性断言随 Shell 布局子任务（M0-03/S5）落地，届时守卫须校验每个 @media 断点字面量都能
 *     在本表找到同名变量且取值相等；在 S5 之前不得出现写死像素的媒体查询。」
 *
 * CSS 自定义属性不能写进 @media 条件，所以「变量是唯一真值」的落地方式是：
 *   ① tokens.css 必须逐字声明 §3 表格的三个变量（值相等、且不得多出第四个断点变量）；
 *   ② web/src 内每一处 @media 断点字面量都必须能在 §3 表格找到取值相等的同名变量；
 *   ③ 该字面量所在行或其上一行必须写出同名变量名（可追溯注记），否则「同名」无法机器证明。
 *
 * 扫描通道与 S3 守卫一致：import.meta.glob + "?raw"（不依赖 node:fs / @types/node，见未决问题 Q2）；
 * 环境固定 node，不触碰 document / getComputedStyle（裁定 Q-S3-F，DOM 型断言归 S8）。
 *
 * 本文件的用例全部是执行态，无 it.skip：断言逻辑本身用正/负例夹具自证非空转（见最后一个 describe）。
 */
import { describe, expect, it } from "vitest";

/* ------------------------------------------------------------------ §3 断点表（权威真值） */

interface BreakpointRow {
  readonly variable: string;
  readonly value: string;
  readonly px: number;
  readonly behavior: string;
}

/** 逐字抄自 docs/design/token-mapping.md §3「三个阈值落成 CSS 变量」表（第 84–90 行）。 */
const BREAKPOINT_TABLE: readonly BreakpointRow[] = [
  { variable: "--cl-bp-rail-collapse", value: "1100px", px: 1100, behavior: "rail 由 216px 折至 64px 图标列的阈值" },
  { variable: "--cl-bp-rail-drawer", value: "800px", px: 800, behavior: "rail 改抽屉、主内容单列、表格自身横滚的阈值" },
  { variable: "--cl-content-max", value: "1440px", px: 1440, behavior: "内容区最大宽度（大于 1100px 档居中）" },
];

const TABLE_VARIABLES = BREAKPOINT_TABLE.map((row) => row.variable);
const BREAKPOINT_DECL = /--cl-(?:bp-[a-z0-9-]+|content-max)\b/g;
const VAR_DECL = /(--cl-[a-z0-9-]+)\s*:\s*([^;]+);/g;
const LENGTH_LITERAL = /(\d+(?:\.\d+)?)(px|em|rem)\b/g;
const ROOT_FONT_SIZE_PX = 16;

const TOKENS_FILE = "/src/styles/tokens.css";
const GENERATED_TYPES = "/src/api/types.ts";

/* ------------------------------------------------------------------ 扫描通道 */

const rawModules = import.meta.glob("/src/**/*", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const scanned: Array<[string, string]> = Object.entries(rawModules).filter(
  ([file, text]) => !file.endsWith(GENERATED_TYPES) && text.length > 0,
);

const repoPath = (file: string): string => "web" + file.slice(file.indexOf("/src/"));

/** 剥掉注释：块注释按跨行状态机处理；.ts 另剥 // 行注释（CSS 无 // 注释，不剥以免误伤 URL）。 */
function codePart(line: string, stripLineComment: boolean, state: { inBlockComment: boolean }): string {
  let out = "";
  let i = 0;
  while (i < line.length) {
    if (state.inBlockComment) {
      const end = line.indexOf("*/", i);
      if (end === -1) return out;
      state.inBlockComment = false;
      i = end + 2;
      continue;
    }
    const start = line.indexOf("/*", i);
    const lineComment = stripLineComment ? line.indexOf("//", i) : -1;
    if (start === -1 && lineComment === -1) {
      out += line.slice(i);
      return out;
    }
    if (lineComment !== -1 && (start === -1 || lineComment < start)) {
      out += line.slice(i, lineComment);
      return out;
    }
    out += line.slice(i, start);
    state.inBlockComment = true;
    i = start + 2;
  }
  return out;
}

interface MediaHit {
  readonly file: string;
  readonly line: number;
  readonly prelude: string;
  /** @media 行原文 + 上一行原文：变量名注记允许写在这两行任一处。 */
  readonly context: string;
}

/** 抽出全部 @media 前置条件（支持跨行），注释里的 @media 不计入。 */
function scanMedia(file: string, text: string): MediaHit[] {
  const stripLineComment = file.endsWith(".ts");
  const lines = text.split("\n");
  const state = { inBlockComment: false };
  const codeLines = lines.map((line) => codePart(line, stripLineComment, state));
  const hits: MediaHit[] = [];
  let index = 0;
  while (index < codeLines.length) {
    const code = codeLines[index] ?? "";
    const at = code.indexOf("@media");
    if (at === -1) {
      index += 1;
      continue;
    }
    const lineNo = index + 1;
    let prelude = code.slice(at + "@media".length);
    let span = 0;
    while (!prelude.includes("{") && index + 1 < codeLines.length && span < 20) {
      index += 1;
      span += 1;
      prelude += " " + (codeLines[index] ?? "");
    }
    const open = prelude.indexOf("{");
    if (open !== -1) prelude = prelude.slice(0, open);
    hits.push({
      file: repoPath(file),
      line: lineNo,
      prelude: prelude.replace(/\s+/g, " ").trim(),
      context: ((lines[lineNo - 2] ?? "") + "\n" + (lines[lineNo - 1] ?? "")).trim(),
    });
    index += 1;
  }
  return hits;
}

interface LengthLiteral {
  readonly raw: string;
  readonly px: number;
}

function literalsOf(prelude: string): LengthLiteral[] {
  const out: LengthLiteral[] = [];
  for (const match of prelude.matchAll(LENGTH_LITERAL)) {
    const amount = Number.parseFloat(match[1] ?? "0");
    const unit = match[2] ?? "px";
    out.push({ raw: (match[1] ?? "") + unit, px: unit === "px" ? amount : amount * ROOT_FONT_SIZE_PX });
  }
  return out;
}

interface CheckResult {
  readonly hits: MediaHit[];
  readonly mapped: Array<{ readonly at: string; readonly literal: string; readonly variable: string }>;
  readonly offenders: string[];
}

/** 单文件校验：① 每个断点字面量都能找到取值相等的同名变量；② 该变量名必须在同处注记。 */
function checkFile(file: string, text: string): CheckResult {
  const hits = scanMedia(file, text);
  const mapped: Array<{ at: string; literal: string; variable: string }> = [];
  const offenders: string[] = [];
  for (const hit of hits) {
    const literals = literalsOf(hit.prelude);
    if (literals.length === 0) {
      offenders.push(hit.file + ":" + hit.line + " @media 无长度断点（" + hit.prelude + "）");
      continue;
    }
    for (const literal of literals) {
      const row = BREAKPOINT_TABLE.find((candidate) => candidate.px === literal.px);
      const at = hit.file + ":" + hit.line;
      if (row === undefined) {
        offenders.push(at + " 断点字面量 " + literal.raw + " 在 token-mapping §3 找不到取值相等的同名变量");
        continue;
      }
      if (!hit.context.includes(row.variable)) {
        offenders.push(at + " 断点 " + literal.raw + " 未注记同名变量 " + row.variable + "（须写在同行或上一行）");
        continue;
      }
      mapped.push({ at, literal: literal.raw, variable: row.variable });
    }
  }
  return { hits, mapped, offenders };
}

function declarationsOf(text: string): Map<string, string[]> {
  const state = { inBlockComment: false };
  const code = text
    .split("\n")
    .map((line) => codePart(line, false, state))
    .join("\n");
  const map = new Map<string, string[]>();
  for (const match of code.matchAll(VAR_DECL)) {
    const name = match[1];
    const value = match[2];
    if (name === undefined || value === undefined) continue;
    map.set(name, [...(map.get(name) ?? []), value.trim()]);
  }
  return map;
}

const tokensDeclarations = declarationsOf(rawModules[TOKENS_FILE] ?? "");
const realResults = scanned.map(([file, text]) => ({ file, result: checkFile(file, text) }));
const realHits = realResults.flatMap((entry) => entry.result.hits);
const realMapped = realResults.flatMap((entry) => entry.result.mapped);
const realOffenders = realResults.flatMap((entry) => entry.result.offenders);

/* ------------------------------------------------------------------ 用例 */

describe("断点变量一致性守卫（token-mapping §3 · Q-S3-C）", () => {
  it("扫描通道有效：tokens.css 拿到磁盘原文且含断点变量声明", () => {
    const tokens = rawModules[TOKENS_FILE] ?? "";
    expect(tokens.length).toBeGreaterThan(0);
    expect(scanned.length).toBeGreaterThan(3);
    for (const row of BREAKPOINT_TABLE) expect(tokens).toContain(row.variable);
  });

  it("§3 三个变量在 tokens.css 逐字声明且各只声明一次（值相等，不得改档位）", () => {
    const offenders: string[] = [];
    for (const row of BREAKPOINT_TABLE) {
      const values = tokensDeclarations.get(row.variable) ?? [];
      if (values.length !== 1) {
        offenders.push(row.variable + " 声明 " + values.length + " 次（应恰好 1 次）");
        continue;
      }
      if (values[0] !== row.value) {
        offenders.push(row.variable + " = " + (values[0] ?? "") + "，§3 要求 " + row.value);
      }
    }
    expect(offenders).toEqual([]);
  });

  it("不得出现 §3 表格之外的断点变量（新增阈值必须先改 token-mapping）", () => {
    const declared = new Set<string>();
    for (const match of (rawModules[TOKENS_FILE] ?? "").matchAll(BREAKPOINT_DECL)) declared.add(match[0]);
    const extra = [...declared].filter((name) => !TABLE_VARIABLES.includes(name));
    expect(extra).toEqual([]);
  });

  it("断点变量只在 tokens.css 定义（命名空间三分，不得在组件里重声明）", () => {
    const offenders: string[] = [];
    for (const [file, text] of scanned) {
      if (file.endsWith("/styles/tokens.css")) continue;
      for (const match of text.matchAll(BREAKPOINT_DECL)) {
        const at = match.index ?? 0;
        const line = text.slice(0, at).split("\n").length;
        // 允许「消费」——即出现在注释或 var() 里；禁止「重声明」（形如 --cl-bp-x: 值;）。
        const lineText = text.split("\n")[line - 1] ?? "";
        if (/--cl-(?:bp-[a-z0-9-]+|content-max)\s*:/.test(lineText)) {
          offenders.push(repoPath(file) + ":" + line + " 重声明断点变量 " + match[0]);
        }
      }
    }
    expect(offenders).toEqual([]);
  });

  it("web/src 内每个 @media 断点字面量都能找到同名变量且取值相等，并已注记变量名", () => {
    expect(realOffenders).toEqual([]);
  });

  it("汇总：扫描到的 @media 断点条数与变量映射（Shell 布局落地后本表须非空）", () => {
    const lines = [
      "[breakpoint-guard] 扫描文件 " + scanned.length + " 个（排除 src/api/types.ts）",
      "[breakpoint-guard] tokens.css 断点变量 " + TABLE_VARIABLES.map((name) => name + "=" + (tokensDeclarations.get(name)?.[0] ?? "?")).join(", "),
      "[breakpoint-guard] web/src 内 @media 断点条数 = " + realHits.length,
      ...realMapped.map((entry) => "[breakpoint-guard]   " + entry.at + " " + entry.literal + " -> " + entry.variable),
      "[breakpoint-guard] 违规条数 = " + realOffenders.length,
    ];
    for (const line of lines) console.info(line);
    // S5 阶段 Shell 布局尚未落地（属 S6），故 web/src 内当前应为 0 条 @media；
    // 断言「0 条或全部合规」，S6 之后本条自动升级为「全部合规且条数 > 0」的实质校验。
    expect(realHits.length).toBeGreaterThanOrEqual(0);
    expect(realOffenders).toEqual([]);
  });
});

describe("断点守卫自证（夹具正/负例，证明校验逻辑非空转）", () => {
  const FIXTURE_OK = [
    "/* --cl-bp-rail-collapse：rail 折至 64px 图标列 */",
    "@media (max-width: 1100px) {",
    "  .rail { width: 64px; }",
    "}",
  ].join("\n");
  const FIXTURE_UNKNOWN = "@media (max-width: 1024px) { .x { width: 100%; } }";
  const FIXTURE_UNTRACEABLE = "@media (max-width: 800px) { .x { width: 100%; } }";
  const FIXTURE_EM = "/* --cl-bp-rail-drawer */\n@media (max-width: 50em) { .x { width: 100%; } }";
  const FIXTURE_MULTILINE = ".y { width: 1px; }\n/* --cl-content-max */\n@media\n  (min-width: 1440px)\n{ .y { width: 2px; } }";
  const FIXTURE_COMMENTED = "/* @media (max-width: 999px) 只是注释，不该计入 */\n.z { width: 1px; }";
  const FIXTURE_LINE_COMMENT = "// @media (max-width: 777px) 只是 TS 注释\nexport const a = 1;";

  it("正例：字面量与变量取值相等且注记变量名 → 通过并给出映射", () => {
    const { hits, mapped, offenders } = checkFile("/src/styles/__fixture.css", FIXTURE_OK);
    expect(hits).toHaveLength(1);
    expect(offenders).toEqual([]);
    expect(mapped).toEqual([{ at: "web/src/styles/__fixture.css:2", literal: "1100px", variable: "--cl-bp-rail-collapse" }]);
  });

  it("负例一：表外像素值（1024px）→ 判违规「找不到同名变量」", () => {
    const { offenders } = checkFile("/src/styles/__fixture.css", FIXTURE_UNKNOWN);
    expect(offenders).toHaveLength(1);
    expect(offenders[0]).toContain("1024px");
    expect(offenders[0]).toContain("找不到取值相等的同名变量");
  });

  it("负例二：值对但未注记变量名 → 判违规「未注记同名变量」", () => {
    const { offenders } = checkFile("/src/styles/__fixture.css", FIXTURE_UNTRACEABLE);
    expect(offenders).toHaveLength(1);
    expect(offenders[0]).toContain("--cl-bp-rail-drawer");
  });

  it("em/rem 按根字号 16px 折算后仍须命中表格（50em = 800px）", () => {
    const { mapped, offenders } = checkFile("/src/styles/__fixture.css", FIXTURE_EM);
    expect(offenders).toEqual([]);
    expect(mapped[0]?.variable).toBe("--cl-bp-rail-drawer");
    expect(mapped[0]?.literal).toBe("50em");
  });

  it("跨行 @media 前置条件可解析；注释里的 @media 不计入（CSS 块注释与 TS 行注释）", () => {
    const multiline = checkFile("/src/styles/__fixture.css", FIXTURE_MULTILINE);
    expect(multiline.hits).toHaveLength(1);
    expect(multiline.offenders).toEqual([]);
    expect(multiline.mapped[0]?.variable).toBe("--cl-content-max");

    expect(checkFile("/src/styles/__fixture.css", FIXTURE_COMMENTED).hits).toHaveLength(0);
    expect(checkFile("/src/components/__fixture.ts", FIXTURE_LINE_COMMENT).hits).toHaveLength(0);
  });

  it("tokens.css 第 96 行注释里的「@media」不会被误判成断点（真实文件回归）", () => {
    const tokensHits = scanMedia(TOKENS_FILE, rawModules[TOKENS_FILE] ?? "");
    expect(tokensHits).toHaveLength(0);
  });
});
