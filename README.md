# Nutrivo (AI-Powered Meal Planner)

Nutrivo is a FastAPI + Streamlit app that turns natural-language meal planning requests into a multi-day plan with recipes, nutrition summaries, and optional AI reranking.
It combines deterministic parsing/scoring with optional LLM enhancements for ambiguous requests and tie-breaking.

## Demo / Screenshots

![Nutrivo logo](app/static/assets/nutrivo_logo.png)

## Features
- Natural-language meal planning via `POST /api/generate-meal-plan`.
- Rules-first parser with optional LLM enhancement for ambiguous queries.
- Recipe aggregation from local JSON (`data/mock_recipes.json`) and TheMealDB.
- Deterministic scoring with diversity and macro-balance penalties.
- Optional LLM reranking of top-K candidates with short selection reasons.
- Optional USDA nutrition enrichment and cached lookups.
- Streamlit UI for interactive demos and raw JSON inspection.
- Rate limiting + request logging middleware in the API.

## How It Works
1. User submits a natural-language query (UI or API).
2. Parser extracts duration, diets, exclusions, calories, and preferences.
3. Conflict resolver enforces constraints (e.g., max 7 days, incompatible diets).
4. Recipe sources fetch and filter candidates (local + TheMealDB) with caching.
5. Deterministic scoring ranks candidates with diversity + macro balance penalties.
6. Optional LLM reranker selects among top-K candidates (per-meal or batch).
7. Planner assembles the plan and returns a summary (avg prep time, etc.).

## Tech Stack
- FastAPI + Uvicorn (API)
- Streamlit (UI)
- Pydantic (models/validation)
- OpenAI API (optional LLM enhancement + rerank)
- Requests (TheMealDB + USDA)
- Pytest (tests)

## Local Setup

### Prerequisites
- Python 3.9+
- pip

### Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables
Copy `.env.example` and fill in only what you need:
```bash
cp .env.example .env
```
Used by the codebase:
- `OPENAI_API_KEY` (optional) for LLM query enhancement + reranking.
  - Used in `app/services/ai_service.py` and `app/services/reranker_service.py`.
- `USDA_API_KEY` (optional) for nutrition enrichment + cached lookups.
  - Used in `app/services/usda_service.py` and `app/services/sources/local.py`/`mealdb.py`.
- `API_URL` (optional) overrides the backend URL in the Streamlit UI.
  - Used in `app/frontend.py`.
- `API_DOCS_URL` (optional) overrides the FastAPI docs link in the UI.
  - Used in `app/frontend.py`.

LLM reranker settings live in `config/llm_config.json` (not environment variables):
- `rerank_enabled`, `rerank_top_k`, `rerank_mode` (`per_meal`, `per_day`, `per_plan`), `rerank_cache_ttl_seconds`.

### Run (API + UI)
```bash
python run.py
```
- API: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- UI: `http://127.0.0.1:8501`

### Run (API only)
```bash
uvicorn app.main:app --reload --port 8000
```

### Run (UI only)
```bash
streamlit run app/frontend.py --server.port 8501
```

## Testing
```bash
pytest
```

## Deployment Notes
- Docker image uses `start.sh` to launch both API (8000) and Streamlit (8501).
- Render deployment is defined in `render.yaml` and expects a Docker build.
- `start.sh` respects `PORT` for the UI and binds both services to `0.0.0.0`.

## Tradeoffs & Limitations
- **LLM cost/latency:** Optional reranking and query enhancement add latency and token cost when enabled.
- **MealDB filtering is best-effort:** TheMealDB lacks strong dietary metadata; filtering uses tags + heuristics.
- **Heuristic nutrition without USDA:** MealDB recipes fall back to heuristic macro estimates if USDA lookups fail.
- **Greedy selection:** Deterministic scoring is per-meal; it is not a global optimizer across the full plan.
- **Top-K rerank only:** The LLM sees only top-K candidates, which can miss a better option outside that set.
- **Retrieval scope is limited:** Local recipes are finite and MealDB fetches only a small sample per request.
- **Prompt brittleness:** LLM output must be valid JSON; invalid outputs fall back to deterministic picks.
- **In-memory caches:** Recipe and reranker caches reset on restart and do not share across processes.
- **Static cost estimate:** `estimated_cost` is a fixed placeholder string today.
- **Max duration:** Plans over 7 days are rejected by `app/services/conflict_resolver.py`.
- **Evaluation gaps:** There is no automated quality eval beyond unit tests.

## Future Improvements (Prioritized)
1. Add a persistent cache (Redis) for MealDB/USDA and reranker results.
2. Improve nutrition accuracy with stronger ingredient parsing and richer food data.
3. Add an evaluation harness to compare scoring vs reranking outcomes.
4. Expand recipe sources and normalize metadata for stricter diet compliance.
5. Replace greedy selection with a constrained optimizer for plan-level balance.
