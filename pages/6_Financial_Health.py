import plotly.graph_objects as go
import streamlit as st

from src.utils.formatting import rag_badge_md

st.set_page_config(page_title="Financial Health", layout="wide")
st.title("Financial Health Scorecard")

if "pipeline_result" not in st.session_state:
    st.warning("Load a dataset on the main page first.")
    st.stop()

r = st.session_state["pipeline_result"]
health = r["health_result"]
rag = r["rag_result"]
dq = r["dq_report"]

col1, col2 = st.columns([1, 2])
with col1:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health.total_score,
        title={"text": "Financial Health Score"},
        gauge={
            "axis": {"range": [0, 100]},
            "steps": [
                {"range": [0, 50], "color": "#f5c2c2"},
                {"range": [50, 70], "color": "#f7e3a1"},
                {"range": [70, 100], "color": "#c6e6c6"},
            ],
            "bar": {"color": "#333333"},
        },
    ))
    st.plotly_chart(fig, use_container_width=True)
with col2:
    st.markdown(f"### RAG Status: {rag_badge_md(rag.status)}", unsafe_allow_html=True)
    if rag.status != rag.score_based_status:
        st.warning(
            f"Note: the numeric score alone maps to **{rag.score_based_status}**, "
            f"but the final status is **{rag.status}** because of critical-risk "
            "override(s) triggered below."
        )
    st.markdown(f"### Data Reliability: {rag_badge_md(dq.status, dq.status)}", unsafe_allow_html=True)
    st.caption(
        "The Financial Health Score and Data Reliability are shown "
        "separately. A low-reliability dataset is a data-quality "
        "warning, not evidence that the business itself is unhealthy."
    )

if rag.triggered_overrides:
    st.subheader("Critical-Risk Overrides Triggered")
    for o in rag.triggered_overrides:
        st.error(f"**{o['rule']}** \u2014 {o['explanation']}")

st.subheader("Score Components (0\u2013100)")
for comp in health.components:
    st.markdown(f"**{comp.name}** — {comp.points:.1f} / {comp.max_points}")
    st.progress(min(comp.points / comp.max_points, 1.0) if comp.max_points else 0)
    subs = health.subcomponents.get(comp.name, [])
    if subs:
        with st.expander(f"See how {comp.name} was calculated"):
            for s in subs:
                st.markdown(f"- {s.name}: **{s.points:.1f} / {s.max_points}** — evidence: `{s.detail}`")
    st.divider()

st.subheader("Break-Even Insight")
be = r["kpis"]["breakeven"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Avg monthly revenue", f"KES {be['avg_monthly_revenue']:,.0f}")
c2.metric("Avg monthly gross profit", f"KES {be['avg_monthly_gross_profit']:,.0f}")
c3.metric("Avg monthly opex", f"KES {be['avg_monthly_opex']:,.0f}")
if be["breakeven_revenue"] == be["breakeven_revenue"]:
    c4.metric("Approx. break-even revenue", f"KES {be['breakeven_revenue']:,.0f}")
    st.info(
        f"At the current gross margin and cost structure, the business "
        f"would need approximately **{be['revenue_gap_pct']:.0f}% more monthly "
        "revenue** to reach operating break-even without changing its cost "
        "or margin structure. This is an **approximate analytical "
        "estimate**, not a forecast — revenue growth alone may not be "
        "sufficient; margin and cost structure may also need attention."
    )
else:
    c4.metric("Approx. break-even revenue", "N/A")
    st.caption("Break-even could not be estimated (gross margin is zero or negative).")

st.subheader("Inventory & Working-Capital Reliability")
inv_status = r["kpis"]["inventory_status"]
if inv_status["usable_for_scoring"]:
    st.success("Inventory is usable for scoring.")
    turnover = r["kpis"]["inventory_turnover"]
    if turnover:
        st.metric("Inventory Turnover (COGS / Avg Inventory Value)", f"{turnover['turnover_ratio']:.2f}x")
        st.caption(
            f"Average inventory value \u2248 KES {turnover['average_inventory_value']:,.0f} "
            f"(opening \u2248 KES {turnover['opening_inventory_value']:,.0f}, "
            f"ending \u2248 KES {turnover['ending_inventory_value']:,.0f})."
        )
else:
    st.error(inv_status["message"])
    st.caption(
        "For a future clean dataset with reliable opening and closing "
        "stock, Inventory Turnover = COGS / Average Inventory can be "
        "added directly."
    )

with st.expander("Metric Definitions"):
    st.markdown(
        """
- **Gross Margin** = Gross Profit / Adjusted Revenue. Source: `net_sales_kes`, `cogs_kes`, `transaction_type`. Excludes invalid sales, duplicate transaction IDs, invalid quantity records.
- **Operating Margin** = Operating Profit / Adjusted Revenue. Source: `expense_amount_kes` (EXPENSE rows only).
- **Collection Coverage** = (Amount received at sale + subsequent customer payments) / Credit-like sales value. Estimate only — no invoice-aging data available.
- **Break-even Revenue** = Average Monthly Operating Expenses / Gross Margin. Approximate analytical estimate.
- **Data Reliability Score** = weighted composite of duplicate, missing-value, invalid-date, invalid-quantity, category-consistency, payment-label-consistency and financial-consistency checks, capped when inventory integrity fails.
        """
    )
