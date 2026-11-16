# R19 · Lane S1 · M1-01/S1 派单文 —— 归一化模型与统一规范校验设计（**关键路径 `slack=0`**）

> 公共纪律一律见 `orchestrator/handoff/LANE-COMMON.md`（**先读它**，本文不重述）。
> 权威条款：`docs/delivery/LONG-HORIZON-ORCHESTRATION.md` v1.7。冲突时**手册胜**、其次本文、再次 design/卡片。
> **PRE-29 双向禁采信**：本文一切读数都是编排器于派单时点的实测快照；你上工**必须自行复测**并贴命令原文，
> 禁采信二手复述（**包括本文件**）。回源一律走 §3 给的**绝对行号 / 路径**自读原文。

## 0. 身份 · 档位 · 边界（A261：一律以 **sha** 为锚，禁写 tag）

| 项 | 值 |
|---|---|
| 派单基线 HEAD（短 sha） | `bd7f89c` |
| 派单基线 HEAD（全 sha） | `bd7f89c127e8e38f65833dc104c7f73e797454e7` |
| 分支 | `m0-framework` |
| 任务 / 子任务 | `M1-01` / **S1**（该任务**第 1 棒**；`subtask_progress` 实测**无** M1-01 键 ⇒ 全新起棒） |
| lane 双键（PRE-31） | (`lane`=`S1`, `task`=`M1-01`)。⚠ 仓内有 `R13-lane-Z-M2-01-S1.md` 属 **M2-01** 的 S1（lane 名 `Z`）⇒ 与本棒**无关**，禁混用其口径 |
| 档位 / reasoning | **`qwen3.8-max`** / `high`（任务卡 `orchestrator/tasks/M1-01.md:36` 档位表原文：S1 = 55k / `qwen3.8-max` high；命中手册 §6.3 强制 max 硬规则＝状态机 ＋ 口径/分母语义 ＋ 归一化算法设计） |
| loop 上限 | **2** 轮（卡片 `dispatch.loop_cap` 原文：依据 `critical=true`、`slack=0`，手册 §15.6 第 1 条）。第 2 轮仍红即写 **BLOCKER** 并附「缩小范围」降级交付选项 |
| token 预算 | **55k**（卡片档位表原值） |
| critical / slack | **`critical=true` / `slack=0`**（台账实测）⇒ **你在关键路径上**。卡片原文警告：「M1-01 卡住会同时锁死 L1 lane 与 wave4 的 M1-P01，须**优先上报**」 |
| 依赖 | `M0-04` —— 编排器实测 **`status=DONE`**、`subtask_progress` 12 个子任务全 DONE ⇒ **依赖已清偿** |
| 门控 | **FU-59 已于 `4637a5b` 清偿**（`api/common.py` 的 If-Match 正则收敛为全仓单源 `IF_MATCH_PATTERN`）⇒ wave-3 开闸的前置阻塞项已清空 |
| 并行对象 | **M2-01/S6**（L2 lane，`qwen3.8-flash`，写集 `tests/api/activities/**`）。编排器已按 **PRE-5** 三判据实测写权面**不相交**（§1.3）⇒ 你**只会**看到自己那 1 件在飞；若 `git status` 出现第三方面，**禁碰**并按 §8 上报（A161 在飞污染） |

**上工第一件事（V0 基线自证）**：复测 HEAD 是否仍为 `bd7f89c`。若已漂移且属编排器自身的纯文档/纯台账提交，
**依 A269 先例：U-BASELINE 已由编排器在本派单文预裁关闭** —— 以 spawn message 里逐字给出的**取代后权威读数**为准；
除此之外的任何漂移（含代码面 sha 变化）一律停手报 `U-BASELINE`。

## 1. 写权面（越界即回报编排器，手册 §6.4；禁「顺手改」）

### 1.1 只新建（**恰 1 件**）

```text
orchestrator/handoff/M1-01-design.md
```

**本棒是纯设计棒：零代码、零测试、零证据。** 手册 §6.4「max 设计 + flash 量产」配对模式的 max 侧：
你产出**接口签名、数据结构、边界清单、验证清单、文件级 TODO**，之后 S2–S8 的 flash/max 棒**只允许在你划定的
文件与函数内工作**。⇒ 你的设计文**就是**后续 7 棒的牢笼与地图，**含糊即下游必错**。

### 1.2 只修改：**无**（`git diff --numstat` 的 `deleted` 列必须全 0；`git status --porcelain` 只允许 1 行 `??`）

### 1.3 硬禁面（**一字不改**）

- `spec/**` · `contracts/**`（**只读**，手册 §1 不变量）· `.git/**` · `orchestrator/state.json` · `scripts/**` ·
  `migrations/**` · `evidence/**` · `qa-reports/**` · `web/**` · `fixtures/**`。
- `src/**` 与 `tests/**` **全部**（本棒零代码写权；含 M1-01 自己 scope 内的 `domain/ingest/**`、
  `api/imports.py`、`infra/files.py`、`tests/domain/ingest/**`、`tests/golden/ingest/**` —— 那些归 S2–S7）。
- `orchestrator/handoff/**` 除 §1.1 那 1 件外的全部（尤其 `M2-01-design.md`、`M0-02-design.md`、
  `M0-03-design.md`、`M0-04-design.md`、各 `*.slice.json`、`LANE-COMMON.md`）。
- `orchestrator/tasks/**`（卡片受 D-011 保护；发现卡片失真**写进你的 §12 未决问题**，禁自行改卡）。
- **禁**执行任何 `git commit / push / add / reset / checkout`（入库由编排器做）；**禁** sudo；
  **禁**建 PR / 触发 workflow（`gh` 未认证）。
- **PRE-5 写集不相交三判据**（编排器实测，你无需复做）：① 路径前缀集不相交（本棒单件
  `orchestrator/handoff/M1-01-design.md` vs 并行棒 `tests/api/activities/`）⇒ 交集 ∅；
  ② 无共享包标记（双方都不新建任何 `__init__.py`）；③ 无共享冻结面（本棒零 `.py` ⇒ 与 mypy/pytest 分母无交叉）。

### 1.4 编码与体例硬要求（LANE-COMMON §2 / §3.1；**违反必判红**）

- **UTF-8 / 无 BOM / 无 `\r` / 以 `\n` 结尾**；无 C0 控制符（`\n`/`\t` 除外）、无 C1（0x80–0x9f）。
- ⚠ **`ruff format` 的作用域含 `.md`（A175）**：你新写的这份 `.md` **必须过** `ruff format --check .`，
  否则全表 ruff 分母那一门判红。围栏代码块会被重排 ⇒ **落盘后必须实跑 V3 并贴原文输出**。
- 写入通道走 LANE-COMMON §2 的**三步法**（PowerShell 单引号 here-string → 无 BOM 落盘 → bash 接**文件路径**驱动）；
  **禁**用 `wsl.exe -e bash -lc "…"` 承载含 `$`、`$(…)`、反引号、嵌套双引号或 `;` 多段表达式的命令。
- **PRE-39（lane 侧命名约束）**：你写 `.orch_tmp/` 的 scratch 件**必须**带**你自己的 lane 标识**
  （建议前缀 `s1m1_`），**禁**使用 `orch_` 前缀（编排器专属命名空间；碰撞会造成取证件混合编码 = R19-9 的实际事故）。
- **here-string 里禁出现行首 `'@`**（会提前终止）—— 写 Markdown 时尤其注意。
- 命令过长会撞 Windows **`os error 206`** ⇒ 拆「数据文件 + 小 driver」。
- **R12-1**：若你写任何 `.py` 辅助脚本（本棒原则上不需要），**禁** `except (A, B):` 元组形式
  （本通道实测会静默损坏成 `except A, B:`），且写完**必须立刻** `ast.parse` 自证语法。

## 2. 预期红清单（PRE-14；由编排器**实测**得出，非推测）

**空集**，且本棒**结构上不可能**判红任何测试门：零 `.py` 改动 ⇒ `pytest` / `mypy` 分母不变；
唯一受影响的是 **`in_scope_md` 218 → 219** 与 **`ruff_formatted_files` 343 → 344**（见 §4.1）。
唯一可能判红的门是 **`ruff format --check .`**（若你的 `.md` 不合 ruff 的 markdown 体例）⇒ V3 是**你的头号门**。

## 3. 逐字口径回源（PRE-29：禁采信二手复述，一律回源到下列**路径 / 行号**自读原文）

### 3.1 你的任务卡（**权威**，只读）

`orchestrator/tasks/M1-01.md`（**70 行 / 13420 B / sha12 `b18813bd6dd1`**）：
`:4` goal · `:6–10` inputs（slice / contracts / fixtures / specs）· `:11–21` **gates 原文**（含 AC-005/AC-006 逐字）·
`:22` `scope_allow` · `:23` `scope_deny` · `:24` **`public_frozen`**（M1-P01 只能经同一套 `domain/ingest` 入口扩展、
**禁另起第二套校验**、**禁改**你冻结的入口签名，改动走 CR）· `:25` outputs · `:26+` dispatch（档位 / loop_cap）·
`:32–49` **子任务档位表 S1–S8**（手册 §15.5：无此表不得 spawn；你写的 §11 文件级 TODO **必须**与之逐棒对应）·
`:58` 派单纪律（编排器已复跑 `tests/unit/test_task_cards.py` = **5 passed**，并实测 dep `M0-04.status=DONE`）。

### 3.2 契约切片（**实现唯一依据**，只读）

`orchestrator/handoff/M1-01.slice.json`（**2876 行 / 60641 B / sha12 `eadbd88e4ef7`**，`spec_version` = **1.0.1**）：

- `operations`（**6** 个 operationId）与**实测**的声明响应码集：
  `createImport` → **201** + 400/401/403/404/409/412/413/422/428/429/500（2 params, 有 requestBody）·
  `attachImportFile` → **200** + 同上（4 params, requestBody）·
  `configureImport` → **200** + 同上（4 params, requestBody）·
  `validateImport` → **202** + 同上（4 params, **无** requestBody）·
  `getImport` → **200** + 同上（2 params）· `listImports` → **200** + 同上（5 params）。
  ⚠ 每个 op 的声明面都是 **12 码**（A95 / design §8 体例：声明面一律 `declared_responses(<2xx>)`）。
  **method / path 在切片的 `operation` 子对象里，禁凭本文的摘要取值 —— 自行实取并逐 op 写进你的 §1。**
- `ddl`（**3** 表，**逐字实测**）：
  - `imports`：`workspace_id` · `id` · `bank_id` · `snapshot_code` ·
    `format CHECK IN ('LEGACY_SYNTHETIC_JSON','SOURCE_JSON','SOURCE_CSV')` ·
    `state CHECK IN ('RECEIVED','CONFIGURED','VALIDATING','VALID','INVALID','PUBLISHING','PUBLISHED')` ·
    `mapping_id` · `validation_digest` · `issue_json CHECK(json_valid)` · `snapshot_id` · `correction_of` ·
    `job_id` · `revision CHECK(revision>=1)` · `created_at`；`PRIMARY KEY(workspace_id,id)`；
    `FOREIGN KEY(workspace_id,mapping_id) REFERENCES source_mappings(...)`；表尾 `STRICT`。
  - `import_files`：`workspace_id` · `id` · `import_id` · `artifact_id` · `table_name` · `label`；
    `PRIMARY KEY(workspace_id,id)`、`UNIQUE(workspace_id,import_id,table_name)`、两个 FK（imports / artifacts）；`STRICT`。
  - `source_mappings`：`workspace_id` · `id` · `bank_id` · `content_json CHECK(json_valid)` ·
    `digest CHECK(length(digest)=64)` · `created_at`；`PRIMARY KEY(workspace_id,id)`；`STRICT`。
  ⇒ **`imports.state` 的 7 态就是你的状态机分母**（`TransitionId` 形态请对齐
  `src/campaignlab/worker/states.py`（**215 行 / 8353 B / sha12 `aa60b26090e1`**）的既有体例）。
- `acceptance_rows`（**逐字**）：
  - **AC-005**：「A 样例注入重复切片、负人数、层级倒置和错误行长。B 注入重复码及孤立切片」→
    「校验返回具体行列，旧验证失效，正式快照未被更新。原型 v0.1 合成文件大于 8 MiB 拒绝」〔主证据：导入 API、数据库〕
  - **AC-006**：「A、B、六行 CSV 与等价 SOURCE_JSON 分别导入」→
    「A/B 各 **510** 切片。B 长表 **4590** 阶段项。元分归一后远程值一致。CSV/JSON 同值，源行和文件摘要可追溯」
    〔主证据：DB、制品、页面〕
- `source.rule` 原文：「活契约 `contracts/` 是实现唯一依据（手册第 7 节）；BASE 仅供活契约中不存在的只读原件
  （`qa/ACCEPTANCE.md`、`ui/*.md`）；`spec_version` 从活契约 `info.version` 动态读取，**禁止硬编码**。」

### 3.3 只读原件与 fixtures（**必须逐个实读**，你的归一化模型要按它们的真实形状设计）

| 路径 | 实测 face | 你要从中取什么 |
|---|---|---|
| `spec/CampaignLab-SDD-v1.0/architecture/DATA.md` | 56 行 / 7957 B / `c0aabbe60796` | 「导入通道」「映射和标准表」「去重和可比性」三段原文 |
| `spec/CampaignLab-SDD-v1.0/framework/DATA.md` | 15 行 / 1973 B / `2a6a17c4ca48` | 「SQLite 与迁移」「文件与 DuckDB」 |
| `spec/CampaignLab-SDD-v1.0/architecture/API.md` | 39 行 / 4136 B / `5fa2ada865c1` | 「错误分类」409/412/422 边界 |
| `spec/CampaignLab-SDD-v1.0/architecture/DOMAIN.md` | 43 行 / 5339 B / `7e8b1778dd9e` | 「唯一标识和精度」「对象与修改」「内容摘要的固定投影」 |
| `spec/.../architecture/OPERATIONS.md` | 卡片 `:10` 点名 | 「文件处理」的**大小上限口径**（8 MiB 的权威出处） |
| `fixtures/banks/bank-a.json` | **1 行 / 147272 B** / `2c57122e202d` | A **宽表**真实形状（单行压缩 JSON ⇒ 禁按行数推断结构） |
| `fixtures/banks/bank-b.json` | **1 行 / 291343 B** / `2d1d96532b78` | B **长表**真实形状（4590 阶段项的来源） |
| `fixtures/banks/map-a.json` | 65 行 / 1653 B / `f37c009d1f88` | A 的映射 |
| `fixtures/banks/map-b.json` | 69 行 / 1601 B / `2246eae3af23` | B 的映射 |
| `fixtures/banks/csv-mini/source.json` | 352 行 / 6821 B / `b0bcd1d2c375` | **等价 SOURCE_JSON** |
| `fixtures/banks/csv-mini/slices.csv` | **7 行** / 1914 B / `c766f7f83c64` | **六行 CSV**（表头 + 6 数据行） |
| `fixtures/banks/csv-mini/metadata.json` | 84 行 / 1632 B / `1d8bbf80f610` | CSV 通道的元数据 |
| `fixtures/analytics-golden.json` | 144 行 / 3277 B / `a7122ae9aae7` | **510 切片 / 4590 阶段项 / 元分归一**的黄金值 |
| `contracts/source-json.schema.json` | 865 行 / 23724 B / `eef2099bddfa` | SOURCE_JSON 的规范 |
| `contracts/source-mapping.schema.json` | 135 行 / 2734 B / `ab5dddd43f2e` | 映射的规范 |
| `contracts/source-metadata.schema.json` | 804 行 / 20125 B / `e0d18ea521ba` | 元数据的规范 |
| `contracts/openapi.json` | 16747 行 / 443309 B / sha16 `592571099d638251` | 6 个 op 的**活契约**原文 |

### 3.4 M0-04 底座（dep 已 DONE；`validateImport` 的 202 作业语义**必须复用**，禁重写队列）

| 路径 | 实测 face | 用途 |
|---|---|---|
| `src/campaignlab/api/jobs.py` | 372 行 / 16934 B / `e9b575602e56` | 202 → `Job` → `Location` 的既有 HTTP 体例；`IF_MATCH_PATTERN` 使用点 :221 / :305；`check_if_match()` 调用点 :259 / :343；**A228 先例**（`if_match` 声明为可空形参是 428 可达的前提） |
| `src/campaignlab/worker/states.py` | 215 行 / 8353 B / `aa60b26090e1` | `TransitionId` 形态与 `creates_new_row` 体例（你的 `imports.state` 状态机照此设计） |
| `src/campaignlab/worker/store.py` | 736 行 / 34328 B / `c9e9416dfb05` | 「一方法一短事务」体例 |
| `src/campaignlab/worker/runner.py` | 448 行 / 18663 B / `5df27f9d7f90` | 作业执行与认领/续租 |
| `src/campaignlab/worker/service.py` · `leases.py` · `capacity.py` · `integrity.py` · `deps.py`(`ac59435dd93f`) · `errors.py` | 实测在场 | 复用面清单（**禁改**，卡片 `scope_deny` 明列 `worker/**`） |
| `src/campaignlab/infra/artifacts.py` | 843 行 / 36033 B / `14515bc840da` | 原子制品；**卡片红线**：「不把 `duckdb` 关系导入绕过 `infra/files.py` 的摘要登记」 |
| `src/campaignlab/infra/db/repositories.py` | 1884 行 / 82850 B / `23437663c59e` | Repository 体例；**A81 SQL 写点唯一**、**A82「纯追加」处置**先例 |
| `src/campaignlab/api/common.py` | 1186 行 / 47180 B / **`b2908617d193`** | DTO 落点（**方案 A** 先例）；`IF_MATCH_PATTERN: Final = r'^"[1-9][0-9]*"$'` @ **:190**（已在 `__all__` @ :88）；`etag()` :838 · `check_if_match()` :843（缺头 → **428 `PRECONDITION_REQUIRED`**、不匹配 → **412 `REVISION_CONFLICT`**）；`canonical_json` · `CaseInput` |
| `src/campaignlab/api/deps.py` | 346 行 / 13524 B / `ed1075a86447` | 提供器体例（**A233**：`TYPE_CHECKING` 块形态规避 ruff `I001`） |
| `src/campaignlab/api/app.py` | 178 行 / 7857 B / `2e4aad126172` | 装配面；**A90① / A10 最小例外**（≤3 行）先例 —— 你的 §11 必须把「挂载 imports router 需要动 app.py」列为**写权缺口** |
| `src/campaignlab/domain/errors.py` | 290 行 / 11269 B / `82af76b29015` | `PROBLEM_CODES`（**20 码注册表**，实取）与 `DomainError` 子类（14 个） |
| `src/campaignlab/application/idempotency.py` | 116 行 / 4868 B / `dcfe3f8eb071` | 幂等键与「禁止裸先查后插」原文 |
| `src/campaignlab/application/audit.py` | 148 行 / 5066 B / `626c8733a449` | `AuditWriter`（**只 import、禁改**、禁复制第二份链逻辑） |

### 3.5 同体例的**已交付** design 文（照此结构写，禁自创体例）

- `orchestrator/handoff/M2-01-design.md`（**1396 行 / 153979 B / `2d39feaac2d1`**）—— **最新最完整的范本**。
  章节骨架实测：§1 接口签名(:22) · §2 数据结构(:135，含 §2.4 落库映射 :197、§2.5 DTO 落点 :224) ·
  §3 状态机(:244) · §4 条款门禁(:354) · §5 检查项框架(:464) · §6 ETag 与 409/412/428 边界(:611) ·
  §7 事务边界与持久化(:766) · §8 逐 op 可达码矩阵(:856) · §9 边界清单(:877) · §10 验证清单 V1–V15(:930) ·
  §11 文件级 TODO(:954，含 §11.9 **写权缺口一览** :1191、§11.10 **方案 B 平移映射** :1203) ·
  §12 未决问题(:1214) · §13 本文件自检(:1307) · §14 编排器裁定追记(:1323，append-only)。
- `orchestrator/handoff/M0-04-design.md`（300 行 / 68557 B / `acb2629ca10d`）—— §9 的
  「`路径:符号,符号,…`」文件级 TODO 体例来源。
- `orchestrator/handoff/M0-02-design.md`（340 行 / 55140 B / `42a046307304`）·
  `M0-03-design.md`（404 行 / 58455 B / `f43abe2bf7fb`）。

## 4. 冻结面实测读数（编排器于 `bd7f89c` 时点实测；你上工**必须自行复测**并贴命令原文）

### 4.1 仓面

```text
counts（权威位点＝state.json -> resume.self_check_gates_rc0.counts，禁写死别处）
  ruff_formatted_files = 343   （组成：in_scope_py 125 + in_scope_md 218）
  mypy_source_files    = 123
  pytest_passed        = 809   （= frozen 788 + GIT_ENV_IGNORES 21）
  contract_registered_nodes = 13 · acceptance_denominator = 47 · acceptance_resolvable = 47
  frontend_baseline_rows = 8
  live_openapi_sha16 = 592571099d638251 · live_openapi_info_version = 1.0.1
```

你落盘 **1 件 `.md`** 后的**期望**：`in_scope_md` 218 → **219**、`ruff_formatted_files` 343 → **344**、
`in_scope_py` **125 不变**、`mypy_source_files` **123 不变**、`pytest_passed` **809 不变**。
若实测不符，**如实报差异并解释**，禁改口径凑数（C10）。

### 4.2 你的 scope 面**全部为空地**（编排器实测，逐项 ABSENT）

```text
src/campaignlab/domain/ingest/     ABSENT     src/campaignlab/api/imports.py    ABSENT
src/campaignlab/infra/files.py     ABSENT     tests/domain/ingest/              ABSENT
tests/golden/ingest/               ABSENT     tests/golden/                     ABSENT   ← ⚠ 见 A276
evidence/M1/                       ABSENT     orchestrator/handoff/M1-01-design.md  ABSENT
```

⇒ 你是**全新起棒**，没有任何既有实现约束你的设计；**但也意味着**：你必须在 §11 里把
「新建目录需要哪些 `__init__.py`」逐件点名（**含 `tests/golden/__init__.py`**，见 **A276**），
否则 S2/S6/S7 会各自踩一次「包标记缺失 ⇒ pytest 收集期 rc=4」的坑（PRE-34：rc=4 ≠ rc=1）。

### 4.3 卡片 gate 的**字面量**（你的 §10 验证清单必须让它们**可被执行**）

| 卡片行 | gate 字面量 | 你的义务 |
|---|---|---|
| `M1-01.md:14` | `pytest -q tests/golden/ingest -k counts` | §11 的 S7 必须产出**函数名含 `counts`** 的用例 |
| `M1-01.md:15` | `pytest -q tests/domain/ingest -k locate` | §11 的 S6 必须产出**函数名含 `locate`** 的用例（负例定位到行/列/字段） |
| `M1-01.md:16` | `pytest -q tests/domain/ingest -k size_limit` | §11 的 S2/S6 必须产出**函数名含 `size_limit`** 的用例（> 8 MiB 拒绝、报 `Problem`、**不留半成品**） |
| `M1-01.md:17` | `pytest -q tests/domain/ingest -k csv_equivalence -k stale_validation` | ⚠ **依 A275 拆成两行**（见 §5），禁照抄双 `-k` 单行形态 |
| `M1-01.md:18` | `pytest -q tests/integration/jobs -k validate_import` | 该用例文件**归 M0-04 lane**、本任务**只跑不改**；你的 §11 必须写明「S5 的 `validateImport` 202 语义**复用** M0-04 底座，禁重写队列」，并把「失败即回报」写进验证清单 |
| `M1-01.md:19` | openapi 指纹新鲜度 | 期望与 `live_openapi_sha16` / `.live_openapi_bytes` 现值一致；不一致即回报 T lane 重切，**禁自行重切**（`scripts/**` 不在 scope_allow） |
| `M1-01.md:20` | ruff check / ruff format --check / mypy / pytest -q | **以 rc 为判据、计数不写死**（指向 `state.json` 现值） |
| `M1-01.md:21` | `python scripts/check_contracts.py check --validate` | 登记项数以 `.counts.contract_registered_nodes` 为准；AC 分母以 `.counts.acceptance_denominator`（**47**）为准 |

## 5. 本棒携带的裁定与义务（append-only；**不得推翻**，有异议走 §8 上报）

### A275（本批新裁）· 卡片 gate `M1-01.md:17` 的**双 `-k`** 是静默削弱 ⇒ 拆成两条独立命令

**卡片原文**：`uv run --no-sync pytest -q tests/domain/ingest -k csv_equivalence -k stale_validation` -> 期望 rc=0。
**编排器实测**（禁推测；命令与输出原文见本批取证件）：在 `tests/domain/activity` 上跑
`-k immutable -k digest --collect-only` 收集 **5** 例，而单跑 `-k immutable` = **3** 例、单跑 `-k digest` = **5** 例
⇒ 双 `-k` 的结果**恰等于后一个** `-k`，**既非交集（应为 0）亦非并集（应为 8）**。
成因＝`-k` 在 pytest 里是 `store` 型选项，**后者覆盖前者**（argparse 语义）。
⇒ 卡片那行 gate **实际只校验了 `stale_validation`**，`csv_equivalence` 被**静默丢弃** —— 而 AC-006 的
「CSV/JSON 同值」正落在 `csv_equivalence` 上。**裁定**：
① 卡片原文按 **D-011 不改写**，其**权威读法**＝**两条独立命令**：
`pytest -q tests/domain/ingest -k csv_equivalence` 与 `pytest -q tests/domain/ingest -k stale_validation`，
各自期望 rc=0；② 你的 design **§10 验证清单必须把它们写成两行**（各自独立 V 编号），
**禁照抄**卡片的双 `-k` 单行形态；③ 你的 §11 必须保证 `csv_equivalence` 与 `stale_validation`
**两个 `-k` 字面量各自至少命中 1 个具名用例**；④ 同批把「**任何 gate/验证命令里出现重复 `-k`** 」
列为**派单前自检的一道门**（并入 FU-58 的机器化范围）。

### A276（本批新裁）· `tests/golden/` 整层不存在 ⇒ 包标记是**写权缺口**，必须在 §11 显式点名

编排器实测：`tests/golden/` 与 `tests/golden/ingest/` **均 ABSENT**，而卡片 gate `M1-01.md:14` 直接跑
`pytest -q tests/golden/ingest`。任务卡 `scope_allow` 只给了 `tests/golden/ingest/**`，
**未含** `tests/golden/__init__.py`（在 `tests/golden/ingest/**` 字面量**之外**）⇒ 与 **A262**
（`tests/domain/__init__.py` 的同型缺口，先例＝M1-03 的 N1）**完全同族**。**裁定**：
① 你的 design §11 必须把 **`tests/golden/__init__.py`** 与 **`tests/golden/ingest/__init__.py`**
两件**显式列为 S7 的新建件**，并在 §11 的「写权缺口一览」里标注 `tests/golden/__init__.py`
为**越字面量件**（授权依据＝A262 同族 ＋ A276）；② 形态一律采**单行 docstring**
（**禁零字节空文件**）—— 依据＝仓内既有 tests 包标记**无一**为零字节（A262 实测结论，
例：`tests/api/activities/__init__.py` = 1 行 / 89 B）；③ 同理，`tests/domain/ingest/__init__.py`
也必须显式点名（`tests/domain/` 本身**已存在**，S5 批已建 `tests/domain/__init__.py`）。

### 承前批裁定与立规（逐字携带，**禁推翻**）

- **FU-59 已清偿 / A271 / PRE-40**：`IF_MATCH_PATTERN` 已收敛为**全仓单源**，定义于
  `src/campaignlab/api/common.py:190`（`Final = r'^"[1-9][0-9]*"$'`），**已在 `__all__`**（`common.py:88`），
  运行期实测 `len(common.__all__) == **80**`。**你的 §1/§6 必须写明：`imports` 的 If-Match 端点一律
  `from campaignlab.api.common import IF_MATCH_PATTERN`，禁内联第二份正则**
  （守护＝`tests/unit/test_if_match_pattern_single_source.py`，**5 判据 + 6 阳性对照 = 11 例**，
  其中判据④是「同族钉桩禁分叉」的元守护 ⇒ 你若发明第二份正则，**必判红**）。
  **PRE-40**：冻结面 sha **已重定基**，`api/common.py` 的权威 sha12 是 **`b2908617d193`**
  （**禁**沿用旧值 `836e7b3e8d3a`）。
- **FU-64**：`M2-01-design.md:215` 那句「`IF_MATCH_PATTERN` **不在** `__all__` 里」**已失真**，
  **禁引用、禁复述**（R18-4 的违例形态＝照抄设计文而未做 AST 实测，属 PRE-20 违例）。
  权威读法一律以**运行期实测**为准。
- **A261**：派单文与设计文的 §0 一律以 **sha** 为锚，禁写 tag（`git tag -l` 实测 0 项）。
- **A269 先例**：派单后 HEAD 因编排器自身纯文档/纯台账提交而漂移时，U-BASELINE 由编排器**预裁**关闭。
- **A228**：`if_match` 必须声明为**可选形参**（`Header(default=None, pattern=IF_MATCH_PATTERN)`），
  否则缺头会在进入函数体前被判 **422**，design 要求的 **428** 分支**结构上不可达**。
- **A260**：状态码判据面＝「**装饰器 2xx 声明 vs 切片 2xx**」；**禁**写运行期 2xx 状态码断言
  （信封承载状态码 ＋ 处理器直接返回 `Response` ⇒ 装饰器 `status_code` 被短路，运行期判据**结构性 NO_TEETH**）。
- **A95**：状态码集合的**唯一权威**是装饰器的 `declared_responses()`；实现码集必须 == 切片码集。
- **A81 / A82**：**SQL 写点唯一**；对 `infra/db/repositories.py` 采**纯追加**处置（0 删除行）。
- **A233**：`api/deps.py` 的追加一律采 **`TYPE_CHECKING` 块形态**（规避 ruff `I001` 与「只允许追加名字」的字面冲突）。
- **A115**：**禁写死符号面计数**（`__all__` 项数、用例数、分母一律 `inspect` / `--collect-only` **实取**）。
- **A171**：数据结构的每行末尾用 `←` 标**真值来源切片路径**。
- **A175**：`ruff format` 的作用域**含 `.md`**。
- **PRE-21**（禁系统 python3 —— 3.12.3 在 PEP 758 上崩；一律 `uv run --no-sync`，仓内 Python 实测 **3.14.10**）·
  **PRE-25/26/27**（符号定义点、枚举项数、契约面切片**实取**）· **PRE-29**（口径回源、**双向**禁采信）·
  **PRE-33**（符号对撞**全仓**范围）· **PRE-34**（区分 **rc=1** 断言红与 **rc=4** 收集期错误）·
  **PRE-37 第 3 款**（跨通道复述的 sha / 计数必须由**同一赋值点**程序化派生）·
  **PRE-38**（自检判据须声明**适用时点**）· **PRE-39**（scratch 命名 ＋ 取证件编码四判据）·
  **PRE-41**（改动被多处钉桩的公共面前，普查必须按**被钉住的值**扫并跑全量 pytest 对撞 ——
  本棒零代码改动 ⇒ 该条对你的实际含义是：**只在设计文里描述**公共面的改动需求，把它列为 §11 的写权缺口，
  **禁自己动手**）。

### 卡片红线（`M1-01.md` 的「禁止」段，逐字义务）

- **禁写第二套校验器** —— 四种入口（A 宽表 / B 长表 / 六行 CSV / 等价 SOURCE_JSON）**共用一套**规范，
  这是 AC-005 / AC-006 的**实质要求**，也是你这份设计文的**核心命题**。
- **禁**用浮点算金额分（一律整数分）；**禁**用系统当前时间做领域计算（**显式时钟**）。
- **禁**把 `duckdb` 关系导入绕过 `infra/files.py` 的摘要登记。
- **禁**为过测改测试期望。
- `public_frozen`（卡片 `:24`）：你的归一化模型与校验规则设计落 `M1-01-design.md`，供 **M1-02 / M1-03 / M1-P01**
  消费；**M1-P01（月报接入，AC-MR-01/02 来源为月度 append 清单）只能经同一套 `domain/ingest` 校验入口扩展，
  不得另起第二套校验，也不得改你冻结的入口签名（改动走 CR）** ⇒ 你的入口签名必须**为月报增量留出扩展点**。

## 6. 交付面：`M1-01-design.md` 的**必备章节**（照 M2-01-design.md 体例；缺章即判 PARTIAL）

| § | 内容 | 硬要求 |
|---|---|---|
| 1 | **接口签名**（6 个 operationId） | 函数名与 operationId **逐字对应**；装饰器必须**显式**给 `operation_id`；逐 op 给 method / path / 形参（含 `if_match` 的**可选**声明形态，A228）/ 2xx 与错误码映射 |
| 2 | **数据结构**（字段级） | 每行末尾 `←` 标真值来源切片路径（A171）；含 §2.4 **落库映射**（列 ↔ DTO，真值来源＝切片 `ddl.*`）与 §2.5 **DTO 落点**（**冻结为方案 A**＝追加进 `api/common.py`，方案 B 的平移映射写进 §11 的缺口段） |
| 3 | **状态机**（`imports.state` **7 态**） | `TransitionId` 形态对齐 `worker/states.py`；逐迁移给 `id / sources / target / trigger / spec_ref / guard（SQL 镜像原文）/ transaction / creates_new_row`；**非法迁移的错误映射逐条冻结**（码名以 `domain/errors.py::PROBLEM_CODES` **实取**） |
| 4 | **归一化模型（本棒的核心）** | 四入口 → **同一套**规范校验的**单一入口签名**；宽表 A / 长表 B / 六行 CSV / SOURCE_JSON 的**解析→归一→校验**三段职责边界；**行列定位结构**（AC-005「返回具体行列」的数据形状，含行号/列名/字段路径的**0/1-based 口径必须显式声明**）；**元分归一**口径（整数分，禁浮点）；**去重与可比性**（DATA.md 三段原文）；**源行与文件摘要可追溯**（AC-006）的落点 |
| 5 | **负例与失效** | 逐条冻结：重复切片 / 负人数 / 层级倒置 / 错误行长 / B 重复码 / 孤立切片 / **> 8 MiB 拒绝**（报 `Problem`、**不留半成品**）；**旧验证在新映射后失效**（`validation_digest` 与 `source_mappings.digest` 的联动）且**正式快照未被更新**；每条给「触发条件 → severity → `Issue.code` → `location`」 |
| 6 | **ETag 与 409/412/428 边界** | `IF_MATCH_PATTERN` **单源 import**（A271/FU-59）；428 可达性前提（A228）；判定顺序（**顺序即代码顺序，禁调序**）；**A260**：禁运行期 2xx 断言 |
| 7 | **事务边界与持久化** | 「一方法一短事务」体例（`worker/store.py`）；**A81 SQL 写点唯一**；审计只 import `AuditWriter`；显式时钟 / ID 前缀 / 幂等键 |
| 8 | **逐 op 的可达码矩阵** | 声明面一律 `declared_responses(<2xx>)` 的 **12** 码；本表只标**可达**面；声明为**不可达**的码要单列一段（体例＝M2-01-design §6.6：断言「不可达」本身，**禁** `skip`/`xfail`） |
| 9 | **边界清单** | AC-005 / AC-006 → 实现约束 → **已知失败模式**，逐条对齐 |
| 10 | **验证清单**（命令 → 期望 rc） | 供 **S6–S8** 直接采集；**无「人工确认」项**；计数一律指向 `state.json.counts` 现值、**禁写死**；**A275**：`csv_equivalence` 与 `stale_validation` **拆两行**；含 **V15 型**条目（新增 `conftest.py` 或同 basename 新文件后必须跑**全树** mypy，LANE-COMMON §3.6） |
| 11 | **文件级 TODO（S2–S8 逐棒）** | 格式＝`路径:符号,符号,…`（M0-04-design §9 体例）；**必须**与卡片 `:32–49` 档位表的 **S2–S8 七棒逐棒对应**（含档位与预估 token）；**必须**含 §11.x「**写权缺口一览**」表（点名所有**不在** `scope_allow` 内却必须改的路径 ＋ 既有裁定先例，至少含：`api/common.py` 的 DTO 追加、`api/deps.py` 的提供器、`api/app.py` 的 `include_router`、`infra/db/repositories.py` 的纯追加、**`tests/golden/__init__.py`（A276）**、`tests/unit/test_domain_errors.py` 的 `__all__` 计数哨兵）＋ §11.y「**方案 B 平移映射**」（仅当编排器拒绝扩围时启用，符号名与字段序完全不变） |
| 12 | **未决问题** | 交编排器裁定，**实现方不得自行决定**（手册 §6.4）；逐条给 U 编号 ＋ 倾向 ＋ 理由 |
| 13 | **本文件自检** | 命令 → rc；**禁写死**任何计数（一律 `inspect` / `--collect-only` 实取） |
| 14 | **编排器裁定追记** | 预留**空段** ＋ 明写「append-only；§1–§13 一字未改」（体例＝M2-01-design §14） |

**PRE-24 / PRE-26 义务（这是本棒最容易失守的地方，同族前例＝D-050 / D-052 / A263–A267）**：
你在 §11 点名的**每一个具名符号**（类名、函数名、常量名、字段名）都必须在**你的设计内自洽**，
且凡引用**仓内既有符号**的，必须**逐个做仓内实存对撞**（`hasattr` / `inspect` / `typing.get_args` / `model_fields`）
并把实测结论写进文内 —— **禁写设想名**。D-052 的教训逐字告你：design 写了 `BoundaryCaseDraft.input_payload`
与 `CaseInput.model_validate`，而仓内实名是 `BoundaryCase.input`、且 `CaseInput` 是 `Annotated` 别名
（`hasattr(CaseInput,'model_validate')` 实测 **False**）⇒ 下游 S4/S6/S7 三棒全部踩坑，
最终由 A256 + D-052 兜底。**凡你无法实存的符号，必须显式标注「待创建 ＋ 由哪一棒创建」**（FU-58 的口径）。

## 7. 门（rc 必须全 0；命令原文与输出尾部**逐字**贴进回执，禁只写「通过」）

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
cd /home/szf/dev/CampaignLab

# V0 基线自证（不等即停手，除 A269 预裁的编排器自身提交外报 U-BASELINE）
git rev-parse HEAD; git rev-parse --abbrev-ref HEAD; git status --porcelain

# V1 你的 1 件 face（行数/字节/sha256[:12]）
wc -l -c orchestrator/handoff/M1-01-design.md; sha256sum orchestrator/handoff/M1-01-design.md

# V2 编码四判据（PRE-39；file -bi 必须含 charset=utf-8）
file -bi orchestrator/handoff/M1-01-design.md
uv run --no-sync python -c "import pathlib;b=pathlib.Path('orchestrator/handoff/M1-01-design.md').read_bytes();t=b.decode('utf-8');print('strict_utf8=OK','bom=',b.startswith(b'\xef\xbb\xbf'),'cr=',b'\r' in b,'nul=',b'\x00' in b,'c0c1=',[hex(ord(c)) for c in t if (ord(c)<0x20 and c not in '\n\t') or 0x7f<=ord(c)<=0x9f],'tail_nl=',b.endswith(b'\n'))"

# V3 ruff（**你的头号门**：A175 —— ruff format 的作用域含 .md）
uv run --no-sync ruff format --check . ; echo "rc=$?"
uv run --no-sync ruff check . ; echo "rc=$?"

# V4 mypy 全仓（期望仍 123 source files —— 你零 .py 改动）
uv run --no-sync mypy ; echo "rc=$?"

# V5 全量 pytest（期望仍 809 passed / 0 failed —— 你零 .py 改动）
uv run --no-sync pytest -q 2>&1 | tail -3

# V6 契约门禁未回归 ＋ 切片新鲜度（卡片 :19 / :21）
uv run --no-sync python scripts/check_contracts.py check --validate ; echo "rc=$?"
uv run --no-sync python -c "import hashlib,pathlib;d=pathlib.Path('contracts/openapi.json').read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))"

# V7 硬禁面零改动（输出**必须只有**你那 1 件 ??，其余为空；numstat 必须为空）
git status --porcelain ; git diff --numstat

# V8 你的 §11 与卡片档位表 S2–S8 **逐棒对应**自证（贴出你文内 §11 的棒号清单）
grep -n '^### 11\.' orchestrator/handoff/M1-01-design.md

# V9 你引用仓内既有符号的**实存对撞**原文（PRE-24；逐个贴命令与输出）
#   例：uv run --no-sync python -c "from campaignlab.api import common;print(hasattr(common,'IF_MATCH_PATTERN'),len(common.__all__))"
```

## 8. U 项上报（**禁自行裁定**；手册 §6.4）

遇下列情形**立刻停手**，在回执里以 `U-<n>` 编号上报，附**实测命令与原文输出**：

- 需要写任何 §1.3 硬禁面（含「顺手补一个 `__init__.py`」—— 那是 S2/S6/S7 的写集，你只在 §11 点名）；
- 活契约 `contracts/openapi.json` 与切片 `M1-01.slice.json` **不一致**（不一致即回报 T lane 重切，**禁自行重切**）；
- 卡片 gate / `scope_allow` 与 design 需求冲突（例如你需要改 `api/app.py` 才能挂载 imports router ⇒
  **写进 §11 的写权缺口一览并开 U 项**，禁自行扩围）；
- fixtures 的**实测形状**与 AC-006 的黄金值（510 切片 / 4590 阶段项）对不上 ⇒ 停手上报，**禁**调期望值凑数；
- 8 MiB 上限的权威出处在 `OPERATIONS.md` 里找不到明确口径；
- 任何门判红且 **2 轮** loop 内未收敛（写 BLOCKER ＋ 附「缩小范围」的降级交付选项；
  ⚠ 你在 **`slack=0` 关键路径**上，卡片原文要求**优先上报**）。

## 9. 派单前置自检（编排器已逐项做完；你只需在回执里**复述结论 ＋ 贴你自己的复测命令**，禁跳过）

| PRE | 编排器做了什么（实测） | 你要复述什么 |
|---|---|---|
| PRE-13 | 本派单文 ＋ `dispatch_log` ＋ `in_flight_agents` **先入库**，spawn 排其后，`agent_id` 由 spawn 后的纯台账批回填（禁填猜测值） | 无需动作 |
| PRE-14 | 预期红清单**实测为空**：本棒零 `.py` 改动 ⇒ 三门分母不变；唯一风险门＝`ruff format --check`（A175） | 复测 V3 并贴原文 |
| PRE-15 | 全部冻结面读数由脚本实测（§3.3 / §3.4 / §4），命令原文已贴 | 复测 §4.1 的 counts 与你引用面的 sha12 |
| PRE-20/24 | 卡片与切片的具名面已做仓内实存对撞：发现 **2 处**失真 ⇒ **A275**（双 `-k` 静默削弱）与 **A276**（`tests/golden/__init__.py` 写权缺口）已裁，实测口径写进 §5，**禁把失真原文抄给你去踩** | 复述 A275 / A276 的结论 |
| PRE-25/26/27 | 6 个 op 的声明码集、3 表 DDL、`imports.state` 7 态、`IF_MATCH_PATTERN` 定义点与 `len(common.__all__)==80` 一律**实取** | 复测并贴实取输出 |
| PRE-29 | §3 给的是**绝对行号 / 路径**而非二手复述，并明写「冲突以原文为准」 | 回执里逐条回源 |
| PRE-31 | **双键定位**：(`S1`,`M1-01`) 不在册（`dispatch_log` 18 条实测无此组合）；并已断言「同形异 task 的干扰面实存」＝`orchestrator/handoff/R13-lane-Z-M2-01-S1.md`（属 **M2-01** 的 S1）⇒ 禁按 lane/子任务号单键定位 | 无需动作 |
| PRE-33/34 | 你**零测试交付** ⇒ 本棒无 PC 义务；但你的 §10 验证清单**必须**为 S6–S8 写出**有牙**的 PC 要求，并逐字携带 rc=1 vs rc=4 的区分口径 | 回执声明你已在 §10 写入 |
| PRE-38 | 本文一切判据的**适用时点**＝「M1-01/S1 派单时点 · HEAD `bd7f89c` · 无同任务在飞棒」；禁跨批复用 | 复述时点 |
| PRE-39 | 你的 scratch 命名约束（`s1m1_` 前缀、**禁** `orch_`）与取证件编码四判据已写进 §1.4 | 回执声明你的 scratch 前缀 |
| PRE-40/41 | 冻结面 sha 已重定基（§5 逐字给出新值） | 复测 §3.4 的 sha12 |
| 卡片 `:58` | **卡片明载的派单前置**已做完：`pytest -q tests/unit/test_task_cards.py` = **5 passed**（rc=0）；dep `M0-04.status` 实测 **DONE**（12 个子任务全 DONE） | 复述这两条 |

## 10. 回执格式（**结构化**，禁散文；编排器会**独立复验**每一项，禁采信自报）

纯文本，**≤ 90 行**（LANE-COMMON §7）。逐段给：

1. `TIER_CONFIRM`：你实际运行的 model 与 reasoning（本环境若不暴露模型身份自证面，**如实说明**并按派单档位申报；编排器**不采信自报**，以档位裁定原文为准）。
2. `BASELINE`：V0 的三行输出原文（HEAD / branch / status）。
3. `FACE`：V1 的 1 件 face（`lines / bytes / sha256[:12]`）＋ V2 的编码四判据原文。
4. `GATES`：V3–V9 逐条「命令原文 → rc → 输出尾部逐字」。
5. `COUNTS`：你实测的 `ruff_formatted_files / mypy_source_files / pytest_passed / in_scope_py / in_scope_md`
   与 §4.1 期望值（344 / 123 / 809 / 125 / **219**）的**逐项对照**（不符即如实报差并解释，禁改口径）。
6. `STRUCT`：你交付的 §1–§14 **章节清单**（`grep -n '^## ' …` 原文）＋ §11 的 **S2–S8 七棒**逐棒对应自证
   ＋ §11 写权缺口一览的**条目数**与逐条路径。
7. `SYMBOLS`：你在文内引用的**仓内既有符号**的实存对撞清单（符号 → 实测命令 → 结果），
   以及你标注为「待创建」的符号清单（符号 → 由哪一棒创建）。
8. `HARDEN`：§1.3 硬禁面**零改动**自证（`git status --porcelain` 原文 ＋ `git diff --numstat` 原文）。
9. `U`：§8 的 U 项（无则写 `NONE`）。
10. `RESULT`：`DONE` / `DONE_WITH_GAP`（附 gap 清单）/ `PARTIAL` / `BLOCKED`（附 BLOCKER 与降级选项）＋ loop 实耗轮数。
