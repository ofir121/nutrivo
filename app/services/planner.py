import uuid
import time
import os
from datetime import datetime, timedelta
from app.models import MealPlanRequest, MealPlanResponse, DailyPlan, MealPlanSummary, Meal, NutritionalInfo
from app.services.parser_service import parser_service
from app.core.logging_config import get_logger
from app.services.scoring import score_recipe

DEFAULT_MEAL_QUICK_MINUTES = 20

logger = get_logger(__name__)
from app.services.recipe_service import recipe_service
from app.services.conflict_resolver import conflict_resolver
from app.services.reranker_service import reranker_service

class MealPlanner:
    def __init__(self) -> None:
        self.rerank_enabled = os.getenv("RERANK_ENABLED", "true").lower() == "true"
        self.rerank_top_k = int(os.getenv("RERANK_TOP_K", "10"))
        self.rerank_mode = os.getenv("RERANK_MODE", "per_meal")

    def generate_meal_plan(self, request: MealPlanRequest) -> MealPlanResponse:
        """Generate a multi-day meal plan using deterministic scoring.

        Args:
            request: Meal plan request containing query and options.

        Returns:
            MealPlanResponse with a daily meal schedule and summary.
        """
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
        warnings = []
        defaults_applied = []
        
        used_recipes = set() # For diversity logic
        
        today = datetime.now().date()
        prev_day_ingredient_tokens = set()
        prev_day_dish_types = set()
        recent_recipe_history = []
        selected_titles = []
        selected_ingredients = set()
        selected_cuisines = set()
        
        rerank_enabled = (
            request.rerank_enabled
            if request.rerank_enabled is not None
            else self.rerank_enabled
        )

        for day_offset in range(parsed.days):
             current_date = (today + timedelta(days=day_offset + 1)).isoformat()
             daily_meals = []
             used_today = set()
             day_ingredient_tokens = set()
             day_dish_types = set()
             day_macros = {"protein": 0, "carbs": 0, "fat": 0}
             meal_types = ["breakfast", "lunch", "dinner"]
             if parsed.meals_per_day > 3:
                 meal_types.append("snack")
             
             recent_ids = set().union(*recent_recipe_history) if recent_recipe_history else set()

             # Try to find a recipe for each type: breakfast, lunch, dinner
             for m_type in meal_types:
                 
                 # Fetch candidates matching HARD CONSTRAINTS (Diet + Exclusions)
                 # DISABLE per-recipe AI estimation here to batch it later
                 candidates = recipe_service.get_recipes(
                     diets=parsed.diets,
                     exclude=parsed.exclude,
                     meal_type=m_type,
                     sources=request.sources
                 )

                 time_limit = self._extract_meal_time_limit(parsed.preferences, m_type)
                 time_limit_applied = False
                 if time_limit:
                     limited = [
                         r for r in candidates
                         if r.ready_in_minutes and r.ready_in_minutes <= time_limit
                     ]
                     if limited:
                         candidates = limited
                         time_limit_applied = True
                     else:
                         warnings.append(
                             f"No {m_type} recipes found under {time_limit} mins on day {day_offset + 1}; relaxing time constraint."
                         )
                 
                 # Score/Filter for Soft Constraints & Diversity
                 available_candidates = [r for r in candidates if r.id not in used_recipes]
                 context = {
                     "recent_ingredient_tokens": prev_day_ingredient_tokens,
                     "recent_dish_types": prev_day_dish_types
                 }
                 history = {
                     "previously_selected_titles": selected_titles[-12:],
                     "previously_selected_main_ingredients": sorted(selected_ingredients)[:20],
                     "cuisines_used": sorted(selected_cuisines)
                 }
                 meal_slot = f"day{day_offset + 1}:{m_type}"
                 constraints = {
                     "meal_type": m_type,
                     "diets": parsed.diets,
                     "exclude": parsed.exclude,
                     "time_limit_minutes": time_limit if time_limit_applied else None
                 }
                 recipe, reasons = self._pick_best_recipe(
                     available_candidates,
                     parsed,
                     context,
                     day_macros,
                     request.query,
                     meal_slot,
                     history,
                     constraints,
                     rerank_enabled
                 )
                 
                 # Fallback: if we ran out of unique recipes, reuse from candidates
                 if not recipe:
                     fallback_pool = [
                         r for r in candidates
                         if r.id not in used_today and r.id not in recent_ids
                     ]
                     if not fallback_pool:
                         fallback_pool = [r for r in candidates if r.id not in used_today]
                     if not fallback_pool:
                         fallback_pool = candidates
                     recipe, reasons = self._pick_best_recipe(
                         fallback_pool,
                         parsed,
                         context,
                         day_macros,
                         request.query,
                         meal_slot,
                         history,
                         constraints,
                         rerank_enabled
                     )
                     if recipe:
                         defaults_applied.append(f"Reused recipe pool for {m_type} on day {day_offset + 1}")
                 
                 if recipe:
                     used_recipes.add(recipe.id)
                     used_today.add(recipe.id)
                     
                     # Create Meal with formatted instructions
                     meal = Meal(
                         meal_type=m_type,
                         recipe_name=recipe.title,
                         description=f"A delicious {m_type}.",
                         ingredients=recipe.ingredients,
                         nutritional_info=recipe.nutrition,
                         preparation_time=f"{recipe.ready_in_minutes} mins",
                         instructions=self._format_instructions(recipe.instructions),
                         source=f"{recipe.source_api}",
                         selection_reasons=reasons if rerank_enabled else None
                     )
                     daily_meals.append(meal)
                     
                     day_ingredient_tokens.update(self._ingredient_tokens(recipe.ingredients))
                     day_dish_types.update(recipe.dish_types)
                     self._update_macros(day_macros, recipe.nutrition)
                     if recipe.title and recipe.title not in selected_titles:
                         selected_titles.append(recipe.title)
                     selected_ingredients.update(self._extract_main_ingredients(recipe.ingredients))
                     selected_cuisines.update(recipe.dish_types or [])
                     
                 else:
                     warnings.append(f"No candidates found for {m_type} on day {day_offset + 1}")
 
             meal_plan.append(DailyPlan(
                 day=day_offset + 1,
                 date=current_date,
                 meals=daily_meals
             ))
             prev_day_ingredient_tokens = day_ingredient_tokens
             prev_day_dish_types = day_dish_types
             if used_today:
                 recent_recipe_history.append(list(used_today))
                 recent_recipe_history = recent_recipe_history[-2:]

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
            dietary_compliance=combined_preferences,
            estimated_cost="$45-60",  # Mocked for now
            avg_prep_time=avg_prep
        )

        total_time = time.time() - total_start
        logger.info(f"✅ Total meal plan generation: {total_time:.2f}s")
        
        return MealPlanResponse(
            meal_plan_id=str(uuid.uuid4()),
            duration_days=parsed.days,
            generated_at=datetime.now().isoformat(),
            meal_plan=meal_plan,
            summary=summary
        )

    def _pick_best_recipe(
        self,
        candidates,
        parsed,
        context,
        day_macros,
        query,
        meal_slot,
        history,
        constraints,
        rerank_enabled
    ):
        """Pick the top-scoring recipe with an optional LLM rerank on the top-K."""
        ranked = self._rank_candidates(candidates, parsed, context, day_macros)
        if not ranked:
            return None, None
        top_recipe = ranked[0][1]
        if not self._should_rerank(ranked, rerank_enabled):
            return top_recipe, None

        top_k = min(self.rerank_top_k, len(ranked))
        top_candidates = [recipe for _, recipe in ranked[:top_k]]
        scores_by_id = {recipe.id: score for score, recipe in ranked[:top_k]}

        chosen_id, reasons = reranker_service.rerank(
            query=query,
            meal_slot=meal_slot,
            meal_type=constraints.get("meal_type"),
            candidates=top_candidates,
            scores_by_id=scores_by_id,
            constraints=constraints,
            history=history,
            fallback_id=top_recipe.id
        )
        selected = next((r for r in top_candidates if r.id == chosen_id), None)
        return selected or top_recipe, reasons

    def _rank_candidates(self, candidates, parsed, context, day_macros):
        if not candidates:
            return []
        scored = []
        for recipe in candidates:
            base_score = score_recipe(recipe, parsed, context)
            balance_penalty = self._macro_balance_penalty(day_macros, recipe.nutrition)
            scored.append((base_score - balance_penalty, recipe))
        scored.sort(key=lambda item: (-item[0], item[1].id))
        return scored

    def _should_rerank(self, ranked, rerank_enabled):
        if not rerank_enabled:
            return False
        if self.rerank_mode != "per_meal":
            logger.info(f"Rerank mode '{self.rerank_mode}' not supported; skipping rerank.")
            return False
        return len(ranked) >= 2

    def _ingredient_tokens(self, ingredients):
        """Extract simple ingredient tokens for overlap penalties."""
        tokens = set()
        for ingredient in ingredients or []:
            for token in ingredient.lower().split():
                if len(token) >= 3:
                    tokens.add(token)
        return tokens

    def _extract_main_ingredients(self, ingredients, limit=6):
        if not ingredients:
            return []
        cleaned = []
        for item in ingredients:
            base = item.split("(")[0].strip()
            if base:
                cleaned.append(base)
        return cleaned[:limit]

    def _extract_meal_time_limit(self, preferences, meal_type):
        """Extract a meal-specific time limit from preferences."""
        if not preferences:
            return None
        prefix = f"{meal_type}-under-"
        for pref in preferences:
            if pref.startswith(prefix) and pref.endswith("-minutes"):
                minutes = pref[len(prefix):-len("-minutes")]
                if minutes.isdigit():
                    return int(minutes)
            if pref == f"{meal_type}-quick":
                return DEFAULT_MEAL_QUICK_MINUTES
        return None

    def _format_instructions(self, instructions):
        """Normalize recipe instructions into a single string."""
        if not instructions:
            return ""
        if isinstance(instructions, list):
            return "\n".join(step for step in instructions if step)
        return str(instructions)

    def _update_macros(self, day_macros, nutrition):
        day_macros["protein"] += nutrition.protein or 0
        day_macros["carbs"] += nutrition.carbs or 0
        day_macros["fat"] += nutrition.fat or 0

    def _macro_balance_penalty(self, day_macros, nutrition):
        """Penalty for pushing macro ratios outside basic ranges."""
        protein = day_macros["protein"] + (nutrition.protein or 0)
        carbs = day_macros["carbs"] + (nutrition.carbs or 0)
        fat = day_macros["fat"] + (nutrition.fat or 0)
        total = protein + carbs + fat
        if total <= 0:
            return 0.0

        protein_ratio = protein / total
        carbs_ratio = carbs / total
        fat_ratio = fat / total

        penalty = 0.0
        if protein_ratio < 0.2:
            penalty += (0.2 - protein_ratio) * 5.0
        if protein_ratio > 0.45:
            penalty += (protein_ratio - 0.45) * 5.0
        if carbs_ratio < 0.25:
            penalty += (0.25 - carbs_ratio) * 4.0
        if carbs_ratio > 0.6:
            penalty += (carbs_ratio - 0.6) * 4.0
        if fat_ratio < 0.15:
            penalty += (0.15 - fat_ratio) * 4.0
        if fat_ratio > 0.4:
            penalty += (fat_ratio - 0.4) * 4.0

        return penalty


planner = MealPlanner()
