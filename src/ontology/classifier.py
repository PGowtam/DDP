"""
Deterministic, explainable, rule-based SDOH domain classifier.

This is the primary classification path -- a transparent keyword-match
over the SDOH taxonomy, with no opaque LLM step. If an LLM/embedding
classifier is ever added, its output must be stored separately and
flagged machine_generated=True on the DomainClassification model.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from src.models.schema import DomainClassification

_TAXONOMY_PATH = Path(__file__).resolve().parents[2] / "configs" / "sdoh_taxonomy.yaml"


def _load_taxonomy() -> dict:
    with open(_TAXONOMY_PATH) as fh:
        return yaml.safe_load(fh)["domains"]


_TAXONOMY = _load_taxonomy()


def classify(text_fields: list[str]) -> DomainClassification:
    """text_fields: e.g. [title, description, ' '.join(topics), ' '.join(measures)].
    Scores each domain by counting keyword hits, in a fully transparent way."""
    haystack = " ".join(f for f in text_fields if f).lower()

    scores: dict[str, list[str]] = {}
    for domain_id, spec in _TAXONOMY.items():
        hits = [kw for kw in spec["keywords"] if kw in haystack]
        if hits:
            scores[domain_id] = hits

    if not scores:
        return DomainClassification(
            primary_domain=None, secondary_domains=[], keywords=[],
            confidence=0.0, rationale=[], machine_generated=False,
        )

    ranked = sorted(scores.items(), key=lambda kv: len(kv[1]), reverse=True)
    primary_domain, primary_hits = ranked[0]
    secondary = [d for d, _ in ranked[1:]]
    total_possible = sum(len(spec["keywords"]) for spec in _TAXONOMY.values())
    total_hits = sum(len(h) for h in scores.values())
    # simple, transparent confidence: how concentrated the hits are on the
    # top domain, scaled down for datasets with very few keyword hits overall.
    concentration = len(primary_hits) / total_hits
    coverage = min(1.0, total_hits / 3)  # 3+ keyword hits -> full coverage credit
    confidence = round(concentration * coverage, 2)

    return DomainClassification(
        primary_domain=primary_domain,
        secondary_domains=secondary,
        keywords=sorted({kw for hits in scores.values() for kw in hits}),
        confidence=confidence,
        rationale=primary_hits,
        machine_generated=False,
    )
