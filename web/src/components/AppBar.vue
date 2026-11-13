<script setup lang="ts">
import StatusTag from "./StatusTag.vue";
import type { Health } from "@/api/endpoints";
import type { Session } from "@/api/endpoints";
const props = defineProps<{ health: Health | null; session: Session | null; recentWorkspace: string | null }>();
const emit = defineEmits<{ evidence: [] }>();
</script>
<template>
  <header class="cl-appbar">
    <div class="cl-appbar__left">
      <StatusTag :label="props.health === null ? '状态未知' : props.health.status" :tone="props.health === null ? 'NEUTRAL' : props.health.status === 'READY' ? 'OK' : 'WARN'" />
      <StatusTag v-if="props.health !== null && props.health.worker === 'OFFLINE'" label="作业受限" tone="DANGER" />
      <span class="cl-appbar__ver">{{ props.health === null ? '—' : props.health.app_version + ' / 契约 ' + props.health.contract_version }}</span>
    </div>
    <div class="cl-appbar__right">
      <span class="cl-appbar__actor">操作者 {{ props.session?.actor_name ?? '未登录' }}</span>
      <span class="cl-appbar__recent">最近工作区 {{ props.recentWorkspace ?? '—' }}</span>
      <button type="button" class="cl-appbar__evidence" @click="emit('evidence')">证据</button>
    </div>
  </header>
</template>
<style scoped>
.cl-appbar { height: var(--cl-topbar-h); display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 0 24px; border-bottom: 1px solid var(--cl-line); background: var(--cl-card); }
.cl-appbar__left, .cl-appbar__right { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--cl-ink-500); }
.cl-appbar__ver { font-family: var(--cl-font-mono); }
.cl-appbar__evidence { height: var(--cl-btn-h-sm); padding: 0 12px; border: 1px solid var(--cl-brand-600); border-radius: var(--cl-radius-sm); background: var(--cl-card); color: var(--cl-brand-600); }
</style>
