# SDOH Data Discovery & Metadata Pipeline

## Overview

A research-quality pipeline that discovers, ingests, normalizes,
validates, indexes, and makes searchable real public
Social-Determinants-of-Health (SDOH) datasets — with full provenance from
canonical metadata field back to a hash-verified raw source file.

Built to support the SDOH & Place Project's Data Discovery Search Tool
(HEROP Lab, UIUC), demonstrating data engineering and ML skills applied
to geospatial public-health data.

## Motivation

Public SDOH data is scattered across many agencies, in different formats,
at different geographic resolutions, with inconsistent (or missing)
metadata. Before any dataset can be discovered or compared, it has to be
described consistently -- what geography, what time period, what format,
who published it, and can that be verified. This pipeline builds a
complete version of that workflow, using real government/publisher
data end to end.

## Research Question

Can a set of heterogeneous, real public SDOH-adjacent datasets be
ingested, normalized into one canonical schema, validated, and made
searchable/filterable by geography and SDOH domain — with every normalized
field traceable back to its original source — using a lightweight,
explainable pipeline?

## System Architecture

See `docs/architecture.md` for the full diagram and rationale. In short:

```
Source Adapters -> Raw Data -> Normalization -> {Geographic Inspection,
SDOH Classification, Validation} -> Canonical Metadata -> Search Index ->
{CLI, Streamlit UI, User Upload Prototype}
```

## Data Sources

| Dataset | Publisher | Geography | Status |
|---|---|---|---|
| Premature Death (YPLL), county data | County Health Rankings & Roadmaps | County | **Ingested (real)** |
| Median Household Income, county data | County Health Rankings & Roadmaps | County | **Ingested (real)** |
| Population by Race/Ethnicity, county data | County Health Rankings & Roadmaps | County | **Ingested (real)** |
| Median Gross Rent (ACS 5-Year), county data | U.S. Census Bureau | County | Implemented, not fetched in this sandbox |
| PLACES chronic disease estimates, county data | CDC | County | Implemented, not fetched in this sandbox |
| CDC/ATSDR Social Vulnerability Index (SVI) | CDC/ATSDR | County, Tract | Implemented, not fetched in this sandbox |
| Opioid Environment Policy Scan (OEPS) | HEROP Lab (UIUC) | County | Implemented, not fetched in this sandbox |

Two adapters (`census_acs`, `cdc_places`) and the new ones (`cdc_svi`, `oeps`) require network access. Run `python -m sdoh pipeline` from a machine with normal
internet access (and a free Census API key) to ingest all 7. See `docs/limitations.md`.

## Metadata Schema

See `docs/metadata-schema.md`. Canonical `DatasetRecord` (Pydantic v2) in
`src/models/schema.py`, grouped into identity / subject-SDOH / geography /
time / structure / access / provenance / quality.

## Pipeline

```bash
pip install -e .
python -m sdoh pipeline      # discover -> fetch -> normalize -> classify -> validate -> index
python -m sdoh validate      # print validation status per record
python -m sdoh search income # deterministic keyword + facet search
python -m sdoh duplicates    # potential-duplicate / related-dataset report
```

## Search

`src/search/engine.py` -- an explainable, additive keyword-match ranking
function (title/description/keyword/topic/measure) plus hard facet filters
(geography level, SDOH domain, publisher, year range). No search server
required. See `docs/evaluation.md` for a real (small) evaluation run.

## Geographic Metadata

`src/geography/inspect.py` and the schema's `GeographyMetadata` block
distinguish datasets whose geography is represented only by an identifier
(e.g. a FIPS code column) from datasets that ship real, drawable geometry --
`geometry_available` is only ever `True` when actually verified, never
inferred from an identifier. See `docs/metadata-schema.md`.

## User Dataset Upload

The Streamlit app's "Upload a dataset" tab (`src/ingestion/user_upload.py`)
lets a user drop in a CSV and see an inferred metadata preview (geography
columns, time columns, numeric measures, categorical columns, warnings) --
without silently accepting it into the index. This is this project's own
independent prototype of that workflow; see `docs/research-notes.md` for why.

## Example Results

```
$ python -m sdoh search income
[8.5] Median Household Income, County Data, 2025 release  (County Health Rankings & Roadmaps ...)
        domain=economic_stability  geo=county  completeness=1.0
```

See `docs/demo-script.md` for a full walkthrough and `docs/evaluation.md`
for computed ingestion/search numbers.

## Reproducibility

- Every canonical metadata field traces back to a `provenance` block with a
  source URL, retrieval timestamp, access method, and SHA-256 hash of the raw
  file -- see `docs/data-lineage.md`.
- `python -m sdoh pipeline` re-derives everything in `data/metadata/` from
  scratch; nothing in that directory is hand-edited.

## Installation

```bash
git clone <this-repo>
cd sdoh-data-discovery-pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Running Locally

```bash
python -m sdoh pipeline
streamlit run app/streamlit_app.py
python scripts/demo.py
```

## Testing

```bash
pip install -e ".[dev]"
pytest
```

43 tests across schema validation, geography/format normalization, the
validation engine, search ranking, adapter failure handling, and
user-upload inference.

## Limitations

See `docs/limitations.md` -- read this before drawing conclusions from
`docs/evaluation.md`.

## Future Research

See `docs/future-work.md` -- more sources, FastAPI layer, Docker/CI,
optional semantic search, real geometry ingestion, FIPS/GEOID crosswalk
validation.

## Skills Demonstrated

```
Computer Science + Data Engineering + Machine Learning +
Research Methodology + Geospatial/Data-Discovery
```
