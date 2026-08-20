"""
These tests exercise the adapter architecture and pipeline error-handling
without making real network calls, so they run deterministically in CI.
Real-network behavior is exercised manually (see docs/demo-script.md) and
was verified during development against the actual CHR&R GitHub source
(see src/ingestion/chr.py's docstring and docs/limitations.md).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.ingestion.base import DatasetSourceAdapter, FetchResult, AdapterError
from src.models.schema import DatasetRecord, ProvenanceMetadata
import src.pipeline.pipeline as pipeline_module
from src.pipeline.pipeline import run_pipeline
from datetime import datetime


@pytest.fixture(autouse=True)
def _isolate_pipeline_output(tmp_path, monkeypatch):
    """Tests must never write into the repo's real data/metadata/ directory --
    that would silently clobber real ingested output with test fixtures.
    Redirect INDEX_PATH and the metadata/raw dirs used by write_manifest and
    _write_index/_write_pipeline_report to an isolated tmp_path instead."""
    import src.ingestion.base as base_module

    tmp_metadata = tmp_path / "metadata"
    tmp_raw = tmp_path / "raw"
    tmp_processed = tmp_path / "processed"
    tmp_metadata.mkdir()
    tmp_raw.mkdir()
    tmp_processed.mkdir()

    monkeypatch.setattr(base_module, "METADATA_DIR", tmp_metadata)
    monkeypatch.setattr(base_module, "RAW_DIR", tmp_raw)
    monkeypatch.setattr(base_module, "PROCESSED_DIR", tmp_processed)
    monkeypatch.setattr(pipeline_module, "METADATA_DIR", tmp_metadata)
    monkeypatch.setattr(pipeline_module, "INDEX_PATH", tmp_metadata / "index.json")
    monkeypatch.setattr(pipeline_module, "REPO_ROOT", tmp_path)
    yield


class _AlwaysFailsAdapter(DatasetSourceAdapter):
    source_id = "always_fails"
    source_organization = "Nonexistent Org"

    def discover(self):
        return [{"dataset_id": "will_fail"}]

    def fetch(self, descriptor):
        raise AdapterError("simulated network failure")

    def extract_metadata(self, descriptor, fetch_result):
        raise NotImplementedError

    def normalize(self, raw_metadata):
        raise NotImplementedError


class _AlwaysSucceedsAdapter(DatasetSourceAdapter):
    source_id = "always_succeeds"
    source_organization = "Fake Org"

    def discover(self):
        return [{"dataset_id": "fake_ds"}]

    def fetch(self, descriptor):
        path = Path("/tmp/fake_ds.csv")
        path.write_text("a,b\n1,2\n")
        return FetchResult(
            dataset_id="fake_ds", raw_path=path, retrieved_at=self.now(),
            access_method="fake local file for testing",
        )

    def extract_metadata(self, descriptor, fetch_result):
        return {"fetch_result": fetch_result}

    def normalize(self, raw_metadata):
        fr = raw_metadata["fetch_result"]
        return DatasetRecord(
            dataset_id="fake_ds",
            title="Fake Dataset",
            publisher="Fake Org",
            source_url="https://example.com/fake",
            provenance=ProvenanceMetadata(
                source_organization="Fake Org",
                source_url="https://example.com/fake",
                retrieval_timestamp=fr.retrieved_at,
                metadata_source="test",
            ),
        )


def test_adapter_failure_is_caught_and_recorded_not_fabricated():
    report = run_pipeline(adapters=[_AlwaysFailsAdapter])
    assert len(report.outcomes) == 1
    assert report.outcomes[0].success is False
    assert "simulated network failure" in report.outcomes[0].error
    assert report.records == []  # no fabricated record was produced


def test_successful_adapter_produces_validated_record():
    report = run_pipeline(adapters=[_AlwaysSucceedsAdapter])
    assert report.success_rate == 1.0
    assert len(report.records) == 1
    assert report.records[0].dataset_id == "fake_ds"


def test_mixed_success_and_failure_reports_partial_rate():
    report = run_pipeline(adapters=[_AlwaysSucceedsAdapter, _AlwaysFailsAdapter])
    assert report.success_rate == 0.5


def test_sha256_helper_is_deterministic(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hello world")
    h1 = DatasetSourceAdapter.sha256_of(f)
    h2 = DatasetSourceAdapter.sha256_of(f)
    assert h1 == h2
    assert len(h1) == 64
