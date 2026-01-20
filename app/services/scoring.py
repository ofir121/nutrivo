import re
from typing import Dict, Iterable, Optional, Set
from app.models import ParsedQuery, Recipe

PREFERENCE_QUICK = "quick"
PREFERENCE_HIGH_PROTEIN = "high-protein"
PREFERENCE_LOW_CARB = "low-carb"
PREFERENCE_BUDGET = "budget-friendly"


def score_recipe(recipe: Recipe, parsed: ParsedQuery, context: Dict[str, object]) -> float:
    """Score a recipe deterministically against query preferences and context.

    Args:
        recipe: Recipe to score.
        parsed: Parsed query containing preferences and constraints.
        context: Context for repetition penalties (recent ingredients/dish types).

    Returns:
        A numeric score where higher is better.

    Notes:
        - Preference matches add a small, explainable boost.
        - Macro alignment adds/subtracts based on protein/carbs.
        - Quick preference penalizes recipes slower than the threshold.
        - Budget preference uses ingredient count as a proxy.
        - Repetition penalties reduce similar ingredients/dish types vs. prior day.
    """
    score = 0.0
    preferences = parsed.preferences or []

    # Build a searchable text surface for soft preference matches.
    recipe_text = " ".join(
        [
            recipe.title or "",
            " ".join(recipe.ingredients or []),
            " ".join(recipe.dish_types or []),
            " ".join(recipe.diets or [])
        ]
    ).lower()

    # Soft boosts for direct preference keyword matches.
    for pref in preferences:
        pref_norm = pref.replace("-", " ").lower()
        if pref_norm and pref_norm in recipe_text:
            score += 1.0

    # Macro alignment: reward protein, penalize carbs.
    if PREFERENCE_HIGH_PROTEIN in preferences:
        score += min(2.5, (recipe.nutrition.protein or 0) / 20.0)
    if PREFERENCE_LOW_CARB in preferences:
        score -= min(2.5, (recipe.nutrition.carbs or 0) / 20.0)

    # Time alignment: penalize slow recipes when "quick" is requested.
    quick_threshold = _extract_quick_threshold(preferences)
    if quick_threshold is not None and recipe.ready_in_minutes:
        if recipe.ready_in_minutes > quick_threshold:
            score -= (recipe.ready_in_minutes - quick_threshold) / 10.0

    # Budget alignment: fewer ingredients roughly implies lower cost.
    if PREFERENCE_BUDGET in preferences:
        ingredient_count = len(recipe.ingredients or [])
        score += max(0, 6 - ingredient_count) * 0.2

    recent_ingredient_tokens = context.get("recent_ingredient_tokens", set())
    recent_dish_types = context.get("recent_dish_types", set())

    # Repetition penalty: reduce overlap with the previous day.
    if recent_ingredient_tokens:
        recipe_tokens = _ingredient_tokens(recipe.ingredients or [])
        if recipe_tokens:
            overlap = recipe_tokens.intersection(recent_ingredient_tokens)
            overlap_ratio = len(overlap) / max(1, len(recipe_tokens))
            score -= overlap_ratio * 2.0

    # Repetition penalty: avoid same dish types day-to-day.
    if recent_dish_types and recipe.dish_types:
        overlap_dish = set(recipe.dish_types).intersection(recent_dish_types)
        score -= 0.5 * len(overlap_dish)

    return score


def _ingredient_tokens(ingredients: Iterable[str]) -> Set[str]:
    """Normalize ingredient strings into a set of tokens for overlap checks."""
    tokens: Set[str] = set()
    for ingredient in ingredients:
        for token in re.split(r'[^a-zA-Z]+', ingredient.lower()):
            if len(token) >= 3:
                tokens.add(token)
    return tokens


def _extract_quick_threshold(preferences: Iterable[str]) -> Optional[int]:
    """Return a quick-cook threshold in minutes if specified in preferences."""
    for pref in preferences:
        match = re.search(r'under-(\d+)-minutes', pref)
        if match:
            return int(match.group(1))
    if PREFERENCE_QUICK in preferences:
        return 20
    return None
