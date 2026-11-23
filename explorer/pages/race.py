from dash import Input, Output, callback, html
import pandas as pd

from .. import charts
from ..components import driver_link, table_head
from ..data import circuits, laps, pits, races, results, stints, tracks


def classification_table(res):
    rows = []
    for r in res.sort_values("position_order").itertuples():
        if r.finished and pd.notna(r.grid) and pd.notna(r.position):
            diff = int(r.grid - r.position)
            gain = html.Span(f"▲{diff}" if diff > 0 else (f"▼{-diff}" if diff < 0 else "–"),
                             className="up" if diff > 0 else ("down" if diff < 0 else ""))
        else:
            gain = ""
        if r.position_order == 1 and isinstance(r.time, str):
            result = r.time
        elif r.finished:
            result = r.gap if isinstance(r.gap, str) else (f"+{int(r.laps_down)} lap" if pd.notna(r.laps_down) else "")
        else:
            reason = r.retired_reason if isinstance(r.retired_reason, str) else r.outcome
            result = html.Span(f"{r.position_text} · {reason}", className="out")
        photo = html.Img(src=r.headshot_url) if isinstance(r.headshot_url, str) else ""
        grid = f"P{int(r.grid)}" if pd.notna(r.grid) else "pit lane"
        rows.append(html.Tr([
            html.Td(r.position_text, className="pos"),
            html.Td(className="bar", style={"background": r.colour}),
            html.Td(photo),
            html.Td([driver_link(r.driver_id, r.driver, "race"),
                     html.Br(),html.Span(r.team, id={"type": "team-link", "id": r.team_id, "src": f"race-{r.driver_id}"},
                                          n_clicks=0, className="team driver-link", title="Open team page")]),
            html.Td(grid, className="team"),
            html.Td(gain),
            html.Td(result),
            html.Td(f"{r.points:g}" if r.points else ""),
        ]))
    head = table_head(("Pos", "Finishing position"), "", "", ("Driver / team", "Click a name to open its page"),
                      ("Start", "Grid position at the start"),
                      ("Gained", "Places gained (▲) or lost (▼) from start to finish"),
                      ("Time / gap", "Winner's race time, gap to the winner, or why the car retired"),
                      ("Pts", "Championship points scored"))
    return html.Table([head, html.Tbody(rows)], className="classification")


def race_facts(race):
    facts = [html.Span(["📅 ", html.B(race["date"].strftime("%d %b %Y"))]),
             html.Span(["🏁 ", html.B(f"{int(race['laps'])} laps"), f" · {race['distance_km']:.0f} km"])]
    if pd.notna(race.get("air_temp")):
        facts += [html.Span(["🌡 air ", html.B(f"{race['air_temp']:.0f}°C"), " track ",
                             html.B(f"{race['track_temp']:.0f}°C")]),
                  html.Span(["💧 ", html.B(f"{race['humidity']:.0f}%")]),
                  html.Span(["🌧 ", html.B("rain" if race["rain"] else "dry")])]
    return facts


@callback(
    Output("classification", "children"), Output("replay", "figure"), Output("lapchart", "figure"),
    Output("tyres", "figure"), Output("weather", "children"),
    Input("race", "value"),
)
def show_race(race_id):
    if race_id is None:
        e = charts.empty("")
        return "", e, e, e, ""
    race = races.set_index("race_id").loc[race_id]
    res = results[results["race_id"] == race_id]
    race_laps = laps[laps["race_id"] == race_id]
    race_pits = pits[pits["race_id"] == race_id]
    race_stints = stints[stints["race_id"] == race_id]
    track = tracks[tracks["layout_id"] == race["layout_id"]].sort_values("i")
    direction = circuits.set_index("id").at[race["circuit_id"], "direction"]

    return (classification_table(res),
            charts.race_replay(race, track, res, race_laps, direction),
            charts.lap_chart(res, race_laps, race_pits),
            charts.tyre_strategy(res, race_stints),
            race_facts(race))
