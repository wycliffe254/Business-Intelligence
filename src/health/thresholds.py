"""Generic piecewise-linear interpolation helper for turning a raw KPI
value into a bounded points score, using the breakpoint tables defined
in config/settings.py.
"""

from __future__ import annotations


def interpolate_score(value: float, points_table: list[tuple[float, float]]) -> float:
    """points_table is a sorted list of (x, score) pairs. Values below the
    first x clamp to the first score; values above the last x clamp to the
    last score; values in between are linearly interpolated.
    """
    if value is None or value != value:  # NaN check
        return 0.0

    table = sorted(points_table, key=lambda p: p[0])
    if value <= table[0][0]:
        return table[0][1]
    if value >= table[-1][0]:
        return table[-1][1]

    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x0 <= value <= x1:
            if x1 == x0:
                return y0
            fraction = (value - x0) / (x1 - x0)
            return y0 + fraction * (y1 - y0)
    return table[-1][1]


def band_score(value: float, table: list[tuple[float, float]]) -> float:
    """table is a list of (min_value_inclusive, score) sorted descending
    by min_value. Returns the score for the highest band the value
    qualifies for. Used for the explicit step tables in the spec
    (e.g. Collection Coverage bands) rather than linear interpolation.
    """
    if value is None or value != value:
        return 0.0
    for min_value, score in sorted(table, key=lambda p: -p[0]):
        if value >= min_value:
            return score
    return 0.0
