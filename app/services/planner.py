import random
import uuid
from datetime import datetime, timedelta
from app.models import MealPlanRequest, MealPlanResponse, DailyPlan, MealPlanSummary, Meal, NutritionalInfo
from app.services.parser_service import parser_service
# Helper to access ai_service instance if needed, or import directly if preferred
try:
    from app.services.ai_service import ai_service as active_ai
except ImportError:
    active_ai = None
from app.services.recipe_service import recipe_service
from app.services.conflict_resolver import conflict_resolver

class MealPlanner:
    def generate_meal_plan(self, request: MealPlanRequest) -> MealPlanResponse:
        # 1. Parse the query (Deterministic extraction)
        parsed = parser_service.parse(request.query)
        
        # 2. Check for Conflicts (e.g. "vegan" + "pescatarian")
        # Raises 409 if invalid
        conflict_resolver.validate(parsed)
        
        # 3. Generate Plan
        meal_plan = []
        total_meals_count = 0
        total_prep_time_mins = 0
        
        used_recipes = set() # For diversity logic
        
        today = datetime.now().date()
        
        for day_offset in range(parsed.days):
             current_date = (today + timedelta(days=day_offset + 1)).isoformat()
             daily_meals = []
             
             # Try to find a recipe for each type: breakfast, lunch, dinner
             for m_type in ["breakfast", "lunch", "dinner"]:
                 
                 # Fetch candidates matching HARD CONSTRAINTS (Diet + Exclusions)
                 candidates = recipe_service.get_recipes(
                     diets=parsed.diets,
                     exclude=parsed.exclude,
                     meal_type=m_type
                 )
                 print(f"DEBUG: For {m_type}, got {len(candidates)} candidates. Type: {type(candidates[0] if candidates else 'N/A')}")
                 
                 # Score/Filter for Soft Constraints & Diversity
                 # Basic Logic: Remove recently used recipes to ensure variety
                 available_candidates = [r for r in candidates if r.id not in used_recipes]
                 
                 # Fallback: if we ran out of unique recipes, reuse from candidates
                 if not available_candidates:
                     available_candidates = candidates
                 
                 if available_candidates:
                     recipe = random.choice(available_candidates)
                     used_recipes.add(recipe.id)
                     
                     # Convert to Meal model
                     daily_meals.append(Meal(
                         meal_type=m_type,
                         recipe_name=recipe.title,
                         description=f"A delicious {m_type}.",
                         ingredients=recipe.ingredients,
                         nutritional_info=recipe.nutrition,
                         preparation_time=f"{recipe.ready_in_minutes} mins",
                         instructions=active_ai.format_instructions(recipe.instructions) if active_ai else recipe.instructions,
                         source=f"{recipe.source_api}"
                     ))
                     
                     # Update Summary Stats
                     total_meals_count += 1
                     total_prep_time_mins += recipe.ready_in_minutes
                 else:
                     # No recipe found logic
                     # Ideally return a generic placeholder or raise error if strict
                     pass
 
             meal_plan.append(DailyPlan(
                 day=day_offset + 1,
                 date=current_date,
                 meals=daily_meals
             ))

        # 4. Create Summary
        avg_prep = "0 mins"
        if total_meals_count > 0:
            avg_prep = f"{total_prep_time_mins // total_meals_count} mins"
        
        # Summary Compliance
        compliance = list(set(parsed.diets + parsed.exclude))
        
        summary = MealPlanSummary(
            total_meals=total_meals_count,
            dietary_compliance=compliance,
            estimated_cost="$45-60", # Mocked for now
            avg_prep_time=avg_prep
        )

        return MealPlanResponse(
            meal_plan_id=str(uuid.uuid4()),
            duration_days=parsed.days,
            generated_at=datetime.now().isoformat(),
            clarified_intent=parsed.clarified_intent,
            meal_plan=meal_plan,
            summary=summary
        )


planner = MealPlanner()
