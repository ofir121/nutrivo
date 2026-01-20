import re
from typing import Iterable, List, Union

MinutesInput = Union[str, Iterable[str], None]


def estimate_prep_time(ingredients: List[str], instructions: MinutesInput) -> int:
    """Estimate total time in minutes from ingredients and instructions."""
    ingredient_count = len([i for i in (ingredients or []) if str(i).strip()])
    steps = _normalize_steps(instructions)
    text = " ".join(steps).lower()

    explicit_minutes = _sum_explicit_minutes(text) + _sum_explicit_hours(text) * 60
    prep_minutes = 5.0 + max(0, ingredient_count - 5) * 0.5
    prep_minutes += max(0, len(steps) - 3) * 1.5

    cook_minutes = explicit_minutes if explicit_minutes > 0 else _keyword_cook_minutes(text)
    wait_minutes = _wait_penalty_minutes(text, explicit_minutes > 0)

    total = prep_minutes + cook_minutes + wait_minutes
    total = max(5, min(int(round(total)), 180))
    return total


def _normalize_steps(instructions: MinutesInput) -> List[str]:
    if not instructions:
        return []
    if isinstance(instructions, str):
        parts = re.split(r'[\r\n]+', instructions)
        return [p.strip() for p in parts if p.strip()]
    steps = [str(s).strip() for s in instructions if str(s).strip()]
    return steps


def _sum_explicit_minutes(text: str) -> int:
    total = 0
    range_pattern = re.compile(r'(\d+)\s*-\s*(\d+)\s*(?:minutes|mins|min)\b')
    for match in range_pattern.finditer(text):
        total += int(match.group(2))
    text = range_pattern.sub("", text)
    single_pattern = re.compile(r'(\d+)\s*(?:minutes|mins|min)\b')
    for match in single_pattern.finditer(text):
        total += int(match.group(1))
    return total


def _sum_explicit_hours(text: str) -> int:
    total = 0
    range_pattern = re.compile(r'(\d+)\s*-\s*(\d+)\s*(?:hours|hour|hrs|hr)\b')
    for match in range_pattern.finditer(text):
        total += int(match.group(2))
    text = range_pattern.sub("", text)
    single_pattern = re.compile(r'(\d+)\s*(?:hours|hour|hrs|hr)\b')
    for match in single_pattern.finditer(text):
        total += int(match.group(1))
    return total


def _keyword_cook_minutes(text: str) -> int:
    if not text:
        return 8
    keyword_buckets = {
        30: ["slow cook", "slow-cook", "slow cooker", "slow-cooker"],
        25: ["pressure cook", "pressure-cook", "instant pot"],
        20: ["bake", "roast", "braise", "stew", "casserole"],
        15: ["boil", "simmer", "poach", "steam"],
        12: ["saute", "stir fry", "stir-fry", "fry", "grill", "sear"]
    }
    best = 8
    for minutes, keywords in keyword_buckets.items():
        if any(k in text for k in keywords):
            best = max(best, minutes)
    return best


def _wait_penalty_minutes(text: str, has_explicit: bool) -> int:
    if "overnight" in text:
        return 480
    if has_explicit:
        return 0
    penalties = {
        "marinate": 60,
        "chill": 30,
        "refrigerate": 30,
        "rest": 10,
        "proof": 60,
        "rise": 60
    }
    return max((v for k, v in penalties.items() if k in text), default=0)
