# -*- coding: utf-8 -*-
import io, os
OUT = r"D:\ws\codex\游侠前端设计模板_浦发风格_V1_20261105"
BAN = ["\u76d1\u542c", "\u60c5\u7eea\u8bc6\u522b", "\u8bed\u6c14\u5206\u6790", "\u5df2\u7b7e\u7f72", "\u5df2\u9a8c\u6536", "\u751f\u4ea7\u5c31\u7eea", "\u51bb\u7ed3\u751f\u6548", "25/25"]
for root, dirs, fs in os.walk(OUT):
    dirs[:] = [d for d in dirs if d not in ("_shots", "_lint", "__pycache__")]
    for f in fs:
        if f == "checklist_交付前自检.md":   # 该文件本身要列出禁字样，属规则条文
            continue
        if not f.endswith((".html", ".css", ".js", ".md", ".json")):
            continue
        p = os.path.join(root, f)
        t = io.open(p, encoding="utf-8", errors="ignore").read()
        for w in BAN:
            if w in t:
                print("BAN HIT", os.path.relpath(p, OUT), w)
print("scan done")
