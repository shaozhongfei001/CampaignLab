# R18 · lane M2-01/S3 派单文 —— `api/activities.py` 四端点铺开 ＋ app.py 挂载（A217③ / A244）

> **上工第一件事**：按 §5 逐条复测冻结面读数并与本文对账。若不符，**先查** `orchestrator/state.json`
> 的 `resume.baseline_authoritative.current`（A223 / PRE-10），对账口径＝**派单快照 ＋ 该键 history 的累计增量**；
> 不符**不要直接判失真、也不要停手空转**，按 §9 报 U。

## §0 身份、档位与预算

| 项 | 值 |
|---|---|
| 任务 / 子任务 | **M2-01**（活动与规则版本）/ **S3**（`activities` 端点 DTO 与路由铺开） |
| 轮次 / lane | Round 18 / lane **S3** |
| 档位 | **`qwen3.8-flash`** · reasoning **medium**（卡片档位表原文冻结为 flash 9k，未升降档） |
| loop | 上限 **2** 轮；超限即停手写 U 项，禁硬撑（手册 15.6） |
| 派单基线 | **含本派单文的那个提交**（tag `R18-predispatch`，其 parent = `1c591b4`）。上工时自取 sha：`git log --oneline -1 -- orchestrator/handoff/R18-lane-M2-01-S3.md`（**禁写猜测值**）· 分支 `m0-framework` · counts 基线 **305 / 107 / 734**（in-scope **109 py + 196 md**；305 与 196 已计入本批 **+3 in-scope md** ＝ 两份 R18 派单文 ＋ `orchestrator/defects/D-050.md`） |
| 前置已满足 | `s3_unblocked_R17`：`app.py` 的 `activity_service` / `rule_service` 两个注入位与 `app.state` 键名已由 **S2b-2**（`87c897a`）落地；`api/deps.py` 的 `ActivityService` Protocol（**4** 个成员，非空端口，PRE-5 已实测）与 `get_activity_service` 提供器已由 **S2b-1**（`a0ee343`）落地；`application/activity_service.py`（2000 行 / 88950 B）实现已在位 ⇒ **本棒是纯铺开，零设计裁量** |
| 并行邻居 | lane **S6**（M0-04：新建 `tests/integration/jobs/test_lease.py` ＋ `test_artifact.py`）—— 写集与你**零交叉**；它的文件对你而言是 **IN_FLIGHT_CONTAMINATION**：**禁改、禁 add、禁 checkout、禁 clean / reset / stash**（PRE-11 / A161） |
| 串行约束 | **S4 与本棒互斥**（同改 `api/app.py`，N4 禁双主写）⇒ S4 必须排在本棒入库之后（`remaining_sequence_R17_post_S2b2`） |

## §1 写权面（新建 3 件 ＋ 改 1 件；越界即按 §9 报 U，禁自行扩大）

```
src/campaignlab/api/activities.py            （新建 · 主交付件）
src/campaignlab/api/app.py                   （修改 · **numstat added ≤3 / deleted = 0**，见 §3.4 与 A244）
tests/api/activities/__init__.py             （新建 · D-035：tests/** 各级都要有 __init__.py；该目录当前不存在）
tests/api/activities/test_activities_router_s3.py （新建 · 履行 s3_precondition_note_R17 的端到端判据义务）
```

`tasks["M2-01"].s3_precondition_note_R17.obligation` **原文**（逐字，禁改写）：

> S3（api/activities.py ＋ 在 app.py 挂载）必须**同批**补上端到端判据：注入 activity_service 后，经 TestClient 走一条真实
> activities 路由，断言 deps.get_activity_service 取到的对象与注入对象**同一**（is），以闭合 S2b-2 只做到「键名双向对撞」
> 的代理证明；S4 对 rule_service 同理。

读取面（PRE-19：限定路径 ＋ 输出上限 ＋ 排除散文面；**禁**无界 `grep -rn` / `rg` 全仓）：

```
sed -n '1,113p' src/campaignlab/api/workspaces.py
sed -n '39,120p' src/campaignlab/api/jobs.py
sed -n '178,300p' src/campaignlab/api/jobs.py
sed -n '22,100p' orchestrator/handoff/M2-01-design.md
sed -n '1073,1082p' orchestrator/handoff/M2-01-design.md
sed -n '125,175p' src/campaignlab/api/app.py
grep -n -e 'def list_activities' -e 'def get_activity' -e 'def create_activity' -e 'def update_activity' src/campaignlab/application/activity_service.py
grep -n -e 'class ActivityService' -A 30 src/campaignlab/api/deps.py | head -45
grep -n -e 'Activity' -e 'IF_MATCH' -e 'IDEMPOTENCY_KEY_HEADER' src/campaignlab/api/common.py | head -40
```

## §2 硬禁面（**逐条**，含 PRE-14 要求的「预期红清单」）

1. **禁改** `src/campaignlab/api/deps.py`、`application/**`、`domain/**`、`infra/**`、`api/common.py`、`api/session.py`、
   `api/workspaces.py`、`api/jobs.py`、`api/health.py`、`api/rules.py`（那是 **S4** 的写集，本棒禁创建）。
   若发现被依赖符号缺失或语义不符 ⇒ 按 §9 报 U，**禁就地修**（手册 6.4：flash 只在 max 设计划定的文件与函数内工作）。
2. **禁改** `contracts/**`、`spec/**`、`scripts/**`、`orchestrator/**`、`web/**`、`migrations/**`、`evidence/**`
   （M2-01 的取证件归 **S7**）、`pyproject.toml`、`uv.lock`、`README.md`。
3. **禁改任何既有测试件**：`tests/unit/**`、`tests/api/{conftest.py,test_contract_declarations.py,test_contract_http.py}`、
   `tests/integration/**`、`tests/domain/**`。sha 见 §5，回收时逐件对撞。
4. `api/app.py` 只准做 §3.4 那 **3 行**：**禁**改 `openapi_url=docs_url=redoc_url=None`、中间件添加顺序、`ALLOWED_METHODS` /
   `ALLOWED_HEADERS`、`app.state` 既有 **8** 个键、既有 **4** 处 `include_router`（health / session / workspaces / jobs）与
   `create_app` 的既有 **7** 个 kwonly 形参（`s3_precondition_note_R17.hard_ban` 原文）。
5. 不执行 `git commit / push / add / reset / checkout / clean / stash`；不 `sudo`。
6. **禁写 SQL**（design §1 公共约定：路由体只做「解析 → 调 service → 组装响应」）；**禁**在路由里现编 `title` / `detail`
   （ADR-005 §2.2 固定中文短句表，detail 一律由 service 侧常量给出）；**禁**用系统当前时间（显式时钟）。

### 2.1 预期红清单（PRE-14：本棒落地后**必然**打红 **2** 件既有哨兵；**它们不在你的写权面，禁修，报 U 即可**）

编排器派单前已逐条实测（命令原文见 §5），下列 **2** 条判据在本棒落地后必红，依 **A224 / A226 同批纪律**由
**编排器在入库提交内同批迁移**（先例＝M0-04/S4 入库时编排器迁移 `test_contract_declarations.py` 24/1 与
`test_s3b_routes.py` 14/2）：

| # | 哨兵 | 红的判据（实测行号） | 红因 |
|---|---|---|---|
| E1 | `tests/unit/test_s3b_routes.py::test_app_py_contains_only_the_a85_mount_lines` | `:207 assert len(mounted_lines) == 4`；`:194-198` 的 `pairs` 三元组；`:201-203` 的三条 `import router as X_router` 断言；`:209-211` 的每 router 出现行数 ≤3 | 挂载行 **4→5**，且新增 `import router as activities_router` |
| E2 | `tests/unit/test_s2b2_app_injection.py::test_g6_mount_and_middleware_surface_unchanged` | `:62-67 EXPECTED_MOUNT_LINES`（**4** 项有序清单）＋ `:268 assert ordered == EXPECTED_MOUNT_LINES`；`:36-38 _BANNED_ROUTER_MODULES = frozenset(f"campaignlab.api.{leaf}" for leaf in ("activ"+"ities","rul"+"es"))` ＋ `:273-274 assert not banned_hits` | 有序清单 **4→5**；且 A217③ 当初为 S2b-2 立的「禁 import activities」禁令自本棒起**到期失效**（该禁令的立法目的正是把 import 权留给 S3） |

**明确不红**（编排器已实测，禁你自己去改它们）：

- `tests/api/test_contract_declarations.py`：其 `mounted_paths` 取自 `(session_api, workspaces_api, health_api)` 三个模块的
  `router.routes`（`:152-156`），**不是**从 app 全量路由取；`_ALL_OPS` 取自 `M0-02.slice.json`（`:206`）⇒ 本棒不影响它。
- `tests/unit/test_api_app.py::test_jobs_router_is_not_mounted_by_s3c`：用**裸装配**（不注入任何 service）探 404；
  activities 是**条件挂载**（`if activity_service is not None:`）⇒ 裸装配下不挂载 ⇒ 不红。
- `tests/unit/test_s3d_application.py`：只断言 session / health / workspace 三个 `app.state` 身份与「不注入就不装配」⇒ 不红。
- `tests/unit/test_s2b2_app_injection.py` 的 **G1–G5、G7–G9**（kwonly 有序 7 名、`EXPECTED_WIRING` 5 项、
  `app.state` 身份、`_protocol_members` 双向对撞、deps 键名对撞）⇒ 本棒不动这些面，**不红**；只有 **G6** 红。

⇒ 你在 §10 回执里必须**原样贴出** E1 / E2 的红文本（`pytest -q` 的 FAIL 段），**禁**修改这两个文件、**禁**把它们算作你的失败。
除 E1 / E2 之外的任何红都是真信号 ⇒ 按 §9 报 U。
## §3 目标形态（**逐字**依据；本棒零设计裁量，形态已由 max 档设计冻结）

### 3.1 `api/activities.py` 的符号面（design §11.4 原文，`M2-01-design.md:1073-1081`）

> `router`（`APIRouter(prefix=API_PREFIX, tags=["activities"])`）· `list_activities` · `create_activity` ·
> `get_activity` · `update_activity` · 私有 `_activity_response(activity, *, request_id, status=200)`（组装 `ETag`）·
> 私有 `_activity_page_response(page, *, request_id)`（**不带 ETag**，§6.1）· `__all__`（以 `inspect` 实取为准）。
> 四个 handler 的签名逐字照 §1.1–§1.4；装饰器一律 `operation_id="<operationId>"` + `responses=declared_responses(<2xx>)`；
> 函数体一律「解析 → 调 service → 组装响应」＋ `except DomainError as exc: return problem_response(exc, request_id=…)`；
> `Depends(...)` 作默认值的两行照 `api/workspaces.py` 就地 `# noqa: B008`（A47 / 手册 §9.9 的既有豁免口径，禁改 `pyproject.toml`）。

⇒ **公开面恰 5 名**（`router` + 4 个 handler），**私面恰 2 名**（`_activity_response` / `_activity_page_response`）。
`__all__` 必须**字母序**（RUF022，实测先例 `api/jobs.py::__all__` = `cancel_job, get_job, list_jobs, retry_job, router`）：
`["create_activity", "get_activity", "list_activities", "router", "update_activity"]`；私有两名**不进** `__all__`。

### 3.2 四个 handler 的装饰器与 2xx（design §1.1–§1.4 实测；权威原文＝`M2-01-design.md:22-100`，用 §1 的受限命令自读）

| operationId | 方法 + 路径 | 2xx | ETag | 幂等键 | If-Match | 正文 DTO |
|---|---|---|---|---|---|---|
| `listActivities` | GET `/workspaces/{workspace_id}/activities` | **200** `ActivityPage` | **无**（切片实测 200.headers 只有 `X-Request-Id`，禁发明） | 无 | 无 | 无 |
| `createActivity` | POST 同路径 | **201** `Activity` | **有** | `Idempotency-Key` 必填（8–128） | 无 | `ActivityCreate` |
| `getActivity` | GET `/workspaces/{workspace_id}/activities/{activity_id}` | **200** `Activity` | **有** | 无 | 无 | 无 |
| `updateActivity` | PATCH 同 getActivity | **200** `Activity` | **有** | 必填 | 契约 `required=true`，**实现侧必须声明为可选**（见下） | `ActivityUpdate` |

- 装饰器一律 `responses=declared_responses(<2xx>)`，`declared_responses` 与 `JSON_MEDIA_TYPE` **实测来自
  `campaignlab.api.session`**（`api/jobs.py:69` 与 `api/workspaces.py:43-47` 的先例），**不在** `api/common.py::__all__` 内。
- `If-Match`（design §1.4 原文，`:80-84`）：`if_match: str | None = Header(None, alias="If-Match", min_length=3,
  max_length=32, pattern=IF_MATCH_PATTERN)`，**再由 service 调 `api/common.py::check_if_match`** —— 若照契约声明为必填，
  Starlette 会在缺头时先抛 `RequestValidationError` 得到 **422**，契约要求的 **428 `PRECONDITION_REQUIRED`** 就永远不可达。
  `check_if_match` 的**调用点**以 `application/activity_service.py::ActivityService.update_activity` 的**实测签名**为准：
  签名已收 `if_match` ⇒ 由 service 调；未收 ⇒ 在路由层调（照 `api/jobs.py::cancel_job` 的 **A228** 先例）。
  **两者择一**并在回执写明依据，**禁**两处都调（会产生第二真源，N5）。
- 路径参数一律 `workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN)`，`activity_id` 同形
  （design §1 公共约定 `:42-44`：三者的 `minLength`/`maxLength`/`pattern` 切片实测逐字相同）。
- `listActivities` 的四个 query 形参逐字照 design §1.1（`:51-54`）：`cursor: str | None = Query(None, min_length=1,
  max_length=300)`、`limit: int = Query(25, ge=1, le=100)`、`q: str | None = Query(None, min_length=1, max_length=100)`、
  `status: str | None = Query(None, min_length=1, max_length=60)`。**排序/键集/游标/白名单/422 位置全在 service 侧**，
  路由层只透传（禁在路由里重算游标、禁第二把密钥、禁第二句 detail）。
- 有正文的 2 个 op（`createActivity` / `updateActivity`）正文解析一律走 design §1 公共约定（`:38-41`）的三连：
  `validate_idempotency_key(<header>)` → `await read_body_within_limit(request, max_bytes=get_config(request).max_json_body_bytes)`
  → `parse_json_body(body, request.headers.get("content-type"), <DTO>)`（三个助手全部来自 `api/common.py`，禁复制第二份）。

### 3.3 函数体体例（**照抄实测先例**，禁自创；`api/workspaces.py:84-112` 全文已在 §1 的读取面里）

```python
request_id = request_id_of(request)
try:
    key = validate_idempotency_key(idempotency_key)
    max_bytes = get_config(request).max_json_body_bytes
    body = await read_body_within_limit(request, max_bytes=max_bytes)
    payload = parse_json_body(body, request.headers.get("content-type"), ActivityCreate)
    outcome = svc.create_activity(
        payload=payload, body=body, idempotency_key=key, actor=actor, request_id=request_id
    )
    return replay_from_envelope(outcome.as_envelope(), request_id=request_id)
except DomainError as exc:
    return problem_response(exc, request_id=request_id)
```

实测：`application/activity_service.py::ActivityCreateOutcome`（`:243-256`）与 `ActivityWriteOutcome`（`:260-270`）
都有 `as_envelope()`，字段序 `status / headers / body / replayed`，且**刻意不含** `X-Request-Id`（重放时必须重新生成，
由 `replay_from_envelope(..., request_id=...)` 覆盖）⇒ `createActivity` 与 `updateActivity` 都走信封路径，
**禁**在路由里自己拼 `Response`。`listActivities` / `getActivity` 无信封，走 `_activity_page_response` / `_activity_response`。
**注意**：`svc.create_activity(...)` 的**真实关键字名以实测签名为准**（用 §1 的 grep 命令自取），若与上例不同，
按实测写并在回执注明；**禁**改 service 侧签名（§2.1）。

### 3.4 `api/app.py` 的 3 行（A244 裁定：额度＝**numstat added ≤3 / deleted = 0**，逐字照 M0-04/S4 先例）

先例实测（`git show c39b17e -- src/campaignlab/api/app.py`，numstat **3/0**）：S4 只加了 1 行 import ＋ 1 行 `if` ＋
1 行 `include_router`；那行 `# M0-04/S4（A10 最小例外，≤3 行）…` 注释是**既存占位**、不是新增行。
本棒**没有**既存占位注释可用 ⇒ **禁加注释行**（加了就是 4 行、超额）。目标 3 行：

```python
from campaignlab.api.activities import router as activities_router     # ← 插进 import 块的正确字母序位（在 `from campaignlab.api.common import (` 之前；ruff 的 I001 会校验）
...
    if activity_service is not None:
        app.include_router(activities_router)
```

挂载位：**在既有 `if workspace_service is not None: app.include_router(jobs_router)`（当前 `:170-171`）之后、
`return app`（当前 `:172`）之前** ⇒ 挂载顺序为 health → session → workspaces → jobs → **activities**
（`EXPECTED_MOUNT_LINES` 的有序清单要求追加在尾部）。条件形如既有先例（design §11.3 原文：「条件与既有
`if workspace_service is not None:` 同形」），本棒用 **`activity_service`**（不是 `workspace_service`）。

## §4 判据（回收时编排器**逐条独立复验**，禁采信你的自报）

| 判据 | 命令（逐字） | 期望 |
|---|---|---|
| V1 本棒新守护 | `uv run --no-sync pytest -q tests/api/activities` | rc=0；collected **≥1**（端到端 `is` 同一性那条例） |
| V2 全量 | `uv run --no-sync pytest -q` | **恰 2 条 FAIL ＝ E1 / E2**（§2.1 的预期红，编排器同批迁移），其余全 passed；rc≠0 属**预期**，你必须在回执贴出两条 FAIL 原文 |
| V3 质量门 | `uv run --no-sync ruff check .` / `ruff format --check .` / `mypy` | 各 rc=0（计数不写死；权威现值见 `state.json -> resume.self_check_gates_rc0.counts`） |
| V4 app.py 额度 | `git diff --numstat HEAD -- src/campaignlab/api/app.py` | **`3	0`** 或更小 added，deleted **必须 0** |
| V5 挂载面 | AST 实取 `include_router` 调用点 | **5** 个，其中含 `activities_router` **恰 1**；既有 4 个逐字未变 |
| V6 符号面 | AST 实取 `api/activities.py` | 公开面**恰** `{router, list_activities, create_activity, get_activity, update_activity}`；私面**恰** `{_activity_response, _activity_page_response}`；`__all__` 5 名且字母序 |
| V7 声明面 | AST 实取 4 个装饰器 | `operation_id` 逐字 = `listActivities` / `createActivity` / `getActivity` / `updateActivity`；`responses=declared_responses(200/201/200/200)` |
| V8 红线 | `grep -n -e 'SELECT' -e 'INSERT' -e 'UPDATE ' -e 'datetime.now' -e 'utcnow' -e 'time.sleep' src/campaignlab/api/activities.py` | **0 命中**（含注释与 docstring；若必须提到这些词，用字符串拼接自指形态避免自匹配，D-049③ 教训） |
| V9 端到端 | 你的 `test_activities_router_s3.py` | 注入 `activity_service` 后经 `TestClient` 走一条**真实** activities 路由，断言 `deps.get_activity_service` 取到的对象与注入对象 **`is` 同一**（`s3_precondition_note_R17` 原文义务；**注意** `is` 同一性是**进程内对象身份**判据，不跨越序列化/HTTP 边界 ⇒ 必须在同进程内取到该对象本身，禁拿响应体字段代理） |
| V10 不回退面 | AST/grep 实取 app.py | `app.state` 键仍 **8** 个；`add_middleware` 顺序未变（guard 最内 → CORS → request_id 最外）；`openapi_url=docs_url=redoc_url=None`；`ALLOWED_METHODS` / `ALLOWED_HEADERS` 未变；`create_app` kwonly 形参仍 **7** 名有序 |
| V11 冻结面 | `git diff --numstat HEAD -- src tests ':!src/campaignlab/api/activities.py' ':!src/campaignlab/api/app.py' ':!tests/api/activities'` | **输出为空** |

## §5 冻结面读数（PRE-15：**全部由编排器脚本实测**，`.orch_tmp/r18_s3_deps.py` / `r18_frozen_readings.py`）

```
src/campaignlab/api/app.py                    173 行 /  7576 B / f039722660bb   ← 你只准 +3/-0
src/campaignlab/api/deps.py                   347 行 / 13524 B / ed1075a86447   ← 禁改
src/campaignlab/api/common.py                1169 行 / 45605 B / 836e7b3e8d3a   ← 禁改
src/campaignlab/api/workspaces.py             113 行 /  5045 B / 4c1d74aeeeb3   ← 体例模板，禁改
src/campaignlab/api/jobs.py                   372 行 / 16916 B / 735d30baf0c4   ← 体例模板，禁改
src/campaignlab/api/session.py                171 行 /  6945 B / 14be2b2fda59   ← declared_responses / JSON_MEDIA_TYPE 的来源，禁改
src/campaignlab/application/activity_service.py 2000 行 / 88950 B / 21425228694b ← 禁改
src/campaignlab/domain/ids.py                  64 行 /  2726 B / 4badc18586c9   ← RESOURCE_ID_PATTERN 来源，禁改
tests/unit/test_s3b_routes.py                 212 行 /  8983 B / b0122388342a   ← E1，禁改（编排器迁移）
tests/unit/test_s2b2_app_injection.py         364 行 / 14545 B / fadf666b810d   ← E2，禁改（编排器迁移）
tests/api/test_contract_declarations.py       215 行 / 11110 B / a9af20101fe7   ← 禁改，实测不红
tests/unit/test_api_app.py                    121 行 /  5271 B / a97c32a63756   ← 禁改，实测不红
tests/api/conftest.py                         194 行 /  7489 B / 2df41d5585dd   ← 禁改（可 import 其 Harness/authed 等）
```

符号面（AST 实取，PRE-20：枚举/计数类断言一律以此为准）：

- `api/deps.py::__all__` **13 名**，含 `ActivityService, RuleService, get_activity_service, get_rule_service`；
  `ActivityService` Protocol 成员 **4** 个：`list_activities, get_activity, create_activity, update_activity`
  （**非空端口**，PRE-5 的「被依赖符号已具备可用成员面」已满足）；`WorkspaceService` 2 个、`RuleService` 7 个（S4 用）。
- `api/common.py::__all__` **79 名**，实测含 `Activity, ActivityCreate, ActivityUpdate, ActivityPage, RuleVersion,
  RuleCreate, RuleUpdate, Confirmation, RuleCheck, RuleDiff, RuleVersionPage, problem_response,
  validate_idempotency_key, read_body_within_limit, check_if_match, X_REQUEST_ID_HEADER, RESOURCE_ID_PATTERN,
  JobPage, WorkspacePage`。**注意**：`parse_json_body` / `request_id_of` / `replay_from_envelope` /
  `IDEMPOTENCY_KEY_HEADER` / `IF_MATCH_PATTERN` **不在** `__all__` 里但**确实**从 `api.common` 导入可用
  （实测先例：`api/workspaces.py:26-36` 与 `api/jobs.py:48-67` 的 import 块）⇒ **照先例的 import 块逐字取用，
  禁以 `__all__` 为准去推断可用性**；若某个符号实测 import 不到，按 §9 报 U。
- `application/activity_service.py::__all__` **26 名**，含 `ActivityService, RuleService, ActivityCreateOutcome,
  ActivityWriteOutcome, RuleWriteOutcome, ACTIVITY_ID_PREFIX, ACTIVITIES_CURSOR_VERSION, activity_query_digest` 等。
- `api/app.py` 现值：`include_router` 调用点 **4**（health / session / workspaces / jobs）；`app.state` 装配 **8** 键
  （config, clock, guard, session_service, health_service, workspace_service, activity_service, rule_service）；
  `create_app` kwonly 形参 **7** 名有序；`api/activities.py` **不存在**（本棒新建）；`tests/api/activities/` **不存在**（本棒新建）。
## §6 纪律（红线，违反即判红）

1. **禁为过测改测试期望**、**禁改既有哨兵**（E1 / E2 由编排器同批迁移；你改了＝越界，整棒判红）。
2. **禁发明 code / detail / title**：`Problem.code` 只用 `domain/errors.py` 注册表内的码（实测 20 个，权威＝
   `spec/CampaignLab-SDD-v1.0/architecture/API.md:22-29`，D14 / D-019 裁定）；detail 一律用 service 侧既有常量
   （`EMPTY_PATCH_DETAIL` / `IMMUTABLE_DETAIL` / `DUPLICATE_EXTERNAL_DETAIL` / `DIGEST_MISMATCH_DETAIL` /
   `NOTE_REQUIRED_DETAIL` / `ARCHIVED_DETAIL` / `BAD_CURSOR_DETAIL` / `CONFLICT_DETAIL`），**禁**在调用点现编。
3. **禁写死**计数、指纹、状态码清单（D-012 / D-014）：状态码集合的唯一权威是装饰器上的 `declared_responses()`（A95），
   测试侧只拿切片对撞，**禁**另立清单。
4. **禁第二真源**（N5）：游标密钥只用 `application/workspace_service.py::load_cursor_secret`、`BAD_CURSOR_DETAIL` 只用
   那一句；`check_if_match` 只调一次（§3.2）。
5. mypy strict 必须过：4 个 handler 的返回类型标 `Response`（或 `-> Response`），形参类型齐全；`Depends(...)` 默认值行
   就地 `# noqa: B008`（照 `api/workspaces.py:87-88`）。
6. ruff：`__all__` 字母序（RUF022）；禁改 `pyproject.toml`；新文件必须过 `ruff format --check`。
7. **禁**在 `src` 内放业务 handler / 桩；测试桩只在 `tests/api/activities/` 内自建（N8 同型口径）。
8. **禁** `git commit / push / add / reset / checkout / clean / stash`（编排器一任务一提交）。
9. 金额用分整数、比率用十进制字符串、时区 `Asia/Shanghai`（卡片原文）；本棒只做路由铺开，**禁**在路由层做任何领域计算。

## §7 阳性对照（PRE-18 / PRE-20③：**先证变异生效，再证判据有牙**）

规则（逐字遵守）：① 每条 PC 先用 **AST / 运行期实取**断言「变异确已生效」（「文件 sha 变了」不构成证明）；
② 变异点必须是**语义合法位置**（禁追加到 `return` 之后或模块尾部导致 import 期崩溃 ⇒ 假阳性取证，A238）；
③ 跑判据、记录 rc 与红的原文；④ **字节级复原到落地态**（不是复原到派单基线；PRE-15 追加注记），复原后 sha 必须与
你落地时的 sha 逐字相同，两次 sha 都写进回执；⑤ 判红预言一律写成「**若不红则如实入档并补替代对照**」，**禁**写「必然判红」。

| PC | 变异点（只动**你自己**新建的文件） | 判据 | 预言 |
|---|---|---|---|
| PC-1 | 把 `test_activities_router_s3.py` 里的 `is` 同一性断言改成「比较某个响应头/字段相等」 | `uv run --no-sync pytest -q tests/api/activities` | 变异后**仍绿** ⇒ 证明原 `is` 断言更强（身份判据不可被字段相等替代）；随后做**主体变异**：把注入的对象换成同类型的另一个实例（`object()` 代理或第二个 stub），期望 rc≠0 |
| PC-2 | 把 `activities.py` 里某一个 handler 的 `operation_id="…"` 改成另一个 op 的名字 | AST 实取 4 个 `operation_id` 的集合 ＋ `pytest -q tests/api/activities` | 期望 AST 集合对撞判红（V7）；**若不红则如实入档并补替代对照** |
| PC-3 | 把 `app.py` 里新增的 `if activity_service is not None:` 改成无条件挂载（删掉 `if`，只留 `app.include_router(activities_router)`） | `uv run --no-sync pytest -q tests/unit/test_s2b2_app_injection.py tests/unit/test_api_app.py` | 期望 rc≠0（G6 的有序清单形态 / 裸装配 404 判据命中）；**注意** added 会变成 2 行 ⇒ 复原时必须回到 3 行落地态；**若不红则如实入档**（说明「不注入就不装配」的不变量在此处无牙，属真缺陷，报 U） |
| PC-4 | 把 `updateActivity` 的 `if_match` 形参从 `Header(None, …)` 改成契约字面的必填形态 | `uv run --no-sync pytest -q tests/api/activities` ＋ 你自建的「缺 If-Match → 428」断言 | 期望 rc≠0（缺头会得到 422 而非 428）；本棒**必须**自建这条 428 断言，否则 PC-4 无从判红 —— 若你因故未建，如实入档并说明（禁假装跑过） |

## §8 取证落点

M2-01 的 `evidence/M2/M2-01/**` 与 `evidence/M2/summaries/M2-01.md` 归 **S7**（`remaining_sequence_R17_post_S2b2` 原文：
「M2-01 的 AC 取证归 S7；本任务在 S7 入库前禁判 DONE」）⇒ **本棒禁新建任何 evidence 文件**（否则与 6 条前向引用登记面
冲突）。本棒只在回执里给出**可复现命令 ＋ rc ＋ 实数**（§4 的 V1–V11 全部），编排器独立复跑后作为 S7 取证的输入。

## §9 U 项协议（只报不裁；编排器逐条终裁）

遇到下列情形**立即停手该条、写 U 项**，禁自行决定（手册 6.4）：

- `ActivityService` 的实测签名与 design §1.1–§1.4 的形参/关键字名不符（尤其 `update_activity` 是否收 `if_match`）；
- §3.2 表里的某个 DTO / 助手符号实测 import 不到（含 `IF_MATCH_PATTERN`、`replay_from_envelope`、`parse_json_body`）；
- `app.py` 的 3 行额度实测不够（例如 ruff 的 I001 要求 import 折行 ⇒ 变成 4 行）；
- 除 E1 / E2 之外出现任何既有哨兵红；
- 需要改 `api/deps.py` / `application/**` / `domain/**` / `api/common.py` 才能过测。

U 项格式：`U-<n>｜现象（含 file:line 与命令原文）｜你实测到的事实｜候选处置（≥2 个）｜你倾向哪个及理由`。
**禁**在 U 项里自行落地任何一种候选处置。

## §10 回执格式（最后一条消息，逐字用这些字段名）

```
RESULT: DONE | DONE_WITH_GAP | PARTIAL | BLOCKED
LOOP_USED: <n>/2
BASE_SHA: <你上工时的派单基线 sha，git log 自取>
FILES_NEW: <逐件：路径 行数 字节 sha256[:12]>
FILES_MODIFIED: <只准 src/campaignlab/api/app.py 一件，附 numstat>
V1_new_guards: rc=<>, collected=<>
V2_full_pytest: rc=<>, failed=<>, failed_ids=<必须恰为 E1/E2 两条>
V3_quality: ruff_check rc=<>, ruff_format rc=<>, mypy rc=<>
V4_appy_numstat: <added>\t<deleted>
V5_include_router_count: <>
V6_symbol_face: public=<>, private=<>, __all__=<>
V7_operation_ids: <>
V8_redline_hits: <>
V9_is_identity: <你如何取到注入对象本身（file:line），以及断言原文>
V10_no_regression: app_state_keys=<>, middleware_order=<>, openapi_urls=<>, allowed=<>, kwonly=<>
V11_numstat_frozen: <必须为空>
EXPECTED_RED_TEXT: <E1 / E2 两条 FAIL 的原文（截断到关键断言行即可）>
PC_RESULTS: <PC-1..PC-4 逐条：变异点、AST/运行期生效证明、rc、红的原文、复原后 sha（须与落地态相同）>
U_ITEMS: <逐条按 §9 格式；无则写 NONE>
SELF_REPORTED_DEVIATIONS: <任何与本派单文不一致之处，宁报勿藏>
TIER_CONFIRM: model=qwen3.8-flash, reasoning=medium（若你被以其它档位启动，必须在此如实写明）
```
