# 26 页视觉走查矩阵（骨架 + 已取证页的实测行）

- 性质：**计划与台账**，不是结果。除 UI-01 / UI-02 外，其余 24 页页面尚未交付，走查不适用（NOT-DELIVERED），
  本表给出每页开工时必须走完的固定八项与证据落点，避免逐页临时发明口径。
- 路由与 operationId 一律抄 `contracts/pages.json`（机器真值）；AC 编号一律抄 `qa/ACCEPTANCE.md`。
- 每页出口证据：`evidence/<M>/ui/<page-id>/`，截图两档 1440×900 与 1024×768，文件名纯 ASCII。
- 走查前置：`fc-list | grep -c "Noto Sans CJK SC"` ≥ 1（缺字体的截图不能作视觉结论）。

## 固定走查八项（每页必过）

1. 六态（空/加载/错误/待补/失效/部分可比）各有文案与下一步，且**不靠颜色区分**（data-state + role + 文案 + 形状）；
2. 键盘：Tab 顺序＝DOM 顺序、表头排序 Enter/Space、抽屉 Esc 关闭并回收焦点、焦点线 2px；
3. 截图两档（1440×900 / 1024×768）整页；
4. 机器门禁 7 条（`web/tests/e2e/activity/gates.ts` 的浏览器侧 6 条 + 源码侧第 7 条）；
5. 深链接 / 刷新 / 切工作区 / 过期会话都回合法入口，且深链参数可恢复；
6. 缺值显示 — 与原因；合成数据有可见标注；禁 0/空串顶替；
7. 请求形状：operationId 逐字取契约、空查询参数不发送、幂等键 8..128 且 409 沿原键、ETag→If-Match；
8. 内容红线字样扫描（禁总括语、关联≠因果、提交≠发布、摘要不冒充原件）。

## 矩阵

| 页 | 标题 | route | 交付状态 | 已取证证据 | 阻塞 / 待办 |
|---|---|---|---|---|---|
| UI-01 | 工作区与首次进入 | / | 已交付（M0-03） | evidence/M0/ui/ui-01-*.png；键盘基线 tests/e2e/keyboard-baseline.spec.ts | 本批未重跑截图（不改写 M0 证据） |
| UI-02 | 活动列表 | /w/:workspace_id/activities | 已交付（本批） | evidence/FE/ui/ui-02/（32 张） | 偏差见 web/docs/FE-UI-02-activity-list.md §4 |
| UI-03 | 活动详情与版本回执 | /w/:workspace_id/activities/:activity_id | NOT-DELIVERED | — | UI-02 详情抽屉暂代其读面 |
| UI-04 | 规则版本编辑与对比 | …/rules/:rule_id | NOT-DELIVERED | — | — |
| UI-05 | 规则检查与边界案例 | …/rules/:rule_id/checks | NOT-DELIVERED | — | — |
| UI-06 | 数据导入任务 | /w/:workspace_id/imports | NOT-DELIVERED | — | **FE-BLK-01**：http.ts 恒 JSON，createImport 需 multipart（CR 请求 [4]） |
| UI-07 | 映射配置与发布 | …/imports/:import_id | NOT-DELIVERED | — | 同 FE-BLK-01（attachImportFile） |
| UI-08 | 数据快照与更正 | /w/:workspace_id/snapshots | NOT-DELIVERED | — | — |
| UI-09 | 指标字典与口径证据 | /w/:workspace_id/definitions | NOT-DELIVERED | — | — |
| UI-10 | 跨行同义指标对账 | /w/:workspace_id/compare | NOT-DELIVERED | — | 部分可比态首现页，走查须带共同子集缺项区 |
| UI-11 | 渠道重算与时间窗关联 | /w/:workspace_id/channels | NOT-DELIVERED | — | — |
| UI-12 | 场景案例库 | /w/:workspace_id/cases | NOT-DELIVERED | — | — |
| UI-13 | 案例输入、实测与预期 | …/cases/:case_id | NOT-DELIVERED | — | — |
| UI-14 | 运行中心与批量复跑 | /w/:workspace_id/runs | NOT-DELIVERED | — | 202 轮询 1.5s×20 + AbortSignal 首现页 |
| UI-15 | 运行结果、轨迹与验收案例 | …/runs/:run_id | NOT-DELIVERED | — | downloadExport 二进制下载口径待 CR |
| UI-16 | 行内预发结果对照 | /w/:workspace_id/preflight | NOT-DELIVERED | — | — |
| UI-17 | 策略复盘工作台 | /w/:workspace_id/review | NOT-DELIVERED | — | 月报 variant（registry 扩展点）首现页 |
| UI-18 | 异常诊断与贡献拆解 | /w/:workspace_id/diagnosis | NOT-DELIVERED | — | 图表等义数据表首现页 |
| UI-19 | 业务问答与专题入口 | /w/:workspace_id/ask | NOT-DELIVERED | — | — |
| UI-20 | 接触转化情景试算 | /w/:workspace_id/estimate | NOT-DELIVERED | — | — |
| UI-21 | 报告列表与新建 | /w/:workspace_id/reports | NOT-DELIVERED | — | — |
| UI-22 | 报告审阅、签认与修订 | …/reports/:report_id | NOT-DELIVERED | — | 签认措辞纪律（提交≠发布）首现页 |
| UI-23 | 改进项列表 | /w/:workspace_id/actions | NOT-DELIVERED | — | — |
| UI-24 | 改进执行与下期复核 | …/actions/:action_id | NOT-DELIVERED | — | — |
| UI-25 | 作业状态与恢复 | /w/:workspace_id/jobs | NOT-DELIVERED | — | 排队或计算态（非六态）首现页 |
| UI-26 | 证据、审计与导出 | /w/:workspace_id/evidence | NOT-DELIVERED | — | 导出/下载口径待 CR |

## 维护规则

- 每交付一页：把该行「交付状态」改为已交付（分支+提交）、补证据路径、把走查八项的实测结论写进
  `web/docs/FE-UI-xx-*.md`（命名同本批 UI-02 文档），本矩阵只留指针，不复制结论。
- 发现冻结面缺陷：不改冻结件，登记 FE-TO-DAG-REQUESTS.md 的 CR 批次，并在对应页文档「诚实偏差」留痕。