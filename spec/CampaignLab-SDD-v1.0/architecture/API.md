# 服务接口实施契约

接口目录以 [OpenAPI 3.1](../contracts/openapi.json) 为准，含 HTTP 方法、路径、操作编号、请求响应模型、状态码与头。 [操作索引](../contracts/operations.json) 便于实施者导航。服务启动基址为 `/api/v1`。页面通过 operationId 对齐，模型命名与发布 Schema 同步。

## 请求与响应

| 约定 | 实施方式 |
|---|---|
| 会话 | getHealth 可访问最小状态。exchangeSession 换会话。其余操作验证本机会话与作用域。每个修改操作用业务职责记录审计角色 |
| 资源查询 | 单对象 GET 返回对象及 ETag。列表默认 25、上限 100，以 created_at DESC、id ASC 稳定排序。游标含查询摘要、最后排序键、作用域，服务端签名。q 对名称和公开编号按 NFKC casefold 查找，status 按对应对象状态白名单过滤 |
| 更新 | PATCH 只覆盖给出的字段，空 PATCH 422。非空对象字段、重复数组等通过 Schema 和领域校验。确认、签认、取消等用明确动作接口 |
| 幂等 | 所有有写入的请求带 Idempotency-Key。作用域、用户、operationId、键组合唯一。摘要含规范化路径、查询、正文和上传文件摘要。完全相同重放原状态码、Location、ETag 和正文，内容不同返回 409。先查幂等重放，再查 If-Match |
| 版本 | ETag 为带双引号的整数修订号。需要 If-Match 的动作缺头 428，过期 412。UI 保留草稿和最新服务器版本供比较 |
| 作业 | 202 返回 Job 和 Location，后续按结果类型取资源。错误记录 request_id 和可追溯问题。同步计算接口只处理有界输入 |
| 导出 | 访问可见 Export 后读取 file。返回 Content-Disposition、合适媒体类型、内容摘要在 Export 元数据。CSV 以 UTF-8 BOM 导出 |
| 空和缺失 | 无结果列表 items 为 []。指标不可得为 null 且附状态。报告和比较的业务缺失由成功响应中的状态与待补清单表示 |

## 错误分类

| HTTP | code 示例 | 处理 |
|---|---|---|
| 400 | BAD_REQUEST、BAD_CURSOR | 保留当前页，调整输入或重置筛选 |
| 401 / 403 | SESSION_EXPIRED、ORIGIN_DENIED、ACCESS_DENIED | 重新打开启动入口或显示授权缺失 |
| 404 | RESOURCE_NOT_FOUND | 显示当前工作区可见对象列表 |
| 409 | IDEMPOTENCY_CONFLICT、STATE_CONFLICT、VERSION_MISMATCH、STALE_CANDIDATE、SNAPSHOT_CONFLICT、ACTION_REVIEW_REQUIRED | 保留本地输入，刷新版本和证据 |
| 412 / 428 | REVISION_CONFLICT、PRECONDITION_REQUIRED | 获取当前 ETag 后重新确认操作 |
| 413 / 422 | INPUT_TOO_LARGE、VALIDATION_ERROR、INVALID_SCOPE、EVIDENCE_REQUIRED | 显示字段位置、源行或业务前置条件 |
| 429 | JOB_CAPACITY | 按 Retry-After 重试，保留已提交结果入口 |
| 500 | INTERNAL_ERROR | 显示 request_id 与恢复入口。保留错误日志证据 |

Problem 响应为 application/problem+json。字段路径用 JSON Pointer，CSV 可补表名和 1 起数据行号。所有响应生成请求编号。服务端对 workspace_id 和全部关联资源做隔离校验。媒体、Origin、Host 与文件限制见 [运行保护](OPERATIONS.md)。

## 主要操作关系

- 活动、规则、案例先建后确认，确认请求带当前内容摘要。保存候选需要当前可验收行，历史复算必须与观察值一致。详见 [规则和回放](RULES.md)。
- 导入校验固定文件、映射和定义。publishImport 接收最近成功校验摘要。同一银行版本同内容复用，内容改变时发布新版本。详见 [接入数据](DATA.md)。
- 复盘、诊断、问答、报告都保存规范化范围。报告可依已执行问题生成专题，但其 review_id、question_id 必须同快照和语义。详见 [指标和复盘](ANALYTICS.md)。
- 审阅预发保存人工说明，自动判定维持原结果。登记版本回执要求预发所有选择行一致、经审阅且候选仍有效。
- 更正、签认、改进及导出按 [报告契约](REPORTS.md)。审计写入的事件带前序摘要。对相同操作的成功重放沿用原业务结果。
