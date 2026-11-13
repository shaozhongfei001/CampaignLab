"""S3c：配置与路径委托（ADR-005 §2.3 / §2.4 裁定 1、2；硬规则 4、5）。

重点是**委托**而不是重实现：``config.py`` 不得自带一套五级解析。这里用「同一组环境变量下
``AppConfig.database`` 与 ``paths.resolve_database_location()`` 逐字相等」把它钉死——
一旦有人在 config 里重写优先级链，本测试立刻红。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from campaignlab.config import (
    API_PREFIX,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_SESSION_TTL_SECONDS,
    LOCAL_ROLES,
    MAX_JSON_BODY_BYTES,
    TOKEN_TTL_SECONDS,
    WORKER_HEARTBEAT_TTL_SECONDS,
    AppIdentity,
    ConfigError,
    LocalIdentityError,
    load_config,
    read_contract_version,
    repo_root,
    resolve_contract_path,
    resolve_local_identity,
)
from campaignlab.infra.db.paths import ResolutionLevel, resolve_database_location

REPO = Path(__file__).resolve().parents[2]
LIVE_OPENAPI = REPO / "contracts" / "openapi.json"


def test_runtime_defaults_match_adr_005() -> None:
    assert DEFAULT_SESSION_TTL_SECONDS == 3600
    assert TOKEN_TTL_SECONDS == 60
    assert MAX_JSON_BODY_BYTES == 1_048_576
    assert WORKER_HEARTBEAT_TTL_SECONDS == 15
    # 令牌 60s 与会话 TTL 3600s 是两个不同对象（OPERATIONS.md vs ADR-005 §2.3），禁混用
    assert (TOKEN_TTL_SECONDS, DEFAULT_SESSION_TTL_SECONDS) == (60, 3600)


def test_serve_defaults_to_loopback_and_port_8000() -> None:
    """硬规则 5：dev_proxy_target 已 ACCEPTED，web/vite.config.ts 的 /api proxy 硬指 8000。"""
    config = load_config(environ={}, home=REPO)
    assert DEFAULT_HOST == "127.0.0.1"
    assert DEFAULT_PORT == 8000
    assert config.host == "127.0.0.1"
    assert config.port == 8000
    assert config.is_loopback()
    assert API_PREFIX == "/api/v1"


def test_contract_version_is_read_from_live_contract_not_hardcoded() -> None:
    """D-004 教训：契约版本必须运行时取自活契约 info.version。"""
    with LIVE_OPENAPI.open(encoding="utf-8") as handle:
        expected = json.load(handle)["info"]["version"]
    config = load_config(environ={}, home=REPO)
    assert config.contract_version == expected
    assert isinstance(config.contract_version, str) and config.contract_version
    assert config.contract_path == resolve_contract_path({}) == REPO / "contracts" / "openapi.json"


def test_contract_version_env_override_is_honoured(tmp_path: Path) -> None:
    fake = tmp_path / "openapi.json"
    fake.write_text(json.dumps({"info": {"version": "9.9.9-test"}}), encoding="utf-8")
    assert read_contract_version(fake) == "9.9.9-test"


def test_database_location_is_delegated_to_paths_module(tmp_path: Path) -> None:
    """硬规则 4：五级解析只有一份实现（paths.py），config 只委托。"""
    environ = {"CAMPAIGNLAB_DATA_DIR": str(tmp_path)}
    config = load_config(environ=environ, home=tmp_path)
    expected = resolve_database_location(environ=environ, home=tmp_path)
    assert config.database == expected
    assert config.database.level is ResolutionLevel.ENV_DATA_DIR
    assert config.database_path == tmp_path / "state" / "campaignlab.db"
    assert config.data_dir == tmp_path


def test_database_url_env_wins_over_data_dir(tmp_path: Path) -> None:
    environ = {
        "CAMPAIGNLAB_DATA_DIR": str(tmp_path / "ignored"),
        "CAMPAIGNLAB_DATABASE_URL": f"sqlite:///{tmp_path / 'explicit.db'}",
    }
    config = load_config(environ=environ, home=tmp_path)
    assert config.database.level is ResolutionLevel.ENV_DATABASE_URL
    assert config.database_path == tmp_path / "explicit.db"
    # 数据目录仍按 CAMPAIGNLAB_DATA_DIR 解析（两者是不同对象，不得互相顶替）
    assert config.data_dir == tmp_path / "ignored"


def test_default_level_is_user_local_share(tmp_path: Path) -> None:
    config = load_config(environ={}, home=tmp_path)
    assert config.database.level is ResolutionLevel.DEFAULT_DATA_DIR
    assert config.data_dir == tmp_path / ".local" / "share" / "campaignlab"
    assert config.database_path == config.data_dir / "state" / "campaignlab.db"


def test_missing_subdirs_reports_operations_md_seven(tmp_path: Path) -> None:
    config = load_config(environ={}, home=tmp_path)
    assert config.missing_subdirs() == (
        "state",
        "raw",
        "snapshots",
        "results",
        "exports",
        "tmp",
        "logs",
    )
    for name in ("state", "logs"):
        (config.data_dir / name).mkdir(parents=True)
    assert config.missing_subdirs() == ("raw", "snapshots", "results", "exports", "tmp")


def test_port_env_override_and_validation() -> None:
    assert load_config(environ={"CAMPAIGNLAB_PORT": "8123"}, home=REPO).port == 8123
    with pytest.raises(ConfigError):
        load_config(environ={"CAMPAIGNLAB_PORT": "0"}, home=REPO)
    with pytest.raises(ConfigError):
        load_config(environ={"CAMPAIGNLAB_PORT": "not-a-port"}, home=REPO)


def test_resolve_local_identity_uses_os_user_and_all_six_roles() -> None:
    identity = resolve_local_identity(user="szf")
    assert identity == AppIdentity(actor_id="szf", actor_name="szf", allowed_roles=LOCAL_ROLES)
    assert len(LOCAL_ROLES) == 6
    assert set(LOCAL_ROLES) == {
        "OPERATOR",
        "DESIGNER",
        "DATA_OWNER",
        "ANALYST",
        "TESTER",
        "REVIEWER",
    }


@pytest.mark.parametrize("bad", ["", "   ", "has space", "ws/1", "a" * 81])
def test_resolve_local_identity_rejects_illegal_user(bad: str) -> None:
    """design §2：不匹配 ID 正则 → 启动失败 rc=2，禁静默改写成假 ID。"""
    with pytest.raises(LocalIdentityError):
        resolve_local_identity(user=bad)


def test_repo_root_points_at_repository_root() -> None:
    assert repo_root() == REPO
    assert (REPO / "contracts" / "openapi.json").is_file()
