"""
python scripts/demo.py

Demonstrates the pipeline end-to-end in the terminal: load normalized
datasets, search, filter by geography, show metadata/provenance/
completeness, and demonstrate the user-upload inference prototype.
Uses whatever is currently in data/metadata/index.json; falls back to
demo/metadata.json (Phase 27) if the live pipeline hasn't been run yet.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.models.schema import DatasetRecord
from src.pipeline.pipeline import load_index
from src.search.engine import SearchIndex
from src.ingestion.user_upload import infer_upload_metadata


def _load_records():
    records = load_index()
    if records:
        print(f"[1] Loaded {len(records)} normalized datasets from data/metadata/index.json (live pipeline output).\n")
        return records
    demo_path = REPO_ROOT / "demo" / "metadata.json"
    raw = json.loads(demo_path.read_text())
    records = [DatasetRecord.model_validate(r) for r in raw]
    print(f"[1] No live index found. Loaded {len(records)} datasets from demo/metadata.json instead.\n")
    return records


def main() -> None:
    print("=" * 70)
    print("SDOH Data Discovery Pipeline -- Terminal Demonstration")
    print("=" * 70)

    records = _load_records()

    print("[2] Searching for 'income'...")
    index = SearchIndex(records)
    results = index.search(query="income")
    for r in results:
        print(f"    -> {r.record.title} (score={r.score:.1f})")
    print()

    print("[3] Filtering by geography=county...")
    county_results = index.search(geography_level="county")
    print(f"    -> {len(county_results)} of {len(records)} datasets are county-level.\n")

    if results:
        top = results[0].record
        print(f"[4] Metadata for top result: {top.title}")
        print(f"    Publisher: {top.publisher}")
        print(f"    SDOH domain: {top.sdoh_domains.primary_domain} (confidence={top.sdoh_domains.confidence})")
        print(f"    Geography level: {top.geography.geographic_level}  "
              f"(geometry available: {top.geography.geometry_available})")
        print()

        print("[5] Provenance:")
        print(f"    Source: {top.source_url}")
        print(f"    Retrieved at: {top.provenance.retrieval_timestamp}")
        print(f"    Access method: {top.provenance.access_method}")
        print(f"    Raw SHA-256: {top.provenance.raw_sha256}")
        print()

        print("[6] Metadata completeness score:")
        print(f"    {top.quality.metadata_completeness_score:.0%} "
              f"(validation status: {top.quality.validation_status})")
        if top.quality.warnings:
            print(f"    Warnings: {top.quality.warnings}")
        print()

    print("[7] Demonstrating user-upload metadata inference on a synthetic sample CSV...")
    sample_csv = (
        "county_fips,year,unemployment_rate,region_type\n"
        "17031,2023,4.2,urban\n17019,2023,5.1,rural\n17097,2023,3.8,urban\n"
    )
    upload_result = infer_upload_metadata(sample_csv)
    print(f"    Detected geography columns: {upload_result.detected_geography_columns}")
    print(f"    Detected time columns: {upload_result.detected_time_columns}")
    print(f"    Detected numeric measures: {upload_result.detected_numeric_measures}")
    print(f"    Warnings: {upload_result.warnings}")
    print()
    print("Demo complete. See docs/demo-script.md for the live-presentation version.")


if __name__ == "__main__":
    main()
