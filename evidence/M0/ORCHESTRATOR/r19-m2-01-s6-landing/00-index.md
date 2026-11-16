# R19 · M2-01 / S6 入库取证件索引（编排器自办）

> 本目录是**编排器**为 lane `S6`（任务 `M2-01`，昵称 **Beauvoir**）回传件做**独立复验**与
> **入库**所留下的证据面。依 PRE-29，一切读数由编排器**自己实测**，lane 自报值仅用于**对撞**。

## 1. 批次身份

| 项 | 值 |
| --- | --- |
| 轮次 / 波 | Round 19 / wave 3 |
| lane / task / subtask | `S6` / `M2-01` / S6（design §11.7：HTTP 与契约层用例面） |
| 昵称 / agent_id | **Beauvoir** / `01a1e5f2-19a3-73d3-ba36-5dcbcdb4bb91` |
| 档位（裁定 = 实用） | `qwen3.8-flash` / reasoning `medium` / 预算 7k / loop_cap 2（**未降档未升档**，C10） |
| 派单文 | `orchestrator/handoff/R19-lane-M2-01-S6.md`（463 行 / 35841 B / `93a62069914e`） |
| predispatch 提交 | `be2b50b`（tag `R19-predispatch-wave3-S1-S6`） |
| spawn 回填提交 | `aa3d02b`（tag `R19-backfill-wave3pd-spawn`） |
| 入库批 tag | `R19-landS6`（本目录随该批入库） |
| 入库前 HEAD | `aa3d02be675d0993c4097f0576398c0565c96912` |
| 关键路径 | `critical=false`、`slack=4`（台账实测） |

## 2. 交付面（7 件，**全部新建**，编排器一字未改）

写权面：`tests/api/activities/**`；硬禁面 `tests/api/activities/__init__.py`（A272）**零触碰**。

| 文件 | 行数 | 字节 | sha256[:12] | 具名用例 |
| --- | --- | --- | --- | --- |
| `tests/api/activities/conftest.py` | 365 | 14029 | `ce3c39e555c5` | —（fixture 面） |
| `tests/api/activities/test_etag.py` | 293 | 12847 | `47474347ed57` | 13 |
| `tests/api/activities/test_conflicts.py` | 317 | 12629 | `0ce9e9d36074` | 10 |
| `tests/api/activities/test_rule_diff.py` | 143 | 6334 | `703e06aeed13` | 4 |
| `tests/api/activities/test_bindings_api.py` | 164 | 6737 | `2aaf4d7df5a3` | 5 |
| `tests/api/activities/test_list_filters.py` | 192 | 9109 | `d19cd794eaf1` | 8 |
| `tests/api/activities/test_contract_declarations_m2.py` | 81 | 3969 | `1b78851294f8` | 3 |
| **合计** | **1555** | **65154** | — | **43** |

上表 face 由编排器**实测**，与 lane 回执 `FACES` 段**逐项相同**（对撞通过）。

## 3. 独立复验结论：**GREEN**

复验脚本 `.orch_tmp/orch_v6s2.py`（只读、零副作用），逐字输出见
[`gates/V-independent-reverify.log`](gates/V-independent-reverify.log)。判据面：

1. **①交付件实存 + face 对撞**（7/7，与自报逐项相同）；
2. **②编码四判据**（严格 utf-8 / 无 BOM·CR·NUL / 无 C0·C1 / 尾换行）全过；
3. **③越界面**：未跟踪件只落在本棒写权面与已登记在飞豁免件（`orchestrator/handoff/M1-01-design.md`，属 lane `S1`）上；**零修改既有文件**（`git diff --numstat` 空 ⇒ deleted 列全 0）；A144(c) 归属分类**越界件 = 0**；
4. **④PRE-40 冻结面 8 件** sha256[:12] 逐字未变（含 A272 硬禁面 `tests/api/activities/__init__.py` = `8ccc54fe0ab9`）；
5. **⑤用例名**：AST 实取 **43** 名，与派单文 §6.1 具名清单**逐字集合相等**（`only_in_code=[]`、`only_in_brief=[]`）；跨 6 文件无重名；A273 三条 428 具名函数、A274 两条 FU-54 具名函数**全部实存**；
6. **⑥门（编排器自跑）**：`ruff format --check` rc=0、`ruff check` rc=0 `All checks passed!`、`mypy` rc=0（工作树 130 / 隔离在飞 7 件后 **123** == 台账值）、`pytest -q tests/api/activities` **47 passed**、`pytest -q tests/domain/activity` **48 passed**（未回归）、`--collect-only` **852 collected**、`check_contracts.py check --validate` **CONTRACT CHECK PASS**（登记项 13 / 实测差异 13 / 元校验 6）。

## 4. counts 口径与迁移（R11-3 恒等式，程序化派生）

`ruff_formatted_files` 的权威口径是**冻结索引树上的 in-scope（`*.py` + `*.md`）件数**
（`orch_harness.RUFF_SUFFIXES`）。工作树报数与台账值之间恒差「未跟踪 in-scope 件数」：

```
复验时点：台账 345（125 py + 220 md） + 未跟踪 8（本棒 7 py + lane S1 的 1 md） = 工作树实测 353 ✓
入库后  ：132 py + 222 md = 354（本批 ADD 含 7 py + 2 md 取证件；.log 与 state.json 不入 in-scope 分母）
```

| 键 | 入库前（`aa3d02b`） | 入库后（本批） | 增量归因 |
| --- | --- | --- | --- |
| `ruff_formatted_files` | 345 | **354** | +7 py（lane）+2 md（取证件） |
| `mypy_source_files` | 123 | **130** | +7 py |
| `pytest_passed` | 809 | **852** | +43 具名用例 |
| `in_scope_py` | 125 | **132** | +7 |
| `in_scope_md` | 220 | **222** | +2 |

## 5. 编排器自纠（同批登记，如实上报）

本批复验过程中发现**两处编排器自身判据失真**，均属判据面、**零交付面损坏、零 lane 责任**：

* **R19-15** —— v1 复验脚本 `orch_v6s.py` 用正则 `test_[a-z0-9_]+` 从派单文 §6.1 抽取具名清单时，
  把 7 个**文件名主干**（`test_etag.py` → `test_etag` 等）一并抽入，使期望集变成 50 名而与 AST 实取
  43 名不等 ⇒ **假 RED**（判据 ⑤c）。v1 输出原文：`only_in_brief=['test_bindings_api', 'test_conflicts',
  'test_contract_declarations', 'test_contract_declarations_m2', 'test_etag', 'test_list_filters',
  'test_rule_diff']`、`only_in_code=[]`。修正：抽名前先剔除 `\btest_[a-z0-9_]+\.py\b` token；
  修正后 `n_brief == n_ast == 43`、集合相等。
* **R19-16** —— v1 把台账 `ruff_formatted_files`（**冻结索引树**口径）直接当成**工作树**报数的期望值，
  忽略了同一工作树里 lane `S1` 的在飞未跟踪件 ⇒ 期望 352、实测 353 的**假 RED**（判据 ⑥a）。
  修正：按 R11-3 恒等式**程序化派生**两个口径的期望值（工作树 = 台账值 + 未跟踪 in-scope 件数；
  冻结树 = 入库后 tracked py+md），禁写死数字（PRE-37 第 1 款）。

两者是 R19-12 / R19-13 / R19-14 同族（**判据期望值凭记忆或口径混用**）的第 4、5 次复发 ⇒
prevention 由文字规劝升级为**硬规则**，机器化归口 FU-62；并同批立 **PRE-42**（见 §7）。

## 6. lane 自报与编排器实测的差异（如实登记，不粉饰）

* **loop**：lane 自报实耗 **2/2** 轮（第 1 轮开发+门+PC 主体；第 2 轮 PC-D 补牙+收工复测+回执）⇒ 未超帽。
* **token**：lane 报「单轮最大上下文 ≈ 15 万 tokens 级、累计 ≈ 40 万 tokens 级，对 7k 预算**大幅超支**，
  `over_cap=true`」，且明确说明是**估算口径**（本环境不暴露计数句柄）⇒ 依 **A183** 台账记
  `tokens=null` + `tokens_estimated=true`，**不入** flash_share_tokens 分母；超支事实如实登记。
* **U 项**：lane 报 `U | NONE` ⇒ 本批**零新裁定**（`A277` 不动）。
* **正向对照 PC-A…PC-E**：lane 自报全 PASS 且 sha 双向复原；**偏差如实报** 3 处（PC 注①②③：
  未用 tmp_path 切片副本而用工作树就地变异+内存复原+sha 双向核验+收工零残留；PC-C 改以变异派生集证明；
  PC-D 按 PRE-33 意图改为三组独立值变异）。编排器接受其**等效证据**，理由：断言牙口由「变异→rc=1 红→
  原文复原→sha 双向核验→收工 `git status`/`git diff` 零残留」四段闭合，且编排器复验时工作树 face 与
  自报逐项相同 ⇒ 无残留污染。
* **在飞污染观察**：lane 报会话中段曾见 `?? orchestrator/handoff/M1-01-design.md`（当时 68557 B，
  为 `M0-04-design.md` 的字节拷贝）短暂出现后消退。编排器复核：该 `=` 前缀越界垃圾件已在
  `aa3d02b` 之后由编排器 `rm` 清除（零信息损失，sha 与被拷贝件相同）；复验时点该路径为 lane `S1`
  的**真交付件**（1301 行 / 159632 B / `99dd191f43b3`），已按 A144(c) 归属到 `S1`、非越界。

## 7. 同批立规 PRE-42（越界垃圾件防治，4 款）

由 §6 末条 incident 触发，全文见台账 `resume.preconditions_added_R19_S6land`：
① 禁在 `bash -lc` 载荷里使用半角双引号；② 禁把 `>` `<` `|` `&` 当表达式字面量写进载荷；
③ landing 批必须扫越界件并**同批**清理（面包屑留痕）；④ 派单文生成器必须附**可执行替代范式**。
机器化归口 **FU-58**。

## 8. 本目录文件清单

| 文件 | 说明 |
| --- | --- |
| `00-index.md` | 本件（索引 + 复验结论 + 口径 + 自纠） |
| `lane-receipt-S6-raw.md` | lane `S6` 回传的**原始回执**逐字归档（未改写，仅补尾换行） |
| `gates/V-independent-reverify.log` | 编排器独立复验脚本 `orch_v6s2.py` 的逐字输出（结论 GREEN） |

## 9. 后续义务（本批**不**做，避免越权判定）

* **禁判 `M2-01` DONE**：AC-002 / AC-003 / AC-004 的判定在 **S7**（`evidence/M2/**`）批；
  本批只把 `tasks['M2-01'].subtask_progress.S6` 置 DONE。
* S7 派单前必须按 **A269** 用**本批入库后的最新 counts** 重给权威读数（禁沿用旧值），并复测 PRE-40 冻结面。
