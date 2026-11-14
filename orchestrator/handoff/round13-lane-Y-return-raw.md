# R13 · lane Y（Mendel）原始回执归档

> 归档义务：`resume.checkpoint_R8.lane_raw_report_archive` —— lane 的原始回执必须先落盘归档，
> 再决定关槽或续接。本文件是**原文照录**（含 lane 自报的估算值与 U 项），
> 编排器的独立复验结论见 `orchestrator/state.json -> resume.round13_lane_Y_return.orchestrator_reverification`，
> **不采信本文件的自报值**（`rule_no_trust_handoff_summary_assertions`）。
>
> - lane：Y ｜ nickname：Mendel ｜ agent_id：`01a1d733-80c7-7611-81ef-742720a226ec`
> - 档位：qwen3.8-max / reasoning high ｜ 任务：M0-04 · S2b-2（`worker/integrity.py` + `worker/deps.py`）
> - 派单轮：R13 ｜ 结果：**PARTIAL**（L 循环 2/2 轮用尽，critical=true / slack=0）
> - ★ 本 lane **未按 A168 关槽**：串行链 S2b-2 → S2b-3 → S2c 由同一 max lane 用 `send_input` 续接（禁档位置换）。
> - ★ U-1 被编排器实测判定为**假 BLOCKER**：`tasks["M0-04"].scope_waivers_round7.items[0]`（依 A82）早已给出
>   `infra/db/repositories.py` 的 append-only 豁免，而 S2b-2 派单文**未逐字引用**它 ⇒ 自纠 R13-7，裁定见 A204。

```text
RESULT: PARTIAL — 4 个交付文件 + 3 份证据全部落地，路径限定门禁全绿，14 条正向对照全 RED；唯一缺口 = design §5:52 的 ④⑤ 两项 `jobs.result_json` 判据（两条实现路径都在本 lane 硬禁内 → U-1，未自行发明判据）。

2. 逐子任务（HEAD `6c35aad` / branch `m0-framework`；对账口径 = 派单基线 `51af733` 树 + 本 lane 增量。取证期间 HEAD 被编排器推进两次，4 个交付文件始终未入库、sha256 未变）

| 文件 | numstat +/− | bytes/lines | sha256 前 12 | 关键判据（全实取） |
|---|---|---|---|---|
| `src/campaignlab/worker/integrity.py` | 271/0 | 13421/271 | `2434f4e42fa7` | `__all__` 11 项；`Discrepancy` 8 字段，前 5 = design §5:52 五元组逐字；`ManifestRow` 7 字段；`hash_file` 唯一调用点 `:189`、**无** `hashlib` import（A157 ✓）；非 docstring SQL 违规字面量 **0**；时间类调用 **0** |
| `src/campaignlab/worker/deps.py` | 156/0 | 8779/156 | `1f2be9761afe` | `__all__` 恰 4 项 = design §9；`verify_same_filesystem` 在 `:147`、`return` 在 `:148`（**严格早于** → A156 ✓）；路径片段字面量 **0**；`JobService` 仅 `TYPE_CHECKING`(`:55`) + `importlib` 运行期取（A169 ✓） |
| `tests/unit/test_worker_integrity.py` | 596/0 | 26584/596 | `1cef72d3092d` | `--collect-only` 实取 **19** 用例 |
| `tests/integration/jobs/test_worker_deps.py` | 605/0 | 25342/605 | `f301ab090cae` | `--collect-only` 实取 **18** 用例 |

硬禁自证：`git status --porcelain -- <全部硬禁路径>` 仅命中 1 行 `?? orchestrator/handoff/M2-01-design.md`（lane Z）；`worker/__init__.py` `git diff --quiet HEAD` rc=0（未改），其 `__all__` 30 项不含 `deps`/`integrity`（design:150 ✓）；`infra/**`→`worker` 反向边 AST 实取 = `[]`（A153 ✓），本 lane 正向边 3 条（`worker`→`infra`，合法）；`tests/integration/jobs/conftest.py` 未新增未改；4 文件 `except (` 出现 **0** 次、`ast.parse` 全 OK、无 BOM/无 `\r`/尾 `\n`、`width_max ≤ 100`。**未执行任何 git 写操作。**

3. 自验命令对账表（cwd 一律 `/home/szf/dev/CampaignLab`；rc 由 `subprocess.run().returncode` 采集）

| 命令 | rc 实测 | 关键输出 | 期望 | 判定 |
|---|---|---|---|---|
| `ruff format --check <4 files>` | 0 | `4 files already formatted` | 0 | ✓ |
| `ruff check <4 files>` | 0 | `All checks passed!` | 0 | ✓ |
| `ruff check --select I --diff <4 files>` | 0 | 空 diff（import 序无需重排，实取裁决） | 0 且空 | ✓ |
| `mypy`（全表，LANE-COMMON §3.4/§3.6） | 0 | `Success: no issues found in 86 source files` | 0；86 = HEAD 82 + 本 lane 4 | ✓ |
| `pytest -q <7 个路径限定套件>` | 0 | `169 passed in 35.89s` | 0；169 = 19+18+8+47+40+24+13（逐套件实取） | ✓ |
| `ruff format --check <2 份证据 .md>` | 0 | `2 files already formatted` | 0（A175：作用域含 `.md`） | ✓ |

派单文 §3 写「mypy 80 → 82 + 测试文件数」= 84；实测 **86**，差额 2 = 本 lane 开工后编排器替**其它 lane** 入库的 `.py`（`test_task_cards_complete.py` + `test_orch_harness.py`），与 write_set 无关。**未跑全表 `ruff format --check .` / 全表 `pytest` 当自己判据。**

4. 正向对照证据
- `evidence/M0/M0-04/positive-control-s2b2.log`（48023 B / 750 行 / sha256 `569f5678…f1a5c`）：**14 变异 → 14 RED**，`判定: RED（守护有牙）`×14、`双向核验（改前 == 复原后）: PASS`×14，末尾全量复跑 `169 passed` rc=0；探针全走 `tmp_path`，未落工作树。
- `evidence/M0/M0-04/s2b2-integrity-deps.md`（35034 B / 502 行 / `e039addb…4c28e`）：16 节，符号面·A157·零 SQL·A156·A154·A169·A153·门禁·分母归因全部程序化实取，每处标 `key=`。
- `evidence/M0/M0-04/commands-s2b2.md`（9797 B / 88 行 / `4df37cb7…5852`）：24 行四元组命令表 + driver 清单 + 禁触自证。

5. U-项（问题 + 两候选 + 倾向）
1. **[BLOCKER] `worker/**` 禁一切 SQL 文本（含只读 `SELECT`），`verify_artifact_index` 无法枚举 `jobs` 行 ⇒ §5:52 ④⑤ 判据不可产出。** (a) 放宽冻结守护 `test_worker_package_contains_no_table_dml_literals`，允许 `worker/**` 出现只读 `SELECT`；(b) 给 `JobRepository` 加一个 `list_all`/`list_for_workspace` 读侧访问器。**倾向 (b)**：不破 A81「SQL 只住在 infra」的分层不变量，且与 `ArtifactRepository.list_for_workspace` 同体例；(a) 会让静态守护出现语义例外，日后难收。两文件均在我硬禁内 → 请裁定归属（建议排给 S2c 或新立 FU）。
2. **A155① 已把 `result_ref` 定为 `ObjectRef(kind="job", id=<job_id>)`，id 指向作业行而非制品行 ⇒「指向存在的制品」在 M0-04 口径下恒不成立。** (a) 该判据改为核 `jobs` 行存在性；(b) 改为核 `artifacts` 表里存在同 `(workspace_id, kind=job_result)` 的行。**倾向 (b)**：与 AC-031「数据库和制品摘要一致」的制品侧语义一致，且不依赖 A155 的 ref 形状再变。需与 U-1 同批裁定。
3. **`get_job_service` 里 `factory(store=…)` 的构造参数是按 design §9 推定的**（`JobService` 属 S2c，尚不存在）。(a) 保持 `store=`；(b) 改成位置参数。**倾向 (a)**：design §9 明写「事务边界全在 JobStore」，关键字传参也最不易被签名变更打断。S2c 若不同，改 `deps.py:135` 一行即可。
4. **`deps.py:55` 的 `# type: ignore[import-not-found]` 是给 S2c 的地雷**：`service.py` 落地后 strict 的 `warn_unused_ignores` 会报 `unused-ignore` 使全表 mypy 判红。(a) S2c 同批删掉该 ignore；(b) 我改成 `importlib` + `cast("JobService", …)` 完全去掉 TYPE_CHECKING 导入（注解退化为字符串前向引用）。**倾向 (a)**：保留注解的类型信息量，代价只是 S2c 的一行删除；已两相实测并写进 `deps.py` docstring + 取证 §8。
5. **A156 的 serve 启动路径接线不在我写集**（`cli.py` / `api/app.py` 硬禁，归 FU-30/S4）。(a) S4 在 `cmd_serve` 启动序列里显式调一次 `get_artifact_writer()`；(b) 由 `create_app()` 的 lifespan 调。**倾向 (a)**：`cmd_serve` 已有 `ConfigError → rc=2` 映射，接一行即闭环；(b) 会让 rc=2 退化成 500。本 lane 已证「异常 → rc=2 映射链成立」（含 `test_cli_rc2_mapping_is_specific_to_config_error` 对照），**未**假装已接线。
6. **三个提供器的形参形状**：本 lane 选 `config: AppConfig = Depends(get_config)`（镜像冻结的 `api/deps.py`，就地 `# noqa: B008` ×3）。(a) 保持现状；(b) 改 `Annotated[AppConfig, Depends(get_config)]`。**倾向 (a)**：design §1 冻结的路由形状就是 `svc: JobService = Depends(get_job_service)`，改 `Annotated` 会牵动冻结签名；A47 已确立就地豁免体例。

6. 自报 token（A183：上限按**累计计费**口径判定，max 200k）
- **单轮上下文规模**：≈ **70k** tokens（本续接段末态上下文：系统/派单上下文 ≈6k + 前序模型交接摘要 ≈2.5k + 本轮 ≈30 次工具输出 ≈30k + 本轮自身产出（含 8 段 here-string 生成器与 1 次撞 `os error 206` 的过长命令）≈32k）。
- **跨轮累计计费**：**`over_cap`（远超 200k）**，如实报、不抹平。计量基础：① 本续接段 ≈30 个工具轮，按「每轮重发全上下文」口径 ≈ 30 × 均 45k ≈ **1.3M**；② 前序段（另一模型完成 1628 行交付物 + 14 变异 × 全量复跑 + 多轮测试修补）**无法从 lane 内读取计量表**，按其规模保守估计 **≥1M**；③ 合计 ≈ **2M+ 量级**。我拿不到计费表读数，以上为口径明确的估算而非实测值 —— 若编排器需要精确数，请以平台侧计量为准，本 lane 不做下调。

7. L 循环状态：用 **2** 轮 / 上限 **2** 轮（`critical=true`, `slack=0`）；**未触发 STALLED**。第 1 轮（前序段）交付代码+守护+正向对照并转绿，第 2 轮（本段）首测即全绿、只做证据与回执，**无任何守护需要重修**。诚实披露：第 1 轮内部有多次测试修补迭代（scratch 里 `fix_unit_test{,2,3}.py` / `fix_deps_test.py` / `patch{1,2}.sh` 为证），但均在同一轮内收敛，不构成「同一条守护连续 2 轮修不绿」。本段自身有 3 次生成器缺陷已就地自纠并复跑（`sh()` 元组顺序致 branch/HEAD 渲染成 `0`；§3 表行被追加到文件尾；`ast.Import` 三元组越界 `IndexError`），另撞 1 次 `os error 206` 后改为分块写入 —— 均已在证据里以实测值覆盖，未留过时结论。

8. IN_FLIGHT_CONTAMINATION（禁修，未修）
- `orchestrator/handoff/M2-01-design.md`（lane Z，`??` 未入库）。
- HEAD 两次被编排器推进：`51af733` → `d22b5f6`（lane X FU-33：新增 `tests/unit/test_task_cards_complete.py`、改 `test_task_cards.py`）→ `6c35aad`（lane V FU-35：入库 `tests/unit/test_orch_harness.py` + `evidence/M0/FU-35/**` + `orchestrator/state.json` + 3 份 handoff）。这些把 mypy 全表分母从 80 抬到 82，**不是我的 RED**。
- `tests/unit/test_orch_harness.py` 在本段前半程曾以未入库状态存在于共享工作树，一度使 mypy 全表读到 85→86；现已由编排器入库，我未改一字。
- `orchestrator/handoff/R13-lane-Y-M0-04-S2c.md`（编排器给我的**下一个**任务派单文，已由 `6c35aad` 入库）—— 不属本 lane write_set，未动。
```
