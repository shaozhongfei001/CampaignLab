/**
 * web/tests/unit/activity/query.spec.ts —— UI-02 过滤项归一化（契约 listActivities q/status）
 * 判据取解析值而非渲染串；每条都配负对照（越界取值必须被拒，禁自造状态词）。
 */
import { describe, expect, it } from "vitest";
import {
  ACTIVITY_QUERY_MAX_LENGTH,
  ACTIVITY_STATUSES,
  ACTIVITY_STATUS_MAX_LENGTH,
} from "@/api/endpoints";
import {
  hasActivityFilter,
  normalizeActivityQuery,
  normalizeActivityStatus,
  sendsActivityQuery,
  sendsActivityStatus,
} from "@/features/activity/query";

describe("normalizeActivityQuery（契约 q：minLength 1 / maxLength 100）", () => {
  it("trim + 折叠连续空白", () => {
    expect(normalizeActivityQuery("  满额   赠券  ")).toBe("满额 赠券");
  });

  it("空与全空白归空串（= 不发送 q 参数）", () => {
    expect(normalizeActivityQuery("")).toBe("");
    expect(normalizeActivityQuery("   \t\n ")).toBe("");
    expect(sendsActivityQuery("   ")).toBe(false);
  });

  it("超长截断到契约 maxLength，且不截出半截空白", () => {
    const long = "a".repeat(ACTIVITY_QUERY_MAX_LENGTH + 50);
    expect(normalizeActivityQuery(long).length).toBe(ACTIVITY_QUERY_MAX_LENGTH);
    expect(sendsActivityQuery(long)).toBe(true);
  });

  it("负对照：归一化不会凭空产生内容", () => {
    expect(normalizeActivityQuery("   ")).not.toBe(" ");
    expect(normalizeActivityQuery("x")).not.toBe("X");
  });
});

describe("normalizeActivityStatus（只接受 Activity.status 枚举原文）", () => {
  it("契约枚举原样通过，允许首尾空白", () => {
    for (const code of ACTIVITY_STATUSES) {
      expect(normalizeActivityStatus(code)).toBe(code);
      expect(normalizeActivityStatus("  " + code + " ")).toBe(code);
      expect(sendsActivityStatus(code)).toBe(true);
    }
  });

  it("空串 = 全部状态（不发送 status 参数）", () => {
    expect(normalizeActivityStatus("")).toBe("");
    expect(sendsActivityStatus("")).toBe(false);
  });

  it("负对照：大小写不符 / 自造状态 / 已否决语义一律归空", () => {
    expect(normalizeActivityStatus("open")).toBe("");
    expect(normalizeActivityStatus("DRAFT")).toBe("");
    expect(normalizeActivityStatus("CLOSED")).toBe("");
    // 工作区侧已被 CR-002/ADR-006 否决的语义不得从活动侧偷偷回流：
    expect(ACTIVITY_STATUSES).not.toContain("READY");
    expect(ACTIVITY_STATUSES).not.toContain("DEGRADED");
  });

  it("契约自洽：枚举取值长度都不超过 status 参数的 maxLength", () => {
    for (const code of ACTIVITY_STATUSES) {
      expect(code.length).toBeLessThanOrEqual(ACTIVITY_STATUS_MAX_LENGTH);
    }
  });
});

describe("hasActivityFilter（无记录态文案必须指明当前筛选，COMMON.md:28）", () => {
  it("真值表", () => {
    expect(hasActivityFilter("", "")).toBe(false);
    expect(hasActivityFilter("满额", "")).toBe(true);
    expect(hasActivityFilter("", "OPEN")).toBe(true);
    expect(hasActivityFilter("满额", "ARCHIVED")).toBe(true);
  });

  it("负对照：非枚举状态不算筛选（与 store 的不发送行为一致）", () => {
    expect(hasActivityFilter("", "DRAFT")).toBe(false);
  });
});
