# M2-01/S4 lane 回执**摘要**（昵称 Wegener · `qwen3.8-flash`/medium · loop_cap 2）

> **本文件是摘要，不是原始回执全文。** 成因＝**FU-61 仍 OPEN**：当前运行环境未提供
> 「把 lane 原始回执字节级落盘归档」的机器化句柄（`archive_lane_return`），编排器只能手工转录。
> 依 A183 如实标注，**禁**把摘要冒充原文。原始回执共 10 段（§1–§10），本摘要保留其**全部实测数字**
> 与 **U-1…U-5 的裁定载荷**，省略叙述性行文。

## 1. lane 自报结论

`DONE_WITH_GAP` —— 交付面 100%（`rules.py` 新建 ＋ `app.py` 挂载 5→6，V1–V6 全 rc=0，
V7 红集**恰为** E1/E2）；GAP 全在**派单文自身的取证面**（V8 点名路径不存在、PC-1/PC-4 部分判据无牙）。

## 2. lane 自报 face（编排器已独立复验，**逐字一致**）

```text
src/campaignlab/api/rules.py 389L 17913B c7b3cccee6ec     ← 新建
src/campaignlab/api/app.py   178L  7857B 2e4aad126172     ← 原 175L/7726B/76fcb0778f64
tail -c 1 rules.py | od -c   -> 0000000  \n                ← 尾换行在场
git diff --numstat -- app.py -> 3  0                      ← added=3 ≤3、deleted=0
grep -i -E "SELECT |INSERT |UPDATE |DELETE |sqlite3|execute" rules.py -> rc=1（零命中）
```

冻结面零漂移复测（与派单文 §0 逐字吻合）：`app.py 175L/7726B/76fcb0778f64` ·
`activities.py 221L/9955B/887bd377a4f7` · `common.py 1168L/45605B/836e7b3e8d3a` ·
`deps.py 346L/13524B/ed1075a86447` · `design 1396L/2d39feaac2d1`。

## 3. lane 自报门读数

| 门 | rc | 关键输出 |
|---|---|---|
| V1 形态 | 0 | 11 个函数 = 7 公开 handler ＋ 恰 4 私助手 |
| V2 符号面 | 0 | `prefix /api/v1`、`tags ['rules']`、`__all__` 8 项、私面 4 项、7 op |
| V3a/V3b ruff | 0 / 0 | `2 files already formatted` / `All checks passed!` |
| V4 mypy strict | 0 | `Success: no issues found in 52 source files` |
| V5 numstat | 0 | `3  0  src/campaignlab/api/app.py` |
| V6 硬禁面 | 0 | 空输出 |
| V7 全量 pytest | **1** | `2 failed, 746 passed, 6 warnings in 155.62s`（红集＝E1/E2，复跑两次读数一致） |
| V8 as-given | **4** | `file or directory not found: tests/unit/test_contract_declarations.py` ⇒ **U-1** |
| V8 补测（活体路径） | 0 | `tests/api/test_contract_declarations.py` → `13 passed`，但对 rules 面 **0 引用** ⇒ 无判据力 |

lane 的 V8 补偿取证（自建判据，非仓内守护）：7 op 的路径/方法/2xx 与 `contracts/openapi.json`
切片逐一对撞 ⇒ `misses = NONE (7/7 match)`；严格签名桩实跑 7 条真实路由 ⇒
`ALL_KWARG_NAMES_MATCH = True`；逐 op 状态码/ETag 实测
`list 200 None · create 201 "1" · get 200 "1" · update 200 "2" · confirm 200 "2" · checks 200 None · diff 200 None`
（＝design §6.1 的逐 op 面）。

## 4. lane 的 4 组阳性对照（PC）自报结论

- **PC-1**（删 `if` ⇒ 无条件挂载）：标 **NO_TEETH** —— 现仓 `pairs` 只 4 项、无 rules 项，
  BASE 与 MUT 的 E1 判红点同为 `:220`。附**迁移形态学仿真**四套：
  `V0 as-committed → BASE RED@220 / MUT RED@220`；`V1 只改计数 → BASE GREEN / MUT GREEN`（**无牙陷阱**）；
  `V2 只追加 pairs → BASE RED@221 / MUT RED@213`；`V3 两处同改 → BASE GREEN / MUT RED@213`（**建议形态**）。
- **PC-2**（`If-Match` 改必填）：**有牙 PASS** —— 缺头由 `428 PRECONDITION_REQUIRED` 翻成
  `422 VALIDATION_ERROR`；并如实区分「外层 `p.default` 两形态都非 None，口径落在 FieldInfo 内层 `.default`」；
  三处正则字面对撞 `jobs.py` 2 命中 / `activities.py` 1 / `rules.py` 2，各文件 distinct 字面均 1 种。
- **PC-3**（去掉 `prefix=API_PREFIX`）：**部分有牙** —— lane 自建契约对撞判据下 7 条全失配（有牙）；
  但派单文点名的 `test_contract_declarations` 路径不存在、活体文件对 rules 0 引用 ⇒ 该门 **NO_TEETH**。
- **PC-4**（`createRule` 的 201 改 200）：**声明面有牙 / 运行期结构性 NO_TEETH** ——
  两种变异下运行期实测**仍是 201**（信封承载状态码 ＋ 处理器返回 `Response` ⇒ 装饰器 `status_code` 被短路）。

## 5. U 项（5 条，全部非阻塞；lane 未自行裁定）→ 编排器裁定见 00-index §5

| U | 冲突面 | lane 倾向 | 编排器裁定 |
|---|---|---|---|
| U-1 | V8/PC-3 点名的 `tests/unit/test_contract_declarations.py` 不存在 | (b) 入库批补 rules 段 | **A257**：改归 **S6**（依 N5 禁第二真源） |
| U-2 | PC-1 的前提「E1 的 pairs 失配」在现仓不成立 | (a) pairs＋计数两处同改 | **A258**：采纳 (a)（V3 形态） |
| U-3 | E2 的 `:280-281` 禁串 bite 本轮未执行到 | (a) 同批移除 `rules` | **A259**：采纳 (a) ＋ 判据**升级**为精确集合 |
| U-4 | PC-4 的运行期判据 | (a) 改声明面对撞 | **A260**：采纳 (a)，运行期判据登记为 NO_TEETH |
| U-5 | 「HEAD 应为 tag R18-predispatch-S4」但 `git tag -l` = 0 项 | (a) tag 仅名义锚点 | **A261**：采纳 (a)，此后一律以 **sha** 为锚 |

## 6. lane 自报的合规面（编排器已抽样复核）

- 越界自查：`git status --porcelain` **恰 2 项**（`M app.py` ＋ `?? rules.py`），无第三项；V6 空输出。
- git 写操作 **0 次**：全程只 `log/status/diff/rev-parse/tag/merge-base/show`；
  未 `add`/`commit`/`push`/`reset`/`checkout`，未用 `--no-verify`。
- 所有 PC/仿真变异落在 `tempfile.mkdtemp()`（`/tmp/s4pc_*`、`/tmp/s4mig_*`），仓内文件仅经 §1.2 的 3 行改动。
- 未放宽任何 lint/type 配置。
- **token 用量：未报** —— lane 实测「运行环境未暴露 token 计数接口」（`get_goal` 返回 `{"goal":null,…}`）
  ⇒ 依 A183 记 null，禁编造。**FU-61 因此保持 OPEN**。

## 7. lane 回执中的一处**继承性失真**（编排器更正，非 lane 过错）

lane §9 复述了 D-052 的 ①②：「仓内无 `BoundaryCaseDraft`／无 `input_payload`」。
编排器全仓对撞实测**推翻**了这两条（该 dataclass 在 `domain/activity/checks.py:171`，
字段含 `input_payload`）⇒ 见 **R18-11** 与 `orchestrator/defects/D-052.md` §9。
**lane 的行为面正确**（`_rule_check_response` 透传），失真来源是**派单文**，lane 无过错；
其 `rules.py:113-121` 的 docstring 前半句「pydantic 在 service 构造 `RuleCheck` 时即完成校验」
经实测**准确**（转换点＝`application/activity_service.py:1925` 的 `BoundaryCase.model_validate`），
故交付件**一字未改**（保留 face `c7b3cccee6ec` 的可审计性）。
