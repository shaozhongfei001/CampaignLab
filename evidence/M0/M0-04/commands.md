# M0-04 / S3 原子制品写入 · 命令台账（门禁记账四元组：cwd + 命令 + rc + 关键输出）

- lane **S** · 子任务 **S3** · 档位 **qwen3.8-max**（手册 §6.3「事务边界与原子性」强制 max，**未降档**）
- 环境：宿主 Win11 / PowerShell；仓库在 WSL2 `/home/szf/dev/CampaignLab`，分支 `m0-framework`；内核 `6.18.58.1-microsoft-standard-WSL2`；`nproc=16`；`.venv` = cpython 3.14.10（uv）
- **所有命令一律在仓库根 `/home/szf/dev/CampaignLab` 执行**（经 `wsl.exe -e bash -lc`）
- rc 语义：`0`=成功/有匹配、`1`=无匹配、`2`=命令自身错误（本轮无 rc=2）
- 采集窗口：2026-11-14 约 01:50 → 02:25（Asia/Shanghai）
- HEAD：开工 `4a82190`；收工 `eaf02dd`（期间其它 lane 有提交，**本卡 git 写操作 0 次**）
- 交付文件的编码纪律实测（写盘用 `encoding="utf-8", newline="\n"`）：

| 文件 | bytes | lines | BOM | `\r` | 尾换行 |
|---|---|---|---|---|---|
| `src/campaignlab/infra/artifacts.py` | 35439 | 837 | False | False | True |
| `tests/integration/jobs/__init__.py` | 108 | 1 | False | False | True |
| `tests/integration/jobs/test_artifact_write.py` | 30646 | 731 | False | False | True |
| `tests/unit/test_artifacts.py` | 16165 | 382 | False | False | True |
| `evidence/M0/M0-04/s3-artifacts.md` | 18584 | 143 | False | False | True |

---

## 1. 开工基线（改动前实测，用于零回归判定）

| # | cwd | 命令 | rc | 关键输出 |
|---|---|---|---|---|
| B1 | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q 2>&1 \| tail -15` | 管道 rc=0；**pytest 自身 rc=1**（有失败即 1） | `1 failed, 355 passed, 6 warnings in 121.62s`；`FAILED tests/unit/test_state_ledger.py::test_every_md_on_disk_has_ledger_entry` |
| B2 | 同上 | `uv run --no-sync pytest -q tests/unit/test_state_ledger.py 2>&1 \| tail -6` | 管道 rc=0；pytest rc=0 | `6 passed in 0.02s` → B1 的红是**在飞瞬时态**（当时磁盘上有其它 lane 的 `orchestrator/defects/D-037.md` 尚未入台账），非本卡引入 |
| B3 | 同上 | `git status --porcelain \| head -30` | 0 | 在飞条目：`A evidence/M0/ORCHESTRATOR/r9-content-review/*`(5)、`A orchestrator/defects/D-037.md`、`M orchestrator/handoff/M0-03-public-components.md`、`?? evidence/M0/M0-02/_runtime/`、`?? evidence/M0/M0-02/http/`、`?? web/src/components/state/` —— 一律**如实记录、未处理** |
| B4 | 同上 | `stat -c '%d %n' /dev/shm /tmp /home/szf /run` + `/dev/shm` 写探针 | 0 | `65 /dev/shm`、`2096 /tmp`、`2096 /home/szf`、`63 /run`；`PROBE_OK` → 本机存在第二个可写文件系统，④ 的**真实** EXDEV 用例可行（无需 skip） |
| B5 | 同上 | `grep -n '^#\|^##\|^###' orchestrator/handoff/M0-04-design.md` | 0 | 定位 §5「原子制品」= 45-52 行、§7 public_frozen = 69 行、§9-S3 符号面 = 86 行（**只定点读**，未整读 49KB 文件） |
| B6 | 同上 | `sed -n '37,95p' orchestrator/handoff/round8-lane-returns-raw.md` | 0 | §1.2「符号面实取核对表（下次派 M0-04/S3·S4 必读）」：`ArtifactRecord` 7 字段、`ArtifactRepository{get,insert,list_for_workspace}`；§1.4 记 `worker/integrity.py`、`worker/deps.py` 因 `infra/artifacts.py` 缺失顺延为 **S2b**（A110） |

## 2. 收工质量门（四条，逐条 rc=0）

| # | cwd | 命令 | rc | 关键输出 |
|---|---|---|---|---|
| G1 | `/home/szf/dev/CampaignLab` | `uv run --no-sync ruff check .` | **0** | `All checks passed!` |
| G2 | 同上 | `uv run --no-sync ruff format --check .` | **0** | `201 files already formatted`（基线 197 → +4 = 本卡 4 个新 `.py`） |
| G3 | 同上 | `uv run --no-sync mypy`（**全树**，未做路径限定替代） | **0** | `Success: no issues found in 77 source files`（77 − 4 个新文件 = 73，与 G2 的 197→201 同一增量口径） |
| G4 | 同上 | `uv run --no-sync pytest -q`（**全树**，原文命令；rc 由 `&& echo GATE_RC_IS_0 \|\| echo GATE_RC_IS_NONZERO` 直接取证，不经 `$?`） | **0**（`GATE_RC_IS_0`） | `416 passed, 6 warnings in 85.51s` |

**零回归判定**：基线 collected = 356（355 passed + 1 在飞红），收工 collected = 416 = 356 + 本卡新增 60；
失败数 1 → **0**（该红在 B2 已证为其它 lane 的在飞瞬时态，收工时已自行消失）。既有 356 例**零回归**。

## 3. 卡内 gate 与定向复跑

| # | cwd | 命令 | rc | 关键输出 |
|---|---|---|---|---|
| V-art | `/home/szf/dev/CampaignLab` | `uv run --no-sync pytest -q tests/integration/jobs -k artifact`（任务卡 `:22` 原文 gate） | **0** | `13 passed in 11.22s` |
| V-new | 同上 | `uv run --no-sync pytest -q tests/unit/test_artifacts.py tests/integration/jobs` | **0** | `60 passed in 11.07s`（13 集成 + 20 单测函数，参数化展开后合计 60 项） |
| V-exdev | 同上 | `uv run --no-sync pytest -q -rs tests/integration/jobs/test_artifact_write.py::test_artifact_cross_device_layout_is_rejected_at_startup_and_at_commit` | **0** | `1 passed in 1.71s`，`-rs` 无 skip 摘要 → **真实双设备用例已实跑**（`/dev/shm` st_dev=65 vs `/tmp` 2096），非跳过充数 |
| V-self | 同上 | `python3 .orch_tmp/volta_verify_lines.py` + `volta_anchors.py`（证据 file:line 实算复核） | 0 | 首轮查出 12 处引用行号与实测不符 → 全部按 grep/AST 实测值更正后复跑，`LEFTOVERS: []`（禁凭记忆填数，D-012/D-014） |

## 4. 越界自证（A144 **三段式**，收紧 A139 双检；三条均在仓库根执行）

允许前缀正则（本卡写权）：`^(src/campaignlab/infra/artifacts\.py|tests/integration/jobs/|tests/unit/test_artifacts\.py|evidence/M0/M0-04/)`

| # | 命令 | rc | 输出 | 判读 |
|---|---|---|---|---|
| (a) | `git diff --name-only HEAD \| grep -vE '<允许前缀>' \| wc -l` | 0 | `1` | 逐行展开＝`orchestrator/handoff/M0-03b-freeze.md`，**非本卡产出**（F lane／编排器在飞的 tracked 修改）。如实记录、未处理、未回滚 |
| (b) | `git diff --numstat HEAD -- src/campaignlab/infra/artifacts.py tests/integration/jobs tests/unit/test_artifacts.py evidence/M0/M0-04 \| wc -l` | 0 | `0` | 写权内**没有任何 tracked 文件被修改**：4 个文件全是新建未跟踪，故 numstat 无行、`deleted == 0` 平凡成立（added/deleted 两列均无值可记，非「只记 added」） |
| (c) | `git status --porcelain src/campaignlab/infra tests/unit tests/integration evidence/M0 \| grep -vE '<允许前缀>' \| wc -l` | 0 | `1` | 逐行展开＝`?? evidence/M0/ORCHESTRATOR/r10-verification/`，编排器在飞证据目录（落在 scope 根 `evidence/M0` 之下但非本卡产出）。如实记录、未处理 |
| (c-附) | `git status --porcelain \| grep -E '<允许前缀>'` | 0 | `?? src/campaignlab/infra/artifacts.py`、`?? tests/integration/jobs/`、`?? tests/unit/test_artifacts.py`、`?? evidence/M0/M0-04/` | 本卡 footprint 恰好 4 条，全部在允许前缀内 |

**禁改清单触碰情况：否。** `src/campaignlab/infra/__init__.py`（M0-02 写权）、`api/common.py`、`domain/errors.py`（公共冻结件，20 码未扩）、
`worker/**`（S2 交付，只读复用）、`migrations/**`、`contracts/sqlite-v1.sql`（28 表冻结）、`api/jobs.py`（S4）、`spec/**`、`contracts/**`、
`orchestrator/state.json`、`scripts/**` 均未修改（(a)/(b)/(c) 三段式为其机器证据）。

## 5. loop 记账

| 轮次 | 内容 | 结果 |
|---|---|---|
| 1 | 定点读卡/设计/S2 回报 → 摸清 `worker/**`、`infra/db/**` 既有面 → 落 `artifacts.py` + 2 个测试文件 | ruff 9 红（E501/SIM117/SIM102/UP012/RUF022）+ mypy 5 红（func-returns-value/attr-defined/隐式 reexport）→ 同轮修完；pytest 定向 **4 failed / 56 passed** |
| 2 | 4 个失败归因：① 缓冲未 flush 导致暂存件在磁盘上为 0 字节（同时会让跨进程 sweep 的 mtime 保护失效）→ `write()` 每块 `flush()`；② 用例把 `state/campaignlab.db-wal` 当受保护样本，实际是 SQLite 打开库时自行回收残留 WAL → 换 `state/restore-marker.txt` | 定向 **60 passed**；四条质量门全绿（G1-G4） |
| 3（复审轮） | 证据 file:line 逐条实算复核（12 处更正）、A144 三段式自证、编码纪律复验 | `LEFTOVERS: []`；(a)=1/(b)=0/(c)=1 均为他 lane 在飞项 |

`loop_used = 3`（2 个修复轮 + 1 个复审轮；上限 3+1，未超）。**UNRESOLVED = 0 项**；上交裁定 6 项见 `s3-artifacts.md` §5（R1-R6）＋知会 2 项（R7/R8）。
---

## 6. 收工复验（追加式小节；上文 §2/§4 的历史行原样保留，A144「禁静默替换」）

复验时点 **2026-11-14T02:24:11+08:00** · HEAD **`69db892`**（`feat(M0-03b/S2+S3)`，即 §2 采集时的 `eaf02dd` 之后其它 lane 又提交了一次）。

### 6.1 四条质量门在最终 HEAD 上复跑

| # | cwd | 命令 | rc | 关键输出 |
|---|---|---|---|---|
| F1 | `/home/szf/dev/CampaignLab` | `uv run --no-sync ruff check .` | **0**（`G1_RC_0`） | `All checks passed!` |
| F2 | 同上 | `uv run --no-sync ruff format --check .` | **0**（`G2_RC_0`） | `206 files already formatted`（§2 时为 201；+5 为其它 lane 在 `69db892` 入库的 `.py`，非本卡产出） |
| F3 | 同上 | `uv run --no-sync mypy`（全树） | **0**（`G3_RC_0`） | `Success: no issues found in 77 source files`（与 §2 同值：新增 5 个文件不在 `files=["src","tests","scripts"]` 面内） |
| F4 | 同上 | `uv run --no-sync pytest -q`（全树） | **0**（`G4B_RC_0`） | `416 passed, 6 warnings in 88.37s` |
| F5 | 同上 | `uv run --no-sync pytest -q tests/integration/jobs -k artifact` | **0**（`GART_RC_0`） | `13 passed in 6.32s` |

### 6.2 一次在飞瞬时红的完整归因（非本卡引入，已自愈）

02:21:08 的一次全树复跑得到 `1 failed, 415 passed`，红的是
`tests/unit/test_counts_freshness.py::test_committed_tree_denominator_matches_authoritative_counts`，断言原文：

> `② md 分母失真：HEAD 提交树实测 122 != 台账 in_scope_md 125（台账刷新时点=2026-11-14T02:55:00+08:00／原因=Round 10 / M0-03b·S2+S3 复验证据入库后重采样：新增 3 个作用域内 .md（evidence/M0/ORCHESTRATOR/r10-verification/ 的 00-index.md、commands.md、v…）`

归因（三条实证，非推测）：

1. 该守护的分母是 **HEAD 提交树**（`_head_tree_paths()`），本卡 4 个文件当时全部是**未跟踪**新建件，结构上不可能进入分母；
   同文件的 `test_denominator_excludes_every_in_flight_working_tree_file` 正是钉这一点的守护，当轮为 passed。
2. 差异量 **3 个 .md** 与失真原因原文点名的 `evidence/M0/ORCHESTRATOR/r10-verification/{00-index.md,commands.md,…}` 逐项吻合 ——
   即编排器先把台账 `counts.composition.in_scope_md` 刷到 125、而那 3 个 .md 当时仍是 `??` 未跟踪（本卡 §4-(c) 那一轮实测到 `?? evidence/M0/ORCHESTRATOR/r10-verification/`）。
3. 该 3 个文件随 `69db892` 入库后，同一守护在 02:22 单独复跑即 `5 passed`（rc=0），02:23 全树复跑 `416 passed`（rc=0，见 F4）→ **已自愈**，与本卡交付无因果关系。

同型现象在开工基线也出现过一次（§1-B1/B2 的 `test_state_ledger` 红：磁盘有 `D-037.md`、台账未入），两次都属「编排器台账与其自身在飞文件之间的时序窗口」，
本卡未修改 `orchestrator/state.json`、`tests/unit/test_counts_freshness.py`、`tests/unit/test_state_ledger.py` 中的任何一个（§4-(a)/(b) 为机器证据）。

### 6.3 A144 三段式越界自证在最终 HEAD 上复跑

| 段 | 命令 | rc | 输出 |
|---|---|---|---|
| (a) | `git diff --name-only HEAD \| grep -vE '<允许前缀>' \| wc -l` | 0 | **`0`**（§4 时为 1：`orchestrator/handoff/M0-03b-freeze.md` 已随 `69db892` 入库） |
| (b) | `git diff --numstat HEAD -- <本卡写权路径…> \| wc -l` | 0 | **`0`**（写权内无任何 tracked 修改，4 个文件全为新建未跟踪 → `deleted == 0`） |
| (c) | `git status --porcelain src/campaignlab/infra tests/unit tests/integration evidence/M0 \| grep -vE '<允许前缀>' \| wc -l` | 0 | **`0`**（§4 时为 1：`?? evidence/M0/ORCHESTRATOR/r10-verification/` 已入库） |
| 全树 | `git status --porcelain` | 0 | 恰好 4 条，全部属本卡允许前缀：`?? evidence/M0/M0-04/`、`?? src/campaignlab/infra/artifacts.py`、`?? tests/integration/jobs/`、`?? tests/unit/test_artifacts.py` |

三段式在最终 HEAD 上 **(a)=0 / (b)=0 / (c)=0**，工作树除本卡 4 条外无任何其它在飞条目。
