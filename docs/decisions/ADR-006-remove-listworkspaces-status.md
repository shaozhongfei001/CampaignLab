# ADR-006 · 从 `listWorkspaces` 移除 `status` 查询参数（CR-002 选项 B）

- 状态：ACCEPTED（项目负责人已裁定选项 B，并授权本次长程无人值守「裁定用默认值」）
- 裁定时间：2026-11-13T02:10:28+08:00
- 裁定人：项目负责人（选项 B）；执行与影响面补充：编排器
- 触发来源：**CR-002**（`orchestrator/change-requests/CR-002.md`），由 M0-02/S1 设计档 §7 的 Q4 上报
- 关联：ADR-005（Problem.type 与运行参数默认值）、D-013（影响面完整性与重切要求）

## 1. 背景：契约自相矛盾

活契约 `contracts/openapi.json` 的 `listWorkspaces`（`GET /workspaces`）声明了查询参数
`status`（`type=string, minLength=1, maxLength=60, required=false`），但：

- `Workspace` schema **没有** `status` 属性；
- 参考 DDL `contracts/sqlite-v1.sql` 的 `workspaces` 表实测列为
  `id / name / source_class / authorization_note / revision / created_at`，**也没有** `status`。

即：契约允许按一个**数据模型里不存在**的字段过滤。实现方若照契约写，只能自行发明取值语义，
这违反本项目两条铁律——「活契约 `contracts/` 是实现唯一依据」与「不得发明契约未规定的语义／不得伪造数据」。

## 2. 事实核查（Q 判定档独立复核为真，编排器定点提取复验）

1. 该 `status` 参数**不是** v1.0.1 月报增量引入：只读基线 v1.0.0
   （`spec/CampaignLab-SDD-v1.0/contracts/openapi.json`，430624 B，sha16=`3a5c6e3b8a0539cd`）**即已含该参数**，
   且其 schema 与活契约逐字相同。
2. `contracts/CHANGES.json` 原 12 条登记项**完全不涉及** `listWorkspaces`
   （程序化实测：12 条中提及 `listWorkspaces` 的条数 = 0）。
3. `scripts/check_contracts.py` 要求「基线 ↔ 活契约的每一处结构差异都有登记项，且登记项的 CR/ADR 文件真实存在」，
   同时要求「登记项反过来必须真实产生差异」（防止僵尸条目）。因此**移除该参数必须同时新建本 ADR 并登记**，
   否则门禁判红。

## 3. 决策

**选项 B：从 `listWorkspaces` 移除 `status` 查询参数。**

- 备选方案 A（给 `Workspace` 补 `status` 字段）被否决：那需要同时发明状态取值枚举、状态机与 `workspaces` 表列，
  等于凭空造出一套契约未规定的领域语义，且 `spec/**` 为只读基线，无据可依。
- `info.version` **保持 `1.0.1` 不 bump**：本次是对既有契约内部不一致的**修正**（移除一个无法实现的参数），
  不是月报增量交付；bump 会连带要求修改 `orchestrator/tasks/M0-03.md`、`docs/delivery/MONTHLY-DELTA-PLAN.md`、
  两份切片的 `spec_version`、`state.json.counts.live_openapi_info_version` 以及所有以 1.0.1 为基准的门禁文本，
  属独立治理动作（清单见 `CR-002.md` 6.2）。

## 4. 影响面（含 Q 判定档 G 项补充，依 D-013）

1. **契约**：`GET /workspaces` 的 `parameters` 由 4 项（cursor/limit/q/status）减为 **3 项**（cursor/limit/q）。
2. **登记**：`contracts/CHANGES.json` 的 `entries` 由 **12 → 13** 条，新增项 `cr=CR-002`、`adr=ADR-006`。
3. **后端**：M0-02/S1 设计档 Q4 的临时处置（`WORKSPACE_STATUS_WHITELIST=frozenset()`，任何非空 `status` →
   422 `INVALID_SCOPE`，`issues[0].location="/query/status"`）**取消**——参数已不存在，该分支无对象。
   S3/S4 不得实现、不得为其写契约测试。
4. **前端**：UI-01 **不提供**工作区状态筛选控件（M0-03 设计档 Q7 的临时处置由「临时」转「终态」）。
5. **切片**：必须重切 `orchestrator/handoff/M0-02.slice.json` 与 `M0-03.slice.json`，
   其 `source.openapi.sha16`/`bytes` 随之变化；重切参数已由编排器**干跑验证可字节复现**：
   M0-02 = `--ops exchangeSession,getSession,getHealth,listWorkspaces,createWorkspace --ac AC-001,AC-034,AC-035`；
   M0-03 = `--ops <同上> --ui UI-01`。
6. **基准文本**：所有硬编码 `01bd28f0772f506e` / `443552` 的门禁文本必须同步，
   含两张任务卡的 PRE-3 段与 `state.json.counts.live_openapi_sha16`（编排器补的步骤 6b，D-013/BLK-Q3）。
7. **未在本次范围内的同类问题（Q 判定档 G 项实测，留待后续 CR）**：活契约中**另有 6 个资源同样缺状态字段**、
   **9 处使用 `state` 命名**。本次只修正 `listWorkspaces.status` 一处；「状态语义」的全局一致性
   属独立议题，不在 CR-002 范围内，**不得据本 ADR 推断其余资源已处理**。

## 5. 可复现验证

```bash
python3 scripts/check_contracts.py check            # rc=0
uv run --no-sync python scripts/check_contracts.py check --validate   # rc=0
python3 scripts/check_contracts.py diff | grep -c . # 登记项与实测差异同为 13
```
