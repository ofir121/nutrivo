from typing import List, Optional
from app.core.logging_config import get_logger
from app.models import NutritionalInfo
from app.utils.ingredient_parser import parse_ingredient
from app.services.usda_service import USDAService

logger = get_logger(__name__)


def calculate_recipe_nutrition(
    ingredients: List[str],
    usda_service: USDAService
) -> Optional[NutritionalInfo]:
    if not ingredients:
        return None

    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    missing = 0

    for item in ingredients:
        name, grams = parse_ingredient(item)
        nutrients = usda_service.get_nutrients_per_100g(name)
        if not nutrients:
            missing += 1
            continue
        weight = grams if grams is not None else 100.0
        factor = weight / 100.0
        totals["calories"] += nutrients["calories"] * factor
        totals["protein"] += nutrients["protein"] * factor
        totals["carbs"] += nutrients["carbs"] * factor
        totals["fat"] += nutrients["fat"] * factor

    if missing == len(ingredients):
        return None

    return NutritionalInfo(
        calories=int(round(totals["calories"])),
        protein=int(round(totals["protein"])),
        carbs=int(round(totals["carbs"])),
        fat=int(round(totals["fat"]))
    )
