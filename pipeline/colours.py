CLASSIC = {
    "ferrari": "#DC0000", "mclaren": "#FF8000", "williams": "#1868DB", "lotus": "#C9A227",
    "red-bull": "#3671C6", "tyrrell": "#2A52BE", "renault": "#FFD12E", "brabham": "#2E9E6B",
    "sauber": "#8B9DC3", "mercedes": "#27F4D2", "minardi": "#7A7A7A", "ligier": "#3A6FD8",
    "arrows": "#FF7F50", "toro-rosso": "#3B4CC0", "benetton": "#3CB371", "jordan": "#F2D200",
    "haas": "#B6BABD", "alfa-romeo": "#A50F2D", "force-india": "#FF9DD2", "brm": "#6B8E23",
    "march": "#E36C0A", "lola": "#C0392B", "aston-martin": "#229971", "toyota": "#E8E8E8",
    "alpine": "#0093CC", "cooper": "#2F8F6F", "bar": "#C0C0C0", "honda": "#F5F5F5",
    "jaguar": "#0B6E4F", "alphatauri": "#5E8FAA", "prost": "#4169E1", "lotus-f1": "#B8860B",
    "marussia": "#9B2335", "maserati": "#B22222", "bmw-sauber": "#6CA0DC", "matra": "#1E90FF",
    "toleman": "#4FB0C6", "caterham": "#0E7C3A", "stewart": "#DADADA", "brawn": "#C6FF00",
    "racing-point": "#F596C8", "kick-sauber": "#52E252", "racing-bulls": "#6692FF",
    "vanwall": "#1F5E3B", "virgin": "#C8102E", "super-aguri": "#D3D3D3", "manor": "#E10600",
    "audi": "#FF2D00", "cadillac": "#AAAAAD",
}
FALLBACK = ["#8D99AE", "#A3B18A", "#B5838D", "#6D9DC5", "#C9ADA7", "#9A8C98", "#84A59D", "#B9A44C"]


def add_team_colours(res, jolpica_colours):
    """OpenF1 colour of that race, else Jolpica's for current teams, else a classic livery, else a fallback."""
    res["colour"] = res["team_colour"]
    res["colour"] = res["colour"].fillna(res["team"].map(jolpica_colours).where(res["year"] >= 2024))
    res["colour"] = res["colour"].fillna(res["team_id"].map(CLASSIC))
    res["colour"] = res["colour"].fillna(res["team_id"].map(lambda t: FALLBACK[sum(map(ord, t)) % len(FALLBACK)]))
    return res
