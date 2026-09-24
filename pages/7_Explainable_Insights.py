import streamlit as st

st.set_page_config(page_title="Explainable Insights", layout="wide")
st.title("Explainable Insights")

if "pipeline_result" not in st.session_state:
    st.warning("Load a dataset on the main page first.")
    st.stop()

r = st.session_state["pipeline_result"]
drivers = r["drivers"]
cards = r["explanation_cards"]

st.subheader("Driver Summary")
triggered = [d for d in drivers if d.triggered]
not_triggered = [d for d in drivers if not d.triggered]

if triggered:
    for d in triggered:
        with st.container(border=True):
            st.markdown(f"### 🔴 Driver {d.code} — {d.name}")
            st.write(d.narrative)
            st.caption(f"Evidence: {d.evidence}")
else:
    st.success("No major risk drivers were triggered by the current thresholds.")

if not_triggered:
    with st.expander(f"Drivers checked but not triggered ({len(not_triggered)})"):
        for d in not_triggered:
            st.markdown(f"- **{d.code} — {d.name}**: not triggered. Evidence: `{d.evidence}`")

st.divider()
st.subheader("Finding \u2192 Evidence \u2192 Driver \u2192 Impact \u2192 Recommendation")
for c in cards:
    with st.container(border=True):
        st.markdown(f"**Finding:** {c.finding}")
        st.markdown(f"**Evidence:** {c.evidence}")
        st.markdown(f"**Driver:** {c.driver}")
        st.markdown(f"**Impact:** {c.impact}")
        st.markdown(f"**Recommendation:** {c.recommendation}")

if not cards:
    st.info("No explanation cards were generated \u2014 KPIs are currently within acceptable ranges.")
