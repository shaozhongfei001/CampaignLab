import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// M0-01 最小可用构建配置：产物固定为 web/dist，供 scripts/verify.sh 之外的前端基线使用。
// M0-03 起在此追加别名、按需引入 Element Plus、ECharts 与代理等真实前端配置。
export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
  },
});
