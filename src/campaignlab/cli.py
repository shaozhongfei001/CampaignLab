"""命令行：``doctor`` 与 ``serve``（M0-02 · S3c；design §6 ``cli.py``）。

命令契约（``spec/CampaignLab-SDD-v1.0/framework/TOOLCHAIN.md:21``）：
``doctor`` **检查绑定、版本、数据目录、数据库和 worker** 五项；``serve`` 启动 HTTP 与后台进程。

退出码口径（与 ``scripts/doctor.sh`` 的 PASS/WARN/FAIL 语义对齐）：

- ``0``＝无 FAIL（可能有 WARN）；``1``＝有 FAIL，或配置本身不可用；
- ``2``＝用法错误／拒绝启动（非回环绑定、本机用户名不合法 —— design §2「启动失败 rc=2」）。

**WARN 不改变退出码**，这是刻意的：doctor 是**诊断**命令，「库尚未迁移」「worker 未装配」
是可恢复的运行状态而非损坏；把它们判成 FAIL 会让 ``python -m campaignlab doctor`` 在任何
一个全新检出上恒 rc=1，gate 就失去了信号价值。FAIL 只留给**真的坏了**的情形
（契约读不到、非回环绑定、数据目录不可写、库文件损坏、已迁移但 revision 与 head 不一致）。
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import socket
import sqlite3
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Final, Literal, TextIO

from campaignlab.config import (
    AppConfig,
    ConfigError,
    LocalIdentityError,
    load_config,
    repo_root,
    resolve_local_identity,
)
from campaignlab.infra.db.migration_head import read_migration_head

__all__ = [
    "CHECK_IDS",
    "CheckResult",
    "build_parser",
    "cmd_doctor",
    "cmd_serve",
    "format_summary",
    "run_doctor",
    "run_doctor_checks",
]

Level = Literal["PASS", "WARN", "FAIL"]

#: TOOLCHAIN.md:21 点名的五项检查，顺序即输出顺序（确定性要求）。
CHECK_IDS: Final[tuple[str, ...]] = ("version", "binding", "data_dir", "database", "worker")

#: 迁移目录（相对仓库根）。alembic head 从这里的脚本目录读取，禁硬编码 revision 串。
MIGRATIONS_DIR: Final = "migrations"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """单项检查结果。``check`` 必须取自 ``CHECK_IDS``（分母断言见 ``run_doctor``）。"""

    level: Level
    check: str
    detail: str


def _port_in_use(host: str, port: int) -> bool:
    """探测 ``host:port`` 是否已被占用（doctor 只读探测，不绑定、不监听）。"""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            return sock.connect_ex((host, port)) == 0
    except OSError:
        return False


def _migration_head() -> str | None:
    """alembic 脚本目录的当前 head；取不到返回 ``None``（调用方报 WARN，不猜 revision）。

    实现已收口到 ``campaignlab.infra.db.migration_head``（D-028 / 裁定 A80 / FU-8），本函数
    只剩委托：传进去的还是收口前自己算的那个 ``repo_root() / MIGRATIONS_DIR``，ini 路径、
    head 判据与降级口径逐字不变。
    """
    return read_migration_head(repo_root() / MIGRATIONS_DIR)


def _check_version(config: AppConfig) -> CheckResult:
    return CheckResult(
        "PASS",
        "version",
        f"app={config.app_version} contract={config.contract_version} "
        f"source={config.contract_path}",
    )


def _check_binding(config: AppConfig) -> CheckResult:
    if not config.is_loopback():
        return CheckResult(
            "FAIL",
            "binding",
            f"host={config.host} 非回环地址；OPERATIONS.md 规定生产式本地运行只绑定 127.0.0.1",
        )
    if _port_in_use(config.host, config.port):
        return CheckResult(
            "WARN",
            "binding",
            f"{config.host}:{config.port} 已被占用（serve 会失败）；回环绑定策略本身合规",
        )
    return CheckResult("PASS", "binding", f"{config.host}:{config.port} 回环且空闲，可 serve")


def _check_data_dir(config: AppConfig) -> CheckResult:
    data_dir = config.data_dir
    if not data_dir.exists():
        return CheckResult(
            "WARN",
            "data_dir",
            f"{data_dir} 尚不存在（首次 serve/迁移时创建）；level={config.database.level.name}",
        )
    if not os.access(data_dir, os.W_OK):
        return CheckResult("FAIL", "data_dir", f"{data_dir} 不可写")
    missing = config.missing_subdirs()
    if missing:
        return CheckResult(
            "WARN", "data_dir", f"{data_dir} 可写，但缺 OPERATIONS.md 子目录：{','.join(missing)}"
        )
    return CheckResult("PASS", "data_dir", f"{data_dir} 可写且七个子目录齐备")


def _check_database(config: AppConfig) -> CheckResult:
    path = config.database_path
    level = config.database.level.name
    if path is None:
        return CheckResult(
            "WARN", "database", f"解析结果非文件型库（url={config.database_url} level={level}）"
        )
    if not path.is_file():
        return CheckResult(
            "WARN",
            "database",
            f"{path} 不存在（level={level} source={config.database.source}）；"
            "先执行 alembic upgrade head",
        )
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type=? AND name=?",
                ("table", "alembic_version"),
            ).fetchall()
            current = (
                conn.execute("SELECT version_num FROM alembic_version").fetchone() if rows else None
            )
    except sqlite3.Error as exc:
        return CheckResult("FAIL", "database", f"{path} 打开或 PRAGMA 失败：{exc}")
    if not integrity or str(integrity[0]) != "ok":
        return CheckResult("FAIL", "database", f"{path} integrity_check={integrity!r}")
    if fk_violations:
        return CheckResult(
            "FAIL", "database", f"{path} foreign_key_check 命中 {len(fk_violations)} 行"
        )
    if current is None:
        return CheckResult(
            "WARN", "database", f"{path} 完整但无 alembic_version（尚未迁移）；level={level}"
        )
    head = _migration_head()
    revision = str(current[0])
    if head is None:
        return CheckResult(
            "WARN", "database", f"{path} revision={revision}，但取不到 migrations head，无法比对"
        )
    if revision != head:
        return CheckResult(
            "FAIL", "database", f"{path} revision={revision} != migrations head={head}"
        )
    return CheckResult("PASS", "database", f"{path} revision={revision}==head，PRAGMA 双检通过")


def _check_worker(config: AppConfig) -> CheckResult:
    spec_found = importlib.util.find_spec("campaignlab.application.worker") is not None
    if not spec_found:
        return CheckResult(
            "WARN",
            "worker",
            "campaignlab.application.worker 未装配（属 M0-02/S3d，Round 6）；"
            f"心跳窗口配置={config.worker_heartbeat_ttl_seconds}s",
        )
    return CheckResult(
        "PASS",
        "worker",
        f"campaignlab.application.worker 可导入；心跳窗口={config.worker_heartbeat_ttl_seconds}s",
    )


def run_doctor_checks(config: AppConfig) -> tuple[CheckResult, ...]:
    """按 ``CHECK_IDS`` 固定顺序跑五项检查（顺序固定＝输出确定性）。"""
    checks: dict[str, Callable[[AppConfig], CheckResult]] = {
        "version": _check_version,
        "binding": _check_binding,
        "data_dir": _check_data_dir,
        "database": _check_database,
        "worker": _check_worker,
    }
    results = tuple(checks[name](config) for name in CHECK_IDS)
    # 分母断言：少跑一项就等于把 gate 悄悄放宽（对齐 test_doctor_determinism.py 的口径）。
    if len(results) != len(CHECK_IDS):
        raise AssertionError(f"doctor 检查项数不符：{len(results)} != {len(CHECK_IDS)}")
    return results


def format_summary(results: Sequence[CheckResult]) -> str:
    """``PASS=n WARN=n FAIL=n RESULT=<HEALTHY|DEGRADED|BROKEN>``。"""
    levels: Final[tuple[str, ...]] = ("PASS", "WARN", "FAIL")
    counts = {level: sum(1 for r in results if r.level == level) for level in levels}
    failed = counts["FAIL"]
    if failed:
        result = "BROKEN"
    elif counts["WARN"]:
        result = "DEGRADED"
    else:
        result = "HEALTHY"
    return f"PASS={counts['PASS']} WARN={counts['WARN']} FAIL={failed} RESULT={result}"


def run_doctor(config: AppConfig, out: TextIO | None = None) -> int:
    """跑检查并打印；返回退出码（0＝无 FAIL）。

    ``out`` 默认在**调用期**解析 ``sys.stdout``：写成 ``out: TextIO = sys.stdout`` 会在
    def 期绑定真实 stdout，pytest 的 ``capsys`` 就抓不到任何输出（已实测踩坑）。
    """
    stream: TextIO = sys.stdout if out is None else out
    results = run_doctor_checks(config)
    loc = config.database
    print(f"[doctor] host={config.host} port={config.port} data_dir={config.data_dir}", file=stream)
    print(f"[doctor] db={loc.url} level={loc.level.name} source={loc.source}", file=stream)
    for item in results:
        print(f"{item.level:<5} {item.check:<9} {item.detail}", file=stream)
    failed = sum(1 for r in results if r.level == "FAIL")
    print(f"  {format_summary(results)}", file=stream)
    return 1 if failed else 0


def _apply_overrides(config: AppConfig, args: argparse.Namespace) -> AppConfig:
    """CLI 的 ``--host`` / ``--port`` 覆盖（只覆盖这两项，不新增任何路径解析口径）。"""
    host = getattr(args, "host", None) or config.host
    port = getattr(args, "port", None) or config.port
    return replace(config, host=host, port=int(port))


def build_parser() -> argparse.ArgumentParser:
    """构造解析器。子命令：``doctor`` / ``serve``（``backup``/``restore`` 不属 M0-02）。"""
    parser = argparse.ArgumentParser(
        prog="python -m campaignlab",
        description="CampaignLab 单机服务端 CLI（TOOLCHAIN.md:21 的命令契约）",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    doctor = sub.add_parser("doctor", help="检查绑定、版本、数据目录、数据库和 worker")
    doctor.add_argument("--host", default=None, help="覆盖绑定地址（默认取配置/127.0.0.1）")
    doctor.add_argument("--port", type=int, default=None, help="覆盖端口（默认 8000）")
    doctor.set_defaults(handler=cmd_doctor)

    serve = sub.add_parser("serve", help="启动 HTTP 与后台进程")
    serve.add_argument("--host", default=None, help="覆盖绑定地址（只允许回环）")
    serve.add_argument(
        "--port",
        type=int,
        default=None,
        help="覆盖端口（默认 8000，与 web/vite.config.ts 的 /api proxy 对齐）",
    )
    serve.set_defaults(handler=cmd_serve)
    return parser


def cmd_doctor(args: argparse.Namespace) -> int:
    """``doctor`` 子命令。配置不可用 → 记一条 FAIL version 并返回 1。"""
    try:
        config = _apply_overrides(load_config(), args)
    except ConfigError as exc:
        print(f"FAIL  version   配置不可用：{exc}", file=sys.stdout)
        print("  PASS=0 WARN=0 FAIL=1 RESULT=BROKEN", file=sys.stdout)
        return 1
    return run_doctor(config)


def cmd_serve(args: argparse.Namespace) -> int:
    """``serve`` 子命令：装配应用并交给 uvicorn。

    拒绝启动的情形一律 **rc=2**（用法/身份错误），与 doctor 的 rc=1（检查失败）区分开。
    """
    try:
        config = _apply_overrides(load_config(), args)
    except ConfigError as exc:
        print(f"[serve] 配置错误：{exc}", file=sys.stderr)
        return 2
    if not config.is_loopback():
        print(
            f"[serve] 拒绝启动：host={config.host} 非回环地址（OPERATIONS.md：只绑定 127.0.0.1）",
            file=sys.stderr,
        )
        return 2
    try:
        identity = resolve_local_identity()
    except LocalIdentityError as exc:
        print(f"[serve] 拒绝启动：{exc}", file=sys.stderr)
        return 2

    # S3d（裁定 Q9/§9.10）：装配用例服务与 worker，原「会话服务未装配」WARN 随之移除。
    # import 全部留在函数内：doctor 不该为一个用不到的 HTTP 栈付导入成本（既有口径）。
    from campaignlab.api.app import create_app
    from campaignlab.application import build_database_runtime
    from campaignlab.application.health_service import HealthService
    from campaignlab.application.session_service import (
        SessionService,
        SessionStore,
        SessionTokenStore,
    )
    from campaignlab.application.worker import WorkerSupervisor
    from campaignlab.application.workspace_service import WorkspaceService
    from campaignlab.clock import SystemClock

    clock = SystemClock()
    runtime = build_database_runtime(database_url=config.database_url)
    tokens = SessionTokenStore(ttl_seconds=config.token_ttl_seconds)
    worker = WorkerSupervisor(
        clock=clock,
        engine=runtime.engine,
        heartbeat_ttl_seconds=config.worker_heartbeat_ttl_seconds,
    )
    app = create_app(
        config,
        clock=clock,
        session_service=SessionService(
            tokens=tokens, sessions=SessionStore(ttl_seconds=config.session_ttl_seconds)
        ),
        health_service=HealthService(
            config=config, clock=clock, engine=runtime.engine, worker=worker
        ),
        workspace_service=WorkspaceService(engine=runtime.engine, clock=clock, config=config),
    )
    print(
        f"[serve] actor={identity.actor_id} roles={len(identity.allowed_roles)} "
        f"contract={config.contract_version} db={config.database_url}",
        file=sys.stderr,
    )
    print(f"[serve] http://{config.host}:{config.port}/api/v1/health", file=sys.stderr)
    # design §2：入口令牌一次性、60s 有效、只存进程内存；进程重启即失效（AC-035）。
    token = tokens.mint(identity, clock.now())
    print(
        f"[serve] entry_token={token} ttl={config.token_ttl_seconds}s 一次性"
        "（换取通道：POST /api/v1/session/exchange）",
        file=sys.stderr,
    )
    import uvicorn

    worker.start()
    try:
        uvicorn.run(app, host=config.host, port=config.port, log_level="info")
    finally:
        worker.stop()
        runtime.dispose()
    return 0
