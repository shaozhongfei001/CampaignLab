import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// 端口纪律 NOTE-01：宿主已占用 TCP 的 30xx 段三个端口（实测 BUSY），5173 FREE。
// dev 与 preview 一律固定 5173 且 strictPort=true —— 端口被占即失败退出，
// 不允许 vite 自动顺延到 5174（顺延会让 playwright.config.ts 的 baseURL 指向空气）。
// 注：本文件刻意不出现那三个被占端口的数字字面量，以免 grep -rn 端口自证命令误命中。
//
// 别名 @ -> <web>/src，与 tsconfig.json 的 compilerOptions.paths 同义；
// vitest 经 vitest.config.ts 展开本对象继承同一份别名（单一真值，避免三处漂移）。
//
// 不使用 node:path / node:url：web/package.json 未声明 @types/node（M0-03-design.md 未决问题 Q2），
// 故用 WHATWG URL + import.meta.url 求绝对路径，零 node 内建依赖、零新增声明。
// Vite 的配置加载器为每个文件注入其原始 import.meta.url，故本文件与被 vitest 导入时结果一致。
const toAbsoluteDir = (relative: string): string => {
  const pathname = decodeURIComponent(new URL(relative, import.meta.url).pathname);
  // Windows 下 URL.pathname 形如 "/D:/ws/..."；本仓库约定代码在 WSL2 ext4（docs/design/frontend-pitfalls.md），
  // 但仍剥掉前导斜杠以保证跨宿主可用。
  return /^\/[A-Za-z]:\//.test(pathname) ? pathname.slice(1) : pathname;
};

// R3-Q1 裁定（编排器落地，2026-11-13T06:55:00+08:00）：src/api/http.ts 的 baseUrl 只从 VITE_API_BASE_URL 注入、
// 默认走**同源相对路径**，而全部路由形如 /api/v1/**，故 dev 与 preview 都必须把 /api 反代到后端，
// 否则前端基线只能对着空气发请求。
//
// 目标端口硬编码而非读环境变量，是三条约束的交集：
//   1) 本文件必须保持**对象形态**导出 —— vitest.config.ts 以 `...viteConfig` 展开继承别名与 server，
//      改成 defineConfig(({ mode }) => ...) 的函数形态会让展开失效、别名继承断裂；
//   2) web/package.json 未声明 @types/node，故不可用 process.env（与本文件上方不用 node:path 同理）；
//   3) loadEnv 需要把配置改成函数形态，同样违反 1)。
// 端口 8000 由编排器实测选定：127.0.0.1:8000 FREE、8080 FREE、5173 为 vite 自身，
// 宿主 3000/3001/3002 实测 BUSY（NOTE-01）。该端口是**项目级默认约定**而非契约项，
// 已登记于 orchestrator/state.json -> decisions.dev_proxy_target；后端 config.py/cli.py 落地时
// （M0-02/S3c）必须取同一默认值，否则前后端起在不同端口上。
//
// changeOrigin=false 是刻意的：保留浏览器原始 Host，使后端 api/common.py::OriginHostGuard
// 能真正校验 Host/Origin（ADR-005、M0-02-design.md §4）。改成 true 会让守卫永远看到 127.0.0.1
// 而失去意义 —— 那是一种假绿。
const API_PROXY = {
  "/api": {
    target: "http://127.0.0.1:8000",
    changeOrigin: false,
  },
};

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": toAbsoluteDir("./src"),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    target: "es2022",
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: API_PROXY,
  },
  preview: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: API_PROXY,
  },
});