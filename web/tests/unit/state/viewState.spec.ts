/**
 * web/tests/unit/state/viewState.spec.ts —— 六态参数化矩阵（M0-03b / S2）
 *
 * 矩阵：六态（§1.2 冻结字面量）× 视口标签 {1440x900, 1024x768}（§7「S2」）。
 * 断言项：data-state、role / aria-live / aria-busy、文案、动作键集合与 data-action、— + 原因、
 * 两错误态的 request_id 可见（§3.4 不变量 + §1.3 四条非颜色载体）。用例数以 rc 为判据，不写死数量（§15.10）。
 *
 * 窄屏 1024x768 一腿只做 vitest 可行的三件事（裁定 A135：真实窄屏截图归 M1-04，本卡不建 e2e harness）：
 *   ① 视口不变性 —— 同一 props 在两腿渲染逐字节相等，断点不吞语义属性；
 *   ② matchMedia mock —— 六态件不自行判定断点（调用次数 0；断点归 AppShell 与 tokens.css，本卡禁改）；
 *   ③ 源码级窄屏纪律 —— state/** 零 @media、零自造 data-narrow、零固定 px 宽度、零色值字面量。
 * 本文件不谎称做过真实视口/布局渲染（vitest 环境固定 node，见 web/vitest.config.ts 顶部裁定）。
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { AUTHORITATIVE_PROBLEM_CODES } from "@/features/shared/problemPresentation";
import {
  actionsOf,
  copyOf,
  stateFromError,
  VIEW_STATE_DEV_NOTICES,
  VIEW_STATE_KINDS,
} from "@/components/state/viewState";
import type { ViewStateKind } from "@/components/state/viewState";
import {
  buttonNames,
  checkStateContract,
  codeOfBucket,
  dataActions,
  errorStub,
  EXPECTED_ACTIONS,
  FORBIDDEN_IN_STATE,
  FROZEN_STATE_KINDS,
  matrixCaseFor,
  renderCase,
  renderProps,
  rootAttr,
  sixStateMatrix,
  stateSource,
  stripComments,
  stripTags,
  VIEWPORTS,
} from "./stateMatrix";

const STATE_FILES: readonly string[] = [
  "viewState.ts",
  "registry.ts",
  "ViewState.vue",
  "FirstLoadSkeleton.vue",
  "MissingValue.vue",
  "index.ts",
];

function stateSources(): Array<[string, string]> {
  return STATE_FILES.map((file): [string, string] => [file, stateSource(file)]);
}

/** 门禁只判代码：注释里的中文说明（例如「不 fetch、不 axios」）不算使用。 */
function codeSources(): Array<[string, string]> {
  return STATE_FILES.map((file): [string, string] => [file, stripComments(stateSource(file))]);
}

const MATRIX = sixStateMatrix().map((item) => ({
  ...item,
  title: item.state + " @ " + item.viewport.label,
}));

afterEach(() => {
  vi.unstubAllGlobals();
});

describe.each(MATRIX)("$title", (testCase) => {
  it("六态契约无违规（data-state / role / aria / 文案 / 动作键 / 缺项 / request_id）", async () => {
    expect(await checkStateContract(testCase)).toEqual([]);
  });

  it("两视口腿的语义呈现逐字节相等（1024x768 不丢状态语义）", async () => {
    const other = testCase.viewport.label === "1440x900" ? "1024x768" : "1440x900";
    expect(await renderCase(matrixCaseFor(testCase.state, other))).toEqual(await renderCase(testCase));
  });

  it("matchMedia mock：六态件不自行判定断点，呈现与未 mock 时一致", async () => {
    const before = await renderCase(testCase);
    const media = vi.fn((query: string) => ({
      matches: testCase.viewport.narrow && query === "(max-width: 1100px)",
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }));
    vi.stubGlobal("matchMedia", media);
    expect(await renderCase(testCase)).toEqual(before);
    expect(media).not.toHaveBeenCalled();
  });
});

describe("六态枚举与默认动作键（§1.2 / §1.3 冻结表）", () => {
  it("VIEW_STATE_KINDS 整序等于冻结的六个字面量，且无第七态", () => {
    expect([...VIEW_STATE_KINDS]).toEqual([...FROZEN_STATE_KINDS]);
  });

  it.each([...FROZEN_STATE_KINDS])("actionsOf(%s) 等于 §1.3「默认动作键」列", (state) => {
    expect([...actionsOf(state)]).toEqual([...EXPECTED_ACTIONS[state]]);
  });
});

describe("props 覆写与 append-only 扩展（§3.4）", () => {
  it("actions prop 显式给定即整组替换默认集", async () => {
    expect(dataActions(await renderProps({ state: "no-record", actions: ["import"] }))).toEqual(["import"]);
  });

  it("actions prop 给空数组时不渲染动作区（口径同 EmptyState.vue:9）", async () => {
    const html = await renderProps({ state: "partial-comparable", actions: [], missing: ["渠道 A 明细"], reason: "共同子集外" });
    expect(dataActions(html)).toEqual([]);
    expect(html).not.toContain('data-part="actions"');
  });

  it("title / hint prop 优先级高于 copyOf（F-4 第一优先级）", async () => {
    const text = stripTags(await renderProps({ state: "pending-fill", title: "页面原文标题", hint: "页面原文提示" }));
    expect(text).toContain("页面原文标题");
    expect(text).toContain("页面原文提示");
    expect(text).not.toContain(copyOf("pending-fill").hint);
  });

  it("missing 只在两态渲染，其余四态即使传入也不出缺项区（§3.4 约束列）", async () => {
    for (const state of ["first-load", "no-record", "failed", "stale-412"] as const) {
      const props: Record<string, unknown> = { state, missing: ["渠道 A 明细"], reason: "不该出现的原因" };
      if (state === "failed" || state === "stale-412") props["error"] = errorStub({ requestId: "rid-x" });
      expect(await renderProps(props)).not.toContain('data-part="missing"');
    }
    for (const state of ["partial-comparable", "pending-fill"] as const) {
      expect(await renderProps({ state, missing: ["渠道 A 明细"], reason: "共同子集外" })).toContain('data-part="missing"');
    }
  });
});

describe("组合复用而非二次实现（§2 F-2 / F-3）", () => {
  it("两错误态复用 AlertBanner（其根 class 与 request_id 行由该件产出）", async () => {
    for (const state of ["failed", "stale-412"] as const) {
      const html = await renderCase(matrixCaseFor(state));
      expect(html).toContain('class="cl-alert"');
      expect(stripTags(html)).toContain("request_id ");
    }
  });

  it("no-record / partial-comparable / pending-fill 复用 EmptyState", async () => {
    for (const state of ["no-record", "partial-comparable", "pending-fill"] as const) {
      expect(await renderCase(matrixCaseFor(state))).toContain('class="cl-empty"');
    }
  });

  it("first-load 复用 FirstLoadSkeleton，且调度件不内联骨架结构", async () => {
    expect(await renderCase(matrixCaseFor("first-load"))).toContain('data-part="first-load-skeleton"');
    expect(stripComments(stateSource("ViewState.vue"))).not.toContain("cl-skeleton__cell");
  });
});

describe("slots 与动作按钮（§3.4 slots / :38 图标按钮须有名称）", () => {
  it("三槽按需渲染，未给定时不留空容器；给定 variant 覆写呈现时槽位仍可用", async () => {
    const bare = await renderProps({ state: "no-record" });
    for (const part of ["body", "footer", "evidence"]) expect(bare).not.toContain('data-part="' + part + '"');
    const full = await renderProps({ state: "no-record" }, {
      default: () => "对照明细",
      footer: () => "页脚补充",
      evidence: () => "证据入口",
    });
    for (const words of ["对照明细", "页脚补充", "证据入口"]) expect(stripTags(full)).toContain(words);
  });

  it("每个动作都是原生 button（Enter / Space 天然可激活）且有可见名称", async () => {
    const html = await renderCase(matrixCaseFor("stale-412"));
    expect(dataActions(html)).toEqual(["refetch", "rerun"]);
    const names = buttonNames(html);
    expect(names).toHaveLength(2);
    expect(names.every((name) => name.trim().length > 0)).toBe(true);
    expect(html).toContain('<button type="button"');
  });
});

describe("stateFromError（§3.3 / F-A / F-B）", () => {
  it("status 412 → stale-412（problem 与非 problem 两条来源都算）", () => {
    expect(stateFromError(errorStub({ status: 412 }))).toBe("stale-412");
    expect(stateFromError(errorStub({ kind: "problem", status: 412, code: codeOfBucket("CONFLICT") }))).toBe("stale-412");
  });

  it("problem 且分桶 CONFLICT → stale-412（由 presentationOf 判定，非 code 白名单）", () => {
    const code = codeOfBucket("CONFLICT");
    expect(code.length).toBeGreaterThan(0);
    expect(stateFromError(errorStub({ kind: "problem", status: 409, code }))).toBe("stale-412");
  });

  it.each(["INPUT", "TRANSIENT", "ENTRY", "INVISIBLE"] as const)("problem 且分桶 %s → failed", (bucket) => {
    const code = codeOfBucket(bucket);
    expect(code.length).toBeGreaterThan(0);
    expect(stateFromError(errorStub({ kind: "problem", status: 400, code }))).toBe("failed");
  });

  it("非 problem（transport / timeout / aborted / payload / assertion）→ failed", () => {
    for (const kind of ["transport", "timeout", "aborted", "payload", "assertion"] as const) {
      expect(stateFromError(errorStub({ kind }))).toBe("failed");
    }
  });

  it("F-B：state/** 内不出现任何权威 problem code 字面量", () => {
    const joined = stateSources().map(([name, text]) => name + "\n" + text).join("\n");
    expect(AUTHORITATIVE_PROBLEM_CODES.length).toBeGreaterThan(0);
    expect(AUTHORITATIVE_PROBLEM_CODES.filter((code) => joined.includes('"' + code + '"'))).toEqual([]);
  });
});

describe("A137 / R-1 静态门禁与窄屏源码纪律", () => {
  it("扫描通道非空转：六个冻结文件都拿到磁盘原文", () => {
    for (const [file, text] of stateSources()) expect(text.length, file).toBeGreaterThan(0);
  });

  it("A137：无数据获取副作用 —— 不出现 fetch / axios，且 api/** 只做 type-only import", () => {
    for (const [file, text] of codeSources()) {
      expect(text.includes("fetch("), file).toBe(false);
      expect(text.includes("axios"), file).toBe(false);
      for (const line of text.split("\n")) {
        if (!line.includes("@/api/")) continue;
        expect(line.trimStart().startsWith("import type"), file + " :: " + line.trim()).toBe(true);
      }
    }
  });

  it("R-1：state/** 不 import pages/** 与 composables/**（依赖方向恒为页面 → state/）", () => {
    const joined = codeSources().map(([, text]) => text).join("\n");
    expect(joined.includes("@/pages")).toBe(false);
    expect(joined.includes("@/composables")).toBe(false);
  });

  it("窄屏纪律：state/** 零 @media、零自造 data-narrow、零 StatusTag tone 依赖、零图标字体", () => {
    for (const [file, text] of codeSources()) {
      for (const token of FORBIDDEN_IN_STATE) expect(text.includes(token), file + " 含 " + token).toBe(false);
    }
  });

  it("<style> 内宽度一律相对量或令牌，无固定 px 宽度（1024x768 不溢出）", () => {
    const offenders: string[] = [];
    for (const [file, text] of codeSources()) {
      const style = /<style[\s\S]*?<\/style>/.exec(text)?.[0] ?? "";
      for (const match of style.matchAll(/(?:^|[\s;{])(?:min-width|max-width|width)\s*:\s*([^;]+);/g)) {
        const value = (match[1] ?? "").trim();
        if (/\d+(?:\.\d+)?px/.test(value)) offenders.push(file + " :: width:" + value);
      }
    }
    expect(offenders).toEqual([]);
  });

  it("不写死色值：state/** 内无十六进制与 rgb()/hsl()（令牌唯一真值 tokens.css）", () => {
    const hits: string[] = [];
    for (const [file, text] of codeSources()) {
      if (/#(?:[0-9a-fA-F]{3,8})\b/.test(text) || /\brgba?\(/.test(text) || /\bhsla?\(/.test(text)) hits.push(file);
    }
    expect(hits).toEqual([]);
  });

  it("F-6：矩阵夹具不携带「按 status 过滤工作区」的字段", () => {
    for (const item of MATRIX) {
      for (const key of Object.keys(item.props)) expect(key).not.toMatch(/status/i);
    }
  });
});

describe.each([...VIEWPORTS])("dev 断言（§3.4：错误态必须显式给 error）@ $label", (viewport) => {
  it("错误态缺 error：根元素留机器可读标记并写入 dev 水槽（禁 console）", async () => {
    VIEW_STATE_DEV_NOTICES.length = 0;
    for (const state of ["failed", "stale-412"] as readonly ViewStateKind[]) {
      const html = await renderProps({ state });
      expect(rootAttr(html, "data-dev-assert"), state + " @" + viewport.label).toBe("error-required");
    }
    expect(VIEW_STATE_DEV_NOTICES.filter((n) => n.source === "ViewState" && n.code === "error-required")).toHaveLength(2);
  });

  it("正常给 error 时不留 dev 标记（断言不当渲染分支用）", async () => {
    expect(rootAttr(await renderProps({ state: "failed", error: errorStub({ requestId: "rid-ok" }) }), "data-dev-assert")).toBeNull();
  });
});
