<script setup lang="ts">
// COMMON.md 一级导航六项。UI-01 只交付「入口」；其余六项目标页属 M0-04+（未交付），
// 故以 aria-disabled 呈现，不发假路由（前端不发明未规定的语义）。
const props = defineProps<{ drawer?: boolean | undefined; entryActive?: boolean | undefined }>();
</script>
<template>
  <nav class="cl-rail" :class="{ 'is-drawer': props.drawer === true }" aria-label="一级导航">
    <router-link v-if="props.entryActive !== false" class="cl-rail__item is-entry" to="/">入口</router-link>
    <span class="cl-rail__group">工作区</span>
    <ul class="cl-rail__list">
      <li v-for="item in ['活动与规则', '数据与口径', '仿真与验收', '策略复盘', '报告与改进', '作业与证据']" :key="item">
        <a class="cl-rail__item" href="#" aria-disabled="true" @click.prevent>{{ item }}</a>
      </li>
    </ul>
  </nav>
</template>
<style scoped>
.cl-rail { width: var(--cl-rail-w); background: var(--cl-nav-grad); color: var(--cl-card); padding: 16px 12px; display: grid; align-content: start; gap: 4px; }
.cl-rail__group { font-size: 13px; color: var(--cl-ink-300); margin: 12px 4px 4px; }
.cl-rail__list { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
.cl-rail__item { display: block; padding: 8px 12px; border-radius: var(--cl-radius-sm); color: var(--cl-card); text-decoration: none; font-size: var(--cl-fs-body); }
.cl-rail__item[aria-disabled="true"] { color: var(--cl-ink-300); cursor: not-allowed; }
/* --cl-bp-rail-collapse */
@media (max-width: 1100px) {
  .cl-rail { width: var(--cl-rail-w-collapsed); padding: 16px 6px; }
  .cl-rail__item { padding: 8px 4px; font-size: 12px; }
  .cl-rail__group { display: none; }
}
/* --cl-bp-rail-drawer */
@media (max-width: 800px) {
  .cl-rail { width: 100%; }
}
.is-entry { background: var(--cl-brand-600); }
</style>
