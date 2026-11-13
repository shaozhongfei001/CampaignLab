<script setup lang="ts">
import type { TableColumn, TableRow } from "./componentTypes";
const props = defineProps<{
  columns: readonly TableColumn[];
  rows: readonly TableRow[];
  sortKey?: string | undefined;
  sortDir?: string | undefined;
  caption: string;
}>();
const emit = defineEmits<{ sort: [key: string] }>();

function ariaSort(col: TableColumn): "ascending" | "descending" | "none" {
  if (col.sortable !== true || props.sortKey !== col.key) return "none";
  return props.sortDir === "desc" ? "descending" : "ascending";
}
</script>
<template>
  <div class="cl-table-scroll">
    <table class="cl-table">
      <caption class="cl-table__caption">{{ props.caption }}</caption>
      <thead>
        <tr>
          <th v-for="col in props.columns" :key="col.key" scope="col" :aria-sort="ariaSort(col)">
            <button v-if="col.sortable === true" type="button" class="cl-table__sort" @click="emit('sort', col.key)">
              {{ col.label }}
            </button>
            <span v-else>{{ col.label }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, r) in props.rows" :key="r">
          <td v-for="col in props.columns" :key="col.key" :class="col.mono === true ? 'is-mono' : ''">
            <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">{{ row[col.key] ?? "—" }}</slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<style scoped>
.cl-table-scroll { overflow-x: auto; }
.cl-table { width: 100%; border-collapse: collapse; font-size: var(--cl-fs-body); }
.cl-table__caption { caption-side: top; text-align: left; font-size: 13px; color: var(--cl-ink-500); padding-bottom: 8px; }
.cl-table th { height: 32px; text-align: left; border-bottom: 1px solid var(--cl-line); color: var(--cl-ink-700); font-weight: 600; white-space: nowrap; }
.cl-table td { height: var(--cl-row-h); border-bottom: 1px solid var(--cl-line); color: var(--cl-ink-600); white-space: nowrap; }
.cl-table td.is-mono { font-family: var(--cl-font-mono); font-variant-numeric: tabular-nums; }
.cl-table__sort { height: 24px; padding: 0 4px; border: 0; background: transparent; color: inherit; font: inherit; font-weight: 600; cursor: pointer; }
</style>
