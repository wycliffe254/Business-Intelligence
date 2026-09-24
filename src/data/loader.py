"""
Data ingestion layer.

Responsible ONLY for reading the uploaded CSV into a raw, untouched
pandas DataFrame plus light structural checks (columns present). No
cleaning, no type coercion beyond what pandas does by default. This
keeps the "RAW DATA" concept genuinely raw so it can be compared against
the "VALIDATED / ANALYTICAL DATA" produced later in cleaning.py.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import pandas as pd

from config.settings import REQUIRED_COLUMNS


@dataclass
class LoadResult:
    success: bool
    raw_df: pd.DataFrame | None = None
    missing_columns: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)
    error_message: str = ""


def load_csv(file_like) -> LoadResult:
    """Load a CSV (path, buffer, or Streamlit UploadedFile) into a raw
    DataFrame and check that the required schema is present.
    """
    try:
        if hasattr(file_like, "read"):
            raw_bytes = file_like.read()
            if isinstance(raw_bytes, bytes):
                buffer = io.BytesIO(raw_bytes)
            else:
                buffer = io.StringIO(raw_bytes)
            df = pd.read_csv(buffer, dtype=str, keep_default_na=True)
        else:
            df = pd.read_csv(file_like, dtype=str, keep_default_na=True)
    except Exception as exc:  # noqa: BLE001
        return LoadResult(
            success=False,
            error_message=(
                "The uploaded file could not be parsed as a CSV. "
                f"Details: {exc}"
            ),
        )

    if df.empty:
        return LoadResult(
            success=False,
            error_message="The uploaded file contains no data rows.",
        )

    # Normalize header whitespace/case-insensitive matching without
    # silently renaming meaningfully different columns.
    df.columns = [c.strip() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    extra = [c for c in df.columns if c not in REQUIRED_COLUMNS]

    if missing:
        return LoadResult(
            success=False,
            raw_df=df,
            missing_columns=missing,
            extra_columns=extra,
            error_message=(
                "The uploaded file does not contain the required fields "
                "for this analysis. Missing columns: " + ", ".join(missing)
            ),
        )

    return LoadResult(
        success=True,
        raw_df=df,
        missing_columns=missing,
        extra_columns=extra,
    )


def load_default_sample() -> LoadResult:
    """Convenience loader for the bundled sample dataset."""
    from pathlib import Path

    sample_path = Path(__file__).resolve().parents[2] / "data" / "sample" / \
        "kenyan_sme_bi_financial_operational_data_1800_records.csv"
    return load_csv(str(sample_path))
