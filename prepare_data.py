# Combines the three raw sources into a few clean tables for the dashboard.
#
#   F1DB     -> base tables: races, circuits, drivers, teams, engines, tyres, standings, pit stops
#   Jolpica  -> lap-by-lap positions and times (1994+), cleaner retirement status codes
#   OpenF1   -> official team colours, driver photos, tyre stints, weather (2023+)
#
# Joining keys:
#   F1DB <-> Jolpica : (year, round) is identical in both, then car number inside a race
#   F1DB <-> OpenF1  : year + race date (+-1 day, Las Vegas is dated differently), then car number

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from svgpathtools import parse_path

RAW = Path("data/raw")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)


def f1db(name):
    return pd.read_csv(RAW / "f1db" / f"f1db-{name}.csv", low_memory=False)


def jolpica(name):
    return pd.read_csv(RAW / "jolpica" / f"formula_one_{name}.csv", low_memory=False)


# ============================================================ F1DB base tables
countries = f1db("countries").set_index("id")["name"]
gp_table = f1db("grands-prix").set_index("id")
gps = gp_table["name"]
drivers = f1db("drivers")
constructors = f1db("constructors").set_index("id")["name"]
engines = f1db("engine-manufacturers").set_index("id")["name"]
tyres = f1db("tyre-manufacturers").set_index("id")["name"]

# ---------- circuits
circuits = f1db("circuits")
circuits = circuits.rename(columns={"fullName": "full_name", "placeName": "place"})
circuits["country"] = circuits["countryId"].map(countries)
circuits["type"] = circuits["type"].str.title()          # RACE -> Race
circuits["direction"] = circuits["direction"].str.replace("_", " ").str.lower()

# ---------- races
races = f1db("races")
races = races[["id", "year", "round", "date", "grandPrixId", "officialName", "circuitId",
               "circuitLayoutId", "laps", "distance", "courseLength"]]
races.columns = ["race_id", "year", "round", "date", "gp_id", "official_name", "circuit_id",
                 "layout_id", "laps", "distance_km", "lap_length_km"]
races["date"] = pd.to_datetime(races["date"])
races["gp"] = races["gp_id"].map(gps) + " GP"
races["gp_abbr"] = races["gp_id"].map(gp_table["abbreviation"])

# ---------- race results
res = f1db("races-race-results")

# DNQ / DNPQ / DNP = never took part in the race -> not a race result
res = res[~res["positionText"].isin(["DNQ", "DNPQ", "DNP"])].copy()

res = res.rename(columns={
    "raceId": "race_id", "driverId": "driver_id", "constructorId": "team_id",
    "positionNumber": "position", "positionText": "position_text", "gridPositionNumber": "grid",
    "driverNumber": "number", "reasonRetired": "retired_reason", "pitStops": "pit_stops",
    "gapLaps": "laps_down", "positionDisplayOrder": "position_order",
})
res["driver"] = res["driver_id"].map(drivers.set_index("id")["name"])
res["abbr"] = res["driver_id"].map(drivers.set_index("id")["abbreviation"])
res["nationality"] = res["driver_id"].map(drivers.set_index("id")["nationalityCountryId"]).map(countries)
res["team"] = res["team_id"].map(constructors)
res["engine"] = res["engineManufacturerId"].map(engines)
res["tyre"] = res["tyreManufacturerId"].map(tyres)
res["number"] = pd.to_numeric(res["number"], errors="coerce").astype("Int64").astype(str)
res["points"] = res["points"].fillna(0)

dob = pd.to_datetime(res["driver_id"].map(drivers.set_index("id")["dateOfBirth"]))
res = res.merge(races[["race_id", "date"]], on="race_id")
res["age"] = ((res["date"] - dob).dt.days / 365.25).round(1)

# ============================================================ Jolpica: status + laps
j_season = jolpica("season")[["id", "year"]].rename(columns={"id": "season_id"})
j_round = jolpica("round").merge(j_season, on="season_id")[["id", "year", "number"]]
j_round.columns = ["round_id", "year", "round"]
j_session = jolpica("session")
j_session = j_session[j_session["type"] == "R"][["id", "round_id"]].rename(columns={"id": "session_id"})
j_rentry = jolpica("roundentry")[["id", "car_number"]].rename(columns={"id": "round_entry_id"})

j_entry = (jolpica("sessionentry")[["id", "session_id", "round_entry_id", "status"]]
           .rename(columns={"id": "session_entry_id"})
           .merge(j_session, on="session_id")
           .merge(j_round, on="round_id")
           .merge(j_rentry, on="round_entry_id"))
j_entry["number"] = j_entry["car_number"].astype("Int64").astype(str)
# shared cars in the 1950s give duplicate car numbers -> keep first
j_entry = j_entry.drop_duplicates(["year", "round", "number"])

res = res.merge(j_entry[["year", "round", "number", "status", "session_entry_id"]],
                on=["year", "round", "number"], how="left")

# outcome category: Jolpica status code first, F1DB position text as fallback
status_names = {0: "Finished", 1: "Finished (lapped)", 10: "DNF - accident",
                11: "DNF - mechanical", 20: "Disqualified", 30: "Did not start", 40: "Did not start"}
fallback = {"DNF": "DNF - mechanical", "DNS": "Did not start", "DSQ": "Disqualified",
            "EX": "Disqualified", "NC": "Not classified"}
res["outcome"] = res["status"].map(status_names)
res["outcome"] = res["outcome"].fillna(res["position_text"].map(fallback))
res.loc[res["outcome"].isna() & (res["laps_down"].fillna(0) > 0), "outcome"] = "Finished (lapped)"
res["outcome"] = res["outcome"].fillna("Finished")
# "not classified" in F1DB is more precise than Jolpica (it marks them as lapped)
res.loc[res["position_text"] == "NC", "outcome"] = "Not classified"

res["finished"] = res["outcome"].str.startswith("Finished")
res["is_win"] = res["position"].eq(1)
res["is_podium"] = res["position"].le(3)
res["positions_gained"] = np.where(res["finished"], res["grid"] - res["position"], np.nan)

# ---------- laps (only Jolpica has full lap-by-lap data)
laps = jolpica("lap")
laps = laps[laps["number"].notna() & laps["position"].notna() & (laps["is_deleted"] == "f")]
laps = laps.merge(res[["session_entry_id", "race_id", "year", "round", "driver_id"]],
                  on="session_entry_id")
laps["lap_ms"] = (pd.to_timedelta(laps["time"]).dt.total_seconds() * 1000).round()
laps = laps.rename(columns={"number": "lap"})
laps = laps[["race_id", "year", "round", "driver_id", "lap", "position", "lap_ms"]]
laps = laps.astype({"lap": int, "position": int}).sort_values(["race_id", "driver_id", "lap"])
laps["race_ms"] = laps.groupby(["race_id", "driver_id"])["lap_ms"].cumsum()

# ---------- pit stops (F1DB, 1994+)
pits = f1db("races-pit-stops")[["raceId", "driverId", "stop", "lap", "timeMillis"]]
pits.columns = ["race_id", "driver_id", "stop", "lap", "duration_ms"]

# ---------- standings after each round (F1DB)
standings = f1db("races-driver-standings")[["raceId", "year", "round", "driverId", "points", "positionNumber"]]
standings.columns = ["race_id", "year", "round", "driver_id", "points", "position"]
standings["driver"] = standings["driver_id"].map(drivers.set_index("id")["name"])

# ============================================================ OpenF1 (2023+)
of1 = RAW / "openf1"
sessions = pd.DataFrame(json.loads((of1 / "race_sessions.json").read_text()))
sessions["date"] = pd.to_datetime(sessions["date_start"].str[:10])

# match each OpenF1 session to an F1DB race of the same year within +-1 day
cand = sessions[["session_key", "year", "date"]].merge(races[["race_id", "year", "date"]], on="year",
                                                        suffixes=("", "_race"))
cand = cand[(cand["date"] - cand["date_race"]).abs() <= pd.Timedelta(days=1)]
session_race = cand[["session_key", "race_id"]].drop_duplicates("session_key")


def read_openf1(endpoint):
    frames = []
    for key in session_race["session_key"]:
        path = of1 / f"{endpoint}_{key}.json"
        if path.exists():
            data = json.loads(path.read_text())
            if data:
                frames.append(pd.DataFrame(data))
    return pd.concat(frames, ignore_index=True).merge(session_race, on="session_key")


of_drivers = read_openf1("drivers")
of_drivers["number"] = of_drivers["driver_number"].astype(str)
of_drivers["team_colour"] = "#" + of_drivers["team_colour"].str.upper()
res = res.merge(of_drivers[["race_id", "number", "team_colour", "headshot_url"]].drop_duplicates(["race_id", "number"]),
                on=["race_id", "number"], how="left")

stints = read_openf1("stints")
stints["number"] = stints["driver_number"].astype(str)
stints = stints.merge(res[["race_id", "number", "driver_id"]], on=["race_id", "number"])
stints = stints[["race_id", "driver_id", "stint_number", "compound", "lap_start", "lap_end", "tyre_age_at_start"]]
stints = stints.dropna(subset=["lap_start", "lap_end"])

weather = read_openf1("weather")
weather = (weather.groupby("race_id")
           .agg(air_temp=("air_temperature", "mean"), track_temp=("track_temperature", "mean"),
                humidity=("humidity", "mean"), wind=("wind_speed", "mean"), rain=("rainfall", "max"))
           .round(1).reset_index())
weather["rain"] = weather["rain"] > 0
races = races.merge(weather, on="race_id", how="left")

# ============================================================ team colours
# 1) OpenF1 official colour for that race (2023+)
# 2) Jolpica primary_color for current teams
# 3) a hand-picked classic livery colour for the big historic teams
# 4) otherwise a neutral colour based on the team name
CLASSIC = {
    "ferrari": "#DC0000", "mclaren": "#FF8000", "williams": "#1868DB", "lotus": "#C9A227",
    "red-bull": "#3671C6", "tyrrell": "#2A52BE", "renault": "#FFD12E", "brabham": "#2E9E6B",
    "sauber": "#8B9DC3", "mercedes": "#27F4D2", "minardi": "#7A7A7A", "ligier": "#3A6FD8",
    "arrows": "#FF7F50", "toro-rosso": "#3B4CC0", "benetton": "#3CB371", "jordan": "#F2D200",
    "haas": "#B6BABD", "alfa-romeo": "#A50F2D", "force-india": "#FF9DD2", "brm": "#6B8E23",
    "march": "#E36C0A", "lola": "#C0392B", "aston-martin": "#229971", "toyota": "#E8E8E8",
    "alpine": "#0093CC", "cooper": "#2F8F6F", "bar": "#C0C0C0", "honda": "#F5F5F5",
    "jaguar": "#0B6E4F", "alphatauri": "#5E8FAA", "prost": "#4169E1", "lotus-f1": "#B8860B",
    "marussia": "#9B2335", "maserati": "#B22222", "bmw-sauber": "#6CA0DC", "matra": "#1E90FF",
    "toleman": "#4FB0C6", "caterham": "#0E7C3A", "stewart": "#DADADA", "brawn": "#C6FF00",
    "racing-point": "#F596C8", "kick-sauber": "#52E252", "racing-bulls": "#6692FF",
    "vanwall": "#1F5E3B", "virgin": "#C8102E", "super-aguri": "#D3D3D3", "manor": "#E10600",
    "audi": "#FF2D00", "cadillac": "#AAAAAD",
}
FALLBACK = ["#8D99AE", "#A3B18A", "#B5838D", "#6D9DC5", "#C9ADA7", "#9A8C98", "#84A59D", "#B9A44C"]

jol_colours = jolpica("team").dropna(subset=["primary_color"]).set_index("name")["primary_color"]
res["colour"] = res["team_colour"]
res["colour"] = res["colour"].fillna(res["team"].map(jol_colours).where(res["year"] >= 2024))
res["colour"] = res["colour"].fillna(res["team_id"].map(CLASSIC))
res["colour"] = res["colour"].fillna(res["team_id"].map(lambda t: FALLBACK[sum(map(ord, t)) % len(FALLBACK)]))

# ============================================================ track shapes from the SVGs
def svg_points(svg_file, n=400):
    """Sample n evenly spaced points along the track path of an F1DB svg."""
    d = re.search(r'\sd="([^"]+)"', svg_file.read_text()).group(1)
    path = parse_path(d)
    t = np.linspace(0, 1, 3000)
    pts = np.array([path.point(x) for x in t])
    dist = np.r_[0, np.cumsum(np.abs(np.diff(pts)))]        # arc length
    even = np.interp(np.linspace(0, dist[-1], n), dist, np.arange(len(pts)))
    pts = pts[np.round(even).astype(int)]
    return pts.real, -pts.imag                                 # svg y axis points down


track_rows = []
for svg in sorted((RAW / "f1db" / "circuits").glob("*.svg")):
    x, y = svg_points(svg)
    track_rows.append(pd.DataFrame({"layout_id": svg.stem, "i": range(len(x)), "x": x.round(1), "y": y.round(1)}))
tracks = pd.concat(track_rows, ignore_index=True)

# ============================================================ circuit summary
done = races[races["race_id"].isin(res["race_id"])]
winners = res[res["is_win"]]
summary = done.groupby("circuit_id").agg(races=("race_id", "count"), first_year=("year", "min"),
                                         last_year=("year", "max")).reset_index()
top_winner = (winners.merge(done[["race_id", "circuit_id"]], on="race_id")
              .groupby(["circuit_id", "driver"]).size().rename("wins").reset_index()
              .sort_values("wins", ascending=False).drop_duplicates("circuit_id"))
summary = summary.merge(top_winner.rename(columns={"driver": "top_winner", "wins": "top_winner_wins"}),
                        on="circuit_id", how="left")
pole = res[res["grid"] == 1].merge(done[["race_id", "circuit_id"]], on="race_id")
summary = summary.merge(pole.groupby("circuit_id")["is_win"].mean().rename("pole_win_rate").round(3),
                        on="circuit_id", how="left")

this_year = races["year"].max()
circuits = circuits.merge(summary, left_on="id", right_on="circuit_id")
circuits["on_calendar"] = circuits["id"].isin(races.loc[races["year"] == this_year, "circuit_id"])
circuits = circuits[["id", "name", "full_name", "type", "direction", "place", "country", "latitude",
                     "longitude", "length", "turns", "races", "first_year", "last_year",
                     "top_winner", "top_winner_wins", "pole_win_rate", "on_calendar"]]

# races: add winner + flags the app uses to decide what can be shown
races = races[races["race_id"].isin(res["race_id"])]
races = races.merge(winners.drop_duplicates("race_id")[["race_id", "driver", "team"]].rename(columns={"driver": "winner", "team": "winner_team"}),
                    on="race_id", how="left")
races["has_laps"] = races["race_id"].isin(laps["race_id"].unique())
races["has_stints"] = races["race_id"].isin(stints["race_id"].unique())

results = res[["race_id", "year", "round", "position_order", "driver_id", "driver", "abbr", "number", "nationality", "age",
               "team_id", "team", "engine", "tyre", "colour", "headshot_url", "grid", "position",
               "position_text", "points", "laps", "time", "gap", "laps_down", "pit_stops", "retired_reason",
               "outcome", "finished", "is_win", "is_podium", "positions_gained"]]

# ============================================================ drivers (career totals)
career = drivers.rename(columns={
    "totalRaceStarts": "starts", "totalRaceWins": "wins", "totalPodiums": "podiums",
    "totalPolePositions": "poles", "totalChampionshipWins": "titles", "totalPoints": "points"})
career["nationality"] = career["nationalityCountryId"].map(countries)
span = results.groupby("driver_id").agg(first_year=("year", "min"), last_year=("year", "max"),
                                        avg_finish=("position", "mean"),
                                        dnf_rate=("finished", lambda f: 1 - f.mean()))
# the colour of the team a driver raced for most often
main_colour = results.groupby("driver_id")["colour"].agg(lambda c: c.value_counts().index[0])
career = career.merge(span, left_on="id", right_index=True)
career["colour"] = career["id"].map(main_colour)
career["decade"] = (career["first_year"] // 10 * 10).astype(str) + "s"
career["win_rate"] = (career["wins"] / career["starts"]).round(4)
career = career[career["starts"] > 0]
career = career[["id", "name", "abbreviation", "nationality", "dateOfBirth", "starts", "wins", "podiums",
                 "poles", "titles", "points", "first_year", "last_year", "decade", "win_rate",
                 "avg_finish", "dnf_rate", "colour"]].rename(columns={"id": "driver_id", "abbreviation": "abbr",
                                                                    "dateOfBirth": "born"})

# ============================================================ save
tables = {"drivers": career, "circuits": circuits, "races": races, "results": results, "laps": laps, "pit_stops": pits,
          "standings": standings, "stints": stints, "tracks": tracks}
for name, table in tables.items():
    table.to_csv(OUT / f"{name}.csv", index=False)
    print(f"{name:<10} {len(table):>8} rows")

print("\nraces with lap data:", races["has_laps"].sum(), "| with tyre stints:", races["has_stints"].sum())
print("results without a colour:", results["colour"].isna().sum())
print("missing values in results:\n", results.isna().sum()[lambda s: s > 0].to_string())
