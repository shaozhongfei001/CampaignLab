# CampaignLab 全行月报 · 纯增量补丁接续入口

**保留 `CampaignLab-SDD-Handoff-v1.0.zip`，把本补丁解压到独立目录。本机 Codex 在原工作树接续。** 补丁提供新增月报的分析说明、12 项验收、页面说明、合成样例和契约节点变更。架构和验收原文继续从 v1.0 读取。

## 第一步 · 确认当前进度

在当前 CampaignLab 开发仓读取：

```bash
git status --short --branch
git log -1 --oneline
git diff --stat
git diff --cached --stat
```

记录当前任务、已经完成的工作及正在修改的文件。保留当前分支、提交和未提交变更。若上个补丁已部分吸收，按本补丁的节点预检核对既有变更。若有其他进程正在写同一文件，先等该次修改落盘，再由当前执行者合入。

## 第二步 · 只读检查契约

从补丁根目录运行。替换路径为实际位置：

```bash
python3 tools/monthly_delta.py --base ../CampaignLab-SDD-Handoff-v1.0.zip
```

`--base` 也接受原始 v1.0 解压根目录。若实现仓已有权威的 OpenAPI 与导入 JSON 契约，改用它们所在的目录：

```bash
python3 tools/monthly_delta.py --contracts-dir /path/to/current/contracts
```

| 结果 | Codex 的处理 |
|---|---|
| ADD 或 UPDATE | 按指定 JSON 路径合入新增节点。仅原 OpenAPI 版本值仍匹配时更新该版本值 |
| ALREADY | 对应节点已经相同，登记并跳过 |
| KEEP | 沿用现有 OpenAPI 版本号 |
| CONFLICT（退出码 2） | 定位冲突文件和节点，结合当前实现与新月报契约合并。先推进无依赖的现有任务 |
| 本机尚未生成 JSON 契约 | 以原 ZIP 为设计基座，按节点改权威模型或源契约，随后使用项目现有命令生成 API 与客户端 |

预检默认只读。需要人工对照时，可在上述命令后加 `--stage /path/to/new-review-directory`，生成独立目录内的候选 JSON。输入契约、源码和基座压缩包保持现有内容。候选文件用于查看差异，合并动作由 Codex 在当前实现中执行。

## 第三步 · 沿现有任务接续

| 当前阶段 | 接续任务 |
|---|---|
| M0 正在开工或已部分完成 | 登记 M0-P01，完成当前未完成任务。按月报入口的依赖安排增量合并 |
| M1 数据或 M2 规则开发已启动 | M1-P01 在原发布机制上增加月报输入。M2 赠券、回拨按原依赖推进 |
| M3 复盘 | M3-P01、P02 优先打通月报分析和工作台 |
| M4 报告与 M5 验收 | M4-P01 复用报告、签认、更正、行动；M5-P01 追加月报端到端走查 |

用 [开发计划](framework/DELIVERY-PATCH.md) 更新当前任务清单。合并后重跑受影响的原验收，再按 [月报验收增补](qa/CampaignLab-Review-Acceptance-Checklist.append.md) 登记实际证据。原 v1.0 包校验从原包解压目录运行。应用验收从当前开发仓运行。

## 补丁中要读的文件

- [ANALYTICS.append.md](architecture/ANALYTICS.append.md) 对应原 `architecture/ANALYTICS.md` 的月报增补章节。
- [CampaignLab-Review-Acceptance-Checklist.append.md](qa/CampaignLab-Review-Acceptance-Checklist.append.md) 对应新增 AC-MR-01 至 12，作为 v1.0 QA 的增补。
- [monthly-contract-delta.json](contracts/monthly-contract-delta.json) 含 11 个新增节点及一个条件版本更新，作用在原 OpenAPI、JSON 导入和 CSV 元数据三个契约。
- [月报实施契约](architecture/MONTHLY-REVIEW.md)、[页面设计](ui/MONTHLY-PAGES.md)、[合成样例](fixtures/MONTHLY-FIXTURES.md) 用于接着做 M1、M3、M4。

## 发给当前本机 Codex 的指令

> 在现有 CampaignLab 工作树接续。先记录当前分支、HEAD、未提交修改和完成的任务，再读这份 START-CODEX-PATCH.md。先用 tools/monthly_delta.py 只读检查月报契约。逐节点合入 ADD，跳过 ALREADY，发现冲突就定位到文件和路径，并继续独立任务。保留原 v1.0 ZIP 和已经完成的实现。把月报任务按 DELIVERY-PATCH.md 挂入当前计划，从第一个未完成且依赖齐备的任务继续实施与验证。
