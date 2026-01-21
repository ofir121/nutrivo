from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, constr
from datetime import datetime


class MealPlanRequest(BaseModel):
    query: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Natural language meal plan request"
    )
    sources: List[str] = Field(default=["Local"], description="List of recipe sources to use")
    rerank_enabled: Optional[bool] = Field(
        default=None,
        description="Enable LLM reranking of top-K candidates"
    )

class ParsedQuery(BaseModel):
    days: int
    diets: List[str] = Field(default_factory=list)  # Changed from single diet_type
    calories: Optional[int] = None
    exclude: List[str] = Field(default_factory=list)
    preferences: List[str] = Field(default_factory=list)  # e.g. ["high-protein", "low-carb"]
    meals_per_day: int = 3
    clarified_intent: Optional[str] = None



class NutritionalInfo(BaseModel):
    calories: int
    protein: int
    carbs: int
    fat: int

class Recipe(BaseModel):
    id: str
    title: str
    ready_in_minutes: int
    servings: int
    image: Optional[str] = None
    diets: List[str] = Field(default_factory=list)
    dish_types: List[str] = Field(default_factory=list)
    ingredients: List[str]
    instructions: List[str] 
    nutrition: NutritionalInfo
    source_api: str 
    original_data: Optional[Dict[str, Any]] = None

class Meal(BaseModel):
    meal_type: str
    recipe_name: str
    description: str
    ingredients: List[str]
    nutritional_info: NutritionalInfo
    preparation_time: str
    instructions: str
    source: str
    selection_reasons: Optional[List[str]] = None

class DailyPlan(BaseModel):
    day: int
    date: str
    meals: List[Meal]

class MealPlanSummary(BaseModel):
    total_meals: int
    dietary_compliance: List[str] = Field(default_factory=list)
    estimated_cost: str
    avg_prep_time: str

class MealPlanResponse(BaseModel):
    meal_plan_id: str
    duration_days: int
    generated_at: str
    meal_plan: List[DailyPlan]
    summary: MealPlanSummary
