# 后台作业与恢复契约

## 接口约定

作业受理为 202，返回 `Job` 和指向状态资源的 `Location`。轮询默认 1 秒，连续 5 次未变化退避到 3 秒，离开页面可停止轮询。作业完成后按 `result_ref.kind` 和 `id` 获取结果。查询状态均可刷新恢复。业务结果中的部分可比、预发差异和规则检查命中仍可作为成功作业输出。

作业类型有 `VALIDATE_IMPORT`、`PUBLISH_IMPORT`、`CORRECT_SNAPSHOT`、`COMPARE`、`REVIEW`、`DIAGNOSE`、`QUESTION`、`SIMULATE`、`REPORT`、`EXPORT`。输入固定快照和对象修订版本。用例接受输入时写任务与请求幂等记录。默认工作区最多 10 个待办，达到上限返回 429 和 Retry-After。

| 当前状态 | 动作或条件 | 下一状态与记录 |
|---|---|---|
| QUEUED | 事务内最早可认领 | RUNNING，递增 attempt，生成随机 lease token，写 lease_until |
| QUEUED | 请求取消 | CANCELLED，写审计 |
| RUNNING | 每 5 秒续租 | RUNNING，租约到期为当前时间加 30 秒，写阶段进度 |
| RUNNING | 请求取消 | CANCEL_REQUESTED，执行进程在安全分段读取取消信号 |
| RUNNING | 成功与租约仍有效 | SUCCEEDED，登记制品和结果引用，同事务公开结果 |
| RUNNING | 已知失败 | FAILED，保留错误码、阶段及可重试标志 |
| RUNNING | 超时租约且证据未提交 | FAILED，错误 JOB_INTERRUPTED |
| CANCEL_REQUESTED | 执行确认或租约到期 | CANCELLED，保留原输入 |
| FAILED 或 CANCELLED | 操作员发起重试 | 新 QUEUED 作业，引用 retry_of 与同一输入快照 |

## 写入与进程恢复

使用 SQLite 本机短事务。认领使用 `BEGIN IMMEDIATE` 后检查状态，提交后开始 CPU 和 I/O 工作。完成和续租均匹配工作区、作业、attempt 和 lease token。旧尝试结果登记失败时其制品视为未引用。若取消与完成争用，先成功提交的合法状态决定结果。终态重复查询一致。遇到中断，启动恢复逻辑扫描过期租约，不重写已成功作业。

作业写临时文件时采用独立尝试目录。完整制品校验后在同一文件系统原子重命名，事务登记索引及结果。事务提交失败允许重试并复用同摘要文件。备份、恢复与垃圾回收按 [运行契约](OPERATIONS.md)。报告和签认保存其输入摘要及历史制品引用。

## 验收

- 重复相同幂等键的请求返回同一任务。不同请求摘要返回 409。
- 两次尝试争抢同一作业时只有有效租约可发布。模拟 kill 后等待过期，原任务标记中断。重试得到一次可见结果。
- 取消排队、运行中取消、在原子提交后取消分别验证，任务记录与可见文件一致。
- DuckDB 作业单次默认使用最多 2 个线程、1 GiB 内存和受控临时目录。任务失败可以在页面查看阶段、原因和输入范围。
