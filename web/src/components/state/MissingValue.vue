<script setup lang="ts">
/**
 * web/src/components/state/MissingValue.vue —— 缺值呈现件（M0-03b / S3）
 *
 * 签名冻结源：M0-03b-freeze.md §3.5；呈现对齐 ui/COMMON.md:36「缺值显示 — 与原因。」
 * 与 token-mapping.md:45（数字一律 tabular-nums）。
 *
 * 缺值判定（§3.5 逐字）：value === null、或非有限的 number、或长度为 0 的 string → 渲染 —。
 * 空串视为缺值是**呈现层裁定**，不改变任何契约字段；数值 0 是合法原值，绝不判为缺值
 * （§1.3「不得渲染 0 冒充数据」的镜像：也不得把 0 吞成 —）。
 *
 * 边界（F-E / U-3，本卡不纳入冻结面）：单位换算（比率转百分数、金额分转元）不在本件，
 * 归各页面显示层，首次真实需要时抽公共件并走 CR。本件只做「— + 原因」。
 */
import { computed } from "vue";

const props = defineProps<{
  value: string | number | null;
  reason?: string | undefined;
  mono?: boolean | undefined;
}>();

const EM_DASH = "\u2014";

const missing = computed<boolean>(() => {
  const value = props.value;
  if (value === null) return true;
  if (typeof value === "number") return Number.isFinite(value) === false;
  return value.length === 0;
});

const shown = computed<string>(() => (missing.value ? EM_DASH : String(props.value)));

const hasReason = computed<boolean>(() => missing.value && props.reason !== undefined && props.reason.length > 0);
</script>

<template>
  <span class="cl-missing" :class="{ 'cl-missing--mono': props.mono === true }" :data-missing="missing ? 'true' : 'false'">
    <span class="cl-missing__value">{{ shown }}</span>
    <span v-if="hasReason" class="cl-missing__reason" data-part="reason">{{ props.reason }}</span>
  </span>
</template>

<style scoped>
.cl-missing {
  display: inline-flex;
  gap: var(--cl-space-2);
  align-items: baseline;
  max-width: 100%;
}
.cl-missing__value {
  color: var(--cl-ink-700);
}
.cl-missing--mono .cl-missing__value {
  font-family: var(--cl-font-mono);
  font-variant-numeric: tabular-nums;
}
.cl-missing__reason {
  color: var(--cl-ink-600);
  font-size: var(--cl-fs-label);
}
</style>
