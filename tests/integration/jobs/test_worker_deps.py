"""``worker/deps.py`` 的守护（M0-04/S2b-2 · A156 启动闸 + A154 接线口径）。

三组判据，每条都能被证伪（正向对照见 ``evidence/M0/M0-04/positive-control-s2b2.log``）：

① **A156**：``get_artifact_writer`` 必须在 ``return`` **之前**调一次
   ``ArtifactWriter.verify_same_filesystem()``，且「``st_dev`` 不符 → ``config.ConfigError``
   → CLI 面 rc=2」这条链要能跑通。行为面用两条独立造法（``os.stat`` 决定性替身 ＋
   真实第二文件系统），静态面用 AST 钉住「调用点在 return 之前」，
   rc=2 那一环走 ``cli.cmd_serve`` 的**既有**映射（``cli.py`` 在本子任务硬禁内，不改一字），
   并配一条对照用例证明该映射**只**吃 ``ConfigError``（否则 rc=2 断言就是恒真）。
② **A154**：handler 侧接线二选一，禁第三种。两种合法接法各自落一条用例，断言同一
   ``(workspace_id, kind, sha256)`` 走完整路径后 ``artifacts`` 表**恰 1 行**（design §11:157）；
   被禁的第三种（先 ``commit()`` 再把 record 交回 ``succeed(artifacts=...)``）单独落一条，
   断言它**必须红**（``IntegrityError``）且事务整体回滚。
③ **A169 → S2c 已落地（A207 同批改写）**：``worker/service.py`` 已由 M0-04/S2c 交付，
   ``deps.py`` 那条 ``# type: ignore[import-not-found]`` 同批删除（留着会让全表 mypy 因
   ``warn_unused_ignores`` 判红）。原判据「缺席时 import 仍成功」的自带前提断言明写
   「它已出现 ⇒ …并改写本用例」，故这一组改成钉**延迟加载形态不变**（模块级不导入
   ``worker.service``、运行期不绑定 ``JobService``、返回注解仍是 ``JobService``）
   ＋「导入失败即指名报错」（用 ``monkeypatch`` 造缺席，不再依赖真实文件状态）；
   另用 ``sys.modules`` 注入桩模块证明延迟导入这条路真的通（不只是错误分支通）。

库用活契约 DDL 建，不跑 alembic —— 与本目录 ``test_artifact_write.py`` 同体例。
本文件**不新增** ``conftest.py``（派单文 §4：那会触发 basename 冲突规则），fixture 全部就地定义。
探针一律落在 ``tmp_path``。
"""

from __future__ import annotations

import ast
import os
import shutil
import sqlite3
import sys
import types
import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from campaignlab import cli
from campaignlab.api.common import ObjectRef, canonical_json
from campaignlab.clock import FixedClock
from campaignlab.config import AppConfig, ConfigError, load_config
from campaignlab.config import resolve_data_dir as config_resolve_data_dir
from campaignlab.infra.artifacts import ARTIFACT_KIND_JOB_RESULT, results_root, stage_root
from campaignlab.infra.db.engine import connect, make_engine
from campaignlab.infra.db.paths import location_from_url
from campaignlab.infra.db.repositories import ArtifactRecord, JobRepository
from campaignlab.worker import deps
from campaignlab.worker.deps import (
    get_artifact_writer,
    get_job_service,
    get_job_store,
    resolve_data_dir,
)
from campaignlab.worker.leases import Lease
from campaignlab.worker.store import JobStore, short_transaction

REPO: Final = Path(__file__).resolve().parents[3]
DDL: Final = REPO / "contracts" / "sqlite-v1.sql"
DEPS_PATH: Final = REPO / "src" / "campaignlab" / "worker" / "deps.py"
SERVICE_PATH: Final = REPO / "src" / "campaignlab" / "worker" / "service.py"
SERVICE_MODULE: Final = "campaignlab.worker.service"

#: 显式时钟的固定时刻（禁 ``datetime.now()`` / 禁 ``sleep``，design §4）。
T0: Final = datetime(2026, 11, 14, 1, 0, 0, tzinfo=UTC)
WS: Final = "ws-dep"
JOB: Final = "J-dep-1"
INPUT_DIGEST: Final = "0" * 64
PAYLOAD: Final = "活动 A 复盘结果 · 金额 12345 分 · 比率 0.15".encode()


# ---------------------------------------------------------------------------------- fixture


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def db_path(data_dir: Path) -> Path:
    """按活契约 DDL 建临时库，并插一个工作区（``jobs``/``artifacts`` 的外键目标）。"""
    assert DDL.is_file(), f"活契约 DDL 读不到：{DDL}"
    state_dir = data_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "campaignlab.db"
    raw = sqlite3.connect(path)
    try:
        raw.executescript(DDL.read_text(encoding="utf-8"))
        raw.execute(
            "INSERT INTO workspaces (id, name, source_class, revision, created_at) "
            "VALUES (?, ?, 'SYNTHETIC', 1, ?)",
            (WS, "依赖装配工作区", T0.isoformat()),
        )
        raw.commit()
    finally:
        raw.close()
    return path


@pytest.fixture
def engine(db_path: Path) -> Iterator[Engine]:
    target = make_engine(f"sqlite:///{db_path}")
    try:
        yield target
    finally:
        target.dispose()


@pytest.fixture
def config(data_dir: Path, db_path: Path) -> AppConfig:
    """``data_dir`` 与库位置都指到 ``tmp_path``；``environ``/``home`` 注入，不改进程环境。"""
    base = load_config(environ={"CAMPAIGNLAB_DATA_DIR": str(data_dir)}, home=data_dir)
    return replace(base, database=location_from_url(f"sqlite:///{db_path}"))


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(T0)


@pytest.fixture
def store(config: AppConfig) -> JobStore:
    """刻意经**被测提供器**取 store，而不是直接 ``JobStore(engine=...)``。"""
    return get_job_store(config=config)


@pytest.fixture
def other_device(data_dir: Path) -> Iterator[Path | None]:
    """找一个与 ``data_dir`` 不同 ``st_dev`` 的可写目录（WSL2 上通常是 ``/dev/shm``）。

    找不到就返回 ``None``，由用例自己 ``skip`` 并说明「已由 os.stat 替身用例覆盖」——
    禁把「环境不具备」写成「通过」。
    """
    primary_dev = data_dir.stat().st_dev
    candidate: Path | None = None
    for base in ("/dev/shm", "/run/lock", "/tmp"):
        root = Path(base)
        if not root.is_dir():
            continue
        probe = root / f"campaignlab-deps-exdev-{uuid.uuid4().hex}"
        try:
            probe.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        if probe.stat().st_dev != primary_dev:
            candidate = probe
            break
        shutil.rmtree(probe, ignore_errors=True)
    yield candidate
    if candidate is not None:
        shutil.rmtree(candidate, ignore_errors=True)


# ----------------------------------------------------------------------------------- 工具


def _running_job(store: JobStore, clock: FixedClock, *, job_id: str = JOB) -> Lease:
    """入队 ＋ 认领，拿到一条 ``RUNNING`` 作业的租约（TX1）。"""
    store.enqueue(
        workspace_id=WS,
        kind="COMPARE",
        input_json=canonical_json({"snapshot": "S-1"}),
        input_digest=INPUT_DIGEST,
        now=clock.now(),
        job_id=job_id,
    )
    claim = store.claim_next(workspace_id=WS, now=clock.now())
    assert claim.lease is not None, "前置条件：必须认领成功"
    return claim.lease


def _artifact_count(engine: Engine) -> int:
    with connect(engine) as conn:
        return int(conn.execute(text("SELECT count(*) FROM artifacts")).scalar_one())


def _job_state(engine: Engine, job_id: str) -> str:
    with connect(engine) as conn:
        return str(
            conn.execute(text("SELECT state FROM jobs WHERE id = :id"), {"id": job_id}).scalar_one()
        )


def _install_cross_device_stat(monkeypatch: pytest.MonkeyPatch, results_dir: Path) -> list[Path]:
    """让 ``os.stat(results_dir)`` 报出一个**不同的 ``st_dev``**，其余路径一律透传。

    这是 A156 的决定性造法：真实双设备依赖本机有第二个可写文件系统（见 ``other_device``），
    没有就会被 skip，守护随之失去信号。替身只改一个目录的 ``st_dev``，
    且只在被测调用期间生效（调用方用 ``monkeypatch.context()`` 或 ``undo()`` 立刻复原）。
    """
    seen: list[Path] = []
    real_stat = os.stat
    marker = str(results_dir)

    def _fake_stat(path: Path, *args: object, **kwargs: object) -> os.stat_result:
        st = real_stat(path)
        if str(path) != marker:
            return st
        seen.append(Path(path))
        return os.stat_result(
            (
                st.st_mode,
                st.st_ino,
                st.st_dev + 1,
                st.st_nlink,
                st.st_uid,
                st.st_gid,
                st.st_size,
                st.st_atime,
                st.st_mtime,
                st.st_ctime,
            )
        )

    monkeypatch.setattr(os, "stat", _fake_stat)
    return seen


def _function_node(name: str) -> ast.FunctionDef:
    tree = ast.parse(DEPS_PATH.read_text(encoding="utf-8"), filename=str(DEPS_PATH))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"deps.py 里找不到函数 {name}")


# ========================================================================= ① A156 启动闸


def test_get_artifact_writer_returns_a_writer_when_both_roots_share_one_device(
    config: AppConfig, data_dir: Path
) -> None:
    """同盘 ⇒ 正常返回 writer，并把两个根目录建好（design §5 目录布局）。"""
    writer = get_artifact_writer(config=config)
    assert writer.data_dir == data_dir
    assert stage_root(data_dir).is_dir()
    assert results_root(data_dir).is_dir()


def test_get_artifact_writer_raises_config_error_when_st_dev_differs(
    config: AppConfig, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A156 决定性用例：``st_dev`` 不符 ⇒ ``config.ConfigError``，**且拿不到 writer**。"""
    seen = _install_cross_device_stat(monkeypatch, results_root(data_dir))
    try:
        with pytest.raises(ConfigError) as excinfo:
            get_artifact_writer(config=config)
    finally:
        monkeypatch.undo()
    assert seen, "前置条件：替身确实作用到了 results 根目录"
    assert "同一文件系统" in str(excinfo.value)
    assert excinfo.value.__class__ is ConfigError, "必须是 config.ConfigError 本尊，CLI 才映射 rc=2"


def test_get_artifact_writer_raises_config_error_on_a_real_second_filesystem(
    config: AppConfig, data_dir: Path, other_device: Path | None
) -> None:
    """A156 真实双设备：用符号链接把 ``tmp/jobs`` 指到另一个文件系统（本机无 root）。"""
    if other_device is None:
        pytest.skip("本机没有第二个可写文件系统；已由 os.stat 替身用例决定性覆盖")
    (data_dir / "tmp").mkdir(parents=True, exist_ok=True)
    results_root(data_dir).mkdir(parents=True, exist_ok=True)
    real_jobs = other_device / "jobs"
    real_jobs.mkdir(parents=True, exist_ok=True)
    os.symlink(real_jobs, stage_root(data_dir))
    with pytest.raises(ConfigError) as excinfo:
        get_artifact_writer(config=config)
    assert "同一文件系统" in str(excinfo.value)


def test_get_artifact_writer_calls_verify_same_filesystem_before_returning() -> None:
    """A156 静态面：``verify_same_filesystem()`` 的调用点必须在**唯一的 return 之前**。

    只看行为不够 —— 把调用挪到 ``return`` 之后就等于闸失效，而多数用例仍会绿。
    故用 AST 钉住顺序（禁正则扫源码文本）。
    """
    node = _function_node("get_artifact_writer")
    verify_lines = [
        child.lineno
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Attribute)
        and child.func.attr == "verify_same_filesystem"
    ]
    return_lines = [child.lineno for child in ast.walk(node) if isinstance(child, ast.Return)]
    assert len(verify_lines) == 1, f"必须恰好调用一次，实测 {verify_lines}"
    assert len(return_lines) == 1, f"必须只有一个 return，实测 {return_lines}"
    assert verify_lines[0] < return_lines[0], "A156：必须在返回 writer **之前**过闸"


def test_st_dev_mismatch_config_error_maps_to_cli_rc2(
    config: AppConfig,
    data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A156 点名要求的完整链：``st_dev`` 不符 → ``ConfigError`` → **CLI 面 rc=2**。

    第二环走 ``cli.cmd_serve`` 的**既有**映射（``except ConfigError → return 2``）。
    ``cli.py`` 在本子任务硬禁内，故不改它、也不假装已经接好线：这里把
    ``get_artifact_writer`` 真实抛出的那个异常对象喂给 ``cmd_serve`` 的配置解析入口，
    证明「这一类异常在 serve 面上就是 rc=2」。启动路径真正调用
    ``get_artifact_writer`` 的那一行属 FU-30／S4（``cli.py`` / ``api/app.py``），
    已在回执里如实标注。
    """
    seen = _install_cross_device_stat(monkeypatch, results_root(data_dir))
    try:
        with pytest.raises(ConfigError) as excinfo:
            get_artifact_writer(config=config)
    finally:
        monkeypatch.undo()
    assert seen, "前置条件：替身确实生效"

    captured = excinfo.value

    def _raise_config_error() -> AppConfig:
        raise captured

    monkeypatch.setattr(cli, "load_config", _raise_config_error)
    rc = cli.cmd_serve(cli.build_parser().parse_args(["serve"]))
    assert rc == 2, f"ConfigError 在 serve 面必须是 rc=2，实测 {rc}"
    assert "同一文件系统" in capsys.readouterr().err


def test_cli_rc2_mapping_is_specific_to_config_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """对照用例：rc=2 **只**吃 ``ConfigError``，别的异常照样往外抛。

    没有这条，上一条的 ``rc == 2`` 就可能是「serve 面把一切异常都吞成 2」的恒真断言。
    """

    def _raise_value_error() -> AppConfig:
        raise ValueError("不是配置错")

    monkeypatch.setattr(cli, "load_config", _raise_value_error)
    with pytest.raises(ValueError, match="不是配置错"):
        cli.cmd_serve(cli.build_parser().parse_args(["serve"]))


# ============================================================== ①b resolve_data_dir 委托


def test_resolve_data_dir_takes_the_config_value_verbatim(config: AppConfig) -> None:
    assert resolve_data_dir(config) == config.data_dir
    assert resolve_data_dir(config).is_absolute(), "前提：注入的 data_dir 是绝对路径"


def test_resolve_data_dir_without_config_matches_the_config_module(tmp_path: Path) -> None:
    """不给 config ⇒ 转发 ``config.resolve_data_dir``（其内部再委托 ``infra.db.paths``）。"""
    environ = {"CAMPAIGNLAB_DATA_DIR": str(tmp_path / "nested")}
    assert resolve_data_dir(environ=environ, home=tmp_path) == config_resolve_data_dir(
        environ, tmp_path
    )
    # 相对值原样透传：不在这里补 expanduser／resolve（禁自拼，也禁「顺手修正」）
    relative = {"CAMPAIGNLAB_DATA_DIR": "relative/data"}
    assert resolve_data_dir(environ=relative, home=tmp_path) == config_resolve_data_dir(
        relative, tmp_path
    )


def test_resolve_data_dir_never_self_assembles_paths() -> None:
    """design §9 点名「必须委托 ``infra.db.paths``／``AppConfig``，**禁自拼**」的静态守护。

    三条判据：函数体内不得有 ``/`` 路径拼接、不得调 ``joinpath``/``expanduser``/``resolve``/
    ``mkdir``、不得出现数据目录子目录名字面量；且必须真的调到转发目标。
    """
    node = _function_node("resolve_data_dir")
    for child in ast.walk(node):
        if isinstance(child, ast.BinOp):
            assert not isinstance(child.op, ast.Div), "禁在 deps 里拼路径"
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            assert child.func.attr not in {
                "joinpath",
                "expanduser",
                "resolve",
                "mkdir",
                "absolute",
            }, f"禁在 deps 里加工路径：{child.func.attr}"
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            assert child.value not in {
                "state",
                "results",
                "tmp",
                "jobs",
                "raw",
                "snapshots",
                "exports",
                "logs",
            }, f"禁把数据目录子目录名写进 deps：{child.value!r}"
    called_names = {
        child.func.id
        for child in ast.walk(node)
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
    }
    assert "resolve_configured_data_dir" in called_names, "必须转发到 config 层的同名函数"


# ======================================================================= ①c get_job_store


def test_get_job_store_is_bound_to_the_configured_database(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """提供器给出的 store 真的连着 ``config.database_url`` 指的那个库（跑一次入队＋回读）。"""
    target = get_job_store(config=config)
    assert isinstance(target, JobStore)
    target.enqueue(
        workspace_id=WS,
        kind="COMPARE",
        input_json=canonical_json({"snapshot": "S-1"}),
        input_digest=INPUT_DIGEST,
        now=clock.now(),
        job_id=JOB,
    )
    record = target.get_job(workspace_id=WS, job_id=JOB)
    assert record is not None, "必须能在同一个库上回读到刚入队的作业"
    assert record.state == "QUEUED"
    assert _job_state(engine, JOB) == "QUEUED", "两个 Engine 指向的必须是同一个库文件"


# =========================================================================== ③ A169 / S2c


def test_deps_exports_exactly_the_four_design_symbols() -> None:
    """design §9 点名的四个符号，逐字不多不少（A151：这是**下限**，私有辅助不在 ``__all__``）。"""
    assert sorted(deps.__all__) == sorted(
        ["get_job_store", "get_job_service", "get_artifact_writer", "resolve_data_dir"]
    )
    for symbol in deps.__all__:
        assert callable(getattr(deps, symbol)), symbol


def test_deps_module_keeps_the_lazy_import_form_after_s2c_landed() -> None:
    """A169 / A207：``service.py`` 已落地，但 ``deps.py`` 的**延迟加载形态**必须一字不动。

    原判据是「``service.py`` 缺席时本模块照样 import 成功」，其自带前提断言明写
    「它已出现 ⇒ 请删掉 deps.py 里的 type: ignore[import-not-found] **并改写本用例**」——
    S2c 照办（A207），本条即改写后的形态。改钉**静态面**是因为「import deps 不传递拉起
    worker.service」这件事在 ``service.py`` 存在之后已无法用 ``sys.modules`` 观测：
    同一 pytest 会话里 ``tests/unit/test_worker_service.py`` 早就导入过它了。

    于是钉三条：① 模块级（非 ``TYPE_CHECKING``）没有对 ``worker.service`` 的导入；
    ② ``deps`` 命名空间里没有运行期绑定的 ``JobService``；③ 返回注解仍是字符串
    ``"JobService"``（``from __future__ import annotations`` 的形态，S4 的路由签名要用）。
    """
    assert SERVICE_PATH.is_file(), "前提：S2c 已交付 worker/service.py"
    deps_path = SERVICE_PATH.with_name("deps.py")
    tree = ast.parse(deps_path.read_text(encoding="utf-8"))
    eager = [
        node.lineno
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == SERVICE_MODULE
    ]
    assert eager == [], f"deps.py 不得在模块级导入 worker.service（延迟加载形态）：行 {eager}"
    assert not hasattr(deps, "JobService"), "deps 不得在运行期绑定 JobService"
    assert deps.get_job_service.__annotations__["return"] == "JobService"


def test_get_job_service_names_the_module_when_the_lazy_import_fails(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """延迟导入失败 ⇒ ``RuntimeError`` 且文本指名模块，**不**静默返回 ``None`` 或替身。

    S2c 已交付 ``worker/service.py``，「缺席」不再能靠真实文件状态制造，故改用
    ``monkeypatch`` 把 ``_SERVICE_MODULE`` 指到一个不存在的模块名：走的仍是
    ``_load_service_module`` 里同一条 ``ModuleNotFoundError -> RuntimeError`` 分支，
    判据强度不降反升（原来那条只能证明「文件不在时报错」，这条证明「导入失败就报错」）。

    ``_SERVICE_MISSING`` 常量文本里「S2c 尚未交付」的措辞在 S2c 落地后已过期，但
    ``deps.py`` 本棒只准删 :55 的 ignore 注释（A207），故不改它 —— 已报 U 项。
    """
    monkeypatch.setattr(deps, "_SERVICE_MODULE", SERVICE_MODULE + "_absent_probe")
    with pytest.raises(RuntimeError) as excinfo:
        get_job_service(config=config)
    assert SERVICE_MODULE in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, ModuleNotFoundError), (
        "必须保留 ModuleNotFoundError 作为 __cause__"
    )


def test_get_job_service_lazily_resolves_the_module_once_it_exists(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """延迟导入这条路**真的通**：注入桩模块后能取到类、能构造、能把 store 传进去。

    只测错误分支的话，「延迟导入」与「永远抛错」是无法区分的 —— 这条就是那个区分器。
    """
    captured: dict[str, object] = {}

    class _StubJobService:
        def __init__(self, *, store: JobStore) -> None:
            captured["store"] = store

    stub = types.ModuleType(SERVICE_MODULE)
    # 经 __dict__ 写：直接赋值会被 mypy 判 ModuleType 无此属性，setattr 常量名会撞 ruff B010
    stub.__dict__["JobService"] = _StubJobService
    monkeypatch.setitem(sys.modules, SERVICE_MODULE, stub)

    service = get_job_service(config=config)
    assert isinstance(service, _StubJobService)
    assert isinstance(captured["store"], JobStore)


def test_get_job_service_rejects_a_module_without_the_class(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """模块在、类不在 ⇒ 也要指名报错，禁 ``AttributeError`` 裸奔。"""
    stub = types.ModuleType(SERVICE_MODULE)
    monkeypatch.setitem(sys.modules, SERVICE_MODULE, stub)
    with pytest.raises(RuntimeError, match="JobService"):
        get_job_service(config=config)


# ========================================================================== ② A154 接线


def test_a154_option_a_succeed_with_empty_artifacts_registers_exactly_one_row(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """接法 (a)：``commit()`` 在 ``BEGIN IMMEDIATE`` 内登记，随后 ``succeed(artifacts=())``。

    design §11-A154：制品行已由 ``commit()`` 在同一事务内登记，故 ``succeed`` 的
    ``artifacts`` 必须是**空**的。断言 ``artifacts`` 表恰 1 行（design §11:157 的判据）。
    """
    target_store = get_job_store(config=config)
    writer = get_artifact_writer(config=config)
    lease = _running_job(target_store, clock)
    with writer.begin(WS, lease.job_id, lease.attempt) as stage:
        stage.write(PAYLOAD)
        with short_transaction(engine) as conn:
            committed = writer.commit(
                conn,
                stage,
                workspace_id=WS,
                kind=ARTIFACT_KIND_JOB_RESULT,
                now=clock.now(),
            )
    record = target_store.succeed(
        lease,
        result_ref=ObjectRef(kind="job", id=lease.job_id),
        now=clock.now(),
        artifacts=(),
    )
    assert record.state == "SUCCEEDED"
    assert _artifact_count(engine) == 1, "同一 (workspace_id,kind,sha256) 只准落 1 行"
    assert _job_state(engine, lease.job_id) == "SUCCEEDED"
    assert committed.reused_row is False, "前置条件：这是首次登记"


def test_a154_option_b_single_transaction_commit_then_terminal_update(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """接法 (b)：同一事务内先 ``commit()`` 再直接发终态谓词 UPDATE（不经 ``succeed``）。"""
    target_store = get_job_store(config=config)
    writer = get_artifact_writer(config=config)
    lease = _running_job(target_store, clock)
    result_json = canonical_json(ObjectRef(kind="job", id=lease.job_id).model_dump(mode="json"))
    with writer.begin(WS, lease.job_id, lease.attempt) as stage:
        stage.write(PAYLOAD)
        with short_transaction(engine) as conn:
            writer.commit(
                conn,
                stage,
                workspace_id=WS,
                kind=ARTIFACT_KIND_JOB_RESULT,
                now=clock.now(),
            )
            touched = JobRepository().mark_succeeded(
                conn,
                workspace_id=lease.workspace_id,
                job_id=lease.job_id,
                attempt=lease.attempt,
                lease_token=lease.token,
                result_json=result_json,
            )
            assert touched == 1, "终态谓词 UPDATE 必须命中租约守卫"
    assert _artifact_count(engine) == 1
    assert _job_state(engine, lease.job_id) == "SUCCEEDED"


def test_a154_forbidden_third_wiring_is_red(
    config: AppConfig, engine: Engine, clock: FixedClock
) -> None:
    """**禁**的第三种：先 ``commit()`` 再把 record 交回 ``succeed(artifacts=...)``。

    必须撞 ``UNIQUE(workspace_id,kind,sha256)`` 判红，且整个事务回滚：
    ``artifacts`` 仍是 ``commit()`` 留下的那 1 行、作业仍停在 ``RUNNING``
    （不得写出第二个终态，AC-029「取消/完成只有一个终态」同口径）。
    """
    target_store = get_job_store(config=config)
    writer = get_artifact_writer(config=config)
    lease = _running_job(target_store, clock)
    with writer.begin(WS, lease.job_id, lease.attempt) as stage:
        stage.write(PAYLOAD)
        with short_transaction(engine) as conn:
            committed = writer.commit(
                conn,
                stage,
                workspace_id=WS,
                kind=ARTIFACT_KIND_JOB_RESULT,
                now=clock.now(),
            )
    assert _artifact_count(engine) == 1, "前置条件：commit() 已登记 1 行"

    duplicate = ArtifactRecord(
        workspace_id=committed.workspace_id,
        id=committed.artifact_id,
        kind=committed.kind,
        sha256=committed.sha256,
        relative_path=committed.relative_path,
        byte_size=committed.byte_size,
        created_at=clock.now().isoformat(),
    )
    with pytest.raises(IntegrityError):
        target_store.succeed(
            lease,
            result_ref=ObjectRef(kind="job", id=lease.job_id),
            now=clock.now(),
            artifacts=(duplicate,),
        )
    assert _artifact_count(engine) == 1, "回滚后不得多出第二行"
    assert _job_state(engine, lease.job_id) == "RUNNING", "回滚后不得写出终态"
