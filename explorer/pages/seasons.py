from dash import Input, Output, callback, dcc, html

from .. import charts
from ..components import card, filter_box, graph, note, stat
from ..data import LAST_FULL_SEASON, YEAR_MAX, races, results, standings

layout = html.Div([
    html.Div([
        filter_box("Season", dcc.Dropdown(id="season", options=sorted(races["year"].unique(), reverse=True),
                                          value=LAST_FULL_SEASON, clearable=False)),
        html.Div(id="season-summary", className="filter grow"),
    ], className="filters"),
    card(html.H3("Championship fight"), graph("champ")),
    card(html.H3("Every result of the season"), graph("matrix"),
         note("Click any cell to open that race on the circuit page.")),
])


@callback(
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
