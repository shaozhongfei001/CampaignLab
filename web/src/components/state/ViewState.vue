<script setup lang="ts">
/**
 * web/src/components/state/ViewState.vue —— 六态调度件（M0-03b / S3）
 *
 * 签名冻结源：M0-03b-freeze.md §3.4（props / emits / slots / 不变量）。非颜色四载体见 §1.3：
 * 文案 + data-state + role 二分 + data-action。**不引入图标字形依赖**（F-D：StatusTag 五 tone 同形，
 * 不得把 tone 当唯一区分手段）。
 *
 * 组合而非改写（§2）：
 *   - F-2 failed / stale-412 渲染 AlertBanner（原址 import，未迁移、未改一行）；
 *          no-record / partial-comparable / pending-fill 渲染 EmptyState；first-load 渲染 FirstLoadSkeleton。
 *   - F-3 不复制两件的结构或样式，只 import 复用。
 *   - F-4 文案优先级 props > variant.copy > copyOf(state)，本件不自编措辞；动作键的可见名称与
 *          「上一结果」徽标一律取 ui/COMMON.md 原文子串（:28 / :30 / :32 / :29），
 *          由 S2 对磁盘原文做子串校验（回报 S3-4）。
 *   - A137 无数据获取副作用：api/** 只做 type-only import（编译期擦除，无运行时模块边）；
 *          不 fetch、不 axios；state 为必填 prop，触发值全部由页面显式传入（F-A 组件不猜）。
 *   - 动作区由本件自行渲染（不走 EmptyState 的单 actionLabel）：每个动作必须带 data-action（§3.4），
 *          而 EmptyState 的签名里没有这个位置，且其 props 属 M0-03 冻结面（本卡禁改）。
 *
 * 回报口径：
 *   - S3-1 context 默认值「由当前路由推导」需要 vue-router 依赖，与 A137「触发值由页面显式传入」冲突，
 *          故未给 context 时三字段一律 null（不猜路由），由页面显式传入以启用 variant。
 *   - S3-3 首载骨架的形状（标题/表头/卡片数量）不在 §3.4 的 props 面内，故本件渲染默认骨架，
 *          页面若需具体骨架请直接用导出的 FirstLoadSkeleton 或经 variant.render 覆写。
 */
import { computed } from "vue";
import type { ApiError } from "@/api/http";
import AlertBanner from "@/components/AlertBanner.vue";
import EmptyState from "@/components/EmptyState.vue";
import FirstLoadSkeleton from "./FirstLoadSkeleton.vue";
import MissingValue from "./MissingValue.vue";
import { resolveVariants } from "./registry";
import type { ViewStateContext } from "./registry";
import { actionsOf, copyOf, pushViewStateNotice } from "./viewState";
import type { ViewStateAction, ViewStateKind } from "./viewState";

const props = defineProps<{
  state: ViewStateKind;
  error?: ApiError | null;
  title?: string | undefined;
  hint?: string | undefined;
  actions?: readonly ViewStateAction[] | undefined;
  missing?: readonly string[] | undefined;
  reason?: string | undefined;
  showPrevious?: boolean | undefined;
  keepInput?: boolean | undefined;
  context?: ViewStateContext | undefined;
}>();

const emit = defineEmits<{ action: [kind: ViewStateAction] }>();

/** 动作键的可见名称：逐字取 ui/COMMON.md 原文子串（:38「图标按钮须有名称」）。 */
const ACTION_NAMES: Record<ViewStateAction, string> = {
  create: "创建",
  import: "导入",
  "clear-filter": "清空筛选",
  export: "导出",
  refetch: "重新获取",
  rerun: "复跑",
};

/** ui/COMMON.md:29 的「上一结果」标识原文子串。 */
const PREVIOUS_BADGE = "上一结果";

const ERROR_STATES: readonly ViewStateKind[] = ["failed", "stale-412"];
const MISSING_STATES: readonly ViewStateKind[] = ["partial-comparable", "pending-fill"];

const error = computed<ApiError | null>(() => props.error ?? null);
const showPrevious = computed<boolean>(() => props.showPrevious === true);
const keepInput = computed<boolean>(() => props.keepInput === true);
const isErrorState = computed<boolean>(() => ERROR_STATES.includes(props.state));
const isMissingState = computed<boolean>(() => MISSING_STATES.includes(props.state));

const context = computed<ViewStateContext>(
  () => props.context ?? { state: props.state, routeName: null, workspaceId: null, reviewId: null },
);

/** R-2：取最后一个命中的 variant 生效（后注册者可细化前者）。 */
const variant = computed(() => resolveVariants(context.value).at(-1));

const baseCopy = computed(() => copyOf(props.state));

const resolvedTitle = computed<string>(
  () => props.title ?? variant.value?.copy?.[props.state]?.title ?? baseCopy.value.title,
);

const resolvedHint = computed<string>(
  () => props.hint ?? variant.value?.copy?.[props.state]?.hint ?? baseCopy.value.hint,
);

const resolvedActions = computed<readonly ViewStateAction[]>(() => {
  const own = props.actions ?? actionsOf(props.state);
  const extra = variant.value?.extraActions?.[props.state] ?? [];
  const out: ViewStateAction[] = [...own];
  for (const action of extra) {
    if (!out.includes(action)) out.push(action);
  }
  return out;
});

/** 缺项区只在两态出现（§3.4：missing 仅 partial-comparable / pending-fill 使用）。 */
const missingRows = computed<readonly string[]>(() => (isMissingState.value ? (props.missing ?? []) : []));

const role = computed<string>(() => (isErrorState.value ? "alert" : "status"));
const ariaLive = computed<"polite" | undefined>(() => (isErrorState.value ? undefined : "polite"));
const ariaBusy = computed<"true" | undefined>(() => (props.state === "first-load" ? "true" : undefined));

/** 骨架态不出字（§1.3 首载行「无文案」）：标题与提示一律不渲染。 */
const showCopy = computed<boolean>(() => props.state !== "first-load");

const overrideRender = computed(() => variant.value?.render);

/** 替换呈现时可透传的解析结果（variant 必须自行满足 §1.3 的四条非颜色载体，S2 用同一矩阵复跑）。 */
const overrideProps = computed<Record<string, unknown>>(() => ({
  state: props.state,
  // 骨架态不出字：覆写呈现同样不得拿到文案串（§1.3 首载行）。
  title: showCopy.value ? resolvedTitle.value : "",
  hint: showCopy.value ? resolvedHint.value : "",
  error: error.value,
  actions: resolvedActions.value,
  missing: missingRows.value,
  reason: props.reason,
  showPrevious: showPrevious.value,
  keepInput: keepInput.value,
}));

/** §3.4 dev 断言：错误态缺 error 时在根元素留机器可读标记并进水槽（no-console=error，禁 console）。 */
const devAssert = computed<string | undefined>(() => {
  if (isErrorState.value && error.value === null) {
    pushViewStateNotice("ViewState", "error-required", 'state="' + props.state + '" requires a non-null error');
    return "error-required";
  }
  return undefined;
});
</script>

<template>
  <section
    class="cl-view-state"
    :data-state="props.state"
    :data-show-previous="showPrevious ? 'true' : undefined"
    :data-keep-input="keepInput ? 'true' : undefined"
    :data-dev-assert="devAssert"
    :role="role"
    :aria-live="ariaLive"
    :aria-busy="ariaBusy"
  >
    <component v-if="overrideRender !== undefined" :is="overrideRender" v-bind="overrideProps" />

    <template v-else>
      <p v-if="showCopy && props.title !== undefined" class="cl-view-state__custom-title" data-part="custom-title">
        {{ props.title }}
      </p>

      <FirstLoadSkeleton v-if="props.state === 'first-load'" />
      <AlertBanner v-else-if="isErrorState" :error="error" :note="resolvedHint" />
      <EmptyState v-else :title="resolvedTitle" :hint="resolvedHint" />

      <p v-if="showPrevious" class="cl-view-state__previous" data-part="previous">{{ PREVIOUS_BADGE }}</p>

      <ul v-if="missingRows.length > 0" class="cl-view-state__missing" data-part="missing">
        <li v-for="item in missingRows" :key="item" class="cl-view-state__missing-item" data-part="missing-item">
          <span class="cl-view-state__missing-name">{{ item }}</span>
          <MissingValue :value="null" :reason="props.reason" />
        </li>
      </ul>

      <div v-if="resolvedActions.length > 0" class="cl-view-state__actions" data-part="actions">
        <button
          v-for="kind in resolvedActions"
          :key="kind"
          type="button"
          class="cl-view-state__action"
          :data-action="kind"
          @click="emit('action', kind)"
        >
          {{ ACTION_NAMES[kind] }}
        </button>
      </div>

    </template>

    <div v-if="$slots.default !== undefined" class="cl-view-state__body" data-part="body">
      <slot />
    </div>

    <div v-if="$slots.evidence !== undefined" class="cl-view-state__evidence" data-part="evidence">
      <slot name="evidence" />
    </div>

    <footer v-if="$slots.footer !== undefined" class="cl-view-state__footer" data-part="footer">
      <slot name="footer" />
    </footer>
  </section>
</template>

<style scoped>
.cl-view-state {
  display: flex;
  flex-direction: column;
  gap: var(--cl-space-3);
  width: 100%;
  max-width: 100%;
  padding: var(--cl-space-4);
  border: 1px solid var(--cl-line);
  border-radius: var(--cl-radius-md);
  background: var(--cl-card);
  color: var(--cl-ink-900);
  font-size: var(--cl-fs-body);
}
.cl-view-state__custom-title {
  margin: 0;
  color: var(--cl-ink-900);
}
.cl-view-state__previous {
  margin: 0;
  align-self: flex-start;
  padding: 0 var(--cl-space-2);
  border: 1px solid var(--cl-line);
  border-radius: var(--cl-radius-sm);
  background: var(--cl-ink-50);
  color: var(--cl-ink-700);
  font-size: var(--cl-fs-label);
}
.cl-view-state__missing {
  margin: 0;
  padding-left: var(--cl-space-4);
  display: flex;
  flex-direction: column;
  gap: var(--cl-space-1);
}
.cl-view-state__missing-item {
  display: flex;
  gap: var(--cl-space-2);
  flex-wrap: wrap;
  color: var(--cl-ink-700);
}
.cl-view-state__actions {
  display: flex;
  gap: var(--cl-space-2);
  flex-wrap: wrap;
}
.cl-view-state__action {
  height: var(--cl-btn-h-sm);
  padding: 0 var(--cl-space-3);
  border: 1px solid var(--cl-brand-600);
  border-radius: var(--cl-radius-sm);
  background: var(--cl-card);
  color: var(--cl-brand-600);
  font-size: var(--cl-fs-label);
}
.cl-view-state__body,
.cl-view-state__evidence,
.cl-view-state__footer {
  max-width: 100%;
}
</style>
