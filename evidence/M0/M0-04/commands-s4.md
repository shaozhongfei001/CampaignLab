# M0-04/S4 · commands-s4.md（逐条命令 + rc + 读数；append-only，禁删改前轮记录）

说明：时间戳为 UTC 实测（会话期），部分读数以编排器第 0 步 scratch 留档为准逐条转录；
「§5 参考 vs 实测」不符处**不修正参考值**，如实双录（PRE-7：派单文数字是待复核参考值）。

## 第 0 步 · 只读复测（PRE-7 / §6，2026-11-14T18:33:03Z – 18:35:09Z）

| 命令 | rc | 读数 |
| --- | --- | --- |
| git rev-parse --abbrev-ref HEAD | 0 | m0-framework |
| git rev-parse --short HEAD | 0 | 234a3f5 |
| sha256sum R15-lane-M0-04-S4.md[:12] | 0 | fe46f8c90934（派单文指纹相符） |
| git status --porcelain=v1 -uall | 0 | 唯一行：?? orchestrator/handoff/R15-lane-M0-04-S4.md（编排器在飞派单文，非越界件、非邻居件） |
| uv run --no-sync ruff format --check . | 0 | 277 files already formatted（台账权威 276 + 派单文自身 .md 1 件，A223 可解释；编排器补充条确认同口径） |
| uv run --no-sync ruff check . | 0 | All checks passed! |
| uv run --no-sync mypy | 0 | Success: no issues found in 95 source files |
| uv run --no-sync pytest -q | 0 | 615 passed, 6 warnings in 127.91s |

### §5 冻结面复测（AST/运行期探针，uv run --no-sync python，3.14.10）

| 面 | §5 参考 | 实测 | 判定 |
| --- | --- | --- | --- |
| api/common.py | 1153 行/45039 B/31a84b00f02c；__all__ 78（AST==运行期==set，不可解析名 []）；PROBLEM_CODES 20；JobPage 不在；12 个必需名在 | 全部相符 | ✓ |
| DomainError 子类 | 14 | domain/errors.py 定义 14；common.__all__ 再导出 13（ArtifactCommitFailed 不入 __all__） | 相符（口径注） |
| api/app.py | 158 行；create_app:87；include_router 149/153/155；占位:156；openapi_url=None:121 | **157 行**；结构锚点全部逐字相符（149 health、151 注释、153 session、155 workspaces、156 占位注释、121、87） | 行数参考值 -1，结构面 ✓（不判失真） |
| api/deps.py | 172 行；__all__ 10 | **171 行；__all__ 9**（=参考括号内列名的恰 9 项） | 参考值 +1 口径差，内容相符 |
| worker/service.py | 256 行/12924 B/7b0dd1591fd5；方法恰 5；__init__(self,*,store)->None；模块级 def 恰 3（def 面 8） | 全部相符 | ✓ |
| worker/deps.py | 156 行；get_job_service:120 | 156 行；get_job_service 在第 120 行，返回 factory(store=get_job_store(config)) | ✓ |
| api/jobs.py | ABSENT | 不存在 | ✓ |
| tests/integration/jobs/ | 3 件、无 conftest；test_worker_deps 632 行/18 用例 | 相符 | ✓ |
| tests/unit/test_domain_errors.py | 189 行/7771 B/e2f9fba56bf0；12 用例；78 两处 | AST 顶层 10 + 参数化展开 = pytest collect **12**；78 字面量恰 2 处 | ✓ |
| 契约 | sha16 592571099d638251 / 443309 | 相符 | ✓ |
| state.json history 对账 | — | bc2ea43(259/86/571)→fa3a6c8→1d9bcb0(268/88/615)→b523635(276/95/615)；234a3f5 为纯台账提交（四门不变） | 分母链完整，A223 闭合 |

**第 0 步结论**：四门 rc 全 0、差异全部可由「派单文未入库 + 参考值口径」解释 ⇒ 放行写码。

## Round 1 · 实现与自验（时序）

| # | 命令 | rc | 读数/备注 |
| --- | --- | --- | --- |
| 1 | 写 src/campaignlab/api/jobs.py（§2 通道：here-string→scratch→cp） | 0 | 语法自证 ast.parse rc=0（uv python）；此后 ruff format 落定 |
| 2 | common.py 追加 JobPage + __all__、app.py 挂载、test_domain_errors 78→79（锚点断言脚本） | 0 | numstat 见交付表；语法自证 rc=0 |
| 3 | ruff format --diff（4 文件） | 1 | 仅 jobs.py 需格式化（尾换行/折行）⇒ 就地 format jobs.py |
| 4 | ruff check . | 1 | RUF022（__all__ 末置「末尾追加」与全表排序守护互斥）+ E501 ⇒ JobPage 改插 JobCapacity 后的 isort 口径位（既有 78 项一字未动、deleted=0 保持）+ docstring 缩行；U-1 上报 |
| 5 | 格式化后 ruff format --check + ruff check | 0 | All checks passed! |
| 6 | pytest 定向（tests/api + api_app + domain_errors + clock + layering + worker_service） | 0 例 1 失败 | test_404_and_429_branches…（既有前提哨兵钉 jobs.py 缺席）红；**禁改面外、未修**（FU-11 同型先例；U-2） |
| 7 | 写 tests/integration/jobs/test_jobs_router_s4.py（自带 fixture；未建 conftest.py） | 0 | 语法 rc=0；首跑 28 passed/6 failed |
| 8 | 红因定位 | — | ①幂等登记缺 conn.begin() ⇒ 重放不成立（M0-02 体例补正）；②store.retry 对源行 revision +1（冻结语义，断言按实测）；③本仓未知路径统一 Problem 404 ⇒ 挂载探针改形状判据；④fastapi 新版路由表不暴露 operation_id ⇒ 改 HTTP 行为探针 |
| 9 | 修订 jobs.py（conn.begin()×4）+ 测试（4 处口径） | 0 | 31 passed/3 failed |
| 10 | 新鲜/重放逐字节一致问题 | — | M0-02 侧既有 U-2（键序漂移）先例确认；jobs 侧改存 envelope_json 为声明序 json.dumps（fresh 与 replay 同一序列化源）⇒ 34/34 passed |
| 11 | 全表四门（第 1 次） | fmt 0 / check 1 / mypy 1 / — | 测试文件 import 面残留（FastAPI 注解名 + I001/RUF100）⇒ 修 import；见下轮复跑 |
| 12 | 全表四门（第 2 次） | fmt 0 | 279 files already formatted（=276+派单文+jobs.py+测试文件） |
| 13 | 同上 ruff check | 0 | All checks passed! |
| 14 | 同上 mypy | 0 | Success: no issues found in 97 source files |
| 15 | 同上 pytest -q | 1 | **647 passed, 2 failed**；红因：test_404_and_429_branches_are_unreachable_for_the_five_ops（钉 jobs.py 不存在 + 4 路径挂载集）与 test_s3b_routes.py::test_app_py_contains_only_the_a85_mount_lines（钉 include_router 恰 3 处）——两条皆 A84/A85 时代前提哨兵，被 S4 落地**必然**打红、均不在 S4 写权面 ⇒ 未修，U-2 上报（红因逐字见「已知红」节） |

## 阳性对照 · 两轮

| 轮 | 结果 | 备注 |
| --- | --- | --- |
| PC 第 1 跑 | RC 1，PC1–PC5 全过（含 sha 双向核验与复跑绿），PC6 因驱动空参 rc=4 误红中断 | 驱动缺陷（测试脚本侧，非交付面）；变异体在断言前已字节复原，git status 复核无残留 |
| PC 第 2 跑（修正驱动后 8 条全量重跑） | **RC 0 · ALL CONTROLS PASSED** | 逐条：注入→守护 rc≠0→字节复原 sha256 双向相等→复跑 rc=0；原文见 positive-control-s4.log |

## 已知红（全表 pytest rc=1 的构成，逐字）

红 1（tests/api/test_contract_declarations.py::test_404_and_429_branches_are_unreachable_for_the_five_ops）：
`assert not (REPO / "src/campaignlab/api/jobs.py").exists()` ⇒ AssertionError（jobs.py 由 §2.1 授权新建）。
该用例另钉挂载路径集恰 4 条（无 jobs）。docstring 自证依据为「jobs 路由未挂载，A84/A85」——纯前提哨兵。

红 2（tests/unit/test_s3b_routes.py::test_app_py_contains_only_the_a85_mount_lines）：
`AssertionError: assert 4 == 3`，include_router 行实测 `[health, session, workspaces, jobs]` 4 行。
该用例钉 A85 时代恰 3 处挂载；§2.3 强制新增第 4 处 ⇒ 必然红。

两文件均在派单 §2 写权面之外、亦不在 §4② 授权位；处置归编排器（先例：FU-11「禁改名或改写既有哨兵，语义迁移归编排器」/FU-19「补齐后必然转红，属设计好的哨兵」）。

## 收尾复核（硬禁面）

| 面 | 命令/方式 | 读数 |
| --- | --- | --- |
| contracts/openapi.json | sha16/bytes 探针 | 592571099d638251 / 443309（未变） |
| worker/service.py | sha256[:12] | 7b0dd1591fd5（与 §5 逐字同） |
| api/deps.py | sha256[:12] | 896f5663b390（未变，邻居未动、我未动） |
| worker/deps.py | sha256[:12] | ac59435dd93f（未变） |
| application/** domain/** infra/** config cli scripts spec contracts orchestrator | git diff --name-only | 0 项（唯一 repositories.py 的 826/0 为邻居 lane 在飞件，非我写非我读改） |
| tests/integration/jobs/conftest.py | ls | 不存在（未建 ✓） |
| git status 残面 | porcelain | 与第 0 步一致（我的 5 件 + 邻居 + 派单文） |
## Round 1 收尾（末态四门 + 在飞污染记录，2026-11-14T19:22–19:27Z）

| 门 | 读数 | rc |
| --- | --- | --- |
| ruff format --check . | 281 files already formatted（=276+派单文+jobs.py+本棒守护测试+本文件+s4-jobs-router.md；design.md 追加段 already formatted、前 256 行 sha12=5b76bcb33984 前后一致） | 0 |
| ruff check . | All checks passed! | 0 |
| mypy | Success: no issues found in 97 source files（=95+2 本棒新建） | 0 |
| pytest -q | 646 passed, 3 failed | 1 |

红因归属逐条：
1. `test_contract_declarations.py::test_404_and_429_branches_are_unreachable_for_the_five_ops` —— S4 落地必然打红的 A84/A85 前提哨兵（写权面外，U-2）。
2. `test_s3b_routes.py::test_app_py_contains_only_the_a85_mount_lines` —— 同上（assert 4==3，写权面外，U-2）。
3. **在飞污染（PRE-11）**：`test_job_repository_terminal.py::test_repositories_module_all_is_unchanged` —— 邻居 M2-01/S2b-1 在飞期 `infra/db/repositories.py`（+826/0）新入 ActivityBin… 等名字打红的邻居守护；**非我写集、非我改动**（该三测试文件 git diff 面为空），按 PRE-11 记录-绕开-未修。

与本棒相关子集合跑（jobs 守护 34 + domain_errors + clock + worker_service + layering）= **106 passed**。
git status 终面与第 0 步一致（我的 7 件 + 邻居件 + 派单文），阳性对照零残留。
