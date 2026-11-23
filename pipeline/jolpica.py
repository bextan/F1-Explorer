import numpy as np
import pandas as pd

from .sources import jolpica

STATUS_NAMES = {0: "Finished", 1: "Finished (lapped)", 10: "DNF - accident",
                11: "DNF - mechanical", 20: "Disqualified", 30: "Did not start", 40: "Did not start"}
POSITION_TEXT_OUTCOMES = {"DNF": "DNF - mechanical", "DNS": "Did not start", "DSQ": "Disqualified",
                          "EX": "Disqualified", "NC": "Not classified"}


def race_entries():
    season = jolpica("season")[["id", "year"]].rename(columns={"id": "season_id"})
    rounds = jolpica("round").merge(season, on="season_id")[["id", "year", "number"]]
    rounds.columns = ["round_id", "year", "round"]
    session = jolpica("session")
    session = session[session["type"] == "R"][["id", "round_id"]].rename(columns={"id": "session_id"})
    round_entry = jolpica("roundentry")[["id", "car_number"]].rename(columns={"id": "round_entry_id"})

    entries = (jolpica("sessionentry")[["id", "session_id", "round_entry_id", "status"]]
               .rename(columns={"id": "session_entry_id"})
               .merge(session, on="session_id")
               .merge(rounds, on="round_id")
               .merge(round_entry, on="round_entry_id"))
    entries["number"] = entries["car_number"].astype("Int64").astype(str)
    # shared cars in the 1950s give duplicate car numbers
    return entries.drop_duplicates(["year", "round", "number"])


def add_outcomes(res):
    entries = race_entries()
    res = res.merge(entries[["year", "round", "number", "status", "session_entry_id"]],
                    on=["year", "round", "number"], how="left")

    res["outcome"] = res["status"].map(STATUS_NAMES)
    res["outcome"] = res["outcome"].fillna(res["position_text"].map(POSITION_TEXT_OUTCOMES))
    res.loc[res["outcome"].isna() & (res["laps_down"].fillna(0) > 0), "outcome"] = "Finished (lapped)"
    res["outcome"] = res["outcome"].fillna("Finished")
    # F1DB's "not classified" is more precise than Jolpica, which marks them as lapped
    res.loc[res["position_text"] == "NC", "outcome"] = "Not classified"

    res["finished"] = res["outcome"].str.startswith("Finished")
    res["is_win"] = res["position"].eq(1)
    res["is_podium"] = res["position"].le(3)
    res["positions_gained"] = np.where(res["finished"], res["grid"] - res["position"], np.nan)
    return res


def load_laps(res):
    laps = jolpica("lap")
    laps = laps[laps["number"].notna() & laps["position"].notna() & (laps["is_deleted"] == "f")]
    laps = laps.merge(res[["session_entry_id", "race_id", "year", "round", "driver_id"]], on="session_entry_id")
    laps["lap_ms"] = (pd.to_timedelta(laps["time"]).dt.total_seconds() * 1000).round()
    laps = laps.rename(columns={"number": "lap"})
    laps = laps[["race_id", "year", "round", "driver_id", "lap", "position", "lap_ms"]]
    laps = laps.astype({"lap": int, "position": int}).sort_values(["race_id", "driver_id", "lap"])
    laps["race_ms"] = laps.groupby(["race_id", "driver_id"])["lap_ms"].cumsum()
    return laps


def team_colours():
    return jolpica("team").dropna(subset=["primary_color"]).set_index("name")["primary_color"]
