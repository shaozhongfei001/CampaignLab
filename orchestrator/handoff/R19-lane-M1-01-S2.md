# R19 · Lane S2 · M1-01/S2 派单文 —— 负例与边界矩阵实现 ＋ 文件接入底座（**关键路径 `slack=0`**）

> 公共纪律一律见 `orchestrator/handoff/LANE-COMMON.md`（**先读它**，本文不重述）。
> 权威条款：`docs/delivery/LONG-HORIZON-ORCHESTRATION.md` v1.7。冲突时**手册胜**、其次本文、再次 design/卡片。
> **PRE-29 双向禁采信**：本文一切读数都是编排器于派单时点的实测快照；你上工**必须自行复测**并贴命令原文，
> 禁采信二手复述（**包括本文件**）。回源一律走 §3 给的**绝对行号 / 路径**自读原文。

## 0. 身份 · 档位 · 边界（A261：一律以 **sha** 为锚，禁写 tag）

| 项 | 值 |
|---|---|
| 派单基线 HEAD（短 sha） | `8a12228` |
| 派单基线 HEAD（全 sha） | `8a1222837d5b197ace4dcda666668bbcd3055db6` |
| 分支 | `m0-framework` |
| 任务 / 子任务 | `M1-01` / **S2**（该任务**第 2 棒**；S1 已 DONE 并入库，设计文已冻结 ⇒ 你是**实现第一棒**） |
| lane 双键（PRE-31） | (`lane`=`S2`, `task`=`M1-01`)。⚠ 仓内 `M2-01` 也有名为 `S2a`/`S2b-1`/`S2b-2` 的子任务（`R15`/`R16`/`R17` 期），与本棒**完全无关**，禁混用其口径或写权面 |
| 档位 / reasoning | **`qwen3.8-max`** / `high`（任务卡 `orchestrator/tasks/M1-01.md:32-49` 档位表原文：**S2 负例与边界矩阵实现 + 文件接入底座**（重复切片、负人数、层级倒置、错误行长、重复码、孤立切片、> 8 MiB；硬规则 6.3：金额分与口径语义强制 max）＝ **45k** / `qwen3.8-max` high） |
| loop 上限 | **2** 轮（卡片 `dispatch.loop_cap` 原文：依据 `critical=true`、`slack=0`，手册 §15.6 第 1 条）。第 2 轮仍红即写 **BLOCKER** 并附「缩小范围」降级交付选项 |
| token 预算 | **45k**（卡片档位表原值） |
| critical / slack | **`critical=true` / `slack=0`**（台账实测）⇒ **你在关键路径上，且是 S3–S8 六棒的前置**。卡片原文警告：「M1-01 卡住会同时锁死 L1 lane 与 wave4 的 M1-P01，须**优先上报**」 |
| 依赖 | `M0-04` ＝ **DONE**（编排器实测）；`M1-01/S1` ＝ **DONE**（design 文 1393 行已入库冻结）⇒ **依赖已清偿** |
| 并行对象 | **无 —— 本棒串行独占**。编排器依 **PRE-5 三判据**实测：与候选并行棒 `M2-01/S7` 的写权面在判据③**命中交叉**（共享冻结面 `src/campaignlab/api/common.py` ＋ 共享 `ruff_formatted_files` 分母）⇒ 依文档 §9「429 缓解」**串行优先**，S7 递延至本棒入库之后（裁定 **A293**，§5 逐字）。因此 `git status` 里**只应**看到你自己的在飞文件；出现任何第三方面**禁碰**并按 §8 上报（A161 在飞污染） |
| 上工第一件事 | **V0 基线自证**：复测 HEAD。若已漂移且属编排器自身的纯文档/纯台账提交（本派单文的 predispatch 批即是），**依 A269 先例：U-BASELINE 已由编排器在本派单文预裁关闭** —— 以 spawn message 里逐字给出的**取代后权威读数**为准；除此之外的任何漂移（含代码面 sha 变化）一律停手报 `U-BASELINE` |

## 1. 写权面（越界即回报编排器，手册 §6.4；禁「顺手改」）

写权面共 **17 项** ＝ 卡片 `scope_allow` 原 8 项 ＋ **A277/A290 扩围授权的 G1–G9 九件**（G10 **本卡禁写**）。
逐件的设计依据在 `M1-01-design.md` §11.1（绝对行 **982–997**）/ §11.2（**998–1014**）/ §11.3（**1015–1037**）
与 §11.10 缺口表（**1124–1138**）—— **必须自读原文**，本段只是索引与红线，**禁以本段取代原文**。

### 1.1 只新建 · 纯领域层与文件底座（design §11.1；**禁 SQL、禁开事务、禁 import `campaignlab.api`**）

```text
src/campaignlab/domain/ingest/__init__.py     （A276 形态：单行 docstring，禁零字节空文件）
src/campaignlab/domain/ingest/model.py
src/campaignlab/domain/ingest/states.py
src/campaignlab/domain/ingest/limits.py
src/campaignlab/domain/ingest/locate.py
src/campaignlab/domain/ingest/digests.py
src/campaignlab/domain/ingest/normalize.py
src/campaignlab/domain/ingest/validate.py
src/campaignlab/domain/ingest/parse.py        （本棒只落**骨架与注册表**；三个 parse_* 适配器实体归 S3/S4）
src/campaignlab/domain/ingest/api.py          （§4.1 唯一入口 ＝ public_frozen 面，改动走 CR）
src/campaignlab/infra/files.py                （§7.4；**零 DML**，只调 ArtifactWriter/ArtifactRepository）
```

每件的**符号清单逐字**见 §11.1 对应行（例如 `model.py:FileRef,RawTable,RawSource,SourceRow,NormalizedSlice,
MappingSpec,LongColumnSpec,Finding,SliceCounts,IngestResult,IngestLimits,DEFAULT_LIMITS,UploadPayload,
UploadedFile,SliceKey,INGEST_SEVERITIES`）。**禁增删符号名、禁改字段序**（字段序逐字按 §4.1/§4.3）。

### 1.2 只新建 · 应用层（G3/G4，design §11.3）

```text
src/campaignlab/application/import_service.py   （事务写法逐字对齐 activity_service.py:620 的 with connect(engine) as conn, conn.begin():）
src/campaignlab/application/import_jobs.py      （ValidateImportHandler：I5/I6/I7 的执行方）
```

### 1.3 纯追加（`git diff --numstat` 的 **`deleted` 列必须为 0**）

| 路径 | 授权 | 追加内容（design 原文行号） |
|---|---|---|
| `src/campaignlab/api/common.py` | **G1**（§11.2，行 998–1006；依据 §2.5 方案 A ＋ A91 同构 append-only） | 11 个 DTO/别名 ＋ 2 个 domain Literal 的再导出 ＋ 全部新名字进 `__all__` |
| `src/campaignlab/infra/db/repositories.py` | **G5**（§11.3；A81 SQL 写点唯一 ＋ A82） | 3 Record ＋ 3 Repository ＋ 3 `*_from_row` ＋ 3 列序常量 ＋ `__all__` |
| `src/campaignlab/api/deps.py` | **G6**（§11.3；**A233 的 `TYPE_CHECKING` 块形态**，规避 ruff `I001`） | 1 Protocol ＋ 1 提供器 ＋ `__all__` |
| `src/campaignlab/api/app.py` | **G7**（§11.3；**A90① / A10 最小例外**） | **总追加 ≤ 4 行**（1 import ＋ 1 `include_router` ＋ 至多 2 行 state/handler 注册），0 删除行 |

### 1.4 硬禁面（**一字不改**；越界即判红）

- **`tests/**` 全部** —— 含 **G2**（`tests/unit/test_domain_errors.py`）、**G8**（`tests/golden/__init__.py`）、
  **G9**（`tests/api/imports/**`）、**G10**（`tests/integration/jobs/**`）。A245/A248：`tests/**` 是 lane 硬禁面，
  凡需改动一律由**编排器自办**。G2 的改造**已由编排器在 A292 批做完**（见 §1.5），你**禁再动**。
- `spec/**` · `contracts/**`（只读，手册 §1 不变量）· `.git/**` · `orchestrator/state.json` · `scripts/**` ·
  `migrations/**` · `evidence/**`（归 S8）· `qa-reports/**` · `web/**` · `fixtures/**` ·
  `pyproject.toml` / `ruff.toml` / `mypy.ini`。
- `src/campaignlab/worker/**`（`VALIDATE_IMPORT` 处理器只在 `application/import_jobs.py` 实现，**注册点**在
  `api/app.py` 的同一处最小例外内 —— design §11.3 末段；`worker/deps.py` 在 `scope_deny`）。
- `src/campaignlab/api/imports.py`（**归 S5**，本棒禁建）；`src/campaignlab/api/activities.py` ·
  `api/rules.py` · `api/preflight.py`（同波 L2：M2-01/M2-02/M2-03）；`src/campaignlab/analytics/**`（M3 lane）。
- `orchestrator/handoff/**` 全部（含 `M1-01-design.md` —— **S1 已交付冻结**，你只读；发现失真写进 §12 型上报，禁自行改）。
- `orchestrator/tasks/**`（卡片受 D-011 保护）。
- **禁**执行任何 `git commit / push / add / reset / checkout`（入库由编排器做）；**禁** sudo；**禁**建 PR / 触发 workflow。

### 1.5 已由编排器做完、**你禁再动**（A292；禁重复劳动）

`tests/unit/test_domain_errors.py`（实测 **301 行 / 11993 B / sha12 `e4a9fec29c20`**）的 `:176`/`:177` 写死项数
已被编排器改造为与 **`COMMON_ALL_NAMES` 显式名单对撞**（该名单在 `:33`，由 `common.__all__` 程序化生成 **80** 名），
断言体在 `:278`：`set(common.__all__) == set(COMMON_ALL_NAMES)` 并附 `only_runtime` / `only_pinned` 双向差集报信；
元守护 `tests/unit/test_if_match_pattern_single_source.py::test_all_common_surface_pins_agree_with_runtime`
已迁移为**双制**：**上限制**（硬编码计数钉桩处数 `<= ALL_COUNT_PIN_SITES_CEILING` ＝ **0**，A115 机器化）
＋ **实取对撞下界制**（带 `LIVE_COLLISION_MARKER` 的守护位点数 `>= LIVE_COLLISION_SITES_FLOOR` ＝ **1**）。

### 1.6 ⚠ **A294 授权红（本棒唯一的预期红，禁自行消除）**

你依 §1.2 向 `common.__all__` 追加新名字后，`:278` 的名单对撞**必然判红**（钉桩名单仍是 80 名）。
**这不是你的缺陷，也不许你去改 `tests/**`**（硬禁面）。裁定 **A294**（§5 逐字）要求你：

1. **禁**改 `tests/unit/test_domain_errors.py` 的任何一行；**禁**为过测改测试期望（卡片红线原文）。
2. 在回执 §10 的 **R-A294** 项里给出**实测三值**：追加后 `len(common.__all__)`、`len(set(common.__all__))`、
   以及 `sorted(set(common.__all__) - set(COMMON_ALL_NAMES))` 的**逐字清单**（`only_runtime`）与
   `sorted(set(COMMON_ALL_NAMES) - set(common.__all__))`（`only_pinned`，**期望为空**）。
3. 编排器在你的**入库批同批**用 `only_runtime` **程序化再生** `COMMON_ALL_NAMES`（PRE-37 第 1 款：禁手打），
   并在冻结索引树上重跑四门 ⇒ 你交付时该用例判红是**已知且已授权**的状态。
4. 除该 1 条外，**其余门必须全绿**；出现第 2 条红即停手按 §8 上报。

### 1.7 编码与体例硬要求（LANE-COMMON §2 / §3.1；**违反必判红**）

- 一律 **UTF-8 / 无 BOM / 无 CR（`\r` 零命中）/ 文件尾恰一个换行**（PRE-39 编码四判据，回执须贴 `file -bi` 原文）。
- `ruff format --check .` 的作用域**含 `.md`**（A175）⇒ 你的 `.py` 必须已是 ruff format 规范形。
- `mypy` 为 **`strict = true`**：集合对撞一律写 `set(...) == set(...)`，**禁** `set` vs `frozenset` 混比（A292 实测口径）。
- **禁写死任何符号面计数**（A115）：`__all__` 项数、用例数、分母一律 `inspect` / `--collect-only` **实取**。
- **禁浮点算金额分**（卡片红线；§4.5 整数分口径）；**禁用系统当前时间做领域计算**（显式时钟，§7.3）。
- **禁在 `domain/ingest/**` 写 SQL 或开事务**（A81 SQL 写点唯一；§11.1 抬头原文）；**禁 import `campaignlab.api`**（分层）。
- **禁新增 `DomainError` 子类、禁新增 `PROBLEM_CODES` 码**（§11.2 末段与 §3.4：码名一律实取自 `domain/errors.py::PROBLEM_CODES`，零发明）。
- 包标记 `__init__.py` 一律 **A276 形态：单行 docstring**，禁零字节空文件（实测先例 `tests/api/activities/__init__.py` ＝ 1 行 / 89 B / `8ccc54fe0ab9`）。
- lane 侧 scratch 文件一律 `orch_` 前缀且只落 `.orch_tmp/`（PRE-39）；取证件编码四判据同 PRE-39。

## 2. 预期红清单（PRE-14；由编排器**实测**得出，非推测）

**实测结论：本棒的预期红＝恰 1 条（A294 授权红），其余门必须全绿。**

| # | 判红对象 | 成因（实测） | 处置 |
|---|---|---|---|
| 1 | `tests/unit/test_domain_errors.py` 的 `set(common.__all__) == set(COMMON_ALL_NAMES)` 名单对撞用例（断言体在 `:278`，钉桩名单在 `:33`，实测 **80** 名） | 你依 design §11.2（G1）向 `api/common.py` 纯追加新名字 ⇒ 运行期 `__all__` 增长而钉桩名单未变 ⇒ 集合对撞判红。**`tests/**` 是 lane 硬禁面（A245/A248），你无权消除它** | **A294 授权红**：禁改测试、禁改期望；在回执 **R-A294** 项给出 `only_runtime` / `only_pinned` 逐字清单，由**编排器在你的入库批同批程序化再生名单** |
| 2 | V11 的 4 条卡片 gate（`tests/golden/ingest -k counts`、`tests/domain/ingest -k locate` / `-k size_limit` / `-k csv_equivalence -k stale_validation`） | 实测 `tests/golden`（归 S7）与 `tests/domain/ingest`（归 S6）**均 ABSENT** ⇒ 命令必然非 0 | 标 **`NOT_APPLICABLE_YET`** 并贴实测 rc；**禁**自建目录或写占位用例 |
| 3 | V11 的 `tests/integration/jobs -k validate_import` | 属 **M0-04** 写权面（**G10 本卡禁写**）；既有诊断 **FU-67** 记该门可能 `NO_TEETH` | **只跑不改**；收集到 0 例即标 **`NO_TEETH`**，**禁标 PASS** |

**除上列 3 类外，出现任何第 2 条真实红（ruff / mypy / 其余 pytest / 契约门）⇒ 停手并按 §8 上报。**
loop 上限 **2** 轮；第 2 轮仍红写 **BLOCKER** ＋ 附缩小范围的降级交付选项。

## 3. 逐字口径回源（PRE-29：禁采信二手复述，一律回源到下列**路径 / 行号**自读原文）

### 3.1 你的任务卡（**权威**，只读）

`orchestrator/tasks/M1-01.md`（**70 行 / 13420 B / sha12 `b18813bd6dd1`**）：
`:4` goal · `:6-10` inputs（slice / contracts / fixtures / specs）· `:11-21` **gates 原文**（含 AC-005/AC-006 逐字与 6 条命令）·
`:22` `scope_allow` · `:23` `scope_deny` · `:24` **`public_frozen`**（M1-P01 只能经同一套 `domain/ingest` 入口扩展、
**禁另起第二套校验**、**禁改**冻结的入口签名，改动走 CR）· `:25` outputs · `:26+` dispatch（档位 / loop_cap）·
`:32-49` **子任务档位表 S1–S8** · 文末「禁止」段（**逐字义务**：不写第二套校验器、不用浮点算金额分、
不用系统当前时间、不把 duckdb 关系导入绕过 `infra/files.py` 的摘要登记、不为过测改测试期望）。

### 3.2 契约切片（**实现唯一依据**，只读）

`orchestrator/handoff/M1-01.slice.json`（**2876 行 / 60641 B / sha12 `eadbd88e4ef7`**，`spec_version` 从活契约 `info.version` 动态读取、**禁硬编码**）：
`operations`（**6** 个 operationId：`createImport` / `attachImportFile` / `configureImport` / `validateImport` /
`getImport` / `listImports`）· `ddl`（**3** 表：`imports` / `import_files` / `source_mappings`；`imports.state` 的
**7 态**＝你状态机的分母）· `acceptance_rows`（**AC-005 / AC-006 逐字**）。
⚠ method / path / 字段序**一律实取自切片**，禁凭本文或 design 的摘要取值（A171 口径）。

### 3.3 你的设计文（**S1 已冻结**，只读；本棒的牢笼与地图）

`orchestrator/handoff/M1-01-design.md`（**1393 行 / 167927 B / sha12 `5616d7c4578c`**）—— **必读章节与绝对行号**：

| 章节 | 绝对行 | 你从中取什么 |
|---|---|---|
| §2.1 / §2.2 / §2.3 | 159 / 180 / 204 | 导入族 · 映射族 · multipart 字段面的**字段级** DTO 定义（落 `api/common.py`，G1） |
| §2.4 | 218 | 落库映射（列 ↔ DTO；真值来源＝切片 `ddl.*`） |
| §2.5 | 262 | DTO 落点**方案 A**（＝ G1 的授权依据；方案 B 见 §11.11，**已否决**） |
| §3 / §3.1–§3.4 | 287 / 309 / 320 / 339 / 350 | 状态机 7 态、`ImportState` 定义落点、迁移表 **I1–I7**、I8–I10 预留行（**本卡禁注册**）、非法迁移的错误映射 |
| §4.0 / §4.1 | 378 / 394 | 命题与结构性保证（**禁第二套校验器**的落地方式）、**单一入口签名**（`public_frozen`） |
| §4.2 / §4.3 | 446 / 472 | 三段职责边界（解析 → 归一 → 校验）、`NormalizedSlice` 字段与类型 |
| §4.4 | 493 | **行列定位结构**（AC-005「返回具体行列」的数据形状；**0/1-based 口径显式声明**） |
| §4.5 / §4.6 / §4.7 | 528 / 546 / 563 | **元/分归一口径（整数分）**、去重与可比性、源行与文件摘要可追溯 ＋ `validation_digest` 固定投影 |
| §4.8 | 617 | M1-P01（月报接入）的扩展点（**只预留、禁实现**） |
| §5.1 | 639 | **负例矩阵 N1–N18**（＝你 `validate.py` 的逐条 `_check_*` 函数分母） |
| §5.2 / §5.3 | 673 / 693 | 三个上限是三个不同对象（**禁新增阈值**，U-3 已裁 D16）、旧验证失效 ＋ 正式快照未被更新 |
| §6.1–§6.4 | 714 / 734 / 751 / 784 | ETag 出现面、428/412 实现口径、**判定顺序（顺序即代码顺序，禁调序）**、409/422 家族逐码触发面 |
| §7.1–§7.4 | 802 / 822 / 834 / 850 | 事务号与边界、审计（`AuditWriter` **只 import 禁改**）、显式时钟/ID 前缀/幂等键、**`infra/files.py` 文件底座** |
| §8 | 873 | 逐 op 可达码矩阵（声明面一律 12 码） |
| §9.1 / §9.2 / §9.3 | 890 / 905 / 917 | **AC-005 / AC-006 的实现约束与已知失败模式**、**本卡不承担的面**（防你越界） |
| §10 / §10.1 | 925 / 955 | 验证清单（命令 → 期望 rc；计数指向 `state.json.counts` 现值、**禁写死**）、正向对照 PC 要求 |
| **§11.1 / §11.2 / §11.3** | **982 / 998 / 1015** | **你的文件级 TODO（逐件逐符号）** —— 本棒的核心依据 |
| §11.4–§11.9 | 1038 / 1052 / 1066 / 1079 / 1098 / 1113 | S3–S8 的边界（**禁替他们干活**：`parse.py` 的三个适配器归 S3/S4，`api/imports.py` 归 S5，`tests/**` 归 S6/S7，`evidence/**` 归 S8） |
| **§11.10** | **1124** | **G1–G10 写权缺口一览表**（G1–G9 已授权给你，**G10 本卡禁写**） |
| §11.11 | 1139 | 方案 B 平移映射（**已否决**，仅供你理解为何必须走方案 A） |
| §14.1–§14.6 | 1309 / 1323 / 1336 / 1347 / 1378 / 1384 | **编排器裁定追记**：A280（`SourceMapping.id` 主键语义）· A283（`IngestLimits` 取值来源）· A285（AC-006「CSV/JSON 同值」口径）· **A292（G2 实际改法 ＋ 元守护口径迁移，订正 A281）** · A291（fixtures 路径口径） |

### 3.4 只读原件（**必须逐个实读**，你的实现要按它们的真实形状对齐体例）

| 路径 | 实测 face | 你要从中取什么 |
|---|---|---|
| `orchestrator/handoff/LANE-COMMON.md` | **120 行 / 8841 B / sha12 `3425b298a0c3`** | 公共纪律（**先读**） |
| `spec/CampaignLab-SDD-v1.0/architecture/DATA.md` | **56 行 / 7957 B / sha12 `c0aabbe60796`** | 「导入通道」「映射和标准表」「去重和可比性」 |
| `spec/CampaignLab-SDD-v1.0/framework/DATA.md` | **15 行 / 1973 B / sha12 `2a6a17c4ca48`** | 「SQLite 与迁移」「文件与 DuckDB」 |
| `spec/CampaignLab-SDD-v1.0/architecture/API.md` | **39 行 / 4136 B / sha12 `5fa2ada865c1`** | 「错误分类」409/412/422 边界 |
| `spec/CampaignLab-SDD-v1.0/architecture/DOMAIN.md` | **43 行 / 5339 B / sha12 `7e8b1778dd9e`** | 「唯一标识和精度」「内容摘要的固定投影」 |
| `spec/CampaignLab-SDD-v1.0/architecture/OPERATIONS.md` | **26 行 / 3251 B / sha12 `187cf3b2a5ab`** | 「文件处理」8 MiB 上限口径 |
| `spec/CampaignLab-SDD-v1.0/framework/PYTHON.md` | **11 行 / 1916 B / sha12 `a4502a0aab94`** | 全文（分层与事务口径） |
| `src/campaignlab/domain/errors.py` | **290 行 / 11269 B / sha12 `82af76b29015`** | `PROBLEM_CODES` 与 `DomainError` 家族（**零发明码**） |
| `src/campaignlab/worker/states.py` | **215 行 / 8353 B / sha12 `aa60b26090e1`** | `Transition` 的 8 字段体例（`ImportTransition` 必须对齐） |
| `src/campaignlab/infra/artifacts.py` | **843 行 / 36033 B / sha12 `14515bc840da`** | `ArtifactWriter.begin/seal/write/commit/discard`（`infra/files.py` 只调不改） |
| `src/campaignlab/domain/activity/digests.py` | **79 行 / 3959 B / sha12 `ca60c91c39f2`** | `canonicalize` **注入**体例（`rule_digest(…, *, canonicalize)`） |
| `src/campaignlab/application/activity_service.py` | **1999 行 / 88950 B / sha12 `21425228694b`** | 事务写法 `:620` 的 `with connect(engine) as conn, conn.begin():` |
| `src/campaignlab/application/audit.py` | **148 行 / 5066 B / sha12 `626c8733a449`** | `AuditWriter`（**只 import、禁改**、禁复制第二份链逻辑） |
| `src/campaignlab/infra/db/engine.py` | **93 行 / 3668 B / sha12 `bee5b2a0432a`** | `connect` 的 import 落点 |
| `tests/api/activities/__init__.py` | **1 行 / 89 B / sha12 `8ccc54fe0ab9`** | 包标记先例（**1 行 / 89 B**，A276 单行 docstring 形态） |
| `spec/CampaignLab-SDD-v1.0/fixtures/banks/bank-a.json` | **1 行 / 147272 B / sha12 `2c57122e202d`** | A 宽表（AC-006 的 510 切片来源） |
| `spec/CampaignLab-SDD-v1.0/fixtures/banks/bank-b.json` | **1 行 / 291343 B / sha12 `2d1d96532b78`** | B 长表（4590 阶段项来源） |
| `fixtures/banks/csv-mini/source.json` | **ABSENT** | CSV 与等价 SOURCE_JSON（A291 的路径口径报备） |
| `fixtures/analytics-golden.json` | **ABSENT** | 切片计数与元分归一黄金值 |


## 4. 冻结面实测读数（编排器于派单时点实测；你上工**必须自行复测**并贴命令原文）

### 4.1 仓面与权威 counts

| 项 | 实测值 |
|---|---|
| HEAD（派单基线） | `8a12228`（全 `8a1222837d5b197ace4dcda666668bbcd3055db6`） |
| 分支 | `m0-framework` |
| 权威 counts（派单基线时点） | **358/130/852(132py+226md)** |
| 权威 counts（本 predispatch 批入库后 ＝ 你上工时的实际基线） | **359/130/852(132py+227md)（由 harness 口径程序化派生：{"ruff_formatted_files": 359, "in_scope_py": 132, "in_scope_md": 227, "mypy_source_files": 130, "pytest_passed": 852}）**（A269：以 spawn message 逐字给出的取代后读数为准） |
| 活契约新鲜度（卡片 gate 原文要求的对账值） | `contracts/openapi.json` sha256[:16] ＝ `592571099d638251`、bytes ＝ `443309` |
| 其他 counts 现值（**禁写死，一律指向台账**） | `ruff_lint_scope_files` ＝ 75 · `contract_registered_nodes` ＝ 13 · `acceptance_denominator` ＝ 47 |

### 4.2 PRE-40 冻结面 8 件（编排器于本批 preflight **重测**，禁沿用历史批读数）

| 路径 | 锁值 sha12 | 本批重测 sha12 | 行 / 字节 | 对账 |
|---|---|---|---|---|
| `src/campaignlab/api/common.py` | `b2908617d193` | `b2908617d193` | 1186 / 47180 | **OK** |
| `src/campaignlab/api/activities.py` | `3865f3eb6b3c` | `3865f3eb6b3c` | 223 / 10121 | **OK** |
| `src/campaignlab/api/rules.py` | `eac1377a4b72` | `eac1377a4b72` | 391 / 18034 | **OK** |
| `src/campaignlab/api/jobs.py` | `e9b575602e56` | `e9b575602e56` | 372 / 16934 | **OK** |
| `tests/api/activities/__init__.py` | `8ccc54fe0ab9` | `8ccc54fe0ab9` | 1 / 89 | **OK** |
| `orchestrator/handoff/M2-01-design.md` | `2d39feaac2d1` | `2d39feaac2d1` | 1396 / 153979 | **OK** |
| `orchestrator/handoff/M1-01.slice.json` | `eadbd88e4ef7` | `eadbd88e4ef7` | 2876 / 60641 | **OK** |
| `orchestrator/handoff/M2-01.slice.json` | `8f44b036f065` | `8f44b036f065` | 4014 / 84893 | **OK** |

**DRIFT_COUNT ＝ 0**（[]）。锁值来源＝台账 `resume.checkpoint_R19_S1pause.locks`，
本批 preflight 自行重测、禁沿用历史批读数（PRE-40 / ⑲ 号 next_action 明文）。

### 4.3 你的追加面 4 件（纯追加，`deleted` 列必须为 0）与运行期符号面

| 路径 | 行 | 字节 | sha12 | 授权 | 追加约束 |
|---|---|---|---|---|---|
| `src/campaignlab/api/common.py` | 1186 | 47180 | `b2908617d193` | **G1** | 11 DTO/别名 ＋ 2 再导出 ＋ `__all__`；**0 删除行** |
| `src/campaignlab/infra/db/repositories.py` | 1884 | 82850 | `23437663c59e` | **G5** | 3 Record ＋ 3 Repo ＋ 3 `*_from_row` ＋ 3 列序常量 ＋ `__all__`；**0 删除行** |
| `src/campaignlab/api/deps.py` | 346 | 13524 | `ed1075a86447` | **G6** | 1 Protocol ＋ 1 提供器 ＋ `__all__`；**A233 `TYPE_CHECKING` 块形态** |
| `src/campaignlab/api/app.py` | 178 | 7857 | `2e4aad126172` | **G7** | **总追加 ≤ 4 行**（A90① / A10 最小例外）；**0 删除行** |


运行期符号面（编排器以 `uv run --no-sync python` **实取**；你须在 V10 自行复测，**禁写死**）：

| 量 | 实测值 | 口径 |
|---|---|---|
| `len(common.__all__)` | **80** | A292 的 `COMMON_ALL_NAMES` 钉桩名单当前项数（`test_domain_errors.py:33`） |
| `len(set(common.__all__))` | **80** | 必须与上值相等（无重复） |
| `len(deps.__all__)` | **13** | design §11.3 的 G6 追加基线 |
| `len(repositories.__all__)` | **16** | design §11.3 的 G5 追加基线 |
| `len(PROBLEM_CODES)` | **20** | **禁新增码**（§3.4：码名一律实取，零发明） |
| `DomainError` 子类数 | **14** | **禁新增子类**（§11.2 末段：本卡零新增） |


### 4.4 你的新建面**全部为空地**（编排器实测，逐项 ABSENT）

| 路径 | 派单时点实测 | 归属 |
|---|---|---|
| `src/campaignlab/domain/ingest` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/domain/ingest/__init__.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/domain/ingest/model.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/domain/ingest/states.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/domain/ingest/limits.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/domain/ingest/locate.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/domain/ingest/digests.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/domain/ingest/normalize.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/domain/ingest/validate.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/domain/ingest/parse.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/domain/ingest/api.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/infra/files.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/application/import_service.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/application/import_jobs.py` | **ABSENT** | **本棒 S2** |
| `src/campaignlab/api/imports.py` | **ABSENT** | **S5**（本棒禁建） |
| `tests/domain/ingest` | **ABSENT** | **S6**（本棒禁建） |
| `tests/golden` | **ABSENT** | **S7**（本棒禁建） |
| `tests/golden/__init__.py` | **ABSENT** | **G8 → S7**（编排器裁定后由编排器建） |
| `evidence/M1` | **ABSENT** | **S8**（本棒禁建） |

## 5. 本棒携带的裁定与义务（append-only；**不得推翻**，有异议走 §8 上报）

### 5.1 本批新裁（编排器于 predispatch 批登记，**逐字原文**）

#### A293（round 19 · task `M1-01 / M2-01` · lane `orchestrator` · at `2026-11-18T03:09:08+08:00`）

- **source**：`next_actions` ⑲ 的「并行前置」＋ **PRE-5** 三判据实测 ＋ 文档 §9「429 缓解」
- **question**：wave-4 的两棒（`M2-01/S7` 与 `M1-01/S2`）能否**并行**派发？若不能，先派哪一棒？
- **fact**：**判据③ 命中交叉 ⇒ 不可并行。**① 判据①（路径前缀集交集）：S7 写权面＝`evidence/M2/M2-01/**` ＋ `evidence/M2/summaries/M2-01.md`（`M2-01-design.md` §11.8，绝对行 1180–1190）；S2 写权面＝`tasks[M1-01].scope` 实测 **17** 项（原 8 项 ＋ A277/A290 扩围的 G1–G9），全部在 `src/campaignlab/**` 与 `orchestrator/handoff/`（零 `evidence/M2`）⇒ 交集 **∅**（PASS）。② 判据②（共享包标记 `__init__.py`）：S7 只写 `evidence/**`、不新建任何 python 包 ⇒ 无共享（PASS）。③ 判据③（共享冻结面 / 分母交叉）：**命中** —— S2 依 `M1-01-design.md` §11.2（G1）必须**纯追加** `src/campaignlab/api/common.py`，而该文件正是 **PRE-40 冻结面 8 件之一**（锁值 `b2908617d193`，本批重测未漂移）；且两棒都向 `ruff_formatted_files` 分母贡献（S7 增 ≥5 件 `.md`、S2 增 ≥13 件 `.py`）⇒ 冻结面与 counts 分母**双重交叉**。④ 环境面：本回合前曾实测 `429 Too Many Requests` 导致长程会话中断（`request id b5bd0289-…`）。
- **ruling**：**串行优先**（文档 §9「429 缓解」）：本批**只派 `M1-01/S2` 一棒**；`M2-01/S7` **递延**到 S2 入库之后另发 predispatch 批。派发顺序依据＝**关键路径**：台账实测 `tasks[M1-01]` 为 `critical=true` / `slack=0`（且 S2 是 S3–S8 六棒的前置），而 `tasks[M2-01]` 为 `critical=false` / `slack=4` ⇒ **S2 先行**。**S7 的 predispatch 批必须重测 PRE-40**（届时 `api/common.py` 的锁值将因 S2 的授权纯追加而更新，属**已授权漂移**，须同批登记新锁值）；既有义务「**S7 入库前禁判 M2-01 DONE**」不变。
- **basis**：**PRE-5**（写集不相交三判据）· 文档 §9（429 缓解）· **PRE-40**（冻结面派单前重测、禁沿用）· **A269**（基线读数取代口径）· **A261**（以 sha 为锚）· 台账实测 `critical` / `slack` · **A245 / A248**（`tests/**` lane 硬禁面，与 A294 同源）
- **action_taken**：本批（`R19-predispatch-wave4-S2`）只写 **1** 份派单文 `orchestrator/handoff/R19-lane-M1-01-S2.md`；`dispatch_log` += 1、`in_flight_agents` += 1（`agent_id`=None、`spawned_after_predispatch`=False、status=`PREDISPATCH_COMMITTED_AWAITING_SPAWN`）、`budget.dispatched_not_yet_returned` 0 → **1**；派单文 §0 的「并行对象」栏明文写「**无 —— 本棒串行独占**」；`M2-01/S7` 的派单义务与「S2 入库批同批更新 PRE-40 锁值」一并转记入 `next_actions` 新条目 ⑳。

#### A294（round 19 · task `M1-01` · lane `orchestrator` · at `2026-11-18T03:09:08+08:00`）

- **source**：编排器于本批 preflight 的**实测对撞**：`M1-01-design.md` §11.2（G1 纯追加 `api/common.py`）× **A292** 落地的 `COMMON_ALL_NAMES` 名单对撞 × **A245 / A248**（`tests/**` 是 lane 硬禁面）
- **question**：S2 依 §11.2 向 `api/common.py` 纯追加 11 个 DTO/别名 ＋ 2 个 domain Literal 再导出并全部进 `__all__` 后，A292 落地的 `tests/unit/test_domain_errors.py:278` 名单对撞（`set(common.__all__) == set(COMMON_ALL_NAMES)`，名单在 `:33`）**必判红**；而 `tests/**` 是 lane 硬禁面、元守护又已把「硬编码计数钉桩」上限制钉到 **0**（A115 机器化）⇒ 该红**由谁消除、以何口径消除**？
- **fact**：**实测四项。**① `tests/unit/test_domain_errors.py` ＝ **301 行 / 11993 B / sha12 `e4a9fec29c20`**；`:33` 定义 `COMMON_ALL_NAMES: Final = (...)`、`:278` 做集合对撞并附 `only_runtime` / `only_pinned` 双向差集报信。② 运行期实取（`uv run --no-sync python`）：`len(common.__all__)` ＝ **80**（uniq **80**）、`len(deps.__all__)` ＝ **13**、`len(repositories.__all__)` ＝ **16**、`len(PROBLEM_CODES)` ＝ **20**、`DomainError` 子类 ＝ **14**。③ 元守护 `tests/unit/test_if_match_pattern_single_source.py` 实测 `:324 ALL_COUNT_PIN_SITES_CEILING = 0`、`:328 LIVE_COLLISION_MARKER`（拼接形态防自指）、`:329 LIVE_COLLISION_SITES_FLOOR = 1`、`:383` 阳性对照 ⇒ **lane 既不能靠改数字（上限制 0）、也不能靠删守护（下界制 ≥1）变绿**。④ `api/common.py` 是 **PRE-40 冻结面之一**（`b2908617d193`，1186 行 / 47180 B）⇒ S2 的纯追加会使该锁值漂移，属 **G1 已授权**的漂移。
- **ruling**：**三条同批生效。**① 该红是**编排器预裁的授权红**（PRE-14 口径）：S2 交付时 `uv run --no-sync pytest -q` **允许且只允许这 1 条**失败；lane **禁**改 `tests/**` 任何一行、**禁**为过测改测试期望（卡片红线原文）。② S2 必须在回执 **R-A294** 项给出**实测三值**（追加后 `len(common.__all__)`、`len(set(common.__all__))`）与 `only_runtime` / `only_pinned` 的**逐字排序清单**；其中 `only_pinned` **期望为空** —— **若非空即判红**，因为 G1 只授权**纯追加**（`only_pinned` 非空意味着既有名字被删/被改名，违反 A82 的 0 删除行）。③ **编排器在 S2 的入库批同批**用 `only_runtime` **程序化再生** `COMMON_ALL_NAMES`（PRE-37 第 1 款：禁手打；体例＝A292 既有生成方式），并在**冻结索引树**上重跑四门、以再生后的绿灯背书 counts；该再生属**编排器自办**（A245 / A248 先例），**不消耗** S2 的 loop 轮次、也**不**记为 S2 的缺陷。
- **basis**：**A292**（名单对撞 ＋ 元守护双制）· **A115**（禁写死符号面计数）· **A245 / A248**（`tests/**` lane 硬禁面 ⇒ 编排器自办）· **A82** ＋ **G1**（纯追加、0 删除行）· **PRE-14**（预期红清单必须实测）· **PRE-37**（期望值程序化派生）· **PRE-44**（判据同口径 ＋ 阳性/阴性对照）· **A183**（禁猜测值）· **D-044**（禁靠改名绕过守护）
- **action_taken**：本批把该授权红写进派单文 **§1.6**（专段）与 **§2** 预期红清单第 1 行、把回执义务写进 **§10** 的 **R-A294** 项、把 **V6**（元守护）与 **V10**（运行期三值实取）两门写进 **§7**；并把「S2 入库批同批程序化再生 `COMMON_ALL_NAMES`」登记为编排器**待办义务** ＝ 新单 **FU-69** ＋ `next_actions` ⑳ 的第 1 项（`counters_next.followup` FU-69 → **FU-70**）。



### 5.2 承前批裁定 A277–A292（**逐字原文**，取自台账 `resume.round19_adjudications`；禁只记编号、禁二手复述）

> 说明：A277–A290 源于 S1 设计文 §12 的 **U-1…U-15** 未决问题，已由编排器**全部裁毕**（S1 的
> `RESULT = DONE_WITH_GAP` 的 GAP 已闭合）；A291 是 fixtures 路径口径报备（**不阻塞**）；
> **A292 订正了 A281**（其 `fact` 面「保留一处即可满足下界」经实测不成立）⇒ 二者冲突时**以 A292 为准**。

#### A277（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-1（行 1152-1161）
- **question**：§11.10 的 G1–G7 七件写权缺口（`api/common.py` · `tests/unit/test_domain_errors.py` · `application/import_service.py` · `application/import_jobs.py` · `infra/db/repositories.py` · `api/deps.py` · `api/app.py`）超出卡片 `M1-01.md:22` 的 `scope_allow` 字面量，如何处置？候选 A＝按 §11.10 扩围、七件全部授权给 S2（max）并同步 `tasks.M1-01.scope`；候选 B＝启用 §11.11 的零扩围回退方案（DTO 落 `api/imports.py`、service 落 `domain/ingest/service.py`）。
- **fact**：卡片 `scope_allow` 实测只给 `domain/ingest/**`、`api/imports.py`、`infra/files.py`、`tests/domain/ingest/**`、`tests/golden/ingest/**`、`orchestrator/handoff/M1-01-design.md`、`evidence/M1/**`（`tasks.M1-01.scope` 实测 **8** 项，与卡片同源）；缺上述七件则 6 个端点无法装配、SQL 无落点（A81）、DTO 无家（§2.5）。lane 另实测 **G8** `tests/golden/__init__.py`、**G9** `tests/api/imports/**` 两处缺口（§11.10 表）⇒ 合计 G1–G9。lane 倾向 A，理由：方案 B 破 A81（SQL 写点唯一）与 `framework/PYTHON.md:5` 的分层口径、需新立 ADR，且 G7（`api/app.py` 的 `include_router`）与 G8 在方案 B 下**依然**无法消除；同族先例 A91/A82/A81/A233/A90①/A231/A262/A276。
- **ruling**：**rule A：G1–G9 全部扩围授权给 S2（`qwen3.8-max`）**，并同步 `tasks.M1-01.scope`。**否决 plan B**（把缺口分派给 S3–S8）—— B 会破坏 A81 分层与棒的写权单一性，且 G7/G8 在 flash 棒上不可解。
- **basis**：A262（同型缺口先例）· A276（包标记形态）· A81 分层 · PRE-34
- **action_taken**：改 `tasks.M1-01.scope`（与 A290 同批）；S2 派单文 §1 的写权面逐条点名 G1–G9。

#### A278（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-2（行 1162-1169）
- **question**：卡片 `M1-01.md:18` 的 gate `pytest -q tests/integration/jobs -k validate_import` 实测 NO_TEETH，如何补牙？候选 A＝由 M0-04 lane（或编排器直接）在 `tests/integration/jobs/**` 内预置具名用例；候选 B＝把该集成用例的写权扩给 M1-01。
- **fact**：design §10 V5 本轮实测：`--collect-only` 输出 `no tests collected (98 deselected) in 0.05s`、**rc=0** ⇒ 该 gate **空转即绿**，无法证明「202 作业语义复用 M0-04 底座」。卡片 `:18` 原文「该用例文件归 M0-04 lane，本任务只跑不改；失败即回报」；`tests/integration/jobs/**` 在 M0-04 的 scope 内（G10：本卡禁写）。M0-04 实测 `status=DONE`。lane 倾向 A。
- **ruling**：**rule A**：由 **M0-04 / 编排器**预置具名用例 `test_validate_import_accepts_and_returns_202_with_location` 到 `tests/integration/jobs/**`（开新单 **FU-67**）；**补牙之前 S8 一律标 `NO_TEETH`，禁标 PASS**。
- **basis**：PRE-33（判据必须有牙）· PRE-34（rc=0 / 0 collected ≠ 通过）· C10（禁粉饰）
- **action_taken**：开 FU-67；S8 的 AC 判定表加 `NO_TEETH` 态；落点随 A289 一并确定。

#### A279（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-3（行 1170-1177）
- **question**：multipart 的两个 schema（切片 `Upload` / `AttachFile`）在纯 pydantic DTO 面如何命名？候选 A＝建 `UploadFields` / `AttachFileFields`（不含 `file` 成员）＋两条对撞断言；候选 B＝建同名 `Upload` / `AttachFile`、`file` 声明为 `StrictBytes`。
- **fact**：切片实测 `Upload` / `AttachFile` 的 `file` 属性为 `{type: string, format: binary}`，无法在纯 pydantic DTO 里表达（design §2.3）。候选 B 等于强制把 8 MiB / 64 MiB 的上传体整体读进内存，直接违反 §1.2 的流式口径与 AC-005「不留半成品」，也违反 `read_body_within_limit` docstring 的既有警告（「先 `await request.body()` 全量读入再判长度等于没有上限」）。lane 倾向 A，自陈代价＝名字与切片不同名、需在对撞测试里显式记录这层映射。
- **ruling**：**rule A**：采 `UploadFields` / `AttachFileFields`（**不含** `file` 成员）＋ **两条对撞断言**：① 文本字段逐字相等；② `properties.file.format == binary` 单独断言（分离关注点）。
- **basis**：A115（禁硬编码计数、要实取对撞）· OpenAPI multipart 规范
- **action_taken**：design §11.3 的 DTO 面按此定名；S2 落契约测试。

#### A280（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-4（行 1178-1187）
- **question**：`SourceMapping.id` 由**客户端**给定（切片 `required` 含 `id`）而 `source_mappings.id` 是主键 ⇒ 主键语义与冲突处理如何定？候选 A＝客户端 id 即主键；候选 B＝忽略客户端 id、服务端一律 `new_resource_id(SOURCE_MAPPING_ID_PREFIX)` 另发主键、客户端 id 存进 `content_json`。
- **fact**：切片实测 `SourceMapping.required` 含 `id`；DDL 实测 `PRIMARY KEY(workspace_id,id)`；`architecture/DOMAIN.md`「配置内容同 ID 变更要求新 ID」＋ `architecture/DATA.md`「每次映射实际变更保存为新映射 ID」要求每次配置产生新行，且 `architecture/DATA.md`「相同银行和版本标签仅允许同摘要复用」正是候选 A 的判据原文。候选 B 会造成「DTO 里的 id ≠ 行主键」的双身份（`content_json` 是 `SourceMapping` 的 canonical 投影）。design §11.3 为此设了 `SOURCE_MAPPING_ID_PREFIX`，但契约里 `id` **必填** ⇒ 无兜底场景，该常量与「客户端 id 即主键」矛盾。既有 409 `VERSION_MISMATCH` 语义（design 行 790）可承载冲突。lane 倾向 A。
- **ruling**：**rule A**：**客户端给的 id 即主键**；同 id ＋ 同 digest ⇒ **幂等复用**既有行（不 INSERT）；同 id ＋ 异 digest ⇒ **409 `VERSION_MISMATCH`**。并**删除 §11.3 的 `SOURCE_MAPPING_ID_PREFIX`**（服务端前缀与「客户端 id 即主键」矛盾）。
- **basis**：D-019（禁凭空加错误码）· 既有 409 语义 · 幂等性口径
- **action_taken**：经 §14 文末追记删除该常量（A214 窄豁免，随 S2 predispatch 批落地）；S2 落幂等/冲突用例。

#### A281（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-5（行 1188-1194）
- **question**：G2 的改法：`tests/unit/test_domain_errors.py:176`/`:177` 钉死 `len(common.__all__) == 80`。候选 A＝把两行整数改成新的实取值（继续钉死数字）；候选 B＝改成**实取对撞**（live-set collision）彻底去掉魔数。是否需要走 CR？
- **fact**：A115 原文即「禁写死符号面计数」；元守护 `test_all_common_surface_pins_agree_with_runtime` 只要求「钉桩处数 ≥ 2 且整数一致」⇒ 候选 B 保留 `len(set(...))` 那一处的钉桩形态即可满足下界、不会让分母塌陷。`len(common.__all__)` 实测 **80**（FU-59 成果：`IF_MATCH_PATTERN` 实存且在 `__all__` 内）。`tests/**` 是 lane 的**硬禁面** ⇒ 改动只能由编排器同批做（A245/A248 先例）。lane 倾向 B，并自陈「风险：改动了他人 lane 的守护语义，需编排器确认是否要走 CR」。
- **ruling**：**rule B**：改为**实取对撞（live-set collision）**，去掉魔数。**无需开 CR** —— A115 本就禁止硬编码计数，此改是**落实既有规则**而非变更守护语义。
- **basis**：A115 · 既有守护体例 · A245 / A248（守护迁移归编排器同批）
- **action_taken**：由**编排器**改这两行；本批是零 `.py` 的 lane landing 批（禁夹带代码改动）⇒ 递延到 **S2 predispatch 批**同批落地，已写入 `next_actions`。

#### A282（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-6（行 1195-1201）
- **question**：`domain/ingest` 是否需要显式时钟？候选 A＝保持零时钟依赖（本文方案）；候选 B＝把 `clock: Clock` 也传进 `ingest()`，为将来「按导入时点判定字典版本」预留。
- **fact**：`framework/PYTHON.md:6` 的要求是「避免在领域计算内调用**系统当前时间**」，注入式时钟不是必须的；`INGEST` 面现在没有任何时点相关的判定（`cutoff` 与 `period` 的关系是纯日历算术）；时刻只用于 `created_at`（application 层）。候选 B 会让纯函数变成需要 fixture 的函数，增加 S6 的用例面而不增加覆盖。lane 倾向 A。
- **ruling**：**rule A：保持零时钟依赖**（领域层纯函数；`created_at` 一律在**应用层**注入）。若后续认定 M1-P01 的月报 append 需要时点判定，再走 §14 追记扩签名（卡片 `public_frozen` 允许「改动走 CR」）。
- **basis**：A81 分层 · 红线 3（禁墙钟 / sleep）· 可测性
- **action_taken**：design §11 明示；S2 落层界守护。

#### A283（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-7（行 1202-1208）
- **question**：`IngestLimits.max_slices = 10_000` / `max_stage_items = 90_000` 不是契约字面量，其取值来源如何认定？候选 A＝采用本文取值（有 spec 文字依据但非硬数字）；候选 B＝**不设**这两个上限、只保留 `max_findings = 1000`（← 实测 `Import.issues.maxItems`，契约字面量）。是否需另立 ADR？
- **fact**：取值依据 `framework/DATA.md`「分析基准先用甲乙各 510 切片，再生成 1 万聚合切片与 10 万事件的合成压力数据」；`OPERATIONS.md`「运行与备份」表给了「10 万行导入 ≤ 60 秒」的工程目标 ⇒ 无上限会让 8 MiB 内的病态密集 JSON（例如 100 万行 × 1 列）打穿该目标，且 413 只管字节数、管不了行数。lane 倾向 A 并自陈「这两个数属本文的设计取值」。
- **ruling**：**rule A**：认定为**设计取值**（spec 派生），**走 §14 追记**说明来源，**不另立 ADR**。
- **basis**：ADR 门槛（非跨模块架构抉择）· §14 追记体例
- **action_taken**：§14 追记一条（随 S2 predispatch 批同批落地）。

#### A284（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-8（行 1209-1214）
- **question**：「哪些金额键可为负」的划分：spec 只有一句「余额增量可为负，销量为非负」，本文据此把 12 个金额键分成 7 个变动类（可负）＋ 5 个销量类（非负，N16）。候选 A＝采用本文划分；候选 B＝**不**做非负校验、只保留「必须是整数分」（把 N16 降级为 `WARNING`）。
- **fact**：AC-005 的负例注入面已包含「负人数」，同族的「负销量」是同一类脏数据，放过会让 `analytics-golden.json` 的 `current.wealthSale == 22809600` 一类黄金值失去意义。lane 自陈风险：「若某行内真实数据存在负销量（退货冲销），A 会误判 ⇒ 需要业务确认；这是本文**无法**从 spec / 契约确定的事，故上报」。
- **ruling**：**rule A**：**7 个 variable 键可为负** ＋ **5 个 sale 键非负**（保持 N16 ERROR）。**退货冲销**的业务确认开新单 **FU-68**（不阻塞本棒）。
- **basis**：业务口径未定 ⇒ 禁自行裁定业务 · C10（禁粉饰）
- **action_taken**：开 FU-68；design §11 标注两类的符号约束。

#### A285（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-9（行 1215-1221）
- **question**：AC-006 的「CSV/JSON 同值」是否包含 `validation_digest` 同值？候选 A＝接受本文口径（「同值」指归一后的业务值与元数据投影，不含文件摘要）；候选 B＝把 `files` 段从 `validation_digest` 的投影里去掉，只留 `mapping_digest` ＋ `metadata_digest` ＋ `parser_version`。
- **fact**：design 实测并冻结：CSV 通道与 SOURCE_JSON 通道的**切片值**与 **`metadata_digest`** 相同，但 `validation_digest` 的 `files` 段含**原字节 SHA**，CSV 通道（2 个上传件）与 SOURCE_JSON 通道（1 个上传件）必然不同 ⇒ `validation_digest` **不相同**。`architecture/DATA.md` 原文「校验摘要覆盖**文件原始 SHA**、映射内容、元数据及解析器版本」是硬要求 ⇒ 候选 B 直接违反 spec；且「新发布时校验摘要必须仍匹配」的安全性正依赖文件 SHA 入摘要（换文件必须重校验）。lane 倾向 A。
- **ruling**：**rule A**：同值 ＝ **归一化业务值 ＋ `metadata_digest`**；**排除 `validation_digest`** —— 其 `files` 段含原字节 SHA，跨通道必然不同，要求同值即逻辑不可能。
- **basis**：AC-006 原文 · digest 口径定义 · `architecture/DATA.md`
- **action_taken**：S8 判 AC-006 时按此口径；design §10 标注；§14 追记口径。

#### A286（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-10（行 1222-1228）
- **question**：「未知切片」与「孤立切片」是否同指一事（决定登记一个还是两个错误码）？候选 A＝同指一事、只登记 `ORPHAN_SLICE`；候选 B＝分成 `ORPHAN_SLICE`（长表有、实体表无）与 `UNKNOWN_SLICE`（实体表的切片 `id` 无法被字典解析）。
- **fact**：AC-005 说 B 注入「重复码及孤立切片」；`architecture/DATA.md`「映射和标准表」段说「未知切片、重复码、缺必填阶段、映射引用不存在列均报错」。lane 实测找不到 spec 里「实体表切片 id 无法被字典解析」的独立语义（`id` 是切片号，实测形如 `2025-09:B01:remote:1`，其可解析性已由 N11 `UNKNOWN_DICTIONARY_REF` 覆盖 `branch` / `channel` 分量）；凭空多一个码会违反 D-019 的精神。lane 倾向 A。
- **ruling**：**rule A：同指一事** ⇒ 只登记 **`ORPHAN_SLICE`** 一个码。（N11 的 `UNKNOWN_DICTIONARY_REF` 覆盖的是**字典解析**，不是切片归属。）
- **basis**：D-019（禁凭空加码）· 既有 PROBLEM_CODES 冻结面
- **action_taken**：design §11 统一用 `ORPHAN_SLICE`。

#### A287（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-11（行 1229-1236）
- **question**：导入上传件的暂存目录名不副实（`ArtifactWriter.begin(workspace_id, job_id, attempt)` 的暂存根实测为 `<data_dir>/tmp/jobs`，而 `infra/artifacts.py` 在卡片 `scope_deny` 内）：候选 A＝传 `job_id=<import_id>`、接受暂存落 `tmp/jobs/**`；候选 B＝`infra/files.py` 自建 `<data_dir>/tmp/imports/**` 暂存与清理。`job_id` 如何传参？
- **fact**：`stage_root` docstring 原文实测暂存根为 `<data_dir>/tmp/jobs`。候选 B 需在 `infra/files.py` 里复制一份「原子重命名 ＋ 同文件系统校验 ＋ 超期清理」逻辑（实测 `artifacts.py` 的 `verify_same_filesystem` / `sweep_unreferenced` / `_prune_empty_dirs` 共约 **200 行**），属「第二份实现」；且既有 `sweep_unreferenced` **不扫** `tmp/imports/**`（实测扫描面「只有 `results/**` 与 `tmp/jobs/**`」）⇒ 会留下永远没人回收的垃圾目录。lane 倾向 A。
- **ruling**：**rule A**：传 `job_id = <import_id>`，**接受暂存落 `tmp/jobs/**`** —— 换来 `sweep_unreferenced` 的既有保护，避免重复实现 ~200 行清理逻辑。
- **basis**：复用优先 · `infra/files.py` 既有能力
- **action_taken**：design §11.3 固化；S2 落清理守护。

#### A288（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-12（行 1237-1243）
- **question**：`SourceRow.source_file_id` 指向哪张表？候选 A＝`import_files.id`（`imf` 前缀）；候选 B＝`artifacts.id`（`art` 前缀，更贴近「文件」字面）。
- **fact**：`architecture/DATA.md` 原文只说「source_row 由导入器生成，含 source_file_id、table_name、row_number」，**未指明表**。候选 A 下 `table_name` 与 `import_files` 同表 ⇒ 三元组自洽；候选 B 下同一份内容被两个导入复用时 `artifact_id` 会相同 ⇒ `source_file_id` 失去「哪一次导入的哪一个上传件」的区分力（实测 `CommittedArtifact.reused_file` / `reused_row` 就是为内容寻址复用而存在）。可追溯性的目的是「从页面上的一个数追回到**这次导入**的这一行」。lane 倾向 A。
- **ruling**：**rule A**：指向 **`import_files.id`**。（若指向内容寻址的 `artifacts.id`，在**复用**场景下会产生歧义。）
- **basis**：数据模型无歧义原则 · `architecture/DATA.md`
- **action_taken**：design §11.3 / DDL 面对齐。

#### A289（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-13（行 1244-1252）
- **question**：`VALIDATE_IMPORT` 作业处理器的实现落点与注册落点（`worker/runner.py::HandlerRegistry` 在 `scope_deny` 内，M0-04 的设计原文是「**src 内不放业务 handler**，测试在 conftest 注册桩」）；**附带问题**：该作业是「同进程内跑」还是「独立 worker 跑」？
- **fact**：候选 A＝实现落 `application/import_jobs.py`、注册落 `api/app.py` 装配面（G7 的同一处最小例外，实测 `api/app.py` 已有 `include_router` 的最小例外先例）；候选 B＝注册落 `worker/deps.py` 的 `registry` 构造处（需改 `worker/**` ＝ `scope_deny`）⇒ B 直接违反卡片。候选 A 与 M0-04 的「src 内不放业务 handler」并不冲突（业务 handler 住 `application/`，装配面只做注册）。lane 明确指出：若注册只在 `create_app()` 内生效，则**独立 worker 进程**看不到该 handler，而这决定 I5/I6/I7 的集成用例落点、也影响 U-2 的补牙方案。lane 倾向 A。
- **ruling**：**rule A**：实现落 **`application/import_jobs.py`**，注册落 **`api/app.py` 装配面**（G7 的**最小例外**）。**并裁定该作业「同进程内跑」**（独立 worker 进程**不在本卡 scope**）⇒ 连带确定 I5/I6/I7 集成用例落点与 U-2 的补牙位置。
- **basis**：A81 分层 · A217 ③（装配面归属）· scope 边界
- **action_taken**：design §11.3 / §11.7 固化；FU-67 的落点随之确定（`tests/integration/jobs/**`）。

#### A290（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-14（行 1253-1260）
- **question**：HTTP 面用例（design §10 V8）放哪？卡片 `scope_allow` 只给了 `tests/domain/ingest/**` 与 `tests/golden/ingest/**`，**没有** `tests/api/imports/**`。候选 A＝扩围新建 `tests/api/imports/**`；候选 B＝把路由面用例塞进 `tests/domain/ingest/**`（用 `TestClient`）。
- **fact**：§1/§6/§8 的路由面（6 个 op 的 `operation_id`、`declared_responses` vs 切片、428/412 的可达性、逐 op 可达码矩阵）**必须**有 HTTP 层用例才算有牙。同族先例：M2-01 的 `tests/api/activities/**` 实测已存在且 `__init__.py` ＝ 1 行 / 89 B。候选 B 会让「领域层测试目录」里出现 HTTP 客户端与 DB fixture，破坏 `tests/` 的分层约定（实测 `tests/` 下 `api/ domain/ integration/ unit/` 四分），也会让卡片 `:15`/`:16`/`:17` 的 `-k locate` / `-k size_limit` / `-k csv_equivalence` / `-k stale_validation` 意外命中 HTTP 用例、**污染 `-k` 的分母**。lane 倾向 A。
- **ruling**：**rule A：扩围新建 `tests/api/imports/**`**（新目录 ＋ `__init__.py` ＋ `conftest.py`；同族先例 `tests/api/activities/**`）。**否决**把 TestClient 塞进领域层测试 —— 会污染 `-k` 的分母。
- **basis**：A276（包标记形态）· S6 先例 · PRE-34
- **action_taken**：`tasks.M1-01.scope` 同步（与 A277 同批）。

#### A291（round 19 · task `M1-01` · lane `S1` · at `2026-11-18T00:01:08+08:00`）

- **source**：orchestrator/handoff/M1-01-design.md §12 U-15（行 1261-1269）
- **question**：派单文 §3.3 与卡片 `inputs:` 里的 fixtures 路径（`fixtures/banks/bank-a.json` / `fixtures/analytics-golden.json`）是简写，还是需新建顶层 `fixtures/`？候选 A＝认定为简写、一律用实测全路径；候选 B＝新建顶层 `fixtures/` 软链或副本。
- **fact**：仓库**没有**顶层 `fixtures/` 目录；`find` 实测真实路径为 `spec/CampaignLab-SDD-v1.0/fixtures/**`（`./spec/CampaignLab-SDD-v1.0/fixtures/analytics-golden.json`、`.../fixtures/banks/bank-a.json`、`.../fixtures/banks/csv-mini/slices.csv`）。卡片 `inputs:` 自己就混用了两种写法（`bank-a.json` 给了全前缀，`csv-mini/*` 与 `analytics-golden.json` 给了简写）；且 `spec/**` 是只读硬禁面 ⇒ 候选 B 需动 `spec/**` 或在仓根新建目录，两者都不该由本卡发起。lane 已按 A 处理、仅报备口径差异、不阻塞。
- **ruling**：**rule A**：认定为**简写**，一律使用实测全路径 **`spec/CampaignLab-SDD-v1.0/fixtures/**`**。**仅口径报备、不阻塞**。
- **basis**：PRE-37 第 1 款（用实测路径）
- **action_taken**：派单文口径注记；S2–S8 的派单文一律用全路径。

#### A292（round 19 · task `M1-01` · lane `orchestrator` · at `2026-11-18T01:37:10+08:00`）

- **source**：`next_actions` ⑱ 的「同批落地两件事」之二（A281）＋ 编排器实测复核
- **question**：A281 裁定「`tests/unit/test_domain_errors.py:176/:177` 的硬编码计数钉桩**保留一处**即可满足元守护`ALL_COUNT_PIN_SITES_FLOOR = 2` 的下界制」是否成立？若不成立，元守护的「钉桩处数 >= 下界」口径与 **A115**（禁写死符号面计数）能否兼得？
- **fact**：**实测不成立。**① 全仓 `len(<common 别名>.__all__) == <整数>` 形态的硬编码计数钉桩**只有 2 处**，恰是 `test_domain_errors.py:176/:177`（本批 preflight Q17 以 `PIN_RE` 全仓 `ls-files *.py` 扫描程序化复核，结果 == []）⇒ 「保留一处」⇒ 处数 1 < 下界 2 ⇒ **仍判红**；「全删」⇒ 处数 0 < 下界 2 ⇒ 亦判红。即**去掉魔数即分母塌陷、保留魔数即违 A115，二者不可兼得**（A281 的 `fact` 面失真）。② 另实测 `common.__all__` = **80** 名且无重复（Q23），但 `api/common.py` 的**顶层公开绑定不是 `__all__` 的子集** —— 有 **10** 名在外（Q23b 以 AST 顶层绑定程序化枚举，逐字等于 `CURSOR_TAG_HEX_LENGTH` / `JobKind` / `JobState` / `NoteStr` / `ObjectKind` / `REPLAYED_HEADERS` / `RevisionInt` / `Role` / `SourceClass` / `request_id_of`）⇒ 「顶层绑定 ⊆ `__all__`」这一**看似更强**的对撞口径**当下即假、禁采**（采之即常驻假红）。③ 无任何测试钉 design sha（已普查）；`mypy` 为 `strict = true` ⇒ 集合对撞一律写 `set(...) == set(...)`，禁 `set` vs `frozenset` 混比。
- **ruling**：**三条同批落地**：① `:176/:177` 的「写死项数」改为与 **`COMMON_ALL_NAMES` 显式名单对撞**（名单由 `common.__all__` **程序化生成** 80 名，禁手打 —— PRE-37 第 1 款），断言形如 `set(common.__all__) == set(COMMON_ALL_NAMES)` 并附 `only_runtime` / `only_pinned` 双向差集报信；② 元守护 `test_all_common_surface_pins_agree_with_runtime` **迁移为双制**：**上限制**（硬编码计数钉桩处数 <= `ALL_COUNT_PIN_SITES_CEILING` ＝ **0**，即 A115 的机器化）＋ **实取对撞下界制**（带 `LIVE_COLLISION_MARKER` 的守护位点数 >= `LIVE_COLLISION_SITES_FLOOR` ＝ **1**，**保住原下界制的牙**：禁靠删守护变绿）；标记串在元守护文件内**只以拼接形态**出现（`"common-surface-live" + "-collision"`）以防**自指**把自己扫成守护位点；③ 阳性对照同步迁移（合成钉桩必须被判违规）**并新增阴性对照**（不含标记串的源不得扫出守护位点，防「恒判有」型假牙 —— PRE-44①⑤）。**函数名沿用不改**（D-044 体例：改名会打断 `tests/integration/jobs/test_jobs_router_s4.py:346` 的交叉引用），语义升级写进 docstring。
- **basis**：**A115**（禁写死符号面计数）· **A281**（本条订正其 `fact` 面，裁定面被取代）· **A214**（design 只追加窄豁免）· **PRE-37**（期望值程序化派生）· **PRE-44**（判据同口径 ＋ 阳性/阴性对照）· **D-011**（台账 append-only，历史归因段逐字不改写）· **D-044**（函数名/文档与断言体不得自相矛盾）· **A245 / A248**（`tests/**` 是 lane 硬禁面 ⇒ 本改造由**编排器自办**）
- **action_taken**：本批（`R19-A292-O8`）由编排器自办落地：`test_domain_errors.py` 194L/8205B/`ff4c25a659b6` → 301L/11993B/`e4a9fec29c20`；`test_if_match_pattern_single_source.py` 354L/16753B/`6fa13556ab67` → 387L/18954B/`e063307487d3`；O-8 同批把 A280 / A283 / A285 / A292 / A291 追记进 `M1-01-design.md` §14（1301L/159632B/`99dd191f43b3` → 1393L/167927B/`5616d7c4578c`，`numstat` = 92/**0**、前 1301 行 sha256[:12] 双向核验相等）。**pytest 分母不变**（测试函数名单守恒 10 / 11，Q18）、**counts 五项逐字不变**（零新增文件，Q03b）。落地过程另生 **1 处自纠 R19-26**（编辑脚本产出 4 处 E501，ruff 口径＝East-Asian 显示宽度）。



### 5.3 更早的通用立规（**逐字义务**，本棒同样适用）

- **A81**：SQL 写点唯一（`infra/db/repositories.py`）⇒ 领域层 `domain/ingest/**` **零 SQL**。
- **A82**：对 `api/common.py` / `repositories.py` 只允许「纯追加、0 删除行」处置。
- **A90① / A10**：`api/app.py` 的最小例外（**≤3 行**为原体例，本棒经 §11.3 放宽到**总追加 ≤ 4 行**、0 删除行）。
- **A91**：`api/common.py` 的 append-only 追加先例（`JobPage` 由 M0-04/S4 追加）。
- **A115**：**禁写死符号面计数**（元守护已把上限制钉到 **0**，你新增任何硬编码计数钉桩都会被判违规）。
- **A161**：在飞污染 —— `git status` 出现非你写权面的第三方面，**禁碰**、立即上报。
- **A171**：真值来源口径 —— DTO 字段行末的 `←` 即切片路径，一律实取。
- **A175**：`ruff format` 的作用域**含 `.md`**。
- **A183**：**禁写猜测值**（凡你无法实测的量，回执里写 `null` 并说明缺失句柄，禁估算填充）。
- **A214**：design 文只追加窄豁免 —— 本棒**零** design 写权（§1.4），该条只约束编排器。
- **A218 / A231 / A233**：`__all__` 追加授权与 `TYPE_CHECKING` 块形态（G6 必须采此形态规避 ruff `I001`）。
- **A245 / A248**：**`tests/**` 是 lane 硬禁面** ⇒ 凡需改测试一律由编排器自办（本棒的 A294 即由此而来）。
- **A254 / A257 / A260 / A261 / A269 / A270**：阻断接线归 M5-01 · 契约声明面授权 · 以 **sha** 为锚 ·
  基线读数取代口径 · 窗口期风险（A270 的守护你可直接引用）。
- **A262 / A276**：包标记形态（**单行 docstring**，禁零字节空文件）。
- **D-011**：台账 append-only（历史归因段逐字不改写）。**D-012 / D-014**：指纹与字节数**不写进卡片**，
  一律指向台账现值。**D-044**：函数名/文档与断言体不得自相矛盾（**禁靠改名绕过守护**）。
- **PRE-24**：引用仓内既有符号必须做**实存对撞**并贴命令原文。
- **PRE-29**：双向禁采信（禁采信本文，也禁采信你自己的记忆）。
- **PRE-37**：期望值**程序化派生**，禁手打。
- **PRE-39**：lane 侧 scratch 前缀 `orch_` ＋ 取证件编码四判据。
- **PRE-44**：判据**同口径** ＋ 阳性/阴性对照（你的守护用例必须能被证伪）。
- **FU-54 / FU-64 / FU-67**：FU-64 ＝ 禁引用 `M2-01-design.md:215` 的失真句；**FU-67 与本棒无关但须在 S8 入库批前闭合**
  （否则 `-k validate_import` 门只能标 `NO_TEETH`）；FU-61 保持 OPEN（token 计量句柄缺失）。

## 6. 交付面（缺件即判 PARTIAL；**禁**替 S3–S8 干活）

1. **§1.1 的 11 件新建**（`domain/ingest/**` 10 件 ＋ `infra/files.py`），符号清单逐字对齐 design §11.1。
2. **§1.2 的 2 件新建**（`application/import_service.py` · `application/import_jobs.py`），符号清单对齐 §11.3。
3. **§1.3 的 4 件纯追加**（`api/common.py` · `infra/db/repositories.py` · `api/deps.py` · `api/app.py`），
   `git diff --numstat` 的 **`deleted` 列必须全 0**，`api/app.py` **总追加 ≤ 4 行**。
4. `validate.py` 必须为 design §5.1 的 **N1–N18 逐条**提供一个私有 `_check_*` 函数
   （函数名后缀用码名的小写 —— §11.1 原文要求，便于 S6 的参数化用例与 AST 守护定位）。
5. `normalize.py` 的 `layout` 分支**恰 1 处**（§11.1 原文）；`parse.py` 只落**骨架与注册表**
   `PARSE_ADAPTERS`（三个 `parse_*` 适配器实体**归 S3/S4**，你**禁**实现它们，也**禁**留 `NotImplementedError` 以外的假实现）。
6. `api.py` 的 `parse` / `ingest` 是 **`public_frozen`** 面（卡片 `:24`：M1-P01 只能经此扩展、禁改签名）⇒ 签名逐字按 §4.1。
7. `infra/files.py` **零 DML**：只调 `ArtifactWriter.begin/seal/write/commit/discard` 与 `ArtifactRepository`；
   必须落实卡片红线「不把 duckdb 关系导入绕过 `infra/files.py` 的摘要登记」。
8. **AC-005 / AC-006 的判定不在本棒**（归 S8）⇒ 你**禁**写 `evidence/**`、**禁**在回执里宣称 AC 已通过。
   本棒的验收口径是「实现面与 design 冻结签名逐字相符 ＋ 四门除 A294 授权红外全绿」。

## 7. 门（rc 必须全 0，除 §1.6 / §2 的 **A294 授权红**；命令原文与输出尾部**逐字**贴进回执，禁只写「通过」）

```bash
# V0 基线自证（不等即停手；除 A269 预裁的编排器自身提交外报 U-BASELINE）
git rev-parse --short HEAD && git rev-parse HEAD && git branch --show-current && git status --porcelain

# V1 你的 face 自证（逐件：行数 / 字节 / sha256[:12]）—— 新建 13 件 ＋ 追加 4 件
wc -lc src/campaignlab/domain/ingest/*.py src/campaignlab/infra/files.py \
       src/campaignlab/application/import_service.py src/campaignlab/application/import_jobs.py
sha256sum src/campaignlab/domain/ingest/*.py src/campaignlab/infra/files.py

# V2 编码四判据（PRE-39；file -bi 必须含 charset=utf-8；BOM / CR / 尾换行逐项）
file -bi src/campaignlab/domain/ingest/model.py
grep -c $'\r' src/campaignlab/domain/ingest/*.py src/campaignlab/infra/files.py || true

# V3 ruff（你的头号门之一：A175 —— format 的作用域含 .md）
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .

# V4 mypy 全仓（分母**会变**：报你实测的 N source files，禁写死 130）
uv run --no-sync mypy

# V5 全量 pytest（**期望 1 条红 ＝ A294 授权红**；其余必须全绿。贴出失败用例全名与 only_runtime/only_pinned 差集原文）
uv run --no-sync pytest -q

# V6 A115 元守护（禁新增硬编码计数钉桩；上限制 == 0、实取对撞下界制 >= 1）
uv run --no-sync pytest -q tests/unit/test_if_match_pattern_single_source.py

# V7 契约门禁未回归 ＋ 切片新鲜度（卡片 gate 原文）
uv run --no-sync python scripts/check_contracts.py check --validate
uv run --no-sync python -c 'import hashlib,pathlib;d=pathlib.Path("contracts/openapi.json").read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))'

# V8 硬禁面零改动（tests/** 必须**零命中**；numstat 的 deleted 列必须全 0）
git status --porcelain
git diff --numstat
git diff --numstat -- tests/ orchestrator/ spec/ contracts/ scripts/ migrations/ worker/ web/ qa-reports/

# V9 领域层零上行依赖（A81 / §11.1 抬头：禁 SQL、禁事务、禁 import campaignlab.api）
grep -rn -e campaignlab.api -e sqlalchemy -e conn.begin src/campaignlab/domain/ingest/ || echo NO_UPWARD_DEP

# V10 运行期符号面实取（禁写死；这三值是编排器再生 COMMON_ALL_NAMES 的唯一输入）
uv run --no-sync python -c 'from campaignlab.api import common,deps;from campaignlab.infra.db import repositories as r;print(len(common.__all__),len(deps.__all__),len(r.__all__))'

# V11 卡片 gate 的 6 条命令（**本棒多数为 NOT_APPLICABLE_YET**：用例面归 S6/S7）
uv run --no-sync pytest -q tests/golden/ingest -k counts
uv run --no-sync pytest -q tests/domain/ingest -k locate
uv run --no-sync pytest -q tests/domain/ingest -k size_limit
uv run --no-sync pytest -q tests/domain/ingest -k csv_equivalence -k stale_validation
uv run --no-sync pytest -q tests/integration/jobs -k validate_import
```

### 7.1 V11 的判读口径（**禁**把 NOT_APPLICABLE_YET 谎报为 PASS）

`tests/golden/ingest`（归 **S7**）与 `tests/domain/ingest`（归 **S6**）在本棒**尚不存在** ⇒ 这 4 条命令**必然非 0**
（路径不存在 / 零用例收集）。回执里一律标 **`NOT_APPLICABLE_YET`** 并贴**实测 rc 与输出尾部**，
**禁标 PASS、禁自建这些目录、禁写占位用例**（那会侵入 S6/S7 的写权面）。
`tests/integration/jobs -k validate_import` 属 **M0-04** 写权面（G10 **本卡禁写**）：**只跑不改**，
如实报 rc ＋ 收集到的用例数；若为 0 例即标 **`NO_TEETH`**（**FU-67** 的既有诊断，禁标 PASS）。

### 7.2 门与 AC 的对应

**AC-005 / AC-006 的判定归 S8**（design §11.9）。本棒的门只证明「实现面自洽 ＋ 未回归」，
**禁**在回执里写「AC-005 通过」。

## 8. U 项上报（**禁自行裁定**；手册 §6.4）

遇到下列情形**立即停手**并在回执写 `U-<n>` ＋ 两个候选 ＋ 你的倾向及理由：

1. design §11.1–§11.3 的符号清单与切片/既有代码**实测冲突**（例如字段序对不上、`Transition` 字段数不是 8）。
2. 需要动 §1.4 硬禁面的任何一件（含 `tests/**`、`api/imports.py`、`worker/**`、`M1-01-design.md`）。
3. 需要新增 `DomainError` 子类或 `PROBLEM_CODES` 码（**零发明**是硬约束）。
4. 需要新增阈值/上限（§5.2 已裁 D16：三个上限是三个不同对象，**禁新增**）。
5. 出现第 2 条非授权红（§1.6 只授权 1 条）。
6. HEAD 漂移且不属 A269 预裁范围（报 `U-BASELINE`）。
7. `git status` 出现非你写权面的第三方面（报 `U-POLLUTION`，A161）。

**loop 纪律**：上限 **2** 轮。第 2 轮仍红 ⇒ 写 **BLOCKER** ＋ 附「缩小范围」的降级交付选项
（例如只交 §1.1 的 11 件、把 §1.2/§1.3 的 6 件退回编排器），**禁**靠削弱断言或改测试期望变绿。

## 9. 派单前置自检（编排器已逐项做完；你只需在回执里**复述结论 ＋ 贴你自己的复测命令**，禁跳过）

| # | 前置项 | 编排器实测结论 |
|---|---|---|
| 1 | 派单基线 HEAD | `8a12228`（全 `8a1222837d5b197ace4dcda666668bbcd3055db6`）、分支 `m0-framework`、`git status --porcelain` 为空 |
| 2 | **PRE-40** 冻结面 8 件重测 | **DRIFT_COUNT ＝ 0**（[]） |
| 3 | **PRE-5** 三判据（与候选并行棒 M2-01/S7 对撞） | 判据① 前缀交集 ∅ ✓；判据② 无共享包标记 ✓；判据③ **命中交叉**（共享冻结面 `src/campaignlab/api/common.py` ＋ 共享 `ruff_formatted_files` 分母）⇒ **串行优先**（**A293**） |
| 4 | 依赖清偿 | `M0-04.status` ＝ **DONE**；`M1-01/S1` ＝ **DONE**（design 1393 行已入库冻结） |
| 5 | 卡片档位表（手册 §15.5：无此表不得 spawn） | `orchestrator/tasks/M1-01.md:32-49` 实测存在；S2 行原文 ＝ `qwen3.8-max` high / **45k** |
| 6 | loop_cap | **2**（卡片 `dispatch.loop_cap` 原文；依据 `critical=true` / `slack=0`，手册 §15.6 第 1 条） |
| 7 | 写权面扩围授权 | **A277（←U-1）＋ A290（←U-14）**：G1–G9 全部授权给 S2；**G10 本卡禁写**；`tasks["M1-01"].scope` 已同步为 **17** 项 |
| 8 | G2 是否已由编排器做完 | **是**（**A292** 批 `e00159b`）⇒ `tests/unit/test_domain_errors.py` 已就绪，**lane 禁再动** |
| 9 | 授权红预裁 | **A294**（`COMMON_ALL_NAMES` 漂移由编排器在入库批同批再生）⇒ 已写进 §1.6 / §2 / §7 V6·V10 / §10 R-A294 |
| 10 | **A269** 基线取代预裁 | U-BASELINE 已预裁关闭：本 predispatch 批入库后 counts 由 358/130/852(132py+226md) → **359**，以 spawn message 逐字给出的取代后读数为准 |
| 11 | **PRE-47** 台账 `$.updated_at` 陈旧度 | 派单前实测 `2026-11-18T03:02:10+08:00`（阈 600 s，本批 mut 末尾会刷新并末断言） |
| 12 | 悬空引用（手册 §15.3） | 本派单文实扫 `h.dangling_refs` 命中 **4** 条，全部属 `evidence/M1/**` 前向引用（已在 `forward_reference_registry` 登记、归 **S8** 闭合）⇒ 走 `allow_dangling` 白名单 |


## 10. 回执格式（**结构化**，禁散文；编排器会**独立复验**每一项，禁采信自报）

```text
RESULT: DONE | DONE_WITH_GAP | PARTIAL | BLOCKER
LOOP_USED: <n> / 2
TOKENS_SELF_ESTIMATE: <k>（无计量句柄即写 null 并说明 —— A183 禁猜测值）

[FACES]  逐件：路径 | 行数 | 字节 | sha256[:12]（新建 13 件 ＋ 追加 4 件的 numstat added/deleted）
[GATES]  逐门：V0…V11 | 命令原文 | rc | 输出尾部逐字 | 判读（PASS / NOT_APPLICABLE_YET / NO_TEETH / AUTHORIZED_RED）
[R-A294] 追加后 len(common.__all__) = ? ; len(set(...)) = ? ;
         only_runtime = [逐字排序清单] ; only_pinned = [期望空] ;
         失败用例全名 = ?（必须恰为 test_domain_errors.py 里那 1 条名单对撞用例）
[SYMBOLS] common.__all__ / deps.__all__ / repositories.__all__ 的运行期实测三值（V10 原文）
[DESIGN_CONFORMANCE] 逐件声明「与 design §11.1/§11.2/§11.3 的符号清单逐字相符」；有差即列差集并给 U 项
[BOUNDARY] tests/** 零改动自证（git status --porcelain -- tests/ 输出为空）;
           domain/ingest/** 零 SQL / 零事务 / 零 import campaignlab.api 自证（V9 原文）
[ENCODING] 四判据逐项（UTF-8 / 无 BOM / 无 CR / 尾换行）＋ file -bi 原文
[U-ITEMS] 无 | U-<n>: 问题 / 候选 A / 候选 B / 倾向及理由
[SELF_CORRECTIONS] 本轮你自己发现并修掉的缺陷（编号 + 成因 + 防再发口径）
```

**禁**：自称「全部通过」而不贴命令原文；把 `NOT_APPLICABLE_YET` 写成 `PASS`；
用估算值填 `TOKENS_SELF_ESTIMATE`（无句柄即 `null`）；在回执里判定 AC-005/AC-006。
