"""GTM Control Layer — Streamlit Dashboard Entry Point."""

import streamlit as st

st.set_page_config(
    page_title="GTM Control Layer",
    page_icon="<unicode_placeholder>",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("GTM Control Layer")
st.caption("Programmable deal policy engine — deterministic-first, AI-augmented")

with st.expander("About This Prototype", expanded=False):
    st.markdown("""
**Design Philosophy**

This prototype demonstrates how GTM operations can be modeled as programmable guardrails:

- **Deterministic-first**: All routing decisions are made by config-driven rules. No AI in the critical path.
- **AI-augmented**: Claude analyzes unstructured contract clauses as a strictly advisory layer.
- **Config-driven**: Thresholds, weights, and escalation order are externalized — change behavior without changing code.
- **Simulation-ready**: Test policy changes against historical deals before deploying them.

The system encodes business policy deterministically, uses AI only for language interpretation,
and surfaces operational metrics with threshold simulation.
""")

st.markdown("---")
st.markdown("Use the sidebar to navigate between pages.")
