# Downloads the three raw data sources into data/raw/.
# Files that already exist are skipped, so it is safe to run again.
#
#   1. Jolpica F1   - results, laps, pit stops (1950-now)      https://github.com/jolpica/jolpica-f1
#   2. F1DB         - circuits, engines, tyres + track SVGs     https://github.com/f1db/f1db
#   3. OpenF1       - team colours, tyre stints, weather (2023+) https://openf1.org

import io
import json
import sys
import time
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


def openf1(years=(2023, 2024, 2025, 2026)):
    # free tier allows 30 requests / minute -> wait 2.1 s between calls
    out = RAW / "openf1"
    out.mkdir(parents=True, exist_ok=True)

    def get(endpoint, **params):
        name = endpoint + "_" + "_".join(f"{v}" for v in params.values()) + ".json"
        path = out / name
        if path.exists():
            return json.loads(path.read_text())
        for attempt in range(5):
            time.sleep(2.1)
            r = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=60)
            if r.status_code == 429:
                time.sleep(20)
                continue
            if r.status_code == 404:  # no data for this session
                data = []
                break
            r.raise_for_status()
            data = r.json()
            break
        else:
            raise RuntimeError(f"gave up on {endpoint} {params}")
        path.write_text(json.dumps(data))
        return data

    sessions = []
    for y in years:
        sessions += [s for s in get("sessions", year=y, session_name="Race")]
    (out / "race_sessions.json").write_text(json.dumps(sessions))
    print(f"openf1: {len(sessions)} race sessions")

    for i, s in enumerate(sessions, 1):
        key = s["session_key"]
        for endpoint in ["drivers", "stints", "weather"]:
            get(endpoint, session_key=key)
        print(f"  {i}/{len(sessions)} {s['year']} {s['country_name']}", flush=True)


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    jolpica()
    f1db()
    if "--skip-openf1" not in sys.argv:
        openf1()
    print("done")
