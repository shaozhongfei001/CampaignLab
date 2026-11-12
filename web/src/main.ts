import { createApp } from "vue";
import App from "@/App.vue";

// 组合根（composition root）。后续子任务只在此处按固定顺序接线，不得在组件内散装配：
//   S3 → import "element-plus/dist/index.css";      // 组件库基础样式，必须最先
//        import "./styles/tokens.css";              // 项目令牌唯一真值（docs/design/token-mapping.md）
//        import "./styles/element-theme.css";       // --el-* ← var(--cl-*)，只允许出现在此文件
//        import "./styles/project.css";             // 项目级覆盖，只允许出现在此文件
//   S5 → app.provide(...) 注入 API 客户端与会话/工作区 store 单例
//   S6 → app.use(router)，router 落在 web/src/router/index.ts（createWebHistory，深链/刷新/404 回合法入口）
// S1 只保证挂载链路真实可用：vite build 与 vue-tsc 均以此为入口。
createApp(App).mount("#app");