"""Page 3: Threshold Simulation — adjust thresholds, toggle rules, see impact."""

import streamlit as st

from api_client import run_simulation
from charts import static_bar_chart

st.header("Threshold Simulation")
st.caption("Modify policy parameters and see the projected impact on historical deals. No data is mutated.")

# ═══════════════════════════════════════════════════════════════════════════
# Custom metric card styling for dark theme
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* Metric cards dark theme */
    [data-testid="stMetricValue"] {
        color: #FFFFFF;
        font-size: 1.5rem;
        font-weight: 700;
    }

    [data-testid="stMetricLabel"] {
        color: #F1F5F9;
        font-size: 0.875rem;
        font-weight: 500;
    }

    [data-testid="stMetricDelta"] {
        font-size: 0.875rem;
        font-weight: 500;
    }

    /* Dark background for control sections */
    .control-section {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Simulation controls
# ---------------------------------------------------------------------------
st.subheader("Adjust Thresholds")
col1, col2 = st.columns(2)

with col1:
    sim_discount = st.slider("Discount Threshold (%)", 0, 50, 20, step=1)
    sim_acv = st.number_input(
        "ACV Executive Threshold ($)", min_value=0, value=150000, step=10000
    )
with col2:
    sim_payment = st.slider("Payment Terms Limit (days)", 15, 120, 45, step=5)
    sim_eu_legal = st.checkbox("EU Requires Legal Review", value=True)

st.subheader("Toggle Rules")
rule_cols = st.columns(5)
disabled_rules = []
with rule_cols[0]:
    if not st.checkbox("Discount Threshold", value=True, key="r_disc"):
        disabled_rules.append("DISCOUNT_THRESHOLD")
with rule_cols[1]:
    if not st.checkbox("ACV Executive", value=True, key="r_acv"):
        disabled_rules.append("ACV_EXEC_THRESHOLD")
with rule_cols[2]:
    if not st.checkbox("EU Legal", value=True, key="r_eu"):
        disabled_rules.append("EU_LEGAL_REVIEW")
with rule_cols[3]:
    if not st.checkbox("Payment Terms", value=True, key="r_pay"):
        disabled_rules.append("PAYMENT_TERMS_LIMIT")
with rule_cols[4]:
    if not st.checkbox("Security Clause", value=True, key="r_sec"):
        disabled_rules.append("CUSTOM_SECURITY_CLAUSE")

# ---------------------------------------------------------------------------
# Run simulation — store results in session state
# ---------------------------------------------------------------------------
if st.button("Run Simulation", use_container_width=True, type="primary"):
    payload = {
        "defaults": {
            "discount_threshold": sim_discount,
            "acv_exec_threshold": sim_acv,
            "payment_terms_limit": sim_payment,
            "eu_requires_legal": sim_eu_legal,
        },
        "disabled_rules": disabled_rules,
    }

    with st.spinner("Simulating..."):
        try:
            st.session_state["sim_result"] = run_simulation(payload)
        except Exception as e:
            st.error(f"Simulation failed: {e}")
            st.session_state.pop("sim_result", None)

# ---------------------------------------------------------------------------
# Display results from session state
# ---------------------------------------------------------------------------
if "sim_result" not in st.session_state:
    st.info("Adjust parameters above and click **Run Simulation** to see results.")
    st.stop()

result = st.session_state["sim_result"]
orig = result["original"]
sim = result["simulated"]
delta = result["delta"]

st.markdown("---")

view_mode = st.radio(
    "Display Mode", ["Side-by-Side", "Delta Summary"], horizontal=True, key="sim_view"
)

if view_mode == "Side-by-Side":
    st.subheader("Comparison")
    col_orig, spacer, col_sim = st.columns([10, 1, 10])

    with col_orig:
        st.metric("Auto-Approved", orig["auto_approved"],
                   f"{orig['auto_approval_rate']:.0%}")
        st.metric("Escalated", orig["escalated"],
                   f"{orig['escalation_rate']:.0%}")
        if orig["escalation_by_team"]:
            static_bar_chart(orig["escalation_by_team"], "Team", "Count",
                             title="Current Config", height=260)

    with col_sim:
        st.metric("Auto-Approved", sim["auto_approved"],
                   f"{sim['auto_approval_rate']:.0%}")
        st.metric("Escalated", sim["escalated"],
                   f"{sim['escalation_rate']:.0%}")
        if sim["escalation_by_team"]:
            static_bar_chart(sim["escalation_by_team"], "Team", "Count",
                             title="Simulated Config", height=260)

else:  # Delta Summary
    st.subheader("Impact Delta")

    d_col1, d_col2, d_col3 = st.columns(3)
    d_col1.metric(
        "Auto-Approval Rate",
        f"{sim['auto_approval_rate']:.0%}",
        f"{delta['auto_approval_rate']:+.1%}",
    )
    d_col2.metric(
        "Escalation Rate",
        f"{sim['escalation_rate']:.0%}",
        f"{delta['escalation_rate']:+.1%}",
        delta_color="inverse",
    )
    d_col3.metric(
        "Escalated Deals",
        sim["escalated"],
        f"{delta['escalated']:+d}",
        delta_color="inverse",
    )

    team_deltas = delta.get("escalation_by_team", {})
    if team_deltas:
        st.subheader("Team Load Changes")
        for team, change in sorted(team_deltas.items()):
            if change != 0:
                direction = "increase" if change > 0 else "decrease"
                st.write(f"**{team}**: {change:+d} ({direction})")

with st.expander("Raw Simulation Data"):
    st.json(result)
