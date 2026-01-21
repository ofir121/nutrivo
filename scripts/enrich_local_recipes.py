import json
import os
from app.services.usda_service import USDAService
from app.services.nutrition_calculator import calculate_recipe_nutrition


def main():
    api_key = os.getenv("USDA_API_KEY")
    if not api_key:
        raise RuntimeError("USDA_API_KEY is required to enrich recipes.")

    input_path = "data/mock_recipes.json"
    with open(input_path, "r") as handle:
        recipes = json.load(handle)

    service = USDAService(api_key)
    updated = 0

    for recipe in recipes:
        ingredients = [i.get("original", "") for i in recipe.get("extendedIngredients", [])]
        nutrition = calculate_recipe_nutrition(ingredients, service)
        if not nutrition:
            continue
        recipe["nutrition"] = {
            "nutrients": [
                {"name": "Calories", "amount": nutrition.calories, "unit": "kcal"},
                {"name": "Protein", "amount": nutrition.protein, "unit": "g"},
                {"name": "Carbohydrates", "amount": nutrition.carbs, "unit": "g"},
                {"name": "Fat", "amount": nutrition.fat, "unit": "g"},
            ]
        }
        updated += 1

    with open(input_path, "w") as handle:
        json.dump(recipes, handle, indent=2)

    print(f"Updated nutrition for {updated} recipes.")


if __name__ == "__main__":
    main()
