"""
Explainable Business Intelligence & Financial Health Decision Support
System for Kenyan SMEs — Streamlit entry point.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config.settings import APP_SUBTITLE, APP_TITLE
from src.analytics.kpis import compute_all_kpis
from src.data.cleaning import clean_dataset, reconstruct_inventory
from src.data.loader import load_csv, load_default_sample
from src.data.validation import build_data_quality_report
from src.explainability.drivers import detect_drivers
from src.explainability.explanations import build_executive_summary, build_explanation_cards
from src.explainability.recommendations import build_recommendations
from src.health.rag import classify as classify_rag
from src.health.scoring import compute_health_score
from src.utils.formatting import rag_badge_md

st.set_page_config(page_title=APP_TITLE, layout="wide", page_icon="📊")


@st.cache_data(show_spinner=False)
def _run_pipeline(file_bytes: bytes, file_name: str):
    import io
    load_result = load_csv(io.BytesIO(file_bytes))
    if not load_result.success:
        return {"success": False, "error": load_result.error_message,
                "missing_columns": load_result.missing_columns}

    clean_result = clean_dataset(load_result.raw_df)
    analytical_df = clean_result["analytical_df"]
    inv_summary = reconstruct_inventory(analytical_df)
    dq_report = build_data_quality_report(
        analytical_df, clean_result["flags"], clean_result["exclusion_summary"], inv_summary
    )
    kpis = compute_all_kpis(analytical_df)
    health_result = compute_health_score(kpis, dq_report.overall_score, dq_report.inventory_integrity_ok)
    rag_result = classify_rag(kpis, health_result.total_score, dq_report)
    drivers = detect_drivers(kpis, dq_report)
    explanation_cards = build_explanation_cards(kpis, drivers)
    recommendations = build_recommendations(kpis, drivers)
    executive_summary = build_executive_summary(
        kpis, health_result.total_score, rag_result.status, dq_report, drivers
    )

    return {
        "success": True,
        "raw_df": load_result.raw_df,
        "analytical_df": analytical_df,
        "exclusion_summary": clean_result["exclusion_summary"],
        "inventory_summary": inv_summary,
        "dq_report": dq_report,
        "kpis": kpis,
        "health_result": health_result,
        "rag_result": rag_result,
        "drivers": drivers,
        "explanation_cards": explanation_cards,
        "recommendations": recommendations,
        "executive_summary": executive_summary,
        "file_name": file_name,
    }


def main():
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    with st.sidebar:
        st.header("Data Input")
        uploaded = st.file_uploader("Upload SME transaction CSV", type=["csv"])
        use_sample = st.checkbox("Use bundled sample dataset", value=uploaded is None)
        st.divider()
        st.caption(
            "Navigate using the pages in the sidebar above once data has "
            "been loaded: Data Quality → Financial Performance → "
            "Product & Category → Customer → Branch & Channel → "
            "Financial Health → Explainable Insights → Recommendations → Report."
        )

    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        file_name = uploaded.name
    elif use_sample:
        with open("data/sample/kenyan_sme_bi_financial_operational_data_1800_records.csv", "rb") as f:
            file_bytes = f.read()
        file_name = "sample dataset (bundled)"
    else:
        st.info("Upload a CSV file or check 'Use bundled sample dataset' to begin.")
        return

    result = _run_pipeline(file_bytes, file_name)

    if not result["success"]:
        st.error(result["error"])
        if result.get("missing_columns"):
            st.write("Missing columns:", result["missing_columns"])
        return

    st.session_state["pipeline_result"] = result

    dq = result["dq_report"]
    health = result["health_result"]
    rag = result["rag_result"]
    core = result["kpis"]["core"]

    st.success(f"Loaded {file_name} — {dq.row_count:,} rows, {dq.column_count} columns.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Financial Health Score", f"{health.total_score:.1f} / 100")
    col2.markdown(f"**RAG Status**<br>{rag_badge_md(rag.status)}", unsafe_allow_html=True)
    col3.markdown(f"**Data Reliability**<br>{rag_badge_md(dq.status, dq.status)}", unsafe_allow_html=True)
    col4.metric("Adjusted Revenue", f"KES {core['adjusted_revenue']:,.0f}")

    if rag.triggered_overrides:
        with st.container(border=True):
            st.markdown("**Why RED?** Critical-risk override(s) triggered:")
            for o in rag.triggered_overrides:
                st.markdown(f"- **{o['rule']}**: {o['explanation']}")

    st.subheader("Executive Summary")
    st.write(result["executive_summary"])

    st.divider()
    st.caption(
        "This is a prototype academic decision-support system. It does not "
        "replace professional accounting, tax, or financial advisory "
        "services, and does not guarantee future business performance. "
        "Use the pages in the left sidebar to explore the full analysis."
    )


if __name__ == "__main__":
    main()
