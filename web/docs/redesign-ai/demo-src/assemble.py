import io,os,re
D="/mnt/c/Users/szf/AppData/Local/Temp/fe-scratch/mock/"
def rd(f): return io.open(D+f,encoding="utf-8").read()
def between(txt,a,b):
    i=txt.index(a); j=txt.index(b,i); return txt[i:j]
m1=rd("m1-copilot-workbench.html"); m2=rd("m2-pulse-home.html"); m3=rd("m3-attribution-canvas.html")
m4=rd("m4-interactive-report.html"); m5=rd("m5-semantic-layer.html"); p3=rd("demo-part3.html")
base=m1[:m1.index("YX.init")]
demo=base+between(m2,"function viewA1(){","YX.init")+between(m3,"function stepsFull(){","YX.init") \
     +between(m4,"function blk(","YX.init")+between(m5,"function viewA5(){","YX.init")+p3
for i in range(1,11):
    demo=demo.replace('href="#a%d"><span'%i, 'href="#a%d" data-nav="a%d"><span'%(i,i))
demo=demo.replace(' class="rail-item on"',' class="rail-item"')
demo=demo.replace('<span class="exp">展开轨迹 ▾</span>','<span class="exp" data-open="sh_plan">展开轨迹 ▾</span>')
demo=demo.replace('<span class="mini" title="查看证据">◆</span>','<span class="mini" data-open="sh_ev" title="查看证据">◆</span>')
old_cf='<div class="card-f"><span class="tiny">证据 snap-20261031 · 口径 v3 · 校验 PASS · 阈值 THR-07</span></div>'
new_cf='<div class="card-f"><span class="tiny">证据 snap-20261031 · 口径 v3 · 校验 PASS · 阈值 THR-07</span><button class="btn btn-sm" data-open="sh_ev" style="margin-left:8px">查看证据</button></div>'
demo=demo.replace(old_cf,new_cf)
io.open(D+"demo-system.html","w",encoding="utf-8").write(demo)
print("demo bytes",len(demo))