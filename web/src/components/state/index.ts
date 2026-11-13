/**
 * web/src/components/state/index.ts —— 六态件 barrel（M0-03b / S3）
 *
 * 冻结口径：M0-03b-freeze.md §3.1 第 10 行「只 re-export 5-9」，即
 * viewState.ts / ViewState.vue / FirstLoadSkeleton.vue / MissingValue.vue / registry.ts 的冻结面。
 * 新增导出须走 CR（同文 §5 第 2 行）。dev 水槽（回报 S3-2）不在冻结面内，故不经 barrel 暴露，
 * 只由 state/ 内部与 web/tests/unit/state/** 按模块路径直接使用。
 */
export { VIEW_STATE_KINDS, actionsOf, copyOf, stateFromError } from "./viewState";
export type { ViewStateAction, ViewStateCopy, ViewStateKind } from "./viewState";

export { registerViewStateVariant, resolveVariants, unregisterViewStateVariant } from "./registry";
export type { ViewStateContext, ViewStateVariant } from "./registry";

export { default as ViewState } from "./ViewState.vue";
export { default as FirstLoadSkeleton } from "./FirstLoadSkeleton.vue";
export { default as MissingValue } from "./MissingValue.vue";
