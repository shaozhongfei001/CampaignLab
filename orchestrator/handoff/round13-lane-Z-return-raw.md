# R13 · lane Z（Meitner）原始回执归档

> 归档义务：`resume.checkpoint_R8.lane_raw_report_archive` —— lane 的原始回执必须先落盘归档，
> 再 `close_agent` 释放并发槽。本文件是**原文照录**（含 lane 自报的估算值与 U 项），
> 编排器的独立复验结论见 `orchestrator/state.json -> resume.round13_lane_Z_return.orchestrator_reverification`，
> **不采信本文件的自报值**（`rule_no_trust_handoff_summary_assertions`）。
>
> - lane：Z ｜ nickname：Meitner ｜ agent_id：`01a1d743-12d5-7090-8bdd-0dd75e49e4cc`
> - 档位：qwen3.8-max / reasoning high ｜ 任务：M2-01 · S1（设计冻结件，禁写实现码）
> - 派单轮：R13 ｜ 结果：PASS（L 循环 1/3 轮）｜ 交付：`orchestrator/handoff/M2-01-design.md`（未跟踪，提交权归编排器）
> - ★ 本回执的 U-1 推翻了派单文与编排器 override 的一条事实前提（`listActivities` 有 `status`），
>   编排器独立实测契约后确认 lane 正确、派单文错误，见 A195 与自纠 R13-5。

```text
RESULT: PASS
S1 design frozen. All path-limited gates rc=0. Two orchestrator rulings (★U-1, ★U-2) block S2–S7 dispatch; reported as U-items, not self-decided. No implementation code written; no git add/commit; deliverable is untracked.

§2 DELIVERABLE — orchestrator/handoff/M2-01-design.md (sole output)
- Measured: 1322 lines / 146775 bytes / sha256 6f40846a1d669aaa9c497ef9cb80b9bec3ad6cdda0ca1c30e1c91e980421a306
- Encoding: UTF-8, BOM=False, CR=False, ENDS_NL=True (single, no double).
- git status: `?? M2-01-design.md` (untracked — commit belongs to orchestrator). git diff --numstat HEAD: EMPTY (correct: untracked, no tracked baseline; size is the wc above).
- ruff format --check (path-limited to my file): rc=0 "1 file already formatted"; ruff check: rc=0 "All checks passed!".
- Hard boundaries honored: wrote ONLY this .md; no src/**, tests/**, contracts/**, spec/**, docs/**, orchestrator/state.json touched; no git add/commit.
- Section list (grep -n '^#' = 55 lines total = 1 H1 + 13 H2 + 41 H3; the 13 H2 verbatim):
22:## 1. 接口签名（11 个 operationId；函数名与 operationId 逐字对应，装饰器必须显式给 `operation_id`）
135:## 2. 数据结构（字段级；每行末尾的 `←` 即真值来源切片路径，A171 口径）
244:## 3. 状态机（`TransitionId` 形态对齐 `src/campaignlab/worker/states.py` 的既有体例）
354:## 4. 条款确认门禁（`confirmRule`；对齐 AC-004「必填条款未确认时无法确认」）
464:## 5. 检查项框架（`checkRule`；对齐 AC-004「门槛、预算、叠加、日期和退款口径分别检查」）
611:## 6. ETag 与 409 / 412 / 428 边界
766:## 7. 事务边界与持久化
856:## 8. 逐 op 的可达码矩阵（声明面一律 `declared_responses(<2xx>)` 的 12 个码；本表只标可达面）
877:## 9. 边界清单（AC → 实现约束 → 已知失败模式）
930:## 10. 验证清单（命令 → 期望 rc；供 S5–S7 直接采集，无「人工确认」项）
954:## 11. 文件级 TODO（S2–S7 严格按此机械铺开；不得越出下列文件与符号，越界即回报编排器，手册 §6.4）
1214:## 12. 未决问题（交编排器裁定，实现方不得自行决定，手册 §6.4）
1307:## 13. 本文件自检（命令 → rc）
- HEAD moved mid-run: 9d27b7e(dispatch)→d22b5f6(lane X FU-33)→6c35aad(lane V FU-35+lane Y S2c). Design unaffected: slice still fresh (live openapi sha16=592571099d638251/443309 == slice.source.openapi; openapi.json untouched by those commits). Symbol faces re-inspected at 6c35aad: PROBLEM_CODES=20, DomainError subclasses=14, api/common.__all__=51(unique), pinned by test_domain_errors.py:165-166 — no drift.

§3 SELF-CHECK TABLE (dispatch §3, 4 items; programmatic rc + measured; scripts z21/z22/z16)
① every referenced operations.<opId> exists in slice: rc=0 — n=11, MISSING=[] (listActivities/createActivity/getActivity/updateActivity/listRules/createRule/getRule/updateRule/confirmRule/checkRule/compareRules). Bonus C7 schema paths: n=25, MISSING=[], rc=0.
② every referenced Problem.code ∈ PROBLEM_CODES-20: rc=0 — 14 used, UNREG=[], STATUS_MISMATCH=[], registry_size=20; 6 unused (ACCESS_DENIED/ACTION_REVIEW_REQUIRED/INVALID_SCOPE/JOB_CAPACITY/SNAPSHOT_CONFLICT/STALE_CANDIDATE). C8: zero invented codes.
③ every referenced repo path exists (dangling scan): real oh.dangling_refs=4 — ALL forward S7 evidence landings (evidence/M2/M2-01/, /clauses.md, /gates/, evidence/M2/summaries/M2-01.md). Broad C5: checked=41 / exists=24 / planned(S2–S7 src+tests+evidence)=17 / unexpected-dangling=0, rc=0.
   The 4 are inside the task-card's OWN scope_allow `evidence/M2/M2-01/**` + `evidence/M2/summaries/M2-01.md` (card lines 25/28/48) ⇒ orchestrator must pass allow_dangling at S1 commit (FU-33 precedent); no genuine broken link.
④ no `status` query param designed: FAIL-by-dispatch-literal / PASS-by-contract-measured. Slice AND live listActivities params=[workspace_id(path),cursor,limit,q,status]; listRules=[workspace_id,activity_id(path),cursor,limit,q,status]; live identical. Designing status+q is contract-faithful (dispatch premise stale) → raised as U-1, not self-decided.

§4 POSITIVE CONTROLS (LANE-COMMON §6 守护必须有牙; ran on in-memory copy + /tmp probe — real doc UNTOUCHED, sha256 BEFORE==AFTER==6f40846a…, /tmp probe deleted, zero worktree pollution)
- PC1 (opId assertion teeth): injected `operations.nonExistentOpXyz` → C3 rc=1 MISSING=['nonExistentOpXyz'] TEETH=True.
- PC2 (Problem-code assertion teeth): injected "409 `FAKE_CODE_XYZ`" → C4 rc=1 UNREG=['FAKE_CODE_XYZ'] TEETH=True.
- PC3 (real dangling_refs scanner teeth): synthetic /tmp/pc_z_dang.md w/ fake `docs/decisions/ADR-999-nonexistent.md` + real refs → scanner returned ONLY the fake (EXACT_MATCH=True), real refs spared ⇒ §3③'s 4 hits are genuine detections, not vacuous green. RED raw text captured in tool output above.

§5 U-ITEMS (problem + 2 candidates + inclination; 禁自行裁定 — 手册 §6.4). ★=BLOCKS a later subtask's dispatch.
- ★U-1 (status/q): dispatch/override say listActivities has none; slice+live DO have status+q (N7① confirms other list* keep status; ADR-006 §4.7 is about resource state FIELDS, not list params). A(incline): implement per contract (frozen §1.1/§1.5, multi-value per N7①), correct dispatch text + rewrite self-check ④. B: cursor/limit only → params declared-but-ignored or a removal CR (echoes CR-002, hits 14 more list ops). Incline A: contract is sole authority; contracts/** read-only to me.
- ★U-2 (S2–S4 scope gap): scope_allow 8 paths insufficient; per ARCHITECTURE/A81 need +7 (application/activity_service.py, infra/db/repositories.py, api/common.py, api/deps.py, api/app.py, tests/unit/test_domain_errors.py count-line, tests/domain/__init__.py). A(incline): approve minimal extension (§11.9) under A91(common append-only)/A82(repos append)/A90①(app.py ≤6 lines) + replace hardcoded `==51` assert with inspect-collision (fixes A115 root). B: reject → §11.10 option-B (DTOs in api files, collides M2-02/03/04 scope_deny + app.py gap unfixable + needs new ADR for domain SQL). Incline A.
- U-3 (evidence-row dep; non-block design, blocks evidence): Binding.evidence_id FK→evidence, but evidence write-face (registerEvidence/getEvidence) belongs to M1-03 (same-wave parallel). A(incline): keep existence check, S5/S6 seed artifacts+evidence via SQL, note in clauses.md. B: relax to non-null only (FK still rejects→must translate; weakens AC-004). Incline A.
- U-4 (binding-overlap strictness): DOMAIN.md "同策略同区间仅一条权威绑定". A(incline): same strategy_id overlapping intervals → reject. B: only exact-identical intervals. Incline A (partial overlap makes "which binding is live" undecidable; AC-002 depends on it).
- U-5 (archived activity locks rules?): spec only gives activity OPEN→ARCHIVED + history queryable. A(incline): after ARCHIVED reject createRule/updateRule/confirmRule (409 STATE_CONFLICT) since confirmRule writes activities.current_rule_id. B: reject only updateActivity. Incline A (B self-否证 §3.1 terminal).
- U-6 (multi confirmed successors): ddl.rule_versions lacks cases' one-confirmed-child partial unique index. A(incline): allow multi, current_rule_id=max confirmed_at (tie→max id). B: add domain constraint (beyond DDL/spec, rejects legit re-confirm→CR if needed). Incline A.
- U-7 (dispatch "409 diff field"): Problem has additionalProperties:false, no diff; only RuleDiff has diff. A(incline): split → Problem.issues[] (409 locate, AC-002) + RuleDiff.changes[].path (compareRules, AC-003). B: add diff to Problem (contract CR). Incline A.
- U-8 (q match fields): API.md "名称和公开编号" not named per-resource. A(incline): listActivities→name+external_activity_id; listRules→label+source_rule_version. B: name/label only. Incline A.
- U-9 (card's own line-62 U-1/U-2/U-3 disposition, no new ruling): card U-1 (AC-004 attribution) → split per card (framework here, ±1 numeric to M2-02); BoundaryCase schema has no judgment field so contract-self-consistent — card still asks orchestrator to fix acs registry. card U-2 (scope sync) → state.json scope_synced_from_card already merged 3 items (resolved; my U-2 above is the DIFFERENT 7-path gap). card U-3 (AC-002 view) → per B9 no view interface, web/** untouched.

§6 SELF-REPORTED TOKENS (A183: §15.5 cap by cumulative-billed caliber, max 200k; honest, no smoothing)
- Single-turn context size: artifact alone = 146775 bytes ≈ ~60k output tokens; peak drafting single-turn input ≈ ~120k (est; slice excerpts + spec sections + source files + growing doc).
- Cross-turn cumulative-billed: **over_cap**. The ~60k-token doc output plus the exploration/drafting/verification turns (prior run z1–z20 + continuation z21–z23 + slice/spec/ADR reads + repeated gates) re-bill a growing context every turn ⇒ cumulative well exceeds 200k. No exact internal counter is exposed to me; per A183 I report over_cap truthfully and do NOT smooth or re-scope to "artifact-only within cap".

§7 L-LOOP: 1 round used / cap 3 / STALLED not triggered. No criterion red across 2 consecutive rounds (the single fix — TEMPLATE_MISMATCH reworded to issues[0].code — cleared a C4 false-positive within the same round).

§8 IN_FLIGHT_CONTAMINATION (not my write_set; NOT my RED; 禁修 — LANE-COMMON §4). git status --porcelain at HEAD 6c35aad:
- lane Y (M0-04): ?? src/campaignlab/worker/deps.py · ?? src/campaignlab/worker/integrity.py · ?? tests/integration/jobs/test_worker_deps.py · ?? tests/unit/test_worker_integrity.py · ?? evidence/M0/M0-04/commands-s2b2.md · ?? evidence/M0/M0-04/positive-control-s2b2.log · ?? evidence/M0/M0-04/s2b2-integrity-deps.md
- Full-tree mypy (files=["src","tests","scripts"]) scans lane Y's 4 untracked .py ⇒ reports more than the frozen 80 source files (e.g. 81+). NOT my red; didn't touch. My self-verify was path-limited to my .md only.
- lane V FU-35 + lane X FU-33 were in-flight earlier, now committed (d22b5f6/6c35aad), no longer in status.
```
