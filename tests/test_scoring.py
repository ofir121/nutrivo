from app.models import ParsedQuery, Recipe, NutritionalInfo
from app.services.scoring import score_recipe


def make_recipe(recipe_id, protein, carbs, minutes, ingredients=None, dish_types=None):
    return Recipe(
        id=recipe_id,
        title=f"Recipe {recipe_id}",
        ready_in_minutes=minutes,
        servings=2,
        ingredients=ingredients or ["chicken breast", "salt"],
        instructions=["step"],
        diets=[],
        dish_types=dish_types or ["main course"],
        nutrition=NutritionalInfo(calories=500, protein=protein, carbs=carbs, fat=10),
        source_api="local"
    )


def test_score_respects_macros_and_quick_time():
    parsed = ParsedQuery(
        days=3,
        diets=[],
        calories=None,
        exclude=[],
        preferences=["high-protein", "low-carb", "quick", "under-15-minutes"],
        meals_per_day=3
    )
    fast_high_protein = make_recipe("1", protein=40, carbs=10, minutes=10)
    slow_low_protein = make_recipe("2", protein=10, carbs=60, minutes=45)

    context = {"recent_ingredient_tokens": set(), "recent_dish_types": set()}
    fast_score = score_recipe(fast_high_protein, parsed, context)
    slow_score = score_recipe(slow_low_protein, parsed, context)

    assert fast_score > slow_score


def test_score_penalizes_repetition():
    parsed = ParsedQuery(
        days=3,
        diets=[],
        calories=None,
        exclude=[],
        preferences=[],
        meals_per_day=3
    )
    recipe = make_recipe("1", protein=20, carbs=20, minutes=20, ingredients=["tomato", "basil"])
    context = {
        "recent_ingredient_tokens": {"tomato", "basil"},
        "recent_dish_types": {"main course"}
    }
    repeated_score = score_recipe(recipe, parsed, context)
    baseline_score = score_recipe(recipe, parsed, {"recent_ingredient_tokens": set(), "recent_dish_types": set()})

    assert repeated_score < baseline_score
