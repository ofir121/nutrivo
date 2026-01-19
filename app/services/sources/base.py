from abc import ABC, abstractmethod
from typing import List, Optional
from app.models import Recipe

class RecipeSource(ABC):
    name: str = "Unknown"

    @abstractmethod
    def get_recipes(self, diets: List[str], exclude: List[str], meal_type: Optional[str], estimate_prep_time: bool = False) -> List[Recipe]:
        """
        Fetch recipes matching the criteria.
        Must return a list of canonical `Recipe` objects.
        """
        pass
