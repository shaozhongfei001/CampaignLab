> **编排器修改标注（2026-11-13T01:54:49+08:00，依 D-014）**：① V11 的写死计数改为「rc=0 为判据 + 引用 state.json 权威键」；
> ② §5 的 V1–V13 共 10 处 `PYTHONPATH=src` 前缀已去除（Q7 裁定后由 S2 删 `[tool.uv] package = false`）；
> ③ §6 关于 `evidence/**` 不在 `scope_allow` 的说法已按 Q8 裁定更正。修改者为编排器，**非 S1 原作者**。

>
> **编排器追注（2026-11-13T02:17:03+08:00，依 CR-002 / ADR-006 / D-013）**：本文写作时（S1）的活契约指纹
> `01bd28f0772f506e` / `443552 B` 已**作废**——CR-002 选项 B 已把 `listWorkspaces` 的 `status` 查询参数
> 从活契约移除，现值 `592571099d638251` / `443309 B`（**权威来源**：
> `orchestrator/state.json → resume.self_check_gates_rc0.counts.live_openapi_sha16` / `.live_openapi_bytes`，禁写死）。
> 下列各处属**历史测量，原值不改写**，但**不得再作为期望值复跑**：
> ① 开头「依据」段的 `source.openapi.sha16` / `bytes`；
> ② §5 的 **V1**（原文「输出须为 `01bd28f0772f506e 443552`」）——复跑 V1 必须改为与 `state.json` 权威键比对，
>    与权威键不一致才是真红，与本文写死值不一致属**基准漂移**；
> ③ §8 的 **C1**（`wc -l` = 117）与 **C2**（48 files）——本文件因编排器追注已增长，`wc -l` 与 ruff 分母均已漂移，
>    分母权威值见 `counts.ruff_formatted_files`。
> 另：§7 **Q4** 的临时处置已**取消**，详见 §7 表后的编排器追注块。

# M0-02 设计 · S1 契约抽取与设计

依据 `orchestrator/handoff/M0-02.slice.json`（spec_version=1.0.1；`source.openapi.sha16=01bd28f0772f506e`、`bytes=443552`，本次实算一致 → 切片新鲜可派单）。活契约 `contracts/sqlite-v1.sql` 与基线 `spec/CampaignLab-SDD-v1.0/contracts/sqlite-v1.sql` **字节相同**（sha256 `ec9ddfbc4e7dba4c0a565161b50a222fee484eb07e6586588871bffa2efc8c0e`，`diff -u` 无输出）→ 不存在「以哪份为准」的分歧；按手册第 7 节，实现唯一依据是活契约 `contracts/`，spec 仅参考。基址 `/api/v1`（`servers[0].url`）；全局 `security=[{LocalSession:[]}]` ＝ Cookie `cl_session`，`exchangeSession`/`getHealth` 显式 `security:[]`（免会话），其余 3 个 op 继承全局；每个响应必带 `X-Request-Id`（正则 `^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$`，取 `uuid4().hex`）；`create_app()` 必须置 `openapi_url=None, docs_url=None, redoc_url=None`，契约真值只在 `contracts/openapi.json`，不得暴露第二个 OpenAPI 面。

## 1. 接口签名（5 个 operationId）

签名逐字照抄，装饰器必须显式给 `operation_id`，返回类型统一 `Response`（由 `api/common.py` 的 helper 构造：Problem 走 `application/problem+json`，成功体走 `model_dump(mode="json")`）；路由函数只做「解析 → 调 application → 组装响应」，不得写 SQL（PYTHON.md）。

- `exchangeSession` POST `/api/v1/session/exchange` — `async def exchange_session(payload: SessionExchange, request: Request, svc: SessionService = Depends(get_session_service)) -> Response`：200 `Session` ＋ `Set-Cookie: cl_session=<sid>; HttpOnly; SameSite=Strict; Path=/api/v1; Max-Age=<ttl>`｜400 `BAD_REQUEST` 正文非 JSON 或 Content-Type 错｜401 `SESSION_EXPIRED` 令牌未知／已消费／超 60s（**三者同码同 detail**，杜绝枚举 oracle）｜403 `ORIGIN_DENIED` Origin 或 Host 非实际绑定的回环源｜413 `INPUT_TOO_LARGE`｜422 `VALIDATION_ERROR` `token` 长度 <16 或 >180、出现未知字段｜500 `INTERNAL_ERROR`；契约另声明的 404/409/412/428/429 在 M0-02 不可达（Q2/Q3）。
- `getSession` GET `/api/v1/session` — `async def get_session(request: Request, svc: SessionService = Depends(get_session_service)) -> Response`：200 `Session`｜401 `SESSION_EXPIRED` 无 cookie／已过期／**进程重启后**｜403 `ORIGIN_DENIED` 仅 Host 非法（GET 不校验 Origin，但必须校验 Host）｜500 `INTERNAL_ERROR`；400/404/409/412/413/422/428/429 不可达。
- `getHealth` GET `/api/v1/health` — `async def get_health(svc: HealthService = Depends(get_health_service)) -> Response`：200 `Health{status,app_version,contract_version,worker,schema_revision}`；`contract_version` 必须运行时从活契约 `contracts/openapi.json` 的 `info.version` 读取（**禁止硬编码**，D-004 教训）；`schema_revision` ＝ alembic head revision 串；`worker` 判定见 §4；`status="READY"` 当且仅当 `worker=="READY"` 且 `schema_revision` 等于 `migrations` 的 head，否则 `"DEGRADED"`；401/403/400/404/409/412/413/422/428/429 全部不可达（`security:[]`，且 Host 白名单必须含健康探针源）｜500 `INTERNAL_ERROR`。
- `listWorkspaces` GET `/api/v1/workspaces` — `async def list_workspaces(cursor: str | None = Query(None, min_length=1, max_length=300), limit: int = Query(25, ge=1, le=100), q: str | None = Query(None, min_length=1, max_length=100), status: str | None = Query(None, min_length=1, max_length=60), actor: Session = Depends(require_session), svc: WorkspaceService = Depends(get_workspace_service)) -> Response`：200 `WorkspacePage{items(0–100), next_cursor}`；排序固定 `created_at DESC, id ASC`，键集翻页谓词 `created_at < :k0 OR (created_at = :k0 AND id > :k1)`，每页取 `limit+1` 行以判 `next_cursor`；`q` 对 `name` 做 NFKC＋casefold 子串匹配；无结果 → `items=[]`、`next_cursor=null`｜400 `BAD_CURSOR` 游标解不开／HMAC 不符／查询摘要不符｜401 `SESSION_EXPIRED`｜403 `ORIGIN_DENIED`（Host 非法）｜422 `VALIDATION_ERROR` `limit` 越界、`q`/`status` 超长｜422 `INVALID_SCOPE` `status` 不在白名单（白名单当前为空集，Q4）｜500 `INTERNAL_ERROR`；404/409/412/413/428/429 不可达。
- `createWorkspace` POST `/api/v1/workspaces` — `async def create_workspace(payload: WorkspaceCreate, idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128), actor: Session = Depends(require_session), svc: WorkspaceService = Depends(get_workspace_service)) -> Response`：201 `Workspace` ＋ `ETag: "1"` ＋ `X-Request-Id`｜400 `BAD_REQUEST`｜401 `SESSION_EXPIRED`｜403 `ORIGIN_DENIED`／`ACCESS_DENIED`｜409 `IDEMPOTENCY_CONFLICT` 同键异摘要｜413 `INPUT_TOO_LARGE`｜422 `VALIDATION_ERROR` `name` 空或 >80、`source_class` 非枚举、`authorization_note` >500、未知字段、`Idempotency-Key` 长度不合规（`issues[0].location="/header/Idempotency-Key"`）｜500 `INTERNAL_ERROR`；404/412/428/429 不可达（Q2/Q3）。领域约束：`source_class="AUTHORIZED_DEIDENTIFIED"` 时 `authorization_note` 必须非空（DDL 表级 CHECK）→ 违反映射 422 `VALIDATION_ERROR`、`issues[0].location="/authorization_note"`；`id` 一律服务端生成 `new_resource_id("W")`，不接受客户端指定；`revision` 恒为 1；写 `workspaces` 与写 `audit`（`sequence=1`）必须同一事务（DOMAIN.md「数据变更和审计事件同事务」）。

> **【编排器追注 · 2026-11-13T06:55:00+08:00 · CR-002/ADR-006 指向性提示 · 只加注不改写原文】**
> 上方第 29 行 `listWorkspaces` 签名中的 `status: str | None = Query(None, min_length=1, max_length=60)` 形参，
> 以及同行的两处错误分支 —— `422 VALIDATION_ERROR`「`q`/`status` 超长」中的 `status` 部分、
> `422 INVALID_SCOPE`「`status` 不在白名单（白名单当前为空集，Q4）」—— **均已作废**，详见本文档下方
> 「CR-002 已 MERGED（选项 B）」追注块。之所以在此重复提示：S3b/S4 为 `qwen3.8-flash` 档、被要求
> 「严格按 S1 设计逐字落地」，若只读本节即照抄，会实现一个活契约里已不存在的查询参数（Gauss Q7 上报的陷阱）。
>
> 编排器实测活契约 `listWorkspaces.parameters` 为 **3** 项：`cursor`(string, minLength 1, maxLength 300)、
> `limit`(integer, 1–100, default 25)、`q`(string, minLength 1, maxLength 100)，**无 `status`**。
> 实现与测试一律以活契约为准（手册第 7 节 / D-011）：不得保留 `status` 形参、不得实现 `WORKSPACE_STATUS_WHITELIST`、
> 不得写 `issues[0].location="/query/status"` 的任何用例期望。**注意区分**：`listJobs.status` 仍存在于活契约中
> （合法，支持逗号分隔多值），`getHealth` 的 `Health.status`（`Literal["READY","DEGRADED"]`）亦为合法响应字段，二者均不得误删。

## 2. 数据结构（字段级）

DTO 一律 `model_config = ConfigDict(extra="forbid")`；Pydantic 必须拒绝未知字段、布尔冒充整数、非有限数值、不带偏移的时刻（PYTHON.md）。
- `SessionExchange`：`token: str`，16–180，必填，无默认。
- `Session`：`actor_id: str`(1–96，ID 正则)｜`actor_name: str`(1–80)｜`allowed_roles: list[Role]`(1–6 项，`Role = Literal["OPERATOR","DESIGNER","DATA_OWNER","ANALYST","TESTER","REVIEWER"]`)，三者全必填。
- `Health`：`status: Literal["READY","DEGRADED"]`｜`app_version: str`(1–48)｜`contract_version: str`(1–48)｜`worker: Literal["READY","OFFLINE"]`｜`schema_revision: str`(1–48)，全必填、不可空。
- `WorkspaceCreate`：`name: str`(1–80，必填)｜`source_class: Literal["SYNTHETIC","AUTHORIZED_DEIDENTIFIED"]`(必填)｜`authorization_note: str | None = None`(1–500 或 null)。
- `Workspace`：`id: str`(1–96，ID 正则)｜`revision: int`(1–9007199254740991)｜`created_at: datetime`(必须 tz-aware)｜`name: str`(1–80)｜`source_class: str`(同上枚举)｜`authorization_note: str | None`；6 字段全在 `required`（含 null），序列化必须显式出现 `authorization_note`。
- `WorkspacePage`：`items: list[Workspace]`(0–100)｜`next_cursor: str | None`(1–300)，全必填。
- `Problem`：`type: str`(1–250)｜`title: str`(1–200)｜`status: int`(400–599)｜`code: str`(1–96，ID 正则)｜`detail: str`(1–500)｜`request_id: str`(1–96，ID 正则)｜`issues: list[Issue]`(0–1000)；7 字段全必填、`extra="forbid"`、`media_type="application/problem+json"`。`Issue`：`code: str`(1–96)｜`location: str`(1–500，JSON Pointer，如 `/name`、`/query/limit`、`/header/Idempotency-Key`)｜`message: str`(1–500)｜`severity: Literal["ERROR","WARNING","INFO"]`，4 字段全必填。
- `domain/errors.py::PROBLEM_CODES: dict[str, tuple[int, str, str]]`（`code → (status, type, title)`），`type = "urn:campaignlab:problem:" + code.lower()`（Q5）：`BAD_REQUEST`=400、`BAD_CURSOR`=400、`SESSION_EXPIRED`=401、`ORIGIN_DENIED`=403、`ACCESS_DENIED`=403、`RESOURCE_NOT_FOUND`=404、`IDEMPOTENCY_CONFLICT`=409、`STATE_CONFLICT`=409、`VERSION_MISMATCH`=409、`REVISION_CONFLICT`=412、`PRECONDITION_REQUIRED`=428、`INPUT_TOO_LARGE`=413、`VALIDATION_ERROR`=422、`INVALID_SCOPE`=422、`EVIDENCE_REQUIRED`=422、`JOB_CAPACITY`=429（必须附 `Retry-After` 1–3600）、`INTERNAL_ERROR`=500；`detail` 缺省取 `title`，500 的 `detail` 只含 `request_id`，禁止回显堆栈／SQL／用户源字段（OPERATIONS.md）。
- 会话令牌（**仅进程内存**；28 表里没有 sessions 表，落库即违背 AC-035）：`SessionTokenStore = RLock + dict[str, _Grant]`，`_Grant(identity: AppIdentity, issued_at: datetime, expires_at: datetime)`；`mint(identity: AppIdentity, now: datetime) -> str` 用 `secrets.token_urlsafe(32)`（43 字符，落在 16–180），`expires_at = now + timedelta(seconds=TOKEN_TTL_SECONDS)`，`TOKEN_TTL_SECONDS: Final = 60`（OPERATIONS.md）；`consume(token: str, now: datetime) -> AppIdentity | None` 在锁内 `pop`（保证一次使用），`now >= expires_at` 返回 `None`。
- 会话记录（**仅进程内存**）：`SessionStore = RLock + dict[str, SessionRecord]`，`SessionRecord(session_id: str, actor_id: str, actor_name: str, allowed_roles: tuple[Role, ...], created_at: datetime, expires_at: datetime, last_seen_at: datetime)`，`session_id = secrets.token_urlsafe(32)`，`expires_at = created_at + timedelta(seconds=config.session_ttl_seconds)`；方法 `create/get/touch/invalidate_all`，`get()` 命中即刷新 `last_seen_at`，过期则删除并返回 `None`；Cookie 参数 `cl_session`、`httponly=True`、`samesite="strict"`、`path="/api/v1"`、`secure=False`（回环 http）、`max_age=` 剩余整数秒。
- `AppIdentity(actor_id: str, actor_name: str, allowed_roles: tuple[Role, ...])`：本机模式 `actor_id = actor_name = getpass.getuser()`（不匹配 ID 正则 → 启动失败 rc=2），`allowed_roles` ＝ 6 个角色全给（OPERATIONS.md「首版以本机当前 OS 用户操作」）；由 `config.py::resolve_local_identity()` 产出，进程启动时铸令牌。
- ETag：`etag(revision: int) -> str` 返回 `f'"{revision}"'`（带双引号十进制整数，对齐 If-Match 正则 `^"[1-9][0-9]*"$`）；`check_if_match(header: str | None, current_revision: int) -> None`：`header is None` → raise `PreconditionRequired`（428 `PRECONDITION_REQUIRED`），`header != etag(current_revision)` → raise `RevisionConflict`（412 `REVISION_CONFLICT`）。切片 5 个 op 均未声明 If-Match，故 `create_workspace` **不得**调用它（Q3）；helper 仍须实现并被单测钉住，供 M1 的 16 个 If-Match op 复用。
- 幂等：唯一键 `(scope_key, actor_id, operation, idem_key)`；`createWorkspace` 的 `scope_key = "GLOBAL"`（无工作区上下文），工作区级 op 取 `workspace_id`；`operation` 取 operationId 字面量；`idem_key` 即 `Idempotency-Key` 原文（8–128）。`request_digest = sha256(canonical_json({"path": <规范化路径>, "query": <排序后键值>, "body_sha256": <原字节 sha256>, "files": []}))` 小写 64 hex，其中 `canonical_json(o) = json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":"))` 且字符串先 NFC。落库 `idempotency.response_json` ＝ 信封 `{"status": int, "headers": {…}, "body": {…}}`，`response_status` 与 `status` 同值并以列为准；命中同 digest → 重放 `status`／`headers`(ETag、Location)／`body`，**仅 `X-Request-Id` 重新生成**；命中异 digest → 409；顺序「先幂等、后 If-Match」（API.md）；**只登记 2xx**，4xx/5xx 不写行、重试重新求值，拒绝与失败由结构化日志（`request_id`/`workspace_id`/`operation`/`result_code`/耗时）留痕；并发靠主键唯一，`INSERT` 冲突即回读已存行重放，禁止裸「先查后插」。
- Cursor：`encode_cursor(payload: dict, secret: bytes) -> str` ＝ `b64u(canonical_json(payload)) + "." + hmac_sha256(secret, b64u)[:16]`，`payload = {"v": 1, "q": sha256(canonical_json(排序后查询))[:16], "k": [created_at, id], "s": actor_id}`；`secret` 取数据目录 `state/cursor.key`（首次生成 32 随机字节、跨重启稳定、权限 0600）；`decode_cursor(s: str, secret: bytes) -> dict | None`，`None` → 400 `BAD_CURSOR`；编码后总长必须 ≤300。
- 显式时钟：`clock.py::Clock`（`Protocol`，`def now(self) -> datetime`，必须返回 tz-aware UTC）；`SystemClock`（**全仓唯一**允许出现 `datetime.now(UTC)` 的地方）、`FixedClock(initial: datetime, step: timedelta = timedelta(0))`（每次 `now()` 前进 `step`）；经 `Depends(get_clock)` 注入 service，application／domain／infra 层禁止自取系统时间。持久层时刻统一 UTC ISO-8601（`datetime.isoformat()`，形如 `2026-11-12T23:01:00+00:00`），业务日期按 `TZ_SHANGHAI = ZoneInfo("Asia/Shanghai")` 投影，月份 `YYYY-MM`。
- 金额与比率：`domain/values.py` 定义 `Cents = int`（人民币分）与 `RatioStr = str`（十进制字符串）类型别名，S3 建立、M1+ 复用；M0-02 的 5 个 op 无金额／比率字段，**任何位置禁止 `float`**。

## 3. 首迁边界

- 28 表全清单（`grep -c '^CREATE TABLE'` 实测＝28）：`workspaces, artifacts, activities, evidence, activity_bindings, rule_versions, source_mappings, imports, import_files, snapshots, cases, thresholds, analysis_results, runs, run_cases, candidates, preflights, preflight_rows, receipts, reports, actions, action_followups, report_actions, exports, jobs, object_evidence, idempotency, audit`；附 5 个显式索引 `jobs_ready, snapshots_lookup, rules_activity, analysis_snapshot, actions_due`；28 表全为 `STRICT`。
- **真正接读写（5 张）**：`workspaces`（listWorkspaces 读、createWorkspace 写）｜`idempotency`（createWorkspace 幂等登记与重放）｜`audit`（createWorkspace 同事务写 `sequence=1`、`action="WORKSPACE_CREATED"`、`outcome="ACCEPTED"`、`role=` actor 业务角色；因 `audit.workspace_id NOT NULL REFERENCES workspaces(id)`，**只有已落到某工作区的操作才能写 audit**，故 `exchangeSession`/`getSession`/`getHealth`/`listWorkspaces` 与被拒绝的 `createWorkspace` 一律不写 audit，只写结构化日志）｜`jobs`（`JobRepository` ＋ `WorkerSupervisor.poll_once()` 租约轮询 ＋ `Health.worker` 可见性；M0-02 无 HTTP 作业面）｜`artifacts`（仅 `ArtifactRepository` ＋ 单测，无 HTTP 面，为 M1 导入落制品预置）。
- **建表但不接业务（23 张，显式声明）**：`activities, evidence, activity_bindings, rule_versions, source_mappings, imports, import_files, snapshots, cases, thresholds, analysis_results, runs, run_cases, candidates, preflights, preflight_rows, receipts, reports, actions, action_followups, report_actions, exports, object_evidence`；只建结构、不写 repository、不出现在任何路由，S3/S4 不得为它们添加代码或用例。
- 迁移形态与连接：`migrations/alembic.ini`（`script_location = %(here)s`、`version_locations = %(here)s/versions`，`sqlalchemy.url` 由 `env.py` 从 `AppConfig` 覆盖），命令 `alembic -c migrations/alembic.ini upgrade head`；revision 串固定 `0001_initial_schema`、`down_revision = None`（`Health.schema_revision` 以此为准）；`env.py` 每次连接执行 `PRAGMA foreign_keys=ON`；`infra/db/engine.py::PRAGMAS` ＝ `foreign_keys=ON`、`busy_timeout=5000`、`journal_mode=DELETE`（OPERATIONS.md，WAL 留待后续评估）；SQLite 连接不可跨线程，必须每请求短连接。
- 等价性判据 —— `src/campaignlab/infra/db/ddl_compare.py::compare_schema(ref_conn: sqlite3.Connection, mig_conn: sqlite3.Connection) -> list[str]`，返回空列表即等价，非空则每项是一条可读差异：① 表集合相等且 `len == 28`（迁移库额外**只**允许 `alembic_version`，显式排除后再比）；② 每表 `PRAGMA table_info` 六元组逐行相等（`cid,name,type,notnull,dflt_value,pk`）；③ 每表 `PRAGMA foreign_key_list` 逐行相等（`id,seq,table,from,to,on_update,on_delete,match`），复合外键列序敏感；④ `PRAGMA index_list` ＋ 每索引 `PRAGMA index_info` 相等，5 个显式索引名与列序一致；⑤ `PRAGMA table_list` 的 `strict` 列 28 表全为 1；⑥ `sqlite_master.sql` 空白归一（连续空白→单空格、去首尾）后逐表字符串相等；⑦ `PRAGMA integrity_check` ＝ `ok` 且 `PRAGMA foreign_key_check` 返回 0 行；⑧ 负例：`evidence(workspace_id='WS-B', artifact_id=<WS-A 的行>)`、`audit(workspace_id='WS-MISSING', …)`、`artifacts(workspace_id='WS-MISSING', …)` 均触发 `sqlite3.IntegrityError`，`workspaces.source_class='X'` 触发 CHECK，`source_class='AUTHORIZED_DEIDENTIFIED'` 且 `authorization_note=''` 被拒而 `source_class='SYNTHETIC'` 且 `authorization_note IS NULL` 通过。

## 4. 边界清单（AC → 实现约束 → 已知失败模式）

- **AC-001**（切片原文：启动本机模式、换取一次性会话、新建并进入工作区；正常会话进入／重复令牌拒绝／工作区切换保留各自数据／worker 状态可见）· 令牌仅首次可用：`consume()` 在单个 `RLock` 内 `pop`，返回值即所有权。失败模式：两个并发请求同时换取 → 必须只有一方 200、另一方 401。
- 重复换取拒绝：第二次 → 401 `SESSION_EXPIRED`，`detail` 与「令牌从未存在」逐字相同。失败模式：detail 写成「令牌已使用」即制造枚举 oracle，并让 M0-03 前端走进错误分支。
- 令牌 60s 过期：判定 `now >= expires_at`，`now` 必须来自注入的 `Clock`。失败模式：混用 `time.monotonic()` 与 `datetime.now()`，或在 service 里直接取系统时间导致测试无法推进。
- 工作区切换保留各自数据：每个 repository 方法首参 `workspace_id: str`，SQL 一律带 `WHERE workspace_id = ?`，DDL 复合主键 `(workspace_id, id)` 与复合外键兜底。失败模式：单对象查询漏 `workspace_id` 条件 → 跨工作区读；`artifacts.relative_path` 是**全局** UNIQUE（不含 workspace_id），制品路径必须内嵌 `workspace_id` 前缀，否则两工作区同内容互撞。
- worker 状态在 health 可见：`WorkerSupervisor` 在 `serve` 时以后台线程启动，循环体每轮 `poll_once()` 后置 `heartbeat_at = clock.now()`；`Health.worker = "READY" if (clock.now() - heartbeat_at) <= WORKER_HEARTBEAT_TTL_SECONDS else "OFFLINE"`（`WORKER_HEARTBEAT_TTL_SECONDS: Final = 15`）。失败模式：worker 线程抛异常退出但心跳仍在窗口内 → 误报 READY；故循环必须捕获后置 `self.failed = True`，`worker` 立即 `OFFLINE`、`status` 降 `DEGRADED`。
- **AC-034**（切片原文：过期会话、错误 Host/Origin、跨工作区 ID、上传失败 → 401/403/404/413 或 422；隔离、路径、日志和 ETag 证据可查）· 过期／缺失会话 → 401 `SESSION_EXPIRED`（两态同码同 detail）。
- 错误 Host/Origin：`api/common.py::OriginHostGuard` 对 unsafe 方法（POST/PUT/PATCH/DELETE）校验 `Host ∈ config.allowed_hosts` 且 `Origin ∈ config.allowed_origins`，GET 只校验 `Host`；不匹配 → 403 `ORIGIN_DENIED`；默认 `allowed_hosts={"127.0.0.1:<port>","localhost:<port>"}`、`allowed_origins={"http://127.0.0.1:<port>","http://localhost:<port>"}`，均可注入。失败模式：`TestClient` 默认 `Host: testserver` 且不带 Origin → 不注入白名单则全部用例 403。
- 资源 ID 校验与「404 与越权同样按不可见处理」：路径／正文中所有 ID 必须匹配 `RESOURCE_ID_RE = ^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$`（不匹配 → 422 `VALIDATION_ERROR`，`issues[].location` 指到具体指针）；归属校验失败与「不存在」**必须返回逐字相同的响应**：404 `RESOURCE_NOT_FOUND` ＋ 固定 `detail`（不回显 ID、不区分原因）。切片 5 个 op 都没有 `workspace_id` 路径参数，故 M0-02 的 404 面 ＝ 未匹配路由：任何深链探测（例如 `GET /api/v1/workspaces/{id}`，契约中**不存在**该路径）必须经 `install_error_handlers()` 返回 Problem 形 404，而不是 FastAPI 默认的 `{"detail":"Not Found"}`；这正是「深链与刷新回到合法入口」的服务端前置。
- 上传失败（M0-02 无文件端点，等价约束＝正文过大）：先按 `Content-Length` 预判、再在流式读取时累计二次判定，超过 `MAX_JSON_BODY_BYTES: Final = 1_048_576`（Q6）→ 413 `INPUT_TOO_LARGE`。失败模式：只信 `Content-Length`（可伪造），或先 `await request.body()` 全量读入再判长度（等于没有上限）。
- ETag 证据可查：201 必带 `ETag: "1"`；幂等重放必须回放**同一** ETag（从 `response_json.headers` 取，不得重算）。
- **AC-035**（切片原文：锁版本、迁移、核对包与 API；任务卡另述会话过期、进程重启后会话失效）· 会话过期：`expires_at = created_at + session_ttl_seconds`（默认 3600，Q6），`SessionStore.get()` 内过期即删并返回 `None` → 401。
- 进程重启后会话失效：两个 store 挂在 `app.state`，纯内存、不落盘不入库 → 重启后浏览器仍带 cookie 但查不到 → 401 `SESSION_EXPIRED`。失败模式：为「让测试好写」把 session 写进 SQLite 或数据目录文件，直接违背本条；测试必须用**新建 app 实例**模拟重启，而不是清字典。
- 并发、锁与运行环境：两个 store 的全部操作在单个 `RLock` 内完成；幂等写入靠 `idempotency` 主键唯一（INSERT 冲突 → 回读重放）；`workspaces` 与 `audit` 同事务；失败模式＝跨线程共享 `sqlite3.Connection`。证据必须记 CPython 3.14.10／SQLite 3.53.1／alembic 1.20.1／uv 0.13.7／ruff 0.17.4／Node v24.22.3，并附 `uv lock --check` 的 rc。

## 5. 验证清单（命令 → 期望 rc；供 S5 直接采集，无「人工确认」项）

全部在 WSL 仓库根执行，前置 `export PATH="$HOME/.local/bin:$HOME/.local/share/node/bin:$PATH"`。**Q7 已裁定**：`pyproject.toml`＋`uv.lock` 已加入 `scope_allow`，**S2 须删除 `[tool.uv] package = false` 并重跑 `uv lock`**，此后 `campaignlab` 可直接导入，故 §5 全部 V 命令的 `PYTHONPATH=src` 前缀**已作废并去除**（见 D-014）。
| # | 目标（gate / AC） | 命令 | 期望 rc |
|---|---|---|---|
| V1 | 切片新鲜度（派单前置） | `uv run --no-sync python -c "import hashlib,pathlib;d=pathlib.Path('contracts/openapi.json').read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))"`，输出须为 `01bd28f0772f506e 443552` | 0 |
| V2 | 活契约门禁未回归 | `uv run --no-sync python scripts/check_contracts.py check --validate` | 0 |
| V3 | 首迁可执行 | `D=$(mktemp -d); CAMPAIGNLAB_DATA_DIR=$D uv run --no-sync alembic -c migrations/alembic.ini upgrade head` | 0 |
| V4 | DDL 等价＋28 表＋PRAGMA＋跨工作区外键负例 | `uv run --no-sync pytest -q tests/integration/bootstrap/test_migration_equivalence.py` | 0 |
| V5 | AC-001 | `uv run --no-sync pytest -q tests/api -k ac001` | 0 |
| V6 | AC-034 | `uv run --no-sync pytest -q tests/api -k ac034` | 0 |
| V7 | AC-035 | `uv run --no-sync pytest -q tests/api tests/integration/bootstrap -k ac035` | 0 |
| V8 | 契约：Problem 结构／ETag／409／412／428／422／幂等重放一次生效 | `uv run --no-sync pytest -q tests/api/test_contract_conformance.py` | 0 |
| V9 | 契约：202 与 GET 作业语义（DTO 级，见 Q2） | `uv run --no-sync pytest -q tests/unit/test_job_dto.py tests/unit/test_problem_codes.py` | 0 |
| V10 | `doctor` 可运行 | `uv run --no-sync python -m campaignlab doctor` | 0 |
| V11 | ruff lint ＋ format | `uv run --no-sync ruff check . && uv run --no-sync ruff format --check .`，后者以 **rc=0** 为判据，**计数不得写死**（写死值随并行 lane 漂移：本档撰写时 40，`f12dcf8` 时点 56）；权威现值见 `state.json → resume.self_check_gates_rc0.counts.ruff_formatted_files`（见 D-014） | 0 |
| V12 | mypy strict ＋ 全量 pytest | `uv run --no-sync mypy && uv run --no-sync pytest -q` | 0 |
| V13 | HTTP 样本落盘 ＋ 证据齐备 | `CAMPAIGNLAB_HTTP_EVIDENCE_DIR=evidence/M0/M0-02/http uv run --no-sync pytest -q tests/api -k record_http && test -s evidence/M0/M0-02/commands.md && test -s evidence/M0/M0-02/ac.md && test -s evidence/M0/M0-02/migration-diff.md && test -s evidence/M0/summaries/M0-02.md && ls evidence/M0/M0-02/http/*.json` | 0 |

## 6. 文件级 TODO 与白名单（S3–S5 不得越出；越界即回报编排器，手册 6.4）

- **S3**（`qwen3.8-flash`，DTO 与路由样板；**只新建**，格式 `路径:符号`，含各目录 `__init__.py`）
  `src/campaignlab/__main__.py:main` · `cli.py:build_parser,cmd_doctor,cmd_serve` · `config.py:AppConfig,load_config,resolve_local_identity,TOKEN_TTL_SECONDS,DEFAULT_SESSION_TTL_SECONDS,MAX_JSON_BODY_BYTES,WORKER_HEARTBEAT_TTL_SECONDS` · `clock.py:Clock,SystemClock,FixedClock`
  `src/campaignlab/domain/errors.py:DomainError,SessionInvalid,OriginDenied,AccessDenied,ResourceNotFound,IdempotencyConflict,StateConflict,RevisionConflict,PreconditionRequired,InputTooLarge,ValidationFailure,InvalidScope,JobCapacity,InternalFailure,PROBLEM_CODES` · `domain/ids.py:RESOURCE_ID_RE,is_resource_id,new_resource_id,new_request_id` · `domain/values.py:Cents,RatioStr,TZ_SHANGHAI`
  `src/campaignlab/api/app.py:create_app` · `api/common.py:Problem,Issue,SessionExchange,Session,Health,WorkspaceCreate,Workspace,WorkspacePage,Job,problem_response,accepted_response,etag,check_if_match,encode_cursor,decode_cursor,canonical_json,OriginHostGuard,request_id_middleware,install_error_handlers` · `api/deps.py:get_config,get_clock,get_session_service,get_health_service,get_workspace_service,require_session` · `api/health.py:get_health` · `api/session.py:exchange_session,get_session` · `api/workspaces.py:list_workspaces,create_workspace`
  `src/campaignlab/application/session_service.py:SessionTokenStore,SessionStore,SessionRecord,AppIdentity,SessionService` · `application/workspace_service.py:WorkspaceService` · `application/health_service.py:HealthService` · `application/idempotency.py:IdempotencyGuard` · `application/audit.py:AuditWriter` · `application/worker.py:WorkerSupervisor`
  `src/campaignlab/infra/db/engine.py:make_engine,PRAGMAS` · `infra/db/repositories.py:WorkspaceRepository,ArtifactRepository,JobRepository,IdempotencyRepository,AuditRepository,job_from_row`。5 个路由函数名与 `operation_id` 必须逐字对应：`get_health/getHealth`、`exchange_session/exchangeSession`、`get_session/getSession`、`list_workspaces/listWorkspaces`、`create_workspace/createWorkspace`。S3 禁止触碰：`pyproject.toml`、`uv.lock`、`contracts/**`、`spec/**`、`scripts/**`、`web/**`、`migrations/**`、`tests/**`、`orchestrator/**`。
- **S4**（`qwen3.8-flash`，契约测试参数化；**只新建**）
  `tests/api/conftest.py:app,client,clock,token_factory,http_recorder` · `tests/api/test_contract_conformance.py:test_problem_shape_for_every_declared_code,test_declared_status_codes_match_slice,test_etag_header_on_201,test_if_match_412_branch,test_missing_if_match_428_branch,test_idempotency_replay_once,test_idempotency_conflict_409,test_validation_422_branches,test_accepted_response_202_shape`
  `tests/api/test_session.py:test_ac001_token_single_use,test_ac001_repeat_token_rejected,test_ac001_token_ttl_60s,test_ac034_expired_session_401,test_ac034_bad_origin_403,test_ac034_bad_host_403,test_ac035_session_ttl_expiry,test_ac035_restart_invalidates_session` · `tests/api/test_health.py:test_ac001_worker_visible,test_health_degraded_when_worker_offline,test_contract_version_read_from_live_openapi`
  `tests/api/test_workspaces.py:test_ac001_create_201_and_etag,test_list_pagination_and_cursor,test_bad_cursor_400,test_idempotency_replay_returns_same_body,test_413_oversized_body,test_ac034_unknown_route_is_problem_404,test_ac034_cross_workspace_is_invisible_404,test_record_http_samples` · `tests/unit/test_job_dto.py:test_job_dto_validates_against_live_schema,test_accepted_response_headers_and_location,test_job_repository_rejects_cross_workspace` · `tests/unit/test_problem_codes.py:test_every_code_maps_to_declared_status,test_type_uri_is_stable,test_problem_serializes_as_problem_json`
  参数化必须覆盖：切片 5 op × 各自声明的全部状态码（断言「凡服务端可能返回的码都是 Problem 形、`status` 与 `code` 一致、`content-type` 为 `application/problem+json`」）；409 `IDEMPOTENCY_CONFLICT`；412 `REVISION_CONFLICT` 与 428 `PRECONDITION_REQUIRED`（走 `check_if_match` 单元路径，Q3）；422（缺字段／超长／未知字段／`limit` 越界／非法 ID 各 ≥1 例）；202＋`Location`＋`Job`（走 `accepted_response` DTO 路径，Q2）；Idempotency-Key 重放**一次生效**（同键同体两次 → 两个 201 逐字节相同且 DB 只 1 行，同键异体 → 409）。S4 禁止修改 `src/**`、`contracts/**`、`migrations/**` 与既有 `tests/unit/test_contract_slice.py`、`tests/unit/test_frontend_baseline.py`。
- **S5**（`qwen3.8-flash`，AC 证据采集；**只新建**，不得改代码或测试）
  `evidence/M0/M0-02/commands.md` · `evidence/M0/M0-02/ac.md` · `evidence/M0/M0-02/migration-diff.md` · `evidence/M0/M0-02/gates/V1.log … V13.log` · `evidence/M0/M0-02/http/{exchangeSession,getSession,getHealth,listWorkspaces,createWorkspace,problem-401,problem-403,problem-404,problem-409,problem-413,problem-422}.json` · `evidence/M0/summaries/M0-02.md`
  S5 逐条采集 §5 的 V1–V13（命令、rc、时间戳、环境行）；`ac.md` 对 AC-001/034/035 各给「判定＋依据＋证据指针」；`migration-diff.md` 贴 `compare_schema()` 的空返回与 28 表指纹摘要；**Q8 已裁定**：`evidence/M0/M0-02/**` 与 `evidence/M0/summaries/M0-02.md` 已显式加入 `scope_allow`，S5 按 `outputs:` 落点采集即属合规（见 D-014）。
- **S2**（`qwen3.8-max`，已由编排器单独派单；白名单列出以免 S3/S4 误入）：`migrations/alembic.ini`、`migrations/env.py`、`migrations/script.py.mako`、`migrations/versions/0001_initial_schema.py:upgrade,downgrade`、`src/campaignlab/infra/db/ddl_compare.py:compare_schema,normalize_sql,table_fingerprint`、`tests/integration/bootstrap/conftest.py:migrated_db,reference_db`、`tests/integration/bootstrap/test_migration_equivalence.py:test_28_tables,test_column_fingerprint_equal,test_foreign_key_list_equal,test_index_list_equal,test_all_tables_strict,test_sql_text_normalized_equal,test_pragma_integrity_and_fk_check,test_cross_workspace_fk_negative,test_check_constraints_negative`。

## 7. 未决问题（不自行决定，交编排器／项目负责人裁定；手册 6.4）

| # | 问题 | 影响面 | 本设计的临时处置 |
|---|---|---|---|
| Q1 | **AC-034/AC-035 语义冲突**：任务卡 gates 把 AC-034 写成「深链与刷新回到合法入口」、AC-035 写成「会话过期、进程重启后会话失效」；但切片与 `spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md` 第 42/43 行原文里 AC-034＝「过期会话、错误 Host/Origin、跨工作区 ID 和上传失败」、AC-035＝「锁版本、迁移、核对包和 API」。「深链/刷新」属 UI-01 页面侧（M0-03），「会话过期/重启」在原文里归 AC-001＋AC-034。 | gates 判定口径、S5 `ac.md` 结论 | §4 同时覆盖两种读法（服务端侧：未匹配路由返回 Problem 形 404 ＋ 会话过期/重启 401），以切片原文为主、任务卡描述为附加约束 |
| Q2 | **「202 与 GET 作业语义」在切片内不可达**：全契约 11 个返回 202 的 op（validateImport、publishImport、correctSnapshot、runComparison、createRun、runReview、runDiagnosis、executeQuestion、createReport、retryJob、createExport）无一在 M0-02 的 5 个 operationId 里，`getJob`/`listJobs` 也不在切片里。 | gate「契约测试：202 与 GET 作业语义」无法在 HTTP 层取证 | 在 `api/common.py` 实现 `accepted_response(job, location)`（202＋`Location`＋`ETag`＋`Job` 体）与 `job_from_row()`／`JobRepository.get()`，用 `tests/unit/test_job_dto.py` 以活契约 `Job` schema 做 jsonschema 校验；HTTP 层 202 用例待裁定（缩 gate 或扩切片重派） |
| Q3 | **412/428 在切片内不可达**：全契约 16 个带 `If-Match` 的 op 无一在 M0-02 内，`createWorkspace` 只声明 `Idempotency-Key`；gate 却要求「ETag 与 412」「409/412/422 各分支」。 | gate「契约测试：…412…」的取证层 | 实现并单测 `check_if_match()`（缺头 428、不匹配 412）＋ Problem 形断言；HTTP 端到端 412 需追加一个 If-Match op 进切片，或把该 gate 判为「DTO 级覆盖即通过」 |
| Q4 | `listWorkspaces` 声明了 `status` 查询参数（1–60），但 `Workspace` schema 与 `workspaces` 表都没有 `status` 字段 → 状态白名单无法确定（API.md 只说「按对应对象状态白名单过滤」）。 | listWorkspaces 行为、S4 用例期望 | 常量 `WORKSPACE_STATUS_WHITELIST: Final[frozenset[str]] = frozenset()`，任何非空 `status` → 422 `INVALID_SCOPE`（`issues[0].location="/query/status"`），裁定后改一行即可 |
| Q5 | `Problem.type` 的 URI 方案与 `title` 文案在契约中**完全未规定**（只约束长度 1–250／1–200），而任务卡 `public_frozen` 写明本任务与 M0-03 共同确立公共件、M0-03b 后冻结 → 一旦落地即成冻结面。 | 前端错误分支、全部后续 lane | 取 `type = "urn:campaignlab:problem:" + code.lower()`，`title` 用固定中文短句表；请在 M0-03b 冻结前裁定是否改为 `https://` 形式 |
| Q6 | 三处运行参数契约未规定：会话 TTL、JSON 正文上限、worker 心跳窗口（OPERATIONS.md 只给了文件 64 MiB／8 MiB 与令牌 60s）。 | AC-035 可测性、413 触发点、`Health.worker` 灵敏度 | 取 `session_ttl_seconds=3600`、`MAX_JSON_BODY_BYTES=1_048_576`、`WORKER_HEARTBEAT_TTL_SECONDS=15`，全部经 `AppConfig` 可注入（测试用小值） |
| Q7 | **`pyproject.toml` 与 `uv.lock` 不在 `scope_allow` 内**，但 gate「`uv run python -m campaignlab doctor` 可运行」与「pytest 全绿」都要求 `campaignlab` 可导入：已实测 `uv run --no-sync python -c "import campaignlab"` → `ModuleNotFoundError`（M0-01 设了 `[tool.uv] package = false`，其注释明确写「M0-02 交付 CLI 与 `__main__` 后删除」）；`PYTHONPATH=src` 可用但会改变 gate 命令原文。 | 全部 gate 命令口径、S2–S5 执行方式 | §5 统一用 `PYTHONPATH=src` 前缀；请裁定「把 `pyproject.toml`＋`uv.lock` 加入 M0-02 `scope_allow`（由 S2 删 `package = false` 并重跑 `uv lock`）」还是「交 Lane T 单独改」 |
| Q8 | `scope_allow` 未包含 `evidence/**`，与任务卡 `outputs:` 指定的 `evidence/M0/M0-02/{commands.md,ac.md,migration-diff.md,http/**}` 冲突；另 S3 的产出列只写 `src/campaignlab/api/**`，而 `state.json` 的 `M0-02.scope` 还含 `src/campaignlab/application/`、`src/campaignlab/infra/db/`、`tests/api/session/`、`tests/integration/bootstrap/`。 | S3/S5 是否越界（手册 6.4 要求越界即回报） | 按 `scope_allow` ∪ `state.json.M0-02.scope` 划白名单（均在 `src/campaignlab/**` 内，未触碰 `scope_deny`），`evidence/**` 按 `outputs:` 执行；请裁定确认，或把 `evidence/M0/M0-02/**` 与 `evidence/M0/summaries/**` 显式加入 `scope_allow` |

> **【编排器追注 · 2026-11-13T02:17:03+08:00 · CR-002 / ADR-006 · 只加注不改写】**
>
> 上表 **Q4** 已由项目负责人裁定，并按 **选项 B**（从契约移除该参数）原子执行完毕：
>
> - `listWorkspaces` 的 `status` 查询参数已从活契约 `contracts/openapi.json` **移除**；
>   登记见 `contracts/CHANGES.json`（pointer `/paths/~1workspaces/get/parameters/3`，kind `removed`，cr `CR-002`，adr `ADR-006`），登记项 12 → 13。
> - 故 Q4 的临时处置（常量 `WORKSPACE_STATUS_WHITELIST` 与「任何非空 `status` → 422 `INVALID_SCOPE`」过渡分支）**取消**：
>   S3/S4 **不得实现**该分支，也**不得**为其编写契约测试或用例期望。
> - 两份切片（`M0-02.slice.json` / `M0-03.slice.json`）已按移除后的活契约**重切**；
>   其 `source.openapi.sha16` / `bytes` 的**权威现值**见
>   `orchestrator/state.json → resume.self_check_gates_rc0.counts.live_openapi_sha16` / `.live_openapi_bytes`，
>   文档内**禁写死**（依 D-012 / D-013 / D-014）。
> - 重切后切片内 `listWorkspaces` 的 `status` **查询参数**残留为 0；
>   仍存在的 `getHealth → Health.properties.status`（enum `READY` / `DEGRADED`）是**合法响应字段**，与本条无关，不得误删。
>
> 本追注为**新增留痕**；上表 Q4 行原文**保持字节不变**（手册 15.9 / 15.10：历史测量值绝不重写）。

## 8. 本文件自检（命令 → rc，均在 WSL 仓库根 `/home/szf/dev/CampaignLab` 执行）

| # | 命令 | 实测 rc | 实测输出 |
|---|---|---|---|
| C1 | `wc -l < orchestrator/handoff/M0-02-design.md` | 0 | `117`（≤120） |
| C2 | `uv run --no-sync ruff format --check .` | 0 | `48 files already formatted`；追加 `--exclude orchestrator/handoff/M0-02-design.md` 复测得 `47 files already formatted` → 差值 **+1**，证明本 `.md` 已进入 ruff format 作用域并被接受（本子任务开工时基线为 39，其间 Q-VERIFY-M0-01 取证档入库使基线升到 47） |
| C3 | `uv run --no-sync ruff check .` | 0 | `All checks passed!` |
| C4 | `git status --porcelain` | 0 | 只输出一行 `?? orchestrator/handoff/M0-02-design.md`；`git ls-files --others --exclude-standard` 只列该文件、`git diff --name-only` 为空（未改动任何已跟踪文件）。采集期间并行 lane 推进了 HEAD（`33bf5c5` → `c39bd8d` → `e391a7b` → `de550a5`）并一度暂存 D-007 相关 7 个文件，**均非本子任务所为**，现已随 `de550a5` 入库，工作树回到只含本文件 |
| C5 | `git ls-files --others --exclude-standard orchestrator/handoff/M0-02-design.md` | 0 | 输出该路径 → 未被 `.gitignore` 忽略、可入库 |
> **【编排器追注 · 2026-11-13T04:12:00+08:00 · M0-02/S2 返回复核 · 只加注不改写】**
>
> S2（Galileo，qwen3.8-max high）已返回，编排器独立复跑全部判据后确认交付成立，
> 并就其上报的 4 条未决问题裁定如下。上文原有字节**一律不改**（手册 15.9 / 项目纪律：
> 历史测量值绝不重写，只加注）。
>
> **① §3 首迁边界 L54「附 5 个显式索引」与 §3 判据④「5 个显式索引名与列序一致」——数量有误，实为 6 个。**
> 活契约 `contracts/sqlite-v1.sql` 实测 `CREATE INDEX` / `CREATE UNIQUE INDEX` 共 **6** 条：`cases_one_confirmed_child`, `jobs_ready`, `snapshots_lookup`, `rules_activity`, `analysis_snapshot`, `actions_due`。
> 设计档漏计的是 **`cases_one_confirmed_child`**，它是带 `WHERE` 子句的**部分唯一索引**
> （`CREATE UNIQUE INDEX`），用朴素的 `grep '^CREATE INDEX'` 会漏掉。
> S2 已按**活契约**实现 6 个（手册第 7 节：活契约是唯一依据，设计档与之冲突时以活契约为准），
> 编排器复跑 `compare_schema(ref, mig)` 返回 **`[]`**，等价性成立。
> 判据④ 的「5 个」自此以本追注的 **6 个**为准；`ddl_compare` 的实现本身是按集合比对、
> 未写死数量，故无需改代码。
>
> **② §5/§7 的 Q7 裁定中「hatchling 进锁」的预期与工具实际行为不符（S2 上报 Q1）。**
> uv 0.13.7 实测**不**把本地可安装成员的 build-backend 写进 `uv.lock`：`grep -c hatchling uv.lock`
> → **0 匹配**；`uv.lock` 的唯一变化是 `campaignlab` 的 `source` 由 `{ virtual = "." }`
> 变为 `{ editable = "." }`（编排器复跑 `git diff --numstat -- uv.lock` = `1 1`）。
> **裁定**：Q7 的意图（删 `[tool.uv] package = false` 使 `campaignlab` 可导入、gate 命令不再需要
> `PYTHONPATH=src` 前缀）已达成且经编排器复验 —— `uv run --no-sync python -c "import campaignlab"`
> rc=0 并解析到 `src/campaignlab/__init__.py`。**AC-035「锁与运行环境清楚可复现」的判定口径为
> `uv lock --check` rc=0 ＋ `uv sync` 能从锁重建环境**，不以「hatchling 是否出现在锁内」为判据。
> 锁文件不含 build-backend 属 uv 的设计，不构成缺陷。
>
> **③ S2 上报的 Q2（库文件路径约定）、Q4（`downgrade base` 后 `alembic_version` 空表残留）、
> Q5（`doctor` gate 在 S2 时点必然 rc=1）三条，已统一裁定入
> [`ADR-005` §2.4](../../docs/decisions/ADR-005-problem-type-and-runtime-defaults.md)。**
> 要点：**库文件固定 `<data_dir>/state/campaignlab.db`**；解析逻辑必须**单一来源**落在
> `src/campaignlab/infra/db/paths.py`，`migrations/env.py` 与 S3 的 `engine.py::make_engine`
> 都 import 它，S3 须附「alembic 侧解析 == 运行期解析」的断言测试；
> 「完整可逆」= 业务表 0 张 + 仅剩空的 `alembic_version`（不计入 28 表分母、不算额外表）；
> `doctor` gate 归 **S3**，S2 不记红。
>
> **④ S2 自报的一次越界已自证复原**：探测 alembic 默认模板时 `alembic init /tmp/...` 在仓库根
> 生成了 `alembic.ini`（不在 scope_allow），同脚本内已 `unlink`。编排器独立复核：
> 仓库根 `alembic.ini` **不存在**；`git ls-files --others --exclude-standard` 中唯一的
> `alembic.ini` 是 `migrations/alembic.ini`（在 scope 内）；未跟踪且未被忽略的 `*.db` = **0**、
> 已跟踪 `*.db` = **0**（仓库内 16 个 `*.db` 全在 `.mypy_cache/3.14/`，被 gitignore 覆盖）。
> 越界已闭合，不计缺陷。
>
> **⑤ 本文件自检 §8 的 C1（`wc -l` = 117）与 C2（48 files）继续失效**：本文件因历次追注
> 已增长，ruff 分母亦随并行 lane 漂移。两者一律以 `state.json →
> resume.self_check_gates_rc0.counts` 为权威，禁写死（依 D-006 / D-012 / D-014）。

## 9. Round 5 编排器追注（S3c 回收裁定 · 纯增量；§1–§8 各历史行一字未改）

**依据**：S lane（Hilbert / `qwen3.8-max`）S3c 交付回报的 Q1–Q9，编排器独立复验后逐条裁定。
本节与 `orchestrator/defects/D-025.md`、`state.json → resume.round5_adjudications`（A39–A48）同一次提交（手册 §15.9）。

### 9.1 Q1 · §5 V1 行的期望指纹已失效 → 立 D-025，判据改指 state.json

§5 V1 行（第 94 行）写死期望 `01bd28f0772f506e 443552`。编排器实测活契约
`contracts/openapi.json` = **`592571099d638251` / 443309 B**，与 `M0-02.slice.json → source.openapi`、
`state.json → counts.live_openapi_*` **三方一致**；写死值是 CR-002 重切前的旧指纹。
§7 追注（140–154 行）已声明「文档内禁写死」，但 V1 行未同步更正 → 记 **D-025**。

**裁定**：V1 的判据自本节起为 `state.json → resume.self_check_gates_rc0.counts.live_openapi_sha16 / .live_openapi_bytes`；
第 94 行原文字节保留不改写。S5 采集 V1 时按此判据，**禁**引用行内写死值。

### 9.2 Q2 · `api/deps.py` 四个提供器的装配位 → 归 S3d，写集扩围

实测 `deps.py`：`get_session_service` / `get_health_service` / `get_workspace_service` / `require_session`
四个函数体一律 `raise NotImplementedError`（文件内 `NotImplementedError` 出现 5 次 = 4 处真 raise + 1 处 docstring 提及）；
三个 Protocol 中 `HealthService.snapshot() -> Health` 已声明，`SessionService` / `WorkspaceService` 为**空端口**。
S3c 未 stub 假实现、未编造数据，处置正确。

**裁定**：
1. `src/campaignlab/api/deps.py` **纳入 S3d 写集**（R4-1 / R5-1 原未列，本节扩围）。S3d 负责
   ① 用真实装配替换四个 `NotImplementedError` 函数体；② 按 `application/*` 实现类的真实公开方法面
   补全三个 Protocol 成员（结构化子类型）。
2. **禁改 `deps.py` 任何已冻结的公开签名与 Protocol 类名**：`get_config` / `get_clock` /
   `require_session(request: Request) -> Session` / `HealthService.snapshot()` 逐字保持。
3. `HealthService.snapshot() -> Health` **追认为冻结接口**。
4. S3b 只读消费补全后的端口（见 §9.3 的串行裁定）。

### 9.3 R5-3 · 「S3d ∥ S3b 并行」裁定作废 → 改为 S3d → S3b 串行（编排器自我更正）

R5-2（`s3_split_ruling_v3.serial_ordering_correction`）判定 Round 6 可「S3d ∥ S3b 并行」，
理由是「写集不相交且两者对 S3c 均为只读依赖」。**该判定再次不成立**，本节更正（原文字节保留）：

- 依 §9.2，S3d 的写集**含 `api/deps.py`**；S3b 的 `api/session.py` / `api/workspaces.py` 必须
  `from campaignlab.api.deps import ...` 并调用 `svc.<method>()`。
- 当前 `SessionService` / `WorkspaceService` 是**空端口** → S3b 若与 S3d 并行：
  ① mypy 对 `svc.exchange(...)` 一类调用**必然报错**（Protocol 无该成员）；
  ② 运行期 `Depends(get_session_service)` 抛 `NotImplementedError` → S3b 的用例**不可能转绿**。
- 即 S3b 对 S3d 存在**编译期 + 运行期单向依赖**，命中 PRE-4 判据「写集不相交 **且** 无编译期/运行期
  单向依赖，二者缺一即串行」的**串行侧**。R5-2 只核了「写集」与「被依赖模块是否存在」，
  漏核「被依赖符号是否已具备**可用成员面**」。

**裁定**：`S3c(R5，已交付) → S3d(R6) → S3b(R7) → S4(R8) → S5(R8/R9)`。
Round 6 的第二条 lane 改为 **D-016 批次 4 补卡（`qwen3.8-flash`，3 张：M4-P01 / M5-01 / M5-02）**，
与 S3d 写集完全不相交（`orchestrator/tasks/*.md` vs `src/campaignlab/**`）且无任何依赖。
M0-04/S2 的前置仍是「S3c 与 S3d 均已交付并入库」，达成时点为 R6 末。

**新增判据 PRE-5**：并行派单前必须**实测**被依赖模块的成员面可用性 —— Protocol/ABC 是否为空、
目标函数体是否 `NotImplementedError` / `pass` / `raise NotImplemented`；凡空端口或 NotImplemented 一律判**串行**。
（同类错误第三次：R5-1 漏核 import 依赖 → R5-2 更正；R5-2 漏核空端口 → 本节更正。）

### 9.4 Q3 · `AppIdentity` 归属 → 追认落 `config.py`

§6（114 行）把 `AppIdentity` 列在 `application/session_service.py`，§2（58 行）又说它由
`config.py::resolve_local_identity()` 产出，两处冲突。S3c 定义在 `config.py`
（实测 `hasattr(config, 'AppIdentity') = True`、`hasattr(api.common, 'AppIdentity') = False`）。

**裁定：追认 `config.py` 为 `AppIdentity` 的唯一定义处**（它是 `resolve_local_identity` 的返回类型）。
S3d **必须** `from campaignlab.config import AppIdentity`，**禁**在 `application/session_service.py` 另建同名类。
§6 第 114 行原文保留不改写，以本节为准。

### 9.5 Q4 · `Role` 不下沉 → 维持 `api/common.py` 权威 + `TYPE_CHECKING` 引用

`config.py` 用 `if TYPE_CHECKING: from campaignlab.api.common import Role`，运行期不产生 `config → api` 导入边。
**裁定：维持现状，不把 `Role` 下沉到 `domain/values.py`** —— 下沉会改动 §6 对 `values.py` 的冻结符号清单
并要求 `api/common.py` 增 re-export，属扩大冻结面变更；收益（消一条 TYPE_CHECKING 边）不抵成本。

### 9.6 Q5 · 「公开符号集相同」口径 → 认可「差集只含失效导入绑定即通过」

实测（编排器亲算）：`common.__all__` 51 → 51 **逐字同序相同**、`set_diff = []`；`dir()` 私有名 17 → 17 差集空；
`dir()` 公开名 91 → 89，差集 = `{ClassVar, uuid}`（stdlib/typing 的**导入绑定**，搬移后不再被引用、
由 ruff F401 移除，且不在 `__all__` 内）。另以 `git show HEAD:` 取旧版做**文本级**比对：
顶层声明 77 → 53，`decls_only_in_CUR = []`（无任何新增声明），`decls_only_in_HEAD` 24 项全部是被搬走的
`DomainError` 系与注册表构件；`common.py` 内定义形态正则命中 **0**；`errors.__all__` 17 项
`common.X is errors.X` 全 True；`ids.__all__` 5 项中 `RESOURCE_ID_PATTERN` identity=True，
其余 4 项（`RESOURCE_ID_RE` / `is_resource_id` / `new_request_id` / `new_resource_id`）是 `ids.py`
**新增的便捷封装**、HEAD 版 `common.py` 从未有过（故 `decls_only_in_CUR = []` 不受影响）。

**裁定：搬移不是复制，成立**；**禁**用 `# noqa: F401` 把失效导入留成死导入来凑 `dir()` 字面相等。

### 9.7 Q6 · 两条归属不明的改动 → 编排器认领（非 lane 越界）

`orchestrator/defects/D-022.md` 与 `orchestrator/handoff/D-016-batch3-context.md` 的改动是
**编排器自身的治理编辑**（D-022 §5 并入 `SNAPSHOT_SUPERSEDED`；批次3 context §10 两处自我更正），
不属任何 lane 写集。已随**提交 A（`71f9644`）**入库，未误归 S3c。

### 9.8 Q7 · doctor 的 WARN/FAIL 语义 → 追认

**裁定：追认 S3c 的口径** —— FAIL 只给「真的坏了」（契约读不到、非回环绑定、数据目录不可写、
`integrity_check` / `foreign_key_check` 不过、已迁移但 revision ≠ head）→ rc=1；
库未迁移 / worker 未装配 / 端口被占 → WARN，不改 rc。
理由：若把「未迁移」判 FAIL，则任何全新检出上 `python -m campaignlab doctor` 恒 rc=1，
本片出口条件（gate7 由 rc=1 → rc=0）在结构上不可达。
编排器实测：`uv run --no-sync python -m campaignlab doctor` → **rc=0**，`PASS=2 WARN=3 FAIL=0 RESULT=DEGRADED`
（三条 WARN = `data_dir` / `database` 未迁移 / `worker` 未装配，后两条属 S3d）。

### 9.9 Q8 · `ruff B008` → 统一走 `# noqa: B008`，**不**改 `pyproject.toml`

§1 冻结签名 `svc: HealthService = Depends(get_health_service)` 与 B008（禁在参数默认值调用函数）直接冲突。
**裁定：S3b / S4 的 5 个路由统一在该行加 `# noqa: B008` + 一行说明**；
**不**在 `pyproject.toml` 加 `extend-per-file-ignores` —— 后者会全局放宽该目录 lint 面，影响半径大于收益。
`api/health.py` 现有 1 处 noqa 追认合规。

### 9.10 Q9 · `serve` 的入口令牌 WARN → 由 S3d 落地时移除

`cmd_serve` 现打印 `WARN 会话服务未装配（属 M0-02/S3d）：/session/exchange 暂不可用`，未伪造令牌，处置正确。
**裁定：该 WARN 由 S3d 装配 `SessionTokenStore` 后移除**，S3c 侧不 stub；已列入 S3d 派单文出口条件。

### 9.11 编排器独立复验结论（本次亲自实测，**非采信 lane 自报**）

| # | 命令（cwd = 仓库根 `/home/szf/dev/CampaignLab`） | 实测 rc | 实测输出 |
|---|---|---|---|
| 1 | `uv run --no-sync python -m campaignlab doctor` | **0** | `PASS=2 WARN=3 FAIL=0 RESULT=DEGRADED`（出口条件 1→0 达成） |
| 2 | `uv run --no-sync pytest -q` | **0** | `166 passed, 1 warning`（既有 110 一个不少 + 新增 56） |
| 3 | `uv run --no-sync pytest -q tests/unit/test_task_cards.py tests/unit/test_task_card_narrative.py tests/unit/test_state_ledger.py` | **0** | `18 passed` |
| 4 | `uv run --no-sync mypy` | **0** | `Success: no issues found in 39 source files`（22 → 39） |
| 5 | `uv run --no-sync ruff check .` | **0** | `All checks passed!` |
| 6 | `uv run --no-sync ruff format --check .` | **0** | `127 files already formatted`（恒等式 tracked 110 + untracked 17 == 127 成立） |
| 7 | `python3 scripts/check_contracts.py check` | **0** | `CONTRACT CHECK PASS 登记项=13 实测差异=13` |
| 8 | `git status --porcelain spec/ \| wc -l` | **0** | `0`（spec 一字节未动） |
| 9 | `cd web && npm run test` | **0** | `Test Files 7 passed (7)`、`Tests 104 passed (104)` |
| 10 | registry ↔ `API.md` 第 22–29 行第 2 列（以 `、` 分隔） | **0** | 20 码三方逐字同序 `API.md == PROBLEM_CODES == registry.codes`，双向差集空 |
| 11 | `grep -rnE '^[[:space:]]*(port\|target)[[:space:]]*:.*300[012]' web/*.config.*`（D-024 的 G6a） | **1** | 无匹配（期望） |

**行数口径**：一律 `wc -l`；`len(split("\n"))` = `wc -l` + 1（文件均以换行结尾），差 1 属正常（手册 §15.10）。
S3c 交付 19 个文件的 `wc -l` 逐个复核与 lane 自报**全等**（含 `cli.py` = 337，早前交接摘要误记 332，以本表为准）。

_追注时间：2026-11-13T08:58:09+08:00（编排器 O lane）_
