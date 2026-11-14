# R16 · M0-04/S4 入库取证索引 —— 编排器独立复验 ＋ U 项终裁 ＋ 哨兵迁移

- **时点**：2026-11-15T04:28:17+08:00　**入库前 HEAD**：`2010d57`　**分支**：`m0-framework`
- **lane**：S4 · task **M0-04**（Jobs 作业队列 HTTP 面）· 档位 **qwen3.8-flash / medium**（design §9 冻结，未升降档）
- **agent_id**：`01a1db53-8f51-7303-842f-499f58768eb0`　**昵称**：Anscombe　**loop**：1 / 2（critical=true, slack=0，未触发 STALLED）
- **回执**：`STATUS: DONE_WITH_GAP`　**编排器终裁**：**PASS**（GAP 全部由编排器同批闭合，见 §3）
- **在飞邻居**：lane S2b-1（M2-01 · `01a1db55-3aec-7093-9f55-785932c63478` · Hooke · max/high），写集与本棒实测零交叉
- **口径**：一切读数由编排器实测（`rule_no_trust_handoff_summary_assertions`：禁采信自报）；
  入库四门一律跑在**冻结索引树**上（R11-3），且本批已根治 D-046 的导入泄漏（`frozen_env`）。

## 1. 交付面逐件实测（行 / 字节 / sha256[:12]，均为入库前实测）

| 文件 | 形态 | 行 | 字节 | sha256[:12] |
|---|---|---|---|---|
| `src/campaignlab/api/jobs.py` | 新建（主交付） | 371 | 16916 | `735d30baf0c4` |
| `src/campaignlab/api/common.py` | 修改（append-only） | 1168 | 45605 | `836e7b3e8d3a` |
| `src/campaignlab/api/app.py` | 修改（A10 ≤3 行） | 160 | 7253 | `110751903e4d` |
| `tests/integration/jobs/test_jobs_router_s4.py` | 新建（本棒守护） | 683 | 26515 | `c3110b40b71d` |
| `tests/unit/test_domain_errors.py` | 修改（仅 2 处字面量） | 189 | 7771 | `a933def6c4e5` |
| `orchestrator/handoff/M0-04-design.md` | 修改（文末追加） | 300 | 68556 | `5dd6360851b8` |
| `evidence/M0/M0-04/s4-jobs-router.md` | 新建（lane 取证） | 35 | 7393 | `587aba1c3da9` |
| `evidence/M0/M0-04/commands-s4.md` | 新建（lane 取证） | 102 | 9547 | `5d2d22eecc9e` |
| `evidence/M0/M0-04/positive-control-s4.log` | 新建（.log 不入 ruff 分母） | 64 | 8025 | `597355204386` |
| `orchestrator/handoff/R15-lane-M0-04-S4.md` | 派单文（本批首次入库） | 213 | 21538 | `fe46f8c90934` |
| `orchestrator/defects/D-047.md` | 新建（本批立单） | 84 | 7379 | `86669ce04120` |
| `tests/api/test_contract_declarations.py` | **编排器**迁移（哨兵①） | 214 | 11110 | `a9af20101fe7` |
| `tests/unit/test_s3b_routes.py` | **编排器**迁移（哨兵②） | 211 | 8983 | `b0122388342a` |

## 2. 编排器独立复验结论（逐条对账 lane 自报，全部相符）

| 判据 | 期望（派单文/设计） | 编排器实测 | 结论 |
|---|---|---|---|
| `api/jobs.py` 公开符号面 | 恰 `router, list_jobs, get_job, cancel_job, retry_job` | AST 实取＝该 5 个，无多无少 | ✅ |
| `api/jobs.py` 私有符号面 | 恰 `_job_page_response, _job_response` | AST 实取＝该 2 个（另有模块级 `__all__`，非私有函数） | ✅ |
| 墙钟 / sleep | 禁（红线 3） | 源文本扫 `datetime.now(`/`utcnow`/`time.time(`/`monotonic`/`sleep(` ⇒ **0 命中** | ✅ |
| SQL 字面量 | 禁（N 面：SQL 只在 repositories/store） | 0 命中 | ✅ |
| `api/common.__all__` | 78 → 79，既有 78 项一字不改 | 运行期 79 / `set` 79 / `JobPage in __all__` True；numstat **15/0**（deleted=0） | ✅ |
| `PROBLEM_CODES` / `DomainError` 子类 | 20 / 14 禁改 | 20 / 14 | ✅ |
| `JobPage` 与契约逐字段对齐 | `contracts/openapi.json` 的 `components.schemas.JobPage` | 编排器直接读契约比对：`items` array of `Job` maxItems 100、`next_cursor` anyOf[string 1..300, null]、required 两项、additionalProperties false ⇒ 与实现（`Field(max_length=100)` / `StrictStr 1..300 | None` / `extra="forbid"`）**逐项相符**，且与既有 `WorkspacePage` 体例同构 | ✅ |
| `api/app.py` | ≤3 行 added / 0 deleted；禁改 `openapi_url=docs_url=redoc_url=None`、中间件顺序、既有 3 处挂载 | numstat **3/0**；`openapi_url=docs_url=redoc_url=None` 在场；`include_router` 由 3 → **4**（新增 jobs 为 `if workspace_service is not None:` 条件挂载，与 workspaces 同形） | ✅ |
| `tests/unit/test_domain_errors.py` | 仅 §4② 授权的 2 处数字，≤2/2 | numstat **2/2**，diff 原文恰为 `78→79` 两处字面量，函数名/docstring 未动 | ✅ |
| `M0-04-design.md` 冻结面 | 前 256 行逐字节不变，仅文末追加 | numstat **44/0**；工作树前 256 行拼接 sha256[:12]=`5b76bcb33984` **== HEAD 全文 sha256[:12]**（逐字节相同） | ✅ |
| 新守护用例数 | ≥ 覆盖 §7.5 清单 | `--collect-only` 实测 **34** 条 | ✅ |
| 契约面 | 本棒禁改 | `git diff --numstat -- contracts/` 为空；`openapi.json` 443309 B / sha16 `592571099d63` 未变 | ✅ |
| `tests/integration/jobs/conftest.py` | 禁建（属 S5 写集） | 仍不存在 | ✅ |
| 阳性对照 | ≥8 条，全红 + 字节级复原 | lane 交付 8 条（派单文 §7.6 全清单）；编排器另做 **3 条**针对自身迁移面的对照（PC-B / PC-C / 复原核验），见 §3 | ✅ |

**归因说明（PRE-11 / A223）**：活动工作树上 `ruff format --check` 报 281、`mypy` 报 97~98、
`pytest` 报 646 passed / 3 failed —— 这三个读数**都不是入库读数**：分母含 lane S4 的未入库件与
lane S2b-1 的在飞半成品（`repositories.py` +830/0、`api/deps.py` +175/0、`activity_service.py`、
`test_s2b_activity_surface.py`）；3 条红里 2 条是本批迁移的前提哨兵（§3）、1 条
（`test_repositories_module_all_is_unchanged`）属邻居 S2b-1 的在飞件，**既不是本棒的红也不是本棒的绿**。
入库四门以 `run_commit` 的冻结索引树读数为准，见 §5。

## 3. U 项终裁（lane 只报不裁；编排器逐条终裁，A225–A230）

| U | 事实 | 终裁 | 依据 |
|---|---|---|---|
| **U-1** | `JobPage` 在 `__all__` 的插入位：派单文写「只在末尾追加」，但 ruff 的 `RUF022`（`__all__` 排序）与「末尾」实测互斥 | **A225 采纳 (b)**：以工具裁决位为准（插在 `JobCapacity` 之后）。硬约束是「既有 78 项一字不改、一项不删、相对顺序不动、`deleted=0`」，实测 numstat 15/0 全部满足。派单文措辞失真 ⇒ 记 **R16-3** | A91 / A82 的立法目的是「纯追加不扰动既有面」，不是「物理位置在文件末尾」 |
| **U-2** | 两条 A84/A85 前提哨兵被 S4 落地打红，且红因落在本棒**无写权**的文件里 | **A226 采纳 (b)**：编排器同批迁移（禁 lane 越界自修）。迁移形态＝文件级哨兵 → 结构级不变量，强度不降反升；立 **D-047** 记该缺陷类，并新立 **PRE-14** | A224（同批纪律）、A10、手册 §6.4（lane 禁自裁） |
| **U-3** | `listJobs` 的工作区存在性核验只能靠 `list_workspaces` 有界翻页枚举（端口无单条读口），成本 O(N/100) 页 | **A227 采纳 (a) 维持现状 ＋ 立 FU-51**（给 `WorkspaceService` 补 `get_workspace` 单条读口）。理由：动 `api/deps.py` 的 Protocol 面属公共冻结件，且该文件此刻正在被 lane S2b-1 纯追加 ⇒ 同批改必然双主写 | N4（禁双主写）、A206（禁给 `JobService` 加第二注入项） |
| **U-4** | design §1 把 `If-Match` 写成必填，而 §6/§7 要求「缺头 → 428」；`required` 声明下 FastAPI 只会产 422，428 **结构不可达** | **A228 追认 (b)**：实现取 `str | None` ＋ 显式 `check_if_match`（缺头 428 / 陈旧 412 / 格式非法 422）。编排器独立读契约核实：`cancelJob`/`retryJob` 的 `If-Match` 声明为 `required: true` 且 responses **同时**声明了 412 与 428 ⇒ 契约面不变（对客户端仍是必填），实现侧接受缺席以产出契约**已声明**的 428，而非未在该点声明的 422 | 契约真值优先；design §6/§7 的行为要求优先于 §1 的签名措辞 |
| **U-5** | `store.retry` 使源行 `revision` 1→2（`state` 不变），与 S2c 注记「一字不变」措辞冲突 | **A229 追认**：按 DDL / design §2「每次写 +1」口径；S2c 注记的「不变」指**状态字段**不变，非 `revision`。属措辞澄清，**零代码改动** | D-011（只加注不改写） |
| **自报越界①** | `cancel_job` / `retry_job` 在 design §1 签名之外各增 `clock: Clock = Depends(get_clock)` 形参 | **A230 追认为授权扩形**：红线 3 / D-045 明文要求「需要现在一律走注入时钟」，该形参是其唯一合法形态；design §1 的签名面由文末 §9-S4 注记承接（44/0，前 256 行逐字节未变） | 红线 3、D-045、A214（窄豁免） |

**编排器自纠（如实入账）**
- **R16-3**：派单文 §5「冻结面实测读数」表存在系统性失真 —— `api/app.py` 记 158 实测 **157**、
  `api/deps.py` 记 172 实测 **171**、`deps.__all__` 记 10 实测 **9**（多算了一个不存在的「首项」）。
  lane 上工复测发现并按 PRE-7 双录、未判失真、未停手，处置正确。责任在编排器。
  防再发：**PRE-15** —— 派单文里的冻结面读数一律由脚本实测并把**命令原文**贴进派单文，禁手工数行/数符号。
- **R16-4**：编排器迁移哨兵①时，第一版阳性对照（PC-C）把变异写成 `@router.get(API_PREFIX + "/workspaces")`，
  因 `jobs.py` 的 `router = APIRouter(prefix=API_PREFIX, ...)` 会再补一次 prefix，实际路径成了
  `/api/v1/api/v1/workspaces`，**撞不上** ⇒ rc=0 假绿；并据此在 docstring 里写了「删掉互斥断言也会判红」
  这句失真措辞。两处均同批更正（变异改 `"/workspaces"` ⇒ rc=1 真红；docstring 改为如实描述），
  原文与 rc 见 `commands-and-outputs.log` 的 STAGE A2/A3 段。教训：**阳性对照必须验「变异确实生效」**，
  不能只看 rc；「删断言」永远不是判据有牙的证明。

## 4. 阳性对照（本批全部，含编排器针对自身迁移面的 3 条）

| 编号 | 变异对象 | 变异 | 期望 | 实测 | 复原核验 |
|---|---|---|---|---|---|
| lane PC1–PC8 | `api/jobs.py` / `api/common.py` / `api/app.py` | 派单文 §7.6 全清单（改 `JobPage` 字段名、删 `__all__` 里的 `JobPage`、删挂载、去掉 404 核验、改 `BAD_CURSOR` detail、注入墙钟调用、把 428 改 400、把 202 改 200） | 全红 | lane 报全过；原文 `evidence/M0/M0-04/positive-control-s4.log` | lane 报 sha256 双向相等 |
| **PC-A** | — | 迁移后基线 | 绿 | **rc=0** | — |
| **PC-B** | `api/app.py` | jobs 的条件挂载 → 无条件挂载 | 哨兵② 红 | **rc=1** FAILED | `api/app.py` → `110751903e4d` 字节级相等 |
| **PC-C** | `api/jobs.py` | 注入 `@router.get("/workspaces")`（真撞 `listWorkspaces`） | 哨兵① 红 | **rc=1**（1 failed / 12 passed） | `api/jobs.py` → `735d30baf0c4` 字节级相等 |
| **PC-D** | — | 复原后复跑三个测试文件 | 绿 | **rc=0 · 26 passed** | — |

## 5. 入库四门（冻结索引树；`run_commit` 的实测值见提交台账 `counts`）

预测值（编排器静态推算，`run_commit` 会用冻结树实测值逐条对账，不符即回滚拒绝提交）：
`ruff_formatted_files` **284**（99 py + 185 md）· `ruff check` clean · `mypy_source_files` **97**（95+2 新 .py）·
`pytest_passed` **652**（618 + 新守护 34；两条迁移后的哨兵用例数不变，`--collect-only` 实测 20 与 HEAD 版一致）。

## 6. 悬空引用（逐条判定，`rule_forward_ref_allowlist_is_explicit_per_commit`）

实测 3 条，全部登记 `allow_dangling`，禁改写文本规避扫描：
1. `evidence/M0/M0-04/s4-jobs-router.md -> contracts/spec/scripts/worker/domain/infra/application`
   —— **正则截断产物**，原文是斜杠枚举「`state.json/pyproject/contracts/spec/scripts/worker/domain/infra/application` 全部 0 写入」，非路径（A184 同型）。
2. `orchestrator/handoff/M0-04-design.md -> evidence/M0/M0-04/ac.md` —— **前瞻引用**，S8 的证据落点；
   实测 HEAD 版该文件已含此引用（`grep -c` = 1），非本批新增。
3. `orchestrator/handoff/M0-04-design.md -> evidence/M0/summaries/M0-04.md` —— 同上，S8 落点，HEAD 既有。
   2/3 两条在 M0-04/S8 入库时自动消解。

## 7. 本批未做 / 收口去向（如实上报）

- `tests/unit/test_api_app.py::test_jobs_router_is_not_mounted_by_s3c` **未改**（它仍绿：探的是不注入
  `workspace_service` 的裸装配形态），但函数名与 docstring 语义已过期 ⇒ **FU-50**。
- 两条迁移后守护的**改名**与 docstring 语义升级 ⇒ **FU-52**（本批只加「R16 迁移注记」，不动函数名）。
- 哨兵登记表 ＋ 派单文自动生成「预期红清单」的机器化 ⇒ **FU-53**（PRE-14 的收口面）。
- `listJobs` 工作区核验的 O(N/100) 翻页 ⇒ **FU-51**。
- M0-04 剩余：**S5 → S6 → S8**（全 flash）。S4 入库即释放 `api/app.py` 锁 ⇒ **M2-01/S2b-2 解锁**（max）。
  M0-04 全链闭合前禁判 DONE、禁开 wave3（它是 21 个 TODO 任务的唯一解锁点）。
## 6.1 更正（入库驱动 preflight 重扫；append-only，§6 原文依 D-011 不改写）

**§6 记「实测 3 条」的口径不完整**：那 3 条是在**不含本索引文件自身**的子集上扫出来的。
入库驱动的 preflight 在 `add_paths` 全集（15 件，含本文件）上重扫 `dangling_refs`，实测 **6 条**：

| # | 来源文件 | 悬空目标 | 判定 |
|---|---|---|---|
| 1 | `evidence/M0/M0-04/s4-jobs-router.md` | `contracts/spec/scripts/worker/domain/infra/application` | 正则截断产物（同 §6①，原文是斜杠枚举非路径） |
| 2 | 本文件（§6① 的原文引用） | `contracts/spec/scripts/worker/domain/infra/application` | **自指产物**：§6 为逐条判定而原文引用了该串，于是本文件自己成了同一目标的第二个来源 |
| 3 | 本文件（§6② 的原文引用） | `evidence/M0/M0-04/ac.md` | 同上（前瞻引用，M0-04/S8 的证据落点） |
| 4 | 本文件（§6③ 的原文引用） | `evidence/M0/summaries/M0-04.md` | 同上（前瞻引用，M0-04/S8 的证据落点） |
| 5 | `orchestrator/handoff/M0-04-design.md` | `evidence/M0/M0-04/ac.md` | §6② 原文（HEAD 既有，非本批新增） |
| 6 | `orchestrator/handoff/M0-04-design.md` | `evidence/M0/summaries/M0-04.md` | §6③ 原文（HEAD 既有，非本批新增） |

处置：6 条**全部**逐条登记 `allow_dangling`，驱动内做集合相等断言（实测集 == 登记集，多登记同样判红）。
依 `rule_forward_ref_allowlist_is_explicit_per_commit`，**禁改写文本规避扫描** ⇒ 不采取「把路径拆断／插空格／换成不可匹配的写法」
这类让正则扫不到的做法 —— 那会使 allowlist 与实际引用面脱钩，等于把判据弄瞎。

**根因与防再发（记 R16-7、立 PRE-17）**：取证索引的职责就是**逐条引用**待判定的路径，
故它天然会把自己登记进悬空引用面 —— 「记录悬空引用的文件自身产生悬空引用」是自指的必然结果，不是缺陷；
真正的问题是**扫描口径**：§6 的 3 条是在入库驱动尚未成形时取的，没把索引自身算进分母。

> **PRE-17**：悬空引用一律由入库驱动在 `add_paths` **全集（含取证索引自身）**上调用 `dangling_refs` 实扫取得，
> 并把实扫结果原样贴进取证索引；禁手工枚举、禁在不含索引自身的子集上取数、禁为凑「条数好看」而改写引用文本。
> 本条与 PRE-15（冻结面读数由脚本实测并贴命令原文）同源：**凡是要写进取证的分母，都必须由脚本在被入库的那个集合上取**。
