# R19 · Lane S5 · M2-01/S5 派单文 —— `tests/domain/activity/**` 只新建（9 件）

> 本文件是**派单契约**。你（lane S5）必须逐字遵守；有异议只走 §8 的 U 项上报，**禁自行裁定、禁顺手改**。
> 同时读 `orchestrator/handoff/LANE-COMMON.md`（全 lane 通用纪律：loop 帽、禁 commit/push、回执结构、禁采信自报）。
> 本文件里所有数字都是编排器在 predispatch 时点**实测**得出的（PRE-15/20/24/26/30）；你上工后**必须自行复测**并把命令原文贴进回执（PRE-29：禁采信二手复述，包括本文件）。

---

## 0. 身份 · 档位 · 边界（A261：一律以 **sha** 为锚，禁写 tag）

| 项 | 值 |
|---|---|
| lane / task / round | **S5** / **M2-01** / **19** |
| 子任务 | design §11.6 ＋ §11.1 末条（`tests/domain/activity/**` 的领域层用例面） |
| model / reasoning | **`qwen3.8-flash`** / **medium** |
| 档位依据（卡片原文冻结，禁改） | `orchestrator/tasks/M2-01.md:46`：「S5 条款与不可变性参数化用例展开（六项 / 三项确认矩阵 x 错误阻止 x 警告需备注）〔低复杂度：按已冻结签名机械展开矩阵，无新算法、无跨模块判断；产物为可复跑的机械铺开，无 §6.3 强制 max 触发项〕 \| `qwen3.8-flash` \| 8k \| `tests/domain/activity/**`」 |
| **基线 sha** | **`0765099`**（`git rev-parse HEAD` 必须逐字等于它；不等 ⇒ **立即停手报 U-BASELINE**，禁在非基线树上写码） |
| 基线读数 | counts 328 / 113 / 750（115 py + 213 md）；`pytest --collect-only -q` = **750 tests collected** |
| critical / slack | false / 4（**但**：S5 是 M2-01 的必经棒，S7 判 AC-002/003/004 需要它；不得跳棒） |
| loop 帽 | **2**（超帽即停手回报现状，禁硬闯；每轮必须写明「上一轮红在哪、这一轮改了什么」） |
| 禁做 | `git commit` / `git push` / `git tag` / 改 `orchestrator/state.json` / 改任何既有文件 / 新建 §1.1 之外的任何文件 |
| 并发提示 | 编排器可能在你飞行期间落**治理批**（FU-59：`api/common.py` 纯追加 `IF_MATCH_PATTERN` ＋ 三处内联字面量改 import ＋ 新哨兵）。它**不动** `domain/activity/**`、不动 `canonical_json`、不动你的写权面 ⇒ 你**无需**因此改动任何东西；若你复测 HEAD 发现 sha 变了，按 §8 报 **U-BASELINE** 并附实测 sha，禁自行推断。 |

---

## 1. 写权面（越界即回报编排器，手册 §6.4；禁「顺手改」）

### 1.1 只新建（**恰 9 件**，一件不多一件不少）

| # | 路径 | 说明 |
|---|---|---|
| 1 | `tests/domain/__init__.py` | ⚠**写权缺口**：不在卡片 `scope_allow` 的 `tests/domain/activity/**` 字面量内 ⇒ 由 **A262** 授权（design §11.9 行 1201 点名，先例＝M1-03 的 N1） |
| 2 | `tests/domain/activity/__init__.py` | 在 scope 内 |
| 3 | `tests/domain/activity/test_states.py` | §6.1-A |
| 4 | `tests/domain/activity/test_clause_gate.py` | §6.1-B |
| 5 | `tests/domain/activity/test_digest.py` | §6.1-C |
| 6 | `tests/domain/activity/test_bindings.py` | §6.1-D |
| 7 | `tests/domain/activity/test_checks.py` | §6.1-E |
| 8 | `tests/domain/activity/test_diff.py` | §6.1-F |
| 9 | `tests/domain/activity/test_layering.py` | §6.1-G（design §11.1 末条，行 1011-1014） |

两个 `__init__.py` 的**形态由 A262 冻结**：单行 docstring（照 `tests/api/activities/__init__.py` 的体例，89 B），**不是**零字节空文件。理由见 §5 的 A262。

### 1.2 只修改：**无**（本棒是纯新建棒，`numstat deleted` 必须全 0）

### 1.3 硬禁面（**一字不改**；改了就判越界、整批回滚）

- `src/**` 全部 —— 含 `src/campaignlab/domain/activity/**`（你要测的对象）、`src/campaignlab/api/common.py`、`application/**`、`infra/**`、`worker/**`
- `tests/unit/**`、`tests/api/**`、`tests/integration/**`、`tests/conftest.py`、`tests/__init__.py`
- `orchestrator/**`（含 `state.json`、任务卡、design）、`scripts/**`、`contracts/**`、`spec/**`、`migrations/**`、`web/**`、`docs/**`、`evidence/**`、`qa-reports/**`、`pyproject.toml`、`uv.lock`

> **PRE-34 提醒**：本棒全部是**领域层纯函数**用例，不经中间件、不起 TestClient ⇒ 不需要 `Origin` 头之类的前置处置。若你发现某个断言必须走 HTTP 才能验，**那是 S6 的活**（A257：rules 的 7-op 契约对撞归 S6），按 §8 报 U，禁自己起 client。

---

## 2. 预期红清单（PRE-14；由编排器**实测**得出，非推测）

**实测结论：本棒的预期红清单为「空」。** 依据（三条实测，命令原文见 §9）：

1. `tests/domain` 目录**整体不存在**（`Path("tests/domain").exists()` → `False`）⇒ 你不是在改既有测试树，而是在开新目录。
2. design §11.6 的 **37** 个具名用例（＋ §11.1 的 `test_layering`）与仓内既有 **594** 个 distinct `test_*` 函数做 AST 精确同名对撞 ⇒ **命中 0 处**。
3. 7 个目标文件名（`test_states.py` / `test_clause_gate.py` / `test_digest.py` / `test_bindings.py` / `test_checks.py` / `test_diff.py` / `test_layering.py`）在 `tests/**` 下的**同名文件命中 0 处**。

因此：

- 你落地后，**既有 750 条用例必须仍然全绿**；全量 pytest 应从 750 增至 **750 + N**（N = 你新增的 collected 数，**必须实测报数**，禁预估）。
- ⚠ 唯一允许的既有面变化：`mypy` 的 `in N source files` 由 **113 → 122**（你的 9 个 `.py` 全在 `tests/` 下，而 `pyproject.toml` 的 `files = ["src","tests","scripts"]` ⇒ 全部入 mypy 域）；`ruff` 的 `N files already formatted` 由 **328 → 337**。这两个数是编排器的对账面，你只需**报实测值**，禁改配置去凑。
- ⚠ 若出现任何**既有**测试判红（尤其 `tests/unit/test_counts_freshness.py`、`tests/unit/test_layering_edges.py`、`tests/unit/test_state_ledger.py`、`tests/unit/test_task_cards*.py`），**立即停手报 U**，禁修改既有测试、禁改台账 counts。

---

## 3. 逐字口径回源（PRE-29：禁采信二手复述，一律回源到下列**行号**自读原文）

### 3.1 被测面（领域层）

| 主题 | 回源位置 |
|---|---|
| `RuleContext` 五字段与语义（`sibling_confirmed` 是**只读投影序列**，不是 bool） | `src/campaignlab/domain/activity/checks.py:154-167` |
| `BoundaryCaseDraft`（字段实测 `id/label/template/input_payload/verification`） | `checks.py:171-187` |
| `CheckResult`（`issues` / `boundary_cases`） | `checks.py:189-195` |
| `Check`（`id/category/templates/spec_ref/clause_keys/run`） | `checks.py:197-206` |
| `CheckId` / `CheckCategory`（**8** 项 Literal） | `checks.py:57-66` |
| `CHECK_ISSUE_CODES`（**23**） | `checks.py:68-94` |
| `REASON_CODE_GLOSSARY` | `checks.py:96-113` |
| 模板常量（`_TEMPLATE_IDS` / `_COUPON` / `_CALLBACK` / `_CONST_BY_TEMPLATE`） | `checks.py:115-146` |
| 长度上限（`_MESSAGE_MAX_LENGTH` / `_LABEL_MAX_LENGTH` / `_VERIFICATION_MAX_LENGTH`） | `checks.py:148-152` |
| `CHECK_IDS`（9）/ `CHECKS`（9，C1..C9 注册序） | `checks.py:985-1071` |
| `run_checks` / `check_state_of` / `boundary_cases_for` | `checks.py:1078-1128` |
| 九项检查实现（构造「必触发输入」必须逐个读它） | `_check_window:369` · `_check_threshold:456` · `_check_budget:518` · `_check_stacking:609` · `_check_refund:665` · `_check_template:767` · `_check_new_customer:793` · `_check_callback_sequence:858` · `_check_competition:938` |
| `REQUIRED_CLAUSE_KEYS`（**dict 2 键**）/ `ALL_CLAUSE_KEYS`（**9**）/ `CLAUSE_ISSUE_CODES`（9） | `clauses.py:46-78` |
| `evaluate_clause_gate`（**全 kw-only**：`template` / `terms` / `registered_evidence_ids`） | `clauses.py:113-229` |
| `note_satisfies_warnings` · `confirm_digest_matches` | `clauses.py:231-249` · `clauses.py:251-261` |
| `digest_projection`（三键信封，terms 按 `key` 升序）· `rule_digest` · `RULE_DIGEST_LENGTH=64` | `digests.py:31-79` |
| `DIFF_PATH_LABEL` / `DIFF_PATH_SOURCE_VERSION` / `DIFF_PATH_CONTENT_PREFIX` / `DIFF_PATH_TERMS_PREFIX` · `FIELD_CHANGE_MAX_LENGTH=1000` · `render_scalar` · `field_changes` | `diff.py:45-53` · `diff.py:69-92` · `diff.py:116-224` |
| `BindingDraft` · `BINDING_SORT_KEY` · `intervals_intersect`（起含止排） · `validate_bindings` · `BINDING_ISSUE_CODES`（4） | `bindings.py:48-56` · `57-69` · `78-92` · `94-196` |
| `ACTIVITY_STATES` / `RULE_STATES` / 两个终态集 / `ACTIVITY_TRANSITIONS`（**3**）/ `RULE_TRANSITIONS`（**4**）/ `assert_activity_transition_allowed` / `assert_rule_transition_allowed` / `ACTIVITY_ISSUE_CODES` | `states.py:65-99` · `139-175` · `176-227` · `249-281` · `283-312` |

### 3.2 契约面与生产调用先例（只读、只用于取值口径，**禁改**）

| 主题 | 回源位置 |
|---|---|
| `CaseInput`＝`Annotated[CouponCaseInput \| CallbackCaseInput, Field(discriminator="template")]`（**Annotated 别名，无 `model_validate`**） | `src/campaignlab/api/common.py:664`（两个成员类：`620-645` / `646-662`） |
| `BoundaryCase`（契约 DTO，`input: CaseInput` 在 `:680`） | `api/common.py:667-690` |
| `canonical_json`（**摘要规范化的唯一来源**） | `api/common.py:841-873` |
| 生产侧构造 `RuleContext` ＋ 注入 `sibling_confirmed` / `registered_evidence_ids` | `application/activity_service.py:1196-1230` |
| design §5.2 的 **500 守护**（`record.digest != computed` → `InternalFailure`）＝`test_rule_digest_matches_stored_column` 的同源面 | `activity_service.py:1229-1236` |
| 生产侧 `rule_digest(..., canonicalize=canonical_json)` 与 `evaluate_clause_gate` / `run_checks` 的调用序 | `activity_service.py:1895-1915` |
| `field_changes(..., canonicalize=canonical_json)` 的调用先例 | `activity_service.py:1974-1978` |

### 3.3 规格与体例

| 主题 | 回源位置 |
|---|---|
| 你的交付清单原文（§11.6） | `orchestrator/handoff/M2-01-design.md:1093-1134` |
| `test_layering.py` 的要求原文（§11.1 末条） | `M2-01-design.md:1011-1014` |
| 反例（`boundary_cases`）的 18 条生成配方（§5.4） | `M2-01-design.md:549-600`（表格 18 行数据 ＋ 表头/分隔行） |
| 判定结果结构四段的冻结口径（§5.2，含 `maxItems` 30 / 1000 与去重键 `(code, location)`） | `M2-01-design.md:487-509` |
| 九项检查的归属表（§5.3，谁报哪个 `code`） | `M2-01-design.md:511-548` |
| AST 分层守护 ＋ `tmp_path` 阳性对照的**体例先例**（照抄结构，禁自创） | `tests/unit/test_layering_edges.py`（294 行；白名单是模块级常量、扫描用 `ast` 禁正则、四条 `tmp_path` 探针） |
| fixtures：四种规则内容 | `spec/CampaignLab-SDD-v1.0/fixtures/cases/rules.json`（1235 B，键＝`CP-V1` / `CP-V2` / `CB-V1` / `CB-V2`） |
| fixtures：六条 `terms` 的**权威取值** | `spec/CampaignLab-SDD-v1.0/fixtures/api-examples.json` → `examples[3]`（**0-based 下标 3**，`operationId=createRule`、`status=201`、`request.terms` 恰 **6** 条，全部 `status="CONFIRMED"`、`evidence_id="EV-CLAUSE-001"`；键序＝new_customer / payment / time_window / stacking / budget_and_quota / refund）⇒ 见 **A266** |
| 任务卡的两条 `-k` gate 字面量 | `orchestrator/tasks/M2-01.md:17`（`-k immutable`）与 `:19`（`-k clause_gate`） |
---

## 4. 冻结面实测读数（编排器于 predispatch 时点＝sha `0765099` 实测；你上工**必须自行复测**并贴命令原文）

### 4.1 仓面

| 项 | 实测值 | 复测命令（受限路径，PRE-19） |
|---|---|---|
| HEAD | `0765099` | `git rev-parse HEAD` |
| 工作树 | 干净（0 条） | `git status --porcelain \| wc -l` |
| `tests/domain` | **不存在** | `uv run --no-sync python -c "import pathlib;print(pathlib.Path('tests/domain').exists())"` |
| tests 子包形态 | `tests/__init__.py` 153 B · `tests/api/__init__.py` 117 B · `tests/unit/__init__.py` 52 B · `tests/integration/__init__.py` 52 B · `tests/api/activities/__init__.py` 89 B · `tests/integration/jobs/__init__.py` 108 B —— **全部是单行 docstring 形态，无一为零字节** | `wc -c tests/*/__init__.py tests/__init__.py` |
| pytest 基线 | **750 tests collected**（`--collect-only -q`，rc=0，0.79s） | `uv run --no-sync python -m pytest --collect-only -q 2>&1 \| tail -2` |
| counts 基线 | 328 / 113 / 750（115 py + 213 md） | 见台账 `resume.self_check_gates_rc0.counts`（**禁改**） |
| mypy 域口径 | `files = ["src","tests","scripts"]`，`strict = true`，`exclude = ^(spec\|prototype\|web\|[.]venv)/` ⇒ 你的 9 件**全部入域** | `sed -n '/\[tool.mypy\]/,/^\[/p' pyproject.toml` |
| ruff 口径 | `line-length = 100`、`target-version = "py314"`、`select = ["E","F","I","UP","B","SIM","RUF"]`、`ignore = ["RUF001","RUF002","RUF003"]`（中文标点不判 confusable）⇒ **无 pydocstyle（D）规则**，但行宽 100 与 import 排序（I）会判红 | `sed -n '/\[tool.ruff\]/,\$p' pyproject.toml` |

### 4.2 被测符号面（**这些数字就是你的断言分母；禁写死别的值**）

| 符号 | 实测 | 备注 |
|---|---|---|
| `domain.activity.__all__` | **55** 项 | 你**不需要**断言它（那是 S2a 的守护面）；列出只为让你知道可用面 |
| `CheckCategory` | **8**：`DATE` `THRESHOLD` `BUDGET` `STACKING` `REFUND` `TEMPLATE` `SEQUENCE` `COMPETITION` | design §11.6 写「five_ac004_categories」⇒ 见 **A264** |
| `CHECKS` / `CHECK_IDS` | **9** / **9**（`C1`..`C9`，注册序即 `CHECKS` 顺序） | `len(CHECKS) > 0` 的分母断言必须写（防 glob 扫空全绿） |
| `CHECK_ISSUE_CODES` | **23** | 逐字清单见 `checks.py:68-94` |
| `CLAUSE_ISSUE_CODES` | **9** | `clauses.py:66-78` |
| `BINDING_ISSUE_CODES` | **4**：`BINDING_EMPTY_INTERVAL` `BINDING_OVERLAP` `BINDING_DUPLICATE_KEY` `BINDING_EVIDENCE_UNREGISTERED` | |
| `ACTIVITY_ISSUE_CODES` | **1**：`ACTIVITY_ARCHIVED` | |
| `ALL_CLAUSE_KEYS` | **9**：`new_customer` `payment` `time_window` `stacking` `budget_and_quota` `refund` `same_day_scope` `priority` `daily_cap` | 与卡片 `public_frozen` 行（`M2-01.md:27`）的键集合**逐字对撞** |
| `REQUIRED_CLAUSE_KEYS` | **dict 2 键**：`coupon_threshold` → 6 键（new_customer/payment/time_window/stacking/budget_and_quota/refund）；`callback_priority` → 3 键（same_day_scope/priority/daily_cap） | ⚠ **禁**把它当成「9 键清单」——那是 `ALL_CLAUSE_KEYS`（design §11.6 的 `required_keys_are_the_spec_nine` 必须与 `ALL_CLAUSE_KEYS` 对撞，见 **A263**②） |
| `ACTIVITY_STATES` / `RULE_STATES` | `('OPEN','ARCHIVED')` / `('DRAFT','CONFIRMED')` | 终态各 1：`ARCHIVED` / `CONFIRMED` |
| `ACTIVITY_TRANSITIONS` | **3** 行：`A1` sources=() → `OPEN`；`A2` `OPEN`→`ARCHIVED`；`A3` `OPEN`→`OPEN` | design §11.6 的 `a1_a2_a3` 与实测**相符** |
| `RULE_TRANSITIONS` | **4** 行：`R1` ()→`DRAFT`；`R2` `DRAFT`→`DRAFT`；`R3` `DRAFT`→`CONFIRMED`；`R4` `CONFIRMED`→`DRAFT`（`creates_new_row=True`） | design §11.6 的 `r1_r4` 指 **R1..R4 共 4 行**（非「R1 与 R4 两行」）⇒ 见 **A263**③ |
| `RULE_DIGEST_LENGTH` / `FIELD_CHANGE_MAX_LENGTH` | **64** / **1000** | |
| `DIFF_PATH_*` | `/label` · `/source_rule_version` · `/content/` · `/terms/` | 四类 path 前缀，`field_changes` 的排序即按此 |
| `boundary_cases_for` 签名 | **`(context: RuleContext) -> tuple[BoundaryCaseDraft, ...]`** | ⚠ **按 context 取，不是按 template 取**：用 `template=` 关键字调用实测 `TypeError` |

### 4.3 反例（`boundary_cases`）与检查项的**实测分母**（这是本棒最容易写错的地方，逐个实测过）

构造方式（**唯一可行形态**，见 §4.4 的陷阱）：`RuleContext(rule_id=…, template=content["template"], content=<fixture 原样 dict>, terms=(), sibling_confirmed=())`

| fixture | `template` | `boundary_cases_for` 条数 | 实测 `id` 集 | `run_checks().issues` | 实测 code 集 | `check_state_of` |
|---|---|---|---|---|---|---|
| `CP-V1` | `coupon_threshold` | **15** | `bc-C1-1` `bc-C1-2` `bc-C1-3` `bc-C2-1` `bc-C2-2` `bc-C3-1` `bc-C3-2` `bc-C3-3` `bc-C4-1` `bc-C4-2` `bc-C5-1` `bc-C5-2` `bc-C7-1` `bc-C7-2` `bc-C7-3` | **6** | 六个 `*_CLAUSE_UNCONFIRMED`（NEW_CUSTOMER / PAYMENT / TIME_WINDOW / STACKING / BUDGET / REFUND） | `NEEDS_CONFIRMATION` |
| `CP-V2` | `coupon_threshold` | **15** | 同 `CP-V1` 的 15 个 id | **7** | 上述 6 ＋ `REFUND_RECOMPUTE` | `NEEDS_CONFIRMATION` |
| `CB-V1` | `callback_priority` | **2** | `bc-C8-1` `bc-C8-2` | **3** | `SAME_DAY_CLAUSE_UNCONFIRMED` `PRIORITY_CLAUSE_UNCONFIRMED` `DAILY_CAP_CLAUSE_UNCONFIRMED` | `NEEDS_CONFIRMATION` |
| `CB-V2` | `callback_priority` | **3** | `bc-C8-1` `bc-C8-2` `bc-C8-3` | **4** | 上述 3 ＋ `PRIORITY_APPOINTMENT_FIRST` | `NEEDS_CONFIRMATION` |

- `evaluate_clause_gate(template=…, terms=(), registered_evidence_ids=())` 实测：`CP-V1` → **6** 条 `CLAUSE_MISSING`（`location` 依次 `/terms/new_customer` … `/terms/refund`，severity 全 `ERROR`）；`CB-V1` → **3** 条（`/terms/same_day_scope` `/terms/priority` `/terms/daily_cap`）。
- design §5.2 行 508 的「满额赠券最多 **15** 条、远程回拨最多 **3** 条」与上表**逐字相符**（15 与 3 分别是两个模板的上界；`CB-V1` 实测 2 是因为 §5.4 第 18 行的配方在 `CB-V1` 的取值下不生成 ⇒ **分母按 fixture 实测定，禁写死 3**）。
- 契约上限（`maxItems`）：`boundary_cases` **30**、`issues` **1000**（design §5.2 行 503-508）⇒ `test_boundary_case_count_never_exceeds_contract_max` 的分母是 **30**，实测最大 15 ⇒ 天然不触顶。
- ⚠ design §5.4 的表格共 **18** 行数据（跨两个模板），而 §11.6 的函数名写 `ten` ⇒ **A263**①。

### 4.4 构造陷阱（**编排器实测踩过，逐字告你**）

1. `RuleContext.sibling_confirmed` 的类型是 `Sequence[Mapping[str, Any]]`（同活动下其它 CONFIRMED 版本的只读投影，供 C9 判重叠）。实测传 `False` ⇒ **`TypeError: 'bool' object is not iterable`**；传 `()` / `frozenset()` / `{}` 均可（`len(boundary_cases_for(ctx))` 都是 15）。**用 `()`**。
2. `boundary_cases_for` 只接受**一个位置参数 `context`**；`boundary_cases_for(template="coupon_threshold")` 实测 `TypeError`。
3. `evaluate_clause_gate` / `validate_bindings` / `field_changes` / `rule_digest` 的 `canonicalize` 等参数是 **kw-only**（签名里有 `*`）⇒ 必须写关键字。
4. `rule_digest(content, terms, source_rule_version, *, canonicalize)` 的 `canonicalize` **必须注入 `campaignlab.api.common.canonical_json`**：`digests.py:73` 的 docstring 原文写明「自己 `json.dumps` 会让『同键同体』在不同 lane 算出不同摘要」⇒ 见 **A265**。
5. 领域层**不含连接、不含时钟**（`checks.py:157`）⇒ 你的用例里禁出现 DB / HTTP / `time.time()` / `datetime.now()`；`test_boundary_cases_are_deterministic_without_clock` 就是钉这一条（同一 context 两次调用逐字节相同）。

---

## 5. 本棒携带的裁定（append-only；**不得推翻**，有异议走 §8 上报）

### A262 · `tests/domain/__init__.py` 的写权授权 ＋ 两个 `__init__.py` 的**形态**
- **缺口**：卡片 `scope_allow`（`M2-01.md:25`）只给 `tests/domain/activity/**`，而 `tests/domain/__init__.py` 在该字面量**之外**（design §11.9 行 1201 已点名，先例＝M1-03 的 N1）。
- **裁定**：**授权** lane S5 新建 `tests/domain/__init__.py`（**仅此一件**越字面量文件，且必须是**新建**、`numstat` 形如 `1/0` 或 `2/0`，禁触碰任何既有文件）。理由：不建它则 `tests/domain/activity/**` 无法作为包被 mypy 以 `tests.domain.activity.*` 解析（D-035 的口径：`tests/**` **各级**都要有 `__init__.py`），gate 会因模块名歧义而不可复现。
- **形态裁定**：design §11.6 行 1094 写「**空文件**」，但仓内 6 个既有 tests 包标记**无一为空**（52–153 B，全部是单行 docstring，且都注明 D-035 口径）⇒ 采 **specific 覆盖 general**（A232 同族推理）：两个 `__init__.py` 一律写成**单行 docstring** 形态，照 `tests/api/activities/__init__.py`（89 B）的体例，内容点明「M2-01/S5 领域层测试子包标记（D-035：钉牢 mypy 模块名）」。零字节空文件**不判错**，但会成为全仓唯一例外，故不采。

### A263 · design §11.6 的三处**数目/命名失真**（PRE-26/30：一律以实测定分母）
① `test_boundary_cases_cover_the_ten_spec_counterexamples`：函数名说 **ten**、正文说「§5.4 的 **18** 条」，而实测**单个 context** 最多 15 条（`CP-V1`/`CP-V2`）、`CB-V1` 2 条、`CB-V2` 3 条 ⇒ **三者都不是 10**。
  **裁定**：函数名改为 **`test_boundary_cases_cover_the_spec_counterexamples_per_template`**（保留 `boundary_case` 字面量以满足 V6 的 `-k`），断言面＝①`CP-V1` 与 `CP-V2` 各 **15** 条且 id 集逐字等于 §4.3 的 15 个；②`CB-V1` **2** 条、`CB-V2` **3** 条且 id 集逐字相等；③全部 id 匹配契约正则 `bc-<CheckId>-<序号>`；④全部 id 在一个 template 内**唯一**、跨 template 不要求唯一（实测两个模板的 id 集互不相交）。**禁**写死 10 或 18。
② `test_clause_gate_required_keys_are_the_spec_nine`：**裁定**＝与 `ALL_CLAUSE_KEYS`（实测 **9** 项）逐字对撞（集合相等 ＋ 顺序相等），并**另加一条**断言 `REQUIRED_CLAUSE_KEYS` 是 **dict 2 键**、其两个值元组拼接后**恰等于** `ALL_CLAUSE_KEYS` 的 9 项（6+3，无重复、无遗漏）——这样「9」这个分母有两个独立来源互证，禁只写其一。
③ `test_rule_state_machine_r1_r4_are_exactly_the_registered_rows`：**裁定**＝`r1_r4` 读作「**R1 到 R4 共 4 行**」（实测 `len(RULE_TRANSITIONS) == 4`，id 依次 `R1`/`R2`/`R3`/`R4`），**不是**「R1 与 R4 两行」。函数名**不改**（`r1_r4` 在英文里可读作区间，且卡片 gate 只认 `-k immutable` / `-k clause_gate` 两个字面量，不含本名）。同理 `a1_a2_a3` ＝ 3 行（实测相符）。

### A264 · `five_ac004_categories` vs `CheckCategory` 实测 8 项
- **事实**：`CheckCategory` 实测 **8** 项；AC-004 的原文口径是「门槛、预算、叠加、日期和退款口径**分别检查**」＝ **5** 个口径。
- **裁定**：函数名 **`test_check_framework_five_ac004_categories_all_have_teeth` 保留**（它指的是 AC-004 点名的五个口径，不是 `CheckCategory` 的全集），但**必须同批**满足两条：
  ① 五个口径逐个构造**必触发输入**并断言真的产出 `ERROR`/`WARNING`（映射：门槛→`THRESHOLD`、预算→`BUDGET`、叠加→`STACKING`、日期→`DATE`、退款→`REFUND`）；
  ② **另设分母断言**：`set(typing.get_args(CheckCategory))` 恰等于实测的 **8** 项集合，且 `len(CHECKS) == 9 == len(CHECK_IDS)`、`len(set(CHECK_IDS)) == 9`、`{c.category for c in CHECKS} <= set(get_args(CheckCategory))`。
  这样「5」与「8」两个数各有其位、互不覆盖；**禁**把 5 写成 `CheckCategory` 的分母（那就是 D-052 那类失真）。
- 未被 AC-004 点名的三类（`TEMPLATE` / `SEQUENCE` / `COMPETITION`）**不要求**在本棒构造必触发输入（它们由 C6/C8/C9 覆盖，§5.3 的归属表已冻结）；但你**可以**加，加了就必须绿。

### A265 · `CaseInput.model_validate` 不可用 ⇒ `TypeAdapter`；`canonicalize` 必须注入 `canonical_json`
- **事实**（承 D-052 §9 / R18-11 的更正）：`CaseInput` 在 `api/common.py:664` 是 `Annotated[CouponCaseInput | CallbackCaseInput, Field(discriminator="template")]`，实测 `type(CaseInput).__name__ == '_AnnotatedAlias'`、`hasattr(CaseInput, "model_validate") is False` ⇒ design §11.6 行 1122 的「每条 `input_payload` 过 `CaseInput.model_validate`」**字面不可执行**。
- **裁定**：`test_boundary_case_inputs_validate_against_contract` 一律用
  `pydantic.TypeAdapter(CaseInput).validate_python(draft.input_payload)`（`input_payload` 实测**就是**领域侧的 `CaseInput` **字典**，`checks.py:174` 原文；判别键是 `template`，已由 `BoundaryCaseDraft.template` 单独带出 ⇒ 若 `input_payload` 内不含 `template` 键，你必须在**测试内**补 `{"template": draft.template, **draft.input_payload}` 后再校验，并在回执里贴出你实测的 `input_payload` 键集合作为依据）。
- **同批裁定**：`rule_digest` / `field_changes` 的 `canonicalize` **必须**传 `campaignlab.api.common.canonical_json`（`digests.py:73` 的 docstring 强制；生产侧 `activity_service.py:1393/1563/1748/1904/1977` 五处全是它）。**测试文件 import `campaignlab.api.common` 不构成跨层违规**：你的 `test_layering.py` 只扫 `src/campaignlab/domain/activity/**`（§11.1 行 1011-1012 原文），不扫 `tests/**`；仓内先例＝`tests/unit/test_domain_errors.py` 也 import `api.common`。

### A266 · design §11.6「`fixtures/api-examples.json` **第 3 条**示例的六个 `terms`」的实指
- **实测**：`examples` 是长度 **22** 的数组；`examples[2]` 的 `operationId` 是 `updateActivity`、**没有** `terms`；`examples[3]` 的 `operationId` 是 `createRule`、`request.terms` 恰 **6** 条 ⇒ 「第 3 条」是 **0-based 下标 3**。
- **裁定**：一律取 **`examples[3].request.terms`**（六条，键序 `new_customer`/`payment`/`time_window`/`stacking`/`budget_and_quota`/`refund`，全部 `status="CONFIRMED"`、`evidence_id="EV-CLAUSE-001"`）。**禁**按下标 2 取（那条没有 terms，会让你写出恒空的假绿矩阵）。取法必须**从文件读**（`json.loads(Path(...).read_text())`），禁把六条 terms 硬编码进测试文件——硬编码就等于造了第二份真相源（N5 口径）。
- `registered_evidence_ids` 的取值：fixture 里没有证据登记表（实测 `fixtures/` 下无 evidence 清单文件；生产侧由 `ActivityBindingRepository.evidence_exists` 批量取，`activity_service.py:701`）⇒ 领域层用例**自行给定** `{"EV-CLAUSE-001"}` 即可，并在 docstring 里注明「证据登记面属仓储层，本层只验『给了/没给』两种分支」。

### A267 · `test_clause_gate_six_by_three_matrix` 的语义
- **实测**：`REQUIRED_CLAUSE_KEYS` ＝ `coupon_threshold` **6** 键 ＋ `callback_priority` **3** 键；`evaluate_clause_gate(terms=())` 对前者产 6 条 `CLAUSE_MISSING`、对后者产 3 条。
- **裁定**：「六项 / 三项确认矩阵」（卡片 `M2-01.md:46` 原文）读作**两个模板各自的必填键矩阵**（6 ＋ 3 ＝ **9** 个参数化用例），**不是** 6×3＝18 的笛卡尔积。每个参数化用例必须验两面：① 该键**缺席** ⇒ 恰有 1 条 `CLAUSE_MISSING`、`location == f"/terms/{key}"`、`severity == "ERROR"`；② 该键以 `status="CONFIRMED"` ＋ 已登记 `evidence_id` 给出（其余键同样给全）⇒ `evaluate_clause_gate` 返回**空元组**。矩阵的键集合必须从 `REQUIRED_CLAUSE_KEYS` **实取**（禁写死 6 或 3 这两个数字）。

### A268 · `test_rule_digest_matches_stored_column` 在**领域层**的可执行形态
- **事实**：领域层拿不到「stored column」（那在 `rule_versions.digest`，属 infra/仓储面；design §5.2 的 500 守护落在 `activity_service.py:1229-1236` 的 `_verify_digest`）。
- **裁定**：本用例在领域层钉**同一公式**（＝「同源」的可执行含义），必须断言三条：
  ① `rule_digest(content, terms, src, canonicalize=canonical_json) == hashlib.sha256(canonical_json(digest_projection(content, terms, src)).encode("utf-8")).hexdigest()`（测试内**独立**算一遍，禁调用 `rule_digest` 自己）；
  ② 结果匹配 `^[0-9a-f]{64}$` 且 `len(...) == RULE_DIGEST_LENGTH`（64）；
  ③ `digest_projection` 的信封**恰三键**（`content` / `source_rule_version` / `terms`），且 `terms` 已按 `key` 升序（打乱输入顺序后投影逐字节相同）。
  **禁**为了「stored」而起 DB / 起 TestClient（那是 S6 与 M0-02 的面）；若你认为必须端到端才能钉住，按 §8 报 U，禁自行扩权。

### 承前批（与 S5 相关，逐字携带）
- **A256**：`_rule_check_response` 只透传、不设 500 `INTERNAL_ERROR` 分支；校验点在 service 构造期 ⇒ 你在领域层验 `input_payload` 的合法性正是**更强位置**（A265 的 TypeAdapter）。
- **A257**：rules 的 **7-op 契约对撞归 S6** ⇒ **S5 禁写任何 HTTP/路由/状态码断言**。
- **A261**：§0 一律以 **sha** 为锚（本文件已照办：`0765099`）。
- **D-052 §9 / R18-11**：`BoundaryCaseDraft` **确实存在**于 `domain.activity`（`checks.py:171`，字段含 `input_payload`）；D-052 的 ①② 两条断言已被更正，**禁**再按「仓内无此符号」行事。
- **PRE-33**：要对「某符号是否存在」下结论，必须覆盖 ①目标层 `__all__`、②全仓 `grep -rn`（限定路径）、③同名近形符号三处。
- **PRE-34**：变异必须先证明「形态成立且不引入收集期错误」再看读数；**rc=4（收集期）与 rc=1（断言红）必须区分**，前者不能当「有牙」的证据。
---

## 6. 交付面 · 用例清单 · 门

### 6.1 七个测试文件的用例清单（design §11.6 逐字 ＋ 本文件 §5 的订正；**函数名一律逐字**）

**A. `test_states.py`**（函数名必须含 `state_machine` 以满足 V7、含 `immutable` 以满足卡片 gate `-k immutable`）
1. `test_activity_state_machine_a1_a2_a3_are_exactly_the_registered_rows` —— 实测 3 行；断言 id 序列 `("A1","A2","A3")`、每行 `sources`/`target` 与 §4.2 逐字相符，且 `ActivityTransitionId` 的 `get_args` 恰为这 3 个。
2. `test_rule_state_machine_r1_r4_are_exactly_the_registered_rows` —— 实测 **4** 行（A263③）；断言 id 序列 `("R1","R2","R3","R4")`、`R4.creates_new_row is True` 而其余为 `False`、`RuleTransitionId` 的 `get_args` 恰为这 4 个。
3. `test_archived_activity_is_immutable_and_rejects_every_mutation` —— `is_activity_terminal("ARCHIVED") is True`；`assert_activity_transition_allowed("ARCHIVED", <每个 ACTIVITY_STATES 成员>, trigger=…)` **全部**抛领域异常（异常类型与 `code` 回源 `states.py:249-281` 与 `ACTIVITY_ISSUE_CODES`，禁写死消息文本）。
4. `test_confirmed_rule_version_is_immutable_on_update` —— `assert_rule_transition_allowed("CONFIRMED","CONFIRMED",trigger="updateRule")` 必须抛；对照 `("DRAFT","DRAFT")` 必须放行（R2）。
5. `test_confirmed_rule_version_is_immutable_on_reconfirm` —— `("CONFIRMED","CONFIRMED")` 在 `trigger="confirmRule"` 下必须抛；对照 `("DRAFT","CONFIRMED")` 放行（R3）。
6. `test_successor_draft_does_not_touch_the_confirmed_parent` —— `("CONFIRMED","DRAFT")` 放行（R4）且 `creates_new_row is True`（语义：产生**新行**，父行不动）。禁在本棒起 DB 验「父行未变」（那是 S6/仓储面）；本棒只钉**迁移表的语义位**。
7. `test_transition_tables_have_teeth_positive_control` —— **正向对照**：在 `tmp_path` 里造「多一行／少一行」的探针迁移表副本，断言你的扫描/对撞逻辑能抓到；**禁落工作树、禁改 `src`**（用 `monkeypatch` 或把表当参数传给你自己的辅助函数）。

**B. `test_clause_gate.py`**（函数名必须含 `clause_gate` 以满足卡片 gate `-k clause_gate`）
8. `test_clause_gate_blocks_when_a_required_key_is_missing`
9. `test_clause_gate_blocks_when_a_required_key_is_open`（`status` 非 `CONFIRMED` ⇒ `CLAUSE_UNCONFIRMED`）
10. `test_clause_gate_blocks_on_duplicate_key`（⇒ `CLAUSE_DUPLICATE`）
11. `test_clause_gate_blocks_on_missing_or_unregistered_evidence`（⇒ `CLAUSE_EVIDENCE_MISSING` / `CLAUSE_EVIDENCE_UNREGISTERED`）
12. `test_clause_gate_blocks_on_empty_decision`（⇒ `CLAUSE_DECISION_EMPTY`）
13. `test_clause_gate_six_by_three_matrix` —— 按 **A267**：`pytest.mark.parametrize` 覆盖 `REQUIRED_CLAUSE_KEYS` **实取**的 6+3=9 个键，每键验「缺席⇒恰 1 条 CLAUSE_MISSING 且 location 逐字」与「给全⇒空元组」两面；terms 取值从 `examples[3]` **读文件**（A266）。
14. `test_clause_gate_warning_requires_note` —— `note_satisfies_warnings`：无 note ⇒ 返回 issue（`CONFIRMATION_NOTE_REQUIRED`）；有满足条件的 note ⇒ 返回 `None`（回源 `clauses.py:231-249` 与 `_NOTE_REQUIRED_TEXT`）。
15. `test_clause_gate_digest_mismatch_is_reported` —— `confirm_digest_matches(provided=…, current=…)`：相等 `True`、不等 `False`；且**只比较不回显**（返回值是 `bool`，禁断言任何摘要文本被返回）。
16. `test_clause_gate_required_keys_are_the_spec_nine` —— 按 **A263②**：与 `ALL_CLAUSE_KEYS` 双向对撞 ＋ 与卡片 `public_frozen` 行（`M2-01.md:27`）的 9 键**逐字**对撞 ＋ `REQUIRED_CLAUSE_KEYS` 两值元组拼接后恰等于该 9 键。
17. `test_clause_gate_rejects_unsupported_schema_version`（**编排器新增要求**，非 §11.6 原文）—— `CLAUSE_ISSUE_CODES` 里有 `SCHEMA_VERSION_UNSUPPORTED`，而 §11.6 的清单**漏了它**；卡片 gate 的口径明写「确认前按 `schema_version` 1 校验」（`M2-01.md:19`）⇒ 必须补一条。断言：`schema_version != 1` 时报该 code；`== 1` 时不报。**若你实测 `evaluate_clause_gate` 根本不接 `schema_version`（签名只有 template/terms/registered_evidence_ids）**，则改为在 `terms` 或 `content` 的实测入口上验；若确认该 code 在领域层**不可达**，按 §8 报 **U**（禁删 code、禁造假绿）。

**C. `test_digest.py`**
18. `test_rule_digest_projection_is_content_sorted_terms_and_source_version`
19. `test_rule_digest_ignores_label_and_confirmation`（投影信封**不含** `label` 与确认面 ⇒ 改它们摘要不变）
20. `test_rule_digest_is_stable_across_key_order`（`content` 键序与 `terms` 顺序打乱后摘要逐字节相同）
21. `test_rule_digest_matches_stored_column` —— 按 **A268** 的三条断言（`canonicalize=canonical_json`，禁自造 dumps）

**D. `test_bindings.py`**
22. `test_binding_interval_is_start_inclusive_end_exclusive`（`intervals_intersect` 的起含止排：`a.from < b.until and b.from < a.until`，回源 `bindings.py:81-92` 的 A198 口径）
23. `test_binding_empty_interval_is_rejected`（⇒ `BINDING_EMPTY_INTERVAL`）
24. `test_binding_overlap_is_rejected`（⇒ `BINDING_OVERLAP`；**部分重叠也必须报**）
25. `test_binding_duplicate_key_is_rejected`（⇒ `BINDING_DUPLICATE_KEY`）
26. `test_binding_evidence_must_be_registered`（⇒ `BINDING_EVIDENCE_UNREGISTERED`）
27. `test_binding_sort_key_is_frozen`（`BINDING_SORT_KEY` 实测是 `(date, str, str)` 三元组；断言 `sorted(drafts, key=BINDING_SORT_KEY)` 的结果序**逐字**稳定，且键的三个分量分别来自 `valid_from` / 另两个字段——**回源 `bindings.py:71-78` 的 `_sort_key` 实取**，禁猜字段）

**E. `test_checks.py`**（函数名必须含 `check_framework` 或 `boundary_case`）
28. `test_check_framework_registers_every_check_id_exactly_once` —— 含**分母断言** `len(CHECKS) == 9 > 0`、`len(set(CHECK_IDS)) == 9`、`CHECK_IDS == tuple(c.id for c in CHECKS)`（注册序一致）、`{c.category for c in CHECKS} <= set(get_args(CheckCategory))`。
29. `test_check_framework_five_ac004_categories_all_have_teeth` —— 按 **A264**：五个口径各造一个**必触发输入**断言真产出 issue ＋ 另设 `CheckCategory` 恰 8 项的分母断言。
30. `test_check_state_needs_confirmation_on_unconfirmed_clause` —— `check_state_of`：含 `severity=="ERROR"` ⇒ `NEEDS_CONFIRMATION`；只有 `WARNING`/`INFO` ⇒ `READY`；空 ⇒ `READY`（回源 §5.2 行 493-496）。
31. `test_boundary_cases_cover_the_spec_counterexamples_per_template` —— 按 **A263①**（**改名**，禁沿用 `ten`）。
32. `test_boundary_case_inputs_validate_against_contract` —— 按 **A265**（`TypeAdapter(CaseInput)`），对**四个 fixture 的全部反例**逐条校验（15+15+2+3 = 35 次），一条不过即判红。
33. `test_boundary_cases_are_deterministic_without_clock` —— 同一 `RuleContext` 两次调用，`[(b.id, b.label, b.template, canonical_json(b.input_payload), b.verification) for b in …]` 两次**逐字节相同**。
34. `test_boundary_case_count_never_exceeds_contract_max` —— 分母 **30**（契约 `maxItems`，回源 design §5.2 行 507）；实测四个 fixture 的最大值是 15 ⇒ 断言 `<= 30` 且**同时**断言实测值 `== 15/15/2/3`（禁只写上限，那样改坏了也不红）。

**F. `test_diff.py`**
35. `test_rule_diff_paths_are_frozen_and_sorted` —— 四类 path 常量逐字（`/label` `/source_rule_version` `/content/` `/terms/`）；`field_changes` 输出的排序＝`/label` → `/content/*` 字段名字典序 → `/source_rule_version` → `/terms/*` 键字典序（design §11.1 行 1009 原文）。
36. `test_rule_diff_excludes_non_projection_fields` —— 改动**不在**投影内的字段（如确认面/标签之外的元数据）⇒ `field_changes` 返回空。
37. `test_rule_diff_renders_values_as_strings` —— `render_scalar`：整数十进制、布尔 `true`/`false`、时刻 ISO、`None` 保持 `None`（design §11.1 行 1007 原文；**回源 `diff.py:69-92` 实取**，禁按想象写）。另断言 `before`/`after` 长度 ≤ `FIELD_CHANGE_MAX_LENGTH`（1000，`_capped` 的行为回源 `diff.py:94-99`）。
38. `test_rule_diff_cp_v1_to_cp_v2_is_refund_policy_only` —— 用 fixture 的 `CP-V1` / `CP-V2`；**编排器实测**：两者键集完全相同（13 键），差值只在 `refund_policy`（`CP-V1` 是 `RECOMPUTE_UNUSED`，`CP-V2` 触发 `REFUND_RECOMPUTE` issue）⇒ 断言 `field_changes` 恰 **1** 条且 `path == "/content/refund_policy"`。**你上工必须自行复测这个「只差一处」**（`diff` 两个 fixture 的键值），若实测不止一处，按 §8 报 U（禁改 fixture、禁改断言去凑）。

**G. `test_layering.py`**（design §11.1 行 1011-1014 原文；体例照 `tests/unit/test_layering_edges.py`）
39. `test_domain_activity_has_no_runtime_import_edge_to_api_infra_application` —— AST 扫 `src/campaignlab/domain/activity/*.py`（**7 个文件**，实测清单见 §4.1），断言零运行期 `campaignlab.api` / `campaignlab.infra` / `campaignlab.application` 导入边；**必须自带分母断言**（扫到的 `.py` 文件数 == 7，防 glob 扫空全绿）；`TYPE_CHECKING` 块内的导入按先例**豁免**（回源 `test_layering_edges.py` 的处理方式与 design §14.3 的 A233）。
40. `test_domain_activity_layering_scanner_has_teeth` —— **正向对照**：在 `tmp_path` 里造一个含 `from campaignlab.api.common import canonical_json` 的探针文件，断言你的扫描器**抓得到**（禁落工作树）。

> 用例总数下限：**40**（其中 39/40 两条是 layering）。你**可以**加更多（例如把 §5.3 的九项检查逐个钉住），加了就必须全绿且在回执里逐条列出。参数化用例的 collected 数会大于函数数 ⇒ 回执必须**同时**报「函数数」与「collected 数」。

### 6.2 门（rc 必须全 0；命令原文与输出尾部逐字贴进回执，禁只写「通过」）

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"; cd /home/szf/dev/CampaignLab

# V0 基线自证（不等即停手报 U-BASELINE）
git rev-parse HEAD                                    # 期望 0765099006544b72de505ea18258159443ff7349
git status --porcelain | wc -l                        # 期望 0（上工前）

# V1 你的 9 件 face（行数/字节/sha256[:12]），逐件报
uv run --no-sync python - <<'PY'
import hashlib, pathlib
for p in sorted(pathlib.Path("tests/domain").rglob("*.py")):
    b = p.read_bytes()
    print(p, len(b.decode().splitlines()), len(b), hashlib.sha256(b).hexdigest()[:12])
PY

# V2 用例名对撞（AST 实取，逐名核对 §6.1；禁采信你自己的记忆）
uv run --no-sync python - <<'PY'
import ast, pathlib
for p in sorted(pathlib.Path("tests/domain").rglob("test_*.py")):
    m = ast.parse(p.read_text(encoding="utf-8"))
    print(p.name, [n.name for n in m.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")])
PY

# V3 ruff（格式 + lint）
uv run --no-sync ruff format --check tests/domain ; uv run --no-sync ruff check tests/domain

# V4 mypy strict（全仓；你的 9 件入域 ⇒ 期望 in 122 source files）
uv run --no-sync mypy 2>&1 | tail -3

# V5 卡片 gate 的两条 -k 字面量（M2-01.md:17 与 :19）
uv run --no-sync pytest -q tests/domain/activity -k immutable 2>&1 | tail -3
uv run --no-sync pytest -q tests/domain/activity -k clause_gate 2>&1 | tail -3
uv run --no-sync pytest -q tests/domain/activity -k state_machine 2>&1 | tail -3
uv run --no-sync pytest -q tests/domain/activity -k "check_framework or boundary_case" 2>&1 | tail -3

# V6 硬禁面零改动（输出**必须只有**你的 9 件 ??，其余为空）
git status --porcelain
git diff --numstat            # 期望**空**（本棒不改任何既有文件）

# V7 全量 pytest（期望 750 + N passed / 0 failed；N 与 collected 数都要报）
uv run --no-sync pytest -q 2>&1 | tail -3
uv run --no-sync python -m pytest --collect-only -q 2>&1 | tail -2

# V8 分层守护自身有牙（你的 test_layering.py 必须能抓探针）
uv run --no-sync pytest -q tests/domain/activity/test_layering.py 2>&1 | tail -3
```

---

## 7. 阳性对照（PC；**每条先实证「有牙」再报绿**，PRE-34：区分 rc=4 收集期错误与 rc=1 断言红）

| PC | 变异/探针 | 期望读数 | 复原对撞 |
|---|---|---|---|
| **PC-A** | `test_transition_tables_have_teeth_positive_control`：`tmp_path` 里造「少一行 R3」的迁移表副本喂给你的辅助断言函数 | 你的断言**判红**（rc=1，不是 rc=4） | 探针只在 `tmp_path`，工作树 sha 不变 |
| **PC-B** | `test_domain_activity_layering_scanner_has_teeth`：`tmp_path` 造含 `from campaignlab.api.common import canonical_json` 的探针 `.py` | 扫描器**抓到该边**（断言命中） | 同上 |
| **PC-C** | 用 `monkeypatch.setattr` 把 `clauses.REQUIRED_CLAUSE_KEYS` 换成少一个键的副本（**只在测试进程内**），跑你的 `six_by_three` 矩阵 | 矩阵**判红**（因为参数化是从常量实取的） | `monkeypatch` 自动撤销；再跑一次全绿 |
| **PC-D** | 摘要稳定性反向对照：把 `content["coupon_fen"]` 改一个值 | `rule_digest` 结果**必须变**（若不变＝摘要没吃 content，判红） | 用副本 dict，禁改 fixture 文件 |
| **PC-E** | 反例合法性反向对照：把某条 `input_payload` 的 `events` 改成 `[]`（契约 `minItems=1`） | `TypeAdapter(CaseInput).validate_python` **必须抛 ValidationError** | 用副本，禁改 `src` |

**每条 PC 的回执必须给三段**：① 变异形态成立的证据（AST 片段或运行期打印，证明变异真的生效了）；② 判红读数（`rc` ＋ 失败用例名 ＋ 断言行）；③ 复原后的 face 对撞（`git status --porcelain` 回到只有 9 件 `??`、`git diff --numstat` 为空）。
**禁**把「变异导致 import 崩溃（rc=4 / collection error）」当成「有牙」。

---

## 8. U 项上报（**禁自行裁定**；手册 §6.4）

遇到下列情形**立即停手**，在回执的 `U_ITEMS` 段逐条写明「事实（含实测命令原文）＋ 影响 ＋ 你的候选方案（≥2 个）＋ 倾向」，然后**继续做不受影响的部分**（禁整棒摆烂）：

- **U-BASELINE**：`git rev-parse HEAD` != `0765099006544b72de505ea18258159443ff7349`。
- 本文件 §4 的任何实测读数与你复测**不符**（禁默默按你的值写，也禁默默按我的值写）。
- design §11.6 / §5.3 / §5.4 的原文与被测代码**冲突**，且本文件 §5 的 A262–A268 **未覆盖**该冲突。
- 某个 `CLAUSE_ISSUE_CODES` / `CHECK_ISSUE_CODES` / `BINDING_ISSUE_CODES` 的 code 在领域层**结构不可达**（例如 `SCHEMA_VERSION_UNSUPPORTED`，见 §6.1-B 第 17 条）。
- 需要动 §1.3 硬禁面的任何文件（包括「只加一行 import」）。
- 需要 HTTP / DB / TestClient 才能验的断言（**那是 S6 的面**，A257）。
- loop 用到第 **2** 轮仍有红。

---

## 9. 派单前置自检（编排器已逐项做完；你只需在回执里**复述结论 ＋ 贴你自己的复测命令**，禁跳过）

| 编号 | 义务 | 编排器实测结论（你必须复测） |
|---|---|---|
| PRE-15/20 | 派单文里的数字一律实测、禁猜测 | §4 全部数字来自 `.orch_tmp/r19_s5_measure*.py` 五个探针脚本的实跑输出 |
| PRE-19 | 检索命令限定路径 ＋ 输出上限 | 本文件所有命令都限定 `tests/domain` / 具体文件，无无界 `grep -rn` 全仓 |
| PRE-21 | 一律 `uv run --no-sync python`（仓库 .venv 的 **3.14.10**），**禁系统 python3**（3.12 会在 PEP 758 语法上 SyntaxError） | 见 §6.2 每条命令 |
| PRE-24 | 具名清单的既有覆盖对撞 | §2：37 名 × 594 既有函数 ⇒ 精确同名 **0** 命中；7 个文件名 **0** 命中 |
| PRE-25/26/27 | 符号定义点 / 枚举项数 / 契约面实取 | §3.1 的行号表 ＋ §4.2 的枚举项数全部实取 |
| PRE-29 | 口径回源、禁采信二手复述 | §3 的三张回源表（含 design 行号） |
| PRE-30 | 断言期望值回源 | §4.3 的反例/issues 分母全部实跑得出；§4.4 的 5 个构造陷阱是编排器**实测踩过**的 |
| PRE-33 | 符号实存对撞的**全仓范围** | `CaseInput` 在 `api/common.py:664`（**不在** domain）；`BoundaryCaseDraft` 在 `checks.py:171`（**在** domain）——两者都已按①`__all__`②全仓 grep③同名近形三处对撞 |
| PRE-34 | 行为守护的前置处置 ＋ 变异有效性 | 本棒无 HTTP 面 ⇒ 无中间件前置处置问题；§7 的 PC 要求「先证变异生效、再读 rc，并区分 rc=4/rc=1」 |
| PRE-35/36 | 哨兵全量普查 / 派生读数全键覆盖 | 属**编排器侧**义务（你无台账写权）；列出只为让你知道：入库批会做全量哨兵普查，你的回执 sha 会被逐字对撞 |
| A261 | §0 以 sha 为锚 | 本文件 §0 已用 `0765099`，未写 tag |

---

## 10. 回执格式（**结构化**，禁散文；编排器会独立复验每一项，禁采信自报）

```
RESULT: DONE | DONE_WITH_GAP | BLOCKED
LOOP_ROUNDS_USED: <n> / 2
BASELINE_SHA_SEEN: <git rev-parse HEAD 实测>
FILES_NEW: <逐件：路径 lines bytes sha256[:12]>   # 恰 9 件
TEST_FUNCTIONS: <逐文件：函数名清单（AST 实取）>
COLLECTED: <tests/domain/activity 的 collected 数> / <全仓 collected 数（期望 750+N）>
GATES:
  V0: <rc + 输出尾>
  V1: <9 件 face 三元组>
  V2: <AST 实取的函数名清单>
  V3: <ruff format --check rc / ruff check rc>
  V4: <mypy rc + "in N source files" 实测值>
  V5: <四条 -k 的 rc 与 collected>
  V6: <git status --porcelain 全文 + git diff --numstat 全文（应为空）>
  V7: <全量 pytest 尾 3 行>
  V8: <test_layering.py 的 rc 与用例数>
POSITIVE_CONTROLS: <PC-A..PC-E 逐条：变异生效证据 / 判红读数 / 复原对撞>
MEASURED_DELTAS: <你复测发现与本文件 §4 不符的每一处（若无，写「无」）>
U_ITEMS: <逐条：事实＋命令原文＋影响＋候选方案≥2＋倾向；若无写「无」>
TOKEN_USAGE: <若运行环境暴露则报数；否则逐字写「未报」并说明探测方式，禁估算>
TIER_CONFIRM: <你实际使用的 model 与 reasoning>
NOTES: <任何你认为编排器该知道的事，包括你主动加的用例>
```

> **最后**：本棒的产物是 M2-01 的**领域层证据面**，S7 会拿它去判 **AC-002 / AC-003 / AC-004**。所以「守护有没有牙」比「用例有多少条」重要得多：**每一条断言都必须能被一次变异打红**，否则它就是装饰。禁为了凑数写恒真断言（`assert True`、`assert len(x) >= 0`、只断言不抛异常而不断言 code/location 的形态）。
