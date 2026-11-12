"""前端设计基线校验脚本的回归护栏（D-002 修复后补齐，满足手册 13.3 第 4 条）。

背景：三份不可变基线中只有前端模板基线没有机读清单，其 8 项产物哈希写在自带 README
第九节的 Markdown 表格里。scripts/check_frontend_baseline.py 用正则解析该表；一旦表格式
或正则退化，就可能出现「解析到 0 行却 rc=0」——正是 D-001 的静默失效类型。本测试钉死
四件事：行数分母、真基线通过、篡改必红、表格式变化必 rc=2。

约定：必须从仓库根目录运行 pytest；合成基线一律建在 tmp_path，绝不触碰真 spec/。
"""

from __future__ import annotations

import importlib.util
from hashlib import sha256
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_frontend_baseline.py"


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_frontend_baseline", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mod: ModuleType,
    bodies: dict[str, bytes],
    rows: int | None = None,
) -> Path:
    """造一个合成基线目录并把模块指针指过去（monkeypatch 自动还原）。"""
    base = tmp_path / "frontend-template-spdb-v1.1"
    base.mkdir(parents=True, exist_ok=True)
    lines = ["## 九、产物清单与哈希", "", "| 文件 | 大小 | SHA256 前16 |", "|---|---|---|"]
    items = list(bodies.items()) if rows is None else list(bodies.items())[:rows]
    for name, data in items:
        target = base / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        lines.append(f"| `{name}` | {len(data)} B | `{sha256(data).hexdigest()[:16]}` |")
    readme = base / "README_设计与使用说明.md"
    readme.write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setattr(mod, "BASELINE", base)
    monkeypatch.setattr(mod, "README", readme)
    return base


def test_real_baseline_has_eight_rows_and_passes(
    mod: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    assert mod.README.exists(), "真基线 README 必须存在"
    rows = mod.parse_manifest(mod.README.read_text(encoding="utf-8"))
    assert mod.EXPECTED_ROWS == 8
    assert len(rows) == 8, f"第九节应解析到 8 项，实际 {len(rows)} 项（表格式或正则已退化）"
    assert mod.main() == 0
    assert "FRONTEND BASELINE PASS 8/8" in capsys.readouterr().out


def test_self_excluded_names_really_exist(mod: ModuleType) -> None:
    # 基线 README 第 21 行把入口页写作「00_模板入口.html」，磁盘上的实际文件是
    # 「00_模版入口.html」（基线不可变，不改）。SELF_EXCLUDED 必须与实际文件名一致，
    # 否则「排除项」是虚构的，也会误导后人去改错文件名。
    for name in mod.SELF_EXCLUDED:
        assert (mod.BASELINE / name).exists(), name


def test_manifest_entries_are_relative_and_inside_baseline(mod: ModuleType) -> None:
    for name, size, digest in mod.parse_manifest(mod.README.read_text(encoding="utf-8")):
        path = Path(name)
        assert not path.is_absolute(), name
        assert ".." not in path.parts, name
        assert size > 0, name
        assert len(digest) == 16, name


def test_tampered_file_must_fail(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bodies = {f"f{i}.txt": f"body-{i}".encode() for i in range(8)}
    base = _make_baseline(tmp_path, monkeypatch, mod, bodies)
    assert mod.main() == 0
    capsys.readouterr()
    target = base / "f3.txt"
    target.write_bytes(target.read_bytes() + b"\n")
    assert mod.main() == 1, "篡改一个字节也必须 rc=1"
    assert "FRONTEND BASELINE FAIL" in capsys.readouterr().err


def test_row_count_change_must_be_rc2_not_silent_pass(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bodies = {f"f{i}.txt": f"body-{i}".encode() for i in range(8)}
    _make_baseline(tmp_path, monkeypatch, mod, bodies, rows=7)
    assert mod.main() == 2, "行数不等于 8 必须 rc=2，禁止静默通过"
    assert "实际解析到 7 项" in capsys.readouterr().err


def test_missing_readme_is_rc2(
    mod: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mod, "README", tmp_path / "not-exists.md")
    assert mod.main() == 2
