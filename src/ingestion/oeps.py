"""
Adapter for the Opioid Environment Policy Scan (OEPS) county-level data.

OEPS is an open-source data harmonization project from the Healthy Regions
& Policies Lab (HEROP Lab) at UIUC -- the same lab behind the SDOH & Place
Project. It harmonizes county-level SDOH indicators across economic stability,
healthcare access, built environment, and social context to support opioid
health equity research, but the underlying measures are broadly applicable
social determinants.

Data source: The OEPS explorer publishes a counties lookup CSV at
  https://raw.githubusercontent.com/healthyregions/oeps/main/explorer/public/csv/counties.csv
which provides a FIPS/Name/State crosswalk (3 columns). Full variable data
requires joining against the OEPS variable registry and downloading per-variable
CSVs. This adapter currently ingests the counties crosswalk as a geographic
reference dataset, documenting the HEROP_ID county coding system.

Repository: https://github.com/healthyregions/oeps
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date
from typing import Any

import requests

from src.ingestion.base import DatasetSourceAdapter, FetchResult, AdapterError, RAW_DIR
from src.models.schema import (
    DatasetRecord,
    GeographyMetadata,
    GeographicLevel,
    GeometryType,
    TemporalMetadata,
    DataStructureMetadata,
    FileFormat,
    AccessMetadata,
    AccessType,
    ProvenanceMetadata,
)

logger = logging.getLogger(__name__)

OEPS_REPO_URL = "https://github.com/healthyregions/oeps"
OEPS_LANDING_PAGE = "https://oeps.healthyregions.org/"
OEPS_COUNTIES_URL = (
    "https://raw.githubusercontent.com/healthyregions/oeps/main/"
    "explorer/public/csv/counties.csv"
)

KNOWN_OEPS_FILES: list[dict[str, Any]] = [
    {
        "dataset_id": "oeps_county_fips_crosswalk",
        "url": OEPS_COUNTIES_URL,
        "title": "OEPS County Geographic Crosswalk (FIPS / Name / State), HEROP Lab",
        "description": (
            "County-level geographic crosswalk from the Opioid Environment Policy Scan "
            "(OEPS), published by the Healthy Regions & Policies Lab (HEROP Lab) at UIUC -- "
            "the same lab that produces the SDOH & Place Project's Data Discovery Tool. "
            "This crosswalk maps the standard 5-digit county FIPS code to county name and "
            "state abbreviation, providing the geographic key used to join OEPS variable "
            "exports to place identifiers. The HEROP Lab uses this file as the reference "
            "for their 'HEROP_ID' geographic identifier, which the SDOH & Place platform "
            "describes as 'a slight variation on the commonly used standard GEOID.' Ingesting "
            "this file demonstrates both the geographic key conventions used by the HEROP Lab "
            "ecosystem and the OEPS data pipeline's structure, where a central crosswalk "
            "anchors all per-variable CSV downloads. The full OEPS variable catalog includes "
            "200+ indicators across economic stability, healthcare access, built environment, "
            "opioid environment, and demographic domains -- all joinable via this FIPS key."
        ),
        "measures": ["county_fips", "county_name", "state_abbreviation"],
        "topics": [
            "geographic crosswalk", "FIPS codes", "HEROP_ID", "county geography",
            "opioid environment", "social determinants of health", "HEROP Lab",
        ],
        "geographic_level": GeographicLevel.COUNTY,
        "geo_identifiers": ["fips_county"],
        "reference_period": "Current (updated with OEPS releases)",
    },
]


class OEPSAdapter(DatasetSourceAdapter):
    source_id = "oeps"
    source_organization = (
        "Healthy Regions & Policies Lab (HEROP Lab), "
        "University of Illinois Urbana-Champaign"
    )

    def discover(self) -> list[dict[str, Any]]:
        return KNOWN_OEPS_FILES

    def fetch(self, descriptor: dict[str, Any]) -> FetchResult:
        url = descriptor["url"]
        dataset_id = descriptor["dataset_id"]
        raw_path = RAW_DIR / f"{dataset_id}.csv"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise AdapterError(
                f"Failed to fetch OEPS data from {url}: {exc}. "
                f"Requires outbound access to raw.githubusercontent.com."
            ) from exc
        raw_path.write_bytes(resp.content)
        return FetchResult(
            dataset_id=dataset_id,
            raw_path=raw_path,
            retrieved_at=self.now(),
            access_method=(
                f"HTTP GET {url} "
                "(HEROP Lab official GitHub repository, public CSV)"
            ),
        )

    def extract_metadata(
        self, descriptor: dict[str, Any], fetch_result: FetchResult
    ) -> dict[str, Any]:
        text = fetch_result.raw_path.read_text()
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        rows = list(reader)
        n_rows = len(rows)
        missing_counts = {col: 0 for col in header}
        for row in rows:
            for col, val in zip(header, row):
                if val is None or val.strip() in ("", "NA", "N/A"):
                    missing_counts[col] += 1
        missingness = {
            col: round(missing_counts[col] / n_rows, 4) if n_rows else 0.0
            for col in header
        }
        return {
            "descriptor": descriptor,
            "fetch_result": fetch_result,
            "columns": header,
            "row_count": n_rows,
            "column_count": len(header),
            "missingness_summary": missingness,
        }

    def normalize(self, raw_metadata: dict[str, Any]) -> DatasetRecord:
        descriptor = raw_metadata["descriptor"]
        fetch_result: FetchResult = raw_metadata["fetch_result"]

        return DatasetRecord(
            dataset_id=descriptor["dataset_id"],
            title=descriptor["title"],
            description=descriptor["description"],
            publisher=self.source_organization,
            source_url=OEPS_REPO_URL,
            landing_page_url=OEPS_LANDING_PAGE,
            topics=descriptor["topics"],
            measures=descriptor["measures"],
            population="U.S. county-level population",
            geography=GeographyMetadata(
                geographic_level=descriptor["geographic_level"],
                geographic_unit="U.S. county (5-digit FIPS)",
                geographic_coverage=["US-national"],
                geographic_identifiers=descriptor["geo_identifiers"],
                county_coverage=True,
                tract_coverage=False,
                geometry_available=False,
                geometry_type=GeometryType.NONE,
            ),
            time=TemporalMetadata(
                reference_period=descriptor["reference_period"],
                update_frequency="Updated with each OEPS data release",
            ),
            structure=DataStructureMetadata(
                file_format=FileFormat.CSV,
                data_type="tabular",
                row_count=raw_metadata["row_count"],
                column_count=raw_metadata["column_count"],
                columns=raw_metadata["columns"],
                missingness_summary=raw_metadata["missingness_summary"],
            ),
            access=AccessMetadata(
                access_type=AccessType.OPEN_DOWNLOAD,
                api_available=False,
                download_available=True,
                authentication_required=False,
                license=(
                    "Open access -- see https://github.com/healthyregions/oeps "
                    "for license details."
                ),
            ),
            provenance=ProvenanceMetadata(
                source_organization=self.source_organization,
                source_url=descriptor["url"],
                retrieval_timestamp=fetch_result.retrieved_at,
                metadata_source=(
                    "Column names and row/column counts computed from the fetched raw CSV; "
                    "description from OEPS documentation at "
                    "https://oeps.healthyregions.org/ and the project README."
                ),
                access_method=fetch_result.access_method,
                raw_file_path=str(
                    fetch_result.raw_path.relative_to(RAW_DIR.parent.parent)
                ),
                raw_sha256=self.sha256_of(fetch_result.raw_path),
                transformation_history=[
                    "Downloaded unmodified CSV from HEROP Lab official GitHub repository.",
                    "Computed row_count, column_count, and per-column missingness.",
                    "No values in the raw data were altered.",
                ],
            ),
        )
