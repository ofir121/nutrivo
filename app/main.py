from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time
import uuid
from app.models import MealPlanRequest, MealPlanResponse
from app.services.planner import planner
from app.services.recipe_service import RecipeSourceError
from app.core.logging_config import get_logger

app = FastAPI(title="AI-Powered Personalized Meal Planner API", version="0.1.0")
logger = get_logger(__name__)
RATE_LIMIT = 60
RATE_LIMIT_WINDOW_SECONDS = 60
rate_limit_state = {}

@app.middleware("http")
async def rate_limit_requests(request: Request, call_next):
    now = time.time()
    client_ip = request.client.host if request.client else "unknown"
    state = rate_limit_state.get(client_ip)

    if not state or now - state["window_start"] > RATE_LIMIT_WINDOW_SECONDS:
        state = {"window_start": now, "count": 0}

    if state["count"] >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please retry later."
            }
        )

    state["count"] += 1
    rate_limit_state[client_ip] = state
    return await call_next(request)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000.0
    logger.info(
        f"{request.method} {request.url.path} {response.status_code} "
        f"{duration_ms:.1f}ms request_id={request_id}"
    )
    response.headers["X-Request-ID"] = request_id
    return response

@app.exception_handler(RecipeSourceError)
async def recipe_source_error_handler(request: Request, exc: RecipeSourceError):
    logger.error(f"Recipe source failure: {exc.errors}")
    return JSONResponse(
        status_code=502,
        content={
            "error_code": "RECIPE_SOURCE_FAILURE",
            "message": "Failed to fetch recipes from configured sources.",
            "sources": exc.sources,
            "errors": exc.errors
        }
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Meal Planner API. Visit /docs for documentation."}


@app.post("/api/generate-meal-plan", response_model=MealPlanResponse)
async def generate_meal_plan(request: MealPlanRequest):
    """
    Generate a personalized meal plan based on a natural language query.
    """
    return planner.generate_meal_plan(request)
