import { defineConfig } from "vitest/config";
import viteConfig from "./vite.config.ts";

// vitest 单独成文而非把 test 块塞进 vite.config.ts：
//   1) vite build 不必载入 vitest（构建期依赖面更小）；
//   2) 别名/server 仍从 vite.config.ts 展开继承，单一真值；
//   3) vitest 优先读取 vitest.config.*，不会与 vite.config.ts 打架。
//
// environment 固定 "node"：web/package.json 未声明 jsdom / happy-dom / @vue/test-utils
// （M0-03-design.md 未决问题 Q1）。在 DOM 环境获批前，tests/** 与 src/** 的用例
// 一律不得触碰 document / window / getComputedStyle —— 否则是环境缺失导致的假红。
//
// tests/e2e/** 由 @playwright/test 独占（见 playwright.config.ts 的 testDir），
// 必须从 vitest 的 include 中排除，否则 Playwright 用例会被 vitest 误跑成红。
export default defineConfig({
  ...viteConfig,
  test: {
    environment: "node",
    include: ["src/**/*.spec.ts", "tests/**/*.spec.ts"],
    exclude: ["tests/e2e/**", "node_modules/**", "dist/**", "test-results/**", "playwright-report/**"],
    restoreMocks: true,
    clearMocks: true,
    reporters: ["default"],
  },
});