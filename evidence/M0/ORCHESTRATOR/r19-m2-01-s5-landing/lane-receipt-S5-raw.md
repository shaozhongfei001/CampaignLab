# M2-01/S5 lane 回执**原文归档**（昵称 Sagan · `qwen3.8-flash`/medium · loop_cap 2 · budget 8k）

**归档口径**：本文件是 lane 回执的**逐字原文**（append-only 时序证据，**不回改、不润色**）。
编排器的独立复验结论见同目录 `00-index.md`；复验命令与输出原文见 `gates/V-independent-reverify.log`。
**PRE-29**：编排器**禁采信**本文件的任何自报读数，所有数字均已独立重跑核对。

- lane / task / round：**S5** / **M2-01** / **19**
- agent_id：`01a1e4e1-ecc2-7dc1-b31c-c05b9b18524b` · nickname：**Sagan**
- 派单文：`orchestrator/handoff/R19-lane-M2-01-S5.md`（424L / 48257B / sha256[:12] `c3ff2c257573`）
- 派单基线锚：`0765099`（派单文 §4.1）→ 由 **A269** 取代为 `d976974`
- 回执接收时点：2026-11-16T23:3x+08:00（本批入库前）

---

## 原文（逐字）

```
RESULT: DONE_WITH_GAP
LOOP_ROUNDS_USED: 1 / 2（轮内红→修：layering 文件名 sorted 序错 1 处、ruff RUF005×2、mypy×7；均在本轮闭环，「红在哪/改了什么」见 NOTES）

BASELINE_SHA_SEEN: d976974158390e1ce917d1a9fbb1cb0f2f4cc484（git rev-parse HEAD rc=0）
FILES_NEW（V1 命令原文实测，恰 9 件，路径 lines bytes sha256[:12]）:
  tests/domain/__init__.py 1 79 d4c9e96acb93（A262 授权；单行 docstring 非零字节）
  tests/domain/activity/__init__.py 1 97 d903691e61e7
  tests/domain/activity/test_bindings.py 117 4981 fc5d94cdbd3c
  tests/domain/activity/test_checks.py 207 7599 dc24c777b4e1
  tests/domain/activity/test_clause_gate.py 264 10796 23add408478c
  tests/domain/activity/test_diff.py 115 4821 3de150ac749d
  tests/domain/activity/test_digest.py 110 4352 6e41aeb5961f
  tests/domain/activity/test_layering.py 134 4817 5fbd5bdcacf8
  tests/domain/activity/test_states.py 163 6878 3c9ce991f2e1

TEST_FUNCTIONS: 40 个函数，逐字 = §6.1 清单（V2 AST 实取原文见下 GATES.V2；matrix 1 函数参数化出 9 例 ⇒ collected 48）
COLLECTED: tests/domain/activity 48 / 全仓 798（=750+48，N=48 实测）

GATES（全部 rc=0；输出尾逐字）:
  V0: HEAD d976974158390e1ce917d1a9fbb1cb0f2f4cc484 rc=0；上工前 porcelain=0（wc -l 实值 0）；tests/domain exists=False；基线 collect "750 tests collected in 1.35s"；ruff format 全表(上工前)="330 files already formatted"；ruff check="All checks passed!"；mypy="Success: no issues found in 113 source files"；Python 3.14.10；counts 台账实取 330/113/750(115py+215md)；7 目标文件名 tests/** 下 find 命中全 0
  V1: rc=0（上表 9 件三元组）
  V2: rc=0 —— states 7 名 / clause_gate 10 名 / digest 4 名 / bindings 6 名 / checks 7 名 / diff 4 名 / layering 2 名，与 §6.1 逐字一致（含 A263①改名 per_template 与 A267/A268 形态）
  V3: "9 files already formatted" rc=0；"All checks passed!" rc=0
  V4: "Success: no issues found in 122 source files" rc=0（113→122，A269 预期值）
  V5: -k immutable "3 passed, 45 deselected" rc=0；-k clause_gate "18 passed, 30 deselected" rc=0；-k state_machine "2 passed, 46 deselected" rc=0；-k "check_framework or boundary_case" "6 passed, 42 deselected" rc=0
  V6: porcelain（上工前）="0 条"；落地后仅 "?? tests/domain/"（+编排器在飞 state.json，见 CONTAMINATION）；git diff --numstat=""，deleted 全 0（纯新建）
  V7: "798 passed, 6 warnings in 173.29s (0:02:53)" rc=0；collect "798 tests collected in 0.62s"；全表 ruff format="339 files already formatted"、ruff check="All checks passed!"（与 A269 的 330→339/115→124py 对账面吻合）
  V8: test_layering.py "2 passed" rc=0

POSITIVE_CONTROLS（三段式；全部 rc=1，无一 rc=4；探针全在 /mnt/d scratch 与 tmp_path，未落工作树）:
  PC-A: 变异生效="MUTATION-PC-A" grep=True（scratch 副本里 _table_diff 短路 return []）⇒ "FAILED ...test_transition_tables_have_teeth_positive_control" 1 failed rc=1；复原对撞=sha256sum -c before.sha 9/9 OK、porcelain 回 "?? tests/domain/"
  PC-B: 变异生效=True（_forbidden 恒 False）⇒ "FAILED ...test_domain_activity_layering_scanner_has_teeth" rc=1；复原 OK
  PC-C: 真实文件+环境旗标 CAMPAIGNLAB_S5_PC_C=1 进程内减键 ⇒ matrix "9 failed, 9 deselected"（[callback_priority-same_day_scope] 等）rc=1；撤销后复跑 rc=0
  PC-D: 变异生效=True（coupon_fen +1→+0 模拟「digest 没吃 content」）⇒ "FAILED ...test_rule_digest_ignores_label_and_confirmation" rc=1；复原 OK
  PC-E: 变异生效=True（events=[] 换成原 payload，DID NOT RAISE）⇒ "FAILED ...test_boundary_case_inputs_validate_against_contract" rc=1；复原 OK

MEASURED_DELTAS:
  - U-BASELINE 已由 A269 预裁关闭，实测 HEAD=d976974158390e1ce917d1a9fbb1cb0f2f4cc484（与 A269 权威值逐字一致；派单文 §0/§6.2 的 0765099 锚与 328/337/113→122 表述均按 A269 取代）
  - 派单文 §4.1/§4.2/§4.3 全部读数复测一致（55 __all__/8 类/9 检查/23 码/9 门禁码/4 绑定码/1 活动码/9 键/dict2 键/3+4 迁移/64/1000/15-15-2-3/6-7-3-4 issues），零偏差；唯 §6.2 V0 命令注释里的基线全 sha 尾串 "443ff7349" 与本消息 "443ff77349" 相差一个字符——两者均已过时，实测锚=d976974
  - 落地后全表实测：ruff format 339 files、mypy 122 source files、collected 798（编排器对账面，未改任何配置）

U_ITEMS:
  - U-1（§6.1-B 第 17 条，实测命令=inspect.signature(clauses.evaluate_clause_gate) 与 run_checks 探针）：事实＝evaluate_clause_gate 签名只有 (*, template, terms, registered_evidence_ids)，不接 schema_version；SCHEMA_VERSION_UNSUPPORTED 在 domain 全部发射面 grep=0，仅登记于 CLAUSE_ISSUE_CODES（clauses.py 注释原文「判定在 api／service 层」）⇒ 该 code 在领域层结构不可达。领域可达的同事实入口实测为 content["schema_version"]!=1 → run_checks 报 TEMPLATE_CONST_MISMATCH(/content/schema_version, ERROR)，==1 不报。影响：第 17 条无法在领域层断到 SCHEMA_VERSION_UNSUPPORTED 本体。候选：(a) 本批已采——测试钉「标签单一出处＋领域实测入口 TEMPLATE_CONST_MISMATCH 双分支＋门禁不误报该标签」，本体发射归 api/service（S6 面）；(b) 给 domain 增加发射点——须改 src/**，S5 无写权。倾向 (a)。

TOKEN_USAGE: 未报（探测方式：get_goal 返回 {"goal":null}，运行环境未暴露 budget/usage 字段；exec 工具返回亦无计费口径；禁估算故按「未报」）
TIER_CONFIRM: 按派单档位 qwen3.8-flash / reasoning_effort=medium / 8k / loop帽2 执行（本环境不暴露模型身份自证面，如实按派单档位申报）

IN_FLIGHT_CONTAMINATION: `M orchestrator/state.json`（staged 359/41，编排器在飞台账批，mtime 23:30:59，非 S5 所写；未触碰、未 unstage；受影响面探针 tests/unit/test_state_ledger.py+test_counts_freshness.py 实测 11 passed，无既有红）

NOTES:
  - 轮内红→修记录：①test_layering EXPECTED_FILE_NAMES 排序错（diff.py<digests.py，f<g）→改序；②ruff RUF005×2 + isort×3 →ruff check --fix/手改；③mypy 7 处（Any-return、裸 tuple、dict[str,object] 推断）→标注/局部 cast。全部发生在首轮落地自检内，未产生第二轮。
  - A265 依据：实测 input_payload 键集合 CP 类=[customer_id, events, initial_budget_used_fen, initial_used, registered_at, schema_version, template]、CB 类=[channel, customer_id, day, events, schema_version, template, used]，**均含 template** ⇒ 无需测试内补键（防御分支仍保留）。
  - 矩阵 callback 3 键在 examples[3] 无对应 terms（A266 只冻结 coupon 6 键取文件），以 _synth_term 造 CONFIRMED+EV-CLAUSE-001+非空 decision 的最小形态；PC-C 的减键开关是 test_clause_gate.py 内 autouse fixture 读环境旗标，默认关、不影响任何门。
  - §2 的「37 名×594 既有 AST 同名对撞」我未复刻脚本，但对撞后果已由全量 798 collected/passed 无模块/函数遮蔽错误间接证实；7 个文件名 find 命中 0 已独立复测。
  - 飞行中一次 PowerShell 命令因参数拼写失败（误发 "cd /tmp/qa…"），解析即拒、零副作用，如实登记。
  - 未 commit/push/tag，未动 state.json 与任何既有文件；提交权属编排器。
```

---

## 归档者的两条如实批注（不改动上文一字）

1. **`IN_FLIGHT_CONTAMINATION` 一条经编排器核对为真且属预期**：lane 飞行期间编排器落了纯台账批
   `4050852`（tag `R19-resume-S5spawn`），它只改 `orchestrator/state.json`。lane **未触碰、未 unstage**
   该文件，处置正确（手册 §6.4：越界即回报，禁顺手改）。本批入库时该文件由 `run_commit` 统一处理。
2. **lane 发现的 sha 尾串差异，责任在编排器而不在派单文**：`git rev-parse 0765099` 实测
   ＝ `0765099006544b72de505ea18258159443ff7349`（**40 位**），与派单文 §6.2/§8 的原文**逐字一致**；
   多出一个 `7` 的是**编排器 spawn message** 里的那一份（41 位）。⇒ 立自纠 **R19-8**，
   详见 `00-index.md` §5。lane 如实上报差异而未自行采信任一侧，做法正确（PRE-29 的双向要求）。
