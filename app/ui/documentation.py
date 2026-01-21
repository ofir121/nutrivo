import streamlit as st


def render_documentation() -> None:
    st.header("📚 Documentation")
    st.markdown(
        """
Welcome to the in-app docs. This is a quick, engineering-focused map of how the meal
planner works and where to extend it.
"""
    )

    st.divider()
    st.subheader("✅ Quick Start")
    st.markdown(
        """
- **Backend:** `uvicorn app.main:app --reload --port 8000`
- **Frontend:** `streamlit run app/frontend.py --server.port 8501` (or `python run.py`)
- **Env vars:**
  - `OPENAI_API_KEY` (optional, enables LLM enhancement)
  - `API_URL` (optional override for the planner endpoint)
  - `API_DOCS_URL` (optional override for FastAPI docs)
- **Optional UI toggle:**
  - `Use LLM to rank meals` shows AI selection reasons per meal when enabled
- **Example queries:**
  - `3-day vegetarian plan with high protein`
  - `7-day gluten-free menu, no nuts`
  - `5-day pescatarian plan under 30 minutes`
"""
    )

    st.subheader("🧠 Walkthrough: What happens when you click Generate?")
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
8. **Optional LLM rerank** can select among top-K and return reasons
   (`app/services/reranker_service.py`).
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
                                -> scoring -> planner
```
"""
    )

    st.divider()
    st.subheader("🧩 Key Features")
    st.markdown(
        """
- **Deterministic scoring:** explainable, reproducible ranking decisions.
- **Constraints vs preferences:** hard conflicts vs soft scoring boosts.
- **Diversity:** ingredient/dish repetition penalties across days.
- **Macro balancing:** keeps protein/carbs/fat distribution steady.
- **Multi-source recipes + caching:** multiple providers with local cache.
- **LLM selection reasons:** explains why a meal was chosen when reranking is enabled.
- **Rate limiting + request logging:** handled by FastAPI middleware in `app/main.py`.
- **Failure modes:** 409 on conflicts, 502 when recipe sources fail.
"""
    )

    st.divider()
    st.subheader("🛠️ How to extend")
    st.markdown(
        """
- **New recipe source:** implement `RecipeSource` in
  `app/services/sources/base.py`, register in `app/services/recipe_service.py`.
- **New preference:** extend parser extraction and add a scoring signal.
- **Tuning weights:** adjust scoring constants carefully and re-run tests.
- **Tests:** add coverage in `tests/` for parser, scoring, and planner loops.
"""
    )

    st.divider()
    st.subheader("❓ FAQ / Troubleshooting")
    st.markdown(
        """
- **“Backend not running” error:** start FastAPI with
  `uvicorn app.main:app --reload --port 8000`.
- **Missing `OPENAI_API_KEY`:** LLM enhancement is disabled, app still works.
- **MealDB failures:** source errors bubble as 502; local recipes still serve.
"""
    )
