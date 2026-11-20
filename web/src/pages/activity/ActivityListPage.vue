<script setup lang="ts">
/**
 * web/src/pages/activity/ActivityListPage.vue —— UI-02 活动列表（FR-02）
 *
 * 契约真值来源（禁凭记忆 / 禁自造）：
 *   - 路由 `/w/:workspace_id/activities`、operation_ids = listActivities/getActivity/createActivity、
 *     acceptance = AC-002 / AC-032：contracts/pages.json（UI-02 条目）；
 *   - 区域与列序「标题行（右侧新建活动）+ 全宽列表（编号、活动、来源银行、行内编号、当前仿真版本、状态）」：
 *     spec/CampaignLab-SDD-v1.0/ui/UI-02-activity-list.md「页面结构」；
 *   - 过滤项「名称或编号、状态 = listActivities q/status」与新建项「名称、银行编号、行内活动编号、说明 = ActivityCreate」：
 *     同文「字段和绑定」；
 *   - 边界「空列表提供创建 / 已归档活动可检索和查看 / 相同银行行内活动编号重复显示冲突并定位既有记录」：同文「页面状态与边界」；
 *   - 公共规范（12 列、六态、25 行游标、键盘排序、证据抽屉 480px、Esc 回收焦点、缺值 — 与原因）：ui/COMMON.md。
 *
 * 冻结面消费纪律（M0-03-public-components.md §5 / M0-03b-freeze.md）：
 *   - 只用 13 件公共件与 6 件六态件的既有 props/emits/slots，不改一行公共件；
 *   - 首载骨架形状（heading / headCells / cardCount）经 M0-03b-freeze.md §4.2 的**外部注册扩展点**
 *     由同目录 firstLoadVariant.ts 覆写呈现（FU-28：禁给 ViewState 扩 props；而绕开 ViewState 直渲骨架
 *     会丢掉 data-state / role / aria-live / aria-busy 四条非颜色载体 —— AC-032）；
 *   - ViewState 的 context 由本页显式传入（FU-27：公共件禁读路由）；
 *   - store 的 phase 是页面私有词汇，六态是呈现层词汇，映射固定在 features/activity/viewState.ts，本页不发明第三种词汇。
 *
 * 诚实偏差（已在 web/docs/FE-UI-02-activity-list.md 与 FE-TO-DAG-REQUESTS.md 留痕）：
 *   - UI-03 活动详情页未交付 ⇒「行点击进入活动详情」由本页证据抽屉承载，数据一律取 getActivity 原值，不发假路由；
 *   - SideRail 六项导航仍是 aria-disabled 占位（激活导航需改公共件 = CR，见请求 [4]）。
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppShell from "@/components/AppShell.vue";
import PageBar from "@/components/PageBar.vue";
import CardPanel from "@/components/CardPanel.vue";
import DataTable from "@/components/DataTable.vue";
import AlertBanner from "@/components/AlertBanner.vue";
import EvidenceDrawer from "@/components/EvidenceDrawer.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import StatusTag from "@/components/StatusTag.vue";
import MissingValue from "@/components/state/MissingValue.vue";
import ViewState from "@/components/state/ViewState.vue";
import type { ViewStateAction } from "@/components/state/viewState";
import type { TableRow } from "@/components/componentTypes";
import { JSON_BODY_LIMIT_BYTES, jsonBodyBytes, newIdempotencyKey } from "@/api/http";
import type { Activity, ActivityCreate, Workspace } from "@/api/endpoints";
import { ACTIVITY_QUERY_MAX_LENGTH } from "@/api/endpoints";
import { useActivities } from "@/composables/useActivities";
import { useSession } from "@/composables/useSession";
import { useWorkspaceScope } from "@/composables/useWorkspaceScope";
import { useWorkspaces } from "@/composables/useWorkspaces";
import {
  ACTIVITY_COLUMNS,
  ACTIVITY_STATUS_VIEWS,
  MISSING_REASON,
  asCellText,
  asCellValue,
  joinIdsOrNone,
  statusTextOf,
  statusViewOfCode,
  toActivityRow,
  validateActivityDraft,
} from "@/features/activity/presentation";
import { hasActivityFilter, normalizeActivityQuery, normalizeActivityStatus } from "@/features/activity/query";
import { asActivitySortKey, nextActivitySort, sortActivities } from "@/features/activity/sort";
import type { ActivitySortState } from "@/features/activity/sort";
import { activityListViewState, showsPreviousResult } from "@/features/activity/viewState";
import type { ActivityListViewState } from "@/features/activity/viewState";
// 副作用 import：注册 UI-02 首载骨架的 ViewState variant（模块只求值一次，见该文件头注）。
import "./firstLoadVariant";

const PAGE_TITLE = "活动总览";
const CRUMB = "工作区 / 活动与规则 / FR-02";
const NO_RECORD_TITLE = "当前筛选没有活动";
const NO_FILTER_TEXT = "无筛选条件";
/** 合成数据可见标注的缺值原因：UI-02 的三个 operationId 都不返回工作区数据用途字段。 */
const SOURCE_CLASS_UNKNOWN_REASON = "本页接口不含工作区数据用途字段";
const SOURCE_CLASS_LABEL: Record<Workspace["source_class"], string> = {
  SYNTHETIC: "合成数据",
  AUTHORIZED_DEIDENTIFIED: "授权脱敏数据",
};

const route = useRoute();
const router = useRouter();
const session = useSession();
const workspaces = useWorkspaces();
const activities = useActivities();
const scope = useWorkspaceScope();

const evidenceOpen = ref(false);
const createOpen = ref(false);
const confirmOpen = ref(false);
const fieldError = ref("");
/** 一次用户意图一个幂等键；409 重试沿原 key，故失败后不清空。 */
const pendingKey = ref("");
const sort = ref<ActivitySortState>({ key: "id", dir: "asc" });
const draft = reactive({ name: "", bank_id: "", external_activity_id: "", description: "" });
const searchInput = ref("");
const statusInput = ref("");

/* ------------------------------------------------------------------ 路由 → 作用域 */

function paramText(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

function queryText(value: string | null | (string | null)[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

const workspaceId = computed<string | null>(() => {
  const text = paramText(route.params.workspace_id);
  return text.length > 0 ? text : null;
});

const workspace = computed<Workspace | null>(() => {
  const id = workspaceId.value;
  if (id === null) return null;
  return workspaces.state.items.find((item) => item.id === id) ?? null;
});

/** 合成数据可见标注（内容红线）：取值只来自契约 Workspace.source_class，未知就显示 — 与原因。 */
const sourceClassCode = computed<string>(() => workspace.value?.source_class ?? "UNKNOWN");
const sourceClassLabel = computed<string | null>(() => {
  const found = workspace.value;
  return found === null ? null : SOURCE_CLASS_LABEL[found.source_class];
});

const crumb = computed<string>(() => {
  const found = workspace.value;
  return found === null ? CRUMB : CRUMB + " / " + found.name;
});

/* ------------------------------------------------------------------ 六态映射 */

const stateInput = computed(() => ({
  phase: activities.state.phase,
  error: activities.state.error,
  itemCount: activities.state.items.length,
}));
const viewState = computed<ActivityListViewState>(() => activityListViewState(stateInput.value));
const showPrevious = computed<boolean>(() => showsPreviousResult(stateInput.value));
const filtered = computed<boolean>(() => hasActivityFilter(activities.state.q, activities.state.status));

const filterDescription = computed<string>(() => {
  const parts: string[] = [];
  if (activities.state.q.length > 0) parts.push("名称或编号「" + activities.state.q + "」");
  if (activities.state.status.length > 0) {
    const view = statusViewOfCode(activities.state.status);
    parts.push("状态「" + view.label + "（" + view.code + "）」");
  }
  return parts.length === 0 ? NO_FILTER_TEXT : parts.join("；");
});

/** 只有 no-record 需要页面级 title（COMMON.md:28「指明当前筛选」）；其余态一律用冻结文案，不覆盖。 */
const stateTitleProps = computed<Record<string, string>>(() =>
  viewState.value === "no-record" ? { title: NO_RECORD_TITLE + "：" + filterDescription.value } : {},
);

const stateActions = computed<readonly ViewStateAction[]>(() => {
  const state = viewState.value;
  if (state === "no-record") return filtered.value ? ["create", "clear-filter"] : ["create"];
  if (state === "failed" || state === "stale-412") return ["refetch"];
  return [];
});

/** ViewState.context 必须由页面显式传入（FU-27）。UI-02 无 review_id，按契约缺省 null。 */
const viewContext = computed(() => ({
  state: viewState.value ?? "first-load",
  routeName: typeof route.name === "string" ? route.name : null,
  workspaceId: workspaceId.value,
  reviewId: null,
}));

function onStateAction(kind: ViewStateAction): void {
  if (kind === "create") {
    openCreate();
    return;
  }
  if (kind === "clear-filter") {
    void clearFilters();
    return;
  }
  if (kind === "refetch" || kind === "rerun") {
    void reload();
    return;
  }
  // export / import 在 UI-02 无对应契约动作：stateActions 不会给出这两个键（禁自造动作语义）。
}

/* ------------------------------------------------------------------ 表格 */

const rows = computed<readonly TableRow[]>(() =>
  sortActivities(activities.state.items, sort.value).map((item) => toActivityRow(item)),
);

function onSort(key: string): void {
  const parsed = asActivitySortKey(key);
  if (parsed === null) return;
  sort.value = nextActivitySort(sort.value, parsed);
}

/* ------------------------------------------------------------------ 筛选与 URL */

function syncUrl(): void {
  const query: Record<string, string> = {};
  if (activities.state.q.length > 0) query.q = activities.state.q;
  if (activities.state.status.length > 0) query.status = activities.state.status;
  void router.replace({ path: route.path, query });
}

async function applyFilters(rawQ: string, rawStatus: string): Promise<void> {
  const q = normalizeActivityQuery(rawQ);
  const status = normalizeActivityStatus(rawStatus);
  searchInput.value = q;
  statusInput.value = status;
  await activities.setFilters(q, status);
  syncUrl();
}

async function clearFilters(): Promise<void> {
  await applyFilters("", "");
}

async function reload(): Promise<void> {
  await activities.loadFirstPage();
}

/* ------------------------------------------------------------------ 新建活动 */

function openCreate(): void {
  createOpen.value = true;
  fieldError.value = "";
}

function closeCreate(): void {
  createOpen.value = false;
  confirmOpen.value = false;
  fieldError.value = "";
}

function resetDraft(): void {
  draft.name = "";
  draft.bank_id = "";
  draft.external_activity_id = "";
  draft.description = "";
}

/** ActivityCreate 只有 name 必填；其余字段为空则**不出现在正文里**（exactOptionalPropertyTypes + 不伪造 null）。 */
function createBody(): ActivityCreate {
  const bank = draft.bank_id.trim();
  const external = draft.external_activity_id.trim();
  const description = draft.description.trim();
  return {
    name: draft.name.trim(),
    ...(bank.length > 0 ? { bank_id: bank } : {}),
    ...(external.length > 0 ? { external_activity_id: external } : {}),
    ...(description.length > 0 ? { description } : {}),
  };
}

const confirmImpact = computed<string>(() => {
  const body = createBody();
  const parts: string[] = ["名称 " + body.name];
  parts.push("来源银行 " + (body.bank_id ?? "未填写"));
  parts.push("行内活动编号 " + (body.external_activity_id ?? "未填写"));
  parts.push("工作区 " + (workspaceId.value ?? "未绑定"));
  parts.push("确认后只提交一次，重试沿原幂等键");
  return parts.join("；");
});

function askCreate(): void {
  const message = validateActivityDraft(draft);
  fieldError.value = message;
  if (message.length > 0) return;
  if (jsonBodyBytes(createBody()) > JSON_BODY_LIMIT_BYTES) {
    fieldError.value = "说明过长，请求正文超过 1 MiB 上限，未发送";
    return;
  }
  // 幂等键在打开确认框时生成一次；取消后再次提交属新的用户意图，重新生成。
  pendingKey.value = newIdempotencyKey("activity-create");
  confirmOpen.value = true;
}

async function submitCreate(): Promise<void> {
  confirmOpen.value = false;
  if (pendingKey.value.length === 0) {
    fieldError.value = "缺少幂等键，未发送";
    return;
  }
  const result = await activities.create(createBody(), pendingKey.value);
  if (!result.ok) {
    // 保留本地输入（COMMON.md:31）；409 的定位既有记录由 store 完成，页面只呈现说明。
    fieldError.value = "";
    return;
  }
  const created: Activity = result.data;
  resetDraft();
  createOpen.value = false;
  pendingKey.value = "";
  // 「创建成功进入详情」：UI-03 未交付，用本页抽屉承载 getActivity 原值（不发假路由）。
  await activities.openDetail(created.id);
}

/* ------------------------------------------------------------------ 详情抽屉 */

const detailOpen = computed<boolean>(
  () => activities.state.detail !== null || activities.state.detailLoading || activities.state.detailError !== null,
);
const detail = computed<Activity | null>(() => activities.state.detail);

async function openDetail(activityId: string): Promise<void> {
  if (activityId.length === 0) return;
  await activities.openDetail(activityId);
}

function closeDetail(): void {
  activities.closeDetail();
}

function closeEvidence(): void {
  evidenceOpen.value = false;
}

/* ------------------------------------------------------------------ 生命周期 */

async function bindWorkspace(): Promise<void> {
  activities.setWorkspace(workspaceId.value);
  await applyFilters(queryText(route.query.q), queryText(route.query.status));
}

watch(
  () => [workspaceId.value, queryText(route.query.q), queryText(route.query.status)] as const,
  (next, prev) => {
    if (prev === undefined) return;
    if (next[0] !== prev[0]) {
      void bindWorkspace();
      return;
    }
    const q = normalizeActivityQuery(next[1]);
    const status = normalizeActivityStatus(next[2]);
    if (q === activities.state.q && status === activities.state.status) return;
    void applyFilters(q, status);
  },
);

onMounted(() => {
  void bindWorkspace();
});

onBeforeUnmount(() => {
  // 路由离开释放本页持有的抽屉与在飞详情请求（FRONTEND.md：路由离开后释放图表与轮询定时器）。
  closeDetail();
  scope.register("listener", "ui-02:unmounted", () => undefined)();
});
</script>

<template>
  <AppShell
    :health="workspaces.state.health ?? undefined"
    :session="session.state.session ?? undefined"
    :recent-workspace="workspace?.name ?? null"
    @evidence="evidenceOpen = true"
  >
    <PageBar :title="PAGE_TITLE" :crumb="crumb">
      <template #meta>
        <span class="cl-chip" data-part="source-class" :data-source-class="sourceClassCode">
          <MissingValue :value="sourceClassLabel" :reason="SOURCE_CLASS_UNKNOWN_REASON" />
        </span>
        <StatusTag :label="'列表 ' + activities.state.phase" />
        <StatusTag :label="'会话 ' + session.state.phase" :tone="session.state.phase === 'active' ? 'OK' : 'NEUTRAL'" />
        <span v-if="activities.state.nextCursor !== null" class="cl-note">还有更多（服务器游标）</span>
        <button type="button" class="cl-btn cl-btn--primary" @click="openCreate">新建活动</button>
      </template>
    </PageBar>

    <AlertBanner :error="activities.state.error" />

    <div class="cl-stack">
      <CardPanel v-if="createOpen" title="新建活动" subtitle="名称必填；来源银行与行内活动编号须成对填写">
        <div class="cl-create">
          <label class="cl-field" for="cl-activity-name">名称
            <input id="cl-activity-name" v-model="draft.name" type="text" maxlength="120" aria-required="true" />
          </label>
          <label class="cl-field" for="cl-activity-bank">来源银行编号
            <input id="cl-activity-bank" v-model="draft.bank_id" type="text" maxlength="96" />
          </label>
          <label class="cl-field" for="cl-activity-external">行内活动编号
            <input id="cl-activity-external" v-model="draft.external_activity_id" type="text" maxlength="96" />
          </label>
          <label class="cl-field" for="cl-activity-desc">说明
            <textarea id="cl-activity-desc" v-model="draft.description" rows="3" maxlength="1000" />
          </label>
        </div>
        <p v-if="fieldError.length > 0" class="cl-field-error" data-part="field-error">{{ fieldError }}</p>
        <p v-if="activities.state.locatedExternalId !== null" class="cl-locate" data-part="locate">
          创建未成功：已按行内活动编号「{{ activities.state.locatedExternalId }}」检索既有记录
        </p>
        <AlertBanner :error="activities.state.createError" />
        <div class="cl-actions">
          <button type="button" class="cl-btn" @click="closeCreate">取消</button>
          <button
            v-if="activities.state.createError !== null && activities.state.createError.status === 409"
            type="button"
            class="cl-btn"
            data-part="retry-same-key"
            :disabled="activities.state.creating"
            @click="submitCreate"
          >沿原幂等键重试</button>
          <button
            type="button"
            class="cl-btn cl-btn--primary"
            :disabled="activities.state.creating"
            @click="askCreate"
          >提交新建</button>
        </div>
        <template #footer>
          <span class="cl-note">请求正文上限 1 MiB；幂等键长度 8..128，由前端生成并可在证据抽屉回查。</span>
        </template>
      </CardPanel>

      <CardPanel title="活动列表" subtitle="编号、活动、来源银行、行内编号、当前仿真版本、状态（服务端原值）">
        <template #actions>
          <input
            v-model="searchInput"
            class="cl-search"
            type="search"
            :maxlength="ACTIVITY_QUERY_MAX_LENGTH"
            aria-label="按名称或编号搜索活动"
            @keyup.enter="applyFilters(searchInput, statusInput)"
          />
          <select v-model="statusInput" class="cl-search" aria-label="按状态筛选活动" @change="applyFilters(searchInput, statusInput)">
            <option value="">全部状态</option>
            <option v-for="view in ACTIVITY_STATUS_VIEWS" :key="view.code" :value="view.code">
              {{ view.label }}（{{ view.code }}）
            </option>
          </select>
          <button type="button" class="cl-btn" @click="applyFilters(searchInput, statusInput)">筛选</button>
          <button type="button" class="cl-btn" @click="reload">刷新</button>
        </template>

        <ViewState
          v-if="viewState !== null"
          :state="viewState"
          :error="activities.state.error"
          v-bind="stateTitleProps"
          :actions="stateActions"
          :show-previous="showPrevious"
          :keep-input="viewState === 'stale-412'"
          :context="viewContext"
          @action="onStateAction"
        />

        <template v-else>
          <p v-if="showPrevious" class="cl-previous" data-part="previous">上一结果</p>
          <DataTable
            :columns="ACTIVITY_COLUMNS"
            :rows="rows"
            :sort-key="sort.key"
            :sort-dir="sort.dir"
            caption="活动"
            @sort="onSort"
          >
            <template #cell-id="{ row }">
              <button
                type="button"
                class="cl-link"
                :aria-label="'查看活动 ' + asCellText(row.id)"
                @click="openDetail(asCellText(row.id))"
              >{{ asCellText(row.id) }}</button>
            </template>
            <template #cell-bank_id="{ row }">
              <MissingValue :value="asCellValue(row.bank_id)" :reason="MISSING_REASON.bank_id" mono />
            </template>
            <template #cell-external_activity_id="{ row }">
              <MissingValue :value="asCellValue(row.external_activity_id)" :reason="MISSING_REASON.external_activity_id" mono />
            </template>
            <template #cell-current_rule_id="{ row }">
              <MissingValue :value="asCellValue(row.current_rule_id)" :reason="MISSING_REASON.current_rule_id" mono />
            </template>
            <template #cell-status="{ row }">
              <span class="cl-status" :data-status="asCellText(row.status)">
                <StatusTag
                  :label="statusViewOfCode(asCellText(row.status)).label"
                  :tone="statusViewOfCode(asCellText(row.status)).tone"
                />
              </span>
            </template>
          </DataTable>
        </template>

        <template #footer>
          <button v-if="activities.state.nextCursor !== null" type="button" class="cl-btn" @click="activities.loadMore()">
            加载更多
          </button>
          <span v-else class="cl-note">
            已加载 {{ activities.state.items.length }} 行（默认 25 行，服务器游标加载）
          </span>
          <span class="cl-note">已归档活动可检索和查看；行内编号点击进入本页详情抽屉（UI-03 详情页未交付）。</span>
        </template>
      </CardPanel>
    </div>

    <EvidenceDrawer :open="detailOpen" title="活动详情" @close="closeDetail">
      <AlertBanner :error="activities.state.detailError" />
      <p v-if="activities.state.detailLoading" class="cl-note" data-part="detail-loading">正在获取活动原值…</p>
      <dl v-if="detail !== null" class="cl-detail" data-part="detail">
        <dt class="cl-detail__k">编号</dt>
        <dd class="cl-detail__v" data-field="id">{{ detail.id }}</dd>
        <dt class="cl-detail__k">修订号</dt>
        <dd class="cl-detail__v" data-field="revision">{{ detail.revision }}</dd>
        <dt class="cl-detail__k">创建时间</dt>
        <dd class="cl-detail__v" data-field="created_at">{{ detail.created_at }}</dd>
        <dt class="cl-detail__k">活动</dt>
        <dd class="cl-detail__v" data-field="name">{{ detail.name }}</dd>
        <dt class="cl-detail__k">来源银行</dt>
        <dd class="cl-detail__v" data-field="bank_id">
          <MissingValue :value="detail.bank_id" :reason="MISSING_REASON.bank_id" mono />
        </dd>
        <dt class="cl-detail__k">行内活动编号</dt>
        <dd class="cl-detail__v" data-field="external_activity_id">
          <MissingValue :value="detail.external_activity_id" :reason="MISSING_REASON.external_activity_id" mono />
        </dd>
        <dt class="cl-detail__k">说明</dt>
        <dd class="cl-detail__v" data-field="description">
          <MissingValue :value="detail.description" reason="服务端返回空说明" />
        </dd>
        <dt class="cl-detail__k">状态</dt>
        <dd class="cl-detail__v" data-field="status">
          <span class="cl-status" :data-status="detail.status">
            <StatusTag :label="statusViewOfCode(detail.status).label" :tone="statusViewOfCode(detail.status).tone" />
            <span class="cl-note">{{ statusTextOf(detail.status) }}</span>
          </span>
        </dd>
        <dt class="cl-detail__k">当前仿真版本</dt>
        <dd class="cl-detail__v" data-field="current_rule_id">
          <MissingValue :value="detail.current_rule_id" :reason="MISSING_REASON.current_rule_id" mono />
        </dd>
        <dt class="cl-detail__k">策略绑定</dt>
        <dd class="cl-detail__v" data-field="bindings">
          <ul v-if="detail.bindings.length > 0" class="cl-binding">
            <li v-for="binding in detail.bindings" :key="binding.strategy_id + binding.source_version" class="cl-binding__item">
              {{ binding.strategy_id }} / {{ binding.source_version }} / {{ binding.valid_from }} 起至 {{ binding.valid_until }} 止 / 证据 {{ binding.evidence_id }}
            </li>
          </ul>
          <MissingValue v-else :value="null" reason="服务端未返回绑定" />
        </dd>
        <dt class="cl-detail__k">规则版本</dt>
        <dd class="cl-detail__v" data-field="rule_ids">
          <MissingValue :value="joinIdsOrNone(detail.rule_ids)" reason="服务端未返回规则版本" mono />
        </dd>
        <dt class="cl-detail__k">回执</dt>
        <dd class="cl-detail__v" data-field="receipt_ids">
          <MissingValue :value="joinIdsOrNone(detail.receipt_ids)" reason="服务端未返回回执" mono />
        </dd>
      </dl>
    </EvidenceDrawer>

    <template #drawer>
      <EvidenceDrawer :open="evidenceOpen" title="证据" @close="closeEvidence">
        <dl class="cl-detail">
          <dt class="cl-detail__k">页面契约</dt>
          <dd class="cl-detail__v">UI-02 / FR-02 / AC-002、AC-032</dd>
          <dt class="cl-detail__k">operationId</dt>
          <dd class="cl-detail__v">listActivities、getActivity、createActivity</dd>
          <dt class="cl-detail__k">工作区作用域</dt>
          <dd class="cl-detail__v">
            {{ scope.state.workspaceId ?? '—' }} / epoch {{ scope.state.epoch }} / 资源 {{ scope.list().length }} 项 / 最近清场 {{ scope.state.lastClearReason ?? '—' }}
          </dd>
          <dt class="cl-detail__k">request_id</dt>
          <dd class="cl-detail__v">{{ activities.state.lastRequestId ?? session.state.lastRequestId ?? '—' }}</dd>
          <dt class="cl-detail__k">幂等键</dt>
          <dd class="cl-detail__v">{{ pendingKey.length > 0 ? pendingKey : '—' }}</dd>
          <dt class="cl-detail__k">当前筛选</dt>
          <dd class="cl-detail__v">{{ filterDescription }}</dd>
          <dt class="cl-detail__k">待跳转深链</dt>
          <dd class="cl-detail__v">{{ session.state.pendingRedirect ?? '—' }}</dd>
        </dl>
      </EvidenceDrawer>
    </template>

    <ConfirmDialog
      :open="confirmOpen"
      summary="新建活动"
      :impact="confirmImpact"
      confirm-label="确认新建"
      @confirm="submitCreate"
      @cancel="confirmOpen = false"
    />
  </AppShell>
</template>

<style scoped>
.cl-stack { display: grid; gap: var(--cl-space-4); align-content: start; min-width: 0; }
.cl-chip { display: inline-flex; align-items: center; gap: var(--cl-space-1); height: 20px; padding: 0 8px; border: 1px dashed var(--cl-line); border-radius: var(--cl-radius-sm); background: var(--cl-canvas); }
.cl-note { font-size: var(--cl-fs-label); color: var(--cl-ink-500); }
.cl-search { height: var(--cl-btn-h); padding: 0 8px; border: 1px solid var(--cl-line); border-radius: var(--cl-radius-sm); font: inherit; color: var(--cl-ink-700); background: var(--cl-card); }
.cl-btn { height: var(--cl-btn-h); padding: 0 16px; border: 1px solid var(--cl-line); border-radius: var(--cl-radius-sm); background: var(--cl-card); color: var(--cl-ink-700); font: inherit; }
.cl-btn:disabled { color: var(--cl-ink-500); background: var(--cl-canvas); }
.cl-btn--primary { border-color: var(--cl-brand-600); background: var(--cl-brand-600); color: var(--cl-card); }
.cl-link { border: 0; background: transparent; color: var(--cl-brand-600); text-decoration: underline; font: inherit; font-family: var(--cl-font-mono); }
.cl-actions { display: flex; gap: var(--cl-space-2); justify-content: flex-end; margin-top: var(--cl-space-3); }
.cl-create { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--cl-space-3); }
.cl-field { display: grid; gap: var(--cl-space-1); font-size: var(--cl-fs-label); color: var(--cl-ink-600); min-width: 0; }
.cl-field input, .cl-field textarea { border: 1px solid var(--cl-line); border-radius: var(--cl-radius-sm); padding: 8px; font: inherit; background: var(--cl-card); color: var(--cl-ink-700); min-width: 0; }
.cl-field-error { margin: var(--cl-space-2) 0 0; color: var(--cl-danger-text); font-size: var(--cl-fs-label); }
.cl-locate { margin: var(--cl-space-2) 0 0; color: var(--cl-warn-text); font-size: var(--cl-fs-label); }
.cl-previous { margin: 0 0 var(--cl-space-2); font-size: var(--cl-fs-label); color: var(--cl-ink-600); border: 1px solid var(--cl-line); border-radius: var(--cl-radius-sm); padding: 2px 8px; display: inline-block; }
.cl-status { display: inline-flex; align-items: center; gap: var(--cl-space-1); }
.cl-detail { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: var(--cl-space-1) var(--cl-space-3); margin: 0; }
.cl-detail__k { color: var(--cl-ink-500); }
.cl-detail__v { margin: 0; color: var(--cl-ink-700); overflow-wrap: anywhere; }
.cl-binding { margin: 0; padding-left: var(--cl-space-4); display: grid; gap: var(--cl-space-1); }
.cl-binding__item { overflow-wrap: anywhere; }
</style>
