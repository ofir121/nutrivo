from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_openapi_docs_contains_generate_meal_plan():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()

    paths = data.get("paths", {})
    assert "/api/generate-meal-plan" in paths
    assert "post" in paths["/api/generate-meal-plan"]
