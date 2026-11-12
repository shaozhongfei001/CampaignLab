import { defineConfig, devices } from "@playwright/test";

// M0-01 仅提供真实入口；e2e 用例属 M5-01，浏览器二进制安装属 BLK-01（需 root）。
export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    ...devices["Desktop Chrome"],
    viewport: { width: 1440, height: 900 },
  },
});
