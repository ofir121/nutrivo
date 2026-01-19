import random
import uuid
import time
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
        total_start = time.time()
        
        # 1. Parse the query (Deterministic extraction)
        parse_start = time.time()
        parsed = parser_service.parse(request.query)
        parse_time = time.time() - parse_start
        print(f"⏱️  Query parsing: {parse_time:.2f}s")
        
        # 2. Check for Conflicts (e.g. "vegan" + "pescatarian")
        # Raises 409 if invalid
        conflict_resolver.validate(parsed)
        
        print(f"\n🍳 Generating {parsed.days}-day meal plan...\n")
        
        # 3. Generate Plan
        meal_plan = []
        meals_to_refine = []  # List of (Meal object, raw_instructions_list)
        
        used_recipes = set() # For diversity logic
        
        today = datetime.now().date()
        
        for day_offset in range(parsed.days):
             current_date = (today + timedelta(days=day_offset + 1)).isoformat()
             daily_meals = []
             
             # Try to find a recipe for each type: breakfast, lunch, dinner
             for m_type in ["breakfast", "lunch", "dinner"]:
                 
                 # Fetch candidates matching HARD CONSTRAINTS (Diet + Exclusions)
                 # DISABLE per-recipe AI estimation here to batch it later
                 candidates = recipe_service.get_recipes(
                     diets=parsed.diets,
                     exclude=parsed.exclude,
                     meal_type=m_type,
                     estimate_prep_time=False, 
                     sources=request.sources
                 )

                 
                 # Score/Filter for Soft Constraints & Diversity
                 available_candidates = [r for r in candidates if r.id not in used_recipes]
                 
                 # Filter by Preferences (e.g. high-protein)
                 # Normalize preferences
                 if parsed.preferences:
                     prefs = [p.lower().replace("-", " ") for p in parsed.preferences]
                     if "high protein" in prefs:
                         # Sort by protein descending and take top 50% or top 3
                         # Ensure we have candidates with protein info
                         available_candidates.sort(key=lambda r: r.nutrition.protein, reverse=True)
                         # Take top 3 to ensure high protein, but maintain slight randomness
                         if len(available_candidates) > 3:
                             available_candidates = available_candidates[:3]
                
                 # Fallback: if we ran out of unique recipes, reuse from candidates
                 if not available_candidates:
                     available_candidates = candidates
                 
                 if available_candidates:
                     recipe = random.choice(available_candidates)
                     used_recipes.add(recipe.id)
                     
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
                     
                     if active_ai:
                         meals_to_refine.append((meal, recipe.instructions))
                 else:
                     pass
 
             meal_plan.append(DailyPlan(
                 day=day_offset + 1,
                 date=current_date,
                 meals=daily_meals
             ))

        # 4. Batch Process with AI (One Call)
        if active_ai and meals_to_refine:
            print("\n🤖 Batch processing instructions/times with AI...")
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
        
        # Summary Compliance
        compliance = list(set(parsed.diets + parsed.exclude + parsed.preferences))
        
        summary = MealPlanSummary(
            total_meals=total_meals_count,
            dietary_compliance=compliance,
            estimated_cost="$45-60", # Mocked for now
            avg_prep_time=avg_prep
        )

        total_time = time.time() - total_start
        print(f"\n✅ Total meal plan generation: {total_time:.2f}s\n")
        
        return MealPlanResponse(
            meal_plan_id=str(uuid.uuid4()),
            duration_days=parsed.days,
            generated_at=datetime.now().isoformat(),
            clarified_intent=parsed.clarified_intent,
            preferences=parsed.preferences,
            meal_plan=meal_plan,
            summary=summary
        )


planner = MealPlanner()
