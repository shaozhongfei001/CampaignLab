# R14 · lane Y（Mendel）续接派单文 · M0-04 / S2b-3（补 design §5:52 的 ④⑤ 判据）

> 本文件是 **A168 串行链的第 5 棒**：S2b-1 → FU-29 → S2b-2 → **S2b-3** → S2c → S4/S5/S6/S8。
> 由**同一条 qwen3.8-max lane 用 `send_input` 续接**（A168 ③④：复用省 token，**禁档位置换**、禁新起 lane）。
> 你的 S2b-2 已回执 **PARTIAL** 并由编排器独立复验通过、随下一次提交入库；本子任务只做那**一个**缺口。
> 读法：本文件是**唯一**派单入口。`orchestrator/handoff/R13-lane-Y-M0-04-S2c.md`（已入库）是**下一棒**，
> 本棒**禁**提前实现 S2c 的任何符号。

## 0. 身份·档位·循环

- lane：Y ｜ nickname：Mendel ｜ 档位：**qwen3.8-max** / reasoning high（A168 禁档位置换）
- 任务：M0-04 ｜ 子任务：**S2b-3**（A204 新立）｜ critical=true ｜ slack=0
- L 循环上限：**2 轮**。同一条判据连续 2 轮修不绿 ⇒ 立刻停手报 `STALLED`（附两轮的 RED 原文），禁第 3 轮硬试。
- 基线：HEAD = 编排器 send_input 时告知的 sha（S2b-2 已入库）。**开工第一件事**是实测 `git log --oneline -1`
  与 `git status --porcelain`，把你的 4 个 S2b-2 交付件确认为**已跟踪且无改动**；若仍是 `??` 未跟踪，
  说明编排器尚未落地，**停手回报**，禁在未入库的树上继续叠加。

## 1. 唯一目标

补齐 `orchestrator/handoff/M0-04-design.md` 第 52 行 `verify_artifact_index` 判据的**后两项**：

- **④ `jobs.result_json` 可解析** → 不可解析时报 `Discrepancy(reason="RESULT_JSON_UNPARSEABLE", …)`
- **⑤ `result_json` 的 ref 指向存在的对象** → 悬空时报 `Discrepancy(reason="RESULT_REF_DANGLING", …)`

①②③（`relative_path` 存在性 / sha256 / byte_size）与两条安全兜底（`PATH_ESCAPE` / `UNREADABLE`）
你在 S2b-2 已交付且复验通过，**禁重写、禁改判据**，只做必要的最小接线。

## 2. 必须携带的裁定（禁自行发明，手册 §6.4）

### A204（你的 U-1 → 采纳选项 b，且**它本来就不是越界**）

编排器实测：`orchestrator/state.json → tasks["M0-04"].scope_waivers_round7.items[0]`（依 **A82**）
早已给出 `src/campaignlab/infra/db/repositories.py` 的 **append-only 豁免**，
而 S2b-2 的派单文**未逐字引用**它 ⇒ 你撞到的「BLOCKER」是**假 BLOCKER**，根因在编排器（自纠 **R13-7**）。
本棒据 A204 明确授予：

- 允许给 `JobRepository` **纯追加**一个读侧访问器：
  `list_for_workspace(self, conn: Connection, workspace_id: str) -> list[JobRecord]`
  （**逐字对齐** 同文件 `ArtifactRepository.list_for_workspace`（:366）的体例：同样的 `conn` 位置参数、
  同样的 `list[Record]` 返回、同样只读、同样走 `_job_of`/既有行→记录转换函数，**禁**新写一个转换器）。
- **禁**新增 `list_all`（全表无界枚举）。枚举口径必须复用你在 `integrity.py::_artifact_records`（:118）
  已经落好的形状：`WorkspaceRepository.list_page(conn, limit=_WORKSPACE_ENUM_LIMIT)` 枚举工作区 →
  逐工作区取 jobs 行。理由：与制品侧同口径、有界、可复现。
- A82 的硬约束**逐条继承**：禁改既有方法的签名/函数体/SQL 文本；禁改 `job_from_row`、5 个 Record dataclass
  的既有字段、其余 4 个 Repository 类；禁在任何其他文件出现 `INSERT INTO jobs` / `UPDATE jobs`。
  `git diff --numstat` 对该文件必须是 **N add / 0 del**，出现删除行即判越界。
- 既有守护必须继续绿：`INSERT INTO jobs|UPDATE jobs` 的文件集合 == `{repositories.py}`；
  `tests/unit/test_job_repository_terminal.py::test_worker_package_contains_no_table_dml_literals` 判绿
  （**worker/** 内除 `BEGIN IMMEDIATE`/`COMMIT`/`ROLLBACK` 三条事务常量外，禁出现任何 SQL 动词字面量，
  含只读 `SELECT`；docstring 例外**不算**豁免通道，禁把 SQL 藏进 docstring 再用字符串拼接取出——那是静默损坏）。

### A205（你的 U-2 → 采纳选项 a 的**精确形态**，否决选项 b）

- A155① 已把 M0-04 的 `result_ref` 冻结为 `ObjectRef(kind="job", id=<job_id>)`，即 id 指向**作业行**。
  故 ⑤ 的判据 = **该 ref 指向的 `jobs` 行存在**（同工作区内）；不存在 → `RESULT_REF_DANGLING`。
- **否决**你的选项 b（核 `artifacts` 里存在同 `(workspace_id, kind=JOB_RESULT)` 的行）。编排器实测依据：
  `ArtifactRecord` 的字段只有 `workspace_id/id/kind/sha256/relative_path/byte_size/created_at`
  —— **没有任何 job 关联列**；且 `infra/artifacts.py::relative_path_for(kind, workspace_id, sha256)`（:144）
  由 (kind, workspace_id, sha256) 决定路径，**不内嵌 job id**。⇒ 制品侧与作业侧**不存在**逐作业的精确链接，
  选项 b 只能退化成「该工作区至少有 1 条 JOB_RESULT 制品」的**工作区级**弱判据：
  它对「无制品的作业」（失败/取消/不产制品的 kind）会**假红**，且不是逐作业判据 ⇒ 判为自毁判据，否决。
  给 `artifacts` 加关联列属 DDL 变更（归 M0-02 首迁 + CR），**不在** M0-04 范围。
- 只核 `result_json IS NOT NULL` 的行（该列可空，实测 `JobRecord.result_json: str | None`）。
- ④ 的判据：`result_json` 必须能 `json.loads` **且**形状符合 A155①/A89 冻结的 ref 形态；
  两者任一不成立 → `RESULT_JSON_UNPARSEABLE`（形状不符与不可解析同一 reason，用 `detail` 区分，禁新增第三个 reason）。
- `Discrepancy` 的 8 字段与前 5 元组**逐字不变**（design §5:52），只允许 `reason` 取值集合扩两项；
  扩了就在模块 docstring 的 reason 清单里同步登记（禁只加代码不登记）。

### A206 / A207 / A208 / A209（你的 U-3 ~ U-6，本棒**只需知道，不需实现**）

- **A206（U-3）**：`deps.py::get_job_service` 的 `factory(store=…)` **保持关键字传参**；
  S2c 的 `JobService.__init__` 已被钉死必须接受 `store` 关键字 ⇒ 你**无需**改 `deps.py:135`。
- **A207（U-4）**：`deps.py:55` 的 `# type: ignore[import-not-found]` **本棒禁删**（`service.py` 尚不存在，
  删了 mypy 立刻判红）。它由 **S2c 在创建 `service.py` 的同一次提交内删除**（已写进 S2c 派单义务）。
- **A208（U-5）**：采纳选项 a。A156 的 serve 启动接线归 **S4**：在 `src/campaignlab/cli.py::cmd_serve`（:289）
  的启动序列里显式调一次 `get_artifact_writer()`（≤3 行新增、0 删除，含 import），
  复用 `cmd_serve` 既有的 `ConfigError → rc=2` 映射（你已证该映射链成立）。**本棒禁碰 cli.py**。
- **A209（U-6）**：三个提供器保持 `config: AppConfig = Depends(get_config)` + 就地 `# noqa: B008`（镜像冻结的
  `api/deps.py`，A47 体例）。**禁**改 `Annotated[...]`（会牵动 design §1 冻结的路由签名）。

## 3. 写集（**只准**这些，逐件给 mode）

| 路径 | mode | 允许 | 禁止 |
| --- | --- | --- | --- |
| `src/campaignlab/infra/db/repositories.py` | append-only（A82/A204） | 只追加 `JobRepository.list_for_workspace` | 改既有方法/SQL/Record 字段；numstat 删除行 > 0 |
| `src/campaignlab/worker/integrity.py` | 改自己的件 | 实现 ④⑤、扩 reason 两项、**删掉那段 `.. warning::` 占位**并改写为已落地判据说明 | 改 ①②③ 与 `PATH_ESCAPE`/`UNREADABLE` 判据；改 `Discrepancy`/`ManifestRow` 字段；引入 `hashlib`（A157：只准复用 `hash_file`）；出现任何 SQL 动词字面量 |
| `tests/unit/test_worker_integrity.py` | 追加用例 | ④⑤ 的绿路径 + 五种形态各一条正向对照 | 删改 S2b-2 既有 19 条用例（只能加，用例数 19 → ≥24） |
| `evidence/M0/M0-04/s2b3-integrity-jobs.md` | 新建 | 取证：符号面/numstat/零 SQL 自检/门禁 rc | 写 AC-031 的 PASS/FAIL 结论（判定归 M5-01） |
| `evidence/M0/M0-04/positive-control-s2b3.log` | 新建 | 变异 → RED 的原始输出 + 双向复原证明 | 用工作树做探针（一律 `tmp_path`） |
| `evidence/M0/M0-04/commands-s2b3.md` | 新建 | 四元组命令表（命令/rc/关键输出/期望） | 写「人工确认」类不可复跑判据 |
| `orchestrator/handoff/M0-04-design.md` | **只在文末追加**一节 | 追加「§5:52 判据④⑤ 裁定注记（A205）」小节，写明 ⑤ 核 `jobs` 行而非制品行及其理由 | **禁改第 52 行原文**（D-011：历史文本只加注不改写）；禁动其余任何段 |

## 4. 硬禁（越界即停手回报）

`orchestrator/state.json`、`scripts/**`、`contracts/**`、`spec/**`、`migrations/**`、`web/**`、`qa-reports/**`、
`src/campaignlab/api/**`（含 `cli.py`、`app.py`、`deps.py`、`common.py`、`jobs.py`）、
`src/campaignlab/domain/**`、`src/campaignlab/application/**`、`src/campaignlab/worker/{service,store,runner,leases,capacity,states,errors,__init__}.py`、
`tests/integration/jobs/conftest.py`、`tests/unit/test_job_repository_terminal.py`（**冻结守护本体，禁改**）、
`orchestrator/handoff/M2-01-design.md` 与一切 M2-* 文件（另一条 lane 在飞）。
**禁任何 git 写操作**（`add`/`commit`/`stash`/`checkout`/`reset` 全禁）——提交权归编排器。

## 5. 自验门禁（**路径限定**，LANE-COMMON §4）

| 命令 | 期望 |
| --- | --- |
| `uv run --no-sync ruff format --check <你的 4 个 .py + 3 个 .md>` | rc=0 · `N files already formatted` |
| `uv run --no-sync ruff check <同上 .py>` | rc=0 · `All checks passed!` |
| `uv run --no-sync ruff check --select I --diff <同上 .py>` | rc=0 且 diff 为空 |
| `uv run --no-sync mypy` | rc=0（**全表**；分母 = HEAD 值 + 你的新增 .py 数。**禁**把全表分母写成硬编码数字**当判据**，只报实测值与归因，见 R13-6） |
| `uv run --no-sync pytest -q tests/unit/test_worker_integrity.py tests/unit/test_job_repository_terminal.py tests/unit/test_layering_edges.py tests/integration/jobs/` | rc=0 · 0 failed |
| `git diff --numstat HEAD -- src/campaignlab/infra/db/repositories.py` | `N 0`（**删除行必须为 0**） |
| AST 自检：`worker/**` 非 docstring 字符串常量里 SQL 动词命中数 | **0** |
| AST 自检：`integrity.py` 是否 import `hashlib` / 是否有第二个 hash 实现 | 都为**否**（A157） |
| `tests/unit/test_layering_edges.py` | 8 passed，且 `infra → worker` 反向边 == `[]`（A153） |

四个 `.py` 一律先 `ast.parse` 再跑（R12-1：写文件通道会把 `except (A, B):` 静默损坏成 `except A, B:`）；
**禁**使用 `except` 元组形式。文件一律 UTF-8 / 无 BOM / 无 CR / 尾单个 `\n` / 行宽 ≤100。

## 6. 正向对照（守护必须有牙，LANE-COMMON §6）

至少 5 条，每条都要「变异 → RED 原文 → 复原 → 双向核验（改前 sha == 复原后 sha）」：

1. 注入一条 `result_json` 为非法 JSON 的 jobs 行 → 必出 `RESULT_JSON_UNPARSEABLE`；
2. 注入一条 `result_json` 指向不存在 job id 的行 → 必出 `RESULT_REF_DANGLING`；
3. 把 `list_for_workspace` 的 `WHERE workspace_id=?` 去掉（在**副本**上） → 跨工作区串号必被判出；
4. 把 ⑤ 的实现改成恒真（`return []`）→ 对照 2 必须转红（证明判据不是 vacuous green）；
5. 往 `worker/integrity.py` 副本塞一条只读 `SELECT` 字面量 → 冻结守护必须 rc≠0（证明 A204 没被用来开后门）。

探针一律走 `tmp_path` 或内存副本，**禁**污染工作树；结束后 `git status --porcelain` 必须与开工时逐字相同
（除你写集内的件）。

## 7. Token 双上限（R13-4：**两个口径都要给结论**）

- **§5.1 单轮输入上限**：max 档 **40k**。回执必须自报单轮上下文峰值并明确「越/未越」。
- **§15.5 累计计费上限**：max 档 **200k**，判定口径 = **累计计费**（A183）。拿不到计费表就如实报
  `over_cap` 与估算依据，**禁**用「纯产出部分在上限内」这类口径把越限记成合规，禁抹平。
- 本子任务目标面很窄（一个访问器 + 两条判据 + 用例 + 证据），**预期单轮 ≤40k**；若你发现需要读
  整份 design（1628 行）或整份 repositories.py（1000+ 行）才能动手，先按本文件 §2/§3 的行号定点读，
  禁整读（这是编排器给你省 token 的主要手段）。

## 8. 回执格式（8 段，缺段判不合格）

1. `RESULT: DONE|PARTIAL|STALLED` + 一句话结论
2. 逐交付件：`numstat +/−`、bytes/lines、sha256 前 12、关键判据实取值
3. 自验命令对账表：命令 / rc 实测 / 关键输出 / 期望 / 判定（**禁**写「应该通过」）
4. 正向对照：每条的变异点 → RED 原文摘要 → 双向复原证明
5. U 项：问题 + 两个候选 + 你的倾向（**禁自行裁定**）
6. 自报 token：§5.1 与 §15.5 **两个口径分别给结论**
7. L 循环：用了几轮 / 上限 / 是否 STALLED
8. IN_FLIGHT_CONTAMINATION：工作树里不属于你写集的件（**禁修、禁计入自己的 RED**）
