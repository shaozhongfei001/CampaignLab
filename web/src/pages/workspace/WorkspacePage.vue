<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppShell from "@/components/AppShell.vue";
import PageBar from "@/components/PageBar.vue";
import PageGrid from "@/components/PageGrid.vue";
import CardPanel from "@/components/CardPanel.vue";
import DataTable from "@/components/DataTable.vue";
import AlertBanner from "@/components/AlertBanner.vue";
import EmptyState from "@/components/EmptyState.vue";
import EvidenceDrawer from "@/components/EvidenceDrawer.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import StatusTag from "@/components/StatusTag.vue";
import type { TableColumn, TableRow } from "@/components/componentTypes";
import { jsonBodyBytes, JSON_BODY_LIMIT_BYTES, newIdempotencyKey } from "@/api/http";
import type { Workspace, WorkspaceCreate } from "@/api/endpoints";
import { useSession } from "@/composables/useSession";
import { useWorkspaces } from "@/composables/useWorkspaces";
import { useWorkspaceScope } from "@/composables/useWorkspaceScope";
import { normalizeWorkspaceQuery } from "@/features/workspace/query";
import { nextSort, sortWorkspaces, type SortState } from "@/features/workspace/sort";

const session = useSession();
const workspaces = useWorkspaces();
const scope = useWorkspaceScope();
const route = useRoute();
const router = useRouter();

const entryToken = ref(typeof route.query.token === "string" ? route.query.token : "");
const draft = reactive({ name: "", source_class: "SYNTHETIC" as Workspace["source_class"], authorization_note: "" });
const sort = ref<SortState>({ key: "created_at", dir: "desc" });
const evidenceOpen = ref(false);
const confirmOpen = ref(false);
const fieldError = ref<string>("");
const searchInput = ref<string>(normalizeWorkspaceQuery(String(route.query.q ?? "")));

const COLUMNS: readonly TableColumn[] = [
  { key: "name", label: "名称", sortable: true },
  { key: "source_class", label: "数据用途", sortable: true },
  { key: "created_at", label: "创建时间", sortable: true, mono: true },
  { key: "action", label: "操作" },
];

const rows = computed<readonly TableRow[]>(() =>
  sortWorkspaces(workspaces.state.items, sort.value).map((w) => ({
    id: w.id,
    name: w.name,
    source_class: w.source_class === "SYNTHETIC" ? "合成" : "授权脱敏",
    created_at: w.created_at,
    action: "",
  })),
);
const selected = computed<Workspace | null>(
  () => workspaces.state.items.find((w) => w.id === workspaces.state.selectedId) ?? null,
);

function onSort(key: string): void {
  sort.value = nextSort(sort.value, key as SortState["key"]);
}

async function enterWorkbench(): Promise<void> {
  fieldError.value = "";
  await session.bootstrap(entryToken.value.length > 0 ? entryToken.value : null);
  await refresh();
}

async function refresh(): Promise<void> {
  await Promise.all([workspaces.refreshHealth(), workspaces.loadFirstPage()]);
  const q = normalizeWorkspaceQuery(String(route.query.q ?? ""));
  if (q.length > 0 && q !== workspaces.state.q) await workspaces.setQuery(q);
}

function submitSearch(): void {
  const q = normalizeWorkspaceQuery(searchInput.value);
  searchInput.value = q;
  void router.replace({ path: "/", query: q.length > 0 ? { q } : {} });
  void workspaces.setQuery(q);
}

function validateDraft(): string {
  if (draft.name.trim().length === 0) return "名称必填";
  if (draft.source_class === "AUTHORIZED_DEIDENTIFIED" && draft.authorization_note.trim().length === 0) {
    return "授权脱敏须填写授权依据";
  }
  return "";
}

function askCreate(): void {
  const message = validateDraft();
  fieldError.value = message;
  if (message.length > 0) return;
  if (jsonBodyBytes(createBody()) > JSON_BODY_LIMIT_BYTES) {
    fieldError.value = "授权依据过长，请求正文超过 1 MiB 上限，未发送";
    return;
  }
  confirmOpen.value = true;
}

function createBody(): WorkspaceCreate {
  return {
    name: draft.name.trim(),
    source_class: draft.source_class,
    authorization_note: draft.authorization_note.trim().length > 0 ? draft.authorization_note.trim() : null,
  };
}

async function confirmCreate(): Promise<void> {
  confirmOpen.value = false;
  const result = await workspaces.create(createBody(), newIdempotencyKey("workspace-create"));
  if (result.ok) {
    draft.name = "";
    draft.authorization_note = "";
    workspaces.select(result.data.id);
    void router.push("/workspaces/" + result.data.id);
  }
}

function choose(id: string): void {
  workspaces.select(id);
  void router.push("/workspaces/" + id);
}

function focusCreateName(): void {
  document.getElementById("cl-create-name")?.focus();
}

function closeEvidence(): void {
  evidenceOpen.value = false;
}

onMounted(() => {
  void refresh();
});
</script>

<template>
  <AppShell :health="workspaces.state.health ?? undefined" :session="session.state.session ?? undefined" :recent-workspace="selected?.name ?? null" @evidence="evidenceOpen = true">
    <PageBar title="工作区与首次进入" crumb="入口 / FR-01">
      <template #meta>
        <StatusTag :label="'phase ' + workspaces.state.phase" />
        <StatusTag :label="'会话 ' + session.state.phase" :tone="session.state.phase === 'active' ? 'OK' : 'NEUTRAL'" />
        <span v-if="workspaces.state.nextCursor !== null">还有更多（服务器游标）</span>
      </template>
    </PageBar>

    <AlertBanner :error="workspaces.state.error" :note="workspaces.state.workerRestricted ? 'worker 离线，作业受限' : undefined" />

    <PageGrid>
      <CardPanel title="工作区列表" subtitle="名称、数据用途、创建时间（服务端原值）">
        <template #actions>
          <input v-model="searchInput" class="cl-search" type="search" aria-label="按名称搜索工作区" @keyup.enter="submitSearch" />
          <button type="button" class="cl-btn" @click="submitSearch">搜索</button>
          <button type="button" class="cl-btn" @click="refresh">刷新</button>
        </template>
        <EmptyState
          v-if="workspaces.state.phase === 'empty'"
          title="当前筛选没有工作区"
          hint="无工作区时请优先创建；授权脱敏须在操作记录填来源授权，工作区类型创建后固定。"
          action-label="新建工作区"
          @action="focusCreateName"
        />
        <DataTable v-else :columns="COLUMNS" :rows="rows" :sort-key="sort.key" :sort-dir="sort.dir" caption="工作区" @sort="onSort">
          <template #cell-action="{ row }">
            <button type="button" class="cl-link" @click="choose(String(row.id))">进入</button>
          </template>
        </DataTable>
        <template #footer>
          <button v-if="workspaces.state.nextCursor !== null" type="button" class="cl-btn" @click="workspaces.loadMore()">加载更多</button>
          <span v-else>已加载 {{ workspaces.state.items.length }} 行（默认 25 行，服务器游标加载）</span>
        </template>
      </CardPanel>

      <template #side>
        <CardPanel title="首跑路线" subtitle="两条业务流程入口">
          <ol class="cl-routes">
            <li>活动与规则 → 导入 → 仿真（UI-02 / UI-06）</li>
            <li>作业与证据 → 作业状态与恢复（UI-25）</li>
          </ol>
          <button type="button" class="cl-btn cl-btn--primary" @click="enterWorkbench">进入本机工作台</button>
          <input v-model="entryToken" class="cl-search" type="text" aria-label="入口令牌（仅首次使用）" />
        </CardPanel>

        <CardPanel title="新建工作区" subtitle="名称必填；数据用途创建后固定">
          <label class="cl-field" for="cl-create-name">名称
            <input id="cl-create-name" v-model="draft.name" type="text" aria-required="true" />
          </label>
          <fieldset class="cl-field">
            <legend>数据用途</legend>
            <label><input v-model="draft.source_class" type="radio" value="SYNTHETIC" /> 合成</label>
            <label><input v-model="draft.source_class" type="radio" value="AUTHORIZED_DEIDENTIFIED" /> 授权脱敏</label>
          </fieldset>
          <label v-if="draft.source_class === 'AUTHORIZED_DEIDENTIFIED'" class="cl-field" for="cl-create-note">授权依据
            <textarea id="cl-create-note" v-model="draft.authorization_note" rows="3" />
          </label>
          <p v-if="fieldError.length > 0" class="cl-field-error">{{ fieldError }}</p>
          <AlertBanner :error="workspaces.state.createError" />
          <template #actions>
            <button type="button" class="cl-btn cl-btn--primary" :disabled="workspaces.state.creating" @click="askCreate">新建工作区</button>
          </template>
        </CardPanel>
      </template>
    </PageGrid>

    <template #drawer>
      <EvidenceDrawer :open="evidenceOpen" title="证据" @close="closeEvidence">
        <dl class="cl-evidence">
          <dt>工作区作用域</dt><dd>{{ scope.state.workspaceId ?? '—' }} / epoch {{ scope.state.epoch }} / 资源 {{ scope.list().length }} 项 / 最近清场 {{ scope.state.lastClearReason ?? '—' }}</dd>
          <dt>request_id</dt><dd>{{ workspaces.state.lastRequestId ?? session.state.lastRequestId ?? '—' }}</dd>
          <dt>Health</dt><dd>{{ JSON.stringify(workspaces.state.health) }}</dd>
          <dt>待跳转深链</dt><dd>{{ session.state.pendingRedirect ?? '—' }}</dd>
        </dl>
      </EvidenceDrawer>
    </template>

    <ConfirmDialog
      :open="confirmOpen"
      summary="新建工作区"
      :impact="'名称 ' + draft.name.trim() + '；数据用途 ' + (draft.source_class === 'SYNTHETIC' ? '合成' : '授权脱敏') + '；确认后只提交一次，重试沿原幂等键。'"
      @confirm="confirmCreate"
      @cancel="confirmOpen = false"
    />
  </AppShell>
</template>

<style scoped>
.cl-search { height: var(--cl-btn-h); padding: 0 8px; border: 1px solid var(--cl-line); border-radius: var(--cl-radius-sm); font: inherit; color: var(--cl-ink-700); background: var(--cl-card); }
.cl-btn { height: var(--cl-btn-h); padding: 0 16px; border: 1px solid var(--cl-line); border-radius: var(--cl-radius-sm); background: var(--cl-card); color: var(--cl-ink-700); font: inherit; }
.cl-btn--primary { border-color: var(--cl-brand-600); background: var(--cl-brand-600); color: var(--cl-card); }
.cl-link { border: 0; background: transparent; color: var(--cl-brand-600); text-decoration: underline; font: inherit; }
.cl-field { display: grid; gap: 4px; margin-bottom: 12px; font-size: 13px; color: var(--cl-ink-600); }
.cl-field input[type='text'], .cl-field textarea { border: 1px solid var(--cl-line); border-radius: var(--cl-radius-sm); padding: 8px; font: inherit; background: var(--cl-card); color: var(--cl-ink-700); }
.cl-field-error { margin: 0 0 8px; color: var(--cl-danger-text); font-size: 13px; }
.cl-routes { margin: 0 0 12px; padding-left: 20px; font-size: 13px; color: var(--cl-ink-600); display: grid; gap: 4px; }
.cl-evidence { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; margin: 0; font-size: 13px; }
.cl-evidence dt { color: var(--cl-ink-500); }
.cl-evidence dd { margin: 0; font-family: var(--cl-font-mono); color: var(--cl-ink-700); overflow-wrap: anywhere; }
</style>
