import os
from pathlib import Path

import numpy as np
import pandas as pd
from dash import ALL, ClientsideFunction, Dash, Input, Output, State, ctx, dcc, html, no_update

import charts

# ------------------------------------------------------------------ data
D = str(Path(__file__).parent / "data" / "processed") + "/"
circuits = pd.read_csv(D + "circuits.csv")
races = pd.read_csv(D + "races.csv", parse_dates=["date"])
results = pd.read_csv(D + "results.csv")
laps = pd.read_csv(D + "laps.csv")
pits = pd.read_csv(D + "pit_stops.csv")
standings = pd.read_csv(D + "standings.csv")
stints = pd.read_csv(D + "stints.csv")
tracks = pd.read_csv(D + "tracks.csv")
drivers = pd.read_csv(D + "drivers.csv")
countries = pd.read_csv(D + "countries.csv", keep_default_na=False)  # keep "NA" (Namibia) as text
# plotly's world map draws a few disputed areas as separate shapes; without them they'd be holes in the land
DISPUTED = ["XAP", "XHT", "XBT", "XAC", "XIT", "XJK"]
countries = pd.concat([countries, pd.DataFrame({"iso3": DISPUTED, "name": "Disputed area"})], ignore_index=True)

results = results.merge(races[["race_id", "circuit_id"]], on="race_id")
YEAR_MIN, YEAR_MAX = int(races["year"].min()), int(races["year"].max())
LAST_FULL_SEASON = int(standings.groupby("year")["round"].max().pipe(
    lambda s: s[s.index < YEAR_MAX].index.max()))

# championship position at the end of each season (for career lines)
last_round = standings.groupby("year")["round"].transform("max")
season_final = standings[standings["round"] == last_round]

driver_names = drivers.set_index("driver_id")["name"].to_dict()
driver_options = [{"label": f"{r.name} ({r.first_year}–{r.last_year})", "value": r.driver_id}
                  for r in drivers.sort_values("starts", ascending=False).itertuples()]
circuit_info = circuits.set_index("id")
race_info = races.set_index("race_id")

teams = pd.read_csv(D + "teams.csv").set_index("team_id")
team_standings = pd.read_csv(D + "team_standings.csv")
team_years = results.groupby("team_id")["year"].agg(["min", "max"])

# one search box for both: values are "d:<driver_id>" or "t:<team_id>"
search_options = [{"label": f"🏎 {r['name']} · team ({team_years.at[tid, 'min']}–{team_years.at[tid, 'max']})",
                   "value": f"t:{tid}"} for tid, r in teams.sort_values("entries", ascending=False).iterrows()] + \
                 [{"label": f"👤 {o['label']}", "value": f"d:{o['value']}"} for o in driver_options]

app = Dash(__name__, title="F1 Explorer", suppress_callback_exceptions=True,
           external_stylesheets=["https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;700;900&display=swap"])
server = app.server

GRAPH_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def graph(id_, **kw):
    return dcc.Graph(id=id_, config=GRAPH_CONFIG, **kw)


def stat(value, label):
    return html.Div([html.Div(value, className="v"), html.Div(label, className="l")], className="stat")


def year_slider(id_, start=1950):
    marks = {y: str(y) for y in range(1950, YEAR_MAX + 1, 10)}
    marks[YEAR_MAX] = str(YEAR_MAX)
    return dcc.RangeSlider(id=id_, min=YEAR_MIN, max=YEAR_MAX, step=1, value=[start, YEAR_MAX], marks=marks,
                           tooltip={"placement": "bottom"}, allowCross=False)


# ------------------------------------------------------------------ layout: circuits tab
circuits_tab = html.Div([
    html.Div([
        html.Div([html.Label("Search circuit, city or country", className="title"),
                  dcc.Input(id="search", type="text", placeholder="e.g. Monza, Italy, street...",
                            className="search", debounce=False)], className="filter grow"),
        html.Div([html.Label("Circuit type", className="title"),
                  dcc.Checklist(id="types", options=["Race", "Street", "Road"], value=["Race", "Street", "Road"],
                                inline=True, className="checks")], className="filter"),
        html.Div([html.Label("Show", className="title"),
                  dcc.Checklist(id="calendar", options=[{"label": f"Only {YEAR_MAX} calendar", "value": "on"}],
                                value=[], className="checks")], className="filter"),
        html.Div([html.Label("Seasons", className="title"), year_slider("years")], className="filter grow"),
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
                    html.Div([html.H3("Race"), dcc.Dropdown(id="race", clearable=False, searchable=True),
                              html.Div(id="weather", className="weather")], className="card"),
                    html.Div([html.H3("Classification"), html.Div(id="classification", className="table-scroll")],
                             className="card"),
                ]),
                html.Div([graph("replay")], className="card"),
            ], className="race-row"),
            html.Div([graph("lapchart")], className="card"),
            html.Div([html.H3("Tyre strategy"), graph("tyres")], className="card"),
            html.Div([html.H3("Where do winners start here?"), graph("history"),
                      html.P("Each dot is one race won at this circuit. The higher the dots, the more "
                             "qualifying matters on this track.", className="note")], className="card"),
        ], className="detail-pane"),
    ]),
])

# ------------------------------------------------------------------ layout: seasons tab
seasons_tab = html.Div([
    html.Div([
        html.Div([html.Label("Season", className="title"),
                  dcc.Dropdown(id="season", options=sorted(races["year"].unique(), reverse=True),
                               value=LAST_FULL_SEASON, clearable=False)], className="filter"),
        html.Div(id="season-summary", className="filter grow"),
    ], className="filters"),
    html.Div([html.H3("Championship fight"), graph("champ")], className="card"),
    html.Div([html.H3("Every result of the season"), graph("matrix"),
              html.P("Click any cell to open that race on the circuit page.", className="note")], className="card"),
])

# ------------------------------------------------------------------ layout: drivers tab
drivers_tab = html.Div([
    html.Div([
        html.Div([html.Label("Compare drivers (type to search, or click a dot)", className="title"),
                  dcc.Dropdown(id="drivers", options=driver_options, multi=True,
                               value=["lewis-hamilton", "max-verstappen", "michael-schumacher"])],
                 className="filter grow"),
    ], className="filters"),
    html.Div([
        html.Div([graph("driver-scatter")], className="card"),
        html.Div([html.H3("Career path"), graph("career"), html.Div(id="driver-table")], className="card"),
    ], className="grid-2"),
])

# ------------------------------------------------------------------ layout: eras tab
eras_tab = html.Div([
    html.Div([html.Div([html.Label("Seasons", className="title"), year_slider("era-years")],
                       className="filter grow")], className="filters"),
    html.Div([
        html.Div([html.H3("How do races end?"), graph("outcomes"),
                  html.P("Share of all starters per season.", className="note")], className="card"),
        html.Div([html.H3("Whose engines win?"), graph("engines"),
                  html.P("Share of race wins by engine manufacturer (3-season rolling window).", className="note")],
                 className="card"),
        html.Div([html.H3("Grid slot vs. finishing position"), graph("gridmap"),
                  html.P("Each column sums to 100%: read a column to see where drivers starting from "
                         "that slot usually end up (finishers only).", className="note")], className="card"),
        html.Div([html.H3("Are drivers getting younger?"), graph("ages")], className="card"),
    ], className="grid-2"),
])

PAGES = {"circuits": circuits_tab, "seasons": seasons_tab, "drivers": drivers_tab, "eras": eras_tab}

# ------------------------------------------------------------------ layout: driver page (opened over any tab)
SEASONS_NOTE = ("Gold, silver and bronze dots are championship top-three finishes. The bars show how every race "
                "of the season ended; hover a season for a full summary.")

driver_page = html.Div([
    html.Div([html.Button("← Back", id="driver-back", className="close-btn"),
              html.Div(id="driver-head")], className="card head-card"),
    html.Div([
        html.Div([html.H3("Circuits raced at"),
                  # no scroll zoom: on a long page the mouse wheel should scroll the page, not the map
                  html.Div([dcc.Graph(id="driver-map", config={**GRAPH_CONFIG, "scrollZoom": False},
                                      clear_on_unhover=True),
                            html.Div(id="driver-map-label", className="map-label")], className="map-wrap"),
                  html.P("Hover a race in the list to find it on the map, or a circuit to find its races. "
                         "Click either to open the race.", className="note")], className="card"),
        html.Div([html.H3("Every race"), html.Div(id="driver-races", className="table-scroll dr-scroll")],
                 className="card"),
    ], className="driver-row"),
    html.Div([
        html.Div([html.H3("Season by season"), graph("driver-seasons"), html.P(SEASONS_NOTE, className="note")],
                 className="card"),
        html.Div([html.H3("Teams"), html.Div(id="driver-teams")], className="card"),
    ], className="driver-row-2"),
])

# ------------------------------------------------------------------ layout: team page (same idea as the driver page)
team_page = html.Div([
    html.Div([html.Button("← Back", id="team-back", className="close-btn"),
              html.Div(id="team-head")], className="card head-card"),
    html.Div([
        html.Div([html.H3("Circuits raced at"),
                  html.Div([dcc.Graph(id="team-map", config={**GRAPH_CONFIG, "scrollZoom": False},
                                      clear_on_unhover=True),
                            html.Div(id="team-map-label", className="map-label")], className="map-wrap"),
                  html.P("Hover a race in the list to find it on the map, or a circuit to find its races. "
                         "Click either to open the race.", className="note")], className="card"),
        html.Div([html.Div([html.H3("Races"),
                            dcc.Dropdown(id="team-season", clearable=False, searchable=False,
                                         className="season-pick")], className="card-title-row"),
                  html.Div(id="team-races", className="table-scroll dr-scroll")], className="card"),
    ], className="driver-row"),
    html.Div([
        html.Div([html.H3("Season by season"), graph("team-seasons"),
                  html.P(SEASONS_NOTE + " Each car counts separately.", className="note")], className="card"),
        html.Div([html.H3("Drivers"), html.Div(id="team-drivers", className="table-scroll dr-scroll")],
                 className="card"),
    ], className="driver-row-2"),
])

app.layout = html.Div([
    dcc.Store(id="selection", data=None),
    dcc.Store(id="country", data=None),    # ISO-3 code of the clicked country
    dcc.Store(id="nav", data=[]),          # open driver/team pages, newest last: [{"kind": "team", "id": ...}, ...]
    dcc.Store(id="driver", data=None),     # driver_id shown on the driver page
    dcc.Store(id="team", data=None),       # team_id shown on the team page
    dcc.Store(id="race-click"),            # set from the browser when a row of the team's race list is clicked
    dcc.Store(id="map-hover"),             # dummy outputs of the clientside hover highlights
    dcc.Store(id="driver-map-hover"),
    dcc.Store(id="team-map-hover"),
    dcc.Store(id="team-races-data"),      # rows of the team's race list, drawn in the browser
    dcc.Store(id="team-races-render"),
    html.Div([html.H1(["F1 ", html.Span("EXPLORER")]),
              html.P(f"Every Formula 1 Grand Prix, {YEAR_MIN}–{YEAR_MAX}"),
              dcc.Dropdown(id="global-search", options=search_options,
                           placeholder="🔍 Search a driver or team…",
                           searchable=True, clearable=True, className="driver-search")], className="header"),
    html.Div([
        # the tabs are only the menu; all pages stay in the page so links between them keep working
        dcc.Tabs(id="tabs", value="circuits", className="tabs", children=[
            dcc.Tab(label=name.title(), value=name, className="tab", selected_className="tab--selected")
            for name in PAGES]),
        *[html.Div(content, id=f"page-{name}", className="tab-page") for name, content in PAGES.items()],
        html.Div(driver_page, id="page-driver", className="tab-page hidden"),
        html.Div(team_page, id="page-team", className="tab-page hidden"),
    ], className="page"),
    html.Div([
        "Data: ", html.A("F1DB", href="https://github.com/f1db/f1db"), " (results, circuits, track layouts) · ",
        html.A("Jolpica F1", href="https://github.com/jolpica/jolpica-f1"), " (lap-by-lap data) · ",
        html.A("OpenF1", href="https://openf1.org"), " (team colours, tyres, weather 2023+)",
    ], className="footer"),
])


@app.callback([Output(f"page-{name}", "className") for name in PAGES] +
              [Output("page-driver", "className"), Output("page-team", "className")],
              Input("tabs", "value"), Input("nav", "data"))
def switch_page(tab, nav):
    # a driver/team page covers the current tab; "Back" goes to the previous page, then to the tab again
    top = nav[-1]["kind"] if nav else None
    pages = ["tab-page" if name == tab and not top else "tab-page hidden" for name in PAGES]
    return pages + ["tab-page" if top == kind else "tab-page hidden" for kind in ("driver", "team")]


# ================================================================== callbacks: circuits
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
    """Races in the season range held at the circuits in `c`, with the circuit's name and country."""
    r = races[races["year"].between(*years)]
    return r.merge(c[["id", "name", "country_iso3"]].rename(columns={"id": "circuit_id", "name": "circuit"}),
                   on="circuit_id")


# races per country over all seasons, to tell "never hosted" apart from "filtered out"
ALL_TIME = races.merge(circuits[["id", "country_iso3"]], left_on="circuit_id", right_on="id") \
    .groupby("country_iso3").size()


def country_stats(c, years):
    """One row per country of the world: races and circuits under the current filters."""
    r = filtered_races(c, years)
    g = r.groupby("country_iso3").agg(races=("race_id", "size"), circuits=("circuit_id", "nunique"),
                                       first=("year", "min"), last=("year", "max"))
    out = countries.merge(g, left_on="iso3", right_index=True, how="left")
    cols = ["races", "circuits", "first", "last"]
    out[cols] = out[cols].fillna(0).astype(int)
    out["ever"] = out["iso3"].map(ALL_TIME).fillna(0).astype(int)
    return out


@app.callback(
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


app.clientside_callback(ClientsideFunction("map", "hover"), Output("map-hover", "data"), Input("map", "hoverData"))


@app.callback(
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


@app.callback(
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
        ever = int(ALL_TIME.get(iso3, 0))
        sub = ""
        body = html.P(f"No races in {name} with the current filters ({ever} all-time)." if ever else
                      f"No Formula 1 Grand Prix has ever been held in {name}.", className="empty")

    content = [html.Div([html.H3(name), html.Small(sub)], className="cp-head"),
               html.Div(body, className="cp-list")]
    return content, "country-panel", "map-pane has-country"


@app.callback(
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
    # list items re-render with n_clicks=0, only react to a real click
    if isinstance(trigger, dict) and ctx.triggered[0]["value"]:
        if trigger["type"] == "country-race":
            circuit = races.loc[races["race_id"] == trigger["id"], "circuit_id"].iloc[0]
            return {"circuit": circuit, "race": trigger["id"]}, no_update
        return {"circuit": trigger["id"], "race": None}, no_update
    return no_update, no_update


@app.callback(Output("circuits-body", "className"), Input("selection", "data"))
def toggle_detail(selection):
    return "circuits-body open" if selection else "circuits-body"


@app.callback(
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
        grid = f"P{int(r.grid)}" if pd.notna(r.grid) else "pit"
        rows.append(html.Tr([
            html.Td(r.position_text if not str(r.position_text).isdigit() else r.position_text, className="pos"),
            html.Td(className="bar", style={"background": r.colour}),
            html.Td(photo),
            html.Td([html.B(r.driver, id={"type": "driver-link", "id": r.driver_id, "src": "race"}, n_clicks=0,
                            className="driver-link", title="Open driver page"),
                     html.Br(), html.Span(r.team, id={"type": "team-link", "id": r.team_id, "src": f"race-{r.driver_id}"},
                                          n_clicks=0, className="team driver-link", title="Open team page")]),
            html.Td([html.Span(grid, className="team"), " ", gain]),
            html.Td(result),
            html.Td(f"{r.points:g}" if r.points else ""),
        ]))
    return html.Table(html.Tbody(rows), className="classification")


@app.callback(
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

    weather = [html.Span(["📅 ", html.B(race["date"].strftime("%d %b %Y"))]),
               html.Span(["🏁 ", html.B(f"{int(race['laps'])} laps"), f" · {race['distance_km']:.0f} km"])]
    if pd.notna(race.get("air_temp")):
        weather += [html.Span(["🌡 air ", html.B(f"{race['air_temp']:.0f}°C"), " track ",
                               html.B(f"{race['track_temp']:.0f}°C")]),
                    html.Span(["💧 ", html.B(f"{race['humidity']:.0f}%")]),
                    html.Span(["🌧 ", html.B("rain" if race["rain"] else "dry")])]

    return (classification_table(res),
            charts.race_replay(race, track, res, race_laps, direction),
            charts.lap_chart(res, race_laps, race_pits),
            charts.tyre_strategy(res, race_stints),
            weather)


# ================================================================== callbacks: seasons
@app.callback(
    Output("champ", "figure"), Output("matrix", "figure"), Output("season-summary", "children"),
    Input("season", "value"),
)
def show_season(year):
    st = standings[standings["year"] == year]
    res = results[results["year"] == year]
    rc = races[races["year"] == year]
    colours = res.groupby("driver_id")["colour"].agg(lambda c: c.value_counts().index[0]).to_dict()

    final = st[st["round"] == st["round"].max()].sort_values("position")
    leader = final.iloc[0]
    winners = res[res["is_win"]]["driver"].nunique()
    summary = html.Div([
        stat(leader["driver"], "champion" if year < YEAR_MAX else "leading"),
        stat(f"{leader['points']:g}", "points"),
        stat(len(rc), "races"),
        stat(winners, "different winners"),
    ], className="stats", style={"marginTop": 0})
    return charts.championship(st[st["driver_id"].isin(final["driver_id"].head(10))], colours), \
        charts.results_matrix(res, rc, st), summary


# ================================================================== callbacks: drivers
@app.callback(Output("drivers", "value"), Input("driver-scatter", "clickData"), State("drivers", "value"),
              prevent_initial_call=True)
def add_driver_from_click(click, current):
    if not click or "customdata" not in click["points"][0]:
        return no_update
    name = click["points"][0]["customdata"][0]
    did = drivers.loc[drivers["name"] == name, "driver_id"].iloc[0]
    current = current or []
    return [d for d in current if d != did] if did in current else (current + [did])[-6:]


@app.callback(
    Output("driver-scatter", "figure"), Output("career", "figure"), Output("driver-table", "children"),
    Input("drivers", "value"),
)
def show_drivers(selected):
    selected = selected or []
    path = season_final[season_final["driver_id"].isin(selected)]
    path = path.set_index("driver_id").loc[[d for d in selected if d in set(path["driver_id"])]].reset_index()

    sel = drivers.set_index("driver_id").loc[[d for d in selected if d in set(drivers["driver_id"])]]
    header = html.Tr([html.Td("")] + [
        html.Td(html.B(n, id={"type": "driver-link", "id": did, "src": "compare"}, n_clicks=0, className="driver-link",
                       title="Open driver page"))
        for did, n in sel["name"].items()])
    rows = [header]
    for label, col, fmt in [("Seasons", None, None), ("Starts", "starts", "{:.0f}"), ("Wins", "wins", "{:.0f}"),
                            ("Podiums", "podiums", "{:.0f}"), ("Poles", "poles", "{:.0f}"),
                            ("Titles", "titles", "{:.0f}"), ("Win rate", "win_rate", "{:.1%}"),
                            ("Avg finish", "avg_finish", "{:.1f}"), ("DNF rate", "dnf_rate", "{:.0%}")]:
        if col is None:
            cells = [f"{r.first_year}–{r.last_year}" for r in sel.itertuples()]
        else:
            cells = [fmt.format(v) if pd.notna(v) else "–" for v in sel[col]]
        rows.append(html.Tr([html.Td(label, className="team")] + [html.Td(c) for c in cells]))
    table = html.Table(html.Tbody(rows), className="classification", style={"marginTop": "10px"})
    return charts.driver_scatter(drivers, selected), charts.career_lines(path, driver_names, drivers.set_index("driver_id")["colour"].to_dict()), table


# ================================================================== callbacks: eras
@app.callback(
    Output("outcomes", "figure"), Output("engines", "figure"), Output("gridmap", "figure"),
    Output("ages", "figure"),
    Input("era-years", "value"),
)
def show_eras(years):
    r = results[results["year"].between(*years)]
    return charts.outcome_area(r), charts.engine_stream(r), charts.grid_heatmap(r), charts.age_violin(r)


# ================================================================== callbacks: driver + team pages
@app.callback(
    Output("nav", "data"), Output("driver", "data"), Output("team", "data"), Output("global-search", "value"),
    Input("global-search", "value"),
    # "src" keeps the ids unique when the same driver/team is linked from several places
    Input({"type": "driver-link", "id": ALL, "src": ALL}, "n_clicks"),
    Input({"type": "team-link", "id": ALL, "src": ALL}, "n_clicks"),
    Input("driver-back", "n_clicks"), Input("team-back", "n_clicks"), Input("tabs", "value"),
    Input({"type": "driver-race", "id": ALL, "n": ALL}, "n_clicks"), Input("driver-map", "clickData"),
    Input("team-map", "clickData"), Input("race-click", "data"),
    State("nav", "data"),
    prevent_initial_call=True,
)
def navigate(search, driver_links, team_links, driver_back, team_back, tab, race_clicks, driver_map, team_map,
             race_click, nav):
    nothing = (no_update,) * 4
    trigger = ctx.triggered_id
    nav = list(nav or [])
    clear_search = no_update

    def push(kind, id_):
        page = {"kind": kind, "id": id_}
        return nav if nav and nav[-1] == page else (nav + [page])[-20:]

    if trigger == "global-search":
        if not search:
            return nothing
        kind, id_ = search.split(":", 1)
        nav = push("driver" if kind == "d" else "team", id_)
        clear_search = None            # empty the box again, so the same name can be searched twice
    elif isinstance(trigger, dict) and trigger["type"] in ("driver-link", "team-link", "driver-race"):
        if not ctx.triggered[0]["value"]:      # lists re-render with n_clicks=0
            return nothing
        if trigger["type"] == "driver-race":
            nav = []                            # a race was opened on the circuits tab
        else:
            nav = push(trigger["type"].split("-")[0], trigger["id"])
    elif trigger in ("driver-back", "team-back"):
        nav = nav[:-1]
    else:                                       # another tab, or a race opened from a map / the team's list
        nav = []

    top = nav[-1] if nav else None
    driver = top["id"] if top and top["kind"] == "driver" else no_update
    team = top["id"] if top and top["kind"] == "team" else no_update
    return nav, driver, team, clear_search


def career_circuits(res):
    """One row per circuit for the career maps (driver or team results)."""
    g = res.groupby("circuit_id").agg(
        races=("race_id", "nunique"), wins=("is_win", "sum"), podiums=("is_podium", "sum"),
        best=("position", "min"), first=("year", "min"), last=("year", "max"))
    g["best"] = g["best"].map(lambda p: f"P{int(p)}" if pd.notna(p) else "–")
    return circuits[["id", "name", "place", "country", "latitude", "longitude"]].merge(g, left_on="id",
                                                                                      right_index=True)


def result_span(r):
    if r.finished and pd.notna(r.position):
        return html.Span(f"P{int(r.position)}", className="win" if r.is_win else ("pod" if r.is_podium else ""))
    text = r.position_text if isinstance(r.position_text, str) and not r.position_text.isdigit() else r.outcome
    return html.Span(text, className="out", title=r.outcome)


def map_attrs(r, map_id):
    """data-* attributes that let assets/map_hover.js find the row's circuit on the page's map."""
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


def team_link(team_id, name, src):
    return html.B(name, id={"type": "team-link", "id": team_id, "src": src}, n_clicks=0, className="driver-link",
                  title="Open team page")


@app.callback(
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
    head = html.Div([
        photo,
        html.Div([
            html.Div([html.H2(d["name"]), html.Div(" · ".join(sub), className="sub")], className="circuit-head"),
            html.Div([
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
            ], className="stats"),
        ], className="driver-head-text"),
    ], className="driver-head")

    races_table = html.Table(html.Tbody([race_row(r, n) for n, r in enumerate(res.itertuples())]),
                             className="classification")

    their_teams = res.groupby(["team_id", "team"]).agg(
        first=("year", "min"), last=("year", "max"), races=("race_id", "nunique"), wins=("is_win", "sum"),
        podiums=("is_podium", "sum"), colour=("colour", lambda c: c.value_counts().index[0]))
    their_teams = their_teams.sort_values(["first", "last"]).reset_index()
    team_list = html.Div([
        html.Div([
            html.Div(className="team-bar", style={"background": t.colour}),
            html.Div([team_link(t.team_id, t.team, f"driver-{did}"),
                      html.Div(f"{t.first}" + (f"–{t.last}" if t.last != t.first else ""), className="team")]),
            html.Div(f"{t.races} races · {t.wins} wins · {t.podiums} podiums", className="team right"),
        ], className="team-item") for t in their_teams.itertuples()])

    return head, charts.career_map(career_circuits(res)), races_table, \
        charts.career_seasons(res, champ), team_list


@app.callback(
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
    first, last = int(res["year"].min()), int(res["year"].max())

    engines = res["engine"].value_counts().index[:4].tolist()
    sub = [t["full_name"]] if t["full_name"] != t["name"] else []
    sub += [t["country"], f"{first}–{last}" if first != last else str(first)]
    if engines:
        sub.append("engines: " + ", ".join(engines))
    badge = html.Div("".join(w[0] for w in t["name"].split()[:3]).upper() if " " in t["name"] else t["name"][:3].upper(),
                     className="driver-photo initials team-badge", style={"background": colour})
    n_races = res["race_id"].nunique()
    head = html.Div([
        badge,
        html.Div([
            html.Div([html.H2(t["name"]), html.Div(" · ".join(sub), className="sub")], className="circuit-head"),
            html.Div([
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
            ], className="stats"),
        ], className="driver-head-text"),
    ], className="driver-head")

    ds = res.groupby(["driver_id", "driver"]).agg(
        first=("year", "min"), last=("year", "max"), races=("race_id", "nunique"), wins=("is_win", "sum"),
        podiums=("is_podium", "sum")).reset_index().sort_values(["races", "wins"], ascending=False)
    driver_list = html.Div([
        html.Div([
            html.Div([html.B(d.driver, id={"type": "driver-link", "id": d.driver_id, "src": f"team-{tid}"},
                             n_clicks=0, className="driver-link", title="Open driver page"),
                      html.Div(f"{d.first}" + (f"–{d.last}" if d.last != d.first else ""), className="team")]),
            html.Div(f"{d.races} races · {d.wins} wins · {d.podiums} podiums", className="team right"),
        ], className="team-item") for d in ds.itertuples()])

    seasons = sorted(res["year"].unique(), reverse=True)
    options = [{"label": "All seasons", "value": "all"}] + [{"label": str(y), "value": int(y)} for y in seasons]
    return head, charts.career_map(career_circuits(res)), \
        charts.career_seasons(res, champ, unit="car results"), driver_list, options, "all"


@app.callback(Output("team-races-data", "data"), Input("team", "data"), Input("team-season", "value"))
def team_races(tid, season):
    if not tid or season is None:
        return None
    res = results[results["team_id"] == tid]
    if season != "all":
        res = res[res["year"] == season]
    place = circuits[["id", "name", "latitude", "longitude"]].rename(columns={"id": "circuit_id", "name": "cname"})
    res = res.merge(races[["race_id", "date", "gp"]], on="race_id").merge(place, on="circuit_id")
    res = res.sort_values(["date", "position_order"], ascending=[False, True])

    # One row per race with every car of the team. Ferrari has 1100+ races, which as dash components took
    # tens of seconds to render, so only the data is sent and assets/map_hover.js builds the table in one go.
    # Everything is done column-wise; a python loop over the races took ~4 s for Ferrari.
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


app.clientside_callback(ClientsideFunction("map", "driverHover"), Output("driver-map-hover", "data"),
                        Input("driver-map", "hoverData"))
app.clientside_callback(ClientsideFunction("map", "teamHover"), Output("team-map-hover", "data"),
                        Input("team-map", "hoverData"))
app.clientside_callback(ClientsideFunction("map", "renderTeamRaces"), Output("team-races-render", "data"),
                        Input("team-races-data", "data"))


if __name__ == "__main__":
    app.run(debug=False, port=int(os.environ.get("PORT", 8050)))
