# Q-VERIFY-M0-01 取证总表（Q lane flash 档，只采事实不判定）

- 取证时间：2026-11-12 22:58–23:10（Asia/Shanghai，逐条命令带 ts 见 raw/）
- 仓库：/home/szf/dev/CampaignLab　分支 m0-framework　HEAD=33bf5c5（与任务卡一致）
- 取证开始时 `git status --porcelain` 为空（工作树干净）；本取证仅向
  `evidence/M0/Q-VERIFY-M0-01/collect/` 写文件，未做任何 git 写操作，未使用 sudo。
- 原始输出：`collect/raw/a1-gates.log`、`a2-contract-gate.log`、`a4-defects.log`、`a5-slice.log`

## 命令总表

| 编号 | 命令原文 | rc | expected | 材料齐备 |
|---|---|---|---|---|
| A1/G1 | uv lock --check | 0 | 0 | 是（01 文件） |
| A1/G2 | uv sync --locked | 0 | 0 | 是 |
| A1/G3 | uv run --no-sync ruff check . | 0 | 0 | 是 |
| A1/G4 | uv run --no-sync ruff format --check . | 0 | 0 | 是 |
| A1/G5 | uv run --no-sync mypy | 0 | 0 | 是 |
| A1/G6 | uv run --no-sync pytest -q | 0 | 0 | 是（28 passed，见漂移） |
| A1/G7 | npm --prefix web run build | 0 | 0 | 是（同时覆盖补充项 G13 的 build 半） |
| A1/G8 | bash scripts/doctor.sh | 0 | 0 | 是（PASS=15 WARN=2，与预期 16/0 不符，见 01） |
| A1/G9 | bash scripts/verify.sh | 0 | 0 | 是 |
| A1/G0a | npm --prefix web ci | 0 | 0 | 是（G13 的 ci 半） |
| A1/G10 | uv run --no-sync python -c "import fastapi,duckdb,pydantic,sqlalchemy,alembic,uvicorn; …" | 0 | 0 | 是（原文无命令串，属重建，声明见 01） |
| A2/C1 | python3 scripts/check_contracts.py check | 0 | 0 | 是（登记项=12 实测差异=12） |
| A2/C2 | uv run --no-sync python scripts/check_contracts.py check --validate | 0 | 0 | 是（元校验=6） |
| A3 | 读 CR-001.md / ADR-004.md / contracts/CHANGES.json（3631B）全文比对 | 0 | — | 是（12 节点三方一致，措辞细节见 03） |
| A4/S1 | python3 scripts/contract_slice.py --all-tables --out /tmp/qverify_all.json | 0 | 0 | 是（28 表+6 索引组=34 键，0 NOT_FOUND，见 04） |
| A4/S2 | python3 scripts/contract_slice.py --tables no_such_table --out … | 2 | 2 | 是 |
| A4/S3 | python3 scripts/contract_slice.py --ops noSuchOp --out … | 2 | 2 | 是（且未写出文件，ls rc=2） |
| A4/S4 | python3 scripts/contract_slice.py --ops getHealth --ac AC-001,AC-MR-01 --out … | 0 | 0 | 是（spec_version=1.0.1） |
| A4/S5 | python3 scripts/contract_slice.py --ops getHealth --ac AC-MR-99 --out … | 2 | 2 | 是 |
| A4/F1 | python3 scripts/check_frontend_baseline.py | 0 | 0 | 是（8/8 PASS） |
| A4/F2R | python3 spec/CampaignLab-SDD-v1.0/qa/verify_package.py | 0 | 0 | 是（PACKAGE PASS 6/6；注：D-002 文中写的 `qa/verify_package.py` 根路径不存在，首次 F2 rc=2） |
| A4/F3R | uv run --no-sync python -m pytest -q -k "live_contract or all_47_acceptance_ids_resolve or frontend_baseline" | 0 | 0 | 是（8 passed / 28 collected） |
| A4/AC | grep -c ''^| AC-'' 基线 ACCEPTANCE.md | 0 | 35 | 是 |
| A4/ACMR | grep -cE ''^\|\s*AC-MR-'' 月报 append 清单 | 0 | 12 | 是 |
| A4/CI | git check-ignore -v ×5 个证据 .log | 1（每条） | 非 0 | 是（均不再被忽略） |
| A4/LS | git ls-files evidence 计数 | 0 | ≥14 | 是（当前 16） |
| A4/6a | git ls-files ''*.py'' | grep -vE … | wc -l | 0 | 6（=composition.in_scope_py） | 是 |
| A4/6b | git ls-files -z ''*.md'' | tr | grep -vE … | wc -l | 0 | 33（=composition.in_scope_md；与任务简报"31"不符，解释见 04） | 是 |
| A5/H1 | python3 hashlib sha256 + json 读 contracts/openapi.json | 0 | — | 是（sha16=01bd28f0772f506e bytes=443552 version=1.0.1） |
| A5/H2 | python3 读两切片比对 + 重切 diff | 0 | 0 | 是（两切片与入库件逐字节一致 diff rc=0） |
| 补充/D | doctor 复跑 2 次（23:03、含 bash -x 探针与 pipefail 机理验证） | 0 | 0 | 是（WARN 根因实证见 01/04） |
| 补充/G4c | 未重跑（遵守"不得篡改 spec/"）；引用 evidence/monthly/M0-P01/run-04/commands.md §1.1 | — | — | 是（引用文本见 04） |

## 会话事故如实记录
1. 会话最初一条 `uv`+git 组合命令返回空输出（进程 rc=0），随即重跑拆分验证，未见影响。
2. 一次 `wsl.exe bash -c` 内嵌双引号脚本被 PowerShell 剥引号导致命令被打散（awk/grep 报错、A2 首次 tee 零输出）；此后全部远程脚本改走规定的 base64 通道。A2 已用 base64 通道重跑成功（C1/C2 为上表结果）。
3. 一次脚本内 `echo WRAP_RC=$LASTEXITCODE` 被 PowerShell 提前展开为空——记录为通道用法失误，不影响被取证命令本身。
4. `dpkg-query -f="${Package}…"` 双引号导致 unbound variable，改单引号重跑成功。
5. 首次 `python3 -m pytest`（F3）用系统解释器报 No module named pytest（rc=1），改用 `uv run --no-sync python -m pytest` 复跑 rc=0（即 F3R，重跑已留痕）。
6. 首次 `qa/verify_package.py`（F2）rc=2（路径不存在），按 state.json G12 的完整路径复跑 rc=0（即 F2R，重跑已留痕）。

（末尾附：git ls-files --others 可入库自检输出，见下）
## 可入库性自检（NOTE-05 硬要求）

命令：git ls-files --others --exclude-standard evidence/M0/Q-VERIFY-M0-01/
时间：2026-11-12T23:17:15+08:00
输出原文：


## 可入库性自检（NOTE-05 硬要求）

命令：git ls-files --others --exclude-standard evidence/M0/Q-VERIFY-M0-01/
时间：2026-11-12T23:17:32+08:00
输出原文（code block）：
```
evidence/M0/Q-VERIFY-M0-01/collect/00-index.md
evidence/M0/Q-VERIFY-M0-01/collect/01-m0-01-gates.md
evidence/M0/Q-VERIFY-M0-01/collect/02-contract-gate.md
evidence/M0/Q-VERIFY-M0-01/collect/03-cr-adr-changes.md
evidence/M0/Q-VERIFY-M0-01/collect/04-defects.md
evidence/M0/Q-VERIFY-M0-01/collect/05-slice-consistency.md
evidence/M0/Q-VERIFY-M0-01/collect/raw/a1-gates.log
evidence/M0/Q-VERIFY-M0-01/collect/raw/a2-contract-gate.log
evidence/M0/Q-VERIFY-M0-01/collect/raw/a3-cr-adr.log
evidence/M0/Q-VERIFY-M0-01/collect/raw/a4-defects.log
evidence/M0/Q-VERIFY-M0-01/collect/raw/a5-slice.log
```
命令 rc=0（0=正常执行）

逐文件核对：
  [在列] 00-index.md
  [在列] 01-m0-01-gates.md
  [在列] 02-contract-gate.md
  [在列] 03-cr-adr-changes.md
  [在列] 04-defects.md
  [在列] 05-slice-consistency.md
  [在列] raw/a1-gates.log
  [在列] raw/a2-contract-gate.log
  [在列] raw/a3-cr-adr.log
  [在列] raw/a4-defects.log
  [在列] raw/a5-slice.log
缺失计数 MISSING=0（应为 0；00-index.md 自身在追加前已存在于磁盘，若标缺说明是自检时序而非忽略问题）
