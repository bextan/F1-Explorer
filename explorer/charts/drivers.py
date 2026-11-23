import plotly.graph_objects as go

from .theme import PALETTE, empty


def driver_scatter(drivers, highlight):
    d = drivers[drivers["starts"] >= 10].copy()
    d["is_hl"] = d["driver_id"].isin(highlight)
    fig = go.Figure()
    base = d[~d["is_hl"]]
    fig.add_scatter(x=base["starts"], y=base["win_rate"] * 100, mode="markers", name="All drivers",
                    marker=dict(size=6 + base["titles"] * 4, color=base["first_year"], colorscale="Plasma",
                                cmin=1950, cmax=2026, opacity=0.35 if len(highlight) else 0.75,
                                colorbar=dict(title="Debut", thickness=10), line=dict(width=0)),
                    customdata=base[["name", "wins", "titles", "first_year", "last_year"]],
                    hovertemplate="<b>%{customdata[0]}</b> (%{customdata[3]}–%{customdata[4]})"
                                  "<br>%{x} starts · %{customdata[1]} wins · %{customdata[2]} titles<extra></extra>")
    hl = d[d["is_hl"]]
    if len(hl):
        fig.add_scatter(x=hl["starts"], y=hl["win_rate"] * 100, mode="markers+text", text=hl["name"],
                        textposition="top center", name="Selected",
                        marker=dict(size=10 + hl["titles"] * 4, color=hl["colour"], line=dict(color="white", width=2)),
                        customdata=hl[["name", "wins", "titles"]],
                        hovertemplate="<b>%{customdata[0]}</b><br>%{x} starts · %{customdata[1]} wins"
                                      " · %{customdata[2]} titles<extra></extra>")
    fig.update_xaxes(type="log", title="Race starts (log scale)", tickvals=[10, 20, 50, 100, 200, 400])
    fig.update_yaxes(title="Win rate (%)")
    fig.update_layout(height=480, showlegend=False,
                      title=dict(text="Every driver with 10+ starts · bubble size = titles", font=dict(size=14)))
    return fig


def career_lines(season_pos, names, colours):
    if season_pos.empty:
        return empty("Pick drivers above to compare their careers", 380)
    fig = go.Figure()
    used = set()
    for i, (did, g) in enumerate(season_pos.groupby("driver_id", sort=False)):
        colour = colours.get(did)
        if colour is None or colour in used:
            colour = PALETTE[i % len(PALETTE)]
        used.add(colour)
        g = g.set_index("year").reindex(range(g["year"].min(), g["year"].max() + 1)).reset_index()
        fig.add_scatter(x=g["year"], y=g["position"], mode="lines+markers", name=names[did], connectgaps=False,
                        line=dict(color=colour, width=2.5), marker=dict(size=8),
                        hovertemplate=f"<b>{names[did]}</b><br>%{{x}}: P%{{y}} in the championship<extra></extra>")
    fig.update_yaxes(autorange="reversed", title="Championship position", dtick=2)
    fig.update_xaxes(title="Season", dtick=1 if season_pos["year"].nunique() < 16 else None)
    fig.update_layout(height=380, legend=dict(orientation="h", y=1.1))
    return fig
