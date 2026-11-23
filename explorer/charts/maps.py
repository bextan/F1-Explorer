import numpy as np
import plotly.graph_objects as go

from .theme import BG, MUTED, RED, TYPE_COLOURS


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
    fig = go.Figure()
    if countries is not None:
        hosted = (countries["races"] > 0).astype(int)
        fig.add_choropleth(
            locations=countries["iso3"], z=hosted, zmin=0, zmax=1, name="countries",
            colorscale=[[0, "#262634"], [1, "#34344c"]], showscale=False,
            marker=dict(line=dict(color="#4a4a62", width=0.5)),
            text=[_country_hover(r) for r in countries.itertuples()], hovertemplate="%{text}<extra></extra>",
        )
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

    # the country layer already draws land and borders; plotly's own layers would double the work while dragging
    has_countries = countries is not None
    geo = dict(showland=not has_countries, landcolor="#262634", showcountries=not has_countries,
               countrycolor="#3a3a50", showcoastlines=not has_countries, coastlinecolor="#3a3a50",
               showocean=True, oceancolor=BG, showlakes=False,
               bgcolor="rgba(0,0,0,0)", showframe=False, projection_type="natural earth", fitbounds=False)

    if selected is not None:
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


def career_map(circuits):
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
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=10, b=0), uirevision="career-map",
                      legend=dict(orientation="h", y=0.02, x=0.01, font=dict(size=12)))
    return fig
