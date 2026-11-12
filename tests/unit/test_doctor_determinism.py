"""D-007 回归：doctor.sh 的字体检查不得再因 SIGPIPE 产生非确定性 WARN。

背景（实测）：`fc-list | grep -qi "noto sans cjk"` 在 `set -uo pipefail` 下，grep 命中即退出，
fc-list（约 18.8KB 输出）继续写管道 -> SIGPIPE(141) -> pipefail 传播 -> 走 else 分支报「未安装」。
30 次复现：rc0=2、rc141=28，即 93% 概率假 WARN；改成 `grep -ci` 后 30/30 稳定命中。

本文件钉住四条不变量（手册 13.3 第 4 条 / 15.4）：
1. 反模式扫描：scripts/ 下不得再出现「管道接 grep -q」（篡改负例的静态等价物）；
2. 定点修复：字体检查必须用 `grep -ci "noto sans cjk"`，不得回退为 `grep -qi`；
3. 确定性：doctor 连跑 3 次的 PASS/WARN/FAIL 摘要必须逐字相同（抖动即失败）；
4. 分母断言：扫描到的脚本数为 0 时判失败，禁止静默通过。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DOCTOR = REPO / "scripts" / "doctor.sh"
SIGPIPE_PRONE = re.compile(r"\|\s*grep\s+-[a-zA-Z]*q")
SUMMARY = re.compile(r"PASS=(\d+)\s+WARN=(\d+)\s+FAIL=(\d+)")


def _scripts() -> list[Path]:
    files = sorted(p for p in (REPO / "scripts").rglob("*.sh") if p.is_file())
    # 分母断言：扫描集合为空说明路径假设已失效，必须显式失败而非静默通过
    if not files:
        pytest.fail("denominator=0：scripts/ 下未找到任何 .sh，扫描口径已失效", pytrace=False)
    return files


def test_no_sigpipe_prone_grep_q_in_scripts() -> None:
    offenders: list[str] = []
    for path in _scripts():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if SIGPIPE_PRONE.search(line):
                offenders.append(f"{path.relative_to(REPO)}:{lineno}")
    assert offenders == [], (
        "检测到「管道接 grep -q」的 SIGPIPE 反模式（set -o pipefail 下会产生假红/假绿）："
        f"{offenders}；改用 grep -c，或先落临时文件再 grep"
    )


def test_doctor_font_check_uses_count_not_quit() -> None:
    text = DOCTOR.read_text(encoding="utf-8")
    assert 'grep -ci "noto sans cjk"' in text, "字体检查必须用 grep -ci（读完全部输入，无 SIGPIPE）"
    assert 'grep -qi "noto sans cjk"' not in text, "不得回退为 grep -qi（D-007 的根因）"


def _run_doctor() -> tuple[int, str]:
    environ = dict(os.environ)
    environ["DOCTOR_SKIP_VERIFY"] = "1"
    environ["PATH"] = f"{Path.home() / '.local/bin'}:{environ.get('PATH', '')}"
    proc = subprocess.run(
        ["bash", str(DOCTOR)], capture_output=True, text=True, cwd=REPO, env=environ, check=False
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_doctor_summary_is_deterministic_across_three_runs() -> None:
    summaries: list[str] = []
    rcs: list[int] = []
    for _ in range(3):
        rc, out = _run_doctor()
        m = SUMMARY.search(out)
        assert m is not None, f"doctor 输出中找不到 PASS/WARN/FAIL 摘要：{out[-800:]}"
        rcs.append(rc)
        summaries.append(m.group(0))
    assert len(set(summaries)) == 1, f"doctor 摘要在 3 次运行间抖动（非确定性门禁）：{summaries}"
    assert set(rcs) == {0}, f"doctor 退出码应为 0，实测 {rcs}"


@pytest.mark.skipif(shutil.which("fc-list") is None, reason="fc-list 不可用，无法判定字体")
def test_noto_detection_is_stable_over_20_samples() -> None:
    """直接复现 D-007 的抖动：修复后 20 次采样必须给出同一个命中条数。"""
    script = (
        "set -uo pipefail; for i in $(seq 1 20); do "
        'n=$(fc-list 2>/dev/null | grep -ci "noto sans cjk"); printf "%s\n" "$n"; done'
    )
    proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=False)
    values = [v for v in proc.stdout.split() if v.isdigit()]
    assert len(values) == 20, f"采样数不足 20（分母断言）：{len(values)}"
    assert len(set(values)) == 1, f"Noto 命中条数在 20 次采样间抖动：{sorted(set(values))}"
