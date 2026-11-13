/**
 * web/src/components/state/registry.ts —— 外部注册扩展点（M0-03b / S3，手册 15.6 末条）
 *
 * 签名冻结源：orchestrator/handoff/M0-03b-freeze.md §4.2（类型签名级冻结；注册内容开放）。
 * 目的：wave5 / wave7 的月报视角（M3-P02，AC-MR-03 至 AC-MR-08）能在**不改 §3 任何签名**的前提下接入。
 *
 * 规则落地：
 *   - R-2 幂等注册：同 id 重复注册即覆盖，并在 dev 下告警；覆盖后重新排到末尾，
 *     使「后注册者生效」（ViewState 取 resolveVariants() 的最后一个命中项）可机器判定。
 *   - R-3 能力上界：variant 只能覆盖文案、追加动作键、替换呈现，取值仍限冻结字面量集合。
 *   - R-5 无副作用装载：本文件顶层没有任何注册调用，注册只发生在调用方模块。
 */
import type { Component } from "vue";
import { pushViewStateNotice } from "./viewState";
import type { ViewStateAction, ViewStateCopy, ViewStateKind } from "./viewState";

/** 注册判定上下文（§4.2）；reviewId 出处 ui/COMMON.md:21「可复盘链接优先使用固定的 review_id」。 */
export interface ViewStateContext {
  readonly state: ViewStateKind;
  readonly routeName: string | null;
  readonly workspaceId: string | null;
  readonly reviewId: string | null;
}

export interface ViewStateVariant {
  readonly id: string;
  readonly appliesTo: (ctx: ViewStateContext) => boolean;
  readonly copy?: Partial<Record<ViewStateKind, Partial<ViewStateCopy>>>;
  readonly extraActions?: Partial<Record<ViewStateKind, readonly ViewStateAction[]>>;
  readonly render?: Component;
}

const VARIANTS = new Map<string, ViewStateVariant>();

export function registerViewStateVariant(variant: ViewStateVariant): void {
  if (VARIANTS.has(variant.id)) {
    pushViewStateNotice("registry", "variant-overwrite", 'id="' + variant.id + '" 重复注册，按 R-2 覆盖前者');
    VARIANTS.delete(variant.id);
  }
  VARIANTS.set(variant.id, variant);
}

/** 仅测试用（§4.2）：卸载后 resolveVariants() 不再命中；对不存在的 id 幂等。 */
export function unregisterViewStateVariant(id: string): void {
  VARIANTS.delete(id);
}

export function resolveVariants(ctx: ViewStateContext): readonly ViewStateVariant[] {
  const hits: ViewStateVariant[] = [];
  for (const variant of VARIANTS.values()) {
    if (variant.appliesTo(ctx)) hits.push(variant);
  }
  return hits;
}
