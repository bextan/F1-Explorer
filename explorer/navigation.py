from dash import ALL, Input, Output, State, callback, ctx, no_update

from .pages import TABS


@callback([Output(f"page-{name}", "className") for name in TABS] +
          [Output("page-driver", "className"), Output("page-team", "className")],
          Input("tabs", "value"), Input("nav", "data"))
def switch_page(tab, nav):
    # an open driver/team page covers the current tab
    top = nav[-1]["kind"] if nav else None
    pages = ["tab-page" if name == tab and not top else "tab-page hidden" for name in TABS]
    return pages + ["tab-page" if top == kind else "tab-page hidden" for kind in ("driver", "team")]


@callback(
    Output("nav", "data"), Output("driver", "data"), Output("team", "data"), Output("global-search", "value"),
    Input("global-search", "value"),
    Input({"type": "driver-link", "id": ALL, "src": ALL}, "n_clicks"),
    Input({"type": "team-link", "id": ALL, "src": ALL}, "n_clicks"),
    Input("driver-back", "n_clicks"), Input("team-back", "n_clicks"), Input("tabs", "value"),
    Input({"type": "driver-race", "id": ALL, "n": ALL}, "n_clicks"), Input("driver-map", "clickData"),
    Input("team-map", "clickData"), Input("race-click", "data"),
    State("nav", "data"),
    prevent_initial_call=True,
)
def navigate(search, driver_links, team_links, driver_back, team_back, tab, race_clicks, driver_map, team_map,
             race_click, nav):
    """`nav` is the stack of open driver/team pages, newest last."""
    nothing = (no_update,) * 4
    trigger = ctx.triggered_id
    nav = list(nav or [])
    clear_search = no_update

    def push(kind, id_):
        page = {"kind": kind, "id": id_}
        return nav if nav and nav[-1] == page else (nav + [page])[-20:]

    if trigger == "global-search":
        if not search:
            return nothing
        kind, id_ = search.split(":", 1)
        nav = push("driver" if kind == "d" else "team", id_)
        clear_search = None
    elif isinstance(trigger, dict) and trigger["type"] in ("driver-link", "team-link", "driver-race"):
        if not ctx.triggered[0]["value"]:
            return nothing
        if trigger["type"] == "driver-race":
            nav = []
        else:
            nav = push(trigger["type"].split("-")[0], trigger["id"])
    elif trigger in ("driver-back", "team-back"):
        nav = nav[:-1]
    else:
        nav = []

    top = nav[-1] if nav else None
    driver = top["id"] if top and top["kind"] == "driver" else no_update
    team = top["id"] if top and top["kind"] == "team" else no_update
    return nav, driver, team, clear_search
