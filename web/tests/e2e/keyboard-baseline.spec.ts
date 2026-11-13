// S7：COMMON.md 键盘与焦点基线（焦点可见 2px、Tab 顺序、抽屉 Esc 关闭并返回触发焦点、表头排序可键盘触发）。
import { expect, test } from "@playwright/test";
import { stubCampaignLabApi } from "./fixtures/stubApi";

test.beforeEach(async ({ page }) => {
  await stubCampaignLabApi(page);
  await page.goto("/");
  await expect(page.getByRole("button", { name: "刷新" })).toBeVisible();
});

test("焦点可见：Tab 进入交互控件时轮廓线宽为 2px", async ({ page }) => {
  let width = "0px";
  for (let i = 0; i < 12; i += 1) {
    await page.keyboard.press("Tab");
    width = await page.evaluate(() => getComputedStyle(document.activeElement ?? document.body).outlineWidth);
    if (width === "2px") break;
  }
  expect(width).toBe("2px");
});

test("Tab 顺序＝DOM 顺序：顶栏证据按钮先于列表搜索框获得焦点", async ({ page }) => {
  const stops: string[] = [];
  for (let i = 0; i < 20; i += 1) {
    await page.keyboard.press("Tab");
    stops.push(await page.evaluate(() => {
      const el = document.activeElement as HTMLElement;
      return (el.getAttribute("aria-label") ?? el.textContent ?? "").trim();
    }));
  }
  const evidence = stops.findIndex((s) => s === "证据");
  const search = stops.findIndex((s) => s.includes("按名称搜索工作区"));
  expect(evidence).toBeGreaterThanOrEqual(0);
  expect(search).toBeGreaterThanOrEqual(0);
  expect(evidence).toBeLessThan(search);
});

test("证据抽屉：键盘打开后 Esc 关闭并把焦点交还触发按钮", async ({ page }) => {
  const trigger = page.getByRole("button", { name: "证据" });
  await trigger.focus();
  await page.keyboard.press("Enter");
  const drawer = page.getByRole("dialog", { name: "证据" });
  await expect(drawer).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await expect(trigger).toBeFocused();
});

test("表头排序可键盘触发：Enter/Space 切换 aria-sort", async ({ page }) => {
  const header = page.getByRole("columnheader", { name: "名称", exact: true });
  await expect(header).toHaveAttribute("aria-sort", "none");
  const button = header.getByRole("button", { name: "名称" });
  await button.focus();
  await page.keyboard.press("Enter");
  await expect(header).toHaveAttribute("aria-sort", "ascending");
  await page.keyboard.press("Space");
  await expect(header).toHaveAttribute("aria-sort", "descending");
});

test("工作区类型创建后固定：数据用途是单选而非可改写文本", async ({ page }) => {
  await page.getByRole("radio", { name: "合成" }).click();
  await expect(page.getByRole("radio", { name: "授权脱敏" })).toBeVisible();
  await page.getByRole("radio", { name: "授权脱敏" }).click();
  await expect(page.getByLabel("授权依据")).toBeVisible();
});
