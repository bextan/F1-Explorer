# All figure-building functions used by app.py.
import numpy as np
import pandas as pd
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


def empty(message, height=300):
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(color=MUTED, size=15))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=height)
    return fig


def teammate_dash(df, team_col="team"):
    """Second driver of a team gets a dotted line so teammates can be told apart."""
    return df.groupby(team_col).cumcount().map(lambda i: "solid" if i == 0 else "dot")


# ===================================================================== map
def _country_hover(r):
    if r.races > 0:
        years = f"{r.first}" if r.first == r.last else f"{r.first}–{r.last}"
        circ = "circuit" if r.circuits == 1 else "circuits"
        return (f"<b>{r.name}</b><br>{r.races} races at {r.circuits} {circ} ({years})"
                "<br><i>click to list the races</i>")
    if r.ever > 0:
        return f"<b>{r.name}</b><br>no races with the current filters<br>({r.ever} races all-time)"
    return f"<b>{r.name}</b><br>never hosted a Formula 1 race"


def circuit_map(circuits, selected=None, countries=None, country=None):
    """World map / globe. `countries` has one row per country (iso3, name, races, circuits, first, last, ever)
    and is drawn as a hoverable, clickable layer under the circuit bubbles. `country` is the clicked ISO-3 code."""
    fig = go.Figure()
    if countries is not None:
        hosted = (countries["races"] > 0).astype(int)
        fig.add_choropleth(
            locations=countries["iso3"], z=hosted, zmin=0, zmax=1, name="countries",
            colorscale=[[0, "#262634"], [1, "#34344c"]], showscale=False,
            marker=dict(line=dict(color="#4a4a62", width=0.5)),
            text=[_country_hover(r) for r in countries.itertuples()], hovertemplate="%{text}<extra></extra>",
        )
        # the hovered country is highlighted in the browser by styling its shape (assets/map_hover.js),
        # so hovering never redraws the map
        if country:
            fig.add_choropleth(locations=[country], z=[1], name="selected-country", zmin=0, zmax=1,
                               showscale=False, colorscale=[[0, "rgba(225,6,0,0.4)"], [1, "rgba(225,6,0,0.4)"]],
                               hoverinfo="skip", marker=dict(line=dict(color=RED, width=1.8)))

    for kind, g in circuits.groupby("type"):
        fig.add_scattergeo(
            lat=g["latitude"], lon=g["longitude"], name=kind,
            customdata=g[["id", "full_name", "place", "country", "races_period", "first_year", "last_year"]],
            marker=dict(size=7 + np.sqrt(g["races_period"]) * 2.6, color=TYPE_COLOURS.get(kind, MUTED),
                        opacity=0.85, line=dict(color="white", width=0.6)),
            hovertemplate="<b>%{customdata[1]}</b><br>%{customdata[2]}, %{customdata[3]}"
                          "<br>%{customdata[4]} races in selected period"
                          "<br>used %{customdata[5]}–%{customdata[6]}<extra></extra>",
        )

    # the country layer already draws land and borders, so plotly's own land/borders/coastline layers are
    # switched off: they doubled the work on every frame while dragging the globe
    has_countries = countries is not None
    geo = dict(showland=not has_countries, landcolor="#262634", showcountries=not has_countries,
               countrycolor="#3a3a50", showcoastlines=not has_countries, coastlinecolor="#3a3a50",
               showocean=True, oceancolor=BG, showlakes=False,
               bgcolor="rgba(0,0,0,0)", showframe=False, projection_type="natural earth", fitbounds=False)

    if selected is not None:
        # zoom out to a small globe that is turned towards the chosen circuit
        fig.add_scattergeo(lat=[selected["latitude"]], lon=[selected["longitude"]], hoverinfo="skip",
                           marker=dict(size=26, color="rgba(0,0,0,0)", line=dict(color="white", width=2.5)),
                           showlegend=False)
        geo.update(projection_type="orthographic",
                   projection_rotation=dict(lon=selected["longitude"], lat=selected["latitude"] * 0.6))
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
    else:
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0),
                          legend=dict(title="Circuit type", orientation="h", y=0.02, x=0.01))

    fig.update_geos(**geo)
    fig.update_layout(uirevision=str(selected["id"]) if selected is not None else "world")
    return fig


# ===================================================================== track + replay
def track_xy(track, direction):
    x, y = track["x"].to_numpy(), track["y"].to_numpy()
    # shoelace formula: positive area = points go anticlockwise
    area = 0.5 * np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])
    if (direction == "clockwise" and area > 0) or (direction == "anticlockwise" and area < 0):
        x, y = x[::-1], y[::-1]
    return x, y


def _track_base(fig, x, y):
    fig.add_scatter(x=x, y=y, mode="lines", line=dict(color="#3a3a50", width=16), hoverinfo="skip",
                    showlegend=False)
    fig.add_scatter(x=x, y=y, mode="lines", line=dict(color="#8a8aa0", width=2), hoverinfo="skip",
                    showlegend=False)
    fig.add_scatter(x=[x[0]], y=[y[0]], mode="markers", hoverinfo="skip", showlegend=False,
                    marker=dict(symbol="square", size=11, color="white", line=dict(color="black", width=2)))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)


def race_replay(race, track, results, laps, direction, frames_per_lap=3):
    """Animated race: every driver is a dot on the track, moved by their real lap times.
    Inside a lap the speed is assumed constant, so the position is an approximation."""
    fig = go.Figure()
    if track.empty:
        return empty("No track drawing for this layout", 520)
    x, y = track_xy(track, direction)
    _track_base(fig, x, y)

    if laps.empty:
        fig.update_layout(height=520, title=dict(text="Track layout · lap data starts in 1994", font=dict(size=14)))
        return fig

    n_pts = len(x)
    total_laps = int(laps["lap"].max())
    info = results.set_index("driver_id")
    drivers = [d for d in results.sort_values("position_order")["driver_id"] if d in set(laps["driver_id"])]

    # cumulative time at the end of every lap, starting with 0 at the start
    cum = {d: np.r_[0, laps.loc[laps["driver_id"] == d, "race_ms"].to_numpy()] for d in drivers}
    finished = {d: bool(info.at[d, "finished"]) for d in drivers}
    end_time = max(c[-1] for d, c in cum.items() if finished[d]) if any(finished.values()) else \
        max(c[-1] for c in cum.values())
    winner_time = min(c[-1] for d, c in cum.items() if len(c) - 1 == total_laps) if any(
        len(c) - 1 == total_laps for c in cum.values()) else end_time
    times = np.linspace(0, winner_time, total_laps * frames_per_lap + 1)
    times = np.r_[times, np.linspace(winner_time, end_time, 6)[1:]]   # let the rest cross the line

    colours = [info.at[d, "colour"] for d in drivers]
    abbrs = [info.at[d, "abbr"] if isinstance(info.at[d, "abbr"], str) else info.at[d, "driver"][:3].upper()
             for d in drivers]
    names = [info.at[d, "driver"] for d in drivers]

    # cars start lined up behind the line in grid order; the gap closes during lap 1
    grid = results.set_index("driver_id")["grid"].reindex(drivers)
    grid_rank = grid.fillna(grid.max() + 1 if grid.notna().any() else 1).rank(method="first").to_numpy()
    start_offset = -0.012 * grid_rank

    def frame_state(t):
        prog = []
        for d in drivers:
            c = cum[d]
            if t > c[-1]:
                prog.append(len(c) - 1 if finished[d] else np.nan)
            else:
                prog.append(np.interp(t, c, np.arange(len(c))))
        prog = np.array(prog)
        prog = prog + start_offset * np.clip(1 - prog, 0, 1)
        order = pd.Series(-prog).rank(method="first").to_numpy()
        idx = np.nan_to_num((prog % 1) * n_pts, nan=0).astype(int) % n_pts
        # parked drivers (retired) disappear, finished drivers wait on the line
        px_ = np.where(np.isnan(prog), np.nan, x[idx])
        py_ = np.where(np.isnan(prog), np.nan, y[idx])
        done = np.where(np.isnan(prog), 0, prog) >= total_laps
        px_ = np.where(done, x[0], px_)
        py_ = np.where(done, y[0], py_)
        lap_now = int(min(np.nanmax(prog) + 1, total_laps)) if not np.all(np.isnan(prog)) else total_laps
        hover = [f"P{int(o)} {n}" if not np.isnan(p) else f"{n} – out" for o, n, p in zip(order, names, prog)]
        return px_, py_, hover, lap_now

    def dots(t):
        px_, py_, hover, lap_now = frame_state(t)
        return go.Scatter(x=px_, y=py_, mode="markers+text", text=abbrs, textposition="top center",
                          textfont=dict(size=10, color=TEXT), hovertext=hover, hoverinfo="text",
                          marker=dict(size=13, color=colours, line=dict(color="white", width=1.2)),
                          showlegend=False), lap_now

    def lap_label(text):
        return go.Scatter(x=[x.min()], y=[y.max() + (y.max() - y.min()) * 0.08], mode="text", text=[text],
                          textposition="middle right", textfont=dict(size=18, color=TEXT), hoverinfo="skip",
                          showlegend=False)

    first, _ = dots(0)
    fig.add_trace(first)
    fig.add_trace(lap_label(f"LAP 1 / {total_laps}"))
    trace_index = len(fig.data) - 2

    frames, steps = [], []
    for i, t in enumerate(times):
        trace, lap_now = dots(t)
        label = "FINISH" if t >= winner_time else f"LAP {lap_now} / {total_laps}"
        frames.append(go.Frame(data=[trace, lap_label(label)], traces=[trace_index, trace_index + 1],
                               name=str(i)))
        steps.append(dict(method="animate", label="", args=[[str(i)], dict(mode="immediate",
                          frame=dict(duration=0, redraw=False), transition=dict(duration=0))]))
    fig.frames = frames

    play = dict(frame=dict(duration=90, redraw=False), transition=dict(duration=80, easing="linear"),
                fromcurrent=True, mode="immediate")
    fig.update_layout(
        height=520, title=dict(text="Race replay", font=dict(size=15)),
        margin=dict(l=10, r=10, t=45, b=60),
        updatemenus=[dict(type="buttons", direction="left", x=0.0, y=-0.02, xanchor="left", yanchor="top",
                          bgcolor=PANEL, bordercolor=GRID, font=dict(color=TEXT), showactive=False,
                          buttons=[dict(label="▶ Play", method="animate", args=[None, play]),
                                   dict(label="❚❚", method="animate",
                                        args=[[None], dict(mode="immediate", frame=dict(duration=0))])])],
        sliders=[dict(steps=steps, x=0.16, len=0.84, y=-0.02, yanchor="top", ticklen=0,
                      tickcolor="rgba(0,0,0,0)", font=dict(color="rgba(0,0,0,0)"),
                      bgcolor=GRID, activebgcolor=RED, bordercolor=GRID, currentvalue=dict(visible=False))],
    )
    return fig


# ===================================================================== lap chart
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
        fig.add_scatter(x=lap_x, y=pos_y, mode="lines", name=r["driver"], line=dict(color=r["colour"], width=2.2, dash=r["dash"]),
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


# ===================================================================== tyre strategy
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


# ===================================================================== circuit history
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


# ===================================================================== seasons
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


# ===================================================================== drivers
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


PALETTE = ["#e10600", "#27f4d2", "#ffd12e", "#ff8000", "#6692ff", "#c77dff"]


def career_lines(season_pos, names, colours):
    if season_pos.empty:
        return empty("Pick drivers above to compare their careers", 380)
    fig = go.Figure()
    used = set()
    for i, (did, g) in enumerate(season_pos.groupby("driver_id", sort=False)):
        # same colour as in the scatter, unless two picked drivers share a team colour
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


# ===================================================================== driver page
def driver_map(circuits):
    """Flat map of the circuits a driver raced at. `circuits` has one row per circuit with
    id, name, place, country, latitude, longitude, races, wins, podiums, best, first, last."""
    fig = go.Figure()
    groups = [("Won here", circuits["wins"] > 0, "#ffd12e"),
              ("Podium here", (circuits["wins"] == 0) & (circuits["podiums"] > 0), "#27f4d2"),
              ("Raced here", circuits["podiums"] == 0, RED)]
    for label, mask, colour in groups:
        g = circuits[mask]
        if g.empty:
            continue
        fig.add_scattergeo(
            lat=g["latitude"], lon=g["longitude"], name=label,
            customdata=g[["id", "name", "place", "country", "races", "wins", "podiums", "best", "first", "last"]],
            marker=dict(size=8 + np.sqrt(g["races"]) * 4, color=colour, opacity=0.9,
                        line=dict(color="white", width=0.8)),
            hovertemplate="<b>%{customdata[1]}</b><br>%{customdata[2]}, %{customdata[3]}"
                          "<br>%{customdata[4]} races (%{customdata[8]}–%{customdata[9]})"
                          "<br>%{customdata[5]} wins · %{customdata[6]} podiums · best %{customdata[7]}"
                          "<extra>click to open the latest race here</extra>",
        )
    fig.update_geos(showland=True, landcolor="#262634", showcountries=True, countrycolor="#3a3a50",
                    showcoastlines=True, coastlinecolor="#3a3a50", showocean=True, oceancolor=BG,
                    showlakes=False, bgcolor="rgba(0,0,0,0)", showframe=False,
                    projection_type="natural earth", fitbounds=False)
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=10, b=0), uirevision="driver-map",
                      legend=dict(orientation="h", y=0.02, x=0.01, font=dict(size=12)))
    return fig


SEASON_COLOURS = {"Win": "#ffd12e", "Podium": "#27f4d2", "Points": "#2a9d8f", "No points": "#4a4a62",
                  "Did not finish": "#e76f51"}


def driver_seasons(res, champ):
    """Stacked bars of how every race of a season ended, plus the championship position."""
    if res.empty:
        return empty("No races", 340)
    r = res.copy()
    r["kind"] = np.select(
        [r["is_win"], r["is_podium"], r["finished"] & (r["points"] > 0), r["finished"]],
        ["Win", "Podium", "Points", "No points"], default="Did not finish")
    counts = r.pivot_table(index="year", columns="kind", values="race_id", aggfunc="count", fill_value=0)
    years = list(range(r["year"].min(), r["year"].max() + 1))
    counts = counts.reindex(years, fill_value=0)
    fig = go.Figure()
    for kind, colour in SEASON_COLOURS.items():
        if kind in counts:
            fig.add_bar(x=counts.index, y=counts[kind], name=kind, marker_color=colour,
                        hovertemplate=f"%{{x}}: %{{y}} × {kind.lower()}<extra></extra>")
    if not champ.empty:
        fig.add_scatter(x=champ["year"], y=champ["position"], name="Championship", yaxis="y2",
                        mode="lines+markers+text", text=["P" + str(int(p)) for p in champ["position"]],
                        textposition="top center", textfont=dict(size=10, color=TEXT),
                        line=dict(color="white", width=1.5, dash="dot"), marker=dict(size=6, color="white"),
                        hovertemplate="%{x}: P%{y} in the championship<extra></extra>")
    fig.update_layout(
        barmode="stack", height=360, margin=dict(t=30, b=40, r=50),
        yaxis=dict(title="Races"),
        # P1 at the top; an explicit range, autorange gave odd ticks (0.33) when every season was P1
        yaxis2=dict(title="Championship", overlaying="y", side="right", showgrid=False, zeroline=False,
                    range=[(champ["position"].max() if len(champ) else 1) + 1.5, 0.3],
                    tickprefix="P", dtick=1 if len(champ) and champ["position"].max() <= 10 else 5),
        legend=dict(orientation="h", y=1.12, font=dict(size=11)),
        xaxis=dict(dtick=1 if len(years) < 16 else None),
    )
    return fig


# ===================================================================== eras
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
    # one season has only ~10-20 wins, so use a 3-season rolling window to show eras instead of noise
    table = table.rolling(3, center=True, min_periods=1).sum()
    brand = {"Ferrari": "#e10600", "Mercedes": "#27f4d2", "Ford": "#1f6fd1", "Renault": "#ffd12e",
             "Honda": "#f0f0f0", "Honda RBPT": "#c77dff", "Climax": "#2a9d8f", "TAG": "#ff8000",
             "BMW": "#6692ff", "Alfa Romeo": "#a50f2d", "Other": "#555566"}
    spare = ["#f4a261", "#8ecae6", "#b5838d", "#84a59d"]
    fig = go.Figure()
    for i, engine in enumerate(list(best) + ["Other"]):
        if engine not in table:
            continue
        colour = brand.get(engine, spare[i % len(spare)])
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
