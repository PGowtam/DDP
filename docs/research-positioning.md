# Research Positioning

## Problem

Public datasets relevant to Social Determinants of Health (SDOH) research are
scattered across dozens of federal agencies, academic labs, and nonprofit
publishers. They use inconsistent geographic identifiers (FIPS codes,
GEOIDs, ZCTAs, HEROP_IDs), different file formats, different temporal
coverage conventions, and widely varying metadata quality. A researcher who
wants to study the relationship between housing cost burden, food access, and
premature mortality must locate, download, decode, and reconcile at least three
different datasets before any analysis begins.

The publicly described [SDOH & Place Project](https://www.sdohplace.org/) Data
Discovery Search Tool (HEROP Lab, UIUC) addresses this problem at scale, with
keyword, AI, and map-based exploration. This prototype explores the same
computational problem at small scale, focusing on what normalization,
provenance, and discovery require at the pipeline level.

---

## Research Question

> Can a set of heterogeneous real public SDOH-adjacent datasets be ingested,
> normalized into a single canonical schema, validated for internal consistency,
> and made searchable by geography and SDOH domain — with every normalized
> field traceable back to its original source — using a lightweight,
> deterministic, and reproducible pipeline?

---

## Contribution

This prototype demonstrates:

1. **Ingestion without fabrication.** Five real public datasets are fetched
   from their actual publisher sources (GitHub, Socrata API), not mocked. Every
   raw file is SHA-256 hashed at retrieval time. Adapters that cannot fetch
   raise structured `AdapterError`, not silent failures or placeholder data.

2. **Canonical metadata normalization.** A single `DatasetRecord` Pydantic
   schema (organized as identity / subject / geography / temporal / structure /
   access / provenance / quality) represents datasets from five structurally
   different sources. The schema enforces internal consistency (e.g., `extra=
   "forbid"` catches typos; `temporal_end ≥ temporal_start` is a validator).

3. **Explicit provenance at the field level.** Every record carries a
   `ProvenanceMetadata` block documenting source URL, publisher, retrieval
   timestamp, access method, raw file path, SHA-256 hash, and a
   `transformation_history` list. Fields that are inferred (not directly
   sourced) are labeled as such.

4. **Geographic characterization without overclaiming.** The pipeline
   explicitly distinguishes datasets that have geographic *identifiers* (e.g.
   a FIPS column) from datasets that ship real drawable *geometry* (a shape).
   `geometry_available` is only ever `True` when geopandas can verify a
   real geometry column — never inferred from an identifier.

5. **Deterministic, explainable SDOH classification.** A YAML-driven keyword
   classifier maps dataset titles, descriptions, topics, and measures to the
   Healthy People 2030 five-domain SDOH taxonomy. The classifier is fully
   transparent: it returns the list of matching keywords as a `rationale`
   field and sets `machine_generated=False` to distinguish it from any future
   LLM-based step.

6. **Explainable search.** A scoring function (title×3 / description×2 /
   keyword×2 / topic×1.5 / measure×1.5) ranks results and returns a
   `matched_on` list for every result, so a user can always understand why
   Dataset A ranked above Dataset B.

7. **User upload prototype.** A Streamlit upload tab accepts a CSV and
   produces an inferred metadata *preview* — not an authoritative record.
   The pipeline explicitly flags inferred fields with warnings and does not
   automatically index anything, modeling the human-in-the-loop review
   described in the target GRA position.

8. **Reproducibility.** Running `python -m sdoh pipeline` re-derives all
   outputs in `data/metadata/` from scratch. No hand-edited generated files.

---

## Datasets Used

| Dataset | Publisher | Geography | Real data in this build? |
|---|---|---|---|
| Premature Death (YPLL), 2026 | County Health Rankings & Roadmaps | County | ✅ Yes |
| Median Household Income, 2025 | County Health Rankings & Roadmaps | County | ✅ Yes |
| Population by Race/Ethnicity, 2026 | County Health Rankings & Roadmaps | County | ✅ Yes |
| County Geographic Crosswalk | HEROP Lab / OEPS (UIUC) | County | ✅ Yes |
| PLACES Chronic Disease Estimates | CDC | County | ✅ Yes |
| Median Gross Rent (ACS 5-Year) | U.S. Census Bureau | County | Needs `CENSUS_API_KEY` |
| Social Vulnerability Index (SVI) | CDC/ATSDR | County, Tract | Needs ATSDR URL verification |

The heterogeneity across these sources (GitHub CSV vs. Socrata API vs. Census
API vs. ATSDR download) is itself the demonstration: metadata normalization
is necessary precisely because each source expresses geography, time, and
format differently.

---

## Limitations

- **Dataset scale.** Five datasets is a proof of concept, not a catalog.
  The real SDOH & Place Project indexes thousands. Scaling this pipeline
  would require a persistent database backend, parallelized ingestion, and
  a more sophisticated search layer.

- **GIS scope.** No GIS-native operations (reprojection, spatial joins,
  geometry simplification) are performed. The geometry distinction
  (`geometry_available`) is enforced logically; the geopandas code path
  exists but is exercised only in unit tests.

- **Ontology.** The SDOH taxonomy uses Healthy People 2030 domains with
  hand-curated keywords. It is a prototype taxonomy, not the official
  ontology used by the SDOH & Place Project or any other authoritative
  source. Keyword coverage is incomplete by design — new datasets require
  new keywords.

- **No semantic search.** Classification and search are keyword-based.
  Embedding-based semantic search would improve recall for datasets whose
  titles and descriptions don't contain exact keyword matches.

- **Reproducibility boundary.** "Reproducible" here means the pipeline
  re-derives the same outputs from the same source snapshot. If a publisher
  changes their data, the pipeline will reflect the change (or fail
  gracefully). It does not guarantee identical outputs across years.

---

## Future Research Directions

- **Semantic search.** Sentence-transformer embeddings on dataset
  descriptions could substantially improve recall, especially for
  datasets whose metadata uses domain-specific jargon not in the keyword
  list.

- **Ontology refinement.** A more expressive SDOH ontology (e.g., aligned
  with [OSHPD](https://hcai.ca.gov/) or
  [NCI Thesaurus](https://ncithesaurus.nci.nih.gov/)) would improve
  classification precision and support faceted browsing by concept, not
  just domain.

- **Spatial crosswalk.** A lightweight FIPS/GEOID validation module that
  checks identifiers against an authoritative Census reference file would
  catch common errors (stale FIPS codes from pre-2020 county boundary
  changes) before they propagate into analyses.

- **Richer geometry handling.** Ingesting GeoJSON or Shapefile sources
  would enable true map-based exploration and spatial clustering of
  datasets by geographic footprint.

- **Human-in-the-loop metadata validation.** The user upload workflow
  currently produces inference results for review. A production version
  would present a review form, allow field-level edits, and record the
  human reviewer's identity and timestamp as part of the provenance chain.

- **Scalable indexing.** For a catalog of thousands of datasets, the
  in-memory JSON index would need to be replaced with a proper search
  backend (e.g., Elasticsearch or a vector store for semantic search).

---

## Disclaimer

This is an independent research prototype developed to explore computational
approaches to data discovery and metadata workflows. It is not affiliated
with, endorsed by, or part of the SDOH & Place Project, the HEROP Lab, or
the University of Illinois at Urbana-Champaign.
