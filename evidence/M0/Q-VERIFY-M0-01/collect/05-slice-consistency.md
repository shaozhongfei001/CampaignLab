# A5 · 切片一致性独立复算

原始输出：`raw/a5-slice.log`。未整读 contracts/openapi.json（443552 B），全部 python3 定点提取。

## 1. 活契约三指标（独立复算）

| 指标 | 实算值 | 编排器转述值 | 判定 |
|---|---|---|---|
| sha256 前 16 | `01bd28f0772f506e`（全值 `01bd28f0772f506e15fb70f07a37479ab9c33c4a3c9a39651445e6fa435cf583`） | 01bd28f0772f506e | **一致** |
| bytes | `443552` | 443552 | **一致** |
| info.version | `1.0.1` | 1.0.1 | **一致** |

## 2. 切片登记值比对

| 字段 | M0-02.slice.json | M0-03.slice.json | 实算 | 判定 |
|---|---|---|---|---|
| source.openapi.path | contracts/openapi.json | contracts/openapi.json | — | ✓ |
| source.openapi.sha16 | 01bd28f0772f506e | 01bd28f0772f506e | 同左 | ✓ |
| source.openapi.bytes | 443552 | 443552 | 同左 | ✓ |
| spec_version | 1.0.1 | 1.0.1 | info.version=1.0.1 | ✓ |

另：state.json counts.live_openapi_sha16=01bd28f0772f506e、live_openapi_info_version=1.0.1 亦同值（旁证，非转述采信）。

## 3. 切片条目统计与内容一致性

- **M0-02**：operations=**5**（createWorkspace、exchangeSession、getHealth、getSession、listWorkspaces）；
  acceptance_rows=**3**（AC-001、AC-034、AC-035）；无 pages 键（0）；无 ddl 键。
- **M0-03**：operations=**5**（同上 5 个 id）；pages=**1**（键 `UI-01`）；无 acceptance_rows 键（0）。
- **抽查 2 个 operationId 的响应状态码**（切片 `operations.<id>.operation.responses` vs 活契约 paths 同 operationId）：
  - `getHealth`：live=/health get，两侧响应码集合均为 `[200,400,401,403,404,409,412,413,422,428,429,500]`，**MATCH=True**；
  - `listWorkspaces`：live=/workspaces get，同上 12 码，**MATCH=True**。
  - 附带事实：切片条目 `method` 为大写（`GET`），openapi paths 的方法键为小写（`get`），属切片工具的规范化表示，
    path 字符串逐字一致（`/health`、`/workspaces`）。不构成内容矛盾，列备案。
- **重切字节级验证**（D-004「重切入库」声明的独立复现）：
  - `python3 scripts/contract_slice.py --ops exchangeSession,getSession,getHealth,listWorkspaces,createWorkspace --ac AC-001,AC-034,AC-035 --out /tmp/qv_M0-02.regen.json` → rc=0；`diff -q` 与入库 M0-02.slice.json **无差异（rc=0）**。
  - `python3 scripts/contract_slice.py --ops <同上 5 id> --ui UI-01 --out /tmp/qv_M0-03.regen.json` → rc=0；`diff -q` 与入库 M0-03.slice.json **无差异（rc=0）**。
  - 即两切片可自活契约以磁盘上的工具逐字节再生，来源链闭环。

## 4. 结论性事实（供判定档）

三项指标、两切片登记、条目统计、抽查状态码、字节级重切：**全部一致，未发现任何不一致条目**。