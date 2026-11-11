# Downloads the three raw data sources into data/raw/.
# Files that already exist are skipped, so it is safe to run again.
#
#   1. Jolpica F1   - results, laps, pit stops (1950-now)      https://github.com/jolpica/jolpica-f1
#   2. F1DB         - circuits, engines, tyres + track SVGs     https://github.com/f1db/f1db

import io
import zipfile
from pathlib import Path

import requests

RAW = Path("data/raw")
F1DB_VERSION = "v2026.20.0"


def jolpica():
    out = RAW / "jolpica"
    if (out / "formula_one_round.csv").exists():
        print("jolpica: already there")
        return
    print("jolpica: downloading csv dump...")
    r = requests.get("https://api.jolpi.ca/data/dumps/download/delayed/?dump_type=csv", timeout=120)
    r.raise_for_status()
    zipfile.ZipFile(io.BytesIO(r.content)).extractall(out)


def f1db():
    out = RAW / "f1db"
    if not (out / "f1db-races.csv").exists():
        print("f1db: downloading csv release", F1DB_VERSION)
        url = f"https://github.com/f1db/f1db/releases/download/{F1DB_VERSION}/f1db-csv.zip"
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        zipfile.ZipFile(io.BytesIO(r.content)).extractall(out)

    # track layouts (one svg per layout, e.g. monza-1.svg)
    svg_dir = out / "circuits"
    svg_dir.mkdir(parents=True, exist_ok=True)
    listing = requests.get("https://api.github.com/repos/f1db/f1db/contents/src/assets/circuits/white",
                           timeout=30).json()
    todo = [f["name"] for f in listing if not (svg_dir / f["name"]).exists()]
    print(f"f1db: {len(listing)} track svgs, {len(todo)} to download")
    for name in todo:
        url = f"https://raw.githubusercontent.com/f1db/f1db/main/src/assets/circuits/white/{name}"
        (svg_dir / name).write_text(requests.get(url, timeout=30).text, encoding="utf-8")


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    jolpica()
    f1db()
    print("done")
