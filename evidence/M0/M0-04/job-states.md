# M0-04 / S8 · T1–T9 状态迁移取证（jobs 行快照 × 迁移前/后 ＋ HTTP 样本）

- 定义点：`worker/states.py::TRANSITIONS`（`JobState`/`JobKind` 定义点在 `api/common.py`，此处 re-export）。
- 采集方式：本棒活链路实跑（工具件 `commands-s8.md` §4/§7 留 sha）；装配面复用 `tests/integration/jobs/test_jobs_router_s4.py::Harness` 冻结口径；时钟只经 `FixedClock`（T0=2026-11-13T01:00:00Z）。
- 快照为 `jobs` 全行逐字（DB 面取证必然含 `lease_token`/`lease_until` 列——它们是 DB 列，**不在 HTTP 响应体**，V5 断言面：`tests/unit/test_job_dto.py`）。
- 迁移前/后快照对同一行作业；`revision` 逐跳 +1 与 `attempt`/租约双列变化即状态机谓词的落盘证据。

## 总表

| T | 迁移 | 触发面 | HTTP 样本 |
|---|---|---|---|
| T1 | QUEUED→RUNNING | worker TX1 claim_next | 无 HTTP 触发面（worker 侧）；只读见证面＝`http/getJob.json` 同型 |
| T2 | QUEUED→CANCELLED | HTTP cancelJob（If-Match 命中） | `http/cancelJob-200.json`（got=200） |
| T3 | RUNNING→RUNNING | worker TX2 renew（+30s） | 无 HTTP 触发面（worker 侧续租） |
| T4 | RUNNING→CANCEL_REQUESTED | HTTP cancelJob | 同 cancelJob 面·本行实跑响应体逐字内联（见 T4 节） |
| T5 | RUNNING→SUCCEEDED | worker TX5 succeed（同事务公开结果） | 无 HTTP 触发面（worker 侧） |
| T6 | RUNNING→FAILED | worker TX6 fail（已知失败 Problem 落 problem_json） | 无 HTTP 触发面（worker 侧） |
| T7 | RUNNING→FAILED | TX7 reap（FixedClock 推过 lease_until） | 无 HTTP 触发面（恢复扫描）；REAP 实测＝{"interrupted": 1, "cancelled": 1} |
| T8 | CANCEL_REQUESTED→CANCELLED | TX4 confirm_cancel ／ TX7 到期收口 | 无 HTTP 触发面；两分支均实测（见 T8 节） |
| T9 | FAILED/CANCELLED→新行 QUEUED | HTTP retryJob | `http/retryJob-202.json`（got=202）＋源行/新行双快照 |

以下逐条快照对（同一 harness、同一时钟链）：

## T1 `QUEUED` → `RUNNING` · 触发：事务内最早可认领

- 权威定义（`src/campaignlab/worker/states.py::TRANSITIONS` 实测逐字）：sources=`['QUEUED']` target=`RUNNING` guard=`state = 'QUEUED' AND revision = :revision` transaction=`TX1 JobRepository.claim_next` spec_ref=`JOBS.md:11` creates_new_row=`False`
- HTTP 样本：无 HTTP 触发面（worker 认领；`attempt 0→1`、租约双列落位、`stage=CLAIMED` 见快照）

**迁移前** · `T1-before ws=ws-s8 job=j-t1`：

```json
{
 "attempt": 0,
 "created_at": "2026-11-13T01:00:00+00:00",
 "id": "j-t1",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": null,
 "lease_until": null,
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 1,
 "stage": "QUEUED",
 "state": "QUEUED",
 "workspace_id": "ws-s8"
}
```

**迁移后** · `T1-after ws=ws-s8 job=j-t1`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:00+00:00",
 "id": "j-t1",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": "vd6VlUPlxKdZT139C5ZmQ6hkwwcZTFZI_0soG49d10w",
 "lease_until": "2026-11-13T01:00:30+00:00",
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 2,
 "stage": "CLAIMED",
 "state": "RUNNING",
 "workspace_id": "ws-s8"
}
```

## T2 `QUEUED` → `CANCELLED` · 触发：请求取消

- 权威定义（`src/campaignlab/worker/states.py::TRANSITIONS` 实测逐字）：sources=`['QUEUED']` target=`CANCELLED` guard=`state = 'QUEUED' AND revision = :revision` transaction=`TX3 JobRepository.request_cancel` spec_ref=`JOBS.md:12` creates_new_row=`False`
- HTTP 样本：`http/cancelJob-200.json`（got=200）。响应体逐字：`{"id":"j-t2","revision":2,"created_at":"2026-11-13T01:00:05Z","kind":"VALIDATE_IMPORT","state":"CANCELLED","attempt":0,"progress":0,"stage":"QUEUED","input_digest":"0000000000000000000000000000000000000000000000000000000000000000","retry_of":null,"result_ref":null,"problem":null,"retryable":true}`

**迁移前** · `T2-before ws=ws-s8 job=j-t2`：

```json
{
 "attempt": 0,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t2",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": null,
 "lease_until": null,
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 1,
 "stage": "QUEUED",
 "state": "QUEUED",
 "workspace_id": "ws-s8"
}
```

**迁移后** · `T2-after ws=ws-s8 job=j-t2`：

```json
{
 "attempt": 0,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t2",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": null,
 "lease_until": null,
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 1,
 "revision": 2,
 "stage": "QUEUED",
 "state": "CANCELLED",
 "workspace_id": "ws-s8"
}
```

## T3 `RUNNING` → `RUNNING` · 触发：每 5 秒续租

- 权威定义（`src/campaignlab/worker/states.py::TRANSITIONS` 实测逐字）：sources=`['RUNNING']` target=`RUNNING` guard=`attempt = :attempt AND lease_token = :lease_token AND state IN ('RUNNING', 'CANCEL_REQUESTED')` transaction=`TX2 JobRepository.renew` spec_ref=`JOBS.md:13` creates_new_row=`False`
- HTTP 样本：无 HTTP 触发面（`renew` 谓词 attempt+token 命中；`lease_until `01:00:30→01:00:35`（=renew 时刻＋30s，谓词 attempt+token 命中）` 见快照）

**迁移前** · `T1-after ws=ws-s8 job=j-t1`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:00+00:00",
 "id": "j-t1",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": "vd6VlUPlxKdZT139C5ZmQ6hkwwcZTFZI_0soG49d10w",
 "lease_until": "2026-11-13T01:00:30+00:00",
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 2,
 "stage": "CLAIMED",
 "state": "RUNNING",
 "workspace_id": "ws-s8"
}
```

**迁移后** · `T3-after ws=ws-s8 job=j-t1`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:00+00:00",
 "id": "j-t1",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": "vd6VlUPlxKdZT139C5ZmQ6hkwwcZTFZI_0soG49d10w",
 "lease_until": "2026-11-13T01:00:35+00:00",
 "problem_json": null,
 "progress": 5,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 3,
 "stage": "s8-renew",
 "state": "RUNNING",
 "workspace_id": "ws-s8"
}
```

## T4 `RUNNING` → `CANCEL_REQUESTED` · 触发：请求取消（执行进程在安全分段读取取消信号）

- 权威定义（`src/campaignlab/worker/states.py::TRANSITIONS` 实测逐字）：sources=`['RUNNING']` target=`CANCEL_REQUESTED` guard=`state = 'RUNNING' AND revision = :revision` transaction=`TX3 JobRepository.request_cancel` spec_ref=`JOBS.md:14` creates_new_row=`False`
- HTTP 样本：无固定文件名样本（11 件面已含 T2 之 200）；本次实跑响应体逐字：`status=200 {"id":"j-t4","revision":3,"created_at":"2026-11-13T01:00:05Z","kind":"VALIDATE_IMPORT","state":"CANCEL_REQUESTED","attempt":1,"progress":0,"stage":"CLAIMED","input_digest":"0000000000000000000000000000000000000000000000000000000000000000","retry_of":null,"result_ref":null,"problem":null,"retryable":false}`（state=CANCEL_REQUESTED 即 T4 生效）

**迁移前** · `T4-before ws=ws-s8 job=j-t4`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t4",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": "x4Dxb7lbUbbLFF4X0eon-IvtUt1XTfJcLlYP43ppZzw",
 "lease_until": "2026-11-13T01:00:35+00:00",
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 2,
 "stage": "CLAIMED",
 "state": "RUNNING",
 "workspace_id": "ws-s8"
}
```

**迁移后** · `T4-after ws=ws-s8 job=j-t4`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t4",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": "x4Dxb7lbUbbLFF4X0eon-IvtUt1XTfJcLlYP43ppZzw",
 "lease_until": "2026-11-13T01:00:35+00:00",
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 3,
 "stage": "CLAIMED",
 "state": "CANCEL_REQUESTED",
 "workspace_id": "ws-s8"
}
```

## T5 `RUNNING` → `SUCCEEDED` · 触发：成功与租约仍有效

- 权威定义（`src/campaignlab/worker/states.py::TRANSITIONS` 实测逐字）：sources=`['RUNNING']` target=`SUCCEEDED` guard=`attempt = :attempt AND lease_token = :lease_token AND state IN ('RUNNING', 'CANCEL_REQUESTED')` transaction=`TX5 JobRepository.mark_succeeded` spec_ref=`JOBS.md:15` creates_new_row=`False`
- HTTP 样本：无 HTTP 触发面（worker 提交；`result_json` 同事务落位、租约双列清空见快照）

**迁移前** · `T3-after ws=ws-s8 job=j-t1`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:00+00:00",
 "id": "j-t1",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": "vd6VlUPlxKdZT139C5ZmQ6hkwwcZTFZI_0soG49d10w",
 "lease_until": "2026-11-13T01:00:35+00:00",
 "problem_json": null,
 "progress": 5,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 3,
 "stage": "s8-renew",
 "state": "RUNNING",
 "workspace_id": "ws-s8"
}
```

**迁移后** · `T5-after ws=ws-s8 job=j-t1`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:00+00:00",
 "id": "j-t1",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": null,
 "lease_until": null,
 "problem_json": null,
 "progress": 100,
 "result_json": "{\"id\":\"j-t1\",\"kind\":\"job\"}",
 "retry_of": null,
 "retryable": 0,
 "revision": 4,
 "stage": "s8-renew",
 "state": "SUCCEEDED",
 "workspace_id": "ws-s8"
}
```

## T6 `RUNNING` → `FAILED` · 触发：已知失败

- 权威定义（`src/campaignlab/worker/states.py::TRANSITIONS` 实测逐字）：sources=`['RUNNING']` target=`FAILED` guard=`attempt = :attempt AND lease_token = :lease_token AND state IN ('RUNNING', 'CANCEL_REQUESTED')` transaction=`TX6 JobRepository.mark_failed` spec_ref=`JOBS.md:16` creates_new_row=`False`
- HTTP 样本：无 HTTP 触发面（worker 失败收口；`problem_json.code=VALIDATION_ERROR`＋`issues[0].code=NO_HANDLER`、`retryable=0` 为永久性输入缺陷口径，见快照）

**迁移前** · `T6-before ws=ws-s8 job=j-t6`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t6",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": "nqjQvP8WroAAnaUj37-RnrnMSYpujYmF2dTExxjln9A",
 "lease_until": "2026-11-13T01:00:35+00:00",
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 2,
 "stage": "CLAIMED",
 "state": "RUNNING",
 "workspace_id": "ws-s8"
}
```

**迁移后** · `T6-after ws=ws-s8 job=j-t6`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t6",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": null,
 "lease_until": null,
 "problem_json": "{\"code\":\"VALIDATION_ERROR\",\"detail\":\"s8 取证：未注册 kind 的桩式失败\",\"issues\":[{\"code\":\"NO_HANDLER\",\"location\":\"/kind\",\"message\":\"未注册 handler\",\"severity\":\"ERROR\"}],\"request_id\":\"req-s8-forensic\",\"status\":422,\"title\":\"字段校验未通过\",\"type\":\"urn:campaignlab:problem:validation_error\"}",
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 3,
 "stage": "CLAIMED",
 "state": "FAILED",
 "workspace_id": "ws-s8"
}
```

## T7 `RUNNING` → `FAILED` · 触发：超时租约且证据未提交

- 权威定义（`src/campaignlab/worker/states.py::TRANSITIONS` 实测逐字）：sources=`['RUNNING']` target=`FAILED` guard=`state = 'RUNNING' AND lease_until < :now` transaction=`TX7 JobRepository.fail_expired_running` spec_ref=`JOBS.md:17` creates_new_row=`False`
- HTTP 样本：无 HTTP 触发面（TX7 恢复扫描）。`FixedClock` 推 31s＞TTL30 ⇒ REAP={"interrupted": 1, "cancelled": 1}；`problem_json`＝INTERNAL_ERROR/status=500/`issues[0].code=JOB_INTERRUPTED`（JOB_INTERRUPTED **不进** Problem.code，A88③）见快照

**迁移前** · `T7-before ws=ws-s8 job=j-t7`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t7",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": "uzaXVClrIb2X_DaRuGhFIpLUU3-QcEi72Zsv5LStOY8",
 "lease_until": "2026-11-13T01:00:35+00:00",
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 2,
 "stage": "CLAIMED",
 "state": "RUNNING",
 "workspace_id": "ws-s8"
}
```

**迁移后** · `T7-after ws=ws-s8 job=j-t7`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t7",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": null,
 "lease_until": null,
 "problem_json": "{\"code\":\"INTERNAL_ERROR\",\"detail\":\"作业租约已过期且证据未提交，本次尝试记为中断；可发起重试。\",\"issues\":[{\"code\":\"JOB_INTERRUPTED\",\"location\":\"/job/lease_until\",\"message\":\"租约已过期且证据未提交\",\"severity\":\"ERROR\"}],\"request_id\":\"90e002a7d3534eada20615e0abefe366\",\"status\":500,\"title\":\"服务内部错误\",\"type\":\"urn:campaignlab:problem:internal_error\"}",
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 1,
 "revision": 3,
 "stage": "CLAIMED",
 "state": "FAILED",
 "workspace_id": "ws-s8"
}
```

## T8 `CANCEL_REQUESTED` → `CANCELLED` · 触发：执行确认或租约到期

- 权威定义（`src/campaignlab/worker/states.py::TRANSITIONS` 实测逐字）：sources=`['CANCEL_REQUESTED']` target=`CANCELLED` guard=`执行确认：attempt = :attempt AND lease_token = :lease_token AND state = 'CANCEL_REQUESTED'；到期：state = 'CANCEL_REQUESTED' AND lease_until < :now` transaction=`TX4 JobRepository.confirm_cancel / TX7 JobRepository.cancel_expired_requested` spec_ref=`JOBS.md:18` creates_new_row=`False`
- HTTP 样本：无 HTTP 触发面。两分支实测：**确认**（本节快照对 T4-after→T8-after）；**到期**（`T8x-before ws=ws-s8 job=j-t8x` → `T8x-after ws=ws-s8 job=j-t8x`，与 T7 同一次 reap，REAP.cancelled=1）

**迁移前** · `T4-after ws=ws-s8 job=j-t4`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t4",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": "x4Dxb7lbUbbLFF4X0eon-IvtUt1XTfJcLlYP43ppZzw",
 "lease_until": "2026-11-13T01:00:35+00:00",
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 3,
 "stage": "CLAIMED",
 "state": "CANCEL_REQUESTED",
 "workspace_id": "ws-s8"
}
```

**迁移后** · `T8-after ws=ws-s8 job=j-t4`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t4",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": null,
 "lease_until": null,
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 1,
 "revision": 4,
 "stage": "CLAIMED",
 "state": "CANCELLED",
 "workspace_id": "ws-s8"
}
```

**T8 到期分支快照对**：

迁移前 · `T8x-before ws=ws-s8 job=j-t8x`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t8x",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": "tNGz19WxrYQO9Hc_rcUbnoc2rrAQZzLHXc7PXnauESA",
 "lease_until": "2026-11-13T01:00:35+00:00",
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 3,
 "stage": "CLAIMED",
 "state": "CANCEL_REQUESTED",
 "workspace_id": "ws-s8"
}
```

迁移后 · `T8x-after ws=ws-s8 job=j-t8x`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t8x",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": null,
 "lease_until": null,
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 1,
 "revision": 4,
 "stage": "CLAIMED",
 "state": "CANCELLED",
 "workspace_id": "ws-s8"
}
```

## T9 `['CANCELLED', 'FAILED']` → `QUEUED` · 触发：操作员发起重试

- 权威定义（`src/campaignlab/worker/states.py::TRANSITIONS` 实测逐字）：sources=`['CANCELLED', 'FAILED']` target=`QUEUED` guard=`state IN ('FAILED', 'CANCELLED') AND revision = :revision` transaction=`TX8 JobRepository.enqueue_retry（新行复用既有入队方法）` spec_ref=`JOBS.md:19` creates_new_row=`True`
- HTTP 样本：`http/retryJob-202.json`（got=202，Location 指向新行）。响应体逐字：`{"id":"J-3f77ad99aeb24fc5afc92215ff335f32","revision":1,"created_at":"2026-11-13T01:00:00Z","kind":"VALIDATE_IMPORT","state":"QUEUED","attempt":0,"progress":0,"stage":"QUEUED","input_digest":"0000000000000000000000000000000000000000000000000000000000000000","retry_of":"j-t6","result_ref":null,"problem":null,"retryable":false}`；**新行快照**（`retry_of` 指回源、`attempt/revision` 重起）：

**迁移前** · `T6-after ws=ws-s8 job=j-t6`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t6",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": null,
 "lease_until": null,
 "problem_json": "{\"code\":\"VALIDATION_ERROR\",\"detail\":\"s8 取证：未注册 kind 的桩式失败\",\"issues\":[{\"code\":\"NO_HANDLER\",\"location\":\"/kind\",\"message\":\"未注册 handler\",\"severity\":\"ERROR\"}],\"request_id\":\"req-s8-forensic\",\"status\":422,\"title\":\"字段校验未通过\",\"type\":\"urn:campaignlab:problem:validation_error\"}",
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 3,
 "stage": "CLAIMED",
 "state": "FAILED",
 "workspace_id": "ws-s8"
}
```

**迁移后** · `T9-source-after ws=ws-s8 job=j-t6`：

```json
{
 "attempt": 1,
 "created_at": "2026-11-13T01:00:05+00:00",
 "id": "j-t6",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": null,
 "lease_until": null,
 "problem_json": "{\"code\":\"VALIDATION_ERROR\",\"detail\":\"s8 取证：未注册 kind 的桩式失败\",\"issues\":[{\"code\":\"NO_HANDLER\",\"location\":\"/kind\",\"message\":\"未注册 handler\",\"severity\":\"ERROR\"}],\"request_id\":\"req-s8-forensic\",\"status\":422,\"title\":\"字段校验未通过\",\"type\":\"urn:campaignlab:problem:validation_error\"}",
 "progress": 0,
 "result_json": null,
 "retry_of": null,
 "retryable": 0,
 "revision": 4,
 "stage": "CLAIMED",
 "state": "FAILED",
 "workspace_id": "ws-s8"
}
```


```json
{
 "attempt": 0,
 "created_at": "2026-11-13T01:00:00+00:00",
 "id": "J-3f77ad99aeb24fc5afc92215ff335f32",
 "input_digest": "0000000000000000000000000000000000000000000000000000000000000000",
 "input_json": "{}",
 "kind": "VALIDATE_IMPORT",
 "lease_token": null,
 "lease_until": null,
 "problem_json": null,
 "progress": 0,
 "result_json": null,
 "retry_of": "j-t6",
 "retryable": 0,
 "revision": 1,
 "stage": "QUEUED",
 "state": "QUEUED",
 "workspace_id": "ws-s8"
}
```

## ⑤ 三点分别落测指针（design §7⑤／派单文 §5⑤）

- 取消排队 **T2**：`http/cancelJob-200.json`（本件 T2 节）＋ `V8-5c` 用例 `test_cancel_job_queued_becomes_cancelled_200`。
- 运行中取消 **T4**：本件 T4 节（HTTP 200 响应体内联，state=CANCEL_REQUESTED）＋ `V8-5b`（参数 id `T4-running-cancel-keeps-lease`）。
- 原子提交后取消 → **409 STATE_CONFLICT**：`http/cancelJob-409.json`（活链路：claim→succeed 后 cancel，got=409）＋ `V8-5a`（取消／完成先提交者定终态，2 参数例）。
- 终态重复查询逐字节一致：`test_get_job_200_with_etag_and_repeat_identical`（既有 S4 面，`V2/V3` 目录同源）。

（本件全部快照与内联体逐字取自 `collect.log` 实跑输出；该 stdout 的逐字命令与 sha 见 `commands-s8.md` §4/§7。）

