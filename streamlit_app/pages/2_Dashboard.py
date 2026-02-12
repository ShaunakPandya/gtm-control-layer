"""Page 2: Dashboard — KPI summary above the fold, deal log below."""

import pandas as pd
import streamlit as st

from api_client import get_metrics, list_deals
from charts import static_bar_chart

st.header("Dashboard")

# ═══════════════════════════════════════════════════════════════════════════
# ABOVE THE FOLD — KPI metrics + visual summaries
# ═══════════════════════════════════════════════════════════════════════════

try:
    metrics = get_metrics()
except Exception as e:
    st.error(f"Could not load metrics: {e}")
    st.info("Start the API server and seed some data first.")
    st.stop()

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
st.markdown("<div style='margin-bottom: 0.5rem'></div>", unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Total Deals", metrics["total_deals"])
kpi2.metric("Auto-Approved", metrics["auto_approved"],
            f"{metrics['auto_approval_rate']:.0%}")
kpi3.metric("Escalated", metrics["escalated"],
            f"{metrics['escalation_rate']:.0%}")
kpi4.metric("Overridden", metrics["overridden"])
kpi5.metric("Override Rate", f"{metrics['override_rate']:.1%}")

st.markdown("<div style='margin: 1.2rem 0 0.4rem'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Side-by-side vertical bar charts
# ---------------------------------------------------------------------------
chart_col1, chart_spacer, chart_col2 = st.columns([10, 1, 10])

with chart_col1:
    esc_data = metrics.get("escalation_by_team", {})
    if esc_data:
        static_bar_chart(esc_data, "Team", "Count", title="Escalation by Team")
    else:
        st.info("No escalations yet.")

with chart_col2:
    trigger_data = metrics.get("top_rule_triggers", [])
    if trigger_data:
        static_bar_chart(trigger_data, "Rule", "Count", title="Top Rule Triggers")
    else:
        st.info("No rule triggers yet.")


# ═══════════════════════════════════════════════════════════════════════════
# BELOW THE FOLD — Deal log (separated by whitespace + divider)
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("<div style='margin: 2.5rem 0 0'></div>", unsafe_allow_html=True)
st.divider()
st.subheader("Deal Log")

try:
    deals_resp = list_deals()
    deals = deals_resp.get("deals", [])
except Exception as e:
    st.error(f"Could not load deals: {e}")
    deals = []

if not deals:
    st.info("No deals in database. Submit or generate some deals first.")
    st.stop()

# Build DataFrame for filtering
df = pd.DataFrame(deals)
display_cols = [
    "id", "deal_type", "customer_segment", "region",
    "annual_contract_value", "discount_percentage", "payment_terms_days",
    "custom_security_clause", "status",
]
existing_cols = [c for c in display_cols if c in df.columns]
df_display = df[existing_cols].copy()

# Filters
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
with filter_col1:
    status_filter = st.multiselect(
        "Status", options=df_display["status"].unique().tolist(),
        default=df_display["status"].unique().tolist(),
    )
with filter_col2:
    segment_filter = st.multiselect(
        "Segment", options=df_display["customer_segment"].unique().tolist(),
        default=df_display["customer_segment"].unique().tolist(),
    )
with filter_col3:
    region_filter = st.multiselect(
        "Region", options=df_display["region"].unique().tolist(),
        default=df_display["region"].unique().tolist(),
    )
with filter_col4:
    deal_type_filter = st.multiselect(
        "Deal Type", options=df_display["deal_type"].unique().tolist(),
        default=df_display["deal_type"].unique().tolist(),
    )

# Apply filters
mask = (
    df_display["status"].isin(status_filter)
    & df_display["customer_segment"].isin(segment_filter)
    & df_display["region"].isin(region_filter)
    & df_display["deal_type"].isin(deal_type_filter)
)
filtered = df_display[mask]

st.dataframe(filtered, use_container_width=True, hide_index=True)
st.caption(f"Showing {len(filtered)} of {len(df_display)} deals")

# ---------------------------------------------------------------------------
# Detail expansion
# ---------------------------------------------------------------------------
st.markdown("<div style='margin-top: 1rem'></div>", unsafe_allow_html=True)
st.subheader("Deal Detail")
deal_ids = filtered["id"].tolist()
if deal_ids:
    selected_id = st.selectbox("Select a deal to inspect", deal_ids)
    if selected_id:
        deal_row = next((d for d in deals if d["id"] == selected_id), None)
        if deal_row:
            detail_tabs = st.tabs(["Decision", "Evaluation", "Advisory", "Raw"])
            with detail_tabs[0]:
                dec = deal_row.get("decision_json")
                if dec:
                    st.json(dec)
                else:
                    st.info("No decision recorded.")
            with detail_tabs[1]:
                ev = deal_row.get("evaluation_json")
                if ev:
                    st.json(ev)
                else:
                    st.info("No evaluation recorded.")
            with detail_tabs[2]:
                adv = deal_row.get("advisory_json")
                if adv:
                    st.json(adv)
                else:
                    st.info("No advisory (no clause text provided).")
            with detail_tabs[3]:
                st.json(deal_row)
