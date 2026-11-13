# R13 · Lane Y · M0-04/S2b-2 派单文（qwen3.8-max / high · critical · loop_cap=2）

> **第一步必做**：完整读 `orchestrator/handoff/LANE-COMMON.md`（公共纪律：写入通道铁律、
> R12-1 except 元组损坏、6 条仓库反直觉事实、在飞污染与路径限定自验、守护必须有牙、
> 回执格式、L 循环上限）。本文只写**本 lane 特有**内容，公共部分不重述（R12-5）。

## 0. 基线（编排器实测，as-of 你开工时的 HEAD）

- branch `m0-framework`，派单时 HEAD = 见派单消息（FU-29 已入库，全仓 infra→worker 反向边 = 0）
- HEAD 树基线：`ruff format --check` 报 **234**、`mypy` **80 source files**、`pytest` **490 passed**
  （冻结索引树口径 = 469 frozen + 21 GIT_ENV_IGNORES 静态收集）
- 对账口径 = **HEAD 树 + 你 write_set 的增量**。同轮有 lane X（任务卡面）与 lane Z
  （`domain/activity/` + `api/{activities,rules}.py`）在飞，工作树的绝对分母会被它们抬高。

## 1. 任务：交付 M0-04/S2b-2 —— `worker/integrity.py` + `worker/deps.py`

**权威输入（按此顺序读，禁读 scope 外目录去找线索）**
1. `orchestrator/tasks/M0-04.md` —— 你的任务卡（含子任务档位表；S2b-2 那一行是你的目标）
2. `orchestrator/handoff/M0-04-design.md` —— **重点读 §9 的 S2 行、§5:47、以及第 52、149–168 行**
   那几段「S2b 硬约束（禁违反）」与 A154/A156 的点名要求
3. `orchestrator/handoff/M0-04.slice.json` —— 契约切片（**禁整读 443 KB 活契约**，手册 §5.3；
   切片里 `operations.<opId>.schemas.*` 是 schema 真值来源）
4. 既有实现（**只读**，是你必须对齐的冻结面）：`src/campaignlab/infra/artifacts.py`
   （S3 已落地，`__all__` 12 项含公共 `hash_file`、`verify_same_filesystem()`、
   `ArtifactWriter.commit()`）、`src/campaignlab/worker/{states,store,runner,leases,errors}.py`、
   `src/campaignlab/config.py`（`ConfigError`）

**必须交付的符号（design §9 点名，禁增减、禁改名）**
- `worker/integrity.py`：`Discrepancy`、`ManifestRow`、`verify_artifact_index(conn, data_dir) -> list[Discrepancy]`、`manifest_rows`
  - `verify_artifact_index` 的判据（design 第 52 行）：逐行核 `artifacts.relative_path` 的
    **存在性、sha256、byte_size**，以及 `jobs.result_json` **可解析且指向存在的制品**；
    缺件返回 `(workspace_id, artifact_id, relative_path, …)` 形态的 Discrepancy。
  - **sha256 必须复用 `infra/artifacts.py` 的公共 `hash_file`**（A157 提升它就是为了让
    integrity「与写入侧**同口径**复核」，design 第 160 行）—— **禁**自己再写一份哈希实现。
- `worker/deps.py`：`get_job_store`、`get_job_service`、`get_artifact_writer`、`resolve_data_dir`
  - **A156 硬要求**：`get_artifact_writer` 必须在**返回 writer 之前**调用一次
    `verify_same_filesystem()`，并落**守护用例**证明「`st_dev` 不符 → 抛 `config.ConfigError`
    → CLI 面 rc=2」。否则 design §5:47 的启动闸永不生效、AC-031 的写入侧前提缺一环。
    （注：`scripts/doctor.sh` 的部署期可见性属 **FU-30，不在你的写集内，禁碰 scripts/**。）
  - **`get_job_service` 目前没有 `JobService` 可返回** —— `worker/service.py` 属 **S2c**
    （A169 新立，排在你之后）。按 A169 处置：`get_job_service` 的**签名与返回类型注解**照 design
    落，函数体对 `JobService` 的引用用**延迟导入/TYPE_CHECKING** 形态，使本提交在
    `service.py` 尚不存在时仍能 import 通过、mypy strict 干净；**禁**自己抢写 `worker/service.py`
    （会与 S2c 双主写）。这一点若你判断有更优解，**报 U 项**，禁自行决定。

**A154 接线口径（强制契约，handler 侧二选一，禁第三种）**
- (a) `store.succeed(..., artifacts=())` —— 制品行已由 `ArtifactWriter.commit()` 在同一
  `BEGIN IMMEDIATE` 内登记；或 (b) 同一事务内先 `commit()` 再直接发终态谓词 UPDATE。
- **禁**「先 `commit()` 再把 record 传给 `succeed(artifacts=…)`」（会撞
  `UNIQUE(workspace_id,kind,sha256)`）。
- design 第 157 行要求 S2b **落守护用例**：同一 `(workspace_id,kind,sha256)` 重复登记必须红。

**A153 / design 第 149–150 行的分层硬约束（FU-29 刚闭合，禁把它弄回去）**
- `worker/integrity.py` 与 `worker/deps.py` 可以 import `infra.artifacts`（**正向边，合法**）。
- **禁**任何 `infra/** → worker` 的反向边：`tests/unit/test_layering_edges.py` 的白名单
  已收紧为 `frozenset()`，你新增一条就立刻判红。
- **禁**把 `deps` 的符号经 `worker/__init__.py` 再导出（design 第 150 行明禁）；
  `worker/__init__.py` 在你的 hard_deny 内。

## 2. 写权与硬禁

**只许写**：
```
src/campaignlab/worker/integrity.py        # 新建
src/campaignlab/worker/deps.py             # 新建
tests/unit/test_worker_integrity.py        # 新建（命名可与既有体例对齐，自行定，但必须在 tests/ 下）
tests/integration/jobs/test_worker_deps.py # 新建
evidence/M0/M0-04/**                       # 追加你的 s2b2-*.md 与 commands-s2b2.md
```
**硬禁（写一个即判越界、整条 lane 判红）**：
```
src/campaignlab/worker/__init__.py   worker/store.py   worker/service.py   worker/runner.py
worker/leases.py   worker/states.py   worker/errors.py
src/campaignlab/infra/**（含 artifacts.py，FU-29/S3 刚入库，禁改一字）
src/campaignlab/api/**（S4 的写集）   src/campaignlab/domain/**
scripts/**（FU-30）  migrations/**  contracts/**  spec/**  web/**  docs/**
orchestrator/**（台账/卡片/缺陷单/handoff 全归编排器）
tests/unit/test_artifacts.py  tests/unit/test_layering_edges.py
tests/unit/test_domain_errors.py  tests/unit/test_job_repository_terminal.py
tests/integration/jobs/test_artifact_write.py
```
**禁自行 `git add` / `git commit`**（LANE-COMMON §5）。

## 3. 必须保持绿 / 必须新增的守护

| 守护 | 期望 |
|---|---|
| `tests/unit/test_layering_edges.py` | 8 用例全绿（你新增的两个模块**不得**引入 infra→worker 反向边） |
| `tests/unit/test_artifacts.py` | 全绿，**你没改它**（它用 AST 读 `artifacts.__all__` + 多出项白名单） |
| `tests/unit/test_worker_runner.py`、`test_job_repository_terminal.py` | 全绿 |
| `tests/integration/jobs/test_artifact_write.py` | 全绿 |
| `mypy` 全表 | rc=0；source files **80 → 82**（你新增 2 个 `src/` 下 .py）+ 你的测试文件数 |
| 新增：`st_dev` 不符 → `ConfigError` → CLI rc=2 | **A156 点名要求，缺此判红** |
| 新增：同一 `(workspace_id,kind,sha256)` 重复登记 → 红 | **A154 / design:157 点名要求** |
| 新增：`verify_artifact_index` 对「缺件 / sha256 不符 / byte_size 不符 / result_json 不可解析 / result_json 指向不存在的制品」五种形态各能报出对应 Discrepancy | 逐形态一条正向对照 |

**正向对照（LANE-COMMON §6，缺此判红）**：每条新守护都要主动制造 RED、落原始输出、
sha256 双向核验后复原并复验绿。探针用 `tmp_path`，**禁落工作树**。

## 4. 自验命令（一律路径限定）

```bash
cd /home/szf/dev/CampaignLab && export PATH="$HOME/.local/bin:$PATH"
uv run --no-sync ruff format --check src/campaignlab/worker/integrity.py \
  src/campaignlab/worker/deps.py tests/unit/test_worker_integrity.py \
  tests/integration/jobs/test_worker_deps.py
uv run --no-sync ruff check src/campaignlab/worker/integrity.py \
  src/campaignlab/worker/deps.py tests/unit/test_worker_integrity.py \
  tests/integration/jobs/test_worker_deps.py
uv run --no-sync mypy            # 全表；80 -> 82+。若报错文件不在你 write_set 内 = 在飞污染，禁修
uv run --no-sync pytest -q tests/unit/test_worker_integrity.py \
  tests/integration/jobs/test_worker_deps.py tests/unit/test_layering_edges.py \
  tests/unit/test_artifacts.py tests/unit/test_worker_runner.py \
  tests/unit/test_job_repository_terminal.py tests/integration/jobs/test_artifact_write.py
```
禁跑全表 `ruff format --check .` / `pytest` 当自己的判据（LANE-COMMON §4）。
**禁**在 `tests/integration/jobs/` 新增 `conftest.py` 而不告知：那会触发
`rule_full_tree_mypy_on_basename_collision`（同 basename 冲突曾造成 D-035 的 G9 全表红灯）；
若确需 fixture，优先复用该目录既有 `conftest.py`，**要改它就先报 U 项**（它不在你的 write_set 内）。

## 5. 证据与回执

证据落 `evidence/M0/M0-04/`：`s2b2-integrity-deps.md`（符号清单 + 逐个判据的实测值）、
`commands-s2b2.md`（每条命令原文 + rc + 关键输出行）、`positive-control-s2b2.log`。
回执按 LANE-COMMON §7 的 8 段格式，≤90 行，必须含 `自报 token` 的**两个口径**
（单轮上下文规模 / 跨轮累计计费，A183：上限按累计计费口径判定，越限如实报 `over_cap` 禁抹平）。
