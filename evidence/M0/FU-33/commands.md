# FU-33 / D-041 + D-042 -- commands actually run (lane X, qwen3.8-max / reasoning high)

generated: 2026-11-14T07:21:02+08:00
HEAD at measurement time: 51af733   branch: m0-framework   commits: 93
cwd for every command: /home/szf/dev/CampaignLab   (WSL2 ext4; host shell is Windows PowerShell)
PATH prefix used before every uv call:  export PATH="$HOME/.local/bin:$PATH"

WHY EVERYTHING BELOW IS PATH-SCOPED: lane W (FU-29) shares this same working tree. Running the
full table here would show its half-finished work, which is IN_FLIGHT_CONTAMINATION and not this
lane's RED (A161: the verifying side must not write to an in-flight surface). The orchestrator
re-runs the full table on the frozen index tree.

BASELINE NOTE: the dispatch message overrides handoff section 0. Handoff section 0 was a snapshot
as-of cf39d64 (ruff 225 / mypy 79 / pytest 490); the dispatch message advanced it to ce08975
(ruff 229 / mypy 80 / pytest 490). During this lane's run, lane W's commit 51af733 landed, which
advanced the ledger again to ruff 230 / mypy 80 / pytest 490 (py 82 + md 148). Section A records
all three points so the orchestrator can reconcile without guessing.

================================================================
== A. baseline reconciliation ==
================================================================

----------------------------------------------------------------
### A1 HEAD / branch / commit count
    $ git rev-parse --short HEAD && git rev-parse --abbrev-ref HEAD && git rev-list --count HEAD
    rc=0
    key output (last 6 lines):
      51af733
      m0-framework
      93

----------------------------------------------------------------
### A2 working tree status (XY = 2 status cols + 1 space; path starts at char 4 -- handoff counter-intuitive point 3)
    $ git status --porcelain
    rc=0
    key output (last 12 lines):
       M tests/unit/test_task_cards.py
      ?? evidence/M0/FU-33/
      ?? orchestrator/handoff/LANE-COMMON.md
      ?? orchestrator/handoff/R13-lane-Y-M0-04-S2b-2.md
      ?? orchestrator/handoff/R13-lane-Z-M2-01-S1.md
      ?? orchestrator/handoff/round12-lane-W-return-raw.md
      ?? orchestrator/tasks/M3-P02.md
      ?? orchestrator/tasks/M5-03.md
      ?? orchestrator/tasks/M5-P01.md
      ?? tests/unit/test_task_cards_complete.py

----------------------------------------------------------------
### A3 ledger ruff/mypy/pytest + card three-keys, current values
    $ uv run --no-sync python -c "import json,pathlib;c=json.loads(pathlib.Path('orchestrator/state.json').read_text(encoding='utf-8'))['resume']['self_check_gates_rc0']['counts'];[print(' ',k,'=',c.get(k)) for k in ('ruff_formatted_files','mypy_source_files','pytest_passed','task_cards_on_disk','known_missing_cards','task_total_denominator')]"
    rc=0
    key output (last 14 lines):
        ruff_formatted_files = 230
        mypy_source_files = 80
        pytest_passed = 490
        task_cards_on_disk = 20
        known_missing_cards = 9
        task_total_denominator = 29

----------------------------------------------------------------
### A4 HEAD tree in-scope py/md recount (independent of the ledger)
    $ git ls-tree -r --name-only HEAD | grep -vE '^(spec|prototype|web)/' | grep -cE '[.]py$' && git ls-tree -r --name-only HEAD | grep -vE '^(spec|prototype|web)/' | grep -cE '[.]md$'
    rc=0
    key output (last 8 lines):
      82
      148

================================================================
== B. card body metrics (caliber reused VERBATIM from the read-only narrative guard) ==
================================================================

No self-invented caliber: _split / _header_of / REQUIRED_TABLE_HEADER / the three caps and both
LEGACY_* sets are imported from tests/unit/test_task_card_narrative.py, which this lane did not
modify. Full raw output is in card-metrics.txt.

----------------------------------------------------------------
### B1 the read-only narrative guard over all 29 cards
    $ uv run --no-sync pytest -q tests/unit/test_task_card_narrative.py
    rc=0
    key output (last 8 lines):
      .......                                                                  [100%]
      7 passed in 0.03s

----------------------------------------------------------------
### B2 head/tail/total/header for the 3 new cards
    $ uv run --no-sync python -c "import importlib.util,pathlib;s=importlib.util.spec_from_file_location('n','tests/unit/test_task_card_narrative.py');n=importlib.util.module_from_spec(s);s.loader.exec_module(n);[print(c,n._split(pathlib.Path('orchestrator/tasks/'+c+'.md').read_text(encoding='utf-8')),n._header_of(pathlib.Path('orchestrator/tasks/'+c+'.md').read_text(encoding='utf-8'))==n.REQUIRED_TABLE_HEADER) for c in ('M3-P02','M5-P01','M5-03')]"
    rc=0
    key output (last 8 lines):
      M3-P02 (43, 19, 75, True) True
      M5-P01 (40, 20, 70, True) True
      M5-03 (37, 18, 61, True) True

================================================================
== C. ruff (ruff format's in-scope INCLUDES .md -- handoff counter-intuitive point 1) ==
================================================================

----------------------------------------------------------------
### C1 ruff format --check over this lane's whole write set
    $ uv run --no-sync ruff format --check orchestrator/tasks/M3-P02.md orchestrator/tasks/M5-P01.md orchestrator/tasks/M5-03.md tests/unit/test_task_cards_complete.py tests/unit/test_task_cards.py evidence/M0/FU-33/commands.md
    rc=0
    key output (last 10 lines):
      6 files already formatted

----------------------------------------------------------------
IMPORTANT correction recorded while running C1: pointing `ruff format` explicitly at a .txt or a
.log file makes ruff parse it as Python and emit bogus `invalid-syntax` errors (rc=2). Those two
extensions are NOT part of ruff's directory-traversal scope -- only .py and .md are -- so the
full-table gate `ruff format --check .` never looks at them. Verified in section C3 below. The
first version of this command listed the .txt/.log evidence files and was therefore wrong; it is
corrected above and the bogus output removed. No repo file was affected by it.
### C2 ruff check (lint) over this lane's .py files
    $ uv run --no-sync ruff check tests/unit/test_task_cards_complete.py tests/unit/test_task_cards.py
    rc=0
    key output (last 8 lines):
      All checks passed!

----------------------------------------------------------------
### C3 full-table ruff format --check, and what the denominator is actually made of
    $ uv run --no-sync ruff format --check .
    rc=0
    key output:
      239 files already formatted

    Composition, measured by asking ruff for its own traversed file list
    (`ruff format --check . --verbose`, counting `format_path; path=` lines by extension):
      .py = 83    .md = 156    other extensions = 0    total = 239

    Reconciliation against the ledger at HEAD (counts: py 82 + md 148 = 230):
      py  82 + 1  = 83   <- this lane's tests/unit/test_task_cards_complete.py (the only new .py)
      md 148 + 3  = 151  <- this lane's 3 task cards
         151 + 1  = 152  <- this lane's evidence/M0/FU-33/commands.md
         152 + 4  = 156  <- NOT this lane: 4 untracked .md the orchestrator dropped into
                            orchestrator/handoff/ while this lane was running
                            (LANE-COMMON.md, R13-lane-Y-M0-04-S2b-2.md, R13-lane-Z-M2-01-S1.md,
                             round12-lane-W-return-raw.md). That directory is in this lane's
                            hard_deny, so they were left untouched and are reported here as
                            IN_FLIGHT_CONTAMINATION of the denominator.

    => this lane's own contribution to the ruff denominator is +5 (4 .md + 1 .py): 230 -> 235.
       The observed 239 additionally carries the orchestrator's 4 pending handoff .md files.
       Per the dispatch message this lane must NOT compute or write the authoritative number;
       the orchestrator re-measures on the frozen index tree and refreshes counts in the same
       commit. The breakdown above is given only so that re-measurement can be cross-checked.

    Also verified here: .gitignore contains `!evidence/**/*.log`, so the two .log evidence files
    are tracked (they appear in `git status --porcelain -uall`) while staying outside ruff's
    .py/.md scope and outside dangling_refs' scanned suffixes (.md .json .py .txt .jsonl).
================================================================
== D. mypy (dispatch baseline 80 -> expect 81, this lane adds exactly 1 .py) ==
================================================================

----------------------------------------------------------------
### D1 mypy, full table
    $ uv run --no-sync mypy
    rc=0
    key output (last 6 lines):
      Success: no issues found in 81 source files

================================================================
== E. pytest, path-scoped per handoff section 4 ==
================================================================

----------------------------------------------------------------
### E1 the 6 guard files named in handoff section 4
    $ uv run --no-sync pytest -q tests/unit/test_task_cards.py tests/unit/test_task_cards_complete.py tests/unit/test_task_card_narrative.py tests/unit/test_state_ledger.py tests/unit/test_wave_deps_consistency.py tests/unit/test_counts_freshness.py
    rc=1
    key output (last 34 lines):
      ........F...................................                             [100%]
      =================================== FAILURES ===================================
      ________________ test_ledger_card_counts_match_disk_measurement ________________
      
          def test_ledger_card_counts_match_disk_measurement() -> None:
              """D-042：台账卡片三键必须与磁盘实测逐键相符，禁只核恒等式。"""
              cards = card_ids_on_disk(CARD_DIR)
              missing, _ = reconcile(CARD_DIR, _registered_task_ids())
              bad = ledger_violations(_ledger_counts(), len(cards), len(missing))
      >       assert not bad, (
                  "台账 counts 的卡片三键已腐化（D-042 形态）：卡片变更必须与 counts 刷新在**同一次"
                  "提交**内完成（A101 rule_counts_same_commit；R12-2：按语义类别而非文件后缀判断该刷"
                  f"哪些键）。违规项：{bad}"
              )
      E       AssertionError: 台账 counts 的卡片三键已腐化（D-042 形态）：卡片变更必须与 counts 刷新在**同一次提交**内完成（A101 rule_counts_same_commit；R12-2：按语义类别而非文件后缀判断该刷哪些键）。违规项：['task_cards_on_disk=20 与磁盘实测卡数 29 不符（D-042：卡片变更未与本键同批刷新）', 'known_missing_cards=9 与实测缺口数 0 不符']
      E       assert not ['task_cards_on_disk=20 与磁盘实测卡数 29 不符（D-042：卡片变更未与本键同批刷新）', 'known_missing_cards=9 与实测缺口数 0 不符']
      
      tests/unit/test_task_cards_complete.py:176: AssertionError
      =========================== short test summary info ============================
      FAILED tests/unit/test_task_cards_complete.py::test_ledger_card_counts_match_disk_measurement
      1 failed, 43 passed in 0.29s

----------------------------------------------------------------
### E2 the new guard alone, verbose (13 tests)
    $ uv run --no-sync pytest -v tests/unit/test_task_cards_complete.py
    rc=1
    key output (last 24 lines):
      tests/unit/test_task_cards_complete.py::test_positive_control_broken_identity_is_reported PASSED [ 84%]
      tests/unit/test_task_cards_complete.py::test_positive_control_consistent_ledger_passes PASSED [ 92%]
      tests/unit/test_task_cards_complete.py::test_positive_control_missing_ledger_key_is_reported PASSED [100%]
      
      =================================== FAILURES ===================================
      ________________ test_ledger_card_counts_match_disk_measurement ________________
      
          def test_ledger_card_counts_match_disk_measurement() -> None:
              """D-042：台账卡片三键必须与磁盘实测逐键相符，禁只核恒等式。"""
              cards = card_ids_on_disk(CARD_DIR)
              missing, _ = reconcile(CARD_DIR, _registered_task_ids())
              bad = ledger_violations(_ledger_counts(), len(cards), len(missing))
      >       assert not bad, (
                  "台账 counts 的卡片三键已腐化（D-042 形态）：卡片变更必须与 counts 刷新在**同一次"
                  "提交**内完成（A101 rule_counts_same_commit；R12-2：按语义类别而非文件后缀判断该刷"
                  f"哪些键）。违规项：{bad}"
              )
      E       AssertionError: 台账 counts 的卡片三键已腐化（D-042 形态）：卡片变更必须与 counts 刷新在**同一次提交**内完成（A101 rule_counts_same_commit；R12-2：按语义类别而非文件后缀判断该刷哪些键）。违规项：['task_cards_on_disk=20 与磁盘实测卡数 29 不符（D-042：卡片变更未与本键同批刷新）', 'known_missing_cards=9 与实测缺口数 0 不符']
      E       assert not ['task_cards_on_disk=20 与磁盘实测卡数 29 不符（D-042：卡片变更未与本键同批刷新）', 'known_missing_cards=9 与实测缺口数 0 不符']
      
      tests/unit/test_task_cards_complete.py:176: AssertionError
      =========================== short test summary info ============================
      FAILED tests/unit/test_task_cards_complete.py::test_ledger_card_counts_match_disk_measurement
      ========================= 1 failed, 12 passed in 0.09s =========================

================================================================
== F. dangling-reference self-scan ==
================================================================

Raw output, including the scale reference against the 26 pre-existing cards and the full
interpretation, is in dangling-refs.log (that extension is deliberately outside the scanner's
scanned-suffix list, so quoting the findings there does not mint new dangling refs).
Summary: this lane's 3 new cards introduce exactly 3 dangling refs, one per card, each a faithful
verbatim transcription of that card's own state.json scope literal -- i.e. a forward-looking
output landing point that cannot exist before the task runs. The 26 cards committed before this
lane already carry 156 refs of exactly that kind, so run_commit must already tolerate them via
allow_dangling. This lane adds NO other kind of dangling ref.

----------------------------------------------------------------
### F1 dangling_refs() over every file this lane touched
    $ uv run --no-sync python /tmp/fu33_scan.py
    rc=0
    key output (last 16 lines):
      Each of this lane's danglers is a faithful, verbatim transcription of that card's own
      state.json -> tasks[<id>].scope literal, i.e. a FORWARD-LOOKING output landing point that
      by definition cannot exist before the task runs. The 26 pre-existing committed cards carry
      156 danglers of exactly this kind (future evidence dirs, future design files, defect globs),
      so scripts/orch_harness.py::run_commit must already be tolerating them via allow_dangling.
      This lane deliberately did NOT add any other kind of dangler:
        - every AUTHORITY path cited (spec/**, contracts/openapi.json, contracts/sqlite-v1.sql,
          docs/delivery/LONG-HORIZON-ORCHESTRATION.md, orchestrator/state.json, orchestrator/defects/
          D-041.md + D-042.md + D-013.md + D-036.md + D-022.md, orchestrator/handoff/,
          orchestrator/change-requests/, orchestrator/BLOCKERS.md, scripts/) was individually
          verified to exist on disk -- see section G below;
        - no card names a concrete slice file, because A179 deferred slicing to FU-34 (section G3/G4);
        - the A178-forbidden monthly-AC filename is not reproduced in any card (section G1);
        - glob forms are written so the scanner resolves them to an existing directory, e.g.
          'orchestrator/defects/' followed by a separate 'DMR-<n>.md' token, which avoids minting
          a dangler for a filename pattern that is not a real path.

================================================================
== G. A178 / A179 compliance checks ==
================================================================

----------------------------------------------------------------
### G1 A178: the forbidden monthly-AC filename must appear in NONE of the 3 cards
    $ grep -c 'ACCEPTANCE-MONTHLY' orchestrator/tasks/M3-P02.md orchestrator/tasks/M5-P01.md orchestrator/tasks/M5-03.md || echo 'grep rc=1 -> zero matches in all three cards, which is what A178 requires'
    rc=0
    key output (last 8 lines):
      orchestrator/tasks/M3-P02.md:0
      orchestrator/tasks/M5-P01.md:0
      orchestrator/tasks/M5-03.md:0
      grep rc=1 -> zero matches in all three cards, which is what A178 requires

----------------------------------------------------------------
### G2 A178: the authoritative monthly-AC path must be cited by all 3 cards
    $ grep -c 'CampaignLab-Review-Acceptance-Checklist.append.md' orchestrator/tasks/M3-P02.md orchestrator/tasks/M5-P01.md orchestrator/tasks/M5-03.md
    rc=0
    key output (last 8 lines):
      orchestrator/tasks/M3-P02.md:2
      orchestrator/tasks/M5-P01.md:2
      orchestrator/tasks/M5-03.md:2

----------------------------------------------------------------
### G3 A178: the other four authoritative paths must exist on disk
    $ for f in spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/ui/MONTHLY-PAGES.md spec/CampaignLab-SDD-v1.0/ui/UI-17-strategy-review.md spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/architecture/MONTHLY-REVIEW.md; do test -f "$f" && echo "OK   $f" || echo "MISS $f"; done
    rc=0
    key output (last 10 lines):
      OK   spec/CampaignLab-SDD-v1.0/qa/ACCEPTANCE.md
      OK   spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/ui/MONTHLY-PAGES.md
      OK   spec/CampaignLab-SDD-v1.0/ui/UI-17-strategy-review.md
      OK   spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/architecture/MONTHLY-REVIEW.md

----------------------------------------------------------------
### G4 A179: all 3 cards must state the slice is still pending FU-34
    $ grep -c 'FU-34' orchestrator/tasks/M3-P02.md orchestrator/tasks/M5-P01.md orchestrator/tasks/M5-03.md
    rc=0
    key output (last 8 lines):
      orchestrator/tasks/M3-P02.md:2
      orchestrator/tasks/M5-P01.md:3
      orchestrator/tasks/M5-03.md:1

----------------------------------------------------------------
### G5 A179: no card may name a concrete slice file that does not exist
    $ ls orchestrator/handoff/ | grep -E 'M3-P02|M5-P01|M5-03' || echo 'no slice and no design file for any of the 3 tasks -> confirms FU-34 has not run, as A179 states'
    rc=0
    key output (last 8 lines):
      no slice and no design file for any of the 3 tasks -> confirms FU-34 has not run, as A179 states

----------------------------------------------------------------
### G6 A179: no card may contain a concrete slice filename for itself
    $ grep -cE 'handoff/(M3-P02|M5-P01|M5-03)[.]slice[.]json' orchestrator/tasks/M3-P02.md orchestrator/tasks/M5-P01.md orchestrator/tasks/M5-03.md || echo 'grep rc=1 -> zero matches; cards say handoff/<task-id>.slice.json generically, which resolves to an existing directory'
    rc=0
    key output (last 8 lines):
      orchestrator/tasks/M3-P02.md:0
      orchestrator/tasks/M5-P01.md:0
      orchestrator/tasks/M5-03.md:0
      grep rc=1 -> zero matches; cards say handoff/<task-id>.slice.json generically, which resolves to an existing directory

================================================================
== H. M5-03 human_only_action + no exemption was used ==
================================================================

----------------------------------------------------------------
### H1 M5-03 must carry the literal human_only_action marker
    $ grep -n 'human_only_action' orchestrator/tasks/M5-03.md | head -12
    rc=0
    key output (last 8 lines):
      6:## human_only_action（本卡最强约束 · D-041 §6②）
      8:- **禁把交付确认动作派给任何子智能体自证通过**：本卡每一个子任务都属 `human_only_action`，编排器**不得** spawn 任何 max／flash 子智能体来「代签」「代确认」「代验收」，也不得把本卡任一子任务并入其他 lane 顺带完成。
      30:  model: **禁 spawn**。本卡 `tier_planned = human`，全部子任务档位为 `human`，编排器不得为本卡 spawn 任何子智能体；`human_only_action` 逐子任务适用，无例外。
      40:| S1 三条端到端路径逐条签收（赠券／回拨／全行月报；逐条核对 M5-P01 的回执指针与锁、固定合成数据摘要齐备后才签名）〔human_only_action：禁派子智能体〕 | `human` | 0k | `docs/delivery/HANDOVER.md` 的「交付签收」段 |
      41:| S2 47 条 AC 最终结论确认（只读 M5-02／M5-P01 的矩阵，逐条确认结论与证据指针，禁自行复跑、禁改写结论）〔human_only_action：禁派子智能体〕 | `human` | 0k | 同文件「验收结论」段 |
      42:| S3 待补事项与责任明确（逐条落「事项 + 责任人 + 期限」三元组：未终裁 U 项、OPEN 缺陷单、已知限制）〔human_only_action：禁派子智能体〕 | `human` | 0k | 同文件「待补事项」段 |
      43:| S4 已知限制与运维交接（备份／恢复、锁与并发边界、合成数据适用范围、跨工作区与重启演练结论）〔human_only_action：禁派子智能体〕 | `human` | 0k | 同文件「已知限制与运维交接」段 |
      47:`human_only_action` 适用范围 = S1..S4 全部四行，无例外；任何一行被 spawn 给子智能体即属违反 D-041 §6②，编排器必须记缺陷。

----------------------------------------------------------------
### H2 M5-03 must carry the explicit no-self-attestation prohibition
    $ grep -n '禁把交付确认动作派给任何子智能体自证通过' orchestrator/tasks/M5-03.md
    rc=0
    key output (last 6 lines):
      8:- **禁把交付确认动作派给任何子智能体自证通过**：本卡每一个子任务都属 `human_only_action`，编排器**不得** spawn 任何 max／flash 子智能体来「代签」「代确认」「代验收」，也不得把本卡任一子任务并入其他 lane 顺带完成。

----------------------------------------------------------------
### H3 neither guard's exemption set may mention M5-03 (handoff section 1.2)
    $ grep -n 'M5-03' tests/unit/test_task_cards.py tests/unit/test_task_card_narrative.py || echo 'M5-03 appears in NEITHER guard file -> LEGACY_CARDS and LEGACY_NO_TABLE were not used to hide the gap'
    rc=0
    key output (last 8 lines):
      tests/unit/test_task_cards.py:28:# R12 / FU-33（D-041）：M3-P02、M5-P01、M5-03 三张卡已补齐，本集合按单调收敛纪律清空。

----------------------------------------------------------------
### H4 both LEGACY exemption sets must still be exactly the two historical cards
    $ grep -n 'LEGACY_CARDS\|LEGACY_NO_TABLE\|LEGACY_TAIL_ANNOTATED' tests/unit/test_task_cards.py tests/unit/test_task_card_narrative.py
    rc=0
    key output (last 8 lines):
      tests/unit/test_task_card_narrative.py:99:        if card in LEGACY_TAIL_ANNOTATED:
      tests/unit/test_task_card_narrative.py:121:        if card in LEGACY_NO_TABLE:
      tests/unit/test_task_card_narrative.py:138:    unregistered = no_table - LEGACY_NO_TABLE
      tests/unit/test_task_card_narrative.py:142:    recovered = LEGACY_NO_TABLE - no_table
      tests/unit/test_task_card_narrative.py:144:        f"这些历史卡已补上档位表，必须从 LEGACY_NO_TABLE 移除以保持单调收敛：{sorted(recovered)}"
      tests/unit/test_task_card_narrative.py:149:    """注记不得变成豁免：LEGACY_TAIL_ANNOTATED 仍须过 head / total / 表头三项。"""
      tests/unit/test_task_card_narrative.py:151:    for card in sorted(LEGACY_TAIL_ANNOTATED):
      tests/unit/test_task_card_narrative.py:167:    assert not violations, f"LEGACY_TAIL_ANNOTATED 被当成全面豁免使用：{violations}"

================================================================
== I. write-set discipline: nothing outside the write set was touched ==
================================================================

----------------------------------------------------------------
### I1 git diff --stat limited to this lane's write set
    $ git diff --stat -- orchestrator/tasks/M3-P02.md orchestrator/tasks/M5-P01.md orchestrator/tasks/M5-03.md tests/unit/test_task_cards_complete.py tests/unit/test_task_cards.py evidence/M0/FU-33/
    rc=0
    key output (last 10 lines):
       tests/unit/test_task_cards.py | 10 +++-------
       1 file changed, 3 insertions(+), 7 deletions(-)

----------------------------------------------------------------
### I2 the ONLY pre-existing file modified is test_task_cards.py, and only KNOWN_MISSING
    $ git diff -- tests/unit/test_task_cards.py
    rc=0
    key output (last 24 lines):
      diff --git a/tests/unit/test_task_cards.py b/tests/unit/test_task_cards.py
      index 094add7..2a6b302 100644
      --- a/tests/unit/test_task_cards.py
      +++ b/tests/unit/test_task_cards.py
      @@ -25,13 +25,9 @@ CARD_DIR = REPO / "orchestrator" / "tasks"
       TASK_TOTAL_DENOMINATOR = 29
       
       # D-016 登记时的已知缺口（25 张，其中 14 张 critical=true）。补齐一张即须从此处删掉一个 id。
      -KNOWN_MISSING: frozenset[str] = frozenset(
      -    {
      -        "M3-P02",
      -        "M5-03",
      -        "M5-P01",
      -    }
      -)
      +# R12 / FU-33（D-041）：M3-P02、M5-P01、M5-03 三张卡已补齐，本集合按单调收敛纪律清空。
      +# 全集双向对账改由 tests/unit/test_task_cards_complete.py 守护（含台账三键对账，D-042）。
      +KNOWN_MISSING: frozenset[str] = frozenset()
       
       # 早于手册 15.5「子任务档位表」要求交付/执行的历史卡，不追溯补写。
       LEGACY_CARDS: frozenset[str] = frozenset({"M0-01", "M0-P01"})

----------------------------------------------------------------
### I3 the two read-only guards are byte-identical to HEAD
    $ git diff --exit-code HEAD -- tests/unit/test_task_card_narrative.py tests/unit/test_counts_freshness.py && echo 'both read-only guards UNCHANGED (rc=0)'
    rc=0
    key output (last 8 lines):
      both read-only guards UNCHANGED (rc=0)

----------------------------------------------------------------
### I4 nothing under hard_deny was written
    $ git status --porcelain -- orchestrator/state.json orchestrator/defects/ orchestrator/handoff/ src/ web/ scripts/ migrations/ spec/ contracts/ prototype/ docs/ | sed 's/^/      /' ; echo '(empty output above == no hard_deny path was touched)'
    rc=0
    key output (last 12 lines):
            ?? orchestrator/handoff/LANE-COMMON.md
            ?? orchestrator/handoff/R13-lane-Y-M0-04-S2b-2.md
            ?? orchestrator/handoff/R13-lane-Z-M2-01-S1.md
            ?? orchestrator/handoff/round12-lane-W-return-raw.md
      (empty output above == no hard_deny path was touched)

