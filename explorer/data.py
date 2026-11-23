from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "processed"


def _read(name, **kw):
    return pd.read_csv(DATA / f"{name}.csv", **kw)


circuits = _read("circuits")
races = _read("races", parse_dates=["date"])
results = _read("results")
laps = _read("laps")
pits = _read("pit_stops")
standings = _read("standings")
stints = _read("stints")
tracks = _read("tracks")
drivers = _read("drivers")
teams = _read("teams").set_index("team_id")
team_standings = _read("team_standings")

# keep_default_na: "NA" is Namibia. The disputed areas are extra shapes on plotly's world map.
countries = _read("countries", keep_default_na=False)
DISPUTED = ["XAP", "XHT", "XBT", "XAC", "XIT", "XJK"]
countries = pd.concat([countries, pd.DataFrame({"iso3": DISPUTED, "name": "Disputed area"})], ignore_index=True)

results = results.merge(races[["race_id", "circuit_id"]], on="race_id")

YEAR_MIN, YEAR_MAX = int(races["year"].min()), int(races["year"].max())
LAST_FULL_SEASON = int(standings.groupby("year")["round"].max().pipe(
    lambda s: s[s.index < YEAR_MAX].index.max()))

season_final = standings[standings["round"] == standings.groupby("year")["round"].transform("max")]

driver_names = drivers.set_index("driver_id")["name"].to_dict()
circuit_info = circuits.set_index("id")
race_info = races.set_index("race_id")
team_years = results.groupby("team_id")["year"].agg(["min", "max"])

races_per_country = races.merge(circuits[["id", "country_iso3"]], left_on="circuit_id", right_on="id") \
    .groupby("country_iso3").size()

driver_options = [{"label": f"{r.name} ({r.first_year}–{r.last_year})", "value": r.driver_id}
                  for r in drivers.sort_values("starts", ascending=False).itertuples()]

search_options = [{"label": f"🏎 {r['name']} · team ({team_years.at[tid, 'min']}–{team_years.at[tid, 'max']})",
                   "value": f"t:{tid}"} for tid, r in teams.sort_values("entries", ascending=False).iterrows()] + \
                 [{"label": f"👤 {o['label']}", "value": f"d:{o['value']}"} for o in driver_options]


def career_circuits(res):
    g = res.groupby("circuit_id").agg(
        races=("race_id", "nunique"), wins=("is_win", "sum"), podiums=("is_podium", "sum"),
        best=("position", "min"), first=("year", "min"), last=("year", "max"))
    g["best"] = g["best"].map(lambda p: f"P{int(p)}" if pd.notna(p) else "–")
    return circuits[["id", "name", "place", "country", "latitude", "longitude"]].merge(g, left_on="id",
                                                                                      right_index=True)
