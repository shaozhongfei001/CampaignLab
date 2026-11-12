# M0-P01 · run-03 · 命令与退出码（D-004 / D-005 修复与差分回归）

运行号 run-03 · 时间 2026-11-12T22:06:38+08:00 · 分支 m0-framework · 运行时 HEAD 0b02dd9
环境：Ubuntu 24.04.2 LTS / 项目 venv Python 3.14.10 / uv uv 0.13.7 (x86_64-unknown-linux-gnu) / Node v24.22.3 / SQLite 3.53.1
触发：PRE-1（wave1 派单前置）。所有 rc 由脚本实跑后回填，非人工誊写。

## 1. 修复前的实测现象（本轮早前采集，作为缺陷证据保留）

```
$ grep -n 'SPEC = Path\|spec_version' scripts/contract_slice.py   # 修复前
22:SPEC = Path("spec/CampaignLab-SDD-v1.0")
149:    bundle: Json = {"spec_version": "1.0.0"}        # 版本硬编码

$ python3 scripts/contract_slice.py --ops exchangeSession,...,createWorkspace \
      --ac AC-001,AC-034,AC-035 --out /tmp/M0-02.new.json     # 修复前重切
rc=0    spec_version = 1.0.0     ← 活契约已是 1.0.1，切片仍盖 1.0.0，且不报错

# AC_ROW = r"^\|\s*(AC-\d+)\s*\|" 修复前无法匹配 AC-MR-<n>，也不读月报追加清单：
state.json 中 5 个 P 任务共引用 AC-MR 30 处（去重 12 条），slice_ac 会返回 {} 且 rc=0
```

## 2. 修复后：数据源与版本戳

| 检查 | 命令 | 实测 |
|---|---|---|
| 活契约版本 | `python3 -c "import json;print(json.load(open('contracts/openapi.json'))['info']['version'])"` | 1.0.1 |
| 基线版本 | 同上，路径换 `spec/CampaignLab-SDD-v1.0/contracts/openapi.json` | 1.0.0 |
| 重切入库 | `contract_slice.py ... --out orchestrator/handoff/M0-02.slice.json` | rc=0 |
| 重切入库 | `contract_slice.py ... --out orchestrator/handoff/M0-03.slice.json` | rc=0 |
| 切片版本戳 | 重切后 `spec_version` | 1.0.1 |
| 切片来源指纹 | `source.openapi.sha16` | 01bd28f0772f506e |
| 判别探针（活契约） | `pytest -k get_review_slice_exposes` | 1 passed, 27 deselected in 0.02s |
| 反证（源换回基线） | `pytest -k baseline_source_would_miss` | 1 passed, 27 deselected in 0.03s |

## 3. 差分回归（手册 13.3 第 3 条：改动抽取脚本必须与改动前对同一入参比对输出）

`DIFF_REGRESSION_OK`

判定：wave1 两张切片的**内容 section 字节等价**，差异仅为 `spec_version`（1.0.0 → 1.0.1）
与新增的 `source` 元段 → 属「修复」而非「回归」，无需重做上下文包内容。

## 4. 验收分母（47 = 35 + 12）

| 检查 | 命令 | 实测 |
|---|---|---|
| 基线 AC 行数 | `grep -c '^| AC-' spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md` | 35 |
| 月报 AC 行数 | `grep -cE '^[[:space:]]*\|[[:space:]]*AC-MR-' spec/.../qa/CampaignLab-Review-Acceptance-Checklist.append.md` | 12 |
| 47 条全部可解析 | `pytest -q -k all_47_acceptance_ids_resolve` | rc=0 |
| 月报黄金值原文锚点 | `pytest -q -k monthly_rows_are_verbatim`（AC-MR-05 含 83.33%、AC-MR-08 含 79.31%，证明未转述） | rc=0 |

## 5. 未命中必须 rc=2 且不产出文件（手册 13.3 / 15.4）

| 用例 | 命令 | rc | 期望 |
|---|---|---|---|
| 未知 operationId | `contract_slice.py --ops noSuchOp --out /tmp/neg_op.json` | 2 | **2** |
| 未知 AC | `contract_slice.py --ac AC-MR-99 --out /tmp/neg_ac.json` | 2 | **2** |
| 未命中时不写文件 | 上述两个输出文件是否存在 | 不存在 | 不存在 |
| 正常路径 | `contract_slice.py --ops getHealth --ac AC-001,AC-MR-01 --out /tmp/pos.json` | 0 | 0 |

> rc=2 的两行是**期望值**，不是失败；Q lane 复核时不得据此判红。

## 6. 质量门与全量门禁复跑

| # | 命令 | rc | 期望 | 实测输出末行 |
|---|---|---|---|---|
| G7 | `uv run --no-sync ruff check .` | 0 | 0 | All checks passed! |
| G8 | `uv run --no-sync ruff format --check .` | 0 | 0 | 35 files already formatted |
| G9 | `uv run --no-sync mypy` | 0 | 0 | Success: no issues found in 6 source files |
| G10 | `uv run --no-sync pytest -q` | 0 | 0 | ............................ [100%] 28 passed in 0.39s |
| G1 | 基线 v1.0 `sha256sum -c`（cd 进目录） | 0 | 0 | — |
| G2 | 基线 v1.0.1 `sha256sum -c`（cd 进目录） | 0 | 0 | — |
| G3 | `python3 scripts/check_frontend_baseline.py` | 0 | 0 | FRONTEND BASELINE PASS 8/8（哈希与字节数逐项一致） |
| G5 | `python3 scripts/check_contracts.py check` | 0 | 0 | CONTRACT CHECK PASS 登记项=12 实测差异=12 元校验=skipped |
| G6 | `check_contracts.py check --validate` | 0 | 0 | CONTRACT CHECK PASS 登记项=12 实测差异=12 元校验=6 |
| G11 | `bash scripts/verify.sh` | 0 | 0 | PASS: 字节级复现 |
| G12 | `python3 spec/CampaignLab-SDD-v1.0/qa/verify_package.py` | 0 | 0 | PACKAGE PASS 6/6 |

单测用例数：28（run-02 时为 14）。`tests/unit/test_contract_slice.py` 现有 22 条，
其中 3 条为**反证**用例——把数据源换回基线、或去掉月报清单，断言月报内容随之消失，
以此证明「切片确实来自活契约」而不是碰巧等价。

## 7. spec/ 未被污染

| 检查 | 命令 | 实测 | 期望 |
|---|---|---|---|
| 基线工作树 | `git status --porcelain spec/` | EMPTY | 空 |
| 基线内容 | `git diff --quiet -- spec/` | 0 | 0 |

## 8. 结论

- D-004（切片源钉死基线 + 版本硬编码）与 D-005（AC-MR 静默不可达）均已修复；
  差分回归证明 wave1 上下文包内容未变，仅版本戳与来源标记被修正。
- 两张 wave1 切片已按活契约 1.0.1 重新生成并入库。
- 状态：FIXED_PENDING_Q，待 M0 阶段 Q 交叉验证时与 D-001/D-002/D-003 一并复核。