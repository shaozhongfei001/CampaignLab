import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo


WORK = Path(__file__).resolve().parent
ROOT = WORK.parent
OUT = ROOT / "campaignlab-review-deliverables"
ARCHIVE = OUT / "CampaignLab-Review-Prototype-Handoff.zip"
DATE = (2026, 11, 11, 0, 0, 0)
DELIVERABLES = (
    "CampaignLab-Strategy-Review-Prototype.html",
    "CampaignLab-Simulated-Bank-A.json",
    "CampaignLab-Simulated-Bank-B.json",
    "CampaignLab-Review-Acceptance-Checklist.md",
    "CampaignLab-Review-Prototype-Reproduction-Spec.md",
)
SOURCES = (
    "shell.html", "style.css", "core.js", "ui.js", "generate_data.py", "build.py",
    "verify.mjs", "questions.json", "verification-results.json", "package.py",
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def put(archive, name, data):
    item = ZipInfo(name, date_time=DATE)
    item.create_system = 3
    item.external_attr = 0o100644 << 16
    item.compress_type = ZIP_STORED
    archive.writestr(item, data)


def main():
    result = subprocess.run(
        ["node", str(WORK / "verify.mjs"), "--json"],
        check=True, capture_output=True,
    ).stdout
    evidence = json.loads(result)
    assert evidence["failed"] == 0 and evidence["total"] == 79
    (WORK / "verification-results.json").write_bytes(result)
    paths = sorted([OUT / name for name in DELIVERABLES] + [WORK / name for name in SOURCES])
    files = {path.relative_to(ROOT).as_posix(): path.read_bytes() for path in paths}
    manifest = "".join(f"{sha256(data)}  {name}\n" for name, data in files.items())
    with ZipFile(ARCHIVE, "w") as archive:
        for name, data in files.items():
            put(archive, name, data)
        put(archive, "SHA256SUMS", manifest.encode("utf-8"))
    print(f"{sha256(ARCHIVE.read_bytes())}  {ARCHIVE.name}  {ARCHIVE.stat().st_size} bytes")


if __name__ == "__main__":
    main()
