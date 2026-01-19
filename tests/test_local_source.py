import pytest
import os
import json
from unittest.mock import MagicMock, patch
from app.services.sources.local import LocalSource

TEST_DATA_FILE = "tests/test_recipes.json"

@pytest.fixture
def mock_local_data():
    data = [
        {
            "id": 1,
            "title": "Recipe with time",
            "readyInMinutes": 45,
            "servings": 2,
            "diets": ["vegetarian"],
            "extendedIngredients": [{"original": "carrot"}],
            "analyzedInstructions": [{"steps": [{"step": "Cook it."}]}],
            "nutrition": {"nutrients": []}
        },
        {
            "id": 2,
            "title": "Recipe without time",
            "readyInMinutes": 0,
            "servings": 2,
            "diets": ["vegan"],
            "extendedIngredients": [{"original": "lettuce"}],
            "analyzedInstructions": [{"steps": [{"step": "Toss it."}]}],
            "nutrition": {"nutrients": []}
        }
    ]
    with open(TEST_DATA_FILE, "w") as f:
        json.dump(data, f)
    yield TEST_DATA_FILE
    if os.path.exists(TEST_DATA_FILE):
        os.remove(TEST_DATA_FILE)

def test_local_source_uses_existing_time(mock_local_data):
    source = LocalSource(TEST_DATA_FILE)
    recipes = source.get_recipes(diets=[], exclude=[], meal_type=None)
    
    r1 = next(r for r in recipes if r.id == "1")
    assert r1.ready_in_minutes == 45


def test_local_source_batch_estimates_missing_times(mock_local_data):
    # Mock AI service
    with patch("app.services.ai_service.ai_service") as mock_ai:
        # Setup batch response
        mock_ai.batch_estimate_preparation_time.return_value = {"2": 15}
        
        source = LocalSource(TEST_DATA_FILE)
        recipes = source.get_recipes(diets=[], exclude=[], meal_type=None, estimate_prep_time=True)
        
        r1 = next(r for r in recipes if r.id == "1")
        r2 = next(r for r in recipes if r.id == "2")
        
        # Recipe 1 should use existing time
        assert r1.ready_in_minutes == 45
        
        # Recipe 2 should use batch estimated time
        assert r2.ready_in_minutes == 15
        
        # Verify batch call was made (not individual calls)
        mock_ai.batch_estimate_preparation_time.assert_called_once()
        # Verify it was called with recipe 2's instructions
        call_args = mock_ai.batch_estimate_preparation_time.call_args[0][0]
        assert "2" in call_args
