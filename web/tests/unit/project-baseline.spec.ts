import { describe, expect, it } from "vitest";
import playwrightConfig from "../../playwright.config";
import tsconfig from "../../tsconfig.json";
import viteConfig from "../../vite.config";

// M0-03/S1 冒烟用例：断言的是「工程基线不变量」，不是业务逻辑。
// 四条都是后续子任务会踩的坑，先钉死：
//   1. NOTE-01 端口纪律 —— 宿主占用 3000/3001/3002，dev/preview/e2e 一律 5173 且 strictPort；
//   2. 别名单一真值 —— vite 侧 @ 与 tsconfig.compilerOptions.paths 必须同义（vitest 由 vitest.config.ts 继承）；
//   3. 严格开关不得被后续 lane 悄悄关掉；
//   4. 测试分域 —— vitest 不得吃 tests/e2e（Playwright 独占），否则 S7 用例会假红。
// 环境为 node（无 jsdom，见未决问题 Q1），故本文件不得触碰 document / window。

// AliasOptions = readonly Alias[] | { [find: string]: string }；本工程只用对象形式。
const readAlias = (alias: unknown): string | undefined => {
  if (alias === undefined || alias === null || Array.isArray(alias)) {
    return undefined;
  }
  return (alias as Record<string, string>)["@"];
};

describe("M0-03/S1 工程基线", () => {
  it("vite dev 与 preview 固定 5173 且 strictPort（NOTE-01）", () => {
    expect(viteConfig.server?.port).toBe(5173);
    expect(viteConfig.server?.strictPort).toBe(true);
    expect(viteConfig.preview?.port).toBe(5173);
    expect(viteConfig.preview?.strictPort).toBe(true);
  });

  it("playwright 的 baseURL 与 webServer 均指向 5173，且配置全文无 3000/3001/3002", () => {
    const serialized = JSON.stringify(playwrightConfig) ?? "";
    expect(serialized).toContain("http://127.0.0.1:5173");
    expect(serialized).not.toMatch(/300[012]/);
    const serializedVite = JSON.stringify(viteConfig) ?? "";
    expect(serializedVite).not.toMatch(/300[012]/);
  });

  it("别名 @ 在 vite 与 tsconfig 两侧一致", () => {
    const at = readAlias(viteConfig.resolve?.alias);
    expect(typeof at).toBe("string");
    expect(at ?? "").toMatch(/\/web\/src$/);
    expect(tsconfig.compilerOptions.paths?.["@/*"]).toEqual(["src/*"]);
    expect(tsconfig.compilerOptions.baseUrl).toBe(".");
  });

  it("tsconfig 严格开关全部开启（vue-tsc 门禁前提）", () => {
    const options = tsconfig.compilerOptions;
    expect(options.strict).toBe(true);
    expect(options.noUncheckedIndexedAccess).toBe(true);
    expect(options.exactOptionalPropertyTypes).toBe(true);
    expect(options.noImplicitOverride).toBe(true);
    expect(options.noFallthroughCasesInSwitch).toBe(true);
    expect(tsconfig.include).toContain("tests/**/*.ts");
  });
});