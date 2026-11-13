<script setup lang="ts">
import { useRoute } from "vue-router";
import CardPanel from "@/components/CardPanel.vue";
const route = useRoute();
const target = String(route.fullPath);
</script>
<template>
  <CardPanel title="页面不存在" :subtitle="'深链 ' + target + ' 无对应已交付页面（该页契约属后续 UI 任务）'">
    <p>当前工作区标识保留在地址栏。可返回入口重新选择工作区。</p>
    <template #footer>
      <router-link to="/">返回入口</router-link>
    </template>
  </CardPanel>
</template>
