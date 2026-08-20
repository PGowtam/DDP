"""
End-to-end pipeline: for every registered adapter, discover -> fetch ->
extract_metadata -> normalize -> classify -> validate -> score -> persist.

Failures in any one source are caught and recorded (never silently skipped,
never papered over with fabricated data) so the pipeline can report an
honest ingestion success rate (Phase 26).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.ingestion.base import DatasetSourceAdapter, AdapterError, METADATA_DIR, REPO_ROOT
from src.ingestion.chr import CountyHealthRankingsAdapter
from src.ingestion.census_acs import CensusACSAdapter
from src.ingestion.cdc_places import CDCPlacesAdapter
from src.ingestion.cdc_svi import CDCSVIAdapter
from src.ingestion.oeps import OEPSAdapter
from src.models.schema import DatasetRecord
from src.ontology.classifier import classify
from src.validation.rules import validate_record, metadata_completeness_score

logger = logging.getLogger(__name__)

ALL_ADAPTERS: list[type[DatasetSourceAdapter]] = [
    CountyHealthRankingsAdapter,
    CensusACSAdapter,
    CDCPlacesAdapter,
    CDCSVIAdapter,
    OEPSAdapter,
]

INDEX_PATH = REPO_ROOT / "data" / "metadata" / "index.json"


@dataclass
class IngestionOutcome:
    dataset_id: str
    source_id: str
    success: bool
    error: str | None = None


@dataclass
class PipelineReport:
    outcomes: list[IngestionOutcome] = field(default_factory=list)
    records: list[DatasetRecord] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if not self.outcomes:
            return 0.0
        return round(sum(1 for o in self.outcomes if o.success) / len(self.outcomes), 2)


def run_pipeline(adapters: list[type[DatasetSourceAdapter]] | None = None) -> PipelineReport:
    adapters = adapters or ALL_ADAPTERS
    report = PipelineReport()

    for adapter_cls in adapters:
        adapter = adapter_cls()
        try:
            descriptors = adapter.discover()
        except Exception as exc:  # discovery itself can fail for a whole source
            logger.error("discover() failed for %s: %s", adapter.source_id, exc)
            report.outcomes.append(IngestionOutcome(
                dataset_id=f"{adapter.source_id}:discover", source_id=adapter.source_id,
                success=False, error=str(exc),
            ))
            continue

        for descriptor in descriptors:
            dataset_id = descriptor["dataset_id"]
            try:
                fetch_result = adapter.fetch(descriptor)
                raw_metadata = adapter.extract_metadata(descriptor, fetch_result)
                record = adapter.normalize(raw_metadata)

                classification = classify([
                    record.title, record.description or "",
                    " ".join(record.topics), " ".join(record.measures),
                ])
                record.sdoh_domains = classification

                status, errors, warnings = validate_record(record)
                record.quality.validation_status = status
                record.quality.validation_errors = errors
                record.quality.warnings = warnings
                record.quality.metadata_completeness_score = metadata_completeness_score(record)

                _write_record(record)
                report.records.append(record)
                report.outcomes.append(IngestionOutcome(dataset_id=dataset_id, source_id=adapter.source_id, success=True))
                logger.info("Ingested %s (%s) -- status=%s", dataset_id, adapter.source_id, status)

            except AdapterError as exc:
                logger.warning("Ingestion failed for %s (%s): %s", dataset_id, adapter.source_id, exc)
                report.outcomes.append(IngestionOutcome(
                    dataset_id=dataset_id, source_id=adapter.source_id, success=False, error=str(exc),
                ))
            except Exception as exc:  # unexpected -- still record, don't crash the whole run
                logger.exception("Unexpected error ingesting %s", dataset_id)
                report.outcomes.append(IngestionOutcome(
                    dataset_id=dataset_id, source_id=adapter.source_id, success=False,
                    error=f"Unexpected error: {exc}",
                ))

    _write_index(report.records)
    _write_pipeline_report(report)
    return report


def _write_record(record: DatasetRecord) -> None:
    path = METADATA_DIR / f"{record.dataset_id}.json"
    path.write_text(record.model_dump_json(indent=2))


def _write_index(records: list[DatasetRecord]) -> None:
    INDEX_PATH.write_text(json.dumps([r.model_dump(mode="json") for r in records], indent=2))


def _write_pipeline_report(report: PipelineReport) -> None:
    path = METADATA_DIR / "pipeline_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "success_rate": report.success_rate,
        "total_sources_attempted": len(report.outcomes),
        "successful": [o.dataset_id for o in report.outcomes if o.success],
        "failed": [
            {"dataset_id": o.dataset_id, "source_id": o.source_id, "error": o.error}
            for o in report.outcomes if not o.success
        ],
    }
    path.write_text(json.dumps(payload, indent=2))


def load_index() -> list[DatasetRecord]:
    if not INDEX_PATH.exists():
        return []
    raw = json.loads(INDEX_PATH.read_text())
    return [DatasetRecord.model_validate(r) for r in raw]
