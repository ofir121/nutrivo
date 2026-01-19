import json
import os
import time
from typing import List, Optional, Dict
from app.services.sources.base import RecipeSource
from app.models import Recipe, NutritionalInfo
from app.core.rules import DIET_DEFINITIONS, INGREDIENT_SYNONYMS
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class LocalSource(RecipeSource):
    name = "Local"
    
    def __init__(self, file_path: str = "data/mock_recipes.json"):
        self.recipes = self._load_data(file_path)

    def _load_data(self, file_path: str) -> List[dict]:
        if not os.path.exists(file_path):
            logger.warning(f"{file_path} not found.")
            return []
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error decoding {file_path}")
            return []

    def get_recipes(self, diets: List[str], exclude: List[str], meal_type: Optional[str], estimate_prep_time: bool = False) -> List[Recipe]:
        """
        Filters the Spoonacular-formatted local data and adapts it to our canonical Recipe model.
        """
        filtered_data = self.recipes

        # 1. Filter by Diet (Hard Constraint)
        for diet in diets:
             # Need to map our internal diet keys (vegan) to Spoonacular's (vegan, vegetarian, gluten free)
             # Spoonacular uses spaces usually "gluten free". Our key is "gluten-free".
             # Simple normalization: check if diet key is effectively present
             
             # Normalized check: 
             # If req diet is "gluten-free", we check if "gluten free" or "gluten-free" is in diets list.
             
             # Also allow soft matching from our rules engine definitions if needed.
             # For now, strict string matching with slight normalization.
             
             filtered_data = [
                 r for r in filtered_data 
                 if self._matches_diet(r.get("diets", []), diet)
             ]

        # 2. Filter by Exclusions (Hard Constraint)
        if exclude:
            filtered_data = [
                r for r in filtered_data 
                if not self._contains_excluded(r, exclude)
            ]


        # 3. Filter by Meal Type
        if meal_type:
            filtered_data = [
                r for r in filtered_data 
                if self._matches_meal_type(r.get("dishTypes", []), meal_type)
            ]

        # 4. Batch Time Estimation (only if requested)
        time_estimates = {}
        if estimate_prep_time:
            # Collect recipes needing time estimation
            recipes_needing_time = {}
            for r in filtered_data:
                recipe_id = str(r.get("id"))
                if r.get("readyInMinutes", 0) <= 0:
                    # Extract instructions
                    steps = []
                    if r.get("analyzedInstructions"):
                        for section in r["analyzedInstructions"]:
                            for step in section.get("steps", []):
                                steps.append(step.get("step", ""))
                    if steps:
                        recipes_needing_time[recipe_id] = " ".join(steps)
            
            # Get batch estimates
            if recipes_needing_time:
                try:
                    batch_start = time.time()
                    from app.services.ai_service import ai_service
                    time_estimates = ai_service.batch_estimate_preparation_time(recipes_needing_time)
                    batch_time = time.time() - batch_start

                except Exception as e:
                    logger.error(f"Batch estimation failed: {e}")
                    time_estimates = {rid: 30 for rid in recipes_needing_time.keys()}

        # 5. Adapt to Canonical Model with estimates
        return [self._adapt(r, time_estimates) for r in filtered_data]

    def _matches_diet(self, recipe_diets: List[str], req_diet: str) -> bool:
        # Normalize both sides
        r_diets = [d.lower().replace("-", " ") for d in recipe_diets]
        req = req_diet.lower().replace("-", " ")
        
        # 1. Direct match
        if req in r_diets: return True
        
        # 2. Hierarchy (Vegan implies Vegetarian)
        if req == "vegetarian" and "vegan" in r_diets: return True
        
        return False

    def _matches_meal_type(self, dish_types: List[str], req_type: str) -> bool:
        # Simple string match
        return req_type.lower() in [dt.lower() for dt in dish_types]

    def _contains_excluded(self, recipe: dict, exclude_list: List[str]) -> bool:
        # Check ingredients and title
        # Ingredients in Spoonacular are in "extendedIngredients" -> "original"
        ingredients_text = " ".join([i.get("original", "") for i in recipe.get("extendedIngredients", [])]).lower()
        title_text = recipe.get("title", "").lower()
        
        for ex in exclude_list:
             bad_words = [ex]
             if ex in INGREDIENT_SYNONYMS:
                 bad_words.extend(INGREDIENT_SYNONYMS[ex])
            
             for bw in bad_words:
                 if bw.lower() in ingredients_text or bw.lower() in title_text:
                     return True
        return False


    def _adapt(self, data: dict, time_estimates: Dict[str, int] = None) -> Recipe:
        if time_estimates is None:
            time_estimates = {}
            
        # Extract nutrition
        nutrients = {n["name"]: n["amount"] for n in data.get("nutrition", {}).get("nutrients", [])}
        
        # Extract instructions
        # "analyzedInstructions" -> [ { "steps": [ { "step": "..." } ] } ]
        steps = []
        if data.get("analyzedInstructions"):
            for section in data["analyzedInstructions"]:
                for step in section.get("steps", []):
                    steps.append(step.get("step", ""))
        
        # Get time - use existing if valid, otherwise use estimate
        recipe_id = str(data.get("id"))
        existing_time = data.get("readyInMinutes", 0)
        ready_time = existing_time if existing_time > 0 else time_estimates.get(recipe_id, 30)
        
        return Recipe(
            id=recipe_id,
            title=data.get("title"),
            ready_in_minutes=ready_time,
            servings=data.get("servings", 1),
            image=data.get("image"),
            diets=data.get("diets", []),
            dish_types=data.get("dishTypes", []),
            ingredients=[i.get("original") for i in data.get("extendedIngredients", [])],
            instructions=steps,
            nutrition=NutritionalInfo(
                calories=int(nutrients.get("Calories", 0)),
                protein=int(nutrients.get("Protein", 0)),
                carbs=int(nutrients.get("Carbohydrates", 0)),
                fat=int(nutrients.get("Fat", 0))
            ),
            source_api="local",
            original_data=data
        )
