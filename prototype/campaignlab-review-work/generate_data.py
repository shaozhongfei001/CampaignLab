import calendar
import json
from datetime import date
from pathlib import Path


WORK = Path(__file__).resolve().parent
OUT = WORK.parent / "campaignlab-review-deliverables"

branches = [
    {"id": "B01", "name": "东岚", "group": "东部组"},
    {"id": "B02", "name": "云川", "group": "东部组"},
    {"id": "B03", "name": "澄海", "group": "东部组"},
    {"id": "B04", "name": "临川", "group": "西部组"},
    {"id": "B05", "name": "青屿", "group": "西部组"},
]
channels = {
    "remote": "远程",
    "manager": "客户经理",
    "ai": "AI外呼",
    "wechat": "企业微信",
    "sms": "短信",
    "push": "手机银行推送",
}
strategies = [
    {"id": "S-101", "name": "预约回拨", "origin": "branch", "version": "V1"},
    {"id": "S-201", "name": "集中触达", "origin": "hq", "version": "V1"},
    {"id": "S-301", "name": "新客服务", "origin": "branch", "version": "V1"},
]
activities = [
    {"id": "AC-101", "name": "回访服务", "strategies": ["S-101"], "from": "2026-01", "to": "2026-11", "metricLabel": "预约任务数", "evidence": "模拟活动配置 AC-101"},
    {"id": "AC-201", "name": "新客欢迎", "strategies": ["S-301"], "from": "2026-01", "to": "2026-11", "metricLabel": "权益达标人数", "evidence": "模拟活动配置 AC-201"},
    {"id": "AC-202", "name": "支付达标", "strategies": []},
    {"id": "AC-203", "name": "证券入金", "strategies": []},
    {"id": "AC-204", "name": "资产提升", "strategies": []},
    {"id": "AC-205", "name": "分期关怀", "strategies": []},
    {"id": "AC-206", "name": "薪资客户福利", "strategies": []},
]
stage_keys = ["sent", "success", "executed", "contacted", "effective"]
value_keys = [
    "aum", "deposit", "wealth", "fund", "loan", "wealthSale", "nonCashWealthSale",
    "fundSale", "nonMoneyFundSale", "insuranceSale", "depositDemand", "depositTerm",
]
count_keys = ["eligible", *stage_keys, "capacity", "intentCount", "activityCount"]
dimension_keys = [
    "id", "period", "cutoff", "branch", "subbranch", "channel", "strategy", "origin",
    "segment", "tag", "cohort", "offset", "definition", "batch",
]
periods = ["2025-09", "2025-10", *[f"2026-{m:02}" for m in range(1, 12)]]
segments = ["大众", "富裕", "贵宾", "私行", "个贷"]
examples = [
    ("R01", "数值", "查10月东岚分行远程渠道有效触达率"),
    ("R02", "数值", "查询2026年9月东岚分行的AUM余额增量"),
    ("R03", "数值", "帮我查一下9月份各分行的下发成功率"),
    ("R04", "数值", "统计9月东部组有效接触客户数，按分行展示"),
    ("R05", "数值", "对比东岚和云川9月的存款增量、理财增量和基金增量"),
    ("R06", "数值", "展示9月各分行下发策略数、名单执行率和触达率"),
    ("R07", "数值", "帮我拉一下9月澄海、临川、青屿的有效触达率数据"),
    ("R08", "数值", "统计9月客户经理渠道下发客户数超过50万的分行有哪些"),
    ("R09", "数值", "查询9月下发成功率低于85%的分行及对应数据"),
    ("R10", "数值", "汇总9月各渠道的AUM增量，按贡献度从高到低排序"),
    ("R11", "数值", "对比东岚8月和9月的名单执行率变化"),
    ("R12", "数值", "展示各分行9月环比8月的存款增量波动情况"),
    ("R13", "数值", "查询东岚近两个月触达率的趋势变化"),
    ("R14", "异常", "10月东岚远程渠道触达率是否异常下降？"),
    ("R15", "异常", "9月东岚的名单执行率是否出现异常下降？"),
    ("R16", "异常", "检测9月各分行下发成功率有无异常波动"),
    ("R17", "异常", "帮我看看云川9月AUM增量是否存在异常"),
    ("R18", "异常", "东岚9月存款增量环比8月下降38%，这个波动是否异常？"),
    ("R19", "异常", "对比9月和8月，哪些分行的理财增量出现异常变化？"),
    ("R20", "异常", "检测各分行9月基金增量环比波动，标记异常点"),
    ("R21", "异常", "9月东岚客户经理渠道执行率35%，是否属于异常偏低？"),
    ("R22", "异常", "检测各分行手机银行渠道下发成功率，标记低于正常范围的异常值"),
    ("R23", "异常", "AI外呼渠道的有效触达率在各分行间是否存在异常差异？"),
    ("R24", "异常", "对东岚9月所有产能指标进行异常检测，列出异常项"),
    ("R25", "异常", "扫描9月数据，标记触达率、有效触达率、名单执行率的异常分行"),
    ("R26", "异常", "帮我检查9月各分行漏斗转化率，找出存在异常断点的环节"),
    ("R27", "归因", "解释10月东岚远程渠道有效触达客户数下降的原因"),
    ("R28", "归因", "东岚9月名单执行率从96%降至81%，帮我做归因分析"),
    ("R29", "归因", "东岚存款增量环比下降38%，主要是什么原因导致的？"),
    ("R30", "归因", "分析东岚AUM增量低于同组均值16亿的核心影响因素"),
    ("R31", "归因", "东岚有效触达率高于均值，帮我分析下原因"),
    ("R32", "归因", "东岚与云川的理财增量差距主要是哪些原因导致的"),
    ("R33", "归因", "东岚理财增量低于同组均值，是哪个客层拖累的？做归因分析"),
    ("R34", "归因", "对比东岚和同组均值，从渠道维度归因AUM增量差距"),
    ("R35", "归因", "东岚存款增量落后同组均值10.42亿，按存款类型拆解归因"),
    ("R36", "归因", "分析东岚已接触客户中，哪些客群对触达率提升贡献最大？"),
    ("R37", "归因", "归因东岚有效接触客户数低于均值的原因，按客户类型拆解"),
    ("R38", "组合", "查询东岚9月存款增量，并分析为什么低于同组均值"),
    ("R39", "组合", "帮我查9月各分行名单执行率，同时归因东岚排名靠后的原因"),
    ("R40", "组合", "统计9月客户经理渠道的AUM增量，并分析东岚贡献度偏低的原因"),
    ("R41", "归因", "东岚9月名单执行率异常下降，帮我分析原因"),
    ("R42", "归因", "检测到东岚存款增量环比大幅下滑，做归因分析"),
    ("R43", "归因", "东岚客户经理渠道执行率异常偏低，帮我拆解归因"),
    ("R44", "组合", "帮我看看东岚9月下发成功率86%是否异常，如果异常帮我归因"),
    ("R45", "组合", "判断东岚有效触达率7%在组内是否属于异常值，并分析原因"),
    ("R46", "组合", "东岚触达率32%高于同组均值，这个偏离是否异常？做归因分析"),
    ("R47", "报告", "生成东岚分行10月远程渠道复盘报告"),
    ("R48", "报告", "生成东岚分行2026年9月策略复盘报告"),
    ("R49", "报告", "帮我复盘本年度东岚分行的策略执行情况"),
    ("R50", "报告", "输出东岚分行9月产能诊断报告"),
    ("R51", "报告", "帮我复盘下策略：S-101"),
    ("R52", "报告", "复盘下上月针对大众客群的策略情况"),
    ("R53", "报告", "复盘上2026年9月远程渠道策略整体的执行情况"),
    ("R54", "报告", "生成9月客户经理渠道专项分析报告，对比各分行执行效率"),
    ("R55", "报告", "帮我写一份9月存款增量专题报告，分析各分行存款变化趋势及归因"),
    ("R56", "报告", "输出9月AI外呼与远程渠道效能对比报告，评估渠道策略优化方向"),
    ("Q01", "口径", "不同渠道的有效触达客户数统计口径是什么？"),
    ("Q02", "口径", "有效触达率的分母是什么？"),
    ("Q03", "澄清", "上个月触达怎样？"),
    ("Q04", "澄清", "帮我复盘下策略：XXX"),
]


def exact_funnel(period, branch, channel):
    if branch == "B01" and channel == "remote":
        return {
            "2026-08": (9800, 9408, 8080, 4040, 2020),
            "2026-09": (10000, 9600, 7680, 3840, 1920),
            "2026-10": (12000, 11520, 8640, 3456, 1728),
            "2026-11": (12000, 11520, 8640, 3888, 1944),
        }.get(period)
    if branch == "B05" and channel == "ai" and period == "2026-10":
        return (1800, 0, 0, 0, 0)
    return None


def make_funnel(period, i, j, branch, channel):
    known = exact_funnel(period, branch, channel)
    if known is not None:
        return known
    month = int(period[-2:])
    sent = (552000 if channel == "manager" and i < 2 else 2400 + 360 * i + 230 * j) + month * (i + 1) * 80
    success_pct = 82 if branch == "B05" and period == "2026-09" else 88 + ((i + j + month) % 9)
    executed_pct = 35 if branch == "B01" and channel == "manager" and period == "2026-09" else 62 + (i * 3 + j + month) % 22
    success = sent * success_pct // 100
    executed = success * executed_pct // 100
    contacted = executed * (42 + (i + 2 * j + month) % 16) // 100
    effective = contacted * (42 + (3 * i + j + month) % 15) // 100
    return sent, success, executed, contacted, effective


def values(effective, period, i, j):
    amount = (i + 2) * 35000 + effective * (120 + 17 * j) + int(period[-2:]) * 9100
    if i == 0 and j == 0 and period == "2026-10":
        amount = -1358000
    if effective == 0:
        amount = 0
    deposit = amount * 54 // 100
    wealth = amount * 28 // 100
    fund = amount * 15 // 100
    deposit_demand = deposit * 44 // 100
    return dict(zip(value_keys, [
        amount, deposit, wealth, fund, amount - deposit - wealth - fund,
        effective * 132, effective * 89, effective * 72, effective * 43,
        effective * 31, deposit_demand, deposit - deposit_demand,
    ]))


def source_facts():
    records = []
    for period in periods:
        year, month = map(int, period.split("-"))
        cutoff = date(year, month, calendar.monthrange(year, month)[1]).isoformat()
        for i, branch in enumerate(branches):
            for j, channel in enumerate(channels):
                if channel == "wechat" and period in ("2026-08", "2026-09"):
                    continue
                total = make_funnel(period, i, j, branch["id"], channel)
                parts = [("S-101", "大众", 2), ("S-201", "富裕", 1), ("S-101", "贵宾", 1)] if channel == "remote" else [
                    (["S-301", "S-201", "S-101"][j % 3], segments[(i + j) % 5], 4)
                ]
                if branch["id"] == "B01" and channel == "remote" and period == "2026-10":
                    parts = [("S-101", "大众", 1), ("S-201", "富裕", 1), ("S-101", "贵宾", 2)]
                rem = list(total)
                for k, (strategy, segment, share) in enumerate(parts):
                    nums = rem if k == len(parts) - 1 else [n * share // 4 for n in total]
                    rem = [a - b for a, b in zip(rem, nums)]
                    subbranch = branch["name"] + ("一支行" if segment in ("大众", "贵宾") else "二支行")
                    cohort = f"{branch['id']}:{segment}"
                    records.append({
                        "id": f"{period}:{branch['id']}:{channel}:{k+1}",
                        "period": period, "cutoff": cutoff, "branch": branch["id"], "subbranch": subbranch,
                        "channel": channel, "strategy": strategy, "origin": "hq" if strategy == "S-201" else "branch",
                        "segment": segment, "tag": ("富裕" if segment == "大众" and channel == "remote" else segment),
                        "cohort": cohort, "offset": 0,
                        "definition": "D-2026.1", "batch": "SNAP-" + period,
                        "eligible": nums[0] * 5 // 4 + 250,
                        **dict(zip(stage_keys, nums)),
                        "capacity": nums[2] * 10 // 9 if nums[2] else 0,
                        "intentCount": nums[4] // 3,
                        "activityCount": nums[4] // 2,
                        **values(nums[-1], period, i, j),
                    })
    return records


def dataset(bank_id, facts):
    wide = bank_id == "A"
    chinese_dims = [
        "记录号", "统计月", "数据截止", "分行号", "支行", "投放渠道", "策略号", "策略来源",
        "部署客群", "月末标签", "客户集合", "集合起点", "触达口径版本", "来源批次",
    ]
    chinese_counts = ["可经营", "下发", "接收", "执行", "接触", "有效", "容量", "意向次数", "活动特色"]
    cn_values = ["AUM变动", "存款变动", "理财变动", "基金变动", "个贷变动", "理财销量", "非现管理财销量", "基金销量", "非货基销量", "保险销量", "活期变动", "定期变动"]
    dims = dict(zip(dimension_keys, chinese_dims if wide else ["slice_id", "month_id", "as_at", "org", "unit_name", "route", "plan", "issuer", "cohort_at_launch", "tag_at_close", "population_id", "start_idx", "definition_id", "snapshot"]))
    count_map = dict(zip(count_keys, chinese_counts if wide else [f"M{i+1:02}" for i in range(len(count_keys))]))
    money_map = dict(zip(value_keys, cn_values if wide else [f"amount_{i+1:02}_fen" for i in range(len(value_keys))]))
    codebook = {
        "channel": {(n if wide else f"C{i+1:02}"): k for i, (k, n) in enumerate(channels.items())},
        "origin": {"分行" if wide else "L": "branch", "总行" if wide else "H": "hq"},
    }
    reverse = {name: {v: k for k, v in codes.items()} for name, codes in codebook.items()}
    amounts = list(money_map.values())
    entity_table = "月度宽表" if wide else "统计切片"
    counts_table = entity_table if wide else "阶段人数长表"
    long_columns = {"id": "切片键", "metric": "指标码", "value": "计数"}
    columns = [*dims.values(), *(count_map.values() if wide else []), *amounts]
    rows, tall_rows = [], []
    for record in facts:
        source = dict(record)
        for name, codes in reverse.items():
            source[name] = codes[source[name]]
        if not wide and record["channel"] == "push":
            source["definition"] = "D-B-PUSH.2"
        row = [source[k] for k in dimension_keys]
        if wide:
            row.extend(source[k] for k in count_keys)
        else:
            tall_rows.extend([record["id"], count_map[k], source[k]] for k in count_keys)
        row.extend(source[k] * (1 if wide else 100) for k in value_keys)
        rows.append(row)
    tables = {entity_table: {"columns": columns, "rows": rows}}
    if not wide:
        tables[counts_table] = {"columns": list(long_columns.values()), "rows": tall_rows}
    return {
        "schemaVersion": 1,
        "synthetic": True,
        "bankId": bank_id,
        "bankName": "甲行（模拟）" if wide else "乙行（模拟）",
        "snapshotVersion": f"{bank_id}-001",
        "description": "虚构客户集合与策略，统计区间为模拟月结。集合区间仅用于复现合成客户去重。",
        "mapping": {
            "version": f"MAP-{bank_id}-1", "layout": "wide" if wide else "long",
            "entityTable": entity_table, "countsTable": counts_table, "dimensions": dims,
            "countFields": count_map, "moneyFields": money_map, "moneyDivisor": 1 if wide else 100,
            "longColumns": long_columns, "codes": codebook,
        },
        "tables": tables,
        "metadata": {
            "branches": branches, "channels": channels, "strategies": strategies, "activities": activities,
            "periods": periods, "defaultScope": {"period": "2026-10", "branch": "B01", "channel": "remote"},
            "coverageEvents": [{"period": "2026-08", "channel": "wechat", "status": "未纳入采集"}, {"period": "2026-09", "channel": "wechat", "status": "未纳入采集"}, {"period": "2026-10", "channel": "wechat", "status": "恢复采集"}],
            "pushDetailSeconds": 0 if wide else 3,
            "thresholds": {"mom": 10, "peer": 20, "own": 1, "layer": 15, "mix": 5},
            "goals": {"cover": 0.75, "execution": 0.8, "reach": 0.35, "effectiveRate": 0.2, "effective": 2000, "aum": 1000000},
            "sources": ["模拟策略看板导出", "模拟渠道执行导出", "模拟产能归属导出"],
            "linkPolicy": {
                "version": "LINK-1",
                "routeWindows": {"remote": [0, 7], "push": [30, 60]},
                "dispatchDays": {"remote": [0, 10], "push": [0]},
                "notes": "模拟配置采用结果日减触达日，包含两端；下发日减触达日按所列值匹配。",
            },
            "linkEvidence": {
                "touches": [
                    {"id": "T-01", "customer": "SIM-C01", "strategy": "S-101", "node": "N-01", "batch": "EV-10", "channel": "remote", "dispatchDate": "2026-10-10", "at": "2026-10-10"},
                    {"id": "T-02", "customer": "SIM-C01", "strategy": "S-201", "node": "N-02", "batch": "EV-10", "channel": "remote", "dispatchDate": "2026-10-22", "at": "2026-10-12"},
                    {"id": "T-03", "customer": "SIM-C02", "strategy": "S-301", "node": "N-01", "batch": "EV-09", "channel": "push", "dispatchDate": "2026-09-10", "at": "2026-09-10"},
                    {"id": "T-04", "customer": "SIM-C04", "strategy": "S-101", "node": "N-02", "batch": "EV-10", "channel": "remote", "dispatchDate": "2026-10-10", "at": "2026-10-09"},
                ],
                "outcomes": [
                    {"id": "O-01", "customer": "SIM-C01", "date": "2026-10-17", "amount": 1200},
                    {"id": "O-02", "customer": "SIM-C02", "date": "2026-11-09", "amount": 720},
                    {"id": "O-03", "customer": "SIM-C03", "date": "2026-10-17", "amount": 430},
                    {"id": "O-04", "customer": "SIM-C04", "date": "2026-10-10", "amount": 210},
                ],
            },
            "replayCases": [
                {"id": "SIM-017", "period": "2026-10", "day": "2026-10-20", "customer": "SIM-U17", "branch": "B01", "channel": "remote", "activity": "AC-101", "version": "V1", "used": 0, "cap": 1, "observedWinner": "S-201", "source": "执行样本 EXEC-17",
                 "events": [{"strategy": "S-201", "time": "09:30", "appointment": False}, {"strategy": "S-101", "time": "11:00", "appointment": True}]},
                {"id": "SIM-018", "period": "2026-10", "day": "2026-10-21", "customer": "SIM-U18", "branch": "B01", "channel": "remote", "activity": "AC-101", "version": "V1", "used": 0, "cap": 1, "observedWinner": "S-101", "source": "执行样本 EXEC-18",
                 "events": [{"strategy": "S-201", "time": "09:45", "appointment": False}, {"strategy": "S-101", "time": "11:30", "appointment": True}]},
                {"id": "SIM-019", "period": "2026-10", "day": "2026-10-22", "customer": "SIM-U19", "branch": "B01", "channel": "remote", "activity": "AC-101", "version": "V1", "used": 1, "cap": 1, "observedWinner": None, "source": "执行样本 EXEC-19",
                 "events": [{"strategy": "S-201", "time": "09:15", "appointment": False}, {"strategy": "S-101", "time": "10:00", "appointment": True}]},
            ],
            "preflight": {"activity": "AC-101", "version": "V2", "source": "模拟预发验收 PRE-101", "winners": {"SIM-017": "S-101", "SIM-018": "S-101", "SIM-019": None}},
        },
    }


def main():
    OUT.mkdir(exist_ok=True)
    facts = source_facts()
    for name in ("A", "B"):
        path = OUT / f"CampaignLab-Simulated-Bank-{name}.json"
        path.write_text(json.dumps(dataset(name, facts), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"{path.name} {len(facts)} slices {path.stat().st_size} bytes")
    (WORK / "questions.json").write_text(json.dumps(examples, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
