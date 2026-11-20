/**
 * web/tests/unit/activity/route-contract.spec.ts —— UI-02 的 route / operationId 与机器真值对账
 *
 * 判据一律结构性（PRE-29）：真值从 contracts/pages.json 与 contracts/operations.json 的**磁盘原文**读出，
 * 实现侧从 web/src/router/index.ts 与 web/src/api/endpoints.ts 的**磁盘原文**用正则抽出符号集合，
 * 两侧做集合相等 / 包含断言；不比对渲染串、不用裸子串、不写死位置下标。
 * 每条断言都配一个「伪造值必须被判出不存在」的负对照，证明检查本身不是空转。
 *
 * 编号纪律出处：AC 只能抄 qa/ACCEPTANCE.md；operationId 只能抄 pages.json.operation_ids 与 operations.json
 * （D-011 / D-036 均为 MAJOR 先例）。
 */
import { describe, expect, it } from "vitest";

interface PageContract {
  readonly id: string;
  readonly requirement: string;
  readonly title: string;
  readonly route: string;
  readonly path: string;
  readonly operation_ids: readonly string[];
  readonly acceptance: readonly string[];
}

const repoFiles = import.meta.glob("../../../../contracts/*.json", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const specFiles = import.meta.glob("../../../../spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const srcFiles = import.meta.glob("/src/**/*", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const readRepo = (suffix: string): string => {
  const key = Object.keys(repoFiles).find((name) => name.endsWith(suffix));
  return key === undefined ? "" : (repoFiles[key] ?? "");
};

const PAGES: readonly PageContract[] = JSON.parse(readRepo("/pages.json")) as PageContract[];
const OPERATIONS_RAW: unknown = JSON.parse(readRepo("/operations.json"));

/** operations.json 是对象数组，键名可能是 operationId / operation_id / id：三种都认，取到即止。 */
const OPERATION_IDS: readonly string[] = (OPERATIONS_RAW as ReadonlyArray<Record<string, unknown>>).map((entry) => {
  const value = entry.operationId ?? entry.operation_id ?? entry.id;
  return typeof value === "string" ? value : "";
});

const ROUTER_SOURCE = srcFiles["/src/router/index.ts"] ?? "";
const ENDPOINTS_SOURCE = srcFiles["/src/api/endpoints.ts"] ?? "";

const PATH_LITERAL = /path:\s*"([^"]+)"/g;
const EXPORTED_FUNCTION = /export\s+function\s+([A-Za-z0-9_]+)\s*\(/g;

function matches(source: string, pattern: RegExp): string[] {
  const out: string[] = [];
  for (const match of source.matchAll(new RegExp(pattern.source, "g"))) {
    const value = match[1];
    if (value !== undefined) out.push(value);
  }
  return out;
}

const ROUTER_PATHS: readonly string[] = matches(ROUTER_SOURCE, PATH_LITERAL);
const EXPORTED_ENDPOINTS: readonly string[] = matches(ENDPOINTS_SOURCE, EXPORTED_FUNCTION);
const CONTRACT_ROUTES: readonly string[] = PAGES.map((page) => page.route);

const UI02 = PAGES.find((page) => page.id === "UI-02");

describe("扫描通道有效（真值与实现原文都读到磁盘内容）", () => {
  it("contracts/pages.json 解析出 26 页且含 UI-02", () => {
    expect(PAGES.length).toBe(26);
    expect(UI02).toBeDefined();
    expect(OPERATION_IDS.length).toBeGreaterThan(0);
  });

  it("router 与 endpoints 原文非空且能抽出符号", () => {
    expect(ROUTER_SOURCE.length).toBeGreaterThan(0);
    expect(ENDPOINTS_SOURCE.length).toBeGreaterThan(0);
    expect(ROUTER_PATHS.length).toBeGreaterThan(0);
    expect(EXPORTED_ENDPOINTS.length).toBeGreaterThan(0);
  });
});

describe("UI-02 路由落地 = 契约 route 原文", () => {
  it("契约 route 逐字出现在 router 的 path 字面量集合里", () => {
    expect(UI02?.route).toBe("/w/:workspace_id/activities");
    expect(ROUTER_PATHS).toContain(UI02?.route);
  });

  it("router 里所有 /w/ 前缀路径都必须是契约 route（禁自造路由）", () => {
    const workspaceScoped = ROUTER_PATHS.filter((path) => path.startsWith("/w/"));
    expect(workspaceScoped.length).toBeGreaterThan(0);
    const invented = workspaceScoped.filter((path) => !CONTRACT_ROUTES.includes(path));
    expect(invented).toEqual([]);
  });

  it("非 /w/ 路径只允许入口、旧实现兼容重定向与 catch-all 三条", () => {
    const allowed: readonly string[] = ["/", "/workspaces/:workspaceId", "/:pathMatch(.*)*"];
    const others = ROUTER_PATHS.filter((path) => !path.startsWith("/w/"));
    expect([...others].sort()).toEqual([...allowed].sort());
  });

  it("负对照：伪造路由（单数 activity / 驼峰参数名）都不在 router 里", () => {
    expect(ROUTER_PATHS).not.toContain("/w/:workspace_id/activity");
    expect(ROUTER_PATHS).not.toContain("/w/:workspaceId/activities");
    expect(CONTRACT_ROUTES).not.toContain("/w/:workspace_id/activity");
  });
});

describe("UI-02 operationId 绑定 = 契约 operation_ids（D-036 先例）", () => {
  it("UI-02 的三个 operationId 都在 endpoints.ts 有同名导出函数", () => {
    expect(UI02?.operation_ids).toEqual(["listActivities", "getActivity", "createActivity"]);
    for (const operationId of UI02?.operation_ids ?? []) {
      expect(EXPORTED_ENDPOINTS, "缺类型化封装 " + operationId).toContain(operationId);
      expect(OPERATION_IDS, operationId + " 不在 contracts/operations.json").toContain(operationId);
    }
  });

  it("endpoints.ts 里与 operations.json 同名的导出，恰好等于 UI-01 与 UI-02 的 operation_ids 并集", () => {
    const ui01 = PAGES.find((page) => page.id === "UI-01");
    const expected = [...new Set([...(ui01?.operation_ids ?? []), ...(UI02?.operation_ids ?? [])])].sort();
    const bound = EXPORTED_ENDPOINTS.filter((name) => OPERATION_IDS.includes(name)).sort();
    expect(bound).toEqual(expected);
  });

  it("负对照：伪造 opId 既不在契约也不在实现", () => {
    expect(OPERATION_IDS).not.toContain("listActivitiesV2");
    expect(EXPORTED_ENDPOINTS).not.toContain("listActivitiesV2");
    expect(EXPORTED_ENDPOINTS).not.toContain("fetchActivities");
  });
});

describe("UI-02 acceptance 编号只来自 qa/ACCEPTANCE.md（禁自造 AC）", () => {
  it("pages.json 的 acceptance 是 AC-002 与 AC-032，且都在 ACCEPTANCE.md 原文里成行出现", () => {
    expect(UI02?.acceptance).toEqual(["AC-002", "AC-032"]);
    const acceptanceKey = Object.keys(specFiles).find((name) => name.endsWith("ACCEPTANCE.md"));
    const acceptance = acceptanceKey === undefined ? "" : (specFiles[acceptanceKey] ?? "");
    expect(acceptance.length, "ACCEPTANCE.md 原文必须读到（否则本条断言是空转）").toBeGreaterThan(1000);
    const rows = acceptance.split("\n").filter((line) => line.startsWith("| AC-"));
    const ids = rows.map((line) => (line.split("|")[1] ?? "").trim());
    expect(ids.length).toBe(35);
    for (const id of UI02?.acceptance ?? []) expect(ids).toContain(id);
  });
});
