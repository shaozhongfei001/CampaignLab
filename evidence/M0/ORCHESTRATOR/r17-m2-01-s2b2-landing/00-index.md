# R17 · M2-01/S2b-2 入库取证索引 —— 编排器独立复验 49 项全绿 ＋ 4 项 U 终裁（A235–A238）＋ 2 项自纠（R17-1 / R17-2）

- **时点**：2026-11-15T07:21:20+08:00　**入库前 HEAD**：`641551c`　**分支**：`m0-framework`
- **lane**：S2b-2 · task **M2-01**（`api/app.py` 追加 `activity_service` / `rule_service` 两个可注入形参 ＋ 两组条件装配；**不含 include_router**，A217 ③ 下放给 S3/S4）
- **档位**：**qwen3.8-flash / medium**（A234 依实测复杂度自 max/high 降档，附升档回路；lane 回执 §7 明确「零设计裁量、不要求升档」⇒ 降档前提未被打破）
- **agent_id**：`01a1dc3f-4619-7492-8be3-0cb3078c3e8a`　**昵称**：Mendel　**loop**：1 / 2（critical=false、slack=3，未触发 STALLED）
- **回执**：`RESULT: DONE` ⇒ **编排器终裁 PASS**（4 项 U 全部同批闭合，见 §3；禁采信任何自报读数，一切以本文实测为准）
- **口径**：入库四门一律跑在**冻结索引树**上（R11-3 ＋ D-046 的 `frozen_env` 导入隔离，工装 `scripts/orch_harness.py`）。
- **命令原文与输出**：同目录 `commands-and-outputs.log`（184 行 / 10860 B / sha256[:12]=`156cdf38fca3`）。
- **在飞邻居**：lane S5（M0-04/S5 · Kierkegaard · critical=true）此刻仍在飞，其 4 个未跟踪件由 `untracked_owner_map` 按前缀 `tests/integration/jobs/` 归属（A144(c)）；门禁取数只来自冻结索引树 ⇒ 在飞件既不入分母也不判红（PRE-12 已降级，禁泊出＝摧毁 lane 产出）。

## 1. 交付面逐件实测（均为**入库前**实测值）

| 文件 | 形态 | numstat | 行 | 字节 | sha256[:12] |
|---|---|---|---|---|---|
| `src/campaignlab/api/app.py` | 修改（160→172 行） | **14/2**（上限 added≤16 / deleted≤2） | 172 | 7576 | `f039722660bb` |
| `tests/unit/test_s2b2_app_injection.py` | 新建（9 例 G1–G9） | 363/0 | 363 | 14545 | `fadf666b810d` |
| `evidence/M0/ORCHESTRATOR/r17-m2-01-s2b2-landing/00-index.md` | 新建（本文） | — | — | — | 本文自身，由驱动实测写入台账 |
| `evidence/M0/ORCHESTRATOR/r17-m2-01-s2b2-landing/commands-and-outputs.log` | 新建（取证原文） | — | 184 | 10860 | `156cdf38fca3` |

被删的 2 行经 `git diff -U0` 逐行核对，恰为派单文 §2.1 / §3.1 授权的两行（`deps` 的 import 折行 ＋ docstring 里陈述形参个数的那一句），**无第三处删除**；numstat 在上限之内。

## 2. 编排器独立复验（49 项对撞，脚本 `.orch_tmp/v_s2b2_fix.py`，结果 **49 PASS / 0 FAIL**）

| 组 | 判据（期望来自派单文 §2/§3/§5 与 `orchestrator/handoff/M2-01-design.md`） | 实测 | 项数 |
|---|---|---|---|
| 交付面 | app.py 172 行 / 7576 B / `f039722660bb`；新守护 363 行 / 14545 B / `fadf666b810d` | 逐件相等 | 6 |
| 写权面 | numstat 14/2；被删行集合 ⊆ 授权 2 行；删除计数 == 2 | 相等 | 3 |
| 硬禁面 | `api/deps.py` `ed1075a86447`、`application/activity_service.py` `21425228694b`、`tests/unit/test_s3b_routes.py` `b0122388342a`、`tests/unit/test_api_app.py` `a97c32a63756`、`tests/unit/test_s3d_application.py` `dca0657b8b18` | 5 件 sha 全等 | 5 |
| 契约面 | `contracts/openapi.json` numstat 为空 ＋ sha256[:12]==`592571099d63` | 未改 | 2 |
| 禁改面 | `api/common.py`、`api/jobs.py`、`worker/service.py`、`worker/deps.py`、`pyproject.toml`、`scripts/orch_harness.py` numstat 全空 | 未改 | 6 |
| 工作树面 | `git status` 脏面 == 本棒 2 件 ＋ S5 在飞件（前缀 `tests/integration/jobs/`），无第三类 | 相等 | 1 |
| 符号面 | posonly+args==`[config]`；kwonly **有序** 7 名且末两位为 `activity_service, rule_service`；8 个 kwonly 默认值全 `None`；解析后注解与 `deps.ActivityService` / `deps.RuleService` **身份对撞**（非字面量）；`app.__all__` 与 4 名冻结集异或为 ∅ | 全等 | 5 |
| 挂载面 | `include_router` AST 调用点 == 4 且源码行 == 4、含 `jobs` 恰 1；`campaignlab.api.activities` / `…rules` 未出现在 import 集合；新增 import == 0 | 全等 | 4 |
| 中间件面 | `add_middleware` == 2（有序 `BaseHTTPMiddleware, CORSMiddleware`）且两处 lineno 均早于 `install_error_handlers(app)`；`openapi_url=docs_url=redoc_url=None` 未动；`ALLOWED_METHODS` 7 元组 / `ALLOWED_HEADERS` 5 元组逐字相等 | 全等 | 5 |
| 装配面 | `app.state` 赋值行 6→**8**；条件装配 AST 字典的键 == `deps.py` 提供器读取的 attribute（双向对撞：`get_activity_service`→`activity_service`、`get_rule_service`→`rule_service`）；形参名 == state 键 == 赋值变量（三位一体） | 全等 | 5 |
| 新守护 | `--collect-only` 实测 **9** 例；AST 实取 9 个 `test_` 函数（G1–G9）；`time.sleep` / `time.monotonic()` / `datetime.now()` / `utcnow` / `# type: ignore` 在新件里 0 命中；app.py 的 `# type: ignore` 计数与 HEAD 版相等 | 全等 | 7 |

合计 49 项。用例名（AST 实取，非自报）：`test_g1_signature_is_the_frozen_injection_surface`、`test_g2_both_new_services_are_attached_by_identity`、`test_g3_bare_app_assembles_neither_new_slot`、`test_g4_the_two_new_slots_are_independent`、`test_g5_existing_assembly_and_openapi_face_untouched`、`test_g6_mount_and_middleware_surface_unchanged`、`test_g7_public_surface_and_cors_constants_unchanged`、`test_g8_provider_keys_match_and_health_chain_works`、`test_g9_unassembled_services_still_yield_500_problem`。

阳性对照（lane 4 条 PC，编排器逐条复核其**复原证据**）：PC-1 无条件装配 → G3 红；PC-2 两个 `if` 合并成 `and` → G4 红；PC-3 多挂一条 router（调用点 5）→ G6 红；PC-4 注解换 `object` → G1 红。四条复原后 sha 均为 `f039722660bb`（与本文 §1 的入库前实测值逐字相等）⇒ **变异零残留**，编排器以同一 sha 独立对撞确认。

## 3. U 项终裁（A235–A238；lane 只报不裁，编排器同批闭合，不留给下一棒）

| 编号 | lane 上报的事实 | 终裁 | 依据 |
|---|---|---|---|
| **A235**（U-1） | 派单文 §7③ 要求 PC 后「复原到 `110751903e4d`」，而那是**入库前**的冻结面读数；本棒落地态是 `f039722660bb` | **采纳 lane 的选择**：复原基准＝落地态（PC 前备份、PC 后逐条 sha 相等）。照字面回到 `110751903e4d` 等于撤销本棒交付，与 §3 写权面自相矛盾 | PC 的价值在证明判据能抓变异，不在回滚交付；派单文 sha 属 PRE-15 口径下的「派单时点快照」，交付后必然失真 ⇒ 缺陷在**立法面**，同批立自纠 R17-1 |
| **A236**（U-2） | lane 自报越界嫌疑：授权的 docstring 那一行里含两处计数，除「六个→八个」外同手把同行的「三个用例服务→五个用例服务」也订正了 | **保留**。仍是同一行（numstat 不变，编排器实测仍 14/2），未扩写权面；若只改一处，文档与「8 形参 / 5 个服务槽」自相矛盾（D-012 同族），会被后续哨兵判红 | lane 主动自报（宁报勿藏）⇒ 记 `honesty` 加分、不记违规；A214（逐字实现授权面）＋ D-012 |
| **A237**（U-3） | 成员面/注解取值用 `typing.get_protocol_members` ＋ `inspect.signature(eval_str=True)`（3.14 public API），而非既有体例的 `__protocol_attrs__` | **保留 public API**。`requires-python >=3.14,<3.15` 下两者皆 public；`__protocol_attrs__` 是 CPython 实现细节、跨版本无契约保证，依赖它会让守护在解释器升级时**静默失效** | 判据强度不减（解析后注解做身份对撞，本文 §2 已独立复验）；体例不统一属风格分叉 ⇒ 立 **FU-55**（P3，非 blocking） |
| **A238**（U-4） | PC-3 的变异点：派单文建议「文件末尾追加」，但那会落在 `return app` 之后、import 期即 `NameError` ⇒ 判据红是**崩溃**而非断言命中（假阳性取证）。lane 改为在 `create_app` 内 `jobs` 挂载之后插入合法一行 | **保留 lane 的做法**。先以 AST 断言「调用点=5」证明变异生效，再跑 G6 判红 ⇒ 因果链干净；落地态调用点回到 4（本文 §2 独立复验） | PRE-18（每条阳性对照先过 AST/运行期语义断言再跑判据）；同批给 PRE-18 追加注记「变异点必须是语义合法位置，禁靠崩溃判红」 |

## 4. 四门口径与 EXPECT（权威读数＝冻结索引树实测，与 EXPECT 逐条相等才允许提交）

- EXPECT：`ruff_formatted_files=294`（104 py ＋ 190 md）、`mypy_source_files=102`、`pytest_passed=708`（冻结树实跑 687 ＋ GIT_ENV_IGNORES 静态收集 21）、`in_scope_py=104`、`in_scope_md=190`。
- 相对入库前基线（292 / 101 / 699，103 py ＋ 189 md）：+1 py（新守护）、+1 md（本取证索引；`.log` 不在 ruff 作用域，不计入分母）、mypy +1、pytest +9。
- lane 自报的 293 / 102 / 708 **不含**编排器的取证索引 .md ⇒ 差 1 属预期，不是失真（口径差异已在派单文 §5 明示：lane 不产出 `evidence/**`）。
- 任一不符 ⇒ `git reset` ＋ 台账 `checkout` 回滚、HEAD 不动、不留半成品（`run_commit` 的既有语义）。

## 5. flash_share 重算与两项护栏的如实上报

- 口径**先反向验证可复现**：以现值 43 条 `subtask_log`（计 42 条，排除 1 条 `orchestrator-self-served`）重算得 tasks=0.5385 / tokens=0.6655 / dev=0.3000，与账本三项逐位相等（见 cmdlog §H）。
- 本棒入库后（+1 条 flash、`tokens=null` ＋ `tokens_estimated=true` ⇒ 不入 tokens 分母）：units 52→**53**、flash 28→**29** ⇒ `flash_share_tasks=29/53≈0.5472`；dev units 30→**31**、dev flash 9→**10** ⇒ `flash_share_dev_lanes=10/31≈0.3226`；`flash_share_tokens` 保持 **0.6655**。
- **护栏①（tasks ≥0.60）未达标**：0.5472 < 0.60。方向仍为回升（连续第 2 棒靠 flash 抬升分子），量产面已排定：M0-04 的 S5/S6/S8 与 M2-01 的 S3–S7 全为 flash。
- **护栏②（tokens ≤0.35）未达标**：0.6655 > 0.35。成因是 max 棒单棒过贵与 flash 棒单轮超输入上限，纠正面＝派单文瘦身（R16-6）＋ 预抽设计文摘要（PRE-15 / FU-53），**不是降档**。
- 本棒 lane 自报 token 为**区间估算**（约 6–9 万）⇒ 依 A183 记 `tokens=null` ＋ `tokens_estimated=true`，禁取中值当精确数。
- 两项一律如实上报、不粉饰、不为凑配比改判（手册 §6.6）。

## 6. 悬空引用与未跟踪件归属

- `dangling_refs` 由驱动在 add_paths **全集**（含本取证 2 件）上实扫（PRE-17），驱动内做**集合相等**断言：多登记与少登记同样判红。本批实测悬空 **0** 条 ⇒ `allow_dangling=()`（本文刻意只引用磁盘上已存在的路径，避免制造前向引用；M2-01 的任务级取证目录归 S7 产出）。
- `untracked_owner_map = {"S5/Kierkegaard": ["tests/integration/jobs/"]}`：S5 的 4 个在飞件被归属登记；归不上的未跟踪 in-scope 件即越界，`run_commit` 会回滚拒绝提交。本棒 2 件交付面 ＋ 2 件取证均在 add_paths 内（已入索引）⇒ 不出现在未跟踪面。

## 7. 未尽面（如实登记，不含糊）

- `api/activities.py` / `api/rules.py` 仍不存在（A217 ③ 归 S3/S4）⇒ 本棒 G8 的「提供器链路」是以**键名 AST 双向对撞 ＋ 既有 health 路由 200 / X-Request-Id** 代理证明；`get_activity_service` / `get_rule_service` 的端到端打通要等 S3/S4 挂 router 后才可证。此项已写进 `tasks["M2-01"].subtask_progress["S3"]` 的前置注记，**不判本棒失败**（写权面本就不含 router）。
- `app.py` 第 108 行含单词 `sleep`，属基线既有散文（ADR-005 §2.3 的引述），不在本棒变更集内；新守护件的墙钟/`sleep` 扫描 0 命中，时钟只用 `FixedClock(T0)`。
- lane 自报一次纪律事故（无界 `grep -rn` 扫到 `evidence/**`、`prototype/**`，原始输出被工装截断）：**全程只读**，编排器以 §2 的 11 项 sha/numstat 对撞证明这些面零改动 ⇒ 无产出污染；纠正面见 R17-2 与 PRE-19。

## 8. 自纠（append-only，原文不改写）

- **R17-1（立法面缺陷）**：派单文里给出的「PC 复原基准 sha」是**派单时点**的冻结面读数，lane 交付后必然失真 ⇒ 今后一律写成「复原基准＝落地态（lane 交付后的文件 sha）；派单文给出的 sha 仅为入库前基线，禁用作复原目标」。本轮由 A235 触发，未造成返工。
- **R17-2（派单纪律）＋ PRE-19（新立）**：给 lane 的检索命令必须**限定路径**并带输出上限（禁无界 `grep -rn` 全仓），避免把 `evidence/**`、`prototype/**` 这类大体积散文面整片拉进上下文（本轮实测原始输出 ~19.9M token 被截断，白耗 loop 预算且无信息增益）。PRE-19 自 Round 18 派单起生效，写入 `resume.dispatch_preconditions_note_R17_S2b2`。
- **验证器缺陷（编排器自己的工具）**：`.orch_tmp/v_s2b2.py` 第 58–59 行把 `hexdigest()[:16]` 与 12 位字面量 `592571099d63` 比较（长度口径不匹配 ⇒ 恒判 FAIL），且 `got` 位硬编码为 `x` 掩盖真因。修正为 `[:12]` 对撞并把实测值填入 `got` 位，另存 `v_s2b2_fix.py`；**原脚本保留不删**以留痕，修正前后的 `diff -u` 已贴进 cmdlog §D-1。旁证「`contracts/openapi.json` 相对 HEAD 零改动」由同批的 numstat 判据独立给出（PASS）⇒ 该 FAIL 从未指向真实缺陷。
