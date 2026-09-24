import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Branch & Channel Analysis", layout="wide")
st.title("Branch & Channel Analysis")

if "pipeline_result" not in st.session_state:
    st.warning("Load a dataset on the main page first.")
    st.stop()

r = st.session_state["pipeline_result"]
kpis = r["kpis"]
branch = kpis["branch"]
channel = kpis["channel"]

st.subheader("Branch Performance")
c1, c2 = st.columns(2)
with c1:
    fig = px.bar(branch, x="branch", y="adjusted_revenue", title="Revenue by Branch")
    st.plotly_chart(fig, use_container_width=True)
with c2:
    fig2 = px.bar(branch, x="branch", y="gross_margin_pct", title="Gross Margin by Branch")
    st.plotly_chart(fig2, use_container_width=True)

st.dataframe(
    branch[["branch", "adjusted_revenue", "transactions", "avg_transaction_value", "gross_margin_pct",
            "revenue_share_pct"]],
    use_container_width=True, hide_index=True,
)

if len(branch) >= 2:
    top_rev = branch.iloc[0]
    top_margin = branch.sort_values("gross_margin_pct", ascending=False).iloc[0]
    if top_rev["branch"] != top_margin["branch"]:
        st.info(
            f"**{top_rev['branch']}** generates the highest revenue, but "
            f"**{top_margin['branch']}** produces the highest gross margin. "
            "Higher revenue does not automatically mean higher profitability."
        )

st.subheader("Sales Channel Performance")
c3, c4 = st.columns(2)
with c3:
    fig3 = px.bar(channel, x="sales_channel", y="adjusted_revenue", title="Revenue by Sales Channel")
    st.plotly_chart(fig3, use_container_width=True)
with c4:
    fig4 = px.bar(channel, x="sales_channel", y="gross_margin_pct", title="Gross Margin by Sales Channel")
    st.plotly_chart(fig4, use_container_width=True)

st.dataframe(
    channel[["sales_channel", "adjusted_revenue", "transactions", "avg_transaction_value", "gross_margin_pct"]],
    use_container_width=True, hide_index=True,
)
