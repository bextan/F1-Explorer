import numpy as np
import pandas as pd
from plotly.subplots import make_subplots

from .theme import BG, MUTED, TEXT, empty

SEASON_KINDS = [("Win", "#ffd12e"), ("Podium", "#27f4d2"), ("Points", "#2a9d8f"), ("No points", "#5a5a72"),
                ("Did not finish", "#e76f51")]
MEDALS = {1: "#ffd12e", 2: "#c0c0c8", 3: "#cd7f32"}


def career_seasons(res, champ, unit="races"):
    if res.empty:
        return empty("No races", 420)
    r = res.copy()
    r["kind"] = np.select(
        [r["is_win"], r["is_podium"], r["finished"] & (r["points"] > 0), r["finished"]],
        ["Win", "Podium", "Points", "No points"], default="Did not finish")
    years = list(range(int(r["year"].min()), int(r["year"].max()) + 1))
    counts = r.pivot_table(index="year", columns="kind", values="race_id", aggfunc="count", fill_value=0)
    counts = counts.reindex(index=years, columns=[k for k, _ in SEASON_KINDS], fill_value=0)
    total = counts.sum(axis=1)
    share = counts.div(total.replace(0, np.nan), axis=0) * 100
    teams = r.groupby("year")["team"].agg(lambda t: " / ".join(dict.fromkeys(t))).reindex(years).fillna("")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.4, 0.6], vertical_spacing=0.09,
                        subplot_titles=("Championship position at the end of the season",
                                        f"How the {unit} ended (share of the season, numbers = count)"))
    fig.update_annotations(font=dict(size=12, color=MUTED), x=0, xanchor="left")

    c = champ.dropna(subset=["position"]).sort_values("position").drop_duplicates("year") \
        .set_index("year").reindex(years)
    has = c["position"].notna()
    if has.any():
        pos = c["position"]
        summary = [
            (f"<b>{y}</b> · {teams[y]}<br>" if teams[y] else f"<b>{y}</b><br>") +
            (f"<b>P{int(p)}</b> in the championship · {pts:g} pts<br>" if pd.notna(p) else "not classified<br>") +
            f"{counts.at[y, 'Win']} wins · {counts.at[y, 'Win'] + counts.at[y, 'Podium']} podiums"
            f" · {counts.at[y, 'Did not finish']} DNF in {total[y]} {unit}"
            for y, p, pts in zip(years, pos, c["points"].fillna(0))]
        colours = [MEDALS.get(int(p), "#8a8aa0") if pd.notna(p) else "#8a8aa0" for p in pos]
        few = has.sum() <= 25
        fig.add_scatter(
            x=years, y=pos, mode="lines+markers+text" if few else "lines+markers", connectgaps=False,
            text=[f"P{int(p)}" if pd.notna(p) else "" for p in pos], textposition="top center",
            textfont=dict(size=10, color=TEXT), line=dict(color="#6a6a85", width=1.5),
            marker=dict(size=[13 if pd.notna(p) and p <= 3 else 8 for p in pos], color=colours,
                        line=dict(color=BG, width=1.5)),
            cliponaxis=False,
            hovertext=summary, hoverinfo="text", showlegend=False, row=1, col=1)
        worst = int(pos.max())
        fig.update_yaxes(autorange=False, range=[worst + 1.2, 0.2] if few else [worst + 0.8, 0.1],
                         tickprefix="P", dtick=1 if worst <= 6 else (2 if worst <= 12 else 5),
                         title="", row=1, col=1)
    else:
        fig.add_annotation(text="no championship standings for these seasons", showarrow=False,
                           font=dict(color=MUTED), xref="x domain", yref="y domain", x=0.5, y=0.5)
        fig.update_yaxes(visible=False, row=1, col=1)

    for kind, colour in SEASON_KINDS:
        n = counts[kind]
        fig.add_bar(
            x=years, y=share[kind], name=kind, marker=dict(color=colour, line=dict(width=0)),
            customdata=np.stack([n, total], axis=-1),
            text=[str(v) if v else "" for v in n], textposition="inside", insidetextanchor="middle",
            textfont=dict(size=11, color="#15151e" if kind in ("Win", "Podium") else TEXT),
            hovertemplate=f"{kind}: %{{customdata[0]}} of %{{customdata[1]}} {unit} (%{{y:.0f}}%)<extra></extra>",
            row=2, col=1)
    fig.update_yaxes(range=[0, 100], ticksuffix="%", title="", row=2, col=1)

    fig.update_xaxes(dtick=1 if len(years) <= 16 else (2 if len(years) <= 30 else 5), showgrid=False,
                     range=[years[0] - 0.6, years[-1] + 0.6])
    fig.update_layout(
        # with many seasons the thin gaps between bars render as uneven stripes
        barmode="stack", bargap=0.15 if len(years) <= 30 else 0, height=520, margin=dict(t=30, b=70, l=45, r=15),
        hovermode="x unified", uniformtext=dict(minsize=9, mode="hide"),
        legend=dict(orientation="h", y=-0.08, yanchor="top", x=0, font=dict(size=11), traceorder="normal"),
    )
    return fig
