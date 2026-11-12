import pluginVue from "eslint-plugin-vue";
import vueParser from "vue-eslint-parser";
import tsParser from "@typescript-eslint/parser";

// M0-03/S1 严格基线扁平配置：覆盖 .vue（含 TS script 块）与 .ts/.js。
// @typescript-eslint/parser 是 eslint-plugin-vue 的可选 peer，此处显式声明以真实解析 TypeScript。
// 注意：仓库只声明了 @typescript-eslint/parser，没有 @typescript-eslint/eslint-plugin，
// 因此本配置只使用 ESLint 核心规则 + eslint-plugin-vue，不启用任何需要类型信息的规则
// （新增该插件属改 package.json，须先经编排器裁定，见 M0-03-design.md 未决问题 Q2）。
//
// 三条项目红线在本配置里做成机器门禁（ADR-003 C 段 / 任务卡「不写死色值」「不 import 模板」）：
//   1. src/** 内禁止六位十六进制色值字面量 —— 令牌唯一真值是 web/src/styles/tokens.css（S3）；
//   2. src/** 内禁止 import 前端模板产物（youxia-*.js / frontend-template-spdb-*）；
//   3. src/** 内禁止 console.*（ADR-003 A 段门禁要求浏览器 0 个 console.error）。
// 说明：<style> 块与 .css 文件不经 ESLint 解析，第 1 条只能覆盖 TS/JS/模板表达式，
// CSS 侧由 rg -n '#[0-9a-fA-F]{6}' web/src --glob '!**/styles/tokens.css' 兜底（两者互补，缺一不可）。
export default [
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "coverage/**",
      "test-results/**",
      "playwright-report/**",
      // openapi-typescript 产物（S4）：约 400KB 生成代码，逐行 lint 无意义且会掩盖真实告警。
      "src/api/generated/**",
      "src/api/types.ts",
    ],
  },
  ...pluginVue.configs["flat/essential"],
  {
    files: ["**/*.ts", "**/*.mts", "**/*.cts"],
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaVersion: "latest", sourceType: "module" },
    },
  },
  {
    files: ["**/*.vue"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: "latest",
        sourceType: "module",
      },
    },
    rules: {
      "vue/multi-word-component-names": "off",
    },
  },
  {
    // 项目红线：只对 src/** 生效，tests/** 允许构造十六进制字符串做对比度断言（token-mapping.md 第 4.4 条）。
    files: ["src/**/*.ts", "src/**/*.vue"],
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          selector: "Literal[value=/#[0-9a-fA-F]{6}/]",
          message:
            "禁止写死六位十六进制色值：请使用 var(--cl-*)（令牌真值 docs/design/token-mapping.md，落地文件 web/src/styles/tokens.css）。",
        },
      ],
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["*frontend-template-spdb*", "*youxia*"],
              message:
                "模板 spec/frontend-template-spdb-v1.1 只是视觉真值参照，不得 import 其 CSS/JS（ADR-003 决定节）。",
            },
          ],
        },
      ],
      "no-console": "error",
    },
  },
];