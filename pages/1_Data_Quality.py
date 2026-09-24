import pandas as pd
import streamlit as st

from src.utils.formatting import rag_badge_md

st.set_page_config(page_title="Data Quality", layout="wide")
st.title("Data Quality Report")

if "pipeline_result" not in st.session_state:
    st.warning("Load a dataset on the main page first.")
    st.stop()

r = st.session_state["pipeline_result"]
dq = r["dq_report"]
df = r["analytical_df"]

st.markdown(
    f"**Data Quality Score:** {dq.overall_score:.1f} / 100 &nbsp;&nbsp; {rag_badge_md(dq.status)}",
    unsafe_allow_html=True,
)
st.caption(
    "Data reliability is assessed separately from business/financial "
    "health. A poor-quality dataset does not automatically mean the "
    "business is unhealthy, and vice versa."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", f"{dq.row_count:,}")
c2.metric("Columns", dq.column_count)
c3.metric("Duplicate transaction IDs", dq.duplicate_count)
c4.metric("Invalid dates", dq.invalid_date_count)

c5, c6, c7, c8 = st.columns(4)
c5.metric("Invalid sale quantities", dq.invalid_quantity_count)
c6.metric("Inconsistent category text", dq.inconsistent_category_count)
c7.metric("Payment-label variants", dq.inconsistent_payment_label_count)
c8.metric("Financial inconsistencies", dq.financial_inconsistency_count)

st.subheader("Inventory Integrity")
if dq.inventory_integrity_ok:
    st.success("Inventory reconstruction is internally consistent for all products.")
else:
    st.error(
        "Inventory integrity: RED — reconstructed stock is negative for "
        f"{len(dq.inventory_negative_products)} product(s): "
        + ", ".join(dq.inventory_negative_products[:15])
        + (" ..." if len(dq.inventory_negative_products) > 15 else "")
    )
    st.caption(
        "Inventory turnover and stock-based KPIs are withheld from "
        "scoring until opening stock and stock movements are reconciled. "
        "This is a deliberate design choice, not a missing feature."
    )

st.subheader("Missing Values by Field")
missing_df = pd.DataFrame(
    [{"field": k, "missing_count": v, "missing_pct": round(v / dq.row_count * 100, 1)}
     for k, v in dq.missing_value_summary.items()]
).sort_values("missing_count", ascending=False)
st.dataframe(missing_df, use_container_width=True, hide_index=True)

st.subheader("Data Quality Limitations")
for lim in dq.limitations:
    st.markdown(f"- {lim}")

st.subheader("Affected Records")
tab1, tab2, tab3, tab4 = st.tabs(
    ["Duplicate transaction IDs", "Invalid dates", "Invalid sale quantities", "Financial inconsistencies"]
)
with tab1:
    st.dataframe(df[df["is_duplicate_txn_id"]].head(200), use_container_width=True)
with tab2:
    st.dataframe(df[~df["is_valid_date"]].head(200), use_container_width=True)
with tab3:
    st.dataframe(df[df["is_invalid_sale_quantity"]].head(200), use_container_width=True)
with tab4:
    st.dataframe(df[df["has_financial_inconsistency"]].head(200), use_container_width=True)

st.subheader("Exclusions from KPI Calculations")
st.json(r["exclusion_summary"])

st.subheader("Download")
c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "Download cleaned / validated dataset (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name="validated_analytical_dataset.csv",
        mime="text/csv",
    )
with c2:
    st.download_button(
        "Download raw uploaded dataset (CSV)",
        r["raw_df"].to_csv(index=False).encode("utf-8"),
        file_name="raw_uploaded_dataset.csv",
        mime="text/csv",
    )
