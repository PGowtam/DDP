# Architecture

## Pipeline flow

```text
Public Data Sources (heterogeneous: static CSV releases, JSON/SODA APIs)
        |
        v
Source Adapters (src/ingestion/*.py, one per publisher)
   discover() -> fetch() -> extract_metadata()
        |
        v
Raw Data (data/raw/, byte-identical to source, sha256-hashed, never edited)
        |
        v
normalize() -> Canonical DatasetRecord (src/models/schema.py, Pydantic)
        |
        +--------> Geographic Inspection (src/geography/inspect.py)
        |           identifier-only vs. real geometry
        |
        +--------> SDOH Classification (src/ontology/classifier.py)
        |           deterministic keyword rules over configs/sdoh_taxonomy.yaml
        |
        +--------> Validation (src/validation/rules.py)
        |           required fields, URL/date/geo/provenance checks,
        |           metadata_completeness_score
        |
        v
Canonical Metadata (data/metadata/*.json, one file per dataset + index.json)
        |
        v
Search Index (src/search/engine.py -- in-memory, rebuilt from index.json)
        |
        +--------> CLI (python -m sdoh ...)
        |
        +--------> Streamlit UI (app/streamlit_app.py)
        |
        +--------> User Upload Pipeline (src/ingestion/user_upload.py)
```

There is no FastAPI/REST layer or Docker packaging in this build -- see
`docs/future-work.md`. The CLI and Streamlit UI both call the same
`src/pipeline`, `src/search`, and `src/models` modules directly, so there is
no duplicated business logic between them.

## Why a custom adapter architecture instead of one ingestion script

Each source in `src/ingestion/` is a subclass of `DatasetSourceAdapter`
(`src/ingestion/base.py`) implementing four methods: `discover`, `fetch`,
`extract_metadata`, `normalize`. Adding a new source means writing one new
adapter file and registering its class in `src/pipeline/pipeline.py`'s
`ALL_ADAPTERS` list -- nothing else in normalization, validation, search, or
the UI needs to change, because they all operate on the canonical
`DatasetRecord`, not on any source-specific representation.

## Why no Solr / Elasticsearch / vector database

The SDOH & Place Project uses Apache Solr for production-scale search.
At the scale of ~3-10 datasets in this pipeline, an in-memory Python ranking
function (`src/search/engine.py`) is easier to read, easier to test, and
produces identical *kinds* of results (keyword + facet search with an
explainable score). The `SearchIndex` class is the single seam where a real
search backend could be substituted later without touching the CLI or UI.

## Why the canonical schema looks the way it does

See `docs/metadata-schema.md`. The schema groups fields the same way
Aardvark-family/GeoBlacklight-style geospatial metadata schemas do:
identity, geography, time, structure, access, provenance, quality.

## Error handling philosophy

`AdapterError` is the only exception type the pipeline expects from a
source's `fetch()`/`extract_metadata()`/`normalize()`. When raised, the
pipeline records the failure in `data/metadata/pipeline_report.json` and
moves on to the next source -- it never substitutes fabricated data. This is
exercised for real in this build: `src/ingestion/census_acs.py` and
`src/ingestion/cdc_places.py` both fail in this sandboxed environment
(network egress restriction, see `docs/limitations.md`), and that failure is
visible in the pipeline report rather than hidden.
