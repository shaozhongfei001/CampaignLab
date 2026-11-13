<script setup lang="ts">
/**
 * web/src/components/state/FirstLoadSkeleton.vue —— 首载骨架（M0-03b / S3）
 *
 * 签名冻结源：M0-03b-freeze.md §3.5；呈现要素对齐 ui/COMMON.md:27
 * 「主区骨架对应标题、表头和卡片位置。保留导航」。
 *
 * 三条硬约束（S2 逐条断言）：
 *   1. 只占位不出字：heading 只决定「标题占位块是否出现」，其值**不渲染为文字**（§1.3 首载行「无文案」）；
 *   2. 不冒充数据：不渲染 0、空串或任何数字（§1.3 首载行「不得渲染 0 或空串冒充数据」，缺值一律走 MissingValue）；
 *   3. 保留导航：本件是纯内容层骨架，不得包裹或替换 SideRail —— 它只应放进 AppShell 的 default slot
 *      （AppShell.vue:14）。故本文件不 import 任何布局件。
 */
const props = defineProps<{
  heading?: string | undefined;
  headCells?: readonly string[] | undefined;
  cardCount?: number | undefined;
}>();

const cellCount = (): number => props.headCells?.length ?? 0;
const cards = (): number => props.cardCount ?? 0;
</script>

<template>
  <div class="cl-skeleton" data-part="first-load-skeleton">
    <div v-if="props.heading !== undefined" class="cl-skeleton__heading" data-part="heading" />
    <div v-if="cellCount() > 0" class="cl-skeleton__row" data-part="head-row">
      <span v-for="cell in cellCount()" :key="'h' + cell" class="cl-skeleton__cell" data-part="head-cell" />
    </div>
    <div v-if="cards() > 0" class="cl-skeleton__cards" data-part="card-row">
      <span v-for="card in cards()" :key="'c' + card" class="cl-skeleton__card" data-part="card" />
    </div>
  </div>
</template>

<style scoped>
.cl-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--cl-space-3);
  width: 100%;
  max-width: 100%;
}
.cl-skeleton__heading {
  width: 40%;
  height: var(--cl-fs-body);
  background: var(--cl-ink-100);
  border-radius: var(--cl-radius-sm);
  animation: cl-skeleton-pulse 1.6s ease-in-out infinite;
}
.cl-skeleton__row {
  display: flex;
  gap: var(--cl-space-2);
  flex-wrap: wrap;
}
.cl-skeleton__cell {
  flex: 1 1 var(--cl-space-6);
  min-width: var(--cl-space-6);
  height: var(--cl-fs-label);
  background: var(--cl-ink-200);
  border-radius: var(--cl-radius-sm);
  animation: cl-skeleton-pulse 1.6s ease-in-out infinite;
}
.cl-skeleton__cards {
  display: flex;
  gap: var(--cl-space-3);
  flex-wrap: wrap;
}
.cl-skeleton__card {
  flex: 1 1 var(--cl-space-6);
  min-width: var(--cl-space-6);
  min-height: var(--cl-row-h);
  background: var(--cl-ink-100);
  border: 1px solid var(--cl-line);
  border-radius: var(--cl-radius-md);
  animation: cl-skeleton-pulse 1.6s ease-in-out infinite;
}
@keyframes cl-skeleton-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}
</style>
