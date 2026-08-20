# Future Work

Roughly in priority order for continued development:

1. **Run the pipeline from an unrestricted network environment** to actually
   ingest the Census ACS and CDC PLACES adapters, plus add 2-3 more sources
   from different publishers (USDA Food Access Research Atlas, HUD, EPA) to
   reach genuine publisher/format/geography diversity.
2. **FastAPI layer** (`api/main.py`) exposing
   `GET /datasets`, `GET /datasets/{id}`, `GET /search`, `POST /datasets/validate`
   over the same `src/pipeline`/`src/search` modules the CLI and Streamlit UI
   already share.
3. **Docker packaging** and a minimal GitHub Actions workflow
   (install -> lint -> pytest) so the project is reproducible without a local
   Python setup.
4. **Optional semantic search layer** (sentence-transformers + FAISS) as an
   add-on to, not a replacement for, the deterministic keyword search --
   architecture already anticipates this as a parallel branch in
   `docs/architecture.md`.
5. **Map visualization** for any dataset where `geography.geometry_available`
   is `True`, using GeoPandas/Folium -- currently no ingested dataset has real
   geometry to visualize.
6. **FIPS/GEOID crosswalk validation** against an authoritative Census
   reference file, so `fips_state_county_to_geoid` can reject GEOIDs that
   don't correspond to a real county, not just malformed ones.
7. **A verified CHR&R data dictionary lookup** to replace the independently-
   corroborated (but not authoritative-source-confirmed) measure identifications
   in `src/ingestion/chr.py`.
8. **User-upload persistence**: currently the Streamlit upload tab only
   previews inferred metadata and does not let a user confirm/edit
   fields and add the record to the index -- that "accept into catalog" step
   is the natural next extension.
