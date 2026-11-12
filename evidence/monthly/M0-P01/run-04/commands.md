# M0-P01 run-04 · 第 3 次接管的全表门禁重跑与无人值守授权落地

- 生成时间：2026-11-12T22:50:51+08:00（Asia/Shanghai）
- 执行者：编排器本体（新实例，模型切换后接管），**未采信上一任会话自述**
- 接管时工作提交：`07ab3ca`，分支 `m0-framework`，`git rev-list --left-right --count '@{u}...HEAD'` = `0	0`
- 依据：手册 15.3（恢复自检必须从磁盘重跑并整体覆盖）、15.1（开工闸门）、15.4（分母断言与证据可入库）

## 1. 16 项门禁全表重跑（rc 实跑取得）

| 门禁 | 命令 | expected | 实测 rc | 耗时 | 判定 |
|---|---|---|---|---|---|
| G9_mypy | `uv run --no-sync mypy` | 0 | 0 | 0s | PASS |
| G10_pytest | `uv run --no-sync pytest -q` | 0 | 0 | 1s | PASS |
| G14_doctor | `bash scripts/doctor.sh` | 0 | 0 | 1s | PASS |
| G7_ruff_check | `uv run --no-sync ruff check .` | 0 | 0 | 0s | PASS |
| G8_ruff_format | `uv run --no-sync ruff format --check .` | 0 | 0 | 0s | PASS |
| G1_baseline_v1.0 | `( cd spec/CampaignLab-SDD-v1.0 && sha256sum -c SHA256SUMS --quiet )` | 0 | 0 | 0s | PASS |
| G5_contract_gate | `python3 scripts/check_contracts.py check` | 0 | 0 | 0s | PASS |
| G12_package_verify | `python3 spec/CampaignLab-SDD-v1.0/qa/verify_package.py` | 0 | 0 | 0s | PASS |
| G11_prototype_verify | `bash scripts/verify.sh` | 0 | 0 | 1s | PASS |
| G13_npm_ci_and_build | `npm --prefix web ci && npm --prefix web run build` | 0 | 0 | 9s | PASS |
| G3_frontend_baseline | `python3 scripts/check_frontend_baseline.py` | 0 | 0 | 0s | PASS |
| G2_baseline_v1.0.1_patch | `( cd spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta && sha256sum -c DELTA-SHA256SUMS --quiet )` | 0 | 0 | 1s | PASS |
| G6_contract_meta_validate | `uv run --no-sync python scripts/check_contracts.py check --validate` | 0 | 0 | 2s | PASS |
| G4_slice_unknown_op_negative | `python3 scripts/contract_slice.py --ops noSuchOp --out /tmp/neg_op.json` | 2 | 2 | 0s | PASS |
| G4c_frontend_tamper_negative | `printf '\n' >> spec/frontend-template-spdb-v1.1/css/tokens.css && python3 scripts/check_frontend_baseline.py` | 1 | 1 | 0s | PASS |
| G4b_slice_unknown_ac_negative | `python3 scripts/contract_slice.py --ac AC-MR-99 --out /tmp/neg_ac.json` | 2 | 2 | 0s | PASS |

- 全表结论：**16/16 rc == expected**，无 FAIL。
- `git status --porcelain spec/ | wc -l` = `0`（只读基线未被污染）
- `git status --porcelain | wc -l` = `0`（全树干净）

### 1.1 G4c 篡改负例本轮真实执行（不再转录 run-02）

```
cp spec/frontend-template-spdb-v1.1/css/tokens.css /tmp/tokens.css.bak
printf '\n' >> spec/frontend-template-spdb-v1.1/css/tokens.css
python3 scripts/check_frontend_baseline.py     # -> rc=1（期望非 0，负例成立）
cp /tmp/tokens.css.bak spec/frontend-template-spdb-v1.1/css/tokens.css
git status --porcelain spec/frontend-template-spdb-v1.1/css/tokens.css | wc -l   # -> 0（按字节还原）
```

## 2. 计数分母重测（手册 15.4 第 6 条）

| 分母 | 实测值 | 复现命令 |
|---|---|---|
| pytest_passed | 28 | `uv run --no-sync pytest -q` |
| mypy_source_files | 6 | `uv run --no-sync mypy` |
| ruff_lint_scope_files | 6 | `uv run --no-sync ruff check . --show-files` |
| ruff_formatted_files | 37 | `uv run --no-sync ruff format --check .` |
| contract_registered_nodes | 12 | `python3 scripts/check_contracts.py check` |
| acceptance_denominator / resolvable | 47 / 47 | `scripts/check_contracts.py` AC 解析 |

### 2.1 `ruff_formatted_files` 35 -> 37 的归因（登记为 D-006）

- `ruff format --check .` 报 37，但作用域内 `.py` 只有 6 个（`ruff format --check scripts src tests` -> `6 files already formatted`）。
- 逐目录实测：`contracts 1`、`docs 8`、`evidence 10`、`orchestrator 11`、`scripts 3`、`src 1`、`tests 2` + 根 `README.md 1` = **37**。
- 探针定性（决定性）：
  - `printf 'x = 1\n' > docs/__probe_zz.py` -> 计数 8 变 **9**（`.py` 计入）
  - `printf 'hello\n' > docs/__probe_zz.txt` -> 计数 **不变**（非 Python 文本不计入）
  - 无扩展名文件 -> 计数 **不变**
  - `docs/` 实有 10 个文件 = 8 个 `.md` + `策略复盘规划-1022.pptx` + `智能复盘.docx`，报 8 -> **`.md` 被计入，Office 文件不计入**
- 排除项验证：把 `x = 1` 探针写入 `spec/`、`prototype/`、`.venv/`、`web/` 后计数**均不变** -> `extend-exclude` 与默认排除生效。
- 构成结论：**37 = 6 个作用域内 `.py` + 31 个作用域内 `.md`**（`git ls-files '*.md'` 去掉 `spec/prototype/web` 后为 31）。
- 历史值 35 未记构成、当前树不可复现 -> 记为 **D-006（MINOR）**，修复方式：在 `counts` 下补 `ruff_formatted_files_composition`（含 cmd/构成/复现命令），并在手册 15.4 增加「分母必须写明构成与命令」条款。

## 3. 无人值守 sudo 免密（限定范围）落地与双向验证

- 落地文件：`/etc/sudoers.d/90-campaignlab-ops`，`-r--r----- 1 root root 360`，`visudo -c -f` 语法校验 rc=0，`install -o root -g root -m 0440` rc=0。
- 作用域：`Cmnd_Alias CAMPAIGNLAB_OPS` 仅含 `command -v` 解析出的绝对路径：apt-get / apt / apt-mark / dpkg / fc-cache / fc-list / systemctl / service / docker / docker-compose / snap。
- **全新会话、无 sudo 时间戳缓存**下的实测（正例应为 0，负例应非 0）：

| 命令 | rc | 期望 | 判定 |
|---|---|---|---|
| `sudo -n apt-get --version` | 0 | 0 | 免密可用 |
| `sudo -n dpkg --version` | 0 | 0 | 免密可用 |
| `sudo -n fc-cache --version` | 0 | 0 | 免密可用 |
| `sudo -n true` | 1 | 非 0 | 已限定 |
| `sudo -n bash -c true` | 1 | 非 0 | 无 shell 逃逸 |
| `sudo -n tee /tmp/x` | 1 | 非 0 | 无任意 root 写 |
| `sudo -n cat /etc/sudoers.d/90-campaignlab-ops` | 1（`a password is required`） | 非 0 | 已限定 |

- 反例留痕：在**同一 tty** 内先 `sudo -S` 认证后再跑 `sudo -n bash -c true` 会得到 rc=0，那是时间戳缓存的假象；作用域判定必须在**新会话**里做，本表即为新会话实测。
- 密码纪律：密码只经 PTY stdin 以 `read -rs` 静默传入，用完 `unset PW`；**本文件、脚本、state.json、提交信息中均不含密码**，临时脚本 `/tmp/setup_sudoers.sh` 内也不含密码字面量。

## 4. `fonts-noto-cjk`（BLK-02）当时状态

- `apt.log` 尾部：`Processing triggers for fontconfig (2.15.0-1.1ubuntu2) ...`
- 需下载 `61.2 MB`，实测下行速率约 45 KB/s（8 秒收 361,410 字节，`/proc/net/dev` 采样）。
- `pgrep -a apt-get`：`(none)`
- `dpkg -l fonts-noto-cjk`：`fonts-noto-cjk 1:20230817+repack1-3`；`fc-list :lang=zh | grep -ci noto` = `30`
- 结论：BLK-02 **暂不关闭**。安装完成后须复验 `dpkg -l` 出现 `ii fonts-noto-cjk`、`fc-list :lang=zh | grep -ci noto > 0`，并复跑 `bash scripts/doctor.sh`（预期 WARN 由 2 降为 1，仅剩 BLK-01），再在 `orchestrator/BLOCKERS.md` 置为已关闭并附本轮实测。
- 期间不并发第二个 apt（dpkg 锁），也不改写 `sources.list`。

## 5. 开工闸门（手册 15.1）

- 项目负责人在会话中明确下达：「确认开工」+「本次要做长程无人值守任务执行，所以裁定用默认值」+「开工前装一下 fonts-noto-cjk」+「sudo 密码已给，授权你不用阻塞」。
- 据此把 `resume.owner_gate.status` 由 `AWAIT_OWNER_GO` 改为 `GO`，并记 `granted_at=2026-11-12T22:50:51+08:00`、`granted_by=项目负责人`、`granted_phrase`、`unattended=true`、`sudo_policy`。
- 同时裁定：POST-PATCH-REVIEW-v1.0.1 第 6 节 4 件事全部按建议批准；追认手册 15.6（关键任务 L 循环上限 2 轮）；`pending_owner` 5 项全部按默认值 RESOLVED_BY_DEFAULT。详见 `resume.owner_decisions`。

## 6. 本轮可入库性自检（NOTE-05）

- 见同目录提交后的 `git ls-files evidence/monthly/M0-P01/run-04/` 输出（记录在提交说明与本文件末尾追加段）。
