# R19 · **FU-59 解冻批** —— If-Match 正则的全仓单源收敛（编排器自办）

- **tag**：`R19-FU59-thawIfMatch`　**parent**：`89b013a`（全 `89b013ad52f902257d33308f7caa42891b1838f8`，tag `R19-backfill-S5land`）
- **时点**：2026-11-17T01:52:00+08:00　**执行者**：编排器自办（`accounting_rule_orch_self_served`：**不入** `budget.subtask_log`）
- **性质**：`api/common.py` 的**专门解冻批**（FU-59 原文：「只能由持权棒或编排器在专门的解冻批内做，
  禁在其它 lane 的写权面里顺手改」）；**M1-01/S1 的门控前置**（该棒 `slack=0`、tier `qwen3.8-max`）
- **本件所有数字／sha／面读数均由生成脚本实测派生**（PRE-37 第 1/3 款），命令原文与输出见
  `evidence/M0/ORCHESTRATOR/r19-fu59-ifmatch-thaw/commands-and-outputs.log`

---

## 1. 为什么现在必须做（关键路径）

FU-59 自 R18 立单起连续两批（R18-landS4、R19-landS5）如实登记为「保持 OPEN · 本批未收敛」，
理由都是当批 lane 的写权面与 `src/campaignlab/api/common.py` 零交叉。R19-landS5 的登记原文已明确：

> **关键路径影响**：M1-01/S1 是 `slack=0` 的关键棒、tier `qwen3.8-max`，其门控正是 FU-59
> ⇒ 解冻批是 wave-3 开闸的**前置阻塞项**，不能再顺延。

`api/common.py::check_if_match` 的 docstring 明载该 helper「供 M1 起 **16 个 If-Match op** 复用」。
本批实测契约里 If-Match 形参**恰为 16 个**（§D1）、schema **两两逐字同构**（distinct = 1 种），
与该 docstring 的 16 逐字吻合 ⇒ 若不在 M1 开闸前收敛，同一正则字面量将由 5 处扩散到 16 处，
收敛成本随棒数**线性**上升（FU-59 `ordering_note` 原文）。

## 2. 落点裁定（**A271**）：`api/common.py` 是**定义点**，不是纯转发面

FU-59 原文要求「必须在动手前由持权棒实测确认落点，禁想当然」，并提示 `common.py:22-25` 的
「纯转发面纪律」。编排器实测结论：**该纪律的辖域被 D-051 §38 读宽了**。

| 实测事实 | 出处 | 结论 |
| --- | --- | --- |
| 禁令原文是「严禁在本文件重新定义**上述任何符号**」，其上文**具名枚举**了 `PROBLEM_CODES` / `_TITLE_BY_CODE` / `_STATUS_BY_CODE` / `DomainError` 及 13 子类 / `_new_request_id` / `RESOURCE_ID_PATTERN` | `src/campaignlab/api/common.py` 模块 docstring 的「归属变更留痕」段 | 禁令辖域 = **该枚举集合**，非「任何符号」 |
| 模块 docstring **首段**自述「本文件是 M0-03b 的**冻结面**之一，故**所有取值都写死在此并附出处**，禁止在调用点现编」 | 同上，第 3 行 | common.py 本身就是 HTTP 公共件的**定义点** |
| `X_REQUEST_ID_HEADER` / `PROBLEM_MEDIA_TYPE` / `IDEMPOTENCY_KEY_HEADER` / `IDEMPOTENCY_KEY_MIN_LENGTH` / `IDEMPOTENCY_KEY_MAX_LENGTH` / `CURSOR_TAG_HEX_LENGTH` / `CURSOR_MAX_LENGTH` / `UNSAFE_METHODS` 全部**定义于本文件** | §C3 同族的常量段实测 | 既有 HTTP 常量的定义点先例一致 |
| `etag()` 与 `check_if_match()`（If-Match 的**唯一消费者**）均定义于本文件 | `src/campaignlab/api/common.py` 的 ETag 段 | 新常量与两者互为对偶，分居两文件反而制造第二处认知负担 |
| 机器守护 `tests/unit/test_domain_errors.py::test_common_py_contains_no_moved_definition` 的 `FORBIDDEN_DEFINITIONS` **不含** `IF_MATCH_PATTERN` | 该文件的常量表 | 在本文件定义它不与任何既有守护冲突 |

**裁定**：`IF_MATCH_PATTERN` 的**定义点 = `src/campaignlab/api/common.py`**（HTTP 常量段），
**不落 `domain/`**。理由：它约束的是 **HTTP 头 `If-Match` 的线格式**（与 `etag()` 产出的响应头
互为对偶），不是领域不变量；`domain/ids.py::RESOURCE_ID_PATTERN` 之所以在 domain，是因为它约束
**领域标识符**本身。把线格式常量放进 domain 会反向污染领域层。
⇒ D-051 §38「common.py 的纯转发面纪律本身就会阻止在该处新建常量」这一归因**不成立**，
本批一并更正（D-051 结案见 §8）。

## 3. 交付面（实测前 → 后）

| 文件 | 类型 | 前行 | 前字节 | 前 sha256[:12] | 后行 | 后字节 | 后 sha256[:12] |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `src/campaignlab/api/common.py` | 修改 | 1168 | 45605 | `836e7b3e8d3a` | 1186 | 47180 | `b2908617d193` |
| `src/campaignlab/api/activities.py` | 修改 | 221 | 9955 | `887bd377a4f7` | 223 | 10121 | `3865f3eb6b3c` |
| `src/campaignlab/api/jobs.py` | 修改 | 371 | 16916 | `735d30baf0c4` | 372 | 16934 | `e9b575602e56` |
| `src/campaignlab/api/rules.py` | 修改 | 389 | 17913 | `c7b3cccee6ec` | 391 | 18034 | `eac1377a4b72` |
| `tests/unit/test_domain_errors.py` | 修改 | 189 | 7771 | `a933def6c4e5` | 194 | 8205 | `ff4c25a659b6` |
| `tests/integration/jobs/test_jobs_router_s4.py` | 修改 | 683 | 26515 | `c3110b40b71d` | 701 | 27630 | `ddd3ba8c362f` |
| `tests/unit/test_if_match_pattern_single_source.py` | **新建** | — | — | — | 354 | 16753 | `6fa13556ab67` |

**`api/common.py` 的三处改动**（全批唯一触及冻结面的文件）：
① `__all__` 追加 `"IF_MATCH_PATTERN"`（位置：`IDEMPOTENCY_KEY_MIN_LENGTH` 之后、`PROBLEM_CODES`
之前 —— 常量段内字母序，`IF_MATCH_PATTERN` > `IDEMPOTENCY_KEY_*` 且 < `PROBLEM_*`）；
② HTTP 常量段新增 `IF_MATCH_PATTERN: Final = r'^"[1-9][0-9]*"$'`，附 16 行出处注释（契约路径 ＋
实测时点 ＋ `live_openapi_sha16` ＋ A271 落点裁定 ＋ 守护文件指针）；
③ `etag()` 的 docstring 原先**内嵌了该正则字面量**，改为指向 `IF_MATCH_PATTERN`
（否则「全仓字面量唯一」这条判据会被 docstring 自己打红 —— 这是 D-051 §49 要求的必然连带）。

**冻结面 sha 变更**：`api/common.py` `836e7b3e8d3a` → **`b2908617d193`**。
⇒ 立 **PRE-40**：后续派单文引用冻结面 sha 一律取本批登记的新值，禁沿用 `836e7b3e8d3a`
判「冻结面被动过」。同批 `activities.py` / `jobs.py` / `rules.py` 的 sha 亦变更（§B2/B3 逐件实测）。

## 4. 收敛面（5 处内联字面量 → 单源常量）

FU-59 的 `what` 原文写「三处内联字面量（`api/jobs.py:216`、`api/jobs.py:300`、`api/activities.py`
的 `update_activity`）」——那是 **R18 时点的快照**。本批实测（§C1/C2）：**5 处**，行号亦已漂移
（R18 之后 `rules.py` 由 M2-01/S4 落地，新增 2 处）。按 **PRE-37 第 1 款**以实测为准：

| # | 收敛点（`pattern=IF_MATCH_PATTERN`） |
| --- | --- |
| 1 | `src/campaignlab/api/activities.py:194` |
| 2 | `src/campaignlab/api/jobs.py:221` |
| 3 | `src/campaignlab/api/jobs.py:305` |
| 4 | `src/campaignlab/api/rules.py:260` |
| 5 | `src/campaignlab/api/rules.py:308` |

分布＝`activities.py` 1 ／ `jobs.py` 2 ／ `rules.py` 2（§C2 实测，与 FU-53 `note_R18_S4land`
登记的「`jobs.py` 2 / `activities.py` 1 / `rules.py` 2」逐字吻合）。
收敛后该正则字面量在 in-scope Python（`src` / `tests` / `scripts`）里**只剩 1 处**：
`src/campaignlab/api/common.py:190`（§C1）—— 即 D-051 §49 要求的「钉住全仓该字面量只出现 1 次」。

## 5. 机器化哨兵（FU-59 的**同批硬性要求**）

新件 `tests/unit/test_if_match_pattern_single_source.py`（354 行 /
16753 B / `6fa13556ab67`），**11 个用例 = 5 条判据 + 6 个阳性对照**。
四条判据全部写成**纯函数**（入参＝源文本／契约对象，出参＝违规清单），阳性对照把合成输入喂给
**同一个函数** ⇒ 牙是真牙（PRE-33/PRE-34 禁无牙守护）：

| 判据 | 纯函数 | 钉住什么 | 阳性对照 |
| --- | --- | --- | --- |
| ① 契约镜像 | `contract_offenders` | 契约 16 个 If-Match 形参两两同构，且 `pattern` 逐字 == `common.IF_MATCH_PATTERN` | ④ 改一个 pattern → 必红；⑤ 摘掉一个形参 → 分母判据必红 |
| ② 字面唯一 | `scan_literal_sites` | 该字面量在 in-scope Python 里恰 1 处，且在 `api/common.py` 的常量赋值行 | ① 合成第二份 → 必报 2 处 |
| ③ 声明收敛 | `header_offenders`（AST） | 凡 `Header(alias="If-Match")` 的 `pattern=` 必须是**名字** `IF_MATCH_PATTERN`；并兜住「换 alias 名内联同一正则」的绕过面 | ② 改回内联 → 必红；③ 干脆不声明 `pattern=` → 必红 |
| ④ 同族钉桩禁分叉 | `all_count_pins` | 全仓所有 `len(<common 别名>.__all__) == <整数>` 的钉桩两两相等且 == 运行期实测；处数 >= 下界（禁靠删钉桩变绿） | ⑥ 合成一处陈旧钉桩 → 必被扫出 |

**判据 ④ 是本批新立的元守护**，直接根治 §6 的 R19-10。契约分母 `16` 与声明处下界 `5`
均在件内以具名常量承载并附归因（D-012/D-014）；声明处取 `>=` 而非 `==`，因为 M1 起还有 11 个 op
要接 If-Match，**增长属预期，禁把增长判红**。

## 6. 自纠 **R19-10**：事前扫描漏掉同族钉桩的**别名**

- **事实**：编排器动手前用 `grep -rn "common\.__all__" tests/` 扫同族前提哨兵，只命中
  `tests/unit/test_domain_errors.py`（2 处 `== 79`）。实际还有**第二处**：
  `tests/integration/jobs/test_jobs_router_s4.py::test_common_all_is_79_with_jobpage_and_problem_codes_still_20`
  —— 它以 **`common_module`** 为别名 import，故按符号名 grep **扫不到**。该红是被全量 pytest
  撞出来的（`assert 80 == 79`），不是被事前扫描发现的。
- **根因**：扫描口径按**符号名**而非按**被钉住的值**。同一事实（`len(common.__all__)`）被多个文件
  以不同别名写死时，按名 grep 的分母天然不全 —— 这正是 **D-047 / FU-53** 家族「哨兵静默到期」的
  同构形态，只是触发方向相反（那里是哨兵到期没人改，这里是改动方没扫全哨兵）。
- **影响**：**无数据损失、无污染入库**。红发生在工作树、入库前；`run_commit` 尚未调用，HEAD 与台账均未动。
- **fix**：① 同批收敛第二处钉桩（79 → 80），并**把函数名里的数字去掉**
  （`test_common_all_is_pinned_with_jobpage_and_problem_codes_still_20`）—— 原名在项数变更后与断言体
  自相矛盾，这正是 **D-044** 修过的形态；历史 node id 的原样留档见
  `evidence/M0/M0-04/positive-control-s4.log`（依 D-011 不改写）。② 新增判据 ④ 元守护。
  ③ **FU-53 范围扩展**：前提哨兵普查必须**按被钉住的值扫**（如 `== <int>`）并跑全量 pytest 对撞，
  禁只按符号名扫。
- **并登记**：FU-59 `what` 里的行号（`jobs.py:216`/`:300`）与处数（「三处」）是 R18 时点快照，
  本批实测为 5 处（§4）。依 D-011 **不改写** FU-59 原文，实测清单以本件与台账 `resolution` 为准。

## 7. 自纠 **R19-11**：`baseline_authoritative.current` 的**双套读数分叉**

- **事实**（§F3 实测）：同一节点内 `current.counts` = **341/122/798·124py+217md**（权威、正确），
  而 `current` 的**扁平字段** = **330/113/750·115py+215md**、`current.as_of` = `2026-11-16T23:30:59+08:00`
  —— 三者全部停在上一批（`4050852`，tag `R19-resume-S5spawn`）的时点，而 `current.head`/`head_full`/
  `commit_tag` 已推进到 `b834a27`/`R19-landS5`。即 `b834a27`（R19-landS5）批推进了 sha 与 `counts`，
  **漏推**扁平字段与 `as_of`。
- **根因**：同一份读数在台账里有**两个存放位**，而写入是手工逐键拷贝（正是 **R19-1 / PRE-36 /
  FU-62** 要根治的「派生读数部分键拷贝而静默陈旧」）。
- **影响**：**未污染门禁**（`run_commit` 的对账口径是 `resume.self_check_gates_rc0.counts`，
  该键一直正确）；污染的是**下一棒派单文 §0 的权威基线读数面** —— 若派单文从扁平字段取值，
  会把 330/113/750 当成基线发给 lane。属**静默失真**，不红任何门。
- **fix**：本批把扁平五键与 `as_of` 校正为本批实测真值，`previous_values` 原样留档（D-011）；
  **FU-62 范围扩展**第 4 类用例：`baseline_authoritative.current` 的扁平计数字段必须由 `current.counts`
  **程序化派生**并断言逐字相等，禁手工二次拷贝。

## 8. 立规与新单

- **PRE-40（冻结面 sha 重定基）**：`api/common.py` 的冻结面 sha 自本批起为 **`b2908617d193`**
  （原 `836e7b3e8d3a`）；`activities.py` `3865f3eb6b3c`、
  `jobs.py` `e9b575602e56`、
  `rules.py` `eac1377a4b72`、
  `test_domain_errors.py` `ff4c25a659b6`、
  `test_jobs_router_s4.py` `ddd3ba8c362f` 同批变更。
  后续派单文与复验脚本引用冻结面 sha **一律取本批登记值**，禁沿用旧值判「冻结面被动过」。
- **PRE-41（前提哨兵普查口径）**：凡改动**被多处钉桩的公共面**（`__all__`、常量表、冻结 sha、
  counts），事前普查必须**按被钉住的值扫**（`== <int>` / `sha256[:12]` 字面）＋ 跑全量 pytest 对撞，
  **禁只按符号名 grep**（别名会漏，R19-10 的根因）。普查结果必须写进批件的 §面读数表。
- **FU-64（新立，P2）**：`orchestrator/handoff/M2-01-design.md` 的 `:215`「`IF_MATCH_PATTERN` **不在**
  `__all__` 里但确实从 `api.common` 导入可用」与 `:82`/`:649-650` 的语境自本批起**部分失真**
  （常量已存在**且已在** `__all__` 内）。设计文受 **D-011** 保护不得改写原文 ⇒ 由 FU-64 追注钉住
  权威面（`len(common.__all__) == 80`、`IF_MATCH_PATTERN in common.__all__`，运行期实测），
  并规定**后续派单文禁再引用 `:215` 的该句**。
- **D-051 结案**（`FIXED_PENDING_Q` → `CLOSED`）：其技术债面（FU-59）已由本批清偿，
  其归因面（§38「纯转发面纪律阻止新建常量」）已由 **A271** 更正。结案段以 append-only 方式追加进
  `orchestrator/defects/D-051.md`（原文一字不改）。
- **FU-59 关闭**（`OPEN` → `CLOSED`）：`what` 的四项要求（追加常量 / 纳入 `__all__` / 改 5 处 import /
  同批增设机器化哨兵）逐条兑现，落点已实测裁定（A271），**无残留**。
- **FU-53 / FU-62 保持 OPEN**，各追加一条范围扩展（§6 / §7）。**FU-61 保持 OPEN**（本批未触及）。

## 9. counts 与四门

| 项 | 入库前（`89b013a`） | 本批预测 | 判据 |
| --- | --- | --- | --- |
| `ruff_formatted_files` | 341 | **343** | +1 py（新哨兵）+1 md（本件）；`.log` 不在 `RUFF_SUFFIXES` |
| `mypy_source_files` | 122 | **123** | +1（新哨兵在 `tests/`，属 mypy 域）；已实测 `Success: no issues found in 123 source files` |
| `pytest_passed` | 798 | **809** | +11（新哨兵 11 例）；工作树全量已两次实测 **809 passed**（§E4/E5） |
| `in_scope_py` | 124 | **125** | +1 |
| `in_scope_md` | 217 | **218** | +1 |

四门由 `scripts/orch_harness.py::run_commit` 在**冻结索引树**上跑（R11-3），并以 `expect_counts`
逐条对账上表；**不符即 `git reset` ＋ `git checkout -- orchestrator/state.json` 回滚、拒绝提交、HEAD 不动**。
本批 `ADD` 共 **10** 件（6 改 + 1 新 py + 1 新 md + 1 改 md），零删除（`numstat` 的 deleted 列见 §B1）。

## 10. 护栏如实上报（**两项仍未达标，禁降档改口径**）

| 护栏 | 目标 | 实测 | 判定 |
| --- | --- | --- | --- |
| ① `flash_share_tasks` | >= 0.60 | **0.5932** | **FAIL** |
| ② `flash_share_tokens` | <= 0.35 | **0.6655** | **FAIL（不可判）**：10 条已知 / 39 条 null-or-estimated，按 A183 估算值不入分母 |
| ③ `flash_share_dev_lanes` | 参考 | 0.4324 | 参考项 |

本批是**编排器自办**（`tier_used = orchestrator-self-served`，依 `accounting_rule_orch_self_served`
**不入** `budget.subtask_log`）⇒ 程序化重算（§F 同口径）三项比值**逐项不变**，
`subtask_log` 仍 49 条入算（总 50 条，其中 1 条为自办被排除）。
**如实登记**：护栏① 的回升**不依赖**本批，而依赖后续已排定的 flash 量产棒（M0-04 剩余 ＋ M2-01 S6/S7）
如实以 flash 档交付；依 **C10** 禁为凑配比发明 flash 工作、禁把 max 档改标为 flash。

## 11. 契约实测面（16 个 If-Match op 全清单）

`live_openapi_sha16` = `592571099d638251`（与台账逐字对撞一致，§D3）。全部 If-Match 形参的 schema
**逐字同构**：`type=string` / `minLength=3` / `maxLength=32` / `pattern` = `^"[1-9][0-9]*"$`。

| # | operationId · METHOD · path |
| --- | --- |
| 1 | `updateActivity PATCH /workspaces/{workspace_id}/activities/{activity_id}` |
| 2 | `updateRule PATCH /workspaces/{workspace_id}/rules/{rule_id}` |
| 3 | `confirmRule POST /workspaces/{workspace_id}/rules/{rule_id}/confirm` |
| 4 | `attachImportFile POST /workspaces/{workspace_id}/imports/{import_id}/files` |
| 5 | `configureImport PUT /workspaces/{workspace_id}/imports/{import_id}/mapping` |
| 6 | `validateImport POST /workspaces/{workspace_id}/imports/{import_id}/validate` |
| 7 | `publishImport POST /workspaces/{workspace_id}/imports/{import_id}/publish` |
| 8 | `updateCase PATCH /workspaces/{workspace_id}/cases/{case_id}` |
| 9 | `confirmCase POST /workspaces/{workspace_id}/cases/{case_id}/confirm` |
| 10 | `reviewPreflight POST /workspaces/{workspace_id}/preflights/{preflight_id}/review` |
| 11 | `signReport POST /workspaces/{workspace_id}/reports/{report_id}/sign` |
| 12 | `updateAction PATCH /workspaces/{workspace_id}/actions/{action_id}` |
| 13 | `transitionAction POST /workspaces/{workspace_id}/actions/{action_id}/transition` |
| 14 | `reviewAction POST /workspaces/{workspace_id}/actions/{action_id}/reviews` |
| 15 | `cancelJob POST /workspaces/{workspace_id}/jobs/{job_id}/cancel` |
| 16 | `retryJob POST /workspaces/{workspace_id}/jobs/{job_id}/retry` |

## 12. 收尾自检

- **悬空引用**（手册 §15.3）：本批 `10` 件入库面由 `h.dangling_refs(ADD)` 实扫，
  结果与 `allow_dangling` 登记面**集合相等**（多一条即判红）；实测结果见生成脚本输出与台账 `dangling_allowlist_note_R19_FU59`。
- **编码四判据**（PRE-39）：9 件（7 交付面 + 2 取证件）逐件过 (a) 严格 utf-8 解码 (b) 无 BOM/CR/NUL
  (c) 无 C0（`\n`/`\t` 除外）无 C1 (d) 尾换行，且 `file -bi` 含 `charset=utf-8`（§G1/G2）。
- **哨兵普查**（PRE-35）：入库前全量 walk 得 **3** 处（§F1，与 `commit_backfill_pending_R19_S5landBF`
  的 `sites_expected_after_mut` **逐字集合相等**）；本批同批兑现该 3 处，并登记本批自身 sha 的新哨兵。
- **台账 append-only**（D-011）：本件与 `orchestrator/defects/D-051.md` 的结案段均为**追加**，原文一字未改。
