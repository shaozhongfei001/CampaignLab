"""worker 侧依赖装配（M0-04/S2b-2；design §9 ``worker/deps.py``）。

本文件被指派的符号：``resolve_data_dir`` / ``get_job_store`` / ``get_job_service`` /
``get_artifact_writer``。四个都是**薄装配**：只把已冻结的件按依赖顺序接起来，
不新建第二套配置解析、不新建第二个哈希实现、不含任何 SQL 文本。

三条落地口径（每条都有守护用例，见 ``tests/integration/jobs/test_worker_deps.py``）：

1. **A156 启动闸**：``get_artifact_writer`` 在 ``return`` **之前**必调一次
   ``ArtifactWriter.verify_same_filesystem()``。design §5:47 要求「启动即
   ``verify_same_filesystem()``」，但 S3 的写权止于 ``infra/artifacts.py``，装配点在本
   文件 —— 少了这一调，跨设备的数据目录只会在第一次 ``commit()`` 时以 ``EXDEV`` 暴露，
   而不是在进程启动期就被拦下。不符时 ``verify_same_filesystem`` 抛
   ``config.ConfigError``，而 ``cli.cmd_serve`` 把 ``ConfigError`` 统一映射为 **rc=2**
   （``cli.py`` 的 ``except ConfigError: ... return 2``），「st_dev 不符 → ConfigError →
   CLI rc=2」这条链因此成立。``scripts/doctor.sh`` 的部署期可见性属 FU-30，不在本写集。
2. **A169（S2c 尚未交付）**：``worker/service.py`` 属 M0-04/S2c，排在本子任务之后，
   当前**不存在**。故 ``JobService`` 只在 ``TYPE_CHECKING`` 下导入（仅供注解），运行期用
   ``importlib`` 延迟取：本模块在 ``service.py`` 缺席时**照样 import 成功**、mypy strict
   干净，只有真的调用 ``get_job_service()`` 才报错，且报错文本直指 S2c —— 不静默返回
   ``None``、不静默造替身。
   **给 S2c 的硬提醒**：``worker/service.py`` 落地时必须**同步删掉**下面那条
   ``# type: ignore[import-not-found]``。strict 开着 ``warn_unused_ignores``，留着会让
   全表 mypy 判红（已实测：模块缺席时 ``Success``，模块出现后
   ``error: Unused "type: ignore" comment [unused-ignore]``）。
3. **禁自拼路径**（design §9 对 ``resolve_data_dir`` 的点名要求）：数据目录委托
   ``AppConfig.data_dir`` 或 ``config.resolve_data_dir``（其内部再委托 ``infra.db.paths``
   的 ``expand_user`` / ``default_data_dir``），库位置委托
   ``application.build_database_runtime``（ADR-005 §2.4 五级链的唯一实现）。
   本文件**一个路径片段字面量都没有**。

分层（design §11-A153 硬约束）：本模块 import ``infra``／``api``／``application`` 都是
正向边，合法；``worker/integrity.py`` 同理。**禁**把这里的符号经 ``worker/__init__.py``
再导出 —— 那会让「导入 ``infra.artifacts`` 传递执行整个 worker 包」重新成环。
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Final, cast

from fastapi import Depends

from campaignlab.api.deps import get_config
from campaignlab.application import build_database_runtime
from campaignlab.config import AppConfig
from campaignlab.config import resolve_data_dir as resolve_configured_data_dir
from campaignlab.infra.artifacts import ArtifactWriter
from campaignlab.worker.store import JobStore

if TYPE_CHECKING:
    from campaignlab.worker.service import JobService

__all__ = [
    "get_artifact_writer",
    "get_job_service",
    "get_job_store",
    "resolve_data_dir",
]

#: S2c 的落点（A169）。模块名与类名各只出现一次，运行期取类与注解共用同一份拼写。
_SERVICE_MODULE: Final = "campaignlab.worker.service"
_SERVICE_CLASS: Final = "JobService"
_SERVICE_MISSING: Final = (
    "campaignlab.worker.service 尚不存在：JobService 属 M0-04/S2c（A169 新立，排在 "
    "S2b-2 之后）。本模块刻意不在模块级导入它，以便 S2c 落地前 worker.deps 仍可 import；"
    "调用 get_job_service() 需等 S2c 交付 worker/service.py:JobService。"
)


def resolve_data_dir(
    config: AppConfig | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """``<data_dir>`` 的 worker 侧取用点（design §9：**禁自拼**）。

    两条委托路径，本函数不写任何路径片段：

    - 给了 ``config`` → 直接取 ``AppConfig.data_dir``（``config.load_config`` 已经过
      ``resolve_data_dir`` → ``paths.expand_user`` / ``paths.default_data_dir``）。
    - 没给 → 转发 ``campaignlab.config.resolve_data_dir(environ, home)``；``environ`` /
      ``home`` 可注入，故测试无需改进程环境即可复现（与 ``config`` 模块同一取向）。

    刻意**不**在这里补 ``expanduser()`` / ``resolve()`` / ``mkdir``：数据目录是否绝对、
    是否存在，分别由 ``ArtifactWriter.__init__`` 与 ``doctor`` 的数据目录检查负责。
    在这里再加一层「顺手修正」就等于开出第二套口径（D-014 / ADR-005 §2.4 裁定 2 同类）。
    """
    if config is not None:
        return config.data_dir
    return resolve_configured_data_dir(environ, home)


# A47 / 手册 §9.9：``Depends(...)`` 作形参默认值与 ruff B008 冲突，而 design §1 冻结的
# 路由形状就是 ``svc: JobService = Depends(get_job_service)``（改成 ``Annotated`` 形会动
# 冻结签名），故与 ``api/health.py`` / ``api/workspaces.py`` 同体例就地豁免。三个提供器
# 一律以 ``Depends(get_config)`` 取配置：``get_config`` 读的是 ``create_app()`` 已装配的
# ``app.state.config``，故本文件不需要 ``api/app.py`` 再新增任何 state 属性。
def get_job_store(config: AppConfig = Depends(get_config)) -> JobStore:  # noqa: B008
    """``JobStore`` 提供器（design §9）。

    库位置**完全委托** ``build_database_runtime(database_url=config.database_url)``，与
    ``cli.cmd_serve`` 同一入口：``config.database_url`` 已是五级链解析后的值，显式传回
    记为 ``CALLER_SUPPLIED``，不会另起第二套解析。

    每次解析新建一个 ``Engine``。这是刻意的：``make_engine`` 默认 ``NullPool``（不缓存
    连接），故 ``Engine`` 对象随请求结束被回收即可，没有连接需要 ``dispose``；而 FastAPI
    默认 ``use_cache=True``，同一请求内本提供器只解析一次。是否改成「应用级共享一个
    runtime 挂在 ``app.state`` 上」属装配策略，归 ``api/app.py``（不在本写集），
    已按 A159 报 U 项，未自行决定。
    """
    runtime = build_database_runtime(database_url=config.database_url)
    return JobStore(engine=runtime.engine)


def get_job_service(config: AppConfig = Depends(get_config)) -> JobService:  # noqa: B008
    """``JobService`` 提供器（design §1：``svc: JobService = Depends(get_job_service)``）。

    **A169**：运行期用 ``importlib`` 延迟取 ``worker/service.py``（S2c 的交付物），
    模块级只在 ``TYPE_CHECKING`` 下引用其类名做注解。缺席时 import 本模块照样成功；
    调用则抛 ``RuntimeError`` 并指明归属，**不静默降级**。
    """
    module = _load_service_module()
    factory = getattr(module, _SERVICE_CLASS, None)
    if not callable(factory):
        raise RuntimeError(
            f"{_SERVICE_MODULE} 里没有可调用的 {_SERVICE_CLASS}（A169：S2c 的交付符号）"
        )
    # 构造参数按 design §9「JobService 的方法面＝list_jobs/get_job/cancel_job/retry_job，
    # 事务边界全在 JobStore」推定为 store=；S2c 若签名不同，改这一行即可（已报 U 项）。
    return cast("JobService", factory(store=get_job_store(config)))


def get_artifact_writer(config: AppConfig = Depends(get_config)) -> ArtifactWriter:  # noqa: B008
    """``ArtifactWriter`` 提供器，**返回前必过同盘闸**（A156 / design §5:47）。

    顺序不可调换：先构造（``ArtifactWriter.__init__`` 会校验 ``data_dir`` 是绝对路径），
    再 ``verify_same_filesystem()``，通过了才 ``return``。这样调用方拿到的 writer 一定是
    「暂存根与终态根同设备」的 —— 跨设备时它抛 ``config.ConfigError`` 而不是返回一个
    注定在 ``commit()`` 时 ``EXDEV`` 的对象。
    """
    writer = ArtifactWriter(resolve_data_dir(config))
    writer.verify_same_filesystem()
    return writer


def _load_service_module() -> ModuleType:
    """延迟导入 ``worker/service.py``；缺席即抛错并指明归属（A169）。"""
    try:
        return importlib.import_module(_SERVICE_MODULE)
    except ModuleNotFoundError as exc:
        raise RuntimeError(_SERVICE_MISSING) from exc
