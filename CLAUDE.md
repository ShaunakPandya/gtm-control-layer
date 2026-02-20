# GTM Control Layer — Project Guide

## Project Overview

This is a **Programmable GTM Control Layer** — a deterministic deal-policy engine with AI clause advisory, built with FastAPI + Streamlit.

Deals flow through a pipeline: **Validate → Evaluate Rules → Route → AI Advisory** — then land in a dashboard with KPIs, simulation, and manual overrides.

**Purpose:** Automate go-to-market deal approval workflows with configurable rules, priority routing, AI-powered clause analysis, and operational metrics.

---

## Tech Stack

### Backend (FastAPI)
- **Framework:** FastAPI (Python 3.11+)
- **Port:** `:8000`
- **Database:** SQLite with WAL mode (`gtm_deals.db`)
- **API Structure:**
  - `app/api/` — routes, error handling (RFC 7807)
  - `app/intake/` — Pydantic v2 models for deal validation
  - `app/rules/` — 5 deterministic rule evaluators
  - `app/routing/` — priority calculation + escalation path
  - `app/advisory/` — dual-mode Claude client (mock/live)
  - `app/db/` — SQLite CRUD operations
  - `app/metrics/` — KPI aggregation, simulation, seed data
- **Testing:** 212 pytest tests covering all features

### Frontend (Streamlit)
- **Framework:** Streamlit
- **Port:** `:8501`
- **Visualization:** Altair charts
- **HTTP Client:** httpx (connects to FastAPI backend)
- **Structure:**
  - `streamlit_app/app.py` — main entry point
  - `streamlit_app/api_client.py` — backend HTTP client
  - `streamlit_app/charts.py` — shared Altair chart helpers
  - `streamlit_app/pages/` — 4 pages (see below)

---

## CRITICAL CONSTRAINT

**NEVER modify the FastAPI backend (`app/` directory) or test files (`tests/`).**

The backend is complete, tested (212 passing tests), and locked. All UI/UX work must be isolated to the Streamlit frontend.

**What you CAN modify:**
- `streamlit_app/app.py`
- `streamlit_app/pages/1_Submit.py`
- `streamlit_app/pages/2_Dashboard.py`
- `streamlit_app/pages/3_Simulation.py`
- `streamlit_app/pages/4_Admin.py`
- `streamlit_app/charts.py`
- `.streamlit/` config files

**What you CANNOT modify:**
- `app/` directory (FastAPI backend)
- `tests/` directory
- `config/rules.json` (unless explicitly requested by user)
- `pyproject.toml`, `requirements.txt`, `requirements-api.txt`

---

## UI Files

All Streamlit UI code lives in `streamlit_app/`:

### Core Files
- **`app.py`** — Landing page, nav sidebar, theme config, page router
- **`api_client.py`** — httpx client for all backend API calls
- **`charts.py`** — Reusable Altair chart components (bar, pie, time series)

### Pages
- **`pages/1_Submit.py`** — Deal submission form, CSV upload, sample data generator with auto-process
- **`pages/2_Dashboard.py`** — 5 KPI cards, escalation-by-team chart, top-triggers chart, filterable deal log with tabs
- **`pages/3_Simulation.py`** — Threshold adjustment sliders, rule toggles, what-if simulation, side-by-side/delta view
- **`pages/4_Admin.py`** — Manual override form, override history chart, config viewer (read-only JSON display)

---

## Design Goal

**Current state:** Functional dark theme with basic Streamlit defaults (purple accents, standard widgets, minimal custom styling).

**Target state:** Polished, professional UI that feels like a modern SaaS dashboard.

### Design Objectives
1. **Cohesive visual identity** — Move beyond default Streamlit aesthetics
2. **Professional color palette** — Replace purple accents with a business-appropriate scheme
3. **Enhanced data visualization** — Upgrade Altair charts with better styling, tooltips, interactions
4. **Improved layout & spacing** — Better use of columns, cards, whitespace
5. **Consistent typography & iconography** — Unified font hierarchy, meaningful icons
6. **Accessibility** — WCAG AA compliance, proper contrast ratios, keyboard navigation
7. **Responsive design** — Works well on 375px, 768px, 1024px, 1440px viewports

### Anti-Patterns to Avoid
- Emojis as icons (use SVG from Heroicons/Lucide instead)
- Harsh animations or bright neon colors
- Inconsistent spacing or alignment
- Poor contrast ratios (ensure 4.5:1 minimum)
- Over-engineering (keep changes minimal and focused)

---

## Available Skills & Tools

This project has two Claude Code skills installed:

### 1. Superpowers (obra/superpowers)
- **Purpose:** Software development workflow automation
- **Key skills:** TDD, systematic debugging, brainstorming, code review, subagent-driven development
- **When to use:** For planning complex features, test-driven refactoring, or systematic debugging

### 2. UI/UX Pro Max (nextlevelbuilder/ui-ux-pro-max-skill)
- **Purpose:** Design system intelligence for UI/UX work
- **Resources:** 67 UI styles, 96 color palettes, 57 font pairings, 100 reasoning rules
- **Auto-activates:** When you request UI/UX work (build, design, create, implement, review, fix, improve)
- **Design system generator:** Analyzes project type and generates tailored style + color + typography recommendations
- **Pre-delivery checklist:** Validates against common UI/UX anti-patterns

Both skills auto-activate based on context, so just describe your intent naturally.

---

## Quick Start (Local Development)

### 1. Install dependencies
```bash
cd GTM
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Start FastAPI backend
```bash
uvicorn app.api.main:app --reload --port 8000
```

### 3. Start Streamlit frontend
In a second terminal:
```bash
source .venv/bin/activate
streamlit run streamlit_app/app.py
```

### 4. Seed sample data
```bash
curl -X POST http://localhost:8000/seed -H "Content-Type: application/json" \
  -d '{"count": 50, "auto_process": true}'
```

---

## Deployment

- **API:** Render (see `render.yaml`)
- **UI:** Streamlit Community Cloud (connects via `GTM_API_URL` env var)
- **Database:** SQLite (ephemeral on Render free tier; use `/tmp/gtm.db`)

---

## Workflow for UI Changes

1. **Read first** — Always read the file you plan to modify before making changes
2. **Minimal changes** — Only modify what's necessary to achieve the goal
3. **Test locally** — Verify changes with the Streamlit dev server before committing
4. **No backend changes** — Double-check you're only editing `streamlit_app/` files
5. **Preserve functionality** — All existing features must continue to work

---

## Notes

- The backend API is deterministic and fully tested — trust it
- Streamlit uses `httpx` for API calls (see `api_client.py`)
- Charts use Altair (see `charts.py` for shared helpers)
- Dark theme is configured via `.streamlit/config.toml`
- All configuration lives in `config/rules.json` (view-only from UI)
