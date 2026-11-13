# R12 · lane X（Mill）原始回执归档

> 归档义务：`resume.checkpoint_R8.lane_raw_report_archive` —— lane 的原始回执必须先落盘归档，
> 再 `close_agent` 释放并发槽。本文件是**原文照录**（含 lane 自报的估算值与 U 项），
> 编排器的独立复验结论见 `orchestrator/state.json -> resume.round12_lane_X_return.orchestrator_reverification`，
> **不采信本文件的自报值**（`rule_no_trust_handoff_summary_assertions`）。
>
> - lane：X ｜ nickname：Mill ｜ agent_id：`01a1d70a-d4d8-75b3-8fc3-dd67c14405c4`
> - 档位：qwen3.8-max / reasoning high ｜ 任务：GOVERNANCE · FU-33 / D-041（+ D-042 取证）
> - 派单轮：R12 ｜ 回执轮：R13 ｜ 结果：PASS（1 轮成型，loop_cap=2）

```text
RESULT: PASS

R12 · lane X · FU-33 / D-041 (+ D-042 取证) · qwen3.8-max / reasoning high
基线对账口径 = HEAD 51af733（93 commits，lane W 的 FU-29 在我执行中途入库，故非派单文所给 ce08975/92）
+ 我 write_set 的增量。未 git add / 未 commit（§15.2 归编排器）。

── 1. 三张卡（口径全部复用只读守护 test_task_card_narrative._split，未自造）───────────
卡        head  ≤60   tail  ≤40   total ≤200  表头逐字                 REQUIRED_SECTIONS 4 串
M3-P02     43   OK     19   OK     75   OK   | 子任务 | 档位 | 预估 token | 产出 |   全命中(scope_allow L31 / scope_deny L32 / outputs L31 / 子任务档位表 L44)
M5-P01     40   OK     20   OK     70   OK   同上（逐字相等）                        全命中(L28 / L29 / L31 / L45)
M5-03      37   OK     18   OK     61   OK   同上（逐字相等）                        全命中(L25 / L26 / L28 / L37)
字节卫生：三卡均 UTF-8 / 无 BOM / 无 CR / 末字节 0x0a（tail -c 1 | xxd 独立复核）。
M5-03 `human_only_action` 字面串命中 10 处，行号 = 1, 2, 6, 8, 30, 40, 41, 42, 43, 47；
  「禁把交付确认动作派给任何子智能体自证通过」在 **第 8 行**（§human_only_action 首条）。
  档位表 4 行数据行 tier 列全为 `human`、token 列全为 `0k`；表头未走任何豁免。
  LEGACY_CARDS / LEGACY_NO_TABLE / LEGACY_TAIL_ANNOTATED **三集均未改动**，M5-03 未进任何豁免集
  （grep 反证：M5-03 在两个守护文件里 0 命中）。
A179：三卡 inputs 段均显式写明「切片待 FU-34 于派单前补切」；且**未**出现任何
  `handoff/<id>.slice.json` 具体文件名（grep 反证 0 命中），只写 `orchestrator/handoff/<task-id>.slice.json`
  泛式 —— 该串被扫描器解析为已存在的目录，既不悬空也不误导下游（D-036 同型）。

── 2. 新守护 tests/unit/test_task_cards_complete.py（本 lane 核心产出）───────────────
13 个用例 = 4 条实树断言 + 9 条正向对照（5 条 tmp_path 假树 / 4 条伪造台账）。实测 12 passed + 1 designed RED。
· 双向：test_no_registered_task_lacks_a_card（missing）／test_no_card_lacks_a_registered_task（orphan），
  各自独立断言 + 独立报错文本。实测 missing=[] orphan=[]。
· 分母：len(tasks)==29 且 len(cards)==29 双双写死，断言消息含「任务总数变更须同批更新此分母并说明依据」。
· 台账三键对账（D-042）：逐键比对 measured，**并**核恒等式；刻意不只核恒等式。
· 纯函数 reconcile(card_dir, task_ids) 与 ledger_violations(counts, measured_cards, measured_missing)
  被实树用例与正向对照**共用**，判定逻辑未写死在用例里。
· 只用 json + pathlib（typing.Any 仅为标注）；无 __subclasses__、无 subprocess、无 import 被测源码、无 type: ignore。
· 正向对照实测值（原始输出 evidence/M0/FU-33/positive-control.log）：
  FORM A 多卡 30/29 → orphan=['M9-99']；FORM B 少卡（回放补卡前 26/29）→ missing=['M3-P02','M5-03','M5-P01']；
  FORM C 空树 → 29 条全报 missing（防 glob 扫空假绿）；FORM D 目录不存在 → 同样不假绿；
  D-042 回放（台账 20/9/29 vs 实测 26/3）→ 报出两条键值违规，**且断言恒等式子检查不触发**
  （证明抓住 D-042 的是逐键比对而非恒等式）；恒等式单独破坏（29/1/29）→ 报恒等式违规；
  一致台账（29/0/29）→ 空列表；缺键 → 抛 AssertionError（A159 不静默通过）。

── 3. §4 命令 rc 与期望值对账 ──────────────────────────────────────────────────
命令                                            rc    实测                        期望/判定
ruff format --check（write set，.py/.md）        0     6 files already formatted   OK
ruff format --check .（全表，仅供参考）           0     239 files already formatted  OK（构成见下）
ruff check（2 个 .py）                           0     All checks passed!          OK
mypy（全表）                                     0     81 source files             80 → 81（+1 .py）OK
pytest（§4 六文件路径限定）                       1     43 passed / 1 failed        唯一 failed = 见下 ①
pytest -q（全表，仅供参考）                       1     502 passed / 1 failed       490 + 13 新用例 = 503 OK
test_task_cards.py                               0     全绿（KNOWN_MISSING 已收敛为 frozenset()）
test_task_card_narrative.py（只读）               0     7 passed，29 卡全过
test_state_ledger.py / test_wave_deps_consistency.py  0  全绿
test_counts_freshness.py（只读）                  0     **绿**                      见下 ②
git diff --exit-code 两个只读守护                  0     UNCHANGED                   OK
hard_deny 面 git status                           —     空                          OK（零越界）

① **预期中间态红（非缺陷）**：test_ledger_card_counts_match_disk_measurement。
   台账仍为 20/9/29，磁盘实测 29/0/29 → 报「task_cards_on_disk=20 与实测 29 不符」+「known_missing_cards=9 与实测 0 不符」。
   这正是 D-042 §6① 要求「校正必须与三张新卡在同一次提交内完成」的那条断言；编排器把三键改成 29/0/29 即转绿。
   我**未**为了让它变绿而弱化判据（那会让守护失去全部价值）。
② **与派单文预测不符，如实上报**：派单文说 test_counts_freshness 提交前必然红，实测为**绿**。
   原因：lane W 的提交 51af733 在我执行中途入库，已把 counts 刷到 230（py 82 + md 148），与 HEAD 树实测一致。
   我新增的 5 个 in-scope 文件仍是 untracked，不进 `git ls-tree -r HEAD`，故不影响该守护。**未去修它。**
   附：我第一次跑它时确实见到一次红（md 147 vs 台账 148），那是 lane W 提交落地瞬间的 IN_FLIGHT_CONTAMINATION，
   重跑即绿 —— 不是我的红，也未修。
③ 全表 ruff 分母 239 的构成（ruff --verbose 实测：py 83 + md 156，其他扩展名 0）：
   py 82+1(我的守护)；md 148+3(三卡)+1(commands.md)+**4(编排器自己在 orchestrator/handoff/ 下新落的
   untracked .md：LANE-COMMON.md、R13-lane-Y-M0-04-S2b-2.md、R13-lane-Z-M2-01-S1.md、
   round12-lane-W-return-raw.md)**。即**我这一 lane 的净增量是 +5（230→235）**，另 4 个不是我的，
   且该目录在我 hard_deny 内，未触碰。权威数字仍由编排器在冻结树上实测，我未算死、未改台账。
   顺带实测到两条口径事实：ruff 目录遍历**只**收 .py/.md（把 .txt/.log 显式传给 ruff format 会被当 Python
   解析并报 invalid-syntax，我的 commands.md 第一版踩过此坑，已修正并在证据里留痕）；
   .gitignore 含 `!evidence/**/*.log`，故两个 .log 证据会被入库，同时不在 ruff 与悬空扫描的作用域内。

── 4. D-042 取证（只取证，未改台账）────────────────────────────────────────────
evidence/M0/FU-33/counts-drift.txt：台账现值 20 / 9 / 29 vs 磁盘实测 29 / 0 / 29（逐键 match=False/False/True）。
漂移分解已拆开，避免两个成因被混为一谈：D-042 历史漂移 = 26 − 20 = **6**（对应 R11-T 的 6 张 wave3 卡）；
当前可见原始差 29 − 20 = 9 = 历史 6 + 本 lane 新增 3，**后者不是台账腐化**，请编排器勿把 9 当作 D-042 漂移量。
恒等式 20+9==29 算术成立而两操作数皆假 —— 已原样复现并由正向对照钉死。

── 5. 悬空引用自查（用 scripts/orch_harness.py::dangling_refs 本体扫，非自造）────────────
本 lane 全部文件 → **4 条**，去重后 **3 条路径**，每条都是该卡自己 state.json scope 字面量的逐字转写
（前瞻产出落点，任务未跑之前不可能存在）：
  M3-P02.md → evidence/monthly/M3-P02/     M5-P01.md → evidence/monthly/M5-P01/
  M5-03.md  → docs/delivery/HANDOVER.md    （第 4 条是 commands.md 里 H1 grep 的真实输出再次含 HANDOVER.md，同一路径）
尺度参照：补卡前已入库的 26 张卡本身携带 **156** 条同类悬空引用，说明 run_commit 一直靠 allow_dangling 容忍此类。
所有**权威引用**路径逐条 os.path.exists 复核通过（spec 四处 A178 路径、contracts/openapi.json、
contracts/sqlite-v1.sql、docs/delivery/LONG-HORIZON-ORCHESTRATION.md、orchestrator/state.json、
orchestrator/defects/D-041|D-042|D-013|D-036|D-022.md、orchestrator/handoff/、orchestrator/change-requests/、
orchestrator/BLOCKERS.md、scripts/）。A178 禁用文件名在三卡中 **0 命中**（grep 反证）。
详见 evidence/M0/FU-33/dangling-refs.log（含完整解读）。

── 6. U 项（无法从卡/派单文/spec 确定，如实上报，未猜）──────────────────────────────
U-A 上述 3 条悬空引用如何处置。① 编排器把它们加进本次 run_commit 的 allow_dangling（**我倾向此项**：
    与 156 条既有同类完全同型，且都是台账自己写的 scope 字面量，改写反而失真）；② 我把它们拆成
    「已存在目录 + 独立文件名 token」形式规避正则（我对 defects 通配已采用此法，故 defects 面零新增悬空）。
    倾向 ①，但若编排器的扫描不接受，我可 5 分钟内改成 ②。
U-B M5-03 的「预估 token」列填法。① 全填 `0k`（**我倾向**：human 档不消耗模型 token，填任何非零值都是编造）；
    ② 折算人工工时为 token 当量。已按 ① 落地并在卡内写明 §6.6 两项 flash 占比对本卡**不适用**（无 flash 子任务），
    未为凑配比把任何 human 子任务降成 flash（那正是 D-041 §6② 禁止的自证）。
U-C 卡内 U 项（交未来执行 lane 的编排器裁定，均已写进各卡，未自行决定）：
    M3-P02 → U-1 与 M3-04 的 `pages/review/**` vs `pages/review/monthly/**` 写权包含冲突（倾向在台账侧收窄 M3-04）；
             U-2 两个上游冻结件（M3-04 图表适配器、M3-P01 指标注册签名）实测**尚不在磁盘**，倾向「缺任一即不派单」；
             U-3 是否给证据目录追加文件数守卫。
    M5-P01 → U-1 D-022 的 `SNAPSHOT_SUPERSEDED` 未终裁（倾向 interim 记法 + **另立** DMR 单登记契约欠账）；
             U-2 「跨工作区、重启与恢复演练」无可判红判据（倾向环境三事实 + 重启后 SHA 不变，二者合取）；
             U-3 AC-MR-12 是本卡唯一 primary（实测 SOLO、cross_ref 为空），但三条路径实现分散在 M4-03/M3-P02/M4-P01，
                   倾向把三者补进该条 cross_ref 以便 FAIL 时定位归属；
             U-4 两条 QA 线对同 12 条 AC 结论分歧时无仲裁方，倾向「分歧即立 DMR 单、双方结论都保留」。
    M5-03  → U-1 签署无可判红判据（倾向「手写签收串+日期」与「三条路径回执指针齐备」合取）；
             U-2 「待补事项与责任明确」缺分母（倾向以全部 status!=CLOSED 缺陷单 + 各卡 U 项全集为分母）；
             U-3 wave10 为 serial 单环，建议 wave9 出口增设「M5-P01 未 PASS 即不进 wave10」硬门。
    AC-MR-01..12 原文全部在 `.append.md`:7–18 找到并逐字引用，**无一条需要我自编判据**（未触发派单文 §6-5 的报 U 条件）。

── 7. 过程中自查并自行更正的两处（留痕，未静默抹平）──────────────────────────────
(a) M5-P01 初稿把 12 条 AC-MR 全写成「本卡不声明 primary」。读 `acceptance.primary_owner` 实测后发现
    **AC-MR-12 = {primary: M5-P01, cross_ref: [], confidence: SOLO}**，即本卡是 AC-MR-12 的唯一主证方；
    已改写为「primary 1 条 + cross_ref 11 条（01/02→M1-P01，03..08→M3-P01，09/10/11→M4-P01）」并新增
    acceptance: 段，同时把该事实提为 U-3。若未更正，wave9 会漏掉一条主证责任。
(b) M5-P01 初稿为「逐字照抄」而转写了 waves[9].constraint 原文，其中含 `evidence/M5-qa/`，
    自查悬空扫描发现它多贡献 1 条悬空引用；已改为只转写属于本卡的那一半并注明理由，悬空引用由 4 降到 3。
    同类地，初稿曾把 A178 禁用的月报 AC 文件名写进卡内以「否定」它 —— 转写即等于把悬空引用复制进新卡，
    已删除，改为指向 D-041 原文。

── 8. IN_FLIGHT_CONTAMINATION（归属他人，未修）──────────────────────────────────
· orchestrator/handoff/ 下 4 个 untracked .md（LANE-COMMON.md、R13-lane-Y-M0-04-S2b-2.md、
  R13-lane-Z-M2-01-S1.md、round12-lane-W-return-raw.md）—— 编排器自己的 R13 派单准备件，
  使全表 ruff md 分母 +4（156 而非我这侧的 152）。该目录在我 hard_deny 内，未读改。
· 第一次跑 test_counts_freshness 见到的 md 147 vs 台账 148 红：lane W 提交 51af733 落地瞬间的中间态，重跑即绿。
· lane W 的写集（src/campaignlab/{domain,worker}/errors.py、src/campaignlab/infra/artifacts.py、
  tests/unit/test_layering_edges.py）在我复跑时已入库且全绿，未观察到其残留红。

── 9. 证据落点 evidence/M0/FU-33/ ─────────────────────────────────────────────
commands.md（417 行，逐条命令原文 + rc + 关键输出，含 C3 分母构成分析与一处自我更正留痕）
card-metrics.txt（43 行，_split 原样口径 + 字节卫生 + REQUIRED_SECTIONS 行号 + M5-03 tier 列逐行）
positive-control.log（83 行，9 条正向对照 pytest -v 原始输出 + 4 种假树形态原始判定 + D-042 台账回放）
counts-drift.txt（77 行，台账 vs 磁盘逐键 + 漂移分解 + 台账原文注记 + 期望终值）
diff-stat.txt（57 行，numstat / status / 逐文件 wc -c / 写权符合性 / counts 期望增量）
dangling-refs.log（39 行，扫描器原始输出 + 156 条既有同类对照 + 完整解读）

── 10. 自报 token ───────────────────────────────────────────────────────────
约 125k / 上限 200k（**估算值**，非精确计量；未超上限，不报 over_cap，未抹平）。
L 循环用量：**1 轮**（上限 2 轮）。同一条守护未出现连续 2 轮修不绿，无需 STALLED / 降级交付。
未触发缩小范围降级：三张卡 + 守护全部交付。
```
