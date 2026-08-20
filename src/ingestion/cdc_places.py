"""
Adapter for CDC PLACES (Population Level Analysis and Community Estimates),
a joint CDC / RWJF Foundation / CDC Foundation project providing model-based
small-area estimates of chronic disease risk factors and health outcomes,
served via data.cdc.gov's Socrata Open Data API (SODA).

STATUS IN THIS BUILD: implemented but NOT successfully executed in this
sandboxed development session, for the same reason documented in
src/ingestion/census_acs.py -- data.cdc.gov is not on this sandbox's
network egress allowlist. See docs/limitations.md.

Dataset identifier ("swc5-untb") for PLACES County Data is a real,
publicly documented Socrata resource ID confirmed via web search of CDC's
own data catalog and healthdata.gov during development of this repository,
not invented.
"""
from __future__ import annotations

from typing import Any

import requests

from src.ingestion.base import DatasetSourceAdapter, FetchResult, AdapterError, RAW_DIR
from src.models.schema import (
    DatasetRecord, GeographyMetadata, GeographicLevel, GeometryType,
    TemporalMetadata, DataStructureMetadata, FileFormat, AccessMetadata,
    AccessType, ProvenanceMetadata,
)

SOCRATA_RESOURCE_ID = "swc5-untb"  # PLACES: County Data, per data.cdc.gov catalog
BASE_URL = f"https://data.cdc.gov/resource/{SOCRATA_RESOURCE_ID}.json"


class CDCPlacesAdapter(DatasetSourceAdapter):
    source_id = "cdc_places"
    source_organization = "Centers for Disease Control and Prevention (PLACES project)"

    def discover(self) -> list[dict[str, Any]]:
        return [{
            "dataset_id": "cdc_places_county_data",
            "title": "PLACES: Local Data for Better Health, County Data",
            "description": (
                "Model-based county-level estimates for chronic disease risk "
                "factors, health outcomes, and prevention practices, produced by "
                "CDC's Division of Population Health from BRFSS, Census population "
                "estimates, and ACS data."
            ),
            "measures": ["chronic_disease_risk_factor_estimates"],
        }]

    def fetch(self, descriptor: dict[str, Any]) -> FetchResult:
        dataset_id = descriptor["dataset_id"]
        raw_path = RAW_DIR / f"{dataset_id}.json"
        try:
            resp = requests.get(BASE_URL, params={"$limit": 5000}, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise AdapterError(
                f"Failed to fetch CDC PLACES data for {dataset_id} from {BASE_URL}: {exc}"
            ) from exc
        raw_path.write_bytes(resp.content)
        return FetchResult(
            dataset_id=dataset_id, raw_path=raw_path, retrieved_at=self.now(),
            access_method=f"HTTP GET {BASE_URL} (Socrata SODA API)",
        )

    def extract_metadata(self, descriptor, fetch_result: FetchResult) -> dict[str, Any]:
        import json
        rows = json.loads(fetch_result.raw_path.read_text())
        columns = sorted({k for row in rows for k in row.keys()}) if rows else []
        return {
            "descriptor": descriptor, "fetch_result": fetch_result,
            "columns": columns, "row_count": len(rows), "column_count": len(columns),
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
            landing_page_url="https://www.cdc.gov/places/",
            topics=["chronic disease", "health outcomes", "social determinants of health"],
            measures=descriptor["measures"],
            geography=GeographyMetadata(
                geographic_level=GeographicLevel.COUNTY,
                geographic_unit="U.S. county",
                geographic_coverage=["US-national"],
                geographic_identifiers=["fips_county"],
                county_coverage=True,
                geometry_available=False,
                geometry_type=GeometryType.NONE,
            ),
            time=TemporalMetadata(temporal_resolution="annual release, model-based estimate"),
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
                authentication_required=False,
                license="Open Data Commons Open Database License (ODbL), per data.cdc.gov.",
            ),
            provenance=ProvenanceMetadata(
                source_organization=self.source_organization,
                source_url=BASE_URL,
                retrieval_timestamp=fetch_result.retrieved_at,
                metadata_source="Socrata SODA API JSON response.",
                access_method=fetch_result.access_method,
                raw_file_path=str(fetch_result.raw_path.relative_to(RAW_DIR.parent.parent)),
                raw_sha256=self.sha256_of(fetch_result.raw_path),
                transformation_history=["Downloaded unmodified JSON response from the SODA API."],
            ),
        )
