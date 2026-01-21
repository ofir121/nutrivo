# AI-Powered Personalized Meal Planner

A production-ready REST API that turns natural language requests into multi-day meal plans with recipes, nutrition, and summaries.

## Problem Understanding
Meal planning is a high-friction task: people describe goals in natural language (diet type, exclusions, prep time, budget), but need a structured, realistic plan. This project bridges that gap by parsing free-form queries into constraints and generating a balanced plan that is practical to cook and easy to review.

## Architecture Overview
- **API layer (FastAPI)**: `app/main.py` exposes `POST /api/generate-meal-plan` and provides rate limiting, request logging, and error handling via `MealPlanRequest`/`MealPlanResponse` models in `app/models.py`.
- **Query parsing**: `app/services/parser_service.py` extracts duration, diets, exclusions, and preferences with deterministic rules and optionally enhances ambiguous queries using OpenAI via `app/services/ai_service.py`.
- **Conflict resolution**: `app/services/conflict_resolver.py` rejects impossible requests (e.g., conflicting diets, >7 days) early with clear error messages.
- **Recipe sourcing**: `app/services/recipe_service.py` aggregates from:
  - `Local` source backed by `data/mock_recipes.json`
  - `TheMealDB` remote API via `app/services/sources/mealdb.py`
  Results are cached in memory with a short TTL.
- **Nutrition and timing**:
  - Local recipes use embedded nutrition; optional USDA lookup enriches nutrition via `app/services/usda_service.py` and `app/services/nutrition_calculator.py`.
  - Prep time is estimated when missing using `app/utils/time_estimator.py`.
- **Planning and scoring**: `app/services/planner.py` assembles a daily plan using deterministic scoring (`app/services/scoring.py`), diversity penalties, and macro balance heuristics.
- **Optional UI**: `app/frontend.py` provides a Streamlit interface for demo and exploration.

## Setup and Installation
### Prerequisites
- Python 3.9+
- pip

### Local setup
1. Create a virtual environment (recommended).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Add OPENAI_API_KEY and/or USDA_API_KEY if you want enhanced parsing/nutrition
   ```

## How to Run the API
### Quick start (API + UI)
```bash
python run.py
```
- API: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`
- UI: `http://127.0.0.1:8501`

### API only
```bash
uvicorn app.main:app --reload --port 8000
```

### Docker
```bash
docker build -t nutrivo .
docker run -p 8000:8000 -p 8501:8501 nutrivo
```

### Example request
```bash
curl -X POST http://127.0.0.1:8000/api/generate-meal-plan \
  -H "Content-Type: application/json" \
  -d '{"query":"Create a 3-day vegetarian meal plan","sources":["Local","TheMealDB"]}'
```

## Design Decisions and Trade-offs
- **Rule-based parsing with LLM fallback**: Rules provide speed, determinism, and zero cost; the LLM is only used when the query is ambiguous. Trade-off: complex or novel phrasing may still miss intent without a key.
- **Hybrid recipe sourcing**: Local data ensures reliability and filtering control; TheMealDB adds variety. Trade-off: external data has limited dietary metadata and requires best-effort filtering.
- **Deterministic scoring and greedy selection**: Fast and explainable, with penalties for repetition and macro imbalance. Trade-off: not globally optimal compared to CSP or ILP approaches.
- **In-memory cache and rate limits**: Simple and effective for the take-home scope. Trade-off: resets on restart and does not scale across processes.
- **Nutrition enrichment via USDA**: Improves accuracy when keys are available. Trade-off: ingredient parsing is heuristic and external lookups can be slow or incomplete.

## Known Limitations
- **Nutrition accuracy**: TheMealDB lacks nutrition data; values may be placeholders unless USDA enrichment succeeds.
- **Diet compliance with external data**: TheMealDB has limited filtering, so compliance is best-effort.
- **Static cost estimate**: `estimated_cost` is a fixed placeholder value.
- **No persistent user state**: Preferences are not stored; there is no auth or profile history.
- **Rate limiting and caching are per-process**: They reset on restart and are not distributed.
- **Plan dates**: Dates start from the next day using local server time.
- **Dataset size**: The local recipe set is finite, so repetition can still occur for long plans.

## Future Improvements
- Replace greedy planning with a constraint solver for stronger nutrition and diversity optimization.
- Add persistent user profiles and history to personalize plans over time.
- Improve cost estimation using ingredient pricing data.
- Expand sources (e.g., Spoonacular) and add richer metadata normalization.
- Add comprehensive tests around nutrition parsing and diet rule coverage.
