# R12 · Lane W · FU-29 派单文（档位 qwen3.8-max / reasoning high）

> 权威条款：`docs/delivery/LONG-HORIZON-ORCHESTRATION.md` v1.7（§1 不变量、§4.1 L 循环、
> §5.3 大文件抽取、§6.3 硬规则、§13.2 写入通道铁律、§15.2 提交纪律、§15.5 成本账本）。
> 本文是 lane W 的**唯一**上下文包。禁止读取本文 §2 write_set 之外的目录去「找线索」。

## 0. 基线三行（as-of HEAD `cf39d64`，branch `m0-framework`，编排器 2026-11-14 实测于冻结索引树）

| 门 | 命令（cwd=仓库根，WSL 内） | 期望 |
|---|---|---|
| ruff format | `uv run --no-sync ruff format --check .` | rc=0 且输出 `225 files already formatted`，禁含 `would be reformatted` |
| ruff check | `uv run --no-sync ruff check .` | rc=0 且含 `All checks passed!` |
| mypy | `uv run --no-sync mypy` | rc=0 且含 `Success: no issues found in 79 source files` |
| pytest | `uv run --no-sync pytest -q` | rc=0 且 `490 passed`，禁含 `failed` |

**在飞污染警告**：本轮同时有 lane X（FU-33，写 `orchestrator/tasks/**` 与
`tests/unit/test_task_cards*.py`）在飞。你在工作树上跑全表门禁**必然**看到它的半成品
（多出的 .md/.py 会抬高 ruff 分母、可能撞红卡片守护）。这是 IN_FLIGHT_CONTAMINATION，
**不是你的 RED，也不许你去修它**（A161：复验方对在飞面禁写）。
你的自验一律用**路径限定**命令（见 §4），全表门禁由编排器在冻结索引树上复跑。

## 1. 任务：闭合 FU-29 —— 消除全仓唯一一条 `infra → worker` 反向分层边

**背景裁定 A153**：`src/campaignlab/infra/artifacts.py:54` 有
`from campaignlab.worker.errors import ArtifactCommitFailed`。`infra` 是 HTTP 进程与 worker
进程共用底座，`worker` 只该被 worker 进程拉起 —— 这条边是**分层倒置**。A153 当时追认现状
（因 `worker/errors.py:55-56` 明写「供 S3 落地后直接复用」，属设计缺陷而非实现缺陷），
立 FU-29 限期修正，并落地 `tests/unit/test_layering_edges.py` 白名单守护，
**白名单做成模块级常量就是为了让你这次只改一行即可收紧为空集**。

**trigger 已到期**：FU-29 必须在 wave3（M1-01 / M2-01）派单前闭合。你是关键路径首棒。

### 1.1 四步改动（顺序即依赖，禁跳步）

**S1 — 下沉类定义**：把 `ArtifactCommitFailed` 的**类定义**从
`src/campaignlab/worker/errors.py:51-59` 搬到 `src/campaignlab/domain/errors.py`。
- `default_code: ClassVar[str] = "INTERNAL_ERROR"` **逐字保留**（该 code 已在
  `PROBLEM_CODES` 20 码注册表内，**禁**扩注册表）。
- docstring 语义保留；原文那句「本卡不实现制品写入（`infra/artifacts.py` 归 M0-04/S3），
  此处只提供 design §9 点名的异常类型，供 S3 落地后直接复用」是 M0-04/S2 的历史语境，
  搬进 domain 后须改写为**当前**事实（S3 已落地、artifacts.py 的 5 个 raise 点是唯一消费者、
  下沉理由是消除 infra→worker 反向边）。改写须在回执里说明，禁静默删语义。
- 插入位置：`domain/errors.py` 现有 13 个 `DomainError` 子类之后（`InternalFailure` 在 261 行）。
- `domain/errors.py.__all__` 现 **17 项**（`inspect` 实取为准，禁写死），加入
  `"ArtifactCommitFailed"` 后按**现有字典序**插入 → 18 项。

**S2 — worker 侧改 re-export**：`src/campaignlab/worker/errors.py`
- 删掉类定义，改为从 `campaignlab.domain.errors` 导入。该文件第 19 行已有
  `from campaignlab.domain.errors import PROBLEM_CODES, DomainError` —— 把
  `ArtifactCommitFailed` 并进这一行（注意 ruff `I001` 的行内字典序：
  `ArtifactCommitFailed, DomainError, PROBLEM_CODES`）。
- **`worker/errors.py.__all__` 必须逐字不变**（现 7 项：`JOB_INTERRUPTED`、`NO_HANDLER`、
  `ArtifactCommitFailed`、`LeaseLost`、`interrupted_problem`、`no_handler_problem`、
  `problem_of`；顺序也不得动）。公开符号集不变是本步的验收判据。
- `LeaseLost` **留在 worker**，不下沉（它是 worker 侧的正常信号，design §4「静默放弃本次
  尝试」，不属 domain 通用错）。
- **反直觉点（必踩）**：mypy 在 strict 下开 `no_implicit_reexport`。「import 进来但没进
  `__all__`」的名字**不算**再导出，下游 `from campaignlab.worker.errors import
  ArtifactCommitFailed` 会判 mypy 错。本项目靠 `__all__` 里已列该名来满足显式再导出 ——
  所以 §S2 的「`__all__` 逐字不变」不是形式要求，是**功能要求**。改完必须实跑 mypy 验证。

**S3 — 消费端改指 domain**：`src/campaignlab/infra/artifacts.py:54`
- 改为 `from campaignlab.domain.errors import ArtifactCommitFailed`。
- **5 个 raise 点（626 / 637 / 642 / 648 / 703 行）一字不改**；第 13 行 docstring 里的
  `ArtifactCommitFailed` 提及也不改。
- **反直觉点**：删掉 `worker.errors` 那行后，import 块要重排（ruff `I001`）。现有块是
  `clock` → `config` → `domain.ids` → `infra.db.repositories` → `worker.errors`；
  新块须为 `clock` → `config` → **`domain.errors`** → `domain.ids` → `infra.db.repositories`
  （`domain.errors` 排在 `domain.ids` **之前**）。改完跑 `ruff check --select I`。

**S4 — 收紧守护**：`tests/unit/test_layering_edges.py`（该文件 289 行，已在你的写集内）
- `ALLOWED_INFRA_TO_WORKER_EDGES`（48-50 行）→ `frozenset()`。**必须保持「模块顶层恰好
  一次 `AnnAssign`」**，因为 `test_the_whitelist_is_a_module_level_constant_ready_for_fu29`
  （264-276 行）用 AST 数声明次数 == 1。写成 `frozenset()` 即可，禁改成
  `ALLOWED_... = frozenset({})` 之外的形态（例如禁改成函数调用结果、禁挪进函数体）。
- `test_infra_to_worker_edges_are_exactly_the_allowed_whitelist`（167-183 行）：
  第 183 行 `assert located, "扫描器一条边都没扫到…"` 在收紧后**必然红**（工作树里已无边）。
  把它替换为**正向对照**：用文件内已有的 `_probe_repo(tmp_path, …)` 造一棵含
  `from campaignlab.worker.errors import ArtifactCommitFailed` 的探针树，断言扫描器
  **仍能**扫出这条边 —— 即「实测为空集」是因为**真没边**，不是因为扫描器坏了。
  这条用例因此需要 `tmp_path` fixture 参数（原本没有）。**禁**把它删掉了事：删掉等于
  让守护失去反假绿能力（手册 15.4 / A159）。
- `test_artifacts_worker_import_is_absolute_and_submodule_scoped`（186-216 行）：整条用例的
  前提是「恰有 1 条边」（196 行 `assert len(nodes) == 1`），收紧后前提消失。
  **重写**为断言 `artifacts.py` 里 worker 导入节点数 == **0**（`ImportFrom` 与 `Import`
  两种节点都要覆盖，保留原 209-216 行对 `ast.Import` 的检查思路），用例名与 docstring 同步
  改为「零反向边」语义。
- 其余用例**一律不动**：`test_parent_package_style_import_would_be_flagged`（219）、
  `test_worker_import_from_a_non_whitelisted_file_would_be_flagged`（229）、
  `test_relative_import_cannot_be_used_to_evade_the_whitelist`（237）、
  `test_scanner_reads_the_ast_not_the_source_text`（255）、
  `test_the_whitelist_is_a_module_level_constant_ready_for_fu29`（264）、
  `test_the_whitelist_never_legalises_a_parent_package_edge`（279）—— 它们都**不写死**白名单
  内容，收紧后自动继续成立；若你发现某条红了，说明你的 S1–S3 做错了，回去改实现而不是改用例。
- 模块 docstring（1-26 行）与 44-47 行注释描述的是「A153 现状 + FU-29 待办」，须改写为
  「FU-29 已闭合、白名单为空集、任何 infra→worker 边都判红」的当前事实。

## 2. 写权（write_set）与硬禁（hard_deny）

**只许写这些**：
```
src/campaignlab/domain/errors.py
src/campaignlab/worker/errors.py
src/campaignlab/infra/artifacts.py          # 仅第 54 行那个 import；raise 点禁动
tests/unit/test_layering_edges.py
evidence/M0/FU-29/**                        # 你的取证目录，自建
```
**硬禁（写一个即判越界、整条 lane 判红）**：
```
src/campaignlab/api/common.py               # test_domain_errors.py:165-166 钉死 len(__all__)==51
tests/unit/test_domain_errors.py            # :94-109 是 13 项硬编码字典；:165 钉死 51
tests/unit/test_artifacts.py                # :289/:299-310 用 AST 读 artifacts.__all__ + 多出项白名单
tests/unit/test_problem_code_registry.py    # :36 钉死 len(PROBLEM_CODES)==20
src/campaignlab/worker/__init__.py          # :37 import + :70 __all__，靠 re-export 自动继续工作
tests/integration/jobs/test_artifact_write.py  # :56 从 worker.errors 导入，靠 re-export 自动继续工作
orchestrator/**（含 state.json、tasks/、defects/、handoff/）  # 台账只归编排器写
spec/**  contracts/**  web/**  prototype/**  scripts/**       # §1 不变量
```
**禁自行提交**：你不跑 `git add` / `git commit`。改完 + 自验绿 + 落证据 + 写回执即止，
由编排器复验后单独提交（one-task-one-commit，§15.2）。

## 3. 必须保持绿的守护（逐条给期望值 + 正向对照要求）

| 守护 | 期望 | 你该怎么验 |
|---|---|---|
| `tests/unit/test_layering_edges.py` | 全绿，且**用例数不得减少**（改前 8 条 → 改后仍 8 条） | 改前先 `--collect-only -q` 记下条数，改后再记一次，两者相等 |
| `tests/unit/test_domain_errors.py` | 全绿，**你没改它** | 路径限定实跑；它红 = 你的 S1/S2 破坏了 re-export 或误扩了注册表 |
| `tests/unit/test_problem_code_registry.py` | 全绿（`len(PROBLEM_CODES)==20`） | 路径限定实跑 |
| `tests/unit/test_artifacts.py` | 全绿 | 路径限定实跑 |
| `tests/unit/test_worker_runner.py` / `test_job_repository_terminal.py` | 全绿（都从 `worker.errors` 导入） | 路径限定实跑 |
| `tests/integration/jobs/test_artifact_write.py` | 全绿（`:56` 从 `worker.errors` 导入 `ArtifactCommitFailed`） | 路径限定实跑 |
| mypy 全表 | rc=0；source files 数 **79 → 79**（你**不新增** .py 文件，只改 4 个既有文件） | `uv run --no-sync mypy` |

**正向对照（手册 15.4，缺此判红）**：你必须**主动制造一次 RED 再改回来**，证明守护真的能红：
把 `infra/artifacts.py:54` 临时改回 `from campaignlab.worker.errors import ArtifactCommitFailed`，
跑 `tests/unit/test_layering_edges.py`，确认 `test_infra_to_worker_edges_are_exactly_the_allowed_whitelist`
**判红**，然后把 RED 输出（含用例名与断言文本）抄进 `evidence/M0/FU-29/positive-control.log`，
再改回正确形态并复验绿。禁只交绿证据 —— 只交绿无法区分「守护有效」与「守护恒绿」。

## 4. 自验命令（一律路径限定，避开在飞 lane X）

```bash
cd /home/szf/dev/CampaignLab
export PATH="$HOME/.local/bin:$PATH"
uv run --no-sync ruff format --check src/campaignlab/domain/errors.py \
  src/campaignlab/worker/errors.py src/campaignlab/infra/artifacts.py \
  tests/unit/test_layering_edges.py
uv run --no-sync ruff check src/campaignlab/domain/errors.py \
  src/campaignlab/worker/errors.py src/campaignlab/infra/artifacts.py \
  tests/unit/test_layering_edges.py
uv run --no-sync mypy                      # mypy 无路径限定口径，全表跑；79 是期望值
uv run --no-sync pytest -q tests/unit/test_layering_edges.py \
  tests/unit/test_domain_errors.py tests/unit/test_problem_code_registry.py \
  tests/unit/test_artifacts.py tests/unit/test_worker_runner.py \
  tests/unit/test_job_repository_terminal.py tests/integration/jobs/test_artifact_write.py
```
`uv run --no-sync mypy` 全表会扫到 lane X 的未入库 .py，可能报它的错 ——
若报错文件**不在你的 write_set 内**，记为 IN_FLIGHT_CONTAMINATION 写进回执，禁去修。

**符号面实取（禁写死，R8-1/A115）**：改完用下面这段把实际值抄进证据，
禁在回执里写「应该是 18」这类推断值：
```bash
uv run --no-sync python -c "import inspect,campaignlab.domain.errors as d,campaignlab.worker.errors as w;print('domain.__all__',len(d.__all__));print('worker.__all__',len(w.__all__),list(w.__all__));print('same_obj',d.ArtifactCommitFailed is w.ArtifactCommitFailed);print('default_code',w.ArtifactCommitFailed.default_code);print('registry',len(d.PROBLEM_CODES))"
```
期望：`same_obj True`、`default_code INTERNAL_ERROR`、`registry 20`、`worker.__all__` 7 项逐字不变。

## 5. 写入通道铁律（§13.2 / §13.2.2 —— 违反必然静默损坏）

宿主是 Windows 11 PowerShell，仓库在 WSL2 ext4。**不要**用
`wsl.exe -e bash -lc "…"` 传含 `$`、`$(…)`、反引号或嵌套双引号的命令 —— PowerShell 会先插值，
实测会产生 `bash: unexpected EOF`、参数被吃掉、以及**字符级静默损坏**。

正确姿势（三步，每次写文件都走这条）：
1. PowerShell 单引号 here-string 装文本：`$txt = (@'` … `'@) -replace "\`r\`n","\`n"`
   （`-replace` 把 CRLF 归一成 LF；仓库文件必须 **UTF-8 / 无 BOM / 无 `\r` / 以 `\n` 结尾**）。
2. `[System.IO.File]::WriteAllText($path,$txt,(New-Object System.Text.UTF8Encoding($false)))`
   写到 `D:\ws\codex_rd\ss_campaignlab\.orch_scratch\<name>`。
3. `wsl.exe -e bash /mnt/d/ws/codex_rd/ss_campaignlab/.orch_scratch/<driver>.sh`（**bash 后接文件路径，
   不用 `-lc` 传内联脚本**），由 driver 把文件 `cp` 进仓库并跑校验。

**R12-1（本轮新立的自我更正，务必遵守）**：本通道实测会把 Python 的
`except (A, B):` 元组形式损坏成 `except A, B:`（Python 3 语法错误）。
因此：① 你写的 Python **禁用** `except (A, B):`，一律拆成两个 `except` 子句；
② 每次写完 .py **必须**立刻 `python3 -m py_compile <file>` 或
`python3 -c "import ast,pathlib;ast.parse(pathlib.Path('<file>').read_text())"` 自证语法，
禁写完就跑测试（语法损坏会让测试结果完全不可信）。

**命令过长会撞 Windows `os error 206`**（命令行长度上限）：拆成「数据文件 + 小 driver」。

## 6. 产出与回执

**证据落点** `evidence/M0/FU-29/`（自建目录）：
- `commands.md` —— 你实跑的每条命令原文 + rc + 关键输出行（禁只写结论）。
- `positive-control.log` —— §3 要求的「主动制造 RED」的原始输出。
- `symbols.txt` —— §4 的 `inspect` 实取结果原文。
- `diff-stat.txt` —— `git diff --numstat -- <你的 write_set>` 原文。

**回执格式**（最终消息，纯文本，≤ 90 行）：
1. `RESULT: PASS | PARTIAL | STALLED`
2. 四步（S1–S4）逐项：改了哪个文件、numstat、关键判据实测值
3. §4 全部命令的 rc 与期望值对账表（含正向对照 RED 证据路径）
4. `U-项`：任何你无法从任务卡/派单文确定的事，**如实上报禁猜**（A159）。
   每条写成「问题 + 你的两个候选方案 + 你倾向哪个及理由」。
5. `自报 token`：本轮你消耗的估算 token 数（§15.5 要入账；max 单任务上限 200k，
   超限即停并如实报 `over_cap`，禁把越限说成合规）。
6. `IN_FLIGHT_CONTAMINATION`：你观察到的、归属 lane X 的红/多余文件清单（禁修）。

## 7. L 循环上限（§4.1 + §15.6）

你在**关键路径**上（`critical=true`，slack=0），L 循环上限**收紧为 2 轮**：
同一条守护连续 2 轮修不绿，**立即停手**写 `STALLED` 回执 + BLOCKER 描述 +
一个「缩小范围」的降级交付选项交编排器裁定。禁第 3 轮硬试。
