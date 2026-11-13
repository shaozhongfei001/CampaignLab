// S9：UI-01 视觉取证（1440x900 与 1024x768 两个 project，文件名全 ASCII）。
// 截图基于合成夹具，非端到端联调证据；BLK-01（浏览器/字体可用性）在回报里单列。
import { expect, test } from "@playwright/test";
import { stubCampaignLabApi } from "./fixtures/stubApi";

const NAMES: Record<string, string> = {
  "desktop-1440x900": "ui-01-desktop-1440x900",
  "laptop-1024x768": "ui-01-laptop-1024x768",
};

test("UI-01 入口页截图与关键尺寸取证", async ({ page }, info) => {
  const base = NAMES[info.project.name] ?? "ui-01-unknown";
  await stubCampaignLabApi(page);
  await page.goto("/");
  await expect(page.getByRole("button", { name: "刷新" })).toBeVisible();
  await page.locator("table caption").waitFor();
  const dir = new URL("../../../evidence/M0/", import.meta.url).pathname;
  await page.screenshot({ path: dir + "M0-03/" + base + ".png", fullPage: true });
  await page.screenshot({ path: dir + "ui/" + base + ".png", fullPage: true });
  const metrics = await page.evaluate(() => {
    const rail = document.querySelector("nav[aria-label='一级导航']") as HTMLElement | null;
    const bar = document.querySelector("header.cl-appbar") as HTMLElement | null;
    return {
      font: getComputedStyle(document.body).fontFamily,
      railWidth: rail ? rail.getBoundingClientRect().width : -1,
      topbarHeight: bar ? bar.getBoundingClientRect().height : -1,
      outlineWidth: (() => {
        const b = document.querySelector("button") as HTMLElement;
        b.focus();
        return getComputedStyle(b).outlineWidth;
      })(),
    };
  });
  await expect.poll(() => metrics.font.length).toBeGreaterThan(0);
  console.log("[ui01-metrics] " + JSON.stringify({ project: info.project.name, base, ...metrics }));
});
