import re
from typing import Optional, Tuple


UNIT_TO_GRAMS = {
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "kg": 1000.0,
    "kilogram": 1000.0,
    "kilograms": 1000.0,
    "oz": 28.3495,
    "ounce": 28.3495,
    "ounces": 28.3495,
    "lb": 453.592,
    "pound": 453.592,
    "pounds": 453.592,
    "ml": 1.0,
    "milliliter": 1.0,
    "milliliters": 1.0,
    "l": 1000.0,
    "liter": 1000.0,
    "liters": 1000.0,
    "tsp": 5.0,
    "tsp.": 5.0,
    "teaspoon": 5.0,
    "teaspoons": 5.0,
    "tbsp": 15.0,
    "tbsp.": 15.0,
    "tblsp": 15.0,
    "tbs": 15.0,
    "tablespoon": 15.0,
    "tablespoons": 15.0,
    "cup": 240.0,
    "cups": 240.0,
    "clove": 3.0,
    "cloves": 3.0,
}


def parse_ingredient(ingredient: str) -> Tuple[str, Optional[float]]:
    """Parse an ingredient string into a normalized name and grams estimate."""
    text = ingredient.strip().lower()
    paren_match = re.search(r"\(([^)]*)\)", text)
    if paren_match:
        paren_text = paren_match.group(1).strip().lower()
        grams = _parse_grams_from_text(paren_text)
        if grams is not None:
            cleaned = _strip_parens(text)
            return _normalize_name(cleaned), grams

    text = _strip_parens(text).strip().lower()
    quantity, rest = _parse_quantity(text)
    if quantity is None:
        return _normalize_name(text), None

    unit, name = _parse_unit(rest)
    name = _normalize_name(name)
    if not unit:
        return name, None

    grams_per_unit = UNIT_TO_GRAMS.get(unit)
    if grams_per_unit is None:
        return name, None
    return name, quantity * grams_per_unit


def _parse_quantity(text: str) -> Tuple[Optional[float], str]:
    match = re.match(r"^(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?|\d+\s*-\s*\d+)", text)
    if not match:
        return None, text

    raw = match.group(1)
    rest = text[match.end():].strip()
    if "-" in raw:
        parts = [p.strip() for p in raw.split("-") if p.strip()]
        values = [_parse_number(p) for p in parts]
        values = [v for v in values if v is not None]
        if values:
            return sum(values) / len(values), rest
        return None, rest

    return _parse_number(raw), rest


def _parse_number(raw: str) -> Optional[float]:
    if " " in raw:
        parts = raw.split()
        base = _parse_number(parts[0])
        frac = _parse_number(parts[1])
        if base is not None and frac is not None:
            return base + frac
        return base or frac
    if "/" in raw:
        numerator, denominator = raw.split("/", 1)
        try:
            return float(numerator) / float(denominator)
        except ValueError:
            return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_unit(text: str) -> Tuple[Optional[str], str]:
    parts = text.split()
    if not parts:
        return None, text
    unit = parts[0].rstrip(".,")
    if unit in UNIT_TO_GRAMS:
        rest = " ".join(parts[1:]).strip()
        return unit, _strip_of(rest)
    return None, text


def _strip_parens(text: str) -> str:
    return re.sub(r"\([^)]*\)", "", text)


def _strip_of(text: str) -> str:
    return re.sub(r"^of\s+", "", text.strip())


def _normalize_name(text: str) -> str:
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return " ".join(text.split())


def _parse_grams_from_text(text: str) -> Optional[float]:
    quantity, rest = _parse_quantity(text)
    if quantity is not None:
        unit, _ = _parse_unit(rest)
        if unit:
            grams_per_unit = UNIT_TO_GRAMS.get(unit)
            if grams_per_unit is not None:
                return quantity * grams_per_unit
    match = re.match(r"^(\d+(?:\.\d+)?)([a-zA-Z]+)$", text)
    if match:
        quantity = _parse_number(match.group(1))
        unit = match.group(2).lower()
        grams_per_unit = UNIT_TO_GRAMS.get(unit)
        if quantity is not None and grams_per_unit is not None:
            return quantity * grams_per_unit
    return None
