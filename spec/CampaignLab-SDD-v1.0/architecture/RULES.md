# 规则验证与事件回放

[规则版本 Schema](../contracts/rule-set.schema.json) 与 [案例输入 Schema](../contracts/case-input.schema.json) 定义首版两种有类型规则。字段通过业务表单录入或作为快照导入验证。自由条款作为来源，业务人员确认它所映射的字段。每条条款保留 evidence_id，确认需要字段齐全、待决事项关闭及当前摘要匹配。候选字段变化可在草稿中比较。每次实际运行固定规则与案例确认版本。

## 规则检视

检查时输出 Issue 和对应边界案例。检查活动时间顺序、阈值和奖励量、预算和单人上限、叠加条件、退款条款、候选同模板、竞争和事件顺序。发现条款未确认时返回 NEEDS_CONFIRMATION。基于支持字段生成最小反例，包括阈值减一分、等于阈值、活动起止边界、重复支付、互斥命中、预算刚足和不足、退款后跌破阈值、已核销退款、同日抢占与频次用尽。预算低于单张券、多个规则覆盖同一情境分别给到可复查告警。检查覆盖基于定义的字段、条件和值域，边界样例之外用案例补充。

## 满额赠券

- 输入以人民币分表示金额，事件时刻有明确偏移。新客在支付时按注册时刻起不足 new_customer_days×24 小时，注册未来或缺失为无效输入。活动 [starts_at, ends_at) 内支付才可触发。退款及核销用于原订单状态转移，可以在活动结束后处理。
- 先验证序号唯一、正数、事件时间非递减。按 seq 执行。event_id 相同且其业务字段一致时仅记录 DUPLICATE，seq 属于交付位置。相同 ID 内容冲突使该案例结果标为需修正。订单已存在时，同金额和同叠加条件的支付只记重复，其他变化需要明确事件。以订单号为键，初始订单集合为空。初始次数和已占预算可为非零。
- 支付创建订单，记录净实付。按活动期、新客、门槛、叠加、单人次数、预算的顺序决定首个不满足原因。DENY_OTHER_APPLIED 时已有互斥优惠的订单被抑制。资格通过且剩余预算至少一张券时发放模拟券，次数 +1、预算 +coupon_fen。相等边界通过。发行和账本变化是仿真投影。
- 退款必须找到原订单，金额大于零且不超过当前净实付。更新净实付。KEEP 保持券和已用账本。RECOMPUTE_UNUSED 下已发行未核销且净实付低于阈值时撤回，次数 −1、预算 −coupon_fen。已核销时标 MANUAL_REVIEW，保留预算和已用次数并进入人工确认。已撤回券继续退款时账本保持，后续核销被拒绝。核销事件 amount_fen 为 0，且只允许 ISSUED 转 REDEEMED。
- 输出 Outcome 中订单按 order_id 升序，winner_ids 为空，used 与 budget_used_fen 为末态，manual_review 表示至少一笔订单待核。轨迹每事件一项。原因码固定为 ISSUED、OUTSIDE_ACTIVITY、NOT_NEW、BELOW_THRESHOLD、STACK_DENIED、CUSTOMER_LIMIT、BUDGET_EXHAUSTED、DUPLICATE_EVENT、DUPLICATE_ORDER、REFUND_RECORDED、REVOKED、USED_COUPON_REVIEW、REDEEMED、INVALID_EVENT。对单例无效输入返回 Issue 并禁止形成候选，批次保留其他合法行。

## 远程回拨

同一个 case 的输入属于同客户、同自然日和 remote 渠道。用于历史比较的 used 是本轮前已占用名额。对 ARRIVAL 按 at、seq 升序处理。对 APPOINTMENT_FIRST，先已预约组，再按各组 at、seq。名额直到 daily_cap，用尽显示 CAP_REACHED。保留按分配顺序的全部 winner_ids，合成样例首个获选即实际策略。事件序号与重复校验同上。所有事件业务日期必须等于 case.day。used 达到或超过上限时保留已用值，后续候选均被抑制。Outcome 的 coupons 为空、budget_used_fen=null、manual_review=false。

## 对照与验收

1. 历史 case 的 observed_original 和 observed_rule_id 均匹配本次原规则并有来源才计算 MATCH 或 DIFF。缺字段返回 MISSING。先比较整个 Outcome 投影，包括状态和预算。SIM-017 一致后才能形成 V2 验收案例。SIM-018 原结果有差异，需补证。SIM-019 已占满。
2. 合成 case 采用业务人员确认的候选预期。原规则观察状态为 NOT_REQUIRED。保存候选需要确认预期等于候选实际输出，且无输入错误或待人工状态。历史 case 还需原规则 MATCH。
3. RunCase.first_divergence_event_id 按原输入序号找第一条轨迹差异，比较 effect、code、账本和赢家归属，补充执行位置差异。摘要包含输入、规则、引擎语义版本和逻辑投影。
4. createCandidate 检查活动当前候选规则与 run 的 candidate_rule_id 一致。单版本运行用 baseline_rule_id。案例有更新的确认后继、或规则确认到新版本时标 STALE。旧运行可查询历史。
5. 预发以选择的 candidate_ids 逐项对照。缺观察为 MISSING，case_digest 或 rule_digest 不同为 VERSION_MISMATCH，输入引用失效为 STALE，值不同为 DIFF，完全一致为 MATCH。未知或重复观察拒绝整批。预发字段映射、证据批次和对照人可追溯。
6. 审阅记录当前预发摘要、操作者和说明。登记正式来源回执前再次校验全部一致、仍有效、来源和审阅齐备。回执是来源证据登记。改案生效后从同一范围选择下一统计期生成 review，回填改进项的观察及证据。

## 条款键与无效案例

满额赠券需要 new_customer、payment、time_window、stacking、budget_and_quota、refund 六项确认。远程回拨需要 same_day_scope、priority、daily_cap 三项确认。每个必需键状态 CONFIRMED，含已登记来源和业务说明。错误阻止确认，警告需要审核者在确认备注记录判断。确认前按 schema_version 1 验证。

案例的事件时间、序号和重复语义在确认时校验。运行对已确认且符合数据契约的案例再校验边界。某版本无法完成时该行的对应 Outcome 为 null，Issue 保留原因，运行返回 COMPLETED_WITH_ISSUES。原规则合法且候选非法时仍保留原规则结果与轨迹。

边界建议每项包含按当前版本计算出的 CaseInput 和待验证行为。取门槛相邻分值、起止边界与当前预算差，建议仍由业务人员确认预期。预发 verdict 记录导入当时的结果，后续规则变化由 eligible_for_receipt 显示当前可登记性。回执的 rule_digest 必须对应预发全部候选的同一已审摘要。
