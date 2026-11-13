"""S3c：CLI 与 ``doctor`` gate（ADR-005 §2.4 裁定 4；TOOLCHAIN.md:21 的五项检查）。

出口条件就是这里的 ``main(["doctor"]) == 0``：S3c 之前 ``python -m campaignlab`` 必然 rc=1
（``No module named campaignlab.__main__``）。

``binding`` 一项会探测端口占用，属**环境相关**输入，故确定性断言把它排除在外
（其余四项在固定配置下必须逐字稳定）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from campaignlab.__main__ import main
from campaignlab.cli import CHECK_IDS, build_parser, cmd_serve, format_summary, run_doctor_checks
from campaignlab.config import load_config

REPO = Path(__file__).resolve().parents[2]


def test_parser_exposes_doctor_and_serve_only() -> None:
    parser = build_parser()
    args = parser.parse_args(["doctor"])
    assert args.command == "doctor" and callable(args.handler)
    serve_args = parser.parse_args(["serve"])
    assert serve_args.command == "serve" and callable(serve_args.handler)
    # 默认不覆盖 host/port：serve 因此落到 config 的 127.0.0.1:8000
    assert serve_args.host is None and serve_args.port is None
    with pytest.raises(SystemExit):
        parser.parse_args(["backup"])


def test_serve_default_port_is_8000() -> None:
    """硬规则 5：vite 的 /api proxy 硬指 127.0.0.1:8000，改默认值会静默切断联调。"""
    config = load_config(environ={}, home=REPO)
    assert (config.host, config.port) == ("127.0.0.1", 8000)


def test_no_subcommand_is_usage_error_rc2() -> None:
    """「什么都没做」不得判成功，否则 CI gate 变假绿。"""
    assert main([]) == 2


def test_doctor_returns_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAMPAIGNLAB_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAMPAIGNLAB_HOST", "127.0.0.1")
    monkeypatch.setenv("CAMPAIGNLAB_PORT", "8000")
    assert main(["doctor"]) == 0


def test_doctor_fails_on_non_loopback_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """OPERATIONS.md：生产式本地运行只绑定 127.0.0.1 → 非回环是 FAIL 而非 WARN。"""
    monkeypatch.setenv("CAMPAIGNLAB_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAMPAIGNLAB_HOST", "0.0.0.0")
    assert main(["doctor"]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out and "RESULT=BROKEN" in out


def test_doctor_checks_five_items_in_fixed_order(tmp_path: Path) -> None:
    config = load_config(environ={"CAMPAIGNLAB_DATA_DIR": str(tmp_path)}, home=tmp_path)
    results = run_doctor_checks(config)
    assert tuple(item.check for item in results) == CHECK_IDS
    assert CHECK_IDS == ("version", "binding", "data_dir", "database", "worker")


def test_doctor_is_deterministic_apart_from_port_probe(tmp_path: Path) -> None:
    config = load_config(environ={"CAMPAIGNLAB_DATA_DIR": str(tmp_path)}, home=tmp_path)
    first = [r for r in run_doctor_checks(config) if r.check != "binding"]
    second = [r for r in run_doctor_checks(config) if r.check != "binding"]
    assert first == second
    assert format_summary(first) == format_summary(second)


def test_summary_levels_map_to_result_word(tmp_path: Path) -> None:
    config = load_config(environ={"CAMPAIGNLAB_DATA_DIR": str(tmp_path)}, home=tmp_path)
    results = run_doctor_checks(config)
    summary = format_summary(results)
    assert summary.startswith("PASS=") and "WARN=" in summary and "FAIL=" in summary
    # 全新数据目录：库未迁移 + worker 未装配（S3d）→ 有 WARN 但无 FAIL
    assert "FAIL=0" in summary
    assert "RESULT=DEGRADED" in summary or "RESULT=HEALTHY" in summary


def test_cmd_serve_refuses_non_loopback_with_rc2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """serve 拒绝启动＝用法/身份错误（rc=2），与 doctor 的检查失败（rc=1）区分。"""
    monkeypatch.setenv("CAMPAIGNLAB_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAMPAIGNLAB_HOST", "10.0.0.5")
    args = build_parser().parse_args(["serve"])
    assert cmd_serve(args) == 2
