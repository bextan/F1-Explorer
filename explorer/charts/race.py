import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .theme import BG, GRID, TYRE_COLOURS, empty, teammate_dash


def lap_chart(results, laps, pits):
    if laps.empty:
        return empty("Lap-by-lap positions are only recorded from 1994", 300)
    res = results.sort_values("position_order").copy()
    res["dash"] = teammate_dash(res).to_numpy()
    fig = go.Figure()
    total = int(laps["lap"].max())
    for _, r in res.iterrows():
        d = laps[laps["driver_id"] == r["driver_id"]]
        if d.empty:
            continue
        lap_x = np.r_[0, d["lap"]] if pd.notna(r["grid"]) else d["lap"].to_numpy()
        pos_y = np.r_[r["grid"], d["position"]] if pd.notna(r["grid"]) else d["position"].to_numpy()
        fig.add_scatter(x=lap_x, y=pos_y, mode="lines", name=r["driver"],
                        line=dict(color=r["colour"], width=2.2, dash=r["dash"]),
                        hovertemplate=f"<b>{r['driver']}</b> ({r['team']})<br>Lap %{{x}} · P%{{y}}<extra></extra>")
        p = pits[pits["driver_id"] == r["driver_id"]].merge(d[["lap", "position"]], on="lap")
        if not p.empty:
            fig.add_scatter(x=p["lap"], y=p["position"], mode="markers", showlegend=False,
                            marker=dict(symbol="circle", size=8, color=BG, line=dict(color=r["colour"], width=2)),
                            customdata=(p["duration_ms"] / 1000).round(1),
                            hovertemplate=f"{r['driver']} pit stop · lap %{{x}}<br>%{{customdata}} s<extra></extra>")
        label = r["abbr"] if isinstance(r["abbr"], str) else r["driver"][:3].upper()
        fig.add_annotation(x=d["lap"].iloc[-1], y=d["position"].iloc[-1], text=label, xanchor="left",
                           showarrow=False, xshift=6, font=dict(size=10, color=r["colour"]))
    n = int(max(laps["position"].max(), res["grid"].max() if res["grid"].notna().any() else 0))
    fig.update_yaxes(autorange=False, range=[n + 0.5, 0.5], dtick=1, title="Position")
    fig.update_xaxes(range=[0, total + 3], title="Lap (0 = starting grid)")
    fig.update_layout(height=max(420, n * 24), showlegend=False, hovermode="closest",
                      title=dict(text="Lap chart · ○ = pit stop · dotted = second team car", font=dict(size=14)))
    return fig


def tyre_strategy(results, stints):
    if stints.empty:
        return empty("Tyre stints come from OpenF1 and exist from 2023", 260)
    order = results.sort_values("position_order")
    order = order[order["driver_id"].isin(stints["driver_id"])]
    labels = dict(zip(order["driver_id"], order["abbr"].fillna(order["driver"].str[:3].str.upper())))
    fig = go.Figure()
    for compound, g in stints.groupby("compound"):
        fig.add_bar(y=g["driver_id"].map(labels), x=g["lap_end"] - g["lap_start"] + 1, base=g["lap_start"] - 1,
                    orientation="h", name=compound.title(),
                    marker=dict(color=TYRE_COLOURS.get(compound, "#777"), line=dict(color=BG, width=2)),
                    customdata=np.c_[g["lap_start"], g["lap_end"], g["tyre_age_at_start"].fillna(0)],
                    hovertemplate=f"{compound.title()}<br>laps %{{customdata[0]}}–%{{customdata[1]}}"
                                  "<br>tyre age at start: %{customdata[2]} laps<extra></extra>")
    fig.update_yaxes(categoryorder="array", categoryarray=list(labels.values())[::-1])
    fig.update_xaxes(title="Lap")
    fig.update_layout(barmode="overlay", height=max(300, len(labels) * 22), bargap=0.25,
                      legend=dict(orientation="h", y=1.08, x=0), margin=dict(t=40))
    return fig


def winners_history(winners):
    if winners.empty:
        return empty("No winners in the selected seasons")
    fig = go.Figure()
    fig.add_hline(y=1, line=dict(color=GRID, dash="dot"))
    fig.add_scatter(x=winners["year"], y=winners["grid"], mode="markers",
                    marker=dict(size=13, color=winners["colour"], line=dict(color="white", width=1)),
                    customdata=winners[["driver", "team"]],
                    hovertemplate="<b>%{x}</b> %{customdata[0]}<br>%{customdata[1]} · started P%{y}<extra></extra>")
    top = int(max(winners["grid"].max(), 5)) if winners["grid"].notna().any() else 5
    fig.update_yaxes(autorange=False, range=[top + 0.5, 0.5], title="Winner's grid slot",
                     tickvals=[1, 5, 10, 15, 20, 25, 30] if top > 12 else list(range(1, top + 1)))
    fig.update_xaxes(title=None)
    fig.update_layout(height=280, margin=dict(t=20, b=30))
    return fig
