# Demo Script (3-5 minutes)

## 1. Problem (30s)
"Public SDOH data is scattered across dozens of agencies, in different
formats, at different geographic resolutions, with inconsistent metadata.
UIUC's SDOH & Place Project is building a discovery tool to solve this. This
prototype demonstrates the same underlying problem -- discovery, metadata
normalization, geospatial-aware validation -- at small scale, with real
public data."

## 2. Data source (30s)
Run:
```bash
python -m sdoh pipeline
```
Point out: 3 real datasets from County Health Rankings & Roadmaps ingested
successfully; 2 additional adapters (Census ACS, CDC PLACES) fail
transparently because of this dev sandbox's network restrictions -- show
`data/metadata/pipeline_report.json` and explain that's the honest result,
not a hidden failure.

## 3. Metadata normalization (45s)
Open `data/metadata/chrr_v063_median_household_income_r2025.json`. Walk
through the canonical schema groups: identity, geography, time, structure,
access, provenance, quality. Emphasize `provenance.raw_sha256` -- every
normalized field traces back to a specific, hash-verified raw file.

## 4. Search (45s)
```bash
python -m sdoh search income
```
Then open the Streamlit UI:
```bash
streamlit run app/streamlit_app.py
```
Search "income", then clear it and filter by SDOH Domain =
`economic_stability`. Show the completeness score and validation status
badges.

## 5. Geographic filtering (30s)
In the UI, filter Geography = county. Explain the identifier-vs-geometry
distinction in `src/geography/inspect.py`: these datasets are county-level
via FIPS codes, not shapefiles -- `geometry_available` is correctly `False`,
not guessed `True`.

## 6. User dataset upload (30s)
Switch to the "Upload a dataset" tab, upload any small CSV with a
`county_fips`-like column and a numeric column. Show the inferred geography/
time/measure preview and the warnings it produces when something's missing.

## 7. Validation (30s)
```bash
python -m sdoh validate
```
Show a record with `VALID_WITH_WARNINGS` and explain what triggered the
warning (usually: no SDOH domain matched by the deterministic keyword
classifier) -- this is intentional transparency, not a bug being hidden.

## 8. Reproducibility (30s)
```bash
pytest
```
43 tests passing, covering schema validation, normalization, the validation
engine, search ranking, and adapter failure handling (including a test that
proves a failed fetch never produces a fabricated record).

## 9. Future improvements (20s)
Point to `docs/limitations.md` and `docs/future-work.md`: more sources once
run outside this sandbox, FastAPI layer, Docker, semantic search, real
geometry ingestion.

---

**Framing throughout:** this is presented as "I understand the shape of this
research data problem and can build a clean, reproducible, honestly-scoped
computational solution to a piece of it" -- not as GIS expertise or a claim
of building the actual SDOH & Place tool.
