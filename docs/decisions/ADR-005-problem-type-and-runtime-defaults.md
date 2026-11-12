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
