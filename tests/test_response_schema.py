from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_generate_meal_plan_response_schema():
    response = client.post(
        "/api/generate-meal-plan",
        json={"query": "Create a 3-day vegetarian meal plan"}
    )
    assert response.status_code == 200
    data = response.json()

    assert "meal_plan_id" in data
    assert "duration_days" in data
    assert "generated_at" in data
    assert "meal_plan" in data
    assert "summary" in data

    summary = data["summary"]
    assert "total_meals" in summary
    assert "dietary_compliance" in summary
    assert "estimated_cost" in summary
    assert "avg_prep_time" in summary

    assert isinstance(data["meal_plan"], list)
    if data["meal_plan"]:
        day = data["meal_plan"][0]
        assert "day" in day
        assert "date" in day
        assert "meals" in day
        if day["meals"]:
            meal = day["meals"][0]
            assert "meal_type" in meal
            assert "recipe_name" in meal
            assert "description" in meal
            assert "ingredients" in meal
            assert "nutritional_info" in meal
            assert "preparation_time" in meal
            assert "instructions" in meal
            assert "source" in meal
