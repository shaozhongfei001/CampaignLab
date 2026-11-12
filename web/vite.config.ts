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
  },
  preview: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
});