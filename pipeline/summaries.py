RESULT_COLUMNS = [
    "race_id",
    "year",
    "round",
    "position_order",
    "driver_id",
    "driver",
    "abbr",
    "number",
    "nationality",
    "age",
    "team_id",
    "team",
    "engine",
    "tyre",
    "colour",
    "headshot_url",
    "grid",
    "position",
    "position_text",
    "points",
    "laps",
    "time",
    "gap",
    "laps_down",
    "pit_stops",
    "retired_reason",
    "outcome",
    "finished",
    "is_win",
    "is_podium",
    "positions_gained",
]


def circuit_summary(circuits, races, res):
    done = races[races["race_id"].isin(res["race_id"])]
    winners = res[res["is_win"]]
    summary = (
        done.groupby("circuit_id")
        .agg(
            races=("race_id", "count"),
            first_year=("year", "min"),
            last_year=("year", "max"),
        )
        .reset_index()
    )
    top_winner = (
        winners.merge(done[["race_id", "circuit_id"]], on="race_id")
        .groupby(["circuit_id", "driver"])
        .size()
        .rename("wins")
        .reset_index()
        .sort_values("wins", ascending=False)
        .drop_duplicates("circuit_id")
    )
    summary = summary.merge(
        top_winner.rename(columns={"driver": "top_winner", "wins": "top_winner_wins"}),
        on="circuit_id",
        how="left",
    )
    pole = res[res["grid"] == 1].merge(done[["race_id", "circuit_id"]], on="race_id")
    summary = summary.merge(
        pole.groupby("circuit_id")["is_win"].mean().rename("pole_win_rate").round(3),
        on="circuit_id",
        how="left",
    )

    this_year = races["year"].max()
    circuits = circuits.merge(summary, left_on="id", right_on="circuit_id")
    circuits["on_calendar"] = circuits["id"].isin(
        races.loc[races["year"] == this_year, "circuit_id"]
    )
    return circuits[
        [
            "id",
            "name",
            "full_name",
            "type",
            "direction",
            "place",
            "country",
            "country_iso3",
            "latitude",
            "longitude",
            "length",
            "turns",
            "races",
            "first_year",
            "last_year",
            "top_winner",
            "top_winner_wins",
            "pole_win_rate",
            "on_calendar",
        ]
    ]


def finish_races(races, res, laps, stints):
    races = races[races["race_id"].isin(res["race_id"])]
    winners = res[res["is_win"]].drop_duplicates("race_id")[
        ["race_id", "driver", "team"]
    ]
    races = races.merge(
        winners.rename(columns={"driver": "winner", "team": "winner_team"}),
        on="race_id",
        how="left",
    )
    races["has_laps"] = races["race_id"].isin(laps["race_id"].unique())
    races["has_stints"] = races["race_id"].isin(stints["race_id"].unique())
    return races


def driver_careers(drivers, results, countries):
    career = drivers.rename(
        columns={
            "totalRaceStarts": "starts",
            "totalRaceWins": "wins",
            "totalPodiums": "podiums",
            "totalPolePositions": "poles",
            "totalChampionshipWins": "titles",
            "totalPoints": "points",
        }
    )
    career["nationality"] = career["nationalityCountryId"].map(countries)
    span = results.groupby("driver_id").agg(
        first_year=("year", "min"),
        last_year=("year", "max"),
        avg_finish=("position", "mean"),
        dnf_rate=("finished", lambda f: 1 - f.mean()),
    )
    main_colour = results.groupby("driver_id")["colour"].agg(
        lambda c: c.value_counts().index[0]
    )
    career = career.merge(span, left_on="id", right_index=True)
    career["colour"] = career["id"].map(main_colour)
    career["decade"] = (career["first_year"] // 10 * 10).astype(str) + "s"
    career["win_rate"] = (career["wins"] / career["starts"]).round(4)
    career = career[career["starts"] > 0]
    return career[
        [
            "id",
            "name",
            "abbreviation",
            "nationality",
            "dateOfBirth",
            "starts",
            "wins",
            "podiums",
            "poles",
            "titles",
            "points",
            "first_year",
            "last_year",
            "decade",
            "win_rate",
            "avg_finish",
            "dnf_rate",
            "colour",
        ]
    ].rename(columns={"id": "driver_id", "abbreviation": "abbr", "dateOfBirth": "born"})
