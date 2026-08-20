# Limitations

This is a small research prototype, not a production system. Known
limitations, honestly stated:

## Data coverage
- Only **3 datasets are actually ingested and validated** in this build, all
  from a single publisher (County Health Rankings & Roadmaps). This falls
  short of the brief's 5-10 datasets across multiple publishers.
- **Why:** this development sandbox's network egress is restricted to a
  package-registry allowlist (pypi, npm, github, etc.) and does not include
  `api.census.gov` or `data.cdc.gov`. Two additional adapters
  (`src/ingestion/census_acs.py`, `src/ingestion/cdc_places.py`) are fully
  implemented against real, documented public APIs and fail with the exact
  `403`/allowlist error this environment returns -- see
  `data/metadata/pipeline_report.json` after running the pipeline. They have
  not been run against live data by the author of this repository. Running
  `python -m sdoh pipeline` from a machine with normal internet access (and,
  for the Census adapter, a free API key) should ingest all 5 sources.
- All 3 successfully-ingested datasets are county-level. No census-tract,
  ZCTA, or point-level dataset has been ingested for real in this build, so
  the geometry-vs-identifier distinction in `src/geography/inspect.py` and
  the GeoJSON/Shapefile code path are exercised by unit tests with synthetic
  data, not by a real ingested geospatial file.

## Metadata interpretation
- CHR&R's raw measure files use opaque measure codes (e.g. `v063`). Two of
  the three ingested files' meanings were corroborated independently (see
  inline comments in `src/ingestion/chr.py`) rather than taken from a
  verified CHR&R data dictionary, which this project did not have direct
  access to during development. The third (`v001_otherdata`, race/ethnicity
  population estimates) is self-evident from its own column names. If a CHR&R
  data dictionary becomes available, these identifications should be
  re-verified against it.

## Ontology / classification
- The SDOH domain taxonomy (`configs/sdoh_taxonomy.yaml`) has roughly a dozen
  keywords per domain. It will misclassify or fail to classify (return
  `primary_domain: null`) datasets whose titles/descriptions don't contain a
  matching keyword -- this happened for two of the three real ingested CHR&R
  datasets in this build (see their `quality.warnings`).
- No LLM/embedding classifier is enabled by default.

## Search
- Ranking is a simple additive keyword-match score (title/description/
  keyword/topic/measure weighted). It has not been evaluated against a
  labeled relevance judgment set beyond the small manual spot-check in
  `docs/demo-script.md`.
- No semantic/embedding search layer is implemented (see `docs/future-work.md`).

## Duplicate detection
- `src/search/duplicates.py` uses title-token Jaccard overlap plus
  same-publisher/same-domain heuristics. With only 3 ingested records from
  one publisher, every pair in this build is flagged as at least
  "potentially related" -- this is a real, if unsurprising, result, not a
  bug, and illustrates why duplicate detection needs a genuinely diverse
  catalog to be useful.

## Geographic/GIS scope
- No live map rendering, no GeoPandas-based CRS reprojection, and no
  Shapefile ingestion have been exercised against real files in this build.
- No FIPS/GEOID crosswalk validation against an authoritative Census
  reference file is implemented; `src/normalization/geography.py`'s
  `fips_state_county_to_geoid` only checks digit-length formatting, not that
  the resulting GEOID corresponds to a real county.

## Engineering scope not attempted
- No FastAPI/REST layer, no Docker packaging, no CI workflow, and no
  semantic search are implemented in this build. See `docs/future-work.md`.
