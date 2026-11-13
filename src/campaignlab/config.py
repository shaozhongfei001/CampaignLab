"""运行期配置与本机身份（M0-02 · S3c；design §6 指派 ``config.py``）。

三条硬约束决定本文件形状：

1. **路径解析单一来源**（ADR-005 §2.4 裁定 2）：库文件位置一律**委托**
   ``campaignlab.infra.db.paths`` 的既有访问器（``resolve_database_location`` /
   ``default_data_dir`` / ``expand_user`` / ``DATA_DIR_ENV``）。本文件**不重实现**五级解析链，
   也不得改 ``paths.py``（不在 S3c 写权限内）。因此「alembic 建出来的库」与
   「运行期打开的库」必然是同一个文件。
2. **运行参数默认值**（ADR-005 §2.3）：``session_ttl_seconds=3600``、
   ``MAX_JSON_BODY_BYTES=1048576``、``WORKER_HEARTBEAT_TTL_SECONDS=15``，三者必须**可注入**
   （测试用小值，禁 sleep 到真实 TTL）。一次性令牌 ``TOKEN_TTL_SECONDS=60`` 是**另一个对象**
   （OPERATIONS.md），与会话 TTL 不得混用。
3. **契约版本禁硬编码**（D-004 教训）：``contract_version`` 运行时从活契约
   ``contracts/openapi.json`` 的 ``info.version`` 读取。

``serve`` 默认端口 **8000**：``state.json → decisions.dev_proxy_target`` 已 ACCEPTED
（编排器实测 127.0.0.1:8000 FREE、3000/3001/3002 BUSY），且 ``web/vite.config.ts`` 的
``/api`` proxy 已硬指 ``http://127.0.0.1:8000``——改这个默认值会静默切断前端联调。
"""

from __future__ import annotations

import getpass
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from campaignlab import __version__
from campaignlab.domain.ids import is_resource_id
from campaignlab.infra.db.paths import (
    DATA_DIR_ENV,
    DatabaseLocation,
    default_data_dir,
    expand_user,
    resolve_database_location,
)

if TYPE_CHECKING:
    # ``Role`` 的权威定义在 ``api/common.py``（design §6 未把它划给 domain 层）。
    # 只在类型检查期引用，避免 ``config -> api`` 的运行期导入边。
    from campaignlab.api.common import Role

__all__ = [
    "API_PREFIX",
    "DATA_DIR_SUBDIRS",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_SESSION_TTL_SECONDS",
    "LOCAL_ROLES",
    "MAX_JSON_BODY_BYTES",
    "TOKEN_TTL_SECONDS",
    "WORKER_HEARTBEAT_TTL_SECONDS",
    "AppConfig",
    "AppIdentity",
    "ConfigError",
    "ContractVersionError",
    "LocalIdentityError",
    "load_config",
    "read_contract_version",
    "repo_root",
    "resolve_contract_path",
    "resolve_data_dir",
    "resolve_local_identity",
]

#: OPERATIONS.md：一次性入口令牌**仅首次可用、有效期 60 秒、内存存放**（AC-001）。
TOKEN_TTL_SECONDS: Final = 60
#: ADR-005 §2.3：会话 TTL 1 小时。与上面的 60s 令牌是两个不同对象，禁混用。
DEFAULT_SESSION_TTL_SECONDS: Final = 3600
#: ADR-005 §2.3：JSON 正文上限 1 MiB，超限 413。**不适用**于文件上传（8 MiB / 64 MiB）。
MAX_JSON_BODY_BYTES: Final = 1_048_576
#: ADR-005 §2.3：超过该窗口无心跳则 ``Health.worker`` 报非健康（AC-001 取证点）。
WORKER_HEARTBEAT_TTL_SECONDS: Final = 15

#: OPERATIONS.md：生产式本地运行**只绑定 127.0.0.1**。
DEFAULT_HOST: Final = "127.0.0.1"
#: ``decisions.dev_proxy_target``（ACCEPTED）＋ ``web/vite.config.ts`` 的 ``/api`` proxy 目标。
DEFAULT_PORT: Final = 8000
#: 活契约的路由前缀（切片里 5 个 op 的 ``path`` 均相对于它）。
API_PREFIX: Final = "/api/v1"

#: OPERATIONS.md:17：数据目录必含的七个子目录。
DATA_DIR_SUBDIRS: Final[tuple[str, ...]] = (
    "state",
    "raw",
    "snapshots",
    "results",
    "exports",
    "tmp",
    "logs",
)

#: 允许的运行期覆盖项（不新增解析口径，只覆盖 host/port/契约路径）。
HOST_ENV: Final = "CAMPAIGNLAB_HOST"
PORT_ENV: Final = "CAMPAIGNLAB_PORT"
CONTRACT_PATH_ENV: Final = "CAMPAIGNLAB_CONTRACT_PATH"

#: 回环 host 白名单。非回环绑定一律拒绝启动（OPERATIONS.md「只绑定 127.0.0.1」）。
LOOPBACK_HOSTS: Final[frozenset[str]] = frozenset({"127.0.0.1", "localhost", "::1"})

#: OPERATIONS.md「首版以本机当前 OS 用户操作」：6 个业务角色全给（design §2）。
LOCAL_ROLES: Final[tuple[Role, ...]] = (
    "OPERATOR",
    "DESIGNER",
    "DATA_OWNER",
    "ANALYST",
    "TESTER",
    "REVIEWER",
)


class ConfigError(RuntimeError):
    """配置不可用。CLI 映射为 rc=1（``doctor``）或 rc=2（``serve`` 拒绝启动）。"""


class ContractVersionError(ConfigError):
    """活契约读不到 ``info.version``。禁硬编码兜底（D-004）。"""


class LocalIdentityError(ConfigError):
    """本机身份不合法。design §2：不匹配 ID 正则 → **启动失败 rc=2**。"""


@dataclass(frozen=True, slots=True)
class AppIdentity:
    """本机操作者身份（design §2：``actor_id = actor_name = getpass.getuser()``）。

    **归属说明（S3c 回报 Q 项）**：design §6 把 ``AppIdentity`` 列在
    ``application/session_service.py`` 名下，但它是 ``config.py::resolve_local_identity()``
    的**返回类型**，而 ``resolve_local_identity`` 由 R5-1 划给 S3c。为免 S3d 再定义一份
    （ADR-005 §2.1 单一来源），本类定义在此；``application/session_service.py`` 必须
    ``from campaignlab.config import AppIdentity``，**禁另建同名类**。
    """

    actor_id: str
    actor_name: str
    allowed_roles: tuple[Role, ...]


@dataclass(frozen=True, slots=True)
class AppConfig:
    """一次解析得到的运行期配置。``frozen`` + ``slots``：配置对象不得被就地改写。"""

    host: str
    port: int
    data_dir: Path
    database: DatabaseLocation
    contract_path: Path
    contract_version: str
    app_version: str
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS
    token_ttl_seconds: int = TOKEN_TTL_SECONDS
    max_json_body_bytes: int = MAX_JSON_BODY_BYTES
    worker_heartbeat_ttl_seconds: int = WORKER_HEARTBEAT_TTL_SECONDS

    @property
    def database_url(self) -> str:
        return self.database.url

    @property
    def database_path(self) -> Path | None:
        return self.database.path

    def is_loopback(self) -> bool:
        """``host`` 是否为回环地址（非回环一律拒绝启动，OPERATIONS.md）。"""
        return self.host in LOOPBACK_HOSTS

    def missing_subdirs(self) -> tuple[str, ...]:
        """``data_dir`` 下尚不存在的 OPERATIONS.md 子目录（doctor 报 WARN，不自动创建）。"""
        return tuple(name for name in DATA_DIR_SUBDIRS if not (self.data_dir / name).is_dir())


def repo_root() -> Path:
    """仓库根：``src/campaignlab/config.py`` 上溯两级。

    只用于定位活契约 ``contracts/openapi.json``（D-004：契约版本必须运行时读取）。
    安装成 wheel 后该相对位置不成立，故 ``resolve_contract_path`` 支持环境变量覆盖。
    """
    return Path(__file__).resolve().parents[2]


def resolve_contract_path(environ: Mapping[str, str] | None = None) -> Path:
    """活契约路径：``CAMPAIGNLAB_CONTRACT_PATH`` 优先，否则 ``<repo>/contracts/openapi.json``。"""
    env = os.environ if environ is None else environ
    raw = (env.get(CONTRACT_PATH_ENV) or "").strip()
    if raw:
        return Path(raw).expanduser()
    return repo_root() / "contracts" / "openapi.json"


def read_contract_version(path: Path) -> str:
    """从活契约读 ``info.version``。**禁硬编码兜底**：读不到就报错（D-004 的教训）。"""
    try:
        with path.open(encoding="utf-8") as handle:
            document = json.load(handle)
    except OSError as exc:
        raise ContractVersionError(f"活契约不可读：{path}（{exc}）") from exc
    except json.JSONDecodeError as exc:
        raise ContractVersionError(f"活契约不是合法 JSON：{path}（{exc}）") from exc
    info = document.get("info") if isinstance(document, dict) else None
    version = info.get("version") if isinstance(info, dict) else None
    if not isinstance(version, str) or not version.strip():
        raise ContractVersionError(f"活契约缺少非空 info.version：{path}")
    return version.strip()


def resolve_data_dir(environ: Mapping[str, str] | None = None, home: Path | None = None) -> Path:
    """数据目录（OPERATIONS.md:17）：``CAMPAIGNLAB_DATA_DIR`` 优先，否则默认用户目录。

    委托 ``paths.expand_user`` / ``paths.default_data_dir``——与库路径解析共用同一套
    ``~`` 展开与默认值口径，避免「数据目录」与「库所在目录」各说一套。
    """
    env = os.environ if environ is None else environ
    base_home = Path.home() if home is None else home
    raw = (env.get(DATA_DIR_ENV) or "").strip()
    if raw:
        return expand_user(raw, base_home)
    return default_data_dir(base_home)


def load_config(
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> AppConfig:
    """解析运行期配置。``environ`` / ``home`` 可注入，故测试结果可复现、不改进程环境。

    库位置**完全委托** ``paths.resolve_database_location``（五级链的唯一实现），
    本函数一个分支都不重写。
    """
    env = os.environ if environ is None else environ
    base_home = Path.home() if home is None else home

    host = (env.get(HOST_ENV) or "").strip() or DEFAULT_HOST
    port_raw = (env.get(PORT_ENV) or "").strip()
    if port_raw:
        try:
            port = int(port_raw)
        except ValueError as exc:
            raise ConfigError(f"{PORT_ENV} 不是合法整数端口：{port_raw!r}") from exc
    else:
        port = DEFAULT_PORT
    if not 1 <= port <= 65535:
        raise ConfigError(f"端口越界（须 1–65535）：{port}")

    contract_path = resolve_contract_path(env)
    return AppConfig(
        host=host,
        port=port,
        data_dir=resolve_data_dir(env, base_home),
        database=resolve_database_location(environ=env, home=base_home),
        contract_path=contract_path,
        contract_version=read_contract_version(contract_path),
        app_version=__version__,
    )


def resolve_local_identity(*, user: str | None = None) -> AppIdentity:
    """本机模式身份：``actor_id = actor_name = getpass.getuser()``，6 个角色全给。

    design §2：用户名不匹配 ID 正则 → **启动失败 rc=2**（``LocalIdentityError``），
    不静默替换成一个假 ID —— 那会让审计记录里的操作者与真实 OS 用户脱钩。
    """
    name = user if user is not None else getpass.getuser()
    name = (name or "").strip()
    if not name:
        raise LocalIdentityError("无法确定本机用户名（getpass.getuser() 返回空）")
    if len(name) > 80:
        raise LocalIdentityError(f"本机用户名超过 80 字符上限（活契约 actor_name）：{len(name)}")
    if not is_resource_id(name):
        raise LocalIdentityError(
            f"本机用户名 {name!r} 不匹配活契约 ID 正则，无法作为 actor_id；"
            "拒绝静默改写身份（design §2：启动失败 rc=2）"
        )
    return AppIdentity(actor_id=name, actor_name=name, allowed_roles=LOCAL_ROLES)
