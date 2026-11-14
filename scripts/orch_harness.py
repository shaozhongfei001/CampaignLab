"""编排器提交工装（R12 重建；取代宿主重置中丢失的 .orch_tmp/lane_commit_lib.py + msg_commit_lib.py）。

设计约束（全部来自 docs/delivery/LONG-HORIZON-ORCHESTRATION.md 与 state.json 的
resume.gate_measurement_caliber）：

* rule_commit_gates_measured_on_frozen_index_tree（R11-3）：同一工作树里可能有多条 lane 在飞，
  在工作树上跑门禁会把他人半成品算进分母/判红。因此门禁一律跑在
  ``git checkout-index -a -f --prefix=<scratch>/`` 出来的**冻结索引树**上。
* rule_double_judge：rc 与输出文本必须双判，任一不符即判红。
* rule_no_trust_handoff_summary_assertions：一切计数实测，禁写死。
* GIT_ENV_IGNORES：两个守护断言「repo-root == HEAD 树」，在冻结树里必然红，
  故从冻结 pytest 排除，改用真实工作树的 ``--collect-only`` 静态计数补回。
* D-046 根治（R16）：冻结树为省掉重建 venv 的开销而软链 ``.venv``，但 editable 安装的
  ``_editable_impl_campaignlab.pth`` 写死了**活动仓库 src 的绝对路径**，于是冻结树上
  ``import campaignlab`` 会解析到活动工作树（门禁读数＝「冻结测试 ＋ 活动源码」的杂交）。
  故凡在冻结树里跑工具链，一律经 ``frozen_env()`` 把冻结树的 ``src`` 钉进
  ``PYTHONPATH`` / ``MYPYPATH`` 夺回解析权。有了它，PRE-12 的「泊出在飞件」不再是前置条件。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

REPO: Final = Path("/home/szf/dev/CampaignLab")
STATE: Final = REPO / "orchestrator" / "state.json"
COUNTS_JSONPATH: Final = ("resume", "self_check_gates_rc0", "counts")

#: ruff format 的 in-scope 口径：*.py + *.md，排除 spec/ prototype/ web/ .venv/ node_modules/
EXCLUDED_PREFIXES: Final = ("spec/", "prototype/", "web/", ".venv/", "node_modules/")
RUFF_SUFFIXES: Final = (".py", ".md")

#: 在冻结树里必然红的守护（断言 repo-root/HEAD 树恒等），排除后另行静态计数。
GIT_ENV_IGNORES: Final = (
    "tests/unit/test_config.py",
    "tests/unit/test_counts_freshness.py",
)

_UV: Final = ("uv", "run", "--no-sync")


class HarnessError(RuntimeError):
    """工装自身的硬失败（区别于被测门禁的 RED）。"""


@dataclass(frozen=True)
class Proc:
    rc: int
    out: str
    err: str


@dataclass
class GateResult:
    name: str
    rc: int
    ok: bool
    detail: str
    tail: str = ""


@dataclass
class CommitReport:
    tag: str
    sha: str
    gates: dict[str, GateResult] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    staged: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- 底层执行


def frozen_env(tree: Path) -> dict[str, str]:
    """D-046 根治：让冻结树上的 Python 导入解析到**冻结树自己的 src**。

    ``frozen_tree()`` 为省掉每次重建 venv 的数十秒开销而软链 ``.venv``，但 editable 安装的
    ``_editable_impl_campaignlab.pth`` 内容是**活动仓库 src 的绝对路径**，会在 site 初始化阶段
    被追加进 ``sys.path`` ⇒ 在冻结树里 ``import campaignlab`` 解析到活动工作树，门禁读数成了
    「冻结测试 ＋ 活动源码」的杂交（D-046：既产假红，也产假绿，后者在无人值守长程里是静默腐化）。

    ``PYTHONPATH`` 的条目在 ``sys.path`` 中**先于** site 阶段追加的 ``.pth`` 路径，故把冻结树的
    ``src`` 放进 ``PYTHONPATH`` 即可在不重建 venv 的前提下夺回解析权。实测（2026-11-15，活动树
    含在飞 lane 的 ``infra/db/repositories.py`` +826/0 作为天然阳性对照）：

    * 不加 ⇒ ``tests/unit/test_job_repository_terminal.py`` = **1 failed, 23 passed**
      （``test_repositories_module_all_is_unchanged`` 被活动树的新名打红）；
    * 加了 ⇒ **24 passed**。

    ``MYPYPATH`` 同批给定：``pyproject.toml`` 的 ``mypy_path = "src"`` 相对 cwd 本就指向冻结树，
    这里再显式钉一次，防 follow-import 落回活动树。

    对 ``tree == REPO`` 的调用（真实工作树口径）本函数**恒等**：返回值与 ``.pth`` 里的绝对路径
    相同，不改变任何既有行为。
    """
    src = str(tree / "src")
    return {"PYTHONPATH": src, "MYPYPATH": src}


def sh(args: Sequence[str], cwd: Path = REPO, env: Mapping[str, str] | None = None) -> Proc:
    """跑命令并取回 rc/out/err。禁接管道（rule_rc：rc 必须由被测命令本身产生）。

    ``env`` 非空时以 ``os.environ`` 为底做**浅覆盖**（不改 ``os.environ`` 本身），
    供 D-046 的冻结树导入隔离用（见 ``frozen_env``）。
    """
    environ = {**os.environ, **env} if env else None
    p = subprocess.run(
        list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=environ,
    )
    return Proc(p.returncode, p.stdout, p.stderr)


def git(*args: str, cwd: Path = REPO) -> Proc:
    return sh(("git", *args), cwd=cwd)


def git_out(*args: str, cwd: Path = REPO) -> str:
    p = git(*args, cwd=cwd)
    if p.rc != 0:
        raise HarnessError(f"git {' '.join(args)} rc={p.rc} err={p.err[:400]}")
    return p.out


def head_sha(short: bool = True) -> str:
    args = ["rev-parse", "--short", "HEAD"] if short else ["rev-parse", "HEAD"]
    return git_out(*args).strip()


def branch() -> str:
    return git_out("rev-parse", "--abbrev-ref", "HEAD").strip()


def status_porcelain() -> list[str]:
    raw = git_out("status", "--porcelain")
    return [ln for ln in raw.splitlines() if ln.strip()]


# --------------------------------------------------------------------------- 文本卫生


def normalize_file(path: Path) -> list[str]:
    """UTF-8 / 无 BOM / 无 CR / 以 \\n 结尾。返回实际做的修正项（空列表 == 本就合规）。"""
    data = path.read_bytes()
    fixes: list[str] = []
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
        fixes.append("BOM_REMOVED")
    if b"\r" in data:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        fixes.append("CR_REMOVED")
    if data and not data.endswith(b"\n"):
        data += b"\n"
        fixes.append("TRAILING_NL_ADDED")
    if fixes:
        path.write_bytes(data)
    return fixes


def normalize_many(paths: Iterable[Path]) -> dict[str, list[str]]:
    return {str(p): f for p in paths if (f := normalize_file(p))}


# --------------------------------------------------------------------------- 分母口径


def in_scope(rel: str) -> bool:
    if rel.startswith(EXCLUDED_PREFIXES):
        return False
    return rel.endswith(RUFF_SUFFIXES)


def tracked_in_scope(*, from_index: bool = False) -> tuple[list[str], list[str]]:
    """in-scope py / md 清单。

    ``from_index=False``（默认）取**已提交树** HEAD —— 这是 ``test_counts_freshness.py``
    的口径，禁从工作树取数（A101）。``from_index=True`` 取**暂存索引**，只在提交闭环内部
    用：此时索引 == 待提交树，提交完成后两种口径必然重合。
    """
    if from_index:
        raw = git_out("ls-files", "--cached", "-z")
    else:
        raw = git_out("ls-tree", "-r", "HEAD", "--name-only", "-z")
    names = [n for n in raw.split("\0") if n]
    py = sorted(n for n in names if n.endswith(".py") and in_scope(n))
    md = sorted(n for n in names if n.endswith(".md") and in_scope(n))
    return py, md


def untracked_in_scope() -> list[str]:
    raw = git_out("ls-files", "--others", "--exclude-standard", "-z")
    return sorted(n for n in raw.split("\0") if n and in_scope(n))


def classify_untracked(
    owner_map: Mapping[str, Sequence[str]] | None,
) -> tuple[dict[str, list[str]], list[str]]:
    """A144(c)：逐件把未跟踪 in-scope 文件归属到在飞 lane 的写集前缀；归不上的即越界。"""
    owners = dict(owner_map or {})
    untracked = untracked_in_scope()
    attributed: dict[str, list[str]] = {}
    outside: list[str] = []
    for f in untracked:
        hit = None
        for lane, prefixes in owners.items():
            if any(
                f == p or f.startswith(p.rstrip("/") + "/") or f.startswith(p) for p in prefixes
            ):
                hit = lane
                break
        if hit is None:
            outside.append(f)
        else:
            attributed.setdefault(hit, []).append(f)
    return attributed, outside


# --------------------------------------------------------------------------- 冻结树 + 门禁


def frozen_tree(scratch: Path) -> Path:
    """把**当前索引**导出到仓库外 scratch，并软链 .venv/.git 以便原地跑工具链。

    ⚠ 软链 ``.venv`` 会把 editable ``.pth`` 里**活动仓库 src 的绝对路径**一并带进来（D-046）。
    隔离由调用侧负责：``run_gates`` / ``count_git_env_ignores`` / ``predict_pytest`` 一律
    经 ``frozen_env(tree)`` 把冻结树的 ``src`` 钉进 ``PYTHONPATH`` / ``MYPYPATH``。
    """
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    p = git("checkout-index", "-a", "-f", f"--prefix={scratch}/")
    if p.rc != 0:
        raise HarnessError(f"checkout-index rc={p.rc} err={p.err[:400]}")
    for name in (".venv", ".git"):
        src = REPO / name
        dst = scratch / name
        if src.exists() and not dst.exists():
            dst.symlink_to(src)
    return scratch


def _judge(name: str, p: Proc, pattern: str, forbid: Sequence[str]) -> GateResult:
    blob = p.out + p.err
    tail = "\n".join(blob.strip().splitlines()[-4:])
    text_ok = re.search(pattern, blob) is not None
    bad = [w for w in forbid if w in blob]
    ok = p.rc == 0 and text_ok and not bad
    detail = f"rc={p.rc} text_ok={text_ok} forbid_hit={bad}"
    return GateResult(name, p.rc, ok, detail, tail)


def run_gates(
    tree: Path,
    *,
    want_pytest: bool = True,
    want_mypy: bool = True,
    want_ruff: bool = True,
) -> dict[str, GateResult]:
    """在冻结树上跑四门。全部双判（rc + 文本）＋ 全部经 ``frozen_env`` 隔离导入（D-046）。"""
    g: dict[str, GateResult] = {}
    env = frozen_env(tree)
    if want_ruff:
        g["ruff_format"] = _judge(
            "ruff_format",
            sh((*_UV, "ruff", "format", "--check", "."), cwd=tree, env=env),
            r"\d+ files? already formatted",
            ("would be reformatted",),
        )
        g["ruff_check"] = _judge(
            "ruff_check",
            sh((*_UV, "ruff", "check", "."), cwd=tree, env=env),
            r"All checks passed",
            ("Found ", "error["),
        )
    if want_mypy:
        g["mypy"] = _judge(
            "mypy",
            sh((*_UV, "mypy"), cwd=tree, env=env),
            r"Success: no issues found in (\d+) source files",
            ("error:", "errors prevented further checking"),
        )
    if want_pytest:
        args = [*_UV, "pytest", "-q", "-p", "no:randomly"]
        for rel in GIT_ENV_IGNORES:
            args += ["--ignore", rel]
        g["pytest_frozen"] = _judge(
            "pytest_frozen",
            sh(tuple(args), cwd=tree, env=env),
            r"\d+ passed",
            ("failed", "error"),
        )
    return g


def gate_number(g: GateResult, pattern: str) -> int | None:
    m = re.search(pattern, g.tail) or re.search(pattern, g.detail)
    return int(m.group(1)) if m else None


def count_git_env_ignores(tree: Path | None = None) -> int:
    """GIT_ENV_IGNORES 两件的静态可收集用例数（补回冻结 pytest 的分母）。

    这两件断言「repo-root == HEAD 树」，在冻结树里实跑必然红，故只**静态收集**；
    默认在真实工作树上收集，传入 ``tree`` 则在冻结树上收集（提交闭环用后者，
    以保证分母与待提交树同源）。
    """
    root = tree or REPO
    total = 0
    for rel in GIT_ENV_IGNORES:
        if not (root / rel).exists():
            continue
        p = sh((*_UV, "pytest", "-q", "--collect-only", rel), cwd=root, env=frozen_env(root))
        m = re.search(r"(\d+) tests? collected", p.out + p.err)
        if m is None:
            m = re.search(r"collected (\d+)", p.out + p.err)
        if m is None:
            raise HarnessError(f"collect-only 无法解析 {rel}: {(p.out + p.err)[-300:]}")
        total += int(m.group(1))
    return total


def all_green(gates: Mapping[str, GateResult]) -> bool:
    return all(g.ok for g in gates.values())


# --------------------------------------------------------------------------- 台账


def load_state() -> dict[str, object]:
    loaded: object = json.loads(STATE.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise HarnessError("state.json 顶层不是对象")
    return {str(k): v for k, v in loaded.items()}


def get_counts(state: Mapping[str, object]) -> dict[str, object]:
    node: object = state
    for k in COUNTS_JSONPATH:
        if not isinstance(node, dict) or k not in node:
            raise HarnessError(f"台账缺键 {COUNTS_JSONPATH}")
        node = node[k]
    if not isinstance(node, dict):
        raise HarnessError("counts 不是对象")
    return node


def dump_state(state: Mapping[str, object]) -> None:
    txt = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    STATE.write_bytes(txt.encode("utf-8"))


# --------------------------------------------------------------------- 计数预测与回填


def _is_mypy_scope(rel: str) -> bool:
    """mypy 的 ``files = ["src", "tests", "scripts"]``（pyproject.toml），排除 exclude 前缀。"""
    if not rel.endswith(".py"):
        return False
    if rel.startswith(("spec/", "prototype/", "web/", ".venv/")):
        return False
    return rel.startswith(("src/", "tests/", "scripts/"))


def predict_counts(add_paths: Sequence[str]) -> dict[str, int]:
    """提交前的静态预测值；``run_commit`` 会用冻结树实测值逐条对账，不符即拒绝提交。

    三项口径：
    * ``ruff_formatted_files`` = 暂存后索引里的 in-scope py+md 件数；
    * ``mypy_source_files``   = 台账现值 + 本次新增（此前不在 HEAD 树）的 mypy 域 .py 件数；
    * ``pytest_passed``       = 冻结树实跑 passed + GIT_ENV_IGNORES 静态收集数。
    """
    head_py, head_md = tracked_in_scope()
    head_set = set(head_py) | set(head_md)
    idx_py, idx_md = tracked_in_scope(from_index=True)
    mypy_raw = get_counts(load_state()).get("mypy_source_files", 0)
    if not isinstance(mypy_raw, int):
        raise HarnessError(f"台账 mypy_source_files 不是整数: {mypy_raw!r}")
    mypy_now = mypy_raw
    new_mypy = [p for p in add_paths if _is_mypy_scope(p) and p not in set(head_py)]
    return {
        "ruff_formatted_files": len(idx_py) + len(idx_md),
        "in_scope_py": len(idx_py),
        "in_scope_md": len(idx_md),
        "mypy_source_files": mypy_now + len(new_mypy),
        "head_in_scope": len(head_set),
    }


def predict_pytest(new_test_files: Sequence[str], tree: Path | None = None) -> int:
    """新增测试文件的可收集用例数（用于预测 pytest_passed 增量）。"""
    total = 0
    root = tree or REPO
    for rel in new_test_files:
        if not (root / rel).exists():
            continue
        p = sh((*_UV, "pytest", "-q", "--collect-only", rel), cwd=root, env=frozen_env(root))
        m = re.search(r"(\d+) tests? collected", p.out + p.err) or re.search(
            r"collected (\d+)", p.out + p.err
        )
        if m is None:
            raise HarnessError(f"collect-only 无法解析 {rel}: {(p.out + p.err)[-300:]}")
        total += int(m.group(1))
    return total


def set_counts(
    state: dict[str, object], values: Mapping[str, int], *, reason: str, at: str
) -> dict[str, object]:
    """把实测/预测值写回台账 counts，并留「历史值只加注不改写」的追加说明键。"""
    counts = get_counts(state)
    prev: dict[str, object] = {}
    for k, v in values.items():
        if k in counts and counts[k] != v:
            prev[k] = counts[k]
        counts[k] = v
    counts["counts_refreshed_at"] = at
    counts["counts_refresh_reason"] = reason
    if prev:
        counts["previous_values_last"] = prev
    return counts


# --------------------------------------------------------------------------- 提交


def stage(add_paths: Sequence[str]) -> list[str]:
    """只用显式路径 add（禁 -A），并断言暂存集 == 期望集。"""
    missing = [p for p in add_paths if not (REPO / p).exists()]
    if missing:
        raise HarnessError(f"待入库路径不存在: {missing}")
    p = git("add", "--", *add_paths)
    if p.rc != 0:
        raise HarnessError(f"git add rc={p.rc} err={p.err[:400]}")
    raw = git_out("diff", "--cached", "--name-only", "-z")
    staged = sorted(n for n in raw.split("\0") if n)
    expected = sorted(set(add_paths))
    if staged != expected:
        raise HarnessError(f"暂存集 != 期望集\n staged={staged}\n expect={expected}")
    return staged


def write_msg_file(msg: str, path: Path) -> Path:
    body = msg.replace("\r\n", "\n").replace("\r", "\n")
    if not body.endswith("\n"):
        body += "\n"
    if body.startswith("\ufeff"):
        body = body[1:]
    path.write_bytes(body.encode("utf-8"))
    return path


def commit_staged(msg: str, msg_dir: Path | None = None) -> str:
    d = msg_dir or Path("/tmp")
    d.mkdir(parents=True, exist_ok=True)
    mf = write_msg_file(msg, d / "orch_commit_msg.txt")
    p = git("commit", "-F", str(mf))
    if p.rc != 0:
        raise HarnessError(f"git commit rc={p.rc} out={p.out[-500:]} err={p.err[-500:]}")
    return head_sha()


#: 台账本体不做悬空引用扫描：state.json 是 1.1 MB 的历史账本，里面的路径绝大多数是
#: 散文式追注、glob、缩写与「当时的实测快照」，逐条要求磁盘存在既不成立也无意义。
#: 它引用面里**真正需要存在性保证**的两类（defects 与 change_requests）已由
#: tests/unit/test_state_ledger.py 的 test_every_ledger_defect_has_md_on_disk 与
#: test_change_request_ids_are_unique 两条机器守护专管，不靠本扫描重复覆盖。
DANGLING_SWEEP_SKIP: Final = frozenset({"orchestrator/state.json"})


def dangling_refs(paths: Sequence[str]) -> list[str]:
    """扫本次入库文件里引用的仓库路径，报出磁盘上不存在者（禁悬空引用，手册 §15.3）。"""
    pat = re.compile(r"(?:evidence|orchestrator|docs|contracts|scripts)/[A-Za-z0-9._@/\-]+")
    bad: list[str] = []
    for rel in paths:
        if rel in DANGLING_SWEEP_SKIP:
            continue
        fp = REPO / rel
        if not fp.is_file() or fp.suffix not in (".md", ".json", ".py", ".txt", ".jsonl"):
            continue
        try:
            txt = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError:
            continue
        for m in pat.findall(txt):
            cand = m.rstrip(".,;:)】、。")
            if not (REPO / cand).exists():
                bad.append(f"{rel} -> {cand}")
    return sorted(set(bad))


def run_commit(
    tag: str,
    add_paths: Sequence[str],
    msg: str,
    *,
    mutate_ledger: Callable[[dict[str, object]], None] | None = None,
    want_pytest: bool = True,
    want_mypy: bool = True,
    untracked_owner_map: Mapping[str, Sequence[str]] | None = None,
    scratch: Path | None = None,
    allow_dangling: Sequence[str] = (),
    keep_scratch: bool = False,
    expect_counts: Mapping[str, int] | None = None,
) -> CommitReport:
    """一任务一提交的完整闭环。

    次序（R11-3 + A101 + rule_counts_sampling_point 的共同要求）：

    1. 文本卫生（BOM / CR / 尾换行）；
    2. 台账变更落盘（counts 用**静态预测值**先写）；
    3. ``git add -- <显式路径>`` 并断言暂存集 == 期望集 —— 索引此刻 == 待提交树；
    4. 从**索引**导出冻结树，在冻结树上跑四门（双判 rc + 文本）；
    5. 用冻结树实测值逐条对账第 2 步写入的预测值，不符即 ``git reset`` 回滚并拒绝提交；
    6. A144(c) 未跟踪件归属分类（归不上 = 越界，拒绝提交）；
    7. 悬空引用扫描（本次入库文件里引用的仓库路径必须存在）；
    8. ``git commit -F``（提交信息同样过卫生）+ 复验 HEAD 已推进。

    任一步失败都保证 HEAD 不动、索引回滚，不留半成品。
    """
    notes: list[str] = []
    before_head = head_sha()
    br = branch()
    if br != os.environ.get("ORCH_BRANCH", "m0-framework"):
        notes.append(f"WARN branch={br}")

    fixes = normalize_many(REPO / p for p in add_paths if (REPO / p).is_file())
    if fixes:
        notes.append(f"normalized={json.dumps(fixes, ensure_ascii=False)}")

    all_paths = list(add_paths)
    if mutate_ledger is not None:
        state = load_state()
        mutate_ledger(state)
        dump_state(state)
        normalize_file(STATE)
        rel = "orchestrator/state.json"
        if rel not in all_paths:
            all_paths.append(rel)
        notes.append("ledger_mutated")

    sc = scratch or Path(f"/tmp/orch_frozen_{tag}")

    def _rollback(why: str) -> HarnessError:
        """撤销暂存；若本轮改过台账，连工作树里的台账一起还原到 HEAD。

        ``git reset`` 只动索引不动工作树，故单靠它会把改坏的 state.json 留在树上：
        下一次重试会在**已改过一遍**的台账上再改一遍（重复 append、previous_values
        取到刷新后的值），造成静默的账本腐化。这是 R12 实测踩到的坑。
        """
        git("reset", "-q", "HEAD", "--")
        if mutate_ledger is not None:
            git("checkout", "--", "orchestrator/state.json")
        if not keep_scratch:
            shutil.rmtree(sc, ignore_errors=True)
        return HarnessError(f"[{tag}] {why}（未提交，HEAD 仍为 {before_head}，台账已还原）")

    try:
        staged = stage(all_paths)
    except HarnessError as e:
        raise _rollback(f"暂存失败: {e}") from e

    tree = frozen_tree(sc)
    gates = run_gates(tree, want_pytest=want_pytest, want_mypy=want_mypy)
    if not all_green(gates):
        red = {k: (v.rc, v.detail, v.tail) for k, v in gates.items() if not v.ok}
        raise _rollback(f"冻结树门禁 RED: {red}")

    attributed, outside = classify_untracked(untracked_owner_map)
    staged_set = set(staged)
    outside = [f for f in outside if f not in staged_set]
    if outside:
        raise _rollback(f"A144(c) 越界未跟踪件: {outside}")
    if attributed:
        notes.append(f"in_flight_untracked={json.dumps(attributed, ensure_ascii=False)}")

    mypy_n = gate_number(gates["mypy"], r"in (\d+) source files") if "mypy" in gates else None
    ruff_n = gate_number(gates["ruff_format"], r"(\d+) files? already formatted")
    frozen_pass = (
        gate_number(gates["pytest_frozen"], r"(\d+) passed") if "pytest_frozen" in gates else None
    )
    env_ign = count_git_env_ignores(tree) if want_pytest else 0
    pytest_total = (frozen_pass or 0) + env_ign if frozen_pass is not None else None

    measured = {
        "ruff_formatted_files": ruff_n,
        "mypy_source_files": mypy_n,
        "pytest_passed": pytest_total,
    }
    idx_py, idx_md = tracked_in_scope(from_index=True)
    measured["in_scope_py"] = len(idx_py)
    measured["in_scope_md"] = len(idx_md)
    notes.append(f"frozen_pytest={frozen_pass} git_env_ignores_collect={env_ign}")

    if expect_counts:
        mismatch = {
            k: (v, measured.get(k))
            for k, v in expect_counts.items()
            if k in measured and measured.get(k) != v
        }
        if mismatch:
            raise _rollback(f"counts 预测 != 冻结树实测 {mismatch}")

    if mutate_ledger is not None:
        ledger_counts = get_counts(load_state())
        drift = {
            k: (ledger_counts.get(k), mv)
            for k, mv in measured.items()
            if mv is not None and k in ledger_counts and ledger_counts[k] != mv
        }
        if drift:
            raise _rollback(f"台账 counts != 实测 {drift}")

    dang = [d for d in dangling_refs(staged) if d not in set(allow_dangling)]
    if dang:
        raise _rollback(f"悬空引用: {dang[:20]}")

    sha = commit_staged(msg)
    if not keep_scratch:
        shutil.rmtree(sc, ignore_errors=True)
    if sha == before_head:
        raise HarnessError(f"[{tag}] 提交未推进 HEAD（仍为 {sha}）")

    counts = {k: v for k, v in measured.items() if v is not None}
    rep = CommitReport(tag=tag, sha=sha, gates=gates, counts=counts, staged=staged, notes=notes)
    rep.notes.append(f"post_status_lines={len(status_porcelain())}")
    return rep


def commit_and_verify(tag: str, add_paths: Sequence[str], msg: str) -> str:
    """轻量通道（纯台账/文档提交）：卫生 -> 显式 add -> 断言暂存集 -> commit -> 复验 HEAD 推进。"""
    before = head_sha()
    normalize_many(REPO / p for p in add_paths if (REPO / p).is_file())
    staged = stage(add_paths)
    sha = commit_staged(msg)
    if sha == before:
        raise HarnessError(f"[{tag}] HEAD 未推进")
    if len(staged) != len(set(add_paths)):
        raise HarnessError(f"[{tag}] 暂存集异常 {staged}")
    return sha


def main(argv: Sequence[str]) -> int:
    if argv and argv[0] == "baseline":
        tree = frozen_tree(Path("/tmp/orch_baseline_probe"))
        g = run_gates(tree)
        for k, v in g.items():
            print(f"{k}: ok={v.ok} {v.detail} :: {v.tail.splitlines()[-1] if v.tail else ''}")
        py, md = tracked_in_scope()
        print(f"tracked_in_scope py={len(py)} md={len(md)} total={len(py) + len(md)}")
        print(f"git_env_ignores_collect={count_git_env_ignores()}")
        print(f"ALL_GREEN={all_green(g)}")
        shutil.rmtree("/tmp/orch_baseline_probe", ignore_errors=True)
        return 0 if all_green(g) else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
