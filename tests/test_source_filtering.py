from app.services.recipe_service import recipe_service
from unittest.mock import MagicMock

def test_source_filtering():
    # Setup mocks
    mock_local = MagicMock()
    mock_local.name = "Local"
    mock_local.get_recipes.return_value = []
    
    mock_mealdb = MagicMock()
    mock_mealdb.name = "TheMealDB"
    mock_mealdb.get_recipes.return_value = []
    
    # Inject mocks
    original_sources = recipe_service.sources
    recipe_service.sources = [mock_local, mock_mealdb]
    
    try:
        # Test 1: Only Local
        recipe_service.cache.clear()
        recipe_service.get_recipes(sources=["Local"])
        mock_local.get_recipes.assert_called_once()
        mock_mealdb.get_recipes.assert_not_called()
    
        mock_local.reset_mock()
        mock_mealdb.reset_mock()
    
        # Test 2: Only TheMealDB
        recipe_service.cache.clear()
        recipe_service.get_recipes(sources=["TheMealDB"])
        mock_local.get_recipes.assert_not_called()
        mock_mealdb.get_recipes.assert_called_once()
    
        mock_local.reset_mock()
        mock_mealdb.reset_mock()
    
        # Test 3: Both
        recipe_service.cache.clear()
        recipe_service.get_recipes(sources=["Local", "TheMealDB"])
        mock_local.get_recipes.assert_called_once()
        mock_mealdb.get_recipes.assert_called_once()
    
    finally:
        # Restore
        recipe_service.sources = original_sources
