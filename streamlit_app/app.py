"""GTM Control Layer — Streamlit Dashboard Entry Point."""

import streamlit as st

st.set_page_config(
    page_title="GTM Control Layer",
    page_icon="<unicode_placeholder>",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════
# Global CSS — Deep Ocean Design System
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* Import Fira Sans font family */
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');

    /* Root color variables — Deep Ocean palette (Dark Theme) */
    :root {
        --primary-blue: #3B82F6;
        --secondary-slate: #334155;
        --accent-amber: #F59E0B;
        --success-green: #10B981;
        --danger-red: #EF4444;
        --bg-dark: #0F172A;
        --bg-card: #1E293B;
        --text-light: #F1F5F9;
        --text-muted: #94A3B8;
        --border-slate: #334155;
    }

    /* Global typography */
    html, body, [class*="css"] {
        font-family: 'Fira Sans', sans-serif;
        color: var(--text-light);
    }

    /* Main content background - Dark theme */
    .main {
        background-color: var(--bg-dark);
    }

    /* Headers - Light text for dark theme */
    h1, h2, h3 {
        color: var(--text-light) !important;
        font-weight: 600 !important;
    }

    h1 {
        font-size: 2rem !important;
    }

    h2 {
        font-size: 1.5rem !important;
    }

    h3 {
        font-size: 1.25rem !important;
    }

    /* Buttons - Bright blue accent */
    .stButton>button {
        background-color: var(--primary-blue);
        color: white;
        border: none;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .stButton>button:hover {
        background-color: #2563EB;
        transform: translateY(-1px);
    }

    /* Dataframe styling */
    .stDataFrame {
        font-family: 'Fira Code', monospace;
        font-size: 0.9rem;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        color: var(--text-muted);
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        color: var(--accent-amber);
        border-bottom-color: var(--accent-amber);
    }

    /* Input fields dark theme */
    input, textarea, select {
        background-color: var(--bg-card) !important;
        color: var(--text-light) !important;
        border: 1px solid var(--border-slate) !important;
    }

    /* Expander dark theme */
    .streamlit-expanderHeader {
        background-color: var(--bg-card);
        color: var(--text-light);
    }

    /* Progress bar */
    .stProgress > div > div {
        background-color: var(--accent-amber);
    }

    /* Labels */
    label {
        color: var(--text-light) !important;
    }

    /* Caption text */
    .stCaption {
        color: var(--text-muted) !important;
    }

    /* Divider */
    hr {
        border-color: var(--border-slate);
    }

    /* Sidebar dark theme */
    [data-testid="stSidebar"] {
        background-color: var(--bg-card);
    }
</style>
""", unsafe_allow_html=True)

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
