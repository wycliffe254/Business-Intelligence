import plotly.graph_objects as go
import streamlit as st

from src.analytics.kpis import compute_all_kpis
from src.utils.formatting import kes, pct

st.set_page_config(page_title="Financial Performance", layout="wide")
st.title("Financial Performance")

if "pipeline_result" not in st.session_state:
    st.warning("Load a dataset on the main page first.")
    st.stop()

r = st.session_state["pipeline_result"]
df = r["analytical_df"]

st.sidebar.header("Filters")
included = df[df["include_in_kpis"]]
branches = sorted(included["branch_norm"].dropna().unique().tolist())
categories = sorted(included["product_category_norm"].dropna().unique().tolist())
customer_types = sorted(included["customer_type_norm"].dropna().unique().tolist())
channels = sorted(included["sales_channel_norm"].dropna().unique().tolist())

sel_branch = st.sidebar.multiselect("Branch", branches, default=branches)
sel_cat = st.sidebar.multiselect("Product category", categories, default=categories)
sel_cust = st.sidebar.multiselect("Customer type", customer_types, default=customer_types)
sel_chan = st.sidebar.multiselect("Sales channel", channels, default=channels)

def _apply_filters(frame):
    mask = frame["_row_id"].notna()
    if sel_branch:
        mask &= frame["branch_norm"].isin(sel_branch) | frame["branch_norm"].isna()
    if sel_cat:
        mask &= frame["product_category_norm"].isin(sel_cat) | frame["product_category_norm"].isna()
    if sel_cust:
        mask &= frame["customer_type_norm"].isin(sel_cust) | frame["customer_type_norm"].isna()
    if sel_chan:
        mask &= frame["sales_channel_norm"].isin(sel_chan) | frame["sales_channel_norm"].isna()
    return frame[mask]

filtered = _apply_filters(df)
kpis = compute_all_kpis(filtered) if len(filtered) else r["kpis"]
core = kpis["core"]
monthly = kpis["monthly"]

st.caption("Filters apply to this page's charts and tables only.")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Adjusted Revenue", kes(core["adjusted_revenue"], millions=True))
c2.metric("Gross Profit", kes(core["gross_profit"], millions=True))
c3.metric("Gross Margin", pct(core["gross_margin_pct"]))
c4.metric("Operating Profit", kes(core["operating_profit"], millions=True))
c5.metric("Operating Margin", pct(core["operating_margin_pct"]))

st.subheader("Revenue, Gross Profit & Operating Profit Trend")
fig = go.Figure()
fig.add_trace(go.Scatter(x=monthly["month_str"], y=monthly["revenue"], name="Revenue", mode="lines+markers"))
fig.add_trace(go.Scatter(x=monthly["month_str"], y=monthly["gross_profit"], name="Gross Profit", mode="lines+markers"))
fig.add_trace(go.Scatter(x=monthly["month_str"], y=monthly["operating_profit"], name="Operating Profit", mode="lines+markers"))
fig.update_layout(xaxis_title="Month", yaxis_title="KES", legend_title="")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Gross Margin Trend")
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=monthly["month_str"], y=monthly["gross_margin_pct"], mode="lines+markers"))
fig2.update_layout(xaxis_title="Month", yaxis_title="Gross Margin %")
st.plotly_chart(fig2, use_container_width=True)

st.subheader("Revenue vs Operating Expenses")
fig3 = go.Figure()
fig3.add_trace(go.Bar(x=monthly["month_str"], y=monthly["revenue"], name="Revenue"))
fig3.add_trace(go.Bar(x=monthly["month_str"], y=monthly["operating_expenses"], name="Operating Expenses"))
fig3.update_layout(barmode="group", xaxis_title="Month", yaxis_title="KES")
st.plotly_chart(fig3, use_container_width=True)

st.subheader("Expense Composition")
exp_bd = kpis["expense_breakdown"]
if not exp_bd.empty:
    fig4 = go.Figure(go.Bar(x=exp_bd["expense_category"], y=exp_bd["amount_kes"]))
    fig4.update_layout(xaxis_title="Category", yaxis_title="KES")
    st.plotly_chart(fig4, use_container_width=True)
    st.dataframe(exp_bd, use_container_width=True, hide_index=True)
else:
    st.info("No expense records in the current filter selection.")

st.subheader("Comparable-Period Analysis (Jan\u2013Aug, year-on-year)")
comp = kpis["comparable_yoy"]
if comp.get("sufficient_data"):
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric(f"Revenue {comp['prior_year']}", kes(comp["prior_period_revenue"], millions=True))
    cc2.metric(f"Revenue {comp['latest_year']}", kes(comp["latest_period_revenue"], millions=True),
               delta=f"{comp['revenue_change_pct']:.1f}%")
    cc3.metric("Gross Margin Change", f"{comp['margin_change_pp']:.1f} pp")
else:
    st.info(comp.get("message", "Insufficient historical data for this analysis."))

st.subheader("Recent Trend (latest 3 months vs preceding 3 months)")
recent = kpis["recent_trend"]
if recent.get("sufficient_data"):
    st.metric("Revenue change", f"{recent['change_pct']:.1f}%",
              delta=kes(recent["recent_period_revenue"] - recent["preceding_period_revenue"]))
else:
    st.info(recent.get("message", "Insufficient historical data for this analysis."))
