"""
SDOH Dataset Discovery -- Streamlit prototype UI.

Run with: streamlit run app/streamlit_app.py
Requires `python -m sdoh pipeline` to have been run at least once so that
data/metadata/index.json exists. Falls back to demo/metadata.json if the
live index is empty, so the app is always demonstrable.
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

st.set_page_config(
    page_title="SDOH Dataset Discovery — Research Prototype",
    page_icon="🔍",
    layout="wide",
)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@st.cache_data(show_spinner=False)
def _load_records(mode: str):
    if mode == "live":
        return load_index()
    demo_path = REPO_ROOT / "demo" / "metadata.json"
    raw = json.loads(demo_path.read_text())
    return [DatasetRecord.model_validate(r) for r in raw]


def _render_upload_tab() -> None:
    st.subheader("Upload a regional dataset (CSV)")

    st.warning(
        "⚠️ **Inferred metadata is a proposal for review, not authoritative metadata.** "
        "Nothing is saved to the index automatically. In a production system, a researcher "
        "would edit the inferred fields — title, publisher, license — before accepting.",
        icon="⚠️",
    )

    st.caption(
        "Upload a CSV to preview what the pipeline can infer: geography columns, "
        "time columns, numeric measures, categorical fields, and data quality warnings."
    )

    uploaded = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded is None:
        return
    if uploaded.size > MAX_UPLOAD_BYTES:
        st.error(f"File exceeds the {MAX_UPLOAD_BYTES // (1024*1024)} MB prototype limit.")
        return

    csv_text = uploaded.read().decode("utf-8", errors="replace")
    result = infer_upload_metadata(csv_text)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Rows scanned", result.row_count)
        st.metric("Total columns", len(result.detected_columns))
    with col2:
        st.metric("Numeric measure columns", len(result.detected_numeric_measures))
        st.metric("Geographic ID columns", len(result.detected_geography_columns))

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Detected geography columns**")
        st.code(
            ", ".join(result.detected_geography_columns)
            or ("lat/lon pair detected" if result.detected_lat_lon else "none detected")
        )
        st.markdown("**Suggested geographic level**")
        st.code(result.suggested_geographic_level)
    with c2:
        st.markdown("**Detected time columns**")
        st.code(", ".join(result.detected_time_columns) or "none detected")
        st.markdown("**Detected categorical columns**")
        st.code(", ".join(result.detected_categorical_columns) or "none detected")

    if result.detected_numeric_measures:
        st.markdown("**Detected numeric measure columns**")
        st.code(", ".join(result.detected_numeric_measures))

    if result.warnings:
        st.warning(
            "**Inference warnings** (fields that could not be inferred and require manual entry):\n\n"
            + "\n".join(f"- {w}" for w in result.warnings)
        )

    st.info(
        "**Next step (not implemented in this prototype):** a researcher would review "
        "the above, fill in title / publisher / license, confirm the geographic level, "
        "and explicitly approve indexing. The pipeline would then validate the completed "
        "record before adding it to the search index."
    )


def main() -> None:
    st.title("🔍 SDOH Dataset Discovery")
    st.caption(
        "A research prototype for discovering and exploring public Social Determinants of "
        "Health (SDOH) datasets. Developed to explore computational approaches to metadata "
        "normalization, geographic characterization, provenance tracking, and dataset "
        "discovery for heterogeneous public health data. "
        "**This is not affiliated with, endorsed by, or part of the SDOH & Place Project, "
        "HEROP Lab, or the University of Illinois.**"
    )

    tab_search, tab_upload = st.tabs(["🔎 Search datasets", "📤 Upload a dataset"])

    with tab_upload:
        _render_upload_tab()

    with tab_search:
        live_records = load_index()
        mode = "live" if live_records else "demo"
        if mode == "demo":
            st.info(
                "No live pipeline output found — run `python -m sdoh pipeline` first. "
                "Showing the deterministic demo index. See `docs/demo-script.md`."
            )
        records = _load_records(mode)

        with st.sidebar:
            st.header("Filters")
            query = st.text_input(
                "Keyword search",
                placeholder="e.g. income, housing, food access, mortality",
            )
            geo_options = ["(any)"] + sorted({r.geography.geographic_level for r in records})
            geography = st.selectbox("Geography level", geo_options)
            domain_options = ["(any)"] + list(SDOH_DOMAINS)
            domain = st.selectbox("SDOH domain", domain_options)
            publisher = st.text_input("Publisher contains")
            st.markdown("---")
            st.caption(
                f"**{len(records)} datasets** in index. "
                f"Search is deterministic keyword + facet ranking — "
                f"no ML model involved."
            )

        index = SearchIndex(records)
        results = index.search(
            query=query or None,
            geography_level=None if geography == "(any)" else geography,
            sdoh_domain=None if domain == "(any)" else domain,
            publisher=publisher or None,
        )

        st.subheader(f"Results — {len(results)} of {len(records)} datasets")

        if not results and (query or geography != "(any)" or domain != "(any)" or publisher):
            st.warning("No datasets matched your filters. Try broadening your search.")

        for res in results:
            r = res.record
            with st.container(border=True):
                header_cols = st.columns([3, 1])
                with header_cols[0]:
                    st.markdown(f"### {r.title}")
                    st.caption(f"**Publisher:** {r.publisher}")
                    if r.description:
                        st.write(r.description[:400] + ("…" if len(r.description or "") > 400 else ""))
                with header_cols[1]:
                    score_pct = int((r.quality.metadata_completeness_score or 0) * 100)
                    st.metric("Metadata completeness", f"{score_pct}%")
                    st.caption(f"Validation: `{r.quality.validation_status}`")

                badge_cols = st.columns(4)
                badge_cols[0].markdown(
                    f"**Geography:** `{r.geography.geographic_level}`"
                )
                badge_cols[1].markdown(
                    f"**SDOH domain:** `{r.sdoh_domains.primary_domain or 'unclassified'}`"
                )
                badge_cols[2].markdown(
                    f"**Format:** `{r.structure.file_format}`"
                )
                badge_cols[3].markdown(
                    f"**Period:** {r.time.reference_period or '_unknown_'}"
                )

                # Search match explanation — show WHY this result ranked
                if res.matched_on:
                    with st.expander("Why this result matched your query"):
                        st.markdown(
                            "**Search score: {:.1f}** — matched on:".format(res.score)
                        )
                        for reason in res.matched_on:
                            field, term = reason.split(":", 1)
                            st.markdown(f"  - `{field}` contains **{term}**")

                with st.expander("Metadata, provenance & geography detail"):
                    left, right = st.columns(2)
                    with left:
                        st.markdown("**Provenance**")
                        st.markdown(f"- **Source URL:** [{r.source_url}]({r.source_url})")
                        if r.landing_page_url:
                            st.markdown(f"- **Landing page:** [{r.landing_page_url}]({r.landing_page_url})")
                        st.markdown(
                            f"- **Retrieved:** {r.provenance.retrieval_timestamp.strftime('%Y-%m-%d %H:%M UTC') if r.provenance.retrieval_timestamp else 'unknown'}"
                        )
                        st.markdown(f"- **Access method:** {r.provenance.access_method or '_not documented_'}")
                        if r.provenance.raw_sha256:
                            st.markdown(f"- **SHA-256:** `{r.provenance.raw_sha256[:16]}…`")
                    with right:
                        st.markdown("**Geography**")
                        st.markdown(
                            f"- **Geometry available:** `{r.geography.geometry_available}` "
                            f"(type: `{r.geography.geometry_type}`)"
                        )
                        st.markdown(
                            f"- **Identifiers:** {', '.join(r.geography.geographic_identifiers) or '_none listed_'}"
                        )
                        st.markdown(f"- **Coverage:** {', '.join(r.geography.geographic_coverage) or '_unknown_'}")
                        st.markdown(
                            f"- **Rows × Columns:** "
                            f"{r.structure.row_count or '?'} × {r.structure.column_count or '?'}"
                        )

                    if r.sdoh_domains.rationale:
                        st.markdown("**SDOH classification rationale**")
                        st.caption(
                            f"Rule-based classifier matched keywords: "
                            f"{', '.join(r.sdoh_domains.rationale)}. "
                            f"Confidence: {r.sdoh_domains.confidence:.2f}. "
                            f"Machine-generated: `{r.sdoh_domains.machine_generated}`."
                        )

                    if r.quality.warnings:
                        st.warning("Warnings: " + "; ".join(r.quality.warnings))
                    if r.quality.validation_errors:
                        st.error("Errors: " + "; ".join(r.quality.validation_errors))

                    if r.provenance.transformation_history:
                        st.markdown("**Transformation history**")
                        for step in r.provenance.transformation_history:
                            st.markdown(f"  - {step}")


if __name__ == "__main__":
    main()
