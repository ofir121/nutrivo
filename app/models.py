from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MealPlanRequest(BaseModel):
    query: str = Field(..., description="Natural language meal plan request")
    estimate_prep_time: bool = Field(False, description="Use AI to estimate preparation times (slower but more accurate)")
    sources: List[str] = Field(default=["Local"], description="List of recipe sources to use")

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
    instructions: List[str]
    source: str

class DailyPlan(BaseModel):
    day: int
    date: str
    meals: List[Meal]

class MealPlanSummary(BaseModel):
    total_meals: int
    diets: List[str] = Field(default_factory=list)  # e.g., ["vegetarian", "vegan"]
    exclusions: List[str] = Field(default_factory=list)  # e.g., ["peanuts", "shellfish"]
    preferences: List[str] = Field(default_factory=list)  # e.g., ["high-protein", "low-carb"]
    estimated_cost: str
    avg_prep_time: str
    warnings: List[str] = Field(default_factory=list)
    defaults_applied: List[str] = Field(default_factory=list)

class MealPlanResponse(BaseModel):
    meal_plan_id: str
    duration_days: int
    generated_at: str
    clarified_intent: Optional[str] = None  # How the AI interpreted the query
    preferences: List[str] = Field(default_factory=list)  # Extracted preferences like "high-protein", "low-carb"
    meal_plan: List[DailyPlan]
    summary: MealPlanSummary
