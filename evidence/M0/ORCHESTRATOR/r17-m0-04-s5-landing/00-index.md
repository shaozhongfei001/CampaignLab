# R17 · M0-04/S5 入库取证索引 —— 编排器独立复验 81 项全绿 ＋ 4 项 U 终裁（A239–A242）＋ 立 D-049 ＋ 编排器同批补牙（autouse 静态哨兵）＋ 自纠 R17-3

- **时点**：2026-11-15T08:04:00+08:00　**入库前 HEAD**：`50be48f`　**分支**：`m0-framework`
- **lane**：S5 · task **M0-04**（`tests/integration/jobs/` 的 conftest 9 个 fixture ＋ 作业状态机 T1–T9 矩阵 ＋ 幂等 3 例 ＋ jobs API 7 例；**只新建 4 件**）
- **档位**：**qwen3.8-flash / medium**（design §9-S5 原文冻结，未升降档）　**critical=true、slack=0、loop 2 / 2**（用满但未硬撑第 3 轮）
- **agent_id**：`01a1dc3e-86e5-73f3-8786-003d10ada510`　**昵称**：Kierkegaard
- **回执**：`RESULT: DONE_WITH_GAP` ⇒ **编排器终裁 PASS**（GAP＝PC-4 的 [B] 步未判红，属**派单文的判红预言失真**而非交付面缺陷；已由 A241 ＋ D-049 ③ ＋ 编排器同批补牙的静态哨兵**当批闭合**，不留给下一棒）
- **口径**：一切读数由编排器实测（`rule_no_trust_handoff_summary_assertions`）；入库四门跑在**冻结索引树**上（R11-3 ＋ D-046 的 `frozen_env` 导入隔离，工装 `scripts/orch_harness.py`）。
- **命令原文与输出**：同目录 `commands-and-outputs.log`（200 行 / 16833 B / sha256[:12]=`50c69ddd6363`；含 §J 的 PREFLIGHT RED #1 自纠原文）。
- **在飞面**：本次入库时**无其它在飞 lane**（S2b-2 已于 `87c897a` 入库、`50be48f` 回填、`close_agent` 释放槽）⇒ `untracked_owner_map` 为空集，`classify_untracked` 的 outside 必须为空。

## 1. 交付面逐件实测（均为**入库前**实测值）

| 文件 | 形态 | 行 | 字节 | sha256[:12] | 用例 |
|---|---|---|---|---|---|
| `tests/integration/jobs/conftest.py` | 新建（lane） | 217 | 8509 | `90ba7b17b115` | 0（9 个 fixture） |
| `tests/integration/jobs/test_state_machine.py` | 新建（lane） | 503 | 18040 | `39e6c8423b1a` | 13（T1–T9） |
| `tests/integration/jobs/test_idempotency.py` | 新建（lane） | 154 | 5697 | `69a69d80abeb` | 3 |
| `tests/integration/jobs/test_jobs_api.py` | 新建（lane） | 300 | 11320 | `64a157a2f176` | 7 |
| `tests/unit/test_jobs_conftest_no_autouse.py` | 新建（**编排器同批补牙**，A241） | 104 | 4483 | `0f37d540f63a` | 3 |
| `orchestrator/defects/D-049.md` | 新建（本批立单） | 46 | 7003 | `49b419b3b407` | — |
| `evidence/M0/ORCHESTRATOR/r17-m0-04-s5-landing/00-index.md` | 新建（本文） | — | — | 本文自身，由驱动实测写入台账 | — |
| `evidence/M0/ORCHESTRATOR/r17-m0-04-s5-landing/commands-and-outputs.log` | 新建（取证原文） | 200 | 16833 | `50c69ddd6363` | — |

lane 的 4 件与回执自报的行/字节/sha **逐件逐字相符**（编排器独立 `wc`/`sha256sum` 复测，非采信）；4 件全部单个 `\n` 结尾、无 `\n\n`。

## 2. 编排器独立复验（81 项对撞，脚本 `.orch_tmp/v_s5.py`，**81 PASS / 0 FAIL**）

| 组 | 判据 | 实测 |
|---|---|---|
| 交付面 | 4 件行/字节/sha 与回执相符；单个尾换行形态 | 逐件相等（4 项形态断言） |
| git 面 | 4 件必须是**未跟踪**；工作树脏面 == 这 4 件（当时点） | 相等 |
| fixture 面 | conftest 的 fixture 名集与派单文 §1(:30)/§3 冻结的 **9 名双向差集为空**；`autouse` **零命中**（AST 实取，禁字符串匹配）；扫描器**非空自证**（合成 autouse 样本必须能抓到 ⇒ 判据非恒真，PRE-18） | 9 名相等、零 autouse、扫描器有牙 |
| 遮蔽面 | 既有三件各自定义的模块级 fixture 实取：`test_artifact_write.py`=`data_dir,engine,clock,store,writer,other_device`；`test_worker_deps.py`=`data_dir,db_path,engine,config,clock,store,other_device`；`test_jobs_router_s4.py`=`harness,client,ws` ⇒ 与 conftest 九名的**遮蔽交集只有 `data_dir`** | 交集 = `['data_dir']`（这是 PC-4 不红的机理，见 §4） |
| 状态机面 | `test_t1_*`…`test_t9_*` 前缀集 == t1..t9（9 个函数）；参数化 id 实测 **13** 个且覆盖 T1..T9（含 `T1-earliest-queued-first`、`T9-retry-from-failed`） | 全等 |
| 用例面 | 幂等 3 函数、API 7 函数（AST 实取函数名集）；`--collect-only` 实测 13 / 3 / 7 == **23** | 全等 |
| 红线面 | 4 件的 `sleep(` / `time.monotonic` / `datetime.now` / `utcnow` / `time.time(` / `asyncio.sleep` / `# type: ignore` **全 0 命中**；conftest 使用 `FixedClock` | 0 命中 |
| 契约面 | `ObjectKind` 成员实取 == **20**（含 `job`）；`contracts/openapi.json` 里 `submitJob` 出现 **0** 次、`cancelJob` 存在 | 见 §3 的 A239 / A242 |
| 冻结面 | `api/deps.py` `ed1075a86447`、`application/activity_service.py` `21425228694b`、`api/app.py` `f039722660bb`（S2b-2 入库后终态）、`contracts/openapi.json` `592571099d63`、`tests/unit/test_s2b2_app_injection.py` `fadf666b810d` | 5 件 sha 全等 |
| 禁改面 | `api/common.py`、`api/jobs.py`、`worker/service.py`、`worker/deps.py`、`worker/runner.py`、`pyproject.toml`、`scripts/orch_harness.py`、既有三件集成测试、`__init__.py` 的 numstat 全空 | 未改 |
| PC-6 复原 | `conftest.py` 的 `STUB_KIND: Final` 终态 == `VALIDATE_IMPORT`（lane 的 PC-6 变异复原证据） | 相等 |

**该目录全量复跑**：`pytest -q -p no:randomly tests/integration/jobs` → **88 passed**（既有 65 ＋ 新增 23）⇒ conftest 未打红任何既有用例（lane 自报的 88 经独立复核成立）。

## 3. U 项终裁（A239–A242；lane 只报不裁，编排器同批闭合）

| 编号 | lane 上报的事实（编排器已独立复核） | 终裁 | 依据 |
|---|---|---|---|
| **A239**（U-1） | N8/A89 裁定原文称 `job` 在「21 枚举」内；实测 `ObjectKind` 成员 **20** 个（含 `job`） | **以代码实测 20 为权威**；N8/A89 原文依 D-011 不改写，由 A239 ＋ D-049 ① append-only 承接。今后引用一律写「实测 20，单一真源＝`src/campaignlab/api/common.py`」，禁再复制 21 | PRE-7（以实际落地代码为准）；裁定实质（用 `kind='job'`）不受影响 |
| **A240**（U-2） | §4.3 要求 `detail` 用 **`is` 判定**；实测经 TestClient 的 JSON 往返后 `is` 恒 False ⇒ 判据与手段物理互斥 | **采纳 lane 的最强形态**：`==` 引用 import 的 `BAD_CURSOR` 常量 ＋ AST 防「同值副本」自守护（其 PC-5 实证有牙）。§4.3 口径更正为「**静态引用同一性**」——JSON 边界内唯一可判定的同一性形态 | D-048 同族（判据与落地手段互斥）；归 D-049 ② |
| **A241**（U-3） | §7 PC-4 预言「conftest 加 `autouse` ⇒ 既有三文件判红」；lane 实测两个 autouse 变体下既有 **65 例 rc=0**，如实入档不冒充通过，并以 PC-6 补替代对照 | **采纳 lane 的如实入档**；预言失真归 D-049 ③。**编排器同批补牙**：新建 `tests/unit/test_jobs_conftest_no_autouse.py`（3 例），并以 **PC-ORCH-1/2** 一次变异两项观测实证（见 §4） | PRE-18；rule_positive_control_must_prove_detection；沿 R16/A231 的「编排器同批补判据」先例 |
| **A242**（U-4） | §4.2 要求「同键同请求**体**」，但活契约 jobs 面**无创建端点**（`submitJob` 实测 0 次）⇒ lane 改以 `cancelJob` 为载体（path 参与 `request_digest`，语义等价），理由写进件 docstring | **采纳现载体**；M1 的创建端点落地后由 **FU-56** 迁移载体（P3，非 blocking）。**不属 D-049**（这是契约面尚未长出的时序问题，不是文档失真） | A214（逐字实现授权面）；活契约为单一真源 |

## 4. GAP 的当批闭合：`autouse` 禁令从「只在 docstring 里」变成「有机器判据」

派单文 §7 的 PC-4 预言不成立 ⇒ 若照信它，就等于把 `autouse` 禁令的执行托付给一个**实测不存在**的机制（日后任何人给 conftest 加 `autouse=True` 都不会判红，属静默劣化）。编排器同批补牙并**自证有牙**：

| 步 | 命令/动作 | 实测 |
|---|---|---|
| 基线 | `pytest tests/unit/test_jobs_conftest_no_autouse.py` | rc=0 · **3 passed**；conftest sha `90ba7b17b115`，9 个 fixture 的 autouse 全 False |
| [A] 变异生效 | 把 `migrated_job_db` 的 `@pytest.fixture` 改为 `@pytest.fixture(autouse=True)`（装饰器 lineno 由 AST 定位），再用同一扫描器 AST 断言 | `migrated_job_db autouse=True`，全表仅此一个 True ⇒ 变异确已生效（PRE-18：禁靠崩溃判红） |
| [B1] 哨兵 | 同上 pytest | **rc=1 · 1 failed, 2 passed** ⇒ 禁令**有牙** |
| [B2] 既有三件 | `pytest test_artifact_write.py test_worker_deps.py test_jobs_router_s4.py` | **rc=0 · 65 passed** ⇒ lane 的 PC-4 GAP 自报**属实**（预言确实不成立） |
| [C] 复原 | 字节级还原备份 | sha256[:12] = `90ba7b17b115` == 入库前实测值 ⇒ **变异零残留** |
| [D] 复跑 | 同基线命令 | rc=0 · 3 passed |

`VERDICT: sentinel_has_teeth=True existing_still_green=True restored=True => PASS`（原文见 cmdlog §F）。
「哨兵有牙」与「既有件不红」两件事**同时成立**，这正是 D-049 ③ 的完整证据链：既有件不红是 pytest 遮蔽语义的必然结果，不是 lane 的失误；因此禁令必须靠**静态哨兵**而非「既有件会红」来执行。

## 5. 四门口径与 EXPECT（权威读数＝冻结索引树实测，与 EXPECT 逐条相等才允许提交）

- EXPECT：`ruff_formatted_files=301`（109 py ＋ 192 md）、`mypy_source_files=107`、`pytest_passed=734`（冻结树实跑 713 ＋ GIT_ENV_IGNORES 静态收集 21）、`in_scope_py=109`、`in_scope_md=192`。
- 换算：入库前基线 294（104 py ＋ 190 md）/ 102 / 708 ＋ lane 4 件 .py ＋ 编排器哨兵 1 件 .py ＋ `D-049.md` ＋ 本取证索引 .md ⇒ py 109、md 192、ruff 301、mypy 107、pytest 708+23+3=734。`commands-and-outputs.log` 为 `.log` 后缀不入 ruff 分母。
- lane 自报的 298 / 106 / 731 是**活动树**口径（含当时在飞的 S2b-2 两件），lane 已在回执 §8 自行标明「回收对账请用派单快照＋在飞台账，而非本棒自报」⇒ 编排器复核认可，不作为判据。
- 任一不符 ⇒ `git reset` ＋ 台账 `checkout` 回滚、HEAD 不动、不留半成品。

## 6. flash_share 重算与两项护栏的如实上报

- 口径**先反向验证可复现**：以现值 44 条 `subtask_log`（计 43 条，排除 1 条 `orchestrator-self-served`）重算得 tasks=0.5472 / dev=0.3226 / tokens=0.6655，与账本三项**逐位相等**（cmdlog §I）。
- 本棒入库后（+1 条 flash、dev lane、`tokens=null`＋`tokens_estimated=true` ⇒ 不入 tokens 分母）：units 53→**54**、flash 29→**30** ⇒ `flash_share_tasks=30/54≈**0.5556**`；dev units 31→**32**、dev flash 10→**11** ⇒ `flash_share_dev_lanes=11/32≈**0.3438**`；`flash_share_tokens` 保持 **0.6655**。
- **交叉验证**：这与 A234 在派单时点给出的预测（「Round 17 两条 lane 均为 flash ⇒ 30/54≈0.5556、11/32≈0.3438、tokens 保持 0.6655」）**逐位相符** ⇒ 记账口径在两批之间未漂移。
- **护栏①（tasks ≥0.60）仍未达标**：0.5556 < 0.60，但连续第 3 棒靠 flash 抬升分子（0.5385→0.5472→0.5556）；剩余量产面 M0-04 的 S6/S8 ＋ M2-01 的 S3–S7 全为 flash（≥7 棒），若如期交付则 units ≈ 37/61 ≈ 0.607 ⇒ 可回达标。
- **护栏②（tokens ≤0.35）仍未达标**：0.6655 > 0.35。本棒 tokens 为区间估算（lane 自报 150k–220k，拒编精确数）⇒ 记 null+estimated、不入分母；成因是 max 棒单棒过贵 ＋ flash 棒单轮输入超限，纠正面＝派单文瘦身（R16-6）＋ 预抽摘要（PRE-15）＋ PRE-19（检索命令限定路径/输出上限/排除散文面），**不是降档**。
- 两项一律如实上报、不粉饰、不为凑配比改判（手册 §6.6）。

## 7. 悬空引用与未跟踪件归属

- `dangling_refs` 由驱动在 add_paths **全集**（8 件，含本文与 D-049.md）上实扫（PRE-17），驱动内做**集合相等**断言（多登记与少登记同样判红）。本文与 D-049.md 刻意只引用磁盘上已存在的路径 ⇒ 预期悬空 **0** 条、`allow_dangling=()`。
- 特别地：M0-04 的任务级取证面（AC-029 / AC-031 的判定与证据指针、任务级摘要）归 **S8** 产出，本文**不引其路径**，以免新增前向引用；R16-S2b1 批已登记的 2 条 M0-04 侧前瞻悬空引用仍在 `resume.forward_reference_registry` 里等 S8 闭合（条目保留不删）。
- `untracked_owner_map = {}`：本次无其它在飞 lane；本棒 5 件 .py ＋ D-049.md ＋ 取证 2 件全在 add_paths 内 ⇒ 未跟踪面必须为空集。

## 8. 未尽面（如实登记，不含糊）

- `stub_handler` 的 `JobOutcome` 交回 runner 的**端到端**链路（`WorkerRunner.execute` 全链）不在本棒契约（design §9-S5 未列）⇒ 未取证。lane 已明示其 `registry_with_stub` / `stub_handler` 可直接复用；若编排器判定需要 runner 级取证，归 **S6/S8**（不属本棒失败）。
- M0-04 的 AC-029 / AC-031 判定归 **S8**（AC-031 只写「写入侧前提已交付＋判定归 M5-01」，禁写 PASS/FAIL）⇒ 本棒不产出 `evidence/M0/M0-04/**`。
- **M0-04 全链 S5→S6→S8 闭合前禁判 DONE、禁开 wave3**（它是 21 个 TODO 任务的唯一解锁点）。S6 依赖 S5 的 conftest fixture 面 ⇒ 必须在**本提交入库之后**才派（同目录 N4 禁双主写）。
- lane 自报的 loop 2 轮里修的问题（FK 前置缺失×13、`Problem.issues` 必填×2、claim 键序×2、容量计数×1；第 2 轮的 mypy 2 错 ＋ T3 推进量缺失 ＋ T5 桩执行链路补强）已由终态 23 例全绿与 88 passed 覆盖 ⇒ 不再单独取证，如实记录其自报口径。

## 9. 自纠（append-only，原文不改写）

- **R17-3（编排器工具口径）**：编排器第 1 次执行复验脚本时误用**系统 python3（3.12）**，在 `ast.parse('src/campaignlab/api/common.py')` 处崩溃（`except ValueError, binascii.Error:` 是 PEP 758 的 3.14 语法，3.12 无法解析）。纠正＝复验/探针脚本一律用 `uv run --no-sync python`（仓库 `.venv` 的 3.14）执行；立 **PRE-21** 固化该口径。该次崩溃**零副作用**（§8 之前只做只读实测，未写任何文件），修正后 81 项全绿。
- 与前两条同批：R17-1（PC 复原基准 sha 的时点口径）、R17-2（无界 grep ⇒ PRE-19）见 `resume.round17_self_corrections`。
- **R17-4（编排器驱动断言口径）**：入库驱动 preflight §8 的「未跟踪件归属」断言把期望集写成 add_paths **全集**（8 件），而 `classify_untracked()` 只在 **in-scope**（`.py`/`.md`，`RUFF_SUFFIXES`）范围内分类 ⇒ `.log` 取证件本就不在 `outside` 里，该断言必然判红。第 1 次 `--preflight-only` 实测 **RC=1、仅 1 项判红、零副作用**（只读：HEAD 仍 `50be48f`、`git status` 仍 7 件未跟踪、台账未改动、`run_commit` 未被调用）。纠正＝期望集改用**同一过滤条件**构造（7 件），并同批加两条自证断言（in-scope 子集恰为 7 件 ＋ `.log` 确实被排除，若哪天进了 outside 即判红 ⇒ 判据非恒真）；立 **PRE-22** 固化「期望集必须与被调判据同口径（先读其过滤条件）」。原文见 cmdlog **§J**。**如实入档，禁粉饰为一次通过。**
