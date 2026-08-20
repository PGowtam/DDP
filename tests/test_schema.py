from datetime import datetime, date

import pytest
from pydantic import ValidationError

from src.models.schema import (
    DatasetRecord, ProvenanceMetadata, TemporalMetadata, GeographyMetadata,
    GeographicLevel,
)


def _minimal_record(**overrides) -> DatasetRecord:
    defaults = dict(
        dataset_id="test_ds",
        title="Test Dataset",
        publisher="Test Publisher",
        source_url="https://example.com/data",
        provenance=ProvenanceMetadata(
            source_organization="Test Publisher",
            source_url="https://example.com/data",
            retrieval_timestamp=datetime.utcnow(),
            metadata_source="unit test",
        ),
    )
    defaults.update(overrides)
    return DatasetRecord(**defaults)


def test_minimal_record_is_valid():
    record = _minimal_record()
    assert record.dataset_id == "test_ds"
    assert record.geography.geographic_level == GeographicLevel.UNKNOWN.value


def test_required_fields_enforced():
    with pytest.raises(ValidationError):
        DatasetRecord(title="Missing dataset_id and provenance")


def test_temporal_end_before_start_rejected():
    with pytest.raises(ValidationError):
        TemporalMetadata(
            temporal_coverage_start=date(2023, 1, 1),
            temporal_coverage_end=date(2020, 1, 1),
        )


def test_geometry_identifier_distinction_defaults_false():
    geo = GeographyMetadata(geographic_level=GeographicLevel.COUNTY)
    assert geo.geometry_available is False
    assert geo.geometry_type == "none"


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        _minimal_record(unexpected_field="should fail")
