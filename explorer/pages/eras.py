from dash import Input, Output, callback, html

from .. import charts
from ..components import card, filter_box, graph, note, year_slider
from ..data import results

layout = html.Div([
    html.Div([filter_box("Seasons", year_slider("era-years"), grow=True)], className="filters"),
    html.Div([
        card(html.H3("How do races end?"), graph("outcomes"), note("Share of all starters per season.")),
        card(html.H3("Whose engines win?"), graph("engines"),
             note("Share of race wins by engine manufacturer (3-season rolling window).")),
        card(html.H3("Grid slot vs. finishing position"), graph("gridmap"),
             note("Each column sums to 100%: read a column to see where drivers starting from "
                  "that slot usually end up (finishers only).")),
        card(html.H3("Are drivers getting younger?"), graph("ages")),
    ], className="grid-2"),
])


@callback(
    Output("outcomes", "figure"), Output("engines", "figure"), Output("gridmap", "figure"),
    Output("ages", "figure"),
    Input("era-years", "value"),
)
def show_eras(years):
    r = results[results["year"].between(*years)]
    return charts.outcome_area(r), charts.engine_stream(r), charts.grid_heatmap(r), charts.age_violin(r)
