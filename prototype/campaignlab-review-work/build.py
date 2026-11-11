import hashlib
import json
from pathlib import Path


WORK = Path(__file__).resolve().parent
OUT = WORK.parent / "campaignlab-review-deliverables"
NAME = "CampaignLab-Strategy-Review-Prototype.html"


def main():
    bank_paths = [OUT / f"CampaignLab-Simulated-Bank-{key}.json" for key in "AB"]
    embedded = {"banks": [json.loads(path.read_text(encoding="utf-8")) for path in bank_paths],
                "questions": json.loads((WORK / "questions.json").read_text(encoding="utf-8"))}
    data = json.dumps(embedded, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    js = "\n".join((WORK / name).read_text(encoding="utf-8") for name in ("core.js", "ui.js"))
    shell = (WORK / "shell.html").read_text(encoding="utf-8")
    parts = {"/* STYLE */": (WORK / "style.css").read_text(encoding="utf-8"), "/* SAMPLES */": data, "/* LOGIC */": js}
    for marker, value in parts.items():
        assert shell.count(marker) == 1
        shell = shell.replace(marker, value)
    html = shell.encode("utf-8")
    (OUT / NAME).write_bytes(html)
    dist = WORK / "dist"
    dist.mkdir(exist_ok=True)
    (dist / "index.html").write_bytes(html)
    for path in [OUT / NAME, *bank_paths]:
        data = path.read_bytes()
        print(f"{hashlib.sha256(data).hexdigest()}  {path.name}  {len(data)} bytes")


if __name__ == "__main__":
    main()
