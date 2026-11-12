# v1.0.1 月报补丁合入后的长程工作流评审

- 产出任务：M0-P01 收尾（Lane T / 编排器自执行）
- 时间：2026-11-12 · 分支 `m0-framework`
- 状态：**评审结论待项目负责人确认；未开工**
- 依据（真值来源，非记忆）：`orchestrator/state.json`、`docs/delivery/LONG-HORIZON-ORCHESTRATION.md`、
  `docs/delivery/MONTHLY-DELTA-PLAN.md`、`orchestrator/BLOCKERS.md`
- 实测数据来源：`evidence/monthly/M0-P01/run-02/commands.md`（14 项门禁，rc 由脚本实跑回填）

---

## 0. 结论摘要

| 维度 | 是否需调整 | 数量 | 性质 |
|---|---|---|---|
| 断点续跑安全 | **需要（已在本轮修复）** | 5 处 | 不修则新实例可能擅自开工、重复实现或丢证据 |
| 剩余任务安排（DAG / 波次） | 需要 | 3 处 | **不改依赖图**，只改「设计前置」触发条件与任务卡验收项，低风险 |
| 模型资源分配 | 需要 | 1 必修 + 2 优化 | 必修＝成本账本从未写入，省钱目标当前**不可验证** |
| Loop engineering | 需要 | 2 处 | 关键任务 L 循环上限 3→2 轮；校验脚本强制自带篡改负例 |

---

## 1. 断点续跑安全（对应「不具备则修正到可续跑状态」）

| # | 隐患 | 实测证据 | 修复 |
|---|---|---|---|
| 1 | **开工闸门缺失（最高危）** | `grep -n "开工\|OWNER_GO\|owner_gate\|HOLD"` 对手册零命中；`resume.next_actions[3]`＝「并行派发 wave1：M0-02 与 M0-03」 | 手册新增 15.1；`state.json.resume.owner_gate=AWAIT_OWNER_GO`；`next_actions` 首条改为「等待开工指令，此前只允许只读自检与治理修复」；BLOCKERS 记 NOTE-04 |
| 2 | `resume.persisted.head` 陈旧 | 记 `baa7389`，实际 HEAD `f842ec2`（同类问题在 30291b8 已发生过一次） | 本轮写入真实提交号，并在手册 15.2 规定「每次提交后同步 head」 |
| 3 | `self_check_gates_rc0` **悬空引用** | `resume.context` 要求「新实例必须重跑本节 `self_check_gates_rc0` 后才能派单」，但 resume 块中**无此键**（实测键列表：recovered_at/incident/wave/gate/next_actions/in_flight_agents/dispatch_requirements/wave0_commit/persisted/context/patch/critical_path_len/slack_note/m0_p01_commit） | 本轮把 G1–G14 的实测 rc 写入该键，引用不再悬空 |
| 4 | **D-003 证据被忽略** | `.gitignore` 的 `*.log` 使 `tasks["M0-P01"].gates[]` 7 条 evidence 指针中 **4 条**在仓库内不存在；手册 9.2 却要求 `<gate>.log` 入库 | `.gitignore` 加 `!evidence/**/*.log`；6 个证据文件入库；实测 `evidence/` 下被忽略文件数＝**0** |
| 5 | **D-002 未提交**（跨会话累积脏树） | 接管时 `git status` 有 2 改 2 新；宿主重启后工作树仍在而上下文丢失 → 新实例可能重复实现同一修复 | 本轮提交；手册 15.2 规定「缺陷修复即时提交，工作树不得跨任务累积未提交改动」 |

补充：D-002 原修复**没有单测**，违反手册 13.3 第 4 条。已补 `tests/unit/test_frontend_baseline.py` 6 条，
`pytest` 用例数 8 → 14，`mypy` 受检源文件 5 → 6，均 rc=0。

---

## 2. 剩余任务安排：3 处调整

事实基线（读自 `state.json`）：29 任务 / 11 波 / 47 AC（35 基线 + 12 月报）；
状态分布 `DONE=1`（M0-P01）、`VERIFYING=1`（M0-01）、`TODO=27`；
关键路径长度 **14**、**3 条并列链**；`critical=true` 共 **16** 个任务。

### 调整 1（必须）· M0-04 任务卡增加「指标注册表可外部注册」验收项
M3-P01（wave5，L3 lane，评分 12＝max high，覆盖 12 条 AC）需要注册月报指标，而指标注册表属**公共件**，
wave2 出口即冻结。若冻结时未预留扩展点，wave5 只能走 CR 由 T lane 串行合并 → 吃掉 M3-P01 的 `slack=4`，
并把 L3 lane 推成关键路径。写权限论证：M0-04 属 S lane，改的是公共件本身、不涉及月报实现，无越界。

### 调整 2（建议）· M4-P01 的 max 设计子任务前置到 wave7
M4-P01 `slack=0` 且是**四前置汇聚点**（M4-01、M4-02、M4-03、M3-P01），任一延误即延误交付；
其 tier 为 mixed（状态机与签认语义 max，页面与导出样板 flash）。
把「max 产出 `orchestrator/handoff/M4-P01-design.md`」移到 wave7 与 M3-P02 并行、实现仍留 wave8，
可将 slack=0 段的部分工作量搬进有浮动的窗口。
- 写权限论证：设计文档只写 `orchestrator/handoff/`（T lane 所有）；M3-P02 只写 `pages/review/monthly/**`
  与 `features/monthly/**` —— 不相交。
- **触发条件（必须）**：仅当 M3-P01 已 `PASS`（分母、交集、去重、覆盖率口径已定稿）时才前置；
  否则保持原计划，避免设计返工反而更贵。

### 调整 3（建议）· M5-P01 的 flash 采集脚本与走查清单前置到 wave8
M5-P01 `slack=0`，依赖 M5-01（固定环境回归）；M5-01 一旦返工，M5-P01 无浮动可吸收。
把「走查清单 + Playwright 采集脚本 + `qa-reports/monthly/` 模板」在 wave8 由 flash 预生成
（只写 `evidence/monthly/M5-P01/prep/` 与 `qa-reports/monthly/`），wave9 只跑 max 判定，
可把最贵的一轮压缩到最短。与 M5-02 的 `qa-reports/m5-02/`、`defects/D-*.md` 不重叠（M5-P01 用 `defects/DMR-*.md`）。

### 明确不调整（据实说明）
- M1-P01（slack=4）、M3-P01（slack=4）、M3-P02（slack=2）落点波次不动：它们的浮动正是用来吸收 max 档返工的，
  提前反而占用关键资源。
- `M5-03.deps=[M5-02, M5-P01]` 已在 M0-P01 补齐（否则月报未走查就签认），无需再改。
- 阶段配额维持 M0-P01 已调值：M0 100 / M1 150 / M2 150 / M3 175 / M4 140 / M5 110。

---

## 3. 模型资源分配：1 处必修 + 2 处优化

事实基线：`tier_planned` 分布 **max=20 / mixed=7 / flash=1 / human=1**；lane 分布 D=9 S=7 F=7 T=3 Q=2 O=1；
`budget.phase_used=0`、全部任务 `tokens=0`、`flash_share_tasks=0.0`、`flash_share_tokens=0.0`。

### 必修 · 成本账本从未写入，省钱目标当前不可验证
手册 6.6 规定：flash ≥ 60% 子任务数、token ≤ 35%、阶段配额 80% 触发上下文压缩、120% 暂停非关键任务、
单任务上限 flash 60k / max 200k。但实测 `tokens` 与 `phase_used` 恒为 0、`flash_share_*` 恒为 0.0，
且**任务级档位无法回答子任务级占比**（任务级 flash 仅 1/29 ＝ 3.4%，与 60% 目标不是同一口径）。
若不修，全部配额与占比条款都无法触发，「高低搭配降本」只是声明。

修复（手册 15.5，wave1 起生效）：
1. 每次 spawn 回收后必须写回该子任务的 `tier_planned` / `tier_used` / `tokens` / `escalated` / `reason`；
2. 新增 `budget.subtask_log[]`（`{task, subtask, tier, tokens, attempt, result}`）作为**子任务级**真值；
3. `flash_share_tasks` / `flash_share_tokens` 由编排器每轮**程序化重算**，禁止手填；
4. 任务卡模板（3.2）增加「子任务档位表」一栏，**无拆解表不得 spawn**。

### 优化 1 · M3-P01 拆成 3 个子任务包
它评分 12（max high）、覆盖 12 条 AC（全项目最多），单包极易撞 200k 上限后被迫拆小返工。
建议按语义聚类拆为「三月交集与去重」「两种覆盖率与容量客均」「客群与总分行口径」三包，
每包由 max high 出黄金值判定，参数化展开与负例枚举下放 flash。
（AC 与子包的对应关系必须在写任务卡时按 `qa/ACCEPTANCE.md` **原文逐条核对**，此处只给聚类方向，不代替原文。）

### 优化 2 · M0 阶段 Q 复核合并为一次
当前待复核：M0-01 九项门禁、M0-P01 契约门禁与 CR-001/ADR-004/CHANGES.json 一致性、D-001、D-002、D-003。
分派 5 次 Q ＝ 5 轮 max 判定开销。建议合并为**一个 Q 任务**：flash 采集全部 rc 与差异清单 → max 一次性判定。
证据已在 `run-01/commands.md`、`run-02/commands.md`、`evidence/M0/M0-01/*` 齐备，具备合并条件。
（是否派 Q 属 `pending_owner` 的 `Q-VERIFY-M0-01`，默认派；本条只改「派几次」。）

### mixed 7 个任务是 flash 占比的主战场
M1-04、M2-04、M3-04、M3-P02、M4-02、M4-03、M4-P01 必须严格执行「max 出设计 → flash 量产」。
可下放清单：页面样板与表单铺开、参数化负例枚举、CSV 等价样例校验、截图与证据采集、文档与回执。
若这 7 个任务按 max 单体执行，flash 子任务占比**不可能**达标。

---

## 4. Loop engineering：2 处调整

### 调整 1（必须）· 关键任务 L 循环上限 3 轮 → 2 轮
现状（6.5 / 10 节）：flash 2 轮失败升 max；max 3 轮未过升 BLOCKER；同任务累计 6 轮。
问题：16 个 `critical=true`（slack=0）任务**没有浮动吸收返工** ——
在 M4-02、M4-03、M4-P01、M5-01、M5-02、M5-P01 上跑满 3 轮 max，等于直接延误交付。
新规则：
| 任务浮动 | L 循环上限 | 触顶动作 |
|---|---|---|
| `critical=true`（slack=0） | **2 轮** | 写 BLOCKER，并**同时给出「缩小范围」的降级交付选项**（降范围不降质量）交项目负责人裁定 |
| slack 1–3（M3-04、M3-P02） | 3 轮 | 原规则：max 3 轮未过升 BLOCKER |
| slack ≥ 4 | 3 轮 + 1 轮 max 复审 | 用浮动吸收返工，不冲击关键路径 |

### 调整 2（必须）· 新增校验脚本强制自带篡改负例
D-001（`--tables` 静默返回 NOT_FOUND 且 rc=0）与 D-002（表格式变化可能解析到 0 行）是**同一类失效：校验器恒真**。
两者都是靠「加负例」才暴露的。新规则（手册 15.4）：任何新增或修改的校验/抽取脚本，交付时必须附
① 一条篡改负例（改一个字节 → 期望非 0 rc）与 ② 一条分母断言（解析条目数 ≠ 期望 → rc=2），
并在证据中记录**期望 rc**；缺负例的脚本不得进 CI。
已落实：`contract_slice.py`（8 例）、`check_frontend_baseline.py`（6 例）。

### 明确不调整
三层循环结构（L 子任务内 / T 任务间 / M 阶段）、L4 失败四分类（实现缺陷 / 契约歧义 / 环境问题 / 测试期望错误）、
幂等重跑要求均不变。本轮实测确认现有门禁**全部可安全重跑**：`monthly_delta.py` 合并后全 ALREADY（幂等）、
`check_frontend_baseline.py` 只读、`check_contracts.py` 幂等、`verify.sh` 字节级复现（跑完 `git status` 干净）。

---

## 5. 其他细节确认

- **环境**：WSL2 Ubuntu 24.04.2 LTS；项目 venv CPython 3.14.10（系统 python 3.12.3）；uv 0.13.7；
  Node v24.22.3；SQLite 3.53.1；无 sudo；`gh` 未认证（PR 需人工建）。
- **写入通道铁律**（不变）：多行 Python 与多行 bash 一律 here-string→base64；禁含 `/` 的 `sed` 模式串；
  提交信息 `git commit -F 文件`；禁 `git add -A`，只用显式路径；子智能体不碰 git。
- **领域不变量**（不变）：`spec/**` 只读、只用合成数据、领域计算禁用系统时钟（显式时钟）、
  金额用分的整数、比率用十进制字符串、时区 Asia/Shanghai。
- **待项目负责人裁定**（`pending_owner`，均有默认值，不阻塞 wave1）：ADR-003 三项、SRC-1（Source-Extract 缺失）、
  `Q-VERIFY-M0-01`（默认派 Q；本评审建议合并为一次）。
- **外部依赖**（不阻塞）：BLK-02 `fonts-noto-cjk`（doctor 实测 WARN，中文字体 7 条可用但字形度量与行内设计基线不一致）、
  BLK-03 `gh auth login`、BLK-04、BLK-05。
- **基线内部一处文字不一致（不改，仅留痕）**：前端基线 README 第 21 行写作 `00_模板入口.html`，
  磁盘实际文件为 `00_模版入口.html`（第九节排除说明用的是正确写法）。`spec/**` 不可变，故不改；
  已用单测钉住 `SELF_EXCLUDED` 与实际文件名一致，防止后人「按第 21 行改正」反而改错。

---

## 6. 开工前需项目负责人确认的 4 件事

1. 是否批准 §2 调整 1（M0-04 增加「指标注册表可外部注册」验收项）—— 建议批准，否则 wave5 有被推成关键路径的风险。
2. 是否批准 §2 调整 2 / 3（M4-P01 设计前置、M5-P01 采集前置）—— 建议批准，且调整 2 必须带「M3-P01 已 PASS」触发条件。
3. 是否批准 §4 调整 1（关键任务 L 循环上限收紧为 2 轮 + 降级交付选项）—— 建议批准。
4. `Q-VERIFY-M0-01`：是否同意把 M0 阶段的 5 项复核合并为一次 Q（flash 采集 + max 判定）。

未获确认前按现有手册执行；获得明确「开工」指令后，从 wave1（M0-02 ∥ M0-03）起派单。