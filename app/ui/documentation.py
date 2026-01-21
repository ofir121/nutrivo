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
Ambiguity detection (used to decide whether to call the LLM):
- **Heuristic only (no numeric score).**
- A query is **ambiguous** if:
  - It has **no concrete constraints** (no diets, exclusions, calories, or preferences) and duration is the **default 3 days**, or
  - It contains **vague terms** like `healthy` or `next week` **and** lacks specific constraints.
- Implemented in `_is_ambiguous(...)` in `app/services/parser_service.py`.
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
    st.subheader("🧮 Heuristics & Algorithms")
    st.markdown(
        """
Query parsing heuristics (`app/services/parser_service.py`):
- **Duration:** "week/next week" -> 7 days, `N-day` -> `max(N, 1)`, default 3.
- **Meals per day:** default 3; if "snack" appears, add 1.
- **Diets:** keyword match against `DIET_DEFINITIONS` (supports hyphen/space variants).
- **Exclusions:** parses "no/without/exclude X" lists and `X-free`; normalizes via `INGREDIENT_SYNONYMS`.
- **Preferences:** detects high/low macros, quick/fast, budget-friendly, healthy, and "under N minutes".
- **Quick threshold:** `under-N-minutes` wins; otherwise "quick" -> 20 minutes.
- **Ambiguity detection:** heuristic gates LLM enhancement (see above).
"""
    )

    st.markdown(
        """
Conflict resolution (`app/services/conflict_resolver.py`, `app/core/rules.py`):
- **Duration cap:** requests over 7 days return a 400 error.
- **Incompatible diets:** any pair in `INCOMPATIBLE_DIETS` triggers 409.
"""
    )

    st.markdown(
        """
Recipe retrieval + filtering:
- **Local source (`app/services/sources/local.py`):**
  - Exclusions check title + ingredient text (with synonym normalization).
  - Diet match: normalized tag match + simple hierarchy (vegan ⇒ vegetarian, keto ⇒ ketogenic).
  - Diet rule enforcement: reject forbidden ingredients/tags unless allowed exceptions apply.
  - Prep time: batch LLM estimate when enabled; fallback to heuristic estimator; default 30 mins if missing.
- **MealDB source (`app/services/sources/mealdb.py`):**
  - Fetch strategy: category mapping for known meal types, then search fallback.
  - Diet bootstrapping: if vegan/vegetarian requested, fetch those categories too.
  - Final fallback: generic searches ("a", then "b") to fill variety; hard cap of 10 recipes.
  - Detail fetch limited to 3 items per category list; dedup by id.
  - Best-effort diet + exclusion filtering using tags/title/ingredients.
  - Nutrition: USDA when available; otherwise heuristic macro estimates.
"""
    )

    st.markdown(
        """
Time estimation heuristic (`app/utils/time_estimator.py`):
- **Prep time:** base 5 mins + ingredient count penalty + step count penalty.
- **Cook time:** sum explicit time ranges if present; otherwise keyword buckets (slow-cook > bake > boil > saute).
- **Wait time:** adds for "overnight"/marinate/rest/proof unless explicit times exist.
- **Clamp:** result is between 5 and 180 minutes.
"""
    )

    st.markdown(
        """
Deterministic scoring (`app/services/scoring.py`):
- **Keyword preference boost:** +1 for soft preference matches in title/ingredients/tags.
- **Macro alignment:** high-protein adds (capped), low-carb/low-fat subtract (capped).
- **Low-sodium:** penalize recipes with salty keywords.
- **Quick:** penalize over-threshold prep times.
- **Budget-friendly:** small boost for fewer ingredients.
- **Diversity penalties:** ingredient token overlap vs previous day and dish type repetition.
"""
    )

    st.markdown(
        """
Planner selection (`app/services/planner.py`):
- **Greedy per-meal selection** using deterministic scores.
- **Macro balance penalty:** penalizes ratios outside protein 20–45%, carbs 25–60%, fat 15–40%.
- **Stable tie-break:** scores sorted by score, then recipe id.
- **Fallbacks:** if unique pool is exhausted, reuse candidates (tracked in `defaults_applied`).
- **Rerank (optional):** only top-K candidates are sent to the LLM; per-meal or batch modes.
"""
    )

    st.markdown(
        """
USDA lookup (`app/services/usda_service.py`):
- **Best match:** choose the first result by preferred data type order.
- **Units:** converts Energy from kJ to kcal.
- **Caching:** per-ingredient cache persisted in `data/usda_cache.json`.
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

    st.subheader("🧭 Future improvements")
    st.markdown(
        """
- **Plan-level optimization:** replace greedy selection with a constraint solver
  (macro balance, diversity, prep-time budgets across the full plan).
- **Persistent caching + shared rate limits:** add Redis for MealDB/USDA lookups
  and reranker results, with cache stampede protection.
- **Evaluation harness:** build a labeled query set and metrics to compare
  deterministic scoring vs. LLM rerank.
- **Richer sources + normalized metadata:** expand providers and map ingredients to
  a diet taxonomy for stricter compliance.
- **Nutrition accuracy upgrades:** improve ingredient parsing (units/quantities) and
  use higher-quality food data.
- **Personalization + budget awareness:** store user profiles and integrate price
  data to enforce budget constraints.
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
