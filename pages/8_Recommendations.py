import pandas as pd
import streamlit as st

st.set_page_config(page_title="Recommendations", layout="wide")
st.title("Management Recommendations")

if "pipeline_result" not in st.session_state:
    st.warning("Load a dataset on the main page first.")
    st.stop()

r = st.session_state["pipeline_result"]
recs = r["recommendations"]

st.caption(
    "Recommendations are generated only from triggered, evidence-based "
    "drivers and are ranked by analytical impact, not by alert count. "
    "They are decision-support suggestions, not automated business "
    "decisions or guarantees of improved performance."
)

if not recs:
    st.success("No priority recommendations were generated \u2014 current indicators are within acceptable ranges.")
else:
    for rec in recs:
        with st.container(border=True):
            st.markdown(f"### Priority {rec.priority} — {rec.title}  \n*Category: {rec.category}*")
            st.markdown(f"**Observed issue:** {rec.observed_issue}")
            st.markdown(f"**Evidence:** {rec.evidence}")
            st.markdown(f"**Management action:** {rec.management_action}")

    st.subheader("Export Recommendations")
    df = pd.DataFrame([r.__dict__ for r in recs])
    st.download_button(
        "Download recommendations (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name="recommendations.csv",
        mime="text/csv",
    )
