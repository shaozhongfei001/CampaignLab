# Vue 与前端开发规范

## 组件和接口

Vue 3 使用 SFC、Composition API 与 TypeScript strict。组件层级采用 pages、features、components、composables、api、router、styles。页面按 [逐页契约](../ui/INDEX.md) 建立路由。公共范围条、状态标签、证据抽屉、作业进度、差异对照及分母提示组件各有一个实现。

由 OpenAPI 生成 TypeScript 类型。API 客户端统一处理 cookie、ETag、Idempotency-Key、Problem 与 202 轮询。类型检查使用 vue-tsc。显示层按 [公共页面规范](../ui/COMMON.md) 转元、百分比和百分点。金额输入转分时使用字符串解析或精确十进制方法。表格、图表与导出用同一服务器结果。状态源可为 URL、请求缓存和本地表单，服务器授权与保存状态由响应决定。

## 界面实现

- 使用 CSS 变量维护公共令牌，Element Plus 承担表单、表格和抽屉，ECharts 使用按需模块。为图表提供数据表替代。
- 深链接带工作区和对象标识。直接打开、刷新、返回、切工作区、404 和过期会话都要能回到合法入口。
- 使用 abort 或请求序列保护较晚响应覆盖当前范围。由计算请求返回的结果标记实际范围。路由离开后释放图表与轮询定时器。
- 空、加载、错误、待补、失效和部分可比均有文案及下一步。提交后状态按服务器响应更新。确认对话框复核证据摘要和业务版本。
- Markdown 报告使用安全解析，展示字段以文本渲染。禁用远程资源和原始 HTML，导出文件按受控接口下载。
- Vitest 验证范围条、数字单位、校验、异步状态。Playwright 以用户可见名称定位控件，固定合成输入和视口，记录可回查截图与请求证据。只比较业务关键信息和设计尺寸允许误差。

官方资料 [Vue TypeScript](https://vuejs.org/guide/typescript/overview) · [Element Plus Table](https://element-plus.org/en-US/component/table.html) · [ECharts Dataset](https://echarts.apache.org/handbook/en/concepts/dataset/) · [Vitest](https://vitest.dev/guide/)
