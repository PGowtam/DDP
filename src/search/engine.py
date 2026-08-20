"""
Deterministic, explainable keyword + facet search over normalized metadata.
No external search server required -- this is intentionally simple (see
docs/architecture.md for why: Phase 10/33 of the project brief explicitly
call for a small, explainable ranking function rather than a search cluster).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.models.schema import DatasetRecord


@dataclass
class SearchResult:
    record: DatasetRecord
    score: float
    matched_on: list[str]


class SearchIndex:
    def __init__(self, records: list[DatasetRecord]):
        self.records = records

    def search(
        self,
        query: str | None = None,
        geography_level: str | None = None,
        sdoh_domain: str | None = None,
        publisher: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        q = (query or "").strip().lower()
        q_terms = [t for t in q.split() if t]

        for record in self.records:
            # -- facet filters (hard filters, applied first) --------------
            if geography_level and record.geography.geographic_level != geography_level:
                continue
            if sdoh_domain and record.sdoh_domains.primary_domain != sdoh_domain:
                if sdoh_domain not in (record.sdoh_domains.secondary_domains or []):
                    continue
            if publisher and publisher.lower() not in (record.publisher or "").lower():
                continue
            if year_from or year_to:
                start = record.time.temporal_coverage_start
                end = record.time.temporal_coverage_end
                years = set()
                if start:
                    years.add(start.year)
                if end:
                    years.add(end.year)
                # Fall back to reference_period text years if structured dates absent.
                if not years and record.time.reference_period:
                    for token in record.time.reference_period.replace("-", " ").split():
                        if token.isdigit() and len(token) == 4:
                            years.add(int(token))
                if years:
                    if year_from and max(years) < year_from:
                        continue
                    if year_to and min(years) > year_to:
                        continue

            # -- scoring ----------------------------------------------------
            score = 0.0
            matched_on: list[str] = []
            if not q_terms:
                score = 1.0  # facet-only browse, everything passing filters is equally relevant
            else:
                title = (record.title or "").lower()
                description = (record.description or "").lower()
                keywords = " ".join(record.sdoh_domains.keywords or []).lower()
                topics = " ".join(record.topics or []).lower()
                measures = " ".join(record.measures or []).lower()

                for term in q_terms:
                    if term in title:
                        score += 3
                        matched_on.append(f"title:{term}")
                    if term in description:
                        score += 2
                        matched_on.append(f"description:{term}")
                    if term in keywords:
                        score += 2
                        matched_on.append(f"sdoh_keyword:{term}")
                    if term in topics:
                        score += 1.5
                        matched_on.append(f"topic:{term}")
                    if term in measures:
                        score += 1.5
                        matched_on.append(f"measure:{term}")

            if score > 0:
                results.append(SearchResult(record=record, score=score, matched_on=matched_on))

        results.sort(key=lambda r: r.score, reverse=True)
        return results
