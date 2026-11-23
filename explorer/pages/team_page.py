from dash import ClientsideFunction, Input, Output, callback, clientside_callback, dcc, html
import numpy as np
import pandas as pd

from .. import charts
from ..components import (back_header, card, circuits_map_card, driver_link, graph, note, profile_head, stat,
                          year_span)
from ..data import career_circuits, circuits, races, results, team_standings, teams
from .driver_page import SEASONS_NOTE

layout = html.Div([
    back_header("team"),
    html.Div([
        circuits_map_card("team"),
        card(html.Div([html.H3("Races"),
                       dcc.Dropdown(id="team-season", clearable=False, searchable=False,
                                    className="season-pick")], className="card-title-row"),
             html.Div(id="team-races", className="table-scroll dr-scroll")),
    ], className="driver-row"),
    html.Div([
        card(html.H3("Season by season"), graph("team-seasons"), note(SEASONS_NOTE + " Each car counts separately.")),
        card(html.H3("Drivers"), html.Div(id="team-drivers", className="table-scroll dr-scroll")),
    ], className="driver-row-2"),
])


def team_head(t, res, colour):
    first, last = int(res["year"].min()), int(res["year"].max())
    engines = res["engine"].value_counts().index[:4].tolist()
    sub = [t["full_name"]] if t["full_name"] != t["name"] else []
    sub += [t["country"], f"{first}–{last}" if first != last else str(first)]
    if engines:
        sub.append("engines: " + ", ".join(engines))
    initials = "".join(w[0] for w in t["name"].split()[:3]).upper() if " " in t["name"] else t["name"][:3].upper()
    badge = html.Div(initials, className="driver-photo initials team-badge", style={"background": colour})
    n_races = res["race_id"].nunique()
    return profile_head(badge, t["name"], sub, [
        stat(res["year"].nunique(), "seasons"),
        stat(n_races, "races"),
        stat(int(t["wins"]), "wins"),
        stat(int(t["podiums"]), "podiums"),
        stat(int(t["one_twos"]), "1–2 finishes"),
        stat(int(t["poles"]), "poles"),
        stat(int(t["titles"]), "constructors' titles"),
        stat(f"{t['points']:g}", "points"),
        stat(f"{t['wins'] / n_races:.1%}" if n_races else "–", "races won"),
        stat(f"P{int(t['best_championship'])}" if pd.notna(t["best_championship"]) else "–",
             "best championship"),
        stat(res["driver_id"].nunique(), "drivers"),
    ])


def driver_list(res, tid):
    ds = res.groupby(["driver_id", "driver"]).agg(
        first=("year", "min"), last=("year", "max"), races=("race_id", "nunique"), wins=("is_win", "sum"),
        podiums=("is_podium", "sum")).reset_index().sort_values(["races", "wins"], ascending=False)
    return html.Div([
        html.Div([
            html.Div([driver_link(d.driver_id, d.driver, f"team-{tid}"),
                      html.Div(year_span(d.first, d.last), className="team")]),
            html.Div(f"{d.races} races · {d.wins} wins · {d.podiums} podiums", className="team right"),
        ], className="team-item") for d in ds.itertuples()])


@callback(
    Output("team-head", "children"), Output("team-map", "figure"), Output("team-seasons", "figure"),
    Output("team-drivers", "children"), Output("team-season", "options"), Output("team-season", "value"),
    Input("team", "data"),
)
def show_team(tid):
    if not tid:
        e = charts.empty("")
        return "", e, e, "", [], None
    t = teams.loc[tid]
    res = results[results["team_id"] == tid]
    champ = team_standings[team_standings["team_id"] == tid].sort_values("year")
    colour = res.sort_values("year")["colour"].iloc[-1]

    seasons = sorted(res["year"].unique(), reverse=True)
    options = [{"label": "All seasons", "value": "all"}] + [{"label": str(y), "value": int(y)} for y in seasons]
    return team_head(t, res, colour), charts.career_map(career_circuits(res)), \
        charts.career_seasons(res, champ, unit="car results"), driver_list(res, tid), options, "all"


@callback(Output("team-races-data", "data"), Input("team", "data"), Input("team-season", "value"))
def team_races(tid, season):
    if not tid or season is None:
        return None
    res = results[results["team_id"] == tid]
    if season != "all":
        res = res[res["year"] == season]
    place = circuits[["id", "name", "latitude", "longitude"]].rename(columns={"id": "circuit_id", "name": "cname"})
    res = res.merge(races[["race_id", "date", "gp"]], on="race_id").merge(place, on="circuit_id")
    res = res.sort_values(["date", "position_order"], ascending=[False, True])

    # Ferrari has 1100+ races, too many to render as dash components: only the data is sent and
    # assets/map_hover.js builds the table. Column-wise on purpose; a loop over the races took ~4 s.
    ok = res["finished"] & res["position"].notna()
    pt = res["position_text"].astype("string")
    other = pt.where(pt.notna() & ~pt.str.isdigit().fillna(False), res["outcome"])
    text = np.where(ok, "P" + res["position"].fillna(0).astype(int).astype(str), other)
    cls = np.select([ok & res["is_win"], ok & res["is_podium"], ok], ["win", "pod", ""], "out")
    res["car"] = list(zip(res["driver"].str.split().str[-1], text, cls, res["outcome"]))
    g = res.groupby("race_id", sort=False).agg(
        year=("year", "first"), colour=("colour", "first"), gp=("gp", "first"), cars=("car", list),
        points=("points", "sum"), circuit=("circuit_id", "first"), cname=("cname", "first"),
        lon=("longitude", "first"), lat=("latitude", "first"))
    return [{"race": int(r.Index), "year": int(r.year), "colour": r.colour, "gp": r.gp, "cars": r.cars,
             "points": f"{r.points:g}" if r.points else "", "circuit": r.circuit, "lon": str(r.lon),
             "lat": str(r.lat), "label": f"{r.year} {r.gp} · {r.cname}"} for r in g.itertuples()]


clientside_callback(ClientsideFunction("map", "teamHover"), Output("team-map-hover", "data"),
                    Input("team-map", "hoverData"))
clientside_callback(ClientsideFunction("map", "renderTeamRaces"), Output("team-races-render", "data"),
                    Input("team-races-data", "data"))
