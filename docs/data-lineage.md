# Data Lineage

Every ingested dataset has two lineage artifacts:

1. **The raw file itself**, unmodified, under `data/raw/<dataset_id>.<ext>`.
2. **A canonical metadata record**, `data/metadata/<dataset_id>.json`, whose
   `provenance` block records, for every field:

```json
{
  "source_organization": "...",
  "source_url": "...",
  "retrieval_timestamp": "...",
  "metadata_source": "...",
  "access_method": "...",
  "raw_file_path": "data/raw/<dataset_id>.csv",
  "raw_sha256": "<64-char hex digest of the raw file at fetch time>",
  "transformation_history": ["step 1", "step 2", "..."]
}
```

`data/metadata/pipeline_report.json` additionally records, for the whole
pipeline run: which sources succeeded, which failed and why (verbatim
exception text -- see `docs/limitations.md` for the two real, current
failures), and an overall success rate.

## How to verify a record traces back to real source data

```bash
python -m sdoh pipeline
python3 -c "
import json, hashlib
rec = json.load(open('data/metadata/chrr_v063_median_household_income_r2025.json'))
raw = open(rec['provenance']['raw_file_path'], 'rb').read()
assert hashlib.sha256(raw).hexdigest() == rec['provenance']['raw_sha256']
print('raw file hash matches recorded provenance -- OK')
"
```

Because raw files are excluded from version control (`.gitignore`) to avoid
committing third-party data, `raw_sha256` is what lets someone re-fetch the
same source URL later and confirm they got byte-identical data -- or detect
that the upstream source has changed since this pipeline last ran.
