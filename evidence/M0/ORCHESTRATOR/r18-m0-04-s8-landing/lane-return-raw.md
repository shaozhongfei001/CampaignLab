# M0-04/S8 · lane 回执原文（**逐字保留，禁删改**；D-011 append-only 口径）

> 采集时点：Round 18 · lane `S8`（昵称 **Planck** · agent_id `01a1e0b9-916a-7ac0-9318-e10f8be00768` ·
> 档位 `qwen3.8-flash` / reasoning `medium` / 预算 9k / loop 上限 2）。
> 派单文：`orchestrator/handoff/R18-lane-M0-04-S8.md`（sha256[:12] `99722f3d4ecd`）。
> 本件是 lane 通过 `spawn_agent` 通道回传的**原始文本**，编排器未做任何润色、删节或改写；
> 编排器的独立复验结论见同目录 `00-index.md`（**禁采信本件自报**，PRE-29）。

## 回执正文

```text
RESULT: DONE
LOOP_USED: 2/2

FILES_NEW（路径 · 行数(wc -l) · 字节 · sha256[:12]）：
  evidence/M0/M0-04/commands-s8.md · 682 · 33034 · 653cc29d980e
  evidence/M0/M0-04/ac.md · 53 · 5565 · 832679d66274
  evidence/M0/M0-04/job-states.md · 582 · 21463 · 0d84c90542ec
  evidence/M0/M0-04/gates/V1.log · 6 · 331 · bf7f5757a6fe
  evidence/M0/M0-04/gates/V2.log · 13 · 827 · 835f6327ee93
  evidence/M0/M0-04/gates/V3.log · 13 · 819 · 82d5eea17c9a
  evidence/M0/M0-04/gates/V4.log · 13 · 823 · 150d8370b6c4
  evidence/M0/M0-04/gates/V5.log · 7 · 305 · 73026e7a042c
  evidence/M0/M0-04/gates/V6.log · 49 · 2987 · a0f20510714a
  evidence/M0/M0-04/gates/V7.log · 6 · 281 · feed9aa2838c
  evidence/M0/M0-04/gates/V8.log · 147 · 8083 · 7044f493f827
  evidence/M0/M0-04/gates/V9.log · 37 · 3470 · 580636291d05
  evidence/M0/M0-04/http/listJobs.json · 0(单行无换行) · 927 · 66bbe5754511
  evidence/M0/M0-04/http/getJob.json · 0 · 296 · c0bd18d44a34
  evidence/M0/M0-04/http/cancelJob-200.json · 0 · 297 · 51f0689a3b5a
  evidence/M0/M0-04/http/cancelJob-409.json · 0 · 248 · 6df6b49f6bac
  evidence/M0/M0-04/http/cancelJob-412.json · 0 · 229 · 65c2f7c5a3fd
  evidence/M0/M0-04/http/cancelJob-428.json · 0 · 245 · d9686d113283
  evidence/M0/M0-04/http/retryJob-202.json · 0 · 327 · 305bbb8926d3
  evidence/M0/M0-04/http/retryJob-429.json · 0 · 305 · 07afd740f7c7
  evidence/M0/M0-04/http/problem-404.json · 0 · 254 · a8d41d2445ad
  evidence/M0/M0-04/http/problem-422.json · 0 · 360 · 225adf278af5
  evidence/M0/M0-04/http/problem-500.json · 0 · 230 · 1cac23746307
  evidence/M0/summaries/M0-04.md · 15 · 2498 · 1547f357dd80

FILES_MODIFIED: 空（git status 实测：已跟踪件改动数=0；仅上述 6 个未跟踪新增路径，全部在 §1 闭集内）

V1..V9（命令原文 · rc · 关键输出末行）：
  V1  uv run --no-sync python -c "import hashlib,pathlib;d=pathlib.Path('contracts/openapi.json').read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))" · rc=0 · 末行 `592571099d638251 443309`（＝台账 live_openapi_sha16/live_openapi_bytes 现值，逐字命中）
  V2  uv run --no-sync pytest -q tests/integration/jobs -k state_machine · rc=0 · `13 passed, 85 deselected`（目录关键字口径·含既有用例；参数面 T1–T9 每条≥1 由 collect-only 实证，见 commands-s8.md §3）
  V3  uv run --no-sync pytest -q tests/integration/jobs -k lease · rc=0 · `14 passed, 84 deselected`
  V4  uv run --no-sync pytest -q tests/integration/jobs -k artifact · rc=0 · `19 passed, 79 deselected`
  V5  uv run --no-sync pytest -q tests/unit/test_job_dto.py · rc=0 · `66 passed in 0.45s`
  V6  ruff check . / ruff format --check . / mypy / pytest -q · rc=0/0/0/0 · `All checks passed!`／`317 files already formatted`／`Success: no issues found in 112 source files`／`748 passed, 6 warnings in 160.91s (0:02:40)`（分母均＝台账现值；本棒新 4 件 md 落盘后复跑 format --check 实测 `321 files already formatted` rc=0，供编排器 run_commit 对账）
  V7  uv run --no-sync python scripts/check_contracts.py check --validate · rc=0 · `CONTRACT CHECK PASS 登记项=13 实测差异=13 元校验=6`（＝counts.contract_registered_nodes 现值 13，未变）
  V8  ①test_idempotency.py(3 passed) ②test_two_claimers_only_one_wins ③test_expired_lease_token_commit_rejected ④test_interrupted_job_marked_job_interrupted ⑤test_cancel_vs_complete_first_commit_wins(2 passed)＋state_machine -k "T2 or T4 or t2 or t4"(2 passed)＋HTTP 排队取消 200；逐条命令原文见 gates/V8.log 头部 · rc 全 0
  V9  pytest …test_verify_artifact_index_detects_missing_file · rc=0 · `1 passed`；＋活链路取证器 rc=0 · 末行 `@@@V9_DONE`（正常库 []；注入缺件→MISSING_FILE 四要素可定位；判定归 M5-01，本卡无结论）

SUMMARY_LINES: 15（≤30 达标）

AC029_VERDICT: PASS —— 依据＝design §7/派单文 §5 ①–⑤ 冻结口径逐条对上本棒实测（V8 各条 rc=0 ＋ 本棒活链路补充）；证据指针：gates/V8.log、job-states.md（T7 中断快照 REAP={"interrupted":1,"cancelled":1}＋problem_json INTERNAL_ERROR/500/issues[0].code=JOB_INTERRUPTED；T2/T4/⑤三点位）、http/retryJob-202.json（重试可见新行 retry_of 指回源）、http/cancelJob-409.json（got=409 STATE_CONFLICT）、http/cancelJob-200.json、tests/integration/jobs/{test_idempotency,test_lease,test_state_machine,test_jobs_router_s4}.py 具名用例。实测与冻结口径无任何不符。

AC031_STATEMENT: 写入侧前提已交付 ＋ 判定归 M5-01（primary_owner=M5-01）。四项前提＝verify_artifact_index()[]（gates/V9.log）、缺件可定位差异且阻断信号可产出（gates/V9.log MISSING_FILE 四要素）、manifest_rows() 清单来源（gates/V9.log）、verify_same_filesystem() 同盘前提（gates/V9.log）。无 PASS/FAIL 字样；未引用 M5 任何未存在路径（PRE-28）。

U_ITEMS:
  U-1「切换守卫阻断」的消费面不在现存 src 面。现象：V9 期望原文含「且切换守卫阻断」，但实测（grep 全 src/scripts）`verify_artifact_index` 无任何消费者，`worker/integrity.py:4` 自述「判定归 M5-01，本模块只交付那把尺子」。命令原文：见 gates/V9.log V9-2 ＋ commands-s8.md §5。实测事实：注入缺件后差异清单非空且逐字段可定位（＝守卫据以阻断的信号已可产出）；「阻断动作」主体（备份/提升接线）在 M0-04 面上不存在。候选处置：(a) 维持现状——信号面＝写入侧前提，阻断接线归 M5-01（与 §4 V9「判定归 M5-01，本卡不出结论」自洽）；(b) 编排器为 M0 出口补一个消费面锚点。倾向：(a)。

SELF_REPORTED_DEVIATIONS:
  1) HEAD 漂移：§0 记 `f105061`，开工实测 `67ba545`（＝本派单文 predispatch 入库提交，§0 的 316/202 为入库前值），gate 期间编排器又落纯台账回填 `f53ff8d`（agent_id 登记，零代码/契约改动；环境行如实记录）。§0 旧基线特征 311/110/738 未出现；一切比对按台账现值（317/112/748/13）。
  2) 本机 WSL `/tmp` 在会话间被回收 ⇒ 首跑 manifest 丢失；辅证两条（COLL/SV2）改以**同逐字命令**重跑并持久化到仓库外工作区工具面（`/mnt/d/ws/codex_rd/ss_campaignlab/_tools/`，源文件全文＋sha256[:12] 已逐字嵌入 commands-s8.md §7）。V1–V9 主日志落仓库盘未受影响。
  3) job-states.md 的「触发该迁移的 HTTP 样本」口径：T1/T3/T5/T6/T7/T8 为 worker 侧事务、**无 HTTP 触发面**，逐字写明并以迁移前后全行快照为见证；T4 有 HTTP 面但 11 件文件名闭集无第二个 200 位，故实跑响应体逐字内联于 job-states.md（非编造，同一采集批）。
  4) http/*.json 内容为**纯响应体逐字**（§3「真实响应体」），状态码/响应头不内嵌——由文件名位＋commands-s8.md §4 采集报告行（expect/got 逐条 got==expect、fails=[]）承载。
  5) 轮内修正两处（如实报）：problem-500 采集初跑 rc=1（TestClient 默认 raise_server_exceptions=True 把 ServerError 重抛）⇒ 改按既有冻结面 `tests/unit/test_api_app.py` 同口径 `raise_server_exceptions=False` 后 rc=0；台账构建器 env 行截取 bug（丢 `uv` 前缀）已修复并重建。
  6) 500 的真实触发面＝`create_app` 未注入 `health_service` → deps 显式 RuntimeError → 500 Problem（既有行为，`tests/unit/test_api_app.py` 钉死）；jobs 路由面上现存代码无法真实触发 500（未伪造、未改期望）。
  7) 本棒零新增仓库内 .py；.log/.json 不入 RUFF_SUFFIXES 分母（§0 口径）；4 件新 md 已实测通过 ruff check/format --check 全树 rc=0。

TOKEN_USAGE: 未报 —— 成因：本运行环境（Qwen3.8 宿主会话）未向 agent 暴露任何 token 计数接口或读数面板，无法给出可复核的实际用量或区间；按 §8 括注要求逐字报「未报」并说明成因，不以任何推算冒充实测值。

TIER_CONFIRM: model=qwen3.8, reasoning=未报（运行时未暴露本会话的档位细分与 reasoning 参数；派单文档位为 qwen3.8-flash/medium，此为卡面记录而非本会话可自证值）
```

## lane 的补充说明（原文）

- 仓库：`/home/szf/dev/CampaignLab`，分支 `m0-framework`；本棒未执行任何 git 写操作，
  未触碰台账 `orchestrator/state.json`（只读）。
- 11/11 HTTP 样本为实跑采集（装配面复用 S4 冻结 `Harness`，时钟只经 `FixedClock`，
  全棒无 `sleep`/墙钟判定），`Problem.code` 全部属已注册 20 码（终验脚本复核通过）。
- 复核抓手：`evidence/M0/M0-04/commands-s8.md`（四元组台账＋PRE-29 口径声明＋附录工具件逐字源码与 sha）；
  `evidence/M0/M0-04/job-states.md`（T1–T9 快照对由构建器从 `collect.log` 逐字机械提取，无手抄数字）。
