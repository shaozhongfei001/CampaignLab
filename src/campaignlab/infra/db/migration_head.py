"""alembic 迁移 head 的**唯一**读取实现（M0-02 · FU-8 / 缺陷 D-028 / 裁定 A80）。

收口背景：D-028 实测 ``get_current_head`` 曾有两份逐字相同的实现 —— ``cli._migration_head()``
（S3c）与 ``application/health_service.read_migration_head()``（S3d）。任一侧改了 ini 路径、
换掉判据（例如改读 ``alembic_version`` 表）或加了异常兜底，另一侧就会**静默分叉**，于是
``python -m campaignlab doctor`` 报的迁移状态与 ``/api/v1/health`` 的 ``schema_revision``
给出不同答案 —— 而后者是契约可见面（A71），分叉会直接污染 AC-034/AC-035 的取证。
本片把实现收进本文件，两个读取方双双改为**委托**，唯一性由
``tests/unit/test_migration_head_single_source.py`` 机器守护。

落 ``infra/db/`` 而非 ``application/``：它是迁移基建，``cli`` 与 ``application`` 两侧都要依赖，
放 application 会造成 ``cli -> application`` 的反向依赖（A80 的理由）。

**行为零变化承诺**（纯重构）：判据与收口前逐字相同 —— 同一个 ``<repo>/migrations/alembic.ini``、
同一个 ``Config`` 加 ``set_main_option("script_location", ...)``、同一个脚本目录的当前 head。
ini 不可读、alembic 不可导入、读取抛任何异常 → 一律返回 ``None``，由调用方降级
（doctor 报 WARN、health 落 DEGRADED），**禁猜 revision**。``UNMIGRATED_REVISION`` 哨兵同批
搬来（搬移不是复制），``application/health_service`` 侧 re-export，既有 import 口径不变。
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from campaignlab.config import repo_root

#: 迁移目录（相对仓库根）：本模块 ``read_migration_head()`` 默认值的唯一来源。
#: 收口前 ``cli.py`` 与 ``health_service.py`` 各存一份同值字面量；``health_service`` 的那份
#: 已并入此处，``cli.py`` 的那份因写集所限本轮保留（由它显式传入，等价于默认值），
#: 已作为 U 项上交编排器裁定是否后续并一。
MIGRATIONS_DIR: Final = "migrations"

#: 库尚未迁移时 ``Health.schema_revision`` 的取值。刻意**不等于**任何合法 revision 串，
#: 这样 ``status`` 才会落 DEGRADED 而不是假 READY。
UNMIGRATED_REVISION: Final = "UNMIGRATED"


def read_migration_head(migrations_dir: Path | None = None) -> str | None:
    """alembic 脚本目录的当前 head；取不到返回 ``None``（调用方降级，不猜 revision）。

    ``migrations_dir`` 省略时取 ``repo_root() / MIGRATIONS_DIR``，与收口前两个调用方各自算出的
    ini 路径逐字相同。所有失败模式都收敛成 ``None``：doctor 与 health 只关心「能不能拿到 head
    来比对」，拿不到是可恢复的降级态，不是崩溃条件 —— 故这里刻意不区分「alembic 没装」
    「ini 缺失」「脚本目录坏了」。
    """
    directory = migrations_dir if migrations_dir is not None else repo_root() / MIGRATIONS_DIR
    ini = directory / "alembic.ini"
    if not ini.is_file():
        return None
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
    except ImportError:
        return None
    try:
        cfg = Config(str(ini))
        cfg.set_main_option("script_location", str(ini.parent))
        return ScriptDirectory.from_config(cfg).get_current_head()
    except Exception:
        return None
