"""
Date-parsing utilities.

The supplied dataset contains at least three date representations:
  - ISO:        YYYY-MM-DD                (majority of rows)
  - Dash:       DD-MM-YYYY                (minority)
  - Slash:      mixed DD/MM/YYYY and MM/DD/YYYY (minority, genuinely
                ambiguous in some rows, e.g. "19/12/2025" can only be
                DD/MM, while "08/19/2026" can only be MM/DD)

ASSUMPTION: where the day/month order cannot be determined from the
values themselves (both components <= 12), we default to day-first
(DD/MM/YYYY), consistent with Kenyan/international date convention, and
flag the row as an "ambiguous date" for the Data Quality Report. This is
a documented, isolated assumption rather than a silent guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

_ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_SEP_RE = re.compile(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$")


@dataclass
class DateParseResult:
    parsed: pd.Timestamp | None
    is_valid: bool
    is_ambiguous: bool
    raw_value: str


def parse_single_date(value) -> DateParseResult:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return DateParseResult(None, False, False, str(value))

    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "nat"}:
        return DateParseResult(None, False, False, text)

    m = _ISO_RE.match(text)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return DateParseResult(pd.Timestamp(year, month, day), True, False, text)
        except ValueError:
            return DateParseResult(None, False, False, text)

    m = _SEP_RE.match(text)
    if m:
        a, b, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a_could_be_day = 1 <= a <= 31
        b_could_be_day = 1 <= b <= 31
        a_could_be_month = 1 <= a <= 12
        b_could_be_month = 1 <= b <= 12

        day, month, ambiguous = None, None, False

        if a > 12 and b_could_be_month:
            # a must be the day
            day, month = a, b
        elif b > 12 and a_could_be_month:
            # b must be the day
            day, month = b, a
        elif a_could_be_month and b_could_be_month:
            # genuinely ambiguous -> default to day-first (ASSUMPTION)
            day, month = a, b
            ambiguous = True
        else:
            return DateParseResult(None, False, False, text)

        try:
            return DateParseResult(pd.Timestamp(year, month, day), True, ambiguous, text)
        except ValueError:
            return DateParseResult(None, False, False, text)

    return DateParseResult(None, False, False, text)


def parse_date_series(series: pd.Series) -> pd.DataFrame:
    """Vectorized-ish wrapper returning a DataFrame with parsed_date,
    is_valid_date, is_ambiguous_date columns aligned to the input index.
    """
    results = series.apply(parse_single_date)
    return pd.DataFrame(
        {
            "parsed_date": results.apply(lambda r: r.parsed),
            "is_valid_date": results.apply(lambda r: r.is_valid),
            "is_ambiguous_date": results.apply(lambda r: r.is_ambiguous),
        },
        index=series.index,
    )
