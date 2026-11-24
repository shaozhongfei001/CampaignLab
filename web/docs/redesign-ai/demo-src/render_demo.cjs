const {chromium}=require('playwright');
const path=require('path');
(async()=>{
  const ids=process.argv.slice(2);
  const b=await chromium.launch();
  const ctx=await b.newContext({viewport:{width:1440,height:900},deviceScaleFactor:2});
  const p=await ctx.newPage();
  p.on('pageerror',e=>console.log('PAGE-ERR:',e.message));
  p.on('console',m=>{if(m.type()==='error')console.log('CONSOLE-ERR:',m.text());});
  const abs=path.resolve('demo-system.html').replace(/\\/g,'/');
  await p.goto('file://'+abs,{waitUntil:'load'});
  await p.waitForTimeout(500);
  for(const id of ids){
    await p.evaluate(v=>YX.nav(v),id);
    await p.waitForTimeout(350);
    await p.screenshot({path:'shots/demo-'+id+'.png'});
    console.log('SHOT demo-'+id);
  }
  await b.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});