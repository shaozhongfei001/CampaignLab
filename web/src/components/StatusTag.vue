<script setup lang="ts">
import type { StatusTone } from "./componentTypes";
const props = defineProps<{ label: string; tone?: StatusTone | undefined }>();
const tone = (): StatusTone => props.tone ?? "NEUTRAL";
</script>
<template>
  <span class="cl-tag" :class="'is-' + tone().toLowerCase()">{{ label }}</span>
</template>
<style scoped>
.cl-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 20px;
  padding: 0 8px;
  border: 1px solid var(--cl-line);
  border-radius: var(--cl-radius-sm);
  font-size: 13px;
  color: var(--cl-ink-600);
  background: var(--cl-canvas);
}
.cl-tag::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.is-ok { color: var(--cl-ok-text); border-color: var(--cl-ok-600); }
.is-warn { color: var(--cl-warn-text); border-color: var(--cl-warn-600); }
.is-danger { color: var(--cl-danger-text); border-color: var(--cl-danger-600); }
.is-info { color: var(--cl-ink-600); border-color: var(--cl-info-600); }
.is-neutral { color: var(--cl-ink-500); }
</style>
