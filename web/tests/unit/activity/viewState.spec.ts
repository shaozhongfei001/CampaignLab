/**
 * web/tests/unit/activity/viewState.spec.ts —— UI-02 页面态 → 六态呈现词汇的映射（穷举 + 负对照）
 *
 * M0-03b-freeze.md §5：store 的 phase 是页面私有词汇，六态是呈现层词汇，映射必须固定且不得发明第三种词汇。
 * 本文件穷举 phase × error × itemCount 的**全部组合**，断言像集恰为 REACHABLE ∪ {null}，
 * 并断言 UNREACHABLE 两态在任何组合下都不会被伪造出来（诚实边界可机器证明）。
 */
import { describe, expect, it } from "vitest";
import { VIEW_STATE_KINDS } from "@/components/state/viewState";
import {
  REACHABLE_VIEW_STATES,
  UNREACHABLE_VIEW_STATES,
  activityListViewState,
  showsPreviousResult,
} from "@/features/activity/viewState";
import type { ActivitiesPhase, ActivityListViewStateInput } from "@/features/activity/viewState";
import { makeProblem, makeTransport } from "./fixtures";

const PHASES: readonly ActivitiesPhase[] = ["idle", "loading", "ready", "empty", "failed"];
const COUNTS: readonly number[] = [0, 1, 25];
const ERRORS = [
  null,
  makeProblem(412, "REVISION_CONFLICT"),
  makeProblem(409, "IDEMPOTENCY_CONFLICT"),
  makeProblem(500, "INTERNAL_ERROR"),
  makeProblem(404, "RESOURCE_NOT_FOUND"),
  makeTransport(0),
] as const;

function combinations(): ActivityListViewStateInput[] {
  const out: ActivityListViewStateInput[] = [];
  for (const phase of PHASES) {
    for (const error of ERRORS) {
      for (const itemCount of COUNTS) out.push({ phase, error, itemCount });
    }
  }
  return out;
}

const ALL = combinations();

describe("映射的封闭性", () => {
  it("穷举组合非空（否则本文件全部断言空转）", () => {
    expect(ALL.length).toBe(PHASES.length * ERRORS.length * COUNTS.length);
  });

  it("返回值只可能是冻结的六态字面量或 null", () => {
    for (const input of ALL) {
      const result = activityListViewState(input);
      expect(result === null || VIEW_STATE_KINDS.includes(result)).toBe(true);
    }
  });

  it("像集恰为 REACHABLE ∪ {null}", () => {
    const image = new Set<string | null>();
    for (const input of ALL) image.add(activityListViewState(input));
    const expected = new Set<string | null>([...REACHABLE_VIEW_STATES, null]);
    expect([...image].sort()).toEqual([...expected].sort());
  });

  it("诚实边界：partial-comparable / pending-fill 在 UI-02 任何组合下都不可达（禁伪造触发条件）", () => {
    expect([...UNREACHABLE_VIEW_STATES].sort()).toEqual(["partial-comparable", "pending-fill"]);
    for (const input of ALL) {
      expect(UNREACHABLE_VIEW_STATES).not.toContain(activityListViewState(input) as never);
    }
  });

  it("REACHABLE 与 UNREACHABLE 互补且并集 = 冻结六态", () => {
    const union = [...REACHABLE_VIEW_STATES, ...UNREACHABLE_VIEW_STATES].sort();
    expect(union).toEqual([...VIEW_STATE_KINDS].sort());
  });
});

describe("逐态映射", () => {
  it("failed + 412 → stale-412（保留本地输入 + 新旧版本，COMMON.md:32）", () => {
    expect(activityListViewState({ phase: "failed", error: makeProblem(412, "REVISION_CONFLICT"), itemCount: 0 })).toBe(
      "stale-412",
    );
  });

  it("failed + CONFLICT 分桶（409）→ stale-412，由冻结件 stateFromError 判定", () => {
    expect(activityListViewState({ phase: "failed", error: makeProblem(409, "IDEMPOTENCY_CONFLICT"), itemCount: 3 })).toBe(
      "stale-412",
    );
  });

  it("failed + 非冲突 problem / 传输失败 → failed", () => {
    expect(activityListViewState({ phase: "failed", error: makeProblem(500, "INTERNAL_ERROR"), itemCount: 0 })).toBe("failed");
    expect(activityListViewState({ phase: "failed", error: makeTransport(0), itemCount: 0 })).toBe("failed");
  });

  it("failed 但 error 缺失（防御分支）→ failed，不抛异常", () => {
    expect(activityListViewState({ phase: "failed", error: null, itemCount: 0 })).toBe("failed");
  });

  it("empty → no-record（与 failed 不混用）", () => {
    for (const itemCount of COUNTS) {
      expect(activityListViewState({ phase: "empty", error: null, itemCount })).toBe("no-record");
    }
  });

  it("idle / loading 且无上次结果 → first-load 骨架", () => {
    expect(activityListViewState({ phase: "idle", error: null, itemCount: 0 })).toBe("first-load");
    expect(activityListViewState({ phase: "loading", error: null, itemCount: 0 })).toBe("first-load");
  });

  it("loading 且已有行 → null（主区继续渲染表格，配合「上一结果」标识）", () => {
    expect(activityListViewState({ phase: "loading", error: null, itemCount: 25 })).toBeNull();
    expect(showsPreviousResult({ phase: "loading", error: null, itemCount: 25 })).toBe(true);
  });

  it("ready 有行 → null；ready 却 0 行按无记录呈现（不冒充骨架）", () => {
    expect(activityListViewState({ phase: "ready", error: null, itemCount: 25 })).toBeNull();
    expect(activityListViewState({ phase: "ready", error: null, itemCount: 0 })).toBe("no-record");
  });

  it("负对照：showsPreviousResult 只在 loading 且有行时为真", () => {
    expect(showsPreviousResult({ phase: "idle", error: null, itemCount: 5 })).toBe(false);
    expect(showsPreviousResult({ phase: "ready", error: null, itemCount: 5 })).toBe(false);
    expect(showsPreviousResult({ phase: "loading", error: null, itemCount: 0 })).toBe(false);
  });

  it("负对照：error 存在但 phase 不是 failed 时不劫持呈现（错误归 AlertBanner，态归 phase）", () => {
    expect(activityListViewState({ phase: "ready", error: makeProblem(500, "INTERNAL_ERROR"), itemCount: 3 })).toBeNull();
  });
});
