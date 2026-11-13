<script setup lang="ts">
const props = defineProps<{ narrowTemplate?: "stack" | undefined }>();
</script>
<template>
  <div class="cl-grid" :data-narrow="props.narrowTemplate ?? 'stack'">
    <div class="cl-grid__main"><slot /></div>
    <div class="cl-grid__side"><slot name="side" /></div>
  </div>
</template>
<style scoped>
.cl-grid__main { grid-column: span 8; }
.cl-grid__side { grid-column: span 4; }
.cl-grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 16px; }
/* --cl-bp-rail-drawer */
@media (max-width: 800px) {
  .cl-grid__main, .cl-grid__side { grid-column: span 12; }
}
</style>
