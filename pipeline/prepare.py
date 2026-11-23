"""Combines F1DB, Jolpica and OpenF1 into the tables in data/processed/. Run: python -m pipeline.prepare"""
from . import f1db, jolpica, openf1
from .colours import add_team_colours
from .sources import OUT
from .summaries import RESULT_COLUMNS, circuit_summary, driver_careers, finish_races
from .tracks import load_tracks


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lk = f1db.lookups()

    races = f1db.load_races(lk)
    res = f1db.load_results(lk, races)
    res = jolpica.add_outcomes(res)
    laps = jolpica.load_laps(res)

    session_race = openf1.match_sessions(races)
    res = openf1.add_driver_info(res, session_race)
    stints = openf1.load_stints(res, session_race)
    races = openf1.add_weather(races, session_race)

    res = add_team_colours(res, jolpica.team_colours())
    results = res[RESULT_COLUMNS]

    teams = f1db.load_teams(lk)
    world = lk.country_table[["alpha3Code", "name"]].dropna().rename(columns={"alpha3Code": "iso3"})

    tables = {
        "countries": world,
        "teams": teams[teams["team_id"].isin(results["team_id"])],
        "team_standings": f1db.load_team_standings(),
        "drivers": driver_careers(lk.drivers, results, lk.countries),
        "circuits": circuit_summary(f1db.load_circuits(lk), races, res),
        "races": finish_races(races, res, laps, stints),
        "results": results,
        "laps": laps,
        "pit_stops": f1db.load_pit_stops(),
        "standings": f1db.load_standings(lk),
        "stints": stints,
        "tracks": load_tracks(),
    }
    for name, table in tables.items():
        table.to_csv(OUT / f"{name}.csv", index=False)
        print(f"{name:<10} {len(table):>8} rows")

    races = tables["races"]
    print("\nraces with lap data:", races["has_laps"].sum(), "| with tyre stints:", races["has_stints"].sum())
    print("results without a colour:", results["colour"].isna().sum())
    print("missing values in results:\n", results.isna().sum()[lambda s: s > 0].to_string())


if __name__ == "__main__":
    main()
