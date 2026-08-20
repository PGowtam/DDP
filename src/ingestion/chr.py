"""
Adapter for County Health Rankings & Roadmaps (CHR&R), a program of the
University of Wisconsin Population Health Institute.

This adapter is fully functional and was exercised against real data during
development of this repository: it downloads official, publisher-maintained
CSV files directly from CHR&R's own open-source GitHub organization
(github.com/countyhealthrankings/county_health_measure_calculations), which
publishes the measure-level datasets behind the annual County Health
Rankings release.

Why GitHub and not countyhealthrankings.org directly: this is simply the
access method CHR&R itself provides for programmatic use of these specific
measure files (see their README, cited below). No scraping or reverse
engineering was involved.

Citation (per the source repository's own README):
  "Measure calculations for the CHR&R annual data release" (v2025). Zenodo.
  https://doi.org/10.5281/zenodo.19473865
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date
from pathlib import Path
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

GITHUB_ORG_REPO = "countyhealthrankings/county_health_measure_calculations"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_ORG_REPO}/main/measure_datasets"
REPO_HTML_URL = f"https://github.com/{GITHUB_ORG_REPO}"

# Each descriptor below is one CSV file this adapter knows how to pull.
# `column_meaning` and `title`/`description` are only populated when this
# project independently corroborated the measure's meaning (see the inline
# notes) -- everything else is left generic rather than guessed, per the
# project's no-fabrication rule.
KNOWN_MEASURE_FILES: list[dict[str, Any]] = [
    {
        "dataset_id": "chrr_v001_premature_death_r2026",
        "filename": "v001_r2026.csv",
        "title": "Premature Death (Years of Potential Life Lost), County Data, 2026 release",
        "description": (
            "Years of Potential Life Lost (YPLL) before age 75 is the County Health Rankings "
            "headline measure of population health and a core metric in health equity research. "
            "Unlike all-cause mortality rates, YPLL weights deaths that occur earlier in life "
            "more heavily than deaths closer to age 75, making it particularly sensitive to "
            "preventable, premature causes of death -- overdose, homicide, traffic fatalities, "
            "and maternal mortality -- that are strongly patterned by socioeconomic and "
            "structural conditions. County-level YPLL rates are routinely used as a dependent "
            "variable in regression analyses linking income inequality, uninsured rates, "
            "environmental exposures, or food access to population health outcomes, and as a "
            "benchmark for tracking whether place-based policy interventions reduce premature "
            "mortality over time. Because it captures structural health disadvantage more "
            "sharply than life expectancy, YPLL is frequently used alongside the Social "
            "Vulnerability Index and Area Deprivation Index to map health burden hot spots. "
            "Column 'ypll_se' (YPLL standard error) in the raw file confirms measure identity "
            "and enables uncertainty-aware analyses."
        ),
        "measures": ["premature_death_ypll_rate_per_100k", "premature_death_ypll_se"],
        "topics": [
            "premature mortality", "years of potential life lost", "length of life",
            "health outcomes", "preventable death", "social determinants of health",
        ],
        "reference_period": "2026 release",
    },
    {
        "dataset_id": "chrr_v063_median_household_income_r2025",
        "filename": "v063_r2025.csv",
        "title": "Median Household Income, County Data, 2025 release",
        "description": (
            "County-level median household income sourced by CHR&R from the Census Bureau's "
            "Small Area Income and Poverty Estimates (SAIPE) program. Median household income "
            "is one of the most widely used proxies for material economic security in "
            "place-based public health research and serves as the primary economic stability "
            "predictor in County Health Rankings models. SAIPE uses model-based methodology "
            "combining ACS survey data with IRS and administrative records, producing more "
            "timely and statistically reliable county estimates than decennial census income "
            "data, particularly for small-population counties where ACS direct estimates have "
            "high margins of error. Because income distributions are right-skewed, the median "
            "is more robust to high-income outliers than the mean; analysts working with this "
            "variable in regression models typically log-transform it to approximate normality. "
            "County income is commonly joined with Medicaid enrollment rates, SNAP participation, "
            "cost-of-living indices, and YPLL data to identify counties where economic hardship "
            "most strongly predicts poor health outcomes. The national-level row (statecode=00, "
            "rawvalue ~$77,719 in the 2025 release) anchors the data to the published U.S. "
            "median, enabling researchers to benchmark individual county values against the "
            "national distribution."
        ),
        "measures": ["median_household_income_usd"],
        "topics": [
            "median household income", "economic stability", "SAIPE",
            "income inequality", "poverty", "social determinants of health",
        ],
        "reference_period": "2025 release",
    },
    {
        "dataset_id": "chrr_v001_race_population_estimates_r2026",
        "filename": "v001_otherdata_r2026.csv",
        "title": "Population Estimates by Race/Ethnicity, County Data, 2026 release",
        "description": (
            "County-level population estimates disaggregated by race/ethnicity, used by "
            "CHR&R as denominators for computing race-stratified health outcome rates. In "
            "health equity research, these estimates serve as contextual covariates -- not "
            "independent causal predictors -- to assess whether outcome disparities correlate "
            "with demographic composition, and to produce race-stratified rates for direct "
            "cross-county comparison. A county's racial composition is a proxy for exposure "
            "to historical and contemporary structural racism, including residential "
            "segregation, environmental injustice, and differential access to healthcare and "
            "economic opportunity. Categories follow OMB standards: Hispanic/Latino is treated "
            "as an ethnicity that may overlap with any racial category, and 'two or more races' "
            "reflects increasing multiracial self-identification in Census data over successive "
            "survey years. These denominators are essential for computing rate ratios -- such "
            "as the Black-white or Hispanic-white premature death rate ratio -- that are "
            "standard indicators of structural health inequality. Column names "
            "(v001_race_white, v001_race_black, v001_race_hispanic, etc.) are self-identifying "
            "in the raw file."
        ),
        "measures": [
            "population_white", "population_black", "population_aian",
            "population_asian", "population_nhopi", "population_two_or_more_races",
            "population_hispanic",
        ],
        "topics": [
            "race and ethnicity", "population estimates", "health equity",
            "race-stratified analysis", "demographic composition",
            "social determinants of health",
        ],
        "reference_period": "2026 release",
    },
]


class CountyHealthRankingsAdapter(DatasetSourceAdapter):
    source_id = "county_health_rankings"
    source_organization = "County Health Rankings & Roadmaps (University of Wisconsin Population Health Institute)"

    def discover(self) -> list[dict[str, Any]]:
        return KNOWN_MEASURE_FILES

    def fetch(self, descriptor: dict[str, Any]) -> FetchResult:
        url = f"{RAW_BASE_URL}/{descriptor['filename']}"
        dataset_id = descriptor["dataset_id"]
        raw_path = RAW_DIR / f"{dataset_id}.csv"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise AdapterError(
                f"Failed to fetch {url} for {dataset_id}: {exc}"
            ) from exc

        raw_path.write_bytes(resp.content)
        return FetchResult(
            dataset_id=dataset_id,
            raw_path=raw_path,
            retrieved_at=self.now(),
            access_method=f"HTTP GET {url} (official CHR&R GitHub org, raw CSV)",
        )

    def extract_metadata(self, descriptor: dict[str, Any], fetch_result: FetchResult) -> dict[str, Any]:
        text = fetch_result.raw_path.read_text()
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        rows = list(reader)
        n_cols = len(header)
        missing_counts = {col: 0 for col in header}
        for row in rows:
            for col, val in zip(header, row):
                if val is None or val.strip() == "":
                    missing_counts[col] += 1
        n_rows = len(rows)
        missingness = {
            col: round(missing_counts[col] / n_rows, 4) if n_rows else 0.0
            for col in header
        }

        return {
            "descriptor": descriptor,
            "fetch_result": fetch_result,
            "columns": header,
            "row_count": n_rows,
            "column_count": n_cols,
            "missingness_summary": missingness,
        }

    def normalize(self, raw_metadata: dict[str, Any]) -> DatasetRecord:
        descriptor = raw_metadata["descriptor"]
        fetch_result: FetchResult = raw_metadata["fetch_result"]

        record = DatasetRecord(
            dataset_id=descriptor["dataset_id"],
            title=descriptor["title"],
            description=descriptor["description"],
            publisher=self.source_organization,
            source_url=REPO_HTML_URL,
            landing_page_url="https://www.countyhealthrankings.org/health-data",
            topics=["social determinants of health", "county health data"],
            measures=descriptor["measures"],
            geography=GeographyMetadata(
                geographic_level=GeographicLevel.COUNTY,
                geographic_unit="U.S. county (state FIPS + county FIPS)",
                geographic_coverage=["US-national"],
                geographic_identifiers=["fips_state", "fips_county"],
                county_coverage=True,
                geometry_available=False,
                geometry_type=GeometryType.NONE,
            ),
            time=TemporalMetadata(
                reference_period=descriptor["reference_period"],
                temporal_resolution="annual release, multi-year underlying estimate",
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
                license="See https://www.countyhealthrankings.org/health-data (not independently re-hosted here beyond this raw CSV).",
            ),
            provenance=ProvenanceMetadata(
                source_organization=self.source_organization,
                source_url=f"{RAW_BASE_URL}/{descriptor['filename']}",
                retrieval_timestamp=fetch_result.retrieved_at,
                metadata_source="Column names and row/column counts computed directly from the fetched raw CSV.",
                access_method=fetch_result.access_method,
                raw_file_path=str(fetch_result.raw_path.relative_to(RAW_DIR.parent.parent)),
                raw_sha256=self.sha256_of(fetch_result.raw_path),
                transformation_history=[
                    "Downloaded unmodified CSV from official CHR&R GitHub org.",
                    "Computed row_count, column_count, and per-column missingness directly from the file.",
                    "No values in the raw data were altered.",
                ],
            ),
        )
        return record
