 R18 · M2-01/S4 派单文（`src/campaignlab/api/rules.py` 新建 ＋ `app.py` 挂载 5→6）

> 本文件由编排器在 **predispatch 提交**内入库（PRE-13 第一步），spawn 排在其后，`agent_id` 由第三步的
> 纯台账提交回填。lane 侧**禁改本文件**；如发现本文与仓内实测面冲突，按 §8 上报 U 项，禁自行裁定。
>
> 一切数字（行数／字节／sha／计数）**禁写死**，一律以本文给出的命令在 WSL 仓库根
> `/home/szf/dev/CampaignLab` 现取为准（PRE-15 / D-012 / D-014）。

## 0. 身份 · 档位 · 边界

| 项 | 值 |
|---|---|
| 任务 | `M2-01`（活动 / 绑定 / 规则版本 / 条款确认门禁 / 检查项框架） |
| 子任务 | **S4**（design §11.5） |
| 档位 | `qwen3.8-flash` / reasoning `medium`（卡片档位表原文冻结；§6.3 无强制 max 触发项） |
| critical / slack | `false` / `4`（M2-01 卡片实取值） |
| loop 上限 | 2（超限即停手上报，禁第 3 轮自我说服） |
| 前序 | S1 / S2a / S2b-1 / S2b-2 / **S3 全部 DONE 且已入库**（S3 = `3422621`，tag `R18-landS3`） |
| 并行 | 与 **M0-04/S8**（在飞，昵称 Planck）并行。写权面**不相交**：S8 只写 `evidence/M0/**`，本棒只写 `src/campaignlab/api/rules.py`（新建）＋ `src/campaignlab/api/app.py`（≤3 行）。`app.py` 的串行约束（原「与 S3 同动 app.py」）**已因 S3 入库而解除**。 |

**分层红线**（`spec/CampaignLab-SDD-v1.0/framework/PYTHON.md:5`）：路由体只做「解析 → 调 service →
组装响应」，**一条 SQL 都不许有**；排序、键集、游标编解码、白名单、422 位置全在
`application/activity_service.py`，本层只透传形参，**禁**重算游标、**禁**备第二把密钥、**禁**备第二句 detail。

## 1. 写权面（越界即回报编排器，手册 §6.4；禁「顺手改」）

### 1.1 只新建

- `src/campaignlab/api/rules.py`

### 1.2 只修改（A90① 的 A10 最小例外，**≤3 行、numstat deleted 必须为 0**）

- `src/campaignlab/api/app.py`：
  1. 追加 1 行 import：`from campaignlab.api.rules import router as rules_router`
     （插在既有 `from campaignlab.api.jobs import router as jobs_router` 之后，保持 ruff `I001` 的字母序：
     `activities` < `common` < `deps` < `jobs` < `rules` < `session` < `workspaces` ⇒ **rules 必须在 jobs 之后、session 之前**）。
  2. 追加 2 行条件挂载，**插在 `app.include_router(activities_router)` 之后、`return app` 之前**：

```python
    if rule_service is not None:
        app.include_router(rules_router)
```

### 1.3 硬禁面（本棒**一字不改**；改了就判越界）

- `src/campaignlab/api/common.py`（冻结件，实测 `45605B` / sha256[:12] `836e7b3e8d3a`）
  —— 规则族 16 个 DTO **已在其中**（§4.3 实测清单），**方案 A 已被采纳并落地**，故本棒**不需要**
  声明任何 DTO（design §11.10 的「方案 B」不启用）。
- `src/campaignlab/api/deps.py`（`RuleService` Protocol 与 `get_rule_service` 已就位，见 §4.2）
- `src/campaignlab/application/**`、`src/campaignlab/domain/**`、`src/campaignlab/infra/**`
- `src/campaignlab/api/activities.py`（S3 交付件，`221L` / `9955B` / `887bd377a4f7`）
- `tests/**` **全部**（含 §2 点名的两个守护文件 —— 它们的迁移归**编排器**在入库批同批做，
  先例＝A245 / A248「编排器同批迁移 E1/E2」；lane 改了即判越界）
- `pyproject.toml` / `ruff.toml` / `mypy.ini`（禁为过门而放宽配置，A47 口径）
- `orchestrator/**`、`docs/**`、`spec/**`、`contracts/**`

### 1.4 `app.py` 的禁改面（逐条，均有既有守护盯着）

- **禁**改 `openapi_url=docs_url=redoc_url=None`
- **禁**改中间件添加顺序（实测必须仍为 `["BaseHTTPMiddleware", "CORSMiddleware"]`）
- **禁**改 `ALLOWED_HEADERS`（`If-Match` 已在其中，实测无需追加）
- **禁**改既有 5 处挂载与 5 个 `app.state.<name> = <service>` 条件赋值
- **禁**新增 `create_app` 形参（`rule_service` **已存在**，见 §4.1）

## 2. 预期红清单（PRE-14；由编排器**实测**得出，非推测）

落地 §1.2 的挂载后，仓内**恰有 2 个既有守护会判红**。这是**预期**的，
不是你的缺陷，**也不许你去修**（写权面外）。请在回执里如实贴出这 2 条红的原文。

| 编号 | 文件 :: 用例 | 判红的断言原文（实测行号） | 红因 |
|---|---|---|---|
| **E1** | `tests/unit/test_s3b_routes.py::test_app_py_contains_only_the_a85_mount_lines` | `:220` `assert len(mounted_lines) == 5` | 挂载行 5→6 |
| **E2** | `tests/unit/test_s2b2_app_injection.py::test_g6_mount_and_middleware_surface_unchanged` | `:275` `assert ordered == EXPECTED_MOUNT_LINES`（5 项清单，`:68-74`）<br>`:280-281` `banned_hits = imported_modules & _BANNED_ROUTER_MODULES` → `assert not banned_hits` | ① 有序挂载清单少第 6 项；② `_BANNED_ROUTER_MODULES` 实测为 `frozenset({"campaignlab.api.rules"})`（`:41`，字面被刻意拆成 `"rul" + "es"` 以免自匹配），app.py 一旦 import rules 即命中 |

**实测已排除的疑红**（编排器逐个核过断言原文，本棒**不会**红）：

- `test_s2b2_app_injection.py` 的 `EXPECTED_WIRING`（`:45-51`）**已含** `rule_service` ⇒ 条件装配面不变；
- 同文件 `EXPECTED_KWONLY`（`:54-62`）**已含** `activity_service` / `rule_service` ⇒ kwonly 面不变；
- 同文件 `:67` 原注记明写「S4 落地 rules 后再追加第 6 项（同型迁移）」⇒ 迁移是**既定计划**，非缺陷；
- `tests/unit/test_api_app.py::…`（`:52` 的 A10 注记只点名 jobs）对 rules **0 命中**；
- `tests/unit/test_domain_errors.py::test_common_public_surface_is_unchanged` 盯的是 `common.__all__`
  的**实取对撞**（A115），本棒不动 `common.py` ⇒ 不红。
## 3. 逐字口径回源（PRE-29：禁采信二手复述，一律回源到下列**行号**自读原文）

设计文：`orchestrator/handoff/M2-01-design.md`（实测 `1396L` / sha256[:12] `2d39feaac2d1`）。

| 你要实现的东西 | **必须自读的原文位置** | 要点（复述仅供导航，冲突以原文为准） |
|---|---|---|
| 7 个 handler 的签名、路径、状态码、参数 | **§1.5–§1.11 ＝ 绝对行 86–134** | 见 §3.1 的实测摘要 |
| `If-Match` 的声明形态（本卡最容易踩红处） | **§6.2 ＝ 绝对行 641–658** | 见 §3.2 |
| 判定顺序（禁调序） | **§6.3 ＝ 绝对行 660–677** | 10 步流水线，顺序即代码顺序 |
| 规则版本状态机 ＋ `current_rule_id` 联动 SQL | **§3.2 ＝ 绝对行 284–318** | 见 §3.3 |
| ETag 出现面（逐 op） | **§6.1 ＝ 绝对行 613–640** | 列表 200 **无** ETag |
| 409 / 422 家族逐码触发面 | **§6.4 ＝ 绝对行 679–723** | 只用 20 码注册表内的码 |
| 你的文件级 TODO | **§11.5 ＝ 绝对行 1083–1091** | 符号面清单（**注意 §5 的 A255 / A256 已修正其中两处失真**） |
| DTO 落点终裁 | **§2.5 ＝ 行 224–242 ＋ §11.9/§11.10 ＝ 行 1191–1212** | **方案 A 已落地**，本棒不写 DTO |
| `deps.py` 的引用形态 | **§14.3 A233 ＝ 行 1377–1396** | 行 1394–1396 明写：`api/rules.py` 在**运行期** import DTO 即可，**不需要**照抄 `TYPE_CHECKING` 形态 |

### 3.1 §1.5–§1.11 的实测摘要（**回源行号为准**，此表只帮你定位）

| op | method | path | 2xx | ETag | 正文 DTO | header |
|---|---|---|---|---|---|---|
| `listRules` | GET | `/api/v1/workspaces/{workspace_id}/activities/{activity_id}/rules` | 200 `RuleVersionPage` | **无** | — | — |
| `createRule` | POST | 同上 | **201** `RuleVersion` | **有** | `RuleCreate` | `Idempotency-Key` **必填**；**无 If-Match** |
| `getRule` | GET | `/api/v1/workspaces/{workspace_id}/rules/{rule_id}` | 200 `RuleVersion` | **有** | — | — |
| `updateRule` | PATCH | 同 `getRule` | 200 `RuleVersion` | **有** | `RuleUpdate` | `Idempotency-Key` ＋ `If-Match` 均必填（契约），声明口径同 §6.2 |
| `confirmRule` | POST | `/api/v1/workspaces/{workspace_id}/rules/{rule_id}/confirm` | 200 `RuleVersion` | **有** | `Confirmation`（`note` 1–500、`digest` 64 位小写 hex，两字段全必填） | 同 `updateRule` |
| `checkRule` | GET | `/api/v1/workspaces/{workspace_id}/rules/{rule_id}/checks` | 200 `RuleCheck` | **无** | — | — |
| `compareRules` | GET | `/api/v1/workspaces/{workspace_id}/rules/{rule_id}/diff` | 200 `RuleDiff` | **无** | — | query `candidate_rule_id` **必填** |

**路径面有两族前缀**（`.../activities/{activity_id}/rules` 与 `.../rules/{rule_id}...`）⇒ 见 §5 的 **A255**。

**`listRules` 的坑（design 行 89–95 原文）**：查询参数名是 `status`，但被过滤的**列**是
`rule_versions.state`（ADR-006 §4.7 点名的「9 处使用 `state` 命名」之一）；**按契约逐字实现，禁改名、
禁据此推断其它资源**。`status` 白名单 = `DRAFT` / `CONFIRMED`（由 service 侧判，本层只透传）。

**`compareRules` 的坑（design 行 131–133 原文）**：两者必须同工作区，否则 404（同一句 detail）；
`content.template` 不同 → 422 `VALIDATION_ERROR`，`issues[0].location="/query/candidate_rule_id"`、
`issues[0].code="TEMPLATE_MISMATCH"`。这两个判定都在 **service 侧**，本层只透传 `candidate_rule_id`。

### 3.2 §6.2 的 `If-Match` 冻结做法（**逐字照抄，禁照契约的 `required: true` 直译**）

design 行 648–650 原文：

```python
if_match: str | None = Header(
    None, alias="If-Match", min_length=3, max_length=32, pattern=IF_MATCH_PATTERN
)
```

其中 `IF_MATCH_PATTERN: Final = r'^"[1-9][0-9]*"$'`（**逐字**抄契约 pattern，禁自己写第二份正则）。

> ⚠ **实测口径修正**：仓内**没有**可 import 的 `IF_MATCH_PATTERN` 常量（S3 已在派单文 §9 记为 U 项，
> 并按 **A228 先例**＝`api/jobs.py::cancel_job` 的形态就地声明）。**先例做法**：在 `rules.py` 内
> 就地 `IF_MATCH_PATTERN: Final = r'^"[1-9][0-9]*"$'`，**禁**去改 `common.py` 加常量（硬禁面）。
> 落地前请先读 `api/jobs.py::cancel_job` 与 `api/activities.py::update_activity` 的实参声明，
> **与它们逐字同形**（三处正则必须字面相同，否则就是「两处各存一份」的第二份漂移）。

**为什么必须可选**（design 行 643–647）：若照抄成必填形参，缺头会在进入函数体**之前**被 Starlette 判成
`RequestValidationError` → `install_error_handlers` 翻成 **422 `VALIDATION_ERROR`**，契约要求的
**428 `PRECONDITION_REQUIRED` 就永远不可达**。三种输入三种结果：
缺头 → **428**；格式非法（如 `abc`、`"0"`、`0`）→ **422**（`issues[0].location="/header/If-Match"`）；
格式合法但不等 → **412**。

**本层不调 `check_if_match`**：428/412 由 **service 侧**判定（`RuleService.update_rule` /
`confirm_rule` 的签名已收 `if_match: str | None`，见 §4.2）；**禁两处都调**（S3 的 N5 口径）。

### 3.3 §3.2 的 `activities.current_rule_id` 联动 SQL（**逐字**，design 行 310–311 原文）

```sql
UPDATE activities SET current_rule_id=:rule_id, revision=revision+1 WHERE workspace_id=:ws AND id=:activity_id
```

- 该 SQL 的**写点唯一**在 `infra/db/repositories.py::ActivityRepository.set_current_rule`（A81），
  **本棒禁写任何 SQL**（分层红线）。此处逐字携带只为让你理解 `confirmRule` 成功后
  **活动自身的 ETag 也会变**（design 行 313–314），从而不在响应组装里做任何「补偿」。
- **A232（design §14.2 ＝ 行 1350 起）已裁定**：§11.3 的一般规则「所有写 UPDATE 的 WHERE 必须含 guard
  镜像」与本条 SQL 原文冲突时 ⇒ **specific 覆盖 general**，即该 UPDATE 的谓词就是
  `workspace_id=:ws AND id=:activity_id`，**不补** `revision` 镜像。**禁**在本棒「顺手」加 guard。
- **FU-54（未闭）**：并发确认同一活动的两个后继规则版本时 `current_rule_id` 的取值行为
  （design 行 315–318：无部分唯一索引 ⇒ 一父多确认后继合法，取「`confirmed_at` 最大者，
  并列时 `id` 字典序最大」）。该行为**由 M2-01/S6 钉成用例**，**不是本棒的责任面**；
  本棒只需知道「不要在路由层做任何排序或挑选」。
## 4. 冻结面实测读数（编排器于 predispatch 时点实测；你落地前**必须自行复测**并贴命令原文）

复测命令（在 WSL 仓库根执行；Python 一律走 `uv run --no-sync python`，**禁系统 `python3`** —— PRE-21：
系统 3.12.3 会在 PEP 758 上崩，本仓 pin 3.14）：

```bash
cd /home/szf/dev/CampaignLab
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
for f in src/campaignlab/api/app.py src/campaignlab/api/activities.py \
         src/campaignlab/api/common.py src/campaignlab/api/deps.py \
         src/campaignlab/api/jobs.py src/campaignlab/api/workspaces.py \
         src/campaignlab/api/session.py; do
  printf '%s %sL %sB %s\n' "$f" "$(wc -l < "$f")" "$(wc -c < "$f")" \
    "$(sha256sum "$f" | cut -c1-12)"
done
```

### 4.1 `api/app.py` 现值（实测 `175L` / `7726B` / `76fcb0778f64`）

- `create_app` 形参面（`:95-104`）实测**已含**：
  `clock` / `guard` / `session_service` / `health_service` / `workspace_service` /
  **`activity_service: ActivityService | None = None`（:103）** /
  **`rule_service: RuleService | None = None`（:104）** ⇒ 本棒**禁**新增形参。
- `app.state` 条件赋值面（`:139-148`）实测**已含** `if rule_service is not None: app.state.rule_service = rule_service`
  （`:147-148`）⇒ 本棒**禁**新增 state 赋值。
- 挂载面（`:163-174`）实测**恰 5 处**，顺序为
  `health.router` → `session_router` → `workspaces_router` → `jobs_router` → `activities_router`
  ⇒ 你的第 6 处必须是 `rules_router`，**且必须排在最后**（`return app` 在 `:175`）。
- import 面（`:27-46`）实测字母序：`health`(:27) → `activities`(:28) → `common`(:29) → `deps`(:37) →
  `jobs`(:44) → `session`(:45) → `workspaces`(:46)。**注意**：`health` 用的是
  `from campaignlab.api import health` 形态（`include_router(health.router)`），其余 6 个用
  `from … import router as <name>_router` 形态 ⇒ 你**必须**用后者（`EXPECTED_MOUNT_LINES` 钉的是
  字面 `app.include_router(rules_router)`）。插入位：`jobs`(:44) 之后、`session`(:45) 之前。

### 4.2 `api/deps.py` 的 `RuleService` Protocol（实测 7 个成员，**全部 kw-only**）

```text
list_rules(self, *, actor: Session, workspace_id: str, activity_id: str,
           cursor: str | None, limit: int, q: str | None, status: str | None) -> RuleVersionPage
create_rule(self, *, workspace_id: str, activity_id: str, payload: RuleCreate, body: bytes,
            idempotency_key: str, actor: Session, request_id: str) -> RuleWriteOutcome
get_rule(self, *, workspace_id: str, rule_id: str) -> RuleVersion
update_rule(self, *, workspace_id: str, rule_id: str, payload: RuleUpdate, body: bytes,
            idempotency_key: str, if_match: str | None, actor: Session, request_id: str) -> RuleWriteOutcome
confirm_rule(self, *, workspace_id: str, rule_id: str, payload: Confirmation, body: bytes,
             idempotency_key: str, if_match: str | None, actor: Session, request_id: str) -> RuleWriteOutcome
check_rule(self, *, workspace_id: str, rule_id: str) -> RuleCheck
compare_rules(self, *, workspace_id: str, rule_id: str, candidate_rule_id: str) -> RuleDiff
```

提供器：`get_rule_service(request: Request) -> RuleService`（实测已存在）。

> **硬约束**：你的 7 个 handler 调用 service 时，**实参名必须与上表逐字一致**（`inspect` 实取，
> 不是文档复述）；`create_rule` **没有** `if_match` 形参（design 行 99：该 op 只有 3 个参数），
> **禁**多传；`list_rules` **没有** `request_id` 形参，**禁**多传。

`RuleWriteOutcome`（`application/activity_service.py`）实测成员面：
`as_envelope` / `body` / `headers` / `replayed` / `status` —— 与 `ActivityWriteOutcome` **同形**
⇒ 三个写 op（`createRule` / `updateRule` / `confirmRule`）一律走**信封路径**，
**禁**在路由里自拼 `Response`；幂等重放的 ETag **从信封取、禁重算**。

### 4.3 `api/common.py` 已就位的规则族 DTO（实测 `__all__` = **79** 项）

| 符号 | 类型 | 实测字段面 |
|---|---|---|
| `RuleVersion` | Model, `extra=forbid` | 13：`id` `revision` `created_at` `label` `content` `terms` `source_rule_version` `parent_rule_id` `activity_id` `state` `digest` `confirmed_at` `confirmation` |
| `RuleVersionPage` | Model, `extra=forbid` | 2：`items` `next_cursor` |
| `RuleCreate` | Model, `extra=forbid` | 5：`label` `content` `terms` `source_rule_version` `parent_rule_id` |
| `RuleUpdate` | Model, `extra=forbid` | 3：`label` `content` `terms`（契约 `required` 实测为**空数组** ⇒ `{}` 能过 Schema，「空 PATCH→422」由 service 判，本层禁判） |
| `Confirmation` | Model, `extra=forbid` | 2：`note` `digest` |
| `RuleCheck` | Model, `extra=forbid` | 5：`rule_id` `rule_digest` `state`(`Literal['READY','NEEDS_CONFIRMATION']`) `issues` `boundary_cases` |
| `RuleDiff` | Model, `extra=forbid` | 4：`baseline_rule_id` `candidate_rule_id` `changes` `requires_rerun_case_ids` |
| `BoundaryCase` | Model, `extra=forbid` | 4：`id` `label` `input` `verification`；其中 **`input` 的注解实测＝`CouponCaseInput \| CallbackCaseInput`**（已校验的判别联合） |
| `CaseInput` | **`Annotated` 别名，不是 Model** | `Annotated[CouponCaseInput \| CallbackCaseInput, FieldInfo(discriminator='template')]`；实测 **`hasattr(CaseInput, "model_validate") == False`** |
| `RuleContent` | **`Annotated` 别名，不是 Model** | `Annotated[CouponRule \| CallbackRule, FieldInfo(discriminator='template')]` |
| `RuleState` / `RuleCheckState` | Literal | — |

⇒ **本棒禁声明任何 DTO**；一律 `from campaignlab.api.common import (...)` **运行期** import
（A233 行 1394–1396 明示：`api/rules.py` 在运行期需要这些 DTO 来构造响应体，
**不需要**照抄 `deps.py` 的 `TYPE_CHECKING` 形态）。

### 4.4 体例先例（**照抄，禁自创**）

`src/campaignlab/api/activities.py`（S3 交付件，`221L` / `9955B` / `887bd377a4f7`）是你的**唯一体例模板**：

- `:30` `from __future__ import annotations`
- `:32` `from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response`
- `:34-49` `from campaignlab.api.common import (...)` 括号多行、**字母序**
- `:50-55` `from campaignlab.api.deps import (...)`
- `:56` `from campaignlab.api.session import JSON_MEDIA_TYPE, declared_responses, parse_json_body`
- `:57` `from campaignlab.config import API_PREFIX`
- `:58` `from campaignlab.domain.ids import RESOURCE_ID_PATTERN`
- `:60` `__all__` **字母序**（体例＝`api/jobs.py::__all__` 的 RUF022 实测口径）
- `Depends(...)` 作默认值的行照 `api/workspaces.py` 就地 `# noqa: B008`（A47 / 手册 §9.9 的既有豁免，
  **禁**改 `pyproject.toml`）
- 错误路径一律 `except DomainError as exc: return problem_response(exc, request_id=…)`，
  `request_id_of` 用同一份
- 正文解析走冻结三连：`validate_idempotency_key` → `read_body_within_limit`
  （上限取 `get_config(request).max_json_body_bytes`）→ `parse_json_body`
- 装饰器一律 `operation_id="<operationId>"` ＋ `responses=declared_responses(<2xx>)`

## 5. 本棒携带的裁定（append-only；**不得推翻**，有异议走 §8 上报）

### A255 · `router` 的 `prefix` 口径（design §11.5 行 1085 只写 `tags=["rules"]`，未写 prefix）

**裁定**：`router = APIRouter(prefix=API_PREFIX, tags=["rules"])`，与 `api/activities.py` **同形**。

依据（全部实测）：① `API_PREFIX` 实测 `'/api/v1'`；② `activities.router.prefix` 实测 `'/api/v1'`、
`tags` 实测 `['activities']`，其路由路径实测为
`['/api/v1/workspaces/{workspace_id}/activities', '/api/v1/workspaces/{workspace_id}/activities/{activity_id}']`
⇒ 即「`prefix` ＋ 相对路径」形态；③ rules 的 7 条路径（§3.1）全部以 `/api/v1/` 起头，
用同一 `prefix` 后相对路径为：

```text
/workspaces/{workspace_id}/activities/{activity_id}/rules          # listRules(GET) / createRule(POST)
/workspaces/{workspace_id}/rules/{rule_id}                          # getRule(GET) / updateRule(PATCH)
/workspaces/{workspace_id}/rules/{rule_id}/confirm                  # confirmRule(POST)
/workspaces/{workspace_id}/rules/{rule_id}/checks                   # checkRule(GET)
/workspaces/{workspace_id}/rules/{rule_id}/diff                     # compareRules(GET)
```

两族前缀共用一个 `prefix=API_PREFIX` **不冲突**（差异在相对路径段内），故**无需**第二个 router。

### A256 · §11.5 行 1088 的 `BoundaryCaseDraft.input_payload` → `CaseInput.model_validate` **双重失真**

design §11.5 原文要求 `_rule_check_response` 「把 `BoundaryCaseDraft.input_payload` 交给 `CaseInput` 做
`model_validate`，**校验失败即 500 `INTERNAL_ERROR`**」。**实测三处与仓内不符**：

1. 仓内**没有** `BoundaryCaseDraft` 这个符号；实名为 **`BoundaryCase`**（`common.__all__` 实取）。
2. 该 Model **没有** `input_payload` 字段；实名为 **`input`**（实测 4 字段 `id`/`label`/`input`/`verification`）。
3. `CaseInput` **不是 Model 而是 `Annotated` 别名**，实测 `hasattr(CaseInput, "model_validate") is False`
   ⇒ 该行代码**字面不可执行**（会 `AttributeError`）。

**裁定**：`_rule_check_response(check, *, request_id)` **只做透传组装**，
**不做二次校验、不设 500 `INTERNAL_ERROR` 分支**。理由：`BoundaryCase.input` 的注解**已经**是
`CouponCaseInput | CallbackCaseInput` 的**判别联合**（`discriminator='template'`），
即 pydantic 在 service 侧构造 `RuleCheck` 时就已完成校验；非法反例**在类型上不可达**响应层。
design 的原意（「框架自己生成的反例不合法属服务端缺陷，禁静默丢弃」）由**上游构造期校验**满足，
强度不降。

**连带义务（如实登记，勿隐瞒）**：该 500 分支因此**结构性不可达** ⇒
① 本棒**禁**写会红的用例去凑它；② **禁** `skip` / `xfail`（design §6.6 口径）；
③ 本棒必须在回执里显式声明「§11.5 的 500 分支依 A256 不实现，理由＝上游已校验」；
④ 编排器将据此立 **D-052**（设计文失真，同族先例＝D-050「design §9-S6 具名清单失真」；D-052 与本派单文**同批入库**）
并把该口径同步给 **M2-01/S6**（`tests/api/activities/**`）与 **S7**（`evidence/M2/**`），
**禁**让下游按失真原文写出必红用例。
## 6. 交付面 · 符号面 · 门

### 6.1 `rules.py` 的公开符号面（design §11.5 逐字；**恰 8 项**）

```text
router, list_rules, create_rule, get_rule, update_rule, confirm_rule, check_rule, compare_rules
```

`__all__` **字母序**（RUF022）：

```python
__all__ = [
    "check_rule",
    "compare_rules",
    "confirm_rule",
    "create_rule",
    "get_rule",
    "list_rules",
    "router",
    "update_rule",
]
```

私面**恰 4 项**（design §11.5 逐字；`_rule_check_response` 依 **A256** 简化为透传）：

```text
_rule_version_response(rule, *, request_id, status)
_rule_version_page_response(page, *, request_id)
_rule_check_response(check, *, request_id)
_rule_diff_response(diff, *, request_id)
```

> `_rule_version_response` 带 `status` 形参（`createRule` 要 **201**，其余 **200**）；
> `_rule_version_page_response` / `_rule_check_response` / `_rule_diff_response` **不带 ETag**
> （design §6.1 切片实测这三个 op 的 `responses.200.headers` 只有 `X-Request-Id`）。

**禁**新增第 9 个公开符号或第 5 个私有符号；如确有必要，走 §8 上报 U 项，禁自行扩面。

### 6.2 门（rc 必须全 0；命令原文贴进回执）

```bash
cd /home/szf/dev/CampaignLab
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# V1 你新建文件的形态
uv run --no-sync python -c "import ast,pathlib;p=pathlib.Path('src/campaignlab/api/rules.py');t=ast.parse(p.read_text(encoding='utf-8'));print(sorted(n.name for n in t.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))))"

# V2 符号面实取对撞（禁采信自报）
uv run --no-sync python -c "
import inspect,sys; sys.path.insert(0,'src')
import campaignlab.api.rules as R
print('prefix',R.router.prefix,'tags',R.router.tags)
print('all',R.__all__)
print('paths',sorted({r.path for r in R.router.routes}))
print('ops',sorted({(r.path,tuple(sorted(r.methods))) for r in R.router.routes}))
print('priv',sorted(n for n,_ in inspect.getmembers(R) if n.startswith('_') and not n.startswith('__')))
"

# V3 ruff（格式 ＋ lint）
uv run --no-sync ruff format --check src/campaignlab/api/rules.py src/campaignlab/api/app.py
uv run --no-sync ruff check src/campaignlab/api/rules.py src/campaignlab/api/app.py

# V4 mypy strict（全仓）
uv run --no-sync mypy src

# V5 app.py 的 numstat（**deleted 必须为 0**，added 必须 ≤3）
git diff --numstat -- src/campaignlab/api/app.py

# V6 硬禁面零改动（**输出必须为空**）
git status --porcelain -- src/campaignlab/api/common.py src/campaignlab/api/deps.py \
  src/campaignlab/api/activities.py src/campaignlab/application src/campaignlab/domain \
  src/campaignlab/infra tests pyproject.toml

# V7 全量 pytest（**只允许 §2 的 E1/E2 两条红**，其余必须全绿；红数 >2 即停手上报）
uv run --no-sync pytest -q 2>&1 | tail -25

# V8 路由面与活契约对撞（7 个 operationId 必须逐字命中）
uv run --no-sync pytest -q tests/unit/test_contract_declarations.py 2>&1 | tail -12
```

**判定口径**：
- V7 的红**必须恰为** `test_app_py_contains_only_the_a85_mount_lines` 与
  `test_g6_mount_and_middleware_surface_unchanged` 两条（E1/E2）。**多出任何一条红即判本棒失败**，
  禁靠改 `tests/**` 或放宽配置把它压绿（写权面外 ＋ A47）。
- **禁**用 `-k` 过滤后报「全绿」冒充全量（PRE-29 口径回源义务：计数与命令必须同源同口径）。
- **禁** `--no-verify` / `git commit -n`；提交由**编排器**的 `scripts/orch_harness.py::run_commit` 统一做
  （一任务一提交），你**只交付文件、不自行 commit、不自行 push**。

## 7. 阳性对照（PC；**每条先实证「有牙」再报绿**）

R16-4 与 R16-9 两次**假绿**的成因：哨兵断言在变异后**仍为真**（例如「无条件赋值 `None` 会让
`hasattr` 为真」）。故每条 PC **必须**先用 AST／运行期**实取被改对象的新值**并断言它**等于预期变异形态**，
再跑判据；顺序不可颠倒。

| PC | 变异（在**临时副本**上做，禁改仓内文件） | 必须判红的判据 |
|---|---|---|
| **PC-1** | 把 `if rule_service is not None:` 删掉，改成无条件 `app.include_router(rules_router)` | E1 的 `pairs` 二元组失配（`test_s3b_routes.py:205-212`）＋ E2 的 `ordered` 清单仍相等但**条件装配**语义已破 ⇒ 至少 E1 判红。**先 AST 实取** `app.py` 内 `include_router(rules_router)` 的父节点**不再是** `If`，断言该变异形态成立，再跑判据 |
| **PC-2** | 把 `If-Match` 改成**必填**（`Header(alias="If-Match")` 无默认值） | `inspect.signature(R.update_rule)` 实取 `if_match.default` **不再是** `None` ⇒ 断言变异成立；再说明「428 永不可达」的判据面（design §6.2 行 643–647）。**禁**为此新写用例（`tests/**` 在硬禁面），改为**运行期实证**：用 `TestClient` 装一个注入 stub 的 app，缺头发 `PATCH .../rules/{id}`，断言实测状态码 **== 422**（即变异后的错误行为），再改回可选形参断言 **== 428** |
| **PC-3** | 把 `router` 的 `prefix=API_PREFIX` 去掉 | V2 的 `paths` 实取**不再**以 `/api/v1/` 起头 ⇒ 断言变异成立；同时 `tests/unit/test_contract_declarations.py` 的契约对撞必须判红（V8） |
| **PC-4** | 把 `create_rule` 的 `status_code` 从 201 改成 200 | V2 实取 `router.routes` 中 `POST .../rules` 的 `response_class`/`status_code`；或运行期 `TestClient` 实测 **== 200**（变异形态成立）⇒ 再改回断言 **== 201** |

**每条 PC 的回执必须含**：变异前后的**实取值对**（不是「应该判红」这类推测语）、
所用命令原文、rc。**做不到「有牙」的 PC 一律如实标 `PC-x: NO_TEETH`，禁标 PASS。**

## 8. U 项上报（禁自行裁定；手册 §6.4）

遇到下列情形**立即停手**，在回执 §U 里逐条列出，**禁**自行选择实现：

- 本文与仓内实测面冲突（例如某个 sha／行数／符号名对不上）
- 需要动 §1.3 的硬禁面才能过门
- V7 的红**多于** E1/E2 两条
- 契约切片（`contracts/`）与 design §1.5–§1.11 的路径／状态码／参数不一致
- `RuleService` Protocol 的成员面与 §4.2 实测不符
- 需要第 9 个公开符号或第 5 个私有符号

U 项格式（逐条）：

```text
U-<n> | 冲突面：<文件:行 或 符号> | 本文口径：<原文引用> | 实测口径：<命令 ＋ 输出> |
        候选：(a) … (b) … | 我的倾向：<a/b> ＋ 一句理由 | 阻塞性：是/否
```

**禁**在 U 项未裁定前「先按自己的理解实现」（那会把裁定权偷渡给 lane）。
非阻塞的 U 项可继续做其余部分，但必须在回执里显式标 `阻塞性：否`。

## 9. 派单前置自检（编排器已逐项做，lane 复述即可，禁跳）

| 编号 | 要求 | 本棒落实情况 |
|---|---|---|
| **PRE-13** | predispatch → spawn → 纯台账回填三步 | 本文在 predispatch 提交内入库；spawn 在其后；`agent_id` 由第三步回填 |
| **PRE-14** | 派单文给「预期红清单」，且由编排器**实测**得出 | §2：E1/E2 两条，断言原文与行号逐个实测；并实测**排除** 4 处疑红 |
| **PRE-15** | 冻结面读数由脚本实测、命令原文贴进派单文 | §4：命令原文在 §4 顶部；读数 `175L/7726B/76fcb0778f64` 等均为实取 |
| **PRE-18** | PC 必须「先实取变异形态、再跑判据」，并写明 R16-4/R16-9 假绿成因 | §7：成因已原文写明；4 条 PC 均要求实取值对 |
| **PRE-21** | 禁系统 `python3`（3.12.3 在 PEP 758 上崩） | §4 / §6.2 全部命令走 `uv run --no-sync python`，并显式 `export PATH` |
| **PRE-25** | 符号**定义点**必须实测（禁把 re-export 当定义点） | §4.3：DTO 全部实测定义在 `api/common.py`；`RuleWriteOutcome` 实测定义在 `application/activity_service.py` |
| **PRE-26** | 枚举／状态集的**项数**一律实取 | §4.3：`RuleCheck.state` 实测 `Literal['READY','NEEDS_CONFIRMATION']`；`RuleVersion` 13 字段实测 |
| **PRE-27** | 契约面（路径／状态码／参数）以**切片实取**为准 | §3.1 表的每格都标了切片来源（`operations.<op>.operation.*`）；§5 A255 的路径面由 `activities.router.routes` 实取同形推得 |
| **PRE-29** | **口径回源义务**：禁采信回执／二手复述，一律回源 | §3 给的是**绝对行号**而非复述；§6.2 V7 明禁「`-k` 过滤冒充全量」 |

## 10. 回执格式（**结构化**，禁散文；编排器会独立复验每一项，禁采信自报）

```text
§1 结论：DONE / DONE_WITH_GAP / PARTIAL / BLOCKED
§2 交付面：逐文件给 <行数>L / <字节>B / sha256[:12]（命令原文 ＋ 输出）
§3 app.py 的 numstat：added/deleted 实取值（deleted 必须 0，added ≤3）
§4 门：V1–V8 逐条给 命令原文 / rc / 关键输出（V7 必须贴出红的**完整清单**）
§5 预期红对账：E1 / E2 是否**恰为**实测红集（集合相等，多一条少一条都算不符）
§6 PC：逐条给 变异前实取值 / 变异后实取值 / 判据 rc；无牙的标 NO_TEETH
§7 符号面实取：__all__（8 项）/ 私面（4 项）/ router.prefix / router.tags / 7 条路径
§8 U 项：按 §8 格式逐条（无则写「无」）
§9 A256 声明：原文「§11.5 的 500 分支依 A256 不实现，理由＝上游已校验」
§10 越界自查：git status --porcelain 全量输出（**只允许** rules.py 新增 ＋ app.py 修改两项）
```

**禁**：① 自行 `git add` / `commit` / `push`；② 改 `tests/**` 去压绿 E1/E2；③ 放宽任何 lint/type 配置；
④ 在回执里写未经实测的数字；⑤ 隐瞒 NO_TEETH 的 PC 或多出来的红。
如实报红**不会**判你失败；**瞒报**会。
