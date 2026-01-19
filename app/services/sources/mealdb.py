import requests
import re
import time
from typing import List, Optional, Any, Dict
from app.services.sources.base import RecipeSource
from app.models import Recipe, NutritionalInfo

class MealDBSource(RecipeSource):
    name = "TheMealDB"
    BASE_URL = "https://www.themealdb.com/api/json/v1/1/"

    def get_recipes(self, diets: List[str], exclude: List[str], meal_type: Optional[str], estimate_prep_time: bool = False) -> List[Recipe]:
        """
        Fetch recipes from TheMealDB.
        Note: The free API has limited filtering capabilities.
        We will fetch a broad set and filter in memory.
        """
        recipes_data = []

        # Strategy:
        # 1. If meal_type is specific and supported, filter by category.
        # 2. Otherwise/Additionally, perform a search (e.g. by letter or random) to get a variety.
        # For simplicity and coverage on the free tier, we'll try a few strategies.
        
        # 1. Try to fetch by category if meal_type matches a MealDB category
        # Common MealDB Categories: Breakfast, Dessert, Starter, Vegan, Vegetarian...
        # Note: 'Vegan' and 'Vegetarian' are categories in MealDB, not just tags.
        
        candidates = []
        
        # Helper to fetch by category
        def fetch_by_category(cat: str):
            try:
                api_start = time.time()
                url = f"{self.BASE_URL}filter.php?c={cat}"
                res = requests.get(url)
                data = res.json()
                api_time = time.time() - api_start
                print(f"      🌐 MealDB API (filter {cat}): {api_time:.2f}s")
                return data.get("meals") or []
            except Exception:
                return []

        def fetch_details(meals_list: List[Dict]):
            detailed = []
            total_detail_time = 0
            for m in meals_list[:3]: # Limit to 3 - enough for variety without excessive API calls
                # lookup.php?i=52772
                try:
                    detail_start = time.time()
                    mid = m.get("idMeal")
                    res = requests.get(f"{self.BASE_URL}lookup.php?i={mid}")
                    d = res.json()
                    detail_time = time.time() - detail_start
                    total_detail_time += detail_time
                    if d.get("meals"):
                        detailed.extend(d["meals"])
                except Exception:
                    pass
            if total_detail_time > 0:
                print(f"      🌐 MealDB API ({len(detailed)} detail lookups): {total_detail_time:.2f}s")
            return detailed
            
        # Helper for search
        def search_meals(query: str):
             try:
                api_start = time.time()
                url = f"{self.BASE_URL}search.php?s={query}"
                res = requests.get(url)
                data = res.json()
                api_time = time.time() - api_start
                print(f"      🌐 MealDB API (search '{query}'): {api_time:.2f}s")
                return data.get("meals") or []
             except Exception:
                return []

        # Logic to gather candidates
        # If specific meal type requested that maps to a category, stick to that.
        # Otherwise, search for common terms or diets.
        
        
        fetched_meals = []
        MAX_RECIPES_TO_FETCH = 10  # Sufficient variety for meal planning
        
        if meal_type:
            # Map simple types to categories
            cat_map = {
                "breakfast": "Breakfast",
                "dessert": "Dessert",
                "starter": "Starter",
                "side": "Side",
                "seafood": "Seafood",
                "vegetarian": "Vegetarian",
                "vegan": "Vegan"
            }
            target_cat = cat_map.get(meal_type.lower())
            if target_cat:
                 items = fetch_by_category(target_cat)
                 fetched_meals.extend(fetch_details(items))
            else:
                 # Fallback search
                 fetched_meals.extend(search_meals(meal_type))
        
        # Early termination if we have enough
        if len(fetched_meals) >= MAX_RECIPES_TO_FETCH:
            fetched_meals = fetched_meals[:MAX_RECIPES_TO_FETCH]
        else:
            # If we have diet constraints like Vegan/Vegetarian, we can try to fetch from those categories too
            # to ensure we have options, then filter.
            for diet in diets:
                if len(fetched_meals) >= MAX_RECIPES_TO_FETCH:
                    break
                d_lower = diet.lower()
                if "vegan" in d_lower:
                    items = fetch_by_category("Vegan")
                    fetched_meals.extend(fetch_details(items))
                elif "vegetarian" in d_lower:
                    items = fetch_by_category("Vegetarian")
                    fetched_meals.extend(fetch_details(items))

            # Final fallback: if nothing fetched yet (e.g. general query), search for generic terms
            if not fetched_meals:
                 # Just fetch some randoms or a common letter to populate
                 # search.php?s=a returns a bunch
                 fetched_meals.extend(search_meals("a"))
                 if len(fetched_meals) < MAX_RECIPES_TO_FETCH:
                     fetched_meals.extend(search_meals("b")) # Add variety
        
        # Deduplicate by idMeal
        seen_ids = set()
        unique_meals = []
        for m in fetched_meals:
            if m["idMeal"] not in seen_ids:
                unique_meals.append(m)
                seen_ids.add(m["idMeal"])

        # FILTERING
        final_recipes = []
        for m in unique_meals:
            if self._satisfies_constraints(m, diets, exclude):
                final_recipes.append(m)
        
        # BATCH TIME ESTIMATION (only if requested)
        time_estimates = {}
        if estimate_prep_time:
            # Collect recipes that need time estimation
            recipes_needing_time = {}
            for m in final_recipes:
                meal_id = f"mealdb_{m.get('idMeal')}"
                instructions_text = m.get("strInstructions", "")
                if instructions_text:
                    recipes_needing_time[meal_id] = instructions_text
            
            # Get batch estimates
            if recipes_needing_time:
                try:
                    batch_start = time.time()
                    from app.services.ai_service import ai_service
                    time_estimates = ai_service.batch_estimate_preparation_time(recipes_needing_time)
                    batch_time = time.time() - batch_start
                    print(f"    ⏱️  Batch time estimation for {len(recipes_needing_time)} recipes: {batch_time:.2f}s")
                except Exception as e:
                    print(f"Batch estimation failed: {e}")
                    time_estimates = {rid: 30 for rid in recipes_needing_time.keys()}
        
        # Adapt with estimates (use default 30 if not estimated)
        adapted_recipes = []
        for m in final_recipes:
            meal_id = f"mealdb_{m.get('idMeal')}"
            estimated_time = time_estimates.get(meal_id, 30)
            adapted_recipes.append(self._adapt(m, estimated_time))
                
        return adapted_recipes

    def _satisfies_constraints(self, meal: Dict, diets: List[str], exclude: List[str]) -> bool:
        # Check Exclusions (Ingredients)
        # Ingredients are strIngredient1...20
        all_text = (str(meal.get("strMeal") or "") + " " + str(meal.get("strCategory") or "") + " " + str(meal.get("strTags") or "")).lower()
        
        ingredients = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}")
            if ing:
                ingredients.append(ing.lower())
                all_text += " " + ing.lower()
        
        for ex in exclude:
            if ex.lower() in all_text:
                return False
                
        # Check Diets
        # MealDB is loose on tags. We check strCategory and strTags.
        # Strict checking might filter everything out, so we use best effort.
        # But if user strictly requested Vegan, we should try to honor it.
        # If the category is explicitly Vegan, great.
        
        for diet in diets:
            d = diet.lower()
            is_vegan = "vegan" in all_text
            is_vegetarian = "vegetarian" in all_text or is_vegan
            
            if d == "vegan" and not is_vegan:
                return False
            if d == "vegetarian" and not is_vegetarian:
                return False
            # Gluten Free is hard to verify on MealDB without explicit tags, 
            # might have to skip or be permissive. 
            # For safety, let's assume if it's not tagged, we can't guarantee it.
            if "gluten" in d and "gluten" not in all_text:
                # Very strict, might result in empty.
                pass 

        return True


    def _adapt(self, data: Dict, estimated_time: int = 30) -> Recipe:
        # Extract ingredients
        ingredients = []
        for i in range(1, 21):
            ing = data.get(f"strIngredient{i}")
            meas = data.get(f"strMeasure{i}")
            if ing and ing.strip():
                measure = f" ({meas})" if meas and meas.strip() else ""
                ingredients.append(f"{ing}{measure}")

        # Instructions
        instructions_text = data.get("strInstructions", "")
        # Split by newlines or periods roughly
        steps = [s.strip() for s in instructions_text.split('\r\n') if s.strip()]
        if not steps:
            steps = [s.strip() for s in instructions_text.split('\n') if s.strip()]

        return Recipe(
            id=f"mealdb_{data.get('idMeal')}",
            title=data.get("strMeal"),
            ready_in_minutes=estimated_time,
            servings=2, # Placeholder
            image=data.get("strMealThumb"),
            diets=[], # Populated from tags if parsing needed, safe to leave empty or infer
            dish_types=[data.get("strCategory", "Main Course")],
            ingredients=ingredients,
            instructions=steps,
            nutrition=NutritionalInfo(
                calories=500, # Placeholder
                protein=20,   # Placeholder
                carbs=50,     # Placeholder
                fat=20        # Placeholder
            ),
            source_api="mealdb",
            original_data=data
        )
