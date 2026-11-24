# -*- coding: utf-8 -*-
import zipfile, os
D = "/mnt/c/Users/szf/AppData/Local/Temp/fe-scratch/mock/"
SH = D + "shots/"
OUT = D + "营销策略复盘CampaignLab-AI-Review-User-Manual.docx"
CW = 5731510; CH = 3582194
TW = 9026

FIGS = [
 ("demo-a1.png",  "打开演示后进入今日复盘（A1），左侧为十个界面，顶栏为语义层与操作者状态"),
 ("demo-a2.png",  "复盘对话（A2）：会话流、四段回答与 Artifact 卡片；右侧嵌入画布预览本问分析"),
 ("demo-x1.png",  "查询计划抽屉：语义解析到分析解释的六步受控链路及耗时"),
 ("demo-a3.png",  "归因画布（A3）：瀑布、因子卡与渠道／客群下钻"),
 ("demo-a4.png",  "复盘报告（A4）：大纲、四类结构化内容、版本与签认"),
 ("demo-x2.png",  "证据抽屉：证据链、生成 SQL 节选与回放时间线"),
 ("demo-a5.png",  "指标语义层（A5）：指标对象、本体关系与版本治理"),
 ("demo-a6.png",  "分析技能库（A6）：技能卡、触发条件与运行状态"),
 ("demo-a7.png",  "经验沉淀（A7）：六步沉淀流程、资产库与本次命中"),
 ("demo-a8.png",  "运行与作业（A8）：运行记录、调度队列与失败恢复"),
 ("demo-a9.png",  "证据与审计（A9）：证据台账、审计时间线与导出"),
 ("demo-a10.png", "改进项（A10）：状态卡、登记分派与下期复核证据"),
]

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

B = []
def raw(x): B.append(x)

def rpr(b=False, sz=None, color=None, style=None):
    x = "<w:rPr>"
    if style: x += '<w:rStyle w:val="%s"/>' % style
    if b: x += "<w:b/>"
    if color: x += '<w:color w:val="%s"/>' % color
    if sz: x += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (sz, sz)
    return x + "</w:rPr>"

def P(text, style=None, b=False, sz=None, jc=None, before=None, after=None, color=None):
    pp = "<w:pPr>"
    if style: pp += '<w:pStyle w:val="%s"/>' % style
    if before is not None or after is not None:
        pp += '<w:spacing w:before="%d" w:after="%d"/>' % (before or 0, after or 0)
    if jc: pp += '<w:jc w:val="%s"/>' % jc
    pp += "</w:pPr>"
    return "<w:p>%s<w:r>%s<w:t xml:space=\"preserve\">%s</w:t></w:r></w:p>" % (pp, rpr(b, sz, color), esc(text))

def PRUN(xml_runs, style=None, jc=None, ind=None, tabs=False, before=None, after=None):
    pp = "<w:pPr>"
    if style: pp += '<w:pStyle w:val="%s"/>' % style
    if tabs: pp += '<w:tabs><w:tab w:val="left" w:pos="%d"/></w:tabs>' % ind[1]
    if before is not None or after is not None:
        pp += '<w:spacing w:before="%d" w:after="%d"/>' % (before or 0, after or 0)
    if ind: pp += '<w:ind w:left="%d" w:hanging="%d"/>' % ind
    if jc: pp += '<w:jc w:val="%s"/>' % jc
    pp += "</w:pPr>"
    return "<w:p>%s%s</w:p>" % (pp, xml_runs)

def R(text, b=False, sz=None, color=None, style=None):
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr(b, sz, color, style), esc(text))

def STEP(n, text):
    return raw(PRUN(R("%d." % n) + "<w:r><w:tab/></w:r>" + R(text), ind=(560, 360), tabs=True, after=40))

def CAP(n, text):
    return P("图 %02d  %s" % (n, text), style="Caption")

def IMG(i):
    rid = i + 2
    return ('<w:p><w:pPr><w:spacing w:before="120" w:after="60"/><w:jc w:val="center"/></w:pPr>'
      '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
      '<wp:extent cx="%d" cy="%d"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
      '<wp:docPr id="%d" name="Picture %d"/><wp:cNvGraphicFramePr>'
      '<a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
      '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
      '<pic:pic><pic:nvPicPr><pic:cNvPr id="%d" name="image%d.png"/><pic:cNvPicPr/></pic:nvPicPr>'
      '<pic:blipFill><a:blip r:embed="rId%d"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
      '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
      '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
      '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>') % (CW, CH, i + 1, i + 1, i + 1, i + 1, rid, CW, CH)

def FIG(i):
    raw(IMG(i)); raw(CAP(i + 1, FIGS[i][1]))

BM = [100]
def H(level, text, bm=None):
    inner = ""
    if bm:
        BM[0] += 1
        inner += '<w:bookmarkStart w:id="%d" w:name="%s"/>' % (BM[0], bm)
    inner += R(text)
    if bm:
        inner += '<w:bookmarkEnd w:id="%d"/>' % BM[0]
    return raw('<w:p><w:pPr><w:pStyle w:val="Heading%d"/></w:pPr>%s</w:p>' % (level, inner))

def PB():
    raw('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

def LINK(anchor, text):
    return '<w:hyperlink w:anchor="%s" w:history="1">%s</w:hyperlink>' % (anchor, R(text, style="Hyperlink"))

def CELL(paras, shade=None, w=None):
    tc = "<w:tc><w:tcPr>"
    if w: tc += '<w:tcW w:w="%d" w:type="dxa"/>' % w
    if shade: tc += '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade
    tc += "</w:tcPr>"
    return tc + "".join(paras) + "</w:tc>"

def CP(text, b=False):
    return P(text, style="TableText", b=b)

def TBL(widths, rows):
    x = '<w:tbl><w:tblPr><w:tblStyle w:val="Tbl"/><w:tblW w:w="%d" w:type="dxa"/><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>' % TW
    for w in widths: x += '<w:gridCol w:w="%d"/>' % w
    x += "</w:tblGrid>"
    for ri, row in enumerate(rows):
        x += "<w:tr>"
        if ri == 0: x += "<w:trPr><w:tblHeader/></w:trPr>"
        for ci, c in enumerate(row):
            shade = "EAF1FB" if ri == 0 else None
            if isinstance(c, list): x += CELL(c, shade, widths[ci])
            else: x += CELL([CP(c, b=(ri == 0))], shade, widths[ci])
        x += "</w:tr>"
    x += "</w:tbl>"
    raw(x); raw(P("", after=120))

def RESULT(text):
    raw(PRUN(R("结果怎么看", b=True) + R("  " + text), before=80, after=160))

def DUTY(text):
    raw(PRUN(R(text), before=40, after=80))

# ---------------- cover ----------------
raw(P("CampaignLab", style="Title"))
raw(P("营销策略复盘操作手册", style="Title"))
raw(P("AI 对话版 · 演示版 v0.2  ·  2026 年 11 月", style="Subtitle"))
raw(P("ChatGPT 式复盘工作台：洞察 → 追问 → 归因 → 报告 → 改进 → 证据", style="Subtitle"))
PB()

# ---------------- front matter ----------------
FIG(0)
H(1, "首次打开")
raw(P("在 Chrome 或 Edge 中打开 demo-system.html（位于仓库 web/docs/redesign-ai/demo/ 目录）。单文件静态演示，无需安装、无需联网；页面自带合成数据，打开即可操作。左侧导航 01–10 切换十个界面，每个界面保留对话入口与证据入口。"))
H(1, "默认演示范围")
TBL([2200, 6826], [
 ["范围项", "默认值"],
 ["期间", "2026 年 10 月（对比 9 月）"],
 ["机构", "全行（重点分行：华东）"],
 ["口径", "M_REACH_RATE v3 · 阈值 THR-07"],
 ["快照", "snap-20261031（10-31 23:59 锁定，只读）"],
 ["操作者", "张三 A-0001"],
])
raw(P("打开后的预期结果", b=True, before=60))
raw(P("有效触达 1,728 人，较基准 1,920 人少 192 人（−10.0%）；有效触达率 15.0%，基准 16.8%（−1.8pp），低于阈值 16.5%，触发规则 THR-07。全部界面共用这一组数字。"))
H(1, "从哪里开始")
raw(P("先在顶栏确认「语义层就绪 · 指标对象 128」与操作者。第 1 章沿同一案例走完洞察、追问、归因与报告；第 2 章核对口径、技能与经验三类资产；第 3 章查看运行、证据与改进的治理闭环。图中编号与记录是演示数据，可按操作步骤复现。Word 导航窗格可按功能标题查阅。"))
H(1, "按任务查阅")
TBL([2600, 5026, 1400], [
 ["章节", "在这里完成的事", "图号"],
 [[LINK("chapter_1", "1  智能复盘（A1–A4）")], "读今日洞察，在对话中追问，沿归因画布拆解，固化为可签认报告。", "图 01–06"],
 [[LINK("chapter_2", "2  分析资产（A5–A7）")], "核对指标语义与口径版本，复用分析技能，把报告经验沉淀为组织资产。", "图 07–09"],
 [[LINK("chapter_3", "3  执行与治理（A8–A10）")], "查看智能体运行与失败恢复，回放证据与审计，登记并验证改进项。", "图 10–12"],
 [[LINK("walkthrough", "附录 A  串讲路线")], "按同一案例从发现异常走到下期复核。", "—"],
 [[LINK("reference", "附录 B  口径与状态")], "查指标计算、阈值与界面状态的处置。", "—"],
])
H(1, "常用角色")
raw(P("分行运营先读第 1 章与 3.3 改进项。指标负责人重点核对 2.1 语义层、1.3 查询计划与附录 B。渠道与活动运营沿 1.5 报告建议与 3.3 改进项验收动作。复核与审计人员从 3.2 证据与审计入口回放全链路并导出证据包。"))
H(1, "演示记录如何保留")
raw(P("静态演示不写服务端：对话追问、抽屉、签认态仅保存在当前浏览器会话（内存态），刷新即回到初始合成数据。需要留存时请用浏览器截图，或在 04 复盘报告点「发布」导出报告快照。换浏览器或设备时重新打开 demo-system.html 即可。"))
PB()# ---------------- chapter 1 ----------------
H(1, "1  智能复盘 · 从洞察到报告", "chapter_1")
DUTY("每天 06:00 日复盘自动生成结论；运营从「读报表」变为「读洞察、追问、签认」。本章覆盖 A1–A4 四个界面。")

H(2, "1.1  今日复盘：今天必须看的三件事", "function_1_1")
DUTY("把当日全部运行结果压缩为三张洞察卡，并给出追问与归因的下一步入口。")
raw(P("界面见图 01。左侧导航 01–10 对应十个界面；顶栏显示语义层状态、操作者与当前时间。"))
STEP(1, "打开演示默认落在「01 今日复盘」。先读三张洞察卡：触达缺口、阈值触发、结构变化；每张卡带证据编号与置信度。")
STEP(2, "点洞察卡上的「追问」进入复盘对话（1.2），或点「看归因」进入归因画布（1.4）。")
STEP(3, "顶栏「语义层就绪 · 指标对象 128」为绿灯时表示可取数；变红时到「08 运行与作业」查看失败运行。")
RESULT("洞察卡数字与对话、画布、报告完全一致：有效触达 1,728、基准 1,920、差 −192（−10.0%）。任一界面改口径，四处同步变化。")

H(2, "1.2  复盘对话：一句话问出完整归因", "function_1_2")
DUTY("ChatGPT 式主工作界面；回答按「结论 → 依据 → 置信」组织，并挂接运行号与证据；对话产出的分析 Artifact 在右侧嵌入画布即时预览，问什么就嵌入什么。")
FIG(1)
STEP(1, "在底部对话条输入问题，或点建议问句（如「只看华东分行」「拆到支行层级」「生成 10 月复盘报告」）。上下文芯片固定为 期间 2026-10 · 机构 全行 · 口径 v3 · 快照 snap-20261031。")
STEP(2, "读回答四段：指标判断（发生了什么）、结构拆解（在哪些维度）、归因分析（谁导致变化）、决策建议（回到业务动作）。段内数字角标即证据引用。")
STEP(3, "点受控链路条上的「轨迹 ▾」打开查询计划抽屉（1.3），核对六步链路与耗时；点建议问句可继续追问。")
RESULT("每条回答标注命中指标对象数与校验 PASS；轨迹显示 RUN-1121-03、耗时 12s。系统执行的是「分析计划」而非自由写 SQL，非法本体组合在规划期即被拦截。画布嵌入本问产出的分析 Artifact（artifact://ATTR-202610-01）：瀑布／渠道／客群三图与回答同构，点「插入报告 §3」回流至 1.5。")

H(2, "1.3  查询计划抽屉：核对 AI 的取数链路", "function_1_3")
DUTY("把一次回答的受控链路展开为六步，供指标负责人逐歩复核。")
FIG(2)
STEP(1, "在对话的受控链路条点「轨迹 ▾」，抽屉从右侧滑出；点「关闭」或 Esc 返回。")
STEP(2, "依次核对六步：语义解析命中指标=有效触达率；查询规划给出趋势／结构／归因三个有序任务；指标映射命中 M_REACH_RATE v3；SQL 生成 3 条；结果校验口径一致、可比子集 98.2%；分析解释输出四段+画布。")
STEP(3, "点「在画布中回放」跳到归因画布（1.4），把同一条链路放到瀑布图上对照。")
RESULT("每步右上角为耗时，全绿表示链路受控。出现黄色提示（如可比子集 98.2%）时结论标「部分可比」，不得直接签认。")

H(2, "1.4  归因画布：把 −1.8pp 拆到可执行因子", "function_1_4")
DUTY("用瀑布、因子卡与下钻条回答「谁导致变化」，并显示被语义层否决的归因路径。")
FIG(3)
STEP(1, "读瀑布：基准 16.8% 经四个因子落到 15.0%；因子按贡献绝对值排序，余量项闭合差值。")
STEP(2, "点因子卡下钻：名单执行率 78%→71%（−0.8pp／44%）、客群结构（−0.6pp／33%）、渠道覆盖（−0.5pp／28%）、余量 +0.1pp／−5%；右侧条形图给渠道与客群切片（企微 −96、短信 −52、外呼 −31、App +14）。")
STEP(3, "查看红色虚线的「禁止边」：语义层不允许的归因路径（如用月末标签解释部署期变化）会被否决并给出理由。")
RESULT("四因子贡献合计恰为 −1.8pp，闭合校验通过；不可比切片标「部分可比」而非给数。")

H(2, "1.5  复盘报告：报告即分析入口", "function_1_5")
DUTY("把对话产物固化为四类结构化内容（指标／结论／归因／建议），可签认、可回流、可沉淀。")
FIG(4)
STEP(1, "左栏大纲跳转摘要、指标、结论、归因、建议、附录·证据；正文每段保留证据角标与「AI 贡献拆解」标记。")
STEP(2, "点段末◆或角标打开证据抽屉（1.6）核对该段来源；点「沉淀为分析资产」把段落送入经验沉淀（2.3）。")
STEP(3, "左栏「版本与签认」查看 v3 生成、指标负责人复核、分行签认进度；齐套后签认锁定版本，点「发布」导出。")
RESULT("未签认段落标 PENDING_REVIEW；签认后版本冻结，重算只能生成新版本。报告数字与 A1／A2／A4 完全一致。")

H(2, "1.6  证据抽屉：任一数字可回放", "function_1_6")
DUTY("展示单个结论的证据链：快照 → 口径 → 阈值 → 查询计划 → SQL → 校验。")
FIG(5)
STEP(1, "从报告段末◆、对话角标或卡片「查看证据」打开；标题显示证据号（如 EVD-1031-01）与 PASS。")
STEP(2, "核对证据链芯片：snap-20261031、M_REACH_RATE v3、THR-07；查看生成 SQL 节选与回放时间线（校验通过 09:14）。")
STEP(3, "点「复制编号」把证据号带入沟通或改进项；点「关闭」、遮罩或 Esc 退出。")
RESULT("抽屉只列可回放来源；缺快照或缺口径的结论不会出现在报告正文。")
PB()

# ---------------- chapter 2 ----------------
H(1, "2  分析资产 · 让经验可复用", "chapter_2")
DUTY("口径、技能与经验三类资产是 AI 复盘的「长期记忆」，全部带人工确认闸口。本章覆盖 A5–A7。")

H(2, "2.1  指标语义层：指标对象是唯一事实源", "function_2_1")
DUTY("维护 128 个指标对象的定义、分母、切片键、版本与禁止边；AI 取数前先查这里。")
FIG(6)
STEP(1, "搜索 M_REACH_RATE 查看定义、分子分母、切片键、生效版本与历史变更。")
STEP(2, "在本体图查看依赖与禁止边；被否决的组合显示红虚线与理由，避免错误归因进入报告。")
STEP(3, "口径变更走「发布 v4」：登记变更理由、影响面与回归结果；发布后旧版本仍可读、可回放。")
RESULT("每个指标对象带 owner 与生效日；A1–A4 的任一数字都能回溯到此处版本。")

H(2, "2.2  分析技能库：把常用分析路径封装为技能", "function_2_2")
DUTY("技能（SK-01…04）= 触发条件 + 有序步骤 + 产物约定，对话中可一键调用。")
FIG(7)
STEP(1, "浏览技能卡：适用问题、输入口径、步骤、产物与最近运行状态。")
STEP(2, "点「在对话中运行」跳转复盘对话并预填上下文；运行记录挂 RUN-1121-0x，可回 3.1 查看。")
STEP(3, "新建技能需登记输入／输出、口径依赖与失败回退；未登记技能不出现在建议问句。")
RESULT("失败技能标 FAILED，可到 3.1 重试或断点恢复；技能产物与手工分析同口径、同证据链。")

H(2, "2.3  经验沉淀：报告经验变组织资产", "function_2_3")
DUTY("从签认报告抽取判断路径、口径约定、重算条件等知识（KNW-041…044），人工确认后入库。")
FIG(8)
STEP(1, "查看六步沉淀流程当前停在「人工确认」：报告生成 → 结构化抽取 → 人工确认 → 入库检索 → 复用学习 → 版本演进；未确认不生效。")
STEP(2, "在分析资产库核对来源报告、复用次数与状态；PENDING_REVIEW 资产不会被 AI 引用。")
STEP(3, "右侧「本次复盘命中」点「引用」把历史结论插入对话，并显示置信度（如 KNW-041 高、KNW-043 中）。")
RESULT("资产被推翻时留痕并生成新版本；复用次数反映组织采纳度。")
PB()

# ---------------- chapter 3 ----------------
H(1, "3  执行与治理 · 可回放可审计", "chapter_3")
DUTY("智能体的每一次运行、每一份证据、每一个改进动作都留痕：可重试、可审计、可验证。本章覆盖 A8–A10。")

H(2, "3.1  运行与作业：智能体调度看板", "function_3_1")
DUTY("查看运行记录、调度队列与失败恢复，保证「AI 干活」的过程可控。")
FIG(9)
STEP(1, "读四张 KPI：今日运行 14（成功 12 · 运行中 1 · 失败 1）、平均耗时 38s、队列等待 2、失败待恢复 1。")
STEP(2, "在运行记录定位 RUN-1121-07（报告导出 · FAILED），查看触发方式、耗时与产物列。")
STEP(3, "右侧失败恢复区选「重试」「从断点恢复」或「放弃」；调度队列显示等待原因（如等待企微覆盖回流）。")
RESULT("快照锁冲突中断不会重复计费或重复写回执；断点恢复保留中间产物，重跑只补失败步。")

H(2, "3.2  证据与审计：全链路可回放", "function_3_2")
DUTY("证据台账 + 审计时间线 + 导出，供内部复核与外部审计。")
FIG(10)
STEP(1, "按证据号查类型（数据快照／口径版本／阈值版本／查询计划／生成 SQL／签认记录）、来源与被引用于。")
STEP(2, "沿审计时间线核对：快照锁定 10-31 23:59 → 日复盘生成 06:00 → 追问归因 09:14 → 口径复核签认 09:40 → 分行签认（待，2 个分行未签）。")
STEP(3, "点「导出证据包」打包快照引用、口径版本、查询计划与 SQL；「取数清单」「审计日志」分别导出。")
RESULT("任一证据可回放到当时快照与口径；黄色节点表示仍有分行未签认，报告保持 PENDING_REVIEW。")

H(2, "3.3  改进项：可分派、可验证的闭环", "function_3_3")
DUTY("把归因结论登记为动作，明确责任、期限与验证方式，下期自动复核。")
FIG(11)
STEP(1, "读四张状态卡：待签认 2、执行中 3、下期待复核 2、已闭环 9（近 90 日）。")
STEP(2, "在「登记改进项」手工填写，或点「从结论带入」由 A2／A4 结论一键生成责任、期限与验证方式。")
STEP(3, "右栏「下期复核证据」查看自动挂接：ACT-2026-112 打开率 +1.4pp 达显著已闭环；ACT-2026-116 等待 RUN-1121-06 重算结果。")
RESULT("未签认不得提交执行；验证方式必须可量化（如下期执行率回升 ≥78%、可比子集 ≥95%）。")
PB()# ---------------- appendix A ----------------
H(1, "附录 A  串讲路线", "walkthrough")
DUTY("用 2026-10 触达缺口案例，按下面顺序十分钟讲完全链路；每一步都可在演示中点击复现。")
TBL([1500, 2400, 5126], [
 ["步骤", "界面", "看点"],
 ["1  发现异常", "01 今日复盘", "触达率 15.0% 低于阈值 16.5%，缺口 −192 人；点「追问」进入对话。"],
 ["2  对话追问", "02 复盘对话", "「华东为什么差」→ 四段回答 + Artifact 卡片 + 右侧嵌入画布（图 02、图 03）。"],
 ["3  归因拆解", "03 归因画布", "瀑布 −1.8pp 四因子闭合；禁止边被语义层否决（图 04）。"],
 ["4  固化报告", "04 复盘报告", "结论与归因块入报告；签认 v3 锁定版本（图 05、图 06）。"],
 ["5  转成动作", "10 改进项", "ACT-2026-118／119 登记并分派；验证方式可量化（图 12）。"],
 ["6  留存证据", "09 证据与审计", "EVD-1031-01…06 全链路回放；导出证据包（图 11）。"],
 ["7  沉淀复用", "07 经验沉淀", "KNW-044 待确认；下期复盘自动命中并显示置信（图 09）。"],
])
raw(P("汇报时可核对的三组证据：本期事实用快照与口径复核；归因用查询计划与生成 SQL 复核；下期表现用同范围新一期数据与改进项验证方式复核。需要确认策略净增量时，再补分组、观察期与结果证据。"))

# ---------------- appendix B ----------------
H(1, "附录 B  口径与状态", "reference")
H(2, "B.1  默认案例的指标口径")
TBL([2400, 4226, 2400], [
 ["指标", "计算", "2026 年 10 月"],
 ["有效触达客户数", "名单内完成有效接触的去重客户", "1,728（基准 1,920）"],
 ["有效触达率", "有效触达客户数 ÷ 下发成功客户数", "15.0%（基准 16.8%，−1.8pp）"],
 ["阈值 THR-07", "触达率低于 16.5% 或降幅 >1.5pp 触发复盘", "触发"],
 ["名单执行率", "已执行客户数 ÷ 下发成功客户数", "71%（基准 78%，−7pp）"],
 ["归因贡献", "因子对 −1.8pp 的依次替换分解", "44%／33%／28%／−5%"],
 ["可比子集", "两期共同可比客户集合占比", "98.2%"],
])
H(2, "B.2  看到提示后怎么处理")
TBL([2600, 6426], [
 ["界面状态", "含义与处置"],
 ["语义层就绪（绿）", "指标对象 128 已加载，可取数；变红先到 08 运行与作业查失败运行。"],
 ["WARN（黄）", "指标判断存在缺口或迟到数据；结论需注明范围后再引用。"],
 ["部分可比", "可比子集不足；缩小范围或补齐同口径覆盖后再签认。"],
 ["REVIEW（黄）", "运行或资产待人工复核；不进入报告正文。"],
 ["FAILED（红）", "运行中断；到 08 重试或从断点恢复，不重复计费、不重复写回执。"],
 ["PENDING_REVIEW", "资产或改进项待签认；AI 不引用未确认资产。"],
 ["已签认 v3", "报告版本冻结；重算生成新版本并留痕，旧版本仍可读。"],
])

# ---------------- package ----------------
STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="微软雅黑" w:cs="Calibri"/><w:sz w:val="21"/><w:szCs w:val="21"/><w:lang w:val="en-US" w:eastAsia="zh-CN"/></w:rPr></w:rPrDefault><w:pPrDefault><w:spacing w:after="120" w:line="288" w:lineRule="auto"/></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="120"/><w:jc w:val="center"/></w:pPr><w:rPr><w:b/><w:color w:val="0B57D0"/><w:sz w:val="56"/><w:szCs w:val="56"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="80"/><w:jc w:val="center"/></w:pPr><w:rPr><w:color w:val="595959"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="360" w:after="160"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="0B57D0"/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="280" w:after="120"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="1F3864"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="200" w:after="100"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:color w:val="404040"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="caption"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="40" w:after="240"/><w:jc w:val="center"/></w:pPr><w:rPr><w:color w:val="595959"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="Table Text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="40"/></w:pPr><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>
<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr></w:style>
<w:style w:type="table" w:styleId="Tbl"><w:name w:val="Tbl"/><w:basedOn w:val="TableNormal"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="BFD0E8"/><w:left w:val="single" w:sz="4" w:space="0" w:color="BFD0E8"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="BFD0E8"/><w:right w:val="single" w:sz="4" w:space="0" w:color="BFD0E8"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="BFD0E8"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="BFD0E8"/></w:tblBorders><w:tblCellMar><w:top w:w="60" w:type="dxa"/><w:left w:w="100" w:type="dxa"/><w:bottom w:w="60" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
</w:styles>"""

CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

drels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>']
for i in range(len(FIGS)):
    drels.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image%d.png"/>' % (i + 2, i + 1))
drels.append('</Relationships>')

DOC = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
 '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
 'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
 'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
 '<w:body>' + "".join(B) +
 '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="851" w:footer="992" w:gutter="0"/></w:sectPr>'
 '</w:body></w:document>')

z = zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED)
z.writestr("[Content_Types].xml", CT)
z.writestr("_rels/.rels", RELS)
z.writestr("word/document.xml", DOC)
z.writestr("word/styles.xml", STYLES)
z.writestr("word/_rels/document.xml.rels", "\n".join(drels))
for i, (fn, cap) in enumerate(FIGS):
    z.write(SH + fn, "word/media/image%d.png" % (i + 1))
z.close()
print("WROTE", OUT, os.path.getsize(OUT))

import xml.dom.minidom as M
for part in ("word/document.xml", "word/styles.xml", "word/_rels/document.xml.rels", "[Content_Types].xml", "_rels/.rels"):
    M.parseString(zipfile.ZipFile(OUT).read(part))
    print("XML-OK", part)