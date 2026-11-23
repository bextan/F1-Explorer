from types import SimpleNamespace

import pandas as pd

from .sources import f1db


def lookups():
    country_table = f1db("countries")
    gp_table = f1db("grands-prix").set_index("id")
    return SimpleNamespace(
        country_table=country_table,
        countries=country_table.set_index("id")["name"],
        gp_table=gp_table,
        drivers=f1db("drivers"),
        constructors=f1db("constructors").set_index("id")["name"],
        engines=f1db("engine-manufacturers").set_index("id")["name"],
        tyres=f1db("tyre-manufacturers").set_index("id")["name"],
    )


def load_circuits(lk):
    circuits = f1db("circuits").rename(columns={"fullName": "full_name", "placeName": "place"})
    circuits["country"] = circuits["countryId"].map(lk.countries)
    circuits["country_iso3"] = circuits["countryId"].map(lk.country_table.set_index("id")["alpha3Code"])
    circuits["type"] = circuits["type"].str.title()
    circuits["direction"] = circuits["direction"].str.replace("_", " ").str.lower()
    return circuits


def load_races(lk):
    races = f1db("races")[["id", "year", "round", "date", "grandPrixId", "officialName", "circuitId",
                           "circuitLayoutId", "laps", "distance", "courseLength"]]
    races.columns = ["race_id", "year", "round", "date", "gp_id", "official_name", "circuit_id",
                     "layout_id", "laps", "distance_km", "lap_length_km"]
    races["date"] = pd.to_datetime(races["date"])
    races["gp"] = races["gp_id"].map(lk.gp_table["name"]) + " GP"
    races["gp_abbr"] = races["gp_id"].map(lk.gp_table["abbreviation"])
    return races


def load_results(lk, races):
    res = f1db("races-race-results")
    # DNQ / DNPQ / DNP never took part in the race
    res = res[~res["positionText"].isin(["DNQ", "DNPQ", "DNP"])].copy()
    res = res.rename(columns={
        "raceId": "race_id", "driverId": "driver_id", "constructorId": "team_id",
        "positionNumber": "position", "positionText": "position_text", "gridPositionNumber": "grid",
        "driverNumber": "number", "reasonRetired": "retired_reason", "pitStops": "pit_stops",
        "gapLaps": "laps_down", "positionDisplayOrder": "position_order",
    })
    drivers = lk.drivers.set_index("id")
    res["driver"] = res["driver_id"].map(drivers["name"])
    res["abbr"] = res["driver_id"].map(drivers["abbreviation"])
    res["nationality"] = res["driver_id"].map(drivers["nationalityCountryId"]).map(lk.countries)
    res["team"] = res["team_id"].map(lk.constructors)
    res["engine"] = res["engineManufacturerId"].map(lk.engines)
    res["tyre"] = res["tyreManufacturerId"].map(lk.tyres)
    res["number"] = pd.to_numeric(res["number"], errors="coerce").astype("Int64").astype(str)
    res["points"] = res["points"].fillna(0)

    dob = pd.to_datetime(res["driver_id"].map(drivers["dateOfBirth"]))
    res = res.merge(races[["race_id", "date"]], on="race_id")
    res["age"] = ((res["date"] - dob).dt.days / 365.25).round(1)
    return res


def load_pit_stops():
    pits = f1db("races-pit-stops")[["raceId", "driverId", "stop", "lap", "timeMillis"]]
    pits.columns = ["race_id", "driver_id", "stop", "lap", "duration_ms"]
    return pits


def load_standings(lk):
    standings = f1db("races-driver-standings")[["raceId", "year", "round", "driverId", "points", "positionNumber"]]
    standings.columns = ["race_id", "year", "round", "driver_id", "points", "position"]
    standings["driver"] = standings["driver_id"].map(lk.drivers.set_index("id")["name"])
    return standings


def load_teams(lk):
    teams = f1db("constructors").rename(columns={
        "id": "team_id", "fullName": "full_name", "totalChampionshipWins": "titles", "totalRaceEntries": "entries",
        "totalRaceStarts": "starts", "totalRaceWins": "wins", "total1And2Finishes": "one_twos",
        "totalPodiums": "podiums", "totalPolePositions": "poles", "totalPoints": "points",
        "bestChampionshipPosition": "best_championship"})
    teams["country"] = teams["countryId"].map(lk.countries)
    return teams[["team_id", "name", "full_name", "country", "titles", "entries", "starts", "wins", "one_twos",
                  "podiums", "poles", "points", "best_championship"]]


def load_team_standings():
    cs = f1db("races-constructor-standings")
    cs = cs[cs["round"] == cs.groupby("year")["round"].transform("max")]
    team_standings = cs[["year", "constructorId", "positionNumber", "points", "championshipWon"]]
    team_standings.columns = ["year", "team_id", "position", "points", "champion"]
    # a team with two engines in a season (McLaren-Ford and McLaren-Serenissima in 1966) has two rows
    return team_standings.sort_values(["year", "position"]).drop_duplicates(["year", "team_id"])
