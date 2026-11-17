# R19 · M1-01/S2 partial-landing 取证索引（编排器自办）

- **批次 tag**：`R19-landS2partial`
- **生成时点**：2026-11-18T05:28:18+08:00
- **在飞棒**：lane `S2` / task `M1-01` / 昵称 **Epicurus** / `agent_id` `01a1eb34-3545-7a30-886d-b03d3f36165e`
- **档位**：`qwen3.8-max` / reasoning `high` / 预算 45k / `loop_cap` 2（卡片 `orchestrator/tasks/M1-01.md:40` 原文冻结，命中手册 §6.3 强制 max 硬规则）
- **lane 自报结论**：`RESULT: PARTIAL`、`LOOP_USED: 2 / 2`、`TOKENS_SELF_ESTIMATE: null`（无计量句柄，A183 禁猜测值）
- **编排器终裁**：**PARTIAL 予以追认** —— 交付面 §11.1 的**结构面 4 件**经独立复验全绿入库；未交付的 **12 项**按派单文 §8 授权的降级选项**退回编排器**，拆两棒续派（见 `resume.followups` 的 **FU-70**）。

## 1. 交付件 face（编排器**独立实测**，非采信 lane 自报 —— PRE-29）

| 文件 | 行 | 字节 | sha256[:12] | 与 lane 自报 [FACES] |
|---|---|---|---|---|
| `src/campaignlab/domain/ingest/__init__.py` | 1 | 73 | `2ad44a31e52d` | **逐字相符** |
| `src/campaignlab/domain/ingest/limits.py` | 39 | 1544 | `b98965d4d621` | **逐字相符** |
| `src/campaignlab/domain/ingest/model.py` | 198 | 5563 | `62518861e62a` | **逐字相符** |
| `src/campaignlab/domain/ingest/states.py` | 242 | 9848 | `e941d047c5b8` | **逐字相符** |

编码四判据（**编排器重跑**；lane 自报的 BOM/CR 探针跑于最后一次 `sed`/`ruff format` 之前，属**沿用同批前值**，故必须重跑）：4 件全数 **UTF-8 可解码 / BOM=False / CR=0 / 尾恰一个换行**；`file -bi` 4 件全数含 `charset=utf-8`。

## 2. 独立复验判据面

- 脚本：`.orch_tmp/orch_vS2p2.py`（**340 行 / 18904 B / `9101cf05179c`**；编排器自写，**禁采信 lane 自报** —— PRE-29）
- 日志：`gates/V-independent-reverify.log`（**53 行 / 7633 B / `dedd225dde38`**）
- 结果：**`JUDGES: 43 PASS: 43 FAIL: 0` ＋ `VERIFY RESULT: GREEN`**（文本双判锚点齐备）
- 实测面 JSON：`.orch_tmp/orch_vS2p2_measured.json`（**178 行 / 3392 B / `aebfe6fda879`**；faces / porcelain / numstat / 允许集 / 上行依赖命中 / AST 差集 / 符号面 / 字段序 / controls）
- **对照（PRE-44 第 5 款）**：**5 阳 3 阴** —— `PC-A` face 谓词篡改 `lines` 判红 · `PC-B` 注入 BOM 判红 · `PC-C` `common_all` 80→81 判红 · `PC-D` 字段序反转判红 · `PC-E` `evidence/` 下取证目录**之外**的命中判红；`NC-A` 未篡改时四谓词全通过 · `NC-B` **判据计数器自证**（`N_PASS>=34`，即 v1「汇总恒报 0」缺陷的回归防线）· `NC-C` 空命中时硬禁面谓词通过。

> **⚠ 本件曾记载 v1 读数（`PASS 34 / FAIL 0`、日志 42 行 / `0aa1d7a7ff45`）—— 已按 §2.3 的归因订正为 v2 实测值。**
> v1 原件留档 `.orch_tmp/orch_vS2p_v1_defective.{py,log}`，v2-run1（判红 2 条）留档 `.orch_tmp/orch_vS2p2_run1_stale.{py,log}`（**均只在暂存区、不入库**；权威面以本件与已入库的 `gates/*.log` 为准 —— PRE-46 第 ③ 款）。

### 2.3 判据缺陷与同口径归因（自纠 **R19-31**，本批如实登记）

编排器**未采信**上一回合交接摘要里的「34 PASS / 0 FAIL」结论，而是**重跑复验脚本实测**，当场发现 **5 处判据缺陷**（PRE-44 同族第 **11** 次复发）：

| # | 缺陷 | 实测证据 | 订正 |
|---|---|---|---|
| (a) | 汇总行 `独立复验判据条数` 写成 `len(fails) + sum(1 for _ in ())`，**恒为 0**（PASS 从未累加） | v1 日志实测 **34** 条 `PASS` 行，汇总却报 `判据条数：0` | v2 引入 `N_PASS`/`N_FAIL` 全局计数器；并加 **NC-B** 作回归防线 |
| (b) | 缺 `JUDGES:` 与 `VERIFY RESULT:` 两行 ⇒ 台账 `verdict_source` 要求的**文本双判**无锚点 | v1 日志 `grep -n 'JUDGES\|VERIFY RESULT'` **零命中** | v2 补齐两行（沿 `round19_lane_S1_postverify_independent.verdict_source` 体例） |
| (c) | 汇总行以 `FAILS:` 开头 ⇒ `grep -c '^FAIL'` 把**它自身**数成 1 条 FAIL（假阳性） | 编排器实测 `grep -c '^FAIL'` = **1**，而真实 FAIL = **0** | v2 改名 `FAILED_ITEMS:`；实测 `grep -c '^FAIL '` = **0** |
| (d) | **零对照** ⇒ 违反 PRE-44 第 5 款（判据无从自证有牙、亦无从自证不恒红） | v1 日志无任何 `PC-*`/`NC-*` 条目 | v2 新增 **5 阳 3 阴** |
| (e) | `V3`/`V3c` 的期望值派生于「**编排器自办取证件尚未落盘**」的时点 ⇒ 复跑必然判红 | v2-run1 实测 **RED 38/40**，2 条 FAIL 全为 `V3`＋`V3c evidence/`，其命中项**唯一**内容＝编排器自己的取证目录 | 按 **PRE-45 第 3 款**做**同口径归因**：属**判据过期**、**非完整性缺口** ⇒ run2 重派生为「**显式允许集** ＋ 允许集之外零命中」，并新增 **V3d**（排除面不过宽）＋ **PC-E**/`NC-C` 两条对照 |

**归因结论（PRE-45③，沿 S1 的 `attribution_probe` 体例）**：(e) 的 2 条红**不是**交付面缺口 —— lane 侧对 `evidence/**` 确实**零改动**（`git status --porcelain -- evidence/` 的命中项**全部**落在 `evidence/M0/ORCHESTRATOR/r19-m1-01-s2-landing/` 内，V3d 已机器断言「恰 1 条且全在该目录内」）。v1 跑于 **05:22**，取证目录由 `orch_s2l_ev.py` 于 **05:28** 生成 ⇒ 期望值天然过期。**判据本体 V1/V2/V2b/V4–V11 的语义一字未改**，只重派生了 V3 族的期望面，保证与 v1 **同口径**（PRE-44 第 1 款）。

### 2.1 判据清单（V1–V11）

| 门 | 判据 | 实测 |
|---|---|---|
| V1 | 4 件 face == lane 自报 | **逐字相符**（4/4） |
| V2 | 编码四判据 ＋ `file -bi` charset | **PASS**（重跑） |
| V3 | `porcelain` 命中集 == **允许集**（lane 交付目录 `src/campaignlab/domain/ingest/` ＋ 编排器自办取证目录），且**允许集之外零命中**；`git diff --numstat` 与 `--cached --numstat` **均为空**（后者＝V3b） | **PASS** ⇒ 零 tracked 改动、4 件纯追加面 added=deleted=0（R19-31e 同口径重派生） |
| V3c | 12 个硬禁面目录 porcelain 逐目录为空（`tests/` `evidence/` `orchestrator/` `spec/` `contracts/` `scripts/` `web/` `api/` `application/` `infra/` `worker/` `migrations/`）；`evidence/` 一项按 R19-31e **显式排除编排器自办取证目录** | **PASS**（12/12） |
| V3d | **排除面不过宽**（R19-31e 的防牙判据）：`evidence/` 下被排除的命中项**非空**、**恰 1 条**且**全部**落在编排器取证目录内 | **PASS** |
| V4 | 上行依赖零命中（`campaignlab.api` / `sqlalchemy` / `conn.begin`，含 docstring 散文面） | **PASS**（`NO_UPWARD_DEP`） |
| V5 | 符号面 == 派单基线：`common.__all__`=**80**(uniq 80) / `deps.__all__`=**13** / `repositories.__all__`=**16** / `PROBLEM_CODES`=**20** / DomainError 子类=**14** | **PASS**（§11.2 未交付 ⇒ 三值逐字不变） |
| V6 | design **§11.1 符号清单（从原文程序化解析）**× AST 实取双向差集 | **PASS**：`limits` 5/5、`model` 16/16、`states` **11/11**（lane 自报「10 个」属**自报少数**，实取 11 个全数落地）；`model.py` 清单外公开名恰为 **U-3** 的 `MappingLayout`/`SourceMoneyUnit`/`DedupMode` 三枚 |
| V7 | A115＋A292 元守护：4 件里 `len(*.__all__) == <整数>` 形态钉桩 | **上限制 == 0**（PASS） |
| V8 | `Finding` 四字段名与顺序 == 实测 `Issue.model_fields` | **PASS**（`code/location/message/severity` ⇒ **U-2 裁定面**：实测序优先于 §4.1 代码块） |
| V9 | `ImportTransition` 8 字段名逐字对齐实测 `worker/states.py::Transition` | **PASS** |
| V9b | `IMPORT_TRANSITIONS` 只注册 I1–I7（§3.3） | **PASS**（count=7） |
| V10 | `__init__.py` A276 形态（单行 docstring、非零字节） | **PASS**（73 B） |
| V11 | 4 件全部落在台账 `in_flight_agents[13].write_set` 前缀面内 | **PASS** |

### 2.2 未执行门（**禁谎报 PASS**）

- **V7 契约门**（lane 侧）：lane 自报 `NOT_RUN`（预算耗尽）；本棒**零改动** `contracts/**`/`spec/**`/`scripts/**` ⇒ 编排器判读 **NOT_APPLICABLE**（无契约面变更）。
- **V11 六条卡片 gate**（lane 侧）：lane 自报 `NOT_RUN`；`tests/golden/ingest`、`tests/domain/ingest` 派单时点实测 ABSENT ⇒ 判读 **NOT_APPLICABLE_YET**（4 条）；`tests/integration/jobs -k validate_import` 判读 **NO_TEETH**（**FU-67** 未闭合前禁标 PASS）。
- **权威四门**（`ruff format --check` / `ruff check` / `mypy` / `pytest`）：由 `run_commit` 在**冻结索引树**上重跑并与 `expect_counts` 逐条对账（不符即 `git reset` 回滚），其读数即本批 counts 的**唯一背书**；lane 自报的工作树读数（363 / 134 / 852）按 **PRE-29 属二手**，只作对撞靶子。

## 3. 交付缺口（lane 退回，编排器承接）

**未交付 12 项**（lane 原文 [GAPS]，禁由下游 lane 代为发明）：

- **§11.1 剩 7 件**：`locate.py`、`digests.py`、`normalize.py`、`validate.py`（N1–N18）、`parse.py`（含 `legacy_mapping_to_source_mapping`）、`api.py`、`infra/files.py`
- **§11.2 全部**：`api/common.py` 的 11 DTO ＋ 2 Literal 再导出 ＋ `__all__`；`tests/unit/test_domain_errors.py` 两行钉桩改实取对撞
- **§11.3 全部**：`application/import_service.py`、`application/import_jobs.py`、`infra/db/repositories.py` / `api/deps.py` / `api/app.py` 三件纯追加

**成因（U-5，阻塞项）**：本棒权威规范面实测 ＝ design 1394 行 ＋ `M1-01.slice.json` ＋ 派单文 615 行 / 72533 B（含 §5.2 的 A277–A292 约 36 KB 逐字正文）≈ **291 KB**，而档位为 **45k** ⇒ 实际用量超档，只能交付 4/13 件。**处置**：拆两棒续派（**FU-70**），且**禁再整包携带 291 KB**（按 **PRE-15** 预抽设计文摘要 ＋ **PRE-19** 检索限定，只带自己那一刀的规范面）。

## 4. U 项裁定（编排器终裁，手册 §6.4：禁让 lane 自裁）

| U | 议题 | 裁定 | 号 |
|---|---|---|---|
| U-1 | `ImportTransition.trigger` 存 token 还是整段散文 | **追认 A 案**（只存 operationId token；I5/I6/I7 共用 `VALIDATE_IMPORT`、以 `target` 相区分），I6 的 `guard` 机械展开合规 | **A296** |
| U-2 | `Finding` 字段序：§4.1 代码块 vs 正文实测序 | **以实测 `Issue.model_fields` 序为准**（`code/location/message/severity`）；design §4.1 代码块走 **§14 文末追记**订正（A214 窄豁免，deleted=0） | **A297** |
| U-3 | `MappingLayout`/`SourceMoneyUnit`/`DedupMode` 落点未点名 | **追认 A 案**（落 `model.py`）；同批把三名字补进 §11.1 清单（§14 追记），以免 S6 的 AST 守护判「越出符号清单」 | **A298** |
| U-4 | `InputTooLarge(detail)` 文案无冻结原文 | **冻结 lane 现文案**为准（S6 若断言 detail 以此为准）；同批写入 §14 追记 | **A299** |
| U-5 | 档位/预算不足（阻塞） | **采 A 案：拆两棒续派**（棒甲 §11.1 剩 7 件、棒乙 §11.2＋§11.3 六项），**禁**把本卡档位提到 ≥120k 后重派全量（关键路径 `slack=0`，串行两棒更可控；且结构面已入库可供下游 import）⇒ **FU-70** | **A300** |
| U-6 | lane 未逐字通读派单文全文（协议偏差自报） | **如实登记、不予免责亦不加重**：未读面属**规范面重复携带**（§5.2 的 36 KB 裁定正文）⇒ 根因归编排器的派单文体量（**A295** 已收窄携带口径），**禁**把它记成 lane 的诚信缺陷；但**禁**把该回执当作「已全读」采信 | **A301** |

## 5. 立规与后续

- **PRE-48（本批新立，源自 lane 自报的 2 条自纠）**：编辑既有文件时，任何「按行号整行替换」**必须先打印该行原文**并确认其是否为多行结构（docstring / 括号 / 围栏）的边界行，禁凭记忆构造替换文本；**领域层 docstring 禁写点号全路径**（如 `campaignlab.api`）以免 grep 类判据假命中，且此类 grep 判据**必须固定带 `--include`**。
- **FU-70（本批新建，P1）**：按 **A300** 拆两棒续派 M1-01/S2 的未交付 12 项；两棒的派单文**只携带自己那一刀的规范面摘录**（PRE-15 / PRE-19），禁再整包携带 291 KB。
- **FU-69 保持 OPEN 并改挂**：其 ①②③④ 四项义务的前提（`api/common.py` 已纯追加）因 §11.2 **未交付**而**不成立** ⇒ `only_runtime=[]`/`only_pinned=[]`、`common.__all__` 仍 **80**、PRE-40 锁值**零漂移**（本批实测 `DRIFT_HEAD=0`，**无需更新锁值**）；义务整体**改挂到棒乙（§11.2）的 landing 批同批闭合**（禁拖批/拆批）。

## 6. PRE-43 证据链

| 环节 | 落盘件 | face |
|---|---|---|
| lane 回执（lane 自落盘 ＋ 工具返回同一份） | `.orch_tmp/orch_S2_receipt.md` | 63 行 / 10634 B / `5917772f9759` |
| 本件（字节级复制入仓） | `evidence/M0/ORCHESTRATOR/r19-m1-01-s2-landing/lane-receipt-S2-raw.md` | 63 行 / 10634 B / `5917772f9759` |
| `spawn_agent` 返回 | `.orch_tmp/orch_S2_spawnret.txt` | 1 行 / 279 B |
| `close_agent` 返回 | `.orch_tmp/orch_S2_close_agentret.txt` | 见该件（正文不复制第二份，PRE-46③） |
| 独立复验日志（**v2**，`VERIFY RESULT: GREEN`） | `evidence/M0/ORCHESTRATOR/r19-m1-01-s2-landing/gates/V-independent-reverify.log` | 53 行 / 7633 B / `dedd225dde38` |
| 独立复验脚本（**v2**） | `.orch_tmp/orch_vS2p2.py` | 340 行 / 18904 B / `9101cf05179c` |
| v1 缺陷原件（留档、不入库） | `.orch_tmp/orch_vS2p_v1_defective.py` / `.log` | 见该件（R19-31 的证据面） |
| v2-run1 判红原件（留档、不入库） | `.orch_tmp/orch_vS2p2_run1_stale.py` / `.log` | 见该件（R19-31e 归因的证据面） |

**槽位释放顺序（如实订正 —— 本件初版此句为事实错误，自纠 R19-31f）**：`close_agent(01a1eb34-3545-7a30-886d-b03d3f36165e)` 的**实际调用时点**是**上一批** `R19-backfill-wave4pd-spawn`（`5745cb0`）**入库并 push 成功之后、本 content-face 落地批之前**（落盘件 `.orch_tmp/orch_S2_close_agentret.txt` 的 mtime **05:20:30**，晚于 `orch_bfw4_commit.log` 的 **05:18:56**、早于本取证目录生成的 **05:28**）。

初版写作「`close_agent` 在**本批** push 成功之后才调用」是**把计划当成了事实**（本批当时尚未提交）⇒ 违反 **A183 禁猜测值**在**文档面**的同族形态。订正口径：

- **不构成不可恢复态**：`close_agent` 返回 `returned_status=completed`，其 `previous_status.completed` 正文与 lane 自行双落盘的 `orch_S2_receipt.md` **逐字同一份**（63 行 / 10634 B / `5917772f9759`），且该份**已字节级复制入仓**为本目录的 `lane-receipt-S2-raw.md` ⇒ 槽位释放**未**丢失任何交付事实（PRE-43① 落盘义务已尽、PRE-46③ 不复制第二份正文）。
- **但确有顺序瑕疵**：O-9 / PRE-43③ 的**本意**是「先入库、后释放槽位」，此处释放发生在**交付件入库之前**（4 件 `.py` 当时仍是未跟踪态）。风险面＝若在「槽位已释放」与「本批入库」之间发生宿主重置，则**无法再向该 agent 追问**未交付的 12 项。缓解事实：12 项缺口已由 lane 回执的 `[GAPS]` 段**逐字落盘并即将入库**，追问本非唯一信息源 ⇒ **风险已被回执落盘消化**，不构成数据损失。
- **立规**：本条瑕疵归入 **PRE-48** 的**第 ③ 款**（新增）——「**取证件里凡描述『执行顺序/时点』的句子，必须由落盘件的 mtime 或台账时间戳程序化背书，禁把计划写成既成事实**」。
