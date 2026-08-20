"""
Adapter for the Opioid Environment Policy Scan (OEPS).

OEPS is an open-source data harmonization project from the Healthy Regions
& Policies Lab (HEROP Lab) at UIUC -- the same lab behind the SDOH & Place
Project. It compiles county- and census-tract-level SDOH indicators across
the full vulnerability spectrum (economic stability, healthcare access, built
environment, social context) to support opioid-related health equity research,
but the underlying measures are broadly applicable social determinants.

Because OEPS is produced by the HEROP Lab itself, its variable construction,
geographic key conventions (5-digit county FIPS, 11-digit tract GEOID), and
thematic organization are directly aligned with the SDOH & Place data ecosystem.

Data: https://github.com/healthyregions/oeps
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

OEPS_GITHUB_ORG = "healthyregions/oeps"
OEPS_REPO_URL = f"https://github.com/{OEPS_GITHUB_ORG}"
OEPS_LANDING_PAGE = "https://oeps.healthyregions.org/"

# OEPS v2 publishes harmonized county-level CSV exports on GitHub.
# Exact file paths reflect the healthyregions/oeps repository structure.
KNOWN_OEPS_FILES: list[dict[str, Any]] = [
    {
        "dataset_id": "oeps_county_economic_housing",
        "url": f"https://raw.githubusercontent.com/{OEPS_GITHUB_ORG}/main/data/tabular/oeps_county.csv",
        "title": "OEPS County-Level SDOH Indicators (Economic Stability & Housing), 2017-2021",
        "description": (
            "County-level harmonized SDOH indicators from the Opioid Environment Policy Scan "
            "(OEPS), produced by the HEROP Lab at UIUC. OEPS compiles a curated set of "
            "economic stability measures -- poverty rate, unemployment rate, median household "
            "income, and share of residents without a high school diploma -- alongside housing "
            "burden indicators including the share of households spending more than 30% of "
            "income on housing costs (cost-burdened) and households without vehicle access. "
            "Healthcare access variables (uninsured rate, federally qualified health center "
            "density per 100,000 population, pharmacy access) are also included. Variables "
            "draw primarily from ACS 5-year estimates and are standardized with consistent "
            "geographic keys (5-digit FIPS county code) to facilitate merging with health "
            "outcome datasets. In health equity research, OEPS county data is used both as "
            "a multi-domain predictor file -- linking structural conditions to overdose "
            "mortality, treatment access disparities, and preventable hospitalization rates -- "
            "and as a general-purpose SDOH covariate file for regression, clustering, and "
            "map-based analysis. As a HEROP Lab product, this dataset is directly relevant "
            "to the SDOH & Place data ecosystem and follows the same geographic key conventions."
        ),
        "measures": [
            "poverty_rate", "unemployment_rate", "median_household_income",
            "no_high_school_diploma_rate", "housing_cost_burden_rate",
            "no_vehicle_rate", "uninsured_rate", "fqhc_per_100k",
        ],
        "topics": [
            "economic stability", "housing cost burden", "healthcare access",
            "opioid environment", "social determinants of health",
            "HEROP Lab", "multi-domain SDOH",
        ],
        "geographic_level": GeographicLevel.COUNTY,
        "geo_identifiers": ["fips_county"],
        "county_coverage": True,
        "tract_coverage": False,
        "reference_period": "2017-2021 (ACS 5-Year Estimates)",
        "temporal_start": date(2017, 1, 1),
        "temporal_end": date(2021, 12, 31),
    },
]


class OEPSAdapter(DatasetSourceAdapter):
    source_id = "oeps"
    source_organization = "Healthy Regions & Policies Lab (HEROP Lab), University of Illinois Urbana-Champaign"

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
                f"Requires outbound network access to raw.githubusercontent.com."
            ) from exc
        raw_path.write_bytes(resp.content)
        return FetchResult(
            dataset_id=dataset_id,
            raw_path=raw_path,
            retrieved_at=self.now(),
            access_method=f"HTTP GET {url} (HEROP Lab official GitHub repo, raw CSV export)",
        )

    def extract_metadata(self, descriptor: dict[str, Any], fetch_result: FetchResult) -> dict[str, Any]:
        text = fetch_result.raw_path.read_text()
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        rows = list(reader)
        n_rows = len(rows)
        oeps_missing = {"", "NA", "N/A", "-999", "."}
        missing_counts = {col: 0 for col in header}
        for row in rows:
            for col, val in zip(header, row):
                if val is None or val.strip() in oeps_missing:
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
                county_coverage=descriptor["county_coverage"],
                tract_coverage=descriptor["tract_coverage"],
                geometry_available=False,
                geometry_type=GeometryType.NONE,
            ),
            time=TemporalMetadata(
                temporal_coverage_start=descriptor["temporal_start"],
                temporal_coverage_end=descriptor["temporal_end"],
                temporal_resolution="5-year ACS estimate period",
                reference_period=descriptor["reference_period"],
                update_frequency="Annual OEPS release",
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
                license="Open access -- see https://github.com/healthyregions/oeps for license.",
            ),
            provenance=ProvenanceMetadata(
                source_organization=self.source_organization,
                source_url=descriptor["url"],
                retrieval_timestamp=fetch_result.retrieved_at,
                metadata_source=(
                    "Column names and row/column counts computed from the fetched raw CSV; "
                    "descriptions and measure definitions from OEPS documentation at "
                    "https://oeps.healthyregions.org/ and the GitHub repository README."
                ),
                access_method=fetch_result.access_method,
                raw_file_path=str(fetch_result.raw_path.relative_to(RAW_DIR.parent.parent)),
                raw_sha256=self.sha256_of(fetch_result.raw_path),
                transformation_history=[
                    "Downloaded unmodified CSV from HEROP Lab official GitHub repository.",
                    "Computed row_count, column_count, and per-column missingness "
                    "(treating empty, 'NA', '-999', '.' as missing).",
                    "No values in the raw data were altered.",
                ],
            ),
        )
