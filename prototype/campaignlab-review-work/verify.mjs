import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {dirname, join} from "node:path";
import {createContext, runInContext} from "node:vm";

const root = dirname(fileURLToPath(import.meta.url));
const output = join(root, "..", "campaignlab-review-deliverables");
const fixtures = ["A", "B"].map(id => JSON.parse(readFileSync(join(output, "CampaignLab-Simulated-Bank-" + id + ".json"), "utf8")));
const questionList = JSON.parse(readFileSync(join(root, "questions.json"), "utf8"));
const context = createContext({fixtures, questionList});
runInContext(readFileSync(join(root, "core.js"), "utf8") + "\nthis.api = {normalizeBank,scopeFor,scopeRows,aggregate,analyze,funnelDecomposition,dimensionSplit,scanAnomalies,matchOutcomes,replayCase,classifyChannel,parseQuestion,runQuestion,reviseSnapshot,reportModel,STAGES};", context);
const api = context.api;
const [a,b] = fixtures.map(api.normalizeBank);
const scope = api.scopeFor(a);
const base = api.analyze(a,scope);
const threshold = a.metadata.thresholds;
const copy = value => JSON.parse(JSON.stringify(value));
const results = [];
const test = (id, name, fn) => {
  try { fn(); results.push({id,name,status:"PASS"}); }
  catch (error) { results.push({id,name,status:"FAIL",error:String(error.message)}); }
};
const range = patch => api.scopeFor(a,patch);
const compare = patch => api.analyze(a,range(patch));
const measure = (patch,key) => compare(patch).current?.[key];

test("V01","导入宽表和长表，元／分转换及切片数",()=>{
  assert.equal(a.records.length,510);
  assert.equal(b.records.length,510);
  assert.equal(a.mapping.layout,"wide");
  assert.equal(b.mapping.layout,"long");
  assert.equal(b.mapping.moneyDivisor,100);
  assert.deepEqual(copy(api.analyze(a,scope).current),copy(api.analyze(b,api.scopeFor(b)).current));
});
test("V02","主例两期五层人数，两个有效触达分母",()=>{
  const stages=api.STAGES.map(([key])=>key);
  assert.deepEqual(Array.from(stages.map(key=>base.current[key])),[12000,11520,8640,3456,1728]);
  assert.deepEqual(Array.from(stages.map(key=>base.base[key])),[10000,9600,7680,3840,1920]);
  assert.equal(base.current.effectiveRate,0.15);
  assert.equal(base.current.validConv,0.5);
  assert.equal(base.current.contactConv,0.4);
  assert.equal(base.base.contactConv,0.5);
});
test("V03","量率拆解与固定参数试算",()=>{
  const impacts=Array.from(api.funnelDecomposition(base.current,base.base).map(item=>item.effect));
  assert.deepEqual(impacts,[384,0,-144,-432,0]);
  assert.equal(impacts.reduce((x,y)=>x+y,0),-192);
  assert.equal(base.current.executed*0.45*base.current.validConv,1944);
});
test("V04","当前范围、全行、分组、机构、产品和来源",()=>{
  assert.equal(base.current.deployed,1);
  assert.equal(measure({branch:"all"},"deployed"),5);
  assert.equal(measure({branch:"all",group:"东部组"},"deployed"),3);
  assert.equal(measure({origin:"hq"},"aum")+measure({origin:"branch"},"aum"),base.current.aum);
  for (const key of ["wealthSale","nonCashWealthSale","fundSale","nonMoneyFundSale","insuranceSale"]) assert.ok(base.current[key]>0);
  assert.ok(measure({subbranch:"东岚二支行"},"sent")>0);
});
test("V05","企微恢复时仅比较共同范围，独立同比可算",()=>{
  const all=compare({channel:"all"});
  assert.equal(all.status,"partial");
  assert.ok(all.notes.some(text=>text.includes("企业微信")));
  assert.ok(all.comparableRows.every(row=>row.channel!=="wechat"));
  assert.equal(compare({reference:"yoy"}).status,"full");
  assert.ok(all.current.effective!==null);
});
test("V06","总体去重、零分母和负金额",()=>{
  const all=compare({channel:"all"});
  const perChannel=Object.keys(a.metadata.channels).reduce((sum,channel)=>sum+measure({channel},"sent"),0);
  assert.ok(all.current.sent<perChannel);
  assert.equal(measure({branch:"B05",channel:"ai"},"effectiveRate"),null);
  assert.equal(base.current.aum,-4074000);
});
test("V07","五类异常规则各有可判定样本及阈值",()=>{
  const alerts=api.scanAnomalies(a,scope,threshold);
  for (const kind of ["mom","peer","own","layer","mix"]) assert.ok(alerts.some(row=>row.kind===kind),"缺少 "+kind);
  assert.ok(alerts.every(row=>row.baseline&&row.threshold&&row.impact));
  const next=api.scanAnomalies(a,scope,{...threshold,mom:12},["effective"],"mom");
  assert.equal(next.length,0);
});
test("V08","归因按客群、渠道、支行、来源和存款类型下钻",()=>{
  for (const dim of ["channel","subbranch","segment","origin"]) {
    const view=api.dimensionSplit(a,base,"aum",dim);
    assert.ok(view.rows.length>0);
    assert.ok(Math.abs(view.rows.reduce((sum,item)=>sum+item.effect,0)+view.residual-(base.current.aum-base.base.aum))<0.01);
  }
  const deposit=api.dimensionSplit(a,base,"deposit","depositType");
  assert.equal(deposit.rows.length,2);
  assert.equal(deposit.rows.reduce((sum,item)=>sum+item.effect,0),base.current.deposit-base.base.deposit);
});
test("V09","客群口径保留，未绑定活动守住数据边界",()=>{
  const deployed=measure({segment:"大众",segmentBasis:"segment"},"effective");
  const tag=measure({segment:"大众",segmentBasis:"tag"},"effective");
  assert.ok(deployed>0);
  assert.notEqual(deployed,tag);
  assert.ok(measure({activity:"AC-101"},"activityCount")>0);
  assert.equal(compare({activity:"AC-202"}).current,null);
});
test("V10","窗端点、加10、多候选及去重归属",()=>{
  const pending=api.matchOutcomes(a);
  assert.equal(pending[0].matched.length,2);
  assert.equal(pending[0].status,"多候选待核");
  assert.equal(pending[0].chosen,null);
  assert.equal(pending[0].matched.find(t=>t.id==="T-01").age,7);
  assert.equal(pending[0].matched.find(t=>t.id==="T-02").dispatch,10);
  assert.equal(pending[1].chosen.age,60);
  assert.equal(pending[2].status,"未匹配");
  assert.equal(pending[3].status,"未匹配");
  assert.equal(api.matchOutcomes(a,"nearest")[0].chosen.id,"T-02");
});
const conditions={channel:"remote",line:"wealth",seconds:59,rounds:0,clicked:false,detail:false,received:true,attempted:true,answered:true,message:true,delivered:true,freqBlocked:false,daysInRange:true,downstream:true};
test("V11","远程财私与个贷的边界和时间范围",()=>{
  const run = patch=>api.classifyChannel(a,{...conditions,...patch});
  assert.equal(run({seconds:59}).effective,false);
  assert.equal(run({seconds:60}).effective,true);
  assert.equal(run({line:"loan",seconds:9}).effective,false);
  assert.equal(run({line:"loan",seconds:10}).effective,true);
  assert.equal(run({daysInRange:false,seconds:60}).executed,false);
});
test("V12","短信、推送、企微、AI外呼、经理渠道事件",()=>{
  const run = patch=>api.classifyChannel(a,{...conditions,...patch});
  assert.equal(run({channel:"sms",delivered:false,clicked:false}).executed,true);
  assert.equal(run({channel:"sms",clicked:true,detail:false}).effective,false);
  assert.equal(run({channel:"sms",clicked:true,detail:true}).effective,true);
  assert.equal(run({channel:"push",delivered:false,clicked:true,detail:true}).effective,false);
  assert.equal(run({channel:"wechat",seconds:0,clicked:false,rounds:1}).effective,true);
  assert.equal(run({channel:"wechat",seconds:60,rounds:0}).effective,true);
  assert.equal(run({channel:"wechat",seconds:0,clicked:true,rounds:0}).effective,true);
  assert.equal(run({channel:"ai",freqBlocked:true,rounds:1}).success,false);
  assert.equal(run({channel:"ai",rounds:1}).effective,true);
  assert.equal(run({channel:"manager",downstream:false}).effective,false);
  assert.equal(run({channel:"manager",downstream:true}).effective,true);
});
test("V13","乙行差异口径被保留",()=>{
  const ra=api.scopeRows(a,api.scopeFor(a,{channel:"push"}));
  const rb=api.scopeRows(b,api.scopeFor(b,{channel:"push"}));
  assert.notEqual(ra[0].definition,rb[0].definition);
  const input={...conditions,channel:"push",clicked:true,detail:true,seconds:2};
  assert.equal(api.classifyChannel(a,input).effective,true);
  assert.equal(api.classifyChannel(b,input).effective,false);
  assert.equal(api.classifyChannel(b,{...input,seconds:3}).effective,true);
});
test("V14","原规则复算一致、差异和频次耗尽",()=>{
  const [pass,fail,used]=a.metadata.replayCases;
  assert.equal(api.replayCase(pass,"arrival").winner,pass.observedWinner);
  assert.equal(api.replayCase(pass,"appointment").winner,"S-101");
  assert.notEqual(api.replayCase(fail,"arrival").winner,fail.observedWinner);
  assert.equal(api.replayCase(used,"appointment").winner,null);
  assert.equal(a.metadata.preflight.winners[pass.id],api.replayCase(pass,"appointment").winner);
  assert.equal(measure({period:"2026-11"},"effective"),1944);
});
test("V15","七段报告、阈值、口径、版本与取数清单",()=>{
  const report=api.reportModel(a,scope,threshold);
  assert.equal(report.canSign,true);
  assert.equal(report.text.match(/^## /gm).length,7);
  for (const text of ["A-001","阈值","2026-10-31","30 天","90 天","1,728","-432","数据来源"]) assert.ok(report.text.includes(text),text);
  const no=api.reportModel(a,range({period:"2026-01"}),threshold);
  assert.equal(no.canSign,false);
  assert.equal(no.status,"待补数据");
  assert.match(no.text,/^# 策略复盘取数清单/);
  const partial=api.reportModel(a,range({channel:"all"}),threshold);
  assert.equal(partial.status,"部分可比草稿");
  assert.equal(partial.canSign,false);
});
test("V16","快照更正保留原值",()=>{
  const changed=api.reviseSnapshot(a);
  assert.equal(changed.snapshot,"A-001-R1");
  assert.equal(api.analyze(changed,scope).current.aum,-3949000);
  assert.equal(api.analyze(a,scope).current.aum,-4074000);
  assert.equal(api.reviseSnapshot(changed),null);
});
test("V17","输入校验拦截重复、负人数、错误列及孤立长表",()=>{
  const duplicates=copy(fixtures[0]);
  const table=duplicates.tables[duplicates.mapping.entityTable];
  table.rows.push(table.rows[0]);
  assert.throws(()=>api.normalizeBank(duplicates),/重复切片/);
  const negative=copy(fixtures[0]);
  const t=negative.tables[negative.mapping.entityTable];
  t.rows[0][t.columns.indexOf(negative.mapping.countFields.sent)]=-1;
  assert.throws(()=>api.normalizeBank(negative),/非负人数/);
  const bad=copy(fixtures[0]);
  bad.tables[bad.mapping.entityTable].rows[0].pop();
  assert.throws(()=>api.normalizeBank(bad),/行列数/);
  const orphan=copy(fixtures[1]);
  orphan.tables[orphan.mapping.countsTable].rows.push(["不存在","M01",1]);
  assert.throws(()=>api.normalizeBank(orphan),/无法匹配/);
});
test("V18","比较参照均值、同比和目标的口径",()=>{
  const same=compare({reference:"peer"});
  assert.equal(same.spec.peers.length,2);
  assert.ok(same.spec.peers.every(branch=>branch.id!=="B01"&&branch.group==="东部组"));
  assert.equal(compare({reference:"bank"}).spec.peers.length,5);
  assert.equal(compare({reference:"target"}).base.effective,2000);
  assert.equal(compare({reference:"yoy"}).spec.periods[0],"2025-10");
});

const qExpect = {
  R01:[1,"effectiveRate"],R02:[1,"aum"],R03:[5,"successRate"],R04:[3,"effective"],R05:[2,"deposit"],
  R06:[5,"strategies"],R07:[3,"effectiveRate"],R08:[2,"sent"],R09:[1,"successRate"],R10:[6,"aum"],
  R11:[1,"execution"],R12:[5,"deposit"],R13:[1,"reach"],R14:[1,"reach"],R15:[1,"execution"],
  R16:[5,"successRate"],R17:[1,"aum"],R18:[1,"deposit"],R19:[5,"wealth"],R20:[5,"fund"],R21:[1,"execution"],
  R22:[5,"successRate"],R23:[5,"effectiveRate"],R24:[1,"aum"],R25:[5,"effectiveRate"],R26:[5,"contactConv"],
  R27:[1,"effective"],R28:[1,"execution"],R29:[1,"deposit"],R30:[1,"aum"],R31:[1,"effectiveRate"],
  R32:[1,"wealth"],R33:[1,"wealth"],R34:[1,"aum"],R35:[1,"deposit"],R36:[1,"reach"],R37:[1,"effective"],
  R38:[1,"deposit"],R39:[5,"execution"],R40:[5,"aum"],R41:[1,"execution"],R42:[1,"deposit"],R43:[1,"execution"],
  R44:[1,"successRate"],R45:[1,"effectiveRate"],R46:[1,"reach"],
  R47:[1,null],R48:[1,null],R49:[1,null],R50:[1,"aum"],R51:[1,null],R52:[1,null],
  R53:[1,null],R54:[5,"execution"],R55:[5,"deposit"],R56:[2,"execution"],
  Q01:[1,"effective"],Q02:[1,"effectiveRate"],
};
for (const [id,intent,question] of questionList) {
  test(id,"问法："+intent,()=>{
    const q=api.runQuestion(question,a,scope,threshold);
    assert.equal(q.intent,intent);
    if (intent==="澄清") return assert.ok(q.message);
    assert.ok(q.focus.analysis.current);
    assert.equal(q.ranking.length,qExpect[id][0]);
    if (qExpect[id][1]) assert.ok(q.keys.includes(qExpect[id][1]));
    if (intent==="归因") assert.ok(q.cause && (q.cause.rows.length || q.cause.funnel?.length));
    if (intent==="报告") {
      const report=api.reportModel(a,q.scope,threshold,[],q.reportType,q);
      assert.ok(report.text.includes("## 七、附录"));
      if (["R54","R55","R56"].includes(id)) assert.ok(report.text.includes("### 专题对照"));
      if (id==="R49") assert.equal(report.status,"部分可比草稿");
    }
    if (id==="R08") assert.ok(q.ranking.every(row=>row.analysis.current.sent>500000));
    if (id==="R09") assert.equal(q.ranking[0].scope.branch,"B05");
    if (id==="R21") assert.ok(Math.abs(q.focus.analysis.current.execution-0.35)<0.00001);
    if (id==="R23") assert.equal(q.scope.reference,"peer");
    if (id==="R35") assert.equal(q.cause.dim,"depositType");
    if (id==="R38") assert.equal(q.focus.scope.reference,"peer");
    if (id==="R44" && !q.compareRows.length) assert.equal(q.cause,null);
    if (id==="R51") assert.equal(q.scope.strategy,"S-101");
    if (id==="R52") assert.equal(q.scope.segment,"大众");
  });
}

const html=readFileSync(join(output,"CampaignLab-Strategy-Review-Prototype.html"),"utf8");
test("V19","单文件内嵌数据与独立 JSON 一致",()=>{
  const data=JSON.parse(html.match(/<script id="samples" type="application\/json">(.*?)<\/script>/s)[1]);
  assert.deepEqual(data.banks,fixtures);
  assert.deepEqual(data.questions,questionList);
  assert.doesNotMatch(html,/<script[^>]+\bsrc=|<link[^>]+rel="stylesheet"|\bfetch\(/);
});
const failed=results.filter(result=>result.status==="FAIL");
const report={total:results.length,passed:results.length-failed.length,failed:failed.length,results};
if (process.argv.includes("--json")) console.log(JSON.stringify(report,null,2));
else {
  console.log(`${report.passed}/${report.total} PASS`);
  for (const result of failed) console.log(result.id,result.name,result.error);
}
if (failed.length) process.exitCode=1;
