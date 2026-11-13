<script setup lang="ts">
const props = defineProps<{ title: string; crumb?: string | undefined }>();
</script>
<template>
  <div class="cl-pagebar">
    <p v-if="props.crumb !== undefined && props.crumb.length > 0" class="cl-pagebar__crumb">{{ props.crumb }}</p>
    <h1 class="cl-pagebar__title">{{ props.title }}</h1>
    <div class="cl-pagebar__meta"><slot name="meta" /></div>
  </div>
</template>
<style scoped>
.cl-pagebar { display: grid; gap: 4px; padding: 16px 0; }
.cl-pagebar__crumb { margin: 0; font-size: 13px; color: var(--cl-ink-500); }
.cl-pagebar__title { margin: 0; font-size: 18px; line-height: 32px; color: var(--cl-ink-900); }
.cl-pagebar__meta { display: flex; gap: 8px; flex-wrap: wrap; font-size: 13px; color: var(--cl-ink-500); }
</style>
