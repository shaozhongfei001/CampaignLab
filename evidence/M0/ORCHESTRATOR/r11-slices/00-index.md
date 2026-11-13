# R11 slice index - T lane (qwen3.8-flash) - 2026-11-14

## 本 lane 新产切片

| task | bytes | pct-of-live | ops | AC | tables | truncated | missing key |
|---|---|---|---|---|---|---|---|
| M1-01 | 60641 | 13.68% | 6 | 2 | 3 | [] | False |
| M1-02 | 48363 | 10.91% | 5 | 3 | 7 | [] | False |
| M1-03 | 49807 | 11.24% | 5 | 3 | 7 | [] | False |
| M2-01 | 84893 | 19.15% | 11 | 3 | 6 | [] | False |
| M2-02 | 61170 | 13.8% | 7 | 4 | 7 | [] | False |
| M2-03 | 63524 | 14.33% | 8 | 2 | 7 | [] | False |

live openapi bytes=443309 sha256[:16]=592571099d638251 spec_version=1.0.1

## 未产出任务 U 项

- M3-P02: orchestrator/tasks/M3-P02.md 不存在（ls 仅见 M3-P01），目标无从取，禁猜。
- M5-P01: orchestrator/tasks/M5-P01.md 不存在（ls 仅见 M5-01/M5-02），同上。
- M5-03: orchestrator/tasks/M5-03.md 不存在（ls 仅见 M5-01/M5-02），同上。

EVIDENCE_COUNT os.walk+rb (fixed point): dir_bytes=954 self_bytes=954
