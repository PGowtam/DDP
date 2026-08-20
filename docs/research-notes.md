# Research Notes: The SDOH & Place Project's Data Discovery Tool

**Purpose of this document.** Background research on the target project
(`https://search.sdohplace.org/`) compiled from public sources, used to inform
design decisions in this pipeline.

---

## 1. Project overview

### 1.1 Who runs it and why
- The SDOH & Place Project is led by the **Healthy Regions & Policies Lab
  (HEROP Lab)** at the University of Illinois Urbana-Champaign Department of
  Geography & GIScience (Dr. Marynia Kolak), in collaboration with Dr. Sheng
  (ChengXi) Zhai's team in the Department of Computer Science, and funded by
  the **Robert Wood Johnson Foundation (RWJF)**.
- Its stated mission is to be a "one stop shop" for finding free, high-quality,
  place-based Social Determinants of Health (SDOH) data, searchable by topic
  and/or location across rural, urban, and suburban U.S. geographies.
- The project has three visible components: (1) a **Data Discovery** search
  application, (2) a **Metadata Manager** application for curating records, and
  (3) a **Community Toolkit** for teaching people to work with SDOH data.

### 1.2 Technical architecture
- The Data Discovery frontend is built with **Next.js / React**.
- The search backend is **Apache Solr**, chosen for its full-text, vector, and
  geospatial indexing/retrieval features.
- The platform's architecture and metadata approach is explicitly **inspired by
  GeoBlacklight**, a well-known multi-institutional open-source geospatial
  discovery platform used by many academic library GIS portals.
- According to the team's own July 2025 conference recap, rather than deploying
  GeoBlacklight out of the box, the team built a **custom search interface**
  embedded directly in their website, while *reusing the same indexing software
  (Solr) and the same metadata schema* that GeoBlacklight uses: the
  **OGM Aardvark** metadata schema (a widely adopted, versioned, open geospatial
  metadata specification maintained by the Open Geospatial Metadata community).
- A companion open-source project, **SDOHPlace-MetadataManager**, is a Flask
  application that writes metadata records directly into the Solr index. Its
  public documentation mentions a **"HEROP_ID"** -- an internally defined
  identifier that is "a slight variation on the commonly used standard GEOID"
  (the Census Bureau's standard geographic identifier), used to key geographic
  boundary records to Census-defined geographies.
- The team has built and is iterating on an **"AI-Inspired Search Mode"**: an
  LLM (OpenAI API) translates a natural-language question into a structured,
  Solr-style query, retrieving datasets that use different terminology than the
  user's literal words (e.g. a query about "food insecurity" also surfacing
  documents about poverty, child care, or education). The team states this
  translation step is isolated from OpenAI's model-training pipeline for privacy
  reasons.
- The project's public roadmap mentions **SDOH ontology / knowledge-graph
  development** as future work -- formal mappings of how SDOH domains and
  concepts relate to one another -- described as still evolving, not yet finalized.

### 1.3 User research and design process
- The team ran a formal UX design process (personas, empathy maps, a design
  sprint, competitor analysis) before building the discovery tool, and has run
  "Super User" testing cohorts of health-equity researchers and practitioners at
  UIUC to pressure-test the search experience pre-launch.
- The Data Discovery App publicly launched in **March 2025**.

### 1.4 Related open resources from the same lab
- The lab also publishes the **US COVID Atlas**, the **Opioid Environment Policy
  Scan (OEPS) toolkit**, **ChiVes** (a Chicago environmental-data harmonization
  project), and a general SDOH data list at
  `geodacenter.github.io/data-and-lab/us-sdoh/`. These show the lab's general
  pattern of practice: harmonizing many heterogeneous public datasets to a
  common county/tract-level geography and republishing them with clear provenance.

---

## 2. What metadata matters

The OGM Aardvark schema is a public, versioned specification. The canonical
schema in `src/models/schema.py` draws structurally on the categories that
Aardvark-family / GeoBlacklight-style schemas use: identity, geography,
temporal coverage, access/rights, provenance, format.

Geography clearly matters more than in a typical dataset catalog: the emphasis
on Solr's geospatial search, a custom `HEROP_ID` geographic key, and GeoBlacklight
lineage all indicate that **every record must be resolvable to a place**, and
that the discovery tool distinguishes at minimum:
- the geographic **level** a dataset is published at (county, tract, place,
  ZCTA, state, etc.), and
- whether a **geometry** (a shape a map can draw) is actually available, versus
  the dataset merely referencing geography through an identifier (a FIPS code,
  a HEROP_ID, a county name).

---

## 3. Design decisions in this pipeline

1. **Canonical schema.** Pydantic schema organized into the same broad
   categories Aardvark-family schemas use (identity / subject /
   geography / time / structure / access / provenance / quality).
2. **Search backend.** Small deterministic keyword + facet ranking
   function in Python. The architecture keeps this swappable -- see
   `docs/architecture.md`.
3. **Ontology.** Rule-based SDOH domain taxonomy
   (`configs/sdoh_taxonomy.yaml`) based on the widely used five-domain SDOH
   framework (Healthy People 2030 / Kaiser Family Foundation framing: Economic
   Stability, Education Access & Quality, Health Care Access & Quality,
   Neighborhood & Built Environment, Social & Community Context).
4. **Geographic identifiers.** The Census Bureau's standard **GEOID** /
   FIPS convention (2-digit state + 3-digit county = 5-digit county FIPS) as
   the geographic key, consistent with the HEROP_ID convention described above.

---

## 4. Sources consulted (all public)

- https://sdohplace.org/news/introducing-the-sdoh-place-project
- https://sdohplace.org/news/data-discovery-app-test-group%E2%80%94call-for-super-users
- https://sdohplace.org/news/transforming-sdoh-data-discovery-with-llm-a-different-journey
- https://healthyregions.org/2024/07/24/the-inaugural-sdoh-place-project-symposium/
- https://healthyregions.org/2025/07/02/healthy-regions-ncsa-at-geo4lib-camp-2025/
- https://metadata.sdohplace.org/
- https://github.com/healthyregions
- https://github.com/healthyregions/SDOHPlace-MetadataManager
- https://sdohplace.org/news/who-are-using-sdoh-place-data
- https://healthyregions.org/resources/
