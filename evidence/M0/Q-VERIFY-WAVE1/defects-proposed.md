# Q-VERIFY-WAVE1 - defects-proposed.md

Proposals only. I opened no tickets (ticket creation is the orchestrator's right) and repaired nothing
(judging lane: non-owned red items get attributed, not fixed).

## P-1 - dispatched gate commands for doctor / alembic cannot meet their own stated expectations
- Phenomenon: on a bare tree, gate 1 yields `PASS=3 WARN=2 FAIL=0 RESULT=DEGRADED` (expected `RESULT=HEALTHY`) and gate 4 yields rc=0 with no revision line (expected `head=0001_initial_schema`).
- Evidence: `raw/gate1-doctor.txt`; `raw/gate4-alembic-current.txt`; corrected re-runs `H1`/`H2`/`H3` in `raw/q-cmdlog.jsonl`; `migrations/alembic.ini:20-24`; `evidence/M0/M0-02/ac.md:5`.
- Characterisation: **dispatch / gate-catalogue defect, not a product defect**. The code is correct - an unmigrated default data dir SHOULD be DEGRADED, and doctor says so with actionable hints. The gate command simply omits the `CAMPAIGNLAB_DATA_DIR` provisioning the S5 lane used. Proven by reproducing `RESULT=HEALTHY` (`PASS=5 WARN=0 FAIL=0`) and `0001_initial_schema (head)` in a provisioned scratch dir.
- Suggested severity: **Medium** - a standing false-RED risk for every future wave exit that reuses this gate text.
- Owner: orchestrator (brief / gate catalogue). Secondary: M0-02 could ship a documented provisioning one-liner for verification runs.

## P-2 - gate 4 mutates the host environment, making gate 1 order-dependent
- Phenomenon: `alembic current` under the default env created `~/.local/share/campaignlab/state/campaignlab.db` (0 bytes) at `02:32:51`; re-running gate 1 afterwards changed its WARN text from 'data_dir does not exist' to 'writable but missing OPERATIONS.md subdirs: raw,snapshots,results,exports,tmp,logs', and the database WARN from 'does not exist' to 'intact but no alembic_version (not yet migrated)'.
- Evidence: `raw/q-cmdlog.jsonl` tags `G1`, `G2`; mtimes under `~/.local/share/campaignlab`.
- Characterisation: a read-only-looking query has a write side effect, so the two gates are neither idempotent nor order-independent. Outside the repo, so no A144 impact.
- Suggested severity: **Medium**.
- Owner: M0-02 (`migrations/env.py` / alembic wiring) plus orchestrator (gate ordering). I did not delete the artefact - deletion is also a mutation and the call is not mine.

## P-3 - a green guard at capture time is red at HEAD (guard rot, NOT a lane false-green)
- Phenomenon: the committed M0-03/S5 transcript records `[G5c] cmd: grep -rn '300[012]' web/*.config.* web/playwright.config.ts` with `rc=1 expect=1 -> OK` and `(no output)`. Re-running that command VERBATIM at HEAD `1675d46` gives rc=0 with one hit: `web/vite.config.ts:32`, a COMMENT reading 'host 3000/3001/3002 measured BUSY (NOTE-01)...'.
- **The S5 lane is exonerated.** I first suspected an unreproducible false-green, then checked ancestry rather than assuming: `git merge-base --is-ancestor c9ef997 9832fd1` -> `NOT_ANCESTOR`, i.e. commit `c9ef997` (which introduced that comment line) is NOT an ancestor of the S5 commit `9832fd1`. Confirmed directly against the blobs: `git show 9832fd1:web/vite.config.ts | grep -cE '300[012]'` -> `0`, while `git show HEAD:web/vite.config.ts | grep -cE '300[012]'` -> `1`. So at capture time the line genuinely did not exist and `rc=1` was correct.
- Evidence: `evidence/M0/M0-03/S5-gate-transcript.txt` (G5c block); `raw/q-cmdlog.jsonl` tags `P3-G5c-verbatim`, `P4-c9ef997-ancestry`, `Q1-c9-ancestry-full`, `Q2-vite-at-S5`, `Q3-vite-at-HEAD`.
- Characterisation: **guard rot / evidence staleness**, not fabrication and not a product defect. A guard recorded as green in a committed transcript no longer holds at HEAD, and nothing in the repo re-checks it. The pattern is also too coarse - it matches prose in a comment, not configuration - so it will keep tripping on any future comment that mentions those ports.
- Suggested severity: **Medium** on evidence integrity (transcripts silently diverge from HEAD), **Low** on product impact.
- Owner: M0-03 (lane F) to re-derive G5c at HEAD and either narrow the pattern to non-comment lines or reword the comment; orchestrator to decide whether committed transcripts should carry an as-of-HEAD re-check obligation at wave exit.

## P-4 - ledger pointer for the public-component freeze doc is byte-stale
- Phenomenon: the ledger records `orchestrator/handoff/M0-03-public-components.md` as '303 lines / 26803 B'; actual is 303 lines / **27115 B** (+312 B).
- Evidence: programmatic `os.stat` (`raw/q-cmdlog.jsonl`); `git show --numstat 0419505 -- orchestrator/handoff/M0-03-public-components.md` -> `1  1`, i.e. one line replaced by the R9-C / D-037 correction AFTER S10 registered the pointer.
- Characterisation: same class as D-038 (evidence figure drift), far smaller magnitude, and the line count still matches. Not a product defect.
- Suggested severity: **Low**.
- Owner: orchestrator (ledger refresh).

## P-5 - freeze doc asserts a filesystem state that is now false
- Phenomenon: `orchestrator/handoff/M0-03-public-components.md` lines 20, 30 and 255 assert that `web/src/components/state/` does not exist; line 20 even ships a guard whose expected output is `STATE_DIR_ABSENT`. At HEAD that directory exists with 6 files, so the doc's own guard would now print `STATE_DIR_EXISTS`.
- Evidence: lines 20/30/255 of that doc; `git show --numstat 69db892 -- web/src/components web/tests` (6 component files + 6 spec files, all pure additions); `orchestrator/handoff/M0-03b-freeze.md:108-119`, which does freeze all 6.
- Characterisation: documentation drift caused by a later task landing in a directory an earlier doc described as absent. Freeze COVERAGE is not missing - `M0-03b-freeze.md` handles it - so this is staleness/consistency, not a gap.
- Suggested severity: **Low-Medium** (a future lane running that guard verbatim gets a surprise RED).
- Owner: M0-03b / orchestrator - add an 'as-of HEAD' marker to the S10 snapshot, or append a forward-pointer to `M0-03b-freeze.md`.

## P-6 - ledger timestamps run ahead of the host clock
- Phenomenon: state.json written during my session carries `updated_at` and `dispatched_at` = `2026-11-14T03:20:00+08:00`; the host clock at that moment read `2026-11-14 02:41:10 +0800`.
- Evidence: `raw/q-cmdlog.jsonl` tags `L2-state-added-lines`, `L5-state-mtime-vs-now`.
- Characterisation: roughly 39 minutes of skew. If ledger timestamps are ever used to order or age evidence, this will mis-sort.
- Suggested severity: **Low**.
- Owner: orchestrator.

## Recorded as NOT defects (so nobody re-opens them)
- The byte-identical screenshot pairs under `evidence/M0/ui/` and `evidence/M0/M0-03/` are intentional: `web/tests/e2e/ui-01-screenshots.spec.ts:18-19` writes both landings in a single run. sha256 equality is the expected outcome and was verified programmatically (`2f3bf97a...` and `35981b0e...`).
- `web/vite.config.ts`, `web/vitest.config.ts` and `web/tsconfig.json` lack a trailing newline. Cosmetic; typecheck and vitest are both rc=0.
- Volta's 4 in-flight untracked paths were excluded from A144(c) only under the dispatch's explicit authorization, and nothing I ran touched them. No repo-wide `pytest` / `mypy` / `ruff .` was executed; `tests/api` was the only Python test path run, per the dispatch constraint. No `IN_FLIGHT_CONTAMINATION` was observed in any of the 7 mandated gates - all contamination found was in the A144(c) worktree census.
