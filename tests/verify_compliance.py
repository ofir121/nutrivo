import unittest
import logging
from unittest.mock import MagicMock, patch
from app.services.parser_service import QueryParser
from app.services.planner import MealPlanner
from app.models import MealPlanRequest, ParsedQuery

logger = logging.getLogger(__name__)

class TestCompliance(unittest.TestCase):
    def test_parser_preference_extraction(self):
        # Mock dependencies?
        # Actually parser_service imports ai_service inside the method or globally.
        # It imports inside _try_llm_enhancement: from app.services.ai_service import ai_service
        
        with patch('app.services.ai_service.ai_service.enhance_query') as mock_enhance:
            mock_enhance.return_value = {
                "diets": ["vegetarian"],
                "preferences": ["high-protein"],
                "clarified_intent": "high protein vegetarian plan"
            }
            
            parser = QueryParser()
            result = parser.parse("2-day vegetarian plan with high protein")
            
            logger.debug(f"Parsed preferences: {result.preferences}")
            self.assertIn("high-protein", result.preferences)
            self.assertIn("vegetarian", result.diets)

    def test_planner_compliance_output(self):
        planner = MealPlanner()
        
        # Mock parser to avoid LLM call in planner
        with patch('app.services.planner.parser_service.parse') as mock_parse:
            mock_parse.return_value = ParsedQuery(
                days=2,
                diets=["vegetarian"],
                preferences=["high-protein"]
            )
            
            # Mock conflict resolver and recipe service to avoid errors/DB calls
            with patch('app.services.planner.conflict_resolver.validate'):
                with patch('app.services.planner.recipe_service.get_recipes') as mock_get_recipes:
                    # Return distinct mock recipes to avoid "ran out of unique recipes" loop issues if logic is complex
                    from app.models import Recipe, NutritionalInfo
                    
                    def make_recipe(id, protein):
                        return Recipe(
                            id=id, title=f"Recipe {id}", ready_in_minutes=30, servings=2,
                            ingredients=["a"], instructions=["step"], diets=["vegetarian"],
                            dish_types=["main course"],
                            nutrition=NutritionalInfo(calories=500, protein=protein, carbs=50, fat=20),
                            source_api="local"
                        )

                    # Return enough recipes for 2 days * 3 meals = 6 recipes
                    # Give them different protein levels to test sorting?
                    # The planner logic slices top 3.
                    mock_recipes = [
                        make_recipe("1", 10),
                        make_recipe("2", 30), # High protein
                        make_recipe("3", 5),
                        make_recipe("4", 40), # High
                        make_recipe("5", 25),
                        make_recipe("6", 15)
                    ]
                    mock_get_recipes.return_value = mock_recipes
                    
                    req = MealPlanRequest(query="dummy")
                    response = planner.generate_meal_plan(req)
                    
                    logger.debug(f"Dietary compliance: {response.summary.dietary_compliance}")
                    self.assertIn("high-protein", response.summary.dietary_compliance)
                    self.assertIn("vegetarian", response.summary.dietary_compliance)

if __name__ == '__main__':
    unittest.main()
