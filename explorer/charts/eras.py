import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .theme import BG, MUTED, OUTCOME_COLOURS, RED, empty

ENGINE_COLOURS = {"Ferrari": "#e10600", "Mercedes": "#27f4d2", "Ford": "#1f6fd1", "Renault": "#ffd12e",
                  "Honda": "#f0f0f0", "Honda RBPT": "#c77dff", "Climax": "#2a9d8f", "TAG": "#ff8000",
                  "BMW": "#6692ff", "Alfa Romeo": "#a50f2d", "Other": "#555566"}
SPARE_COLOURS = ["#f4a261", "#8ecae6", "#b5838d", "#84a59d"]


def outcome_area(results):
    share = results.groupby(["year", "outcome"]).size().rename("n").reset_index()
    share["share"] = share["n"] / share.groupby("year")["n"].transform("sum") * 100
    fig = go.Figure()
    for outcome, colour in OUTCOME_COLOURS.items():
        g = share[share["outcome"] == outcome]
        fig.add_scatter(x=g["year"], y=g["share"], name=outcome, stackgroup="one", mode="lines",
                        line=dict(width=0.5, color=colour), fillcolor=colour,
                        hovertemplate=f"{outcome}: %{{y:.0f}}%<extra></extra>")
    fig.update_yaxes(range=[0, 100], ticksuffix="%", title=None)
    fig.update_layout(height=400, hovermode="x unified", legend=dict(orientation="h", y=-0.15))
    return fig


def engine_stream(results, top=8):
    wins = results[results["is_win"]]
    best = wins["engine"].value_counts().head(top).index
    wins = wins.assign(engine=wins["engine"].where(wins["engine"].isin(best), "Other"))
    table = wins.groupby(["year", "engine"]).size().unstack(fill_value=0)
    table = table.rolling(3, center=True, min_periods=1).sum()
    fig = go.Figure()
    for i, engine in enumerate(list(best) + ["Other"]):
        if engine not in table:
            continue
        colour = ENGINE_COLOURS.get(engine, SPARE_COLOURS[i % len(SPARE_COLOURS)])
        fig.add_scatter(x=table.index, y=table[engine], name=engine, stackgroup="one", groupnorm="percent",
                        mode="lines", line=dict(width=0.5, color=colour, shape="spline", smoothing=0.6),
                        fillcolor=colour,
                        hovertemplate=f"{engine}: %{{y:.0f}}% of wins<extra></extra>")
    fig.update_yaxes(ticksuffix="%", range=[0, 100])
    fig.update_layout(height=400, hovermode="x unified", legend=dict(orientation="h", y=-0.15))
    return fig


def grid_heatmap(results):
    g = results[results["finished"] & results["grid"].between(1, 20) & results["position"].between(1, 20)]
    if g.empty:
        return empty("No finishers in this selection")
    table = pd.crosstab(g["position"], g["grid"]).reindex(index=range(1, 21), columns=range(1, 21), fill_value=0)
    share = table / table.sum(axis=0).replace(0, np.nan) * 100
    fig = go.Figure(go.Heatmap(z=share.to_numpy(), x=list(range(1, 21)), y=list(range(1, 21)),
                               colorscale=[[0, BG], [0.3, "#5a2a3a"], [1, RED]], xgap=1, ygap=1,
                               customdata=table.to_numpy(),
                               colorbar=dict(title="% of starters<br>from that slot", thickness=10),
                               hovertemplate="from P%{x} to P%{y}<br>%{z:.1f}% (%{customdata} results)<extra></extra>"))
    fig.update_yaxes(autorange="reversed", title="Finishing position", dtick=1)
    fig.update_xaxes(title="Starting position", dtick=1)
    fig.update_layout(height=470)
    return fig


def age_violin(results):
    d = results.dropna(subset=["age"]).copy()
    d["decade"] = (d["year"] // 10 * 10).astype(str) + "s"
    fig = go.Figure()
    fig.add_violin(x=d["decade"], y=d["age"], name="All starters", side="negative", line_color=MUTED,
                   fillcolor="rgba(154,154,174,0.35)", meanline_visible=True, points=False)
    w = d[d["is_win"]]
    fig.add_violin(x=w["decade"], y=w["age"], name="Race winners", side="positive", line_color=RED,
                   fillcolor="rgba(225,6,0,0.4)", meanline_visible=True, points=False)
    fig.update_layout(height=400, violingap=0.1, violinmode="overlay", yaxis_title="Age on race day",
                      legend=dict(orientation="h", y=1.1))
    return fig
