# R19 · Lane S6 · M2-01/S6 派单文 —— `tests/api/activities/**` 只新建（7 件 / 43 用例）

> 公共纪律一律见 `orchestrator/handoff/LANE-COMMON.md`（**先读它**，本文不重述）。
> 权威条款：`docs/delivery/LONG-HORIZON-ORCHESTRATION.md` v1.7。冲突时**手册胜**、其次本文、再次 design。
> **PRE-29 双向禁采信**：本文一切读数都是编排器于派单时点的实测快照；你上工**必须自行复测**并贴命令原文，
> 禁采信二手复述（**包括本文件**）。回源一律走 §3 给的**绝对行号**自读原文。

## 0. 身份 · 档位 · 边界（A261：一律以 **sha** 为锚，禁写 tag）

| 项 | 值 |
|---|---|
| 派单基线 HEAD（短 sha） | `bd7f89c` |
| 派单基线 HEAD（全 sha） | `bd7f89c127e8e38f65833dc104c7f73e797454e7` |
| 分支 | `m0-framework` |
| 任务 / 子任务 | `M2-01` / **S6**（该任务第 **6** 棒；S1–S5 均已 DONE） |
| lane 双键（PRE-31） | (`lane`=`S6`, `task`=`M2-01`)。⚠ 仓内已有 `lane=='S6'` 属 **M0-04**（R18，已 RETURNED_LANDED）⇒ **禁按 lane 单键定位本棒** |
| 档位 / reasoning | **`qwen3.8-flash`** / `medium`（任务卡 `orchestrator/tasks/M2-01.md:46` 档位表原文冻结；**禁自行升降档**，需升降走 §8 U 项上报） |
| loop 上限 | **2** 轮（手册 §15.6；第 2 轮仍红即写 BLOCKER 并附「缩小范围」降级交付选项） |
| token 预算 | **7k**（任务卡档位表原值） |
| critical / slack | `critical=false` / `slack=4`（台账实取值）。**但** S6 是 M2-01 的必经棒：S7 判 AC-002/003/004 依赖它，**不得跳棒** |
| 并行对象 | **M1-01/S1**（L1 lane，`qwen3.8-max`）。写权面已由编排器按 PRE-5 三判据实测**不相交**（见 §1.4）⇒ 你**只会**看到自己的 7 件在飞；若 `git status` 出现**不属于** §1.1 的第三方面，一律**禁碰**并按 §8 上报（A161 在飞污染） |

**上工第一件事（V0 基线自证）**：复测 HEAD 是否仍为 `bd7f89c`。若已漂移（编排器自身的纯文档/纯台账提交所致），
**依 A269 先例：U-BASELINE 已由编排器在本派单文预裁关闭** —— 以 spawn message 里逐字给出的**取代后权威读数**为准，
禁自行停手；除此之外的任何漂移（含代码面 sha 变化）一律停手报 `U-BASELINE`。

## 1. 写权面（越界即回报编排器，手册 §6.4；禁「顺手改」）

### 1.1 只新建（**恰 7 件**，一件不多一件不少）

1. `tests/api/activities/conftest.py`
2. `tests/api/activities/test_etag.py`
3. `tests/api/activities/test_conflicts.py`
4. `tests/api/activities/test_rule_diff.py`
5. `tests/api/activities/test_bindings_api.py`
6. `tests/api/activities/test_list_filters.py`
7. `tests/api/activities/test_contract_declarations_m2.py`

`conftest.py` 的必备件（design §11.7 原文，绝对行 **1136–1143**）：`REPO` / `SLICE`（读
`orchestrator/handoff/M2-01.slice.json`）/ `LIVE_CONTRACT` / `DDL` / `T0` / `GUARD` / `IDENTITY` /
`harness`（体例照 `tests/api/conftest.py::Harness`：`create_app()` 的注入位**显式给齐**、DDL 从活契约建库、
时间一律 `FixedClock`）/ `seed_evidence(ws, *, artifact_id, evidence_id)`（**只**用 SQL 播种 `artifacts` +
`evidence` 两行，§3.4；**禁** import `api/evidence.py`）/ `seed_activity(...)` / `idem_key()` /
`authed_client` / `create_activity_json(...)` / `create_rule_json(...)`。

⚠ **`conftest.py` 与既有 `tests/api/conftest.py` 同 basename** ⇒ 落盘后**必须**跑一次**全树** mypy（V15，
LANE-COMMON §3.6 `rule_full_tree_mypy_on_basename_collision`：路径限定 mypy **不**触发跨目录重复模块名检测）。

### 1.2 只修改：**无**（本棒是纯新建棒，`git diff --numstat` 的 `deleted` 列必须全 0）

### 1.3 硬禁面（**一字不改**；改了就判越界、整批回滚）

- `tests/api/activities/__init__.py` —— ⚠ **依 A272（本文 §5）本件已在仓**（实测 **1 行 / 89 B / sha12
  `8ccc54fe0ab9`**，单行 docstring 形态），design §11.7 把它列为「空文件·新建」属**失真** ⇒ 本件**转硬禁面**，
  禁重写、禁「补成空文件」、禁改 docstring。
- `tests/api/activities/test_activities_router_s3.py`（S3 的交付件，sha12 `e4d1d145cca5`；含
  `test_update_activity_etag412_stale_and_missing_if_match_428`，与你的新用例**同 gate 字面量但不同名**，共存合法）。
- `tests/api/conftest.py`（sha12 `2df41d5585dd`）· `tests/api/test_contract_http.py`（`d2015097b0ef`）·
  `tests/api/test_contract_declarations.py`（`a9af20101fe7`，绑定 **M0-02** 切片且自身明载 **N5 禁第二真源**）。
- `src/**` 全部（含 `api/activities.py` `3865f3eb6b3c`、`api/rules.py` `eac1377a4b72`、`api/common.py`
  `b2908617d193`、`application/activity_service.py`、`domain/activity/**`）。
- `tests/unit/**`（含**前提哨兵** `tests/unit/test_domain_errors.py` `ff4c25a659b6`、
  `tests/unit/test_if_match_pattern_single_source.py`、`tests/unit/test_s2b_activity_service.py`）·
  `tests/domain/**`（S5 的 9 件）· `tests/integration/**`（含 `test_jobs_router_s4.py` `ddd3ba8c362f`）·
  `tests/contract/**` · 各级 `conftest.py`（除 §1.1 第 1 件）· `fixtures/**` ·
  `pyproject.toml` / `ruff.toml` / `mypy.ini` · `scripts/**` · `migrations/**` ·
  `spec/**` · `contracts/**` · `orchestrator/state.json` · `orchestrator/handoff/**` · `evidence/**`（**归 S7**）·
  `web/**` · `qa-reports/**`。
- **禁**执行任何 `git commit / push / add / reset / checkout`（入库由编排器做）；**禁** sudo。

### 1.4 PRE-5 写集不相交三判据（编排器实测，你无需复做，但**禁越出**）

① 路径前缀集不相交：本棒 ⊂ `tests/api/activities/`，并行棒 M1-01/S1 ⊂ `orchestrator/handoff/M1-01-design.md`
（单件）⇒ 交集 ∅。② 无共享包标记：`tests/api/activities/__init__.py` 已存在且**双方均禁改**。
③ 无共享冻结面：S1 是**纯设计文档棒**（零 `src/**`、零 `tests/**`）⇒ 与本棒的 mypy/pytest 分母无交叉改动。

## 2. 预期红清单（PRE-14；由编排器**实测**得出，非推测）

**空集**（本棒落盘后不应有任何既有用例判红）。实测依据：

- 全仓 AST 实取测试函数 **647** 个，与 §6.1 的 **43** 个新用例名做集合对撞 ⇒ 交集 **0**（逐名核过）。
- 三个 gate 字面量的**当前**命中面（`tests/api/activities` 路径内）：`-k etag412` = **1** 例（S3 的
  `test_update_activity_etag412_stale_and_missing_if_match_428`，已绿）；`-k dup_external` = **0** 例（全仓 0）；
  `-k rule_diff` = **0** 例（全仓 4 例**全在** `tests/domain/activity/test_diff.py`，不在本 gate 路径内）
  ⇒ **V4 / V5 当前必红（rc=5 无用例可跑）**，正是本棒要清偿的；V2 当前已绿，本棒把它**加厚**到三端点 × 412/428。
- **前提哨兵提示（PRE-41）**：`tests/api/test_contract_declarations.py::test_no_if_match_declared_so_412_and_428_are_unreachable`
  与 `tests/unit/test_if_match_pattern_single_source.py`（**5 判据 + 6 阳性对照 = 11 例**）都钉住了
  `IF_MATCH_PATTERN` 的形态与 `common.__all__` 的项数（现值 **80**）。你在硬禁面**外**工作，正常不会碰到它们；
  但若你的用例试图改契约声明面或 `__all__`，**立刻停手走 §8**。

## 3. 逐字口径回源（PRE-29：禁采信二手复述，一律回源到下列**行号**自读原文）

`orchestrator/handoff/M2-01-design.md`（**1396 行 / 153979 B / sha12 `2d39feaac2d1`**，只读）：

| 你要什么 | 绝对行 |
|---|---|
| **§11.7 本棒的文件级 TODO（权威写集与用例名清单）** | **1135–1179** |
| §10 验证清单 V1–V15（命令 → 期望 rc） | 930–952 |
| §6.1 ETag 出现面（逐 op 以切片 `operation.responses.<2xx>.headers` 实取，禁发明） | 613–640 |
| §6.2 **428 / 412 的实现口径**（含「让 428 永不可达」的陷阱） | 641–659 |
| §6.3 判定顺序（五个写 op 统一流水线；**顺序即代码顺序，禁调序**） | 660–678 |
| §6.4 409 / 422 家族逐码触发面（只用 20 码注册表内的码；码名以 `domain/errors.py::PROBLEM_CODES` **实取**） | 679–723 |
| §6.5「409 的 `diff` 字段」口径（**按契约冻结**，派单文措辞与契约不符时以此为准） | 724–756 |
| §6.6 声明为**不可达**的注册表码（断言「不可达」本身，**禁** `skip` / `xfail`、禁写会红的用例） | 757–765 |
| §3.2 规则版本状态机 ＋ **`set_current_rule` SQL 原文**（FU-54 要求逐字携带，见 §5） | 284–319 |
| §3.4 绑定（有效期区间代数；`Binding` 5 字段全必填、无 `id`） | 328–353 |
| §1.1 / §1.5 列表过滤与 `status` 参数命名陷阱 | 22–134 |
| §4.6 规则摘要（`rule_digest`）的固定投影（`label`-only 更新改 ETag 不改摘要的依据） | 444–463 |
| §7.5 显式时钟、ID 前缀与幂等键（幂等重放返回**原** ETag 的依据） | 834–855 |
| §8 逐 op 的**可达码矩阵** | 856–876 |
| §9 边界清单（AC → 实现约束 → 已知失败模式） | 877–929 |
| §14.2 **A232**（specific 覆盖 general 的 SQL 谓词，禁补 guard 镜像） | 1350–1376 |

被测生产面（**只读**，取值口径来源）：`src/campaignlab/api/activities.py`（路由 `list_activities`:96 ·
`create_activity`:127 · `get_activity`:163 · `update_activity`:184；`IF_MATCH_PATTERN` import :37、使用 :194）、
`src/campaignlab/api/rules.py`（`list_rules`:147 · `create_rule`:185 · `get_rule`:225 · `update_rule`:250 ·
`confirm_rule`:298 · `check_rule`:345 · `compare_rules`:370；`IF_MATCH_PATTERN` 使用 :260 / :308）、
`src/campaignlab/api/common.py`（**`IF_MATCH_PATTERN: Final = r'^"[1-9][0-9]*"$'` 在 :190**，已在 `__all__` :88；
`etag()` :838、`check_if_match()` :843 —— 缺头 → **428 `PRECONDITION_REQUIRED`**、不匹配 → **412 `REVISION_CONFLICT`**）。

路由路径（实测逐字）：`/workspaces/{workspace_id}/activities`（GET :91 / POST :122）·
`/workspaces/{workspace_id}/activities/{activity_id}`（GET :158 / **PATCH** :179）·
`/workspaces/{workspace_id}/activities/{activity_id}/rules`（GET :142 / POST :180）·
`/workspaces/{workspace_id}/rules/{rule_id}`（GET :220 / **PATCH** :245）·
`/workspaces/{workspace_id}/rules/{rule_id}/confirm`（**POST** :293）。
⚠ 三个 If-Match 端点 = `updateActivity`(PATCH) / `updateRule`(PATCH) / `confirmRule`(POST)。

## 4. 冻结面实测读数（编排器于 `bd7f89c` 时点实测；你上工**必须自行复测**并贴命令原文）

### 4.1 仓面

```text
counts（权威位点＝state.json -> resume.self_check_gates_rc0.counts，禁写死别处）
  ruff_formatted_files = 343   （组成：in_scope_py 125 + in_scope_md 218）
  mypy_source_files    = 123
  pytest_passed        = 809   （= frozen 788 + GIT_ENV_IGNORES 21）
  contract_registered_nodes = 13 · acceptance_denominator = 47 · acceptance_resolvable = 47
  live_openapi_sha16 = 592571099d638251 · live_openapi_info_version = 1.0.1
```

你落盘 **7 件**（全 `.py`）后的**期望**：`in_scope_py` 125 → **132**、`ruff_formatted_files` 343 → **350**、
`in_scope_md` **218 不变**、`mypy_source_files` 123 → **130**、`pytest_passed` 809 → **809 + N**
（N = 你 `--collect-only` 实取的**净新增** collected 数，期望 **43**；禁凭记忆、禁用 `-k` 过滤后的数字冒充全量）。
`mypy` 分母 +7 的前提是 7 件全部入 mypy 作用域；若实测不是 +7，**如实报**、禁改口径（C10）。

### 4.2 关键分母（一律**实取**，禁写死；实取命令见 §6.2）

- `IF_MATCH_PATTERN` 的值与 `len(common.__all__)`（现值 **80**）—— 依 **FU-64**：`M2-01-design.md:215` 那句
  「`IF_MATCH_PATTERN` **不在** `__all__` 里」自 FU-59 / A271 起**已失真**，**禁引用**；权威读法＝
  「定义于 `api/common.py:190`、**已在** `__all__` 内（`common.py:88`）、值逐字 == 契约 pattern（运行期实测）」。
  同族失真还有 design `:82` 与 `:649-650`（要求 `pattern=IF_MATCH_PATTERN` —— 该要求现已**可执行且已被执行**）。
- 11 个 operationId 的 2xx 声明集：**从 `orchestrator/handoff/M2-01.slice.json` 实取**（A257 / A95 口径），禁写死。
- `PROBLEM_CODES`（20 码注册表）：从 `src/campaignlab/domain/errors.py` **实取**。
- §6.6 的**五个不可达码**：从 design 757–765 行**自读原文**取名单，禁凭记忆。

### 4.3 构造陷阱（编排器实测，逐字告你）

1. **428 可达性的前提**：`if_match` 必须声明为**可选形参**（`Header(default=None, pattern=IF_MATCH_PATTERN)`）。
   若按契约字面声明 `required=true`，缺头会在进入函数体前被 FastAPI 判 **422**，428 **永不可达**
   （design §6.2；体例先例＝`api/jobs.py::cancel_job` 的 **A228**）。生产面**已按此实现**（activities.py:194、
   rules.py:260/:308）⇒ 你写 428 用例时**直接发无 `If-Match` 头的请求**即可，**禁**去改生产面。
2. **畸形 `If-Match` → 422**（不是 412）：`pattern=` 不匹配时由 FastAPI 参数校验层拦截 ⇒
   `test_malformed_if_match_is_422` 的期望码是 **422**。
3. **运行期状态码断言结构性 NO_TEETH（A260）**：三个写 op 一律走信封路径且处理器**直接返回 `Response`**
   ⇒ 装饰器 `status_code` 被短路。**禁**写「TestClient 实测 == 200/201」这类**声明面**断言；
   状态码的判据面**只能是**「路由装饰器的 2xx 声明集 vs 切片的 2xx 声明集」对撞（`route.responses`）。
   注意区分：**响应实际状态码**（如 412/428/409/422，由 service 抛出、经 error handler 转 Problem）是**可断言**的；
   A260 禁的是**2xx 声明面**的运行期断言。
4. **`ETag` 形态**：`"<revision>"` —— 带双引号的十进制整数，其字面必须 `fullmatch(IF_MATCH_PATTERN)`
   （`common.py:839` docstring 原文）。断言 ETag 时**含双引号**一起断。
5. **幂等重放**：命中幂等键的重放返回**原** ETag，即使带了**错误**的 `If-Match`（design §7.5 末条）⇒
   处置顺序是「先幂等、再 If-Match」（`api/jobs.py:229` 同族先例）。
6. **列表页无 ETag**（design §6.1）⇒ `test_list_pages_have_no_etag_header` 断言**响应头里没有** `ETag`。
7. **SQLite NULL 语义**：`bank_id` 为 NULL 时**永不**触发 `dup_external`（NULL ≠ NULL）⇒ 用例须显式覆盖。
8. **探针禁落工作树**（LANE-COMMON §6 / design §10 末段）：阳性对照一律用 pytest 的 `tmp_path`，
   **禁**在仓库里留临时文件（会污染 ruff/mypy 分母）。

## 5. 本棒携带的裁定与义务（append-only；**不得推翻**，有异议走 §8 上报）

### A272（本批新裁）· `tests/api/activities/__init__.py` 已存在 ⇒ 写权面 **7 件**、该件转硬禁面

design §11.7（绝对行 **1136**）把 `tests/api/activities/__init__.py`（**空文件**）列为本棒新建件。
编排器实测：该件**已在仓**，**1 行 / 89 B / sha12 `8ccc54fe0ab9`**，形态是**单行 docstring**
（与 **A262** 对 `tests/domain/__init__.py` 的裁定同族：仓内既有 tests 包标记**无一**为零字节 ⇒
**specific 覆盖 general**，A232 同族）。**裁定**：① 本棒写权面＝**7 件**（`conftest.py` + 6 个 `test_*.py`），
`__init__.py` **不在**写集内；② 该件**转入硬禁面**，禁重写、禁清空、禁改 docstring；
③ design 原文按 **D-011 不改写**，其权威读法＝本裁定。

### A273（本批新裁）· §11.7 的 `test_missing_if_match_is_428_not_422` 字面自相矛盾 ⇒ 展开为**三条**具名函数

design §11.7（绝对行 **1144–1149**）原文：`` `test_missing_if_match_is_428_not_422`（三个端点各一条；
**函数名必须含 `etag412`**，V2 的 `-k` 字面量）``。**三重矛盾**：① 只给**一个**函数名却说「三个端点各一条」；
② 该名字**不含** `etag412`，与同句「函数名必须含 `etag412`」直接冲突；③ 任务卡 gate 原文要求
「`updateActivity`、`updateRule`、`confirmRule` **三个** If-Match 端点的端到端 **412/428** 必须在此落证」
（`orchestrator/tasks/M2-01.md` 的 gates 段，M0-02 裁定 **Q3 `RULING_NARROW_GATE_DEFER_HTTP`** 点名本卡为
`deferred_to` 承接方）。**裁定**：展开为**三条**具名函数，逐字冻结（含 `etag412` 以满足 V2 的 `-k`；
命名族与三条 412 用例同构 = **D-044** 形态）：

```text
test_update_activity_etag412_missing_if_match_is_428_not_422
test_update_rule_etag412_missing_if_match_is_428_not_422
test_confirm_rule_etag412_missing_if_match_is_428_not_422
```

design 原文按 **D-011 不改写**，其权威读法＝本裁定。

### A274（本批新裁）· FU-54 的 ①② 在 §11.7 无具名落点 ⇒ `test_etag.py` 追加**两条**

**FU-54**（台账 `resume.followups[FU-54]`，P2，owner = **M2-01/S6**，源 = R16 **A232** / **D-048 §4** 残留风险）
原文义务：「① 顺序确认 A→B 后 `current_rule_id==B`；② 同一事务内两条规则版本各自 guard 通过时对
`current_rule_id` 的最终取值有明确断言；③ **若真实并发下判红，禁就地改 SQL，先立缺陷走 CR**
（可能形态＝`WHERE ... AND (current_rule_id IS NULL OR revision=:revision)`）。」
其 `ordering_note` 明载：「派单文**必须逐字携带**本 FU 与 §3.2 的 SQL 原文，禁让 lane 再猜一次口径。」
design §11.7 只有 `test_confirm_rule_bumps_activity_etag_and_current_rule_id`（覆盖 design §3.2 末段
「确认规则会使活动自身的 ETag 变化」），**未覆盖** FU-54 的 ①②。**裁定**：在 `test_etag.py` 追加两条，逐字冻结：

```text
test_current_rule_id_follows_the_latest_confirmed_successor_a_then_b
test_current_rule_id_tie_break_is_id_lexicographic_max_per_design_3_2
```

**§3.2 的 `set_current_rule` SQL 原文（逐字，design 绝对行 311–312）**：

```sql
UPDATE activities SET current_rule_id=:rule_id, revision=revision+1 WHERE workspace_id=:ws AND id=:activity_id
```

**§3.2 的取值规则原文（逐字，design 绝对行 316–318）**：「`current_rule_id` 取『该活动下 `confirmed_at`
最大者（并列时 `id` 字典序最大）』」。**A232 已裁定**：维持该 SQL 原文（specific 覆盖 general），
**禁补 guard 镜像**（补 guard 物理上需一次额外 SELECT，而 §3.2 明文禁裸先查后改）；并发安全由同一事务内
规则侧的 `state='DRAFT' AND revision=:revision AND digest=:digest` 谓词承担。⇒ 你的两条用例是**行为钉桩**：
若判红，**禁改 SQL、禁改生产码**，按 FU-54 ③ 走 §8 上报（编排器立缺陷 + CR）。

### 承前批裁定（逐字携带，**禁推翻**）

- **A270**：`SCHEMA_VERSION_UNSUPPORTED` 的**标签单一出处**在 domain 的 `CLAUSE_ISSUE_CODES`
  （`domain/activity/clauses.py:73`；`:64` 是设计期注释原文「判定在 api／service 层」），**唯一发射点**在
  `src/campaignlab/application/activity_service.py:218`（`_SCHEMA_VERSION_CODE: Final`）⇒ **发射面的对撞归本棒**。
  **禁**在 domain 增设发射点（会形成第二真源，违反 **N5** 与 **A257** 同族判例）。领域可达的同事实入口＝
  `checks.py` 的 `_CONST_BY_TEMPLATE` 含 `("schema_version", 1)`（实测 :125 / :131）⇒ `content["schema_version"] != 1`
  时 `run_checks` 报 `TEMPLATE_CONST_MISMATCH` @ `/content/schema_version`、severity `ERROR`（S5 已钉死领域侧）。
- **A257**：rules 的 **7** 个 operationId 的声明面／契约对撞**归本棒**（对撞
  `orchestrator/handoff/M2-01.slice.json`，实测在场 **4014 行 / 84893 B / sha12 `8f44b036f065`**）；
  **禁**塞进 `tests/api/test_contract_declarations.py`（该目录绑定 **M0-02** 切片且自身明载 **N5 禁第二真源**）。
  ⇒ 这就是 `test_contract_declarations_m2.py` 那 3 条用例的授权来源。
- **A260**：状态码判据面＝「**装饰器 2xx 声明 vs 切片 2xx**」；**禁**写运行期 2xx 状态码断言（结构性 NO_TEETH）。
- **A256 ＋ D-052 §9 / R18-11**：`_rule_check_response` **只做透传组装**、不做二次校验、**不设 500
  `INTERNAL_ERROR` 分支**。**正确理由（禁再抄「类型上不可达」）**＝校验点在**应用层**
  `application/activity_service.py:1925`。**禁**按 design §11.5（绝对行 1087–1089）的失真原文写必红用例
  （失真三重：符号实名 `BoundaryCase` 非 `BoundaryCaseDraft`；字段实名 `input` 非 `input_payload`；
  `CaseInput` 是 `Annotated` 别名、`hasattr(CaseInput,'model_validate')` 实测 **False**）。
- **A232**：见上文 A274 段（specific 覆盖 general，禁补 guard 镜像）。
- **A261**：派单文 §0 一律以 **sha** 为锚，禁写 tag（`git tag -l` 实测 0 项）。
- **A269 先例**：派单后 HEAD 因编排器自身纯文档/纯台账提交而漂移时，U-BASELINE 由编排器**预裁**关闭。
- **PRE-39（lane 侧命名约束，必携）**：你写 `.orch_tmp/` 的 scratch 件**必须**带**你自己的 lane 标识**
  （建议前缀 `s6m2_`），**禁**使用 `orch_` 前缀（那是**编排器专属**命名空间，碰撞会造成取证件混合编码 =
  R19-9 的实际事故形态）；凡你要交给编排器的取证件必须过**编码四判据**（严格 utf-8 可解 / 无 BOM·CR·NUL /
  无 C0·C1 控制符（`\n`/`\t` 除外）/ 以 `\n` 结尾）。
- **PRE-40**：冻结面 sha **已重定基**（FU-59 解冻批 `4637a5b` 之后）。`api/common.py` 的权威 sha12 是
  **`b2908617d193`**（**禁**沿用旧值 `836e7b3e8d3a`）；`api/activities.py` = `3865f3eb6b3c`、
  `api/rules.py` = `eac1377a4b72`、`api/jobs.py` = `e9b575602e56`。
- **PRE-41**：改动被多处钉桩的公共面前，普查必须按**被钉住的值**扫并跑全量 pytest 对撞。本棒**不改**任何公共面
  ⇒ 该条对你的实际含义是：**别去碰** §1.3 点名的前提哨兵文件。
- **PRE-21**（禁系统 python3，一律 `uv run --no-sync`；仓内 Python 实测 **3.14.10**）·
  **PRE-25/26/27**（符号定义点、枚举项数、契约面切片**实取**）· **PRE-29**（口径回源、**双向**禁采信）·
  **PRE-33**（符号对撞**全仓**范围）· **PRE-34**（区分 **rc=1** 断言红与 **rc=4** 收集期错误；行为守护的
  中间件前置处置）· **PRE-35**（哨兵全量普查）· **PRE-37 第 3 款**（跨通道复述的 sha/计数必须由同一赋值点派生）·
  **PRE-38**（preflight 判据须声明适用时点）。

## 6. 交付面 · 用例清单 · 门

### 6.1 六个测试文件的用例清单（design §11.7 逐字 ＋ 本文 §5 的 A273/A274 订正；**函数名一律逐字**）

**`test_etag.py`（13 条）**

```text
test_update_activity_etag412_rejects_stale_if_match
test_update_rule_etag412_rejects_stale_if_match
test_confirm_rule_etag412_rejects_stale_if_match
test_update_activity_etag412_missing_if_match_is_428_not_422      # A273
test_update_rule_etag412_missing_if_match_is_428_not_422           # A273
test_confirm_rule_etag412_missing_if_match_is_428_not_422          # A273
test_malformed_if_match_is_422
test_etag_is_quoted_decimal_revision
test_confirm_rule_bumps_activity_etag_and_current_rule_id          # V9 的 -k current_rule
test_current_rule_id_follows_the_latest_confirmed_successor_a_then_b   # A274 / FU-54 ①
test_current_rule_id_tie_break_is_id_lexicographic_max_per_design_3_2  # A274 / FU-54 ②
test_replay_returns_the_original_etag_even_with_a_wrong_if_match   # design §7.5 末条
test_label_only_update_changes_etag_but_not_digest                 # design §4.6 的反直觉面
```

**`test_conflicts.py`（10 条）**

```text
test_dup_external_activity_id_is_409_with_two_issues               # V4 的 -k dup_external；断言两条 issues 的 location 与 message 含既有活动 ID
test_dup_external_race_falls_back_to_409_not_500
test_null_bank_id_never_triggers_dup_external                      # SQLite NULL 语义，design §6.4
test_idempotency_conflict_is_409
test_empty_patch_is_422
test_archived_activity_rejects_update_409
test_confirmed_rule_rejects_update_409_and_writes_denied_audit     # AC-003 的「试编辑」+ 审计留痕
test_confirm_with_stale_digest_is_409_version_mismatch
test_confirm_without_required_clause_is_422_evidence_required      # AC-004 的 HTTP 面
test_unreachable_codes_are_declared_but_unreachable                # design §6.6 的五个码；断言不可达本身，禁 skip/xfail
```

**`test_rule_diff.py`（4 条）**

```text
test_rule_diff_shows_changed_fields_sources_and_digest             # V5 的 -k rule_diff；AC-003「差异字段、条款来源和摘要」三件一起断言
test_rule_diff_cross_template_is_422
test_rule_diff_requires_rerun_case_ids_is_empty_when_no_change
test_rule_diff_across_workspaces_is_404
```

**`test_bindings_api.py`（5 条；函数名一律含 `binding`，V8）**

```text
test_binding_full_replacement_semantics
test_binding_absent_from_patch_leaves_rows_untouched               # AC-002 的「保持无绑定」
test_binding_overlap_is_422
test_binding_unregistered_evidence_is_422_evidence_required
test_binding_empty_interval_is_422_not_500
```

**`test_list_filters.py`（8 条；前 5 条函数名一律含 `list_filter`，V10）**

```text
test_list_filter_by_status_multi_value
test_list_filter_by_q_matches_name_and_external_id
test_list_filter_unknown_status_is_422
test_list_filter_cursor_binds_all_four_params
test_list_filter_bad_cursor_is_400_with_the_frozen_detail
test_list_rules_status_param_filters_the_state_column              # design §1.5 的命名陷阱（不含 list_filter，合法）
test_list_pages_have_no_etag_header                               # design §6.1
test_cross_workspace_is_404
```

**`test_contract_declarations_m2.py`（3 条；A257 授权）**

```text
test_declared_responses_match_the_slice_for_all_eleven_ops         # route.responses vs 切片 operations.<opId>.operation.responses（A95 口径；期望值从切片实取，禁写死）
test_operation_id_matches_function_name_for_all_eleven_ops
test_every_problem_code_used_here_is_in_the_registry               # 体例＝tests/api/test_contract_declarations.py::_CODES_USED_BY_THIS_DIRECTORY
```

**合计 43 条**（13 + 10 + 4 + 5 + 8 + 3）。这个数目由上面清单**逐行数出**；若你的实测 collect 数与之不符，
**如实报差异并解释**，禁改口径凑数（C10）。参数化（`@pytest.mark.parametrize`）会让 collected > 43，
那是**允许**的 —— 回执里同时报「函数名 43 个（AST 实取）」与「collected N 例」两个数。

### 6.2 门（rc 必须全 0；命令原文与输出尾部**逐字**贴进回执，禁只写「通过」）

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
cd /home/szf/dev/CampaignLab

# V0 基线自证（不等即停手，除 A269 预裁的编排器自身提交外报 U-BASELINE）
git rev-parse HEAD; git rev-parse --abbrev-ref HEAD; git status --porcelain

# V1 你的 7 件 face（行数/字节/sha256[:12]），逐件报
for f in tests/api/activities/conftest.py tests/api/activities/test_etag.py \
         tests/api/activities/test_conflicts.py tests/api/activities/test_rule_diff.py \
         tests/api/activities/test_bindings_api.py tests/api/activities/test_list_filters.py \
         tests/api/activities/test_contract_declarations_m2.py; do
  wc -l -c "$f"; sha256sum "$f"; done

# V2 用例名对撞（AST 实取，逐名核对 §6.1；禁采信你自己的记忆）
uv run --no-sync python -c 'import ast,pathlib;[print(p.name,n.name) for p in sorted(pathlib.Path("tests/api/activities").glob("test_*.py")) for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith("test_")]'

# V3 任务卡的四个 gate 字面量（V2/V4/V5/V8/V9/V10 对应 design §10）
uv run --no-sync pytest -q tests/api/activities -k etag412        # design V2 · 期望 rc=0
uv run --no-sync pytest -q tests/api/activities -k dup_external   # design V4 · 期望 rc=0
uv run --no-sync pytest -q tests/api/activities -k rule_diff      # design V5 · 期望 rc=0
uv run --no-sync pytest -q tests/api/activities -k binding        # design V8 · 期望 rc=0
uv run --no-sync pytest -q tests/api/activities -k current_rule   # design V9 · 期望 rc=0
uv run --no-sync pytest -q tests/api/activities -k list_filter    # design V10 · 期望 rc=0

# V6 本目录全量 ＋ 领域层未回归（design V11）
uv run --no-sync pytest -q tests/api/activities
uv run --no-sync pytest -q tests/domain/activity
uv run --no-sync pytest -q tests/domain/activity -k immutable     # design V1
uv run --no-sync pytest -q tests/domain/activity -k clause_gate   # design V3

# V7 ruff（格式 + lint）
uv run --no-sync ruff format --check . ; uv run --no-sync ruff check .

# V8 mypy strict 全仓（你的 7 件入域 ⇒ 期望 130 source files）
uv run --no-sync mypy

# V9 全量 pytest（期望 809 + N passed / 0 failed；N 与 --collect-only 的净新增都要报）
uv run --no-sync pytest -q --collect-only 2>&1 | tail -3
uv run --no-sync pytest -q 2>&1 | tail -5

# V10 契约门禁未回归 ＋ 切片新鲜度（design V13 / V14）
uv run --no-sync python scripts/check_contracts.py check --validate
uv run --no-sync python -c "import hashlib,pathlib;d=pathlib.Path('contracts/openapi.json').read_bytes();print(hashlib.sha256(d).hexdigest()[:16],len(d))"

# V11 硬禁面零改动（输出**必须只有**你的 7 件 ??，其余为空）
git status --porcelain
git diff --numstat            # deleted 列必须全 0

# V15 全树 mypy（同 basename conftest 强制项，LANE-COMMON §3.6）—— 与 V8 同命令，须在 7 件**全部落盘后**再跑一次
uv run --no-sync mypy
```

## 7. 阳性对照（PC；**每条先实证「有牙」再报绿**；PRE-34：区分 rc=4 收集期错误与 rc=1 断言红）

探针一律在 `tmp_path` 内做，**禁落工作树**；每次变异后必须**复原**并用 sha256 **双向**核验（变异前 / 复原后两个摘要都进回执）。

| # | 变异 | 期望 |
|---|---|---|
| PC-A | 把 `test_etag.py` 里某条 412 用例的期望码从 412 改成 413 | 该例 rc=**1** 判红（证明断言真的在读响应码，不是永绿） |
| PC-B | 把 `test_conflicts.py::test_dup_external_activity_id_is_409_with_two_issues` 的 `issues` 条数期望从 2 改成 1 | rc=**1** 判红 |
| PC-C | 把 `test_contract_declarations_m2.py` 的切片 2xx 期望集**人为改一个码**（在 `tmp_path` 的切片副本上） | rc=**1** 判红（证明对撞的是**切片**而非硬编码） |
| PC-D | 把 `test_rule_diff.py::test_rule_diff_shows_changed_fields_sources_and_digest` 的三件断言之一删掉 | rc=**1** 判红（证明三件都在断） |
| PC-E | 把 `test_bindings_api.py` 某条的期望码 422 改成 500 | rc=**1** 判红 |

做不到有牙的一律**如实标 `NO_TEETH`**、禁标 PASS（手册 §15.4 / A159 / PRE-33）。
⚠ **A260 提醒**：不要拿「运行期 2xx 状态码」当 PC 对象 —— 那个面**结构性 NO_TEETH**，做不出有牙的变异。

## 8. U 项上报（**禁自行裁定**；手册 §6.4）

遇下列情形**立刻停手**，在回执里以 `U-<n>` 编号上报，附**实测命令与原文输出**：

- 需要改任何 §1.3 硬禁面（含「顺手修一个明显的 bug」）；
- design §11.7 / §6.x / §3.2 的原文与**实测生产面**冲突，且本文 §5 未给裁定；
- 需要新增 §6.1 之外的用例名，或需要**删减** §6.1 点名的用例（禁静默跳过）；
- 任何 gate 判红且 **2 轮** loop 内未收敛（写 BLOCKER ＋ 附「缩小范围」的降级交付选项）；
- FU-54 ③ 的情形：`current_rule_id` 在并发/顺序确认下判红 ⇒ **禁就地改 SQL**，上报走 CR；
- 出现不属于 §1.1 的第三方面改动（并行棒污染，A161）；
- 需要升档（flash → max）：判据＝同任务 2 轮验证失败 / 需改契约 / 需跨文件推断 / 需新写算法 /
  触及金额·分母·状态语义。上报时**必须附「已排除假设」**（手册 §6.5）。

## 9. 派单前置自检（编排器已逐项做完；你只需在回执里**复述结论 ＋ 贴你自己的复测命令**，禁跳过）

| PRE | 编排器做了什么 | 你要复述什么 |
|---|---|---|
| PRE-13 | 本派单文 ＋ `dispatch_log` ＋ `in_flight_agents` **先入库**，spawn 排其后，`agent_id` 由 spawn 后的纯台账批回填（禁填猜测值） | 无需动作 |
| PRE-14 | 预期红清单**实测为空**（647 个既有函数名 vs 43 个新名，交集 0）；并实测 V4/V5 当前**必红**（0 例可跑）⇒ 本棒清偿 | 复测 §2 的三个 `-k` 命中数 |
| PRE-15 | 全部冻结面读数由脚本实测（§4），命令原文已贴 | 复测 §4.1 的 counts 与 §4.2 的分母 |
| PRE-20/24 | design §11.7 的具名件与具名函数已逐个做**仓内实存对撞**：发现 **3 处**失真 ⇒ **A272 / A273 / A274** 已裁，实测口径写进 §5/§6.1，**禁把失真原文抄给你去踩** | 复述 A272/A273/A274 的结论 |
| PRE-25/26/27 | 符号定义点、枚举项数、契约面一律**实取**（`IF_MATCH_PATTERN` @ `common.py:190`、`len(common.__all__)==80`、11 个 op 的 2xx 从切片实取） | 复测并贴实取输出 |
| PRE-29 | §3 给的是**绝对行号**而非二手复述，并明写「冲突以原文为准」；V9 明禁「用 `-k` 过滤后报全绿冒充全量」 | 回执里逐条回源 |
| PRE-31 | **双键定位**：(`S6`,`M2-01`) 不在册；且已断言「同 lane 异 task 的干扰条实存」＝`in_flight_agents[6]`/`dispatch_log[13]` 的 (`S6`,`M0-04`) ⇒ 证明按 lane 单键查找**必然错配** | 无需动作 |
| PRE-33/34 | PC 五条均要求「先实证形态成立、再看读数」，并逐字携带 rc=1 vs rc=4 的区分口径 | §7 逐条报 PASS/NO_TEETH |
| PRE-39 | 你的 scratch 命名约束与取证件编码四判据已写进 §5 | 回执声明你的 scratch 前缀 |
| PRE-40/41 | 冻结面 sha 已重定基（§5 逐字给出新值）；前提哨兵清单已点名（§1.3 / §2） | 复测 §1.3 的 sha12 |

## 10. 回执格式（**结构化**，禁散文；编排器会**独立复验**每一项，禁采信自报）

纯文本，**≤ 90 行**（LANE-COMMON §7）。逐段给：

1. `TIER_CONFIRM`：你实际运行的 model 与 reasoning（本环境若不暴露模型身份自证面，**如实说明**并按派单档位申报；编排器**不采信自报**，以档位裁定原文为准）。
2. `BASELINE`：V0 的三行输出原文（HEAD / branch / status）。
3. `FACES`：V1 的 7 件 face（逐件 `lines / bytes / sha256[:12]`）。
4. `NAMES`：V2 的 AST 实取函数名**全清单** ＋ 总数（期望 43）＋ collected 数。
5. `GATES`：V3–V15 逐条「命令原文 → rc → 输出尾部逐字」。
6. `COUNTS`：你实测的 `ruff_formatted_files / mypy_source_files / pytest_passed / in_scope_py / in_scope_md`
   与 §4.1 期望值的**逐项对照**（不符即如实报差并解释，禁改口径）。
7. `PC`：§7 五条逐条 `PASS` / `NO_TEETH` ＋ 变异前后两个 sha256（复原核验）。
8. `HARDEN`：§1.3 硬禁面**零改动**自证（`git status --porcelain` 原文 ＋ `git diff --numstat` 原文）。
9. `U`：§8 的 U 项（无则写 `NONE`）。
10. `RESULT`：`DONE` / `DONE_WITH_GAP`（附 gap 清单）/ `PARTIAL` / `BLOCKED`（附 BLOCKER 与降级选项）＋ loop 实耗轮数。
