"""
Lightweight geographic inspection utilities.

The core distinction this module enforces is:

    geography represented by identifiers (e.g. a FIPS code column)
        is NOT the same thing as
    geography represented by actual spatial geometry (a shape a map can draw).

Uses simple, explainable heuristics on column names and file extensions,
and (optionally, if geopandas is installed) inspects real geometry/CRS
from GeoJSON/Shapefile inputs. Never infers geometry_available=True from
a dataset that only has identifier columns.
"""
from __future__ import annotations

from pathlib import Path

from src.models.schema import GeometryType

_GEOID_COLUMN_HINTS = {
    "fips", "geoid", "fips_state", "fips_county", "county_fips", "state_fips",
    "statecode", "countycode", "herop_id", "zcta", "zip", "tract",
}
_LATLON_HINTS = {"lat", "latitude", "lon", "lng", "longitude"}


def has_identifier_only_geography(columns: list[str]) -> bool:
    lowered = {c.lower() for c in columns}
    return bool(lowered & _GEOID_COLUMN_HINTS) and not bool(lowered & _LATLON_HINTS)


def has_lat_lon_columns(columns: list[str]) -> bool:
    lowered = {c.lower() for c in columns}
    has_lat = any(h in lowered for h in {"lat", "latitude"})
    has_lon = any(h in lowered for h in {"lon", "lng", "longitude"})
    return has_lat and has_lon


def inspect_file_geometry(path: Path) -> tuple[bool, GeometryType, str | None]:
    """Returns (geometry_available, geometry_type, spatial_reference_system).
    Uses geopandas if available and the file extension suggests real geometry;
    otherwise returns conservative "no geometry" defaults."""
    suffix = path.suffix.lower()
    if suffix not in {".geojson", ".shp", ".json"}:
        return False, GeometryType.NONE, None

    try:
        import geopandas as gpd  # optional dependency
    except ImportError:
        # We can't verify geometry without geopandas; do not guess "yes".
        return False, GeometryType.UNKNOWN, None

    try:
        gdf = gpd.read_file(path)
    except Exception:
        return False, GeometryType.NONE, None

    if gdf.empty or "geometry" not in gdf.columns:
        return False, GeometryType.NONE, None

    geom_types = set(gdf.geometry.geom_type.dropna().unique())
    if geom_types & {"Polygon", "MultiPolygon"}:
        gtype = GeometryType.MULTIPOLYGON if "MultiPolygon" in geom_types else GeometryType.POLYGON
    elif geom_types & {"Point", "MultiPoint"}:
        gtype = GeometryType.POINT
    elif geom_types & {"LineString", "MultiLineString"}:
        gtype = GeometryType.LINE
    else:
        gtype = GeometryType.UNKNOWN

    crs = str(gdf.crs) if gdf.crs else None
    return True, gtype, crs
