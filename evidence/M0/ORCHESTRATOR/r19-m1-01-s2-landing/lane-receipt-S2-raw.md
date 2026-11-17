RESULT: PARTIAL
LOOP_USED: 2 / 2
TOKENS_SELF_ESTIMATE: null（无计量句柄；A183 禁猜测值。编排器侧可读数：本棒实际用量已超 45k 档位）

[FACES] 新建 4 件（其余 9 件未交付，见 [GAPS]）
src/campaignlab/domain/ingest/__init__.py | 1 | 73 | 2ad44a31e52d
src/campaignlab/domain/ingest/limits.py   | 39 | 1544 | b98965d4d621
src/campaignlab/domain/ingest/model.py    | 198 | 5563 | 62518861e62a
src/campaignlab/domain/ingest/states.py   | 242 | 9848 | e941d047c5b8
纯追加 4 件：**零改动**（`git diff --numstat` 输出为空 ⇒ added/deleted 均 0；§11.2/§11.3 未交付）

[GATES]
V0 `git rev-parse --short HEAD`+`git status --porcelain` | rc=0 | `9c7fd59` / 分支 `m0-framework` / 上工时 porcelain 为空 | PASS（== A269 取代读数，U-BASELINE 已预裁关闭）
V1 `wc -l -c`+`sha256sum` | rc=0 | 见 [FACES] | PASS
V2 `file -bi src/campaignlab/domain/ingest/limits.py` | rc=0 | `text/plain; charset=utf-8` | PASS
V3 `uv run --no-sync ruff check .` | rc=0 | `All checks passed!`；`ruff format --check .` | rc=0 | `363 files already formatted`（359→363，+4） | PASS
V4 `uv run --no-sync mypy` | rc=0 | `Success: no issues found in 134 source files`（130→134，+4） | PASS
V5 `uv run --no-sync pytest -q` | rc=0 | `852 passed, 6 warnings in 172.71s (0:02:52)` | PASS（**0 红**；A294 授权红**未出现**，因 §11.2 未交付 ⇒ 见 R-A294）
V6 未单独执行 | rc=null | 由 V5 全量覆盖（852 passed 含 `test_if_match_pattern_single_source.py`） | NOT_SEPARATELY_RUN
V7 契约门 | rc=null | **未执行**（预算耗尽）；本棒零改动 `contracts/**`/`spec/**`/`scripts/**` | NOT_RUN（禁谎报 PASS）
V8 `git status --porcelain` / `git diff --numstat` | rc=0 | `?? src/campaignlab/domain/ingest/`（唯一命中）/ numstat 空 | PASS（硬禁面零改动）
V9 `grep -rn --include="*.py" -e campaignlab.api -e sqlalchemy -e conn.begin src/campaignlab/domain/ingest/` | rc=1 | `NO_UPWARD_DEP` | PASS
V10 `python -c "...len(common.__all__),len(deps.__all__),len(r.__all__)..."` | rc=0 | `80 13 16 NO_REEXPORT` | PASS（三值与派单基线逐字相同）
V11 6 条卡片 gate | rc=null | **未执行**；`tests/golden/ingest`、`tests/domain/ingest` 派单时点实测 ABSENT ⇒ 判读 `NOT_APPLICABLE_YET`（4 条）；`tests/integration/jobs -k validate_import` 判读 `NO_TEETH`（FU-67） | NOT_RUN + 判读按 §7.1

[R-A294] 追加后 len(common.__all__) = **80**（未追加，与派单基线同）；len(set(common.__all__)) = null（未单独实测）；
only_runtime = []（空）；only_pinned = []（空，符合期望）；失败用例全名 = **无**（pytest 0 failed）
⇒ A294 授权红**未触发**，编排器入库批**无需**再生 `COMMON_ALL_NAMES`（FU-69 可撤）；该义务随 §11.2 一并退回。

[SYMBOLS] common.__all__=80 · deps.__all__=13 · repositories.__all__=16 · PROBLEM_CODES/DomainError 子类未复测（null）

[DESIGN_CONFORMANCE]
- `states.py`：§11.1 的 10 个符号**全数落地、名字逐字相符**；`ImportTransition` 8 字段名逐字对齐；I1–I7 的 `sources/target/spec_ref/guard/transaction/creates_new_row` 逐字取自 design §3.2 表；I8–I10 未注册（§3.3）。差集见 U-1。
- `model.py`：§11.1 的 16 个符号**全数落地**；字段序逐字按 §4.1 代码块；`Finding` 采 §4.1 **正文实测**序（U-2）。差集见 U-3。
- `limits.py`：§11.1 的 5 个符号全数落地；`8 MiB / 64 MiB / 32` 逐字按 §5.2；`InputTooLarge` 由 `domain.errors` import，零新增异常类。见 U-4。
- `__init__.py`：A276 形态（单行 docstring，73 B，非零字节）。

[GAPS] 未交付 12 项（**退回编排器**，禁由下游 lane 代为发明）：
§11.1 剩 7 件：`locate.py`（`LocationParts` 字段面未在已读片段冻结）、`digests.py`、`normalize.py`、`validate.py`（N1–N18）、`parse.py`（含 `legacy_mapping_to_source_mapping`，需 legacy 内嵌映射的真实形状）、`api.py`、`infra/files.py`；
§11.2 全部（`api/common.py` 11 DTO ＋ 2 Literal 再导出 ＋ `__all__`）；
§11.3 全部（`application/import_service.py`、`application/import_jobs.py`、`repositories.py`/`deps.py`/`app.py` 三件纯追加）。
⇒ 降级交付选项（§8 原文授权）：**本棒只交 §11.1 的结构面 4 件**，其余按上述清单另发一棒（建议 `qwen3.8-max` high / ≥45k，且**只**派 §11.1 剩 7 件，§11.2/§11.3 再拆一棒）。

[BOUNDARY] `git status --porcelain -- tests/` 无输出（tests/** 零改动）；V9 = `NO_UPWARD_DEP`（零 SQL / 零事务 / 零 import campaignlab.api）；`evidence/**`、`orchestrator/**`、`spec/**`、`contracts/**`、`scripts/**` 零改动（porcelain 唯一命中＝新建目录）。

[ENCODING] 四判据实测（Python 探针：BOM=False / CR=False / ENDNL=True / utf-8 可解码，4 件全数）＋ `file -bi` = `text/plain; charset=utf-8`。
口径声明（A183）：BOM/CR/ENDNL 探针跑于**最后一次 `sed` 与 `ruff format` 之前**；其后仅替换 `limits.py:1` 一行文本且 `ruff format` 报 `4 files left unchanged`（规范形不变），`file -bi` 为**修正后**实测。未在修正后重跑 BOM/CR 探针 ⇒ 该两项严格意义上为「沿用同批前值」。

[PRE-40] 8 件逐件重测 sha256[:12] **全数相符**（`b2908617d193`/`3865f3eb6b3c`/`eac1377a4b72`/`e9b575602e56`/`8ccc54fe0ab9`/`2d39feaac2d1`/`eadbd88e4ef7`/`8f44b036f065`）⇒ **DRIFT_COUNT = 0**。
命令原文：`sha256sum <8 路径> | cut -c1-12,65-200` ＋ `wc -l -c <8 路径>`（两件 slice.json 的 `wc -l` 为 2875/4013，即末行无换行 ⇒ 逻辑行数 2876/4014，字节与 sha 逐字相符）。
派单文 face 自算：`wc -l -c` → **615 / 72533**；`sha256sum` → `543e774617b5e06be3e984d3b7a3c576f0b1ebea29c76d5d147217c43f0355ae`（[:12] = `543e774617b5`）⇒ **== §2 的值**。

[U-ITEMS]
U-1（§8 第 1 款：符号清单与实测/正文冲突）：design §3.2 的 `trigger` 列是「operationId ＋ 中文散文」，而 §3 抬头要求 `trigger` 与调用方传入的 operationId **前缀匹配**（体例＝`domain/activity/states.py`）。候选 A＝只存 token（`createImport`/`attachImportFile`/`configureImport`/`validateImport`；I5/I6/I7 共用作业 kind `VALIDATE_IMPORT`，三者只以 `target` 相区分）；候选 B＝逐字存整段散文并改成「包含匹配」。**已按 A 落地**（理由：A 与既有 `assert_activity_transition_allowed` 的前缀/等值匹配体例一致，且 I5/I6/I7 在 `(source,target)` 上已互斥）；同批附随：I6 的 `guard` 在 §3.2 原文是散文「同 I5 形状，`SET state='INVALID'`」，已按该散文**机械展开**为 I5 同形 SQL（非发明）。请编排器追认或改判。
U-2（§8 第 1 款：字段序对不上）：§4.1 代码块写 `Finding : (code, severity, location, message)`，同节正文写「四字段名与顺序**逐字等于** `Issue` 的实测 `model_fields`（code / location / message / severity）」。实测 `list(Issue.model_fields)` = `['code','location','message','severity']` ⇒ **已按实测序落地**。请编排器订正 §4.1 代码块（design 已冻结，lane 禁改）。
U-3（§11.1 符号清单未点名落点）：`MappingLayout`/`SourceMoneyUnit`/`DedupMode` 依 §3.1「五个 Literal 一律定义在 `domain/ingest/`」必须住领域层，但 §11.1 的 `states.py`/`model.py` 两份符号清单都**没有**它们；`MappingSpec` 的字段类型又需要它们。候选 A＝落 `model.py`（**已落地**）；候选 B＝落 `states.py` 并由 `model.py` import。倾向 A（它们是 DTO/映射面取值，不是状态机面）。请裁定后同批把三名字补进 §11.1 的清单，以免 S6 的 AST 守护判「越出符号清单」。
U-4（低危发明面报备）：`assert_within_size_limit` 抛出的 `InputTooLarge(detail)` 文案在 design/切片中**无冻结原文**（§5.2 只冻结 413 与码名）⇒ 现文案 `"{location}：{size_bytes} 字节超过上限 {limit} 字节"` 为本棒所拟。请编排器确认或给冻结文案（S6 若断言 detail 需以此为准）。
U-5（**档位/预算不足，阻塞性**）：本棒权威规范面实测 ＝ design 1393 行 / 167927 B ＋ slice.json 2875 行 / 60641 B ＋ 派单文 615 行 / 72533 B（含 §5.2 的 A277–A292 36 KB 逐字正文），而档位为 45k tokens；实际用量已超档 ⇒ 只能交付 4/13 件。候选 A＝**追加一棒**（同档 45k，只派 §11.1 剩 7 件）＋**再一棒**（§11.2/§11.3 的 6 项）；候选 B＝把本卡档位提到 ≥120k 后重派全量。倾向 A（关键路径 `slack=0`，串行两棒仍比单棒超档可控，且 §11.1 结构面已入库可供下游 import）。
U-6（协议偏差自报，PRE-29）：受 U-5 同一预算约束，**未**逐字通读派单文 615 行全文与 §5.2 的 A277–A292（36 KB）；实际逐字回源面 ＝ 派单文 §6/§7/§7.1/§8/§9/§10（480–615 行）＋ §5.1 的 A293/A294（spawn message 逐字）＋ design §3/§3.1/§3.2/§3.3/§3.4/§4.1/§4.2/§4.3/§4.4/§5.2/§11.1–§11.3/§14.2 ＋ 实测 `api/common.py::Issue.model_fields`、`domain/errors.py`（`StateConflict:227`/`InputTooLarge:245`）、`domain/activity/states.py:1-52`。未读面：派单文 §1–§4（25–276）、§5.2/§5.3、design §1/§2/§4.5–§4.8/§5.1/§5.3/§6/§7.1–§7.3/§7.4/§8–§10/§12/§13/§14.1/§14.3–§14.6、slice.json 全文。**这是本回执的已知缺陷，禁当作「已全读」采信。**

[SELF_CORRECTIONS]
1. 成因：用「按行号整行替换」修 E501 时，把 `limits.py:1`（多行 docstring 的**开引号行**）替换成了自带闭引号的单行 docstring ⇒ 文件语法崩（`ruff check` 69 errors、`mypy` 32 errors in 1 file、`ruff format --check` 分母 363→362）。同轮（loop 2）由 `sed -i '1s|...|'` 去掉多余闭引号修复 ⇒ 复测 `All checks passed!` / `134 source files` / `363 files already formatted`。防再发口径：**整行替换前必须先 `sed -n 'Np'` 打印该行原文并确认其是否为多行结构的边界行**；禁凭记忆构造替换文本。
2. 成因：`states.py`/`model.py` 的 docstring 里写了字面量 `campaignlab.api`，使 V9 的 `grep -rn -e campaignlab.api` 命中**散文**（V9 无法输出 `NO_UPWARD_DEP`）。已把散文改为「api 层 / infra 层 / worker 层」措辞，并给 V9 加 `--include="*.py"` ⇒ 复测输出 `NO_UPWARD_DEP`。防再发口径：领域层 docstring 提及禁用层时**不写点号全路径**，且 V9 命令固定带 `--include="*.py"`（`__pycache__/*.pyc` 会假命中）。
