# lane S3（M2-01/S3）原始回执归档 —— 逐字留档（R18-6 的补齐动作 · FU-61 的人工纪律先行）

> **归档口径（如实登记，禁粉饰）**：本件是编排器**实际收到**的 lane 回执原文。Round 18 编排器**未在回收当刻落盘**
> 原始回执（违反 R12 / R13 的既有先例）⇒ 立自纠 **R18-6** ＋ **FU-61**（机器化 `archive_lane_return`）。
> 编排器上下文在 R18 中途经历一次**跨模型交接**，且两次 `wait_agent` 回传均发生**传输截断**，故本件由两段拼合：
>
> - **§1**＝首次回传中**未被截断**的尾段（PC-3 / PC-4 / U_ITEMS / SELF_REPORTED_DEVIATIONS 8 条 / TIER_CONFIRM），逐字；
> - **§2**＝编排器发出「只重发原文、禁任何文件操作与命令」窄请求后，lane **重发**的头部区块
>   （RESULT / LOOP_USED / BASE_SHA / FILES_* / V1–V11 / EXPECTED_RED_TEXT / PC_RESULTS / U_ITEMS / TIER_CONFIRM），逐字。
>
> **不可复原部分（明示，禁凭记忆重构）**：
> ① 首次回传的**头部**（RESULT…PC-2 段）被截断 `…3125 tokens truncated…`，已由 §2 的重发覆盖；
> ② §2 重发里 **PC-1(b) / PC-2** 段自身又遇截断 `…191 tokens truncated…`，该两段的完整红原文**已不可复原**；
> ③ lane **未报** token 用量（§2 明载「未报（上一条回执未含该字段）」）⇒ 台账 `tokens=null`、
> `tokens_estimated=true`，**无自报区间可引**（与 R17-S5 的「自报 150k–220k」不同，本棒连区间都没有）。
>
> 编排器对 lane 自报的一切**均不采信**：交付面读数（行 / 字节 / sha256 / rc / collected）全部由编排器独立实测，
> 见同目录 `00-index.md` 与 `commands-and-outputs.log`。本件仅作**留痕**与**成本可观测性**用途（D-011 append-only）。

- **lane**：S3 · **task**：M2-01 · **round**：18
- **agent_id**：`01a1dff3-0aed-7620-a0f8-6b3e08af0d77` · **昵称**：Nash
- **档位**：`qwen3.8-flash` / `medium`（lane `TIER_CONFIRM` 与派单档位一致，未升降档 ⇒ `tier_match=true`）
- **派单文**：`orchestrator/handoff/R18-lane-M2-01-S3.md`（299 行 / 28576 B / sha256[:12]=`67acfc97305e`）
- **归档时点**：见 `00-index.md` 的取证时点（编排器实测时钟）

---

## §1 首次回传的未截断尾段（逐字）

```text
T …/activities→**404**（未挂载），变异态同请求→进入路由、死于 deps.py:343 `require_session`→`RuntimeError: app.state.session_service 未装配`（500 面）——行为差异真实存在，只是无哨兵咬合 ⇒ **报 U-2**。复原 sha=76fcb0778f64＝落地态、numstat 回到 3/0。
**PC-4**（`uv run --no-sync pytest -q tests/api/activities`＋自建 428 断言）：`if_match` 改契约字面必填（`str`＋无 `default=None`）。生效证明：AST 注解==`str` True＋红原文自证（422 形态）。结果 **rc=1，1 failed, 3 passed**（归因干净——只有 428 断言红），红原文：

>       assert missing.status_code == 428, missing.text
E       AssertionError: {"type":"urn:campaignlab:problem:validation_error",...,"status":422,...,"issues":[{"code":"VALIDATION_ERROR","location":"/header/If-Match","message":"Field required",...}]}
E       assert 422 == 428   （test_activities_router_s3.py:197）

复原 sha=887bd377a4f7＝落地态；复原后 V1 复跑 rc=0。

U_ITEMS:
- **U-1**｜现象：派单文 §3.2/§5 与 design §1.4/§6.2 点名 `IF_MATCH_PATTERN`（「不在 `api/common.py::__all__` 但确实从 api.common 导入可用」），但实测该符号**全仓不存在**（受限 grep：`src/campaignlab`、`tests/unit`、`tests/api` 三面对 `IF_MATCH_PATTERN` 0 命中；`api/common.py:1168 行/45605 B/sha 836e7b3e8d3a` 的 defs 清单无此常量；`domain/ids.py`、`api/session.py`、`api/deps.py` 亦无）。实测到的事实：`check_if_match@common.py:825` 存在可用；冻结先例 `api/jobs.py::cancel_job`（sha 735d30baf0c4）的 If-Match 形参形态＝`Header(alias="If-Match", default=None, min_length=3, max_length=32, pattern=r'^"[1-9][0-9]*"$')` 内联字面量；design §6.2 同时冻结 pattern 值逐字＝契约 `operations.updateActivity…pattern`。候选处置：①维持 jobs.py 先例的内联字面量（本棒现状）；②由有权 lane 在 `api/common.py` 追加 `IF_MATCH_PATTERN` 常量后路由改 import（触及冻结面，非本棒权限）。倾向①，理由：零设计裁量（字面量值与参数形态是逐字照抄既有冻结先例，非新裁），且 pattern 值单源＝契约，不构成第二真源。本棒已按①交付并在此如实报裁，未动②。
- **U-2**｜现象：§7 PC-3 条款命中的「无牙」真缺陷。命令原文：`uv run --no-sync pytest -q tests/unit/test_s2b2_app_injection.py tests/unit/test_api_app.py`（变异态）。实测到的事实：把 `app.py:173-174` 条件挂载改成无条件后，**没有任何既有守护因该变异本身判红**（唯一红＝E2 既有；`test_api_app.py::test_jobs_router_is_not_mounted_by_s3c` 型裸装配 404 探针只覆盖 jobs，不覆盖 activities）；行为差异真实存在（落地裸装配 404 vs 变异态 500/RuntimeError，file:line 见 PC-3 原文）。候选处置：①由 S7/编排器增设 activities 的裸装配 404 守护（照 jobs 先例同形）；②编排器在本批 E1 同批迁移时把 conditional pair `"    if activity_service is not None:\n        app.include_router(activities_router)"` 追加进 `pairs` 四元组（E1 的 pairs 机制已实测对「改成无条件挂载」形态有牙）。倾向②，理由：迁移面已在编排器写权内、零新文件，且 pairs 形态判据经 M0-04/S4 先例验证四形态均判红。均未自行落地。

SELF_REPORTED_DEVIATIONS:
1. `IF_MATCH_PATTERN` 不存在（U-1），`if_match` 形参按 jobs.py 冻结先例的内联 pattern 落地。
2. §3.2「三个助手全部来自 api/common.py」与实测 import 先例不符：`parse_json_body` 实定义在 `api/session.py:89`，本棒逐字照 `workspaces.py:43-47` 先例从 `campaignlab.api.session` 导入（`declared_responses`/`JSON_MEDIA_TYPE` 同源）；`request_id_of`/`replay_from_envelope`/`validate_idempotency_key`/`read_body_within_limit` 确从 `api/common.py`。
3. `svc.create_activity(...)` 实测关键字比 §3.3 示例多一个前置 `workspace_id`（实测依据：`api/deps.py:166-174` 与 `application/activity_service.py:783-790`），按 §3.3「真实关键字名以实测签名为准」落地。
4. `check_if_match` 调用点二选一取 **service 侧**（实测 `update_activity` 签名已收 `if_match`，`api/deps.py:182-191`）；路由层未调、信封与 Problem 组装无第二真源。
5. 私有助手把 `request_id` 用于 `X-Request-Id` 响应头装配（照 `replay_from_envelope@common.py:951` 的既有头部口径，非新造 id；最外层 `request_id_middleware@common.py:1076-1086` 以同值覆写，两态行为逐字一致）。此为 design §11.4 冻结签名（含 `request_id` 形参）与 §1「中间件统一给出」两处原文之间取的调和位。
6. 测试件 `test_update_activity_etag412_stale_and_missing_if_match_428` 的函数名含 `etag412` 子串，动机＝design §6.2 提到的任务卡 gate `pytest -q tests/api/activities -k etag412`（派单 §4 V1 未点名词表，此命名令该 gate 非空可跑）；PC-1b 用 `-k identity` 时命中 2 条（`test_create_activity_envelope_201_etag_and_identity` 名内亦含 identity），红样本条已如实标注。
7. 过程事故（已闭环、最终态无偏差）：app.py 首次补丁脚本笔误吃掉 `return app`（numstat 一度 4/1），在任何判据度量之前已修复为 3/0；首次 deploy 因 WSL 非登录 PATH 缺 uv 半途而废（无副作用）。过程草稿放于仓库外（Windows scratch `.s3tmp` 与 `~/s3_backup`），未新建任何 `evidence/**`，未 add/commit/push，未触碰 S6 文件。
8. §5「行数」全部比 `wc -l` 多 1（newline+1 计数口径）；sha＋字节逐字全等，按文首指示核对过 `resume.baseline_authoritative.current`（head=bc8a52d、counts 305/107/734，与实测一致），不构成不符。

TIER_CONFIRM: model=qwen3.8-flash, reasoning=medium
```

---

## §2 lane 重发的头部区块（逐字；编排器窄请求「只重发原文、禁任何文件操作与命令」）

```text
RESULT: DONE_WITH_GAP
（注：4 件写权面交付齐全、V1–V11 全部达标；“GAP”仅指 2 条待编排器终裁的 U 项，非交付缺口。）

LOOP_USED: 1/2
（1 个实现-验证轮：轮内含两处小修正——5 行超长（E501）与 1 处 mypy comparison-overlap——均在同轮闭环；PC 电池与判据复测不另计轮。）

BASE_SHA: bc8a52dc3b263a53a02bfb13956f9b6e3f13abd0
（§5 冻结面 13 件首测：sha256[:12] 与字节数全部逐字相符（行数差 1＝派单 newline+1 计数口径 vs wc -l，非实质不符）；收尾复测 12 件（除 app.py）FROZEN_MISMATCH: NONE。工作区上工即干净；S6 的 test_lease.py / test_artifact.py 全程未跟踪在场，未碰。轮中 HEAD 移至 c94eff9（纯台账件 orchestrator/state.json 40/30），V4/V11 已对新 HEAD 复测无变化。）

FILES_NEW:
  src/campaignlab/api/activities.py                     221 行 /  9955 B / 887bd377a4f7
  tests/api/activities/__init__.py                        1 行 /    89 B / 8ccc54fe0ab9
  tests/api/activities/test_activities_router_s3.py     221 行 /  8872 B / e4d1d145cca5
FILES_MODIFIED:
  src/campaignlab/api/app.py  numstat 3	0（git diff --numstat HEAD）
  175 行 / 7726 B / 落地态 sha=76fcb0778f64（基线 f039722660bb）
  新增恰 3 行：:28 from campaignlab.api.activities import router as activities_router（字母序位在 from campaignlab.api.common import ( 之前）＋ :173     if activity_service is not None: ＋ :174         app.include_router(activities_router)（位于 jobs 条件挂载之后、return app 之前）；无注释行。

V1_new_guards: rc=0, collected=4
V2_full_pytest: rc=1, failed=2, failed_ids=
  tests/unit/test_s3b_routes.py::test_app_py_contains_only_the_a85_mount_lines            ＝E1
  tests/unit/test_s2b2_app_injection.py::test_g6_mount_and_middleware_surface_unchanged    ＝E2
  （passed=745 / collected=747；745＝基线 734＋本棒 4＋邻居 S6 未跟踪新文件的 9 条，运行当时 S6 条目全绿。运行于落地态字节上；PC 变异均已字节级复原后 sha 复核，落地态与本测一一对应。）
V3_quality: ruff_check rc=0（All checks passed!）, ruff_format rc=0（310 files already formatted）, mypy rc=0（Success: no issues found in 112 source files；107 基线＋本棒 3＋邻居 2）
V4_appy_numstat: 3	0
V5_include_router_count: 5（AST 实取＝[health.router, session_router, workspaces_router, jobs_router, activities_router]；activities_router 恰 1，既有 4 个逐字未变）
V6_symbol_face: public=5（{create_activity, get_activity, list_activities, router, update_activity}）, private=2（{_activity_page_response, _activity_response}）, __all__=5 且字母序 True
V7_operation_ids: listActivities/getActivity=declared_responses(200)、createActivity=declared_responses(201)、updateActivity=declared_responses(200)（AST 逐字实取，四装饰器顺序＝list/create/get/update）
V8_redline_hits: 0（grep -c 输出 0、rc=1；SELECT/INSERT/"UPDATE "/datetime.now/utcnow/time.sleep 全零，含注释与 docstring）
V9_is_identity:
  取注入对象本身的路径＝桩方法体在 DI 解析到的 self 上自捕获：
    test_activities_router_s3.py:87  _RESOLVED.append(self)（stub.list_activities 内，:77 def）
    test_activities_router_s3.py:161 provider_calls = [sub.call for sub in route.dependant.dependencies] → assert deps.get_activity_service in provider_calls
    test_activities_router_s3.py:166 断言原文：assert _RESOLVED[-1] is injected
  提供器侧：deps.py:316-324 get_activity_service → _state_service(request, "activity_service", ActivityService)（deps.py:286-298 读 app.state）；注入点 app.py:145-146。
  走的是真实路由 GET /api/v1/workspaces/{workspace_id}/activities，TestClient＋真实会话（exchange 换 Cookie）。进程内 is，未用任何序列化/HTTP 字段替代（PC-1 双变异即沿此线取证）。
V10_no_regression: app_state_keys=8（config/clock/guard/session_service/health_service/workspace_service/activity_service/rule_service）, middleware_order=不变（:152 BaseHTTPMiddleware(guard) → :153 CORSMiddleware → :161 install_error_handlers＝request_id 最外）, openapi_urls=None×3, allowed=ALLOWED_METHODS 7 项/ALLOWED_HEADERS 5 项逐字未变, kwonly=7 有序 [clock, guard, session_service, health_service, workspace_service, activity_service, rule_service]
V11_numstat_frozen: 空（git diff --numstat HEAD -- src tests 排除 3 个写权面后无输出；对新 HEAD c94eff9 复测仍空）

EXPECTED_RED_TEXT:
E1（tests/unit/test_s3b_routes.py:207）：
>       assert len(mounted_lines) == 4
E       AssertionError: assert 5 == 4
E        +  where 5 = len(['    app.include_router(health.router)', '        app.include_router(session_router)', '        app.include_router(workspaces_router)', '        app.include_router(jobs_router)', '        app.include_router(activities_router)'])
E2（tests/unit/test_s2b2_app_injection.py:268）：
>       assert ordered == EXPECTED_MOUNT_LINES
E       AssertionError: assert ['app.include...ties_router)'] == ['app.include...jobs_router)']
E         Left contains one more item: 'app.include_router(activities_router)'
注（如实）：E2 的第二触发面 :274 assert not banned_hits（import campaignlab.api.activities 解禁面）因 :268 先行判红而本轮运行时未获求值机会；两件均未改。

PC_RESULTS:
PC-1（判据 uv run --no-sync pytest -q tests/api/activities）
- (a) is→字段相等：变异落地态 :166 行改为 assert response.json()["items"][0]["id"] == _ACTIVITY_ID。生效证明（AST/文本实取）：文件不再含 is injected＝True。结果 rc=0，4 passed（仍绿）⇒ 证明字段相等弱于身份判据、原 is 断言不可被替代。复原 sha e4d1d145cca5。
- (b) 主体变异：注入对象换成同类…【传输截断 …191 tokens truncated… 不可复原】
PC-3（uv run --no-sync pytest -q tests/unit/test_s2b2_app_injection.py tests/unit/test_api_app.py）：删 if 改无条件挂载。生效证明：AST 判定 include 调用不在任何 If 体内＝True；变异态 numstat 2/0、sha 6d50dbbf9299。结果 rc=1，但唯一 FAILED＝test_g6（E2 既有预期红），14 passed 全绿 ⇒ 该变异自身无既有守护可归因判红。按 §7 该行指示补替代对照并如实入档：裸装配（guard 放行配置）下落地态 GET …/activities→404（未挂载），变异态同请求→进入路由、死于 deps.py:343 require_session→RuntimeError: app.state.session_service 未装配（500 面）——行为差异真实存在，只是无哨兵咬合 ⇒ 报 U-2。复原 sha=76fcb0778f64＝落地态、numstat 回到 3/0。
PC-4（uv run --no-sync pytest -q tests/api/activities＋自建 428 断言）：if_match 改契约字面必填（str＋无 default=None）。生效证明：AST 注解==str True＋红原文自证（422 形态）。结果 rc=1，1 failed, 3 passed（归因干净——只有 428 断言红），红原文：
>       assert missing.status_code == 428, missing.text
E       AssertionError: {"type":"urn:campaignlab:problem:validation_error",...,"status":422,...,"issues":[{"code":"VALIDATION_ERROR","location":"/header/If-Match","message":"Field required",...}]}
E       assert 422 == 428   （test_activities_router_s3.py:197）
复原 sha=887bd377a4f7＝落地态；复原后 V1 复跑 rc=0。

U_ITEMS:
- U-1｜IF_MATCH_PATTERN 全仓不存在（受限 grep 三面 0 命中；common.py 1168 行/45605 B/836e7b3e8d3a defs 清单无此常量）；jobs.py::cancel_job 内联字面量先例在位。候选①维持内联字面量（本棒现状）／②有权 lane 追加常量后改 import。倾向①。（已终裁 A247：采纳①，零返工。）
- U-2｜PC-3 命中「无牙」真缺陷：无条件挂载变异仅 E2 既有红、无既有守护可归因；行为差异 404 vs 500/RuntimeError 实测在案。候选①增设 activities 裸装配 404 守护／②编排器 E1 迁移时把 conditional pair 追加进 pairs。倾向②。（已终裁 A248：采纳②，PC-U2 实证有牙。）

SELF_REPORTED_DEVIATIONS:（8 条，原文见上一条回执，经 A249 逐条核过全部 PASS，此处不重发）

COVERAGE_MAP_*:（本段无内容）

token 用量自报：未报（上一条回执未含该字段）。

TIER_CONFIRM: model=qwen3.8-flash, reasoning=medium

residual / 未尽面:（本段无内容——回执当时未单列此段；U-1/U-2 已终裁闭环，写权面无未尽事项。）
```

---

## §3 编排器对自报值的独立复核结论（禁采信自报）

| lane 自报 | 编排器实测 | 判定 |
|---|---|---|
| `activities.py` 221 行 / 9955 B / `887bd377a4f7` | **222** 行 / 9955 B / `887bd377a4f7` | 字节与 sha **逐字相符**；行数差 1 ＝ lane 的 `wc -l` 口径 vs 编排器 `len(text.split("\n"))` 口径（lane 自报偏差 #8 已明示该口径差）⇒ 非实质不符 |
| `app.py` 175 行 / 7726 B / `76fcb0778f64`、numstat `3/0` | **176** 行 / 7726 B / `76fcb0778f64`、numstat `3/0` | 同上口径差；numstat **逐字相符** |
| `__init__.py` 1 行 / 89 B / `8ccc54fe0ab9` | **2** 行 / 89 B / `8ccc54fe0ab9` | 同上 |
| `test_activities_router_s3.py` 221 行 / 8872 B / `e4d1d145cca5` | **222** 行 / 8872 B / `e4d1d145cca5` | 同上 |
| V1 `rc=0, collected=4` | `rc=0`、`4 passed`（§D 实跑） | 相符 |
| V3 `ruff_format 310 files` / `mypy 112 source files` | 工作树 `311 files` / `112 source files` | **310 vs 311 差 1**：lane 测于其落地时点（D-051.md 尚未由编排器新建）；编排器复测时 D-051.md 已在磁盘 ⇒ 分母 +1。属**时点差**，非造假。冻结树权威值以 `run_commit` 的 `expect_counts` 对账为准 |
| V5 `include_router` 恰 5、`activities_router` 恰 1 | AST 实取 5、恰 1 | 相符 |
| V6 public 5 / private 2 / `__all__` 5 字母序 | AST 实取全等 | 相符 |
| V9 `:166 assert _RESOLVED[-1] is injected` | 同行同文（进程内对象身份，非响应体代理） | 相符 |
| V10 `app.state` 8 键 / 中间件顺序不变 / `openapi=docs=redoc=None` / kwonly 7 名有序 | AST 实取全等 | 相符 |
| PC-3 变异态 sha `6d50dbbf9299` | 编排器自办 **PC-U2** 独立变异 ⇒ sha **`6d50dbbf9299`** | **逐字相同**（两次独立变异得到同一 sha ⇒ 强交叉验证，非采信） |
| 预期红 E1 `:207` / E2 `:268` | 编排器同批迁移后 E1+E2 **16 passed rc=0**；PC-U2 变异态下 E1 判红于 **`:212`** | E1/E2 均由**编排器**迁移（A245：两件不在 M2-01 的 `scope_allow`，lane 禁改），lane 报的红是**迁移前**的合法预期红 |

**结论**：lane 自报与编排器实测在**一切字节面与判据面逐字相符**，两处差值（行数口径、ruff 分母时点）均已定位到**口径/时点**成因，非交付面缺陷 ⇒ **A249 判 8 条自报偏差全部 PASS**。

`RESULT: DONE_WITH_GAP` 的 GAP ＝ 2 条待终裁的 U 项（U-1 / U-2），已由 **A247 / A248** 同批闭合（U-1 采纳候选①零返工；U-2 采纳候选②并由 PC-U2 实证有牙）⇒ 编排器终裁 **PASS**。
