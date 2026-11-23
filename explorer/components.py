from dash import dcc, html

from .data import YEAR_MAX, YEAR_MIN

GRAPH_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}

MAP_NOTE = "Hover a race in the list to find it on the map, or a circuit to find its races. Click either to open the race."


def graph(id_, **kw):
    return dcc.Graph(id=id_, config=GRAPH_CONFIG, **kw)


def card(*children, **kw):
    return html.Div(list(children), className="card", **kw)


def note(text):
    return html.P(text, className="note")


def stat(value, label):
    return html.Div([html.Div(value, className="v"), html.Div(label, className="l")], className="stat")


def table_head(*cols):
    """A column is a label, or (label, tooltip)."""
    return html.Thead(html.Tr([html.Th(c[0], title=c[1]) if isinstance(c, tuple) else html.Th(c) for c in cols]))


def filter_box(label, control, grow=False):
    return html.Div([html.Label(label, className="title"), control], className="filter grow" if grow else "filter")


def year_slider(id_, start=1950):
    marks = {y: str(y) for y in range(1950, YEAR_MAX + 1, 10)}
    marks[YEAR_MAX] = str(YEAR_MAX)
    return dcc.RangeSlider(id=id_, min=YEAR_MIN, max=YEAR_MAX, step=1, value=[start, YEAR_MAX], marks=marks,
                           tooltip={"placement": "bottom"}, allowCross=False)


def driver_link(driver_id, name, src):
    return html.B(name, id={"type": "driver-link", "id": driver_id, "src": src}, n_clicks=0,
                  className="driver-link", title="Open driver page")


def team_link(team_id, name, src):
    return html.B(name, id={"type": "team-link", "id": team_id, "src": src}, n_clicks=0, className="driver-link",
                  title="Open team page")


def back_header(prefix):
    return html.Div([html.Button("← Back", id=f"{prefix}-back", className="close-btn"),
                     html.Div(id=f"{prefix}-head")], className="card head-card")


def circuits_map_card(prefix):
    # no scroll zoom: on a long page the mouse wheel should scroll the page
    return card(html.H3("Circuits raced at"),
                html.Div([dcc.Graph(id=f"{prefix}-map", config={**GRAPH_CONFIG, "scrollZoom": False},
                                    clear_on_unhover=True),
                          html.Div(id=f"{prefix}-map-label", className="map-label")], className="map-wrap"),
                note(MAP_NOTE))


def profile_head(badge, title, sub, stats):
    return html.Div([
        badge,
        html.Div([
            html.Div([html.H2(title), html.Div(" · ".join(sub), className="sub")], className="circuit-head"),
            html.Div(stats, className="stats"),
        ], className="driver-head-text"),
    ], className="driver-head")


def year_span(first, last):
    return f"{first}" + (f"–{last}" if last != first else "")
