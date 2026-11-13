<script setup lang="ts">
const props = defineProps<{ title: string; subtitle?: string | undefined }>();
</script>
<template>
  <section class="cl-card" :aria-label="props.title">
    <header class="cl-card__head">
      <h2 class="cl-card__title">{{ props.title }}</h2>
      <p v-if="props.subtitle !== undefined && props.subtitle.length > 0" class="cl-card__sub">{{ props.subtitle }}</p>
      <div class="cl-card__actions"><slot name="actions" /></div>
    </header>
    <div class="cl-card__body"><slot /></div>
    <footer class="cl-card__foot"><slot name="footer" /></footer>
  </section>
</template>
<style scoped>
.cl-card { border: 1px solid var(--cl-line); border-radius: var(--cl-radius-sm); background: var(--cl-card); box-shadow: var(--cl-shadow-1); }
.cl-card__head { padding: 12px 16px; border-bottom: 1px solid var(--cl-line); display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; }
.cl-card__title { margin: 0; font-size: var(--cl-fs-body); color: var(--cl-ink-900); line-height: 32px; }
.cl-card__sub { grid-column: 1; margin: 0; font-size: 13px; color: var(--cl-ink-500); }
.cl-card__actions { grid-row: 1 / span 2; grid-column: 2; display: flex; gap: 8px; align-items: center; }
.cl-card__body { padding: 16px; }
.cl-card__foot { padding: 12px 16px; border-top: 1px solid var(--cl-line); font-size: 13px; color: var(--cl-ink-500); }
.cl-card__foot:empty { display: none; }
</style>
