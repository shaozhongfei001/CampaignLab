# M0-04 / S8 · 纯取证棒 · V1–V9 命令台账（gate 四元组）

- 生成方式：构建器机械提取自 `gates/V*.log` 实测原文（无手抄数字）· 构建时刻 2026-11-16T04:02:24+08:00
- 环境行（全部条目同源）：`uv 0.13.7 / CPython 3.14.10 x86_64 Linux / HEAD=f53ff8d / cwd=/home/szf/dev/CampaignLab`
- 命令口径：§4 表**逐字**（PRE-29）；V8=design §7 ①–⑤ 逐条；台账 counts 为**现值**，本文不写死分母（D-012/D-014）。
- 落点裁定 **A253**：design §9 的 `commands.md` 已被 S3 占用（禁改写）⇒ 本件为 S8 台账，命名与同目录 `commands-s2b1/s2b2/s2b3/s2c/s4/s7` 先例同型。
- 基线说明：派单文 §0 记 HEAD `f105061`；开工实测 `67ba545`（= 本派单文的 predispatch 入库提交），gate 执行期间编排器又落纯台账回填 `f53ff8d`（agent_id 登记，零代码/契约改动）。counts 冻结三项（py/mypy/pytest）实测未变（见 V6）。**无 311/110/738 旧基线特征**。
- 环境注意：本机 WSL `/tmp` 在会话间被回收 ⇒ COLL/SV2 两条辅证在 V1–V9 完成后以**同逐字命令**独立补跑（rc 如实记录）；V1–V9 主日志不受影响。

## 1. V1–V9 四元组（命令 · rc · 时间戳 · 环境行见上）

### V1 · 切片新鲜度

| 条目 | 时间戳 | rc | 关键输出末行 |
|---|---|---|---|
| `V1` | 2026-11-16T03:54:31+08:00 | 0 | `592571099d638251 443309` |

命令原文：

```text
uv run --no-sync python -c "import hashlib,pathlib;d=pathlib.Path('contracts/openapi.json').read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))"
```

### V2 · 状态机（目录关键字过滤口径，collected 含既有用例，禁推算增量）

| 条目 | 时间戳 | rc | 关键输出末行 |
|---|---|---|---|
| `V2` | 2026-11-16T03:54:31+08:00 | 0 | `13 passed, 85 deselected, 1 warning in 9.78s` |

命令原文：

```text
uv run --no-sync pytest -q tests/integration/jobs -k state_machine
```

### V3 · 租约与争用（同上口径）

| 条目 | 时间戳 | rc | 关键输出末行 |
|---|---|---|---|
| `V3` | 2026-11-16T03:54:43+08:00 | 0 | `14 passed, 84 deselected, 1 warning in 8.80s` |

命令原文：

```text
uv run --no-sync pytest -q tests/integration/jobs -k lease
```

### V4 · 原子制品（同上口径）

| 条目 | 时间戳 | rc | 关键输出末行 |
|---|---|---|---|
| `V4` | 2026-11-16T03:54:51+08:00 | 0 | `19 passed, 79 deselected, 1 warning in 10.69s` |

命令原文：

```text
uv run --no-sync pytest -q tests/integration/jobs -k artifact
```

### V5 · Job DTO 单测

| 条目 | 时间戳 | rc | 关键输出末行 |
|---|---|---|---|
| `V5` | 2026-11-16T03:55:03+08:00 | 0 | `66 passed in 0.45s` |

命令原文：

```text
uv run --no-sync pytest -q tests/unit/test_job_dto.py
```

### V6 · 质量门四连（check / format --check / mypy / pytest 全量）

| 条目 | 时间戳 | rc | 关键输出末行 |
|---|---|---|---|
| `V6a` | 2026-11-16T03:55:04+08:00 | 0 | `All checks passed!` |
| `V6b` | 2026-11-16T03:55:05+08:00 | 0 | `317 files already formatted` |
| `V6c` | 2026-11-16T03:55:05+08:00 | 0 | `Success: no issues found in 112 source files` |
| `V6d` | 2026-11-16T03:55:05+08:00 | 0 | `748 passed, 6 warnings in 160.91s (0:02:40)` |

命令原文：

```text
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy
uv run --no-sync pytest -q
```

### V7 · 契约门禁未回归

| 条目 | 时间戳 | rc | 关键输出末行 |
|---|---|---|---|
| `V7` | 2026-11-16T03:57:42+08:00 | 0 | `CONTRACT CHECK PASS 登记项=13 实测差异=13 元校验=6` |

命令原文：

```text
uv run --no-sync python scripts/check_contracts.py check --validate
```

### V8 · AC-029 边界 ①–⑤ 逐条（design §7 原文口径）

| 条目 | 时间戳 | rc | 关键输出末行 |
|---|---|---|---|
| `V8-1` | 2026-11-16T03:57:43+08:00 | 0 | `========================= 3 passed, 1 warning in 1.52s =========================` |
| `V8-2` | 2026-11-16T03:57:46+08:00 | 0 | `========================= 1 passed, 1 warning in 0.51s =========================` |
| `V8-3` | 2026-11-16T03:57:48+08:00 | 0 | `========================= 1 passed, 1 warning in 0.54s =========================` |
| `V8-4` | 2026-11-16T03:57:49+08:00 | 0 | `========================= 1 passed, 1 warning in 0.50s =========================` |
| `V8-5a` | 2026-11-16T03:57:51+08:00 | 0 | `========================= 2 passed, 1 warning in 1.06s =========================` |
| `V8-5b` | 2026-11-16T03:57:53+08:00 | 0 | `================= 2 passed, 11 deselected, 1 warning in 1.06s ==================` |
| `V8-5c` | 2026-11-16T03:57:55+08:00 | 0 | `========================= 1 passed, 1 warning in 0.62s =========================` |

命令原文：

```text
uv run --no-sync pytest -q tests/integration/jobs/test_idempotency.py -v
uv run --no-sync pytest -q tests/integration/jobs/test_lease.py::test_two_claimers_only_one_wins -v
uv run --no-sync pytest -q tests/integration/jobs/test_lease.py::test_expired_lease_token_commit_rejected -v
uv run --no-sync pytest -q tests/integration/jobs/test_lease.py::test_interrupted_job_marked_job_interrupted -v
uv run --no-sync pytest -q tests/integration/jobs/test_lease.py::test_cancel_vs_complete_first_commit_wins -v
uv run --no-sync pytest -q tests/integration/jobs/test_state_machine.py -k "T2 or T4 or t2 or t4" -v
uv run --no-sync pytest -q "tests/integration/jobs/test_jobs_router_s4.py::test_cancel_job_queued_becomes_cancelled_200" -v
```

### V9 · AC-031 写入侧前提（判定归 M5-01）

| 条目 | 时间戳 | rc | 关键输出末行 |
|---|---|---|---|
| `V9-1` | 2026-11-16T03:57:57+08:00 | 0 | `========================= 1 passed, 1 warning in 0.57s =========================` |
| `V9-2` | 2026-11-16T03:57:59+08:00 | 0 | `@@@V9_DONE` |

命令原文：

```text
uv run --no-sync pytest -q tests/integration/jobs/test_artifact.py::test_verify_artifact_index_detects_missing_file -v
uv run --no-sync python /mnt/d/ws/codex_rd/ss_campaignlab/_tools/v9_integrity.py
```

期望比对（台账现值口径）：V1 输出须等于 `counts.live_openapi_sha16`/`.live_openapi_bytes` **现值**；
V6 分母等于 `counts.ruff_formatted_files`/`.mypy_source_files`/`.pytest_passed` **现值**；V7 登记项数等于 `counts.contract_registered_nodes` **现值**。
以上比对由回执侧读台账现值进行，本文只贴实测输出原文（禁写死分母）。

## 2. V8 ①–⑤ → 条目映射（design §7 逐字边界项）

| 边界项 | 取证条目 | 补充实测 |
|---|---|---|
| ① 同键同请求重放／异请求 409 | `V8-1`（test_idempotency 3 例：same_key_same_request_same_object / same_key_different_request_409 / replay_body_byte_identical） | — |
| ② 两执行者争用一方 `LeaseLost` | `V8-2` | — |
| ③ 失效 token 提交 rowcount=0 拒提交 | `V8-3` | — |
| ④ 中断 `JOB_INTERRUPTED`＋T9 重试可见 | `V8-4` | 本棒活链路实测：`job-states.md` T7（REAP interrupted=1，problem.code=INTERNAL_ERROR/status=500/issues[0]=JOB_INTERRUPTED）＋ T9（retryJob 202 新行） |
| ⑤ 取消／完成先提交者定终态 | `V8-5a`（2 参数例）＋ `V8-5b`（T2/T4）＋ `V8-5c`（HTTP 排队取消 200） | 原子提交后取消 → 409 `STATE_CONFLICT` 实测样本 `http/cancelJob-409.json`（本棒活采集，got=409） |

## 3. V2 参数面 T1–T9 覆盖实证（collect-only 逐字）

辅证命令（非 §4 表内件，目录级 collected 与逐字参数一览）：

```text
uv run --no-sync pytest tests/integration/jobs/test_state_machine.py --collect-only -q
```

实测参数 id（每条 T1–T9 均 ≥1，逐字）：

```text
tests/integration/jobs/test_state_machine.py::test_t1_claim_queued_to_running[T1-earliest-queued-first]
tests/integration/jobs/test_state_machine.py::test_t2_cancel_queued_to_cancelled[T2-queued-direct-cancelled]
tests/integration/jobs/test_state_machine.py::test_t3_renew_keeps_running_and_extends_lease[T3-renew-extends-lease]
tests/integration/jobs/test_state_machine.py::test_t3_renew_keeps_running_and_extends_lease[T3-stale-lease-rejected]
tests/integration/jobs/test_state_machine.py::test_t4_running_to_cancel_requested[T4-running-cancel-keeps-lease]
tests/integration/jobs/test_state_machine.py::test_t5_succeed_with_valid_lease[T5-valid-lease-succeeds]
tests/integration/jobs/test_state_machine.py::test_t6_fail_known_problem[T6-retryable-internal-error]
tests/integration/jobs/test_state_machine.py::test_t6_fail_known_problem[T6-permanent-validation-error]
tests/integration/jobs/test_state_machine.py::test_t7_reap_expired_running_to_failed[T7-lease-expiry-reap]
tests/integration/jobs/test_state_machine.py::test_t8_cancel_requested_to_cancelled[T8-executor-confirm]
tests/integration/jobs/test_state_machine.py::test_t8_cancel_requested_to_cancelled[T8-expiry-reap]
tests/integration/jobs/test_state_machine.py::test_t9_retry_creates_new_queued[T9-retry-from-failed]
tests/integration/jobs/test_state_machine.py::test_t9_retry_creates_new_queued[T9-retry-from-cancelled]
```

（`82afaa9352ff` 为该实测件 sha256[:12]；命令 rc=0，13 tests collected，与 V2 `13 passed` 同数）

## 4. HTTP 样本采集（design §9-S8 行 11 件 · 实跑非手写）

```text
uv run --no-sync python /mnt/d/ws/codex_rd/ss_campaignlab/_tools/collect_s8.py
```

采集报告（逐字取自本次实测 stdout；expect=派单文 §1 文件名编码的状态码，got=真实响应）：

```text
@@@HTTP cancelJob-200.json expect=200 got=200 bytes=297 headers={"ETag": "\"2\"", "Content-Type": "application/json", "X-Request-Id": "0a10bc79133944ae8e9065dadfe7f896"}
@@@HTTP retryJob-202.json expect=202 got=202 bytes=327 headers={"ETag": "\"1\"", "Location": "/api/v1/workspaces/ws-s8/jobs/J-3f77ad99aeb24fc5afc92215ff335f32", "Content-Type": "application/json", "X-Request-Id": "d5988c05817547389638e0cf832a4064"}
@@@HTTP listJobs.json expect=200 got=200 bytes=927 headers={"Content-Type": "application/json", "X-Request-Id": "9594c537971b4c55af1a0fffa3603d64"}
@@@HTTP getJob.json expect=200 got=200 bytes=296 headers={"ETag": "\"1\"", "Content-Type": "application/json", "X-Request-Id": "0076e33a06944bda91da95a8aae7a735"}
@@@HTTP problem-404.json expect=404 got=404 bytes=254 headers={"Content-Type": "application/problem+json", "X-Request-Id": "ad954797cffc4d7fa5249572a331f231"}
@@@HTTP problem-422.json expect=422 got=422 bytes=360 headers={"Content-Type": "application/problem+json", "X-Request-Id": "9196e5bbf95b4b71b44647630ffacdab"}
@@@HTTP cancelJob-412.json expect=412 got=412 bytes=229 headers={"Content-Type": "application/problem+json", "X-Request-Id": "9ec43ad5c8034d82b751e7db9d120c29"}
@@@HTTP cancelJob-428.json expect=428 got=428 bytes=245 headers={"Content-Type": "application/problem+json", "X-Request-Id": "61b31174120c45bba5337855cc8fa97c"}
@@@HTTP cancelJob-409.json expect=409 got=409 bytes=248 headers={"Content-Type": "application/problem+json", "X-Request-Id": "61cd81e73a264a4d9db7bf773332193f"}
@@@HTTP retryJob-429.json expect=429 got=429 bytes=305 headers={"Retry-After": "3", "Content-Type": "application/problem+json", "X-Request-Id": "ead0b434a164431d8c7a480db4c2ac3d"}
@@@HTTP problem-500.json expect=500 got=500 bytes=230 headers={"Content-Type": "application/problem+json", "X-Request-Id": "c008536fcf514e70ac4b42863bce7119"}
@@@COLLECT_DONE fails=[]
```

采集器源文件 sha256[:12]=`186a75f6ad8d`（**11/11 got==expect、fails=[]、rc=0**）。
装配面逐字复用 `tests/integration/jobs/test_jobs_router_s4.py::Harness`（S4 冻结面）；`problem-500` 触发面＝`create_app` 未注入 `health_service` → `api/deps.py` 显式 `RuntimeError` → 500 Problem（既有冻结行为，`tests/unit/test_api_app.py` 钉死；TestClient 口径与该既有件一致 `raise_server_exceptions=False`）。

## 5. V9 写入侧前提实测（逐字）

```text
uv run --no-sync python /mnt/d/ws/codex_rd/ss_campaignlab/_tools/v9_integrity.py
```

@@@ 报告行（原文见 `gates/V9.log`）：

```text
@@@V9 verify_same_filesystem: OK（同盘前提成立）
@@@V9 committed={"workspace_id": "ws-s9", "artifact_id": "art-b3cd46157b584e49bf2e50d85f28acdb", "kind": "JOB_RESULT", "sha256": "5d1f99d6ef40743b935126ad125d8b5079033570fc35bfab973bb8341ae8bf8a", "relative_path": "results/JOB_RESULT/ws-s9/5d/5d1f99d6ef40743b935126ad125d8b5079033570fc35bfab973bb8341ae8bf8a", "byte_size": 24, "path": "/tmp/s8-v9-j6_1i0n3/results/JOB_RESULT/ws-s9/5d/5d1f99d6ef40743b935126ad125d8b5079033570fc35bfab973bb8341ae8bf8a", "reused_file": false, "reused_row": false}
@@@V9 healthy-db verify_artifact_index -> []
@@@V9 manifest_rows -> [{"workspace_id": "ws-s9", "artifact_id": "art-b3cd46157b584e49bf2e50d85f28acdb", "kind": "JOB_RESULT", "sha256": "5d1f99d6ef40743b935126ad125d8b5079033570fc35bfab973bb8341ae8bf8a", "relative_path": "results/JOB_RESULT/ws-s9/5d/5d1f99d6ef40743b935126ad125d8b5079033570fc35bfab973bb8341ae8bf8a", "byte_size": 24, "created_at": "2026-11-13T01:00:00+00:00"}]
@@@V9 inject: unlink referenced artifact /tmp/s8-v9-j6_1i0n3/results/JOB_RESULT/ws-s9/5d/5d1f99d6ef40743b935126ad125d8b5079033570fc35bfab973bb8341ae8bf8a
@@@V9 injected verify_artifact_index -> [{"workspace_id": "ws-s9", "artifact_id": "art-b3cd46157b584e49bf2e50d85f28acdb", "relative_path": "results/JOB_RESULT/ws-s9/5d/5d1f99d6ef40743b935126ad125d8b5079033570fc35bfab973bb8341ae8bf8a", "expected_sha256": "5d1f99d6ef40743b935126ad125d8b5079033570fc35bfab973bb8341ae8bf8a", "actual_sha256": null, "reason": "MISSING_FILE", "expected_byte_size": null, "actual_byte_size": null}]
@@@V9 LOCATABLE: 差异含 workspace_id/artifact_id/relative_path/expected_sha256 四要素，可定位到该制品
@@@V9 GUARD_SIGNAL: discrepancies 非空（1 条）即切换守卫的阻断信号；判定归 M5-01，本件不出结论
@@@V9_DONE
```

V9 取证器源文件 sha256[:12]=`3f84fbab1f37`。**判定归 M5-01，本台账不出 AC-031 结论**；`切换守卫` 的 src 侧消费面（备份/提升流程）尚不存在（实测 grep：`verify_artifact_index` 的消费者仅在 `worker/integrity.py` 自身文档面），差异清单非空即守卫可依据的阻断信号——该事实如实登记，见回执 U/偏差面。

## 6. 写权与红线自证

- 本棒对仓库**只新建**派单文 §1 闭集路径（`commands-s8.md`/`ac.md`/`job-states.md`/`gates/V1–V9.log`/`http/*.json`/`summaries/M0-04.md`），**零修改件**（回执 FILES_MODIFIED 空；git 状态由编排器复核）。
- 本棒未新增任何仓库内 `.py`（采集器/构建器均为仓库外工作区工具件，已在本节留 sha 供复核）⇒ counts 的 py/mypy/pytest 三项不变；`in_scope_md` 因本批 md 增长属预期（.log/.json 不入 `RUFF_SUFFIXES` 分母）。
- 禁 git 写操作：遵守（本棒仅只读 git 命令）；台账 `orchestrator/state.json` 只读。
- 时钟：推进一律 `FixedClock`（见 `job-states.md` T3/T7/T8x 快照的 `lease_until` 与推进量），全棒无 `sleep`/`time.monotonic` 判定。

## 7. 附录 · 工具件逐字源码

### cmds.tsv（sha256[:12]=`f05076066f97`）

```text
V1|V1.log|uv run --no-sync python -c "import hashlib,pathlib;d=pathlib.Path('contracts/openapi.json').read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))"
V2|V2.log|uv run --no-sync pytest -q tests/integration/jobs -k state_machine
V3|V3.log|uv run --no-sync pytest -q tests/integration/jobs -k lease
V4|V4.log|uv run --no-sync pytest -q tests/integration/jobs -k artifact
V5|V5.log|uv run --no-sync pytest -q tests/unit/test_job_dto.py
V6a|V6.log|uv run --no-sync ruff check .
V6b|V6.log|uv run --no-sync ruff format --check .
V6c|V6.log|uv run --no-sync mypy
V6d|V6.log|uv run --no-sync pytest -q
V7|V7.log|uv run --no-sync python scripts/check_contracts.py check --validate
V8-1|V8.log|uv run --no-sync pytest -q tests/integration/jobs/test_idempotency.py -v
V8-2|V8.log|uv run --no-sync pytest -q tests/integration/jobs/test_lease.py::test_two_claimers_only_one_wins -v
V8-3|V8.log|uv run --no-sync pytest -q tests/integration/jobs/test_lease.py::test_expired_lease_token_commit_rejected -v
V8-4|V8.log|uv run --no-sync pytest -q tests/integration/jobs/test_lease.py::test_interrupted_job_marked_job_interrupted -v
V8-5a|V8.log|uv run --no-sync pytest -q tests/integration/jobs/test_lease.py::test_cancel_vs_complete_first_commit_wins -v
V8-5b|V8.log|uv run --no-sync pytest -q tests/integration/jobs/test_state_machine.py -k "T2 or T4 or t2 or t4" -v
V8-5c|V8.log|uv run --no-sync pytest -q "tests/integration/jobs/test_jobs_router_s4.py::test_cancel_job_queued_becomes_cancelled_200" -v
V9-1|V9.log|uv run --no-sync pytest -q tests/integration/jobs/test_artifact.py::test_verify_artifact_index_detects_missing_file -v
V9-2|V9.log|uv run --no-sync python /mnt/d/ws/codex_rd/ss_campaignlab/_tools/v9_integrity.py
SV2|/tmp/s8_r18/sv2.log|uv run --no-sync pytest tests/integration/jobs/test_state_machine.py --collect-only -q
COLL|/tmp/s8_r18/collect.log|uv run --no-sync python /mnt/d/ws/codex_rd/ss_campaignlab/_tools/collect_s8.py
```

### run_gates.sh（sha256[:12]=`112213ff8e2c`）

```text
#!/usr/bin/env bash
# R18 S8 · gate runner（工具脚本，不在仓库内；逐条执行 cmds.tsv 的逐字命令并落盘原始输出）
set -u
export PATH="$HOME/.local/bin:$PATH"
REPO=/home/szf/dev/CampaignLab
TOOLS=/mnt/d/ws/codex_rd/ss_campaignlab/_tools
cd "$REPO"
WORK=/tmp/s8_r18
rm -rf "$WORK"; mkdir -p "$WORK/parts"
GATES="$REPO/evidence/M0/M0-04/gates"
HTTPD="$REPO/evidence/M0/M0-04/http"
mkdir -p "$GATES" "$HTTPD"
PYV=$(uv run --no-sync python -c "import sys,platform;print('CPython',sys.version.split()[0],platform.machine(),platform.system())")
ENVLINE="uv $(uv --version | awk '{print $2}') / ${PYV} / HEAD=$(git rev-parse --short HEAD) / cwd=$REPO"
MAN="$WORK/manifest.txt"; : > "$MAN"
declare -A SEEN
while IFS='|' read -r id log cmd; do
  [ -z "${id:-}" ] && continue
  case "$log" in
    /*) tgt="$log" ;;
    *)  tgt="$WORK/parts/$log" ;;
  esac
  if [ -z "${SEEN[$log]:-}" ]; then SEEN[$log]=1; : > "$tgt"; fi
  ts=$(date -Iseconds)
  { echo "### id=$id"; echo "\$ $cmd"; echo "# ts=$ts"; echo "# env=$ENVLINE"; } >> "$tgt"
  bash -c "$cmd" >> "$tgt" 2>&1; rc=$?
  echo "### id=$id rc=$rc" >> "$tgt"
  echo "$id|$ts|$rc|$cmd|$log" >> "$MAN"
done < "$TOOLS/cmds.tsv"
cp "$WORK"/parts/*.log "$GATES"/
echo "ALL_DONE" >> "$MAN"
```

### collect_s8.py（sha256[:12]=`186a75f6ad8d`）

```text
"""R18 M0-04/S8 · 纯取证采集器（工具件，位于仓库外，不入任何 py/mypy/pytest 分母）。

口径：装配面逐字复用 tests/integration/jobs/test_jobs_router_s4.py 的 Harness（S4 冻结装配面）；
时钟只经 FixedClock；禁 sleep／禁系统时间判定（派单文红线 3）。
输出：evidence/M0/M0-04/http/*.json（11 件真实响应体）＋ stdout 的 @@@ 行（快照与状态码报告，
供 job-states.md / commands-s8.md 逐字引用）。
"""

import dataclasses
import json
import sqlite3
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

REPO = Path("/home/szf/dev/CampaignLab")
sys.path.insert(0, str(REPO))

from campaignlab.api.common import PROBLEM_CODES, ObjectRef, Problem  # noqa: E402
from campaignlab.api.common import Issue as IssueDto  # noqa: E402
from campaignlab.config import API_PREFIX  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from campaignlab.worker.store import JobStore  # noqa: E402
from tests.integration.jobs.test_jobs_router_s4 import TEST_ORIGIN, Harness  # noqa: E402

WS = "ws-s8"
WSB = "ws-s8b"
WSC = "ws-s8c"
WSCAP = "ws-s8cap"
OUT = REPO / "evidence/M0/M0-04/http"
fails: list[str] = []


def problem(code: str, detail: str, issues: tuple = ()):
    reg = PROBLEM_CODES[code]
    return Problem(
        type=reg[1],
        title=reg[2],
        status=reg[0],
        code=code,
        detail=detail,
        issues=list(issues),
        request_id="req-s8-forensic",
    )


def main() -> int:
    tmp = tempfile.TemporaryDirectory(prefix="s8-r18-")
    h = Harness(Path(tmp.name))
    for ws in (WS, WSB, WSC, WSCAP):
        h.seed_workspace(ws)
    client = h.authed_client()
    store = JobStore(engine=h.engine)
    clock = h.clock

    def mk(ws: str, jid: str):
        return store.enqueue(
            workspace_id=ws,
            kind="VALIDATE_IMPORT",
            input_json="{}",
            input_digest="0" * 64,
            now=clock.now(),
            job_id=jid,
        )

    def jrow(ws: str, jid: str):
        conn = sqlite3.connect(h.db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM jobs WHERE workspace_id=? AND id=?", (ws, jid)
            ).fetchone()
        finally:
            conn.close()
        return dict(row) if row is not None else None

    def snap(tag: str, ws: str, jid: str) -> None:
        print(f"@@@SNAP {tag} ws={ws} job={jid}")
        print(json.dumps(jrow(ws, jid), ensure_ascii=False, sort_keys=True, default=str))

    def etag_of(ws: str, jid: str) -> str:
        r = client.get(f"{API_PREFIX}/workspaces/{ws}/jobs/{jid}")
        assert r.status_code == 200, r.text
        return r.headers["ETag"]

    def save(name: str, resp, expect: int) -> None:
        hdrs = {
            k: resp.headers[k]
            for k in ("ETag", "Location", "Retry-After", "Content-Type", "X-Request-Id")
            if k in resp.headers
        }
        print(f"@@@HTTP {name} expect={expect} got={resp.status_code} bytes={len(resp.content)} headers={json.dumps(hdrs, ensure_ascii=False)}")
        try:
            json.loads(resp.text)
        except Exception as exc:  # 非 JSON 体也是实测事实：记录并保留原文
            fails.append(f"{name}:body-not-json:{exc}")
        if resp.status_code != expect:
            fails.append(f"{name}:status {resp.status_code}!={expect}")
        (OUT / name).write_text(resp.text, encoding="utf-8")

    # ---------------- T1：认领 QUEUED→RUNNING（worker TX1，无 HTTP 触发面） ----------------
    mk(WS, "j-t1")
    snap("T1-before", WS, "j-t1")
    claim1 = store.claim_next(workspace_id=WS, now=clock.now())
    assert claim1.claimed and claim1.record is not None and claim1.record.id == "j-t1", claim1
    snap("T1-after", WS, "j-t1")

    # ---------------- T3：续租 RUNNING→RUNNING（TX2） ----------------
    clock.advance(timedelta(seconds=5))
    r3 = store.renew(claim1.lease, now=clock.now(), stage="s8-renew", progress=5)
    assert r3.renewed is True
    snap("T3-after", WS, "j-t1")

    # ---------------- T5：成功收口 RUNNING→SUCCEEDED（TX5） ----------------
    s5 = store.succeed(
        claim1.lease,
        result_ref=ObjectRef(kind="job", id="j-t1"),
        now=clock.now(),
    )
    snap("T5-after", WS, "j-t1")

    # ---------------- T2：取消排队 QUEUED→CANCELLED（HTTP cancelJob 200） ----------------
    mk(WS, "j-t2")
    snap("T2-before", WS, "j-t2")
    e2 = etag_of(WS, "j-t2")
    r2 = client.post(
        f"{API_PREFIX}/workspaces/{WS}/jobs/j-t2/cancel",
        headers={"Idempotency-Key": "s8-idem-cancel-t2", "If-Match": e2},
    )
    save("cancelJob-200.json", r2, 200)
    print(f"@@@BODY-INLINE T2-http-response-body {r2.text}")
    snap("T2-after", WS, "j-t2")

    # ---------------- T4：运行中取消 RUNNING→CANCEL_REQUESTED（HTTP cancelJob 200） ----------
    mk(WS, "j-t4")
    claim4 = store.claim_next(workspace_id=WS, now=clock.now())
    assert claim4.claimed and claim4.record is not None and claim4.record.id == "j-t4", claim4
    snap("T4-before", WS, "j-t4")
    e4 = etag_of(WS, "j-t4")
    r4 = client.post(
        f"{API_PREFIX}/workspaces/{WS}/jobs/j-t4/cancel",
        headers={"Idempotency-Key": "s8-idem-cancel-t4", "If-Match": e4},
    )
    if r4.status_code != 200:
        fails.append(f"T4-inline:status {r4.status_code}!=200")
    print(f"@@@BODY-INLINE T4-http-response-body status={r4.status_code} {r4.text}")
    snap("T4-after", WS, "j-t4")

    # ---------------- T8：取消确认 CANCEL_REQUESTED→CANCELLED（TX4，无 HTTP 触发面） --------
    c8 = store.confirm_cancel(
        claim4.lease, now=clock.now(), actor_id="s8-forensic", request_id="req-s8-t8"
    )
    snap("T8-after", WS, "j-t4")

    # ---------------- T6：已知失败 RUNNING→FAILED（TX6，无 HTTP 触发面） ------------------
    mk(WS, "j-t6")
    claim6 = store.claim_next(workspace_id=WS, now=clock.now())
    assert claim6.claimed and claim6.record is not None and claim6.record.id == "j-t6", claim6
    snap("T6-before", WS, "j-t6")
    store.fail(
        claim6.lease,
        problem=problem(
            "VALIDATION_ERROR",
            "s8 取证：未注册 kind 的桩式失败",
            (IssueDto(code="NO_HANDLER", location="/kind", message="未注册 handler", severity="ERROR"),),
        ),
        now=clock.now(),
    )
    snap("T6-after", WS, "j-t6")

    # ---------------- T7 + T8到期分支：FixedClock 推过 lease_until → reap（TX7） ----------
    mk(WS, "j-t7")
    mk(WS, "j-t8x")
    claim7 = store.claim_next(workspace_id=WS, now=clock.now())
    claim8x = store.claim_next(workspace_id=WS, now=clock.now())
    assert claim7.claimed and claim7.record is not None and claim7.record.id == "j-t7"
    assert claim8x.claimed and claim8x.record is not None and claim8x.record.id == "j-t8x"
    store.request_cancel(
        workspace_id=WS,
        job_id="j-t8x",
        revision=claim8x.record.revision,
        now=clock.now(),
        actor_id="s8-forensic",
        request_id="req-s8-t8x",
    )
    snap("T7-before", WS, "j-t7")
    snap("T8x-before", WS, "j-t8x")
    clock.advance(timedelta(seconds=31))
    reaped = store.reap_expired(now=clock.now())
    print(f"@@@REAP {json.dumps(dataclasses.asdict(reaped), ensure_ascii=False)}")
    snap("T7-after", WS, "j-t7")
    snap("T8x-after", WS, "j-t8x")

    # ---------------- T9：重试 FAILED→新 QUEUED（HTTP retryJob 202） ---------------------
    e6 = etag_of(WS, "j-t6")
    r9 = client.post(
        f"{API_PREFIX}/workspaces/{WS}/jobs/j-t6/retry",
        headers={"Idempotency-Key": "s8-idem-retry-t9", "If-Match": e6},
    )
    save("retryJob-202.json", r9, 202)
    print(f"@@@BODY-INLINE T9-http-response-body {r9.text}")
    new_id = json.loads(r9.text)["id"]
    snap("T9-after-new-row", WS, new_id)
    snap("T9-source-after", WS, "j-t6")

    # ---------------- 其余 HTTP 样本 ------------------------------------------------------
    mk(WSB, "j-list-a")
    mk(WSB, "j-list-b")
    mk(WSB, "j-get")
    save("listJobs.json", client.get(f"{API_PREFIX}/workspaces/{WSB}/jobs"), 200)
    save("getJob.json", client.get(f"{API_PREFIX}/workspaces/{WSB}/jobs/j-get"), 200)
    save("problem-404.json", client.get(f"{API_PREFIX}/workspaces/{WSB}/jobs/j-absent"), 404)
    save("problem-422.json", client.get(f"{API_PREFIX}/workspaces/{WSB}/jobs?limit=0"), 422)
    mk(WSB, "j-412")
    save(
        "cancelJob-412.json",
        client.post(
            f"{API_PREFIX}/workspaces/{WSB}/jobs/j-412/cancel",
            headers={"Idempotency-Key": "s8-idem-cancel-412", "If-Match": '"9999"'},
        ),
        412,
    )
    mk(WSB, "j-428")
    save(
        "cancelJob-428.json",
        client.post(
            f"{API_PREFIX}/workspaces/{WSB}/jobs/j-428/cancel",
            headers={"Idempotency-Key": "s8-idem-cancel-428"},
        ),
        428,
    )
    mk(WSC, "j-done")
    claimd = store.claim_next(workspace_id=WSC, now=clock.now())
    assert claimd.claimed and claimd.record is not None and claimd.record.id == "j-done"
    store.succeed(
        claimd.lease, result_ref=ObjectRef(kind="job", id="j-done"), now=clock.now()
    )
    save(
        "cancelJob-409.json",
        client.post(
            f"{API_PREFIX}/workspaces/{WSC}/jobs/j-done/cancel",
            headers={"Idempotency-Key": "s8-idem-cancel-409", "If-Match": etag_of(WSC, "j-done")},
        ),
        409,
    )
    mk(WSCAP, "j-00-src")
    for i in range(10):
        mk(WSCAP, f"j-cap-{i:02d}")
    claims = store.claim_next(workspace_id=WSCAP, now=clock.now())
    assert claims.claimed and claims.record is not None and claims.record.id == "j-00-src", claims
    store.fail(
        claims.lease,
        problem=problem("VALIDATION_ERROR", "s8 取证：容量样本的源失败"),
        now=clock.now(),
    )
    save(
        "retryJob-429.json",
        client.post(
            f"{API_PREFIX}/workspaces/{WSCAP}/jobs/j-00-src/retry",
            headers={"Idempotency-Key": "s8-idem-retry-429", "If-Match": etag_of(WSCAP, "j-00-src")},
        ),
        429,
    )
    with TestClient(
        h.make_app(with_workspace=False),
        headers={"Origin": TEST_ORIGIN},
        raise_server_exceptions=False,
    ) as client500:  # 口径照抄 tests/unit/test_api_app.py 的既有 500 取证面
        save("problem-500.json", client500.get(f"{API_PREFIX}/health"), 500)

    print(f"@@@COLLECT_DONE fails={json.dumps(fails, ensure_ascii=False)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
```

### v9_integrity.py（sha256[:12]=`3f84fbab1f37`）

```text
"""R18 M0-04/S8 · V9 取证（写入侧前提）：正常库 verify_artifact_index()==[]；
注入「删一个被引用制品」⇒ 差异可定位（MISSING_FILE ＋ workspace/artifact/relative_path/expected_sha256，
actual_sha256=None）。切换守卫阻断的判定归 M5-01，本件不出结论。
工具件在仓库外，不入分母；时钟只经 FixedClock。
"""

import dataclasses
import json
import sys
import tempfile
from pathlib import Path

REPO = Path("/home/szf/dev/CampaignLab")
sys.path.insert(0, str(REPO))

from campaignlab.api.common import ObjectRef  # noqa: E402
from campaignlab.infra.artifacts import ARTIFACT_KIND_JOB_RESULT, ArtifactWriter  # noqa: E402
from campaignlab.worker.integrity import (  # noqa: E402
    MISSING_FILE,
    manifest_rows,
    verify_artifact_index,
)
from campaignlab.worker.store import JobStore, short_transaction  # noqa: E402
from tests.integration.jobs.test_jobs_router_s4 import Harness  # noqa: E402

WS = "ws-s9"


def main() -> int:
    tmp = tempfile.TemporaryDirectory(prefix="s8-v9-")
    h = Harness(Path(tmp.name))
    h.seed_workspace(WS)
    store = JobStore(engine=h.engine)
    clock = h.clock
    store.enqueue(
        workspace_id=WS,
        kind="VALIDATE_IMPORT",
        input_json="{}",
        input_digest="0" * 64,
        now=clock.now(),
        job_id="j-v9",
    )
    claim = store.claim_next(workspace_id=WS, now=clock.now())
    assert claim.claimed and claim.lease is not None
    writer = ArtifactWriter(h.config.data_dir)
    writer.verify_same_filesystem()
    print("@@@V9 verify_same_filesystem: OK（同盘前提成立）")
    with writer.begin(WS, "j-v9", claim.record.attempt) as stage:
        stage.write(b"s8-v9-referenced-payload")
        with short_transaction(h.engine) as conn:
            committed = writer.commit(
                conn,
                stage,
                workspace_id=WS,
                kind=ARTIFACT_KIND_JOB_RESULT,
                now=clock.now(),
            )
    print(f"@@@V9 committed={json.dumps(dataclasses.asdict(committed), ensure_ascii=False, default=str)}")
    store.succeed(
        claim.lease, result_ref=ObjectRef(kind="job", id="j-v9"), now=clock.now()
    )
    with short_transaction(h.engine) as conn:
        healthy = [dataclasses.asdict(d) for d in verify_artifact_index(conn, h.config.data_dir)]
        rows = [dataclasses.asdict(m) for m in manifest_rows(h_engine(conn))]
    print(f"@@@V9 healthy-db verify_artifact_index -> {json.dumps(healthy, ensure_ascii=False)}")
    assert healthy == [], healthy
    print(f"@@@V9 manifest_rows -> {json.dumps(rows, ensure_ascii=False, default=str)}")
    assert len(rows) == 1, rows
    target = h.config.data_dir / rows[0]["relative_path"]
    print(f"@@@V9 inject: unlink referenced artifact {target}")
    target.unlink()
    with short_transaction(h.engine) as conn:
        dirty = [dataclasses.asdict(d) for d in verify_artifact_index(conn, h.config.data_dir)]
    print(f"@@@V9 injected verify_artifact_index -> {json.dumps(dirty, ensure_ascii=False)}")
    hits = [
        d
        for d in dirty
        if d["reason"] == MISSING_FILE
        and d["relative_path"] == rows[0]["relative_path"]
        and d["artifact_id"] == rows[0]["artifact_id"]
        and d["actual_sha256"] is None
    ]
    assert hits, dirty
    print("@@@V9 LOCATABLE: 差异含 workspace_id/artifact_id/relative_path/expected_sha256 四要素，可定位到该制品")
    print(f"@@@V9 GUARD_SIGNAL: discrepancies 非空（{len(dirty)} 条）即切换守卫的阻断信号；判定归 M5-01，本件不出结论")
    print("@@@V9_DONE")
    return 0


def h_engine(conn):  # manifest_rows 需要同一连接的轻量包装占位（防误用：直接传 conn）
    return conn


if __name__ == "__main__":
    sys.exit(main())
```

