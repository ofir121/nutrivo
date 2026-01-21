import streamlit as st


def render_documentation() -> None:
    st.header("📚 Documentation")
    st.markdown(
        """
Welcome to the in-app docs. This is a quick, engineering-focused map of how the meal
planner works, how AI is used, and where to extend it.
"""
    )

    st.divider()
    st.subheader("✅ Quickstart Walkthrough")
    st.markdown(
        """
- **Start the app:** `python run.py` (or run API + UI separately).
- **Open the UI:** `http://127.0.0.1:8501`.
- **Enter a query:** e.g. `3-day vegetarian plan with high protein`.
- **Pick sources:** `Local` and/or `TheMealDB`.
- **Optional toggle:** `Use LLM to rank meals` adds selection reasons.
- **Generate:** Expect a multi-day plan, summary metrics, and expandable meals.
"""
    )

    st.markdown(
        """
Environment setup:
- `OPENAI_API_KEY` (optional) enables LLM parsing + reranking.
- `USDA_API_KEY` (optional) enables nutrition enrichment.
- `API_URL` / `API_DOCS_URL` override Streamlit links.
- Rerank settings live in `config/llm_config.json`.
"""
    )

    st.subheader("🧠 What happens when you click Generate?")
    st.markdown(
        """
1. **UI collects input** (`app/frontend.py`): query + recipe sources + optional LLM rerank.
2. **API request** to `/api/generate-meal-plan` (`app/main.py`).
3. **Parser extracts structure** and optionally enhances ambiguous text via LLM
   (`app/services/parser_service.py`, `app/services/ai_service.py`).
4. **Conflict validation** (duration caps, incompatible diets) is enforced
   (`app/services/conflict_resolver.py`, `app/core/rules.py`).
5. **Recipe retrieval** aggregates sources with caching
   (`app/services/recipe_service.py`, `app/services/sources/local.py`,
   `app/services/sources/mealdb.py`).
6. **Deterministic scoring** ranks candidates and applies diversity penalties
   (`app/services/scoring.py`).
7. **Macro balance + stable tie-breaks** pick the final schedule
   (`app/services/planner.py`).
8. **Optional LLM rerank** can select among top-K and return reasons,
   either per meal or in batch (`app/services/reranker_service.py`).
9. **Response model** returns to UI and renders expanders, macros, and raw JSON.
"""
    )

    st.markdown(
        """
Architecture at a glance:
```
[Streamlit UI] -> [FastAPI /api/generate-meal-plan]
        |                    |
        v                    v
  user query           parser -> conflicts -> recipes
                                -> scoring -> planner -> response
```
"""
    )

    st.divider()
    st.subheader("🧩 Engineering Overview")
    st.markdown(
        """
- **Prompts live in:**
  - `app/services/ai_service.py` (query enhancement prompt)
  - `app/services/reranker_service.py` (rerank + batch rerank prompts)
- **Scoring/ranking lives in:**
  - `app/services/scoring.py` (preference + diversity scoring)
  - `app/services/planner.py` (macro balance penalties + selection)
- **Caching:**
  - In-memory recipe cache in `app/services/recipe_service.py` (TTL 300s).
  - In-memory reranker cache in `app/services/reranker_service.py` (TTL via `config/llm_config.json`).
  - USDA ingredient cache persisted to `data/usda_cache.json`.
- **Error handling/fallbacks:**
  - `400` when duration exceeds 7 days (`app/services/conflict_resolver.py`).
  - `409` for conflicting diets.
  - `502` if all recipe sources fail (`app/services/recipe_service.py`).
  - LLM failures fall back to deterministic scoring.
"""
    )

    st.divider()
    st.subheader("🤖 AI Design")
    st.markdown(
        """
- **LLM calls per request (when enabled):**
  - Query enhancement: `0–1` calls (only for ambiguous queries).
  - Reranking:
    - `per_meal`: up to 1 call per meal.
    - `per_day`: 1 batch call per day.
    - `per_plan`: 1 batch call for the entire plan.
- **What each call does:**
  - Parse enhancement extracts structured intent.
  - Rerank selects from top-K candidates and returns short reasons.
- **Cost/latency control:**
  - LLM is optional and guarded by `OPENAI_API_KEY` + UI toggle.
  - Rerank mode + top-K live in `config/llm_config.json`.
  - Caching avoids repeated rerank calls.
- **Deterministic vs non-deterministic:**
  - Parsing rules, scoring, and plan assembly are deterministic.
  - LLM enhancement and reranking are non-deterministic by nature.
"""
    )

    st.divider()
    st.subheader("⚖️ Known Tradeoffs")
    st.markdown(
        """
- **Best-effort diet filtering for MealDB:** limited metadata means some tags are noisy.
- **Heuristic nutrition when USDA is missing:** MealDB macros are estimates.
- **Greedy selection:** scoring is per-meal, not a global optimizer across days.
- **Top-K rerank only:** the LLM never sees the full candidate set.
- **In-memory caches:** reset on restart and are not shared across processes.
- **Static cost estimate:** `estimated_cost` is a placeholder string.
- **Prompt brittleness:** malformed LLM output leads to fallback selection.
"""
    )

    st.divider()
    st.subheader("🛠️ How to extend")
    st.markdown(
        """
- **New recipe source:** implement `RecipeSource` in
  `app/services/sources/base.py`, then register in `app/services/recipe_service.py`.
- **New preference:** extend parser extraction and add a scoring signal.
- **Tune weights:** update scoring constants in `app/services/scoring.py`.
- **Tests:** add coverage in `tests/` for parser, scoring, and planner loops.
"""
    )

    st.divider()
    st.subheader("❓ FAQ / Troubleshooting")
    st.markdown(
        """
- **“Backend not running” error:** start FastAPI with
  `uvicorn app.main:app --reload --port 8000`.
- **Missing `OPENAI_API_KEY`:** LLM features are disabled; deterministic plan still works.
- **MealDB failures:** source errors bubble as 502; local recipes still serve.
"""
    )
