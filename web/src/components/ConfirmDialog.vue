<script setup lang="ts">
// Q3 裁定：M0-03 交付最小实现（520px，摘要 + 影响 + 取消 + 主按钮），M2-04 复用同一实现。
const props = defineProps<{
  open: boolean;
  summary: string;
  impact: string;
  confirmLabel?: string | undefined;
  cancelLabel?: string | undefined;
}>();
const emit = defineEmits<{ confirm: []; cancel: [] }>();
</script>
<template>
  <div v-if="props.open" class="cl-confirm-mask" @keydown.esc="emit('cancel')">
    <div class="cl-confirm" role="dialog" aria-modal="true" :aria-label="props.summary" tabindex="-1">
      <p class="cl-confirm__label">确认动作</p>
      <h2 class="cl-confirm__summary">{{ props.summary }}</h2>
      <p class="cl-confirm__impact">{{ props.impact }}</p>
      <div class="cl-confirm__actions">
        <button type="button" class="cl-confirm__cancel" @click="emit('cancel')">{{ props.cancelLabel ?? "取消" }}</button>
        <button type="button" class="cl-confirm__ok" @click="emit('confirm')">{{ props.confirmLabel ?? "确认提交" }}</button>
      </div>
    </div>
  </div>
</template>
<style scoped>
.cl-confirm-mask { position: fixed; inset: 0; background: var(--cl-canvas); display: grid; place-items: center; z-index: 40; }
.cl-confirm { width: var(--cl-dialog-w); max-width: calc(100vw - 32px); background: var(--cl-card); border: 1px solid var(--cl-line); border-radius: var(--cl-radius-sm); padding: 24px; box-shadow: var(--cl-shadow-1); }
.cl-confirm__label { margin: 0; font-size: 13px; color: var(--cl-ink-500); }
.cl-confirm__summary { margin: 8px 0; font-size: var(--cl-fs-body); color: var(--cl-ink-900); }
.cl-confirm__impact { margin: 0 0 16px; font-size: 13px; color: var(--cl-ink-600); }
.cl-confirm__actions { display: flex; justify-content: flex-end; gap: 8px; }
.cl-confirm__cancel { height: var(--cl-btn-h); padding: 0 16px; border: 1px solid var(--cl-line); border-radius: var(--cl-radius-sm); background: var(--cl-card); color: var(--cl-ink-700); }
.cl-confirm__ok { height: var(--cl-btn-h); padding: 0 16px; border: 1px solid var(--cl-brand-600); border-radius: var(--cl-radius-sm); background: var(--cl-brand-600); color: var(--cl-card); }
</style>
