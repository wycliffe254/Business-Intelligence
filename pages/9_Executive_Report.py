import streamlit as st

from src.reporting.report import build_html_report

st.set_page_config(page_title="Executive Report", layout="wide")
st.title("Executive Business Health Report")

if "pipeline_result" not in st.session_state:
    st.warning("Load a dataset on the main page first.")
    st.stop()

r = st.session_state["pipeline_result"]

html_report = build_html_report(
    kpis=r["kpis"],
    health_result=r["health_result"],
    rag_result=r["rag_result"],
    dq_report=r["dq_report"],
    drivers=r["drivers"],
    explanation_cards=r["explanation_cards"],
    recommendations=r["recommendations"],
    executive_summary=r["executive_summary"],
)

st.download_button(
    "Download Executive Report (HTML)",
    html_report.encode("utf-8"),
    file_name="business_health_report.html",
    mime="text/html",
)
st.caption("Open the downloaded HTML file in a browser and use Print → Save as PDF if a PDF copy is needed.")

st.divider()
st.subheader("Preview")
st.components.v1.html(html_report, height=900, scrolling=True)

st.divider()
st.subheader("Other Downloads")
c1, c2, c3 = st.columns(3)
with c1:
    kpi_summary_df = st.session_state["pipeline_result"]["kpis"]["core"]
    import pandas as pd
    kpi_df = pd.DataFrame([kpi_summary_df])
    st.download_button(
        "KPI Summary (CSV)", kpi_df.to_csv(index=False).encode("utf-8"),
        file_name="kpi_summary.csv", mime="text/csv",
    )
with c2:
    st.download_button(
        "Product/Category Table (CSV)",
        r["kpis"]["product_category"].to_csv(index=False).encode("utf-8"),
        file_name="product_category_performance.csv", mime="text/csv",
    )
with c3:
    st.download_button(
        "Branch Performance (CSV)",
        r["kpis"]["branch"].to_csv(index=False).encode("utf-8"),
        file_name="branch_performance.csv", mime="text/csv",
    )
