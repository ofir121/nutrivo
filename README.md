# AI-Powered Personalized Meal Planner

A production-ready REST API that turns natural language requests into multi-day meal plans with recipes, nutrition, and summaries.

## ✨ At a Glance
- ✅ `POST /api/generate-meal-plan` for natural language meal planning
- 🧠 Rules-first parsing with optional LLM fallback for ambiguous queries
- 🧺 Hybrid recipe sources: local JSON + TheMealDB
- 🥗 Nutrition support with optional USDA enrichment
- 🖥️ Optional Streamlit UI for demos

## 🧭 Table of Contents
- Problem Understanding
- Architecture Overview
- Setup and Installation
- How to Run the API
- API Usage (Request + Response Example)
- Testing
- Design Decisions and Trade-offs
- Known Limitations
- Future Improvements

## 🧠 Problem Understanding
Meal planning is a high-friction task: people describe goals in natural language (diet type, exclusions, prep time, budget),
but need a structured, realistic plan. This project bridges that gap by parsing free-form queries into constraints and
producing balanced meal plans that are practical to cook and easy to review.

## 🏗️ Architecture Overview
- **API layer (FastAPI)**: `app/main.py` exposes `POST /api/generate-meal-plan` with rate limiting, request logging, and
  Pydantic validation using `app/models.py`.
- **Query parsing**: `app/services/parser_service.py` extracts duration, diets, exclusions, and preferences using
  deterministic rules and (optionally) `app/services/ai_service.py` for ambiguous queries.
- **Conflict resolution**: `app/services/conflict_resolver.py` rejects invalid requests (e.g., conflicting diets, >7 days).
- **Recipe sourcing**: `app/services/recipe_service.py` aggregates from:
  - `Local` source backed by `data/mock_recipes.json`
  - `TheMealDB` via `app/services/sources/mealdb.py`
  Results are cached in memory with a short TTL.
- **Nutrition and timing**:
  - Local recipes use embedded nutrition; optional USDA enrichment via
    `app/services/usda_service.py` + `app/services/nutrition_calculator.py`.
  - Missing prep times are estimated with `app/utils/time_estimator.py`.
- **Planning and scoring**: `app/services/planner.py` assembles day-by-day plans using deterministic scoring
  (`app/services/scoring.py`), diversity penalties, and macro balance heuristics.
- **Optional UI**: `app/frontend.py` provides a Streamlit interface for demos.

## ⚙️ Setup and Installation
### Prerequisites
- Python 3.9+
- pip

### Local setup
1. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   - `OPENAI_API_KEY` enables LLM enhancement for ambiguous queries (optional).
   - `USDA_API_KEY` enables nutrition enrichment (optional).

## 🚀 How to Run the API
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

## 📡 API Usage
### Endpoint
`POST /api/generate-meal-plan`

### Example request
```bash
curl -X POST http://127.0.0.1:8000/api/generate-meal-plan \
  -H "Content-Type: application/json" \
  -d '{"query":"Create a 3-day vegetarian meal plan","sources":["Local","TheMealDB"]}'
```

### Example response (truncated to 1 day and 1 meal)
```json
{
  "meal_plan_id": "b5a2c4c2-1d0a-4b5c-9b1e-0a0b2a2d7f23",
  "duration_days": 3,
  "generated_at": "2025-01-15T12:34:56Z",
  "meal_plan": [
    {
      "day": 1,
      "date": "2025-01-16",
      "meals": [
        {
          "meal_type": "breakfast",
          "recipe_name": "High-Protein Oatmeal Bowl",
          "description": "A delicious breakfast.",
          "ingredients": ["1 cup oats", "1 cup almond milk", "1 tbsp chia seeds"],
          "nutritional_info": {
            "calories": 350,
            "protein": 25,
            "carbs": 45,
            "fat": 8
          },
          "preparation_time": "15 mins",
          "instructions": "Cook oats, top with fruit.",
          "source": "local"
        }
      ]
    }
  ],
  "summary": {
    "total_meals": 9,
    "dietary_compliance": ["vegetarian", "high-protein"],
    "estimated_cost": "$45-60",
    "avg_prep_time": "18 mins"
  }
}
```

## 🧪 Testing
Run the full test suite:
```bash
pytest
```

## ⚖️ Design Decisions and Trade-offs
- **Rule-based parsing with LLM fallback**: Rules provide speed, determinism, and zero cost; the LLM is only used when
  the query is ambiguous. Trade-off: complex or novel phrasing may still miss intent without a key.
- **Hybrid recipe sourcing**: Local data ensures reliability and filtering control; TheMealDB adds variety.
  Trade-off: external data has limited dietary metadata and requires best-effort filtering.
- **Deterministic scoring and greedy selection**: Fast and explainable, with penalties for repetition and macro imbalance.
  Trade-off: not globally optimal compared to CSP or ILP approaches.
- **In-memory cache and rate limits**: Simple and effective for the take-home scope.
  Trade-off: resets on restart and does not scale across processes.
- **Nutrition enrichment via USDA**: Improves accuracy when keys are available.
  Trade-off: ingredient parsing is heuristic and external lookups can be slow or incomplete.

## ⚠️ Known Limitations
- **Nutrition accuracy**: TheMealDB lacks nutrition data; values use a heuristic fallback unless USDA enrichment succeeds.
- **Diet compliance with external data**: TheMealDB has limited filtering, so compliance is best-effort.
- **Static cost estimate**: `estimated_cost` is a fixed placeholder value.
- **No persistent user state**: Preferences are not stored; there is no auth or profile history.
- **Rate limiting and caching are per-process**: They reset on restart and are not distributed.
- **Plan dates**: Dates start from the next day using local server time.
- **Dataset size**: The local recipe set is finite, so repetition can still occur for long plans.

## 🔭 Future Improvements
- Replace greedy planning with a constraint solver for stronger nutrition and diversity optimization.
- Add persistent user profiles and history to personalize plans over time.
- Improve cost estimation using ingredient pricing data.
- Expand sources (e.g., Spoonacular) and add richer metadata normalization.
- Add comprehensive tests around nutrition parsing and diet rule coverage.
