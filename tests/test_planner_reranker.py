from app.models import MealPlanRequest, NutritionalInfo, Recipe
from app.services.planner import MealPlanner, recipe_service, reranker_service


def make_recipe(recipe_id: str) -> Recipe:
    return Recipe(
        id=recipe_id,
        title=f"Recipe {recipe_id}",
        ready_in_minutes=15,
        servings=2,
        ingredients=["chicken breast", "salt", "olive oil"],
        instructions=["step"],
        diets=[],
        dish_types=["main course"],
        nutrition=NutritionalInfo(calories=400, protein=30, carbs=20, fat=10),
        source_api="local"
    )


def test_planner_calls_reranker(monkeypatch):
    monkeypatch.setenv("RERANK_ENABLED", "true")
    monkeypatch.setenv("RERANK_TOP_K", "2")
    monkeypatch.setenv("RERANK_MODE", "per_meal")

    recipe_a = make_recipe("1")
    recipe_b = make_recipe("2")

    def fake_get_recipes(diets=None, exclude=None, meal_type=None, sources=None):
        return [recipe_a, recipe_b]

    calls = {"count": 0}

    def fake_rerank(**kwargs):
        calls["count"] += 1
        return kwargs["candidates"][-1].id

    monkeypatch.setattr(recipe_service, "get_recipes", fake_get_recipes)
    monkeypatch.setattr(reranker_service, "rerank", fake_rerank)

    planner = MealPlanner()
    response = planner.generate_meal_plan(
        MealPlanRequest(query="1-day meal plan", sources=["Local"])
    )

    assert calls["count"] >= 1
    first_meal = response.meal_plan[0].meals[0]
    assert first_meal.recipe_name == recipe_b.title
