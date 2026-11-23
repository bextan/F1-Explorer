import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OPENF1 = RAW / "openf1"


def f1db(name):
    return pd.read_csv(RAW / "f1db" / f"f1db-{name}.csv", low_memory=False)


def jolpica(name):
    return pd.read_csv(RAW / "jolpica" / f"formula_one_{name}.csv", low_memory=False)


def openf1(endpoint, session_race):
    frames = []
    for key in session_race["session_key"]:
        path = OPENF1 / f"{endpoint}_{key}.json"
        if path.exists():
            data = json.loads(path.read_text())
            if data:
                frames.append(pd.DataFrame(data))
    return pd.concat(frames, ignore_index=True).merge(session_race, on="session_key")
