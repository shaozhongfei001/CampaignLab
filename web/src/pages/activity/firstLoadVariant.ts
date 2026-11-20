/**
 * web/src/pages/activity/firstLoadVariant.ts —— UI-02 首载骨架的 variant 注册（§4.2 外部注册扩展点）
 *
 * R-5「无副作用装载」的落点：registry.ts 顶层零注册，注册只发生在**调用方模块**（本文件）。
 * 本模块由 ActivityListPage.vue 以副作用方式 import ⇒ 模块只求值一次（ESM 语义），
 * 不会像写在 <script setup> 里那样每次组件实例化都重复注册（那会触发 R-2 的覆盖告警）。
 *
 * appliesTo 的判定只用 ViewState.context 的两个字段（均由页面显式传入，FU-27 公共件禁读路由）：
 *   routeName === "activity-list"（contracts/pages.json UI-02 的路由名）＋ state === "first-load"。
 * 其余五态一律不命中 ⇒ 继续走 ViewState 的默认呈现（文案/动作键不变）。
 */
import { registerViewStateVariant } from "@/components/state/registry";
import ActivityFirstLoad from "./ActivityFirstLoad.vue";

/** 注册 id（R-2 幂等：同 id 重复注册即覆盖）。 */
export const ACTIVITY_FIRST_LOAD_VARIANT_ID = "ui-02-first-load-skeleton";

/** contracts/pages.json UI-02 的 route 对应的路由名（web/src/router/index.ts）。 */
export const ACTIVITY_ROUTE_NAME = "activity-list";

registerViewStateVariant({
  id: ACTIVITY_FIRST_LOAD_VARIANT_ID,
  appliesTo: (context) => context.routeName === ACTIVITY_ROUTE_NAME && context.state === "first-load",
  render: ActivityFirstLoad,
});