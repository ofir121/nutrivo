from fastapi import FastAPI
from app.models import MealPlanRequest, MealPlanResponse
from app.services.planner import planner

app = FastAPI(title="AI-Powered Personalized Meal Planner API", version="0.1.0")

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Meal Planner API. Visit /docs for documentation."}


@app.post("/api/generate-meal-plan", response_model=MealPlanResponse)
async def generate_meal_plan(request: MealPlanRequest):
    """
    Generate a personalized meal plan based on a natural language query.
    """
    return planner.generate_meal_plan(request)


