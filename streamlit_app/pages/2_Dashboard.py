"""Page 2: Dashboard — KPI summary above the fold, deal log below."""

import pandas as pd
import streamlit as st

from api_client import get_metrics, list_deals
from charts import static_bar_chart

st.header("Dashboard")

# ═══════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════

def format_rule_name(rule_code: str) -> str:
    """Convert rule code to human-readable name."""
    rule_mapping = {
        "DISCOUNT_THRESHOLD": "Discount Limit",
        "ACV_EXEC_THRESHOLD": "ACV Exec Threshold",
        "EU_LEGAL_REVIEW": "EU Legal Review",
        "PAYMENT_TERMS_LIMIT": "Payment Terms",
        "CUSTOM_SECURITY_CLAUSE": "Security Clause"
    }
    return rule_mapping.get(rule_code, rule_code)

# ═══════════════════════════════════════════════════════════════════════════
# Custom KPI Card Styling
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    .kpi-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1.25rem 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
        transition: all 0.2s ease;
        text-align: center;
        /* Force equal sizing */
        min-height: 120px;
        max-height: 120px;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }

    .kpi-card:hover {
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4);
        transform: translateY(-2px);
    }

    .kpi-label {
        font-size: 0.75rem;
        font-weight: 500;
        color: #F1F5F9;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
        width: 100%;
        text-align: center;
        line-height: 1.2;
    }

    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: #FFFFFF;
        font-family: 'Fira Code', monospace;
        margin-bottom: 0.25rem;
        line-height: 1;
    }

    .kpi-delta {
        font-size: 0.875rem;
        font-weight: 500;
        margin-top: 0.25rem;
        line-height: 1;
    }

    .kpi-delta.positive {
        color: #10B981;
    }

    .kpi-delta.negative {
        color: #EF4444;
    }

    .kpi-delta.neutral {
        color: #94A3B8;
    }
</style>
""", unsafe_allow_html=True)

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
# KPI row — Custom styled cards
# ---------------------------------------------------------------------------
st.markdown("<div style='margin-bottom: 1rem'></div>", unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Deals</div>
            <div class="kpi-value">{metrics["total_deals"]}</div>
        </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Auto-Approved</div>
            <div class="kpi-value">{metrics["auto_approved"]}</div>
            <div class="kpi-delta positive">{metrics['auto_approval_rate']:.0%}</div>
        </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Escalated</div>
            <div class="kpi-value">{metrics["escalated"]}</div>
            <div class="kpi-delta negative">{metrics['escalation_rate']:.0%}</div>
        </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Overridden</div>
            <div class="kpi-value">{metrics["overridden"]}</div>
        </div>
    """, unsafe_allow_html=True)

with kpi5:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Override Rate</div>
            <div class="kpi-value">{metrics['override_rate']:.1f}%</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin: 1.5rem 0 1rem'></div>", unsafe_allow_html=True)

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
        # Build label mapping for chart display
        rule_label_map = {
            "DISCOUNT_THRESHOLD": "Discount Limit",
            "ACV_EXEC_THRESHOLD": "ACV Exec Threshold",
            "EU_LEGAL_REVIEW": "EU Legal Review",
            "PAYMENT_TERMS_LIMIT": "Payment Terms",
            "CUSTOM_SECURITY_CLAUSE": "Security Clause"
        }
        static_bar_chart(
            trigger_data,
            "Rule",
            "Count",
            title="Top Rule Triggers",
            label_mapping=rule_label_map
        )
    else:
        st.info("No rule triggers yet.")


# ═══════════════════════════════════════════════════════════════════════════
# PENDING REVIEW QUEUE
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("<div style='margin: 2.5rem 0 1rem'></div>", unsafe_allow_html=True)
st.divider()

# Section header with amber left border
st.markdown("""
<div style='border-left: 4px solid #F59E0B; padding-left: 1rem; margin-bottom: 1rem;'>
    <h3 style='margin: 0; color: #F1F5F9;'>Pending Review</h3>
</div>
""", unsafe_allow_html=True)

try:
    deals_resp = list_deals()
    deals = deals_resp.get("deals", [])
except Exception as e:
    st.error(f"Could not load deals: {e}")
    deals = []

# Filter for escalated deals that haven't been overridden
pending_deals = [
    d for d in deals
    if d.get("status") == "processed"
    and d.get("decision_json", {}).get("auto_approved") == False
]

if not pending_deals:
    st.markdown("""
    <div style='background: #1E293B; border: 1px solid #10B981; border-radius: 6px; padding: 1rem; text-align: center;'>
        <span style='color: #10B981; font-weight: 600;'>✓ All caught up — no deals pending review</span>
    </div>
    """, unsafe_allow_html=True)
else:
    # Build compact pending review table
    pending_data = []
    for d in pending_deals:
        decision = d.get("decision_json", {})
        pending_data.append({
            "Deal #": f"#{d['id'][:8].upper()}",
            "Segment": d.get("customer_segment", "—"),
            "ACV": f"${d.get('annual_contract_value', 0):,.0f}",
            "Priority": decision.get("priority", "—"),
            "Escalation Path": " → ".join(decision.get("escalation_path", [])),
        })

    pending_df = pd.DataFrame(pending_data)

    st.dataframe(
        pending_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Deal #": st.column_config.TextColumn("Deal #", width="small"),
            "Segment": st.column_config.TextColumn("Segment", width="small"),
            "ACV": st.column_config.TextColumn("ACV", width="small"),
            "Priority": st.column_config.TextColumn("Priority", width="small"),
            "Escalation Path": st.column_config.TextColumn("Escalation Path", width="large"),
        }
    )

    st.markdown(f"""
    <div style='margin-top: 0.5rem; text-align: right;'>
        <a href="/Admin" style='color: #F59E0B; text-decoration: none; font-weight: 500;'>
            Review in Admin →
        </a>
    </div>
    """, unsafe_allow_html=True)

    st.caption(f"{len(pending_deals)} deal(s) pending review")

# ═══════════════════════════════════════════════════════════════════════════
# DEAL LOG
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("<div style='margin: 2rem 0 1rem'></div>", unsafe_allow_html=True)
st.divider()
st.subheader("Deal Log")

if not deals:
    st.info("No deals in database. Submit or generate some deals first.")
    st.stop()

# Build DataFrame for filtering
df = pd.DataFrame(deals)

# Extract deal number from UUID (first 8 chars for readability)
df["Deal #"] = df["id"].apply(lambda x: f"#{x[:8].upper()}")

# Format status with visual indicators
def format_status(status):
    """Add visual indicator to status."""
    if status == "Auto-Approved":
        return "✓ Auto-Approved"
    elif status == "Escalated":
        return "⚠ Escalated"
    elif status == "Overridden":
        return "↻ Overridden"
    return status

df["Status Badge"] = df["status"].apply(format_status)

# Extract AI risk level from advisory_json if available
def extract_risk_level(advisory_json):
    """Extract and format risk level from advisory JSON."""
    if not advisory_json or not isinstance(advisory_json, dict):
        return "—"
    risk = advisory_json.get("risk_level", None)
    if not risk:
        return "—"
    # Add visual indicators for risk levels using colored emoji circles
    if risk == "low":
        return "🟢 Low"
    elif risk == "medium":
        return "🟡 Medium"
    elif risk == "high":
        return "🔴 High"
    return risk.capitalize()

df["AI Risk"] = df.get("advisory_json", pd.Series([None] * len(df))).apply(extract_risk_level)

# Extract triggered rules and format them nicely
def format_triggered_rules(evaluation_json):
    """Extract and format triggered rule names using global mapping."""
    if not evaluation_json or not isinstance(evaluation_json, dict):
        return "—"
    triggers = evaluation_json.get("triggered_rules", [])
    if not triggers:
        return "—"
    # Convert rule codes to readable names using helper function
    readable = [format_rule_name(r) for r in triggers]
    return ", ".join(readable[:3]) + ("..." if len(readable) > 3 else "")

df["Triggered Rules"] = df.get("evaluation_json", pd.Series([None] * len(df))).apply(format_triggered_rules)

display_cols = [
    "Deal #", "deal_type", "customer_segment", "region",
    "annual_contract_value", "discount_percentage", "payment_terms_days",
    "Status Badge", "Triggered Rules", "AI Risk"
]
existing_cols = [c for c in display_cols if c in df.columns]
df_display = df[existing_cols].copy()

# Filters
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
with filter_col1:
    status_filter = st.multiselect(
        "Status", options=df["status"].unique().tolist(),
        default=df["status"].unique().tolist(),
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

# Status legend
st.markdown("""
<div style='margin: 0.5rem 0; padding: 0.75rem; background: #1E293B; border-radius: 6px; border: 1px solid #334155; font-size: 0.85rem;'>
    <span style='color: #10B981; margin-right: 1rem;'><strong>✓</strong> Auto-Approved</span>
    <span style='color: #F59E0B; margin-right: 1rem;'><strong>⚠</strong> Escalated</span>
    <span style='color: #94A3B8; margin-right: 1rem;'><strong>↻</strong> Overridden</span>
    <span style='color: #E2E8F0; margin-left: 1.5rem;'><strong>AI Risk:</strong></span>
    <span style='margin-right: 0.5rem;'>🟢 Low</span>
    <span style='margin-right: 0.5rem;'>🟡 Medium</span>
    <span>🔴 High</span>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 0.75rem'></div>", unsafe_allow_html=True)

# Apply filters (using original 'status' column for filtering)
mask = (
    df["status"].isin(status_filter)
    & df_display["customer_segment"].isin(segment_filter)
    & df_display["region"].isin(region_filter)
    & df_display["deal_type"].isin(deal_type_filter)
)
filtered = df_display[mask]

# Column configuration for styled display
column_config = {
    "Deal #": st.column_config.TextColumn(
        "Deal #",
        width="small",
    ),
    "Status Badge": st.column_config.TextColumn(
        "Status",
        width="medium",
    ),
    "annual_contract_value": st.column_config.NumberColumn(
        "ACV",
        format="$%d",
        width="medium",
    ),
    "discount_percentage": st.column_config.NumberColumn(
        "Discount",
        format="%.0f%%",
        width="small",
    ),
    "payment_terms_days": st.column_config.NumberColumn(
        "Payment Days",
        format="%d",
        width="small",
    ),
    "Triggered Rules": st.column_config.TextColumn(
        "Triggered Rules",
        width="large",
    ),
    "AI Risk": st.column_config.TextColumn(
        "AI Risk",
        width="small",
    ),
}

st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True,
    column_config=column_config,
)

# Add custom CSS for status badges in the dataframe
st.markdown("""
<style>
    /* Make dataframe rows hoverable */
    .stDataFrame [data-testid="stDataFrameResizable"] tbody tr:hover {
        background-color: rgba(30, 64, 175, 0.05) !important;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

st.caption(f"Showing {len(filtered)} of {len(df_display)} deals")

# ---------------------------------------------------------------------------
# Detail expansion
# ---------------------------------------------------------------------------
st.markdown("<div style='margin-top: 1.5rem'></div>", unsafe_allow_html=True)
st.subheader("Deal Detail")

# Build a mapping of "Deal #" to original ID for selection
if len(filtered) > 0:
    deal_display_map = dict(zip(
        df.loc[filtered.index, "Deal #"],
        df.loc[filtered.index, "id"]
    ))
    deal_options = list(deal_display_map.keys())

    selected_deal_num = st.selectbox("Select a deal to inspect", deal_options)
    if selected_deal_num:
        selected_id = deal_display_map[selected_deal_num]
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
                    # Show formatted evaluation first
                    triggered = ev.get("triggered_rules", [])
                    if triggered:
                        st.markdown("**Triggered Rules:**")
                        for rule in triggered:
                            st.markdown(f"- {format_rule_name(rule)}")
                    else:
                        st.markdown("**No rules triggered**")

                    st.markdown("<div style='margin-top: 1rem'></div>", unsafe_allow_html=True)
                    with st.expander("Raw Evaluation JSON"):
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
else:
    st.info("No deals match the current filters.")
