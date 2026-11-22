from pathlib import Path

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

results = results.merge(races[["race_id", "circuit_id"]], on="race_id")
YEAR_MIN, YEAR_MAX = int(races["year"].min()), int(races["year"].max())
LAST_FULL_SEASON = int(standings.groupby("year")["round"].max().pipe(
    lambda s: s[s.index < YEAR_MAX].index.max()))

# championship position at the end of each season (for career lines)
last_round = standings.groupby("year")["round"].transform("max")
season_final = standings[standings["round"] == last_round]

driver_names = drivers.set_index("driver_id")["name"].to_dict()

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
driver_options = [{"label": f"{r.name} ({r.first_year}–{r.last_year})", "value": r.driver_id}
                  for r in drivers.sort_values("starts", ascending=False).itertuples()]
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

app.layout = html.Div([
    dcc.Store(id="selection", data=None),
    dcc.Store(id="country", data=None),    # ISO-3 code of the clicked country
    dcc.Store(id="map-hover"),             # dummy output of the clientside hover highlight
    html.Div([html.H1(["F1 ", html.Span("EXPLORER")]),
              html.P(f"Every Formula 1 Grand Prix, {YEAR_MIN}–{YEAR_MAX}")], className="header"),
    html.Div([
        # the tabs are only the menu; all pages stay in the page so links between them keep working
        dcc.Tabs(id="tabs", value="circuits", className="tabs", children=[
            dcc.Tab(label=name.title(), value=name, className="tab", selected_className="tab--selected")
            for name in PAGES]),
        *[html.Div(content, id=f"page-{name}", className="tab-page") for name, content in PAGES.items()],
    ], className="page"),
    html.Div([
        "Data: ", html.A("F1DB", href="https://github.com/f1db/f1db"), " (results, circuits, track layouts) · ",
        html.A("Jolpica F1", href="https://github.com/jolpica/jolpica-f1"), " (lap-by-lap data) · ",
        html.A("OpenF1", href="https://openf1.org"), " (team colours, tyres, weather 2023+)",
    ], className="footer"),
])


@app.callback([Output(f"page-{name}", "className") for name in PAGES], Input("tabs", "value"))
def switch_page(tab):
    return ["tab-page" if name == tab else "tab-page hidden" for name in PAGES]


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
    prevent_initial_call=True,
)
def select_circuit(map_click, item_clicks, race_clicks, matrix_click, close):
    trigger = ctx.triggered_id
    if trigger == "close":
        return None, no_update
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
            html.Td([html.B(r.driver), html.Br(), html.Span(r.team, className="team")]),
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
    header = html.Tr([html.Td("")] + [html.Td(html.B(n)) for n in sel["name"]])
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


if __name__ == "__main__":
    app.run(debug=False, port=8050)
