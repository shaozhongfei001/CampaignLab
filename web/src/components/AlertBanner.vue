<script setup lang="ts">
import type { ApiError } from "@/api/http";
import { presentationOf } from "@/features/shared/problemPresentation";
// ADR-005 §2.2：title 原样渲染服务端返回值，前端不另编文案；request_id 必须可见。
// R3-Q6：只有 kind === "problem" 才是服务端词汇，其余五类走通用失败态（不伪装 code）。
const props = defineProps<{ error: ApiError | null; note?: string | undefined }>();
</script>
<template>
  <section v-if="error !== null" class="cl-alert" role="alert" :data-bucket="presentationOf(error).bucket ?? 'default'">
    <strong class="cl-alert__title">{{ presentationOf(error).showServerTitle ? error.title : "请求未完成" }}</strong>
    <p v-if="error.detail.length > 0" class="cl-alert__detail">{{ error.detail }}</p>
    <p v-if="presentationOf(error).showServerTitle" class="cl-alert__meta">
      code {{ error.code }} · HTTP {{ error.status }}
    </p>
    <ul v-if="error.issues.length > 0" class="cl-alert__issues">
      <li v-for="(issue, i) in error.issues" :key="i" :data-severity="issue.severity">
        {{ issue.location }} — {{ issue.message }}
      </li>
    </ul>
    <p v-if="note !== undefined && note.length > 0" class="cl-alert__note">{{ note }}</p>
    <p class="cl-alert__rid">request_id {{ error.requestId }}</p>
  </section>
</template>
<style scoped>
.cl-alert {
  border: 1px solid var(--cl-danger-600);
  border-left-width: 4px;
  border-radius: var(--cl-radius-sm);
  background: var(--cl-brand-50);
  padding: 12px 16px;
  color: var(--cl-danger-text);
}
.cl-alert__title { font-size: var(--cl-fs-body); }
.cl-alert__detail, .cl-alert__meta, .cl-alert__note, .cl-alert__rid {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--cl-ink-600);
}
.cl-alert__rid { font-family: var(--cl-font-mono); }
.cl-alert__issues { margin: 8px 0 0; padding-left: 20px; font-size: 13px; }
.cl-alert__issues li[data-severity="WARNING"] { color: var(--cl-warn-text); }
.cl-alert__issues li[data-severity="INFO"] { color: var(--cl-ink-500); }
</style>
