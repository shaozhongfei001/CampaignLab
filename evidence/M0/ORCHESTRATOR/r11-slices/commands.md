# R11 commands log - T lane 2026-11-14

cwd for all: /home/szf/dev/CampaignLab

## M1-01
- cmd: `cd /home/szf/dev/CampaignLab && python3 scripts/contract_slice.py --ops createImport,attachImportFile,configureImport,validateImport,getImport,listImports --ac AC-005,AC-006 --tables imports,import_files,source_mappings --out orchestrator/handoff/M1-01.slice.json`
- rc: 0
- key output: spec_version=1.0.1 slice_bytes=60641 slice_lines=2875 sections=['spec_version', 'source', 'operations', 'acceptance_rows', 'ddl', 'truncated_schemas'] missing=[] depth=5 truncated_schemas=[]
- idempotent: sha16 before=eadbd88e4ef79c48 after=eadbd88e4ef79c48 equal=True

## M1-02
- cmd: `cd /home/szf/dev/CampaignLab && python3 scripts/contract_slice.py --ops publishImport,listSnapshots,getSnapshot,correctSnapshot,listDefinitions --ac AC-007,AC-008,AC-020 --tables snapshots,imports,source_mappings,artifacts,idempotency,audit --out orchestrator/handoff/M1-02.slice.json`
- rc: 0
- key output: spec_version=1.0.1 slice_bytes=48363 slice_lines=2190 sections=['spec_version', 'source', 'operations', 'acceptance_rows', 'ddl', 'truncated_schemas'] missing=[] depth=5 truncated_schemas=[]
- idempotent: sha16 before=c5fb644162ba6826 after=c5fb644162ba6826 equal=True

## M1-03
- cmd: `cd /home/szf/dev/CampaignLab && python3 scripts/contract_slice.py --ops classifyChannel,verifyLinks,runComparison,getComparison,listSnapshots --ac AC-009,AC-010,AC-011 --tables analysis_results,snapshots,evidence,object_evidence,artifacts --out orchestrator/handoff/M1-03.slice.json`
- rc: 0
- key output: spec_version=1.0.1 slice_bytes=49807 slice_lines=2310 sections=['spec_version', 'source', 'operations', 'acceptance_rows', 'ddl', 'truncated_schemas'] missing=[] depth=5 truncated_schemas=[]
- idempotent: sha16 before=149366dc731f45f7 after=149366dc731f45f7 equal=True

## M2-01
- cmd: `cd /home/szf/dev/CampaignLab && python3 scripts/contract_slice.py --ops listActivities,createActivity,getActivity,updateActivity,listRules,createRule,getRule,updateRule,confirmRule,checkRule,compareRules --ac AC-002,AC-003,AC-004 --tables activities,activity_bindings,rule_versions,audit,artifacts --out orchestrator/handoff/M2-01.slice.json`
- rc: 0
- key output: spec_version=1.0.1 slice_bytes=84893 slice_lines=4013 sections=['spec_version', 'source', 'operations', 'acceptance_rows', 'ddl', 'truncated_schemas'] missing=[] depth=5 truncated_schemas=[]
- idempotent: sha16 before=8f44b036f0656497 after=8f44b036f0656497 equal=True

## M2-02
- cmd: `cd /home/szf/dev/CampaignLab && python3 scripts/contract_slice.py --ops createRun,getRun,getRunCase,listRuns,getCase,getRule,listCandidates --ac AC-012,AC-013,AC-014,AC-015 --tables runs,run_cases,cases,candidates,artifacts,audit --out orchestrator/handoff/M2-02.slice.json`
- rc: 0
- key output: spec_version=1.0.1 slice_bytes=61170 slice_lines=2768 sections=['spec_version', 'source', 'operations', 'acceptance_rows', 'ddl', 'truncated_schemas'] missing=[] depth=5 truncated_schemas=[]
- idempotent: sha16 before=112b8bcfd0ec0e13 after=112b8bcfd0ec0e13 equal=True

## M2-03
- cmd: `cd /home/szf/dev/CampaignLab && python3 scripts/contract_slice.py --ops createPreflight,listPreflights,getPreflight,reviewPreflight,recordReceipt,getReceipt,listCandidates,getRun --ac AC-016,AC-017 --tables preflights,preflight_rows,receipts,candidates,evidence,audit,artifacts --out orchestrator/handoff/M2-03.slice.json`
- rc: 0
- key output: spec_version=1.0.1 slice_bytes=63524 slice_lines=2822 sections=['spec_version', 'source', 'operations', 'acceptance_rows', 'ddl', 'truncated_schemas'] missing=[] depth=5 truncated_schemas=[]
- idempotent: sha16 before=abf239e13284a00c after=abf239e13284a00c equal=True

## 失败轮次（诚实记录）
- cmd: `wsl.exe -e bash -lc "... for t in ... grep -nE -B2 -A2 ..."` (UI/AC 上下文批量提取)
  - rc: 1 (bash: unexpected EOF) -- 原因: 在 bash -lc 双引号内嵌套 $t 与转义引号，违反通道规则。改用宿主 here-string python 提取脚本重做，rc=0。
- cmd: `python3 .orch_tmp/fix_fp.py` (自指不动点第一版)
  - rc: 0 但打印 UNRESOLVED fixedpoint -- 占位态与终态字符串不一致导致不收敛。第二版 fix_fp2.py 以「文件字节==文内声明字节」判据，pass2 收敛 dir_bytes=954。
## 断言命令（A18 口径，程序化）
- `python3 .orch_tmp/assert_slices.py`: rc=0。对 6 份切片断言: "missing" not in slice; truncated_schemas==[]; source.openapi.sha16=="592571099d638251"; spec_version=="1.0.1"（切片结构中 info_version 不落 source.openapi 键，版本以顶层 spec_version 承载，实测 1.0.1 与活契约 info.version 一致）。全部通过，无 KeyError。
- live openapi: bytes=443309 sha256[:16]=592571099d638251。
