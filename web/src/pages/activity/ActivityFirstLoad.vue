<script setup lang="ts">
/**
 * web/src/pages/activity/ActivityFirstLoad.vue —— UI-02 首载骨架的 variant 呈现件
 *
 * 为什么需要这一件（而不是页面直接渲染 FirstLoadSkeleton）：
 *   - ViewState 的 props 面（M0-03b-freeze.md §3.4）里没有 headCells / cardCount，
 *     默认骨架无法对应本页的六列表头（COMMON.md:27「主区骨架对应标题、表头和卡片位置」）；
 *   - 但若绕过 ViewState 直接渲染 FirstLoadSkeleton，就会丢掉 data-state / role / aria-live / aria-busy
 *     四条非颜色载体（AC-032「状态可读…不靠颜色区分」），首载态在机器可读面上变成哑态。
 *   ⇒ 走 §4.2 的**外部注册扩展点**（registry.registerViewStateVariant({ render })）覆写呈现：
 *     形状由本页决定，四载体仍由冻结件 ViewState 统一发出。注册见同目录 firstLoadVariant.ts。
 *
 * 属性透传纪律：ViewState 以 v-bind="overrideProps" 透传 9 个键（§3.4），本件**逐一声明为 props**，
 *   否则 Vue 的属性回退会把 error 对象序列化成 "[object Object]" 落到 DOM 属性上
 *   —— 正好撞上机器门禁第 2 条（页面文本与属性禁 [object Object]）。
 */
import type { ApiError } from "@/api/http";
import FirstLoadSkeleton from "@/components/state/FirstLoadSkeleton.vue";
import type { ViewStateAction, ViewStateKind } from "@/components/state/viewState";
import { ACTIVITY_COLUMN_LABELS } from "@/features/activity/presentation";

defineProps<{
  state: ViewStateKind;
  title: string;
  hint: string;
  error: ApiError | null;
  actions: readonly ViewStateAction[];
  missing: readonly string[];
  reason?: string | undefined;
  showPrevious: boolean;
  keepInput: boolean;
}>();

/**
 * FirstLoadSkeleton 的 heading 只决定「标题占位块是否出现」，其值**不渲染为文字**（§3.5 第 1 条），
 * 故此处取页面标题字面量仅为语义可读；真正的标题文字由 PageBar 渲染（单一出处）。
 */
const HEADING = "活动总览";
const CARD_COUNT = 2;
</script>

<template>
  <FirstLoadSkeleton :heading="HEADING" :head-cells="ACTIVITY_COLUMN_LABELS" :card-count="CARD_COUNT" />
</template>