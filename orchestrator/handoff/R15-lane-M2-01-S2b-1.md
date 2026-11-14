# R15 · lane ⟨待派⟩ · M2-01 / S2b-1 派单文（qwen3.8-max / reasoning high · critical=false · loop_cap=3+1 复审）

> **状态＝待派件。** 本文由编排器在 R15 第 3 槽留白期间预先编写，履行 A210 的拆分义务与 A215 ④。
> **派发前置条件：M2-01/S2a 必须已入库**（本棒要 import 它新建的 `src/campaignlab/domain/activity/**`
> 六模块与 `src/campaignlab/api/common.py` 追加的 DTO 面）。S2a 未入库前**禁 spawn 本棒**。
> 本文与 `orchestrator/handoff/LANE-COMMON.md` 同时生效；两者冲突时**以本文为准**（specific 覆盖 general，A214 口径）。
> 设计真值来源＝`orchestrator/handoff/M2-01-design.md` §11.3。⚠ 其中 `api/app.py` 一项已由 **A217 从本棒剥离**（见 §2）。
> 任务卡＝`orchestrator/tasks/M2-01.md`；卡与本文冲突时**停手回报**，禁自行取舍（手册 §6.4）。

## 0. 基线（开工第一件事，逐条实测；与派单消息给的数不符即**停手回报**，禁自行「修正」）

命令一律 `uv run --no-sync …`（实测 Python 3.14.10）。**禁用系统 `python3`（3.12.3）**：它会对 PEP 758 的
`except A, B:` 报假 SyntaxError（R14-1；全仓仅 `src/campaignlab/api/common.py` 两处为合法用法）。

- `git rev-parse --abbrev-ref HEAD` → `m0-framework`
- `git rev-parse --short HEAD` → 以**派单消息**给的值为权威（本文不写死任何哈希/计数，D-012 / D-014）
- `git status --porcelain` → 必须为空（共享工作树，A161；非空即停手回报，禁 `git checkout`/`clean`）
- `uv run --no-sync ruff format --check .` → rc=0，`N files already formatted` 的 N ＝派单消息值
- `uv run --no-sync ruff check .` → rc=0，`All checks passed!`
- `uv run --no-sync mypy` → rc=0，`Success: no issues found in N source files` 的 N ＝派单消息值
- pytest 冻结面收集数＝派单消息值（口径＝frozen-scope collect ＋ GIT_ENV_IGNORES 静态收集）

**分母纪律（R13-6）**：回执里一切计数只报**实测值 ＋ 归因**，禁把本文或派单文里的数字当判据抄回去。

## 1. 任务＝design §11.3 **减去** `api/app.py`（A217）

三个落点 ＋ 测试，严格按此铺开；**越出下列文件与符号即回报编排器**，禁自行扩围。

### 1.1 `src/campaignlab/application/activity_service.py`（**只新建**，实测当前 ABSENT）

符号面逐字照 design §11.3 第一条，**禁增减、禁改名**：

- 审计 action 常量 8 个：`ACTION_ACTIVITY_CREATED` / `ACTION_ACTIVITY_UPDATED` / `ACTION_ACTIVITY_ARCHIVED` /
  `ACTION_RULE_DRAFT_CREATED` / `ACTION_RULE_SUCCESSOR_DRAFT_CREATED` / `ACTION_RULE_CONTENT_UPDATED` /
  `ACTION_RULE_LABEL_UPDATED` / `ACTION_RULE_CONFIRMED`
- 审计 target 常量 2 个：`TARGET_KIND_ACTIVITY` / `TARGET_KIND_RULE`
  （`AuditWriter.write(action=…)` 收 `str` ⇒ **禁改** `src/campaignlab/application/audit.py`；
  实测该文件 148 行 / `__all__` 4 项 / `AuditWriter` 2 方法 / `audit_digest` 在顶层）
- ID 前缀 2 个：`ACTIVITY_ID_PREFIX = "act"` / `RULE_ID_PREFIX = "rul"`
- detail 常量 6 个：`EMPTY_PATCH_DETAIL` / `ARCHIVED_DETAIL` / `IMMUTABLE_DETAIL` / `DIGEST_MISMATCH_DETAIL` /
  `NOTE_REQUIRED_DETAIL` / `DUPLICATE_EXTERNAL_DETAIL`（一律固定中文短句，**禁**在调用点现编）
- Outcome 3 个：`ActivityCreateOutcome` / `ActivityWriteOutcome` / `RuleWriteOutcome`，
  `@dataclass(frozen=True, slots=True)`，字段 `status` / `headers` / `body` / `replayed` ＋ `as_envelope()`；
  体例逐条照 `application/workspace_service.py::WorkspaceCreateOutcome`
- 服务类 2 个：`ActivityService`（`list_activities` / `get_activity` / `create_activity` / `update_activity`）·
  `RuleService`（`list_rules` / `create_rule` / `get_rule` / `update_rule` / `confirm_rule` / `check_rule` /
  `compare_rules`）。两个构造签名与 `WorkspaceService` **同形**（`engine` / `clock` / `config` / 各 repository /
  `IdempotencyGuard` / `AuditWriter` / `cursor_secret`，全部可注入）
- 内部控制流 1 个：`_Replay`（照 `workspace_service.py` 同名类）
- 游标 4 个：`ACTIVITIES_CURSOR_VERSION = 1` / `activity_query_digest(...)` / `rule_query_digest(...)` /
  `_cursor_key(...)`。**复用** `application/workspace_service.py::load_cursor_secret` 与 `BAD_CURSOR_DETAIL`
  —— **禁**第二把密钥、**禁**第二句 detail（design §11.3 明写）
- 事务边界照 design §7.1（体例＝`worker/store.py` 的「一方法一短事务」＋ `workspace_service.py` 的连接口径）；
  SQL 写点唯一照 design §7.2（**SQL 只允许出现在 `infra/db/repositories.py`**，A81）；审计照 design §7.3；
  只读跨表查询照 design §7.4；显式时钟/ID 前缀/幂等键照 design §7.5

**分层许可（已实测确认，禁自行怀疑）**：`application/workspace_service.py` 现状**确实** import
`campaignlab.api.common`（13 个名字）与 `campaignlab.infra.db.repositories`；`infra/db/repositories.py` 现状
**确实** import `campaignlab.api.common`（6 个名字）。故 `api/common.py` 是共享内核、不是路由层，
本棒沿用同型导入边**不违反分层**。反之 `domain/activity/**` 有零 `api`/`infra`/`application` 导入边的
AST 守护（design §11.1 末条，S5 落）—— **本棒禁往 `domain/activity/**` 里加任何导入边**（该目录不在写权内）。

### 1.2 `src/campaignlab/infra/db/repositories.py`（**A82 纯追加，`git diff --numstat` 对该文件 deleted 必须 = 0**）

- 三个 Record：`ActivityRecord` / `BindingRecord` / `RuleVersionRecord`
- 三个行映射私有助手：`_activity_of(row)` / `_binding_of(row)` / `_rule_version_of(row)`
- `ActivityRepository`：`insert` / `get` / `list_page` / `update_fields` / `find_by_external` /
  `set_current_rule` / `list_receipt_ids` / `list_rule_ids`（8 个）
- `ActivityBindingRepository`：`replace_set` / `list_for_activity` / `list_for_activities`（批量，防 N+1）/
  `evidence_exists`（只读 `evidence` 表）（4 个）
- `RuleVersionRepository`：`insert` / `get` / `list_page` / `update_draft` / `confirm` /
  `list_confirmed_siblings`（供 C9）/ `list_confirmed_case_ids`（只读 `cases`，供 design §6.5 的
  `requires_rerun_case_ids`）（7 个）
- `__all__` **纯追加** 上述 6 个公开名（3 个 Record ＋ 3 个 Repository）；私有助手**不进** `__all__`
  （体例＝既有 `_workspace_of` / `_job_of` 等 4 个私有映射均不在 `__all__` 内，而 `job_from_row` 在）
- **三张表的 DML 文本只允许出现在本文件**（A81「SQL 写点唯一」）
- 所有 UPDATE 一律返回 `int`（`rowcount`）；**禁**在仓储层翻译领域错（`worker/store.py` docstring 的既有分工）
- 所有写 UPDATE 的 WHERE 谓词必须含 design §3 的 `guard` 镜像：
  `status='OPEN' AND revision=:revision` / `state='DRAFT' AND revision=:revision` /
  `state='DRAFT' AND revision=:revision AND digest=:digest`
- 列↔DTO 映射照 design §2.4；DDL 真值来源＝`contracts/sqlite-v1.sql`（与 design §2.4 同源）

### 1.3 `src/campaignlab/api/deps.py`（**纯追加，deleted = 0**）

- `ActivityService` Protocol ＋ `RuleService` Protocol：`@runtime_checkable`，基类 `Protocol`，
  **成员面逐字对应 §1.1 的两个实现类**（4 ＋ 7 个方法，签名含关键字-only 形态照既有 `WorkspaceService` Protocol）；
  docstring 写明「实现＝`application/activity_service.py::…`」
- `get_activity_service(request)` / `get_rule_service(request)`：**复用既有私有 `_state_service(request, attribute, port)`**，
  `attribute` 分别取 `"activity_service"` / `"rule_service"`。**禁**复制 `_state_service` 的取值口径、
  **禁**新写第二个私有取值助手（design §11.10 已把「各抄一份」判为方案 B 的代价，本棒走方案 A）
- `__all__` **纯追加** 4 个名（2 Protocol ＋ 2 提供器）。`no_implicit_reexport` 已开 ⇒ 漏进 `__all__` 即 mypy 红
- 既有 import 行只允许**追加名字**，禁改动既有名字顺序（该行属纯追加额度）

### 1.4 `tests/**`（守护 ＋ 用例）

- 落在 `tests/unit/` 与 `tests/integration/` 下**新建**文件；命名体例照既有 `test_worker_integrity.py`
- **禁改** `tests/unit/test_domain_errors.py`（那是 S2a 的写权，且其 `len(common.__all__)` 断言已由 A115 处置）
- **禁改** `tests/unit/test_task_cards.py`、`tests/unit/test_layering_edges.py`（既有守护，改了即失去牙）
- 新建 `tests/domain/**` 属 S5 写权 ⇒ **本棒禁建**
- 每条守护必须有牙（LANE-COMMON §6）：断言**符号面/行为**，禁断言本文写死的数字；
  计数型断言一律「`inspect`/AST 实取 ↔ 期望集合对撞」，禁 `len(...) == <字面量>`（A115）

## 2. 必须携带的裁定（禁自行发明，禁重新论证）

- **A217（本轮新立，对本棒最关键）**：design §11.3 的 `api/app.py` 一项要求「两行 `app.include_router(<router>)`」，
  但那两个 router 分别来自 `api/activities.py`（design §11.4＝**S3**）与 `api/rules.py`（design §11.5＝**S4**），
  而子任务序固定为 S2a → S2b → S3 → S4（A210 / A196 ①）⇒ **S2b 时点这两个模块还不存在**，
  照字面实现必然产生悬空 import。裁定：**① 本棒（S2b-1）完全不碰 `api/app.py`**；
  **② `api/app.py` 拆为独立微步骤 S2b-2（max，≤4 行：2 个可注入形参 ＋ 2 行 `app.state.<name> = <service>`），
  且必须排在 M0-04/S4 之后**（同文件争用，锁表既定顺序）；**③ 两行 `include_router` 分别下放给 S3 / S4**，
  与既有先例一致（`api/app.py` 第 156 行现存的注释占位「M0-04/S4（A10 最小例外，≤3 行）：
  `app.include_router(jobs.router)`」正是「router 挂载随创建该 router 的子任务走」的成例）。
  该设计文档自相矛盾处已记 **D-043**，原文依 D-011 **不改写**。
- **A82**：对 `infra/db/repositories.py` 的处置＝**纯追加、0 删除行**（`numstat` 的 deleted 必须为 0）
- **A81**：SQL 写点唯一 —— 三张表的 DML 只允许出现在 `infra/db/repositories.py`
- **A91**：`api/common.py` 的追加额度归 **S2a**（DTO 面）与 **M0-04/S4**（`JobPage`）；**本棒无该文件写权**
- **A115**：禁写死符号面计数；计数型守护一律实取对撞
- **A47**：`Depends(...)` 默认值 ＋ 就地 `noqa: B008` 体例，**禁**改 `Annotated`
- **A196 ①**：时序禁令 —— 禁提前实现 S3/S4 的路由层内容
- **A210**：S2 拆为 S2a（design §11.1＋§11.2）与 S2b（design §11.3），各记 1 个 max 单位，如实记账不凑配比
- **A214**：`orchestrator/**` 的禁令是**默认值**；本棒**未获**任何窄豁免 ⇒ 禁写 `orchestrator/**`（含 design 文档）
- **A206 同型纪律**：依赖注入的形态以**既有提供器**为准，禁反过来改既有提供器去迁就新类

## 3. 冻结面实测（编排器 PRE-7 逐条实测；本表为**唯一口径**，派单文/设计文里的数字一律视为待复核参考值）

| 文件 | 行数 | `__all__` | 结构面（实测） | 本棒处置 |
|---|---|---|---|---|
| `src/campaignlab/infra/db/repositories.py` | 1054 | 第 42 行，**10** 项 | 9 个类（`ArtifactRecord`/`IdempotencyRecord`/`AuditRecord`/`JobRecord`/`WorkspaceRepository` 3 法/`ArtifactRepository` 3 法/`JobRepository` **15** 法/`IdempotencyRepository` 2 法/`AuditRepository` 3 法）＋ 7 个顶层函数（`_fold`/`_iso`/`_workspace_of`/`_artifact_of`/`_idempotency_of`/`_job_of`/`job_from_row`） | 纯追加 → `__all__` 10→**16**、类 9→**12**、顶层函数 7→**10**；deleted=0 |
| `src/campaignlab/api/deps.py` | 171 | 第 40 行，**9** 项 | 3 个 Protocol（`HealthService` 1 法 / `SessionService` 3 法 / `WorkspaceService` 2 法，均 `@runtime_checkable`）＋ 顶层 `get_config`/`get_clock`/`_state_service`/`get_session_service`/`get_health_service`/`get_workspace_service`/`require_session` | 纯追加 → `__all__` 9→**13**、Protocol 3→**5**；deleted=0 |
| `src/campaignlab/api/app.py` | 157 | 第 42 行，4 项 | `create_app` 在第 87–157 行，现 6 个形参；`include_router` 区块在 149–156 | **本棒禁碰**（A217 → S2b-2） |
| `src/campaignlab/application/workspace_service.py` | 376 | 第 71 行，13 项 | `_Replay`@111 / `load_cursor_secret`@125 / `_read_key`@146 / `audit_role_of`@156 / `_query_digest`@168 / `WorkspaceCreateOutcome`@179 / `_outcome_of`@196 / `WorkspaceService`@212（6 法） | **只读**（体例来源，禁改） |
| `src/campaignlab/application/audit.py` | 148 | 第 31 行，4 项 | `audit_digest`@49 / `AuditWriter`@82（2 法） | **只读**（禁改，见 §1.1） |
| `src/campaignlab/application/activity_service.py` | — | — | **ABSENT** | 本棒新建 |
| `src/campaignlab/api/activities.py` / `api/rules.py` | — | — | **ABSENT** | 归 S3 / S4，本棒禁建 |
| `src/campaignlab/domain/activity/` | — | — | 由 **S2a** 新建（六模块＋`__init__`） | 本棒**只读** |

`src/campaignlab/application/` 实测现存：`__init__.py` `audit.py` `health_service.py` `idempotency.py`
`session_service.py` `worker.py` `workspace_service.py`。
`src/campaignlab/api/` 实测现存：`__init__.py` `app.py` `common.py` `deps.py` `health.py` `session.py` `workspaces.py`。

## 4. 写权与硬禁

**写权（白名单，仅此五项）**：
1. `src/campaignlab/application/activity_service.py`（新建）
2. `src/campaignlab/infra/db/repositories.py`（纯追加，deleted=0）
3. `src/campaignlab/api/deps.py`（纯追加，deleted=0）
4. `tests/unit/**`、`tests/integration/**` 下的**新建**文件
5. 无第五项

**硬禁**：
- 禁碰 `src/campaignlab/api/app.py`（A217 已剥离给 S2b-2）
- 禁碰 `src/campaignlab/api/common.py`（S2a 的写权；其锁入库后转 M0-04/S4 的 `JobPage`，**不是本棒**）
- 禁碰 `src/campaignlab/domain/activity/**`（S2a 的成品，本棒只读）
- 禁碰 `src/campaignlab/application/{audit,workspace_service,session_service,health_service,idempotency,worker}.py`
  与 `application/__init__.py`（只读体例来源）
- 禁碰 `src/campaignlab/api/{session,workspaces,health}.py`、`src/campaignlab/worker/**`（后者是 M0-04 链的锁）
- 禁碰 `tests/unit/test_domain_errors.py`、`tests/unit/test_task_cards.py`、`tests/unit/test_layering_edges.py`
- 禁建 `tests/domain/**`（S5 写权）
- 禁写 `orchestrator/**`、`docs/**`、`contracts/**`、`spec/**`（A214：本棒未获窄豁免）
- 禁产出取证件（design §11.8 的取证面归 **S7**）
- **零新增** `Problem.code`、**零新增** `DomainError` 子类（design §11.2 已冻结；`PROBLEM_CODES` 实测 20 码、
  `DomainError` 子类实测 14 个，本棒结束后两个数都**必须不变**）
- 禁改 `pyproject.toml` / `scripts/**`（工装面，编排器专属；FU-39 在飞期间冻结）
- AST/语法探针一律 `uv run --no-sync python`（3.14.10），**禁**系统 `python3`（3.12.3）—— R14-1
- 禁 `git commit` / `git add` / `git checkout` / `git clean` / `git stash`：**入库由编排器独占**（`scripts/orch_harness.py`）

## 5. 自验门禁（全绿才可回执；一律 `uv run --no-sync`，rc 与文本双判）

1. `ruff format --check .` → rc=0；`ruff check .` → rc=0
2. `mypy` → rc=0（strict；`warn_unused_ignores` 已开 ⇒ **禁留无用 `# type: ignore`**）
3. pytest 全量 → rc=0，passed 数 ≥ 基线值（只增不减；减少即回归，禁删既有用例凑绿）
4. `git diff --numstat -- src/campaignlab/infra/db/repositories.py` → **deleted 列必须为 0**
5. `git diff --numstat -- src/campaignlab/api/deps.py` → **deleted 列必须为 0**
6. `git status --porcelain` → 出现的路径必须**全部**落在 §4 白名单内（越界即回报）
7. 符号面实取对撞（禁写死数字，A115）：
   - `repositories.__all__` 实取集合 ⊇ 既有 10 名，且新增恰为 §1.2 的 6 个公开名
   - `api/deps.__all__` 实取集合 ⊇ 既有 9 名，且新增恰为 §1.3 的 4 个名
   - `ActivityService` / `RuleService` 两个 Protocol 的成员名集合，与 `application/activity_service.py`
     里两个实现类的公开方法名集合**逐字相等**（用 `inspect` 实取对撞，禁抄字面量）
   - `PROBLEM_CODES` 仍为实取的 20 码、`DomainError` 子类仍为实取的 14 个（**零新增**断言）
8. SQL 写点唯一（A81）：AST 扫描 `src/campaignlab/application/activity_service.py`，断言其中**零** `sqlalchemy.text(`
   调用、零 SQL 字符串字面量（正向对照：在 `tmp_path` 造一个违规探针，断言扫描器抓得到）

## 6. 守护必须有牙（LANE-COMMON §6 / A159）

每条新增守护都要在回执里给**变异探针**取证：临时改坏被测面 → 断言该守护**变红** → **字节级复原**
（复原后 `git diff --numstat` 对该文件必须回到 §5 第 4/5 条要求的状态）。
探针文件一律建在 `tmp_path` 或临时目录，**禁**把探针留在仓库里。至少覆盖：
① `ActivityRepository` 的 `guard` 镜像缺失时（去掉 `revision=:revision`）用例必须红；
② `_state_service` 被复制成第二个私有助手时，§5 第 7 条的对撞必须红；
③ 第二把 cursor 密钥/第二句 detail 出现时必须有守护红（复用断言）。

## 7. Token 双上限（R13-4：两个口径都要在回执里给结论）

- 单棒上限与超限处置照 `orchestrator/handoff/LANE-COMMON.md`；超限**先回执再继续**，禁静默截断
- 禁把 design 文档整篇抄进回执（回执 ≤90 行，只给指针：`orchestrator/handoff/M2-01-design.md` §号 ＋ 行号）

## 8. 回执（LANE-COMMON §7 的 8 段，纯文本 ≤90 行）

必须含：① 基线复测四项实测值；② 交付面逐件（路径 / 行数 / sha256 前 12 位 / `numstat` 的 added-deleted）；
③ §5 八条门禁逐条 rc ＋ 关键文本；④ 符号面实取对撞结果（集合差，不是数字）；⑤ 变异探针三组（改坏→红→复原证据）；
⑥ token 双口径结论；⑦ **U 项**（一切需编排器裁定的，禁自行决定）；⑧ 未尽面与风险。

## 9. L 循环（loop engineering）

`loop_cap = 3` ＋ 1 次复审。每轮必须**自迭代收敛**：定位 → 修 → 复跑门禁 → 记录 delta。
同一处连续 2 轮无进展即**停手回报**（禁第 3 次同法重试）。
遇 §4 硬禁与任务目标冲突、或发现设计文档自相矛盾（如 A217 那类），**一律记为 U 项上报**，禁自行取舍。
