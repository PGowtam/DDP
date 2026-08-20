"""
Canonical metadata schema for the SDOH Data Discovery Pipeline.

Schema is organized into the same broad categories used by
Aardvark-family / GeoBlacklight-style geospatial metadata schemas:
identity, geography, temporal coverage, format, access, provenance, quality.

Every field is deliberately optional unless a dataset record cannot be
meaningfully validated without it (see REQUIRED_FIELDS in
src/validation/rules.py). Real public datasets are heterogeneous -- a
schema that forces every field to be populated would force fabrication.
"""
from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------

class GeographicLevel(str, Enum):
    """Controlled vocabulary for the geographic resolution of a dataset.

    Kept deliberately small and US-focused, matching what the real ingested
    sources in this prototype actually use. Extend as new adapters are added.
    """
    NATION = "nation"
    STATE = "state"
    COUNTY = "county"
    CENSUS_TRACT = "census_tract"
    ZCTA = "zcta"
    PLACE = "place"
    METRO_AREA = "metropolitan_statistical_area"
    POINT = "point"
    OTHER = "other"
    UNKNOWN = "unknown"


class GeometryType(str, Enum):
    NONE = "none"                # geography is identifier-only (e.g. FIPS), no shape
    POLYGON = "polygon"
    MULTIPOLYGON = "multipolygon"
    POINT = "point"
    LINE = "line"
    UNKNOWN = "unknown"


class FileFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    GEOJSON = "geojson"
    SHAPEFILE = "shapefile"
    XLSX = "xlsx"
    XML = "xml"
    API = "api"
    OTHER = "other"
    UNKNOWN = "unknown"


class AccessType(str, Enum):
    OPEN_DOWNLOAD = "open_download"
    OPEN_API = "open_api"
    REGISTRATION_REQUIRED = "registration_required"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class ValidationStatus(str, Enum):
    VALID = "valid"
    VALID_WITH_WARNINGS = "valid_with_warnings"
    INVALID = "invalid"
    NOT_YET_VALIDATED = "not_yet_validated"


SDOH_DOMAINS = (
    "economic_stability",
    "education_access_and_quality",
    "health_care_access_and_quality",
    "neighborhood_and_built_environment",
    "social_and_community_context",
)


# ---------------------------------------------------------------------------
# Sub-models, grouped the way docs/research-notes.md Section 2 describes
# ---------------------------------------------------------------------------

class GeographyMetadata(BaseModel):
    geographic_level: GeographicLevel = GeographicLevel.UNKNOWN
    geographic_unit: Optional[str] = Field(
        default=None,
        description="Free-text label for the unit, e.g. 'U.S. county' or 'census tract'.",
    )
    geographic_coverage: list[str] = Field(
        default_factory=list,
        description="States/regions covered, e.g. ['US-national'] or ['IL','IN'].",
    )
    geographic_identifiers: list[str] = Field(
        default_factory=list,
        description="Identifier scheme(s) used to key rows to places, e.g. ['fips_county'].",
    )
    state_coverage: bool = False
    county_coverage: bool = False
    tract_coverage: bool = False
    spatial_reference_system: Optional[str] = Field(
        default=None, description="e.g. 'EPSG:4326'. Only set if geometry_available."
    )
    geometry_available: bool = Field(
        default=False,
        description="True only if the dataset itself ships drawable geometry, "
        "not merely a geographic identifier such as a FIPS code.",
    )
    geometry_type: GeometryType = GeometryType.NONE


class TemporalMetadata(BaseModel):
    temporal_coverage_start: Optional[date] = None
    temporal_coverage_end: Optional[date] = None
    temporal_resolution: Optional[str] = Field(
        default=None, description="e.g. 'annual', 'multi-year estimate', 'point-in-time'."
    )
    reference_period: Optional[str] = Field(
        default=None, description="Source's own label for the period, e.g. '2019-2023 5-year estimate'."
    )
    update_frequency: Optional[str] = None

    @field_validator("temporal_coverage_end")
    @classmethod
    def end_after_start(cls, v, info):
        start = info.data.get("temporal_coverage_start")
        if v is not None and start is not None and v < start:
            raise ValueError("temporal_coverage_end is before temporal_coverage_start")
        return v


class DataStructureMetadata(BaseModel):
    file_format: FileFormat = FileFormat.UNKNOWN
    data_type: Optional[str] = Field(default=None, description="e.g. 'tabular', 'geospatial-tabular'.")
    schema_url: Optional[str] = None
    row_count: Optional[int] = Field(default=None, ge=0)
    column_count: Optional[int] = Field(default=None, ge=0)
    columns: list[str] = Field(default_factory=list)
    missingness_summary: dict[str, float] = Field(
        default_factory=dict,
        description="column_name -> fraction missing (0.0-1.0), computed from the actual raw data.",
    )


class AccessMetadata(BaseModel):
    access_type: AccessType = AccessType.UNKNOWN
    api_available: bool = False
    download_available: bool = False
    authentication_required: bool = False
    license: Optional[str] = None
    usage_restrictions: Optional[str] = None


class ProvenanceMetadata(BaseModel):
    """Every normalized field must be traceable back through this block."""
    source_organization: str
    source_url: str
    retrieval_timestamp: datetime
    metadata_source: str = Field(
        description="Where the metadata itself came from, e.g. 'source API response', "
        "'manually transcribed from source webpage on <date>'."
    )
    access_method: Optional[str] = Field(
        default=None,
        description="How the raw data was actually obtained in this build, e.g. "
        "'GitHub-hosted official release CSV (raw.githubusercontent.com)', "
        "'documented API, not fetched in this sandboxed session'.",
    )
    raw_file_path: Optional[str] = Field(default=None, description="Path under data/raw/.")
    raw_sha256: Optional[str] = None
    transformation_history: list[str] = Field(default_factory=list)


class DomainClassification(BaseModel):
    primary_domain: Optional[str] = None
    secondary_domains: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: list[str] = Field(default_factory=list)
    machine_generated: bool = Field(
        default=False,
        description="True only if an LLM/embedding step (not the deterministic "
        "rule-based classifier) produced this classification.",
    )


class QualityMetadata(BaseModel):
    validation_status: ValidationStatus = ValidationStatus.NOT_YET_VALIDATED
    validation_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata_completeness_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Fraction of scored fields populated. NOT a data-quality score -- "
        "see docs/metadata-schema.md for the distinction.",
    )


# ---------------------------------------------------------------------------
# Top-level canonical record
# ---------------------------------------------------------------------------

class DatasetRecord(BaseModel):
    """The canonical, normalized representation of one public dataset."""

    # Identity
    dataset_id: str = Field(description="Stable slug, unique within this pipeline.")
    title: str
    description: Optional[str] = None
    publisher: str
    source_url: str
    landing_page_url: Optional[str] = None

    # Subject / SDOH
    topics: list[str] = Field(default_factory=list)
    sdoh_domains: DomainClassification = Field(default_factory=DomainClassification)
    population: Optional[str] = None
    measures: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)

    # Groups
    geography: GeographyMetadata = Field(default_factory=GeographyMetadata)
    time: TemporalMetadata = Field(default_factory=TemporalMetadata)
    structure: DataStructureMetadata = Field(default_factory=DataStructureMetadata)
    access: AccessMetadata = Field(default_factory=AccessMetadata)
    provenance: ProvenanceMetadata
    quality: QualityMetadata = Field(default_factory=QualityMetadata)

    model_config = {
        "use_enum_values": True,
        "extra": "forbid",
    }
