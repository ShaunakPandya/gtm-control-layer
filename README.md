# Programmable GTM Control Layer

A deterministic deal-policy engine with AI clause advisory, built with FastAPI + Streamlit.

Deals flow through a pipeline: **Validate → Evaluate Rules → Route → AI Advisory** — then land in a dashboard with KPIs, simulation, and manual overrides.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI (:8501)                  │
│  Submit │ Dashboard │ Simulation │ Admin                │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP (httpx)
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI API (:8000)                    │
│                                                         │
│  POST /deals ──── Full Pipeline                         │
│    ├── Intake (Pydantic validation)                     │
│    ├── Rule Engine (5 deterministic rules)              │
│    ├── Routing Engine (priority + escalation path)      │
│    └── AI Advisory (Claude API / mock)                  │
│                                                         │
│  GET  /metrics          POST /simulate                  │
│  POST /deals/{id}/override    POST /seed                │
│  GET  /deals/list       GET  /health                    │
└────────────────────────┬────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   SQLite (WAL mode) │
              │   deals │ overrides │
              └─────────────────────┘
```

---

## Features

### Feature 1 — Deal Intake & Validation
Pydantic v2 models for deal input with strict type enforcement. Validates deal type, customer segment, region, ACV, discount, payment terms, security clause, and optional clause text.

- **Endpoint:** `POST /deals/validate`
- **Models:** `app/intake/models.py` — `DealInput`, `ValidatedDeal`, enums (`DealType`, `CustomerSegment`, `Region`)
- **Errors:** RFC 7807 Problem Details format (`app/api/errors.py`)

### Feature 2 — Deterministic Rule Engine
Five configurable rules evaluated against segment-aware thresholds loaded from `config/rules.json`. Supports per-segment overrides (Enterprise, SMB have different limits).

| Rule | Trigger | Escalation Team |
|------|---------|-----------------|
| `DISCOUNT_THRESHOLD` | Discount exceeds segment threshold | Finance |
| `ACV_EXEC_THRESHOLD` | ACV exceeds segment ceiling | Exec |
| `EU_LEGAL_REVIEW` | EU region + legal review enabled | Legal |
| `PAYMENT_TERMS_LIMIT` | Payment days exceed limit | Finance |
| `CUSTOM_SECURITY_CLAUSE` | Custom security clause present | Security |

- **Endpoint:** `POST /deals/evaluate`
- **Config:** `config/rules.json` — thresholds, segment overrides, rule weights, priority cutoffs
- **Engine:** `app/rules/engine.py` — pure, deterministic, idempotent

### Feature 3 — Routing & Priority
Converts rule triggers into a routing decision: auto-approved (no triggers) or escalated with a priority-weighted escalation path.

- **Endpoint:** `POST /deals/route`
- **Priority:** Weight-based — P1 (weight >= 5), P2 (>= 3), P3 (>= 1)
- **Escalation order:** Configurable in `config/rules.json` (Finance → Legal → Security → Exec)
- **Engine:** `app/routing/engine.py`

### Feature 4 — AI Clause Advisory
Dual-mode Claude integration: mock mode returns deterministic results for testing; live mode calls the Claude API with retries. Analyzes contract clause text for risk level, categories, and recommendations.

- **Endpoint:** `POST /deals/analyze-clause`
- **Modes:** Set via `ADVISORY_MODE` env var (`mock` or `live`)
- **Model:** Set via `CLAUDE_MODEL` env var (defaults to `claude-sonnet-4-5-20250929`)
- **Retries:** 2 retries on failure, then flags `review_required: true`
- **Client:** `app/advisory/client.py`

### Feature 5 — Persistence, Metrics, Simulation & UI
SQLite storage, operational metrics, threshold simulation, seed data generation, manual overrides, and a full Streamlit dashboard.

- **Database:** `app/db/database.py` — SQLite with WAL mode, foreign keys
- **Metrics:** `app/metrics/compute.py` — auto-approval rate, escalation by team, top triggers, override breakdowns
- **Simulation:** `app/metrics/simulation.py` — re-evaluate historical deals against modified thresholds without mutating data
- **Seed data:** `app/metrics/seed.py` — generate realistic random deals, auto-process through pipeline
- **Override:** `POST /deals/{id}/override` — post-decision override for escalated deals only
- **Dashboard:** 4-page Streamlit app (see UI section below)

---

## Full Pipeline

`POST /deals` runs the complete pipeline in one call:

```
DealInput → Validate → Evaluate Rules → Route → AI Advisory (if clause_text) → Persist to DB
```

Returns the validated deal, routing decision, and optional advisory in a single response.

---

## UI Pages (Streamlit)

| Page | Purpose |
|------|---------|
| **Submit** | Single deal form, CSV upload, sample data generator with auto-process |
| **Dashboard** | KPI metrics (5 cards), escalation-by-team + top-triggers charts, filterable deal log with detail tabs |
| **Simulation** | Adjust thresholds + toggle rules, run what-if against historical deals, side-by-side or delta view |
| **Admin** | Apply overrides to escalated deals, override history with charts, config viewer |

---

## Quick Start

### Prerequisites
- Python 3.11+
- (Optional) `ANTHROPIC_API_KEY` env var for live AI advisory

### 1. Install

```bash
cd GTM
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Start the API server

```bash
uvicorn app.api.main:app --reload --port 8000
```

### 3. Start the Streamlit dashboard

In a second terminal:

```bash
source .venv/bin/activate
streamlit run streamlit_app/app.py
```

### 4. Seed sample data

Either use the **Submit > Generate Sample Data** tab in the UI, or:

```bash
curl -X POST http://localhost:8000/seed -H "Content-Type: application/json" \
  -d '{"count": 50, "auto_process": true}'
```

### 5. Run tests

```bash
python -m pytest tests/ -q
```

All 212 tests should pass.

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/deals` | Full pipeline (validate + evaluate + route + advisory + persist) |
| `POST` | `/deals/validate` | Validate deal input only |
| `POST` | `/deals/evaluate` | Evaluate rules against a deal |
| `POST` | `/deals/route` | Route a deal based on evaluation |
| `POST` | `/deals/analyze-clause` | AI clause advisory |
| `GET` | `/deals/list` | List all stored deals |
| `POST` | `/deals/{id}/override` | Override an escalated deal |
| `GET` | `/metrics` | Operational metrics summary |
| `POST` | `/simulate` | Threshold simulation |
| `POST` | `/seed` | Generate sample deals |
| `POST` | `/seed/reset` | Reset DB and regenerate |

---

## Configuration

All rule thresholds, weights, and escalation order are in `config/rules.json`:

```json
{
  "defaults": {
    "discount_threshold": 20,
    "acv_exec_threshold": 150000,
    "payment_terms_limit": 45,
    "eu_requires_legal": true
  },
  "segment_overrides": {
    "Enterprise": { "discount_threshold": 25, "acv_exec_threshold": 200000 },
    "SMB": { "discount_threshold": 15, "acv_exec_threshold": 75000, "payment_terms_limit": 30 }
  },
  "escalation_order": ["Finance", "Legal", "Security", "Exec"],
  "rule_weights": { ... },
  "priority_cutoffs": { "P1": 5, "P2": 3, "P3": 1 }
}
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ADVISORY_MODE` | `mock` | `mock` for deterministic results, `live` for Claude API |
| `CLAUDE_MODEL` | `claude-sonnet-4-5-20250929` | Claude model ID for live advisory |
| `ANTHROPIC_API_KEY` | — | Required for live advisory mode |
| `GTM_DB_PATH` | `gtm_deals.db` | SQLite database file path |
| `GTM_API_URL` | `http://localhost:8000` | API base URL for Streamlit client |
| `GTM_API_KEY` | — | Optional API key (sent as `X-API-Key` header) |

---

## Project Structure

```
GTM/
├── app/
│   ├── api/                  # FastAPI routes + error handling
│   │   ├── main.py           # App entry point, router registration
│   │   ├── errors.py         # RFC 7807 error handler
│   │   ├── routes_pipeline.py    # POST /deals (full pipeline)
│   │   ├── routes_intake.py      # POST /deals/validate
│   │   ├── routes_rules.py       # POST /deals/evaluate
│   │   ├── routes_routing.py     # POST /deals/route
│   │   ├── routes_advisory.py    # POST /deals/analyze-clause
│   │   ├── routes_metrics.py     # GET /metrics
│   │   ├── routes_override.py    # POST /deals/{id}/override
│   │   ├── routes_simulation.py  # POST /simulate
│   │   └── routes_seed.py        # POST /seed, /seed/reset, GET /deals/list
│   ├── intake/
│   │   └── models.py         # DealInput, ValidatedDeal, enums
│   ├── rules/
│   │   ├── config.py         # Config loader, segment-aware threshold resolution
│   │   └── engine.py         # 5 deterministic rule evaluators
│   ├── routing/
│   │   └── engine.py         # Priority calculation, escalation path builder
│   ├── advisory/
│   │   ├── models.py         # ClauseAdvisory, RiskLevel, ClauseCategory
│   │   └── client.py         # Dual-mode Claude client (mock/live)
│   ├── db/
│   │   └── database.py       # SQLite CRUD (deals + overrides tables)
│   └── metrics/
│       ├── compute.py        # KPI aggregation
│       ├── simulation.py     # What-if re-evaluation engine
│       └── seed.py           # Random deal generator
├── streamlit_app/
│   ├── app.py                # Streamlit entry point
│   ├── api_client.py         # HTTP client for the API
│   ├── charts.py             # Shared Altair chart helpers
│   └── pages/
│       ├── 1_Submit.py       # Deal form, CSV upload, seed generator
│       ├── 2_Dashboard.py    # KPIs, charts, filterable deal log
│       ├── 3_Simulation.py   # Threshold tuning + what-if analysis
│       └── 4_Admin.py        # Overrides, history, config viewer
├── config/
│   └── rules.json            # Rule thresholds, weights, escalation order
├── tests/                    # 212 tests (pytest)
└── pyproject.toml
```

---

## Testing

```bash
# Run all 212 tests
python -m pytest tests/ -q

# Run a specific feature's tests
python -m pytest tests/test_intake_models.py -v
python -m pytest tests/test_rules_engine.py -v
python -m pytest tests/test_routing_engine.py -v
python -m pytest tests/test_advisory_client.py -v
python -m pytest tests/test_db.py tests/test_metrics.py tests/test_feature5_api.py -v
```

Tests use temporary databases (via `GTM_DB_PATH` env var override) and mock mode for AI advisory, so no external dependencies are needed.

---

## Example: Submit a Deal via API

```bash
curl -X POST http://localhost:8000/deals \
  -H "Content-Type: application/json" \
  -d '{
    "deal_type": "New",
    "customer_segment": "Enterprise",
    "annual_contract_value": 250000,
    "discount_percentage": 30,
    "payment_terms_days": 60,
    "region": "EU",
    "custom_security_clause": true,
    "clause_text": "Vendor shall provide annual SOC 2 Type II audit reports."
  }'
```

This deal would trigger:
- `DISCOUNT_THRESHOLD` (30% > Enterprise threshold of 25%) → Finance
- `ACV_EXEC_THRESHOLD` ($250k > Enterprise ceiling of $200k) → Exec
- `EU_LEGAL_REVIEW` (EU region) → Legal
- `CUSTOM_SECURITY_CLAUSE` (security clause present) → Security

**Result:** Escalated, Priority P1 (weight = 2+3+2+3 = 10), path: Finance → Legal → Security → Exec

---

## Deployment Notes

### Environment variables must be set on the platform — never hardcoded

| Scenario | Required Variables |
|----------|--------------------|
| **Mock mode (demo/staging)** | `ADVISORY_MODE=mock` |
| **Live mode (production)** | `ADVISORY_MODE=live`, `ANTHROPIC_API_KEY`, optionally `CLAUDE_MODEL` |
| **Streamlit separate from API** | `GTM_API_URL=https://your-api-host.com` |

Copy `.env.example` to `.env` for local development:

```bash
cp .env.example .env
```

### Key deployment considerations

- **Database:** SQLite is file-based. The `.db` file is created at the path in `GTM_DB_PATH` (defaults to `gtm_deals.db` in the working directory). It is gitignored and must not be committed.
- **Streamlit + FastAPI split:** If deploying Streamlit and FastAPI as separate services, set `GTM_API_URL` on the Streamlit side to point to the public FastAPI URL.
- **AI advisory in production:** Set `ADVISORY_MODE=live` and provide `ANTHROPIC_API_KEY`. The default model is `claude-sonnet-4-5-20250929` — override with `CLAUDE_MODEL` if needed.
- **Secrets:** Never commit `.env`. Use your platform's secret management (Render env vars, Railway secrets, etc.).
