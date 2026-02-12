"""Page 1: Submit Deal — form, CSV upload, sample data generator."""

import csv
import io
import json

import streamlit as st

from api_client import seed_deals, reset_and_seed, submit_deal

st.header("Submit Deal")

tab_form, tab_csv, tab_generate = st.tabs(["Single Deal", "CSV Upload", "Generate Sample Data"])

# ---------------------------------------------------------------------------
# Tab 1: Single deal form
# ---------------------------------------------------------------------------
with tab_form:
    with st.form("deal_form"):
        col1, col2 = st.columns(2)
        with col1:
            deal_type = st.selectbox("Deal Type", ["New", "Renewal", "Expansion", "Pilot"])
            customer_segment = st.selectbox(
                "Customer Segment", ["Enterprise", "Mid-Market", "SMB", "Strategic"]
            )
            region = st.selectbox("Region", ["NA", "EU", "UK", "APAC", "LATAM", "MEA"])
            custom_security = st.checkbox("Custom Security Clause")
        with col2:
            acv = st.number_input("Annual Contract Value ($)", min_value=1.0, value=100000.0, step=1000.0)
            discount = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, value=15.0, step=0.5)
            payment_days = st.number_input("Payment Terms (days)", min_value=1, value=30, step=1)

        clause_text = st.text_area("Clause Text (optional)", placeholder="Enter contract clause for AI analysis...")
        submitted = st.form_submit_button("Submit Deal", use_container_width=True)

    if submitted:
        payload = {
            "deal_type": deal_type,
            "customer_segment": customer_segment,
            "annual_contract_value": acv,
            "discount_percentage": discount,
            "payment_terms_days": payment_days,
            "region": region,
            "custom_security_clause": custom_security,
        }
        if clause_text.strip():
            payload["clause_text"] = clause_text.strip()

        try:
            result = submit_deal(payload)
            decision = result["decision"]

            if decision["auto_approved"]:
                st.success(f"Deal **auto-approved** | Priority: {decision['priority']}")
            else:
                teams = ", ".join(decision["escalation_path"])
                st.warning(
                    f"Deal **escalated** to {teams} | Priority: {decision['priority']} | Weight: {decision['total_weight']}"
                )

            with st.expander("Full Pipeline Result"):
                st.json(result)

        except Exception as e:
            st.error(f"Error: {e}")

# ---------------------------------------------------------------------------
# Tab 2: CSV upload
# ---------------------------------------------------------------------------
with tab_csv:
    st.markdown("Upload a CSV with columns: `deal_type, customer_segment, annual_contract_value, discount_percentage, payment_terms_days, region, custom_security_clause, clause_text`")

    uploaded = st.file_uploader("Choose CSV file", type=["csv"])
    if uploaded is not None:
        process_btn = st.button("Process CSV", use_container_width=True)
        if process_btn:
            content = uploaded.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(content))
            results = []
            errors = []
            progress = st.progress(0)
            rows = list(reader)
            for i, row in enumerate(rows):
                try:
                    payload = {
                        "deal_type": row["deal_type"].strip(),
                        "customer_segment": row["customer_segment"].strip(),
                        "annual_contract_value": float(row["annual_contract_value"]),
                        "discount_percentage": float(row["discount_percentage"]),
                        "payment_terms_days": int(row["payment_terms_days"]),
                        "region": row["region"].strip(),
                        "custom_security_clause": row.get("custom_security_clause", "").strip().lower() in ("true", "1", "yes"),
                    }
                    clause = row.get("clause_text", "").strip()
                    if clause:
                        payload["clause_text"] = clause
                    result = submit_deal(payload)
                    results.append(result)
                except Exception as e:
                    errors.append({"row": i + 1, "error": str(e)})
                progress.progress((i + 1) / len(rows))

            st.success(f"Processed {len(results)} deals successfully.")
            if errors:
                st.error(f"{len(errors)} deals failed:")
                st.json(errors)

# ---------------------------------------------------------------------------
# Tab 3: Sample data generator
# ---------------------------------------------------------------------------
with tab_generate:
    col1, col2 = st.columns(2)
    with col1:
        gen_count = st.number_input("Number of deals", min_value=1, max_value=500, value=50)
    with col2:
        auto_process = st.checkbox("Auto-process through pipeline", value=True)

    col_gen, col_reset = st.columns(2)
    with col_gen:
        if st.button("Generate Deals", use_container_width=True):
            with st.spinner(f"Generating {gen_count} deals..."):
                try:
                    result = seed_deals(count=gen_count, auto_process=auto_process)
                    st.success(f"Generated {result['generated']} deals.")
                except Exception as e:
                    st.error(f"Error: {e}")

    with col_reset:
        if st.button("Reset & Regenerate", use_container_width=True, type="secondary"):
            with st.spinner(f"Resetting and generating {gen_count} deals..."):
                try:
                    result = reset_and_seed(count=gen_count)
                    st.success(f"Database reset. Generated {result['generated']} deals.")
                except Exception as e:
                    st.error(f"Error: {e}")
