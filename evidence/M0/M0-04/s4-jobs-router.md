# M0-04/S4 · s4-jobs-router.md（交付说明 + U 项 + 硬禁面收尾复核）

## 1. 交付面（逐文件 added/deleted、行数、字节、sha256[:12]）

| 文件 | numstat | 行数 | 字节 | sha256[:12] | 说明 |
| --- | --- | --- | --- | --- | --- |
| src/campaignlab/api/jobs.py（新建） | 未跟踪→+371 | 371 | 16916 | 735d30baf0c4 | 公开面恰 router/list_jobs/get_job/cancel_job/retry_job；私有面恰 _job_page_response/_job_response（AST 守护钉死）；0 条 SQL；0 处墙钟字面量（含注释/docstring） |
| src/campaignlab/api/common.py | 15/0 | 1168 | 45605 | 836e7b3e8d3a | JobPage append-only（deleted=0；既有 78 项一字未动）；__all__ 78→79（运行期实测 79）；插入位为 RUF022 工具裁决位（JobCapacity 后），见 U-1 |
| src/campaignlab/api/app.py | 3/0 | 160（基线 157 实测 + 3） | 7253 | 110751903e4d | 1 行 import（别名体例 jobs_router，同 session/workspaces 两处既有体例）+ 2 行条件挂载（候选 (b) 形）；既有三处 include_router、openapi_url=None、中间件顺序、ALLOWED_HEADERS 未触碰 |
| tests/integration/jobs/test_jobs_router_s4.py（新建） | 未跟踪→+683 | 683 | 26515 | c3110b40b71d | 34 用例全绿；自带 fixture；**未建 conftest.py**（S5 写集） |
| tests/unit/test_domain_errors.py | 2/2 | 189 | 7771 | a933def6c4e5 | §4② 唯一授权：两处 78→79 数字字面量，函数名与 docstring 语义未碰 |
| orchestrator/handoff/M0-04-design.md | EOF 追加 | — | — | 前 256 行 sha12=5b76bcb33984（追加前后逐字节不变） | §9-S4 行落地注记 |
| evidence/M0/M0-04/{s4-jobs-router.md, commands-s4.md, positive-control-s4.log} | 新建 | — | — | — | 本三件套 |

义务对账（派单 §4 五条）：①A220 404 由路由侧产生（listJobs 前置工作区核验 + 挂载候选 (b)）✓；②A91 JobPage append-only + 78→79 预裁 ✓；③A169③ 编解码/query_digest 归路由、绑定校验未重复实现、CURSOR_VERSION 未第二写、BAD_CURSOR detail 复用同句（PC5 钉）✓；④A10/A217 挂载 3/0 行、未为 M2-01 加任何形参/router ✓；⑤PRE-7 第 0 步先复测后写码 ✓（见 commands-s4.md）。

落地口径两则（如实）：
- 幂等信封的落库 envelope_json 与响应回放共用**声明序** ``json.dumps``（非 canonical 排序），使 AC-029①「两次响应含头逐字节相同」在 jobs 面真达成；M0-02 createWorkspace 同类问题的既有 U-2 注记（键序漂移）未在 jobs 面复制。重放语义、request_digest、信封形状（status/headers/body）与 M0-02 落地面逐字兼容。
- cancel/retry 的 ``now`` 由 ``clock: Clock = Depends(get_clock)`` 注入（D-045 条规定的唯一取时形态），该形参在 design §1 的 op 签名清单之外——派单 §3/§5 明文要求此注入，视为授权扩形，NOTES 留痕。

## 2. U 项（只报不裁；每条：事实 + 两候选 + 倾向 + 理由 + 影响面）

**U-1（__all__ 追加位）** 事实：RUF022 在 ruff 配置生效（HEAD 树上 __all__ 全表有序，实测违规报红），派单 §2.2「只在末尾追加」的字面与 `ruff check` rc=0 互斥（末置 JobPage ⇒ rc=1）。候选：(a) 末置 + ruff 判红；(b) 插入 isort 口径位（JobCapacity 之后，既有 78 项一字未动、numstat 仍 15/0）。**倾向并已按 (b) 落地**——理由：四门 rc=0 是台账权威基线、优先级高于位置字面；硬约束（不删不改不重排既有项、78→79）全部保持。影响面：仅该行的位置；FU-48 语义升级时可一并追认。

**U-2（两条既有前提哨兵被 S4 落地必然打红）** 事实：全表 pytest 647 passed / 2 failed；`test_contract_declarations.py::test_404_and_429_branches_are_unreachable_for_the_five_ops` 钉「jobs.py 不存在 + 挂载路径集恰 4」（docstring 自引 A84/A85），`test_s3b_routes.py::test_app_py_contains_only_the_a85_mount_lines` 钉「include_router 恰 3 行」（实测 assert 4==3，逐字见 commands-s4.md）。两文件不在 §2 写权面。候选：(a) S4 就地改写两哨兵（越界，禁）；(b) 保持红、由编排器按 FU-11/FU-19 先例统一迁移语义（M0-02 交付面入库位随 S4 提交或批给 S6/S8）。**倾向 (b)**——理由：FU-11 明文「禁改名或改写既有哨兵，语义迁移在 design 追注」，且迁移涉及 M0-02/S4 的守护所有权。影响面：全表 pytest 门在编排器冻结索引树复跑时以 647+2 红为本棒末态；两哨兵的**行为内核**（404/429 五 op 不可达、Problem 码集权威）未受本棒影响，红的是前提断言。

**U-3（listJobs 工作区核验的枚举面）** 事实：A220 指定路由侧核验，但 `deps.WorkspaceService` 端口恰 2 方法、无单条读取口（§5 表实测），实现只能 `list_workspaces` 有界翻页全枚举逐页比对 id；工作区数增长后每请求成本 O(N/100) 页。候选：(a) 维持现状（M0 规模下页数为个位数，语义无泄露：命中/穷尽二态、穷尽统一 404）；(b) FU 给 WorkspaceService 端口补 `get_workspace(workspace_id)` 只读口（动 application/**，非本棒）。**倾向 (a) + 建议 (b) 立 FU**——理由：不动硬禁面即可闭合 A220 验收点；(b) 是正解但不属 S4。影响面：仅 listJobs 延迟特征。

**U-4（If-Match 形参可空化 vs §1 签名逐字）** 事实：design §1 把 `if_match` 写为非可空 required Header，而 §6/§7 要求「缺 If-Match → 428」；required 声明下缺头被 FastAPI 在函数体前判 422，428 分支结构上不可达（本仓 install_error_handlers 无按头名细分）。候选：(a) 按 §1 字面（428 不可达，违约 §7 验收点）；(b) 形参 `str | None` + `check_if_match` 产 428（已实现；格式非法仍 422，语义与 §6 全表一致）。**倾向 (b)**——理由：§6 错误映射是权威面、§7 把 428 列为必测验收点；§1 该行属示意性简写（同 §1 未列 clock 形参而 §3/D-045 明文要求注入，同类）。影响面：cancelJob/retryJob 形参表 1 处可空标注。

**U-5（retry 源行 revision 的口径措辞）** 事实：§1/S2c 注记「源作业终态一字不变」，实测 store.retry 的 enqueue_retry 对源行做守卫更新 ⇒ 源 revision 1→2（state 不变），M0-04 design §2「每次写 +1」与此自洽；本棒守护按实测断言 revision==2。候选：(a) 以 DDL/§2「每次写 +1」为准，接受源行 revision 递增（现状，store 为冻结件）；(b) 判 store 违约并立 FU 改 store（动 worker/**，硬禁面）。**倾向 (a)**——理由：JOBS.md T9 与 §2 行口径支持「写即 +1」，且 S2c 注记同段本就声明 revision 由 store 独占。影响面：仅文档措辞对齐。

## 3. 未触碰的硬禁面收尾复核

见 commands-s4.md 末节表：契约 sha16/bytes 未变；`worker/service.py` sha=7b0dd1591fd5、`api/deps.py` sha=896f5663b390、`worker/deps.py` 156 行/120 行位逐字与 §5 同；git diff --name-only 内除我 5 件 + 邻居 1 件（repositories.py 826/0，未读改）外零项；`tests/integration/jobs/conftest.py` 保持不存在；state.json/pyproject/contracts/spec/scripts/worker/domain/infra/application 全部 0 写入。git status 终面与第 0 步一致（阳性对照零残留，8 条 sha 双向核验见 positive-control-s4.log）。
