# -*- coding: utf-8 -*-
"""校验：模板三个产出页里用到的 class，是否都在 youxia-ui.css / 页内 <style> 里有定义。"""
import io, os, re
OUT = r"D:\ws\codex\游侠前端设计模板_浦发风格_V1_20261105"
css = io.open(os.path.join(OUT, "css", "youxia-ui.css"), encoding="utf-8").read()
defined = set(re.findall(r"\.([A-Za-z][\w-]*)", re.sub(r"/\*.*?\*/", "", css, flags=re.S)))
for f in ["template_blank.html", "template_blank_singlefile.html", "gallery_组件图鉴.html"]:
    t = io.open(os.path.join(OUT, f), encoding="utf-8").read()
    local = "".join(re.findall(r"<style>(.*?)</style>", t, re.S))
    defined_local = defined | set(re.findall(r"\.([A-Za-z][\w-]*)", local))
    used = set()
    for m in re.finditer(r'class="([^"]*)"', t):
        for tok in re.split(r"[\s]+", m.group(1)):
            tok = re.sub(r"^[^A-Za-z]+", "", tok)
            if re.match(r"^[a-z][\w-]*$", tok):
                used.add(tok)
    miss = sorted(u for u in used if u not in defined_local)
    print("%-26s used=%3d  UNDEFINED=%s" % (f, len(used), miss))
