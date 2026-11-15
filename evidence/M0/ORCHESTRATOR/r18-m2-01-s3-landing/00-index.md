# R18 · M2-01/S3 入库取证索引 —— 编排器独立复验全绿 ＋ 3 项 U 终裁（A247–A249）＋ 立 D-051 ＋ 编排器同批迁移 E1/E2 并自办阳性对照 PC-U2 ＋ 自纠 R18-4 / R18-6

- **取证时点**：`2026-11-16T01:21:47+08:00`（新鲜复验 §1 的实测时钟）　**入库前 HEAD**：`c94eff9`　**分支**：`m0-framework`　**tag**：`R18-landS3`
- **lane**：S3 · task **M2-01**（新建 `src/campaignlab/api/activities.py` 四端点 ＋ `api/app.py` 挂载 **3 行**（A244）＋ 新建 `tests/api/activities/{__init__.py,test_activities_router_s3.py}`（A246））
- **档位**：**qwen3.8-flash / medium**（卡片档位表原文冻结，未升降档 ⇒ `tier_match=true`）　**critical=false、slack=4、loop 1 / 2**
- **agent_id**：`01a1dff3-0aed-7620-a0f8-6b3e08af0d77`　**昵称**：Nash
- **回执**：`RESULT: DONE_WITH_GAP` ⇒ **编排器终裁 PASS**。GAP ＝ 2 条待终裁的 U 项（U-1 / U-2），**非交付缺口**；已由 A247 / A248 **同批闭合**，不留给下一棒。
- **口径**：一切读数由编排器实测（`rule_no_trust_handoff_summary_assertions`，禁采信自报）；入库四门跑在**冻结索引树**上（R11-3 ＋ D-046 的 `frozen_env` 导入隔离，工装 `scripts/orch_harness.py`）。解释器一律 `uv run --no-sync python`（3.14.10）；系统 `python3`（3.12.3）禁用于探针（R14-1 / PRE-21：会对 PEP 758 假报 SyntaxError）。
- **命令原文与输出**：同目录 `commands-and-outputs.log`（**557 行 / 37024 B / sha256[:12]=`8bca4d3c8cfd`**；由 `.orch_tmp` 下**已留档的真实捕获输出**逐段拼接，禁重打字）。
- **lane 原始回执归档**：同目录 `lane-return-raw.md`（**160 行 / 19507 B / sha256[:12]=`21bfa9a78097`**）。这是 **R18-6 的补齐动作**（Round 18 未在回收当刻落盘原始回执）⇒ 机器化归 **FU-61**。该件**如实标注了两处不可复原的传输截断**，并明示 lane **未报** token 用量。
- **在飞面**：本次入库时 lane **S6（Lorentz / task M0-04）已回传 `RESULT: DONE`（loop 2/2）但尚未入库**（一任务一提交 ⇒ 其 2 件产物归**另一个提交**）。故 `untracked_owner_map = {"S6/Lorentz": [test_lease.py, test_artifact.py]}`，`classify_untracked` 的 `outside` 必须为空集（A144(c)）。

## 1. 交付面逐件实测（**入库前**实测值；编排器口径 `lines = len(text.split("\n"))`）

| 文件 | 形态 | 行 | 字节 | sha256[:12] | 用例 |
|---|---|---|---|---|---|
| `src/campaignlab/api/activities.py` | 新建（lane） | 222 | 9955 | `887bd377a4f7` | 0（4 个端点 ＋ 2 个私有助手） |
| `src/campaignlab/api/app.py` | 修改（lane，numstat **3/0**） | 176 | 7726 | `76fcb0778f64` | — |
| `tests/api/activities/__init__.py` | 新建（lane，A246） | 2 | 89 | `8ccc54fe0ab9` | 0 |
| `tests/api/activities/test_activities_router_s3.py` | 新建（lane，A246） | 222 | 8872 | `e4d1d145cca5` | **4** |
| `tests/unit/test_s3b_routes.py`（**E1**） | 修改（**编排器**迁移，A245/A248） | 227 | 10365 | `ae4416aeabbf` | 8 |
| `tests/unit/test_s2b2_app_injection.py`（**E2**） | 修改（**编排器**迁移，A245） | 371 | 15265 | `8902dff88058` | 8 |
| `orchestrator/defects/D-051.md` | 新建（本批立单，A247） | 75 | 8257 | `11c70447e327` | — |
| `evidence/M0/ORCHESTRATOR/r18-m2-01-s3-landing/00-index.md` | 新建（本文） | — | — | 本文自身，由驱动实测写入台账 | — |
| `evidence/M0/ORCHESTRATOR/r18-m2-01-s3-landing/commands-and-outputs.log` | 新建（取证原文） | 557 | 37024 | `8bca4d3c8cfd` | — |
| `evidence/M0/ORCHESTRATOR/r18-m2-01-s3-landing/lane-return-raw.md` | 新建（回执归档，R18-6） | 160 | 19507 | `21bfa9a78097` | — |

- lane 自报的 4 件行/字节/sha 与编排器实测**逐件相符**；行数一律差 1（lane 用 `wc -l`，编排器用 `split("\n")`）⇒ lane 自报偏差 #8 已明示该口径差，**非实质不符**。
- 7 件全部 `crlf=0`、`bom=False`、`ends_nl=True`（单个 `\n` 结尾）。
- **迁移前**的 E1/E2 原值（append-only 留档，禁用于入库断言）：E1 `212 / 8983 / b0122388342a`、E2 `364 / 14545 / fadf666b810d`。

## 2. 编排器独立复验（V1–V11 全绿；原文见 cmdlog §1 与 §2）

| 组 | 判据 | 实测 |
|---|---|---|
| **V1** | `uv run --no-sync pytest -q tests/api/activities` | `rc=0`、**4 passed** |
| **V3** | `ruff check .` / `ruff format --check .` / `mypy` | `rc=0`「All checks passed!」/ `rc=0`「**311** files already formatted」/ `rc=0`「**112** source files」。**时点声明（PRE-20，禁mis-attributed 读数）**：这三是**工作树快照**，测于 `2026-11-16T01:21:47+08:00`，当时**本批 3 件取证文尚未落盘**、但 S6 在飞的 2 件已在磁盘 ⇒ 311 = 305(tracked) + 3(S3 py) + 1(D-051) + 2(S6 py)；三件取证文落盘后工作树复测为 **313**（`.log` 不入分母）。**冻结索引树的权威值 311 / 110 / 738 见 §6**，由 `run_commit` 的 `expect_counts` 逐条对账 |
| **V4** | `git diff --numstat HEAD -- app.py` | 恰 1 行 **`3	0`**（added≤3 且 deleted=0，A244）；**无注释行** |
| **V5** | `include_router` 调用点（AST 实取） | 恰 **5** = `[health.router, session_router, workspaces_router, jobs_router, activities_router]`；`activities_router` 恰 **1** |
| **V6** | 公开面 / 私面 / `__all__` | public 恰 **5**、private 恰 **2**、`__all__` **5** 名且字母序（多/缺均空集） |
| **V7** | 4 个 `operation_id` ＋ `declared_responses` | `listActivities`(GET,200) / `createActivity`(POST,**201**) / `getActivity`(GET,200) / `updateActivity`(PATCH,200)，逐字相符 |
| **V8** | 红线扫描（`time.sleep(` / `asyncio.sleep(` / `time.monotonic` / `datetime.now` / `utcnow` / `time.time(` / `# type: ignore`） | **0 命中** |
| **V9** | 依赖注入同一性 | `:166 assert _RESOLVED[-1] is injected` —— **进程内对象身份**判据，非响应体/序列化代理（另有 `:182`、`:207` 两处 `is stub`） |
| **V10** | 无回归面 | `app.state` **8** 键；中间件顺序不变（`BaseHTTPMiddleware` → `CORSMiddleware`，`install_error_handlers` 最外）；`openapi=docs=redoc=None`；kwonly **7** 名有序 |
| **V11** | 冻结面 numstat | **空**（排除 3 个授权写权面后无输出） |
| **冻结面** | 10 件 sha 独立复测（cmdlog §C） | `common.py 836e7b3e8d3a` / `jobs.py 735d30baf0c4` / `deps.py ed1075a86447` / `activity_service.py 21425228694b` / `openapi.json 592571099d63` / `test_api_app.py a97c32a63756` / `conftest.py 90ba7b17b115` / `test_jobs_conftest_no_autouse.py 0f37d540f63a` —— **8/8 全等**，`session.py` 与 `workspaces.py` 无冻结基线（仅作先例参照）⇒ **唯一变动＝授权的 `app.py`** |
| **全量** | 工作树 `pytest -q`（cmdlog §7） | `rc=0`、**747 passed / 0 failed**（= 基线 734 ＋ S3 的 4 ＋ S6 在飞的 9）；**计划外红＝空集** |

## 3. 三项 U 的编排器终裁（A247–A249，事实均经独立复核）

- **A247（S3 的 U-1）**：派单文与 design §1.4/§6.2 点名的 `IF_MATCH_PATTERN` **全仓 0 命中**（受限 grep 三面 ＋ `common.py` 的 defs/`__all__` 实取；cmdlog §3）。⇒ **采纳候选 ①**：维持 `api/jobs.py:216/:300` 冻结先例的**内联字面量** `pattern=r'^"[1-9][0-9]*"$'`（值与契约 pattern 逐字相同）⇒ **S3 产物零返工入库**。候选 ② 转 **FU-59**（P2，M1 开闸前）。**立 D-051** 记设计文失真；派单文那句未实测的「确实可用」归**编排器自纠 R18-4**，并立 **PRE-25**。
  - **如实登记残留技术债**：正则字面量现 `src/**` 共 **3** 处，与 design「禁自己写第二份正则」的意图相违。本裁定**没有消除**该相违，只是把它从「阻塞 S3」改为「有主、有优先级、有期限的 FU-59」；三处同值**当前无机器化哨兵**钉住（`D-051.residual_risk`）。
- **A248（S3 的 U-2）**：lane 的 PC-3 命中「**无牙**」真缺陷 —— 条件挂载改无条件后**无任何既有守护因该变异本身判红**（`grep -rn activities tests/unit/test_api_app.py` ⇒ 0 命中）。⇒ **采纳候选 ②**（编排器同批已落地）：把 conditional pair 追加进 E1 的 `pairs` 四元组（现 `:209`）。候选 ① 转 **FU-60**（P3，需 `test_api_app.py` 写权，本批无权）。有牙证明见 §5。
- **A249（S3 的 8 条自报偏差）**：**逐条核过全部 PASS**。两处与编排器实测的差值（行数口径差 1、`ruff format` 分母 310 vs 311）均定位到**口径/时点**成因（后者＝lane 测量时 `D-051.md` 尚未由编排器新建），**非交付面缺陷、非造假**。

## 4. 编排器同批迁移 E1 / E2（A245：预期红归编排器，lane 禁改）

- **E1** `tests/unit/test_s3b_routes.py`（5 处编辑）：`pairs` 追加 activities 条件挂载对、import 断言追加、挂载行计数 `4→5`、`activities` 恰 1、`activities_router` 出现次数上限；docstring 追加 R18 迁移注记（**R16 原注记逐字保留**）。`212 / 8983 / b0122388342a` → **`227 / 10365 / ae4416aeabbf`**。
- **E2** `tests/unit/test_s2b2_app_injection.py`（2 处编辑）：`_BANNED_ROUTER_MODULES` 移除 `activities`（**保留 `rules`**）、`EXPECTED_MOUNT_LINES` 追加第 5 项。`364 / 14545 / fadf666b810d` → **`371 / 15265 / 8902dff88058`**。
- 迁移后 **E1+E2 = 16 passed，rc=0**（cmdlog §4 / §1 的 §J）。
- **如实登记**：迁移过程中**编排器自己**引入了 2 处 E501 ＋ 1 处 `ruff format` 违规，由 `ruff check .` rc=1 / `ruff format --check .` rc=1 **实测拦下**并已修复（cmdlog §6）——**判据语义零变化**，只改自己新加的注记行文。该修复使 E1 增 1 行，故 PC-U2 的判红行号由首次的 `:211` 位移到 **`:212`**（两处均如实留档，禁只留一个）。

## 5. 编排器自办阳性对照 PC-U2（证明 A248 处置 ② **确有牙**）

| 步 | 动作 | 实测 |
|---|---|---|
| 0 | 复原基准 | `app.py` sha **`76fcb0778f64`** / 7726 B |
| 1 | 变异：`if activity_service is not None:` 条件挂载 → **无条件**挂载 | 变异态 sha **`6d50dbbf9299`** —— 与 **lane 自报的 PC-3 变异 sha 逐字相同** ⇒ 两次**独立**变异得到同一 sha，构成强交叉验证（非采信自报） |
| 2 | AST 生效证明 | `include_router` 调用点仍 5，但条件层被削平（`if` 体内不再有 include） |
| 3 | 判据实跑 `pytest -q E1 E2` | **`rc=1`**、`1 failed, 15 passed`；红原文 `assert pair in source` ⇒ `tests/unit/test_s3b_routes.py:**212**: AssertionError`（首次执行为 `:211`，见 §4） |
| 4 | 逐字节复原 | sha 回 **`76fcb0778f64`**，与基准**全等** |
| 5 | 复原后复跑 | **`rc=0`、16 passed** |

- **结论**：处置 ② 的判据**有牙**（变异必判红、复原必回绿）。
- **如实登记**：有牙的证据**只来自 E1**。E2 的 `EXPECTED_MOUNT_LINES` 是**去掉缩进的行文本**比对，「条件挂载→无条件挂载」这一变异会被 `strip()` 吃掉 ⇒ **E2 单独不能捕获**。此点已写进 E1 的迁移注记，**禁后续棒误以为 E2 也有该强度**。

## 6. counts 与两项护栏（如实上报，禁粉饰、禁为凑配比降档）

| 口径 | 入库前（`c94eff9`） | 本提交后（冻结索引树权威值） | 增量归因 |
|---|---|---|---|
| `ruff_formatted_files` | 305 | **311** | +3 py（activities / `tests/api/activities/__init__` / test_activities_router_s3）＋3 md（D-051 ＋ 本文 ＋ lane-return-raw）；`.log` **不入分母**（`RUFF_SUFFIXES=(.py,.md)`） |
| `mypy_source_files` | 107 | **110** | +3（同上 3 件 py；**冻结树不含** S6 在飞的 2 件） |
| `pytest_passed` | 734 | **738** | +4（S3 新例；S6 的 2 件未跟踪、不入索引 ⇒ 不在冻结树内） |
| `in_scope_py` | 109 | **112** | +3 |
| `in_scope_md` | 196 | **199** | +3 |

- **A101 恒等式**（冻结索引树口径）：`112 py + 199 md + 0 untracked(已归属 S6) == 311 == ruff format --check 的报数`，由 `run_commit` 的 `expect_counts` 逐条对账，不符即 `git reset` ＋ 台账 `checkout` 回滚。
- **flash 配比**（`recompute_flash_share` **程序化重算**，禁手填）：本棒入 `subtask_log`（第 **46** 条，flash / dev lane / `tokens=null`）后 units `54→**55**`、flash `30→**31**` ⇒ `flash_share_tasks = 31/55 ≈ **0.5636**`；dev units `32→**33**`、dev flash `11→**12**` ⇒ `flash_share_dev_lanes = 12/33 ≈ **0.3636**`；`token_entries_null 34→**35**`，`flash_share_tokens` 保持 **0.6655**。
- **护栏①（tasks ≥ 0.60）：未达标**（0.5636 < 0.60）。趋势 0.5385 → 0.5472 → 0.5556 → **0.5636**（连续第 4 棒靠 flash 抬分子）。剩余量产面 M0-04 的 S6/S8 ＋ M2-01 的 S4–S7 全为 flash，若如期交付可回达标。
- **护栏②（tokens ≤ 0.35）：未达标**（0.6655 > 0.35）。本棒 lane **未报** token（连区间都没有）⇒ 记 `null` + `tokens_estimated=true`、不入分母（A183：无计量句柄一律记 null，禁估算、禁取中值当精确数）。**其「不可判定」性质比 R17 更弱一档**（R17-S5 至少有自报区间 150k–220k），如实登记于 R18-6。
- 两项一律如实上报、不粉饰、不为凑配比改判（手册 §6.6）。

## 7. 悬空引用与未跟踪件归属

- `dangling_refs` 由驱动在 `add_paths` **全集**（10 件，含本文、`lane-return-raw.md` 与 `D-051.md`）上实扫（PRE-17），驱动内做**集合相等**断言（多登记与少登记同样判红）。实测 **0** 条 ⇒ `allow_dangling = ()`。
- 三件取证/缺陷文刻意只引用磁盘上**已存在**的路径。特别地：M2-01 的**任务级取证面**（M2 侧的任务级取证目录与任务级摘要）归 **S7** 产出，本文**刻意不写出其路径字面量**，以免新增前向引用——此即 R17-S5 索引的同形先例。`forward_reference_registry` 里该目录一条的 `allow_dangling_scope` 明载「仅当 `orchestrator/handoff/M2-01-design.md` 被再次暂存时才需豁免」⇒ 本批不暂存该 design，故正确处置是**不新增引用方**，而非扩豁免面。
- `untracked_owner_map = {"S6/Lorentz": [...]}`：lane S6 已回传但**尚未入库**，其 2 件 `.py` 仍是未跟踪 in-scope 件 ⇒ 必须显式归属，否则 `classify_untracked` 判越界并拒绝提交（A144(c)）。本批**禁 add** 这 2 件（一任务一提交）。

## 8. 未尽面（如实登记，不含糊）

- **M2-01 剩余序列**：S3（本批）→ **S4**（`rules.py` ＋ `app.py` 挂载 5→6，**串行**：同文件双主写禁并发）→ S5 → S6 → S7。S4 必须在本提交**入库之后**才派。
- `api/common.py` 的 `IF_MATCH_PATTERN` 收敛（3 处字面量 → 单源常量 ＋ 哨兵）归 **FU-59**，**M1 开闸前**必须处理；本批**无权**动 `common.py`（对 M2-01 冻结，`836e7b3e8d3a`）。
- activities 的**裸装配 404 守护**（运行期行为层，与本批 E1 的源码文本层判据面不同、不可互替）归 **FU-60**；本批**无权**动 `test_api_app.py`（对 M2-01 冻结，`a97c32a63756`）。
- M2-01 的 AC 判定与 M2 侧任务级取证面归 **S7** ⇒ 本批不产出任务级取证面、不判 AC（路径字面量同上刻意不写，以免新增前向引用）。
- lane 自报的过程事故（`app.py` 首次补丁脚本笔误吃掉 `return app`，numstat 一度 `4/1`，在任何判据度量之前已修复为 `3/0`）已由终态 numstat `3/0` 覆盖 ⇒ 不另取证，如实记录其自报口径（A249 判 PASS）。

## 9. 自纠（append-only，原文不改写）

- **R18-4（MAJOR）**：派单文 §3.2/§5 与其转述的 design §1.4/§6.2 断言 `IF_MATCH_PATTERN`「**确实**从 api.common 导入可用」，实测**为假**（全仓 0 命中）；同段「三个助手全部来自 api/common.py」亦失真（`parse_json_body` 实定义在 `api/session.py:89`）。⇒ 造成 U-1 与 loop 1/2；**零交付面缺陷**（A247 判零返工）。立 **D-051** ＋ **FU-59** ＋ **PRE-25**（「符号 X 可从模块 M 导入」的断言必须实跑 grep/AST 取定义点并贴命令原文，禁写「确实可用」）。原文见 `resume.round18_self_corrections`。
- **R18-5（MAJOR，随 S6 入库批处置）**：S6 派单文 §3.A#3 要求断言 `issues[0]["retryable"]`，实测**结构上不可满足**（`Issue` 模型 `extra="forbid"` 且只有 4 个字段，无 `retryable`）；同段引用的「**A88④**」经全表存在性校验**不存在**（串号/伪造）。⇒ 造成 S6 loop **用满 2/2**。立 **PRE-26**（模型字段面与 `extra` 策略必须 AST 实取）＋ **PRE-27**（引用裁定号必须脚本校验存在性）。**本条的台账处置与 S6 的终裁同批入库**（本批先立项留痕，因其成因与 R18-4 同族、必须同批说明 PRE-15 的实测范围从**文件面**扩到**符号面**）。
- **R18-6（MINOR）**：Round 18 两条 lane 的**原始回执均未在回收当刻落盘归档**（违 R12/R13 先例），跨模型交接后自报 token 区间**不可复原**。⇒ **零交付面影响**（一切读数均编排器实测），受损的只是**成本可观测性**。纠正＝本批补齐 `lane-return-raw.md`（含两处截断的如实标记）＋ 立 **FU-61**（机器化 `archive_lane_return` ＋ `run_commit` 顺序门）＋ PRE-13 增第四步「回收即归档」。
- 与前批同族：R18-1 / R18-2 / R18-3 见 `resume.round18_self_corrections`；D-047 / D-049 / D-050 / D-051 是 M0 阶段**立法面失真的连续四例** ⇒ PRE-25/26/27 定为**强制门**而非建议。
