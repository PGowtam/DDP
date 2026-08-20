# Canonical Metadata Schema

Defined in `src/models/schema.py` as a Pydantic `DatasetRecord`. Every field
group below corresponds to a section of the project brief.

| Group | Fields | Notes |
|---|---|---|
| Identity | `dataset_id`, `title`, `description`, `publisher`, `source_url`, `landing_page_url` | `dataset_id` is a stable slug, unique within this pipeline. |
| Subject/SDOH | `topics`, `sdoh_domains` (nested `DomainClassification`), `population`, `measures`, `concepts` | `sdoh_domains.machine_generated` is `False` for every record in this build -- only the deterministic rule-based classifier is enabled (Phase 6). |
| Geography | `GeographyMetadata`: `geographic_level`, `geographic_unit`, `geographic_coverage`, `geographic_identifiers`, `state_coverage`/`county_coverage`/`tract_coverage`, `spatial_reference_system`, `geometry_available`, `geometry_type` | `geometry_available` defaults to `False` and is only ever set `True` when the raw file itself contains drawable geometry (checked in `src/geography/inspect.py`) -- never inferred from an identifier column such as a FIPS code. |
| Time | `TemporalMetadata`: `temporal_coverage_start/end`, `temporal_resolution`, `reference_period`, `update_frequency` | Pydantic validator rejects `end < start` at construction time. |
| Data Structure | `DataStructureMetadata`: `file_format`, `data_type`, `schema_url`, `row_count`, `column_count`, `columns`, `missingness_summary` | `row_count`/`column_count`/`missingness_summary` are computed directly from the fetched raw file, never estimated. |
| Access | `AccessMetadata`: `access_type`, `api_available`, `download_available`, `authentication_required`, `license`, `usage_restrictions` | |
| Provenance | `ProvenanceMetadata`: `source_organization`, `source_url`, `retrieval_timestamp`, `metadata_source`, `access_method`, `raw_file_path`, `raw_sha256`, `transformation_history` | This is the only *required* nested model (every other group has defaults) -- a record with no provenance cannot be constructed. |
| Quality | `QualityMetadata`: `validation_status`, `validation_errors`, `warnings`, `metadata_completeness_score` | Populated by the pipeline, not by adapters. |

## `metadata_completeness_score` vs. a "data quality score"

`metadata_completeness_score` (`src/validation/rules.py`) is the fraction of
a fixed set of *metadata* fields (title, description, publisher, source_url,
topics, measures, landing_page_url) that are populated. It says nothing
about whether the underlying *data* is accurate, unbiased, or fit for a
particular research use -- a dataset can have 100% metadata completeness
and still have significant known limitations in the data itself (see, e.g.,
CHR&R's own published caveats about small-county reliability). The two
concepts are deliberately named and computed differently in this codebase
so they are never confused.

## Controlled vocabularies

`GeographicLevel`, `GeometryType`, `FileFormat`, `AccessType`,
`ValidationStatus`, and `SDOH_DOMAINS` are all closed enumerations. Genuinely
different geographic concepts (county vs. census tract vs. ZCTA vs. MSA) are
never collapsed into one value -- see `src/normalization/geography.py` and
its tests in `tests/test_normalization.py`.
