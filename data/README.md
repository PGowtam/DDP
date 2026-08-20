# `data/` Layout

```text
data/
  raw/        Unmodified files exactly as downloaded from the source.
              Never edited by any pipeline step. Excluded from git
              (.gitignore) -- see "Why raw data isn't committed" below.
  processed/  Reserved for any derived/transformed data products.
              Currently unused: every adapter in this build normalizes
              directly from raw -> canonical metadata without an
              intermediate processed-data step, since the ingested
              measure files needed no reshaping beyond parsing.
  metadata/   Canonical, normalized DatasetRecord JSON -- one file per
              dataset (<dataset_id>.json), plus index.json (all records)
              and pipeline_report.json (per-run ingestion outcomes).
              Also excluded from git; regenerate with `python -m sdoh pipeline`.
```

## Why raw data isn't committed to this repository

Per the project's research-integrity rules, this repo does not re-host
third-party datasets. Instead, every raw file's exact source URL, retrieval
timestamp, and SHA-256 hash are recorded in the corresponding metadata
record's `provenance` block (see `docs/data-lineage.md`), so the data is
always traceable and re-fetchable, without this repository redistributing it.

## Reproducing `data/`

```bash
pip install -e .
python -m sdoh pipeline
```

This re-downloads the 3 currently-working CHR&R sources into `data/raw/`,
normalizes them into `data/metadata/`, and writes `data/metadata/index.json`
and `data/metadata/pipeline_report.json`. See `docs/limitations.md` for why
2 of the 5 configured sources currently fail in this sandbox specifically
(not in a normal networked environment).
