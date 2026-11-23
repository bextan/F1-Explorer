import plotly.graph_objects as go
import plotly.io as pio

BG = "#15151e"
PANEL = "#1e1e2a"
GRID = "#2b2b3c"
TEXT = "#ececf1"
MUTED = "#9a9aae"
RED = "#e10600"

pio.templates["f1"] = go.layout.Template(layout=dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Titillium Web, Segoe UI, sans-serif", color=TEXT, size=13),
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
    hoverlabel=dict(bgcolor=PANEL, bordercolor=GRID, font=dict(color=TEXT)),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=50, r=20, t=50, b=40),
))
pio.templates.default = "plotly_dark+f1"

TYPE_COLOURS = {"Race": RED, "Street": "#ffd12e", "Road": "#27f4d2"}
TYRE_COLOURS = {"SOFT": "#ff3333", "MEDIUM": "#ffd12e", "HARD": "#f0f0f0",
                "INTERMEDIATE": "#43b02a", "WET": "#0067ad", "UNKNOWN": "#777777"}
OUTCOME_COLOURS = {
    "Finished": "#2a9d8f", "Finished (lapped)": "#8ecae6", "Not classified": "#c9ada7",
    "DNF - mechanical": "#e76f51", "DNF - accident": "#f4a261",
    "Disqualified": "#6c757d", "Did not start": "#495057",
}
PALETTE = ["#e10600", "#27f4d2", "#ffd12e", "#ff8000", "#6692ff", "#c77dff"]


def empty(message, height=300):
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(color=MUTED, size=15))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=height)
    return fig


def teammate_dash(df, team_col="team"):
    return df.groupby(team_col).cumcount().map(lambda i: "solid" if i == 0 else "dot")
