from dash import ClientsideFunction, Input, Output, callback, clientside_callback, html
import pandas as pd

from .. import charts
from ..components import (back_header, card, circuits_map_card, graph, note, profile_head, stat, table_head,
                          team_link, year_span)
from ..data import career_circuits, circuit_info, drivers, races, results, season_final

SEASONS_NOTE = ("Gold, silver and bronze dots are championship top-three finishes. The bars show how every race "
                "of the season ended; hover a season for a full summary.")

layout = html.Div([
    back_header("driver"),
    html.Div([
        circuits_map_card("driver"),
        card(html.H3("Every race"), html.Div(id="driver-races", className="table-scroll dr-scroll")),
    ], className="driver-row"),
    html.Div([
        card(html.H3("Season by season"), graph("driver-seasons"), note(SEASONS_NOTE)),
        card(html.H3("Teams"), html.Div(id="driver-teams")),
    ], className="driver-row-2"),
])


def result_span(r):
    if r.finished and pd.notna(r.position):
        return html.Span(f"P{int(r.position)}", className="win" if r.is_win else ("pod" if r.is_podium else ""))
    text = r.position_text if isinstance(r.position_text, str) and not r.position_text.isdigit() else r.outcome
    return html.Span(text, className="out", title=r.outcome)


def map_attrs(r, map_id):
    """data-* attributes that let assets/map_hover.js find the row's circuit on the map."""
    c = circuit_info.loc[r.circuit_id]
    return {"data-circuit": r.circuit_id, "data-lon": str(c["longitude"]), "data-lat": str(c["latitude"]),
            "data-label": f"{r.year} {r.gp} · {c['name']}", "data-map": map_id}


def race_row(r, n):
    return html.Tr([
        html.Td(str(r.year), className="pos"),
        html.Td(className="bar", style={"background": r.colour}),
        html.Td([html.Div(r.gp), html.Span(r.team, className="team")]),
        html.Td(f"P{int(r.grid)}" if pd.notna(r.grid) else "pit", className="team"),
        html.Td(result_span(r)),
        html.Td(f"{r.points:g}" if r.points else ""),
    ], id={"type": "driver-race", "id": int(r.race_id), "n": n}, n_clicks=0, className="dr-race",
        title="Click to open this race", **map_attrs(r, "driver-map"))


def races_table(res):
    head = table_head("Year", "", ("Race / team", "Click a race to open it"),
                      ("Start", "Grid position at the start"), ("Finish", "Finishing position, or why the car retired"),
                      ("Pts", "Championship points scored"))
    return html.Table([head, html.Tbody([race_row(r, n) for n, r in enumerate(res.itertuples())])],
                      className="classification")


def team_list(res, did):
    teams = res.groupby(["team_id", "team"]).agg(
        first=("year", "min"), last=("year", "max"), races=("race_id", "nunique"), wins=("is_win", "sum"),
        podiums=("is_podium", "sum"), colour=("colour", lambda c: c.value_counts().index[0]))
    teams = teams.sort_values(["first", "last"]).reset_index()
    return html.Div([
        html.Div([
            html.Div(className="team-bar", style={"background": t.colour}),
            html.Div([team_link(t.team_id, t.team, f"driver-{did}"),
                      html.Div(year_span(t.first, t.last), className="team")]),
            html.Div(f"{t.races} races · {t.wins} wins · {t.podiums} podiums", className="team right"),
        ], className="team-item") for t in teams.itertuples()])


def driver_head(d, res, champ):
    photos = res["headshot_url"].dropna()
    photo = html.Img(src=photos.iloc[0], className="driver-photo") if len(photos) else \
        html.Div(d["abbr"] if isinstance(d["abbr"], str) else d["name"][:3].upper(), className="driver-photo initials",
                 style={"background": d["colour"]})
    born = pd.to_datetime(d["born"], errors="coerce")
    numbers = ", ".join(f"#{int(n)}" for n in res["number"].dropna().astype(int).unique()[:4])
    sub = [d["nationality"]]
    if pd.notna(born):
        sub.append(f"born {born:%d %b %Y}")
    sub.append(f"{d['first_year']}–{d['last_year']}")
    if numbers:
        sub.append(numbers)

    best_champ = f"P{int(champ['position'].min())}" if len(champ) else "–"
    return profile_head(photo, d["name"], sub, [
        stat(res["year"].nunique(), "seasons"),
        stat(int(d["starts"]), "starts"),
        stat(int(d["wins"]), "wins"),
        stat(int(d["podiums"]), "podiums"),
        stat(int(d["poles"]), "poles"),
        stat(int(d["titles"]), "titles"),
        stat(f"{d['points']:g}", "points"),
        stat(f"{d['win_rate']:.1%}", "win rate"),
        stat(f"{d['avg_finish']:.1f}" if pd.notna(d["avg_finish"]) else "–", "avg finish"),
        stat(f"{d['dnf_rate']:.0%}", "DNF rate"),
        stat(best_champ, "best championship"),
    ])


@callback(
    Output("driver-head", "children"), Output("driver-map", "figure"), Output("driver-races", "children"),
    Output("driver-seasons", "figure"), Output("driver-teams", "children"),
    Input("driver", "data"),
)
def show_driver(did):
    if not did:
        e = charts.empty("")
        return "", e, "", e, ""
    d = drivers.set_index("driver_id").loc[did]
    res = results[results["driver_id"] == did].merge(races[["race_id", "date", "gp"]], on="race_id")
    res = res.sort_values("date", ascending=False)
    champ = season_final[season_final["driver_id"] == did].sort_values("year")

    return driver_head(d, res, champ), charts.career_map(career_circuits(res)), races_table(res), \
        charts.career_seasons(res, champ), team_list(res, did)


clientside_callback(ClientsideFunction("map", "driverHover"), Output("driver-map-hover", "data"),
                    Input("driver-map", "hoverData"))
