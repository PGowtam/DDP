"""CLI: python -m sdoh <command>"""
from __future__ import annotations

import argparse
import logging
import sys

from src.pipeline.pipeline import run_pipeline, load_index
from src.search.engine import SearchIndex
from src.search.duplicates import find_duplicates


def cmd_pipeline(args: argparse.Namespace) -> None:
    report = run_pipeline()
    print(f"Ingestion complete. Success rate: {report.success_rate:.0%} "
          f"({sum(1 for o in report.outcomes if o.success)}/{len(report.outcomes)})")
    for o in report.outcomes:
        status = "OK" if o.success else f"FAILED: {o.error}"
        print(f"  [{o.source_id}] {o.dataset_id} -- {status}")


def cmd_ingest(args: argparse.Namespace) -> None:
    cmd_pipeline(args)


def cmd_validate(args: argparse.Namespace) -> None:
    records = load_index()
    if not records:
        print("No records found. Run `python -m sdoh pipeline` first.")
        return
    for r in records:
        print(f"{r.dataset_id}: {r.quality.validation_status} "
              f"(errors={len(r.quality.validation_errors)}, warnings={len(r.quality.warnings)}, "
              f"completeness={r.quality.metadata_completeness_score})")


def cmd_search(args: argparse.Namespace) -> None:
    records = load_index()
    if not records:
        print("No records found. Run `python -m sdoh pipeline` first.")
        return
    index = SearchIndex(records)
    results = index.search(query=args.query, geography_level=args.geography, sdoh_domain=args.domain)
    if not results:
        print("No results.")
        return
    for res in results:
        r = res.record
        print(f"[{res.score:.1f}] {r.title}  ({r.publisher})")
        print(f"        domain={r.sdoh_domains.primary_domain}  geo={r.geography.geographic_level}  "
              f"completeness={r.quality.metadata_completeness_score}")


def cmd_duplicates(args: argparse.Namespace) -> None:
    records = load_index()
    findings = find_duplicates(records)
    if not findings:
        print("No potential duplicates or related datasets found.")
        return
    for f in findings:
        print(f"[{f.classification}] {f.dataset_id_a}  <->  {f.dataset_id_b}")
        for reason in f.reasons:
            print(f"    - {reason}")


def cmd_index(args: argparse.Namespace) -> None:
    records = load_index()
    print(f"{len(records)} records currently indexed (data/metadata/index.json).")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sdoh")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("pipeline", help="Run the full ingest -> normalize -> validate -> index pipeline").set_defaults(func=cmd_pipeline)
    sub.add_parser("ingest", help="Alias for pipeline").set_defaults(func=cmd_ingest)
    sub.add_parser("validate", help="Print validation status for all indexed records").set_defaults(func=cmd_validate)
    sub.add_parser("index", help="Show index summary").set_defaults(func=cmd_index)

    p_search = sub.add_parser("search", help="Search indexed datasets")
    p_search.add_argument("query", nargs="?", default=None)
    p_search.add_argument("--geography", default=None)
    p_search.add_argument("--domain", default=None)
    p_search.set_defaults(func=cmd_search)

    sub.add_parser("duplicates", help="Report potential duplicate/related datasets").set_defaults(func=cmd_duplicates)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
