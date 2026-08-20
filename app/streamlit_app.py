"""
SDOH Dataset Discovery -- Streamlit prototype UI.

Run with: streamlit run app/streamlit_app.py
Requires `python -m sdoh pipeline` to have been run at least once so that
data/metadata/index.json exists. Falls back to demo/metadata.json if the
live index is empty, so the app is always demonstrable (Phase 27).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.pipeline.pipeline import load_index
from src.search.engine import SearchIndex
from src.models.schema import DatasetRecord, SDOH_DOMAINS, GeographicLevel
from src.ingestion.user_upload import infer_upload_metadata

st.set_page_config(page_title="SDOH Dataset Discovery (prototype)", layout="wide")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB, per Phase 30 (basic upload validation)


@st.cache_data(show_spinner=False)
def _load_records(mode: str):
    if mode == "live":
        return load_index()
    demo_path = REPO_ROOT / "demo" / "metadata.json"
    raw = json.loads(demo_path.read_text())
    return [DatasetRecord.model_validate(r) for r in raw]


def _render_upload_tab() -> None:
    st.subheader("Upload a regional dataset")
    st.caption(
        "Upload a CSV to preview inferred metadata (geography columns, time columns, "
        "numeric measures). Nothing is saved to the index automatically — you review "
        "the preview before accepting."
    )
    uploaded = st.file_uploader("CSV file", type=["csv"])
    if uploaded is None:
        return
    if uploaded.size > MAX_UPLOAD_BYTES:
        st.error(f"File exceeds the {MAX_UPLOAD_BYTES // (1024*1024)}MB prototype limit.")
        return

    csv_text = uploaded.read().decode("utf-8", errors="replace")
    result = infer_upload_metadata(csv_text)

    st.markdown("**Detected Geography**")
    st.write(", ".join(result.detected_geography_columns) or ("lat/lon columns" if result.detected_lat_lon else "_none detected_"))
    st.markdown("**Detected Time Columns**")
    st.write(", ".join(result.detected_time_columns) or "_none detected_")
    st.markdown("**Detected Numeric Measures**")
    st.write(", ".join(result.detected_numeric_measures) or "_none detected_")
    st.markdown("**Detected Categorical Columns**")
    st.write(", ".join(result.detected_categorical_columns) or "_none detected_")
    st.markdown(f"**Rows scanned:** {result.row_count}")

    if result.warnings:
        st.warning("Warnings:\n" + "\n".join(f"- {w}" for w in result.warnings))

    st.info(
        "This preview is not automatically accepted. A production version would let "
        "you edit title, publisher, and license before adding it to the index."
    )


def main() -> None:
    st.title("SDOH Dataset Discovery")

    tab_search, tab_upload = st.tabs(["Search datasets", "Upload a dataset"])
    with tab_upload:
        _render_upload_tab()

    with tab_search:
        live_records = load_index()
        mode = "live" if live_records else "demo"
        if mode == "demo":
            st.info(
                "No live pipeline output found (run `python -m sdoh pipeline` first). "
                "Showing the deterministic demo index instead — see docs/demo-script.md."
            )
        records = _load_records(mode)

        with st.sidebar:
            st.header("Filters")
            query = st.text_input("Search", placeholder="e.g. income, housing, food access")
            geo_options = ["(any)"] + sorted({r.geography.geographic_level for r in records})
            geography = st.selectbox("Geography", geo_options)
            domain_options = ["(any)"] + list(SDOH_DOMAINS)
            domain = st.selectbox("SDOH Domain", domain_options)
            publisher = st.text_input("Publisher contains")

        index = SearchIndex(records)
        results = index.search(
            query=query or None,
            geography_level=None if geography == "(any)" else geography,
            sdoh_domain=None if domain == "(any)" else domain,
            publisher=publisher or None,
        )

        st.subheader(f"Results ({len(results)} of {len(records)} datasets)")

        for res in results:
            r = res.record
            with st.container(border=True):
                cols = st.columns([3, 1])
                with cols[0]:
                    st.markdown(f"**{r.title}**")
                    st.caption(f"{r.publisher}")
                    if r.description:
                        st.write(r.description)
                with cols[1]:
                    st.metric("Completeness", f"{(r.quality.metadata_completeness_score or 0):.0%}")
                    st.caption(f"Validation: {r.quality.validation_status}")

                badge_cols = st.columns(4)
                badge_cols[0].markdown(f"**Geography:** {r.geography.geographic_level}")
                badge_cols[1].markdown(f"**Domain:** {r.sdoh_domains.primary_domain or '_unclassified_'}")
                badge_cols[2].markdown(f"**Format:** {r.structure.file_format}")
                badge_cols[3].markdown(f"**Period:** {r.time.reference_period or '_unknown_'}")

                with st.expander("Metadata, provenance & geography detail"):
                    st.markdown(f"- **Source:** [{r.source_url}]({r.source_url})")
                    st.markdown(f"- **Retrieved:** {r.provenance.retrieval_timestamp}")
                    st.markdown(f"- **Access method:** {r.provenance.access_method}")
                    st.markdown(
                        f"- **Geometry available:** {r.geography.geometry_available} "
                        f"(type: {r.geography.geometry_type})"
                    )
                    st.markdown(f"- **Rows x Columns:** {r.structure.row_count} x {r.structure.column_count}")
                    if r.quality.warnings:
                        st.warning("Warnings: " + "; ".join(r.quality.warnings))
                    if r.quality.validation_errors:
                        st.error("Errors: " + "; ".join(r.quality.validation_errors))


if __name__ == "__main__":
    main()
