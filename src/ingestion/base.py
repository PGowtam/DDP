"""
Base adapter interface. Adding a new data source means subclassing
DatasetSourceAdapter and implementing discover/fetch/extract_metadata/
normalize/validate -- nothing else in the pipeline needs to change.
"""
from __future__ import annotations

import abc
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
METADATA_DIR = REPO_ROOT / "data" / "metadata"


@dataclass
class FetchResult:
    """What an adapter's fetch() step produces."""
    dataset_id: str
    raw_path: Path
    retrieved_at: datetime
    access_method: str
    success: bool = True
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class AdapterError(RuntimeError):
    """Raised when a source cannot be discovered, fetched, or parsed.

    Per the project's research-integrity rules, adapters must raise this
    (and the pipeline must record it) rather than silently returning
    fabricated or placeholder data.
    """


class DatasetSourceAdapter(abc.ABC):
    """One adapter per publisher/source. See src/ingestion/chr.py for a
    fully worked, real example."""

    #: short machine-readable id for this source, e.g. "county_health_rankings"
    source_id: str = "base"
    #: human-readable publisher/org name for provenance
    source_organization: str = "Unknown"

    def __init__(self) -> None:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        METADATA_DIR.mkdir(parents=True, exist_ok=True)

    # -- required interface -------------------------------------------------
    @abc.abstractmethod
    def discover(self) -> list[dict[str, Any]]:
        """Return a list of dataset descriptors this adapter can fetch.
        Each descriptor is a plain dict the adapter itself defines
        (e.g. {"dataset_id": ..., "url": ...})."""

    @abc.abstractmethod
    def fetch(self, descriptor: dict[str, Any]) -> FetchResult:
        """Retrieve raw data for one descriptor and save it under data/raw/,
        unmodified. Must raise AdapterError on failure -- never fabricate
        a placeholder file."""

    @abc.abstractmethod
    def extract_metadata(self, descriptor: dict[str, Any], fetch_result: FetchResult) -> dict[str, Any]:
        """Pull whatever metadata is directly observable from the source
        and/or the raw file (columns, row count, etc). Returns a plain
        dict; normalize() turns this into a DatasetRecord."""

    @abc.abstractmethod
    def normalize(self, raw_metadata: dict[str, Any]) -> "DatasetRecord":  # noqa: F821
        """Map raw_metadata into the canonical DatasetRecord schema."""

    # -- shared helpers -------------------------------------------------
    @staticmethod
    def sha256_of(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

    def write_manifest(self, dataset_id: str, manifest: dict[str, Any]) -> Path:
        path = METADATA_DIR / f"{dataset_id}.manifest.json"
        path.write_text(json.dumps(manifest, indent=2, default=str))
        return path
