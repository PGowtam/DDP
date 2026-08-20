# SDOH Data Discovery & Metadata Pipeline

> **Disclaimer:** This is an independent research prototype. It is not
> affiliated with, endorsed by, or part of the SDOH & Place Project, the
> HEROP Lab, or the University of Illinois at Urbana-Champaign. Developed to
> explore computational approaches to data discovery and metadata normalization
> workflows relevant to publicly described SDOH research problems.

---

## Overview

A reproducible pipeline that ingests real public Social Determinants of Health
(SDOH) datasets from heterogeneous sources, normalizes them into a single
canonical metadata schema, validates every record, and makes them searchable
by keyword, geography, and SDOH domain — with complete provenance from every
normalized field back to a SHA-256-verified raw source file.

---

## Motivation

Public SDOH data is scattered across agencies in different formats, at
different geographic resolutions, with inconsistent (or missing) metadata.
Before any dataset can be discovered or compared, it must be consistently
described: what geography, what time period, what format, who published it,
and can that be verified? This pipeline builds a complete version of that
normalization and provenance-tracking workflow using real government and
publisher data end to end.

---

## Research Question

Can a set of heterogeneous, real public SDOH-adjacent datasets be ingested,
normalized into one canonical schema, validated, and made searchable by
geography and SDOH domain — with every normalized field traceable back to its
original source — using a lightweight, explainable, deterministic pipeline?

See `docs/research-positioning.md` for the full framing.

---

## Architecture

```
Source Adapters ──► Raw Data ──► Normalization ──► {Geographic Inspection,
SDOH Classification, Validation} ──► Canonical Metadata ──► Search Index ──►
{CLI, Streamlit UI, User Upload Prototype}
```

See `docs/architecture.md` for the full diagram. Each publisher has one
adapter that implements `discover → fetch → extract_metadata → normalize`.
Failures are caught per-adapter and reported in `data/metadata/pipeline_report.json`
— one source failing never crashes the rest of the pipeline.

---

## Data Sources

| Dataset | Publisher | Geography | Status |
|---|---|---|---|
| Premature Death (YPLL), county, 2026 | County Health Rankings & Roadmaps | County | **Ingested (real, SHA-256 verified)** |
| Median Household Income, county, 2025 | County Health Rankings & Roadmaps | County | **Ingested (real, SHA-256 verified)** |
| Population by Race/Ethnicity, county, 2026 | County Health Rankings & Roadmaps | County | **Ingested (real, SHA-256 verified)** |
| PLACES: Local Data for Better Health, county | CDC (Socrata API) | County | **Ingested (real, SHA-256 verified)** |
| County Geographic Crosswalk (FIPS/Name/State) | HEROP Lab / OEPS (UIUC) | County | **Ingested (real, SHA-256 verified)** |
| Median Gross Rent (ACS 5-Year), county, 2019–2023 | U.S. Census Bureau | County | Implemented — requires `CENSUS_API_KEY` |
| Social Vulnerability Index (SVI), county + tract, 2022 | CDC/ATSDR | County, Census Tract | Implemented — requires ATSDR URL verification |

**Verified pipeline run (2026-08-19):** 5/8 sources ingest successfully.
The 3 that fail do so with structured, actionable `AdapterError` messages,
not silent failures or fabricated data. See `data/metadata/pipeline_report.json`
after running.

---

## Canonical Metadata Schema

`src/models/schema.py` — Pydantic v2 `DatasetRecord` with `extra="forbid"`.
Organized as:

| Block | Key fields |
|---|---|
| **Identity** | `dataset_id`, `title`, `description`, `publisher`, `source_url` |
| **Subject/SDOH** | `topics`, `measures`, `sdoh_domains` (with `rationale` + `machine_generated` flag) |
| **Geography** | `geographic_level`, `geographic_identifiers`, `geometry_available` (only True when verified), `geometry_type` |
| **Temporal** | `temporal_coverage_start/end`, `temporal_resolution`, `reference_period` |
| **Structure** | `file_format`, `row_count`, `column_count`, `missingness_summary` |
| **Access** | `access_type`, `api_available`, `authentication_required`, `license` |
| **Provenance** | `source_url`, `retrieval_timestamp`, `access_method`, `raw_sha256`, `transformation_history` |
| **Quality** | `validation_status`, `validation_errors`, `warnings`, `metadata_completeness_score` |

Full documentation in `docs/metadata-schema.md`.

---

## Geographic Representation

`src/geography/inspect.py` enforces the distinction between:

- **Identifier-only geography** — dataset has a FIPS column but no drawable geometry.
  `geometry_available = False`.
- **Point geography** — dataset has lat/lon columns.
- **Real geometry** — dataset ships a GeoJSON/Shapefile and geopandas can verify it.
  Only then is `geometry_available = True`.

This distinction is explicit in every adapter and tested in the suite.
No adapter in this build has real geometry — all real ingested datasets are
tabular with FIPS identifiers.

---

## SDOH Classification

`src/ontology/classifier.py` — fully deterministic, YAML-driven keyword classifier.

- Taxonomy source: Healthy People 2030 five-domain SDOH framework
  (`configs/sdoh_taxonomy.yaml`)
- Classification method: keyword hit-count per domain; confidence = concentration × coverage
- Output fields: `primary_domain`, `secondary_domains`, `keywords` (matched),
  `rationale` (matched keyword list), `confidence`, `machine_generated=False`
- **Never represents inferred classification as authoritative source metadata**

---

## Search

`src/search/engine.py` — additive keyword scoring + hard facet filters.

**Scoring weights:**
- Title match: 3 pts/term
- Description match: 2 pts/term
- SDOH keyword match: 2 pts/term
- Topic match: 1.5 pts/term
- Measure match: 1.5 pts/term

**Hard facet filters:** geography level, SDOH domain, publisher, year range.

Every result includes a `matched_on` list explaining exactly which field
matched each query term. The Streamlit UI surfaces this in the search results.

```bash
$ python -m sdoh search income
[8.5] Median Household Income, County Data, 2025 release
      domain=economic_stability  geo=county  completeness=1.00
      matched: title:income, description:income, sdoh_keyword:income, topic:income
```

---

## User Dataset Workflow

`src/ingestion/user_upload.py` + Streamlit upload tab.

1. User uploads a CSV (≤5MB)
2. Pipeline infers: geography columns, time columns, numeric measures, categorical columns
3. Warns about fields it cannot infer (publisher, license, title)
4. Presents a **preview only** — not an authoritative record
5. UI displays: `"⚠️ This is an inferred metadata preview only. Nothing is indexed automatically."`
6. A production version would let the user edit and confirm before indexing

The separation between inferred and accepted metadata is a deliberate design
choice, modeled on the human-in-the-loop review workflow described for the
SDOH & Place Project.

---

## Provenance & Reproducibility

- Every `DatasetRecord` has a `ProvenanceMetadata` block: `source_url`,
  `source_organization`, `retrieval_timestamp`, `access_method`,
  `raw_file_path`, `raw_sha256`, `transformation_history`.
- `python -m sdoh pipeline` re-derives all `data/metadata/*.json` from scratch.
  No hand-edited generated files exist in the repo.
- Raw files are gitignored (`data/raw/*`); only `.gitkeep` is committed.
  Reproducibility is at the pipeline level given a source snapshot, not
  guaranteed across future source changes.

---

## Validation

`src/validation/rules.py` — explainable rule engine.

Validates: required fields present, URLs syntactically valid, date ordering
consistent, geometry / geometry_type consistency, provenance completeness,
SDOH domain in controlled vocabulary.

`metadata_completeness_score` is the fraction of scored metadata fields
populated. **This is not a data quality score** — it measures metadata
completeness only. The distinction is documented in `docs/metadata-schema.md`.

---

## Installation

```bash
git clone https://github.com/PGowtam/DDP
cd DDP
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

---

## Running the Pipeline

```bash
python -m sdoh pipeline      # discover → fetch → normalize → classify → validate → index
python -m sdoh validate      # print validation status per record
python -m sdoh search income # keyword + facet search
python -m sdoh duplicates    # potential-duplicate report
streamlit run app/streamlit_app.py
```

For Census ACS, set a free API key first:

```bash
export CENSUS_API_KEY=your_key_here   # https://api.census.gov/data/key_signup.html
```

---

## Testing

```bash
pip install -e ".[dev]"
pytest
```

**43 tests, 43 passed, 0 warnings** (Python 3.13).

Coverage: schema validation, geography/format normalization, validation rules,
search ranking, adapter failure isolation, user-upload inference.
All tests are network-free and deterministic.

---

## Evaluation

See `docs/evaluation.md` for a full search evaluation run against the live index.

---

## Demo

See `docs/professor-demo.md` for a complete 3–5 minute walkthrough.

---

## Limitations

See `docs/limitations.md` — read this before drawing conclusions from
`docs/evaluation.md`. Key limits: 5 of 8 sources ingest in this environment;
no live geometry; taxonomy keyword coverage is incomplete by design.

---

## Future Research

See `docs/future-work.md` — semantic search, FIPS/GEOID crosswalk validation,
richer geometry handling, FastAPI layer, Docker/CI.

---

## GRA Relevance

See `docs/gra-relevance.md` for a direct mapping of project components to the
GRA position responsibilities.
