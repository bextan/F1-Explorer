import numpy as np
import plotly.graph_objects as go

from .theme import BG, MUTED


def championship(standings, colours):
    final_round = standings["round"].max()
    final = standings[standings["round"] == final_round].sort_values("position")
    fig = go.Figure()
    teams_seen = {}
    for _, r in final.iterrows():
        g = standings[standings["driver_id"] == r["driver_id"]]
        colour = colours.get(r["driver_id"], MUTED)
        dash = "dot" if colour in teams_seen else "solid"
        teams_seen[colour] = True
        fig.add_scatter(x=g["round"], y=g["points"], mode="lines+markers", name=r["driver"],
                        line=dict(color=colour, width=2.5, dash=dash), marker=dict(size=5),
                        hovertemplate=f"<b>{r['driver']}</b><br>round %{{x}}: %{{y}} pts<extra></extra>")
    fig.update_layout(height=430, hovermode="x unified", xaxis_title="Round", yaxis_title="Points",
                      legend=dict(font=dict(size=11)))
    return fig


def results_matrix(results, races, standings):
    final = standings[standings["round"] == standings["round"].max()].sort_values("position")
    order = [d for d in final["driver"] if d in set(results["driver"])]
    order += [d for d in results["driver"].unique() if d not in order]
    rounds = races.sort_values("round")
    cols = rounds["round"].tolist()

    z = results.pivot_table(index="driver", columns="round", values="position", aggfunc="min")
    txt = results.pivot_table(index="driver", columns="round", values="position_text", aggfunc="first")
    z = z.reindex(index=order, columns=cols)
    txt = txt.reindex(index=order, columns=cols).fillna("")
    race_ids = np.tile(rounds["race_id"].to_numpy(), (len(order), 1))

    labels = [f"{a}" for a in rounds["gp_abbr"].fillna(rounds["round"].astype(str))]
    fig = go.Figure(go.Heatmap(
        z=z.to_numpy(), x=labels, y=order, text=txt.to_numpy(), texttemplate="%{text}",
        textfont=dict(size=10), customdata=race_ids, xgap=2, ygap=2,
        colorscale=[[0, "#ffd700"], [0.1, "#e10600"], [0.45, "#5a2a3a"], [1, "#23232f"]],
        zmin=1, zmax=20, colorbar=dict(title="Pos", thickness=10),
        hovertemplate="%{y}<br>%{x}: %{text}<extra>click to open race</extra>",
    ))
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=11))
    fig.update_xaxes(side="top", tickfont=dict(size=11))
    fig.update_layout(height=max(380, 22 * len(order)), margin=dict(l=130, t=60, r=20, b=20),
                      plot_bgcolor=BG)
    return fig
