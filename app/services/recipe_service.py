from typing import List, Optional
from app.services.sources.base import RecipeSource
from app.services.sources.local import LocalSource
from app.models import Recipe
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class RecipeService:
    def __init__(self):
        self.sources: List[RecipeSource] = []
        
        # Initialize sources
        self.sources.append(LocalSource())
        from app.services.sources.mealdb import MealDBSource
        self.sources.append(MealDBSource())

    def get_recipes(self, diets: List[str] = [], exclude: List[str] = [], meal_type: Optional[str] = None, sources: List[str] = None) -> List[Recipe]:
        """
        Aggregates recipes from all registered sources.
        Returns a list of Recipe objects.
        """
        all_recipes = []
        # Default to all if not specified (or should it be default to Local? The request model handles default)
        # If sources is None or empty, we might want to default to something, but let's assume caller provides it.
        # But for safety:
        active_source_names = sources if sources else ["Local"]
        
        for source in self.sources:
            if source.name in active_source_names:
                try:
                    recipes = source.get_recipes(diets, exclude, meal_type)
                    all_recipes.extend(recipes)
                except Exception as e:
                    logger.error(f"Error fetching from source {source}: {e}")
                
        return all_recipes

recipe_service = RecipeService()
