import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .theme import GRID, PANEL, RED, TEXT, empty


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


def race_replay(race, track, results, laps, direction, frames_per_lap=12):
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

    cum = {d: np.r_[0, laps.loc[laps["driver_id"] == d, "race_ms"].to_numpy()] for d in drivers}
    finished = {d: bool(info.at[d, "finished"]) for d in drivers}
    end_time = max(c[-1] for d, c in cum.items() if finished[d]) if any(finished.values()) else \
        max(c[-1] for c in cum.values())
    winner_time = min(c[-1] for d, c in cum.items() if len(c) - 1 == total_laps) if any(
        len(c) - 1 == total_laps for c in cum.values()) else end_time
    # a lap far slower than usual is a red flag; it is played as two normal laps so the replay doesn't stall
    lead = np.array([min(c[k] for c in cum.values() if len(c) > k) for k in range(total_laps + 1)])
    lap_ms = np.diff(lead)
    normal = np.median(lap_ms)
    stopped = lap_ms > 3 * normal
    shown = np.r_[0, np.cumsum(np.where(stopped, 2 * normal, lap_ms))]
    times = np.interp(np.linspace(0, shown[-1], total_laps * frames_per_lap + 1), shown, lead)
    step = shown[-1] / (total_laps * frames_per_lap)
    tail = int(np.ceil((end_time - lead[-1]) / step)) if end_time > lead[-1] else 0
    times = np.r_[times, np.linspace(lead[-1], end_time, tail + 1)[1:]]
    red_flags = [(lead[k], lead[k + 1]) for k in np.flatnonzero(stopped)]

    colours = [info.at[d, "colour"] for d in drivers]
    abbrs = [info.at[d, "abbr"] if isinstance(info.at[d, "abbr"], str) else info.at[d, "driver"][:3].upper()
             for d in drivers]
    names = [info.at[d, "driver"] for d in drivers]

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
        px_ = np.where(np.isnan(prog), np.nan, x[idx])
        py_ = np.where(np.isnan(prog), np.nan, y[idx])
        done = np.where(np.isnan(prog), 0, prog) >= total_laps
        px_ = np.where(done, x[0], px_)
        py_ = np.where(done, y[0], py_)
        lap_now = int(np.clip(np.nanmax(prog) + 1, 1, total_laps)) if not np.all(np.isnan(prog)) else total_laps
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
        px_, py_, hover, lap_now = frame_state(t)
        label = "FINISH" if t >= winner_time else f"LAP {lap_now} / {total_laps}"
        if t < winner_time and any(a < t < b for a, b in red_flags):
            label += " · RED FLAG"
        frames.append(go.Frame(data=[go.Scatter(x=px_, y=py_, hovertext=hover), go.Scatter(text=[label])],
                               traces=[trace_index, trace_index + 1], name=str(i)))
        steps.append(dict(method="animate", label="", args=[[str(i)], dict(mode="immediate",
                          frame=dict(duration=0, redraw=False), transition=dict(duration=0))]))
    fig.frames = frames

    def play(speed):
        ms = 1200 / frames_per_lap / speed
        return dict(label=f"▶ {speed:g}×", method="animate",
                    args=[None, dict(frame=dict(duration=ms, redraw=False),
                                     transition=dict(duration=ms, easing="linear"),
                                     fromcurrent=True, mode="immediate")])

    fig.update_layout(
        height=520, title=dict(text="Race replay", font=dict(size=15)),
        margin=dict(l=10, r=10, t=45, b=95),
        updatemenus=[dict(type="buttons", direction="left", x=0.0, y=-0.02, xanchor="left", yanchor="top",
                          bgcolor=PANEL, bordercolor=GRID, font=dict(color=TEXT), showactive=False,
                          buttons=[play(0.25), play(0.5), play(1), play(2), play(4),
                                   dict(label="❚❚", method="animate",
                                        args=[[None], dict(mode="immediate", frame=dict(duration=0))])])],
        sliders=[dict(steps=steps, x=0.0, len=1.0, y=-0.1, yanchor="top", ticklen=0,
                      tickcolor="rgba(0,0,0,0)", font=dict(color="rgba(0,0,0,0)"),
                      bgcolor=GRID, activebgcolor=RED, bordercolor=GRID, currentvalue=dict(visible=False))],
    )
    return fig
