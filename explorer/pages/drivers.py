from dash import Input, Output, State, callback, dcc, html, no_update
import pandas as pd

from .. import charts
from ..components import card, driver_link, filter_box, graph
from ..data import driver_names, driver_options, drivers, season_final

layout = html.Div([
    html.Div([
        filter_box("Compare drivers (type to search, or click a dot)",
                   dcc.Dropdown(id="drivers", options=driver_options, multi=True,
                                value=["lewis-hamilton", "max-verstappen", "michael-schumacher"]), grow=True),
    ], className="filters"),
    html.Div([
        card(graph("driver-scatter")),
        card(html.H3("Career path"), graph("career"), html.Div(id="driver-table")),
    ], className="grid-2"),
])

COMPARE_ROWS = [("Seasons", None, None), ("Starts", "starts", "{:.0f}"), ("Wins", "wins", "{:.0f}"),
                ("Podiums", "podiums", "{:.0f}"), ("Poles", "poles", "{:.0f}"),
                ("Titles", "titles", "{:.0f}"), ("Win rate", "win_rate", "{:.1%}"),
                ("Avg finish", "avg_finish", "{:.1f}"), ("DNF rate", "dnf_rate", "{:.0%}")]


@callback(Output("drivers", "value"), Input("driver-scatter", "clickData"), State("drivers", "value"),
          prevent_initial_call=True)
def add_driver_from_click(click, current):
    if not click or "customdata" not in click["points"][0]:
        return no_update
    name = click["points"][0]["customdata"][0]
    did = drivers.loc[drivers["name"] == name, "driver_id"].iloc[0]
    current = current or []
    return [d for d in current if d != did] if did in current else (current + [did])[-6:]


def compare_table(selected):
    sel = drivers.set_index("driver_id").loc[[d for d in selected if d in set(drivers["driver_id"])]]
    rows = [html.Tr([html.Td("")] + [html.Td(driver_link(did, n, "compare")) for did, n in sel["name"].items()])]
    for label, col, fmt in COMPARE_ROWS:
        if col is None:
            cells = [f"{r.first_year}–{r.last_year}" for r in sel.itertuples()]
        else:
            cells = [fmt.format(v) if pd.notna(v) else "–" for v in sel[col]]
        rows.append(html.Tr([html.Td(label, className="team")] + [html.Td(c) for c in cells]))
    return html.Table(html.Tbody(rows), className="classification", style={"marginTop": "10px"})


@callback(
    Output("driver-scatter", "figure"), Output("career", "figure"), Output("driver-table", "children"),
    Input("drivers", "value"),
)
def show_drivers(selected):
    selected = selected or []
    path = season_final[season_final["driver_id"].isin(selected)]
    path = path.set_index("driver_id").loc[[d for d in selected if d in set(path["driver_id"])]].reset_index()
    colours = drivers.set_index("driver_id")["colour"].to_dict()
    return charts.driver_scatter(drivers, selected), charts.career_lines(path, driver_names, colours), \
        compare_table(selected)
