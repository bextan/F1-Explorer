# F1 Explorer

An interactive dashboard for exploring the history of Formula 1, from the first World Championship race in 1950
to the 2026 season. You can start from a world map of every circuit, open a single race and replay it lap by lap
on the real track layout, follow a championship fight through a season, compare drivers' careers, and see how the
sport changed across eras.

Built with **Dash** and **Plotly** (both listed on [PyViz.org](https://pyviz.org)) and **pandas**.

## Analytical questions

1. **Where has F1 raced, and how has the calendar moved over time?** World map, filtered by season range, circuit type and search.
2. **How did a specific race unfold: overtakes, pit stops, tyre strategy?** Race replay, lap chart, tyre strategy.
3. **Does qualifying matter more on some tracks than others?** Winners by starting slot per circuit, pole → win rate.
4. **How was a championship won during the season?** Points progression and a full results matrix.
5. **How do drivers' careers compare?** Scatter of every driver, career paths, comparison table.
6. **How have reliability, engine dominance and driver age changed across eras?** Eras tab.

## Data sources

Three sources are combined, because none of them has everything:

| Source | What I use from it | Coverage | Licence |
|---|---|---|---|
| [F1DB](https://github.com/f1db/f1db) (release `v2026.20.0`) | races, results, circuits (type, length, turns, direction), drivers, constructors, engines, tyres, standings, pit stops, **track layout SVGs** | 1950–2026 | CC BY 4.0 |
| [Jolpica F1](https://github.com/jolpica/jolpica-f1) (CSV database dump, successor of the Ergast API) | **lap-by-lap times and positions**, retirement status codes | laps from 1994 | Apache 2.0 / API terms of use |
| [OpenF1](https://openf1.org) (REST API) | official **team colours**, driver photos, **tyre stints**, **weather** | 2023–2026 | CC BY-NC-SA 4.0 (non-commercial) |

Everything was downloaded on 16 Nov 2026. `download_data.py` downloads all of it again.

## Data preparation (`prepare_data.py`)

**Joining the sources**
- F1DB ↔ Jolpica: both number races by `(year, round)`, and all 1172 races match. Inside a race, results are matched by car number.
- F1DB ↔ OpenF1: OpenF1 uses its own session keys, so sessions are matched by year plus race date within ±1 day, then by car number.
  The tolerance is needed because sources can date a race a day apart (local time vs. UTC; F1DB and Jolpica already differ by
  a day for Las Vegas). Matching by name wasn't possible either:
  OpenF1 labels the 2026 Kuala Lumpur race with country "Bahrain".

**Cleaning**
- Removed entries that never took part in the race (DNQ, DNPQ, DNP).
- A grid position of 0 or empty means a pit-lane start, so it stays missing instead of being counted as pole.
- Missing points become 0. Lap times are converted from `hh:mm:ss.sss` text to milliseconds.
- Deleted laps and laps without a position are dropped. Duplicate car numbers from shared drives in the 1950s are dropped.
- Races scheduled in the future (no results yet) are left out.

**New variables**
- `outcome`: Finished / Finished (lapped) / Not classified / DNF – mechanical / DNF – accident / Disqualified / Did not start.
  It uses the Jolpica status code first, and F1DB's position text (`DNF`, `DSQ`, `NC`…) as a fallback.
- `positions_gained`, driver age on race day, win and podium flags, cumulative race time after each lap.
- **Team colour** for every result, in order of priority: OpenF1's official colour, then Jolpica's colour for current teams,
  then a hand-picked livery colour for about 50 historic teams, then a neutral fallback.
- **Track shapes**: each F1DB SVG path is sampled into 400 evenly spaced points (by arc length).
  The y axis is flipped and the direction is set using the shoelace formula plus the circuit's official direction.
- Circuit summary: number of races, first and last year, driver with the most wins, pole → win rate.
- Driver careers: starts, wins, podiums, poles, titles, average finish, DNF rate, main team colour.
- Weather averaged per race: air and track temperature, humidity, wind, rain yes/no.

**Output** (`data/processed/`)

| Table | Rows | Content |
|---|---|---|
| `results.csv` | 26 347 | one row per driver per race |
| `laps.csv` | 637 842 | position and time of every lap (1994+) |
| `races.csv` | 1 169 | race info + weather + winner |
| `circuits.csv` | 78 | circuit info + summary |
| `drivers.csv` | 794 | career totals |
| `standings.csv` | 21 660 | championship standings after each round |
| `pit_stops.csv` | 22 755 | pit stops (1994+) |
| `stints.csv` | 5 256 | tyre stints (2023+) |
| `tracks.csv` | 64 000 | 400 points × 160 track layouts |

## The dashboard

**Circuits**
- A filter bar (search, circuit type, current calendar only, season range) controls a world map of all circuits.
  Bubble size is the number of races in the selected period, and colour is the circuit type.
- Clicking a circuit shrinks the map into a small globe turned towards it. A clickable list of the filtered circuits appears
  below the globe, and the circuit page opens beside it:
  - circuit facts and a race picker;
  - the classification in team colours, with driver photos and positions gained;
  - an **animated race replay**: every car is a dot moving around the real track layout using its actual lap times;
  - a **lap chart** with pit stops marked, with teammates told apart by solid vs. dotted lines;
  - **tyre strategy** for 2023+ races;
  - a chart of the starting slot of every winner at that circuit.

**Seasons**
- Championship points after every round for the top 10.
- A results matrix of every driver in every race. Clicking a cell opens that race on the Circuits tab.

**Drivers**
- A scatter of every driver with 10+ starts: starts vs. win rate, with bubble size for titles and colour for debut year.
- Searching for drivers or clicking dots adds them to the comparison: career championship positions plus a stats table.

**Eras**
- How races end per season (100% stacked area).
- Share of wins by engine manufacturer (3-season rolling window).
- Grid slot vs. finishing position heatmap.
- Age of all starters vs. race winners per decade (split violin).
- All four charts follow the season range slider.

## How to run

```
pip install -r requirements.txt
python download_data.py      # about 10–15 min (OpenF1 is rate-limited); skips files that already exist
python prepare_data.py       # about 1 min
python app.py                # then open http://localhost:8050
```

`python download_data.py --skip-openf1` skips the OpenF1 part. The app also runs without it, but without colours, tyres and weather for 2023+.

## Project structure

```
download_data.py    downloads the three sources into data/raw/
prepare_data.py     cleaning + joining -> data/processed/
app.py              Dash layout and callbacks
charts.py           all Plotly figures + the dark theme
assets/style.css    page styling
```

## Limitations

- **Replay**:
  - Inside a lap each car moves at a constant speed, so positions between lap ends are estimated.
  - The start of the SVG path is not always exactly at the real start/finish line.
  - Pit stops are not shown on the track, only in the lap chart.
- Lap data starts in 1994, and tyre and weather data in 2023. Older races show the track and results only.
- Team colours before 2023 are hand-picked, one per constructor, so they ignore livery changes over the years.
- The 2026 season is still running, so its numbers are partial. The Seasons tab opens on 2025 by default.
- Before the 1960s the field often had more than 20 cars, so the grid heatmap is cut off at position 20.
