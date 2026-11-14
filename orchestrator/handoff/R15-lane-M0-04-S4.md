# R15 · lane ? · M0-04/S4 派单文 —— `api/jobs.py` 路由层落地（4 个 operationId）＋ `JobPage` append-only ＋ `api/app.py` ≤3 行挂载

> **本文件是权威派单文。** 上工第一步读全文，第二步按 §6 做只读复测；**复测未过禁写任何文件**。
> 凡本文件里的具体数字，一律视为**待复核的参考值**（PRE-7）；权威基线以 §1 的 `resume.baseline_authoritative` 为准。
> 遇到本文件与设计文档 `orchestrator/handoff/M0-04-design.md` 冲突、或撞上不可自证的矛盾：**停手、写 U 项上报，禁自行裁定**（手册 §6.4）。

## §0 身份 / 档位 / 预算

| 项 | 值 |
| --- | --- |
| 任务 | **M0-04**（Jobs 作业队列 HTTP 面） |
| 子任务 | **S4** |
| 档位 | **qwen3.8-flash**（reasoning: medium）—— design §9 冻结为 flash；**禁自行升档**，若你认为必须升档，写 U 项上报由编排器裁定（C10：禁为凑配比发明工作，也禁把 max 档改标 flash；反向同理） |
| loop_cap | **2**（自迭代最多 2 轮；第 2 轮仍不绿就停手回报，禁第 3 轮） |
| 关键路径 | **是**，slack = 0。M0-04 的 S8 是 21 个 TODO 任务的唯一解锁点，本棒拖延会卡住整个 wave3 |
| 邻居在飞 lane | **M2-01/S2b-1**（max high）：写 `src/campaignlab/application/activity_service.py`（新建）、`src/campaignlab/infra/db/repositories.py`（纯追加）、`src/campaignlab/api/deps.py`（纯追加）、`tests/**`。**与你的写集不相交**，但你上工复测四门时可能读到它的半成品 ⇒ 见 §6 的 PRE-11 条款 |
| 前置已满足 | M0-04/S2c 已入库（`1d9bcb0`）：`worker/service.py::JobService` 就绪；M2-01/S2a 已入库（`b523635`）：`api/common.py` 的 DTO 面就绪 |

## §1 权威基线（A223 / PRE-10 —— 只信这一段，禁信任何继承数字）

- **HEAD**：`234a3f5`（分支 `m0-framework`）
- **四门权威读数**（源：`orchestrator/state.json` 的 `resume.baseline_authoritative.current`）：

| 门 | 命令 | 读数 |
| --- | --- | --- |
| ruff format | `uv run --no-sync ruff format --check .` | **276 files already formatted** |
| ruff check | `uv run --no-sync ruff check .` | **All checks passed!** |
| mypy | `uv run --no-sync mypy` | **Success: no issues found in 95 source files** |
| pytest | `uv run --no-sync pytest -q` | **615 passed** |

- 构成：`in_scope_py` **97** ＋ `in_scope_md` **179** ＝ 276（`ruff` 的 format 作用域含 `.md`）。
- **A223 口径（重要）**：以上是**派单时点的快照**。若你在飞期间编排器又自办入库，分母会变；
  此时**不要判「派单文失真」也不要停手空转**，改查 `resume.baseline_authoritative.history` 的累计增量后再对账。
- **解释器铁律**：一切探针/门禁一律 `uv run --no-sync python`（3.14.10）。
  **禁用系统 `python3`（3.12.3）** —— 它会对 PEP 758（`except A, B:`）假报 SyntaxError（R14-1）。
- 契约真值：`contracts/openapi.json` sha16 = `592571099d638251` / `info.version` = `1.0.1`。**本棒禁改契约**（S4 不动 `contracts/**`）。

## §2 写权面（逐条 + 额度；越界即回报，禁自行扩围）

1. **`src/campaignlab/api/jobs.py`（新建，本棒主交付）**
   公开符号**恰为**：`router, list_jobs, get_job, cancel_job, retry_job`；私有符号**恰为**：`_job_page_response, _job_response`（design §9-S4 行冻结）。
   签名与错误映射由 design **§1（第 5–13 行）** 与 **§6（第 54–65 行）** 冻结，逐字段照抄，禁自创。
2. **`src/campaignlab/api/common.py`（append-only，A91 / A82）**
   **只允许追加 `JobPage`**（及其必需的 import）。硬额度：`git diff --numstat` 的 **deleted 必须为 0**；
   既有 `__all__` 的 **78 项一字不改、一项不删、顺序不动**，只在末尾追加；追加后 `__all__` 长度 = **79**。
   `PROBLEM_CODES`（**20** 个）与 `DomainError` 子类（**14** 个）**禁改**（它们是 M2-01 后续 S3/S4 的契约判据）。
3. **`src/campaignlab/api/app.py`（A10 最小例外，≤3 行）**
   **只在第 156 行的既有注释占位处**追加：`from campaignlab.api import jobs` 的位置按文件既有体例（顶部 import 区），
   以及 `app.include_router(jobs.router)`（条件形式与紧邻的 `if workspace_service is not None:` 同形或无条件，见 §4④）。
   硬额度：**≤3 行 added、0 deleted**；禁改 `openapi_url=docs_url=redoc_url=None`、中间件添加顺序、`ALLOWED_HEADERS`、既有三处 `include_router`。
4. **`tests/integration/jobs/test_jobs_router_s4.py`（新建，本棒守护）**
   本棒的守护与用例**全部写在这一个文件里**，**含它自己需要的 fixture**。
   **禁新建 / 禁修改 `tests/integration/jobs/conftest.py`** —— 该文件属 M0-04/S5 的写集（design §9-S5 行点名 9 个 fixture），
   你先建就会造成双主写（N4 同型）。fixture 就地定义在你的测试文件内即可，重复不是问题，争用才是。
5. **`evidence/M0/M0-04/`（追加）**：`s4-jobs-router.md`（交付说明 + U 项）、`commands-s4.md`（逐条命令 + rc + 时间戳）、
   `positive-control-s4.log`（阳性对照原始输出）。**禁改**该目录下 S2c/S2b-*/S7 的既有件。
6. **`orchestrator/handoff/M0-04-design.md`（A214 窄豁免：仅文末追加）**
   只允许在**文件末尾**追加「§9-S4 行 · S4 落地注记」一节，`deleted` 必须为 **0**；
   **前 256 行必须逐字节不变**（编排器会算 sha256 对账）。历史文本只加注不改写（D-011）。

## §3 硬禁清单（碰一条即停手回报）

- **禁碰** `src/campaignlab/worker/**`（`service.py` / `store.py` / `deps.py` / `runner.py` / `states.py` / `integrity.py` / `leases.py` / `capacity.py` / `errors.py` 全部冻结；
  你只**调用** `worker/deps.py::get_job_service` 与 `worker/service.py::JobService`，不改它们）。
  特别地：**禁改 `worker/deps.py:120` 的 `get_job_service` 提供器形态**（A206/A207 已冻结）。
- **禁碰** `src/campaignlab/api/deps.py`（邻居 lane S2b-1 的写集）、`src/campaignlab/api/{health,session,workspaces,activities,rules}.py`、
  `src/campaignlab/application/**`、`src/campaignlab/domain/**`、`src/campaignlab/infra/**`、`src/campaignlab/config.py`、`src/campaignlab/cli.py`。
- **禁碰** `contracts/**`、`spec/**`、`prototype/**`、`web/**`、`scripts/**`、`pyproject.toml`、`migrations/**`、`orchestrator/state.json`。
- **禁碰** `tests/unit/test_domain_errors.py`、`tests/unit/test_layering_edges.py`、`tests/unit/test_clock.py`、
  `tests/integration/jobs/{test_worker_deps.py,test_artifact_write.py,__init__.py}`、`tests/unit/test_worker_service.py`。
- **禁发明问题码**：只用 `API.md:22–29` 的 **20** 个权威 code（D-019）；`JOB_INTERRUPTED` **禁**提升为 `Problem.code`，
  它只能落在 `Problem.issues[0].code`（N7③ 已裁）。
- **禁取系统当前时间**：`src/campaignlab/**` 下**禁**出现 `datetime.now(` / `.utcnow(` / `time.time(` 的**任何**字面量 ——
  连 **docstring 和注释里也不要写**！守护 `tests/unit/test_clock.py` 是**逐行源文本正则**、不是 AST（**D-045 就是这么踩的**）。
  需要「现在」一律 `clock: Clock = Depends(get_clock)` 由调用方传入。
- **禁写第二份游标实现**：`encode_cursor` / `decode_cursor` / `canonical_json` 一律 import `api/common.py` 的那一份；
  `CURSOR_VERSION` / `BAD_CURSOR_DETAIL` 一律 import `application/workspace_service.py` 的那一份（A169③；现状由 A222/FU-46 追认）。
  `400 BAD_CURSOR` 的 detail 必须与 `worker/service.py` 里的**同一句**（禁写第二句）。
- **禁 `sleep` / 禁 `time.monotonic` 判定**（时间一律 `FixedClock` / `advance_clock` 形态的替身）。
- **禁在 src 内放业务 handler**（N8：测试在 conftest/测试文件内注册桩）。
## §4 五条强制义务（源：`tasks.M0-04.s4_obligations_R15`，由 A220/A91/A169③/A10/A223 裁定而来；回收时逐条对账）

**① A220：`listJobs` 的 `404 RESOURCE_NOT_FOUND` 必须由你在路由侧产生。**
- 背景：design §6 给 `listJobs` 声明「404 工作区不存在或属外工作区」，但 A206 把 `JobService.__init__` 钉成只有 `store=`，
  而 `JobStore` 没有工作区查读面 ⇒ **服务层无法产生这条 404**，只能由路由层产生。
- 做法：在调用 `svc.list_jobs(...)` **之前**先核工作区存在性与归属。可用的既有面：
  `api/deps.py::get_workspace_service(request)`（已在 `__all__` 内，返回 `WorkspaceService` Protocol）与
  `api/deps.py::require_session`（取 `actor`）。**禁给 `JobService` 加第二个注入项**（那要动 `worker/deps.py:135`，超出 A207 窄豁免）。
- 若 `app.state.workspace_service` 未装配（`create_app()` 允许它为 `None`），`get_workspace_service` 会抛 `RuntimeError`。
  此时**不要**吞异常、也**不要**改成 500：按 §9 写 U 项上报你的处置倾向（两个候选：(a) 该情形下 jobs 路由整体 404；
  (b) `create_app` 未装配 workspace_service 时不挂载 jobs.router）。**先按 (b) 实现**（与既有 `if workspace_service is not None:` 体例一致、
  零新语义），并在 U 项里写明，等编排器追认或改裁。
- `getJob` / `cancelJob` / `retryJob` 的跨工作区 404 由 `JobStore`/`JobService` 既有的 `workspace_id` 过滤承担（design §7），
  你**不需要**为它们再加一层工作区核验，但**必须**把 `actor` 的当前工作区 id 正确传下去。

**② A91：`JobPage` 在 `api/common.py` 以 append-only 追加。**
- `items` 的元素类型 = `Job`（已存在于 `__all__`）；行→DTO 的映射**唯一**来源是 `infra.db.repositories.job_from_row`（N5，禁复制第二份）。
  注意：`worker/service.py::JobService.list_jobs` 返回的是**领域/DTO 层结果**（`JobRecord` 序列 + 未编码游标载荷），
  **HTTP 分页壳由你组装**（A169④）。
- `JobPage` 必须 `model_config = ConfigDict(extra="forbid")`（design §2 的 DTO 通用约束），字段与 `contracts/openapi.json` 的
  `listJobs` 200 响应 schema **逐字段对齐**（自己读契约取真值，禁猜）。
- 追加后必须让 `tests/unit/test_domain_errors.py::test_common_public_surface_is_unchanged` 仍绿 —— 该用例断言的是 `len(__all__)`，
  它当前值为 **78**（A218 裁为「按实取值更新」）。你追加 1 项后它会变 79 ⇒ **该用例会红**。
  **处置（已预裁，照做即可，不必再报 U 项）**：把该用例断言里的 `78` 更新为 `79`，**只改这两个数字字面量**，
  函数名与 docstring 的语义升级**禁碰**（归 FU-48）。这是本棒对 `tests/unit/test_domain_errors.py` 的**唯一**授权改动，
  `git diff --numstat` 必须 ≤ `2 added / 2 deleted`；改完在 `evidence/M0/M0-04/commands-s4.md` 里贴上 diff 原文。

**③ 游标的编解码归你（A169③）。**
- `worker/service.py` 收发的是**未编码**载荷 `{"v":1,"q":<16hex>,"k":[created_at,id],"s":actor_id}`；
  `str ↔ payload` 的编解码与 `query_digest` 的计算（公式见 design §1）**全部在 `api/jobs.py` 内完成**。
- `encode_cursor` / `decode_cursor` / `canonical_json` 从 `api/common.py` import；`CURSOR_VERSION` / `BAD_CURSOR_DETAIL`
  从 `application/workspace_service.py` import。禁写第二个版本号、禁写第二句 detail。
- 载荷的**绑定校验**（版本 / 查询摘要 / actor / `k` 形状 → `400 BAD_CURSOR`）留在 `worker/service.py`（它同时握有本次请求的
  `limit`/`q`/`status`/`actor_id`）⇒ 你**只负责编解码与传参**，禁在路由层重复实现一遍校验。
- `CURSOR_MAX_LENGTH` 已在 `api/common.__all__` 内，超限的处置照 design §1/§6。

**④ A10：`api/app.py` 的挂载 ≤3 行，且本棒必须先于 M2-01/S2b-2。**
- 第 156 行既有注释占位：`# M0-04/S4（A10 最小例外，≤3 行）：app.include_router(jobs.router)`。
- 你在该处落地挂载；**体例与紧邻的 `if workspace_service is not None:` 一致**（见 §4① 的 (b) 候选）。
- **禁**顺手为 M2-01 加 `activity_service` / `rule_service` 形参或 `include_router(activities.router)` / `include_router(rules.router)`
  —— 那两个 router 模块**尚不存在**（`api/activities.py` 归 M2-01/S3、`api/rules.py` 归 M2-01/S4），照字面加必然悬空 import（D-043/A217）。

**⑤ 上工第 0 步的复测口径（PRE-7 / PRE-11 / A223）。**
- 见 §6。**特别注意 PRE-11**：工作树里可能出现邻居 lane（M2-01/S2b-1）的半成品。
  你复测四门时若判红，**先判红因是否落在你的写集内**；若红因来自 `application/activity_service.py`、`infra/db/repositories.py`、
  `api/deps.py` 或它们的测试 ⇒ **那是邻居的件，不是你的责任，也不要试图修它**，记录下来、绕开（只跑与你相关的用例子集），
  并在回执里如实说明。**禁把邻居的在飞件当成自己的交付面去复验或修改。**

## §5 冻结面实测读数（编排器于 HEAD `234a3f5` 现跑取得；PRE-7 要求你上工再测一次并与本表对账）

| 冻结面 | 实测读数 |
| --- | --- |
| `src/campaignlab/api/common.py` | 1153 行 / 45039 B / sha256[:12]=`31a84b00f02c`；`__all__` = **78** 项（AST 与运行期双口径一致，`set` 亦 78，不可解析名 `[]`）；`PROBLEM_CODES` = **20**；`JobPage` **不在** `__all__`（待你追加）；`Job`/`ObjectRef`/`Problem`/`Issue`/`encode_cursor`/`decode_cursor`/`canonical_json`/`accepted_response`/`problem_response`/`etag`/`check_if_match`/`CURSOR_MAX_LENGTH` **均已在** `__all__` |
| `src/campaignlab/api/app.py` | **158** 行；`create_app` 在第 **87** 行；`include_router` 区块在第 **149–156** 行（`health` 149 无条件、`session` 153 条件、`workspaces` 155 条件）；第 **156** 行是本棒的注释占位；`openapi_url=None` 在第 **121** 行 |
| `src/campaignlab/api/deps.py` | **172** 行；`__all__` = **10** 项（`HealthService, SessionService, WorkspaceService, get_clock, get_config, get_health_service, get_session_service, get_workspace_service, require_session` ＋ 首项）；**本棒禁改**（邻居写集） |
| `src/campaignlab/worker/service.py` | **256** 行 / 12924 B / sha256[:12]=`7b0dd1591fd5`；`class JobService` 方法**恰** `__init__, list_jobs, get_job, cancel_job, retry_job`；`__init__(self, *, store: JobStore) -> None`；模块级私有函数**恰** `_parse_status, _cursor_key, _next_cursor_payload`（合计 def 面 **8** 个，已钉成守护） |
| `src/campaignlab/worker/deps.py` | **156** 行；`get_job_service(config: AppConfig = Depends(get_config)) -> JobService` 在第 **120** 行附近，返回 `factory(store=get_job_store(config))`；**本棒禁改** |
| `src/campaignlab/api/jobs.py` | **ABSENT**（待你新建） |
| `tests/integration/jobs/` | 现有 `__init__.py` / `test_artifact_write.py` / `test_worker_deps.py`（632 行 / 18 个 `def test_`）；**无 `conftest.py`**（属 S5，你禁建） |
| `tests/unit/test_domain_errors.py` | 189 行 / 7771 B / sha256[:12]=`e2f9fba56bf0`；**12** 个用例；`test_common_public_surface_is_unchanged` 断言 `len(__all__) == 78` 两处（见 §4②） |

## §6 上工第 0 步（**强制、只读**；未做完禁写任何文件）

```bash
cd /home/szf/dev/CampaignLab
git rev-parse --short HEAD                                   # 期望 234a3f5
git status --porcelain=v1 -uall                              # 记录在树面；区分「你的」「邻居的」
uv run --no-sync ruff format --check .                       # 期望 276 files already formatted
uv run --no-sync ruff check .                                # 期望 All checks passed!
uv run --no-sync mypy                                        # 期望 Success: no issues found in 95 source files
uv run --no-sync pytest -q                                   # 期望 615 passed
```

- 与 §1 不符 ⇒ **先查 `resume.baseline_authoritative.history`**（A223）：若差异可由编排器中途自办入库解释，继续；
  若无法解释，停手回报，**禁自行改判据**。
- 若红因落在邻居 lane 的写集（§4⑤ / PRE-11）⇒ 记录、绕开、继续，回执里如实说明。
- 再按 §5 逐条复测冻结面（用 `uv run --no-sync python` 跑 AST 探针，禁系统 `python3`），把实测值写进 `evidence/M0/M0-04/commands-s4.md`。
- **然后**才开始写代码。

## §7 交付物与取证要求

1. `src/campaignlab/api/jobs.py`：4 个 operationId 的路由 + 2 个私有组装函数，签名逐字段照 design §1、错误映射照 §6。
2. `src/campaignlab/api/common.py`：`JobPage` append-only（`deleted=0`，`__all__` 78→79）。
3. `src/campaignlab/api/app.py`：≤3 行挂载（`deleted=0`）。
4. `tests/unit/test_domain_errors.py`：仅 §4② 授权的两处数字（≤2/2）。
5. `tests/integration/jobs/test_jobs_router_s4.py`：本棒守护 + 用例，**自带 fixture**。至少覆盖：
   - `listJobs` 200 分页壳逐字段对齐契约（含 `next_cursor` 为空/非空两态）；
   - `listJobs` 的 `404 RESOURCE_NOT_FOUND`（工作区不存在 / 属外工作区）——**这是 §4① 的验收点，必须有例**；
   - `status` 多值（逗号分隔）与非法值的处置（N7① 已裁为逗号分隔多值）；
   - `getJob` 200 与 404；`cancelJob` 的 200 / 409 / 412 / 428 四态（`If-Match` 缺失 → **428**，陈旧 → **412**）；
   - `retryJob` 的 202（`accepted_response` 的 `Location` 与 `Retry-After` 语义照 design §1/§6）与 429（`JOB_CAPACITY` + `Retry-After`）；
   - `400 BAD_CURSOR`（游标版本/摘要/actor/`k` 形状任一不符，detail 与 `worker/service.py` 同句）；
   - `Problem` 体的 `code` **必属** 20 个权威码；`JOB_INTERRUPTED` 只出现在 `issues[0].code`（N7③）。
6. **阳性对照（positive control）≥8 条**，每条必须：注入变异 → 跑对应守护 → **rc≠0** → **字节级复原** → 复跑 → rc=0，
   并把 sha256 双向核验写进 `evidence/M0/M0-04/positive-control-s4.log`。至少含：
   改 `JobPage` 一个字段名 / 删 `__all__` 里的 `JobPage` / 把 `include_router(jobs.router)` 删掉 /
   把 404 核验去掉 / 把 `BAD_CURSOR` 的 detail 改成第二句 / 在 `jobs.py` 里写一个取系统当前时间的调用（**注意：这条会触发 D-045 那个源文本正则守护，正是我们要的**）/
   把 `cancelJob` 缺 `If-Match` 的 428 改成 400 / 把 `retryJob` 的 202 改成 200。
   变异一律在 `/tmp` 或原地字节复原，**禁留残留**（复原后 `git status` 必须与第 0 步一致）。
7. `evidence/M0/M0-04/{s4-jobs-router.md, commands-s4.md, positive-control-s4.log}`；
   `s4-jobs-router.md` 必须含「交付面逐文件行数/字节/sha256[:12] + numstat」「U 项（只报不裁，每条给两个候选 + 你的倾向 + 理由）」「未触碰的硬禁面收尾复核」三节。
8. `orchestrator/handoff/M0-04-design.md` 文末追加「§9-S4 行 · S4 落地注记」（`deleted=0`，前 256 行逐字节不变）。

## §8 loop engineering（自迭代，最多 2 轮）

- **第 1 轮**：实现 → 自跑四门 + 你的新用例 → 定位红因 → 修 → 复跑。**每轮都要把命令与 rc 追加进 `commands-s4.md`**（append-only，禁删改前轮记录）。
- **第 2 轮**：仍不绿 ⇒ **停手回报**，写清「已试过什么、红因是什么、你判断卡在哪、需要编排器裁什么」。**禁第 3 轮**、禁为了让门变绿而削弱守护/删用例/放宽断言。
- 全程禁：`git commit`（入库一律由编排器执行）、`git push`、改 `orchestrator/state.json`、改 `pyproject.toml`、`uv add`/`uv sync`。

## §9 U 项上报规则（只报不裁）

- 任何「本文件与设计文档冲突」「设计文档自相矛盾」「契约与实现口径不一致」「需要动硬禁面才能完成」的情形：
  **停在该点，写 U 项**，编号 U-1、U-2 …，每条给：**事实（附实测证据）+ 两个候选 + 你的倾向 + 理由 + 影响面**。
- 禁自行裁定、禁自行扩围、禁「先做了再报」。编排器回收时逐条终裁（先例：A219–A224）。
- **诚实上报优先**：越界了就说越界了，超限了就说超限了。如实上报不扣分，隐藏或粉饰按缺陷入账（先例：D-044）。
- 令牌/上下文超限也如实报（§5.1 单轮输入上限、§15.5 累计上限），无计量句柄就写明是估算值。

## §10 回执格式（最后一条消息，编排器只认这个）

```
STATUS: DONE | DONE_WITH_GAP | BLOCKED
LOOP_ROUNDS_USED: n / 2
GATES: ruff_format=<读数> ruff_check=<rc> mypy=<读数> pytest=<读数>   # 你末态在活动工作树上的实测
DELIVERED: 逐文件 <路径> <added>/<deleted> <行数> <字节> <sha256[:12]>
FROZEN_FACE_DIFF: api/common.__all__ 78→? ; api/app.py 行数 158→? ; design.md 前 256 行 sha 是否未变
POSITIVE_CONTROLS: n 条，全红？复原后 sha 是否全等？
U_ITEMS: 逐条（无则写 NONE）
SELF_REPORTED_VIOLATIONS: 逐条（无则写 NONE）
TOKENS: <值或估算> estimated=<true|false>；单轮上下文峰值 <值或估算>
NOTES: 需要编排器注意的任何事
```

**禁采信自报**：编排器会独立复测上述每一项，不符即退回。
