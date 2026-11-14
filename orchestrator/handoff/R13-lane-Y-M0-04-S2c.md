# R13 · Lane Y 续接（send_input）· M0-04/S2c 派单文（qwen3.8-max / high · critical · loop_cap=2）

> 你刚交付完 S2b-2。**本条是同一 lane 的下一棒**（A168 ③：四步串行由同一条 max lane 复用承接，
> 复用可免去重复读取 artifacts.py 的 `__all__`、layering 守护白名单、worker 包分层红线 —— 这是省 token 的正解；
> A168 ④：**档位置换 max→flash 一律禁止**）。公共纪律仍在 `orchestrator/handoff/LANE-COMMON.md`，不重述。

## 0. 基线

- branch `m0-framework`，HEAD = 见本消息（你的 S2b-2 已由编排器独立复验后入库）。
- HEAD 树基线：见本消息（编排器在冻结索引树上实测的 ruff / mypy / pytest 三值，禁自己推算）。
- 在飞：lane Z（`orchestrator/handoff/M2-01-design.md`）、lane V（`tests/unit/test_orch_harness.py` +
  `evidence/M0/FU-35/`）。自验一律路径限定；全表 mypy 会因它们的未入库 `.py` 抬高 source files 数，那不是你的红。

## 1. 任务：M0-04/S2c —— `worker/service.py` + `JobStore.list_jobs`（A169 新立，A168 串行链第 4 棒）

**权威依据（按此顺序读，禁读 scope 外目录找线索）**
1. 台账 `tasks["M0-04"].s2c_note`（A169 的完整裁定，本 lane 的**主契约**）与 `s2b_note`、`subtask_progress`。
2. `orchestrator/handoff/M0-04-design.md` §9 的 S2 行（点名 `worker/service.py:JobService`，
   方法 `list_jobs,get_job,cancel_job,retry_job`）。注意：**design 文档里没有 S2c 字样**（它是 A169 后立的），
   所以 S2c 的写权与硬约束**以 `s2c_note` 为准**，design 只提供 `JobService` 的方法面。
3. `orchestrator/handoff/M0-04.slice.json` 的 `operations.listJobs`（响应形状 `JobPage{items(0-100), next_cursor}`）。
4. 既有实现（**只读**，必须对齐的冻结面）：`src/campaignlab/worker/store.py`（671 行 / 16 个 `def`）、
   `worker/deps.py`（你刚写的，`get_job_service` 是**延迟 import** 形态，正等着 `service.py` 出现）、
   `worker/{states,leases,runner,integrity,errors}.py`、`worker/__init__.py`（分层红线，尤其红线 3）、
   `src/campaignlab/infra/db/repositories.py`（`job_from_row` 在第 221 行，`__all__` 第 52 行含它）。

**必须交付的符号（A169 点名，禁增减、禁改名）**
- `src/campaignlab/worker/service.py`（**新建**）：`JobService`，方法面 = `list_jobs` / `get_job` / `cancel_job` / `retry_job`。
- `src/campaignlab/worker/store.py`：**纯追加** `JobStore.list_jobs`。既有 16 个 `def` 的签名、函数体、SQL 文本
  **一字不改**；`git diff --numstat` 对该文件必须是「N add / **0 del**」，出现任何删除行即判越界（体例同 A82）。

## 2. 五条硬约束（A169 原文，违反即判红）

1. **复用 `infra.db.repositories.job_from_row` 做行→DTO（N5）**，禁复制第二份实现。
2. **SQL 写点唯一（A81）**：`JobRepository`（`infra/db/repositories.py`）是**唯一**含 `INSERT INTO jobs` /
   `UPDATE jobs` 的模块。你新增的任何文件里都**禁**出现这两个串（已有机器守护按文件集合判红）。
   `JobStore` 只能是调用 `JobRepository` 的薄封装。
3. **游标禁另发明**（A169 ③）。**但编排器在此预裁一个分层陷阱**：`encode_cursor` / `decode_cursor` 定义在
   `src/campaignlab/api/common.py`（api 层），而 `worker` 是更内层 —— **worker 包禁 import api 包**，
   否则制造 worker→api 反向分层边（FU-29 刚把 infra→worker 的最后一条反向边消掉，禁再开一条）。
   故 A169 ③ 的「复用」= **复用同一套游标语义与载荷形状**：`JobService.list_jobs` 接收/返回**未编码的游标载荷**
   （与 `encode_cursor` 的入参 `payload: Mapping[str, Any]` 同形状），**编解码的调用点归 S4（api 层）**。
   若你实测发现既有代码里 worker 已经 import 了 api，**报 U 项**，禁照抄。
4. **只返回领域/DTO 层结果**（`JobRecord` 序列 + 游标载荷），**禁组装 HTTP 分页壳**：`JobPage` 依 A91 归
   **M0-04/S4** 在 `api/common.py` append-only 追加，S2c **禁抢先添加**（避免双主写，A84/A91 同理）。
   故 `src/campaignlab/api/**` 全在你的 hard_deny 内。
5. **`now` 一律由调用方从 `Clock` 传入**，本包禁取系统当前时间（`worker/__init__.py` 红线 3）。

## 3. 写权与硬禁

**只许写**：
```
src/campaignlab/worker/service.py            # 新建
src/campaignlab/worker/store.py              # 只准纯追加 list_jobs（numstat deleted 必须为 0）
tests/unit/test_worker_service.py            # 新建（JobService 四方法 + list_jobs 分页/游标）
evidence/M0/M0-04/**                         # 追加你的 s2c-*.md 与 commands-s2c.md
```
**硬禁**：`src/campaignlab/api/**`（S4 的写集，含 `common.py` 的 `JobPage`）、`src/campaignlab/infra/**`
（A82 的 repositories.py append-only 豁免**不给 S2c** —— `list_jobs` 依 A169 落 `store.py`；若你判断分页查询
更适合放 `JobRepository`，**报 U 项**由编排器裁定，禁自行扩写集）、`worker/__init__.py`（公共冻结面：
`__all__` 现为 20+ 项且被守护钉死，**禁**把 `JobService` 加进去 —— 下游按 `campaignlab.worker.service.JobService`
直接取；若你判断必须 re-export，报 U 项）、`worker/{integrity,deps,states,leases,runner,errors,capacity}.py`
（`deps.py` 是你上一棒刚交付的，本棒**禁再改**：它的 `get_job_service` 已是延迟 import，`service.py` 一出现即生效）、
`contracts/** spec/** docs/** web/** scripts/** migrations/** orchestrator/**`、
`tests/unit/test_layering_edges.py`、`tests/unit/test_domain_errors.py`、`tests/integration/jobs/**`（S5/S6 的写集）。
**禁自行 `git add` / `git commit`**。

## 4. 必须保持绿 / 必须新增的守护

- `tests/unit/test_layering_edges.py`：实跑必须仍全绿，且**反向边数仍为 0**（你新写的 `service.py` 不得引入
  worker→api 或 worker→infra 之外的新反向边；`worker → infra.db.repositories` 是既有合法方向，照 `store.py` 的体例）。
- A81 守护（`INSERT INTO jobs|UPDATE jobs` 的文件集合 == `{repositories.py}`）：实跑必须绿。
- 新增守护必须有牙（LANE-COMMON §6）：① `store.py` 的**纯追加**性质 —— 用 `git diff --numstat` 的 deleted==0
  作断言，或用 `inspect.signature` 钉住既有 16 个方法的签名逐个未变；② `service.py` 内**禁出现** SQL 写文本
  （用 AST/正则扫，禁裸子串判「声明禁用」的文本 —— R13-2 的教训）；③ `now` 由参数传入 ——
  断言 `service.py` 内不出现取系统当前时间的调用（如 `datetime.now` / `time.time`）。
- 正向对照 ≥3 条，全部用 `tmp_path` 或**局部构造**，禁落工作树；若必须改本体，用 sha256 双向核验复原并留两个摘要。

- **worker → api 反向边守护（本 lane 新增，编排器预裁的分层陷阱要有机器牙）**：现有
  `tests/unit/test_layering_edges.py` 只覆盖 `infra → worker` 一个方向（编排器实读其 docstring 与
  `INFRA_ROOT` / `WORKER_PACKAGE` / `scan_worker_import_edges` 确认），**全仓没有任何守护覆盖
  `worker → api`**。故第 2.3 条的禁令目前只是纪律、没有牙。要求：在你自己的
  `tests/unit/test_worker_service.py` 里加一条用例，扫 `src/campaignlab/worker/*.py` 的
  `Import` / `ImportFrom` AST 节点，断言**没有任何一条**指向 `campaignlab.api`（含父包属性式
  `from campaignlab.api import ...` 与子模块式 `from campaignlab.api.common import ...` 两种形态，
  口径照抄 `test_layering_edges.py` 的 `_is_worker` / 相对导入 level 处理，注意它 docstring 里记的
  `level == 0` 会多留一级那个坑）。该用例必须配 `tmp_path` 探针正向对照（造一条 worker→api 边必须判红）。
  **禁改 `test_layering_edges.py`**（它在 hard_deny 内）；把「该守护应上提为全仓分层守护的通用一面」
  写进回执 U 项，由编排器立 followup 统一收口（禁你自己扩 scope）。
## 5. 回执（LANE-COMMON §7 的 8 段，≤90 行）

第 2 段给逐文件 `git diff --numstat`（`store.py` 那条必须显式写出 `deleted=0`）与 `JobService` 四方法的
`inspect.signature` 实取原文；第 3 段给命令对账表（rc + 实测 vs 期望）；第 4 段给正向对照 RED 原文位置；
第 5 段 U 项（含第 2.3 条分层陷阱与第 3 节两处「报 U 项」的实测结论）；第 6 段 token 两口径
（max 累计计费上限 200k，A183）；第 7 段 L 循环；第 8 段 IN_FLIGHT_CONTAMINATION（归 Z/V 的，禁修）。

## 6. L 循环

`critical=true`（slack=0）⇒ 上限 **2 轮**。同一条守护连续 2 轮修不绿 → 立即停手写 `STALLED` + BLOCKER +
一个「缩小范围不降质量」的降级交付选项，禁第 3 轮硬试。
