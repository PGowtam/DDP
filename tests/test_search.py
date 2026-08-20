from datetime import datetime, date

from src.models.schema import DatasetRecord, ProvenanceMetadata, GeographyMetadata, GeographicLevel, TemporalMetadata
from src.search.engine import SearchIndex


def _record(dataset_id, title, description="", geo_level=GeographicLevel.COUNTY, domain=None, year=None):
    r = DatasetRecord(
        dataset_id=dataset_id,
        title=title,
        description=description,
        publisher="Publisher",
        source_url="https://example.com/" + dataset_id,
        geography=GeographyMetadata(geographic_level=geo_level),
        time=TemporalMetadata(reference_period=str(year) if year else None),
        provenance=ProvenanceMetadata(
            source_organization="Publisher",
            source_url="https://example.com/" + dataset_id,
            retrieval_timestamp=datetime.utcnow(),
            metadata_source="test",
        ),
    )
    if domain:
        r.sdoh_domains.primary_domain = domain
    return r


def _index():
    records = [
        _record("ds_housing", "Housing Cost Burden by County", "median rent and housing burden", domain="neighborhood_and_built_environment", year=2022),
        _record("ds_income", "Median Household Income", "income and poverty statistics", domain="economic_stability", year=2023),
        _record("ds_tract", "Housing Vacancy by Census Tract", "vacancy rates", geo_level=GeographicLevel.CENSUS_TRACT, year=2021),
    ]
    return SearchIndex(records)


def test_keyword_search_ranks_title_matches_highest():
    results = _index().search(query="housing")
    ids = [r.record.dataset_id for r in results]
    assert "ds_housing" in ids
    assert "ds_tract" in ids
    assert "ds_income" not in ids


def test_geography_filter():
    results = _index().search(geography_level=GeographicLevel.CENSUS_TRACT)
    ids = [r.record.dataset_id for r in results]
    assert ids == ["ds_tract"]


def test_domain_filter():
    results = _index().search(sdoh_domain="economic_stability")
    ids = [r.record.dataset_id for r in results]
    assert ids == ["ds_income"]


def test_empty_query_with_filter_returns_all_matching_facet():
    results = _index().search(query=None, geography_level=GeographicLevel.COUNTY)
    ids = {r.record.dataset_id for r in results}
    assert ids == {"ds_housing", "ds_income"}


def test_no_match_returns_empty():
    results = _index().search(query="nonexistent_keyword_xyz")
    assert results == []
