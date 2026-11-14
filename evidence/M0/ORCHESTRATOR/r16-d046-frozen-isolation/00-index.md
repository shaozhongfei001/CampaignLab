# R16 · D-046 根治取证索引 —— 冻结索引树的 Python 导入隔离

- **时点**：2026-11-15T03:57:02+08:00　**执行方**：编排器自办（无 lane 参与）
- **归属**：GOVERNANCE / 工装面 · 缺陷单 `orchestrator/defects/D-046.md` §8 · 后续收口 FU-39
- **触发原因**：R16 需要入库 M0-04/S4（lane 已回执），但另一条 lane（M2-01/S2b-1）**仍在飞**且
  已修改被跟踪的 in-scope 文件（`src/campaignlab/infra/db/repositories.py` +826/0、
  `src/campaignlab/api/deps.py` +175/0）。D-046 未根治时，任何入库都会在冻结树上产生
  「冻结测试 ＋ 活动源码」的杂交读数；而 D-046 的规避手段 PRE-12 要求把在飞件泊出工作树 ——
  对**活着的** lane 执行泊出等于摧毁其产出，客观不可用。故根治是本轮唯一的入库前置条件。

## 1. 结论（一句话）

`sys.path` 中 `PYTHONPATH` 的条目先于 site 阶段由 editable `.pth` 追加的路径 ⇒
把冻结树的 `src` 注入 `PYTHONPATH` / `MYPYPATH` 即可在不重建 venv、不复制 `.venv`、
不改 `.pth` 的前提下夺回导入解析权；对真实工作树口径**恒等无副作用**。

## 2. 阳性对照（天然污染样本，非合成；这是本取证的核心）

| 口径 | `import campaignlab.infra.db.repositories` 实际解析到 | 哨兵用例 rc / 读数 |
|---|---|---|
| A 修复前（`sh` 不带 `env`） | `/home/szf/dev/CampaignLab/src/campaignlab/infra/db/repositories.py`（**活动树**） | rc=1 · **1 failed, 23 passed** |
| B 修复后（`env=frozen_env(tree)`） | `/tmp/orch_d046_evtree/src/campaignlab/infra/db/repositories.py`（**冻结树**） | rc=0 · **24 passed** |

红因＝`tests/unit/test_job_repository_terminal.py::test_repositories_module_all_is_unchanged`，
与 D-046 §1 记录的触发实例同型（该守护断言 `repositories.__all__` 冻结面，被活动树的新名打红）。
`.pth` 实测内容＝`/home/szf/dev/CampaignLab/src`（单行绝对路径，纯路径形态、非 meta_path 钩子）。

## 3. 交付面（本批入库件；行/字节/sha256[:12] 均为采集时实测）

| 文件 | 形态 | 行 | 字节 | sha256[:12] |
|---|---|---|---|---|
| `scripts/orch_harness.py` | 修改（新增 `frozen_env` + `sh(env=)` + 6 处调用点） | 676 | 26510 | `0d8ac533afec` |
| `tests/unit/test_orch_harness.py` | 修改（追加 3 条纯单元守护；用例 20 → 23） | 434 | 17361 | `4ccd73e99f2a` |
| `orchestrator/defects/D-046.md` | 修改（文末追加 §8；前 96 行逐字节未动） | 139 | 11858 | `82b46c8dfc59` |
| `evidence/M0/ORCHESTRATOR/r16-d046-frozen-isolation/commands-and-outputs.log` | 新建 | 140 | 4439 | `ca0aa0a75a80` |
| `evidence/M0/ORCHESTRATOR/r16-d046-frozen-isolation/00-index.md` | 新建（本件；自身读数由提交台账登记，避免自指） | — | — | — |
| `orchestrator/state.json` | 台账（counts / defects[D-046] / round16_predispatch / in_flight_agents / baseline_authoritative） | — | — | — |

## 4. 门禁（活动工作树，路径限定；全表归 `run_commit` 在冻结树上复跑）

- `uv run --no-sync ruff format --check scripts/orch_harness.py tests/unit/test_orch_harness.py` → rc=0 · `2 files already formatted`
- `uv run --no-sync ruff check scripts/orch_harness.py tests/unit/test_orch_harness.py` → rc=0 · `All checks passed!`
- `uv run --no-sync mypy`（全表） → rc=0 · `Success: no issues found in 98 source files`
  （98 = 台账权威 95 ＋ 在飞 lane S4 的 2 件 ＋ 在飞 lane S2b-1 的 1 件；**本批零新增 .py**，
  故 mypy 分母不变，仍为 95 —— 98 是活动树读数，不是入库读数，依 A223/PRE-11 归因不入账）
- `uv run --no-sync pytest -q tests/unit/test_orch_harness.py` → rc=0 · `23 passed`（`--collect-only` 亦 23）

## 5. 未覆盖面 / 残留风险（如实上报，禁粉饰）

1. 本修复只夺回 **Python 导入**的解析权。靠 `Path(__file__).parents[n]` 定位仓库根的守护本就取
   冻结树路径（D-046 §1 表格已核实），无需改；`mypy_path = "src"` 相对 cwd 本就指向冻结树，
   `MYPYPATH` 属冗余加固。
2. 若 editable 安装形态由「纯路径 `.pth`」变为「`__editable___*_finder` 元路径钩子」，
   `PYTHONPATH` 将失效（`sys.meta_path` 优先于 `sys.path`）。该形态变更必须同批改本方案 —— 已并入 FU-39。
3. `run_gates` 的 `want_ruff=False` 等裁剪参数不变；`frozen_env` 无条件计算（纯函数，零成本）。
4. 本批**未**改动 `frozen_tree()` 的软链策略（仍软链 `.venv`/`.git`）：重建 venv 的数十秒开销
   在无人值守长程里按每次入库计，代价不可接受；隔离改由调用侧 env 保证，并在 docstring 内
   留下显式警示，防后人只软链不注入。
