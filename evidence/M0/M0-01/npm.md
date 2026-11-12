# M0-01 npm 依赖解析结论

取证时间 2026-11-12T03:26:10+08:00（编排器独立复核，非开发自述）

| 项 | 结果 |
|---|---|
| package-lock.json | 122775 字节，sha256 前16 ee1cd610219f6347 |
| npm ci | rc=0，added 218 packages in 8s |
| npm run build | rc=0，vite 产出 dist/index.html 0.32 kB 与 dist/assets/index-*.js 62.82 kB |
| npm 版本 | 11.19.1（Node v24.22.3 自带，Linux 路径） |
| engines | node 约束 >=24,<25，与 contracts/dependencies.json 一致 |
| peer 冲突 | 无（npm ci 未报 ERESOLVE） |
| 区间符合性 | vue、vue-router、element-plus、echarts 与 vite、@vitejs/plugin-vue、typescript、vitest、@playwright/test、vue-tsc、eslint、eslint-plugin-vue、openapi-typescript 均落在 dependencies.json 区间内 |

web/dist 与 web/node_modules 由根 .gitignore 排除，不入库。
