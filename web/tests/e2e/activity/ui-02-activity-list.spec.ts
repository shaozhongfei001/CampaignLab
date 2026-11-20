/**
 * web/tests/e2e/activity/ui-02-activity-list.spec.ts —— UI-02 活动列表的出口取证与门禁
 *
 * 契约真值（禁凭记忆）：
 *   contracts/pages.json UI-02 = route `/w/:workspace_id/activities`、
 *   operation_ids [listActivities, getActivity, createActivity]、acceptance [AC-002, AC-032]；
 *   spec/CampaignLab-SDD-v1.0/ui/UI-02-activity-list.md「页面结构 / 字段和绑定 / 操作接口与反馈 / 页面状态与边界」；
 *   qa/ACCEPTANCE.md:40 AC-032 =「1440×900 与 1024×768 操作键盘、空页和错误分支 → 状态可读，焦点回收，
 *   表头和表格滚动正常。数字和缺项不靠颜色区分」（证据形态：截图 + 键盘轨迹）。
 *
 * 证据性质（如实声明，禁冒充）：
 *   后端未联调，全部响应来自 tests/e2e/activity/stubActivityApi.ts 的合成夹具 ⇒
 *   本文件是**前端层**呈现与交互基线，不构成 AC-001 的端到端联调证据（FU-31）。
 *   截图落在 evidence/FE/ui/ui-02/（纯 ASCII 文件名，两档视口各一份）。
 *
 * 判据纪律（PRE-29）：locator / 解析值 / computed style / 请求形状；禁渲染串前缀、禁裸子串、
 *   禁写死位置下标（列下标一律由表头文字反查），并在门禁自证用例里证明门禁本身会红。
 */
import { expect, test } from "@playwright/test";
import type { Page, TestInfo } from "@playwright/test";
import {
  PROBLEM_409,
  PROBLEM_412,
  PROBLEM_500,
  stubActivityApi,
  type ActivityStub,
  type ActivityStubOptions,
  type RecordedRequest,
} from "./stubActivityApi";
import {
  classGapDrift,
  clearGateSeeds,
  gateFailures,
  KNOWN_FROZEN_CLASS_GAPS,
  gateSummary,
  runMachineGates,
  scanChartContainers,
  scanClassDefinitions,
  scanForbiddenTokens,
  scanHorizontalOverflow,
  scanTagPairing,
  seedGateViolation,
  watchConsole,
  type ConsoleRecorder,
  type GateSeed,
} from "./gates";

/* ------------------------------------------------------------------ 常量（全部有出处） */

const EVIDENCE_DIR = new URL("../../../../evidence/FE/ui/ui-02/", import.meta.url).pathname;
const WORKSPACE_ID = "ws-1";
const ACTIVITY_PATH = "/w/" + WORKSPACE_ID + "/activities";
const ENTRY_TOKEN = "synthetic-entry-token-ui02";
const ROOT_ONLY = /^http:\/\/[^/]+\/$/;

/** UI-02「页面结构 · 全宽列表」列序原文；与 src 常量的绑定由 tests/unit/activity/presentation.spec.ts 承担。 */
const CONTRACT_COLUMNS: readonly string[] = ["编号", "活动", "来源银行", "行内编号", "当前仿真版本", "状态"];

/** 冻结语义常量（M0-03b-freeze.md）：证据抽屉 480px、确认框 520px。断言＝留痕，不是改它。 */
const DRAWER_WIDTH_PX = 480;
const DIALOG_WIDTH_PX = 520;

const EM_DASH = "\u2014";

/* ------------------------------------------------------------------ 通用步骤 */

function viewportSuffix(projectName: string): string {
  if (projectName === "desktop-1440x900") return "1440x900";
  if (projectName === "laptop-1024x768") return "1024x768";
  return "unknown-viewport";
}

async function shot(page: Page, info: TestInfo, kind: string): Promise<void> {
  const name = "ui-02-" + kind + "-" + viewportSuffix(info.project.name) + ".png";
  await page.screenshot({ path: EVIDENCE_DIR + name, fullPage: true });
}

async function openEntry(page: Page, rec: ConsoleRecorder, options: ActivityStubOptions = {}): Promise<ActivityStub> {
  // 采集器必须在任何导航之前挂上，否则门禁 1 会漏掉加载期的 console.error。
  expect(rec.errors).toEqual([]);
  const stub = await stubActivityApi(page, options);
  await page.goto("/");
  await expect(page.getByLabel("入口令牌（仅首次使用）")).toBeVisible();
  return stub;
}

async function signIn(page: Page): Promise<void> {
  await page.getByLabel("入口令牌（仅首次使用）").fill(ENTRY_TOKEN);
  await page.getByRole("button", { name: "进入本机工作台" }).click();
  await expect(page.getByText("会话 active").first()).toBeVisible();
}

async function enterWorkspace(page: Page): Promise<void> {
  await page.getByRole("button", { name: "进入", exact: true }).first().click();
  await expect(page).toHaveURL(new RegExp("^https?://[^/]+" + ACTIVITY_PATH));
}

/** 完整入口链路：UI-01 → 换取会话 → 进入工作区 → 落到契约路由（UI-02）。 */
async function enterActivityList(
  page: Page,
  rec: ConsoleRecorder,
  options: ActivityStubOptions = {},
): Promise<ActivityStub> {
  const stub = await openEntry(page, rec, options);
  await signIn(page);
  await enterWorkspace(page);
  return stub;
}

async function expectRows(page: Page, count: number): Promise<void> {
  await expect(page.locator("table.cl-table caption")).toHaveText("活动");
  await expect(page.locator("table.cl-table tbody tr")).toHaveCount(count);
}

/** 列下标由表头文字反查（禁写死位置下标）；返回该列每一行的文本。 */
async function columnValues(page: Page, headerLabel: string): Promise<string[]> {
  return page.evaluate((label: string) => {
    const table = document.querySelector("table.cl-table");
    if (table === null) return [];
    const heads = Array.from(table.querySelectorAll("thead th"));
    const index = heads.findIndex((head) => (head.textContent ?? "").trim() === label);
    if (index < 0) return [];
    return Array.from(table.querySelectorAll("tbody tr")).map((row) => {
      const cell = row.children[index];
      return cell === undefined ? "" : (cell.textContent ?? "").trim();
    });
  }, headerLabel);
}

function isOrdered(values: readonly string[], dir: "asc" | "desc"): boolean {
  for (let i = 1; i < values.length; i += 1) {
    const prev = values[i - 1] ?? "";
    const cur = values[i] ?? "";
    if (dir === "asc" && cur < prev) return false;
    if (dir === "desc" && prev < cur) return false;
  }
  return true;
}

async function headerLabels(page: Page): Promise<string[]> {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll("table.cl-table thead th")).map((th) => (th.textContent ?? "").trim()),
  );
}

/** 机器门禁 6 条（浏览器侧）一次跑完并判红；第 7 条属源码文本门禁，在 vitest 侧另行断言。 */
/**
 * 机器门禁判红入口。expectedHttpStatuses ＝本用例**故意**触发的错误响应状态码；
 * 浏览器会为每个 >=400 的响应自动打一条 console 错误（网络层噪声），
 * 门禁 1 把它与应用侧 console.error 分开统计并与本清单双向对账（多一个少一个都判红）。
 */
async function expectGatesClean(
  page: Page,
  rec: ConsoleRecorder,
  label: string,
  expectedHttpStatuses: readonly number[] = [],
): Promise<void> {
  const report = await runMachineGates(page, rec, label, expectedHttpStatuses);
  console.log("[gates] " + gateSummary(report));
  expect(gateFailures(report), "机器门禁未过（" + label + "）").toEqual([]);
}

function bodyOf(request: RecordedRequest | undefined): Record<string, unknown> {
  const text = request?.bodyText ?? "";
  return text.length === 0 ? {} : (JSON.parse(text) as Record<string, unknown>);
}

function lastParams(stub: ActivityStub): URLSearchParams {
  return stub.paramsOf(stub.listRequests().at(-1) as RecordedRequest);
}
/* ------------------------------------------------------------------ 用例 */

test.describe("UI-02 活动列表 · 状态与取证", () => {
  test("首载骨架：延迟响应下主区出骨架、导航保留、骨架不出字", async ({ page }, info) => {
    const rec = watchConsole(page);
    await openEntry(page, rec, { listDelayMs: 2500 });
    await signIn(page);
    await enterWorkspace(page);

    const skeleton = page.locator('[data-part="first-load-skeleton"]');
    await expect(skeleton).toBeVisible();
    // 骨架形状 = 本页六列 + 两张卡片（与真表列数恒等，FU-28：页面直接消费 FirstLoadSkeleton）。
    await expect(skeleton.locator('[data-part="head-cell"]')).toHaveCount(CONTRACT_COLUMNS.length);
    await expect(skeleton.locator('[data-part="card"]')).toHaveCount(2);
    // 骨架不出字（M0-03b §1.3）：整块 innerText 必须是空串，而不是「加载中」之类文案。
    expect((await skeleton.innerText()).trim().length).toBe(0);
    // 保留导航（COMMON.md:27）：骨架期间一级导航仍在。
    await expect(page.locator('nav[aria-label="一级导航"]')).toBeVisible();
    // 六态载体齐全（AC-032）：首载态经 variant 仍由 ViewState 发 data-state / role / aria-live / aria-busy。
    const firstLoad = page.locator('[data-state="first-load"]');
    await expect(firstLoad).toHaveAttribute("role", "status");
    await expect(firstLoad).toHaveAttribute("aria-live", "polite");
    await expect(firstLoad).toHaveAttribute("aria-busy", "true");
    // 骨架嵌在调度件里（variant 覆写呈现），而不是绕过 ViewState 另起一块。
    await expect(firstLoad.locator('[data-part="first-load-skeleton"]')).toBeVisible();
    // 骨架期间不渲染真表（禁拿空表冒充数据），且 store 私有 phase 在页头芯片上可见为 loading。
    await expect(page.locator("table.cl-table")).toHaveCount(0);
    await expect(page.getByText("列表 loading").first()).toBeVisible();
    await shot(page, info, "first-load");
    await expectGatesClean(page, rec, "first-load");

    await expectRows(page, 4);
    await expect(page.locator('[data-part="first-load-skeleton"]')).toHaveCount(0);
  });

  test("正常态：契约六列列序、合成标注、缺值 — 与原因、状态不靠颜色区分", async ({ page }, info) => {
    const rec = watchConsole(page);
    const stub = await enterActivityList(page, rec);
    await expectRows(page, 4);

    // 列序 = 契约原文（整序相等，禁子串）。
    expect(await headerLabels(page)).toEqual([...CONTRACT_COLUMNS]);

    // 合成数据可见标注（内容红线）：芯片的机器载体是 data-source-class，文字载体是「合成数据」。
    const chip = page.locator('[data-part="source-class"]');
    await expect(chip).toHaveAttribute("data-source-class", "SYNTHETIC");
    await expect(chip).toContainText("合成数据");

    // 缺值行（act-003 三字段全缺）：三个 — + 三条原因，禁 0/空串顶替（COMMON.md:36）。
    const missingRow = page.locator("tbody tr", { has: page.getByRole("button", { name: "查看活动 act-003" }) });
    await expect(missingRow.locator('[data-missing="true"]')).toHaveCount(3);
    expect(await missingRow.locator(".cl-missing__value").allInnerTexts()).toEqual([EM_DASH, EM_DASH, EM_DASH]);
    expect(await missingRow.locator('[data-part="reason"]').allInnerTexts()).toEqual([
      "服务端未返回来源银行",
      "服务端未返回行内活动编号",
      "服务端未返回当前仿真版本",
    ]);

    // 有值行（act-001）：同样三列一律 data-missing="false" 且**不出原因**（正对照）。
    const fullRow = page.locator("tbody tr", { has: page.getByRole("button", { name: "查看活动 act-001" }) });
    await expect(fullRow.locator('[data-missing="false"]')).toHaveCount(3);
    await expect(fullRow.locator('[data-part="reason"]')).toHaveCount(0);

    // 状态：契约枚举原文作机器载体，中文状态词作文本载体；两者一一对应 ⇒ 不依赖颜色即可区分（AC-032）。
    const statuses = await page.evaluate(() =>
      Array.from(document.querySelectorAll("table.cl-table tbody tr")).map((row) => {
        const marker = row.querySelector("[data-status]");
        const tag = marker === null ? null : marker.querySelector(".cl-tag");
        const style = tag === null ? null : getComputedStyle(tag);
        return {
          code: marker === null ? "" : marker.getAttribute("data-status") ?? "",
          label: tag === null ? "" : (tag.textContent ?? "").trim(),
          shape: style === null ? "" : style.borderRadius + "|" + style.height + "|" + style.borderWidth,
        };
      }),
    );
    expect(statuses.map((item) => item.code)).toEqual(["OPEN", "OPEN", "ARCHIVED", "ARCHIVED"]);
    expect(statuses.map((item) => item.label)).toEqual(["开放", "开放", "已归档", "已归档"]);
    // D-034③ 留痕：StatusTag 五 tone 形状相同（属冻结面，未改），故区分只能落在 code + 文本上。
    expect(new Set(statuses.map((item) => item.shape)).size).toBe(1);
    // 已归档活动可检索和查看（UI-02:32）：归档行在同一张表里直接可见，不需要额外开关。
    await expect(page.getByRole("button", { name: "查看活动 act-004" })).toBeVisible();

    // 请求形状：路径 = 契约 path；limit 默认 25；未筛选时 q/status/cursor 一律不出现在查询串里。
    const first = stub.listRequests().at(-1) as RecordedRequest;
    expect(first.pathname).toBe("/workspaces/" + WORKSPACE_ID + "/activities");
    expect(lastParams(stub).get("limit")).toBe("25");
    expect(lastParams(stub).has("q")).toBe(false);
    expect(lastParams(stub).has("status")).toBe(false);
    expect(lastParams(stub).has("cursor")).toBe(false);

    await shot(page, info, "activity-list");
    await expectGatesClean(page, rec, "ready");
  });

  test("筛选：q 与 status 落成契约查询参数，空值不发送，清空筛选回到全量", async ({ page }) => {
    const rec = watchConsole(page);
    const stub = await enterActivityList(page, rec);
    await expectRows(page, 4);

    // 按行内编号检索（UI-02 快速定位）：q 落进查询串，命中一行。
    const search = page.getByLabel("按名称或编号搜索活动");
    await search.fill("EXT-A-101");
    await search.press("Enter");
    await expectRows(page, 1);
    await expect(page.getByRole("button", { name: "查看活动 act-001" })).toBeVisible();
    expect(lastParams(stub).get("q")).toBe("EXT-A-101");
    expect(lastParams(stub).has("status")).toBe(false);
    // URL 同步（深链接可分享）：query 只带非空项。
    await expect(page).toHaveURL(/q=EXT-A-101/);

    // 叠加状态筛选：已归档 + 该行内编号 ⇒ 无记录态，标题必须指明当前筛选（COMMON.md:28）。
    await page.getByLabel("按状态筛选活动").selectOption("ARCHIVED");
    const empty = page.locator('[data-state="no-record"]');
    await expect(empty).toBeVisible();
    await expect(empty).toHaveAttribute("role", "status");
    expect(await empty.locator('[data-part="custom-title"]').innerText()).toBe(
      "当前筛选没有活动：名称或编号「EXT-A-101」；状态「已归档（ARCHIVED）」",
    );
    await expect(empty.locator('[data-action="create"]')).toBeVisible();
    await expect(empty.locator('[data-action="clear-filter"]')).toBeVisible();
    expect(lastParams(stub).get("status")).toBe("ARCHIVED");
    expect(lastParams(stub).get("q")).toBe("EXT-A-101");

    // 清空筛选：两个参数都不再发送（负对照，证明「空值不发送」不是恒真）。
    await empty.locator('[data-action="clear-filter"]').click();
    await expectRows(page, 4);
    expect(lastParams(stub).has("q")).toBe(false);
    expect(lastParams(stub).has("status")).toBe(false);
    await expect(search).toHaveValue("");
    await expect(page.getByLabel("按状态筛选活动")).toHaveValue("");
    await expectGatesClean(page, rec, "filtered-and-cleared");
  });

  test("空列表：无记录态只给创建入口，不给清空筛选（负对照）", async ({ page }, info) => {
    const rec = watchConsole(page);
    await enterActivityList(page, rec, { activities: [] });

    const empty = page.locator('[data-state="no-record"]');
    await expect(empty).toBeVisible();
    await expect(empty).toHaveAttribute("role", "status");
    await expect(empty).toHaveAttribute("aria-live", "polite");
    await expect(empty.locator('[data-action="create"]')).toBeVisible();
    // 无筛选时不该出现「清空筛选」：动作集由 filtered 决定（结构性负对照）。
    await expect(empty.locator('[data-action="clear-filter"]')).toHaveCount(0);
    // 无记录态不渲染真表（禁拿空表冒充数据）。
    await expect(page.locator("table.cl-table")).toHaveCount(0);
    await shot(page, info, "no-record");
    await expectGatesClean(page, rec, "no-record");

    // 空列表提供创建（UI-02:32）：动作键直达新建表单。
    await empty.locator('[data-action="create"]').click();
    await expect(page.locator("#cl-activity-name")).toBeVisible();
    await expect(page.locator("#cl-activity-name")).toHaveAttribute("aria-required", "true");
  });

  test("失败态：500 出 role=alert、code/HTTP/request_id 可见，重新获取可恢复", async ({ page }, info) => {
    const rec = watchConsole(page);
    const stub = await enterActivityList(page, rec, { listProblem: PROBLEM_500 });

    const failed = page.locator('[data-state="failed"]');
    await expect(failed).toBeVisible();
    await expect(failed).toHaveAttribute("role", "alert");
    // 失败摘要必须可核对：problem code、HTTP 状态、request_id 三者都在页面上。
    await expect(failed.locator(".cl-alert__title")).toHaveText("服务内部错误（合成）");
    await expect(failed.locator(".cl-alert__meta")).toHaveText("code INTERNAL_ERROR · HTTP 500");
    await expect(failed.locator(".cl-alert__rid")).toHaveText("request_id req-synthetic-500");
    await expect(failed.locator('[data-action="refetch"]')).toBeVisible();
    // 失败态不伪造数据行。
    await expect(page.locator("table.cl-table tbody tr")).toHaveCount(0);
    await shot(page, info, "failed-500");
    await expectGatesClean(page, rec, "failed", [500]);

    const before = stub.listRequests().length;
    stub.setListProblem(null);
    await failed.locator('[data-action="refetch"]').click();
    await expectRows(page, 4);
    expect(stub.listRequests().length).toBeGreaterThan(before);
    await expect(page.locator('[data-state="failed"]')).toHaveCount(0);
  });

  test("版本失效态：412 保留本地输入并给重新获取入口", async ({ page }, info) => {
    const rec = watchConsole(page);
    const stub = await enterActivityList(page, rec);
    await expectRows(page, 4);

    stub.setListProblem(PROBLEM_412);
    const search = page.getByLabel("按名称或编号搜索活动");
    await search.fill("EXT-B-202");
    await search.press("Enter");

    const stale = page.locator('[data-state="stale-412"]');
    await expect(stale).toBeVisible();
    await expect(stale).toHaveAttribute("data-keep-input", "true");
    await expect(stale).toHaveAttribute("role", "alert");
    await expect(stale.locator(".cl-alert__meta")).toHaveText("code REVISION_CONFLICT · HTTP 412");
    await expect(stale.locator('[data-action="refetch"]')).toBeVisible();
    // 「保留本地输入」（COMMON.md:31）：筛选框里的词没被失败冲掉。
    await expect(search).toHaveValue("EXT-B-202");
    await shot(page, info, "stale-412");
    await expectGatesClean(page, rec, "stale-412", [412]);

    stub.setListProblem(null);
    await stale.locator('[data-action="refetch"]').click();
    await expectRows(page, 1);
    await expect(page.getByRole("button", { name: "查看活动 act-002" })).toBeVisible();
  });

  test("上一结果保留：刷新期间旧行可见并打「上一结果」标识", async ({ page }, info) => {
    const rec = watchConsole(page);
    const stub = await enterActivityList(page, rec);
    await expectRows(page, 4);

    stub.setListDelay(1500);
    await page.getByRole("button", { name: "刷新" }).click();
    const previous = page.locator('[data-part="previous"]');
    await expect(previous).toBeVisible();
    await expect(previous).toHaveText("上一结果");
    // 加载中不清空旧结果（COMMON.md:29）：四行仍在，且不出首载骨架。
    await expect(page.locator("table.cl-table tbody tr")).toHaveCount(4);
    await expect(page.locator('[data-part="first-load-skeleton"]')).toHaveCount(0);
    await shot(page, info, "previous-result");
    await expectGatesClean(page, rec, "previous-result");

    await expect(previous).toHaveCount(0, { timeout: 15000 });
    await expectRows(page, 4);
  });

  test("游标翻页：加载更多是追加而非替换，游标耗尽后入口消失", async ({ page }) => {
    const rec = watchConsole(page);
    const stub = await enterActivityList(page, rec, { nextCursor: "cursor-page-2" });
    await expectRows(page, 4);
    await expect(page.getByText("还有更多（服务器游标）")).toBeVisible();

    const more = page.getByRole("button", { name: "加载更多" });
    await expect(more).toBeVisible();
    await more.click();
    await expectRows(page, 5);
    // 追加语义的行级证据：第二页新行出现，第一页旧行仍在。
    await expect(page.getByRole("button", { name: "查看活动 act-005" })).toBeVisible();
    await expect(page.getByRole("button", { name: "查看活动 act-001" })).toBeVisible();
    expect(lastParams(stub).get("cursor")).toBe("cursor-page-2");
    expect(lastParams(stub).get("limit")).toBe("25");
    await expect(more).toHaveCount(0);
    await expect(page.getByText("还有更多（服务器游标）")).toHaveCount(0);
    await expectGatesClean(page, rec, "cursor-paging");
  });
});
test.describe("UI-02 活动列表 · 键盘与焦点（AC-032）", () => {
  test("Tab 顺序＝DOM 顺序，焦点线 2px，表头 Enter/Space 改 aria-sort 并真的重排行", async ({ page }, info) => {
    const rec = watchConsole(page);
    await enterActivityList(page, rec);
    await expectRows(page, 4);

    // 键盘轨迹：逐次 Tab 记录落点（结构值 = aria-label 或元素文本），再按序比较，不写死下标。
    const stops: string[] = [];
    for (let i = 0; i < 26; i += 1) {
      await page.keyboard.press("Tab");
      stops.push(
        await page.evaluate(() => {
          const el = document.activeElement;
          if (el === null) return "";
          const label = el.getAttribute("aria-label");
          const text = (el.textContent ?? "").trim();
          return (label ?? text).slice(0, 40);
        }),
      );
    }
    const indexOf = (predicate: (value: string) => boolean): number => stops.findIndex(predicate);
    const evidenceAt = indexOf((value) => value === "证据");
    const createAt = indexOf((value) => value === "新建活动");
    const searchAt = indexOf((value) => value.includes("按名称或编号搜索活动"));
    const sortAt = indexOf((value) => value === "编号");
    expect(evidenceAt).toBeGreaterThanOrEqual(0);
    expect(createAt).toBeGreaterThan(evidenceAt);
    expect(searchAt).toBeGreaterThan(createAt);
    expect(sortAt).toBeGreaterThan(searchAt);

    // 焦点可见 2px（AppShell 全站焦点线）：键盘走到搜索框后取 computed outlineWidth。
    const search = page.getByLabel("按名称或编号搜索活动");
    for (let i = 0; i < 26; i += 1) {
      await page.keyboard.press("Shift+Tab");
      const label = await page.evaluate(() => document.activeElement?.getAttribute("aria-label") ?? "");
      if (label.includes("按名称或编号搜索活动")) break;
    }
    await expect(search).toBeFocused();
    expect(await page.evaluate(() => getComputedStyle(document.activeElement ?? document.body).outlineWidth)).toBe(
      "2px",
    );
    await shot(page, info, "keyboard-focus");

    // 初始排序 = 编号升序（页面默认），其余列为 none。
    const idHeader = page.getByRole("columnheader", { name: "编号", exact: true });
    const nameHeader = page.getByRole("columnheader", { name: "活动", exact: true });
    await expect(idHeader).toHaveAttribute("aria-sort", "ascending");
    await expect(nameHeader).toHaveAttribute("aria-sort", "none");

    await nameHeader.getByRole("button", { name: "活动" }).focus();
    await page.keyboard.press("Enter");
    await expect(nameHeader).toHaveAttribute("aria-sort", "ascending");
    await expect(idHeader).toHaveAttribute("aria-sort", "none");
    const asc = await columnValues(page, "活动");
    expect(asc.length).toBe(4);
    expect(isOrdered(asc, "asc")).toBe(true);
    // 负对照：同一序列在降序判据下必须为假，证明 isOrdered 不是恒真。
    expect(isOrdered(asc, "desc")).toBe(false);

    await page.keyboard.press("Space");
    await expect(nameHeader).toHaveAttribute("aria-sort", "descending");
    const desc = await columnValues(page, "活动");
    expect(isOrdered(desc, "desc")).toBe(true);
    expect(desc).toEqual(asc.slice().reverse());
    await expectGatesClean(page, rec, "keyboard-sort");
  });

  test("行进入详情：抽屉 480px、原值来自 getActivity、Esc 关闭并把焦点交还触发按钮", async ({ page }, info) => {
    const rec = watchConsole(page);
    const stub = await enterActivityList(page, rec);
    await expectRows(page, 4);

    const trigger = page.getByRole("button", { name: "查看活动 act-001" });
    await trigger.focus();
    await page.keyboard.press("Enter");

    const drawer = page.getByRole("dialog", { name: "活动详情" });
    await expect(drawer).toBeVisible();
    const box = await drawer.boundingBox();
    expect(box).not.toBeNull();
    expect(Math.round(box?.width ?? 0)).toBe(DRAWER_WIDTH_PX);

    // 抽屉里的每个字段都是 getActivity 原值（含 null → —），不是列表行的复制。
    await expect(drawer.locator('[data-field="id"]')).toHaveText("act-001");
    await expect(drawer.locator('[data-field="revision"]')).toHaveText("3");
    await expect(drawer.locator('[data-field="created_at"]')).toHaveText("2026-11-01T09:00:00+08:00");
    await expect(drawer.locator('[data-field="bank_id"]')).toContainText("BANK-A");
    await expect(drawer.locator('[data-field="bindings"] li')).toHaveCount(1);
    await expect(drawer.locator('[data-field="rule_ids"]')).toContainText("rule-a-001、rule-a-002、rule-a-003");
    await expect(drawer.locator('[data-field="status"] [data-status]')).toHaveAttribute("data-status", "OPEN");
    expect((stub.detailRequests().at(-1) as RecordedRequest).pathname).toBe(
      "/workspaces/" + WORKSPACE_ID + "/activities/act-001",
    );

    await shot(page, info, "detail-drawer");
    await expectGatesClean(page, rec, "detail-drawer");

    // Esc 关闭 + 焦点回收（COMMON.md 键盘与焦点；EvidenceDrawer 冻结行为）。
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "活动详情" })).toHaveCount(0);
    await expect(trigger).toBeFocused();
  });

  test("缺值行详情：null 字段一律 — 与原因，空数组不冒充 0", async ({ page }, info) => {
    const rec = watchConsole(page);
    await enterActivityList(page, rec);
    await expectRows(page, 4);

    await page.getByRole("button", { name: "查看活动 act-003" }).click();
    const drawer = page.getByRole("dialog", { name: "活动详情" });
    await expect(drawer).toBeVisible();
    await expect(drawer.locator('[data-field="bank_id"] [data-missing="true"]')).toBeVisible();
    await expect(drawer.locator('[data-field="external_activity_id"] .cl-missing__value')).toHaveText(EM_DASH);
    await expect(drawer.locator('[data-field="current_rule_id"] [data-part="reason"]')).toHaveText(
      "服务端未返回当前仿真版本",
    );
    // 空数组（bindings / rule_ids / receipt_ids）走 MissingValue，不渲染 0 或空串。
    await expect(drawer.locator('[data-field="bindings"] [data-missing="true"]')).toBeVisible();
    await expect(drawer.locator('[data-field="rule_ids"] .cl-missing__value')).toHaveText(EM_DASH);
    await expect(drawer.locator('[data-field="receipt_ids"] [data-part="reason"]')).toHaveText("服务端未返回回执");
    await expect(drawer.locator('[data-field="description"] [data-part="reason"]')).toHaveText("服务端返回空说明");
    await shot(page, info, "detail-missing");
    await expectGatesClean(page, rec, "detail-missing");
  });
});

test.describe("UI-02 活动列表 · 新建与冲突（AC-002）", () => {
  test("成对校验：只填银行编号不发请求；仅填名称时空字段不出现在正文", async ({ page }, info) => {
    const rec = watchConsole(page);
    const stub = await enterActivityList(page, rec);
    await expectRows(page, 4);

    await page.getByRole("button", { name: "新建活动", exact: true }).click();
    await page.locator("#cl-activity-name").fill("成对校验对照活动");
    await page.locator("#cl-activity-bank").fill("BANK-A");
    await page.getByRole("button", { name: "提交新建" }).click();

    // 负对照：成对校验失败 ⇒ 不打开确认框、不发 POST（结构性证据＝请求记录数为 0）。
    await expect(page.locator('[data-part="field-error"]')).toHaveText("来源银行与行内活动编号须成对填写");
    await expect(page.getByRole("dialog", { name: "新建活动" })).toHaveCount(0);
    expect(stub.listRequests("POST")).toHaveLength(0);
    await shot(page, info, "create-validation");

    await page.locator("#cl-activity-bank").fill("");
    await page.getByRole("button", { name: "提交新建" }).click();
    const dialog = page.getByRole("dialog", { name: "新建活动" });
    await expect(dialog).toBeVisible();
    expect(Math.round((await dialog.boundingBox())?.width ?? 0)).toBe(DIALOG_WIDTH_PX);
    // 确认框的影响说明按「；」拆成键值对后逐项核对（解析值，非裸子串）。
    const pairs = new Map(
      (await dialog.locator(".cl-confirm__impact").innerText())
        .split("；")
        .map((part) => [part.slice(0, part.indexOf(" ")), part.slice(part.indexOf(" ") + 1)] as const),
    );
    expect(pairs.get("名称")).toBe("成对校验对照活动");
    expect(pairs.get("来源银行")).toBe("未填写");
    expect(pairs.get("行内活动编号")).toBe("未填写");
    expect(pairs.get("工作区")).toBe(WORKSPACE_ID);

    await dialog.getByRole("button", { name: "确认新建" }).click();
    const detail = page.getByRole("dialog", { name: "活动详情" });
    await expect(detail).toBeVisible();
    await expect(detail.locator('[data-field="id"]')).toHaveText("act-900");

    const posts = stub.listRequests("POST");
    expect(posts).toHaveLength(1);
    // 空字段不出现在正文（exactOptionalPropertyTypes 的线上证据）：键集合恰为 {name}。
    expect(Object.keys(bodyOf(posts[0]))).toEqual(["name"]);
    expect(bodyOf(posts[0])["name"]).toBe("成对校验对照活动");
    const key = posts[0]?.idempotencyKey ?? "";
    expect(key.length).toBeGreaterThanOrEqual(8);
    expect(key.length).toBeLessThanOrEqual(128);
    expect(posts[0]?.contentType ?? "").toContain("application/json");
    // 创建成功进入详情（UI-02）＋ 新行插到列表首（服务端原值回填）。
    await expectRows(page, 5);
    await expect(page.getByRole("button", { name: "查看活动 act-900" })).toBeVisible();
    await shot(page, info, "created");
    await expectGatesClean(page, rec, "created");
  });

  test("409 冲突：显示冲突、按行内编号定位既有记录、沿原幂等键重试", async ({ page }, info) => {
    const rec = watchConsole(page);
    const stub = await enterActivityList(page, rec);
    await expectRows(page, 4);

    await page.getByRole("button", { name: "新建活动", exact: true }).click();
    await page.locator("#cl-activity-name").fill("重复行内编号的活动");
    await page.locator("#cl-activity-bank").fill("BANK-A");
    await page.locator("#cl-activity-external").fill("EXT-A-101");
    await page.getByRole("button", { name: "提交新建" }).click();
    const dialog = page.getByRole("dialog", { name: "新建活动" });
    await expect(dialog).toBeVisible();
    await shot(page, info, "create-confirm");

    stub.setCreateProblem(PROBLEM_409);
    await dialog.getByRole("button", { name: "确认新建" }).click();

    // 冲突可见：problem code / HTTP / request_id 三件套。
    const panel = page.locator("section.cl-card", { has: page.locator("#cl-activity-name") });
    await expect(panel.locator(".cl-alert__meta")).toHaveText("code IDEMPOTENCY_CONFLICT · HTTP 409");
    await expect(panel.locator(".cl-alert__rid")).toHaveText("request_id req-synthetic-409");
    // 保留本地输入（COMMON.md:31）：三个字段一个都没被清掉。
    await expect(page.locator("#cl-activity-name")).toHaveValue("重复行内编号的活动");
    await expect(page.locator("#cl-activity-bank")).toHaveValue("BANK-A");
    await expect(page.locator("#cl-activity-external")).toHaveValue("EXT-A-101");
    // 定位既有记录（UI-02:32）：页面说明 + 以该行内编号重查列表，把既有记录带回。
    await expect(panel.locator('[data-part="locate"]')).toContainText("EXT-A-101");
    await expectRows(page, 1);
    await expect(page.getByRole("button", { name: "查看活动 act-001" })).toBeVisible();
    expect(lastParams(stub).get("q")).toBe("EXT-A-101");
    expect(lastParams(stub).has("status")).toBe(false);
    await shot(page, info, "conflict-409");
    await expectGatesClean(page, rec, "conflict-409", [409]);

    // 沿原幂等键重试：第二次 POST 的 Idempotency-Key 必须与第一次逐字相同（不得重新生成）。
    const firstKey = stub.listRequests("POST")[0]?.idempotencyKey ?? "";
    expect(firstKey.length).toBeGreaterThan(0);
    const retry = panel.locator('[data-part="retry-same-key"]');
    await expect(retry).toBeVisible();
    stub.setCreateProblem(null);
    await retry.click();
    const posts = stub.listRequests("POST");
    expect(posts).toHaveLength(2);
    expect(posts[1]?.idempotencyKey ?? "").toBe(firstKey);
    expect(bodyOf(posts[1])["external_activity_id"]).toBe("EXT-A-101");
    await expect(page.getByRole("dialog", { name: "活动详情" }).locator('[data-field="id"]')).toHaveText("act-900");
  });
});
test.describe("UI-02 活动列表 · 深链接与作用域", () => {
  test("未登录深链：回合法入口、捕获原路径、会话建立后按原样恢复（含 q）", async ({ page }, info) => {
    const rec = watchConsole(page);
    const stub = await stubActivityApi(page);
    await page.goto(ACTIVITY_PATH + "?q=EXT-A-101");

    // 回到合法入口（COMMON.md:19）：受会话保护的路由在无会话时一律回 "/"。
    await expect(page).toHaveURL(ROOT_ONLY);
    await page.getByRole("button", { name: "证据" }).click();
    const evidence = page.getByRole("dialog", { name: "证据" });
    await expect(evidence).toBeVisible();
    // 捕获值按 dt→dd 结构取（禁裸子串）：待跳转深链必须逐字等于原始 fullPath。
    const captured = await page.evaluate(() => {
      const terms = Array.from(document.querySelectorAll('[role="dialog"] dt'));
      const hit = terms.find((term) => (term.textContent ?? "").trim() === "待跳转深链");
      const value = hit?.nextElementSibling;
      return value === undefined || value === null ? "" : (value.textContent ?? "").trim();
    });
    expect(captured).toBe(ACTIVITY_PATH + "?q=EXT-A-101");
    await shot(page, info, "deep-link-captured");
    await page.keyboard.press("Escape");
    await expect(evidence).toHaveCount(0);

    await signIn(page);
    await enterWorkspace(page);
    // 恢复：URL 与筛选框都回到深链原样，且请求真的带了 q（不是只在地址栏好看）。
    await expect(page).toHaveURL(/q=EXT-A-101/);
    await expect(page.getByLabel("按名称或编号搜索活动")).toHaveValue("EXT-A-101");
    await expectRows(page, 1);
    expect(lastParams(stub).get("q")).toBe("EXT-A-101");
    await shot(page, info, "deep-link-restored");
    await expectGatesClean(page, rec, "deep-link");
  });

  test("契约外子路径回 404 入口，不静默渲染活动列表", async ({ page }) => {
    const rec = watchConsole(page);
    const stub = await enterActivityList(page, rec);
    await expectRows(page, 4);
    expect((stub.listRequests().at(-1) as RecordedRequest).pathname).toBe(
      "/workspaces/" + WORKSPACE_ID + "/activities",
    );

    // 负对照：同一工作区前缀下未交付的子路径由 catch-all 承接（禁把 404 渲染成空列表）。
    await page.goto("/w/" + WORKSPACE_ID + "/not-a-page");
    await expect(page.locator("table.cl-table")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "页面不存在" })).toBeVisible();
    await expect(page.getByRole("link", { name: "返回入口" })).toBeVisible();
    // 404 页把请求过的深链原样回显（可核对，不猜）。
    const subtitle = await page.locator(".cl-card__sub").innerText();
    expect(subtitle.includes("/w/" + WORKSPACE_ID + "/not-a-page")).toBe(true);
    await expectGatesClean(page, rec, "not-found");

    await page.getByRole("link", { name: "返回入口" }).click();
    await expect(page).toHaveURL(ROOT_ONLY);
  });
});

test.describe("UI-02 活动列表 · 门禁自证（正负对照）", () => {
  test("六条浏览器侧门禁在正常态全绿，且植入违规必被抓到", async ({ page }) => {
    const rec = watchConsole(page);
    await enterActivityList(page, rec);
    await expectRows(page, 4);
    await expectGatesClean(page, rec, "gate-baseline");

    // 白名单双向校验：G6 的已知冻结面缺口清单必须与实测**逐字一致**
    // （既不允许白名单膨胀，也不允许里面留着已修好的条目）。
    const classScan = await scanClassDefinitions(page);
    expect(classGapDrift(classScan)).toEqual([]);
    expect(classScan.violations.map((item) => item.token).sort()).toEqual([...KNOWN_FROZEN_CLASS_GAPS].sort());

    const seeds: readonly GateSeed[] = [
      "forbidden-token",
      "overflow",
      "nesting",
      "undefined-class",
      "zero-size-chart",
    ];
    for (const seed of seeds) {
      await seedGateViolation(page, seed);
      expect(await violationCountFor(page, seed), "负对照失败：门禁没抓到 " + seed).toBeGreaterThan(0);
      await clearGateSeeds(page);
      expect(await violationCountFor(page, seed), "植入摘除后仍有违规：" + seed).toBe(0);
    }
    // 植入摘除后整页仍全绿（证明负对照没有留下残留）。
    await expectGatesClean(page, rec, "gate-after-seeds");
  });
});

/** 负对照专用：只跑与该种子相关的那一条门禁，返回违规条数。 */
async function violationCountFor(page: Page, seed: GateSeed): Promise<number> {
  if (seed === "forbidden-token") return (await scanForbiddenTokens(page)).length;
  if (seed === "overflow") return (await scanHorizontalOverflow(page)).length;
  if (seed === "nesting") return (await scanTagPairing(page)).length;
  if (seed === "undefined-class") {
    // 已登记的冻结面缺口（AppBar.vue 两个 class）不算本轮负对照的新增项；其穷举性由 classGapDrift 盯住。
    const scan = await scanClassDefinitions(page);
    return scan.violations.filter(
      (item) => item.token === undefined || !KNOWN_FROZEN_CLASS_GAPS.includes(item.token),
    ).length;
  }
  return (await scanChartContainers(page)).violations.length;
}
test.describe("UI-02 活动列表 · 合成标注（内容红线）", () => {
  test("页头芯片跟随服务端 source_class：授权脱敏工作区不显示「合成数据」", async ({ page }, info) => {
    const rec = watchConsole(page);
    // 负对照：同一页面、同一套活动数据，只把工作区的 source_class 换成 AUTHORIZED_DEIDENTIFIED。
    await enterActivityList(page, rec, { workspaceSourceClass: "AUTHORIZED_DEIDENTIFIED" });
    await expectRows(page, 4);

    const chip = page.locator('[data-part="source-class"]');
    await expect(chip).toHaveAttribute("data-source-class", "AUTHORIZED_DEIDENTIFIED");
    await expect(chip).toContainText("授权脱敏数据");
    // 反向断言：不得再出现「合成数据」字样（证明芯片不是写死的常量）。
    expect((await chip.innerText()).includes("合成数据")).toBe(false);
    await shot(page, info, "source-class-authorized");
    await expectGatesClean(page, rec, "source-class-authorized");
  });
});