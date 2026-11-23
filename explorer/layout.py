from dash import dcc, html

from .data import YEAR_MAX, YEAR_MIN, search_options
from .pages import TABS, driver_page, race, team_page  # noqa: F401  (importing registers the callbacks)
from . import navigation  # noqa: F401

STORES = [
    dcc.Store(id="selection", data=None),
    dcc.Store(id="country", data=None),
    dcc.Store(id="nav", data=[]),
    dcc.Store(id="driver", data=None),
    dcc.Store(id="team", data=None),
    dcc.Store(id="race-click"),
    dcc.Store(id="map-hover"),
    dcc.Store(id="driver-map-hover"),
    dcc.Store(id="team-map-hover"),
    dcc.Store(id="team-races-data"),
    dcc.Store(id="team-races-render"),
]

header = html.Div([
    html.H1(["F1 ", html.Span("EXPLORER")]),
    html.P(f"Every Formula 1 Grand Prix, {YEAR_MIN}–{YEAR_MAX}"),
    dcc.Dropdown(id="global-search", options=search_options, placeholder="🔍 Search a driver or team…",
                 searchable=True, clearable=True, className="driver-search"),
], className="header")

footer = html.Div([
    "Data: ", html.A("F1DB", href="https://github.com/f1db/f1db"), " (results, circuits, track layouts) · ",
    html.A("Jolpica F1", href="https://github.com/jolpica/jolpica-f1"), " (lap-by-lap data) · ",
    html.A("OpenF1", href="https://openf1.org"), " (team colours, tyres, weather 2023+)",
], className="footer")

# the tabs are only the menu: every page stays mounted so links between them keep working
pages = html.Div([
    dcc.Tabs(id="tabs", value="circuits", className="tabs", children=[
        dcc.Tab(label=name.title(), value=name, className="tab", selected_className="tab--selected")
        for name in TABS]),
    *[html.Div(content, id=f"page-{name}", className="tab-page") for name, content in TABS.items()],
    html.Div(driver_page.layout, id="page-driver", className="tab-page hidden"),
    html.Div(team_page.layout, id="page-team", className="tab-page hidden"),
], className="page")

layout = html.Div([*STORES, header, pages, footer])
