<script setup lang="ts">
import { onBeforeUpdate, onUpdated, ref } from "vue";
// COMMON.md：证据抽屉桌面 480px，窄屏全宽；Esc 可关闭并返回触发焦点。
const props = defineProps<{ open: boolean; title: string }>();
const emit = defineEmits<{ close: [] }>();
const panel = ref<HTMLElement | null>(null);
const trigger = ref<HTMLElement | null>(null);
const closable = ref(false);

onUpdated(() => {
  if (props.open && !closable.value) {
    closable.value = true;
    panel.value?.focus();
  }
  if (!props.open && closable.value) {
    closable.value = false;
    trigger.value?.focus();
    trigger.value = null;
  }
});
onBeforeUpdate(() => {
  if (props.open && trigger.value === null) {
    trigger.value = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  }
});

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    event.stopPropagation();
    emit("close");
  }
}
</script>
<template>
  <div v-if="open" class="cl-drawer" role="dialog" aria-modal="true" :aria-label="title" tabindex="-1" ref="panel" @keydown="onKeydown">
    <header class="cl-drawer__head">
      <h2>{{ title }}</h2>
      <button type="button" class="cl-drawer__close" @click="emit('close')">关闭证据</button>
    </header>
    <div class="cl-drawer__body"><slot /></div>
  </div>
</template>
<style scoped>
.cl-drawer { position: fixed; top: var(--cl-topbar-h); right: 0; width: var(--cl-drawer-w); height: calc(100vh - var(--cl-topbar-h)); background: var(--cl-card); border-left: 1px solid var(--cl-line); z-index: 30; display: grid; grid-template-rows: auto 1fr; }
.cl-drawer__head { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--cl-line); }
.cl-drawer__head h2 { margin: 0; font-size: var(--cl-fs-body); color: var(--cl-ink-900); }
.cl-drawer__close { height: var(--cl-btn-h-sm); padding: 0 12px; border: 1px solid var(--cl-line); border-radius: var(--cl-radius-sm); background: var(--cl-card); color: var(--cl-ink-700); }
.cl-drawer__body { padding: 16px; overflow: auto; font-size: 13px; color: var(--cl-ink-600); }
/* --cl-bp-rail-drawer */
@media (max-width: 800px) {
  .cl-drawer { width: 100%; }
}
</style>
