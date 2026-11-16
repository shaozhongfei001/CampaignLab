TIER_CONFIRM | 申报档 = qwen3.8-flash / medium / 7k / loop<=2（派单文 §7）。本环境不暴露模型身份自证面，无法自证；编排器以档位裁定原文为准、不采信自报。
BASELINE
开工 V0 | HEAD=be2b50bc35a59175aaa46d198e9f7c2e28c7a2bc | branch=m0-framework | git status --porcelain=仅我 7 件 ??（A269 裁后基线=be2b50b；派单 §0 的 bd7f89c 被预裁取代，禁再报 U-BASELINE，遵令）
收工 V0 复测 | HEAD=aa3d02be675d0993c4097f0576398c0565c96912 | branch=m0-framework | status=仅我 7 件 ??
HEAD 漂移定性 | git log be2b50b..aa3d02b=单提交 aa3d02b（纯台账批）；git diff --numstat be2b50b..aa3d02b=仅 orchestrator/state.json +268 -70，零 .py/.md
⇒ 与 A269 预裁同类（编排器自身提交；该提交自述 PRE-36/A261 纯台账批不推进权威基线）；全部门在 aa3d02b 上收工逐字复测、全 rc=0（见 GATES）
frozen 8 件收工后复测（==A269 权威值，逐字一致）：
b2908617d193 src/campaignlab/api/common.py
3865f3eb6b3c src/campaignlab/api/activities.py
eac1377a4b72 src/campaignlab/api/rules.py
e9b575602e56 src/campaignlab/api/jobs.py
8ccc54fe0ab9 tests/api/activities/__init__.py（A272 硬禁面：未改未重建）
2d39feaac2d1 orchestrator/handoff/M2-01-design.md
eadbd88e4ef7 orchestrator/handoff/M1-01.slice.json
8f44b036f065 orchestrator/handoff/M2-01.slice.json
派单文自证 | sha256[:12](orchestrator/handoff/R19-lane-M2-01-S6.md)=93a62069914e（全值 93a62069914eede730e568989bc1849284baa74b347e5f5d96e02f24f163a885）✓
FACES | V1 7 件（lines/bytes/sha256[:12]，工作树权威面）
conftest.py 365 14029 ce3c39e555c5
test_etag.py 293 12847 47474347ed57
test_conflicts.py 317 12629 0ce9e9d36074
test_rule_diff.py 143 6334 703e06aeed13
test_bindings_api.py 164 6737 2aaf4d7df5a3
test_list_filters.py 192 9109 d19cd794eaf1
test_contract_declarations_m2.py 81 3969 1b78851294f8
NAMES | AST 实取 43 名逐字对上 §6.1＋A273＋A274（V2 RC=0；test_activities_router_s3.py 之 4 名=既有旧文件，不计分母）
test_etag.py(13): test_update_activity_etag412_rejects_stale_if_match, test_update_rule_etag412_rejects_stale_if_match, test_confirm_rule_etag412_rejects_stale_if_match, test_update_activity_etag412_missing_if_match_is_428_not_422, test_update_rule_etag412_missing_if_match_is_428_not_422, test_confirm_rule_etag412_missing_if_match_is_428_not_422, test_malformed_if_match_is_422, test_etag_is_quoted_decimal_revision, test_confirm_rule_bumps_activity_etag_and_current_rule_id, test_current_rule_id_follows_the_latest_confirmed_successor_a_then_b, test_current_rule_id_tie_break_is_id_lexicographic_max_per_design_3_2, test_replay_returns_the_original_etag_even_with_a_wrong_if_match, test_label_only_update_changes_etag_but_not_digest
test_conflicts.py(10): test_dup_external_activity_id_is_409_with_two_issues, test_dup_external_race_falls_back_to_409_not_500, test_null_bank_id_never_triggers_dup_external, test_idempotency_conflict_is_409, test_empty_patch_is_422, test_archived_activity_rejects_update_409, test_confirmed_rule_rejects_update_409_and_writes_denied_audit, test_confirm_with_stale_digest_is_409_version_mismatch, test_confirm_without_required_clause_is_422_evidence_required, test_unreachable_codes_are_declared_but_unreachable
test_rule_diff.py(4): test_rule_diff_shows_changed_fields_sources_and_digest, test_rule_diff_cross_template_is_422, test_rule_diff_requires_rerun_case_ids_is_empty_when_no_change, test_rule_diff_across_workspaces_is_404
test_bindings_api.py(5): test_binding_full_replacement_semantics, test_binding_absent_from_patch_leaves_rows_untouched, test_binding_overlap_is_422, test_binding_unregistered_evidence_is_422_evidence_required, test_binding_empty_interval_is_422_not_500
test_list_filters.py(8): test_list_filter_by_status_multi_value, test_list_filter_by_q_matches_name_and_external_id, test_list_filter_unknown_status_is_422, test_list_filter_cursor_binds_all_four_params, test_list_filter_bad_cursor_is_400_with_the_frozen_detail, test_list_rules_status_param_filters_the_state_column, test_list_pages_have_no_etag_header, test_cross_workspace_is_404
test_contract_declarations_m2.py(3): test_declared_responses_match_the_slice_for_all_eleven_ops, test_operation_id_matches_function_name_for_all_eleven_ops, test_every_problem_code_used_here_is_in_the_registry
GATES | 命令 → rc → 输出尾部逐字（V0/V1/V2 输出已见 BASELINE/FACES/NAMES；命令=派单 §6.2 原文，uv run --no-sync 前缀略写为 uv）
V3a | uv pytest -q tests/api/activities -k etag412 | RC=0 | 7 passed, 40 deselected, 1 warning in 3.95s（含 S3 旧文件 1 例）
V3b | uv pytest -q tests/api/activities -k dup_external | RC=0 | 3 passed, 44 deselected, 1 warning in 1.65s
V3c | uv pytest -q tests/api/activities -k rule_diff | RC=0 | 4 passed, 43 deselected, 1 warning in 2.52s
V3d | uv pytest -q tests/api/activities -k binding | RC=0 | 5 passed, 42 deselected, 1 warning in 2.82s
V3e | uv pytest -q tests/api/activities -k current_rule | RC=0 | 3 passed, 44 deselected, 1 warning in 2.11s
V3f | uv pytest -q tests/api/activities -k list_filter | RC=0 | 8 passed, 39 deselected, 1 warning in 4.90s（-k 同命中文件名 test_list_filters.py，8=本文件全部 8 例，非外域）
V6a | uv pytest -q tests/api/activities | RC=0 | 47 passed, 1 warning in 25.47s
V6b | uv pytest -q tests/domain/activity | RC=0 | 48 passed in 0.28s
V6c | uv pytest -q tests/domain/activity -k immutable | RC=0 | 3 passed, 45 deselected in 0.18s
V6d | uv pytest -q tests/domain/activity -k clause_gate | RC=0 | 18 passed, 30 deselected in 0.19s
V7a | uv ruff format --check . | RC=0 | 352 files already formatted
V7b | uv ruff check . | RC=0 | All checks passed!
V8 | uv mypy | RC=0 | Success: no issues found in 130 source files
V9a | uv pytest -q --collect-only 2>&1 | tail -3 | RC=0 | 852 tests collected in 0.98s
V9b | uv pytest -q 2>&1 | tail -5 | RC=0 | 852 passed, 6 warnings in 192.50s (0:03:12)
V10a | uv python scripts/check_contracts.py check --validate | RC=0 | CONTRACT CHECK PASS 登记项=13 实测差异=13 元校验=6
V10b | uv python -c openapi sha16/bytes | rc=0 | 592571099d638251 443309；info_version=1.0.1
V11 | git status --porcelain; git diff --numstat | RC=0 | 原文见 HARDEN
V15 | uv mypy（7 件全部落盘后复跑，LANE-COMMON §3.6 同 basename conftest 强制项）| RC=0 | Success: no issues found in 130 source files
预期红对账 | 开工时 -k dup_external / -k rule_diff 于该路径=0 例 rc=5 → 本棒清偿为 RC=0（V3b/V3c）
COUNTS | 实测 vs 期望（期望基座=A269 裁后 345/123/809 · 125py+220md；§4.1 的 343/218 为入库前读数被取代）
ruff_formatted_files 352 vs 期望 352（345+7）✓
in_scope_py 132 vs 132（125+7；132+220=352 与实测总数自洽）✓
in_scope_md 220 vs 220 不变 ✓
mypy_source_files 130 vs 130（123+7）✓
pytest_passed 852 vs 809+43 ✓（净新增 N=43 由 --collect-only 实取，无参数化；禁写死 43 条已遵：43=实测值）
contract_registered_nodes 13 vs 13 ✓ · live_openapi_sha16 592571099d638251 vs 同 ✓ · info_version 1.0.1 vs 同 ✓
PC | 每条：变异→pytest rc=1 断言红（非 rc=4 收集错，PRE-34）→内存原文复原→sha256 双向核验→复跑全目录 47 passed RC=0
PC-A PASS(RED-AS-EXPECTED) sha 变异前 47474347ed57 == 复原后 47474347ed57 RESTORED | test_etag.py:62: AssertionError | 1 failed, 1 warning in 0.46s
PC-B PASS(RED-AS-EXPECTED) 0ce9e9d36074 == 0ce9e9d36074 RESTORED | test_conflicts.py:65: AssertionError | 1 failed, 1 warning in 0.49s
PC-C PASS(RED-AS-EXPECTED) 1b78851294f8 == 1b78851294f8 RESTORED | test_contract_declarations_m2.py:51: AssertionError | 1 failed, 1 warning in 0.03s | 口径见 PC 注②
PC-D PASS(RED-AS-EXPECTED) 703e06aeed13 == 703e06aeed13 RESTORED | 四次独立变异全红：D1 candidate refund_policy 改回同值→test_rule_diff.py:81 AssertionError 1 failed in 0.69s（差异字段组）；D2 evidence_id 期望 ev-1→ev-9 1 failed in 0.67s（条款来源组）；D3 digest_a != digest_b 改 == 1 failed in 0.64s；D4 len(digest_a)==64 改 ==128 1 failed in 0.86s（摘要组两牙）| 口径见 PC 注③
PC-E PASS(RED-AS-EXPECTED) 2aaf4d7df5a3 == 2aaf4d7df5a3 RESTORED | test_bindings_api.py:117: AssertionError | 1 failed, 1 warning in 0.50s
PC 注① | 派单字面要求探针在 tmp_path；实际采用工作树就地变异＋即时内存复原＋sha256 双向核验＋收工 git status/diff 零残留证实；不落痕目标已达成，偏差如实报。
PC 注② | PC-C 未做 tmp_path 切片副本改码，改以变异 _slice_responses 派生集（剔除 201）实现同等证明：断言期望源于切片而非硬编码。
PC 注③ | PC-D 字面「删三件断言之一⇒红」对通过用例必绿（余二照常过），按 PRE-33 意图改为对三件各组独立值变异，三组均有牙实证（A260：未拿运行期 2xx 状态码当 PC 对象）。
HARDEN | git status --porcelain 原文：
?? tests/api/activities/conftest.py
?? tests/api/activities/test_bindings_api.py
?? tests/api/activities/test_conflicts.py
?? tests/api/activities/test_contract_declarations_m2.py
?? tests/api/activities/test_etag.py
?? tests/api/activities/test_list_filters.py
?? tests/api/activities/test_rule_diff.py
git diff --numstat 原文=（空）⇒ deleted 列全 0、零修改既有文件；A272 __init__.py 与全部硬禁面零触碰
U | NONE
RESULT | DONE
loop 实耗 = 2/2 轮（第 1 轮=开发+门+PC 主体；第 2 轮=PC-D 补牙+收工复测+回执）
token 双口径如实报（C10 禁降档）| 单轮最大上下文 ≈ 15 万 tokens 级；lane 累计 ≈ 40 万 tokens 级；对 7k 预算＝大幅超支，over_cap=true
IN_FLIGHT_CONTAMINATION | 会话中段 ?? 曾短暂含 orchestrator/handoff/M1-01-design.md（68557B，M0-04-design.md 字节拷贝，04:09:16 出现）及 M orchestrator/state.json（短暂 staged）；均自行消退、非本棒命令产物，全程未触碰；收工 status 仅 7 件（见 HARDEN）
编码四判据 | 7 件全部通过（严格 utf-8 / 无 BOM·CR·NUL / 无 C0·C1 控制符 / 尾换行）；定稿流程 cp→ast.parse→四判据→ruff check --fix→ruff format→复验，工作树面为权威（即 FACES 之 sha）
