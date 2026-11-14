# M2-01 设计 · S1 活动 / 绑定 / 规则版本 / 条款确认门禁 / 检查项框架（qwen3.8-max high · 本文件只设计、不含实现代码）

> **真值来源与口径**（R8-1 / A115 `rule_no_hardcoded_symbol_counts`、R12-4 `rule_no_hardcoded_tool_verdicts`）：
> ① 契约字段级断言一律标注切片路径 `operations.<opId>.schemas.<Name>`（A171：切片**无**顶层 `components`，
> 需要 `Problem` / `Issue` / `ProblemXXX` 响应形时定向读活契约 `contracts/openapi.json`，本文已逐处标注）；
> ② 本文**不写死**任何符号面计数（`__all__` 项数、`PROBLEM_CODES` 码数、方法数、用例数），一律写「以 `inspect` /
> `ast` / `--collect-only` 实取为准」；③ 本文**不写死**工具裁决（import 序、格式化结果），一律写「以
> `ruff check --select I --diff` / `ruff format --check` 实取为准」；④ 错误码只用 `domain/errors.py::PROBLEM_CODES`
> 注册表内的既有码（ADR-005 §2.1），**本文零新增 `Problem.code`**；细粒度语义标签一律落 `Issue.code`
> （契约 `Issue.code` 为自由串，正则见 `operations.checkRule.schemas.Issue.properties.code`，非冻结面；
> 同型裁定：M0-04 的 N7③ / A88③ `JOB_INTERRUPTED`）。
>
> **R13 派单文更正（必须先读，见 §12 U-1）**：派单文与派单消息称「切片实测 `listActivities` 的查询参数只有
> `cursor` / `limit`」——**实测为假**。切片 `operations.listActivities.operation.parameters` 有 5 项
> （`workspace_id`(path) / `cursor` / `limit` / `q` / `status`），活契约 `contracts/openapi.json` 同路径同参数，
> `operations.listRules` 亦然（6 项，多一个 path `activity_id`）。既有实现 `src/campaignlab/api/workspaces.py`
> 模块 docstring 亦明写「该裁定**只**作用于 `listWorkspaces`，其它 `list*` op 的 `status` 参数不受影响」，
> 且编排器 N7① 裁定原文（`orchestrator/state.json`）已确认「`listJobs.status` …该参数仍在活契约中，合法」。
> 故本文按**契约实测**设计 `q` / `status` 两个查询参数（多值口径沿用 N7① 已裁定的「逗号分隔多值」），
> **不是**发明参数；派单文自查项 ④ 因此无法按字面满足，已在回执中如实报为 FAIL 并附实测证据。

## 1. 接口签名（11 个 operationId；函数名与 operationId 逐字对应，装饰器必须显式给 `operation_id`）

**全体 11 个 op 的公共约定**（逐 op 不再重复；真值来源＝切片各 op 的 `operation.responses`，实测 11 个 op
**均**声明「1 个 2xx + 11 个 Problem 形」共 12 个响应，Problem 形状态码集合与
`src/campaignlab/api/session.py::PROBLEM_STATUSES` 逐字相同）：

- 装饰器一律 `responses=declared_responses(<2xx>)`（import 自 `api/session.py`，A95：状态码集合的唯一权威是
  装饰器，测试侧只拿切片对撞，禁另立清单）。
- 路由体只做「解析 → 调 service → 组装响应」，**禁写 SQL**（`spec/CampaignLab-SDD-v1.0/framework/PYTHON.md`
  第 5 行「服务层应用事务，不在路由里直接写 SQL」）。
- `actor: Session = Depends(require_session)`（11 个 op 在切片里都**未**写 `security` ⇒ 继承全局 `LocalSession`，
  与 M0-02/M0-04 同口径）；service 走 `Depends(get_activity_service)` / `Depends(get_rule_service)`（见 §11 写权缺口）。
- 成功响应一律 `Response(content=<dto>.model_dump_json(), status_code=<2xx>, media_type=JSON_MEDIA_TYPE,
  headers={...})`；`X-Request-Id` 由 `install_error_handlers` / 中间件面统一给出（既有行为，禁在路由里第二份实现）。
- 错误路径一律 `except DomainError as exc: return problem_response(exc, request_id=request_id)`
  （`request_id = request_id_of(request)`）；**禁**在路由里现编 `title`（ADR-005 §2.2 固定中文短句表）。
- 有正文的 5 个 op（`createActivity` / `updateActivity` / `createRule` / `updateRule` / `confirmRule`）正文解析一律：
  `key = validate_idempotency_key(<header>)` → `body = await read_body_within_limit(request,
  max_bytes=get_config(request).max_json_body_bytes)` → `payload = parse_json_body(body,
  request.headers.get("content-type"), <DTO>)`（三个助手全部来自 `api/common.py` 与 `api/session.py`，禁复制第二份）。
- 路径参数一律 `workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN)`，
  `activity_id` / `rule_id` 同形（真值来源：各 op `operation.parameters[*].schema`，实测三者的
  `minLength`/`maxLength`/`pattern` 逐字相同）。
- `candidate_rule_id`（`compareRules` 的 **query**，实测 `required=true`）：
  `candidate_rule_id: str = Query(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN)`。

**1.1 `listActivities`** GET `/api/v1/workspaces/{workspace_id}/activities` → `async def list_activities(...)`：
200 `ActivityPage`；**无 ETag**（切片 `operations.listActivities.operation.responses.200.headers` 实测只有
`X-Request-Id`，禁发明 ETag，同 M0-02 对 `WorkspacePage` 的处置）。形参：
`cursor: str | None = Query(None, min_length=1, max_length=300)`、`limit: int = Query(25, ge=1, le=100)`、
`q: str | None = Query(None, min_length=1, max_length=100)`、`status: str | None = Query(None, min_length=1,
max_length=60)`（四项的 `minLength`/`maxLength`/`minimum`/`maximum`/`default` 全部取自
`operations.listActivities.operation.parameters`，实测 `limit` 的 `default=25`、`minimum=1`、`maximum=100`）。
排序固定 `created_at DESC, id ASC`（`architecture/API.md`「资源查询」行），键集谓词
`created_at < :k0 OR (created_at = :k0 AND id > :k1)`，每页取 `limit+1` 行判 `next_cursor`
（与 `listWorkspaces` / `listJobs` 同口径，复用同一份冻结游标实现）。游标 payload：
`{"v":1,"q":sha256(canonical_json({"workspace_id":<id>,"limit":<int>,"q":<str|None>,"status":<str|None>}))[:16],
"k":[created_at,id],"s":actor_id}`（形态沿用 M0-04-design §1 已冻结的 `listJobs` 游标；密钥取
`application/workspace_service.py::load_cursor_secret`，**禁**另生成第二把密钥）。改任一筛选或换 actor →
400 `BAD_CURSOR`，detail 复用 `application/workspace_service.py::BAD_CURSOR_DETAIL`（同一句，禁另编）。
`q` 对 `activities.name` 与 `activities.external_activity_id` 做 NFKC + casefold 子串匹配
（`API.md`「q 对名称和公开编号按 NFKC casefold 查找」；实现复用 `infra/db/repositories.py::_fold`）。
`status` 为**逗号分隔多值**（N7① 已裁定口径），白名单 = `operations.listActivities.schemas.Activity.properties.
status.enum` 实取（即 `OPEN` / `ARCHIVED`）；含未知态名或空 token → 422 `VALIDATION_ERROR`，
`issues[0].location="/query/status"`。无结果 → `items=[]`、`next_cursor=null`。

**1.2 `createActivity`** POST 同路径 → `async def create_activity(...)`：201 `Activity` + `ETag`
（切片 `responses.201.headers` 实测含 `ETag` 与 `X-Request-Id`）；header `Idempotency-Key`（实测
`required=true`、`minLength=8`、`maxLength=128`）；正文 `ActivityCreate`。走「幂等信封」全链：
同键同摘要 → `replay_from_envelope` 回放**同一** `ETag` 与逐字节相同正文、仅 `X-Request-Id` 重新生成；
同键异摘要 → 409 `IDEMPOTENCY_CONFLICT`（detail 复用 `application/idempotency.py::CONFLICT_DETAIL`）。

**1.3 `getActivity`** GET `/api/v1/workspaces/{workspace_id}/activities/{activity_id}` → `async def get_activity(...)`：
200 `Activity` + `ETag`（切片 `responses.200.headers` 实测含 `ETag`）。无正文、无 `Idempotency-Key`、无 `If-Match`
（切片 `operation.parameters` 实测只有 2 个 path 项）。跨工作区 / 不存在 → 404 `RESOURCE_NOT_FOUND`
**逐字相同**响应（`domain/errors.py::ResourceNotFound` docstring 的禁枚举口径）。

**1.4 `updateActivity`** PATCH 同 1.3 路径 → `async def update_activity(...)`：200 `Activity` + `ETag`；
header `Idempotency-Key`（必填）与 **`If-Match`（切片实测 `required=true`、`pattern="^\"[1-9][0-9]*\"$"`、
`minLength=3`、`maxLength=32`）**；正文 `ActivityUpdate`。**If-Match 必须在 FastAPI 侧声明为可选形参**
`if_match: str | None = Header(None, alias="If-Match", min_length=3, max_length=32, pattern=IF_MATCH_PATTERN)`
再由 service 调 `api/common.py::check_if_match` —— 若照契约声明为必填，Starlette 会在缺头时先抛
`RequestValidationError` 得到 **422**，契约要求的 **428 `PRECONDITION_REQUIRED`** 就永远不可达（见 §6.2）。

**1.5 `listRules`** GET `/api/v1/workspaces/{workspace_id}/activities/{activity_id}/rules` → `async def list_rules(...)`：
200 `RuleVersionPage`；**无 ETag**（切片 `responses.200.headers` 实测只有 `X-Request-Id`）。形参同 1.1 的四项
（切片 `operations.listRules.operation.parameters` 实测 6 项 = 2 path + `cursor`/`limit`/`q`/`status`）。
`status` 白名单 = `operations.listRules.schemas.RuleVersion.properties.state.enum` 实取（`DRAFT` / `CONFIRMED`）
—— **注意参数名是 `status` 而被过滤的列是 `rule_versions.state`**（ADR-006 §4.7 点名的「9 处使用 `state` 命名」
之一；本文按契约逐字实现，不做改名、不据此推断其它资源）。`q` 对 `rule_versions.label` 与
`rule_versions.source_rule_version` 做 NFKC + casefold 子串匹配。排序 / 键集 / 游标口径同 1.1，
游标查询摘要的输入改为 `{"workspace_id":…,"activity_id":…,"limit":…,"q":…,"status":…}`
（**必须**含 `activity_id`，否则跨活动复用游标不会被判 400）。可用索引：切片 `ddl.rule_versions__indexes`
实测 `CREATE INDEX rules_activity ON rule_versions(workspace_id,activity_id,created_at)`。

**1.6 `createRule`** POST 同 1.5 路径 → `async def create_rule(...)`：**201** `RuleVersion` + `ETag`
（切片 `operations.createRule.operation.responses` 实测 2xx 只有 `201`，且 `201.headers` 含 `ETag`）；
header `Idempotency-Key` 必填；正文 `RuleCreate`；**无 If-Match**（切片实测该 op 只有 3 个参数）。
新草稿一律 `state="DRAFT"`、`revision=1`、`confirmed_at=None`、`confirmation=None`
（切片 `ddl.rule_versions` 的 `CHECK((state='CONFIRMED')=(confirmed_at IS NOT NULL AND confirmation IS NOT NULL))`
双向钉死，禁只写一侧）。`parent_rule_id` 给出时必须指向**同一活动**的既有规则版本，否则 404（§3.2 R4）。

**1.7 `getRule`** GET `/api/v1/workspaces/{workspace_id}/rules/{rule_id}` → `async def get_rule(...)`：
200 `RuleVersion` + `ETag`；无正文、无幂等键、无 If-Match（切片实测 2 个 path 参数）。
路径里**没有** `activity_id`：活动归属由行内 `rule_versions.activity_id` 决定，但工作区隔离仍按
`workspace_id` 严格校验，越区 → 404（不回显 ID、不区分原因）。

**1.8 `updateRule`** PATCH 同 1.7 路径 → `async def update_rule(...)`：200 `RuleVersion` + `ETag`；
`Idempotency-Key` 与 `If-Match` 均必填（切片实测），声明口径同 1.4；正文 `RuleUpdate`
（`operations.updateRule.schemas.RuleUpdate.required` 实测为**空数组** ⇒ `{}` 能通过 Schema 校验，
必须由 service 判「空 PATCH」→ 422，见 §6.4）。目标为 `CONFIRMED` → 409 `STATE_CONFLICT`（§3.2）。

**1.9 `confirmRule`** POST `/api/v1/workspaces/{workspace_id}/rules/{rule_id}/confirm` → `async def confirm_rule(...)`：
200 `RuleVersion` + `ETag`；`Idempotency-Key` 与 `If-Match` 均必填（切片实测）；正文 `Confirmation`
（两字段全必填：`note` 1–500、`digest` 64 位小写 hex，真值来源 `operations.confirmRule.schemas.Confirmation`）。
判定顺序见 §4.2 / §6.3：门禁不通过 → 422 `EVIDENCE_REQUIRED`；`digest` 与当前规则摘要不符 →
409 `VERSION_MISMATCH`；目标已 `CONFIRMED` → 409 `STATE_CONFLICT`。成功后同事务把
`activities.current_rule_id` 指向本版本并 `activities.revision + 1`（`architecture/DOMAIN.md`「对象与修改」表：
「最近确认版本为活动候选规则」）。

**1.10 `checkRule`** GET `/api/v1/workspaces/{workspace_id}/rules/{rule_id}/checks` → `async def check_rule(...)`：
200 `RuleCheck`；**无 ETag**（切片 `responses.200.headers` 实测只有 `X-Request-Id`）；无正文、无幂等键、
无 If-Match（切片实测 2 个 path 参数）⇒ 只读、可重复调用、结果只由 `rule_versions` 行内容决定
（`rule_digest` 取自该行 `digest` 列，禁在响应里重算出第二个值）。**本 op 只生成反例数据与待验证行为文案，
不做任何金额分回放判定**（§5.4；任务卡「禁止」行：不得在 domain 层做金额分回放）。

**1.11 `compareRules`** GET `/api/v1/workspaces/{workspace_id}/rules/{rule_id}/diff` → `async def compare_rules(...)`：
200 `RuleDiff`；**无 ETag**（切片实测只有 `X-Request-Id`）；参数 = 2 path + **必填** query `candidate_rule_id`
（切片 `operations.compareRules.operation.parameters[2]` 实测 `in=query`、`required=true`）。
`rule_id` 为 baseline、`candidate_rule_id` 为候选；两者必须同工作区，否则 404（同一句 detail）。
**同模板校验**：两者 `content.template` 不同 → 422 `VALIDATION_ERROR`（`issues[0].location="/query/candidate_rule_id"`，
`issues[0].code="TEMPLATE_MISMATCH"`；`architecture/RULES.md`「规则检视」的「候选同模板」）。

## 2. 数据结构（字段级；每行末尾的 `←` 即真值来源切片路径，A171 口径）

**公共约定**（与 `api/common.py` 既有 DTO 同构，禁另立第二套）：一律 `model_config = ConfigDict(extra="forbid")`；
字符串用 `StrictStr`、整数用 `StrictInt`、布尔用 `StrictBool`（`framework/PYTHON.md` 第 3 行：Pydantic 拒绝未知字段、
布尔冒充整数、非有限数值和不带偏移的时刻）；时刻用 `AwareDatetime`；ID 型字段复用 `api/common.py` 的私有别名
`_IdStr`（= `Annotated[StrictStr, Field(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN)]`）与
`RevisionInt`（`ge=1, le=9007199254740991`）——这两个别名是**模块内私有／已导出**的既有面，
「DTO 落哪」直接决定能否复用它们（见 §2.5）。可空字段一律显式 `| None`（禁省略默认值造成「缺字段＝None」
与「显式 null」不可区分，PATCH 语义依赖 `model_fields_set`，见 §6.4）。

### 2.1 活动族

| DTO | 字段（`!`=必填，`?`=可空/可选） | 真值来源 |
|---|---|---|
| `Activity` | `id!`(ID 正则) · `revision!`(RevisionInt) · `created_at!`(date-time，带偏移) · `name!`(1–120) · `bank_id?`(ID 正则\|null) · `external_activity_id?`(ID 正则\|null) · `description!`(0–1000) · `status!`(enum) · `current_rule_id?`(ID 正则\|null) · `bindings!`(0–1000) · `rule_ids!`(0–1000，ID 正则) · `receipt_ids!`(0–1000，ID 正则) | `operations.getActivity.schemas.Activity`（12 个属性全部在 `required` 内，`additionalProperties=false`） |
| `Binding` | `strategy_id!`(ID 正则) · `source_version!`(1–80) · `valid_from!`(format=date) · `valid_until!`(format=date) · `evidence_id!`(ID 正则，**非空**) | `operations.getActivity.schemas.Binding`（5 属性全必填） |
| `ActivityPage` | `items!`(0–100 个 `Activity`) · `next_cursor!`(1–300 \| null) | `operations.listActivities.schemas.ActivityPage`（与 `WorkspacePage` 同构，A91 追加口径） |
| `ActivityCreate` | `name!`(1–120) · `bank_id?` · `external_activity_id?` · `description?`(0–1000) | `operations.createActivity.schemas.ActivityCreate`（`required` 实测只有 `name`） |
| `ActivityUpdate` | `name?`(1–120) · `description?`(0–1000) · `status?`(enum `OPEN`/`ARCHIVED`) · `bindings?`(0–1000 个 `Binding`) | `operations.updateActivity.schemas.ActivityUpdate`（`required` 实测为**空数组**；**没有** `bank_id` / `external_activity_id` ⇒ 银行与外部活动号创建后不可改，§6.4 的 409 只可能在 create 面触发） |

`Activity.status` 的取值集合 = `operations.getActivity.schemas.Activity.properties.status.enum` 实取
（实测 `["OPEN","ARCHIVED"]`），与切片 `ddl.activities` 的 `CHECK(status IN ('OPEN','ARCHIVED'))` 逐字一致；
**实现禁抄字面量**，一律 `ActivityStatus = Literal[...]` 后 `ACTIVITY_STATES: Final[tuple[str, ...]] =
tuple(get_args(ActivityStatus))`（体例＝`worker/states.py::JOB_STATES`：取值来自活契约 DTO 的 Literal 参数，
契约改枚举代码立刻跟着改）。`Binding.valid_from` / `valid_until` 是 `format=date`（**日期**，非时刻）⇒
DTO 侧用 `date` 类型（pydantic 会拒绝带时间的串），落库为 `TEXT`；区间语义「起含止排」见 §3.4。

### 2.2 规则版本族

| DTO | 字段 | 真值来源 |
|---|---|---|
| `RuleVersion` | `id!` · `revision!`(RevisionInt) · `created_at!`(date-time) · `label!`(1–80) · `content!`(`RuleContent`) · `terms!`(0–1000 个 `Term`) · `source_rule_version?`(1–80\|null) · `parent_rule_id?`(ID 正则\|null) · `activity_id!`(ID 正则) · `state!`(enum `DRAFT`/`CONFIRMED`) · `digest!`(64 位 `^[0-9a-f]{64}$`) · `confirmed_at?`(date-time\|null) · `confirmation?`(0–1000\|null) | `operations.getRule.schemas.RuleVersion`（13 属性全必填，`additionalProperties=false`） |
| `RuleContent` | `oneOf[CouponRule, CallbackRule]`（**无判别式字段声明**，判别靠 `template` 的 `const`） | `operations.getRule.schemas.RuleContent`（实测 `{"oneOf":[{"$schema":"CouponRule"},{"$schema":"CallbackRule"}]}`） |
| `CouponRule` | `schema_version!`(const `1`) · `template!`(const `coupon_threshold`) · `currency!`(const `CNY`) · `zone!`(const `Asia/Shanghai`) · `starts_at!`(date-time) · `ends_at!`(date-time) · `new_customer_days!`(1–365) · `min_payment_fen!`(0–9000000000000) · `coupon_fen!`(1–9000000000000) · `max_per_customer!`(1–1000) · `budget_fen!`(0–9000000000000) · `stacking!`(enum `ALLOW`/`DENY_OTHER_APPLIED`) · `refund_policy!`(enum `KEEP`/`RECOMPUTE_UNUSED`) | `operations.getRule.schemas.CouponRule`（13 属性全必填；与 `contracts/rule-set.schema.json` 的 `$defs.CouponRule` 逐字同构） |
| `CallbackRule` | `schema_version!`(const `1`) · `template!`(const `callback_priority`) · `zone!`(const `Asia/Shanghai`) · `channel!`(const `remote`) · `priority!`(enum `ARRIVAL`/`APPOINTMENT_FIRST`) · `daily_cap!`(1–20) | `operations.getRule.schemas.CallbackRule`（6 属性全必填；同 `contracts/rule-set.schema.json` 的 `$defs.CallbackRule`） |
| `Term` | `key!`(ID 正则 1–96) · `clause!`(1–1000) · `decision!`(**0**–1000，Schema 允许空串) · `status!`(enum `OPEN`/`CONFIRMED`) · `evidence_id?`(ID 正则\|null) | `operations.getRule.schemas.Term`（5 属性全必填；`decision.minLength=0` 是**契约事实**，故「业务说明非空」只能由 §4 的领域门禁承担，禁改契约） |
| `RuleVersionPage` | `items!`(0–100 个 `RuleVersion`) · `next_cursor!`(1–300\|null) | `operations.listRules.schemas.RuleVersionPage` |
| `RuleCreate` | `label!`(1–80) · `content!` · `terms!`(0–1000) · `source_rule_version?`(1–80\|null) · `parent_rule_id?`(ID 正则\|null) | `operations.createRule.schemas.RuleCreate`（`required` 实测 = `label`,`content`,`terms`） |
| `RuleUpdate` | `label?`(1–80) · `content?` · `terms?`(0–1000) | `operations.updateRule.schemas.RuleUpdate`（`required` 实测为空数组 ⇒ 空 PATCH 必须 422；**没有** `parent_rule_id` / `source_rule_version` ⇒ 血缘创建后不可改） |

`RuleVersion.state` 的 Literal 别名记为 `RuleState`（**与 `api/common.py::JobState` 同名不同物，禁复用**）；
`RuleContent` 用 pydantic 的判别式联合落地：`Annotated[Union[CouponRule, CallbackRule], Field(discriminator="template")]`
——`template` 在两个分支上是不同 `const`，满足判别式要求，且能在**校验期**就给出
`issues[0].location="/content/template"` 级别的定位（比 `oneOf` 的「两个分支都失败」报错更可复查）。
`schema_version` 一律 `Literal[1]`（`architecture/RULES.md`「条款键与无效案例」：**确认前按 `schema_version` 1 验证**）。

### 2.3 确认 / 检查 / 比较族

| DTO | 字段 | 真值来源 |
|---|---|---|
| `Confirmation` | `note!`(1–500) · `digest!`(64 位小写 hex) | `operations.confirmRule.schemas.Confirmation` |
| `RuleCheck` | `rule_id!`(ID 正则) · `rule_digest!`(64 hex) · `state!`(enum `READY`/`NEEDS_CONFIRMATION`) · `issues!`(0–1000 个 `Issue`) · `boundary_cases!`(0–**30** 个内联对象) | `operations.checkRule.schemas.RuleCheck`（5 属性全必填） |
| `BoundaryCase`（内联匿名对象，本文命名） | `id!`(ID 正则) · `label!`(1–120) · `input!`(`CaseInput`) · `verification!`(1–500) | `operations.checkRule.schemas.RuleCheck.properties.boundary_cases.items`（实测 4 属性全必填、`additionalProperties=false`、`maxItems=30`；**没有任何 verdict / expected / actual 字段** ⇒ 契约本身就不允许本 op 返回判定结果，§5.4） |
| `Issue` | `code!`(ID 正则 1–96，**自由串**) · `location!`(1–500，JSON Pointer 形) · `message!`(1–500) · `severity!`(enum `ERROR`/`WARNING`/`INFO`) | `operations.checkRule.schemas.Issue`（与 `api/common.py::Issue` 既有定义逐字段一致 ⇒ **复用既有类，禁第二份**） |
| `CaseInput` | `oneOf[CouponCaseInput, CallbackCaseInput]` | `operations.checkRule.schemas.CaseInput` |
| `CouponCaseInput` | `schema_version!`(const 1) · `template!`(const `coupon_threshold`) · `customer_id!`(ID 正则) · `registered_at!`(date-time) · `initial_used!`(0–9000000000000) · `initial_budget_used_fen!`(0–9000000000000) · `events!`(1–1000 个 `CouponEvent`) | `operations.checkRule.schemas.CouponCaseInput`（与 `contracts/case-input.schema.json` 同源） |
| `CouponEvent` | `seq!`(1–9007199254740991) · `event_id!`(ID 正则) · `kind!`(enum `PAYMENT`/`REFUND`/`REDEEM`) · `at!`(date-time) · `order_id!`(ID 正则) · `amount_fen!`(0–9000000000000) · `other_offer_applied!`(bool) | `operations.checkRule.schemas.CouponEvent`（7 属性全必填） |
| `CallbackCaseInput` | `schema_version!`(const 1) · `template!`(const `callback_priority`) · `customer_id!` · `day!`(format=date) · `channel!`(const `remote`) · `used!`(0–9000000000000) · `events!`(1–1000 个 `CallbackEvent`) | `operations.checkRule.schemas.CallbackCaseInput` |
| `CallbackEvent` | `seq!` · `event_id!` · `at!`(date-time) · `strategy_id!`(ID 正则) · `appointment!`(bool) | `operations.checkRule.schemas.CallbackEvent`（5 属性全必填） |
| `RuleDiff` | `baseline_rule_id!` · `candidate_rule_id!` · `changes!`(0–1000 个 `FieldChange`) · `requires_rerun_case_ids!`(0–1000，ID 正则) | `operations.compareRules.schemas.RuleDiff`（4 属性全必填） |
| `FieldChange` | `path!`(1–500) · `before?`(0–1000\|null) · `after?`(0–1000\|null) | `operations.compareRules.schemas.FieldChange`（3 属性全必填；`before`/`after` 是**字符串化**取值，非任意 JSON ⇒ 见 §6.5 的渲染口径） |

### 2.4 落库映射（列 ↔ DTO；真值来源＝切片 `ddl.*`，与 `contracts/sqlite-v1.sql` 同源）

- `activities`：`workspace_id`(FK workspaces) · `id` · `name` · `bank_id`(可空) · `external_activity_id`(可空) ·
  `description`(**NOT NULL** ⇒ `ActivityCreate.description` 缺省时写 `""`，契约 `minLength=0` 允许) ·
  `status`(CHECK 2 值) · `current_rule_id`(可空，复合 FK `(workspace_id,current_rule_id)` → `rule_versions`) ·
  `revision`(≥1) · `created_at`；`PRIMARY KEY(workspace_id,id)`；
  **`UNIQUE(workspace_id,bank_id,external_activity_id)`**（§6.4 的 409 唯一物理来源）。
- `activity_bindings`：`workspace_id` · `activity_id` · `strategy_id` · `source_version` · `valid_from` ·
  `valid_until`(**`CHECK(valid_until>valid_from)`**) · `evidence_id`(**FK → `evidence(workspace_id,id)`**)；
  `PRIMARY KEY(workspace_id,activity_id,strategy_id,source_version,valid_from)`。
  ⇒ `Binding` 没有自己的 `id` 列，DTO 也**不得**发明一个（`additionalProperties=false` 会当场判红）。
- `rule_versions`：`workspace_id` · `id` · `activity_id`(FK activities) · `parent_rule_id`(可空，自引用 FK) ·
  `label` · `template`(**CHECK 2 值**，冗余于 `content_json.template`，写入时由 service 从 `content.template` 取，
  禁由客户端第二处给) · `source_rule_version`(可空) · `state`(CHECK 2 值) · `revision`(≥1) ·
  `content_json`(`json_valid`) · `terms_json`(`json_valid`) · `digest`(`length=64`) · `created_at` ·
  `confirmed_at`(可空) · `confirmation`(可空)；`CHECK((state='CONFIRMED')=(confirmed_at IS NOT NULL AND
  confirmation IS NOT NULL))`。
- **JSON 列的存法（冻结）**：`content_json = canonical_json(content.model_dump(mode="json"))`、
  `terms_json = canonical_json([t.model_dump(mode="json") for t in terms])`（**保持客户端给出的数组顺序**，
  排序只发生在摘要投影里，见 §4.6）。这样「落库字节」与「摘要输入」是同一份规范化文本，
  杜绝重序列化造成的摘要漂移（`architecture/DOMAIN.md`「内容摘要的固定投影」＋「可复算摘要」段）。
- `audit`：`PRIMARY KEY(workspace_id,sequence)`、`UNIQUE(workspace_id,id)`、`outcome CHECK IN
  ('ACCEPTED','DENIED','FAILED')`、`previous_digest`/`digest`(64)。哈希链与 `sequence` 由
  `application/audit.py::AuditWriter` 独家维护（本文**只 import**，禁改该文件、禁复制第二份链逻辑）。
- `receipts` / `cases`：本卡**只读**（`Activity.receipt_ids` 与 `RuleDiff.requires_rerun_case_ids` 需要），
  写入分别归 M2-03 与 M2-02；只读查询的口径见 §7.4。

### 2.5 DTO 落点（本文冻结为**方案 A**，方案 B 的映射见 §12 U-2）

- **方案 A（推荐，A91 同构 append-only）**：§2.1–§2.3 的全部新 DTO 追加进 `src/campaignlab/api/common.py`
  （纯追加、0 删除行），与 `WorkspacePage`/`Job` 同一份家：① 可直接复用模块内私有别名 `_IdStr` 与既有
  `RevisionInt`/`Issue`/`Problem`，不产生第二份定义（`domain/errors.py` docstring 的「严禁两处各存一份」口径）；
  ② `api/deps.py` 的端口 Protocol 能正常 import 它们而不与 `api/activities.py` 形成**循环导入**
  （若 DTO 住在 `api/activities.py`，则 `deps.py → activities.py → deps.py` 成环）；
  ③ 任务卡 `public_frozen` 行明写规则版本状态机与条款键集合落本文后「M2-02 / M2-03 / M2-04 按此消费」，
  而 M2-03 的 `scope_deny` **显式包含** `src/campaignlab/api/activities.py` 与 `api/rules.py` ⇒ DTO 若住在这两个文件里，
  下游卡**读不到**（会逼它们各抄一份）。
  代价：需同步 `api/common.py.__all__`（**项数以 `inspect` 实取为准，本文不写死**；`no_implicit_reexport`
  已开 ⇒ 不进 `__all__` 的名字下游 import 会判 mypy 错，LANE-COMMON §3.5），并需改
  `tests/unit/test_domain_errors.py::test_common_public_surface_is_unchanged` 里那条**按数字钉死**的断言
  （该文件不在本卡 `scope_allow`，属写权缺口，见 §11.8 与 §12 U-2）。
- **方案 B（零扩围回退）**：DTO 分别住 `api/activities.py`（活动族）与 `api/rules.py`（规则族），
  `_IdStr` 等私有别名在各自文件内**重新声明**（承认漂移风险），`api/deps.py` 的端口签名改用
  `if TYPE_CHECKING:` 导入以避免运行期成环，`RuleVersion`/`Activity` 的跨卡消费改为「按需 import 具体模块」。
  仅当编排器拒绝方案 A 的写权扩围时启用；两方案的**符号名与字段序完全一致**，故 §3–§10 的设计一字不改，
  §11 的文件级 TODO 按 §11.9 的映射表平移即可。

## 3. 状态机（`TransitionId` 形态对齐 `src/campaignlab/worker/states.py` 的既有体例）

**体例约定（照抄 `worker/states.py`，但禁 import 该模块）**：`worker/**` 在本卡 `scope_deny` 内，且其
`TransitionId = Literal["T1"…"T9"]` 是作业面的冻结类型，复用会让活动／规则迁移被塞进作业的 Literal。
故本卡在 `src/campaignlab/domain/activity/states.py` 内**同构另立**：`Literal` 别名 + `@dataclass(frozen=True,
slots=True)` 的迁移行 + `Final[tuple[…, …]]` 注册表 + 两条纯函数判定（`assert_*_transition_allowed` / `is_*_terminal`），
字段名与 `worker/states.py::Transition` 逐字对齐（`id` / `sources` / `target` / `trigger` / `spec_ref` / `guard` /
`transaction` / `creates_new_row`），使 Q 判定档能用同一套读法复核两张迁移表。状态取值一律
`tuple(get_args(<Literal 别名>))` 从契约 DTO 反推，**禁抄字面量**（`worker/states.py::JOB_STATES` 同法）。
`guard` 是那条 UPDATE 的 WHERE 谓词**可读镜像**，供测试逐条对照；**运行期只信 `rowcount`**
（`worker/states.py` docstring 的既有裁定，本文沿用）。

### 3.1 活动状态机（`ActivityStatus`；状态集 = `OPEN` / `ARCHIVED`；终态 = `ARCHIVED`）

`ActivityTransitionId = Literal["A1","A2","A3"]`；`ACTIVITY_TRANSITIONS` 恰 3 项（**运行时以 `len()` 实取为准，
本文不写死计数**），逐行：

| id | sources | target | trigger | spec_ref | guard（镜像） | transaction |
|---|---|---|---|---|---|---|
| `A1` | `()` | `OPEN` | `createActivity` 建活动（新建即 OPEN，DDL 无默认值 ⇒ service 显式写） | `architecture/DOMAIN.md`「对象与修改」活动及绑定行「OPEN → ARCHIVED」 | `INSERT … status='OPEN', revision=1` | `TX-A1 ActivityService.create_activity` |
| `A2` | `(OPEN,)` | `ARCHIVED` | `updateActivity` 且 `status="ARCHIVED"` | 同上 | `UPDATE activities SET status='ARCHIVED', revision=revision+1 WHERE … AND status='OPEN' AND revision=:revision` | `TX-A2 ActivityService.update_activity` |
| `A3` | `(OPEN,)` | `OPEN` | `updateActivity` 改 `name`/`description`/`bindings`（`status` 缺省或仍为 `OPEN`） | `architecture/API.md`「更新」行「PATCH 只覆盖给出的字段」 | `UPDATE … revision=revision+1 WHERE … AND status='OPEN' AND revision=:revision` | `TX-A2`（同一方法，仅 `status` 列不参与 SET） |

- `ACTIVITY_TERMINAL_STATES = frozenset({"ARCHIVED"})`，取值由 `tuple(get_args(ActivityStatus))` 的末项推出亦可，
  但**冻结为显式 frozenset**（与 `worker/states.py::TERMINAL_STATES` 同形，便于测试直接对撞）。
- **非法迁移的错误映射（冻结）**：`ARCHIVED → ARCHIVED`（归档后再 PATCH 任何字段，含 `status="ARCHIVED"` 的
  重复归档）与 `ARCHIVED → OPEN`（复活）在 `ACTIVITY_TRANSITIONS` 里**根本不存在** ⇒
  `assert_activity_transition_allowed` 一律抛 **409 `STATE_CONFLICT`**（`StateConflict`，
  detail 固定「活动已归档，不可再修改」，`issues[0].location="/status"`（请求里给了 `status` 时）或
  `issues[0].location="/"`（只改字段时），`issues[0].code="ACTIVITY_ARCHIVED"`）。
  归档后**读取不受限**（`getActivity` / `listActivities` / `listRules` / `getRule` / `checkRule` / `compareRules`
  照常 200），依据＝`DOMAIN.md`「有依赖活动归档后可查询历史」。
- **聚合终态的连带面（冻结）**：活动 `ARCHIVED` 后，其下 `createRule`（新草稿）、`updateRule`、`confirmRule`
  一律 **409 `STATE_CONFLICT`**（`issues[0].code="ACTIVITY_ARCHIVED"`，`issues[0].location="/activity_id"`）——
  理由：`confirmRule` 必须写 `activities.current_rule_id`（§3.2 R3），即会改动已归档活动行，与 A2/A3 的终态口径
  互相否证；`checkRule` / `compareRules` 是只读的，照常 200。此点非 spec 明文，见 §12 U-5（非阻塞提示项）。
- **每次被接受的 `updateActivity` 都 `revision + 1`**（含「值未变」的幂等赋值）：`revision` 是并发控制号而非
  内容号（`DOMAIN.md`「Revision 用于修改冲突控制，内容摘要用于业务版本」），故不做「无变化则不 bump」的优化——
  那会让客户端手里的 ETag 在两次相同 PATCH 后仍然有效，412 语义随之失效。

### 3.2 规则版本状态机（`RuleState`；状态集 = `DRAFT` / `CONFIRMED`；终态 = `CONFIRMED`，语义为「内容冻结」）

`RuleTransitionId = Literal["R1","R2","R3","R4"]`；`RULE_TRANSITIONS` 恰 4 项（以 `len()` 实取为准）：

| id | sources | target | trigger | spec_ref | guard（镜像） | transaction | creates_new_row |
|---|---|---|---|---|---|---|---|
| `R1` | `()` | `DRAFT` | `createRule`，`parent_rule_id` 缺省 | `DOMAIN.md`「规则版本」行「DRAFT 可修改」 | `INSERT … state='DRAFT', revision=1, confirmed_at=NULL, confirmation=NULL` | `TX-R1 RuleService.create_rule` | `False` |
| `R2` | `(DRAFT,)` | `DRAFT` | `updateRule`（改 `label` / `content` / `terms`） | 同上 ＋ `API.md`「更新」行 | `UPDATE rule_versions SET … revision=revision+1 WHERE … AND state='DRAFT' AND revision=:revision` | `TX-R2 RuleService.update_rule` | `False` |
| `R3` | `(DRAFT,)` | `CONFIRMED` | `confirmRule`（条款门禁 §4.2 ＋ 摘要匹配全过） | `DOMAIN.md`「CONFIRMED 固定字段和条款」；`RULES.md`「条款键与无效案例」 | `UPDATE … SET state='CONFIRMED', confirmed_at=:now, confirmation=:note, digest=:digest, revision=revision+1 WHERE … AND state='DRAFT' AND revision=:revision AND digest=:digest` | `TX-R3 RuleService.confirm_rule` | `False` |
| `R4` | `(CONFIRMED,)` | `DRAFT` | `createRule` 且 `parent_rule_id` = 某 `CONFIRMED` 版本 | `DOMAIN.md`「变动时以 `parent_rule_id` 建新草稿」 | `INSERT … state='DRAFT', parent_rule_id=:parent, revision=1`（**源行一字不改**） | `TX-R1`（同方法，仅多带 `parent_rule_id`） | **`True`** |

- `RULE_TERMINAL_STATES = frozenset({"CONFIRMED"})`。`R4` 的 `target` 落在**新行**上（体例＝`worker/states.py`
  的 `T9 creates_new_row=True`：「源作业终态一字不变」），故「终态不可再迁移」与「可从终态派生草稿」不矛盾。
- **非法迁移的错误映射（冻结）**：
  - `CONFIRMED --updateRule--> *`（AC-003 的「试编辑」）→ **409 `STATE_CONFLICT`**，detail 固定
    「已确认版本不可修改，请以其为父版本新建草稿」，`issues[0].location="/"`、`issues[0].code="RULE_CONFIRMED_IMMUTABLE"`。
    物理保证＝UPDATE 谓词带 `state='DRAFT'` ⇒ `rowcount=0`（禁先 SELECT 后 UPDATE 的裸检查，
    `application/idempotency.py` docstring 的「禁止裸先查后插」同理）。
  - `CONFIRMED --confirmRule--> CONFIRMED`（重复确认）→ **409 `STATE_CONFLICT`**，
    `issues[0].code="RULE_ALREADY_CONFIRMED"`。
  - `CONFIRMED → DRAFT`（就地回退／撤确认）在表里**不存在** ⇒ 409 `STATE_CONFLICT`，
    `issues[0].code="RULE_NO_UNCONFIRM"`。（契约无 `unconfirmRule` op，实测 11 个 op 里也没有。）
  - `R1`/`R4` 的 `parent_rule_id` 指向不存在或**别的活动**的版本 → **404 `RESOURCE_NOT_FOUND`**
    （`ResourceNotFound` docstring：归属校验失败与不存在必须逐字相同，不回显 ID）；
    指向 `DRAFT` 版本 → **409 `STATE_CONFLICT`**（`issues[0].code="PARENT_NOT_CONFIRMED"`；
    `DOMAIN.md` 只在「变动时」即从已确认版本派生，草稿没有后继语义）。
- **`activities.current_rule_id` 的联动（冻结）**：`R3` 成功后同事务执行
  `UPDATE activities SET current_rule_id=:rule_id, revision=revision+1 WHERE workspace_id=:ws AND id=:activity_id`
  （`DOMAIN.md`「最近确认版本为活动候选规则，原规则版本可按源证据继续用于历史比较」＋持久化列
  `activities.current_rule_id`）。因此**确认规则会使活动自身的 ETag 变化**，S6 必须把这条钉成用例
  （`confirmRule` 前后 `getActivity` 的 `ETag` 与 `current_rule_id` 都变）。
- **一父多确认后继**：切片 `ddl.rule_versions` 与其 `__indexes` 实测**没有**类似
  `cases_one_confirmed_child` 的部分唯一索引 ⇒ 同一父版本可有多个 `CONFIRMED` 后继；
  `current_rule_id` 取「该活动下 `confirmed_at` 最大者（并列时 `id` 字典序最大）」，与 DDL 无冲突。
  此点与 `cases` 的「每个父版本仅一条已确认直接后继」不同，**禁把 cases 的约束抄过来**（见 §12 U-6，非阻塞）。

### 3.3 迁移判定的唯一实现（禁两处各存一份）

`domain/activity/states.py` 只暴露纯函数，**不碰数据库、不开事务、不写 SQL**（`worker/states.py` 的既有红线）：
`assert_activity_transition_allowed(source: str | None, target: str, *, trigger: str) -> None`（`source=None` 表示新建）、
`assert_rule_transition_allowed(…)` 同形、`is_activity_terminal(state)` / `is_rule_terminal(state)`。
非法一律抛 `StateConflict`（**同一个类、同一个 code**，靠 `issues[0].code` 区分细因，禁为每种非法迁移造新异常类——
`domain/errors.py::DomainError` docstring 明写「不额外造类」，且 `PROBLEM_CODES` 是冻结的 20 码面）。

### 3.4 绑定（无状态列，但有效期区间代数必须冻结；`Binding` 5 字段全必填，无 `id`）

- **区间语义**：`[valid_from, valid_until)` —— 起日**包含**、截止日**排除**（`DOMAIN.md`「绑定使用生效起日包含、
  截止日排除」）。故 `valid_until == valid_from` 是**空区间**，DDL `CHECK(valid_until>valid_from)` 也会拒；
  领域侧必须**先**判，否则 SQLite 的 `IntegrityError` 会被兜成 500：违例 → **422 `VALIDATION_ERROR`**，
  `issues[0].location="/bindings/<i>/valid_until"`、`issues[0].code="BINDING_EMPTY_INTERVAL"`。
- **权威绑定唯一（冻结判定式）**：同一 `strategy_id` 下，两条绑定的区间**相交**（`a.valid_from < b.valid_until
  AND b.valid_from < a.valid_until`，起含止排的标准相交式）即违例 → **422 `VALIDATION_ERROR`**，
  `issues` 同时给出两条的 `location`（`/bindings/<i>/…` 与 `/bindings/<j>/…`）、`issues[0].code="BINDING_OVERLAP"`。
  依据＝`DOMAIN.md`「相同策略同有效区间仅允许一条权威绑定」；本文取**更严**的「相交即拒」而非「仅完全相同才拒」，
  因为部分重叠同样使「该策略在该日生效的是哪一条」不可判定（AC-002 的「缺绑定」判定依赖这个唯一性）。
  更宽口径见 §12 U-4（非阻塞，倾向维持严口径）。
- **PATCH 的 `bindings` 语义（冻结）**：`ActivityUpdate.bindings` 一旦**出现在请求里**（`model_fields_set` 命中），
  就是对该活动绑定集合的**整体替换**（同事务 `DELETE FROM activity_bindings WHERE workspace_id=? AND activity_id=?`
  后按数组顺序 `INSERT`）；未出现则**完全不动**（AC-002 的「AC-202 保持无绑定」靠这条）。
  依据＝`API.md`「PATCH 只覆盖给出的字段」：数组是值，不是 merge-patch 的键集合。
  数组内 `(strategy_id, source_version, valid_from)` 重复会撞 PK ⇒ 领域侧先判，
  违例 → 422 `VALIDATION_ERROR`、`issues[0].code="BINDING_DUPLICATE_KEY"`（禁让 `IntegrityError` 冒到 500）。
- **`evidence_id` 的存在性（冻结）**：DDL 有 `FOREIGN KEY(workspace_id,evidence_id) REFERENCES evidence(workspace_id,id)`
  且 `Binding.evidence_id` **非空** ⇒ 每条绑定都必须指向本工作区已登记的证据行。写入前由 service 显式查
  `evidence` 表（只读），缺失 → **422 `EVIDENCE_REQUIRED`**，`issues[0].location="/bindings/<i>/evidence_id"`、
  `issues[0].code="BINDING_EVIDENCE_UNREGISTERED"`（`API.md` 422 行的「业务前置条件」＋ code 字面义「证据不齐备」）。
  **本卡不实现任何 evidence 写入面**：`registerEvidence` / `getEvidence` 归 M1-03（A1 裁定，见
  `orchestrator/tasks/M1-03.md`），S5/S6 的用例一律用 SQL 直接播种 `artifacts` + `evidence` 行
  （`evidence.artifact_id` 有 FK，播种必须两表同插），禁 import `api/evidence.py`。

## 4. 条款确认门禁（`confirmRule`；对齐 AC-004「必填条款未确认时无法确认」）

### 4.1 条款键集合（任务卡 `public_frozen` 面，M2-02 / M2-03 / M2-04 按此消费，改动走 CR）

`architecture/RULES.md`「条款键与无效案例」原文：「满额赠券需要 `new_customer`、`payment`、`time_window`、
`stacking`、`budget_and_quota`、`refund` 六项确认。远程回拨需要 `same_day_scope`、`priority`、`daily_cap` 三项确认。」
⇒ 冻结为一张**按模板索引**的必需键表（顺序即 `RULES.md` 的原文顺序，供 `issues[]` 稳定排序）：

- `REQUIRED_CLAUSE_KEYS["coupon_threshold"] = ("new_customer", "payment", "time_window", "stacking",
  "budget_and_quota", "refund")`
- `REQUIRED_CLAUSE_KEYS["callback_priority"] = ("same_day_scope", "priority", "daily_cap")`
- `ALL_CLAUSE_KEYS` = 上述两元组按序去重后的并集（**项数以 `len(ALL_CLAUSE_KEYS)` 运行时实取为准，禁写死**），
  与任务卡 `public_frozen` 行列出的键集合逐字相同。
- 键名**禁**发明成 spec 之外的值（任务卡「禁止」行）；表外的自由键**允许**存在（`RULES.md`：「自由条款作为来源，
  业务人员确认它所映射的字段」），既不阻塞确认、也不参与必需性判定，但**同键重复**一律拒（§4.2 第 3 条）。

### 4.2 确认前置条件与判定顺序（冻结；顺序即代码顺序，S2/S4 禁调序）

`RULES.md`「确认需要字段齐全、待决事项关闭及当前摘要匹配」＋「每个必需键状态 CONFIRMED，含已登记来源和业务说明」
⇒ 在 `TX-R3` 内、拿到行锁后按下列顺序判定，**任一不通过即抛，不做后续判定**（避免一次返回一堆互相掩盖的错）：

1. **存在性与工作区隔离**：`rule_versions` 行不存在或属外工作区 → 404 `RESOURCE_NOT_FOUND`（同一句 detail）。
2. **幂等优先**：`Idempotency-Key` 命中同摘要 → 直接回放信封（**不再**判 If-Match / 门禁），依据
   `API.md`「先查幂等重放，再查 If-Match」＋ `api/common.py::check_if_match` docstring 的同一裁定。
3. **If-Match**：缺头 → 428 `PRECONDITION_REQUIRED`；与当前 `revision` 不符 → 412 `REVISION_CONFLICT`
   （一律调 `api/common.py::check_if_match(header, current_revision)`，**禁**自己比较字符串或另编 detail）。
4. **状态**：目标已 `CONFIRMED` → 409 `STATE_CONFLICT`（§3.2）。活动已 `ARCHIVED` → 409 `STATE_CONFLICT`（§3.1）。
5. **`schema_version`**：`content.schema_version != 1` → 422 `VALIDATION_ERROR`、
   `issues[0].location="/content/schema_version"`、`issues[0].code="SCHEMA_VERSION_UNSUPPORTED"`
   （`RULES.md`「确认前按 `schema_version` 1 验证」；契约的 `const: 1` 已在解析期挡住绝大多数情况，
   本条是纵深防御，禁删）。
6. **摘要匹配**：`Confirmation.digest != <按 §4.6 现算的 rule_digest>` → **409 `VERSION_MISMATCH`**
   （`DomainError(code="VERSION_MISMATCH")`，该码在 20 码注册表内但**没有**专属异常类，
   依 `domain/errors.py::DomainError` docstring 的口径直接抛），`issues[0].location="/digest"`、
   `issues[0].code="CONFIRMATION_DIGEST_MISMATCH"`，detail 固定「确认摘要与当前规则内容不一致，请重新读取后再确认」，
   **禁回显两个摘要值**（回显等于给客户端一个「服务端存了哪一版」的探针，`application/idempotency.py::CONFLICT_DETAIL`
   的同一思路）。
7. **条款门禁（本文的核心）**：按 §4.3 的六条规则逐项收集 `Issue`；只要存在 `severity="ERROR"` 的项 →
   **422 `EVIDENCE_REQUIRED`**，`issues` = 收集到的**全部** ERROR 项（按 `REQUIRED_CLAUSE_KEYS` 的键序、
   再按数组下标稳定排序），`detail` 固定「必需条款未全部确认，无法确认该规则版本」。
8. **警告需备注**：若存在 `severity="WARNING"` 的项（来自 §5 的检查项框架），则 `Confirmation.note`
   经 NFKC + `strip()` 后必须**非空** → 否则 **422 `EVIDENCE_REQUIRED`**、`issues[0].location="/note"`、
   `issues[0].code="CONFIRMATION_NOTE_REQUIRED"`，detail 固定「存在需审核备注的警告，请在确认备注中记录判断」。
   依据＝`RULES.md`「错误阻止确认，警告需要审核者在确认备注记录判断」。契约的 `note.minLength=1` 允许单个空格
   （真值来源 `operations.confirmRule.schemas.Confirmation.properties.note`），故「非空」必须由领域侧判、禁依赖 Schema。
9. 全过 → 执行 R3 的 UPDATE（谓词见 §3.2）＋ `activities.current_rule_id` 联动 ＋ 审计（§7.3），同事务提交。

### 4.3 条款门禁的六条规则（逐条给 `Issue` 三元组；全部只读 `terms` 数组与 `evidence` 表）

设 `required = REQUIRED_CLAUSE_KEYS[content.template]`，`by_key = 按 key 分组后的 terms`：

| # | 条件 | severity | `Issue.code` | `Issue.location` | `message`（≤500，中文固定句式） |
|---|---|---|---|---|---|
| G1 | `k ∈ required` 但 `k ∉ by_key` | ERROR | `CLAUSE_MISSING` | `/terms/<k>` | 「必需条款 `<k>` 缺失」 |
| G2 | `k ∈ required` 且 `by_key[k]` 的 `status != "CONFIRMED"`（即 `OPEN`） | ERROR | `CLAUSE_UNCONFIRMED` | `/terms/<k>/status` | 「必需条款 `<k>` 仍为 OPEN」 |
| G3 | 任一 `key` 在 `terms` 里出现 **>1 次**（含自由键） | ERROR | `CLAUSE_DUPLICATE` | `/terms/<i>` 与 `/terms/<j>` 两条 | 「条款键 `<k>` 重复登记」 |
| G4 | `k ∈ required` 且 `evidence_id is None` | ERROR | `CLAUSE_EVIDENCE_MISSING` | `/terms/<k>/evidence_id` | 「必需条款 `<k>` 缺已登记来源」 |
| G5 | `k ∈ required` 且 `evidence_id` 在 `evidence(workspace_id,id)` 中查不到 | ERROR | `CLAUSE_EVIDENCE_UNREGISTERED` | `/terms/<k>/evidence_id` | 「必需条款 `<k>` 的来源未登记」 |
| G6 | `k ∈ required` 且 `decision.strip()` 为空（契约允许 `minLength=0`） | ERROR | `CLAUSE_DECISION_EMPTY` | `/terms/<k>/decision` | 「必需条款 `<k>` 缺业务说明」 |

- `clause` 非空由契约保证（`operations.getRule.schemas.Term.properties.clause.minLength=1`），**不另设**门禁项。
- G5 的存在性校验依据 `DOMAIN.md`「复杂可空引用和对象类型在领域服务校验」（`terms_json` 是 JSON 列、无 FK，
  物理层不会替我们守）＋ `RULES.md`「含**已登记**来源」。它使 M2-01 与 M1-03 的 evidence 行产生**数据**依赖
  （不是代码依赖，不违反「跨 lane 并行期的依赖即假依赖」）：见 §12 U-3。
- 六条全是 **ERROR** ⇒ 全部阻塞确认（`RULES.md`「错误阻止确认」）。**门禁本身不产生 WARNING**；
  WARNING 只来自 §5 的检查项框架（预算低于单张券、多规则覆盖同一情境），对应「警告需备注」的 §4.2 第 8 条。
- `Issue.code` 是**自由串**（真值来源 `operations.checkRule.schemas.Issue.properties.code`：ID 正则 1–96），
  与 `Problem.code` 的 20 码注册表是**两个面**；本表 12 个 code（G1–G6 六个 + §3.4 四个 + §4.2 两个）
  构成 M2-01 的 `Issue.code` 登记面，冻结在 `domain/activity/clauses.py`（`CLAUSE_ISSUE_CODES`）与
  `domain/activity/checks.py`（`CHECK_ISSUE_CODES`）里，**禁**提升为 `Problem.code`（ADR-005 §2.1；
  同型裁定 N7③ / A88③）。

### 4.4 确认后的不可变性（三层保证，缺一即判设计不合格）

1. **契约层**：`RuleUpdate` 只有 `label` / `content` / `terms`（真值来源
   `operations.updateRule.schemas.RuleUpdate.properties`），没有 `state` ⇒ 客户端无法用 PATCH 改状态。
2. **SQL 层**：所有针对 `rule_versions` 的 UPDATE 谓词**必须**带 `state='DRAFT'`（R2）或
   `state='DRAFT' AND revision=:revision AND digest=:digest`（R3），运行期只信 `rowcount`；
   `rowcount=0` 时按「先判 404、再判 412、最后判 409」的顺序翻译（能区分是因为行已在事务内读出）。
3. **领域层**：`assert_rule_transition_allowed("CONFIRMED", …)` 在 service 入口先跑一次，
   让「试编辑」在**读事务**里就拿到 409（AC-003 的「确认并试编辑」需要这个确定的错误面，
   而不是依赖 UPDATE 落空）。

### 4.5 `Confirmation.note` 与 `RuleVersion.confirmation` 的落点

`RuleVersion.confirmation` 是 `0–1000` 可空串（真值来源 `operations.getRule.schemas.RuleVersion.properties.confirmation`），
`Confirmation.note` 是 `1–500` 必填（同切片 `.Confirmation.properties.note`）⇒ 确认时
`confirmation = note`（长度天然满足 ≤1000），`confirmed_at = clock.now()`（**显式时钟**，
任务卡「禁止」行：不用系统当前时间做领域计算）。二者必须**同时**非空，否则撞 DDL 的双向 CHECK。

### 4.6 规则摘要（`rule_digest`）的固定投影

`DOMAIN.md`「内容摘要的固定投影」表·规则行原文：「`content`、按 key 排序的 `terms`、`source_rule_version`。
规则标签和确认说明分别审计」⇒ 冻结：

- 投影信封 `{"content": <content.model_dump(mode="json")>, "source_rule_version": <str|None>,
  "terms": [<每个 term.model_dump(mode="json")>，按 `key` 升序排序]}`；
  `rule_digest = hashlib.sha256(canonical_json(信封).encode("utf-8")).hexdigest()`（64 位小写）。
  **必须**复用 `api/common.py::canonical_json`（键排序、无多余空白、非 ASCII 原样、字符串先 NFC），
  禁自己 `json.dumps`（该函数 docstring 明写「两个 lane 各写一个 `json.dumps` 就会让同键同体算出不同摘要」）。
- **不参与**摘要：`id` / `revision` / `created_at` / `activity_id` / `parent_rule_id` / `state` /
  `confirmed_at` / `confirmation` / **`label`**（`DOMAIN.md`「业务摘要排除运行时间、作业号、租约和随机资源 ID」；
  `label` 与确认说明按原文「分别审计」⇒ 走 §7.3 的独立审计事件，不进摘要）。
  故**改 `label` 不改 `digest`**：这是 S6 必须钉住的反直觉用例（`updateRule` 只改 label → `ETag` 变、`digest` 不变）。
- `terms` 排序键只用 `key`（G3 已保证同键不重复 ⇒ 排序稳定、无二级键歧义）；`RuleVersion.terms` 的**响应顺序**
  则保持落库顺序（§2.4），两者不同，禁混用。
- 同一个投影函数（`domain/activity/digests.py::rule_digest(content, terms, source_rule_version)`）是
  `rule_versions.digest` 列、`RuleVersion.digest` 字段、`RuleCheck.rule_digest`、`Confirmation.digest` 比对的
  **唯一**实现（四处一个来源，禁复制）。

## 5. 检查项框架（`checkRule`；对齐 AC-004「门槛、预算、叠加、日期和退款口径分别检查」）

### 5.1 注册形态（与 §3 的迁移表同构，便于同一套读法复核）

`CheckId = Literal["C1","C2","C3","C4","C5","C6","C7","C8","C9"]`（形态对齐 `worker/states.py::TransitionId`）；
`CheckCategory = Literal["DATE","THRESHOLD","BUDGET","STACKING","REFUND","TEMPLATE","SEQUENCE","COMPETITION"]`
（前五类即 AC-004 点名的「日期 / 门槛 / 预算 / 叠加 / 退款口径」，后三类来自 `RULES.md`「规则检视」的
「候选同模板、竞争和事件顺序」）；`TemplateId = Literal["coupon_threshold","callback_priority"]`
（取值 = 切片 `ddl.rule_versions` 的 `CHECK(template IN (…))` 与 `operations.getRule.schemas.CouponRule.properties.
template.const` / `.CallbackRule.properties.template.const`，两处逐字一致）。

`@dataclass(frozen=True, slots=True) class Check`：`id: CheckId` · `category: CheckCategory` ·
`templates: tuple[TemplateId, ...]` · `spec_ref: str`（`RULES.md` 的行级出处）· `clause_keys: tuple[str, ...]`
（本检查项负责「未确认即报 ERROR」的那些必需键，见 §5.3 的归属表）· `run: Callable[[RuleContext], CheckResult]`
（纯函数；`RuleContext` 只含 `content` / `terms` / `template` / `sibling_confirmed_rules`，**不含连接、不含时钟**）。
`CHECKS: Final[tuple[Check, …]]` 是**唯一**注册表，`CHECK_IDS = tuple(get_args(CheckId))`，
运行期以 `len(CHECKS) == len(CHECK_IDS)` 自证「不多不少」（体例＝`worker/states.py` 的「9 条不多不少」），
`CheckId` 表外或重复注册即启动期断言失败（`domain/activity/checks.py` 模块级 `assert`，禁静默跳过）。

`CheckResult` = `tuple[Issue, …] + tuple[BoundaryCaseDraft, …]` 的冻结数据类（`issues` / `boundary_cases` 两个字段），
`BoundaryCaseDraft` 是**领域侧**中间形态（`id` / `label` / `input` 的领域数据 / `verification`），
由 `api/rules.py` 组装成契约 DTO（分层：领域层不 import `api`，`domain/errors.py` 的既有 TYPE_CHECKING 口径）。

### 5.2 判定结果结构（`RuleCheck` 四段，逐段给冻结口径）

- `rule_id` = 路径 `rule_id`（原样回显；已通过 404 隔离校验）。
- `rule_digest` = `rule_versions.digest` 列值**原样读出**；同时用 §4.6 的投影函数现算一次并断言两者相等，
  不等 → **500 `INTERNAL_ERROR`**（`InternalFailure`，detail 只含 request_id，不回显摘要——这是数据损坏，
  不是客户端错误）。这一条是「守护必须有牙」的落点：摘要投影一旦被第二份实现污染，这里立刻红。
- `state` = `"NEEDS_CONFIRMATION"` **当且仅当** `issues` 里存在 `severity == "ERROR"` 的项；否则 `"READY"`
  （`RULES.md`「发现条款未确认时返回 NEEDS_CONFIRMATION」；条款未确认由 §5.3 的归属检查项报成 ERROR）。
  **警告面**：`WARNING` / `INFO` **不**影响 `state`（它们是「可复查告警」，`RULES.md`「预算低于单张券、
  多个规则覆盖同一情境分别给到可复查告警」）。
  ⚠ **命名陷阱（S4/S5 必读）**：`RuleCheck.state` 是**检查结论**（`READY`/`NEEDS_CONFIRMATION`），
  与 `RuleVersion.state`（`DRAFT`/`CONFIRMED`）、与 `listRules` 的 `status` **查询参数**（过滤 `rule_versions.state`）
  是三个不同的面，取值集合互不相同，禁互相赋值。
- `issues` = 全部检查项产出的 `Issue` 之和，**去重键 = `(code, location)`**（同一事实只报一次；
  §5.3 的归属表已保证「每个必需键只由一个检查项负责报未确认」，去重是纵深防御），
  排序 = 先按 `CHECKS` 的注册序、再按检查项内部产出序（稳定、可复跑）。
  上限 `maxItems=1000`（真值来源 `operations.checkRule.schemas.RuleCheck.properties.issues`）⇒ 组装前
  `assert len(issues) <= 1000`，超限 → 500 `INTERNAL_ERROR`（不是截断：截断会让「有几个错」不可信）。
- `boundary_cases` = 各检查项产出的反例之和，`id` 全局唯一（`bc-<CheckId>-<序号>`，如 `bc-C2-1`；
  必须匹配 ID 正则，真值来源 `…RuleCheck.properties.boundary_cases.items.properties.id`），
  上限 **30**（同上真值来源 `maxItems=30`）⇒ 组装前 `assert len(boundary_cases) <= 30`；
  按 §5.4 的配方，满额赠券最多 15 条、远程回拨最多 3 条，**天然不触顶**（该余量是给 M2-02 扩充用的，
  本卡不预留占位项）。

### 5.3 九项检查（逐条冻结：触发条件 → severity → `Issue.code` → `location`；反例配方见 §5.4）

| id | category | templates | 负责的必需键 | 触发条件（全部只读 `RuleContext`） | severity / `Issue.code` | `spec_ref` |
|---|---|---|---|---|---|---|
| `C1` | DATE | coupon | `time_window` | `starts_at >= ends_at` | ERROR `WINDOW_ORDER_INVALID` @ `/content/ends_at` | `RULES.md`「检查活动时间顺序」 |
| | | | | `time_window` 键缺失 / `status!="CONFIRMED"` / `evidence_id is None` | ERROR `TIME_WINDOW_CLAUSE_UNCONFIRMED` @ `/terms/time_window` | `RULES.md`「条款键与无效案例」 |
| `C2` | THRESHOLD | coupon | `payment` | `coupon_fen > min_payment_fen` | WARNING `REWARD_EXCEEDS_THRESHOLD` @ `/content/coupon_fen` | `RULES.md`「阈值和奖励量」 |
| | | | | `min_payment_fen == 0` | WARNING `THRESHOLD_ZERO` @ `/content/min_payment_fen` | 同上 |
| | | | | `payment` 键未确认（三态同 C1） | ERROR `PAYMENT_CLAUSE_UNCONFIRMED` @ `/terms/payment` | 同上 |
| `C3` | BUDGET | coupon | `budget_and_quota` | `budget_fen == 0` | ERROR `BUDGET_ZERO` @ `/content/budget_fen` | `RULES.md`「预算和单人上限」 |
| | | | | `budget_fen < coupon_fen` | WARNING `BUDGET_BELOW_COUPON` @ `/content/budget_fen` | `RULES.md`「预算低于单张券…可复查告警」（**原文点名**） |
| | | | | `max_per_customer * coupon_fen > budget_fen` | INFO `QUOTA_EXCEEDS_BUDGET` @ `/content/max_per_customer` | `RULES.md`「预算和单人上限」 |
| | | | | `budget_and_quota` 键未确认 | ERROR `BUDGET_CLAUSE_UNCONFIRMED` @ `/terms/budget_and_quota` | 同上 |
| `C4` | STACKING | coupon | `stacking` | `stacking` 键未确认 | ERROR `STACKING_CLAUSE_UNCONFIRMED` @ `/terms/stacking` | `RULES.md`「叠加条件」 |
| | | | | `stacking == "ALLOW"` | INFO `STACKING_ALLOW` @ `/content/stacking`（记录生效口径，供复查） | 同上 |
| `C5` | REFUND | coupon | `refund` | `refund` 键未确认 | ERROR `REFUND_CLAUSE_UNCONFIRMED` @ `/terms/refund` | `RULES.md`「退款条款」 |
| | | | | `refund_policy == "RECOMPUTE_UNUSED"` | INFO `REFUND_RECOMPUTE` @ `/content/refund_policy` | `RULES.md`「RECOMPUTE_UNUSED 下…撤回」 |
| `C6` | TEMPLATE | 两者 | —（集合级） | `content.template` 不在 2 值白名单 | ERROR `TEMPLATE_UNKNOWN` @ `/content/template` | `RULES.md`「候选同模板」；切片 `ddl.rule_versions` 的 CHECK |
| | | | | 任一 `const` 字段偏离契约常量（`schema_version`/`currency`/`zone`/`channel`/`template`） | ERROR `TEMPLATE_CONST_MISMATCH` @ `/content/<字段名>` | `operations.getRule.schemas.CouponRule`（各 `const`） |
| | | | | `compareRules` 场景：baseline 与 candidate 的 `template` 不同 | （不落 `RuleCheck`，直接 422 `VALIDATION_ERROR`，`issues[0].code="TEMPLATE_MISMATCH"`，见 §1.11） | `RULES.md`「候选同模板」 |
| `C7` | DATE | coupon | `new_customer` | `new_customer` 键未确认 | ERROR `NEW_CUSTOMER_CLAUSE_UNCONFIRMED` @ `/terms/new_customer` | `RULES.md`「新客在支付时按注册时刻起不足 new_customer_days×24 小时」 |
| | | | | `new_customer_days <= 0`（契约 `minimum=1` 已挡，纵深防御） | ERROR `NEW_CUSTOMER_WINDOW_INVALID` @ `/content/new_customer_days` | 同上 |
| `C8` | SEQUENCE | callback | `same_day_scope`,`priority`,`daily_cap` | 三键中任一未确认（逐键各报一条） | ERROR `SAME_DAY_CLAUSE_UNCONFIRMED` / `PRIORITY_CLAUSE_UNCONFIRMED` / `DAILY_CAP_CLAUSE_UNCONFIRMED` @ `/terms/<键>` | `RULES.md`「远程回拨」「事件顺序」「同日抢占与频次用尽」 |
| | | | | `priority == "APPOINTMENT_FIRST"` | INFO `PRIORITY_APPOINTMENT_FIRST` @ `/content/priority` | `RULES.md`「先已预约组，再按各组 at、seq」 |
| `C9` | COMPETITION | 两者 | — | 同活动下存在**另一条** `CONFIRMED` 规则版本、同 `template`、且（coupon 时）窗口与本版相交 | WARNING `RULE_OVERLAP_REVIEW` @ `/content`（`message` 里给出对方 `rule_id`） | `RULES.md`「多个规则覆盖同一情境分别给到可复查告警」 |

- **每个必需键恰由一个检查项负责**（coupon：`time_window`→C1、`payment`→C2、`budget_and_quota`→C3、
  `stacking`→C4、`refund`→C5、`new_customer`→C7；callback：三键→C8），与 §4.3 的 G1/G2/G4 **不重复报同一事实**：
  门禁（§4）跑在 `confirmRule` 里、返回 `Problem.issues`；检查（§5）跑在 `checkRule` 里、返回 `RuleCheck.issues`。
  两个面**共用同一份键表** `REQUIRED_CLAUSE_KEYS`（§4.1，唯一来源），但各自独立求值、互不调用
  （`checkRule` 是只读 GET，**不得**触发门禁的写路径）。
- `Issue.message` 一律中文固定句式（含具体键名／数值），**禁**把 SQL、堆栈、用户源字段写进去
  （`framework/PYTHON.md`「不泄露用户源字段」）；长度按契约截到 ≤500。
- `Issue.location` 一律 JSON Pointer 形（`domain/errors.py::ValidationFailure` docstring 的既有要求），
  数组用**键名**而非下标定位条款（`/terms/stacking`），因为条款的身份是 `key`、下标会随客户端顺序漂移；
  `bindings` 侧（§3.4）用下标（`/bindings/0/valid_until`），因为 `Binding` 没有身份键 —— 这个差异是**刻意的**，
  S5/S6 断言时禁统一。

### 5.4 反例（`boundary_cases`）的生成配方（**只生成数据与待验证行为文案，禁判定、禁回放**）

全部时间戳与金额**只从被检规则版本的 `content` 推导**，`checkRule` 无正文、无查询参数 ⇒
**禁读时钟**（`clock.now()` 不得出现在反例生成路径上；任务卡「禁止」行＋`framework/PYTHON.md`
「每次业务运行传入显式时钟或事件时间」）。同一规则版本重复调用必须产出**逐字节相同**的 `boundary_cases`
（S6 钉这条：两次 GET 的响应体除 `X-Request-Id` 外全等）。

`RULES.md`「基于支持字段生成最小反例，包括阈值减一分、等于阈值、活动起止边界、重复支付、互斥命中、
预算刚足和不足、退款后跌破阈值、已核销退款、同日抢占与频次用尽」⇒ 十类逐条落地
（`customer_id="CUS-CHECK"`、`initial_used`/`initial_budget_used_fen` 缺省 0、事件 `seq` 从 1 连续、
`event_id`/`order_id` 用 `EV-<CheckId>-<n>-<seq>` / `ORD-<CheckId>-<n>-<seq>` 形态，均满足 ID 正则）：

| # | 归属 | `id` | `label`（≤120） | `input` 配方 | `verification`（待验证行为，≤500） |
|---|---|---|---|---|---|
| 1 | C2 | `bc-C2-1` | 门槛减一分 | 单个 `PAYMENT`，`amount_fen = min_payment_fen - 1`；**`min_payment_fen == 0` 时本条不生成**（无合法减一分值，且 C2 已报 `THRESHOLD_ZERO`） | 「净实付低于门槛一分，期望不发放（原因码 BELOW_THRESHOLD）」 |
| 2 | C2 | `bc-C2-2` | 等于阈值 | `amount_fen = min_payment_fen` | 「相等边界通过，期望发放一张（原因码 ISSUED）」 |
| 3 | C1 | `bc-C1-1` | 活动起点（含） | `at = content.starts_at` | 「起点包含，期望参与判定（`[starts_at, ends_at)` 左闭）」 |
| 4 | C1 | `bc-C1-2` | 活动终点（排） | `at = content.ends_at` | 「终点排除，期望不触发（原因码 OUTSIDE_ACTIVITY）」 |
| 5 | C8/C1 | `bc-C1-3` | 重复支付 | 两个 `PAYMENT`：`seq=1,2`、**同一 `event_id`**、同 `order_id`、同 `amount_fen` | 「同 ID 同业务字段仅记重复（原因码 DUPLICATE_EVENT），第二笔不再发放」 |
| 6 | C4 | `bc-C4-1` | 互斥命中 | 单个 `PAYMENT`，`other_offer_applied = true`，`amount_fen = min_payment_fen` | 「`DENY_OTHER_APPLIED` 下期望被抑制（原因码 STACK_DENIED）；`ALLOW` 下期望照常发放」 |
| 7 | C4 | `bc-C4-2` | 叠加放行 | 同上但 `other_offer_applied = false` | 「无互斥优惠，期望发放（原因码 ISSUED）」 |
| 8 | C3 | `bc-C3-1` | 预算刚足 | `initial_budget_used_fen = max(budget_fen - coupon_fen, 0)`，单笔 `amount_fen = min_payment_fen` | 「剩余预算恰够一张，期望发放后预算用尽（原因码 ISSUED）」 |
| 9 | C3 | `bc-C3-2` | 预算不足 | `initial_budget_used_fen = budget_fen` | 「剩余预算不足一张，期望不发放（原因码 BUDGET_EXHAUSTED）」 |
| 10 | C3 | `bc-C3-3` | 频次用尽 | `initial_used = max_per_customer` | 「单人次数已用尽，期望不发放（原因码 CUSTOMER_LIMIT）」 |
| 11 | C5 | `bc-C5-1` | 退款后跌破阈值 | `PAYMENT(amount_fen=min_payment_fen)` 后 `REFUND(amount_fen=1)`；**`min_payment_fen == 0` 时不生成** | 「净实付回落到门槛以下：`RECOMPUTE_UNUSED` 下撤回未核销券（REVOKED），`KEEP` 下保持（REFUND_RECORDED）」 |
| 12 | C5 | `bc-C5-2` | 已核销退款 | `PAYMENT(min_payment_fen)` → `REDEEM(amount_fen=0)` → `REFUND(amount_fen=1)` | 「券已核销后退款，期望转人工（USED_COUPON_REVIEW / manual_review=true）」 |
| 13 | C7 | `bc-C7-1` | 新客未满 | `registered_at = starts_at - (new_customer_days*24 - 1) 小时`，`PAYMENT` 发生在 `starts_at` | 「注册尚未满 `new_customer_days` 天，期望按新客发放（原因码 ISSUED）」 |
| 14 | C7 | `bc-C7-2` | 新客已满 | `registered_at = starts_at - (new_customer_days + 1)*24 小时` | 「注册已满，期望不发（原因码 NOT_NEW）」 |
| 15 | C7 | `bc-C7-3` | 注册时刻在未来 | `registered_at = starts_at + 24 小时` | 「注册时刻晚于事件时刻属无效输入，期望该行返回 Issue 且不形成候选（原因码 INVALID_EVENT）」 |
| 16 | C8 | `bc-C8-1` | 同日抢占 | `CallbackCaseInput`：`day` 固定取 `2026-01-05`，`daily_cap + 1` 个 `ARRIVAL` 事件（`at` 依次为当日 09:00、10:00…，`strategy_id="S-101"`、`appointment=false`、`used=0`） | 「名额到 `daily_cap` 用尽，超出部分期望被抑制（CAP_REACHED）」 |
| 17 | C8 | `bc-C8-2` | 频次用尽（回拨） | 同上但 `used = daily_cap` | 「本轮前已占满名额，期望全部抑制并保留已用值（CAP_REACHED）」 |
| 18 | C8 | `bc-C8-3` | 先已预约组 | `priority == "APPOINTMENT_FIRST"` 时生成：1 个 `appointment=true` 事件（`at` 较晚）＋ `daily_cap` 个 `appointment=false` 事件（`at` 较早） | 「期望先处理已预约组，再按各组 at、seq（winner_ids 保留分配顺序）」 |

- `verification` 里出现的**原因码字面量全部取自 `RULES.md`「满额赠券」段的固定清单**
  （`ISSUED`、`OUTSIDE_ACTIVITY`、`NOT_NEW`、`BELOW_THRESHOLD`、`STACK_DENIED`、`CUSTOMER_LIMIT`、
  `BUDGET_EXHAUSTED`、`DUPLICATE_EVENT`、`DUPLICATE_ORDER`、`REFUND_RECORDED`、`REVOKED`、
  `USED_COUPON_REVIEW`、`REDEEMED`、`INVALID_EVENT`）与「远程回拨」段的 `CAP_REACHED`；
  它们是**文案里的期望行为描述**，不是本卡计算出的判定，也**不得**被提升为 `Problem.code`（20 码冻结面）。
- `input` 必须能通过契约校验（`CouponCaseInput.events.minItems=1`、`seq >= 1`、`amount_fen >= 0` 等，
  真值来源 `operations.checkRule.schemas.*`）⇒ S5 必须有一条用例把**每个**生成的 `input` 拿去
  `model_validate` 一遍（「生成的反例自身不合法」是这类框架最典型的假绿）。
- **本卡与 M2-02 的边界（冻结）**：`BoundaryCase` 契约形状实测**只有** `id`/`label`/`input`/`verification` 四字段、
  **没有** `expected`/`actual`/`verdict`/`outcome`（真值来源
  `operations.checkRule.schemas.RuleCheck.properties.boundary_cases.items.properties`）⇒ 契约本身就不允许
  `checkRule` 返回数值判定。故 AC-004 的「反例覆盖 ±1 分、起止端点、重复、互斥、退款」在本卡落在
  **框架级**（反例数据 + 待验证行为 + 五类检查项各能跑出结论），**判定级**（真的跑一遍引擎、比对 Outcome）
  归 M2-02（任务卡 gates 已注明、U-1 已上报）。本卡**禁**在 `domain/activity/**` 里实现任何
  订单／账本／券状态的推进逻辑（任务卡「禁止」行：不得在 domain 层做金额分回放）。

### 5.5 AC-004 五类 ↔ 检查项对应（供 S7 的 `ac.md` 直接引用）

| AC-004 原文分类 | `CheckCategory` | `CheckId` | 可跑出的结论（示例触发） |
|---|---|---|---|
| 规则门槛 | `THRESHOLD` | `C2` | `REWARD_EXCEEDS_THRESHOLD` / `THRESHOLD_ZERO` / `PAYMENT_CLAUSE_UNCONFIRMED` + 反例 1、2 |
| 预算 | `BUDGET` | `C3` | `BUDGET_ZERO` / `BUDGET_BELOW_COUPON` / `QUOTA_EXCEEDS_BUDGET` + 反例 8、9、10 |
| 叠加 | `STACKING` | `C4` | `STACKING_CLAUSE_UNCONFIRMED` / `STACKING_ALLOW` + 反例 6、7 |
| 日期 | `DATE` | `C1`,`C7` | `WINDOW_ORDER_INVALID` / `TIME_WINDOW_CLAUSE_UNCONFIRMED` / `NEW_CUSTOMER_*` + 反例 3、4、13、14、15 |
| 退款口径 | `REFUND` | `C5` | `REFUND_CLAUSE_UNCONFIRMED` / `REFUND_RECOMPUTE` + 反例 11、12 |
| （附）重复与事件顺序 | `SEQUENCE` | `C8` | `*_CLAUSE_UNCONFIRMED` / `PRIORITY_APPOINTMENT_FIRST` + 反例 5、16、17、18 |
| （附）候选同模板 | `TEMPLATE` | `C6` | `TEMPLATE_UNKNOWN` / `TEMPLATE_CONST_MISMATCH`（+ `compareRules` 的 422 `VALIDATION_ERROR`，其 `issues[0].code="TEMPLATE_MISMATCH"`） |
| （附）竞争 | `COMPETITION` | `C9` | `RULE_OVERLAP_REVIEW` |

## 6. ETag 与 409 / 412 / 428 边界

### 6.1 ETag 出现面（逐 op 以切片 `operation.responses.<2xx>.headers` 实取为准，禁发明）

| op | 2xx | `ETag` | `X-Request-Id` | `Idempotency-Key` | `If-Match` |
|---|---|---|---|---|---|
| `listActivities` | 200 | **无** | 有 | 无 | 无 |
| `createActivity` | 201 | 有 | 有 | **必填** | 无 |
| `getActivity` | 200 | 有 | 有 | 无 | 无 |
| `updateActivity` | 200 | 有 | 有 | **必填** | **必填** |
| `listRules` | 200 | **无** | 有 | 无 | 无 |
| `createRule` | 201 | 有 | 有 | **必填** | 无 |
| `getRule` | 200 | 有 | 有 | 无 | 无 |
| `updateRule` | 200 | 有 | 有 | **必填** | **必填** |
| `confirmRule` | 200 | 有 | 有 | **必填** | **必填** |
| `checkRule` | 200 | **无** | 有 | 无 | 无 |
| `compareRules` | 200 | **无** | 有 | 无 | 无 |

- `ETag` 值一律 `api/common.py::etag(revision)` → `"<十进制整数>"`（带双引号），与 `If-Match` 的契约正则
  `^"[1-9][0-9]*"$`（真值来源 `operations.updateActivity.operation.parameters[3].schema.pattern`，
  `updateRule` / `confirmRule` 逐字相同）对齐；`ETag` 头的契约长度上限 32
  （`…responses.201.headers.ETag.schema.maxLength`）。
- **列表与只读计算面不带 ETag**（`ActivityPage` / `RuleVersionPage` / `RuleCheck` / `RuleDiff` 四个 DTO 里也
  **没有** `revision` 之外的页面级版本字段）⇒ 禁给 200 的列表响应加 `ETag`（M0-02 对 `WorkspacePage` 的同一处置）。
- 幂等重放时 `ETag` **从信封取、禁重算**（`api/common.py::replay_from_envelope` docstring 与
  `REPLAYED_HEADERS = ("ETag", "Location")`；本卡无 `Location`，故只回放 `ETag`）。
- `confirmRule` 会同时改 `rule_versions.revision` 与 `activities.revision`（§3.2）⇒ 响应里的 `ETag` 是
  **规则版本**的新 revision（响应体是 `RuleVersion`），活动的新 ETag 由随后的 `getActivity` 取；
  禁把活动的 revision 混进本响应的 `ETag`。

### 6.2 428 / 412 的实现口径（含一个会让 428 永不可达的陷阱）

- 契约把 `If-Match` 声明为 `required: true`。**若**在 FastAPI 侧照抄成必填形参（`Header(alias="If-Match")`
  无默认值），缺头会在进入函数体之前被 Starlette 判成 `RequestValidationError` →
  `install_error_handlers` 翻成 **422 `VALIDATION_ERROR`**，契约要求的 **428 `PRECONDITION_REQUIRED`**
  （`operations.updateActivity.operation.responses.428`）就**永远不可达**，任务卡 gate
  `pytest -q tests/api/activities -k etag412` 与 AC-003「旧 ETag 拒绝」同时判红。
- **冻结做法**：形参声明为**可选**但保留长度与正则校验——
  `if_match: str | None = Header(None, alias="If-Match", min_length=3, max_length=32, pattern=IF_MATCH_PATTERN)`，
  其中 `IF_MATCH_PATTERN: Final = r'^"[1-9][0-9]*"$'`（**逐字**抄契约 pattern，禁自己写第二份正则）；
  然后把 `if_match` 原样交给 service，由 service 在读到当前行之后调
  `api/common.py::check_if_match(if_match, current_revision)`：`None` → 428 `PreconditionRequired`、
  不等于 `etag(current_revision)` → 412 `RevisionConflict`（detail 由该 helper 固定，**禁**在调用点另编）。
  于是三种输入三种结果：缺头 → 428；格式非法（如 `abc`、`"0"`、`0`）→ 422 `VALIDATION_ERROR`
  （形参级校验，`issues[0].location="/header/If-Match"`）；格式合法但不等 → 412。
- `check_if_match` 必须在**事务内、读到当前行之后**调用（`revision` 是当前值，不是客户端给的）；
  428 例外——缺头无需读行即可判，但为了保持「404 优先于 428」（§6.3）仍在读行之后判。
- 412 与 428 都**不写审计**（§7.3 只给业务性拒绝写 `DENIED`；协议性缺头属请求形状问题）。

### 6.3 判定顺序（五个写 op 统一流水线；顺序即代码顺序，禁调序）

1. **形参级校验**（FastAPI）：路径参数正则、`limit`/`q`/`status` 长度、`If-Match` 与 `Idempotency-Key` 形状
   → 违例 422 `VALIDATION_ERROR`（`_handle_validation_error` 既有面）。
2. **会话**：`require_session` → 401 `SESSION_EXPIRED`（同码同 detail，禁枚举）；`OriginHostGuard` 中间件 →
   403 `ORIGIN_DENIED`（更外层，先于路由）。
3. **`Idempotency-Key` 值校验**：`validate_idempotency_key` → 422，`issues[0].location="/header/Idempotency-Key"`。
4. **正文**：`read_body_within_limit` → 413 `INPUT_TOO_LARGE`；`parse_json_body` → Content-Type/JSON 语法
   400 `BAD_REQUEST`、DTO 校验（含未知字段）422 `VALIDATION_ERROR` + `validation_issues(exc)`。
5. **开事务（`BEGIN IMMEDIATE`）→ 读当前行**：不存在或属外工作区 → **404 `RESOURCE_NOT_FOUND`**
   （逐字相同响应，不回显 ID）。
6. **幂等重放**：`IdempotencyGuard.peek` 命中同摘要 → 回滚本次、`replay_from_envelope` 回放
   （**先幂等、后 If-Match**，`API.md`「先查幂等重放，再查 If-Match」）。同键异摘要 → 409 `IDEMPOTENCY_CONFLICT`。
7. **If-Match**：428 → 412（§6.2）。
8. **状态机**：`assert_*_transition_allowed` → 409 `STATE_CONFLICT`（§3）。
9. **业务门禁**：空 PATCH / 绑定区间 / 条款门禁 / 摘要匹配 → 422 或 409 `VERSION_MISMATCH`（§3.4、§4.2）。
10. **写 + 审计 + 幂等登记**（同事务）→ 提交；`IdempotencyGuard.record` 撞主键（并发同键）→ 回滚并按
    `_Replay` 口径回放（`application/workspace_service.py::_Replay` 的既有控制流，禁改成裸「先查后插」）。

### 6.4 409 / 422 家族逐码触发面（**只用 20 码注册表内的码**，码名以 `domain/errors.py::PROBLEM_CODES` 实取为准）

| HTTP | `Problem.code` | 触发面（M2-01） | 承载异常 | `issues[0]` 口径 |
|---|---|---|---|---|
| 409 | `IDEMPOTENCY_CONFLICT` | 同 `(workspace_id, actor_id, operationId, Idempotency-Key)` 命中不同 `request_digest` | `IdempotencyConflict` | 无 `issues`（detail 复用 `CONFLICT_DETAIL`，禁回显摘要） |
| 409 | `STATE_CONFLICT` | §3 的全部非法迁移（归档后改活动、试编辑已确认版本、重复确认、就地回退、父版本仍是草稿、活动归档后建/改/确认规则）；**同银行外部活动号重复**（见下） | `StateConflict` | `code` 用 §3 的细因标签，`location` 见各条 |
| 409 | `VERSION_MISMATCH` | `confirmRule` 的 `Confirmation.digest` ≠ 当前 `rule_digest` | `DomainError(code="VERSION_MISMATCH")`（无专属类） | `location="/digest"`、`code="CONFIRMATION_DIGEST_MISMATCH"` |
| 412 | `REVISION_CONFLICT` | `If-Match` ≠ `etag(当前 revision)`（三个 op） | `RevisionConflict` | detail 由 `check_if_match` 固定 |
| 428 | `PRECONDITION_REQUIRED` | 三个 op 缺 `If-Match` | `PreconditionRequired` | 同上 |
| 422 | `VALIDATION_ERROR` | DTO 校验失败（含未知字段）、空 PATCH、`If-Match`/`Idempotency-Key` 形状非法、`limit` 越界、`q`/`status` 超长、`status` 含未知态名或空 token、绑定区间非法/重复/相交、`compareRules` 跨模板 | `ValidationFailure` 或 `DomainError(code="VALIDATION_ERROR")` | `location` 为 JSON Pointer（`/query/status`、`/header/If-Match`、`/bindings/0/valid_until`、`/content/…`） |
| 422 | `EVIDENCE_REQUIRED` | 条款门禁 G1–G6、警告缺备注、绑定 `evidence_id` 未登记 | `DomainError(code="EVIDENCE_REQUIRED")`（无专属类） | 逐条给出（§4.3 的表），多条时全部返回 |
| 413 | `INPUT_TOO_LARGE` | 五个写 op 的正文超 `AppConfig.max_json_body_bytes` | `InputTooLarge` | 无 |
| 400 | `BAD_REQUEST` | Content-Type 非 `application/json`、正文非合法 JSON | `DomainError(code="BAD_REQUEST")` | 无 |
| 400 | `BAD_CURSOR` | `listActivities` / `listRules` 的游标解不开、HMAC 不符、查询摘要不符、换 actor | `DomainError(code="BAD_CURSOR")` | 无（detail 复用 `BAD_CURSOR_DETAIL`，同一句） |
| 404 | `RESOURCE_NOT_FOUND` | 活动/规则/父版本不存在或属外工作区；`compareRules` 的 `candidate_rule_id` 不存在或属外工作区 | `ResourceNotFound` | 无（禁回显 ID、禁区分原因） |
| 401 / 403 | `SESSION_EXPIRED` / `ORIGIN_DENIED` / `ACCESS_DENIED` | 会话失效／回环守卫／`audit_role_of(actor)` 遇到空 `allowed_roles` | `SessionInvalid` / `OriginDenied` / `AccessDenied` | 无 |
| 500 | `INTERNAL_ERROR` | 未捕获异常、`digest` 列与现算摘要不符、`issues`/`boundary_cases` 超契约上限 | `InternalFailure` / `ArtifactCommitFailed`（本卡不产制品，故不涉及） | detail 只含 request_id |

**同银行外部活动号重复（AC-002「同银行外部活动号重复明确定位」）冻结口径**：

- 物理来源＝切片 `ddl.activities` 的 `UNIQUE(workspace_id,bank_id,external_activity_id)`。
- 判定＝`createActivity` 在事务内先 `SELECT 1 FROM activities WHERE workspace_id=? AND bank_id=? AND
  external_activity_id=?`（仅当**两者都非空**时才查），命中 → **409 `STATE_CONFLICT`**，
  `detail` 固定「同一银行下外部活动号已存在」，`issues` **两条**：
  `{code:"DUPLICATE_EXTERNAL_ACTIVITY", location:"/bank_id", message:"银行 <bank_id>", severity:"ERROR"}` 与
  `{code:"DUPLICATE_EXTERNAL_ACTIVITY", location:"/external_activity_id", message:"外部活动号 <external_activity_id> 已用于活动 <既有 activity_id>", severity:"ERROR"}`
  —— 「明确定位」= 同时给出**冲突字段**与**既有活动 ID**（AC-002 的通过条件原文）。
  这**不是**回显探针：`bank_id` + `external_activity_id` 都是客户端自己刚提交的值，
  既有活动 ID 属于同一工作区（已过 404 隔离），与「404 不回显 ID」的禁枚举口径不冲突。
- 竞态兜底：`SELECT` 未命中但 `INSERT` 撞 `IntegrityError`（并发同键）→ **同样**翻成 409
  `STATE_CONFLICT` + 上述两条 `issues`（禁让 `IntegrityError` 冒成 500）。
- **SQLite NULL 语义陷阱（S5 必须钉）**：`UNIQUE` 索引里 NULL 互不相等 ⇒ `bank_id` 或
  `external_activity_id` 任一为 `NULL` 的活动**永不**触发该冲突（可以重复建多条 `bank_id=null` 的活动）。
  这是契约与 DDL 的既有事实，**禁**在领域侧额外加「两者皆空也要唯一」的规则（那会超出契约）。
- `updateActivity` **不可能**触发本冲突：`ActivityUpdate` 没有 `bank_id` / `external_activity_id` 字段
  （真值来源 `operations.updateActivity.schemas.ActivityUpdate.properties`）。

**空 PATCH（`API.md`「更新」行原文「空 PATCH 422」）冻结口径**：`ActivityUpdate` / `RuleUpdate` 的
`required` 都是空数组 ⇒ `{}` 能通过 Schema。service 必须用 `payload.model_dump(exclude_unset=True)`
（**不是** `exclude_none`）判空：为空 → 422 `VALIDATION_ERROR`、`issues[0].location="/"`、
`issues[0].code="EMPTY_PATCH"`、detail 固定「PATCH 正文至少给出一个字段」。
用 `exclude_unset` 而非 `exclude_none` 的理由：`ActivityUpdate.description` 允许 `""`、
`RuleUpdate.terms` 允许 `[]`，客户端**显式**给空值是合法的「清空」意图，不能与「没给」混为一谈；
`bindings` 的出现与否更是直接决定「整体替换 vs 完全不动」（§3.4）。

### 6.5 「409 的 `diff` 字段」口径（派单文措辞与契约不符，本文按契约冻结；见 §12 U-7）

活契约 `components.schemas.Problem` 实测**只有 7 个属性**（`type`/`title`/`status`/`code`/`detail`/
`request_id`/`issues`，全部必填）且 **`additionalProperties: false`** ⇒ 409 的响应体里**不存在**、
也**不允许**出现 `diff` 字段；全契约带 `diff` 字样的 Schema 只有 `RuleDiff`（`compareRules` 的 200 体）。
故本文把「409 的 diff 断言口径」拆成两处**都存在**的口径，S6 分别钉：

1. **409 侧的「差异/定位」= `Problem.issues[]`**：`issues[].location` 给字段级 JSON Pointer、
   `issues[].code` 给细因标签、`issues[].message` 给可读值（§6.4 的逐码口径）。
   断言口径＝「同银行外部活动号重复的 409 必须带**两条** `issues`，`location` 分别是 `/bank_id` 与
   `/external_activity_id`，`code` 同为 `DUPLICATE_EXTERNAL_ACTIVITY`，且 `message` 含既有活动 ID」。
2. **`compareRules` 侧的「差异字段」= `RuleDiff.changes[].path`**（AC-003「显示差异字段、条款来源和摘要」）。
   冻结 `path` 口径＝**指向规则版本业务投影的 JSON Pointer**，取值域：
   - `/label`（`before`/`after` = 两个 label 原文）；
   - `/source_rule_version`（`null` 侧渲染为 JSON `null`，即 `FieldChange.before/after = None`）；
   - `/content/<字段名>`（如 `/content/min_payment_fen`；`before`/`after` 为**字符串化**取值：
     整数用十进制串、布尔用 `"true"`/`"false"`、时刻用 `model_dump(mode="json")` 的 ISO 串——
     因为 `FieldChange.before/after` 契约类型是 `string|null`（0–1000），**不是**任意 JSON）；
   - `/terms/<key>/<字段名>`（如 `/terms/refund/status`、`/terms/refund/decision`；用**键名**而非数组下标，
     理由同 §5.3 末条：条款身份是 `key`，下标会随客户端顺序漂移）；
   - 条款整条新增/删除 → `path="/terms/<key>"`，`before`/`after` 一侧为 `null`，另一侧为
     `canonical_json(term.model_dump(mode="json"))`（≤1000 字符；实测单条条款的规范化 JSON 远小于该上限，
     超限时截断会破坏可复查性 ⇒ 组装前 `assert len(...) <= 1000`，超限 → 500 `INTERNAL_ERROR`）。
   `changes` 的排序＝先 `/label`、再 `/content/*` 按字段名字典序、再 `/source_rule_version`、
   最后 `/terms/*` 按 `key` 字典序（稳定、可复跑，S6 直接断言整个数组）。
   **只比较参与摘要的投影 + `label`**（§4.6）：`id`/`revision`/`created_at`/`confirmed_at`/`confirmation`/
   `state`/`activity_id`/`parent_rule_id` **不进** `changes`（它们不是「候选字段变化」，
   `RULES.md`「候选字段变化可在草稿中比较」）。
   `RuleDiff.requires_rerun_case_ids` = 同工作区中 `cases.state='CONFIRMED'` 且
   `cases.observed_rule_id IN (baseline_rule_id, candidate_rule_id)` 的 `cases.id`，升序去重；
   `changes` 为空 ⇒ 直接返回 `[]`（无字段变化即无需重跑）。**只读** `cases`，
   基于 `candidates` 的 STALE 标记归 M2-02（`RULES.md`「对照与验收」第 4 条），本卡不碰。

### 6.6 声明为**不可达**的注册表码（S5/S6 断言其不可达本身，禁写会红的用例、禁 `skip`/`xfail`）

`STALE_CANDIDATE`（候选面，M2-02）· `SNAPSHOT_CONFLICT`（快照面，M1-02）· `ACTION_REVIEW_REQUIRED`（改进项面，M4-02）·
`JOB_CAPACITY`（作业面，M0-04；本卡 11 个 op 全是同步有界计算，`API.md`「同步计算接口只处理有界输入」）·
`INVALID_SCOPE`（本卡的筛选非法值一律走 422 `VALIDATION_ERROR`，与 N7① 已裁定的 `listJobs.status` 口径一致，
故 `INVALID_SCOPE` 无触发面）。这 5 个码**仍在** `declared_responses()` 声明的 422/409/429 形里
（因为切片对 11 个 op 都声明了 11 个 Problem 形），「声明了但不可达」是契约面的既有事实，
与 M0-02 的处置一致（`tests/api/test_contract_declarations.py` docstring：不可达分支**断言不可达本身**）。

## 7. 事务边界与持久化

### 7.1 事务号与边界（体例＝`worker/store.py` 的「一方法一短事务」＋ `application/workspace_service.py` 的连接口径）

| 事务 | 落点方法 | 内容（同一 `BEGIN IMMEDIATE` 内） |
|---|---|---|
| `TX-A1` | `ActivityService.create_activity` | 查重（§6.4）→ `INSERT activities` → `INSERT activity_bindings`（若 `ActivityCreate` 无 `bindings` 字段则为空；**注意**：`ActivityCreate` 实测**没有** `bindings` ⇒ 新建活动必然零绑定，AC-002 的绑定由随后的 `updateActivity` 落）→ `INSERT audit` → `INSERT idempotency` |
| `TX-A2` | `ActivityService.update_activity` | 读行（404）→ 幂等（回放/409）→ `check_if_match`（428/412）→ 迁移判定（409）→ 绑定校验（422）→ `UPDATE activities`（谓词带 `status='OPEN' AND revision=:revision`）→ `DELETE`+`INSERT activity_bindings`（仅当 `bindings` 出现）→ `INSERT audit` → `INSERT idempotency` |
| `TX-R1` | `RuleService.create_rule` | 读活动行（404 / 归档 409）→ 读父版本（R4：404 / 非 CONFIRMED 409）→ 幂等 → `INSERT rule_versions`（`state='DRAFT'`,`revision=1`,`digest`=§4.6）→ `INSERT audit` → `INSERT idempotency` |
| `TX-R2` | `RuleService.update_rule` | 读行 → 幂等 → `check_if_match` → 迁移判定（409）→ 空 PATCH（422）→ 重算 `digest` → `UPDATE rule_versions`（谓词 `state='DRAFT' AND revision=:revision`）→ `INSERT audit`（label 与 content/terms 分别一行，§7.3）→ `INSERT idempotency` |
| `TX-R3` | `RuleService.confirm_rule` | 读行 → 幂等 → `check_if_match` → 迁移判定（409）→ `schema_version`（422）→ 摘要匹配（409）→ 条款门禁（422）→ 警告备注（422）→ `UPDATE rule_versions`（谓词 `state='DRAFT' AND revision=:revision AND digest=:digest`）→ `UPDATE activities SET current_rule_id, revision+1` → `INSERT audit` → `INSERT idempotency` |
| `TX-READ` | 各 `get_*` / `list_*` / `check_rule` / `compare_rules` | **只读**，`connect()` 单连接、不开显式事务（与 `WorkspaceService.list_workspaces` 同口径） |

- 连接口径照既有实现：每个事务一条新连接、短时持有、不跨线程、`AUTOCOMMIT` 隔离级 +
  显式 `BEGIN IMMEDIATE`（`worker/store.py` docstring「连接口径照 design §4」）；
  库路径**不在**本卡任何文件出现（单点在 `infra/db/paths.py`，ADR-005 §2.4）。
- 写事务一律 `BEGIN IMMEDIATE`：`updateActivity` 的「DELETE+INSERT 绑定集合」与 `confirmRule` 的
  「双表 UPDATE」都需要写锁前置，否则并发下会出现「两个请求都读到 `revision=N`」的丢失更新。
- 任何被拒的写请求**不留半成品**：业务写入与审计在同一事务，异常即整体回滚
  （AC-002「无绑定活动在关联视图可见」与「不留半成品」的可复查性都依赖这条）。

### 7.2 SQL 写点唯一（A81 口径）

`activities` / `activity_bindings` / `rule_versions` 三表的 **DML 文本只允许出现在
`infra/db/repositories.py`**（A82 的「纯追加」体例：对既有文件 0 删除行），
新增 `ActivityRepository` / `ActivityBindingRepository` / `RuleVersionRepository` 三个类；
service 层（§11 的 `application/activity_service.py`）只负责事务开关、`rowcount` → 领域错翻译、审计与幂等
（`worker/store.py` docstring 点名的「仓储层刻意只回 `int`，把零行意味着什么留给知道上下文的本层判断」）。
`receipts` / `cases` / `evidence` 三表**只读**，读语句同样落 `repositories.py`（`ReceiptIdRepository` 等），
禁在 service 里拼 SQL（`framework/PYTHON.md` 第 5 行）。

### 7.3 审计（`audit` 表；`application/audit.py::AuditWriter` 只 import、禁改）

- `ACTION_*` 常量**定义在本卡新增的 service 模块里**（`AuditWriter.write(action=…)` 收 `str`，
  故无需改 `application/audit.py` —— 该文件不在 `scope_allow`）：
  `ACTIVITY_CREATED`（A1）· `ACTIVITY_UPDATED`（A3）· `ACTIVITY_ARCHIVED`（A2）·
  `RULE_DRAFT_CREATED`（R1）· `RULE_SUCCESSOR_DRAFT_CREATED`（R4）· `RULE_CONTENT_UPDATED`（R2 的 content/terms 变化）·
  `RULE_LABEL_UPDATED`（R2 的 label 变化）· `RULE_CONFIRMED`（R3）。
  命名体例对齐既有 `ACTION_WORKSPACE_CREATED` 与 M0-04 的 `JOB_CANCEL_REQUESTED` / `JOB_CANCELLED` / `JOB_RETRIED`。
- **`DOMAIN.md`「规则标签和确认说明分别审计」的落地**：`updateRule` 同时改 `label` 与 `content`/`terms` 时，
  同事务写**两行**审计（`RULE_LABEL_UPDATED` + `RULE_CONTENT_UPDATED`）；只改其一时写一行；
  `confirmRule` 的确认说明由 `RULE_CONFIRMED` 这一行独立承载（`confirmation` 不进摘要，§4.6）。
- `target_kind` 取 `"activity"` / `"rule"`（两者都在 `api/common.py::ObjectKind` 的 Literal 里，实测含
  `activity` 与 `rule`）；`target_id` = 活动 ID / 规则版本 ID；`role` = `audit_role_of(actor)`（复用既有实现，
  优先 `OPERATOR`，否则取契约枚举序第一个）；`request_id` = 本次 `X-Request-Id`。
- `outcome`：提交成功的业务写入 → `ACCEPTED`；**业务性拒绝**（409 `STATE_CONFLICT` 的「试编辑已确认版本」、
  「归档后修改」、409 `VERSION_MISMATCH`、422 `EVIDENCE_REQUIRED` 的门禁不通过）→ 追加一行 `DENIED`，
  写在**业务事务回滚之后**的独立短事务里（AC-003 的主证据含「审计」，「确认并试编辑」被拒这件事必须留痕；
  体例＝M0-04 对被拒取消/重试写 `DENIED` 的裁定）。协议性拒绝（401/403/404/412/413/422 形状校验/428）
  **不写**审计（无业务判断可留痕，且 404 写审计会把「不存在」与「属外工作区」的差异带进审计链）。
  `FAILED` 本卡不使用（无异步作业面）。
- 审计链：`sequence` 与 `previous_digest` 必须在**同一事务内**取（`AuditWriter.write` 已经这么做，
  事务外取必撞 PK —— M0-04 design §2 点名的已知失败模式）。

### 7.4 只读跨表查询（`Activity` 的三个数组字段与 `RuleDiff.requires_rerun_case_ids`）

- `Activity.bindings` ← `activity_bindings`；`Activity.rule_ids` ← `rule_versions.id`；
  `Activity.receipt_ids` ← `receipts.id`（M2-03 的写面，本卡只读，未落地时天然为空数组）。
- **数组顺序（冻结，禁各处不一）**：`bindings` 按 `valid_from ASC, strategy_id ASC, source_version ASC`；
  `rule_ids` 与 `receipt_ids` 按 `created_at ASC, id ASC`（`DOMAIN.md`「读取顺序稳定，以 `created_at`、`id` 做游标」
  的稳定序，升序＝业务时间线顺序，便于前端直接展示版本演进）。
- **禁 N+1**：`listActivities` 一页最多 100 个活动 ⇒ 三张从表各**一次**批量查询
  （`WHERE workspace_id=:ws AND activity_id IN (:…)`，参数按页内 ID 列表展开），在 Python 侧分组回填。
  单对象 `getActivity` 走同样的三个方法（页大小 1），禁为单对象另写第二套查询。
- `receipts` / `cases` 表当前**可能整表为空**（M2-03 / M2-02 未落地）⇒ 查询必须容忍空结果并返回 `[]`，
  禁假设「至少一行」；表存在性由 `contracts/sqlite-v1.sql`（迁移头）保证，本卡**不建表、不改迁移**
  （`migrations/**` 在 `scope_deny`）。

### 7.5 显式时钟、ID 前缀与幂等键

- 时间一律由调用方从 `Clock` 传入（`api/deps.py::get_clock` → service 构造参数），
  `created_at` / `confirmed_at` / `audit.at` 全取 `clock.now()`；`domain/activity/**` 内**禁**出现
  `datetime.now()` / `time.time()` / `utcnow()`（任务卡「禁止」行＋`framework/PYTHON.md`）。
  落库文本用 `infra/db/repositories.py::_iso`（既有实现，UTC 归一，禁第二份格式化）。
- ID 前缀：活动 `new_resource_id("act")`、规则版本 `new_resource_id("rul")`（`domain/ids.py` 的既有生成器，
  形态 `<prefix>-<uuid4 hex>`，实测长度落在 ID 正则的 1–96 内）；审计 ID 由 `AuditWriter` 自持（`aud`）。
  **禁**把 fixture 里的 `AC-101` / `S-101` 当本地 ID（`DOMAIN.md`「外部活动、规则版本和切片号单独保存」：
  `AC-101` 是 `external_activity_id`，`S-101` 是 `Binding.strategy_id`，本地 `id` 由服务端生成）。
- 幂等键四元组：`IdempotencyKey(scope_key=<workspace_id>, actor_id=<actor.actor_id>,
  operation=<operationId 字面量>, idem_key=<校验后的键>)`（`API.md`「作用域、用户、operationId、键组合唯一」；
  工作区级作用域，**不是** `GLOBAL_SCOPE` —— 后者只属 `createWorkspace`）。
  `request_digest = api/common.py::request_digest(path=<API_PREFIX + 具体路径（含真实 ID）>, query={}, body=<原始字节>, files=())`；
  路由必须把**原始字节**交给 service（`application/workspace_service.py::create_workspace` docstring 的既有裁定：
  用重新序列化的 DTO 代替原字节会让「同键同体」在字段顺序不同时算出不同摘要）。
  `If-Match` **不进**摘要（`API.md` 列举的摘要成分只有「规范化路径、查询、正文和上传文件摘要」）；
  由于「先幂等、后 If-Match」，同键同体的重放会回放**原**结果而不再判 412 —— 这是 `API.md` 的明文顺序，
  S6 必须把它钉成用例（同键同体重放 + 故意给错的 `If-Match` 仍回放 200/201）。
- 只登记 2xx（`application/idempotency.py` docstring 的既有口径）⇒ 4xx/5xx 不写 `idempotency` 行，
  客户端重试会重新求值；被拒的确认（422 门禁）因此**可以**在补全条款后用同一个键重试。

## 8. 逐 op 的可达码矩阵（声明面一律 `declared_responses(<2xx>)` 的 12 个码；本表只标**可达**面）

| op | 可达（触发面见 §6.4） | 声明但**不可达**（S5/S6 断言不可达本身） |
|---|---|---|
| `listActivities` | 400 `BAD_CURSOR`·401·403 `ORIGIN_DENIED`/`ACCESS_DENIED`·404（工作区不存在/属外）·422 `VALIDATION_ERROR`（`limit`/`q`/`status` 形状与未知态名）·500 | 409 全部 6 码·412·413·428·429·`INVALID_SCOPE`·`EVIDENCE_REQUIRED` |
| `createActivity` | 400 `BAD_REQUEST`·401·403·404（工作区不存在）·409 `IDEMPOTENCY_CONFLICT`/`STATE_CONFLICT`（外部活动号重复）·413·422（DTO/幂等键形状）·500 | 400 `BAD_CURSOR`·`VERSION_MISMATCH`·`STALE_CANDIDATE`·`SNAPSHOT_CONFLICT`·`ACTION_REVIEW_REQUIRED`·412·428·429·`INVALID_SCOPE`·`EVIDENCE_REQUIRED` |
| `getActivity` | 401·403·404·500 | 400 两码·409 全部·412·413·422·428·429 |
| `updateActivity` | 400 `BAD_REQUEST`·401·403·404·409 `IDEMPOTENCY_CONFLICT`/`STATE_CONFLICT`（归档后修改）·412·413·422（DTO/空 PATCH/`If-Match` 形状/绑定区间与证据）·428·500·422 `EVIDENCE_REQUIRED`（`evidence_id` 未登记） | 400 `BAD_CURSOR`·`VERSION_MISMATCH`·`STALE_CANDIDATE`·`SNAPSHOT_CONFLICT`·`ACTION_REVIEW_REQUIRED`·429·`INVALID_SCOPE` |
| `listRules` | 400 `BAD_CURSOR`·401·403·404（工作区或活动不存在/属外）·422·500 | 409·412·413·428·429·`INVALID_SCOPE`·`EVIDENCE_REQUIRED` |
| `createRule` | 400 `BAD_REQUEST`·401·403·404（活动/父版本不存在或属外）·409 `IDEMPOTENCY_CONFLICT`/`STATE_CONFLICT`（活动归档、父版本仍是草稿）·413·422·500 | 400 `BAD_CURSOR`·`VERSION_MISMATCH`·412·428·429·`INVALID_SCOPE`·`EVIDENCE_REQUIRED` |
| `getRule` | 401·403·404·500 | 400·409·412·413·422·428·429 |
| `updateRule` | 400 `BAD_REQUEST`·401·403·404·409 `IDEMPOTENCY_CONFLICT`/`STATE_CONFLICT`（试编辑已确认版本、活动归档）·412·413·422（DTO/空 PATCH/形状）·428·500 | 400 `BAD_CURSOR`·`VERSION_MISMATCH`·429·`INVALID_SCOPE`·`EVIDENCE_REQUIRED` |
| `confirmRule` | 400 `BAD_REQUEST`·401·403·404·409 `IDEMPOTENCY_CONFLICT`/`STATE_CONFLICT`（重复确认、活动归档）/`VERSION_MISMATCH`（摘要不符）·412·413·422 `VALIDATION_ERROR`（形状/`schema_version`）·422 `EVIDENCE_REQUIRED`（条款门禁 G1–G6、警告缺备注）·428·500 | 400 `BAD_CURSOR`·`STALE_CANDIDATE`·`SNAPSHOT_CONFLICT`·`ACTION_REVIEW_REQUIRED`·429·`INVALID_SCOPE` |
| `checkRule` | 401·403·404·500（`digest` 列与现算不符、`issues`/`boundary_cases` 超上限） | 400·409·412·413·422·428·429 |
| `compareRules` | 401·403·404（任一侧不存在/属外）·422 `VALIDATION_ERROR`（跨模板，`issues[0].code="TEMPLATE_MISMATCH"`；`candidate_rule_id` 形状）·500 | 400·409·412·413·428·429·`INVALID_SCOPE`·`EVIDENCE_REQUIRED` |

> 本表**不是**第二份状态码清单：期望值一律由「路由装饰器 `declared_responses()` 的实现侧」与
> 「切片 `operations.<opId>.operation.responses` 的声明侧」对撞得出（A95），错误码一律由
> `domain/errors.py::PROBLEM_CODES` 反查（禁自造码）。本表只承载「哪些码在本卡有触发面」这一设计判断，
> 供 S5/S6 枚举用例、供 Q 判定档复核「声明了但不可达」的断言是否齐全。

## 9. 边界清单（AC → 实现约束 → 已知失败模式）

- **AC-002**（`qa/ACCEPTANCE.md` 第 10 行；切片 `acceptance_rows.AC-002` 逐字同源）：
  「建两活动，给 AC-101 绑定 S-101 与有效期，AC-202 保持无绑定」→「关联复盘显示预约任务，AC-202 显示缺绑定。
  同银行外部活动号重复明确定位」〔主证据：API 和页面〕。
  **实现约束**：① 两次 `createActivity` 用**不同**的 `Idempotency-Key`（同键同体会回放同一个活动）；
  ② `AC-101` 落 `external_activity_id`、`bank_id="A"`（fixture `api-examples.json` 的 `createActivity` 样本逐字），
  `S-101` 落 `Binding.strategy_id`、有效期 `valid_from="2026-01-01"` / `valid_until="2026-12-01"`（同 fixture 的
  `updateActivity` 样本），`evidence_id` 必须先播种 `artifacts`+`evidence` 两行（§3.4）；
  ③ `AC-202` 不发 `bindings` ⇒ `getActivity` 的 `bindings` 必须是 `[]`（不是缺字段、不是 `null`：
  契约 `Activity.bindings` 是必填数组，`minItems=0`）；④ 重复的外部活动号 → 409 + 两条 `issues`（§6.4）；
  ⑤ 「关联复盘显示预约任务」与「页面」侧 **deferred_to M3-01 / M3-04**（任务卡 gates 已固化，B9 裁定不需要 CR），
  本卡**不出**任何视图接口、**不碰** `web/**`。
  **已知失败模式**：把 `AC-101` 当本地 `id`（应为 `external_activity_id`）；`bindings` 用 merge 语义导致
  「保持无绑定」的活动被误加绑定；`valid_until == valid_from` 撞 DDL CHECK 冒成 500；
  `evidence_id` 未播种导致 FK 失败冒成 500；409 只回 `detail` 不给 `issues` ⇒「明确定位」不成立；
  用 `bank_id=null` 复现重复冲突（SQLite NULL 互不相等，永不触发）。
- **AC-003**（`ACCEPTANCE.md` 第 11 行）：「保存规则草稿，比较两个版本，确认并试编辑」→「显示差异字段、
  条款来源和摘要。确认版不可变，变更通过草稿。旧 ETag 拒绝」〔主证据：API、审计〕。
  **实现约束**：① `createRule` → 201 `state="DRAFT"`、`revision=1`、`digest` 为 §4.6 投影、`ETag="\"1\""`；
  ② `compareRules?candidate_rule_id=<R4 派生的新草稿>` → `changes` 含 `/content/refund_policy`
  （fixture `rules.json` 的 `CP-V1` 与 `CP-V2` **实测只差 `refund_policy`** 一个字段，是天然的 diff 样本）；
  ③ 「条款来源」= `Term.evidence_id` + `clause`（`RULES.md`「自由条款作为来源」），必须原样出现在
  `getRule` 的 `terms[]` 里；「摘要」= `RuleVersion.digest`；
  ④ `confirmRule` → 200 `state="CONFIRMED"`、`confirmed_at`/`confirmation` 同时非空、`revision+1`、
  同事务把 `activities.current_rule_id` 指向它并 `activities.revision+1`；
  ⑤ 「试编辑」= 对已确认版本 `updateRule` → **409 `STATE_CONFLICT`** + `issues[0].code="RULE_CONFIRMED_IMMUTABLE"`，
  且 DB 行**逐字节不变**（含 `revision`）；「变更通过草稿」= `createRule` 带 `parent_rule_id` → 201 新 `DRAFT`
  行、父行不变（R4 `creates_new_row=True`）；
  ⑥ 「旧 ETag 拒绝」= 拿确认前的 `ETag` 去 `updateRule`/`confirmRule` → **412**；缺 `If-Match` → **428**
  （任务卡 gate `-k etag412` 点名的三个 If-Match 端点：`updateActivity`、`updateRule`、`confirmRule`，
  M0-02 裁定 Q3 `RULING_NARROW_GATE_DEFER_HTTP` 的承接方就是本卡）；
  ⑦ 审计：草稿保存 / 确认 / 试编辑被拒（`DENIED`）三类事件都要有行（§7.3），主证据「审计」才成立。
  **已知失败模式**：只改 `label` 也重算 `digest`（应不变，§4.6）；`confirmRule` 忘了联动
  `current_rule_id`（AC-003 的「候选规则」语义丢失）；把 `If-Match` 声明成必填形参导致 428 变 422（§6.2）；
  幂等重放时重算 `ETag`（必须回放信封里的原值）；对已确认版本的 UPDATE 谓词漏掉 `state='DRAFT'`
  ⇒ 「不可变」只剩领域层一道、并发下被穿透；用 `revision` 当摘要（两个面不可互换）。
- **AC-004**（`ACCEPTANCE.md` 第 12 行）：「规则门槛、预算、叠加、日期和退款口径分别检查」→「反例覆盖 ±1 分、
  起止端点、重复、互斥、退款。必填条款未确认时无法确认」〔主证据：规则检查、页面〕。
  **实现约束**：① 五类检查项各由 §5.3 的 `CheckId` 承载，且**每类至少有一个可触发的 ERROR 或 WARNING**
  （守护必须有牙：只交「全 READY」无法区分框架有效与恒绿）；② `checkRule` 对「必需条款未确认」的草稿
  必须返回 `state="NEEDS_CONFIRMATION"` 且 `issues` 里能定位到具体键（`/terms/<key>`）；
  ③ 同一草稿直接 `confirmRule` → **422 `EVIDENCE_REQUIRED`**，`issues` 覆盖全部不合格键（G1–G6）；
  ④ 反例覆盖 §5.4 的 18 条（±1 分 = `bc-C2-1`/`bc-C2-2`，起止端点 = `bc-C1-1`/`bc-C1-2`，
  重复 = `bc-C1-3`，互斥 = `bc-C4-1`，退款 = `bc-C5-1`/`bc-C5-2`），每条 `input` 自身必须过契约校验；
  ⑤ **数值判定与 ±1 分的回放比对归 M2-02**（任务卡 gates 与 U-1 已固化），本卡不实现引擎、
  `BoundaryCase` 也没有承载判定的字段（§5.4）；⑥ 「页面」侧归 M2-04（`contracts/pages.json` 的 UI-05），本卡不碰 `web/**`。
  **已知失败模式**：把 `RuleCheck.state` 与 `RuleVersion.state` 混用（§5.2 的命名陷阱）；
  反例生成读了 `clock.now()`（同一版本两次调用结果不同 ⇒ 不可复算）；`boundary_cases` 超 30 条被静默截断；
  `issues` 未按 `(code, location)` 去重导致同一事实刷满 1000 条上限；
  把 `WARNING` 也当成阻塞（会让「警告需备注」这条 AC 永远走不到）；
  在 `domain/activity/**` 里实现券/账本推进（越界到 M2-02，任务卡「禁止」行）。

## 10. 验证清单（命令 → 期望 rc；供 S5–S7 直接采集，**无「人工确认」项**；计数一律以 `state.json.counts` 现值为准，禁写死）

| # | 命令（均在 WSL 仓库根 `/home/szf/dev/CampaignLab`，`export PATH="$HOME/.local/bin:$PATH"`） | 期望 |
|---|---|---|
| V1 | `uv run --no-sync pytest -q tests/domain/activity -k immutable` | rc=0（任务卡 gate 原文） |
| V2 | `uv run --no-sync pytest -q tests/api/activities -k etag412` | rc=0（任务卡 gate 原文；含 428 与 412 两面） |
| V3 | `uv run --no-sync pytest -q tests/domain/activity -k clause_gate` | rc=0（任务卡 gate 原文） |
| V4 | `uv run --no-sync pytest -q tests/api/activities -k dup_external` | rc=0（任务卡 gate 原文） |
| V5 | `uv run --no-sync pytest -q tests/api/activities -k rule_diff` | rc=0（任务卡 gate 原文） |
| V6 | `uv run --no-sync pytest -q tests/domain/activity -k "boundary_case or check_framework"` | rc=0（§5 框架面：九项注册齐全、每类有牙、反例自身合法、两次调用逐字节相同） |
| V7 | `uv run --no-sync pytest -q tests/domain/activity -k "state_machine"` | rc=0（§3 迁移表：A1–A3 / R1–R4 逐条 + 全部非法迁移 → 409） |
| V8 | `uv run --no-sync pytest -q tests/api/activities -k "binding"` | rc=0（§3.4：起含止排、空区间、相交、重复键、`evidence_id` 未登记、整体替换 vs 不动） |
| V9 | `uv run --no-sync pytest -q tests/api/activities -k "current_rule"` | rc=0（§3.2：确认后活动 `current_rule_id` 与活动 `ETag` 同步变化） |
| V10 | `uv run --no-sync pytest -q tests/api/activities -k "list_filter"` | rc=0（§1.1/§1.5：`q` + `status` 多值过滤、游标绑定四项筛选、`BAD_CURSOR` 同一句 detail） |
| V11 | `uv run --no-sync pytest -q tests/api/activities` 与 `uv run --no-sync pytest -q tests/domain/activity` | 各自 rc=0 |
| V12 | `uv run --no-sync ruff check .` · `uv run --no-sync ruff format --check .` · `uv run --no-sync mypy` · `uv run --no-sync pytest -q` | 各自 rc=0（**以 rc 为判据**，分母现值见 `state.json.counts.ruff_lint_scope_files` / `.ruff_formatted_files` / `.mypy_source_files` / `.pytest_passed`，禁写死） |
| V13 | `uv run --no-sync python scripts/check_contracts.py check --validate` | rc=0（契约门禁未回归；登记项数以 `.counts.contract_registered_nodes` 为准） |
| V14 | `uv run --no-sync python -c "import hashlib,pathlib;d=pathlib.Path('contracts/openapi.json').read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))"` | rc=0 且与 `state.json -> resume.self_check_gates_rc0.counts.live_openapi_sha16` / `.live_openapi_bytes` 现值一致（切片新鲜度；不一致即回报 T lane 重切，**禁自行重切**） |
| V15 | 新增 `conftest.py` 或与既有文件同 basename 的新文件后，跑一次**全树** `uv run --no-sync mypy` | rc=0（LANE-COMMON §3.6 `rule_full_tree_mypy_on_basename_collision`：路径限定 mypy 不触发跨目录重复模块名检测；本卡 S5/S6 会新增 `tests/api/activities/conftest.py`，与既有 `tests/api/conftest.py` **同 basename**，故本条为强制项） |

> 正向对照要求（LANE-COMMON §6）：V1–V11 的每一组守护都必须由实现方**主动制造一次 RED**、
> 把原始输出落进 `evidence/M2/M2-01/gates/`、再复原并复验绿（复原用 sha256 双向核验，两个摘要都进证据）；
> 探针一律用 pytest 的 `tmp_path`，**禁落工作树**（否则污染 ruff/mypy 分母）。

## 11. 文件级 TODO（S2–S7 严格按此机械铺开；不得越出下列文件与符号，越界即回报编排器，手册 §6.4）

> 格式＝`路径:符号,符号,…`（与 M0-04-design §9 同体例）。**标注「⚠写权缺口」的路径不在任务卡
> `scope_allow` / `state.json.tasks["M2-01"].scope` 内**，必须先拿到 §12 U-2 的裁定才能动；
> 未裁定前 S2–S7 **禁**自行创建或修改它们（手册 §6.4：flash 遇设计外问题必须回报，不得自行决定）。
> 本文**不写死**任何符号面计数与工具裁决：`__all__` 项数、用例数、分母一律以 `inspect` / `--collect-only` 实取为准，
> import 序以 `ruff check --select I --diff` 实取为准（R8-1 / A115 / R12-4）。

### 11.1 S2（`qwen3.8-max` high，`src/campaignlab/domain/activity/**`，**只新建**；纯领域层，禁 SQL、禁开事务、禁 import `campaignlab.api`）

- `domain/activity/__init__.py`：分层说明（照 `application/__init__.py` 与 `worker/__init__.py` 的 docstring 体例，
  写明「本包不碰数据库、不开事务、不取系统时间」三条红线）＋ re-export 面（`__all__` 以 `inspect` 实取为准）。
- `domain/activity/states.py`：`ActivityStatus`（Literal，取值 = 切片 `operations.getActivity.schemas.Activity.
  properties.status.enum` 实取）· `RuleState`（= `operations.getRule.schemas.RuleVersion.properties.state.enum`）·
  `RuleCheckState`（= `operations.checkRule.schemas.RuleCheck.properties.state.enum`）·
  `TemplateId`（= `operations.getRule.schemas.CouponRule.properties.template.const` 与 `.CallbackRule.…const`）·
  `ACTIVITY_STATES` · `RULE_STATES`（两者一律 `tuple(get_args(<Literal>))`，禁抄字面量）·
  `ACTIVITY_TERMINAL_STATES` · `RULE_TERMINAL_STATES` · `ActivityTransitionId` · `ActivityTransition` ·
  `ACTIVITY_TRANSITIONS`（§3.1 三行）· `RuleTransitionId` · `RuleTransition` · `RULE_TRANSITIONS`（§3.2 四行）·
  `assert_activity_transition_allowed` · `assert_rule_transition_allowed` · `is_activity_terminal` · `is_rule_terminal` ·
  `ACTIVITY_ISSUE_CODES`（`ACTIVITY_ARCHIVED` 等 §3.1 的细因标签）。
  体例逐条对齐 `worker/states.py`（`@dataclass(frozen=True, slots=True)` + `Final[tuple[…]]` +
  「表外迁移根本不存在」+ `guard` 只是可读镜像、运行期只信 `rowcount`），但**禁 import `worker`**（`scope_deny`）。
- `domain/activity/digests.py`：`RULE_DIGEST_LENGTH`（=64，取自切片 `ddl.rule_versions` 的 `CHECK(length(digest)=64)`）·
  `rule_digest(content, terms, source_rule_version, *, canonicalize) -> str`（§4.6；
  `canonicalize` 由调用方注入 `api/common.py::canonical_json` —— 这样既不在 `domain` 里产生运行期
  `domain → api` 导入边，又不出现第二份规范化实现）· `digest_projection(content, terms, source_rule_version) -> dict`
  （供测试直接断言投影信封的键集与 `terms` 排序）。
- `domain/activity/clauses.py`：`REQUIRED_CLAUSE_KEYS`（§4.1 两个模板的键元组，**唯一来源**）· `ALL_CLAUSE_KEYS` ·
  `GateIssue`（`@dataclass(frozen=True, slots=True)`：`code` / `location` / `message` / `severity`，
  领域侧中间形态，由 api 层映射成契约 `Issue`，**禁**在 domain 里 import `Issue`）· `CLAUSE_ISSUE_CODES`
  （G1–G6 六个 + `SCHEMA_VERSION_UNSUPPORTED` + `CONFIRMATION_DIGEST_MISMATCH` + `CONFIRMATION_NOTE_REQUIRED`）·
  `evaluate_clause_gate(*, template, terms, registered_evidence_ids) -> tuple[GateIssue, …]`（§4.3 六条，
  顺序即 G1→G6、按 `REQUIRED_CLAUSE_KEYS` 的键序再按数组下标）·
  `note_satisfies_warnings(*, note, warnings) -> GateIssue | None`（§4.2 第 8 条：NFKC + `strip()` 后非空）·
  `confirm_digest_matches(*, provided, current) -> bool`（§4.2 第 6 条，只比较、不回显）。
- `domain/activity/bindings.py`：`BindingDraft`（`@dataclass(frozen=True, slots=True)`：`strategy_id` /
  `source_version` / `valid_from` / `valid_until` / `evidence_id`，`valid_*` 为 `datetime.date`）·
  `BINDING_ISSUE_CODES`（`BINDING_EMPTY_INTERVAL` / `BINDING_OVERLAP` / `BINDING_DUPLICATE_KEY` /
  `BINDING_EVIDENCE_UNREGISTERED`）· `validate_bindings(*, drafts, registered_evidence_ids) -> tuple[GateIssue, …]`
  （§3.4 四条，顺序＝空区间 → 重复键 → 相交 → 证据未登记）· `intervals_intersect(a, b) -> bool`
  （起含止排的标准相交式，**单独导出**供测试直接打表）· `BINDING_SORT_KEY`（§7.4 的数组顺序）。
- `domain/activity/checks.py`：`CheckId` · `CheckCategory` · `Check` · `CHECKS` · `CHECK_IDS` ·
  `RuleContext`（`@dataclass(frozen=True, slots=True)`：`rule_id` / `template` / `content`(Mapping) /
  `terms`(Sequence[Mapping]) / `sibling_confirmed`(Sequence[Mapping]，供 C9，只含 `id`/`template`/`starts_at`/`ends_at`）·
  `CheckResult`（`issues` / `boundary_cases`）· `BoundaryCaseDraft`（`id` / `label` / `template` /
  `input_payload`(Mapping，**领域侧的 CaseInput 字典**，由 api 层 `model_validate` 成契约 DTO) / `verification`）·
  `CHECK_ISSUE_CODES`（§5.3 表里全部 code）· `REASON_CODE_GLOSSARY`（§5.4 的 15 个原因码字面量，**只作文案用**）·
  `run_checks(context) -> CheckResult`（按 `CHECKS` 注册序跑、`(code, location)` 去重、稳定排序）·
  `check_state_of(issues) -> RuleCheckState`（§5.2 的判定式）· `boundary_cases_for(context) -> tuple[BoundaryCaseDraft, …]`
  （§5.4 的 18 条配方，**禁读时钟**）· 模块级自证 `assert len(CHECKS) == len(CHECK_IDS)` 且 `CheckId` 无重复。
- `domain/activity/diff.py`：`FieldChangeDraft`（`path` / `before` / `after`，值为 `str | None`）·
  `DIFF_PATH_LABEL` / `DIFF_PATH_SOURCE_VERSION` / `DIFF_PATH_CONTENT_PREFIX` / `DIFF_PATH_TERMS_PREFIX`（§6.5 的四类 path）·
  `render_scalar(value) -> str | None`（§6.5 的字符串化口径：整数十进制、布尔 `true`/`false`、时刻 ISO、`None` 保持 `None`）·
  `field_changes(*, baseline, candidate, canonicalize) -> tuple[FieldChangeDraft, …]`
  （只比较 §4.6 的投影 + `label`；排序＝`/label` → `/content/*` 字段名字典序 → `/source_rule_version` → `/terms/*` 键字典序）·
  `FIELD_CHANGE_MAX_LENGTH`（=1000，取自 `operations.compareRules.schemas.FieldChange.properties.before.maxLength`）。
- `tests/domain/activity/test_layering.py`（S5 落，符号见 §11.5）：AST 断言 `domain/activity/**` 内**零**运行期
  `campaignlab.api` / `campaignlab.infra` / `campaignlab.application` 导入边（体例＝`tests/unit/test_layering_edges.py`
  的「读 AST 不读源文本」＋ 自带分母断言防 glob 扫空），并附**正向对照**（在 `tmp_path` 里造一个违规探针文件，
  断言扫描器抓得到）。

### 11.2 S2 附带的契约 DTO 面（⚠写权缺口：`src/campaignlab/api/common.py`、`tests/unit/test_domain_errors.py`）

- `api/common.py`（**A91 同构、纯追加、0 删除行**）：`ActivityStatus` / `RuleState` / `RuleCheckState` /
  `TemplateId` 四个别名改为 **import 自 `domain/activity/states.py` 并 re-export**（`no_implicit_reexport` 已开 ⇒
  必须同步进 `__all__`，LANE-COMMON §3.5）· 新 DTO `Binding` · `Activity` · `ActivityPage` · `ActivityCreate` ·
  `ActivityUpdate` · `RuleContent`（判别式联合，§2.2）· `CouponRule` · `CallbackRule` · `Term` · `RuleVersion` ·
  `RuleVersionPage` · `RuleCreate` · `RuleUpdate` · `Confirmation` · `BoundaryCase` · `CaseInput`（判别式联合）·
  `CouponCaseInput` · `CouponEvent` · `CallbackCaseInput` · `CallbackEvent` · `RuleCheck` · `FieldChange` · `RuleDiff`
  （字段与约束逐条照 §2，全部 `ConfigDict(extra="forbid")`，位置排在既有 `Job` 之后、私有助手之前，
  与 `WorkspacePage` 的分节注释体例一致）· `__all__` 追加上述公开名（**项数以 `inspect` 实取为准，本文不写死**）。
  复用既有 `_IdStr` / `RevisionInt` / `Issue` / `Problem` / `ObjectKind`，**禁**第二份定义
  （`tests/unit/test_domain_errors.py::test_common_py_contains_no_moved_definition` 的同型纪律）。
- `tests/unit/test_domain_errors.py`：**只改** `test_common_public_surface_is_unchanged` 里那条按数字钉死的
  `len(common.__all__)` 断言（改成「与 `inspect` 实取的公开名集合对撞」或按新实取值更新，**二选一由编排器定**，
  见 §12 U-2 ③）；该文件其余用例（含 `PROBLEM_CODES` 20 码面与 `DomainError` 子类面）**一字不改** ——
  本设计**零新增** `Problem.code`、**零新增** `DomainError` 子类（§4.3、§6.4 已逐处遵守）。

### 11.3 S2 附带的应用层与基础设施层（⚠写权缺口：`application/`、`infra/db/repositories.py`、`api/deps.py`、`api/app.py`）

- `application/activity_service.py`（**只新建**）：`ACTION_ACTIVITY_CREATED` / `ACTION_ACTIVITY_UPDATED` /
  `ACTION_ACTIVITY_ARCHIVED` / `ACTION_RULE_DRAFT_CREATED` / `ACTION_RULE_SUCCESSOR_DRAFT_CREATED` /
  `ACTION_RULE_CONTENT_UPDATED` / `ACTION_RULE_LABEL_UPDATED` / `ACTION_RULE_CONFIRMED` /
  `TARGET_KIND_ACTIVITY` / `TARGET_KIND_RULE`（§7.3；`AuditWriter.write(action=…)` 收 `str`，故**无需**改
  `application/audit.py`）· `ACTIVITY_ID_PREFIX="act"` · `RULE_ID_PREFIX="rul"` · `EMPTY_PATCH_DETAIL` ·
  `ARCHIVED_DETAIL` · `IMMUTABLE_DETAIL` · `DIGEST_MISMATCH_DETAIL` · `NOTE_REQUIRED_DETAIL` ·
  `DUPLICATE_EXTERNAL_DETAIL`（detail 一律固定中文短句，禁调用点现编）·
  `ActivityCreateOutcome` / `ActivityWriteOutcome` / `RuleWriteOutcome`（`@dataclass(frozen=True, slots=True)`：
  `status` / `headers` / `body` / `replayed` + `as_envelope()`，体例＝`WorkspaceCreateOutcome`）·
  `ActivityService`（方法：`list_activities` · `get_activity` · `create_activity` · `update_activity`）·
  `RuleService`（方法：`list_rules` · `create_rule` · `get_rule` · `update_rule` · `confirm_rule` · `check_rule` ·
  `compare_rules`）· `_Replay`（内部控制流，照 `workspace_service.py` 同名类）·
  游标：`ACTIVITIES_CURSOR_VERSION=1` · `activity_query_digest(...)` · `rule_query_digest(...)` ·
  `_cursor_key(...)`（复用 `application/workspace_service.py::load_cursor_secret` 与 `BAD_CURSOR_DETAIL`，
  **禁**第二把密钥、第二句 detail）。两个 service 的构造签名与 `WorkspaceService` 同形
  （`engine` / `clock` / `config` / 各 repository / `IdempotencyGuard` / `AuditWriter` / `cursor_secret`，全部可注入）。
- `infra/db/repositories.py`（**A82 纯追加、0 删除行**）：`ActivityRecord` · `BindingRecord` · `RuleVersionRecord` ·
  `_activity_of(row)` · `_binding_of(row)` · `_rule_version_of(row)` · `ActivityRepository`
  （`insert` · `get` · `list_page` · `update_fields` · `find_by_external` · `set_current_rule` ·
  `list_receipt_ids` · `list_rule_ids`）· `ActivityBindingRepository`（`replace_set` · `list_for_activity` ·
  `list_for_activities`（批量，防 N+1）· `evidence_exists`（只读 `evidence` 表））·
  `RuleVersionRepository`（`insert` · `get` · `list_page` · `update_draft` · `confirm` ·
  `list_confirmed_siblings`（供 C9）· `list_confirmed_case_ids`（只读 `cases`，供 §6.5 的
  `requires_rerun_case_ids`））。**三张表的 DML 文本只允许出现在本文件**（A81「SQL 写点唯一」）；
  所有 UPDATE 一律返回 `int`（`rowcount`），**禁**在仓储层翻译领域错（`worker/store.py` docstring 的既有分工）；
  所有写 UPDATE 的 WHERE 谓词必须含 §3 的 `guard` 镜像（`status='OPEN' AND revision=:revision` /
  `state='DRAFT' AND revision=:revision` / `state='DRAFT' AND revision=:revision AND digest=:digest`）。
- `api/deps.py`（**纯追加**）：`ActivityService` Protocol · `RuleService` Protocol（`@runtime_checkable`，
  成员面逐字对应 §11.3 的两个实现类；docstring 写明「实现＝`application/activity_service.py::…`」，
  体例＝既有 `WorkspaceService` Protocol）· `get_activity_service(request)` · `get_rule_service(request)`
  （复用既有私有 `_state_service(request, attribute, port)`，`attribute` 分别取
  `"activity_service"` / `"rule_service"`）。
- `api/app.py`（**A90① 的 A10 最小例外，≤6 行**）：`create_app` 追加两个可注入形参
  `activity_service` / `rule_service`（默认 `None`，**不注入就不装配**，与既有三个服务同语义）＋
  两行 `app.state.<name> = <service>` ＋ 两行 `app.include_router(<router>)`（条件与既有
  `if workspace_service is not None:` 同形）。**禁**改 `openapi_url=docs_url=redoc_url=None`、
  中间件添加顺序、`ALLOWED_HEADERS`（`If-Match` 已在其中，实测无需追加）、既有路由挂载。

### 11.4 S3（`qwen3.8-flash`，`src/campaignlab/api/activities.py`，**只新建**）

`router`（`APIRouter(prefix=API_PREFIX, tags=["activities"])`）· `list_activities` · `create_activity` ·
`get_activity` · `update_activity` · 私有 `_activity_response(activity, *, request_id, status=200)`（组装 `ETag`）·
私有 `_activity_page_response(page, *, request_id)`（**不带 ETag**，§6.1）· `__all__`（以 `inspect` 实取为准）。
四个 handler 的签名逐字照 §1.1–§1.4；装饰器一律 `operation_id="<operationId>"` + `responses=declared_responses(<2xx>)`；
函数体一律「解析 → 调 service → 组装响应」＋ `except DomainError as exc: return problem_response(exc, request_id=…)`；
`Depends(...)` 作默认值的两行照 `api/workspaces.py` 就地 `# noqa: B008`（A47 / 手册 §9.9 的既有豁免口径，
禁改 `pyproject.toml`）。**禁**新增／修改本文件以外的任何文件（挂载与端口在 §11.3，DTO 在 §11.2）。

### 11.5 S4（`qwen3.8-flash`，`src/campaignlab/api/rules.py`，**只新建**）

`router`（`tags=["rules"]`）· `list_rules` · `create_rule` · `get_rule` · `update_rule` · `confirm_rule` ·
`check_rule` · `compare_rules` · 私有 `_rule_version_response(rule, *, request_id, status)` ·
私有 `_rule_version_page_response(page, *, request_id)` · 私有 `_rule_check_response(check, *, request_id)`
（把 `BoundaryCaseDraft.input_payload` 交给 `CaseInput` 做 `model_validate`，**校验失败即 500 `INTERNAL_ERROR`**：
框架自己生成的反例不合法属服务端缺陷，禁静默丢弃）· 私有 `_rule_diff_response(diff, *, request_id)` · `__all__`。
七个 handler 的签名逐字照 §1.5–§1.11；`If-Match` 的三个声明一律按 §6.2 的**可选形参 + 契约 pattern** 口径
（这是本卡最容易踩红的一处，禁照契约的 `required: true` 直译）。

### 11.6 S5（`qwen3.8-flash`，`tests/domain/activity/**`，**只新建**；⚠写权缺口：`tests/domain/__init__.py`）

- `tests/domain/__init__.py`（**空文件**，⚠不在 `tests/domain/activity/**` 字面量内，见 §12 U-2 ④）·
  `tests/domain/activity/__init__.py`（空文件，在 scope 内）。
- `test_states.py`：`test_activity_state_machine_a1_a2_a3_are_exactly_the_registered_rows` ·
  `test_rule_state_machine_r1_r4_are_exactly_the_registered_rows` ·
  `test_archived_activity_is_immutable_and_rejects_every_mutation` ·
  `test_confirmed_rule_version_is_immutable_on_update` ·
  `test_confirmed_rule_version_is_immutable_on_reconfirm` ·
  `test_successor_draft_does_not_touch_the_confirmed_parent` ·
  `test_transition_tables_have_teeth_positive_control`（**正向对照**：临时增删一行迁移即断言失败，用 `tmp_path`
  造探针，禁落工作树）。函数名必须含 `state_machine`（V7）与 `immutable`（V1，任务卡 gate 的 `-k` 字面量）。
- `test_clause_gate.py`：`test_clause_gate_blocks_when_a_required_key_is_missing` ·
  `test_clause_gate_blocks_when_a_required_key_is_open` ·
  `test_clause_gate_blocks_on_duplicate_key` ·
  `test_clause_gate_blocks_on_missing_or_unregistered_evidence` ·
  `test_clause_gate_blocks_on_empty_decision` ·
  `test_clause_gate_six_by_three_matrix`（满额赠券 6 键 × 远程回拨 3 键的参数化确认矩阵，
  fixture 取值直接用 `spec/CampaignLab-SDD-v1.0/fixtures/cases/rules.json` 的 `CP-V1` / `CB-V1` 与
  `fixtures/api-examples.json` 第 3 条示例的六个 `terms`）·
  `test_clause_gate_warning_requires_note` · `test_clause_gate_digest_mismatch_is_reported` ·
  `test_clause_gate_required_keys_are_the_spec_nine`（与任务卡 `public_frozen` 行的键集合逐字对撞）。
  函数名必须含 `clause_gate`（V3，任务卡 gate 的 `-k` 字面量）。
- `test_digest.py`：`test_rule_digest_projection_is_content_sorted_terms_and_source_version` ·
  `test_rule_digest_ignores_label_and_confirmation` · `test_rule_digest_is_stable_across_key_order` ·
  `test_rule_digest_matches_stored_column`（与 §5.2 的 500 守护同源）。
- `test_bindings.py`：`test_binding_interval_is_start_inclusive_end_exclusive` ·
  `test_binding_empty_interval_is_rejected` · `test_binding_overlap_is_rejected` ·
  `test_binding_duplicate_key_is_rejected` · `test_binding_evidence_must_be_registered` ·
  `test_binding_sort_key_is_frozen`。
- `test_checks.py`：`test_check_framework_registers_every_check_id_exactly_once`（含分母断言：`len(CHECKS) > 0`，
  防 glob 扫空全绿）· `test_check_framework_five_ac004_categories_all_have_teeth`（逐类构造一个必触发输入，
  断言 ERROR/WARNING 真的产出）· `test_check_state_needs_confirmation_on_unconfirmed_clause` ·
  `test_boundary_cases_cover_the_ten_spec_counterexamples`（§5.4 的 18 条逐条对 id/label）·
  `test_boundary_case_inputs_validate_against_contract`（每条 `input_payload` 过 `CaseInput.model_validate`）·
  `test_boundary_cases_are_deterministic_without_clock`（同一 `RuleContext` 两次调用逐字节相同）·
  `test_boundary_case_count_never_exceeds_contract_max`。函数名必须含 `check_framework` 或 `boundary_case`（V6）。
- `test_diff.py`：`test_rule_diff_paths_are_frozen_and_sorted` · `test_rule_diff_excludes_non_projection_fields` ·
  `test_rule_diff_renders_values_as_strings` · `test_rule_diff_cp_v1_to_cp_v2_is_refund_policy_only`
  （用 fixture 的 `CP-V1` / `CP-V2`，实测只差 `refund_policy`）。
- `test_layering.py`：见 §11.1 末条（含正向对照）。

### 11.7 S6（`qwen3.8-flash`，`tests/api/activities/**`，**只新建**）

- `tests/api/activities/__init__.py`（空文件）· `tests/api/activities/conftest.py`：
  `REPO` / `SLICE`（读 `orchestrator/handoff/M2-01.slice.json`）/ `LIVE_CONTRACT` / `DDL` / `T0` / `GUARD` /
  `IDENTITY` / `harness`（体例照 `tests/api/conftest.py::Harness`：`create_app()` 的注入位**显式给齐**、
  DDL 从活契约建库、时间一律 `FixedClock`）· `seed_evidence(ws, *, artifact_id, evidence_id)`
  （**只**用 SQL 播种 `artifacts` + `evidence` 两行，§3.4；禁 import `api/evidence.py`）·
  `seed_activity(...)` · `idem_key()` · `authed_client` · `create_activity_json(...)` · `create_rule_json(...)`。
  ⚠ **本文件与既有 `tests/api/conftest.py` 同 basename ⇒ 落盘后必须跑一次全树 mypy（V15，LANE-COMMON §3.6）。**
- `test_etag.py`：`test_update_activity_etag412_rejects_stale_if_match` ·
  `test_update_rule_etag412_rejects_stale_if_match` · `test_confirm_rule_etag412_rejects_stale_if_match` ·
  `test_missing_if_match_is_428_not_422`（三个端点各一条；**函数名必须含 `etag412`**，V2 的 `-k` 字面量）·
  `test_malformed_if_match_is_422` · `test_etag_is_quoted_decimal_revision` ·
  `test_confirm_rule_bumps_activity_etag_and_current_rule_id`（V9 的 `current_rule`）·
  `test_replay_returns_the_original_etag_even_with_a_wrong_if_match`（§7.5 末条）·
  `test_label_only_update_changes_etag_but_not_digest`（§4.6 的反直觉面）。
- `test_conflicts.py`：`test_dup_external_activity_id_is_409_with_two_issues`（**函数名必须含 `dup_external`**，
  V4 的 `-k` 字面量；断言两条 `issues` 的 `location` 与 `message` 含既有活动 ID）·
  `test_dup_external_race_falls_back_to_409_not_500` ·
  `test_null_bank_id_never_triggers_dup_external`（SQLite NULL 语义，§6.4）·
  `test_idempotency_conflict_is_409` · `test_empty_patch_is_422` · `test_archived_activity_rejects_update_409` ·
  `test_confirmed_rule_rejects_update_409_and_writes_denied_audit`（AC-003 的「试编辑」+ 审计留痕）·
  `test_confirm_with_stale_digest_is_409_version_mismatch` ·
  `test_confirm_without_required_clause_is_422_evidence_required`（AC-004 的 HTTP 面）·
  `test_unreachable_codes_are_declared_but_unreachable`（§6.6 的五个码，断言不可达本身，禁 `skip`/`xfail`）。
- `test_rule_diff.py`：`test_rule_diff_shows_changed_fields_sources_and_digest`（**函数名必须含 `rule_diff`**，
  V5 的 `-k` 字面量；AC-003 的「差异字段、条款来源和摘要」三件一起断言）·
  `test_rule_diff_cross_template_is_422` · `test_rule_diff_requires_rerun_case_ids_is_empty_when_no_change` ·
  `test_rule_diff_across_workspaces_is_404`。
- `test_bindings_api.py`：函数名一律含 `binding`（V8）：`test_binding_full_replacement_semantics` ·
  `test_binding_absent_from_patch_leaves_rows_untouched`（AC-002 的「保持无绑定」）·
  `test_binding_overlap_is_422` · `test_binding_unregistered_evidence_is_422_evidence_required` ·
  `test_binding_empty_interval_is_422_not_500`。
- `test_list_filters.py`：函数名一律含 `list_filter`（V10）：`test_list_filter_by_status_multi_value` ·
  `test_list_filter_by_q_matches_name_and_external_id` ·
  `test_list_filter_unknown_status_is_422` · `test_list_filter_cursor_binds_all_four_params` ·
  `test_list_filter_bad_cursor_is_400_with_the_frozen_detail` ·
  `test_list_rules_status_param_filters_the_state_column`（§1.5 的命名陷阱）·
  `test_list_pages_have_no_etag_header`（§6.1）· `test_cross_workspace_is_404`。
- `test_contract_declarations_m2.py`：`test_declared_responses_match_the_slice_for_all_eleven_ops`
  （实现侧 `route.responses` vs 切片 `operations.<opId>.operation.responses`，A95 口径；
  期望值**不写死**，从切片实取）· `test_operation_id_matches_function_name_for_all_eleven_ops` ·
  `test_every_problem_code_used_here_is_in_the_registry`（体例＝
  `tests/api/test_contract_declarations.py::_CODES_USED_BY_THIS_DIRECTORY`）。

### 11.8 S7（`qwen3.8-flash`，`evidence/M2/M2-01/**` ＋ `evidence/M2/summaries/M2-01.md`）

`commands.md`（V1–V15 逐条：命令、rc、时间戳、环境行）· `ac.md`（AC-002 给「数据面 + API 已交付，
复盘视图侧 deferred_to M3-01 / M3-04」；AC-003 给判定 + 依据 + 证据指针；AC-004 给「框架级判定 +
数值判定归 M2-02」，逐条对齐 §9）· `clauses.md`（满额赠券 6 键 × 远程回拨 3 键的确认矩阵 +
错误阻止 vs 警告需备注的实际输出）· `gates/V1.log`…`V15.log`（含**正向对照**的 RED 原文与复原后的 sha256 双向核验）·
`http/{listActivities,createActivity-201,createActivity-409,getActivity-200,updateActivity-200,updateActivity-412,
updateActivity-428,listRules,createRule-201,getRule-200,updateRule-409,confirmRule-200,confirmRule-422,
checkRule-needs-confirmation,checkRule-ready,compareRules-200,problem-404,problem-409,problem-412,problem-422,
problem-428}.json` · `evidence/M2/summaries/M2-01.md`（**≤30 行**）。S7 禁改任何代码或测试。

### 11.9 写权缺口一览（＝§12 U-2 的载荷；未裁定前 S2–S7 禁动）

| 路径 | 需要的改动 | 缺口类型 | 既有裁定先例 |
|---|---|---|---|
| `src/campaignlab/application/activity_service.py` | 新建（§11.3） | 不在 `scope_allow` | M0-02/S3d 的 `application/workspace_service.py`、M0-04 的 `worker/store.py` |
| `src/campaignlab/infra/db/repositories.py` | 纯追加 3 个 Repository（0 删除行） | 不在 `scope_allow` | A82（对该文件的「纯追加」处置）、A81（SQL 写点唯一） |
| `src/campaignlab/api/common.py` | 纯追加 24 个 DTO/别名 + `__all__`（0 删除行） | 不在 `scope_allow`，且派单文 §1 明写「禁在 S1 阶段改它」 | A91（`JobPage` 由 S4 在该文件 append-only 追加，与 `WorkspacePage` 同构） |
| `src/campaignlab/api/deps.py` | 纯追加 2 个 Protocol + 2 个提供器 | 不在 `scope_allow` | M0-02/S3d 的三个提供器；M0-04/S2b-2 的 `worker/deps.py` |
| `src/campaignlab/api/app.py` | ≤6 行（2 形参 + 2 state + 2 include_router） | 不在 `scope_allow` | A90① 的「A10 最小例外，≤3 行」 |
| `tests/unit/test_domain_errors.py` | 只改 `len(common.__all__)` 那一行断言 | 不在 `scope_allow`；且当前 `tests/unit/test_task_cards.py` 正由 lane X 在飞（**本卡不碰**） | A115（禁写死符号面计数）⇒ 建议改成实取对撞而非改数字 |
| `tests/domain/__init__.py` | 新建空文件 | 在 `tests/domain/activity/**` 字面量**之外** | M1-03 的 N1（同型：gate 点名的测试目录未入 scope） |

### 11.10 方案 B 的平移映射（仅当编排器拒绝 §11.9 的扩围时启用；符号名与字段序**完全不变**）

| 方案 A 落点 | 方案 B 落点 | 代价 |
|---|---|---|
| `api/common.py` 的 24 个 DTO/别名 | `api/activities.py`（活动族 5 个 + `Binding`）与 `api/rules.py`（规则族 18 个） | `_IdStr`/`RevisionInt` 需在两处各自重声明（漂移风险）；M2-02/M2-03/M2-04 的 `scope_deny` 含这两个文件 ⇒ 下游**读不到** DTO，只能各抄一份（违反「禁两处各存一份」） |
| `api/deps.py` 的 2 个 Protocol + 2 个提供器 | 在 `api/activities.py` / `api/rules.py` 内各自实现私有 `_activity_service(request)` / `_rule_service(request)`（读 `request.app.state`，缺失即 `RuntimeError`） | 复制 `_state_service` 的取值口径（约 10 行 ×2）；`deps.py` 不再是提供器的单一入口 |
| `api/app.py` 的 2 行 `include_router` | **仍必须**改 `api/app.py`（无替代落点） | 缺口无法消除，仍需最小例外裁定 |
| `application/activity_service.py` | `domain/activity/service.py`（含事务与 SQL） | 违反 `ARCHITECTURE.md`「用例层负责事务／基础设施层实现 SQLite」与 A81「SQL 写点唯一」⇒ 需新立 ADR，**本文不推荐** |
| `infra/db/repositories.py` 的 3 个 Repository | 同上，SQL 落 `domain/activity/service.py` | 同上 |
| `tests/unit/test_domain_errors.py` 的那一行 | **不需要改**（`__all__` 不变） | 方案 B 的唯一净收益 |

## 12. 未决问题（交编排器裁定，实现方不得自行决定，手册 §6.4）

- **U-1（阻塞面：派单文与编排器覆盖项的一处事实断言与切片／活契约不符 ⇒ 自查项 ④ 无法按字面满足）**
  **问题**：派单消息的「编排器覆盖项」与派单文 §1 硬约束都写「切片实测 `listActivities` 的查询参数只有
  `cursor`/`limit`（+ path 的 `workspace_id`）」，并据此要求「未出现 `status` 查询参数的设计」。
  实测相反：切片 `operations.listActivities.operation.parameters` 有 **5** 项
  （`workspace_id`(path) / `cursor` / `limit` / `q` / `status`），`operations.listRules` 有 **6** 项
  （多一个 path `activity_id`）；活契约 `contracts/openapi.json` 的同两个 op 逐字相同，且全契约共 **16** 个
  list op 带 `status` 查询参数（`listActivities`/`listRules`/`listImports`/`listSnapshots`/`listDefinitions`/
  `listCases`/`listRuns`/`listCandidates`/`listPreflights`/`listThresholds`/`listReports`/`listActions`/
  `listJobs`/`listEvidence`/`listAudit`/`listExports`），只有 `listWorkspaces` 被 CR-002 移除（实测其参数为
  `cursor`/`limit`/`q`）。旁证三条：① `src/campaignlab/api/workspaces.py` 模块 docstring 原文
  「该裁定**只**作用于 `listWorkspaces`，其它 `list*` op 的 `status` 参数不受影响」；
  ② `orchestrator/state.json` 的 N7① 裁定原文「`listJobs.status` 支持逗号分隔多值（编排器实测该参数仍在活契约中，
  合法；注意与 CR-002 已移除的 `listWorkspaces.status` 区分）」；③ ADR-006 §4.7（该文件第 57–59 行）说的是
  「另有 6 个资源同样**缺状态字段**、9 处使用 `state` 命名」，讲的是**资源 Schema 的状态字段**与命名一致性，
  不是「list op 的 `status` 查询参数已被移除」。
  **候选 A（倾向）**：承认实测，按契约实现 `q` + `status`（本文 §1.1 / §1.5 已按此冻结，多值口径沿用 N7①），
  并由编排器更正派单文与覆盖项的该句、把自查项 ④ 改成「设计的查询参数集合与切片
  `operations.<opId>.operation.parameters` 逐字相同（既不多也不少）」。
  理由：活契约是实现唯一依据（手册 §7、切片 `source.rule` 原文），且 `contracts/**` 对本卡只读——
  我**无权**让契约去适配派单文的断言。
  **候选 B**：坚持派单文口径，只实现 `cursor`/`limit`。后果：`status`/`q` 成为契约里声明但服务端忽略的参数
  （前端按契约发筛选会静默得到未过滤结果），或者必须走手册 §7 立 CR 从活契约的 `listActivities`/`listRules`
  移除这两个参数（与 CR-002 同型，且会连带影响另外 14 个 list op 的一致性）。**不推荐**：这不是设计问题，
  是契约变更问题，且与 N7① 已生效的裁定互相否证。
  **本 lane 的处置**：按候选 A 冻结设计（因为「禁发明」的前提是契约里没有，而实测有），
  并在回执第 3 段如实把自查项 ④ 报为 **FAIL（按派单文字面）／PASS（按契约实测）**，附可复跑断言。
- **U-2（阻塞面：S2–S4 的写权缺口，未裁定则 flash 档无法派单）**
  **问题**：任务卡 `scope_allow` 与 `state.json.tasks["M2-01"].scope` 实测只含 8 项
  （`domain/activity/`、`api/activities.py`、`api/rules.py`、`tests/domain/activity/`、`tests/api/activities/`、
  本文件、`evidence/M2/M2-01/`、`evidence/M2/summaries/M2-01.md`），但按 `ARCHITECTURE.md`「用例层负责事务／
  基础设施层实现 SQLite」与 A81「SQL 写点唯一」，11 个 op 要跑通还必须动 §11.9 表里的 7 处
  （`application/activity_service.py`、`infra/db/repositories.py`、`api/common.py`、`api/deps.py`、
  `api/app.py`、`tests/unit/test_domain_errors.py`、`tests/domain/__init__.py`）。
  **候选 A（倾向）**：按 §11.9 逐项批准**最小扩围**，并对三处既有冻结面沿用既有裁定口径——
  `api/common.py` 走 A91 的 append-only（0 删除行）、`infra/db/repositories.py` 走 A82 的纯追加（0 删除行）、
  `api/app.py` 走 A90① 的 A10 最小例外（≤6 行）。同时请裁定 ③：`tests/unit/test_domain_errors.py` 里
  `assert len(common.__all__) == 51` 这条**按数字钉死**的断言，是改成新实取值（又一次写死，违反 A115
  `rule_no_hardcoded_symbol_counts`）还是改成「`__all__` 与 `inspect` 实取的公开名集合逐字对撞」（倾向后者，
  一次改掉根因）。
  **候选 B**：拒绝扩围，启用 §11.10 的方案 B。代价：DTO 住进 `api/activities.py`/`api/rules.py`，
  而 M2-02/M2-03/M2-04 的 `scope_deny` 显式含这两个文件 ⇒ 下游卡读不到 `Activity`/`RuleVersion`，
  只能各抄一份（违反全仓「禁两处各存一份」纪律）；且 `api/app.py` 的挂载缺口**无法**用方案 B 消除，
  仍需最小例外；`domain` 里写 SQL 还需新立 ADR 推翻 `ARCHITECTURE.md` 的分层。**不推荐**。
- **U-3（数据依赖，非阻塞设计、阻塞取证）**
  **问题**：`Binding.evidence_id` 非空且有 FK → `evidence(workspace_id,id)`（切片 `ddl.activity_bindings`），
  `Term.evidence_id` 按 `RULES.md`「含**已登记**来源」也需存在性校验；但 `evidence` 的写入面
  （`registerEvidence`/`getEvidence`）归 **M1-03**（A1 裁定），与本卡同波并行 ⇒ M2-01 无法通过 API 造出证据行。
  **候选 A（倾向）**：维持存在性校验（§3.4、§4.3 G5），S5/S6 用 SQL 直接播种 `artifacts` + `evidence` 两行
  （`evidence.artifact_id` 也有 FK，必须两表同插），并在 `evidence/M2/M2-01/clauses.md` 里注明「证据行由测试播种，
  登记面归 M1-03」；M2-04 的页面演示依赖 M1-03 先落地（wave 序已保证）。
  **候选 B**：降级为「只校验非空、不校验存在」。后果：绑定面仍会被 SQLite 的 FK 拒（`IntegrityError`），
  必须额外翻译成 422 才不冒 500，等于用更差的口径换更少的耦合；条款面（JSON 列、无 FK）则会放过
  指向不存在证据的「已确认」条款，直接削弱 AC-004 的「必填条款未确认时无法确认」。**不推荐**。
- **U-4（口径宽严，非阻塞）**：**问题**：`DOMAIN.md`「相同策略同有效区间仅允许一条权威绑定」是否只禁
  「完全相同的区间」？**候选 A（倾向）**：同 `strategy_id` 的区间**相交即拒**（§3.4），因为部分重叠同样使
  「该策略某日生效的是哪一条」不可判定，而 AC-002 的「缺绑定」判定依赖这个唯一性。
  **候选 B**：只禁完全相同的区间（更贴字面），重叠留给业务自行负责。请裁定；未裁定前按 A 实现。
- **U-5（口径补白，非阻塞）**：**问题**：活动 `ARCHIVED` 后，其下的 `createRule`/`updateRule`/`confirmRule`
  是否一并拒绝？spec 只写了活动自身「OPEN → ARCHIVED」与「归档后可查询历史」。
  **候选 A（倾向）**：一并拒绝（409 `STATE_CONFLICT`），因为 `confirmRule` 必须写
  `activities.current_rule_id`（§3.2），若放行就会修改已归档活动行，与 §3.1 的终态口径互相否证
  （LANE-COMMON §6「判据之间不得互相否证」）。**候选 B**：只拒 `updateActivity`，规则面照常可写
  （归档活动仍能产生新候选规则）。请裁定；未裁定前按 A 实现，并在 S5 用 `test_archived_activity_*` 钉住。
- **U-6（与 `cases` 的口径差异，非阻塞）**：**问题**：切片 `ddl.rule_versions` 与其 `__indexes` 实测**没有**
  「每个父版本仅一条已确认直接后继」的部分唯一索引（`cases` 有 `cases_one_confirmed_child`），
  而 `DOMAIN.md` 的规则版本行也没写这条约束。**候选 A（倾向）**：允许一父多确认后继，
  `activities.current_rule_id` 取「该活动下 `confirmed_at` 最大者（并列时 `id` 字典序最大）」（§3.2）。
  **候选 B**：领域侧自行加「一父仅一条确认后继」约束（超出 DDL 与 spec，且会让「多轮确认后回到旧父版本」
  的合法场景被拒）。若业务确需 B，属 DDL/契约变更，须走 CR。**不推荐 B**。
- **U-7（派单文措辞与契约不符，非阻塞）**：**问题**：派单文 §1 要求冻结「409 的 `diff` 字段断言口径」，
  但活契约 `components.schemas.Problem` 实测只有 7 个必填属性且 `additionalProperties: false` ⇒
  409 的响应体里**不存在也不允许**出现 `diff` 字段；全契约带 `diff` 字样的 Schema 只有 `RuleDiff`。
  **候选 A（倾向）**：按 §6.5 拆成两处真实存在的口径——409 侧用 `Problem.issues[]` 做字段级定位
  （满足 AC-002「明确定位」），`compareRules` 侧用 `RuleDiff.changes[].path` 承载「差异字段」
  （满足 AC-003）。**候选 B**：认为派单文本意是给 409 加 `diff` 字段 ⇒ 属契约变更，须走手册 §7 立 CR
  （并会撞上 `additionalProperties: false` 与前端类型生成）。**不推荐 B**。
- **U-8（`q` 的匹配字段集合，非阻塞）**：**问题**：`API.md`「q 对名称和公开编号按 NFKC casefold 查找」
  未逐资源点名「公开编号」是哪一列。**候选 A（倾向）**：`listActivities` 匹配 `name` + `external_activity_id`
  （`DOMAIN.md`「外部活动、规则版本和切片号单独保存」⇒ 外部活动号就是活动的公开编号）；
  `listRules` 匹配 `label` + `source_rule_version`（规则版本的公开编号）。
  **候选 B**：只匹配 `name` / `label`（与 `listWorkspaces` 既有实现同口径——工作区没有公开编号，
  故那边只匹配 `name`）。请裁定；未裁定前按 A 实现，并在 V10 里钉住两个字段都命中。
- **U-9（卡内既有未决问题的处置回报，无需新裁定）**：任务卡第 62 行起的三条，本 lane 的实测处置如下——
  **U-1（AC-004 归属）**：本设计按卡内切分执行（§5.4 / §5.5 / §9：框架级与反例生成归本卡，
  ±1 分的**数值判定**归 M2-02），且契约的 `BoundaryCase` 形状实测**没有**承载判定的字段，
  物理上也不可能由本卡返回判定 ⇒ 该切分与契约自洽，无需本 lane 再请裁定；
  **U-2（scope 同步）**：实测 `state.json.tasks["M2-01"].scope_synced_from_card`（`at` = 2026-11-13T04:25）
  **已**把 `orchestrator/handoff/M2-01-design.md`、`evidence/M2/M2-01/`、`evidence/M2/summaries/M2-01.md`
  三项并入，故卡内 U-2 已消解（但本文 §11.9 / U-2 指出的是**另外 7 处**缺口，与卡内 U-2 不是同一批）；
  **U-3（AC-002 的复盘视图）**：已按 B9 裁定执行，本设计**不含**任何视图接口、不碰 `web/**`（§9）。

## 13. 本文件自检（命令 → rc；均在 WSL 仓库根 `/home/szf/dev/CampaignLab` 执行，rc 与实测值以**本轮实取**为准，见回执第 2/3 段，禁写死）

| # | 命令 | 期望 |
|---|---|---|
| C1 | `uv run --no-sync ruff format --check orchestrator/handoff/M2-01-design.md` | rc=0（LANE-COMMON §3.1：`ruff format` 的作用域含 `.md`，围栏会被重排） |
| C2 | `uv run --no-sync python -c "import pathlib;d=pathlib.Path('orchestrator/handoff/M2-01-design.md').read_bytes();print(d[:3]==b'\xef\xbb\xbf', b'\r' in d, d.endswith(b'\n'), len(d))"` | rc=0 且输出 `False False True <字节数>`（UTF-8 无 BOM / 无 `\r` / 以 `\n` 结尾） |
| C3 | 自查项 ①：断言本文引用的每个 `operations.<opId>` 都实测存在于切片（正则抽取 + 集合差集，**禁目视**） | rc=0 且差集为空 |
| C4 | 自查项 ②：断言本文引用的每个 `Problem.code` 都在 `domain/errors.py::PROBLEM_CODES` 内（`import` 后集合对撞），并断言本文引用的**全部** `Problem.code` 集合 ⊆ 20 码注册表 | rc=0 且越界集为空 |
| C5 | 自查项 ③：断言本文引用的每个**仓库路径**实测存在；§11 中标注「只新建」的**待建**路径单列一张清单（用 `新建` 标记识别），不参与存在性断言 | rc=0 且悬空引用集为空 |
| C6 | 自查项 ④：按派单文字面执行「未出现 `status` 查询参数的设计」——**实测为 FAIL**，同时给出契约侧的反证断言：切片与活契约的 `listActivities`/`listRules` 参数集合逐字含 `status` | 两个 rc 都如实回报（见 U-1） |
| C7 | 附加自查：断言本文引用的每个 `operations.<opId>.schemas.<Name>` 路径都实测存在（A171 口径的**可复跑**版） | rc=0 且差集为空 |
| C8 | 附加自查：断言本文出现的每个下划线全大写 token 要么在 `PROBLEM_CODES`（20 码）内、要么在切片枚举值/DDL CHECK 值/本文 §4.3+§5.3 登记的 `Issue.code` 面内 ⇒ 证明「零发明 code」 | rc=0 且越界集为空 |

> **append-only 纪律**：本文 §1–§13 为 S1 冻结件。后续编排器裁定一律以 **§14 追记**形式增量写入
> （体例＝`M0-02-design.md` §9 与 `M0-04-design.md` §11：「纯增量，历史行一字未改」），
> 禁回头改写 §1–§13 的任何一行；`public_frozen` 面（规则版本状态机、9 个条款键）改动走 CR。
