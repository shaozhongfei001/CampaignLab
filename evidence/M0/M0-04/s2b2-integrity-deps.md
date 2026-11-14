# M0-04/S2b-2 取证：`worker/integrity.py` + `worker/deps.py`（lane Y）

本文件由 `.orch_scratch/y_facts.py` / `y_facts2.py` / `y_facts3.sh` / `y_ev.py` 在仓库根
`/home/szf/dev/CampaignLab` 内实测（`inspect` / `ast` / `dataclasses.fields` /
`subprocess.run(...).returncode`）产出的 `/tmp/y_facts.json` 拼装，**无手抄数值**；每处数字
以 `key=` 标出 JSON 键名，可逐条复核。**禁写死符号面计数**（R8-1 / A115）与**禁写死工具裁决**
（R12-4）在此落实为：`__all__`、字段序、签名、行号、import 序、用例分母全部实取。

采集时点：branch `m0-framework`，HEAD `6c35aad`（全 sha `6c35aadb3e2352d9705561c09efd3c74e94a6fb4`）。基线口径 = 派单消息给的
`51af733` 树 + 本 lane write_set 增量（LANE-COMMON §4），**不**拿工作树快照当基线。

---

## 0. write_set 实测（`git diff --no-index --numstat /dev/null <file>`，索引未被触碰）

| 文件 | added | deleted | bytes | lines | sha256 | BOM | CR | 尾 NL | width_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `src/campaignlab/worker/integrity.py` | 271 | 0 | 13421 | 271 | `2434f4e42fa73deb40d6d12bfcc62015afe0bcfdc7e4867b8e94329213f24d3e` | False | False | True | 99 |
| `src/campaignlab/worker/deps.py` | 156 | 0 | 8779 | 156 | `1f2be9761afec23df91ca824b579ce5afd483a5192f864b75f222863bc5b3cd4` | False | False | True | 97 |
| `tests/unit/test_worker_integrity.py` | 596 | 0 | 26584 | 596 | `1cef72d3092dec3315ea6b37e386666827c5cd8439022f3d255699c552a7874b` | False | False | True | 100 |
| `tests/integration/jobs/test_worker_deps.py` | 605 | 0 | 25342 | 605 | `f301ab090caee403d76432961560e9b37b72c53a5fd5337f968ba51851434330` | False | False | True | 100 |

- `git diff --no-index` 的 rc = **1**（该命令「有差异」即返回 1，属正常语义，非失败）。`key=numstat`
- 4 个文件全部 **无 BOM / 无 `\r` / 以 `\n` 结尾**，`width_max ≤ 100`（`pyproject.toml` 的 `line-length=100`）。`key=hygiene`
- 4 个文件在 `git status --porcelain` 里都是 `??`（未入库），本 lane **未执行任何 git 写操作**。`key=status_lines`

### 0.1 R12-1 语法自证（写完 `.py` 立刻 `ast.parse`；此处为本轮复跑）

```
AST OK src/campaignlab/worker/integrity.py
AST OK src/campaignlab/worker/deps.py
AST OK tests/unit/test_worker_integrity.py
AST OK tests/integration/jobs/test_worker_deps.py
```

rc = **0**；`except (` 在 4 个文件里的出现次数合计 = **0**（LANE-COMMON §2 硬禁元组形式）。

---

## 1. `worker/integrity.py` 符号面（design §9 点名 4 个，禁增减／禁改名）

### 1.1 `__all__`（`import campaignlab.worker.integrity` 后取 `module.__all__`）

`key=integrity_all`，`len` = **11**（`key=integrity_all_len`）：

```python
__all__ = [
    "BYTE_SIZE_MISMATCH",
    "MISSING_FILE",
    "PATH_ESCAPE",
    "RESULT_JSON_UNPARSEABLE",
    "RESULT_REF_DANGLING",
    "SHA256_MISMATCH",
    "UNREADABLE",
    "Discrepancy",
    "ManifestRow",
    "manifest_rows",
    "verify_artifact_index",
]
```

| 断言 | 实测 | key |
| --- | --- | --- |
| `__all__` 里每个名字都真实存在于模块 | `True`（缺失清单 = `[]`） | `integrity_missing_from_module` |
| design §9 点名的 4 个符号全在 `__all__` | `True` | `integrity_all` |
| 未进 `__all__` 的公开名（`no_implicit_reexport` 下**不算**再导出，符合 LANE-COMMON §3.5） | 9 项：`ArtifactRecord`, `ArtifactRepository`, `Connection`, `Final`, `Path`, `WorkspaceRepository`, `annotations`, `dataclass`, `hash_file` | `integrity_public_not_in_all` |

### 1.2 两个函数的签名与 file:line（`inspect.signature` / `inspect.getsourcelines`）

| 符号 | signature（逐字） | return annotation | file:line |
| --- | --- | --- | --- |
| `verify_artifact_index` | `(conn: 'Connection', data_dir: 'Path') -> 'list[Discrepancy]'` | `list[Discrepancy]` | `src/campaignlab/worker/integrity.py:215` |
| `manifest_rows` | `(conn: 'Connection') -> 'list[ManifestRow]'` | `list[ManifestRow]` | `src/campaignlab/worker/integrity.py:250` |

`key=integrity_signatures`。派单文要求的 `verify_artifact_index(conn, data_dir) -> list[Discrepancy]` 与实测逐字一致：

| # | 参数 | kind | default | annotation |
| --- | --- | --- | --- | --- |
| 1 | `conn` | `POSITIONAL_OR_KEYWORD` | `<empty>` | `Connection` |
| 2 | `data_dir` | `POSITIONAL_OR_KEYWORD` | `<empty>` | `Path` |

### 1.3 两个 dataclass 的字段面（`dataclasses.fields`，顺序即声明序）

- `Discrepancy`（定义行 `:81`，`frozen=True`、`slots=True`）`key=Discrepancy_fields`：

```python
[
    "workspace_id",
    "artifact_id",
    "relative_path",
    "expected_sha256",
    "actual_sha256",
    "reason",
    "expected_byte_size",
    "actual_byte_size",
]
```

  design §5:52 点名的五元组 `(workspace_id, artifact_id, relative_path, …)` 对应**前五个字段**，实测 = `['workspace_id', 'artifact_id', 'relative_path', 'expected_sha256', 'actual_sha256']`
  （`key=Discrepancy_first_five`），逐字一致 ✓。后三个（`reason` / `expected_byte_size` / `actual_byte_size`）是
  「可独立定位」所必需的归因字段，属 A151「符号面是下限而非上限」的追加。

- `ManifestRow`（定义行 `:100`，`frozen=True`）`key=ManifestRow_fields`：

```python
["workspace_id", "artifact_id", "kind", "sha256", "relative_path", "byte_size", "created_at"]
```

### 1.4 差异形态常量（`Final`，值与名同字）

| 常量 | 值 | design §5:52 点名 | 当前能否产出 |
| --- | --- | --- | --- |
| `MISSING_FILE` | `MISSING_FILE` | ① 存在性 | 是（各有正向对照，见 §15） |
| `SHA256_MISMATCH` | `SHA256_MISMATCH` | ② sha256 | 是（各有正向对照，见 §15） |
| `BYTE_SIZE_MISMATCH` | `BYTE_SIZE_MISMATCH` | ③ byte_size | 是（各有正向对照，见 §15） |
| `RESULT_JSON_UNPARSEABLE` | `RESULT_JSON_UNPARSEABLE` | ④ `result_json` 可解析 | **否** —— 见 §11 诚实披露 + U 项 |
| `RESULT_REF_DANGLING` | `RESULT_REF_DANGLING` | ⑤ 指向存在的制品 | **否** —— 见 §11 诚实披露 + U 项 |
| `PATH_ESCAPE` | `PATH_ESCAPE` | 安全兜底（A151 追加） | 是（各有正向对照，见 §15） |
| `UNREADABLE` | `UNREADABLE` | 安全兜底（A151 追加） | 是（各有正向对照，见 §15） |

`key=reason_constants`。

---

## 2. A157 硬要求：sha256 **复用** `infra/artifacts.py` 的公共 `hash_file`（禁第二份哈希）

| 判据 | 实测 | key |
| --- | --- | --- |
| `hash_file` 的 import 来源 | `campaignlab.infra.artifacts`（行 `:37`） | `integrity_hash_file_imported_from` |
| 模块内 `hash_file` 调用点 | `[[189, 'hash_file']]`（唯一一处，行 `:189`） | `integrity_hash_file_call_sites` |
| 是否 import `hashlib` | **False**（须为 False） | `integrity_imports_hashlib` |
| 其它含 `hash` 字样的调用（第二份实现的特征） | `[]`（须为空） | `integrity_hashlib_call_sites` |
| 模块 docstring 是否写明 A157「同口径」理由 | `{'A157': True, 'hash_file': True, '同口径': True}` | `integrity_module_doc_a157` |

完整 import 面（`ast` 实取：行号 / 形式 / 模块 / 名字）`key=integrity_imports`：

```python
((29, "from", "__future__", "annotations"),)
((31, "from", "dataclasses", "dataclass"),)
((32, "from", "pathlib", "Path"),)
((33, "from", "typing", "Final"),)
((35, "from", "sqlalchemy", "Connection"),)
((37, "from", "campaignlab.infra.artifacts", "hash_file"),)
((38, "from", "campaignlab.infra.db.repositories", "ArtifactRecord"),)
((38, "from", "campaignlab.infra.db.repositories", "ArtifactRepository"),)
((38, "from", "campaignlab.infra.db.repositories", "WorkspaceRepository"),)
```

守护：`test_hashing_goes_through_infra_hash_file`（monkeypatch `hash_file`，断言复核确实走它）＋
`test_integrity_module_has_no_second_hash_implementation`（AST 断言无 `hashlib`、无第二份分块摘要实现）。
正向对照 **M3**（自写第二份哈希）→ RED，见 §15。

---

## 3. 零 SQL 文本（design §4 / A81）——按**冻结守护的原算法**重算

冻结守护 = `tests/unit/test_job_repository_terminal.py::test_worker_package_contains_no_table_dml_literals`
（该文件在本 lane **硬禁**内，未改一字）。其算法：`ast` 取所有 `Constant(str)`，**排除 docstring**
（AST 精确识别模块／类／函数体首条 `Expr(Constant(str))`），排除 `BEGIN IMMEDIATE` / `COMMIT` /
`ROLLBACK` 三条白名单，再用 `\b(INSERT|UPDATE|DELETE|SELECT|CREATE|DROP|ALTER)\b`（IGNORECASE）匹配。

本 lane 用**同一算法**在 `src/campaignlab/worker/` 全包重算：

| 判据 | 实测 | key |
| --- | --- | --- |
| 被扫文件数（分母断言，防 glob 扫空全绿） | **9** 个：`__init__.py`, `capacity.py`, `deps.py`, `errors.py`, `integrity.py`, `leases.py`, `runner.py`, `states.py`, `store.py` | `worker_package_py_files` |
| 全包违规字面量 | `[]`（须为空） | `worker_package_sql_verb_offenders` |
| `integrity.py` 非 docstring 字符串常量数 | 24 | `integrity_nondoc_str_literals` |
| `integrity.py` 违规 | `[]` | `integrity_sql_verb_offenders` |
| `integrity.py` 命中的事务白名单字面量 | `[]`（本模块连事务语句都不需要，故为空） | `integrity_allowed_tx_literals` |
| `deps.py` 非 docstring 字符串常量数 | 10 | `deps_nondoc_str_literals` |
| `deps.py` 违规 | `[]` | `deps_sql_verb_offenders` |

**推论（本 lane 的关键取舍）**：`worker/**` 连**只读** `SELECT` 也禁，故 `verify_artifact_index` 不能自己
发查询枚举 `artifacts` / `jobs`，一律委托既有仓储面：

- 实测调用 = `['list_for_workspace', 'list_page']`（`WorkspaceRepository.list_page` 枚举工作区 → `ArtifactRepository.list_for_workspace` 逐工作区取制品行）`key=integrity_repo_calls`
- 守护：`test_artifact_enumeration_delegates_to_repositories`
- 正向对照 **M5**（在 worker 内就地写 SQL 字面量）→ RED，见 §15

时间口径：本模块**不取系统当前时间**（`tests/unit/test_clock.py` 的全树静态守护），实测时间类调用 =
`[]`（须为空）。`key=integrity_time_calls`

---

## 4. `worker/deps.py` 符号面（design §9 点名 4 个）

`__all__` = `['get_artifact_writer', 'get_job_service', 'get_job_store', 'resolve_data_dir']`，`len` = **4**（`key=deps_all` / `key=deps_all_len`），与 design §9
点名的四个符号**逐字同集**。守护：`test_deps_exports_exactly_the_four_design_symbols`。

| 符号 | signature（逐字，`Depends(...)` 默认值以 `Depends(get_config)` 简写） | return | file:line |
| --- | --- | --- | --- |
| `resolve_data_dir` | `(config: 'AppConfig | None' = None, *, environ: 'Mapping[str, str] | None' = None, home: 'Path | None' = None) -> 'Path'` | `Path` | `src/campaignlab/worker/deps.py:74` |
| `get_job_store` | `(config: 'AppConfig' = Depends(dependency=<function get_config at 0x733761da3530>, use_cache=True, scope=None)) -> 'JobStore'` | `JobStore` | `src/campaignlab/worker/deps.py:103` |
| `get_job_service` | `(config: 'AppConfig' = Depends(dependency=<function get_config at 0x733761da3530>, use_cache=True, scope=None)) -> 'JobService'` | `JobService` | `src/campaignlab/worker/deps.py:120` |
| `get_artifact_writer` | `(config: 'AppConfig' = Depends(dependency=<function get_config at 0x733761da3530>, use_cache=True, scope=None)) -> 'ArtifactWriter'` | `ArtifactWriter` | `src/campaignlab/worker/deps.py:138` |

`key=deps_signatures`（表中已把 `repr` 里含内存地址的 `Depends` 对象替换为等价写法，其余逐字）。
三个提供器的形参默认值是 `Depends(get_config)`，与冻结的 `api/deps.py` 同体例；`# noqa: B008` 出现
**3** 次（A47 / 手册 §9.9 就地豁免，`api/health.py` 同口径）。`key=deps_noqa_b008_count`

完整 import 面（`ast` 实取）`key=deps_imports`：

```python
((37, "from", "__future__", "annotations"),)
((39, "import", "importlib"),)
((40, "from", "collections.abc", "Mapping"),)
((41, "from", "pathlib", "Path"),)
((42, "from", "types", "ModuleType"),)
((43, "from", "typing", "TYPE_CHECKING"),)
((43, "from", "typing", "Final"),)
((43, "from", "typing", "cast"),)
((45, "from", "fastapi", "Depends"),)
((47, "from", "campaignlab.api.deps", "get_config"),)
((48, "from", "campaignlab.application", "build_database_runtime"),)
((49, "from", "campaignlab.config", "AppConfig"),)
((50, "from", "campaignlab.config", "resolve_data_dir"),)
((51, "from", "campaignlab.infra.artifacts", "ArtifactWriter"),)
((52, "from", "campaignlab.worker.store", "JobStore"),)
((55, "from", "campaignlab.worker.service", "JobService"),)
```

import 序由 `ruff check --select I --diff` **实取裁决**：rc = **0**，diff 输出 = ''（空即无需重排）。
`key=gate_ruff_isort_diff`（R12-4：连 import 序这类工具裁决也禁写死）

---

## 5. A156 硬要求①：`get_artifact_writer` 在 `return` **之前**必调 `verify_same_filesystem()`

`ast` 取 `get_artifact_writer` 函数体内所有 `Call` / `Return` 节点并按行号排序（`key=deps_get_artifact_writer_stmt_order`）：

```python
((138, "call:Depends"),)
((146, "call:ArtifactWriter"),)
((146, "call:resolve_data_dir"),)
((147, "call:verify_same_filesystem"),)
((148, "return"),)
```

| 判据 | 实测 | key |
| --- | --- | --- |
| `verify_same_filesystem` 调用行 | **147** | `A156_verify_line` |
| `return` 行 | **148** | `A156_return_line` |
| 调用严格早于返回 | **True** | `A156_verify_before_return` |

顺序不可调换：先 `ArtifactWriter(resolve_data_dir(config))`（构造期校验 `data_dir` 为绝对路径），
再 `verify_same_filesystem()`，通过了才 `return` —— 调用方拿到的一定是「暂存根与终态根同设备」的 writer。
守护：

- `test_get_artifact_writer_calls_verify_same_filesystem_before_returning`（AST 行号序断言，**有牙**）
- `test_get_artifact_writer_returns_a_writer_when_both_roots_share_one_device`（同盘时正常返回，正向）
- `test_get_artifact_writer_raises_config_error_when_st_dev_differs`（monkeypatch `os.stat` 造 `st_dev` 不符 → `config.ConfigError`）
- `test_get_artifact_writer_raises_config_error_on_a_real_second_filesystem`（真实第二文件系统，非替身）

正向对照 **M1**（删掉这一调）→ RED，见 §15。

## 6. A156 硬要求②：`st_dev` 不符 → `config.ConfigError` → **CLI 面 rc=2**

| 环节 | 实测 |
| --- | --- |
| `verify_same_filesystem()` 抛出的异常类型 | `campaignlab.config.ConfigError`（`infra/artifacts.py` 既有行为，**未改**） |
| `cli.cmd_serve` 对 `ConfigError` 的映射 | `except ConfigError: ... return 2`（`cli.py` 既有行为，**在本 lane 硬禁内，未改一字**） |
| 守护用例 | `test_st_dev_mismatch_config_error_maps_to_cli_rc2`：把 `get_artifact_writer` 真实抛出的那个异常对象喂给 `cli.load_config`（monkeypatch），再 `cli.cmd_serve(cli.build_parser().parse_args(["serve"]))`，断言 `rc == 2` 且 stderr 含「同一文件系统」 |
| 对照用例（防「恒 rc=2」假绿） | `test_cli_rc2_mapping_is_specific_to_config_error`：换成非 `ConfigError` 的异常，断言 rc **不是** 2 |

**诚实边界**：serve 启动路径里「真正调用 `get_artifact_writer` 的那一行」属 `cli.py` / `api/app.py`，两者都在
本 lane 硬禁内（归 FU-30 / S4）。故本 lane 证明的是**异常 → rc 的映射链成立**，不是**启动路径已接线**。
已按 A159 报 U 项，未自行改 `cli.py`。`scripts/doctor.sh` 的部署期可见性属 FU-30，同样未碰。

---

## 7. A154 接线口径（二选一，禁第三种）＋ 同一 `(workspace_id,kind,sha256)` 重复登记必红

| 接线 | 守护用例 | 实测断言 |
| --- | --- | --- |
| (a) `store.succeed(..., artifacts=())` | `test_a154_option_a_succeed_with_empty_artifacts_registers_exactly_one_row` | 制品行已由 `ArtifactWriter.commit()` 在同一 `BEGIN IMMEDIATE` 内登记，`succeed` 传空元组 ⇒ `artifacts` 表**恰 1 行** |
| (b) 同一事务内先 `commit()` 再直接发终态谓词 UPDATE | `test_a154_option_b_single_transaction_commit_then_terminal_update` | 同一事务内两步 ⇒ **恰 1 行** ＋ 作业进终态 |
| **禁**的第三种：先 `commit()` 再把 record 交回 `succeed(artifacts=…)` | `test_a154_forbidden_third_wiring_is_red` | 撞 `UNIQUE(workspace_id,kind,sha256)` ⇒ `sqlalchemy.exc.IntegrityError`；事务回滚 ⇒ `artifacts` 仍 **1** 行、作业仍 `RUNNING`（不写出第二个终态，AC-029 同口径） |

正向对照 **M9**（把「恰 1 行」的期望改成 2）→ RED，见 §15。

---

## 8. A169：`worker/service.py` 缺席时本模块仍 import 通过、mypy strict 干净

| 判据 | 实测 | key |
| --- | --- | --- |
| `src/campaignlab/worker/service.py` 是否存在 | **False**（S2c 的交付物，排在本 lane 之后） | `worker_service_exists` |
| `JobService` 只在 `TYPE_CHECKING` 下导入 | `[[55, 'from', 'campaignlab.worker.service', 'JobService']]`（`col_offset > 0` 即在 `if TYPE_CHECKING:` 块内） | `deps_type_checking_imports` |
| 该行原文 | `from campaignlab.worker.service import JobService  # type: ignore[import-not-found]`（行 `:55`） | `deps_type_ignore_code_line` |
| 运行期取模块的方式 | `importlib.import_module` 出现 = **True** | `deps_importlib_used` |
| 缺席时 `import campaignlab.worker.deps` | 成功（`y_facts.py` 内真实 import，rc=0） | — |
| 缺席时调用 `get_job_service(...)` | 抛 `RuntimeError` = **True**，且报错文本指名 S2c = **True**（不静默返回 `None`、不静默造替身） | `get_job_service_raises_when_absent` |
| mypy 全表 | rc = **0**，`Success: no issues found in 86 source files` | `gate_mypy` |

守护：`test_deps_module_is_importable_while_worker_service_is_absent`、`test_get_job_service_names_s2c_until_worker_service_lands`、
`test_get_job_service_lazily_resolves_the_module_once_it_exists`（在 `tmp_path` 里造一个真的 `worker/service.py`
并注入 `sys.path`，证明延迟导入一旦模块出现即生效）、`test_get_job_service_rejects_a_module_without_the_class`
（模块在但类不在 → 报错，不静默）。正向对照 **M7**（改成静默返回 `None`）→ RED，见 §15。

> **给 S2c 的地雷提醒（已写进 `deps.py` 模块 docstring）**：`worker/service.py` 落地时必须**同步删掉**
> `deps.py:55` 的 `# type: ignore[import-not-found]`。mypy strict 开着 `warn_unused_ignores`，
> 留着会报 `error: Unused "type: ignore" comment [unused-ignore]` 使全表 mypy 判红。本 lane 已**两相实测**
> （模块缺席 = `Success`；模块出现 = `unused-ignore`）。另：`get_job_service` 里 `factory(store=...)` 的构造参数
> 是按 design §9「JobService 的方法面 = list_jobs/get_job/cancel_job/retry_job，事务边界全在 JobStore」推定的，
> S2c 若签名不同，改 `deps.py:135` 一行即可（已报 U 项）。

---

## 9. `resolve_data_dir` 禁自拼路径（design §9）

| 判据 | 实测 | key |
| --- | --- | --- |
| `deps.py` 内含 `/` 或 `\\` 的短字符串字面量（路径片段特征） | `[]`（须为空） | `deps_path_fragment_literals` |
| 数据目录委托 | 给了 `config` → `AppConfig.data_dir`；没给 → `campaignlab.config.resolve_data_dir(environ, home)`（其内部再委托 `infra.db.paths` 的 `expand_user` / `default_data_dir`） | `deps_imports` |
| 库位置委托 | `application.build_database_runtime(database_url=config.database_url)`（ADR-005 §2.4 五级链的唯一实现，与 `cli.cmd_serve` 同一入口） | `deps_imports` |

守护：`test_resolve_data_dir_takes_the_config_value_verbatim`、`test_resolve_data_dir_without_config_matches_the_config_module`
（与 `config` 模块同值）、`test_resolve_data_dir_never_self_assembles_paths`（AST 断言无路径片段字面量）、
`test_get_job_store_is_bound_to_the_configured_database`。正向对照 **M4**（自拼路径）→ RED、
**M13**（`get_job_store` 改接内存库、忽略 `config.database_url`）→ RED，见 §15。

---

## 10. A153 分层硬约束（FU-29 刚闭合，禁把它弄回去）

| 判据 | 实测 | key |
| --- | --- | --- |
| `src/campaignlab/infra/**` → `campaignlab.worker` 的**反向边** | `[]`（须为空，对应 `ALLOWED_INFRA_TO_WORKER_EDGES = frozenset()`） | `infra_to_worker_edges` |
| 本 lane 两个新模块的**正向边**（`worker` → `infra`，合法） | 3 条：`[['src/campaignlab/worker/integrity.py', 37, 'campaignlab.infra.artifacts'], ['src/campaignlab/worker/integrity.py', 38, 'campaignlab.infra.db.repositories'], ['src/campaignlab/worker/deps.py', 51, 'campaignlab.infra.artifacts']]` | `my_forward_worker_to_infra_edges` |
| `worker/__init__.py` 是否被改 | **未改**（`git diff --quiet HEAD -- src/campaignlab/worker/__init__.py` rc = 0） | `worker_init_modified_vs_HEAD` |
| `worker/__init__.py` 的 `__all__` 是否含 `deps` / `integrity`（design:150 明禁再导出） | `[]`（须为空；该 `__all__` 共 30 项） | `worker_init_all_has_deps_or_integrity` |
| `worker/__init__.py` 是否 import `worker.deps` / `worker.integrity` | `[[29, '__future__'], [31, 'campaignlab.worker.capacity'], [37, 'campaignlab.worker.errors'], [38, 'campaignlab.worker.leases'], [39, 'campaignlab.worker.runner'], [47, 'campaignlab.worker.states'], [57, 'campaignlab.worker.store']]`（7 条 `ImportFrom`，无 deps / integrity） | `worker_init_imports` |

说明：`worker/__init__.py` 的 docstring 第 24–25 行本来就提到 `integrity.py` / `deps.py`
（`key=worker_init_word_hits` = `[[24, '未在本卡落地的 design §9 符号（``integrity.py``、``deps.py``、``store.list_jobs``）见'], [25, 'M0-04/S2 的回报：前者与 ``deps.get_artifact_writer`` 依赖 ``infra/artifacts.py``']]`），那是**既有说明文字**，既不是导入也不是再导出。

守护：`tests/unit/test_layering_edges.py`（硬禁，未改）**8 用例全绿**，
与派单文 §3 的期望「8 用例全绿」一致。

---

## 11. 诚实披露：design §5:52 的 ④⑤ 两项判据（`jobs.result_json` 侧）当前**不可产出**

design §5:52 要求 `verify_artifact_index` 除制品侧三项外，还要核「`jobs.result_json` 可解析」与
「`result_json` 指向存在的制品」。这两项**没有实现**。原因不是取舍而是写权：

1. 枚举 `jobs` 行需要一条只读查询 → `worker/**` 内**任何** SQL 文本（含只读 `SELECT`）被
   `test_worker_package_contains_no_table_dml_literals` 判红，该守护文件在本 lane **硬禁**内。
2. 或需要一个 `JobRepository` 读侧访问器 → `infra/db/repositories.py` 现有读侧只有「按主键取一行」与
   `list_ready`（只出 `QUEUED`），**没有**全表／按工作区枚举 `jobs` 的访问器；`infra/db/**` 同样**硬禁**。

两条路都要编排器裁定，已按 A159 报 U 项，**未**自行发明判据、**未**用字符串拼接绕过静态守护
（那属 R12-1 同类的静默损坏）。

另：A155① 已把 M0-04 的 `result_ref` 断言面定为 `ObjectRef(kind="job", id=<job_id>)`，即 id 指向**作业行**
而非制品行，故「指向存在的制品」在 M0-04 口径下**恒不成立** —— 该判据到底核 `jobs` 还是核 `artifacts`，
需与上一条一并裁定（同一 U 项内）。

**披露不是口头承诺，是有牙的**：

- `verify_artifact_index` 的 docstring 里带 `.. warning::` 段，实测包含 `{'RESULT_JSON_UNPARSEABLE': True, 'RESULT_REF_DANGLING': True, '尚未产出': True, 'U 项': True, 'A155': True}`（`key=integrity_doc_disclosure`）。
- 守护 `test_jobs_side_reasons_are_declared_but_not_yet_produced`：AST 断言两个常量在模块里**各只出现一次**
  （定义处），且 docstring 含「尚未产出」＋两个常量名 —— 将来谁真实现了 jobs 侧（常量出现第二处引用），
  或谁把披露文字删了，都会立刻判红，防「声明七个 reason、实际只产五个」被后来者静默当作已全覆盖。
- 正向对照 **M6**（删掉缺口披露，把未实现说成已覆盖）→ RED、**M2**（`verify_artifact_index` 恒返回空表）
  → RED，见 §15。

---

## 12. 门禁实测（一律路径限定；rc 由 `subprocess.run(...).returncode` 采集）

| # | 命令（cwd = `/home/szf/dev/CampaignLab`） | rc | 关键输出 | 期望 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `uv run --no-sync ruff format --check <4 files>` | **0** | `4 files already formatted` | rc=0 | PASS |
| 2 | `uv run --no-sync ruff check <4 files>` | **0** | `All checks passed!` | rc=0 | PASS |
| 3 | `uv run --no-sync ruff check --select I --diff <4 files>` | **0** | `(空 diff)` | rc=0 且 diff 为空 | PASS |
| 4 | `uv run --no-sync mypy`（全表） | **0** | `Success: no issues found in 86 source files` | rc=0；source files = HEAD 82 + 本 lane 4 = 86 | PASS |
| 5 | `uv run --no-sync pytest -q <7 个路径限定套件>` | **0** | `169 passed in 35.89s` | rc=0，全绿 | PASS |

`key=gate_ruff_format` / `gate_ruff_check` / `gate_ruff_isort_diff` / `gate_mypy` / `gate_pytest_scoped`。
**禁**跑全表 `ruff format --check .` / 全表 `pytest` 当自己的判据（LANE-COMMON §4）——全表由编排器在冻结索引树上复跑。

### 12.1 mypy 分母归因（逐项实取，禁写死）

| 项 | 实测 | key |
| --- | --- | --- |
| `51af733`（派单基线）树内 `src`+`tests`+`scripts` 的 `.py` 数 | **80** | `py_count_51af733` |
| 当前 HEAD `6c35aad` 树内同口径 `.py` 数 | **82** | `py_count_head` |
| 工作树内同口径 `.py` 数（`find`，含未入库） | **86** | `worktree_py_count` |
| 工作树里未入库（`??`）的 `.py` | ['src/campaignlab/worker/deps.py', 'src/campaignlab/worker/integrity.py', 'tests/integration/jobs/test_worker_deps.py', 'tests/unit/test_worker_integrity.py'] | `untracked_py` |
| `51af733` → HEAD `6c35aad` 期间**其它 lane** 入库的 `.py` | ['A\ttests/unit/test_orch_harness.py', 'M\ttests/unit/test_task_cards.py', 'A\ttests/unit/test_task_cards_complete.py'] | `head_vs_base_py` |
| 本 lane write_set 新增 | **+4**（`worker/integrity.py`、`worker/deps.py`、`test_worker_integrity.py`、`test_worker_deps.py`） | `status_lines` |
| 合计 = mypy 报告的 source files | **86** ✓（HEAD 82 + 本 lane 4 = 86；未入库的非本 lane `.py` = 0 个） | `gate_mypy` |

派单文 §3 写的「80 → 82（你新增 2 个 `src/` 下 .py）+ 你的测试文件数」= 80 + 2 + 2 = **84**；实测 **86**。差额
**2** 全部来自本 lane 开工后编排器替**其它 lane** 入库的 `.py`（`key=head_vs_base_py`：lane X 的
`test_task_cards_complete.py` ＋ lane V 的 `test_orch_harness.py`），与本 lane write_set 无关；本 lane 开工时 HEAD 为
`51af733`，取证期间被推进到 `6c35aad`，4 个交付文件始终是未入库状态、sha256 未变（见 §0）。
LANE-COMMON §3.6：本 lane 新增了与既有测试同目录家族的新文件，故跑的是**全树** mypy（上表第 4 行即全表口径，
rc=0），`rule_full_tree_mypy_on_basename_collision` 已满足；`tests/integration/jobs/conftest.py` **未新增、未修改**
（`key=hard_deny_status_lines` 里无该路径）。

### 12.2 用例分母（`pytest -q --collect-only` 逐套件实取）

| 套件 | collected | 归属 |
| --- | --- | --- |
| `tests/unit/test_worker_integrity.py` | **19** | **本 lane 新建** |
| `tests/integration/jobs/test_worker_deps.py` | **18** | **本 lane 新建** |
| `tests/unit/test_layering_edges.py` | **8** | 既有（硬禁，未改一字） |
| `tests/unit/test_artifacts.py` | **47** | 既有（硬禁，未改一字） |
| `tests/unit/test_worker_runner.py` | **40** | 既有（硬禁，未改一字） |
| `tests/unit/test_job_repository_terminal.py` | **24** | 既有（硬禁，未改一字） |
| `tests/integration/jobs/test_artifact_write.py` | **13** | 既有（硬禁，未改一字） |
| **合计** | **169** | 与 §12 第 5 行的 `169 passed in 35.89s` 一致 ✓ |

---

## 13. 硬禁自证（write_set 之外的路径一字未动）

`git status --porcelain -- <每条硬禁路径>` 的全部输出（`key=hard_deny_status_lines`）：

```
?? orchestrator/handoff/M2-01-design.md
```

命中项共 **1** 行，逐行都以 `??`（未入库）开头且**全部**落在 `orchestrator/handoff/`
（归编排器／其它 lane，属 `IN_FLIGHT_CONTAMINATION`）—— 本 lane 未处理、未修改、未删除。
`src/campaignlab/{infra,api,domain}/**`、`scripts/**`、`migrations/**`、`contracts/**`、`spec/**`、`web/**`、
`docs/**`、`worker/` 既有 7 个模块（`__init__` / `capacity` / `errors` / `leases` / `runner` / `states` / `store`）、
以及 5 个硬禁测试文件 + `tests/integration/jobs/conftest.py` **零命中**。

本 lane **未执行任何 git 写操作**（无 `add` / `commit` / `push` / `checkout` / `reset` / `stash` / `branch`），
未 sudo，未整读 `contracts/openapi.json`（443 KB 活契约，手册 §5.3，只读 `M0-04.slice.json` 切片）。

---

## 14. 差异形态 → 守护用例映射（派单文 §3「逐形态一条正向对照」）

| design §5:52 形态 | reason 常量 | 守护用例 | 状态 |
| --- | --- | --- | --- |
| ① 缺件（`relative_path` 不存在） | `MISSING_FILE` | `test_verify_artifact_index_reports_missing_file` | 已落 |
| ② sha256 不符 | `SHA256_MISMATCH` | `test_verify_artifact_index_reports_sha256_mismatch` | 已落 |
| ③ byte_size 不符 | `BYTE_SIZE_MISMATCH` | `test_verify_artifact_index_reports_byte_size_mismatch` | 已落 |
| ④ `result_json` 不可解析 | `RESULT_JSON_UNPARSEABLE` | `test_jobs_side_reasons_are_declared_but_not_yet_produced`（只钉「已声明＋缺口已披露」） | **判据未落地**，见 §11 + U 项 |
| ⑤ `result_json` 指向不存在的制品 | `RESULT_REF_DANGLING` | 同上 | **判据未落地**，见 §11 + U 项 |
| 追加：路径逃逸（`..` / 绝对路径 / 反斜杠） | `PATH_ESCAPE` | `test_verify_artifact_index_reports_path_escape_without_hashing_outside`（并断言**没有**去 hash 受控目录外的文件） | 已落（A151 追加） |
| 追加：读不出来（权限 / 非文件） | `UNREADABLE` | `test_verify_artifact_index_reports_unreadable_file` | 已落（A151 追加） |
| 追加：全一致时必须回空表 | — | `test_verify_artifact_index_is_empty_when_index_and_files_agree` | 已落 |
| 追加：`data_dir` 必须绝对路径 | — | `test_verify_artifact_index_rejects_relative_data_dir` | 已落 |
| 追加：`Discrepancy` 前五字段 = design 五元组 | — | `test_discrepancy_leading_five_fields_are_the_design_tuple` | 已落 |
| 追加：冻结签名逐字比对 | — | `test_frozen_signatures_match_design_52` | 已落 |
| 追加：`ManifestRow` 字段面冻结 | — | `test_manifest_row_field_surface_is_frozen` | 已落 |
| 追加：7 个 reason 常量全部再导出 | — | `test_all_reason_constants_are_exported` | 已落 |
| 追加：`manifest_rows` 全表 + 排序稳定 | — | `test_manifest_rows_returns_every_artifact_row_sorted` | 已落 |
| 追加：`manifest_rows` 只读索引、**不碰文件系统** | — | `test_manifest_rows_reads_the_index_only_never_the_filesystem` | 已落 |

---

## 15. 正向对照（LANE-COMMON §6：只交绿证据无法区分「守护有效」与「守护恒绿」）

- 原始日志：`evidence/M0/M0-04/positive-control-s2b2.log`（**48023** bytes / **750** 行 / sha256 `569f5678800373be85252d34d9c49435166bc3f44bb6c68e0bd61a82dd9f1a5c`）
- 方法：对 write_set 内 4 个文件逐个施加**单点变异** → 跑目标用例 → 落原始输出 → 从 `/tmp/s2b2-pristine`
  复原 → sha256 **双向核验**（改前快照 == 复原后）→ 末尾全量复验绿。
- 探针一律走 pytest `tmp_path`，**未落工作树**（故 ruff / mypy 分母未被污染）。

| # | 变异（对准的守护） | 判定 | 复原 sha256 双向核验 |
| --- | --- | --- | --- |
| M1 | A156-去掉启动闸（不调 verify_same_filesystem） | **RED（守护有牙）** | **PASS** |
| M2 | integrity-verify 恒返回空表（校验静默失效） | **RED（守护有牙）** | **PASS** |
| M3 | A157-自写第二份哈希实现（不复用 hash_file） | **RED（守护有牙）** | **PASS** |
| M4 | resolve_data_dir-自拼路径（违 design §9 禁自拼） | **RED（守护有牙）** | **PASS** |
| M5 | worker 内就地写 SQL 字面量（违 A81 / design §4） | **RED（守护有牙）** | **PASS** |
| M6 | 删掉 jobs 侧缺口披露（把未实现说成已覆盖） | **RED（守护有牙）** | **PASS** |
| M7 | A169-静默返回 None 而不指名 S2c | **RED（守护有牙）** | **PASS** |
| M8 | manifest_rows-枚举恒空（备份清单静默变空） | **RED（守护有牙）** | **PASS** |
| M9 | A154-把「恰 1 行」的期望改成 2 | **RED（守护有牙）** | **PASS** |
| M10 | 把 MISSING_FILE 移出 __all__（no_implicit_reexport 退导出） | **RED（守护有牙）** | **PASS** |
| M11 | 打乱 Discrepancy 字段序（违 design §5:52 五元组） | **RED（守护有牙）** | **PASS** |
| M12 | 改 verify_artifact_index 的返回注解（违冻结签名） | **RED（守护有牙）** | **PASS** |
| M13 | get_job_store 改接内存库（忽略 config.database_url） | **RED（守护有牙）** | **PASS** |
| M14 | 去掉 data_dir 绝对路径前置校验 | **RED（守护有牙）** | **PASS** |

上表 14 行的编号与标题由 `re.finditer(r'(?m)^## (M\d+)-(.+)$', <日志原文>)` **实取**，非手抄；
日志里 `## M` 段落数 = 14，`判定: RED（守护有牙）` 出现次数 = 14，
`双向核验（改前 == 复原后）: PASS` 出现次数 = 14，三者相等 ⇒ 无一条变异后仍绿、无一条复原失败。

日志末行原文：`变异 14 条，制造出 RED 14 条，复原 sha256 双向核验全通过 = True`。
复原后逐文件复核：日志末段 `match_before=True` 出现 **4** 次（= 4 个交付文件各一次，改前快照 == 复原后），
4 个 sha256 与 §0 表格逐字相同；末尾全量复跑 7 个路径限定套件 → `169 passed in 35.89s`、rc = **0**。

---

## 16. 未决项索引（详情见回执 `U-项` 段）

1. `worker/**` 的 `SELECT` 禁令 vs `verify_artifact_index` 的 jobs 侧判据（**BLOCKER**，需编排器裁定）
2. A155① 的 `result_ref.id = job_id` 使「指向存在的制品」恒不成立 —— 核 `jobs` 还是核 `artifacts`
3. `get_job_service` 里 `factory(store=...)` 的构造参数（S2c 确认，改 `deps.py:135` 一行）
4. `deps.py:55` 的 `# type: ignore[import-not-found]` 地雷（S2c 落地时必须同步删）
5. A156 的 serve 启动路径接线（`cli.py` / `api/app.py`，归 FU-30 / S4）
6. 三个提供器的形参形状（本 lane 选 `config: AppConfig = Depends(get_config)`，与冻结 `api/deps.py` 同体例）

