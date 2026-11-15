# R18 · M2-01/S4 入库批 —— 编排器独立复验索引（00-index）

**批次**：M2-01/S4（`api/rules.py` 新建 ＋ `app.py` 挂载 5→6）的交付入库 ＋ 守护迁移批
**lane**：S4 / 昵称 `Wegener` / agent_id `01a1e0ff-bd00-7b53-bf8a-9c1b3510d5ea` / `qwen3.8-flash` · medium
**派单基线**：`5416990`（counts 323/112/748）→ 派单文入库 `b510b33`（counts 325/112/748）
**入库前 HEAD**：`cf29fc9`（R18-backfill-S4agentid，纯台账）
**复验时点**：2026-11-16T05:33–05:40+08:00
**复验口径**：PRE-29 —— 编排器**独立重跑**，禁采信 lane 自报；lane 回执仅作对照。

---

## 1. 交付面 face（编排器实测，非采信）

| 文件 | 行数 | 字节 | sha256[:12] | 归属 |
|---|---|---|---|---|
| `src/campaignlab/api/rules.py` | 389 | 17913 | `c7b3cccee6ec` | **lane 新建**（编排器一字未改） |
| `src/campaignlab/api/app.py` | 178 | 7857 | `2e4aad126172` | **lane 修改**（原 175L/7726B/`76fcb0778f64`，`numstat 3/0`） |
| `tests/unit/test_s3b_routes.py` | 239 | 11531 | `99a78f2bd590` | **编排器迁移**（E1，A258） |
| `tests/unit/test_s2b2_app_injection.py` | 389 | 16635 | `07e1d8a7ea5d` | **编排器迁移**（E2，A259） |
| `tests/unit/test_api_app.py` | 178 | 9168 | `e1eab478a344` | **编排器新增**（FU-60 两条探针 ＋ R18-12 修正后的**终面**） |
| `orchestrator/defects/D-052.md` | 150 | 10413 | `6900b721bf0c` | **编排器附录**（R18-11 更正） |

### 1bis 如实登记：`test_api_app.py` 的**双面**（本批内发生过一次自我修正）

- 首版面（编排器初稿，**未入库**）：`166L / 8166B / 99c66cbb1f6a` → ruff format 归一后
  `168L / 8168B / 68b50bf37dbf`；
- 该首版**判红**（2 failed）⇒ 依 **R18-12** 修正（FU-60 探针补白名单 `Origin` 头）后的**终版面**
  才是本批入库面：`178L / 9168B / e1eab478a344`（已回填进 §1 表格）。
  **注意**：`gates/V-independent-reverify.log` 的 V0/V1 段记录的是**修正前**的 face
  （`168L / 8168B / 68b50bf37dbf`）——该 log 是**时序证据、按发生顺序 append-only**，故不回改；
  本文件 §1 表格记的是**终面**。两处读数不同**属预期**，不是矛盾。
- **为何如实记双面**：首版从未进入任何提交，但它是本批 loop-engineering 迭代的真实痕迹；
  只记终面会让「一次成功」的假象掩盖 R18-12 这条自我纠正。

---

## 2. 静态门（编排器实测，全部 rc=0）

| 门 | 命令要点 | rc | 关键读数 |
|---|---|---|---|
| V0 | `ruff format`（6 件改动面归一） | 0 | 首跑 `1 file reformatted, 5 left unchanged`；终跑 `5 files already formatted` |
| V1 | face 三件套 ＋ `tail -c 1 \| od -c` | 0 | `rules.py` 尾换行 `\n` 在场 |
| V2 | `ast` 实取符号面 ＋ `router` 实取路由面 | 0 | 公开 **7** handler ／ 私面 **恰 4** ／ `__all__` **8** 项 ／ `prefix='/api/v1'` `tags=['rules']` ／ **7** 条路由（5 个唯一 path），2xx 实测 `createRule=201`、其余 6 个 `=200` |
| V3 | `grep -i -E "SELECT \|INSERT \|UPDATE \|DELETE \|sqlite3\|execute"` on `rules.py` | grep rc=**1** | **零命中** ⇒ 路由层一条 SQL 都没有（PYTHON.md:5 分层红线） |
| V4 | `ruff format --check` ＋ `ruff check` ＋ `mypy src tests` | 0 / 0 / 0 | `All checks passed!` · `Success: no issues found in 109 source files` |
| V5 | `git diff --numstat -- app.py` | 0 | `3  0` ⇒ added=3（≤3 ✓）、deleted=**0** ✓（A90① 的 A10 最小例外） |
| V6 | `git status --porcelain` on 硬禁面 | 0 | **0 行** ⇒ `common.py`/`deps.py`/`activities.py`/`application`/`domain`/`infra`/`pyproject.toml` **一字未改** |

---

## 3. 阳性对照（PC）—— 编排器**自己重做**，不采信 lane 的仿真

| PC | 变异 | 期望 | 实测 | 判定 |
|---|---|---|---|---|
| **PC-A** | `app.py`：删 `if rule_service is not None:` ⇒ rules 改**无条件挂载** | E1 与 FU-60(rules) 均 RED | `2 failed`（`test_app_py_contains_only_the_a85_mount_lines` ＋ `test_rules_router_is_not_mounted_without_rule_service`），rc=1 | **有牙 ✓**（A258 的 V3 迁移形态成立；lane 的 V1「只改计数」形态实测无牙，已弃用） |
| **PC-B** | `app.py`：追加 `from campaignlab.api.health import router as _probe`（模块**存在**但不在 `_EXPECTED_API_IMPORTS`） | G6 精确集合断言 RED `1 failed`，判红点 `tests/unit/test_s2b2_app_injection.py:297`（正是 `_EXPECTED_API_IMPORTS` 的精确集合断言），rc=1 | **有牙 ✓** |
| **PC-B（首版，已作废）** | 追加 `from campaignlab.api import health as _probe` | —— | rc=0 | **读数不可用**：该写法的 `ImportFrom.module` 是 `campaignlab.api`，本就在期望集合内 ⇒ 变异**无效**（如实登记，禁把「rc=0」当成「守护无牙」的证据） |
| **PC-B（次版，已作废）** | 追加 `from campaignlab.api.zzz_mutation_probe import nothing` | —— | rc=**4**（collection ERROR） | **读数不可用**：模块不存在 ⇒ 测试模块 import `create_app` 时即 ImportError，红在**收集期**而非断言，未证明精确集合不变量本身有牙 |

**还原保证**：每次变异后 `cp` 回备份并**校验 sha**，三次 `RESTORED-OK`（`2e4aad126172`）。
变异全部落在 `src/campaignlab/api/app.py` 的工作树副本，**未** `git add`、**未**进入任何提交。

---

## 4. 预期红（E1/E2）的闭合

派单文 §2 预告的 2 条预期红，在本批由**编排器同批迁移**（A245/A248 先例；lane 的硬禁面含 `tests/**`）：

| 预期红 | 判红原文（lane 实测 ＋ 编排器复验一致） | 本批迁移 |
|---|---|---|
| **E1** `tests/unit/test_s3b_routes.py::test_app_py_contains_only_the_a85_mount_lines` | `:220 assert len(mounted_lines) == 5` → `AssertionError: assert 6 == 5` | `pairs` 追加 rules 的「if＋include_router」二元组 **且** 计数 `5→6`（A258 的 V3 形态）；另加「rules 挂载行恰 1 条」「`rules_router` 出现 ≤3 行」两条 |
| **E2** `tests/unit/test_s2b2_app_injection.py::test_g6_mount_and_middleware_surface_unchanged` | `:275 assert ordered == EXPECTED_MOUNT_LINES` → `Left contains one more item: 'app.include_router(rules_router)'` | `EXPECTED_MOUNT_LINES` 追加第 6 项；`_BANNED_ROUTER_MODULES` 清空 **并**把判据升级为 `_EXPECTED_API_IMPORTS` 精确集合不变量（A259，禁留恒真断言） |

**如实登记 lane 报的偏差**：E2 的第二 bite（`:281` 的 `_BANNED_ROUTER_MODULES` 命中）本轮**未被执行到**
（同一用例内 `:275` 先红）；本批把禁串面清空后该 bite **永久消失**，其守护职责由 A259 的精确集合
不变量承接（更强：多一个 / 少一个 / 换一个 api 子模块 import 都判红）。

---

## 5. 本批裁定与自我纠正（全文见 `orchestrator/state.json`）

- **A257**（U-1）：派单文 §6.2 V8 点名的 `tests/unit/test_contract_declarations.py` **在仓内不存在**
  （实测 pytest rc=4）；活体文件是 `tests/api/test_contract_declarations.py`，但它绑定
  `M0-02.slice.json` 且其自身 docstring 明载 **N5「禁第二真源」**（jobs 四 op 的声明面取证
  「归 M0-04 的守护，本目录不重复登记」）⇒ 裁定 **rules 的 7-op 声明面／契约对撞归 S6**
  （`tests/api/activities/**`，该棒已承载 `-k etag412` / `-k rule_diff` 两个任务卡 gate，
  且 `orchestrator/handoff/M2-01.slice.json` 实测在场可供对撞）。**S6 派单文必须逐字携带本裁定。**
- **A258**（U-2）：E1 迁移采 **V3 形态**（pairs ＋ 计数两处同改）。依据＝lane 的四形态仿真
  ＋ 编排器 PC-A 独立复验（V1 只改计数 ⇒ BASE/MUT 双绿＝无牙）。
- **A259**（U-3）：`rules` 从禁串面移除；因清空会使 `banned_hits` 沦为恒真，同批**升级**为
  `campaignlab.api.*` 的**精确集合**不变量（期望集合按 PRE-30 实测取值 = 8 项）。
- **A260**（U-4）：PC-4 的**运行期**判据（「TestClient 实测 == 200」）结构性 **NO_TEETH** ——
  信封（`RuleWriteOutcome.status` → `replay_from_envelope`）承载状态码、处理器直接返回 `Response`
  ⇒ FastAPI 装饰器的 `status_code` 被短路。裁定：判据面改为**「装饰器 2xx 声明 vs 切片 2xx」对撞**；
  S6/S7 派单文**禁**再按失真原文写运行期状态码断言（会产出空转用例）。
- **A261**（U-5）：`git tag -l` 实测 **0 项** ⇒ 台账里的 `R18-*` 只是**名义锚点**、从不落 git tag。
  裁定：接受名义锚点；**自本批起派单文 §0 与简报一律以 sha 为锚**，禁写「当前 HEAD 应为 tag X」。
- **R18-11**（编排器自我纠正，MAJOR）：**D-052 的 ①② 两条断言事实错误**。全仓对撞实测
  `campaignlab.domain.activity.__all__`（55 项）**含** `BoundaryCaseDraft`，定义在
  `domain/activity/checks.py:171`，字段实测 `['id','label','template','input_payload','verification']`
  ⇒ 本单「仓内无 `BoundaryCaseDraft`」「无 `input_payload`」均**错**（③ 关于 `CaseInput` 的断言**对**）。
  根因＝编排器立单时把对撞范围限定在 `api/common.py` 单个模块（PRE-24/PRE-25 的**范围性**失误）。
  **A256 结论不变**（路由层确实无事可校验），但理由重述为「校验点位于**应用层**
  `application/activity_service.py:1925` 的 `BoundaryCase.model_validate`，位置更靠前＝更强」，
  而**非**原文的「非法反例在类型上不可达」（`input_payload` 静态类型是未校验的 `Mapping[str, Any]`，
  类型上**可达**转换点）。详见 `orchestrator/defects/D-052.md` §9。
- **R18-12**（编排器自我纠正，MINOR）：编排器自己写的 FU-60 首版探针**判红 2 条**。根因＝
  `OriginHostGuard`（BaseHTTPMiddleware）对**非安全方法**先于路由判来源，TestClient 默认不带 `Origin`
  ⇒ 得到 403 `ORIGIN_DENIED`，**掩盖**了「路由未挂载 ⇒ 404」这一目标事实。修正＝逐请求带白名单
  `Origin: http://testserver`；**禁**降级为「只探 GET」（会丢掉 4 个非安全 op 的覆盖）。
  同批作废两次无效 PC-B 变异（见 §3），如实留档。
- **PRE-33**（新立，防 R18-11 再发）：符号实存对撞**必须全仓**（`__all__` / `ast` / `grep -rn`），
  禁把范围限定在单个模块后就下「仓内无此符号」的结论。
- **PRE-34**（新立，防 R18-12 再发）：写「路由未挂载 ⇒ 404」类行为守护时，**必须**先实测
  中间件链对**非安全方法**的前置处置（本项目＝Origin 守卫 403），探针需显式带白名单 `Origin`。

---

## 6. FU 处置

- **FU-60** → **CLOSED**（本批）：`activities` 与 `rules` 的裸装配 404 探针各 1 条已入库，
  并经 PC-A 实测有牙。
- **FU-61** → 保持 **OPEN**：本批仍**无**机器化句柄可归档 lane 原始回执
  （`lane-receipt-S4-digest.md` 是**摘要**、非原文，已在其首行明示）；token 计量句柄仍缺失
  ⇒ 护栏② `flash_share_tokens` 继续冻结为「不可判」（A183：记 null，禁估算）。
- **FU-53 / FU-59**（`common.py` 的 `IF_MATCH_PATTERN` 收敛）→ 仍归**专门解冻批**，
  本批**未**动 `common.py`（V6 实测 0 行改动）。**如实登记**：S4 依 A228 先例在 `rules.py` 内
  就地声明 pattern，使该字面量由 2 处变 **3** 处（`jobs.py` 2 命中 / `activities.py` 1 / `rules.py` 2，
  各文件内 distinct 字面均 1 种 ⇒ 无第二份漂移），FU-53 的收敛成本随之上升，M1 开闸前必须做。

---

## 7. counts 预测（由 run_commit 的冻结树实测逐条对账，不符即 reset＋回滚）

| 键 | 入库前（`cf29fc9`） | 本批预测 | 增量来源 |
|---|---|---|---|
| `ruff_formatted_files` | 325 | **328** | +1 py（`rules.py`）＋2 md（本文件 ＋ lane 回执摘要） |
| `mypy_source_files` | 112 | **113** | +1（`src/campaignlab/api/rules.py`） |
| `pytest_passed` | 748 | **750** | +2（FU-60 的两条探针）；E1/E2 是**迁移**既有断言，不新增用例 |
| `in_scope_py` | 114 | **115** | +1 |
| `in_scope_md` | 211 | **213** | +2 |

`gates/*.log` 是 `.log`，**不入** ruff 的 py+md 作用域（`RUFF_SUFFIXES=(".py",".md")`）⇒ 不计入分母。
`orchestrator/state.json` 是 `.json`，同理不计入，也不入 mypy 域。
