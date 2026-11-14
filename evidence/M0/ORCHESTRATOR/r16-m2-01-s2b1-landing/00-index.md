# R16 · M2-01/S2b-1 入库取证索引 —— 编排器独立复验 ＋ U 项终裁 ＋ 前提哨兵迁移（D-047 同族第三例）

- **时点**：2026-11-15T06:20:00+08:00　**入库前 HEAD**：`fe9e4ce`　**分支**：`m0-framework`
- **lane**：S2b-1 · task **M2-01**（活动/规则版本的应用层 ＋ 仓储层 ＋ 端口面）· 档位 **qwen3.8-max / high**（design §11.3 冻结，未升降档）
- **agent_id**：`01a1db55-3aec-7093-9f55-785932c63478`　**昵称**：Hooke　**loop**：2 / 3（critical=false, slack=4，未触发 STALLED）
- **回执**：`RESULT: PARTIAL`（本棒交付面全绿，1 条红落在无写权的既有哨兵上、1 条红归编排器在飞件）⇒ **编排器终裁 PASS**（3 项 U 全部同批闭合，见 §3）
- **口径**：一切读数由编排器实测（`rule_no_trust_handoff_summary_assertions`：禁采信自报）；入库四门一律跑在**冻结索引树**上（R11-3 ＋ D-046 的 `frozen_env` 导入隔离）。
- **命令原文与输出**：见同目录 `commands-and-outputs.log`（206 行 / 14904 B / sha256[:12]=`3d1fb4582839`）。

## 1. 交付面逐件实测（行 / 字节 / sha256[:12]，均为**入库前**实测；口径见 §6.1 与 R16-8）

| 文件 | 形态 | numstat | 行 | 字节 | sha256[:12] |
|---|---|---|---|---|---|
| `src/campaignlab/application/activity_service.py` | 新建（主交付） | 1999/0 | 1999 | 88950 | `21425228694b` |
| `src/campaignlab/infra/db/repositories.py` | 修改（A82 纯追加） | **830/0** | 1884 | 82850 | `23437663c59e` |
| `src/campaignlab/api/deps.py` | 修改（纯追加） | **175/0** | 346 | 13524 | `ed1075a86447` |
| `tests/unit/test_s2b_activity_surface.py` | 新建（16 例） | 605/0 | 605 | 24342 | `a64e4e8eb52a` |
| `tests/unit/test_s2b_activity_repositories.py` | 新建（16 例） | 682/0 | 682 | 28889 | `e57e7467d6be` |
| `tests/unit/test_s2b_activity_service.py` | 新建（15 例） | 1163/0 | 1163 | 48080 | `d99a137c498e` |
| `tests/unit/test_job_repository_terminal.py` | **编排器**迁移哨兵（A231） | 56/13 | 819 | 34134 | `794271b41609` |
| `orchestrator/handoff/M2-01-design.md` | 修改（A214 文末追加 §14） | **74/0** | 1396 | 153979 | `2d39feaac2d1` |
| `orchestrator/defects/D-048.md` | 新建（本批立单） | 61/0 | 61 | 5154 | `46df6b26bb47` |

迁移前基线（供复原核验）：`test_job_repository_terminal.py` 776 行 / 31538 B / `60c291480568`；
`M2-01-design.md` 1322 行 / 146775 B / `6f40846a1d66`（前 1322 行拼接 sha256[:12]=`518dca08c795`，追加后**逐字节相同**）。

## 2. 编排器独立复验结论（24 项，脚本 `.orch_tmp/v_s2b1.py`，全部 PASS）

| 判据 | 期望（派单文 / design §11.3） | 编排器实测 | 结论 |
|---|---|---|---|
| 6 件交付面的行/字节/sha | 与回执逐字相符 | 6/6 全等 | ✅ |
| `repositories.py` / `api/deps.py` 纯追加 | `numstat` deleted=0（A82） | 830/**0** · 175/**0** | ✅ |
| 硬禁面零改动 | `api/app.py`、`api/common.py`、`domain/**`、`worker/**`、`orchestrator/**`、`scripts/**`、`contracts/**`、`pyproject.toml` | `git status` 面**恰为** S2b-1 的 6 件；上述路径 `git diff --numstat` 全空 | ✅ |
| `repos.__all__` | 既有 10 名在位且相对顺序不变；差集恰为授权 6 名 | 16 名；`kept == FROZEN10` 逐字相等；差集恰 `{ActivityBindingRepository, ActivityRecord, ActivityRepository, BindingRecord, RuleVersionRecord, RuleVersionRepository}` | ✅ |
| `deps.__all__` | 既有 9 名在位且相对顺序不变；差集恰 4 名 | 13 名；既有面（HEAD 实取 9 名）逐字相等；差集恰 `{ActivityService, RuleService, get_activity_service, get_rule_service}` | ✅ |
| 端口 vs 实现（A115 集合对撞，禁计数） | `deps.ActivityService` / `deps.RuleService` 的公开方法面 == 实现类 | 双向差集均为 ∅（`inspect` 实取） | ✅ |
| `api/common.PROBLEM_CODES` / `DomainError` 子类 | 20 / 14 禁改（design §11.2 零新增） | 20 / 14 | ✅ |
| `api/common.__all__` | 79 禁改（S4 已落地 `JobPage`） | 79 | ✅ |
| `deps` 模块级私有函数 | 恰 1 个（`_state_service`，A206 复用） | `['_state_service']`（AST 实取） | ✅ |
| `activity_service.py` 的 SQL 写点 | ∅（A81：三张表的 DML 文本只允许出现在 `repositories.py`） | `text(` / `UPDATE` / `INSERT INTO` / `DELETE FROM` / `import sqlalchemy` **0 命中**；同一扫描器在 `repositories.py` 上**非空**（反向自证非空断言） | ✅ |
| 墙钟 / sleep 字面量 | ∅（红线 3 / D-045），含注释与 docstring | 三件 src 交付面 0 命中 | ✅ |
| 禁第二把密钥 / 第二句 detail | 复用 `workspace_service` 的 `load_cursor_secret` / `BAD_CURSOR_DETAIL` / `audit_role_of` | 三者 `is` 判定均为 **True**（同一对象，非同值副本） | ✅ |
| `activity_service.__all__` | design §11.3 第一条的 26 名逐字 | 实取 **26** 名，与 §11.3 清单逐字对撞相符（8 个 `ACTION_*` ＋ 2 个 `TARGET_KIND_*` ＋ 2 个 `*_ID_PREFIX` ＋ 6 个 `*_DETAIL` ＋ 3 个 `*Outcome` ＋ 2 个 service 类 ＋ `ACTIVITIES_CURSOR_VERSION` ＋ 2 个 `*_query_digest`） | ✅ |
| Repository 方法面 | `ActivityRepository` 8 · `ActivityBindingRepository` 4 · `RuleVersionRepository` 7 | lane 报 8/4/7；编排器另以 §11.3 的符号清单逐名 `hasattr` 复核 | ✅ |
| 新增用例数 | — | `--collect-only` 实测 **47**（16+16+15） | ✅ |
| 迁移后守护的用例数 | 不变 | `test_job_repository_terminal.py` 迁移前后均 **24** 例 | ✅ |
| `mypy` | rc=0 | `Success: no issues found in 101 source files`（95+2 S4 +4 本棒） | ✅ |

**归因说明（PRE-11 / A223）**：lane 回执报的活动树读数 `ruff format 288` / `mypy 101` / `pytest 2 failed, 697 passed`
**不是入库读数** —— 分母含当时尚未入库的 S4 件与编排器件；2 条红里 ①
`test_job_repository_terminal::test_repositories_module_all_is_unchanged` 是本批迁移的前提哨兵（§3 A231），
② `test_state_ledger::test_every_md_on_disk_has_ledger_entry`（报 `['D-047']`）是**编排器在飞件**造成的，
已随 `c39b17e` 把 D-047 登账而自动消解（本批复测该文件 rc=0）。入库四门以 `run_commit` 的冻结索引树读数为准，见 §5。

## 3. U 项终裁（lane 只报不裁；编排器逐条终裁，A231–A233）

| U | 事实 | 终裁 | 依据 |
|---|---|---|---|
| **U-1** | §1.2/§11.3 授权 `repositories.__all__` 10→16，既有哨兵 `test_repositories_module_all_is_unchanged` 硬断言「== 10 项字面量」⇒ 必红；该文件既不在 §4 白名单（第 4 项只给 `tests/**` 的**新建**文件）也不在 §1.4 禁改清单 ⇒ lane 无写权，未修未削弱 | **A231 采纳候选 (a) 编排器同批迁移**（与 A226 对 lane S4 两条哨兵的处置完全同型）。迁移形态＝「字面量相等 → 结构级对撞」：既有 10 名在位**且相对顺序不变** ∧ 差集恰为授权 6 名 ∧ `denominator=0` 断言 ∧ 无重复名。函数名本批不改（归 FU-52）。同批在 design §14.1 追记，供 S3–S7 直接引用 | A226 / A224（同批纪律）/ A82 / A115 / D-047 / PRE-14 |
| **U-2** | §11.3 的一般规则「所有写 UPDATE 的 WHERE 必须含 guard 镜像」与 §3.2 给 `set_current_rule` 的 **SQL 原文**（谓词只有 `workspace_id=:ws AND id=:activity_id`）矛盾；且 §3.2 明文「禁先 SELECT 后 UPDATE 的裸检查」⇒ 补 guard 需先读活动行，物理上不可同时满足 | **A232 采纳「维持 §3.2 原文」（specific 覆盖 general），零代码改动**；同批立 **D-048** 记该设计文档缺陷，并在 design §14.2 追记三条理由 ＋ 残留风险（`current_rule_id` 绝对赋值在并发确认下可能被后到者覆盖）⇒ 立 **FU-54** 交 M2-01/S6 钉成用例 | A214（逐字实现 design 原文）/ §3.2 的禁裸检查 / D-011（只加注不改写）/ D-043 同族 |
| **U-3** | §11.3「`api/deps.py` 纯追加（deleted=0）」与派单文 §1.3「既有 import 行只允许追加名字」在 ruff `I001` 下字面不可同时满足（新 Protocol 需 11 个 `api.common` DTO ＋ 3 个 `activity_service` Outcome） | **A233 采纳 lane 已落地的形态**：新增 1 行 `import typing` ＋ 1 个 `if typing.TYPE_CHECKING:` 块，既有 import 行一字未动。理由：`from __future__ import annotations` 使注解运行期不求值 ⇒ 既满足 mypy strict 又零运行期成本，且**降低**运行期耦合；候选 (b) 与 (a) 在功能/类型安全/四门读数上完全等价，唯一收益是风格同型性，为此重派一整棒 max（lane 自报累计 ≈3.4M token）违反成本纪律。design §14.3 追记，并明确 S3/S4 **不需**照抄此形态（它们在运行期真的需要 DTO） | A82 / A214 / 成本纪律（手册 §6.6）/ 分层红线 |

**编排器自纠（如实入账）**

- **R16-9**：编排器为迁移后的哨兵做「判据自证」对照（PC-5）时，第一版把变异写成
  `_REPOS_ALL_FROZEN_10 = [] or [...]` —— 因 Python 的 `or` 对空 list 返回**右操作数**，
  该文件字节 sha 确实变了（`794271b41609` → `60ab5fc1ca92`），但 AST 实取的常量值**仍是原 10 名**，
  语义未生效 ⇒ rc=0 **假绿**。驱动当场以 `assert rc != 0` 拦下并崩出，随后字节级复原（sha 回到 `794271b41609`）。
  这是 **R16-4 同一教训的第二次出现**（R16-4：PC-C 的变异路径被 `APIRouter(prefix=...)` 再补一次前缀 ⇒ 撞不上 ⇒ 假绿）。
  防再发（并入 PRE-14 的执行细则，记 **PRE-18**）：**每条阳性对照在跑判据之前，必须先用 AST／运行期实取被改对象的
  新值并断言它确实等于预期的变异后形态**；「文件 sha 变了」不构成「变异生效」的证明，
  「删掉断言」更永远不构成「判据有牙」的证明。第 2 版驱动的 5 条对照全部先过语义断言再跑，原文见 `commands-and-outputs.log` §6。

## 4. 阳性对照（第 2 版；每条先过 AST 语义断言，再跑判据，再字节级双向复原）

| 编号 | 变异对象 | 变异 | 语义断言（变异确实生效） | 期望 | 实测 | 复原核验 |
|---|---|---|---|---|---|---|
| PC-A | — | 迁移后基线 | — | 绿 | **rc=0 · 1 passed** | — |
| PC-1 | `repositories.py` 的 `__all__` | 删掉既有名 `job_from_row` | AST 实取 15 名 | 红（冻结面缺一名） | **rc=1 FAILED** | `23437663c59e` sha＋AST 双向相等 |
| PC-2 | 同上 | 交换 `ArtifactRecord` / `ArtifactRepository` 先后 | AST 实取顺序已换 | 红（**集合相同**，计数型判据抓不到，只有顺序对撞能抓） | **rc=1 FAILED** | 同上 |
| PC-3 | 同上 | 追加未授权名 `RogueRepository` | AST 实取 17 名 | 红（超出 §11.3 授权面） | **rc=1 FAILED** | 同上 |
| PC-4 | 同上 | 删掉授权名 `BindingRecord` | AST 实取 15 名 | 红（授权面少一名） | **rc=1 FAILED** | 同上 |
| PC-5 | **守护自身** | 把 `_REPOS_ALL_FROZEN_10` **真的**置空（`: list[str] = []`） | AST 实取 `[]` | 红（`denominator=0` 断言不是死代码） | **rc=1 FAILED** | `794271b41609` sha＋AST 双向相等 |
| PC-D | — | 全部复原后复跑（守护全量 ＋ 本棒 3 个新测试文件） | — | 绿 | **rc=0 · 71 passed** | 末态 sha 与基线逐字相等 |

第 1 版 PC-5 的假绿已如实留痕（§3 的 R16-9 与 `commands-and-outputs.log` §6 开头段），不抹平、不删档。

## 5. 入库四门（冻结索引树；`run_commit` 的实测值见提交台账 `counts`）

预测值（编排器静态推算 ＋ 活动树实测归因；`run_commit` 会用冻结树实测值逐条对账，不符即 `git reset` ＋
`git checkout -- orchestrator/state.json` 回滚并拒绝提交）：

- `ruff_formatted_files` **290** ＝ 103 in-scope py ＋ 187 in-scope md
  （py +4：`activity_service.py` 与 3 个新测试文件；md +2：`D-048.md` 与本索引；`.log` 不入 ruff 分母）
- `ruff check` clean（活动树实测 `All checks passed!`）
- `mypy_source_files` **101**（97 + 4 个新 .py；活动树实测已是 101）
- `pytest_passed` **699** ＝ 652（`c39b17e` 基线）＋ 47（本棒新守护）；
  迁移后的哨兵用例数不变（24 → 24），`GIT_ENV_IGNORES` 两件（`test_config.py` / `test_counts_freshness.py`）本批未触碰 ⇒ 静态补数不变（21）

## 6. 悬空引用（PRE-17：由入库驱动在 `add_paths` **全集（含本索引自身）**上实扫 `dangling_refs`）

`orchestrator/handoff/M2-01-design.md` 的 4 条**前瞻引用**（§11.8 / §10 的 S7 证据落点，HEAD 版已含、非本批新增）：
`evidence/M2/M2-01/`、`evidence/M2/M2-01/clauses.md`、`evidence/M2/M2-01/gates/`、`evidence/M2/summaries/M2-01.md`；
外加本索引 §6 为逐条判定而**原文引用**这 4 个目标所产生的 4 条**自指**镜像（R16-7 的同型产物）。
全部逐条登记 `allow_dangling`，驱动内做**集合相等**断言（多登记同样判红）；
依 `rule_forward_ref_allowlist_is_explicit_per_commit`，**禁改写文本规避扫描**。
8 条在 M2-01/S7 入库时自动消解。本索引对 `M2-01-design.md` 的引用（§14.1 处）**不构成**悬空：该文件本批同入库。

### 6.1 sha 口径（R16-8）

§1 表内 sha 一律为**入库前**实测。`run_commit` 第 1 步的 `normalize_file` 可能给文本件补尾换行
（`TRAILING_NL_ADDED`），使**入库后** sha 相差 1 字节；凡发生者由入库提交在台账里**双录** pre/post
（体例＝`resume.round16_lane_S4_return.post_commit_sha256_normalization`）。本批 9 件的入库后 sha 由回填提交复测登记。

## 7. 本批未做 / 收口去向（如实上报）

- **FU-54（新立）**：并发确认同一活动的两个后继规则版本时，`activities.current_rule_id` 是否仍等于 §3.2 定义的
  「`confirmed_at` 最大者（并列时 `id` 字典序最大）」—— 必须由 M2-01/S6（`tests/api/activities/**`）钉成用例；
  若真实并发下判红，再立缺陷走 CR（A232 的残留风险面）。
- `test_repositories_module_all_is_unchanged` 的**改名**与 docstring 语义升级 ⇒ 并入 **FU-52**（与 R16 迁移的另两条哨兵同批）。
- 哨兵登记表 ＋ 派单文自动生成「预期红清单」的机器化 ⇒ **FU-53**（本批是 D-047 之后**第三例**，密度已在上升，优先级建议由 P2 提为 P1）。
- lane 自报 token 超限（单轮 ≈115k > max 档 40k；累计 ≈3.4M > 200k）：如实入账为 `over_cap`，
  **不入** `flash_share_tokens` 分母（`tokens=null` + `tokens_estimated=true`，A183）；不降档、不重派（磁盘产出完整且已逐条独立实测）。
- M2-01 剩余：**S2b-2**（max，`api/app.py` ≤6 行挂载两个 service；S4 已入库 ⇒ `app.py` 锁已释放，**解锁成立**）→ S3 → S4 → S5 → S6 → S7。
- **M0-04 仍是 21 个 TODO 任务的唯一解锁点**：剩余 S5→S6→S8（全 flash），全链闭合前禁判 M0-04 DONE、禁开 wave3。
