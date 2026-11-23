import json

import pandas as pd

from .sources import OPENF1, openf1


def match_sessions(races):
    """OpenF1 session -> F1DB race of the same year within ±1 day (sources date some races a day apart)."""
    sessions = pd.DataFrame(json.loads((OPENF1 / "race_sessions.json").read_text()))
    sessions["date"] = pd.to_datetime(sessions["date_start"].str[:10])
    cand = sessions[["session_key", "year", "date"]].merge(races[["race_id", "year", "date"]], on="year",
                                                            suffixes=("", "_race"))
    cand = cand[(cand["date"] - cand["date_race"]).abs() <= pd.Timedelta(days=1)]
    return cand[["session_key", "race_id"]].drop_duplicates("session_key")


def add_driver_info(res, session_race):
    drivers = openf1("drivers", session_race)
    drivers["number"] = drivers["driver_number"].astype(str)
    drivers["team_colour"] = "#" + drivers["team_colour"].str.upper()
    return res.merge(drivers[["race_id", "number", "team_colour", "headshot_url"]].drop_duplicates(["race_id", "number"]),
                     on=["race_id", "number"], how="left")


def load_stints(res, session_race):
    stints = openf1("stints", session_race)
    stints["number"] = stints["driver_number"].astype(str)
    stints = stints.merge(res[["race_id", "number", "driver_id"]], on=["race_id", "number"])
    stints = stints[["race_id", "driver_id", "stint_number", "compound", "lap_start", "lap_end", "tyre_age_at_start"]]
    return stints.dropna(subset=["lap_start", "lap_end"])


def add_weather(races, session_race):
    weather = openf1("weather", session_race)
    weather = (weather.groupby("race_id")
               .agg(air_temp=("air_temperature", "mean"), track_temp=("track_temperature", "mean"),
                    humidity=("humidity", "mean"), wind=("wind_speed", "mean"), rain=("rainfall", "max"))
               .round(1).reset_index())
    weather["rain"] = weather["rain"] > 0
    return races.merge(weather, on="race_id", how="left")
