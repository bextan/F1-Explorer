from dash import ALL, ClientsideFunction, Input, Output, State, callback, clientside_callback, ctx, dcc, html, no_update
import pandas as pd

from .. import charts
from ..components import GRAPH_CONFIG, card, filter_box, graph, note, stat, year_slider
from ..data import (YEAR_MAX, circuits, countries, race_info, races, races_per_country, results)

layout = html.Div([
    html.Div([
        filter_box("Search circuit, city or country",
                   dcc.Input(id="search", type="text", placeholder="e.g. Monza, Italy, street...",
                             className="search", debounce=False), grow=True),
        filter_box("Circuit type",
                   dcc.Checklist(id="types", options=["Race", "Street", "Road"], value=["Race", "Street", "Road"],
                                 inline=True, className="checks")),
        filter_box("Show",
                   dcc.Checklist(id="calendar", options=[{"label": f"Only {YEAR_MAX} calendar", "value": "on"}],
                                 value=[], className="checks")),
        filter_box("Seasons", year_slider("years"), grow=True),
    ], className="filters"),

    html.Div(id="circuits-body", className="circuits-body", children=[
        html.Div([
            html.Div(id="map-hint", className="map-hint"),
            dcc.Graph(id="map", config=GRAPH_CONFIG, responsive=True, className="map-graph",
                      clear_on_unhover=True),
            html.Div([html.Button("×", id="country-close", className="x-btn", title="Close"),
                      html.Div(id="country-content", className="cp-content")],
                     id="country-panel", className="country-panel hidden"),
            html.Div(id="map-list", className="map-list"),
        ], id="map-pane", className="map-pane"),

        html.Div([
            html.Div([html.Button("× Back to map", id="close", className="close-btn"),
                      html.Div(id="circuit-head")], className="card head-card"),
            html.Div([
                html.Div([
                    card(html.H3("Race"), dcc.Dropdown(id="race", clearable=False, searchable=True),
                         html.Div(id="weather", className="weather")),
                    card(html.H3("Classification"), html.Div(id="classification", className="table-scroll")),
                ]),
                card(graph("replay")),
            ], className="race-row"),
            card(graph("lapchart")),
            card(html.H3("Tyre strategy"), graph("tyres")),
            card(html.H3("Where do winners start here?"), graph("history"),
                 note("Each dot is one race won at this circuit. The higher the dots, the more "
                      "qualifying matters on this track.")),
        ], className="detail-pane"),
    ]),
])


def filtered_circuits(search, types, years, calendar):
    in_range = races[races["year"].between(*years)].groupby("circuit_id").size().rename("races_period")
    c = circuits.merge(in_range, left_on="id", right_index=True)
    c = c[c["type"].isin(types or [])]
    if "on" in (calendar or []):
        c = c[c["on_calendar"]]
    if search:
        s = search.strip().lower()
        text = (c["name"] + " " + c["full_name"] + " " + c["place"] + " " + c["country"] + " " + c["type"]).str.lower()
        c = c[text.str.contains(s, regex=False)]
    return c


def filtered_races(c, years):
    r = races[races["year"].between(*years)]
    return r.merge(c[["id", "name", "country_iso3"]].rename(columns={"id": "circuit_id", "name": "circuit"}),
                   on="circuit_id")


def country_stats(c, years):
    r = filtered_races(c, years)
    g = r.groupby("country_iso3").agg(races=("race_id", "size"), circuits=("circuit_id", "nunique"),
                                       first=("year", "min"), last=("year", "max"))
    out = countries.merge(g, left_on="iso3", right_index=True, how="left")
    cols = ["races", "circuits", "first", "last"]
    out[cols] = out[cols].fillna(0).astype(int)
    out["ever"] = out["iso3"].map(races_per_country).fillna(0).astype(int)
    return out


@callback(
    Output("map", "figure"), Output("map-hint", "children"), Output("map-list", "children"),
    Input("search", "value"), Input("types", "value"), Input("years", "value"), Input("calendar", "value"),
    Input("selection", "data"), Input("country", "data"),
)
def update_map(search, types, years, calendar, selection, country):
    c = filtered_circuits(search, types, years, calendar)
    selected = None
    if selection:
        selected = circuits.set_index("id").loc[selection["circuit"]].copy()
        selected["id"] = selection["circuit"]
    hint = (f"{len(c)} circuits · click a circuit to open it, or a country to list its races"
            if selection is None else f"{len(c)} circuits match")
    items = [html.Div([html.Span(r.name), html.Small(f"{r.races_period} races")],
                      id={"type": "circuit-item", "id": r.id}, n_clicks=0,
                      className="item active" if selection and r.id == selection["circuit"] else "item")
             for r in c.sort_values("races_period", ascending=False).itertuples()]
    return charts.circuit_map(c, selected, country_stats(c, years), country), hint, items


clientside_callback(ClientsideFunction("map", "hover"), Output("map-hover", "data"), Input("map", "hoverData"))


@callback(
    Output("country", "data"),
    Input("map", "clickData"), Input("country-close", "n_clicks"),
    prevent_initial_call=True,
)
def select_country(map_click, close):
    if ctx.triggered_id == "country-close":
        return None if close else no_update
    point = (map_click or {}).get("points", [{}])[0]
    # only country shapes have a "location"; circuit bubbles are handled by select_circuit
    return point.get("location") or no_update


@callback(
    Output("country-content", "children"), Output("country-panel", "className"), Output("map-pane", "className"),
    Input("country", "data"), Input("search", "value"), Input("types", "value"), Input("years", "value"),
    Input("calendar", "value"), Input("race", "value"),
)
def country_panel(iso3, search, types, years, calendar, race_id):
    if not iso3:
        return [], "country-panel hidden", "map-pane"
    name = countries.set_index("iso3")["name"].get(iso3, iso3)
    r = filtered_races(filtered_circuits(search, types, years, calendar), years)
    r = r[r["country_iso3"] == iso3].sort_values("date", ascending=False)

    if len(r):
        n_circ = r["circuit_id"].nunique()
        sub = (f"{len(r)} races · {n_circ} circuit{'s' if n_circ > 1 else ''} · "
               f"{r['year'].min()}–{r['year'].max()} · click a race to open it")
        body = [html.Div([
                    html.Span(str(x.year), className="yr"),
                    html.Div([html.Div(x.gp),
                              html.Small(x.circuit + (f" · won by {x.winner}" if isinstance(x.winner, str) else ""))]),
                ], id={"type": "country-race", "id": int(x.race_id)}, n_clicks=0,
                    className="race-item active" if x.race_id == race_id else "race-item")
                for x in r.itertuples()]
    else:
        ever = int(races_per_country.get(iso3, 0))
        sub = ""
        body = html.P(f"No races in {name} with the current filters ({ever} all-time)." if ever else
                      f"No Formula 1 Grand Prix has ever been held in {name}.", className="empty")

    content = [html.Div([html.H3(name), html.Small(sub)], className="cp-head"),
               html.Div(body, className="cp-list")]
    return content, "country-panel", "map-pane has-country"


@callback(
    Output("selection", "data"), Output("tabs", "value"),
    Input("map", "clickData"), Input({"type": "circuit-item", "id": ALL}, "n_clicks"),
    Input({"type": "country-race", "id": ALL}, "n_clicks"),
    Input("matrix", "clickData"), Input("close", "n_clicks"),
    Input({"type": "driver-race", "id": ALL, "n": ALL}, "n_clicks"), Input("driver-map", "clickData"),
    Input("team-map", "clickData"), Input("race-click", "data"),
    State("driver", "data"), State("team", "data"),
    prevent_initial_call=True,
)
def select_circuit(map_click, item_clicks, race_clicks, matrix_click, close, driver_race_clicks, driver_map_click,
                   team_map_click, race_click, driver, team):
    trigger = ctx.triggered_id
    if trigger == "close":
        return None, no_update
    if trigger in ("driver-map", "team-map"):
        # open the driver's / team's latest race at the clicked circuit
        click, col, who = (driver_map_click, "driver_id", driver) if trigger == "driver-map" else \
            (team_map_click, "team_id", team)
        if not click or not who:
            return no_update, no_update
        cid = click["points"][0]["customdata"][0]
        mine = results[(results[col] == who) & (results["circuit_id"] == cid)]
        race_id = int(mine.sort_values("year")["race_id"].iloc[-1])
        return {"circuit": cid, "race": race_id}, "circuits"
    if trigger == "race-click" and race_click:
        race_id = int(race_click["race"])
        return {"circuit": race_info.at[race_id, "circuit_id"], "race": race_id}, "circuits"
    if isinstance(trigger, dict) and trigger["type"] == "driver-race" and ctx.triggered[0]["value"]:
        return {"circuit": race_info.at[trigger["id"], "circuit_id"], "race": trigger["id"]}, "circuits"
    if trigger == "map" and map_click:
        point = map_click["points"][0]
        if "customdata" not in point:
            return no_update, no_update
        return {"circuit": point["customdata"][0], "race": None}, no_update
    if trigger == "matrix" and matrix_click:
        race_id = int(matrix_click["points"][0]["customdata"])
        circuit = races.loc[races["race_id"] == race_id, "circuit_id"].iloc[0]
        return {"circuit": circuit, "race": race_id}, "circuits"
    # list items re-render with n_clicks=0, so only react to a real click
    if isinstance(trigger, dict) and ctx.triggered[0]["value"]:
        if trigger["type"] == "country-race":
            circuit = races.loc[races["race_id"] == trigger["id"], "circuit_id"].iloc[0]
            return {"circuit": circuit, "race": trigger["id"]}, no_update
        return {"circuit": trigger["id"], "race": None}, no_update
    return no_update, no_update


@callback(Output("circuits-body", "className"), Input("selection", "data"))
def toggle_detail(selection):
    return "circuits-body open" if selection else "circuits-body"


@callback(
    Output("circuit-head", "children"), Output("race", "options"), Output("race", "value"),
    Output("history", "figure"),
    Input("selection", "data"), Input("years", "value"),
)
def circuit_header(selection, years):
    if not selection:
        return "", [], None, charts.empty("")
    cid = selection["circuit"]
    c = circuits.set_index("id").loc[cid]
    here = races[races["circuit_id"] == cid].sort_values("date", ascending=False)

    head = [
        html.Div([html.H2(c["full_name"]), html.Div(f"{c['place']}, {c['country']}", className="sub")],
                 className="circuit-head"),
        html.Div([
            stat(c["type"], "type"),
            stat(f"{c['length']:.3f} km", "lap length"),
            stat(int(c["turns"]), "turns"),
            stat(c["direction"], "direction"),
            stat(int(c["races"]), f"races {int(c['first_year'])}–{int(c['last_year'])}"),
            stat(f"{c['top_winner']} ({int(c['top_winner_wins'])})", "most wins"),
            stat(f"{c['pole_win_rate']:.0%}" if pd.notna(c["pole_win_rate"]) else "–", "pole → win"),
        ], className="stats"),
    ]

    options = [{"label": f"{r.year} {r.gp}" + ("" if r.has_laps else "  (results only)"), "value": r.race_id}
               for r in here.itertuples()]
    value = selection.get("race") or int(here["race_id"].iloc[0])

    w = results[(results["circuit_id"] == cid) & results["is_win"] & results["year"].between(*years)]
    return head, options, value, charts.winners_history(w)
