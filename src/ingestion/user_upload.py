"""
Metadata inference for user-uploaded regional CSV datasets.

Inspects an uploaded CSV's columns and produces a metadata *preview* the
user must review and confirm -- it never silently overwrites anything the
user explicitly supplies, and it never fabricates a value it can't infer
(e.g. a publisher name is left blank + flagged as a warning, not guessed).
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from src.geography.inspect import has_identifier_only_geography, has_lat_lon_columns
from src.normalization.geography import normalize_geographic_level

_GEO_ID_COLUMN_HINTS = ["fips", "geoid", "county_fips", "state_fips", "zip", "zcta", "tract"]
_TIME_COLUMN_HINTS = ["year", "date", "period", "yr"]
_CATEGORICAL_MAX_UNIQUE_RATIO = 0.2


@dataclass
class UploadInferenceResult:
    detected_columns: list[str] = field(default_factory=list)
    detected_geography_columns: list[str] = field(default_factory=list)
    detected_lat_lon: bool = False
    detected_time_columns: list[str] = field(default_factory=list)
    detected_numeric_measures: list[str] = field(default_factory=list)
    detected_categorical_columns: list[str] = field(default_factory=list)
    suggested_geographic_level: str = "unknown"
    row_count: int = 0
    warnings: list[str] = field(default_factory=list)


def infer_upload_metadata(csv_text: str, max_rows_scanned: int = 2000) -> UploadInferenceResult:
    reader = csv.reader(io.StringIO(csv_text))
    try:
        header = next(reader)
    except StopIteration:
        return UploadInferenceResult(warnings=["File appears to be empty."])

    rows = []
    for i, row in enumerate(reader):
        if i >= max_rows_scanned:
            break
        rows.append(row)

    result = UploadInferenceResult(detected_columns=header, row_count=len(rows))

    lowered = {c: c.lower() for c in header}
    result.detected_geography_columns = [
        c for c in header if any(h in lowered[c] for h in _GEO_ID_COLUMN_HINTS)
    ]
    result.detected_lat_lon = has_lat_lon_columns(header)
    result.detected_time_columns = [
        c for c in header if any(h in lowered[c] for h in _TIME_COLUMN_HINTS)
    ]

    # crude numeric vs categorical inference from a sample of values
    for col_idx, col in enumerate(header):
        values = [row[col_idx] for row in rows if col_idx < len(row) and row[col_idx] != ""]
        if not values:
            continue
        numeric_count = sum(1 for v in values if _looks_numeric(v))
        if numeric_count / len(values) > 0.9:
            result.detected_numeric_measures.append(col)
        else:
            unique_ratio = len(set(values)) / len(values)
            if unique_ratio <= _CATEGORICAL_MAX_UNIQUE_RATIO:
                result.detected_categorical_columns.append(col)

    if result.detected_geography_columns and "county" in " ".join(result.detected_geography_columns).lower():
        result.suggested_geographic_level = normalize_geographic_level("county")
    elif result.detected_geography_columns:
        result.suggested_geographic_level = "unknown"  # do not guess further
    elif result.detected_lat_lon:
        result.suggested_geographic_level = normalize_geographic_level("point")

    if not result.detected_geography_columns and not result.detected_lat_lon:
        result.warnings.append("No recognizable geographic identifier or lat/lon columns detected.")
    if not result.detected_time_columns:
        result.warnings.append("No recognizable time/date column detected; temporal coverage unknown.")
    if not result.detected_numeric_measures:
        result.warnings.append("No numeric measure columns detected.")

    return result


def _looks_numeric(value: str) -> bool:
    try:
        float(value.replace(",", ""))
        return True
    except ValueError:
        return False
