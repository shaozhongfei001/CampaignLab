# M1-01 设计 · 三格式接入与映射（归一化模型与统一规范校验）

> 本文 ＝ `M1-01/S1`（纯设计棒）的**唯一**交付件：零代码 / 零测试 / 零证据。
> 公共纪律见 `orchestrator/handoff/LANE-COMMON.md`；权威条款见 `docs/delivery/LONG-HORIZON-ORCHESTRATION.md` v1.7。
> 冲突时**手册胜**、其次派单文 `orchestrator/handoff/R19-lane-M1-01-S1.md`、再次本文与任务卡 `orchestrator/tasks/M1-01.md`。
> 体例范本 ＝ `orchestrator/handoff/M2-01-design.md`（章节骨架同构）；`路径:符号,符号,…` 的 TODO 体例 ＝ `orchestrator/handoff/M0-04-design.md` §9。
> **append-only 纪律**：本文 §0–§13 为 S1 冻结件，后续编排器裁定一律以 **§14 追记**形式增量写入，禁回头改写 §0–§13 的任何一行。
> 本文是 S2–S8 七棒的**牢笼与地图**：flash 棒只允许在本文 §11 划定的文件与符号内工作，遇设计外问题必须回报（手册 §6.4）。

## 0. 身份与锚（A261：一律以 sha 为锚，禁写 tag；PRE-38：本文一切判据的适用时点见本段末行）

| 项 | 值（本文落盘时点在 WSL 仓库根实测） |
|---|---|
| 分支 | `m0-framework` |
| 基线 HEAD（短 / 全） | `be2b50b` / `be2b50bc35a59175aaa46d198e9f7c2e28c7a2bc`（A269 预裁：派单文写的 `bd7f89c` 已被编排器自身的 predispatch 纯文档提交取代） |
| 任务 / 子任务 / lane 双键 | `M1-01` / **S1** / (`lane`=`S1`, `task`=`M1-01`)（PRE-31：禁与 `R13-lane-Z-M2-01-S1.md` 混用） |
| 契约切片 | `orchestrator/handoff/M1-01.slice.json` ＝ 2876 行 / 60641 B / sha256[:12] `eadbd88e4ef7`；`spec_version` 实测 **1.0.1** |
| 活契约 | `contracts/openapi.json` ＝ 16747 行 / 443309 B / sha256[:16] `592571099d638251`（与切片 `source.openapi` 逐字一致） |
| 任务卡 | `orchestrator/tasks/M1-01.md` ＝ 70 行 / 13420 B / sha256[:12] `b18813bd6dd1` |
| 冻结面（本文引用且**一字不改**） | `api/common.py`=`b2908617d193` · `api/activities.py`=`3865f3eb6b3c` · `api/rules.py`=`eac1377a4b72` · `api/jobs.py`=`e9b575602e56` · `tests/api/activities/__init__.py`=`8ccc54fe0ab9`（PRE-40 重定基后的权威值） |
| 适用时点 | **M1-01/S1 交付时点 · HEAD `be2b50b` · 同任务无在飞棒**；并行棒 `M2-01/S6`（写集 `tests/api/activities/**`）与本棒写权面不相交（PRE-5 三判据）。禁跨批复用本文读数 |

**本文引用的仓内既有符号一律做过实存对撞**（`inspect` / `typing.get_args` / `model_fields` / `grep -n`），
实测结论写在引用处；本文**新立**的符号一律显式标注「待创建 ＋ 由哪一棒创建」（FU-58 口径）。
**禁写死任何计数**：`__all__` 项数、用例数、分母一律实取（A115 / R8-1 / R12-4）。

## 1. 接口签名（6 个 operationId；函数名与 operationId 逐字对应，装饰器必须显式给 `operation_id`）

**全体 6 个 op 的公共约定**（逐 op 不再重复；真值来源＝切片 `operations.<opId>.operation`，本文实测 6 个 op
**均**声明「1 个 2xx + 11 个 Problem 形」共 **12** 个响应，Problem 形状态码集合与
`src/campaignlab/api/session.py::PROBLEM_STATUSES` 实测值 `(400, 401, 403, 404, 409, 412, 413, 422, 428, 429, 500)` 逐字相同）：

- 落点 ＝ **新建** `src/campaignlab/api/imports.py`（S5）；`router = APIRouter(prefix=API_PREFIX, tags=["imports"])`
  （体例逐字对齐实测的 `api/jobs.py:88` 与 `api/activities.py:64`；`API_PREFIX` 实存于 `campaignlab.config.__all__`）。
- 装饰器一律 `responses=declared_responses(<2xx>)`，`declared_responses` 与 `JSON_MEDIA_TYPE` **均 import 自
  `campaignlab.api.session`**（实测签名 `declared_responses(success_status: int) -> dict[int | str, dict[str, Any]]`；
  体例＝`api/jobs.py:70`）。A95：状态码集合的唯一权威是装饰器的 `declared_responses()`，测试侧只拿切片对撞，禁另立清单。
- 路由体只做「解析 → 调 service → 组装响应」，**禁写 SQL**（`framework/PYTHON.md` 第 5 行「服务层应用事务，不在路由里直接写 SQL」）。
- `actor: Session = Depends(require_session)` · `clock: Clock = Depends(get_clock)` ·
  `svc: ImportService = Depends(get_import_service)`（三个提供器中 `require_session` / `get_clock` **实存**于
  `api/deps.py.__all__`；`get_import_service` 与 `ImportService` 为**待创建**，见 §11.8 写权缺口）。
  **禁用系统当前时间**：一切时刻经注入的 `Clock`（`campaignlab.clock.__all__` 实测含 `Clock` / `FixedClock` / `SystemClock` / `ensure_utc`）。
- 成功响应一律 `Response(content=<dto>.model_dump_json(), status_code=<2xx>, media_type=JSON_MEDIA_TYPE, headers={...})`；
  `validateImport` 的 202 一律走 **既有** `api/common.py::accepted_response(job, *, location, request_id, extra_headers=None)`
  （实测签名如左），**禁重写队列**（卡片 gate `M1-01.md:18`）。
- 错误路径一律 `except DomainError as exc: return problem_response(exc, request_id=request_id)`，
  `request_id = request_id_of(request)`（两者均实存于 `api/common.py`）；**禁**在路由里现编 `title`
  （`title` 由 `domain/errors.py::PROBLEM_CODES` 的第 3 元固定，ADR-005 §2.2）。
- 路径参数一律 `workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN)`，`import_id` 同形
  （真值来源：6 个 op 的 `operation.parameters[*].schema`，实测三者的 `minLength=1` / `maxLength=96` /
  `pattern="^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$"` 逐字相同；`RESOURCE_ID_PATTERN` 实存于 `api/common.py.__all__`）。
- `Idempotency-Key`（4 个写 op 均 `required=true`，实测 `minLength=8` / `maxLength=128`）：
  `idempotency_key: str = Header(alias=IDEMPOTENCY_KEY_HEADER, min_length=8, max_length=128)`，
  函数体第一句 `key = validate_idempotency_key(idempotency_key)`（两个符号均实存于 `api/common.py.__all__`）。
- `If-Match`（3 个 op 有：`attachImportFile` / `configureImport` / `validateImport`）：**必须声明为可选形参**（A228）——
  `if_match: str | None = Header(alias="If-Match", default=None, min_length=3, max_length=32, pattern=IF_MATCH_PATTERN)`，
  其中 `IF_MATCH_PATTERN` **单源 import 自 `api/common.py`**（A271 / FU-59 / PRE-40；实测定义点
  `api/common.py:190`、实测值 `'^"[1-9][0-9]*"$'`、实测已在 `__all__` 内）。**禁内联第二份正则**：守护
  `tests/unit/test_if_match_pattern_single_source.py` 的判据④（`test_all_common_surface_pins_agree_with_runtime` 同族元守护）
  与 `test_literal_appears_exactly_once_in_scope_python` 会当场判红。
  ⚠ 切片把 `If-Match` 声明为 `required: true`，**实现侧的可选声明不是契约偏离**：A228 已裁——照抄成必填会让缺头
  在进入函数体前被判 422，契约要求的 **428 `PRECONDITION_REQUIRED`** 结构上永不可达。
- **FU-64**：`M2-01-design.md:215` 那句「`IF_MATCH_PATTERN` 不在 `__all__` 里」**已失真，禁引用、禁复述**；
  权威读法一律以运行期实测为准（本轮实测：`IF_MATCH_PATTERN in common.__all__` → `True`，`len(common.__all__)` → **80**）。

### 1.1 逐 op 签名（method / path 一律实取自切片 `operations.<opId>.method` 与 `.path`，禁凭摘要取值）

| op | method ＋ path（切片实取） | 2xx | 函数名 | 形参面（切片实取的参数集） |
|---|---|---|---|---|
| `createImport` | `POST /workspaces/{workspace_id}/imports` | **201** | `create_import` | `workspace_id`(path,必) · `Idempotency-Key`(header,必)；body `multipart/form-data` → `Upload`；**无 If-Match** |
| `attachImportFile` | `POST /workspaces/{workspace_id}/imports/{import_id}/files` | **200** | `attach_import_file` | `workspace_id`(path,必) · `import_id`(path,必) · `Idempotency-Key`(header,必) · `If-Match`(header,必)；body `multipart/form-data` → `AttachFile` |
| `configureImport` | `PUT /workspaces/{workspace_id}/imports/{import_id}/mapping` | **200** | `configure_import` | 同上 4 参数；body `application/json` → `ImportConfigure` |
| `validateImport` | `POST /workspaces/{workspace_id}/imports/{import_id}/validate` | **202** | `validate_import` | 同上 4 参数；**无 requestBody**（切片实测无该键）；202 响应头实测 `X-Request-Id` · `Location` · `ETag`，body `Job` |
| `getImport` | `GET /workspaces/{workspace_id}/imports/{import_id}` | **200** | `get_import` | `workspace_id`(path,必) · `import_id`(path,必)；无 body / 无 Idempotency-Key / 无 If-Match |
| `listImports` | `GET /workspaces/{workspace_id}/imports` | **200** | `list_imports` | `workspace_id`(path,必) · `cursor`(query,选,1–300) · `limit`(query,选,int 1–100,default 25) · `q`(query,选,1–100) · `status`(query,选,1–60)；body `ImportPage` |

签名骨架（以 `attachImportFile` 为例，其余 5 个按 §1.1 表机械替换装饰器与形参）：

```python
@router.post(
    "/workspaces/{workspace_id}/imports/{import_id}/files",
    operation_id="attachImportFile",
    responses=declared_responses(200),
)
async def attach_import_file(
    request: Request,
    workspace_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    import_id: str = Path(min_length=1, max_length=96, pattern=RESOURCE_ID_PATTERN),
    idempotency_key: str = Header(alias=IDEMPOTENCY_KEY_HEADER, min_length=8, max_length=128),
    if_match: str | None = Header(
        alias="If-Match", default=None, min_length=3, max_length=32, pattern=IF_MATCH_PATTERN
    ),
    actor: Session = Depends(require_session),  # noqa: B008
    clock: Clock = Depends(get_clock),  # noqa: B008
    svc: ImportService = Depends(get_import_service),  # noqa: B008
) -> Response:
```

### 1.2 两类正文的解析口径（**multipart 与 JSON 走两条不同的通道，禁混用**）

- **`configureImport`（`application/json` → `ImportConfigure`）**：与既有 5 个 JSON 写 op 逐字同构——
  `body = await read_body_within_limit(request, max_bytes=get_config(request).max_json_body_bytes)`
  → `payload = parse_json_body(body, request.headers.get("content-type"), ImportConfigure)`
  （`read_body_within_limit` 实存于 `api/common.py.__all__`、`get_config` 实存于 `api/deps.py.__all__`；
  `parse_json_body(raw: bytes, content_type: str | None, model: type[ModelT]) -> ModelT` 实存于 `api/session.py`，
  **不在** `session.__all__`（实测 `session.__all__ == ['exchange_session','get_session','router']`）⇒ 与
  `declared_responses` / `JSON_MEDIA_TYPE` / `validation_issues` 同一处置：按既有 `api/jobs.py:70` 的直接 import 体例取用，
  **禁**为此改 `api/session.py.__all__`（该文件不在本卡 `scope_allow`）。
  上限 ＝ `AppConfig.max_json_body_bytes`（实测 `config.MAX_JSON_BODY_BYTES = 1_048_576`，即卡片 U-3 已裁 D16 表的 **1 MiB「仅 JSON 请求正文」**行）→ 413 `INPUT_TOO_LARGE`。
- **`createImport` / `attachImportFile`（`multipart/form-data`）**：**禁**用 `read_body_within_limit`
  （它把整个正文读进内存 `bytearray`，对 8 MiB / 64 MiB 的文件入口等于把上限变成内存放大攻击面），
  也**禁**用 FastAPI 的 `File(...)` / `Form(...)` 自动形参（形参层解析发生在函数体之前 ⇒ 413 的判定会晚于
  Starlette 把整个上传体 spool 落盘，AC-005「不留半成品」无法保证）。**冻结做法**：路由签名只收 `request: Request`，
  正文由 `api/imports.py` 的私有协程 `async def _read_form_within_limit(request: Request, *, max_bytes: int) -> FormData`
  （**待创建，S5**）三段处理：
  1. `Content-Length` 预判（体例＝`api/common.py::read_body_within_limit` 的两阶段口径原文「只信 Content-Length 可被伪造」）：
     非整数 → 400 `BAD_REQUEST`；`> max_bytes` → **413 `INPUT_TOO_LARGE`**（此时尚未落任何字节）。
  2. `form = await request.form()`；`form.get("file")` 不是上传件 → 422 `VALIDATION_ERROR`，`issues[0].location="/file"`。
  3. 按 `UPLOAD_CHUNK_BYTES`（**待创建，S2**，`infra/files.py`，取 `1048576`，与 `artifacts.hash_file` 的默认
     `chunk_size` 实测同值）流式拷进 `AttemptStage`，**边拷边累计**；累计 `> max_bytes` → `stage.discard()` ＋
     **413 `INPUT_TOO_LARGE`**（`issues[0].location="/file"`）⇒ 磁盘上不留任何半成品（AC-005）。
  `max_bytes` 的取值见 §5.2 的三上限表（8 MiB / 64 MiB，按 `format` 分派）。
  文本字段（`table_name` / `bank_id` / `snapshot_code` / `format` / `correction_of`）从 `form` 取出后交
  `UploadFields.model_validate(...)` 做严格校验（见 §2.3），违例 → 422 `VALIDATION_ERROR` ＋ `validation_issues(exc)`。

### 1.3 逐 op 的 2xx 与错误码映射（可达面见 §8；本段只冻结「哪个错误由谁抛」）

| op | 2xx 组装 | 主要错误来源（码名一律实取自 `domain/errors.py::PROBLEM_CODES`，本文**零发明** code） |
|---|---|---|
| `createImport` | 201 ＋ `Response(headers={"ETag": etag(dto.revision), "X-Request-Id": request_id})`，body `Import` | 400 `BAD_REQUEST`（Content-Type 非 multipart / Content-Length 非法）·401 `SESSION_EXPIRED`·403 `ORIGIN_DENIED`/`ACCESS_DENIED`·404 `RESOURCE_NOT_FOUND`（工作区不存在或属外）·409 `IDEMPOTENCY_CONFLICT`（同键异摘要）·413 `INPUT_TOO_LARGE`（§5.2）·422 `VALIDATION_ERROR`（`UploadFields` / 幂等键形状 / `format` 不在枚举 / `table_name` 重复）·422 `EVIDENCE_REQUIRED`（`LEGACY_SYNTHETIC_JSON` 的 `synthetic` 非 true、字典缺失）·500 `INTERNAL_ERROR` |
| `attachImportFile` | 200 ＋ 新 `ETag`（`revision+1`），body `Import` | 上列全部（除「工作区不存在」外**加**「`import_id` 不存在或属外 → 404」）＋ 428 `PRECONDITION_REQUIRED`（缺 `If-Match`）＋ 412 `REVISION_CONFLICT`（不匹配）＋ 409 `STATE_CONFLICT`（`VALIDATING`/`PUBLISHING`/`PUBLISHED` 期间文件只读，§3.4） |
| `configureImport` | 200 ＋ 新 `ETag`，body `Import` | 同 `attachImportFile`，另加 422 `VALIDATION_ERROR`（映射引用不存在的列 / `long_columns` 与 `layout` 矛盾，§5.1 N7–N9）与 409 `VERSION_MISMATCH`（同 `bank_id` 同内容不同摘要，§4.7） |
| `validateImport` | **202** ＋ `accepted_response(job, location=..., request_id=..., extra_headers={"ETag": etag(...)})`，body `Job` | 同 `configureImport`，另加 429 `JOB_CAPACITY`（`worker/capacity.py::check_capacity` 既有面，**只调用禁改**）与 409 `STATE_CONFLICT`（源状态不在 `IMPORT_TRANSITIONS` 的 I4 `sources` 内） |
| `getImport` | 200 ＋ `ETag`，body `Import` | 401·403·404·500（只读，无 4xx 写侧码） |
| `listImports` | 200，body `ImportPage`（`items` 0–100 ＋ `next_cursor` 可空） | 400 `BAD_CURSOR`（游标签名/形状不符）·401·403·404（工作区不存在或属外）·422 `VALIDATION_ERROR`（`limit`/`q`/`status` 形状、`status` 不在 `IMPORT_STATES` 白名单）·500 |

- `status` 过滤白名单 ＝ `IMPORT_STATES`（**待创建，S2**，`domain/ingest/states.py`，取值一律
  `tuple(get_args(ImportState))` 从契约 DTO 反推，**禁抄字面量**；体例＝实测的 `worker/states.py::JOB_STATES` 与
  `domain/activity/states.py::ACTIVITY_STATES`）。
- `q` 的查找面（`architecture/API.md`「资源查询」行原文「q 对名称和公开编号按 NFKC casefold 查找」）⇒ 本卡冻结为
  `imports.bank_id` · `imports.snapshot_code` · `imports.id` 三列（`imports` 表**无** `name` 列，实测 DDL 见 §2.4），
  一律 `NFKC` ＋ `casefold` 后比较。
- 列表排序 ＝ `created_at DESC, id ASC`（`architecture/API.md`「资源查询」行原文「以 created_at DESC、id ASC 稳定排序」）；
  游标编解码复用 `api/common.py::encode_cursor(payload, secret)` / `decode_cursor(cursor, secret)`，
  payload 三段（查询摘要 / 最后排序键 / 作用域）**一律实取** `api/activities.py` 与 `api/workspaces.py` 的既有构造口径，
  禁自拼（A115：禁写死；S5 落地时以 `ruff check --select I --diff` 与既有用例对撞为准）。
## 2. 数据结构（字段级；每行末尾的 `←` 即真值来源切片路径，A171 口径）

**公共约定**（与 `api/common.py` 既有 DTO 同构，禁另立第二套）：一律 `model_config = ConfigDict(extra="forbid")`
（切片侧实测 `Import` / `ImportPage` / `SourceMapping` / `Upload` 的 `additionalProperties` **均为 `false`**）；
字符串用 `StrictStr`、整数用 `StrictInt`、布尔用 `StrictBool`（`framework/PYTHON.md` 第 3 行「Pydantic 拒绝未知字段、
布尔冒充整数、非有限数值和不带偏移的时刻」）；时刻用 `AwareDatetime`；ID 型字段复用 `api/common.py` 的私有别名
`_IdStr` 与既有 `RevisionInt`；可空字段一律显式 `| None`。
**禁新增 `DomainError` 子类**：`tests/unit/test_domain_errors.py:109` 实测钉死
`assert len(expected) == 13, "DomainError 子类必须是 13 个（R5-1 硬规则）"`（运行期实测子类 14 个，其中
`ArtifactCommitFailed` 是 `worker/errors.py` 的再导出、不在该 dict 内）⇒ 本卡一切错误一律复用既有 14 个子类，
业务细分只走 `Issue.code`（§5.1）与 `detail`。

### 2.1 导入族（新建于 `api/common.py`，方案 A；全部**待创建，S2**）

| DTO / 别名 | 字段（`!`＝必填，`?`＝可空） | 真值来源（← 切片路径） |
|---|---|---|
| `ImportFormat` | `Literal["LEGACY_SYNTHETIC_JSON","SOURCE_JSON","SOURCE_CSV"]` | ← `operations.getImport.schemas.Import.properties.format.enum`（与 `ddl.imports` 的 `CHECK(format IN (...))` 逐字一致） |
| `ImportState` | `Literal["RECEIVED","CONFIGURED","VALIDATING","VALID","INVALID","PUBLISHING","PUBLISHED"]` | ← `operations.getImport.schemas.Import.properties.state.enum`（与 `ddl.imports` 的 `CHECK(state IN (...))` 逐字一致，**7 态**） |
| `IMPORT_FORMATS` / `IMPORT_STATES` | `Final[tuple[str, ...]] = tuple(get_args(<Literal>))` | ← 同上两行；体例＝`worker/states.py::JOB_STATES`（禁抄字面量） |
| `ImportFile` | `id!`(ID 正则) · `table_name!`(1–120) · `label!`(1–180) · `sha256!`(`^[0-9a-f]{64}$`) · `size_bytes!`(StrictInt 0–9000000000000) | ← `operations.createImport.schemas.ImportFile`（`required` 实测 5 项全在） |
| `Import` | `id!` · `revision!`(RevisionInt) · `created_at!`(date-time 带偏移) · `bank_id!` · `snapshot_code!` · `format!`(enum) · `state!`(enum) · `files!`(1–32 个 `ImportFile`) · `mapping!`(`SourceMapping`\|null) · `issues!`(0–1000 个 `Issue`) · `snapshot_id?` · `correction_of?` · `validation_digest?`(64hex\|null) · `job_id?` | ← `operations.getImport.schemas.Import`（`required` 实测 **14** 项，含 4 个可空项 ⇒ 一律「必填但可为 null」，禁给默认值） |
| `ImportPage` | `items!`(0–100 个 `Import`) · `next_cursor!`(1–300\|null) | ← `operations.listImports.schemas.ImportPage`（与既有 `WorkspacePage`/`JobPage` 同构，A91 追加口径） |
| `ImportConfigure` | `mapping!`(`SourceMapping`) | ← `operations.configureImport.schemas.ImportConfigure`（`required` 实测只有 `mapping`） |

- `Import.files` 的 `minItems=1` 是**契约硬约束**：`createImport` 自带一个上传件 ⇒ 建对象即满足；
  `import_files` 表侧无 `minItems` 概念，故「至少一个文件」由**路由/service 层**保证，禁靠 DDL 兜。
- `Issue` **复用既有** `api/common.py::Issue`（实测 `model_fields` ＝ `code` / `location` / `message` / `severity`，
  与切片 `operations.validateImport.schemas.Issue` 的 4 个 `required` 逐字同名）；**禁另立第二份**。
  `severity` 的取值集合一律以 `typing.get_args(Issue.model_fields["severity"].annotation)` **实取**并与切片 enum
  `["ERROR","WARNING","INFO"]` 对撞（A115），本文不写死其声明形态。
- `Job` / `ObjectRef` / `Problem` **均已实存**于 `api/common.py`（实测 `Job.model_fields` 13 项、`kind` 的 enum 实测含
  `VALIDATE_IMPORT` 与 `PUBLISH_IMPORT`）⇒ `validateImport` 的 202 直接复用，**零新 DTO**。

### 2.2 映射族（新建于 `api/common.py`；全部**待创建，S2**）

| DTO / 别名 | 字段 | 真值来源 |
|---|---|---|
| `MappingLayout` | `Literal["wide","long"]` | ← `operations.configureImport.schemas.SourceMapping.properties.layout.enum` |
| `SourceMoneyUnit` | `Literal["CNY_YUAN","CNY_FEN"]` | ← `...SourceMapping.properties.source_money_unit.enum` |
| `DedupMode` | `Literal["SYNTHETIC_INTERVAL","DISTINCT_CUSTOMER","AGGREGATE_ONLY"]` | ← `...SourceMapping.properties.dedup_mode.enum`（三值的语义原文见 `architecture/DATA.md`「去重和可比性」三条） |
| `LongColumns` | `id!`(1–120) · `metric!`(1–120) · `value!`(1–120) | ← `...SourceMapping.properties.long_columns.anyOf[0]`（实测 `required=["id","metric","value"]`、`additionalProperties=false`） |
| `SourceMapping` | `id!` · `bank_id!` · `layout!` · `entity_table!`(1–120) · `counts_table!`(1–120) · `dimensions!`(`dict[str,StrictStr]`，值 1–120) · `count_fields!`(同形) · `money_fields!`(同形) · `source_money_unit!` · `long_columns!`(`LongColumns`\|null) · `codes!`(`dict[str, dict[str,StrictStr]]`，值 1–120) · `dedup_mode!` | ← `operations.configureImport.schemas.SourceMapping`（`required` 实测 **12** 项全在，`additionalProperties=false`） |

- `SourceMapping` 与既有 `contracts/source-mapping.schema.json`（实测 135 行 / 2734 B / `ab5dddd43f2e`）**同源**；
  S2 必须落一条对撞断言（DTO `model_fields` ↔ 该 schema 的 `properties`/`required`），禁目视。
- **实测的 fixture 映射与 DTO 逐字段吻合**：`spec/CampaignLab-SDD-v1.0/fixtures/banks/map-a.json`
  （65 行 / 1653 B / `f37c009d1f88`）＝ `layout="wide"`、`source_money_unit="CNY_YUAN"`、`long_columns=null`、
  `dedup_mode="SYNTHETIC_INTERVAL"`、`dimensions` 14 键、`count_fields` 9 键、`money_fields` 12 键、
  `codes` 2 组（`channel` 6 项 / `origin` 2 项）；`map-b.json`（69 行 / 1601 B / `2246eae3af23`）＝ `layout="long"`、
  `source_money_unit="CNY_FEN"`、`long_columns={"id":"切片键","metric":"指标码","value":"计数"}`、其余同形。
  ⇒ **14 / 9 / 12 三个键数就是 `dimensions` / `count_fields` / `money_fields` 的规范键分母**，
  与 `architecture/DATA.md`「映射和标准表」的字段表逐字对应（`slices.parquet` 行 14 维度、9 计数、12 金额）。
- **legacy 内嵌映射的键名是 camelCase**（实测 `bank-a.json.mapping` 的键为 `entityTable` / `countsTable` /
  `countFields` / `moneyFields` / `moneyDivisor` / `longColumns`，且 `version` 而非 `id`）⇒ 归一层必须做一次
  **显式键名映射**（§4.2 的 `legacy_mapping_to_source_mapping`），**禁**给 `SourceMapping` 加 alias 生成器
  （`extra="forbid"` ＋ 单一真值来源原则；alias 会让契约对撞测试出现两套键名口径）。

### 2.3 multipart 的字段面（本文新立名；**待创建，S2**，落 `api/common.py`）

| DTO | 字段 | 真值来源 |
|---|---|---|
| `UploadFields` | `table_name!`(1–120) · `bank_id!`(ID 正则) · `snapshot_code!`(ID 正则) · `format!`(`ImportFormat`) · `correction_of?`(ID 正则\|null) | ← `operations.createImport.schemas.Upload`（`required` 实测 `["file","table_name","bank_id","snapshot_code","format"]`，`correction_of` 实测**不在** `required`） |
| `AttachFileFields` | `table_name!`(1–120) | ← `operations.attachImportFile.schemas.AttachFile`（`required` 实测 `["file","table_name"]`） |

**为什么不是 `Upload` / `AttachFile` 两个同名 DTO**：切片里这两个 schema 的 `file` 属性实测为
`{"type":"string","format":"binary"}` —— 二进制面**无法**在纯 pydantic DTO 里表达（写成 `StrictBytes` 就等于强制
把 8 MiB / 64 MiB 的上传体整体读进内存，直接违反 §1.2 的流式口径与 AC-005「不留半成品」）。故本文冻结：
`file` 走 §1.2 的流式通道（不进 DTO），其余文本字段进 `UploadFields` / `AttachFileFields`；
契约对撞测试用**两条**断言覆盖 —— ① DTO `model_fields` ↔ 切片 schema 的 `properties` **去掉 `file`** 后逐字相等；
② 切片侧 `properties.file.format == "binary"` 且 `"file" in required`。此命名与切片的偏离已开 **§12 U-3** 交裁定。

### 2.4 落库映射（列 ↔ DTO；真值来源＝切片 `ddl.*`，与 `contracts/sqlite-v1.sql` 同源）

三张表**已在** `migrations/versions/0001_initial_schema.py` 建好（实测该文件 `:107` `source_mappings`、`:112` `imports`、
`:126` `import_files`；参考 DDL 实测 `contracts/sqlite-v1.sql:50` 起为 `CREATE TABLE imports`）⇒
**本卡零迁移改动**（`migrations/**` 在卡片 `scope_deny` 与派单文 §1.3 硬禁面内）。

- **`imports`**（切片 `ddl.imports` 逐字实测）：`workspace_id`(NOT NULL，FK `workspaces(id)`) · `id` · `bank_id` ·
  `snapshot_code` · `format`(CHECK 3 值) · `state`(CHECK **7** 值) · `mapping_id`(可空) · `validation_digest`(可空) ·
  `issue_json`(**NOT NULL** ＋ `CHECK(json_valid(issue_json))`) · `snapshot_id`(可空) · `correction_of`(可空) ·
  `job_id`(可空) · `revision`(NOT NULL，`CHECK(revision>=1)`) · `created_at`(NOT NULL)；
  `PRIMARY KEY(workspace_id,id)`；`FOREIGN KEY(workspace_id,mapping_id) REFERENCES source_mappings(workspace_id,id)`；
  另有 `snapshot_id` / `correction_of` → `snapshots(workspace_id,id)`、`job_id` → `jobs(workspace_id,id)` 三条复合 FK；表尾 `STRICT`。
  - `issue_json` 是 **NOT NULL** ⇒ `issues` 为空时写 `canonical_json([])`（即字面 `[]`），**禁写 NULL**、禁写 `""`。
  - `Import.mapping` ← `mapping_id` JOIN `source_mappings.content_json` 反序列化；`mapping_id IS NULL` → `None`。
  - `Import.snapshot_id` / `correction_of` / `job_id` 直读同名列（`snapshot_id` 由 **M1-02** 写，本卡只读；
    `job_id` 由 `validateImport` 写，见 §3.2 I4）。
  - `validation_digest` ← 本卡写入（§4.7）；`attachImportFile` / `configureImport` 一律置 `NULL` 并把 `issue_json` 复位为 `[]`（§5.3）。
- **`import_files`**（切片 `ddl.import_files` 逐字实测）：`workspace_id` · `id` · `import_id` · `artifact_id` ·
  `table_name` · `label`；`PRIMARY KEY(workspace_id,id)`、**`UNIQUE(workspace_id,import_id,table_name)`**、
  `FOREIGN KEY(workspace_id,import_id) REFERENCES imports(workspace_id,id)`、
  `FOREIGN KEY(workspace_id,artifact_id) REFERENCES artifacts(workspace_id,id)`；表尾 `STRICT`。
  - ⚠ **`sha256` 与 `size_bytes` 不在本表**：`ImportFile.sha256` / `.size_bytes` 一律经 `artifact_id` JOIN
    `artifacts` 表取（实测 `ArtifactRecord` 的字段面含 `sha256` / `byte_size` / `relative_path` / `kind`）。
    ⇒ `ImportFile.size_bytes` ← `artifacts.byte_size`（**列名与 DTO 字段名不同名，禁抄错**）。
  - ⚠ **本表无 `created_at`** ⇒ `Import.files` 的数组顺序冻结为 `ORDER BY import_files.id ASC`
    （`id` 由 `new_resource_id(IMPORT_FILE_ID_PREFIX)` 单调生成不保证时序，但**保证确定**；契约只要求数组，
    不要求顺序，故取「确定性」而非「时序」，禁改成随机序导致 ETag/摘要抖动）。
  - `UNIQUE(workspace_id,import_id,table_name)` ⇒ 同表名重复 attach 的**物理**兜底；逻辑前置检查在 service
    （422 `VALIDATION_ERROR`，`issues[0].code="DUPLICATE_TABLE_NAME"`、`location="/table_name"`），
    竞态下 DDL 违约一律翻译成**同一个** 422（禁裸抛 500）。
  - `label`：实测 `AttachFile` schema **无** `label` 字段 ⇒ 冻结口径「`label` ＝ 客户端上传件的原始文件名
    （`architecture/DATA.md`「导入通道」与 `OPERATIONS.md:11` 原文『导入使用生成的制品名，用户文件名仅作显示』），
    截断到 180 字符（`ImportFile.label` 的 `maxLength`），空则回落到 `table_name`」。
- **`source_mappings`**（切片 `ddl.source_mappings` 逐字实测）：`workspace_id`(FK `workspaces(id)`) · `id` ·
  `bank_id` · `content_json`(NOT NULL ＋ `CHECK(json_valid(content_json))`) · `digest`(NOT NULL ＋
  `CHECK(length(digest)=64)`) · `created_at`；`PRIMARY KEY(workspace_id,id)`；表尾 `STRICT`。
  - **本表无 `revision` 列** ⇒ 映射的「版本」语义靠**新 ID**：`architecture/DATA.md`「更正和发布边界」段原文
    「每次映射实际变更保存为新映射 ID，老快照仍引用原版」＋ `architecture/DOMAIN.md`「对象与修改」表原文
    「配置内容同 ID 变更要求新 ID」。⇒ `configureImport` **每次**都 INSERT 一行新 `source_mappings`
    （`id = new_resource_id(SOURCE_MAPPING_ID_PREFIX)`）并把 `imports.mapping_id` 指过去，**禁** UPDATE `content_json`。
  - `content_json = canonical_json(SourceMapping.model_dump(mode="json"))`；`digest = sha256(content_json)`
    （64 位小写十六进制，`architecture/DOMAIN.md`「唯一标识和精度」段原文）。
  - `SourceMapping.id` 由**客户端**给（切片 `required` 含 `id`）而 `source_mappings.id` 是主键 ⇒ 冲突处置见 **§12 U-4**。

### 2.5 DTO 落点（本文冻结为**方案 A**；方案 B 的平移映射见 §11.9）

- **方案 A（推荐，A91 同构 append-only）**：§2.1–§2.3 的全部新 DTO / 别名追加进 `src/campaignlab/api/common.py`
  （**纯追加、0 删除行**，A82 处置先例），与既有 `WorkspacePage` / `JobPage` / `Job` / `Issue` / `Problem` 同一份家。理由：
  ① 可直接复用模块内私有别名 `_IdStr` 与既有 `RevisionInt` / `Issue` / `Problem`，不产生第二份定义；
  ② `api/deps.py` 的 `ImportService` Protocol 能正常 import 它们而不与 `api/imports.py` 形成循环导入
  （若 DTO 住在 `api/imports.py`，则 `deps.py → imports.py → deps.py` 成环）；
  ③ 卡片 `public_frozen` 行（`M1-01.md:24`）明写本设计供 **M1-02 / M1-03 / M1-P01** 消费，而 M1-P01 的
  `scope_deny` 必然含 `api/imports.py`（同族先例：M1-01 自己的 `scope_deny` 就显式列了同波下游的
  `api/snapshots.py` / `api/definitions.py` / `api/channels.py` / `api/compare.py`）⇒ DTO 若住在 `api/imports.py`，
  下游**读不到**，只能各抄一份（违反「禁两处各存一份」）。
- **代价（必须同批改，属写权缺口，见 §11.8）**：
  ① `api/common.py.__all__` 需追加新名字（`no_implicit_reexport` 已开 ⇒ 不进 `__all__` 的名字下游 import 会判 mypy 错，
  LANE-COMMON §3.5）；项数**以 `inspect` 实取为准，本文不写死**（本轮实测 `len(common.__all__) == 80`）。
  ② 同族钉桩必须同步：`tests/unit/test_if_match_pattern_single_source.py` 的元判据
  `test_all_common_surface_pins_agree_with_runtime` 用 `ALL_COUNT_PIN_RE` 扫全仓
  `len(<common 别名>.__all__) == <整数>` 形态的钉桩，要求**所有钉桩整数两两相等且等于运行期实测**，
  且钉桩处数 `>= ALL_COUNT_PIN_SITES_FLOOR`（实测常量值 **2**，**禁靠删钉桩变绿**）。
  本轮实测命中 **2 处**：`tests/unit/test_domain_errors.py:176` 与 `:177`（恰等于下界）⇒
  S2 落地时必须把**这两行**同步改成同一实取值（该文件不在本卡 `scope_allow` ⇒ 写权缺口）。
  位点清单**一律用 `all_count_pins(in_scope_sources())` 实取**，禁写死处数。
- **方案 B（零扩围回退）**：DTO 住 `api/imports.py`，`_IdStr` / `RevisionInt` 在该文件内**重新声明**（承认漂移风险），
  `api/deps.py` 的 `ImportService` 签名改用 `if TYPE_CHECKING:` 导入以避免运行期成环，下游 M1-02/M1-03/M1-P01
  改为「按需 import `api/imports.py`」。仅当编排器拒绝方案 A 的写权扩围时启用；两方案的**符号名与字段序完全一致**，
  故 §3–§10 的设计一字不改，§11 的文件级 TODO 按 §11.9 的映射表平移即可。
## 3. 状态机（`imports.state` **7 态**；`TransitionId` 形态对齐 `src/campaignlab/worker/states.py` 的既有体例）

**体例约定（照抄体例、禁 import 该模块）**：`worker/**` 在卡片 `scope_deny` 内，且其
`TransitionId = Literal["T1"…"T9"]`（实测 `typing.get_args` 取值）是作业面的冻结类型，复用会把导入迁移塞进作业的
Literal。故本卡在 **新建** `src/campaignlab/domain/ingest/states.py`（S2）内**同构另立**，字段名与
`worker/states.py::Transition`（实测字段序 `id / sources / target / trigger / spec_ref / guard / transaction /
creates_new_row`）**逐字对齐**，也与已交付的 `domain/activity/states.py::RuleTransition`（实测同 8 字段）同构，
使 Q 判定档能用同一套读法复核三张迁移表：

- `ImportTransitionId = Literal["I1", …, "I7"]`（本卡只注册 I1–I7；I8–I10 属 **M1-02**，见 §3.4 的预留行）
- `IMPORT_STATES: Final[tuple[str, ...]] = tuple(get_args(ImportState))`（**禁抄字面量**；体例＝实测的
  `worker/states.py::JOB_STATES` 与 `domain/activity/states.py::ACTIVITY_STATES`）
- `IMPORT_TERMINAL_STATES: Final[frozenset[str]] = frozenset({"PUBLISHED"})`（体例＝实测
  `domain/activity/states.py::ACTIVITY_TERMINAL_STATES == frozenset({'ARCHIVED'})`）
- 两条纯函数：`assert_import_transition_allowed(source: str | None, target: str, *, trigger: str) -> None` 与
  `is_import_terminal(state: str) -> bool`（签名逐字对齐实测的 `assert_activity_transition_allowed` /
  `is_activity_terminal`，含 keyword-only 的 `trigger`）
- `guard` 是那条 UPDATE 的 WHERE 谓词的**可读镜像**，供测试逐条对照；**运行期只信 `rowcount`**
  （`worker/states.py` 的既有裁定，A232：specific 覆盖 general，本文沿用）
- `creates_new_row` 的语义冻结为「**本迁移是否在 `imports` 表新建行**」（与 `worker/states.py::T9` 同义），
  在**别的**表建行（如 I3 新建 `source_mappings` 行）一律记 `False`

### 3.1 `ImportState` 的定义落点（**实测先例，禁自创**）

`ImportState` / `ImportFormat` / `MappingLayout` / `SourceMoneyUnit` / `DedupMode` 五个 `Literal` 别名
**一律定义在 `domain/ingest/`**，由 `api/common.py` **import 后列入 `__all__`** 再导出给 DTO 用。
实测先例：`api/common.py:50` 原文 `from campaignlab.domain.activity.states import (`，且运行期实测
`common.ActivityStatus is states.ActivityStatus` → `True`、`common.RuleState is states.RuleState` → `True`、
`common.TemplateId is states.TemplateId` → `True` ⇒ **同一对象、单一真值来源**，不是两份定义。
本卡照此办理：`ImportState is domain.ingest.states.ImportState` 必须为 `True`（S2 落一条 `is` 对撞断言）。
依赖方向合法（`api → domain`，`framework/PYTHON.md` 第 3 行「分层保持依赖朝领域内收」）；
**反向（`domain/ingest` import `campaignlab.api`）一律禁止**。

### 3.2 迁移表 I1–I7（逐行；`spec_ref` 一律给到 `spec/CampaignLab-SDD-v1.0/` 下的**行级**出处）

| id | sources | target | trigger | spec_ref | guard（SQL 镜像原文） | transaction | creates_new_row |
|---|---|---|---|---|---|---|---|
| `I1` | `()` | `RECEIVED` | `createImport` 建导入（DDL 无默认值 ⇒ service 显式写） | `architecture/DATA.md:11`「支持状态流 RECEIVED → CONFIGURED → VALIDATING → VALID 或 INVALID → PUBLISHING → PUBLISHED」 | `INSERT INTO imports(…) VALUES(… state='RECEIVED', revision=1, issue_json='[]', validation_digest=NULL …)` | `TX-I1 ImportService.create_import` | **True** |
| `I2` | `(RECEIVED, CONFIGURED, VALID, INVALID)` | `CONFIGURED` | `attachImportFile` 追加/替换文件；「修改文件或映射使此前验证失效并递增 revision」 | `architecture/DATA.md:11` 同句 ＋ 同段「VALIDATING、PUBLISHING 期间文件与映射只读」 | `UPDATE imports SET state='CONFIGURED', validation_digest=NULL, issue_json='[]', revision=revision+1 WHERE workspace_id=:workspace_id AND id=:id AND state IN ('RECEIVED','CONFIGURED','VALID','INVALID') AND revision=:revision` | `TX-I2 ImportService.attach_file` | False |
| `I3` | `(RECEIVED, CONFIGURED, VALID, INVALID)` | `CONFIGURED` | `configureImport`：**INSERT 一行新 `source_mappings`**（新 ID）＋把 `imports.mapping_id` 指过去；同样使旧验证失效 | `architecture/DATA.md`「更正和发布边界」段「每次映射实际变更保存为新映射 ID，老快照仍引用原版」＋ `architecture/DOMAIN.md`「对象与修改」表「配置内容同 ID 变更要求新 ID」 | `UPDATE imports SET mapping_id=:mapping_id, state='CONFIGURED', validation_digest=NULL, issue_json='[]', revision=revision+1 WHERE workspace_id=:workspace_id AND id=:id AND state IN ('RECEIVED','CONFIGURED','VALID','INVALID') AND revision=:revision` | `TX-I3 ImportService.configure_mapping`（同一短事务内先 INSERT `source_mappings`，再 UPDATE `imports`） | False（新建的是 `source_mappings` 行，非 `imports` 行） |
| `I4` | `(CONFIGURED, VALID, INVALID)` | `VALIDATING` | `validateImport` 受理：**202** ＋ `Job(kind='VALIDATE_IMPORT')` ＋ `Location`；`imports.job_id` 同事务写入 | `architecture/DATA.md:11` ＋ `architecture/API.md`「作业」行「202 返回 Job 和 Location」 | `UPDATE imports SET state='VALIDATING', job_id=:job_id, revision=revision+1 WHERE workspace_id=:workspace_id AND id=:id AND state IN ('CONFIGURED','VALID','INVALID') AND revision=:revision` | `TX-I4 ImportService.accept_validation`（复用 M0-04 的 `worker/store.py::JobStore.enqueue`，**禁重写队列**） | False |
| `I5` | `(VALIDATING,)` | `VALID` | `VALIDATE_IMPORT` 作业成功且 `findings` 中**无** `severity='ERROR'` 项 | `architecture/DATA.md:11`「校验的业务问题记入 INVALID 与结构化 issues」的反面 | `UPDATE imports SET state='VALID', validation_digest=:validation_digest, issue_json=:issue_json, revision=revision+1 WHERE workspace_id=:workspace_id AND id=:id AND state='VALIDATING' AND revision=:revision` | `TX-I5 ImportService.finish_validation`（由作业处理器调用，见 §11.8） | False |
| `I6` | `(VALIDATING,)` | `INVALID` | 同上作业完成但**存在** `severity='ERROR'` 的 finding（业务性不合格，**不是**技术失败） | `architecture/DATA.md:11` 原文「校验的业务问题记入 INVALID 与结构化 issues」 | 同 I5 形状，`SET state='INVALID'`，`validation_digest=:validation_digest`（**仍写**，供 §5.3 的失效对撞） | `TX-I5`（同一方法，仅 target 与 issue 面不同） | False |
| `I7` | `(VALIDATING,)` | `CONFIGURED` | 作业**技术失败**且可重试（`worker/states.py::retryable_for` 判定为真）；「技术失败回到可重试的稳定状态，关联 FAILED 作业」 | `architecture/DATA.md:11` 原文「技术失败回到可重试的稳定状态，关联 FAILED 作业」 | `UPDATE imports SET state='CONFIGURED', validation_digest=NULL, issue_json='[]', job_id=:job_id, revision=revision+1 WHERE workspace_id=:workspace_id AND id=:id AND state='VALIDATING' AND revision=:revision` | `TX-I7 ImportService.fail_validation` | False |

- **I5 / I6 的分歧判据是唯一的一条**：`any(f.severity == "ERROR" for f in findings)` ⇒ `INVALID`，否则 `VALID`。
  `WARNING` / `INFO` **不阻断**（`architecture/DATA.md`「去重和可比性」段「人数显示待补去重证据」即以 WARNING 表达）。
- **I7 与 I6 禁混用**：技术失败（例如制品丢失、DB 异常、解析器崩溃）**不得**记成 `INVALID`，否则
  「旧验证失效」与「业务不合格」两种语义在 `issue_json` 上不可区分；`NON_RETRYABLE_PROBLEM_CODES`
  （实测 `frozenset` 含 `EVIDENCE_REQUIRED` / `INPUT_TOO_LARGE` / `INVALID_SCOPE` / `VALIDATION_ERROR`）命中的
  失败**属业务面** ⇒ 走 I6，`issue_json` 记该 `Problem` 对应的 finding，`retryable=0`。

### 3.3 I8–I10 的**预留行**（属 M1-02 写权；本卡**禁注册**，只预写行内容以免下游发明）

| id | sources | target | trigger | spec_ref |
|---|---|---|---|---|
| `I8` | `(VALID,)` | `PUBLISHING` | `publishImport` 受理（接收最近成功校验摘要） | `architecture/API.md`「主要操作关系」原文「publishImport 接收最近成功校验摘要」 |
| `I9` | `(PUBLISHING,)` | `PUBLISHED` | 发布事务提交 | `architecture/DATA.md:11` 原文「发布在同一事务更新 import 与 snapshot 的索引」＋「已发布记录只读」 |
| `I10` | `(PUBLISHING,)` | `VALID` | 发布作业技术失败可重试（与 I7 同族） | 同 I7 的 `spec_ref` |

⇒ 本卡的 `is_import_terminal("PUBLISHED")` 已为 `True`，但 `PUBLISHED` 在本卡**结构上不可达**（无迁移以它为 target）。
S6/S7 **禁**为此写会红的用例，一律按「断言不可达本身」处置（体例＝`M2-01-design.md` §6.6，**禁** `skip` / `xfail`）。

### 3.4 非法迁移的错误映射（**逐条冻结**；码名一律实取自 `domain/errors.py::PROBLEM_CODES`，本文零发明 code）

`PROBLEM_CODES` 实测为 **20 项** dict，值形如 `(status, urn, 中文 title)`；本卡用到的 6 个码实测原文：
`STATE_CONFLICT=(409, urn:campaignlab:problem:state_conflict, 当前状态不允许该操作)` ·
`VERSION_MISMATCH=(409, …:version_mismatch, 版本不一致)` · `IDEMPOTENCY_CONFLICT=(409, …, 幂等键冲突)` ·
`PRECONDITION_REQUIRED=(428, …, 缺少 If-Match 前置条件)` · `REVISION_CONFLICT=(412, …, 修订号不匹配)` ·
`VALIDATION_ERROR=(422, …, 字段校验未通过)` · `INPUT_TOO_LARGE=(413, …, 输入体积超过上限)` ·
`EVIDENCE_REQUIRED=(422, …, 证据不齐备)` · `RESOURCE_NOT_FOUND=(404, …, 对象不存在或不可见)`。

| 非法面 | 抛出 | `detail`（冻结原文） | `issues[0].code` | `issues[0].location` |
|---|---|---|---|---|
| `source in {"VALIDATING","PUBLISHING"}` 时的 I2 / I3 / I4 | 409 `StateConflict` | `导入正在处理中，文件与映射只读` | `IMPORT_BUSY` | `/state` |
| `source == "PUBLISHED"` 时的任何写迁移 | 409 `StateConflict` | `导入已发布，记录只读` | `IMPORT_PUBLISHED` | `/state` |
| `source == "RECEIVED"` 时的 I4（尚无映射） | 409 `StateConflict` | `导入尚未配置映射，无法校验` | `IMPORT_NOT_CONFIGURED` | `/mapping` |
| `source in {"VALID","INVALID"}` 时的 I1（重复建） | 不适用（I1 的 `sources` 为空 ⇒ 只有「新建」一条路径） | — | — | — |
| I5/I6/I7 的 `source != "VALIDATING"`（含并发双作业） | 409 `StateConflict` | `导入不在校验中，作业结果已失效` | `IMPORT_NOT_VALIDATING` | `/state` |
| `If-Match` 缺失 / 不匹配 | 428 `PreconditionRequired` / 412 `RevisionConflict` | 由 `api/common.py::check_if_match` **固定**，禁在调用点另编 | —（helper 不给 issues） | — |
| 幂等键同键异摘要 | 409 `IdempotencyConflict` | 复用 `application/idempotency.py::CONFLICT_DETAIL` 实测原文「同一 Idempotency-Key 已用于不同的请求内容」 | — | — |

- `INGEST_STATE_ISSUE_CODES: Final[tuple[str, ...]] = ("IMPORT_BUSY","IMPORT_PUBLISHED","IMPORT_NOT_CONFIGURED","IMPORT_NOT_VALIDATING")`
  （**待创建，S2**；体例＝实测 `domain/activity/states.py::ACTIVITY_ISSUE_CODES == ('ACTIVITY_ARCHIVED',)`）。
- 这四个 `Issue.code` **不是** `Problem.code`，**不进** `PROBLEM_CODES`（20 码注册表封闭，D-019「禁发明」只约束
  `Problem.code`）；它们是 `Issue.code`（切片 `Issue.code` 实测只约束 `1–96` ＋ ID 正则，无枚举）。
  S6 必须落一条断言：本文出现的**每个** `Issue.code` 都在 `INGEST_ISSUE_CODES ∪ INGEST_STATE_ISSUE_CODES` 内
  （§13 C8 的可复跑版），且**每个** `Problem.code` 都在 `PROBLEM_CODES` 的 20 项内。

## 4. 归一化模型（**本棒的核心**：四入口 → 同一套规范校验）

### 4.0 命题与结构性保证（卡片红线「禁写第二套校验器」的落地方式）

命题：A 宽表（`LEGACY_SYNTHETIC_JSON` ＋ `layout="wide"`）、B 长表（`LEGACY_SYNTHETIC_JSON` ＋ `layout="long"`）、
六行 CSV（`SOURCE_CSV`）、等价 SOURCE_JSON（`SOURCE_JSON`）**共用同一套**规范校验。
本文不用「约定」保证它，而用**三条结构性保证**（S6 必须逐条落成有牙的守护，见 §10 V6）：

1. **唯一的 `format` 分派点**：`format` 只出现在 `domain/ingest/parse.py` 的 `PARSE_ADAPTERS` 注册表里，
   `parse()` 是全 `domain/ingest` 内**唯一**读 `payload.format` 的函数。
2. **下游签名里没有 `format`**：`normalize()` 与 `validate()` 的形参面**根本不含** `format` / `layout`
   ⇒ 想在下游分叉必须先改签名（会被 §10 V6 的 AST 守护判红）。
   `layout` 的分支**只**发生在 `normalize()` 内的**一处**（宽表逐行 vs 长表透视），且两条分支**汇合到同一个**
   `NormalizedSlice` 构造点与同一套 `validate()`。
3. **等价性即断言**：CSV 与等价 SOURCE_JSON 必须产出**逐字段相等**的 `tuple[NormalizedSlice, ...]`
   （实测依据：`csv-mini/slices.csv` 的表头与 `csv-mini/source.json` 的 `tables["月度宽表"].columns`
   **逐字相等**（35 列），6 个数据行在「数字串→int」归一后**逐格相等**，两份 `metadata` 实测 `==` 为 `True`）。

### 4.1 单一入口签名（`public_frozen` 面；卡片 `M1-01.md:24`：M1-P01 只能经此扩展、禁改签名）

新建 `src/campaignlab/domain/ingest/`（S2；`__init__.py` 形态见 §11.1）。**领域层纯度**：禁 SQL、禁开事务、
禁 import `campaignlab.api` / `campaignlab.infra`、**禁持时钟**（时刻一律由 application 层注入 DB，
`framework/PYTHON.md` 第 6 行「每次业务运行传入显式时钟…避免在领域计算内调用系统当前时间」⇒
本层的归一与校验是**纯函数**，无需时钟；这是刻意的，见 §12 U-6）。

```python
# domain/ingest/model.py（待创建，S2）—— 领域数据形状，全部 @dataclass(frozen=True, slots=True)
FileRef            : (table_name: str, sha256: str, size_bytes: int)
RawTable           : (name: str, columns: tuple[str, ...], rows: tuple[tuple[object, ...], ...])
RawSource          : (format: ImportFormat, tables: Mapping[str, RawTable],
                      metadata: Mapping[str, Any], file_refs: tuple[FileRef, ...])
SourceRow          : (source_file_id: str, table_name: str, row_number: int)
NormalizedSlice    : (id, period, cutoff, branch, subbranch, channel, strategy, origin, segment, tag,
                      definition, batch, cohort, offset, customer_key,
                      counts: Mapping[str, int | None], money_fen: Mapping[str, int | None],
                      source_row: SourceRow, contributing_rows: tuple[SourceRow, ...])
MappingSpec        : (id, bank_id, layout: MappingLayout, entity_table, counts_table,
                      dimensions: Mapping[str, str], count_fields: Mapping[str, str],
                      money_fields: Mapping[str, str], source_money_unit: SourceMoneyUnit,
                      long_columns: LongColumnSpec | None, codes: Mapping[str, Mapping[str, str]],
                      dedup_mode: DedupMode)
LongColumnSpec     : (id: str, metric: str, value: str)
Finding            : (code: str, severity: str, location: str, message: str)
SliceCounts        : (slice_count: int, stage_item_count: int, entity_row_count: int, count_cell_count: int)
IngestResult       : (slices: tuple[NormalizedSlice, ...], findings: tuple[Finding, ...],
                      counts: SliceCounts, projection: Mapping[str, Any])
IngestLimits       : (max_slices: int, max_stage_items: int, max_findings: int)

# domain/ingest/api.py（待创建，S2）—— 本卡冻结的**唯一入口**
def parse(payload: UploadPayload) -> RawSource: ...
def ingest(source: RawSource, *, mapping: MappingSpec, limits: IngestLimits = DEFAULT_LIMITS) -> IngestResult: ...
```

- `UploadPayload`（**待创建，S2**，`domain/ingest/model.py`）＝「**尚未解析的**上传件集合」：
  `(format: ImportFormat, files: tuple[UploadedFile, ...])`，`UploadedFile = (table_name: str, raw: bytes, sha256: str, size_bytes: int)`。
  `raw` 是**已经过 §1.2 流式上限判定**的字节（413 在到达本层之前就已抛），故本层只需再做**结构**上限判定。
- `ingest()` 内部严格三段（§4.2），**返回值不含任何 HTTP / DB 概念**：`Finding` 的四个字段名与顺序
  **逐字等于** `api/common.py::Issue` 的实测 `model_fields`（`code` / `location` / `message` / `severity`）⇒
  application 层的映射冻结为 `Issue(code=f.code, location=f.location, message=f.message, severity=f.severity)`，
  **禁**在两层之间做任何字段改名或增删。
- `Finding.severity` 的类型冻结为 `str` ＋ 运行期成员校验（`severity in INGEST_SEVERITIES`），
  `INGEST_SEVERITIES: Final = ("ERROR","WARNING","INFO")` 取自切片 `Issue.properties.severity.enum`；
  **禁**在 domain 里另立第二个 `Literal`（会与既有 `Issue.severity` 的注解分叉）。
  S6 必须落一条跨层对撞断言：`INGEST_SEVERITIES == tuple(get_args(Issue.model_fields["severity"].annotation))`。
- `IngestLimits` 的默认值 `DEFAULT_LIMITS` 一律**实取**契约上限：`max_findings = 1000`
  （← `Import.issues.maxItems` 实测 1000）、`max_slices` / `max_stage_items` 由 `framework/DATA.md`
  「分析基准先用甲乙各 510 切片，再生成 1 万聚合切片与 10 万事件的合成压力数据」取
  `10_000` / `90_000`（1 万切片 × 9 阶段）⇒ 超限 → 422 `VALIDATION_ERROR`，`Issue.code="TOO_MANY_SLICES"` /
  `"TOO_MANY_STAGE_ITEMS"`。**这两个数是本文的设计取值、不是契约字面量** ⇒ 已开 **§12 U-7** 交裁定。

### 4.2 三段职责边界（解析 → 归一 → 校验）

| 段 | 落点（全部**待创建**） | 职责 | 允许感知 `format` / `layout` |
|---|---|---|---|
| ① 解析 | `domain/ingest/parse.py`：`ParseAdapter`（Protocol）、`PARSE_ADAPTERS: Final[Mapping[ImportFormat, ParseAdapter]]`、`parse_legacy_synthetic`、`parse_source_json`、`parse_source_csv`、`legacy_mapping_to_source_mapping`、`parse()` | 把字节变成 `RawSource`：JSON 解码、CSV 解码（UTF-8 或 UTF-8 BOM）、表名/列名/行的原样保留、`schema_version` 与 `synthetic` 前置断言、legacy 内嵌 camelCase 映射 → `MappingSpec` | **`format`：是（唯一分派点）**；`layout`：否 |
| ② 归一 | `domain/ingest/normalize.py`：`normalize(source: RawSource, *, mapping: MappingSpec) -> tuple[NormalizedSlice, ...]`、私有 `_normalize_wide` / `_normalize_long` / `_coerce_cell` / `_to_fen` / `_map_code` | 源列名 → 规范键；宽表逐行 / 长表按 `(id, metric)` 透视；码值 → 标准值；金额 → **整数分**；CSV 文本 → 类型 | `format`：**否**；`layout`：**是，且只在 `normalize()` 内一处** |
| ③ 校验 | `domain/ingest/validate.py`：`validate(slices, *, mapping: MappingSpec, metadata: Mapping[str, Any], source: RawSource) -> tuple[Finding, ...]`、`INGEST_ISSUE_CODES` | §5.1 的全部负例；**完全**格式无关、布局无关 | `format`：**否**；`layout`：**否** |

- **CSV 的类型转换发生在映射层**（`framework/DATA.md`「文件与 DuckDB」第 2 条原文）⇒ `_coerce_cell` 是
  **②归一段**的职责，**不是**①解析段：`parse_source_csv` 交出的 `RawTable.rows` 一律是**原文字符串**
  （实测 `slices.csv` 的 `集合起点` 列在 CSV 里是 `0`、在 `source.json` 里是 int `0`），
  由 `_coerce_cell` 按 `mapping` 的规范键角色（dimension / count / money）决定目标类型。
  这正是 §4.0 保证 3「CSV 与 SOURCE_JSON 逐字段相等」能成立的**唯一**正确落点。
- `SOURCE_CSV` 的元数据来自**表名为 `__metadata__` 的那一份 JSON 上传件**
  （`architecture/DATA.md`「导入通道」表 `SOURCE_CSV` 行原文「必需一个 table_name 为 `__metadata__` 的 JSON 文件」）⇒
  `METADATA_TABLE_NAME: Final = "__metadata__"`（**待创建，S2**，`domain/ingest/parse.py`）；
  缺失 → 422 `EVIDENCE_REQUIRED`，`Issue.code="MISSING_METADATA_TABLE"`，`location="__metadata__#"`（§4.4）。
  该常量长度 12 字符，落在 `AttachFile.table_name` 的 `maxLength=120` 内，合法。
- `LEGACY_SYNTHETIC_JSON` 的前置断言（`architecture/DATA.md`「导入通道」表原文「synthetic 必须 true，保留原编号和元数据。
  内嵌映射由后端生成配置，映射与文件摘要固定」）：`synthetic is not True` → 422 `EVIDENCE_REQUIRED`，
  `Issue.code="NOT_SYNTHETIC"`；实测 `bank-a.json.synthetic is True`、`bank-b.json.synthetic is True`。
  「内嵌映射由后端生成配置」⇒ `parse_legacy_synthetic` 必须把文件内嵌的 `mapping` 经
  `legacy_mapping_to_source_mapping` 转成 `MappingSpec`，并在 application 层作为 `configureImport` 的**等价输入**
  写入 `source_mappings`（`content_json` 与 `digest` 同口径）——即 legacy 通道**隐式**完成 I1＋I3，
  但对外的状态机与摘要口径与显式 `configureImport` **完全一致**（这是「四入口一套规范」在映射面的体现）。

### 4.3 规范切片行（`NormalizedSlice`）的字段与类型（真值来源＝`architecture/DATA.md`「映射和标准表」的字段表）

| 段 | 规范键（14 / 9 / 12） | 类型与约束 |
|---|---|---|
| 维度（`mapping.dimensions` 的 **14** 个键，实测 `map-a.json` / `map-b.json` 均为 14 键） | `id` `period` `cutoff` `branch` `subbranch` `channel` `strategy` `origin` `segment` `tag` `cohort` `offset` `definition` `batch` | `id`＝`StrictStr` 非空（切片号，A 实测形如 `2025-09:B01:remote:1`）；`period`＝`YYYY-MM`；`cutoff`＝`date`（DATA.md「cutoff 为 DATE」）；`offset`＝`int`（DATA.md「offset 为 BIGINT」）；其余为 `str \| None`（DATA.md「未适用字段可空」）；`channel` / `origin` 一律经 `mapping.codes` 映射为**标准码**（A 实测源值 `远程`→`remote`、`分行`→`branch`；B 实测 `C01`→`remote`、`L`→`branch`） |
| 计数（`mapping.count_fields` 的 **9** 个键） | `eligible` `sent` `success` `executed` `contacted` `effective` `capacity` `intentCount` `activityCount` | `int \| None`，**非负**（DATA.md「BIGINT 非负」）；`None` 表示源缺值（DATA.md「缺值以 null 表达并带证据」） |
| 金额（`mapping.money_fields` 的 **12** 个键） | `aum` `deposit` `wealth` `fund` `loan` `wealthSale` `nonCashWealthSale` `fundSale` `nonMoneyFundSale` `insuranceSale` `depositDemand` `depositTerm` | `int \| None`，单位**一律整数分**（DATA.md「BIGINT 分，可空」；卡片红线「禁用浮点算金额分」） |
| 追溯 | `customer_key` `source_row` `contributing_rows` | `customer_key`＝`str \| None`（`DISTINCT_CUSTOMER` 用；本卡 fixtures 的 `dedup_mode` 实测均为 `SYNTHETIC_INTERVAL` ⇒ A/B/CSV 三份实测数据里**无** `customer_key` 源列，一律 `None`）；`source_row`＝该切片的**首**贡献行；`contributing_rows`＝**全部**贡献行（wide 布局下恰 1 项；long 布局下 9 项，见 §4.4） |

- 实测对撞（本文写作时点跑过）：`bank-a.json.tables["月度宽表"]` ＝ **35** 列 / **510** 行；
  `bank-b.json.tables["统计切片"]` ＝ **26** 列 / **510** 行、`tables["阶段人数长表"]` ＝ **3** 列
  （实测列名 `["切片键","指标码","计数"]`，与 `map-b.json.long_columns` 的值逐字对应）/ **4590** 行 ＝ 510 × 9。
  ⇒ **14 + 9 + 12 = 35** 正是 A 宽表的列数，**14 + 12 = 26** 正是 B 实体表的列数（B 的 9 个计数不在实体表里，
  在长表里）—— 这两个等式就是 §10 V7「黄金计数」的结构性依据，S7 必须把它们写成断言而不是注释。
- **元/分归一（AC-006「元分归一后远程值一致」）**：实测 `bank-a.json.tables["月度宽表"].rows[0]` 的 `AUM变动`
  ＝ `182260`（元，`map-a.json.source_money_unit == "CNY_YUAN"`），`bank-b.json.tables["统计切片"].rows[0]` 的
  `amount_01_fen` ＝ `18226000`（分，`map-b.json.source_money_unit == "CNY_FEN"`）⇒
  归一后两者**均为 `18226000` 分，逐字相等**。`fixtures/analytics-golden.json.cross_bank` 实测
  `{"remote_state":"FULL","push_comparison":"NOT_COMPARABLE","push_b_min_seconds":3,"slices_each":510}`
  ⇒ S7 的黄金断言取 `slices_each == 510` 与「A/B 同 `id` 切片的 `money_fen` 与 `counts` 逐键相等」。

### 4.4 行列定位结构（AC-005「校验返回具体行列」的数据形状；**0/1-based 口径显式声明**）

权威口径 ＝ `architecture/API.md`「错误分类」段末原文：**「Problem 响应为 application/problem+json。
字段路径用 JSON Pointer，CSV 可补表名和 1 起数据行号。」** 据此冻结：

- **行号 `row_number`：1-based，且只数数据行（表头 / `columns` 行不计）。**
  - `SOURCE_CSV`：`slices.csv` 实测 7 行 ＝ 1 表头 ＋ 6 数据行 ⇒ 第 1 个数据行 `row_number == 1`
    （实测其 `记录号` ＝ `2026-09:B01:remote:1`）。
  - `LEGACY_SYNTHETIC_JSON` / `SOURCE_JSON`：`tables[t].rows[i]` ⇒ `row_number == i + 1`。
  - **禁** 0-based、**禁**把表头算成第 1 行（会让 CSV 与 JSON 的行号差 1，直接毁掉 §4.0 保证 3 的等价性）。
- **列的定位一律用「规范键」而不是源列名**，源列名进 `message`（人读）。理由：AC-006 要求 CSV 与 SOURCE_JSON
  同值，同一个负例在两个入口必须给出**同一个** `location`；而 A 的源列名是中文（`可经营`）、B 的是码（`M01`）⇒
  只有规范键（`eligible`）能跨入口/跨行内稳定。
- **`Issue.location` 的语法（冻结，三种形状，`minLength=1` / `maxLength=500` 内）**：

| 形状 | 语法 | 例（本文实测数据） |
|---|---|---|
| 行内字段 | `<table_name>#r<row_number>/<section>/<canonical_key>` | `月度宽表#r4/count_fields/eligible`（A 宽表第 4 数据行的「可经营」列） |
| 整行 | `<table_name>#r<row_number>` | `阶段人数长表#r17`（B 长表第 17 数据行） |
| 文件 / 元数据级 | `<table_name>#<json_pointer>`（无行号段） | `__metadata__#/coverage/0/period`、`月度宽表#/columns/3` |

  - `<section>` ∈ `dimensions` / `count_fields` / `money_fields`（＝ `MappingSpec` 的三个映射名，实测键名逐字如此）。
  - JSON Pointer 里的**数组下标一律 0-based**（RFC 6901 标准，与 `row_number` 的 1-based **刻意不同**）⇒
    本文在此**显式声明**这个不对称，并要求 S6 用一条断言把它钉住（`test_location_pointer_is_0_based_while_row_is_1_based`）。
  - `location` 是**纯字符串**（切片 `Issue.location` 实测 `type=string, minLength=1, maxLength=500`，无结构）⇒
    解析器 `parse_location(location: str) -> LocationParts`（**待创建，S2**，`domain/ingest/locate.py`）
    必须与生成器 `make_location(...)` 互为逆，S6 落 round-trip 断言。超 500 字符一律截断**表名**段并在
    `message` 里保留全名（禁截断行号或指针段，那会毁掉可追溯性）。
- **long 布局的定位口径**：B 的一个切片由 `阶段人数长表` 的 **9** 行聚合而成（实测 4590 ＝ 510 × 9）⇒
  `source_row` 取 `指标码 == mapping.count_fields["eligible"]`（即 `M01`）的那一行；`contributing_rows` 保留全部 9 行，
  **顺序 ＝ `mapping.count_fields` 的键序**（实测 `map-b.json.count_fields` 键序为
  `eligible,sent,success,executed,contacted,effective,capacity,intentCount,activityCount`，即 `M01…M09`）。
  针对单个阶段项的负例（如「重复码」「孤立切片」）`location` 指到**那一行**（`阶段人数长表#r<1-based>`），
  针对切片级的负例指到 `source_row`。

### 4.5 元/分归一口径（**整数分**；卡片红线「禁用浮点算金额分」）

- `source_money_unit == "CNY_FEN"`（B 实测）：源值必须是**整数**；`fen = int(源值)`。
- `source_money_unit == "CNY_YUAN"`（A 与 csv-mini 实测）：`fen = 元 × 100`，**只用整数/`Decimal` 运算**：
  冻结实现 ＝ `Decimal(源文本或源整数)` → `scaled = value.scaleb(2)` → 断言
  `scaled == scaled.to_integral_value()`，成立则 `fen = int(scaled)`，不成立则报 `INVALID_MONEY`
  （`architecture/DATA.md`「映射和标准表」段原文「甲行金额元乘 100，乙行分保持原整数。超出精度报 INVALID_MONEY」）。
  **禁** `float`、**禁** `round(float(x) * 100)`（`0.29 * 100 == 28.999999999999996`，会静默丢分）。
- 计数与 `offset`：`int`，**禁** `bool`（`StrictInt` 语义；`framework/PYTHON.md` 第 3 行「布尔冒充整数」）。
  CSV 通道下 `_coerce_cell` 用 `int(text)`，失败 → `Issue.code="NOT_AN_INTEGER"`。
- 余额增量可为负、销量为非负（`architecture/DATA.md` 原文「余额增量可为负，销量为非负」）⇒
  `money_fields` 的 12 键分两组：`depositDemand` / `depositTerm` / `aum` / `deposit` / `wealth` / `fund` / `loan`
  为**变动**类（可负，实测 golden 的 `current.aum == "-407400000"`）；`wealthSale` / `nonCashWealthSale` /
  `fundSale` / `nonMoneyFundSale` / `insuranceSale` 为**销量**类（非负，实测 golden 的 `current.wealthSale == "22809600"`）
  ⇒ 销量类出现负数 → `Issue.code="NEGATIVE_SALE"`（`severity="ERROR"`）。
  这组「哪些键可负」的划分**是本文的设计判断**（契约与 spec 只给了「余额增量可为负，销量为非负」这一句）⇒ 开 **§12 U-8**。
- 金额绝对值上限一律**实取** `contracts/source-json.schema.json` 的 `minimum` / `maximum`
  （S2 用 jsonschema 对撞，**禁写死**，A115）；超限 → `Issue.code="INVALID_MONEY"`。

### 4.6 去重与可比性（`architecture/DATA.md`「去重和可比性」三段原文的落点）

- `dedup_mode` 三值的**语义**逐字来自 DATA.md 三条：`SYNTHETIC_INTERVAL`（「以银行快照、period、cohort 分组，
  逐阶段求半开区间 `[offset, offset+count)` 的并集长度。相邻区间允许合并」）·
  `DISTINCT_CUSTOMER`（「每客户切片的名单阶段为 0 或 1」）· `AGGREGATE_ONLY`（「多行范围内缺交集时，人数显示待补去重证据」）。
- **本卡的职责边界（冻结）**：M1-01 **只**负责 ① 把 `dedup_mode` 原样归一并透传，② 提供**分组键**
  `SliceKey = (bank_id, period, cohort, channel)`（**待创建，S2**，`domain/ingest/model.py`；键的四元组取自
  DATA.md 原文「以银行快照、period、cohort 分组」＋「同一客户跨策略和渠道取并集」所需的渠道维），
  ③ 校验 `SYNTHETIC_INTERVAL` 的**可算性前置**（`offset` 为整数、`cohort` 非空、同键下 `period` 一致）。
  **区间并集的算术、0/1 判定、待补证据的显示一律归 M1-02 / M1-03**（卡片 `scope_deny` 显式含
  `domain/snapshot/**` / `domain/caliber/**` / `analytics/**`）⇒ 本卡**禁**实现 `dedup_*` 任何算术函数，
  也**禁**在 §11 里给 S2–S8 派这类活。
- 可比性判据（「每个本期和基准配对以渠道、统计范围、采集状态、语义键和截止进度判断」）与
  `semantic_key`（实测 `csv-mini/metadata.json.coverage[*].semantic_key == "REMOTE-1"`）在本卡**只归一只校验存在性**：
  `coverage[*]` 缺 `semantic_key` → `Issue.code="MISSING_SEMANTIC_KEY"`（`severity="WARNING"`，不阻断）。

### 4.7 源行与文件摘要可追溯（AC-006）＋ `validation_digest` 的固定投影

三层摘要，各自单一真值来源：

1. **文件摘要** ＝ 制品的原字节 SHA-256，落在 `artifacts.sha256`（`architecture/DOMAIN.md`「唯一标识和精度」段原文
   「制品摘要按原字节计算」）；`ImportFile.sha256` / `.size_bytes` 经 `import_files.artifact_id` JOIN 读出（§2.4）。
   `FileRef` / `SourceRow.source_file_id` 把它带进每一个 `NormalizedSlice` ⇒ **源行可追溯**落到
   `NormalizedSlice.source_row`（DATA.md「映射和标准表」表原文「source_row 由导入器生成，含 source_file_id、
   table_name、row_number」）与 `contributing_rows`。
2. **映射摘要** ＝ `source_mappings.digest = sha256(canonical_json(SourceMapping.model_dump(mode="json")))`，
   64 位小写十六进制（DDL 实测 `CHECK(length(digest)=64)`）。
3. **校验摘要** ＝ `imports.validation_digest`。固定投影（`architecture/DATA.md`「映射和标准表」段原文
   「校验摘要覆盖文件原始 SHA、映射内容、元数据及解析器版本」＋ `architecture/DOMAIN.md`「业务摘要排除运行时间、
   作业号、租约和随机资源 ID」）：

```python
# domain/ingest/digests.py（待创建，S2）；体例逐字对齐实测的
# domain/activity/digests.py::rule_digest(content, terms, source_rule_version, *, canonicalize)
# —— canonicalize 由**调用方注入**，领域层不 import campaignlab.api（§3.1 的依赖方向）
VALIDATION_DIGEST_KIND: Final = "IMPORT_VALIDATION"
DIGEST_LENGTH: Final = 64  # 体例＝实测 domain/activity/digests.py::RULE_DIGEST_LENGTH == 64


def validation_projection(
    *, file_refs, mapping_digest, metadata, parser_version
) -> dict[str, Any]: ...
def validation_digest(
    projection: Mapping[str, Any], *, canonicalize: Callable[[object], str]
) -> str: ...
```

  投影字段（**键序即摘要输入序，禁调序**；`canonicalize` 一律注入 `api/common.py::canonical_json`，
  实测签名 `canonical_json(obj: object) -> str`，其口径「键排序、无额外空格、保留数组顺序、字符串先 NFC」
  由 S2 落一条对撞断言钉住，**禁另写第二份序列化**）：

| 键 | 值 | 依据 |
|---|---|---|
| `kind` | `"IMPORT_VALIDATION"` | 与 `architecture/DOMAIN.md`「内容摘要的固定投影」表的「快照」行同族（该行含「原始文件摘要」） |
| `parser_version` | `domain/ingest/parse.py::PARSER_VERSION`（**待创建，S2**） | DATA.md 原文「及解析器版本」 |
| `files` | `[{"table_name":…, "sha256":…, "size_bytes":…}]`，按 `(table_name, sha256)` 升序 | DATA.md 原文「文件原始 SHA」；排序是为了「同一组文件不同上传顺序」得到同一摘要 |
| `mapping_digest` | 64hex | DATA.md 原文「映射内容」 |
| `metadata_digest` | `sha256(canonicalize(metadata))` | DATA.md 原文「元数据」 |

  **禁入投影**的字段（`architecture/DOMAIN.md`「业务摘要排除运行时间、作业号、租约和随机资源 ID」）：
  `created_at` · `job_id` · `import_id` · `artifact_id` · `revision` · `lease_*` · `request_id`。
  S6 必须落一条断言：投影的键集合**恰等于**上表 5 键（多一键少一键都判红）。
- **元数据摘要的输入面**：`SOURCE_JSON` / `LEGACY_SYNTHETIC_JSON` 取文件内嵌的 `metadata` 对象；
  `SOURCE_CSV` 取 `__metadata__` 件的**已解析 JSON 对象**（不是原字节）⇒ 实测 `csv-mini/metadata.json`
  与 `csv-mini/source.json` 的 `metadata` 子树**逐字相等**（本轮实测 `==` → `True`）⇒
  CSV 与 SOURCE_JSON 的 `metadata_digest` 相同 ⇒ `validation_digest` 相同 ⇒ AC-006「CSV/JSON 同值」
  在**摘要面**也成立，而不只在切片面成立。**但**两者的 `files` 段不同（一份 6 行 CSV ＋ 一份 metadata JSON vs
  一份 source.json；原字节 SHA 必然不同）⇒ `validation_digest` **不相同**。本文在此**显式声明**：
  AC-006 的「同值」指**归一后的切片值与元数据投影同值**，**不**指 `validation_digest` 同值。已开 **§12 U-9**。

### 4.8 M1-P01（月报接入）的扩展点（卡片 `public_frozen`：只能经同一套入口扩展，禁另起第二套、禁改签名）

- 实测 `contracts/source-json.schema.json:474` 存在 `"monthly_review"` 属性（v1.0.1 月度增量补丁面）⇒
  月报 append 清单**走 `SOURCE_JSON` / `SOURCE_CSV` 两个既有 `format`**，不新增第 4 个 `format`
  （`ImportFormat` 的 3 值被 `ddl.imports` 的 `CHECK` 与切片 enum 双向钉死，新增即需改契约）。
- 因此扩展缝**只有一处**：`RawSource.metadata` 里的 `monthly_review` 子树。冻结扩展方式：
  ① `parse_source_json` / `parse_source_csv` 把 `metadata` **原样**交给 `RawSource.metadata`（不做白名单裁剪）；
  ② `validate()` 的形参 `metadata: Mapping[str, Any]` **不变**，月报的追加校验作为
  `domain/ingest/monthly.py`（**M1-P01 新建**，本卡不建）里的**附加 finding 生成器**，由 `validate()` 末尾
  经一个**注册表**调用：`METADATA_VALIDATORS: Final[tuple[MetadataValidator, ...]]`（**待创建，S2**，
  本卡注册 0 项或仅注册基础项；M1-P01 只**追加**注册项）。
  ⇒ `ingest()` 与 `validate()` 的**签名一字不改**，`public_frozen` 得到满足；改动走 CR。
- **禁**给 M1-P01 留「第二个 `ingest` 入口」「第二个 `validate`」或 `if monthly:` 分支（那正是卡片红线
  「不得另起第二套校验」的违例形态）。
## 5. 负例与失效（逐条冻结：触发条件 → severity → `Issue.code` → `location`）

`INGEST_ISSUE_CODES`（**待创建，S2**，`domain/ingest/validate.py`）＝下表 N1–N18 的 `Issue.code` 全集，
形态 `Final[tuple[str, ...]]`（体例＝实测 `domain/activity/states.py::ACTIVITY_ISSUE_CODES`）。
**这些是 `Issue.code`，不是 `Problem.code`**；`Problem.code` 一律只用 `domain/errors.py::PROBLEM_CODES` 的 20 项（§3.4）。
`severity` 一律取自 `INGEST_SEVERITIES = ("ERROR","WARNING","INFO")`（§4.1）。
下表**每一行都必须被 S6 的一个具名参数化用例覆盖**（§10 V2/V5/V6），且用例名必须含卡片 gate 的 `-k` 字面量。

### 5.1 负例矩阵（AC-005 的六类注入 ＋ 归一面必需的其余负例）

| # | 触发条件（**实测数据面**） | severity | `Issue.code` | `location`（§4.4 语法） | HTTP 面 | AC / spec 出处 |
|---|---|---|---|---|---|---|
| N1 | **重复切片**：`entity_table` 内两行的 `dimensions.id` 相同（A 实测 `id` 形如 `2025-09:B01:remote:1`） | ERROR | `DUPLICATE_SLICE` | `<entity_table>#r<后出现行的 1-based 行号>/dimensions/id` | 202 → `Job.problem=null`、`imports.state='INVALID'`（I6），`Import.issues` 带本条 | AC-005「A 样例注入重复切片」 |
| N2 | **负人数**：任一 `count_fields` 归一后 `< 0` | ERROR | `NEGATIVE_COUNT` | `<table>#r<row>/count_fields/<规范键>` | 同 N1 | AC-005「负人数」；DATA.md「BIGINT 非负」 |
| N3 | **层级倒置**：名单阶段链 `eligible ≥ sent ≥ success ≥ executed ≥ contacted ≥ effective` 被破坏（DATA.md 原文「名单阶段链逐级不增」） | ERROR | `FUNNEL_INVERSION` | `<table>#r<row>/count_fields/<被破坏的那一级的规范键>`；`message` 必须同时给出上一级的键名与两个值 | 同 N1 | AC-005「层级倒置」 |
| N4 | **错误行长**：`len(row) != len(columns)`（宽表实测 35 列、B 实体表 26 列、B 长表 3 列、CSV 实测表头 35 列） | ERROR | `ROW_LENGTH_MISMATCH` | `<table>#r<row>`（整行形状） | 同 N1 | AC-005「错误行长」 |
| N5 | **重复码**（B 长表）：同一 `(切片键, 指标码)` 出现两次 | ERROR | `DUPLICATE_CODE` | `<counts_table>#r<row>`；`message` 含首次出现的行号 | 同 N1 | AC-005「B 注入重复码」；DATA.md「重复码…均报错」 |
| N6 | **孤立切片 / 未知切片**（B 长表）：`切片键` 在 `entity_table` 的 `dimensions.id` 集合里不存在 | ERROR | `ORPHAN_SLICE` | `<counts_table>#r<row>` | 同 N1 | AC-005「B 注入…孤立切片」；DATA.md「未知切片…均报错」（**本文裁定两处措辞同指一事**，只登记 `ORPHAN_SLICE` 一个码，见 §12 U-10） |
| N7 | **缺必填阶段**（B 长表）：某切片缺 9 个 `count_fields` 规范键中的任意一个 | ERROR | `MISSING_STAGE` | `<entity_table>#r<该切片所在行>`；`message` 列出缺失的规范键 | 同 N1 | DATA.md「缺必填阶段…均报错」 |
| N8 | **映射引用不存在列**：`mapping.dimensions/count_fields/money_fields` 的值（源列名）不在对应表的 `columns` 里 | ERROR | `UNKNOWN_COLUMN` | `<table>#/columns/<该源列名在 mapping 里的规范键>`；`message` 含源列名原文 | `configureImport` → **422 `VALIDATION_ERROR`**（映射面错误在配置时即可判，不必等校验作业） | DATA.md「映射引用不存在列均报错」 |
| N9 | **`layout` 与 `long_columns` 矛盾**：`layout=="long"` 而 `long_columns is None`，或 `layout=="wide"` 而 `long_columns is not None` | ERROR | `LAYOUT_MISMATCH` | `/layout` | 422 `VALIDATION_ERROR` | 切片 `SourceMapping.long_columns.anyOf[1].type == "null"` ＋ DATA.md「wide 的阶段来自 entity_table。long 的阶段先按长表切片键和指标码唯一连接」 |
| N10 | **未知码值**：源列值不在 `mapping.codes[<维度>]` 的键集合内（A 实测 `codes.channel` 6 项、`codes.origin` 2 项；B 同） | ERROR | `UNKNOWN_CODE` | `<table>#r<row>/dimensions/<规范键>`；`message` 含源值原文 | 同 N1 | DATA.md「codes 按规范维度为键，映射源代码至标准值」 |
| N11 | **字典引用不存在**：`branch` / `channel` / `strategy` 归一后的标准值不在 `metadata` 的对应字典里（实测 `metadata.branches` 为 5 项 list、`metadata.channels` 为 6 键 dict、`metadata.strategies` 为 3 项 list） | ERROR | `UNKNOWN_DICTIONARY_REF` | `<table>#r<row>/dimensions/<规范键>` | 同 N1 | DATA.md「字典引用存在」 |
| N12 | **来源与策略不匹配**：行的 `origin` 与 `metadata.strategies[<strategy>].origin` 不一致 | ERROR | `ORIGIN_STRATEGY_MISMATCH` | `<table>#r<row>/dimensions/origin` | 同 N1 | DATA.md「来源与策略匹配」 |
| N13 | **月份 / 日历非法**：`period` 不是 `YYYY-MM` 或不是合法日历月；`cutoff` 不是合法 `YYYY-MM-DD` | ERROR | `INVALID_PERIOD` / `INVALID_CUTOFF`（两个码） | `<table>#r<row>/dimensions/period`（或 `/dimensions/cutoff`） | 同 N1 | DATA.md「月份和日期用解析器校验日历」 |
| N14 | **`cutoff` 不在 `period` 内** | ERROR | `CUTOFF_OUTSIDE_PERIOD` | `<table>#r<row>/dimensions/cutoff` | 同 N1 | DATA.md「cutoff 必须在 period」 |
| N15 | **金额精度 / 类型**：`CNY_YUAN` 下 `元×100` 非整；`CNY_FEN` 下带小数；文本无法解析为 `Decimal`；绝对值超契约上下限 | ERROR | `INVALID_MONEY` | `<table>#r<row>/money_fields/<规范键>` | 同 N1 | DATA.md「超出精度报 INVALID_MONEY」；卡片红线「禁用浮点算金额分」 |
| N16 | **销量为负**：§4.5 划定的 5 个销量键出现负值 | ERROR | `NEGATIVE_SALE` | `<table>#r<row>/money_fields/<规范键>` | 同 N1 | DATA.md「余额增量可为负，销量为非负」 |
| N17 | **`__metadata__` 件缺失**（`SOURCE_CSV`）或 `synthetic` 非 `true`（`LEGACY_SYNTHETIC_JSON`）或 `schema_version` / `metadata` 缺必需键 | ERROR | `MISSING_METADATA_TABLE` / `NOT_SYNTHETIC` / `MISSING_SEMANTIC_KEY`（第三者 `severity="WARNING"`，**不阻断**） | `__metadata__#` / `<表名>#/synthetic` / `__metadata__#/coverage/<0-based 下标>/semantic_key` | 前两者 → **422 `EVIDENCE_REQUIRED`**（`createImport` / `attachImportFile` 同步面）；第三者只进 `issues` | DATA.md「导入通道」表 `SOURCE_CSV` / `LEGACY_SYNTHETIC_JSON` 行；「去重和可比性」段 `semantic_key` |
| N18 | **规模上限**：`len(slices) > limits.max_slices` 或长表阶段项 `> limits.max_stage_items` 或 `len(findings) > limits.max_findings` | ERROR | `TOO_MANY_SLICES` / `TOO_MANY_STAGE_ITEMS` / `TOO_MANY_ISSUES` | `<table>#`（文件级） | 422 `VALIDATION_ERROR` | §4.1（`Import.issues.maxItems` 实测 1000；切片/阶段项上限见 §12 U-7） |

**`-k` 字面量覆盖要求（A275 ③：两个 `-k` 各自至少命中 1 个具名用例）**：

| 卡片 gate 的 `-k` 字面量 | 必须命中的具名用例（S6/S7 落地，函数名逐字含该字面量） |
|---|---|
| `locate` | `test_locate_duplicate_slice_reports_row_and_column` · `test_locate_negative_count_reports_canonical_key` · `test_locate_funnel_inversion_reports_lower_stage` · `test_locate_row_length_mismatch_reports_whole_row` · `test_locate_duplicate_code_reports_long_row` · `test_locate_orphan_slice_reports_long_row`（N1–N6，全在 `tests/domain/ingest/`） |
| `size_limit` | `test_size_limit_rejects_synthetic_over_8mib` · `test_size_limit_rejects_generic_over_64mib` · `test_size_limit_leaves_no_partial_artifact` · `test_size_limit_problem_shape_is_413_input_too_large`（§5.2，`tests/domain/ingest/`） |
| `csv_equivalence` | `test_csv_equivalence_slices_match_source_json_field_by_field` · `test_csv_equivalence_metadata_digest_matches` · `test_csv_equivalence_locations_are_identical`（§4.0 保证 3 / §4.7，`tests/domain/ingest/`） |
| `stale_validation` | `test_stale_validation_after_reconfigure_clears_digest` · `test_stale_validation_after_reattach_clears_digest` · `test_stale_validation_leaves_published_snapshot_untouched`（§5.3，`tests/domain/ingest/`） |
| `counts` | `test_counts_bank_a_is_510_slices` · `test_counts_bank_b_is_510_slices_and_4590_stage_items` · `test_counts_cross_bank_money_fen_agree_after_normalization`（§4.3，`tests/golden/ingest/`） |
| `validate_import` | ⚠ **NO_TEETH**：本轮实测 `pytest -q tests/integration/jobs -k validate_import --collect-only` 输出 `no tests collected (98 deselected) in 0.05s`、**rc=0** ⇒ 该 gate 现在**空转即绿**。见 §10 V5 与 §12 U-2 |

### 5.2 三个上限不是冲突，是三个不同对象（卡片 U-3 已裁 **D16**，本表逐字沿用、**禁新增阈值**）

| 上限值 | 适用对象 | 权威出处（本轮回源实读） | 触发 |
|---|---|---|---|
| **1 MiB** ＝ `config.MAX_JSON_BODY_BYTES`（实测 `1_048_576`） | **仅 JSON 请求正文** ⇒ 本卡只有 `configureImport` | `docs/decisions/ADR-005-problem-type-and-runtime-defaults.md` §2.3（卡片 U-3 表原文：「文件上传沿用 OPERATIONS.md 的 8 MiB / 64 MiB 口径，**两者不得混用**」） | 413 `INPUT_TOO_LARGE` |
| **8 MiB** | **合成 v0.1 文件入口** ⇒ `format == "LEGACY_SYNTHETIC_JSON"` 的上传件（AC-005 的拒绝线） | `spec/CampaignLab-SDD-v1.0/architecture/OPERATIONS.md:11` 原文（本轮 `grep -n MiB` 实测命中第 **11** 行）：「普通上传限制单文件 64 MiB，合成 v0.1 文件入口限 8 MiB」 | 413 `INPUT_TOO_LARGE` |
| **64 MiB** | **普通上传单文件** ⇒ `format ∈ {"SOURCE_JSON","SOURCE_CSV"}` 的每一个上传件 | 同 `OPERATIONS.md:11` 同句 | 413 `INPUT_TOO_LARGE` |

- 落点：`domain/ingest/limits.py`（**待创建，S2**）持
  `SYNTHETIC_V01_MAX_BYTES: Final = 8 * 1024 * 1024` · `GENERIC_UPLOAD_MAX_BYTES: Final = 64 * 1024 * 1024` ·
  `MAX_FILES_PER_IMPORT: Final = 32`（← 实测 `Import.files.maxItems == 32`）·
  `max_bytes_for_format(fmt: ImportFormat) -> int` · `assert_within_size_limit(*, fmt, size_bytes, location) -> None`。
  **常量住领域层、不住 `config.py`**：`config.py` 不在 `scope_allow`（改它是写权缺口），且 `framework/PYTHON.md`
  第 3 行要求依赖朝领域内收 ⇒ `api/imports.py` 与 `infra/files.py` 都从 `domain/ingest/limits.py` **单向** import。
- 判定时点＝ §1.2 的**三段**（`Content-Length` 预判 → 流式累计 → `stage.discard()`）；
  **「不留半成品」是可证的**：`AttemptStage.discard()`（实测存在于 `infra/artifacts.py`）删除尝试目录，
  `artifacts` 表**零插入**、`import_files` 表**零插入**、`imports` 行**不被创建/不被改状态**（413 抛在 TX 之前）。
  S6 的 `test_size_limit_leaves_no_partial_artifact` 必须断言这四件事**全部**成立（探针用 `tmp_path`，禁落工作树）。
- **禁**用 `AppConfig.max_json_body_bytes` 当文件上限（那正是 ADR-005 §2.3 禁止的「两者混用」）。

### 5.3 旧验证在新映射后失效 ＋ 正式快照未被更新（AC-005 后半句）

- **失效的实现＝结构性清空，不是打标记**：I2 / I3 的 UPDATE 一律
  `SET validation_digest=NULL, issue_json='[]', state='CONFIGURED', revision=revision+1`（§3.2 的 guard 原文）⇒
  之后 `getImport` 读出的 `Import.validation_digest is None`、`Import.issues == []`、`Import.state == "CONFIGURED"`，
  **三面同时**证明旧验证已失效；`ETag` 因 `revision+1` 而变（§6.1），旧 `If-Match` 立刻 412。
- **联动关系（冻结）**：`validation_digest` 的输入含 `mapping_digest`（§4.7）⇒
  「新映射 → 新 `source_mappings.id` 与新 `digest`（§2.4：禁 UPDATE `content_json`）→ 旧 `validation_digest`
  必然不再匹配」。因此**即使**某条路径漏了清空动作，摘要对撞也会失败 ⇒ 双层保证。
  S6 必须两条都测：`test_stale_validation_after_reconfigure_clears_digest`（清空面）与
  `test_stale_validation_digest_would_not_match_new_mapping`（摘要面）。
- **正式快照未被更新**：`snapshots` 表在本卡**零写入**（卡片 inputs 原文「`snapshots` 由 M1-02 写入，
  本任务只建表读写边界不发布」；`imports.snapshot_id` 本卡**只读**，恒为 `NULL`）⇒
  S6 的 `test_stale_validation_leaves_published_snapshot_untouched` 断言：
  ① 校验前后 `SELECT count(*) FROM snapshots` 相等；② `imports.snapshot_id IS NULL`；
  ③ `artifacts` 表只多了**上传件**行（`kind == ARTIFACT_KIND_IMPORT_FILE`），无快照制品行。
- 「新发布时校验摘要必须仍匹配」（DATA.md 原文）的**执行**归 M1-02（`publishImport`）；本卡的义务是
  提供一个**可复算、可跨进程比对**的 `validation_digest`（§4.7 的固定投影 ＋ 注入式 `canonicalize` 已保证）。

## 6. ETag 与 409 / 412 / 428 边界

### 6.1 ETag 出现面（逐 op 以切片 `operation.responses.<2xx>.headers` **实取**为准，禁发明）

| op | 2xx | 实测响应头 | ETag 值 |
|---|---|---|---|
| `createImport` | 201 | `X-Request-Id` · `ETag` | `etag(1)`（新行 `revision=1`） |
| `attachImportFile` | 200 | `X-Request-Id` · `ETag` | `etag(revision_after)`（I2 后 = 旧值 +1） |
| `configureImport` | 200 | `X-Request-Id` · `ETag` | `etag(revision_after)`（I3 后 = 旧值 +1） |
| `validateImport` | 202 | `X-Request-Id` · **`Location`** · `ETag` | `etag(revision_after)`（I4 后 = 旧值 +1）；`Location` ＝ 新 `Job` 的绝对/相对 URL，一律走既有 `accepted_response(job, location=…, request_id=…, extra_headers={"ETag": …})`（实测签名），体例逐字对齐 `api/jobs.py::retry_job` |
| `getImport` | 200 | `X-Request-Id` · `ETag` | `etag(current_revision)` |
| `listImports` | 200 | `X-Request-Id`（**实测无 `ETag`**） | — （列表不给 ETag，禁自行添加） |

- `etag(revision: int) -> str` 与 `check_if_match(header: str | None, current_revision: int) -> None` **均实存**于
  `api/common.py.__all__`（实测签名如左）；`architecture/API.md`「版本」行原文「ETag 为带双引号的整数修订号。
  需要 If-Match 的动作缺头 428，过期 412」⇒ **禁**自己拼 `f'"{rev}"'`，一律 `etag(rev)`。
- **A260（禁运行期 2xx 断言）**：状态码判据面 ＝「**装饰器 `declared_responses(<2xx>)` 的声明 vs 切片 `operation.responses` 的 2xx**」。
  本卡的成功响应一律**直接返回 `Response`**（信封承载状态码）⇒ 装饰器的 `status_code` 被短路，
  运行期断言 `resp.status_code == 201` 属**结构性 NO_TEETH**，S6 **禁写**；
  改写为「路由对象的 `responses` 键集合 == 切片该 op 的 `responses` 键集合」＋「2xx 恰一个」两条静态断言
  （体例＝A95：`declared_responses()` 是唯一权威）。

### 6.2 428 / 412 的实现口径（A228；含会让 428 永不可达的陷阱）

- 切片把 `If-Match` 声明为 `required: true`（3 个 op 实测如此）。**若**照抄成必填形参，缺头会在进入函数体之前被
  Starlette 判 `RequestValidationError` → `install_error_handlers` 翻成 **422 `VALIDATION_ERROR`**，
  契约要求的 **428 `PRECONDITION_REQUIRED`** 就**永远不可达**。
- **冻结做法（A228 逐字）**：`if_match: str | None = Header(alias="If-Match", default=None, min_length=3,
  max_length=32, pattern=IF_MATCH_PATTERN)`；`IF_MATCH_PATTERN` **单源 import** 自 `api/common.py`
  （A271 / FU-59 / PRE-40；实测定义点 `api/common.py:190`，实测值 `'^"[1-9][0-9]*"$'`，实测已在 `__all__`）。
  然后把 `if_match` 原样交给 service，由 service **在事务内读到当前行之后**调
  `check_if_match(if_match, current_revision)`：`None` → 428 `PreconditionRequired`、
  `!= etag(current_revision)` → 412 `RevisionConflict`（detail 由该 helper 固定，**禁**在调用点另编）。
  三种输入三种结果：缺头 → 428；格式非法（`abc` / `"0"` / `0`）→ 422（形参级校验，
  `issues[0].location="/header/If-Match"`）；格式合法但不等 → 412。
- **`createImport` 无 `If-Match`**（切片实测只有 2 个参数）⇒ 它的 428 / 412 属**声明但结构不可达**，
  按 §8 的「不可达」段处置（断言不可达本身，**禁** `skip` / `xfail`）。
- 412 与 428 都**不写审计**（§7.3 只给业务性拒绝写 `DENIED`；协议性缺头属请求形状问题）。

### 6.3 判定顺序（4 个写 op 统一流水线；**顺序即代码顺序，禁调序**）

1. **中间件**：`OriginHostGuard` → 403 `ORIGIN_DENIED`（`request_id_middleware` 给 `X-Request-Id`）；
   `require_session` → 401 `SESSION_EXPIRED`（同码同 detail，禁枚举 oracle）。
2. **形参级校验**（FastAPI）：路径参数正则、`limit`/`q`/`status`/`cursor` 长度、`If-Match` 与 `Idempotency-Key` 形状
   → 422 `VALIDATION_ERROR`（既有 `_handle_validation_error` 面，禁第二份实现）。
3. **`Idempotency-Key` 值校验**：`validate_idempotency_key(...)` → 422，`issues[0].location="/header/Idempotency-Key"`。
4. **正文**：
   - `configureImport`：`read_body_within_limit(request, max_bytes=get_config(request).max_json_body_bytes)` → 413；
     `parse_json_body(body, content_type, ImportConfigure)` → Content-Type / JSON 语法 400 `BAD_REQUEST`、
     DTO 校验（含未知字段，`extra="forbid"`）422 ＋ `validation_issues(exc)`。
   - `createImport` / `attachImportFile`：§1.2 的 `_read_form_within_limit` → 413（**在**任何落盘之前）；
     文本字段 → `UploadFields` / `AttachFileFields` 校验 → 422。
5. **开事务 → 读当前行**：`imports` 行不存在或属外工作区 → **404 `RESOURCE_NOT_FOUND`**
   （逐字相同响应，不回显 ID；`architecture/OPERATIONS.md`「会话和作用域」段原文「外工作区对象按 404 返回」）。
   `createImport` 无此步（它读的是 `workspaces` 行）。
6. **幂等重放**：`IdempotencyGuard.peek(conn, key=…, request_digest=…)`（实测签名）命中同摘要 →
   回滚本次、`replay_from_envelope(envelope, request_id=…)` 回放（**先幂等、后 If-Match**，
   `architecture/API.md`「幂等」行原文「先查幂等重放，再查 If-Match」）。同键异摘要 → 409 `IDEMPOTENCY_CONFLICT`
   （detail 复用 `application/idempotency.py::CONFLICT_DETAIL` 实测原文）。
   `request_digest` 实测签名 `request_digest(*, path, query, body, files=())` ⇒
   两个 multipart op 必须把上传件的 sha256 传进 `files=`（`architecture/API.md`「幂等」行原文
   「摘要含规范化路径、查询、正文和上传文件摘要」），**禁**只传 `body`。
7. **If-Match**：428 → 412（§6.2）。
8. **状态机**：`assert_import_transition_allowed(source, target, trigger=…)` → 409 `STATE_CONFLICT`（§3.4）。
9. **业务门禁**：文件规模（§5.2，multipart 面已在第 4 步判过 `Content-Length`，此处判**实际累计**）、
   `table_name` 重复（422 `DUPLICATE_TABLE_NAME`）、映射列存在性（N8/N9 → 422）、
   `bank_id`＋内容摘要复用冲突（409 `VERSION_MISMATCH`，§4.7）。
10. **写 ＋ 审计 ＋ 幂等登记（同一短事务）** → 提交；`IdempotencyGuard.record(...)`（实测签名含
    `status` / `envelope_json` / `now`）撞主键（并发同键）→ 回滚并按既有 `_Replay` 控制流回放
    （体例＝`application/workspace_service.py`，**禁**改成裸「先查后插」——`application/idempotency.py`
    docstring 原文即「禁止裸先查后插」）。

### 6.4 409 / 422 家族逐码触发面（**只用 20 码注册表内的码**，码名以 `PROBLEM_CODES` 实取为准）

| 码 | status | 本卡的触发面 |
|---|---|---|
| `IDEMPOTENCY_CONFLICT` | 409 | 同 `Idempotency-Key` ＋ 不同 `request_digest`（§6.3 第 6 步） |
| `STATE_CONFLICT` | 409 | §3.4 的四条非法迁移（`IMPORT_BUSY` / `IMPORT_PUBLISHED` / `IMPORT_NOT_CONFIGURED` / `IMPORT_NOT_VALIDATING`） |
| `VERSION_MISMATCH` | 409 | 同 `workspace_id`＋`bank_id` 下，客户端给的 `SourceMapping.id` 已存在但 `digest` 不同（§2.4「同 ID 变更要求新 ID」；处置见 §12 U-4） |
| `SNAPSHOT_CONFLICT` | 409 | **本卡不可达**（`snapshots` 零写入，归 M1-02） |
| `STALE_CANDIDATE` / `ACTION_REVIEW_REQUIRED` | 409 | **本卡不可达**（候选与复核归 M2 lane） |
| `VALIDATION_ERROR` | 422 | 形参级校验、DTO 校验（`extra="forbid"` 命中未知字段）、N8/N9/N18、`status` 不在 `IMPORT_STATES` 白名单 |
| `EVIDENCE_REQUIRED` | 422 | N17（`__metadata__` 缺失、`synthetic` 非 true、`schema_version` 缺失） |
| `INVALID_SCOPE` | 422 | **本卡不可达**（无范围筛选面；`q`/`status` 的形状错误走 `VALIDATION_ERROR`） |
| `INPUT_TOO_LARGE` | 413 | §5.2 的三个上限（1 MiB JSON / 8 MiB 合成 / 64 MiB 普通） |
| `BAD_CURSOR` | 400 | `listImports` 的 `cursor` 签名不符 / 解码失败（`decode_cursor` 返回 `None`） |
| `BAD_REQUEST` | 400 | Content-Type 不是 `multipart/form-data`（两个上传 op）或不是 `application/json`（`configureImport`）；`Content-Length` 非整数 |

## 7. 事务边界与持久化

### 7.1 事务号与边界（体例＝实测 `application/activity_service.py:620` 的 `with connect(engine) as conn, conn.begin():`）

| TX | 方法（**待创建，S2**，`application/import_service.py`） | 事务内的写 | 说明 |
|---|---|---|---|
| `TX-I1` | `ImportService.create_import` | `artifacts` INSERT（经 `ArtifactWriter.commit`）· `imports` INSERT · `import_files` INSERT · `audit` INSERT · `idempotency` INSERT | 制品先落盘（事务外 `stage.write`，事务内 `commit` 登记），保证「DB 有行 ⇔ 磁盘有文件」 |
| `TX-I2` | `ImportService.attach_file` | 同上（少 `imports` INSERT，多 `imports` UPDATE） | `UNIQUE(workspace_id,import_id,table_name)` 违约 → 422（§2.4） |
| `TX-I3` | `ImportService.configure_mapping` | `source_mappings` INSERT · `imports` UPDATE · `audit` · `idempotency` | **先 INSERT 映射行、后 UPDATE `mapping_id`**：`imports` 的复合 FK `(workspace_id,mapping_id) → source_mappings` 要求被引用行已存在（连接实测开外键，`framework/DATA.md`「SQLite 与迁移」段） |
| `TX-I4` | `ImportService.accept_validation` | `jobs` INSERT（**复用** `worker/store.py::JobStore.enqueue`，禁重写队列）· `imports` UPDATE(`state`,`job_id`) · `audit` · `idempotency` | 202 的 `Location` 由 `Job.id` 组装；`Job.kind == "VALIDATE_IMPORT"`（实测在 `JobKind` 的 10 值 enum 内） |
| `TX-I5` | `ImportService.finish_validation` | `imports` UPDATE(`state`,`validation_digest`,`issue_json`) · `audit` | 由 `VALIDATE_IMPORT` 作业处理器在**作业租约事务内**调用；I5/I6 共用本方法 |
| `TX-I7` | `ImportService.fail_validation` | `imports` UPDATE(`state`,`validation_digest=NULL`,`issue_json='[]'`,`job_id`) · `audit` | 技术失败面（§3.2 I7） |

- **一方法一短事务**（体例＝`worker/store.py` docstring 第 1 条原文「`BEGIN IMMEDIATE` 短事务的开关与回滚」）；
  **重计算与文件传输在事务外**（`architecture/DOMAIN.md`「数据库迁移约定」段原文「事务外运行重计算与文件传输」）⇒
  `parse()` ＋ `ingest()`（可能吃 8 MiB / 510 行 / 4590 行）**必须**在 `conn.begin()` **之外**跑完，
  只把结果（`validation_digest` ＋ `issue_json`）写进事务。这是 I5/I6 的硬约束，S2 **禁**把 `ingest()` 挪进事务。
- **A81 SQL 写点唯一**：全部 DML 落在 `infra/db/repositories.py`（**纯追加**，A82：0 删除行）——
  新增 `ImportRecord` / `ImportFileRecord` / `SourceMappingRecord` / `ImportRepository` / `ImportFileRepository` /
  `SourceMappingRepository` / `import_from_row`，并追加进该模块的 `__all__`（实测现有 16 项，
  项数以实取为准、禁写死）。`domain/ingest/**` 与 `api/imports.py` **零 SQL**。

### 7.2 审计（`application/audit.py::AuditWriter` **只 import、禁改**、禁复制第二份链逻辑）

- 实测签名：`AuditWriter.write(conn, *, workspace_id, at, actor_id, role, action, target_kind, target_id, outcome,
  request_id, audit_id=None) -> AuditRecord`；`audit.py.__all__` 实测含 `OUTCOME_ACCEPTED`（`'ACCEPTED'`）可直接复用。
- 新增常量（**待创建，S2**，定义在 `application/import_service.py`，体例＝该模块自带 `ACTIVITY_ID_PREFIX` 的既有做法；
  **禁改** `application/audit.py`）：`TARGET_KIND_IMPORT = "import"`（实测 `ObjectRef.kind` 的 20 值 enum 内**含** `"import"`）、
  `ACTION_IMPORT_CREATED` / `ACTION_IMPORT_FILE_ATTACHED` / `ACTION_IMPORT_MAPPING_CONFIGURED` /
  `ACTION_IMPORT_VALIDATION_ACCEPTED` / `ACTION_IMPORT_VALIDATION_FINISHED`。
- 写 `DENIED` 的面：§3.4 的四条 409 `STATE_CONFLICT` ＋ 409 `VERSION_MISMATCH`（业务性拒绝）；
  **不写**审计的面：412 / 428 / 422 / 400 / 404（协议与形状问题，§6.2 末条）。
- `audit_id` 一律不传（由 `AuditWriter` 用实测的 `_AUDIT_ID_PREFIX = "aud"` 自行生成）。

### 7.3 显式时钟、ID 前缀与幂等键

- **显式时钟**：`at` / `created_at` 一律取注入的 `Clock.now()`（`Depends(get_clock)`，实测在 `api/deps.py.__all__`）；
  测试一律 `FixedClock`（实测在 `campaignlab.clock.__all__`）。**禁** `datetime.now()` / `time.time()`
  （卡片红线「不用系统当前时间做领域计算」）；`domain/ingest/**` **零时钟依赖**（§4.1）。
- **ID 前缀**（**待创建，S2**；体例＝实测 `WORKSPACE_ID_PREFIX="ws"` / `JOB_ID_PREFIX="J"` / `ACTIVITY_ID_PREFIX="act"` /
  `RULE_ID_PREFIX="rul"` / `ARTIFACT_ID_PREFIX="art"` / `_AUDIT_ID_PREFIX="aud"`，一律经
  `domain/ids.py::new_resource_id(prefix)`，实测签名 `new_resource_id(prefix: str) -> str`）：
  `IMPORT_ID_PREFIX: Final = "imp"` · `IMPORT_FILE_ID_PREFIX: Final = "imf"` · `SOURCE_MAPPING_ID_PREFIX: Final = "smp"`。
  三个前缀必须过 `is_resource_id`（实测在 `domain/ids.py.__all__`）与 `artifacts._safe_token` 的路径片段约束
  （实测禁 `/` `\` NUL、禁 `.`/`..`、禁以点或空格结尾）⇒ 上述三值均合法（纯小写字母）。
- **幂等键**：`IdempotencyKey(scope_key=workspace_id, actor_id=…, operation=<operationId>, idem_key=…)`
  （实测 `__dataclass_fields__` 恰为这 4 项）；`scope_key` 取 `workspace_id`，`operation` 取**逐字的 operationId**
  （`createImport` / `attachImportFile` / `configureImport` / `validateImport`），
  `GLOBAL_SCOPE`（实测存在于 `idempotency.__all__`）**不用**（本卡四个写 op 全部工作区作用域）。

### 7.4 文件底座 `infra/files.py`（**待创建，S2**；卡片红线「不把 duckdb 关系导入绕过 `infra/files.py` 的摘要登记」）

- **禁改** `infra/artifacts.py`（卡片 `scope_deny` 显式列出）⇒ 一律**复用**其公开面（实测在 `artifacts.__all__`）：
  `ArtifactWriter`（实测 `__init__(data_dir, *, artifacts=None)`，内部实测已用 `ArtifactRepository.insert`，
  docstring 原文「写路径复用 `ArtifactRepository.insert`（本模块零 DML）」）·
  `AttemptStage`（实测方法 `write` / `write_file` / `seal` / `discard` / `mark_committed`，属性 `sha256` / `byte_size` / `path`）·
  `CommittedArtifact`（实测字段 `workspace_id, artifact_id, kind, sha256, relative_path, byte_size, path, reused_file, reused_row`）·
  `hash_file(path, *, chunk_size=1048576) -> tuple[str, int]` · `relative_path_for(*, kind, workspace_id, sha256) -> str`。
- `ARTIFACT_KIND_IMPORT_FILE: Final = "IMPORT_FILE"`（**待创建，S2**，`infra/files.py`）。
  合法性依据：`relative_path_for` 的实测 docstring 原文「形状：`results/<kind>/<workspace_id>/<sha256[:2]>/<sha256>`。
  三段前缀都是刻意的：`kind` 分桶让 M1/M2 的多类制品互不混淆」⇒ `kind` 是**自由 token**（只过 `_safe_token`），
  传 `IMPORT_FILE` **无需**改 `artifacts.py`；且落点在 `results/**` 内 ⇒ 自动受既有
  `sweep_unreferenced`（实测扫描面「**只有** `results/**` 与 `tmp/jobs/**`」）的引用边界保护。
- **暂存目录的语义代价（如实记录）**：`ArtifactWriter.begin(workspace_id, job_id, attempt)` 的实测形参名是
  `job_id`，暂存根实测为 `<data_dir>/tmp/jobs`（`stage_root` docstring 原文）⇒ 本卡冻结
  `begin(workspace_id, job_id=<import_id>, attempt=<该导入下的第几个上传件，从 0 起>)`。
  `import_id` 用 `imp` 前缀 ⇒ 过 `is_resource_id`。**代价**：导入的暂存目录物理上落在 `tmp/jobs/**` 下，
  名字不副实。已开 **§12 U-11**（是否另立 `tmp/imports/**` 需改 `artifacts.py` ＝ `scope_deny`）。
- `infra/files.py` 的公开面（**待创建，S2**）：`ARTIFACT_KIND_IMPORT_FILE` · `UPLOAD_CHUNK_BYTES` ·
  `ImportFileStore`（方法 `stage_from_chunks` / `register` / `label_from_filename`）· `ImportFileRef`。
  **摘要登记的唯一入口**＝`ImportFileStore.register`（内部只调 `ArtifactWriter.commit` ⇒ 零 DML，A81 不破）；
  任何「把文件塞进 DuckDB / Parquet 的关系导入」都必须先经它拿到 `artifact_id`（卡片红线）。

## 8. 逐 op 的可达码矩阵（声明面一律 `declared_responses(<2xx>)` 的 **12** 个码；本表只标**可达**面）

| op | 可达（触发面见 §5 / §6.4） | 声明但**不可达**（S6 断言不可达本身，禁 `skip`/`xfail`） |
|---|---|---|
| `createImport` | 400 `BAD_REQUEST`（Content-Type / Content-Length）·401 `SESSION_EXPIRED`·403 `ORIGIN_DENIED`/`ACCESS_DENIED`·404 `RESOURCE_NOT_FOUND`（工作区不存在或属外）·409 `IDEMPOTENCY_CONFLICT`·413 `INPUT_TOO_LARGE`（8 MiB / 64 MiB）·422 `VALIDATION_ERROR`（`UploadFields`、幂等键形状、`table_name` 重复、N18）·422 `EVIDENCE_REQUIRED`（N17）·500 `INTERNAL_ERROR` | **412 `REVISION_CONFLICT`**·**428 `PRECONDITION_REQUIRED`**（本 op 无 `If-Match` 形参，切片实测）·429 `JOB_CAPACITY`·409 的 `VERSION_MISMATCH`/`STATE_CONFLICT`/`SNAPSHOT_CONFLICT`/`STALE_CANDIDATE`/`ACTION_REVIEW_REQUIRED`·400 `BAD_CURSOR`·422 `INVALID_SCOPE` |
| `attachImportFile` | `createImport` 的全部可达码（404 另含 `import_id`）**＋** 428（缺 `If-Match`）·412（不匹配）·409 `STATE_CONFLICT`（`IMPORT_BUSY` / `IMPORT_PUBLISHED`） | 429·409 的 `VERSION_MISMATCH`/`SNAPSHOT_CONFLICT`/`STALE_CANDIDATE`/`ACTION_REVIEW_REQUIRED`·400 `BAD_CURSOR`·422 `INVALID_SCOPE`·422 `EVIDENCE_REQUIRED`（本 op 不解析文件内容，只登记 ⇒ N17 归 `createImport` 与 `validateImport`） |
| `configureImport` | 400 `BAD_REQUEST`·401·403·404·409 `IDEMPOTENCY_CONFLICT`/`STATE_CONFLICT`/`VERSION_MISMATCH`·412·413（1 MiB JSON 上限）·422 `VALIDATION_ERROR`（`ImportConfigure` DTO、N8、N9、N18）·428·500 | 429·400 `BAD_CURSOR`·409 `SNAPSHOT_CONFLICT`/`STALE_CANDIDATE`/`ACTION_REVIEW_REQUIRED`·422 `EVIDENCE_REQUIRED`/`INVALID_SCOPE` |
| `validateImport` | 400·401·403·404·409 `IDEMPOTENCY_CONFLICT`/`STATE_CONFLICT`（`IMPORT_NOT_CONFIGURED` / `IMPORT_BUSY` / `IMPORT_PUBLISHED`）·412·413（无正文 ⇒ 仅 `Content-Length` 非零时的形状判定）·422·**429 `JOB_CAPACITY`**（`worker/capacity.py::check_capacity` 既有面，`Retry-After` 由 `problem_response` 从异常的 `retry_after` 落成头）·428·500 | 400 `BAD_CURSOR`·409 `VERSION_MISMATCH`/`SNAPSHOT_CONFLICT`/`STALE_CANDIDATE`/`ACTION_REVIEW_REQUIRED`·422 `EVIDENCE_REQUIRED`/`INVALID_SCOPE`（N17 在**作业内**判定 ⇒ 落 `imports.issue_json` 与 I6，不走 HTTP 422） |
| `getImport` | 401·403·404·500 | 400 两码·409 全部·412·413·422 全部·428·429 |
| `listImports` | 400 `BAD_CURSOR`·401·403·404·422 `VALIDATION_ERROR`（`limit`/`q`/`status` 形状、`status` 不在 `IMPORT_STATES`）·500 | 409 全部·412·413·428·429·400 `BAD_REQUEST`·422 `EVIDENCE_REQUIRED`/`INVALID_SCOPE` |

> 本表**不是**第二份状态码清单：期望值一律由「路由装饰器 `declared_responses()` 的实现侧」与
> 「切片 `operations.<opId>.operation.responses` 的声明侧」对撞得出（A95 / A260），错误码一律由
> `domain/errors.py::PROBLEM_CODES`（实测 20 项）反查，**禁自造码**（D-019）。
> 本表只承载「哪些码在本卡有触发面」这一设计判断，供 S6 枚举用例、供 Q 判定档复核「声明了但不可达」的断言是否齐全。
## 9. 边界清单（AC → 实现约束 → 已知失败模式）

### 9.1 AC-005（切片 `acceptance_rows.AC-005` 逐字：「A 样例注入重复切片、负人数、层级倒置和错误行长。B 注入重复码及孤立切片」→「校验返回具体行列，旧验证失效，正式快照未被更新。原型 v0.1 合成文件大于 8 MiB 拒绝」；主证据：导入 API、数据库）

| AC 分句 | 实现约束（本文的冻结位点） | 已知失败模式（S6 必须各落一条有牙的守护） |
|---|---|---|
| 「A 样例注入重复切片」 | N1 `DUPLICATE_SLICE`；`entity_table` 内 `dimensions.id` 唯一 | 只查相邻行 ⇒ 隔行重复漏检；用 `dict` 去重时**保留首行**而 `location` 指向首行（应指向**后出现**的行） |
| 「负人数」 | N2 `NEGATIVE_COUNT`；`count_fields` 9 键归一后 `>= 0` | CSV 通道下 `-1` 被 `int()` 前的 `isdigit()` 判成非数字 ⇒ 报 `NOT_AN_INTEGER` 而非 `NEGATIVE_COUNT`（码错＝证据不可用） |
| 「层级倒置」 | N3 `FUNNEL_INVERSION`；链条 `eligible ≥ sent ≥ success ≥ executed ≥ contacted ≥ effective`（DATA.md「名单阶段链逐级不增」） | `None`（缺值）参与比较 ⇒ `TypeError` 或静默跳过；`capacity`/`intentCount`/`activityCount` 被误纳入链条（DATA.md 原文只说「名单阶段链」，且「容量、意向次数、活动特色依字典单位」） |
| 「错误行长」 | N4 `ROW_LENGTH_MISMATCH`；`len(row) != len(columns)` | CSV 里带引号逗号的单元格被朴素 `split(',')` 切碎 ⇒ 行长误判（必须用 `csv` 模块，实测 `slices.csv` 无引号字段但**禁**依赖此巧合） |
| 「B 注入重复码」 | N5 `DUPLICATE_CODE`；长表 `(切片键, 指标码)` 唯一（DATA.md「long 的阶段先按长表切片键和指标码唯一连接」） | 用 `指标码` 的**源列名**（`指标码`）而不是 `mapping.long_columns["metric"]` 取值 ⇒ 换一份映射就失效 |
| 「B 注入孤立切片」 | N6 `ORPHAN_SLICE`；长表 `切片键` ⊆ 实体表 `dimensions.id` | 反向漏检：实体表有切片但长表**没有**任何阶段项 ⇒ 那是 N7 `MISSING_STAGE`，两个码禁混用 |
| 「校验返回具体行列」 | §4.4 的 `location` 三段语法 ＋ 1-based 数据行号 ＋ 规范键 | 用源列名 ⇒ CSV 与 JSON 的 `location` 不同，AC-006 的同值面被破坏；用 0-based ⇒ 与 `API.md`「1 起数据行号」原文冲突 |
| 「旧验证失效」 | §5.3：I2/I3 清空 `validation_digest` ＋ `issue_json` ＋ `revision+1`；摘要含 `mapping_digest` 双层保证 | 只清 `validation_digest` 不清 `issue_json` ⇒ `Import.issues` 仍显示旧问题；或忘了 `revision+1` ⇒ 旧 `If-Match` 仍可用（412 不触发） |
| 「正式快照未被更新」 | §5.3：`snapshots` 表零写入、`imports.snapshot_id` 恒 `NULL` | 为了「让校验看起来完成」而顺手写 `snapshot_id` ⇒ 越界到 M1-02，且 FK 指向不存在的行会直接 `IntegrityError` |
| 「原型 v0.1 合成文件大于 8 MiB 拒绝」 | §5.2：`format=="LEGACY_SYNTHETIC_JSON"` → 8 MiB；三段判定；413 `INPUT_TOO_LARGE` | 用 1 MiB 的 JSON 上限当文件上限（ADR-005 §2.3 明禁混用）；或先 `await request.body()` 全量读入再判长度（＝没有上限，`read_body_within_limit` docstring 原文即此警告）；或 413 抛出时暂存目录已落地未 `discard()` ⇒ 「留半成品」 |

### 9.2 AC-006（切片 `acceptance_rows.AC-006` 逐字：「A、B、六行 CSV 与等价 SOURCE_JSON 分别导入」→「A/B 各 510 切片。B 长表 4590 阶段项。元分归一后远程值一致。CSV/JSON 同值，源行和文件摘要可追溯」；主证据：DB、制品、页面）

| AC 分句 | 实现约束 | 已知失败模式 |
|---|---|---|
| 「A/B 各 510 切片」 | `SliceCounts.slice_count`；实测 `bank-a.json.tables["月度宽表"].rows` ＝ 510、`bank-b.json.tables["统计切片"].rows` ＝ 510 | 长表布局下把 `stage_item_count`（4590）当成 `slice_count` ⇒ B 报 4590；或宽表下按 `counts_table` 计（A 的 `entity_table == counts_table`，恰好也是 510 ⇒ **这个错误在 A 上看不出来**，必须在 B 上钉住） |
| 「B 长表 4590 阶段项」 | `SliceCounts.stage_item_count` ＝ `mapping.counts_table` 的源行数；实测 4590 ＝ 510 × 9 | 把「非空计数单元数」当阶段项数（缺值行会少算）；或把 A 的 `stage_item_count` 也算成 4590（A 是宽表，实测其 `counts_table` 行数 ＝ 510） |
| 「元分归一后远程值一致」 | §4.3 / §4.5：`CNY_YUAN × 100`（只用 `Decimal`）；实测 A `rows[0]["AUM变动"] == 182260` 与 B `rows[0]["amount_01_fen"] == 18226000` 归一后**同为 18226000** | 用 `float` ⇒ `182260 * 100` 虽恰好精确，但 `267100.0` 一类值在别的行会漂移；或忘了 B 已是分 ⇒ 又乘 100 变成 1822600000 |
| 「CSV/JSON 同值」 | §4.0 保证 3；实测 `slices.csv` 表头与 `source.json` 的 `columns` 逐字相等、6 数据行在数字串→int 归一后逐格相等、两份 `metadata` `==` 为 `True` | CSV 全按字符串比较 ⇒ `"0" != 0`；或 CSV 的 `row_number` 把表头算进去 ⇒ 与 JSON 差 1，`location` 不一致 |
| 「源行…可追溯」 | `NormalizedSlice.source_row`（`source_file_id` / `table_name` / `row_number`）＋ `contributing_rows` | 长表下只留 `source_row` 丢掉 `contributing_rows` ⇒ 9 个阶段项无法回溯到具体行；或 `source_file_id` 填了 `artifact_id` 而不是 `import_files.id`（DATA.md 原文是「source_row 由导入器生成，含 source_file_id、table_name、row_number」，本文冻结 `source_file_id == import_files.id`，见 §12 U-12） |
| 「…文件摘要可追溯」 | §4.7 三层摘要；`ImportFile.sha256`/`.size_bytes` 经 `artifacts` JOIN；`validation_digest` 的 `files` 段含每个上传件的 sha256 | `validation_digest` 里放了 `created_at` / `job_id` / `import_id` ⇒ 同输入不同摘要（违反 DOMAIN.md「业务摘要排除运行时间、作业号、租约和随机资源 ID」），M1-02 发布时的「摘要必须仍匹配」必然失败 |
| 「页面」（主证据之一） | **本卡无前端写权**（`web/**` 在 `scope_deny`，属 F lane）⇒ 页面证据由 S8 记为「判定归 F/M5 lane」，**禁**在 `evidence/M1/M1-01/ac.md` 里自行宣称通过 | 为了凑「主证据」而伪造页面截图 ⇒ 直接判缺陷 |

### 9.3 本卡**不**承担的面（写清以免 S2–S8 越界）

- `publishImport` / `snapshots` 写入 / I8–I10（归 **M1-02**）；`correctSnapshot`（归 M1-02）；
  口径与语义键的**判定**（归 **M1-03**）；去重区间的**算术**（§4.6，归 M1-02/M1-03）；
  渠道事件重算与关联（`architecture/DATA.md`「渠道事件重算」段，归 M2 lane）；页面（F lane）；
  `worker/**` 的任何改动（M0-04，卡片 `scope_deny`）；`migrations/**`（三张表实测已建好）。
- `VALIDATE_IMPORT` 作业处理器的**注册点**在 `worker/**` 之外，但注册动作本身落在装配面 ⇒ 写权缺口，见 §11.8。

## 10. 验证清单（命令 → 期望 rc；供 **S6–S8** 直接采集，**无「人工确认」项**；计数一律指向 `state.json.counts` 现值，**禁写死**）

> 全部命令在 WSL 仓库根 `/home/szf/dev/CampaignLab` 执行，前置
> `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"`；Python 一律 `uv run --no-sync`（PRE-21：禁系统 `python3`）。
> **rc 语义（PRE-34，逐字携带）**：`rc=0` 绿；**`rc=1` ＝ 断言红**（有用例失败）；
> **`rc=4` ＝ 收集期错误**（用法错／导入错／**包标记缺失**）；`rc=5` ＝ 没有收集到任何用例。
> `rc=4` 与 `rc=1` **禁混报**：出现 `rc=4` 一律先查 `__init__.py`（§11 已逐件点名）再谈断言。
> **A260**：一切状态码判据走「装饰器 `declared_responses()` vs 切片声明」的**静态**对撞，
> **禁**写 `resp.status_code == 2xx` 这类运行期断言（信封承载状态码 ⇒ 结构性 NO_TEETH）。

| # | 命令 | 期望 |
|---|---|---|
| V1 | `uv run --no-sync pytest -q tests/golden/ingest -k counts` | rc=0（卡片 `M1-01.md:14` gate 原文）；**且** `--collect-only` 实测选中数 `>= 3`（§5.1 的三个 `counts` 用例），选中数为 0 即 `NO_TEETH`，如实报不得写 PASS |
| V2 | `uv run --no-sync pytest -q tests/domain/ingest -k locate` | rc=0（卡片 `:15`）；`--collect-only` 选中数 `>= 6`（N1–N6） |
| V3 | `uv run --no-sync pytest -q tests/domain/ingest -k size_limit` | rc=0（卡片 `:16`）；`--collect-only` 选中数 `>= 4`（§5.1 的四个 `size_limit` 用例） |
| V4a | `uv run --no-sync pytest -q tests/domain/ingest -k csv_equivalence` | rc=0；`--collect-only` 选中数 `>= 3`。**A275：本行与 V4b 是两条独立命令，禁合并成卡片 `:17` 的双 `-k` 单行形态**（`-k` 是 argparse `store` 型，后者覆盖前者 ⇒ 双 `-k` 的结果恰等于后一个，`csv_equivalence` 会被静默丢弃） |
| V4b | `uv run --no-sync pytest -q tests/domain/ingest -k stale_validation` | rc=0；`--collect-only` 选中数 `>= 3`。与 V4a 独立采集、独立记 rc |
| V5 | `uv run --no-sync pytest -q tests/integration/jobs -k validate_import` | ⚠ **NO_TEETH（本轮实测）**：`--collect-only` 输出 `no tests collected (98 deselected) in 0.05s`、rc=0 ⇒ 该 gate 现在**空转即绿**。S8 采集时**必须**同时记 `--collect-only` 的选中数；选中数为 0 时如实标 `NO_TEETH`，**禁**标 PASS。补牙方案见 §12 U-2（用例文件在 `tests/integration/jobs/**` ＝ M0-04 的 scope，本卡只跑不改） |
| V6 | `uv run --no-sync pytest -q tests/domain/ingest -k single_validator` | rc=0（§4.0 的三条结构性保证）：① `format` 只在 `parse.py` 出现（AST 扫 `domain/ingest/*.py`，`normalize.py`/`validate.py` 内出现 `format` 属性访问或 `ImportFormat` 名字即判红）；② `normalize`/`validate` 的 `inspect.signature` 形参名集合**不含** `format`；③ `layout` 分支在 `normalize.py` 内**恰 1 处**（AST 计数）。选中数 `>= 3` |
| V7 | `uv run --no-sync pytest -q tests/domain/ingest` 与 `uv run --no-sync pytest -q tests/golden/ingest` | 各自 rc=0（两目录的**全量**，防 `-k` 空转掩盖红点） |
| V8 | `uv run --no-sync pytest -q tests/api/imports` | rc=0（§1/§6/§8 的路由面：6 个 op 的 `operation_id` 逐字、`declared_responses` 声明面 vs 切片、`If-Match` 可选形参形态、`IF_MATCH_PATTERN` 单源、逐 op 的可达/不可达码矩阵） |
| V9 | `uv run --no-sync ruff check .` · `uv run --no-sync ruff format --check .` · `uv run --no-sync mypy` · `uv run --no-sync pytest -q` | 各自 rc=0（**以 rc 为判据、计数不写死**；分母现值一律指向 `state.json -> resume.self_check_gates_rc0.counts` 的 `.ruff_lint_scope_files` / `.ruff_formatted_files` / `.mypy_source_files` / `.pytest_passed`） |
| V10 | `uv run --no-sync python scripts/check_contracts.py check --validate` | rc=0（卡片 `:21`；登记项数以 `.counts.contract_registered_nodes` 为准、AC 分母以 `.counts.acceptance_denominator` 为准，**禁写死**） |
| V11 | `uv run --no-sync python -c "import hashlib,pathlib;d=pathlib.Path('contracts/openapi.json').read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))"` | rc=0 且输出与 `.counts.live_openapi_sha16` / `.live_openapi_bytes` 现值一致（卡片 `:19` 切片新鲜度）；不一致即回报 **T lane 重切**，**禁自行重切**（`scripts/**` 不在 `scope_allow`） |
| V12 | `uv run --no-sync python -c "import json,pathlib;s=json.loads(pathlib.Path('orchestrator/handoff/M1-01.slice.json').read_bytes());print(s['spec_version'],sorted(s['operations']))"` | rc=0 且 `spec_version` 与 `.counts.live_openapi_info_version` 一致、6 个 operationId 与本文 §1.1 表逐字相同（**禁硬编码** `spec_version`，卡片 `source.rule` 原文） |
| V13 | `uv run --no-sync pytest -q tests/unit/test_if_match_pattern_single_source.py` | rc=0（A271/FU-59 的单源守护；本文要求 `imports` 的三个 `If-Match` 端点一律 import `IF_MATCH_PATTERN`，禁内联第二份正则） |
| V14 | `uv run --no-sync pytest -q tests/unit/test_domain_errors.py` | rc=0（`len(common.__all__)` 的同族钉桩已按 §2.5 方案 A 同步；`DomainError` 子类数钉桩 13 未被破坏 ⇒ 证明本卡**没有**新增异常类） |
| V15 | 新增 `conftest.py` 或**与既有文件同 basename** 的新文件后，跑一次**全树** `uv run --no-sync mypy` | rc=0（LANE-COMMON §3.6 `rule_full_tree_mypy_on_basename_collision`：路径限定 mypy **不触发**跨目录重复模块名检测。本卡强制项 —— S6 会新建 `tests/domain/ingest/__init__.py` 与 `tests/domain/ingest/conftest.py`，二者都与既有 `tests/domain/activity/` 下的同名文件**同 basename**；S7 会新建 `tests/golden/ingest/{__init__,conftest}.py`，同族） |
| V16 | `uv run --no-sync pytest -q tests/unit/test_task_cards.py` | rc=0（卡片 `:58` 的派单前置；本卡**禁改卡片**，故本条只证明「设计文没有倒逼改卡」） |

### 10.1 正向对照（PC）要求（LANE-COMMON §6；**S6/S7 的交付缺此即判红**）

- §10 的 V1–V8、V13、V14 每一组守护都必须由实现方**主动制造一次 RED**、把**原始输出**落进
  `evidence/M1/M1-01/gates/`（文件名 `V<n>-positive-control.log`）、再复原并复验绿。
  **只交绿证据无法区分「守护有效」与「守护恒绿」**。
- 复原必须**可证**：改前快照与复原后的 sha256 **双向核验**，两个摘要都写进证据。
- 探针一律用 pytest 的 `tmp_path`，**禁落工作树**（否则污染 ruff/mypy 分母）。
- 每条守护**自带分母断言**（防 glob 扫空导致全绿）：`-k` 类守护一律附 `--collect-only` 的选中数下限（见上表）。
- PC 的**最小配方**（逐条给 S6，禁自行发明）：V1 → 把 `bank-a` 的期望 510 临时改成 509；
  V2 → 把 `DUPLICATE_SLICE` 的 `location` 临时改成整行形状；V3 → 把 `max_bytes_for_format` 的 8 MiB 临时改成 64 MiB；
  V4a → 把 `_coerce_cell` 的 CSV 整数归一临时关掉；V4b → 把 I3 的 `validation_digest=NULL` 临时去掉；
  V6 → 在 `validate.py` 里临时加一行 `if source.format == "SOURCE_CSV":`；
  V8 → 把某个装饰器的 `operation_id` 临时改小写；V13 → 在 `api/imports.py` 里临时内联一份 `If-Match` 正则；
  V14 → 临时给 `api/common.py.__all__` 加一个不存在的名字。
  **每个配方复原后必须复验绿**，且 RED 的 rc 必须是 **1**（不是 4）——若出现 4，说明 PC 制造方式错了，重做。
## 11. 文件级 TODO（S2–S8 严格按此机械铺开；不得越出下列文件与符号，越界即回报编排器，手册 §6.4）

> 格式 ＝ `路径:符号,符号,…`（与 `M0-04-design.md` §9 同体例）。**标注「⚠写权缺口」的路径不在任务卡
> `scope_allow`（`M1-01.md:22`）内**，必须先拿到 §12 对应 U 项的裁定才能动；未裁定前 S2–S8 **禁**自行创建或修改
> （手册 §6.4：flash 遇设计外问题必须回报，不得自行决定）。
> 本文**不写死**任何符号面计数与工具裁决：`__all__` 项数、用例数、分母一律 `inspect` / `--collect-only` 实取，
> import 序以 `ruff check --select I --diff` 实取为准（R8-1 / A115 / R12-4）。
> **棒号 ↔ 卡片 `M1-01.md:32–49` 档位表逐棒对应**（档位与预估 token 逐字抄卡片，禁改）：
> S2 `qwen3.8-max` high / 45k → §11.1–§11.3 · S3 `qwen3.8-flash` / 12k → §11.4 · S4 `qwen3.8-flash` / 10k → §11.5 ·
> S5 `qwen3.8-flash` / 8k → §11.6 · S6 `qwen3.8-flash` / 7k → §11.7 · S7 `qwen3.8-flash` / 5k → §11.8 ·
> S8 `qwen3.8-flash` / 6k → §11.9。（S1 ＝ 本文，`qwen3.8-max` high / 55k，已交付。）

### 11.1 S2（`qwen3.8-max` high，45k，`src/campaignlab/domain/ingest/**` ＋ `src/campaignlab/infra/files.py`，**只新建**；纯领域层＋文件底座，禁 SQL、禁开事务、禁 import `campaignlab.api`）

- `src/campaignlab/domain/ingest/__init__.py`（**A276 形态：单行 docstring，禁零字节空文件**；依据＝仓内既有 tests/src 包标记无一为零字节，实测例 `tests/api/activities/__init__.py` ＝ 1 行 / 89 B / `8ccc54fe0ab9`）
- `src/campaignlab/domain/ingest/model.py:FileRef,RawTable,RawSource,SourceRow,NormalizedSlice,MappingSpec,LongColumnSpec,Finding,SliceCounts,IngestResult,IngestLimits,DEFAULT_LIMITS,UploadPayload,UploadedFile,SliceKey,INGEST_SEVERITIES`（全部 `@dataclass(frozen=True, slots=True)`，字段序逐字按 §4.1／§4.3）
- `src/campaignlab/domain/ingest/states.py:ImportState,ImportFormat,IMPORT_STATES,IMPORT_FORMATS,IMPORT_TERMINAL_STATES,ImportTransitionId,ImportTransition,IMPORT_TRANSITIONS,INGEST_STATE_ISSUE_CODES,assert_import_transition_allowed,is_import_terminal`（§3；`ImportTransition` 的 8 个字段名逐字对齐实测的 `worker/states.py::Transition`）
- `src/campaignlab/domain/ingest/limits.py:SYNTHETIC_V01_MAX_BYTES,GENERIC_UPLOAD_MAX_BYTES,MAX_FILES_PER_IMPORT,max_bytes_for_format,assert_within_size_limit`（§5.2；`InputTooLarge` 从 `campaignlab.domain.errors` import，**禁新增异常类**）
- `src/campaignlab/domain/ingest/locate.py:LocationParts,make_location,parse_location,LOCATION_MAX_LENGTH`（§4.4；`LOCATION_MAX_LENGTH: Final = 500` ← 实测 `Issue.location.maxLength`）
- `src/campaignlab/domain/ingest/digests.py:VALIDATION_DIGEST_KIND,DIGEST_LENGTH,PARSER_VERSION,validation_projection,validation_digest,mapping_digest,metadata_digest`（§4.7；`canonicalize` 一律**注入**，体例＝实测 `domain/activity/digests.py::rule_digest(…, *, canonicalize)`）
- `src/campaignlab/domain/ingest/normalize.py:normalize`＋私有 `_normalize_wide,_normalize_long,_coerce_cell,_to_fen,_map_code`（§4.2 ②；`layout` 分支**恰 1 处**）
- `src/campaignlab/domain/ingest/validate.py:validate,INGEST_ISSUE_CODES`＋每条负例一个私有 `_check_*`（§5.1 的 N1–N18 逐条一个函数，函数名后缀用码名的小写，便于 V6 的 AST 守护与 §10.1 的 PC 配方定位）
- `src/campaignlab/domain/ingest/parse.py:ParseAdapter,PARSE_ADAPTERS,parse,PARSER_VERSION`＋`legacy_mapping_to_source_mapping`（§4.2 ①；**本棒只落骨架与注册表**，三个 `parse_*` 适配器由 S3/S4 填）
- `src/campaignlab/domain/ingest/api.py:parse,ingest`（§4.1 的唯一入口；**`public_frozen` 面**，改动走 CR）
- `src/campaignlab/infra/files.py:ARTIFACT_KIND_IMPORT_FILE,UPLOAD_CHUNK_BYTES,ImportFileRef,ImportFileStore,label_from_filename`（§7.4；**零 DML**，只调 `ArtifactWriter.begin/seal/write/commit/discard` 与 `ArtifactRepository`）
- **METADATA_TABLE_NAME**（`"__metadata__"`）落 `parse.py`（§4.2）
- S2 **禁触碰**：`application/**`、`infra/db/**`、`api/**`、`worker/**`、`migrations/**`、`contracts/**`、`spec/**`、`scripts/**`、`web/**`、`tests/**`（除 §11.2/§11.3 拿到裁定后的那几件）

### 11.2 S2 附带的契约 DTO 面（⚠写权缺口：`src/campaignlab/api/common.py`、`tests/unit/test_domain_errors.py`；授权依据＝§2.5 方案 A ＋ A91 同构 append-only）

- `src/campaignlab/api/common.py`（**纯追加、0 删除行**，A82）：
  `ImportFile,Import,ImportPage,ImportConfigure,SourceMapping,LongColumns,UploadFields,AttachFileFields,MappingLayout,SourceMoneyUnit,DedupMode`
  ＋ `from campaignlab.domain.ingest.states import ImportFormat, ImportState`（体例＝实测 `api/common.py:50`
  `from campaignlab.domain.activity.states import (`；运行期必须 `common.ImportState is states.ImportState` → `True`）
  ＋ 上述**全部**新名字追加进 `__all__`（`no_implicit_reexport` 已开，LANE-COMMON §3.5）。
  项数**以 `inspect` 实取为准，本文不写死**（本轮实测基线 `len(common.__all__) == 80`）。
- `tests/unit/test_domain_errors.py`：**只改** `:176` 与 `:177` 两行的钉死整数（实测原文
  `assert len(common.__all__) == 80` / `assert len(set(common.__all__)) == 80`），改成**同一个实取值**。
  ⚠ 元守护 `tests/unit/test_if_match_pattern_single_source.py::test_all_common_surface_pins_agree_with_runtime`
  要求「所有钉桩整数两两相等且等于运行期实测」且「钉桩处数 `>= ALL_COUNT_PIN_SITES_FLOOR`（实测 2）」⇒
  **两行必须同批改、禁删任何一行**；位点清单一律用该模块的 `all_count_pins(in_scope_sources())` **实取**（禁写死处数）。
  **A115 建议**：改成实取对撞（例如与切片 schema 的属性数对撞）而不是改数字 —— 但该文件不在本卡 `scope_allow`，
  改法本身也要裁定 ⇒ 见 §12 U-5。
- **禁改** `tests/unit/test_domain_errors.py:109` 的 `assert len(expected) == 13`（本卡零新增 `DomainError` 子类，§2 开头）。

### 11.3 S2 附带的应用层与基础设施层（⚠写权缺口：`application/`、`infra/db/repositories.py`、`api/deps.py`、`api/app.py`）

- `src/campaignlab/application/import_service.py`（**新建**；体例＝既有 `application/activity_service.py` 与
  `application/workspace_service.py`，事务写法逐字对齐实测的 `activity_service.py:620`
  `with connect(engine) as conn, conn.begin():`，`connect` import 自 `campaignlab.infra.db.engine`）：
  `IMPORT_ID_PREFIX,IMPORT_FILE_ID_PREFIX,SOURCE_MAPPING_ID_PREFIX,TARGET_KIND_IMPORT,ACTION_IMPORT_CREATED,ACTION_IMPORT_FILE_ATTACHED,ACTION_IMPORT_MAPPING_CONFIGURED,ACTION_IMPORT_VALIDATION_ACCEPTED,ACTION_IMPORT_VALIDATION_FINISHED,ImportService`
  （方法：`create_import,attach_file,configure_mapping,accept_validation,finish_validation,fail_validation,get_import,list_imports`；
  事务号 ↔ 方法的一一对应见 §7.1；行→DTO 一律 import `infra.db.repositories.import_from_row`，**不复制**）
- `src/campaignlab/infra/db/repositories.py`（**纯追加、0 删除行**，A81 SQL 写点唯一 ＋ A82）：
  `ImportRecord,ImportFileRecord,SourceMappingRecord,ImportRepository,ImportFileRepository,SourceMappingRepository,import_from_row,import_file_from_row,source_mapping_from_row`
  ＋ 列序常量 `_IMPORT_COLUMNS,_IMPORT_FILE_COLUMNS,_SOURCE_MAPPING_COLUMNS`（体例＝实测该文件 `:62`/`:65`/`:72`/`:79` 的
  `_WORKSPACE_COLUMNS`/`_JOB_COLUMNS`/`_ACTIVITY_COLUMNS`/`_BINDING_COLUMNS`）＋ 全部新名字进 `__all__`（实测现 16 项，禁写死）
- `src/campaignlab/api/deps.py`（**纯追加**，一律采 **A233 的 `TYPE_CHECKING` 块形态**规避 ruff `I001`）：
  `ImportService`（Protocol）· `get_import_service(request: Request) -> ImportService` ＋ 两者进 `__all__`（实测现 13 项）
- `src/campaignlab/api/app.py`（**A90① / A10 最小例外，≤3 行**；体例＝实测该文件里
  `# M0-04/S4（A10 最小例外，≤3 行）：app.include_router(jobs.router)` 与其下 `app.include_router(jobs_router)`）：
  ① `from campaignlab.api.imports import router as imports_router`；② `app.include_router(imports_router)`；
  ③ 若 `ImportService` 需要 `app.state`，追加 `app.state.import_service = …` 一行。**总追加行数 ≤ 4**，0 删除行。
- `VALIDATE_IMPORT` 作业处理器的**注册**（I5/I6/I7 的执行方）：处理器实现落
  `src/campaignlab/application/import_jobs.py:ValidateImportHandler`（**新建**，只调 `ImportService.finish_validation` /
  `.fail_validation` 与 `domain/ingest/api.py::ingest`）；**注册点**在装配面（`api/app.py` 或 `worker/deps.py` 的
  `registry` 构造处，后者在 `scope_deny`）⇒ 本文冻结注册落 `api/app.py` 的同一处最小例外内，**已开 §12 U-13**。

### 11.4 S3（`qwen3.8-flash`，12k，`src/campaignlab/domain/ingest/**`，**只改 `parse.py`**）：A/B JSON 解析器（严格按 §4.1/§4.2 的签名机械展开字段映射，**禁**新增校验分支）

- `parse.py:parse_legacy_synthetic`（`LEGACY_SYNTHETIC_JSON`；实测输入形状＝`bank-a.json` / `bank-b.json` 均为
  **单行压缩 JSON**（1 行 / 147272 B 与 1 行 / 291343 B）⇒ **禁按行数推断结构**，一律 `json.loads` 后按
  实测键序 `schemaVersion,synthetic,bankId,bankName,snapshotVersion,description,mapping,tables,metadata` 取；
  `metadata` 实测 15 键）
- `parse.py:legacy_mapping_to_source_mapping`（camelCase → snake_case 的**显式**键名映射：
  `version→id`、`entityTable→entity_table`、`countsTable→counts_table`、`countFields→count_fields`、
  `moneyFields→money_fields`、`longColumns→long_columns`、`moneyDivisor→source_money_unit`；
  ⚠ `moneyDivisor` 实测 A=`1`、B=`100` ⇒ 映射规则冻结为 `1 → "CNY_YUAN"`、`100 → "CNY_FEN"`，
  **其余值一律报 422 `VALIDATION_ERROR`**（`Issue.code="UNSUPPORTED_MONEY_DIVISOR"`），禁静默折算；
  `bankId→bank_id`、`layout`/`dimensions`/`codes`/`dedup_mode` 实测**同名同形**，直传）
- **禁改** `normalize.py` / `validate.py` / `api.py` / `model.py`（签名已由 S1 冻结；发现问题回报，禁自行决定）

### 11.5 S4（`qwen3.8-flash`，10k，`src/campaignlab/domain/ingest/**`，**只改 `parse.py`**）：六行 CSV 与等价 SOURCE_JSON 解析器（同 §11.4 规范，**不新增校验分支**）

- `parse.py:parse_source_json`（实测输入形状＝`csv-mini/source.json` 的顶层键 `metadata,schema_version,tables`；
  `tables["月度宽表"]` 实测 `columns` 35 项 / `rows` 6 项；schema 依据 `contracts/source-json.schema.json`
  实测 865 行 / 23724 B / `eef2099bddfa`，其 `:474` 存在 `monthly_review` 属性 ⇒ **原样保留**进 `RawSource.metadata`，
  禁白名单裁剪，这是 §4.8 给 M1-P01 留的**唯一**扩展缝）
- `parse.py:parse_source_csv`（`csv` 模块，编码 UTF-8 或 UTF-8 BOM（`OPERATIONS.md:11` 原文），首行为列名；
  必须要求恰有一份 `table_name == METADATA_TABLE_NAME` 的 JSON 上传件，其内容按
  `contracts/source-metadata.schema.json`（实测 804 行 / 20125 B / `e0d18ea521ba`）校验后作为 `RawSource.metadata`；
  实测 `csv-mini/slices.csv` ＝ 7 行（1 表头 ＋ 6 数据行）/ 1914 B / `c766f7f83c64`，
  `csv-mini/metadata.json` ＝ 84 行 / 1632 B / `1d8bbf80f610`，两者与 `source.json` 的等价性已实测（§4.0 保证 3））
- `parse.py:PARSE_ADAPTERS` 补齐三个 `ImportFormat` 键（**恰 3 项**，实取 `len(PARSE_ADAPTERS) == len(IMPORT_FORMATS)` 断言由 S6 落）
- **禁改** 同 §11.4

### 11.6 S5（`qwen3.8-flash`，8k，`src/campaignlab/api/imports.py`，**只新建**）：6 个端点的路由样板（签名与错误映射由本文 §1/§6/§8 冻结，逐字段填充）

- `api/imports.py:router,create_import,attach_import_file,configure_import,validate_import,get_import,list_imports`
  ＋ 私有 `_read_form_within_limit,_import_response,_import_page_response,_to_issues`（`Finding → Issue` 的映射，§4.1）
- 装饰器逐 op 显式给 `operation_id` 与 `responses=declared_responses(<2xx>)`，2xx 取值逐字按 §1.1 表
  （`createImport`=201、`validateImport`=202、其余 4 个=200）
- `validateImport` 的 202 一律走既有 `accepted_response(...)`，**禁重写队列**（卡片 `:18`）
- **禁**新增/改路由以外的任何文件；**禁**改 `api/app.py`（挂载点在 §11.3，需先拿裁定）；
  **禁**写 `resp.status_code == 2xx` 的运行期断言（A260）
- ⚠ **本棒的卡片预估（8k / flash）只覆盖路由样板本身**；§11.2/§11.3 的 DTO 与应用层/仓储层**不在** S5 的档位内
  （它们含跨模块判断与 SQL 写点，命中手册 §6.3 强制 max）⇒ 已按 §11 抬头归给 **S2**，
  但这**超出**卡片给 S2 的产出面（`domain/ingest/**`、`infra/files.py`）⇒ 见 §12 U-1（本棒最大的写权缺口）。

### 11.7 S6（`qwen3.8-flash`，7k，`tests/domain/ingest/**`，**只新建**；⚠写权缺口：`tests/domain/ingest/__init__.py` 的父层已存在，无需越界）

- `tests/domain/ingest/__init__.py`（**A276 显式点名**：单行 docstring，禁零字节；`tests/domain/__init__.py` **已实测存在**，
  S5 批已建 ⇒ 本件是 `tests/domain/` 下的**新子包**标记）
- `tests/domain/ingest/conftest.py:bank_a_payload,bank_b_payload,csv_mini_payload,source_json_payload,map_a_spec,map_b_spec,tmp_data_dir,fixed_clock,ingest_limits`
  （fixture 一律从 `spec/CampaignLab-SDD-v1.0/fixtures/**` **只读**加载；**禁**把 fixture 拷进工作树；
  探针产物一律 `tmp_path`，LANE-COMMON §6）
- `test_negative_matrix.py`（N1–N18 逐条参数化，函数名逐字含 §5.1 表要求的 `-k` 字面量：
  `test_locate_*` 六个 · `test_size_limit_*` 四个 · `test_csv_equivalence_*` 三个 · `test_stale_validation_*` 三个）
- `test_single_validator.py:test_single_validator_format_only_dispatched_in_parse,test_single_validator_signatures_have_no_format,test_single_validator_layout_branch_count_is_one`（§4.0 三条结构性保证，AST 实扫）
- `test_normalize.py`（§4.3 的 14/9/12 键面、`_to_fen` 的 `Decimal` 口径、long 布局的 `contributing_rows` 9 项与键序）
- `test_digests.py`（§4.7：投影键集合**恰** 5 键、禁入字段一个都没有、同输入两次调用**逐字节**相同、
  `INGEST_SEVERITIES == tuple(get_args(Issue.model_fields["severity"].annotation))` 的跨层对撞）
- `test_states.py`（§3.2 的 I1–I7 逐条 ＋ §3.4 的**全部**非法迁移 → 409 与四个 `INGEST_STATE_ISSUE_CODES`；
  I8–I10 断言「在 `IMPORT_TRANSITIONS` 里不存在」本身，**禁** `skip`/`xfail`）
- **每条守护自带分母断言**（LANE-COMMON §6）；**每条都要做 §10.1 的 PC**，RED 的 rc 必须是 **1**（PRE-34）
- ⚠ V15 强制项：本棒新建 `conftest.py` 与 `__init__.py`，与既有 `tests/domain/activity/` 下的同名文件**同 basename**
  ⇒ 必须跑一次**全树** `mypy`（LANE-COMMON §3.6）

### 11.8 S7（`qwen3.8-flash`，5k，`tests/golden/ingest/**`，**只新建**；⚠写权缺口：`tests/golden/__init__.py`）

- **`tests/golden/__init__.py`**（**A276 显式点名 · 越字面量件**：卡片 `scope_allow` 只给了 `tests/golden/ingest/**`，
  本件在该字面量**之外**；授权依据＝**A262 同族**（`tests/domain/__init__.py` 的同型缺口，先例＝M1-03 的 N1）
  ＋ **A276**。形态＝**单行 docstring**，**禁零字节空文件**）
- **`tests/golden/ingest/__init__.py`**（**A276 显式点名**；在 `scope_allow` 字面量**之内**；同形态）
- `tests/golden/ingest/conftest.py:golden,analytics_golden,bank_a_result,bank_b_result,csv_result,source_json_result`
  （`golden` ← `spec/CampaignLab-SDD-v1.0/fixtures/analytics-golden.json`，实测 144 行 / 3277 B / `a7122ae9aae7`）
- `test_counts.py:test_counts_bank_a_is_510_slices,test_counts_bank_b_is_510_slices_and_4590_stage_items,test_counts_cross_bank_money_fen_agree_after_normalization,test_counts_csv_matches_source_json`
  （函数名逐字含 `counts`，供卡片 `:14` 的 `-k counts` 命中；期望值一律从 `analytics-golden.json` **实读**
  —— 实测 `cross_bank.slices_each == 510`，**禁**把 510/4590 写成裸字面量而不给来源注释；
  A115：禁写死符号面计数，黄金值属**数据**不属符号面，但仍须标来源路径）
- `test_traceability.py`（§4.7 的三层摘要 ＋ `source_row` / `contributing_rows` 的可追溯断言）
- ⚠ V15 强制项（同 §11.7）；⚠ **禁**为过测改期望值（卡片红线）；fixtures 与黄金值对不上时**停手上报**（派单文 §8）

### 11.9 S8（`qwen3.8-flash`，6k，`evidence/M1/M1-01/**` ＋ `evidence/M1/summaries/M1-01.md`）：AC-005 / AC-006 证据采集与回执归档（**禁改任何代码或测试**）

- `evidence/M1/M1-01/commands.md`（§10 的 V1–V16 逐条：命令原文、rc、时间戳、环境行；**V4a/V4b 分行记**，A275）
- `evidence/M1/M1-01/ac.md`（AC-005 / AC-006 逐分句给「判定 ＋ 依据 ＋ 证据指针」；
  AC-006 的「页面」一项如实记「判定归 F/M5 lane，本卡无前端写权」，**禁**自行宣称通过）
- `evidence/M1/M1-01/counts.md`（510 / 4590 / 元分归一 / CSV↔JSON 同值的实取输出 ＋ 输入文件的 sha256）
- `evidence/M1/M1-01/gates/V1.log … V16.log` ＋ `V<n>-positive-control.log`（§10.1 的 RED 原文与 sha256 双向核验）
- `evidence/M1/M1-01/http/{createImport-201,attachImportFile-200,configureImport-200,validateImport-202,getImport-200,listImports-200,problem-404,problem-409,problem-412,problem-413,problem-422,problem-428,problem-429}.json`
- `evidence/M1/summaries/M1-01.md`（卡片 `outputs` 原文要求 **≤ 30 行**）
- 证据文件同样必须过 **UTF-8 / 无 BOM / 无 `\r` / 尾换行** ＋ `ruff format --check`（A175：作用域含 `.md`）

### 11.10 写权缺口一览（＝§12 U-1/U-4/U-5/U-11/U-13 的载荷；未裁定前 S2–S8 **禁动**）

| # | 路径 | 需要的改动 | 缺口类型 | 既有裁定先例 |
|---|---|---|---|---|
| G1 | `src/campaignlab/api/common.py` | 纯追加 11 个 DTO/别名 ＋ 2 个 domain Literal 的再导出 ＋ `__all__`（0 删除行） | 不在 `scope_allow`；且卡片 `scope_deny` **未**列它 | A91（`JobPage` 由 M0-04/S4 在该文件 append-only 追加）· A82（纯追加处置）· M2-01-design §11.9 同型条目 |
| G2 | `tests/unit/test_domain_errors.py` | **只改** `:176`/`:177` 两行的钉死整数（同族钉桩元守护要求两两相等且处数 ≥ 2） | 不在 `scope_allow` | A115（禁写死符号面计数）⇒ 建议改成实取对撞而非改数字（§12 U-5） |
| G3 | `src/campaignlab/application/import_service.py` | **新建**（§11.3；事务＋用例编排，含 ID 前缀与审计常量） | 不在 `scope_allow` | M0-02/S3d 的 `application/workspace_service.py` · M2-01 的 `application/activity_service.py` |
| G4 | `src/campaignlab/application/import_jobs.py` | **新建**（`VALIDATE_IMPORT` 处理器，I5/I6/I7 的执行方） | 不在 `scope_allow` | M0-04 的 `worker/runner.py::HandlerRegistry`（本卡**只注册不改** `worker/**`） |
| G5 | `src/campaignlab/infra/db/repositories.py` | 纯追加 3 个 Record ＋ 3 个 Repository ＋ 3 个 `*_from_row` ＋ 3 个列序常量 ＋ `__all__`（0 删除行） | 不在 `scope_allow` | **A81**（SQL 写点唯一）· **A82**（对该文件的「纯追加」处置）· A231（`repositories.__all__` 追加授权） |
| G6 | `src/campaignlab/api/deps.py` | 纯追加 1 个 Protocol ＋ 1 个提供器 ＋ `__all__`，采 **`TYPE_CHECKING` 块形态** | 不在 `scope_allow` | **A233**（规避 ruff `I001` 与「只允许追加名字」的字面冲突） |
| G7 | `src/campaignlab/api/app.py` | ≤4 行（1 import ＋ 1 `include_router` ＋ 至多 2 行 state/handler 注册），0 删除行 | 不在 `scope_allow` | **A90① / A10 最小例外（≤3 行）**；实测该文件已有 `# M0-04/S4（A10 最小例外，≤3 行）` 的同型注释与 `app.include_router(jobs_router)` |
| G8 | **`tests/golden/__init__.py`** | **新建 · 单行 docstring** | **越字面量件**：在 `tests/golden/ingest/**` 字面量**之外** | **A276** ＋ **A262 同族**（`tests/domain/__init__.py`，先例＝M1-03 的 N1） |
| G9 | `tests/api/imports/**`（若编排器要求 HTTP 面用例独立成目录，V8） | 新建目录 ＋ `__init__.py` ＋ `conftest.py` | 不在 `scope_allow`（卡片只给了 `tests/domain/ingest/**` 与 `tests/golden/ingest/**`） | M2-01 的 `tests/api/activities/**`（该目录实测已存在，`__init__.py` ＝ 1 行 / 89 B） ⇒ 见 §12 U-14 |
| G10 | `tests/integration/jobs/**` 里名为 `*validate_import*` 的用例 | **本卡禁写**（卡片 `:18` 原文「该用例文件归 M0-04 lane，本任务只跑不改；失败即回报」） | 在 M0-04 的 scope 内 | 卡片 U-2 ＋ 本轮实测该 gate **NO_TEETH**（§10 V5） ⇒ §12 U-2 |

### 11.11 方案 B 的平移映射（仅当编排器拒绝 §11.10 的扩围时启用；符号名与字段序**完全不变**）

| 方案 A 落点 | 方案 B 落点 | 代价 |
|---|---|---|
| `api/common.py` 的 11 个 DTO/别名（G1） | `api/imports.py`（`Import`/`ImportPage`/`ImportFile`/`ImportConfigure`/`SourceMapping`/`LongColumns`/`UploadFields`/`AttachFileFields` 与 3 个 Literal 的再导出） | `_IdStr`/`RevisionInt` 需在 `api/imports.py` 内**重新声明**（漂移风险）；M1-02/M1-03/M1-P01 的 `scope_deny` 若含 `api/imports.py`（同族先例：本卡 `scope_deny` 就显式列了同波下游的 `api/snapshots.py` 等）⇒ 下游**读不到** DTO，只能各抄一份（违反「禁两处各存一份」） |
| `tests/unit/test_domain_errors.py` 的两行（G2） | **不需要改**（`common.__all__` 不变） | 方案 B 的**唯一**净收益 |
| `api/deps.py` 的 Protocol ＋ 提供器（G6） | 在 `api/imports.py` 内实现私有 `_import_service(request)`（读 `request.app.state`，缺失即 `RuntimeError`） | 复制既有 `_state_service` 的取值口径（约 10 行）；`deps.py` 不再是提供器的单一入口 |
| `api/app.py` 的 `include_router`（G7） | **仍必须**改 `api/app.py`（无替代落点） | 缺口无法消除，仍需 A90①/A10 最小例外裁定 |
| `application/import_service.py`（G3）＋ `application/import_jobs.py`（G4） | `domain/ingest/service.py`（含事务与 SQL） | 违反 `framework/PYTHON.md` 第 5 行「服务层应用事务，不在路由里直接写 SQL」与 `framework/DATA.md`「SQLite 与迁移」的分层口径，且破 **A81**「SQL 写点唯一」⇒ 需新立 ADR，**本文不推荐** |
| `infra/db/repositories.py` 的 3 个 Repository（G5） | 同上，SQL 落 `domain/ingest/service.py` | 同上 |
| `tests/golden/__init__.py`（G8） | **无替代**（pytest 收集期需要包标记，否则 rc=4） | 缺口无法消除，仍需 A276/A262 裁定 |
## 12. 未决问题（交编排器裁定，**实现方不得自行决定**，手册 §6.4；逐条给 U 编号 ＋ 两个候选 ＋ 倾向及理由）

- **U-1（本棒最大项）· §11.10 的 G1–G7 七件写权缺口**（`api/common.py` · `tests/unit/test_domain_errors.py` ·
  `application/import_service.py` · `application/import_jobs.py` · `infra/db/repositories.py` · `api/deps.py` · `api/app.py`）。
  问题：卡片 `M1-01.md:22` 的 `scope_allow` 只给了 `domain/ingest/**`、`api/imports.py`、`infra/files.py`、
  `tests/domain/ingest/**`、`tests/golden/ingest/**`、`orchestrator/handoff/M1-01-design.md`、`evidence/M1/**`，
  **不含**上述七件；但没有它们，6 个端点无法装配、SQL 无落点（A81）、DTO 无家（§2.5）。
  候选 A：按 §11.10 扩围，七件全部授权给 **S2**（max），并同步 `state.json.tasks["M1-01"].scope`（T lane / 编排器独占写）。
  候选 B：启用 §11.11 的方案 B（零扩围回退），DTO 落 `api/imports.py`、service 落 `domain/ingest/service.py`。
  **倾向 A**：方案 B 会破 A81（SQL 写点唯一）与 `framework/PYTHON.md` 第 5 行的分层口径，需新立 ADR；
  且 G7（`api/app.py` 的 `include_router`）与 G8（`tests/golden/__init__.py`）在方案 B 下**依然**无法消除。
  同族先例充分（A91 / A82 / A81 / A233 / A90① / A231 / A262 / A276）。
- **U-2 · 卡片 `:18` 的 gate `pytest -q tests/integration/jobs -k validate_import` 当前 NO_TEETH。**
  实测（本文写作时点）：`uv run --no-sync pytest -q tests/integration/jobs -k validate_import --collect-only` →
  `no tests collected (98 deselected) in 0.05s`、**rc=0**。即该 gate **空转即绿**，无法证明
  「202 作业语义复用 M0-04 底座」。候选 A：由 **M0-04 lane**（或编排器直接）在 `tests/integration/jobs/**` 内
  预置 `test_validate_import_accepts_and_returns_202_with_location`（该目录属 M0-04 的 scope，卡片 `:18` 原文
  「本任务只跑不改」）。候选 B：把该集成用例的写权扩给 M1-01（即卡片 U-2 的第二种处置）。
  **倾向 A**：卡片 `:18` 与卡片文末 U-2 已把「只跑不改」写成明文，改判需编排器裁定；且 M0-04 已 `status=DONE`，
  由它补一条用例的成本最低、也不破坏 `scope_deny`。**在裁定前，S8 采集该 gate 时一律如实标 `NO_TEETH`，禁标 PASS。**
- **U-3 · multipart 的两个 schema 在 DTO 面的命名。** 切片 `Upload` / `AttachFile` 的 `file` 属性实测
  `{"type":"string","format":"binary"}`，无法在纯 pydantic DTO 里表达（§2.3）。
  候选 A：本文的冻结方案 —— 建 `UploadFields` / `AttachFileFields`（不含 `file`），契约对撞用两条断言覆盖
  （文本字段逐字对撞 ＋ `properties.file.format == "binary"` 单独断言）。
  候选 B：建同名 `Upload` / `AttachFile`，`file` 声明为 `StrictBytes`，对撞测试可完全逐字。
  **倾向 A**：候选 B 等于强制把 8 MiB / 64 MiB 的上传体整体读进内存，直接违反 §1.2 的流式口径与
  AC-005「不留半成品」，也违反 `read_body_within_limit` docstring 的既有警告（「先 `await request.body()` 全量读入
  再判长度等于没有上限」）。代价是名字与切片不同名，需在对撞测试里显式记录这层映射。
- **U-4 · `SourceMapping.id` 由客户端给，而 `source_mappings.id` 是主键。** 切片实测
  `SourceMapping.required` 含 `id`；DDL 实测 `PRIMARY KEY(workspace_id,id)`；而 `architecture/DOMAIN.md`
  「配置内容同 ID 变更要求新 ID」＋ `architecture/DATA.md`「每次映射实际变更保存为新映射 ID」要求每次配置产生新行。
  候选 A：**客户端给的 `id` 就是主键**（`SOURCE_MAPPING_ID_PREFIX` 只用于客户端缺省时的兜底 —— 但契约里 `id` 是必填，
  故无兜底）；同 `id` ＋ 同 `digest` → 幂等复用既有行（不 INSERT）；同 `id` ＋ 异 `digest` → **409 `VERSION_MISMATCH`**。
  候选 B：忽略客户端的 `id`，服务端一律 `new_resource_id(SOURCE_MAPPING_ID_PREFIX)` 另发主键，客户端的 `id` 存进
  `content_json`（但 `content_json` 是 `SourceMapping` 的 canonical 投影 ⇒ 会出现「DTO 里的 id ≠ 行主键」的双身份）。
  **倾向 A**：与 `ImportConfigure` 的契约语义一致（客户端声明映射身份），也与「同 ID 变更要求新 ID」的原文对齐
  （冲突即拒，而不是静默换 ID）；且 `architecture/DATA.md`「相同银行和版本标签仅允许同摘要复用」正是 A 的判据原文。
  ⇒ §11.3 的 `SOURCE_MAPPING_ID_PREFIX` 在候选 A 下**不需要**，若裁定 A 请把它从 §11.3 删掉（走 §14 追记）。
- **U-5 · G2 的改法。** `tests/unit/test_domain_errors.py:176`/`:177` 钉死 `len(common.__all__) == 80`。
  候选 A：把两行的整数改成新的实取值（最小改动，但**继续**钉死数字，A115 的精神未落实）。
  候选 B：把两行改成**实取对撞**（例如 `assert set(common.__all__) >= <本文 §11.2 列出的名字集合>` ＋
  `assert len(common.__all__) == len(set(common.__all__))`），彻底去掉魔数。
  **倾向 B**：A115 原文即「禁写死符号面计数」，且元守护 `test_all_common_surface_pins_agree_with_runtime` 只要求
  「钉桩处数 ≥ 2 且整数一致」—— 候选 B 保留了 `len(set(...))` 那一处的钉桩形态即可满足下界，不会让分母塌陷。
  风险：候选 B 改动了他人 lane 的守护语义，需编排器确认是否要走 CR。
- **U-6 · `domain/ingest` 是否需要显式时钟。** 本文冻结为**零时钟依赖**（§4.1），因为归一与校验是纯函数，
  时刻只用于 `created_at`（application 层）。候选 A：保持零时钟（本文方案）。
  候选 B：把 `clock: Clock` 也传进 `ingest()`，为将来的「按导入时点判定字典版本」预留。
  **倾向 A**：`framework/PYTHON.md` 第 6 行的要求是「避免在领域计算内调用**系统当前时间**」，注入式时钟不是必须的；
  而 `INGEST` 面现在没有任何时点相关的判定（`cutoff` 与 `period` 的关系是纯日历算术）。候选 B 会让纯函数变成
  需要 fixture 的函数，增加 S6 的用例面而不增加覆盖。**若**编排器认为 M1-P01 的月报 append 需要时点判定，
  再走 §14 追记扩签名（卡片 `public_frozen` 允许「改动走 CR」）。
- **U-7 · `IngestLimits.max_slices` / `max_stage_items` 的取值不是契约字面量。** 本文取 `10_000` / `90_000`，
  依据 `framework/DATA.md`「分析基准先用甲乙各 510 切片，再生成 1 万聚合切片与 10 万事件的合成压力数据」。
  候选 A：采用本文取值（有 spec 文字依据，但不是硬数字）。候选 B：**不设**这两个上限，只保留
  `max_findings = 1000`（← 实测 `Import.issues.maxItems`，契约字面量）。
  **倾向 A**：`OPERATIONS.md`「运行与备份」表给了「10 万行导入 ≤ 60 秒」的工程目标，无上限会让 8 MiB 内的
  病态密集 JSON（例如 100 万行 × 1 列）打穿该目标；且 413 只管字节数、管不了行数。
  但**这两个数属本文的设计取值**，若编排器认为应由 ADR 固定，请裁定后走 §14 追记。
- **U-8 · 「哪些金额键可为负」的划分。** spec 只有一句「余额增量可为负，销量为非负」。本文据此把 12 个金额键
  分成 7 个变动类（可负）＋ 5 个销量类（非负，N16）。候选 A：采用本文划分。
  候选 B：**不**做非负校验，只保留「必须是整数分」（把 N16 降级为 `WARNING`）。
  **倾向 A**：AC-005 的负例注入面已经包含「负人数」，同族的「负销量」是同一类脏数据，放过会让
  `analytics-golden.json` 的 `current.wealthSale == "22809600"` 一类黄金值失去意义。
  风险：若某行内真实数据存在负销量（退货冲销），A 会误判 ⇒ 需要业务确认；这是本文**无法**从 spec/契约确定的事，故上报。
- **U-9 · AC-006「CSV/JSON 同值」是否包含 `validation_digest` 同值。** 本文实测并冻结：两者的**切片值**与
  **`metadata_digest`** 相同，但 `validation_digest` 的 `files` 段含**原字节 SHA**，CSV 通道（2 个上传件）与
  SOURCE_JSON 通道（1 个上传件）必然不同 ⇒ `validation_digest` **不相同**。
  候选 A：接受本文口径（「同值」指归一后的业务值与元数据投影，不含文件摘要）。
  候选 B：把 `files` 段从 `validation_digest` 的投影里去掉，只留 `mapping_digest` ＋ `metadata_digest` ＋ `parser_version`。
  **倾向 A**：`architecture/DATA.md` 原文「校验摘要覆盖**文件原始 SHA**、映射内容、元数据及解析器版本」是硬要求，
  候选 B 直接违反 spec；且「新发布时校验摘要必须仍匹配」的安全性正依赖文件 SHA 入摘要（换文件必须重校验）。
- **U-10 · 「未知切片」与「孤立切片」是否同指一事。** AC-005 说 B 注入「重复码及孤立切片」，
  `architecture/DATA.md`「映射和标准表」段说「未知切片、重复码、缺必填阶段、映射引用不存在列均报错」。
  候选 A：同指一事，只登记 `ORPHAN_SLICE` 一个码（本文方案）。
  候选 B：分成两个码 —— `ORPHAN_SLICE`（长表有、实体表无）与 `UNKNOWN_SLICE`（实体表的切片 `id` 无法被字典解析）。
  **倾向 A**：本文找不到 spec 里「实体表切片 id 无法被字典解析」的独立语义（`id` 是切片号，
  实测形如 `2025-09:B01:remote:1`，其可解析性已由 N11 `UNKNOWN_DICTIONARY_REF` 覆盖 `branch`/`channel` 分量）；
  凭空多一个码会违反 D-019 的精神。**若**编排器认定两者不同，请给「未知切片」的判定条件原文，S2 再补。
- **U-11 · 导入上传件的暂存目录名不副实。** `ArtifactWriter.begin(workspace_id, job_id, attempt)` 的暂存根实测为
  `<data_dir>/tmp/jobs`（`stage_root` docstring 原文），而 `infra/artifacts.py` 在卡片 `scope_deny` 内。
  候选 A：本文方案 —— 传 `job_id=<import_id>`，接受暂存目录物理上落在 `tmp/jobs/**`（换来零改 `artifacts.py`
  ＋ 自动受 `sweep_unreferenced` 保护）。候选 B：`infra/files.py` 自建 `<data_dir>/tmp/imports/**` 暂存与清理。
  **倾向 A**：候选 B 需要在 `infra/files.py` 里复制一份「原子重命名 ＋ 同文件系统校验 ＋ 超期清理」逻辑
  （实测 `artifacts.py` 的 `verify_same_filesystem` / `sweep_unreferenced` / `_prune_empty_dirs` 共约 200 行），
  属「第二份实现」，且既有 `sweep_unreferenced` **不扫** `tmp/imports/**`（实测扫描面「只有 `results/**` 与
  `tmp/jobs/**`」）⇒ 会留下永远没人回收的垃圾目录。
- **U-12 · `SourceRow.source_file_id` 指哪一个 ID。** `architecture/DATA.md` 原文只说
  「source_row 由导入器生成，含 source_file_id、table_name、row_number」。
  候选 A：`import_files.id`（本文方案；`imf` 前缀，导入面的一等公民，`table_name` 与它同表 ⇒ 三元组自洽）。
  候选 B：`artifacts.id`（`art` 前缀；更贴近「文件」字面，但同一份内容被两个导入复用时 `artifact_id` 会相同
  ⇒ `source_file_id` 失去「哪一次导入的哪一个上传件」的区分力）。
  **倾向 A**：可追溯性的目的是「从页面上的一个数追回到**这次导入**的这一行」，`artifacts` 是内容寻址的、跨导入共享的
  （实测 `CommittedArtifact.reused_file` / `reused_row` 就是为此存在），用它做 `source_file_id` 会在复用场景下歧义。
- **U-13 · `VALIDATE_IMPORT` 作业处理器的注册点。** `worker/runner.py::HandlerRegistry` 在 `scope_deny` 内，
  M0-04 的设计原文是「**src 内不放业务 handler**，测试在 conftest 注册桩」。
  候选 A：本文方案 —— 处理器实现落 `application/import_jobs.py`，注册落 `api/app.py` 的装配面（G7 的同一处最小例外）。
  候选 B：注册落 `worker/deps.py` 的 `registry` 构造处（需改 `worker/**` ＝ `scope_deny`）。
  **倾向 A**：候选 B 直接违反卡片 `scope_deny`；候选 A 与 M0-04 的「src 内不放业务 handler」并不冲突
  （业务 handler 住在 `application/`，装配面只做注册），且实测 `api/app.py` 已有 `include_router` 的最小例外先例。
  **附带问题**：`WorkerRunner` 由谁启动（CLI `serve` 面）不在本卡 scope ⇒ 若注册只在 `create_app()` 内生效，
  则**独立 worker 进程**看不到该 handler。请编排器明确 `validateImport` 的作业是「同进程内跑」还是「独立 worker 跑」，
  这决定 I5/I6/I7 的集成用例落点（也影响 U-2 的补牙方案）。
- **U-14 · HTTP 面用例（§10 V8）的落点。** 卡片 `scope_allow` 只给了 `tests/domain/ingest/**` 与
  `tests/golden/ingest/**`，**没有** `tests/api/imports/**`。但 §1/§6/§8 的路由面（6 个 op 的 `operation_id`、
  `declared_responses` vs 切片、428/412 的可达性、逐 op 可达码矩阵）**必须**有 HTTP 层用例才算有牙。
  候选 A：扩围 `tests/api/imports/**`（同族先例：M2-01 的 `tests/api/activities/**`，实测该目录已存在且
  `__init__.py` ＝ 1 行 / 89 B）。候选 B：把路由面用例塞进 `tests/domain/ingest/**`（用 `TestClient`）。
  **倾向 A**：候选 B 会让「领域层测试目录」里出现 HTTP 客户端与 DB fixture，破坏 `tests/` 的分层约定
  （实测 `tests/` 下 `api/ domain/ integration/ unit/` 四分），也会让卡片 `:15`/`:16`/`:17` 的
  `-k locate` / `-k size_limit` / `-k csv_equivalence` / `-k stale_validation` 意外命中 HTTP 用例、污染分母。
- **U-15 · 派单文 §3.3 的 fixtures 路径是简写。** 派单文与卡片 `inputs:` 都写作 `fixtures/banks/bank-a.json` /
  `fixtures/analytics-golden.json`，但仓库**没有**顶层 `fixtures/` 目录；实测真实路径为
  `spec/CampaignLab-SDD-v1.0/fixtures/**`（`find` 实测：`./spec/CampaignLab-SDD-v1.0/fixtures/analytics-golden.json`、
  `./spec/CampaignLab-SDD-v1.0/fixtures/banks/bank-a.json`、`./spec/CampaignLab-SDD-v1.0/fixtures/banks/csv-mini/slices.csv`）。
  候选 A：认定是简写，本文一律用**实测全路径**（已如此）。候选 B：认定为需要新建顶层 `fixtures/` 软链或副本。
  **倾向 A**：卡片 `inputs:` 自己就混用了两种写法（`bank-a.json` 给了 `spec/CampaignLab-SDD-v1.0/fixtures/banks/` 全前缀，`csv-mini/*` 与 `analytics-golden.json` 给了简写），
  且 `spec/**` 是只读硬禁面 ⇒ 候选 B 需要动 `spec/**` 或在仓根新建目录，两者都不该由本卡发起。
  **本文已按 A 处理，仅报备口径差异，不阻塞。**

## 13. 本文件自检（命令 → rc；均在 WSL 仓库根 `/home/szf/dev/CampaignLab` 执行；rc 与实测值以**本轮实取**为准，见回执，**禁写死**）

| # | 命令 | 期望 |
|---|---|---|
| C1 | `uv run --no-sync ruff format --check orchestrator/handoff/M1-01-design.md` | rc=0（A175 / LANE-COMMON §3.1：`ruff format` 的作用域含 `.md`，围栏与表格会被重排 ⇒ 本件落盘后必须实跑） |
| C2 | `uv run --no-sync python -c "import pathlib;b=pathlib.Path('orchestrator/handoff/M1-01-design.md').read_bytes();t=b.decode('utf-8');print('strict_utf8=OK','bom=',b.startswith(b'\xef\xbb\xbf'),'cr=',b'\r' in b,'nul=',b'\x00' in b,'c0c1=',[hex(ord(c)) for c in t if (ord(c)<0x20 and c not in '\n\t') or 0x7f<=ord(c)<=0x9f],'tail_nl=',b.endswith(b'\n'))"` | rc=0 且输出 `bom= False cr= False nul= False c0c1= [] tail_nl= True`（编码四判据，PRE-39） |
| C3 | 自查①：断言本文引用的每个 `operations.<opId>` 都实测存在于切片（正则抽取 ＋ 集合差集，**禁目视**） | rc=0 且差集为空（本文引用面：`createImport` `attachImportFile` `configureImport` `validateImport` `getImport` `listImports`） |
| C4 | 自查②：断言本文引用的每个 `Problem.code` 都在 `domain/errors.py::PROBLEM_CODES`（实测 20 项）内，且本文引用的全部 `Problem.code` 集合 ⊆ 该注册表 | rc=0 且越界集为空（**零发明 code**，D-019） |
| C5 | 自查③：断言本文引用的每个**仓库路径**实测存在；§11 中标注「只新建／待创建」的路径单列一张清单（用 `新建`/`待创建` 标记识别），不参与存在性断言 | rc=0 且悬空引用集为空 |
| C6 | 自查④：断言本文出现的每个下划线全大写 token 要么在 `PROBLEM_CODES`（20 码）内、要么在切片枚举值 / DDL `CHECK` 值 / 本文 §3.4＋§5.1 登记的 `Issue.code` 面内 | rc=0 且越界集为空（体例＝`M2-01-design.md` §13 C8） |
| C7 | 自查⑤：断言本文引用的每个 `operations.<opId>.schemas.<Name>` 路径都实测存在（A171 口径的**可复跑**版），且 §2 各表的 `required` 项数与切片**实取**一致 | rc=0 且差集为空 |
| C8 | 自查⑥：断言本文引用的每个**仓内既有符号**都实存（`hasattr` / `inspect.signature` / `typing.get_args` / `model_fields` 逐个对撞），并把「待创建」符号单列（§11 逐棒归属） | rc=0 且缺失集为空（PRE-24；D-052 的教训：禁写设想名） |
| C9 | 自查⑦：断言本文 §10 的 `-k` 字面量集合 ⊇ 卡片 `M1-01.md:14–18` 五条 gate 的全部 `-k` 字面量，且 **A275** 的 `csv_equivalence` 与 `stale_validation` 在 §10 里是**两条独立的 V 行**（V4a / V4b），全文**不存在**任何一行同时出现两个 `-k` | rc=0（正则扫描本文自身） |
| C10 | 自查⑧：断言本文 §11 的棒号集合恰为 `{S2,…,S8}`（7 棒）且与卡片 `:32–49` 档位表逐棒对应（档位 / token / 产出路径三项都对得上） | rc=0（供派单文 §7 的 V8 `grep -n '^### 11\.'` 交叉核验） |

> **append-only 纪律（PRE-38 的适用时点声明）**：本文一切读数与判据的适用时点 ＝
> **M1-01/S1 交付时点 · HEAD `be2b50b` · 分支 `m0-framework` · 同任务无在飞棒**（并行棒 `M2-01/S6` 写集
> `tests/api/activities/**` 与本棒不相交）。跨批复用本文读数一律无效，须重新实取。
> 本文 §0–§13 为 S1 冻结件；后续编排器裁定一律以 **§14 追记**形式增量写入
> （体例＝`M2-01-design.md` §14 与 `M0-04-design.md` §11：「纯增量，历史行一字未改」，`numstat` 的 deleted 必须为 0），
> **禁**回头改写 §0–§13 的任何一行；`public_frozen` 面（`domain/ingest/api.py` 的 `parse` / `ingest` 两个入口签名、
> §4.4 的 `location` 语法、§4.7 的投影键集合）改动一律走 CR。

## 14. 编排器裁定追记（append-only；§0–§13 一字未改）

> 体例＝`M2-01-design.md` §14 与 `M0-04-design.md` §11（「纯增量，历史行一字未改」）。
> 本节**预留空段**：由编排器在后续批次依 A214 窄豁免**只在文末追加**（`git diff --numstat` 的 `deleted` 列必须为 0），
> 追加前的全部行逐字节未变（追加前后请做前 N 行拼接 sha256[:12] 的**双向核验**并把两个摘要落进证据）。
> 待裁项清单＝ §12 的 **U-1 … U-15**（其中 U-1 / U-2 / U-4 / U-13 / U-14 会直接影响 S2–S8 的写权面与棒内工作量，
> 建议在 **S2 派单前**给出裁定；U-15 仅报备口径差异，不阻塞）。

（本段暂无追记。）
