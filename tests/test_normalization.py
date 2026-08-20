from src.normalization.geography import normalize_geographic_level, fips_state_county_to_geoid
from src.normalization.formats import normalize_file_format
from src.models.schema import GeographicLevel, FileFormat

import pytest


@pytest.mark.parametrize("raw,expected", [
    ("County", GeographicLevel.COUNTY),
    ("counties", GeographicLevel.COUNTY),
    ("county-level", GeographicLevel.COUNTY),
    ("US county", GeographicLevel.COUNTY),
    ("Census Tract", GeographicLevel.CENSUS_TRACT),
    ("ZIP Code", GeographicLevel.ZCTA),
    ("state", GeographicLevel.STATE),
    ("Metropolitan Statistical Area", GeographicLevel.METRO_AREA),
    ("something nonsensical", GeographicLevel.UNKNOWN),
    (None, GeographicLevel.UNKNOWN),
])
def test_geography_normalization(raw, expected):
    assert normalize_geographic_level(raw) == expected


def test_geography_normalization_does_not_collapse_distinct_concepts():
    # county and census tract must never map to the same value
    assert normalize_geographic_level("county") != normalize_geographic_level("census tract")
    assert normalize_geographic_level("zip code") != normalize_geographic_level("county")


@pytest.mark.parametrize("raw,expected", [
    ("CSV", FileFormat.CSV),
    ("csv", FileFormat.CSV),
    ("Comma Separated Values", FileFormat.CSV),
    ("GeoJSON", FileFormat.GEOJSON),
    ("Shapefile", FileFormat.SHAPEFILE),
    (None, FileFormat.UNKNOWN),
])
def test_format_normalization(raw, expected):
    assert normalize_file_format(raw) == expected


def test_fips_geoid_construction():
    assert fips_state_county_to_geoid("17", "019") == "17019"
    assert fips_state_county_to_geoid(1, 1) == "01001"


def test_fips_geoid_rejects_garbage():
    with pytest.raises(ValueError):
        fips_state_county_to_geoid("abc", "019")
