# M0-P01 月报增量契约合入 · 命令与退出码

运行号 run-01 · 时间 2026-11-12T20:31:23+08:00 · 分支 m0-framework · 合入前 HEAD 30291b8
环境: Python 3.14.10 / uv uv 0.13.7 (x86_64-unknown-linux-gnu) / Node v24.22.3 / npm 11.19.1 / Ubuntu 24.04.2 LTS

## 1. 来源完整性（三份基线均可字节级复验）
```
$ sha256sum CampaignLab-SDD-Handoff-v1.0.zip
c8ac004c50f53ea08416807bd43a4b585784b31892513082e4aa635952850d81  CampaignLab-SDD-Handoff-v1.0.zip  CampaignLab-SDD-Handoff-v1.0.zip
  期望 c8ac004c50f53ea08416807bd43a4b585784b31892513082e4aa635952850d81 （补丁工具内置 BASE_SHA）
$ sha256sum spec/CampaignLab-SDD-v1.0/SHA256SUMS
3d3e32632c1d28368fc3fec4e591572dc73b0ed56eb89193e4c84d54e4ef3d91  spec/CampaignLab-SDD-v1.0/SHA256SUMS
  期望 3d3e32632c1d28368fc3fec4e591572dc73b0ed56eb89193e4c84d54e4ef3d91 （内置 BASE_MANIFEST_SHA）
$ sha256sum CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta.zip
13b1be8cfa11c8b457f3d66eb3d9431e8238c15b5b0985b15d79dc3a1856c371  CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta.zip  CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta.zip
$ cd spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta && sha256sum -c DELTA-SHA256SUMS | tail -3
reference/EVIDENCE-AND-DECISIONS.md: OK
tools/monthly_delta.py: OK
ui/MONTHLY-PAGES.md: OK
manifest_rc=0
```

## 2. 只读预检 A：对纯净 v1.0 基座
```
$ python3 spec/CampaignLab-SDD-Patch-v1.0.1-Monthly-Review-Delta/tools/monthly_delta.py --base <原 ZIP>
PASS 补丁摘要 21 项
ADD      openapi.json /components/schemas/ReviewCreate/properties/profile
ADD      openapi.json /components/schemas/Review/properties/monthly_review
ADD      openapi.json /components/schemas/MonthlyCapacity
ADD      openapi.json /components/schemas/MonthlyComparison
ADD      openapi.json /components/schemas/MonthlyOriginOverlap
ADD      openapi.json /components/schemas/MonthlyParticipation
ADD      openapi.json /components/schemas/MonthlyProduction
ADD      openapi.json /components/schemas/MonthlyReview
ADD      openapi.json /components/schemas/MonthlyTrend
ADD      source-json.schema.json /$defs/SourceMetadata/properties/monthly_review
ADD      source-metadata.schema.json /properties/monthly_review
UPDATE   openapi.json /info/version · 1.0.0 → 1.0.1
只读检查通过。
rc=0
```

## 3. 只读预检 B：对活契约（合并前，活契约=基线逐字节副本）
```
PASS 补丁摘要 21 项
ALREADY  openapi.json /components/schemas/ReviewCreate/properties/profile
ALREADY  openapi.json /components/schemas/Review/properties/monthly_review
ALREADY  openapi.json /components/schemas/MonthlyCapacity
ALREADY  openapi.json /components/schemas/MonthlyComparison
ALREADY  openapi.json /components/schemas/MonthlyOriginOverlap
ALREADY  openapi.json /components/schemas/MonthlyParticipation
ALREADY  openapi.json /components/schemas/MonthlyProduction
ALREADY  openapi.json /components/schemas/MonthlyReview
ALREADY  openapi.json /components/schemas/MonthlyTrend
ALREADY  source-json.schema.json /$defs/SourceMetadata/properties/monthly_review
ALREADY  source-metadata.schema.json /properties/monthly_review
ALREADY  openapi.json /info/version
只读检查通过。
rc=0
```

## 4. 候选生成 → 指针级审计 → 覆盖
```
$ monthly_delta.py --contracts-dir contracts --stage orchestrator/handoff/monthly-candidate-20261112
候选文件: openapi.json source-json.schema.json source-metadata.schema.json 
$ check_contracts.py diff --base contracts --live <候选>/contracts --files openapi.json,source-json.schema.json,source-metadata.schema.json
total_differences=12 compared=3 skipped=[]   # 11 added + 1 changed，与工具 ADD/UPDATE 清单一一对应
$ check_contracts.py diff --base spec/CampaignLab-SDD-v1.0/contracts --live <候选>/contracts
total_differences=12 compared=3 skipped=[]   # 对不可变基线同为 12 处，证明无夹带
$ cp <候选>/{openapi.json,source-json.schema.json,source-metadata.schema.json} contracts/
其余 8 个文件与基线 sha256 逐个比对: 全部 SAME
```

## 5. 合并后门禁
```
$ check_contracts.py check
CONTRACT CHECK PASS 登记项=12 实测差异=12 元校验=skipped
rc=0
$ check_contracts.py check --validate
CONTRACT CHECK PASS 登记项=12 实测差异=12 元校验=6
rc=0
```

## 6. 幂等性：合并后复跑预检应全部 ALREADY（重复合并不产生二次变更）
```
PASS 补丁摘要 21 项
ALREADY  openapi.json /components/schemas/ReviewCreate/properties/profile
ALREADY  openapi.json /components/schemas/Review/properties/monthly_review
ALREADY  openapi.json /components/schemas/MonthlyCapacity
ALREADY  openapi.json /components/schemas/MonthlyComparison
ALREADY  openapi.json /components/schemas/MonthlyOriginOverlap
ALREADY  openapi.json /components/schemas/MonthlyParticipation
ALREADY  openapi.json /components/schemas/MonthlyProduction
ALREADY  openapi.json /components/schemas/MonthlyReview
ALREADY  openapi.json /components/schemas/MonthlyTrend
ALREADY  source-json.schema.json /$defs/SourceMetadata/properties/monthly_review
ALREADY  source-metadata.schema.json /properties/monthly_review
ALREADY  openapi.json /info/version
只读检查通过。
rc=0
```

## 7. 负例：篡改活契约必须被门禁拦下
```
injected __tamper__ node into contracts/dependencies.json
FAIL 未登记的契约差异: dependencies.json /__tamper__ (added)
CONTRACT CHECK FAIL (1 项)
tamper_rc=1  # 期望 1
CONTRACT CHECK PASS 登记项=12 实测差异=12 元校验=skipped
restored_rc=0  # 期望 0
```

## 8. 结论
- 12 个节点全部 ADD/UPDATE 成功，0 CONFLICT，0 ALREADY 跳过（首次合入）。
- 新增属性均为可选，未进入任何 required 数组；既有端点与既有字段未被修改 → 向后兼容。
- 活契约 openapi info.version = 1.0.1；差异全部登记 contracts/CHANGES.json（CR-001 / ADR-004）。
- 门禁具备拦截能力（篡改负例 rc=1），已接入 CI job contract-gate。
