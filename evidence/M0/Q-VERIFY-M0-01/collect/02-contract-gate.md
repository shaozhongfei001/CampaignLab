# A2 · M0-P01 契约门禁复跑

两条命令均走 PowerShell→base64→WSL 通道执行（首跑因引号通道事故零输出，已重跑，留痕见 00-index 事故记录 2）。
原文全量：`raw/a2-contract-gate.log`。

| # | 命令原文 | rc | 输出原文（逐字） |
|---|---|---|---|
| C1 | `python3 scripts/check_contracts.py check` | 0 | `CONTRACT CHECK PASS 登记项=12 实测差异=12 元校验=skipped` |
| C2 | `uv run --no-sync python scripts/check_contracts.py check --validate` | 0 | `CONTRACT CHECK PASS 登记项=12 实测差异=12 元校验=6` |

- 「登记项 == 实测 == 12」：**成立**（两条输出均为 登记项=12 实测差异=12）。
- C1 ts=2026-11-12T23:05:06+08:00；C2 ts 同秒级记录于 raw。
- 附加旁证（A3 独立实做）：contracts/ 与基线逐文件 cmp：SAME=8、DIFFERS=3（openapi.json、source-json.schema.json、source-metadata.schema.json），
  与 12 个登记节点恰好只触及这 3 个文件的事实一致。
- 材料齐备：是。