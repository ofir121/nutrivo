from app.models import NutritionalInfo, Recipe
from app.services.reranker_service import RerankerService, ai_service


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


def test_reranker_returns_valid_selection(monkeypatch):
    service = RerankerService()
    candidates = [make_recipe("A"), make_recipe("B"), make_recipe("C")]
    scores = {"A": 1.0, "B": 2.0, "C": 0.5}

    monkeypatch.setattr(ai_service, "client", object())
    monkeypatch.setattr(
        service,
        "_call_llm",
        lambda prompt: {
            "selected_id": "B",
            "backup_id": None,
            "reasons": ["best fit"],
            "confidence": 0.7
        }
    )

    selected = service.rerank(
        query="test query",
        meal_slot="day1:breakfast",
        meal_type="breakfast",
        candidates=candidates,
        scores_by_id=scores,
        constraints={"meal_type": "breakfast"},
        history={},
        fallback_id="A"
    )
    assert selected == "B"


def test_reranker_falls_back_on_invalid_selection(monkeypatch):
    service = RerankerService()
    candidates = [make_recipe("A"), make_recipe("B"), make_recipe("C")]
    scores = {"A": 1.0, "B": 2.0, "C": 0.5}

    monkeypatch.setattr(ai_service, "client", object())
    monkeypatch.setattr(
        service,
        "_call_llm",
        lambda prompt: {
            "selected_id": "Z",
            "backup_id": None,
            "reasons": ["invalid"],
            "confidence": 0.2
        }
    )

    selected = service.rerank(
        query="test query",
        meal_slot="day1:breakfast",
        meal_type="breakfast",
        candidates=candidates,
        scores_by_id=scores,
        constraints={"meal_type": "breakfast"},
        history={},
        fallback_id="A"
    )
    assert selected == "A"
