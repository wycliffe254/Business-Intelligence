import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Product & Category Analysis", layout="wide")
st.title("Product & Category Analysis")

if "pipeline_result" not in st.session_state:
    st.warning("Load a dataset on the main page first.")
    st.stop()

r = st.session_state["pipeline_result"]
kpis = r["kpis"]
cat = kpis["product_category"]
prod = kpis["product"]

st.caption(
    "Quadrants use neutral analytical language. A low-revenue or "
    "low-margin category is not automatically described as a 'bad' "
    "product \u2014 it simply indicates where investigation may be useful."
)

st.subheader("Category Performance")
fig = px.scatter(
    cat, x="revenue_share_pct", y="gross_margin_pct", size="adjusted_revenue",
    color="quadrant", hover_name="product_category",
    labels={"revenue_share_pct": "Revenue Share (%)", "gross_margin_pct": "Gross Margin (%)"},
)
st.plotly_chart(fig, use_container_width=True)

st.dataframe(
    cat[["product_category", "adjusted_revenue", "units_sold", "cogs", "gross_profit",
         "gross_margin_pct", "revenue_share_pct", "discount_rate_pct", "refund_rate_pct", "quadrant"]],
    use_container_width=True, hide_index=True,
)

high_rev_low_margin = cat[cat["quadrant"] == "High revenue / Low margin"]
if not high_rev_low_margin.empty:
    names = ", ".join(high_rev_low_margin["product_category"].tolist())
    st.warning(
        f"**{names}** contribute a substantial share of sales but produce "
        "relatively weak gross margins, making margin improvement in "
        "these categories potentially important to overall profitability."
    )

st.subheader("Product-Level Detail")
st.dataframe(
    prod[["product_name", "adjusted_revenue", "units_sold", "gross_profit", "gross_margin_pct",
          "revenue_share_pct", "discount_rate_pct", "refund_rate_pct"]].head(50),
    use_container_width=True, hide_index=True,
)
