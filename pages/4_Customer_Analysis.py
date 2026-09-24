import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Customer Analysis", layout="wide")
st.title("Customer Analysis")

if "pipeline_result" not in st.session_state:
    st.warning("Load a dataset on the main page first.")
    st.stop()

r = st.session_state["pipeline_result"]
kpis = r["kpis"]
cust = kpis["customer_type"]

st.caption(
    "The largest customer segment by revenue is not necessarily the most "
    "profitable one \u2014 compare revenue share against gross margin below."
)

c1, c2 = st.columns(2)
with c1:
    fig = px.bar(cust, x="customer_type", y="adjusted_revenue", title="Revenue by Customer Type")
    st.plotly_chart(fig, use_container_width=True)
with c2:
    fig2 = px.bar(cust, x="customer_type", y="gross_margin_pct", title="Gross Margin by Customer Type")
    st.plotly_chart(fig2, use_container_width=True)

st.dataframe(
    cust[["customer_type", "adjusted_revenue", "transactions", "avg_transaction_value",
          "gross_margin_pct", "revenue_share_pct", "discount_rate_pct", "refund_rate_pct"]],
    use_container_width=True, hide_index=True,
)

st.subheader("Credit / Collection Signal (portfolio-level estimate)")
collections = kpis["collections"]
c1, c2, c3 = st.columns(3)
c1.metric("Credit-like sales value", f"KES {collections['credit_sales_value']:,.0f}")
c2.metric("Collection coverage", f"{collections['collection_coverage_pct']:.1f}%")
c3.metric("Estimated uncollected exposure", f"KES {collections['estimated_uncollected_exposure']:,.0f}")
st.caption(collections["note"])
