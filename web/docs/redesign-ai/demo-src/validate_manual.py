# -*- coding: utf-8 -*-
import zipfile, re
import xml.dom.minidom as M
P = "/mnt/c/Users/szf/AppData/Local/Temp/fe-scratch/mock/营销策略复盘CampaignLab-AI-Review-User-Manual.docx"
z = zipfile.ZipFile(P)
doc = z.read("word/document.xml").decode("utf-8")
rels = z.read("word/_rels/document.xml.rels").decode("utf-8")

PPR = "pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr suppressLineNumbers pBdr shd tabs suppressAutoHyphens kinsoku wordWrap overflowPunct topLinePunct autoSpaceDE autoSpaceDN bidi adjustRightInd snapToGrid spacing ind contextualSpacing mirrorIndents suppressOverlap jc textDirection textAlignment textboxTightWrap outlineLvl divId cnfStyle rPr sectPr pPrChange".split()
RPR = "rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow emboss imprint noProof snapToGrid vanish webHidden color spacing w kern position sz szCs highlight u effect bdr shd fitText vertAlign rtl cs em lang eastAsianLayout specVanish oMath".split()
TCPR = "cnfStyle tcW gridSpan hMerge vMerge tcBorders shd noWrap tcMar textDirection tcFitText vAlign hideMark headers".split()
TBLPR = "tblStyle tblpPr tblOverlap bidiVisual tblStyleRowBandSize tblStyleColBandSize tblW jc tblCellSpacing tblInd tblBorders shd tblLayout tblCellMar tblLook tblCaption tblDescription".split()
TRPR = "cnfStyle divId gridBefore gridAfter wBefore wAfter cantSplit trHeight tblHeader tblCellSpacing jc hidden".split()
ORD = {"pPr": PPR, "rPr": RPR, "tcPr": TCPR, "tblPr": TBLPR, "trPr": TRPR}

d = M.parseString(doc)
bad = []
def walk(node):
    for c in node.childNodes:
        if c.nodeType == c.ELEMENT_NODE:
            ln = c.localName
            if ln in ORD:
                names = [x.localName for x in c.childNodes if x.nodeType == x.ELEMENT_NODE]
                idx = [ORD[ln].index(n) for n in names if n in ORD[ln]]
                unk = [n for n in names if n not in ORD[ln]]
                if unk: bad.append(("UNKNOWN", ln, unk))
                if idx != sorted(idx): bad.append(("ORDER", ln, names))
            walk(c)
walk(d.documentElement)
print("PPR-ORDER-BAD:", bad if bad else "none")

embeds = re.findall(r'r:embed="(rId\d+)"', doc)
rel_imgs = re.findall(r'Id="(rId\d+)"[^>]*image', rels)
print("embeds", len(embeds), "relimgs", len(rel_imgs), "match", sorted(embeds) == sorted(rel_imgs))
print("drawings", doc.count("<w:drawing>"), "caps", len(re.findall(r"图 \d\d", doc)))
print("bookmarks", len(re.findall(r"bookmarkStart", doc)), "links", len(re.findall(r"<w:hyperlink", doc)))
anchors = set(re.findall(r'w:anchor="([^"]+)"', doc))
bms = set(re.findall(r'w:name="([^"]+)"[^>]*/></w:bookmarkStart>|<w:bookmarkStart[^>]*w:name="([^"]+)"', doc))
bms = set(re.findall(r'<w:bookmarkStart w:id="\d+" w:name="([^"]+)"', doc))
print("anchors-ok", anchors <= bms, sorted(anchors), sorted(bms))

# text extraction
out = []
def text(node):
    for c in node.childNodes:
        if c.nodeType == c.ELEMENT_NODE:
            if c.localName == "t":
                out.append("".join(t.data for t in c.childNodes if t.nodeType == t.TEXT_NODE))
            elif c.localName in ("p", "tr"):
                text(c); out.append("\n")
            elif c.localName == "tab":
                out.append("\t")
            elif c.localName == "tc":
                text(c); out.append(" | ")
            elif c.localName == "br":
                out.append("\n")
            else:
                text(c)
text(d.documentElement)
txt = "".join(out)
txt = re.sub(r"\n{3,}", "\n\n", txt)
io_open = open("/mnt/c/Users/szf/AppData/Local/Temp/fe-scratch/mock/manual_ai.txt", "w", encoding="utf-8")
io_open.write(txt); io_open.close()
print("TEXT-LEN", len(txt))