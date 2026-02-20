"""Page 4: Admin — Override management, config viewer, override history."""

import json

import pandas as pd
import streamlit as st

from api_client import get_metrics, list_deals, override_deal
from charts import static_bar_chart

st.header("Admin")

# ═══════════════════════════════════════════════════════════════════════════
# Custom styling for dark theme consistency
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* Form section styling for dark theme */
    [data-testid="stForm"] {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1.5rem;
    }

    /* Expander styling for dark theme */
    [data-testid="stExpander"] {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 6px;
    }

    /* Input fields dark theme */
    input, textarea, select {
        background-color: #0F172A !important;
        color: #F1F5F9 !important;
        border-color: #334155 !important;
    }

    /* JSON viewer dark theme */
    pre {
        background-color: #0F172A !important;
        border: 1px solid #334155;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

tab_override, tab_history, tab_config = st.tabs(
    ["Apply Override", "Override History", "Config Viewer"]
)

OVERRIDE_REASONS = [
    "Strategic deal",
    "Pre-approved by VP",
    "Customer relationship",
    "Competitive pressure",
    "One-time exception",
    "Other",
]

# ---------------------------------------------------------------------------
# Tab 1: Apply override
# ---------------------------------------------------------------------------
with tab_override:
    st.subheader("Override Escalated Deal")

    try:
        deals_resp = list_deals()
        all_deals = deals_resp.get("deals", [])
    except Exception as e:
        st.error(f"Could not load deals: {e}")
        all_deals = []

    # Filter to escalated deals only
    escalated_deals = [
        d for d in all_deals
        if d.get("decision_json")
        and not d["decision_json"].get("auto_approved")
        and d.get("status") == "processed"
    ]

    if not escalated_deals:
        st.info("No escalated deals available for override.")
    else:
        deal_options = {
            f"{d['id'][:8]}... | {d['customer_segment']} | ${d['annual_contract_value']:,.0f} | {d['decision_json'].get('priority', 'N/A')}": d["id"]
            for d in escalated_deals
        }
        selected_label = st.selectbox("Select escalated deal", list(deal_options.keys()))
        selected_deal_id = deal_options[selected_label]

        # Show deal details
        selected_deal = next(d for d in escalated_deals if d["id"] == selected_deal_id)
        with st.expander("Deal Details"):
            dec = selected_deal.get("decision_json", {})
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Escalation Path:** {', '.join(dec.get('escalation_path', []))}")
            col2.write(f"**Priority:** {dec.get('priority', 'N/A')}")
            col3.write(f"**Weight:** {dec.get('total_weight', 0)}")
            st.json(dec)

        with st.form("override_form"):
            reason = st.selectbox("Override Reason", OVERRIDE_REASONS)
            notes = st.text_area("Additional Notes (optional)")
            overrider = st.text_input("Overridden By", value="approver")
            submitted = st.form_submit_button("Apply Override", use_container_width=True)

        if submitted:
            try:
                result = override_deal(
                    deal_id=selected_deal_id,
                    reason=reason,
                    notes=notes if notes.strip() else None,
                    overridden_by=overrider,
                )
                st.success(f"Override applied. Override ID: {result['override_id']}")
            except Exception as e:
                st.error(f"Override failed: {e}")

# ---------------------------------------------------------------------------
# Tab 2: Override history
# ---------------------------------------------------------------------------
with tab_history:
    st.subheader("Override History")

    try:
        metrics = get_metrics()
    except Exception:
        metrics = {}

    override_by_reason = metrics.get("override_by_reason", {})
    override_by_team = metrics.get("override_by_team", {})

    if override_by_reason:
        mcol1, mcol2 = st.columns(2)
        with mcol1:
            st.markdown("**Overrides by Reason**")
            static_bar_chart(override_by_reason, "Reason", "Count")
        with mcol2:
            st.markdown("**Overrides by Team**")
            if override_by_team:
                static_bar_chart(override_by_team, "Team", "Count")

    # Overridden deals list
    overridden_deals = [d for d in all_deals if d.get("status") == "overridden"]
    if overridden_deals:
        st.markdown(f"**{len(overridden_deals)} overridden deals**")
        for d in overridden_deals:
            with st.expander(f"Deal {d['id'][:8]}... | {d['customer_segment']} | ${d['annual_contract_value']:,.0f}"):
                st.json(d)
    else:
        st.info("No overrides recorded yet.")

# ---------------------------------------------------------------------------
# Tab 3: Config viewer
# ---------------------------------------------------------------------------
with tab_config:
    st.subheader("Current Rules Configuration")
    try:
        import pathlib
        config_path = pathlib.Path(__file__).resolve().parent.parent.parent / "config" / "rules.json"
        if config_path.exists():
            with open(config_path) as f:
                config_data = json.load(f)
            st.json(config_data)
        else:
            st.warning("Config file not found.")
    except Exception as e:
        st.error(f"Error loading config: {e}")
