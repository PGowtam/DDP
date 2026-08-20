# Evaluation

All numbers below were computed by actually running `python -m sdoh pipeline`
against this repository's 3 successfully-ingested real datasets on
2026-08-19, then querying the resulting index. Nothing here is invented or
projected -- see `data/metadata/pipeline_report.json` and the reproduction
command at the bottom of this file.

## Ingestion

| Metric | Value |
|---|---|
| Sources attempted | 5 (3 CHR&R measure files + Census ACS + CDC PLACES) |
| Successful | 3 |
| Failed | 2 (Census ACS, CDC PLACES -- see `docs/limitations.md` for why) |
| Ingestion success rate | 60% |

## Metadata

| Metric | Value |
|---|---|
| Average metadata completeness score | 1.00 (all 3 records fully populate every scored field) |
| Fields most frequently missing | none, among the 3 ingested records |

This 100% figure should be read with caution: it reflects that this
adapter's `normalize()` step was written carefully for exactly 3 known
files, not that real-world metadata is typically this complete. A larger,
more heterogeneous catalog (see `docs/future-work.md`) would very likely
show lower and more varied completeness.

## Validation

| Metric | Value |
|---|---|
| Total validation errors (blocking) | 0 |
| Total validation warnings | 2 |

Both warnings are "No SDOH domain could be classified from title/
description/measures" -- the deterministic keyword classifier
(`src/ontology/classifier.py`) didn't find a matching keyword for the
Premature Death (YPLL) and race/ethnicity population datasets. This is an
honest limitation of a small keyword list, not a validation bug -- see
`docs/limitations.md`.

## Search: manual evaluation set

This is a small, manually defined evaluation set, exactly as the project
brief requests, run against the current 3-dataset index:

| Query | Results | Relevant result appears? |
|---|---|---|
| `income` | 1 (`chrr_v063_median_household_income_r2025`) | Yes -- top result is exactly the income dataset |
| `housing` | 0 | N/A -- no housing dataset is currently ingested |
| `unemployment` | 0 | N/A -- no unemployment dataset is currently ingested |
| `food access` | 0 | N/A -- no food-access dataset is currently ingested |
| `education` | 0 | N/A -- no education dataset is currently ingested |
| `healthcare` | 0 | N/A -- premature death is a health *outcome*, not classified under "healthcare" keywords |

**This evaluation is intentionally small and its zero-result rows are
expected, not a search-quality failure** -- the queries were chosen to match
the project brief's example list, but this build's catalog only contains 3
income/mortality/demographic datasets. Once the Census ACS and CDC PLACES
adapters are run in an unrestricted network environment (`docs/future-work.md`),
the `housing` and `healthcare` queries in particular should return results.

## Reproduction

```bash
python -m sdoh pipeline
python3 -c "
import json
from src.search.engine import SearchIndex
from src.models.schema import DatasetRecord
records = [DatasetRecord.model_validate(r) for r in json.load(open('data/metadata/index.json'))]
index = SearchIndex(records)
for q in ['housing','unemployment','food access','education','healthcare','income']:
    results = index.search(query=q)
    print(q, '->', [r.record.dataset_id for r in results])
"
```
