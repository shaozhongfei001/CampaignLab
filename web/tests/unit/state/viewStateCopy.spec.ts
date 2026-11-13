/**
 * web/tests/unit/state/viewStateCopy.spec.ts —— 文案逐字守卫（M0-03b / S2，D-011）
 *
 * 口径：copyOf 的每个字段必须是 spec/CampaignLab-SDD-v1.0/ui/COMMON.md **磁盘原文**（按冻结登记 §3.3
 * 映射表的行号取「行为」列）的连续子串；渲染进产物的也是同一串；错误两态的标题载体是服务端原样串。
 * 任何改写措辞、组件自编文案、行号漂移都在这里判红。行号本身是契约（§5 第 3 行：改映射须走 CR）。
 */
import { describe, expect, it } from "vitest";
import type { ApiError } from "@/api/http";
import { copyOf } from "@/components/state/viewState";
import type { ViewStateAction, ViewStateKind } from "@/components/state/viewState";
import {
  buttonNames,
  commonBehavior,
  commonLine,
  dataActions,
  EXPECTED_ACTIONS,
  expectedCopyOf,
  FROZEN_STATE_KINDS,
  matrixCaseFor,
  NON_PROBLEM_TITLE,
  renderCase,
  renderProps,
  reusedSource,
  sixStateMatrix,
  stateSource,
  stripTags,
} from "./stateMatrix";

/** §3.3 映射表：态 → 文案来源行（pending-fill 由 :30 + :36 两段拼接）。 */
const COPY_LINES: Record<ViewStateKind, readonly number[]> = {
  "first-load": [27],
  "no-record": [28],
  failed: [31],
  "partial-comparable": [30],
  "pending-fill": [30, 36],
  "stale-412": [32],
};

/** 动作键 → 名称出处行（:28 创建/导入/清空筛选、:30 导出、:32 重新获取/复跑；:38 要求有名称）。 */
const ACTION_LINES: Record<ViewStateAction, readonly number[]> = {
  create: [28],
  import: [28],
  "clear-filter": [28],
  export: [30],
  refetch: [32],
  rerun: [32],
};

const SEPARATORS = /[；;]/;

/** 返回「不是给定行原文连续子串」的片段清单（检查器有正/负例自证，见下）。 */
function nonVerbatim(value: string, lines: readonly number[]): string[] {
  const haystack = lines.map((no) => commonBehavior(no)).join("\n");
  return value
    .split(SEPARATORS)
    .map((part) => part.split("。")[0] ?? "")
    .map((part) => part.trim())
    .filter((part) => part.length > 0)
    .filter((part) => !haystack.includes(part));
}

const isErrorState = (state: ViewStateKind): boolean => state === "failed" || state === "stale-412";

describe("扫描通道与规范行锚点", () => {
  it("六态引用的七行原文都拿到磁盘内容（行号漂移即判红）", () => {
    for (const no of [27, 28, 29, 30, 31, 32, 36]) {
      expect(commonLine(no).length, "COMMON.md:" + String(no)).toBeGreaterThan(0);
      expect(commonBehavior(no).length, "COMMON.md:" + String(no) + " 行为列").toBeGreaterThan(0);
    }
    expect(commonBehavior(27)).toContain("主区骨架");
    expect(commonBehavior(36)).toContain("\u2014");
    expect(commonBehavior(29)).toContain("上一结果");
  });

  it("检查器自证非空转：真原文零违规、改写措辞判违规", () => {
    expect(nonVerbatim(copyOf("first-load").title, COPY_LINES["first-load"])).toEqual([]);
    expect(nonVerbatim("主区骨架对应标题、表头与卡片位置", [27])).toEqual(["主区骨架对应标题、表头与卡片位置"]);
  });
});

describe.each([...FROZEN_STATE_KINDS])("copyOf(%s) 逐字对齐 ui/COMMON.md", (state) => {
  it("hint 是来源行「行为」列的连续子串", () => {
    expect(nonVerbatim(copyOf(state).hint, COPY_LINES[state])).toEqual([]);
  });

  it("title 是来源行原文子串；failed 的固定串与 AlertBanner.vue 交叉核对", () => {
    if (state === "failed") {
      expect(copyOf(state).title).toBe(NON_PROBLEM_TITLE);
      expect(reusedSource("AlertBanner.vue")).toContain('"' + NON_PROBLEM_TITLE + '"');
      expect(nonVerbatim(copyOf(state).title, [31])).not.toEqual([]);
      return;
    }
    expect(nonVerbatim(copyOf(state).title, COPY_LINES[state])).toEqual([]);
  });
});

describe.each(sixStateMatrix())("$state @ $viewport.label 渲染出的文案就是规范原文", (testCase) => {
  it("渲染文本含该态解析后的 title / hint 原串", async () => {
    const text = stripTags(await renderCase(testCase));
    if (testCase.state === "first-load") {
      expect(text).toBe("");
      return;
    }
    const want = expectedCopyOf(testCase.state, testCase.props);
    expect(want.hint).not.toBeNull();
    expect(text).toContain(want.hint ?? "");
    expect(text).toContain(want.title ?? "");
  });

  it("源自 copyOf 的两串逐字来自绑定行", () => {
    const copy = copyOf(testCase.state);
    const lines = COPY_LINES[testCase.state];
    if (testCase.state === "failed") return;
    expect(nonVerbatim(copy.hint, lines)).toEqual([]);
    if (!isErrorState(testCase.state) && typeof testCase.props["title"] !== "string") {
      expect(nonVerbatim(copy.title, lines)).toEqual([]);
    }
  });

  it("错误态：服务端 title / detail / request_id 原样可见，前端不另编（§1.3 / ADR-005 §2.2）", async () => {
    if (!isErrorState(testCase.state)) return;
    const text = stripTags(await renderCase(testCase));
    const error = testCase.props["error"] as ApiError;
    expect(text).toContain(error.kind === "problem" ? error.title : NON_PROBLEM_TITLE);
    expect(text).toContain("request_id " + error.requestId);
    if (error.kind === "problem") expect(text).toContain(error.detail);
  });
});

describe("动作键名称与「上一结果」标识（:38 / :29）", () => {
  it("六态默认动作按钮的可见名称逐字取自各自绑定行", async () => {
    for (const state of FROZEN_STATE_KINDS) {
      const want = EXPECTED_ACTIONS[state];
      if (want.length === 0) continue;
      const html = await renderCase(matrixCaseFor(state));
      const keys = dataActions(html);
      const names = buttonNames(html);
      expect(keys).toEqual([...want]);
      expect(names).toHaveLength(want.length);
      keys.forEach((key, index) => {
        const action = key as ViewStateAction;
        expect(ACTION_LINES[action]).toBeDefined();
        expect(nonVerbatim(names[index] ?? "", ACTION_LINES[action]), key + " 的名称").toEqual([]);
      });
    }
  });

  it("import 动作名（页面显式传入时）同样取自 :28 原文", async () => {
    const html = await renderProps({ state: "no-record", actions: ["import"] });
    expect(nonVerbatim(buttonNames(html)[0] ?? "", ACTION_LINES.import)).toEqual([]);
  });

  it("「上一结果」是 :29 原文子串，且在 showPrevious 时可见", async () => {
    expect(nonVerbatim("上一结果", [29])).toEqual([]);
    expect(stripTags(await renderCase(matrixCaseFor("stale-412")))).toContain("上一结果");
  });
});

describe("件内样板无夹带措辞", () => {
  it("viewState.ts 磁盘原文里就是同一串（渲染值与源码常量之间无二次加工）", () => {
    const source = stateSource("viewState.ts");
    for (const state of FROZEN_STATE_KINDS) {
      expect(source, state).toContain(copyOf(state).title);
      expect(source, state).toContain(copyOf(state).hint);
    }
  });
});
