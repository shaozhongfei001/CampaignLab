# M0-04/S2c 取证 · `worker/service.py:JobService` + `JobStore.list_jobs`（lane Y2 · R15）

档位 `qwen3.8-max` / reasoning high（A215 ①：禁降档；本 lane 是原 lane 随主机重启消亡后的
新承接者，档位不变）。基线 `m0-framework` @ `bc2ea43`，开工首检 `git status --porcelain` 为空。
命令与 rc 全表见 `commands-s2c.md`，阳性对照原文见 `positive-control-s2c.log`。

## 1. 交付面（全部实测）

| 文件                                            | 形态     | numstat       | 行数 | 字节    | sha256\[:12\]  |
| ----------------------------------------------- | -------- | ------------- | ---- | ------- | -------------- |
| `src/campaignlab/worker/service.py` | 新建 | —（untracked） | 254 | 12 685 | `ad62252fd1de` |
| `src/campaignlab/worker/store.py` | **纯追加** | **65 / 0** | 736 | 34 328 | `c9e9416dfb05` |
| `src/campaignlab/worker/deps.py` | 仅删 :55 的 ignore 注释（A207） | 1 / 1 | 156 | 8 745 | `ac59435dd93f` |
| `tests/unit/test_worker_service.py` | 新建 | —（untracked） | 1053 | 49 062 | `686ab99091d7` |
| `tests/integration/jobs/test_worker_deps.py` | 改写 2 条用例 + 1 段 docstring（见 §5 U-6） | 45 / 18 | 632 | 27 316 | `69234fb4f35d` |
| `orchestrator/handoff/M0-04-design.md` | **仅文末追加**（A214 窄豁免） | **48 / 0** | 256 | 64 557 | `5b76bcb33984`；前 52 行 sha256 恒为 `a5e3807475ecf2…` |

`JobStore.list_jobs` 与 `JobService` 四方法的 `inspect.signature` 实取原文（3.14.10 / `uv run --no-sync`）：

    JobService.__init__(self, *, store: 'JobStore') -> 'None'
    JobService.list_jobs(self, *, workspace_id: 'str', actor_id: 'str', query_digest: 'str',
        limit: 'int', cursor_payload: 'Mapping[str, Any] | None' = None,
        q: 'str | None' = None, status: 'str | None' = None
    ) -> 'tuple[list[JobRecord], dict[str, Any] | None]'
    JobService.get_job(self, *, workspace_id: 'str', job_id: 'str') -> 'JobRecord | None'
    JobService.cancel_job(self, *, workspace_id: 'str', job_id: 'str', revision: 'int',
        now: 'datetime', actor_id: 'str', request_id: 'str',
        role: 'str' = 'OPERATOR') -> 'JobRecord'
    JobService.retry_job(self, *, workspace_id: 'str', job_id: 'str', revision: 'int',
        now: 'datetime', actor_id: 'str', request_id: 'str',
        role: 'str' = 'OPERATOR') -> 'JobRecord'
    JobStore.list_jobs(self, *, workspace_id: 'str', limit: 'int',
        after: 'tuple[str, str] | None' = None, q: 'str | None' = None,
        states: 'Sequence[str] | None' = None) -> 'list[JobRecord]'

`store.py` 的 65 行新增里，**64 行是文件末尾连续追加的 `list_jobs`**，另 **1 行是在 stdlib
导入块里插入 `import unicodedata`**（`import sqlite3` 之后，符合 isort 序）。两处都是**插入**，
故 `git diff --numstat` 的 deleted 恒为 0；既有 20 个 `def` 的源码段 sha256 逐个未变（守护
`test_store_py_frozen_defs_are_byte_identical`，期望值由 `git show HEAD:…/store.py` 机器求得后写死）。

## 2. 五项义务逐条对账

| 义务              | 落地形态                                                                                                     | 守护（用例名）                                              | 阳性对照 |
| ----------------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- | -------- |
| **A206** `store=` | `def __init__(self, *, store: JobStore)`，keyword-only、无默认值；`deps.py:135` 的 `factory(store=…)` 一字未动 | `test_job_service_constructor_takes_keyword_only_store`        | PC5      |
| **A207** 删 ignore | 同一次工作内删掉 `deps.py:55` 的 `# type: ignore[import-not-found]`；全表 `mypy` = `Success … 88 source files`，无 `unused-ignore` | `test_deps_no_longer_carries_the_import_not_found_ignore`（AST 定位行号，不搜全文） | PC7 |
| **A169** 纯追加    | `store.py` numstat **65 / 0**；20 个既有 `def` 源码段 sha256 逐个相同；文件里只多出 `list_jobs` 一个 `def`       | `test_store_py_frozen_defs_are_byte_identical`                | PC2      |
| **A91** 禁抢先落 `JobPage` | `list_jobs` 返回**裸二元组** `(list[JobRecord], dict \| None)`；`api/**` 全未触碰；`service.py` 的 AST 里不出现 `JobPage` 这个名字 | `test_list_jobs_returns_records_not_an_http_page_shell`       | —（判据是 AST 名字，S4 落地后不会变假红） |
| **分层红线 3** 显式时钟 | `service.py` 不 import `time`、无任何属性式取系统时间；`cancel_job`/`retry_job` 的 `now` 是必填 keyword-only | `test_service_module_never_reads_the_system_clock` + `test_mutating_service_methods_take_now_as_a_required_keyword` | PC6 |
| **A169③** 游标禁另发明 | `CURSOR_VERSION` / `BAD_CURSOR_DETAIL` 直接 import `application/workspace_service.py` 的那一份；载荷四键与键序照抄 design §1；`service.py` **0 条** `worker → api` 边 | `test_service_py_contributes_no_worker_to_api_edge` + `test_worker_to_api_edges_are_exactly_the_frozen_baseline` + `test_the_unencoded_payload_round_trips_through_the_frozen_codec` | PC4 |
| **A169①** 禁复制第二份 | `service.py` 里定义的函数**恰为 8 个**（4 方法 + `__init__` + 3 个私有游标/状态助手），无任何行→DTO 转换器、未 import `job_from_row` | `test_service_module_def_face_is_exactly_the_delivered_one`   | PC8      |
| **A81** SQL 写点唯一 | `store.py` 与 `service.py` 的**非 docstring** 字符串常量里 0 条 jobs DML；`store.py` 里像 SQL 的常量仍**恰为** `BEGIN IMMEDIATE`/`COMMIT`/`ROLLBACK` 三条 | `test_store_and_service_carry_no_jobs_dml_text` + `test_store_py_sql_text_is_still_only_the_three_transaction_control_statements` | PC3 |
| **A169 方法面** 禁增减禁改名 | `JobService` 公有方法集合 == `{list_jobs, get_job, cancel_job, retry_job}`；未经 `worker/__init__.py` 再导出 | `test_job_service_method_face_is_exactly_the_four_a169_named` + `test_job_service_is_not_reexported_from_the_worker_package` | —（集合相等即双向牙） |

守护用例合计 **44** 条（`tests/unit/test_worker_service.py`，`--collect-only` 实取），
其中 **11 条阳性对照**全部判红并字节级复原（`positive-control-s2c.log`）。

## 3. 关键设计决定（每条都给依据，无自创判据）

1. **`JobStore.list_jobs` 一条 SQL 都不写**。`store.py` 的模块纪律是「SQL 一律委托
   `JobRepository`」，且 `immediate()` 上方那句「只此三条是本模块出现的全部 SQL 文本」是
   冻结文本（纯追加禁改）。故取行走 A204 纯追加的 `JobRepository.list_for_workspace`，
   排序／键集／筛选在其返回的行序上做（Python 侧），与 `WorkspaceRepository.list_page`
   处理 `q` 的取向一致（「先过滤后计数」，先 LIMIT 会漏数据）。代价与后续选项见 U-3。
2. **`created_at DESC, id ASC` 用两趟稳定排序**：先按 `id` 升序，再按 `created_at` 逆序。
   Python 的 `sort` 稳定且 `reverse=True` 不颠倒等值元素，故与 SQL 的
   `ORDER BY created_at DESC, id ASC` 逐行等价（用例 `…_ties_on_created_at_fall_back_to_id_asc` 钉住）。
3. **`list_jobs` 返回裸二元组而不是新造一个结果 dataclass**：A169「禁增减」＋A91「禁组装分页壳」，
   新增任何公开结果类型都可能与 S4 的 `JobPage` 撞主写。二元组不引入任何新公开符号。
4. **`query_digest` 由调用方传入**：design §1 的公式含 `canonical_json`，而它住在 `api/common.py`；
   在 `service.py` 里调它就是新开一条 `worker → api` 边。故摘要计算与 `str ↔ payload`
   编解码一起归 S4，本层只做**绑定校验**（版本／摘要／actor／`k` 形状 → 400 `BAD_CURSOR`
   同一句 detail，七种失败收敛成一句，用例逐条打表）。
5. **`status` 非法值走 422 `VALIDATION_ERROR`**：design §6 的 `listJobs` 行原文
   「422 `VALIDATION_ERROR` `limit` 越界、`q`/`status` 超长、`status` 含未知态名」，
   且 `_STATUS_BY_CODE["VALIDATION_ERROR"] == 422`（不是 400 —— 第 1 轮就是这里判据写错）。
   大小写不放宽：`queued` 不是注册态名，与 `q` 的 casefold 子串匹配是两回事。
6. **`q` 折叠口径**：`store.list_jobs` 就地写 `unicodedata.normalize("NFKC", x).casefold()`，
   并配 10 探针的**等价性守护**对齐 `repositories._fold`（全角、合字 `ﬁ`、德语 `ß`、
   组合序列 `e`+`́`、土耳其 `İ`）。不 import 那个私有名、也不新增第二个公共折叠函数，见 U-4。

## 4. 实测更正（承接 R15-1 的体例，只报不改台账）

1. **第四处失真 · `worker → api` 边**：派单文 §六.5 与 R13 §2.3 都写「`worker` 禁 import `api`」，
   但 HEAD 树上这样的边**实测 6 条**（AST 与 grep 两种口径逐条一致）：`deps.py:47`、`states.py:20`、
   `runner.py:30`、`errors.py:27`、`integrity.py:59`、`store.py:33`；`worker/deps.py` 的模块
   docstring 还明写「import `infra`／`api`／`application` 都是**正向边，合法**」，
   `infra/db/repositories.py` 自己也 import `api.common` 取 DTO。`worker/__init__.py` 的
   **红线 3 是「显式时钟」**，不是分层。⇒「零边」判据在 HEAD 上即红，违反 LANE-COMMON §6 末条，
   故改为**冻结基线集合**（多一条红、少一条也红）。见 U-1。
2. **第五处失真 · ruff 分母**：派单文 §四 给「259 files already formatted」，HEAD 树实测 **261**
   （`git ls-tree -r HEAD` 取 `.py`+`.md`、按 `pyproject.toml` 的 `extend-exclude` 排除
   `spec/ prototype/ web/ node_modules`；`.py` 88 + `.md` 173）。两次实测自洽：
   261 + 2（本 lane）= **263**，261 + 9（本 lane 2 + 在飞 A1b 7）= **270**。
3. **`mypy` 分母无误**：基线 86 + 本 lane 2 = **88**（`Success`），收尾时 88 + A1b 7 = **95**（`Success`）。
   A207 已验证生效：`service.py` 出现且 ignore 删除后，全表 mypy 无 `unused-ignore`。
4. **`store.py` 的 20 个 `def` 确认**（R15-1 的口径复算通过）：AST 数 HEAD 树得 20，
   派单文的 16 与旧台账的 12 均不成立；`def list_jobs` 在 HEAD 的出现次数为 0。

## 5. U 项（只报不裁；每条给两个候选 + 倾向）

**U-1 `worker → api` 的 6 条既有边怎么收口。** 派单文要求「断言没有任何一条指向
`campaignlab.api`」，实测 HEAD 有 6 条且被 `deps.py` docstring 明确追认为合法正向边。
候选 A：维持本 lane 的做法 —— 冻结基线集合 + `service.py` 零边（判据在 HEAD 上成立，
新增即红）。候选 B：编排器立 followup，把 `api/common.py` 的 DTO/`Problem`/`canonical_json`
下沉到 `domain` 或新建一个契约层，再把这 6 条边清零，并把「`worker → api`」上提为
`test_layering_edges.py` 的通用一面（R13 §4 原文就要求把这一条写进 U 项由编排器统一收口）。
**倾向 A 短期 + B 长期**：A 已落地且有牙；B 涉及公共冻结面，不属 S2c 写集。

**U-2 `listJobs` 的 404 `RESOURCE_NOT_FOUND` 无人产生。** design §6 给 `listJobs` 声明
「404 工作区不存在或属外工作区」，但 A206 把 `JobService.__init__` 钉成只有 `store=`，
`JobStore` 也没有工作区查读面（`WorkspaceRepository` 在 `store.py` 里根本没被注入），
故本层**无法**产生这条 404。候选 A：S4 在路由侧先核工作区存在性（api 层已有 `Session`/config，
也可复用 `application` 侧的既有查读面）。候选 B：给 `JobService` 加第二个注入项
（如 `workspaces: WorkspaceRepository`）—— 需要同步改 `deps.py:135` 的 `factory(store=…)`，
**超出 A207 的窄豁免**，且会动 A206 的构造面。**倾向 A**：不扩冻结面，且 404 的语义
（工作区可见性）本就属于会话/路由层。

**U-3 分页在 Python 侧的性能面。** `JobStore.list_jobs` 每翻一页都要经
`JobRepository.list_for_workspace` 取该工作区的**全部** `jobs` 行，再在内存里排序/筛选/截断。
M0 数据量下可接受，但作业表是只增不减的。候选 A：保持现状（不动 hard-deny 文件，
`store.py` 的 SQL 文本面保持恰好三条事务控制语句）。候选 B：编排器给
`infra/db/repositories.py` 再开一次 append-only 豁免，加
`JobRepository.list_page(conn, *, workspace_id, limit, after, q, states)`（对齐
`WorkspaceRepository.list_page` 与显式索引），`JobStore.list_jobs` 退回薄委托。
**倾向 B 作为 S4/S5 之前的 followup**，但它必须另派 lane —— `repositories.py` 在本 lane 硬禁内，
本 lane 未自行扩写集。

**U-4 `q` 折叠口径没有公共单点。** `NFKC + casefold` 的唯一实现是
`infra/db/repositories.py::_fold`（**私有**名），S2c 既不能把它提升为公共符号
（该文件硬禁），也不该 import 私有名。已在 `store.list_jobs` 就地写同一表达式并加
10 探针等价性守护。候选 A：保持「就地实现 + 等价性守护」。候选 B：followup 把 `_fold`
提升为 `repositories.fold` 并进 `__all__`，`WorkspaceRepository.list_page` 与
`JobStore.list_jobs` 同指该符号。**倾向 B**（消掉第二份实现才是 A169① 的终局），
但同属 `repositories.py` 的写权问题，须编排器裁定。

**U-5 `deps.py` 的「S2c 尚未交付」文本已过期。** `_SERVICE_MISSING` 常量与模块 docstring
第 2 条仍写「`worker/service.py` 属 M0-04/S2c … 当前**不存在**」，S2c 落地后是错的；
`test_worker_deps.py` 里那条错误分支用例也因此必须靠 `monkeypatch` 造缺席（已改写，PC10/PC11 有牙）。
本 lane 对 `deps.py` 的写权只有 :55 那一行（A207），故**未改**。候选 A：编排器给 `deps.py`
一次窄豁免更新这两段文本（它是**当前状态描述**而非历史裁定，留着会误导下一棒）。
候选 B：按 D-011「历史文本只加注不改写」保持原文，由 design.md 的 S2c 注记承担更正。
**倾向 A**，因为 `_SERVICE_MISSING` 是**运行期报错文本**，用户/下一棒会真的读到它。

**U-6 改写了 R13 §3 列为硬禁的 `tests/integration/jobs/test_worker_deps.py`。** 该文件里
两条用例以「`service.py` 缺席」为前提，S2c 一落地必然判红（实测 2 failed）。改写的依据不是自裁：
那条用例的**自带前提断言原文**就写着「它已出现 ⇒ 请删掉 deps.py 里的
type: ignore[import-not-found] **并改写本用例**」；且本轮编排器消息 §七 给的写权是
`tests/**`（§八 的硬禁清单里没有该路径）。numstat = 45 add / 18 del，改写范围严格限于
这 2 条用例 + docstring 的 ③ 段，其余 16 条一字未动（`tests/integration/jobs` 31 passed）。
候选 A：追认本次改写。候选 B：回退，由编排器另派 lane 处理 —— 代价是全表 pytest 会留 2 条红，
与 A207「否则全表判红」的立法目的直接冲突。**倾向 A**。

**U-7 游标常量的跨用例模块耦合。** `service.py` 从 `application/workspace_service.py` import
`CURSOR_VERSION` / `BAD_CURSOR_DETAIL`（A169③「禁另发明」的最强形态：单一真源，不写第二个
版本号/第二句 detail）。副作用是 jobs 的用例服务依赖 workspace 的用例服务模块。
候选 A：保持 import（漂移不可能发生）。候选 B：followup 把这两个常量连同 `load_cursor_secret`
上提到一个共享模块（如 `application/cursors.py`），两侧同指。**倾向 B**，但上提会动
`application/workspace_service.py`（非本 lane 写集），须另派。

## 6. 未触碰的硬禁面（收尾复核）

`src/campaignlab/infra/db/repositories.py`、`src/campaignlab/domain/activity/**`、
`src/campaignlab/api/**`（含 `common.py`/`app.py`/`deps.py`/`jobs.py`）、
`tests/unit/test_domain_errors.py`、`tests/unit/test_layering_edges.py`、`scripts/**`、
`pyproject.toml`、`contracts/**`、`spec/**`、`prototype/**`、`web/**`、`orchestrator/state.json`：
本 lane **零字节改动**（`git status --porcelain` 里出现的 `api/common.py` 401/0 与
`test_domain_errors.py` 2/2、`domain/activity/` 7 个新文件全部属在飞 lane A1b，见回执第 8 段）。
`orchestrator/handoff/M0-04-design.md` 仅在文末追加（A214 窄豁免），前 52 行 sha256 复核仍为
`a5e3807475ecf2791a879b30f337ff4c2652c84fbd2efb94ecab64c5348513dd`。
