# M0-04 / S3 原子制品写入 · 设计 → 实现 → 测试对应表

- lane **S** · 子任务 **S3** · 档位 **qwen3.8-max**（手册 §6.3「事务边界与原子性」强制 max，未降档）
- 采集时点 **2026-11-14T02:06+08:00**（Asia/Shanghai）· HEAD `eaf02dd` · WSL2 内核 `6.18.58.1-microsoft-standard-WSL2`
- 权威依据（只读）：`orchestrator/tasks/M0-04.md:45`（S3 行）、`:22`（gate）、`:26-30`（scope_allow/deny、public_frozen）、`:33`（禁止段）；
  `orchestrator/handoff/M0-04-design.md:45-52`（§5 原子制品）、`:69`（§7 public_frozen）、`:86`（§9-S3 符号面）、`:19`（§2 运行参数）、`:40`（§4 TX5 败者制品）；
  `orchestrator/state.json` 裁定 **A89**（`artifacts.kind="JOB_RESULT"`、`result_ref` 断言口径）、**A110**（`worker/integrity.py`+`worker/deps.py` 顺延为 S2b，硬依赖本文件）、**A81/A82/A83**（SQL 写点／冻结面／租约计算点）
- 交付落点（全部新建，未改任何既有文件）：`src/campaignlab/infra/artifacts.py`、`tests/integration/jobs/__init__.py`、
  `tests/integration/jobs/test_artifact_write.py`、`tests/unit/test_artifacts.py`、`evidence/M0/M0-04/{commands.md,s3-artifacts.md}`

---

## 1. 冻结符号面逐条落地（design §9-S3 点名的 10 个符号 + 1 个 id 前缀常量）

| design §9-S3 要求的符号 | 实现落点（file:line） | 形状／口径 |
|---|---|---|
| `ARTIFACT_KIND_JOB_RESULT` | `src/campaignlab/infra/artifacts.py:71` | `= "JOB_RESULT"`（A89 为其权威来源） |
| `TMP_STALE_SECONDS` | `artifacts.py:74` | `= 3600`（design §2 运行参数表）；`min_age` 可注入小值，测试不 sleep |
| `relative_path_for` | `artifacts.py:143` | `(*, kind, workspace_id, sha256) -> str`；`results/<kind>/<ws>/<sha[:2]>/<sha>`，相对路径、posix 分隔符 |
| `stage_root` | `artifacts.py:115` | `(data_dir) -> Path` = `<data_dir>/tmp/jobs`（design §5 独立尝试目录根） |
| `results_root` | `artifacts.py:120` | `(data_dir) -> Path` = `<data_dir>/results`（OPERATIONS.md:17 七子目录之一） |
| `CommittedArtifact` | `artifacts.py:231` | frozen dataclass：`workspace_id/artifact_id/kind/sha256/relative_path/byte_size/path/reused_file/reused_row` |
| `AttemptStage` | `artifacts.py:295` | 上下文管理器；`write/write_file/seal/mark_committed/discard`；`sha256`/`byte_size` **增量**累计 |
| `ArtifactWriter.verify_same_filesystem` | `artifacts.py:504` | `() -> None`；`st_dev` 不等 → `config.ConfigError`（CLI 侧 rc=2） |
| `ArtifactWriter.begin` | `artifacts.py:526` | `(workspace_id, job_id, attempt) -> AttemptStage`；`attempt` 进路径 + 暂存名带随机后缀 |
| `ArtifactWriter.commit` | `artifacts.py:553` | `(conn, stage, *, workspace_id, kind, now) -> CommittedArtifact`；在调用方的 `BEGIN IMMEDIATE` 内执行 |
| `SweepReport` | `artifacts.py:260` | frozen dataclass：dry_run/min_age_seconds/referenced_rows/scanned_result_files/referenced_files_seen/ 4 个路径元组/skipped_symlinks/removed_files/removed_dirs/failed_removals |
| `sweep_unreferenced` | `artifacts.py:730` | `(conn, data_dir, *, now, min_age=TMP_STALE_SECONDS, dry_run=True) -> SweepReport` |
| `ARTIFACT_ID_PREFIX`（新增常量，非 design 点名） | `artifacts.py:76` | `= "art"`，与 `audit` 的 `aud`／`workspaces` 的 `ws` 同体例（`new_resource_id`） |

**冻结面机器守护**：`tests/unit/test_artifacts.py:249`（参数名／参数序／keyword-only 边界／默认值／返回注解逐条对齐 design §5）
与 `:273`（design §9 点名的 10 个符号必须全在 `__all__` 内，多出项只允许 `ARTIFACT_ID_PREFIX`）。

## 2. design §5 六条要求 → 实现 → 测试

| design §5 原文要求 | 实现落点 | 证明用例 |
|---|---|---|
| 独立尝试目录 `<data_dir>/tmp/jobs/<ws>/<job>/<attempt>/`，`attempt` 入路径使并发尝试互不覆写 | `artifacts.py:526-551`（`begin`）、`_TMP_PARTS:79` | 集成 `test_artifact_attempt_dirs_are_isolated_per_attempt`（`tests/integration/jobs/test_artifact_write.py:336`）、单测 `test_artifact_stage_is_reusable_only_once_per_attempt_dir`（`tests/unit/test_artifacts.py:192`） |
| 启动即 `verify_same_filesystem()`，`st_dev` 不符即抛配置错（rc=2），跨设备 `os.replace` 会 `EXDEV` | `artifacts.py:504-524` | 集成 `test_artifact_cross_device_layout_is_rejected_at_startup_and_at_commit`（`:470`，**真实双设备**：`/dev/shm` 符号链接，未 skip）、`test_artifact_commit_reports_exdev_as_red_instead_of_copying`（`:432`，monkeypatch 决定性用例，断言只调用一次 `os.replace`、无 copy 兜底） |
| 写入序：`begin` → 事务外增量算 `sha256`/`byte_size` → `commit` 在 TX5 内 `makedirs`→`os.replace`→登记→**回读权威 id** | `artifacts.py:553-611`（`commit`）、`613-645`（`_place_file`）、`647-701`（`_register`）、`703-718`（`_select_artifact_id`） | 集成 `test_artifact_commit_registers_index_and_result_ref_in_one_transaction`（`:240`）、`test_artifact_final_path_stays_invisible_until_the_atomic_rename`（`:297`，含「事务内文件已就位、索引行对其它连接仍不可见」的隔离断言） |
| 提交失败复用：终态已有同摘要文件则**跳过 `os.replace`** 直接登记；TX5 回滚后重试命中同一摘要文件（JOBS.md:25） | `artifacts.py:617-626`（复用判定）、`667-669`（行复用即返回既有 id） | 集成 `test_artifact_same_content_yields_stable_digest_and_reuses_row`（`:640`，第二次提交把 `os.replace` 换成「一调就 AssertionError」的桩，证明真的没再 rename）、`test_artifact_retry_after_failed_commit_reuses_the_same_digest_file`（`:678`，断言 **inode 不变**） |
| 未引用制品回收：只清「无 `artifacts` 行引用的 results 文件」＋「超期尝试目录」；`dry_run=False` 才真删；永不删有行者与关联证据（OPERATIONS.md:22） | `artifacts.py:730-837`；引用集合来自一条只读 `SELECT relative_path FROM artifacts`（`:760`） | 集成 `test_artifact_sweep_removes_unreferenced_and_keeps_referenced`（`:521`）、`test_artifact_sweep_never_touches_in_flight_attempt_dirs`（`:567`）、`test_artifact_sweep_ignores_every_other_data_subdir`（`:610`） |
| 重命名成功后事务失败 → 该制品成为「未引用制品」，交 sweep 回收（design §4:40 / JOBS.md:23） | `artifacts.py:688-695`（登记失败就地回收）＋ `sweep_unreferenced` 兜底 | 集成 `test_artifact_registration_failure_reclaims_the_renamed_file`（`:361`）、`test_artifact_rollback_after_rename_is_reclaimable_by_sweep`（`:390`） |
| 终态路径已有**不同内容**的文件 → 拒绝覆盖（内容寻址冲突／受控目录被污染） | `artifacts.py:618-627` | 集成 `test_artifact_commit_rejects_mismatched_content_at_the_final_path`（`:707`） |

## 3. 派单文 6 项覆盖点 → 测试函数名（rc 为判据，计数不写死）

| # | 覆盖点 | 测试函数（file:line） |
|---|---|---|
| ① | 正常写入 ＋ 同事务登记索引与结果引用 | `test_artifact_commit_registers_index_and_result_ref_in_one_transaction`（`tests/integration/jobs/test_artifact_write.py:240`）；纯函数面 `test_artifact_relative_path_is_content_addressed_and_relative`（`tests/unit/test_artifacts.py:52`）、`test_artifact_digest_is_stable_across_chunk_boundaries`（`:119`） |
| ② | 重命名原子性（终态不可见中间态） | `test_artifact_final_path_stays_invisible_until_the_atomic_rename`（`:297`）、`test_artifact_attempt_dirs_are_isolated_per_attempt`（`:336`）；`test_artifact_stage_discards_payload_when_not_committed`（`tests/unit/test_artifacts.py:156`）、`test_artifact_stage_cleans_up_when_handler_raises`（`:170`） |
| ③ | 事务回滚不留终态制品（＋重命名后回滚可被回收识别） | `test_artifact_registration_failure_reclaims_the_renamed_file`（`:361`）、`test_artifact_rollback_after_rename_is_reclaimable_by_sweep`（`:390`） |
| ④ | 跨盘 `EXDEV` 判红 | `test_artifact_commit_reports_exdev_as_red_instead_of_copying`（`:432`）、`test_artifact_cross_device_layout_is_rejected_at_startup_and_at_commit`（`:470`，真实双设备） |
| ⑤ | 未引用回收命中／不命中在飞尝试目录 | `test_artifact_sweep_removes_unreferenced_and_keeps_referenced`（`:521`）、`test_artifact_sweep_never_touches_in_flight_attempt_dirs`（`:567`）、`test_artifact_sweep_ignores_every_other_data_subdir`（`:610`） |
| ⑥ | 同内容稳定摘要 | `test_artifact_same_content_yields_stable_digest_and_reuses_row`（`:640`）、`test_artifact_retry_after_failed_commit_reuses_the_same_digest_file`（`:678`）、`test_artifact_digest_is_stable_across_chunk_boundaries`（`tests/unit/test_artifacts.py:119`）、`test_artifact_write_file_matches_incremental_write`（`:133`）、`test_artifact_empty_payload_is_a_legal_artifact`（`:146`） |

S6 预留的 6 个用例名（design §9-S6）与本卡覆盖点的对应：`test_stage_dir_isolated_per_attempt`↔②、`test_atomic_rename_same_filesystem`↔②④、
`test_commit_failure_reuses_same_digest_file`↔⑥、`test_unreferenced_artifact_swept`/`test_referenced_artifact_never_swept`↔⑤、
`test_verify_artifact_index_detects_missing_file`↔**S2b**（依赖 `worker/integrity.py`，A110 顺延，本卡未交付）。
本卡文件名刻意取 `test_artifact_write.py`（不与 S6 的 `test_artifact.py` 同 basename），S6 落地时两者可共存、`-k artifact` 一并命中。

## 4. 关键实现取舍（均有代码内注释与守护用例）

1. **零 DML**：本模块不发任何 `INSERT/UPDATE/DELETE`；`artifacts` 行的写入一律经
   `infra.db.repositories.ArtifactRepository.insert`（`artifacts.py:673-683`），只保留两条只读 `SELECT`
   （`:703` 回读权威 id、`:760` 取全表已引用路径）。守护：`tests/unit/test_artifacts.py:335`（AST 扫非 docstring 字符串常量，
   DML 命中数必须为 0、SELECT 常量恰好 2 条）。这是为了同时满足 design §5 的「回读权威 id」与 A81／`repositories.py:5`
   的「5 张表 SQL 写点收敛」——见本报告 §5 裁定项 R1。
2. **幂等登记**用「先按 `(workspace_id,kind,sha256)` 查、查不到才插、插完再回读」实现（`artifacts.py:647-701`），
   等价于 design §5 写的 `ON CONFLICT(workspace_id,kind,sha256) DO NOTHING`：`BEGIN IMMEDIATE` 已把写者串行化，
   「查不到 → 插入」之间不会有第二个写者插入同一摘要。
3. **`write()` 每块 `flush()`（非 `fsync`）**（`artifacts.py:366-384`）：缓冲留在进程内会让暂存件 `st_mtime` 停在开始写入的时刻，
   于是「写一小时的巨大制品」在**另一个进程**的 sweep 眼里成了超期尝试目录。`fsync` 只在 `seal()`（`:398-409`）做一次，
   保证 `os.replace` 搬到终态的是已落盘内容（否则崩溃后可能看到零长度终态文件）。
4. **在飞尝试目录双层保护**（`sweep_unreferenced`）：进程内 `_LIVE_STAGES` 登记（`artifacts.py:93-109`，`begin` 入册、
   `mark_committed`/`discard` 出册）＋ 子树最新 `st_mtime` 与 `now - min_age` 比（`:185-198`，取子树最新值而不是目录自身
   mtime，理由同上）。守护：`tests/integration/jobs/test_artifact_write.py:567` 把在飞目录的 mtime **人为推到超期**，
   断言它仍进 `in_flight_attempt_dirs` 而未被删，且随后还能正常提交 TX5。
5. **扫描面只有 `results/**` 与 `tmp/jobs/**`**：`state`／`raw`／`snapshots`／`exports`／`logs` 结构上不可能被触碰
   （OPERATIONS.md:22「只清理超期临时件与没有记录引用的制品」）。守护：`tests/integration/jobs/test_artifact_write.py:610`。
6. **显式时钟**：模块内不出现 `datetime.now(`/`time.time(`/`time.monotonic(`、不 `import time`；`now` 一律由调用方注入，
   文件年龄只用 `st_mtime`。守护：`tests/unit/test_artifacts.py:353`（本模块级）＋ 既有全树守护 `tests/unit/test_clock.py:68`。
7. **受控目录守卫**：`_assert_within`（`artifacts.py:219`）对终态路径做 `resolve()` + `is_relative_to(data_dir)`，
   路径片段另经 `is_resource_id`／`_safe_token` 校验（`:125-140`），堵死 `..`／分隔符／尾点尾空格的目录穿越
   （OPERATIONS.md:11）。守护：`tests/unit/test_artifacts.py:81`/`:105`/`:212`/`:219`。
8. **不吞领域错**：`except` 只允许 `OSError`（清理尽力而为）与 `BaseException`（登记失败时先回收再原样重抛）。
   守护：`tests/unit/test_artifacts.py:369`。
9. **金额／比率／时区**：本模块不处理金额与比率，全文件无 `float` 参与领域计算（唯一的浮点是 `st_mtime` 与 `min_age`
   的年龄比较，非金额／比率）；`created_at` 一律 `ensure_utc(now).isoformat()` 落 UTC ISO-8601（`artifacts.py:682`），
   `Asia/Shanghai` 只用于证据时间戳投影。

## 5. 上交编排器裁定／知会的事项（禁自行扩 scope，均未动手）

- **R1（design §5 字面 vs 既有 SQL 落点约定）**：design §5 写的是在 `commit()` 内直接发
  `INSERT INTO artifacts(…) ON CONFLICT(workspace_id,kind,sha256) DO NOTHING`；但 `infra/db/repositories.py:5` 自称
  「5 张表唯一的 SQL 落点」，且 `worker/store.py:207`／`infra/db/repositories.py:712-714` 都写明「制品行由调用方用
  `ArtifactRepository.insert` 登记」。`infra/db/**` 不在本卡写权内（无法给它加 `upsert_ignore`），故本实现取
  **「SELECT → 必要时 `ArtifactRepository.insert` → 再 SELECT 回读」**，可观测语义与 design §5 一致（幂等、冲突时既有行 id 胜出、
  回读值权威），且把写点留在仓储内。若编排器要求逐字实现 `ON CONFLICT`，需给 `infra/db/**` 开口子（走 S2b／CR），本卡未自行裁定。
- **R2（infra → worker 的导入边）**：按 design §9 与 `worker/errors.py:52-57` 的「供 S3 落地后直接复用」，本文件
  `from campaignlab.worker.errors import ArtifactCommitFailed`（`artifacts.py:54`），形成 `infra → worker` 的反向导入边。
  实测无环（`mypy` 77 文件 rc=0、全树 pytest rc=0）。若 S2b 的 `worker/deps.py` 让 `worker/__init__.py` 先于 `errors`
  导入 `deps`，本导入仍能解析（走子模块路径而非父包属性）；如编排器希望消除这条边，正解是把 `ArtifactCommitFailed`
  下沉到 `domain/errors.py`（公共冻结件，本卡禁改）。
  **导入序实测（4 种顺序，各 rc=0）**：`worker → artifacts`(1)、`artifacts` 单独(2)、
  `worker.errors → artifacts`(3)、`infra.db.repositories → artifacts`(4)；并实测
  `campaignlab.worker.ArtifactCommitFailed is campaignlab.infra.artifacts.ArtifactCommitFailed == True`
  （同一个类对象，无重定义、无影子异常），`len(artifacts.__all__) == 11`。
- **R3（`CommittedArtifact` 刻意不给 `record` 字段）**：`JobStore.succeed(artifacts=…)`（`worker/store.py:417-447`）会自己
  `ArtifactRepository.insert`，而 `commit()` 已在同事务内登记过行；若把 `ArtifactRecord` 交回去会撞
  `UNIQUE(workspace_id,kind,sha256)`。故 `CommittedArtifact` 只暴露字段、不暴露可再插入的记录对象，并在其 docstring
  （`artifacts.py:241-245`）写明「正确用法是 `succeed(..., artifacts=())`，或在同一 `BEGIN IMMEDIATE` 内先 `commit()` 再发终态
  UPDATE」。**S2b／S4 接线时必须按此口径**，请编排器在 S2b 派单文里重申。
- **R4（`result_ref` 口径冲突，请裁定）**：design §5 说「`result_ref.id` 必须取回读值（＝artifact id）」，而 A89／design §10 注⑥
  说 M0-04 的断言口径是 `ObjectRef(kind="job", id=<job_id>)`。本卡两者都不发明：`commit()` 只回读并暴露 `artifact_id`
  （`artifacts.py:696-701`），`result_ref` 由 handler／S2b 组装（N8：按 kind 的业务映射归 M1/M2）。集成用例按 **A89** 断言
  `result_json == {"kind":"job","id":<job_id>}`（`tests/integration/jobs/test_artifact_write.py:289`），同时另断言
  「同内容第二次提交回读到同一个 `artifact_id`」（`:673`）以钉住 design §5 的「禁用刚生成的 id」。
- **R5（`verify_same_filesystem()` 的调用点）**：design §5 要求「启动即」调用，但启动路径（`cli.py`／`api/app.py`／
  `worker/deps.get_artifact_writer`）都不在本卡写权内。本实现把它做成显式方法（`artifacts.py:504`），并在 fixture 里调用
  （`tests/integration/jobs/test_artifact_write.py:117`）。**请编排器在 S2b 派单文里点名**：`get_artifact_writer` 必须在返回前
  调一次，否则 rc=2 的启动闸不会生效。
- **R6（`_hash_file` 是否提升为公共件）**：S2b 的 `worker/integrity.py::verify_artifact_index` 需要「按行核 sha256/byte_size」，
  与本模块私有的 `_hash_file`（`artifacts.py:158-175`）同一能力。为不越出 design §9 给 S3 划定的符号面，本卡保持其私有；
  是否提升为公共符号（或由 S2b 自带）请裁定。
- **R7（未改 `infra/__init__.py`）**：按派单文铁律，`src/campaignlab/infra/__init__.py` 属 M0-02 写权，本卡**未改**。
  调用方一律 `from campaignlab.infra.artifacts import ...` 直接导入（本模块不依赖包级 re-export）。
- **R8（两次在飞红灯均非本卡引入，均已自愈，请编排器知悉其共性根因）**：
  ① 开工基线全树 `pytest -q` = `1 failed, 355 passed`，红的是
  `tests/unit/test_state_ledger.py::test_every_md_on_disk_has_ledger_entry`（磁盘上有 `orchestrator/defects/D-037.md`
  而台账尚无对应条目）；单独复跑该文件即 `6 passed`。
  ② 02:21 一次全树复跑 = `1 failed, 415 passed`，红的是
  `tests/unit/test_counts_freshness.py::test_committed_tree_denominator_matches_authoritative_counts`
  （`② md 分母失真：HEAD 提交树实测 122 != 台账 in_scope_md 125`，差值 3 恰为当时仍未跟踪的
  `evidence/M0/ORCHESTRATOR/r10-verification/{00-index.md,commands.md,…}`）；那 3 个文件随 `69db892` 入库后，
  同守护单独复跑 `5 passed`、全树复跑 `416 passed`（rc=0）。
  **共性根因**：台账（`state.json`）与其自身在飞文件的入库时序窗口；两个守护的分母都取**已提交树**，
  本卡 4 个文件全程未跟踪，结构上进不了分母。完整证据与断言原文见 `commands.md` §6.2；
  本卡未修改 `orchestrator/state.json`、`tests/unit/test_state_ledger.py`、`tests/unit/test_counts_freshness.py`。

## 6. 客观量

| 项 | 值 |
|---|---|
| 交付文件 | 4 个新建（1 src + 3 tests）＋ 2 个证据 md |
| `src/campaignlab/infra/artifacts.py` | 837 行 / 35439 B |
| `tests/integration/jobs/test_artifact_write.py` | 731 行 / 30646 B（13 个测试函数） |
| `tests/unit/test_artifacts.py` | 382 行 / 16165 B（20 个测试函数，含 4 组参数化） |
| `tests/integration/jobs/__init__.py` | 1 行 / 108 B（D-035 口径：tests/** 各级都要有 `__init__.py`） |
| 新增用例实跑 | `pytest -q tests/unit/test_artifacts.py tests/integration/jobs` → **60 passed** |
| 全树 | `pytest -q` → **416 passed**（基线 356 collected：355 passed + 1 在飞红；356 + 60 = 416，零回归） |
| `# noqa` / `# type: ignore` | **0 处** |
| 新建 `conftest.py` | **0 个**（D-035／R8-4 教训：不给全树再添同 basename 文件；fixture 全在本模块内） |
| 编码纪律 | 4 个文件均 `bom=False cr=False tail_nl=True`（写盘用 `encoding="utf-8", newline="\n"`） |
| git 写操作 | **0 次**（无 add/commit/push/reset/checkout） |
| 最终复验 | HEAD `69db892` · 2026-11-14T02:24:11+08:00 · 四门 rc=0/0/0/0 · 全树 `416 passed` · 卡内 gate `-k artifact` `13 passed` · A144 三段式 (a)=0/(b)=0/(c)=0（详见 `commands.md` §6） |
