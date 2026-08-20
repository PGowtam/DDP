"""
Basic, explainable duplicate/similarity detector. Never deletes or merges
anything automatically -- only reports a classification per pair.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from src.models.schema import DatasetRecord


@dataclass
class DuplicateFinding:
    dataset_id_a: str
    dataset_id_b: str
    classification: str  # "potential_duplicate" | "potentially_related" | "unique"
    reasons: list[str]


def _normalize_title(title: str) -> set[str]:
    return {t.lower() for t in title.replace(",", " ").replace("-", " ").split() if len(t) > 2}


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def find_duplicates(records: list[DatasetRecord]) -> list[DuplicateFinding]:
    findings: list[DuplicateFinding] = []
    for i, a in enumerate(records):
        for b in records[i + 1:]:
            reasons: list[str] = []

            same_publisher = a.publisher.strip().lower() == b.publisher.strip().lower()
            if same_publisher:
                reasons.append("same publisher")

            same_domain = _domain(a.source_url) == _domain(b.source_url) and _domain(a.source_url) != ""
            if same_domain:
                reasons.append("same source domain")

            title_a, title_b = _normalize_title(a.title), _normalize_title(b.title)
            overlap = title_a & title_b
            jaccard = len(overlap) / len(title_a | title_b) if (title_a | title_b) else 0.0
            if jaccard >= 0.3:
                reasons.append(f"title token overlap (jaccard={jaccard:.2f})")

            shared_measures = set(a.measures) & set(b.measures)
            if shared_measures:
                reasons.append(f"shared measures: {sorted(shared_measures)}")

            if jaccard >= 0.6 or (same_domain and jaccard >= 0.3):
                classification = "potential_duplicate"
            elif reasons:
                classification = "potentially_related"
            else:
                classification = "unique"
                continue  # don't report every unique pair -- only interesting ones

            findings.append(DuplicateFinding(
                dataset_id_a=a.dataset_id, dataset_id_b=b.dataset_id,
                classification=classification, reasons=reasons,
            ))
    return findings
