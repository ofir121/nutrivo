from typing import Dict, List, Set

# --- Diet Definitions ---
# Defines forbidden ingredients/tags for each diet
DIET_DEFINITIONS: Dict[str, Dict[str, List[str]]] = {
    "vegan": {
        "forbidden_ingredients": ["meat", "chicken", "fish", "egg", "dairy", "milk", "cheese", "butter", "honey", "seafood", "beef", "pork"],
        "forbidden_tags": ["non-vegan"]
    },
    "vegetarian": {
        "forbidden_ingredients": ["meat", "chicken", "fish", "seafood", "beef", "pork"],
        "forbidden_tags": ["non-vegetarian"]
    },
    "pescatarian": {
        "forbidden_ingredients": ["meat", "chicken", "beef", "pork"],
        "forbidden_tags": ["meat", "chicken"]
    },
    "dairy-free": {
        "forbidden_ingredients": ["milk", "cheese", "butter", "cream", "yogurt", "whey", "casein", "ghee"],
        "forbidden_tags": ["dairy"]
    },
    "nut-free": {
        "forbidden_ingredients": ["nut", "almond", "peanut", "cashew", "walnut", "pecan", "pistachio", "hazelnut"],
        "forbidden_tags": ["nuts"]
    },
    "soy-free": {
        "forbidden_ingredients": ["soy", "tofu", "tempeh", "edamame", "soy sauce", "tamari", "miso"],
        "forbidden_tags": ["soy"]
    },
    "gluten-free": {
        "forbidden_ingredients": ["wheat", "flour", "barley", "rye", "bread", "pasta", "soy sauce"],
        "allowed_exceptions": ["gluten-free", "gf"], # e.g. "gluten-free pasta" is ok
        "forbidden_tags": ["gluten"]
    },
    "low-carb": {
        "forbidden_ingredients": ["sugar", "bread", "pasta", "rice", "potato", "corn", "flour", "tortilla"],
        "forbidden_tags": ["high-carb"]
    },
    "keto": {
        "forbidden_ingredients": ["sugar", "bread", "pasta", "rice", "potato", "corn", "flour"],
        "forbidden_tags": ["high-carb"]
    },
     "paleo": {
        "forbidden_ingredients": ["sugar", "dairy", "cheese", "milk", "butter", "bean", "legume", "grain", "rice", "bread", "pasta"],
        "forbidden_tags": ["processed"]
    },
    "halal": {
        "forbidden_ingredients": ["pork", "bacon", "ham", "lard", "gelatin", "wine", "beer", "rum", "vodka", "whiskey", "whisky", "brandy"],
        "forbidden_tags": ["pork", "alcohol"]
    },
    "kosher": {
        "forbidden_ingredients": ["pork", "bacon", "ham", "lard", "gelatin", "shrimp", "crab", "lobster", "clam", "mussel", "oyster", "squid", "octopus"],
        "forbidden_tags": ["shellfish", "pork"]
    },
    "mediterranean": {
        "forbidden_ingredients": ["bacon", "sausage", "pepperoni", "salami", "hot dog", "lard", "shortening"],
        "forbidden_tags": ["processed"]
    },
    "dash": {
        "forbidden_ingredients": ["bacon", "ham", "sausage", "hot dog", "pepperoni", "salami", "processed", "deli", "pickles", "soy sauce"],
        "forbidden_tags": ["processed"]
    }
}

# --- Allergen/Exclusion Mappings ---
# Maps a user exclusion request query (key) to actual ingredients (value)
INGREDIENT_SYNONYMS: Dict[str, List[str]] = {
    "dairy": ["milk", "cheese", "butter", "cream", "yogurt", "whey", "casein"],
    "nut": ["nut", "almond", "peanut", "cashew", "walnut", "pecan"],
    "egg": ["egg", "eggs", "albumin"],
    "soy": ["soy", "tofu", "tempeh", "edamame"],
    "shellfish": ["shrimp", "crab", "lobster", "clam", "mussel", "oyster"],
    "fish": ["fish", "salmon", "tuna", "cod", "tilapia"],
    "meat": ["meat", "beef", "pork", "chicken", "lamb", "steak", "bacon", "ham"],
    "gluten": ["wheat", "barley", "rye", "malt", "flour", "bread"]
}

# --- Conflict Definitions ---
# Explicitly incompatible pairs for conflict resolution
INCOMPATIBLE_DIETS: List[Set[str]] = [
    {"vegan", "pescatarian"},   # Vegan implies no fish
    {"vegan", "keto"},          # Often hard, but technically possible. Use caution.
    {"vegetarian", "paleo"},    # Paleo eats meat, excludes legumes/grains (veg staple) -> hard to reconcile
]
