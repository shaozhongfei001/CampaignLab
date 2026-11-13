# R13 · Lane Z · M2-01/S1 派单文（qwen3.8-max / high · slack=4 · loop_cap=3）

> **第一步必做**：完整读 `orchestrator/handoff/LANE-COMMON.md`（公共纪律：写入通道铁律、
> R12-1 except 元组损坏、6 条仓库反直觉事实、在飞污染与路径限定自验、守护必须有牙、
> 回执格式、L 循环上限）。本文只写**本 lane 特有**内容（R12-5）。

## 0. 基线与本轮范围

- branch `m0-framework`，派单时 HEAD = 见派单消息。HEAD 树基线：
  `ruff format --check` 报 **234**、`mypy` **80 source files**、`pytest` **490 passed**。
- 对账口径 = **HEAD 树 + 你 write_set 的增量**。同轮有 lane X（任务卡面）与 lane Y
  （`worker/integrity.py` + `worker/deps.py`）在飞。
- **本轮只交付 M2-01 的 S1（设计），不写任何实现代码。** 依据手册 §6.4「max 设计 + flash 量产」
  配对模式与任务卡子任务档位表：S1 是 max/high/45k，产出 `M2-01-design.md`；
  S2（max）与 S3–S7（flash）在你交付**之后**由编排器另派。
  你**禁**顺手实现 S2–S7 的任何代码 —— 那会与后续 lane 双主写，且超你的 write_set。

## 1. 任务：M2-01/S1 —— 活动 / 绑定 / 规则版本的设计冻结件

**权威输入（按此顺序读；禁读 scope 外目录找线索）**
1. `orchestrator/tasks/M2-01.md` —— 你的任务卡。**第 42 行是 S1 那一行**，逐字照它的产出定义做；
   第 62 行起是「未决问题（交编排器裁定，实现方不得自行决定）」，**先读它**，
   里面已列明的问题**禁自行裁定**，照卡内指示处理或报 U 项。
2. `orchestrator/handoff/M2-01.slice.json`（84 KB，**已核对为新鲜**：其 `source.openapi.sha16`
   = `592571099d638251`、`bytes` = 443309，与活契约 `contracts/openapi.json` 的实测值逐字相同，
   即它是在 CR-002 合入**之后**切的）。用 python/jq 按 `operations.<opId>` 抽取，**禁整读**。
   覆盖的 op：`listActivities`/`createActivity`/`getActivity`/`updateActivity`、
   `listRules`/`createRule`/`getRule`/`updateRule`/`confirmRule`/`checkRule`/`compareRules`。
   schema 真值在 `operations.<opId>.schemas.*`（A171：切片**无**顶层 `components`）。
3. `spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md` 的 **AC-002 / AC-003 / AC-004** 原文
   （台账 `acceptance.primary_owner` 判定这三条的 primary owner 都是 **M2-01**）。
4. `spec/CampaignLab-SDD-v1.0/architecture/` 下与活动/规则/条款相关的小节（按小节读，禁整读）。
5. 既有实现对齐面（**只读**，你的设计必须与它们一致，禁另立口径）：
   - `src/campaignlab/api/common.py` —— `Problem`/`Issue`/`ObjectRef`、`encode_cursor`/`decode_cursor`、
     分页壳（`WorkspacePage`）。**`__all__` 实测 51 项，被 `test_domain_errors.py:165-166` 钉死**，
     你的设计**禁**要求在 S1 阶段改它（`JobPage` 归 M0-04/S4，A91/A84；活动侧若需新分页壳，
     在 S1 里写成「S3/S4 阶段按 A91 同构追加」的 TODO，禁现在动）。
   - `src/campaignlab/domain/errors.py` —— `PROBLEM_CODES` **实测恰 20 码**、`DomainError` 子类
     **实测 14 个**（FU-29 刚把 `ArtifactCommitFailed` 下沉进来）。你的状态机/门禁错误
     **只能复用这 20 码**；确需新码 → **报 U 项走 ADR-005 变更协议**（§7），**禁自行发明**。
   - `src/campaignlab/api/workspaces.py` 与 `src/campaignlab/domain/`（既有体例：路由只做
     「解析 → 调 service → 组装响应」，**禁写 SQL**，PYTHON.md:5；装饰器必须显式给
     `operation_id`，函数名与 operationId 逐字对应）。
   - `docs/decisions/ADR-005-*.md`（Problem code 注册表冻结）、
     `docs/decisions/ADR-006-remove-listworkspaces-status.md`。

**S1 必须冻结的内容（任务卡第 42 行逐项展开）**
- 活动 / 绑定 / 规则版本的**状态机**：状态集、迁移集（`TransitionId` 形态对齐
  `worker/states.py` 的既有体例）、终态、非法迁移的错误映射。
- **条款确认门禁**：确认前置条件、错误阻止 vs 警告需备注的分界、确认后的不可变性。
- **检查项框架**（`checkRule`）：检查项的注册形态、判定结果结构、与 AC-004 的对应。
- **ETag 与 409 / 412 边界**：`If-Match` 缺失 → 428 `PRECONDITION_REQUIRED`、不匹配 → 412
  `REVISION_CONFLICT`、同银行外部活动号重复 → 409（具体 code **以 20 码注册表实取为准**，
  禁写死推断值）、以及 409 的 `diff` 字段断言口径。
- **文件级 TODO 清单**：给 S2–S7 的逐文件交付边界（哪个文件写哪些符号、谁依赖谁），
  使后续 flash 档 lane 能「逐字段样板填充」而不需再做跨模块判断（§6.4 的配对前提）。

**硬约束（违反即判红）**
- **禁发明 `status` 查询参数**：ADR-006 §4.7 明写「另有 6 个资源同缺状态字段、9 处用 `state`
  命名，属**独立议题**，不得据本 ADR 推断其余已处理」。CR-002 已按**选项 B** 从 `listWorkspaces`
  **移除** `status`；切片实测 `listActivities` 的查询参数只有 `cursor`/`limit`（+ path 的
  `workspace_id`），**没有 `status`**。你的设计必须与切片逐字一致，禁补一个契约里没有的参数。
  若你认为业务上确需按状态过滤 → **报 U 项走 §7 契约变更协议**，禁在 S1 里私自设计。
- **禁改活契约与基线**：`contracts/**` 与 `spec/**` 只读（§1 不变量）。
- 设计文档必须**可复跑地**指向真值来源：凡写「字段 X 的类型/取值范围」，必须注明取自
  `M2-01.slice.json` 的哪个 `operations.<opId>.schemas.<name>` 路径，禁写「按惯例应该是」。
- 禁写死符号面计数（`__all__` 项数、方法数）与工具裁决结果（import 序）——
  一律写「以 inspect / `ruff check --select I --diff` 实取为准」（R8-1/A115、R12-4）。

## 2. 写权与硬禁

**只许写**：
```
orchestrator/handoff/M2-01-design.md      # 你唯一的交付物（任务卡 scope 显式包含它）
```
**硬禁**：`src/**`、`tests/**`、`web/**`、`scripts/**`、`migrations/**`、`contracts/**`、
`spec/**`、`docs/**`、`prototype/**`、`orchestrator/state.json`、`orchestrator/tasks/**`、
`orchestrator/defects/**`、`orchestrator/handoff/` 下**除 `M2-01-design.md` 以外的一切**
（尤其禁碰 `LANE-COMMON.md`、其他 lane 的派单文、`*.slice.json`）。
**禁自行 `git add` / `git commit`**（LANE-COMMON §5）。

## 3. 自验（你只产一个 .md，故门禁面很窄）

```bash
cd /home/szf/dev/CampaignLab && export PATH="$HOME/.local/bin:$PATH"
uv run --no-sync ruff format --check orchestrator/handoff/M2-01-design.md
uv run --no-sync ruff format orchestrator/handoff/M2-01-design.md   # 若上一步红，用这一步整形后复验
```
- **`ruff format` 的作用域含 `.md`**（LANE-COMMON §3.1）：文档里的 ``` 围栏会被重排，
  所以**必须**过 `ruff format --check`。
- 文件必须 **UTF-8 / 无 BOM / 无 `\r` / 以 `\n` 结尾**。
- **禁**跑全表门禁当自己的判据（在飞污染，LANE-COMMON §4）。
- 自查项（写进回执）：① 设计里引用的每个 `operations.<opId>` 都**实测存在**于切片中
  （用 python 断言，禁目视）；② 引用的每个 Problem code 都**实测在** `PROBLEM_CODES` 的 20 码内；
  ③ 文档内引用的每个**仓库路径**都实测存在（编排器的悬空引用扫描会逐条复核，
  指向不存在的文件 = 整条 lane 判红）；④ 未出现 `status` 查询参数的设计。

## 4. 回执

按 LANE-COMMON §7 的 8 段格式，≤90 行。特别要求：
- 第 2 段给出 `M2-01-design.md` 的**实测**行数 / 字节数 / 章节清单（`grep -n '^#'` 原文）。
- 第 3 段给出上面 4 条自查项的**程序化断言**结果（rc + 实测值），禁只写结论。
- 第 5 段 `U-项`：任务卡第 62 行起「未决问题」里凡是**你无法从卡/切片/spec 确定**的，
  逐条上报（问题 + 两个候选 + 倾向及理由）。**禁自行裁定** —— 手册 §6.4 明定
  实现方不得自行决定未决问题。
- 第 6 段 `自报 token`：两个口径都给（单轮上下文规模 / 跨轮累计计费）。
  A183：§15.5 上限按**累计计费口径**判定（max 200k），越限如实报 `over_cap`，禁抹平。
