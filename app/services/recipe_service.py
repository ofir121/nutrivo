from typing import List, Optional
from app.services.sources.base import RecipeSource
from app.services.sources.local import LocalSource
from app.models import Recipe

class RecipeService:
    def __init__(self):
        self.sources: List[RecipeSource] = []
        
        # Initialize sources
        self.sources.append(LocalSource())

    def get_recipes(self, diets: List[str] = [], exclude: List[str] = [], meal_type: Optional[str] = None) -> List[Recipe]:
        """
        Aggregates recipes from all registered sources.
        Returns a list of Recipe objects.
        """
        all_recipes = []
        for source in self.sources:
            try:
                recipes = source.get_recipes(diets, exclude, meal_type)
                all_recipes.extend(recipes)
            except Exception as e:
                print(f"Error fetching from source {source}: {e}")
                
        return all_recipes

recipe_service = RecipeService()
