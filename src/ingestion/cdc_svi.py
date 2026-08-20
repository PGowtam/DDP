"""
Adapter for the CDC/ATSDR Social Vulnerability Index (SVI).

The CDC SVI is a composite index built from 16 U.S. Census variables that
is extensively used in health equity and SDOH research as a summary measure
of structural vulnerability at the county and census-tract level. It is
produced by the Agency for Toxic Substances and Disease Registry (ATSDR)
and updated on a two-year release cycle using ACS 5-year estimates.

The SVI aggregates vulnerability across four themes:
  1. Socioeconomic Status (poverty, unemployment, income, education)
  2. Household Characteristics (elderly, disability, single-parent, English proficiency)
  3. Racial and Ethnic Minority Status (minority population share)
  4. Housing Type and Transportation (multi-unit, mobile homes, crowding,
     no vehicle access, group quarters)

Each theme produces a percentile rank (0 = least vulnerable, 1 = most
vulnerable), as does the overall composite RPL_THEMES score. Both
county-level and census-tract-level files are publicly available as free
CSV downloads with no registration required.

Data: https://www.atsdr.cdc.gov/placeandhealth/svi/data_documentation_download.html
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

SVI_LANDING_PAGE = "https://www.atsdr.cdc.gov/placeandhealth/svi/data_documentation_download.html"
# NOTE: CDC/ATSDR migrated SVI data hosting from svi.cdc.gov to atsdr.cdc.gov.
# The 2022 CSV files are available from the landing page above. Direct download
# URLs are not stable across ATSDR server updates; run from a machine with
# normal internet access and verify the URL from the official landing page.
# Format used in the 2022 release (verify current URL at landing page):
SVI_COUNTY_URL = "https://www.atsdr.cdc.gov/placeandhealth/svi/documentation/csv/SVI2022_US_county.csv"
SVI_TRACT_URL = "https://www.atsdr.cdc.gov/placeandhealth/svi/documentation/csv/SVI2022_US.csv"

KNOWN_SVI_FILES: list[dict[str, Any]] = [
    {
        "dataset_id": "cdc_svi_county_2022",
        "url": SVI_COUNTY_URL,
        "title": "CDC/ATSDR Social Vulnerability Index (SVI), County Level, 2022",
        "description": (
            "The CDC/ATSDR Social Vulnerability Index (SVI) ranks every U.S. county on "
            "structural vulnerability using 16 Census variables organized into four themes. "
            "Theme 1 (Socioeconomic Status) captures poverty rate, unemployment, per-capita "
            "income, and share lacking a high school diploma -- the economic foundation of "
            "SDOH vulnerability. Theme 2 (Household Characteristics) captures elderly "
            "residents, people with disabilities, single-parent households, and those with "
            "limited English proficiency -- populations with elevated barriers to disaster "
            "recovery and healthcare access. Theme 3 (Racial & Ethnic Minority Status) "
            "captures the share of non-white and Hispanic/Latino residents, a proxy for "
            "historical disinvestment and structural racism effects on health. Theme 4 "
            "(Housing Type & Transportation) captures multi-unit housing, mobile homes, "
            "crowding, no-vehicle households, and group quarters population -- indicators "
            "of housing instability and mobility constraints. Each theme yields a county "
            "percentile rank (RPL_THEME1-4), and the composite RPL_THEMES score ranks all "
            "3,144 counties from 0 (least vulnerable) to 1 (most vulnerable). In SDOH "
            "research, the SVI serves as both a dependent variable and a structural covariate "
            "when modeling outcomes such as COVID-19 mortality, preterm birth, and mental "
            "health service utilization disparities. Geographic key is the 5-digit FIPS county code."
        ),
        "measures": [
            "svi_overall_percentile_rank",
            "svi_socioeconomic_percentile_rank",
            "svi_household_characteristics_percentile_rank",
            "svi_minority_status_percentile_rank",
            "svi_housing_transportation_percentile_rank",
        ],
        "topics": [
            "social vulnerability", "socioeconomic status", "housing instability",
            "disability", "racial minority status", "transportation access",
            "social determinants of health", "composite index",
        ],
        "geographic_level": GeographicLevel.COUNTY,
        "geo_identifiers": ["fips_county", "geoid"],
        "county_coverage": True,
        "tract_coverage": False,
        "reference_period": "2022 (ACS 2018-2022 5-Year Estimates)",
        "temporal_start": date(2018, 1, 1),
        "temporal_end": date(2022, 12, 31),
    },
    {
        "dataset_id": "cdc_svi_tract_2022",
        "url": SVI_TRACT_URL,
        "title": "CDC/ATSDR Social Vulnerability Index (SVI), Census Tract Level, 2022",
        "description": (
            "Census-tract-level version of the CDC/ATSDR Social Vulnerability Index, covering "
            "approximately 85,000 U.S. census tracts. The tract-level SVI is essential for "
            "sub-county health equity analysis: it exposes within-county spatial heterogeneity "
            "in structural vulnerability that county averages mask, enabling identification of "
            "high-need neighborhoods rather than generalizing to an entire county. The same "
            "four-theme structure applies (Socioeconomic Status, Household Characteristics, "
            "Racial & Ethnic Minority Status, Housing & Transportation), and percentile ranks "
            "are computed within the full national distribution of tracts. Geographic key is "
            "the 11-digit census tract GEOID (2-digit state FIPS + 3-digit county FIPS + "
            "6-digit tract code), consistent with the HEROP_ID geographic convention used by "
            "the SDOH & Place platform. Because tract boundaries shift with each decennial "
            "census, analysts must verify boundary vintage alignment when joining to other "
            "tract-level datasets. The large file size (~85,000 rows x 150 columns) makes "
            "this dataset well-suited for map-based spatial clustering and hotspot analysis."
        ),
        "measures": [
            "svi_overall_percentile_rank",
            "svi_socioeconomic_percentile_rank",
            "svi_household_characteristics_percentile_rank",
            "svi_minority_status_percentile_rank",
            "svi_housing_transportation_percentile_rank",
        ],
        "topics": [
            "social vulnerability", "socioeconomic status", "housing instability",
            "disability", "racial minority status", "transportation access",
            "census tract", "sub-county analysis", "spatial analysis",
            "social determinants of health", "composite index",
        ],
        "geographic_level": GeographicLevel.CENSUS_TRACT,
        "geo_identifiers": ["geoid_tract", "fips_state", "fips_county"],
        "county_coverage": False,
        "tract_coverage": True,
        "reference_period": "2022 (ACS 2018-2022 5-Year Estimates)",
        "temporal_start": date(2018, 1, 1),
        "temporal_end": date(2022, 12, 31),
    },
]


class CDCSVIAdapter(DatasetSourceAdapter):
    source_id = "cdc_svi"
    source_organization = "CDC/ATSDR (Agency for Toxic Substances and Disease Registry)"

    def discover(self) -> list[dict[str, Any]]:
        return KNOWN_SVI_FILES

    def fetch(self, descriptor: dict[str, Any]) -> FetchResult:
        url = descriptor["url"]
        dataset_id = descriptor["dataset_id"]
        raw_path = RAW_DIR / f"{dataset_id}.csv"
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise AdapterError(
                f"Failed to fetch CDC SVI from {url}: {exc}. "
                f"The ATSDR SVI portal ({SVI_LANDING_PAGE}) occasionally changes "
                f"direct download URLs. Verify the current URL for the 2022 county/tract "
                f"CSV at the landing page above, update SVI_COUNTY_URL / SVI_TRACT_URL "
                f"in this file, and re-run from a machine with normal internet access."
            ) from exc
        raw_path.write_bytes(resp.content)
        return FetchResult(
            dataset_id=dataset_id,
            raw_path=raw_path,
            retrieved_at=self.now(),
            access_method=f"HTTP GET {url} (official CDC/ATSDR SVI download portal, CSV)",
        )

    def extract_metadata(self, descriptor: dict[str, Any], fetch_result: FetchResult) -> dict[str, Any]:
        # SVI CSV files may include a UTF-8 BOM; utf-8-sig handles that transparently.
        text = fetch_result.raw_path.read_text(encoding="utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        rows = list(reader)
        n_rows = len(rows)
        svi_missing = {"", "-999", ".", "NA", "N/A"}
        missing_counts = {col: 0 for col in header}
        for row in rows:
            for col, val in zip(header, row):
                if val is None or val.strip() in svi_missing:
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
        geo_level = descriptor["geographic_level"]

        return DatasetRecord(
            dataset_id=descriptor["dataset_id"],
            title=descriptor["title"],
            description=descriptor["description"],
            publisher=self.source_organization,
            source_url=descriptor["url"],
            landing_page_url=SVI_LANDING_PAGE,
            topics=descriptor["topics"],
            measures=descriptor["measures"],
            population="U.S. general population",
            geography=GeographyMetadata(
                geographic_level=geo_level,
                geographic_unit=(
                    "U.S. census tract (11-digit GEOID)"
                    if geo_level == GeographicLevel.CENSUS_TRACT
                    else "U.S. county (5-digit FIPS)"
                ),
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
                update_frequency="Every 2 years (next release: 2024 SVI)",
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
                license="Public domain -- U.S. federal government data (CDC/ATSDR).",
            ),
            provenance=ProvenanceMetadata(
                source_organization=self.source_organization,
                source_url=descriptor["url"],
                retrieval_timestamp=fetch_result.retrieved_at,
                metadata_source=(
                    "Column names and row/column counts computed from the fetched raw CSV; "
                    "descriptions and measure definitions from the official CDC SVI "
                    "documentation at https://www.atsdr.cdc.gov/placeandhealth/svi/."
                ),
                access_method=fetch_result.access_method,
                raw_file_path=str(fetch_result.raw_path.relative_to(RAW_DIR.parent.parent)),
                raw_sha256=self.sha256_of(fetch_result.raw_path),
                transformation_history=[
                    "Downloaded unmodified CSV from official CDC/ATSDR SVI data portal.",
                    "Decoded with utf-8-sig to handle potential UTF-8 BOM in source file.",
                    "Computed row_count, column_count, and per-column missingness "
                    "(treating empty, '-999', '.', 'NA' as missing per SVI codebook).",
                    "No values in the raw data were altered.",
                ],
            ),
        )
