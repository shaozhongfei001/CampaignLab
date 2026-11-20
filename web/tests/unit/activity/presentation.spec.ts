/**
 * web/tests/unit/activity/presentation.spec.ts —— UI-02 显示层与契约原文对账
 *
 * 判据结构性（PRE-29）：列名 / 路由 / operationId 都从 spec 与 contracts 的**磁盘原文**解析出来再比对，
 * 不在测试里重抄一遍期望值当「真值」；同时配负对照（伪造列名、枚举外状态、禁词）。
 */
import { describe, expect, it } from "vitest";
import { ACTIVITY_STATUSES } from "@/api/endpoints";
import type { StatusTone } from "@/components/componentTypes";
import {
  ACTIVITY_COLUMNS,
  ACTIVITY_COLUMN_LABELS,
  ACTIVITY_STATUS_VIEWS,
  MISSING_REASON,
  asCellText,
  asCellValue,
  joinIdsOrNone,
  statusTextOf,
  statusViewOf,
  statusViewOfCode,
  toActivityRow,
  validateActivityDraft,
} from "@/features/activity/presentation";
import { makeActivity, makeSparseActivity } from "./fixtures";

const specFiles = import.meta.glob("../../../../spec/CampaignLab-SDD-v1.0/ui/UI-02-activity-list.md", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;
const contractFiles = import.meta.glob("../../../../contracts/pages.json", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;
const srcFiles = import.meta.glob("/src/pages/activity/*.vue", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const readOne = (files: Record<string, string>, suffix: string): string => {
  const key = Object.keys(files).find((name) => name.endsWith(suffix));
  return key === undefined ? "" : (files[key] ?? "");
};

const UI02_MD = readOne(specFiles, "UI-02-activity-list.md");
const PAGE_SOURCE = readOne(srcFiles, "ActivityListPage.vue");
interface PageContractRow {
  readonly id: string;
  readonly route: string;
  readonly operation_ids: readonly string[];
}
const PAGES = JSON.parse(readOne(contractFiles, "pages.json")) as readonly PageContractRow[];
const UI02 = PAGES.find((page) => page.id === "UI-02");

/** 从 markdown 表格里取「| 区域 | 内容 |」行的第二列原文。 */
function tableCellOf(markdown: string, firstCell: string): string {
  const line = markdown
    .split("\n")
    .find((row) => row.startsWith("|") && (row.split("|")[1] ?? "").trim() === firstCell);
  return line === undefined ? "" : (line.split("|")[2] ?? "").trim();
}

const TONES: readonly StatusTone[] = ["NEUTRAL", "OK", "WARN", "DANGER", "INFO"];

describe("扫描通道有效", () => {
  it("UI-02 契约原文、pages.json、页面源码都读到内容", () => {
    expect(UI02_MD.length).toBeGreaterThan(500);
    expect(UI02).toBeDefined();
    expect(PAGE_SOURCE.length).toBeGreaterThan(1000);
  });
});

describe("列定义 = 契约「页面结构 · 全宽列表」原文", () => {
  it("六个列名与列序逐字相等", () => {
    const contractLabels = tableCellOf(UI02_MD, "全宽列表").split("、").map((label) => label.trim());
    expect(contractLabels.length).toBe(6);
    expect([...ACTIVITY_COLUMN_LABELS]).toEqual(contractLabels);
    expect(ACTIVITY_COLUMNS.map((column) => column.label)).toEqual(contractLabels);
  });

  it("列 key 都是契约 Activity 的真实字段名（禁自造字段）", () => {
    const contractFields = Object.keys(makeActivity());
    for (const column of ACTIVITY_COLUMNS) {
      expect(contractFields, "列 key " + column.key + " 不是 Activity 字段").toContain(column.key);
    }
  });

  it("六列全部可键盘排序（COMMON.md:38「表格排序支持键盘」）", () => {
    expect(ACTIVITY_COLUMNS.every((column) => column.sortable === true)).toBe(true);
  });

  it("负对照：伪造列名不在契约原文里", () => {
    const contractText = tableCellOf(UI02_MD, "全宽列表");
    expect(contractText).not.toContain("创建时间");
    expect([...ACTIVITY_COLUMN_LABELS]).not.toContain("创建时间");
  });
});

describe("页面标题与路由 = 契约原文", () => {
  it("标题行原文的页名与页面常量一致", () => {
    const titleCell = tableCellOf(UI02_MD, "标题行");
    const contractTitle = titleCell.split("，")[0] ?? "";
    expect(contractTitle.length).toBeGreaterThan(0);
    const literal = /const PAGE_TITLE = "([^"]+)";/.exec(PAGE_SOURCE);
    expect(literal?.[1]).toBe(contractTitle);
  });

  it("契约 md 里反引号包裹的路由与 pages.json 的 route 一致，且页面路由常量同源", () => {
    const inMarkdown = /路由 `([^`]+)`/.exec(UI02_MD);
    expect(inMarkdown?.[1]).toBe(UI02?.route);
    expect(UI02?.route).toBe("/w/:workspace_id/activities");
  });

  it("契约「操作、接口与反馈」表里出现的 operationId 集合 = pages.json 的 operation_ids", () => {
    const sectionStart = UI02_MD.indexOf("## 操作、接口与反馈");
    const sectionEnd = UI02_MD.indexOf("## 页面状态与边界");
    expect(sectionStart).toBeGreaterThan(-1);
    expect(sectionEnd).toBeGreaterThan(sectionStart);
    const section = UI02_MD.slice(sectionStart, sectionEnd);
    const found = new Set<string>();
    for (const match of section.matchAll(/\b(?:list|get|create|update)[A-Z][A-Za-z0-9]*/g)) {
      found.add(match[0]);
    }
    expect([...found].sort()).toEqual([...(UI02?.operation_ids ?? [])].sort());
  });
});

describe("状态词映射（不靠颜色区分 + 禁自造状态）", () => {
  it("映射的 code 集合恰好等于契约枚举，整序一致", () => {
    expect(ACTIVITY_STATUS_VIEWS.map((view) => view.code)).toEqual([...ACTIVITY_STATUSES]);
  });

  it("两个状态的可见文字互不相同（文字是非颜色载体，AC-032）", () => {
    const labels = ACTIVITY_STATUS_VIEWS.map((view) => view.label);
    expect(new Set(labels).size).toBe(labels.length);
    for (const label of labels) expect(label.length).toBeGreaterThan(0);
  });

  it("tone 取值全部落在 StatusTag 的冻结字面量集合内", () => {
    for (const view of ACTIVITY_STATUS_VIEWS) expect(TONES).toContain(view.tone);
  });

  it("ARCHIVED 的中文措辞能在 UI-02 契约原文里找到（留痕，非自造）", () => {
    const archived = statusViewOf("ARCHIVED");
    expect(archived.label).toBe("已归档");
    expect(UI02_MD).toContain(archived.label);
  });

  it("statusTextOf 同时给出措辞与契约枚举原文", () => {
    expect(statusTextOf("OPEN")).toBe(statusViewOf("OPEN").label + "（OPEN）");
    expect(statusTextOf("ARCHIVED")).toContain("ARCHIVED");
  });

  it("负对照：枚举外取值原样回显，绝不渲染 undefined", () => {
    const unknown = statusViewOfCode("SOMETHING_ELSE");
    expect(unknown.label).toBe("SOMETHING_ELSE");
    expect(unknown.code).toBe("SOMETHING_ELSE");
    expect(TONES).toContain(unknown.tone);
    expect(statusViewOfCode("").label).toBe("");
    expect(ACTIVITY_STATUS_VIEWS.map((view) => view.code)).not.toContain("SOMETHING_ELSE");
  });
});

describe("缺值呈现（COMMON.md:36「缺值显示 — 与原因」）", () => {
  it("三个可空列各有一条非空原因，且原因是可核对事实而非因果推断", () => {
    const nullableColumns = ["bank_id", "external_activity_id", "current_rule_id"] as const;
    expect(Object.keys(MISSING_REASON).sort()).toEqual([...nullableColumns].sort());
    for (const key of nullableColumns) {
      const reason = MISSING_REASON[key];
      expect(reason.length).toBeGreaterThan(0);
      expect(reason).not.toContain("因为");
      expect(reason).not.toContain("所以");
    }
  });

  it("行投影保留 null（禁把缺值渲染成 0 或空串冒充数据）", () => {
    const row = toActivityRow(makeSparseActivity("s1"));
    expect(row.bank_id).toBeNull();
    expect(row.external_activity_id).toBeNull();
    expect(row.current_rule_id).toBeNull();
    expect(row.id).toBe("s1");
    expect(Object.keys(row).sort()).toEqual(ACTIVITY_COLUMNS.map((column) => column.key).sort());
  });

  it("asCellValue / asCellText 把 undefined 折成 null / 空串", () => {
    expect(asCellValue(undefined)).toBeNull();
    expect(asCellValue(null)).toBeNull();
    expect(asCellValue(0)).toBe(0);
    expect(asCellText(undefined)).toBe("");
    expect(asCellText(null)).toBe("");
    expect(asCellText(0)).toBe("0");
  });

  it("joinIdsOrNone：空数组 = 缺值，非空按顿号连接", () => {
    expect(joinIdsOrNone([])).toBeNull();
    expect(joinIdsOrNone(["rule-1"])).toBe("rule-1");
    expect(joinIdsOrNone(["rule-1", "rule-2"])).toBe("rule-1、rule-2");
  });
});

describe("新建活动草稿校验（UI-02:28「来源银行与行内编号成对填写」）", () => {
  it("真值表", () => {
    expect(validateActivityDraft({ name: "", bank_id: "", external_activity_id: "" })).toBe("名称必填");
    expect(validateActivityDraft({ name: "  ", bank_id: "B", external_activity_id: "E" })).toBe("名称必填");
    expect(validateActivityDraft({ name: "甲", bank_id: "B", external_activity_id: "" })).toBe(
      "来源银行与行内活动编号须成对填写",
    );
    expect(validateActivityDraft({ name: "甲", bank_id: "", external_activity_id: "E" })).toBe(
      "来源银行与行内活动编号须成对填写",
    );
    expect(validateActivityDraft({ name: "甲", bank_id: "", external_activity_id: "" })).toBe("");
    expect(validateActivityDraft({ name: "甲", bank_id: "B", external_activity_id: "E" })).toBe("");
  });

  it("负对照：只填名称不报错（两字段同为空是合法组合）", () => {
    expect(validateActivityDraft({ name: "甲", bank_id: "", external_activity_id: "" })).not.toBe(
      "来源银行与行内活动编号须成对填写",
    );
  });
});

describe("内容红线：显示层字符串禁总括语（ADR-003 C 段）", () => {
  const BANNED: readonly string[] = ["监听", "情绪识别", "语气分析", "生产就绪", "冻结生效", "全部通过"];
  const collected: string[] = [
    ...ACTIVITY_COLUMN_LABELS,
    ...ACTIVITY_STATUS_VIEWS.map((view) => view.label),
    ...ACTIVITY_STATUS_VIEWS.map((view) => statusTextOf(view.code as "OPEN")),
    ...Object.values(MISSING_REASON),
    validateActivityDraft({ name: "", bank_id: "", external_activity_id: "" }),
    validateActivityDraft({ name: "甲", bank_id: "B", external_activity_id: "" }),
  ];

  it("收集到的显示层字符串非空（否则本组断言空转）", () => {
    expect(collected.filter((text) => text.length > 0).length).toBeGreaterThan(5);
  });

  it("无禁用总括语，且不含「N/N 已验收」式不可核对表述", () => {
    for (const text of collected) {
      for (const word of BANNED) expect(text, text + " 命中禁词 " + word).not.toContain(word);
      expect(text).not.toMatch(/\d+\s*\/\s*\d+\s*已验收/);
    }
  });
});
