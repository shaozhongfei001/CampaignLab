# ADR-005 · Problem.type 标识方案与 M0 运行参数默认值

- 状态：ACCEPTED（项目负责人已授权本次长程无人值守「裁定用默认值」）
- 裁定时间：2026-11-12T23:44:54+08:00
- 裁定人：编排器（超级技术经理／架构师角色），可被项目负责人或 Q 判定档推翻
- 触发来源：M0-02/S1 设计文档 §7 的 Q5、Q6（`orchestrator/handoff/M0-02-design.md`）
- 冻结影响：本 ADR 定义的 `Problem.type` 方案与 code 注册表属**公共件**，M0-03b 之后冻结；
  冻结后如需变更必须走 CR（手册第 8 节），不得由单个 lane 私自改。

## 1. 背景

活契约对 `Problem`（RFC 9457 错误体）只约束了 `type` 长度 1–250、`title` 长度 1–200，
**未规定** `type` 的标识方案与 `title` 文案；同时三处运行参数（会话 TTL、JSON 正文上限、
worker 心跳窗口）在契约中缺失，而 `OPERATIONS.md` 只给了文件 64 MiB / 8 MiB 与一次性令牌 60s。
M0-02 与 M0-03 共同确立公共件，若不先定稿，前端错误分支与后续全部 lane 会各自发明，冻结面被污染。

## 2. 裁定

### 2.1 `Problem.type`：URN 方案

```
type = "urn:campaignlab:problem:" + code.lower()
```

- 例：`INVALID_SCOPE` -> `urn:campaignlab:problem:invalid_scope`；
  `SESSION_EXPIRED` -> `urn:campaignlab:problem:session_expired`。
- 理由：① URN 稳定、不依赖域名与部署环境（`https://` 形式会暗示存在一个可访问的错误文档站点，
  而本项目为内网单机交付，无此站点，属**虚假可解析性**）；② RFC 9457 允许 `type` 为任意 URI，
  URN 合规；③ 全小写、可机器比对，前端只需按 `code` 分支，不必解析 URL。
- `code` 注册表（公共件，冻结面）：由 `src/campaignlab/domain/errors.py` 单一来源定义，
  任何新增 code 必须先进注册表再使用；注册表变更在 M0-03b 冻结后走 CR。

> **编排器增补（2026-11-13T04:05:00+08:00 · 依 D-019 · 只加注不改写）**：`code` 的**取值集合**并非由本 ADR 或
> `errors.py` 发明，其唯一权威枚举是 `spec/CampaignLab-SDD-v1.0/architecture/API.md` 的「错误分类」表（第 20–29 行），
> 编排器逐行提取实测 **20 个**：BAD_REQUEST、BAD_CURSOR、SESSION_EXPIRED、ORIGIN_DENIED、
> ACCESS_DENIED、RESOURCE_NOT_FOUND、IDEMPOTENCY_CONFLICT、STATE_CONFLICT、VERSION_MISMATCH、
> STALE_CANDIDATE、SNAPSHOT_CONFLICT、ACTION_REVIEW_REQUIRED、REVISION_CONFLICT、
> PRECONDITION_REQUIRED、INPUT_TOO_LARGE、VALIDATION_ERROR、INVALID_SCOPE、EVIDENCE_REQUIRED、
> **JOB_CAPACITY（429）**、INTERNAL_ERROR。
> `domain/errors.py` 是该表的**代码化副本**：不得新增表外 code，不得改名；确需新增时
> **先改本 ADR（走 CR，手册第 7 节）再改注册表**。判定「契约缺项」前必须穷尽
> `spec/**/architecture/*.md`（手册第 0 节优先级第 2 项的「包内领域契约」不只指
> `contracts/openapi.json`）——429 `JOB_CAPACITY` 曾被误判为缺项，即因未查该表。

### 2.2 `Problem.title`：固定中文短句表

- `title` 取自与 `code` 一一对应的固定中文短句表（同文件维护），**不得**在调用点现编文案，
  以保证同一错误在所有 lane 的措辞一致（可测、可截图比对）。
- `detail` 才允许携带上下文（含 `issues[]` 定位），`title` 保持稳定。

### 2.3 运行参数默认值（全部经 `AppConfig` 可注入）

| 参数 | 默认值 | 依据与约束 |
|---|---|---|
| `session_ttl_seconds` | 3600 | 契约未规定；取 1 小时。与 OPERATIONS.md 的**一次性令牌 60s** 是两个不同对象：令牌仅首次换取可用（AC-001），会话是换取后的存活期，不得混用 |
| `MAX_JSON_BODY_BYTES` | 1048576（1 MiB） | 契约未规定；超限返回 413。**仅适用于 JSON 正文**；文件上传沿用 OPERATIONS.md 的 8 MiB / 64 MiB 口径，两者不得混用 |
| `WORKER_HEARTBEAT_TTL_SECONDS` | 15 | 契约未规定；超过该窗口无心跳则 `Health.worker` 报非健康，供 AC-001「worker 状态可见」取证 |

- 三个值必须可注入：测试用小值（如 TTL=1s、正文上限=64B）以在秒级内触发过期与 413，
  禁止在测试里 sleep 到真实 TTL。
- 领域计算一律用**显式时钟**（不得读系统当前时间），故 TTL 判定必须走注入的 clock。

### 2.4 数据库文件路径约定与「完整可逆」口径（%s 增补 · 依 M0-02/S2 的 Q2、Q4、Q5）

**背景**：`OPERATIONS.md:17` 只规定数据目录由 `CAMPAIGNLAB_DATA_DIR` 指定并含
`state/raw/snapshots/results/exports/tmp/logs` 七个子目录，**未规定 SQLite 库文件的确切相对路径**。
S2（Alembic 首迁）已实现一套约定；若 S3（服务入口 `infra/db/engine.py`）另取一套，
`alembic upgrade` 与运行期会作用于**两个不同的库文件**，`Health.schema_revision` 判定随之失真。
故在此定为项目级运行参数默认值（项目负责人已授权本次长程无人值守「裁定用默认值」）。

**裁定 1 · 路径约定**：库文件固定在 `<data_dir>/state/campaignlab.db`；
`<data_dir>` 默认 `~/.local/share/campaignlab`。解析优先级（高 → 低）：

1. alembic `-x db_path=<path>`（仅迁移期显式覆盖）
2. `alembic.ini` 的 `sqlalchemy.url`（`set_main_option` 注入）
3. 环境变量 `CAMPAIGNLAB_DATABASE_URL`
4. 环境变量 `CAMPAIGNLAB_DATA_DIR` + `/state/campaignlab.db`
5. 默认 `~/.local/share/campaignlab/state/campaignlab.db`

**裁定 2 · 单一来源（硬约束）**：上述解析逻辑必须**只存在一份**，落在
`src/campaignlab/infra/db/paths.py`；`migrations/env.py` 与 S3 的
`infra/db/engine.py::make_engine` 都必须 **import 该模块**，禁止各自复制一份优先级链。
S3 必须附一条测试，断言「alembic 侧解析结果 == 运行期解析结果」（同一组环境变量下逐字相等），
否则本裁定无法被机器守护。

**裁定 3 · 「完整可逆」口径（回答 Q4）**：`alembic downgrade base` 之后
**业务表 0 张 + 仅剩空的 `alembic_version`** 即为完整可逆。`alembic_version` 是 alembic 的
簿记表，**不计入 28 表分母**，也**不算** `Health` 或备份校验里的「额外表」。
`Health.schema_revision` 的取值来源就是 `alembic_version` 表的当前行。

**裁定 4 · gate 归属（回答 Q5）**：`uv run python -m campaignlab doctor` 依赖
`src/campaignlab/__main__.py`，属 **S3** 交付物；在 S2 时点必然 rc=1，
**不得在 S2 记红**，该 gate 的判定归 S3。

## 3. 被否决的选项

1. `type` 用 `https://campaignlab.example/errors/<code>`：否决。制造不存在的可解析 URL，
   且域名随部署变化会破坏冻结面稳定性。
2. 各 lane 自定义 `title` 文案：否决。破坏跨 lane 一致性与截图比对可重复性。
3. 把 JSON 正文上限直接设为 64 MiB（对齐文件上限）：否决。会让 413 分支在 JSON 路径上几乎不可测，
   且与 OPERATIONS.md 的对象划分不符。

## 4. 后果与回归

- S3 必须从 `domain/errors.py` 取 code 与 title，不得就地拼字符串。
- S4 的 413 / 会话过期用例必须通过注入小值触发，用例内不得出现真实 TTL 的等待。
- Q 判定档复核点：① `type` 是否全部符合 URN 前缀；② `title` 是否全部来自注册表；
  ③ 三个默认值是否与 OPERATIONS.md 的 60s / 8 MiB / 64 MiB **不冲突且不混用**。
- 与 ADR-002 的实现细则并行生效；如与 ADR-003（前端设计基线）的错误呈现冲突，以本 ADR 的
  code/title 为准，视觉呈现以 ADR-003 为准。
