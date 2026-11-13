# M0-04/S7 —— `tests/unit/test_job_dto.py`（lane U / Hertz，qwen3.8-flash）

## 交付形态
- **新建**文件（A86 实测 HEAD 无此路径，非追加式）。299 行 / 12679 字节（程序化实测）。
- 7 个函数逐字落地，禁改名/禁合并：`test_job_dto_matches_live_schema_13_required`、
  `test_job_dto_forbids_lease_fields`、`test_state_enum_is_6_values`、`test_kind_enum_is_10_values`、
  `test_objectref_kind_enum`、`test_retryable_matrix`、`test_problem_code_all_in_registry_20`。
- 未使用 M0-02/S4 的三个在册函数名（`test_job_dto_validates_against_live_schema`、
  `test_accepted_response_headers_and_location`、`test_job_repository_rejects_cross_workspace`）；
  实测 `git diff --numstat HEAD -- tests/unit/test_job_dto.py` 无输出（新建，不进 diff）。
- **未新建任何 `conftest.py`**（R8-4）。

## 判据来源（只读，未整读 openapi.json / spec/**）
- 契约真值 = `orchestrator/handoff/M0-04.slice.json` 的 `operations.<opId>.schemas.*`
  （`listJobs`/`getJob`/`cancelJob`/`retryJob` 四个 operation 内嵌展开，`truncated_schemas == []`，
  切片 35392 字节）。测试对四个副本做**逐字一致**断言，取到的即同一份展开结果。
  实测切片**无顶层 `components` 键**（schema 只挂在 operations 下），故本卡「`components.schemas.*` 定点抽取」
  的口径按 `operations.*.schemas.*` 落地，已作为 U-1 上报。
- DTO 真值 = `campaignlab/api/common.py` 的 `Job`/`ObjectRef`/`Problem`/`Issue`（均 `extra="forbid"`）。
- 枚举/可重试真值 = `campaignlab/worker/states.py` 的 `JOB_STATES`/`JOB_KINDS`/`retryable_for`/
  `NON_RETRYABLE_PROBLEM_CODES`。
- 20 码真值 = `campaignlab/domain/errors.py::PROBLEM_CODES`。

## 逐条判据要点
1. `…_13_required`：契约 `Job.required` 恰 13 项；DTO 字段集 ⊆ 契约 **且** 契约 ⊆ DTO；
   `Job.properties` 键集 == `required`（无漏网可选字段）；`additionalProperties:false` ↔ `extra="forbid"`；
   合法体 round-trip 后键集 == 契约 required；带未知字段的体必 `ValidationError`。
2. `…_forbids_lease_fields`：契约 `Job.properties` 中**任何**含 `lease` 的键都判红（实扫为空）；
   同族 5 个命名（`lease_token`/`lease_until`/`lease_owner`/`lease_expires_at`/`lease_renewed_at`）逐个
   构造带该字段的 dict → 必须 `ValidationError`；并断言这些列确实只活在 DDL（切片 `ddl.jobs` 含
   `lease_token`/`lease_until`）。
3. `…_state_enum_is_6_values`：契约 6 ↔ 代码 6 双向；`Literal[JobState]` 与 `JOB_STATES` 同源；
   DDL `CHECK(state IN …)` 覆盖契约 6 值；非法值 `LEASED` 必须被拒。
4. `…_kind_enum_is_10_values`：契约 10 ↔ 代码 10 双向；`JobKind` Literal 同源；`MIGRATE` 必须被拒。
5. `test_objectref_kind_enum`：契约 `ObjectRef.kind` 20 ↔ `ObjectKind` 20 双向；`required=={kind,id}`
   与 DTO 字段双向；`kind="lease"` 与多带 `lease_until` 均必须 `ValidationError`。
6. `test_retryable_matrix`：**全矩阵** = 6 状态 × 10 kind ×（20 code + `None`）= 1260 组判定
   （参数化 60 个用例，每用例内层遍历 21 个 code 取值，无抽样）。期望值由测试内**冻结字面量**
   `SPEC_NON_RETRYABLE_CODES` 独立推导（不调用被测函数，避免自证），并与
   `states.NON_RETRYABLE_PROBLEM_CODES` 做集合相等（双向）；每个 (state,kind) 还须能被 DTO 接受。
7. `test_problem_code_all_in_registry_20`：注册表**恰 20**（多一个少一个都判红），且与冻结的 20 码
   期望**双向**集合相等 + 顺序一致；`Problem.required`(7)/`Issue.required`(4)/`Issue.severity` enum
   均与 DTO 双向；`Problem.code` 的契约 enum 若存在则与注册表集合相等。
   实测契约 `Problem.code` **不是 enum**（`type: string` + `pattern ^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$`、
   `maxLength 96`），故走弱分支：逐码校验 pattern/长度、`status` 落在契约 `[400,599]`、
   `type` 长度 ≤ 契约 `maxLength 250`、`problem_type(code)` 与注册表逐字一致、逐码 DTO 可构造；
   另加一条「不合契约 pattern 的码必须 `ValidationError`」的反向取证。已作为 U-2 上报。

## 假绿防护说明
所有枚举/必填/注册表比对一律成对写 `A - B == set()` 与 `B - A == set()`（或 `==` 集合相等），
并配一次「非法构造必 `ValidationError`」的反向断言；`truncated_schemas != []` 直接判红，
防止切片被截空时断言退化为恒真。

## 实测结果
`uv run --no-sync pytest -q tests/unit/test_job_dto.py` → **66 passed**（60 矩阵 + 6 其余），rc=0。
全量 `pytest -q` → 482 passed / 0 failed（基线 416 + 本卡 66 = 482，**零回归**）。
四元组记账见 `commands-s7.md`。
