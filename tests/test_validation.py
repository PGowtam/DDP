from datetime import datetime

from src.models.schema import DatasetRecord, ProvenanceMetadata, ValidationStatus
from src.validation.rules import validate_record, metadata_completeness_score


def _valid_record() -> DatasetRecord:
    return DatasetRecord(
        dataset_id="ds1",
        title="A Dataset",
        description="A description",
        publisher="Publisher",
        source_url="https://example.com/data",
        landing_page_url="https://example.com",
        topics=["housing"],
        measures=["median_rent"],
        provenance=ProvenanceMetadata(
            source_organization="Publisher",
            source_url="https://example.com/data",
            retrieval_timestamp=datetime.utcnow(),
            metadata_source="test",
            access_method="test fetch",
        ),
    )


def test_fully_populated_record_validates_clean():
    record = _valid_record()
    status, errors, warnings = validate_record(record)
    # geography is UNKNOWN by default and no domain is set -> expect warnings, not errors
    assert status in (ValidationStatus.VALID, ValidationStatus.VALID_WITH_WARNINGS)
    assert errors == []


def test_missing_required_field_is_invalid():
    record = _valid_record()
    record.publisher = ""
    status, errors, warnings = validate_record(record)
    assert status == ValidationStatus.INVALID
    assert any("publisher" in e for e in errors)


def test_bad_url_is_flagged():
    record = _valid_record()
    record.source_url = "not-a-url"
    status, errors, warnings = validate_record(record)
    assert status == ValidationStatus.INVALID
    assert any("source_url" in e for e in errors)


def test_geometry_inconsistency_is_error():
    record = _valid_record()
    record.geography.geometry_available = True
    record.geography.geometry_type = "none"
    status, errors, warnings = validate_record(record)
    assert status == ValidationStatus.INVALID
    assert any("geometry" in e for e in errors)


def test_completeness_score_between_0_and_1():
    record = _valid_record()
    score = metadata_completeness_score(record)
    assert 0.0 <= score <= 1.0


def test_completeness_score_drops_when_fields_missing():
    full = metadata_completeness_score(_valid_record())
    sparse_record = _valid_record()
    sparse_record.description = None
    sparse_record.topics = []
    sparse_record.measures = []
    sparse = metadata_completeness_score(sparse_record)
    assert sparse < full
