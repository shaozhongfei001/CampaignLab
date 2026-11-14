# R14 · lane A1 · M2-01 / S2a 派单文（qwen3.8-max / reasoning high · critical=false · slack=4 · loop_cap=3+1 复审）

> 本文件是本棒的**唯一**派单入口。公共纪律见 `orchestrator/handoff/LANE-COMMON.md`（已入库，按需定点读，禁整读）。
> 设计权威＝`orchestrator/handoff/M2-01-design.md`（1322 行，S1 已冻结入库）。**禁整读该文件**：
> 按 §1 的映射表**逐段定点读**，写哪个模块就读哪一段（这是本棒省 token 的主要手段）。
> 你的 S1 前任（lane Z）已把符号面、错误码、状态机、字段约束全部冻结并逐条标了切片真值来源路径，
> 你的工作是**机械而精确地铺开**，不是再设计一遍。遇设计外问题一律报 U 项（手册 §6.4），禁自裁。

## 0. 基线（开工第一件事，全部实测）

1. `git log --oneline -1` 与 `git status --porcelain` —— 记下 HEAD sha；工作树里若有**不属于你写集**的件，
   按 LANE-COMMON §4 记进回执第 8 段（IN_FLIGHT_CONTAMINATION），**禁修、禁计入自己的 RED**。
   当前已知在飞：lane Y（Mendel · M0-04/S2b-3）会动 `src/campaignlab/infra/db/repositories.py`、
   `src/campaignlab/worker/integrity.py`、`tests/unit/test_worker_integrity.py`、`evidence/M0/M0-04/*`、
   `orchestrator/handoff/M0-04-design.md`（文末追加）。**这些你一律禁碰。**
2. 切片新鲜度：`contracts/openapi.json` 实算 sha256 前 16 位与字节数，必须等于
   `state.json → resume.self_check_gates_rc0.counts.live_openapi_sha16` / `.live_openapi_bytes` 的**现值**
   （禁写死数字，D-012/D-014）；不一致即停手回报，**禁自行重切**（`scripts/**` 不在 scope_allow）。
3. 符号面实取：`PROBLEM_CODES` 应为 20 码、`api/common.__all__` 应为 51 项、`DomainError` 子类应为 14 个。
   **本设计零新增 Problem.code、零新增 DomainError 子类**（design §4.3 / §6.4 已逐处遵守）；若你的实现
   发现必须新增，停手报 U 项。

## 1. 任务：M2-01/S2a ＝ design §11.1 ＋ §11.2（**不含 §11.3**）

| 模块 | 定点读 design 的哪一段 | 产出 |
| --- | --- | --- |
| `domain/activity/states.py` | §11.1 该条 ＋ §3（状态机，行 244–353） | 类型别名 + 迁移表 + assert 守卫 |
| `domain/activity/digests.py` | §11.1 该条 ＋ §4.6 | `rule_digest` / `digest_projection` |
| `domain/activity/clauses.py` | §11.1 该条 ＋ §4（条款门禁，行 354–463） | `REQUIRED_CLAUSE_KEYS` / `evaluate_clause_gate` 等 |
| `domain/activity/bindings.py` | §11.1 该条 ＋ §3.4 | `BindingDraft` / `validate_bindings` / `intervals_intersect` |
| `domain/activity/checks.py` | §11.1 该条 ＋ §5（检查项框架，行 464–610） | `CHECKS` / `run_checks` / `boundary_cases_for` 等 |
| `domain/activity/diff.py` | §11.1 该条 ＋ §6.5 | `field_changes` / `render_scalar` / 四类 path 常量 |
| `domain/activity/__init__.py` | §11.1 开头 | 导出面（与 design 的符号清单逐字一致） |
| `api/common.py`（**纯追加**） | §11.2（行 1016–1032）＋ §2（数据结构，行 135–243） | 4 个别名 re-export ＋ 全部新 DTO ＋ `__all__` 追加 |
| `tests/unit/test_domain_errors.py`（**仅 1 行**） | §11.2 末条 | 只抬 `len(common.__all__)` 的数字字面量 |

**§11.3（`application/activity_service.py`、`infra/db/repositories.py`、`api/deps.py`、`api/app.py`）本棒禁做**，
已拆为 **S2b**（裁定 **A210**）：`infra/db/repositories.py` 的 append-only 额度当前由 M0-04/S2b-3 持有
（A204，依 A82），两个 lane 同窗追加同一文件＝写集相交，禁。S2b 会在 S2b-3 入库后另发派单文。

## 2. 必须携带的裁定（禁自行发明）

- **A195**：`listActivities` / `listRules` 在活契约里**确实有** `status` 与 `q` 参数（编排器实测：17 个 list*
  操作中 16 个含 status、17 个含 q；只有 `listWorkspaces` 依 CR-002/ADR-006 移除了 status）。
  设计文档是**契约忠实**的，照它实现即可；本棒是纯领域层 + DTO 面，`status`/`q` 的**查询实现**归 S3/S4，
  但 `ActivityStatus` / `RuleState` 的取值集合必须与契约 enum 逐字一致。
- **A196**：7 条路径的窄口径扩围已批准，其中本棒只用到 3 条（`domain/activity/**` 新建、
  `api/common.py` 纯追加、`test_domain_errors.py` 的计数字面量行）。三条硬约束：
  ① `api/common.py` **numstat 必须 N add / 0 del**（A91 体例）；
  ② `test_domain_errors.py` **只准改那一条数字字面量**，**禁**把它改造成 inspect 碰撞检查
  （编排器已裁定：字面量钉死比碰撞检查更有牙，改造诉求顺延 FU-39）；改动行数 ≤2、禁删任何用例；
  ③ 新 DTO 的位置排在既有 `Job` 之后、私有助手之前，分节注释体例对齐 `WorkspacePage`。
- **A198**：同 `strategy_id` 的绑定区间**部分重叠即拒** ⇒ `bindings.py` 的 `intervals_intersect` 必须是
  「起含止排」的标准相交式（部分重叠返回 True），`validate_bindings` 的四条顺序＝空区间 → 重复键 → 相交 →
  证据未登记，issue code 用 `BINDING_OVERLAP` 等 design 已钉死的标签，**禁另编**。
- **A200**：允许同一父版本存在多个 `CONFIRMED` 后继；「当前版本」＝`confirmed_at` 最大者，**并列取 id 最大者**。
  本棒若需暴露该选择逻辑，只准做成**纯函数**（禁读时钟、禁 SQL）；真正的取数归 S2b。
- **A201**：`Problem` 是 `additionalProperties: false`，**没有** `diff` 字段 ⇒ 409 的定位信息走
  `Problem.issues[]`（code + location），`compareRules` 的差异走 `RuleDiff.changes[].path`。
  `diff.py` 的 `FieldChangeDraft.path` 只准用 §6.5 的四类 path 常量，禁发明第五类。
- **A203**：AC-004 的**框架面**（必填条款未确认则无法确认、五类检查项各自可判）归本任务；
  **±1 数值面**归 M2-02 ⇒ `checks.py` **禁**实现金额分/数值容差判定（那是 M2-02 的 `domain/rules/**`）。
- **A209**（体例参考）：本仓 DI 一律 `Depends(...)` 默认值形式 + 就地 `# noqa: B008`，禁 `Annotated[...]`。
  本棒不动 `api/deps.py`，此条只作为你写 DTO/领域码时的体例参考。

## 3. 写权与硬禁

**只准写**：`src/campaignlab/domain/activity/**`（只新建）、`src/campaignlab/api/common.py`（纯追加）、
`tests/unit/test_domain_errors.py`（仅那 1 行数字）。**禁任何 git 写操作**（add/commit/stash/reset/checkout 全禁）。

**硬禁**（越界即停手回报）：`orchestrator/state.json`、`scripts/**`、`contracts/**`、`spec/**`、`migrations/**`、
`web/**`、`qa-reports/**`、`src/campaignlab/infra/**`（含 `db/repositories.py`）、`src/campaignlab/application/**`、
`src/campaignlab/worker/**`、`src/campaignlab/api/{activities,rules,deps,app,jobs,session,workspaces,imports,snapshots,definitions,channels,compare,preflight}.py`、
`src/campaignlab/domain/{rules,replay,preflight,ingest,snapshot,caliber}/**`、
`tests/**`（除上面那 1 行）、`orchestrator/handoff/M2-01-design.md`（**S1 已冻结，禁改一字**）、
`orchestrator/handoff/M0-04-design.md`、`evidence/**`（证据采集归 S7）。
**domain 层三禁**：禁 SQL 文本、禁开事务、禁 `import campaignlab.api`
（`digests.py` 的 `canonicalize` 由调用方注入，正是为了不产生 `domain → api` 运行期导入边）。

## 4. 自验门禁（一律 `uv run --no-sync`；分母只报**实测值 + 归因**，禁写死数字当判据 —— R13-6）

| 命令 | 期望 |
| --- | --- |
| `ruff format --check <你的 3 个写集路径>` | rc=0 |
| `ruff check <同上>` | rc=0 |
| `ruff check --select I --diff <同上 .py>` | rc=0 且 diff 为空 |
| `mypy`（全表） | rc=0；报**实测**源文件数并归因（= HEAD 基线 + 你的新增 .py 数） |
| `pytest -q`（全表） | rc=0、0 failed；报实测 passed 数并归因（本棒**不新增**测试文件，故用例数应 = HEAD 基线） |
| `pytest -q tests/unit/test_domain_errors.py` | rc=0（含你抬升后的 `__all__` 计数字面量） |
| `python scripts/check_contracts.py check --validate` | rc=0（契约门禁未回归；登记项数以 `.counts.contract_registered_nodes` 现值为准） |
| `git diff --numstat HEAD -- src/campaignlab/api/common.py` | `N 0`（**删除行必须为 0**） |
| AST 自检：`domain/activity/**` 内 SQL 动词字面量 / `import campaignlab.api` / 读时钟（`time.`/`datetime.now`） | 三者命中数均 **0** |

**★ R14-1（重要，避免你自己踩假红）**：本项目 `requires-python = ">=3.14,<3.15"`、ruff `target-version = "py314"`、
mypy `python_version = "3.14"`、`.python-version` = 3.14.10。故 `except A, B:`（不带括号，PEP 758）在**本项目是合法**写法
（既有例：`api/common.py:574`、`:608`）。**一切 AST / 语法探针必须用 `uv run --no-sync python`（3.14.10）**，
**禁**用系统 `python3`（实测 3.12.3）—— 3.12 会对 PEP 758 写法报
`SyntaxError: multiple exception types must be parenthesized`，那是**假红**，不是你的缺陷。
两种写法都可接受；若你偏好带括号的形式，同样合法。

文件卫生：UTF-8 / 无 BOM / 无 CR / 尾单个 `\n` / 行宽 ≤100（ruff line-length=100）。

## 5. 守护必须有牙（LANE-COMMON §6）——本棒不新增测试文件，故用**变异探针**取证

本棒的量产测试归 S5/S6（flash 档，A210 的档位面安排），但你必须证明**已落地的自证面真的有牙**：

1. design 要求的模块级自证（如 `checks.py` 的 `assert len(CHECKS) == len(CHECK_IDS)` 且 `CheckId` 无重复）：
   在 **tmp 副本**上复制一份 `checks.py`、故意让某个 `CheckId` 重复 → 必须 `AssertionError`；贴 RED 原文。
2. `test_domain_errors.py` 里你抬升后的 `len(common.__all__)` 字面量：在 **tmp 副本**上把该数字改成 ±1 →
   该用例必须判红；贴 RED 原文（证明你抬的是真钉子，不是把守护掏空）。
3. `api/common.py` 的「无第二份定义」纪律：程序化断言 `_IdStr` / `RevisionInt` / `Issue` / `Problem` /
   `ObjectKind` 在本文件内**只有一处定义**（`class X` / `X =` 的计数 == 1），贴实测计数。
4. 所有探针一律走 `tmp_path` 或 `/tmp`，**结束后 `git status --porcelain` 必须与开工时逐字相同**
   （除你写集内的件）；贴开工/收工两次 status 原文。

## 6. Token 双上限（R13-4：两个口径都要在回执里给结论）

- **§5.1 单轮输入上限**：max 档 **40k**。禁整读 design（1322 行）与整读 `api/common.py`；按 §1 映射表定点读。
- **§15.5 累计计费上限**：max 档 **200k**，判定口径＝**累计计费**（A183）。拿不到计费表读数就如实报
  `over_cap` 与估算依据，**禁**抹平、**禁**用「纯产出部分在上限内」这类口径把越限记成合规。
- 卡片规划口径：S2 预估 35k（本棒少了 §11.3，应更低）。

## 7. 回执（LANE-COMMON §7 的 8 段，≤90 行）

1. `RESULT: DONE|PARTIAL|STALLED` + 一句话结论
2. 逐交付件：`numstat +/−`、bytes/lines、sha256 前 12、关键判据实取值（`__all__` 新实取值必须给）
3. 自验命令对账表：命令 / rc 实测 / 关键输出 / 期望 / 判定（**禁**写「应该通过」）
4. 正向对照：§5 的 4 条，每条给变异点 → RED 原文摘要 → 复原证明
5. U 项：问题 + 两个候选 + 你的倾向（**禁自行裁定**）
6. 自报 token：§5.1 与 §15.5 **两个口径分别给结论**
7. L 循环：用了几轮 / 上限 3（+1 max 复审轮）/ 是否 STALLED
8. IN_FLIGHT_CONTAMINATION：不属于你写集的在飞件（禁修、禁计入自己的 RED）

## 8. L 循环

上限 **3 轮**（卡片 `loop_cap`：3 轮 + 1 轮 max 复审，依 `critical=false`、`slack=4`）。
同一条判据连续 2 轮修不绿 ⇒ 停手报 `STALLED`（附两轮 RED 原文），禁无脑重试烧 token。
