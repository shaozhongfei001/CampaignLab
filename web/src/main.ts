import { createApp } from "vue";
import App from "@/App.vue";

// 组合根（composition root）。后续子任务只在此处按固定顺序接线，不得在组件内散装配：
//   S3（已接线，顺序即 M0-03-design.md 2.1，错序则覆盖失效）：
//     1) element-plus/dist/index.css  组件库基础样式，必须最先
//     2) ./styles/tokens.css          项目令牌唯一真值（docs/design/token-mapping.md）
//     3) ./styles/element-theme.css   --el-* ← var(--cl-*)，只允许出现在此文件
//     4) ./styles/project.css         项目级覆盖，只允许出现在此文件
//   S5（本次接线）→ app.provide(...) 注入 API 客户端 + 会话 / 工作区作用域 / 工作区 store 单例
//     （Q5 裁定：Vue 原生 reactive + composable 单例，不引入 Pinia、不新增 stores 层）
//   S6 → app.use(router)，router 落在 web/src/router/index.ts（createWebHistory，深链/刷新/404 回合法入口）
import "element-plus/dist/index.css";
import "./styles/tokens.css";
import "./styles/element-theme.css";
import "./styles/project.css";

import { http, httpKey } from "@/api/http";
import { sessionStoreKey, useSession } from "@/composables/useSession";
import { useWorkspaceScope, workspaceScopeKey } from "@/composables/useWorkspaceScope";
import { useWorkspaces, workspacesStoreKey } from "@/composables/useWorkspaces";

const app = createApp(App);

// 注入顺序 = 依赖顺序：http ← scope ← session ← workspaces（后者复用前者的单例，不重复创建）。
app.provide(httpKey, http);
app.provide(workspaceScopeKey, useWorkspaceScope());
app.provide(sessionStoreKey, useSession());
app.provide(workspacesStoreKey, useWorkspaces());

// S1 只保证挂载链路真实可用：vite build 与 vue-tsc 均以此为入口。
app.mount("#app");
