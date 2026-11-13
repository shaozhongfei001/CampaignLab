# Q-VERIFY-WAVE1 - 00-index.md

Every count below was produced by `os.walk` + `open(..., 'rb')` over this directory at write time
(rule_evidence_count_must_be_programmatic). Nothing was hand-tallied. The byte and line figures for
this file itself are a two-pass fixed point (pass 1 renders, pass 2 re-reads the written file), so the
self-row is not one generation stale.

| file (relative to this directory) | bytes | lines | kind | encoding assertion |
|---|---|---|---|---|
| `00-index.md` | 2311 | 38 | text | no-BOM / no-CR / ends-NL OK |
| `commands.md` | 33723 | 135 | text | no-BOM / no-CR / ends-NL OK |
| `defects-proposed.md` | 7401 | 52 | text | no-BOM / no-CR / ends-NL OK |
| `raw/gate1-doctor.txt` | 1082 | 17 | text | no-BOM / no-CR / ends-NL OK |
| `raw/gate2-pytest-tests-api.txt` | 814 | 17 | text | no-BOM / no-CR / ends-NL OK |
| `raw/gate3-verify-package.txt` | 648 | 16 | text | no-BOM / no-CR / ends-NL OK |
| `raw/gate4-alembic-current.txt` | 368 | 11 | text | no-BOM / no-CR / ends-NL OK |
| `raw/gate5-npm-test.txt` | 3032 | 46 | text | no-BOM / no-CR / ends-NL OK |
| `raw/gate6-npm-typecheck.txt` | 301 | 13 | text | no-BOM / no-CR / ends-NL OK |
| `raw/q-cmdlog.jsonl` | 85490 | 99 | text | no-BOM / no-CR / ends-NL OK |
| `verdict.md` | 20987 | 132 | text | no-BOM / no-CR / ends-NL OK |

## Totals

- files under `evidence/M0/Q-VERIFY-WAVE1/**` (recursive, including this index): **11**
- top-level deliverables: **4** (`00-index.md`, `verdict.md`, `commands.md`, `defects-proposed.md`)
- raw transcripts under `raw/`: **7**
- total bytes: **156157**
- total lines: **576**
- command four-tuples recorded in `commands.md`: **110**
- mandated gates personally re-run (dispatch section 6): **7 of 7**
- verdict tally over the 11 gates: PASS **7**, PASS_WITH_TODO **4**, FAIL **0**, NOT_YET_COLLECTED **0**
- bare `rc:null` gates remaining: **0** (A109 (3) discharged for all 11)
- text files failing the no-BOM / no-CR / ends-with-NL assertion: **0**
- proposed defects: **6** (P-1 .. P-6); P-3 explicitly exonerates lane F after an ancestry check

Note on the 11-gate tally: `verdict.md` also contains a 3-row composite-AC table in section 6 whose
verdict cells are `**PASS**` / `**PASS_WITH_TODO**`; those are AC-level roll-ups, not gates, and are
excluded from the counts above.
