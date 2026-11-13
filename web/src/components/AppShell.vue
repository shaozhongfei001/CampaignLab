<script setup lang="ts">
import AppBar from "./AppBar.vue";
import SideRail from "./SideRail.vue";
import type { Health } from "@/api/endpoints";
import type { Session } from "@/api/endpoints";
const props = defineProps<{ health?: Health | undefined; session?: Session | undefined; recentWorkspace?: string | null }>();
const emit = defineEmits<{ evidence: [] }>();
</script>
<template>
  <div class="cl-shell">
    <SideRail />
    <div class="cl-shell__col">
      <AppBar :health="props.health ?? null" :session="props.session ?? null" :recent-workspace="props.recentWorkspace ?? null" @evidence="emit('evidence')" />
      <main class="cl-shell__main"><slot /></main>
    </div>
    <slot name="drawer" />
  </div>
</template>
<style>
/* 全站焦点可见：WCAG 2.2 AA / COMMON.md「2px 焦点线」。放在非 scoped 块内以覆盖子组件。 */
:where(a, button, input, select, textarea, [tabindex]):focus-visible {
  outline: 2px solid var(--cl-brand-600);
  outline-offset: 1px;
}
</style>
<style scoped>
.cl-shell { display: grid; grid-template-columns: var(--cl-rail-w) minmax(0, 1fr); min-height: 100vh; background: var(--cl-canvas); color: var(--cl-ink-600); font-family: var(--cl-font-sans); }
.cl-shell__col { display: grid; grid-template-rows: auto minmax(0, 1fr); min-width: 0; }
.cl-shell__main { padding: 24px; max-width: var(--cl-content-max); width: 100%; margin: 0 auto; }
/* --cl-bp-rail-collapse */
@media (max-width: 1100px) {
  .cl-shell { grid-template-columns: var(--cl-rail-w-collapsed) minmax(0, 1fr); }
  .cl-shell__main { padding: 16px; }
}
/* --cl-bp-rail-drawer */
@media (max-width: 800px) {
  .cl-shell { grid-template-columns: minmax(0, 1fr); }
}
</style>
