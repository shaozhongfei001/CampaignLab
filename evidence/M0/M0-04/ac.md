# M0-04 / S8 · AC 取证判定面（纯取证棒；判定只基于派单文 §5 的 ①–⑤ 冻结口径＋本棒实测）

> 立法依据：`orchestrator/handoff/R18-lane-M0-04-S8.md` §3/§5；判据命令与逐字实测见 `commands-s8.md`；
> 快照与 HTTP 样本见 `job-states.md` 与 `http/*.json`、`gates/V1.log…V9.log`。
> 本件不新增任何判定口径；实测与冻结口径无不符项（不符即报 U，见回执）。

## AC-029（`spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md:37`）

**判定：PASS**

切片原文（引）：「重复提交、两个执行者争用、运行中断、取消和重试」→「同键同请求同对象，异请求 409。
失效租约不能提交。中断后可重试。取消/完成只有一个终态」，主证据：作业与 DB。

**依据（design §7 / 派单文 §5 ①–⑤ 逐条）＋ 证据指针**：

| 冻结口径 | 实测事实（本棒） | 证据指针 |
|---|---|---|
| ① 同键同请求→PK 命中重放、DB 只 1 行、含头逐字节相同；异请求→409 `IDEMPOTENCY_CONFLICT` | `V8-1` rc=0：`test_same_key_same_request_same_object`／`test_same_key_different_request_409`／`test_replay_body_byte_identical`（3 passed，逐字见日志） | `gates/V8.log`；`tests/integration/jobs/test_idempotency.py`；异请求 409 形状参照 `http/cancelJob-409.json` 同型 Problem 面 |
| ② 两执行者争用：`BEGIN IMMEDIATE`＋T1 谓词 UPDATE，一方 `rowcount=1`、另一方 `LeaseLost` | `V8-2` rc=0：`test_two_claimers_only_one_wins`（1 passed） | `gates/V8.log`；`tests/integration/jobs/test_lease.py` |
| ③ 失效 token 提交：`attempt=? AND lease_token=?` 不匹配→`rowcount=0` 拒提交、原状态与 `revision` 不变 | `V8-3` rc=0：`test_expired_lease_token_commit_rejected`（1 passed） | `gates/V8.log`；`job-states.md`（有效 token 路径的正向对照＝T3/T5 快照的 attempt+token 谓词列值） |
| ④ 运行中断：`FixedClock` 推过 `lease_until`→TX7 记 `FAILED`＋`issues[0].code=JOB_INTERRUPTED`，T9 重试得一次可见结果 | `V8-4` rc=0：`test_interrupted_job_marked_job_interrupted`；＋本棒活链路：推 31s>TTL30→`@@@REAP {"interrupted": 1, "cancelled": 1}`，T7 快照 `problem_json`＝INTERNAL_ERROR/status=500/`issues[0].code=JOB_INTERRUPTED`（JOB_INTERRUPTED 未进 Problem.code，A88③）；T9 `retryJob` 202 新行（`retry_of` 指回源） | `gates/V8.log`；`job-states.md` T7/T9 节；`http/retryJob-202.json` |
| ⑤ 取消／完成争用：先 `COMMIT` 者定终态、终态重复查询逐字节一致；取消排队 T2／运行中取消 T4／原子提交后取消 409 `STATE_CONFLICT` 三者分别落测 | `V8-5a` rc=0（`test_cancel_vs_complete_first_commit_wins`，2 参数例＝先提交者定终态）；`V8-5b` rc=0（T2/T4 参数例）；`V8-5c` rc=0（HTTP 排队取消 200）；本棒活采集：T2＝`http/cancelJob-200.json`（got=200）、T4＝`job-states.md` T4 节内联 200 体（state=CANCEL_REQUESTED）、提交后取消＝`http/cancelJob-409.json`（got=409，code=STATE_CONFLICT）；逐字节一致由 `test_get_job_200_with_etag_and_repeat_identical` 钉住 | `gates/V8.log`；`job-states.md` ⑤ 指针节；`http/cancelJob-200.json`、`http/cancelJob-409.json`；`tests/integration/jobs/test_jobs_router_s4.py` |

支撑面（同一实测批）：T1–T9 全迁移快照对见 `job-states.md`；V2 目录关键字面 rc=0 且 collect-only
实证参数 id 覆盖 `T1…T9` 每条 ≥1（逐字清单见 `commands-s8.md` §3）；错误码全部取自已注册
`domain/errors.py::PROBLEM_CODES`（D-019，无发明码）。

## AC-031（`spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md:39`）

**判定（口径固定，本卡不出 PASS/FAIL）：写入侧前提已交付 ＋ 判定归 M5-01（`primary_owner = M5-01`）。**

写入侧前提四项（实测指针）：

1. `verify_artifact_index()` 在正常库（真实 T5 写入链：`claim→begin→commit→succeed`）上返回 `[]`
   ——`gates/V9.log` `@@@V9 healthy-db verify_artifact_index -> []`。
2. 注入「删一个被引用制品」后返回**可定位**差异：`reason=MISSING_FILE`＋
   `workspace_id`/`artifact_id`/`relative_path`/`expected_sha256` 四要素齐、`actual_sha256=None`
   ——`gates/V9.log` `@@@V9 injected ...`／`@@@V9 LOCATABLE`。差异清单非空即「阻止错误切换」所依据的
   阻断信号；**守卫消费方（备份/提升流程）的接线与端到端判定归 M5-01**（本卡无既有消费面，
   实测面见 `commands-s8.md` §5 末段；该事实已按口径报 U，见回执）。
3. `manifest_rows()` 提供 SHA 清单来源（被引用制品的清单行与索引同值）
   ——`gates/V9.log` `@@@V9 manifest_rows -> [...]`（1 行，sha 与落盘文件自算摘要一致）。
4. `verify_same_filesystem()` 保证原子重命名前提（同盘断言通过；跨设备在进程启动/提交即拒）
   ——`gates/V9.log` `@@@V9 verify_same_filesystem: OK`；写入侧行为面另有既有集成面
   `tests/integration/jobs/test_artifact_write.py`（`V4` 目录关键字实测，rc=0）。

「停受理备份＋恢复至新目录＋运行迁移校核」的端到端复跑与 AC-031 判定**归 M5-01 负责**；
本件不引用其任何尚未存在的落点路径（PRE-28）。

## 交叉指针

- 任务小结：`evidence/M0/summaries/M0-04.md`（同批新建，已在台账 `forward_reference_registry` 登记、本棒闭合）。
- 命令台账：`commands-s8.md`（A253：非 `commands.md`，后者属 S3 证据面，本棒禁改写）。
