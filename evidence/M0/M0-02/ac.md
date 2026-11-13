# M0-02 · S5 · AC-001 / AC-034 / AC-035 验收证据回执

- 执行位置（cwd）：WSL2 仓库根 `/home/szf/dev/CampaignLab`，分支 `m0-framework`，会话内 HEAD `4a82190f69c0b0b864ce3a55a11a06fddf2a9b38`（`git rev-parse HEAD` rc=0，见 `http/97-gate-summary.json`）。
- 原文口径（裁定 Q1）：`spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md` **第 9 / 42 / 43 行** + `orchestrator/handoff/M0-02.slice.json → acceptance_rows` 为权威；本回执只引原文、不转述改写。
- 起服务方式（项目既有 CLI，现值取自 `src/campaignlab/cli.py:261-277`）：`uv run --no-sync python -m campaignlab serve --port <8765|8766>`，数据目录经 `CAMPAIGNLAB_DATA_DIR` 注入；进程由驱动脚本管理并显式等待 `/api/v1/health` 可用（0.2s 轮询，实测 0.8s 就绪，无固定 sleep），退出时 SIGTERM 进程组并轮询确认端口释放（`port_A_released=true`、`port_B_released=true`，见 `http/98-run-summary.json`）。
- 领域时间口径：全部时间戳来自响应体自身（服务端显式时钟），S5 未做任何系统时间领域计算。

## 1. AC 原文四元组（逐字引用）

| 行号 | 编号 | 输入及操作 | 通过条件 | 主证据 |
|---|---|---|---|---|
| 9 | AC-001 | 启动本机模式，换取一次性会话，新建并进入工作区 | 正常会话进入。重复令牌拒绝。工作区切换保留各自数据。worker 状态可见 | HTTP 与 Playwright |
| 42 | AC-034 | 测试过期会话、错误 Host/Origin、跨工作区 ID 和上传失败 | 按 401/403/404/413 或 422 返回。隔离、路径、日志和 ETag 证据可查 | HTTP 负例 |
| 43 | AC-035 | 按 M0 锁版本、迁移、核对包和 API | `verify_package.py`、DDL 等价、OpenAPI 请求响应及前端生成类型通过。锁和运行环境清楚 | 命令、锁和报告 |

## 2. AC-001 —— 结论：**PASS**（HTTP 面全取；Playwright 面依裁定 Q1 归 M0-03/UI-01，本回执不扩 scope）

| 通过条件（原文短语） | 证据 | 实测 |
|---|---|---|
| 正常会话进入 | `http/02-exchange-first-200.http` | `POST /api/v1/session/exchange` → 200 `Session{actor_id=szf, 6 roles}` + `Set-Cookie: cl_session=…; Path=/api/v1; Max-Age=3600; HttpOnly; SameSite=strict`；`http/04-get-session-200.http` → 200 |
| 重复令牌拒绝 | `http/03-exchange-replay-401.http` | 同一 entry_token 二次换取 → 401 `code=SESSION_EXPIRED`、`type=urn:campaignlab:problem:session_expired`；令牌 TTL=60s（serve 日志行 `entry_token=… ttl=60 一次性`，令牌明文不落盘，仅存 sha256 前 12 位 `05e8026524f7`） |
| 工作区切换保留各自数据 | `http/05/08/09/10` + `http/40-audit-and-db-rows.txt` | Alpha(201, ETag \"1\") 与 Beta(201) 并存：`list_total=2`；`?q=S5-AC001-Alpha` 仅回 Alpha；库内 workspaces 2 行、audit 2 行（各自 workspace_id、sequence 独立） |
| worker 状态可见 | `http/01-health-after-boot.http`、`http/11-health-with-worker.http` | `GET /api/v1/health` → 200 `{status:READY, worker:READY, schema_revision:0001_initial_schema, contract_version:1.0.1}` |

一次性令牌语义（`application/session_service.py:11,133,243`）：未知/已消费/已过期共用同一 401 面孔，无枚举旁路——与 `http/17-neg-unknown-token-401.http` 的 detail 逐字相同（「会话不可用，请重新使用一次性令牌换取会话」）。

## 3. AC-034 —— 结论：**PASS_WITH_TODO**（负例全落 401/403/413/422；「跨工作区 ID → 404」在 M0-02 契约切片 5 个 op 上无 HTTP 触发面，取证deferred，见 3.2）

### 3.1 逐项命中

| 输入（原文短语） | 状态码 | 证据 | 关键值 |
|---|---|---|---|
| 错误 Host | 403 | `http/12-neg-bad-host-403.http` | `Host: evil.invalid` → `code=ORIGIN_DENIED`（GET 也校验 Host） |
| 错误 Origin | 403 | `http/18-neg-bad-origin-403.http` | `Origin: http://evil.invalid:9` → 403 `ORIGIN_DENIED` |
| 上传失败（正文超限） | 413 | `http/14-neg-body-over-1mib-413.http` | 1,100,023 B JSON → 413 `INPUT_TOO_LARGE`（阈值=JSON 正文 1 MiB，ADR-005/Q6；不适用文件上传口径） |
| 无会话 | 401 | `http/16-neg-no-session-401.http` | `GET /session` 无 cookie → 401 `SESSION_EXPIRED` |
| 未知令牌（过期同面孔） | 401 | `http/17-neg-unknown-token-401.http` | 同码同 detail |
| 非法请求体 | 422 | `http/15-neg-unknown-field-422.http` | 未知字段 → `VALIDATION_ERROR`，`issues[0].location=/bogus` |
| 幂等键过短 | 422 | `http/19-neg-idem-key-too-short-422.http` | `Idempotency-Key: abc` → 422，`location=/header/Idempotency-Key` |
| （旁证）同键异体 | 409 | `http/07-create-workspace-alpha-conflict-409.http` | `IDEMPOTENCY_CONFLICT`，未落新行 |
| 过期会话（真实时钟） | — | `http/97-gate-summary.json`：`pytest -k expired` tests/api rc=0（2 passed）、`pytest -k expir` tests/unit/test_s3d_application.py rc=0（3 passed，含 `test_expired_session_401_uses_the_same_detail`、`test_token_is_single_use_and_expires_at_ttl`） | 会话 TTL=3600s、令牌 60s，真实运行时无法在证据窗口内跨过期点且不改进程（禁 sleep 到真实 TTL）；过期→401 与上表 401 为**同一 handler 同一形状**（SessionInvalid 唯一面孔），时钟注入测试补真实过期点 |

### 3.2 跨工作区 ID → 404：**无 HTTP 触发面（如实记录，deferred）**

M0-02 切片 5 个 op（exchangeSession/getSession/getHealth/listWorkspaces/createWorkspace）均非 workspace 子资源；`tests/api/test_contract_declarations.py:126` `test_404_and_429_branches_are_unreachable_for_the_five_ops`（本次复跑 rc=0，2 passed，`http/96-selfcheck-greps.json`）断言挂载路径集恰为上述 4 条。服务层跨工作区读隔离由 `tests/unit/test_s3d_repositories.py -k workspace`（rc=0，2 passed）覆盖。HTTP 端到端 404 应归**拥有 workspace 子资源 op 的后续任务**取证（口径同裁定 Q2/Q3）。故 AC-034 记 PASS_WITH_TODO。

### 3.3 「隔离、路径、日志和 ETag 证据可查」

- 隔离：`http/10`（q 过滤仅见本名）；游标签名含 actor（`application/workspace_service.py:290-295`，换人复用→400 同形，禁枚举面）。
- 路径：`Set-Cookie … Path=/api/v1`（`http/02`）。
- 日志：`http/40-audit-and-db-rows.txt`（audit 2 行含 actor/request_id，重放未追加行：idempotency 计数=2）。
- ETag：201 发布 `ETag: \"1\"`（`http/05`）；重放同 ETag（`http/06`）。If-Match 412/428 端到端依裁定 Q3 deferred（切片 5 op 无 If-Match 语义，`If-Match` 头被忽略仍 201，见 `tests/api/test_contract_declarations.py` 同名用例复跑绿）。
- **CR-002（选项 B）遵守**：本回执与全部证据不含 `/query/status` 分支（参数已移出契约）。

### 3.4 D-033（OPEN，禁修只记录，不粉饰）

同键同体重放：`http/05` vs `http/06` —— 状态码（201=201）、`ETag`、字段集合与逐字段值**全部一致**（`json_equal=true`），但**正文非逐字节相同**：首次=DTO 声明序 `[id,revision,created_at,name,source_class,authorization_note]`，重放=经 `canonical_json` 落库回读的字典序 `[authorization_note,created_at,id,name,revision,source_class]`；`byte_identical=false`（`http/98-run-summary.json → d033`）。机制位点：`api/common.py:540 replay_from_envelope` + `application/workspace_service.py:360-365`。**指向 D-033 / FU-21，S5 未触碰 `api/common.py`。**

## 4. AC-035 —— 结论：**PASS**

| 通过条件（原文短语） | 命令（cwd=仓库根） | rc | 关键输出 |
|---|---|---|---|
| `verify_package.py` | `python3 spec/CampaignLab-SDD-v1.0/qa/verify_package.py` | 0 | `PACKAGE PASS 6/6`（28 表 DDL、完整性与外键负例在内） |
| DDL 等价 | `uv run --no-sync alembic -c migrations/alembic.ini upgrade head` + `ddl_compare.compare_schema` 复跑（`http/97-gate-summary.json → ddl-compare-rerun`） | 0 | `ddl_sha256=ec9ddfbc…c8c0e`（与 S2 记录逐字一致）；28=28；`compare_schema_diffs []`；`integrity [('ok',)]`；`fk_violations []`；head=`0001_initial_schema`。另 `pytest tests/integration/bootstrap/test_migration_equivalence.py tests/unit/test_migration_schema.py` rc=0（26 passed） |
| OpenAPI 请求响应 | `uv run --no-sync python scripts/check_contracts.py check --validate` | 0 | 活契约校验通过（sha16 `592571099d638251` / 443309 B = 切片 `source.openapi` 现值，一致） |
| 前端生成类型通过 | `cd web && npx openapi-typescript ../contracts/openapi.json -o <tmp>` + `cmp` + `npm run typecheck`（vue-tsc 5.9.3） | 0 / 0 / 0 | 重跑生成物与 `web/src/api/types.ts` **逐字节一致**（byte-equal=True）；typecheck 无错；`scripts/check_frontend_baseline.py` rc=0 |
| 锁和运行环境清楚 | `uv lock --check`；`uv --version`；`sys.executable -c platform,sqlite3` | 0 | 锁一致（52 packages）；CPython 3.14.10、sqlite 3.53.1、uv 0.13.7、node v24.22.3、npm 11.19.1；HEAD `4a82190` |

质量门旁证：`ruff check .` rc=0；`ruff format --check .` rc=0（194 files）；`mypy` rc=0（73 files）；`pytest -q` **rc=1：1 failed / 355 passed**——失败项 `tests/unit/test_state_ledger.py::test_every_md_on_disk_has_ledger_entry`，断言原文「磁盘上有缺陷单但账本查不到：['D-037']」（orchestrator/defects/D-037.md mtime 2026-11-14T01:18 +08，编排器在飞记账，**非 M0-02 代码缺陷、非 S5 写集**）→ 如实回报，不属 AC-035 原文四条件。

doctor gate transcript（`uv run python -m campaignlab doctor`，原文命令、无 PYTHONPATH 前缀，rc=**0**）全文已记入 `commands.md` S5 节：`PASS=5 WARN=0 FAIL=0 RESULT=HEALTHY`。

## 5. FU-7 —— 「未迁移时 /health 响应体」命令级取证：**已拿到**

- 取证：`CAMPAIGNLAB_DATA_DIR=<空目录> uv run --no-sync python -m campaignlab serve --port 8766` → `GET /api/v1/health` → 200，响应体（`http/20-health-unmigrated-degraded.http` 原文）：
  `{\"status\":\"DEGRADED\",\"app_version\":\"0.0.0\",\"contract_version\":\"1.0.1\",\"worker\":\"READY\",\"schema_revision\":\"UNMIGRATED\"}`
- 语义证明：worker=READY 而 status=DEGRADED ⇒ READY 的「worker==READY **且** revision==head」是与关系（`application/health_service.py` snapshot()），未迁移库不会亮绿灯。
- 前端分支取证：`web/src/composables/useWorkspaces.ts:180` 按 `status === \"DEGRADED\" || worker === \"OFFLINE\"` 置 `workerRestricted`（注释同文件 :50）；「禁把哨兵串当版本号展示」：`grep -rn schema_revision web/src` 全仓唯一命中 `web/src/api/types.ts:1058`（类型声明，无任何渲染使用）；`grep -rn UNMIGRATED web/src prototype` → **rc=1（无匹配）**，哨兵串不进入展示面。

## 6. 证据文件索引

`http/01–12、14–20`（无 13 号；HTTP 请求/响应全文）、`40-audit-and-db-rows.txt`、`90-requests-index.txt`（19 个请求→状态码；R10 补全，原记 23、实测原索引仅 17 行，见 D-038）、`96-selfcheck-greps.json`、`97-gate-summary.json`（23 条 gate 命令四元组；R10 核实，原记 22）、`98-run-summary.json`（HTTP 驱动结果+命令四元组）。运行期临时数据目录（`_runtime/**` 含 sqlite 库、serve 进程日志、生成物 types.gen.ts）已在 S5 出口删除，不入库。
