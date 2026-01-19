from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MealPlanRequest(BaseModel):
    query: str = Field(..., description="Natural language meal plan request")

class ParsedQuery(BaseModel):
    days: int
    diets: List[str] = [] # Changed from single diet_type
    calories: Optional[int] = None
    exclude: List[str] = []
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
    diets: List[str] = []
    dish_types: List[str] = []
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
    instructions: List[str]
    source: str

class DailyPlan(BaseModel):
    day: int
    date: str
    meals: List[Meal]

class MealPlanSummary(BaseModel):
    total_meals: int
    dietary_compliance: List[str]
    estimated_cost: str
    avg_prep_time: str

class MealPlanResponse(BaseModel):
    meal_plan_id: str
    duration_days: int
    generated_at: str
    clarified_intent: Optional[str] = None  # How the AI interpreted the query
    meal_plan: List[DailyPlan]
    summary: MealPlanSummary
