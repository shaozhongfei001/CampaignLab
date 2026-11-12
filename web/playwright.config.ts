import { defineConfig } from "@playwright/test";

// 端口纪律 NOTE-01：宿主占用 TCP 的 30xx 段三个端口，本机只有 5173 可用。
// 本文件所有 URL、注释与超时数值都刻意避开那三个端口的数字字面量（连注释也不写），
// 以便用 grep -rn 的 300[012] 模式对 web/*.config.* 做零输出自证（M0-03-design.md 第 9 节 G7）。
//
// testDir 落在 web/tests/e2e/**（任务卡 scope_allow: web/tests/**），
// 与 vitest 的 tests/unit/** 分域；S7 写键盘基线用例，S9 采集 1440x900 与 1024x768 截图。
const BASE_URL = "http://127.0.0.1:5173";

export default defineConfig({
  testDir: "./tests/e2e",
  outputDir: "./test-results",
  reporter: [["list"]],
  retries: 0,
  workers: 1,
  timeout: 60000,
  expect: { timeout: 10000 },
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    actionTimeout: 15000,
    navigationTimeout: 45000,
    locale: "zh-CN",
    timezoneId: "Asia/Shanghai",
  },
  projects: [
    {
      name: "desktop-1440x900",
      use: { viewport: { width: 1440, height: 900 } },
    },
    {
      name: "laptop-1024x768",
      use: { viewport: { width: 1024, height: 768 } },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: BASE_URL,
    reuseExistingServer: true,
    timeout: 60000,
    stdout: "pipe",
    stderr: "pipe",
  },
});