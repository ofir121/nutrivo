import json
import os
from typing import Dict, Optional
import requests
from dotenv import load_dotenv
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class USDAService:
    BASE_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
    PREFERRED_DATA_TYPES = ["Foundation", "SR Legacy", "Survey (FNDDS)", "Branded"]

    def __init__(self, api_key: str, cache_path: str = "data/usda_cache.json"):
        load_dotenv(".env")
        self.api_key = api_key or os.getenv("USDA_API_KEY")
        self.cache_path = cache_path
        self.cache: Dict[str, Dict[str, object]] = self._load_cache()
        if not self.api_key:
            logger.warning("USDA_API_KEY not set. USDA nutrition lookup is disabled.")
        else:
            logger.info("USDA_API_KEY loaded. USDA nutrition lookup enabled.")

    def get_nutrients_per_100g(self, ingredient: str) -> Optional[Dict[str, float]]:
        if not ingredient:
            return None
        logger.debug(f"USDA lookup for ingredient: {ingredient}")
        cache_key = ingredient.lower()
        cached = self.cache.get(cache_key)
        if cached:
            return cached.get("nutrients_per_100g")

        data = self._search_food(ingredient)
        if not data:
            return None

        nutrients = _extract_nutrients(data.get("foodNutrients", []))
        if not nutrients:
            logger.warning(f"USDA lookup returned no nutrients for: {ingredient}")
            return None

        self.cache[cache_key] = {
            "fdc_id": data.get("fdcId"),
            "nutrients_per_100g": nutrients
        }
        self._save_cache()
        return nutrients

    def _search_food(self, ingredient: str) -> Optional[Dict[str, object]]:
        if not self.api_key:
            return None
        params = {
            "api_key": self.api_key,
            "query": ingredient,
            "pageSize": 5
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            payload = response.json()
            foods = payload.get("foods", [])
            if not foods:
                return None
            return _pick_best_food(foods, self.PREFERRED_DATA_TYPES)
        except Exception as exc:
            logger.warning(f"USDA lookup failed for '{ingredient}': {exc}")
            return None

    def _load_cache(self) -> Dict[str, Dict[str, object]]:
        if not os.path.exists(self.cache_path):
            return {}
        try:
            with open(self.cache_path, "r") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_cache(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w") as handle:
                json.dump(self.cache, handle, indent=2)
        except OSError as exc:
            logger.warning(f"Failed to write USDA cache: {exc}")


def _pick_best_food(foods, preferred_types):
    def score(item):
        data_type = item.get("dataType", "")
        try:
            return preferred_types.index(data_type)
        except ValueError:
            return len(preferred_types) + 1

    foods = sorted(foods, key=score)
    return foods[0] if foods else None


def _extract_nutrients(food_nutrients) -> Optional[Dict[str, float]]:
    mapping = {
        "Energy": "calories",
        "Protein": "protein",
        "Carbohydrate, by difference": "carbs",
        "Total lipid (fat)": "fat"
    }
    result = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for nutrient in food_nutrients:
        name = nutrient.get("nutrientName")
        value = nutrient.get("value")
        unit = nutrient.get("unitName", "")
        key = mapping.get(name)
        if key is None or value is None:
            continue
        if name == "Energy" and unit.lower() == "kj":
            value = value / 4.184
        result[key] = float(value)

    if all(v == 0.0 for v in result.values()):
        return None
    return result
