/**
 * web/tests/unit/activity/sort.spec.ts —— UI-02 表头排序（纯显示层，契约无 sort 参数）
 * 判据取解析后的 id 序列，不比对渲染串；缺值排位单独断言（正/负双向）。
 */
import { describe, expect, it } from "vitest";
import { ACTIVITY_COLUMNS } from "@/features/activity/presentation";
import {
  ACTIVITY_SORT_KEYS,
  asActivitySortKey,
  nextActivitySort,
  sortActivities,
} from "@/features/activity/sort";
import { makeActivity, makeSparseActivity } from "./fixtures";

const ids = (rows: readonly { id: string }[]): string[] => rows.map((row) => row.id);

describe("排序键集合与契约列定义不漂移", () => {
  it("ACTIVITY_SORT_KEYS 整序等于 ACTIVITY_COLUMNS 的 key 整序", () => {
    expect(ACTIVITY_SORT_KEYS).toEqual(ACTIVITY_COLUMNS.map((column) => column.key));
  });

  it("asActivitySortKey 只收敛集合内取值，集合外返回 null（禁自造排序键）", () => {
    for (const key of ACTIVITY_SORT_KEYS) expect(asActivitySortKey(key)).toBe(key);
    expect(asActivitySortKey("revision")).toBeNull();
    expect(asActivitySortKey("")).toBeNull();
    expect(asActivitySortKey("__proto__")).toBeNull();
  });
});

describe("nextActivitySort", () => {
  it("换列回到 asc，同列在 asc/desc 间切换", () => {
    expect(nextActivitySort({ key: "id", dir: "asc" }, "name")).toEqual({ key: "name", dir: "asc" });
    expect(nextActivitySort({ key: "name", dir: "asc" }, "name")).toEqual({ key: "name", dir: "desc" });
    expect(nextActivitySort({ key: "name", dir: "desc" }, "name")).toEqual({ key: "name", dir: "asc" });
  });
});

describe("sortActivities", () => {
  // 名称用 ASCII 单字符：字符串比较按 UTF-16 码元，中文字的码元序与笔画/拼音序无关，
  // 用中文当排序夹具会把「实现按码元排序」这件事藏起来（判据必须可解释）。
  const rows = [
    makeActivity({ id: "a3", name: "C" }),
    makeActivity({ id: "a1", name: "A" }),
    makeActivity({ id: "a2", name: "B" }),
  ];

  it("按名称升序 / 降序", () => {
    expect(ids(sortActivities(rows, { key: "name", dir: "asc" }))).toEqual(["a1", "a2", "a3"]);
    expect(ids(sortActivities(rows, { key: "name", dir: "desc" }))).toEqual(["a3", "a2", "a1"]);
  });

  it("不改传入数组（纯函数，避免污染 store 的响应式 items）", () => {
    const sorted = sortActivities(rows, { key: "name", dir: "asc" });
    expect(ids(rows)).toEqual(["a3", "a1", "a2"]);
    expect(ids(sorted)).toEqual(["a1", "a2", "a3"]);
    expect(sorted).not.toBe(rows);
  });

  it("缺值行在升序与降序下都固定排在末尾（不得被读成最小值）", () => {
    const mixed = [makeSparseActivity("s1"), makeActivity({ id: "b1", bank_id: "BANK-B" }), makeSparseActivity("s2")];
    expect(ids(sortActivities(mixed, { key: "bank_id", dir: "asc" }))).toEqual(["b1", "s1", "s2"]);
    expect(ids(sortActivities(mixed, { key: "bank_id", dir: "desc" }))).toEqual(["b1", "s1", "s2"]);
  });

  it("同值以 id 稳定收口，排序结果可复现", () => {
    const same = [
      makeActivity({ id: "z1", name: "SAME" }),
      makeActivity({ id: "a9", name: "SAME" }),
      makeActivity({ id: "m3", name: "SAME" }),
    ];
    expect(ids(sortActivities(same, { key: "name", dir: "asc" }))).toEqual(["a9", "m3", "z1"]);
    expect(ids(sortActivities(same, { key: "name", dir: "desc" }))).toEqual(["a9", "m3", "z1"]);
  });

  it("负对照：状态列排序确实改变顺序（证明断言不是恒真）", () => {
    const mixedStatus = [
      makeActivity({ id: "o1", status: "OPEN" }),
      makeActivity({ id: "r1", status: "ARCHIVED" }),
    ];
    expect(ids(sortActivities(mixedStatus, { key: "status", dir: "asc" }))).toEqual(["r1", "o1"]);
    expect(ids(sortActivities(mixedStatus, { key: "status", dir: "asc" }))).not.toEqual(["o1", "r1"]);
  });
});
