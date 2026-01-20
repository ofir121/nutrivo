import uuid
import time
from datetime import datetime, timedelta
from app.models import MealPlanRequest, MealPlanResponse, DailyPlan, MealPlanSummary, Meal, NutritionalInfo
from app.services.parser_service import parser_service
from app.core.logging_config import get_logger
from app.services.scoring import score_recipe

logger = get_logger(__name__)
# Helper to access ai_service instance if needed, or import directly if preferred
try:
    from app.services.ai_service import ai_service as active_ai
except ImportError:
    active_ai = None
from app.services.recipe_service import recipe_service
from app.services.conflict_resolver import conflict_resolver

class MealPlanner:
    def generate_meal_plan(self, request: MealPlanRequest) -> MealPlanResponse:
        total_start = time.time()
        
        # 1. Parse the query (Deterministic extraction)
        parse_start = time.time()
        parsed = parser_service.parse(request.query)
        parse_time = time.time() - parse_start
        logger.info(f"⏱️  Query parsing: {parse_time:.2f}s")
        
        # 2. Check for Conflicts (e.g. "vegan" + "pescatarian")
        # Raises 409 if invalid
        conflict_resolver.validate(parsed)
        
        logger.info(f"🍳 Generating {parsed.days}-day meal plan...")
        
        # 3. Generate Plan
        meal_plan = []
        meals_to_refine = []  # List of (Meal object, raw_instructions_list)
        warnings = []
        defaults_applied = []
        
        used_recipes = set() # For diversity logic
        
        today = datetime.now().date()
        prev_day_ingredient_tokens = set()
        prev_day_dish_types = set()
        
        for day_offset in range(parsed.days):
             current_date = (today + timedelta(days=day_offset + 1)).isoformat()
             daily_meals = []
             used_today = set()
             day_ingredient_tokens = set()
             day_dish_types = set()
             meal_types = ["breakfast", "lunch", "dinner"]
             if parsed.meals_per_day > 3:
                 meal_types.append("snack")
             
             # Try to find a recipe for each type: breakfast, lunch, dinner
             for m_type in meal_types:
                 
                 # Fetch candidates matching HARD CONSTRAINTS (Diet + Exclusions)
                 # DISABLE per-recipe AI estimation here to batch it later
                 candidates = recipe_service.get_recipes(
                     diets=parsed.diets,
                     exclude=parsed.exclude,
                     meal_type=m_type,
                     estimate_prep_time=request.estimate_prep_time, 
                     sources=request.sources
                 )
                 
                 # Score/Filter for Soft Constraints & Diversity
                 available_candidates = [r for r in candidates if r.id not in used_recipes]
                 context = {
                     "recent_ingredient_tokens": prev_day_ingredient_tokens,
                     "recent_dish_types": prev_day_dish_types
                 }
                 recipe = self._pick_best_recipe(available_candidates, parsed, context)
                 
                 # Fallback: if we ran out of unique recipes, reuse from candidates
                 if not recipe:
                     fallback_pool = [r for r in candidates if r.id not in used_today]
                     if not fallback_pool:
                         fallback_pool = candidates
                     recipe = self._pick_best_recipe(fallback_pool, parsed, context)
                     if recipe:
                         defaults_applied.append(f"Reused recipe pool for {m_type} on day {day_offset + 1}")
                 
                 if recipe:
                     used_recipes.add(recipe.id)
                     used_today.add(recipe.id)
                     
                     # Create Meal with raw instructions initially
                     meal = Meal(
                         meal_type=m_type,
                         recipe_name=recipe.title,
                         description=f"A delicious {m_type}.",
                         ingredients=recipe.ingredients,
                         nutritional_info=recipe.nutrition,
                         preparation_time=f"{recipe.ready_in_minutes} mins",
                         instructions=recipe.instructions,
                         source=f"{recipe.source_api}"
                     )
                     daily_meals.append(meal)
                     
                     day_ingredient_tokens.update(self._ingredient_tokens(recipe.ingredients))
                     day_dish_types.update(recipe.dish_types)
                     
                     if active_ai:
                         meals_to_refine.append((meal, recipe.instructions))
                 else:
                     warnings.append(f"No candidates found for {m_type} on day {day_offset + 1}")
 
             meal_plan.append(DailyPlan(
                 day=day_offset + 1,
                 date=current_date,
                 meals=daily_meals
             ))
             prev_day_ingredient_tokens = day_ingredient_tokens
             prev_day_dish_types = day_dish_types

        # 4. Batch Process with AI (One Call)
        if active_ai and meals_to_refine and request.estimate_prep_time:
            logger.info("🤖 Batch processing instructions/times with AI...")
            batch_input = {}
            temp_map = {} # map id -> meal object
            
            for idx, (meal_obj, raw_instr) in enumerate(meals_to_refine):
                tid = str(idx)
                # Join list of strings to text block
                text_block = "\n".join(raw_instr) if raw_instr else ""
                batch_input[tid] = text_block
                temp_map[tid] = meal_obj
                
            processed = active_ai.batch_process_recipes(batch_input, estimate_time=request.estimate_prep_time)
            
            # Apply updates
            for tid, data in processed.items():
                target_meal = temp_map.get(tid)
                if target_meal:
                    if data.get("instructions"):
                        target_meal.instructions = data["instructions"]
                    if request.estimate_prep_time and data.get("total_minutes"):
                        target_meal.preparation_time = f"{data['total_minutes']} mins"

        # 5. Create Summary (Recalculate stats after AI updates)
        total_meals_count = 0
        total_prep_time_mins = 0
        
        for daily in meal_plan:
            total_meals_count += len(daily.meals)
            for m in daily.meals:
                try:
                    # Parse "45 mins" -> 45
                    val = int(m.preparation_time.split()[0])
                    total_prep_time_mins += val
                except (ValueError, IndexError):
                    pass
            
        avg_prep = "0 mins"
        if total_meals_count > 0:
            avg_prep = f"{total_prep_time_mins // total_meals_count} mins"

        combined_preferences = []
        for item in parsed.preferences + parsed.diets:
            if item not in combined_preferences:
                combined_preferences.append(item)
        
        summary = MealPlanSummary(
            total_meals=total_meals_count,
            diets=parsed.diets,
            exclusions=parsed.exclude,
            preferences=combined_preferences,
            estimated_cost="$45-60",  # Mocked for now
            avg_prep_time=avg_prep,
            warnings=warnings,
            defaults_applied=defaults_applied
        )

        total_time = time.time() - total_start
        logger.info(f"✅ Total meal plan generation: {total_time:.2f}s")
        
        return MealPlanResponse(
            meal_plan_id=str(uuid.uuid4()),
            duration_days=parsed.days,
            generated_at=datetime.now().isoformat(),
            clarified_intent=parsed.clarified_intent,
            preferences=combined_preferences,
            meal_plan=meal_plan,
            summary=summary
        )

    def _pick_best_recipe(self, candidates, parsed, context):
        if not candidates:
            return None
        scored = []
        for recipe in candidates:
            scored.append((score_recipe(recipe, parsed, context), recipe))
        scored.sort(key=lambda item: (-item[0], item[1].id))
        return scored[0][1]

    def _ingredient_tokens(self, ingredients):
        tokens = set()
        for ingredient in ingredients or []:
            for token in ingredient.lower().split():
                if len(token) >= 3:
                    tokens.add(token)
        return tokens


planner = MealPlanner()
