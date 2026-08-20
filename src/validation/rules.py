"""
Validation engine. Runs a set of explainable rules over a DatasetRecord and
returns (status, errors, warnings). Never mutates the record's substantive
fields -- only src/pipeline writes quality.* back onto the record.
"""
from __future__ import annotations

from urllib.parse import urlparse

from src.models.schema import DatasetRecord, ValidationStatus, GeographicLevel, SDOH_DOMAINS

REQUIRED_FIELDS = ("dataset_id", "title", "source_url", "publisher")

# Fields scored for metadata_completeness_score (Phase 8). Kept separate from
# REQUIRED_FIELDS: completeness is informational, required-ness is a hard rule.
COMPLETENESS_FIELDS = (
    "title", "description", "publisher", "source_url", "topics",
    "measures", "landing_page_url",
)


def _is_valid_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return bool(parsed.scheme) and bool(parsed.netloc)


def validate_record(record: DatasetRecord) -> tuple[ValidationStatus, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    # Required fields
    for field_name in REQUIRED_FIELDS:
        if not getattr(record, field_name, None):
            errors.append(f"Missing required field: {field_name}")

    # URL validation
    if record.source_url and not _is_valid_url(record.source_url):
        errors.append(f"source_url is not a syntactically valid URL: {record.source_url!r}")
    if record.landing_page_url and not _is_valid_url(record.landing_page_url):
        warnings.append(f"landing_page_url is not a syntactically valid URL: {record.landing_page_url!r}")

    # Date validation (also enforced by the schema's own field_validator, but
    # re-checked here so validation errors are collected in one place)
    t = record.time
    if t.temporal_coverage_start and t.temporal_coverage_end:
        if t.temporal_coverage_end < t.temporal_coverage_start:
            errors.append("time.temporal_coverage_end is before time.temporal_coverage_start")

    # Geography validation: controlled vocabulary is enforced by the Enum
    # itself at the schema level, so here we just flag UNKNOWN as a warning.
    geo_level = record.geography.geographic_level
    if geo_level in (GeographicLevel.UNKNOWN, "unknown"):
        warnings.append("geography.geographic_level is UNKNOWN")
    if record.geography.geometry_available and record.geography.geometry_type in ("none",):
        errors.append("geometry_available=True but geometry_type is 'none' (inconsistent)")

    # Provenance validation
    if not record.provenance.source_organization:
        errors.append("provenance.source_organization is missing")
    if not record.provenance.retrieval_timestamp:
        errors.append("provenance.retrieval_timestamp is missing")
    if not record.provenance.access_method:
        warnings.append("provenance.access_method is not documented")

    # SDOH domain validation
    primary = record.sdoh_domains.primary_domain
    if primary and primary not in SDOH_DOMAINS:
        errors.append(f"sdoh_domains.primary_domain {primary!r} is not in the controlled taxonomy")
    if primary is None:
        warnings.append("No SDOH domain could be classified from title/description/measures")

    if errors:
        status = ValidationStatus.INVALID
    elif warnings:
        status = ValidationStatus.VALID_WITH_WARNINGS
    else:
        status = ValidationStatus.VALID

    return status, errors, warnings


def metadata_completeness_score(record: DatasetRecord) -> float:
    """Fraction of COMPLETENESS_FIELDS that are populated. This is a
    reproducible completeness measure, NOT a claim about data quality --
    see docs/metadata-schema.md."""
    populated = 0
    for field_name in COMPLETENESS_FIELDS:
        value = getattr(record, field_name, None)
        if isinstance(value, (list, dict)):
            populated += 1 if len(value) > 0 else 0
        else:
            populated += 1 if value not in (None, "") else 0
    return round(populated / len(COMPLETENESS_FIELDS), 2)
