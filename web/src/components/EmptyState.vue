<script setup lang="ts">
const props = defineProps<{ title: string; hint?: string | undefined; actionLabel?: string | undefined }>();
const emit = defineEmits<{ action: [] }>();
</script>
<template>
  <div class="cl-empty">
    <p class="cl-empty__title">{{ props.title }}</p>
    <p v-if="props.hint !== undefined && props.hint.length > 0" class="cl-empty__hint">{{ props.hint }}</p>
    <button v-if="props.actionLabel !== undefined && props.actionLabel.length > 0" type="button" class="cl-empty__action" @click="emit('action')">
      {{ props.actionLabel }}
    </button>
  </div>
</template>
<style scoped>
.cl-empty { padding: 32px 24px; text-align: center; border: 1px dashed var(--cl-line); border-radius: var(--cl-radius-sm); }
.cl-empty__title { margin: 0; color: var(--cl-ink-700); font-size: var(--cl-fs-body); }
.cl-empty__hint { margin: 8px 0 0; color: var(--cl-ink-500); font-size: 13px; }
.cl-empty__action { margin-top: 12px; height: var(--cl-btn-h-sm); padding: 0 12px; border: 1px solid var(--cl-brand-600); border-radius: var(--cl-radius-sm); background: var(--cl-card); color: var(--cl-brand-600); }
</style>
