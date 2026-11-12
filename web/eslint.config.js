import pluginVue from "eslint-plugin-vue";
import vueParser from "vue-eslint-parser";
import tsParser from "@typescript-eslint/parser";

// M0-01 最小 ESLint 扁平配置：覆盖 .vue（含 TS script 块）与 .ts/.js。
// @typescript-eslint/parser 是 eslint-plugin-vue 的可选 peer，此处显式声明以真实解析 TypeScript。
// TODO(M0-03)：如需类型感知规则，再引入 @typescript-eslint/eslint-plugin（需同步 dependencies.json）。
export default [
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "coverage/**",
      "test-results/**",
      "playwright-report/**",
      "src/api/generated/**",
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
];
