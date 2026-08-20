"""
Normalizes free-text geography terms into the controlled GeographicLevel
vocabulary. Deliberately conservative: distinct geographic concepts (county
vs. tract vs. ZIP vs. MSA) are never collapsed into each other, per the
project's research-integrity rules.
"""
from __future__ import annotations

from src.models.schema import GeographicLevel

# Each canonical level maps to a list of surface forms seen "in the wild"
# across the sources this pipeline ingests (and common synonyms documented
# in Census Bureau geography guides). This table is intentionally small and
# grows only when a new adapter actually needs a new synonym.
_SYNONYMS: dict[GeographicLevel, list[str]] = {
    GeographicLevel.NATION: ["nation", "national", "united states", "us", "u.s."],
    GeographicLevel.STATE: ["state", "states", "state-level"],
    GeographicLevel.COUNTY: [
        "county", "counties", "county-level", "us county", "u.s. county",
        "county fips",
    ],
    GeographicLevel.CENSUS_TRACT: ["census tract", "tract", "tracts"],
    GeographicLevel.ZCTA: [
        "zcta", "zip code tabulation area", "zip code", "zip",
    ],
    GeographicLevel.PLACE: ["place", "places", "city", "town"],
    GeographicLevel.METRO_AREA: [
        "msa", "metropolitan statistical area", "metro area", "cbsa",
    ],
    GeographicLevel.POINT: ["point", "lat/lon", "latitude/longitude", "address"],
}

_LOOKUP: dict[str, GeographicLevel] = {
    synonym: level for level, synonyms in _SYNONYMS.items() for synonym in synonyms
}


def normalize_geographic_level(raw_text: str | None) -> GeographicLevel:
    """Map free text like 'County-level' or 'US county' to GeographicLevel.COUNTY.
    Returns GeographicLevel.UNKNOWN (not a guess) if nothing matches."""
    if not raw_text:
        return GeographicLevel.UNKNOWN
    key = raw_text.strip().lower()
    if key in _LOOKUP:
        return _LOOKUP[key]
    # fall back to substring match, but only if unambiguous
    matches = {level for synonym, level in _LOOKUP.items() if synonym in key}
    if len(matches) == 1:
        return matches.pop()
    return GeographicLevel.UNKNOWN


def fips_state_county_to_geoid(state_fips: str, county_fips: str) -> str:
    """Combine 2-digit state FIPS + 3-digit county FIPS into a 5-digit GEOID,
    the U.S. Census Bureau's standard county identifier."""
    s = str(state_fips).strip().zfill(2)
    c = str(county_fips).strip().zfill(3)
    if len(s) != 2 or len(c) != 3 or not (s + c).isdigit():
        raise ValueError(f"Invalid state/county FIPS pair: {state_fips!r}, {county_fips!r}")
    return s + c
