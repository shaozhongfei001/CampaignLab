# R17 · lane M0-04/S5 派单文 —— `tests/integration/jobs/` 的 conftest 与状态机矩阵

> **上工第一件事**：按 §5 逐条复测冻结面读数并与本文对账。若不符，**先查** `orchestrator/state.json`
> 的 `resume.baseline_authoritative.current`（A223 / PRE-10：编排器在你在飞期间的自办入库会在同一提交内
> 更新该键），对账口径＝**派单快照 ＋ 该键 history 的累计增量**；不符**不要直接判失真、也不要停手空转**。

## §0 身份、档位与预算

| 项 | 值 |
|---|---|
| 任务 / 子任务 | **M0-04**（作业队列与执行器）/ **S5** |
| 轮次 / lane | Round 17 / lane **S5** |
| 档位 | **`qwen3.8-flash`** · reasoning **medium**（design §9-S5 冻结，未升降档） |
| loop | 上限 **2** 轮（critical=true 链上的一环，slack 小）；超限即停手写 U 项，禁硬撑 |
| 派单基线 | **含本派单文的那个提交**（tag `R17-predispatch`；其 parent = `dd09aa2`。上工时用 `git log --oneline -1 -- orchestrator/handoff/R17-lane-M0-04-S5.md` 自行取 sha，禁写猜测值）· 分支 `m0-framework` · ruff format **292** / mypy **101** / pytest **699**（in-scope **103 py + 189 md**）。292 与 189 已计入**两份 R17 派单文自身**入库带来的 +2 in-scope md（`orchestrator/**` 的 `.md` 在 ruff 作用域内，实测口径见 `counts.ruff_formatted_files_composition`）；除此之外交付面与 `dd09aa2` **逐字节相同**（该提交是纯台账回填）。 |
| 并行邻居 | lane **S2b-2**（M2-01，只动 `src/campaignlab/api/app.py`）—— 写集与你**不相交**；它的文件对你而言是 **IN_FLIGHT_CONTAMINATION**：**禁改、禁 add、禁 checkout、禁 clean/reset/stash**（PRE-11 / A161：复验方与邻居对在飞面禁写） |

## §1 写权面（**只新建**，共 4 件；越界即按 §9 报 U，禁自行扩大）

```
tests/integration/jobs/conftest.py            （新建）
tests/integration/jobs/test_state_machine.py  （新建）
tests/integration/jobs/test_idempotency.py    （新建）
tests/integration/jobs/test_jobs_api.py       （新建）
```

design §9-S5 的**原文**（逐字，禁改写）：

> **S5**（`qwen3.8-flash`，14k，`tests/integration/jobs/**`，**只新建**）：
> `conftest.py:job_store,registry_with_stub,fixed_clock,data_dir,migrated_job_db,http_client,idem_key,advance_clock,stub_handler`
> · `test_state_machine.py:test_t1_claim_queued_to_running,…,test_t9_retry_creates_new_queued`（9 个函数，函数名含 `t1`…`t9` 与 `state_machine`）
> · `test_idempotency.py:test_same_key_same_request_same_object,test_same_key_different_request_409,test_replay_body_byte_identical`
> · `test_jobs_api.py:test_list_pagination_and_cursor,test_bad_cursor_400,test_status_filter_multi_value,test_cross_workspace_is_404,test_cancel_missing_if_match_428,test_cancel_stale_if_match_412,test_retry_capacity_429_has_retry_after`。

即：**9 个 fixture 名**、**9 个状态机函数**（`test_t1_*`…`test_t9_*`）、**3 个幂等函数**、**7 个 API 函数** —— 名字逐字照抄，
禁改名、禁合并、禁增删。`…` 处的 `test_t2`–`test_t8` 函数名由你按 §4 的 T2–T8 语义自拟，但**必须**满足
「以 `test_t<N>_` 开头」且所在文件是 `test_state_machine.py`（V2 的 `-k state_machine` 靠**文件名**命中，
参数化 id 必须含 `T1`…`T9`，见 §4）。

## §2 硬禁面（**逐条**，含 PRE-14 要求的「预期红清单」）

1. **禁改任何 `src/**`**（含 `worker/**`、`api/**`、`application/**`、`infra/**`、`domain/**`）。S5 是**纯测试棒**。
   若发现 src 侧缺陷 ⇒ 按 §9 报 U，**禁就地修**。
2. **禁改既有测试件**：`tests/integration/jobs/{__init__.py,test_artifact_write.py,test_worker_deps.py,test_jobs_router_s4.py}`、
   `tests/api/**`、`tests/unit/**`。它们的 sha 见 §5，回收时逐件对撞。
3. **禁改** `contracts/**`、`spec/**`、`scripts/**`、`orchestrator/**`、`web/**`、`pyproject.toml`、`uv.lock`、`README.md`。
   `contracts/openapi.json` 必须保持 **443309 B / sha16 `592571099d63`**（V1/V7 的判据）。
4. **conftest.py 禁 `autouse=True`**（任何 fixture 都不许）。理由（实测）：同目录已有三个测试文件各自定义了
   同名 fixture（`data_dir` 出现在 `test_artifact_write.py` 与 `test_worker_deps.py`，`clock`/`engine`/`store`/
   `other_device` 亦重名）。模块级 fixture 会**遮蔽** conftest 的同名 fixture，故普通 fixture 不冲突；
   但 `autouse` 会**强行注入**到既有 39+30+13 条用例里 ⇒ 必然改变它们的行为。这是本棒唯一的**结构性**风险点。
5. **禁 `sleep`、禁 `time.monotonic` / `time.time` 判定、禁读墙钟**（红线 3 / D-045 / design §9-S6 原文同型要求）：
   一律用 `campaignlab.clock.FixedClock` ＋ 你的 `advance_clock` fixture。回收时编排器会对你的 4 件做
   字面量扫描（含注释与 docstring），命中即判红。若需引用禁串，用**拼接**构造（体例见 `test_jobs_router_s4.py`
   的 `needle = "INVALID" + "_SCOPE"`）。
6. **禁在 `src` 内放测试桩**（A89 / N8 裁定原文）：
   > 测试桩只准注册在 `tests/integration/jobs/conftest.py`，**src 内禁放桩**；`result_ref` 断言口径用
   > `ObjectRef(kind='job', id=<job_id>)`（`job` 在 21 枚举内）；`artifacts.kind` 取常量 `'JOB_RESULT'`
   > （DDL 无 enum，本裁定即其权威来源）。`kind` 的**业务映射**（VALIDATE_IMPORT->import、COMPARE->comparison、
   > REPORT->report、EXPORT->export …）仍归 M1/M2，本卡**禁发明**。
7. **禁发明第二个游标版本号或第二句 `BAD_CURSOR_DETAIL`**（A222 / FU-46）：单一真源在
   `application/workspace_service.py` 的 `CURSOR_VERSION` / `BAD_CURSOR_DETAIL` / `load_cursor_secret`，
   一律 **import 复用**，回收时会用 `is` 判定（同对象，非同值副本）。
8. **禁跑 `uv add` / `uv sync` / `git commit` / `git add` / `git push`**；禁改 `.gitignore`。

### 2.1 预期红清单（PRE-14：**本棒落地后不会打红任何既有哨兵**，此结论已由编排器实测）

编排器已用 AST 扫过 `tests/**` 的全部 fixture 与断言面，结论：
- **没有**任何既有用例断言「`tests/integration/jobs/conftest.py` 不存在」（只有 `test_jobs_router_s4.py` 的
  **docstring** 写了「本目录的 `conftest.py` 归 S5，禁建」—— 那是给 S4 的约束，不是判据，且它现在正是给你的授权）。
- `tests/unit/test_s3b_routes.py::test_app_py_contains_only_the_a85_mount_lines`、
  `tests/api/test_contract_declarations.py` 探的是 `api/app.py` 与 `contracts/`，与你无关。
- 因此**你的 4 件落地后，全表 pytest 必须仍是 0 failed**（699 → 699 + 你的新增数）。
  若出现任何红：① 先确认不是邻居 lane S2b-2 的在飞件造成（IN_FLIGHT_CONTAMINATION，禁修）；
  ② 若确是你的 conftest 泄漏到既有用例 ⇒ 十有八九是违反了 §2.4 的 autouse 禁令，自己修。

## §3 conftest.py 的 9 个 fixture —— 契约（名字逐字，语义如下）

| fixture | 语义与硬要求 |
|---|---|
| `data_dir` | `tmp_path` 下的数据目录（`Path`）。**不得**与 `test_artifact_write.py` / `test_worker_deps.py` 的同名 fixture 相互影响（它们模块级遮蔽你）。 |
| `migrated_job_db` | 建库并**执行首迁 DDL**：DDL 一律**直读活契约** `contracts/sqlite-v1.sql`（体例照抄 `test_jobs_router_s4.py` 的 `Harness.__init__`：`sqlite3.connect(...).executescript(DDL.read_text())`），再 `make_engine(f"sqlite:///{db_path}")`。**禁**在测试里内嵌第二份 DDL。 |
| `fixed_clock` | `campaignlab.clock.FixedClock(T0)`，`T0` 自定但必须是**带 tzinfo=UTC 的常量**（体例 `datetime(2026, 11, 13, 1, 0, 0, tzinfo=UTC)`）。 |
| `advance_clock` | 推进 `fixed_clock` 的可调用 fixture（签名建议 `advance(seconds: int) -> datetime`，返回推进后的时刻）。**T3/T7/T8 的到期分支全靠它**，禁 sleep。 |
| `job_store` | `campaignlab.worker.store.JobStore(...)` 实例，绑定 `migrated_job_db` 的 engine 与 `fixed_clock`。构造签名以**实际落地代码**为准（PRE-7：上工先 `inspect.signature` 实测，禁按本文猜）。 |
| `stub_handler` | 一个最小 `JobHandler` 实现（N8/A89：桩只准在这里）。其 `result_ref` 必须返回 `ObjectRef(kind="job", id=<job_id>)`；制品写入用 `infra.artifacts.ArtifactWriter` ＋ `ARTIFACT_KIND_JOB_RESULT`。 |
| `registry_with_stub` | `HandlerRegistry()` 且已 `register(...)` 上述桩，覆盖 T5 取证所需的 kind。`HandlerRegistry` 的公开方法面实测为 `['register','get','kinds']`。 |
| `idem_key` | 生成幂等键的可调用或常量工厂（`Idempotency-Key` 头用）。 |
| `http_client` | 已认证的 `TestClient`：**照抄** `test_jobs_router_s4.py` 的 `Harness.authed_client()` 口径 —— `create_app(config, clock=..., guard=OriginHostGuard(frozenset({"testserver"}), frozenset({"http://testserver"})), session_service=..., workspace_service=...)`，`headers={"Origin": "http://testserver"}`，再 `POST /api/v1/session/exchange` 换 token。**关键**：jobs 服务不经 `create_app` 注入 —— `worker/deps.py::get_job_service` 按 `app.state.config.database_url` 自建引擎，故 DB 位置必须通过 `CAMPAIGNLAB_DATABASE_URL` 环境变量与 config 对齐（五级链唯一实现，ADR-005 §2.4）。 |

## §4 判据（回收时编排器逐条独立复验，**禁采信你的自报**）

### 4.1 T1–T9 状态机矩阵（`test_state_machine.py`，9 个函数一一对应）

`campaignlab.worker.states.TRANSITIONS` 的**实测全文**（编排器运行期实取，9 条；禁改写、禁只测子集）：

| id | sources | target | trigger | guard（实测原文） | transaction | 新行 |
|---|---|---|---|---|---|---|
| **T1** | `QUEUED` | `RUNNING` | 事务内最早可认领 | `state = 'QUEUED' AND revision = :revision` | `TX1 claim_next` | 否 |
| **T2** | `QUEUED` | `CANCELLED` | 请求取消 | `state = 'QUEUED' AND revision = :revision` | `TX3 request_cancel` | 否 |
| **T3** | `RUNNING` | `RUNNING` | 每 5 秒续租 | `attempt = :attempt AND lease_token = :lease_token AND state IN ('RUNNING','CANCEL_REQUESTED')` | `TX2 renew` | 否 |
| **T4** | `RUNNING` | `CANCEL_REQUESTED` | 请求取消（安全分段读信号） | `state = 'RUNNING' AND revision = :revision` | `TX3 request_cancel` | 否 |
| **T5** | `RUNNING` | `SUCCEEDED` | 成功且租约仍有效 | `attempt = :attempt AND lease_token = :lease_token AND state IN ('RUNNING','CANCEL_REQUESTED')` | `TX5 succeed` | 否 |
| **T6** | `RUNNING` | `FAILED` | 已知失败 | 同 T5 | `TX6 fail` | 否 |
| **T7** | `RUNNING` | `FAILED` | 超时租约且证据未提交 | `state = 'RUNNING' AND lease_until < :now` | `TX7 reap_expired` | 否 |
| **T8** | `CANCEL_REQUESTED` | `CANCELLED` | 执行确认或租约到期 | 确认：`attempt/lease_token/state='CANCEL_REQUESTED'`；到期：`state='CANCEL_REQUESTED' AND lease_until < :now` | `TX4 confirm_cancel / TX7` | 否 |
| **T9** | `CANCELLED`,`FAILED` | `QUEUED` | 操作员发起重试 | `state IN ('FAILED','CANCELLED') AND revision = :revision` | `TX8 retry` | **是** |

每个 `test_t<N>_*` 必须：① 走**真实的** `JobStore` 方法（不是自己拼 SQL）；② 断言迁移**前**与**后**的
`jobs` 行快照（至少 `state`/`revision`/`attempt`，T3/T7/T8 还须含 `lease_until`，T9 还须含**新行 id ≠ 旧行 id**
且新行 `retry_of == 旧行 id`）；③ 用 `pytest.mark.parametrize` 时 **id 必须含 `T1`…`T9` 字样**（design §8-V2 原文：
「T1–T9 **每条 ≥1 例**（参数化 id 必须含 `T1`…`T9` 以便逐条取证）」）。
其余实测常量（运行期实取，禁写死在断言里当权威）：
`JOB_STATES = ('QUEUED','RUNNING','CANCEL_REQUESTED','SUCCEEDED','FAILED','CANCELLED')`；
`TERMINAL_STATES = frozenset({'FAILED','CANCELLED','SUCCEEDED'})`；
`NON_RETRYABLE_PROBLEM_CODES = frozenset({'VALIDATION_ERROR','INPUT_TOO_LARGE','EVIDENCE_REQUIRED','INVALID_SCOPE'})`；
`JobStore` 公开方法面 `['get_job','pending_count','claim_next','renew','request_cancel','confirm_cancel','succeed','fail','reap_expired','enqueue','retry','fail_unhandled','list_jobs']`。

### 4.2 幂等三例（`test_idempotency.py`）
- `test_same_key_same_request_same_object`：同 `Idempotency-Key` ＋ 同请求体 ⇒ 返回**同一对象**（id 相等、体逐字节相等）。
- `test_same_key_different_request_409`：同键不同体 ⇒ **409**（Problem code 以活契约与 `api/common.PROBLEM_CODES`
  的权威 20 码为准，**禁发明新 code**，D-019）。
- `test_replay_body_byte_identical`：重放的响应体与首次**逐字节相同**（含 `X-Request-Id` 之外的全部字段；
  若 `X-Request-Id` 每次不同，断言时排除该头并**在 docstring 写明理由**）。

### 4.3 API 七例（`test_jobs_api.py`）
`test_list_pagination_and_cursor`（翻页 ＋ 游标往返）、`test_bad_cursor_400`（坏游标 ⇒ **400**，`detail` 必须
**是** `workspace_service.BAD_CURSOR_DETAIL` 本体，`is` 判定）、`test_status_filter_multi_value`
（N7① 已裁定：`status` 为**逗号分隔多值**，单值为其子集）、`test_cross_workspace_is_404`（跨工作区 ⇒ **404**
`RESOURCE_NOT_FOUND`，A220）、`test_cancel_missing_if_match_428`（缺 `If-Match` ⇒ **428**）、
`test_cancel_stale_if_match_412`（旧 ETag ⇒ **412**）、`test_retry_capacity_429_has_retry_after`
（N7② 已裁定：待办＝**非终态**计数 `QUEUED|RUNNING|CANCEL_REQUESTED`、上限 `JOB_PENDING_LIMIT`、
**429 且必带 `Retry-After`**，值取 `worker.capacity.JOB_CAPACITY_RETRY_AFTER_SECONDS`，禁写死 3）。

### 4.4 门禁（design §8 原文，逐条采集 rc）
- **V2**：`uv run --no-sync pytest -q tests/integration/jobs -k state_machine` → rc=0，T1–T9 每条 ≥1 例。
- **V6**：`uv run --no-sync ruff check .` / `ruff format --check .` / `mypy` / `pytest -q` 各 rc=0。
  分母以 `counts.*` 现值为准（**禁写死**）；本棒预期（基线已含两份派单文的 +2 md）：in-scope py 103→**107**、in-scope md **189** 不变、
  ruff format 292→**296**、mypy 101→**105**、pytest 699→699+你的新增数（实测为准）。
- 你的 4 件必须 **`ruff format --check` 干净**（含 `.md` 也在 ruff 作用域，但你本棒不产出 `.md`）。
- **mypy strict 必须干净**：`# type: ignore` 出现次数必须为 **0**（回收时 grep 实测）。

## §5 冻结面读数（PRE-15：以下全部由编排器脚本 `.orch_tmp/measure_r17.py` 实测，命令原文一并给出）

```
$ git rev-parse --short HEAD && git rev-parse --abbrev-ref HEAD
dd09aa2 m0-framework
$ git rev-parse --short HEAD          # 在 dd09aa2 上测得（= 派单文的 parent）
dd09aa2
$ uv run --no-sync ruff format --check . 2>&1 | tail -1
290 files already formatted
$ uv run --no-sync mypy 2>&1 | tail -1
Success: no issues found in 101 source files
$ git status --porcelain -uall | wc -l
0
```

> **口径换算（务必读）**：上面 290 是在 `dd09aa2` 上的实测值。本派单文与邻居 lane 的派单文（共 2 个
> `orchestrator/handoff/R17-lane-*.md`）随 predispatch 提交入库后，in-scope `.md` 由 187 → **189**、
> `ruff format --check` 报数由 290 → **292**；`mypy` 101 与 `pytest` **699** 不变
> （`.md` 不入 mypy 的 `src/tests/scripts` 域，本批零 `.py` 改动）。
> 你上工后复测应得 **292 / 101 / 699**；若得 290，说明你 checkout 到了 predispatch 之前，先 `git log` 核对。

| 文件 | 行 | 字节 | sha256[:12] |
|---|---|---|---|
| `src/campaignlab/api/app.py` | 160 | 7253 | `110751903e4d` |
| `src/campaignlab/api/deps.py` | 346 | 13524 | `ed1075a86447` |
| `src/campaignlab/application/activity_service.py` | 1999 | 88950 | `21425228694b` |
| `tests/integration/jobs/test_jobs_router_s4.py` | 683 | 26515 | `c3110b40b71d` |
| `tests/integration/jobs/test_worker_deps.py` | 632 | 27316 | `69234fb4f35d` |
| `tests/integration/jobs/test_artifact_write.py` | 731 | 30646 | `ffce1792d82f` |
| `tests/api/conftest.py` | 193 | 7489 | `2df41d5585dd` |
| `contracts/sqlite-v1.sql` | 234 | 17284 | `ec9ddfbc4e7d` |
| `contracts/openapi.json` | 16747 | 443309 | `592571099d63` |

pytest 分母 **699**（冻结索引树实测：678 passed ＋ GIT_ENV_IGNORES 静态收集 21；该 21 条属 `test_config.py` 16 + `test_counts_freshness.py` 5，静态补回，禁重复计入）。
既有 3 个集成文件的 fixture 名（**遮蔽关系**已核，见 §2.4）：`test_artifact_write.py` = `data_dir,engine,clock,store,writer,other_device`；
`test_worker_deps.py` = `data_dir,db_path,engine,config,clock,store,other_device`；`test_jobs_router_s4.py` = `harness,client,ws`。

## §6 纪律（红线，违反即判红）
1. **A81**：`jobs` 表的 DML 文本只允许出现在 `src/campaignlab/infra/db/repositories.py` 与 `worker/store.py`。
   你的测试**不得**内嵌 `UPDATE jobs SET ...` 一类原文；要造前置状态一律走 `JobStore` 的公开方法。
2. **A115**：符号面判据一律用**集合对撞**（差集为空），禁用「计数 == N」（计数型判据抓不到换序／换名）。
3. **D-045 / 红线 3**：见 §2.5。
4. **N4 禁双主写**：不得新建与既有测试文件同名的 fixture 并期望它们生效（遮蔽是 pytest 语义，不是 bug）。
5. **PRE-7**：上工第一步对 `worker/store.py`、`worker/runner.py`、`worker/service.py`、`infra/artifacts.py`、
   `api/deps.py` 做 `inspect.signature` 实测，**以实际落地代码为准**；本文与 design 的数字一律视为待复核参考值，
   签名不符即按 §9 报 U，禁自行假定或就地重写 src。

## §7 阳性对照（PRE-18：**先证变异生效，再证判据有牙**）
至少 **5** 条，每条三步且**三步都要贴原文**：
1. **语义断言**：用 AST 或运行期实取被改对象的**新值**，断言它确实等于预期的变异后形态
   （「文件 sha 变了」**不构成**「变异生效」的证明 —— 这是 R16-4 与 R16-9 两次假绿的成因）；
2. **跑判据** ⇒ 必须 **rc≠0**（真红）；
3. **字节级双向复原** ⇒ sha256[:12] 与 AST 双口径都回到基线。

建议的 5 条（可替换，但强度不得低于此）：
- PC-1：把 `stub_handler` 的 `result_ref.kind` 从 `"job"` 改成 `"jobX"` ⇒ T5 相关用例判红；
- PC-2：把某个 `test_t<N>_*` 的后置快照断言改成**错**的目标态 ⇒ 该用例判红（证断言不是摆设）；
- PC-3：把 `advance_clock` 的推进量改成 0 ⇒ T7/T8 的到期分支判红（证到期判据真的依赖时钟推进）；
- PC-4：给 conftest 的任一 fixture 加 `autouse=True` ⇒ **既有**三个文件的用例判红（证 §2.4 的禁令是有牙的、
  且证你的 conftest 确实没泄漏）；
- PC-5：把 `test_bad_cursor_400` 的 `detail` 断言改成比较**同值副本**而非 `is` ⇒ 判红或至少能被集合对撞抓到
  （若抓不到，如实写成 U 项，禁假装通过）。
备份只准放 `/tmp` 或仓库外，**工作树零残留**。

## §8 取证落点（S5 只产出代码，取证文件归 S8；本棒只需在回执里给出可复现命令与 rc）
- 回执必须逐条给出：V2 / V6 的**命令原文 ＋ rc ＋ 关键输出行**（禁只写「通过」）。
- 交付面逐件报 **行 / 字节 / sha256[:12] / 用例数**（`--collect-only -q` 实测）。
- **不要**自己建 `evidence/**` 文件（S8 的写集，禁侵占）。

## §9 U 项协议（只报不裁；编排器逐条终裁）
遇到下列任一情形，**停手报 U**，禁自行决定：
① design／本文与**实际落地代码**冲突；② 需要的符号不存在或签名不符；③ 判据本身自相矛盾
（D-048 就是这么来的：`§11.3` 的通则与 `§3.2` 的 SQL 原文互斥）；④ 必须动 §2 的硬禁面才能完成；
⑤ 你**已经**动了硬禁面（自报越界，宁报勿藏 —— A230/A233 的先例：自报越界记入 honesty 正面样本，静默扩形才是重罪）。
每条 U 写清：**事实（实测，非转述）→ 候选方案（≥2 个，含你的倾向与理由）→ 影响面**。

## §10 回执格式（最后一条消息，逐字用这些字段名）
```
RESULT: DONE | DONE_WITH_GAP | PARTIAL | BLOCKED
① 基线复测（对账 resume.baseline_authoritative）
② 交付面（逐件 行/字节/sha256[:12]/用例数）
③ 四门与 V2/V6（命令原文 + rc + 关键输出）
④ 符号面／集合对撞结果（A115）
⑤ 阳性对照（≥5 条，每条三步原文）
⑥ 自报 token（拿不到计量句柄就写 estimated=true 与区间，禁编精确数）
⑦ U 项（只报不裁）
⑧ 未尽面 / 风险 / IN_FLIGHT_CONTAMINATION / loop 用了几轮 / 自报越界
```
