# R17 · lane M2-01/S2b-2 派单文 —— `api/app.py` 的两个 service 注入位（微步骤，**不含 include_router**）

> **上工第一件事**：按 §5 逐条复测冻结面读数并与本文对账。若不符，**先查** `orchestrator/state.json` 的
> `resume.baseline_authoritative.current`（A223 / PRE-10），对账口径＝**派单快照 ＋ 该键 history 的累计增量**；
> 不符**不要直接判失真、也不要停手空转**。

## §0 身份、档位与预算（含 **A234** 的档位更正，务必读完）

| 项 | 值 |
|---|---|
| 任务 / 子任务 | **M2-01**（活动与规则版本）/ **S2b-2** |
| 轮次 / lane | Round 17 / lane **S2b-2** |
| 档位 | **`qwen3.8-flash`** · reasoning **medium** · loop 上限 **2** |
| 派单基线 | **含本派单文的那个提交**（tag `R17-predispatch`；其 parent = `dd09aa2`。上工时用 `git log --oneline -1 -- orchestrator/handoff/R17-lane-M2-01-S2b-2.md` 自行取 sha，禁写猜测值）· 分支 `m0-framework` · ruff format **292** / mypy **101** / pytest **699**（in-scope **103 py + 189 md**）。292 与 189 已计入**两份 R17 派单文自身**入库带来的 +2 in-scope md（`orchestrator/**` 的 `.md` 在 ruff 作用域内，实测口径见 `counts.ruff_formatted_files_composition`）；除此之外交付面与 `dd09aa2` **逐字节相同**（该提交是纯台账回填）。 |
| 并行邻居 | lane **S5**（M0-04，只新建 `tests/integration/jobs/{conftest,test_state_machine,test_idempotency,test_jobs_api}.py`）—— 写集与你**不相交**；它的文件对你是 **IN_FLIGHT_CONTAMINATION**：**禁改、禁 add、禁 checkout、禁 clean/reset/stash**（PRE-11 / A161） |

### 0.1 为什么本棒是 flash 而不是 A217 当初写的 max（**A234**，如实说明）

A217（2026-11-14 拆分 S2b 时）把 S2b-2 冻结为 `qwen3.8-max` / high，当时的事实是：`api/deps.py` 的
`ActivityService` / `RuleService` 两个 Protocol **还不存在**，本棒要在端口面未定的情况下决定注入形态。
**该前提已在 `a0ee343`（R16 / M2-01/S2b-1）消失**，编排器实测：

- `api/deps.py` 346 行 / 13524 B / `ed1075a86447`，`__all__` 实取 13 名，已含
  `ActivityService, RuleService, get_activity_service, get_rule_service`；
- 端口 vs 实现的**双向差集为 ∅**（`inspect` 实取，A115 集合对撞，已由编排器复验）；
- 本棒要做的事被收窄成「在 `create_app` 的既有注入位尾部加 2 个同形形参 ＋ 2 组 `if X is not None:` 装配」，
  **目标形态在 §3 里已逐字给出**，且既有守护（`test_s3b_routes.py` / `test_api_app.py` / `test_s3d_application.py`）
  已把挂载面、中间件顺序、`openapi_url=None`、「不注入就不装配」全部钉死 ⇒ 无任何设计裁量空间。

⇒ **裁定 A234：S2b-2 降档为 `qwen3.8-flash` / medium。** 依据是**实测复杂度**（零裁量、目标形态已冻结、
判据面已被既有守护覆盖），**不是**为了凑 flash 配比（手册 §6.6 明文「禁为凑配比降档」）。
副作用如实登记：本棒以 flash 计入分母会使 `flash_share_tasks` 由 0.5385 升至约 0.5556、
`flash_share_dev_lanes` 由 0.3000 升至约 0.3438（两条护栏仍未同时达标，`flash_share_tokens` 0.6655 不变）。
**若你在执行中发现本棒实际需要设计裁量**（例如 `app.state` 命名与 `deps.py` 提供器的读取口径不一致、
或必须动挂载面才能自洽）⇒ 立即按 §8 报 U 并**要求升档**，禁硬做。

## §1 写权面（**恰好 2 件**，越界即按 §8 报 U）

```
src/campaignlab/api/app.py                 （修改 · 目标形态见 §3 · numstat 上限见 §2.1）
tests/unit/test_s2b2_app_injection.py      （新建 · 守护清单见 §4）
```

A217 的**原文**（逐字，禁改写）：

> **S2b-2**：`api/app.py` 微步骤 —— `create_app` 追加 `activity_service` / `rule_service` 两个可注入形参
> （默认 `None`，**不注入就不装配**）＋ 两行 `app.state.<name> = <service>`。**不含 `include_router`**
> （A217 ③ 下放给 M2-01/S3、S4）。
> **hard_ban**：禁改 `openapi_url=docs_url=redoc_url=None`、中间件添加顺序、`ALLOWED_HEADERS`、既有路由挂载。

`A217.S3_S4_router_mount` 的**原文**：

> A217 ③：`api/activities.py` 的 router 挂载归 **S3**、`api/rules.py` 的归 **S4**，各获 A90①/A10 同型窄豁免
> （单文件 `api/app.py` ＋ ≤2 行 ＋ 仅挂载位）。**S2b-2 入库后 `app.py` 的形参面已就绪，S3/S4 只需加 import
> ＋ 条件 `include_router`。**

⇒ 你**只做形参面与 `app.state` 装配面**；`api/activities.py` / `api/rules.py` **还不存在**，禁创建、禁 import。

## §2 硬禁面（逐条）

1. **禁改除 `src/campaignlab/api/app.py` 之外的任何 `src/**` 文件**。特别是：
   `api/deps.py`（`ed1075a86447`）、`api/common.py`、`api/jobs.py`、`application/**`、`worker/**`、
   `domain/**`、`infra/**` —— 回收时逐件 sha 对撞（§5 给了关键件的实测值）。
2. **禁改既有测试件**：`tests/unit/test_s3b_routes.py`（`b0122388342a`）、`tests/unit/test_api_app.py`
   （`a97c32a63756`）、`tests/unit/test_s3d_application.py`（`dca0657b8b18`）、`tests/api/**`、
   `tests/unit/test_s2b_activity_*.py`（3 件，S2b-1 刚落地）、`tests/integration/**`（含邻居 S5 的在飞件）。
3. **禁改** `contracts/**`（`openapi.json` 必须保持 **443309 B / sha16 `592571099d63`**）、`spec/**`、
   `scripts/**`、`orchestrator/**`、`web/**`、`pyproject.toml`、`uv.lock`。
4. **禁新增任何 `include_router`**（A217 ③）；**禁**新增 `activities` / `rules` 相关 import；
   `app.include_router(` 开头的行数必须**仍是 4**，且其中含 `jobs` 的**仍是 1**、且必须**仍是**
   `if workspace_service is not None:` 的同形条件挂载（这是 `test_s3b_routes.py::
   test_app_py_contains_only_the_a85_mount_lines` 的既有判据，**你改动后它必须仍然绿**）。
5. **禁改** `app.__all__`（实测恰 4 名：`ALLOWED_HEADERS, ALLOWED_METHODS, create_app, origin_host_guard_middleware`）、
   `ALLOWED_METHODS`（7 项）、`ALLOWED_HEADERS`（5 项）、`origin_host_guard_middleware`、
   三处 `openapi_url=docs_url=redoc_url=None`、`app.add_middleware(...)` 的**两次调用与其先后顺序**、
   `install_error_handlers(app)` 的**位置（必须在两次 add_middleware 之后）**。
6. **禁 `sleep` / 墙钟字面量**（红线 3 / D-045）：新测试一律用 `campaignlab.clock.FixedClock`。
   编排器会对你的 2 件做字面量扫描（含注释与 docstring）；需引用禁串时用**拼接**构造。
7. **禁跑** `uv add` / `uv sync` / `git commit` / `git add` / `git push`；禁改 `.gitignore`。

### 2.1 numstat 上限（回收时逐字对账）

`git diff --numstat HEAD -- src/campaignlab/api/app.py` 必须满足：**added ≤ 16 · deleted ≤ 2**，
且**被删的行只可能是这两行**（其余一律必须是纯插入）：

1. `from campaignlab.api.deps import HealthService, SessionService, WorkspaceService`
   —— 加两个名字后行长 111 > 88，`ruff format` 必然把它折成**带括号的多行**形式（7 行替 1 行）；
2. （**可选**）`create_app` docstring 里含「六个参数全部**可注入**」的那一行 —— 若你要把它订正为「八个」。
   若你选择**不改**该行，则必须在 docstring **末尾纯追加**一段说明新增两个注入位（禁留下与代码矛盾的文档，
   D-012 同族）。二者择一，**禁两条都不做**。

`tests/unit/test_s2b2_app_injection.py` 为新建件，无 numstat 上限，但必须 `ruff format --check` 干净、
**mypy strict 零 `# type: ignore`**。

### 2.2 预期红清单（PRE-14：编排器已实测，**本棒落地后不应打红任何既有哨兵**）

编排器逐条读过与本棒相关的三个守护，结论与依据：

| 既有守护 | 判据（实测原文要点） | 本棒是否打红 |
|---|---|---|
| `test_s3b_routes.py::test_app_py_contains_only_the_a85_mount_lines` | 3 组 `if …is not None:\n        app.include_router(…)` 逐字在场；`import router as {session,workspaces,jobs}_router` 在场；`app.include_router(` 行数 == **4**；含 `jobs` 的 == **1**；三个 `*_router` 各出现 ≤3 行 | **否**：你不新增挂载、不动 import 别名 |
| `test_s3b_routes.py::test_app_mounts_routers_only_when_services_injected` | 裸装配不含 session/workspaces router；注入后含 | **否** |
| `test_api_app.py::test_health_returns_200_when_dependency_overridden` 等 | `create_app(config, guard=TESTSERVER)` 位置参数 ＋ kwonly 调用 | **否**：新形参是**尾部追加的 kwonly 且默认 None** |
| `test_s3d_application.py::test_create_app_attaches_injected_services_and_keeps_legacy_behaviour` | 注入三个既有 service 后 `app.state.X is X`；`app.state.config/clock/guard` 未变；`openapi_url/docs_url/redoc_url is None`；`/api/v1/health` 200 | **否** |
| 同文件 `assert not hasattr(app.state, "workspace_service")`（裸装配分支） | 不注入就不装配 | **否**，但**这正是你新形参必须遵守的形态**（§3 的 `if … is not None:`） |

⇒ **你的 2 件落地后，全表 pytest 必须仍是 0 failed**（699 → 699 + 你的新增数）。
若出现任何红：① 先判是否邻居 lane S5 的在飞件造成（IN_FLIGHT_CONTAMINATION，禁修，按 §8 报）；
② 若确是你造成 ⇒ 十有八九违反了 §2.4/§2.5，自己修。

## §3 目标形态（**逐字**给出，禁自行发挥；这是 A234 降档的前提）

### 3.1 import 行（ruff format 折行后的**期望终态**）
```python
from campaignlab.api.deps import (
    ActivityService,
    HealthService,
    RuleService,
    SessionService,
    WorkspaceService,
)
```
（名字**按字母序**，这是 ruff `I001` 的要求；禁手工排成别的顺序。）

### 3.2 `create_app` 形参面（**尾部追加**两个 kwonly，默认 `None`）
```python
def create_app(
    config: AppConfig | None = None,
    *,
    clock: Clock | None = None,
    guard: OriginHostGuard | None = None,
    session_service: SessionService | None = None,
    health_service: HealthService | None = None,
    workspace_service: WorkspaceService | None = None,
    activity_service: ActivityService | None = None,
    rule_service: RuleService | None = None,
) -> FastAPI:
```
既有 6 个形参的**名字、顺序、默认值、注解一字不改**（`test_s3d_application.py` 与 `test_api_app.py` 按名调用）。

### 3.3 装配面（**紧接**既有 `workspace_service` 那组之后，同形纯追加）
```python
    if activity_service is not None:
        app.state.activity_service = activity_service
    if rule_service is not None:
        app.state.rule_service = rule_service
```
`app.state` 的属性名必须**恰为** `activity_service` / `rule_service`。依据（编排器实测 `api/deps.py` 第 286–332 行原文，
非转述）：`_state_service(request, attribute, port)` 是唯一私有取值助手，`get_activity_service` 的函数体是
`return cast(ActivityService, _state_service(request, "activity_service", ActivityService))`、
`get_rule_service` 是 `return cast(RuleService, _state_service(request, "rule_service", RuleService))`；
且 `get_activity_service` 的 docstring 原文已写明「``attribute`` 取 ``"activity_service"``，即 ``create_app`` 的
**同名可注入形参**（该形参由 S2b-2 追加，A217）」⇒ 键名与形参名是**已被上游冻结**的，你没有裁量空间。
另注意 `_state_service` 用 `isinstance(service, port)` 做**结构化**校验（`port` 是 `@runtime_checkable` Protocol），
故测试替身只要方法面齐全即可通过 —— 但 `app.state.<name>` **不存在**时会抛 `RuntimeError` ⇒ 500 Problem，
这正是 `test_api_app.py` 钉住的「不注入就不装配」既有行为，**禁**为了少写一行而给默认实现。

## §4 `tests/unit/test_s2b2_app_injection.py` 的守护清单（**至少** 9 条，A115：一律集合/身份对撞，禁「计数 == N」）

| # | 判据 | 硬要求 |
|---|---|---|
| G1 | `create_app` 形参面 | `inspect.signature` 实取：posonly+args == `['config']`；kwonly **有序** == `['clock','guard','session_service','health_service','workspace_service','activity_service','rule_service']`；两个新形参的 default **is None**、annotation 解析后 **is** `deps.ActivityService` / `deps.RuleService`（`typing.get_type_hints` 或 `inspect` 的 `annotation`，注意本文件有 `from __future__ import annotations` ⇒ 注解是**字符串**，必须解析后比对，禁比字面量） |
| G2 | 注入即装配 | 传入结构合规的替身 ⇒ `app.state.activity_service is stub_a` 且 `app.state.rule_service is stub_r`（**身份**判定，非相等） |
| G3 | **不注入就不装配** | 裸装配 ⇒ `not hasattr(app.state, "activity_service")` 且 `not hasattr(app.state, "rule_service")`（体例照抄 `test_s3d_application.py` 对 `workspace_service` 的同型断言） |
| G4 | 只提供其一 | 只注入 `activity_service` ⇒ `hasattr(...,"activity_service")` 为真且 `hasattr(...,"rule_service")` 为假（证两个 `if` 相互独立，不是 `and` 连写） |
| G5 | 既有装配面一字未改 | `app.state.config is config`、`app.state.clock is clock`、`app.state.guard is guard`；`app.openapi_url is None and app.docs_url is None and app.redoc_url is None` |
| G6 | 挂载面未变 | 读 `src/campaignlab/api/app.py` 源码：以 `app.include_router(` 开头的行数 **== 4**；含 `jobs` 的 **== 1**；源码里**不含** `activities` / `rules` 的 router import（A217 ③）；`source.count("app.add_middleware(") == 2`；`install_error_handlers(app)` 的位置索引 **大于** 两次 `add_middleware` 的位置索引 |
| G7 | `__all__` 与常量未变 | `app.__all__` 与 `{'ALLOWED_HEADERS','ALLOWED_METHODS','create_app','origin_host_guard_middleware'}` **双向差集为 ∅**；`ALLOWED_METHODS` 与 7 项元组逐字相等；`ALLOWED_HEADERS` 与 5 项元组逐字相等 |
| G8 | 提供器链路真的通 | 用 `app.dependency_overrides` **或**直接注入替身后，`TestClient` 打一个**既有**路由（如 `/api/v1/health`）仍 200，且 `X-Request-Id` 头在场（证中间件顺序没被你的插入打乱） |
| G9 | 未装配时的既有行为未回归 | 裸装配下 `GET /api/v1/health`（不带 `dependency_overrides`）仍返回 **500** 且 `body["code"] == "INTERNAL_ERROR"`、`body["issues"] == []`、`detail` 里**不含** `RuntimeError` / `Traceback`（体例照抄 `test_api_app.py`，那是 `install_error_handlers` 的既有收敛行为） |

替身（stub）怎么写：`deps.ActivityService` / `deps.RuleService` 是 `@runtime_checkable` Protocol，
**只需方法面齐全**即可通过 `isinstance`。方法面以 `inspect` 实取为准（S2b-1 已复验「端口 vs 实现双向差集为 ∅」），
禁在测试里硬编码方法名清单当权威 —— 用 `_protocol_members(deps.ActivityService)` 一类的**动态**取法
（`tests/unit/test_s2b_activity_surface.py` 第 470–482 行已有同型实现可直接参照，但**禁改**那个文件）。

## §5 冻结面读数（PRE-15：全部由编排器脚本 `.orch_tmp/measure_r17.py` 实测，命令原文一并给出）

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
| **`src/campaignlab/api/app.py`**（你的唯一 src 写权件） | 160 | 7253 | `110751903e4d` |
| `src/campaignlab/api/deps.py`（**冻结**，S2b-1 刚落地） | 346 | 13524 | `ed1075a86447` |
| `src/campaignlab/application/activity_service.py`（**冻结**） | 1999 | 88950 | `21425228694b` |
| `tests/unit/test_s3b_routes.py`（**冻结**，G6 的既有守护） | 211 | 8983 | `b0122388342a` |
| `tests/unit/test_api_app.py`（**冻结**） | 120 | 5271 | `a97c32a63756` |
| `tests/unit/test_s3d_application.py`（**冻结**） | 550 | 24931 | `dca0657b8b18` |
| `contracts/openapi.json`（**冻结**，V1/V7 判据） | 16747 | 443309 | `592571099d63` |

`api/app.py` 的实测结构面（编排器 AST 实取，你上工后须自行复核一遍）：
`__all__` = `['ALLOWED_HEADERS','ALLOWED_METHODS','create_app','origin_host_guard_middleware']`（4 名）；
`create_app` posonly+args = `['config']`、kwonly = `['clock','guard','session_service','health_service','workspace_service']`；
以 `app.include_router(` 开头的行 = **4**；`app.add_middleware(` 出现 = **2**；
`install_error_handlers(app)` 出现 = **2**（其中 1 处在 docstring/注释里，实际调用 1 处 —— 你自己核清楚再写 G6）；
以 `app.state.` 开头且含 `=` 的行 = **6**（`config`/`clock`/`guard` 三条无条件 ＋ `session_service`/`health_service`/
`workspace_service` 三条条件）⇒ 你落地后应为 **8**；
`from campaignlab.api.deps import` 那行原文 = `from campaignlab.api.deps import HealthService, SessionService, WorkspaceService`。

`api/deps.py` 的 `__all__`（实测 13 名，**冻结**）：
`['ActivityService','HealthService','RuleService','SessionService','WorkspaceService','get_activity_service','get_clock','get_config','get_health_service','get_rule_service','get_session_service','get_workspace_service','require_session']`。

pytest 分母 **699**（冻结索引树实测：678 passed ＋ GIT_ENV_IGNORES 静态收集 21）。
本棒预期（以实测为准，禁写死；基线已含两份派单文的 +2 md）：in-scope py 103→**104**、
in-scope md **189** 不变、ruff format 292→**293**、mypy 101→**102**、pytest 699→699+你的新增数。

## §6 纪律（红线）
1. **A82 纯追加精神**：除 §2.1 明确允许的那 1–2 行外，`app.py` 的改动必须是**纯插入**；既有语义一字不改。
2. **A115**：一切符号面判据用**集合对撞**（双向差集为 ∅）或**身份**判定（`is`），禁「计数 == N」当唯一判据
   （计数型抓不到换序与换名 —— 这是 R16 的 PC-2 实证过的）。
3. **PRE-7**：上工第一步先 `inspect.signature(create_app)` ＋ 读 `api/deps.py` 第 286–332 行实测，
   本文数字一律视为**待复核参考值**；不符即报 U，禁自行假定。
4. **D-012**：禁在代码/测试/回执里写死「四门分母」当判据；引用时须指明口径与时点（本文 §5 已给）。
5. **成本纪律**：本棒是 flash / medium、loop 上限 2。禁把 1999 行的 `activity_service.py` 通读一遍 ——
   你只需要 `deps.py` 的两个 Protocol 名与 `app.py` 本身。禁读 `contracts/openapi.json` 全文（443309 B），
   需要时只 grep。

## §7 阳性对照（PRE-18：**先证变异生效，再证判据有牙**；至少 4 条，每条三步都贴原文）
1. **语义断言**：AST／运行期实取被改对象的**新值**，断言它确实等于预期变异形态
   （「文件 sha 变了」**不构成**「变异生效」—— R16-4 与 R16-9 两次假绿的成因，务必照做）；
2. **跑判据** ⇒ 必须 **rc≠0**；
3. **字节级双向复原** ⇒ sha256[:12] 与 AST 双口径都回到 `110751903e4d`。

建议的 4 条（可替换，强度不得低于此）：
- PC-1：把 `if activity_service is not None:` 改成**无条件** `app.state.activity_service = activity_service`
  ⇒ G3 判红（证「不注入就不装配」有牙）。**注意**：无条件赋值 `None` 会让 `hasattr` 为真 ⇒ 这正是 R16 里
  `test_jobs_router_is_not_mounted_by_s3c` 那条哨兵的教训形态。
- PC-2：把 §3.3 的两组 `if` 合并成 `if activity_service is not None and rule_service is not None:`
  ⇒ G4 判红（证两个注入位相互独立）。
- PC-3：在 `app.py` 末尾追加一行 `app.include_router(health.router)` ⇒ G6 判红（证挂载面守护有牙）；
  复原后必须回到 4 行。
- PC-4：把 `rule_service` 形参的注解从 `RuleService | None` 改成 `object | None` ⇒ G1 判红
  （证注解是**解析后**比对的，不是比字面量字符串）。
备份只准放 `/tmp` 或仓库外（如 `D:\ws\codex_rd\ss_campaignlab\.orch_scratch`），**工作树零残留**。

## §8 U 项协议（只报不裁；编排器逐条终裁）
遇到下列任一情形**停手报 U**，禁自行决定：
① `deps.py` 的提供器实际读取的 `app.state` 键名与 §3.3 不符；② 必须新增 `include_router` 才能自洽；
③ 必须动 §2 的硬禁面；④ 既有守护因你的**合法**改动而判红（那就是哨兵到期，归编排器迁移，A226/A231 先例）；
⑤ 你**已经**动了硬禁面（自报越界，宁报勿藏 —— A230/A233 先例：自报越界记入 honesty 正面样本，静默扩形才是重罪）；
⑥ 你认为本棒需要设计裁量 ⇒ **要求升档回 max**（A234 的降档前提失效）。
每条 U 写清：**事实（实测，非转述）→ 候选方案（≥2 个，含你的倾向与理由）→ 影响面**。

## §9 取证与回执
本棒**不产出** `evidence/**` 文件（编排器在入库时自建 `evidence/M0/ORCHESTRATOR/r17-m2-01-s2b2-landing/`）。
回执（最后一条消息）逐字用这些字段名：
```
RESULT: DONE | DONE_WITH_GAP | PARTIAL | BLOCKED
① 基线复测（对账 resume.baseline_authoritative）
② 交付面（逐件 行/字节/sha256[:12]/用例数；app.py 的 git diff --numstat 原文）
③ 四门（ruff check / ruff format --check / mypy / pytest 的命令原文 + rc + 关键输出行；禁只写「通过」）
④ 符号面／集合对撞结果（A115：__all__、kwonly 有序清单、挂载行数、add_middleware 次数）
⑤ 阳性对照（≥4 条，每条三步原文）
⑥ 自报 token（拿不到计量句柄就写 estimated=true 与区间，禁编精确数）
⑦ U 项（只报不裁）
⑧ 未尽面 / 风险 / IN_FLIGHT_CONTAMINATION / loop 用了几轮 / 自报越界
```
