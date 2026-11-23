import re

import numpy as np
import pandas as pd
from svgpathtools import parse_path

from .sources import RAW


def svg_points(svg_file, n=400):
    """n points evenly spaced along the track path of an F1DB svg."""
    d = re.search(r'\sd="([^"]+)"', svg_file.read_text()).group(1)
    path = parse_path(d)
    pts = np.array([path.point(x) for x in np.linspace(0, 1, 3000)])
    dist = np.r_[0, np.cumsum(np.abs(np.diff(pts)))]
    even = np.interp(np.linspace(0, dist[-1], n), dist, np.arange(len(pts)))
    pts = pts[np.round(even).astype(int)]
    return pts.real, -pts.imag


def load_tracks():
    rows = []
    for svg in sorted((RAW / "f1db" / "circuits").glob("*.svg")):
        x, y = svg_points(svg)
        rows.append(pd.DataFrame({"layout_id": svg.stem, "i": range(len(x)), "x": x.round(1), "y": y.round(1)}))
    return pd.concat(rows, ignore_index=True)
