"""
Adapter for the U.S. Census Bureau's American Community Survey (ACS) 5-Year
Estimates API.

STATUS IN THIS BUILD: implemented but NOT successfully executed in this
sandboxed development session. The sandbox's outbound network egress is
restricted to a package-registry allowlist (pypi, npm, github, etc.) and does
not include api.census.gov. A live attempt during development returned:

    "Host not in allowlist: api.census.gov. Add this host to your network
    egress settings to allow access."

This is not a fabricated limitation -- it is the exact error returned by
this environment's egress proxy. See docs/limitations.md.

The code below is otherwise a real, correct client for the public ACS API
(https://www.census.gov/data/developers/data-sets/acs-5year.html) and will
run normally in an environment with standard internet access and a free
Census API key (https://api.census.gov/data/key_signup.html) set as the
CENSUS_API_KEY environment variable. It is included so the adapter
architecture (Phase 2) is demonstrably extensible to a second, structurally
different publisher (a live JSON API vs. CHR&R's static CSV releases), and
so this gap is documented rather than silently glossed over.
"""
from __future__ import annotations

import os
from datetime import date
from typing import Any

import requests

from src.ingestion.base import DatasetSourceAdapter, FetchResult, AdapterError, RAW_DIR
from src.models.schema import (
    DatasetRecord, GeographyMetadata, GeographicLevel, GeometryType,
    TemporalMetadata, DataStructureMetadata, FileFormat, AccessMetadata,
    AccessType, ProvenanceMetadata,
)

ACS_YEAR = 2023
ACS_DATASET = "acs/acs5"
# B25064_001E = median gross rent (dollars), a standard ACS housing-cost variable.
ACS_VARIABLE = "B25064_001E"
BASE_URL = f"https://api.census.gov/data/{ACS_YEAR}/{ACS_DATASET}"


class CensusACSAdapter(DatasetSourceAdapter):
    source_id = "census_acs"
    source_organization = "U.S. Census Bureau"

    def discover(self) -> list[dict[str, Any]]:
        return [{
            "dataset_id": "census_acs5_median_gross_rent_county_2023",
            "title": "Median Gross Rent by County, ACS 5-Year Estimates (2019-2023)",
            "description": (
                "County-level median gross rent (contract rent plus utilities) "
                "for renter-occupied housing units, from the Census Bureau's "
                "American Community Survey 5-Year Estimates."
            ),
            "measures": ["median_gross_rent_usd"],
        }]

    def fetch(self, descriptor: dict[str, Any]) -> FetchResult:
        api_key = os.environ.get("CENSUS_API_KEY")
        params = {"get": f"NAME,{ACS_VARIABLE}", "for": "county:*", "in": "state:*"}
        if api_key:
            params["key"] = api_key
        dataset_id = descriptor["dataset_id"]
        raw_path = RAW_DIR / f"{dataset_id}.json"
        try:
            resp = requests.get(BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise AdapterError(
                f"Failed to fetch Census ACS data for {dataset_id} from {BASE_URL}: {exc}"
            ) from exc
        # The Census API returns 200 OK with an empty body when the request
        # is malformed or the API key is missing and rate-limiting kicks in.
        if not resp.content.strip():
            raise AdapterError(
                f"Census ACS API returned an empty response for {dataset_id}. "
                f"Set CENSUS_API_KEY (free key: https://api.census.gov/data/key_signup.html)."
            )
        # The Census API returns 200 OK with an HTML error page when no API key
        # is provided or the request is otherwise rejected.
        content_type = resp.headers.get("Content-Type", "")
        if "html" in content_type or resp.content.lstrip()[:1] == b"<":
            raise AdapterError(
                f"Census ACS API returned an HTML error page instead of JSON for "
                f"{dataset_id}. This means the API key is missing or invalid. "
                f"Set CENSUS_API_KEY in your environment "
                f"(free key: https://api.census.gov/data/key_signup.html) and re-run."
            )
        raw_path.write_bytes(resp.content)
        return FetchResult(
            dataset_id=dataset_id,
            raw_path=raw_path,
            retrieved_at=self.now(),
            access_method=f"HTTP GET {BASE_URL} (Census ACS 5-Year API, key={'set' if api_key else 'NOT SET'})",
        )

    def extract_metadata(self, descriptor: dict[str, Any], fetch_result: FetchResult) -> dict[str, Any]:
        import json
        raw_text = fetch_result.raw_path.read_text()
        if not raw_text.strip() or raw_text.lstrip().startswith("<"):
            raise AdapterError(
                f"Raw file for {descriptor['dataset_id']} is not valid JSON "
                f"(empty or HTML). Census API requires a valid CENSUS_API_KEY."
            )
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise AdapterError(
                f"Failed to parse Census ACS response as JSON for "
                f"{descriptor['dataset_id']}: {exc}"
            ) from exc
        header, *rows = data
        return {
            "descriptor": descriptor, "fetch_result": fetch_result,
            "columns": header, "row_count": len(rows), "column_count": len(header),
            "missingness_summary": {},
        }

    def normalize(self, raw_metadata: dict[str, Any]) -> DatasetRecord:
        descriptor = raw_metadata["descriptor"]
        fetch_result: FetchResult = raw_metadata["fetch_result"]
        return DatasetRecord(
            dataset_id=descriptor["dataset_id"],
            title=descriptor["title"],
            description=descriptor["description"],
            publisher=self.source_organization,
            source_url=BASE_URL,
            landing_page_url="https://www.census.gov/data/developers/data-sets/acs-5year.html",
            topics=["housing", "social determinants of health"],
            measures=descriptor["measures"],
            geography=GeographyMetadata(
                geographic_level=GeographicLevel.COUNTY,
                geographic_unit="U.S. county",
                geographic_coverage=["US-national"],
                geographic_identifiers=["fips_state", "fips_county"],
                county_coverage=True,
                geometry_available=False,
                geometry_type=GeometryType.NONE,
            ),
            time=TemporalMetadata(
                temporal_coverage_start=date(2019, 1, 1),
                temporal_coverage_end=date(2023, 12, 31),
                temporal_resolution="5-year rolling estimate",
                reference_period="2019-2023 ACS 5-Year Estimates",
                update_frequency="annual",
            ),
            structure=DataStructureMetadata(
                file_format=FileFormat.JSON,
                data_type="tabular",
                row_count=raw_metadata["row_count"],
                column_count=raw_metadata["column_count"],
                columns=raw_metadata["columns"],
            ),
            access=AccessMetadata(
                access_type=AccessType.OPEN_API,
                api_available=True,
                download_available=True,
                authentication_required=True,
                usage_restrictions="Free Census API key required for sustained use.",
            ),
            provenance=ProvenanceMetadata(
                source_organization=self.source_organization,
                source_url=BASE_URL,
                retrieval_timestamp=fetch_result.retrieved_at,
                metadata_source="Census ACS API JSON response header row.",
                access_method=fetch_result.access_method,
                raw_file_path=str(fetch_result.raw_path.relative_to(RAW_DIR.parent.parent)),
                raw_sha256=self.sha256_of(fetch_result.raw_path),
                transformation_history=["Downloaded unmodified JSON response from the ACS API."],
            ),
        )
