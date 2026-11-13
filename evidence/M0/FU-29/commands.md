# FU-29 · lane W · commands.md

任务：闭合 FU-29 —— 把 `ArtifactCommitFailed` 从 `src/campaignlab/worker/errors.py` 下沉到
`src/campaignlab/domain/errors.py`；`worker/errors.py` 改 import 后 re-export（`__all__` 7 项逐字不变）；
`infra/artifacts.py:54` 改指 `domain.errors`（5 个 raise 点一字不动）；
`tests/unit/test_layering_edges.py` 的 `ALLOWED_INFRA_TO_WORKER_EDGES` 收紧为 `frozenset()`
并重写两条前提失效的用例（保留正向对照，未删任何用例）。

派单文：`orchestrator/handoff/R12-lane-W-FU-29.md`（212 行，已分两段完整读取）。
本文件由 driver `.orch_scratch/w29_cmds.sh` 实跑生成：每条命令原文 + rc + **完整**输出，无手写结论。
cwd 一律 `/home/szf/dev/CampaignLab`（WSL2 ext4），`PATH` 前置 `$HOME/.local/bin`。
同目录另有：`positive-control.log`、`symbols.txt`、`diff-stat.txt`。

## 对账口径

编排器消息（覆盖派单文 §0 快照）给的基线是 **HEAD `ce08975` 的树**：
`ruff format --check` = 229 files、`mypy` = 80 source files、`pytest` = 490 passed。
本 lane 对账口径 = HEAD `ce08975` 的树 + 本 lane write_set 的增量
（**4 个既有文件，零新增 .py**，故 mypy source files 应为 80）。
自验一律路径限定（派单文 §4）；全表由编排器在冻结索引树上复跑。

## 改前基线（在任何编辑之前实跑捕获，driver `.orch_scratch/w29_pre.sh`）

    $ cd /home/szf/dev/CampaignLab && git rev-parse --short HEAD && git rev-list --count HEAD
    ce08975
    92
    $ uv run --no-sync pytest --collect-only -q tests/unit/test_layering_edges.py
    tests/unit/test_layering_edges.py::test_infra_to_worker_edges_are_exactly_the_allowed_whitelist
    tests/unit/test_layering_edges.py::test_artifacts_worker_import_is_absolute_and_submodule_scoped
    tests/unit/test_layering_edges.py::test_parent_package_style_import_would_be_flagged
    tests/unit/test_layering_edges.py::test_worker_import_from_a_non_whitelisted_file_would_be_flagged
    tests/unit/test_layering_edges.py::test_relative_import_cannot_be_used_to_evade_the_whitelist
    tests/unit/test_layering_edges.py::test_scanner_reads_the_ast_not_the_source_text
    tests/unit/test_layering_edges.py::test_the_whitelist_is_a_module_level_constant_ready_for_fu29
    tests/unit/test_layering_edges.py::test_the_whitelist_never_legalises_a_parent_package_edge

    8 tests collected in 0.01s
    rc=0

改前 **8** 条 → 改后必须仍 **8** 条（见下文 L7 实测）。

## ruff isort 行内序实测（派单文 §S2 的期望序与 ruff 实际裁决不一致 → 回执 U-1）

派单文 §S2 要求 `ArtifactCommitFailed, DomainError, PROBLEM_CODES`。实测 ruff 要求的是
`PROBLEM_CODES, ArtifactCommitFailed, DomainError`：`pyproject.toml` 的 `[tool.ruff.lint]`
只设了 `select`/`ignore`，**未设** `[tool.ruff.lint.isort] order-by-type`，ruff 默认 `true`
⇒ 常量先、CamelCase 类次之、小写函数最后。旁证：改前 `worker/errors.py:19` 原文就是
`import PROBLEM_CODES, DomainError`（常量在前），`worker/__init__.py:37` 是
`import JOB_INTERRUPTED, NO_HANDLER, ArtifactCommitFailed, LeaseLost`（同规则）。
本 lane 以 `ruff check` rc=0 为硬门，故采用 ruff 的裁决序。driver `.orch_scratch/w29_isort.sh`：

    $ printf 'from __future__ import annotations\n...import ArtifactCommitFailed, DomainError, PROBLEM_CODES\n...' > /tmp/w29_probe.py
    $ uv run --no-sync ruff check --select I --diff --stdin-filename src/campaignlab/worker/errors.py - < /tmp/w29_probe.py
    --- src/campaignlab/worker/errors.py
    +++ src/campaignlab/worker/errors.py
    @@ -1,4 +1,5 @@
     from __future__ import annotations
    +
     from campaignlab.api.common import Issue, Problem
    -from campaignlab.domain.errors import ArtifactCommitFailed, DomainError, PROBLEM_CODES
    +from campaignlab.domain.errors import PROBLEM_CODES, ArtifactCommitFailed, DomainError
     from campaignlab.domain.ids import new_request_id

    Would fix 1 error.
    rc=1

（探针文件写在 `/tmp`，**未落工作树**，不影响 ruff/mypy 分母。）

## 以下为改完后实跑的命令（driver `.orch_scratch/w29_cmds.sh`，rc 与输出均为实跑产物）
### L0 · 环境

    $ git rev-parse --short HEAD && git rev-parse --abbrev-ref HEAD && git rev-list --count HEAD
    ce08975
    m0-framework
    92
    rc=0
    $ uv --version && python3 --version && date -u +%Y-%m-%dT%H:%M:%SZ
    uv 0.13.7 (x86_64-unknown-linux-gnu)
    Python 3.12.3
    2026-11-13T22:54:25Z

### L1 · 派单文 §4 ruff format --check（路径限定 4 文件）· 期望 rc=0 且 4 files already formatted

    $ uv run --no-sync ruff format --check src/campaignlab/domain/errors.py src/campaignlab/worker/errors.py src/campaignlab/infra/artifacts.py tests/unit/test_layering_edges.py
    4 files already formatted
    rc=0

### L2 · 派单文 §4 ruff check（路径限定 4 文件）· 期望 rc=0 且 All checks passed!

    $ uv run --no-sync ruff check src/campaignlab/domain/errors.py src/campaignlab/worker/errors.py src/campaignlab/infra/artifacts.py tests/unit/test_layering_edges.py
    All checks passed!
    rc=0

### L3 · 派单文 §S3 要求 ruff check --select I（import 块重排后）· 期望 rc=0

    $ uv run --no-sync ruff check --select I src/campaignlab/domain/errors.py src/campaignlab/worker/errors.py src/campaignlab/infra/artifacts.py tests/unit/test_layering_edges.py
    All checks passed!
    rc=0

### L4 · 派单文 §4 mypy（无路径限定口径，全表）· 期望 rc=0；含 lane X 未入库 .py 故为 81

    $ uv run --no-sync mypy
    Success: no issues found in 81 source files
    rc=0

### L5 · mypy 排除 lane X 的未入库文件 · 期望 rc=0 且 80 source files（== HEAD 基线，证明本 lane 零新增 .py）

    $ uv run --no-sync mypy --exclude tests/unit/test_task_cards_complete.py
    Success: no issues found in 80 source files
    rc=0

### L6 · 派单文 §4 pytest（路径限定 7 个守护文件）· 期望 rc=0 且 149 passed，禁含 failed

    $ uv run --no-sync pytest -q tests/unit/test_layering_edges.py tests/unit/test_domain_errors.py tests/unit/test_problem_code_registry.py tests/unit/test_artifacts.py tests/unit/test_worker_runner.py tests/unit/test_job_repository_terminal.py tests/integration/jobs/test_artifact_write.py
    ........................................................................ [ 48%]
    ........................................................................ [ 96%]
    .....                                                                    [100%]
    149 passed in 27.01s
    rc=0

### L7 · 改后 collect-only（对账改前 8 条）· 期望 8 tests collected

    $ uv run --no-sync pytest --collect-only -q tests/unit/test_layering_edges.py
    tests/unit/test_layering_edges.py::test_infra_to_worker_edges_are_exactly_the_allowed_whitelist
    tests/unit/test_layering_edges.py::test_artifacts_has_zero_worker_import_nodes_of_either_kind
    tests/unit/test_layering_edges.py::test_parent_package_style_import_would_be_flagged
    tests/unit/test_layering_edges.py::test_worker_import_from_a_non_whitelisted_file_would_be_flagged
    tests/unit/test_layering_edges.py::test_relative_import_cannot_be_used_to_evade_the_whitelist
    tests/unit/test_layering_edges.py::test_scanner_reads_the_ast_not_the_source_text
    tests/unit/test_layering_edges.py::test_the_whitelist_is_a_module_level_constant_ready_for_fu29
    tests/unit/test_layering_edges.py::test_the_whitelist_never_legalises_a_parent_package_edge
    
    8 tests collected in 0.01s
    rc=0

### L8 · 全表 ruff format --check（污染普查）· HEAD 基线 229，lane X 多 1 个未入库 .py ⇒ 期望 230

    $ uv run --no-sync ruff format --check .
    232 files already formatted
    rc=0

### L9 · 全表 ruff check（污染普查）· 期望 rc=0

    $ uv run --no-sync ruff check .
    All checks passed!
    rc=0

### L10 · 工作树状态 + mypy 可见的未入库 .py 普查（lane X 归属，禁修）

    $ git status --porcelain=v1
     M src/campaignlab/domain/errors.py
     M src/campaignlab/infra/artifacts.py
     M src/campaignlab/worker/errors.py
     M tests/unit/test_layering_edges.py
    ?? evidence/M0/FU-29/
    ?? orchestrator/tasks/M5-03.md
    ?? tests/unit/test_task_cards_complete.py
    rc=0

### L11 · R12-1 写入通道审计：UTF-8 / 无 BOM / 无 CR / 尾 LF / ast.parse / except 元组损坏扫描

    $ python3 /mnt/d/ws/codex_rd/ss_campaignlab/.orch_scratch/w29_audit.py
    src/campaignlab/domain/errors.py | bytes=11269 utf8=OK bom=False cr=0 endsLF=True ast.parse=OK except_tuple_lines=[] R12_1_corrupt_lines=[] -> OK
    src/campaignlab/worker/errors.py | bytes=5568 utf8=OK bom=False cr=0 endsLF=True ast.parse=OK except_tuple_lines=[] R12_1_corrupt_lines=[] -> OK
    src/campaignlab/infra/artifacts.py | bytes=36033 utf8=OK bom=False cr=0 endsLF=True ast.parse=OK except_tuple_lines=[] R12_1_corrupt_lines=[] -> OK
    tests/unit/test_layering_edges.py | bytes=16114 utf8=OK bom=False cr=0 endsLF=True ast.parse=OK except_tuple_lines=[] R12_1_corrupt_lines=[] -> OK
    AUDIT rc=0 (0 == all four changed files clean)
    rc=0

### L12 · 符号面实取（派单文 §4，禁写死）→ 全文另见 symbols.txt

    $ uv run --no-sync python -c import inspect,campaignlab.domain.errors as d,campaignlab.worker.errors as w;print('domain.__all__',len(d.__all__));print('worker.__all__',len(w.__all__),list(w.__all__));print('same_obj',d.ArtifactCommitFailed is w.ArtifactCommitFailed);print('default_code',w.ArtifactCommitFailed.default_code);print('registry',len(d.PROBLEM_CODES))
    domain.__all__ 18
    worker.__all__ 7 ['JOB_INTERRUPTED', 'NO_HANDLER', 'ArtifactCommitFailed', 'LeaseLost', 'interrupted_problem', 'no_handler_problem', 'problem_of']
    same_obj True
    default_code INTERNAL_ERROR
    registry 20
    rc=0

### L13 · 5 个 raise 点与第 13 行 docstring 未被触碰（与 HEAD 逐行对比）→ 全文另见 diff-stat.txt

    $ bash -c diff <(git show HEAD:src/campaignlab/infra/artifacts.py | grep -n 'raise ArtifactCommitFailed(\|^   抛') <(grep -n 'raise ArtifactCommitFailed(\|^   抛' src/campaignlab/infra/artifacts.py) && echo 'IDENTICAL: 5 raise points + line-13 docstring byte-equal to HEAD (line numbers unchanged)'
    IDENTICAL: 5 raise points + line-13 docstring byte-equal to HEAD (line numbers unchanged)
    rc=0

### L14 · diff --numstat（write_set 范围）

    $ git --no-pager diff --numstat -- src/campaignlab/domain/errors.py src/campaignlab/worker/errors.py src/campaignlab/infra/artifacts.py tests/unit/test_layering_edges.py
    26	0	src/campaignlab/domain/errors.py
    1	1	src/campaignlab/infra/artifacts.py
    10	12	src/campaignlab/worker/errors.py
    60	55	tests/unit/test_layering_edges.py
    rc=0

### L15 · 证据目录清单 + sha256

    $ bash -c ls -l evidence/M0/FU-29/ && sha256sum evidence/M0/FU-29/*
    total 32
    -rwxr-xr-x 1 szf szf 11025 Nov 14 06:54 commands.md
    -rw-r--r-- 1 szf szf  1832 Nov 14 06:51 diff-stat.txt
    -rw-r--r-- 1 szf szf  9726 Nov 14 06:49 positive-control.log
    -rw-r--r-- 1 szf szf  3675 Nov 14 06:51 symbols.txt
    373f4ab54625abd01671d8e845237a4c2f913ae37b946c23e37ab26d06592e81  evidence/M0/FU-29/commands.md
    2743a322e95df820fd19dc96559637db6c8b42df8325c6a058a4ebe57912b5bf  evidence/M0/FU-29/diff-stat.txt
    96903ada76591dd9132aa55f4fddbc832af44424bcf9db2244de6f0c78506824  evidence/M0/FU-29/positive-control.log
    7fe7efb4980329fbbf2085f09e3d7a103a389ffda20312cff5aec0a248f9a702  evidence/M0/FU-29/symbols.txt
    rc=0

### L16 · 正向对照（派单文 §3 硬要求，缺此判红）

原始输出全文见同目录 `positive-control.log`（163 行）。做法：把 `infra/artifacts.py`
的 import 临时改回 FU-29 之前的形态 `from campaignlab.worker.errors import ArtifactCommitFailed`
（即 HEAD 的形态），跑 `tests/unit/test_layering_edges.py` 取 RED，再 byte-exact 改回。

    $ grep -n 'MUTATE-OK\|FAILED\|failed,\|pytest_rc_during_mutation\|restored_sha256\|snapshot_sha256\|RESTORE-OK\|passed\|pytest_rc_after_restore' evidence/M0/FU-29/positive-control.log
    23:snapshot_sha256=14515bc840dadb9d77f7f03dee86051abadd0b3a8f72e6aa5f04eee0d6eb7e2f
    25:MUTATE-OK: artifacts.py import reverted to the pre-FU-29 (worker.errors) form
    79:E       AssertionError: 出现未授权的 infra → worker 反向边（FU-29 已把白名单收紧为空集，任何一条都判红）：[('src/campaignlab/infra/artifacts.py', 'campaignlab.worker.errors')]
    82:tests/unit/test_layering_edges.py:180: AssertionError
    105:E       AssertionError: artifacts.py 仍有 from … worker 的反向边（FU-29 后必须是 0 条）：[(54, 'campaignlab.worker.errors', 0)]
    116:tests/unit/test_layering_edges.py:210: AssertionError
    118:FAILED tests/unit/test_layering_edges.py::test_infra_to_worker_edges_are_exactly_the_allowed_whitelist
    119:FAILED tests/unit/test_layering_edges.py::test_artifacts_has_zero_worker_import_nodes_of_either_kind
    120:========================= 2 failed, 6 passed in 0.18s ==========================
    121:pytest_rc_during_mutation=1   (non-zero => the guard really goes red)
    124:restored_sha256=14515bc840dadb9d77f7f03dee86051abadd0b3a8f72e6aa5f04eee0d6eb7e2f
    125:snapshot_sha256=14515bc840dadb9d77f7f03dee86051abadd0b3a8f72e6aa5f04eee0d6eb7e2f
    126:RESTORE-OK: byte-exact
    162:============================== 8 passed in 0.13s ===============================
    163:pytest_rc_after_restore=0

结论：mutation 期间 **2 failed / 6 passed，rc=1**（两条重写用例都真的会红，不是恒绿）；
restore 后 sha256 与改前逐字节相同、**8 passed，rc=0**。

### L17 · 两点自述（禁抹平）

1. **L15 里 `commands.md` 自己的 sha256 是「写到 L15 那一刻」的值**，本段是之后追加的，
   故该 sha256 与本文件最终字节不对应（自指不可避免）。其余三个证据文件
   （`positive-control.log`、`symbols.txt`、`diff-stat.txt`）在 L15 之前已写完，sha256 有效。
2. **本 lane 未跑 `git add` / `git commit`**（派单文 §2、手册 §15.2：one-task-one-commit 归编排器）。
   工作树交付形态见 `diff-stat.txt` 的 `git status --porcelain=v1`：4 个 ` M` + `?? evidence/M0/FU-29/`。
   `?? tests/unit/test_task_cards_complete.py` 属 **lane X**（其声明写集内），本 lane 未读未改未修。
